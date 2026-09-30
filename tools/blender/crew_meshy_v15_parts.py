"""Split the rigged v15 character into separate, named body-part objects, for
custom versions later (swap a head, recolour a sash, drop the wrist wraps).

Meshy built him from 40 loose pieces in one mesh. This separates them and
groups them into parts. The pieces that span a joint are cut first and each
cut is capped: the arm tubes at the elbow, the shorts down the middle and
each shin-and-foot piece at the ankle. Every vertex is weighted from its
position (the same rules as crew_meshy_v15_pose.py), so the two sides of a
cut get identical weights and stay together when he bends.

Object names use the skeleton's side suffixes (.R is +X, as for the bones).
Outputs crew-meshy-v15/parts/: deckhand-v15-parts.fbx (rigged, T-pose rest,
preview colours), part renders; and tools/blender/source/crew-meshy-v15-parts.blend
(T-pose rest with the idle pose applied).
"""
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_meshy_v15_colour as C
import crew_meshy_v15_pose as P
from crew_meshy_v14 import side_name

ROOT=C.ROOT;OUT=C.OUT/'parts';K=P.K
ELBOW_X,ANKLE_Z=.25,.06          # Meshy units: the bone joints

HEAD={'head','ear','nose','eye','brow','plate-head'}


def part_name(label,c):
    """c: centre of the piece (or cut half) in Meshy units."""
    s=1 if c.x>0 else -1
    side=lambda base:base+('.R' if s>0 else '.L')
    if label in HEAD:return 'Head'
    if label in('hair','tuft'):return 'Hair'
    if label.startswith('headband'):return 'Headband'
    if label in('tunic','plate-body'):return 'Torso'
    if label in('sash','sash knot','sash tail'):return 'Sash'
    if label=='sleeve':return side('Sleeve')
    if label=='arm':return side('UpperArm') if abs(c.x)<ELBOW_X else side('Forearm')
    if label=='wrist wrap':return side('WristWrap')
    if label=='hand':return side('Hand')
    if label in('shorts','shorts patch','shorts cuff'):return side('Shorts')
    if label=='foot':return side('Shin') if c.z>ANKLE_Z else side('Foot')
    if label in('sole','sandal strap'):return side('Foot')
    raise ValueError(label)


def bbox(o):
    pts=[v.co/K for v in o.data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])


def cut(o,co,no):
    """Split object o by a plane into two capped halves; returns both."""
    halves=[]
    for keep_outer in (False,True):
        h=o.copy();h.data=o.data.copy();bpy.context.scene.collection.objects.link(h)
        bm=bmesh.new();bm.from_mesh(h.data)
        col=bm.loops.layers.color.get('Col')
        bm.faces.ensure_lookup_table()
        sample=bm.faces[0].loops[0][col].copy() if col else None
        bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],plane_co=Vector(co)*K,plane_no=Vector(no),
                               clear_inner=keep_outer,clear_outer=not keep_outer)
        edges=[e for e in bm.edges if e.is_boundary]
        new=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']
        caps=bmesh.ops.triangulate(bm,faces=new)['faces']
        for f in bm.faces:f.smooth=False
        if col:
            for f in caps:                                  # cap faces: the piece's own colour
                for l in f.loops:l[col]=sample
        bm.normal_update();bm.to_mesh(h.data);bm.free()
        if h.data.polygons:halves.append(h)
        else:bpy.data.objects.remove(h,do_unlink=True)
    bpy.data.objects.remove(o,do_unlink=True)
    return halves


def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tools/blender/source/crew-meshy-v15.blend'))
    body=bpy.data.objects['Deckhand_v15']
    P.close_fists(body)
    for o in list(bpy.data.objects):
        if o!=body:bpy.data.objects.remove(o,do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE');bpy.ops.object.mode_set(mode='OBJECT')

    # Label each loose piece, then cut the ones that span a joint.
    work=[]
    for o in [o for o in bpy.data.objects if o.type=='MESH']:
        lo,hi=bbox(o);_,label=C.classify(lo,hi,len(o.data.polygons))
        if label=='?':label='plate-head' if lo.z>.58 else 'plate-body'   # mouth; tunic planks
        if label=='arm':
            s=1 if lo.x+hi.x>0 else -1
            work+=[(h,label) for h in cut(o,(s*ELBOW_X,0,0),(1,0,0))]
        elif label=='shorts':work+=[(h,label) for h in cut(o,(0,0,0),(1,0,0))]
        elif label=='foot':work+=[(h,label) for h in cut(o,(0,0,ANKLE_Z),(0,0,1))]
        else:work.append((o,label))

    # Weights per vertex, from position, then join into named parts.
    groups={}
    for o,label in work:
        o.vertex_groups.clear()
        vg={n:o.vertex_groups.new(name=n) for n in P.REST}
        for v in o.data.vertices:
            for n,w in P.weights_for(label,v.co/K).items():
                if w>1e-4:vg[n].add([v.index],w,'REPLACE')
        lo,hi=bbox(o);groups.setdefault(part_name(label,(lo+hi)/2),[]).append(o)
    parts=[]
    for name,objs in sorted(groups.items()):
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:o.select_set(True)
        bpy.context.view_layer.objects.active=objs[0]
        if len(objs)>1:bpy.ops.object.join()
        o=bpy.context.view_layer.objects.active;o.name=name;o.data.name=name
        for g in [g for g in o.vertex_groups]:                 # drop empty groups
            if not any(g.index in [x.group for x in v.groups] for v in o.data.vertices):o.vertex_groups.remove(g)
        o['part']=name;parts.append(o)

    # Rig: same skeleton as the one-mesh version.
    data=bpy.data.armatures.new('DeckhandSkeleton')
    rig=bpy.data.objects.new('Deckhand_Rig',data);bpy.context.scene.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT');bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for n,(a,b,parent) in P.REST.items():
        e=data.edit_bones.new(n);e.head=a;e.tail=b;e.use_deform=True
        if parent:e.parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in parts:
        o.parent=rig;m=o.modifiers.new('Armature','ARMATURE');m.object=rig

    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/'deckhand-v15-parts.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},
        axis_forward='-Z',axis_up='Y',add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,
        use_triangles=True,colors_type='SRGB',mesh_smooth_type='FACE')
    tris={o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in parts}
    report={'parts':len(parts),'triangles':sum(tris.values()),'per_part':tris}
    import json;(OUT/'parts.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    P.idle(rig)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'tools/blender/source/crew-meshy-v15-parts.blend'))


if __name__=='__main__':
    main()
