# Modelling brief: Gawain's starship (White Falcon)

You're taking on a modelling challenge in the repo `SoulFireMage/UtilityCode`, folder `white_falcon/`. The goal is to build a clean, recognisable, **hard-surface** Blender model of a starship from one of the user's stories. The user will open and keep working on it in **Blender 5.2** on Windows, so your output must open there. 

## The ship
- Gawain is a 17-year-old who transforms into this ship, so it is a character as well as a vehicle. It should feel elegant and organic: swept, talon-like blades, not a boxy fighter.
- Size: **25 m long, about 25.5 m wide (spikes included), about 4.4 m tall**. It is very flat.
- **The nose is the blade tips.** At the front are three main blades: left, central and right. The central blade is the largest and reaches about 1 m further forward than the other two. Gaps open between the blades towards the nose.
- Swept spikes flare outwards and backwards from the sides. Two round pods/domes sit on the upper rear hull, about ±3.5 m from the centreline. A low crest runs along the rear centre.
- **Rear engines (decided by the user):** use the three circular engines in a triangle from `views/05_rear_redraw_gpt54.png`. One engine sits top-centre and two sit lower, either side, with curved cyan conduit lines and the pearl blades flaring out around them. Fit the engines inside the Meshy back silhouette, which stays the authority for the overall outline. `views/04_rear_mirrored_cutout.png` shows the same layout as a symmetric close-up.
- Materials: pearl/white hull panels, dark navy recesses between panels, and glowing **cyan** slots, vents and engine rings, which should be emissive.
- Original concept art: `views/01_cutout_white.png`. It's a perspective 3/4 view from above, so use it for mood and surface detail only, never for proportions.

## Files to use (all under `white_falcon/`)
- `blender_ref/blender_TOP_numpad7_SYMMETRIC.png`, `blender_ref/blender_BACK_ctrl_numpad1_SYMMETRIC.png` and `blender_ref/blender_RIGHT_numpad3.png` are the **authoritative orthographic references**. They are all at 40 px/m, on 30 m × 30 m canvases centred on the ship, with a 5 m grid baked in. They come from the user's own Meshy turntable (`blender_ref/meshy_screens/`). The top and back images are mirrored right halves and are exactly symmetric.
- `blender/white_falcon_blockout.blend` has these references already placed as axis-aligned image empties, plus a crude starting block. The block is the intersection of the extruded top, side and back silhouettes, cut to the +X half with a Mirror modifier. It is the right size but slabby, and its blades are far too thick.
- `blender/build_blockout.py`, `blender/trace_silhouettes.py` and `blender/silhouettes.json` are the pipeline that made it. The silhouettes are polygons in metres, so they make good guide curves.
- `mesh/` holds an earlier AI-generated mesh. Its proportions are **wrong** (the user rejected it), so don't use it as a reference.

## Conventions
- Units: metric, scale 1. **Nose points to −Y**, up is +Z, symmetric about X = 0.
- Keep a **Mirror modifier on X** so the user's edits stay symmetric. Leave the modifiers live, not applied.
- Give each major part (central blade, side blades, spikes, core/hull, pods, crest, engines) its own named object inside a `Ship` collection, so the user can tweak one part at a time.
- Keep the geometry clean and editable: quads where practical, no zero-area faces, sensible bevels or weighted normals, and nothing wildly dense. Aim for under about 150k triangles in total.

## Environment notes
**If you're running locally on the user's Windows PC:** they have an **RTX 3080 Ti**. Use the installed Blender headless (`blender -b -P script.py`, or `blender -b file.blend -P script.py`) and set Cycles to GPU:
```python
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'   # fall back to 'CUDA' if OptiX errors
prefs.get_devices(); [setattr(d, 'use', True) for d in prefs.devices]
bpy.context.scene.render.engine = 'CYCLES'   # make Cycles the active renderer (new scenes default to Eevee)
bpy.context.scene.cycles.device = 'GPU'
```
That makes iteration renders fast enough to check silhouettes after every change.

**If you're in a cloud session (no GPU),** these notes from the previous session apply:
- Blender runs headless through the `bpy` wheel. Use the **5.2.x** wheel so the .blend opens in the user's 5.2: `python3 -m venv venv && venv/bin/pip install "bpy==5.2.*"` (Python 3.13). scikit-image, scipy and shapely also install fine.
- **Cycles on CPU** renders work headless. Don't rely on a browser or WebGL renderer, because that route was blocked.
- Mesh hygiene: an earlier export broke because of degenerate faces. Before exporting or decimating, remove degenerate and duplicate faces and check vertex and face counts.

## How to check your work (do this, don't eyeball it)
Render orthographic **top, right and back** views of the ship. Use flat white on black, a 30 m ortho scale, and the camera on the matching axis, at the same framing as the references. Threshold each render to a silhouette and compare it with the traced reference silhouettes: report the overlap (IoU) for each view and aim for 0.85 or better on each. Also render a lit 3/4 beauty shot. Iterate until the silhouettes match **and** the blades read as thin and separate, not one fused slab.

## Deliverables (in `white_falcon/blender/`)
1. `white_falcon_model.blend`, saved with Blender 5.2.x, references packed, mirror modifier live.
2. `white_falcon_model.glb`, an export with modifiers applied.
3. `model_preview.jpg`: a contact sheet of the three ortho views with the reference overlaid, plus the 3/4 beauty render. Put the IoU scores in the caption or in a notes file.
4. A short `MODEL_NOTES.md`: how each part was built, which parts are guesses, and suggestions for what the user might refine.

## Git
Develop on your assigned branch, then open a PR and **merge it to main**. That's the user's standing preference for this repo. Send the user the .blend and preview images directly as file attachments, because downloading single files from GitHub has caught them out before.
