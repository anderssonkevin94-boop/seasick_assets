"""Islander villager v6: chunky proportions, island clothing, readable at 24 px.

Improves on crew-astra-no-hat-v5 (the deckhand currently in the game) while
keeping its runtime contract, so it can replace Deckhand.fbx in place:
  - the same 16 bones with the same names and hierarchy (VillagerActing and
    AstraPlaytestImport find pelvis/spine/head/upper_arm.*/thigh.*/hand.*),
  - two skinned meshes, CREW_Cloth and CREW_Skin, exported in rest pose,
  - skin vertex colours exported white so CrewVertexColor can tint it
    (sickness green); skin _BaseColor stays sRGB #D99259,
  - flat vertex colours, no textures, faceted normals.

What changed (see README in crew-islander-v6/):
  1. ~3.6 heads tall instead of ~6.5: bigger head, broad torso, short legs.
  2. Undyed tunic with rolled sleeves, cloth sash, cropped rolled trousers,
     bare feet on leather sandals, instead of T-shirt, jeans and riding boots.
  3. One strong accent (coral sash + headcloth) over cream and deep teal.
  4. A silhouette hook: headcloth knot with flared tails, and a hair tuft.
  5. Chunky fists with a real thumb instead of mittens with a spike.
  6. Bolder, simpler face: big eyes, heavy brows, broad nose, mouth, ears.

Blender coordinates: X across the shoulders, -Y forward, Z up.
Run: blender -b -P tools/blender/crew_islander_v6.py  (or python with bpy)
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
OUT=ROOT/'crew-islander-v6'
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=HERE/'source/crew-islander-v6.blend'
SOURCE.parent.mkdir(parents=True,exist_ok=True)
# Cream tunic echoes the approved patched tarps; coral is the one accent;
# deep teal trousers keep the top and bottom halves apart at gameplay size.
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
SHAPE=[(math.cos(i*math.tau/8),math.sin(i*math.tau/8)) for i in range(8)]
TORSO=[(-.72,-1),(.72,-1),(1,-.65),(1,0),(1,.65),
       (.72,1),(-.72,1),(-1,.65),(-1,0),(-1,-.65)]
BOX=[(-.72,-1),(.72,-1),(1,-.72),(1,.72),(.72,1),(-.72,1),(-1,.72),(-1,-.72)]


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
        for e in bm.edges:
            if e.is_manifold:e.smooth=e.calc_face_angle()<math.radians(55)
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
    v=Vector((0,1,0));v=(v-d*v.dot(d)).normalized()
    u=v.cross(d).normalized()
    return [Vector(center)+u*rx*math.cos(i*math.tau/n)+v*ry*math.sin(i*math.tau/n) for i in range(n)]


def match_boundary(mesh,indices,points):
    # Cyclic correspondence preserves the armhole instead of twisting it.
    choices=[]
    for seq in [indices,list(reversed(indices))]:
        for k in range(len(seq)):
            order=seq[k:]+seq[:k]
            error=sum((Vector(mesh.v[j])-Vector(p)).length_squared for j,p in zip(order,points))
            choices.append((error,order))
    return min(choices,key=lambda pair:pair[0])[1]


def loft(m,rows,color,weights,shape=SHAPE,caps=True):
    rs=[]
    for x,y,z,rx,ry in rows:
        r=m.ring([(x+a*rx,y+b*ry,z) for a,b in shape],weights)
        if rs:m.bridge(rs[-1],r,color)
        rs.append(r)
    if caps:m.close(rs[0],color);m.close(rs[-1],color)
    return rs


def tube(m,path,color,weights,n=6):
    # A tapered cloth tail along a polyline of (point, radius) pairs.
    prev=None
    for j,(p,r) in enumerate(path):
        d=Vector(path[min(j+1,len(path)-1)][0])-Vector(path[max(j-1,0)][0])
        ring=m.ring(section(p,d,r,r*.45,n),weights)
        if prev is None:m.close(list(reversed(ring)),color)
        else:m.bridge(prev,ring,color)
        prev=ring
    m.close(prev,color)


# Same bone names and hierarchy as v5; only the rest positions move to the
# new proportions (Unity rescales the model to 1.7 m from its bounds).
REST={
    'root':((0,0,.02),(0,0,.20),None),
    'pelvis':((0,0,.60),(0,0,.72),'root'),
    'spine':((0,0,.72),(0,0,1.12),'pelvis'),
    'head':((0,0,1.12),(0,0,1.60),'spine')}
for s in [-1,1]:
    upper=side_name('upper_arm',s);fore=side_name('forearm',s);hand=side_name('hand',s)
    thigh=side_name('thigh',s);shin=side_name('shin',s);foot=side_name('foot',s)
    REST[upper]=((s*.265,0,1.05),(s*.37,0,.83),'spine')
    REST[fore]=(REST[upper][1],(s*.43,-.01,.63),upper)
    REST[hand]=(REST[fore][1],(s*.46,-.015,.51),fore)
    REST[thigh]=((s*.11,0,.60),(s*.125,-.012,.35),'pelvis')
    REST[shin]=(REST[thigh][1],(s*.125,0,.10),thigh)
    REST[foot]=(REST[shin][1],(s*.125,-.15,.035),shin)


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
    # Undyed smock: flares over the hips, broad barrel chest, short sleeves
    # rolled above the elbow so the forearms are bare (tintable) skin.
    m=Mesh('Tunic')
    rows=[(.56,.234,.167),(.70,.214,.150),(.84,.236,.160),
          (.96,.262,.168),(1.07,.248,.158),(1.115,.108,.092)]
    rings=[]
    for j,(z,rx,ry) in enumerate(rows):
        ids=[]
        for i,(x,y) in enumerate(TORSO):
            w={'spine':1}
            if j==0:w={'pelvis':1}
            if j==1:w={'pelvis':.6,'spine':.4}
            if j in [2,3,4] and i in [2,3,4,7,8,9]:
                s=1 if x>0 else -1
                amount=[.04,.16,.27][j-2]
                w={'spine':1-amount,side_name('upper_arm',s):amount}
            ids.append(m.vertex((x*rx,y*ry,z),w))
        rings.append(ids)
    for j in range(len(rings)-1):
        for i in range(10):
            # Each shoulder opening occupies a 2x2 patch of the torso grid.
            if j in [2,3] and i in [2,3,7,8]:continue
            m.face([rings[j][i],rings[j][(i+1)%10],rings[j+1][(i+1)%10],rings[j+1][i]],'linen')
    for s,start in [(1,2),(-1,7)]:
        boundary=[rings[2][start],rings[2][start+1],rings[2][start+2],
                  rings[3][start+2],rings[4][start+2],rings[4][start+1],
                  rings[4][start],rings[3][start]]
        upper=side_name('upper_arm',s)
        a,e,_=REST[upper]
        path=[(lerp(a,e,.25),.100,.097,'linen'),
              (lerp(a,e,.50),.095,.092,'linen'),
              (lerp(a,e,.60),.094,.091,'linen'),
              (lerp(a,e,.61),.106,.102,'cuff'),   # the rolled-up fold
              (lerp(a,e,.80),.106,.102,'cuff'),
              (lerp(a,e,.81),.097,.094,'cuff')]
        direction=Vector(e)-Vector(a)
        first=section(path[0][0],direction,path[0][1],path[0][2])
        prev=match_boundary(m,boundary,first)
        for p,rx,ry,color in path:
            r=m.ring(section(p,direction,rx,ry),{upper:1})
            m.bridge(prev,r,color);prev=r
        inner=m.ring(section(path[-1][0],direction,.078,.076),{upper:1})
        m.bridge(prev,inner,'cuff')
    collar=m.ring([(x*.086,y*.074,1.125) for x,y in TORSO],{'spine':.6,'head':.4})
    m.bridge(rings[-1],collar,'cuff')
    o=m.finish();o['expected_components']=1;o['expected_boundary_loops']=4


def sash():
    # The one bold accent: a cloth sash knotted at the left hip with two tails.
    m=Mesh('Sash')
    loft(m,[(0,0,.652,.230,.165),(0,0,.738,.228,.163)],'sash',{'pelvis':1},TORSO)
    loft(m,[(-.20,-.105,.655,.045,.035),(-.205,-.112,.695,.05,.04),
            (-.20,-.105,.735,.042,.032)],'knot',{'pelvis':1},BOX)
    tube(m,[((-.21,-.12,.665),.030),((-.232,-.128,.59),.028),((-.25,-.13,.52),.022)],'sash',{'pelvis':1})
    tube(m,[((-.185,-.13,.665),.028),((-.19,-.145,.60),.025),((-.198,-.15,.545),.02)],'sash',{'pelvis':1})
    m.finish()


def trousers():
    # Cropped at mid-shin with a rolled cuff; the bottoms stay open so the
    # bare shin passes through instead of the tube being capped over it.
    m=Mesh('Trousers');tops={}
    outline=[(0,-.072,.545),(.06,-.118,.60),(.18,-.12,.615),(.215,-.06,.612),
             (.215,.062,.612),(.18,.128,.615),(.06,.122,.595),(0,.078,.545)]
    shared={}
    for s in [1,-1]:
        thigh=side_name('thigh',s);shin=side_name('shin',s)
        r=[]
        for i,(x,y,z) in enumerate(outline):
            if x==0 and i in shared:r.append(shared[i])
            else:
                w={'pelvis':1} if x==0 else {'pelvis':.8,thigh:.2}
                idx=m.vertex((s*x,y,z),w);r.append(idx)
                if x==0:shared[i]=idx
        tops[s]=r
        specs=[(.50,s*.118,0,.108,.108,{thigh:1},'pants'),
               (.40,s*.124,-.008,.095,.097,{thigh:.9,shin:.1},'pants'),
               (.35,s*.125,-.012,.091,.091,{thigh:.55,shin:.45},'pants'),
               (.31,s*.125,-.008,.087,.087,{thigh:.15,shin:.85},'pants'),
               (.26,s*.125,0,.084,.082,{shin:1},'pants'),
               (.259,s*.125,0,.096,.094,{shin:1},'pantcuff'),
               (.205,s*.125,0,.096,.094,{shin:1},'pantcuff'),
               (.204,s*.125,0,.074,.072,{shin:1},'pantcuff'),
               (.25,s*.125,0,.071,.069,{shin:1},'pants')]
        prev=r
        shape=[(-1,-.65),(-.65,-1),(.65,-1),(1,-.65),(1,.65),(.65,1),(-.65,1),(-1,.65)]
        for z,x,y,rx,ry,weights,color in specs:
            pts=[(x+s*u*rx,y+v*ry,z) for u,v in shape]
            r=m.ring(pts,weights);m.bridge(prev,r,color);prev=r
    perimeter=tops[1]+list(reversed(tops[-1][1:-1]))
    prev=perimeter
    for z,rx,ry in [(.66,.214,.146),(.70,.204,.138)]:
        pts=[]
        for idx in perimeter:
            x,y,_=m.v[idx]
            a=math.atan2(y/.125,x/.215)
            pts.append((rx*math.cos(a),ry*math.sin(a),z))
        r=m.ring(pts,{'pelvis':1});m.bridge(prev,r,'pants');prev=r
    m.close(prev,'pants')
    o=m.finish();o['expected_components']=1;o['expected_boundary_loops']=2


def arms():
    for s in [-1,1]:
        m=Mesh('Arm_Hand'+('.R' if s>0 else '.L'))
        upper=side_name('upper_arm',s);fore=side_name('forearm',s);hand=side_name('hand',s)
        a,e,_=REST[upper];w=REST[fore][1];end=REST[hand][1]
        direction=Vector(end)-Vector(a)
        rows=[(lerp(a,e,.45),.070,.068,{upper:1}),
              (lerp(a,e,.85),.069,.067,{upper:.8,fore:.2}),
              (Vector(e),.067,.065,{upper:.5,fore:.5}),
              (lerp(e,w,.20),.067,.064,{fore:1}),
              (lerp(e,w,.60),.062,.059,{fore:1}),
              (lerp(e,w,.95),.050,.048,{fore:.7,hand:.3}),
              (lerp(w,end,.15),.054,.048,{hand:1}),
              (lerp(w,end,.45),.074,.060,{hand:1}),
              (lerp(w,end,.80),.076,.062,{hand:1}),
              (lerp(w,end,1.06),.062,.050,{hand:1}),
              (lerp(w,end,1.17),.036,.030,{hand:1})]
        rings=[m.ring(section(p,direction,rx,ry),weights) for p,rx,ry,weights in rows]
        m.close(rings[0],'skin')
        # A chunky thumb grows from one palm quad, facing forward and inward.
        side=6 if s>0 else 5
        for j in range(len(rings)-1):
            for i in range(8):
                if j==7 and i==side:continue
                m.face([rings[j][i],rings[j][(i+1)%8],rings[j+1][(i+1)%8],rings[j+1][i]],'skin')
        root=[rings[7][side],rings[7][(side+1)%8],rings[8][(side+1)%8],rings[8][side]]
        center=sum((Vector(m.v[i]) for i in root),Vector())/4
        previous=root
        # Short and fat, tucked against the fist rather than a spike.
        for offset,scale in [(Vector((-s*.012,-.022,0)),.95),
                             (Vector((-s*.018,-.036,-.010)),.86),
                             (Vector((-s*.018,-.041,-.024)),.70)]:
            r=m.ring([center+offset+(Vector(m.v[i])-center)*scale for i in root],{hand:1})
            m.bridge(previous,r,'skin');previous=r
        m.close(previous,'skin');m.close(rings[-1],'skin')
        o=m.finish(skin=True);o['expected_components']=1;o['expected_boundary_loops']=0


def legs():
    # Bare shin and a broad bare foot in one loft, so the green tint shows
    # at the feet too; a leather sandal sole and instep strap underneath.
    for s in [-1,1]:
        foot=side_name('foot',s);shin=side_name('shin',s);x=s*.125
        def weights(p):
            t=clamp01((p[2]-.10)/.10);return {foot:1-t,shin:t}
        m=Mesh('Leg_Foot'+('.R' if s>0 else '.L'))
        loft(m,[(x,0,.248,.058,.058),(x,0,.23,.059,.058),(x,0,.15,.050,.050),
                (x,-.012,.115,.056,.072),(x,-.045,.075,.068,.120),
                (x,-.05,.036,.066,.125)],'skin',weights,BOX)
        o=m.finish(skin=True);o['expected_components']=1;o['expected_boundary_loops']=0
        m=Mesh('Sandal'+('.R' if s>0 else '.L'))
        loft(m,[(x,-.05,.0,.074,.134),(x,-.05,.031,.074,.134)],'sole',{foot:1},BOX)
        # Instep strap: follows the foot's taper 5 mm proud, above bare skin.
        # A closed band (outer and inner walls), never a cap through the foot.
        band=loft(m,[(x,-.0359,.086,.0697,.1118),(x,-.0211,.104,.0643,.0902),
                     (x,-.0211,.104,.0618,.0877),(x,-.0359,.086,.0672,.1093)],'strap',weights,BOX,caps=False)
        m.bridge(band[-1],band[0],'strap')
        m.finish()


def head():
    m=Mesh('Head_Neck')
    def weights(p):
        t=clamp01((p[2]-1.12)/.06);return {'head':t,'spine':1-t}
    loft(m,[(0,0,1.10,.072,.070),(0,0,1.16,.078,.075),
            (0,-.01,1.20,.150,.135),(0,-.012,1.25,.178,.160),
            (0,-.01,1.36,.192,.172),(0,0,1.47,.196,.176),
            (0,.005,1.57,.172,.158),(0,.005,1.63,.118,.110)],'skin',weights,TORSO)
    m.finish(skin=True)
    m=Mesh('Ears')
    for s in [-1,1]:
        loft(m,[(s*.195,.012,1.335,.020,.034),(s*.203,.014,1.385,.024,.040),
                (s*.195,.016,1.435,.018,.030)],'skin',{'head':1},BOX)
    m.finish(skin=True)
    m=Mesh('Nose')
    ids=m.ring([(-.028,-.176,1.42),(.028,-.176,1.42),(-.036,-.228,1.335),
                (.036,-.228,1.335),(-.043,-.176,1.318),(.043,-.176,1.318)],{'head':1})
    for f in [(0,1,3,2),(2,3,5,4),(0,2,4),(1,5,3),(0,4,5,1)]:m.face([ids[i] for i in f],'skin')
    m.finish(skin=True)
    m=Mesh('Hair')
    loft(m,[(0,.035,1.40,.200,.172),(0,.012,1.53,.197,.182),
            (0,.010,1.615,.156,.146),(0,.010,1.662,.098,.092)],'hair',{'head':1},TORSO)
    # Forelock: a fringe that tumbles forward over the headcloth.
    loft(m,[(.02,-.07,1.615,.090,.075),(.04,-.16,1.618,.060,.042),
            (.055,-.212,1.575,.016,.012)],'hair',{'head':1},BOX)
    m.finish()
    # Bold, simple face marks; the acting is in the body, not here.
    m=Mesh('Face_details')
    for s in [-1,1]:
        loft(m,[(s*.074,-.183,1.392,.021,.006),(s*.074,-.183,1.428,.021,.006)],'eye',{'head':1},BOX)
        loft(m,[(s*.078,-.181,1.448,.040,.008),(s*.080,-.181,1.468,.040,.008)],'hair',{'head':1},BOX)
    loft(m,[(0,-.177,1.268,.046,.006),(0,-.177,1.282,.048,.006)],'mouth',{'head':1},BOX)
    m.finish()
    m=Mesh('Headcloth')
    loft(m,[(0,.01,1.465,.212,.200),(0,.01,1.54,.210,.198)],'sash',{'head':1},TORSO)
    loft(m,[(.165,.155,1.47,.040,.036),(.172,.162,1.505,.046,.042),
            (.165,.155,1.54,.036,.032)],'knot',{'head':1},BOX)
    # Two tails flare out past the head: the villager's signature shape.
    tube(m,[((.19,.17,1.49),.032),((.26,.205,1.43),.030),((.30,.225,1.37),.022)],'sash',{'head':1})
    tube(m,[((.175,.19,1.475),.028),((.215,.235,1.39),.026),((.235,.255,1.31),.018)],'sash',{'head':1})
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
        if kind=='reach':u=(s*.30,-.90,.18);f=(s*.08,-1,.05)
        else:u=(s*.48,-.25,-.85);f=(s*.05,-1,-.08)
        e=aim(upper,REST[upper][0],u);w=aim(fore,e,f);aim(hand,w,f)
        thigh=side_name('thigh',s);shin=side_name('shin',s);foot=side_name('foot',s)
        if kind=='crouch':td=(s*.08,-.73,-.68);sd=(0,.65,-.76)
        elif kind=='stride':td=(0,-s*.48,-.88);sd=(0,s*.17,-.98)
        else:td=(s*.16,-.16,-.97);sd=(s*.02,.17,-.985)
        knee=aim(thigh,REST[thigh][0],td);ankle=aim(shin,knee,sd)
        aim(foot,ankle,(0,-.885,-.467))
    graph=bpy.context.evaluated_depsgraph_get()
    minimum=min((o.evaluated_get(graph).matrix_world@v.co).z
                for o in MODELS if o.name.startswith('Sandal') for v in o.evaluated_get(graph).data.vertices)
    RIG.location.z=-minimum+.01;bpy.context.view_layer.update()


def render(name,eye=(3,5,3),size=(1000,1100),wire=False,scale=2.0):
    cam.location=eye;cam.rotation_euler=(Vector((0,-.02,.86))-cam.location).to_track_quat('-Z','Y').to_euler()
    cd.ortho_scale=scale
    scene.render.resolution_x,scene.render.resolution_y=size
    temporary=[]
    if wire:
        for o in MODELS:
            ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
            ob=bpy.data.objects.new('Topology',bpy.data.meshes.new_from_object(ev))
            scene.collection.objects.link(ob);ob.matrix_world=o.matrix_world.copy()
            for c in ob.data.color_attributes['Col'].data:c.color=(.025,.025,.025,1)
            mod=ob.modifiers.new('Edges','WIREFRAME');mod.thickness=.0015;mod.offset=1;mod.use_replace=True
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
tunic();sash();trousers();arms();legs();head()
AUDIT['topology']={o.name:topology(o) for o in MODELS}
AUDIT['triangles']=sum(d['triangles'] for d in AUDIT['topology'].values())
scene=bpy.context.scene;setup_render(scene)
cd=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',cd);scene.collection.objects.link(cam)
scene.camera=cam;cd.type='ORTHO'
AUDIT['poses']={}
PAIRS=[('Tunic','Arm_Hand.L'),('Tunic','Arm_Hand.R'),
       ('Trousers','Leg_Foot.L'),('Trousers','Leg_Foot.R'),
       ('Sandal.L','Leg_Foot.L'),('Sandal.R','Leg_Foot.R')]
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
        render('side',(-5.8,-.4,1.4))
    if kind=='working':render('game-size',(3,5,3),(180,198),scale=2.2)
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
