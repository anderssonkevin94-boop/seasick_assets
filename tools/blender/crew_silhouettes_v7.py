"""Three silhouette studies for the next villager, next to the current v6.

Quick 3D blockouts (not production meshes) rendered as flat black shapes, so
the choice is made on shape alone: A "Hauler", B "Pear", C "Wiry". Each is
scaled to the same 1.7 m the game gives every crew model, so the comparison
is what the phone will show.

Blender coordinates: X across the shoulders, -Y forward, Z up.
Run: blender -b -P tools/blender/crew_silhouettes_v7.py  (or python with bpy)
"""
import math
from pathlib import Path
import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'crew-silhouettes-v7'
OUT.mkdir(parents=True,exist_ok=True)
V6=ROOT/'crew-islander-v6/deckhand-rigged.fbx'


class Shape:
    """Accumulates closed lofts into one mesh."""
    def __init__(self):self.v=[];self.f=[]

    def ring(self,pts):
        base=len(self.v);self.v+=[tuple(p) for p in pts];return list(range(base,base+len(pts)))

    def loft(self,rings):
        ids=[self.ring(r) for r in rings]
        for a,b in zip(ids,ids[1:]):
            n=len(a)
            for i in range(n):self.f.append([a[i],a[(i+1)%n],b[(i+1)%n],b[i]])
        self.f.append(list(reversed(ids[0])));self.f.append(ids[-1])

    def body(self,rows,n=8,flat=.0):
        """Horizontal rings: (z, y, rx, ry[, tilt]). tilt slants the ring in z
        across x (for a diagonal hem). flat>0 squares off the polygon."""
        rings=[]
        for row in rows:
            z,y,rx,ry=row[:4];tilt=row[4] if len(row)>4 else 0
            pts=[]
            for i in range(n):
                a=i*math.tau/n+math.pi/n
                c,s=math.cos(a),math.sin(a)
                k=1/max(abs(c),abs(s))**flat if flat else 1
                x=rx*c*k;pts.append((x,y+ry*s*k,z+tilt*x))
            rings.append(pts)
        self.loft(rings)

    def limb(self,path,n=6):
        """Rings perpendicular to a polyline of (point, radius[, depth ratio])."""
        rings=[]
        for j,p in enumerate(path):
            c=Vector(p[0]);r=p[1];ratio=p[2] if len(p)>2 else 1
            d=Vector(path[min(j+1,len(path)-1)][0])-Vector(path[max(j-1,0)][0])
            d.normalize()
            up=Vector((0,1,0)) if abs(d.y)<.9 else Vector((1,0,0))
            v=(up-d*up.dot(d)).normalized();u=v.cross(d).normalized()
            rings.append([c+u*r*math.cos(i*math.tau/n)+v*r*ratio*math.sin(i*math.tau/n) for i in range(n)])
        self.loft(rings)

    def mirror_limb(self,path,n=6):
        for s in [-1,1]:
            self.limb([((s*p[0][0],p[0][1],p[0][2]),)+tuple(p[1:]) for p in path],n)

    def object(self,name):
        me=bpy.data.meshes.new(name);me.from_pydata(self.v,[],self.f);me.update()
        o=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(o)
        return o


def hauler():
    """A: inverted-wedge torso, huge forearms and fists, small head pushed
    forward, soft bowed knees. A strong worker who carries the island."""
    m=Shape()
    for s in [-1,1]:
        m.body([(0,-.05,.085,.16),(.07,-.05,.085,.16),(.11,-.01,.055,.07)],8,flat=.6)
        m.v[-24:]=[(x+s*.15,y,z) for x,y,z in m.v[-24:]]
    m.mirror_limb([((.15,0,.08),.045),((.165,-.03,.33),.06),((.14,-.01,.45),.10),((.11,0,.60),.12)])
    # Wrap tunic: slanted hem, pinched waist, broad chest thrust forward.
    m.body([(.50,.0,.22,.16,.30),(.66,-.01,.16,.12),(.88,-.05,.31,.19),
            (1.03,-.08,.36,.19),(1.10,-.09,.24,.14),(1.13,-.10,.08,.07)],8,flat=.35)
    m.body([(1.09,-.14,.07,.07),(1.15,-.15,.115,.115),(1.27,-.16,.125,.125),
            (1.37,-.15,.10,.10),(1.40,-.15,.05,.05)],8,flat=.5)
    m.limb([((0,-.265,1.25),.035),((0,-.31,1.22),.025)],5)
    m.body([(1.29,-.15,.14,.14),(1.34,-.15,.14,.14)],8,flat=.5)
    m.limb([((.10,-.07,1.31),.03,.5),((.19,.00,1.25),.028,.5),((.25,.04,1.17),.02,.5)])
    m.mirror_limb([((.33,-.08,1.02),.085),((.40,-.10,.76),.08),((.41,-.13,.62),.10),
                   ((.41,-.16,.50),.05)])
    for s in [-1,1]:
        m.body([(.36,-.17,.06,.06),(.40,-.17,.095,.09),(.48,-.17,.10,.095),(.52,-.17,.07,.07)],8,flat=.25)
        m.v[-32:]=[(x+s*.41,y,z) for x,y,z in m.v[-32:]]
    return m


def pear():
    """B: bottom-heavy bell shape, narrow shoulders, stubby arms, big feet,
    round head with a ball nose and a topknot. Comic and warm."""
    m=Shape()
    for s in [-1,1]:
        m.body([(0,-.06,.085,.155),(.07,-.06,.085,.155),(.11,-.02,.05,.06)],8,flat=.6)
        m.v[-24:]=[(x+s*.11,y,z) for x,y,z in m.v[-24:]]
    m.mirror_limb([((.11,0,.08),.045),((.12,0,.24),.05),((.13,0,.36),.07)])
    m.body([(.32,-.02,.22,.18),(.44,-.05,.285,.235),(.60,-.05,.27,.22),
            (.76,-.02,.20,.16),(.90,.01,.14,.115),(.95,.01,.07,.07)],10)
    m.body([(.93,0,.08,.08),(.99,-.01,.16,.15),(1.12,-.01,.19,.18),
            (1.24,.0,.165,.155),(1.32,.0,.10,.10),(1.345,.0,.04,.04)],10)
    m.body([(1.03,-.19,.05,.045),(1.08,-.215,.06,.055),(1.13,-.19,.045,.04)],8)
    m.body([(1.32,.03,.05,.05),(1.37,.03,.07,.07),(1.43,.03,.055,.055),(1.45,.03,.02,.02)],8)
    # Stubby arms held out from the bell so they still read at phone size.
    m.mirror_limb([((.14,0,.88),.058),((.28,-.03,.76),.052),((.36,-.07,.66),.046)])
    for s in [-1,1]:
        m.body([(.57,-.08,.045,.045),(.60,-.08,.068,.064),(.66,-.08,.066,.062),(.685,-.08,.04,.04)],8,flat=.25)
        m.v[-32:]=[(x+s*.375,y,z) for x,y,z in m.v[-32:]]
    return m


def wiry():
    """C: lanky and stooped: long limbs with knobbly knees and elbows, a tall
    wedge head with a big jaw and a long nose, and a trailing headcloth tail."""
    m=Shape()
    for s in [-1,1]:
        m.body([(0,-.08,.06,.17),(.05,-.08,.06,.17),(.09,-.02,.04,.06)],8,flat=.6)
        m.v[-24:]=[(x+s*.12,y,z) for x,y,z in m.v[-24:]]
    m.mirror_limb([((.12,0,.07),.035),((.125,-.05,.46),.04),((.125,-.055,.50),.058),
                   ((.125,-.05,.54),.045),((.11,-.01,.80),.055)])
    m.body([(.76,.0,.155,.11),(.92,-.01,.13,.10),(1.10,-.03,.17,.11),
            (1.23,-.08,.20,.12),(1.28,-.10,.10,.08)],8,flat=.35)
    m.limb([((0,-.09,1.25),.045),((0,-.15,1.40),.04)])
    m.body([(1.37,-.17,.12,.11),(1.44,-.18,.145,.13),(1.56,-.17,.12,.12),
            (1.68,-.16,.09,.10),(1.75,-.15,.045,.05)],8,flat=.4)
    m.limb([((0,-.28,1.56),.032),((0,-.37,1.49),.018)],5)
    m.body([(1.60,-.16,.115,.115),(1.645,-.16,.105,.11)],8,flat=.4)
    m.limb([((0,-.05,1.63),.03,.5),((0,.06,1.54),.03,.5),((.02,.12,1.40),.02,.5)])
    m.mirror_limb([((.20,-.08,1.21),.04),((.245,-.05,.93),.042),((.25,-.055,.90),.052),
                   ((.255,-.06,.87),.038),((.27,-.11,.64),.03)])
    for s in [-1,1]:
        m.body([(.50,-.12,.07,.045),(.62,-.12,.075,.05)],8,flat=.6)
        m.v[-16:]=[(x+s*.275,y,z) for x,y,z in m.v[-16:]]
    return m


def normalise(objs,height=1.7):
    top=max((o.matrix_world@Vector(c)).z for o in objs for c in o.bound_box)
    for o in objs:o.scale=[v*height/top for v in o.scale]
    bpy.context.view_layer.update()


def clear():
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)


def render(name,eye,size,scale=2.1,target=(0,0,.85)):
    cam.location=eye
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cd.ortho_scale=scale
    scene.render.resolution_x,scene.render.resolution_y=size
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)


def srgb(h):
    h=h.lstrip('#');c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return [v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c]


clear()
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH'
sh=scene.display.shading
sh.light='FLAT';sh.color_type='SINGLE';sh.single_color=srgb('#1C2428')
sh.background_type='WORLD';sh.show_backface_culling=False
scene.world=scene.world or bpy.data.worlds.new('Paper')
scene.world.color=srgb('#ECE5D5')
scene.view_settings.view_transform='Standard'
scene.display.render_aa='16'
scene.render.image_settings.file_format='PNG';scene.render.resolution_percentage=100
cd=bpy.data.cameras.new('Sil');cam=bpy.data.objects.new('Sil',cd);scene.collection.objects.link(cam)
scene.camera=cam;cd.type='ORTHO'

VIEWS=[('front34',(3,-5,2.6),(500,560)),('side',(-6,0,.85),(500,560)),
       ('front',(0,-6,.85),(500,560)),('phone',(3,-5,2.6),(40,44))]
for key,build in [('v6',None),('A-hauler',hauler),('B-pear',pear),('C-wiry',wiry)]:
    for o in list(bpy.data.objects):
        if o!=cam:bpy.data.objects.remove(o,do_unlink=True)
    if build is None:
        bpy.ops.import_scene.fbx(filepath=str(V6))
        objs=[o for o in bpy.data.objects if o.type=='MESH']
        for o in [o for o in bpy.data.objects if o.type=='ARMATURE']:o.hide_render=True
        low=min((o.matrix_world@Vector(c)).z for o in objs for c in o.bound_box)
        for o in bpy.data.objects:
            if o.parent is None and o!=cam:o.location.z-=low
        bpy.context.view_layer.update()
    else:
        objs=[build().object(key)]
    normalise(objs)
    for view,eye,size in VIEWS:render(f'{key}-{view}',eye,size)
