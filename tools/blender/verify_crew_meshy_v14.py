"""Independent rigged-FBX round trip: geometry, skin data and deformation.

Also checks the runtime contract shared with the in-game v5 deckhand: the
same 16 bone names, and the two mesh names CREW_Cloth / CREW_Skin.
"""
import json
from pathlib import Path
import bpy

OUT=Path(__file__).resolve().parents[2]/'crew-meshy-v14'
V5_BONES={'root','pelvis','spine','head'}|{b+s for b in ['upper_arm','forearm','hand',
          'thigh','shin','foot'] for s in ['.L','.R']}
expected=json.loads((OUT/'validation.json').read_text())['triangles']
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.import_scene.fbx(filepath=str(OUT/'deckhand-rigged.fbx'))
rigs=[o for o in bpy.data.objects if o.type=='ARMATURE']
meshes=[o for o in bpy.data.objects if o.type=='MESH']
assert len(rigs)==1 and len(meshes)==2
rig=rigs[0];assert {b.name for b in rig.data.bones}==V5_BONES
assert {o.name for o in meshes}=={'CREW_Cloth','CREW_Skin'},[o.name for o in meshes]
triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes)
assert triangles==expected,(triangles,expected)
for o in meshes:
    assert 'Col' in o.data.color_attributes
    assert not any(p.use_smooth for p in o.data.polygons)
    assert any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)
    for v in o.data.vertices:
        assert abs(sum(g.weight for g in v.groups)-1)<1e-4
        assert all(o.vertex_groups[g.group].name in rig.data.bones for g in v.groups)
    if 'Skin' in o.name:
        assert all(min(c.color[:3])>.99 for c in o.data.color_attributes['Col'].data)
def positions():
    graph=bpy.context.evaluated_depsgraph_get()
    return [(o.evaluated_get(graph).matrix_world@v.co).copy()
            for o in meshes for v in o.evaluated_get(graph).data.vertices]
before=positions()
pb=rig.pose.bones['forearm.R'];pb.rotation_mode='XYZ';pb.rotation_euler.x=.5
bpy.context.view_layer.update();after=positions()
motion=max((a-b).length for a,b in zip(after,before))
assert motion>.01,motion
height=max(p.z for p in before)-min(p.z for p in before)
report={'meshes':sorted(o.name for o in meshes),'bones':len(rig.data.bones),
        'bone_names_match_v5':True,'triangles':triangles,'height_m':round(height,3),
        'vertex_colors':True,'normalized_weights':True,'neutral_skin_shade':True,
        'imported_rig_deformation_max_displacement':motion}
(OUT/'export-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
