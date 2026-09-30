"""Rig the coloured v15 character with the game's 16-bone deckhand skeleton
and pose him like the reference: standing relaxed, arms hanging a little
away from the tunic, elbows softly bent, head turned slightly.

Weights come from Meshy's separate pieces rather than a heat solve: every
head piece follows the head, hands the hands, sleeves the upper arms, the
sash knot and tails the hips, and so on. Only the one-piece arm tubes are
blended (upper arm to forearm across the elbow), plus the tunic's shoulder
frill, which follows the arm a little so no gap opens under it.

Outputs tools/blender/source/crew-meshy-v15-posed.blend (rig in its T rest
pose, the idle pose on top) and crew-meshy-v15/deckhand-v15-rigged.fbx
(T-pose rest, same runtime contract as v14: skin exported white).
Blender coordinates: X across the shoulders (+X is his left), -Y forward, Z up.
"""
import math
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_meshy_v15_colour as C
from crew_meshy_v14 import side_name

ROOT=C.ROOT;OUT=C.OUT
K=C.HEIGHT/.894          # landmarks below are in Meshy's units (0.894 tall)


def P(x,y,z):return Vector((x,y,z))*K


REST={'root':(P(0,0,0),P(0,0,.12),None),
      'pelvis':(P(0,0,.25),P(0,0,.33),'root'),
      'spine':(P(0,0,.33),P(0,0,.58),'pelvis'),
      'head':(P(0,0,.58),P(0,0,.89),'spine')}
for s in (-1,1):
    REST[side_name('upper_arm',s)]=(P(s*.15,0,.525),P(s*.25,0,.525),'spine')
    REST[side_name('forearm',s)]=(P(s*.25,0,.525),P(s*.37,0,.525),side_name('upper_arm',s))
    REST[side_name('hand',s)]=(P(s*.37,0,.525),P(s*.5,0,.525),side_name('forearm',s))
    REST[side_name('thigh',s)]=(P(s*.075,0,.30),P(s*.075,0,.16),'pelvis')
    REST[side_name('shin',s)]=(P(s*.075,0,.16),P(s*.075,0,.05),side_name('thigh',s))
    REST[side_name('foot',s)]=(P(s*.075,0,.05),P(s*.08,-.13,.02),side_name('shin',s))

HEAD_PIECES={'tuft','hair','headband','headband knot','headband tail','brow','eye','nose','ear','head'}


def smooth(t):t=max(0.,min(1.,t));return t*t*(3-2*t)


def weights_for(label,p):
    """p in Meshy units. Returns {bone: weight}."""
    s=1 if p.x>0 else -1;ax=abs(p.x)
    u,f,h=side_name('upper_arm',s),side_name('forearm',s),side_name('hand',s)
    if label in HEAD_PIECES or label=='plate-head':return {'head':1}
    if label=='hand':return {h:1}
    if label=='wrist wrap':return {f:1}
    if label=='arm':
        t=smooth((ax-.225)/.05)                           # elbow at x .25
        if ax>.355:t2=smooth((ax-.355)/.03);return {f:1-t2,h:t2} if t2>0 else {f:1}
        return {u:1-t,f:t} if 0<t<1 else ({f:1} if t>=1 else {u:1})
    if label=='sleeve':return {u:1}
    if label=='tunic':
        w={'spine':1.}
        if p.z<.3:b=smooth((.3-p.z)/.06);w={'spine':1-b,'pelvis':b}
        if ax>.13 and p.z>.46:                             # shoulder frill follows the arm a little
            a=.6*smooth((ax-.13)/.05)*smooth((p.z-.46)/.05)
            w={k:v*(1-a) for k,v in w.items()};w[u]=a
        return w
    if label in('sash','plate-body'):return {'spine':1}
    if label in('sash knot','sash tail'):return {'pelvis':1}
    if label in('shorts','shorts patch'):
        b=smooth((p.z-.24)/.08);return {'pelvis':b,side_name('thigh',s):1-b} if b>0 else {side_name('thigh',s):1}
    if label=='shorts cuff':return {side_name('shin',s):1}
    if label=='foot':return {side_name('shin',s):1} if p.z>.06 else {side_name('foot',s):1}
    if label in('sole','sandal strap'):return {side_name('foot',s):1}
    raise ValueError(label)


PALM,FIST_DROP,THUMB_Y=.507,.038,-.058


def close_fists(body):
    """Meshy's hands are open mittens: a palm, a flat finger slab pointing
    along the arm (palm side down in the T-pose, about as thick as it is
    long, so it cannot be folded) and a thumb sticking forward. Close them
    into the chunky block fists of the reference: drop the whole underside
    (palm and fingers) so the hand is as deep as a fist, tapering into the
    wrist; tuck the bottom-front edge back where the fingers curl under;
    press the thumb flat against the front of the fist."""
    bm=bmesh.new();bm.from_mesh(body.data);moved=0
    for comp in C.pieces(bm):
        vs={v for f in comp for v in f.verts}
        lo=Vector([min(v.co[i] for v in vs) for i in range(3)])/K;hi=Vector([max(v.co[i] for v in vs) for i in range(3)])/K
        if C.classify(lo,hi,len(comp))[1]!='hand':continue
        s=1 if lo.x>0 else -1
        tip=max(abs(v.co.x)/K for v in vs)
        for v in vs:
            p=v.co/K;x=s*p.x;y,z=p.y,p.z
            ramp=smooth((x-.385)/.045)                      # 0 at the wrist, 1 from the knuckles out
            if y<THUMB_Y:                                   # thumb: flat against the front, a little lower
                y=THUMB_Y+(y-THUMB_Y)*.35
            elif z<PALM+.008:                               # underside: palm and fingers deepen to a fist
                z-=FIST_DROP*ramp
                if x>tip-.012:x-=.014*smooth((x-(tip-.012))/.012)   # fingers curl under at the front
            else:continue
            v.co=Vector((s*x,y,z))*K;moved+=1
    bm.to_mesh(body.data);bm.free()
    print('fist vertices moved',moved)


def build():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tools/blender/source/crew-meshy-v15.blend'))
    body=bpy.data.objects['Deckhand_v15']
    close_fists(body)
    data=bpy.data.armatures.new('DeckhandSkeleton')
    rig=bpy.data.objects.new('Deckhand_Rig',data);bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for name,(a,b,parent) in REST.items():
        e=data.edit_bones.new(name);e.head=a;e.tail=b;e.use_deform=True
        if parent:e.parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')

    groups={n:body.vertex_groups.new(name=n) for n in REST}
    bm=bmesh.new();bm.from_mesh(body.data)
    count={}
    for comp in C.pieces(bm):
        vs={v for f in comp for v in f.verts}
        lo=Vector([min(v.co[i] for v in vs) for i in range(3)])/K;hi=Vector([max(v.co[i] for v in vs) for i in range(3)])/K
        _,label=C.classify(lo,hi,len(comp))
        if label=='?':label='plate-head' if lo.z>.58 else 'plate-body'   # mouth; tunic planks
        count[label]=count.get(label,0)+1
        for v in vs:
            for n,w in weights_for(label,v.co/K).items():
                if w>1e-4:groups[n].add([v.index],w,'REPLACE')
    bm.free()
    body.parent=rig;mod=body.modifiers.new('Armature','ARMATURE');mod.object=rig
    print('pieces',count)
    return body,rig


def aim(rig,name,head,direction):
    bone=rig.data.bones[name];length=bone.length
    d=Vector(direction).normalized()
    delta=(bone.tail_local-bone.head_local).rotation_difference(d)
    m=delta.to_matrix().to_4x4()@bone.matrix_local.to_quaternion().to_matrix().to_4x4()
    m.translation=Vector(head);rig.pose.bones[name].matrix=m
    bpy.context.view_layer.update()
    return Vector(head)+d*length


def idle(rig):
    """Relaxed stand, like the reference sheet's hero view."""
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    for s in (-1,1):
        u,f,h=side_name('upper_arm',s),side_name('forearm',s),side_name('hand',s)
        a=math.radians(38)                                  # clear of the wide tunic
        e=aim(rig,u,REST[u][0],(s*math.sin(a),-.08,-math.cos(a)))
        b=math.radians(16)
        w=aim(rig,f,e,(s*math.sin(b),-.22,-math.cos(b)))    # elbow softly bent, forearm forward
        aim(rig,h,w,(s*math.sin(b*.6),-.18,-math.cos(b*.6)))
    head=rig.pose.bones['head'];head.rotation_mode='XYZ';head.rotation_euler=(math.radians(4),0,math.radians(-7))
    bpy.context.view_layer.update()


def export_rigged(body,rig):
    """T rest pose FBX, v14 contract: skin faces exported white."""
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    col=body.data.color_attributes['Col'];keep=[tuple(c.color) for c in col.data]
    skin=C.COL['skin']
    for c in col.data:
        if max(abs(a-b) for a,b in zip(c.color[:3],skin))<.01:c.color=(1,1,1,1)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);body.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/'deckhand-v15-rigged.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},
        axis_forward='-Z',axis_up='Y',add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,
        use_triangles=True,colors_type='LINEAR',mesh_smooth_type='FACE')
    for c,v in zip(col.data,keep):c.color=v


if __name__=='__main__':
    body,rig=build()
    export_rigged(body,rig)
    idle(rig)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'tools/blender/source/crew-meshy-v15-posed.blend'))
