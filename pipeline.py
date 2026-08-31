import os, traceback, json, ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from config import *
from db import *
from intelligence import research_market, generate_concepts, score_concepts, fingerprint, jaccard
from generator import render_design, visual_score
from safety import adaptive_concurrency, system_health
from runtime_lock import cycle_lock


def _log(message,cycle_id=None,stage=None):
    prefix='[Trend2Sketch]'
    if cycle_id is not None: prefix+=f'[cycle={cycle_id}]'
    if stage: prefix+=f'[stage={stage}]'
    print(f'{prefix} {message}',flush=True)

def _existing_texts(limit=1500):
    rows=query('SELECT title,description,concept_family FROM designs ORDER BY id DESC LIMIT ?',(limit,))
    return [' '.join([r.get('title') or '',r.get('description') or '',r.get('concept_family') or '']) for r in rows]

def _novel(item,texts,threshold=0.72):
    text=' '.join(str(item.get(k,'')) for k in ('title','description','concept_family'))
    return all(jaccard(text,t)<threshold for t in texts[-1200:])

def cleanup_old_images():
    cutoff=datetime.now(timezone.utc)-timedelta(days=RETENTION_DAYS)
    for r in query('SELECT id,image_path,created_at,favorite FROM designs WHERE image_path IS NOT NULL AND favorite=0'):
        try:
            dt=datetime.fromisoformat(r['created_at'])
            if dt<cutoff and os.path.exists(r['image_path']):
                os.remove(r['image_path']); execute('UPDATE designs SET image_path=NULL,status=? WHERE id=?',('archived',r['id']))
        except Exception as e: _log(f'cleanup warning: {type(e).__name__}: {e}')

def _fail_cycle(cycle_id,stage,exc):
    tb=traceback.format_exc(); message=f'{type(exc).__name__}: {exc}'
    update_cycle(cycle_id,status='failed',stage=stage,finished_at=now_iso(),note=f'FAILED AT {stage}\n{message}\n{tb}'[:12000])
    _log(message,cycle_id,stage); print(tb,flush=True)

def _speed_profile(mode,render_cap):
    mode=(mode or 'Balanced').title()
    if mode not in ('Fast','Balanced','Deep'): mode='Balanced'
    if mode=='Fast':
        pool=min(180,max(60,render_cap*2+40)); return dict(mode=mode,pool=pool,batch=20,concept_workers=FAST_CONCEPT_WORKERS,score_workers=FAST_SCORE_WORKERS,cache_minutes=360)
    if mode=='Deep':
        return dict(mode=mode,pool=max(CONCEPT_POOL_SIZE,min(400,render_cap*4)),batch=40,concept_workers=DEEP_CONCEPT_WORKERS,score_workers=DEEP_SCORE_WORKERS,cache_minutes=0)
    pool=min(CONCEPT_POOL_SIZE,max(100,render_cap*3)); return dict(mode=mode,pool=pool,batch=25,concept_workers=BALANCED_CONCEPT_WORKERS,score_workers=BALANCED_SCORE_WORKERS,cache_minutes=120)

def _cached_research(selected_categories,selected_lanes,max_age_minutes):
    if max_age_minutes<=0: return None
    row=one('SELECT * FROM research_snapshots ORDER BY id DESC LIMIT 1')
    if not row: return None
    try:
        created=datetime.fromisoformat(row['created_at'])
        if created.tzinfo is None: created=created.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc)-created>timedelta(minutes=max_age_minutes): return None
        meta=json.loads(row.get('source_note') or '{}')
        if meta.get('categories',[])!=selected_categories or meta.get('lanes',[])!=selected_lanes: return None
        try: data=json.loads(row.get('summary') or '{}')
        except Exception: data=ast.literal_eval(row.get('summary') or '{}')
        return data if isinstance(data,dict) else None
    except Exception: return None

def run_cycle(manual=False):
    init_db(); cleanup_old_images(); mark_stale_running_cycles(CYCLE_STALE_MINUTES)
    with cycle_lock(blocking=False) as acquired:
        if not acquired:
            active=active_cycle(); _log(f'cycle request skipped because another cycle is active: #{active.get("id") if active else "unknown"}',None,'single_cycle_guard')
            return active.get('id') if active else None
        if not manual and not get_bool_setting('auto_enabled',True):
            _log('autonomous generation is paused by Live Studio Controls',None,'automation_paused'); return None
        cycle_id=create_cycle()
        quality_threshold=max(75,min(100,get_int_setting('quality_threshold',DISPLAY_THRESHOLD)))
        render_cap=max(1,min(100,get_int_setting('render_cap',MAX_RENDER_PER_CYCLE)))
        speed_mode=get_setting('speed_mode','Balanced') or 'Balanced'; profile=_speed_profile(speed_mode,render_cap)
        try:
            selected_categories=json.loads(get_setting('selected_categories','[]') or '[]')
            if not isinstance(selected_categories,list): selected_categories=[]
        except Exception: selected_categories=[]
        try:
            selected_lanes=json.loads(get_setting('selected_lanes','["Diamond", "South Indian Gemstone"]') or '[]')
            if not isinstance(selected_lanes,list) or not selected_lanes: selected_lanes=['Diamond','South Indian Gemstone']
        except Exception: selected_lanes=['Diamond','South Indian Gemstone']
        stage='startup'; _log(f'cycle started; speed={profile}',cycle_id,stage)
        try:
            if not OPENAI_API_KEY: raise RuntimeError('OPENAI_API_KEY is missing from the environment')
            stage='resource_check'; health=system_health(); _log(f'health={health}',cycle_id,stage)
            if not health['ok']:
                update_cycle(cycle_id,status='paused',stage='resource_guard',finished_at=now_iso(),note=str(health)); return cycle_id
            stage='budget_check'; spend=today_spend(); _log(f'estimated spend today=${spend:.2f}; budget=${DAILY_API_BUDGET_USD:.2f}',cycle_id,stage)
            if spend+EST_TEXT_CYCLE_COST_USD>=DAILY_API_BUDGET_USD:
                update_cycle(cycle_id,status='paused',stage='budget_guard',finished_at=now_iso(),note=f'Daily budget reached: ${spend:.2f}'); return cycle_id

            stage='research'; update_cycle(cycle_id,stage=stage,note=f'{profile["mode"]} mode: checking research cache')
            research=_cached_research(selected_categories,selected_lanes,profile['cache_minutes'])
            if research is not None:
                _log(f'reusing matching research cache (max age {profile["cache_minutes"]} min)',cycle_id,stage)
                update_cycle(cycle_id,note=f'{profile["mode"]} mode: reused recent matching research; starting parallel discovery')
            else:
                _log(f'calling text model {TEXT_MODEL} with automatic retry/fallback',cycle_id,stage)
                research=research_market(selected_categories=selected_categories,selected_lanes=selected_lanes)
                meta=json.dumps({'categories':selected_categories,'lanes':selected_lanes,'live_web':True})
                execute('INSERT INTO research_snapshots(created_at,summary,source_note) VALUES(?,?,?)',(now_iso(),json.dumps(research),meta))
                log_spend(cycle_id,'research_and_concepts',EST_TEXT_CYCLE_COST_USD,'configured estimate')

            stage='concept_discovery'; update_cycle(cycle_id,stage=stage,note=f'{profile["mode"]}: parallel concept discovery 0/{profile["pool"]}')
            def concept_progress(done,total):
                update_cycle(cycle_id,concepts_discovered=done,note=f'{profile["mode"]}: parallel concept discovery {done}/{total}')
            concepts=generate_concepts(research,profile['pool'],selected_categories=selected_categories,selected_lanes=selected_lanes,workers=profile['concept_workers'],batch_size=profile['batch'],progress_callback=concept_progress)
            update_cycle(cycle_id,concepts_discovered=len(concepts),stage='scoring',note=f'Parallel discovery complete: {len(concepts)}. Scoring 0/{len(concepts)}')

            stage='scoring'
            def score_progress(done,total): update_cycle(cycle_id,candidates_scored=done,note=f'{profile["mode"]}: parallel scoring {done}/{total}')
            scored=score_concepts(concepts,workers=profile['score_workers'],progress_callback=score_progress)
            update_cycle(cycle_id,candidates_scored=len(scored),note=f'Parallel scoring completed: {len(scored)} candidates')

            existing=_existing_texts(); shortlist=[]
            for c in sorted(scored,key=lambda x:x.get('pre_score',0),reverse=True):
                if float(c.get('pre_score',0))<PRE_RENDER_MIN_SCORE: continue
                if not _novel(c,existing): continue
                fp=fingerprint(c)
                if one('SELECT id FROM designs WHERE fingerprint=?',(fp,)): continue
                shortlist.append(c); existing.append(' '.join([c.get('title',''),c.get('description',''),c.get('concept_family','')]))
                if len(shortlist)>=render_cap: break
            _log(f'ranked shortlist={len(shortlist)}; cap={render_cap}; final gate={quality_threshold}+',cycle_id,'shortlist')
            remaining=max(0,DAILY_API_BUDGET_USD-today_spend()); affordable=int(remaining//max(EST_IMAGE_COST_USD,0.0001)); shortlist=shortlist[:affordable]
            if not shortlist:
                update_cycle(cycle_id,status='completed',stage='complete',finished_at=now_iso(),note='No novel ranked concepts could be rendered within the remaining daily budget.'); return cycle_id
            concurrency=adaptive_concurrency()
            if concurrency<=0:
                update_cycle(cycle_id,status='paused',stage='resource_guard',finished_at=now_iso(),note=str(system_health())); return cycle_id
            # Fast/Balanced may safely use one extra render slot when resources allow; safety.py remains the hard guard.
            if profile['mode']=='Fast': concurrency=min(5,max(concurrency,4))
            elif profile['mode']=='Balanced': concurrency=min(4,max(concurrency,3))
            stage='rendering'; update_cycle(cycle_id,stage=stage,note=f'{profile["mode"]}: rendering {len(shortlist)} concepts with {concurrency} parallel workers')
            rendered=visible=rejected=failed=0
            def job(pair):
                idx,c=pair; path=render_design(c,cycle_id,idx); vscore,vreason,redesign=visual_score(c,path)
                pre=float(c.get('pre_score',0)); visual=float(vscore); tw=max(FINAL_PRE_WEIGHT+FINAL_VISUAL_WEIGHT,0.0001)
                final=round((pre*FINAL_PRE_WEIGHT+visual*FINAL_VISUAL_WEIGHT)/tw,1)
                return c,path,vscore,vreason,redesign,final
            with ThreadPoolExecutor(max_workers=concurrency) as ex:
                futs={ex.submit(job,p):p for p in enumerate(shortlist,1)}
                for fut in as_completed(futs):
                    c=futs[fut][1]
                    try:
                        c,path,vscore,vreason,redesign,final=fut.result(); rendered+=1; vis=1 if final>=quality_threshold else 0
                        if vis: visible+=1
                        else: rejected+=1
                        execute('''INSERT OR IGNORE INTO designs(cycle_id,created_at,lane,category,concept_family,title,description,materials,target_weight,region_signal,rationale,pre_score,visual_score,final_score,image_path,visible,fingerprint,status,error) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(
                            cycle_id,now_iso(),c.get('lane'),c.get('category'),c.get('concept_family'),c.get('title'),c.get('description'),c.get('materials'),c.get('target_weight'),c.get('region_signal'),(c.get('score_reason','')+' | Visual: '+vreason),c.get('pre_score'),vscore,final,path,vis,fingerprint(c),'visible' if vis else 'rejected',redesign if not vis else None))
                        log_spend(cycle_id,'image',EST_IMAGE_COST_USD,'configured estimate')
                    except Exception as e:
                        failed+=1; _log(f'render job failed after retries: {type(e).__name__}: {e}',cycle_id,stage)
                    update_cycle(cycle_id,rendered=rendered,visible=visible,rejected=rejected,failed=failed,estimated_cost_usd=EST_TEXT_CYCLE_COST_USD+rendered*EST_IMAGE_COST_USD,note=f'{profile["mode"]}: {rendered}/{len(shortlist)} rendered, {failed} failed')
            update_cycle(cycle_id,status='completed',stage='complete',finished_at=now_iso(),rendered=rendered,visible=visible,rejected=rejected,failed=failed,note=f'Cycle completed successfully in {profile["mode"]} mode; parallel pipeline active.')
            return cycle_id
        except Exception as e:
            _fail_cycle(cycle_id,stage,e); return cycle_id
