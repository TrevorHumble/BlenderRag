# Retrieval eval results

Run with `uv run python scripts/eval.py` over `eval/queries.jsonl` (54 labeled
queries, k=5). Metrics defined in `src/blender_rag/evaluate.py`.

## Latest run — 2026-05-31, 34,370 chunks

Index: full 5 sources + the new per-class **class-summary** chunks (#40), 34,370
rows (was 32,279). This run is the regression check for class-summary.

| config | hit@k | recall@k | MRR |
|--------|------:|---------:|----:|
| vector-only | 0.722 | 0.722 | 0.522 |
| **hybrid (dense + BM25)** | **0.759** | **0.759** | **0.542** |
| hybrid + symbol boost | 0.741 | 0.741 | 0.573 |
| hybrid + rerank | 0.759 | 0.759 | 0.521 |

**Headline: no regression.** Plain hybrid holds at hit@k 0.759 after adding 2,070
class-summary rows; MRR drifts 0.550 → 0.542 (≈ one query moving rank 1 → 2,
inside noise for n=54). The class-summary chunks are *not visible* to this eval by
design: the matcher (`evaluate.py`) inspects only identifier fields
(title/symbol/url/section), and a summary's title is the class name, which the
per-symbol class doc already carried. Their value is body recall on multi-attribute
questions (eval log #4), which the harness does not substring-match — so "no
regression" is the most this set can say. Confirming the body-recall win needs a
multi-attribute query probe, not this matcher.

This run also **sharpens the symbol-boost verdict**: it now *lowers* hit@k to 0.741
(it tied 0.759 on the prior index) while buying a small MRR edge (0.573). It trades
a real hit for a ranking nicety — still not worth enabling. Rerank remains
neutral-on-hit, negative-on-MRR (0.521).

**Default config (unchanged):** plain **hybrid** (dense + BM25 + RRF), no reranker,
no symbol boost. Both enhancements stay opt-in (`embedding.use_reranker`,
`embedding.symbol_boost`) with this evidence attached.

Per-source (hybrid + symbol boost, this run):

| source | hit@k | MRR | n |
|--------|------:|----:|--:|
| manual | 1.000 | 0.929 | 7 |
| dev_docs | 1.000 | 1.000 | 3 |
| release_notes | 1.000 | 0.857 | 7 |
| blendermcp | 1.000 | 0.625 | 2 |
| api | 0.600 | 0.406 | 35 |

### The 14 API misses are the #41 lead

Every miss this run is an API query, in exactly the two buckets #41 names:

- **Modifier-class lookups** — "add a {mirror,array,solidify,boolean} modifier",
  "create a subdivision surface modifier" → expect `*Modifier` (e.g.
  `SubsurfModifier`). The new class-summary chunk is positioned to help here, but
  hit@k did not move — so the modifier class still isn't surfacing top-5. First
  thing to dig into for #41: does the `SubsurfModifier` summary exist, and what
  out-ranks it?
- **Operator leaf-name burial** — `object.select_all`, `transform.translate`,
  `transform.resize`, `mesh.bevel`, `object.parent_set`, `render.render`,
  `wm.save_mainfile`, `wm.open_mainfile`, `subdivision_set`. The leaf name matches
  but sits under many `select_*` / `mesh.*` / `wm.*` siblings.

## Prior run — 32,279 chunks (pre class-summary)

| config | hit@k | recall@k | MRR |
|--------|------:|---------:|----:|
| vector-only | 0.722 | 0.722 | 0.522 |
| hybrid (dense + BM25) | 0.759 | 0.759 | 0.550 |
| hybrid + symbol boost | 0.759 | 0.759 | 0.580 |
| hybrid + rerank | 0.759 | 0.759 | 0.527 |

Per-source (hybrid + rerank, prior index):

| source | hit@k | MRR | n |
|--------|------:|----:|--:|
| manual | 1.000 | 0.929 | 7 |
| dev_docs | 1.000 | 0.778 | 3 |
| blendermcp | 1.000 | 0.667 | 2 |
| release_notes | 0.857 | 0.690 | 7 |
| api | 0.657 | 0.385 | 35 |

## Findings

**1. The reranker does not earn its latency.** Across runs, hybrid+rerank has the
*same* hit@k as plain hybrid and a *lower* MRR (0.521 here; 0.527 prior). It loads a
~600M cross-encoder per query for a measurable ranking *regression*. Caveat: this
set is API-heavy (35/54) and prose sources are at ceiling, so the reranker may help
query types this set under-samples. One-line disable. Tracked in #27.

**2. Hybrid clearly beats vector-only** (hit@k 0.722 → 0.759). The BM25 half pulls
real weight on exact operator/symbol names.

**3. Non-API sources are effectively solved** (manual/dev_docs/release_notes 1.000,
blendermcp 1.000).

**4. The API recall gap is the real, sized problem (0.600–0.657 over 35 queries).**
Two causes: the manual outranks the API symbol for general phrasings
(`source_type="api"` recovers it), and sibling operators outrank the target within
the API. This is the live lead for #41.

## Caveats

- 54 queries, API-heavy. Directional, and the reranker verdict is conditional on
  query mix (finding #1).
- Labeling is one person's judgment; the API/manual answer boundary is genuinely
  fuzzy (finding #4).
- The harness cannot see chunk *body* content — only identifier fields — so
  body-recall improvements (class-summary, contextual retrieval) are invisible to
  it and need a different probe.
