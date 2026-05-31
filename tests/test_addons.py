from blender_rag.acquire.addons import _repo_web, documents_from_source
from blender_rag.schema import SourceType

WEB = "https://projects.blender.org/blender/blender/src/branch/blender-v5.1-release"


def _make_tree(root):
    sub = root / "scripts" / "addons_core" / "io_demo"
    sub.mkdir(parents=True)
    (sub / "__init__.py").write_text("import bpy\n\ndef register():\n    pass\n")
    (sub / "empty.py").write_text("   \n")  # whitespace-only -> skipped
    (sub / "notes.txt").write_text("not python")  # non-.py -> skipped
    # a .py OUTSIDE the target subdir must not be picked up
    other = root / "scripts" / "modules"
    other.mkdir(parents=True)
    (other / "stray.py").write_text("x = 1\n")


def test_documents_from_source_only_subdir_python(tmp_path):
    _make_tree(tmp_path)
    docs = list(documents_from_source(tmp_path, "scripts/addons_core", WEB))
    titles = {d.title for d in docs}
    assert titles == {"scripts/addons_core/io_demo/__init__.py"}
    d = docs[0]
    assert d.source_type is SourceType.CODE
    assert d.source_url == f"{WEB}/scripts/addons_core/io_demo/__init__.py"
    assert d.extra["path"] == "scripts/addons_core/io_demo/__init__.py"


def test_missing_subdir_yields_nothing(tmp_path):
    assert list(documents_from_source(tmp_path, "scripts/addons_core", WEB)) == []


def test_repo_web_strips_git_suffix():
    assert _repo_web("https://x/blender/blender.git", "blender-v5.1-release") == (
        "https://x/blender/blender/src/branch/blender-v5.1-release"
    )
