"""Acquire Blender release notes from the developer-docs repo.

Release notes live as clean markdown at ``docs/release_notes/<version>/*.md``
inside ``blender-developer-docs`` (one file per topic: python_api, geometry_nodes,
sequencer, ...). They are the highest-value version-delta signal — they tell the
model what changed from 4.x, so each is tagged with its specific version.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from blender_rag.acquire._repo import ensure_repo
from blender_rag.config import Config, load_config
from blender_rag.schema import Document, SourceType

DEV_DOCS_DIRNAME = "blender-developer-docs"
LIVE_BASE = "https://developer.blender.org/docs/release_notes"

_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _title_for(text: str, version: str, slug: str) -> str:
    m = _H1.search(text)
    base = m.group(1).strip() if m else slug.replace("_", " ").title()
    return f"Blender {version} Release Notes — {base}"


def _url_for(version: str, slug: str) -> str:
    if slug == "index":
        return f"{LIVE_BASE}/{version}/"
    return f"{LIVE_BASE}/{version}/{slug}/"


def documents_from_dir(version: str, vdir: str | Path) -> Iterator[Document]:
    """Yield one Document per markdown file in a release-notes version dir.

    Pure (no network) — operates on an already-present directory, so it is
    unit-testable with a fake fixture dir.
    """
    vdir = Path(vdir)
    for md in sorted(vdir.glob("*.md")):
        text = md.read_text(encoding="utf-8").strip()
        if not text:
            continue
        slug = md.stem
        yield Document.create(
            text=text,
            source_type=SourceType.RELEASE_NOTES,
            source_url=_url_for(version, slug),
            title=_title_for(text, version, slug),
            blender_version=version,
            extra={"topic": slug},
        )


def acquire_release_notes(cfg: Config | None = None) -> Iterator[Document]:
    """Clone (if needed) the dev-docs repo and yield release-note Documents."""
    cfg = cfg or load_config()
    repo_url = cfg.section("sources", "dev_docs", "repo")
    versions = cfg.section("sources", "release_notes", "versions") or []
    repo_dest = cfg.path("raw") / DEV_DOCS_DIRNAME
    ensure_repo(repo_url, repo_dest)
    for version in versions:
        vdir = repo_dest / "docs" / "release_notes" / str(version)
        if vdir.is_dir():
            yield from documents_from_dir(str(version), vdir)
