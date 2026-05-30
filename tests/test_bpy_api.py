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
    bar = next(d for d in docs if d.title == "bpy.types.Bar")
    assert bar.extra["kind"] == "class"
