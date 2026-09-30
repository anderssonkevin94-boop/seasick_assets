# Task animations (v15 deckhand)

One animation per building job and per camp task, on the game's 16-bone deckhand skeleton,
made with `../../tools/blender/crew_meshy_v15_anims.py`. **Not wired into Unity**; that's
for the Unity agent (notes below).

![building jobs](overview-buildings.png)

![basics and tasks](overview-basics-and-tasks.png)

Each clip also has an animated preview, `<Clip>.gif`, and a six-frame strip, `<Clip>-strip.png`.

## Clips

| Take | Building / task | Length | Right hand | Left hand | What he does |
|---|---|---|---|---|---|
| `Crew_Idle` | standing | 2.4 s | - | - | breathing, weight settling, a glance round |
| `Crew_Walk` | walking | 0.9 s | - | - | in place: the game moves him; stride about 0.44 m a cycle |
| `Crew_Chop` | timber, clearing | 1.15 s | axe | - | two-handed axe into a log (timber, clearing) |
| `Crew_Mine` | stone, ore | 1.1 s | pick | - | pickaxe into rock (stone, ore) |
| `Crew_Forage` | spice, food | 1.7 s | - | basket | crouch, pick from a bush, drop it in the basket (spice, food) |
| `Crew_Build` | raising a building | 0.95 s | hammer | - | nailing a board to a post (raising any building) |
| `Crew_Carry` | hauling | 0.9 s | carrylog | - | walking with a log on his right shoulder (the game adds 1-3) |
| `Crew_PickUp` | lifting a load | 1.3 s, one-shot | sack | - | stoop, lift a load to his chest (one-shot) |
| `Crew_Saw` | Sawmill (sawyer) | 0.9 s | saw | - | sawmill: sawing a plank on a trestle |
| `Crew_Farm` | Farm plot (farmhand) | 1.25 s | hoe | - | farm plot: hoeing the rows |
| `Crew_Smith` | Forge (smith) | 0.8 s | hammer | - | forge: hammering hot iron on the anvil |
| `Crew_Cook` | Kitchen (cook) | 1.6 s | paddle | - | kitchen: stirring the pot |
| `Crew_Mill` | Mill (miller) | 1.5 s | peg | - | mill: turning the quern stone by its peg |
| `Crew_Lookout` | Watchtower (lookout) | 4.0 s | - | - | watchtower: leaning on the rail, scanning the horizon, pointing out a sail |
| `Crew_Quarry` | Quarry (quarryman) | 0.95 s | mallet | chisel | quarry: mallet and chisel, dressing stone into brick |
| `Crew_Fletcher` | Fletcher's (fletcher) | 1.5 s | knife | shaft | fletcher: whittling an arrow shaft |
| `Crew_Fisher` | Fishing hut (fisher) | 1.2 s | knife | - | fishing hut: gutting the catch on the prep bench |
| `Crew_Hunt` | hunting | 2.2 s | - | bow | hunting: draw, loose, reach back to the quiver for the next arrow |
| `Crew_SetDown` | dropping a load | 1.3 s, one-shot | sack | - | lower the load to the ground and straighten (one-shot) |

All clips are 30 fps, and every loop's last frame matches its first. Walk and Carry are in place
(the game moves him); the stride is about 0.44 m a cycle at this 1.30 m source size.

## How they are made

Each clip is a few key poses of **targets** (where each fist is and which way its tool points,
where the feet stand, how far the hips drop and the spine bends). Every frame is solved from
them (two-bone IK for arms and legs) and baked, so the fists stay on their tools, two-handed
tools stay in both hands, and the feet stay planted. To change a clip, edit its keys in the
script and rerun it, then `render_v15_anims.py` for the previews.

The tools follow the game's tool frame (`VillagerActing.BuildTool`: origin in the middle of the
fist, +Y up the haft, +Z the working side) and its sizes, and they go in his **right hand, the
bone named `hand.L`**, as `VillagerActing.ToolArm` expects. The props and tools in the previews
(log, anvil, pot, quern, rail, bow...) are **preview only**; the FBX carries the rig, mesh and
clips.

## Files

| File | What |
|---|---|
| `deckhand-v15-anims.fbx` | Rig + `CREW_Skin` / `CREW_Cloth` (skin exported white) + all clips as separate takes |
| `clips.json` | Takes, lengths, loop flags, which tool goes in which hand |
| `<Clip>.gif`, `<Clip>-strip.png`, `overview-*.png` | Previews |
| `../../tools/blender/crew_meshy_v15_anims.py` | Clip definitions, IK solver, bake and export |
| `../../tools/blender/render_v15_anims.py` | Preview renders |
| `../../tools/blender/source/crew-meshy-v15-anims.blend` | Editable source with every action |

FBX re-import check (`verify_crew_meshy_v15.py`): 16 bones, `CREW_Skin` + `CREW_Cloth` (3,135 triangles), every take moving. Blender's
importer names the takes `Deckhand_Rig|Crew_<Clip>`, and Unity may show a similar prefix.

## Notes for the Unity agent

- The game currently plays only Idle and Walk and bends bones in code for the work poses
  (`VillagerActing`, modes Chop, Saw, Hammer, Hoe, Stir, Carry, Bend). Wiring these clips means
  adding states to the crew Animator (or playing them directly) and switching them off in
  `VillagerActing` for the jobs that have a clip. `CampWorker.ModeAt` and `ModeFor` already
  map each building position and resource to a job.
- Suggested mapping:
  - sawyer → Saw, farmhand → Farm, smith → Smith, cook → Cook, miller → Mill, lookout → Lookout,
    quarryman → Quarry, fletcher → Fletcher, fisher → Fisher
  - timber and clearing → Chop, stone and ore → Mine, spice and food → Forage
  - raising a building → Build, hauling → Carry, the bend at a pile → PickUp / SetDown,
    hunting → Hunt
- New tools the game doesn't have yet: pickaxe, mallet and chisel, quern peg, knife, arrow
  shaft, bow, basket (the clips work without them; they only show in the previews).
- Walk and Carry need their playback speed matched to the move speed.
- **Not yet tested in Unity:** the clips on the imported rig, tool placement on the real tool
  meshes, and blending between clips.
