"""Arm and fist study for v13: hand-modelled planes instead of smooth + decimate.

Kevin compared a close-up of the reference's fist with v11/v12: the reference
is built from a few deliberate planes (a forearm prism with long faces, a
blocky fist with a knuckle face, a separate thumb block), while decimation
gave noisy slivers and a hook-shaped thumb. This study builds only the left
arm, fist and torn sleeve that way, at the v12 rig positions, and renders a
close-up lit like the reference so the two can be compared before the rest of
the body is rebuilt the same way.

Blender coordinates: X across the shoulders (+X is his left), -Y forward, Z up.
"""
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'crew-arm-study-v13'
OUT.mkdir(parents=True,exist_ok=True)


def srgb(h):
    h=h.lstrip('#');c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)


COL={'skin':srgb('#D99259'),'linen':srgb('#D8CFBC'),'fold':srgb('#BDB29B')}
# v12 rest positions of the left arm (s=+1).
SH=Vector((.225,-.01,.75));EL=Vector((.29,-.02,.62));WR=Vector((.345,-.03,.49));END=Vector((.368,-.035,.37))


def axes(d):
    """Right-handed frame for a segment: d along the limb, F toward his front
    (-Y), X toward his outside (+X for the left arm)."""
    d=d.normalized();F=Vector((0,-1,0));F=(F-d*F.dot(d)).normalized()
    X=F.cross(d).normalized()
    if X.x<0:X=-X
    return d,X,F


class Mesh:
    def __init__(self,name):self.name=name;self.v=[];self.f=[];self.c=[]

    def ring(self,pts):
        b=len(self.v);self.v+=[tuple(p) for p in pts];return list(range(b,b+len(pts)))

    def bridge(self,a,b,col):
        n=len(a)
        for i in range(n):self.f.append([a[i],a[(i+1)%n],b[(i+1)%n],b[i]]);self.c.append(col)

    def cap(self,r,col,flip=False):
        self.f.append(list(reversed(r)) if flip else list(r));self.c.append(col)

    def finish(self):
        me=bpy.data.meshes.new(self.name);me.from_pydata(self.v,[],self.f);me.update()
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]);bm.to_mesh(me);bm.free()
        o=bpy.data.objects.new(self.name,me);bpy.context.scene.collection.objects.link(o)
        mat=bpy.data.materials.get('VC') or make_mat();me.materials.append(mat)
        attr=me.color_attributes.new('Col','BYTE_COLOR','CORNER')
        for p,c in zip(me.polygons,self.c):
            p.use_smooth=False
            for li in p.loop_indices:attr.data[li].color=(*COL[c],1)
        tris=sum(len(p.vertices)-2 for p in me.polygons)
        print(self.name,'triangles',tris);return o,tris


def make_mat():
    m=bpy.data.materials.new('VC');m.use_nodes=True
    a=m.node_tree.nodes.new('ShaderNodeVertexColor');a.layer_name='Col'
    b=m.node_tree.nodes['Principled BSDF'];b.inputs['Roughness'].default_value=.8
    m.node_tree.links.new(a.outputs['Color'],b.inputs['Base Color']);return m


def hexring(c,d,r,depth=1.,twist=0.,shift=Vector()):
    """Six-sided section with a flat face to the front; twist turns it a few
    degrees so the long planes of the forearm are not all parallel."""
    d,X,F=axes(d);pts=[]
    for i in range(6):
        a=math.radians(i*60+twist)
        pts.append(c+shift+X*r*math.cos(a)+F*r*depth*math.sin(a+math.radians(30)))
    return pts


def blockring(c,d,w,h,ch=.8,front=0.,shift=Vector()):
    """Chamfered rectangle: w across (X), h front-to-back (F). ch sets how far
    along each edge the corner cut starts (1 = square). front pushes the two
    front vertices forward (the curl of the fingers)."""
    d,X,F=axes(d)
    shape=[(-ch,1),(ch,1),(1,ch),(1,-ch),(ch,-1),(-ch,-1),(-1,-ch),(-1,ch)]
    pts=[]
    for a,b in shape:
        extra=front if b>.9 else 0
        pts.append(c+shift+X*a*w+F*(b*h+extra))
    return pts


arm=Mesh('Arm_Fist')
fd=WR-EL
# Forearm: four sections only. Muscle swell high on the outside, crease at the wrist.
A=arm.ring(hexring(EL.lerp(SH,.35),fd,.064,twist=0))
B=arm.ring(hexring(EL.lerp(WR,.33),fd,.082,depth=.95,twist=8,shift=axes(fd)[1]*.007))
C=arm.ring(hexring(EL.lerp(WR,.8),fd,.076,depth=.92,twist=4))
D=arm.ring(hexring(WR,fd,.06,depth=.9,twist=0))
arm.cap(A,'skin',flip=True)
for a,b in [(A,B),(B,C),(C,D)]:arm.bridge(a,b,'skin')
# Fist: back of the hand, knuckles, curled fingers stepping forward, blunt end.
hd=END-WR;dd,X,F=axes(hd)
# Square back of the hand, a knuckle ridge, the curled fingers stepping in
# under it (the crease), and a flat blunt end.
H=[arm.ring(blockring(WR-dd*.012,hd,.062,.056,ch=.7)),   # starts inside the wrist
   arm.ring(blockring(WR+dd*.05,hd,.082,.074,ch=.86,shift=F*.004)),
   arm.ring(blockring(WR+dd*.1,hd,.086,.08,ch=.88,front=.014,shift=F*.008)),    # knuckle ridge
   arm.ring(blockring(WR+dd*.118,hd,.08,.074,ch=.86,front=.0,shift=F*.006)),   # crease under it
   arm.ring(blockring(WR+dd*.158,hd,.078,.072,ch=.84,front=.004,shift=F*.008)),  # curled fingers
   arm.ring(blockring(WR+dd*.172,hd,.06,.054,ch=.8,shift=F*.006))]
# The wrist hex is capped and the hand starts from its own ring, tucked a few
# millimetres inside the forearm, so the joint reads as a crease.
arm.cap(D,'skin')
arm.cap(H[0],'skin',flip=True)
for a,b in zip(H,H[1:]):arm.bridge(a,b,'skin')
arm.cap(H[-1],'skin')
# Thumb: a square block in two segments lying across the front of the fingers,
# rooted at the inner-front corner of the hand, tip toward the fingers' middle.
inner=-X   # toward his body
root=WR+dd*.06+inner*.058+F*.04
mid=WR+dd*.1+inner*.048+F*.092
tip=WR+dd*.132+inner*.008+F*.1
def sq(c,d,w,h):
    d,Xl,Fl=axes(d);return [c+Xl*a*w+Fl*b*h for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]]
T0=arm.ring(sq(root,mid-root,.033,.034));T1=arm.ring(sq(mid,tip-root,.031,.031));T2=arm.ring(sq(tip,tip-mid,.022,.022))
arm.cap(T0,'skin',flip=True);arm.bridge(T0,T1,'skin');arm.bridge(T1,T2,'skin');arm.cap(T2,'skin')

sleeve=Mesh('Sleeve')
ud=EL-SH
# Loose sleeve: an 8-sided tube, with big torn teeth and a turned hem inside.
def oct_ring(c,d,r,teeth=None):
    d,Xs,Fs=axes(d);pts=[]
    for i in range(8):
        a=math.radians(i*45+22.5)
        p=c+Xs*r*math.cos(a)+Fs*r*math.sin(a)
        if teeth:p+=d*teeth[i]
        pts.append(p)
    return pts
S0=sleeve.ring(oct_ring(SH-ud*.2,ud,.09));S1=sleeve.ring(oct_ring(SH.lerp(EL,.35),ud,.105))
S2=sleeve.ring(oct_ring(SH.lerp(EL,.62),ud,.11,teeth=[.05,.0,.035,-.005,.055,.01,.03,.0]))
S3=sleeve.ring(oct_ring(SH.lerp(EL,.6),ud,.09))
sleeve.cap(S0,'linen',flip=True);sleeve.bridge(S0,S1,'linen');sleeve.bridge(S1,S2,'linen');sleeve.bridge(S2,S3,'fold')

for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
arm_o,arm_t=arm.finish();sl_o,sl_t=sleeve.finish()
print('TOTAL arm+fist',arm_t,'sleeve',sl_t)

# Lighting and camera as in the lit review renders.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.view_settings.view_transform='Standard';scene.view_settings.exposure=-.35;scene.render.film_transparent=True
world=bpy.data.worlds.new('W');scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(*srgb('#8FB7D6'),1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55
def light(name,loc,energy,size,col=(1,1,1)):
    L=bpy.data.lights.new(name,'AREA');L.energy=energy;L.size=size;L.color=col
    o=bpy.data.objects.new(name,L);scene.collection.objects.link(o);o.location=loc
    o.rotation_euler=(Vector((.3,0,.55))-Vector(loc)).to_track_quat('-Z','Y').to_euler()
light('Key',(-1.8,-2.4,2.6),170,2.2,(1,.96,.9));light('Fill',(2.4,-1.6,1.1),45,3,(.8,.88,1));light('Rim',(1.2,2.2,1.8),90,1.5)
cd=bpy.data.cameras.new('Cam');cam=bpy.data.objects.new('Cam',cd);scene.collection.objects.link(cam);scene.camera=cam
def shot(name,eye,target,lens,size=(900,900)):
    cam.location=eye;cam.rotation_euler=(Vector(target)-Vector(eye)).to_track_quat('-Z','Y').to_euler();cd.lens=lens
    scene.render.resolution_x,scene.render.resolution_y=size
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
target=(WR+END)/2+Vector((0,0,.06))
shot('closeup',(target.x-.28,-1.2,target.z+.12),target+Vector((0,0,.03)),88)   # framed like Kevin's reference crop
shot('outside',(1.6,-.25,.55),(.33,-.03,.52),60)
shot('front',(.33,-1.8,.55),(.33,-.03,.52),60)

import numpy as np
BACK=np.array([95,142,178],dtype=np.float32)/255
for png in OUT.glob('*.png'):
    img=bpy.data.images.load(str(png));w,h=img.size
    px=np.array(img.pixels[:],dtype=np.float32).reshape(h,w,4)
    rgb=px[...,:3]*px[...,3:4]+BACK*(1-px[...,3:4])
    img.pixels[:]=np.concatenate([rgb,np.ones((h,w,1),np.float32)],axis=2).ravel()
    img.filepath_raw=str(png);img.file_format='PNG';img.save()
