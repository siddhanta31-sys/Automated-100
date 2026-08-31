import os
import streamlit as st
from config import *
from db import init_db, query, one, execute, today_spend, get_int_setting, get_bool_setting, set_setting
from safety import system_health
from pipeline import run_cycle

st.set_page_config(page_title='Trend2Sketch Advanced Studio', page_icon='💎', layout='wide')
init_db()

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

st.title('💎 Trend2Sketch Advanced Studio')
st.caption('Autonomous jewellery intelligence • Dynamic South Indian + Diamond discovery • Rank → Render → Visually score → Filter')

with st.expander('🎛️ Live Studio Controls — no redeployment needed', expanded=True):
    c1,c2,c3=st.columns(3)
    new_threshold=c1.slider('Quality acceptance score',75,100,quality_threshold,help='Change this anytime. Designs at or above this final score become accepted in the library.')
    new_cap=c2.slider('Number of designs to generate per cycle',1,100,render_cap,step=1,help='Choose the exact number of jewellery designs the system should attempt to generate in each cycle. Change this anytime without redeploying.')
    new_auto=c3.toggle('Autonomous cycles enabled',value=auto_enabled,help='Turn background scheduled generation on/off without changing Render or GitHub.')
    changed = (new_threshold != quality_threshold) or (new_cap != render_cap) or (new_auto != auto_enabled)
    if changed:
        set_setting('quality_threshold', new_threshold)
        set_setting('render_cap', new_cap)
        set_setting('auto_enabled', '1' if new_auto else '0')
        # Reclassify already-rendered designs immediately. No API call or regeneration required.
        execute('UPDATE designs SET visible=CASE WHEN final_score>=? THEN 1 ELSE 0 END WHERE final_score IS NOT NULL',(new_threshold,))
        st.success('Saved instantly. These settings persist after closing the browser and after normal app restarts.')
        quality_threshold,render_cap,auto_enabled=new_threshold,new_cap,new_auto

    preset_cols=st.columns(3)
    if preset_cols[0].button('🧪 Trial preset: 75 / 10'):
        set_setting('quality_threshold',75); set_setting('render_cap',10); set_setting('auto_enabled','1')
        execute('UPDATE designs SET visible=CASE WHEN final_score>=75 THEN 1 ELSE 0 END WHERE final_score IS NOT NULL')
        st.rerun()
    if preset_cols[1].button('⚖️ Review preset: 85 / 30'):
        set_setting('quality_threshold',85); set_setting('render_cap',30); set_setting('auto_enabled','1')
        execute('UPDATE designs SET visible=CASE WHEN final_score>=85 THEN 1 ELSE 0 END WHERE final_score IS NOT NULL')
        st.rerun()
    if preset_cols[2].button('🏆 Production preset: 95 / 100'):
        set_setting('quality_threshold',95); set_setting('render_cap',100); set_setting('auto_enabled','1')
        execute('UPDATE designs SET visible=CASE WHEN final_score>=95 THEN 1 ELSE 0 END WHERE final_score IS NOT NULL')
        st.rerun()

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
    c[3].metric('Health', 'OK' if h['ok'] else 'GUARD ACTIVE')
    st.write(f'Automatic interval: {AUTO_INTERVAL_MINUTES} min • Research pool: {CONCEPT_POOL_SIZE} • Current render cap: {render_cap} • Pre-render floor: {PRE_RENDER_MIN_SCORE:.0f} • Current acceptance threshold: {quality_threshold} • Autonomous: {"ON" if auto_enabled else "PAUSED"}')

if st.button('Generate one trial cycle now', type='primary'):
    with st.spinner('Running research, concept discovery, scoring and rendering with your current live controls...'):
        cid=run_cycle(manual=True)
    st.success(f'Cycle #{cid} finished/updated.')
    st.rerun()

st.subheader(f'Accepted Design Library — {quality_threshold}+ Final Score')
filters=st.columns(3)
lane=filters[0].selectbox('Lane',['All','Diamond','South Indian Gemstone'])
review_floor=filters[1].slider('Review floor',75,100,quality_threshold,help='This is only a viewing filter; it does not change your saved acceptance score.')
limit=filters[2].selectbox('Show',['30','60','120'],index=0)
params=[review_floor]; where='final_score>=? AND image_path IS NOT NULL'
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
                if st.button('⭐ Favourite',key=f"fav{r['id']}"):
                    execute('UPDATE designs SET favorite=1 WHERE id=?',(r['id'],)); st.toast('Saved as favourite')

st.subheader('Score Calibration Lab')
st.caption('Use this to compare 75–100 rated output side by side before deciding your permanent production threshold. Changing the Review floor costs nothing and requires no regeneration.')
bands=query('''SELECT 
SUM(CASE WHEN final_score>=75 AND final_score<80 THEN 1 ELSE 0 END) AS s75_79,
SUM(CASE WHEN final_score>=80 AND final_score<85 THEN 1 ELSE 0 END) AS s80_84,
SUM(CASE WHEN final_score>=85 AND final_score<90 THEN 1 ELSE 0 END) AS s85_89,
SUM(CASE WHEN final_score>=90 AND final_score<95 THEN 1 ELSE 0 END) AS s90_94,
SUM(CASE WHEN final_score>=95 THEN 1 ELSE 0 END) AS s95_100
FROM designs WHERE image_path IS NOT NULL''')
if bands:
    b=bands[0]; bc=st.columns(5)
    bc[0].metric('75–79',b.get('s75_79') or 0); bc[1].metric('80–84',b.get('s80_84') or 0); bc[2].metric('85–89',b.get('s85_89') or 0); bc[3].metric('90–94',b.get('s90_94') or 0); bc[4].metric('95–100',b.get('s95_100') or 0)

st.subheader('Recent autonomous cycles')
cycles=query('SELECT id,started_at,status,stage,concepts_discovered,candidates_scored,rendered,visible,rejected,failed,estimated_cost_usd,note FROM cycles ORDER BY id DESC LIMIT 12')
st.dataframe(cycles,width='stretch',hide_index=True)

st.caption('Scores are Trend2Sketch internal design-intelligence scores, not guaranteed sales probabilities. Public trend research is used for inspiration; branded products must not be copied.')
