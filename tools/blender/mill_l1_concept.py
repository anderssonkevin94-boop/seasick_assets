"""Level 1 mill concept: a quern under a canvas, wheat in, flour out.

Kevin, 2026-10-02: "now make the lvl 1 mill".

The game's `BuildPlan.Mill` (fire II, food rework): a miller grinds two
wheat into one flour; plot 5.2 x 4.8 m, ridge 3.6 m, 6 input and 6 output
slots; it wears the sawmill as placeholder art. A first-tier building, so
by the art direction a canvas roof, and like the level 1 sawmill: input on
the left, the work in the middle, output on the right, both stores forward
of the canopy, every stock item its own toggleable object.

  - A tall quern on a tree stump, where the reworked Crew_Mill clip turns it
    (MILL below: found by searching the miller's pose against the anatomy
    check; the old clip's knee-high quern could not be reached on the near
    side of the turn). Off to his right and in front, the peg at belly
    height, so his forearm runs level and his left hand hangs free.
  - Quern_Runner turns about its own axis (object origin), its peg on it;
    the take 'Mill1_Grind' turns it once per Crew_Mill loop (1.5 s), in step
    with the miller's fist. (The clip's own preview peg is then not needed.)
  - Input_Sheaf_01..06 (wheat sheaves) on a rack, Output_Sack_01..06 (flour
    sacks) on a pallet, Flour_Heap in the quern's tray (show while grinding).

Writes mill-l1-concept/ (FBX with the take, renders, a GIF of the miller).
"""
import math
import random
import sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

sys.path.insert(0,str(Path(__file__).resolve().parent))
import sawmill_l2_concept as S
from sawmill_l2_concept import Part, C

ROOT=S.ROOT;OUT=ROOT/'mill-l1-concept'
PLOT=(5.2,4.8);RIDGE=3.6
SRC=1.30/1.7                                  # the clips are authored at his 1.30 m source size
C.update(wheat=(214,176,92),wheat_d=(184,146,70),stalk=(196,160,86),linen=(226,214,188),linen_d=(204,190,162),
         flour=(244,240,230),quern=(150,146,136),quern_d=(124,120,112))

PLATFORM=.12
STAND=Vector((.2,.62,PLATFORM))               # Worker_Stand: he faces -Y, as at the level 1 sawmill
# The miller's grip, from the Crew_Mill clip's pose search, at his 1.30 m
# source size in his own frame: the fist circles MILL['r'] about a point
# MILL['right'] to his right and MILL['ahead'] in front, MILL['grip'] up.
MILL=dict(right=.31,ahead=.32,grip=.66,r=.08,lean=10)
Q=STAND+Vector((-MILL['right'],-MILL['ahead'],0))/SRC        # the quern's axis
GRIP_Z=PLATFORM+MILL['grip']/SRC                             # 0.98: belly height
PEG_R=MILL['r']/SRC                                          # 0.105
Q_R=.2                                                       # stone radius: the tray's rim stays clear of his hip
RUNNER_T=.1
RUNNER_TOP=GRIP_Z-.1                                         # the fist closes round the peg's top
Q_BASE_TOP=RUNNER_TOP-RUNNER_T                               # the bed stone's top: the runner turns on it
PEG_TOP=GRIP_Z+.06
CLIP_SECONDS=1.5;FPS=30                       # Crew_Mill


def platform(name):
    p=Part(name);x0,x1,y0,y1=-1.1,1.1,-1.0,1.25
    n=8
    for i in range(n):
        x=x0+(x1-x0)*(i+.5)/n;p.box((x,(y0+y1)/2,PLATFORM-.03),((x1-x0)/n-.012,y1-y0,.06),('wood','wood_l','wood','wood_d')[i%4])
    for y in(y0+.1,(y0+y1)/2,y1-.1):p.box((0,y,.045),(x1-x0,.12,.09),'wood_d')
    p.box((0,y0-.2,.04),(.8,.36,.08),'wood')                                   # the front step
    return p


def quern_base(name):
    """A thick tree stump, a wooden tray on it to catch the flour, the bed
    stone in the tray, a spout to the front."""
    p=Part(name);top=Q_BASE_TOP;z0=PLATFORM
    st=top-.16                                                                # the stump's top, under the tray
    p.cyl((Q.x,Q.y,z0),(Q.x,Q.y,st),.3,'bark',n=10,cap='endgrain')
    for k in range(5):                                                        # root flares
        ang=2*math.pi*k/5+1.2                                             # none toward his feet
        p.beam((Q.x+.2*math.cos(ang),Q.y+.2*math.sin(ang),z0+.22),(Q.x+.42*math.cos(ang),Q.y+.42*math.sin(ang),z0+.02),.12,.1,'bark',up=(0,0,1))
    p.cyl((Q.x,Q.y,st),(Q.x,Q.y,st+.06),Q_R+.05,'wood',n=12,cap='wood_l')        # the tray
    p.cyl((Q.x,Q.y,st+.06),(Q.x,Q.y,st+.1),Q_R+.05,'wood_d',n=12,cap='flour')   # its lip, flour in it
    p.box((Q.x,Q.y-Q_R-.12,st+.06),(.12,.14,.05),'wood_d')                     # the spout
    p.cyl((Q.x,Q.y,st+.08),(Q.x,Q.y,top),Q_R,'quern_d',n=12,cap='quern')       # bed stone
    return p


def quern_runner(name):
    """The turning stone, peg on it, built about its own axis (origin); the
    peg at angle 0 (+X), where the clip's fist is at t=0."""
    p=Part(name,pivot=(Q.x,Q.y,Q_BASE_TOP))
    z=Q_BASE_TOP
    p.cyl((Q.x,Q.y,z+.004),(Q.x,Q.y,RUNNER_TOP),Q_R-.01,'quern',n=12,cap='quern')
    p.cyl((Q.x,Q.y,RUNNER_TOP),(Q.x,Q.y,RUNNER_TOP+.012),.07,'quern_d',n=8)    # the eye, grain goes in here
    p.cyl((Q.x,Q.y,RUNNER_TOP+.004),(Q.x,Q.y,RUNNER_TOP+.03),.05,'wheat',n=8)
    p.cyl((Q.x+PEG_R,Q.y,RUNNER_TOP-.03),(Q.x+PEG_R,Q.y,PEG_TOP),.03,'wood_l',n=6,cap='wood_d')
    return p


def flour_heap(name):
    p=Part(name);top=Q_BASE_TOP
    p.cyl((Q.x,Q.y-Q_R-.26,PLATFORM),(Q.x,Q.y-Q_R-.26,PLATFORM+.06),.11,'flour',n=8)     # under the spout
    return p


def sheaf(p,at,lean=0.,seed=0):
    """A wheat sheaf lying on the rack: stalks bundled and tied, ears splayed."""
    rnd=random.Random(f'sheaf{seed}');a=Vector(at);d=Vector((0,-1,0))           # ears toward the front
    L=.95;r=.11
    p.cyl(a-d*L/2,a+d*(L/2-.25),r*.8,'stalk',n=8,cap='wheat_d')
    p.cyl(a+d*(L/2-.25),a+d*L/2,r,'wheat',n=8,cap='wheat')
    for k in range(6):
        ang=2*math.pi*k/6+rnd.uniform(-.3,.3)
        tip=a+d*(L/2+.08)+Vector((math.cos(ang)*.09,0,math.sin(ang)*.09))
        p.beam(a+d*(L/2-.04)+Vector((math.cos(ang)*.05,0,math.sin(ang)*.05)),tip,.035,.035,'wheat')
    p.cyl(a+d*(-.05),a+d*.03,r*.84,'hemp',n=8)                                       # the band


def sack(p,at,seed=0):
    """A flour sack standing up: plump body, gathered neck, hemp tie."""
    rnd=random.Random(f'sack{seed}');a=Vector(at)
    r=.17+rnd.uniform(-.015,.015);h=.5
    p.cyl(a,a+Vector((0,0,h*.2)),r*.9,'linen_d',n=8)                                 # a plump body: wider in the middle
    p.cyl(a+Vector((0,0,h*.2)),a+Vector((0,0,h*.7)),r,'linen',n=8)
    p.cyl(a+Vector((0,0,h*.7)),a+Vector((0,0,h*.85)),r*.75,'linen',n=8)
    p.cyl(a+Vector((0,0,h*.85)),a+Vector((0,0,h*.97)),r*.32,'linen_d',n=6)           # gathered neck
    p.cyl(a+Vector((0,0,h*.88)),a+Vector((0,0,h*.93)),r*.36,'hemp',n=6)               # tie
    p.box(a+Vector((0,-r-.004,h*.45)),(r*.9,.012,h*.3),'wheat_d')                    # a wheat mark on the cloth


def build(objs):
    root=bpy.data.objects.new('Mill_Level_1',None);bpy.context.scene.collection.objects.link(root)
    for f,n in((platform,'Mill1_Platform'),(quern_base,'Mill1_QuernBase'),(flour_heap,'Flour_Heap')):
        f(n).build(objs).parent=root
    r=quern_runner('Quern_Runner').build(objs);r.parent=root;r.matrix_world=Matrix.Translation((Q.x,Q.y,Q_BASE_TOP))

    # canopy: canvas from two back posts down to front stakes, over the quern only
    c=Part('Mill1_Canopy');bx,by,bz=1.25,1.25,3.4;fx,fy,fz=1.5,-.55,2.85      # a near-flat awning: the game camera sees under it
    for sx in(-1,1):
        c.box((sx*bx,by,bz/2),(.22,.22,bz),'wood')
        c.box((sx*bx,by,bz+.06),(.3,.3,.12),'wood_d')
        c.prism([(sx*bx-.13,by-.13),(sx*bx+.13,by-.13),(sx*bx+.13,by+.13),(sx*bx-.13,by+.13)],-.02,.12,'stone_d')
        c.beam((sx*bx,by,bz-.05),(sx*(fx+.25),fy-.35,0),.03,.03,'hemp')               # guy ropes to the front
        c.box((sx*(fx+.25),fy-.35,.06),(.1,.1,.14),'wood_d')
        c.beam((sx*bx,by,bz-.2),(sx*(bx+.5),by+.7,0),.03,.03,'hemp')                  # and back
        c.box((sx*(bx+.5),by+.7,.06),(.1,.1,.14),'wood_d')
        c.box((sx*fx,fy,fz/2),(.12,.12,fz),'wood')                                     # front poles
    c.box((0,by,bz-.02),(2*bx+.3,.16,.16),'wood_d')                                    # ridge pole between the back posts
    c.tri_board([(-bx,by,bz+.02),(bx,by,bz+.02),(fx,fy,fz),(-fx,fy,fz)],.03,'canvas')
    c.tri_board([(-bx,by-.002,bz+.035),(bx,by-.002,bz+.035),(bx+.1,by-.6,bz-.33+.035),(-bx-.1,by-.6,bz-.33+.035)],.02,'stripe')
    c.build(objs).parent=root

    # input: a low sheaf rack on the left; output: a sack pallet on the right; both forward of the canopy
    ir=Part('Input_Container_Rack');ix=-2.0
    for y in(-.95,.15):
        for sx in(-1,1):ir.box((ix+sx*.48,y,.32),(.08,.08,.64),'wood')
        ir.box((ix,y,.56),(1.06,.1,.08),'wood_d')
        ir.box((ix,y,.18),(1.06,.08,.07),'wood_d')
    for sx in(-1,1):ir.box((ix+sx*.48,-.4,.56),(.08,1.2,.06),'wood')
    ir.build(objs).parent=root
    inp=bpy.data.objects.new('Input_Container',None);bpy.context.scene.collection.objects.link(inp);inp.parent=root;inp.location=(ix,-.4,0)
    for i in range(6):                          # two layers of three, sheaves lying front to back
        p=Part(f'Input_Sheaf_{i+1:02d}');col,row=i%3,i//3
        sheaf(p,(ix+(col-1)*.3,-.4,.71+row*.19),seed=i)
        o=p.build(objs);o.parent=inp;o.matrix_parent_inverse=inp.matrix_world.inverted()

    orr=Part('Output_Container_Pallet');ox=2.0
    orr.box((ox,-.4,.05),(1.1,1.1,.1),'wood_d')
    for k in range(5):orr.box((ox-.44+k*.22,-.4,.12),(.18,1.1,.04),'wood' if k%2 else 'wood_l')
    orr.build(objs).parent=root
    out=bpy.data.objects.new('Output_Container',None);bpy.context.scene.collection.objects.link(out);out.parent=root;out.location=(ox,-.4,0)
    for i in range(6):                          # two rows of three standing sacks
        p=Part(f'Output_Sack_{i+1:02d}');col,row=i%3,i//3
        sack(p,(ox+(col-1)*.36,-.4-.22+row*.44,.14),seed=i)
        o=p.build(objs);o.parent=out;o.matrix_parent_inverse=out.matrix_world.inverted()

    # dressing: a sieve on the back left post, a scoop in a little flour bin, the trade sign
    d=Part('Mill1_Dressing')
    d.cyl((-bx+.16,by,1.5),(-bx+.2,by,1.5),.22,'wood_l',n=12,cap='linen_d')          # sieve hung on the post
    d.box((.75,.45,PLATFORM+.18),(.34,.3,.36),'wood');d.box((.75,.45,PLATFORM+.365),(.3,.26,.01),'flour')
    d.beam((.68,.45,PLATFORM+.36),(.86,.52,PLATFORM+.52),.05,.03,'wood_l')
    sx,sy=bx+.12,by
    d.beam((sx,sy,2.6),(sx+.75,sy,2.6),.08,.08,'wood_d')                               # sign arm off the right post
    d.box((sx+.5,sy,2.2),(.62,.05,.56),'sign')
    for x,yy in((sx+.32,2.56),(sx+.68,2.56)):d.beam((x,sy,yy),(x,sy,2.48),.012,.012,'hemp')
    d.box((sx+.42,sy-.03,2.2),(.14,.02,.32),'wheat');d.cyl((sx+.62,sy-.03,2.2),(sx+.62,sy-.04,2.2),.1,'linen',n=10)   # glyph: an ear and a millstone
    d.build(objs).parent=root

    for mk,at in(('Worker_Stand',STAND),('Worker_Approach',(.6,1.75,0)),('Input_Pickup',(ix,-1.55,0)),('Output_Dropoff',(ox,-1.55,0)),
                 ('Entrance_Anchor',(0,-1.5,0)),('Quern_Anchor',(Q.x,Q.y,Q_BASE_TOP))):
        e=bpy.data.objects.new(mk,None);e.empty_display_size=.15;bpy.context.scene.collection.objects.link(e);e.parent=root;e.location=at
    return root


def animate(objs):
    """Quern_Runner turns once per Crew_Mill loop with the miller's fist:
    the clip's grip angle is a = 2*pi*t (mill_pose), the peg built at 0."""
    sc=bpy.context.scene;sc.render.fps=FPS;sc.render.fps_base=1
    n=round(CLIP_SECONDS*FPS);sc.frame_start,sc.frame_end=0,n
    o=objs['Quern_Runner'];o.rotation_mode='XYZ';o.animation_data_create()
    act=bpy.data.actions.new('Mill1_Grind');o.animation_data.action=act
    for f in(0,n):
        o.rotation_euler=(0,0,2*math.pi*f/n);o.keyframe_insert('rotation_euler',index=2,frame=f)
    fcs=act.fcurves if hasattr(act,'fcurves') else [c for l in act.layers for st in l.strips for cb in st.channelbags for c in cb.fcurves]
    for fc in fcs:
        for kp in fc.keyframe_points:kp.interpolation='LINEAR'
    sc.frame_set(0)


def bounds(objs):
    lo=Vector((1e9,)*3);hi=-lo
    for o in objs:
        if o.type!='MESH':continue
        for v in o.data.vertices:
            w=o.matrix_world@v.co;lo=Vector(map(min,lo,w));hi=Vector(map(max,hi,w))
    return lo,hi


def main():
    OUT.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);objs={}
    build(objs);bpy.context.view_layer.update()
    meshes=[o for o in bpy.data.objects if o.type=='MESH']
    lo,hi=bounds(meshes)
    tris=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes)
    print('bounds',[round(x,2) for x in lo],[round(x,2) for x in hi],'triangles',tris)
    assert -PLOT[0]/2<=lo.x and hi.x<=PLOT[0]/2 and -PLOT[1]/2<=lo.y and hi.y<=PLOT[1]/2,'outside the plot'
    assert hi.z<=RIDGE,'over the ridge'
    animate(objs)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(OUT/'mill-lvl1.fbx'),use_selection=False,object_types={'EMPTY','MESH'},
        axis_forward='-Z',axis_up='Y',use_triangles=False,mesh_smooth_type='FACE',colors_type='SRGB',add_leaf_bones=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0.)
    g=Part('ground');g.box((0,0,-.03),(9,8,.06),'mortar');go=g.build(objs)
    go.data.color_attributes['Col'].data.foreach_set('color',[v for _ in range(len(go.data.loops)) for v in (*[S.lin(k) for k in (104,128,78)],1)])
    cam=S.setup_render()
    S.shoot(cam,OUT/'mill-l1-empty.png',-32,28,7.4,target=(0,0,1.3),res=(1400,1050))
    # the miller at work: Crew_Mill at Worker_Stand, the deckhand at game size
    holder,_=S.load_deckhand();holder.location=STAND
    act=next(a for a in bpy.data.actions if a.name.endswith('Crew_Mill'))
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE' and o.animation_data);arm.animation_data.action=act
    bpy.context.scene.frame_set(10)
    S.shoot(cam,OUT/'mill-l1-hero.png',-32,28,7.4,target=(0,0,1.3),res=(1400,1050))
    S.shoot(cam,OUT/'mill-l1-front.png',0,10,6.6,target=(0,0,1.4),res=(1400,1000))
    S.shoot(cam,OUT/'mill-l1-rear.png',160,26,7.4,target=(0,0,1.3),res=(1400,1050))
    canopy=objs['Mill1_Canopy']
    canopy.hide_render=True
    S.shoot(cam,OUT/'mill-l1-closeup.png',-38,20,2.3,target=(0,.1,.75),res=(1100,1000))
    # does the fist meet the peg? sample the loop
    n=round(CLIP_SECONDS*FPS);worst=0.                 # the imported action's own frame range reads 0
    hand=arm.pose.bones['hand.L'];runner=objs['Quern_Runner']
    for f in range(0,n+1,1):
        bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
        fist=arm.matrix_world@((hand.head+hand.tail)/2);peg=runner.matrix_world@Vector((PEG_R,0,GRIP_Z-Q_BASE_TOP))
        worst=max(worst,math.hypot(fist.x-peg.x,fist.y-peg.y))
    print(f'fist centre to the peg, horizontal, worst over the loop: {worst:.3f} m')
    from PIL import Image
    from render_v15_anims import save_gif
    tmp=OUT/'_frames';tmp.mkdir(exist_ok=True);frames=[]
    for f in range(0,n,2):
        bpy.context.scene.frame_set(f)
        S.shoot(cam,tmp/f'{f:03d}.png',-38,20,2.3,target=(0,.1,.75),res=(560,520))
        im=Image.open(tmp/f'{f:03d}.png').convert('RGBA');bg=Image.new('RGBA',im.size,(40,44,48,255));bg.alpha_composite(im);frames.append(bg.convert('RGB'))
    save_gif(frames,OUT/'mill-l1-grind.gif',int(2000/FPS))
    for f in tmp.glob('*.png'):f.unlink()
    tmp.rmdir()
    canopy.hide_render=False
    print('done')


if __name__=='__main__':
    main()
