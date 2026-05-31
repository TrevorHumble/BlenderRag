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


def documents_from_dump_xml(
    posts_xml: str, *, min_score: int = 3, since_year: int = 2019
) -> list[Document]:
    """Parse a Stack Exchange ``Posts.xml`` into creative-tier answer Documents.

    Pairs each answer with its question title for context, strips HTML bodies,
    and drops answers below ``min_score`` or older than ``since_year`` (the
    ~Blender-2.8/2019 ingestion floor). Provenance (score, date, author,
    question id, license) rides in ``extra`` for attribution + trust-weighting.
    """
    root = ET.fromstring(posts_xml)
    questions: dict[str, dict[str, str]] = {}
    answers: list[ET.Element] = []
    for row in root.findall("row"):
        post_type = row.get("PostTypeId")
        if post_type == "1":
            questions[row.get("Id", "")] = {
                "title": row.get("Title", ""),
                "tags": row.get("Tags", ""),
            }
        elif post_type == "2":
            answers.append(row)

    docs: list[Document] = []
    for ans in answers:
        try:
            score = int(ans.get("Score", "0"))
        except ValueError:
            score = 0
        created = ans.get("CreationDate", "")
        year = int(created[:4]) if created[:4].isdigit() else 0
        if score < min_score or year < since_year:
            continue

        q = questions.get(ans.get("ParentId", ""), {})
        title = q.get("title") or "Blender Stack Exchange answer"
        body = BeautifulSoup(ans.get("Body", ""), "lxml").get_text("\n", strip=True)
        if not body:
            continue
        ans_id = ans.get("Id", "")
        docs.append(
            Document.create(
                text=f"Q: {title}\n\nA:\n{body}",
                source_type=SourceType.STACKEXCHANGE,
                source_url=f"{SE_ANSWER_URL}/{ans_id}",
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
        )
    return docs


def acquire_stackexchange(cfg: Config | None = None) -> Iterator[Document]:
    """Yield SE answer Documents from the dump path in config.

    Unregistered by design — call explicitly. Needs ``sources.stackexchange.
    posts_xml`` pointing at an extracted ``Posts.xml`` (from the archive.org
    Blender dump). Raises a clear error if unset rather than silently no-op.
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
    with open(path, encoding="utf-8") as f:
        yield from documents_from_dump_xml(f.read(), min_score=min_score, since_year=since_year)
