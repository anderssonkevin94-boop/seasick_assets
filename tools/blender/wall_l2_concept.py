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
import bpy
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/blender'))
import sawmill_l2_concept as S          # the shared Part builder, palette and render helpers
from sawmill_l2_concept import Part, C

OUT=ROOT/'wall-l2-concept'
L1=Path('/tmp/claude-0/sc/wall')         # level 1 palisade FBX copies, for the comparison render (see fetch_l1)
L1_URL='https://media.githubusercontent.com/media/anderssonkevin94-boop/seasick/ships-into-unity/art-staging/palisade-astra-lvl1-v2/'

C.update(stone_l=(146,141,128),stone_m=(112,108,99),stone_dd=(84,82,77),mortar_d=(78,74,66),
         oak=(112,70,34),oak_d=(92,56,27),oak_l=(132,84,42))

BASE_H=1.15;BASE_T=.40                  # stone base height, thickness (Y -0.2..0.2)
COURSE=BASE_H/5
SILL=(.32,.10)                          # oak sill on the base: depth, height
TIMBER=(.23,.17)                        # width along the wall, depth
PITCH=.25
POST_W=.56;POST_H=3.05


def stone_course(p,x0,x1,z0,h,joints,seed,y0=-BASE_T/2,y1=BASE_T/2):
    """One course of blocks from x0 to x1 with vertical joints at `joints`
    (sorted, inside x0..x1), proud of a mortar core on both faces and the top."""
    tones=('stone','stone_m','stone_l','stone','stone_m','stone_dd')
    edges=[x0]+list(joints)+[x1]
    for i,(a,b) in enumerate(zip(edges,edges[1:])):
        t=tones[(seed*7+i*5)%len(tones)];inset=.012
        bulge=.006*((seed+i)%3)
        p.box(((a+b)/2,(y0+y1)/2,z0+h/2),(b-a-2*inset,y1-y0+.02+bulge,h-.018),t)


def run(name,variant):
    """A 1 m run: stone base, sill, four timbers, bands, rear rails."""
    p=Part(name)
    p.box((.5,0,BASE_H/2),(1,BASE_T-.03,BASE_H),'mortar_d')           # core
    # Courses: even ones join at the module ends, odd ones a quarter in; the
    # inner joints vary by variant so A/B/C read as different stones.
    inner={'A':[(.5,),(.25,.75),(.45,),(.25,.62,.75),(.55,)],
           'B':[(.4,),(.25,.75),(.6,),(.25,.5,.75),(.35,)],
           'C':[(.55,),(.25,.75),(.3,.7),(.25,.75),(.5,)]}[variant]
    for k in range(4):   # on odd courses the 0.25 m end blocks pair with the neighbour's into one stone
        stone_course(p,0,1,k*COURSE,COURSE,inner[k],k+ord(variant))
    # capstone course: thin, wider, overhanging both faces
    zc=4*COURSE
    for i,(a,b) in enumerate(zip((0,)+inner[4],inner[4]+(1,))):
        p.box(((a+b)/2,0,zc+COURSE*.45),(b-a-.02,BASE_T+.08,COURSE*.9),('stone_l','stone')[i%2])
    # oak sill
    zs=BASE_H;p.box((.5,0,zs+SILL[1]/2),(1,SILL[0],SILL[1]),'oak_d')
    # timbers: squared, chamfered corners suggested by a darker face strip, adzed points
    tops={'A':(2.58,2.5,2.64,2.53),'B':(2.5,2.62,2.55,2.47),'C':(2.6,2.52,2.48,2.63)}[variant]
    z0=zs+SILL[1]
    for i in range(4):
        x=.125+i*PITCH;top=tops[i];w,d=TIMBER
        tone=('oak','oak_l','oak','oak_d')[(i+ord(variant))%4]
        p.box((x,0,(z0+top)/2),(w,d,top-z0),tone)
        tip=top+.22                                           # four-sided point
        hw,hd=w/2,d/2
        p._add([Vector((x-hw,-hd,top)),Vector((x+hw,-hd,top)),Vector((x+hw,hd,top)),Vector((x-hw,hd,top)),Vector((x,0,tip))],
               [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)],'oak_l')
    # iron bands across the front, riveted to every timber
    for zb in(1.62,2.22):
        p.box((.5,-TIMBER[1]/2-.008,zb),(1,.016,.07),'iron')
        for i in range(4):p.box((.125+i*PITCH,-TIMBER[1]/2-.02,zb),(.035,.012,.035),'stone_dd')
    # rear rails and pegs
    for zr in(1.5,2.25):
        p.box((.5,TIMBER[1]/2+.05,zr),(1,.1,.12),'oak_d')
        for i in range(4):p.box((.125+i*PITCH,TIMBER[1]/2+.105,zr),(.04,.02,.04),'oak_l')
    return p


def post(name):
    """Stone pillar: quoined courses (long and short faces alternate), a
    capstone and a pointed cap. Root at the start edge, centre at x=POST_W/2."""
    p=Part(name);c=POST_W/2;h=POST_H-.45;n=11;ch=h/n
    p.box((c,0,h/2),(POST_W-.04,POST_W-.04,h),'mortar_d')
    tones=('stone','stone_m','stone_l','stone_dd','stone')
    for k in range(n):
        z=k*ch;t=lambda j:tones[(k*3+j)%len(tones)]
        if k%2:   # long blocks on the X faces, short on the Y faces
            for s in(-1,1):p.box((c,s*(POST_W/2-.03),z+ch/2),(POST_W,.08,ch-.018),t(s+1))
            for s in(-1,1):
                for j,(a,b) in enumerate(((-.2,.0),(.0,.2))):p.box((c+s*(POST_W/2-.03),(a+b)/2,z+ch/2),(.08,b-a-.016,ch-.018),t(j+2))
        else:
            for s in(-1,1):p.box((c+s*(POST_W/2-.03),0,z+ch/2),(.08,POST_W,ch-.018),t(s+1))
            for s in(-1,1):
                for j,(a,b) in enumerate(((-.2,.0),(.0,.2))):p.box((c+(a+b)/2,s*(POST_W/2-.03),z+ch/2),(b-a-.016,.08,ch-.018),t(j+2))
    p.box((c,0,h+.08),(POST_W+.12,POST_W+.12,.16),'stone_l')            # capstone
    p.box((c,0,h+.19),(POST_W,POST_W,.06),'stone')
    a=POST_W/2-.02;top=POST_H
    p._add([Vector((c-a,-a,h+.22)),Vector((c+a,-a,h+.22)),Vector((c+a,a,h+.22)),Vector((c-a,a,h+.22)),Vector((c,0,top))],
           [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)],'stone_m')
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


def wall_line(make_run,make_post,start,yaw,spans):
    """Posts and runs along a polyline: spans = metres between post centres
    (whole metres, as the adapter would tile them)."""
    d=Vector((math.cos(math.radians(yaw)),math.sin(math.radians(yaw)),0));at=Vector(start)
    make_post(at,yaw)
    for L in spans:
        for i in range(L):make_run(at+d*i,yaw,i)
        at=at+d*L;make_post(at,yaw)
    return at


def main():
    OUT.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs={}
    roots=[module(objs,run(f'Wall2_Run_1m_{v}',v),length=1) for v in 'ABC']
    roots.append(module(objs,post('Wall2_Post'),center=(POST_W/2,0,0)))
    for i,r in enumerate(roots):r.location=(i*1.6,0,0)
    tris={o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in objs.values()}
    print('triangles',tris)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(OUT/'wall-l2-kit.fbx'),use_selection=False,object_types={'EMPTY','MESH'},
        axis_forward='-Z',axis_up='Y',use_triangles=False,mesh_smooth_type='FACE',colors_type='SRGB',add_leaf_bones=False,bake_anim=False)
    cam=S.setup_render();sc=bpy.context.scene
    S.shoot(cam,OUT/'wall-l2-kit.png',-30,22,6.6,target=(2.7,0,1.4),res=(1500,1000))

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
    end=wall_line(mk_run,mk_post,(0,0,0),0,[3,3])
    wall_line(mk_run,mk_post,end,40,[3])
    ground=Part('ground');ground.box((3.5,1.5,-.03),(16,10,.06),'mortar');g=ground.build(objs)
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

    # level 1 and level 2 side by side, same camera and scale
    fetch_l1()
    off=Vector((-4.6,0,0))                       # level 1 on the same line, to the left
    for i in range(3):
        for r in import_l1(f'Palisade_Run_1m_{"ABC"[i]}.fbx'):r.location=off+Vector((i,0,0))
    for x in(0,3):
        for r in import_l1('Palisade_Post.fbx'):r.location=off+Vector((x-.2,0,0))
    holder.location=(-.6,-1.0,0)
    S.shoot(cam,OUT/'wall-l1-vs-l2.png',-18,16,10.4,target=(-.1,0,1.4),res=(1800,900))
    print('done')


if __name__=='__main__':
    main()
