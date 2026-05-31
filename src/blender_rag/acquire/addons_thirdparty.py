"""Acquire third-party open-license add-ons as idiomatic 5.x bpy code examples.

The community half of the code tier (see docs/CREATIVE_SOURCES_PLAN.md): a vetted
list of actively-maintained GPL/MIT add-ons whose source shows how people really
script Blender 5.x — geometry nodes, modifiers, operators, drivers, UI. GitHub is
heavily version-mixed, so we admit a repo only if its ``blender_manifest.toml``
declares a recent ``blender_version_min`` (the 4.2+ extensions era) — that single
gate drops the bulk of stale 2.7/2.8 code.

**Not registered in the default build.** Parser/filter + a thin acquirer; cloning
+ ingestion + the tier retrieval rail are gated on approval (#49). GPL source is
safe to index privately but must stay out of any redistributable build — hence the
per-Document ``license`` tag (the commercial-revert filter keys on it).

Pure ``is_current_manifest`` / ``documents_from_addon`` are unit-tested.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterator
from pathlib import Path

from blender_rag.acquire._repo import ensure_repo
from blender_rag.config import Config, load_config
from blender_rag.schema import Document, SourceType

# Vetted 2026-05 (manifest blender_version_min confirmed). (name, url, license).
VETTED: tuple[tuple[str, str, str], ...] = (
    ("MolecularNodes", "https://github.com/BradyAJohnston/MolecularNodes.git", "gpl-3.0"),
    ("tissue", "https://github.com/alessandro-zomparelli/tissue.git", "gpl-3.0"),
    ("NodeToPython", "https://github.com/BrendanParmer/NodeToPython.git", "gpl-3.0"),
    ("CAD_Sketcher", "https://github.com/hlorus/CAD_Sketcher.git", "gpl-3.0"),
    ("JewelCraft", "https://github.com/mrachinskiy/jewelcraft.git", "gpl-3.0"),
    ("Projectors", "https://github.com/Ocupe/Projectors.git", "gpl-3.0"),
    ("camera_shakify", "https://github.com/EatTheFuture/camera_shakify.git", "gpl-3.0"),
    ("fake-bpy-module", "https://github.com/nutti/fake-bpy-module.git", "mit"),
    ("pynodes", "https://github.com/iplai/pynodes.git", "mit"),  # node-as-code (MIT, sell-safe)
)

WEB_BASE = "https://github.com"


def is_current_manifest(toml_text: str, *, floor: tuple[int, int] = (4, 2)) -> bool:
    """True if ``blender_manifest.toml`` declares blender_version_min >= ``floor``.

    The manifest format only exists in the 4.2+ extensions era, so its mere
    presence + a recent floor is the strongest single currency signal.
    """
    try:
        data = tomllib.loads(toml_text)
    except (tomllib.TOMLDecodeError, ValueError):
        return False
    raw = data.get("blender_version_min")
    if not isinstance(raw, str):
        return False
    try:
        parts = tuple(int(x) for x in raw.split(".")[:2])
    except ValueError:
        return False
    if not parts:
        return False
    if len(parts) == 1:  # "5" -> (5, 0), so a major-only manifest isn't dropped
        parts = (parts[0], 0)
    return parts >= floor


def find_manifest(root: str | Path) -> Path | None:
    """Locate ``blender_manifest.toml`` at the repo root OR in a package subdir.

    Many add-ons ship the manifest inside their package folder, not at the repo
    root, so a root-only check wrongly skips current add-ons (e.g. MolecularNodes,
    min 5.1). Prefer the shallowest match.
    """
    root = Path(root)
    matches = sorted(root.rglob("blender_manifest.toml"), key=lambda p: (len(p.parts), str(p)))
    return matches[0] if matches else None


# Non-bpy noise to skip: tests, packaging, vendored deps, caches.
_SKIP_PARTS = {"tests", "test", "__pycache__", ".git", "vendor", "vendored", "lib", "libs"}
_SKIP_FILES = {"setup.py", "conftest.py"}


def _web_base(repo_url: str | None, name: str) -> str:
    """GitHub blob base from the clone URL (owner/repo), else a name fallback."""
    if repo_url:
        return f"{repo_url.removesuffix('.git')}/blob/HEAD"
    return f"{WEB_BASE}/{name}"


def documents_from_addon(
    root: str | Path,
    *,
    name: str,
    license_id: str,
    version_status: str = "current",
    repo_url: str | None = None,
) -> Iterator[Document]:
    """Yield one CODE Document per idiomatic ``.py`` in an add-on repo (pure).

    Skips tests / packaging / vendored / cache files so the corpus stays
    idiomatic-bpy, not build scaffolding.
    """
    root = Path(root)
    web = _web_base(repo_url, name)
    for py in sorted(root.rglob("*.py")):
        rel_parts = py.relative_to(root).parts
        if py.name in _SKIP_FILES or py.name.startswith("test_"):
            continue
        if _SKIP_PARTS.intersection(rel_parts):
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            continue
        rel = py.relative_to(root).as_posix()
        yield Document.create(
            text=text,
            source_type=SourceType.CODE,
            source_url=f"{web}/{rel}",
            title=f"{name}/{rel}",
            extra={
                "tier": "creative",
                "addon": name,
                "license": license_id,
                "version_status": version_status,
                "path": rel,
            },
        )


def acquire_addons_thirdparty(cfg: Config | None = None) -> Iterator[Document]:
    """Clone the vetted add-ons and yield code Documents (current manifests only).

    Unregistered by design — call explicitly. Skips any repo whose manifest isn't
    4.2+ (or is missing), logging nothing to keep this importable in the light tier.
    """
    cfg = cfg or load_config()
    dest_root = cfg.path("raw") / "addons_thirdparty"
    for name, url, license_id in VETTED:
        dest = dest_root / name
        ensure_repo(url, dest)
        # MIT mirrors (fake-bpy-module, pynodes) aren't extensions — always take.
        if license_id != "mit":
            manifest = find_manifest(dest)
            if manifest is None or not is_current_manifest(
                manifest.read_text(encoding="utf-8", errors="ignore")
            ):
                continue
        yield from documents_from_addon(
            dest, name=name, license_id=license_id, repo_url=url
        )
