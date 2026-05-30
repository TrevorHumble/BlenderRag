"""FastMCP server exposing the Blender 5.1 knowledge base to Claude Code.

Registers a single ``search_blender_docs`` tool. The embedding model and the
LanceDB table are loaded once on first use and reused for every query (a stdio
MCP server is a long-lived process).

Run: ``uv run python src/blender_rag/server.py``  (needs the ``ml`` dep group)
"""

# ruff: noqa: I001 — import order is load-bearing here. torch's native runtime
# must initialize BEFORE `mcp` is imported: on Windows (Python 3.14) importing
# mcp first and torch (via sentence-transformers) second segfaults with an
# access violation. Verified by process-level bisection. Do not reorder.
import os
import sys
from functools import lru_cache
from typing import Any, Literal

import torch  # noqa: F401 — eager: force torch to load before mcp (see note)

from mcp.server.fastmcp import FastMCP

from blender_rag.config import load_config
from blender_rag.embed import Embedder
from blender_rag.index import DOCS_TABLE, hybrid_search, open_table
from blender_rag.rerank import Reranker

SourceType = Literal["manual", "api", "release_notes", "dev_docs", "code", "blendermcp"]

mcp = FastMCP(
    "blender-docs",
    instructions=(
        "Local semantic search over a curated Blender 5.1 knowledge corpus "
        "(Python/bpy API, operators, geometry/shader nodes, the manual, and "
        "release notes). Search here BEFORE writing or running Blender Python "
        "to confirm API signatures, operator/node names, and version-specific "
        "behavior, instead of relying on older 4.x knowledge. For an exact bpy "
        "symbol, pass source_type='api'; for how-to questions, source_type='manual'."
    ),
)


@lru_cache(maxsize=1)
def _resources() -> tuple[Embedder, Any, Reranker | None, bool]:
    """Load the embedder, LanceDB table, reranker, and the symbol-boost flag."""
    cfg = load_config()
    index_path = os.environ.get("INDEX_PATH") or str(cfg.path("index"))
    device = cfg.section("embedding", "device", default="auto")
    embedder = Embedder(cfg.section("embedding", "prose_model"), device=device)
    table = open_table(index_path, DOCS_TABLE)
    symbol_boost = bool(cfg.section("embedding", "symbol_boost", default=False))

    # The eval (eval/RESULTS.md) shows the cross-encoder reranker hurts MRR while
    # the free symbol boost helps, so the reranker is off by default. Re-enable
    # with embedding.use_reranker: true.
    reranker = None
    model = cfg.section("embedding", "reranker")
    if cfg.section("embedding", "use_reranker", default=False) and model:
        reranker = Reranker(model, device=device)
    return embedder, table, reranker, symbol_boost


@mcp.tool()
def search_blender_docs(
    query: str,
    top_k: int = 6,
    source_type: SourceType | None = None,
    blender_version: str | None = None,
) -> list[dict[str, Any]]:
    """Semantically search the local Blender 5.1 documentation corpus.

    Use this whenever you need to verify a Blender Python (bpy) API signature, an
    operator or node name, a node socket, or version-specific behavior, before
    writing or running Blender code. Returns the most relevant documentation
    chunks with their source URL, type, Blender version, and a relevance score.

    Args:
        query: Natural-language description of what you need (e.g. "add a
            subdivision surface modifier in Python", "what changed in the
            sequencer in 5.1").
        top_k: Number of chunks to return (default 6).
        source_type: Restrict to one corpus segment — one of manual, api,
            release_notes, dev_docs, code, blendermcp. TIP: to confirm a specific
            bpy operator/type/property signature, set ``source_type="api"`` — it
            surfaces the exact symbol even when conceptual manual pages would
            otherwise out-rank it. Use ``manual`` for how-to/UI questions.
        blender_version: Restrict to a version string like "5.1" or "5.0". Set it
            when behavior may have changed across versions.
    """
    embedder, table, reranker, symbol_boost = _resources()
    return hybrid_search(
        table,
        embedder,
        query,
        top_k=top_k,
        source_type=source_type,
        blender_version=blender_version,
        reranker=reranker,
        symbol_boost=symbol_boost,
    )


def main() -> None:
    # Preload models in the MAIN thread before the event loop starts. FastMCP
    # runs sync tools in an anyio worker thread; loading heavy native models
    # (torch/sentence-transformers) off the main thread can deadlock, so we warm
    # the cache here while we still own the main thread. The handler then only
    # runs inference on already-loaded models.
    print("blender-docs: loading models + index ...", file=sys.stderr, flush=True)
    _resources()
    print("blender-docs: ready", file=sys.stderr, flush=True)
    mcp.run()  # stdio transport by default


if __name__ == "__main__":
    main()
