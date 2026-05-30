"""Cross-encoder reranking of retrieved candidates.

Hybrid retrieval (vector + BM25) is good at recall; a cross-encoder reading the
query and each candidate together is far better at precision. We over-fetch
candidates, rerank, and keep the best ``top_k``.

``apply_rerank`` is a pure helper (unit-tested without torch); the ``Reranker``
class lazily loads the model so this module imports in the light CI tier.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def apply_rerank(
    hits: list[dict[str, Any]], scores: Sequence[float], top_k: int
) -> list[dict[str, Any]]:
    """Attach ``rerank_score`` to each hit and return the top_k by that score."""
    for hit, score in zip(hits, scores, strict=True):
        hit["rerank_score"] = round(float(score), 6)
    ranked = sorted(hits, key=lambda h: h["rerank_score"], reverse=True)
    return ranked[:top_k]


class Reranker:
    """Wraps a sentence-transformers CrossEncoder, loaded once and reused."""

    def __init__(self, model_name: str, *, device: str = "auto") -> None:
        from sentence_transformers import CrossEncoder

        from blender_rag.embed import resolve_device

        self.model_name = model_name
        self.device = resolve_device(device)
        self.model = CrossEncoder(model_name, device=self.device, trust_remote_code=True)

    def rerank(
        self, query: str, hits: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        if not hits:
            return []
        pairs = [(query, hit["text"]) for hit in hits]
        scores = self.model.predict(pairs)
        return apply_rerank(hits, scores, top_k)
