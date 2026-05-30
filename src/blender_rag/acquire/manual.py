"""Acquire the Blender manual (Sphinx RST).

Clones the version-pinned manual, converts each RST page to clean markdown
(see :mod:`blender_rag.acquire._rst`), and emits one Document per page. The
existing markdown chunker then splits on the converted headers. Near-empty
pages (bare ``toctree`` index stubs) are skipped.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from blender_rag.acquire._repo import ensure_repo
from blender_rag.acquire._rst import rst_to_markdown
from blender_rag.config import Config, load_config
from blender_rag.schema import Document, SourceType

MANUAL_DIRNAME = "blender-manual"
MANUAL_URL_BASE = "https://docs.blender.org/manual/en/5.1"
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _title(md: str, relpath: str) -> str:
    m = _H1.search(md)
    if m:
        return m.group(1).strip()
    return relpath.rsplit("/", 1)[-1].replace("_", " ").title()


def documents_from_manual(manual_root: str | Path, *, min_chars: int = 120) -> Iterator[Document]:
    """Yield one Document per manual RST page (pure: operates on a local tree)."""
    manual_root = Path(manual_root)
    for rst in sorted(manual_root.rglob("*.rst")):
        raw = rst.read_text(encoding="utf-8", errors="ignore")
        md = rst_to_markdown(raw).strip()
        if len(md) < min_chars:  # skip near-empty toctree/index stubs
            continue
        relpath = rst.relative_to(manual_root).as_posix()[:-4]  # drop ".rst"
        yield Document.create(
            text=md,
            source_type=SourceType.MANUAL,
            source_url=f"{MANUAL_URL_BASE}/{relpath}.html",
            title=_title(md, relpath),
            blender_version="5.1",
            extra={"path": relpath},
        )


def acquire_manual(cfg: Config | None = None) -> Iterator[Document]:
    cfg = cfg or load_config()
    repo = cfg.section("sources", "manual", "repo")
    branch = cfg.section("sources", "manual", "branch")
    dest = cfg.path("raw") / MANUAL_DIRNAME
    ensure_repo(repo, dest, branch=branch)
    yield from documents_from_manual(dest / "manual")
