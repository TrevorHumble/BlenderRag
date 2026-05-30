# Retrieval eval results

Run with `uv run python scripts/eval.py` over `eval/queries.jsonl` (54 labeled
queries, k=5). Metrics defined in `src/blender_rag/evaluate.py`. Index: full
5 sources, 32,279 chunks.

## Results (54 queries)

| config | hit@k | recall@k | MRR |
|--------|------:|---------:|----:|
| vector-only | 0.722 | 0.722 | 0.522 |
| hybrid (dense + BM25) | **0.759** | **0.759** | **0.550** |
| hybrid + rerank | 0.759 | 0.759 | 0.527 |

Per-source (hybrid + rerank):

| source | hit@k | MRR | n |
|--------|------:|----:|--:|
| manual | 1.000 | 0.929 | 7 |
| dev_docs | 1.000 | 0.778 | 3 |
| blendermcp | 1.000 | 0.667 | 2 |
| release_notes | 0.857 | 0.690 | 7 |
| api | 0.657 | 0.385 | 35 |

## Findings

**1. The reranker does not earn its latency — now with stronger evidence.**
Across both the 28- and 54-query sets, hybrid+rerank has the *same* hit@k as plain
hybrid and a *lower* MRR (0.527 vs 0.550 here; 0.635 vs 0.640 on the 28-set). It
loads a ~600M cross-encoder and runs it on every query for a measurable
*regression* in ranking. Caveat: this set is API-heavy (35/54) and the prose
sources are already at ceiling (manual/dev_docs at 1.000), so the reranker may
still help query types this set under-samples. Recommendation: it is a one-line
config change to disable (`embedding.reranker: null`); flip it off unless a
prose-heavy eval shows it helping. Tracked in #27.

**2. Hybrid clearly beats vector-only** (hit@k 0.722 -> 0.759, MRR 0.522 -> 0.550).
The BM25 half pulls real weight on exact operator/symbol names.

**3. Non-API sources are effectively solved** (manual/dev_docs/blendermcp 1.000,
release_notes 0.857).

**4. The API recall gap is the real, sized problem: 0.657 over 35 queries.**
Two distinct causes:
- **Manual outranks the API symbol** for general phrasings ("create a subdivision
  surface modifier" -> the manual page wins; `source_type="api"` recovers it).
- **Sibling operators outrank the target** within the API itself
  (`object.select_all`, `transform.translate`, `mesh.inset`, `render.render`,
  `wm.save_mainfile`, ...). The leaf name matches the query but is buried under
  many `select_*` / `mesh.*` / `wm.*` neighbors. This is the lead for a
  symbol-name boost (#27).

## Caveats

- 54 queries, API-heavy. Directional, and the reranker verdict is conditional on
  query mix (see finding #1).
- Labeling is one person's judgment; the API/manual answer boundary is genuinely
  fuzzy (finding #4, first bullet).
