"""Shared acquisition helpers: shallow git clone (idempotent)."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path


def ensure_repo(
    repo_url: str,
    dest: str | Path,
    *,
    branch: str | None = None,
    depth: int = 1,
    sparse: Sequence[str] | None = None,
) -> Path:
    """Shallow-clone ``repo_url`` into ``dest`` if not already present.

    Idempotent: if ``dest`` already holds a git working copy, returns it
    unchanged (no network). Returns the destination path.

    ``sparse`` restricts the checkout to the given subdirectories via a
    blobless partial clone (``--filter=blob:none --sparse``). Use this for huge
    monorepos (e.g. ``blender/blender``) where only one subtree is wanted —
    only that subtree's blobs are fetched, not the whole history.
    """
    dest = Path(dest)
    if (dest / ".git").exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["git", "clone", "--depth", str(depth)]
    if branch:
        cmd += ["--branch", branch, "--single-branch"]
    if sparse:
        cmd += ["--filter=blob:none", "--sparse"]
    cmd += [repo_url, str(dest)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    if sparse:
        subprocess.run(
            ["git", "-C", str(dest), "sparse-checkout", "set", *sparse],
            check=True,
            capture_output=True,
            text=True,
        )
    return dest
