"""Retrieval smoke test against the docs table.

Usage: ``uv run python scripts/search.py "how do I add a modifier in python"``
"""

from __future__ import annotations

import sys

from blender_rag.config import load_config
from blender_rag.embed import Embedder
from blender_rag.index import DOCS_TABLE, hybrid_search, open_table
from blender_rag.rerank import Reranker


def main() -> None:
    query = " ".join(sys.argv[1:]) or "What changed in the Python API in Blender 5.1?"
    cfg = load_config()
    device = cfg.section("embedding", "device", default="auto")
    embedder = Embedder(cfg.section("embedding", "prose_model"), device=device)
    tbl = open_table(cfg.path("index"), DOCS_TABLE)
    reranker_model = cfg.section("embedding", "reranker")
    reranker = Reranker(reranker_model, device=device) if reranker_model else None
    hits = hybrid_search(tbl, embedder, query, top_k=5, reranker=reranker)

    print(f"QUERY: {query}\n")
    for i, h in enumerate(hits, 1):
        snippet = h["text"][:180].replace("\n", " ")
        score = h.get("rerank_score", h["score"])
        print(f"[{i}] score={score:.4f}  v{h['blender_version']}  {h['title']}")
        print(f"    {h['source_url']}")
        print(f"    {snippet}...\n")


if __name__ == "__main__":
    main()
