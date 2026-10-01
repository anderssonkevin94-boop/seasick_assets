# Level 2 concepts: checklist (session 2026-10-01)

Everything made on branch `claude/beautiful-mendel-wxvyo6` of `anderssonkevin94-boop/seasick_assets`,
for handing to the Unity agent. All of it is **concept art, staged here, not imported**. Nothing was
committed to the game repo. Each folder's README has the details.

## ⚠ First: the Crank clip is not in the game yet

The game repo's last clip import came from **`claude/sharp-wright-iy5jr7`** (commit `a8b6125`), not this
branch. The `Crew_Crank` clip and the `mill2` environment exist only here. Both branches changed the same
pipeline files: `crew_meshy_v15_anims.py`, `crew_v15_mill.py`, `check_v15_clip.py`, `render_v15_anims.py`,
`render_v15_clip_views.py`, `export_v15_viewer.py`, the anims README, and the generated `clips.json`, FBX,
GLB, viewer and .blend.

- [ ] Merge this branch's code into the clip branch (or the reverse). Then **regenerate** the generated files
      with the pipeline. Don't hand-merge the FBX, .blend or GLB.
- [ ] Run `check_v15_clip.py -- Crank Saw Chop`. All three must print `clean`.
- [ ] Re-import the clips into the game so `Crew_Crank` is there.

## 1. Sawmill level 2: `sawmill-l2-concept/`

- [x] Brick-footed saw shed on the level 1 plot (7.56 × 5.85 m, ridge 3.83 m < 3.84 m). The script asserts both.
- [x] Board gable roof, open gable to the front. Brick plinth at the level 1 platform height (0.16 m).
- [x] Level 1 kit reused unchanged: input cradle, `Input_Log_01..06`, output rack, `Output_Plank_01..12`
      (upper six recoloured as fine boards), trade sign (own post, brass "II" plate), and all
      `MillL1Import` markers except `Worker_Stand`.
- [x] **Saw wheel** (Kevin's change): iron circular blade, 2 cm thick, **no guard** (removed on request),
      axle under the table. Gravity log feed (rope, sheave, hanging stone).
- [x] **Crank:** a bent iron crank across in front of the worker, two bearing posts, a flywheel on his left,
      a belt to the saw (1:5).
- [x] `Worker_Stand` **moved** to (−0.95, 0.62) (Blender coordinates). He faces **+X** along the table; the
      clip's own root turns him 90°.
- [x] Grindstone and a spare blade (saw blade wear), canvas lean-to over the output rack.
- [x] **Wheels animated:** take `Mill2_Crank`, 1.2 s. `Mill2_CrankWheel` turns once and `Saw2_Wheel` 5 times,
      both turning about their own origins. The saw's top teeth run toward the log.
- [x] Five-level plan in the README (levels 3–5 are proposals only).
- [ ] Unity: an importer for the building (like `MillL1Import`). Play `Crew_Crank` and `Mill2_Crank` together,
      both looping, from frame 0.
- [ ] Unity: the sawyer must face +X at level 2 (or let the clip's root yaw do it).
- [ ] Not made: state-kit variants for the saw table (loaded, cutting, finished), and the log sliding into
      the blade.

## 2. Crew clip `Crew_Crank`: `crew-meshy-v15/anims/`

- [x] 1.2 s loop, both hands on the crank, lean 18–30° with the stroke. In `deckhand-v15-anims.fbx` with
      every other clip (36 takes).
- [x] Crank geometry found by a search scored by the anatomy check. **Clean on every frame**, the crank
      itself against his body included. Saw and Chop re-checked: clean.
- [x] GIF, filmstrip, five-angle sheet, viewer entry. `verify_crew_meshy_v15.py` passes (36 takes move,
      lengths match).
- [ ] The viewer page artifact (https://claude.ai/artifact/GcDxNt3L667f99DjPvV5Kt) was **not republished**.
      Its local file is updated.
- [ ] See ⚠ above: not yet in the game.

## 3. Wall level 2: `wall-l2-concept/` (`wall-l2-kit.fbx`)

- [x] Stone base (1.15 m, three courses + capstones), squared light-oak timbers on an oak sill, iron bands,
      rear rails. Stone pillars 0.56 m square, 3.05 m high.
- [x] Revisions from Kevin: fewer and chunkier stones, lighter stone and wood, crude uneven bevels (seeded,
      repeatable).
- [x] Pieces on the level 1 palisade's snap contract (start-end roots, `__Snap_Start`/`__Snap_End`, 0.25 m
      spacing, `__Post_Center`): `Wall2_Run_1m_A/B/C`, `Wall2_Filler_050m`, `Wall2_Filler_025m`,
      `Wall2_Breached_1m`, `Wall2_Post`. Any mix tiles with no seam.
- [x] Bend bug fixed: one pillar per corner, turned halfway between the two sections.
- [ ] Unity: **the wall adapter needs the same rule**: one pillar per node, turned to the bisector, never one
      per segment end.
- [ ] Unity: trimming at arbitrary lengths and angles (same open work as level 1), an importer.

## 4. Gate level 2: `wall-l2-concept/` (`gate-l2-kit.fbx`)

- [x] 3 m module on the level 1 gate's contract: `Gate2__Snap_Start/End`, `__Passage`, its own two pillars
      (`__Post_Center_Left/Right`), leaves under `Gate2_Hinge` / `Gate2_Hinge_Right`, opening −100° / +100°
      outward to −Y.
- [x] Stone pillars 3.6 m, plank leaves with strap hinges, ring pulls, Z-braced ledges.
- [x] **Top beam removed** (Kevin). Hinge pins kept as `Gate2_Pintles`.
- [x] Swing check against the real stones: 2.6 cm clearance. The build fails on contact.
- [x] Breached state `Gate2_Breached`.
- [ ] **Decide:** the clear opening is **1.88 m**, against level 1's 2.22 m, because the stone pillars are
      wider inside the same 3 m. Enough for crew on foot; carts would need a wider module.
- [ ] Unity: don't place a wall pillar on the gate's two nodes. Gate open/close control, an importer.

## 5. Watchtower level 2: `tower-l2-concept/` (`watchtower-lvl2.fbx`)

- [x] Same 2.6 × 2.6 m plot on the ground. Stone legs, oak frame with X-braces and knee braces.
- [x] **Deck 4.2 × 4.2 m** (about 3× level 1) for the cannon to turn. Low oak parapet 0.72 m, so the gun
      fires over it.
- [x] Checked against Astra's cannon: the wheels sweep 0.92 m inside a 1.96 m parapet, with 0.89 m behind
      the breech for a gunner. The ladder hatch sits outside the wheels' sweep.
- [x] Deck **4.61 m** (`WatchtowerGun.DeckHeight` unchanged). `Ladder_Bottom`, `Ladder_Top`, `Lookout_Anchor`
      unchanged.
- [ ] Unity: overall height is **5.65 m** (was 5.37). Update `BuildPlan` `ridge` for level 2.
- [ ] Unity: the deck overhangs the plot to ±2.1 m at height. Selection, occlusion and wall-tower snapping
      should allow for it.
- [ ] Unity: check that `WatchtowerGun`'s own primitive gun (scale 1.1) fits the same circles. Importer,
      colliders, the hatch in the walking logic.

## Scripts (`tools/blender/`)

| Script | Makes |
|---|---|
| `sawmill_l2_concept.py` | Sawmill level 2 FBX with its wheel take, renders |
| `render_l2_crank_gif.py` | The sawmill-at-work GIFs |
| `crew_meshy_v15_anims.py` (+ `check_v15_clip.py`, renders, viewer) | `Crew_Crank` among all clips |
| `crew_v15_mill.py` | `load_env('mill2')`: the level 2 mill as a clip environment |
| `wall_l2_concept.py` | Wall pieces, renders |
| `gate_l2_concept.py` | Gate, breached gate, swing check, renders |
| `tower_l2_concept.py` | Watchtower, gun-clearance and plot checks, traverse GIF |

Rebuild needs the venv (`python3.11 -m venv venv && venv/bin/pip install bpy==5.0.1 pillow numpy`) and
`EGL_PLATFORM=surfaceless`. The tower, wall and gate scripts fetch their level 1 references from the
game repo's LFS on first run.

## Commits on this branch (newest last)

`cf313f7` sawmill concept and the 5-level plan · `4c63274` ignore venv · `f3b8d02` saw wheel and crank ·
`50783ea` crank animation (deckhand and wheels) · `e66bfc5` wall · `6a90b7f` chunkier, lighter ·
`8bee53a` crude bevels · `3fe28f6` one pillar per bend · `7d0f5e6` gate · `a15a428` fillers, breached
run, gate without the top beam · then the watchtower and this checklist.

## Next (Kevin)

- [ ] The level 1 mill (asked for after the watchtower).
