"""Silhouette IoU check: model vs traced reference silhouettes (40 px/m, 30 m canvas).

Usage:
  python silhouette_check.py parts            # project model_parts.json faces (fast, pre-Blender)
  python silhouette_check.py renders DIR      # threshold Blender ortho renders sil_{top,right,back}.png
Writes overlay_{view}.png (red = reference only, green = model only, white = both).
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, 'silhouettes.json')))
PPM, C, W = 40, 600, 1200
VIEWS = {'top': (0, 1), 'side': (1, 2), 'back': (0, 2)}   # (u axis, v axis) from xyz

def ref_mask(view):
    im = Image.new('L', (W, W), 0); d = ImageDraw.Draw(im)
    for i, p in enumerate(S[view]):
        d.polygon([(C + u * PPM, C - v * PPM) for u, v in p], fill=255 if i == 0 else 0)
    return np.array(im) > 0

def parts_mask(view, parts):
    a, b = VIEWS[view]
    im = Image.new('L', (W, W), 0); d = ImageDraw.Draw(im)
    for p in parts:
        V = np.array(p['verts'])
        for sgn in (1, -1):
            V2 = V.copy(); V2[:, 0] *= sgn
            for f in p['faces']:
                d.polygon([(C + V2[i, a] * PPM, C - V2[i, b] * PPM) for i in f], fill=255)
    return np.array(im) > 0

def iou(m, r):
    return (m & r).sum() / max((m | r).sum(), 1)

def overlay(m, r, path):
    img = np.zeros((W, W, 3), np.uint8)
    img[r & ~m] = (220, 40, 40); img[m & ~r] = (40, 220, 40); img[m & r] = (235, 235, 235)
    Image.fromarray(img).save(path)

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'parts'
    outdir = sys.argv[2] if len(sys.argv) > 2 else HERE
    res = {}
    if mode == 'parts':
        parts = json.load(open(os.path.join(HERE, 'model_parts.json')))
        for v in VIEWS:
            m, r = parts_mask(v, parts), ref_mask(v)
            res[v] = round(float(iou(m, r)), 4); overlay(m, r, os.path.join(outdir, f'overlay_{v}.png'))
    else:
        names = {'top': 'top', 'side': 'right', 'back': 'back'}
        for v in VIEWS:
            g = np.array(Image.open(os.path.join(outdir, f'sil_{names[v]}.png')).convert('L'))
            m, r = g > 127, ref_mask(v)
            res[v] = round(float(iou(m, r)), 4); overlay(m, r, os.path.join(outdir, f'overlay_{v}.png'))
    print(json.dumps(res))
