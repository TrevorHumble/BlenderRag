from blender_rag.acquire.dev_blog import documents_from_rss, documents_from_wp_posts
from blender_rag.schema import SourceType

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Blender Developers Blog</title>
    <item>
      <title>Cycles memory in 5.2</title>
      <link>https://code.blender.org/2025/05/cycles-memory/</link>
      <pubDate>Wed, 14 May 2025 10:00:00 +0000</pubDate>
      <content:encoded><![CDATA[<p>We reworked <b>memory</b> handling.</p>]]></content:encoded>
    </item>
    <item>
      <title>Old post</title>
      <link>https://code.blender.org/2020/01/old/</link>
      <pubDate>Mon, 06 Jan 2020 09:00:00 +0000</pubDate>
      <description>&lt;p&gt;A 2020 note.&lt;/p&gt;</description>
    </item>
  </channel>
</rss>"""


def test_parses_items_with_content_and_description():
    docs = documents_from_rss(RSS)
    assert len(docs) == 2
    by_title = {d.title: d for d in docs}
    cycles = by_title["Cycles memory in 5.2"]
    assert cycles.source_type is SourceType.DEV_BLOG
    assert "reworked" in cycles.text and "<p>" not in cycles.text  # HTML stripped
    assert cycles.source_url == "https://code.blender.org/2025/05/cycles-memory/"


def test_version_status_from_pubdate_and_license():
    by_title = {d.title: d for d in documents_from_rss(RSS)}
    assert by_title["Cycles memory in 5.2"].extra["version_status"] == "current"  # 2025
    assert by_title["Old post"].extra["version_status"] == "dated_valid"  # 2020
    assert by_title["Cycles memory in 5.2"].extra["license"] == "cc-by-sa-4.0"
    assert by_title["Cycles memory in 5.2"].extra["tier"] == "technical"


def test_skips_items_missing_title_or_body():
    rss = RSS.replace("Old post", "").replace("&lt;p&gt;A 2020 note.&lt;/p&gt;", "")
    assert len(documents_from_rss(rss)) == 1


WP_POSTS = [
    {
        "title": {"rendered": "Volume Grids in Geometry Nodes"},
        "link": "https://code.blender.org/2025/10/volume-grids/",
        "date": "2025-10-07T09:00:00",
        "content": {"rendered": "<p>New <b>volume</b> grids.</p>"},
    },
    {  # missing body -> skipped
        "title": {"rendered": "Empty"},
        "link": "https://code.blender.org/x/",
        "date": "2026-01-01T00:00:00",
        "content": {"rendered": ""},
    },
]


def test_wp_posts_parse_and_skip_empty():
    docs = documents_from_wp_posts(WP_POSTS)
    assert len(docs) == 1
    d = docs[0]
    assert d.source_type is SourceType.DEV_BLOG
    assert d.title == "Volume Grids in Geometry Nodes"
    assert "volume" in d.text and "<p>" not in d.text
    assert d.extra["source_date"] == "2025-10-07"
    assert d.extra["version_status"] == "current"
