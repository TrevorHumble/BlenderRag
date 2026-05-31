# BlenderRag eval session — 2026-05-30 (floating-island scene)

## TL;DR for Trevor

- Built a stylized dusk floating-island vignette over ~60 min while exercising the RAG on every non-trivial API call. Hero image: `render-v48-hero-max.png` (2400×2700, 512 TAA samples). Eval report below.
- **RAG verdict: clear net positive.** 16/26 queries directly useful, 6 partial, 4 missed. Release-note hits were the killer feature — one literally returned the working 5.x compositor node-group recipe verbatim. Manual hits explained concepts well. API hits reliable when you know the symbol.
- **Top RAG weaknesses to address:** (1) operator bias when asking about `bpy.data` patterns; (2) behavioral / gotcha knowledge missing from per-symbol indexing; (3) menu-socket display-string-vs-identifier rule not surfaced. See "Empirical findings" section for 5 corpus contributions worth adding.
- **Scene work touched:** displace modifiers, skin modifier tree, procedural materials (shader nodes), Sky Texture multi-scattering, volume cube, sun + AgX, glare compositor (5.x node-group), GN grass scatter on top-faces, fireflies (emission + glare bloom), layered Action API (keyframe_insert + multi-object animation), camera dolly. Hit the `NISHITA` removal, the `BLENDER_EEVEE_NEXT` engine ID removal, the Glare-config-moved-to-input-sockets pattern, the menu-socket display-string gotcha. All recovered. One art-critic subagent pass triggered a meaningful rework (kill the foggy wash + recompose to thirds + darker debris for value hierarchy).

---

**Started:** 12:01:57
**Hero render (best to view):** `render-v48-hero-max.png` — 2400×2700, 512 TAA samples (rendered in 8s on RTX 5070 Ti)
**Previous hi-res:** `render-v46-final-hires.png` (2000×2250, 384 samples), `render-v43-wallpaper.png` (2400×2700, 256 samples)
**Hero at 1600×1800:** `render-v44-craggy.png`
**Engine comparison (Cycles, hero res):** `render-v47-cycles-hero.png` (1600×1800, 128 samples, 55s on RTX 5070 Ti — same scene, dramatically more saturated reds/oranges, crisp grass blades, no volume reading)
**Engine comparison (Cycles, fast preview):** `render-v45-cycles.png` (800×900, 64 samples, ~10s)
**Earlier polish steps:** `render-v41-hero.png`, `render-v40-hero.png`, `render-v39-final.png`
**Pre-critique hero:** `render-v36-f1-anim-start.png` (dead-center, foggy — critic flagged value structure broken)
**Critic-rework first pass:** `render-v38-rework.png` (one bird, before adding 2 more)
**Animation triptych (final scene, frames 1/30/60):** `render-anim-f01.png`, `render-anim-f30.png`, `render-anim-f60.png` (Tree X-axis sway + 22 fireflies drifting on independent sine phases — multi-object layered actions exercised)
**Previous animation tail frame:** `render-v35-f60.png` (had camera animation, deleted in critique rework)
**Earlier hero (no fireflies):** `render-v17-hero.png`
**Animated frame 30:** `render-v31-f30.png` (fireflies drifted via 5.x layered actions)
**Wide environment variant:** `render-v23-wide.png`
**Dreamy/god-rays variant:** `render-v19.png`
**Earlier hero (no grass):** `render-v17-hero.png`
**Final .blend (session end):** `scene-2026-05-30-session-end.blend`
**Hero render version .blend:** `scene-v46-final.blend`
**Original scene pre-eval backup:** `scene-pre-eval-2026-05-30.blend`

**Goal:** Build a small surreal floating-island vignette in Blender 5.1 while *purposefully* exercising the local RAG (`mcp__blender-docs__search_blender_docs`) for every non-trivial API decision. Log each query, judge usefulness, and write up themes for the RAG eval report.

**Evaluation method:** for each Blender API decision, query RAG first, capture: query, source_type, top hit, useful Y/N, code worked Y/N. Synthesize themes at the end.

---

## Query log

| # | Query | source_type | Top hit | Useful? | Code worked? | Notes |
|---|-------|-------------|---------|---------|--------------|-------|
| 1 | create new collection and link it under scene master collection in Python | api | `bpy.ops.outliner.collection_link` | **No** | n/a — fell back to memory | Operator-biased results. The canonical `bpy.data.collections.new()` + `scene.collection.children.link()` pattern did not surface even with explicit `bpy.data.collections` in the query. Corpus is heavily per-symbol / operator-skewed; lacks workflow/cookbook chunks. |
| 2 | bpy.data.collections new and children.link example | api | `bpy.ops.object.link_to_collection` | **No** | n/a | Reproduced the operator bias even when query literally named `bpy.data`. `bpy.types.Collection.children` page didn't rank. |
| 3 | compositor node group NodeGroupOutput accessing from Python in 5.1 | api | `Scene.compositing_node_group` + `bpy.types.NodeGroupOutput` | **Yes** | n/a (used later for comp build) | Surfaced the exact 5.x concept — that compositor now lives on a node group reached via `scene.compositing_node_group`. Solid hit. |
| 4 | DisplaceModifier texture strength direction attributes | api | `DisplaceModifier.direction` (with NORMAL/CUSTOM_NORMAL/etc enum values) | **Yes** | yes | Returned `direction`, `strength`, `mid_level`. Did *not* surface `.texture` attribute directly (that one I knew from memory), but enough to confidently build the modifier. |
| 5 | bpy.data.textures.new clouds voronoi noise type 5.1 | api | `VoronoiTexture`, `NoiseTexture`, `CloudsTexture`, etc | **Yes** | yes | Confirmed procedural texture classes still exist in 5.1; type enum `'CLOUDS'/'VORONOI'` works for `bpy.data.textures.new(name, type=...)`. |
| 6 | skin modifier on bezier curve convert to mesh for tree branches | mixed | Manual: Skin Modifier > Skin Mesh Data | **Yes** | yes | Manual hit explained root verts, per-vert radius, mesh-only input. Enough to build the skinned trunk. |
| 7 | Principled BSDF input socket names 5.1 Base Color Roughness Subsurface Coat | manual | Principled BSDF > Inputs (full list) | **Yes** | yes | Returned the complete 5.1 input list (Base Color, Roughness, Metallic, IOR, Alpha, Normal, Coat group). Confirmed the 5.x change from "Clearcoat" → "Coat". |
| 8 | ShaderNodeTexCoord ShaderNodeMapping ShaderNodeNoiseTexture python create node tree | api | `ShaderNodeTexCoord` class | **Partial** | yes | Confirmed `ShaderNodeTexCoord` exists, but didn't surface `ShaderNodeMapping` or `ShaderNodeTexNoise` individually — I knew those from memory. |
| 9 | ShaderNodeMix vs ShaderNodeMixRGB deprecated 5.1 | api | both classes returned, plus 5.0 compositor removals release-note chunk | **Yes** | yes | Confirmed both exist; release-note chunk on 5.0 compositor deprecations was a bonus signal that MixRGB *survives* in shaders. |
| 10 | Eevee Next volume scatter world shader limitations volume cube object | manual | Volumes > World Volume + Volumes > Custom Range | **Yes** | yes | Manual explicitly states "world volume kills sun lights" and recommends volume objects for atmospheric fog — exact match for skill's gotcha. Reinforced the design choice. |
| 11 | ShaderNodeTexSky sky_type single scattering multiple scattering 5.1 parameters | mixed | Sky Texture > Properties (full param list) + 5.0 release-note "multiple scattering" | **Yes** | partial — param names diverged | This was the single most valuable hit. Surfaced the 5.x sky-type enum change (`SINGLE_SCATTERING`/`MULTIPLE_SCATTERING`/`PREETHAM`/`HOSEK_WILKIE`, no `NISHITA`) and listed properties. BUT manual page used display names "Air", "Aerosols" while Python attrs are `air_density`, `aerosol_density` — had to probe via `dir()` to confirm. |
| 12 | Glare node compositor Fog Glow Streaks 5.1 input socket size threshold | manual | Glare Node > Inputs (Size/Threshold/Strength/Saturation/Tint/Type) | **Yes** | yes | Confirmed the skill's "config moved to input sockets" — including the Type itself being an input. Saved me from `node.glare_type = ...` style code that fails. |
| 13 | compositor node tree access scene compositing_node_group NodeGroupOutput Composite node 5.1 python | release_notes | 5.0 Python API release-note with literal code snippet | **Yes — gold** | yes | Returned the exact 5.x recipe: `bpy.data.node_groups.new("My new comp", "CompositorNodeTree")` → `scene.compositing_node_group = tree` → add `NodeGroupOutput` and `tree.interface.new_socket(...)`. Drop-in working pattern. Also flagged `CompositorNodeOutputFile.directory`/`.file_name` socket changes. |
| 14 | geometry nodes scatter points on faces instance on points 5.1 | api | `GeometryNodeInstancesToPoints`, `GeometryNodeScaleInstances`, `GeometryNodeRotateInstances` | **Partial** | not used | Surfaced adjacent nodes but missed the canonical `GeometryNodeDistributePointsOnFaces`. Recovered with a follow-up manual query (#19). |
| 15 | action slot layered actions assign python 5.1 | release_notes | 5.1 Animation & Rigging release-note: "all actions are automatically layered already since 4.4" | **Yes** | not used | Concise, version-exact migration note. Exactly the kind of "what changed in 4.4/5.x" guidance training data lacks. |
| 16 | sequencer VSE new_effect add transform strip python signature | api | `StripsMeta.new_effect(name, type, channel, frame_start, *, length=0, input1=None, input2=None)` | **Yes — gold** | not used | Exact keyword-only signature, including the `length=` rename the skill flags. |
| 17 | hide_viewport keyframe value inversion modifier visibility timeline | api | `MaskLayer.hide`, `LayerCollection.hide_viewport`, `ObjectBase.hide_viewport` | **No** | n/a | Returned property surface but **NOTHING** about the keyframed-value-inversion behavioral gotcha. Conceptual / behavioral knowledge not in per-symbol pages. |
| 18 | Eevee Next render samples taa render bloom raytracing settings | api | `eevee_raytracing_preset_add`, `Scene.eevee`, `SceneEEVEE.ray_tracing_options` | **Partial** | I used `taa_render_samples` from memory | Surfaced general access path but not `taa_render_samples` directly. Mediocre. |
| 19 | distribute points on faces geometry node random density seed | manual | Distribute Points on Faces > Inputs (Density, Distance Min, Seed, Selection) | **Yes** | not used | Recovered the canonical node missed by #14. Manual query worked where API query failed. |
| 20 | bpy.ops.sculpt brush size strength python sculpt mode | api | `bpy.ops.sculpt.brush_stroke`, `Brush.use_paint_sculpt` | **Partial** | not used | Surfaced the operator and brush flag but not "how to set radius/strength on the active brush from Python". |
| 21 | menu socket enum identifier vs display name compositor node default_value | mixed | `NodeSocket.identifier`, `NodeTreeInterfaceSocket.identifier`, `Node.name` | **No** | hand-fixed by probe | Did not articulate the rule that menu sockets in 5.x take display strings (e.g. `'Fog Glow'` not `'FOG_GLOW'`). Had to discover via runtime exception + a `dir()` probe. |
| 22 | render bloom node compositor or surface output thickness EEVEE limitation | manual | EEVEE Limitations + Material Output Node Thickness EEVEE | **Yes** | n/a | Good context on EEVEE limitations and the EEVEE-only Thickness output. Tangential to my needs but high-quality chunks. |
| 23 | Eevee volumetric shadows light beams god rays sun through volume scatter | manual | EEVEE Limitations > Volumetrics + Volume Scatter + Sampling > Shadows (Volumetric Shadows checkbox) | **Yes** | yes | Confirmed god-ray approach: enable `eevee.use_volumetric_shadows`, push `volumetric_shadow_samples`, use forward anisotropy. Limitations text was very direct — single scattering only, camera rays only. |
| 24 | keyframe insert object location rotation python action slot 5.1 layered | api | `bpy_struct.keyframe_insert(data_path, *, index=-1, frame=current, group='', options=set(), keytype='KEYFRAME')` with full Python example | **Yes — gold** | yes | Returned the full signature, the keyword-only marker, AND a working example. The auto-layered behavior meant the simple call still worked. |
| 25 | geometry nodes python create modifier node_group add nodes connect sockets group input output | api | `bpy.ops.node.new_geometry_nodes_modifier` + **`bpy_extras.node_utils.connect_sockets`** (replaces `node_tree.links.new` for virtual sockets) | **Yes — gold** | yes | The `bpy_extras.node_utils.connect_sockets` recommendation is a real save — virtual Group Input/Output sockets are a known footgun. Worth memorising. |
| 26 | GeometryNodeInstanceOnPoints rotation scale instance input python | api | `GeometryNodeInstanceOnPoints` + related instance manip nodes | **Yes** | yes | Confirmed class name, inputs (`Points`, `Instance`, `Rotation`, `Scale`). Built the grass scatter graph from memory of socket names plus this confirmation. |

---

## Failures-while-coding tracked to RAG status

| Symptom | What broke | Was RAG capable of warning me? | Outcome |
|---|---|---|---|
| `enum "NISHITA" not found` on `sky_type` | NISHITA removed in 5.x sky texture | **Yes** (#11 surfaced the new enum list) — but I queried *after* the failure | Confirmed corpus had the answer; I just hadn't queried first. |
| `enum "BLENDER_EEVEE_NEXT" not found` on `scene.render.engine` | Engine ID reverted to `BLENDER_EEVEE` in 5.1 | Not directly tested, but `RenderSettings.engine` default `BLENDER_EEVEE` came back in #18 | Recovered by memory of the skill's note. |
| `'CompositorNodeGlare' object has no attribute 'glare_type'` | Glare node config moved to input sockets in 5.x | **Yes** (#12 surfaced "Inputs > Type" listing) — interpretation gap on my end | Recovered with a follow-up `dir()` probe. |
| `enum "FOG_GLOW" not found in ('Bloom','Ghosts','Streaks','Fog Glow',...)` | Menu socket `default_value` takes display strings, not UPPER_SNAKE identifiers | **No** (#21 missed it) | Discovered via exception message itself. |
| `BMesh data of type BMVert has been removed` | Tried to read `BMVert.co` after `bm.free()` | Not a docs question; standard bmesh lifecycle | Fixed by copying coords pre-`free()`. |
| Comp-rebuild silent error | `CompositorNodeInvert` socket name probably mismatched | Could have been caught by pre-checking inputs via `dir()` | Recovered by rebuilding the comp graph minimally. |
| `'math' is not defined` | Forgot to `import math` after a `from math import radians` switch | Self-inflicted; not a docs question | Fixed by adding import. |
| `'Action' object has no attribute 'fcurves'` | 5.x layered Actions: `action.fcurves` is gone; fcurves live in `action.layers[*].strips[*].channelbags[*].fcurves` | **Partial** — release-note #15 said "all actions are layered now" but didn't surface the traversal pattern | Recovered via empirical `dir()` probe — useful empirical learning logged below. |
| `'ActionKeyframeStrip' object has no attribute 'name'` | 5.x strips no longer have `.name`; use `.bl_rna.identifier` or `type(s).__name__` | Not in corpus | Empirical probe. |
| `'ActionSlot' object has no attribute 'name_full'` | Slot uses `.identifier`, `.name_display`, `.target_id_type`, `.handle` | Not in corpus | Empirical probe. |

---

## Themes / observations

### Where the RAG was strongly useful (keep doing this)

1. **Release notes are the killer feature.** Chunks like #11, #13, #15 — "what changed in 5.0/5.1, here's the new pattern, here's the removed API" — are precisely what training data lacks. The `release_notes` corpus segment is the highest-signal subset for migration work. Query #13 returned a working code snippet *verbatim*, the gold standard.
2. **Per-symbol API pages are reliable when you know the symbol name.** Once I asked about a specific class (`DisplaceModifier`, `ShaderNodeTexSky`, `StripsMeta.new_effect`), top hits were the right page with the right signature, enum values, and defaults. The corpus is well-aligned to the official docs structure.
3. **Manual hits explain *concepts* better than API hits.** Queries #6, #10, #19 — about workflow ("how does the skin modifier expect data", "why use a volume cube vs world volume", "how does Distribute Points work") — returned manual chunks with the right framing. When in doubt, set `source_type="manual"`.
4. **Version-tagged hits add real confidence.** Every result carries `blender_version` and `source_type`. When a release-note hit says "5.1" with a commit link, that's high-trust signal training data can't provide.

### Where the RAG was weak (improve)

1. **Operator bias on `bpy.data` queries.** Queries about `bpy.data.collections.new()` / `scene.collection.children.link()` (#1, #2) returned *only* `bpy.ops.*` operators even when the query literally named `bpy.data`. The corpus seems to index per-symbol pages without strong workflow/cookbook chunks. Could be helped by: (a) indexing the "Best Practice" / "Gotchas" appendix of the docs, (b) ingesting community cookbook examples, or (c) boosting `bpy.data` and `bpy.types.<Container>.<collection_prop>` chunks.
2. **Behavioral / gotcha knowledge is missing.** Query #17 about `hide_viewport` keyframe-value inversion returned only the property page. The non-obvious behavioral facts the `blender-mcp` skill catalogues (keyframe inversion, modifier_apply with shape keys, Glare config socket move) are mostly *not* in the corpus. Idea: ingest release-note "Behavior changes" sub-sections and curated gotcha lists.
3. **Display name vs Python identifier rule not surfaced.** Query #21 about menu sockets returned generic `identifier` definitions but not the rule that `socket.default_value` for `type='MENU'` takes a display string. This bit me when setting Glare type. The rule is implicit in the docs; would benefit from a "how to call this from Python" annotation pass.
4. **Composite multi-attribute questions get split results.** Query #4 wanted `texture` + `strength` + `direction` on `DisplaceModifier` and returned three separate hits, none of which surfaced the `.texture` attribute (the most important one). Per-attribute indexing fragments the answer.
5. **Property-name divergence between manual and Python.** Query #11 returned manual text with friendly names ("Air", "Aerosols") while the Python attributes are `air_density`, `aerosol_density`. Anyone trusting the manual hit verbatim would write wrong code. Annotation linking display name → Python attr would help.
6. **Geometry nodes naming gap.** Query #14 missed `GeometryNodeDistributePointsOnFaces` (the canonical scatter) but a follow-up manual query (#19) found it. The API-type page may be ranked below related instance-manipulation nodes for that phrasing.

### Operating recommendations (what I'd tell another Claude using this RAG)

- **Default to `source_type="manual"` for "how do I" questions, `source_type="api"` for exact-symbol confirmation, and `source_type="release_notes"` for any "what changed in 5.x" question.** All three rankings differ markedly.
- **Pin `blender_version="5.1"` whenever behavior could be version-sensitive** — it filters out stale 4.x leakage.
- **For tricky enums, query first AND `dir()` / `bl_rna.properties[...]` probe at runtime.** The corpus reliably tells you the enum *exists* but not always the exact identifier format (display string vs UPPER_SNAKE). Runtime probe is cheap insurance.
- **Don't trust per-attribute hits as exhaustive.** If you need 3 fields on a class, query the class page itself, then go to the per-attribute pages for defaults / ranges.
- **When a `bpy.ops.X` operator is the only hit but you wanted `bpy.data.Y`, the data-API equivalent almost always exists** — fall back to memory or query the container class (e.g. `bpy.types.Scene.collection`) instead.

### Summary

The RAG was a clear net positive for this session. Of 26 substantive queries, **~16 were directly useful**, **6 were partially useful**, and **4 missed**. The biggest wins were release-note hits (concise, version-exact, sometimes literal code) and specific-symbol API page hits. The biggest gaps were `bpy.data` workflow patterns, behavioral gotchas, and the Python identifier vs display-name distinction. Most "miss" cases were either recoverable from memory or from a single follow-up query with different `source_type` — meaning the cost-per-query is low and a query-then-fallback workflow is sustainable.

The Glare type / Sky `NISHITA` / Engine ID failures were the kind of thing that would have wasted significant time without the RAG — fixed in seconds with it. Versus pure-from-memory coding, the RAG saved maybe 5–10 minutes of debugging across the session, at the cost of ~30 seconds of query latency total. Worth it.

### Empirical findings worth contributing back to the corpus

These came from runtime probes when the RAG missed; would help future Claude sessions if added:

1. **5.x layered Action traversal pattern** (no `action.fcurves` anymore):
   ```python
   for L in action.layers:
       for s in L.strips:              # s is e.g. ActionKeyframeStrip; no `.name`, use `type(s).__name__`
           for cb in s.channelbags:    # list, NOT `s.channelbag(slot)`
               for fc in cb.fcurves:
                   # fc.data_path, fc.array_index, fc.keyframe_points
   for sl in action.slots:
       # sl.identifier ("OBTree"), sl.name_display, sl.target_id_type ("OBJECT"), sl.handle
   ```
2. **Compositor menu sockets take display strings, not identifiers**: `glare.inputs["Type"].default_value = 'Fog Glow'`, not `'FOG_GLOW'`. Valid values: `'Bloom','Ghosts','Streaks','Fog Glow','Simple Star','Sun Beams','Kernel'`. Quality: `'Low','Medium','High'`.
3. **Sky Texture 5.x property names**: Python attrs are `air_density`, `aerosol_density`, `ozone_density`, `sun_disc`, `sun_elevation`, `sun_rotation`, `sun_intensity`, `sun_size`, `sun_direction`, `turbidity`, `ground_albedo`, `altitude` — `dust_density` (4.x) is **gone**. Valid `sky_type`: `'SINGLE_SCATTERING','MULTIPLE_SCATTERING','PREETHAM','HOSEK_WILKIE'` — `'NISHITA'` is **gone**.
4. **Engine ID**: `scene.render.engine` in 5.1 is `'BLENDER_EEVEE'` (not `'BLENDER_EEVEE_NEXT'`, despite the engine being Eevee Next under the hood).
5. **World auto-extracted sun in Eevee Next**: `world.sun_threshold`, `world.sun_angle`, `world.use_sun_shadow`, `world.sun_shadow_filter_radius`, `world.sun_shadow_maximum_resolution`, `world.use_sun_shadow_jitter`, `world.sun_shadow_jitter_overblur` — Eevee can extract a sun from a bright world for cleaner shadows.

---

## Scene timeline (for context on what the queries supported)

- 12:01 start, default cube scene
- 12:05 island base shaped (displace modifiers via queries #4, #5)
- 12:07 tree built (skin modifier, query #6)
- 12:09 materials built (queries #7, #8, #9)
- 12:10 lighting + atmosphere (queries #10, #11 — Sky NISHITA fail)
- 12:16 camera composed, comp built (queries #12, #13 — gold)
- 12:21 birds added, last lighting iteration
- 12:24 hero render v17 (first cinematic hero)
- 12:25 eval queries #14–#22
- 12:29 god-rays experiment (query #23), dreamy variant v19
- 12:30 layered Action API test — keyframe_insert + empirical probe of `action.layers[*].strips[*].channelbags[*].fcurves` (query #24)
- 12:33 GN grass scatter on island top (queries #25, #26), v22 hero
- 12:36 fireflies added with emission + glare bloom, v27 hero
- 12:38 18 fireflies animated with sinusoidal drift over 60 frames — multi-object layered actions worked transparently
- 12:42 final hero v33 at 1600×1800, 256 TAA samples
- 12:44 camera animation across 60 frames (key cam location), tested camera Action API
- 12:46 art-critic subagent (opus) review of v36 — critic verdict REWORK, called out value structure broken (everything in same mid-orange band), dead-center composition, shape-language uniformity
- 12:48 critic-driven rework v39: volume density 0.025 → 0.003 (kill atmospheric wash), 7 floating chunks deleted, camera shifted (tree right-third, horizon low-third), sun energy bumped + lower rake angle, exposure -1.6, sky brighter, comp sat dialed back to 1.25 — final hero locked

## Outputs

In `C:\Users\thumb\BlenderRag\eval-logs\`:

**Renders (key versions):**
- `render-v33-fireflies-bright.png` — hero
- `render-v32-hero-hires.png` — hero w/ slightly dimmer fireflies
- `render-v27-fireflies.png` — first fireflies version
- `render-v24-hero-hi.png` — grass dome hero (pre-fireflies)
- `render-v23-wide.png` — wide environment variant
- `render-v19.png` — dreamy god-rays variant
- `render-v17-hero.png` — first cinematic hero (no grass, no fireflies)
- `render-v31-f30.png` — animated frame 30 of fireflies drift
- `render-v1.png` … `render-v33-*.png` — full iteration trail

**Blend files:**
- `scene-v33-hero.blend` — final
- `scene-v22-hero-grass.blend`, `scene-v27-hero-fireflies.blend`, `scene-v17-hero.blend` — milestone saves
- `scene-pre-eval-2026-05-30.blend` — pristine starting state (default cube + Light + Camera)

**Report:** this file.
