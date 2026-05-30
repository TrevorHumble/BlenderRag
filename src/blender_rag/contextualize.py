"""Contextual retrieval (Anthropic-style): prepend an LLM-written context blurb
to each chunk before it is embedded / BM25-indexed.

A chunk read in isolation loses the document it came from ("the ``columns``
parameter was deprecated" — of what?). A one-sentence blurb situating the chunk
within its parent document measurably cuts retrieval failures. The blurb is
stored in :attr:`Chunk.context`; :attr:`Chunk.embed_text` already prepends it.

This is the one expensive ingestion step — one local-LLM call per chunk — so it
is opt-in and **resumable** (chunks that already have context are skipped). The
pure orchestration (``contextualize_chunks``, ``build_prompt``) is unit-tested
with a fake generator; ``OllamaContextualizer`` is the live backend (lazy import).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from typing import Protocol

from blender_rag.schema import Chunk, Document

CONTEXT_PROMPT = """<document>
{document}
</document>

Here is a chunk taken from the document above:
<chunk>
{chunk}
</chunk>

Write ONE short sentence that situates this chunk within the document to improve
search retrieval. Answer with only the sentence, no preamble."""


def build_prompt(document: str, chunk: str, *, max_doc_chars: int = 6000) -> str:
    return CONTEXT_PROMPT.format(document=document[:max_doc_chars], chunk=chunk)


class Contextualizer(Protocol):
    def context_for(self, document_text: str, chunk_text: str) -> str: ...


class OllamaContextualizer:
    """Generate context blurbs with a local Ollama model (one call per chunk)."""

    def __init__(self, model: str, *, host: str | None = None, max_doc_chars: int = 6000):
        import ollama

        self.model = model
        self.max_doc_chars = max_doc_chars
        self.client = ollama.Client(host=host) if host else ollama.Client()

    def context_for(self, document_text: str, chunk_text: str) -> str:
        prompt = build_prompt(document_text, chunk_text, max_doc_chars=self.max_doc_chars)
        resp = self.client.generate(
            model=self.model,
            prompt=prompt,
            options={"num_predict": 80, "temperature": 0.0},
        )
        return resp["response"].strip()


def contextualize_chunks(
    chunks: Iterable[Chunk],
    documents: Sequence[Document],
    contextualizer: Contextualizer,
    *,
    scope: Sequence[str] | None = None,
) -> Iterator[Chunk]:
    """Yield each chunk with ``context`` filled from its parent document.

    Skips chunks whose ``source_type`` is outside ``scope`` and chunks that
    already have context (resumability). Falls back to the chunk's own text if
    the parent document isn't found.
    """
    by_id = {d.id: d for d in documents}
    scope_set = set(scope) if scope else None
    for ch in chunks:
        if ch.context or (scope_set is not None and ch.source_type.value not in scope_set):
            yield ch
            continue
        doc = by_id.get(ch.doc_id)
        doc_text = doc.text if doc is not None else ch.text
        context = contextualizer.context_for(doc_text, ch.text)
        yield ch.model_copy(update={"context": context})
