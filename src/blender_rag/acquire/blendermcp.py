"""Acquire the BlenderMCP addon source (Python).

The addon that Claude drives Blender through — directly relevant to this
project's own tool surface. Python, so it routes to the AST chunker.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from blender_rag.acquire._repo import ensure_repo
from blender_rag.config import Config, load_config
from blender_rag.schema import Document, SourceType

BLENDERMCP_DIRNAME = "blender-mcp"
REPO_WEB = "https://github.com/ahujasid/blender-mcp/blob/main"


def documents_from_source(root: str | Path) -> Iterator[Document]:
    root = Path(root)
    for py in sorted(root.rglob("*.py")):
        text = py.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            continue
        rel = py.relative_to(root).as_posix()
        yield Document.create(
            text=text,
            source_type=SourceType.BLENDERMCP,
            source_url=f"{REPO_WEB}/{rel}",
            title=rel,
            extra={"path": rel},
        )


def acquire_blendermcp(cfg: Config | None = None) -> Iterator[Document]:
    cfg = cfg or load_config()
    repo = cfg.section("sources", "blendermcp", "repo")
    dest = cfg.path("raw") / BLENDERMCP_DIRNAME
    ensure_repo(repo, dest)
    yield from documents_from_source(dest)
