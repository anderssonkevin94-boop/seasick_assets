"""Level 2 wall concept: a stone base under squared timbers, stone pillars.

Kevin, 2026-10-01: "a lvl 2 wall? im thinking half wood (sturdier wood) and
half stone blocks towards the base and for the pillars".

Built to the level 1 palisade kit's contract (art-staging/palisade-astra-
lvl1-v2), so the wall adapter can swap it in: metres, Blender +X along the
wall, +Y the rear, +Z up; every run's root at its START end on the ground,
`<Part>__Snap_Start` (0,0,0) and `__Snap_End` (length,0,0); timbers on the
same 0.25 m pitch (centres 0.125 + i*0.25); the pillar's root at its start
edge with `__Post_Center` marking where it stands on a bend.

  - Base: dry-laid stone blocks, 1.15 m, in five courses with a capstone
    course. Courses alternate between joints AT the module ends and joints a
    quarter metre in, so runs tile with no seam every metre.
  - Upper half: squared timbers (0.23 x 0.17, three times the level 1 stakes'
    bulk), adzed points, on an oak sill, two iron bands across the front,
    two rails and pegs at the rear. Tops at 2.45-2.65 m.
  - Pillar: stone all the way up, 0.56 m square, quoined courses, a wider
    capstone and a pointed cap: 3.05 m.

Writes wall-l2-concept/ (module FBX, renders).
"""
import math
import sys
from pathlib import Path
import random
import bpy
import bmesh
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/blender'))
import sawmill_l2_concept as S          # the shared Part builder, palette and render helpers
from sawmill_l2_concept import Part, C

OUT=ROOT/'wall-l2-concept'
L1=Path('/tmp/claude-0/sc/wall')         # level 1 palisade FBX copies, for the comparison render (see fetch_l1)
L1_URL='https://media.githubusercontent.com/media/anderssonkevin94-boop/seasick/ships-into-unity/art-staging/palisade-astra-lvl1-v2/'

# Light and few: three pale stone tones over darker mortar (the joints carry the
# read), light oak, dark iron for contrast.
C.update(st1=(214,207,190),st2=(199,191,173),st3=(226,220,205),mortar_d=(112,105,93),
         oak=(200,144,86),oak_d=(170,118,66),oak_l=(216,162,102),oak_tip=(232,192,134))

BASE_H=1.15;BASE_T=.40                  # stone base height, thickness (Y -0.2..0.2)
CAP=.19;COURSE=(BASE_H-CAP)/3           # three chunky courses and a capstone course
SILL=(.32,.10)                          # oak sill on the base: depth, height
TIMBER=(.23,.17)                        # width along the wall, depth
PITCH=.25
POST_W=.56;POST_H=3.05


JOINT=.045                              # mortar joint between stones: wide, so each stone reads at game zoom


def stone(p,c,size,tone,axis=None,flush=()):
    """One crude, hand-dressed block: every corner knocked off by its own
    uneven chamfer, the faces a little out of true, and the whole stone
    standing a little proud or shy of its neighbours. Seeded by position, so
    the same stone comes out the same every build. flush: sides ('-x', '+x')
    left square, where two runs' end stones meet as one stone."""
    c=Vector(c);h=Vector(size)/2
    rnd=random.Random(f'{c.x:.3f},{c.y:.3f},{c.z:.3f},{tone}')   # str seeds are stable across runs (unlike hash())
    depth=rnd.uniform(-.012,.012)                  # proud or shy of the wall face
    pts=[]
    for sx in(-1,1):
        for sy in(-1,1):
            for sz in(-1,1):
                corner=Vector((sx*h.x,sy*h.y,sz*h.z))
                if (sx<0 and '-x' in flush) or (sx>0 and '+x' in flush):
                    b=[0,rnd.uniform(.02,.05),rnd.uniform(.02,.05)]     # square to the seam
                else:b=[rnd.uniform(.025,.07) for _ in range(3)]
                b=[min(v,h[i]*.45) for i,v in enumerate(b)]
                for i in range(3):                # three points per corner: the chamfer
                    q=corner.copy();q[i]-=(1 if q[i]>0 else -1)*b[i]
                    for j in range(3):            # faces a little out of true
                        if j!=i and not ((j==0) and ((sx<0 and '-x' in flush) or (sx>0 and '+x' in flush))):
                            q[j]+=rnd.uniform(-.008,.008)
                    pts.append(q)
    off=Vector((0,0,0))
    if axis is not None:off[axis]=depth
    bm=bmesh.new();vs=[bm.verts.new(c+off+q) for q in pts]
    bmesh.ops.convex_hull(bm,input=vs)
    bmesh.ops.dissolve_limit(bm,angle_limit=math.radians(2),verts=bm.verts[:],edges=bm.edges[:])
    for f in bm.faces:p._add([v.co.copy() for v in f.verts],[tuple(range(len(f.verts)))],tone)
    bm.free()


def stone_course(p,x0,x1,z0,h,joints,seed,y0=-BASE_T/2,y1=BASE_T/2,flush=False):
    """One course of blocks from x0 to x1 with vertical joints at `joints`
    (sorted, inside x0..x1), over a mortar core, through the wall's thickness.
    flush: the end stones run right to the module ends with no joint there, so
    they meet the neighbouring run's end stones as one stone."""
    tones=('st1','st2','st3')
    edges=[x0]+list(joints)+[x1];last=len(edges)-2
    for i,(a,b) in enumerate(zip(edges,edges[1:])):
        a2=a if (flush and i==0) else a+JOINT/2;b2=b if (flush and i==last) else b-JOINT/2
        tone=tones[seed%3] if flush and i in(0,last) else tones[(seed+i*2)%3]   # both halves of the shared stone match
        fl=tuple(k for k,on in(('-x',flush and i==0),('+x',flush and i==last)) if on)
        stone(p,((a2+b2)/2,(y0+y1)/2,z0+h/2),(b2-a2,y1-y0+.02,h-JOINT),tone,1,fl)


# Course joints per run length. Course 0 and 2 and the capstones joint AT the
# module ends; course 1's end stones run flush to the ends and pair with the
# neighbour's into one stone (a quarter metre in from each end).
JOINTS={1.:{'A':[(.45,),(.25,.75),(.55,),(.5,)],'B':[(.6,),(.25,.75),(.4,),(.45,)],'C':[(.5,),(.25,.75),(.35,),(.6,)]},
        .5:{'A':[(),(.25,),(),()]},
        .25:{'A':[(),(),(),()]}}
TOPS={'A':(2.58,2.5,2.64,2.53),'B':(2.5,2.62,2.55,2.47),'C':(2.6,2.52,2.48,2.63)}


def base(p,L,inner,variant,keep=None):
    """The stone base of a run of length L. keep(k, a, b) -> False drops a
    stone (course k, from a to b): the breached run's knocked-out stones."""
    p.box((L/2,0,BASE_H/2 if keep is None else COURSE),(L,BASE_T-.03,BASE_H if keep is None else 2*COURSE),'mortar_d')
    for k in range(3):
        z=k*COURSE;edges=[0.]+list(inner[k])+[L]
        if keep is None:
            stone_course(p,0,L,z,COURSE,inner[k],k+ord(variant) if k!=1 else 1,flush=k==1);continue
        tones=('st1','st2','st3');last=len(edges)-2
        for i,(a,b) in enumerate(zip(edges,edges[1:])):
            if not keep(k,a,b):continue
            fl=k==1;a2=a if (fl and i==0) else a+JOINT/2;b2=b if (fl and i==last) else b-JOINT/2
            f=tuple(n for n,on in(('-x',fl and i==0),('+x',fl and i==last)) if on)
            stone(p,((a2+b2)/2,0,z+COURSE/2),(b2-a2,BASE_T+.02,COURSE-JOINT),tones[(k+i*2)%3] if not fl or i not in(0,last) else tones[1],1,f)
    zc=3*COURSE
    for i,(a,b) in enumerate(zip((0.,)+tuple(inner[3]),tuple(inner[3])+(L,))):
        if keep is None or keep(3,a,b):
            stone(p,((a+b)/2,0,zc+CAP/2),(b-a-JOINT,BASE_T+.1,CAP-.03),('st3','st1')[i%2],2)


def pointed(p,x,z0,top,tone,tip=.22):
    w,d=TIMBER;hw,hd=w/2,d/2
    p.box((x,0,(z0+top)/2),(w,d,top-z0),tone)
    p._add([Vector((x-hw,-hd,top)),Vector((x+hw,-hd,top)),Vector((x+hw,hd,top)),Vector((x-hw,hd,top)),Vector((x,0,top+tip))],
           [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)],'oak_tip')


def run(name,variant='A',length=1.):
    """A run of length 1, 0.5 or 0.25 m: stone base, sill, timbers on the
    0.25 m pitch, iron bands at the front, rails and pegs at the rear."""
    p=Part(name);L=length;n=round(L/PITCH)
    base(p,L,JOINTS[L][variant],variant)
    zs=BASE_H;p.box((L/2,0,zs+SILL[1]/2),(L,SILL[0],SILL[1]),'oak_d')
    z0=zs+SILL[1]
    for i in range(n):
        pointed(p,.125+i*PITCH,z0,TOPS[variant][i],('oak','oak_l','oak','oak_l')[(i+ord(variant))%4])
    for zb in(1.62,2.22):                                        # iron bands, riveted to every timber
        p.box((L/2,-TIMBER[1]/2-.008,zb),(L,.016,.07),'iron')
        for i in range(n):p.box((.125+i*PITCH,-TIMBER[1]/2-.02,zb),(.035,.012,.035),'iron')
    for zr in(1.5,2.25):                                         # rear rails and pegs
        p.box((L/2,TIMBER[1]/2+.05,zr),(L,.1,.12),'oak_d')
        for i in range(n):p.box((.125+i*PITCH,TIMBER[1]/2+.105,zr),(.04,.02,.04),'oak_l')
    return p


def splintered(p,x,z0,top,tone,seed,lean=0.):
    """A timber snapped at `top`: jagged corners and a torn, off-centre spike.
    lean: degrees it has been knocked over toward -Y (front), about its foot."""
    rnd=random.Random(f'splinter{seed}');w,d=TIMBER;hw,hd=w/2,d/2
    R=Matrix.Rotation(math.radians(-lean),3,'X');foot=Vector((x,0,z0))
    P=lambda q:foot+R@(Vector(q)-foot)
    corners=[(x-hw,-hd),(x+hw,-hd),(x+hw,hd),(x-hw,hd)]
    hs=[top-rnd.uniform(0,.16) for _ in corners]
    vs=[P((cx,cy,z0)) for cx,cy in corners]+[P((cx,cy,h)) for (cx,cy),h in zip(corners,hs)]
    spike=P((x+rnd.uniform(-.06,.06),rnd.uniform(-.04,.04),top+rnd.uniform(.08,.2)))
    p._add(vs+[spike],[(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,8),(5,6,8),(6,7,8),(7,4,8)],tone)
    # the splintered face, lighter: a few raw slivers
    for k in range(3):
        cx=x+rnd.uniform(-hw*.6,hw*.6);h=max(hs)+rnd.uniform(.02,.12)
        a,b,c=P((cx-.025,-hd*.5,min(hs)-.02)),P((cx+.025,hd*.5,min(hs)-.02)),P((cx+rnd.uniform(-.02,.02),0,h))
        p._add([a,b,c],[(0,1,2)],'oak_tip')


def breached_run(name):
    """1 m, the middle smashed: the ends still meet whole runs (bottom course
    whole, end stones in place, timber stumps at the ends tallest), the
    middle stones knocked out and lying in front, timbers snapped short or
    leaning, bands and rails torn off. Same start-end root and snaps."""
    p=Part(name);inner=JOINTS[1.]['A']
    def keep(k,a,b):
        mid=(a+b)/2
        if k==0:return True                                  # the footing course stands
        if k==1:return a<.01 or b>.99                        # only its end stones (they pair with the neighbours)
        if k==2:return b<.3 or a>.7                          # stubs at the ends
        return b<.3 or a>.7                                  # capstones only over the stubs
    base(p,1.,inner,'A',keep)
    # what was the second and top course: a ragged step over the gap
    zs=BASE_H;z0=zs+SILL[1]
    for x0,x1 in((0,.24),(.76,1)):p.box(((x0+x1)/2,0,zs+SILL[1]/2),(x1-x0,SILL[0],SILL[1]),'oak_d')   # sill ends
    # timbers: the outer two snapped high, the inner two low; one knocked over
    splintered(p,.125,z0,1.95,'oak',1)
    zb=2*COURSE                                              # the top of what stands of the stone
    splintered(p,.375,zb+.02,zb+1.25,'oak_l',2,lean=34)                   # knocked over forward, still on its foot
    splintered(p,.625,zb,zb+.55,'oak',3)                                  # snapped low
    splintered(p,.875,z0,1.75,'oak_l',4)
    # torn band ends and rail ends, bent
    for zb,(x0,x1) in((1.62,(0,.2)),(1.62,(.8,1)),(2.22,(0,.17))):
        p.box(((x0+x1)/2,-TIMBER[1]/2-.008,zb),(x1-x0,.016,.07),'iron')
    p.beam((.2,-TIMBER[1]/2-.008,1.62),(.3,-.2,1.5),.016,.07,'iron')         # a band end bent out
    for zr,(x0,x1) in((1.5,(0,.22)),(1.5,(.82,1)),(2.25,(0,.12))):
        p.box(((x0+x1)/2,TIMBER[1]/2+.05,zr),(x1-x0,.1,.12),'oak_d')
    # the knocked-out stones on the ground, front and back
    for i,(x,y,sx,sy,sz,t) in enumerate(((.45,-.42,.42,.3,.22,'st1'),(.7,-.55,.3,.26,.18,'st3'),(.25,-.62,.24,.2,.15,'st2'),
                                         (.55,.38,.36,.28,.2,'st2'),(.9,-.4,.22,.2,.14,'st1'))):
        stone(p,(x,y,sz/2-.01),(sx,sy,sz),t,2)
    stone(p,(.5,-.1,2*COURSE+.08),(.36,.3,.16),'st3',2)                     # one cap stone slumped into the gap
    return p


def post(name,height=POST_H,n=6,cap=True):
    """Stone pillar: n chunky courses, the corner stones alternating which
    face runs long, a wider capstone and (cap) a pointed cap. Root at the
    start edge, centre at x=POST_W/2."""
    p=Part(name);c=POST_W/2;h=height-.45;ch=h/n;W=POST_W;t=.17
    p.box((c,0,h/2),(W-.06,W-.06,h),'mortar_d')
    tones=('st1','st2','st3')
    for k in range(n):
        z=k*ch+ch/2;tn=lambda j:tones[(k+j)%3];hh=ch-JOINT
        if k%2:   # long stones on the front and back faces, short on the sides
            for j,sy in enumerate((-1,1)):stone(p,(c,sy*(W/2-t/2),z),(W,t,hh),tn(j),1)
            for j,sx in enumerate((-1,1)):stone(p,(c+sx*(W/2-t/2),0,z),(t,W-2*t-JOINT,hh),tn(j+2),0)
        else:
            for j,sx in enumerate((-1,1)):stone(p,(c+sx*(W/2-t/2),0,z),(t,W,hh),tn(j),0)
            for j,sy in enumerate((-1,1)):stone(p,(c,sy*(W/2-t/2),z),(W-2*t-JOINT,t,hh),tn(j+2),1)
    stone(p,(c,0,h+.08),(W+.12,W+.12,.16),'st3',1)                    # capstone
    if not cap:return p
    a=W/2-.02;top=height
    p._add([Vector((c-a,-a,h+.2)),Vector((c+a,-a,h+.2)),Vector((c+a,a,h+.2)),Vector((c-a,a,h+.2)),Vector((c,0,top))],
           [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)],'st2')
    return p


def module(objs,part,length=None,center=None):
    o=part.build(objs);root=bpy.data.objects.new(part.name+'_Root',None);bpy.context.scene.collection.objects.link(root)
    o.parent=root
    for mk,at in((('Snap_Start',(0,0,0)),('Snap_End',(length,0,0))) if length else (('Post_Center',center),)):
        e=bpy.data.objects.new(f'{part.name}__{mk}',None);e.empty_display_size=.1;bpy.context.scene.collection.objects.link(e)
        e.parent=root;e.location=at
    return root


def place(root,at,yaw):
    root.matrix_world=Matrix.Translation(at)@Matrix.Rotation(math.radians(yaw),4,'Z')


def fetch_l1():
    import urllib.request
    L1.mkdir(parents=True,exist_ok=True)
    for f in('Palisade_Run_1m_A.fbx','Palisade_Run_1m_B.fbx','Palisade_Run_1m_C.fbx','Palisade_Post.fbx'):
        if not (L1/f).exists():urllib.request.urlretrieve(L1_URL+f,L1/f)


def import_l1(f):
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(L1/f))
    new=[o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.type=='MESH':
            col=o.data.color_attributes.get('Col') or (o.data.color_attributes[0] if o.data.color_attributes else None)
            if col:
                o.data.color_attributes.active_color=col
                # the kit's colours come back one gamma step dark through this importer
                # (its own kit-overview.png shows them lighter): lift them once
                for d in col.data:
                    c=d.color;d.color=(*[(1.055*v**(1/2.4)-.055) if v>.0031308 else v*12.92 for v in c[:3]],1)
    return [o for o in new if o.parent is None]


def wall_line(make_run,make_post,start,legs):
    """A wall along a polyline: legs = [(yaw degrees, whole metres)], as the
    adapter would tile them. One pillar per node, never two: an end node
    faces its leg, a bend node is turned to the bisector of the two legs
    that meet there (a square pillar looks right from both)."""
    nodes=[Vector(start)];dirs=[]
    for yaw,L in legs:
        d=Vector((math.cos(math.radians(yaw)),math.sin(math.radians(yaw)),0))
        for i in range(L):make_run(nodes[-1]+d*i,yaw,i)
        nodes.append(nodes[-1]+d*L);dirs.append(yaw)
    for k,at in enumerate(nodes):
        inc=dirs[max(0,k-1):k+1]                     # the legs meeting at this node
        make_post(at,sum(inc)/len(inc))
    return nodes[-1]


def main():
    OUT.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs={}
    roots=[module(objs,run(f'Wall2_Run_1m_{v}',v),length=1) for v in 'ABC']
    roots+=[module(objs,run('Wall2_Filler_050m','A',.5),length=.5),module(objs,run('Wall2_Filler_025m','A',.25),length=.25),
            module(objs,breached_run('Wall2_Breached_1m'),length=1)]
    roots.append(module(objs,post('Wall2_Post'),center=(POST_W/2,0,0)))
    x=0.
    for r,L in zip(roots,(1,1,1,.5,.25,1,POST_W)):r.location=(x,0,0);x+=L+.6
    tris={o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in objs.values()}
    print('triangles',tris)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(OUT/'wall-l2-kit.fbx'),use_selection=False,object_types={'EMPTY','MESH'},
        axis_forward='-Z',axis_up='Y',use_triangles=False,mesh_smooth_type='FACE',colors_type='SRGB',add_leaf_bones=False,bake_anim=False)
    cam=S.setup_render();sc=bpy.context.scene
    S.shoot(cam,OUT/'wall-l2-kit.png',-30,22,9.0,target=(4.1,0,1.4),res=(1700,1000))

    # A stretch of wall with a bend, and level 1 beside it from the same camera
    bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene
    objs={};kit={v:run(f'Wall2_Run_1m_{v}',v).build(objs) for v in 'ABC'}
    pk=post('Wall2_Post').build(objs)
    for o in list(kit.values())+[pk]:o.hide_render=True
    def mk_run(at,yaw,i):
        o=bpy.data.objects.new('run',kit['ABC'[(i*2+int(at.x*3))%3]].data);sc.collection.objects.link(o);place(o,at,yaw)
    def mk_post(at,yaw):
        o=bpy.data.objects.new('post',pk.data);sc.collection.objects.link(o)
        place(o,at,yaw);o.location-=Matrix.Rotation(math.radians(yaw),3,'Z')@Vector((POST_W/2,0,0))
    wall_line(mk_run,mk_post,(0,0,0),[(0,3),(0,3),(40,3)])
    ground=Part('ground');ground.box((3.5,1.5,-.03),(16,10,.06),'mortar_d');g=ground.build(objs)
    g.data.color_attributes['Col'].data.foreach_set('color',[v for _ in range(len(g.data.loops)) for v in (*[S.lin(c) for c in (104,128,78)],1)])
    # the deckhand for scale, outside the wall
    holder,_=S.load_deckhand();holder.location=(2.1,-1.1,0)
    act=next((a for a in bpy.data.actions if a.name.endswith('Crew_Idle')),None)
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE');arm.animation_data.action=act;sc.frame_set(0)
    cam=S.setup_render()
    S.shoot(cam,OUT/'wall-l2-hero.png',-28,24,9.5,target=(4.3,1.0,1.2),res=(1600,1000))
    S.shoot(cam,OUT/'wall-l2-front.png',0,8,6.5,target=(3,0,1.4),res=(1500,900))
    S.shoot(cam,OUT/'wall-l2-rear.png',165,24,9.5,target=(4.3,1.0,1.2),res=(1600,1000))
    S.shoot(cam,OUT/'wall-l2-closeup.png',-38,16,3.3,target=(3.1,0,1.5),res=(1200,1100))
    S.shoot(cam,OUT/'wall-l2-bend.png',-25,30,3.6,target=(6.1,.2,1.6),res=(1000,1100))      # the 40-degree bend: one pillar
    S.shoot(cam,OUT/'wall-l2-bend-rear.png',150,30,3.6,target=(6.1,.2,1.6),res=(1000,1100))
    S.shoot(cam,OUT/'wall-l2-bend-top.png',0,89.9,2.4,target=(6.0,0,1.0),res=(1000,1000))

    # level 1 and level 2 side by side, same camera and scale
    fetch_l1()
    off=Vector((-4.6,0,0))                       # level 1 on the same line, to the left
    for i in range(3):
        for r in import_l1(f'Palisade_Run_1m_{"ABC"[i]}.fbx'):r.location=off+Vector((i,0,0))
    for x in(0,3):
        for r in import_l1('Palisade_Post.fbx'):r.location=off+Vector((x-.2,0,0))
    holder.location=(-.6,-1.0,0)
    S.shoot(cam,OUT/'wall-l1-vs-l2.png',-18,16,10.4,target=(-.1,0,1.4),res=(1800,900))

    # the pieces in use: a 4.75 m stretch tiled from runs and both fillers, breached once
    bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene;objs={}
    parts={'A':run('_A','A').build(objs),'B':run('_B','B').build(objs),'C':run('_C','C').build(objs),
           'F5':run('_F5','A',.5).build(objs),'F25':run('_F25','A',.25).build(objs),'X':breached_run('_X').build(objs)}
    pk=post('_P').build(objs)
    for o in list(parts.values())+[pk]:o.hide_render=True
    x=0.
    for k,L in(('A',1),('X',1),('B',1),('F5',.5),('F25',.25),('C',1)):
        o=bpy.data.objects.new(k,parts[k].data);sc.collection.objects.link(o);o.location=(x,0,0);x+=L
    for px in(0.,x):
        o=bpy.data.objects.new('post',pk.data);sc.collection.objects.link(o);o.location=(px-POST_W/2,0,0)
    ground=Part('ground');ground.box((2.4,0,-.03),(12,8,.06),'mortar_d');g=ground.build(objs)
    g.data.color_attributes['Col'].data.foreach_set('color',[v for _ in range(len(g.data.loops)) for v in (*[S.lin(c) for c in (104,128,78)],1)])
    holder,_=S.load_deckhand();holder.location=(2.6,-1.2,0)
    act=next((a for a in bpy.data.actions if a.name.endswith('Crew_Idle')),None)
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE');arm.animation_data.action=act;sc.frame_set(0)
    cam=S.setup_render()
    S.shoot(cam,OUT/'wall-l2-pieces.png',-22,20,6.4,target=(2.4,0,1.3),res=(1700,1000))
    S.shoot(cam,OUT/'wall-l2-breach.png',-30,22,2.8,target=(1.5,-.2,1.0),res=(1100,1000))
    S.shoot(cam,OUT/'wall-l2-breach-rear.png',150,24,2.8,target=(1.5,.1,1.0),res=(1100,1000))
    print('done')


if __name__=='__main__':
    main()
