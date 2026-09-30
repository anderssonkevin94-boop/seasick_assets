"""Islander villager v9: the Bean refined toward Kevin's reference sheet.

Reference: a painted concept Kevin got by asking for "a more refined look
while keeping the style" of v8 (crew-islander-v9/reference.jpg). Reproduced as
closely as flat vertex colours allow:
  - chiselled, blocky forms: a chamfered box head, a squarer body, block fists
    and block feet (v8 was a round 12-sided bean),
  - the head sits in a tall stand-up collar with a V opening at the front,
  - ragged zigzag hems on the tunic and sleeves,
  - diagonal red sash from the left shoulder to a big knot on the right hip,
  - wide red headband with a ball knot and three tails on the left side,
  - messy dark hair with a topknot tuft,
  - sewn patches (planks and a stitch on the tunic, one on the shorts), a cloth
    wrap on the right wrist,
  - rectangular eyes, heavy brows, a pyramid nose, a small red mouth, block ears,
  - two-layer wooden sandal soles with an instep strap.
The painted texture of the reference is suggested by a slight per-face colour
variation on cloth only; skin stays one flat colour because the game tints it.

Keeps the runtime contract of the in-game deckhand (crew-astra-no-hat-v5):
  - the same 16 bones, names and hierarchy,
  - two skinned meshes, CREW_Cloth and CREW_Skin, exported in rest pose,
  - skin vertex colours exported white (CrewVertexColor tints skin; sickness
    green), skin _BaseColor stays sRGB #D99259,
  - flat vertex colours, no textures, faceted normals.
The source is about 1.3 m tall; AstraPlaytestImport rescales to 1.7 m.

Blender coordinates: X across the shoulders (+X is his left), -Y forward, Z up.
Run: blender -b -P tools/blender/crew_islander_v9.py  (or python with bpy)
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
OUT=ROOT/'crew-islander-v9'
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=HERE/'source/crew-islander-v9.blend'
SOURCE.parent.mkdir(parents=True,exist_ok=True)
PALETTE={'linen':'#E4DDCD','fold':'#CFC6B2','skin':'#D99259',
         'pants':'#2E5A69','pantcuff':'#3A6979','sash':'#CF4136',
         'knot':'#B53A31','hair':'#35271F','eye':'#1D1916',
         'mouth':'#9B3A2E','sole':'#3F2B20','wood':'#A0703F',
         'strap':'#6A4A2F','patch':'#8C5B35','stitch':'#3E2A1C','wrap':'#ECE6D8'}
# Cloth colours that get the faint painted variation (never skin or face marks).
JITTER={'linen','fold','pants','pantcuff','sash','knot','hair','wood','patch','wrap'}


def _hex(h):
    h=h.lstrip('#');return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))


def srgb_to_linear(c):
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)


COL={k:srgb_to_linear(_hex(v)) for k,v in PALETTE.items()}
MODELS=[]
AUDIT={}
N=16   # ring sides; vertex 12 is dead centre front, vertex 4 dead centre back
BOX=[(-.72,-1),(.72,-1),(1,-.72),(1,.72),(.72,1),(-.72,1),(-1,.72),(-1,-.72)]
# (z, y centre, half width, half depth) for the tunic and for the head.
TUNIC=[(.34,0,.215,.165),(.40,0,.215,.165),(.50,0,.22,.168),(.62,-.005,.228,.17),
       (.72,-.01,.232,.168),(.78,-.01,.228,.165),(.84,-.015,.215,.18),(.90,-.015,.238,.205)]
HEAD=[(.74,-.01,.09,.085),(.80,-.012,.13,.12),(.83,-.016,.185,.165),(.88,-.02,.203,.182),
      (1.00,-.02,.207,.186),(1.10,-.016,.20,.18),(1.16,-.01,.17,.155),(1.195,-.006,.115,.105)]
SQUARE=.55   # superellipse exponent: lower is boxier


def prof(z,table):
    for (z0,*a),(z1,*b) in zip(table,table[1:]):
        if z<=z1:
            t=max(0,min(1,(z-z0)/(z1-z0)));return [p+(q-p)*t for p,q in zip(a,b)]
    return list(table[-1][1:])


def corner(a):
    c,s=math.cos(a),math.sin(a)
    return math.copysign(abs(c)**SQUARE,c),math.copysign(abs(s)**SQUARE,s)


def around(z,grow=0.,table=TUNIC,tilt=0.,n=N):
    """A ring hugging a rounded-box surface at height z, pushed out by grow.
    With tilt the ring slants (z rises toward +x) and still hugs the surface."""
    pts=[]
    for i in range(n):
        cx,cy=corner(i*math.tau/n)
        zz=z
        for _ in range(4):
            y,rx,ry=prof(zz,table);zz=z+tilt*(rx+grow)*cx
        y,rx,ry=prof(zz,table)
        pts.append(((rx+grow)*cx,y+(ry+grow)*cy,zz))
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
        for k,(p,c) in enumerate(zip(me.polygons,self.colors)):
            col=COL[c]
            if c in JITTER and not skin:
                # Deterministic +-4% per face: a hint of the painted cloth.
                j=1+.04*math.sin(k*12.9898+len(self.name)*78.233)
                col=tuple(min(1,v*j) for v in col)
            for li in p.loop_indices:attr.data[li].color=(*col,1)
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


def frame(direction):
    d=Vector(direction).normalized()
    v=Vector((0,1,0))
    if abs(d.dot(v))>.95:v=Vector((0,0,1))
    v=(v-d*v.dot(d)).normalized()
    return d,v.cross(d).normalized(),v


def section(center,direction,rx,ry,n=8):
    d,u,v=frame(direction)
    return [Vector(center)+u*rx*math.cos(i*math.tau/n)+v*ry*math.sin(i*math.tau/n) for i in range(n)]


def block(center,direction,rx,ry):
    """A chamfered square section: the blocky limb profile."""
    d,u,v=frame(direction)
    return [Vector(center)+u*rx*a+v*ry*b for a,b in BOX]


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


def band(m,z,height,grow,color,weights,table=TUNIC,tilt=0.,thick=.012):
    # A closed cloth band hugging the surface: outer and inner walls, no caps.
    rings=[around(z,grow+thick,table,tilt),around(z+height,grow+thick,table,tilt),
           around(z+height,grow,table,tilt),around(z,grow,table,tilt)]
    ids=[m.ring(r,weights) for r in rings]
    for a,b in zip(ids,ids[1:]+ids[:1]):m.bridge(a,b,color)


def body_weights(p):
    z=p[2]
    if z<.42:return {'pelvis':1}
    if z<.56:t=(z-.42)/.14;return {'pelvis':1-t,'spine':t}
    if z<.86:return {'spine':1}
    t=clamp01((z-.86)/.05)*.25;return {'spine':1-t,'head':t}


def head_weights(p):
    t=clamp01((p[2]-.78)/.06);return {'spine':1-t,'head':t}


REST={
    'root':((0,0,.02),(0,0,.20),None),
    'pelvis':((0,0,.42),(0,0,.52),'root'),
    'spine':((0,0,.52),(0,0,.82),'pelvis'),
    'head':((0,0,.82),(0,0,1.20),'spine')}
for s in [-1,1]:
    upper=side_name('upper_arm',s);fore=side_name('forearm',s);hand=side_name('hand',s)
    thigh=side_name('thigh',s);shin=side_name('shin',s);foot=side_name('foot',s)
    REST[upper]=((s*.20,-.01,.76),(s*.30,-.03,.60),'spine')
    REST[fore]=(REST[upper][1],(s*.33,-.045,.47),upper)
    REST[hand]=(REST[fore][1],(s*.345,-.05,.35),fore)
    REST[thigh]=((s*.11,0,.42),(s*.11,-.005,.26),'pelvis')
    REST[shin]=(REST[thigh][1],(s*.11,0,.09),thigh)
    REST[foot]=(REST[shin][1],(s*.11,-.12,.03),shin)


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
    """Squared smock: ragged zigzag hem, shoulders stepping in to a tall
    stand-up collar with a V cut at the front."""
    m=Mesh('Tunic')
    def w(p):
        wt=body_weights(p)
        if .64<p[2]<=.78 and abs(p[0])>.17:
            s=1 if p[0]>0 else -1;k=.15*min(1,(p[2]-.64)/.14)
            wt={n:v*(1-k) for n,v in wt.items()};wt[side_name('upper_arm',s)]=k
        return wt
    heights=[.40,.50,.62,.72,.78,.84]
    rings=[m.ring(around(z),w) for z in heights]
    for a,b in zip(rings,rings[1:]):m.bridge(a,b,'linen')
    # Zigzag hem: alternate vertices drop, so the edge reads as torn cloth.
    drops=[.30,.375,.33,.39,.31,.37,.285,.385,.32,.38,.30,.365,.335,.39,.295,.375]
    teeth=m.ring([(x*1.02,y*1.02,drops[i]) for i,(x,y,z) in enumerate(around(.40,.004))],
                 {'pelvis':1})
    m.bridge(teeth,rings[0],'linen')
    lining=m.ring([(x*.84,y*.84,.43) for x,y,z in around(.40)],{'pelvis':1})
    m.bridge(lining,teeth,'fold')
    # Collar: V-cut front (vertex 12 is centre front), folded rim inside.
    drop={12:.80,11:.845,13:.845,10:.88,14:.88,3:.875,4:.87,5:.875,2:.885,6:.885}
    top=[(x,y,drop.get(i,z)) for i,(x,y,z) in enumerate(around(.90))]
    inner=[(x,y,drop.get(i,z)-.012) for i,(x,y,z) in enumerate(around(.90,-.014))]
    t=m.ring(top,body_weights);m.bridge(rings[-1],t,'linen')
    ii=m.ring(inner,body_weights);m.bridge(t,ii,'fold')
    m.finish()


def sleeves():
    m=Mesh('Sleeves')
    for s in [-1,1]:
        upper=side_name('upper_arm',s)
        a,e,_=REST[upper];d=Vector(e)-Vector(a)
        prev=None
        for p,r in [(Vector(a)-d*.22,.080),(Vector(a),.092),(lerp(a,e,.35),.094),(lerp(a,e,.52),.096)]:
            ring=m.ring(block(p,d,r,r*.92),{upper:1})
            if prev is None:m.close(list(reversed(ring)),'linen')
            else:m.bridge(prev,ring,'linen')
            prev=ring
        # Ragged cuff: alternate corners hang lower along the arm.
        dn=d.normalized()
        rag=m.ring([Vector(q)+dn*(.045 if i%2==0 else .012) for i,q in
                    enumerate(block(lerp(a,e,.52),d,.098,.090))],{upper:1})
        m.bridge(prev,rag,'linen')
        inner=m.ring(block(lerp(a,e,.50),d,.076,.070),{upper:1})
        m.bridge(rag,inner,'fold')
    m.finish()


def sash():
    """Diagonal red sash from the left shoulder to a big knot on the right
    hip, with two long tails."""
    m=Mesh('Sash')
    band(m,.52,.12,.006,'sash',body_weights,tilt=.72,thick=.016)
    loft(m,[(-.225,-.14,.33,.05,.04),(-.236,-.155,.38,.08,.066),(-.236,-.155,.43,.078,.064),
            (-.225,-.14,.47,.05,.04)],
         'knot',body_weights,[(math.cos(i*math.tau/8),math.sin(i*math.tau/8)) for i in range(8)])
    tube(m,[((-.25,-.17,.36),.050),((-.275,-.185,.23),.046),((-.29,-.19,.10),.032)],'sash',{'pelvis':1},flat=.3)
    tube(m,[((-.205,-.18,.36),.046),((-.21,-.20,.24),.042),((-.215,-.21,.13),.028)],'sash',{'pelvis':1},flat=.3)
    m.finish()


def wrist_wrap():
    # Cloth wrap on his right forearm, just above the fist.
    m=Mesh('Wrap');s=-1
    fore=side_name('forearm',s);e,w,_=REST[fore]
    d=Vector(w)-Vector(e)
    rings=[m.ring(block(lerp(e,w,t),d,r,r*.94),{fore:1}) for t,r in
           [(.50,.084),(.80,.082),(.80,.072),(.50,.074)]]
    for a,b in zip(rings,rings[1:]+rings[:1]):m.bridge(a,b,'wrap')
    m.finish()


def shorts():
    m=Mesh('Shorts')
    for s in [-1,1]:
        thigh=side_name('thigh',s);shin=side_name('shin',s);x=s*.11
        # Baggy shorts down past the knee, with a deep rolled cuff at mid-shin.
        rows=[(.47,.100,{'pelvis':.6,thigh:.4},'pants'),(.38,.106,{thigh:1},'pants'),
              (.30,.110,{thigh:.7,shin:.3},'pants'),(.25,.110,{thigh:.4,shin:.6},'pants'),
              (.24,.108,{shin:1},'pants'),(.239,.116,{shin:1},'pantcuff'),
              (.185,.116,{shin:1},'pantcuff'),(.184,.088,{shin:1},'pantcuff'),(.215,.086,{shin:1},'pants')]
        prev=None
        for z,r,wt,color in rows:
            ring=m.ring([(x+a*r,b*r*.95,z) for a,b in BOX],wt)
            if prev is None:m.close(list(reversed(ring)),'pants')
            else:m.bridge(prev,ring,color)
            prev=ring
    o=m.finish();o['expected_boundary_loops']=2
    return o


def legs():
    for s in [-1,1]:
        foot=side_name('foot',s);shin=side_name('shin',s);thigh=side_name('thigh',s);x=s*.11
        def weights(p):
            # The hidden top of the shin, under the knee, half follows the thigh.
            if p[2]>.21:k=.5*clamp01((p[2]-.21)/.02);return {shin:1-k,thigh:k}
            t=clamp01((p[2]-.09)/.07);return {foot:1-t,shin:t}
        m=Mesh('Leg_Foot'+('.R' if s>0 else '.L'))
        loft(m,[(x,0,.21,.062,.062),(x,0,.13,.065,.065),(x,-.01,.095,.068,.082),
                (x,-.06,.068,.09,.13),(x,-.065,.047,.09,.135)],'skin',weights,BOX)
        o=m.finish(skin=True);o['expected_components']=1;o['expected_boundary_loops']=0
        m=Mesh('Sandal'+('.R' if s>0 else '.L'))
        loft(m,[(x,-.065,0,.098,.147),(x,-.065,.018,.098,.147)],'sole',{foot:1},BOX)
        loft(m,[(x,-.065,.018,.096,.144),(x,-.065,.046,.096,.144)],'wood',{foot:1},BOX)
        # Foot +5 mm at z .072 and .087 (interpolated between its .068/.095 rows).
        ring=loft(m,[(x,-.0526,.072,.0917,.1279),(x,-.0248,.087,.0795,.1012),
                     (x,-.0248,.087,.0770,.0987),(x,-.0526,.072,.0892,.1254)],'strap',weights,BOX,caps=False)
        m.bridge(ring[-1],ring[0],'strap')
        m.finish()


def arms():
    for s in [-1,1]:
        m=Mesh('Arm_Hand'+('.R' if s>0 else '.L'))
        upper=side_name('upper_arm',s);fore=side_name('forearm',s);hand=side_name('hand',s)
        a,e,_=REST[upper];w=REST[fore][1];end=REST[hand][1]
        direction=Vector(end)-Vector(a)
        rows=[(lerp(a,e,.30),.070,.066,{upper:1}),
              (lerp(a,e,.80),.070,.066,{upper:.8,fore:.2}),
              (Vector(e),.068,.064,{upper:.5,fore:.5}),
              (lerp(e,w,.45),.068,.064,{fore:1}),
              (lerp(e,w,.95),.056,.053,{fore:.7,hand:.3}),
              (lerp(w,end,.12),.066,.058,{hand:1}),
              (lerp(w,end,.40),.086,.074,{hand:1}),
              (lerp(w,end,.80),.088,.076,{hand:1}),
              (lerp(w,end,1.08),.074,.064,{hand:1}),
              (lerp(w,end,1.16),.050,.044,{hand:1})]
        rings=[m.ring(block(p,direction,rx,ry),weights) for p,rx,ry,weights in rows]
        m.close(rings[0],'skin')
        # Thumb from the inward-forward corner of the palm (BOX quad 1-2 or 7-0).
        side=1 if s>0 else 7
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
    m=Mesh('Head')
    rows=[.74,.80,.83,.88,1.00,1.10,1.16,1.195]
    rings=[m.ring(around(z,0,HEAD),head_weights) for z in rows]
    for a,b in zip(rings,rings[1:]):m.bridge(a,b,'skin')
    top=m.ring([(x*.5,y,1.205) for x,y,z in around(1.195,0,HEAD)],{'head':1})
    m.bridge(rings[-1],top,'skin')
    m.close(list(reversed(rings[0])),'skin');m.close(top,'skin')
    o=m.finish(skin=True);o['expected_components']=1;o['expected_boundary_loops']=0
    return o


def hair_and_headband():
    m=Mesh('Hair')
    # A full, rounded dome of hair bulging above the headband.
    crown=around(1.17,.034,HEAD)
    rows=[around(1.04,.012,HEAD),around(1.10,.016,HEAD),around(1.15,.034,HEAD),crown,
          [(x*.80,y*.80+.004,1.225) for x,y,z in crown],[(x*.46,y*.46+.004,1.262) for x,y,z in crown]]
    rings=[m.ring(r,{'head':1}) for r in rows]
    for a,b in zip(rings,rings[1:]):m.bridge(a,b,'hair')
    m.close(rings[-1],'hair');m.close(list(reversed(rings[0])),'hair')
    # Small tuft on top, tipped forward like the reference.
    loft(m,[(.0,-.02,1.24,.07,.055),(.005,-.07,1.285,.045,.034),(.01,-.115,1.295,.012,.01)],
         'hair',{'head':1})
    m.finish()
    m=Mesh('Headband')
    band(m,1.055,.085,.026,'sash',{'head':1},table=HEAD,thick=.016)
    ball=[(math.cos(i*math.tau/8),math.sin(i*math.tau/8)) for i in range(8)]
    loft(m,[(.228,.02,1.05,.038,.038),(.248,.02,1.08,.062,.06),(.25,.02,1.125,.06,.058),
            (.228,.02,1.15,.032,.032)],'knot',{'head':1},ball)
    tube(m,[((.27,.03,1.09),.044),((.33,.06,1.00),.042),((.36,.08,.88),.030)],'sash',{'head':1},flat=.3)
    tube(m,[((.26,.07,1.08),.040),((.30,.13,.98),.037),((.315,.16,.87),.026)],'sash',{'head':1},flat=.3)
    tube(m,[((.265,-.01,1.08),.036),((.32,-.03,.99),.032),((.34,-.04,.91),.022)],'sash',{'head':1},flat=.3)
    m.finish()


def caster(obj):
    me=obj.data
    tree=BVHTree.FromPolygons([v.co.copy() for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
    def hit(x,z,side=None,y0=-2):
        if side:o=Vector((side*2,-.02,z));d=Vector((-side,0,0))
        else:o=Vector((x,y0,z));d=Vector((0,1,0))
        p,n,_,_=tree.ray_cast(o,d);assert p is not None,(obj.name,x,z);return p,n
    return hit


def plate(m,hit,x,z,w,h,depth,color,weights,side=None,roll=0.):
    """A small block laid flush on a surface found by ray cast."""
    p,n=hit(x,z,side)
    up=Vector((0,0,1));u=up.cross(n).normalized();v=n.cross(u).normalized()
    c,sn=math.cos(roll),math.sin(roll);u,v=u*c+v*sn,v*c-u*sn
    pts=[]
    for dz in [-depth*.4,depth]:
        for a,b in BOX:pts.append(p+n*dz+u*a*w/2+v*b*h/2)
    ids=m.ring(pts,weights)
    m.bridge(ids[:8],ids[8:],color);m.close(list(reversed(ids[:8])),color);m.close(ids[8:],color)


def face(head_obj):
    hit=caster(head_obj)
    m=Mesh('Face_details')
    for s in [-1,1]:
        plate(m,hit,s*.086,.968,.052,.074,.008,'eye',{'head':1})
        plate(m,hit,s*.09,1.024,.088,.022,.01,'hair',{'head':1},roll=-s*.06)
    plate(m,hit,0,.862,.056,.014,.006,'mouth',{'head':1})
    m.finish()
    m=Mesh('Nose_Ears')
    # Pyramid nose: square base on the face, apex forward and a little down.
    p,n=hit(0,.925)
    up=Vector((0,0,1));u=up.cross(n).normalized();v=n.cross(u).normalized()
    base=[m.vertex(p-n*.01+u*a*.034+v*b*.038,{'head':1}) for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    apex=m.vertex(p+n*.075-v*.022,{'head':1})
    m.close(list(reversed(base)),'skin')
    for i in range(4):m.face([base[i],base[(i+1)%4],apex],'skin')
    for s in [-1,1]:
        plate(m,hit,0,.96,.08,.09,.034,'skin',{'head':1},side=s)
    m.finish(skin=True)


def patches(tunic_obj,shorts_obj):
    """Sewn repairs, as in the reference: two planks over a stitch on the
    tunic (his left, low chest) and one on the left shorts leg."""
    m=Mesh('Patches')
    hit=caster(tunic_obj)
    plate(m,hit,.115,.53,.016,.15,.006,'stitch',body_weights,roll=.12)
    plate(m,hit,.115,.575,.10,.032,.012,'patch',body_weights,roll=.18)
    plate(m,hit,.12,.49,.10,.032,.012,'patch',body_weights,roll=-.1)
    hit=caster(shorts_obj)
    plate(m,hit,.10,.32,.085,.035,.01,'patch',{side_name('thigh',1):1},roll=.1)
    m.finish()


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
    cam.location=eye;cam.rotation_euler=(Vector((0,-.02,.64))-cam.location).to_track_quat('-Z','Y').to_euler()
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
    scene.world.color=srgb_to_linear(_hex('#6F93A8'))
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False;scene.render.resolution_percentage=100


for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
CLOTH=mat('Crew_Cloth');SKIN=mat('Crew_Skin_Preview');RIG=rig()
tunic();sleeves();sash();wrist_wrap();legs();arms()
face(head());hair_and_headband()
patches(bpy.data.objects['Tunic'],shorts())
AUDIT['topology']={o.name:topology(o) for o in MODELS}
AUDIT['triangles']=sum(d['triangles'] for d in AUDIT['topology'].values())
scene=bpy.context.scene;setup_render(scene)
cd=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',cd);scene.collection.objects.link(cam)
scene.camera=cam;cd.type='ORTHO'
AUDIT['poses']={}
# The arm leaves the body at an angle, so its root is always partly inside the
# tunic; that is covered by the sleeve and is not checked.
PAIRS=[('Sleeves','Arm_Hand.L'),('Sleeves','Arm_Hand.R'),('Wrap','Arm_Hand.L'),
       ('Shorts','Leg_Foot.L'),('Shorts','Leg_Foot.R'),
       ('Sandal.L','Leg_Foot.L'),('Sandal.R','Leg_Foot.R'),
       ('Tunic','Head')]
for frame_no,kind in [(1,'neutral'),(21,'working'),(41,'reach'),(61,'crouch'),(81,'stride')]:
    scene.frame_set(frame_no);pose(kind)
    for pb in RIG.pose.bones:
        pb.rotation_mode='QUATERNION'
        pb.keyframe_insert('location',frame=frame_no);pb.keyframe_insert('rotation_quaternion',frame=frame_no)
        pb.keyframe_insert('scale',frame=frame_no)
    RIG.keyframe_insert('location',frame=frame_no)
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
        render('left',(6,-.3,.9));render('right',(-6,-.3,.9))
        render('front',(0,-6,.9));render('back',(0,6,.9))
        render('closeup',(1.2,-2.6,1.6),(1000,1000),scale=.75)
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
