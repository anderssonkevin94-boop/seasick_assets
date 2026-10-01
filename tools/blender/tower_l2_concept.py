"""Level 2 watchtower concept: the level 1 tower, half stone, with a gun bay.

Kevin, 2026-10-01: "I want essentially the same tower, half stone like the
wall, and the side opposite the ladder to have a small extended section to
make more room for the canon."

The level 1 tower (Art/TowerL1, chunky V5): a closed box on the 2.6 x 2.6 m
plot, corner posts, plank walls, the ladder up the front (-Y), a ~2.4 m deck
at 4.61 m with an open rail and pointed corner posts. Level 2 keeps that:

  - Lower half stone, like the level 2 wall: crude stone corner pillars and
    stone walls to 2.25 m. Upper half oak: corner posts, plank walls, an
    iron band.
  - The deck runs out 1.2 m past the back wall (+Y, opposite the ladder) on
    outrigger beams and knee braces: 2.5 x 3.5 m. Its middle, where the gun
    turns, is a new marker Gun_Pivot (0, 0.6, 4.61).
  - Open rail like level 1's (pointed posts, two rails), low enough for the
    gun to fire over, a gap at the ladder's top.
  - Level 1's contract is unchanged: deck 4.61 m (WatchtowerGun.DeckHeight),
    Ladder_Bottom (0,-1.23,0.05), Ladder_Top (0,-1.10,4.61),
    Lookout_Anchor (0,0,4.61).
  - Checked against Astra's cannon at Gun_Pivot: it turns a full circle
    inside the rail; the room left behind it for a gunner is printed.

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
import crew_v15_mill as M
from sawmill_l2_concept import Part, C

ROOT=W.ROOT;OUT=ROOT/'tower-l2-concept'
REF=Path('/tmp/claude-0/sc/tower')       # level 1 tower and Astra's cannon (fetch_refs)
REF_URL='https://media.githubusercontent.com/media/anderssonkevin94-boop/seasick/ships-into-unity/'
REFS={'watchtower-lvl1.fbx':'Assets/_Project/Art/TowerL1/Models/watchtower-lvl1.fbx','cannon.fbx':'art-staging/cannon-astra-v1/cannon.fbx'}

PLOT=2.6
DECK_Z=4.61                              # WatchtowerGun.DeckHeight
CORNER=.93                               # corner pillars/posts at (+-CORNER, +-CORNER): capstones inside the plot
WALL_Y=.9;WALL_T=.2                      # wall planes at +-0.9: the front face (-1.0) clears the ladder
STONE_H=2.25                             # stone to here, oak above
POST=.3
DECK_X=1.25;DECK_Y0=-1.15;BAY=1.2        # deck: x +-1.25, y from the ladder edge to the bay's end
DECK_Y1=CORNER+.15+BAY                   # 2.35
GUN=Vector((0,(DECK_Y0+DECK_Y1)/2,DECK_Z))   # the middle of the bigger deck: (0, 0.6, 4.61)
RAIL_Z=.44;RAIL_SEC=(.14,.16)            # one chunky rail: centre height above the deck, section (thick, tall)
RAIL_TOP=RAIL_Z+RAIL_SEC[1]/2              # 0.52: under the gun barrel
RAIL_T=RAIL_SEC[0]
POST_SEC=.24                             # rail posts: corners and the ladder gap only
GUN_SCALE=.75                            # Astra's cannon at three quarters: it fits the tower better
LADDER_BOTTOM=Vector((0,-1.23,.05));LADDER_TOP=Vector((0,-1.10,DECK_Z))
LADDER_GAP=.36                           # half-width of the rail's gap at the ladder


def stone_wall(p,axis,at,u0,u1,z0,z1,seed):
    """A crude stone wall in the plane `axis`=at ('y' or 'x'), from u0 to u1
    along it, z0 to z1 high: chunky courses with alternating joints."""
    n=4;ch=(z1-z0)/n;tones=('st1','st2','st3')
    for k in range(n):
        L=u1-u0;cuts=[u0+L*f for f in ((.5,) if k%2 else (.27,.73))]
        edges=[u0]+cuts+[u1]
        for i,(a,b) in enumerate(zip(edges,edges[1:])):
            a2,b2=a+W.JOINT/2,b-W.JOINT/2;zc=z0+k*ch+ch/2;t=tones[(seed+k+i*2)%3]
            if axis=='y':W.stone(p,((a2+b2)/2,at,zc),(b2-a2,WALL_T+.03,ch-W.JOINT),t,1)
            else:W.stone(p,(at,(a2+b2)/2,zc),(WALL_T+.03,b2-a2,ch-W.JOINT),t,0)


def base(name):
    """Stone lower half: four corner pillars and four walls between them."""
    p=Part(name);inner=CORNER-W.POST_W/2
    for s in(-1,1):
        p.box((0,s*WALL_Y,STONE_H/2),(2*inner,WALL_T-.04,STONE_H),'mortar_d')
        p.box((s*WALL_Y,0,STONE_H/2),(WALL_T-.04,2*inner,STONE_H),'mortar_d')
        stone_wall(p,'y',s*WALL_Y,-inner,inner,0,STONE_H,3+s)
        stone_wall(p,'x',s*WALL_Y,-inner,inner,0,STONE_H,6+s)
    return p


def pillars(objs,root):
    """The wall's stone pillar, stopped at STONE_H, at each corner (one mesh)."""
    src=W.post('TowerL2_Pillars',STONE_H+.29,n=4,cap=False)
    tmp=src.build(objs);parts=[tmp]
    for i,(sx,sy) in enumerate(((-1,-1),(1,-1),(-1,1),(1,1))):
        o=tmp if i==0 else bpy.data.objects.new('TowerL2_Pillars',tmp.data.copy())
        if i:bpy.context.scene.collection.objects.link(o);parts.append(o)
        o.location=(sx*CORNER-W.POST_W/2,sy*CORNER,0)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
    parts[0].parent=root;objs['TowerL2_Pillars']=parts[0]


def upper(name):
    """Oak upper half: corner posts, plank walls, sill, top beam, iron band."""
    p=Part(name);z0=STONE_H;zt=DECK_Z-.32;inner=CORNER-POST/2
    for sx in(-1,1):
        for sy in(-1,1):
            x,y=sx*CORNER,sy*CORNER
            p.box((x,y,(z0+zt)/2),(POST,POST,zt-z0),'oak')
            for z in(z0+.15,zt-.15):p.box((x,y,z),(POST+.03,POST+.03,.06),'iron')
    for s in(-1,1):
        for along in('x','y'):
            for z,h,t in((z0+.05,.1,'oak_d'),(zt-.06,.14,'oak_d')):            # sill and top beam
                c=(0,s*WALL_Y,z) if along=='x' else (s*WALL_Y,0,z)
                p.box(c,(2*inner,WALL_T+.04,h) if along=='x' else (WALL_T+.04,2*inner,h),t)
            n=7
            for i in range(n):                                               # vertical planks
                u=-inner+2*inner*(i+.5)/n;tone=('oak','oak_l')[i%2]
                c=(u,s*WALL_Y,(z0+zt)/2) if along=='x' else (s*WALL_Y,u,(z0+zt)/2)
                p.box(c,(2*inner/n-.014,WALL_T-.06,zt-z0-.1) if along=='x' else (WALL_T-.06,2*inner/n-.014,zt-z0-.1),tone)
            c=(0,s*(WALL_Y+WALL_T/2-.02),z0+1.0) if along=='x' else (s*(WALL_Y+WALL_T/2-.02),0,z0+1.0)
            p.box(c,(2*inner,.016,.07) if along=='x' else (.016,2*inner,.07),'iron')
    return p


def deck(name):
    """Deck 2.5 x 3.5 m: joists on the walls and two outriggers into the bay,
    knee braces under the bay, planks, and the iron traverse ring."""
    p=Part(name);zt=DECK_Z;zb=zt-.1
    for x in(-CORNER,0,CORNER):                                              # outriggers: inside the tower out to the bay's end
        p.box((x,(.2+DECK_Y1)/2,zb-.11),(.2,DECK_Y1-.2,.2),'oak_d')
    for y in(DECK_Y0+.1,-.5,0,.5,CORNER,1.7,DECK_Y1-.1):                      # cross joists
        p.box((0,y,zb-.04),(2*DECK_X,.12,.08),'oak_d')
    for x in(-CORNER,0,CORNER):                                              # knee braces from the back wall out to the bay's end
        p.beam((x,WALL_Y+.08,zb-1.15),(x,DECK_Y1-.15,zb-.2),.15,.15,'oak',up=(1,0,0))
    p.box((0,WALL_Y+.08,zb-1.2),(2*CORNER+.3,.16,.16),'oak_d')               # their bearing beam on the back wall
    n=17;w=(DECK_Y1-DECK_Y0)/n
    for i in range(n):
        y0=DECK_Y0+i*w;tone=('oak','oak_l','oak','oak_d')[i%4]
        p.box((0,y0+w/2,zb+.05),(2*DECK_X,w-.012,.1),tone)
    r0,r1=.78,.85
    for k in range(24):
        a0,a1=2*math.pi*k/24,2*math.pi*(k+1)/24
        q=[GUN+Vector((math.cos(a)*r,math.sin(a)*r,.012)) for a,r in((a0,r0),(a1,r0),(a1,r1),(a0,r1))]
        p._add(q+[v+Vector((0,0,.012)) for v in q],[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'iron')
    p.cyl(GUN,GUN+Vector((0,0,.06)),.2,'iron',n=10,cap='stone_d')
    return p


def rail(name):
    """Level 1's open rail, simplified for readability: chunky pointed posts
    at the four corners and either side of the ladder, one heavy rail."""
    p=Part(name);zt=DECK_Z;e=RAIL_T/2;h=POST_SEC/2
    x0,x1,y0,y1=-DECK_X+h,DECK_X-h,DECK_Y0+h,DECK_Y1-h
    posts=[(x,y) for x in(x0,x1) for y in(y0,y1)]+[(-LADDER_GAP-h,y0),(LADDER_GAP+h,y0)]
    top=zt+RAIL_TOP+.14
    for x,y in posts:
        p.box((x,y,(zt-.1+top)/2),(POST_SEC,POST_SEC,top-zt+.1),'oak_d')
        p._add([Vector((x-h,y-h,top)),Vector((x+h,y-h,top)),Vector((x+h,y+h,top)),Vector((x-h,y+h,top)),Vector((x,y,top+.24))],
               [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)],'oak_tip')
    z=zt+RAIL_Z;t,hh=RAIL_SEC
    p.box((x0,(y0+y1)/2,z),(t,y1-y0,hh),'oak');p.box((x1,(y0+y1)/2,z),(t,y1-y0,hh),'oak')
    p.box((0,y1,z),(x1-x0,t,hh),'oak')
    for a,b in((x0,-LADDER_GAP-h),(LADDER_GAP+h,x1)):p.box(((a+b)/2,y0,z),(b-a,t,hh),'oak')
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


def import_ref(f):
    """Import a reference FBX. The level 1 tower's GameColor is a tint the
    game multiplies by its wood and rope textures: approximated here with
    each texture's mean colour, as crew_v15_mill does for the mill."""
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(REF/f))
    new=[o for o in bpy.data.objects if o not in before]
    mean={'SS_TowerL1_Wood':(140,88,31),'SS_TowerL1_Hemp':(157,120,68)}
    for o in new:
        if o.type!='MESH' or not o.data.color_attributes:continue
        me=o.data;gc=me.color_attributes.get('GameColor')
        if gc is None:
            me.color_attributes.active_color=me.color_attributes.get('Col') or me.color_attributes[0];continue
        col=me.color_attributes.new('Col','BYTE_COLOR','CORNER');gc=me.color_attributes['GameColor']
        mats=[m.name.split('.')[0] if m else '' for m in me.materials]
        for p in me.polygons:
            t=mean.get(mats[p.material_index] if p.material_index<len(mats) else '',(255,255,255))
            for li in p.loop_indices:
                g=gc.data[li].color;col.data[li].color=(*[g[i]*M._lin(t[i]/255) for i in range(3)],1)
        me.color_attributes.active_color=me.color_attributes['Col']
    return new


def cannon(at=GUN,yaw=0.):
    new=import_ref('cannon.fbx');root=next(o for o in new if o.name.startswith('Cannon_Root'))
    root.location=at;root.rotation_euler.z=math.radians(yaw);root.scale=(GUN_SCALE,)*3;return root,new


def gun_reach(new):
    """Radius of the cannon's footprint below the rail's top (it must turn
    inside the rail), of all of it, and of its breech end."""
    bpy.context.view_layer.update()
    root=next(o for o in new if o.name.startswith('Cannon_Root'))
    turn=root.matrix_world.to_quaternion().inverted();at=root.matrix_world.translation   # world metres, the gun's own axes
    low=full=rear=0.
    for o in new:
        if o.type!='MESH':continue
        for v in o.data.vertices:
            q=turn@(o.matrix_world@v.co-at);r=math.hypot(q.x,q.y);full=max(full,r)
            if q.z<RAIL_TOP+.05:low=max(low,r)
            if q.y>0:rear=max(rear,q.y)
    return low,full,rear


def ground(objs,size=12):
    g=Part('ground');g.box((0,0,-.03),(size,size,.06),'mortar_d');o=g.build(objs)
    o.data.color_attributes['Col'].data.foreach_set('color',[v for _ in range(len(o.data.loops)) for v in (*[S.lin(k) for k in (104,128,78)],1)])


def build(objs):
    root=bpy.data.objects.new('Watchtower_Level_2',None);bpy.context.scene.collection.objects.link(root)
    pillars(objs,root)
    for f,n in((base,'TowerL2_Stone'),(upper,'TowerL2_Timber'),(deck,'TowerL2_Deck'),(rail,'TowerL2_Rail'),(ladder,'TowerL2_Ladder')):
        f(n).build(objs).parent=root
    for mk,at in(('Ladder_Bottom',LADDER_BOTTOM),('Ladder_Top',LADDER_TOP),('Lookout_Anchor',(0,0,DECK_Z)),('Gun_Pivot',GUN)):
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
    for f in OUT.glob('*'):
        if f.suffix in('.png','.gif','.fbx'):f.unlink()              # the first (wide-deck) version's files go
    bpy.ops.wm.read_factory_settings(use_empty=True);objs={}
    build(objs);bpy.context.view_layer.update()
    tower=[o for o in bpy.data.objects if o.type=='MESH']
    lo,hi=bounds(tower);glo,ghi=bounds(tower,below=3.0)
    tris={o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in tower}
    print('bounds',[round(x,2) for x in lo],[round(x,2) for x in hi],'below 3 m',[round(x,2) for x in glo],[round(x,2) for x in ghi])
    print('triangles',tris,sum(tris.values()))
    assert max(-glo.x,-glo.y,ghi.x,ghi.y)<=PLOT/2+1e-3,'the tower leaves its plot below the deck'
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(OUT/'watchtower-lvl2.fbx'),use_selection=False,object_types={'EMPTY','MESH'},
        axis_forward='-Z',axis_up='Y',use_triangles=False,mesh_smooth_type='FACE',colors_type='SRGB',add_leaf_bones=False,bake_anim=False)
    # Astra's cannon at Gun_Pivot, for the renders and the clearance check (not exported: the game builds its own)
    root,gun=cannon(yaw=-30)
    low,full,rear=gun_reach(gun)
    side=DECK_X-RAIL_T-GUN.x;fore=GUN.y-(DECK_Y0+RAIL_T)
    print(f'gun at {tuple(round(v,2) for v in GUN)}: low footprint radius {low:.2f}, whole gun {full:.2f}, breech end {rear:.2f}')
    print(f'rail inside: {side:.2f} m to each side, {fore:.2f} m fore and aft; room behind the breech for a gunner: '
          f'{fore-rear:.2f} m firing toward the ladder or the bay, {side-rear:.2f} m firing to the sides')
    assert low+.2<side,'the gun cannot turn inside the rail'
    ground(objs)
    holder,_=S.load_deckhand();holder.location=(-.75,GUN.y+1.25,DECK_Z);holder.rotation_euler.z=math.radians(200)
    act=next((a for a in bpy.data.actions if a.name.endswith('Crew_Idle')),None)
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE' and o.animation_data);arm.animation_data.action=act;bpy.context.scene.frame_set(0)
    cam=S.setup_render()
    S.shoot(cam,OUT/'tower-l2-hero.png',-32,26,7.8,target=(0,.4,2.8),res=(1150,1300))
    S.shoot(cam,OUT/'tower-l2-front.png',0,6,7.0,target=(0,.4,2.9),res=(1000,1300))
    S.shoot(cam,OUT/'tower-l2-side.png',-90,10,7.6,target=(0,.5,2.9),res=(1150,1300))
    S.shoot(cam,OUT/'tower-l2-rear.png',150,24,7.8,target=(0,.4,2.8),res=(1150,1300))
    S.shoot(cam,OUT/'tower-l2-deck.png',-30,44,4.6,target=(0,.5,4.9),res=(1300,1100))
    rings=Part('reach')
    for r,col in((low,'stripe'),(full,'brass')):
        for k in range(48):
            a0,a1=2*math.pi*k/48,2*math.pi*(k+.6)/48
            rings.beam(GUN+Vector((r*math.cos(a0),r*math.sin(a0),.03)),GUN+Vector((r*math.cos(a1),r*math.sin(a1),.03)),.04,.01,col)
    rings.build(objs)
    S.shoot(cam,OUT/'tower-l2-top.png',0,89.9,4.6,target=(0,.5,4.6),res=(1000,1150))
    for o in bpy.data.objects:
        if o.name.startswith('reach'):o.hide_render=True
    from PIL import Image
    from render_v15_anims import save_gif
    tmp=OUT/'_frames';tmp.mkdir(exist_ok=True);frames=[]
    for o in [holder]+list(holder.children_recursive):o.hide_render=True
    for i in range(24):
        root.rotation_euler.z=math.radians(-30+15*i);bpy.context.view_layer.update()
        S.shoot(cam,tmp/f'{i:02d}.png',-30,32,5.6,target=(0,.5,4.2),res=(640,640))
        im=Image.open(tmp/f'{i:02d}.png').convert('RGBA');bg=Image.new('RGBA',im.size,(40,44,48,255));bg.alpha_composite(im);frames.append(bg.convert('RGB'))
    save_gif(frames,OUT/'tower-l2-traverse.gif',80)
    for f in tmp.glob('*.png'):f.unlink()
    tmp.rmdir()
    for o in [holder]+list(holder.children_recursive):o.hide_render=False
    root.rotation_euler.z=math.radians(-30)
    for o in import_ref('watchtower-lvl1.fbx'):
        if o.parent is None:o.location=(-3.8,0,0)
    S.shoot(cam,OUT/'tower-l1-vs-l2.png',-20,18,10.6,target=(-1.9,.3,3.1),res=(1500,1200))
    print('done')


if __name__=='__main__':
    main()
