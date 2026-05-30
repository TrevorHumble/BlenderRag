from blender_rag.config import load_config


def test_config_loads_defaults():
    cfg = load_config()
    assert cfg.blender_version == "5.1"
    assert cfg.path("index").name == "lancedb"
    assert cfg.section("sources", "manual", "branch") == "blender-v5.1-release"
    assert cfg.section("sources", "missing", "x", default="fallback") == "fallback"
