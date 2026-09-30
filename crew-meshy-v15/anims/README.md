# Task, ship and seasickness animations (v15 deckhand)

One animation per building job and per camp task, on the game's 16-bone deckhand skeleton,
made with `../../tools/blender/crew_meshy_v15_anims.py`. **Not wired into Unity**; that's
for the Unity agent (notes below).

![building jobs](overview-buildings.png)

![basics and tasks](overview-basics-and-tasks.png)

![seasickness](overview-seasick.png)

![aboard ship](overview-ship.png)

Each clip also has an animated preview, `<Clip>.gif`, and a six-frame strip, `<Clip>-strip.png`.

## Viewer

`../viewer/index.html` plays every clip in 3D in a browser: pick a clip, play, pause, step frames,
scrub, change speed, turn and zoom, and show or hide the clip's tools and props. The model is
embedded, so the one file opens on its own. Rebuild it with
`../../tools/blender/export_v15_viewer.py` after changing the clips.

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
| `Crew_SickSway` | seasick, standing | 3.0 s | - | - | queasy: swaying, a fist on his stomach, head lolling |
| `Crew_SickWalk` | seasick, moving | 1.2 s | - | - | queasy walk: short lurching steps, a fist on his stomach (in place) |
| `Crew_SickClutch` | badly seasick | 1.6 s | - | - | hunched over, both fists on his stomach, a cramp each cycle |
| `Crew_SickRail` | seasick at the rail | 1.5 s | - | - | leaning over the rail, heaving twice |
| `Crew_SickCollapse` | worst seasickness | 1.8 s, one-shot | - | - | staggers, knees buckle, down on hands and knees; then `Crew_SickKneel` |
| `Crew_SickKneel` | worst seasickness | 2.0 s | - | - | on hands and knees, heaving |
| `Crew_DeckBrace` | aboard, at his post (`Station`) | 4.0 s | - | - | braced wide, riding the roll of the deck |
| `Crew_RailGrip` | aboard, at the rail through a warning (`RailHold`) | 1.8 s | - | - | gripping the rail while a sea slams him |
| `Crew_Gangway` | boarding (`Boarding`, the gangway) | 2.0 s | - | - | balancing along the plank, arms out (in place) |
| `Crew_Bail` | sent to the buckets (`Bailing`) | 1.6 s | bucket | on the bucket | scooping bilge water and tossing it over the side (rail on his right) |
| `Crew_ThrowLine` | man overboard, rescue (`HaulGoing`) | 1.4 s, one-shot | coiled line | - | throwing the line; then `Crew_HaulLine` |
| `Crew_HaulLine` | man overboard, rescue (`Hauling`) | 1.2 s | - | - | hauling the swimmer in, hand over hand |
| `Crew_GunRam` | gunner (`CannonBattery`) | 1.5 s | rammer | on the rammer | ramming the charge home, twice (gun on his left, muzzle beside him) |
| `Crew_GunFire` | gunner | 1.8 s, one-shot | linstock | - | touching off the gun and flinching from the blast (breech on his left front) |
| `Crew_Row` | jolly boat (`JollyBoatDuty`) | 1.7 s | oar | oar | seated, rowing: reach, pull, feather, return |
| `Crew_Soaked` | resting after a rescue (`restLeft`) | 1.0 s | - | - | arms wrapped round himself, shivering |

All clips are 30 fps (the scene is set to 30 fps before export, and the verifier checks every take's length in seconds), and every loop's last frame matches its first. Walk and Carry are in place
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
| `deckhand-v15-anims.fbx` | Rig + `CREW_Skin` / `CREW_Cloth` (skin exported white) + all 35 clips as separate takes |
| `clips.json` | Takes, lengths, loop flags, which tool goes in which hand |
| `<Clip>.gif`, `<Clip>-strip.png`, `overview-*.png` | Previews (overview sheets: building jobs, basics and tasks, seasickness, aboard ship) |
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
- **Saw is the level 1 lumber mill's clip** (`CLIPS['Saw']['env']='mill'`): authored at the
  mill's `Worker_Stand`, sawing the log on the bench. It needs the **lowered bench**
  (`env/lumber-mill-state-kit-lowbench.fbx`, made by `../../tools/blender/mill_l1_lowbench.py`;
  bench top 1.33 m -> 0.78 m, mallet and wedge removed, `Mallet_Tool` kept as an empty for
  `MillL1Import`; `env/bench-height.png`). He stands 10 cm behind `Worker_Stand` (baked into the
  root) so his belly clears the log. The saw's blade runs out of the fist along the forearm
  (tool frame +Z), so the game's saw mesh (blade up +Y) needs turning +90 degrees about X (blade +Y to +Z, teeth to -Y).
- **Chop is set at a tree** (`CLIPS['Chop']['env']='tree'`: Astra's `Tree_B1` at its smallest game
  size, 9 m, the trunk 1.1 m (game) in front of him as `CampWorker.Stand` places a chopper). It is
  **one-handed**, from his right side, the whole upper body winding 45 degrees right and unwinding
  into the strike; the blade bites 2 cm into the bark at his chest. With his short arms and round
  belly, every two-handed side swing put one arm through his body at contact. The axe is in his
  right hand at the end of the haft, the game's own grip; the game's two-handed second-hand
  placement (`VillagerActing`, 0.11 m up the haft) is not used by this clip. Chest height is lower
  than the tree's own `Trunk_Target` (1.3 m at game size, above his shoulders).
- Tools in the previews are **Astra's worker tools v1** (`env/tools/`, from
  `art-staging/worker-tools-v1`), placed by the game's tool frame.
- New tools the game doesn't have yet: pickaxe, mallet and chisel, quern peg, knife, arrow
  shaft, bow, basket, bucket, coiled line, rammer, linstock, oars (the clips work without them; they only show in the previews).
- Walk, Carry and SickWalk need their playback speed matched to the move speed.
- Aboard: `CrewAgent`'s states map straight onto the ship clips (Station -> DeckBrace,
  RailHold -> RailGrip, Bailing -> Bail, AtRail -> SickRail, HaulGoing/Hauling -> ThrowLine then
  HaulLine, JollyBoatDuty -> Row, the post-rescue rest -> Soaked); gunners play GunRam while
  reloading and GunFire on the shot.
- Seasickness: `CrewAgent.Sickness01` could pick SickSway / SickWalk from about 0.4, SickClutch
  from about 0.7 and SickCollapse then SickKneel near 1; SickRail when a sick hand is sent to the
  rail. The vomit itself (a splash or particles) is for the game to add; the preview puddle is
  a prop.
- **Not yet tested in Unity:** the clips on the imported rig, tool placement on the real tool
  meshes, and blending between clips.
