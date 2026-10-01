"""Preview renders of the v15 task animations (crew_meshy_v15_anims.py):
for every clip an animated GIF and a six-frame filmstrip, with the clip's
preview props (log, anvil, pot...) and the tools in his hands. Workbench,
vertex colours, three-quarter view from his right (tool) side.

Usage: python render_v15_anims.py [-- Clip Clip ...]
"""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_meshy_v15_anims as A
from PIL import Image

OUT=A.OUT
ONLY=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []


def save_gif(frames,path,ms):
    """Small GIFs: one 64-colour palette for the whole clip, no dithering."""
    pal=frames[len(frames)//2].quantize(colors=64,dither=Image.Dither.NONE)
    q=[f.quantize(palette=pal,dither=Image.Dither.NONE) for f in frames]
    q[0].save(path,save_all=True,append_images=q[1:],duration=ms,loop=0,optimize=True)


def main():
    bpy.ops.wm.open_mainfile(filepath=str(A.ROOT/'tools/blender/source/crew-meshy-v15-anims.blend'))
    rig=bpy.data.objects['Deckhand_Rig'];solver=A.Solver(rig)
    sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.render.fps=A.FPS
    sc.render.film_transparent=False;sc.view_settings.view_transform='Standard';sc.view_settings.exposure=0
    sh=sc.display.shading;sh.light='STUDIO';sh.color_type='VERTEX';sh.background_type='VIEWPORT'
    sh.background_color=(.37,.55,.68);sh.show_cavity=True;sh.cavity_type='WORLD';sh.show_shadows=True
    sc.display.shadow_focus=.6
    if sc.world is None:sc.world=bpy.data.worlds.new('W')
    sc.world.color=(.37,.55,.68)
    ground=A.box_mesh('ground',[((8,8,.02),(0,-1.5,-.011),'soil')])
    ground.data.color_attributes['Col'].data.foreach_set('color',[v for _ in range(len(ground.data.loops)) for v in (*A.C.srgb('#7E9E62'),1)])
    cd=bpy.data.cameras.new('cam');cam=bpy.data.objects.new('cam',cd);sc.collection.objects.link(cam);sc.camera=cam
    cd.type='ORTHO';cd.ortho_scale=1.75
    eye=Vector((-1.9,-2.7,1.35));tgt=Vector((0,-.18,.56))
    cam.location=eye;cam.rotation_euler=(tgt-eye).to_track_quat('-Z','Y').to_euler()
    sc.render.resolution_x,sc.render.resolution_y=420,440
    tmp=OUT/'_frames';tmp.mkdir(parents=True,exist_ok=True)
    for name,c in A.CLIPS.items():
        if ONLY and name not in ONLY:continue
        act=bpy.data.actions['Crew_'+name];rig.animation_data.action=act
        cd.ortho_scale=1.75
        extra=[];stand=Vector((0,0,0))
        if c.get('env'):
            import crew_v15_mill as MILL
            env,stand,_=MILL.load_env(c['env']);rig.location=stand
            extra+=list(env.values());ground.hide_render=False
            view=Vector((-2.6,-4.2,3.0)) if c['env']=='mill' else Vector((-3.2,1.2,2.2))
            if c['env']=='tree':
                for o in env.values():
                    if 'Canopy' in o.name:o.hide_render=True     # the canopy would hide him from a game camera; left out of the preview
            cam.location=stand+view;cam.rotation_euler=(stand+Vector((0,-.3,.5))-cam.location).to_track_quat('-Z','Y').to_euler()
        elif c.get('throw'):                        # wide: him, the flight and the target
            rig.location=(0,0,0);e2=Vector((-3.6,.2,2.0));t2=Vector((0,-1.5,.5));cd.ortho_scale=3.6
            cam.location=e2;cam.rotation_euler=(t2-e2).to_track_quat('-Z','Y').to_euler()
        else:
            rig.location=(0,0,0);cam.location=eye;cam.rotation_euler=(tgt-eye).to_track_quat('-Z','Y').to_euler()
        bpy.context.view_layer.update()
        for pname,centre,size,colour,_ in c['props']:
            extra.append(A.box_mesh(pname,[(size,centre,colour)]))
        sc.frame_set(0)
        if c['rtool']:
            extra.append(A.attach_tool(rig,solver,c['rtool'],A.RIGHT))
            if A.flies(c):A.animate_load(extra[-1],rig,name)   # the tool leaves him (dropped, thrown)
        if c['ltool']:extra.append(A.attach_tool(rig,solver,c['ltool'],A.LEFT))
        n=int(act.frame_end);frames=[];step=2
        for f in range(0,n+(0 if c['loop'] else 1),step):
            sc.frame_set(f);sc.render.filepath=str(tmp/f'{name}_{f:03d}.png');bpy.ops.render.render(write_still=True)
            frames.append(Image.open(sc.render.filepath).convert('RGB'))
        if not c['loop']:frames+= [frames[-1]]*8
        save_gif(frames,OUT/f'{name}.gif',int(1000*step/A.FPS))
        pick=[frames[round(i*(len(frames)-1)/5)] for i in range(6)] if not c['loop'] else [frames[round(i*len(frames)/6)%len(frames)] for i in range(6)]
        w,h=pick[0].size;strip=Image.new('RGB',(w*6,h))
        for i,im in enumerate(pick):strip.paste(im,(i*w,0))
        strip.save(OUT/f'{name}-strip.png')
        for o in extra:bpy.data.objects.remove(o,do_unlink=True)
        print('rendered',name,len(frames))
    for p in tmp.glob('*.png'):p.unlink()
    tmp.rmdir()


if __name__=='__main__':
    main()
