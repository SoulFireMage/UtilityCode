"""Contact sheet: reference ortho views with the model silhouette overlaid + beauty renders + IoU."""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, 'renders')
REF = {'top': 'blender_TOP_numpad7_SYMMETRIC.png', 'right': 'blender_RIGHT_numpad3.png', 'back': 'blender_BACK_ctrl_numpad1_SYMMETRIC.png'}
iou = json.loads(subprocess.check_output([sys.executable, os.path.join(HERE, 'silhouette_check.py'), 'renders', R]).decode().strip().splitlines()[-1])
key = {'top': 'top', 'right': 'side', 'back': 'back'}
try: font = ImageFont.truetype('arial.ttf', 26); small = ImageFont.truetype('arial.ttf', 20)
except OSError: font = small = ImageFont.load_default()
tiles = {}
for v, f in REF.items():
    ref = Image.open(os.path.join(HERE, '..', 'blender_ref', f)).convert('RGB').resize((1200, 1200))
    m = np.array(Image.open(os.path.join(R, f'sil_{v}.png')).convert('L')) > 127
    edge = m & ~ndi.binary_erosion(m, iterations=2)
    a = np.array(ref).astype(float)
    a[m] = a[m] * 0.6 + np.array([0, 200, 255]) * 0.4
    a[edge] = (0, 255, 255)
    t = Image.fromarray(a.astype(np.uint8))
    crop = (60, 60, 1140, 1140) if v == 'top' else (40, 420, 1160, 780)
    t = t.crop(crop); d = ImageDraw.Draw(t)
    d.text((14, 10), f'{v.upper()}  IoU {iou[key[v]]:.3f}', fill=(255, 255, 120), font=font)
    tiles[v] = t
W = 2200; sheet = Image.new('RGB', (W, 1790), (18, 22, 32)); d = ImageDraw.Draw(sheet)
top = tiles['top'].resize((1000, 1000)); sheet.paste(top, (20, 80))
for i, v in enumerate(('right', 'back')):
    t = tiles[v].resize((1140, 366)); sheet.paste(t, (1040, 80 + i * 386))
b1 = Image.open(os.path.join(R, 'beauty_34.png')).convert('RGB').resize((1060, 662))
b2 = Image.open(os.path.join(R, 'beauty_rear.png')).convert('RGB').resize((1060, 662))
sheet.paste(b1, (20, 1100)); sheet.paste(b2, (1120, 1100))
d.rectangle((1040, 850, 2180, 1000), fill=(18, 22, 32))
d.text((20, 18), "White Falcon (Gawain's starship): model vs Meshy ortho references", fill=(230, 235, 245), font=font)
d.text((1060, 870), 'Cyan = model silhouette (Blender ortho render, 30 m @ 40 px/m)', fill=(0, 230, 255), font=small)
d.text((1060, 900), f"IoU  top {iou['top']:.3f}   right {iou['side']:.3f}   back {iou['back']:.3f}   (target 0.85)", fill=(255, 255, 120), font=small)
d.text((1060, 930), 'Bottom: Cycles GPU beauty, front 3/4 and rear (engine triangle)', fill=(200, 205, 215), font=small)
sheet.save(os.path.join(HERE, 'model_preview.jpg'), quality=90)
json.dump(iou, open(os.path.join(R, 'iou.json'), 'w'))
print(iou)
