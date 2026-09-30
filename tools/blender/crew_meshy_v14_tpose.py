"""T-pose versions of the Meshy character v14.

  crew-meshy-v14/tpose/deckhand-tpose-rigged.fbx : same skeleton and weights,
      re-bound so the T-pose is the rest pose (for retargeting: Mixamo,
      Unity Humanoid, other animation libraries).
  crew-meshy-v14/tpose/deckhand-tpose-mesh.fbx   : the mesh alone, standing in
      a T (for auto-riggers such as Mixamo, which want an unrigged mesh).
The game FBX (crew-meshy-v14/deckhand-rigged.fbx) is unchanged: the game's
generated clips are built relative to its current rest pose.
"""
import sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_meshy_v14 as M

OUT=M.OUT/'tpose'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(M.ROOT/'tools/blender/source/crew-meshy-v14.blend'))
rig=bpy.data.objects['Deckhand_Rig'];meshes=[o for o in rig.children if o.type=='MESH']


def aim(name,head,direction):
    bone=rig.data.bones[name];length=bone.length
    delta=(bone.tail_local-bone.head_local).rotation_difference(Vector(direction).normalized())
    m=delta.to_matrix().to_4x4()@bone.matrix_local.to_quaternion().to_matrix().to_4x4()
    m.translation=Vector(head);rig.pose.bones[name].matrix=m
    bpy.context.view_layer.update()
    return Vector(head)+Vector(direction).normalized()*length


for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
for s in [-1,1]:
    u,f,h=M.side_name('upper_arm',s),M.side_name('forearm',s),M.side_name('hand',s)
    e=aim(u,M.REST[u][0],(s,0,0));w=aim(f,e,(s,0,0));aim(h,w,(s,0,0))   # arms straight out
    t,sh,ft=M.side_name('thigh',s),M.side_name('shin',s),M.side_name('foot',s)
    k=aim(t,M.REST[t][0],(0,0,-1));a=aim(sh,k,(0,0,-1));aim(ft,a,(0,-.95,-.3))  # legs straight
bpy.context.view_layer.update()

# Bake the deformation into the meshes, then make this pose the rest pose.
for o in meshes:
    mod=[m for m in o.modifiers if m.type=='ARMATURE'][0]
    with bpy.context.temp_override(object=o,active_object=o,selected_objects=[o],selected_editable_objects=[o]):
        bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.context.view_layer.objects.active=rig;bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
bpy.ops.object.mode_set(mode='POSE');bpy.ops.pose.armature_apply(selected=False);bpy.ops.object.mode_set(mode='OBJECT')
for o in meshes:
    mod=o.modifiers.new('Armature','ARMATURE');mod.object=rig
low=min((o.matrix_world@v.co).z for o in meshes for v in o.data.vertices)
rig.location.z-=low;bpy.context.view_layer.update()


def export(path,objs,types):
    skin=bpy.data.objects['CREW_Skin'];col=skin.data.color_attributes['Col']
    keep=[tuple(c.color) for c in col.data]
    for c in col.data:c.color=(1,1,1,1)       # skin exported white, as in the game FBX
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types=types,
        axis_forward='-Z',axis_up='Y',add_leaf_bones=False,use_armature_deform_only=True,
        bake_anim=False,use_triangles=True,colors_type='LINEAR',mesh_smooth_type='FACE')
    for c,v in zip(col.data,keep):c.color=v


export(OUT/'deckhand-tpose-rigged.fbx',[rig]+meshes,{'ARMATURE','MESH'})
# Mesh only: a joined, unparented copy with no weights.
copies=[]
for o in meshes:
    c=o.copy();c.data=o.data.copy();bpy.context.scene.collection.objects.link(c)
    c.parent=None;c.matrix_world=o.matrix_world.copy();c.modifiers.clear();c.vertex_groups.clear();copies.append(c)
bpy.ops.object.select_all(action='DESELECT')
for c in copies:c.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();mesh_only=bpy.context.object;mesh_only.name='Deckhand_TPose'
# The mesh-only file keeps the preview skin colour (no tint system outside the game).
bpy.ops.object.select_all(action='DESELECT');mesh_only.select_set(True);bpy.context.view_layer.objects.active=mesh_only
bpy.ops.export_scene.fbx(filepath=str(OUT/'deckhand-tpose-mesh.fbx'),use_selection=True,object_types={'MESH'},
    axis_forward='-Z',axis_up='Y',use_triangles=True,colors_type='SRGB',mesh_smooth_type='FACE')
mesh_only.hide_render=True

# Review renders.
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH'
sh=sc.display.shading;sh.light='STUDIO';sh.color_type='VERTEX';sh.background_type='VIEWPORT'
sh.background_color=(.37,.55,.68);sh.show_cavity=False
cd=bpy.data.cameras.new('c');cam=bpy.data.objects.new('c',cd);sc.collection.objects.link(cam);sc.camera=cam;cd.type='ORTHO'
for name,eye,scale,size in [('tpose-front',(0,-5,.7),1.55,(1000,800)),('tpose-q34',(2.8,-3.8,1.6),1.7,(1000,900)),
                            ('tpose-back',(0,5,.7),1.55,(1000,800)),('tpose-armpit',(.9,-2.2,.95),.55,(800,800))]:
    cd.ortho_scale=scale;sc.render.resolution_x,sc.render.resolution_y=size
    tgt=(.35,0,.72) if name=='tpose-armpit' else (0,0,.66)
    cam.location=eye;cam.rotation_euler=(Vector(tgt)-Vector(eye)).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(M.ROOT/'tools/blender/source/crew-meshy-v14-tpose.blend'))
print('T-pose exported')
