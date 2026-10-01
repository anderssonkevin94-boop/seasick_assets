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
| Bench, bucksaw cutting across the log | Rip trestle: the log points at the worker, and he rips it toward himself with an **iron-bladed frame saw** |
| No upkeep | A grindstone and a spare blade on the back wall (the blade wears) |
| Sign on a canvas pillar | Same sign on its own brick-footed post, with a brass **II** plate |
| Output rack of boards | The same rack: boards in the lower courses, **fine boards** (paler, planed) in the upper ones |

The level 1 canvas stays on as a lean-to over the output rack, so the building still reads as the same place.

## Kept the same, so it swaps in place

- The plot (7.56 × 5.85 m), with the ridge at 3.83 m (limit 3.84). The script checks both.
- Every `MillL1Import` marker: `Worker_Stand`, `Worker_Approach`, `Input_Pickup`, `Output_Dropoff`,
  `Entrance_Anchor`, `Bench_Anchor`.
- The input cradle with `Input_Log_01..06`, and the output rack with `Output_Plank_01..12`.
- The worker stands where he stands at level 1. The log's near end is about 0.3 m in front of his belly.
  The saw's cross handle is at belly height. The stroke is a straight push and pull with both fists in
  front of him, the easiest kind of motion to keep clear of his body.

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
| **2** | **Brick-footed saw shed (this one)** | **brick, iron blade** | **rip with a frame saw** |
| 3 | Crank saw house: a flywheel and crank drive an up-and-down sash saw in a timber frame, with half-walls of brick | gearing | turn the crank, feed the log |
| 4 | Wind saw mill: a small post-mill head with sails on a brick tower over the sash frame, and a gang of blades | wind | feed the carriage, stack boards |
| 5 | Steam saw mill: a brick engine house with a chimney, an iron roof and a circular saw on a log carriage | steam, iron | feed the carriage, tend the boiler |

The way the levels progress (canvas, then board roof, then brick walls, then the tower, then the chimney)
gives each level a silhouette you can tell apart at island zoom.

## Files

| File | What |
|---|---|
| `sawmill-l2-concept.fbx` | The concept, with the reused level 1 slots and markers under `LumberMill_C_Level_2` |
| `l1-vs-l2.png` | Level 1 (bench lowered) and level 2 from the same camera, at the same scale |
| `l2-hero.png`, `l2-front.png`, `l2-right.png`, `l2-rear.png`, `l2-top.png` | Review angles |
| `l2-hero-crew.png`, `l2-work-closeup.png` | With the v15 deckhand (idle) at `Worker_Stand`, for scale |
| `l2-work-side.png` | Side cutaway of the rip trestle, the saw and him |
| `l2-roof-off.png` | Roof hidden: the frame, the floor and the layout |

About 11.7k triangles in all, most of them proud bricks. A game kit would bake the bricks into a texture.

Not done yet: a state kit (loaded, cutting and finished variants for the rip trestle), the importer,
or a work animation. A level 2 `Saw` clip would reuse his level 1 stance.
