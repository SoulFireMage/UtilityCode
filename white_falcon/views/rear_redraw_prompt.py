import json,base64,os,sys,urllib.request
model,out=sys.argv[1],sys.argv[2]
def d(p,mt): return "data:%s;base64,"%mt+base64.b64encode(open(p,'rb').read()).decode()
prompt="""Image 1 is the REAR of a starship: three large circular cyan-glowing engines in a triangle (one top-centre, two lower), curved cyan conduit lines, swept blade hulls flaring out to both sides. Images 2 and 3 show the SAME ship from the front, top and side: long swept white/pearl talon-like blade hulls (the blade tips are the nose), dark navy under-structure, cyan light slots.

Draw ONE clean, perfectly left-right symmetric, orthographic REAR VIEW of this ship, looking straight at the engines, centred on a plain light-grey background, neutral studio lighting, no background scenery, no text.
Keep the engine arrangement and shapes from image 1 exactly (three circular engines in a triangle, the conduit lines, the central lower keel). Make the hull materials match images 2 and 3: the outer swept blades and upper hull in white/pearl panels with dark navy gaps and cyan slots, so it is clearly the back of the ship in images 2 and 3. The blade tips seen beyond the engines should match the multi-prong layout of the top-down views in image 2. Same painterly concept-art rendering style as image 3."""
body={"model":model,"modalities":["image","text"],"messages":[{"role":"user","content":[{"type":"text","text":prompt},
 {"type":"image_url","image_url":{"url":d('mirrorR_cut.png','image/png')}},
 {"type":"image_url","image_url":{"url":d('gptsheet.webp','image/webp')}},
 {"type":"image_url","image_url":{"url":d('cut.png','image/png')}}]}]}
req=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",json.dumps(body).encode(),{"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"})
r=json.load(urllib.request.urlopen(req,timeout=500))
m=r['choices'][0]['message']; imgs=m.get('images') or []
print(model,'cost',r.get('usage',{}).get('cost'),'n',len(imgs))
for i,im in enumerate(imgs): open(f"{out}_{i}.png",'wb').write(base64.b64decode(im['image_url']['url'].split(',',1)[1]))
