import pytest

from blender_rag.sceneval.gotchas import count_gotchas, detect_gotchas


def _ids(code):
    return {h.rule_id for h in detect_gotchas(code)}


def test_eevee_next_flagged():
    assert "eevee_next_engine_id" in _ids("scene.render.engine = 'BLENDER_EEVEE_NEXT'")


def test_plain_eevee_not_flagged():
    assert _ids("scene.render.engine = 'BLENDER_EEVEE'") == set()


def test_nishita_flagged():
    assert "nishita_sky_removed" in _ids("node.sky_type = 'NISHITA'")


def test_agx_casing_wrong_flagged_correct_ok():
    assert "agx_view_transform_casing" in _ids("view.view_transform = 'Agx'")
    assert "agx_view_transform_casing" not in _ids("view.view_transform = 'AgX'")
    # an unrelated transform value is not flagged
    assert "agx_view_transform_casing" not in _ids("view.view_transform = 'Filmic'")


def test_glare_type_attr_flagged():
    assert "glare_type_attribute" in _ids("node.glare_type = 'FOG_GLOW'")


def test_bgl_flagged_two_forms():
    assert "bgl_module_removed" in _ids("import bgl")
    assert "bgl_module_removed" in _ids("bgl.glEnable(x)")


def test_register_module_flagged():
    assert "register_module_removed" in _ids("bpy.utils.register_module(__name__)")


def test_new_effect_missing_length_flagged_but_with_length_ok():
    assert "new_effect_missing_length" in _ids("seq.strips.new_effect(type='CROSS')")
    assert "new_effect_missing_length" not in _ids(
        "seq.strips.new_effect(type='CROSS', length=10)"
    )


def test_clean_code_has_no_hits():
    code = "import bpy\nbpy.ops.mesh.primitive_cube_add()\nob = bpy.context.object\n"
    assert detect_gotchas(code) == []
    assert count_gotchas(code) == 0


def test_count_matches_detect_length():
    code = "BLENDER_EEVEE_NEXT and NISHITA and import bgl"
    assert count_gotchas(code) == len(detect_gotchas(code)) == 3


@pytest.mark.parametrize("snippet", ["", "   ", "x = 1"])
def test_no_false_positives_on_trivial(snippet):
    assert count_gotchas(snippet) == 0
