"""Dense embedding via sentence-transformers (BGE-M3 by default).

ML imports are lazy so this module imports without torch installed; only
constructing an :class:`Embedder` pulls the heavy stack. That keeps the rest of
the package CI-testable in the light dependency tier.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import numpy as np


def resolve_device(pref: str = "auto") -> str:
    """Resolve an ``embedding.device`` preference to a concrete device string."""
    if pref and pref != "auto":
        return pref
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


class Embedder:
    """Wraps a SentenceTransformer model, loaded once and reused for queries."""

    def __init__(
        self,
        model_name: str,
        *,
        device: str = "auto",
        batch_size: int = 32,
        normalize: bool = True,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.device = resolve_device(device)
        self.batch_size = batch_size
        self.normalize = normalize
        # trust_remote_code: some code embedders (CodeRankEmbed) require it.
        self.model = SentenceTransformer(
            model_name, device=self.device, trust_remote_code=True
        )

    @property
    def dim(self) -> int:
        return int(self.model.get_sentence_embedding_dimension())

    def encode(self, texts: Sequence[str], *, show_progress: bool = False) -> np.ndarray:
        return self.model.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )

    def encode_one(self, text: str) -> list[float]:
        return self.encode([text])[0].tolist()
