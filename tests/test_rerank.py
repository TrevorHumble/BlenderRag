from blender_rag.rerank import apply_rerank


def test_apply_rerank_sorts_by_score_and_truncates():
    hits = [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}, {"id": "c", "text": "z"}]
    scores = [0.1, 0.9, 0.5]  # b best, then c, then a
    out = apply_rerank(hits, scores, top_k=2)
    assert [h["id"] for h in out] == ["b", "c"]
    assert out[0]["rerank_score"] == 0.9
    # original hits were annotated in place
    assert all("rerank_score" in h for h in hits)


def test_apply_rerank_top_k_larger_than_hits():
    hits = [{"id": "a", "text": "x"}]
    assert len(apply_rerank(hits, [0.3], top_k=10)) == 1
