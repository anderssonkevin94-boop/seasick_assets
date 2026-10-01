# Sawmill level 2 concept: the brick-footed saw shed

Concept for review, not a game kit. Built by `tools/blender/sawmill_l2_concept.py`
from the level 1 kit (`lumber-mill-state-kit.fbx`), in game metres.

![level 1 and level 2](l1-vs-l2.png)

## What level 2 is in the game

Raised at fire II (hamlet) for **6 brick + 4 fine boards**. It works **1.5× faster** and
opens **fine boards** (2 boards make 1 fine board on an iron saw blade, which wears at 0.05).
So the shed is level 1 rebuilt with what the hamlet makes: brick, sawn boards and iron.

| Level 1 (tarp camp) | Level 2 (saw shed) |
|---|---|
| Canvas on two posts | Board gable roof on four squared posts with iron straps |
| Wooden work platform | Brick plinth, the same 0.16 m height |
| Bench, bucksaw cutting across the log | **Saw wheel**: an iron circular blade standing up through a saw table, driven by a **crank wheel** that the worker turns |
| No upkeep | A grindstone and a spare blade on the back wall (the blade wears) |
| Sign on a canvas pillar | Same sign on its own brick-footed post, with a brass **II** plate |
| Output rack of boards | The same rack: boards in the lower courses, **fine boards** (paler, planed) in the upper ones |

The level 1 canvas stays on as a lean-to over the output rack, so the building still reads as the same place.

## Kept the same, so it swaps in place

- The plot (7.56 × 5.85 m), with the ridge at 3.83 m (limit 3.84). The script checks both.
- Every other `MillL1Import` marker: `Worker_Approach`, `Input_Pickup`, `Output_Dropoff`,
  `Entrance_Anchor`, `Bench_Anchor`.
- The input cradle with `Input_Log_01..06`, and the output rack with `Output_Plank_01..12`.
## The saw wheel and the crank (Kevin, 2026-10-01)

- The saw table runs left to right, along the building's flow. Logs come in from the input cradle and are
  fed into the wheel, and the sawn slabs come out toward the output rack. A rope from a push block behind
  the log runs over a sheave at the table's end to a hanging stone, so the log feeds itself while he cranks.
- The saw wheel is iron, 1.04 m across, with its axle at the table top. Its upper half stands above the log
  under a bent iron guard. Its arbor runs back under the table to a small pulley.
- The crank wheel (0.8 m across) stands in front of him on one heavy upright. A leather belt runs from its rim
  to the arbor pulley, so one turn of the crank turns the saw about six times.
- He turns a crank on the wheel's face toward him: a long grip for both fists, circling 0.65–1.05 m
  (belly to shoulder) about a centre 0.85 m up, with a 0.2 m throw.
- `Mill2_CrankWheel` and `Saw2_Wheel` are separate objects with their origins on their axles, so the game
  can spin them while he works.
- `Worker_Stand` moves to (-0.55, 0.80) (Blender coordinates) to stand behind the crank. At level 1 it was
  at (-0.04, 0.66). His belly is about 0.12 m from the handle. These positions get tuned against the
  anatomy check when the crank clip is made.

The open gable faces the front, so the game camera sees him working. From the side and the rear
the roof hides more of him than the level 1 canvas did. If that is a problem, the roof can fade
from the rear (as the level 1 README already suggests), or the eaves can go up.

## Five levels: where level 2 sits

Each level adds one power source and one material, on the same plot, with the input on the left,
the work in the middle and the output on the right. **Levels 3–5 are proposals only**: the game
defines fire levels I–II and building level 2 so far.

| Level | Concept | New material or power | Work |
|---|---|---|---|
| 1 | Tarp saw camp (approved, in game) | timber, canvas | bucksaw on the bench |
| **2** | **Brick-footed saw shed (this one)** | **brick, an iron saw wheel** | **turn the crank wheel** |
| 3 | Treadwheel saw house: a walk-in treadwheel replaces the hand crank and drives a bigger saw wheel and a log carriage, with half-walls of brick | gearing, carriage | walk the treadwheel |
| 4 | Wind saw mill: a small post-mill head with sails on a brick tower drives two saw wheels | wind | feed the carriage, stack boards |
| 5 | Steam saw mill: a brick engine house with a chimney, an iron roof and a big saw wheel on a powered log carriage | steam, iron | feed the carriage, tend the boiler |

The way the levels progress (canvas, then board roof, then brick walls, then the tower, then the chimney)
gives each level a silhouette you can tell apart at island zoom.

## Files

| File | What |
|---|---|
| `sawmill-l2-concept.fbx` | The concept, with the reused level 1 slots and markers under `LumberMill_C_Level_2` |
| `l1-vs-l2.png` | Level 1 (bench lowered) and level 2 from the same camera, at the same scale |
| `l2-hero.png`, `l2-front.png`, `l2-right.png`, `l2-rear.png`, `l2-top.png` | Review angles |
| `l2-hero-crew.png`, `l2-work-closeup.png` | With the v15 deckhand (idle) at `Worker_Stand`, for scale (the close-up has the roof hidden) |
| `l2-mechanism.png`, `l2-work-rear.png` | The saw table, saw wheel, crank wheel and him, with the shed hidden |
| `l2-roof-off.png` | Roof hidden: the frame, the floor and the layout |

About 11.7k triangles in all, most of them proud bricks. A game kit would bake the bricks into a texture.

Not done yet: a state kit (loaded, cutting and finished variants for the saw table), the importer,
or the crank work animation.
