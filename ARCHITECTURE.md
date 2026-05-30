# Architecture

The *why* behind BlenderRag — decisions, measured findings, and the non-obvious
bugs that shaped the code. The README has the overview; this is the design record.

## Pipeline

```
acquire/*  ->  normalize (Document)  ->  chunk (Chunk)  ->  embed  ->  LanceDB
   |              corpus.jsonl          chunks.jsonl                  index/lancedb
   |
   release_notes, manual, bpy_api, dev_docs, blendermcp
```

- **Document** = one normalized source unit (a manual page, an API symbol, a code
  file). **Chunk** = an embeddable slice with retrieval metadata. IDs are
  deterministic hashes, so re-running over unchanged sources is idempotent.
- Every stage writes JSONL, so each is independently re-runnable and inspectable.
  `scripts/build_all.py` runs the whole thing; the stages are also separate scripts.
- The dependency split matters: the pure-logic stages (acquire/normalize/chunk)
  live in the light tier and test in CI without torch. Only embed/index/server
  pull the `ml` group.

## Key decisions

| Decision | Why |
|----------|-----|
| **LanceDB** (embedded) | Single-user, file-based, no server to babysit; native dense + BM25 hybrid. |
| **BGE-M3**, normalized, 1024-dim | Strong general retriever, 8K context, MIT, runs on the local GPU. |
| **Hybrid + RRF** | BM25 catches exact operator/symbol names that dense embeddings blur; RRF fuses without tuning weights. |
| **One Document per API symbol** | Precise retrieval of an exact `bpy.types.X` / operator, vs. a coarse page. |
| **Markdown chunker for RST** | The manual is RST; converting headers to `#` lets one chunker serve docs + manual + dev docs. |
| **Plain hybrid is the default** | The eval (below) says so — see "Measured findings". |

## Measured findings (eval/RESULTS.md, 54 labeled queries)

- hit@k is **identical** (0.759) across plain hybrid, hybrid+symbol-boost, and
  hybrid+rerank. The differences are MRR-only and small.
- The **cross-encoder reranker hurts** MRR consistently (and costs a 600M model
  per query). Off by default.
- The **leaf-symbol-name boost** gives a tiny MRR edge but *lowers* API hit@k
  (promotes sibling operators); it does not fix the gap it targeted. Off by default.
- **Plain hybrid wins** on simplicity and API hit@k. Both enhancements remain as
  opt-in config flags with the evidence attached.
- Weak spot: **API hit@k 0.657** — the target symbol is often out-ranked by the
  (relevant) manual page or by sibling operators. The tool's `source_type="api"`
  filter recovers many. Open in #27.

## Non-obvious bugs handled (don't undo these)

1. **`mcp`-before-`torch` segfault** (Windows, Py 3.14). Importing `mcp` and then
   loading torch crashes with an access violation. `server.py` eager-imports torch
   *before* `mcp`, and ruff import-sorting is disabled on that file to preserve the
   order. (Bisected across processes.)
2. **FastMCP worker-thread deadlock.** FastMCP runs sync tools in an anyio worker
   thread; loading heavy native models there hangs. `server.main()` preloads the
   models in the main thread before `mcp.run()`. The handler then only does inference.
3. **99k-char code chunk.** AST chunking left a whole class unsplit (BlenderMCP's
   `addon.py`). The embedder truncated it (losing 70%) *and* the padded sequence
   made the full embed take 25+ min. `window_code()` caps code chunks; full embed
   dropped to ~2 min.
4. **Min-chunk filter dropped 10k API symbols.** Prose dedup logic dropped terse
   attribute entries. API has its own passthrough (no min-length filter).
5. **stdio MCP needs a clean stdout.** Launch the server via the venv python
   directly, not `uv run` (uv can leak startup text onto the JSON-RPC stream).

## Open

- **#4** core add-on source (needs the full `blender/blender` clone).
- **#8** contextual retrieval via Ollama — the one expensive ingestion step; the
  `Chunk.context` field + `embed_text` already support it, the generator isn't built.
- **#27** the API recall gap, plus a larger eval to settle the reranker for prose.
