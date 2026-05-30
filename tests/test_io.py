from blender_rag.io import read_jsonl, write_jsonl
from blender_rag.schema import Document, SourceType


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
