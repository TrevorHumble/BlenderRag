from blender_rag.schema import Chunk, Document, SourceType, stable_id


def test_stable_id_is_deterministic_and_short():
    a = stable_id("manual", "https://x", "Title")
    b = stable_id("manual", "https://x", "Title")
    assert a == b
    assert len(a) == 16
    assert a != stable_id("manual", "https://x", "Other")


def test_document_create_has_stable_id():
    kw = dict(
        text="body",
        source_type=SourceType.MANUAL,
        source_url="https://docs.blender.org/p",
        title="Modifiers",
    )
    d1 = Document.create(**kw)
    d2 = Document.create(**kw)
    assert d1.id == d2.id
    assert d1.blender_version == "5.1"
    assert d1.source_type is SourceType.MANUAL


def test_document_create_accepts_string_source_type():
    d = Document.create(
        text="x", source_type="api", source_url="u", title="t"
    )
    assert d.source_type is SourceType.API


def test_chunk_from_document_inherits_metadata():
    doc = Document.create(
        text="long body",
        source_type=SourceType.RELEASE_NOTES,
        source_url="https://rel/5.1",
        title="What's New",
        extra={"version": "5.1"},
    )
    chunk = Chunk.from_document(doc, "slice one", 0, extra={"section": "Sequencer"})
    assert chunk.doc_id == doc.id
    assert chunk.source_url == doc.source_url
    assert chunk.source_type is SourceType.RELEASE_NOTES
    assert chunk.extra == {"version": "5.1", "section": "Sequencer"}


def test_chunk_ids_distinguish_position_and_full_text():
    doc = Document.create(text="b", source_type="manual", source_url="u", title="t")
    # same text, different position -> different id
    assert Chunk.from_document(doc, "same", 0).id != Chunk.from_document(doc, "same", 1).id
    # shared 64-char prefix, different tail -> different id (no head collision)
    head = "x" * 64
    a = Chunk.from_document(doc, head + "ALPHA", 0)
    b = Chunk.from_document(doc, head + "BETA", 0)
    assert a.id != b.id


def test_chunk_embed_text_prepends_context():
    doc = Document.create(text="b", source_type="code", source_url="u", title="t")
    plain = Chunk.from_document(doc, "def f(): ...", 0)
    assert plain.embed_text == "def f(): ..."
    ctx = Chunk.from_document(doc, "def f(): ...", 0, context="A helper in addon.py.")
    assert ctx.embed_text.startswith("A helper in addon.py.")
    assert "def f(): ..." in ctx.embed_text
