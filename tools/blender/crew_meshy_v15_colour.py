"""Colour the paid Meshy model (v15, "Red Bandana Adventure") like the reference.

Meshy delivered shape only (3,095 triangles, T-pose, no texture, UVs or
colours), but built from 40 separate pieces: tunic, sash, knot, headband,
hair, eyes, ears, cuffs, soles and so on. Each piece is identified from its
bounding box and gets one flat colour from the reference sheet, the way the
game colours its crew (vertex colours, no image textures). A mouth and two
plank patches on the tunic, which Meshy left out, are added as small plates.

Outputs crew-meshy-v15/: the coloured .blend source, an unrigged FBX with
vertex colours, and preview renders.
Blender coordinates: X across the shoulders (+X is his left), -Y forward, Z up.
"""
import json
import math
import shutil
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'crew-meshy-v15'
SRC=OUT/'source/meshy-red-bandana-adventure.fbx'
HEIGHT=1.30          # game source height; AstraPlaytestImport rescales to 1.7 m
SLEEVE_END=.22       # arm faces nearer the shoulder than this (Meshy units) are under the sleeve


def srgb(h):
    h=h.lstrip('#');c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)


# Colours picked from the reference sheet (same family as v14).
PALETTE={'skin':'#D99259','linen':'#D8CFBC','wrap':'#E6E0D2','sash':'#D0443A','hair':'#3A2921',
         'eye':'#1C1816','mouth':'#A23B2F','pants':'#2D5664','pantcuff':'#2F6572',
         'sole':'#3E2A20','wood':'#B07A4A','strap':'#5A3A28','patch':'#8A5A36'}
COL={k:srgb(v) for k,v in PALETTE.items()}


def classify(lo,hi,n):
    """Name a Meshy piece from its bounding box (metres, before scaling:
    0.894 m tall, feet at z 0, centred). Order matters."""
    c=(lo+hi)/2;d=hi-lo;ax=abs(c.x)
    if lo.z>.855:return 'hair','tuft'
    if lo.z>.74 and d.z>.1:return 'hair','hair'
    if lo.z>.69 and hi.z<.79 and d.x>.28:return 'sash','headband'
    if .12<ax<.19 and .72<c.z<.79 and d.x<.07:return 'sash','headband knot'
    if c.x>.14 and lo.z>.59 and hi.z<.76:return 'sash','headband tail'
    if .71<c.z<.74 and d.z<.025:return 'hair','brow'
    if .68<c.z<.725 and d.x<.04 and c.y<-.08:return 'eye','eye'
    if c.y<-.1 and .63<c.z<.71:return 'skin','nose'
    if ax>.1 and .63<c.z<.72 and d.x<.07:return 'skin','ear'
    if lo.z>.57 and hi.z>.74 and d.x>.25:return 'skin','head'
    if ax>.43:return 'skin','hand'
    if .34<ax<.39 and d.x<.05:return 'wrap','wrist wrap'
    if ax>.2 and d.x>.25:return 'skin','arm'
    if ax>.14 and lo.z>.44 and hi.z<.6 and d.x<.13:return 'linen','sleeve'
    if n>300:return 'linen','tunic'
    if lo.z>.33 and d.z>.2 and d.x>.3:return 'sash','sash'
    if c.x<0 and .34<c.z<.42 and d.z<.07:return 'sash','sash knot'
    if c.x<0 and .19<lo.z<.22 and hi.z<.38:return 'sash','sash tail'
    if .19<lo.z<.24 and d.z<.04:return 'patch','shorts patch'
    if .14<lo.z<.16 and hi.z<.34:return 'pants','shorts'
    if .12<lo.z<.135 and hi.z<.165:return 'pantcuff','shorts cuff'
    if hi.z<.035:return 'sole','sole'
    if lo.z>.02 and hi.z<.09 and d.y<.06:return 'strap','sandal strap'
    if lo.z>.02 and hi.z<.15:return 'skin','foot'
    return None,'?'


def pieces(bm):
    seen=set();out=[]
    for f in bm.faces:
        if f.index in seen:continue
        stack=[f];comp=[]
        while stack:
            g=stack.pop()
            if g.index in seen:continue
            seen.add(g.index);comp.append(g)
            stack+=[h for e in g.edges for h in e.link_faces if h.index not in seen]
        out.append(comp)
    return out


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(SRC))
    o=[o for o in bpy.data.objects if o.type=='MESH'][0];o.name='Deckhand_v15'
    me=o.data
    # Bake the import transform, centre, feet on the ground.
    me.transform(o.matrix_world);o.matrix_world.identity()
    pts=[v.co for v in me.vertices]
    lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
    me.transform(__import__('mathutils').Matrix.Translation(-Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))))
    native_h=hi.z-lo.z

    bm=bmesh.new();bm.from_mesh(me)
    face_col={};report=[];unknown=[]
    for comp in pieces(bm):
        vs={v for f in comp for v in f.verts}
        plo=Vector([min(v.co[i] for v in vs) for i in range(3)]);phi=Vector([max(v.co[i] for v in vs) for i in range(3)])
        col,label=classify(plo,phi,len(comp))
        if col is None:unknown.append((len(comp),tuple(plo),tuple(phi)))
        for f in comp:
            name=col
            if label=='foot' and f.calc_center_median().z<.058:name='wood'   # wooden sandal block
            # The arm tube runs on inside the sleeve to the shoulder. Paint that hidden
            # part linen, like the sleeve, so a raised arm poking through doesn't show skin.
            if label=='arm' and abs(f.calc_center_median().x)<SLEEVE_END:name='linen'
            face_col[f.index]=name
        report.append((label,col,len(comp)))
    bm.free()
    assert not unknown,unknown

    # Mouth and tunic patches: small plates laid on the surface by ray cast.
    tree=BVHTree.FromPolygons([v.co.copy() for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
    verts=[];faces=[];pcol=[]
    def plate(x,z,w,h,depth,color,tilt=0.):
        p,n,_,_=tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
        up=Vector((math.sin(tilt),0,math.cos(tilt)));u=up.cross(n).normalized();v=n.cross(u).normalized()
        base=len(verts)
        for dz in [-depth*.4,depth]:
            for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]:verts.append(p+n*dz+u*a*w/2+v*b*h/2)
        for f in [(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]:faces.append([base+i for i in f]);pcol.append(color)
    plate(-.005,.617,.04,.009,.004,'mouth')
    plate(.075,.435,.07,.018,.005,'patch',tilt=-.25)         # two planks on his left front
    plate(.08,.405,.066,.017,.005,'patch',tilt=.15)
    plate(.078,.42,.006,.075,.0065,'strap')                     # the stitch across them
    base=len(me.vertices)
    bm=bmesh.new();bm.from_mesh(me)
    nv=[bm.verts.new(p) for p in verts];bm.verts.ensure_lookup_table()
    first=len(bm.faces)
    for f in faces:bm.faces.new([nv[i] for i in f])
    bm.to_mesh(me);bm.free()
    for i,c in enumerate(pcol):face_col[first+i]=c

    # Scale to game height, flat shading, vertex colours with faint per-face
    # variation on cloth (skin stays flat: the game tints it).
    me.transform(__import__('mathutils').Matrix.Scale(HEIGHT/native_h,4))
    attr=me.color_attributes.new('Col','BYTE_COLOR','CORNER')
    for p in me.polygons:
        p.use_smooth=False
        name=face_col[p.index];col=COL[name]
        if name not in('skin','eye','mouth'):
            j=1+.045*math.sin(p.index*12.9898);col=tuple(min(1,x*j) for x in col)
        for li in p.loop_indices:attr.data[li].color=(*col,1)
    me.color_attributes.active_color=attr
    mat=bpy.data.materials.new('Crew_VertexColour')
    mat.use_nodes=True
    vc=mat.node_tree.nodes.new('ShaderNodeVertexColor');vc.layer_name='Col'
    bsdf=mat.node_tree.nodes['Principled BSDF'];bsdf.inputs['Roughness'].default_value=.85
    mat.node_tree.links.new(vc.outputs['Color'],bsdf.inputs['Base Color'])
    me.materials.clear();me.materials.append(mat)

    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.export_scene.fbx(filepath=str(OUT/'deckhand-v15-coloured.fbx'),use_selection=True,object_types={'MESH'},
        axis_forward='-Z',axis_up='Y',use_triangles=True,colors_type='SRGB',mesh_smooth_type='FACE')
    (ROOT/'tools/blender/source').mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'tools/blender/source/crew-meshy-v15.blend'))
    counts={}
    for label,col,n in report:counts.setdefault(col,[]).append(label)
    summary={'source_triangles':3095,'pieces':len(report),'triangles':sum(len(p.vertices)-2 for p in me.polygons),
             'height_m':HEIGHT,'pieces_by_colour':{k:sorted(set(v)) for k,v in counts.items()}}
    (OUT/'validation.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
