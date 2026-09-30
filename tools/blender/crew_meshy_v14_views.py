"""Colour review for crew-meshy-v14: front, back, both sides, three-quarter
and a face close-up, flat vertex colours (Workbench)."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_meshy_v14 as M
bpy.ops.wm.open_mainfile(filepath=str(M.ROOT/'tools/blender/source/crew-meshy-v14.blend'))
sc=bpy.context.scene;rig=bpy.data.objects['Deckhand_Rig'];M.pose(rig,'rest')
sc.render.engine='BLENDER_WORKBENCH'
sh=sc.display.shading;sh.light='STUDIO';sh.color_type='VERTEX';sh.background_type='VIEWPORT'
sh.background_color=(.37,.55,.68);sh.show_cavity=False
sc.view_settings.view_transform='Standard'
cd=bpy.data.cameras.new('c');cam=bpy.data.objects.new('c',cd);sc.collection.objects.link(cam);sc.camera=cam;cd.type='ORTHO'
for name,eye,tgt,scale,size in [('view-front',(0,-5,.65),(0,0,.65),1.45,(560,640)),('view-back',(0,5,.65),(0,0,.65),1.45,(560,640)),
    ('view-left',(5,0,.65),(0,0,.65),1.45,(560,640)),('view-right',(-5,0,.65),(0,0,.65),1.45,(560,640)),
    ('view-q34',(2.6,-3.6,1.5),(0,0,.62),1.5,(900,1000)),('view-face',(1.1,-3.4,1.25),(0,0,.95),.6,(800,800))]:
    cd.ortho_scale=scale;sc.render.resolution_x,sc.render.resolution_y=size
    cam.location=eye;cam.rotation_euler=(Vector(tgt)-Vector(eye)).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=str(M.OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
