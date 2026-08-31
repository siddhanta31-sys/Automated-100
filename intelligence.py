import hashlib, json, re, time, random
from typing import List, Dict
from openai import OpenAI
from config import (OPENAI_API_KEY, TEXT_MODEL, VISION_MODEL, RESEARCH_DOMAINS,
                    API_TIMEOUT_SECONDS, API_MAX_RETRIES, CONCEPT_BATCH_SIZE, CONCEPT_MAX_BATCHES)

client = OpenAI(api_key=OPENAI_API_KEY, timeout=API_TIMEOUT_SECONDS, max_retries=2) if OPENAI_API_KEY else None

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

def _retry(label, fn, retries=None):
    retries = API_MAX_RETRIES if retries is None else retries
    last = None
    for attempt in range(1, max(1, retries)+1):
        try:
            return fn()
        except Exception as e:
            last = e
            _log(f'{label} attempt {attempt}/{retries} failed: {type(e).__name__}: {e}')
            if attempt < retries:
                time.sleep(min(12, 2 ** (attempt-1)) + random.random())
    raise last

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
Do NOT restrict yourself to a predefined category list unless the user selected categories. The purpose is to discover concepts the user may not know to name.
Focus on South Indian gemstone jewellery and diamond jewellery, while allowing cross-category innovation.
Return concise JSON with keys: trends (array), discovered_families (array), opportunities (array), avoid_copying_note (string).'''
    try:
        _log(f'research request model={TEXT_MODEL}, web_search=on')
        return _retry('web research', lambda: _json_from_text(_text(client.responses.create(model=TEXT_MODEL, tools=[{'type':'web_search'}], input=prompt))))
    except Exception as first_error:
        _log(f'web research exhausted retries: {type(first_error).__name__}: {first_error}; using non-web fallback')
        return _retry('research fallback', lambda: _json_from_text(_text(client.responses.create(model=TEXT_MODEL, input=prompt + '\nIf web search is unavailable, use general jewellery design knowledge and clearly label it as non-live.'))))

def _normalize_choice(value, allowed):
    raw=str(value or '').strip()
    if not allowed: return raw
    exact={a.lower():a for a in allowed}
    if raw.lower() in exact: return exact[raw.lower()]
    # tolerate punctuation/slash differences but never invent a category outside the user's choices
    canon=lambda x: re.sub(r'[^a-z0-9]+',' ',x.lower()).strip()
    c=canon(raw)
    for a in allowed:
        ca=canon(a)
        if c==ca or (c and (c in ca or ca in c)):
            return a
    return None

def generate_concepts(research: Dict, total: int, selected_categories=None, selected_lanes=None) -> List[Dict]:
    _require_client()
    selected_categories = selected_categories or []
    selected_lanes = selected_lanes or ['Diamond','South Indian Gemstone']
    all_items=[]
    batch_no=0
    no_progress=0
    batch_size=max(10,min(60,CONCEPT_BATCH_SIZE))
    max_batches=max((total + batch_size - 1)//batch_size + 3, CONCEPT_MAX_BATCHES)
    while len(all_items) < total and batch_no < max_batches:
        batch_no += 1
        need=min(batch_size,total-len(all_items))
        cats = ('The category field MUST be exactly one of: ' + json.dumps(selected_categories) + '.') if selected_categories else 'Choose category dynamically from the research.'
        lanes = 'The lane field MUST be exactly one of: ' + json.dumps(selected_lanes) + '.'
        prompt=f'''You are an expert jewellery creative director. Based on this research JSON:\n{json.dumps(research)[:14000]}

Create exactly {need} ORIGINAL jewellery design concepts.
{cats}
{lanes}
Spread the batch across the allowed categories and lanes as evenly as practical. Explore wide variety; do not repeat the same few archetypes.
Each concept must be manufacturable in precious metal and distinct in architecture, motif, setting, stone hierarchy or wearing experience.
Do not recreate a known branded SKU.
Return ONLY a JSON array. Each item must have: lane, category, concept_family, title, description, materials, target_weight, region_signal, commercial_rationale, originality_rationale, manufacturability_rationale.'''
        _log(f'concept batch {batch_no}: requesting {need}; current={len(all_items)}/{total}')
        try:
            items=_retry(f'concept batch {batch_no}', lambda: _json_from_text(_text(client.responses.create(model=TEXT_MODEL,input=prompt))))
        except Exception as e:
            _log(f'concept batch {batch_no} skipped after retries: {type(e).__name__}: {e}')
            no_progress += 1
            if no_progress >= 3 and all_items:
                break
            continue
        if isinstance(items,dict): items=items.get('concepts',[])
        if not isinstance(items,list): items=[]
        valid=[]
        for item in items:
            if not isinstance(item,dict): continue
            lane=_normalize_choice(item.get('lane'),selected_lanes)
            cat=_normalize_choice(item.get('category'),selected_categories) if selected_categories else str(item.get('category','')).strip()
            if not lane or (selected_categories and not cat):
                continue
            item['lane']=lane
            if cat: item['category']=cat
            valid.append(item)
        if not valid:
            no_progress += 1
            _log(f'concept batch {batch_no}: 0 valid concepts; retry budget remains')
            if no_progress >= 3 and all_items: break
            continue
        no_progress=0
        take=valid[:need]
        all_items.extend(take)
        _log(f'concept batch {batch_no}: accepted {len(take)}; total={len(all_items)}/{total}')
    if not all_items:
        raise RuntimeError('Concept generation produced no valid concepts after automatic retries.')
    if len(all_items) < total:
        _log(f'concept pool partial but usable: {len(all_items)}/{total}; continuing instead of hanging')
    return all_items[:total]

def score_concepts(items: List[Dict]) -> List[Dict]:
    _require_client(); out=[]
    for i in range(0,len(items),30):
        chunk=items[i:i+30]; batch_no=i//30+1
        prompt=f'''Act as a strict jewellery design director. Score each concept from 1-100. Scores above 95 must be rare and exceptional.
Evaluate: originality 20, commercial relevance 20, aesthetics/balance 15, manufacturability 15, stone/material logic 10, weight practicality 10, regional/concept authenticity 5, trend relevance 5.
Penalize generic designs, repetitive variations, impractical construction and likely copies.
Return ONLY JSON array with same index order; each item: score (number), reason (short string), risk (short string).
Concepts:\n{json.dumps(chunk)[:24000]}'''
        _log(f'score batch {batch_no}: scoring {len(chunk)}')
        try:
            scores=_retry(f'score batch {batch_no}',lambda: _json_from_text(_text(client.responses.create(model=TEXT_MODEL,input=prompt))))
        except Exception as e:
            _log(f'score batch {batch_no} skipped after retries: {type(e).__name__}: {e}')
            continue
        if isinstance(scores,dict): scores=scores.get('scores',[])
        if not isinstance(scores,list): scores=[]
        for concept,s in zip(chunk,scores):
            if not isinstance(s,dict): continue
            c=dict(concept)
            try: c['pre_score']=float(s.get('score',0))
            except Exception: c['pre_score']=0.0
            c['score_reason']=s.get('reason',''); c['risk']=s.get('risk',''); out.append(c)
    if not out:
        raise RuntimeError('Concept scoring produced no usable results after automatic retries.')
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
