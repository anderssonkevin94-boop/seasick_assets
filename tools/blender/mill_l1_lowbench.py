"""Level 1 lumber mill with the bench lowered for the v15 deckhand.

Kevin, 2026-09-30: the game's bench top is 1.33 m (1.17 m above the work
platform), above the v15 deckhand's shoulders once he is scaled to 1.7 m, so
he cannot work at it. Lower the bench to his hip, and remove the mallet and
the wedge that float over the log ("they shouldn't be part of the structure").

From the game's `lumber-mill-state-kit.fbx` (copy in
crew-meshy-v15/anims/env/) this makes `lumber-mill-state-kit-lowbench.fbx`:
  - Mill_Workbench: the top and everything near it moves down rigidly by
    DROP; the legs below shorten to meet it (nothing else is reshaped).
  - Bench_Loaded, Bench_Cutting, Bench_Result_01..03 move down by DROP
    (their Bench_Anchor / Bench_Finished parents stay where MillL1Import
    checks them).
  - Bench_Cutting loses its wedge: only the log piece is kept.
  - Mallet_Tool keeps its name (MillL1Import requires it) as an empty with
    no geometry.
Every other object, name, parent, marker, material and GameColor layer is
unchanged; the script re-imports its own export and checks that against the
original. Game-scale metres, Blender Z up, front -Y.
"""
import json
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
ENV=ROOT/'crew-meshy-v15/anims/env'
SRC=ENV/'lumber-mill-state-kit.fbx'
OUT=ENV/'lumber-mill-state-kit-lowbench.fbx'
PLATFORM=.16            # Worker_Stand height: the work platform's top
BENCH_TOP=.78           # new bench top (game metres): 0.62 m above the platform, his hip at 1.7 m
TOP_BAND=.30            # the bench's top structure: this much below the old top moves rigidly


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    return {o.name.split('.')[0]:o for o in bpy.data.objects}


def world_box(o):
    pts=[o.matrix_world@v.co for v in o.data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])


def snapshot(objs):
    snap={}
    for n,o in objs.items():
        e={'type':o.type,'parent':o.parent.name.split('.')[0] if o.parent else None,
           'at':[round(x,3) for x in o.matrix_world.translation]}
        if o.type=='MESH' and o.data.vertices:
            lo,hi=world_box(o);e['box']=[round(x,3) for x in (*lo,*hi)]
            e['tris']=sum(len(p.vertices)-2 for p in o.data.polygons)
            e['colours']=[a.name for a in o.data.color_attributes]
            e['materials']=[m.name.split('.')[0] for m in o.data.materials if m]
        snap[n]=e
    return snap


def main():
    objs=load(SRC);before=snapshot(objs)
    wb=objs['Mill_Workbench'];old_top=world_box(wb)[1].z;drop=old_top-BENCH_TOP
    band=old_top-TOP_BAND
    k=(band-drop-PLATFORM)/(band-PLATFORM)     # leg squash below the band
    inv=wb.matrix_world.inverted()
    for v in wb.data.vertices:
        w=wb.matrix_world@v.co
        if w.z>=band:w.z-=drop
        elif w.z>PLATFORM:w.z=PLATFORM+(w.z-PLATFORM)*k
        v.co=inv@w
    wb.data.update()
    for n in('Bench_Loaded','Bench_Cutting','Bench_Result_01','Bench_Result_02','Bench_Result_03'):
        o=objs[n];m=o.matrix_world.copy();m.translation.z-=drop;o.matrix_world=m
    bpy.context.view_layer.update()
    # Bench_Cutting: keep the log (its biggest loose piece), drop the wedge
    cut=objs['Bench_Cutting'];bm=bmesh.new();bm.from_mesh(cut.data)
    seen=set();parts=[]
    for f in bm.faces:
        if f in seen:continue
        stack=[f];comp=[]
        while stack:
            g=stack.pop()
            if g in seen:continue
            seen.add(g);comp.append(g);stack+=[h for e in g.edges for h in e.link_faces if h not in seen]
        parts.append(comp)
    parts.sort(key=lambda c:-sum(g.calc_area() for g in c))
    wedge=[f for c in parts[1:] for f in c]
    bmesh.ops.delete(bm,geom=wedge,context='FACES');bm.to_mesh(cut.data);bm.free()
    # Mallet_Tool: an empty with the same name, parent and place
    mal=objs['Mallet_Tool'];name,parent,mw=mal.name,mal.parent,mal.matrix_world.copy()
    kids=list(mal.children)
    bpy.data.objects.remove(mal,do_unlink=True)
    e=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(e)
    e.parent=parent;e.matrix_world=mw
    for c in kids:c.parent=e
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(OUT),use_selection=False,object_types={'EMPTY','MESH'},
        axis_forward='-Z',axis_up='Y',use_triangles=False,mesh_smooth_type='FACE',colors_type='SRGB',
        add_leaf_bones=False,bake_anim=False)
    # Re-import and compare with the original.
    after=snapshot(load(OUT))
    changed={'Mill_Workbench','Bench_Loaded','Bench_Cutting','Bench_Result_01','Bench_Result_02','Bench_Result_03','Mallet_Tool'}
    problems=[]
    if set(before)!=set(after):problems.append(('names',sorted(set(before)^set(after))))
    for n,b in before.items():
        a=after.get(n)
        if a is None:continue
        if n in changed:
            if a['parent']!=b['parent']:problems.append((n,'parent'))
            continue
        for key in('type','parent','at','box','tris','colours','materials'):
            if b.get(key)!=a.get(key) and not (key=='at' and all(abs(x-y)<.002 for x,y in zip(a['at'],b['at']))) \
               and not (key=='box' and all(abs(x-y)<.002 for x,y in zip(a.get('box',[]),b.get('box',[])))):
                problems.append((n,key,b.get(key),a.get(key)))
    report={'old_bench_top':round(old_top,3),'new_bench_top':round(world_box(bpy.data.objects['Mill_Workbench'])[1].z,3) if 'Mill_Workbench' in bpy.data.objects else None,
            'drop':round(drop,3),'bench_cutting_tris':after['Bench_Cutting']['tris'],'mallet':after['Mallet_Tool']['type'],
            'unchanged_objects_match_original':not problems,'problems':problems[:10]}
    (ENV/'lowbench-verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    assert not problems,problems


if __name__=='__main__':
    main()
