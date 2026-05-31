from blender_rag.acquire.stackexchange import documents_from_dump_xml
from blender_rag.schema import SourceType

# Posts.xml fixture: 1 question + 4 answers (high/low score, recent/old).
SAMPLE = """<posts>
  <row Id="1" PostTypeId="1" Title="How to add a subdivision surface modifier?" Tags="&lt;py&gt;" />
  <row Id="2" PostTypeId="2" ParentId="1" Score="42" OwnerUserId="7"
       CreationDate="2024-03-01T10:00:00.000"
       Body="&lt;p&gt;Use &lt;code&gt;modifier_add&lt;/code&gt;.&lt;/p&gt;" />
  <row Id="3" PostTypeId="2" ParentId="1" Score="1" OwnerUserId="8"
       CreationDate="2024-03-02T10:00:00.000"
       Body="&lt;p&gt;low score answer&lt;/p&gt;" />
  <row Id="4" PostTypeId="2" ParentId="1" Score="20" OwnerUserId="9"
       CreationDate="2015-01-01T10:00:00.000"
       Body="&lt;p&gt;old 2.7 era answer&lt;/p&gt;" />
  <row Id="5" PostTypeId="2" ParentId="1" Score="9" OwnerUserId="10"
       CreationDate="2022-06-01T10:00:00.000"
       Body="&lt;p&gt;decent dated answer&lt;/p&gt;" />
</posts>"""


def _by_url(docs):
    return {d.source_url: d for d in docs}


def test_keeps_high_score_recent_answers_only():
    docs = documents_from_dump_xml(SAMPLE, min_score=3, since_year=2019)
    urls = _by_url(docs)
    # answer 2 (score 42, 2024) and 5 (score 9, 2022) pass; 3 (low score) + 4 (old) dropped
    assert set(urls) == {
        "https://blender.stackexchange.com/a/2",
        "https://blender.stackexchange.com/a/5",
    }


def test_pairs_question_title_and_strips_html():
    d = _by_url(documents_from_dump_xml(SAMPLE))["https://blender.stackexchange.com/a/2"]
    assert d.source_type is SourceType.STACKEXCHANGE
    assert "How to add a subdivision surface modifier?" in d.text
    assert "modifier_add" in d.text
    assert "<p>" not in d.text  # HTML stripped


def test_creative_tier_and_provenance_metadata():
    d = _by_url(documents_from_dump_xml(SAMPLE))["https://blender.stackexchange.com/a/2"]
    assert d.extra["tier"] == "creative"
    assert d.extra["version_status"] == "current"  # 2024
    assert d.extra["score"] == 42
    assert d.extra["source_date"] == "2024-03-01"
    assert d.extra["author"] == "7"
    assert d.extra["license"] == "cc-by-sa-4.0"


def test_version_status_gradient():
    d5 = _by_url(documents_from_dump_xml(SAMPLE))["https://blender.stackexchange.com/a/5"]
    assert d5.extra["version_status"] == "dated_valid"  # 2022


def test_old_answer_excluded_by_floor_even_if_high_score():
    # answer 4 is score 20 but 2015 -> below the 2019 floor -> dropped
    docs = documents_from_dump_xml(SAMPLE, min_score=3, since_year=2019)
    assert "https://blender.stackexchange.com/a/4" not in _by_url(docs)
