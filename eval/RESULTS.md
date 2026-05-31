# Retrieval eval results

Run with `uv run python scripts/eval.py` over `eval/queries.jsonl` (62 labeled
queries, k=5). Metrics defined in `src/blender_rag/evaluate.py`.

## Latest run — 2026-05-31, 62-query set (#27 eval expansion)

Same 37,354-chunk index; the **eval set** grew 54 → 62. Added 2 `code` queries
(core add-ons), 2 multi-attribute modifier queries (exercise class-summary), 2
data-API queries (`bpy.data` operator-bias cases), and 2 more API/node queries. All
8 expects pre-validated present in the corpus.

| config | hit@k | recall@k | MRR |
|--------|------:|---------:|----:|
| vector-only | 0.758 | 0.758 | 0.526 |
| **hybrid (dense + BM25)** | **0.758** | **0.758** | **0.512** |
| hybrid + symbol boost | 0.710 | 0.710 | 0.553 |
| hybrid + rerank | 0.758 | 0.758 | 0.502 |

**#27.1 — reranker verdict reconfirmed on the bigger set.** hybrid+rerank ties plain
hybrid on hit@k (0.758) and is *lower* on MRR (0.502 vs 0.512). On the harder,
more-varied 62-query set the cross-encoder still earns nothing for its ~600M-param
per-query cost. **Decision: stays opt-in/off** (`embedding.use_reranker: false`).
symbol_boost again *lowers* hit@k (0.710). Both opt-in flags remain off by default.

Aggregate hit@k is a touch below the 54-set's 0.778 because the 8 new queries are
deliberately **routing-dependent**: this ablation passes no `source_type`, so the
data-API / node / second code query miss. With the skill's routing
(`source_type=api`/`code`, `top_k=8`) each was validated to return at rank 1–5 —
see #41. The index did not change.

**#27.3 — answer-type boundary (product call for Trevor, not auto-changed).** For
general phrasings ("create a subdivision surface modifier") the manual page rightly
out-ranks the API type; `source_type="api"` recovers the symbol. Options: (a) keep
the deliberate-routing design as-is — the data says routing is highly effective
(api hit@k 0.657→0.829 at k=8, #41) and the skill now instructs it; (b) add an
"auto" default that detects symbol-shaped queries (`bpy.`, CamelCase, dotted paths)
and blends a couple of `api` hits into an unrouted query. Recommendation: **(a)** —
mixing risks diluting prose results, and routing already wins when followed. (b) is
a future enhancement if telemetry shows callers not routing. Surfaced for decision;
default unchanged.

Per-source (hybrid + symbol boost, this run):

| source | hit@k | MRR | n |
|--------|------:|----:|--:|
| manual | 1.000 | 1.000 | 7 |
| dev_docs | 1.000 | 1.000 | 3 |
| release_notes | 1.000 | 0.857 | 7 |
| blendermcp | 1.000 | 0.625 | 2 |
| code | 0.500 | 0.100 | 2 |
| api | 0.585 | 0.411 | 41 |

`code` shows 0.500 only because this ablation doesn't route; with `source_type="code"`
both code queries return their target at rank 1.

## Prior run — 54-query set, 37,354 chunks (core add-ons landed, #4)

Index: full 6 sources incl. the core add-on source (#4, `source_type=code`,
298 files → 2,984 chunks), 37,354 rows.

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
direction is right and there is no regression on any source. (At the time this run
had no `code`-type eval queries; #27 since added two — see the latest run above.)

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
