"""Generate the White Falcon part meshes as JSON (pure Python: numpy + PIL).

Each blade/hull part is a quad loft along a spine curve. Spine points and
height/thickness/cant profiles are hand-set below; the plan-view widths at each
station are sampled from the traced TOP silhouette (silhouettes.json), so the
top outline follows the Meshy reference. Run, then build in Blender with
build_model.py. Coordinates: metres, nose -Y, up +Z, +X half only (mirrored).
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, 'silhouettes.json')))
PPM, C = 40, 600

def raster(polys, W=1200):
    im = Image.new('L', (W, W), 0); d = ImageDraw.Draw(im)
    for i, p in enumerate(polys):
        d.polygon([(C + u * PPM, C - v * PPM) for u, v in p], fill=255 if i == 0 else 0)
    return np.array(im) > 0
TOP = raster(S['top'][:1])   # outer outline only: tiny interior slots don't pinch widths

def inside(x, y):
    c, r = int(round(C + x * PPM)), int(round(C - y * PPM))
    return 0 <= r < 1200 and 0 <= c < 1200 and TOP[r, c]

def march(p, d, cap):
    """distance from p along unit d that stays inside the top mask (<= cap)."""
    s = 0.0
    while s < cap and inside(p[0] + d[0] * s, p[1] + d[1] * s):
        s += 0.025
    return min(s, cap)

def catmull(ctrl, ds=0.22):
    P = [np.array(c, float) for c in ctrl]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    pts = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        n = max(2, int(np.linalg.norm(p2 - p1) / ds * 3))
        for k in range(n):
            t = k / n
            pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    pts.append(P[-2])
    pts = np.array(pts)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    L = seg[-1]; m = max(3, int(L / ds))
    out = np.stack([np.interp(np.linspace(0, L, m + 1), seg, pts[:, k]) for k in range(2)], 1)
    return out

def tab(table, u):
    a = np.array(table, float)
    return float(np.interp(u, a[:, 0], a[:, 1]))

def smooth(a, n=2):
    a = np.array(a, float)
    for _ in range(n):
        b = a.copy(); b[1:-1] = 0.25 * a[:-2] + 0.5 * a[1:-1] + 0.25 * a[2:]; a = b
    return a

# section templates (s across width, t up). s>0 -> right-of-travel side.
# Upper surface is faceted (hard-surface): edge -> navy chamfer -> pearl panel -> ridge.
FULL = [(1, 0), (0.82, 0.38), (0.55, 0.84), (0, 1), (-0.55, 0.84), (-0.82, 0.38), (-1, 0),
        (-0.6, -0.72), (0, -1), (0.6, -0.72)]
HALF = [(0, 1), (0.55, 0.84), (0.82, 0.38), (1, 0), (0.6, -0.72), (0, -1)]
SHARP_FULL = {0, 1, 2, 3, 4, 5, 6, 8}
SHARP_HALF = {0, 1, 2, 3, 5}
def facet_mat(a, b):
    if a[1] < 0 or b[1] < 0: return 1                       # underside: navy
    if abs(a[0]) == 1 or abs(b[0]) == 1: return 1           # edge chamfer: navy recess band
    return 0

class Mesh:
    def __init__(s, name, mats=('Pearl_Hull', 'Navy_Recess', 'Cyan_Glow'), axis=False, bisect=False):
        s.name, s.mats, s.axis, s.bisect = name, list(mats), axis, bisect
        s.v, s.f, s.m, s.sharp = [], [], [], []
    def add_v(s, p):
        s.v.append([round(float(c), 5) for c in p]); return len(s.v) - 1
    def add_f(s, idx, mat=0):
        s.f.append(list(idx)); s.m.append(mat)
    def js(s):
        return dict(name=s.name, verts=s.v, faces=s.f, mat=s.m, mats=s.mats, sharp=s.sharp,
                    axis=s.axis, bisect=s.bisect)

def loft(name, ctrl, P, axis=False, glow=None):
    """P: dict of u-tables: z, ht, hb, k (dz per m of x away from spine), capL, capR, wmin."""
    sp = catmull(ctrl)
    n = len(sp)
    tang = np.gradient(sp, axis=0); tang /= np.linalg.norm(tang, axis=1)[:, None]
    nor = np.stack([tang[:, 1], -tang[:, 0]], 1)            # right of travel
    u = np.linspace(0, 1, n)
    wr = np.array([march(sp[i], nor[i], tab(P['capR'], u[i])) for i in range(n)])
    wl = np.zeros(n) if axis else np.array([march(sp[i], -nor[i], tab(P['capL'], u[i])) for i in range(n)])
    wmin = P.get('wmin', 0.05)
    wr = np.maximum(smooth(wr, 3), wmin); wl = np.maximum(smooth(wl, 3), wmin)
    if 'wscale' in P:
        sc = np.array([tab(P['wscale'], x) for x in u]); wr *= sc; wl *= sc
    M = Mesh(name, axis=axis)
    tmpl = HALF if axis else FULL
    sharp = SHARP_HALF if axis else SHARP_FULL
    rings = []
    for i in range(1, n - 1):
        z = tab(P['z'], u[i]); ht = tab(P['ht'], u[i]); hb = tab(P['hb'], u[i]); k = tab(P.get('k', [[0, 0], [1, 0]]), u[i])
        kt = tab(P.get('kt', [[0, 0], [1, 0]]), u[i])   # extra cant on the upper surface only (lens taper)
        ring = []
        for (s_, t_) in tmpl:
            w = wr[i] if s_ >= 0 else wl[i]
            off = nor[i] * s_ * w
            x, y = sp[i, 0] + off[0], sp[i, 1] + off[1]
            if axis: x = max(x, 0.0)
            dx = x - sp[i, 0]
            zz = z + (t_ * ht if t_ >= 0 else t_ * hb) + k * dx + (kt * dx * (1 if t_ > 0 else -1 if t_ < 0 else 0))
            ring.append(M.add_v((x, y, zz)))
        rings.append(ring)
    m = len(tmpl)
    def ends(i):
        return M.add_v((sp[i, 0], sp[i, 1], tab(P['z'], u[i]) + 0.5 * (tab(P['ht'], u[i]) - tab(P['hb'], u[i]))))
    tip, root = ends(0), ends(n - 1)
    nj = m if not axis else m - 1
    for a, b in zip(rings[:-1], rings[1:]):
        for j in range(nj):
            j2 = (j + 1) % m
            M.add_f((a[j], a[j2], b[j2], b[j]), facet_mat(tmpl[j], tmpl[j2]))
    for j in range(nj):
        j2 = (j + 1) % m
        mat = facet_mat(tmpl[j], tmpl[j2])
        M.add_f((tip, rings[0][j2], rings[0][j]), mat)
        M.add_f((root, rings[-1][j], rings[-1][j2]), mat)
    if axis:   # close the open half-ends on the mirror plane is not needed (mirror merges)
        pass
    for j in sharp:
        for a, b in zip(rings[:-1], rings[1:]):
            M.sharp.append([a[j], b[j]])
    # glowing slots: dashes floating just above the upper facet(s)
    if glow:
        for (u0, u1, side, s0, s1, dash) in glow:
            i0, i1 = int(u0 * (n - 3)), int(u1 * (n - 3))
            jA, jB = (0, 1) if side > 0 else (6, 5)
            if axis: jA, jB = 3, 2
            i = i0
            while i + 2 <= i1:
                pts = []
                for ii in (i, i + 2):
                    A, B = np.array(M.v[rings[ii][jA]]), np.array(M.v[rings[ii][jB]])
                    for s in (s0, s1):
                        q = A + (B - A) * s; q[2] += 0.025; pts.append(q)
                q = [M.add_v(p) for p in pts]
                M.add_f((q[0], q[1], q[3], q[2]), 2)
                i += dash
    return M

def revolve(name, centre, axis_dir, profile, seg=40, mats=None, half=False):
    """profile: list of (r, a, mat) points along the axis (a = distance along axis_dir)."""
    c = np.array(centre, float); d = np.array(axis_dir, float); d /= np.linalg.norm(d)
    e1 = np.cross(d, [0, 0, 1.0]) if abs(d[2]) < 0.9 else np.cross(d, [1.0, 0, 0]); e1 /= np.linalg.norm(e1)
    e2 = np.cross(d, e1)
    M = Mesh(name, mats=mats or ['Pearl_Hull', 'Navy_Recess', 'Cyan_Glow'], axis=half)
    # half=True: only the +X half (x = r*cos t, t in [-90, 90] deg), open on the mirror plane
    ang = np.linspace(-math.pi / 2, math.pi / 2, seg // 2 + 1) if half else np.linspace(0, 2 * math.pi, seg, endpoint=False)
    rings = []
    for (r, a, _) in profile:
        if r < 1e-4:
            rings.append([M.add_v(c + d * a)] * len(ang))
        else:
            pts = [c + d * a + r * (math.cos(t) * e1 + math.sin(t) * e2) for t in ang]
            if half:
                for p in pts: p[0] = max(p[0], 0.0)
            rings.append([M.add_v(p) for p in pts])
    nseg = len(ang) - 1 if half else seg
    for k in range(len(profile) - 1):
        A, B, mat = rings[k], rings[k + 1], profile[k][2]
        for j in range(nseg):
            j2 = (j + 1) % len(ang)
            q = [A[j], A[j2], B[j2], B[j]]
            q = [x for i, x in enumerate(q) if x not in q[:i]]
            if len(q) >= 3: M.add_f(q, mat)
    return M

def tube(name, pts, r=0.07, seg=8):
    pts = [np.array(p, float) for p in pts]
    M = Mesh(name, mats=['Cyan_Glow'])
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]); t /= np.linalg.norm(t)
        e1 = np.cross(t, [0, 0, 1.0]); e1 /= np.linalg.norm(e1); e2 = np.cross(t, e1)
        rings.append([M.add_v(p + r * (math.cos(a) * e1 + math.sin(a) * e2)) for a in np.linspace(0, 2 * math.pi, seg, endpoint=False)])
    for A, B in zip(rings[:-1], rings[1:]):
        for j in range(seg):
            M.add_f((A[j], A[(j + 1) % seg], B[(j + 1) % seg], B[j]), 0)
    for R, rev in ((rings[0], True), (rings[-1], False)):
        M.add_f(R[::-1] if rev else R, 0)
    return M

def bez(p0, p1, p2, n=10):
    p0, p1, p2 = map(np.array, (p0, p1, p2))
    return [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2 for t in np.linspace(0, 1, n)]

# ---------------------------------------------------------------- parts
def build():
    parts = []
    # Central blade: the biggest nose blade, on the centreline.
    parts.append(loft('Blade_Central', [(0, -12.62), (0, -8), (0, -3), (0, 1.5)], dict(
        z=[[0, -1.4], [0.3, -0.7], [0.6, -0.05], [1, 0.2]],
        ht=[[0, 0.03], [0.12, 0.3], [0.35, 0.5], [0.65, 0.65], [1, 0.7]],
        hb=[[0, 0.03], [0.06, 0.35], [0.3, 1.05], [0.6, 1.75], [1, 1.9]],
        capR=[[0, 2.4], [1, 2.4]]), axis=True,
        glow=[(0.2, 0.7, 1, 0.25, 0.75, 4)]))
    # Core hull: thick rear body that the blades grow out of.
    parts.append(loft('Core_Hull', [(0, -3.5), (0, 2), (0, 7), (0, 10.4)], dict(
        z=[[0, -0.2], [0.25, -0.45], [1, -0.5]],
        ht=[[0, 0.6], [0.3, 1.4], [0.85, 1.45], [1, 1.3]],
        hb=[[0, 1.4], [0.3, 1.6], [0.7, 1.6], [0.85, 1.1], [1, 0.9]],
        capR=[[0, 2.0], [0.42, 2.2], [0.47, 4.3], [0.85, 4.4], [1, 3.0]]), axis=True))
    # Lower tail: the chevron keel under the top engine, between the lower engines.
    parts.append(loft('Tail_Keel', [(0, 6.0), (0, 9.5), (0, 12.3)], dict(
        z=[[0, -1.3], [0.6, -1.05], [1, -0.75]],
        ht=[[0, 0.5], [0.6, 0.3], [1, 0.08]], hb=[[0, 0.4], [0.6, 0.35], [1, 0.05]],
        capR=[[0, 1.2], [0.6, 1.0], [1, 0.3]]), axis=True))
    # Side blade: the long talon arm from the nose to the rear tip.
    parts.append(loft('Blade_Side', [(1.5, -11.95), (2.7, -9), (3.8, -6), (4.9, -3), (5.7, 0),
                                     (6.15, 3), (6.0, 6), (5.2, 8.8), (4.15, 11.55)], dict(
        z=[[0, -1.5], [0.15, -1.15], [0.4, -0.75], [0.55, -0.6], [0.8, -0.55], [0.9, -0.1], [1, 0.6]],
        ht=[[0, 0.03], [0.1, 0.35], [0.35, 0.55], [0.55, 1.3], [0.8, 1.45], [0.9, 0.7], [1, 0.03]],
        hb=[[0, 0.03], [0.1, 0.3], [0.35, 0.5], [0.55, 1.35], [0.8, 1.5], [0.9, 0.6], [1, 0.03]],
        k=[[0, -0.15], [0.45, -0.15], [0.58, 0.0], [1, 0.0]],
        kt=[[0, 0], [0.45, 0], [0.58, -0.14], [0.85, -0.14], [1, 0]],
        capL=[[0, 2.0], [1, 2.0]], capR=[[0, 2.4], [0.48, 2.4], [0.55, 1.5], [0.65, 1.4], [0.8, 2.2], [1, 2.0]]),
        glow=[(0.1, 0.5, 1, 0.25, 0.75, 4), (0.1, 0.45, -1, 0.25, 0.75, 4), (0.6, 0.88, 1, 0.25, 0.75, 4)]))
    # Swept spikes flaring out and back from the flanks.
    parts.append(loft('Spike_Lower', [(11.0, -5.45), (9.9, -3.3), (9.05, -1.0), (8.6, 1.2), (7.8, 3.2)], dict(
        z=[[0, -0.55], [0.5, -0.9], [1, -1.05]],
        ht=[[0, 0.02], [0.3, 0.2], [1, 0.3]], hb=[[0, 0.03], [0.2, 0.35], [0.5, 0.35], [1, 0.45]],
        k=[[0, 0.1], [1, 0.1]],
        capL=[[0, 0.9], [1, 1.0]], capR=[[0, 0.9], [1, 1.0]])))
    parts.append(loft('Spike_Upper', [(12.75, -0.42), (11.2, 0.95), (9.7, 2.5), (8.3, 4.1), (7.0, 5.7)], dict(
        z=[[0, 0.0], [0.5, -0.02], [1, 0.0]],
        ht=[[0, 0.02], [0.3, 0.17], [1, 0.3]], hb=[[0, 0.02], [0.3, 0.45], [1, 0.7]],
        k=[[0, 0.05], [1, 0.05]],
        capL=[[0, 1.0], [1, 1.3]], capR=[[0, 1.0], [1, 1.3]])))
    # Rear fin: small upswept spike between the crest tail and the side blade's rear tip.
    parts.append(loft('Fin_Rear', [(2.3, 12.05), (2.35, 10.6), (2.5, 9.0), (2.6, 7.5)], dict(
        z=[[0, 1.25], [1, 0.75]],
        ht=[[0, 0.02], [0.4, 0.15], [1, 0.3]], hb=[[0, 0.02], [0.4, 0.15], [1, 0.3]],
        capL=[[0, 0.8], [1, 0.8]], capR=[[0, 0.8], [1, 0.8]])))
    # Crest: low dorsal ridge along the rear centre, ending in the tail spike.
    parts.append(loft('Crest', [(0, 1.0), (0, 5), (0, 9), (0, 12.45)], dict(
        z=[[0, 0.95], [0.6, 1.15], [0.8, 1.2], [1, 1.5]],
        ht=[[0, 0.2], [0.25, 0.65], [0.55, 1.22], [0.8, 0.8], [1, 0.25]],
        hb=[[0, 0.3], [0.8, 0.3], [1, 0.08]],
        capR=[[0, 1.0], [0.3, 1.6], [0.7, 1.6], [0.85, 0.9], [1, 0.4]]), axis=True,
        glow=[(0.15, 0.75, 1, 0.25, 0.75, 3)]))
    # Pods: two domes on the upper rear hull (eye-like), with a glowing collar.
    for side in (1,):
        cx, cy = 3.45 * side, 7.0
        prof = [(1.15, 0.0, 1), (1.12, 0.12, 2), (0.98, 0.2, 0)]
        for k in range(1, 9):
            a = k / 8 * math.pi / 2
            prof.append((0.98 * math.cos(a), 0.2 + 0.4 * math.sin(a), 0))
        prof[-1] = (0.0, 0.6, 0)
        parts.append(revolve('Pod', (cx, cy, 0.38), (0, 0, 1), prof, seg=32))
    # Engines: triangle layout from the rear redraw (one top-centre, two lower).
    def engine(name, c, R, L, half=False):
        # nacelle shell (navy) -> pearl lip -> cyan ring -> navy recess -> thin inner cyan ring -> navy cone
        prof = [(0.0, -L, 1), (R * 0.9, -L, 1), (R, -L * 0.6, 1), (R, -0.35, 0), (R * 1.08, -0.1, 0),
                (R * 1.06, 0, 2), (R * 0.84, 0, 1), (R * 0.8, -0.1, 1), (R * 0.58, -0.3, 2),
                (R * 0.5, -0.32, 1), (R * 0.2, -0.15, 1), (0.0, -0.1, 1)]
        # profile order: outer shell (navy/pearl), front glow ring, recess, glowing core
        return revolve(name, c, (0, 1, 0), prof, seg=40, half=half)
    parts.append(engine('Engine_Top', (0, 10.95, 0.3), 1.0, 3.8, half=True))
    parts.append(engine('Engine_Lower', (2.75, 10.35, -0.85), 0.86, 3.3))
    # Curved cyan conduits sweeping outward from the lower engines.
    lines = []
    for dz, dy in ((0.25, 0.0), (0.0, -0.2), (-0.25, -0.4)):
        lines.append(bez((3.6, 9.9 + dy, -0.85 + dz), (5.2, 9.9 + dy, -0.85 + dz), (6.6, 7.6 + dy, -0.45 + dz * 0.6)))
    tubes = [tube('Conduit_%d' % i, l) for i, l in enumerate(lines)]
    T = Mesh('Engine_Conduits', mats=['Cyan_Glow'])
    for t in tubes:
        o = len(T.v); T.v += t.v; T.f += [[i + o for i in f] for f in t.f]; T.m += t.m
    parts.append(T)
    return parts

if __name__ == '__main__':
    parts = build()
    out = os.path.join(HERE, 'model_parts.json')
    json.dump([p.js() for p in parts], open(out, 'w'))
    print('parts', [(p.name, len(p.v), len(p.f)) for p in parts])
