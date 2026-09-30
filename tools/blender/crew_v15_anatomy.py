"""Anatomy check for the v15 deckhand's animations, frame by frame.

Reports, per clip:
  - clipping: arm, fist, wrist wrap or sleeve vertices inside his torso,
    sash, head, hair, headband or shorts (and the held tool, and his body
    inside the clip's props), with the deepest penetration in metres;
  - elbow: flexion over 150 degrees;
  - forearm twist: pronation or supination beyond 90 degrees from neutral;
  - upper-arm twist: humeral rotation beyond 100 degrees;
  - wrist: bent more than 60 degrees off the forearm.

Inside tests use each body piece's surface: the nearest surface point and
its outward normal (the pieces are closed shells). Arm vertices the tunic
already covers in the rest T-pose are left out, and contact within 12 cm of
the shoulder joint (under the sleeve) is allowed up to 3.5 cm: the rig's
own shoulder give, present even standing still.
"""
import math
import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import crew_meshy_v15_colour as C

ARM_PIECES={'arm','hand','wrist wrap','sleeve'}
BODY_PIECES={'tunic','sash','sash knot','sash tail','head','hair','tuft','headband','headband knot',
             'ear','nose','shorts','shorts cuff','shorts patch'}
LIMITS={'elbow_flex':150,'pronation':90,'humeral':100,'wrist':60,'clip_mm':8,'shoulder_mm':35}


class Checker:
    def __init__(self,body,rig,K):
        self.body=body;self.rig=rig
        bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table()
        self.pieces=[];self.arm_verts={'.L':[],'.R':[]};self.vert_piece={}
        for comp in C.pieces(bm):
            vs=sorted({v.index for f in comp for v in f.verts})
            lo=Vector([min(bm.verts[i].co[j] for i in vs) for j in range(3)])/K
            hi=Vector([max(bm.verts[i].co[j] for i in vs) for j in range(3)])/K
            label=C.classify(lo,hi,len(comp))[1]
            if label=='?':label='plate'
            faces=[[v.index for v in f.verts] for f in comp]
            self.pieces.append((label,vs,faces))
            if label in ARM_PIECES:
                side='.L' if lo.x+hi.x<0 else '.R'
                sh=rig.data.bones['upper_arm'+side].head_local
                keep=[i for i in vs if (bm.verts[i].co-sh).length>.05]
                self.arm_verts[side]+=keep
                for i in keep:self.vert_piece[i]=label
        bm.free()
        # Arm vertices the tunic already covers in the rest (T) pose are part of
        # the shoulder's own overlap, not a clip: leave them out.
        rest=[v.co.copy() for v in body.data.vertices];self._rest=rest
        inside=self._inside_fn(rest)
        for side in self.arm_verts:
            self.arm_verts[side]=[i for i in self.arm_verts[side] if inside(rest[i])[0]==0]

    def _inside_fn(self,co):
        def parity(t,p):
            """Confirm with rays: inside if at least 2 of 3 rays cross the
            surface an odd number of times (the nearest-normal test alone
            misreads points near a crease)."""
            odd=0
            for d in(Vector((0,0,1)),Vector((0,-1,0)),Vector((1,0,0))):
                n=0;o=p.copy()
                for _ in range(16):
                    hit=t.ray_cast(o,d)
                    if hit[0] is None:break
                    n+=1;o=hit[0]+d*1e-4
                odd+=n%2
            return odd>=2
        trees=[]
        for label,vs,faces in self.pieces:
            if label not in BODY_PIECES:continue
            remap={i:k for k,i in enumerate(vs)};pts=[co[i] for i in vs]
            lo=Vector([min(q[j] for q in pts) for j in range(3)]);hi=Vector([max(q[j] for q in pts) for j in range(3)])
            trees.append((label,BVHTree.FromPolygons(pts,[[remap[i] for i in f] for f in faces]),lo,hi))
        def inside(p):
            worst=(0,None)
            for label,t,lo,hi in trees:
                if not all(lo[j]<p[j]<hi[j] for j in range(3)):continue   # only pieces whose box holds the point
                hit=t.find_nearest(p)
                if hit[0] is None:continue
                loc,n,_,d=hit
                if (p-loc).dot(n)<0 and d>worst[0] and parity(t,p):worst=(d,label)
            return worst
        return inside

    def _coords(self):
        dg=bpy.context.evaluated_depsgraph_get();ev=self.body.evaluated_get(dg)
        mw=ev.matrix_world;return [mw@v.co for v in ev.data.vertices]

    def frame(self,tools=(),props=()):
        """Issues for the current frame: list of (kind, detail, amount)."""
        co=self._coords();issues=[]
        inside=self._inside_fn(co)
        pbs=self.rig.pose.bones
        for side,vs in self.arm_verts.items():
            deep=(0,None);where=0;piece=''
            for i in vs:
                d=inside(co[i])
                if d[0]>deep[0]:deep=d;where=(co[i]-self.rig.matrix_world@pbs['upper_arm'+side].head).length;piece=self.vert_piece[i]   # world, the rig may stand anywhere
            part='shoulder' if where<.12 else 'upper arm' if where<.2 else 'forearm' if where<.36 else 'fist'
            limit=LIMITS['shoulder_mm'] if part=='shoulder' else LIMITS['clip_mm']   # the sleeve covers the shoulder's own give
            if deep[0]*1000>limit:
                issues.append(('clip',f'arm{side} {part} ({piece}) into {deep[1]}',round(deep[0],3)))
        for obj in tools:
            mw=obj.matrix_world;deep=(0,None)
            for v in obj.data.vertices:
                d=inside(mw@v.co)
                if d[0]>deep[0]:deep=d
            if deep[0]*1000>LIMITS['clip_mm']:issues.append(('clip',obj.name+' into '+deep[1],round(deep[0],3)))
        for obj in props:                                  # his body inside a prop box
            mw=obj.matrix_world;inv=mw.inverted()
            lo=Vector([min(v.co[j] for v in obj.data.vertices) for j in range(3)])
            hi=Vector([max(v.co[j] for v in obj.data.vertices) for j in range(3)])
            deep=0
            for p in co:
                q=inv@p
                if all(lo[j]<q[j]<hi[j] for j in range(3)):
                    deep=max(deep,min(min(q[j]-lo[j],hi[j]-q[j]) for j in range(3)))
            if deep*1000>LIMITS['clip_mm']:issues.append(('clip','body into '+obj.name,round(deep,3)))
        pb=self.rig.pose.bones;b=self.rig.data.bones
        for side in('.L','.R'):
            u,f,h=pb['upper_arm'+side],pb['forearm'+side],pb['hand'+side]
            ua=(u.tail-u.head).normalized();fa=(f.tail-f.head).normalized();ha=(h.tail-h.head).normalized()
            flex=math.degrees(math.acos(max(-1,min(1,ua.dot(fa)))))
            if flex>LIMITS['elbow_flex']:issues.append(('elbow','arm'+side,round(flex)))
            wrist=math.degrees(math.acos(max(-1,min(1,fa.dot(ha)))))
            if wrist>LIMITS['wrist']:issues.append(('wrist','arm'+side,round(wrist)))
            # forearm twist against the neutral frame carried from the upper arm
            thumb=f.matrix.to_3x3()@b[f.name].matrix_local.to_3x3().inverted()@Vector((0,-1,0))   # rest thumb side, posed
            thumb=thumb-fa*thumb.dot(fa)
            ref=-ua-fa*(-ua).dot(fa)
            if flex<8:                                     # straight arm: the upper arm's own flexion side
                ref=u.matrix.to_3x3()@b[u.name].matrix_local.to_3x3().inverted()@Vector((0,-1,0));ref=ref-fa*ref.dot(fa)
            if thumb.length>1e-6 and ref.length>1e-6:
                ang=math.degrees(thumb.normalized().angle(ref.normalized()))
                if ang>LIMITS['pronation']:issues.append(('twist','forearm'+side,round(ang)))
            # humeral rotation: swing-twist of the upper arm from its rest
            q=(u.matrix.to_3x3()@b[u.name].matrix_local.to_3x3().inverted()).to_quaternion()
            axis=ua;proj=Vector((q.x,q.y,q.z)).dot(axis)
            tw=abs(math.degrees(2*math.atan2(abs(proj),q.w)))
            tw=min(tw,360-tw)
            if tw>LIMITS['humeral']:issues.append(('humeral','upper_arm'+side,round(tw)))
        return issues


def check_clip(checker,rig,action,frames,tools=(),props=(),step=1):
    rig.animation_data.action=action;report={}
    for fr in range(int(action.frame_range[0]),int(action.frame_range[1])+1,step):
        bpy.context.scene.frame_set(fr)
        for kind,what,amount in checker.frame(tools,props):
            k=(kind,what)
            if k not in report or amount>report[k][0]:report[k]=(amount,fr)
    return report
