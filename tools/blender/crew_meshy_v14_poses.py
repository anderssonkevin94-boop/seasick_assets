"""Deformation review for crew-meshy-v14: rest, walk, work and crouch poses,
rendered flat-shaded from three-quarter front and side."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_meshy_v14 as M
bpy.ops.wm.open_mainfile(filepath=str(M.ROOT/'tools/blender/source/crew-meshy-v14.blend'))
sc=bpy.context.scene;rig=bpy.data.objects['Deckhand_Rig']
sc.render.engine='BLENDER_WORKBENCH'
sh=sc.display.shading;sh.light='STUDIO';sh.color_type=('VERTEX' if len(sys.argv)>1 and sys.argv[-1]=='color' else 'SINGLE')
sh.single_color=(.8,.72,.62);sh.background_type='VIEWPORT';sh.background_color=(.37,.55,.68);sh.show_cavity=False
cd=bpy.data.cameras.new('c');cam=bpy.data.objects.new('c',cd);sc.collection.objects.link(cam);sc.camera=cam
cd.type='ORTHO';cd.ortho_scale=1.55;sc.render.resolution_x,sc.render.resolution_y=560,640
for kind in ['rest','walk','work','reach','crouch']:
    M.pose(rig,kind)
    for view,eye in [('q34',(2.6,-3.6,1.5)),('side',(5,-.2,.65))]:
        cam.location=eye;cam.rotation_euler=(Vector((0,0,.62))-Vector(eye)).to_track_quat('-Z','Y').to_euler()
        sc.render.filepath=str(M.OUT/f'pose-{kind}-{view}.png');bpy.ops.render.render(write_still=True)
