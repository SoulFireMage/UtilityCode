from PIL import Image
import numpy as np, json
from scipy import ndimage as ndi
from skimage import measure
from shapely.geometry import Polygon
PPM=40
TH={'top':85,'back':62,'side':62}
out={}
for n in ('top','back','side'):
    g=np.array(Image.open(f'ref_{n}_clean.png').convert('L')).astype(float)
    m=g>TH[n]; m=ndi.binary_opening(m,iterations=1); m=ndi.binary_closing(m,iterations=3)
    holes=ndi.binary_fill_holes(m)&~m; lab,nl=ndi.label(holes)
    if nl:
        sizes=ndi.sum(holes,lab,range(1,nl+1))
        for i,s in enumerate(sizes):
            if s<400: m[lab==i+1]=True
    lab,nl=ndi.label(m); sizes=ndi.sum(m,lab,range(1,nl+1)); m=lab==(np.argmax(sizes)+1)
    if n!='top': m=ndi.binary_fill_holes(m)
    Image.fromarray((m*255).astype('uint8')).save(f'mask_{n}.png')
    polys=[]
    for c in measure.find_contours(np.pad(m,1).astype(float),0.5):
        if len(c)<20: continue
        p=Polygon([((x-1-600)/PPM,(600-(y-1))/PPM) for y,x in c]).simplify(0.04)
        if p.area<0.3: continue
        polys.append(list(p.exterior.coords)[:-1])
    out[n]=polys
    ys,xs=np.nonzero(m); print(n,'polys',[len(p) for p in polys],'extent u %.1f..%.1f v %.1f..%.1f m'%((xs.min()-600)/PPM,(xs.max()-600)/PPM,(600-ys.max())/PPM,(600-ys.min())/PPM))
json.dump(out,open('silhouettes.json','w'))
