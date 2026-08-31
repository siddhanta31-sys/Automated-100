import os, time, traceback, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from config import *
from db import *
from intelligence import research_market, generate_concepts, score_concepts, fingerprint, jaccard
from generator import render_design, visual_score
from safety import adaptive_concurrency, system_health


def _log(message, cycle_id=None, stage=None):
    prefix='[Trend2Sketch]'
    if cycle_id is not None: prefix += f'[cycle={cycle_id}]'
    if stage: prefix += f'[stage={stage}]'
    print(f'{prefix} {message}', flush=True)


def _existing_texts(limit=1500):
    rows=query('SELECT title,description,concept_family FROM designs ORDER BY id DESC LIMIT ?', (limit,))
    return [' '.join([r.get('title') or '',r.get('description') or '',r.get('concept_family') or '']) for r in rows]

def _novel(item, texts, threshold=0.72):
    text=' '.join(str(item.get(k,'')) for k in ('title','description','concept_family'))
    return all(jaccard(text,t) < threshold for t in texts[-1200:])

def cleanup_old_images():
    cutoff=datetime.now(timezone.utc)-timedelta(days=RETENTION_DAYS)
    rows=query('SELECT id,image_path,created_at,favorite FROM designs WHERE image_path IS NOT NULL AND favorite=0')
    for r in rows:
        try:
            dt=datetime.fromisoformat(r['created_at'])
            if dt < cutoff and os.path.exists(r['image_path']):
                os.remove(r['image_path'])
                execute('UPDATE designs SET image_path=NULL,status=? WHERE id=?',('archived',r['id']))
        except Exception as e:
            _log(f'cleanup warning: {type(e).__name__}: {e}')

def _fail_cycle(cycle_id, stage, exc):
    tb=traceback.format_exc()
    message=f'{type(exc).__name__}: {exc}'
    note=f'FAILED AT {stage}\n{message}\n{tb}'[:12000]
    update_cycle(cycle_id,status='failed',stage=stage,finished_at=now_iso(),note=note)
    _log(message, cycle_id, stage)
    print(tb, flush=True)


def run_cycle(manual=False):
    init_db(); cleanup_old_images()
    cycle_id=create_cycle()
    quality_threshold=max(75,min(100,get_int_setting('quality_threshold',DISPLAY_THRESHOLD)))
    render_cap=max(1,min(100,get_int_setting('render_cap',MAX_RENDER_PER_CYCLE)))
    try:
        selected_categories=json.loads(get_setting('selected_categories','[]') or '[]')
        if not isinstance(selected_categories,list): selected_categories=[]
    except Exception:
        selected_categories=[]
    try:
        selected_lanes=json.loads(get_setting('selected_lanes','[\"Diamond\", \"South Indian Gemstone\"]') or '[]')
        if not isinstance(selected_lanes,list) or not selected_lanes: selected_lanes=['Diamond','South Indian Gemstone']
    except Exception:
        selected_lanes=['Diamond','South Indian Gemstone']
    if not manual and not get_bool_setting('auto_enabled',True):
        update_cycle(cycle_id,status='paused',stage='automation_paused',finished_at=now_iso(),note='Autonomous cycles are paused from Live Studio Controls.')
        _log('autonomous generation paused by live setting', cycle_id, 'automation_paused')
        return cycle_id
    stage='startup'
    _log('cycle started', cycle_id, stage)
    try:
        if not OPENAI_API_KEY:
            raise RuntimeError('OPENAI_API_KEY is missing from the environment')

        stage='resource_check'
        health=system_health()
        _log(f'health={health}', cycle_id, stage)
        if not health['ok']:
            update_cycle(cycle_id,status='paused',stage='resource_guard',finished_at=now_iso(),note=str(health))
            return cycle_id

        stage='budget_check'
        spend=today_spend()
        _log(f'estimated spend today=${spend:.2f}; budget=${DAILY_API_BUDGET_USD:.2f}', cycle_id, stage)
        if spend + EST_TEXT_CYCLE_COST_USD >= DAILY_API_BUDGET_USD:
            update_cycle(cycle_id,status='paused',stage='budget_guard',finished_at=now_iso(),note=f'Daily budget reached: ${spend:.2f}')
            return cycle_id

        stage='research'
        update_cycle(cycle_id,stage=stage,note='Research started')
        _log(f'calling text model {TEXT_MODEL} with web research', cycle_id, stage)
        research=research_market(selected_categories=selected_categories, selected_lanes=selected_lanes)
        _log(f'research returned keys={list(research.keys()) if isinstance(research,dict) else type(research).__name__}', cycle_id, stage)
        execute('INSERT INTO research_snapshots(created_at,summary,source_note) VALUES(?,?,?)',(now_iso(),str(research),'Live web research where available; public signals only.'))
        log_spend(cycle_id,'research_and_concepts',EST_TEXT_CYCLE_COST_USD,'configured estimate')

        stage='concept_discovery'
        update_cycle(cycle_id,stage=stage,note='Generating concept pool')
        _log(f'generating {CONCEPT_POOL_SIZE} concepts for categories={selected_categories or ["AUTO"]}, lanes={selected_lanes}', cycle_id, stage)
        concepts=generate_concepts(research,CONCEPT_POOL_SIZE, selected_categories=selected_categories, selected_lanes=selected_lanes)
        _log(f'generated {len(concepts)} concepts', cycle_id, stage)
        update_cycle(cycle_id,concepts_discovered=len(concepts),stage='scoring',note='Concept discovery completed')

        stage='scoring'
        scored=score_concepts(concepts)
        _log(f'scored {len(scored)} concepts', cycle_id, stage)
        update_cycle(cycle_id,candidates_scored=len(scored),note='Scoring completed')

        # Rank first, render second. Do NOT require a 95+ concept score before image generation.
        # The strict 95+ gate is applied only after the finished design has been visually evaluated.
        existing=_existing_texts(); shortlist=[]
        ranked=sorted(scored,key=lambda x:x.get('pre_score',0),reverse=True)
        for c in ranked:
            if float(c.get('pre_score',0)) < PRE_RENDER_MIN_SCORE: continue
            if not _novel(c,existing): continue
            fp=fingerprint(c)
            if one('SELECT id FROM designs WHERE fingerprint=?',(fp,)): continue
            shortlist.append(c)
            existing.append(' '.join([c.get('title',''),c.get('description',''),c.get('concept_family','')]))
            if len(shortlist)>=render_cap: break
        _log(f'ranked shortlist={len(shortlist)}; render cap={render_cap}; pre-render floor={PRE_RENDER_MIN_SCORE}; final visibility gate={quality_threshold}+', cycle_id, 'shortlist')

        remaining=max(0, DAILY_API_BUDGET_USD-today_spend())
        affordable=int(remaining//max(EST_IMAGE_COST_USD,0.0001))
        shortlist=shortlist[:affordable]
        if not shortlist:
            update_cycle(cycle_id,status='completed',stage='complete',finished_at=now_iso(),note='No novel ranked concepts could be rendered within the remaining daily budget.')
            _log('completed with no affordable renderable concepts', cycle_id, 'complete')
            return cycle_id

        concurrency=adaptive_concurrency()
        if concurrency<=0:
            update_cycle(cycle_id,status='paused',stage='resource_guard',finished_at=now_iso(),note=str(system_health()))
            return cycle_id
        stage='rendering'
        update_cycle(cycle_id,stage=stage,note=f'Rendering top {len(shortlist)} ranked concepts with concurrency {concurrency}; live final gate is {quality_threshold}+')
        rendered=visible=rejected=failed=0

        def job(pair):
            idx,c=pair
            path=render_design(c,cycle_id,idx)
            vscore,vreason,redesign=visual_score(c,path)
            pre=float(c.get('pre_score',0))
            visual=float(vscore)
            # Final score is dominated by the finished design review, while still retaining
            # commercial/manufacturing intelligence from the concept stage.
            total_w=max(FINAL_PRE_WEIGHT+FINAL_VISUAL_WEIGHT, 0.0001)
            final=round((pre*FINAL_PRE_WEIGHT + visual*FINAL_VISUAL_WEIGHT)/total_w, 1)
            return c,path,vscore,vreason,redesign,final

        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futs={ex.submit(job,p):p for p in enumerate(shortlist,1)}
            for fut in as_completed(futs):
                c=futs[fut][1]
                try:
                    c,path,vscore,vreason,redesign,final=fut.result(); rendered+=1
                    vis=1 if final>=quality_threshold else 0
                    if vis: visible+=1
                    else: rejected+=1
                    execute('''INSERT OR IGNORE INTO designs(cycle_id,created_at,lane,category,concept_family,title,description,materials,target_weight,region_signal,rationale,pre_score,visual_score,final_score,image_path,visible,fingerprint,status,error)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(
                        cycle_id,now_iso(),c.get('lane'),c.get('category'),c.get('concept_family'),c.get('title'),c.get('description'),c.get('materials'),c.get('target_weight'),c.get('region_signal'),
                        (c.get('score_reason','')+' | Visual: '+vreason),c.get('pre_score'),vscore,final,path,vis,fingerprint(c),'visible' if vis else 'rejected',redesign if not vis else None))
                    log_spend(cycle_id,'image',EST_IMAGE_COST_USD,'configured estimate')
                    update_cycle(cycle_id,rendered=rendered,visible=visible,rejected=rejected,failed=failed,estimated_cost_usd=EST_TEXT_CYCLE_COST_USD+rendered*EST_IMAGE_COST_USD)
                    _log(f'rendered={rendered}, visible={visible}, rejected={rejected}, failed={failed}', cycle_id, stage)
                except Exception as e:
                    failed+=1
                    err=f'{type(e).__name__}: {e}'
                    _log(f'render job failed: {err}', cycle_id, stage)
                    update_cycle(cycle_id,failed=failed,note=f'Last render error: {err}'[:1000])
        update_cycle(cycle_id,status='completed',stage='complete',finished_at=now_iso(),rendered=rendered,visible=visible,rejected=rejected,failed=failed,note='Cycle completed')
        _log(f'cycle completed rendered={rendered}, visible={visible}, rejected={rejected}, failed={failed}', cycle_id, 'complete')
        return cycle_id
    except Exception as e:
        _fail_cycle(cycle_id, stage, e)
        return cycle_id
