"""Gather + prep the (inert) creative/community sources to normalized JSONL.

Runs the creative-tier acquirers and writes one ``data/creative/<source>.jsonl`` of
normalized Documents per source, with a summary. This is the **gather + prep** step
from docs/SOURCES_AND_WEIGHTING.md — it deliberately does NOT touch the LanceDB
index. Wiring (the tier/version_status retrieval rail + reindex) is gated (#49/#72).

Usage:
  uv run python scripts/gather_creative_sources.py --sources dev_blog
  uv run python scripts/gather_creative_sources.py --sources dev_blog stackexchange addons

Sources:
  dev_blog       — code.blender.org full archive (live; no extra config)
  stackexchange  — needs sources.stackexchange.posts_xml (extracted Posts.xml)
  addons         — clones the vetted third-party add-ons (network + disk)
"""

from __future__ import annotations

import argparse
import collections
from collections.abc import Iterator
from pathlib import Path

from blender_rag.config import REPO_ROOT
from blender_rag.schema import Document

OUT_DIR = REPO_ROOT / "data" / "creative"


def _gather(source: str) -> Iterator[Document]:
    if source == "dev_blog":
        from blender_rag.acquire.dev_blog import acquire_dev_blog

        yield from acquire_dev_blog()
    elif source == "stackexchange":
        from blender_rag.acquire.stackexchange import acquire_stackexchange

        yield from acquire_stackexchange()
    elif source == "addons":
        from blender_rag.acquire.addons_thirdparty import acquire_addons_thirdparty

        yield from acquire_addons_thirdparty()
    else:
        raise SystemExit(f"unknown source: {source}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Gather + prep creative sources (not wired)")
    ap.add_argument(
        "--sources", nargs="+", default=["dev_blog"],
        choices=["dev_blog", "stackexchange", "addons"],
    )
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    grand = 0
    for source in args.sources:
        path = args.out / f"{source}.jsonl"
        n = 0
        vstatus: collections.Counter = collections.Counter()
        with path.open("w", encoding="utf-8") as f:
            for doc in _gather(source):
                f.write(doc.model_dump_json() + "\n")
                n += 1
                vstatus[doc.extra.get("version_status", "?")] += 1
        grand += n
        print(f"{source:14} {n:>6} docs  {dict(vstatus)}  -> {path}")
    print(f"\ntotal: {grand} creative-tier docs prepped (NOT wired into the index).")


if __name__ == "__main__":
    main()
