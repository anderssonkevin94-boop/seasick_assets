"""The level 2 sawmill concept at work: the deckhand's Crank clip with the
crank and saw wheels turning in step, the whole building from the game
camera's height (front, the open gable). Writes
sawmill-l2-concept/l2-crank.gif and l2-crank-closeup.gif.

Usage: python render_l2_crank_gif.py
"""
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_meshy_v15_anims as A, crew_v15_mill as MILL
from render_v15_anims import save_gif
from PIL import Image

OUT=A.ROOT/'sawmill-l2-concept'


def main():
    bpy.ops.wm.open_mainfile(filepath=str(A.ROOT/'tools/blender/source/crew-meshy-v15-anims.blend'))
    sc=bpy.context.scene;sc.render.fps=A.FPS
    rig=bpy.data.objects['Deckhand_Rig']
    sc.render.engine='BLENDER_WORKBENCH';sc.view_settings.view_transform='Standard'
    sh=sc.display.shading;sh.light='STUDIO';sh.color_type='VERTEX';sh.show_cavity=True;sh.cavity_type='WORLD'
    sh.show_shadows=True;sh.shadow_intensity=.35;sh.background_type='VIEWPORT';sh.background_color=(.16,.17,.19)
    env,stand,_=MILL.load_env('mill2');rig.location=stand
    act=bpy.data.actions['Crew_Crank'];rig.animation_data.action=act
    cd=bpy.data.cameras.new('c');cam=bpy.data.objects.new('c',cd);sc.collection.objects.link(cam);sc.camera=cam;cd.type='ORTHO'
    tmp=OUT/'_frames';tmp.mkdir(exist_ok=True)
    n=int(act.frame_end)
    shots=[('l2-crank.gif',-12,26,7.0,Vector((0,0,1.2)),(900,700),()),
           ('l2-crank-closeup.gif',-28,20,2.3,stand+Vector((.4,-.1,.7)),(760,680),MILL.SHED2+('Input_','Mill_InputCradle'))]
    for name,az,el,scale,tgt,res,hide in shots:
        for o in env.values():o.hide_render=o.name.startswith(hide) if hide else False
        for o in env.values():
            if o.name.startswith(('Input_Log','Output_Plank')) and int(o.name.split('.')[0][-2:])>(6 if 'Input' in o.name else 12):o.hide_render=True
        d=Vector((math.sin(math.radians(az))*math.cos(math.radians(el)),-math.cos(math.radians(az))*math.cos(math.radians(el)),math.sin(math.radians(el))))
        cam.location=tgt+d*30;cam.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=scale*MILL.SCALE if scale>3 else scale
        sc.render.resolution_x,sc.render.resolution_y=res
        frames=[]
        for f in range(0,n,2):
            sc.frame_set(f);sc.render.filepath=str(tmp/f'{f:03d}.png');bpy.ops.render.render(write_still=True)
            frames.append(Image.open(sc.render.filepath).convert('RGB'))
        save_gif(frames,OUT/name,int(2000/A.FPS));print('wrote',name,len(frames))
    for p in tmp.glob('*.png'):p.unlink()
    tmp.rmdir()


if __name__=='__main__':
    main()
