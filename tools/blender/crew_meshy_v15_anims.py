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
DEFAULT={'root':V(0,0,0),'yaw':0.,'pelvis':(0,0,0),'spine':(0,0,0),'head':(0,0,0),
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
# one-handed, from his right side, driven by his whole upper body: wound
# right with the axe cocked behind the right shoulder, unwinding left to whip
# the blade into the trunk's front, holding, pulling free. One-handed on
# purpose: with his short arms and round belly every two-handed side swing
# put the upper hand's arm 5-8 cm through his body at contact. The axe is in
# his right hand at the end of the haft, the game's own grip.
# CampWorker.Stand puts him 1.1 m (game) from the trunk's centre: no offset.
# Key poses found by search against crew_v15_anatomy (no clipping, joints in
# range) with the blade exactly on the notch at contact.
AXE_EDGE=V(0,.56,.13)*TOOL_SCALE                  # the edge's middle in the tool frame (Astra's manifest)
AXE_SECOND=.11*TOOL_SCALE                          # second hand up the haft (two-handed tools)
CHOP_BACK=0.
CHOP_HEIGHT=.62                                    # the notch, above his feet: his chest, where the arm swings level
TREE_D=.84                                         # 1.1 m (game) at his scale; matches crew_v15_mill.TREE_STAND
TRUNK_R=.27                                        # the bark at his chest height (measured on the placed tree), less a 2 cm bite: see CHOP_BITE
CHOP_BITE=.02
CHOP_WIND,CHOP_HIT=-45,-10                         # upper-body twist (degrees, - is to his right): wound, at contact


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


def twist(sy):return dict(pelvis=(0,sy*.35,0),spine=None,head=(0,-sy*.75,0))


def chop_keys():
    T=V(0,-TREE_D,CHOP_HEIGHT)
    notch=T+nrm((math.cos(math.radians(100)),math.sin(math.radians(100)),0))*(TRUNK_R-CHOP_BITE)   # the trunk's front, a touch to his right, the blade 2 cm into the bark
    into=nrm((T-notch).normalized()+V(0,0,-.4))
    feet=dict(rf=(-.03,.07,0,0),lf=(.03,-.07,0,0))
    balance_top=hand((.36,-.30,.60),(.3,-.8,-.3),(0,0,1),(.9,.3,-.2))
    balance_hit=hand((.38,-.10,.52),(.4,-.2,-1),(0,-1,0),(.8,.6,0))
    G=Matrix.Rotation(math.radians(CHOP_WIND),3,'Z')
    top=K_(root=V(0,0,-.03),**feet,pelvis=(0,CHOP_WIND*.35,0),spine=(4,CHOP_WIND*.65,-4),head=(4,-CHOP_WIND*.75,0),
           rh=hand(tuple(G@V(-.36,-.12,.88)),G@nrm((-.3,-.3,.9)),G@nrm((-.3,.45,.85)),(-.9,.4,0)),lh=balance_top)
    hit_rh=axe_hand(notch,V(-.3,-.3,.58),into,(-.9,.3,-.3))
    hit=K_(root=V(0,0,-.05),**feet,pelvis=(0,CHOP_HIT*.4,0),spine=(10,CHOP_HIT,0),head=(8,-CHOP_HIT*.6,0),rh=hit_rh,lh=balance_hit)
    pull=dict(hit_rh);pull['grip']=hit_rh['grip']-hit_rh['haft']*.07
    out=K_(root=V(0,0,-.04),**feet,pelvis=(0,-6,0),spine=(8,-16,0),head=(6,8,0),rh=pull,lh=balance_hit)
    def wound(sy,grip,face,haft,elbow,balance):     # a pose with the upper body twisted sy, hand targets turning with it
        R=Matrix.Rotation(math.radians(sy),3,'Z')
        return K_(root=V(0,0,-.04),**feet,pelvis=(0,sy*.35,0),spine=(6,sy*.65,-2),head=(6,-sy*.75,0),
                  rh=hand(tuple(R@V(*grip)),R@nrm(face),R@nrm(haft),elbow),lh=balance)
    balance_mid=hand((.36,-.22,.62),(.3,-.8,-.3),(0,0,1),(.9,.3,-.2))
    down=wound(-22,(-.50,-.16,.70),(-.6,-.6,.4),(-.6,.7,.4),(-.9,.3,-.2),balance_mid)    # the axe swung out wide round his right
    up=wound(-24,(-.40,-.10,.90),(-.5,.1,.85),(-.3,.4,.85),(-.9,.4,0),balance_mid)       # lifted back round his right, clear of his head
    low=wound(-14,(-.46,-.18,.52),(-.8,-.4,-.4),(-.3,-.8,-.4),(-.8,.5,0),balance_mid)   # pulled free, the axe dropped to his right side
    lift=wound(-18,(-.44,-.16,.74),(-.8,-.3,.5),(-.5,-.4,.75),(-.9,.1,-.4),balance_mid)  # halfway up, the axe coming upright
    return [(0,top),(.16,top),(.30,down),(.40,hit),(.56,hit),(.66,out),(.76,low),(.88,down)]   # recovery retraces the swing's own path


clip('Chop',1.3,chop_keys(),rtool='axe',what='felling a tree: a one-handed side swing from his right, the whole upper body unwinding into it')
CLIPS['Chop']['env']='tree'

PICK_ROCK=[('rock',(0,-.56,.07),(.34,.30,.16),'stone',0)]
clip('Mine',1.1,[
    (0,K_(root=V(0,0,-.03),spine=(-4,0,0),head=(-6,0,0),rh=swing_hand((-.09,.02,1.02),.35,.94),lh={'on_tool':.12,'elbow':V(.6,.3,-.4)})),
    (.28,K_(root=V(0,0,-.03),spine=(-6,0,0),head=(-4,0,0),rh=swing_hand((-.08,.03,1.03),.42,.9),lh={'on_tool':.12,'elbow':V(.6,.3,-.4)})),
    (.45,K_(root=V(0,0,-.10),spine=(34,0,0),head=(14,0,0),rh=swing_hand((-.04,-.28,.40),-.62,-.78,(-.5,.4,-.2)),lh={'on_tool':.12,'elbow':V(.6,.4,0)})),
    (.56,K_(root=V(0,0,-.10),spine=(32,0,0),head=(14,0,0),rh=swing_hand((-.04,-.27,.43),-.6,-.8,(-.5,.4,-.2)),lh={'on_tool':.12,'elbow':V(.6,.4,0)})),
    (.78,K_(root=V(0,0,-.06),spine=(10,0,0),rh=swing_hand((-.07,-.10,.82),.1,1.,(-.6,.4,-.3)),lh={'on_tool':.12,'elbow':V(.6,.3,-.3)})),
    ],rtool='pick',props=PICK_ROCK,what='pickaxe into rock (stone, ore)')

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


def carry_log(q,sw):
    q['rh']=hand((-.31,-.03,.86),(0,0,1),(0,1,0),(-.8,.2,-.6))
    q['head']=(0,6,0)


clip('Carry',.9,lambda t:walk_pose(t,carry=carry_log),rtool='carrylog',what='walking with a log on his right shoulder (the game adds 1-3)')
clip('PickUp',1.3,[
    (0,K_()),
    (.45,K_(root=V(0,0,-.17),spine=(46,0,0),head=(20,0,0),rh=hand((-.13,-.36,.13),(0,-.2,-1),(0,-1,.2),(-.7,.4,0)),lh=hand((.13,-.36,.13),(0,-.2,-1),(0,-1,.2),(.7,.4,0)))),
    (.6,K_(root=V(0,0,-.17),spine=(44,0,0),head=(20,0,0),rh=hand((-.13,-.35,.15),(0,-.2,-1),(0,-1,.2),(-.7,.4,0)),lh=hand((.13,-.35,.15),(0,-.2,-1),(0,-1,.2),(.7,.4,0)))),
    (1,K_(spine=(4,0,0),rh=hand((-.14,-.24,.56),(.3,-1,0),(0,0,1),(-.7,.4,-.3)),lh=hand((.14,-.24,.56),(-.3,-1,0),(0,0,1),(.7,.4,-.3)))),
    ],loop=False,ltool=None,rtool='sack',what='stoop, lift a load to his chest (one-shot)')

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

clip('Hunt',2.2,[
    (0,K_(yaw=0,spine=(0,-12,0),head=(0,10,0),lh=hand((.20,-.34,.80),(.25,-1,.1),(0,0,1),(.6,.3,-.2)),rh=hand((.05,-.30,.80),(1,-.3,0),(0,0,1),(-.7,.3,-.3)))),
    (.15,K_(spine=(0,-12,0),head=(0,10,0),lh=hand((.20,-.34,.80),(.25,-1,.1),(0,0,1),(.6,.3,-.2)),rh=hand((.05,-.30,.80),(1,-.3,0),(0,0,1),(-.7,.3,-.3)))),
    (.50,K_(spine=(0,-16,0),head=(0,14,0),lh=hand((.20,-.36,.80),(.25,-1,.1),(0,0,1),(.6,.3,-.2)),rh=hand((-.08,-.06,.86),(1,-.3,0),(0,0,1),(-.8,.5,.2)))),
    (.62,K_(spine=(0,-16,0),head=(0,14,0),lh=hand((.20,-.36,.80),(.25,-1,.1),(0,0,1),(.6,.3,-.2)),rh=hand((-.08,-.06,.86),(1,-.3,0),(0,0,1),(-.8,.5,.2)))),
    (.68,K_(spine=(0,-16,0),head=(0,14,0),lh=hand((.20,-.37,.80),(.25,-1,.1),(0,0,1),(.6,.3,-.2)),rh=hand((-.16,.02,.86),(1,-.1,.3),(0,0,1),(-.8,.5,.3)))),
    (.85,K_(spine=(0,-10,0),head=(0,8,0),lh=hand((.20,-.34,.78),(.25,-1,.1),(0,0,1),(.6,.3,-.2)),rh=hand((-.20,.06,.92),(0,0,1),(0,1,0),(-.8,.3,-.3)))),
    ],ltool='bow',what='hunting: draw, loose, reach back to the quiver for the next arrow')


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

GUN_RAM=[('carriage',(.62,-.02,.10),(.60,.30,.20),'wood',0),('barrel',(.60,-.02,.30),(.70,.15,.15),'iron',0)]
RAM_R=lambda x:hand((x,-.20,.42),(0,-1,0),(1,0,0),(-.8,.3,-.2))
RAM_L={'on_tool':.20,'elbow':V(.6,.5,-.2)}
clip('GunRam',1.5,[
    (0,K_(root=V(0,0,-.05),spine=(14,24,0),head=(6,20,0),rh=RAM_R(-.20),lh=RAM_L)),
    (.25,K_(root=V(.02,0,-.06),spine=(20,28,0),head=(6,22,0),rh=RAM_R(-.02),lh=RAM_L)),
    (.45,K_(root=V(0,0,-.05),spine=(14,24,0),head=(6,20,0),rh=RAM_R(-.18),lh=RAM_L)),
    (.70,K_(root=V(.02,0,-.06),spine=(20,28,0),head=(6,22,0),rh=RAM_R(-.02),lh=RAM_L)),
    ],rtool='rammer',props=GUN_RAM,what='gunner: ramming the charge home, twice (gun on his left, muzzle beside him)')
GUN_FIRE=[('carriage',(.34,-.20,.10),(.30,.60,.20),'wood',0),('barrel',(.34,-.28,.30),(.15,.70,.15),'iron',0)]
TOUCH=nrm((.46,.29,-.28))
clip('GunFire',1.8,[
    (0,K_(spine=(4,10,0),head=(0,20,0),rh=hand((-.20,-.10,.60),(0,-.4,-1),TOUCH,(-.7,.4,-.2)))),
    (.30,K_(root=V(.02,0,-.04),spine=(18,26,0),head=(10,30,0),rh=hand((-.12,-.25,.66),nrm(TOUCH.cross(V(0,0,1))),TOUCH,(-.7,.4,-.3)))),
    (.42,K_(root=V(.02,0,-.04),spine=(18,26,0),head=(10,30,0),rh=hand((-.12,-.25,.66),nrm(TOUCH.cross(V(0,0,1))),TOUCH,(-.7,.4,-.3)))),
    (.52,K_(root=V(-.04,.05,-.06),spine=(-6,-20,-8),head=(-10,-45,-10),rh=hand((-.30,-.02,.64),(-.3,-.3,-1),TOUCH,(-.8,.4,-.2)),
            lh=hand((.20,-.22,.80),(-.5,-.5,.8),(0,0,1),(.8,.2,-.2)))),
    (.75,K_(root=V(-.03,.04,-.05),spine=(-2,-12,-4),head=(-4,-30,-4),rh=hand((-.28,-.04,.60),(-.3,-.3,-1),TOUCH,(-.8,.4,-.2)),
            lh=hand((.24,-.18,.66),(-.3,-.6,.6),(0,0,1),(.8,.3,-.2)))),
    (1,K_(spine=(4,10,0),head=(0,20,0),rh=hand((-.20,-.10,.60),(0,-.4,-1),TOUCH,(-.7,.4,-.2)))),
    ],loop=False,rtool='linstock',props=GUN_FIRE,what='gunner: touching off the gun with the linstock and flinching from the blast (one-shot)')

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


clip('SetDown',1.3,reverse(CLIPS['PickUp']['keys']),loop=False,rtool='sack',what='lower the load to the ground and straighten (one-shot)')


# ---------------------------------------------------------------- props
COLOURS={'wood':'#8A5A36','wood_light':'#C09060','wood_bark':'#6B4A30','iron':'#5E6166','stone':'#9C968C',
         'stone_light':'#B8B2A6','leaf':'#4F8A3A','berry':'#B03A48','soil':'#6A4A30','hot':'#F07A28',
         'stew':'#B8763A','fish':'#9FB4C0','sick':'#9DB04A','water':'#4E86A8','rope':'#C8B080','steel':'#B8BEC6','string':'#EDE6D4'}


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
    tool frame: +Y up the haft, +Z the working side."""
    s=S_
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
    s=SIDE_SIGN[side];hb='hand'+side
    # tool frame in the rest pose: +Y thumb (forward), +Z along the fist, X = Y x Z
    Y=V(0,-1,0);Z=V(s,0,0);X=Y.cross(Z)
    m=Matrix((X,Y,Z)).transposed().to_4x4();m.translation=P.P(s*.44,0,.513)
    solver.reset()
    o.parent=rig;o.parent_type='BONE';o.parent_bone=hb
    bpy.context.view_layer.update();o.matrix_world=rig.matrix_world@m      # the rig may stand anywhere (a building's Worker_Stand)
    return o


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
