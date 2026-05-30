# BlenderRag

A local **Blender 5.1** knowledge base that [Claude Code](https://claude.com/claude-code)
can semantically search mid-task. When Claude writes Blender Python (`bpy`) against a
live Blender MCP server, it can first confirm API signatures, operator/node names, and
version-specific behavior — instead of guessing from stale 4.x training data.

## Why

Blender's Python API and UI shift between versions, and most of the web is still on 4.x.
An LLM working blind produces code that no longer matches the current API. BlenderRag
indexes the authoritative, version-exact 5.1 sources and serves them over
[MCP](https://modelcontextprotocol.io) so retrieval is one tool call away.

## Architecture

```
OFFLINE (build once, re-runnable):
  acquire -> normalize -> chunk -> contextualize -> embed -> LanceDB index

RUNTIME (every Claude Code session):
  Claude Code --stdio--> "blender-docs" MCP server
                          search_blender_docs(query, top_k, source_type, blender_version)
                          -> hybrid retrieve (dense + BM25) -> cross-encoder rerank -> top hits
```

| Layer | Choice |
|-------|--------|
| Vector store | LanceDB (embedded, hybrid dense + BM25) |
| Prose embedding | BGE-M3 (1024-dim, dense + sparse) |
| Code embedding | CodeRankEmbed (768-dim, dedicated `bpy` index) |
| Reranker | bge-reranker-v2-m3 (cross-encoder) |
| Context | Anthropic-style contextual retrieval (local LLM via Ollama) |

All local, all open-licensed. Runs on the GPU (CUDA 12.8 / Blackwell) with CPU fallback.

## Sources (core, openly licensed)

Blender manual (RST), bpy API reference, release notes (5.0 + 5.1), developer docs,
core add-on source, and the BlenderMCP addon. ~300 MB of raw text — the whole index
fits in a few GB. Every chunk is tagged with `blender_version` for freshness filtering.

## Layout

```
src/blender_rag/
  schema.py        Document + Chunk data contracts
  config.py        config.yaml accessor
  io.py            JSONL helpers
  acquire/         one module per source
  chunk.py         structure-aware + AST chunking
  embed.py         BGE-M3 / CodeRankEmbed
  build_index.py   LanceDB tables + BM25
  server.py        FastMCP search_blender_docs
tests/             pytest (pure-logic, no torch)
config.yaml        pipeline configuration
```

## Develop

```bash
uv sync                       # core + dev deps (fast, no torch)
uv run pytest -q              # run tests
uv run ruff check .           # lint
uv sync --group ml            # add torch + embedding stack (GPU build)
```

## Connect to Claude Code

The repo ships a project-scoped `.mcp.json`. Open the project in Claude Code and
approve the `blender-docs` server when prompted. It exposes one tool:

```
search_blender_docs(query, top_k=6, source_type=None, blender_version=None)
  -> ranked doc chunks with source_url, source_type, title, blender_version, score
```

To make it available in **every** session (not just this project), register it at
user scope:

```powershell
claude mcp add --scope user blender-docs -- `
  uv --directory C:\Users\thumb\BlenderRag run python src/blender_rag/server.py
```

Build the index first (`uv run python scripts/build_corpus.py`, then `build_chunks.py`,
then `build_index.py`) so the server has something to search.

## Status

Under active construction. See the [issues](https://github.com/TrevorHumble/BlenderRag/issues)
for the build plan.
