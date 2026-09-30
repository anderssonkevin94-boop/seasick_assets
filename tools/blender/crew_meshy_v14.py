"""Meshy character v14: Kevin's Meshy model made game-ready and rigged.

Source: crew-meshy-v14/source/meshy-bandana-adventurer.fbx (Meshy image-to-3D,
"Bandana Adventurer", 771,306 triangles, untextured, Z up, facing -Y).

Pipeline:
  1. Feet on the ground, scaled to 1.30 m (AstraPlaytestImport rescales to 1.7).
  2. Reduce to ~2,600 triangles: collapse to 40k, dissolve near-coplanar faces
     (keeps Meshy's flat facets), collapse to target, flat shading.
  3. Rig: the game's 16-bone skeleton (same names/hierarchy as the in-game
     deckhand) placed on landmarks measured from the mesh's own silhouettes;
     Blender automatic (heat) weights, then clean-up rules, max 4 influences.
  4. Colour by region (Meshy gave no texture), plus crisp face plates.
  5. Split into CREW_Skin (white for the sickness tint) and CREW_Cloth.
  6. Pose tests, renders, FBX export.
Stages 4-6 are added once the deformation passes review.
"""
import json
import math
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'crew-meshy-v14'
SRC=OUT/'source/meshy-bandana-adventurer.fbx'
TARGET=2300
HEIGHT=1.30
AUDIT={}


def apply_mod(o,m):
    with bpy.context.temp_override(object=o,active_object=o,selected_objects=[o],selected_editable_objects=[o]):
        bpy.ops.object.modifier_apply(modifier=m.name)


def tris(o):return sum(len(p.vertices)-2 for p in o.data.polygons)


def load_and_reduce():
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=str(SRC))
    o=[x for x in bpy.data.objects if x.type=='MESH'][0];o.name='Body'
    me=o.data
    zs=[v.co.z for v in me.vertices];zmin,zmax=min(zs),max(zs);k=HEIGHT/(zmax-zmin)
    for v in me.vertices:v.co=Vector((v.co.x*k,v.co.y*k,(v.co.z-zmin)*k))
    me.update()
    AUDIT['source_triangles']=tris(o)
    for kind,val in [('collapse',40000),('planar',4),('collapse',TARGET)]:
        if kind=='collapse':
            t=o.modifiers.new('t','TRIANGULATE');apply_mod(o,t)
            m=o.modifiers.new('d','DECIMATE');m.decimate_type='COLLAPSE';m.ratio=min(1,val/tris(o));m.use_collapse_triangulate=True
        else:
            m=o.modifiers.new('d','DECIMATE');m.decimate_type='DISSOLVE';m.angle_limit=math.radians(val);m.delimit={'NORMAL'}
        apply_mod(o,m)
    t=o.modifiers.new('t','TRIANGULATE');apply_mod(o,t)
    with bpy.context.temp_override(object=o,active_object=o,selected_objects=[o],selected_editable_objects=[o]):
        try:bpy.ops.mesh.customdata_custom_splitnormals_clear()
        except RuntimeError:pass
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.dissolve_degenerate(bm,dist=1e-6,edges=bm.edges[:])
    bmesh.ops.triangulate(bm,faces=bm.faces[:])
    bm.to_mesh(me);bm.free()
    for p in me.polygons:p.use_smooth=False
    me.materials.clear()
    AUDIT['triangles']=tris(o)
    return o


def cut_boundaries(o):
    """Slice the mesh along the sash's two edges and the headband's top and
    bottom, so those colour boundaries are straight lines rather than whole
    large triangles flipping between red and cream."""
    me=o.data;bm=bmesh.new();bm.from_mesh(me)
    n=Vector((-SASH_TILT,0,1)).normalized();up=Vector((0,0,1))
    # Each cut only touches the faces of the part it separates.
    torso=lambda c:abs(c.x)<.34 and .38<c.z<.87
    head=lambda c:c.z>.95
    for co,no,where in [((0,0,SASH_Z-SASH_HALF),n,torso),((0,0,SASH_Z+SASH_HALF),n,torso),
                        ((0,0,1.035),up,head),((0,0,1.14),up,head)]:
        faces=[f for f in bm.faces if where(f.calc_center_median())]
        verts={v for f in faces for v in f.verts};edges={e for f in faces for e in f.edges}
        bmesh.ops.bisect_plane(bm,geom=list(verts)+list(edges)+faces,plane_co=co,plane_no=no,dist=1e-5)
    bmesh.ops.triangulate(bm,faces=bm.faces[:])
    bm.to_mesh(me);bm.free()
    for p in me.polygons:p.use_smooth=False
    AUDIT['triangles_after_cuts']=tris(o)


def side_name(base,s):return base+('.R' if s>0 else '.L')


# Landmarks measured from 1 px = 1 mm front and side silhouettes of the
# normalised Meshy mesh (see README). +X is his left, -Y his front.
REST={'root':((0,0,.02),(0,0,.20),None),
      'pelvis':((0,0,.36),(0,0,.46),'root'),
      'spine':((0,0,.46),(0,0,.82),'pelvis'),
      'head':((0,0,.82),(0,0,1.28),'spine')}
for s in [-1,1]:
    u,f,h=side_name('upper_arm',s),side_name('forearm',s),side_name('hand',s)
    t,sh,ft=side_name('thigh',s),side_name('shin',s),side_name('foot',s)
    REST[u]=((s*.20,-.01,.73),(s*.29,-.02,.60),'spine')
    REST[f]=(REST[u][1],(s*.335,-.03,.51),u)
    REST[h]=(REST[f][1],(s*.35,-.04,.37),f)
    REST[t]=((s*.12,0,.37),(s*.13,-.01,.22),'pelvis')
    REST[sh]=(REST[t][1],(s*.14,-.02,.10),t)
    REST[ft]=(REST[sh][1],(s*.15,-.2,.04),sh)


def build_rig():
    data=bpy.data.armatures.new('DeckhandSkeleton')
    rig=bpy.data.objects.new('Deckhand_Rig',data);bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for name,(a,b,parent) in REST.items():
        bone=data.edit_bones.new(name);bone.head=a;bone.tail=b
        if parent:bone.parent=data.edit_bones[parent]
        bone.use_deform=True
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


def bind(body,rig):
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    groups={g.index:g.name for g in body.vertex_groups}
    unweighted=sum(1 for v in body.data.vertices if not any(g.weight>1e-4 for g in v.groups))
    AUDIT['heat_unweighted_vertices']=unweighted
    return unweighted


def clean_weights(body):
    """Rules the heat solver cannot know: the head owns everything above the
    collar (face, hair, headband and its tails); arms never own the body's
    front (the sash knot sits right by the right fist); vertices the solver
    missed take the nearest bone. Then keep 4 influences and normalise."""
    rig=body.parent
    vg={g.name:g for g in body.vertex_groups}
    for name in REST:
        if name not in vg:vg[name]=body.vertex_groups.new(name=name)
    idx={g.index:g.name for g in body.vertex_groups}
    def seg_dist(p,a,b):
        a,b=Vector(a),Vector(b);ab=b-a;t=max(0,min(1,(p-a).dot(ab)/ab.length_squared));return (a+ab*t-p).length
    arm_bones=[n for n in REST if n.split('.')[0] in ('upper_arm','forearm','hand')]
    for v in body.data.vertices:
        p=v.co;w={idx[g.group]:g.weight for g in v.groups if g.weight>1e-4}
        if p.z>.86:w={'head':1.}
        elif p.z>.80 and abs(p.x)<.19:w={'head':.3,'spine':.7}
        if abs(p.x)<.245 and p.z<.58:
            for n in arm_bones:w.pop(n,None)
        sash_tail=p.y<-.13 and -.33<p.x<-.19 and .15<p.z<.5
        if sash_tail:                               # knot and tails follow the hips
            for n in arm_bones:w.pop(n,None)
        elif abs(p.x)>.255 and .33<p.z<.60:        # fists and forearms: arm bones only
            w={n:x for n,x in w.items() if n in arm_bones}
            if not w:
                d={n:seg_dist(p,*REST[n][:2]) for n in arm_bones}
                w={min(d,key=d.get):1.}
        if not w:
            d={n:seg_dist(p,a,b) for n,(a,b,_) in REST.items() if n!='root'}
            n=min(d,key=d.get);w={n:1.}
        top=sorted(w.items(),key=lambda kv:-kv[1])[:4];total=sum(x for _,x in top)
        old=[idx[g.group] for g in v.groups]      # names first: removing shifts v.groups
        for n in old:vg[n].remove([v.index])
        for n,x in top:vg[n].add([v.index],x/total,'REPLACE')


def pose(rig,kind):
    """Test poses built by aiming bones at world directions (as for v11):
    rest, work (arms forward and down), reach (arms forward), crouch (deep
    squat, heels raised) and walk (stride)."""
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    rig.location=(0,0,0);bpy.context.view_layer.update()
    if kind=='rest':return
    def aim(name,head,direction):
        bone=rig.data.bones[name];length=bone.length
        delta=(bone.tail_local-bone.head_local).rotation_difference(Vector(direction).normalized())
        m=delta.to_matrix().to_4x4()@bone.matrix_local.to_quaternion().to_matrix().to_4x4()
        m.translation=Vector(head);rig.pose.bones[name].matrix=m
        bpy.context.view_layer.update()
        return Vector(head)+Vector(direction).normalized()*length
    for s in [-1,1]:
        u,f,h=side_name('upper_arm',s),side_name('forearm',s),side_name('hand',s)
        t,sh,ft=side_name('thigh',s),side_name('shin',s),side_name('foot',s)
        if kind=='reach':ud=(s*.35,-.90,.10);fd=(s*.08,-1,.05)
        elif kind=='work':ud=(s*.45,-.45,-.77);fd=(s*.1,-1,-.15)
        elif kind=='walk':ud=(s*.3,s*.35,-.88);fd=(s*.2,s*.2,-.96)
        else:ud=(s*.55,-.15,-.82);fd=(s*.25,-.2,-.95)
        e=aim(u,REST[u][0],ud);w=aim(f,e,fd);aim(h,w,fd)
        if kind=='crouch':td=(s*.12,-.7,-.7);sd=(0,.55,-.83);fdir=(0,-.8,-.6)
        elif kind=='walk':td=(0,-s*.42,-.9);sd=(0,s*.15,-.99);fdir=(0,-.97,-.24)
        else:td=(s*.06,-.05,-.99);sd=(s*.03,.1,-.99);fdir=(0,-.97,-.24)
        knee=aim(t,REST[t][0],td);ankle=aim(sh,knee,sd);aim(ft,ankle,fdir)
    body=[o for o in rig.children if o.type=='MESH']
    graph=bpy.context.evaluated_depsgraph_get()
    low=min((o.evaluated_get(graph).matrix_world@v.co).z for o in body for v in o.evaluated_get(graph).data.vertices)
    rig.location.z=-low;bpy.context.view_layer.update()


PALETTE={'linen':'#D8CFBC','skin':'#D99259','pants':'#2D5664','pantcuff':'#2F6572',
         'sash':'#D0443A','hair':'#3A2921','eye':'#1C1816','mouth':'#A23B2F',
         'sole':'#4A3226','wood':'#B07A4A'}


def srgb_to_linear(h):
    h=h.lstrip('#');c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)


COL={k:srgb_to_linear(v) for k,v in PALETTE.items()}
# Sash: a band along the plane z = SASH_Z + SASH_TILT * x (his left shoulder
# down to the knot on his right hip), measured on the Meshy front view.
SASH_Z,SASH_TILT,SASH_HALF=.63,.78,.042


def region(c):
    """Palette name for a face centred at c (rest pose, metres)."""
    x,y,z=c
    if z<.042:return 'sole'
    if z<.093:return 'wood'
    if z<.172:return 'skin'                                   # ankles and feet
    if x<-.19 and x>-.33 and y<-.13 and .15<z<.50:return 'sash' # knot and tails at his right hip
    if z>.84 and x>.265:return 'sash'                         # headband tails
    if z>.86 and y>.11 and x>.13 and z<1.15:return 'sash'     # knot at the back-left
    if z<.225:return 'pantcuff'
    if z<.36:
        leg=min(math.hypot(x-s*.13,y+.02) for s in (-1,1))
        return 'pants' if leg<.118 else 'linen'
    if abs(x)>.25 and z<.575:return 'skin'                    # forearms and fists
    if z>=.87 or (z>=.79 and (x/.255)**2+((y+.03)/.235)**2<1):
        if z>1.14:return 'hair'
        if z>1.035:return 'sash'                              # headband
        return 'skin'
    if .40<z<.84 and abs(z-(SASH_Z+SASH_TILT*x))<SASH_HALF:return 'sash'
    return 'linen'


def colour(body):
    me=body.data
    attr=me.color_attributes.new('Col','BYTE_COLOR','CORNER')
    counts={}
    for k,p in enumerate(me.polygons):
        name=region(tuple(p.center))
        counts[name]=counts.get(name,0)+1
        col=COL[name]
        if name!='skin':
            j=1+.045*math.sin(k*12.9898)                     # faint painted variation
            col=tuple(min(1,v*j) for v in col)
        for li in p.loop_indices:attr.data[li].color=(*col,1)
        p.material_index=0
    me.color_attributes.active_color=attr
    body['regions']=json.dumps(counts)
    AUDIT['face_regions']=counts


def face_plates(body):
    """Eyes, brows and mouth as small flat plates laid on the face by ray
    cast (Meshy's fine eye outlines do not survive the reduction). Four-sided,
    no hidden back face: 10 triangles each. Returned as their own mesh,
    weighted to the head, and merged into the cloth mesh at export."""
    from mathutils.bvhtree import BVHTree
    me=body.data
    tree=BVHTree.FromPolygons([v.co.copy() for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
    verts=[];faces=[];cols=[]
    def plate(x,z,w,h,depth,color):
        p,n,_,_=tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
        up=Vector((0,0,1));u=up.cross(n).normalized();v=n.cross(u).normalized()
        base=len(verts)
        for dz in [-depth*.4,depth]:
            for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]:verts.append(p+n*dz+u*a*w/2+v*b*h/2)
        for f in [(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]:
            faces.append([base+i for i in f]);cols.append(color)
    for s in [-1,1]:
        plate(s*.085,.972,.044,.062,.008,'eye')
        plate(s*.087,1.016,.066,.016,.008,'hair')
    plate(0,.872,.056,.013,.006,'mouth')
    pm=bpy.data.meshes.new('Face_plates');pm.from_pydata([tuple(v) for v in verts],[],faces);pm.update()
    po=bpy.data.objects.new('Face_plates',pm);bpy.context.scene.collection.objects.link(po)
    attr=pm.color_attributes.new('Col','BYTE_COLOR','CORNER')
    for p,c in zip(pm.polygons,cols):
        p.use_smooth=False
        for li in p.loop_indices:attr.data[li].color=(*COL[c],1)
    g=po.vertex_groups.new(name='head');g.add(list(range(len(verts))),1.,'REPLACE')
    po.parent=body.parent;mod=po.modifiers.new('Armature','ARMATURE');mod.object=body.parent
    AUDIT['face_plate_triangles']=sum(len(p.vertices)-2 for p in pm.polygons)
    return po


def split_and_export(body,plates):
    """CREW_Skin: every skin face, vertex colours exported white so the
    game's CrewVertexColor tint (skin _BaseColor #D99259, sickness green) owns
    its colour. CREW_Cloth: everything else plus the face plates."""
    rig=body.parent
    def keep(o,want_skin):
        bm=bmesh.new();bm.from_mesh(o.data)
        doomed=[f for f in bm.faces if (region(tuple(f.calc_center_median()))=='skin')!=want_skin]
        bmesh.ops.delete(bm,geom=doomed,context='FACES');bm.to_mesh(o.data);bm.free()
    skin=body.copy();skin.data=body.data.copy();bpy.context.scene.collection.objects.link(skin)
    keep(skin,True);keep(body,False)
    skin.name='CREW_Skin';body.name='CREW_Cloth'
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True);plates.select_set(True);bpy.context.view_layer.objects.active=body
    bpy.ops.object.join()
    for o,name in ((body,'Crew_Cloth'),(skin,'Crew_Skin')):
        o.data.color_attributes.active_color=o.data.color_attributes['Col']
        m=bpy.data.materials.new(name);m.use_nodes=True
        vc=m.node_tree.nodes.new('ShaderNodeVertexColor');vc.layer_name='Col'
        bsdf=m.node_tree.nodes['Principled BSDF'];bsdf.inputs['Roughness'].default_value=.85
        m.node_tree.links.new(vc.outputs['Color'],bsdf.inputs['Base Color'])
        o.data.materials.clear();o.data.materials.append(m)
        for p in o.data.polygons:p.use_smooth=False;p.material_index=0
    AUDIT['export_triangles']={'CREW_Cloth':tris(body),'CREW_Skin':tris(skin)}
    AUDIT['triangles_final']=tris(body)+tris(skin)
    # Export: skin white, then restore the preview colour in the .blend.
    col=skin.data.color_attributes['Col'];keep_col=[tuple(c.color) for c in col.data]
    for c in col.data:c.color=(1,1,1,1)
    bpy.ops.object.select_all(action='DESELECT')
    for o in (rig,body,skin):o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/'deckhand-rigged.fbx'),use_selection=True,
        object_types={'MESH','ARMATURE'},axis_forward='-Z',axis_up='Y',add_leaf_bones=False,
        use_armature_deform_only=True,bake_anim=False,use_triangles=True,colors_type='LINEAR',mesh_smooth_type='FACE')
    for c,v in zip(col.data,keep_col):c.color=v
    return body,skin


if __name__=='__main__':
    body=load_and_reduce()
    cut_boundaries(body)
    rig=build_rig()
    missed=bind(body,rig)
    clean_weights(body)
    colour(body)
    plates=face_plates(body)
    split_and_export(body,plates)
    AUDIT['triangles']=AUDIT['triangles_final']
    AUDIT['skin_base_color_srgb']=PALETTE['skin'];AUDIT['rig_bones']=len(rig.data.bones)
    AUDIT['palette_srgb']=PALETTE
    (OUT/'validation.json').write_text(json.dumps(AUDIT,indent=2))
    print(json.dumps(AUDIT,indent=2))
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'tools/blender/source/crew-meshy-v14.blend'))
