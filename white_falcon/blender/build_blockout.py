import bpy, bmesh, json, math, os
from mathutils import Vector
D='/tmp/claude-0/bl'; S=json.load(open(f'{D}/silhouettes.json'))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene; sc.unit_settings.system='METRIC'; sc.unit_settings.scale_length=1.0
def coll(name):
    c=bpy.data.collections.new(name); sc.collection.children.link(c); return c
cref=coll('References'); cship=coll('Ship'); ccut=coll('Cutters')
# ---- reference images
def ref(name,img,rot):
    im=bpy.data.images.load(f'{D}/{img}'); im.pack()
    e=bpy.data.objects.new(name,None); cref.objects.link(e)
    e.empty_display_type='IMAGE'; e.data=im; e.empty_display_size=30.0
    e.empty_image_offset=(-0.5,-0.5); e.use_empty_image_alpha=True; e.color[3]=0.45
    e.empty_image_side='FRONT'; e.show_empty_image_perspective=False; e.show_empty_image_only_axis_aligned=True
    e.rotation_euler=[math.radians(a) for a in rot]; e.hide_select=True
ref('REF_Top','ref_top_clean.png',(0,0,0))
ref('REF_Right','ref_side_clean.png',(90,0,90))
ref('REF_Back','ref_back_clean.png',(90,0,180))
# ---- silhouette extrusions
def extr(name,polys,rot,depth,col):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='2D'; cu.fill_mode='BOTH'; cu.extrude=depth
    for p in polys:
        sp=cu.splines.new('POLY'); sp.points.add(len(p)-1)
        for i,(u,v) in enumerate(p): sp.points[i].co=(u,v,0,1)
        sp.use_cyclic_u=True
    o=bpy.data.objects.new(name,cu); col.objects.link(o); o.rotation_euler=[math.radians(a) for a in rot]
    bpy.context.view_layer.objects.active=o
    for ob in bpy.context.view_layer.objects: ob.select_set(False)
    o.select_set(True); bpy.ops.object.convert(target='MESH'); return bpy.context.view_layer.objects.active
hull=extr('WhiteFalcon_Blockout',S['top'],(0,0,0),6.0,cship)
cs=extr('Cut_Side',S['side'],(90,0,90),16.0,ccut)
cb=extr('Cut_Back',S['back'],(90,0,180),16.0,ccut)
for c in (cs,cb):
    m=hull.modifiers.new('Intersect_'+c.name,'BOOLEAN'); m.operation='INTERSECT'; m.object=c; m.solver='EXACT'
bpy.context.view_layer.objects.active=hull
for ob in bpy.context.view_layer.objects: ob.select_set(False)
hull.select_set(True)
for m in list(hull.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)
ccut.hide_viewport=True; ccut.hide_render=True
# ---- cut to +X half, add live Mirror so edits stay symmetric
bm=bmesh.new(); bm.from_mesh(hull.data)
geom=bm.verts[:]+bm.edges[:]+bm.faces[:]
bmesh.ops.bisect_plane(bm,geom=geom,plane_co=(0,0,0),plane_no=(1,0,0),clear_inner=True)
bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=0.002)
bm.to_mesh(hull.data); bm.free()
mm=hull.modifiers.new('Mirror','MIRROR'); mm.use_axis[0]=True; mm.use_clip=True; mm.use_mirror_merge=True
for p in hull.data.polygons: p.use_smooth=False
# ---- material
mat=bpy.data.materials.new('Pearl_Hull'); mat.use_nodes=True
b=mat.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value=(0.86,0.87,0.9,1); b.inputs['Metallic'].default_value=0.35; b.inputs['Roughness'].default_value=0.28
try: b.inputs['Coat Weight'].default_value=0.6
except: pass
hull.data.materials.append(mat)
print('faces',len(hull.data.polygons),'dims',tuple(round(x,2) for x in hull.dimensions))
# ---- preview camera/light (kept in file for convenience)
cam=bpy.data.cameras.new('Cam'); cam.type='ORTHO'; cam.ortho_scale=32
co=bpy.data.objects.new('Preview_Camera',cam); sc.collection.objects.link(co); sc.camera=co
sun=bpy.data.lights.new('Sun','SUN'); sun.energy=3.5; so=bpy.data.objects.new('Sun',sun); sc.collection.objects.link(so); so.rotation_euler=(math.radians(40),math.radians(15),math.radians(30))
w=bpy.data.worlds.new('World'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.05,0.055,0.065,1); w.node_tree.nodes['Background'].inputs[1].default_value=1.0
sc.render.engine='CYCLES'; sc.cycles.samples=24; sc.cycles.device='CPU'; sc.render.resolution_x=900; sc.render.resolution_y=700
sc.render.film_transparent=False
def shot(name,loc):
    co.location=Vector(loc); d=(Vector((0,0,0))-co.location); co.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=f'{D}/render_{name}.png'; bpy.ops.render.render(write_still=True)
shot('top',(0,0,40)); shot('threequarter',(-22,-24,14)); shot('side',(40,0,0)); shot('back',(0,40,3))
co.location=(-22,-24,14); co.rotation_euler=(Vector((0,0,0))-co.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=f'{D}/white_falcon_blockout.blend',compress=True)
print('saved')
