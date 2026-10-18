"""Original Blender build script; run with blender -b --python scripts/build_model.py.

Reads CC0 MakeHuman data, not MakeHuman application code. Blender 4.3+.
"""
from pathlib import Path
import json, math
import bpy
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
           ('torso/torso-muscle-dorsi-incr.target', 0.10),
           ('stomach/stomach-tone-incr.target', 0.10)]
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

skin=material('Skin',(.58,.345,.22),.60)
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

# Garments follow the real body topology and remain opaque. There is no undress control.
bra_ids=[];short_ids=[];hair_ids=[]
for i in body_faces:
    center=sum((verts[j] for j in faces[i]),Vector())/len(faces[i])
    x,y,z=center
    torso=abs(x)<1.50
    if torso and ((1.68<y<3.20 and z>0.05) or (1.68<y<2.14)):
        bra_ids.append(i)
    if -2.40<y<.12 and abs(x)<2.12: short_ids.append(i)
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

bra=shell('Sports_Bra',bra_ids,cloth,.006)
shorts=shell('Mid_Thigh_Shorts',short_ids,cloth,.006)
cap=shell('Hair_Cap',hair_ids,hair,.002)
sub=body.modifiers.new('Surface refinement','SUBSURF');sub.levels=2;sub.render_levels=2

# Separate smooth ribbons avoid stair-step straps inherited from face selection.
for side in [-1,1]:
    anchors=[Vector((side*.86,2.55,1.12)),Vector((side*.86,3.35,.9)),Vector((side*.86,4.02,.25)),Vector((side*.86,3.65,-.5)),Vector((side*.86,2.75,-.65)),Vector((side*.86,1.97,-.55))]
    path=[]
    for k in range(len(anchors)-1):
        p0=anchors[max(k-1,0)];p1=anchors[k];p2=anchors[k+1];p3=anchors[min(k+2,len(anchors)-1)]
        for step in range(16):
            t=step/16
            path.append((2*p1+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)*.5)
    path.append(anchors[-1])
    ribbon=[]
    for p in path:
        for j in range(5):ribbon.append(convert(p+Vector(((j-2)*.055,0,0))))
    rf=[]
    for i in range(len(path)-1):
        for j in range(4):rf.append([i*5+j,i*5+j+1,(i+1)*5+j+1,(i+1)*5+j])
    strap=make_mesh('Bra_Strap_'+str(side),ribbon,rf,mat=cloth)
    ss=strap.modifiers.new('Smooth ribbon','SUBSURF');ss.levels=1;ss.render_levels=1
    wrap=strap.modifiers.new('Follow shoulder','SHRINKWRAP');wrap.target=body;wrap.wrap_method='NEAREST_SURFACEPOINT';wrap.wrap_mode='ABOVE_SURFACE';wrap.offset=.009
    solid=strap.modifiers.new('Ribbon thickness','SOLIDIFY');solid.thickness=.0015;solid.offset=1

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
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/asian-female.blend'))
bpy.ops.export_scene.gltf(filepath=str(ROOT/'assets/asian-female.glb'),export_format='GLB',export_apply=True,export_cameras=False,export_lights=False,export_extras=True)

# Inspect the evaluated body rather than claiming subdivision created new anatomical information.
deps=bpy.context.evaluated_depsgraph_get();evaluated=body.evaluated_get(deps);mesh=evaluated.to_mesh()
mesh.calc_loop_triangles()
edge_counts={}
for poly in body.data.polygons:
    ids=list(poly.vertices)
    for a,b in zip(ids,ids[1:]+ids[:1]):
        key=tuple(sorted([a,b]));edge_counts[key]=edge_counts.get(key,0)+1
report={'body_height_m':1.65,'height_is_synthetic':True,'base_vertices':len(body.data.vertices),'base_faces':len(body.data.polygons),
        'evaluated_body_vertices':len(mesh.vertices),'evaluated_body_triangles':len(mesh.loop_triangles),
        'boundary_edges':sum(v==1 for v in edge_counts.values()),'nonmanifold_edges':sum(v>2 for v in edge_counts.values()),
        'targets':[{'file':n,'weight':w} for n,w in targets],
        'scope':'External surface only; mathematical topology checks, not professional anatomical validation.'}
(ROOT/'assets/model-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('MODEL_REPORT',json.dumps(report))
