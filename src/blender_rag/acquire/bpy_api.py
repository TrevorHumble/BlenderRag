"""Acquire the bpy Python API reference (Sphinx HTML).

The offline reference ships as a versioned zip of Sphinx-generated HTML. Each
symbol is a ``<dl class="py ...">`` with a ``<dt id="fully.qualified.name">``
signature and a ``<dd>`` description. We emit one Document per symbol (precise
retrieval of an exact function/class/property), stripping nested ``<dl>``s so a
class doesn't absorb every method's text — methods become their own Documents.
"""

from __future__ import annotations

import copy
import zipfile
from collections.abc import Iterator
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from blender_rag.config import Config, load_config
from blender_rag.schema import Document, SourceType

API_BASE = "https://docs.blender.org/api/current"
EXTRACT_DIRNAME = "bpy_api"
INNER_DIRNAME = "blender_python_reference_5_1"


def _symbol_kind(dl) -> str:
    classes = dl.get("class", [])
    return next((c for c in classes if c != "py"), "py")


def documents_from_html(html: str, filename: str) -> list[Document]:
    """Parse one Sphinx HTML page into per-symbol Documents (pure, testable)."""
    soup = BeautifulSoup(html, "lxml")
    docs: list[Document] = []
    for dl in soup.select("dl.py"):
        dt = dl.find("dt", recursive=False)
        if dt is None or not dt.get("id"):
            continue
        name = dt["id"]
        signature = dt.get_text(" ", strip=True).replace("¶", "").strip()

        dd = dl.find("dd", recursive=False)
        description = ""
        if dd is not None:
            dd_copy = copy.copy(dd)
            for nested in dd_copy.find_all("dl"):
                nested.decompose()  # children become their own Documents
            description = dd_copy.get_text("\n", strip=True)

        text = signature if not description else f"{signature}\n\n{description}"
        docs.append(
            Document.create(
                text=text,
                source_type=SourceType.API,
                source_url=f"{API_BASE}/{filename}#{name}",
                title=name,
                extra={"symbol": name, "kind": _symbol_kind(dl)},
            )
        )
    return docs


def _ensure_extracted(cfg: Config) -> Path:
    """Download + extract the API zip if the HTML tree isn't already present."""
    raw = cfg.path("raw")
    inner = raw / EXTRACT_DIRNAME / INNER_DIRNAME
    if inner.is_dir():
        return inner

    zip_url = cfg.section("sources", "bpy_api", "zip_url")
    zip_path = raw / "bpy_api_5_1.zip"
    raw.mkdir(parents=True, exist_ok=True)
    if not zip_path.exists():
        resp = requests.get(zip_url, timeout=120, stream=True)
        resp.raise_for_status()
        with zip_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(raw / EXTRACT_DIRNAME)
    return inner


def acquire_bpy_api(cfg: Config | None = None) -> Iterator[Document]:
    """Yield one Document per bpy symbol across the whole API reference."""
    cfg = cfg or load_config()
    root = _ensure_extracted(cfg)
    for html_file in sorted(root.glob("*.html")):
        html = html_file.read_text(encoding="utf-8", errors="ignore")
        yield from documents_from_html(html, html_file.name)
