"""Level 2 sawmill concept: the brick-footed saw shed.

Kevin, 2026-10-01: "show me a concept for the level 2 sawmill. keep in mind
that there should be 5 in total."

Level 2 is raised at fire II (hamlet) for 6 brick + 4 fine boards, works
1.5x faster and opens the fine boards recipe (2 boards -> 1 fine boards on an
iron saw blade). So the shed is the level 1 tarp camp rebuilt with what the
hamlet makes: brick, sawn boards and iron.

  - Same plot (7.56 x 5.85 m, ridge under 3.84 m) and the same markers as
    MillL1Import, so the building swaps in place; only Worker_Stand moves,
    behind the crank.
  - The canvas becomes a plank gable roof on four squared posts, each on a
    brick pier; the work floor is a brick plinth at the same 0.16 m height.
  - The bench becomes a saw table with an iron saw wheel (Kevin: "the
    cutting mechanism should be a saw wheel cutting the logs and he has a
    cranking lever to operate it"). He turns a crank wheel in front of him;
    a belt drives the saw's arbor pulley; the log is fed left to right by a
    rope and a hanging stone. Both wheels spin about their own origins.
  - A grindstone and a spare blade on the back wall: the saw blade wears.
  - Input cradle, log slots, output rack and plank slots are the level 1
    kit's own, unchanged; the upper plank slots show fine boards (paler,
    planed). The level 1 canvas survives as a lean-to over the output rack.

Builds in game metres (Blender Z up, front -Y), writes
sawmill-l2-concept/sawmill-l2-concept.fbx and the review renders. Concept
geometry, not a game kit: no state contract or importer yet.
"""
import math
import os
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/blender'))
import crew_v15_mill as M

OUT=ROOT/'sawmill-l2-concept'
RIG=ROOT/'crew-meshy-v15/anims/deckhand-v15-anims.fbx'
SKIN=(217,146,89)                  # the README's skin #D99259

PLOT=(7.56,5.85);RIDGE_LIMIT=3.84
PLATFORM=.16                       # Worker_Stand height, as at level 1
STAND=Vector((-.95,.62,PLATFORM))  # Worker_Stand: at the crank, looking along the table at the saw (level 1: -0.04, 0.66)

# Palette (sRGB), sampled from the level 1 mill's preview colours where they exist.
C=dict(
    wood=(140,88,31),wood_d=(129,81,28),wood_l=(161,100,46),hemp=(157,120,68),hide=(92,58,34),
    canvas=(189,158,110),stripe=(133,57,26),hem=(145,110,64),
    bark=(45,22,2),endgrain=(168,110,56),sign=(10,36,31),
    roof=(118,74,30),roof_d=(102,63,26),
    brick=(152,68,44),brick_d=(133,57,37),brick_l=(166,82,55),mortar=(170,152,124),
    iron=(58,60,64),steel=(150,156,162),stone=(122,119,110),stone_d=(98,96,90),
    fine=(214,170,104),fine_e=(232,196,140),brass=(196,152,58),water=(70,104,112),
)


def lin(c):
    c/=255;return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4


class Part:
    """One named mesh object, built from coloured primitives."""
    def __init__(self,name,parent=None,pivot=None):
        self.name=name;self.parent=parent;self.pivot=Vector(pivot or (0,0,0));self.bm=bmesh.new();self.cols=[]

    def _add(self,verts,faces,col):
        vs=[self.bm.verts.new(v) for v in verts]
        for f in faces:
            self.bm.faces.new([vs[i] for i in f]);self.cols.append(col)

    def box(self,c,s,col,rot=None):
        """Box centred at c, size s, optional rotation matrix about its centre."""
        c=Vector(c);h=Vector(s)/2;R=rot or Matrix.Identity(3)
        vs=[c+R@Vector((x*h.x,y*h.y,z*h.z)) for z in(-1,1) for y in(-1,1) for x in(-1,1)]
        self._add(vs,[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)],col)

    def beam(self,a,b,w,d,col,up=(0,0,1)):
        """Square beam from a to b, w across (horizontal), d deep."""
        a,b=Vector(a),Vector(b);ax=(b-a);L=ax.length;ax.normalize()
        u=Vector(up);
        if abs(ax.dot(u))>.95:u=Vector((0,1,0))
        x=u.cross(ax).normalized();z=ax.cross(x)
        R=Matrix((x,ax,z)).transposed()
        self.box((a+b)/2,(w,L,d),col,R)

    def cyl(self,a,b,r,col,n=8,cap=None,phase=None):
        """Faceted cylinder from a to b (flat shaded logs, posts, wheels)."""
        a,b=Vector(a),Vector(b);ax=(b-a).normalized()
        x=ax.orthogonal().normalized();y=ax.cross(x)
        ph=math.pi/n if phase is None else phase
        ring=lambda o:[o+(x*math.cos(ph+2*math.pi*i/n)+y*math.sin(ph+2*math.pi*i/n))*r for i in range(n)]
        vs=ring(a)+ring(b)
        self._add(vs,[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)],col)
        self._add(vs,[tuple(reversed(range(n))),tuple(range(n,2*n))],cap or col)

    def prism(self,pts,z0,z1,col):
        """Vertical prism over a polygon (x, y) list."""
        n=len(pts);vs=[Vector((x,y,z0)) for x,y in pts]+[Vector((x,y,z1)) for x,y in pts]
        self._add(vs,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)],col)

    def tri_board(self,pts,t,col):
        """A flat polygon given in 3D, thickened by t along its normal."""
        p=[Vector(v) for v in pts];nrm=(p[1]-p[0]).cross(p[2]-p[0]).normalized()*t/2
        n=len(p);vs=[v-nrm for v in p]+[v+nrm for v in p]
        self._add(vs,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)],col)

    def build(self,objs):
        me=bpy.data.meshes.new(self.name);self.bm.normal_update()
        bmesh.ops.recalc_face_normals(self.bm,faces=self.bm.faces[:])
        for v in self.bm.verts:v.co-=self.pivot
        self.bm.to_mesh(me);self.bm.free()
        col=me.color_attributes.new('Col','BYTE_COLOR','CORNER')
        for p,c in zip(me.polygons,self.cols):
            for li in p.loop_indices:col.data[li].color=(*[lin(v) for v in C[c]],1)
        me.color_attributes.active_color=col
        o=bpy.data.objects.new(self.name,me);bpy.context.scene.collection.objects.link(o)
        if self.parent:o.parent=objs[self.parent]
        bpy.context.view_layer.update();o.matrix_world=Matrix.Translation(self.pivot)   # built in world coordinates
        objs[self.name]=o;return o


def brick_courses(p,x0,x1,y0,y1,z0,z1,course=.075,brick=.23):
    """A brick block: mortar core, and on its four sides proud bricks in
    running bond, alternating tones."""
    p.box(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2),(x1-x0-.02,y1-y0-.02,z1-z0),'mortar')
    tones=('brick','brick_d','brick_l','brick','brick_d')
    k=0;z=z0
    while z+course<=z1+1e-6:
        zc=z+course/2;off=(brick/2) if int(round((z-z0)/course))%2 else 0
        for side in range(4):
            a0,a1=((x0,x1) if side<2 else (y0,y1))
            u=a0-off
            while u<a1-1e-6:
                lo,hi=max(u+.006,a0),min(u+brick-.006,a1)
                if hi-lo>.03:
                    m=(lo+hi)/2;L=hi-lo
                    if side==0:p.box((m,y0+.012,zc),(L,.024,course-.012),tones[k%5])
                    elif side==1:p.box((m,y1-.012,zc),(L,.024,course-.012),tones[k%5])
                    elif side==2:p.box((x0+.012,m,zc),(.024,L,course-.012),tones[k%5])
                    else:p.box((x1-.012,m,zc),(.024,L,course-.012),tones[k%5])
                    k+=1
                u+=brick
        z+=course


# ------------------------------------------------------------- the layout
POST_X=1.22;POST_YF=-1.45;POST_YB=1.75
PLATE_Z=2.45;RIDGE_Z=3.68         # ridge runs front to back: the open gable faces the camera
EAVE=.38;GABLE=.4
TABLE_Y=-.35;TABLE_Z=.78           # saw table: centre line of the cut, top (his hip, as the lowered level 1 bench)
BLADE=Vector((.15,TABLE_Y,.69));BLADE_R=.52    # the saw wheel: axle along Y just under the table top, clear of the floor, standing well above the log
BLADE_T=.02                                    # blade thickness
# The crank, from the Crank clip (crew_meshy_v15_anims.py), which found it by
# searching poses against the anatomy check. At his 1.30 m source scale, in his
# own frame (-Y forward): the handle circles CRANK['r'] about a point CRANK['ahead']
# in front of him and CRANK['up'] above his feet, both fists on it CRANK['grip']
# either side of his midline. He faces +X in the mill (the clip turns him 90
# degrees): the crank axle runs along Y, across him.
SRC=1.30/1.7
CRANK=dict(ahead=.44,up=.62,r=.07,grip=.22)
CRANK_C=STAND+Vector((CRANK['ahead'],0,CRANK['up']))/SRC     # the crank axle's centre in front of him
CRANK_R=CRANK['r']/SRC                                        # crank throw
HANDLE_HALF=(CRANK['grip']+.06)/SRC                           # half the handle: room for each fist
BEARING=HANDLE_HALF+.1                                        # bearing posts either side of him
FLY=Vector((CRANK_C.x,STAND.y+BEARING+.12,CRANK_C.z));FLY_R=.4   # the flywheel, on the crank axle on his left: behind him from the game camera
RATIO=5;PULLEY_R=FLY_R/RATIO                  # on the saw's arbor: one turn of the crank turns the saw 5 times
CLIP_SECONDS=1.2;FPS=30                       # one turn of the crank: the Crank clip's length
LOG_R=.15;LOG_Z=TABLE_Z+LOG_R
LOG_X0=-1.08                                  # the log's tail; it is fed +X into the wheel
SIGN_POST=(-1.98,.9)               # the level 1 sign's bracket hung off a canvas pillar; it gets its own post


def roof_z(x):
    return RIDGE_Z-(RIDGE_Z-PLATE_Z)*abs(x)/POST_X


def build_shed(objs):
    # brick plinth: the work floor, at level 1's platform height
    p=Part('Mill2_BrickPlinth','LumberMill_C_Level_2')
    x0,x1,y0,y1=-1.5,1.5,-1.72,2.02
    p.box((0,(y0+y1)/2,.07),(x1-x0,y1-y0,.14),'mortar')
    tones=('brick','brick_d','brick_l','brick_d','brick')
    k=0;row=0;y=y0+.01
    while y<y1-.06:
        off=.115 if row%2 else 0;x=x0+.01-off
        while x<x1-.01:
            lo,hi=max(x+.006,x0+.01),min(x+.23-.006,x1-.01)
            if hi-lo>.04:p.box(((lo+hi)/2,y+.0575,.15),(hi-lo,.103,.02),tones[k%5]);k+=1
            x+=.23
        y+=.115;row+=1
    for sx in(-1,1):p.box((sx*(x1-.04),(y0+y1)/2,.08),(.08,y1-y0,.16),'stone_d')
    for sy in(y0,y1):p.box((0,sy+(.04 if sy==y0 else -.04),.08),(x1-x0,.08,.16),'stone_d')
    p.box((0,y0-.22,.05),(.9,.4,.1),'stone')                  # the step at the front
    p.build(objs)

    # brick piers and squared posts with iron straps
    pi=Part('Mill2_Piers','LumberMill_C_Level_2');po=Part('Mill2_Frame','LumberMill_C_Level_2')
    for sx in(-1,1):
        for py in(POST_YF,POST_YB):
            x=sx*POST_X
            brick_courses(pi,x-.21,x+.21,py-.21,py+.21,PLATFORM,PLATFORM+.45)
            pi.box((x,py,PLATFORM+.47),(.46,.46,.04),'stone')
            po.box((x,py,(PLATFORM+.49+PLATE_Z)/2),(.22,.22,PLATE_Z-PLATFORM-.49),'wood')
            for z in(PLATFORM+.62,PLATE_Z-.2):po.box((x,py,z),(.235,.235,.05),'iron')
            po.beam((x,py,PLATE_Z-.7),(x,py+(.5 if py<0 else -.5),PLATE_Z-.04),.09,.09,'wood_d')   # knee braces
            po.beam((x,py,PLATE_Z-.7),(x-sx*.5,py,PLATE_Z-.04),.09,.09,'wood_d')
    for sx in(-1,1):                                           # side plates, front to back
        po.box((sx*POST_X,(POST_YF+POST_YB)/2,PLATE_Z+.06),(.24,POST_YB-POST_YF+.5,.16),'wood_d')
    for py in(POST_YF,POST_YB):                                # tie beam, king post, struts: the gable trusses
        po.box((0,py,PLATE_Z+.06),(2*POST_X+.36,.2,.16),'wood_d')
        po.box((0,py,(PLATE_Z+RIDGE_Z)/2+.02),(.16,.16,RIDGE_Z-PLATE_Z-.06),'wood')
        for sx in(-1,1):
            m=sx*POST_X*.55
            po.beam((0,py,PLATE_Z+.3),(m,py,roof_z(m)-.1),.1,.1,'wood_d')
    yF,yB=POST_YF-GABLE,POST_YB+GABLE
    po.box((0,(yF+yB)/2,RIDGE_Z-.06),(.16,yB-yF,.14),'wood_d')   # ridge beam
    for i in range(5):                                         # rafter pairs
        y=yF+.06+(yB-yF-.12)*i/4
        for sx in(-1,1):
            po.beam((sx*(POST_X+EAVE),y,roof_z(POST_X+EAVE)-.07),(0,y,RIDGE_Z-.07),.08,.1,'wood_d')
    po.build(objs);pi.build(objs)

    # board roof: long boards from ridge to eave, every other one lapped over its neighbours
    r=Part('Mill2_BoardRoof','LumberMill_C_Level_2')
    xe=POST_X+EAVE;n=18
    for sx in(-1,1):
        for j in range(n):
            ya=yF+(yB-yF)*j/n+.004;yb=yF+(yB-yF)*(j+1)/n-.004
            lap=.035 if j%2 else 0;w=.03 if j%2 else 0
            e=.04*((j*5)%3)                                        # ragged eave ends
            xa=sx*(xe+e-.04)
            r.tri_board([(0,ya-w,RIDGE_Z+.01+lap),(xa,ya-w,roof_z(xe+e-.04)+.01+lap),
                         (xa,yb+w,roof_z(xe+e-.04)+.01+lap),(0,yb+w,RIDGE_Z+.01+lap)],.035,
                        ('roof','roof_d','wood_d')[(j*2+(sx>0))%3] if j%2 else 'roof')
    for sx in(-1,1):                                           # ridge cap boards
        r.tri_board([(0,yF-.03,RIDGE_Z+.1),(sx*.2,yF-.03,roof_z(.2)+.1),(sx*.2,yB+.03,roof_z(.2)+.1),(0,yB+.03,RIDGE_Z+.1)],.04,'wood_d')
    for y in(yF-.02,yB+.02):                                   # barge boards
        for sx in(-1,1):
            r.beam((sx*(xe+.02),y,roof_z(xe)-.02),(0,y,RIDGE_Z+.1),.05,.16,'wood_d')
    r.build(objs)

    # back: half-height boards between the rear posts and boards in the rear gable
    w=Part('Mill2_BackWall','LumberMill_C_Level_2')
    for i in range(10):
        x=-POST_X+.11+(2*POST_X-.22)*(i+.5)/10
        w.box((x,POST_YB,PLATFORM+.49+.5),((2*POST_X-.22)/10-.012,.05,1.0),'wood' if i%2 else 'wood_l')
    w.box((0,POST_YB-.04,PLATFORM+1.5),(2*POST_X-.2,.08,.08),'wood_d')
    w.box((0,POST_YB-.05,PLATFORM+.62),(2*POST_X-.2,.06,.08),'wood_d')
    for i in range(12):
        xa=-POST_X+2*POST_X*i/12+.006;xb=-POST_X+2*POST_X*(i+1)/12-.006
        za=PLATE_Z+.14;zt=min(roof_z(xa),roof_z(xb))-.08
        if zt-za>.05:w.box(((xa+xb)/2,POST_YB+.08,(za+zt)/2),(xb-xa,.04,zt-za),'wood' if i%2 else 'wood_l')
    w.build(objs)

    # a post for the level 1 trade sign, on its own brick footing
    sp=Part('Mill2_SignPost','LumberMill_C_Level_2')
    x,y=SIGN_POST
    brick_courses(sp,x-.16,x+.16,y-.16,y+.16,0,.3)
    sp.box((x,y,.32),(.36,.36,.04),'stone')
    sp.box((x,y,1.67),(.16,.16,2.7),'wood')
    sp.prism([(x-.1,y-.1),(x+.1,y-.1),(x+.1,y+.1),(x-.1,y+.1)],3.02,3.06,'wood_d')
    for z in(.55,2.7):sp.box((x,y,z),(.175,.175,.04),'iron')
    sp.build(objs)


def half_log(p,sz,x0,x1,gap):
    """A sawn slab of the octagonal log along X: sz=1 the half toward +Y, -1 toward -Y."""
    a=LOG_R*math.cos(math.pi/8)
    prof=[(0,-a)]+[(LOG_R*math.cos(t),LOG_R*math.sin(t)) for t in(-3*math.pi/8,-math.pi/8,math.pi/8,3*math.pi/8)]+[(0,a)]
    prof=[(TABLE_Y+sz*(u+gap),LOG_Z+v) for u,v in prof]
    n=len(prof);vs=[Vector((x0,y,z)) for y,z in prof]+[Vector((x1,y,z)) for y,z in prof]
    p._add(vs,[(i,i+1,n+i+1,n+i) for i in range(n-1)],'bark')
    p._add(vs,[(n-1,0,n,2*n-1)],'endgrain')
    p._add(vs,[tuple(reversed(range(n))),tuple(range(n,2*n))],'endgrain')


def wheel(p,c,r,t,col,spokes=6,rim=.06,n=16,hub='iron'):
    """Spoked wheel in the XZ plane (axle along Y) centred at c, thickness t."""
    c=Vector(c)
    for i in range(n):                                       # rim segments
        a0,a1=2*math.pi*i/n,2*math.pi*(i+1)/n;rm=r-rim/2
        pa=c+Vector((math.cos(a0)*rm,0,math.sin(a0)*rm));pb=c+Vector((math.cos(a1)*rm,0,math.sin(a1)*rm))
        p.beam(pa,pb+(pb-pa).normalized()*.01,t,rim,col,up=(0,1,0))
    for i in range(spokes):
        a=2*math.pi*i/spokes+.3
        p.beam(c,c+Vector((math.cos(a),0,math.sin(a)))*(r-rim*.8),t*.6,.04,col,up=(0,1,0))
    p.cyl(c-Vector((0,t*.9,0)),c+Vector((0,t*.9,0)),.06,hub,n=8)


def build_station(objs):
    # saw table: logs come in from the input cradle on the left, boards leave toward the output rack
    t=Part('Mill2_SawTable','Bench_Anchor')
    x0,x1=-1.15,1.15;w=.62
    for side in(-1,1):                                       # top boards either side of the blade slot
        t.box((0,TABLE_Y+side*(w/4+.015),TABLE_Z-.03),(x1-x0,w/2-.03,.06),'wood_l')
    for side in(-1,1):t.box((0,TABLE_Y+side*(w/2-.05),TABLE_Z-.09),(x1-x0,.08,.06),'wood_d')   # side rails; open under the blade
    for x in(x0+.12,-.6,.8,x1-.12):                         # legs clear of the saw wheel
        for side in(-1,1):t.box((x,TABLE_Y+side*(w/2-.06),(PLATFORM+TABLE_Z-.09)/2),(.09,.09,TABLE_Z-.09-PLATFORM),'wood')
        t.box((x,TABLE_Y,.34),(.06,w-.1,.06),'wood_d')
    t.box((0,TABLE_Y-w/2+.06,.34),(x1-x0-.2,.06,.06),'wood_d')
    for x in(-.95,-.62):t.cyl((x,TABLE_Y-.2,TABLE_Z+.015),(x,TABLE_Y+.2,TABLE_Z+.015),.03,'wood_d',n=6)   # feed rollers
    t.box((0,TABLE_Y-.29,TABLE_Z+.05),(x1-x0-.1,.04,.1),'wood_d')                   # fence along the far edge
    # the saw's arbor: two bearing blocks under the table, the shaft back to the drive pulley
    for y in(TABLE_Y-.24,-.02):t.box((BLADE.x,y,BLADE.z),(.14,.1,.14),'iron')
    for y in(TABLE_Y-.24,-.02):t.box((BLADE.x,y,(PLATFORM+BLADE.z-.07)/2),(.1,.08,BLADE.z-.07-PLATFORM),'wood_d')
    # gravity feed: a rope from the push block over a sheave at the table end to a hanging stone
    t.box((LOG_X0-.06,TABLE_Y,LOG_Z),(.08,.3,.24),'wood_d')
    t.beam((LOG_X0-.06,TABLE_Y+.2,LOG_Z),(x1,TABLE_Y+.24,LOG_Z),.012,.012,'hemp')
    t.beam((LOG_X0-.06,TABLE_Y+.2,LOG_Z),(LOG_X0-.06,TABLE_Y+.15,LOG_Z),.012,.012,'hemp')
    t.cyl((x1+.02,TABLE_Y+.24,LOG_Z-.06),(x1+.02,TABLE_Y+.24,LOG_Z+.06),.06,'iron',n=8)
    t.box((x1,TABLE_Y+.24,LOG_Z-.04),(.12,.04,.12),'wood_d')
    t.beam((x1+.08,TABLE_Y+.24,LOG_Z),(x1+.08,TABLE_Y+.24,.52),.012,.012,'hemp')
    t.box((x1+.08,TABLE_Y+.24,.42),(.18,.18,.2),'stone')
    t.build(objs)

    # the saw's long arbor shaft back to the flywheel's plane, and its far bearing
    r=Part('Mill2_SawArbor','Bench_Anchor')
    r.cyl((BLADE.x,TABLE_Y-.3,BLADE.z),(BLADE.x,FLY.y+.05,BLADE.z),.025,'iron',n=6)
    r.box((BLADE.x,FLY.y-.12,BLADE.z),(.14,.1,.14),'iron')
    r.box((BLADE.x,FLY.y-.12,(PLATFORM+BLADE.z-.07)/2),(.1,.08,BLADE.z-.07-PLATFORM),'wood_d')
    r.build(objs)

    # the crank stand: two bearing posts either side of him, braced along the axle's line of pull
    f=Part('Mill2_CrankStand','Bench_Anchor')
    for y in(STAND.y-BEARING,STAND.y+BEARING):
        f.box((CRANK_C.x,y,(PLATFORM+CRANK_C.z)/2+.02),(.12,.12,CRANK_C.z-PLATFORM+.04),'wood')
        for sx in(-1,1):f.beam((CRANK_C.x,y,CRANK_C.z-.35),(CRANK_C.x+sx*.3,y,PLATFORM),.07,.07,'wood_d',up=(0,1,0))
        f.box((CRANK_C.x,y,PLATFORM+.03),(.7,.16,.06),'wood_d')
        f.box((CRANK_C.x,y,CRANK_C.z),(.16,.14,.14),'iron')                         # bearing
    f.build(objs)

    # the crank: a bent iron axle (the U between the bearings is the handle's throw)
    # and the flywheel on its end; all of it turns about the axle (object origin).
    # Built with the handle at the top of its turn.
    k=Part('Mill2_CrankWheel','Bench_Anchor',pivot=CRANK_C)
    x,z=CRANK_C.x,CRANK_C.z;y0,y1=STAND.y-HANDLE_HALF,STAND.y+HANDLE_HALF
    k.cyl((x,STAND.y-BEARING-.08,z),(x,y0,z),.03,'iron',n=6)
    k.cyl((x,y1,z),(x,FLY.y+.05,z),.03,'iron',n=6)
    for y in(y0,y1):k.box((x,y,z+CRANK_R/2),(.07,.035,CRANK_R+.07),'iron')        # the crank's cheeks
    k.cyl((x,y0,z+CRANK_R),(x,y1,z+CRANK_R),.022,'iron',n=6)
    k.cyl((x,y0+.03,z+CRANK_R),(x,y1-.03,z+CRANK_R),.032,'wood_d',n=8)              # wooden grip sleeve
    wheel(k,FLY,FLY_R,.07,'fine')
    k.build(objs)

    # the saw wheel: iron disc with teeth, the small drive pulley on the same arbor (object origin)
    b=Part('Saw2_Wheel','Bench_Anchor',pivot=BLADE)
    n=24
    ring=[BLADE+Vector((math.cos(2*math.pi*i/n),0,math.sin(2*math.pi*i/n)))*(BLADE_R-.03) for i in range(n)]
    teeth=[BLADE+Vector((math.cos(2*math.pi*(i+.15)/n),0,math.sin(2*math.pi*(i+.15)/n)))*BLADE_R for i in range(n)]
    pts=[];[pts.extend((ring[i],teeth[i])) for i in range(n)]
    b.tri_board([tuple(v) for v in pts],BLADE_T,'steel')
    b.cyl((BLADE.x,BLADE.y-.04,BLADE.z),(BLADE.x,BLADE.y+.04,BLADE.z),.08,'iron',n=8)   # hub and its collars
    py=FLY.y
    b.cyl((BLADE.x,py-.035,BLADE.z),(BLADE.x,py+.035,BLADE.z),PULLEY_R,'wood_d',n=10,cap='iron')
    b.build(objs)

    # the belt: open run from the crank wheel's rim to the arbor pulley
    e=Part('Mill2_Belt','Bench_Anchor')
    d=Vector((BLADE.x-FLY.x,0,BLADE.z-FLY.z));L=d.length;d.normalize()
    nrm=Vector((-d.z,0,d.x));sa=(FLY_R-PULLEY_R)/L;ca=math.sqrt(1-sa*sa)
    for sgn in(-1,1):
        u=(nrm*ca*sgn+d*sa).normalized()     # outer tangents
        u=Vector((u.x,0,u.z))
        e.beam(FLY+u*(FLY_R+.01),BLADE+Vector((0,py-BLADE.y,0))+u*(PULLEY_R+.01),.05,.012,'hide',up=(0,1,0))
    e.build(objs)

    # the log being fed into the wheel, and the two slabs that have passed it
    lg=Part('Bench2_Cutting','Bench_Anchor')
    lg.cyl((LOG_X0,TABLE_Y,LOG_Z),(BLADE.x-.03,TABLE_Y,LOG_Z),LOG_R,'bark',n=8,cap='endgrain')
    for sz in(-1,1):half_log(lg,sz,BLADE.x-.03,BLADE.x+.5,.006+(.02 if sz>0 else 0))
    lg.box(((LOG_X0+BLADE.x)/2,TABLE_Y,LOG_Z+LOG_R*.93),(-LOG_X0-.06,.01,.006),'fine_e')   # chalk line ahead of the cut
    lg.build(objs)

    # the grindstone: the saw blade wears and is ground true here
    g=Part('Mill2_Grindstone','LumberMill_C_Level_2')
    gx,gy=-1.08,1.42
    for sx in(-1,1):
        g.box((gx+sx*.17,gy,.45),(.06,.5,.06),'wood')
        for sy in(-1,1):g.beam((gx+sx*.17,gy+sy*.08,.48),(gx+sx*.2,gy+sy*.22,PLATFORM),.06,.06,'wood_d')
    g.cyl((gx-.08,gy,.72),(gx+.08,gy,.72),.27,'stone',n=12,cap='stone_d')
    g.cyl((gx-.25,gy,.72),(gx+.27,gy,.72),.025,'iron',n=6)
    g.box((gx+.29,gy,.62),(.03,.03,.22),'iron');g.cyl((gx+.29,gy,.52),(gx+.4,gy,.52),.02,'wood_d',n=6)
    g.box((gx,gy,.38),(.3,.42,.16),'wood_d');g.box((gx,gy,.455),(.25,.37,.01),'water')   # trough
    g.build(objs)

    # spare blade and the level 1 hand saw on the back wall
    h=Part('Mill2_ToolRail','LumberMill_C_Level_2')
    h.box((.25,POST_YB-.1,PLATFORM+1.2),(.62,.01,.06),'steel')
    for x in(-.06,.56):h.box((x,POST_YB-.1,PLATFORM+1.2),(.03,.02,.03),'iron')
    h.box((.48,POST_YB-.12,PLATFORM+1.05),(.42,.01,.12),'steel')
    h.box((.73,POST_YB-.12,PLATFORM+1.05),(.12,.03,.07),'wood_l')
    h.build(objs)


def build_dressing(objs):
    # the level 1 canvas lives on as a lean-to over the output rack
    c=Part('Mill2_OutputCanvas','LumberMill_C_Level_2')
    xa,xb=POST_X+.3,3.25;za,zb=roof_z(POST_X+.3)-.08,1.6;ya,yb=-1.45,.75
    c.tri_board([(xa,ya,za),(xb,ya-.05,zb),(xb,yb+.05,zb),(xa,yb,za)],.02,'canvas')
    c.tri_board([(xa+.0,ya-.002,za+.012),(xb,ya-.052,zb+.012),(xb,ya+.28,zb+.012),(xa,ya+.33,za+.012)],.02,'stripe')
    for y in(ya-.05,yb+.05):
        c.box((xb+.03,y,zb/2),(.07,.07,zb),'wood')
        c.box((xb+.03,y,zb+.04),(.1,.1,.08),'wood_d')
        c.beam((xb+.03,y,zb),(3.7,y+(-.15 if y<0 else .15),.03),.015,.015,'hemp')
        c.box((3.7,y+(-.15 if y<0 else .15),.04),(.1,.1,.12),'wood_d')
    c.box((xa,(ya+yb)/2,za+.03),(.07,yb-ya+.1,.07),'wood_d')
    c.build(objs)
    # level plate under the trade sign: two brass bars
    s=Part('Mill2_LevelPlate','LumberMill_C_Level_2')
    s.box((-2.55,.86,1.62),(.4,.04,.24),'sign')   # under the level 1 sign
    for x in(-2.61,-2.49):s.box((x,.835,1.62),(.05,.02,.16),'brass')
    s.beam((-2.7,.87,1.74),(-2.75,.87,1.82),.012,.012,'hemp');s.beam((-2.4,.87,1.74),(-2.35,.87,1.82),.012,.012,'hemp')
    s.build(objs)


def recolour(o,col):
    me=o.data;c=me.color_attributes['Col']
    for d in c.data:d.color=(*[lin(v) for v in C[col]],1)


def build(objs_l1):
    """Level 1 kit in, level 2 concept out. Returns {name: object}."""
    objs={}
    root=bpy.data.objects.new('LumberMill_C_Level_2',None);bpy.context.scene.collection.objects.link(root)
    objs['LumberMill_C_Level_2']=root
    # keep the level 1 kit's stock, racks, sign and markers; reparent to the new root
    keep=('Input_Container','Output_Container','Mill_InputCradle','Mill_OutputRack','Mill_TradeSign','Mill_TradeGlyph',
          'Bench_Anchor','Entrance_Anchor','Input_Pickup','Output_Dropoff','Worker_Approach','Worker_Stand')
    old_root=objs_l1['LumberMill_C_Level_1']
    for n,o in objs_l1.items():
        if o.parent==old_root and n in keep:
            mw=o.matrix_world.copy();o.parent=root;o.matrix_world=mw
    ws=objs_l1['Worker_Stand'];ws.matrix_world=Matrix.Translation(STAND)
    for n,o in objs_l1.items():
        if n in keep or n.startswith(('Input_Log_','Output_Plank_')):objs[n]=o
    for n in('Mill_Pillars','Mill_TriangularCanvas','Mill_CanvasHem','Mill_GroundTies','Mill_WorkPlatform','Mill_Workbench',
             'Bench_Loaded','Bench_Cutting','Bench_Finished','Bench_Result_01','Bench_Result_02','Bench_Result_03','Mallet_Tool'):
        o=objs_l1.get(n)
        if o and o.name in bpy.data.objects:bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.objects.remove(old_root,do_unlink=True)
    build_shed(objs);build_station(objs);build_dressing(objs)
    for i in range(7,13):recolour(objs[f'Output_Plank_{i:02d}'],'fine')   # upper courses: fine boards
    bpy.context.view_layer.update()
    return objs


def crank_angle(t):
    """The crank's turn about its axle (+Y, radians) at clip phase t, matched
    to the Crank clip's fists: at t=0 the handle is nearest him, halfway up,
    and he winds it down, away, up and back. The saw turns the same way
    (open belt) RATIO times as fast, so its top teeth run toward the log."""
    return -2*math.pi*t-math.pi/2


def animate_wheels(objs):
    """One loop of the work: the crank wheel turns once, the saw RATIO times.
    Object animation, take 'Mill2_Crank', CLIP_SECONDS long at FPS."""
    sc=bpy.context.scene;sc.render.fps=FPS;sc.render.fps_base=1
    n=round(CLIP_SECONDS*FPS);sc.frame_start,sc.frame_end=0,n
    for name,mult in(('Mill2_CrankWheel',1),('Saw2_Wheel',RATIO)):
        o=objs[name];o.rotation_mode='XYZ'
        o.animation_data_create();act=bpy.data.actions.new('Mill2_Crank_'+name);o.animation_data.action=act
        for f in(0,n):
            o.rotation_euler=(0,mult*crank_angle(f/n),0);o.keyframe_insert('rotation_euler',index=1,frame=f)
        for fc in(act.fcurves if hasattr(act,'fcurves') else [c for l in act.layers for st in l.strips for cb in st.channelbags for c in cb.fcurves]):
            for kp in fc.keyframe_points:kp.interpolation='LINEAR'
    sc.frame_set(0)


# ------------------------------------------------------------- the deckhand, for scale
def load_deckhand():
    before=set(bpy.data.objects);sc=bpy.context.scene;fps=(sc.render.fps,sc.render.fps_base)
    bpy.ops.import_scene.fbx(filepath=str(RIG))
    sc.render.fps,sc.render.fps_base=fps
    new=[o for o in bpy.data.objects if o not in before]
    arm=next(o for o in new if o.type=='ARMATURE')
    act=next((a for a in bpy.data.actions if a.name.endswith('Crew_Crank')),None) or next((a for a in bpy.data.actions if 'Idle' in a.name),None)
    if act:
        arm.animation_data_create();arm.animation_data.action=act
        if hasattr(arm.animation_data,'action_slot') and act.slots:arm.animation_data.action_slot=act.slots[0]
    sc.frame_set(0)
    top=[o for o in new if o.parent is None]
    holder=bpy.data.objects.new('Deckhand_ForScale',None);sc.collection.objects.link(holder)
    for o in top:o.parent=holder
    holder.scale=(1.7/1.30,)*3;holder.location=STAND
    skin=next(o for o in new if o.name.startswith('CREW_Skin'))   # exported white for the game's tint
    for d in skin.data.color_attributes['Col'].data:d.color=(*[lin(v) for v in SKIN],1)
    return holder,new


# ------------------------------------------------------------- checks and renders
def world_box(objs):
    lo=Vector((1e9,)*3);hi=-lo
    for o in objs:
        if o.type!='MESH' or o.hide_render:continue
        for v in o.data.vertices:
            w=o.matrix_world@v.co;lo=Vector(map(min,lo,w));hi=Vector(map(max,hi,w))
    return lo,hi


def setup_render():
    sc=bpy.context.scene
    sc.render.engine='BLENDER_WORKBENCH';sc.view_settings.view_transform='Standard'
    sh=sc.display.shading;sh.light='STUDIO';sh.color_type='VERTEX';sh.show_cavity=True;sh.cavity_type='WORLD'
    sh.show_shadows=True;sh.shadow_intensity=.35
    sc.render.film_transparent=True
    cd=bpy.data.cameras.new('c');cam=bpy.data.objects.new('c',cd);sc.collection.objects.link(cam);sc.camera=cam
    cd.type='ORTHO';return cam


def shoot(cam,path,az,el,scale,target=(0,0,1.6),res=(1400,1050)):
    sc=bpy.context.scene;sc.render.resolution_x,sc.render.resolution_y=res
    d=Vector((math.sin(math.radians(az))*math.cos(math.radians(el)),-math.cos(math.radians(az))*math.cos(math.radians(el)),
              math.sin(math.radians(el))))
    cam.location=Vector(target)+d*40;cam.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=scale;sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)


def main():
    OUT.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    l1=M.load('empty',logs=6,planks=12,fbx=M.FBX_GAME)
    l1['LumberMill_C_Level_1'].scale=(1,1,1);bpy.context.view_layer.update()
    objs=build(l1)
    lo,hi=world_box(objs.values())
    print('bounds',[round(x,2) for x in lo],[round(x,2) for x in hi])
    assert hi.z<=RIDGE_LIMIT+1e-3,hi.z
    assert -PLOT[0]/2<=lo.x and hi.x<=PLOT[0]/2 and -PLOT[1]/2<=lo.y and hi.y<=PLOT[1]/2,(lo,hi)
    tris=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objs.values() if o.type=='MESH')
    print('triangles',tris)
    animate_wheels(objs)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(OUT/'sawmill-l2-concept.fbx'),use_selection=False,object_types={'EMPTY','MESH'},
        axis_forward='-Z',axis_up='Y',use_triangles=False,mesh_smooth_type='FACE',colors_type='SRGB',
        add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0.)
    STILL=9                                        # the frame the stills show: handle at the bottom of its turn
    cam=setup_render()
    views=[('hero',-35,30,9.2),('front',0,22,9.2),('right',55,28,9.2),('rear',200,30,9.2),('top',0,89.9,8.6)]
    for n,az,el,s in views:shoot(cam,OUT/f'l2-{n}.png',az,el,s)
    for o in objs.values():
        if o.name.startswith('Mill2_BoardRoof'):o.hide_render=True
    shoot(cam,OUT/'l2-roof-off.png',-35,48,9.2)
    for o in objs.values():
        if o.name.startswith('Mill2_BoardRoof'):o.hide_render=False
    # with the deckhand at the worker stand, for scale and the work line
    holder,_=load_deckhand()
    bpy.context.scene.frame_set(STILL)
    shoot(cam,OUT/'l2-hero-crew.png',-35,30,9.2)
    roof=[o for o in objs.values() if o.name.startswith('Mill2_BoardRoof')]
    for o in roof:o.hide_render=True
    shoot(cam,OUT/'l2-work-closeup.png',-18,20,3.3,target=(-.4,.15,.8),res=(1200,1000))
    for o in roof:o.hide_render=False
    # the mechanism alone with him, the shed hidden: his side of the crank wheel
    shed=('Mill2_BoardRoof','Mill2_BackWall','Mill2_ToolRail','Mill2_Grindstone','Mill2_Frame','Mill2_Piers',
          'Mill2_OutputCanvas','Mill2_SignPost','Mill2_LevelPlate','Mill_Trade','Mill_InputCradle','Mill_OutputRack',
          'Input_Log','Output_Plank')
    for o in bpy.data.objects:
        if o.name.startswith(shed):o.hide_render=True
    shoot(cam,OUT/'l2-work-rear.png',235,26,3.0,target=(-.4,.4,.75),res=(1200,1000))
    shoot(cam,OUT/'l2-mechanism.png',-35,25,3.0,target=(-.35,.1,.75),res=(1200,1000))
    # level 1 (bench lowered for him, as the animations use it) from the same camera
    bpy.ops.wm.read_factory_settings(use_empty=True)
    l1=M.load('cutting',logs=6,planks=12)
    l1['LumberMill_C_Level_1'].scale=(1,1,1);bpy.context.view_layer.update()
    cam=setup_render();shoot(cam,OUT/'l1-hero.png',-35,30,9.2)
    print('tris',tris,'bounds ok')


if __name__=='__main__':
    main()
