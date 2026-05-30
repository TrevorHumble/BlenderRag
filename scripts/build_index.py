"""Embed chunks and build the LanceDB docs table.

Reads ``data/chunks.jsonl`` -> writes the LanceDB index.
Usage: ``uv run python scripts/build_index.py``  (needs the ``ml`` dep group)
"""

from __future__ import annotations

from blender_rag.config import load_config
from blender_rag.embed import Embedder
from blender_rag.index import DOCS_TABLE, build_table
from blender_rag.io import read_jsonl
from blender_rag.schema import Chunk


def main() -> None:
    cfg = load_config()
    chunks = list(read_jsonl(cfg.path("chunks"), Chunk))
    model = cfg.section("embedding", "prose_model")
    device = cfg.section("embedding", "device", default="auto")
    batch_size = int(cfg.section("embedding", "batch_size", default=32))

    embedder = Embedder(model, device=device, batch_size=batch_size)
    print(f"embedding {len(chunks)} chunks | {model} | {embedder.device} | dim {embedder.dim}")

    tbl = build_table(chunks, embedder, cfg.path("index"), table_name=DOCS_TABLE)
    print(f"built '{DOCS_TABLE}' with {tbl.count_rows()} rows -> {cfg.path('index')}")


if __name__ == "__main__":
    main()
