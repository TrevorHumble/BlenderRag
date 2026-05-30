"""Retrieval evaluation metrics (pure — no torch, unit-testable).

A query is labeled with ``expect`` strings: each is a substring that should
appear in a relevant hit's identifying fields (title / source_url / symbol /
section). A hit "matches" an expectation if the substring is present
(case-insensitive). From that we compute, per query and aggregated:

* **hit@k**   — did any expected match land in the top-k? (coverage)
* **recall@k** — fraction of the query's expected matches found in the top-k
* **MRR**     — reciprocal rank of the first matching hit (ranking quality)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

_MATCH_FIELDS = ("title", "source_url", "symbol", "section")


def hit_matches(hit: dict[str, Any], expect: str) -> bool:
    """True if ``expect`` (case-insensitive) appears in the hit's id fields."""
    haystack = " ".join(str(hit.get(f, "")) for f in _MATCH_FIELDS).lower()
    return expect.lower() in haystack


def first_match_rank(hits: Sequence[dict[str, Any]], expects: Sequence[str]) -> int | None:
    """1-based rank of the first hit matching any expectation, or None."""
    for rank, hit in enumerate(hits, start=1):
        if any(hit_matches(hit, e) for e in expects):
            return rank
    return None


def query_metrics(
    hits: Sequence[dict[str, Any]], expects: Sequence[str], *, k: int
) -> dict[str, float]:
    """Per-query hit@k, recall@k, and reciprocal rank (over the full list)."""
    if not expects:
        return {"hit": 0.0, "recall": 0.0, "rr": 0.0}
    top_k = hits[:k]
    found = sum(1 for e in expects if any(hit_matches(h, e) for h in top_k))
    rank = first_match_rank(hits, expects)
    return {
        "hit": 1.0 if (rank is not None and rank <= k) else 0.0,
        "recall": found / len(expects),
        "rr": 1.0 / rank if rank is not None else 0.0,
    }


def aggregate(per_query: Sequence[dict[str, float]]) -> dict[str, float]:
    """Mean hit@k, recall@k, and MRR over a set of per-query metrics."""
    n = len(per_query)
    if n == 0:
        return {"hit@k": 0.0, "recall@k": 0.0, "mrr": 0.0, "n": 0}
    return {
        "hit@k": sum(q["hit"] for q in per_query) / n,
        "recall@k": sum(q["recall"] for q in per_query) / n,
        "mrr": sum(q["rr"] for q in per_query) / n,
        "n": float(n),
    }
