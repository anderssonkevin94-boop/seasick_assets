"""Task animations for the v15 deckhand: one clip per building job and per
camp task, on the game's 16-bone skeleton.

Each clip is authored as a few key poses of TARGETS, not bone angles: where
each fist is (and which way the tool in it points), where the feet stand,
how far the hips drop and the spine bends. Every frame is solved from those
targets (two-bone IK for arms and legs, feet planted unless a clip moves
them) and baked, so fists stay on their tools and feet stay on the ground.

Tools follow the game's tool frame (`VillagerActing.BuildTool`): origin in
the middle of the fist, +Y up the haft, +Z the working side. Tools go in his
RIGHT hand, which is the bone NAMED `hand.L` (Blender -X), as in the game.
Sizes are the game's fallback tools scaled from its 1.7 m body to this
1.30 m source. Props are for the preview renders only and are not exported.

Outputs crew-meshy-v15/anims/: deckhand-v15-anims.fbx (rig, CREW_Skin /
CREW_Cloth and every clip as its own take), a GIF and a filmstrip per clip, clips.json.
Blender coordinates: X across the shoulders (+X is his left), -Y forward, Z up.
"""
import json
import math
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix, Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_meshy_v15_colour as C
import crew_meshy_v15_pose as P

ROOT=C.ROOT;OUT=C.OUT/'anims';K=P.K
FPS=30
TOOL_SCALE=C.HEIGHT/1.7            # game tools are sized for the 1.7 m body

# Anatomical sides -> bone suffixes (his right hand is the bone named .L, on -X).
RIGHT,LEFT='.L','.R'
SIDE_SIGN={RIGHT:-1,LEFT:1}


def V(*a):return Vector(a)


def nrm(v):v=Vector(v);return v.normalized() if v.length>1e-9 else Vector((0,0,1))


def sag(hy,hz):
    """A haft direction in the sagittal plane and the working face that leads
    a downward swing: (haft, face)."""
    h=nrm((0,hy,hz));return h,Vector((0,-h.z,h.y))


def rot(p,y,r):
    """Character-axis rotation from degrees: pitch forward (+X), yaw to his
    left (+Z), roll to his left (-Y)."""
    return (Matrix.Rotation(math.radians(y),3,'Z')@Matrix.Rotation(math.radians(p),3,'X')
            @Matrix.Rotation(math.radians(r),3,'Y'))


# ------------------------------------------------------------------ the solver
class Solver:
    def __init__(self,rig):
        self.rig=rig;self.b=rig.data.bones;self.pb=rig.pose.bones
        self.L={n:self.b[n].length for n in P.REST};self.miss={};self.twist_clamped={}
        # fist centre in each hand bone's rest space
        self.fist_local={}
        for side,s in SIDE_SIGN.items():
            hb=self.b['hand'+side]
            centre=P.P(s*.44,0,.513)
            self.fist_local[side]=hb.matrix_local.inverted()@centre

    def reset(self):
        self.miss={};self.twist_clamped={}
        for p in self.pb:p.matrix_basis=Matrix.Identity(4)
        bpy.context.view_layer.update()

    def set_rot(self,name,R):
        """World rotation R (3x3) applied on top of the rest orientation,
        pinned at the bone's current head."""
        pb=self.pb[name];head=pb.head.copy()
        m=(R@self.b[name].matrix_local.to_3x3()).to_4x4();m.translation=head
        pb.matrix=m;bpy.context.view_layer.update()

    def orient(self,name,direction,up,rest_up=V(0,-1,0)):
        """Point the bone along `direction`, turning it about its own axis so
        its rest `rest_up` side faces `up`."""
        R0=self.b[name].matrix_local.to_3x3()
        a0=R0@V(0,1,0);b0=(rest_up-a0*rest_up.dot(a0)).normalized();c0=a0.cross(b0)
        a1=nrm(direction);u=Vector(up);b1=u-a1*u.dot(a1)
        if b1.length<1e-6:b1=b0-a1*b0.dot(a1)
        b1.normalize();c1=a1.cross(b1)
        Fr=Matrix((a0,b0,c0)).transposed();Ft=Matrix((a1,b1,c1)).transposed()
        self.set_rot(name,Ft@Fr.transposed())

    def two_bone(self,a,la,lb,target,hint):
        """Joint position for a two-bone chain from a to target."""
        d=target-a;dist=max(abs(la-lb)+1e-4,min(la+lb-1e-4,d.length));n=d.normalized()
        x=(la*la-lb*lb+dist*dist)/(2*dist);h=math.sqrt(max(0.,la*la-x*x))
        perp=Vector(hint)-n*Vector(hint).dot(n)
        if perp.length<1e-6:perp=V(0,-1,0)-n*n.y
        return a+n*x+perp.normalized()*h,a+n*dist

    PRONATION=math.radians(85)       # forearm twist either way from neutral

    def arm(self,side,grip,face,haft,elbow):
        """Place the fist centre at `grip`, knuckles along `face`, thumb along
        `haft`, the elbow bending toward `elbow` (a hint direction).

        Anatomy: the upper arm rolls with the elbow's hinge (its flexion side
        faces the forearm), the forearm twists toward the thumb only within
        +-85 degrees of neutral, and the hand keeps the forearm's twist (a
        wrist bends, it does not turn). Misses (a target out of reach) are
        recorded in self.miss."""
        s=SIDE_SIGN[side];u,f,h='upper_arm'+side,'forearm'+side,'hand'+side
        face=nrm(face);haft=Vector(haft);haft=(haft-face*haft.dot(face)).normalized()
        palm=(haft.cross(face) if s<0 else face.cross(haft))
        wrist=Vector(grip)-face*(.07*K)-palm*(.012*K)
        sh=self.pb[u].head.copy()
        el,wr=self.two_bone(sh,self.L[u],self.L[f],wrist,elbow)
        self.miss[side]=max(self.miss.get(side,0),(wr-wrist).length)
        ua=el-sh;fa=wr-el;ua_n=ua.normalized();fa_n=fa.normalized()
        bend=fa-ua_n*fa.dot(ua_n)
        if bend.length<1e-4:                          # straight arm: flex side away from the elbow hint
            bend=-(Vector(elbow)-ua_n*Vector(elbow).dot(ua_n))
        self.orient(u,ua,bend)                        # upper arm: flexion side toward the forearm
        ref=-ua_n-fa_n*(-ua_n).dot(fa_n)              # neutral thumb: carried from the upper arm across the hinge
        if ref.length<1e-4:ref=bend-fa_n*bend.dot(fa_n)
        ref.normalize()
        want=haft-fa_n*haft.dot(fa_n)
        want=want.normalized() if want.length>1e-4 else ref
        ang=ref.angle(want)
        if ang>self.PRONATION:                        # clamp the twist to what a forearm can do
            axis=ref.cross(want);axis=axis.normalized() if axis.length>1e-6 else fa_n
            want=Matrix.Rotation(self.PRONATION,3,axis)@ref
            self.twist_clamped[side]=max(self.twist_clamped.get(side,0),math.degrees(ang))
        self.orient(f,fa,want)
        # The hand holds the tool as asked until the forearm runs out of twist;
        # past the limit it turns back by exactly the excess (continuous: no pop).
        asked=haft-fa_n*haft.dot(fa_n)
        if ang>self.PRONATION and asked.length>1e-6:
            hand_up=asked.normalized().rotation_difference(want)@haft
        else:hand_up=haft
        self.orient(h,face,hand_up)

    def leg(self,side,ankle,foot_dir,knee):
        t,sh,ft='thigh'+side,'shin'+side,'foot'+side
        hip=self.pb[t].head.copy()
        kn,an=self.two_bone(hip,self.L[t],self.L[sh],Vector(ankle),knee)
        self.orient(t,kn-hip,knee);self.orient(sh,an-kn,knee);self.orient(ft,foot_dir,V(0,0,1),rest_up=V(0,0,1))

    def fist(self,side):
        """World fist centre and (haft, face) of a posed hand."""
        m=self.pb['hand'+side].matrix;R=m.to_3x3();R0=self.b['hand'+side].matrix_local.to_3x3()
        d=R@R0.inverted()
        return m@self.fist_local[side],d@V(0,-1,0),d@(R0@V(0,1,0))

    def pose(self,q):
        """Apply one pose dict q (see DEFAULT)."""
        self.reset()
        G=Matrix.Rotation(math.radians(q['yaw']),3,'Z')
        root=self.pb['root'];m=(G@self.b['root'].matrix_local.to_3x3()).to_4x4()
        m.translation=G@(self.b['root'].head_local+Vector(q['root']));root.matrix=m
        bpy.context.view_layer.update()
        Rp=G@rot(*q['pelvis']);self.set_rot('pelvis',Rp)
        Rs=Rp@rot(*q['spine']);self.set_rot('spine',Rs)
        self.set_rot('head',Rs@rot(*q['head']))
        for side,s,key in((RIGHT,-1,'rf'),(LEFT,1,'lf')):
            f=q[key];rest=self.b['foot'+side].head_local
            ankle=G@(rest+Vector(f[:3]))
            pitch=math.radians(f[3]) if len(f)>3 else 0
            fd=G@(Matrix.Rotation(pitch,3,'X')@V(0,-.97,-.24))
            self.leg(side,ankle,fd,G@(V(s*.15,-1,0)))
        w=float(q.get('hands_on_spine',0))
        if w>0:                                     # hand targets authored standing (rest), carried by the spine: a load parented there stays on the arms
            M=self.pb['spine'].matrix@self.b['spine'].matrix_local.inverted()
            if w<1:                                 # part way: blend from the world (G) frame to the spine's, so a clip can hand over smoothly
                Mg=G.to_4x4();loc=Mg.translation.lerp(M.translation,w)
                M=Matrix.Translation(loc)@Mg.to_quaternion().slerp(M.to_quaternion(),w).to_matrix().to_4x4()
            R=M.to_3x3()
            for side,key in((RIGHT,'rh'),(LEFT,'lh')):
                r=q[key];self.arm(side,M@Vector(r['grip']),R@Vector(r['face']),R@Vector(r['haft']),R@Vector(r['elbow']))
            return
        r=q['rh'];self.arm(RIGHT,G@Vector(r['grip']),G@Vector(r['face']),G@Vector(r['haft']),G@Vector(r['elbow']))
        l=q['lh']
        if 'on_tool' in l:                          # second hand on the right hand's haft
            c,haft,face=self.fist(RIGHT)
            self.arm(LEFT,c+haft*l['on_tool'],face,haft,G@Vector(l['elbow']))
        elif 'tool_pt' in l:                        # second hand anywhere on the held tool (tool frame, metres)
            c,haft,face=self.fist(RIGHT);x,y,z=l['tool_pt'];X=haft.cross(face)
            self.arm(LEFT,c+X*x+haft*y+face*z,G@Vector(l['face']),G@Vector(l['haft']),G@Vector(l['elbow']))
        else:
            self.arm(LEFT,G@Vector(l['grip']),G@Vector(l['face']),G@Vector(l['haft']),G@Vector(l['elbow']))


# ---------------------------------------------------------------- the clips
def hand(grip,face,haft,elbow):return {'grip':V(*grip),'face':nrm(face),'haft':Vector(haft),'elbow':V(*elbow)}


RELAX_R=hand((-.35,-.07,.45),(-.2,-.25,-1),(0,-1,0),(-.6,.7,0))
RELAX_L=hand((.35,-.07,.45),(.2,-.25,-1),(0,-1,0),(.6,.7,0))
DEFAULT={'hands_on_spine':0.,'root':V(0,0,0),'yaw':0.,'pelvis':(0,0,0),'spine':(0,0,0),'head':(0,0,0),
         'rf':(0,0,0,0),'lf':(0,0,0,0),'rh':RELAX_R,'lh':RELAX_L}


def swing_hand(grip,hy,hz,elbow=(-.6,.5,-.3)):
    h,f=sag(hy,hz);return hand(grip,f,h,elbow)


def mix(a,b,t):
    """Blend two pose values of the same shape."""
    if isinstance(a,dict):
        if set(a)!=set(b):return a if t<.5 else b
        return {k:mix(a[k],b[k],t) for k in a}
    if isinstance(a,Vector):return a.lerp(b,t)
    if isinstance(a,(tuple,list)):return tuple(x+(y-x)*t for x,y in zip(a,b))
    return a+(b-a)*t


def sample(keys,t,loop):
    """Pose at phase t (0..1): keys is either a function of t, or
    [(t, pose)] eased between keys."""
    if callable(keys):return keys(t)
    ks=sorted(keys,key=lambda k:k[0])
    if loop:ks=ks+[(ks[0][0]+1,ks[0][1])]
    if t<=ks[0][0]:return ks[0][1]
    for (t0,a),(t1,b) in zip(ks,ks[1:]):
        if t0<=t<=t1:
            u=(t-t0)/max(1e-6,t1-t0);u=u*u*(3-2*u)
            return mix(a,b,u)
    return ks[-1][1]


def K_(**kw):
    q=dict(DEFAULT);q.update(kw);return q


CLIPS={}


def clip(name,seconds,keys,loop=True,props=(),rtool=None,ltool=None,what=''):
    CLIPS[name]={'seconds':seconds,'keys':keys,'loop':loop,'props':props,'rtool':rtool,'ltool':ltool,'what':what}


# --- the basics
clip('Idle',2.4,[(0,K_(spine=(1,0,0),head=(-2,-4,0))),
                 (.5,K_(root=V(0,0,-.006),spine=(3,0,0),head=(2,4,0),
                        rh=hand((-.35,-.06,.44),(-.2,-.2,-1),(0,-1,0),(-.6,.7,0)),
                        lh=hand((.35,-.06,.44),(.2,-.2,-1),(0,-1,0),(.6,.7,0))))],what='breathing, weight settling, a glance round')


def walk_pose(t,arms=True,carry=None):
    """In-place walk at phase t: right foot forward at t=0."""
    a=t*2*math.pi;c,sn=math.cos(a),math.sin(a);stride=.11
    q=K_()
    q['rf']=(0,-stride*c,.045*max(0,-sn),-12*c)        # swing foot (moving forward) lifts
    q['lf']=(0,stride*c,.045*max(0,sn),12*c)
    q['root']=V(0,0,-.012-.016*abs(c))
    q['spine']=(4,-5*c,0);q['pelvis']=(0,6*c,0)
    if arms:
        q['rh']=hand((-.34,-.07+.10*c,.46),(-.15,.2*c-.2,-1),(0,-1,0),(-.6,.7,0))
        q['lh']=hand((.34,-.07-.10*c,.46),(.15,-.2*c-.2,-1),(0,-1,0),(.6,.7,0))
    if carry:carry(q,c)
    return q


clip('Walk',.9,walk_pose,what='in place: the game moves him; stride about 0.44 m a cycle')

# --- camp tasks
# Chop: felling a standing tree (Astra's Tree_B1 at its smallest game size),
# one-handed, swung flat like a bat: cocked up in front of his right shoulder,
# the body wound right; the fist drops to chest height with the head trailing
# level behind him; the body unwinds and the axe sweeps round flat into the
# trunk's right flank, the edge travelling straight at the trunk's centre;
# it bites and holds, is pulled free, and goes back up the way it came.
# One-handed on purpose: with his short arms and round belly every two-handed
# side swing put the upper hand's arm 5-8 cm through his body at contact. The
# axe is in his right hand at the end of the haft, the game's own grip.
# CampWorker.Stand puts him 1.1 m (game) from the trunk's centre: no offset.
# Key poses found by search against crew_v15_anatomy (no clipping, joints in
# range, the haft clear of the trunk) with the blade exactly on the notch.
AXE_EDGE=V(0,.56,.13)*TOOL_SCALE                  # the edge's middle in the tool frame (Astra's manifest)
AXE_SECOND=.11*TOOL_SCALE                          # second hand up the haft (two-handed tools)
CHOP_HEIGHT=.62                                    # the notch, above his feet: his chest, where the arm swings level
TREE_D=.84                                         # 1.1 m (game) at his scale; matches crew_v15_mill.TREE_STAND
TRUNK_R=.27                                        # the bark at his chest height (measured on the placed tree), less a 2 cm bite: see CHOP_BITE
CHOP_BITE=.02
CHOP_AT=145                                        # the notch, degrees round the trunk from his left (180 is its right flank)
CHOP_WIND,CHOP_SLOT,CHOP_SIDE,CHOP_HIT=-35,-28,-6,16   # upper-body twist (degrees, - is to his right): cocked, hands dropped, sweeping, at contact


def axe_hand(edge_at,fist_near,swing,elbow):
    """The right fist and axe frame that put the axe's edge at `edge_at`
    (rig space), the fist as near `fist_near` as the axe allows, the edge
    facing `swing`."""
    swing=nrm(swing);F=Vector(fist_near);f=swing
    for _ in range(12):
        v=Vector(edge_at)-F
        h=nrm(v-f*AXE_EDGE.z)                      # haft direction, the edge offset taken out
        f=nrm(swing-h*swing.dot(h))                # edge facing the swing, square to the haft
        F=Vector(edge_at)-h*AXE_EDGE.y-f*AXE_EDGE.z  # so the fist, haft and face agree exactly
    return {'grip':F,'face':f,'haft':h,'elbow':V(*elbow)}


def chop_keys():
    T=V(0,-TREE_D,CHOP_HEIGHT)
    a=math.radians(CHOP_AT)
    notch=T+V(math.cos(a),math.sin(a),0)*(TRUNK_R-CHOP_BITE)   # the blade 2 cm into the bark
    into=nrm(V(*(T-notch).xy,0))                   # level, straight at the trunk's centre
    haft=Matrix.Rotation(math.radians(12),3,'Z')@V(into.y,-into.x,0)   # square to the swing, a little ahead of it
    haft=nrm(haft+V(0,0,math.tan(math.radians(10))))                 # the head a touch above the fist
    feet=dict(rf=(-.03,.07,0,0),lf=(.03,-.07,0,0))
    def wound(sy,grip,face,haft,elbow,balance):     # a pose with the upper body twisted sy, hand targets turning with it
        R=Matrix.Rotation(math.radians(sy),3,'Z');haft=nrm(haft);face=nrm(face);face=nrm(face-haft*face.dot(haft))
        return K_(root=V(0,0,-.04),**feet,pelvis=(0,sy*.35,0),spine=(4,sy*.65,-2),head=(6,-sy*.75,0),
                  rh=hand(tuple(R@V(*grip)),R@face,R@haft,elbow),lh=balance)
    balance_top=hand((.36,-.30,.60),(.3,-.8,-.3),(0,0,1),(.9,.3,-.2))
    balance_mid=hand((.36,-.22,.62),(.3,-.8,-.3),(0,0,1),(.9,.3,-.2))
    balance_hit=hand((.38,-.10,.52),(.4,-.2,-1),(0,-1,0),(.8,.6,0))
    cocked=wound(CHOP_WIND,(-.30,-.16,.86),(.3,-1,.3),(-.2,.6,.8),(-.9,.2,-.4),balance_top)     # the axe standing up behind his right shoulder
    slot=wound(CHOP_SLOT,(-.46,-.16,.66),(-.3,-1,.1),(-.1,1,.25),(-.5,.1,-.9),balance_mid)      # fist at chest height, the head trailing level behind
    balance_side=hand((.37,-.16,.57),(.35,-.5,-.65),(0,-.5,.5),(.85,.45,-.1))
    side=wound(CHOP_SIDE,(-.34,-.36,.62),(-.2,-1,.2),(-1,-.35,.2),(-.2,.3,-.95),balance_side)   # sweeping round: the axe level, out to his right
    hit_rh=axe_hand(notch,notch-haft*AXE_EDGE.y-into*AXE_EDGE.z,into,(-.4,.1,-.9))
    hit=K_(root=V(0,0,-.05),**feet,pelvis=(0,CHOP_HIT*.4,0),spine=(4,CHOP_HIT,0),head=(6,-CHOP_HIT*.6,0),rh=hit_rh,lh=balance_hit)
    R=Matrix.Rotation(math.radians(-25),3,'Z')      # tugged back out of the cut, the head levering round to his right
    pull=hand(tuple(hit_rh['grip']-into*.07),R@hit_rh['face'],R@hit_rh['haft'],(-.4,.1,-.9))
    out=dict(hit);out['rh']=pull
    return [(0,cocked),(.14,cocked),(.28,slot),(.33,side),(.40,hit),(.54,hit),(.60,out),(.68,side),(.77,slot),(.90,cocked)]   # back up the swing's own path


clip('Chop',1.3,chop_keys(),rtool='axe',what='felling a tree: a one-handed flat swing like a bat, from his right into the trunk\'s side, the whole upper body unwinding into it')
CLIPS['Chop']['env']='tree'

# Mine: a one-handed pickaxe swing, vertical, like an overhand bat swing: the
# pick raised behind his head, the fist coming up to head height with the head
# trailing above it, the arm reaching forward and the pick tipping over, and the
# point driving down into the rock's upper front. It holds, levers free and goes
# back up the way it came. Set at Astra's Stone_Field (the commonest deposit),
# its front and __Mine_Target turned to him, where StoneDeposit.StandOff puts a
# miner (1.80 m game from its pivot: its front face about 1 m off). Its top is
# above his shoulders, so the pick strikes its sloping upper front, not a top.
# Key poses found by search against crew_v15_anatomy (no clipping, joints in
# range, the pick clear of the rock but for its point) on the real rock.
MINE_TIP=V(0,.58,.23)*TOOL_SCALE                   # the pick's point in the tool frame (the game's fallback pick)
MINE_AT=V(-.20,-.849,.472)                         # the point 2 cm into the rock's upper front, in line with his right shoulder
MINE_ANGLE=60                                      # the point driving in this far below level


def pick_pose(grip,tilt,elbow,lean,drop,balance):
    """The pick held up in the swing plane: `tilt` degrees from straight up
    (+ back over his head, - forward toward the rock), the point leading."""
    a=math.radians(tilt)
    return K_(root=V(0,0,drop),rf=(-.03,.07,0,0),lf=(.03,-.07,0,0),spine=(lean,0,0),head=(-lean*.5,0,0),
              rh=hand(grip,(0,-math.cos(a),math.sin(a)),(0,math.sin(a),math.cos(a)),elbow),lh=balance)


def mine_keys():
    balance_up=hand((.36,-.26,.58),(.3,-.8,-.3),(0,0,1),(.9,.3,-.2))
    balance_low=hand((.34,-.24,.46),(.3,-.5,-.8),(0,-1,0),(.8,.5,0))
    cocked=pick_pose((-.32,-.04,.98),100,(-.9,.2,-.4),-10,-.02,balance_up)    # raised behind his head, the point up
    lag=pick_pose((-.28,-.22,.90),40,(-.6,.3,-.7),0,-.03,balance_up)          # fist at head height, the head trailing above
    over=pick_pose((-.22,-.38,.64),-20,(-.5,.3,-.8),12,-.05,balance_low)      # reaching forward, the pick tipping over
    a=math.radians(MINE_ANGLE);face=V(0,-math.cos(a),-math.sin(a));haft=V(0,-math.sin(a),math.cos(a))
    grip=MINE_AT-haft*MINE_TIP.y-face*MINE_TIP.z
    hit=K_(root=V(0,0,-.07),rf=(-.03,.07,0,0),lf=(.03,-.07,0,0),spine=(20,0,0),head=(-10,0,0),
           rh=hand(tuple(grip),face,haft,(-.5,.3,-.8)),lh=balance_low)
    free=pick_pose(tuple(grip+V(0,.06,.03)),-45,(-.5,.3,-.8),18,-.06,balance_low)   # levered back out of the rock
    return [(0,cocked),(.12,cocked),(.26,lag),(.34,over),(.40,hit),(.54,hit),(.62,free),(.72,over),(.82,lag),(.92,cocked)]


clip('Mine',1.1,mine_keys(),rtool='pick',what='a one-handed vertical pickaxe swing, overhand like a bat, into the rock')
CLIPS['Mine']['env']='rock'

BUSH=[('bush',(-.02,-.40,.09),(.26,.24,.18),'leaf',0),('berries',(-.02,-.42,.17),(.08,.08,.06),'berry',0)]
clip('Forage',1.7,[
    (0,K_(root=V(0,0,-.03),spine=(10,0,0),head=(10,0,0),lh=hand((.30,-.12,.40),(.3,-.3,-1),(0,-1,0),(.6,.6,0)))),
    (.35,K_(root=V(0,0,-.16),spine=(42,6,0),head=(22,0,0),rh=hand((-.07,-.36,.16),(0,-.3,-1),(0,-1,0),(-.6,.4,0)),
            lh=hand((.24,-.18,.30),(.3,-.4,-1),(0,-1,0),(.6,.6,0)))),
    (.52,K_(root=V(0,0,-.16),spine=(42,6,0),head=(24,0,0),rh=hand((-.06,-.33,.19),(0,-.1,-1),(0,-1,0),(-.6,.4,0)),
            lh=hand((.24,-.18,.30),(.3,-.4,-1),(0,-1,0),(.6,.6,0)))),
    (.78,K_(root=V(0,0,-.06),spine=(16,-6,0),head=(8,-10,0),rh=hand((.14,-.20,.40),(.6,-.3,-.6),(0,-1,0),(-.5,.2,-.6)),
            lh=hand((.30,-.12,.40),(.3,-.3,-1),(0,-1,0),(.6,.6,0)))),
    ],ltool='basket',props=BUSH,what='crouch, pick from a bush, drop it in the basket (spice, food)')

POST=[('post',(0,-.44,.52),(.12,.12,1.04),'wood',0),('board',(0,-.38,.62),(.46,.03,.12),'wood_light',0)]
clip('Build',.95,[
    (0,K_(spine=(2,-6,0),head=(0,-4,0),rh=hand((-.29,-.10,.84),(-.1,-.4,1),(0,.85,.5),(-.9,.3,-.3)),lh=hand((.09,-.34,.64),(0,-1,0),(0,0,1),(.6,.2,-.4)))),
    (.40,K_(spine=(2,-6,0),head=(0,-4,0),rh=hand((-.29,-.09,.86),(-.1,-.45,1),(0,.85,.55),(-.9,.3,-.3)),lh=hand((.09,-.34,.64),(0,-1,0),(0,0,1),(.6,.2,-.4)))),
    (.55,K_(spine=(8,-2,0),head=(4,-2,0),rh=hand((-.07,-.29,.55),(0,-1,0),(0,0,1),(-.6,.3,-.4)),lh=hand((.09,-.34,.64),(0,-1,0),(0,0,1),(.6,.2,-.4)))),
    (.66,K_(spine=(8,-2,0),head=(4,-2,0),rh=hand((-.07,-.28,.57),(0,-1,.15),(0,.15,1),(-.6,.3,-.4)),lh=hand((.09,-.34,.64),(0,-1,0),(0,0,1),(.6,.2,-.4)))),
    ],rtool='hammer',props=POST,what='nailing a board to a post (raising any building)')


# Carry: a heavy load held out on both arms, walked in place. The arms reach
# straight ahead at shoulder width, fists just below the shoulders, the load
# resting on both fists, its back against his belly; he leans back 16 degrees against it, hips
# pushed forward under it, head tipped only half as far forward to see past it, and walks slow and short, sinking into each
# step with a waddle from foot to foot. The hands are keyed in the spine's
# frame (hands_on_spine), so a load parented to the spine bone at CARRY_SOCKET
# rides on the forearms on every frame, whatever it is: that socket is the
# one contract for the game's stacks (logs, planks, stones, bricks, sacks).
# Arm pose found by search against crew_v15_anatomy with a 0.54 x 0.26 x
# 0.18 m crate (the preview crate is now 0.50 wide, the width PickUp grips) (his scale) on it, its top kept under his chin; no part of him
# inside the load (the checker tests both ways for a load).
CARRY_FIST=V(.22,-.34,.54)                          # his left fist, standing (the right mirrors it)
CARRY_SOCKET=V(0,-.40,.648)                         # the load's bottom centre, on the fists (rest pose, parent: spine): its back face at his belly
CARRY_DEPTH=.26                                     # deepest load, centred on the socket, whose back face clears his belly (0.26 m out)
CARRY_LEAN=-16


def carry_pose(t):
    """Heavy in-place walk at phase t, right foot forward at t=0."""
    a=t*2*math.pi;c,sn=math.cos(a),math.sin(a);stride=.075
    q=K_(hands_on_spine=1.)
    q['rf']=(0,-stride*c,.03*max(0,-sn),-8*c);q['lf']=(0,stride*c,.03*max(0,sn),8*c)
    q['root']=V(-.016*c,-.03,-.06-.024*abs(c))     # hips forward under the load, sinking into each footfall, the weight rolling over the planted foot
    q['pelvis']=(CARRY_LEAN*.3,4*c,-4*c)
    q['spine']=(CARRY_LEAN+2.5*abs(c),-3*c,3*c)    # leaning back, the load squashing him a little at each step
    q['head']=(-CARRY_LEAN*.5+2*abs(c),0,-2*c)     # tipped forward to see past it: half the lean, so the lean still shows
    tilt=math.radians(20)
    for key,s in(('rh',-1),('lh',1)):
        q[key]=hand((s*CARRY_FIST.x,CARRY_FIST.y,CARRY_FIST.z),(0,-math.cos(tilt),-math.sin(tilt)),(0,0,1),(s*.5,.3,-.8))
    return q


clip('Carry',1.2,carry_pose,rtool='crate',what='a heavy load held out on both arms, leaning back against it, walking slow and short (in place)')
PICK_AT=V(0,-.48,0)                                # the load on the ground in front of him (bottom centre)
PICK_GRAB=hand((-.35,-.48,.12),(0,-.8,-.6),(0,0,1),(-.7,.4,-.6))   # his right fist on the load's right side, palm in (the left mirrors it)


def mirror_hand(h):
    return hand((-h['grip'].x,h['grip'].y,h['grip'].z),(-h['face'].x,h['face'].y,h['face'].z),
                (-h['haft'].x,h['haft'].y,h['haft'].z),(-h['elbow'].x,h['elbow'].y,h['elbow'].z))


# PickUp: from Walk's first frame he steps in over a load on the ground,
# squats and bends, takes it by both sides, braces, heaves it up with his legs
# and rolls it onto his fists, ending on Carry's first frame (the load on the
# carry socket). The load: on the ground until pickup['grab'], then carried
# in the frame of his two fists up to pickup['seat'], where it settles onto the
# carry socket against his belly; the fists then drop and slide in under it
# (pickup_track). Grab found by search against crew_v15_anatomy
# (the load checked both ways: nothing of him in it, it in nothing of him).
def pickup_keys():
    D=2.0;T=lambda sec:sec/D
    feet=dict(rf=(-.07,.02,0,0),lf=(.07,.02,0,0))
    look=K_(**feet,root=V(0,.02,-.05),spine=(12,0,0),head=(14,0,0),
            rh=hand((-.32,-.16,.44),(0,-.6,-.8),(0,0,1),(-.7,.4,-.6)),lh=hand((.32,-.16,.44),(0,-.6,-.8),(0,0,1),(.7,.4,-.6)))
    grab=K_(**feet,root=V(0,.04,-.18),pelvis=(22,0,0),spine=(42,0,0),head=(-10,0,0),rh=PICK_GRAB,lh=mirror_hand(PICK_GRAB))
    brace=dict(grab);brace['root']=V(0,.04,-.19);brace['head']=(-18,0,0)          # gripped, eyes up: the effort coming
    heave_r=hand((-.39,-.46,.50),(0,-.8,-.6),(0,0,1),(-.6,.4,-.7))
    heave=K_(**feet,root=V(0,.02,-.10),pelvis=(4,0,0),spine=(6,0,0),head=(0,0,0),rh=heave_r,lh=mirror_hand(heave_r))
    # the rest in the spine's frame, as Carry: the load seated against his belly on the carry
    # socket, still held by its sides; the fists drop below it, then slide in under it
    end=carry_pose(0)
    def on_spine(fist,face=(0,-.8,-.6),haft=(0,0,1),el=(-.7,.4,-.6)):
        q=dict(end);r=hand(fist,face,haft,el);q['rh']=r;q['lh']=mirror_hand(r);return q
    seat=on_spine((-.36,-.36,.68),face=(0,-1,0),el=(-.8,.3,-.5))                 # load at carry height, its back on his belly
    under=on_spine((-.39,-.36,.51),face=(0,-1,0),el=(-.8,.3,-.5))                # fists down past its bottom edge
    return [(0,walk_pose(0)),(T(.30),look),(T(.70),grab),(T(.85),brace),(T(1.25),heave),(T(1.50),seat),
            (T(1.68),under),(1,end)]


clip('PickUp',2.0,pickup_keys(),loop=False,rtool='crate',
     what='squats, takes the load by its sides and heaves it up onto his arms; from Walk, into Carry (one-shot)')
CLIPS['PickUp']['pickup']={'grab':.85/2.0,'seat':1.50/2.0,'at':PICK_AT}

# --- building jobs
# Saw, at the level 1 lumber mill with its bench lowered for him
# (mill_l1_lowbench.py; crew_v15_mill.py loads it). Measured from
# Worker_Stand, at his 1.30 m source scale: the log on the bench lies along
# X, 0.33 to 0.61 m in front of him, its top 0.57 m up (his belly), 0.28 m
# across. He crosscuts its right end: the stroke runs beside his belly on
# his right, blade 35 degrees down, forearm in line with the saw; the teeth
# stay in one kerf on the log's top. His left fist holds the log down.
# Anatomy (every frame, crew_v15_anatomy.py): shoulders 0.22 m out inside
# the tunic's 0.25 m, belly 0.26 m in front, reach 0.42 m.
LOG_TOP,LOG_Y,LOG_R=.57,-.47,.14
SAW_ANGLE=math.radians(26)                          # blade below horizontal
SAW_DIR=nrm((0,-math.cos(SAW_ANGLE),-math.sin(SAW_ANGLE)));SAW_UP=nrm((0,-math.sin(SAW_ANGLE),math.cos(SAW_ANGLE)))
KERF=V(-.37,LOG_Y+.04,LOG_TOP-.005)                # the cut, on the log's top, near his side of centre
SAW_IN=.27                                         # blade from the fist to the kerf at the pull ...
SAW_LEN=.15                                        # ... and the stroke, so the fist stays 12 cm off the log
SAW_PULL=KERF-SAW_DIR*SAW_IN+SAW_UP*.05
STAND_BACK=.10                                     # he stands 10 cm behind Worker_Stand: his belly clears the log
TRESTLE=[]                                         # the mill is the prop now (env='mill')


def saw_pose(t):
    s=.5-.5*math.cos(t*2*math.pi)                   # 0 at the pull, 1 at the end of the push
    grip=SAW_PULL+SAW_DIR*(SAW_LEN*s)
    return K_(root=V(0,STAND_BACK-.012*s,-.04-.005*s),rf=(0,.07,0,0),lf=(0,-.05,0,0),
              pelvis=(0,-2*s,0),spine=(26+3*s,4,0),head=(12-2*s,-8,0),
              rh=hand(tuple(grip),SAW_DIR,SAW_UP,(-.8,.6,.2)),
              lh=hand((.40,LOG_Y+.14,LOG_TOP+.08),(.1,-.7,-.7),(-.6,-.8,0),(1,.5,-.2)))   # on the log's left end, outside his belly


clip('Saw',1.0,saw_pose,rtool='saw',props=TRESTLE,what='level 1 lumber mill: sawing the log on the bench, the left hand holding it down')
CLIPS['Saw']['env']='mill'

FIELD=[('soil',(0,-.60,.015),(.6,.5,.03),'soil',0),('sprout',(.12,-.70,.06),(.05,.05,.08),'leaf',0),('sprout',(-.14,-.74,.06),(.05,.05,.08),'leaf',0)]
clip('Farm',1.25,[
    (0,K_(root=V(0,0,-.02),spine=(4,0,0),head=(8,0,0),rh=swing_hand((-.05,-.02,.76),-.25,.97,(-.6,.5,-.3)),lh={'on_tool':.22,'elbow':V(.6,.2,-.3)})),
    (.32,K_(root=V(0,0,-.02),spine=(2,0,0),head=(8,0,0),rh=swing_hand((-.05,-.02,.78),-.2,.98,(-.6,.5,-.3)),lh={'on_tool':.22,'elbow':V(.6,.2,-.3)})),
    (.48,K_(root=V(0,0,-.07),spine=(24,0,0),head=(18,0,0),rh=swing_hand((-.05,-.12,.56),-.72,-.69,(-.6,.5,-.1)),lh={'on_tool':.22,'elbow':V(.6,.3,0)})),
    (.62,K_(root=V(0,0,-.07),spine=(22,0,0),head=(18,0,0),rh=swing_hand((-.05,-.09,.59),-.66,-.74,(-.6,.5,-.1)),lh={'on_tool':.22,'elbow':V(.6,.3,0)})),
    (.82,K_(root=V(0,0,-.04),spine=(14,0,0),head=(12,0,0),rh=swing_hand((-.05,-.02,.62),-.55,.5,(-.6,.5,-.2)),lh={'on_tool':.22,'elbow':V(.6,.2,-.2)})),
    ],rtool='hoe',props=FIELD,what='farm plot: hoeing the rows')

ANVIL=[('anvil',(0,-.40,.17),(.16,.30,.34),'iron',0),('anvil_top',(0,-.41,.36),(.18,.40,.06),'iron',0),('bar',(.03,-.40,.405),(.03,.18,.025),'hot',0)]
clip('Smith',.8,[
    (0,K_(root=V(0,0,-.02),spine=(10,-6,0),head=(14,0,0),rh=hand((-.29,-.06,.84),*reversed(sag(.3,.95)),(-.9,.3,-.3)),lh=hand((.12,-.30,.47),(0,-1,-.4),(-1,0,0),(.6,.4,0)))),
    (.45,K_(root=V(0,0,-.02),spine=(10,-6,0),head=(14,0,0),rh=hand((-.29,-.05,.86),*reversed(sag(.35,.94)),(-.9,.3,-.3)),lh=hand((.12,-.30,.47),(0,-1,-.4),(-1,0,0),(.6,.4,0)))),
    (.62,K_(root=V(0,0,-.04),spine=(18,-2,0),head=(16,0,0),rh=hand((-.03,-.18,.50),*reversed(sag(-1,-.05)),(-.6,.4,-.2)),lh=hand((.12,-.30,.47),(0,-1,-.4),(-1,0,0),(.6,.4,0)))),
    (.74,K_(root=V(0,0,-.04),spine=(17,-2,0),head=(16,0,0),rh=hand((-.04,-.17,.55),*reversed(sag(-.95,.3)),(-.6,.4,-.2)),lh=hand((.12,-.30,.47),(0,-1,-.4),(-1,0,0),(.6,.4,0)))),
    ],rtool='hammer',props=ANVIL,what='forge: hammering hot iron on the anvil')


def stir_pose(t):
    a=t*2*math.pi
    g=(-.03+.07*math.cos(a),-.20+.06*math.sin(a),.60)
    h=nrm((.06*math.cos(a),-.30+.06*math.sin(a),-.95))
    return K_(root=V(0,0,-.03),spine=(16,4*math.cos(a),0),head=(20,0,0),
              rh=hand(g,nrm(h.cross(V(1,0,0))),h,(-.6,.5,-.2)),lh={'on_tool':-.11,'elbow':V(.6,.5,-.2)})


POT=[('pot',(0,-.36,.14),(.30,.30,.28),'iron',0),('stew',(0,-.36,.27),(.26,.26,.02),'stew',0),('fire',(0,-.36,.02),(.36,.36,.04),'hot',0)]
clip('Cook',1.6,stir_pose,rtool='paddle',props=POT,what='kitchen: stirring the pot')


def mill_pose(t):
    a=t*2*math.pi;g=V(0,-.36,.40)+V(.11*math.cos(a),.11*math.sin(a),.04)
    return K_(root=V(0,0,-.08),spine=(28,8*math.cos(a),0),head=(22,0,0),
              rh=hand(g,(0,-.3,-1),(0,-1,0),(-.6,.5,-.1)),lh=hand((.18,-.24,.36),(.3,-.4,-1),(0,-1,0),(.6,.5,0)))


QUERN=[('quern_base',(0,-.36,.17),(.40,.40,.34),'stone',0),('quern_top',(0,-.36,.37),(.36,.36,.06),'stone_light',0)]
clip('Mill',1.5,mill_pose,rtool='peg',props=QUERN,what='mill: turning the quern stone by its peg')

RAIL=[('rail',(0,-.34,.56),(.9,.06,.05),'wood',0),('rail_post',(-.40,-.34,.28),(.05,.05,.56),'wood',0),('rail_post',(.40,-.34,.28),(.05,.05,.56),'wood',0)]
ON_RAIL_R=hand((-.14,-.28,.60),(0,-.6,-1),(1,0,0),(-.8,.3,0))
ON_RAIL_L=hand((.14,-.28,.60),(0,-.6,-1),(-1,0,0),(.8,.3,0))
POINT_R=hand((-.24,-.30,.84),(-.25,-1,.35),(0,0,1),(-.9,.3,-.2))
clip('Lookout',4.0,[
    (0,K_(spine=(14,0,0),head=(-14,-30,0),rh=ON_RAIL_R,lh=ON_RAIL_L)),
    (.22,K_(spine=(14,4,0),head=(-14,-28,0),rh=ON_RAIL_R,lh=ON_RAIL_L)),
    (.45,K_(spine=(14,-4,0),head=(-14,30,0),rh=ON_RAIL_R,lh=ON_RAIL_L)),
    (.55,K_(spine=(8,-6,0),head=(-16,18,0),rh=ON_RAIL_R,lh=ON_RAIL_L)),
    (.65,K_(spine=(2,-4,0),head=(-16,6,0),rh=POINT_R,lh=ON_RAIL_L)),
    (.80,K_(spine=(2,-4,0),head=(-16,4,0),rh=POINT_R,lh=ON_RAIL_L)),
    (.90,K_(spine=(12,-2,0),head=(-14,-10,0),rh=ON_RAIL_R,lh=ON_RAIL_L)),
    ],props=RAIL,what='watchtower: leaning on the rail, scanning the horizon, pointing out a sail')

STONE=[('block',(0,-.40,.17),(.36,.30,.34),'stone',0)]
clip('Quarry',.95,[
    (0,K_(root=V(0,0,-.05),spine=(22,-6,0),head=(20,0,0),rh=hand((-.29,-.08,.80),*reversed(sag(.25,.97)),(-.9,.3,-.3)),lh=hand((.06,-.34,.46),(0,-.5,-1),(0,0,1),(.6,.5,0)))),
    (.45,K_(root=V(0,0,-.05),spine=(22,-6,0),head=(20,0,0),rh=hand((-.29,-.07,.82),*reversed(sag(.3,.95)),(-.9,.3,-.3)),lh=hand((.06,-.34,.46),(0,-.5,-1),(0,0,1),(.6,.5,0)))),
    (.62,K_(root=V(0,0,-.06),spine=(26,-2,0),head=(22,0,0),rh=hand((.03,-.14,.56),*reversed(sag(-1,.1)),(-.6,.4,-.2)),lh=hand((.06,-.34,.46),(0,-.5,-1),(0,0,1),(.6,.5,0)))),
    (.74,K_(root=V(0,0,-.06),spine=(26,-2,0),head=(22,0,0),rh=hand((.02,-.14,.60),*reversed(sag(-.95,.35)),(-.6,.4,-.2)),lh=hand((.06,-.34,.46),(0,-.5,-1),(0,0,1),(.6,.5,0)))),
    ],rtool='mallet',ltool='chisel',props=STONE,what='quarry: mallet and chisel, dressing stone into brick')

clip('Fletcher',1.5,[
    (0,K_(spine=(14,4,0),head=(26,0,0),rh=hand((-.02,-.22,.60),(.6,-.8,-.1),(0,0,1),(-.6,.4,-.3)),lh=hand((.12,-.24,.57),(-.4,-.9,0),(0,0,1),(.6,.4,-.3)))),
    (.45,K_(spine=(14,4,0),head=(26,0,0),rh=hand((-.03,-.23,.60),(.6,-.8,-.1),(0,0,1),(-.6,.4,-.3)),lh=hand((.12,-.24,.57),(-.4,-.9,0),(0,0,1),(.6,.4,-.3)))),
    (.62,K_(spine=(14,2,0),head=(26,0,0),rh=hand((-.13,-.30,.56),(.3,-.9,-.2),(0,0,1),(-.6,.4,-.3)),lh=hand((.12,-.24,.57),(-.4,-.9,0),(0,0,1),(.6,.4,-.3)))),
    ],rtool='knife',ltool='shaft',what='fletcher: whittling an arrow shaft')

BENCH=[('bench',(0,-.38,.19),(.50,.26,.38),'wood',0),('fish',(.04,-.38,.40),(.30,.09,.05),'fish',0)]
clip('Fisher',1.2,[
    (0,K_(root=V(0,0,-.04),spine=(32,-4,0),head=(20,0,0),rh=hand((-.06,-.25,.53),(-.2,-.5,-1),(0,-1,.2),(-.6,.5,0)),lh=hand((.15,-.36,.46),(0,-.3,-1),(0,-1,0),(.6,.4,0)))),
    (.4,K_(root=V(0,0,-.04),spine=(32,-4,0),head=(20,0,0),rh=hand((-.07,-.26,.52),(-.2,-.5,-1),(0,-1,.2),(-.6,.5,0)),lh=hand((.15,-.36,.46),(0,-.3,-1),(0,-1,0),(.6,.4,0)))),
    (.62,K_(root=V(0,0,-.05),spine=(36,0,0),head=(22,0,0),rh=hand((-.12,-.40,.48),(-.2,-.5,-1),(0,-1,.2),(-.6,.5,0)),lh=hand((.15,-.36,.46),(0,-.3,-1),(0,-1,0),(.6,.4,0)))),
    ],rtool='knife',props=BENCH,what='fishing hut: gutting the catch on the prep bench')

# HuntWalk: stalking with the spear (the game's placeholder, HunterProps):
# crouched, leaning in, short careful steps that lift and place each foot, the
# spear raised by his right cheek in a javelin grip, level and pointing ahead,
# ready to throw; the left hand out in front for balance; the head scanning
# slowly left and right once across the clip's two strides. In place, 2.2 s.
# Spear grip found by search against crew_v15_anatomy, clean at every head turn,
# the spear pointing where it is asked to (checked on the posed fist).
STALK_GRIP=hand((-.33,-.06,.92),(.26,.10,.96),nrm((0,-.995,.105)),(-.9,.3,-.3))   # knuckles square to the spear: it points level ahead, 6 degrees up
STALK_LEFT=hand((.30,-.24,.58),(.3,-.8,-.3),(0,0,1),(.9,.3,-.2))


def stalk_pose(t):
    """Two strides over t = 0..1 (right foot forward at t=0), the head scanning once."""
    a=t*4*math.pi;c,sn=math.cos(a),math.sin(a);stride=.085
    q=K_()
    q['rf']=(0,-stride*c,.04*max(0,-sn),-10*c);q['lf']=(0,stride*c,.04*max(0,sn),10*c)
    q['root']=V(-.008*c,0,-.08-.012*abs(c))        # low and smooth: knees bent, little bob
    q['pelvis']=(0,4*c,0);q['spine']=(12,-3*c,0)
    q['head']=(-8,18*math.sin(t*2*math.pi),0)       # alert: looking up and ahead, scanning
    q['rh']=STALK_GRIP;q['lh']=STALK_LEFT
    return q


clip('HuntWalk',2.2,stalk_pose,rtool='spear',what='stalking with the spear raised, crouched and alert, head scanning (in place)')

# Hunt: lining up a goat 4 m off (game; his 1.30 m scale: 3.06 m) and
# throwing the spear, from HuntWalk's first frame: he stops and turns side-on,
# the left arm pointing at the goat, the spear drawn back level behind his
# right shoulder, aimed; holds it; then the hips come round, the elbow leads
# high, the arm whips through and the spear goes at 14 degrees up, flies on a
# real arc (gravity at his scale) and sticks in the goat's flank; he follows
# through onto the front foot, the back heel up, watches it land and ends on
# Walk's first frame to go and fetch it. One-shot, 2.6 s. Every key pose found
# by search against crew_v15_anatomy (spear in hand checked against his body).
HUNT_TARGET=V(0,-3.06,0)                           # the goat's middle, on the ground
HUNT_FLANK=V(0,-2.99,.30)                          # where the spear's point ends: 3 cm into the near flank
SPEAR_TIP=1.35*TOOL_SCALE                          # grip to point, the game's placeholder spear
THROW_AIM=nrm((0,-.99,.14))                        # the spear drawn back, sighting along it
THROW_REL=nrm((0,-.97,.24))                        # its line as it leaves the hand
GOAT=[('goat',(0,-3.06,.30),(.44,.19,.19),'goat',0),('goat_head',(.27,-3.06,.42),(.12,.10,.12),'goat',0),
      ('goat_horn',(.29,-3.06,.50),(.03,.07,.06),'wood_bark',0)]+[
     ('goat_leg',(x,-3.06+y,.105),(.035,.035,.21),'goat',0) for x in(-.16,.16) for y in(-.06,.06)]


def hunt_keys():
    D=2.6;T=lambda sec:sec/D
    stance=dict(lf=(0,-.12,0,0),rf=(0,.10,0,0))
    sight=K_(**stance,root=V(0,.03,-.06),pelvis=(0,-30,0),spine=(-4,-25,0),head=(-4,50,0),
             rh=hand((-.36,.32,.86),(0,.14,.99),THROW_AIM,(-.5,.5,-.7)),lh=hand((.10,-.48,.86),(0,-1,.15),(0,0,1),(.6,.2,-.6)))
    aim=dict(sight);aim['root']=V(0,.04,-.07);aim['head']=(-5,51,0)          # settling onto the back foot, eyes on it
    cock=K_(**stance,root=V(0,0,-.07),pelvis=(0,-10,0),spine=(4,-30,0),head=(0,38,0),
            rh=hand((-.36,.14,.92),(0,.14,.99),THROW_AIM,(-.8,.2,-.6)),lh=hand((.20,-.40,.66),(.1,-1,0),(0,0,1),(.8,.2,-.5)))
    release=K_(**stance,root=V(0,-.04,-.07),pelvis=(0,10,0),spine=(14,10,0),head=(-6,-18,0),
               rh=hand((-.26,-.28,1.02),(.5,.2,.85),THROW_REL,(-.6,.4,-.7)),lh=hand((.38,-.04,.52),(.2,-.3,-1),(0,-1,0),(.6,.7,0)))
    follow=K_(lf=(0,-.12,0,0),rf=(0,.06,.03,20),root=V(0,-.06,-.09),pelvis=(0,15,0),spine=(26,15,0),head=(-16,-28,0),
              rh=hand((-.10,-.38,.40),(.3,-.3,-.9),(0,0,1),(-.6,-.3,-.7)),lh=hand((.34,-.12,.44),(.2,-.3,-1),(0,-1,0),(.6,.7,0)))
    watch=K_(lf=(0,-.08,0,0),rf=(0,.04,0,0),root=V(0,-.02,-.04),spine=(8,4,0),head=(-6,-6,0))
    # waypoints, each found by search along its blended path:
    walk0=stalk_pose(0)
    rise=mix(walk0,sight,.5);rise['lh']=hand((.26,-.34,.66),(.2,-1,0),(0,0,1),(.9,.3,-.2))        # the left arm on its way to pointing
    pull=mix(aim,cock,.5);pull['lh']=hand((.18,-.40,.70),(.1,-1,0),(0,0,1),(.6,.2,-.6))           # and pulling in
    over=mix(cock,release,.5);over['rh']=hand((-.34,-.10,.98),(.4,.2,.9),nrm((0,-.98,.19)),(-.9,.4,-.2))   # the arm coming over, clear of his head
    over['lh']=hand((.24,-.32,.62),(.1,-1,0),(0,0,1),(.8,.2,-.5))
    whip=mix(release,follow,.35);whip['rh']=hand((-.22,-.40,.88),(.3,-.6,.75),(1,0,0),(-.9,.2,-.3))   # the arm through, knuckles still up
    turn=mix(release,follow,.7);turn['rh']=hand((-.16,-.46,.56),(0,-.8,-.6),(.7,0,.7),(-.9,.2,-.3))   # coming down, the hand turning over
    back=mix(follow,watch,.5);back['rh']=hand((-.24,-.34,.40),(-.2,-.3,-.94),(0,-1,0),(-.6,.7,0))     # the right hand back to his side, clear of the sash
    return [(0,walk0),(T(.20),rise),(T(.40),sight),(T(.85),aim),(T(.95),pull),(T(1.05),cock),(T(1.115),over),(T(1.18),release),
            (T(1.26),whip),(T(1.35),turn),(T(1.42),follow),(T(1.70),follow),(T(1.93),back),(T(2.15),watch),(1,walk_pose(0))]


clip('Hunt',2.6,hunt_keys(),loop=False,rtool='spear',props=GOAT,
     what='lines up the goat and throws the spear, follows through and watches it strike; from HuntWalk, into Walk (one-shot)')
CLIPS['Hunt']['throw']={'release':1.18/2.6,'tip_at':HUNT_FLANK,'flight':.42}


# --- seasickness (the game's own mechanic: CrewAgent.Sickness01)
def belly(side,lift=0.,push=0.):
    """A fist pressed to his belly (he must hunch a little to reach it)."""
    s=SIDE_SIGN[side]
    return hand((s*.10,-.28-push,.58+lift),(-s,-.1,-.25),(0,0,1),(s*.9,.4,-.2))


LOOSE_L=hand((.36,-.02,.42),(.3,-.1,-1),(0,-1,0),(.6,.7,0))


def sick_sway(t):
    a=t*2*math.pi;b=a-.9                                   # the head lags the body
    return K_(root=V(.022*math.sin(a),0,-.02-.006*math.cos(2*a)),yaw=3*math.sin(a),
              pelvis=(0,0,-3*math.sin(a)),spine=(14+3*math.cos(2*a),0,6*math.sin(a)),
              head=(12+4*math.cos(2*b),-6*math.sin(b),14*math.sin(b)),
              rh=belly(RIGHT,.01*math.sin(2*a)),
              lh=hand((.36+.03*math.sin(a),-.02,.42),(.3,-.1,-1),(0,-1,0),(.6,.7,0)))


def sick_walk(t):
    q=walk_pose(t,arms=False);a=t*2*math.pi;c=math.cos(a)
    q['rf']=(q['rf'][0],q['rf'][1]*.6,q['rf'][2]*.7,q['rf'][3]*.6)
    q['lf']=(q['lf'][0],q['lf'][1]*.6,q['lf'][2]*.7,q['lf'][3]*.6)
    q['root']=q['root']+V(.028*math.sin(a+.6),0,-.02)       # lurching side to side
    q['spine']=(16,-3*c,7*math.sin(a+.6));q['pelvis']=(0,4*c,-4*math.sin(a+.6))
    q['head']=(14,6*math.sin(a),-12*math.sin(a))
    q['rh']=belly(RIGHT,.012*c)
    q['lh']=hand((.38+.04*math.sin(a+.6),-.05-.08*c,.44),(.35,-.2*c,-1),(0,-1,0),(.7,.6,0))
    return q


def sick_clutch(t):
    a=t*2*math.pi;h=max(0,math.sin(a))**3                    # a cramp once a cycle
    return K_(root=V(0,.015*h,-.05-.04*h),spine=(28+10*h,0,0),head=(18+10*h,0,0),
              rh=belly(RIGHT,-.02*h,.01),lh=belly(LEFT,-.02*h,.01))


RAIL_SICK=[('rail',(0,-.36,.58),(.9,.06,.05),'wood',0),('rail_post',(-.40,-.36,.29),(.05,.05,.58),'wood',0),
           ('rail_post',(.40,-.36,.29),(.05,.05,.58),'wood',0)]
ON_RAIL=lambda side:hand((SIDE_SIGN[side]*.17,-.35,.64),(0,-.4,-1),(0,-1,0),(SIDE_SIGN[side]*.9,.3,0))


def sick_rail(t):
    # two heaves a cycle, then a sag
    h=0.
    for c0 in (.18,.42):h=max(h,math.exp(-((t-c0)/.07)**2))
    return K_(root=V(0,.07+.02*h,-.03-.01*h),spine=(36+10*h,0,0),head=(18+16*h,0,0),rh=ON_RAIL(RIGHT),lh=ON_RAIL(LEFT))


KNEEL=dict(root=V(0,.02,-.23),rf=(0,.17,-.03,150),lf=(0,.17,-.03,150))
PUDDLE=[('puddle',(0,-.40,.004),(.26,.20,.008),'sick',0)]


def sick_kneel(t):
    h=0.
    for c0 in (.25,.45):h=max(h,math.exp(-((t-c0)/.08)**2))
    return K_(**KNEEL,spine=(48+16*h,0,0),head=(24+20*h,0,0),
              rh=hand((-.15,-.33,.07),(0,-.2,-1),(0,-1,0),(-.8,.2,.2)),lh=hand((.15,-.33,.07),(0,-.2,-1),(0,-1,0),(.8,.2,.2)))


clip('SickSway',3.0,sick_sway,what='queasy: swaying, a fist on his stomach, head lolling')
clip('SickWalk',1.2,sick_walk,what='queasy walk: short lurching steps, a fist on his stomach')
clip('SickClutch',1.6,sick_clutch,what='hunched over, both fists on his stomach, a cramp each cycle')
clip('SickRail',1.5,sick_rail,props=RAIL_SICK,what='leaning over the rail, heaving twice')
clip('SickCollapse',1.8,[
    (0,sick_sway(0)),
    (.25,K_(root=V(.04,0,-.03),spine=(16,0,10),head=(14,0,16),rh=belly(RIGHT),lh=hand((.44,-.10,.52),(.8,-.2,-.6),(0,-1,0),(.8,.3,-.2)))),
    (.55,K_(root=V(.02,.01,-.13),rf=(0,.06,0,20),lf=(0,.08,0,30),spine=(30,0,4),head=(20,0,8),rh=belly(RIGHT),lh=hand((.30,-.18,.30),(.3,-.4,-1),(0,-1,0),(.8,.3,0)))),
    (.80,K_(**KNEEL,spine=(40,0,0),head=(20,0,0),rh=hand((-.15,-.32,.08),(0,-.2,-1),(0,-1,0),(-.8,.2,.2)),lh=hand((.15,-.32,.08),(0,-.2,-1),(0,-1,0),(.8,.2,.2)))),
    (1,sick_kneel(0)),
    ],loop=False,what='staggers, knees buckle, down on hands and knees (one-shot; then SickKneel)')
clip('SickKneel',2.0,sick_kneel,props=PUDDLE,what='on hands and knees, heaving')


# --- aboard ship
def deck_brace(t):
    a=t*2*math.pi;roll=math.sin(a)                         # the deck rolls under him
    return K_(root=V(.03*roll,0,-.035-.012*math.cos(2*a)),rf=(-.04,0,0,0),lf=(.04,0,0,0),
              pelvis=(0,0,4*roll),spine=(5,0,-7*roll),head=(0,4*math.sin(a+1),5*roll),
              rh=hand((-.40+.02*roll,-.06,.50),(-.4,-.2,-1),(0,-1,0),(-.7,.6,0)),
              lh=hand((.40+.02*roll,-.06,.50),(.4,-.2,-1),(0,-1,0),(.7,.6,0)))


def rail_grip(t):
    a=t*2*math.pi;j=math.exp(-((t-.55)/.06)**2)             # a sea slams him once a cycle
    return K_(root=V(0,.05+.03*math.sin(a)+.04*j,-.06-.02*j),spine=(22+8*math.sin(a)+10*j,0,4*math.sin(a)),
              head=(20+6*j,0,-4*math.sin(a)),rh=ON_RAIL(RIGHT),lh=ON_RAIL(LEFT))


SIDE_RAIL=[('rail',(-.46,-.10,.58),(.06,1.0,.05),'wood',0),('rail_post',(-.46,-.50,.29),(.05,.05,.58),'wood',0),
           ('rail_post',(-.46,.30,.29),(.05,.05,.58),'wood',0),('bilge',(0,-.36,.006),(.36,.30,.012),'water',0)]
BUCKET_L=lambda f,h,e=(.7,.4,0):{'tool_pt':(0,0,.20),'face':V(*f),'haft':V(*h),'elbow':V(*e)}
clip('Bail',1.6,[
    (0,K_(root=V(0,0,-.15),spine=(44,0,0),head=(20,0,0),rh=hand((-.06,-.30,.30),(0,-.3,-1),(1,0,0),(-.7,.4,0)),lh=BUCKET_L((0,-.3,-1),(-1,0,0)))),
    (.22,K_(root=V(0,0,-.15),spine=(46,0,0),head=(22,0,0),rh=hand((-.06,-.32,.26),(0,-.1,-1),(1,0,0),(-.7,.4,0)),lh=BUCKET_L((0,-.1,-1),(-1,0,0)))),
    (.45,K_(root=V(0,0,-.05),spine=(12,-20,0),head=(4,-20,0),rh=hand((-.10,-.24,.56),(0,-1,.2),(1,0,0),(-.7,.4,-.2)),lh=BUCKET_L((-.2,-1,.2),(-1,0,0)))),
    (.62,K_(root=V(-.03,0,-.03),spine=(4,-55,6),head=(0,-35,0),rh=hand((-.32,-.14,.70),(-1,-.1,.5),(0,-1,0),(-.6,.6,-.3)),lh=BUCKET_L((-1,-.1,.2),(0,-1,0),(.6,.2,-.4)))),
    (.74,K_(root=V(-.03,0,-.03),spine=(4,-55,6),head=(0,-35,0),rh=hand((-.33,-.14,.72),(-1,-.2,.9),(0,-1,0),(-.6,.6,-.3)),lh=BUCKET_L((-1,-.2,.6),(0,-1,0),(.6,.2,-.4)))),
    ],rtool='bucket',props=SIDE_RAIL,what='scooping bilge water and tossing it over the side')

ROPE=[('rope',(-.02,-.40,.47),(.025,1.6,.025),'rope',0)]


def rope_hand(side,t):
    """Hand over hand: grip at the front, pull back while gripping, let go
    and reach forward again, half a cycle apart for the two hands."""
    ph=(t+(0 if side==RIGHT else .5))%1;s=SIDE_SIGN[side]
    if ph<.55:y=-.34+.30*(ph/.55);lift=0.                    # pulling
    else:u=(ph-.55)/.45;y=-.04-.30*u;lift=.06*math.sin(u*math.pi)
    z=.40+(y+1.2)*.075+lift
    return hand((-.02+s*.02,y,z),(s*-.5,0,-1),(0,-1,0),(s*.8,.4,-.3))


def haul(t):
    a=t*2*math.pi
    return K_(root=V(0,.05,-.06),rf=(0,-.07,0,0),lf=(0,.09,0,0),spine=(-6+3*math.sin(2*a),0,0),head=(8,0,0),
              rh=rope_hand(RIGHT,t),lh=rope_hand(LEFT,t))


clip('HaulLine',1.2,haul,props=ROPE,what='hauling a swimmer in, hand over hand on the line')
clip('ThrowLine',1.4,[
    (0,K_(spine=(4,0,0),rh=hand((-.30,-.10,.50),(-.2,-.3,-1),(0,-1,0),(-.7,.5,0)))),
    (.35,K_(root=V(0,.03,-.04),spine=(-6,-25,0),head=(0,-10,0),rh=hand((-.30,.14,.46),(-.3,.6,-.6),(0,-1,0),(-.8,.2,-.2)))),
    (.55,K_(root=V(0,-.02,-.05),spine=(14,15,0),head=(0,5,0),rh=hand((-.12,-.38,.78),(0,-1,.4),(0,0,1),(-.7,.2,-.4)))),
    (.70,K_(root=V(0,-.02,-.05),spine=(18,18,0),head=(4,6,0),rh=hand((-.08,-.40,.66),(0,-1,-.1),(0,0,1),(-.7,.2,-.3)))),
    (1,K_(spine=(6,6,0),head=(2,4,0))),
    ],loop=False,rtool='coil',what='throwing the rescue line over the rail (one-shot; then HaulLine)')

# Manning the cannon (Astra's naval deck cannon, crew_v15_mill.load_cannon),
# set up for the ship's deck, where the muzzle sits out over the rail: one
# gunner, his station beside the back of the gun (the gun on his right, ahead
# of him), outside the rear wheel and clear of the recoil. GunRam (the reload
# loop, 3.2 s, Cannon.reloadTime): he steps behind the gun, crouches to sight
# along the barrel, works the elevation wedge's handle to lay it, sights again
# and steps back to the station (loading the ball is implied: from the back
# he cannot reach the muzzle, and his arms cannot reach up to the vent).
# GunFire (one-shot): from the station he leans in with the linstock, touches
# the match to the vent, the gun fires and recoils past his right side, he
# flinches away, watches the shot and settles back as it runs out again.
# Both start and end on the same station pose. Poses found by search against
# crew_v15_anatomy with the gun's parts as props, tested on their real surfaces.
from crew_v15_mill import GUN_AT as _GUN_AT, GUN_RECOIL
GUN_AT=V(*_GUN_AT)
GUN_VENT=V(0,.343,.927)                             # the vent on top of the breech, from the gun's origin
GUN_HANDLE=V(0,.665,.43)                            # the end of the elevation wedge's handle, from the gun's origin
LINSTOCK_MATCH=.85*TOOL_SCALE                       # grip to the slow match
GUN_STAND=hand((-.32,-.24,.62),(0,-1,0),(0,0,1),(-.6,.7,0))   # his right hand at his side (in GunFire it holds the linstock upright)
GUN_LEFT=hand((.30,-.12,.52),(.2,-.3,-1),(0,-1,0),(.6,.7,0))


def gun_station():
    return K_(root=V(0,0,-.03),rf=(-.04,.02,0,0),lf=(.06,0,0,0),spine=(2,0,0),head=(0,-10,0),rh=GUN_STAND,lh=GUN_LEFT)


def _rel(h,root):
    """A hand target carried along with his root's step."""
    return hand(tuple(h['grip']+V(root[0],root[1],0)),h['face'],h['haft'],h['elbow'])


def _behind(st,rz,sp,hd,rh,lh):
    return K_(root=V(st[0],st[1],rz),rf=(st[0]-.05,st[1]+.03,0,0),lf=(st[0]+.05,st[1]-.03,0,0),spine=sp,head=hd,rh=rh,lh=lh)


def _knee(st,s,g):
    return hand((st[0]+s*g[0],st[1]+g[1],g[2]),(s*.2,-.6,-.8),(0,-1,0),(s*.6,.6,-.4))


def gunram_keys():
    st=gun_station()
    S=(-.75,.14);sight=_behind(S,-.14,(16,0,0),(-20,0,0),_knee(S,-1,(.26,-.24,.32)),_knee(S,1,(.26,-.24,.32)))   # crouched behind the breech, eye along the barrel
    look=dict(sight);look['head']=(-20,-5,0)
    Q=(-.58,.20);h=GUN_AT+GUN_HANDLE
    def quoin(dy):return _behind(Q,-.10,(16,14,0),(20,0,0),hand(tuple(h+V(-.05,.05+dy,0)),(.3,-.8,-.5),(0,0,1),(-.6,.6,-.5)),_knee(Q,1,(.26,-.24,.44)))   # the fist beside the handle's end, thumb up
    P=(-.38,.12);step=_behind(P,-.06,(8,0,0),(4,0,0),_rel(hand((-.40,-.10,.52),(-.2,-.3,-1),(0,-1,0),(-.6,.7,0)),P),_rel(GUN_LEFT,P))   # right fist dropped to his side, clear of the breech
    def swing(a,b):                                    # half way, his right fist swung out wide past the sash knot and the handle
        q=mix(a,b,.5);q['rh']=hand(tuple(q['rh']['grip']+V(-.12,0,-.04)),(-.2,-.3,-1),(.055,-.959,.277),(-.6,.7,0));return q
    return [(0,st),(.12,step),(.26,sight),(.40,look),(.46,swing(look,quoin(0))),(.52,quoin(0)),(.60,quoin(-.025)),(.68,quoin(0)),(.76,quoin(-.025)),
            (.79,swing(quoin(-.025),sight)),(.86,sight),(.94,step)]


clip('GunRam',3.2,gunram_keys(),what='gunner: behind the gun, sighting along the barrel and laying it with the elevation wedge, from his station beside it')
CLIPS['GunRam']['env']='cannon';CLIPS['GunRam']['gun']=[(0,0.),(1,0.)]


def hand_turn(a,b,u):
    """A hand target part way from a to b: its position lerped, its frame
    (knuckles, thumb) turned by a true rotation, so a blend through it
    cannot flip the forearm."""
    def frame(h):
        f=nrm(h['face']);t=nrm(h['haft']-f*h['haft'].dot(f));return Matrix((f,t,f.cross(t))).transposed().to_quaternion()
    q=frame(a).slerp(frame(b),u).to_matrix()
    return hand(tuple(a['grip'].lerp(b['grip'],u)),q.col[0],q.col[1],a['elbow'].lerp(b['elbow'],u))


def linstock_hand(tip_off,d=(-.6,-.75,-.2),roll=10):
    tip=GUN_AT+GUN_VENT+V(*tip_off);d=nrm(d);g=tip-d*LINSTOCK_MATCH
    up0=nrm(V(0,0,1)-d*d.z);side=d.cross(up0);a=math.radians(roll)
    return hand(tuple(g),nrm(up0*math.cos(a)+side*math.sin(a)),d,(-.6,.6,-.5))


def gunfire_keys():
    D=2.0;T=lambda sec:sec/D
    st=gun_station()
    touch=K_(root=V(0,0,-.03),rf=(-.04,.02,0,0),lf=(.06,0,0,0),spine=(10,-10,-4),head=(4,-19,0),rh=linstock_hand((0,0,.02),roll=-10),lh=GUN_LEFT)
    pull=touch['rh'];back=hand(tuple(pull['grip']-pull['haft']*.06),pull['face'],pull['haft'],pull['elbow'])
    flinch=dict(touch);flinch['rh']=back;flinch['head']=(8,10,2);flinch['spine']=(6,-4,0)   # the match drawn straight back, head turned from the blast
    watch=K_(root=V(.02,0,-.03),rf=(-.04,.02,0,0),lf=(.06,0,0,0),spine=(2,-2,0),head=(-4,-12,0),rh=_rel(GUN_STAND,(.02,0)),lh=_rel(GUN_LEFT,(.02,0)))
    def via(qa,qb,u):                                  # part way, the linstock turned by a true rotation
        q=mix(qa,qb,u*u*(3-2*u));q['rh']=hand_turn(qa['rh'],qb['rh'],u);return q
    return [(0,st),(T(.25),via(st,touch,1/3)),(T(.50),dict(via(st,touch,2/3),head=(-8,-19,0))),(T(.75),touch),(T(.82),touch),(T(1.00),flinch),
            (T(1.25),via(flinch,watch,1/3)),(T(1.40),via(flinch,watch,2/3)),(T(1.55),watch),(1,st)]


clip('GunFire',2.0,gunfire_keys(),loop=False,rtool='linstock',
     what='gunner: from his station beside the back of the gun, touches the linstock to the vent; the gun fires and recoils past him; he flinches away and watches the shot (one-shot)')
CLIPS['GunFire']['env']='cannon'
CLIPS['GunFire']['gun']=[(0,0.),(.80/2.0,0.),(.86/2.0,GUN_RECOIL),(1.10/2.0,GUN_RECOIL),(1.80/2.0,0.),(1,0.)]   # fires, recoils, runs out again

BOAT=[('hull',(0,-.10,.04),(.76,1.2,.08),'wood',0),('thwart',(0,.12,.15),(.70,.14,.04),'wood_light',0),
      ('gunwale',(-.38,-.10,.20),(.05,1.2,.28),'wood',0),('gunwale',(.38,-.10,.20),(.05,1.2,.28),'wood',0)]
SEAT=dict(root=V(0,.02,-.25),rf=(0,-.20,.0,-10),lf=(0,-.20,.0,-10))
OAR_R=lambda y,z:hand((-.18,y,z),(0,-1,0),(1,0,.35),(-.8,.4,0))
OAR_L=lambda y,z:hand((.18,y,z),(0,-1,0),(-1,0,.35),(.8,.4,0))
clip('Row',1.7,[
    (0,K_(**SEAT,spine=(26,0,0),head=(-12,0,0),rh=OAR_R(-.30,.40),lh=OAR_L(-.30,.40))),
    (.45,K_(**SEAT,spine=(-16,0,0),head=(10,0,0),rh=OAR_R(-.02,.44),lh=OAR_L(-.02,.44))),
    (.60,K_(**SEAT,spine=(-18,0,0),head=(12,0,0),rh=OAR_R(-.02,.38),lh=OAR_L(-.02,.38))),
    (.85,K_(**SEAT,spine=(10,0,0),head=(-4,0,0),rh=OAR_R(-.22,.36),lh=OAR_L(-.22,.36))),
    ],rtool='oar',ltool='oar',props=BOAT,what='rowing the jolly boat: reach, pull, feather, return')


def gangway(t):
    q=walk_pose(t,arms=False);a=t*2*math.pi
    q['rf']=(.05,q['rf'][1]*.7,q['rf'][2],q['rf'][3]);q['lf']=(-.05,q['lf'][1]*.7,q['lf'][2],q['lf'][3])   # one foot before the other
    w=math.sin(a*.5+.3)
    q['root']=q['root']+V(.02*w,0,-.01);q['spine']=(6,0,-9*w);q['head']=(10,0,6*w)
    q['rh']=hand((-.44,-.06,.60+.05*w),(-1,-.1,-.2),(0,-1,0),(-.6,.4,.3))
    q['lh']=hand((.44,-.06,.60-.05*w),(1,-.1,-.2),(0,-1,0),(.6,.4,.3))
    return q


clip('Gangway',2.0,gangway,props=[('plank',(0,-.1,.01),(.18,1.8,.02),'wood_light',0)],what='balancing along the gangway, arms out (in place; two strides a cycle)')


def soaked(t):
    a=t*2*math.pi*6;j=math.sin(a);br=math.sin(t*2*math.pi)     # shiver on top of slow, shaky breaths
    return K_(root=V(0,0,-.03-.01*br),spine=(16+4*br,0,2.5*j),head=(12+3*br,0,3*j),
              rh=hand((.06,-.27,.62+.004*j),(1,.1,-.3),(0,0,1),(-.9,.3,-.3)),
              lh=hand((-.06,-.25,.66+.004*j),(-1,.1,-.3),(0,0,1),(.9,.3,-.3)))


clip('Soaked',1.0,soaked,props=[('drip',(0,-.05,.004),(.34,.30,.008),'water',0)],what='after a rescue: arms wrapped round himself, shivering')
clip('DeckBrace',4.0,deck_brace,what='at his post: braced wide, riding the roll of the deck')
clip('RailGrip',1.8,rail_grip,props=RAIL_SICK,what='gripping the rail through a warning while a sea slams him')


def reverse(keys):return [(1-t,q) for t,q in keys]


# SetDown: the end of a Carry. From Carry's own first frame he lets the load
# go: the arms spring apart and drop, the load falls (gravity at his scale) to
# the ground in front of him, pushed just clear of his toes; he slumps with
# relief, then wipes his brow with the back of his right wrist (the head tips
# into the hand: his arms are too short for the middle of that big forehead),
# flicks the sweat off and ends on Walk's own first frame. One-shot, 2.4 s.
# The load: held on the spine socket until DROP['release'], then a falling
# track (load_track) to rest at DROP['at'] (bottom centre, his rig space).
# The wipe found by search against crew_v15_anatomy, the head surface
# measured with the head tipped into the hand.
DROP={'release':.10/2.4,'at':V(0,-.52,0),'yaw':4}
G_RIG=9.81*C.HEIGHT/1.7                            # gravity at his 1.30 m source scale


def setdown_keys():
    D=2.4;T=lambda sec:sec/D
    hold=carry_pose(0)
    def arms(w,fist_r,fist_l,face=(0,-1,-.3),elbow=(.6,.2,-.8)):
        return {'hands_on_spine':w,'rh':hand(fist_r,face,(0,0,1),(-elbow[0],elbow[1],elbow[2])),
                'lh':hand(fist_l,(-face[0],face[1],face[2]),(0,0,1),elbow)}
    feet=dict(rf=hold['rf'],lf=hold['lf'])
    let_go=K_(**feet,root=V(-.01,-.02,-.05),pelvis=(-4,0,0),spine=(-10,0,0),head=(6,0,0),
              **arms(1.,(-.32,-.34,.48),(.32,-.34,.48)))                       # fists spring apart and drop: the load is free
    fling=K_(rf=(0,-.03,0,0),lf=(0,.03,0,0),root=V(0,0,-.05),spine=(2,0,0),head=(8,0,0),
             **arms(.4,(-.38,-.16,.50),(.38,-.16,.50),face=(0,-.6,-1)))      # arms dropping out to the sides
    slump=K_(rf=(0,0,0,0),lf=(0,0,0,0),root=V(0,0,-.06),pelvis=(2,0,0),spine=(14,0,0),head=(14,0,0),
             rh=hand((-.33,-.10,.43),(-.2,-.3,-1),(0,-1,0),(-.6,.7,0)),lh=hand((.33,-.10,.43),(.2,-.3,-1),(0,-1,0),(.6,.7,0)))
    sigh=K_(root=V(0,0,-.04),spine=(8,0,0),head=(6,0,0))
    WIPE=dict(root=V(0,0,-.02),spine=(6,0,4),head=(14,-10,-16),lh=RELAX_L)
    wipe=lambda y,x:K_(**WIPE,rh=hand((x,y,1.03),(.3,-.2,.95),(0,-1,0),(-1,.3,-.1)))   # the back of the hand to the brow, thumb forward
    flick=K_(root=V(0,0,-.02),spine=(4,0,2),head=(6,-4,-6),lh=RELAX_L,rh=hand((-.46,-.02,.86),(-.6,.2,.75),(0,-1,0),(-.8,.3,-.5)))
    down=K_(root=V(0,0,-.01),spine=(3,0,0),head=(0,0,0))
    raise_=K_(root=V(0,0,-.03),spine=(6,0,2),head=(10,-4,-8),lh=RELAX_L,rh=hand((-.46,-.20,.70),(-.3,-.7,.6),(0,-1,0),(-.8,.3,-.5)))   # the hand comes up clear of his side
    lower=K_(root=V(0,0,-.015),spine=(3,0,1),head=(3,-2,-3),lh=RELAX_L,rh=hand((-.46,-.20,.70),(-.3,-.7,.6),(0,-1,0),(-.8,.3,-.5)))     # and goes down clear of it
    return [(0,hold),(T(.10),let_go),(T(.30),fling),(T(.55),slump),(T(.85),sigh),(T(.98),raise_),
            (T(1.10),wipe(-.14,-.337)),(T(1.32),wipe(-.07,-.338)),(T(1.50),wipe(0,-.326)),
            (T(1.66),flick),(T(1.82),lower),(T(2.02),down),(1,walk_pose(0))]


clip('SetDown',2.4,setdown_keys(),loop=False,rtool='crate',
     what='drops the load off his arms, slumps, wipes his brow and flicks the sweat off; from Carry, into Walk (one-shot)')
CLIPS['SetDown']['drop']=DROP


def load_track(rig,name):
    """Per-frame armature-space matrices of a clip's load (bottom centre):
    on the spine socket until the drop's release, then falling under gravity
    to rest at drop['at'], levelled and turned drop['yaw'] degrees.
    Returns (matrices, release frame, landing frame)."""
    c=CLIPS[name];d=c['drop'];act=bpy.data.actions['Crew_'+name];n=int(act.frame_end)
    sc=bpy.context.scene;keep=(rig.animation_data.action,sc.frame_current);rig.animation_data.action=act
    sock=Matrix.Translation(CARRY_SOCKET);inv=rig.data.bones['spine'].matrix_local.inverted()
    def held(f):
        sc.frame_set(f);return rig.pose.bones['spine'].matrix@inv@sock
    rel=round(d['release']*n);M0=held(rel);p0=M0.translation.copy();q0=M0.to_quaternion()
    at=Vector(d['at']);h=max(1e-3,p0.z-at.z);fall=max(1,round(FPS*math.sqrt(2*h/G_RIG)))
    q1=Quaternion((0,0,1),math.radians(d.get('yaw',0)))
    out=[]
    for f in range(n+1):
        if f<=rel:out.append(held(f));continue
        u=min(1.,(f-rel)/fall)
        p=Vector((p0.x+(at.x-p0.x)*u,p0.y+(at.y-p0.y)*u,p0.z-h*u*u))
        out.append(Matrix.Translation(p)@q0.slerp(q1,u).to_matrix().to_4x4())
    rig.animation_data.action,f0=keep;sc.frame_set(f0)
    return out,rel,rel+fall


def animate_load(o,rig,name):
    """Key a load object (from attach_tool) along load_track for a drop clip,
    as a child of the rig object rather than of the spine bone."""
    track,rel,land=prop_track(rig,name)
    o.parent=rig;o.parent_type='OBJECT';o.parent_bone='';o.matrix_parent_inverse=Matrix.Identity(4)
    o.rotation_mode='QUATERNION';o.animation_data_create()
    o.animation_data.action=bpy.data.actions.new('Load_'+name)
    for f,M in enumerate(track):
        o.matrix_basis=M;o.keyframe_insert('location',frame=f);o.keyframe_insert('rotation_quaternion',frame=f);o.keyframe_insert('scale',frame=f)
    return rel,land



# ---------------------------------------------------------------- props
COLOURS={'wood':'#8A5A36','wood_light':'#C09060','wood_bark':'#6B4A30','iron':'#5E6166','stone':'#9C968C',
         'stone_light':'#B8B2A6','leaf':'#4F8A3A','berry':'#B03A48','soil':'#6A4A30','hot':'#F07A28',
         'stew':'#B8763A','fish':'#9FB4C0','sick':'#9DB04A','water':'#4E86A8','rope':'#C8B080','steel':'#B8BEC6','string':'#EDE6D4','goat':'#C9B79A','horn':'#D9C9A0'}


def box_mesh(name,parts):
    """parts: [(size, centre, colour)] in the object's own frame."""
    me=bpy.data.meshes.new(name);bm=bmesh.new();col=bm.loops.layers.color.new('Col')
    for size,centre,c in parts:
        r=bmesh.ops.create_cube(bm,size=1.)
        for v in r['verts']:v.co=Vector((v.co.x*size[0],v.co.y*size[1],v.co.z*size[2]))+Vector(centre)
        h=COLOURS[c].lstrip('#');rgb=tuple(int(h[i:i+2],16)/255 for i in (0,2,4))   # bmesh byte colours are sRGB
        for f in {f for v in r['verts'] for f in v.link_faces}:
            f.smooth=False
            for l in f.loops:l[col]=(*rgb,1)
    bm.to_mesh(me);bm.free()
    me.color_attributes.active_color=me.color_attributes['Col'];me.color_attributes.render_color_index=0
    o=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(o);o['preview_prop']=True
    return o


S_=TOOL_SCALE


def tool_parts(kind):
    """The game's fallback tools (VillagerActing.BuildTool), scaled, in the
    tool frame: +Y up the haft, +Z the working side. Loads are at his scale
    already, with their bottom centre at the origin (the carry socket)."""
    s=1 if kind in LOADS or kind in LINES else S_
    T={'hammer':[((.035,.34,.035),(0,.13,0),'wood'),((.055,.06,.16),(0,.30,.02),'iron')],
       'mallet':[((.035,.30,.035),(0,.12,0),'wood'),((.09,.09,.16),(0,.27,.0),'wood_light')],
       'axe':[((.04,.67,.04),(0,.285,0),'wood'),((.03,.14,.12),(0,.56,.07),'steel'),((.05,.08,.06),(0,.56,-.02),'iron')],
       'pick':[((.04,.66,.04),(0,.28,0),'wood'),((.05,.05,.46),(0,.58,0),'iron')],
       # the saw's blade runs on out of the fist along the forearm (+Z), teeth on the
       # pinky side (-Y): a real handsaw grip. The game's saw (blade up +Y) needs
       # turning -90 degrees about X for this clip.
       'saw':[((.008,.11,.50),(0,-.01,.30),'steel'),((.035,.10,.13),(0,0,0),'wood')],
       'hoe':[((.038,1.13,.038),(0,.485,0),'wood'),((.17,.025,.15),(0,1.02,.07),'iron')],
       'paddle':[((.03,.66,.03),(0,.27,0),'wood'),((.09,.17,.02),(0,.66,0),'wood_light')],
       'peg':[((.04,.16,.04),(0,-.04,0),'wood')],
       'knife':[((.03,.10,.03),(0,0,0),'wood'),((.008,.12,.035),(0,.11,.0),'steel')],
       'chisel':[((.025,.22,.025),(0,-.06,0),'steel')],
       'shaft':[((.018,.62,.018),(0,.0,0),'wood_light')],
       'bow':[((.03,.95,.03),(0,0,.0),'wood'),((.004,.93,.004),(0,0,-.12),'string')],
       'basket':[((.26,.26,.20),(0,0,.20),'rope')],
       'carrylog':[((.16,.80,.16),(.14,0,-.02),'wood_bark')],
       # the game's placeholder hunting spear (HunterProps): 1.8 m, grip at the origin, butt 0.65 m
       # below it, the head 1.15 m above; +Y to the tip
       'spear':[((.035,1.80,.035),(0,.25,0),'wood'),((.045,.07,.045),(0,1.12,0),'rope'),((.07,.20,.018),(0,1.25,0),'steel')],
       'lanyard':[((.012,1.0,.012),(0,.5,0),'rope')],
       'horn':[((.055,.17,.055),(0,.07,0),'horn'),((.03,.07,.03),(0,.18,0),'horn'),((.016,.04,.016),(0,.235,0),'wood_light')],   # a powder horn, its spout along +Y     # a unit line along +Y, stretched hand to vent (lanyard_track)
       'crate':[((.50,.26,.18),(0,0,.09),'wood'),((.51,.265,.03),(0,0,.04),'wood_bark'),((.51,.265,.03),(0,0,.14),'wood_bark')],
       'sack':[((.30,.26,.30),(.18,0,.03),'rope')],
       'bucket':[((.26,.26,.28),(0,0,.24),'wood'),((.27,.27,.03),(0,0,.12),'iron')],
       'coil':[((.26,.06,.26),(0,0,.12),'rope')],
       'rammer':[((.035,1.1,.035),(0,.45,0),'wood'),((.08,.10,.08),(0,1.0,0),'rope')],
       'linstock':[((.03,.9,.03),(0,.35,0),'wood'),((.05,.06,.05),(0,.82,0),'hot')],
       'oar':[((.04,1.0,.04),(0,-.45,0),'wood'),((.03,.30,.15),(0,-.92,0),'wood_light')]}
    return [((a*s,b*s,c*s),(x*s,y*s,z*s),col) for (a,b,c),(x,y,z),col in T[kind]]


# Astra's worker tools v1 (approved 2026-09-30, art-staging/worker-tools-v1;
# copies in crew-meshy-v15/anims/env/tools). Each FBX is one mesh in the game's
# tool frame, exported as Blender (x,-z,y); read back here as game (x, y, z) =
# Blender (x, z, -y), then scaled to his 1.30 m source. The Saw clip holds its
# saw with the blade along the forearm, so that mesh turns +90 degrees about X
# (blade +Y -> +Z, teeth +Z -> -Y): the game's saw needs the same turn.
LOADS={'crate'}                                     # held on both arms (Carry), not in a hand
LINES={'lanyard'}                                   # a line between his hand and a point on a prop: its own track
ASTRA_TOOLS={'axe':'Axe','hammer':'Hammer','saw':'Saw','hoe':'Hoe','paddle':'StirPaddle'}
TOOL_DIR=Path(__file__).resolve().parents[2]/'crew-meshy-v15/anims/env/tools'
_tool_cache={}


def astra_tool(kind):
    if kind in _tool_cache:return _tool_cache[kind]
    before=set(bpy.data.objects);sc=bpy.context.scene;fps=(sc.render.fps,sc.render.fps_base)
    bpy.ops.import_scene.fbx(filepath=str(TOOL_DIR/(ASTRA_TOOLS[kind]+'.fbx')))
    sc.render.fps,sc.render.fps_base=fps
    new=[o for o in bpy.data.objects if o not in before];src=[o for o in new if o.type=='MESH'][0]
    me=src.data.copy();me.name='Tool_'+kind
    mw=src.matrix_world.copy()
    for o in new:bpy.data.objects.remove(o,do_unlink=True)
    turn=Matrix.Rotation(math.radians(90),3,'X') if kind=='saw' else Matrix.Identity(3)
    for v in me.vertices:
        b=mw@v.co;g=Vector((b.x,b.z,-b.y))
        v.co=(turn@g)*TOOL_SCALE
    gc=me.color_attributes.get('GameColor')
    if gc:gc.name='Col';me.color_attributes.active_color=gc;me.color_attributes.render_color_index=0
    for p in me.polygons:p.use_smooth=False
    _tool_cache[kind]=me;return me


def attach_tool(rig,solver,kind,side):
    if kind in ASTRA_TOOLS:
        o=bpy.data.objects.new('Prop_'+kind,astra_tool(kind));bpy.context.scene.collection.objects.link(o);o['preview_prop']=True
    else:o=box_mesh('Prop_'+kind,tool_parts(kind))
    if kind in LINES:                                # placed every frame by its track (animate_props)
        o.parent=rig;return o
    if kind in LOADS:                                # a load rides on the spine at the carry socket
        o['load']=True;solver.reset();o.parent=rig;o.parent_type='BONE';o.parent_bone='spine'
        bpy.context.view_layer.update();o.matrix_world=rig.matrix_world@Matrix.Translation(CARRY_SOCKET);return o
    s=SIDE_SIGN[side];hb='hand'+side
    m=tool_rest(side)
    solver.reset()
    o.parent=rig;o.parent_type='BONE';o.parent_bone=hb
    bpy.context.view_layer.update();o.matrix_world=rig.matrix_world@m      # the rig may stand anywhere (a building's Worker_Stand)
    return o


def tool_rest(side):
    """A held tool's frame in the rest pose: +Y thumb (forward), +Z along the
    fist, X = Y x Z, at the fist centre."""
    s=SIDE_SIGN[side];Y=V(0,-1,0);Z=V(s,0,0);X=Y.cross(Z)
    m=Matrix((X,Y,Z)).transposed().to_4x4();m.translation=P.P(s*.44,0,.513);return m


def throw_track(rig,name):
    """Per-frame armature-space matrices of a thrown tool (right hand): in the
    fist until throw['release'], then a ballistic arc (gravity at his scale),
    the tool turning to fly point first, its point ending at throw['tip_at']
    after throw['flight'] seconds, and stuck there. (matrices, release, impact)"""
    c=CLIPS[name];d=c['throw'];act=bpy.data.actions['Crew_'+name];n=int(act.frame_end)
    sc=bpy.context.scene;keep=(rig.animation_data.action,sc.frame_current);rig.animation_data.action=act
    rest=tool_rest(RIGHT);inv=rig.data.bones['hand'+RIGHT].matrix_local.inverted()
    def held(f):
        sc.frame_set(f);return rig.pose.bones['hand'+RIGHT].matrix@inv@rest
    rel=round(d['release']*n);M0=held(rel);p0=M0.translation.copy()
    Tf=d['flight'];g=V(0,0,-G_RIG);tip=Vector(d['tip_at']);dirn=nrm(tip-p0)
    for _ in range(8):                             # the grip's end point depends on the arrival direction
        pT=tip-dirn*SPEAR_TIP;v=(pT-p0-.5*g*Tf*Tf)/Tf;dirn=nrm(v+g*Tf)
    hit=rel+round(Tf*FPS);out=[]
    R0=M0.to_quaternion();y0=M0.to_3x3()@V(0,1,0)
    for f in range(n+1):
        if f<=rel:out.append(held(f));continue
        tt=min(Tf,(f-rel)/FPS);p=p0+v*tt+.5*g*tt*tt;fly=nrm(v+g*tt)
        q=y0.rotation_difference(fly)@R0              # point first, its roll kept from the hand
        if f-rel<3:q=R0.slerp(q,(f-rel)/3)            # leaving the fingers over three frames
        out.append(Matrix.Translation(p)@q.to_matrix().to_4x4())
    rig.animation_data.action,f0=keep;sc.frame_set(f0)
    return out,rel,hit


def hands_frame(rig,sv):
    """A frame on his two fists (posed): origin between the fist centres, X
    from the right fist to the left, Z the spine's up made square to it."""
    r=sv.fist(RIGHT)[0];l=sv.fist(LEFT)[0];x=nrm(l-r)
    up=(rig.pose.bones['spine'].matrix@rig.data.bones['spine'].matrix_local.inverted()).to_3x3()@V(0,0,1)
    up=nrm(up-x*up.dot(x));y=up.cross(x)
    M=Matrix((x,y,up)).transposed().to_4x4();M.translation=(r+l)/2;return M


def pickup_track(rig,name):
    """A load picked up: on the ground at pickup['at'] until pickup['grab'],
    then held in the frame of his fists, its offset there sliding from where
    it was gripped to where the carry socket puts it at pickup['seat']; from
    there it rides the socket (so the hand-over to Carry is exact).
    (matrices, grab frame, seat frame)"""
    c=CLIPS[name];d=c['pickup'];act=bpy.data.actions['Crew_'+name];n=int(act.frame_end)
    sc=bpy.context.scene;keep=(rig.animation_data.action,sc.frame_current);rig.animation_data.action=act;sv=Solver(rig)
    rest=Matrix.Translation(Vector(d['at']));grab=round(d['grab']*n);seat=round(d['seat']*n)
    def sock():return rig.pose.bones['spine'].matrix@rig.data.bones['spine'].matrix_local.inverted()@Matrix.Translation(CARRY_SOCKET)
    sc.frame_set(grab);og=hands_frame(rig,sv).inverted()@rest
    sc.frame_set(seat);oe=hands_frame(rig,sv).inverted()@sock()
    out=[]
    for f in range(n+1):
        if f<=grab:out.append(rest.copy());continue
        sc.frame_set(f)
        if f>=seat:out.append(sock());continue     # seated: it rides the carry socket, as in Carry
        u=(f-grab)/(seat-grab);u=u*u*(3-2*u)
        loc=og.translation.lerp(oe.translation,u);q=og.to_quaternion().slerp(oe.to_quaternion(),u)
        out.append(hands_frame(rig,sv)@(Matrix.Translation(loc)@q.to_matrix().to_4x4()))
    rig.animation_data.action,f0=keep;sc.frame_set(f0)
    return out,grab,seat


def gun_offset(name,f,n):
    """How far the clip's gun is run in at frame f (0 = run out), from its
    piecewise-linear CLIPS[name]['gun'] keys [(phase, offset)]."""
    ks=CLIPS[name]['gun'];t=f/max(1,n)
    for (t0,a),(t1,b) in zip(ks,ks[1:]):
        if t0<=t<=t1:return a+(b-a)*((t-t0)/max(1e-6,t1-t0))
    return ks[-1][1]


def animate_env(env,name,n):
    """Key a gun clip's cannon (its root) through the run-out and the recoil."""
    root=[o for o in env.values() if o.parent is None][0];y0=GUN_AT.y
    for f in range(n+1):
        root.location.y=y0+gun_offset(name,f,n);root.keyframe_insert('location',frame=f)


def lanyard_track(rig,name):
    """The firing lanyard: a line from his left fist to the gun's vent (which
    moves with the gun), from lanyard['take'] to lanyard['release']; folded
    away at the vent otherwise. (matrices, take, release)"""
    c=CLIPS[name];d=c['lanyard'];act=bpy.data.actions['Crew_'+name];n=int(act.frame_end)
    sc=bpy.context.scene;keep=(rig.animation_data.action,sc.frame_current);rig.animation_data.action=act;sv=Solver(rig)
    t0=round(d['take']*n);t1=round(d['release']*n);out=[]
    for f in range(n+1):
        vent=GUN_AT+V(0,gun_offset(name,f,n),0)+GUN_VENT
        if t0<=f<t1:
            sc.frame_set(f);h=sv.fist(LEFT)[0];v=vent-h
            R=V(0,1,0).rotation_difference(v.normalized()).to_matrix().to_4x4()
            out.append(Matrix.Translation(h)@R@Matrix.Diagonal((1,v.length,1,1)))
        else:out.append(Matrix.Translation(vent)@Matrix.Diagonal((1,.001,1,1)))
    rig.animation_data.action,f0=keep;sc.frame_set(f0)
    return out,t0,t1


def flying_side(c):
    return LEFT if c.get('lanyard') else RIGHT


def animate_props(rig,name,by_side):
    """Animate whichever of a clip's held props has its own track."""
    c=CLIPS[name];o=by_side.get(flying_side(c))
    if flies(c) and o is not None:animate_load(o,rig,name)


def flies(c):
    """A clip whose tool leaves him (a dropped load, a thrown spear)."""
    return bool(c.get('drop') or c.get('throw') or c.get('pickup') or c.get('lanyard'))


def prop_track(rig,name):
    c=CLIPS[name];return (throw_track if c.get('throw') else pickup_track if c.get('pickup') else lanyard_track if c.get('lanyard') else load_track)(rig,name)


# ---------------------------------------------------------------- bake + export
def bake(rig,solver):
    rig.animation_data_create()
    info={}
    for name,c in CLIPS.items():
        act=bpy.data.actions.new('Crew_'+name);act.use_fake_user=True
        rig.animation_data.action=act
        n=max(2,round(c['seconds']*FPS))
        last={}
        for f in range(n+1):
            t=f/n
            solver.pose(sample(c['keys'],t,c['loop']))
            for pb in rig.pose.bones:
                q=pb.rotation_quaternion.copy()
                if pb.name in last and last[pb.name].dot(q)<0:q.negate();pb.rotation_quaternion=q
                last[pb.name]=q
                pb.keyframe_insert('rotation_quaternion',frame=f);pb.keyframe_insert('location',frame=f)
        act.use_frame_range=True;act.frame_start=0;act.frame_end=n
        act.use_cyclic=c['loop']
        info[name]={'take':'Crew_'+name,'seconds':c['seconds'],'frames':n+1,'loop':c['loop'],'what':c['what'],
                    'tool_right_hand':c['rtool'],'held_left_hand':c['ltool']}
        if c.get('throw'):
            _,rel,hit=throw_track(rig,name);k=1.7/C.HEIGHT;tp=Vector(c['throw']['tip_at'])*k
            info[name]['spear_throw']={'release_frame':rel,'hits_frame':hit,
                'point_lands_game_m':{'x':round(tp.x,3),'up':round(tp.z,3),'forward':round(-tp.y,3)}}
        if c.get('gun'):
            ks=c['gun'];info[name]['cannon']={'run_in_m_game':round(GUN_RECOIL*1.7/C.HEIGHT,3),'elevation_deg':__import__('crew_v15_mill').GUN_ELEV,
                'keys_frame_runin_game_m':[[round(t*n),round(o*1.7/C.HEIGHT,3)] for t,o in ks]}
            if name=='GunFire':info[name]['cannon']['fires_frame']=round(.80/2.0*n)
        if c.get('pickup'):
            at=Vector(c['pickup']['at'])*(1.7/C.HEIGHT)
            info[name]['load_pickup']={'grab_frame':round(c['pickup']['grab']*n),'load_bottom_centre_game_m':{'x':round(at.x,3),'up':round(at.z,3),'forward':round(-at.y,3)},
                'ends_on':'the carry socket (Carry frame 0)'}
        if c.get('drop'):
            _,rel,land=load_track(rig,name)
            at=Vector(c['drop']['at'])*(1.7/C.HEIGHT)
            info[name]['load_drop']={'release_frame':rel,'lands_frame':land,
                'rest_bottom_centre_game_m':{'x':round(at.x,3),'up':round(at.z,3),'forward':round(-at.y,3)},'rest_yaw_deg':c['drop'].get('yaw',0)}
    return info


def main():
    body,rig=P.build()
    body.name='Deckhand_v15'
    bpy.context.scene.render.fps=FPS;bpy.context.scene.render.fps_base=1   # exporters time keys by the scene rate
    solver=Solver(rig)
    info=bake(rig,solver)
    OUT.mkdir(parents=True,exist_ok=True)
    # FBX: rig + CREW_Skin / CREW_Cloth + every clip as its own take
    rig.animation_data.action=None;solver.reset()
    P.export_game_fbx(body,rig,OUT/'deckhand-v15-anims.fbx',bake_anim=True,bake_anim_use_all_actions=True,
        bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0.)
    (OUT/'clips.json').write_text(json.dumps(info,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'tools/blender/source/crew-meshy-v15-anims.blend'))
    print(json.dumps({k:v['frames'] for k,v in info.items()}))


if __name__=='__main__':
    main()
