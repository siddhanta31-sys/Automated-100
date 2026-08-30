
import os, json, re, sqlite3, base64, random, time, requests, hashlib
from pathlib import Path
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed

APP_DIR = Path(__file__).parent
DATA_DIR = Path(os.getenv("TREND2SKETCH_DATA_DIR", str(APP_DIR / "data")))
CONCEPT_DIR = DATA_DIR / "concepts"
DB_PATH = DATA_DIR / "trend2sketch.db"
CONCEPT_DIR.mkdir(parents=True, exist_ok=True)

BRANDS = [
    {"name":"Tanishq","domain":"tanishq.co.in"},
    {"name":"Malabar Gold & Diamonds","domain":"malabargoldanddiamonds.com"},
    {"name":"Kalyan Jewellers","domain":"kalyanjewellers.net"},
    {"name":"Joyalukkas","domain":"joyalukkas.in"},
]

# Exactly 100 design slots: 50 Diamond + 50 South Indian gemstone. Each category gets five weight bands.
DESIGN_MATRIX = {
    "Diamond": {
        "Bangle": ["8-12g","12-18g","18-25g","25-35g","35-50g"],
        "Earring": ["2-4g","4-7g","7-10g","10-15g","15-22g"],
        "Jhumka": ["4-7g","7-10g","10-15g","15-22g","22-30g"],
        "Chandbali": ["5-8g","8-12g","12-18g","18-25g","25-35g"],
        "Ring": ["2-4g","4-6g","6-8g","8-12g","12-18g"],
        "Short Necklace": ["10-16g","16-22g","22-30g","30-40g","40-55g"],
        "Long Necklace": ["18-25g","25-35g","35-50g","50-70g","70-90g"],
        "Haram": ["25-35g","35-50g","50-70g","70-95g","95-125g"],
        "Bridal Set": ["25-40g","40-60g","60-85g","85-120g","120-160g"],
        "Vaddanam": ["35-50g","50-70g","70-100g","100-140g","140-190g"],
    },
    "South Indian Gemstone": {
        "Bangle": ["12-18g","18-25g","25-35g","35-50g","50-70g"],
        "Earring": ["3-6g","6-10g","10-15g","15-22g","22-30g"],
        "Jhumka": ["5-9g","9-14g","14-20g","20-30g","30-42g"],
        "Chandbali": ["6-10g","10-15g","15-22g","22-32g","32-45g"],
        "Ring": ["3-5g","5-8g","8-12g","12-18g","18-25g"],
        "Short Necklace": ["18-28g","28-40g","40-55g","55-75g","75-100g"],
        "Long Necklace": ["30-45g","45-65g","65-90g","90-120g","120-160g"],
        "Haram": ["40-60g","60-80g","80-110g","110-150g","150-200g"],
        "Bridal Set": ["45-70g","70-100g","100-140g","140-190g","190-260g"],
        "Vaddanam": ["50-75g","75-100g","100-150g","150-200g","200-275g"],
    }
}

def get_db():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con=get_db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS batches(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at TEXT NOT NULL,
      started_at TEXT,
      finished_at TEXT,
      status TEXT NOT NULL,
      trend_payload TEXT,
      generated_count INTEGER DEFAULT 0,
      failed_count INTEGER DEFAULT 0,
      email_status TEXT,
      note TEXT
    );
    CREATE TABLE IF NOT EXISTS concepts(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      batch_id INTEGER,
      created_at TEXT NOT NULL,
      lane TEXT,
      category TEXT,
      weight_band TEXT,
      trend_name TEXT,
      title TEXT,
      commercial_score INTEGER,
      image_path TEXT,
      prompt TEXT,
      source TEXT,
      favorite INTEGER DEFAULT 0
    );
    """)
    # tolerate older DBs
    for stmt in [
        "ALTER TABLE concepts ADD COLUMN batch_id INTEGER",
        "ALTER TABLE concepts ADD COLUMN category TEXT",
        "ALTER TABLE concepts ADD COLUMN weight_band TEXT",
        "ALTER TABLE concepts ADD COLUMN commercial_score INTEGER",
    ]:
        try: con.execute(stmt)
        except Exception: pass
    con.commit(); con.close()
init_db()

def openai_client():
    from openai import OpenAI
    k=os.getenv("OPENAI_API_KEY","").strip()
    if not k: raise RuntimeError("OPENAI_API_KEY is missing.")
    return OpenAI(api_key=k)

def safe_json(text):
    if not text: return None
    t=re.sub(r"^```json\s*|^```\s*|\s*```$","",text.strip())
    try:return json.loads(t)
    except Exception:
        m=re.search(r"\{.*\}",t,re.S)
        if not m:return None
        try:return json.loads(m.group(0))
        except Exception:return None

def trend_research():
    c=openai_client()
    model=os.getenv("OPENAI_TEXT_MODEL","gpt-5.6-luna")
    domains=[x["domain"] for x in BRANDS]
    prompt=f"""
You are the autonomous commercial jewellery intelligence engine for Trend2Sketch.
Today is {date.today().isoformat()}.

Research CURRENT public catalogue pages on:
{', '.join(b['name'] for b in BRANDS)}.

The app's only main lanes are:
1) Diamond jewellery: rings, earrings, pendants, bracelets, bangles, necklaces/chokers.
2) South Indian gemstone jewellery: ruby, emerald, pearls, uncut/polki accents, temple/nakshi/kemp-inspired
   chokers, long harams, jhumkas and vaddanam.

Goal: identify cross-brand signals that are MOST LIKELY TO HAVE COMMERCIAL APPEAL.
Do NOT claim guaranteed sales. "Commercial score" means inferred potential from:
- repeated visibility across multiple brands
- new arrival/latest/featured/bestseller/wedding positioning where visible
- wearable/affordable weight appearance
- broad Indian market appeal
- manufacturability
- distinctive but not overly experimental styling

Do not copy a product. Extract trend DNA.

Return ONLY JSON:
{{
 "confidence":0-100,
 "diamond_trends":[
  {{"name":"...","commercial_score":0-100,"why":"...","silhouette":"...","motifs":["..."],
    "stone_direction":"...","construction":"...","weight_strategy":"...","source_brands":["..."]}}
 ],
 "south_trends":[
  {{"name":"...","commercial_score":0-100,"why":"...","silhouette":"...","motifs":["..."],
    "stone_direction":"...","construction":"...","weight_strategy":"...","source_brands":["..."]}}
 ],
 "market_notes":["..."],
 "avoid":["..."]
}}
Return at least 10 trends in each lane so the 100-design matrix can vary concepts.
"""
    try:
        r=c.responses.create(model=model,tools=[{"type":"web_search","filters":{"allowed_domains":domains}}],input=prompt)
    except Exception:
        r=c.responses.create(model=model,tools=[{"type":"web_search"}],input=prompt+"\nUse only these domains: "+", ".join(domains))
    data=safe_json(r.output_text)
    if not data: raise RuntimeError("Trend research returned invalid JSON.")
    return data, model

def build_slots():
    slots=[]
    for lane,cats in DESIGN_MATRIX.items():
        for cat,bands in cats.items():
            for band in bands:
                slots.append({"lane":lane,"category":cat,"weight_band":band})
    assert len(slots)==100
    return slots

def choose_trend(trends, index):
    if not trends: return {}
    # Bias toward high score, while rotating enough to keep collections varied.
    ordered=sorted(trends,key=lambda t:int(t.get("commercial_score",70)),reverse=True)
    top=ordered[:min(6,len(ordered))]
    return top[index % len(top)]

def concept_prompt(slot, trend, idx):
    is_diamond=slot["lane"]=="Diamond"
    material_rules = """
Diamond lane: elegant diamond-led Indian luxury. Use crisp stone layouts and high perceived value.
Possible visual vocabulary: round, pear, marquise, emerald-cut, baguette-like geometries, floral clusters,
line/tennis constructions, negative space, detachable modules. Do not imply diamond origin or certification.
""" if is_diamond else """
South Indian gemstone lane: strong South Indian identity using ruby/emerald/pearl/uncut gemstone colour logic,
temple/nakshi/kemp-influenced motifs, lotus, paisley/mango, peacock, floral, yali-inspired rhythm and pearl movement
where appropriate. Preserve gold visibility and broad visual impact while controlling unnecessary metal mass.
"""
    return f"""
Create an ORIGINAL commercially-oriented jewellery DESIGN SKETCH.

Batch slot {idx}/100
Lane: {slot['lane']}
Category: {slot['category']}
Target finished gold weight band: {slot['weight_band']}

Current cross-brand trend DNA:
Trend: {trend.get('name')}
Commercial-potential score: {trend.get('commercial_score')}
Why: {trend.get('why')}
Silhouette: {trend.get('silhouette')}
Motifs: {', '.join(trend.get('motifs',[]))}
Stone direction: {trend.get('stone_direction')}
Construction: {trend.get('construction')}
Weight strategy: {trend.get('weight_strategy')}

{material_rules}

MANDATORY:
- Professional black pencil/fine-ink jewellery designer sketch on warm white paper.
- Front elevation; clear stone placement and manufacturing logic.
- Original composition based only on aggregated trend DNA.
- Do not copy or closely imitate any Tanishq, Malabar, Kalyan, Joyalukkas or other branded product.
- Respect the stated weight band; design visual spread, gauge, negative space, modularity and backing accordingly.
- Wearable and manufacturable, not fantasy jewellery.
- No person, hand, mannequin, logo, brand name, watermark or text inside the artwork.
- Make this concept visibly different from other batch slots.
"""

def generate_one(batch_id, idx, slot, trend):
    c=openai_client()
    model=os.getenv("OPENAI_IMAGE_MODEL","gpt-image-2")
    quality=os.getenv("OPENAI_IMAGE_QUALITY","low")
    prompt=concept_prompt(slot,trend,idx)
    r=c.images.generate(model=model,prompt=prompt,size="1024x1024",quality=quality)
    item=r.data[0]
    if getattr(item,"b64_json",None):
        raw=base64.b64decode(item.b64_json)
    elif getattr(item,"url",None):
        rr=requests.get(item.url,timeout=120); rr.raise_for_status(); raw=rr.content
    else:
        raise RuntimeError("No image returned.")
    fn=f"batch{batch_id:06d}_{idx:02d}_{slot['lane'].replace(' ','_')}_{slot['category'].replace('/','-').replace(' ','_')}.png"
    path=CONCEPT_DIR/fn
    path.write_bytes(raw)
    score=max(50,min(99,int(trend.get("commercial_score",75))+random.randint(-3,3)))
    con=get_db()
    con.execute("""INSERT INTO concepts(batch_id,created_at,lane,category,weight_band,trend_name,title,
                 commercial_score,image_path,prompt,source)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (batch_id,datetime.now().isoformat(timespec="seconds"),slot["lane"],slot["category"],
                 slot["weight_band"],trend.get("name","Trend-led"),f"Design {idx:02d}",score,str(path),prompt,model))
    con.commit();con.close()
    return {"idx":idx,"path":str(path),"score":score,"slot":slot,"trend":trend.get("name","")}

def app_public_url():
    return os.getenv("APP_PUBLIC_URL","").strip()

def send_email_digest(batch_id, results, trend_data):
    to=os.getenv("SEND_TO_EMAIL","").strip()
    key=os.getenv("RESEND_API_KEY","").strip()
    sender=os.getenv("SEND_FROM_EMAIL","").strip()
    if not (to and key and sender):
        return "Email not configured"
    top=sorted(results,key=lambda x:x["score"],reverse=True)[:12]
    rows="".join(
        f"<tr><td>{x['idx']:02d}</td><td>{x['slot']['lane']}</td><td>{x['slot']['category']}</td>"
        f"<td>{x['slot']['weight_band']}</td><td>{x['trend']}</td><td>{x['score']}/100</td></tr>"
        for x in top
    )
    link=app_public_url()
    html=f"""
    <h2>Trend2Sketch Batch #{batch_id}</h2>
    <p><b>{len(results)} new jewellery concepts</b> have been generated.</p>
    <p>The batch covers 50 Diamond and 50 South Indian gemstone category/weight slots.</p>
    <p>Top commercially-scored concepts:</p>
    <table border="1" cellspacing="0" cellpadding="6">
    <tr><th>#</th><th>Lane</th><th>Category</th><th>Weight</th><th>Trend</th><th>Score</th></tr>{rows}</table>
    """ + (f'<p><a href="{link}">Open all 100 designs in Trend2Sketch</a></p>' if link else "") + """
    <p><small>Scores represent inferred commercial potential from public trend signals, not guaranteed sales.</small></p>
    """
    r=requests.post("https://api.resend.com/emails",
        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
        json={"from":sender,"to":[to],"subject":f"Trend2Sketch: 100 new designs — Batch #{batch_id}","html":html},
        timeout=30)
    if r.status_code>=300: return f"Email failed: {r.status_code} {r.text[:200]}"
    return "Email sent"

def create_batch():
    con=get_db()
    cur=con.execute("INSERT INTO batches(created_at,started_at,status) VALUES(?,?,?)",
                    (datetime.now().isoformat(timespec="seconds"),datetime.now().isoformat(timespec="seconds"),"researching"))
    batch_id=cur.lastrowid; con.commit();con.close()

    trends, text_model=trend_research()
    con=get_db()
    con.execute("UPDATE batches SET status=?,trend_payload=? WHERE id=?",
                ("generating",json.dumps(trends,ensure_ascii=False),batch_id))
    con.commit();con.close()

    slots=build_slots()
    jobs=[]
    for i,slot in enumerate(slots,1):
        pool=trends.get("diamond_trends",[]) if slot["lane"]=="Diamond" else trends.get("south_trends",[])
        trend=choose_trend(pool,i-1)
        jobs.append((i,slot,trend))

    max_workers=max(1,min(int(os.getenv("GENERATION_CONCURRENCY","4")),5))
    results=[]; errors=[]
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs={ex.submit(generate_one,batch_id,i,slot,trend):(i,slot) for i,slot,trend in jobs}
        for fut in as_completed(futs):
            i,slot=futs[fut]
            try: results.append(fut.result())
            except Exception as e: errors.append({"idx":i,"slot":slot,"error":str(e)})

    email_status=send_email_digest(batch_id,results,trends)
    con=get_db()
    con.execute("""UPDATE batches SET finished_at=?,status=?,generated_count=?,failed_count=?,email_status=?,note=?
                   WHERE id=?""",
                (datetime.now().isoformat(timespec="seconds"),
                 "completed" if not errors else "completed_with_errors",
                 len(results),len(errors),email_status,
                 json.dumps(errors,ensure_ascii=False)[:10000] if errors else "",batch_id))
    con.commit();con.close()
    return batch_id,results,errors,email_status
