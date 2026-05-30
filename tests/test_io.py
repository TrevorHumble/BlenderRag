import pytest

from blender_rag.io import read_jsonl, write_jsonl
from blender_rag.schema import Chunk, Document, SourceType


def test_jsonl_round_trip(tmp_path):
    docs = [
        Document.create(text=f"body {i}", source_type=SourceType.MANUAL,
                        source_url=f"https://x/{i}", title=f"t{i}")
        for i in range(3)
    ]
    path = tmp_path / "sub" / "corpus.jsonl"
    n = write_jsonl(path, docs)
    assert n == 3
    assert path.exists()

    loaded = list(read_jsonl(path, Document))
    assert len(loaded) == 3
    assert [d.id for d in loaded] == [d.id for d in docs]
    assert loaded[1].text == "body 1"


def test_chunk_round_trip_preserves_enum_and_context(tmp_path):
    doc = Document.create(text="b", source_type=SourceType.CODE, source_url="u", title="t")
    chunks = [
        Chunk.from_document(doc, "def a(): ...", 0, context="helper a"),
        Chunk.from_document(doc, "def b(): ...", 1),
    ]
    path = tmp_path / "chunks.jsonl"
    write_jsonl(path, chunks)
    loaded = list(read_jsonl(path, Chunk))
    assert loaded[0].source_type is SourceType.CODE
    assert loaded[0].context == "helper a"
    assert [c.id for c in loaded] == [c.id for c in chunks]


def test_read_jsonl_reports_line_number_on_bad_row(tmp_path):
    path = tmp_path / "bad.jsonl"
    # line 1 is valid; line 2 is missing required Document fields
    good = Document.create(text="ok", source_type=SourceType.MANUAL, source_url="u", title="t")
    path.write_text(good.model_dump_json() + '\n{"id":"x"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"bad\.jsonl:2"):
        list(read_jsonl(path, Document))
