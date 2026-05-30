"""End-to-end retrieval regression tests against the real built index.

Complements the metric unit tests (which run on fixtures) by exercising the
actual embed + LanceDB + RRF path: known queries must return the expected hit in
the top-k. Marked ``network`` so the light CI skips it; skips gracefully if the
``ml`` deps or the built index are absent.

Run: ``uv run pytest -m network``
"""

import pytest

pytest.importorskip("lancedb")
pytest.importorskip("sentence_transformers")

from blender_rag.config import load_config  # noqa: E402

pytestmark = pytest.mark.network


@pytest.fixture(scope="module")
def searcher():
    cfg = load_config()
    index_path = cfg.path("index")
    if not (index_path / "docs.lance").exists():
        pytest.skip("index not built — run scripts/build_all.py first")
    from blender_rag.embed import Embedder
    from blender_rag.index import DOCS_TABLE, open_table

    embedder = Embedder(cfg.section("embedding", "prose_model"), device="auto")
    table = open_table(index_path, DOCS_TABLE)
    return embedder, table


@pytest.mark.parametrize(
    "query, expect",
    [
        ("add a cube mesh using a python operator", "primitive_cube_add"),
        ("subdivision surface modifier", "subdivision"),
        ("what changed in the python api in blender 5.1", "python_api"),
        ("how do I extrude faces", "extrude"),
    ],
)
def test_known_query_returns_expected_hit_in_topk(searcher, query, expect):
    from blender_rag.index import hybrid_search

    embedder, table = searcher
    hits = hybrid_search(table, embedder, query, top_k=5)
    blob = " ".join((h["title"] + " " + h["source_url"]) for h in hits).lower()
    assert expect in blob, f"{expect!r} not in top-5 for {query!r}"
