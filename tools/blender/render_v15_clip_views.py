"""Five-angle review sheet of one v15 clip at key frames: OUT=<dir> python render_v15_clip_views.py -- <Clip>"""
import sys,os;sys.path.insert(0,'tools/blender')
import bpy
from mathutils import Vector
from PIL import Image,ImageDraw
import crew_meshy_v15_anims as A
name=sys.argv[sys.argv.index('--')+1];out=os.environ['OUT']
bpy.ops.wm.open_mainfile(filepath='tools/blender/source/crew-meshy-v15-anims.blend')
sc=bpy.context.scene;sc.render.fps=30
rig=bpy.data.objects['Deckhand_Rig'];sv=A.Solver(rig);c=A.CLIPS[name]
sc.render.engine='BLENDER_WORKBENCH';sc.view_settings.view_transform='Standard'
sh=sc.display.shading;sh.light='STUDIO';sh.color_type='VERTEX';sh.show_cavity=True;sh.cavity_type='WORLD';sh.show_shadows=True
sh.background_type='VIEWPORT';sh.background_color=(.37,.55,.68)
if sc.world is None:sc.world=bpy.data.worlds.new('W')
sc.world.color=(.37,.55,.68)
g=A.box_mesh('ground',[((4,4,.02),(0,0,-.011),'soil')])
g.data.color_attributes['Col'].data.foreach_set('color',[v for _ in range(len(g.data.loops)) for v in (*A.C.srgb('#7E9E62'),1)])
for p in c['props']:A.box_mesh(p[0],[(p[2],p[1],p[3])])
act=bpy.data.actions['Crew_'+name];rig.animation_data.action=act;sc.frame_set(0)
if c['rtool']:A.attach_tool(rig,sv,c['rtool'],A.RIGHT)
if c['ltool']:A.attach_tool(rig,sv,c['ltool'],A.LEFT)
cd=bpy.data.cameras.new('c');cam=bpy.data.objects.new('c',cd);sc.collection.objects.link(cam);sc.camera=cam;cd.type='ORTHO';cd.ortho_scale=1.45
sc.render.resolution_x=sc.render.resolution_y=380
views=[('3/4 his right',(-2.2,-2.4,1.3)),('side, his right',(-3,0,.7)),('front',(0,-3,.8)),('3/4 his left',(2.2,-2.4,1.3)),('above',(-.8,-1.6,3.2))]
n=int(act.frame_end);keys=[round(n*k/4) for k in range(4)] if c['loop'] else [round(n*k/4) for k in range(5)]
rows=[]
for f in keys:
    sc.frame_set(f);row=[]
    for vn,eye in views:
        tgt=Vector((0,-.2,.55));cam.location=eye;cam.rotation_euler=(tgt-Vector(eye)).to_track_quat('-Z','Y').to_euler()
        sc.render.filepath=out+'/_v.png';bpy.ops.render.render(write_still=True);row.append(Image.open(out+'/_v.png').convert('RGB'))
    rows.append((f,row))
W=380;sheet=Image.new('RGB',(W*len(views),W*len(rows)+24),'white');d=ImageDraw.Draw(sheet)
for i,(vn,_) in enumerate(views):d.text((i*W+6,6),vn,fill='black')
for r,(f,row) in enumerate(rows):
    for i,im in enumerate(row):sheet.paste(im,(i*W,24+r*W))
    d.rectangle((0,24+r*W,70,40+r*W),fill='white');d.text((4,26+r*W),f'frame {f}',fill='black')
sheet.save(out+f'/{name}-views.png')
