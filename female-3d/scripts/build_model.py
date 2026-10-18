"""Original Blender build script; run with blender -b --python scripts/build_model.py.

Reads CC0 MakeHuman data, not MakeHuman application code. Blender 4.3+.
"""
from pathlib import Path
import json, math
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'assets/source'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def obj_data(path):
    verts, tex, faces, face_uv, groups = [], [], [], [], []
    group = ''
    for line in path.read_text().splitlines():
        a = line.split()
        if not a: continue
        if a[0] == 'v': verts.append(Vector(tuple(map(float, a[1:4]))))
        elif a[0] == 'vt': tex.append(tuple(map(float, a[1:3])))
        elif a[0] == 'g': group = a[1]
        elif a[0] == 'f':
            faces.append([int(x.split('/')[0])-1 for x in a[1:]])
            face_uv.append([int(x.split('/')[1])-1 if len(x.split('/'))>1 and x.split('/')[1] else 0 for x in a[1:]])
            groups.append(group)
    return verts, tex, faces, face_uv, groups

verts, uv, faces, fuv, groups = obj_data(DATA / '3dobjs/base.obj')
targets = [('macrodetails/asian-female-young.target', 1.0),
           ('macrodetails/universal-female-young-averagemuscle-averageweight.target', 1.0),
           ('macrodetails/universal-female-young-averagemuscle-maxweight.target', 0.18),
           ('breast/nipple-point-decr.target', 0.70),
           ('breast/nipple-size-decr.target', 0.65),
           ('armslegs/l-upperarm-shoulder-muscle-incr.target', 0.10),
           ('armslegs/r-upperarm-shoulder-muscle-incr.target', 0.10),
           ('torso/torso-muscle-dorsi-incr.target', 0.14),
           ('stomach/stomach-tone-incr.target', 0.08)]
for name, weight in targets:
    for line in (DATA / 'targets' / name).read_text().splitlines():
        a = line.split()
        if a and not a[0].startswith('#'):
            verts[int(a[0])] += Vector(tuple(float(x)*weight for x in a[1:4]))

body_faces = [i for i,g in enumerate(groups) if g == 'body']
body_indices = sorted({j for i in body_faces for j in faces[i]})
low = min(verts[j].y for j in body_indices)
high = max(verts[j].y for j in body_indices)
scale = 1.65 / (high-low)
def convert(v): return (v.x*scale, -v.z*scale, (v.y-low)*scale)

def material(name, color, rough=.6):
    m=bpy.data.materials.new(name);m.use_nodes=True
    bsdf=m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(*color,1)
    bsdf.inputs['Roughness'].default_value=rough
    if name=='Skin':
        bsdf.inputs['Subsurface Weight'].default_value=.09
    return m

skin=material('Skin and flush sportswear',(1,1,1),.62)
skin.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value=.07
cloth=material('Clinical sportswear',(.105,.135,.155),.9)
hair=material('Black hair',(.018,.013,.010),.47)
lip=material('Natural lips',(.40,.19,.145),.65)

def make_mesh(name, v, f, tex=None, indices=None, mat=None):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(v,[],f);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    if mat: mesh.materials.append(mat)
    if tex and indices:
        layer=mesh.uv_layers.new(name='UVMap')
        for poly, coords in zip(mesh.polygons,indices):
            for li, ui in zip(poly.loop_indices,coords): layer.data[li].uv=tex[ui]
    for p in mesh.polygons: p.use_smooth=True
    return ob

mapping={j:i for i,j in enumerate(body_indices)}
body=make_mesh('Female_Surface', [convert(verts[j]) for j in body_indices],
               [[mapping[j] for j in faces[i]] for i in body_faces],uv,[fuv[i] for i in body_faces],skin)
body['description']='Adult female with MakeHuman Asian appearance target. Synthetic 1.65 m body, not a scan or medical measurement.'

# Preserve an editable low-poly source, but export only its refined render mesh.
source_body=body;source_body.name='SOURCE_LowPoly_Female'
sub=source_body.modifiers.new('Surface refinement','SUBSURF');sub.levels=2;sub.render_levels=2
deps=bpy.context.evaluated_depsgraph_get()
render_mesh=bpy.data.meshes.new_from_object(source_body.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
body=bpy.data.objects.new('Female_Surface',render_mesh);bpy.context.collection.objects.link(body)
body['clothing']='Opaque vertex-color sportswear on the exact same surface: zero extra clothing thickness or displacement.'
source_body.hide_render=True;source_body.hide_set(True)

# Clothing is a smooth material boundary on the body, not offset geometry.
# This guarantees zero floating hems, zero fabric thickness and no simulated folds.
positions=np.empty((len(render_mesh.vertices),3),dtype=np.float32)
render_mesh.vertices.foreach_get('co',positions.reshape(-1))
x=positions[:,0]/scale;y=positions[:,2]/scale+low;z=-positions[:,1]/scale
def smooth01(v):
    t=np.clip(v,0,1);return t*t*(3-2*t)
def band(v,lo,hi,edge=.03):return smooth01((v-lo)/edge)*smooth01((hi-v)/edge)
front=smooth01((z+.04)/.12)
torso=smooth01((1.56-np.abs(x))/.05)
neckline=3.52-.48*np.exp(-np.power(x/.76,4))
bra_front=smooth01((y-1.68)/.03)*smooth01((neckline-y)/.03)*front
bra_back=band(y,1.68,2.12)*(1-front)
straps=band(np.abs(x),.73,.98)*band(y,1.98,4.60)
bra_mask=np.maximum(bra_front+bra_back,straps)*torso
short_mask=band(y,-2.40,.14)*smooth01((2.20-np.abs(x))/.04)
clothing=np.maximum(bra_mask,short_mask)
skin_rgb=np.array([.58,.345,.22],dtype=np.float32)
cloth_rgb=np.array([.105,.135,.155],dtype=np.float32)
rgba=np.ones((len(positions),4),dtype=np.float32)
rgba[:,:3]=skin_rgb[None,:]*(1-clothing[:,None])+cloth_rgb[None,:]*clothing[:,None]
color=render_mesh.color_attributes.new(name='SurfaceColor',type='FLOAT_COLOR',domain='POINT')
color.data.foreach_set('color',rgba.reshape(-1))
attr=skin.node_tree.nodes.new('ShaderNodeVertexColor');attr.layer_name='SurfaceColor'
# Bake the analytical coverage at texel positions, avoiding vertex-interpolation
# stair steps along hems. Point colors remain only as editable diagnostic data.
nodes=skin.node_tree.nodes;links=skin.node_tree.links
def value_node(operation,a,b=None):
    node=nodes.new('ShaderNodeMath');node.operation=operation
    for socket,v in zip(node.inputs,[a,b]):
        if v is None:continue
        if isinstance(v,(int,float)):socket.default_value=v
        else:links.new(v,socket)
    return node.outputs[0]
def node_smooth(v):
    t=value_node('MINIMUM',1,value_node('MAXIMUM',0,v))
    return value_node('MULTIPLY',value_node('MULTIPLY',t,t),value_node('SUBTRACT',3,value_node('MULTIPLY',2,t)))
def node_band(v,lo,hi,edge=.03):
    return value_node('MULTIPLY',node_smooth(value_node('DIVIDE',value_node('SUBTRACT',v,lo),edge)),node_smooth(value_node('DIVIDE',value_node('SUBTRACT',hi,v),edge)))
geometry=nodes.new('ShaderNodeNewGeometry');separate=nodes.new('ShaderNodeSeparateXYZ');links.new(geometry.outputs['Position'],separate.inputs[0])
px=value_node('DIVIDE',separate.outputs['X'],scale)
py=value_node('ADD',value_node('DIVIDE',separate.outputs['Z'],scale),low)
pz=value_node('DIVIDE',separate.outputs['Y'],-scale)
absx=value_node('ABSOLUTE',px)
f=node_smooth(value_node('DIVIDE',value_node('ADD',pz,.04),.12))
torso_node=node_smooth(value_node('DIVIDE',value_node('SUBTRACT',1.56,absx),.05))
exponent=value_node('MULTIPLY',-1,value_node('POWER',value_node('DIVIDE',px,.76),4))
neckline_node=value_node('SUBTRACT',3.52,value_node('MULTIPLY',.48,value_node('POWER',math.e,exponent)))
front_node=value_node('MULTIPLY',value_node('MULTIPLY',node_smooth(value_node('DIVIDE',value_node('SUBTRACT',py,1.68),.03)),node_smooth(value_node('DIVIDE',value_node('SUBTRACT',neckline_node,py),.03))),f)
back_node=value_node('MULTIPLY',node_band(py,1.68,2.12),value_node('SUBTRACT',1,f))
strap_node=value_node('MULTIPLY',node_band(absx,.73,.98),node_band(py,1.98,4.60))
bra_node=value_node('MULTIPLY',value_node('MAXIMUM',value_node('ADD',front_node,back_node),strap_node),torso_node)
short_node=value_node('MULTIPLY',node_band(py,-2.4,.14),node_smooth(value_node('DIVIDE',value_node('SUBTRACT',2.20,absx),.04)))
mask_node=value_node('MAXIMUM',bra_node,short_node)
mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';links.new(mask_node,mix.inputs[0]);mix.inputs[1].default_value=(*skin_rgb,1);mix.inputs[2].default_value=(*cloth_rgb,1)
emission=nodes.new('ShaderNodeEmission');links.new(mix.outputs[0],emission.inputs['Color'])
output=nodes.get('Material Output');links.new(emission.outputs[0],output.inputs['Surface'])
albedo=bpy.data.images.new('Seamless sportswear color 4K',width=4096,height=4096,alpha=False)
bake_node=nodes.new('ShaderNodeTexImage');bake_node.image=albedo;nodes.active=bake_node
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.context.scene.render.engine='CYCLES';bpy.context.scene.cycles.samples=1;bpy.context.scene.render.bake.margin=12
bpy.ops.object.bake(type='EMIT')
albedo.filepath_raw=str(ROOT/'assets/skin-sportswear-albedo-4k.png');albedo.file_format='PNG';albedo.save();albedo.pack()
links.new(bake_node.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])
links.new(nodes.get('Principled BSDF').outputs[0],output.inputs['Surface'])

# Original 4K procedural tangent normal texture. Microtexture only, not anatomy.
resolution=4096
rng=np.random.default_rng(20261018)
noise=rng.standard_normal((resolution,resolution),dtype=np.float32)
height=(noise+np.roll(noise,1,0)+np.roll(noise,-1,0)+np.roll(noise,1,1)+np.roll(noise,-1,1))/5
nx=(np.roll(height,1,1)-np.roll(height,-1,1))*.027
ny=(np.roll(height,1,0)-np.roll(height,-1,0))*.027
normal_pixels=np.ones((resolution,resolution,4),dtype=np.float32)
normal_pixels[:,:,0]=nx*.5+.5;normal_pixels[:,:,1]=ny*.5+.5
normal_pixels[:,:,2]=np.sqrt(np.clip(1-nx*nx-ny*ny,0,1))*.5+.5
normal_image=bpy.data.images.new('Original skin micro-normal 4K',width=resolution,height=resolution,alpha=False)
normal_image.colorspace_settings.name='Non-Color';normal_image.pixels.foreach_set(normal_pixels.reshape(-1))
normal_image.filepath_raw=str(ROOT/'assets/skin-micro-normal-4k.png');normal_image.file_format='PNG';normal_image.save();normal_image.pack()
texture=skin.node_tree.nodes.new('ShaderNodeTexImage');texture.image=normal_image
normal_node=skin.node_tree.nodes.new('ShaderNodeNormalMap');normal_node.inputs['Strength'].default_value=.35
skin.node_tree.links.new(texture.outputs['Color'],normal_node.inputs['Color'])
skin.node_tree.links.new(normal_node.outputs['Normal'],skin.node_tree.nodes.get('Principled BSDF').inputs['Normal'])
del noise,height,nx,ny,normal_pixels,positions,rgba

# Hair is still a separate close-fitting shell; garments are not.
hair_ids=[]
for i in body_faces:
    center=sum((verts[j] for j in faces[i]),Vector())/len(faces[i])
    x,y,z=center
    if y>6.12 or (y>5.75 and z<.47) or (y>5.35 and z<-.04): hair_ids.append(i)

def shell(name, ids, mat, offset):
    used=sorted({j for i in ids for j in faces[i]}); remap={j:i for i,j in enumerate(used)}
    ob=make_mesh(name,[convert(verts[j]) for j in used],[[remap[j] for j in faces[i]] for i in ids],mat=mat)
    # Relax the boundary independently to avoid staircase-shaped garment/hair edges.
    counts={}
    for poly in ob.data.polygons:
        ids=list(poly.vertices)
        for a,b in zip(ids,ids[1:]+ids[:1]):
            edge=tuple(sorted([a,b]));counts[edge]=counts.get(edge,0)+1
    neighbors={}
    for (a,b),n in counts.items():
        if n==1:
            neighbors.setdefault(a,[]).append(b);neighbors.setdefault(b,[]).append(a)
    for _ in range(16):
        new={i:ob.data.vertices[i].co*.5+sum((ob.data.vertices[j].co for j in ns),Vector())*(.5/len(ns)) for i,ns in neighbors.items()}
        for i,p in new.items():ob.data.vertices[i].co=p
    smooth=ob.modifiers.new('Relax fabric','SMOOTH');smooth.factor=.7;smooth.iterations=4
    sub=ob.modifiers.new('Smooth fabric surface','SUBSURF');sub.levels=2;sub.render_levels=2
    wrap=ob.modifiers.new('Fit to refined body','SHRINKWRAP');wrap.target=body;wrap.wrap_method='NEAREST_SURFACEPOINT';wrap.wrap_mode='ABOVE_SURFACE';wrap.offset=offset
    solid=ob.modifiers.new('Garment thickness','SOLIDIFY');solid.thickness=.0015;solid.offset=1
    return ob

cap=shell('Hair_Cap',hair_ids,hair,.002)

# Fit the bundled CC0 eye asset through its barycentric proxy attachment data.
ev, et, ef, eu, eg=obj_data(DATA/'eyes/high-poly/high-poly.obj')
spec=(DATA/'eyes/high-poly/high-poly.mhclo').read_text().splitlines()
scales={}
for l in spec:
    a=l.split()
    if a and a[0] in ['x_scale','y_scale','z_scale']:
        scales[a[0][0]]=abs(verts[int(a[1])]['xyz'.index(a[0][0])]-verts[int(a[2])]['xyz'.index(a[0][0])])/float(a[3])
rows=[];reading=False
for l in spec:
    a=l.split()
    if a and a[0]=='verts': reading=True;continue
    if reading:
        if not a or a[0].startswith('#'): continue
        if not a[0].isdigit(): break
        rows.append(a)
eye_v=[]
for a in rows[:len(ev)]:
    v=sum((verts[int(a[k])]*float(a[k+3]) for k in range(3)),Vector())
    v+=Vector((float(a[6])*scales['x'],float(a[7])*scales['y'],float(a[8])*scales['z']))
    eye_v.append(convert(v))
eye_mat=material('Eyes',(.85,.82,.74),.3)
nodes=eye_mat.node_tree.nodes
image=nodes.new('ShaderNodeTexImage');image.image=bpy.data.images.load(str(DATA/'eyes/materials/brown_eye.png'));image.image.pack()
eye_mat.node_tree.links.new(image.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])
eye_mat.node_tree.links.new(image.outputs['Alpha'],nodes.get('Principled BSDF').inputs['Alpha'])
eye_mat.surface_render_method='DITHERED'
eyes=make_mesh('Eyes',eye_v,ef,et,eu,eye_mat)

bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=32,location=(0,.096,1.584))
bun=bpy.context.object;bun.name='Hair_Bun';bun.scale=(.052,.045,.05);bun.data.materials.append(hair)
for p in bun.data.polygons:p.use_smooth=True

# Save editable source with non-destructive subdivision; export evaluated geometry to GLB.
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene['status']='Surface concept. No internal bones, no clinical calibration, no professional anatomical approval.'
scene['asset_source']='MakeHuman CC0 assets at a8bc2d54ff0ac92e78ff71431b1023eda42bf482'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/asian-female.blend'),compress=True)
bpy.ops.object.select_all(action='DESELECT')
for ob in scene.objects:
    if ob.type=='MESH' and ob!=source_body:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'assets/asian-female.glb'),export_format='GLB',use_selection=True,export_apply=True,export_vertex_color='NONE',export_tangents=True,export_cameras=False,export_lights=False,export_extras=True)

# Inspect the evaluated body rather than claiming subdivision created new anatomical information.
deps=bpy.context.evaluated_depsgraph_get();evaluated=body.evaluated_get(deps);mesh=evaluated.to_mesh()
mesh.calc_loop_triangles()
edge_counts={}
for poly in source_body.data.polygons:
    ids=list(poly.vertices)
    for a,b in zip(ids,ids[1:]+ids[:1]):
        key=tuple(sorted([a,b]));edge_counts[key]=edge_counts.get(key,0)+1
report={'revision':3,'body_height_m':1.65,'height_is_synthetic':True,'base_vertices':len(source_body.data.vertices),'base_faces':len(source_body.data.polygons),
        'evaluated_body_vertices':len(mesh.vertices),'evaluated_body_triangles':len(mesh.loop_triangles),
        'boundary_edges':sum(v==1 for v in edge_counts.values()),'nonmanifold_edges':sum(v>2 for v in edge_counts.values()),
        'targets':[{'file':n,'weight':w} for n,w in targets],
        'clothing_method':'Analytical garment coverage baked to 4K albedo on the exact body surface; no separate garment mesh.',
        'garment_offset_m':0,'garment_thickness_m':0,'micro_normal_pixels':[4096,4096],'albedo_pixels':[4096,4096],
        'scope':'External surface only; mathematical topology checks, not professional anatomical validation.'}
(ROOT/'assets/model-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('MODEL_REPORT',json.dumps(report))
