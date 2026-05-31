"""Acquire Blender's bundled core add-on source (Python).

``scripts/addons_core/`` in the main ``blender/blender`` repo is real,
idiomatic, version-exact bpy — the best in-tree example of how Blender's own
developers drive the API. The repo is enormous, so we blobless-sparse-clone
only that subtree (see ``ensure_repo(..., sparse=...)``).

Python, so it routes to the AST chunker. ``source_type=code``.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from blender_rag.acquire._repo import ensure_repo
from blender_rag.config import Config, load_config
from blender_rag.schema import Document, SourceType

ADDONS_DIRNAME = "blender-core"


def _repo_web(repo: str, branch: str) -> str:
    """Gitea blob base for a clone URL, e.g. .../blender/blender/src/branch/<b>."""
    base = repo.removesuffix(".git")
    return f"{base}/src/branch/{branch}"


def documents_from_source(
    root: str | Path, subdir: str, web_base: str
) -> Iterator[Document]:
    """Yield one Document per ``.py`` file under ``root/subdir`` (pure, testable)."""
    root = Path(root)
    base = root / subdir
    if not base.is_dir():
        return
    for py in sorted(base.rglob("*.py")):
        text = py.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            continue
        rel = py.relative_to(root).as_posix()
        yield Document.create(
            text=text,
            source_type=SourceType.CODE,
            source_url=f"{web_base}/{rel}",
            title=rel,
            extra={"path": rel},
        )


def acquire_addons(cfg: Config | None = None) -> Iterator[Document]:
    cfg = cfg or load_config()
    repo = cfg.section("sources", "addons_core", "repo")
    branch = cfg.section("sources", "addons_core", "branch")
    subdir = cfg.section("sources", "addons_core", "subdir", default="scripts/addons_core")
    dest = cfg.path("raw") / ADDONS_DIRNAME
    ensure_repo(repo, dest, branch=branch, sparse=[subdir])
    yield from documents_from_source(dest, subdir, _repo_web(repo, branch))
