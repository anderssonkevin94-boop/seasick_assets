"""Soft-lit review renders of the Meshy character v15 (coloured, T-pose as delivered), set up like the reference sheet:
blue studio backdrop, soft key from the upper left, cool fill, contact
shadow. Cycles on the CPU, so it runs headless. These are presentation
renders for comparing against the painted reference, not the game's look
(Unity uses its own toon lighting)."""
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'crew-meshy-v15'
# Optional: python render_v15_lit.py -- <blend name> <file prefix>
ARGS=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
BLEND=ARGS[0] if ARGS else 'crew-meshy-v15.blend';PREFIX=ARGS[1] if len(ARGS)>1 else 'lit'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tools/blender/source'/BLEND))
scene=bpy.context.scene
scene.frame_set(1)
for o in list(scene.objects):
    if o.type in {'CAMERA','LIGHT'}:bpy.data.objects.remove(o,do_unlink=True)
scene.render.engine='CYCLES'
scene.cycles.device='CPU';scene.cycles.samples=96;scene.cycles.use_denoising=True
try:scene.cycles.denoiser='OPENIMAGEDENOISE'
except Exception:pass
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
scene.view_settings.exposure=-.35
# Transparent film + a shadow-catcher floor: the renders are composited onto
# a flat reference-blue backdrop afterwards, so there is no horizon seam.
scene.render.film_transparent=True

def srgb(h):
    h=h.lstrip('#');c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return [v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c]

world=scene.world or bpy.data.worlds.new('Studio');scene.world=world;world.use_nodes=True
bg=world.node_tree.nodes['Background'];bg.inputs['Color'].default_value=(*srgb('#8FB7D6'),1);bg.inputs['Strength'].default_value=.55
# Backdrop: one curved-free sweep, same blue as the reference, catches the shadow.
bpy.ops.mesh.primitive_plane_add(size=30,location=(0,0,0))
floor=bpy.context.object;fm=bpy.data.materials.new('Backdrop');fm.use_nodes=True
fb=fm.node_tree.nodes['Principled BSDF'];fb.inputs['Base Color'].default_value=(*srgb('#5E8DAE'),1);fb.inputs['Roughness'].default_value=1
floor.data.materials.append(fm)
floor.is_shadow_catcher=True
key=bpy.data.lights.new('Key','AREA');key.energy=300;key.size=2.5;key.color=(1,.96,.9)
k=bpy.data.objects.new('Key',key);scene.collection.objects.link(k);k.location=(-2.6,-3.2,3.4)
k.rotation_euler=(Vector((0,0,.7))-k.location).to_track_quat('-Z','Y').to_euler()
fill=bpy.data.lights.new('Fill','AREA');fill.energy=70;fill.size=4;fill.color=(.8,.88,1)
f=bpy.data.objects.new('Fill',fill);scene.collection.objects.link(f);f.location=(3.2,-2.4,1.6)
f.rotation_euler=(Vector((0,0,.7))-f.location).to_track_quat('-Z','Y').to_euler()
rim=bpy.data.lights.new('Rim','AREA');rim.energy=160;rim.size=2
r=bpy.data.objects.new('Rim',rim);scene.collection.objects.link(r);r.location=(1.5,3,2.5)
r.rotation_euler=(Vector((0,0,.8))-r.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Cam');cam=bpy.data.objects.new('Cam',cd);scene.collection.objects.link(cam);scene.camera=cam


def shot(name,eye,target,size,lens=None,ortho=None):
    cam.location=eye;cam.rotation_euler=(Vector(target)-Vector(eye)).to_track_quat('-Z','Y').to_euler()
    if ortho:cd.type='ORTHO';cd.ortho_scale=ortho
    else:cd.type='PERSP';cd.lens=lens
    scene.render.resolution_x,scene.render.resolution_y=size;scene.render.resolution_percentage=100
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)


# Hero: three-quarter from his left-front, as in the reference (framed wide for the T-pose).
shot(PREFIX+'-hero',(1.3,-2.6,.95),(0,0,.64),(1100,1000),lens=50)
for name,eye in [('lit-front',(0,-7,.7)),('lit-back',(0,7,.7))]:
    shot(PREFIX+name[3:],eye,(0,0,.66),(900,700),ortho=1.75)
for name,eye in [('lit-left',(7,-.1,.7)),('lit-right',(-7,-.1,.7))]:
    shot(PREFIX+name[3:],eye,(0,0,.66),(520,700),ortho=1.4)
shot(PREFIX+'-face',(.55,-2.2,1.12),(0,-.1,.98),(700,700),lens=70)


# Composite every render onto the reference's flat blue backdrop.
import numpy as np
BACK=np.array([95,142,178],dtype=np.float32)/255
for png in OUT.glob(PREFIX+'-*.png'):
    img=bpy.data.images.load(str(png));w,h=img.size
    px=np.array(img.pixels[:],dtype=np.float32).reshape(h,w,4)
    y=np.linspace(0,1,h)[:,None,None]
    back=np.clip(BACK*(0.86+0.22*y),0,1)   # gentle vertical gradient, lighter at the top
    rgb=px[...,:3]*px[...,3:4]+back*(1-px[...,3:4])
    out=np.concatenate([rgb,np.ones((h,w,1),np.float32)],axis=2)
    img.pixels[:]=out.ravel();img.filepath_raw=str(png);img.file_format='PNG';img.save()
