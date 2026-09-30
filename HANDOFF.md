# Handoff: SeaSick crew (v15 deckhand) and his animations

Read this first in a new session. Branch `claude/focused-cerf-rrqoy5` of
`anderssonkevin94-boop/seasick_assets` holds all of the work, pushed.

## Ground rules from Kevin

- **Never commit to the Unity repo** (`anderssonkevin94-boop/seasick`, branch `ships-into-unity`).
  Read it only. Another agent (the Unity agent) imports everything from this repo.
- Show an image before fiddling with small details. Kevin reviews through renders, GIFs and the
  viewer page.
- **Anatomy first:** no arm, hand, sleeve or tool through the body, and joints within human
  range. He is a big-headed chibi, but his proportions must be respected.
- Level 1 buildings get their own work animations. The work changes as buildings level up.
- He stays **1.7 m in game** (`AstraPlaytestImport` scales the 1.30 m source to 1.7 m).

## The character

`crew-meshy-v15/`: Kevin's paid Meshy model ("Red Bandana Adventure"), coloured, rigged to
the game's 16-bone deckhand skeleton, fists closed, split into parts. The README has the details.

| File | What |
|---|---|
| `deckhand-v15-rigged.fbx` | Game drop-in: 16 v5 bones, `CREW_Skin` (white) + `CREW_Cloth`, T rest pose |
| `anims/deckhand-v15-anims.fbx` | The same, plus all 35 clips as takes `Crew_<Clip>` |
| `parts/deckhand-v15-parts.fbx` | 21 named body-part objects on the same rig (for custom versions) |
| `anims/README.md` | Every clip, the game-state mapping and notes for the Unity agent |

His measurements, at the 1.30 m source size: shoulder joints ±0.22 m (inside the tunic's ±0.25 m);
belly 0.26 m in front; arm reach shoulder to fist centre 0.42 m; head x ±0.21, z 0.85-1.27 with the hair.
Tools go in his **right hand, the bone named `hand.L` (Blender -X)**, as the game's
`VillagerActing.ToolArm` expects. Tool frame (game): origin at the fist centre, +Y up the haft,
+Z the working face.

## Tools and environment

- Blender through the pip `bpy` 5.0.1 module (Python 3.11), with numpy and Pillow. Rebuild the venv:
  `python3.11 -m venv venv && venv/bin/pip install bpy==5.0.1 pillow numpy`. Workbench renders
  need `EGL_PLATFORM=surfaceless`. Never name a script `inspect.py` (it breaks bpy).
- Git LFS files from the game repo: fetch them from
  `https://media.githubusercontent.com/media/anderssonkevin94-boop/seasick/ships-into-unity/<path>`
  (plain curl works; `git lfs` is not installed).
- The Blender FBX importer resets the scene's frame rate to the file's (24). Every loader here
  restores 30 fps. Keep that, or clips export 25% too long.

## Pipeline (tools/blender/)

| Script | Does |
|---|---|
| `crew_meshy_v15_colour.py` | Meshy FBX to coloured mesh (pieces classified by bounding box) |
| `crew_meshy_v15_pose.py` | Rig, weights per piece, `close_fists`, idle pose, game FBX export (`export_game_fbx`) |
| `crew_meshy_v15_anims.py` | **All clips**: target-and-IK `Solver`, clip keys, bake, FBX. The main file |
| `crew_v15_anatomy.py` | Per-frame anatomy check: clipping (nearest-normal + ray parity), elbow, forearm twist, humeral twist, wrist |
| `check_v15_clip.py -- Clip ...` | Runs the check on every frame, with tools, props and environment |
| `render_v15_clip_views.py -- Clip` (env `OUT=dir`) | Five-angle review sheet at key frames |
| `render_v15_anims.py -- Clip ...` | GIF and filmstrip per clip in `crew-meshy-v15/anims/` |
| `crew_v15_mill.py` | Environments: `load_env('mill')` (lowered level 1 lumber mill), `load_env('tree')` (Astra's tree) |
| `mill_l1_lowbench.py` | Makes the lowered-bench mill FBX from the game's kit |
| `export_v15_viewer.py` | GLB + the self-contained viewer page `crew-meshy-v15/viewer/index.html` |
| `verify_crew_meshy_v15.py` | FBX re-import check (names, weights, white skin, every take moves, lengths) |

Rebuild order after changing a clip: `crew_meshy_v15_anims.py`, then `check_v15_clip.py -- <Clip>`
(it must print `clean`), then the renders, then `verify_crew_meshy_v15.py`, then
`export_v15_viewer.py`, then publish the viewer (Artifact tool, same file path; the URL is
https://claude.ai/artifact/GcDxNt3L667f99DjPvV5Kt). After a rig change, rerun
`crew_meshy_v15_pose.py` first.

## How to make a clip anatomically right (what worked)

1. Put him in the real environment (a building's `Worker_Stand`, or where `CampWorker.Stand`
   puts him) and measure it against his proportions first.
2. Author **key poses as targets** (fist position, knuckle direction `face`, thumb/haft
   direction, elbow hint), and let the solver do the IK.
3. **Search, don't guess**: grid-search each key pose's parameters, score each with the anatomy
   check, reach misses, twist clamps and the tool's working point against its target, and keep
   a zero-score pose. The scripts under `tmp` in the old session did this; recreate them as needed.
4. Check **every frame** (`check_v15_clip.py`): in-between frames clip even when the keys don't.
   Route the tool around the head with extra keys (the recovery can retrace the swing's path).
5. Allowed: up to 3.5 cm of contact within 12 cm of the shoulder (under the sleeve). Anything
   else over 8 mm is a clip.

## Clip status (35 in the FBX)

| Status | Clips |
|---|---|
| **Reworked and clean on every frame** | `Saw` (level 1 lumber mill, lowered bench, sawing the log), `Chop` (Astra's tree, one-handed flat bat swing into the trunk's right flank) |
| Made before the anatomy rules; **need rework the same way** | Idle, Walk, Mine, Forage, Build, Carry, PickUp, SetDown, Hunt, Farm, Smith, Cook, Mill, Lookout, Quarry, Fletcher, Fisher, SickSway, SickWalk, SickClutch, SickRail, SickCollapse, SickKneel, Bail, ThrowLine, HaulLine, GunRam, GunFire, Row, Gangway, Soaked, DeckBrace, RailGrip |

Kevin goes down the list one clip at a time. Ask which is next.

## Decisions already made

- Level 1 lumber mill: the bench is lowered from 1.33 m to 0.78 m, and the mallet and wedge are
  removed (`Mallet_Tool` kept as an empty; `MillL1Import` requires the name). The job is sawing the log.
- He stands 10 cm behind the mill's `Worker_Stand` (baked into the root) so his belly clears the log.
- Chop is one-handed: every two-handed side swing put one arm through his belly. It uses the
  game's own grip. The tree is at its smallest game size (9 m), and the notch is at chest height,
  below the tree's `Trunk_Target`.
- The saw's blade runs along the forearm, so the game's saw mesh turns +90° about X for that clip.
- Rig: the sleeves' underside near the armpit blends 55% to the spine.

## Game-repo references (read only)

- Crew animation today: `Scripts/Dev/Editor/AstraPlaytestImport.cs` (Idle and Walk only) and
  `Scripts/World/VillagerActing.cs` (code-bent work poses and `ToolArm`).
- Jobs: `Scripts/World/BuildPlan.cs` (positions), and `CampWorker.ModeAt` / `ModeFor`.
- Crew states: `Scripts/Crew/CrewAgent.cs` (`State` enum, `Sickness01`, rail and bailing).
- Level 1 mill: `Scripts/Dev/Editor/MillL1Import.cs` and `Art/MillL1/Models/lumber-mill-state-kit.fbx`.
- Astra's tools: `art-staging/worker-tools-v1/`. Tree: `art-staging/tree-b1-astra-v1/`.
  Tree sizes: `WorldScale.TreeMin/Max`.
