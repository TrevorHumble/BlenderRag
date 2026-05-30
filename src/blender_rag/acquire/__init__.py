"""Source acquisition modules — one per Blender 5.1 data source.

Each acquirer yields normalized :class:`~blender_rag.schema.Document` objects.
New sources register here so ``acquire_all`` picks them up.
"""

from __future__ import annotations

from collections.abc import Iterator

from blender_rag.acquire.release_notes import acquire_release_notes
from blender_rag.config import Config, load_config
from blender_rag.schema import Document

# name -> acquirer callable. Extend as sources come online.
ACQUIRERS = {
    "release_notes": acquire_release_notes,
}


def acquire_all(cfg: Config | None = None) -> Iterator[Document]:
    """Run every registered acquirer and yield all Documents."""
    cfg = cfg or load_config()
    for fn in ACQUIRERS.values():
        yield from fn(cfg)


__all__ = ["ACQUIRERS", "acquire_all", "acquire_release_notes"]
