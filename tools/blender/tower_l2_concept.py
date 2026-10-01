"""Level 2 watchtower concept: a wide gun deck on stone legs.

Kevin, 2026-10-01: "make the level 2 watch tower as well. it should have a
wider area to stand on to allow for more canon movement."

The level 1 tower (Art/TowerL1, chunky V5) is a 2.4 m deck on four posts in
the 2.6 x 2.6 m plot; Astra's cannon (art-staging/cannon-astra-v1) sweeps a
1.44 m radius at its muzzle corners, so it cannot turn there. Level 2:

  - Same plot on the ground (buildings keep their plot across upgrades):
    four crude stone legs (the level 2 wall's pillars, 2.6 m) inside 2.6 x
    2.6, then squared oak posts with tie beams and X-braces.
  - A 4.2 x 4.2 m deck (three times level 1's area), cantilevered 1.1 m past
    the posts on girders and knee braces.
  - Same contract as level 1, so the game's code still fits: deck at 4.61 m
    (WatchtowerGun.DeckHeight), markers Ladder_Bottom (0,-1.23,0.05),
    Ladder_Top (0,-1.10,4.61), Lookout_Anchor (0,0,4.61). The ladder comes
    up through a hatch in the deck.
  - A low oak parapet (0.72 m) the gun fires over, an iron traverse ring
    round the gun's pivot at the deck's centre.
  - Checked: the cannon's whole footprint below the parapet's top turns a
    full circle clear of the parapet, with room for a gunner behind it.

Writes tower-l2-concept/ (FBX, renders, a traverse GIF).
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

ROOT=W.ROOT;OUT=ROOT/'tower-l2-concept'
REF=Path('/tmp/claude-0/sc/tower')       # level 1 tower and Astra's cannon (fetch_refs)
REF_URL='https://media.githubusercontent.com/media/anderssonkevin94-boop/seasick/ships-into-unity/'
REFS={'watchtower-lvl1.fbx':'Assets/_Project/Art/TowerL1/Models/watchtower-lvl1.fbx','cannon.fbx':'art-staging/cannon-astra-v1/cannon.fbx'}

PLOT=2.6
DECK_Z=4.61                              # WatchtowerGun.DeckHeight
DECK=2.1                                 # deck half-width: 4.2 x 4.2
LEG=.93                                  # leg centres at (+-LEG, +-LEG): capstones just inside the plot
LEG_H=2.6                                # stone leg height (its capstone tops out at 2.31)
POST=.3                                  # oak post section
PLANK_T=.1;JOIST_H=.22
PARAPET_H=.72;PARAPET_T=.14
HATCH=(-.36,.36,-1.50,-1.00)             # x0,x1,y0,y1 in the deck, round the ladder's top, outside the gun wheels' sweep
LADDER_BOTTOM=Vector((0,-1.23,.05));LADDER_TOP=Vector((0,-1.10,DECK_Z))
STONE_TOP=LEG_H-.45+.16


def legs(p_name):
    """Four stone legs: the wall pillar, shorter, no pointed cap."""
    base=W.post(p_name,LEG_H,n=4,cap=False)
    return base


def frame(name):
    p=Part(name);z0=STONE_TOP;z1=DECK_Z-PLANK_T-JOIST_H
    for sx in(-1,1):
        for sy in(-1,1):
            x,y=sx*LEG,sy*LEG
            p.box((x,y,(z0+z1)/2),(POST,POST,z1-z0),'oak')
            for z in(z0+.12,z1-.18):p.box((x,y,z),(POST+.02,POST+.02,.05),'iron')
    for z in(z0+.35,z1-.05):                                     # tie beams, all four sides
        for s in(-1,1):
            p.box((0,s*LEG,z),(2*LEG+POST,.2,.2),'oak_d');p.box((s*LEG,0,z),(.2,2*LEG+POST,.2),'oak_d')
    za,zb=z0+.45,z1-.15                                          # X-braces: sides and back (the ladder's front stays open)
    for a,b in(((-LEG,LEG),(LEG,LEG)),((-LEG,-LEG),(-LEG,LEG)),((LEG,-LEG),(LEG,LEG))):
        A,B=Vector((*a,0)),Vector((*b,0))
        p.beam((A.x,A.y,za),(B.x,B.y,zb),.14,.12,'oak_d');p.beam((A.x,A.y,zb),(B.x,B.y,za),.14,.12,'oak_d')
    # girders on the posts, out to the deck's edge both ways, and knee braces under the overhang
    zg=z1+.11
    for s in(-1,1):
        p.box((s*LEG,0,zg),(.22,2*DECK,.22),'oak_d')            # along Y on the left and right posts
        p.box((0,s*LEG,zg-.22),(2*DECK,.22,.22),'oak_d')         # along X on the front and back posts, under them
    for sx in(-1,1):
        for sy in(-1,1):
            x,y=sx*LEG,sy*LEG
            p.beam((x,y,zg-1.05),(x,sy*(DECK-.12),zg-.1),.14,.14,'oak',up=(1,0,0))     # out along Y
            p.beam((x,y,zg-1.27),(sx*(DECK-.12),y,zg-.32),.14,.14,'oak',up=(0,1,0))    # out along X
    return p


def deck(name):
    p=Part(name);zt=DECK_Z;zb=zt-PLANK_T
    # joists across the girders, skipping the hatch
    for y in(-1.9,-1.58,-.9,-.45,0.,.45,.95,1.45,1.9):
        p.box((0,y,zb-.06),(2*DECK,.12,.12),'oak_d')
    for x in(HATCH[0]-.06,HATCH[1]+.06):p.box((x,(HATCH[2]+HATCH[3])/2,zb-.06),(.12,HATCH[3]-HATCH[2]+.12,.12),'oak_d')   # hatch trimmers
    # planks along X, 0.21 wide, the hatch left open
    n=20;w=2*DECK/n
    for i in range(n):
        y0=-DECK+i*w;y1=y0+w;yc=(y0+y1)/2;tone=('oak','oak_l','oak','oak_d')[i%4]
        if y1>HATCH[2] and y0<HATCH[3]:
            for xa,xb in((-DECK,HATCH[0]),(HATCH[1],DECK)):p.box(((xa+xb)/2,yc,zb+PLANK_T/2),(xb-xa,w-.012,PLANK_T),tone)
        else:p.box((0,yc,zb+PLANK_T/2),(2*DECK,w-.012,PLANK_T),tone)
    # the hatch lid, propped open against the parapet side
    hx0,hx1,hy0,hy1=HATCH
    p.tri_board([(hx0,hy0,zt+.02),(hx1,hy0,zt+.02),(hx1,hy0-.12,zt+.58),(hx0,hy0-.12,zt+.58)],.05,'oak_l')
    # iron traverse ring and pivot block for the gun
    r0,r1=.78,.85                                  # inside the wheels' track, clear of the hatch
    for k in range(24):
        a0,a1=2*math.pi*k/24,2*math.pi*(k+1)/24
        q=[Vector((math.cos(a)*r,math.sin(a)*r,zt+.012)) for a,r in((a0,r0),(a1,r0),(a1,r1),(a0,r1))]
        p._add(q+[v+Vector((0,0,.012)) for v in q],[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'iron')
    p.cyl((0,0,zt),(0,0,zt+.06),.2,'iron',n=10,cap='stone_d')
    return p


def parapet(name):
    """Low oak parapet round the deck: corner and middle posts, vertical
    boards, a cap rail and one iron band. Top at DECK_Z + PARAPET_H."""
    p=Part(name);zt=DECK_Z;top=zt+PARAPET_H;e=DECK-PARAPET_T/2
    for s in(-1,1):
        for along in('x','y'):
            n=16
            for i in range(n):
                u=-DECK+2*DECK*(i+.5)/n;tone=('oak','oak_l')[i%2]
                c=(u,s*e,(zt+top)/2) if along=='x' else (s*e,u,(zt+top)/2)
                sz=(2*DECK/n-.014,PARAPET_T,PARAPET_H) if along=='x' else (PARAPET_T,2*DECK/n-.014,PARAPET_H)
                p.box(c,sz,tone)
            cap=(0,s*e,top+.04) if along=='x' else (s*e,0,top+.04)
            p.box(cap,(2*DECK+.08,PARAPET_T+.08,.08) if along=='x' else (PARAPET_T+.08,2*DECK+.08,.08),'oak_d')
            band=(0,s*(DECK+.008),zt+.42) if along=='x' else (s*(DECK+.008),0,zt+.42)
            p.box(band,(2*DECK,.016,.07) if along=='x' else (.016,2*DECK,.07),'iron')
    # corner posts with short points, and middle posts
    for sx in(-1,1):
        for sy in(-1,1):
            x,y=sx*(DECK-.09),sy*(DECK-.09)
            p.box((x,y,(zt-.2+top+.12)/2),(.2,.2,top+.12-zt+.2),'oak_d')
            h=top+.12;p._add([Vector((x-.1,y-.1,h)),Vector((x+.1,y-.1,h)),Vector((x+.1,y+.1,h)),Vector((x-.1,y+.1,h)),Vector((x,y,h+.2))],
                             [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)],'oak_tip')
    return p


def ladder(name):
    p=Part(name);a,b=LADDER_BOTTOM,LADDER_TOP+Vector((0,0,.75))      # rails run on past the deck: a handhold
    for sx in(-1,1):p.beam((sx*.24+a.x,a.y,a.z-.05),(sx*.24+b.x,b.y,b.z),.07,.07,'oak')
    d=(b-a);n=int((LADDER_TOP.z-a.z)/.3)
    for i in range(1,n+1):
        q=a+d*(i*.3/d.z);p.box((q.x,q.y,q.z),(.5,.05,.05),'oak_l')
    return p


def fetch_refs():
    import urllib.request
    REF.mkdir(parents=True,exist_ok=True)
    for f,path in REFS.items():
        if not (REF/f).exists():urllib.request.urlretrieve(REF_URL+path,REF/f)


def import_ref(f,lift_colours=False):
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(REF/f))
    new=[o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.type=='MESH' and o.data.color_attributes:
            col=o.data.color_attributes.get('Col') or o.data.color_attributes[0];o.data.color_attributes.active_color=col
            if lift_colours:     # the game kit's GameColor is a tint on a texture: approximate with the wall's oak
                for d in col.data:
                    c=d.color;d.color=(*[min(1,v*.75+.0) for v in (S.lin(178),S.lin(122),S.lin(70))],1) if sum(c[:3])>2.5 else c
    return new


def cannon(at=(0,0,DECK_Z),yaw=0.):
    new=import_ref('cannon.fbx');root=next(o for o in new if o.name.startswith('Cannon_Root'))
    root.location=at;root.rotation_euler.z=math.radians(yaw);return root,new


def gun_clearance(new):
    """Radius of the cannon's footprint below the parapet's top (it must turn
    inside the parapet), and of all of it (the muzzle may overhang)."""
    bpy.context.view_layer.update()
    root=next(o for o in new if o.name.startswith('Cannon_Root'));inv=root.matrix_world.inverted()
    low=0.;full=0.
    for o in new:
        if o.type!='MESH':continue
        for v in o.data.vertices:
            q=inv@(o.matrix_world@v.co);r=math.hypot(q.x,q.y)
            full=max(full,r)
            if q.z<PARAPET_H+.02:low=max(low,r)
    return low,full


def ground(objs,size=12):
    g=Part('ground');g.box((0,0,-.03),(size,size,.06),'mortar_d');o=g.build(objs)
    o.data.color_attributes['Col'].data.foreach_set('color',[v for _ in range(len(o.data.loops)) for v in (*[S.lin(k) for k in (104,128,78)],1)])


def build(objs):
    root=bpy.data.objects.new('Watchtower_Level_2',None);bpy.context.scene.collection.objects.link(root)
    lg=legs('TowerL2_Legs');parts=[]
    for sx in(-1,1):
        for sy in(-1,1):
            o=lg.build(objs) if not parts else bpy.data.objects.new('TowerL2_Legs',parts[0].data)
            if parts:bpy.context.scene.collection.objects.link(o)
            o.parent=root;o.location=(sx*LEG-W.POST_W/2,sy*LEG,0);parts.append(o)
    # one mesh for the four legs, as the other kits keep one mesh per material group
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.make_single_user(object=True,obdata=True);bpy.ops.object.join()
    objs['TowerL2_Legs']=parts[0]
    for f in(frame,deck,parapet,ladder):
        n={'frame':'TowerL2_Frame','deck':'TowerL2_Deck','parapet':'TowerL2_Parapet','ladder':'TowerL2_Ladder'}[f.__name__]
        f(n).build(objs).parent=root
    for mk,at in(('Ladder_Bottom',LADDER_BOTTOM),('Ladder_Top',LADDER_TOP),('Lookout_Anchor',(0,0,DECK_Z))):
        e=bpy.data.objects.new(mk,None);e.empty_display_size=.15;bpy.context.scene.collection.objects.link(e);e.parent=root;e.location=at
    return root


def bounds(objs,below=None):
    lo=Vector((1e9,)*3);hi=-lo
    for o in objs:
        if o.type!='MESH':continue
        for v in o.data.vertices:
            w=o.matrix_world@v.co
            if below is not None and w.z>below:continue
            lo=Vector(map(min,lo,w));hi=Vector(map(max,hi,w))
    return lo,hi


def main():
    OUT.mkdir(exist_ok=True);fetch_refs()
    bpy.ops.wm.read_factory_settings(use_empty=True);objs={}
    build(objs);bpy.context.view_layer.update()
    tower=[o for o in bpy.data.objects if o.type=='MESH']
    lo,hi=bounds(tower);glo,ghi=bounds(tower,below=2.4)
    tris={o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in tower}
    print('bounds',[round(x,2) for x in lo],[round(x,2) for x in hi],'on the ground',[round(x,2) for x in glo],[round(x,2) for x in ghi])
    print('triangles',tris,sum(tris.values()))
    assert max(abs(glo.x),abs(glo.y),ghi.x,ghi.y)<=PLOT/2+1e-3,'legs outside the plot'
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(OUT/'watchtower-lvl2.fbx'),use_selection=False,object_types={'EMPTY','MESH'},
        axis_forward='-Z',axis_up='Y',use_triangles=False,mesh_smooth_type='FACE',colors_type='SRGB',add_leaf_bones=False,bake_anim=False)
    # the gun: Astra's cannon on the pivot, for the renders and the clearance check (not exported: the game builds its own)
    root,gun=cannon(yaw=-30)
    low,full=gun_clearance(gun);inner=DECK-PARAPET_T
    print(f'gun footprint below the parapet top: radius {low:.2f}; whole gun {full:.2f}; parapet inner half-width {inner:.2f}; '
          f'room behind the breech for a gunner: {inner-1.07:.2f} m')
    assert low+.25<inner,'the gun cannot turn inside the parapet'
    assert -HATCH[3]>low+.05,'the gun wheels run over the hatch'
    print(f'hatch inner edge {-HATCH[3]:.2f} m from the pivot, wheels sweep {low:.2f} m')
    ground(objs)
    holder,_=S.load_deckhand();holder.location=(.55,1.45,DECK_Z);holder.rotation_euler.z=math.radians(160)
    act=next((a for a in bpy.data.actions if a.name.endswith('Crew_Idle')),None)
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE' and o.animation_data);arm.animation_data.action=act;bpy.context.scene.frame_set(0)
    cam=S.setup_render()
    S.shoot(cam,OUT/'tower-l2-hero.png',-32,26,8.4,target=(0,0,2.8),res=(1200,1300))
    S.shoot(cam,OUT/'tower-l2-front.png',0,6,7.6,target=(0,0,2.9),res=(1100,1300))
    S.shoot(cam,OUT/'tower-l2-rear.png',150,24,8.4,target=(0,0,2.8),res=(1200,1300))
    S.shoot(cam,OUT/'tower-l2-deck.png',-30,44,5.4,target=(0,0,4.9),res=(1300,1100))
    # the gun's reach drawn on the deck: its low footprint (inside) and its muzzle (over the parapet)
    rings=Part('reach')
    for r,col in((low,'stripe'),(full,'brass')):
        for k in range(48):
            a0,a1=2*math.pi*k/48,2*math.pi*(k+.6)/48
            rings.beam((r*math.cos(a0),r*math.sin(a0),DECK_Z+.03),(r*math.cos(a1),r*math.sin(a1),DECK_Z+.03),.04,.01,col)
    rings.build(objs)
    S.shoot(cam,OUT/'tower-l2-top.png',0,89.9,5.2,target=(0,0,4.6),res=(1100,1100))
    for o in bpy.data.objects:
        if o.name.startswith('reach'):o.hide_render=True
    # the gun traversing a full turn: a GIF from the game camera's height
    from PIL import Image
    from render_v15_anims import save_gif
    tmp=OUT/'_frames';tmp.mkdir(exist_ok=True);frames=[]
    holder.hide_render=True
    for o in holder.children_recursive:o.hide_render=True
    for i in range(24):
        root.rotation_euler.z=math.radians(-30+15*i);bpy.context.view_layer.update()
        S.shoot(cam,tmp/f'{i:02d}.png',-30,30,6.6,target=(0,0,4.0),res=(640,640))
        im=Image.open(tmp/f'{i:02d}.png').convert('RGBA');bg=Image.new('RGBA',im.size,(40,44,48,255));bg.alpha_composite(im);frames.append(bg.convert('RGB'))
    save_gif(frames,OUT/'tower-l2-traverse.gif',80)
    for f in tmp.glob('*.png'):f.unlink()
    tmp.rmdir()
    # level 1 beside level 2, same camera
    for o in holder.children_recursive:o.hide_render=False
    holder.hide_render=False;root.rotation_euler.z=math.radians(-30)
    for o in import_ref('watchtower-lvl1.fbx',lift_colours=True):
        if o.parent is None:o.location=(-4.4,0,0)
    S.shoot(cam,OUT/'tower-l1-vs-l2.png',-20,20,10.6,target=(-2.0,0,3.1),res=(1500,1150))
    print('done')


if __name__=='__main__':
    main()
