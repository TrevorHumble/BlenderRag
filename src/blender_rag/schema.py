"""Core data contracts for the Blender RAG pipeline.

A :class:`Document` is a normalized unit of source content (one manual page,
one API symbol, one release-notes section, one code function). A :class:`Chunk`
is an embeddable slice of a Document that carries enough metadata for filtered,
attributable retrieval (by source type and Blender version).

IDs are deterministic hashes of their identifying parts, so re-running the
pipeline over unchanged sources yields stable IDs (idempotent upserts).
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

_SEP = "\x1f"  # unit separator — won't collide with content


class SourceType(StrEnum):
    """Where a piece of content came from. Used as a retrieval filter."""

    MANUAL = "manual"
    API = "api"
    RELEASE_NOTES = "release_notes"
    DEV_DOCS = "dev_docs"
    CODE = "code"
    BLENDERMCP = "blendermcp"


def stable_id(*parts: str) -> str:
    """Deterministic 16-hex-char id derived from its parts.

    Stable across runs and machines, so unchanged content keeps its id.
    """
    digest = hashlib.sha256(_SEP.join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def _src_value(source_type: SourceType | str) -> str:
    return source_type.value if isinstance(source_type, SourceType) else str(source_type)


class Document(BaseModel):
    """A normalized source document, pre-chunking."""

    id: str
    text: str
    source_type: SourceType
    source_url: str
    title: str
    blender_version: str = "5.1"
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        text: str,
        source_type: SourceType | str,
        source_url: str,
        title: str,
        blender_version: str = "5.1",
        extra: dict[str, Any] | None = None,
    ) -> Document:
        """Build a Document with a deterministic id from (type, url, title)."""
        doc_id = stable_id(_src_value(source_type), source_url, title)
        return cls(
            id=doc_id,
            text=text,
            source_type=SourceType(_src_value(source_type)),
            source_url=source_url,
            title=title,
            blender_version=blender_version,
            extra=extra or {},
        )


class Chunk(BaseModel):
    """An embeddable slice of a :class:`Document`."""

    id: str
    doc_id: str
    text: str
    # Contextual-retrieval blurb (Anthropic-style). Prepended to ``text`` at
    # embed/index time; empty until the contextualize step runs.
    context: str = ""
    source_type: SourceType
    source_url: str
    title: str
    blender_version: str = "5.1"
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def embed_text(self) -> str:
        """Text fed to the embedder and BM25 index: context blurb + body."""
        if self.context:
            return f"{self.context}\n\n{self.text}".strip()
        return self.text

    @classmethod
    def from_document(
        cls,
        doc: Document,
        text: str,
        index: int,
        *,
        context: str = "",
        extra: dict[str, Any] | None = None,
    ) -> Chunk:
        """Create a chunk from ``doc``; id is stable per (doc, position, text)."""
        # Hash the full text (not a prefix): repeated headers / API signatures
        # share long prefixes and would otherwise collide and overwrite.
        chunk_id = stable_id(doc.id, str(index), text)
        merged = dict(doc.extra)
        if extra:
            merged.update(extra)
        return cls(
            id=chunk_id,
            doc_id=doc.id,
            text=text,
            context=context,
            source_type=doc.source_type,
            source_url=doc.source_url,
            title=doc.title,
            blender_version=doc.blender_version,
            extra=merged,
        )
