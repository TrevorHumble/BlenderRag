# Blender 5.x Python gotchas and identifier changes

Behavioral and naming gotchas that the per-symbol API reference does not surface —
the non-obvious 5.x changes that silently corrupt data, render wrong, or raise
`enum not found` / `attribute` errors. Curated from real 5.1 work and runtime
probes. Each entry: the symptom, the rule, and the correct pattern. When writing
bpy for 5.1, check here for the relevant subsystem before running code.

## Layered Actions: action.fcurves is gone

In 5.x, Actions use a layered structure and `action.fcurves` may not exist —
f-curves live at `action.layers[*].strips[*].channelbags[*].fcurves`. Traverse
with a legacy fallback:

```python
def iter_fcurves(action):
    if getattr(action, "layers", None):
        for layer in action.layers:
            for strip in layer.strips:            # ActionKeyframeStrip; no .name
                for cb in getattr(strip, "channelbags", ()):  # a list, not strip.channelbag(slot)
                    yield from cb.fcurves
    elif hasattr(action, "fcurves"):              # legacy
        yield from action.fcurves
```

Slots use `slot.identifier` (e.g. `"OBTree"`), `slot.name_display`,
`slot.target_id_type` (`"OBJECT"`), `slot.handle` — there is no `slot.name` or
`slot.name_full`. Strips have no `.name`; use `type(strip).__name__`. Since 4.4 all
Actions are auto-layered, so a plain `obj.keyframe_insert(...)` still works for
writing — the traversal only matters when reading/removing f-curves.

## Shared Actions after obj.copy()

`obj.copy()` returns an object that **shares its Action datablock** with the
source — keyframing one silently changes the other, no warning. After copying,
separate the animation:

```python
new_obj = src.copy()
new_obj.data = src.data.copy()
if new_obj.animation_data:
    new_obj.animation_data_clear()           # or .action = src...action.copy()
```

## keyframe_insert value inversion on hide_viewport

With pre-existing keyframes on `hide_viewport`/`hide_render`, `keyframe_insert`
can land the new key with a flipped value (you set `True`, the f-curve stores 0).
Insert to create the point, then force the value and use CONSTANT interpolation:

```python
setattr(obj, "hide_viewport", hide)
obj.keyframe_insert(data_path="hide_viewport", frame=frame)
# then find the keyframe_point at `frame` and set kp.co.y = 1.0 if hide else 0.0
# kp.interpolation = 'CONSTANT'   # Bezier between 0 and 1 evaluates fractional mid-frames
```

## VSE new_effect uses length=, not frame_end

```python
# 5.1:
seq.strips.new_effect(name="x", type='COLOR', channel=1, frame_start=cur, length=duration)
```

Wrong-keyword error: `... invalid keyword argument(s) (frame_end), expected (name, type, channel, frame_start, length, input1, input2)`.

## VSE text strip alignment renamed to anchor_x / anchor_y

5.1 uses `anchor_x` / `anchor_y`; older builds used `align_x` / `align_y`. Use a
`hasattr` fallback. Valid value e.g. `'CENTER'`.

## modifier_apply fails on meshes with shape keys

`bpy.ops.object.modifier_apply()` raises `Modifier cannot be applied to a mesh with shape keys`.
Either remove shape keys first (`obj.shape_key_remove(...)` in a loop), or bake the
evaluated mesh:

```python
deps = bpy.context.evaluated_depsgraph_get()
new_mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
obj.data = new_mesh   # then remove the now-baked modifiers
```

## Excluded collections block edit-mode operators

If an object's collection has `exclude = True` in the view layer, entering Edit
mode via the operator fails. Link the object to the scene master collection
(`scene.collection.objects.link(obj)`) and ensure `hide_viewport = False` +
`hide_set(False)` first.

## Eevee Next world volumes silently drop from the final render

A Principled Volume on `world.node_tree` renders in the **viewport** but is
silently dropped from the **final render** (black background, no error). Use a
large mesh cube enclosing the scene with a volume-only material instead:

```python
bpy.ops.mesh.primitive_cube_add(size=120, location=(0,0,30))
mat = bpy.data.materials.new("Fog"); mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
vol = nt.nodes.new('ShaderNodeVolumePrincipled')
out = nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(vol.outputs['Volume'], out.inputs['Volume'])   # Volume only, no Surface
```

The cube must enclose the camera and be larger than `scene.eevee.volumetric_end`.

## Compositor is a node group in 5.x (no scene.node_tree)

`scene.node_tree` and `CompositorNodeComposite` no longer exist. The compositor is
a NodeGroup reached via `scene.compositing_node_group`, terminated by a
`NodeGroupOutput`:

```python
if scene.compositing_node_group is None:
    scene.compositing_node_group = bpy.data.node_groups.new("Composite", 'CompositorNodeTree')
ct = scene.compositing_node_group
ct.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
out = ct.nodes.new('NodeGroupOutput')   # not CompositorNodeComposite
```

Old-pattern errors: `'Scene' object has no attribute 'node_tree'`, `Node type CompositorNodeComposite undefined`.

## Compositor node config moved to MENU input sockets (display strings, not IDs)

Many compositor nodes expose former Python properties as MENU input sockets in
5.x, and those take the **display string**, not an UPPER_SNAKE identifier. The
Glare node:

```python
glare.inputs['Type'].default_value = 'Fog Glow'   # not 'FOG_GLOW', not glare.glare_type
glare.inputs['Quality'].default_value = 'High'
glare.inputs['Size'].default_value = 0.7           # now 0..1
```

Valid Glare Type values: `'Bloom','Ghosts','Streaks','Fog Glow','Simple Star','Sun Beams','Kernel'`; Quality: `'Low','Medium','High'`.
Old-pattern error: `key "glare_type" not found`, or `enum "FOG_GLOW" not found in ('Bloom','Ghosts',...)`. Probe any node's sockets with `for s in node.inputs: print(s.identifier, s.type, getattr(s,'default_value',None))`.

## Principled BSDF Transmission ≠ Alpha (Eevee)

`Transmission Weight` looks translucent in the viewport but renders **opaque** —
it's refraction, not transparency. For see-through, lower `inputs['Alpha']` below
1.0 (or use a Glass BSDF), and set `mat.use_screen_refraction = True`,
`mat.surface_render_method = 'BLENDED'`.

## Volume node type identifier is 'PRINCIPLED_VOLUME'

The class is `ShaderNodeVolumePrincipled` but `node.type` returns
`'PRINCIPLED_VOLUME'` (not `'VOLUME_PRINCIPLED'`). Match on `'PRINCIPLED_VOLUME'`.

## view_transform is 'AgX' (mixed case)

```python
scene.view_settings.view_transform = 'AgX'   # 'AGX' -> ValueError: enum "AGX" not found
```

Valid: `'Standard','ACES 1.3','ACES 2.0','Khronos PBR Neutral','AgX','Filmic','Filmic Log','False Color','Raw'`.

## Render engine ID is 'BLENDER_EEVEE' (not 'BLENDER_EEVEE_NEXT')

5.x consolidated Eevee — the new engine inherited the id `'BLENDER_EEVEE'`;
`'BLENDER_EEVEE_NEXT'` is invalid. There is no `scene.eevee.use_raytracing`
toggle anymore (raytracing is always on; config via `ray_tracing_method` /
`SceneEEVEE.ray_tracing_options`).

```python
scene.render.engine = 'BLENDER_EEVEE'   # 'BLENDER_EEVEE_NEXT' -> enum not found
```

## Sky Texture: NISHITA removed; new sky_type and property names

`'NISHITA'` is gone from `sky_type`. Valid: `'SINGLE_SCATTERING','MULTIPLE_SCATTERING','PREETHAM','HOSEK_WILKIE'`.
Python attrs (the manual's friendly names differ — "Air"/"Aerosols" → these):
`air_density`, `aerosol_density`, `ozone_density`, `sun_disc`, `sun_elevation`,
`sun_rotation`, `sun_intensity`, `sun_size`, `sun_direction`, `turbidity`,
`ground_albedo`, `altitude`. `dust_density` (4.x) is gone.

## Eevee Next can auto-extract a sun from a bright world

For cleaner shadows from an HDRI/sky world: `world.sun_threshold`,
`world.sun_angle`, `world.use_sun_shadow`, `world.sun_shadow_filter_radius`,
`world.sun_shadow_maximum_resolution`, `world.use_sun_shadow_jitter`,
`world.sun_shadow_jitter_overblur`.

## Emissive objects embedded in geometry render invisible

A bright emissive placed inside/behind geometry (glass, fog, a spire tip) often
won't reach the camera at any strength. Symptom: changing emission strength
(100→500→1500) produces identical renders. Place accents above/outside the
geometry; debug with a magenta cube in clearly empty space.

## Viewport ≠ render in Eevee — test-render early

Viewport "Rendered" uses different paths than the final render for volumetrics
(see world-volume gotcha), Principled transmission, screen-space refraction, and
tone mapping. Don't trust the viewport for the final look — do a small low-sample
test render to disk before iterating.
