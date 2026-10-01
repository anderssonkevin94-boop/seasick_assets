"""GLB and page for the v15 animation viewer (crew-meshy-v15/viewer/): the
GLB is embedded in index.html (base64), so the page is one self-contained file.

Rig + mesh in its preview colours (skin not white: this is for looking at),
every clip from crew_meshy_v15_anims.py as a glTF animation, and each clip's
preview props and tools as named nodes the page shows per clip:
`prop__<Clip>__<n>` (static, in the scene) and `tool__<Clip>__R` / `__L`
(parented to the hand bones). Everything is visible in the file; the page
hides what the current clip does not use.
"""
import sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_meshy_v15_anims as A

OUT=A.C.OUT/'viewer'


def main():
    bpy.ops.wm.open_mainfile(filepath=str(A.ROOT/'tools/blender/source/crew-meshy-v15-anims.blend'))
    rig=bpy.data.objects['Deckhand_Rig'];solver=A.Solver(rig)
    rig.animation_data.action=None;solver.reset()
    count=0
    for name,c in A.CLIPS.items():
        for i,(pname,centre,size,colour,_) in enumerate(c['props']):
            o=A.box_mesh(f'prop__{name}__{i}',[(size,centre,colour)]);count+=1
        for kind,side,tag in((c['rtool'],A.RIGHT,'R'),(c['ltool'],A.LEFT,'L')):
            if kind:
                o=A.attach_tool(rig,solver,kind,side);o.name=f'tool__{name}__{tag}';count+=1
    # Clips set in a building: the building itself is their prop, placed so its
    # Worker_Stand is where he stands (the origin), under one prop__<Clip>__env node.
    import crew_v15_mill as MILL
    for name,c in A.CLIPS.items():
        if not c.get('env'):continue
        env,stand,_=MILL.load_env(c['env'])
        for o in list(env.values()):
            if o.hide_render or 'Canopy' in o.name:bpy.data.objects.remove(o,do_unlink=True);env={k:v for k,v in env.items() if v!=o}   # a tree's canopy would hide him
        root=bpy.data.objects.new(f'prop__{name}__env',None);bpy.context.scene.collection.objects.link(root)
        for o in env.values():
            if o.parent is None:o.parent=root
        root.location=-stand;count+=1
    for o in bpy.data.objects:
        if o.type=='MESH':
            for p in o.data.polygons:p.use_smooth=False
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/'deckhand-v15.glb'),export_format='GLB',use_selection=False,
        export_yup=True,export_apply=False,export_animations=True,export_animation_mode='ACTIONS',
        export_force_sampling=True,export_skins=True,export_def_bones=True,export_vertex_color='ACTIVE',
        export_all_vertex_colors=False,export_materials='EXPORT')
    print('props and tools',count)
    write_page()


GROUPS=[('Building jobs',['Saw','Crank','Farm','Smith','Cook','Mill','Lookout','Quarry','Fletcher','Fisher']),
        ('Camp tasks',['Idle','Walk','Chop','Mine','Forage','Build','Carry','PickUp','SetDown','Hunt']),
        ('Aboard ship',['DeckBrace','RailGrip','Gangway','Bail','ThrowLine','HaulLine','GunRam','GunFire','Row','Soaked']),
        ('Seasickness',['SickSway','SickWalk','SickClutch','SickRail','SickCollapse','SickKneel'])]
WHERE={'Saw':'Sawmill · sawyer','Crank':'Sawmill level 2 (concept) · sawyer','Farm':'Farm plot · farmhand','Smith':'Forge · smith','Cook':'Kitchen · cook',
       'Mill':'Mill · miller','Lookout':'Watchtower · lookout','Quarry':'Quarry · quarryman',
       'Fletcher':"Fletcher's · fletcher",'Fisher':'Fishing hut · fisher',
       'Idle':'Standing about','Walk':'Walking (in place)','Chop':'Gathering timber, clearing ground',
       'Mine':'Gathering stone and ore','Forage':'Gathering spice and food','Build':'Raising a building',
       'Carry':'Hauling a load (in place)','PickUp':'Lifting a load off a pile','SetDown':'Setting a load down',
       'Hunt':'Hunting','DeckBrace':'Aboard, at his post','RailGrip':'Aboard, gripping the rail through a warning',
       'Gangway':'Boarding over the gangway (in place)','Bail':'Aboard, sent to the buckets',
       'ThrowLine':'Man overboard: throwing the line','HaulLine':'Man overboard: hauling the swimmer in',
       'GunRam':'Gunner: reloading','GunFire':'Gunner: firing','Row':'Jolly boat','Soaked':'Resting after a rescue',
       'SickSway':'Seasick, standing','SickWalk':'Seasick, walking (in place)','SickClutch':'Badly seasick',
       'SickRail':'Seasick at the rail','SickCollapse':'Worst seasickness: going down','SickKneel':'Worst seasickness: on his knees'}
LABEL={'PickUp':'Pick up','SetDown':'Set down','DeckBrace':'Deck brace','RailGrip':'Rail grip','ThrowLine':'Throw line',
       'HaulLine':'Haul line','GunRam':'Gun: ram','GunFire':'Gun: fire','SickSway':'Sick: sway','SickWalk':'Sick: walk',
       'SickClutch':'Sick: clutch','SickRail':'Sick: at the rail','SickCollapse':'Sick: collapse','SickKneel':'Sick: kneel'}
TOOLS={'carrylog':'log','sack':'sack','peg':'quern peg','shaft':'arrow shaft','coil':'coiled line','pick':'pickaxe'}


def write_page():
    import json
    info=json.loads((A.OUT/'clips.json').read_text())
    clips={k:{'label':LABEL.get(k,k),'where':WHERE.get(k,''),'what':v['what'][:1].upper()+v['what'][1:]+'.',
              'seconds':v['seconds'],'frames':v['frames'],'loop':v['loop'],
              'rtool':TOOLS.get(v['tool_right_hand'],v['tool_right_hand']),'ltool':TOOLS.get(v['held_left_hand'],v['held_left_hand']),'env':A.CLIPS[k].get('env')}
           for k,v in info.items()}
    groups=[{'name':n,'clips':[c for c in cs if c in clips]} for n,cs in GROUPS]
    missing=set(clips)-{c for g in groups for c in g['clips']}
    assert not missing,missing
    html=(OUT/'index.template.html').read_text()
    import base64
    html=html.replace('/*GLB_DATA*/',base64.b64encode((OUT/'deckhand-v15.glb').read_bytes()).decode())
    html=html.replace('/*CLIPS_DATA*/',json.dumps(clips)).replace('/*GROUPS_DATA*/',json.dumps(groups))
    # ASCII only, so the page reads right whatever charset it is served with:
    # entities in the markup, \u escapes inside the script.
    import re
    def esc(text,script):
        return ''.join(ch if ord(ch)<128 else ('\\u%04x'%ord(ch) if script else '&#x%x;'%ord(ch)) for ch in text)
    parts=re.split(r'(<script>.*?</script>)',html,flags=re.S)
    html=''.join(esc(x,x.startswith('<script>')) for x in parts)
    (OUT/'index.html').write_text(html)


if __name__=='__main__':
    main()
