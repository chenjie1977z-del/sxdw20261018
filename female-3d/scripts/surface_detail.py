"""Original, approximate external surface sculpt and procedural hair/face meshes.

Coordinates in sculpt fields follow the CC0 base asset (x lateral, y up,
z anterior). These are authored visual cues, not measured clinical landmarks.
"""
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def sculpt_surface(body, scale, low):
    mesh=body.data
    positions=np.empty((len(mesh.vertices),3),np.float32)
    mesh.vertices.foreach_get('co',positions.reshape(-1))
    x=positions[:,0]/scale; y=positions[:,2]/scale+low; z=-positions[:,1]/scale
    a=np.abs(x)
    def g(v,w):return np.exp(-(v/w)**2)
    def smooth(t):
        t=np.clip(t,0,1);return t*t*(3-2*t)
    def interval(v,lo,hi,w=.12):return smooth((v-lo)/w)*smooth((hi-v)/w)
    front=smooth((z-.03)/.35);back=smooth((-z-.03)/.28)
    # Gentle S-shaped clavicular relief with shallow adjacent fossae.
    t=np.clip((a-.10)/1.25,0,1)
    clav_y=3.98+.11*np.sin(math.pi*t)-.045*np.sin(2*math.pi*t)
    span=interval(a,.10,1.40,.16)
    anterior=.036*g(y-clav_y,.065)*span
    anterior-=.026*g(y-(clav_y+.15),.115)*span
    anterior-=.021*g(y-(clav_y-.16),.13)*span
    # SCM runs obliquely from sternoclavicular area toward mastoid region.
    neck_t=np.clip((y-4.03)/.96,0,1)
    neck_x=.12+.42*neck_t
    anterior+=.028*g(a-neck_x,.065)*interval(y,4.00,4.99,.16)
    anterior-=.019*g(x,.15)*g(y-4.02,.10)
    # Quadriceps: soft rectus and distal vastus medialis volumes.
    anterior+=.027*g(a-.99,.25)*g(y+2.75,.87)*interval(y,-3.95,-1.65,.25)
    anterior+=.022*g(a-.77,.17)*g(y+3.70,.30)
    # Scapular spine and medial border remain under intact soft tissue.
    u=np.clip((a-.48)/.86,0,1)
    scap_y=3.48+.20*np.sin(math.pi*u*.72)
    posterior=.030*g(y-scap_y,.08)*interval(a,.45,1.40,.16)
    medial_x=.53+.10*(3.45-y)
    posterior+=.021*g(a-medial_x,.09)*interval(y,2.12,3.58,.25)
    posterior+=.022*g(a-.66,.14)*g(y-2.16,.17)
    posterior-=.014*g(a-.29,.16)*g(y-2.98,.55)
    # Paired shallow lumbar dimples and subtle paraspinal transition.
    posterior-=.032*g(a-.49,.14)*g(y-.10,.17)
    posterior+=.013*g(a-.20,.14)*g(y-1.45,.66)
    # Shallow normal skin folds, authored for this neutral A-pose only.
    radius=np.sqrt((x/.085)**2+((y-1.01)/.105)**2)
    anterior+=.004*g(radius-1,.30)*g(z-1.32,.28)
    anterior-=.014*g(x,.050)*g(y-1.01,.070)*g(z-1.32,.28)
    anterior+=.012*g(a-1.25,.20)*g(y+4.25,.25)
    anterior-=.005*g(y+4.05+.13*(a-1.25)**2,.025)*g(a-1.25,.36)
    posterior-=.012*g(y+4.27-.10*(a-1.25)**2,.035)*g(a-1.25,.40)
    axilla_y=3.10+.72*(a-1.42)
    anterior-=.006*g(y-axilla_y,.036)*g(a-1.53,.15)*g(z-.60,.30)
    displacement=(-anterior*front+posterior*back)*scale
    positions[:,1]+=displacement
    # Relax the neutral open-mouth rest pose toward a narrow natural lip seam.
    lip_gate=g(x,.33)**4*np.exp(-((y-5.13)/.22)**4)*smooth((z-1.05)/.15)
    lip_lift=(-.008*np.tanh((y-5.13)/.05)*lip_gate+.032*g(a-.26,.12)*g(y-5.17,.18)*smooth((z-1.10)/.15))*scale
    positions[:,2]+=lip_lift
    # Palmar wrist creases are shallow surface depressions, never dark ink lines.
    wrist_t=(a-3.92)*.57-(y-.93)*.69+(z-1.50)*.45
    wrist_gate=g(a-3.92,.28)*g(y-.93,.30)*g(z-1.39,.24)*smooth((1.50-z)/.10)
    wrist_depth=(.007*g(wrist_t,.022)+.0045*g(wrist_t-.065,.020))*wrist_gate*scale
    normals=np.empty_like(positions);mesh.vertices.foreach_get('normal',normals.reshape(-1));positions-=normals*wrist_depth[:,None]
    mesh.vertices.foreach_set('co',positions.reshape(-1));mesh.update()
    body['surface_detail']='Authored gentle clavicular, SCM, scapular, lumbar and quadriceps surface relief; not clinical calibration.'
    return {'method':'Smooth analytic displacement of refined continuous body mesh',
            'regions':['clavicles','supraclavicular fossae','infraclavicular fossae','sternocleidomastoid relief','scapular spine and medial border relief','lumbar dimples','quadriceps relief','umbilicus','patellar contour','popliteal crease','palmar wrist creases','anterior axillary fold'],
            'max_absolute_displacement_m':float(np.max(np.hypot(displacement,lip_lift))),
            'professionally_validated':False}


class Strands:
    """Combine tapered closed sweep tubes into a single small mesh per material."""
    def __init__(self):self.vertices=[];self.faces=[]
    def add(self, points, radii, sides=7):
        points=[Vector(p) for p in points];offset=len(self.vertices)
        for i,p in enumerate(points):
            tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
            axis=Vector((0,0,1))
            if abs(tangent.dot(axis))>.92:axis=Vector((1,0,0))
            n=tangent.cross(axis).normalized();b=tangent.cross(n).normalized()
            for k in range(sides):
                angle=2*math.pi*k/sides
                self.vertices.append(tuple(p+float(radii[i])*(n*math.cos(angle)+b*math.sin(angle))))
        for i in range(len(points)-1):
            for k in range(sides):
                a=offset+i*sides+k;c=offset+i*sides+(k+1)%sides
                self.faces.append((a,c,c+sides,a+sides))
        self.faces.append(tuple(offset+k for k in reversed(range(sides))))
        self.faces.append(tuple(offset+(len(points)-1)*sides+k for k in range(sides)))
    def mesh(self,name,make_mesh,mat):
        return make_mesh(name,self.vertices,self.faces,mat=mat)


def add_face_and_hair(body, cap, hair, scale, low, make_mesh, material):
    mesh=body.data
    bvh=BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons])
    def point(x,y,z):return Vector((x*scale,-z*scale,(y-low)*scale))
    def skin_point(x,y,offset=.001):
        origin=point(x,y,4)
        hit,normal,_,_=bvh.ray_cast(origin,Vector((0,1,0)),1)
        if hit is None:raise ValueError(f'Face attachment missed body at {x},{y}')
        return hit+normal*offset
    # Continuous scalp sampling removes stair-stepped face-selection boundaries.
    scalp_v=[];scalp_f=[];columns=160;rows=38
    origin=point(0,6.02,.30)
    for j in range(columns):
        angle=2*math.pi*j/columns
        c=math.cos(angle)
        hairline_y=5.80+(.46 if c>=0 else .32)*c+.035*math.cos(2*angle)-.035*math.exp(-(math.sin(angle)/.18)**2)*max(0,c)
        def scalp_at(phi):
            direction=Vector((math.sin(phi)*math.sin(angle),-math.sin(phi)*math.cos(angle),math.cos(phi)))
            hit,normal,_,_=bvh.ray_cast(origin,direction,1)
            if hit is None:raise ValueError('Scalp ray missed')
            return hit+normal*.0022
        lo_phi=.01;hi_phi=2.7
        for _ in range(19):
            mid=(lo_phi+hi_phi)/2
            if scalp_at(mid).z/scale+low>hairline_y:lo_phi=mid
            else:hi_phi=mid
        for k in range(rows):scalp_v.append(tuple(scalp_at(.003+(hi_phi-.003)*k/(rows-1))))
    for j in range(columns):
        for k in range(rows-1):
            a=j*rows+k;b=((j+1)%columns)*rows+k
            # A narrow sagittal part reveals the underlying scalp instead of painted hair.
            scalp_f.append((a,b,b+1,a+1))
    scalp_f.append(tuple(j*rows for j in reversed(range(columns))))
    new_cap=make_mesh('Continuous scalp',scalp_v,scalp_f,mat=hair)
    import bpy
    bpy.data.objects.remove(cap,do_unlink=True);new_cap.name='Hair_Cap'
    hair.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.64
    # Fine, swept-back strands share the scalp cap sampling; a center part stays visible.
    strokes=Strands()
    for j in range(columns):
        if j in [0,79,80,159]:continue
        # Long shallow sweeps give readable hair flow at face close-up, no fringe.
        pts=[Vector(scalp_v[j*rows+k]) for k in range(3,rows)]
        for p in pts:
            direction=(p-origin).normalized();p+=direction*.00022
        strokes.add(pts,[.000045+.000010*math.sin(j*2.4)]*len(pts),5)
    strokes.mesh('Hair_Fine_Strokes',make_mesh,hair)
    part_mat=material('Scalp at center part',(.43,.25,.17),.9)
    part_points=[Vector(scalp_v[k]) for k in reversed(range(1,rows))]+[Vector(scalp_v[80*rows+k]) for k in range(1,rows-5)]
    part_v=[]
    for p in part_points:
        p=p+(p-origin).normalized()*.00012
        part_v.extend([tuple(p+Vector((-.00030,0,0))),tuple(p+Vector((.00030,0,0)))])
    make_mesh('Natural_Center_Part',part_v,[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(part_points)-1)],mat=part_mat)
    # Small upper dental arch, positioned inside the existing lip opening.
    # These are original visual forms, not a dental anatomy or treatment model.
    tooth_mat=material('Natural ivory teeth',(.74,.72,.65),.38)
    teeth=[]
    widths=[.045,.060,.075,.075,.060,.045];cursor=-sum(widths)/2
    for i,w in enumerate(widths):
        x=cursor+w/2;cursor+=w
        y=5.166+.9*x*x;front=1.312-2.2*x*x;angle=math.atan(4.4*x)
        import bpy
        bpy.ops.mesh.primitive_cube_add(size=1,location=point(x-math.sin(angle)*.020,y,front-math.cos(angle)*.020))
        ob=bpy.context.object;ob.name='Upper tooth';ob.rotation_euler.z=angle
        ob.dimensions=((w-.003)*scale,.040*scale,.035*scale)
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        ob.data.materials.append(tooth_mat);bevel=ob.modifiers.new('Rounded enamel edges','BEVEL');bevel.width=.00065;bevel.segments=3
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        for poly in ob.data.polygons:poly.use_smooth=True
        teeth.append(ob)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in teeth:ob.select_set(True)
    bpy.context.view_layer.objects.active=teeth[0];bpy.ops.object.join();teeth[0].name='Upper_Teeth'
    brow_mat=material('Natural dark eyebrows',(.024,.016,.012),.86)
    lash_mat=material('Fine dark eyelashes',(.018,.012,.009),.70)
    brows=Strands();upper=Strands();lower=Strands()
    for side in [-1,1]:
        # Tapered eyebrow hairs follow the actual body surface through ray casts.
        for j,t in enumerate(np.linspace(0,1,300)):
            x=.145+.36*t
            y=5.945+.037*math.sin(math.pi*t)-.016*t
            width=.046*(1-t)**.6+.005
            jitter=((j*37)%11/10-.5)*width
            pts=[skin_point(side*(x+.014*u),y+jitter+.014*u,.00030) for u in np.linspace(0,1,5)]
            brows.add(pts,[.000065,.00006,.00005,.000035,.000012],5)
        # Upper lash line and individual modest-length eyelashes.
        def lid(t,upper=True):
            x=.155+.282*t
            y=5.779+(.058 if upper else -.043)*math.sin(math.pi*t)+.012*t
            return skin_point(side*x,y,.0009)
        line=[lid(t) for t in np.linspace(.02,.98,35)]
        upper.add(line,[.00035]*len(line),6)
        for t in np.linspace(.05,.98,27):
            start=lid(t);length=.0035+.0024*math.sin(math.pi*t)
            pts=[start+Vector((side*length*.28*u,-length*.75*u,length*(.30*u+.35*u*u))) for u in np.linspace(0,1,6)]
            upper.add(pts,[.00020,.00019,.00017,.00013,.00008,.000025],5)
        for t in np.linspace(.12,.92,14):
            start=lid(t,False);length=.0020+.0011*math.sin(math.pi*t)
            pts=[start+Vector((side*length*.25*u,-length*.5*u,-length*.55*u)) for u in np.linspace(0,1,4)]
            lower.add(pts,[.00013,.00011,.00007,.00002],5)
    brows.mesh('Eyebrows',make_mesh,brow_mat)
    upper.mesh('Upper_Eyelashes',make_mesh,lash_mat)
    lower.mesh('Lower_Eyelashes',make_mesh,lash_mat)
    return {'hairstyle':'Center-parted swept-back close-fitting hair; curved frontal and nuchal hairlines; no bangs or ponytail',
            'eyebrows':'600 fine body-fitted tapered hairs over a soft baked brow tint',
            'eyelashes':{'upper':54,'lower':28},'smile':'Coral lip tint with a small original upper dental arch visible through the neutral lip opening','attachment':'Ray cast to refined adult body surface',
            'age':'adult, 20–25 years','reference':'User supplied frontal portrait: oval face, defined brows, almond eyes, coral smile and center-parted dark hair; interpretive 3D approximation, not an identity reconstruction'}
