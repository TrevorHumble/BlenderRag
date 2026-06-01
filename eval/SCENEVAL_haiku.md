# Scene-eval (Layer A) — headless Haiku RAG ablation

**Setup.** 3 tasks × 5 runs/condition = 30 sessions. Driver: Claude Haiku subagents (on-subscription). RAG-on vs RAG-off = whether `search_blender_docs` is offered. Executor: **static 5.1-API validation** (syntax + operator + `nodes.new` bl_idname existence) + lexical 5.x gotcha scan. This is a **lower bound** on real breakage — it checks *existence*, not arguments, socket names, or semantics — so `ok` means "named only real symbols," never "runs."

## Bottom line

- **WIN — known 5.x gotchas: 20 → 2** (off→on), broad-based across three independent footguns (`BLENDER_EEVEE_NEXT` 8→1, `bpy.bmesh` 6→0, removed `.inputs/.outputs.new` 6→1). This is the dimension the corpus most directly targets.
- **MISS — geometry-node bl_idnames: RAG did not help** (off 10/62 invalid, on 10/78). RAG-on invented `GeometryNodeRandomValue` 10× across 3/5 procedural-rocks runs **after querying docs** (the real node is `FunctionNodeRandomValue`) — a corpus/retrieval gap, not a win.
- **MARGINAL — hallucinated operators 1→0; script-level static failure 4/15 → 3/15.** At n=5 with single-digit event counts this is within sampling noise (no significance test passes here).
- **EXCLUDED — "grounding 0%→100%" is tautological**: the RAG-off arm cannot query by construction (0/15 off vs 15/15 on logged any query). It measures the experiment's wiring, not the RAG, so it is not a result.

## Pooled signals (recomputed from raw; n=15/condition)

| signal | RAG-off | RAG-on | note |
|---|--:|--:|---|
| 5.x gotchas (occurrences) | 20 | 2 | broad real win (3 footgun types) |
| hallucinated node bl_idnames | 10 / 62 | 10 / 78 | **no win**; denominators differ (parity caveat) |
| hallucinated operators | 1 / 133 | 0 / 133 | marginal |
| scripts failing static check | 4 / 15 | 3 / 15 | within noise at n=5 |

Per-task static failures (script ok=False): floating_island off 2/5 on 0/5; procedural_rocks off 2/5 on 3/5.

## Named hallucinations / footguns (provenance)

- **RAG-off gotchas:** `eevee_next_engine_id`×8, `bpy_bmesh_namespace`×6, `node_socket_interface_removed`×6
- **RAG-on gotchas:** `eevee_next_engine_id`×1, `node_socket_interface_removed`×1
- **RAG-off bad node bl_idnames:** `ShaderNodePrincipled`×4, `GeometryNodeRandomValue`×2, `GeometryNodeInputRandomValue`×2, `GeometryNodeDisplace`×1, `GeometryNodeScale`×1
- **RAG-on bad node bl_idnames:** `GeometryNodeRandomValue`×10
- **RAG-off bad operators:** `bpy.ops.mesh.noise`×1
- **RAG-on bad operators:** —

## Residual-failure ledger (RAG-on did NOT fix these)

- `floating_island_on_2.py` — gotchas eevee_next_engine_id
- `procedural_rocks_on_0.py` — nodes GeometryNodeRandomValue; gotchas node_socket_interface_removed
- `procedural_rocks_on_1.py` — nodes GeometryNodeRandomValue
- `procedural_rocks_on_4.py` — nodes GeometryNodeRandomValue

## Limitations (direction of bias stated)

- **Driver ≠ deployment.** Haiku hallucinates more than the frontier model that actually runs this RAG in Claude Code, so the RAG-off baseline is artificially weak and the gotcha delta is **inflated** vs real use.
- **Static check is existence-only.** Confirmed false negatives it cannot see: `bpy.bmesh.new()` (caught now as a gotcha), wrong socket names, wrong arg counts, and semantic errors all pass. `ok=True` ≠ runnable.
- **n=5/condition, single-digit events.** Per-task error deltas do not reach significance; treat the script-failure and operator lines as directional only. The gotcha win is the only broad-based, multi-type signal.
- **Sessions are model-self-authored, not captured transcripts.** `queries` are transcribed by the agent, not measured by the harness; the RAG-on arm also iterated more, so 'RAG content helped' is not fully separable from 'thought longer.'
- For a runtime-truth comparison use the live `McpBlenderExecutor` path (`scripts/run_scene_eval.py --backend live`).