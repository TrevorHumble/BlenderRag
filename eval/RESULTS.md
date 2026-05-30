# Retrieval eval results

Run with `uv run python scripts/eval.py` over `eval/queries.jsonl` (28 labeled
queries, k=5). Metrics defined in `src/blender_rag/evaluate.py`.

## Full index — 5 sources, 32,279 chunks

| config | hit@k | recall@k | MRR |
|--------|------:|---------:|----:|
| vector-only | 0.821 | 0.821 | 0.618 |
| hybrid (dense + BM25) | 0.857 | 0.857 | **0.640** |
| hybrid + rerank | 0.857 | 0.857 | 0.635 |

Per-source (hybrid + rerank):

| source | hit@k | MRR | n |
|--------|------:|----:|--:|
| manual | 1.000 | 0.900 | 5 |
| release_notes | 1.000 | 0.867 | 5 |
| dev_docs | 1.000 | 0.667 | 2 |
| blendermcp | 1.000 | 0.667 | 2 |
| api | 0.714 | 0.449 | 14 |

## Findings

**1. The reranker is not earning its latency on this set.** Hybrid+rerank MRR is
*lower* than hybrid alone here (0.635 vs 0.640) and was barely higher on the
earlier 3-source run (0.558 vs 0.551). Both deltas are within noise on 28 queries.
Verdict: no reliable benefit yet — either the corpus/query style doesn't need it,
or the eval set is too small to detect it. Don't trust it until measured on a
larger set; consider making it optional/off by default.

**2. Hybrid clearly beats vector-only** (0.821 -> 0.857): the BM25 half earns its
place, mostly by nailing exact operator/symbol names.

**3. manual, release_notes, dev_docs, blendermcp are effectively solved** (perfect
hit@k). blendermcp only works because the code-chunk cap (#25) stopped the
embedder from truncating the addon into one giant blob.

**4. The 4 "api misses" are mostly good behavior, not failures.** For general
phrasings like "create a subdivision surface modifier", the **manual** page wins
the top-5 (score 0.99) over the API type `bpy.types.SubsurfModifier` — a fine
answer. Adding the tool's `source_type="api"` filter recovers 2 of the 4
(`SubsurfModifier` -> rank 1, `subdivision_set` -> rank 3).

**5. Two genuine ranking gaps remain** even with the API filter:
`object.select_all` and `transform.translate` are outranked by sibling operators
(many `select_*` / `transform.*` exist). These are the real, narrow weak spots —
candidates for a symbol-name boost or larger code top-k.

## Caveats

- 28 queries is small; treat as directional. The reranker verdict especially
  needs a larger set to be conclusive.
- Labeling (which doc is "the" right answer) is one person's judgment — finding #4
  shows the API/manual answer boundary is genuinely fuzzy.
