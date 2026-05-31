"""Acquire Blender Stack Exchange answers from the public data dump (CC BY-SA).

The cleanest community source (see docs/CREATIVE_SOURCES_PLAN.md): the dump is
free on archive.org with no LLM clickwrap, and every post carries date + score,
so we can recency/score-filter the heavily-version-mixed corpus down to durable,
well-regarded answers.

**Not registered in the default build.** This is the parser + a thin acquirer; it
runs only when explicitly invoked with a dump path, and wiring it into the corpus
(plus the tier/version_status retrieval rail) is gated on owner approval (#49).
Every Document is tagged creative-tier with provenance for attribution and for
the trust-weight the plan describes.

Pure ``documents_from_dump_xml`` is unit-tested with a small Posts.xml fixture.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

from bs4 import BeautifulSoup

from blender_rag.config import Config, load_config
from blender_rag.schema import Document, SourceType

SE_ANSWER_URL = "https://blender.stackexchange.com/a"


def _version_status(year: int) -> str:
    if year >= 2024:
        return "current"
    if year >= 2021:
        return "dated_valid"
    return "stale"


def _license_for(year: int) -> str:
    # SE relicensed to CC BY-SA 4.0 on 2018-05-02; older posts stay 3.0.
    return "cc-by-sa-4.0" if year >= 2018 else "cc-by-sa-3.0"


def _question_entry(row: ET.Element) -> dict[str, str]:
    return {"title": row.get("Title", ""), "tags": row.get("Tags", "")}


def _answer_to_document(
    ans: ET.Element, questions: dict[str, dict[str, str]], *, min_score: int, since_year: int
) -> Document | None:
    """Build one creative-tier Document from an answer row, or None if filtered.

    Shared by the in-memory and streaming parsers so the filter/provenance logic
    lives in one place.
    """
    try:
        score = int(ans.get("Score", "0"))
    except ValueError:
        score = 0
    created = ans.get("CreationDate", "")
    year = int(created[:4]) if created[:4].isdigit() else 0
    if score < min_score or year < since_year:
        return None
    body = BeautifulSoup(ans.get("Body", ""), "lxml").get_text("\n", strip=True)
    if not body:
        return None
    q = questions.get(ans.get("ParentId", ""), {})
    title = q.get("title") or "Blender Stack Exchange answer"
    return Document.create(
        text=f"Q: {title}\n\nA:\n{body}",
        source_type=SourceType.STACKEXCHANGE,
        source_url=f"{SE_ANSWER_URL}/{ans.get('Id', '')}",
        title=title,
        extra={
            "tier": "creative",
            "version_status": _version_status(year),
            "source_date": created[:10],
            "score": score,
            "author": ans.get("OwnerUserId", ""),
            "question_id": ans.get("ParentId", ""),
            "tags": q.get("tags", ""),
            "license": _license_for(year),
        },
    )


def documents_from_dump_xml(
    posts_xml: str, *, min_score: int = 3, since_year: int = 2019
) -> list[Document]:
    """Parse a Stack Exchange ``Posts.xml`` STRING into answer Documents.

    In-memory; fine for tests and small slices. For the full ~hundreds-of-MB
    Blender dump use :func:`iter_documents_from_posts_file` (streaming).
    """
    root = ET.fromstring(posts_xml)
    questions: dict[str, dict[str, str]] = {}
    answers: list[ET.Element] = []
    for row in root.findall("row"):
        if row.get("PostTypeId") == "1":
            questions[row.get("Id", "")] = _question_entry(row)
        elif row.get("PostTypeId") == "2":
            answers.append(row)
    docs = (
        _answer_to_document(a, questions, min_score=min_score, since_year=since_year)
        for a in answers
    )
    return [d for d in docs if d is not None]


def iter_documents_from_posts_file(
    path: str | Path, *, min_score: int = 3, since_year: int = 2019
) -> Iterator[Document]:
    """Stream a real ``Posts.xml`` file into Documents with bounded memory.

    Uses ``iterparse`` and clears each row after handling, so the 192 MB Blender
    dump never lands in memory whole. Only question *titles* are retained (small);
    answer bodies are processed one at a time. Assumes the SE dump's Id-ascending
    order (a question precedes its answers); an answer whose question hasn't been
    seen falls back to a generic title.
    """
    questions: dict[str, dict[str, str]] = {}
    for _event, row in ET.iterparse(str(path), events=("end",)):
        if row.tag != "row":
            continue
        ptype = row.get("PostTypeId")
        if ptype == "1":
            questions[row.get("Id", "")] = _question_entry(row)
        elif ptype == "2":
            doc = _answer_to_document(row, questions, min_score=min_score, since_year=since_year)
            if doc is not None:
                yield doc
        row.clear()


def extract_posts_xml(archive_7z: str | Path, dest_dir: str | Path) -> Path:
    """Extract ``Posts.xml`` from a Stack Exchange ``.7z`` dump (lazy py7zr)."""
    import py7zr

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    with py7zr.SevenZipFile(str(archive_7z), mode="r") as z:
        z.extract(path=str(dest_dir), targets=["Posts.xml"])
    return dest_dir / "Posts.xml"


def acquire_stackexchange(cfg: Config | None = None) -> Iterator[Document]:
    """Stream SE answer Documents from the dump configured in ``sources``.

    Unregistered by design — call explicitly. Reads ``sources.stackexchange.
    posts_xml`` (an extracted Posts.xml) and streams it. Gated ingestion (#49).
    """
    cfg = cfg or load_config()
    path = cfg.section("sources", "stackexchange", "posts_xml", default=None)
    if not path:
        raise RuntimeError(
            "sources.stackexchange.posts_xml is not set — point it at an extracted "
            "Blender SE Posts.xml (archive.org dump). SE ingestion is gated (#49)."
        )
    min_score = int(cfg.section("sources", "stackexchange", "min_score", default=3))
    since_year = int(cfg.section("sources", "stackexchange", "since_year", default=2019))
    yield from iter_documents_from_posts_file(path, min_score=min_score, since_year=since_year)
