from blender_rag.acquire.addons_thirdparty import (
    documents_from_addon,
    find_manifest,
    is_current_manifest,
)
from blender_rag.schema import SourceType


def test_current_manifest_passes_floor():
    assert is_current_manifest('blender_version_min = "5.1.0"') is True
    assert is_current_manifest('blender_version_min = "4.2.0"') is True


def test_old_or_missing_manifest_rejected():
    assert is_current_manifest('blender_version_min = "3.5.0"') is False
    assert is_current_manifest('name = "x"') is False  # no key
    assert is_current_manifest("not valid toml :::") is False
    assert is_current_manifest('blender_version_min = "garbage"') is False


def test_documents_from_addon_emits_creative_code_docs(tmp_path):
    sub = tmp_path / "ops"
    sub.mkdir()
    (sub / "__init__.py").write_text("import bpy\n\ndef register():\n    pass\n")
    (sub / "empty.py").write_text("  \n")  # skipped
    docs = list(documents_from_addon(tmp_path, name="MyAddon", license_id="gpl-3.0"))
    assert len(docs) == 1
    d = docs[0]
    assert d.source_type is SourceType.CODE
    assert d.extra["tier"] == "creative"
    assert d.extra["license"] == "gpl-3.0"
    assert d.extra["addon"] == "MyAddon"
    assert d.extra["version_status"] == "current"
    assert d.title == "MyAddon/ops/__init__.py"


def test_find_manifest_in_subdir(tmp_path):
    # manifest in a package subdir (the case that wrongly skipped MolecularNodes)
    pkg = tmp_path / "molecularnodes"
    pkg.mkdir()
    (pkg / "blender_manifest.toml").write_text('blender_version_min = "5.1.0"')
    found = find_manifest(tmp_path)
    assert found is not None
    assert found.parent.name == "molecularnodes"


def test_find_manifest_prefers_shallowest(tmp_path):
    (tmp_path / "blender_manifest.toml").write_text('blender_version_min = "5.0.0"')
    deep = tmp_path / "sub"
    deep.mkdir()
    (deep / "blender_manifest.toml").write_text('blender_version_min = "4.2.0"')
    assert find_manifest(tmp_path).parent == tmp_path  # root wins


def test_find_manifest_absent(tmp_path):
    assert find_manifest(tmp_path) is None


def test_single_component_manifest_min_not_rejected():
    assert is_current_manifest('blender_version_min = "5"') is True  # -> (5,0) >= (4,2)
    assert is_current_manifest('blender_version_min = "4"') is False  # (4,0) < (4,2)


def test_source_url_derives_from_repo_url(tmp_path):
    (tmp_path / "a.py").write_text("import bpy\n")
    docs = list(documents_from_addon(
        tmp_path, name="MolecularNodes", license_id="gpl-3.0",
        repo_url="https://github.com/BradyAJohnston/MolecularNodes.git",
    ))
    assert docs[0].source_url == (
        "https://github.com/BradyAJohnston/MolecularNodes/blob/HEAD/a.py"
    )


def test_skips_tests_and_packaging_noise(tmp_path):
    (tmp_path / "addon.py").write_text("import bpy\n")
    (tmp_path / "setup.py").write_text("from setuptools import setup\n")
    (tmp_path / "test_thing.py").write_text("def test_x(): pass\n")
    tdir = tmp_path / "tests"
    tdir.mkdir()
    (tdir / "helpers.py").write_text("x = 1\n")
    titles = {d.title for d in documents_from_addon(tmp_path, name="A", license_id="gpl-3.0")}
    assert titles == {"A/addon.py"}  # setup.py, test_*.py, tests/ all skipped
