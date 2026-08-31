import hashlib, json, re
from typing import List, Dict
from openai import OpenAI
from config import OPENAI_API_KEY, TEXT_MODEL, VISION_MODEL, RESEARCH_DOMAINS

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def _log(msg):
    print(f'[Trend2Sketch][intelligence] {msg}', flush=True)

def _require_client():
    if client is None:
        raise RuntimeError('OpenAI client is not configured because OPENAI_API_KEY is empty')

def _text(resp):
    if hasattr(resp, 'output_text'):
        return resp.output_text
    return str(resp)

def _json_from_text(text):
    text = (text or '').strip()
    m = re.search(r'```(?:json)?\s*(.*?)```', text, flags=re.S)
    if m: text = m.group(1).strip()
    start_candidates = [i for i in [text.find('['), text.find('{')] if i >= 0]
    if start_candidates:
        text = text[min(start_candidates):]
    try:
        return json.loads(text)
    except Exception:
        for ch in (']','}'):
            idx = text.rfind(ch)
            if idx > 0:
                try: return json.loads(text[:idx+1])
                except Exception: pass
        raise ValueError(f'Model response was not valid JSON. First 500 chars: {text[:500]}')

def research_market(selected_categories=None, selected_lanes=None):
    _require_client()
    domains = ', '.join(RESEARCH_DOMAINS)
    selected_categories = selected_categories or []
    selected_lanes = selected_lanes or ['Diamond','South Indian Gemstone']
    category_instruction = ('Focus product development ONLY on these selected product categories: ' + ', '.join(selected_categories) + '.') if selected_categories else 'Product categories are open-ended; discover promising categories dynamically.'
    lane_instruction = 'Selected design lanes: ' + ', '.join(selected_lanes) + '.'
    prompt = f'''You are the autonomous jewellery research director for an Indian jewellery manufacturer.
Research current PUBLIC catalogue and trend signals from the web, especially {domains}, but do not copy any specific branded product.
{lane_instruction}
{category_instruction}
Also use broad public knowledge of Indian jewellery traditions and contemporary diamond/gemstone design.
Discover design families, sub-families, regional concepts, motifs, setting styles, construction ideas, stone combinations, silhouette changes, lightweighting approaches, bridal/everyday directions and emerging hybrids.
Do NOT restrict yourself to a predefined category list. The purpose is to discover concepts the user may not know to name.
Focus on South Indian gemstone jewellery and diamond jewellery, while allowing cross-category innovation.
Return concise JSON with keys: trends (array), discovered_families (array), opportunities (array), avoid_copying_note (string).'''
    try:
        _log(f'research request model={TEXT_MODEL}, web_search=on')
        resp = client.responses.create(model=TEXT_MODEL, tools=[{'type':'web_search'}], input=prompt)
    except Exception as first_error:
        _log(f'web research call failed: {type(first_error).__name__}: {first_error}; retrying without web_search')
        try:
            resp = client.responses.create(model=TEXT_MODEL, input=prompt + '\nIf web search is unavailable, use general jewellery design knowledge and clearly label it as non-live.')
        except Exception as second_error:
            raise RuntimeError(f'Research API failed with web search ({type(first_error).__name__}: {first_error}) and fallback failed ({type(second_error).__name__}: {second_error})') from second_error
    raw=_text(resp)
    _log(f'research response chars={len(raw)}')
    return _json_from_text(raw)

def generate_concepts(research: Dict, total: int, selected_categories=None, selected_lanes=None) -> List[Dict]:
    _require_client()
    selected_categories = selected_categories or []
    selected_lanes = selected_lanes or ['Diamond','South Indian Gemstone']
    all_items = []
    chunk = 60
    batch_no=0
    while len(all_items) < total:
        batch_no+=1
        need = min(chunk, total-len(all_items))
        prompt = f'''You are an expert jewellery creative director. Based on this research JSON:\n{json.dumps(research)[:14000]}\n\nCreate {need} ORIGINAL jewellery design concepts. Explore wide variety; do not repeat the same few necklace/earring archetypes.\nUse dynamic categories and concept families discovered from research. Include both Diamond and South Indian Gemstone directions across the batch.\nEach concept must be manufacturable in precious metal and distinct in architecture, motif, setting or wearing experience.\nDo not recreate a known branded SKU.\nReturn ONLY a JSON array. Each item must have:\nlane, category, concept_family, title, description, materials, target_weight, region_signal, commercial_rationale, originality_rationale, manufacturability_rationale.'''
        _log(f'concept batch {batch_no}: requesting {need}')
        resp = client.responses.create(model=TEXT_MODEL, input=prompt)
        items = _json_from_text(_text(resp))
        if isinstance(items, dict): items = items.get('concepts', [])
        if not isinstance(items, list) or not items:
            raise ValueError(f'Concept batch {batch_no} returned no concepts')
        if selected_categories:
            allowed={c.strip().lower():c for c in selected_categories}
            filtered=[]
            for item in items:
                cat=str(item.get('category','')).strip().lower()
                if cat in allowed:
                    item['category']=allowed[cat]
                    filtered.append(item)
            items=filtered
        if selected_lanes:
            allowed_lanes={c.strip().lower():c for c in selected_lanes}
            filtered=[]
            for item in items:
                lane=str(item.get('lane','')).strip().lower()
                if lane in allowed_lanes:
                    item['lane']=allowed_lanes[lane]
                    filtered.append(item)
            items=filtered
        if not items:
            raise ValueError(f'Concept batch {batch_no} did not follow the selected category/lane controls')
        take=items[:need]
        all_items.extend(take)
        _log(f'concept batch {batch_no}: received {len(take)} valid selected-category concepts; total={len(all_items)}')
    return all_items[:total]

def score_concepts(items: List[Dict]) -> List[Dict]:
    _require_client()
    out=[]
    for i in range(0, len(items), 40):
        chunk=items[i:i+40]
        batch_no=i//40+1
        prompt=f'''Act as a strict jewellery design director. Score each concept from 1-100. Scores above 95 must be rare and exceptional.\nEvaluate: originality 20, commercial relevance 20, aesthetics/balance 15, manufacturability 15, stone/material logic 10, weight practicality 10, regional/concept authenticity 5, trend relevance 5.\nPenalize generic designs, repetitive variations, impractical construction and likely copies.\nReturn ONLY JSON array with same index order; each item: score (number), reason (short string), risk (short string).\nConcepts:\n{json.dumps(chunk)[:24000]}'''
        _log(f'score batch {batch_no}: scoring {len(chunk)}')
        resp=client.responses.create(model=TEXT_MODEL,input=prompt)
        scores=_json_from_text(_text(resp))
        if isinstance(scores, dict): scores=scores.get('scores',[])
        if not isinstance(scores,list) or len(scores) < len(chunk):
            raise ValueError(f'Score batch {batch_no} returned {len(scores) if isinstance(scores,list) else 0} scores for {len(chunk)} concepts')
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
