import hashlib, json, re, time, random
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from config import (OPENAI_API_KEY, TEXT_MODEL, VISION_MODEL, RESEARCH_DOMAINS,
                    API_TIMEOUT_SECONDS, API_MAX_RETRIES, CONCEPT_BATCH_SIZE, CONCEPT_MAX_BATCHES)

client = OpenAI(api_key=OPENAI_API_KEY, timeout=API_TIMEOUT_SECONDS, max_retries=2) if OPENAI_API_KEY else None

def _log(msg): print(f'[Trend2Sketch][intelligence] {msg}', flush=True)
def _require_client():
    if client is None: raise RuntimeError('OpenAI client is not configured because OPENAI_API_KEY is empty')
def _text(resp): return resp.output_text if hasattr(resp,'output_text') else str(resp)

def _json_from_text(text):
    text=(text or '').strip(); m=re.search(r'```(?:json)?\s*(.*?)```',text,flags=re.S)
    if m: text=m.group(1).strip()
    starts=[i for i in (text.find('['),text.find('{')) if i>=0]
    if starts: text=text[min(starts):]
    try: return json.loads(text)
    except Exception:
        for ch in (']','}'):
            idx=text.rfind(ch)
            if idx>0:
                try: return json.loads(text[:idx+1])
                except Exception: pass
        raise ValueError(f'Model response was not valid JSON. First 500 chars: {text[:500]}')

def _retry(label,fn,retries=None):
    retries=API_MAX_RETRIES if retries is None else retries; last=None
    for attempt in range(1,max(1,retries)+1):
        try: return fn()
        except Exception as e:
            last=e; _log(f'{label} attempt {attempt}/{retries} failed: {type(e).__name__}: {e}')
            if attempt<retries: time.sleep(min(10,2**(attempt-1))+random.random())
    raise last

def research_market(selected_categories=None,selected_lanes=None,deep=False,feedback=None,references=None,product_constraints=None):
    _require_client(); domains=', '.join(RESEARCH_DOMAINS)
    selected_categories=selected_categories or []; selected_lanes=selected_lanes or ['Diamond','South Indian Gemstone']
    cat=('Focus product development ONLY on these selected product categories: '+', '.join(selected_categories)+'.') if selected_categories else 'Product categories are open-ended; discover promising categories dynamically.'
    lanes='Selected design lanes: '+', '.join(selected_lanes)+'.'
    fb=json.dumps((feedback or [])[:80],ensure_ascii=False)[:10000]
    refs=json.dumps((references or [])[:60],ensure_ascii=False)[:8000]
    constraints=json.dumps(product_constraints or {},ensure_ascii=False)[:4000]
    base=f"""You are the R&D research director of an Indian jewellery manufacturing company, not a generic image-prompt writer.
Research PUBLIC current jewellery signals. Prioritize {domains}, then broaden to other credible Indian retailer/manufacturer/catalogue/exhibition/trend sources when useful. Never copy a specific branded SKU.
{lanes}
{cat}
Study PRODUCT ARCHITECTURE, not just visual keywords: category, concept family/sub-family, regional grammar, motif system, stone hierarchy, stone shapes/cuts, setting language, articulation, construction, approximate weight strategy, negative space, repeat rhythm, centre-piece architecture, detachable/convertible opportunities, wearability, manufacturing constraints, and lightweighting.
For South Indian gemstone jewellery explicitly distinguish useful families/sub-families such as guttapusalu, kasu, Lakshmi/temple, mango, kemp, navaratna, nakshi, peacock/yali, chakra, vanki-derived geometry, antique bridal, contemporary gemstone and credible hybrids; do not force these if research points elsewhere.
Recent owner feedback, if any: {fb}
Owner-approved reference-library notes (learn design DNA; NEVER copy a specific piece): {refs}
Current product engineering constraints: {constraints}
The goal is commercially developable concepts that a jewellery design/CAD team can use, not merely attractive AI imagery."""
    if not deep:
        prompt=base+"""
Return concise JSON with keys: trends, discovered_families, opportunities, manufacturing_signals, avoid_copying_note."""
        try:
            _log(f'research request model={TEXT_MODEL}, web_search=on')
            return _retry('web research',lambda:_json_from_text(_text(client.responses.create(model=TEXT_MODEL,tools=[{'type':'web_search'}],input=prompt))))
        except Exception as e:
            _log(f'web research exhausted retries: {type(e).__name__}: {e}; using non-web fallback')
            return _retry('research fallback',lambda:_json_from_text(_text(client.responses.create(model=TEXT_MODEL,input=prompt+'\nIf live search is unavailable, label limitations.'))))

    lenses=[
      'South Indian heritage/regional concept taxonomy and credible contemporary hybrids',
      'commercial retail/catalogue signals, stone layouts, silhouettes, lightweighting and price/weight practicality',
      'manufacturing/CAD feasibility: settings, articulation, strength, comfort, dimensions, stone-size logic and production risks'
    ]
    def agent(i,lens):
        prompt=base+f"""
DEEP RESEARCH LENS {i}: {lens}. Use web search broadly. Return JSON with evidence_signals, families, subfamilies, opportunities, construction_rules, stone_rules, avoid_patterns, white_space_opportunities."""
        return _retry(f'deep research agent {i}',lambda:_json_from_text(_text(client.responses.create(model=TEXT_MODEL,tools=[{'type':'web_search'}],input=prompt))))
    reports=[]
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs=[ex.submit(agent,i+1,l) for i,l in enumerate(lenses)]
        for f in as_completed(futs):
            try: reports.append(f.result())
            except Exception as e: _log(f'deep research agent failed: {type(e).__name__}: {e}')
    if not reports:
        return research_market(selected_categories,selected_lanes,deep=False,feedback=feedback,references=references,product_constraints=product_constraints)
    synthesis=f"""Act as Chief Jewellery Product Director. Synthesize these independent research reports into an R&D map.
{json.dumps(reports,ensure_ascii=False)[:30000]}
Return ONLY JSON with: trends, discovered_families, subfamilies, opportunities, manufacturing_rules, stone_architecture_rules, regional_grammar, lightweighting_rules, avoid_patterns, concept_seeds, research_depth_note. concept_seeds must be specific product-development directions, not generic adjectives. Never recommend copying a branded SKU."""
    return _retry('deep research synthesis',lambda:_json_from_text(_text(client.responses.create(model=TEXT_MODEL,input=synthesis))))


def analyze_reference_image(path, note='', profile_name='General'):
    """Convert an owner-approved reference into reusable design DNA. Never asks model to copy it."""
    _require_client()
    import base64, mimetypes
    mime=mimetypes.guess_type(path)[0] or 'image/png'
    with open(path,'rb') as f: data=base64.b64encode(f.read()).decode()
    prompt=f"""Act as a senior jewellery design director and manufacturing engineer. Analyze this OWNER-APPROVED reference only to extract reusable design DNA; never recreate/copy the exact piece.
Profile: {profile_name}
Owner note: {note}
Return ONLY JSON with keys: category, regional_style, silhouette, motif_language, stone_hierarchy, stone_colors, stone_shapes_sizes, setting_language, metal_to_stone_ratio, negative_space, motif_density, symmetry, center_architecture, border_fringe_language, articulation, weight_philosophy, manufacturability_rules, comfort_rules, commercial_character, traditional_modern_balance, distinctive_traits, avoid_copying_features, generation_directives.
Generation directives should describe abstract preferences that can guide new original designs."""
    resp=_retry('design DNA image analysis',lambda:client.responses.create(model=VISION_MODEL,input=[{'role':'user','content':[{'type':'input_text','text':prompt},{'type':'input_image','image_url':f'data:{mime};base64,{data}'}]}]),retries=max(2,API_MAX_RETRIES))
    return _json_from_text(_text(resp))

def _normalize_choice(value,allowed):
    raw=str(value or '').strip()
    if not allowed: return raw
    exact={a.lower():a for a in allowed}
    if raw.lower() in exact: return exact[raw.lower()]
    canon=lambda x:re.sub(r'[^a-z0-9]+',' ',x.lower()).strip(); c=canon(raw)
    for a in allowed:
        ca=canon(a)
        if c==ca or (c and (c in ca or ca in c)): return a
    return None

def _concept_batch(research,need,batch_no,selected_categories,selected_lanes):
    cats=('The category field MUST be exactly one of: '+json.dumps(selected_categories)+'.') if selected_categories else 'Choose category dynamically from the research.'
    lanes='The lane field MUST be exactly one of: '+json.dumps(selected_lanes)+'.'
    prompt=f'''You are an expert jewellery creative director. Based on this research JSON:\n{json.dumps(research)[:12000]}
Create exactly {need} ORIGINAL jewellery design concepts. This is parallel creative batch {batch_no}; deliberately explore different architectures and motifs from other batches.
{cats}\n{lanes}
Spread the batch across allowed categories and lanes. Do not recreate a known branded SKU. Every concept must be a CAD-actionable PRODUCT BRIEF, not a vague visual idea. Specify a distinct architecture and credible construction. Avoid generic 'floral luxury necklace' language.\nReturn ONLY a JSON array. Each item: lane, category, concept_family, title, description, materials, target_weight, region_signal, dimensions, stone_hierarchy, stone_shapes_sizes, setting_strategy, construction, articulation, comfort_notes, lightweighting_strategy, commercial_rationale, originality_rationale, manufacturability_rationale.'''
    items=_retry(f'concept batch {batch_no}',lambda:_json_from_text(_text(client.responses.create(model=TEXT_MODEL,input=prompt))), retries=2)
    if isinstance(items,dict): items=items.get('concepts',[])
    if not isinstance(items,list): return []
    valid=[]
    for item in items:
        if not isinstance(item,dict): continue
        lane=_normalize_choice(item.get('lane'),selected_lanes)
        cat=_normalize_choice(item.get('category'),selected_categories) if selected_categories else str(item.get('category','')).strip()
        if not lane or (selected_categories and not cat): continue
        item['lane']=lane
        if cat: item['category']=cat
        valid.append(item)
    return valid[:need]

def _concept_batch_resilient(research,need,batch_no,selected_categories,selected_lanes):
    """Timeout-resilient concept generation. Large failed jobs split into smaller checkpoints."""
    try:
        return _concept_batch(research,need,batch_no,selected_categories,selected_lanes)
    except Exception as e:
        if need <= 3:
            raise
        left=max(2,need//2); right=need-left
        _log(f'concept batch {batch_no}: {type(e).__name__}; splitting {need} into {left}+{right}')
        out=[]
        for suffix,n in (("a",left),("b",right)):
            if n<=0: continue
            try:
                part=_concept_batch(research,n,f'{batch_no}{suffix}',selected_categories,selected_lanes)
                out.extend(part)
                _log(f'concept batch {batch_no}{suffix}: checkpoint saved {len(part)}')
            except Exception as sub:
                _log(f'concept batch {batch_no}{suffix} failed: {type(sub).__name__}: {sub}')
        if not out:
            raise e
        return out[:need]

def generate_concepts(research:Dict,total:int,selected_categories=None,selected_lanes=None,workers=3,batch_size=25,progress_callback=None)->List[Dict]:
    '''Parallel concept discovery. Independent batches run concurrently; failures are retried/fallback-filled.'''
    _require_client(); selected_categories=selected_categories or []; selected_lanes=selected_lanes or ['Diamond','South Indian Gemstone']
    total=max(1,int(total)); batch_size=max(5,min(20,int(batch_size))); workers=max(1,min(5,int(workers)))
    needs=[]; left=total; n=0
    while left>0:
        n+=1; need=min(batch_size,left); needs.append((n,need)); left-=need
    _log(f'parallel concept discovery: target={total}, batches={len(needs)}, workers={workers}, batch_size={batch_size}')
    all_items=[]; seen=set()
    def add(items):
        added=0
        for item in items:
            key=re.sub(r'[^a-z0-9]+',' ',(str(item.get('title',''))+' '+str(item.get('description',''))).lower()).strip()
            key=hashlib.sha1(key.encode()).hexdigest() if key else fingerprint(item)
            if key in seen: continue
            seen.add(key); all_items.append(item); added+=1
            if len(all_items)>=total: break
        return added
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs={ex.submit(_concept_batch_resilient,research,need,bno,selected_categories,selected_lanes):(bno,need) for bno,need in needs}
        for fut in as_completed(futs):
            bno,need=futs[fut]
            try:
                items=fut.result(); added=add(items); _log(f'concept batch {bno}: accepted {added}; live total={len(all_items)}/{total}')
            except Exception as e: _log(f'concept batch {bno} failed after retries: {type(e).__name__}: {e}')
            if progress_callback:
                try: progress_callback(min(len(all_items),total),total)
                except Exception: pass
    # Small sequential fill only if parallel responses were incomplete.
    fill_no=len(needs)+1; attempts=0
    while len(all_items)<total and attempts<3:
        attempts+=1; need=min(batch_size,total-len(all_items))
        try: add(_concept_batch_resilient(research,need,fill_no,selected_categories,selected_lanes))
        except Exception as e: _log(f'fill batch failed: {type(e).__name__}: {e}')
        fill_no+=1
        if progress_callback:
            try: progress_callback(min(len(all_items),total),total)
            except Exception: pass
    if not all_items: raise RuntimeError('Concept generation produced no valid concepts after automatic retries.')
    if len(all_items)<total: _log(f'concept pool partial but usable: {len(all_items)}/{total}; continuing')
    return all_items[:total]

def _score_chunk(chunk,batch_no):
    prompt=f'''Act as a strict jewellery design director. Score each concept from 1-100. Scores above 95 must be rare and exceptional.
Evaluate originality 15, commercial relevance 15, aesthetics/balance 10, manufacturability 15, stone/material logic 10, weight practicality 10, regional/concept authenticity 10, trend relevance 5, novelty/non-repetition 10. Penalize generic/repetitive/impractical/copy-like ideas.
Return ONLY JSON array in same index order; each item: score, reason, risk.\nConcepts:\n{json.dumps(chunk)[:22000]}'''
    scores=_retry(f'score batch {batch_no}',lambda:_json_from_text(_text(client.responses.create(model=TEXT_MODEL,input=prompt))))
    if isinstance(scores,dict): scores=scores.get('scores',[])
    if not isinstance(scores,list): return []
    out=[]
    for concept,s in zip(chunk,scores):
        if not isinstance(s,dict): continue
        c=dict(concept)
        try: c['pre_score']=float(s.get('score',0))
        except Exception: c['pre_score']=0.0
        c['score_reason']=s.get('reason',''); c['risk']=s.get('risk',''); c['cad_instruction']=s.get('cad_instruction','')
        c['score_dimensions']={k:s.get(k) for k in ('commercial','originality','south_indian_authenticity','stone_composition','proportion_balance','manufacturability','weight_efficiency','wearability','trend_relevance','novelty')}
        out.append(c)
    return out

def score_concepts(items:List[Dict],workers=3,progress_callback=None)->List[Dict]:
    '''Parallel scoring keeps ordering irrelevant because pipeline ranks by score.''' 
    _require_client(); workers=max(1,min(5,int(workers))); chunks=[items[i:i+25] for i in range(0,len(items),25)]
    out=[]; done=0; _log(f'parallel scoring: concepts={len(items)}, batches={len(chunks)}, workers={workers}')
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs={ex.submit(_score_chunk,ch,i+1):(i+1,len(ch)) for i,ch in enumerate(chunks)}
        for fut in as_completed(futs):
            bno,count=futs[fut]
            try: scored=fut.result(); out.extend(scored); done+=len(scored); _log(f'score batch {bno}: accepted {len(scored)}; live total={done}/{len(items)}')
            except Exception as e: _log(f'score batch {bno} failed after retries: {type(e).__name__}: {e}')
            if progress_callback:
                try: progress_callback(done,len(items))
                except Exception: pass
    if not out: raise RuntimeError('Concept scoring produced no usable results after automatic retries.')
    return out

def fingerprint(item:Dict)->str:
    base=' '.join(str(item.get(k,'')) for k in ('lane','category','concept_family','title','description'))
    base=re.sub(r'[^a-z0-9 ]+',' ',base.lower()); base=' '.join(sorted(set(base.split())))
    return hashlib.sha256(base.encode()).hexdigest()[:32]

def jaccard(a:str,b:str)->float:
    sa=set(re.findall(r'[a-z0-9]+',a.lower())); sb=set(re.findall(r'[a-z0-9]+',b.lower()))
    return len(sa&sb)/max(1,len(sa|sb))
