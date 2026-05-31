from blender_rag.sceneval.schema import CodeExecEvent, RagQueryEvent, SessionLog
from blender_rag.sceneval.transcript import render_transcript


def test_transcript_shows_queries_execs_errors_and_gotchas():
    log = SessionLog(
        task_id="island",
        rag_enabled=True,
        model="claude-sonnet-4-5",
        success_hints=["BLENDER_EEVEE"],
        events=[
            RagQueryEvent(query="render engine", source_type="api", n_hits=3),
            CodeExecEvent(code="scene.render.engine = 'BLENDER_EEVEE'", ok=True),
            CodeExecEvent(code="x = 'BLENDER_EEVEE_NEXT'", ok=False, error_type="TypeError"),
        ],
        completed=True,
    )
    t = render_transcript(log)
    assert "island" in t and "RAG-on" in t
    assert "SEARCH [api]: render engine  -> 3 hits" in t
    assert "EXEC [OK]" in t
    assert "EXEC [ERR TypeError]" in t
    assert "eevee_next_engine_id" in t  # gotcha annotated inline
    assert "summary:" in t


def test_transcript_rag_off_label_and_no_hints_line():
    log = SessionLog(
        task_id="t", rag_enabled=False,
        events=[CodeExecEvent(code="ok()", ok=True)],
    )
    t = render_transcript(log)
    assert "RAG-off" in t
    assert "brief concepts" not in t  # no success_hints -> line omitted
