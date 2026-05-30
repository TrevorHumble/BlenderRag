from blender_rag.acquire.release_notes import (
    _title_for,
    _url_for,
    documents_from_dir,
)
from blender_rag.schema import SourceType


def test_documents_from_dir(tmp_path):
    v = tmp_path / "5.1"
    v.mkdir()
    (v / "python_api.md").write_text("# Python API\n\nNew bpy stuff.\n", encoding="utf-8")
    (v / "index.md").write_text("# Blender 5.1\n\nOverview.\n", encoding="utf-8")
    (v / "empty.md").write_text("   \n", encoding="utf-8")

    docs = list(documents_from_dir("5.1", v))

    assert len(docs) == 2  # empty file skipped
    by_topic = {d.extra["topic"]: d for d in docs}
    api = by_topic["python_api"]
    assert api.source_type is SourceType.RELEASE_NOTES
    assert api.blender_version == "5.1"
    assert api.source_url == "https://developer.blender.org/docs/release_notes/5.1/python_api/"
    assert by_topic["index"].source_url == "https://developer.blender.org/docs/release_notes/5.1/"
    assert "Python API" in api.title


def test_url_and_title_helpers():
    assert _url_for("5.0", "sequencer").endswith("/5.0/sequencer/")
    assert _url_for("5.1", "index").endswith("/5.1/")
    # falls back to humanized slug when no H1 present
    assert _title_for("no header here", "5.1", "geometry_nodes").endswith("Geometry Nodes")
