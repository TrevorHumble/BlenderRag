from blender_rag.acquire.gotchas import documents_from_curated
from blender_rag.schema import SourceType


def test_documents_from_curated(tmp_path):
    (tmp_path / "g.md").write_text(
        "# Blender 5.x gotchas\n\n## Layered Actions\n\naction.fcurves is gone.\n",
        encoding="utf-8",
    )
    (tmp_path / "empty.md").write_text("   \n", encoding="utf-8")

    docs = list(documents_from_curated(tmp_path, repo_rel="corpus/curated"))

    assert len(docs) == 1
    d = docs[0]
    assert d.source_type is SourceType.GOTCHAS
    assert d.title == "Blender 5.x gotchas"
    assert d.source_url.endswith("corpus/curated/g.md")
    assert d.blender_version == "5.1"
