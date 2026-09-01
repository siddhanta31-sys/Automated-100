import os, json
import streamlit as st
from config import *
from db import init_db, query, one, execute, today_spend, get_setting, get_int_setting, get_bool_setting, set_setting, active_cycle, mark_stale_running_cycles, add_feedback, repair_rejection_integrity
from safety import system_health
from pipeline import run_cycle
from intelligence import analyze_reference_image
import re

st.set_page_config(page_title='Trend2Sketch Advanced Studio', page_icon='💎', layout='wide')
init_db()
repaired_rejections=repair_rejection_integrity()
mark_stale_running_cycles(CYCLE_STALE_MINUTES)

if APP_PASSWORD:
    if 'auth' not in st.session_state: st.session_state.auth=False
    if not st.session_state.auth:
        st.title('Trend2Sketch Advanced Studio')
        pwd=st.text_input('Password',type='password')
        if st.button('Open Studio') and pwd==APP_PASSWORD:
            st.session_state.auth=True; st.rerun()
        st.stop()

# Persistent controls — saved in SQLite on the Render disk, so changing them does not require redeployment.
quality_threshold = max(75, min(100, get_int_setting('quality_threshold', DISPLAY_THRESHOLD)))
render_cap = max(1, min(100, get_int_setting('render_cap', MAX_RENDER_PER_CYCLE)))
auto_enabled = get_bool_setting('auto_enabled', True)
speed_mode = get_setting('speed_mode','Balanced') or 'Balanced'
if speed_mode not in ('Fast','Balanced','Deep'): speed_mode='Balanced'
try:
    selected_categories = json.loads(get_setting('selected_categories','[]') or '[]')
    if not isinstance(selected_categories,list): selected_categories=[]
except Exception:
    selected_categories=[]
try:
    selected_lanes = json.loads(get_setting('selected_lanes','[\"Diamond\", \"South Indian Gemstone\"]') or '[]')
    if not isinstance(selected_lanes,list) or not selected_lanes: selected_lanes=['Diamond','South Indian Gemstone']
except Exception:
    selected_lanes=['Diamond','South Indian Gemstone']

st.title('💎 Trend2Sketch Advanced Studio')
st.caption('Product Intelligence • Design DNA → deep R&D → stone/weight engineering → novelty gate → CAD handoff → owner learning')

with st.expander('🎛️ Live Studio Controls — no redeployment needed', expanded=True):
    c1,c2,c3,c4=st.columns(4)
    new_threshold=c1.slider('Quality acceptance score',75,100,quality_threshold,help='Change this anytime. Designs at or above this final score become accepted in the library.')
    new_cap=c2.slider('Number of designs to generate per cycle',1,100,render_cap,step=1,help='Choose the exact number of jewellery designs the system should attempt to generate in each cycle. Change this anytime without redeploying.')
    new_auto=c3.toggle('Autonomous cycles enabled',value=auto_enabled,help='Turn background scheduled generation on/off without changing Render or GitHub.')
    new_speed=c4.selectbox('Worker speed', ['Fast','Balanced','Deep'], index=['Fast','Balanced','Deep'].index(speed_mode), help='Deep is now Design Director R&D mode: three research lenses, synthesis, a larger concept pool, CAD-actionable briefs and stricter product-development scoring.')
    changed = (new_threshold != quality_threshold) or (new_cap != render_cap) or (new_auto != auto_enabled) or (new_speed != speed_mode)
    if changed:
        set_setting('quality_threshold', new_threshold)
        set_setting('render_cap', new_cap)
        set_setting('auto_enabled', '1' if new_auto else '0')
        set_setting('speed_mode', new_speed)
        # Reclassify already-rendered designs immediately. No API call or regeneration required.
        execute('''UPDATE designs SET visible=CASE WHEN final_score>=? AND COALESCE(status,'')<>'owner_rejected' AND NOT EXISTS (SELECT 1 FROM design_feedback f WHERE f.design_id=designs.id AND lower(trim(f.verdict))='reject') THEN 1 ELSE 0 END WHERE final_score IS NOT NULL''',(new_threshold,))
        st.success('Saved instantly. These settings persist after closing the browser and after normal app restarts.')
        quality_threshold,render_cap,auto_enabled,speed_mode=new_threshold,new_cap,new_auto,new_speed

    st.markdown('**Product Development Selector**')
    st.caption('Choose exactly which jewellery product categories the AI should develop. Select several at once. These choices apply to both manual and autonomous cycles.')
    lane_choice=st.multiselect('Design lanes', ['Diamond','South Indian Gemstone'], default=selected_lanes, help='Select one or both lanes.')
    preset_name=st.selectbox('Category quick select', ['Custom selection'] + list(CATEGORY_PRESETS.keys()), index=0)
    default_for_widget = selected_categories
    if preset_name != 'Custom selection':
        default_for_widget = CATEGORY_PRESETS[preset_name]
    category_choice=st.multiselect('Product categories to develop', PRODUCT_CATEGORIES, default=[c for c in default_for_widget if c in PRODUCT_CATEGORIES], help='Leave empty for dynamic auto-discovery across any jewellery category.')
    custom_text=st.text_input('Add custom product categories (optional)', value=get_setting('custom_categories',''), placeholder='Example: Ear cuff, Convertible necklace, Detachable pendant')
    custom_categories=[x.strip() for x in custom_text.split(',') if x.strip()]
    effective_categories=[]
    for c in category_choice + custom_categories:
        if c not in effective_categories: effective_categories.append(c)
    valid_lanes=lane_choice or ['Diamond','South Indian Gemstone']
    selection_changed=(effective_categories != selected_categories) or (valid_lanes != selected_lanes) or (custom_text != get_setting('custom_categories',''))
    if selection_changed:
        set_setting('selected_categories',json.dumps(effective_categories))
        set_setting('selected_lanes',json.dumps(valid_lanes))
        set_setting('custom_categories',custom_text)
        selected_categories,selected_lanes=effective_categories,valid_lanes
        st.success('Product development selection saved. The next cycle will use these categories automatically.')
    if effective_categories:
        st.info('Next cycles will develop only: ' + ' • '.join(effective_categories))
    else:
        st.info('Category mode: AUTO-DISCOVER — the research engine may choose any promising jewellery product category.')

    preset_cols=st.columns(3)
    if preset_cols[0].button('🧪 Trial preset: 75 / 10'):
        set_setting('quality_threshold',75); set_setting('render_cap',10); set_setting('auto_enabled','1')
        execute("""UPDATE designs SET visible=CASE WHEN final_score>=75 AND COALESCE(status,'')<>'owner_rejected' AND NOT EXISTS (SELECT 1 FROM design_feedback f WHERE f.design_id=designs.id AND lower(trim(f.verdict))='reject') THEN 1 ELSE 0 END WHERE final_score IS NOT NULL""")
        st.rerun()
    if preset_cols[1].button('⚖️ Review preset: 85 / 30'):
        set_setting('quality_threshold',85); set_setting('render_cap',30); set_setting('auto_enabled','1')
        execute("""UPDATE designs SET visible=CASE WHEN final_score>=85 AND COALESCE(status,'')<>'owner_rejected' AND NOT EXISTS (SELECT 1 FROM design_feedback f WHERE f.design_id=designs.id AND lower(trim(f.verdict))='reject') THEN 1 ELSE 0 END WHERE final_score IS NOT NULL""")
        st.rerun()
    if preset_cols[2].button('🏆 Production preset: 95 / 100'):
        set_setting('quality_threshold',95); set_setting('render_cap',100); set_setting('auto_enabled','1')
        execute("""UPDATE designs SET visible=CASE WHEN final_score>=95 AND COALESCE(status,'')<>'owner_rejected' AND NOT EXISTS (SELECT 1 FROM design_feedback f WHERE f.design_id=designs.id AND lower(trim(f.verdict))='reject') THEN 1 ELSE 0 END WHERE final_score IS NOT NULL""")
        st.rerun()

# Product Intelligence controls — persistent, no redeployment needed.
st.subheader('🧬 Product Intelligence')
pi1,pi2,pi3=st.columns(3)
target_weight=pi1.text_input('Target gold-weight range',value=get_setting('target_weight_range','Auto'),placeholder='Example: 35–45 g')
stone_strategy=pi2.text_input('Stone strategy',value=get_setting('stone_strategy','Auto'),placeholder='Example: Emerald dominant, ruby accents')
commercial_market=pi3.text_input('Target market / customer',value=get_setting('commercial_market','South India retail'),placeholder='Example: Hyderabad bridal retailers')
novelty_gate=st.slider('Novelty / repetition gate',35,95,get_int_setting('novelty_gate',72),help='Higher = stricter rejection of concepts similar to previous Trend2Sketch designs.')
if (target_weight!=get_setting('target_weight_range','Auto') or stone_strategy!=get_setting('stone_strategy','Auto') or commercial_market!=get_setting('commercial_market','South India retail') or novelty_gate!=get_int_setting('novelty_gate',72)):
    set_setting('target_weight_range',target_weight); set_setting('stone_strategy',stone_strategy); set_setting('commercial_market',commercial_market); set_setting('novelty_gate',novelty_gate)
    st.success('Product engineering targets saved for the next cycle.')

with st.expander('⭐ My Design DNA — gold-standard learning library',expanded=False):
    st.caption('Upload designs you consider excellent. Trend2Sketch automatically analyzes the image itself plus your note, learns the abstract design language, and never asks the model to copy the exact piece.')
    existing_profiles=[r['profile_name'] for r in query("SELECT DISTINCT COALESCE(profile_name,'General') AS profile_name FROM design_references WHERE active=1") if r.get('profile_name')]
    default_profiles=['General','South Indian Bridal','Lightweight South Indian','Diamond Everyday','Diamond Bridal']
    profiles=[]
    for x in default_profiles+existing_profiles:
        if x not in profiles: profiles.append(x)
    profile_name=st.selectbox('Design DNA profile',profiles+['+ New profile'])
    if profile_name=='+ New profile':
        profile_name=st.text_input('New profile name',placeholder='Example: Hyderabad Emerald Bridal') or 'General'
    ref_file=st.file_uploader('Add reference design',type=['png','jpg','jpeg','webp'])
    ref_note=st.text_area('What should the system learn from this design?',placeholder='Optional — image analysis is automatic. Example: strong emerald hierarchy, compact peacock rhythm, commercial bridal proportion')
    if st.button('Analyze & save to Design DNA',disabled=ref_file is None):
        ref_dir=os.path.join(DATA_DIR,'references'); os.makedirs(ref_dir,exist_ok=True)
        safe=re.sub(r'[^A-Za-z0-9._-]+','_',ref_file.name); path=os.path.join(ref_dir,f'{int(__import__("time").time())}_{safe}')
        with open(path,'wb') as f: f.write(ref_file.getbuffer())
        rid=execute('INSERT INTO design_references(created_at,name,image_path,note,active,profile_name,analysis_status) VALUES(?,?,?,?,1,?,?)',(__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),ref_file.name,path,ref_note,profile_name,'analyzing')).lastrowid
        try:
            with st.spinner('Analyzing silhouette, motifs, stone hierarchy, settings, weight philosophy and manufacturability…'):
                dna=analyze_reference_image(path,ref_note,profile_name)
            execute('UPDATE design_references SET dna_json=?, analysis_status=? WHERE id=?',(json.dumps(dna,ensure_ascii=False),'ready',rid))
            st.success('Design learned successfully. Its Design DNA will influence future Deep cycles.')
        except Exception as e:
            execute('UPDATE design_references SET analysis_status=? WHERE id=?',('analysis_failed',rid))
            st.warning(f'Reference saved safely, but automatic analysis could not finish: {type(e).__name__}. You can keep working; your note will still be used.')
    refs=query('SELECT * FROM design_references WHERE active=1 ORDER BY id DESC LIMIT 20')
    if refs:
        rc=st.columns(4)
        for i,r in enumerate(refs):
            with rc[i%4]:
                if r.get('image_path') and os.path.exists(r['image_path']): st.image(r['image_path'],width='stretch')
                st.caption(f"{r.get('profile_name') or 'General'} • {r.get('analysis_status') or 'pending'}")
                if r.get('dna_json'):
                    try:
                        dna=json.loads(r['dna_json']); st.caption('Learned: '+str(dna.get('generation_directives') or dna.get('distinctive_traits') or '')[:220])
                    except Exception: pass
                elif r.get('note'): st.caption((r.get('note') or '')[:180])
                if st.button('Remove',key=f'ref_remove_{r["id"]}'):
                    execute('UPDATE design_references SET active=0 WHERE id=?',(r['id'],)); st.rerun()

latest=one('SELECT * FROM cycles ORDER BY id DESC LIMIT 1') or {}
h=system_health(); spend=today_spend()

if latest.get('status') == 'failed':
    st.error(f"Latest cycle failed at stage: {latest.get('stage','unknown')}")
    if latest.get('note'):
        with st.expander('Show exact failure details', expanded=True):
            st.code(latest.get('note',''), language='text')

cols=st.columns(7)
cols[0].metric('Latest cycle', latest.get('id','—'))
cols[1].metric('Stage', latest.get('stage','idle'))
cols[2].metric('Concepts', latest.get('concepts_discovered',0))
cols[3].metric('Rendered', latest.get('rendered',0))
cols[4].metric(f'{quality_threshold}+ accepted', latest.get('visible',0))
cols[5].metric('Render cap', render_cap)
cols[6].metric('Est. spend today', f'${spend:.2f} / ${DAILY_API_BUDGET_USD:.2f}')

with st.expander('System health', expanded=False):
    c=st.columns(4)
    c[0].metric('RAM used', f"{h['memory_percent']:.1f}%")
    c[1].metric('RAM available', f"{h['memory_available_gb']:.1f} GB")
    c[2].metric('Disk free', f"{h['disk_free_gb']:.1f} GB")
    active_now=active_cycle()
    health_label='WORKING' if active_now else ('HEALTHY' if h['ok'] else 'ATTENTION REQUIRED')
    c[3].metric('Health', health_label)
    st.write(f'Single-cycle lock: ON • Self-restarting worker: ON • Heartbeat recovery: ON • Checkpoints: ON • Parallel pipeline: ON • Research cache: ON • Auto retry: ON • API timeout: {API_TIMEOUT_SECONDS:.0f}s')
    st.write(f'Automatic interval: {AUTO_INTERVAL_MINUTES} min • Worker speed: {speed_mode} • Adaptive concept pool: ON • Current render cap: {render_cap} • Pre-render floor: {PRE_RENDER_MIN_SCORE:.0f} • Acceptance threshold: {quality_threshold} • Autonomous: {"ON" if auto_enabled else "PAUSED"}')
    st.write('Active lanes: ' + ', '.join(selected_lanes) + ' • Categories: ' + (', '.join(selected_categories) if selected_categories else 'AUTO-DISCOVER'))

active = active_cycle()
if active:
    st.info(f"🟢 System is already working on cycle #{active.get('id')} — stage: {active.get('stage','working')}. A second cycle will not be started.")
    if active.get('stage') == 'rendering':
        note = active.get('note') or ''
        m = re.search(r'rendering\s+(\d+)/(\d+)', note, re.I)
        if m:
            done,total = int(m.group(1)), max(1,int(m.group(2)))
            st.progress(min(1.0, done/total), text=f'🎨 Rendering progress: {done}/{total}')
            st.caption(note)
        else:
            st.progress(0.0, text='🎨 Rendering started…')
            st.caption(note or 'Waiting for first rendered design.')

if st.button('Generate one trial cycle now', type='primary', disabled=bool(active)):
    with st.spinner('Running one protected cycle. Automatic retries and single-cycle lock are active...'):
        cid=run_cycle(manual=True)
    if cid:
        st.success(f'Cycle #{cid} finished/updated.')
    else:
        st.info('No new cycle was started because another cycle was already active.')
    st.rerun()

if repaired_rejections:
    st.caption(f'🛡️ Library self-audit repaired {repaired_rejections} previously rejected design(s) and kept them hidden.')

st.subheader(f'Accepted Design Library — {quality_threshold}+ Final Score')
filters=st.columns(3)
lane=filters[0].selectbox('Lane',['All','Diamond','South Indian Gemstone'])
review_floor=filters[1].slider('Review floor',75,100,quality_threshold,help='This is only a viewing filter; it does not change your saved acceptance score.')
limit=filters[2].selectbox('Show',['30','60','120'],index=0)
params=[review_floor]; where="final_score>=? AND image_path IS NOT NULL AND COALESCE(visible,0)=1 AND COALESCE(status,'')<>'owner_rejected' AND NOT EXISTS (SELECT 1 FROM design_feedback f WHERE f.design_id=designs.id AND lower(trim(f.verdict))='reject')"
if lane!='All': where+=' AND lane=?'; params.append(lane)
rows=query(f'SELECT * FROM designs WHERE {where} ORDER BY final_score DESC, id DESC LIMIT ?',tuple(params+[int(limit)]))
if not rows:
    st.info('No rendered designs are available at this review score yet. For first testing, use the Trial preset (75 / 10) and run one trial cycle.')
else:
    for i in range(0,len(rows),3):
        cs=st.columns(3)
        for j,r in enumerate(rows[i:i+3]):
            with cs[j]:
                if r.get('image_path') and os.path.exists(r['image_path']):
                    st.image(r['image_path'],width='stretch')
                accepted=float(r.get('final_score') or 0)>=quality_threshold
                badge='✅ ACCEPTED' if accepted else '🧪 REVIEW ONLY'
                st.markdown(f"**{r.get('title') or 'Untitled'}** — **{r.get('final_score',0):.0f}/100**  \n{badge}")
                st.caption(f"{r.get('lane','')} • {r.get('category','')} • {r.get('concept_family','')}")
                st.write(r.get('description',''))
                st.caption(f"Concept score {float(r.get('pre_score') or 0):.0f} • Visual score {float(r.get('visual_score') or 0):.0f}")
                if r.get('cad_brief'):
                    with st.expander('📐 CAD handoff sheet'):
                        try: brief=json.loads(r.get('cad_brief') or '{}')
                        except Exception: brief={}
                        st.write(f"**Target weight:** {r.get('target_weight') or '—'}")
                        for label,key in [('Dimensions','dimensions'),('Stone hierarchy','stone_hierarchy'),('Stone shapes / sizes','stone_shapes_sizes'),('Setting strategy','setting_strategy'),('Construction','construction'),('Articulation','articulation'),('Comfort','comfort_notes'),('Lightweighting','lightweighting_strategy'),('Manufacturability','manufacturability_rationale')]:
                            if brief.get(key): st.write(f"**{label}:** {brief.get(key)}")

                fb1,fb2,fb3=st.columns(3)
                if fb1.button('❤️ Excellent',key=f"excellent{r['id']}"):
                    execute('UPDATE designs SET favorite=1 WHERE id=?',(r['id'],)); add_feedback(r['id'],'excellent','Approved as gold-standard direction'); st.toast('Excellent — this direction will influence future Deep research.')
                if fb2.button('✓ Usable',key=f"usable{r['id']}"):
                    add_feedback(r['id'],'usable','Commercially usable'); st.toast('Usable feedback saved.')
                if fb3.button('✕ Reject',key=f"reject{r['id']}"):
                    st.session_state[f"reject_open_{r['id']}"]=True
                if st.session_state.get(f"reject_open_{r['id']}",False):
                    reason=st.selectbox('Why reject?', ['Too generic','Not South Indian enough','Poor stone dominance','Bad proportions','Too heavy','Too light/plain','Not manufacturable','Too repetitive','Not commercial','Wrong category','Other'],key=f"reason{r['id']}")
                    note=st.text_input('Optional note',key=f"note{r['id']}")
                    if st.button('Save rejection',key=f"save_reject{r['id']}"):
                        add_feedback(r['id'],'reject',reason,note); st.session_state[f"reject_open_{r['id']}"]=False; st.toast('Rejected permanently: removed from every visible library, retained only for negative learning.'); st.rerun()

st.subheader('Score Calibration Lab')
st.caption('Use this to compare 75–100 rated output side by side before deciding your permanent production threshold. Changing the Review floor costs nothing and requires no regeneration.')
bands=query('''SELECT 
SUM(CASE WHEN final_score>=75 AND final_score<80 THEN 1 ELSE 0 END) AS s75_79,
SUM(CASE WHEN final_score>=80 AND final_score<85 THEN 1 ELSE 0 END) AS s80_84,
SUM(CASE WHEN final_score>=85 AND final_score<90 THEN 1 ELSE 0 END) AS s85_89,
SUM(CASE WHEN final_score>=90 AND final_score<95 THEN 1 ELSE 0 END) AS s90_94,
SUM(CASE WHEN final_score>=95 THEN 1 ELSE 0 END) AS s95_100
FROM designs WHERE image_path IS NOT NULL AND COALESCE(visible,0)=1 AND COALESCE(status,'')<>'owner_rejected' AND NOT EXISTS (SELECT 1 FROM design_feedback f WHERE f.design_id=designs.id AND lower(trim(f.verdict))='reject')''')
if bands:
    b=bands[0]; bc=st.columns(5)
    bc[0].metric('75–79',b.get('s75_79') or 0); bc[1].metric('80–84',b.get('s80_84') or 0); bc[2].metric('85–89',b.get('s85_89') or 0); bc[3].metric('90–94',b.get('s90_94') or 0); bc[4].metric('95–100',b.get('s95_100') or 0)

st.subheader('Recent autonomous cycles')
cycles=query('SELECT id,started_at,status,stage,concepts_discovered,candidates_scored,rendered,visible,rejected,failed,estimated_cost_usd,note FROM cycles ORDER BY id DESC LIMIT 12')
st.dataframe(cycles,width='stretch',hide_index=True)

st.caption('Foolproof Design OS: Design DNA image learning + multi-agent Deep R&D + CAD-actionable briefs + owner feedback + crash recovery. Scores are internal design-intelligence scores, not guaranteed sales probabilities. Public trend research is used for inspiration; branded products must not be copied.')
