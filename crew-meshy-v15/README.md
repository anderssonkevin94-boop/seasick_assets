# Meshy character v15: the paid "Red Bandana Adventure" model, coloured

Kevin's paid Meshy generation of the reference character (`../crew-islander-v9/reference.jpg`).
Meshy delivered shape only, but a clean game-ready one, so this folder colours it like the
reference. **Not rigged yet and not imported into Unity**; that's left for the Unity agent.

![hero](lit-hero.png)

## The Meshy file

| | |
|---|---|
| Source (`source/meshy-red-bandana-adventure.fbx`) | 1 mesh, **3,095 triangles**, T-pose, no texture, UVs, colours or rig; Z up, facing −Y |
| Pieces | 40 separate parts: tunic, sleeves, sash, sash knot and tails, headband, knot and tails, hair and tuft, head, ears, nose, eyes, brows, arms, hands, wrist wraps, shorts, cuffs, a shorts patch, feet, soles and sandal straps |

## Colouring

Each piece is recognised from its bounding box and gets one flat colour from the reference
(vertex colours, no image textures, like the rest of the game's crew). Cloth faces get a faint
per-face shade; skin stays flat so the game's sickness tint works.

| Colour | Pieces |
|---|---|
| Skin `#D99259` | head, ears, nose, arms, hands, feet |
| Cream linen `#D8CFBC` | tunic, sleeves; wrist wraps a lighter `#E6E0D2` |
| Red `#D0443A` | sash, sash knot and tails, headband, headband knot and tails |
| Dark brown `#3A2921` | hair, tuft, brows |
| Near black `#1C1816` | eyes |
| Teal `#2D5664` / `#2F6572` | shorts / rolled cuffs |
| Sandal | sole `#3E2A20`, wood block `#B07A4A` (bottom of the foot piece), strap `#5A3A28` |
| Patch brown `#8A5A36` | shorts patch |

Added as small plates laid on the surface (Meshy left them out): the mouth `#A23B2F`, and two
planks with a stitch on the tunic's front, as in the reference. **Total: 3,135 triangles**,
1.30 m tall (`AstraPlaytestImport` rescales to 1.7 m).

## Files

| File | What |
|---|---|
| `deckhand-v15-coloured.fbx` | Coloured, unrigged, T-pose (vertex colours, −Z forward, Y up, flat) |
| `lit-*.png` | Soft-lit review renders |
| `validation.json` | Pieces found per colour, triangle count |
| `../tools/blender/crew_meshy_v15_colour.py` | Colouring pipeline |
| `../tools/blender/render_v15_lit.py` | Review renders |
| `../tools/blender/source/crew-meshy-v15.blend` | Editable coloured source |

## Next

Rig to the game's 16-bone deckhand skeleton (the T-pose and separate pieces make the weights
much cleaner than v14's), split `CREW_Skin` / `CREW_Cloth` and export skin white, as in v14.
The hands are open and pointing rather than the reference's fists.
