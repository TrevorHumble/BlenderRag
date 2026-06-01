from blender_rag.sceneval.static_exec import node_new_types, operator_calls, validate_code

# A tiny fake 5.1 symbol table — keeps this test off the real index (CI-friendly).
SYMBOLS = frozenset(
    {
        "bpy.ops.mesh.primitive_cube_add",
        "bpy.ops.object.light_add",
        "bpy.ops.object.select_all",
        "bpy.ops.object.delete",
        "bpy.types.ShaderNodeBsdfPrincipled",
        "bpy.types.FunctionNodeRandomValue",
    }
)


def test_operator_calls_extracts_full_paths():
    code = (
        "import bpy\n"
        "bpy.ops.mesh.primitive_cube_add(size=2)\n"
        "obj = bpy.context.active_object\n"
        "obj.location.x = 1.0\n"  # attribute access, not an operator -> ignored
    )
    assert operator_calls(code) == ["bpy.ops.mesh.primitive_cube_add"]


def test_valid_operators_pass():
    code = "import bpy\nbpy.ops.mesh.primitive_cube_add()\nbpy.ops.object.light_add(type='SUN')\n"
    res = validate_code(code, SYMBOLS)
    assert res.ok
    assert res.error_type is None


def test_hallucinated_operator_flagged():
    code = "import bpy\nbpy.ops.mesh.make_awesome_island()\n"
    res = validate_code(code, SYMBOLS)
    assert not res.ok
    assert res.error_type == "InvalidOperator"
    assert "bpy.ops.mesh.make_awesome_island" in res.error_message


def test_syntax_error_flagged():
    res = validate_code("import bpy\nbpy.ops.mesh.primitive_cube_add(\n", SYMBOLS)
    assert not res.ok
    assert res.error_type == "SyntaxError"


def test_attribute_access_on_runtime_vars_never_flagged():
    # The bulk of real bpy: instance attributes the symbol table can't resolve.
    # These must NOT be treated as errors (precision-first).
    code = (
        "import bpy\n"
        "mod = obj.modifiers.new(name='Subsurf', type='SUBSURF')\n"
        "mod.levels = 2\n"
        "mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8\n"
        "bpy.data.materials.new('m')\n"
    )
    assert validate_code(code, SYMBOLS).ok


def test_node_new_types_extracts_bl_idnames():
    code = (
        "import bpy\n"
        "nt = mat.node_tree\n"
        "a = nt.nodes.new('ShaderNodeBsdfPrincipled')\n"
        "b = nodes.new('FunctionNodeRandomValue')\n"
        "obj.modifiers.new(name='x', type='SUBSURF')\n"  # .new but not on nodes -> ignored
    )
    assert node_new_types(code) == ["ShaderNodeBsdfPrincipled", "FunctionNodeRandomValue"]


def test_valid_node_types_pass():
    code = "import bpy\nn = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')\n"
    assert validate_code(code, SYMBOLS).ok


def test_hallucinated_node_type_flagged():
    # The real Random Value node is FunctionNodeRandomValue; the Geometry* form is invented.
    code = "import bpy\nn = ng.nodes.new('GeometryNodeRandomValue')\n"
    res = validate_code(code, SYMBOLS)
    assert not res.ok
    assert res.error_type == "InvalidNodeType"
    assert "GeometryNodeRandomValue" in res.error_message
