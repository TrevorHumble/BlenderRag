from blender_rag.acquire.blendermcp import documents_from_source
from blender_rag.acquire.dev_docs import documents_from_handbook
from blender_rag.schema import SourceType


def test_handbook_docs(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "build.md").write_text(
        "# Building Blender\n\nDetailed steps to build Blender from source with "
        "cmake and the required precompiled library dependencies on Windows, "
        "macOS, and Linux, including how to keep them up to date.",
        encoding="utf-8",
    )
    (tmp_path / "stub.md").write_text("# x", encoding="utf-8")  # too short -> skipped

    docs = list(documents_from_handbook(tmp_path))
    assert len(docs) == 1
    d = docs[0]
    assert d.source_type is SourceType.DEV_DOCS
    assert d.title == "Building Blender"
    assert d.source_url.endswith("/sub/build/")


def test_blendermcp_source(tmp_path):
    (tmp_path / "addon.py").write_text(
        "import bpy\n\ndef register():\n    pass\n", encoding="utf-8"
    )
    (tmp_path / "empty.py").write_text("", encoding="utf-8")  # skipped

    docs = list(documents_from_source(tmp_path))
    assert len(docs) == 1
    assert docs[0].source_type is SourceType.BLENDERMCP
    assert docs[0].title == "addon.py"
    assert "register" in docs[0].text
