"""Generate contextual-retrieval blurbs for chunks — the one expensive step.

Reads ``data/chunks.jsonl`` + ``data/corpus.jsonl``, fills ``Chunk.context`` via a
local Ollama model (scope from ``config.yaml``), and writes ``chunks.jsonl`` back.
Resumable: chunks that already have context are skipped, so you can run it in
slices. Re-run ``build_index.py`` afterwards to embed the contextualized text.

Usage:
  uv run python scripts/build_context.py --limit 20   # sample / smoke
  uv run python scripts/build_context.py              # full run (slow!)
"""

from __future__ import annotations

import argparse

from tqdm import tqdm

from blender_rag.config import load_config
from blender_rag.contextualize import OllamaContextualizer, contextualize_chunks
from blender_rag.io import read_jsonl, write_jsonl
from blender_rag.schema import Chunk, Document


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only process first N chunks (0=all)")
    args = ap.parse_args()

    cfg = load_config()
    if not cfg.section("contextual", "enabled", default=False):
        print("contextual.enabled is false in config.yaml — enable it to run.")
        return

    docs = list(read_jsonl(cfg.path("corpus"), Document))
    chunks = list(read_jsonl(cfg.path("chunks"), Chunk))
    model = cfg.section("contextual", "ollama_model")
    scope = cfg.section("contextual", "scope")

    ctx = OllamaContextualizer(model)
    head = chunks[: args.limit] if args.limit else chunks
    tail = chunks[args.limit :] if args.limit else []

    processed = list(
        tqdm(contextualize_chunks(head, docs, ctx, scope=scope), total=len(head))
    )
    out = processed + tail
    n_ctx = sum(1 for c in out if c.context)
    write_jsonl(cfg.path("chunks"), out)
    print(f"contextualized {n_ctx}/{len(out)} chunks ({model}) -> {cfg.path('chunks')}")


if __name__ == "__main__":
    main()
