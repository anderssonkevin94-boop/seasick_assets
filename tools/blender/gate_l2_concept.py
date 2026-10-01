"""Level 2 gate concept, for the level 2 wall (wall_l2_concept.py).

Kevin, 2026-10-01: "now make the level two gate".

The level 2 wall's materials on the level 1 gate's contract
(art-staging/palisade-astra-lvl1-v2 README, "Gate"), so the wall adapter can
swap it in: metres, Blender +X along the wall, +Y the rear, +Z up; a 3 m
module whose root is at its START end on the ground; `__Snap_Start` (0,0,0),
`__Snap_End` (3,0,0), `__Passage` (1.5,0,0); the gate brings its own two
pillars (no wall pillar goes on its nodes); the leaves hang from hinge
empties and swing outward to -Y: left -100 degrees, right +100 about local Z.

  - Pillars: the wall's crude stone pillars, taller (3.6 m, seven courses),
    inside the module: centres 0.28 and 2.72.
  - No lintel (Kevin, 2026-10-01: "remove the top beam"): the opening is
    open to the sky between the two pillars.
  - Leaves: four vertical oak planks each, pointed like the wall's timbers;
    two long iron strap hinges and studs on the front, three ledges and a
    Z-brace on the back, a ring pull at the meeting edge.
  - Breached: the pillars stand, the leaves are gone, rubble and
    one broken leaf stump on the left hinge.

Writes wall-l2-concept/gate-l2-kit.fbx and gate renders.
"""
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

sys.path.insert(0,str(Path(__file__).resolve().parent))
import wall_l2_concept as W
import sawmill_l2_concept as S
from sawmill_l2_concept import Part, C

OUT=W.OUT
SPAN=3.0
PW=W.POST_W                                   # 0.56
PILLAR_H=3.6
OPEN_X0,OPEN_X1=PW,SPAN-PW                    # clear opening 0.56..2.44 (1.88 m)
HINGE_Y=-.20                                  # hinges near the pillars' front face, so the leaves clear the stone at 100 degrees open
HINGE_INSET=.04                               # hinge line off the pillar's inner face
LEAF_GAP=.012
LEAF_W=(OPEN_X1-OPEN_X0)/2-HINGE_INSET-LEAF_GAP*1.5
LEAF_T=.09
LEAF_Z0,LEAF_TOP=.06,2.55
OPEN_DEG=100


def leaf(name,side):
    """One leaf in its hinge's frame: it runs +X from the hinge for the left
    leaf, -X for the right; front face toward -Y."""
    p=Part(name);s=1 if side=='L' else -1
    x0=LEAF_GAP;n=4;pw=LEAF_W/n
    y_front=.01;yc=y_front+LEAF_T/2                       # planks just behind the hinge line
    for i in range(n):
        xa=x0+i*pw;xc=s*(xa+pw/2)
        top=LEAF_TOP-(.0 if i in(1,2) else .05)-.03*((i*3)%2)
        tone=('oak','oak_l')[i%2]
        p.box((xc,yc,(LEAF_Z0+top)/2),(pw-.012,LEAF_T,top-LEAF_Z0),tone)
        hw,hd=(pw-.012)/2,LEAF_T/2;tip=top+.17
        p._add([Vector((xc-hw,yc-hd,top)),Vector((xc+hw,yc-hd,top)),Vector((xc+hw,yc+hd,top)),Vector((xc-hw,yc+hd,top)),Vector((xc,yc,tip))],
               [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)],'oak_tip')
    # front: two long strap hinges from the hinge side, studs along them
    yf=y_front-.012
    for zh in(.45,2.05):
        L=LEAF_W*.78
        p.box((s*(x0+L/2),yf,zh),(L,.016,.075),'iron')
        p.box((s*(x0+L+.03),yf,zh),(.07,.016,.11),'iron')            # the strap's spade end
        for i in range(4):p.box((s*(x0+.12+i*L/4),yf-.01,zh),(.03,.012,.03),'stone_d')
        p.cyl((0,yf,zh-.06),(0,yf,zh+.06),.025,'iron',n=6)           # hinge knuckle on the pintle
    # ring pull at the meeting edge
    xr=s*(x0+LEAF_W-.13);zr=1.15
    p.box((xr,yf,zr),(.08,.012,.08),'iron')
    for k in range(8):
        a0,a1=2*math.pi*k/8,2*math.pi*(k+1)/8;r=.06
        p.beam((xr+r*math.sin(a0),yf-.025,zr-.08+r*(1-math.cos(a0))),(xr+r*math.sin(a1),yf-.025,zr-.08+r*(1-math.cos(a1))),.014,.014,'iron')
    # back: three ledges and a Z-brace
    yb=y_front+LEAF_T+.03
    zs=(.3,1.3,2.25)
    for z in zs:p.box((s*(x0+LEAF_W/2),yb,z),(LEAF_W-.06,.06,.14),'oak_d')
    for za,zb in zip(zs,zs[1:]):
        p.beam((s*(x0+.08),yb,za+.06),(s*(x0+LEAF_W-.08),yb,zb-.06),.12,.06,'oak_d',up=(0,1,0))
    return p


def pillar(name):
    return W.post(name,PILLAR_H,n=7)


def pintles(name):
    """The iron pins the leaves hang on, set into the pillars' inner faces at
    the two hinge heights."""
    p=Part(name)
    for x in(OPEN_X0,OPEN_X1):
        for z in(.45,2.05):p.box((x+(.025 if x<1.5 else -.025),HINGE_Y,z),(.05,.04,.04),'iron')
    return p


def rubble(name):
    p=Part(name)
    for i,(x,y,z,sx,sy,sz) in enumerate(((.75,-.35,.1,.34,.26,.2),(1.1,-.6,.08,.28,.24,.16),(2.1,-.4,.1,.36,.3,.2),
                                         (1.7,.2,.07,.26,.2,.14),(.95,.15,.06,.2,.18,.12))):
        W.stone(p,(x,y,z),(sx,sy,sz),('st1','st2','st3')[i%3],2)
    # what is left of the left leaf: two splintered planks on the bottom hinge
    for i,top in enumerate((.95,.62)):
        x=OPEN_X0+HINGE_INSET+.13+i*.24
        p.box((x,HINGE_Y+.055,(LEAF_Z0+top)/2),(.22,LEAF_T,top-LEAF_Z0),'oak_d')
        p._add([Vector((x-.11,HINGE_Y+.01,top)),Vector((x+.11,HINGE_Y+.01,top)),Vector((x+.11,HINGE_Y+.1,top)),Vector((x-.11,HINGE_Y+.1,top)),
                Vector((x+.04,HINGE_Y+.055,top+.22))],[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)],'oak_tip')
    return p


def empty(name,parent,at):
    e=bpy.data.objects.new(name,None);e.empty_display_size=.1;bpy.context.scene.collection.objects.link(e)
    e.parent=parent;e.location=at;return e


def build_gate(objs,prefix='Gate2',opened=0.):
    """The intact gate: root at its start end. opened: 0 closed .. 1 open."""
    root=bpy.data.objects.new(prefix,None);bpy.context.scene.collection.objects.link(root)
    for side,x in(('Left',0.),('Right',SPAN-PW)):
        o=pillar(f'{prefix}_Pillar_{side}').build(objs);o.parent=root;o.location=(x,0,0)
    pintles(f'{prefix}_Pintles').build(objs).parent=root
    hl=empty(f'{prefix}_Hinge',root,(OPEN_X0+HINGE_INSET,HINGE_Y,0));hr=empty(f'{prefix}_Hinge_Right',root,(OPEN_X1-HINGE_INSET,HINGE_Y,0))
    ll=leaf(f'{prefix}_Leaf_Left','L').build(objs);ll.parent=hl
    lr=leaf(f'{prefix}_Leaf_Right','R').build(objs);lr.parent=hr
    hl.rotation_euler.z=math.radians(-OPEN_DEG*opened);hr.rotation_euler.z=math.radians(OPEN_DEG*opened)
    for mk,at in(('Snap_Start',(0,0,0)),('Snap_End',(SPAN,0,0)),('Passage',(SPAN/2,0,0)),
                 ('Post_Center_Left',(PW/2,0,0)),('Post_Center_Right',(SPAN-PW/2,0,0))):
        empty(f'{prefix}__{mk}',root,at)
    return root


def swing_clearance(objs,prefix='Gate2'):
    """Closest approach (m) of either leaf to its pillar's actual stones,
    over the whole swing in 5-degree steps. Negative: they overlap."""
    from mathutils.bvhtree import BVHTree
    dg=bpy.context.evaluated_depsgraph_get();worst=9.
    for side,hn in(('Left','Hinge'),('Right','Hinge_Right')):
        pil=objs[f'{prefix}_Pillar_{side}'];leaf_o=objs[f'{prefix}_Leaf_{side}'];h=bpy.data.objects[f'{prefix}_{hn}']
        bpy.context.view_layer.update()
        tree=BVHTree.FromObject(pil,dg)               # in the pillar's local frame
        inv=pil.matrix_world.inverted()
        for deg in range(0,OPEN_DEG+1,5):
            h.rotation_euler.z=math.radians(-deg if side=='Left' else deg);bpy.context.view_layer.update()
            for v in leaf_o.data.vertices:
                if Vector((v.co.x,v.co.y)).length<.05:continue   # the knuckle round the pintle: meant to touch
                q=inv@(leaf_o.matrix_world@v.co);hit=tree.find_nearest(q)
                if hit[0] is None:continue
                # the pillar is many closed stone shells: test against its solid footprint
                # (stones stand up to 2 cm proud), and take the distance outside it
                inside=-.02<q.x<PW+.02 and abs(q.y)<PW/2+.02 and q.z<PILLAR_H
                d=-hit[3] if inside else hit[3]
                if d<worst:worst=d;where=(side,deg,tuple(round(c,3) for c in v.co))
        h.rotation_euler.z=0
    bpy.context.view_layer.update()
    print('closest',where)
    return worst


def build_breached(objs,prefix='Gate2_Breached'):
    root=bpy.data.objects.new(prefix,None);bpy.context.scene.collection.objects.link(root)
    for side,x in(('Left',0.),('Right',SPAN-PW)):
        o=pillar(f'{prefix}_Pillar_{side}').build(objs);o.parent=root;o.location=(x,0,0)
    rubble(f'{prefix}_Rubble').build(objs).parent=root
    for mk,at in(('Snap_Start',(0,0,0)),('Snap_End',(SPAN,0,0)),('Passage',(SPAN/2,0,0))):empty(f'{prefix}__{mk}',root,at)
    return root


def wall_either_side(objs,x0,x1,legs=2):
    """Level 2 wall runs to the left of x0 and right of x1, a pillar at each far end."""
    kit={v:W.run(f'_run_{v}',v).build(objs) for v in 'ABC'};pk=W.post('_post').build(objs)
    for o in list(kit.values())+[pk]:o.hide_render=True
    sc=bpy.context.scene
    def mk(data,at):
        o=bpy.data.objects.new('w',data);sc.collection.objects.link(o);o.location=at;return o
    for i in range(legs):
        mk(kit['ABC'[i%3]].data,(x0-legs+i,0,0));mk(kit['CAB'[i%3]].data,(x1+i,0,0))
    mk(pk.data,(x0-legs-PW/2,0,0));mk(pk.data,(x1+legs-PW/2,0,0))


def ground(objs,c=(1.5,0,0),size=(14,10)):
    g=Part('ground');g.box((c[0],c[1],-.03),(size[0],size[1],.06),'mortar_d');o=g.build(objs)
    o.data.color_attributes['Col'].data.foreach_set('color',[v for _ in range(len(o.data.loops)) for v in (*[S.lin(k) for k in (104,128,78)],1)])


def deckhand(at,yaw=0,action='Crew_Idle',frame=0):
    holder,_=S.load_deckhand();holder.location=at;holder.rotation_euler.z=math.radians(yaw)
    act=next((a for a in bpy.data.actions if a.name.endswith(action)),None)
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE' and o.animation_data)
    arm.animation_data.action=act;bpy.context.scene.frame_set(frame)
    return holder


def main():
    OUT.mkdir(exist_ok=True)
    # the kit: intact (closed) and breached, as their own roots
    bpy.ops.wm.read_factory_settings(use_empty=True);objs={}
    g=build_gate(objs);b=build_breached(objs);b.location=(4,0,0)
    clear=swing_clearance(objs);print('leaf-to-pillar clearance over the swing',round(clear,3))
    assert clear>.01,clear
    tris={o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in objs.values()}
    print('triangles',tris,'gate',sum(v for k,v in tris.items() if not k.startswith('Gate2_Breached')))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(OUT/'gate-l2-kit.fbx'),use_selection=False,object_types={'EMPTY','MESH'},
        axis_forward='-Z',axis_up='Y',use_triangles=False,mesh_smooth_type='FACE',colors_type='SRGB',add_leaf_bones=False,bake_anim=False)

    # in the wall: closed, open, and breached, with the deckhand for scale
    for state in('closed','open','breached'):
        bpy.ops.wm.read_factory_settings(use_empty=True);objs={}
        if state=='breached':build_breached(objs)
        else:build_gate(objs,opened=1. if state=='open' else 0.)
        wall_either_side(objs,0,SPAN);ground(objs)
        if state=='open':deckhand((1.5,.7,0),0,'Crew_Walk',8)
        else:deckhand((2.2,-1.2,0))
        cam=S.setup_render()
        S.shoot(cam,OUT/f'gate-l2-{state}.png',-28,22,7.6,target=(1.6,0,1.6),res=(1500,1000))
        if state=='closed':
            S.shoot(cam,OUT/'gate-l2-front.png',0,6,5.2,target=(1.5,0,1.8),res=(1200,1000))
            S.shoot(cam,OUT/'gate-l2-rear.png',160,20,5.6,target=(1.5,0,1.6),res=(1200,1000))
            S.shoot(cam,OUT/'gate-l2-closeup.png',-35,14,2.6,target=(1.0,-.1,1.4),res=(1000,1100))
        if state=='open':
            S.shoot(cam,OUT/'gate-l2-open-top.png',0,89.9,4.8,target=(1.5,-.6,1.0),res=(1200,1000))

    # level 1's gate beside level 2's, same camera
    bpy.ops.wm.read_factory_settings(use_empty=True);objs={}
    build_gate(objs);wall_either_side(objs,0,SPAN,1);ground(objs,(-1,0,0),(18,10))
    W.fetch_l1()
    l1=W.L1/'Gate_L1.fbx'
    if not l1.exists():
        import urllib.request;urllib.request.urlretrieve(W.L1_URL+'Gate_L1.fbx',l1)
    for r in W.import_l1('Gate_L1.fbx'):r.location=(-4.6,0,0)
    deckhand((-.6,-1.0,0))
    cam=S.setup_render()
    S.shoot(cam,OUT/'gate-l1-vs-l2.png',-18,16,9.6,target=(-.6,0,1.6),res=(1800,950))
    print('done')


if __name__=='__main__':
    main()
