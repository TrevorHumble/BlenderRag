from blender_rag.chunk import (
    chunk_document,
    pack_section,
    split_markdown_sections,
    split_python_symbols,
)
from blender_rag.schema import Document, SourceType


def test_split_markdown_sections_builds_breadcrumbs():
    md = "# Top\n\nintro text\n\n## A\n\nbody a\n\n### A1\n\nbody a1\n\n## B\n\nbody b\n"
    secs = split_markdown_sections(md)
    paths = [p for p, _ in secs]
    assert ("Top",) in paths
    assert ("Top", "A") in paths
    assert ("Top", "A", "A1") in paths
    assert ("Top", "B") in paths  # deeper level A1 dropped when B opens
    bodies = {p: b for p, b in secs}
    assert bodies[("Top", "A", "A1")] == "body a1"


def test_pack_section_splits_long_body_with_prefix():
    body = "\n\n".join(f"paragraph number {i} with filler words" for i in range(60))
    chunks = pack_section(("Heading",), body, max_chars=200, overlap_chars=20, min_chars=10)
    assert len(chunks) > 1
    assert all(c.startswith("Heading\n\n") for c in chunks)
    assert all(len(c) <= 200 + 40 for c in chunks)  # prefix + small slack


def test_pack_section_short_body_single_chunk():
    chunks = pack_section(("H",), "short body", max_chars=512, overlap_chars=8, min_chars=4)
    assert chunks == ["H\n\nshort body"]


def test_split_python_symbols():
    src = (
        "import bpy\n\n"
        "def add_cube():\n    bpy.ops.mesh.primitive_cube_add()\n\n"
        "class Panel:\n    def draw(self):\n        pass\n"
    )
    syms = split_python_symbols(src)
    names = [name for name, _, _ in syms]
    assert names == ["<module>", "add_cube", "Panel"]
    assert "import bpy" in syms[0][1]
    assert "primitive_cube_add" in syms[1][1]


def test_chunk_document_routes_by_type():
    md_doc = Document.create(
        text=(
            "# H\n\n## Sec\n\n"
            "This is a release note body with enough length to clear the "
            "minimum chunk threshold comfortably."
        ),
        source_type=SourceType.RELEASE_NOTES,
        source_url="u",
        title="t",
    )
    md_chunks = list(chunk_document(md_doc))
    assert md_chunks
    assert all("section" in c.extra for c in md_chunks)

    code_doc = Document.create(
        text="def f():\n    return 1\n",
        source_type=SourceType.CODE,
        source_url="u",
        title="t",
    )
    code_chunks = list(chunk_document(code_doc))
    assert [c.extra["symbol"] for c in code_chunks] == ["f"]
