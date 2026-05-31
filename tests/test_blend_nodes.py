from blender_rag.acquire.blend_nodes import serialize_node_graph

GRAPH = {
    "name": "Rock",
    "kind": "material",
    "nodes": [
        {"name": "Principled BSDF", "type": "ShaderNodeBsdfPrincipled",
         "inputs": {"Roughness": 0.8, "Metallic": 0.0, "Base Color": (0.5, 0.4, 0.3, 1.0)}},
        {"name": "Noise Texture", "type": "ShaderNodeTexNoise", "inputs": {"Scale": 5.0}},
    ],
    "links": [
        {"from_node": "Noise Texture", "from_socket": "Fac",
         "to_node": "Principled BSDF", "to_socket": "Roughness"},
    ],
}


def test_serialize_includes_header_nodes_and_links():
    text = serialize_node_graph(GRAPH)
    assert "Material node graph: Rock" in text
    assert "ShaderNodeBsdfPrincipled 'Principled BSDF'" in text
    assert "Roughness=0.8" in text
    assert "ShaderNodeTexNoise 'Noise Texture'  (Scale=5)" in text
    assert "Noise Texture.Fac -> Principled BSDF.Roughness" in text


def test_vector_socket_compacted():
    text = serialize_node_graph(GRAPH)
    assert "Base Color=(0.5, 0.4, 0.3, 1)" in text  # 4-vector inlined


def test_long_vector_summarized():
    g = {"name": "x", "kind": "geometry",
         "nodes": [{"name": "n", "type": "T", "inputs": {"big": list(range(9))}}], "links": []}
    assert "big=[9 values]" in serialize_node_graph(g)


def test_empty_links_section_omitted():
    g = {"name": "m", "kind": "material",
         "nodes": [{"name": "a", "type": "T", "inputs": {}}], "links": []}
    out = serialize_node_graph(g)
    assert "Links:" not in out
    assert "- T 'a'" in out
