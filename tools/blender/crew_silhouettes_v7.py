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

    def body(self,rows,n=8,flat=.0,phase=None):
        """Horizontal rings: (z, y, rx, ry[, tilt]). tilt slants the ring in z
        across x (for a diagonal hem). flat>0 squares off the polygon."""
        rings=[]
        for row in rows:
            z,y,rx,ry=row[:4];tilt=row[4] if len(row)>4 else 0
            pts=[]
            for i in range(n):
                a=i*math.tau/n+(math.pi/n if phase is None else phase)
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


def feet(m,x,y,rx,ry,top=.07):
    for s in [-1,1]:
        m.body([(0,y,rx,ry),(top,y,rx,ry),(top+.04,y+.04,rx*.7,ry*.45)],8,flat=.6)
        m.v[-24:]=[(px+s*x,py,pz) for px,py,pz in m.v[-24:]]


def fists(m,x,y,z,r):
    for s in [-1,1]:
        m.body([(z-r,y,r*.6,r*.6),(z-r*.6,y,r,r*.95),(z+r*.6,y,r,r*.95),(z+r,y,r*.7,r*.7)],8,flat=.25)
        m.v[-32:]=[(px+s*x,py,pz) for px,py,pz in m.v[-32:]]


def bean():
    """D: head and body are one bean, no neck; thick stubby legs, mitten arms
    held clear of the body, headcloth tails as the hook."""
    m=Shape()
    feet(m,.12,-.05,.08,.14)
    m.mirror_limb([((.12,0,.07),.07),((.12,0,.30),.08)])
    m.body([(.24,0,.19,.16),(.34,-.01,.26,.21),(.60,-.02,.285,.225),(.90,-.02,.265,.21),
            (1.10,-.01,.22,.19),(1.22,0,.155,.14),(1.28,0,.07,.07)],10)
    m.limb([((0,-.21,.99),.045),((0,-.27,.96),.035)],6)
    m.body([(1.04,-.01,.235,.20),(1.11,-.01,.228,.195)],10)
    m.limb([((.20,.08,1.08),.035,.5),((.31,.13,1.02),.032,.5),((.38,.15,.93),.022,.5)])
    m.limb([((.18,.11,1.07),.03,.5),((.25,.18,.98),.028,.5),((.28,.21,.90),.02,.5)])
    m.mirror_limb([((.24,-.02,.86),.072),((.34,-.04,.70),.066),((.37,-.05,.62),.06)])
    fists(m,.38,-.05,.56,.08)
    return m


def bighead():
    """E: a head about 40% of the height on a compact body. At 24 px the head
    carries everything: face, headcloth, sickness tint."""
    m=Shape()
    feet(m,.09,-.04,.07,.12)
    m.mirror_limb([((.09,0,.07),.06),((.095,0,.34),.07)])
    m.body([(.30,0,.175,.14,.15),(.52,0,.15,.12),(.84,-.01,.19,.14),(.95,-.01,.13,.10),(1.0,0,.08,.07)],8,flat=.3)
    m.body([(.98,-.01,.10,.10),(1.04,-.02,.24,.22),(1.25,-.02,.29,.27),(1.45,-.01,.26,.245),
            (1.56,0,.15,.14),(1.59,0,.05,.05)],10)
    m.limb([((0,-.28,1.22),.05),((0,-.33,1.19),.04)],6)
    m.body([(1.31,-.01,.30,.28),(1.39,-.01,.295,.275)],10)
    m.limb([((.24,.14,1.36),.045,.5),((.38,.22,1.28),.042,.5),((.46,.26,1.16),.03,.5)])
    m.limb([((.22,.18,1.34),.04,.5),((.30,.28,1.22),.036,.5),((.33,.32,1.10),.026,.5)])
    m.limb([((.02,-.08,1.55),.07),((.05,-.16,1.62),.04),((.08,-.22,1.62),.012)],6)
    m.mirror_limb([((.19,0,.88),.062),((.28,-.02,.70),.058),((.30,-.03,.62),.055)])
    fists(m,.31,-.03,.56,.075)
    return m


def block():
    """F: square torso, wide planted stance, heavy arms with clear gaps, and a
    wide conical straw hat: the biggest single silhouette hook of the set."""
    m=Shape()
    feet(m,.17,-.05,.09,.15)
    m.mirror_limb([((.17,0,.07),.075),((.16,0,.30),.085),((.15,0,.47),.10)])
    m.body([(.44,0,.27,.17),(.60,0,.26,.16),(1.00,-.02,.30,.18),(1.10,-.02,.26,.16),
            (1.14,-.02,.09,.08)],8,flat=.8)
    m.body([(1.12,-.03,.10,.10),(1.16,-.03,.13,.13),(1.36,-.03,.13,.13),(1.40,-.03,.11,.11)],8,flat=.6)
    m.limb([((0,-.16,1.26),.035),((0,-.21,1.23),.025)],5)
    m.body([(1.34,-.03,.42,.42),(1.37,-.03,.42,.42),(1.50,-.03,.12,.12),(1.57,-.03,.02,.02)],12)
    m.mirror_limb([((.36,-.02,1.02),.08),((.43,-.03,.76),.075),((.45,-.06,.60),.07)])
    fists(m,.46,-.07,.51,.09)
    return m


def poncho():
    """G: a diamond poncho gives a wide middle with points at the sides; the
    forearms poke out below it and a sprouting topknot tops the head."""
    m=Shape()
    feet(m,.10,-.05,.07,.13)
    m.mirror_limb([((.10,0,.07),.055),((.105,0,.30),.065),((.11,0,.48),.08)])
    m.body([(.40,0,.18,.13),(.66,0,.16,.12)],8)
    m.body([(.60,-.01,.06,.05),(.90,-.01,.46,.27),(1.05,-.02,.21,.16),(1.12,-.02,.09,.08)],4,phase=0)
    m.body([(1.09,-.02,.08,.08),(1.15,-.03,.165,.155),(1.30,-.03,.175,.165),
            (1.42,-.02,.13,.125),(1.46,-.02,.05,.05)],10)
    m.limb([((0,-.19,1.27),.04),((0,-.245,1.24),.03)],6)
    m.limb([((0,0,1.43),.06),((0,.02,1.56),.045),((.0,.07,1.66),.012)],6)
    m.mirror_limb([((.24,-.08,.88),.065),((.31,-.14,.70),.06),((.33,-.15,.64),.058)])
    fists(m,.34,-.16,.58,.078)
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
CONCEPTS=[('v6',None),('A-hauler',hauler),('B-pear',pear),('C-wiry',wiry),
          ('D-bean',bean),('E-bighead',bighead),('F-block',block),('G-poncho',poncho)]
for key,build in CONCEPTS:
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
