"""Measure retrieval quality over the labeled eval set.

Runs every query in ``eval/queries.jsonl`` through three configs and reports
hit@k / recall@k / MRR, plus a per-source breakdown and a miss list (for
curating the eval set vs. finding real retrieval gaps).

Usage: ``uv run python scripts/eval.py``  (needs the ``ml`` group + built index)
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from blender_rag.config import REPO_ROOT, load_config
from blender_rag.embed import Embedder
from blender_rag.evaluate import aggregate, query_metrics
from blender_rag.index import DOCS_TABLE, build_where, hybrid_search, open_table
from blender_rag.rerank import Reranker

K = 5
_HIT_FIELDS = (
    "id", "text", "source_type", "source_url",
    "title", "section", "symbol", "blender_version",
)


def load_queries(path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _version_filter(q: dict[str, Any]) -> str | None:
    return (q.get("filter") or {}).get("blender_version")


def vector_only(tbl, embedder, query, k, where):
    q = tbl.search(embedder.encode_one(query)).metric("cosine").limit(k)
    if where:
        q = q.where(where, prefilter=True)
    return [{f: row.get(f) for f in _HIT_FIELDS} for row in q.to_list()]


def evaluate_config(fn, queries):
    rows = [(q, query_metrics(fn(q), q["expect"], k=K)) for q in queries]
    overall = aggregate([m for _, m in rows])
    by_type: dict[str, list] = defaultdict(list)
    for q, m in rows:
        by_type[q.get("type", "?")].append(m)
    per_type = {t: aggregate(ms) for t, ms in by_type.items()}
    return overall, per_type, rows


def main() -> None:
    cfg = load_config()
    device = cfg.section("embedding", "device", default="auto")
    embedder = Embedder(cfg.section("embedding", "prose_model"), device=device)
    tbl = open_table(cfg.path("index"), DOCS_TABLE)
    reranker = Reranker(cfg.section("embedding", "reranker"), device=device)
    queries = load_queries(REPO_ROOT / "eval" / "queries.jsonl")

    configs = {
        "vector_only": lambda q: vector_only(
            tbl, embedder, q["query"], K, build_where(blender_version=_version_filter(q))
        ),
        "hybrid": lambda q: hybrid_search(
            tbl, embedder, q["query"], top_k=K, blender_version=_version_filter(q)
        ),
        "hybrid+symbol": lambda q: hybrid_search(
            tbl, embedder, q["query"], top_k=K,
            blender_version=_version_filter(q), symbol_boost=True,
        ),
        "hybrid+rerank": lambda q: hybrid_search(
            tbl, embedder, q["query"], top_k=K,
            blender_version=_version_filter(q), reranker=reranker,
        ),
    }

    print(f"eval: {len(queries)} queries, k={K}\n")
    print(f"{'config':16}{'hit@k':>8}{'recall@k':>10}{'mrr':>8}")
    print("-" * 42)
    results = {}
    for name, fn in configs.items():
        overall, per_type, rows = evaluate_config(fn, queries)
        results[name] = (overall, per_type, rows)
        print(f"{name:16}{overall['hit@k']:>8.3f}{overall['recall@k']:>10.3f}{overall['mrr']:>8.3f}")

    focus = "hybrid+symbol"
    overall, per_type, rows = results[focus]
    print(f"\nper-source ({focus}):")
    for t, agg in sorted(per_type.items()):
        print(f"  {t:14} hit@k {agg['hit@k']:.3f}  mrr {agg['mrr']:.3f}  (n={int(agg['n'])})")

    print(f"\nmisses ({focus}, hit@k=0) — check if expectation is wrong or retrieval failed:")
    misses = 0
    for (q, m) in rows:
        if m["hit"] == 0.0:
            misses += 1
            print(f"  [{q.get('type')}] {q['query'][:50]}  expect={q['expect']}")
    if not misses:
        print("  (none)")


if __name__ == "__main__":
    main()
