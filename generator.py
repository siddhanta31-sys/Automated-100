import base64, os, time, urllib.request
from openai import OpenAI
from config import OPENAI_API_KEY, IMAGE_MODEL, IMAGE_QUALITY, IMAGE_SIZE, IMAGE_DIR, VISION_MODEL
from intelligence import _json_from_text, _text

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


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
Make the jewellery architecture clear enough for a professional designer to evaluate stone layout, motif rhythm, setting strategy and metal distribution. White/neutral studio background, centered, high design readability.
{('Revision instruction: ' + revision_note) if revision_note else ''}'''


def render_design(c, cycle_id, idx, revision_note=''):
    os.makedirs(IMAGE_DIR, exist_ok=True)
    result = client.images.generate(model=IMAGE_MODEL, prompt=build_prompt(c, revision_note), size=IMAGE_SIZE, quality=IMAGE_QUALITY)
    item = result.data[0]
    path = os.path.join(IMAGE_DIR, f'c{cycle_id}_{idx}_{int(time.time())}.png')
    if getattr(item,'b64_json',None):
        with open(path,'wb') as f: f.write(base64.b64decode(item.b64_json))
    elif getattr(item,'url',None):
        urllib.request.urlretrieve(item.url,path)
    else:
        raise RuntimeError('Image API returned no image payload')
    return path


def visual_score(c, path):
    try:
        with open(path,'rb') as f: data=base64.b64encode(f.read()).decode()
        prompt='''Score this jewellery design visualization 1-100 as a strict design director. Above 95 must be exceptional. Evaluate visual balance, originality, stone dominance/layout, manufacturability, coherence with concept, commercial appeal and obvious defects. Return ONLY JSON: {"score": number, "reason": "...", "redesign": "..."}.'''
        resp=client.responses.create(model=VISION_MODEL,input=[{
            'role':'user','content':[
                {'type':'input_text','text':prompt+'\nConcept: '+str(c)},
                {'type':'input_image','image_url':'data:image/png;base64,'+data}
            ]
        }])
        obj=_json_from_text(_text(resp))
        return float(obj.get('score',0)), obj.get('reason',''), obj.get('redesign','')
    except Exception as e:
        # Do not discard a successfully rendered design solely because vision scoring had a transient failure.
        return float(c.get('pre_score',0)), 'Vision score unavailable; pre-score used.', str(e)
