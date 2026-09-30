"""Islander villager v12: v11 with a longer tunic, a deeper V, a broader face,
and about half the triangles (coarser base shapes, harder decimation, 4-sided
plates and lighter knots). Kevin: "you're using a lot of shapes to make
something you could do with less faces."

Previous header (v11):

crew-islander-v9/reference.jpg was measured view by view (front, back, left,
right, hero and detail crops); every height below is the reference's fraction
of total height times 1.30 m. v10 had the right sculpted surface but the wrong
proportions. v11 fixes both:
  - head: a rounded cube ~34% of the height, sitting down in a thick cowl collar
    with a V at the front,
  - tunic: a deep, gently barrelled bell reaching to ~27% with long irregular
    torn teeth; loose short sleeves with torn edges down to the elbow,
  - huge forearms and fists held out at hip height in a slight A pose,
  - shorts: a short baggy band and a thick rolled cuff just above the ankle,
  - thick two-layer platform sandals with a strap; feet ~22% of height long,
  - headband flaring wider than the head; ball knot on his left with four flat
    ribbon tails; the sash runs from his left shoulder to a ball knot on his
    right hip with three flat tails,
  - rectangular eyes, bar brows, pyramid nose, small red mouth, block ears,
  - plank-and-stitch patches (tunic front, tunic back, shorts), right wrist wrap.
Rounded volumes are smoothed one level and decimated into irregular facets
(the reference's painted low-poly surface); ribbons, knots, face marks,
patches and sandal soles are built crisp.

Runtime contract (unchanged from the in-game deckhand crew-astra-no-hat-v5):
16 bones with the same names and hierarchy; skinned CREW_Cloth and CREW_Skin
meshes in rest pose; skin vertex colours exported white for the CrewVertexColor
sickness tint (skin _BaseColor sRGB #D99259); flat vertex colours, no textures.

Blender coordinates: X across the shoulders (+X is his left), -Y forward, Z up.
Run: blender -b -P tools/blender/crew_islander_v11.py  (or python with bpy)
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
OUT=ROOT/'crew-islander-v12'
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=HERE/'source/crew-islander-v12.blend'
SOURCE.parent.mkdir(parents=True,exist_ok=True)
# Sampled from the reference's lit mid-tones.
PALETTE={'linen':'#D8CFBC','fold':'#BDB29B','skin':'#D99259',
         'pants':'#2D5664','pantcuff':'#2F6572','sash':'#D0443A',
         'knot':'#B8392F','hair':'#3A2921','eye':'#1C1816',
         'mouth':'#A23B2F','sole':'#4A3226','wood':'#B07A4A',
         'strap':'#5E4030','patch':'#8E5C38','stitch':'#3E2A1C','wrap':'#EAE3D3'}
JITTER={'linen','fold','pants','pantcuff','sash','knot','hair','wood','patch','wrap'}


def _hex(h):
    h=h.lstrip('#');return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))


def srgb_to_linear(c):
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)


COL={k:srgb_to_linear(_hex(v)) for k,v in PALETTE.items()}
MODELS=[]
AUDIT={}
N=12   # ring sides; vertex 9 is dead centre front, vertex 3 dead centre back
BOX=[(-.72,-1),(.72,-1),(1,-.72),(1,.72),(.72,1),(-.72,1),(-1,.72),(-1,-.72)]
# (z, y centre, half width, half depth), measured from the reference views.
TUNIC=[(.27,0,.25,.205),(.36,-.005,.256,.208),(.45,-.01,.266,.213),(.56,-.012,.272,.216),
       (.66,-.012,.266,.211),(.74,-.012,.26,.204),(.79,-.012,.25,.196),(.85,-.012,.275,.232)]
# Broad face: cheeks and jaw wider than the crown. The rows below .78 are the
# neck and upper chest, hidden in the tunic except through the deep V.
HEAD=[(.64,-.035,.13,.125),(.72,-.03,.14,.13),(.78,-.024,.17,.15),(.80,-.024,.215,.176),(.84,-.028,.24,.192),
      (.95,-.03,.248,.203),(1.04,-.026,.24,.2),(1.12,-.02,.22,.19),(1.18,-.015,.18,.16),(1.22,-.01,.115,.105)]
SQUARE={'tunic':.82,'head':.66}   # superellipse exponent: lower is boxier
RATIO=.2


def prof(z,table):
    for (z0,*a),(z1,*b) in zip(table,table[1:]):
        if z<=z1:
            t=max(0,min(1,(z-z0)/(z1-z0)));return [p+(q-p)*t for p,q in zip(a,b)]
    return list(table[-1][1:])


def corner(a,e):
    c,s=math.cos(a),math.sin(a)
    return math.copysign(abs(c)**e,c),math.copysign(abs(s)**e,s)


def around(z,grow=0.,table=TUNIC,tilt=0.,n=N):
    """A ring hugging a rounded-box surface at height z, pushed out by grow.
    With tilt the ring slants (z rises toward +x) and still hugs the surface."""
    e=SQUARE['head' if table is HEAD else 'tunic']
    pts=[]
    for i in range(n):
        cx,cy=corner(i*math.tau/n,e)
        zz=z
        for _ in range(4):
            y,rx,ry=prof(zz,table);zz=z+tilt*(rx+grow)*cx
        y,rx,ry=prof(zz,table)
        pts.append(((rx+grow)*cx,y+(ry+grow)*cy,zz))
    return pts


class Mesh:
    def __init__(self,name):
        self.name=name;self.v=[];self.f=[];self.colors=[];self.weights=[];self.creases=[]

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

    def crease(self,ring):
        # Hard corners through smoothing: every edge at these vertices creased.
        self.creases+=list(ring)

    def finish(self,skin=False,sculpt=True,ratio=None):
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
            if c in JITTER and not skin and not sculpt:
                j=1+.045*math.sin(k*12.9898+len(self.name)*78.233)
                col=tuple(min(1,v*j) for v in col)
            for li in p.loop_indices:attr.data[li].color=(*col,1)
        me.color_attributes.active_color=attr
        bm=bmesh.new();bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        for f in bm.faces:f.smooth=False
        if self.creases:
            layer=bm.edges.layers.float.get('crease_edge') or bm.edges.layers.float.new('crease_edge')
            bm.verts.ensure_lookup_table()
            for a in self.creases:
                for e in bm.verts[remap[a]].link_edges:e[layer]=1.
        bm.to_mesh(me);bm.free()
        groups={n:o.vertex_groups.new(name=n) for n in sorted({n for w in self.weights for n in w})}
        for i,w in enumerate(self.weights):
            total=sum(w.values())
            assert total>0
            for n,value in w.items():
                if value>0:groups[n].add([i],value/total,'REPLACE')
        if sculpt:sculpt_pass(o,skin,ratio or RATIO)
        mod=o.modifiers.new('Crew deformation','ARMATURE');mod.object=RIG
        mod.use_deform_preserve_volume=False
        o.parent=RIG;o['skin_tint']=skin
        MODELS.append(o)
        return o


def sculpt_pass(o,skin,ratio):
    """Round the volume (one smoothing level), collapse it into irregular
    facets, renormalise weights, and give each facet one flat colour: its
    nearest palette colour plus a faint shade of its own (cloth only)."""
    sub=o.modifiers.new('Round','SUBSURF');sub.levels=1;sub.render_levels=1
    dec=o.modifiers.new('Facet','DECIMATE');dec.ratio=ratio;dec.use_collapse_triangulate=True
    with bpy.context.temp_override(object=o,active_object=o,selected_objects=[o]):
        bpy.ops.object.modifier_apply(modifier='Round');bpy.ops.object.modifier_apply(modifier='Facet')
    me=o.data
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.dissolve_degenerate(bm,dist=1e-6,edges=bm.edges[:])
    bm.to_mesh(me);bm.free()
    for v in me.vertices:
        total=sum(g.weight for g in v.groups)
        for g in v.groups:g.weight=g.weight/total
    attr=me.color_attributes['Col']
    for k,p in enumerate(me.polygons):
        avg=[sum(attr.data[li].color[c] for li in p.loop_indices)/p.loop_total for c in range(3)]
        key=min(COL,key=lambda n:sum((a-b)**2 for a,b in zip(avg,COL[n])))
        col=COL[key]
        if key in JITTER and not skin:
            j=1+.055*math.sin(k*12.9898+len(o.name)*78.233)
            col=tuple(min(1,v*j) for v in col)
        for li in p.loop_indices:attr.data[li].color=(*col,1)
        p.use_smooth=False


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


def ball(m,c,r,color,weights,squash=1.):
    """A faceted knot: an 8-sided sphere with 5 rings."""
    rows=[]
    for t in [-.85,-.3,.3,.85]:
        rr=r*math.sqrt(1-t*t)
        rows.append((c[0],c[1],c[2]+t*r*squash,rr,rr))
    hex6=[(math.cos(i*math.tau/6),math.sin(i*math.tau/6)) for i in range(6)]
    loft(m,rows,color,weights,hex6)


def ribbon(m,path,width,color,weights,thick=.012,twist=0.,out=Vector((1,0,0))):
    """A flat cloth tail: a thin band along a polyline, turning by twist, with
    a torn V at the end."""
    prev=None;n=len(path)
    for j,p in enumerate(path):
        p=Vector(p);d=Vector(path[min(j+1,n-1)])-Vector(path[max(j-1,0)]);d.normalize()
        side=(out-d*out.dot(d)).normalized()
        a=twist*j/max(1,n-1);nrm=d.cross(side).normalized()
        side,nrm=side*math.cos(a)+nrm*math.sin(a),nrm*math.cos(a)-side*math.sin(a)
        w=width*(1-.15*j/max(1,n-1))
        pts=[p+side*w/2+nrm*thick/2,p-side*w/2+nrm*thick/2,p-side*w/2-nrm*thick/2,p+side*w/2-nrm*thick/2]
        if j==n-1:
            # Torn end: the middle of the last edge pulled back up the tail.
            back=Vector(path[n-2])-p;back.normalize()
            mid=[p+back*w*.45+nrm*thick/2,p+back*w*.45-nrm*thick/2]
            r=m.ring(pts,weights);ids=m.ring(mid,weights)
            m.bridge(prev,r,color)
            m.face([r[0],ids[0],r[1]],color);m.face([r[3],r[2],ids[1]],color)
            m.face([r[0],r[3],ids[1],ids[0]],color);m.face([r[1],ids[0],ids[1],r[2]],color)
            return
        r=m.ring(pts,weights)
        if prev is None:m.close(list(reversed(r)),color)
        else:m.bridge(prev,r,color)
        prev=r


def band(m,z,height,grow,color,weights,table=TUNIC,tilt=0.,thick=.012,flare=0.):
    rings=[around(z,grow+thick,table,tilt),around(z+height,grow+thick+flare,table,tilt),
           around(z+height,grow+flare,table,tilt),around(z,grow,table,tilt)]
    ids=[m.ring(r,weights) for r in rings]
    for a,b in zip(ids,ids[1:]+ids[:1]):m.bridge(a,b,color)


def body_weights(p):
    z=p[2]
    if z<.40:return {'pelvis':1}
    if z<.52:t=(z-.40)/.12;return {'pelvis':1-t,'spine':t}
    if z<.83:return {'spine':1}
    t=clamp01((z-.83)/.03)*.2;return {'spine':1-t,'head':t}


def head_weights(p):
    t=clamp01((p[2]-.79)/.05);return {'spine':1-t,'head':t}


REST={
    'root':((0,0,.02),(0,0,.20),None),
    'pelvis':((0,0,.36),(0,0,.45),'root'),
    'spine':((0,0,.45),(0,0,.80),'pelvis'),
    'head':((0,0,.80),(0,0,1.25),'spine')}
for s in [-1,1]:
    upper=side_name('upper_arm',s);fore=side_name('forearm',s);hand=side_name('hand',s)
    thigh=side_name('thigh',s);shin=side_name('shin',s);foot=side_name('foot',s)
    REST[upper]=((s*.225,-.01,.75),(s*.29,-.02,.62),'spine')
    REST[fore]=(REST[upper][1],(s*.345,-.03,.49),upper)
    REST[hand]=(REST[fore][1],(s*.368,-.035,.37),fore)
    REST[thigh]=((s*.131,0,.40),(s*.131,-.005,.24),'pelvis')
    REST[shin]=(REST[thigh][1],(s*.131,0,.12),thigh)
    REST[foot]=(REST[shin][1],(s*.131,-.14,.06),shin)


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
    """Deep bell tunic: long torn teeth at the hem, a thick cowl collar
    that rolls outward and frames the jaw, V-cut at the front."""
    m=Mesh('Tunic')
    def w(p):
        wt=body_weights(p)
        if .62<p[2]<=.79 and abs(p[0])>.17:
            s=1 if p[0]>0 else -1;k=.15*min(1,(p[2]-.62)/.17)
            wt={n:v*(1-k) for n,v in wt.items()};wt[side_name('upper_arm',s)]=k
        return wt
    heights=[.30,.42,.56,.66,.74,.79]
    rings=[m.ring(around(z),w) for z in heights]
    for a,b in zip(rings,rings[1:]):m.bridge(a,b,'linen')
    drops=[.215,.28,.235,.29,.205,.275,.225,.29,.21,.27,.235,.285]
    teeth=m.ring([(x*1.015,y*1.015,drops[i]) for i,(x,y,z) in enumerate(around(.30,.004))],{'pelvis':1})
    m.bridge(teeth,rings[0],'linen');m.crease(teeth)
    lining=m.ring([(x*.94,y*.94,.33) for x,y,z in around(.30)],{'pelvis':1})
    m.bridge(lining,teeth,'fold')
    # Cowl: out and up from the shoulders, rolled over, tucked down inside.
    drop={9:.665,8:.745,10:.745,7:.815,11:.815}   # deep V at centre front
    outer=[(x,y,drop.get(i,z)) for i,(x,y,z) in enumerate(around(.85,.004))]
    lip=[(x,y,drop.get(i,z)-.016) for i,(x,y,z) in enumerate(around(.85,-.026))]
    tuck=[(x,y,drop.get(i,.85)-.05) for i,(x,y,z) in enumerate(around(.85,-.03))]
    a=m.ring(outer,body_weights);m.bridge(rings[-1],a,'linen')
    b=m.ring(lip,body_weights);m.bridge(a,b,'fold')
    c=m.ring(tuck,body_weights);m.bridge(b,c,'fold')
    m.finish(ratio=.2)


def sleeves():
    m=Mesh('Sleeves')
    for s in [-1,1]:
        upper=side_name('upper_arm',s)
        a,e,_=REST[upper];d=Vector(e)-Vector(a);dn=d.normalized()
        prev=None
        for p,r in [(Vector(a)-d*.25,.085),(Vector(a),.098),(lerp(a,e,.38),.104),(lerp(a,e,.60),.108)]:
            ring=m.ring(section(p,d,r,r*.94),{upper:1})
            if prev is None:m.close(list(reversed(ring)),'linen')
            else:m.bridge(prev,ring,'linen')
            prev=ring
        rag_len=[.045,.012,.036,.01,.05,.015,.032,.012]
        rag=m.ring([Vector(q)+dn*rag_len[i] for i,q in enumerate(section(lerp(a,e,.60),d,.114,.107))],{upper:1})
        m.bridge(prev,rag,'linen');m.crease(rag)
        inner=m.ring(section(lerp(a,e,.58),d,.09,.085),{upper:1})
        m.bridge(rag,inner,'fold')
    m.finish(ratio=.24)


def sash():
    """Diagonal red sash: his left shoulder down to a ball knot on his right
    hip, three flat tails."""
    m=Mesh('Sash')
    band(m,.585,.09,.014,'sash',body_weights,tilt=.75,thick=.016)
    m.finish(ratio=.3)
    m=Mesh('Sash_Knot')
    ball(m,(-.245,-.175,.455),.055,'knot',{'pelvis':1},squash=.9)
    out=Vector((1,-.25,0))   # ribbons face forward, broad side to the viewer
    ribbon(m,[(-.25,-.19,.43),(-.262,-.205,.35),(-.272,-.212,.27),(-.27,-.215,.19)],.064,'sash',{'pelvis':1},out=out,twist=.4)
    ribbon(m,[(-.225,-.20,.43),(-.215,-.215,.36),(-.21,-.222,.29),(-.214,-.228,.215)],.058,'sash',{'pelvis':1},out=out,twist=-.35)
    ribbon(m,[(-.28,-.17,.43),(-.3,-.18,.37),(-.312,-.185,.31)],.045,'knot',{'pelvis':1},out=Vector((1,.5,0)),twist=.5)
    m.finish(sculpt=False)


def wrist_wrap():
    m=Mesh('Wrap');s=-1
    fore=side_name('forearm',s);e,w,_=REST[fore]
    d=Vector(w)-Vector(e)
    rings=[m.ring(block(lerp(e,w,t),d,r,r*.95),{fore:1}) for t,r in
           [(.56,.094),(.84,.090),(.84,.082),(.56,.086)]]
    for a,b in zip(rings,rings[1:]+rings[:1]):m.bridge(a,b,'wrap')
    m.finish(sculpt=False)


def shorts():
    """Short baggy band under the tunic, thick rolled cuff above the ankle."""
    m=Mesh('Shorts')
    for s in [-1,1]:
        thigh=side_name('thigh',s);shin=side_name('shin',s);x=s*.131
        foot=side_name('foot',s)
        rows=[(.46,.098,.104,{'pelvis':.6,thigh:.4},'pants'),(.36,.100,.108,{thigh:1},'pants'),
              (.28,.100,.108,{thigh:.6,shin:.4},'pants'),(.225,.098,.104,{thigh:.2,shin:.8},'pants'),
              (.224,.108,.114,{shin:1},'pantcuff'),(.168,.108,.114,{shin:.45,foot:.55},'pantcuff'),
              (.167,.082,.086,{shin:1},'pantcuff'),(.20,.08,.084,{shin:1},'pants')]
        prev=None
        for z,rx,ry,wt,color in rows:
            ring=m.ring([(x+a*rx,b*ry,z) for a,b in BOX],wt)
            if prev is None:m.close(list(reversed(ring)),'pants')
            else:m.bridge(prev,ring,color)
            prev=ring
    m.finish(ratio=.22)
    return bpy.data.objects['Shorts']


def legs():
    for s in [-1,1]:
        foot=side_name('foot',s);shin=side_name('shin',s);x=s*.131
        thigh=side_name('thigh',s)
        def weights(p):
            if p[2]>.175:k=.5*clamp01((p[2]-.175)/.01);return {shin:1-k,thigh:k}
            t=clamp01((p[2]-.118)/.03);return {foot:1-t,shin:t}
        m=Mesh('Leg_Foot'+('.R' if s>0 else '.L'))
        loft(m,[(x,0,.185,.064,.068),(x,-.005,.155,.064,.068),(x,-.035,.125,.084,.122),
                (x,-.05,.114,.088,.14),(x,-.05,.098,.088,.142)],'skin',weights,BOX)
        m.finish(skin=True,ratio=.32)
        m=Mesh('Sandal'+('.R' if s>0 else '.L'))
        loft(m,[(x,-.05,0,.099,.153),(x,-.05,.04,.099,.153)],'sole',{foot:1},BOX)
        loft(m,[(x,-.05,.04,.097,.15),(x,-.05,.094,.097,.15)],'wood',{foot:1},BOX)
        m.finish(sculpt=False)
        m=Mesh('Strap'+('.R' if s>0 else '.L'))
        # Dark strap arching over the instep: a thin band across the top of
        # the foot from sole to sole, a few mm proud of the skin.
        arch=[(-.099,.094),(-.099,.118),(-.086,.14),(-.045,.152),(.045,.152),(.086,.14),(.099,.118),(.099,.094)]
        outer=[m.vertex((x+ax,yy,az),{foot:1}) for yy in (-.115,-.082) for ax,az in arch]
        inner=[m.vertex((x+ax*.9,yy,az-.014 if az>.1 else az),{foot:1}) for yy in (-.115,-.082) for ax,az in arch]
        k=len(arch)
        for i in range(k-1):
            m.face([outer[i],outer[i+1],outer[k+i+1],outer[k+i]],'strap')
            m.face([inner[k+i],inner[k+i+1],inner[i+1],inner[i]],'strap')
            m.face([outer[i+1],outer[i],inner[i],inner[i+1]],'strap')
            m.face([outer[k+i],outer[k+i+1],inner[k+i+1],inner[k+i]],'strap')
        m.face([outer[0],outer[k],inner[k],inner[0]],'strap');m.face([outer[k-1],inner[k-1],inner[2*k-1],outer[2*k-1]],'strap')
        m.finish(sculpt=False)


def arms():
    for s in [-1,1]:
        m=Mesh('Arm_Hand'+('.R' if s>0 else '.L'))
        upper=side_name('upper_arm',s);fore=side_name('forearm',s);hand=side_name('hand',s)
        a,e,_=REST[upper];w=REST[fore][1];end=REST[hand][1]
        rows=[(lerp(a,e,.25),.066,.064,{upper:1},Vector(e)-Vector(a)),
              (lerp(a,e,.80),.066,.064,{upper:.8,fore:.2},Vector(e)-Vector(a)),
              (Vector(e),.068,.066,{upper:.5,fore:.5},Vector(w)-Vector(a)),
              (lerp(e,w,.40),.076,.072,{fore:1},Vector(w)-Vector(e)),
              (lerp(e,w,.80),.074,.07,{fore:.9,hand:.1},Vector(w)-Vector(e)),
              (Vector(w),.066,.062,{fore:.5,hand:.5},Vector(end)-Vector(w)),
              (lerp(w,end,.28),.086,.08,{hand:1},Vector(end)-Vector(w)),
              (lerp(w,end,.70),.092,.084,{hand:1},Vector(end)-Vector(w)),
              (lerp(w,end,1.0),.084,.076,{hand:1},Vector(end)-Vector(w)),
              (lerp(w,end,1.12),.052,.046,{hand:1},Vector(end)-Vector(w))]
        rings=[m.ring(block(p,d,rx,ry),weights) for p,rx,ry,weights,d in rows]
        m.close(rings[0],'skin')
        side=1 if s>0 else 7
        for j in range(len(rings)-1):
            for i in range(8):
                if j==6 and i==side:continue
                m.face([rings[j][i],rings[j][(i+1)%8],rings[j+1][(i+1)%8],rings[j+1][i]],'skin')
        root=[rings[6][side],rings[6][(side+1)%8],rings[7][(side+1)%8],rings[7][side]]
        center=sum((Vector(m.v[i]) for i in root),Vector())/4
        previous=root
        for offset,scale in [(Vector((-s*.014,-.028,0)),.95),(Vector((-s*.02,-.046,-.012)),.86),
                             (Vector((-s*.02,-.052,-.03)),.70)]:
            r=m.ring([center+offset+(Vector(m.v[i])-center)*scale for i in root],{hand:1})
            m.bridge(previous,r,'skin');previous=r
        m.close(previous,'skin');m.close(rings[-1],'skin')
        m.finish(skin=True,ratio=.24)


def head():
    m=Mesh('Head')
    rows=[.64,.72,.78,.80,.84,.95,1.04,1.12,1.18,1.22]
    rings=[m.ring(around(z,0,HEAD),head_weights) for z in rows]
    for a,b in zip(rings,rings[1:]):m.bridge(a,b,'skin')
    top=m.ring([(x*.5,y,1.232) for x,y,z in around(1.22,0,HEAD)],{'head':1})
    m.bridge(rings[-1],top,'skin')
    m.close(list(reversed(rings[0])),'skin');m.close(top,'skin')
    return m.finish(skin=True,ratio=.24)


def hair_and_headband():
    m=Mesh('Hair')
    crown=around(1.16,.03,HEAD)
    rows=[around(1.03,.01,HEAD),around(1.10,.014,HEAD),crown,
          [(x*.86,y*.86+.006,1.205) for x,y,z in crown],[(x*.55,y*.55+.008,1.24) for x,y,z in crown]]
    rings=[m.ring(r,{'head':1}) for r in rows]
    for a,b in zip(rings,rings[1:]):m.bridge(a,b,'hair')
    m.close(rings[-1],'hair');m.close(list(reversed(rings[0])),'hair')
    # Small tuft on the crown, a little behind centre.
    loft(m,[(.0,.03,1.23,.075,.06),(.01,.02,1.275,.06,.045),(.02,.0,1.3,.03,.024)],'hair',{'head':1})
    m.finish(ratio=.24)
    m=Mesh('Headband')
    band(m,1.04,.1,.028,'sash',{'head':1},table=HEAD,thick=.016,flare=.008)
    m.finish(ratio=.3)
    m=Mesh('Headband_Knot')
    # Tied at the back-left corner of the head; the tails fall behind and out.
    ball(m,(.235,.15,1.09),.05,'knot',{'head':1})
    out=Vector((.7,.7,0))
    ribbon(m,[(.235,.17,1.065),(.27,.2,1.0),(.3,.225,.94),(.325,.24,.875)],.064,'sash',{'head':1},out=out,twist=.5)
    ribbon(m,[(.22,.19,1.06),(.235,.24,.995),(.245,.275,.935),(.25,.3,.87)],.058,'sash',{'head':1},out=out,twist=-.4)
    ribbon(m,[(.245,.14,1.065),(.29,.15,1.005),(.325,.155,.95),(.345,.16,.905)],.052,'knot',{'head':1},out=out,twist=.3)
    ribbon(m,[(.2,.2,1.06),(.2,.25,1.0),(.195,.285,.945)],.046,'sash',{'head':1},out=Vector((1,-.3,0)),twist=.6)
    m.finish(sculpt=False)


def caster(obj):
    me=obj.data
    tree=BVHTree.FromPolygons([v.co.copy() for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
    def hit(x,z,side=None,back=False):
        if side:o=Vector((side*2,-.02,z));d=Vector((-side,0,0))
        elif back:o=Vector((x,2,z));d=Vector((0,-1,0))
        else:o=Vector((x,-2,z));d=Vector((0,1,0))
        p,n,_,_=tree.ray_cast(o,d);assert p is not None,(obj.name,x,z);return p,n
    return hit


def plate(m,hit,x,z,w,h,depth,color,weights,side=None,roll=0.,back=False):
    p,n=hit(x,z,side,back)
    up=Vector((0,0,1));u=up.cross(n).normalized();v=n.cross(u).normalized()
    c,sn=math.cos(roll),math.sin(roll);u,v=u*c+v*sn,v*c-u*sn
    quad=[(-1,-1),(1,-1),(1,1),(-1,1)]
    pts=[p+n*dz+u*a*w/2+v*b*h/2 for dz in [-depth*.4,depth] for a,b in quad]
    ids=m.ring(pts,weights)
    m.bridge(ids[:4],ids[4:],color);m.close(ids[4:],color)


def face(head_obj):
    hit=caster(head_obj)
    m=Mesh('Face_details')
    for s in [-1,1]:
        plate(m,hit,s*.098,.968,.046,.064,.008,'eye',{'head':1})
        plate(m,hit,s*.098,1.022,.068,.018,.01,'hair',{'head':1})
    plate(m,hit,0,.867,.064,.013,.006,'mouth',{'head':1})
    m.finish(sculpt=False)
    m=Mesh('Nose_Ears')
    p,n=hit(0,.93)
    up=Vector((0,0,1));u=up.cross(n).normalized();v=n.cross(u).normalized()
    base=[m.vertex(p-n*.012+u*a*.036+v*b*.042,{'head':1}) for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    apex=m.vertex(p+n*.064-v*.026,{'head':1})
    m.close(list(reversed(base)),'skin')
    for i in range(4):m.face([base[i],base[(i+1)%4],apex],'skin')
    for s in [-1,1]:plate(m,hit,0,.962,.04,.07,.032,'skin',{'head':1},side=s)
    m.finish(skin=True,sculpt=False)


def patches(tunic_obj,shorts_obj):
    m=Mesh('Patches')
    hit=caster(tunic_obj)
    for back,x,z in [(False,.175,.49),(True,.2,.52)]:
        plate(m,hit,x,z,.014,.105,.006,'stitch',body_weights,roll=.08,back=back)
        plate(m,hit,x,z+.028,.066,.022,.011,'patch',body_weights,roll=.2,back=back)
        plate(m,hit,x+.004,z-.03,.066,.022,.011,'patch',body_weights,roll=-.12,back=back)
    hit=caster(shorts_obj)
    plate(m,hit,.17,.245,.07,.028,.01,'patch',{side_name('thigh',1):1},roll=.12)
    plate(m,hit,.17,.245,.01,.045,.012,'stitch',{side_name('thigh',1):1},roll=.12)
    m.finish(sculpt=False)


def topology(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    d={'vertices':len(bm.verts),'triangles':sum(len(f.verts)-2 for f in bm.faces),
       'overconnected_edges':sum(len(e.link_faces)>2 for e in bm.edges),
       'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces)}
    bm.free()
    d['weights_normalized']=all(abs(sum(g.weight for g in v.groups)-1)<1e-4 for v in o.data.vertices)
    assert d['weights_normalized'],(o.name,d)
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
        # Deep squat with the heel lifted: the reference's low, baggy cuff cannot
        # clear a flat-footed squat (ankle ~67 deg); a real one would fold.
        aim(foot,ankle,(0,-.80,-.60) if kind=='crouch' else (0,-.97,-.24))
    graph=bpy.context.evaluated_depsgraph_get()
    minimum=min((o.evaluated_get(graph).matrix_world@v.co).z
                for o in MODELS if o.name.startswith('Sandal') for v in o.evaluated_get(graph).data.vertices)
    RIG.location.z=-minimum+.005;bpy.context.view_layer.update()


def render(name,eye=(3,5,3),size=(1000,1100),scale=1.62,target=(0,-.02,.64)):
    cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cd.ortho_scale=scale
    scene.render.resolution_x,scene.render.resolution_y=size
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)


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
    render(kind+'-front',(3,-5,2.6))
    if kind=='neutral':
        render('front',(0,-6,.9));render('back',(0,6,.9))
        render('left',(6,-.2,.9));render('right',(-6,-.2,.9))
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
