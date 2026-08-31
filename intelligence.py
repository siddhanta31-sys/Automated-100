import hashlib, json, re, time
from typing import List, Dict
from openai import OpenAI
from config import OPENAI_API_KEY, TEXT_MODEL, VISION_MODEL, RESEARCH_DOMAINS

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def _text(resp):
    if hasattr(resp, 'output_text'):
        return resp.output_text
    return str(resp)

def _json_from_text(text):
    text = text.strip()
    m = re.search(r'```(?:json)?\s*(.*?)```', text, flags=re.S)
    if m: text = m.group(1).strip()
    start_candidates = [i for i in [text.find('['), text.find('{')] if i >= 0]
    if start_candidates:
        text = text[min(start_candidates):]
    try:
        return json.loads(text)
    except Exception:
        # Trim after last valid-looking bracket.
        for ch in (']','}'):
            idx = text.rfind(ch)
            if idx > 0:
                try: return json.loads(text[:idx+1])
                except Exception: pass
        raise

def research_market():
    domains = ', '.join(RESEARCH_DOMAINS)
    prompt = f'''
You are the autonomous jewellery research director for an Indian jewellery manufacturer.
Research current PUBLIC catalogue and trend signals from the web, especially {domains}, but do not copy any specific branded product.
Also use broad public knowledge of Indian jewellery traditions and contemporary diamond/gemstone design.
Discover design families, sub-families, regional concepts, motifs, setting styles, construction ideas, stone combinations, silhouette changes, lightweighting approaches, bridal/everyday directions and emerging hybrids.
Do NOT restrict yourself to a predefined category list. The purpose is to discover concepts the user may not know to name.
Focus on South Indian gemstone jewellery and diamond jewellery, while allowing cross-category innovation.
Return concise JSON with keys: trends (array), discovered_families (array), opportunities (array), avoid_copying_note (string).
'''
    try:
        resp = client.responses.create(model=TEXT_MODEL, tools=[{'type':'web_search'}], input=prompt)
    except Exception:
        # Fallback without web tool so generation can continue during transient search issues.
        resp = client.responses.create(model=TEXT_MODEL, input=prompt + '\nIf web search is unavailable, use general jewellery design knowledge and clearly label it as non-live.')
    return _json_from_text(_text(resp))


def generate_concepts(research: Dict, total: int) -> List[Dict]:
    all_items = []
    chunk = 60
    while len(all_items) < total:
        need = min(chunk, total-len(all_items))
        prompt = f'''
You are an expert jewellery creative director. Based on this research JSON:
{json.dumps(research)[:14000]}

Create {need} ORIGINAL jewellery design concepts. Explore wide variety; do not repeat the same few necklace/earring archetypes.
Use dynamic categories and concept families discovered from research. Include both Diamond and South Indian Gemstone directions across the batch.
Each concept must be manufacturable in precious metal and distinct in architecture, motif, setting or wearing experience.
Do not recreate a known branded SKU.
Return ONLY a JSON array. Each item must have:
lane, category, concept_family, title, description, materials, target_weight, region_signal, commercial_rationale, originality_rationale, manufacturability_rationale.
'''
        resp = client.responses.create(model=TEXT_MODEL, input=prompt)
        items = _json_from_text(_text(resp))
        if isinstance(items, dict): items = items.get('concepts', [])
        all_items.extend(items[:need])
    return all_items[:total]


def score_concepts(items: List[Dict]) -> List[Dict]:
    out=[]
    # score in chunks to control response size
    for i in range(0, len(items), 40):
        chunk=items[i:i+40]
        prompt=f'''
Act as a strict jewellery design director. Score each concept from 1-100. Scores above 95 must be rare and exceptional.
Evaluate: originality 20, commercial relevance 20, aesthetics/balance 15, manufacturability 15, stone/material logic 10, weight practicality 10, regional/concept authenticity 5, trend relevance 5.
Penalize generic designs, repetitive variations, impractical construction and likely copies.
Return ONLY JSON array with same index order; each item: score (number), reason (short string), risk (short string).
Concepts:
{json.dumps(chunk)[:24000]}
'''
        resp=client.responses.create(model=TEXT_MODEL,input=prompt)
        scores=_json_from_text(_text(resp))
        if isinstance(scores, dict): scores=scores.get('scores',[])
        for concept, s in zip(chunk,scores):
            c=dict(concept); c['pre_score']=float(s.get('score',0)); c['score_reason']=s.get('reason',''); c['risk']=s.get('risk',''); out.append(c)
    return out


def fingerprint(item: Dict) -> str:
    base=' '.join(str(item.get(k,'')) for k in ('lane','category','concept_family','title','description'))
    base=re.sub(r'[^a-z0-9 ]+',' ',base.lower())
    base=' '.join(sorted(set(base.split())))
    return hashlib.sha256(base.encode()).hexdigest()[:32]


def jaccard(a: str, b: str) -> float:
    sa=set(re.findall(r'[a-z0-9]+',a.lower())); sb=set(re.findall(r'[a-z0-9]+',b.lower()))
    if not sa or not sb: return 0
    return len(sa&sb)/len(sa|sb)
