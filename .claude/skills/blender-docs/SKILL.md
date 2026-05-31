---
name: blender-docs
description: >-
  Search the local Blender 5.1 knowledge base (bpy Python API, operators, geometry/
  shader nodes, the manual, release notes, BlenderMCP addon source) via the
  search_blender_docs MCP tool. Use it BEFORE writing, running, or debugging Blender
  Python, or answering Blender questions — Blender's API and UI changed in 5.x and
  training data is largely 4.x, so confirm against this corpus instead of guessing.
  Triggers: bpy, blender python, blender 5.0/5.1, addon scripting, geometry nodes,
  modifiers, operators, execute_blender_code, "how do I ... in Blender".
---

# Using the Blender 5.1 knowledge base

A local retrieval system serves version-exact Blender 5.1 docs over MCP. Query it
instead of trusting your training data — most of what you learned is Blender 4.x,
and operators, properties, and node sockets have changed.

## The tool

`search_blender_docs` (from the `blender-docs` MCP server):

```
search_blender_docs(
  query: str,                 # natural language: what you need
  top_k: int = 6,
  source_type: str | None,    # api | manual | release_notes | dev_docs | code | blendermcp
  blender_version: str | None # "5.1" or "5.0"
) -> list of hits, each: { text, source_url, source_type, title, blender_version, score }
```

## When to use it

- **Before writing `bpy` code** — confirm the operator/type/property exists and its
  exact signature in 5.1 (e.g. before `bpy.ops.mesh.primitive_cube_add(...)`).
- **Before running `execute_blender_code`** against a live Blender MCP server.
- **When a script errors** with `AttributeError` / unknown operator / changed enum —
  the symbol was likely renamed or moved in 5.x.
- **For "how do I … in Blender" / UI questions** — the manual covers workflows.
- **To check what changed** between versions — the release notes are indexed per version.

Skip it for non-Blender questions, or when you've already confirmed the symbol this session.

## How to use it well

**Pick `source_type` deliberately — it's the biggest quality lever:**

| You want… | Set `source_type` |
|-----------|-------------------|
| the exact bpy operator/type/property signature | `"api"` |
| how to do something / a UI workflow | `"manual"` |
| what changed in a version | `"release_notes"` (+ `blender_version`) |
| a 5.x behavioral gotcha / renamed identifier | `"gotchas"` |
| real example code / idioms | `"code"` or `"blendermcp"` |

Why it matters: for a general phrasing like *"create a subdivision surface modifier"*,
the conceptual manual page out-ranks the API type. If you need the symbol
(`bpy.types.SubsurfModifier`), pass `source_type="api"`; if you need the how-to,
pass `source_type="manual"`.

**For API-symbol lookups, set `source_type="api"` AND `top_k=8` (measured: #41).**
This is the single biggest retrieval lever. On the eval set, routing API queries to
`source_type="api"` lifts API hit@k 0.657 → 0.771 at k=5, and to 0.829 at k=8
(overall 0.759 → 0.889). The target operator is often present but ranked 6–8, buried
under lexically-similar siblings (`object.select_all` under many `*_select_all`;
`object.parent_set` under other `parent_*`), so the wider window matters. Don't stop
at the default `top_k=6` when hunting an exact operator.

**Set `blender_version="5.1"`** when behavior may be version-specific, to avoid 5.0/4.x noise.

**Two-step pattern for scripting:** first `source_type="manual"` to learn the workflow,
then `source_type="api"` to lock the exact call. Then write the code.

## Operating recommendations (from real eval sessions)

These cost the most when ignored — an eval session hit `NISHITA`-removed and
`Glare.glare_type` errors whose answers were *in the corpus*, just queried too late:

- **Query BEFORE you write the call, not after it throws.** The corpus knows the
  5.x enum/signature; an exception you could have prevented wastes an iteration.
- **Behavioral gotchas live in `source_type="gotchas"`** — keyframe-value inversion,
  the compositor-as-node-group rewrite, NISHITA removal, etc. Per-symbol `api`
  pages won't warn you about these; the `gotchas` source will.
- **Menu/enum sockets take the display string, not `UPPER_SNAKE`** (e.g. Glare
  Type `'Fog Glow'`, not `'FOG_GLOW'`). The corpus confirms the enum *exists*;
  `dir()` / `node.inputs[...].default_value` probe at runtime confirms the exact
  literal.
- **Manual display names ≠ Python attrs** (manual says "Air"; Python is
  `air_density`). Don't copy a manual hit's friendly label as an attribute.
- **If `bpy.ops.X` is the only hit but you wanted `bpy.data.Y`**, the data-API
  equivalent almost always exists — query the container class
  (`bpy.types.Scene.collection`, `bpy.types.Collection.children`) or fall back to
  memory; don't accept the operator as the only answer.
- **Don't treat a per-attribute hit as exhaustive.** Need three fields on a class?
  Query the class itself, then drill into individual attribute pages for defaults.
- **Mind operator vocabulary mismatch (known #41 limitation).** Some operators are
  named differently from how you'd phrase the task: *scale* an object is
  `transform.resize`; *save* is `wm.save_mainfile`; *render a frame* is
  `render.render`. Natural-language queries can miss these even with
  `source_type="api"`. If a sensible query returns nothing, try the *operator's own
  vocabulary* (search `"resize"` not `"scale"`) or the `bpy.ops.<category>` group
  page to browse siblings.

### Examples

```
search_blender_docs("add a subdivision surface modifier in python", source_type="api")
  -> bpy.types.SubsurfModifier, bpy.ops.object.modifier_add(type='SUBSURF')

search_blender_docs("how do I extrude faces along normals", source_type="manual")
  -> manual page modeling/meshes/editing/.../extrude_faces_normal

search_blender_docs("what changed in the sequencer", source_type="release_notes",
                    blender_version="5.1")
  -> the 5.1 Sequencer release note (e.g. strip time properties renamed)
```

## Reading results

Each hit has a `source_url` — **cite it** when you state a fact ("per the 5.1 manual:
<url>"). Prefer hits whose `blender_version` matches the target. `score` is a fused
relevance score (higher = better); if the top hits look off, rephrase the query or
change `source_type`.

If retrieval contradicts your memory, **trust retrieval** — it's version-exact; you
are probably remembering 4.x.

## If the tool isn't available

The server is project-scoped via `.mcp.json` in the BlenderRag repo. To enable it:

1. Build the index once (needs the `ml` deps + a GPU is ideal):
   `uv run python scripts/build_all.py`
2. Open the BlenderRag project in Claude Code and approve the `blender-docs` server,
   or register it at user scope:
   `claude mcp add --scope user blender-docs -- uv --directory <repo> run python src/blender_rag/server.py`

The corpus covers the full bpy 5.1 API (~23k symbols), the manual, release notes
(5.0 + 5.1), the developer handbook, and the BlenderMCP addon source.
