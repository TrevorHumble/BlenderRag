from blender_rag.evaluate import (
    aggregate,
    first_match_rank,
    hit_matches,
    query_metrics,
)


def _hit(**kw):
    base = {"title": "", "source_url": "", "symbol": "", "section": ""}
    base.update(kw)
    return base


def test_hit_matches_is_case_insensitive_across_fields():
    h = _hit(symbol="bpy.ops.mesh.primitive_cube_add")
    assert hit_matches(h, "primitive_cube_add")
    assert hit_matches(h, "PRIMITIVE_CUBE_ADD")
    assert not hit_matches(h, "uv_sphere")
    assert hit_matches(_hit(source_url="https://x/sequencer/"), "sequencer")


def test_first_match_rank():
    hits = [_hit(title="a"), _hit(symbol="target"), _hit(title="c")]
    assert first_match_rank(hits, ["target"]) == 2
    assert first_match_rank(hits, ["nope"]) is None


def test_query_metrics_recall_and_rr():
    hits = [_hit(title="x"), _hit(symbol="foo"), _hit(symbol="bar")]
    m = query_metrics(hits, ["foo", "bar"], k=5)
    assert m["hit"] == 1.0
    assert m["recall"] == 1.0  # both found
    assert m["rr"] == 0.5  # first match at rank 2

    # match exists but below k -> hit@k 0, but rr still reflects the rank
    m2 = query_metrics(hits, ["bar"], k=1)
    assert m2["hit"] == 0.0
    assert m2["recall"] == 0.0
    assert m2["rr"] == 1.0 / 3


def test_query_metrics_no_match():
    hits = [_hit(title="x")]
    m = query_metrics(hits, ["missing"], k=5)
    assert m == {"hit": 0.0, "recall": 0.0, "rr": 0.0}


def test_aggregate_means():
    per_q = [
        {"hit": 1.0, "recall": 1.0, "rr": 1.0},
        {"hit": 0.0, "recall": 0.0, "rr": 0.0},
    ]
    agg = aggregate(per_q)
    assert agg["hit@k"] == 0.5
    assert agg["mrr"] == 0.5
    assert agg["n"] == 2.0
    assert aggregate([])["n"] == 0
