"""LanceDB index: build tables from Chunks and hybrid-search them.

Hybrid retrieval = dense vector search (semantic) fused with BM25 full-text
search (lexical) via reciprocal rank fusion. Metadata columns
(``source_type``, ``blender_version``) support filtered retrieval.

ML/LanceDB imports are lazy so this module imports in the light tier; the pure
helpers (``chunk_to_record``, ``reciprocal_rank_fusion``, ``build_where``) are
unit-testable without torch or lancedb.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from blender_rag.embed import Embedder
from blender_rag.schema import Chunk

DOCS_TABLE = "docs"
CODE_TABLE = "code"

_HIT_FIELDS = (
    "id",
    "text",
    "source_type",
    "source_url",
    "title",
    "blender_version",
    "section",
    "symbol",
)


def chunk_to_record(chunk: Chunk, vector: list[float]) -> dict[str, Any]:
    """Flatten a Chunk (+ its dense vector) into a LanceDB row."""
    return {
        "id": chunk.id,
        "doc_id": chunk.doc_id,
        "source_type": chunk.source_type.value,
        "source_url": chunk.source_url,
        "title": chunk.title,
        "blender_version": chunk.blender_version,
        "section": str(chunk.extra.get("section", "")),
        "symbol": str(chunk.extra.get("symbol", "")),
        "text": chunk.text,
        "embed_text": chunk.embed_text,
        "vector": vector,
    }


def build_where(
    source_type: str | None = None, blender_version: str | None = None
) -> str | None:
    """Build a LanceDB SQL ``where`` clause from optional filters."""
    clauses = []
    if source_type:
        clauses.append(f"source_type = '{source_type}'")
    if blender_version:
        clauses.append(f"blender_version = '{blender_version}'")
    return " AND ".join(clauses) if clauses else None


def reciprocal_rank_fusion(
    result_lists: Sequence[Sequence[dict[str, Any]]], *, k: int = 60
) -> list[tuple[dict[str, Any], float]]:
    """Fuse ranked result lists by id using RRF (score = sum 1/(k+rank))."""
    scores: dict[str, float] = {}
    rows: dict[str, dict[str, Any]] = {}
    for results in result_lists:
        for rank, row in enumerate(results):
            rid = row["id"]
            scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank + 1)
            rows.setdefault(rid, row)
    ordered = sorted(scores, key=lambda r: scores[r], reverse=True)
    return [(rows[r], scores[r]) for r in ordered]


def _to_hit(row: dict[str, Any], score: float) -> dict[str, Any]:
    hit = {field: row.get(field) for field in _HIT_FIELDS}
    hit["score"] = round(float(score), 6)
    return hit


def _create_fts(tbl: Any, column: str) -> None:
    # Newer LanceDB defaults to a native (non-tantivy) FTS index; pass the flag
    # when supported, fall back gracefully on older signatures.
    try:
        tbl.create_fts_index(column, replace=True, use_tantivy=False)
    except TypeError:
        tbl.create_fts_index(column, replace=True)


def build_table(
    chunks: Iterable[Chunk],
    embedder: Embedder,
    db_path: str | Path,
    *,
    table_name: str = DOCS_TABLE,
) -> Any:
    """Embed ``chunks`` and (over)write a LanceDB table with a BM25 FTS index."""
    import lancedb

    chunks = list(chunks)
    if not chunks:
        raise ValueError("no chunks to index")
    vectors = embedder.encode([c.embed_text for c in chunks], show_progress=True)
    records = [
        chunk_to_record(c, v.tolist()) for c, v in zip(chunks, vectors, strict=True)
    ]

    db = lancedb.connect(str(db_path))
    tbl = db.create_table(table_name, data=records, mode="overwrite")
    _create_fts(tbl, "embed_text")
    return tbl


def open_table(db_path: str | Path, table_name: str = DOCS_TABLE) -> Any:
    import lancedb

    return lancedb.connect(str(db_path)).open_table(table_name)


def hybrid_search(
    tbl: Any,
    embedder: Embedder,
    query: str,
    *,
    top_k: int = 6,
    source_type: str | None = None,
    blender_version: str | None = None,
    candidates: int = 40,
) -> list[dict[str, Any]]:
    """Vector + BM25 hybrid search fused with RRF. Returns ``top_k`` hits."""
    where = build_where(source_type, blender_version)

    qvec = embedder.encode_one(query)
    vq = tbl.search(qvec).metric("cosine").limit(candidates)
    if where:
        vq = vq.where(where, prefilter=True)
    vhits = vq.to_list()

    try:
        fq = tbl.search(query, query_type="fts").limit(candidates)
        if where:
            fq = fq.where(where, prefilter=True)
        fhits = fq.to_list()
    except Exception:
        fhits = []  # FTS optional; vector results still valid

    fused = reciprocal_rank_fusion([vhits, fhits])
    return [_to_hit(row, score) for row, score in fused[:top_k]]
