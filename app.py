import os, time
import streamlit as st
from PIL import Image
from config import *
from db import init_db, query, one, execute, today_spend
from safety import system_health
from pipeline import run_cycle

st.set_page_config(page_title='Trend2Sketch Studio', page_icon='💎', layout='wide')
init_db()

if APP_PASSWORD:
    if 'auth' not in st.session_state: st.session_state.auth=False
    if not st.session_state.auth:
        st.title('Trend2Sketch Studio')
        pwd=st.text_input('Password',type='password')
        if st.button('Open Studio') and pwd==APP_PASSWORD:
            st.session_state.auth=True; st.rerun()
        st.stop()

st.title('💎 Trend2Sketch Studio')
st.caption('Autonomous jewellery intelligence • Rank first, render best concepts • Show only 95+')

latest=one('SELECT * FROM cycles ORDER BY id DESC LIMIT 1') or {}
h=system_health(); spend=today_spend()

if latest.get('status') == 'failed':
    st.error(f"Latest cycle failed at stage: {latest.get('stage','unknown')}")
    if latest.get('note'):
        with st.expander('Show exact failure details', expanded=True):
            st.code(latest.get('note',''), language='text')
cols=st.columns(6)
cols[0].metric('Latest cycle', latest.get('id','—'))
cols[1].metric('Stage', latest.get('stage','idle'))
cols[2].metric('Concepts', latest.get('concepts_discovered',0))
cols[3].metric('Rendered', latest.get('rendered',0))
cols[4].metric('95+ visible', latest.get('visible',0))
cols[5].metric('Est. spend today', f'${spend:.2f} / ${DAILY_API_BUDGET_USD:.2f}')

with st.expander('System health', expanded=False):
    c=st.columns(4)
    c[0].metric('RAM used', f"{h['memory_percent']:.1f}%")
    c[1].metric('RAM available', f"{h['memory_available_gb']:.1f} GB")
    c[2].metric('Disk free', f"{h['disk_free_gb']:.1f} GB")
    c[3].metric('Health', 'OK' if h['ok'] else 'GUARD ACTIVE')
    st.write(f'Automatic interval: {AUTO_INTERVAL_MINUTES} min • Concept pool: {CONCEPT_POOL_SIZE} • Top renders/cycle: {MAX_RENDER_PER_CYCLE} • Pre-render floor: {PRE_RENDER_MIN_SCORE:.0f} • Visibility threshold: {DISPLAY_THRESHOLD}')

if st.button('Generate one extra cycle now', type='primary'):
    with st.spinner('Running research, concept discovery, scoring and rendering...'):
        cid=run_cycle()
    st.success(f'Cycle #{cid} finished/updated.')
    st.rerun()

st.subheader('95+ Design Library')
filters=st.columns(3)
lane=filters[0].selectbox('Lane',['All','Diamond','South Indian Gemstone'])
min_score=filters[1].slider('Minimum score',95,100,95)
limit=filters[2].selectbox('Show',['30','60','120'],index=0)
params=[min_score]; where='visible=1 AND final_score>=?'
if lane!='All': where+=' AND lane=?'; params.append(lane)
rows=query(f'SELECT * FROM designs WHERE {where} ORDER BY final_score DESC, id DESC LIMIT ?',tuple(params+[int(limit)]))
if not rows:
    st.info('No finished designs have passed the 95+ gate yet. The worker now renders the highest-ranked novel concepts first, then applies the 95+ final-design gate.')
else:
    for i in range(0,len(rows),3):
        cs=st.columns(3)
        for j,r in enumerate(rows[i:i+3]):
            with cs[j]:
                if r.get('image_path') and os.path.exists(r['image_path']):
                    st.image(r['image_path'],width='stretch')
                st.markdown(f"**{r.get('title') or 'Untitled'}** — **{r.get('final_score',0):.0f}/100**")
                st.caption(f"{r.get('lane','')} • {r.get('category','')} • {r.get('concept_family','')}")
                st.write(r.get('description',''))
                if st.button('⭐ Favourite',key=f"fav{r['id']}"):
                    execute('UPDATE designs SET favorite=1 WHERE id=?',(r['id'],)); st.toast('Saved as favourite')

st.subheader('Recent autonomous cycles')
cycles=query('SELECT id,started_at,status,stage,concepts_discovered,candidates_scored,rendered,visible,rejected,failed,estimated_cost_usd,note FROM cycles ORDER BY id DESC LIMIT 12')
st.dataframe(cycles,width='stretch',hide_index=True)

st.caption('Scores are Trend2Sketch internal design-intelligence scores, not guaranteed sales probabilities. Public trend research is used for inspiration; branded products must not be copied.')
