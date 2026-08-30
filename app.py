
import streamlit as st
import os, sqlite3, json, hashlib
from pathlib import Path
from autonomous_core import DB_PATH, DESIGN_MATRIX, create_batch

st.set_page_config(page_title="Trend2Sketch Auto100",page_icon="💎",layout="wide",initial_sidebar_state="collapsed")

st.markdown("""
<style>
.block-container{padding-top:1rem;max-width:1550px}
[data-testid="stMetric"]{background:#111923;border:1px solid #293442;padding:14px;border-radius:16px}
div.stButton>button,.stDownloadButton button{min-height:52px;border-radius:14px;font-weight:750}
.card{background:#111923;border:1px solid #293442;border-radius:18px;padding:14px}
.gold{color:#d3ad59;font-weight:800}.muted{color:#9aa6b5}
@media(max-width:900px){
 .block-container{padding:.7rem .8rem 5rem}
 [data-testid="column"]{min-width:100%!important;width:100%!important;flex:1 1 100%!important}
 div.stButton>button,.stDownloadButton button{width:100%}
}
</style>
""",unsafe_allow_html=True)

def login():
    pw=os.getenv("APP_PASSWORD","").strip()
    if not pw:return
    if st.session_state.get("ok"):return
    st.title("💎 Trend2Sketch Auto100")
    with st.form("login"):
        v=st.text_input("Private workspace password",type="password")
        if st.form_submit_button("Open Studio",use_container_width=True):
            if hashlib.sha256(v.encode()).hexdigest()==hashlib.sha256(pw.encode()).hexdigest():
                st.session_state.ok=True;st.rerun()
            st.error("Incorrect password")
    st.stop()
login()

def db():
    con=sqlite3.connect(DB_PATH,timeout=30);con.row_factory=sqlite3.Row;return con

st.title("💎 Trend2Sketch Auto100")
st.caption("Autonomous commercial design intelligence • 100 sketches every 30 minutes • Diamond + South Indian gemstone jewellery")

tabs=st.tabs(["Live Dashboard","Latest 100","Design Library","Coverage","Settings"])

with tabs[0]:
    con=db()
    last=con.execute("SELECT * FROM batches ORDER BY id DESC LIMIT 1").fetchone()
    total=con.execute("SELECT COUNT(*) n FROM concepts").fetchone()["n"]
    fav=con.execute("SELECT COUNT(*) n FROM concepts WHERE favorite=1").fetchone()["n"]
    con.close()
    a,b,c,d=st.columns(4)
    a.metric("Generation cadence",os.getenv("AUTO_INTERVAL_MINUTES","30")+" min")
    b.metric("Designs per batch","100")
    c.metric("Total library",total)
    d.metric("Favourites",fav)
    if last:
        st.markdown("### Latest autonomous batch")
        x1,x2,x3,x4=st.columns(4)
        x1.metric("Batch",f"#{last['id']}")
        x2.metric("Status",last["status"])
        x3.metric("Generated",last["generated_count"])
        x4.metric("Failed",last["failed_count"])
        st.caption(f"Started {last['started_at']} • Finished {last['finished_at'] or 'running'} • {last['email_status'] or ''}")
    else:
        st.info("The background engine will create its first batch automatically after deployment.")

    st.warning("“Commercial score” estimates market potential from public catalogue signals. It is not a guarantee that a design will sell.")

    if st.button("Generate an extra 100 now",type="primary",use_container_width=True):
        with st.spinner("Running a full 100-design batch. This can take several minutes…"):
            try:
                bid,res,err,email=create_batch()
                st.success(f"Batch #{bid}: {len(res)} generated, {len(err)} failed. {email}")
                st.rerun()
            except Exception as e:
                st.error(str(e))

with tabs[1]:
    con=db()
    batch=con.execute("SELECT id FROM batches ORDER BY id DESC LIMIT 1").fetchone()
    if not batch:
        st.info("No batch yet.")
    else:
        rows=con.execute("SELECT * FROM concepts WHERE batch_id=? ORDER BY id",(batch["id"],)).fetchall()
        st.markdown(f"### Batch #{batch['id']} — {len(rows)} designs")
        cols=st.columns(3)
        for i,r in enumerate(rows):
            with cols[i%3]:
                p=Path(r["image_path"])
                if p.exists():st.image(str(p),use_container_width=True)
                st.markdown(f"**{r['title']}** · {r['commercial_score']}/100")
                st.caption(f"{r['lane']} • {r['category']} • {r['weight_band']} • {r['trend_name']}")
    con.close()

with tabs[2]:
    con=db()
    lanes=["All","Diamond","South Indian Gemstone"]
    lane=st.selectbox("Lane",lanes)
    cat=st.text_input("Filter category/trend","")
    q="SELECT * FROM concepts"
    params=[]
    cond=[]
    if lane!="All":cond.append("lane=?");params.append(lane)
    if cat.strip():cond.append("(category LIKE ? OR trend_name LIKE ?)");params += [f"%{cat.strip()}%",f"%{cat.strip()}%"]
    if cond:q+=" WHERE "+" AND ".join(cond)
    q+=" ORDER BY id DESC LIMIT 300"
    rows=con.execute(q,params).fetchall()
    cols=st.columns(3)
    for i,r in enumerate(rows):
        with cols[i%3]:
            p=Path(r["image_path"])
            if p.exists():st.image(str(p),use_container_width=True)
            st.markdown(f"**{r['title']}** · {r['commercial_score']}/100")
            st.caption(f"{r['lane']} • {r['category']} • {r['weight_band']}")
            fav=bool(r["favorite"])
            if st.button("✓ Favourite" if fav else "♡ Favourite",key=f"fav{r['id']}"):
                con.execute("UPDATE concepts SET favorite=? WHERE id=?",(0 if fav else 1,r["id"]))
                con.commit();st.rerun()
    con.close()

with tabs[3]:
    st.markdown("### Exact 100-design coverage matrix")
    total=0
    for lane,cats in DESIGN_MATRIX.items():
        st.markdown(f"#### {lane}")
        for cat,bands in cats.items():
            st.write(f"**{cat}:** "+", ".join(bands))
            total+=len(bands)
    st.success(f"Total slots per autonomous batch: {total}")

with tabs[4]:
    st.markdown("### Autonomous engine")
    st.code("""AUTO_INTERVAL_MINUTES=30
AUTO_RUN_ON_START=true
GENERATION_CONCURRENCY=1
GENERATION_MAX_ATTEMPTS=3
OPENAI_TEXT_MODEL=gpt-5.6-luna
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_QUALITY=low""")
    st.markdown("### Email delivery")
    st.write("The email contains a digest of the strongest concepts and a link to all 100 designs in this app.")
    st.code("""SEND_TO_EMAIL=you@example.com
RESEND_API_KEY=re_...
SEND_FROM_EMAIL=Trend2Sketch <designs@your-verified-domain.com>
APP_PUBLIC_URL=https://your-app.onrender.com""")
    st.info("100 images as direct email attachments is usually too large. The app keeps all 100 in the library and emails the batch summary + app link.")
