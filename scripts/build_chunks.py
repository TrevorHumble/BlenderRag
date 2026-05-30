"""Chunk the normalized corpus into embeddable Chunks.

Reads ``data/corpus.jsonl`` -> writes ``data/chunks.jsonl``.
Usage: ``uv run python scripts/build_chunks.py``
"""

from __future__ import annotations

from collections import Counter

from blender_rag.chunk import approx_tokens, chunk_corpus
from blender_rag.config import load_config
from blender_rag.io import read_jsonl, write_jsonl
from blender_rag.schema import Document


def main() -> None:
    cfg = load_config()
    docs = list(read_jsonl(cfg.path("corpus"), Document))
    chunks = list(chunk_corpus(docs, cfg))
    out = cfg.path("chunks")
    n = write_jsonl(out, chunks)

    print(f"chunked {len(docs)} docs -> {n} chunks -> {out}")
    by_type = Counter(c.source_type.value for c in chunks)
    for k, v in sorted(by_type.items()):
        print(f"  type {k}: {v}")
    if chunks:
        toks = [approx_tokens(c.text) for c in chunks]
        mean = sum(toks) // len(toks)
        print(f"  approx tokens/chunk: min {min(toks)}, mean {mean}, max {max(toks)}")


if __name__ == "__main__":
    main()
