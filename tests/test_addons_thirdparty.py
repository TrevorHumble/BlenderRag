from blender_rag.acquire.addons_thirdparty import (
    documents_from_addon,
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
    assert d.title == "MyAddon/ops/__init__.py"
