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
    displacement=(-anterior*front+posterior*back)*scale
    positions[:,1]+=displacement
    # Relax the neutral open-mouth rest pose toward a narrow natural lip seam.
    lip_gate=g(x,.33)**4*np.exp(-((y-5.13)/.22)**4)*smooth((z-1.05)/.15)
    lip_lift=-.035*np.tanh((y-5.13)/.04)*lip_gate*scale
    positions[:,2]+=lip_lift
    mesh.vertices.foreach_set('co',positions.reshape(-1));mesh.update()
    body['surface_detail']='Authored gentle clavicular, SCM, scapular, lumbar and quadriceps surface relief; not clinical calibration.'
    return {'method':'Smooth analytic displacement of refined continuous body mesh',
            'regions':['clavicles','supraclavicular fossae','infraclavicular fossae','sternocleidomastoid relief','scapular spine and medial border relief','lumbar dimples','quadriceps relief'],
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
        hairline_y=5.78+(.42 if c>=0 else .30)*c
        def scalp_at(phi):
            direction=Vector((math.sin(phi)*math.sin(angle),-math.sin(phi)*math.cos(angle),math.cos(phi)))
            hit,normal,_,_=bvh.ray_cast(origin,direction,1)
            if hit is None:raise ValueError('Scalp ray missed')
            return hit+normal*.0038
        lo_phi=.01;hi_phi=2.7
        for _ in range(19):
            mid=(lo_phi+hi_phi)/2
            if scalp_at(mid).z/scale+low>hairline_y:lo_phi=mid
            else:hi_phi=mid
        for k in range(rows):scalp_v.append(tuple(scalp_at(.003+(hi_phi-.003)*k/(rows-1))))
    for j in range(columns):
        for k in range(rows-1):
            a=j*rows+k;b=((j+1)%columns)*rows+k
            scalp_f.append((a,b,b+1,a+1))
    scalp_f.append(tuple(j*rows for j in reversed(range(columns))))
    new_cap=make_mesh('Continuous scalp',scalp_v,scalp_f,mat=hair)
    import bpy
    bpy.data.objects.remove(cap,do_unlink=True);new_cap.name='Hair_Cap'
    hair.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.64
    # A ponytail made of overlapping tapered locks, directed away from the back.
    pony=Strands()
    for j in range(23):
        angle=j*2.399963
        radial=.18*math.sqrt((j+.5)/23)
        pts=[];radii=[]
        for t in np.linspace(0,1,33):
            cx=.07*math.sin(t*math.pi)
            cy=6.26-(1.50+.10*math.sin(j*1.8))*t+.26*math.sin(math.pi*t)
            cz=-.60-.91*math.sin(math.pi*t*.64)
            spread=.42+.65*math.sin(math.pi*t*.92)
            pts.append(point(cx+radial*math.cos(angle)*spread,cy,cz+radial*math.sin(angle)*spread))
            radii.append(scale*(.074*(1-t)**.50+.003))
        pony.add(pts,radii,9)
    pony.mesh('Hair_Ponytail',make_mesh,hair)
    # Wispy locks are individually separated; their tips do not form a solid fringe.
    bangs=Strands()
    for j,xend in enumerate([-.47,-.36,-.24,-.12,.035,.16,.285,.41,.50]):
        for strand in range(5):
            pts=[];radii=[]
            tip_y=6.015+.075*math.sin(j*2.1)+.014*math.sin(strand*2)
            for t in np.linspace(0,1,19):
                x=xend*(.54+.46*t)+.025*math.sin(math.pi*t+j)+(strand-2)*.009
                y=6.42+(tip_y-6.42)*t
                pts.append(skin_point(x,y,.0044+.0018*math.sin(math.pi*t)))
                radii.append(scale*(.0045*(1-t)**.6+.00025))
            bangs.add(pts,radii,6)
    bangs.mesh('Hair_Wispy_Bangs',make_mesh,hair)
    # Fine brushed strokes on the cap prevent a smooth helmet-like highlight.
    strokes=Strands()
    for j,x in enumerate(np.linspace(-.48,.48,65)):
        pts=[]
        for t in np.linspace(0,1,14):
            xx=x*(1-.25*t)
            yy=6.24+.33*t
            pts.append(skin_point(xx,yy,.0044))
        strokes.add(pts,[.00012]*len(pts),5)
    strokes.mesh('Hair_Fine_Strokes',make_mesh,hair)
    brow_mat=material('Natural dark eyebrows',(.040,.027,.020),.86)
    lash_mat=material('Fine dark eyelashes',(.018,.012,.009),.70)
    brows=Strands();upper=Strands();lower=Strands()
    for side in [-1,1]:
        # Tapered eyebrow hairs follow the actual body surface through ray casts.
        for j,t in enumerate(np.linspace(0,1,210)):
            x=.145+.36*t
            y=5.993+.067*math.sin(math.pi*t)-.016*t
            width=.030*(1-t)**.4+.004
            jitter=((j*37)%11/10-.5)*width
            pts=[skin_point(side*(x+.014*u),y+jitter+.014*u,.00030) for u in np.linspace(0,1,5)]
            brows.add(pts,[.00008,.000075,.00006,.00004,.000015],5)
        # Upper lash line and individual modest-length eyelashes.
        def lid(t,upper=True):
            x=.155+.282*t
            y=5.779+(.047 if upper else -.036)*math.sin(math.pi*t)+.008*t
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
    return {'hairstyle':'High ponytail with nine separated wispy bang locks and fine cap strokes',
            'eyebrows':'420 fine body-fitted tapered hairs over a soft baked brow tint',
            'eyelashes':{'upper':54,'lower':28},'attachment':'Ray cast to refined adult body surface',
            'age':'adult, 20–25 years','not_a_real_person':True}
