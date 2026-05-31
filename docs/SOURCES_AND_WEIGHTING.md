# Sources, weighting, and the two-build split

**Status:** design + acquisition prep. Nothing here is wired into the live index
yet — this plans *which* sources to gather, *how much to trust each*, and *which
can legally ship*. Builds on `docs/CREATIVE_SOURCES_PLAN.md`.

## The goal

A **bigger but still useful** RAG. "Bigger" is easy and dangerous — community
content is noisy and version-mixed, and Blender's API churns hard. So every source
gets (a) a **license class** that decides which build it can go in, and (b) a
**trust weight** that decides how it ranks once it's in. Volume without weighting
makes retrieval *worse*; the weighting is the whole point.

## Two builds (a filter, not two pipelines)

Same pipeline, same index schema; the build is a `WHERE` over the `license` +
`tier` columns (see CREATIVE_SOURCES_PLAN). Three license classes:

| Class | Licenses | `commercial-clean` build | `personal-full` build |
|-------|----------|:------------------------:|:---------------------:|
| **Permissive** | CC0, CC-BY, MIT, BSD, public domain | ✅ (incl. closed/sold) | ✅ |
| **Copyleft** | CC-BY-SA, GPL | ✅ *only if the product is open-source* (attribution + share-alike/source) | ✅ |
| **Restricted** | CC-BY-**NC**-SA, no-license, ToS-bound | ❌ | ✅ (local, never redistributed) |

- **`commercial-clean`** = Permissive (+ Copyleft if we ship open-source). This is
  the sellable / open-source-releasable RAG.
- **`personal-full`** = everything, including Restricted. Trevor's local power tool;
  legally cannot be handed to others.

Because it's a column filter, we maintain **one** corpus and stamp every chunk with
`license` + `tier` + `version_status`; the two builds fall out of `build_index`
flags. No divergent forks to keep in sync.

## Trust weighting

Retrieval is rank-based RRF with no source prior (see `eval/RESULTS.md`). We add a
post-RRF multiplier (reusing the `symbol_boost` machinery). **Ships at 1.0 / off;
tuned only against eval — never blind** (the reranker/symbol_boost lesson).

```
final = rrf_score
        * w_source(source_type)     # authority of the source class
        * w_version(version_status)  # current / dated_valid / stale
        * w_recency(source_date)     # smooth decay to the 2019 floor
        * w_authority(score|stars)   # community signal WITHIN a source  [new]
        * w_media(text|transcript)   # transcript noise penalty          [new]
```

Two **new** weight dimensions beyond CREATIVE_SOURCES_PLAN, both of which Trevor
flagged ("add extra weights"):

- **`w_authority`** — a quality prior *inside* a source: SE answer score, GitHub
  stars, video view/like ratio. Normalized per source (a top-1% SE answer ≠ a
  score-3 one). Lets us admit a large source but float its best to the top.
- **`w_media`** — a small penalty for lossy media: auto-caption transcripts garble
  exactly the high-value tokens ("Geometry Nodes", "Principled BSDF"), so
  `transcript` < `prose` < `api/code` at equal relevance.

Indicative starting weights (all eval-gated):

| source | tier | license class | w_source | notes |
|--------|------|---------------|:--------:|-------|
| bpy API / manual / release notes / dev docs | technical | CC-BY-SA (manual) / docs | **1.00** | authoritative, version-exact |
| core add-ons (in-tree) | technical | GPL | 1.00 | idiomatic, version-exact |
| curated gotchas | technical | ours | 1.10 | hand-verified 5.x footguns |
| third-party add-ons (GPL/MIT) | creative | GPL / **MIT** | 0.90 | code ages slowly; manifest-gated |
| Blender Stack Exchange | creative | CC-BY-SA | 0.70 | score+recency filtered |
| devtalk.blender.org | creative | CC-BY-NC-SA | 0.75 | core-dev signal; **restricted** |
| Blender Artists | creative | CC-BY-NC-SA | 0.60 | noisy; **restricted** |
| YouTube (CC-BY only) | creative | CC-BY | 0.65 | workflow gold, transcript noise |
| *(new sources — see inventory below)* | | | | folded in from research |

`w_version`: current 1.0 · dated_valid 0.8 · stale 0.5.
`w_recency`: `0.6 + 0.4 * clamp01((year-2019)/(now-2019))`.

## Anti-staleness (the headline risk of going bigger)

1. **Tier routing** — API/signature queries are barred from the creative tier
   (a forum post never answers "what's the exact operator").
2. **version_status surfaced** in tool results so the model self-down-weights "2021
   technique".
3. **w_version × w_recency** push old content down on ties.
4. **Ingestion floor** ~Blender 2.8 / 2019 — older content admitted only if clearly
   conceptual.

## Source inventory + acquisition status

Legend: 🟢 permissive · 🟡 copyleft · 🔴 restricted.

**Already indexed (technical):** manual 🟡, bpy API, release notes, dev docs, core
add-ons 🟡, BlenderMCP 🟢(MIT), curated gotchas.

**Parser built, inert (creative):**
- 🟡 **Blender Stack Exchange** — `acquire/stackexchange.py` (now **streaming** via
  `iter_documents_from_posts_file` + `extract_posts_xml`). **Downloaded + validated
  at scale 2026-05-31:** the 192 MB dump → 293 MB Posts.xml streamed in **13 s**
  (bounded memory). Filtered to score≥5 / 2019+ = **6,010 answers**, but the
  version-mix is stark — **140 current · 3,376 dated_valid · 2,494 stale** — which is
  the empirical case *for* the trust-weight: admit the volume, float the durable.
  Still **not wired** into the index.
- 🟡/🟢 **Third-party add-ons** — `acquire/addons_thirdparty.py` (vetted GPL + MIT
  `fake-bpy-module` + MIT `pynodes`). Clone + manifest-gate; not wired.
- 🟡 **code.blender.org dev blog** — `acquire/dev_blog.py`. **Built + validated
  2026-05-31:** full WP REST archive = **248 posts, 2010→2026** (30 current / 218
  dated_valid), CC-BY-SA. Prepped to `data/creative/dev_blog.jsonl`. Not wired.
- 🟢 **`.blend` node-graph miner** — `acquire/blend_nodes.py` (`serialize_node_graph`
  pure + `node_tree_to_graph` bpy). The extractor for Demo Files / open-movie graphs.

**Gather + prep:** `scripts/gather_creative_sources.py` runs the inert acquirers →
normalized `data/creative/<source>.jsonl` (gitignored). Prepped so far: dev_blog
(248), stackexchange (6,010) — **6,258 creative-tier docs staged, none wired.**

**Planned (from CREATIVE_SOURCES_PLAN):** devtalk 🔴, Blender Artists 🔴 (Discourse
`.json`); YouTube CC-BY 🟢 (Data API, supervised). Reddit — **excluded** (ToS/legal).

**New candidates (verified 2026-05-31).** Ranked by leverage:

| # | source | class | tier | currency | value | w_source | how to acquire |
|---|--------|:-----:|------|----------|-------|:--------:|----------------|
| 1 | **Blender Demo Files** (splash + demo scenes) | 🟢 CC0/CC-BY (per-file) | technical | **5.x-current** | idiomatic *current* node graphs (shader/geo/compositor) | 0.95 | download per release → mine `.blend` → text |
| 2 | **code.blender.org** dev blog | 🟡 CC-BY-SA | technical | current (2026) | dev *rationale* behind features — complements release notes | 0.95 | scrape (HTML) |
| 3 | **Blender Studio pipeline / tools docs** | 🟡 CC-BY / GPL | technical | current | production-workflow knowledge nothing else has | 0.85 | scrape + git (studio/blender-studio-tools) |
| 4 | **blender.org Fundamentals / FAQ / tutorials** | 🟡 CC-BY-SA | technical | maintained | onboarding + FAQ Q&A pairs (good RAG shape) | 0.90 | scrape |
| 5 | **Open-movie production `.blend`s** (Peach→Gooseberry, Sprite Fright…) | 🟢 CC-BY (⚠ Agent 327 = **CC-BY-ND, exclude**) | creative | dated graphs (2.4–4.x) | idiomatic scene/rig/material structure | 0.70 | download → mine `.blend` (re-save in 5.x first) |
| 6 | **Blender Conference talks** | 🟢 CC-BY 3.0 | creative | recent yrs cover 5.x | dev + production deep-dives | 0.65 | Whisper ASR → transcript (apply `w_media`) |
| 7 | **`iplai/pynodes`** (node-as-code) | 🟢 MIT | creative | current | programmatic node-construction examples | 0.85 | git clone |
| — | awesome-blender index | 🟢 CC0 | — | — | *discovery only* (find more repos) | n/a | git clone, mine for repos |

**New acquisition capability needed:** a **`.blend` → text miner** — walk
`node_group.nodes` + `.links` (or run **NodeToPython**, GPLv3, 4.2–5.1) to serialize
shader/geometry/compositor graphs as legible Python. Unlocks #1 and #5 (the
structural-knowledge gap nothing else fills). For #1, re-save in 5.x first so
sockets are current; for #5, tag `version_status` from the file's Blender version.

**Skip / quarantine:** Wikibooks *Noob-to-Pro* (CC-BY-SA but Blender ~2.75, the page
itself warns it's outdated — actively harmful for 5.x); Poly Haven / ambientCG (CC0
*assets* but negligible *text* knowledge, and Poly Haven's API feed is NC).

Net: the two highest-leverage clean adds are **Demo Files** (current node graphs,
sell-safe) and **code.blender.org** (dev rationale, copyleft) — both pure wins for a
*bigger-but-still-useful* RAG, neither needing the noisy NC/ToS sources.

## Next steps (gather + prep, NOT wire)

1. Finish the SE dump download → run `acquire/stackexchange.py` at scale → sample +
   sanity-check the creative-tier Documents (date/score/license metadata).
2. Fold the new vetted sources into the inventory + weights table above.
3. When approved (#49): add the `tier`/`version_status`/`license`/`source_date`/
   `authority`/`media` columns to the index schema, backfill technical defaults,
   register the creative acquirers, reindex, and tune the weights against creative +
   "stale-trap" eval queries before trusting them.
