"""Anatomy check of v15 clips, every frame, with their tools and props: python check_v15_clip.py -- <Clip> ..."""
import sys;sys.path.insert(0,'tools/blender')
import bpy
import crew_meshy_v15_anims as A, crew_v15_mill as MILL, crew_v15_anatomy as N
bpy.ops.wm.open_mainfile(filepath='tools/blender/source/crew-meshy-v15-anims.blend')
bpy.context.scene.render.fps=30
rig=bpy.data.objects['Deckhand_Rig'];body=bpy.data.objects['Deckhand_v15'];sv=A.Solver(rig)
ck=N.Checker(body,rig,A.K)
for name in sys.argv[sys.argv.index('--')+1:]:
    c=A.CLIPS[name];rig.animation_data.action=None;bpy.context.scene.frame_set(0)
    props=[A.box_mesh(p[0],[(p[2],p[1],p[3])]) for p in c['props']]
    if c.get('env'):
        env,at,extra=MILL.load_env(c['env']);rig.location=at;props+=extra
    else:rig.location=(0,0,0)
    bpy.context.view_layer.update()
    tools=[]
    rig.animation_data.action=bpy.data.actions['Crew_'+name];bpy.context.scene.frame_set(0)
    if c['rtool']:tools.append(A.attach_tool(rig,sv,c['rtool'],A.RIGHT))
    if A.flies(c):A.animate_load(tools[-1],rig,name)          # the tool leaves him (dropped, thrown)
    if c['ltool']:tools.append(A.attach_tool(rig,sv,c['ltool'],A.LEFT))
    r=N.check_clip(ck,rig,bpy.data.actions['Crew_'+name],None,tools=tools,props=props,step=1)
    print('CHECK',name,{f'{k[0]}:{k[1]}':v for k,v in sorted(r.items())} or 'clean: no clipping, joints in range, every frame')
