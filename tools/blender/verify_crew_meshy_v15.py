"""Independent FBX round trip for the v15 game files: the drop-in
`deckhand-v15-rigged.fbx` and the clip library `anims/deckhand-v15-anims.fbx`.

Checks the runtime contract shared with the in-game v5 deckhand: the same 16
bone names, the two meshes CREW_Cloth / CREW_Skin, vertex colours, flat
shading, white skin, weights that sum to 1, and a rig that moves the mesh.
For the clip library it also checks every take is there and moves.
"""
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'crew-meshy-v15'
V5_BONES={'root','pelvis','spine','head'}|{b+s for b in ['upper_arm','forearm','hand',
          'thigh','shin','foot'] for s in ['.L','.R']}
EXPECTED=json.loads((OUT/'rigged.json').read_text())['triangles']


def check(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    rigs=[o for o in bpy.data.objects if o.type=='ARMATURE'];meshes=[o for o in bpy.data.objects if o.type=='MESH']
    assert len(rigs)==1 and len(meshes)==2,(rigs,meshes)
    rig=rigs[0];assert {b.name for b in rig.data.bones}==V5_BONES
    assert {o.name for o in meshes}=={'CREW_Cloth','CREW_Skin'},[o.name for o in meshes]
    tris={o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes}
    assert sum(tris.values())==EXPECTED,(tris,EXPECTED)
    influences=0
    for o in meshes:
        assert 'Col' in o.data.color_attributes and not any(p.use_smooth for p in o.data.polygons)
        assert any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)
        for v in o.data.vertices:
            ws=[g.weight for g in v.groups if g.weight>1e-5];influences=max(influences,len(ws))
            assert abs(sum(ws)-1)<1e-4
        if o.name=='CREW_Skin':
            assert all(min(c.color[:3])>.99 for c in o.data.color_attributes['Col'].data)
        else:
            assert any(min(c.color[:3])<.9 for c in o.data.color_attributes['Col'].data)
    graph=lambda:bpy.context.evaluated_depsgraph_get()
    def positions():
        g=graph();return [(o.evaluated_get(g).matrix_world@v.co).copy() for o in meshes for v in o.evaluated_get(g).data.vertices]
    if rig.animation_data:rig.animation_data.action=None
    for pb in rig.pose.bones:pb.matrix_basis.identity()
    bpy.context.view_layer.update();before=positions()
    height=max(p.z for p in before)-min(p.z for p in before)
    pb=rig.pose.bones['forearm.R'];pb.rotation_mode='XYZ';pb.rotation_euler.x=.5
    bpy.context.view_layer.update();motion=max((a-b).length for a,b in zip(positions(),before))
    assert motion>.01,motion
    report={'file':str(path.relative_to(ROOT)),'meshes':tris,'bones':len(rig.data.bones),'bone_names_match_v5':True,
            'triangles':sum(tris.values()),'height_m':round(height,3),'vertex_colours':True,'flat':True,
            'white_skin':True,'weights_sum_to_1':True,'max_influences':influences,'rig_moves_mesh':round(motion,3)}
    takes=[a for a in bpy.data.actions]
    if takes:
        pb.rotation_euler.x=0;moving=0
        for a in takes:
            rig.animation_data.action=a;f0,f1=a.frame_range
            bpy.context.scene.frame_set(int(f0));p0=[b.matrix.copy() for b in rig.pose.bones]
            far=0.
            for k in range(1,6):                         # several frames: some loops pass their start again mid-way
                bpy.context.scene.frame_set(int(f0+(f1-f0)*k/6))
                far=max(far,max((x.translation-b.matrix.translation).length for x,b in zip(p0,rig.pose.bones)))
            if far>.01:moving+=1
        report['takes']=sorted(a.name.split('|')[-1] for a in takes);report['takes_that_move']=moving
        assert moving==len(takes)
    return report


reports=[check(OUT/'deckhand-v15-rigged.fbx'),check(OUT/'anims/deckhand-v15-anims.fbx')]
(OUT/'export-verification.json').write_text(json.dumps(reports,indent=2))
print(json.dumps(reports,indent=2))
