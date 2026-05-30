"""Acquire the Blender developer handbook (markdown).

The handbook lives at ``docs/handbook/**/*.md`` in the same dev-docs repo used
for release notes (build/design/internals docs). Markdown, so the existing
markdown chunker handles it directly. One Document per page.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from blender_rag.acquire._repo import ensure_repo
from blender_rag.config import Config, load_config
from blender_rag.schema import Document, SourceType

DEV_DOCS_DIRNAME = "blender-developer-docs"
HANDBOOK_URL_BASE = "https://developer.blender.org/docs/handbook"
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _title(text: str, relpath: str) -> str:
    m = _H1.search(text)
    if m:
        return m.group(1).strip()
    return relpath.rsplit("/", 1)[-1].replace("_", " ").title()


def documents_from_handbook(
    handbook_dir: str | Path, *, min_chars: int = 120
) -> Iterator[Document]:
    handbook_dir = Path(handbook_dir)
    for md in sorted(handbook_dir.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore").strip()
        if len(text) < min_chars:
            continue
        relpath = md.relative_to(handbook_dir).as_posix()[:-3]  # drop ".md"
        yield Document.create(
            text=text,
            source_type=SourceType.DEV_DOCS,
            source_url=f"{HANDBOOK_URL_BASE}/{relpath}/",
            title=_title(text, relpath),
            extra={"path": relpath},
        )


def acquire_dev_docs(cfg: Config | None = None) -> Iterator[Document]:
    cfg = cfg or load_config()
    repo = cfg.section("sources", "dev_docs", "repo")
    dest = cfg.path("raw") / DEV_DOCS_DIRNAME
    ensure_repo(repo, dest)
    yield from documents_from_handbook(dest / "docs" / "handbook")
