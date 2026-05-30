from blender_rag.contextualize import build_prompt, contextualize_chunks
from blender_rag.schema import Chunk, Document, SourceType


class FakeContextualizer:
    def __init__(self):
        self.calls = []

    def context_for(self, document_text, chunk_text):
        self.calls.append((document_text, chunk_text))
        return f"From doc about {document_text[:10]}."


def _doc_and_chunk(source_type=SourceType.MANUAL):
    doc = Document.create(
        text="A full manual page about modifiers and how to use them.",
        source_type=source_type,
        source_url="u",
        title="t",
    )
    chunk = Chunk.from_document(doc, "Apply the modifier from the dropdown.", 0)
    return doc, chunk


def test_build_prompt_includes_document_and_chunk_and_truncates():
    p = build_prompt("D" * 9000, "MARKER", max_doc_chars=100)
    assert "MARKER" in p
    assert p.count("D") == 100  # document truncated to max_doc_chars


def test_contextualize_fills_and_prepends_context():
    doc, chunk = _doc_and_chunk()
    out = list(contextualize_chunks([chunk], [doc], FakeContextualizer()))
    assert out[0].context.startswith("From doc about")
    assert out[0].embed_text.startswith("From doc about")  # prepended for embedding
    assert "Apply the modifier" in out[0].embed_text


def test_contextualize_respects_scope():
    doc, chunk = _doc_and_chunk(SourceType.API)
    fake = FakeContextualizer()
    out = list(contextualize_chunks([chunk], [doc], fake, scope=["manual"]))
    assert out[0].context == ""  # api chunk skipped under manual-only scope
    assert fake.calls == []


def test_contextualize_is_resumable():
    doc, chunk = _doc_and_chunk()
    done = chunk.model_copy(update={"context": "already here"})
    fake = FakeContextualizer()
    out = list(contextualize_chunks([done], [doc], fake))
    assert out[0].context == "already here"
    assert fake.calls == []  # not regenerated
