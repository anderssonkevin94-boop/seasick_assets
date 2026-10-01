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


# ---------------------------------------------------------------- the level 2 concept
L2_FBX=ROOT/'sawmill-l2-concept/sawmill-l2-concept.fbx'   # sawmill_l2_concept.py; carries the wheels' 'Mill2_Crank' take


SHED2=('Mill2_BoardRoof','Mill2_BackWall','Mill2_ToolRail','Mill2_Frame','Mill2_Piers','Mill2_OutputCanvas',
       'Mill2_SignPost','Mill2_LevelPlate','Mill_Trade')   # left out of close work previews


def load_l2():
    """The level 2 sawmill concept at his scale, the crank and saw wheels
    animated in step with the Crank clip. Returns {name: object}."""
    before=set(bpy.data.objects);sc=bpy.context.scene;fps=(sc.render.fps,sc.render.fps_base)
    bpy.ops.import_scene.fbx(filepath=str(L2_FBX))
    sc.render.fps,sc.render.fps_base=fps
    objs={o.name.split('.')[0]:o for o in bpy.data.objects if o not in before}
    for o in objs.values():                       # the FBX keys every object; only the wheels move
        if o.animation_data and o.name.split('.')[0] not in('Mill2_CrankWheel','Saw2_Wheel'):o.animation_data_clear()
    objs['LumberMill_C_Level_2'].scale=(SCALE,)*3
    for o in objs.values():
        if o.type=='MESH':
            me=o.data;col=me.color_attributes.get('Col')
            if col:me.color_attributes.active_color=col;me.color_attributes.render_color_index=0
            for p in me.polygons:p.use_smooth=False
    bpy.context.view_layer.update()
    return objs


L1M_FBX=ROOT/'mill-l1-concept/mill-lvl1.fbx'   # mill_l1_concept.py; carries the quern's 'Mill1_Grind' take


def load_l1mill():
    """The level 1 mill concept at his scale, the quern's runner turning in
    step with the Crew_Mill clip. Returns {name: object}."""
    before=set(bpy.data.objects);sc=bpy.context.scene;fps=(sc.render.fps,sc.render.fps_base)
    bpy.ops.import_scene.fbx(filepath=str(L1M_FBX))
    sc.render.fps,sc.render.fps_base=fps
    objs={o.name.split('.')[0]:o for o in bpy.data.objects if o not in before}
    for o in objs.values():                       # the FBX keys every object; only the runner moves
        if o.animation_data and o.name.split('.')[0]!='Quern_Runner':o.animation_data_clear()
    objs['Mill_Level_1'].scale=(SCALE,)*3
    for o in objs.values():
        if o.type=='MESH':
            me=o.data;col=me.color_attributes.get('Col')
            if col:me.color_attributes.active_color=col;me.color_attributes.render_color_index=0
            for p in me.polygons:p.use_smooth=False
    bpy.context.view_layer.update()
    return objs


def load_env(kind):
    """(objects, where he stands, props his body must stay out of)."""
    if kind=='mill':
        objs=load('cutting');return objs,marker(objs,'Worker_Stand'),[objs['Bench_Cutting']]
    if kind=='mill1':
        objs=load_l1mill();return objs,marker(objs,'Worker_Stand'),[]      # the quern is checked as an env tool (exact mesh)
    if kind=='mill2':
        objs=load_l2();return objs,marker(objs,'Worker_Stand'),[objs['Mill2_SawTable'],objs['Bench2_Cutting']]
    if kind=='tree':
        from mathutils import Vector
        objs=load_tree();return objs,Vector((0,0,0)),[]
    raise ValueError(kind)
