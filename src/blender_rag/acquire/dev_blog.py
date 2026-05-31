"""Acquire the Blender developer blog (code.blender.org) via its RSS feed.

Pure dev *rationale* — the "why" behind features — which the release notes don't
carry. CC-BY-SA. The site HTML is JS-structured, but the WordPress RSS feed
(``/feed/``) is stable XML with full post content, so we parse that instead of
scraping the DOM.

**Not registered in the default build.** Parser + thin acquirer; wiring +
ingestion are gated (#49/#72). Tagged technical-tier (official dev content) with a
CC-BY-SA license stamp for the commercial-clean filter. Pure ``documents_from_rss``
is unit-tested with a fixture; live-validated against the feed (10 current posts).

NOTE: the RSS feed carries only the latest ~10 posts. For the full ~12-year
archive, page the WordPress REST API (``/wp-json/wp/v2/posts?per_page=100&page=N``)
or the sitemap — a follow-up; the RSS path proves the parser + gives current posts.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator

import requests
from bs4 import BeautifulSoup

from blender_rag.config import Config, load_config
from blender_rag.schema import Document, SourceType

FEED_URL = "https://code.blender.org/feed/"
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


def acquire_dev_blog(cfg: Config | None = None) -> Iterator[Document]:
    """Fetch + parse the dev-blog RSS feed. Unregistered (gated, #49/#72)."""
    cfg = cfg or load_config()
    url = cfg.section("sources", "dev_blog", "feed_url", default=FEED_URL)
    resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    yield from documents_from_rss(resp.text)
