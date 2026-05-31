# Ranking-gap investigation (#41)

Investigation of the API recall gap — why exact `bpy` operators/types miss top-k.
Index: 37,354 chunks (6 sources). Measured 2026-05-31.

## What was measured

For every API miss, ran default hybrid and `source_type="api"` and recorded the
rank of the expected symbol. All 14 expected symbols **exist in the corpus** (rows
≥ 1), so each miss is a genuine ranking failure, not an absent label (AC1).

## Finding 1 — the modifier-class "misses" are a `symbol_boost` artifact, not a real gap

The miss list printed by `eval.py` is for its focus config `hybrid+symbol`. Under
the **default** config (plain hybrid), the modifier-class queries mostly hit:

| query | default rank | hybrid+symbol |
|-------|-------------:|--------------:|
| create a subdivision surface modifier → `SubsurfModifier` | 3 | miss |
| add a mirror modifier → `MirrorModifier` | 3 | miss |
| add a boolean modifier → `BooleanModifier` | 2 | miss |
| add an array modifier → `ArrayModifier` | 5 | miss |

`symbol_boost` promotes leaf-name siblings and **buries** the class the default
already finds. This is independent confirmation of the standing decision to keep
`symbol_boost` off (see RESULTS.md).

## Finding 2 — the real lever is `source_type="api"` + a wider `top_k`

Quantifying the shipped skill workaround (route API-symbol queries to
`source_type="api"`), measured on the 54-query eval (AC2/AC3):

| config | overall hit@k | api hit@k |
|--------|--------------:|----------:|
| default, k=5 | 0.759 | 0.657 |
| **api-routed, k=5** | **0.833** | **0.771** |
| default, k=8 | 0.815 | 0.714 |
| **api-routed, k=8** | **0.889** | **0.829** |

Routing alone is +0.114 API hit@k at k=5; routing + k=8 reaches 0.829 / 0.889
overall. This beats every code-side knob tried (symbol_boost and the cross-encoder
reranker are both measured-negative). The targets are usually present at rank 6–8,
buried under lexically-similar siblings — a wider window recovers them. The skill
(`.claude/skills/blender-docs/SKILL.md`) now states this explicitly.

## Finding 3 — the residual hard misses are vocabulary mismatch (known limitation)

These survive even `source_type="api"` + k=8 because the symbol uses different words
than a natural query, and many lexical siblings compete:

| query | expected symbol | why it misses |
|-------|-----------------|---------------|
| scale an object using an operator | `transform.resize` | "scale" ≠ "resize" |
| save the current blend file | `wm.save_mainfile` | "save file" ≠ "save_mainfile" |
| open a blend file | `wm.open_mainfile` | buried under `asset.open_containing_blend_file` |
| render the current frame | `render.render` | matches `*.frame_current` properties |
| move or translate an object | `transform.translate` | buried under `*.duplicate_move` |
| create a new collection with bpy.data | `BlendDataCollections` | `bpy.ops.collection.*` dominate |

Root cause: dense retrieval doesn't bridge the synonym gap (scale↔resize), and BM25
rewards the many siblings that share leaf tokens. `symbol_boost` makes this worse,
not better.

## Decision (AC4)

1. **No code change ships.** The two available knobs (`symbol_boost`, reranker) are
   both measured-negative; `symbol_boost` actively breaks Finding 1. The largest
   real lever — `source_type="api"` + `top_k=8` — is *usage*, not code.
2. **Skill updated** with the measured guidance (route API lookups to
   `source_type="api"`, use `top_k=8`, and try the operator's own vocabulary when a
   natural phrasing misses).
3. **Vocabulary mismatch (Finding 3) is documented as a known limitation.** The
   candidate real fix is query expansion / operator purpose-text enrichment (e.g.
   index a synonym line per operator: "resize = scale"). That is a feature, not a
   tuning change — deferred to **#27** (eval expansion + answer-type work), with
   these six validated queries as its seed set.
