"""Acquire all registered sources and write the normalized corpus to JSONL.

Usage: ``uv run python scripts/build_corpus.py``
"""

from __future__ import annotations

from collections import Counter

from blender_rag.acquire import acquire_all
from blender_rag.config import load_config
from blender_rag.io import write_jsonl


def main() -> None:
    cfg = load_config()
    out = cfg.path("corpus")
    docs = list(acquire_all(cfg))
    n = write_jsonl(out, docs)

    print(f"wrote {n} documents -> {out}")
    by_type = Counter(d.source_type.value for d in docs)
    by_version = Counter(d.blender_version for d in docs)
    for k, v in sorted(by_type.items()):
        print(f"  type {k}: {v}")
    for k, v in sorted(by_version.items()):
        print(f"  version {k}: {v}")
    total_chars = sum(len(d.text) for d in docs)
    print(f"  total text: {total_chars / 1_000:.0f}K chars")


if __name__ == "__main__":
    main()
