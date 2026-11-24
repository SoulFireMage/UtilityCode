"""Build white_falcon_model.blend from model_parts.json (Blender 5.2, headless).

  blender -b -P build_model.py                 # build, render checks + beauty, save, export GLB
  blender -b -P build_model.py -- --no-render  # build + save + export only
Reference image empties are taken from white_falcon_blockout.blend (packed).
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(bpy.data.filepath or __file__)) if False else os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.join(HERE, 'renders'); os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'white_falcon_blockout.blend'))
sc = bpy.context.scene
for ob in list(bpy.data.objects):
    if not ob.name.startswith('REF_'):
        bpy.data.objects.remove(ob, do_unlink=True)
for c in list(bpy.data.collections):
    if c.name not in ('References',):
        bpy.data.collections.remove(c)
for m in list(bpy.data.meshes) + list(bpy.data.curves):
    if m.users == 0: (bpy.data.meshes if isinstance(m, bpy.types.Mesh) else bpy.data.curves).remove(m)
ship = bpy.data.collections.new('Ship'); sc.collection.children.link(ship)
stage = bpy.data.collections.new('Stage'); sc.collection.children.link(stage)

# ---------------------------------------------------------------- materials
def principled(name, base, metal, rough, coat=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*base, 1)
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = coat
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = strength
    return m
MATS = {
    'Pearl_Hull': principled('Pearl_Hull', (0.72, 0.73, 0.76), 0.2, 0.3, coat=0.6),
    'Navy_Recess': principled('Navy_Recess', (0.015, 0.028, 0.07), 0.6, 0.35),
    'Cyan_Glow': principled('Cyan_Glow', (0.0, 0.45, 0.8), 0.0, 0.3, emit=(0.0, 0.62, 1.0), strength=5.0),
}
for n, m in MATS.items():
    m.diffuse_color = {'Pearl_Hull': (0.85, 0.86, 0.88, 1), 'Navy_Recess': (0.03, 0.05, 0.12, 1), 'Cyan_Glow': (0.1, 0.8, 1, 1)}[n]

# ---------------------------------------------------------------- parts
centre = bpy.data.objects.new('Mirror_Centre', None); ship.objects.link(centre)
centre.empty_display_type = 'ARROWS'; centre.empty_display_size = 1.0
parts = json.load(open(os.path.join(HERE, 'model_parts.json')))
stats = {}
for p in parts:
    me = bpy.data.meshes.new(p['name'])
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in p['verts']]
    bm.verts.ensure_lookup_table()
    for f, mi in zip(p['faces'], p['mat']):
        try:
            face = bm.faces.new([vs[i] for i in f]); face.material_index = mi; face.smooth = True
        except ValueError:
            pass   # duplicate face
    sharp = {frozenset(e) for e in p['sharp']}
    bm.edges.ensure_lookup_table()
    for e in bm.edges:
        if frozenset((e.verts[0].index, e.verts[1].index)) in sharp: e.smooth = False
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-5)
    if p['bisect']:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(1, 0, 0), clear_inner=True)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for mn in p['mats']: me.materials.append(MATS[mn])
    ob = bpy.data.objects.new(p['name'], me); ship.objects.link(ob)
    # origin: part centre (kept on X=0 for centreline parts so scaling stays symmetric)
    xs = [v.co for v in me.vertices]
    c = Vector([(min(v[i] for v in xs) + max(v[i] for v in xs)) / 2 for i in range(3)])
    if p['axis'] or p['bisect']: c.x = 0.0
    me.transform(__import__('mathutils').Matrix.Translation(-c)); ob.location = c
    mm = ob.modifiers.new('Mirror', 'MIRROR'); mm.use_axis = (True, False, False)
    mm.mirror_object = centre; mm.use_mirror_merge = True; mm.merge_threshold = 0.002
    mm.use_clip = bool(p['axis'] or p['bisect'])
    wn = ob.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL'); wn.keep_sharp = True; wn.mode = 'FACE_AREA_WITH_ANGLE'
    stats[p['name']] = len(me.polygons)

dg = bpy.context.evaluated_depsgraph_get()
tris = 0
for ob in ship.objects:
    if ob.type == 'MESH':
        e = ob.evaluated_get(dg); m = e.to_mesh(); m.calc_loop_triangles(); tris += len(m.loop_triangles); e.to_mesh_clear()
xs = []
for ob in ship.objects:
    if ob.type == 'MESH':
        e = ob.evaluated_get(dg); m = e.to_mesh()
        xs += [ob.matrix_world @ v.co for v in m.vertices]; e.to_mesh_clear()
dims = [round(max(v[i] for v in xs) - min(v[i] for v in xs), 2) for i in range(3)]
print('STATS', json.dumps(dict(tris=tris, dims=dims, faces=stats)))

# ---------------------------------------------------------------- render setup (GPU)
sc.render.engine = 'CYCLES'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for dev in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = dev; prefs.get_devices()
            for d in prefs.devices: d.use = True
            sc.cycles.device = 'GPU'; print('GPU', dev); break
        except Exception as ex:
            print('GPU fail', dev, ex)
except Exception as ex:
    print('no cycles prefs', ex)

world = bpy.data.worlds.get('World') or bpy.data.worlds.new('World'); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']

cam_d = bpy.data.cameras.new('Camera'); cam = bpy.data.objects.new('Camera', cam_d); stage.objects.link(cam); sc.camera = cam
cam_d.clip_end = 200

def look(loc, target=(0, 0, 0)):
    cam.location = Vector(loc); cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()

def ortho(view):
    cam_d.type = 'ORTHO'; cam_d.ortho_scale = 30
    if view == 'top': cam.location = (0, 0, 60); cam.rotation_euler = (0, 0, 0)
    if view == 'right': cam.location = (60, 0, 0); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    if view == 'back': cam.location = (0, 60, 0); cam.rotation_euler = (math.radians(90), 0, math.radians(180))

if '--no-render' not in ARGS:
    # silhouettes: flat white on black
    white = bpy.data.materials.new('SIL_White'); white.use_nodes = True
    nt = white.node_tree; nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 1.0
    out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(em.outputs[0], out.inputs[0])
    vl = sc.view_layers[0]; vl.material_override = white
    bg.inputs[0].default_value = (0, 0, 0, 1); bg.inputs[1].default_value = 0
    sc.render.resolution_x = sc.render.resolution_y = 1200; sc.render.resolution_percentage = 100
    sc.cycles.samples = 4; sc.cycles.use_denoising = False; sc.render.filter_size = 0.01
    sc.view_settings.view_transform = 'Standard'; sc.render.film_transparent = False
    for v in ('top', 'right', 'back'):
        ortho(v); sc.render.filepath = os.path.join(OUT, f'sil_{v}.png'); bpy.ops.render.render(write_still=True)
    vl.material_override = None; bpy.data.materials.remove(white)

# beauty lighting (kept in the file for the user)
def light(name, kind, loc, energy, size=5.0, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    if kind == 'AREA': ld.size = size
    o = bpy.data.objects.new(name, ld); stage.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
light('Key', 'AREA', (-18, -20, 22), 18000, 14)
light('Rim', 'AREA', (20, 26, 10), 12000, 10, (0.7, 0.85, 1.0))
light('Fill', 'AREA', (24, -10, -6), 3000, 12, (0.85, 0.9, 1.0))
bg.inputs[0].default_value = (0.012, 0.016, 0.028, 1); bg.inputs[1].default_value = 1.0
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy' if 'AgX - Punchy' in [i.identifier for i in sc.view_settings.bl_rna.properties['look'].enum_items] else 'None'
cam_d.type = 'PERSP'; cam_d.lens = 50
sc.render.resolution_x, sc.render.resolution_y = 1600, 1000
if '--no-render' not in ARGS:
    sc.cycles.samples = 256; sc.cycles.use_denoising = True; sc.render.filter_size = 1.5
    for name, loc, tgt in (('beauty_34', (-30, -36, 21), (0, -1, -0.5)), ('beauty_rear', (7, 40, 6), (0, 3, -0.3))):
        look(loc, tgt); sc.render.filepath = os.path.join(OUT, f'{name}.png'); bpy.ops.render.render(write_still=True)
look((-30, -36, 21), (0, -1, -0.5))

# ---------------------------------------------------------------- save + export
for area in []: pass
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'white_falcon_model.blend'), compress=True)
for o in bpy.context.view_layer.objects: o.select_set(o.users_collection[0] == ship and o.type == 'MESH')
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, 'white_falcon_model.glb'), export_format='GLB',
                          use_selection=True, export_apply=True, export_yup=True)
print('DONE')
