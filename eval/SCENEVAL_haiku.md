# Scene-eval report (Layer A)

Backend: **haiku-static (headless)**. 3 tasks; 15 RAG-on + 15 RAG-off sessions. Driver: Claude Haiku subagents. Executor: static 5.1-API validation (syntax + operator + node-type existence) — a lower bound on real breakage (blind to wrong args / socket names); not live Blender.

## Summary

RAG helped on **3/3** tasks (net of error_rate, gotcha_hits, task_signal_rate, grounding).

| task | Δ error_rate | Δ gotcha_hits | Δ task_signal | Δ grounding | RAG |
|------|-------------:|--------------:|--------------:|------------:|:---:|
| floating_island | -0.200 | -0.200 | -0.133 | +1.000 | ✅ |
| moody_interior | 0 | -1.200 | +0.067 | +1.000 | ✅ |
| procedural_rocks | -0.200 | 0 | 0 | +1.000 | ✅ |

## floating_island  (RAG-on n=5, RAG-off n=5)

| metric | RAG-off | RAG-on | Δ (on−off) | |
|--------|--------:|-------:|-----------:|:--:|
| error_rate | 0.200 | 0.000 | -0.200 | ✅ |
| clean_run | 0.800 | 1.000 | +0.200 | ✅ |
| query_before_call_rate | 0.000 | 1.000 | +1.000 | ✅ |
| gotcha_hits | 0.400 | 0.200 | -0.200 | ✅ |
| task_signal_rate | 1.000 | 0.867 | -0.133 | ⚠️ |
| scene_total | 0.000 | 0.000 | 0 | · |
| completed | 1.000 | 1.000 | 0 | · |
| code_executions | 1.000 | 1.000 | 0 | · |
| code_errors | 0.200 | 0.000 | -0.200 | ✅ |
| rag_queries | 0.000 | 7.800 | +7.800 | · |
| iterations | 1.000 | 8.800 | +7.800 | · |

_Pooled error_rate (sum errors / sum execs): off 0.200 → on 0.000._
_Spread (±pop. stdev): error_rate off ±0.40 / on ±0.00, gotcha_hits off ±0.49 / on ±0.40, task_signal_rate off ±0.00 / on ±0.16._

**RAG effect:** error rate -0.20, gotchas -0.20, grounding +1.00 (negative error/gotchas = better).

## moody_interior  (RAG-on n=5, RAG-off n=5)

| metric | RAG-off | RAG-on | Δ (on−off) | |
|--------|--------:|-------:|-----------:|:--:|
| error_rate | 0.000 | 0.000 | 0 | · |
| clean_run | 1.000 | 1.000 | 0 | · |
| query_before_call_rate | 0.000 | 1.000 | +1.000 | ✅ |
| gotcha_hits | 1.200 | 0.000 | -1.200 | ✅ |
| task_signal_rate | 0.667 | 0.733 | +0.067 | ✅ |
| scene_total | 0.000 | 0.000 | 0 | · |
| completed | 1.000 | 1.000 | 0 | · |
| code_executions | 1.000 | 1.000 | 0 | · |
| code_errors | 0.000 | 0.000 | 0 | · |
| rag_queries | 0.000 | 7.000 | +7.000 | · |
| iterations | 1.000 | 8.000 | +7.000 | · |

_Pooled error_rate (sum errors / sum execs): off 0.000 → on 0.000._
_Spread (±pop. stdev): error_rate off ±0.00 / on ±0.00, gotcha_hits off ±0.40 / on ±0.00, task_signal_rate off ±0.00 / on ±0.13._

**RAG effect:** gotchas -1.20, grounding +1.00 (negative error/gotchas = better).

## procedural_rocks  (RAG-on n=5, RAG-off n=5)

| metric | RAG-off | RAG-on | Δ (on−off) | |
|--------|--------:|-------:|-----------:|:--:|
| error_rate | 0.200 | 0.000 | -0.200 | ✅ |
| clean_run | 0.800 | 1.000 | +0.200 | ✅ |
| query_before_call_rate | 0.000 | 1.000 | +1.000 | ✅ |
| gotcha_hits | 0.000 | 0.000 | 0 | · |
| task_signal_rate | 0.933 | 0.933 | 0 | · |
| scene_total | 0.000 | 0.000 | 0 | · |
| completed | 1.000 | 1.000 | 0 | · |
| code_executions | 1.000 | 1.000 | 0 | · |
| code_errors | 0.200 | 0.000 | -0.200 | ✅ |
| rag_queries | 0.000 | 8.200 | +8.200 | · |
| iterations | 1.000 | 9.200 | +8.200 | · |

_Pooled error_rate (sum errors / sum execs): off 0.200 → on 0.000._
_Spread (±pop. stdev): error_rate off ±0.40 / on ±0.00, gotcha_hits off ±0.00 / on ±0.00, task_signal_rate off ±0.13 / on ±0.13._

**RAG effect:** error rate -0.20, grounding +1.00 (negative error/gotchas = better).

## Operator validity (pooled, headless static check)

| condition | scripts | total ops | invalid | invalid rate |
|---|--:|--:|--:|--:|
| RAG-off | 15 | 133 | 1 | 1% |
| RAG-on | 15 | 133 | 0 | 0% |

**RAG-off hallucinated operators:** `bpy.ops.mesh.noise`×1

## Node-type validity (nodes.new bl_idname) (pooled, headless static check)

| condition | scripts | total node calls | invalid | invalid rate |
|---|--:|--:|--:|--:|
| RAG-off | 15 | 25 | 3 | 12% |
| RAG-on | 15 | 10 | 0 | 0% |

**RAG-off hallucinated node types:** `GeometryNodeRandomValue`×2, `GeometryNodeDisplace`×1
