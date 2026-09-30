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
FBX=ROOT/'crew-meshy-v15/anims/env/lumber-mill-state-kit.fbx'
SCALE=1.30/1.7
TEXTURE_MEAN={'SS_LumberL1_Wood':(140,88,31),'SS_LumberL1_Hemp':(157,120,68)}   # wood-tile-512, rope-tile-512


def _lin(c):return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4



def load(state='cutting',logs=3,planks=3):
    """Import the mill, scaled, and show one bench state ('empty', 'loaded',
    'cutting', 'finished') plus the first `logs` input logs and `planks`
    output planks. Returns {name: object}."""
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    objs={o.name:o for o in bpy.data.objects if o not in before}
    objs['LumberMill_C_Level_1'].scale=(SCALE,)*3
    for o in objs.values():
        n=o.name
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
            me.color_attributes.active_color=col
            for p in me.polygons:p.use_smooth=False
    bpy.context.view_layer.update()
    return objs


def marker(objs,name):
    return objs[name].matrix_world.translation.copy()
