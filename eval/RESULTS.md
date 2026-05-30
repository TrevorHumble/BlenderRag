# Retrieval eval results

Run with `uv run python scripts/eval.py` over `eval/queries.jsonl` (28 labeled
queries, k=5). Metrics defined in `src/blender_rag/evaluate.py`.

## Latest run — index: 3 sources, 31,218 chunks (api + manual + release_notes)

| config | hit@k | recall@k | MRR |
|--------|------:|---------:|----:|
| vector-only | 0.679 | 0.679 | 0.544 |
| hybrid (dense + BM25) | 0.714 | 0.714 | 0.551 |
| hybrid + rerank | 0.714 | 0.714 | 0.558 |

Per-source (hybrid + rerank):

| source | hit@k | MRR | n |
|--------|------:|----:|--:|
| manual | 1.000 | 0.900 | 5 |
| release_notes | 1.000 | 0.867 | 5 |
| api | 0.714 | 0.485 | 14 |
| dev_docs | 0.000 | 0.000 | 2 |
| blendermcp | 0.000 | 0.000 | 2 |

## Reading the numbers honestly

- **dev_docs + blendermcp score 0.0 because they aren't in this index yet** — it
  was built before those sources were added. They are *not* retrieval failures.
  Excluding those 4 queries, hit@k on indexed sources is **20/24 = 0.833**.
- **The reranker barely moves hit@k** on this set (0.714 -> 0.714); it only nudges
  MRR (0.551 -> 0.558). On a 24-query set that is within noise. It is *not* clearly
  earning its latency here — revisit on a larger set before trusting it.
- **Hybrid beats vector-only** (0.679 -> 0.714): the BM25 half is pulling its weight,
  mostly on exact operator/symbol names.
- **manual and release_notes are effectively solved** (perfect hit@k, high MRR).
- **api has a real recall gap** (0.714): 4 of 14 API queries miss at k=5 —
  `SubsurfModifier`, `object.select_all`, `transform.translate`, `subdivision_set`.
  The symbols exist in the corpus (pre-checked), so they're being out-ranked at
  k=5 — partly by manual pages competing for the same intent. This is the clearest
  lead for improvement (e.g. a source-aware boost, or a larger top-k for code).

## Caveats

- 28 queries is small; treat these as directional, not definitive.
- Expectations were pre-validated against `corpus.jsonl`, so a miss is a genuine
  ranking failure, not a typo — but the *labeling* (which doc is "the" right answer)
  is one person's judgment.
