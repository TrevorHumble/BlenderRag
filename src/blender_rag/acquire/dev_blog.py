"""Acquire the Blender developer blog (code.blender.org) via its RSS feed.

Pure dev *rationale* — the "why" behind features — which the release notes don't
carry. CC-BY-SA. The site HTML is JS-structured, but the WordPress RSS feed
(``/feed/``) is stable XML with full post content, so we parse that instead of
scraping the DOM.

**Not registered in the default build.** Parser + thin acquirer; wiring +
ingestion are gated (#49/#72). Tagged technical-tier (official dev content) with a
CC-BY-SA license stamp for the commercial-clean filter. Pure ``documents_from_rss``
is unit-tested with a fixture; live-validated against the feed (10 current posts).

Two fetch paths: ``iter_wp_archive`` pages the **full** WordPress REST API archive
(~248 posts) — the default — and ``documents_from_rss`` parses the latest-~10 feed
(``mode: rss``). Both pure parsers (``documents_from_wp_posts`` / ``documents_from_rss``)
are fixture-tested; the fetchers are live.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator

import requests
from bs4 import BeautifulSoup

from blender_rag.config import Config, load_config
from blender_rag.schema import Document, SourceType

FEED_URL = "https://code.blender.org/feed/"
WP_API = "https://code.blender.org/wp-json/wp/v2/posts"
_CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}encoded"


def _year_of(pub_date: str) -> int:
    """RSS pubDate like 'Wed, 14 May 2025 10:00:00 +0000' -> year int (0 if none)."""
    for tok in pub_date.split():
        if tok.isdigit() and len(tok) == 4:
            return int(tok)
    return 0


def documents_from_rss(rss_xml: str) -> list[Document]:
    """Parse a code.blender.org RSS feed into dev-blog Documents (pure)."""
    root = ET.fromstring(rss_xml)
    docs: list[Document] = []
    for item in root.iterfind(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        # Prefer full content:encoded; fall back to description.
        raw_html = item.findtext(_CONTENT_NS) or item.findtext("description") or ""
        body = BeautifulSoup(raw_html, "lxml").get_text("\n", strip=True)
        if not (title and body):
            continue
        year = _year_of(pub)
        docs.append(
            Document.create(
                text=f"{title}\n\n{body}",
                source_type=SourceType.DEV_BLOG,
                source_url=link or FEED_URL,
                title=title,
                extra={
                    "tier": "technical",
                    "version_status": "current" if year >= 2024 else "dated_valid",
                    "source_date": pub[:16],
                    "license": "cc-by-sa-4.0",
                },
            )
        )
    return docs


def _document_from_wp_post(post: dict) -> Document | None:
    """Build a Document from one WordPress REST API post object (pure)."""
    title = (post.get("title", {}).get("rendered") or "").strip()
    raw_html = post.get("content", {}).get("rendered") or ""
    body = BeautifulSoup(raw_html, "lxml").get_text("\n", strip=True)
    if not (title and body):
        return None
    date = (post.get("date") or "")[:10]  # ISO 'YYYY-MM-DD...'
    year = int(date[:4]) if date[:4].isdigit() else 0
    return Document.create(
        text=f"{title}\n\n{body}",
        source_type=SourceType.DEV_BLOG,
        source_url=post.get("link") or WP_API,
        title=title,
        extra={
            "tier": "technical",
            "version_status": "current" if year >= 2024 else "dated_valid",
            "source_date": date,
            "license": "cc-by-sa-4.0",
        },
    )


def documents_from_wp_posts(posts: list[dict]) -> list[Document]:
    """Parse a page of WordPress REST API post objects into Documents (pure)."""
    docs = (_document_from_wp_post(p) for p in posts)
    return [d for d in docs if d is not None]


def iter_wp_archive(
    base_url: str = WP_API, *, per_page: int = 100, max_pages: int = 50
) -> Iterator[Document]:
    """Page the full WordPress archive (the RSS feed is only the latest ~10).

    Stops at the reported ``X-WP-TotalPages`` (or an empty page). Live network.
    """
    for page in range(1, max_pages + 1):
        resp = requests.get(
            base_url,
            params={"per_page": per_page, "page": page, "_fields": "title,link,date,content"},
            timeout=60,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if resp.status_code != 200:
            break
        posts = resp.json()
        if not posts:
            break
        yield from documents_from_wp_posts(posts)
        if page >= int(resp.headers.get("X-WP-TotalPages", page)):
            break


def acquire_dev_blog(cfg: Config | None = None) -> Iterator[Document]:
    """Fetch the dev blog. Defaults to the FULL archive via the WP REST API;
    set ``sources.dev_blog.mode: rss`` for the latest-only feed. Gated (#49/#72)."""
    cfg = cfg or load_config()
    mode = cfg.section("sources", "dev_blog", "mode", default="archive")
    if mode == "rss":
        url = cfg.section("sources", "dev_blog", "feed_url", default=FEED_URL)
        resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        yield from documents_from_rss(resp.text)
    else:
        yield from iter_wp_archive(cfg.section("sources", "dev_blog", "api_url", default=WP_API))
