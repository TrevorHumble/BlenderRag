from blender_rag.acquire.bpy_api import documents_from_html
from blender_rag.schema import SourceType

SAMPLE_HTML = """
<html><body>
<dl class="py function">
  <dt class="sig sig-object py" id="bpy.ops.mesh.foo"><span>foo</span>(x)</dt>
  <dd><p>Does foo.</p></dd>
</dl>
<dl class="py class">
  <dt class="sig sig-object py" id="bpy.types.Bar"><span>Bar</span></dt>
  <dd><p>A bar class.</p>
    <dl class="py method">
      <dt class="sig sig-object py" id="bpy.types.Bar.baz"><span>baz</span>()</dt>
      <dd><p>Does baz.</p></dd>
    </dl>
  </dd>
</dl>
</body></html>
"""


def test_documents_from_html_extracts_each_symbol():
    docs = documents_from_html(SAMPLE_HTML, "bpy.types.Bar.html")
    by_name = {d.title: d for d in docs}
    assert set(by_name) == {"bpy.ops.mesh.foo", "bpy.types.Bar", "bpy.types.Bar.baz"}
    assert all(d.source_type is SourceType.API for d in docs)


def test_class_doc_excludes_nested_method_text():
    docs = documents_from_html(SAMPLE_HTML, "bpy.types.Bar.html")
    bar = next(d for d in docs if d.title == "bpy.types.Bar")
    assert "A bar class." in bar.text
    assert "Does baz." not in bar.text  # nested method stripped
    baz = next(d for d in docs if d.title == "bpy.types.Bar.baz")
    assert "Does baz." in baz.text


def test_symbol_metadata_and_url():
    docs = documents_from_html(SAMPLE_HTML, "bpy.ops.mesh.html")
    foo = next(d for d in docs if d.title == "bpy.ops.mesh.foo")
    assert foo.extra["kind"] == "function"
    assert foo.source_url == "https://docs.blender.org/api/current/bpy.ops.mesh.html#bpy.ops.mesh.foo"
    bar = next(d for d in docs if d.title == "bpy.types.Bar" and d.extra["kind"] == "class")
    assert bar.extra["kind"] == "class"


def test_class_summary_lists_members_not_siblings():
    docs = documents_from_html(SAMPLE_HTML, "bpy.types.Bar.html")
    summary = next(d for d in docs if d.extra.get("kind") == "class_summary")
    assert summary.title == "bpy.types.Bar"
    assert "baz" in summary.text  # member listed
    assert "foo" not in summary.text  # sibling top-level function NOT listed
    # distinct id / url from the per-symbol class doc, so they don't collide
    assert summary.source_url.endswith("#bpy.types.Bar-summary")
    per_symbol = next(
        d for d in docs if d.title == "bpy.types.Bar" and d.extra["kind"] == "class"
    )
    assert summary.id != per_symbol.id


def test_class_summary_does_not_drop_per_symbol_docs():
    docs = documents_from_html(SAMPLE_HTML, "bpy.types.Bar.html")
    kinds = {(d.title, d.extra.get("kind")) for d in docs}
    assert ("bpy.ops.mesh.foo", "function") in kinds
    assert ("bpy.types.Bar", "class") in kinds
    assert ("bpy.types.Bar.baz", "method") in kinds
    assert ("bpy.types.Bar", "class_summary") in kinds
