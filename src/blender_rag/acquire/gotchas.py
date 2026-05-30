"""Acquire curated Blender 5.x gotchas / Python-identifier notes.

Hand-curated, version-current *behavioral* knowledge that the per-symbol API
reference doesn't carry (hide_viewport keyframe inversion, menu sockets take
display strings, NISHITA removed, the compositor-as-node-group pattern, ...).
Sourced from the blender-mcp skill + runtime findings. Lives in-repo under
``corpus/curated/`` (committed, unlike the downloaded sources). Markdown, so the
markdown chunker splits it into one chunk per gotcha section.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from blender_rag.config import Config, load_config
from blender_rag.schema import Document, SourceType

REPO_BLOB = "https://github.com/TrevorHumble/BlenderRag/blob/main"
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def documents_from_curated(
    curated_dir: str | Path, *, repo_rel: str = "corpus/curated"
) -> Iterator[Document]:
    """Yield one Document per curated markdown file (pure, testable)."""
    curated_dir = Path(curated_dir)
    for md in sorted(curated_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            continue
        m = _H1.search(text)
        title = m.group(1).strip() if m else md.stem.replace("_", " ").title()
        yield Document.create(
            text=text,
            source_type=SourceType.GOTCHAS,
            source_url=f"{REPO_BLOB}/{repo_rel}/{md.name}",
            title=title,
            blender_version="5.1",
            extra={"file": md.name},
        )


def acquire_gotchas(cfg: Config | None = None) -> Iterator[Document]:
    cfg = cfg or load_config()
    rel = cfg.section("sources", "gotchas", "dir", default="corpus/curated")
    curated = cfg.root / rel
    if curated.is_dir():
        yield from documents_from_curated(curated, repo_rel=rel)
