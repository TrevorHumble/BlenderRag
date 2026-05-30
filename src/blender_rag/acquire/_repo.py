"""Shared acquisition helpers: shallow git clone (idempotent)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def ensure_repo(
    repo_url: str,
    dest: str | Path,
    *,
    branch: str | None = None,
    depth: int = 1,
) -> Path:
    """Shallow-clone ``repo_url`` into ``dest`` if not already present.

    Idempotent: if ``dest`` already holds a git working copy, returns it
    unchanged (no network). Returns the destination path.
    """
    dest = Path(dest)
    if (dest / ".git").exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", str(depth)]
    if branch:
        cmd += ["--branch", branch, "--single-branch"]
    cmd += [repo_url, str(dest)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return dest
