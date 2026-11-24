import json,base64,os,sys,urllib.request,re
model,out=sys.argv[1],sys.argv[2]
def d(p,mt): return "data:%s;base64,"%mt+base64.b64encode(open(p,'rb').read()).decode()
prompt="""These images show one starship design: the original concept art (image 1), a clean cut-out (image 2) and a bird's-eye view of the same ship (image 3). The ship is about 25 metres long. It has several long, swept, white/pearl talon-like blade hulls that converge toward the rear into a layered core, dark navy under-structure between the blades, and glowing cyan panels, slots and circular vents.

Create a professional concept-art TURNAROUND SHEET of exactly this ship, for a 3D modeller: a 2x2 grid on a plain light-grey background, neutral studio lighting, no planet, no stars, no motion streaks, no text other than small panel labels.
Panels: (top-left) SIDE PROFILE, orthographic, nose pointing left; (top-right) REAR VIEW, looking straight at the engines; (bottom-left) TOP-DOWN plan view; (bottom-right) FRONT three-quarter view from below.
Keep the design strictly consistent between all four panels and faithful to the reference: same number of blade prongs, same proportions, same colours and cyan light placement. Invent plausible engines at the rear that match the ship's organic, blade-like style (curved cyan-glowing nacelles nested between the blades), not generic round jet nozzles."""
body={"model":model,"modalities":["image","text"],"messages":[{"role":"user","content":[{"type":"text","text":prompt},
 {"type":"image_url","image_url":{"url":d('ship.jpg','image/jpeg')}},
 {"type":"image_url","image_url":{"url":d('ship_cut_white.png','image/png')}},
 {"type":"image_url","image_url":{"url":d('q_top.webp','image/webp')}}]}]}
req=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",json.dumps(body).encode(),{"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"})
r=json.load(urllib.request.urlopen(req,timeout=500))
m=r['choices'][0]['message']; imgs=m.get('images') or []
print(model,'usage',r.get('usage',{}).get('cost'),'text:',(m.get('content') or '')[:200],'n_images',len(imgs))
for i,im in enumerate(imgs):
    u=im['image_url']['url']; open(f"{out}_{i}.png",'wb').write(base64.b64decode(u.split(',',1)[1]))
