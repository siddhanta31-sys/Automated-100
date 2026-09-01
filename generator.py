import base64, os, time, urllib.request, random
from openai import OpenAI
from config import (OPENAI_API_KEY, IMAGE_MODEL, IMAGE_QUALITY, IMAGE_SIZE, IMAGE_DIR, VISION_MODEL,
                    API_TIMEOUT_SECONDS, API_MAX_RETRIES, RENDER_RETRIES)
from intelligence import _json_from_text, _text

client = OpenAI(api_key=OPENAI_API_KEY, timeout=API_TIMEOUT_SECONDS, max_retries=2) if OPENAI_API_KEY else None

def _retry(label, fn, retries):
    last=None
    for attempt in range(1,max(1,retries)+1):
        try: return fn()
        except Exception as e:
            last=e
            print(f'[Trend2Sketch][generator] {label} attempt {attempt}/{retries} failed: {type(e).__name__}: {e}',flush=True)
            if attempt<retries: time.sleep(min(10,2**(attempt-1))+random.random())
    raise last

def build_prompt(c, revision_note=''):
    return f'''Create a premium jewellery DESIGN SKETCH / clean product concept visualization, not a lifestyle photo.
Original design only; do not copy any branded SKU.
Lane: {c.get('lane')}
Category: {c.get('category')}
Concept family: {c.get('concept_family')}
Concept: {c.get('description')}
Materials/stones: {c.get('materials')}
Target weight: {c.get('target_weight')}
Regional signal: {c.get('region_signal')}
Approx dimensions: {c.get('dimensions')}
Stone hierarchy: {c.get('stone_hierarchy')}
Stone shapes/sizes: {c.get('stone_shapes_sizes')}
Setting strategy: {c.get('setting_strategy')}
Construction: {c.get('construction')}
Articulation: {c.get('articulation')}
Comfort: {c.get('comfort_notes')}
Lightweighting: {c.get('lightweighting_strategy')}
CAD direction: {c.get('cad_instruction')}
Approx dimensions: {c.get('dimensions')}
Stone hierarchy: {c.get('stone_hierarchy')}
Stone shapes/sizes: {c.get('stone_shapes_sizes')}
Setting strategy: {c.get('setting_strategy')}
Construction: {c.get('construction')}
Articulation: {c.get('articulation')}
Comfort: {c.get('comfort_notes')}
Lightweighting: {c.get('lightweighting_strategy')}
CAD direction: {c.get('cad_instruction')}
Make this look like a professional jewellery product-development sketch. Preserve the specified architecture exactly enough for a CAD designer to interpret stone hierarchy, approximate stone scale, motif rhythm, joints/articulation, setting strategy, negative space and metal distribution. Avoid fantasy construction, impossible stone placement, excessive decorative noise, and generic AI-jewellery symmetry. White/neutral studio background, centered, high design readability.
{('Revision instruction: ' + revision_note) if revision_note else ''}'''

def render_design(c,cycle_id,idx,revision_note=''):
    if client is None: raise RuntimeError('OpenAI image client is not configured')
    os.makedirs(IMAGE_DIR,exist_ok=True)
    def call():
        result=client.images.generate(model=IMAGE_MODEL,prompt=build_prompt(c,revision_note),size=IMAGE_SIZE,quality=IMAGE_QUALITY)
        item=result.data[0]
        path=os.path.join(IMAGE_DIR,f'c{cycle_id}_{idx}_{int(time.time())}.png')
        if getattr(item,'b64_json',None):
            with open(path,'wb') as f: f.write(base64.b64decode(item.b64_json))
        elif getattr(item,'url',None):
            urllib.request.urlretrieve(item.url,path)
        else: raise RuntimeError('Image API returned no image payload')
        return path
    return _retry(f'render c{cycle_id}/{idx}',call,RENDER_RETRIES+1)

def visual_score(c,path):
    if client is None: return float(c.get('pre_score',0)),'Vision unavailable; pre-score used.','OpenAI client not configured'
    def call():
        with open(path,'rb') as f: data=base64.b64encode(f.read()).decode()
        prompt='''Score this jewellery design visualization 1-100 as a strict design director. Above 95 must be exceptional. Evaluate visual balance, originality, stone dominance/layout, manufacturability, coherence with concept, commercial appeal and obvious defects. Return ONLY JSON: {"score": number, "reason": "...", "redesign": "..."}.'''
        resp=client.responses.create(model=VISION_MODEL,input=[{'role':'user','content':[{'type':'input_text','text':prompt+'\nConcept: '+str(c)},{'type':'input_image','image_url':'data:image/png;base64,'+data}]}])
        obj=_json_from_text(_text(resp))
        return float(obj.get('score',0)),obj.get('reason',''),obj.get('redesign','')
    try:
        return _retry('visual score',call,max(2,API_MAX_RETRIES))
    except Exception as e:
        return float(c.get('pre_score',0)),'Vision score unavailable after retries; pre-score used.',str(e)
