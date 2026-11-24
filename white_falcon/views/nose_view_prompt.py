import json,base64,os,sys,urllib.request
model,out=sys.argv[1],sys.argv[2]
def d(p,mt): return "data:%s;base64,"%mt+base64.b64encode(open(p,'rb').read()).decode()
prompt="""All three images show the same starship. Image 1 is its REAR view (three circular cyan engines). Image 2 is a sheet of top-down and side views (the multi-prong blade tips are the NOSE). Image 3 is the original concept art, a front three-quarter view from above.

Draw ONE clean, perfectly left-right symmetric, orthographic FRONT VIEW of this ship: the camera looks straight down the ship's long axis at the nose, so the long swept white/pearl blade prongs point directly at the viewer and are seen end-on and heavily foreshortened, arranged in the same multi-prong pattern as the top-down views; behind them the layered core and the outer swept blades flare out to the sides, matching the silhouette width of the rear view in image 1. White/pearl hull panels all over, dark navy gaps, cyan light slots and vents. Centred on a plain light-grey background, neutral studio lighting, same painterly concept-art rendering style, no background scenery, no text."""
body={"model":model,"modalities":["image","text"],"messages":[{"role":"user","content":[{"type":"text","text":prompt},
 {"type":"image_url","image_url":{"url":d('rear.png','image/png')}},
 {"type":"image_url","image_url":{"url":d('sheet.webp','image/webp')}},
 {"type":"image_url","image_url":{"url":d('cut.png','image/png')}}]}]}
req=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",json.dumps(body).encode(),{"Authorization":"Bearer "+os.environ["OPENROUTER_API_KEY"],"Content-Type":"application/json"})
r=json.load(urllib.request.urlopen(req,timeout=500))
m=r['choices'][0]['message']; imgs=m.get('images') or []
print(model,'cost',r.get('usage',{}).get('cost'),'n',len(imgs))
for i,im in enumerate(imgs): open(f"{out}_{i}.png",'wb').write(base64.b64decode(im['image_url']['url'].split(',',1)[1]))
