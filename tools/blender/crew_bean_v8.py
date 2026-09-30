"""Bean villager v8: the chosen silhouette D ("Bean") as a rigged game model.

Head and body are one bean with no neck: a cream tunic flows straight into the
head, a coral sash crosses it diagonally, a coral headcloth trails two tails,
mitten fists are held clear of the body, and short teal shorts end in bare
legs and big sandalled feet.

Keeps the runtime contract of the in-game deckhand (crew-astra-no-hat-v5) and
of v6, so it can replace Deckhand.fbx in place:
  - the same 16 bones, names and hierarchy (VillagerActing, HunterProps and
    AstraPlaytestImport find pelvis/spine/head/upper_arm.*/thigh.*/hand.*),
  - two skinned meshes, CREW_Cloth and CREW_Skin, exported in rest pose,
  - skin vertex colours exported white so CrewVertexColor can tint it
    (sickness green); skin _BaseColor stays sRGB #D99259,
  - flat vertex colours, no textures, faceted normals.
The source is 1.3 m tall; AstraPlaytestImport rescales every crew model to
1.7 m from its bounds.

Blender coordinates: X across the shoulders, -Y forward, Z up.
Run: blender -b -P tools/blender/crew_bean_v8.py  (or python with bpy)
"""
import json
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'crew-bean-v8'
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=HERE/'source/crew-bean-v8.blend'
SOURCE.parent.mkdir(parents=True,exist_ok=True)
PALETTE={'linen':'#E9DFC4','cuff':'#CDBF9C','skin':'#D99259',
         'pants':'#2F5E60','pantcuff':'#437573','sash':'#D2553E',
         'knot':'#B4443A','hair':'#3A2A20','eye':'#1F1915',
         'mouth':'#6E3B2C','sole':'#5B4130','strap':'#7C5B3B'}


def _hex(h):
    h=h.lstrip('#');return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))


def srgb_to_linear(c):
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)


COL={k:srgb_to_linear(_hex(v)) for k,v in PALETTE.items()}
MODELS=[]
AUDIT={}
N=12   # sides of the bean: round enough to read as one soft shape
BOX=[(-.72,-1),(.72,-1),(1,-.72),(1,.72),(.72,1),(-.72,1),(-1,.72),(-1,-.72)]
# The bean: (z, y centre, half width, half depth). Widest at the belly,
# a little narrower at the face, rounding off at the crown. No neck.
PROFILE=[(.24,0,.19,.16),(.30,-.005,.235,.195),(.40,-.01,.268,.215),
         (.60,-.02,.285,.225),(.80,-.02,.275,.217),(.90,-.02,.265,.21),
         (1.00,-.015,.245,.20),(1.10,-.01,.22,.19),(1.18,-.005,.18,.16),
         (1.24,0,.13,.12),(1.28,0,.06,.06)]
COLLAR=.86   # where the tunic ends and the head (skin) begins


def prof(z):
    for (z0,*a),(z1,*b) in zip(PROFILE,PROFILE[1:]):
        if z<=z1:
            t=max(0,min(1,(z-z0)/(z1-z0)));return [p+(q-p)*t for p,q in zip(a,b)]
    return list(PROFILE[-1][1:])


def around(z,grow=0.,n=N,tilt=0.):
    """A ring on the bean surface at height z, pushed out by grow. With tilt,
    the ring slants (z rises across x) and still hugs the surface."""
    pts=[]
    for i in range(n):
        a=i*math.tau/n+math.pi/n
        zz=z
        for _ in range(4):
            y,rx,ry=prof(zz);zz=z+tilt*(rx+grow)*math.cos(a)
        y,rx,ry=prof(zz)
        pts.append(((rx+grow)*math.cos(a),y+(ry+grow)*math.sin(a),zz))
    return pts


class Mesh:
    def __init__(self,name):
        self.name=name;self.v=[];self.f=[];self.colors=[];self.weights=[]

    def vertex(self,p,w):
        self.v.append(tuple(p));self.weights.append(dict(w));return len(self.v)-1

    def face(self,ids,color):
        self.f.append(list(ids));self.colors.append(color)

    def ring(self,points,weights):
        return [self.vertex(p,weights(p) if callable(weights) else weights) for p in points]

    def bridge(self,a,b,color):
        assert len(a)==len(b)
        for i in range(len(a)):
            self.face([a[i],a[(i+1)%len(a)],b[(i+1)%len(b)],b[i]],color)

    def close(self,r,color):
        self.face(r,color)

    def finish(self,skin=False):
        used=sorted({i for face in self.f for i in face})
        remap={old:new for new,old in enumerate(used)}
        self.v=[self.v[i] for i in used];self.weights=[self.weights[i] for i in used]
        self.f=[[remap[i] for i in face] for face in self.f]
        me=bpy.data.meshes.new(self.name);me.from_pydata(self.v,[],self.f);me.update()
        o=bpy.data.objects.new(self.name,me);bpy.context.scene.collection.objects.link(o)
        me.materials.append(SKIN if skin else CLOTH)
        attr=me.color_attributes.new(name='Col',type='BYTE_COLOR',domain='CORNER')
        for p,c in zip(me.polygons,self.colors):
            for li in p.loop_indices:attr.data[li].color=(*COL[c],1)
        me.color_attributes.active_color=attr
        bm=bmesh.new();bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        for f in bm.faces:f.smooth=False
        bm.to_mesh(me);bm.free()
        groups={n:o.vertex_groups.new(name=n) for n in sorted({n for w in self.weights for n in w})}
        for i,w in enumerate(self.weights):
            total=sum(w.values())
            assert total>0
            for n,value in w.items():
                if value>0:groups[n].add([i],value/total,'REPLACE')
        mod=o.modifiers.new('Crew deformation','ARMATURE');mod.object=RIG
        mod.use_deform_preserve_volume=False
        o.parent=RIG;o['skin_tint']=skin
        MODELS.append(o)
        return o


def mat(name):
    m=bpy.data.materials.new(name);m.use_nodes=True
    a=m.node_tree.nodes.new('ShaderNodeVertexColor');a.layer_name='Col'
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Roughness'].default_value=.85
    m.node_tree.links.new(a.outputs['Color'],b.inputs['Base Color'])
    return m


def side_name(base,side):return base+('.R' if side>0 else '.L')


def lerp(a,b,t):return Vector(a).lerp(Vector(b),t)


def clamp01(t):return max(0.,min(1.,t))


def section(center,direction,rx,ry,n=8):
    d=Vector(direction).normalized()
    v=Vector((0,1,0))
    if abs(d.dot(v))>.95:v=Vector((0,0,1))
    v=(v-d*v.dot(d)).normalized()
    u=v.cross(d).normalized()
    return [Vector(center)+u*rx*math.cos(i*math.tau/n)+v*ry*math.sin(i*math.tau/n) for i in range(n)]


def loft(m,rows,color,weights,shape=BOX,caps=True):
    rs=[]
    for x,y,z,rx,ry in rows:
        r=m.ring([(x+a*rx,y+b*ry,z) for a,b in shape],weights)
        if rs:m.bridge(rs[-1],r,color)
        rs.append(r)
    if caps:m.close(rs[0],color);m.close(rs[-1],color)
    return rs


def tube(m,path,color,weights,n=6,flat=.45):
    # A tapered cloth tail along a polyline of (point, radius) pairs.
    prev=None
    for j,(p,r) in enumerate(path):
        d=Vector(path[min(j+1,len(path)-1)][0])-Vector(path[max(j-1,0)][0])
        ring=m.ring(section(p,d,r,r*flat,n),weights)
        if prev is None:m.close(list(reversed(ring)),color)
        else:m.bridge(prev,ring,color)
        prev=ring
    m.close(prev,color)


def band(m,z,height,grow,color,weights,tilt=0.,thick=.012):
    # A closed cloth band hugging the bean: outer and inner walls, no caps.
    rings=[around(z,grow+thick,tilt=tilt),around(z+height,grow+thick,tilt=tilt),
           around(z+height,grow,tilt=tilt),around(z,grow,tilt=tilt)]
    ids=[m.ring(r,weights) for r in rings]
    for a,b in zip(ids,ids[1:]+ids[:1]):m.bridge(a,b,color)


def body_weights(p):
    z=p[2]
    if z<.30:return {'pelvis':1}
    if z<.50:t=(z-.30)/.20;return {'pelvis':1-t,'spine':t}
    if z<COLLAR-.04:return {'spine':1}
    if z<COLLAR+.08:t=(z-(COLLAR-.04))/.12;return {'spine':1-t,'head':t}
    return {'head':1}


REST={
    'root':((0,0,.02),(0,0,.20),None),
    'pelvis':((0,0,.30),(0,0,.42),'root'),
    'spine':((0,0,.42),(0,0,COLLAR),'pelvis'),
    'head':((0,0,COLLAR),(0,0,1.28),'spine')}
for s in [-1,1]:
    upper=side_name('upper_arm',s);fore=side_name('forearm',s);hand=side_name('hand',s)
    thigh=side_name('thigh',s);shin=side_name('shin',s);foot=side_name('foot',s)
    REST[upper]=((s*.21,-.02,.80),(s*.315,-.035,.665),'spine')
    REST[fore]=(REST[upper][1],(s*.355,-.045,.57),upper)
    REST[hand]=(REST[fore][1],(s*.38,-.05,.46),fore)
    REST[thigh]=((s*.12,0,.30),(s*.12,-.005,.19),'pelvis')
    REST[shin]=(REST[thigh][1],(s*.12,0,.07),thigh)
    REST[foot]=(REST[shin][1],(s*.12,-.13,.025),shin)


def rig():
    data=bpy.data.armatures.new('DeckhandSkeleton')
    o=bpy.data.objects.new('Deckhand_Rig',data);bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.objects.active=o;o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for name,(a,b,parent) in REST.items():
        bone=data.edit_bones.new(name);bone.head=a;bone.tail=b
        if parent:bone.parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT');o.show_in_front=True
    return o


def tunic():
    """The lower bean: one cream smock from hem to collar, with a turned hem
    (the legs come out below it) and a folded collar the head sits in."""
    m=Mesh('Tunic')
    heights=[.24,.30,.40,.50,.60,.70,.80,COLLAR]
    def w(p):
        wt=body_weights(p)
        # Shoulder corners follow the arms a little so the sleeve roots stay covered.
        if .66<p[2]<=.80 and abs(p[0])>.18:
            s=1 if p[0]>0 else -1;k=.15*min(1,(p[2]-.66)/.14)
            wt={n:v*(1-k) for n,v in wt.items()};wt[side_name('upper_arm',s)]=k
        return wt
    rings=[m.ring(around(z,.012 if z==.24 else .0),w) for z in heights]
    for a,b in zip(rings,rings[1:]):m.bridge(a,b,'linen')
    lining=m.ring([(x*.86,y*.86,z+.04) for x,y,z in around(.24,.012)],{'pelvis':1})
    m.bridge(lining,rings[0],'cuff')
    fold=m.ring(around(COLLAR+.018,.016),body_weights)
    m.bridge(rings[-1],fold,'cuff')
    inner=m.ring(around(COLLAR+.022,.003),body_weights)
    m.bridge(fold,inner,'cuff')
    o=m.finish();o['expected_components']=1;o['expected_boundary_loops']=2


def sleeves():
    m=Mesh('Sleeves')
    for s in [-1,1]:
        upper=side_name('upper_arm',s)
        a,e,_=REST[upper];d=Vector(e)-Vector(a)
        rows=[(Vector(a)-d*.20,.078,'linen'),(Vector(a),.086,'linen'),
              (lerp(a,e,.30),.084,'linen'),(lerp(a,e,.31),.094,'cuff'),
              (lerp(a,e,.55),.094,'cuff'),(lerp(a,e,.56),.086,'cuff')]
        prev=None
        for p,r,color in rows:
            ring=m.ring(section(p,d,r,r*.95),{upper:1})
            if prev is None:m.close(list(reversed(ring)),'linen')
            else:m.bridge(prev,ring,color)
            prev=ring
        inner=m.ring(section(rows[-1][0],d,.072,.070),{upper:1})
        m.bridge(prev,inner,'cuff')
    m.finish()


def sash():
    """Diagonal coral sash: high on the right shoulder side, knotted low on
    the left hip, where two tails hang. The one diagonal breaks the stripes."""
    m=Mesh('Sash')
    band(m,.585,.075,.004,'sash',body_weights,tilt=.62)
    loft(m,[(-.25,-.12,.43,.045,.034),(-.255,-.13,.47,.052,.04),(-.25,-.12,.51,.042,.032)],
         'knot',body_weights)
    tube(m,[((-.262,-.14,.45),.032),((-.285,-.15,.36),.030),((-.30,-.155,.28),.022)],'sash',{'pelvis':1})
    tube(m,[((-.232,-.15,.45),.030),((-.24,-.17,.37),.027),((-.245,-.18,.30),.02)],'sash',{'pelvis':1})
    m.finish()


def shorts():
    m=Mesh('Shorts')
    for s in [-1,1]:
        thigh=side_name('thigh',s);shin=side_name('shin',s);x=s*.12
        rows=[(.40,.085,{'pelvis':.6,thigh:.4},'pants'),(.30,.088,{thigh:1},'pants'),
              (.215,.086,{thigh:.6,shin:.4},'pants'),(.18,.084,{thigh:.2,shin:.8},'pants'),
              (.179,.095,{shin:1},'pantcuff'),(.145,.095,{shin:1},'pantcuff'),
              (.144,.072,{shin:1},'pantcuff'),(.165,.070,{shin:1},'pants')]
        prev=None
        for z,r,wt,color in rows:
            ring=m.ring([(x+a*r,b*r,z) for a,b in BOX],wt)
            if prev is None:m.close(list(reversed(ring)),'pants')
            else:m.bridge(prev,ring,color)
            prev=ring
    o=m.finish();o['expected_boundary_loops']=2


def legs():
    for s in [-1,1]:
        foot=side_name('foot',s);shin=side_name('shin',s);x=s*.12
        thigh=side_name('thigh',s)
        def weights(p):
            # The hidden top of the shin, just under the knee, half follows
            # the thigh so a deep crouch does not push it through the shorts.
            if p[2]>.14:k=.5*clamp01((p[2]-.14)/.02);return {shin:1-k,thigh:k}
            t=clamp01((p[2]-.085)/.08);return {foot:1-t,shin:t}
        m=Mesh('Leg_Foot'+('.R' if s>0 else '.L'))
        loft(m,[(x,0,.16,.058,.058),(x,0,.12,.060,.060),(x,-.01,.09,.058,.07),
                (x,-.045,.062,.078,.135),(x,-.05,.032,.078,.14)],'skin',weights,BOX)
        o=m.finish(skin=True);o['expected_components']=1;o['expected_boundary_loops']=0
        m=Mesh('Sandal'+('.R' if s>0 else '.L'))
        loft(m,[(x,-.05,.0,.086,.148),(x,-.05,.029,.086,.148)],'sole',{foot:1},BOX)
        ring=loft(m,[(x,-.0375,.068,.0787,.126),(x,-.0225,.080,.0701,.0982),
                     (x,-.0225,.080,.0676,.0957),(x,-.0375,.068,.0762,.1235)],'strap',weights,BOX,caps=False)
        m.bridge(ring[-1],ring[0],'strap')
        m.finish()


def arms():
    for s in [-1,1]:
        m=Mesh('Arm_Hand'+('.R' if s>0 else '.L'))
        upper=side_name('upper_arm',s);fore=side_name('forearm',s);hand=side_name('hand',s)
        a,e,_=REST[upper];w=REST[fore][1];end=REST[hand][1]
        direction=Vector(end)-Vector(a)
        rows=[(lerp(a,e,.30),.068,.066,{upper:1}),
              (lerp(a,e,.80),.068,.066,{upper:.8,fore:.2}),
              (Vector(e),.066,.064,{upper:.5,fore:.5}),
              (lerp(e,w,.40),.064,.062,{fore:1}),
              (lerp(e,w,.95),.056,.054,{fore:.7,hand:.3}),
              (lerp(w,end,.12),.060,.056,{hand:1}),
              (lerp(w,end,.40),.082,.070,{hand:1}),
              (lerp(w,end,.78),.085,.072,{hand:1}),
              (lerp(w,end,1.05),.068,.058,{hand:1}),
              (lerp(w,end,1.16),.040,.034,{hand:1})]
        rings=[m.ring(section(p,direction,rx,ry),weights) for p,rx,ry,weights in rows]
        m.close(rings[0],'skin')
        side=6 if s>0 else 5
        for j in range(len(rings)-1):
            for i in range(8):
                if j==6 and i==side:continue
                m.face([rings[j][i],rings[j][(i+1)%8],rings[j+1][(i+1)%8],rings[j+1][i]],'skin')
        root=[rings[6][side],rings[6][(side+1)%8],rings[7][(side+1)%8],rings[7][side]]
        center=sum((Vector(m.v[i]) for i in root),Vector())/4
        previous=root
        for offset,scale in [(Vector((-s*.012,-.024,0)),.95),
                             (Vector((-s*.018,-.040,-.010)),.86),
                             (Vector((-s*.018,-.046,-.026)),.70)]:
            r=m.ring([center+offset+(Vector(m.v[i])-center)*scale for i in root],{hand:1})
            m.bridge(previous,r,'skin');previous=r
        m.close(previous,'skin');m.close(rings[-1],'skin')
        o=m.finish(skin=True);o['expected_components']=1;o['expected_boundary_loops']=0


def head():
    """The upper bean is skin from just inside the collar to the crown; hair
    caps the crown and a coral headcloth sits over the hair's edge."""
    m=Mesh('Head')
    heights=[(COLLAR-.04,-.02),(COLLAR+.02,-.006),(.95,0),(1.02,0),(1.10,0),(1.18,0),(1.24,0)]
    rings=[m.ring(around(z,g),body_weights) for z,g in heights]
    for a,b in zip(rings,rings[1:]):m.bridge(a,b,'skin')
    top=m.ring(around(1.278,-.0),{'head':1});m.bridge(rings[-1],top,'skin')
    m.close(rings[0],'skin');m.close(top,'skin')
    o=m.finish(skin=True);o['expected_components']=1;o['expected_boundary_loops']=0
    return o


def hair_and_headcloth():
    m=Mesh('Hair')
    rows=[1.06,1.12,1.18,1.23,1.262]
    rings=[m.ring(around(z,.012),{'head':1}) for z in rows]
    for a,b in zip(rings,rings[1:]):m.bridge(a,b,'hair')
    top=m.ring([(x*.55,y*.55,1.29) for x,y,z in around(1.262,.012)],{'head':1})
    m.bridge(rings[-1],top,'hair');m.close(top,'hair');m.close(list(reversed(rings[0])),'hair')
    # A short fringe tuft over the band, off-centre, so the crown is not a dome.
    loft(m,[(.05,-.12,1.235,.07,.05),(.075,-.19,1.215,.045,.03),(.095,-.225,1.17,.012,.01)],
         'hair',{'head':1})
    m.finish()
    m=Mesh('Headcloth')
    band(m,1.075,.07,.022,'sash',{'head':1},thick=.014)
    loft(m,[(.19,.10,1.07,.042,.036),(.198,.108,1.105,.05,.042),(.19,.10,1.14,.038,.032)],
         'knot',{'head':1})
    tube(m,[((.21,.12,1.09),.034),((.31,.16,1.03),.032),((.38,.18,.94),.023)],'sash',{'head':1})
    tube(m,[((.19,.15,1.08),.030),((.25,.21,.99),.028),((.28,.24,.91),.02)],'sash',{'head':1})
    m.finish()


def face(head_obj):
    """Face marks are placed by casting onto the head, so they sit flush on
    the curved bean instead of floating off a guessed front plane."""
    me=head_obj.data
    tree=BVHTree.FromPolygons([v.co.copy() for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
    def hit(x,z,side=None):
        if side:o=Vector((side*2,-.02,z));d=Vector((-side,0,0))
        else:o=Vector((x,-2,z));d=Vector((0,1,0))
        p,n,_,_=tree.ray_cast(o,d);assert p is not None,(x,z);return p,n
    def plate(m,x,z,w,h,depth,color,side=None,roll=0.):
        p,n=hit(x,z,side)
        up=Vector((0,0,1));u=up.cross(n).normalized();v=n.cross(u).normalized()
        c,sn=math.cos(roll),math.sin(roll);u,v=u*c+v*sn,v*c-u*sn
        pts=[]
        for dz in [-depth*.4,depth]:
            for a,b in BOX:pts.append(p+n*dz+u*a*w/2+v*b*h/2)
        ids=[m.vertex(q,{'head':1}) for q in pts]
        m.bridge(ids[:8],ids[8:],color);m.close(list(reversed(ids[:8])),color);m.close(ids[8:],color)
    m=Mesh('Face_details')
    for s in [-1,1]:
        plate(m,s*.085,1.005,.04,.058,.008,'eye')
        plate(m,s*.088,1.052,.068,.016,.009,'hair',roll=-s*.12)
    plate(m,0,.905,.07,.012,.006,'mouth')
    m.finish()
    m=Mesh('Nose_Ears')
    p,n=hit(0,.955)
    tube(m,[(p-n*.01,.030),(p+n*.028,.046),(p+n*.058,.036)],'skin',{'head':1},n=8,flat=.9)
    for s in [-1,1]:
        p,n=hit(0,.99,side=s)
        tube(m,[(p-n*.01,.030),(p+n*.018,.036),(p+n*.034,.026)],'skin',{'head':1},n=6,flat=.55)
    m.finish(skin=True)


def topology(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    unseen=set(bm.verts);components=0
    while unseen:
        components+=1;stack=[unseen.pop()]
        while stack:
            for e in stack.pop().link_edges:
                for v in e.verts:
                    if v in unseen:unseen.remove(v);stack.append(v)
    boundary={e for e in bm.edges if e.is_boundary};loops=0
    while boundary:
        loops+=1;stack=list(boundary.pop().verts)
        while stack:
            for e in stack.pop().link_edges:
                if e in boundary:boundary.remove(e);stack.extend(e.verts)
    d={'vertices':len(bm.verts),'triangles':sum(len(f.verts)-2 for f in bm.faces),
       'components':components,'boundary_loops':loops,
       'overconnected_edges':sum(len(e.link_faces)>2 for e in bm.edges),
       'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces)}
    bm.free()
    assert not d['overconnected_edges'] and not d['degenerate_faces'],(o.name,d)
    if 'expected_components' in o:assert components==o['expected_components'],(o.name,d)
    if 'expected_boundary_loops' in o:assert loops==o['expected_boundary_loops'],(o.name,d)
    for v in o.data.vertices:assert abs(sum(g.weight for g in v.groups)-1)<1e-5
    return d


def pose(kind):
    RIG.location=(0,0,0)
    for pb in RIG.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    if kind=='neutral':return
    def aim(name,head,direction):
        bone=RIG.data.bones[name];length=bone.length
        delta=(bone.tail_local-bone.head_local).rotation_difference(Vector(direction).normalized())
        rotation=delta.to_matrix().to_4x4()@bone.matrix_local.to_quaternion().to_matrix().to_4x4()
        rotation.translation=Vector(head);RIG.pose.bones[name].matrix=rotation
        bpy.context.view_layer.update()
        return Vector(head)+Vector(direction).normalized()*length
    for s in [-1,1]:
        upper=side_name('upper_arm',s);fore=side_name('forearm',s);hand=side_name('hand',s)
        if kind=='reach':u=(s*.35,-.90,.10);f=(s*.08,-1,.05)
        else:u=(s*.55,-.30,-.78);f=(s*.10,-1,-.12)
        e=aim(upper,REST[upper][0],u);w=aim(fore,e,f);aim(hand,w,f)
        thigh=side_name('thigh',s);shin=side_name('shin',s);foot=side_name('foot',s)
        if kind=='crouch':td=(s*.10,-.70,-.70);sd=(0,.60,-.80)
        elif kind=='stride':td=(0,-s*.45,-.89);sd=(0,s*.15,-.99)
        else:td=(s*.10,-.10,-.99);sd=(s*.02,.10,-.995)
        knee=aim(thigh,REST[thigh][0],td);ankle=aim(shin,knee,sd)
        aim(foot,ankle,(0,-.94,-.34))
    graph=bpy.context.evaluated_depsgraph_get()
    minimum=min((o.evaluated_get(graph).matrix_world@v.co).z
                for o in MODELS if o.name.startswith('Sandal') for v in o.evaluated_get(graph).data.vertices)
    RIG.location.z=-minimum+.005;bpy.context.view_layer.update()


def render(name,eye=(3,5,3),size=(1000,1100),wire=False,scale=1.62):
    cam.location=eye;cam.rotation_euler=(Vector((0,-.02,.66))-cam.location).to_track_quat('-Z','Y').to_euler()
    cd.ortho_scale=scale
    scene.render.resolution_x,scene.render.resolution_y=size
    temporary=[]
    if wire:
        for o in MODELS:
            ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
            ob=bpy.data.objects.new('Topology',bpy.data.meshes.new_from_object(ev))
            scene.collection.objects.link(ob);ob.matrix_world=o.matrix_world.copy()
            for c in ob.data.color_attributes['Col'].data:c.color=(.025,.025,.025,1)
            mod=ob.modifiers.new('Edges','WIREFRAME');mod.thickness=.0012;mod.offset=1;mod.use_replace=True
            temporary.append(ob)
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    for o in temporary:bpy.data.objects.remove(o,do_unlink=True)


def intersection_count(a,b):
    graph=bpy.context.evaluated_depsgraph_get()
    def tree(o):
        ev=o.evaluated_get(graph);me=ev.to_mesh();me.calc_loop_triangles()
        t=BVHTree.FromPolygons([ev.matrix_world@v.co for v in me.vertices],
                              [tuple(f.vertices) for f in me.loop_triangles],all_triangles=True)
        ev.to_mesh_clear();return t
    return len(tree(a).overlap(tree(b)))


def setup_render(scene):
    scene.render.engine='BLENDER_WORKBENCH'
    sh=scene.display.shading
    sh.color_type='VERTEX';sh.light='STUDIO'
    sh.show_shadows=False;sh.show_cavity=True
    sh.show_backface_culling=True;sh.show_specular_highlight=False
    sh.show_object_outline=False;sh.background_type='WORLD'
    scene.display.light_direction=(-.35,.45,.82)
    scene.display.render_aa='16'
    scene.view_settings.view_transform='Standard';scene.view_settings.exposure=.65
    scene.world=scene.world or bpy.data.worlds.new('Review')
    scene.world.color=srgb_to_linear(_hex('#708D96'))
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False;scene.render.resolution_percentage=100


for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
CLOTH=mat('Crew_Cloth');SKIN=mat('Crew_Skin_Preview');RIG=rig()
tunic();sleeves();sash();shorts();legs();arms()
face(head());hair_and_headcloth()
AUDIT['topology']={o.name:topology(o) for o in MODELS}
AUDIT['triangles']=sum(d['triangles'] for d in AUDIT['topology'].values())
scene=bpy.context.scene;setup_render(scene)
cd=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',cd);scene.collection.objects.link(cam)
scene.camera=cam;cd.type='ORTHO'
AUDIT['poses']={}
# The arm leaves the round body at an angle, so the arm's root is always
# partly inside the tunic; that is covered by the sleeve and is not checked.
PAIRS=[('Sleeves','Arm_Hand.L'),('Sleeves','Arm_Hand.R'),
       ('Shorts','Leg_Foot.L'),('Shorts','Leg_Foot.R'),
       ('Sandal.L','Leg_Foot.L'),('Sandal.R','Leg_Foot.R'),
       ('Tunic','Head')]
for frame,kind in [(1,'neutral'),(21,'working'),(41,'reach'),(61,'crouch'),(81,'stride')]:
    scene.frame_set(frame);pose(kind)
    for pb in RIG.pose.bones:
        pb.rotation_mode='QUATERNION'
        pb.keyframe_insert('location',frame=frame);pb.keyframe_insert('rotation_quaternion',frame=frame)
        pb.keyframe_insert('scale',frame=frame)
    RIG.keyframe_insert('location',frame=frame)
    graph=bpy.context.evaluated_depsgraph_get()
    degenerate=0
    for o in MODELS:
        ev=o.evaluated_get(graph);me=ev.to_mesh();me.calc_loop_triangles()
        degenerate+=sum(t.area<1e-10 for t in me.loop_triangles);ev.to_mesh_clear()
    contacts={a+' / '+b:intersection_count(bpy.data.objects[a],bpy.data.objects[b]) for a,b in PAIRS}
    AUDIT['poses'][kind]={'degenerate_triangles':degenerate,'garment_intersections':contacts}
    assert degenerate==0,(kind,degenerate)
    assert not any(contacts.values()),(kind,contacts)
    render(kind+'-rear')
    render(kind+'-front',(3,-5,2.6))
    if kind=='neutral':
        render('topology-front',(3,-5,2.6),wire=True)
        render('side',(-5.8,-.4,1.2))
        render('front',(0,-6,.66))
    if kind=='working':render('game-size',(3,5,3),(180,198),scale=1.72)
scene.frame_end=81
scene.frame_set(1);pose('neutral')
for o in MODELS:
    if o['skin_tint']:
        for c in o.data.color_attributes['Col'].data:c.color=(1,1,1,1)
export_objects=[]
for skin in [False,True]:
    copies=[]
    for o in MODELS:
        if bool(o['skin_tint'])!=skin:continue
        ob=o.copy();ob.data=o.data.copy();scene.collection.objects.link(ob);copies.append(ob)
    bpy.ops.object.select_all(action='DESELECT')
    for o in copies:o.select_set(True)
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join()
    ob=bpy.context.object;ob.name='CREW_Skin' if skin else 'CREW_Cloth';export_objects.append(ob)
bpy.ops.object.select_all(action='DESELECT');RIG.select_set(True)
for o in export_objects:o.select_set(True)
bpy.context.view_layer.objects.active=RIG
bpy.ops.export_scene.fbx(filepath=str(OUT/'deckhand-rigged.fbx'),use_selection=True,
    object_types={'MESH','ARMATURE'},axis_forward='-Z',axis_up='Y',add_leaf_bones=False,
    use_armature_deform_only=True,bake_anim=False,use_triangles=True,colors_type='LINEAR',mesh_smooth_type='FACE')
for o in export_objects:bpy.data.objects.remove(o,do_unlink=True)
for o in MODELS:
    if o['skin_tint']:
        for c in o.data.color_attributes['Col'].data:c.color=(*COL['skin'],1)
AUDIT['skin_base_color_srgb']=PALETTE['skin'];AUDIT['rig_bones']=len(RIG.data.bones)
AUDIT['palette_srgb']=PALETTE
AUDIT['notes']='Five keyed deformation tests, not polished gameplay animations. No Unity integration.'
(OUT/'validation.json').write_text(json.dumps(AUDIT,indent=2))
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
print(json.dumps({k:AUDIT[k] for k in ['triangles','poses']},indent=2))
