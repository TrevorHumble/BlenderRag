# Retrieval eval results

Run with `uv run python scripts/eval.py` over `eval/queries.jsonl` (54 labeled
queries, k=5). Metrics defined in `src/blender_rag/evaluate.py`.

## Latest run — 2026-05-31, 37,354 chunks (core add-ons added)

Index: full 6 sources, now including the core add-on source (#4, `source_type=code`,
298 files → 2,984 chunks). 37,354 rows (was 34,370). Regression check for #4.

| config | hit@k | recall@k | MRR |
|--------|------:|---------:|----:|
| vector-only | 0.722 | 0.722 | 0.522 |
| **hybrid (dense + BM25)** | **0.778** | **0.778** | **0.544** |
| hybrid + symbol boost | 0.759 | 0.759 | 0.607 |
| hybrid + rerank | 0.759 | 0.759 | 0.521 |

**Headline: small, real gain.** Default hybrid hit@k rose 0.759 → **0.778** — one
query (`mesh.bevel`) flipped miss → hit. The likely mechanism is a BM25 IDF shift:
adding 2,984 code chunks changes global term statistics, and "bevel" appearing in
add-on source reweights the lexical half enough to lift the `bpy.ops.mesh.bevel`
API page into top-5. It's +1 query — modest, not a structural fix — but the
direction is right and there is no regression on any source. (No `code`-type eval
queries exist yet, so the *new* source's own retrieval is unmeasured — see #27.)

Symbol boost recovered to hit@k 0.759 with its best-ever MRR (0.607), but still
trails default hybrid on hit@k and stays opt-in. Rerank unchanged (neutral hit,
negative MRR).

**Default config (unchanged):** plain **hybrid** (dense + BM25 + RRF), no reranker,
no symbol boost. Both enhancements stay opt-in (`embedding.use_reranker`,
`embedding.symbol_boost`).

Per-source (hybrid + symbol boost, this run):

| source | hit@k | MRR | n |
|--------|------:|----:|--:|
| manual | 1.000 | 1.000 | 7 |
| dev_docs | 1.000 | 1.000 | 3 |
| release_notes | 1.000 | 0.857 | 7 |
| blendermcp | 1.000 | 0.625 | 2 |
| api | 0.629 | 0.444 | 35 |

The 13 remaining misses are unchanged and all API: 5 modifier-class lookups
(`SubsurfModifier`, `MirrorModifier`, `ArrayModifier`, `SolidifyModifier`,
`BooleanModifier`) and 8 buried operators (`object.select_all`,
`transform.translate`, `transform.resize`, `subdivision_set`, `object.parent_set`,
`render.render`, `wm.save_mainfile`, `wm.open_mainfile`). These are the #41 target.

## Prior run — 34,370 chunks (class-summary, #40)

Default hybrid hit@k 0.759 / MRR 0.542; symbol 0.741 / 0.573; rerank 0.759 / 0.521.
Class-summary added 2,070 rows with no regression. It is invisible to this harness
by design — the matcher inspects only identifier fields (title/symbol/url/section),
not chunk body, and a summary's title is the class name the per-symbol doc already
carried. Its value (body recall on multi-attribute questions, eval log #4) needs a
separate probe.

## Prior run — 32,279 chunks (pre class-summary, 5 sources)

Baseline before #40/#4. Default hybrid hit@k 0.759 / MRR 0.550; symbol 0.759 /
0.580; rerank 0.759 / 0.527. Per-source (hybrid+rerank) api 0.657, release_notes
0.857, all others 1.000.

## Findings

**1. The reranker does not earn its latency.** Across runs, hybrid+rerank has the
*same* hit@k as plain hybrid and a *lower* MRR (0.521 here; 0.527 prior). It loads a
~600M cross-encoder per query for a measurable ranking *regression*. Caveat: this
set is API-heavy (35/54) and prose sources are at ceiling, so the reranker may help
query types this set under-samples. One-line disable. Tracked in #27.

**2. Hybrid clearly beats vector-only** (hit@k 0.722 → 0.778). The BM25 half pulls
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
