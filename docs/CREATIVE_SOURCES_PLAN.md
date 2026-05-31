# Incorporating creative / community sources (design plan)

**Status:** design, not yet built. **Date:** 2026-05-31. **Owner decision pending.**

## Goal

Add community/creative sources (Blender Stack Exchange, the official forums,
CC-licensed YouTube tutorials, third-party open-license add-ons) so the assistant
can draw on *how people actually build cool things* — workflow, aesthetic judgment,
technique — **without** ever mistaking that older, noisier content for authoritative
Blender 5.1 API truth.

The core tension: community content is high-signal for **inspiration** and
low-signal (often wrong) for **current API/behavior**. The whole design is about
keeping those two roles separate so the creative tier *informs taste* but never
*answers a signature question*.

## Decision summary (research-backed, 2025-2026)

| Source | License | Access | Verdict |
|--------|---------|--------|---------|
| **Blender Stack Exchange** | CC BY-SA 4.0 (3.0 pre-2018) | **archive.org dump** (free, no login, no LLM clickwrap) + SE API for live refresh | **Include** — best community source; rich date/score metadata |
| **Third-party GPL add-ons** | GPL (per-repo) | GitHub API; filter by `blender_manifest.toml` | **Include (private)** — idiomatic 5.x bpy; vetted list below |
| **`fake-bpy-module`** | **MIT** | GitHub | **Include** — API type stubs; MIT = commercial-safe |
| **devtalk.blender.org** | CC BY-NC-SA 3.0 | Discourse `.json` API | **Include (private only)** — high signal, version-current; NC blocks commercial build |
| **Blender Artists** | CC BY-NC-SA 3.0 | Discourse `.json` API | **Include (private), low priority** — noisy, version-mixed |
| **YouTube tutorials** | Standard (no reuse) / **CC-BY subset** | Data API `videoLicense=creativeCommon` | **Include CC-BY only, supervised** — workflow gold, transcript noise |
| **Reddit** | No third-party license | API gated; Pushshift dead | **EXCLUDE** — AI use is an explicit ToS breach; Reddit is suing AI users (Anthropic, Perplexity, Oct 2025). Not worth it. |

Reddit is the one hard "no": its terms classify *any* ML/AI use as unauthorized
without a license, there is no compliant bulk path, and third parties get no content
license at all. The signal it offers (creative inspiration) is fully covered by SE +
forums + YouTube at far lower risk.

## Architecture — logical separation, one index

We do **not** build a second database. (See the earlier decision: a metadata filter
gives the same isolation as a separate RAG, plus cheap cross-pollination, one
embedding space, one RRF.) Instead, every chunk carries metadata that lets retrieval
*route* and *weight* by trust.

### New metadata columns (extend `chunk_to_record` + `_HIT_FIELDS`)

- **`tier`**: `technical` | `creative`.
  - `technical` = api, manual, release_notes, dev_docs, code (core add-ons) — the
    current authoritative corpus.
  - `creative` = stackexchange, devtalk, blenderartists, youtube, addons_thirdparty.
- **`version_status`**: `current` | `dated_valid` | `stale`.
  - `current` — authored against 4.2+/5.x, or authoritative-tier.
  - `dated_valid` — older but the *idea/technique* still applies (conceptual answers,
    workflow). The recency rail's middle band.
  - `stale` — pre-2.8 (≈ pre-2019) API-specific content; ideas maybe, code no.
- **`source_date`** (ISO) — post/commit/video date. The raw signal for recency.
- **`authority_score`** (float, optional) — community score where available (SE vote
  count, GitHub stars). Normalized per source.
- **`license`** — `cc-by-sa-4.0`, `cc-by-nc-sa-3.0`, `gpl-3.0`, `mit`, `cc-by`, … —
  carried per chunk so the **commercial-revert filter** is a `WHERE` clause, not a
  rebuild (see "Commercial revert").

`source_type` stays as the fine-grained label; `tier` is the coarse routing switch.
The **ingestion date floor** is ~Blender 2.8 / 2019: content older than that is
admitted only if explicitly conceptual, else dropped at acquisition.

### Trust weighting — how creative content gets used appropriately

Retrieval today is rank-based RRF (no source prior). We add a **post-RRF trust
multiplier**, reusing the exact machinery built for `symbol_boost`:

```
final_score = rrf_score * w_source(tier, source_type) * w_version(version_status) * w_recency(source_date)
```

Indicative starting weights (ALL gated on eval — see below):

- `w_source`: technical authoritative **1.0**; third-party add-ons **0.85** (code is
  durable); SE **0.7**; devtalk **0.75**; YouTube CC-BY **0.65**; Blender Artists **0.6**.
- `w_version`: current **1.0**; dated_valid **0.8**; stale **0.5**.
- `w_recency`: gentle decay from `now` to the 2019 floor (e.g. `0.6 + 0.4 * clamp01((year-2019)/(now-2019))`).

This guarantees the property Trevor asked for: on a near-tie, an authoritative 5.1
page out-ranks a confident-but-old forum post — community content *informs* but does
not *out-rank truth*.

**On "weighting by creativity":** do **not** make creativity a global multiplier — it
is intent-dependent (noise when debugging an API call, signal when brainstorming a
scene). Creativity is a **mode**, not a weight:
- The `tier` filter decides *whether* creative content is in the candidate set.
- *Within* creative mode, an optional ingest-time **`technique_richness`** score (an
  LLM rates each creative chunk once) can rank by relevance × richness. This is a
  future enhancement, fires only in creative mode, and is never applied to technical
  queries.

### Query routing (the safeguard that prevents "confused for current API")

- **Default = technical tier only.** `search_blender_docs` gains a `tier` arg
  defaulting to `technical`. API/operator/signature questions never see creative content.
- **Creative is opt-in:** `tier="creative"` or `tier="all"`, used for "how would you
  approach…", "ideas for…", aesthetic/workflow questions.
- **Hard rule:** a query that names a `bpy` symbol or asks for a signature is forced
  to technical regardless — the creative tier is structurally barred from answering it.
- **Every creative hit surfaces `version_status` + `source_date`** in the tool result,
  so the model can see "2021 technique — verify the API against 5.1 docs" and self-down-weight.

The skill (`blender-docs`) gets a short section: *creative tier is for inspiration;
confirm any API it implies against the technical tier before writing code.*

## Per-source acquisition + chunking notes

- **Blender SE** (`acquire/stackexchange.py`): pull `blender.stackexchange.com.7z`
  from archive.org; parse `Posts.xml` (CreationDate, Score, Tags, OwnerUserId). One
  Document per accepted/high-score answer + its question title as context. Drop
  answers with score < threshold and pre-2019 *Python* answers (keep conceptual).
  Store author + question URL for CC BY-SA attribution. Markdown/code-fence aware
  chunking (it has both prose and code).
- **Forums** (`acquire/discourse.py`, parametrized for devtalk + BA): Discourse
  `.json` endpoints, polite throttle (429-aware). Filter to coding/python categories
  + `created_at >= 2024` for BA; devtalk can go a bit older. Thread → Document, posts
  as sections.
- **YouTube** (`acquire/youtube.py`, **supervised**): Data API `search.list`
  `videoLicense=creativeCommon` + a Blender query set → video IDs; pull manual
  captions where present, else auto-captions; clean (strip timestamps/filler, fix a
  Blender-term substitution dict for the ~10% auto-caption garble on "Geometry
  Nodes", "Principled BSDF", etc.). Tag with in-video version if stated + upload date.
- **Third-party add-ons** (`acquire/addons_thirdparty.py`): GitHub clone the vetted
  list; **require** `blender_manifest.toml` with `blender_version_min >= 4.2`, `pushed_at`
  within ~12 months, not archived. Reuse the existing AST code chunker. `source_type=code`,
  `tier=creative` (or a `code_thirdparty` sub-label).

### Vetted add-on seed list (verified current 2026-05-31)

GPL unless noted; all have a 4.2+/5.x manifest and recent pushes:

- Molecular Nodes — geometry nodes (min 5.1.0)
- Tissue — procedural mesh/modifiers (min 5.0.0)
- NodeToPython — **generates idiomatic node-creation bpy** (min 4.2)
- CAD Sketcher — modal operators, gizmos, constraints (min 4.0)
- Sverchok — node framework, parametric geometry
- JewelCraft — instancing, modifiers, materials (4.2+)
- Projectors — lights, drivers, node materials (small, readable)
- Camera Shakify — animation/drivers/f-curves (compact)
- **fake-bpy-module — MIT — API type stubs (commercial-safe)**

Skip: MACHIN3tools (not on GitHub), modifier_list / uhlik/bpy / Magic-UV (stale or
unverified against 5.x), `blender/blender-addons` (archived mid-2025 — reference only).

## Eval — you cannot tune the weights blind

The `symbol_boost`/reranker lesson applies: **every weight ships at 1.0 (off) and is
tuned only against measurements.** Sequence:

1. Ingest one clean creative source first (SE), `tier=creative`, weights = 1.0.
2. Add **creative-intent eval queries** to `eval/queries.jsonl` (new `type: creative`):
   "ideas for a stylized low-poly forest", "how do people light a moody interior",
   "approaches to procedural rock in geometry nodes". Label expected *useful* chunks.
3. Confirm the **isolation property**: existing technical queries must be unchanged
   with `tier=technical` default (no regression vs current RESULTS).
4. *Then* tune `w_source`/`w_version`/`w_recency` against the creative queries +
   a "stale-trap" set (queries where an old answer is tempting but wrong) to verify
   the trust weight actually suppresses stale API content.

## Commercial-revert story (unchanged, now concrete)

A sellable build is a **filter**, not a rebuild:
`WHERE tier='technical' AND license IN ('cc-by','mit', <permissive>)`.
- Drop CC-BY-NC-SA forum content (NonCommercial) and GPL add-on source
  (redistribution obligations); keep `fake-bpy-module` (MIT) and the CC-BY-SA /
  CC-BY content with attribution preserved (per-chunk `license` + `source_url` +
  author make attribution mechanical).
- The pipeline ships; the corpus does not. Noisy/NC/GPL data never enters a
  redistributable artifact.

## Phasing (by legal cleanliness, lowest risk first)

- **Phase 1 — buildable now, low risk:** third-party add-ons (private) +
  `fake-bpy-module` (MIT) + Blender SE (CC BY-SA via archive.org). Add `tier` +
  `version_status` + provenance columns; ship trust-weight *off*; add creative eval
  queries; confirm isolation.
- **Phase 2 — supervised:** YouTube CC-BY subset (Data API key + caption cleanup).
- **Phase 3 — private-only:** devtalk + Blender Artists (CC-NC-SA); excluded from any
  commercial build by the license filter.
- **Excluded:** Reddit.

## Risks

- **Licensing:** NC (forums) and GPL (add-ons) are fine privately, blocked for resale —
  handled by the `license` column + commercial filter. CC BY-SA/BY need attribution —
  handled by per-chunk `source_url`/author.
- **Staleness leakage** is the headline risk; mitigated by tier routing + version_status
  surfacing + recency/trust weighting + the hard "no creative answers for API queries" rule.
- **Corpus bloat / embed time:** SE alone is ~100k posts; cap by score/recency filters
  at acquisition, not after embedding.
- **ToS:** archive.org SE dump and Discourse `.json` are clean; YouTube transcript even
  of CC-BY video is a ToS grey area → keep it supervised and CC-BY-only; Reddit excluded.
