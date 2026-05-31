# Scene-eval report (Layer A)

Backend: **fake**. 3 tasks x 3 runs/condition.

> ⚠️ **Synthetic backend** — this exercises the harness plumbing, not a real measurement. Real numbers require the live backend.

## Summary

RAG helped on **3/3** tasks (net of error_rate, gotcha_hits, task_signal_rate, grounding).

| task | Δ error_rate | Δ gotcha_hits | Δ task_signal | Δ grounding | RAG |
|------|-------------:|--------------:|--------------:|------------:|:---:|
| floating_island | -0.389 | -2.000 | +0.667 | +1.000 | ✅ |
| moody_interior | -0.389 | -2.000 | +1.000 | +1.000 | ✅ |
| procedural_rocks | -0.389 | -2.000 | +1.000 | +1.000 | ✅ |

## floating_island  (RAG-on n=3, RAG-off n=3)

| metric | RAG-off | RAG-on | Δ (on−off) | |
|--------|--------:|-------:|-----------:|:--:|
| error_rate | 0.389 | 0.000 | -0.389 | ✅ |
| clean_run | 0.000 | 1.000 | +1.000 | ✅ |
| query_before_call_rate | 0.000 | 1.000 | +1.000 | ✅ |
| gotcha_hits | 2.000 | 0.000 | -2.000 | ✅ |
| task_signal_rate | 0.333 | 1.000 | +0.667 | ✅ |
| scene_total | 9.000 | 25.000 | +16.000 | ✅ |
| completed | 1.000 | 1.000 | 0 | · |
| code_executions | 3.333 | 2.000 | -1.333 | · |
| code_errors | 1.333 | 0.000 | -1.333 | ✅ |
| rag_queries | 0.000 | 2.000 | +2.000 | · |
| iterations | 3.333 | 4.000 | +0.667 | · |

**RAG effect:** error rate -0.39, gotchas -2.00, grounding +1.00 (negative error/gotchas = better).

## moody_interior  (RAG-on n=3, RAG-off n=3)

| metric | RAG-off | RAG-on | Δ (on−off) | |
|--------|--------:|-------:|-----------:|:--:|
| error_rate | 0.389 | 0.000 | -0.389 | ✅ |
| clean_run | 0.000 | 1.000 | +1.000 | ✅ |
| query_before_call_rate | 0.000 | 1.000 | +1.000 | ✅ |
| gotcha_hits | 2.000 | 0.000 | -2.000 | ✅ |
| task_signal_rate | 0.000 | 1.000 | +1.000 | ✅ |
| scene_total | 9.000 | 25.000 | +16.000 | ✅ |
| completed | 1.000 | 1.000 | 0 | · |
| code_executions | 3.333 | 2.000 | -1.333 | · |
| code_errors | 1.333 | 0.000 | -1.333 | ✅ |
| rag_queries | 0.000 | 2.000 | +2.000 | · |
| iterations | 3.333 | 4.000 | +0.667 | · |

**RAG effect:** error rate -0.39, gotchas -2.00, grounding +1.00 (negative error/gotchas = better).

## procedural_rocks  (RAG-on n=3, RAG-off n=3)

| metric | RAG-off | RAG-on | Δ (on−off) | |
|--------|--------:|-------:|-----------:|:--:|
| error_rate | 0.389 | 0.000 | -0.389 | ✅ |
| clean_run | 0.000 | 1.000 | +1.000 | ✅ |
| query_before_call_rate | 0.000 | 1.000 | +1.000 | ✅ |
| gotcha_hits | 2.000 | 0.000 | -2.000 | ✅ |
| task_signal_rate | 0.000 | 1.000 | +1.000 | ✅ |
| scene_total | 9.000 | 25.000 | +16.000 | ✅ |
| completed | 1.000 | 1.000 | 0 | · |
| code_executions | 3.333 | 2.000 | -1.333 | · |
| code_errors | 1.333 | 0.000 | -1.333 | ✅ |
| rag_queries | 0.000 | 2.000 | +2.000 | · |
| iterations | 3.333 | 4.000 | +0.667 | · |

**RAG effect:** error rate -0.39, gotchas -2.00, grounding +1.00 (negative error/gotchas = better).
