"""The game's level 1 lumber mill ("concept C Timber Fan", MillL1Import) as
a work environment for the v15 deckhand's sawmill animation.

`crew-meshy-v15/anims/env/lumber-mill-state-kit.fbx` is a copy of the game's
Assets/_Project/Art/MillL1/Models/lumber-mill-state-kit.fbx (reference only;
the game's file is the one that ships). It is built at the game's 1.7 m
scale, the deckhand at his 1.30 m source size (AstraPlaytestImport scales him
to 1.7 m), so the mill is loaded at 1.30 / 1.7.

The mill's faces are coloured in the game by a wood or rope texture times its
`GameColor` vertex colours. For preview renders each face's colour here is
`GameColor` times the texture's average colour, written to a `Col` layer.
"""
import math
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[2]
FBX=ROOT/'crew-meshy-v15/anims/env/lumber-mill-state-kit-lowbench.fbx'   # the bench lowered for him (mill_l1_lowbench.py)
FBX_GAME=ROOT/'crew-meshy-v15/anims/env/lumber-mill-state-kit.fbx'
SCALE=1.30/1.7
TEXTURE_MEAN={'SS_LumberL1_Wood':(140,88,31),'SS_LumberL1_Hemp':(157,120,68)}   # wood-tile-512, rope-tile-512


def _lin(c):return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4



def load(state='cutting',logs=3,planks=3,fbx=None):
    """Import the mill, scaled, and show one bench state ('empty', 'loaded',
    'cutting', 'finished') plus the first `logs` input logs and `planks`
    output planks. Returns {name: object}."""
    before=set(bpy.data.objects);sc=bpy.context.scene;fps=(sc.render.fps,sc.render.fps_base)
    bpy.ops.import_scene.fbx(filepath=str(fbx or FBX))
    sc.render.fps,sc.render.fps_base=fps           # the FBX importer resets the scene rate to the file's
    objs={o.name.split('.')[0]:o for o in bpy.data.objects if o not in before}
    objs['LumberMill_C_Level_1'].scale=(SCALE,)*3
    for o in objs.values():
        n=o.name.split('.')[0]
        if n.startswith('Input_Log_'):o.hide_render=o.hide_viewport=int(n[-2:])>logs
        if n.startswith('Output_Plank_'):o.hide_render=o.hide_viewport=int(n[-2:])>planks
        if n in('Bench_Loaded','Bench_Cutting','Mallet_Tool') or n.startswith('Bench_Result'):
            show={'loaded':('Bench_Loaded',),'cutting':('Bench_Cutting','Mallet_Tool'),
                  'finished':('Bench_Result',),'empty':()}[state]
            o.hide_render=o.hide_viewport=not any(n.startswith(k) for k in show)
        if o.type=='MESH':
            me=o.data;gc=me.color_attributes.get('GameColor')
            if gc is None:continue
            col=me.color_attributes.new('Col','BYTE_COLOR','CORNER');gc=me.color_attributes['GameColor']   # re-fetch: adding a layer invalidates it
            mats=[m.name.split('.')[0] if m else '' for m in me.materials]
            for p in me.polygons:
                t=TEXTURE_MEAN.get(mats[p.material_index] if p.material_index<len(mats) else '',(255,255,255))
                for li in p.loop_indices:
                    g=gc.data[li].color
                    col.data[li].color=(*[g[i]*_lin(t[i]/255) for i in range(3)],1)   # byte colours read and write linear
            me.color_attributes.remove(me.color_attributes['GameColor'])   # previews and the viewer's GLB use Col only
            col=me.color_attributes['Col'];me.color_attributes.active_color=col;me.color_attributes.render_color_index=0
            for p in me.polygons:p.use_smooth=False
    bpy.context.view_layer.update()
    return objs


def marker(objs,name):
    return objs[name].matrix_world.translation.copy()


# ---------------------------------------------------------------- a tree
TREE_FBX=ROOT/'crew-meshy-v15/anims/env/Tree_B1.fbx'   # Astra's Tree_B1 (art-staging/tree-b1-astra-v1)
TREE_STAND=1.1*SCALE          # CampWorker.Stand: a chopper stands 1.1 m (game) from the trunk's centre
TREE_GAME_SCALE=9.0/6.94      # the game grows trees 9-14 m (WorldScale.TreeMin/Max); Tree_B1 is 6.94 m: the smallest in-game size
TRUNK_R=.30*TREE_GAME_SCALE*SCALE   # trunk radius at his waist and chest (0.30 m on the 6.94 m model)
TRUNK_CENTRE=(-.015,0.)       # the trunk's centre in the tree's own frame (game metres)


def load_tree():
    """Astra's tree at his scale, its trunk TREE_STAND in front of him (-Y),
    where CampWorker.Stand puts a chopper. Returns {name: object}."""
    before=set(bpy.data.objects);sc=bpy.context.scene;fps=(sc.render.fps,sc.render.fps_base)
    bpy.ops.import_scene.fbx(filepath=str(TREE_FBX))
    sc.render.fps,sc.render.fps_base=fps
    objs={o.name.split('.')[0]:o for o in bpy.data.objects if o not in before}
    for o in objs.values():
        if o.parent is None:
            o.scale=(SCALE*TREE_GAME_SCALE,)*3
            o.location=(-TRUNK_CENTRE[0]*SCALE*TREE_GAME_SCALE,-TREE_STAND-TRUNK_CENTRE[1]*SCALE*TREE_GAME_SCALE,0)
        if o.type=='MESH':
            me=o.data;col=me.color_attributes.get('Col')
            if col:me.color_attributes.active_color=col;me.color_attributes.render_color_index=0
            for p in me.polygons:p.use_smooth=False
    bpy.context.view_layer.update()
    return objs


ROCK_FBX=ROOT/'crew-meshy-v15/anims/env/Stone_Field.fbx'   # Astra's Stone_Field (art-staging/stone-resources-astra-v2), the commonest deposit
ROCK_FOOTPRINT=1.38*.8         # StoneDeposit.FootprintRadius: the mesh's widest bounds corner, x0.8, at size 1
ROCK_STAND=max(1.1,ROCK_FOOTPRINT+.7)*SCALE   # StoneDeposit.StandOff: the footprint plus an arm's length (1.80 m game)


def load_rock():
    """Astra's Stone_Field at his scale, its pivot ROCK_STAND in front of him
    (-Y) where StoneDeposit.StandOff puts a miner, its front (and
    __Mine_Target) turned to face him. Returns {name: object}."""
    before=set(bpy.data.objects);sc=bpy.context.scene;fps=(sc.render.fps,sc.render.fps_base)
    bpy.ops.import_scene.fbx(filepath=str(ROCK_FBX))
    sc.render.fps,sc.render.fps_base=fps
    objs={o.name.split('.')[0]:o for o in bpy.data.objects if o not in before}
    for o in objs.values():
        if o.parent is None:
            o.scale=(SCALE,)*3;o.rotation_euler=(0,0,math.pi);o.location=(0,-ROCK_STAND,0)
        if o.type=='MESH':
            me=o.data;col=me.color_attributes.get('Col')
            if col:me.color_attributes.active_color=col;me.color_attributes.render_color_index=0
            for p in me.polygons:p.use_smooth=False
    bpy.context.view_layer.update()
    return objs


CANNON_FBX=ROOT/'crew-meshy-v15/anims/env/cannon.fbx'   # Astra's naval deck cannon (art-staging/cannon-astra-v1)
GUN_AT=(-.75,-.80,0.)          # the gun's origin at his 1.30 m scale: on his right and ahead, he beside its back end (inboard), clear of the wheels and the recoil
GUN_ELEV=4                     # barrel elevation, degrees (the model's default)
GUN_RECOIL=.55*SCALE           # Cannon.recoilDistance (0.55 m game): run in, the muzzle is this far further back


def load_cannon():
    """Astra's cannon at his scale, muzzle toward -Y (his forward), its origin
    at GUN_AT: he stands beside its back end with the gun on his right (where
    he can stand on a ship's deck, the muzzle out over the rail), the barrel
    laid at GUN_ELEV degrees.
    Returns ({name: object}, [parts his body must stay out of])."""
    before=set(bpy.data.objects);sc=bpy.context.scene;fps=(sc.render.fps,sc.render.fps_base)
    bpy.ops.import_scene.fbx(filepath=str(CANNON_FBX))
    sc.render.fps,sc.render.fps_base=fps
    objs={o.name:o for o in bpy.data.objects if o not in before}
    for o in objs.values():
        if o.parent is None:o.scale=(SCALE,)*3;o.location=GUN_AT
        if o.name.split('.')[0]=='Elevation_Pivot':o.rotation_euler.x-=math.radians(GUN_ELEV-4)   # muzzle up
        if o.type=='MESH':
            me=o.data;col=me.color_attributes.get('Col')
            if col:me.color_attributes.active_color=col;me.color_attributes.render_color_index=0
            for p in me.polygons:p.use_smooth=False
    bpy.context.view_layer.update()
    solid=[o for n,o in objs.items() if o.type=='MESH' and n.split('.')[0] in('Barrel','Carriage_Cheek_-1','Carriage_Cheek_1','Truck_Wheel','Trunnion','Bearing_Cap_-1','Bearing_Cap_1','Quoin_Handle','Elevation_Quoin','Carriage_Bed')]
    for o in solid:o['exact']=True                 # checked against their real surfaces (the anatomy checker)
    return objs,solid


FARM_FBX=ROOT/'crew-meshy-v15/anims/env/farm.fbx'   # Astra's level 1 farm (art-staging/farm-astra-lvl1-v1, farm-state-kit)
FARM_EDGE=.42                  # the front edge of the bed he works (Bed_02, front row centre) this far ahead of him, at his scale


def load_farm():
    """Astra's level 1 farm at his scale, turned so the front row's centre
    bed (Bed_02) lies ahead of him (-Y), its front edge FARM_EDGE away. The
    bed he works is bare (just turned soil); the other beds show sprouts.
    Returns ({name: object}, [parts his body must stay out of])."""
    before=set(bpy.data.objects);sc=bpy.context.scene;fps=(sc.render.fps,sc.render.fps_base)
    bpy.ops.import_scene.fbx(filepath=str(FARM_FBX))
    sc.render.fps,sc.render.fps_base=fps
    objs={o.name:o for o in bpy.data.objects if o not in before}
    for o in objs.values():
        n=o.name.split('.')[0]
        if o.parent is None:o.scale=(SCALE,)*3;o.rotation_euler=(0,0,math.pi);o.location=(0,-FARM_EDGE-1.72*SCALE,0)
        if ('_Growing' in n or '_Ripe' in n or 'Harvest_Sheaf' in n or n=='Bed_02_Sprout'):o.hide_render=o.hide_viewport=True;o['hidden_env']=True
        if o.type=='MESH':
            me=o.data;col=me.color_attributes.get('Col')
            if col:me.color_attributes.active_color=col;me.color_attributes.render_color_index=0
            for p in me.polygons:p.use_smooth=False
    bpy.context.view_layer.update()
    solid=[o for n,o in objs.items() if o.type=='MESH' and n.split('.')[0] in('Bed_01_Soil','Bed_02_Soil','Bed_03_Soil')]
    for o in solid:o['exact']=True
    return objs,solid


def load_env(kind):
    """(objects, where he stands, props his body must stay out of)."""
    if kind=='mill':
        objs=load('cutting');return objs,marker(objs,'Worker_Stand'),[objs['Bench_Cutting']]
    if kind=='tree':
        from mathutils import Vector
        objs=load_tree();return objs,Vector((0,0,0)),[]
    if kind=='cannon':
        from mathutils import Vector
        objs,solid=load_cannon();return objs,Vector((0,0,0)),solid
    if kind=='rock':
        from mathutils import Vector
        objs=load_rock();return objs,Vector((0,0,0)),[]
    if kind=='farm':
        from mathutils import Vector
        objs,solid=load_farm();return objs,Vector((0,0,0)),solid
    raise ValueError(kind)
