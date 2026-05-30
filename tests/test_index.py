from blender_rag.index import (
    build_where,
    chunk_to_record,
    reciprocal_rank_fusion,
    symbol_name_ranking,
    symbol_name_score,
)
from blender_rag.schema import Chunk, Document, SourceType


def test_symbol_name_score():
    q = set("select or deselect all objects".split())
    assert symbol_name_score("bpy.ops.object.select_all", "", q) == 1.0
    partial = symbol_name_score(
        "bpy.ops.wm.save_mainfile", "", set("save the blend file".split())
    )
    assert 0.0 < partial < 1.0
    assert symbol_name_score("", "", q) == 0.0


def test_symbol_name_ranking_orders_full_match_first():
    rows = [
        {"id": "1", "symbol": "bpy.ops.object.select_linked", "title": ""},
        {"id": "2", "symbol": "bpy.ops.object.select_all", "title": ""},
    ]
    ranked = symbol_name_ranking(rows, "select all objects")
    assert ranked[0]["id"] == "2"  # full leaf match outranks partial


def test_build_where():
    assert build_where() is None
    assert build_where(source_type="manual") == "source_type = 'manual'"
    assert build_where(blender_version="5.1") == "blender_version = '5.1'"
    assert (
        build_where("api", "5.1")
        == "source_type = 'api' AND blender_version = '5.1'"
    )


def test_chunk_to_record_flattens():
    doc = Document.create(text="b", source_type=SourceType.CODE, source_url="u", title="t")
    ch = Chunk.from_document(
        doc, "def f(): ...", 0, context="ctx", extra={"symbol": "f", "line": 3}
    )
    rec = chunk_to_record(ch, [0.1, 0.2])
    assert rec["source_type"] == "code"
    assert rec["symbol"] == "f"
    assert rec["section"] == ""
    assert rec["embed_text"].startswith("ctx")
    assert rec["vector"] == [0.1, 0.2]


def test_rrf_ranks_items_in_both_lists_first():
    a, b, c = {"id": "a"}, {"id": "b"}, {"id": "c"}
    # b appears in both lists -> highest fused score
    fused = reciprocal_rank_fusion([[a, b], [b, c]])
    ids = [row["id"] for row, _ in fused]
    assert ids[0] == "b"
    assert set(ids) == {"a", "b", "c"}
    # scores descending
    scores = [s for _, s in fused]
    assert scores == sorted(scores, reverse=True)
