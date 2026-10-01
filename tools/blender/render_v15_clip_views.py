"""Five-angle review sheet of one v15 clip at key frames: OUT=<dir> python render_v15_clip_views.py -- <Clip>"""
import sys,os;sys.path.insert(0,'tools/blender')
import bpy
from mathutils import Vector
from PIL import Image,ImageDraw
import crew_meshy_v15_anims as A, crew_v15_mill as MILL
name=sys.argv[sys.argv.index('--')+1];out=os.environ['OUT']
bpy.ops.wm.open_mainfile(filepath='tools/blender/source/crew-meshy-v15-anims.blend')
sc=bpy.context.scene;sc.render.fps=30
rig=bpy.data.objects['Deckhand_Rig'];sv=A.Solver(rig);c=A.CLIPS[name]
sc.render.engine='BLENDER_WORKBENCH';sc.view_settings.view_transform='Standard'
sh=sc.display.shading;sh.light='STUDIO';sh.color_type='VERTEX';sh.show_cavity=True;sh.cavity_type='WORLD';sh.show_shadows=True
sh.background_type='VIEWPORT';sh.background_color=(.37,.55,.68)
if sc.world is None:sc.world=bpy.data.worlds.new('W')
sc.world.color=(.37,.55,.68)
g=A.box_mesh('ground',[((8,8,.02),(0,-1.5,-.011),'soil')])
g.data.color_attributes['Col'].data.foreach_set('color',[v for _ in range(len(g.data.loops)) for v in (*A.C.srgb('#7E9E62'),1)])
for p in c['props']:A.box_mesh(p[0],[(p[2],p[1],p[3])])
if c.get('env'):
    env,stand,_=MILL.load_env(c['env']);rig.location=stand;bpy.context.view_layer.update()
else:stand=Vector((0,0,0))
act=bpy.data.actions['Crew_'+name];rig.animation_data.action=act;sc.frame_set(0)
held={}
if c['rtool']:held[A.RIGHT]=A.attach_tool(rig,sv,c['rtool'],A.RIGHT)
if c['ltool']:held[A.LEFT]=A.attach_tool(rig,sv,c['ltool'],A.LEFT)
A.animate_props(rig,name,held)                             # a tool with its own track (dropped, thrown, a lanyard)
if c.get('gun'):A.animate_env(env,name,int(act.frame_end))  # the gun runs out and recoils
cd=bpy.data.cameras.new('c');cam=bpy.data.objects.new('c',cd);sc.collection.objects.link(cam);sc.camera=cam;cd.type='ORTHO';cd.ortho_scale=1.45
sc.render.resolution_x=sc.render.resolution_y=380
views=[('3/4 his right',(-2.2,-2.4,1.3)),('side, his right',(-3,0,.7)),('front',(0,-3,.8)),('3/4 his left',(2.2,-2.4,1.3)),('above',(-.8,-1.6,3.2))]
if c.get('env')=='mill':      # game-camera angles from the front of the building, clear of its pillars
    views=[('game view, front 3/4',(-2.6,-4.2,3.0)),('front, eye level',(0,-3,.9)),('3/4 his right, low',(-2.4,-2.0,1.1)),('3/4 his left',(2.2,-2.4,1.4)),('above',(-.8,-1.6,3.2))]
    cd.ortho_scale=1.75
if c.get('env')=='tree':      # the canopy hides him from above: side and low angles, the canopy left out of these
    views=[('game view, his right',(-3.4,1.6,2.4)),('side, his right',(-3,.2,.8)),('behind him',(-.8,3,1.2)),('3/4 his left, low',(2.6,-.3,.9)),('game view, his left',(3.2,1.8,2.4))]
    cd.ortho_scale=1.9
    for o in env.values():
        if 'Canopy' in o.name:o.hide_render=True
if c.get('env')=='cannon':    # the gun on his right, ahead of him: from behind and his left, clear of the gun
    views=[('behind, high',(-.4,3.4,2.2)),('3/4 behind his left',(2.8,2.6,1.6)),('side, his left',(3.2,-.3,.9)),('3/4 behind his right',(-3.0,2.6,1.8)),('above',(-.4,-.4,4.2))]
    cd.ortho_scale=2.6
if c.get('env')=='farm':      # the bed in front of him, he turned to his right: across the bed, from both sides, behind
    views=[('game view, his right',(-3.4,1.4,2.6)),('side, his right',(-3.2,-.4,.8)),('3/4 his left, low',(2.6,-1.8,1.0)),('behind him',(.6,3.0,1.4)),('above',(-.3,-.6,4.0))]
    cd.ortho_scale=2.2
if c.get('env')=='rock':      # the rock stands in front of him: side and back angles
    views=[('game view, his right',(-3.4,1.6,2.4)),('side, his right',(-3,.2,.8)),('behind him',(-.8,3,1.2)),('3/4 his left, low',(2.6,-.3,.9)),('side, his left',(3,.2,.8))]
    cd.ortho_scale=1.9
TGT=Vector((-.4,-.3,.55)) if c.get('env')=='cannon' else Vector((-.1,-.35,.4)) if c.get('env')=='farm' else Vector((0,-.2,.55))
if c.get('throw'):            # the target stands 3 m off: wide side angles taking in him, the flight and the goat
    views=[('side, his right',(-4.2,-1.5,1.0)),('game view, his right',(-3.4,1.4,3.0)),('behind him',(-.5,3.2,1.4)),('3/4 his left',(3.2,.4,1.6)),('above',(-1.0,-1.5,4.8))]
    cd.ortho_scale=3.9;TGT=Vector((0,-1.5,.55))
n=int(act.frame_end);keys=[round(n*k/4) for k in range(4)] if c['loop'] else [round(n*k/4) for k in range(5)]
if name=='Hunt':keys=[0,round(n*.33),round(n*.45),round(n*.52),round(n*.62)]   # stalking, sighting, the release, in flight, the hit
if name=='PickUp':keys=[0,26,37,45,51,60]   # walking in, the grip, the heave, seated on his belly, fists under, carrying
if name=='GunFire':keys=[0,8,16,23,30,44]   # at the station, raising the linstock, the match on the vent, the recoil, the flinch, watching the shot
if name=='SetDown':keys=[0,9,16,40,50,72]   # letting go, landed, mid-wipe, the flick, into the walk
if name=='GunTend':keys=[0,12,29,38,95,155]   # station, arm down, fist on the breech, the pat, looking out, the glance
if name=='Farm':keys=[0,9,14,20,32]   # raised, coming down, the bite, holding, dragged back
if name=='Mine':keys=[0,round(n*.26),round(n*.34),round(n*.40)]   # raised, head trailing, tipping over, the strike
if name=='Chop':keys=[0,round(n*.28),round(n*.33),round(n*.40)]   # cocked, hands dropped, sweeping level, the bite
rows=[]
for f in keys:
    sc.frame_set(f);row=[]
    for vn,eye in views:
        tgt=stand+TGT;eye=stand+Vector(eye);cam.location=eye;cam.rotation_euler=(tgt-Vector(eye)).to_track_quat('-Z','Y').to_euler()
        sc.render.filepath=out+'/_v.png';bpy.ops.render.render(write_still=True);row.append(Image.open(out+'/_v.png').convert('RGB'))
    rows.append((f,row))
W=380;sheet=Image.new('RGB',(W*len(views),W*len(rows)+24),'white');d=ImageDraw.Draw(sheet)
for i,(vn,_) in enumerate(views):d.text((i*W+6,6),vn,fill='black')
for r,(f,row) in enumerate(rows):
    for i,im in enumerate(row):sheet.paste(im,(i*W,24+r*W))
    d.rectangle((0,24+r*W,70,40+r*W),fill='white');d.text((4,26+r*W),f'frame {f}',fill='black')
sheet.save(out+f'/{name}-views.png')
