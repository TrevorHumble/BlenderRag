from blender_rag.sceneval.metrics import query_before_call_rate, score
from blender_rag.sceneval.schema import (
    CodeExecEvent,
    RagQueryEvent,
    SceneSnapshot,
    SessionLog,
)


def _log(events, **kw):
    return SessionLog(task_id="t", rag_enabled=kw.pop("rag", True), events=events, **kw)


def test_error_rate_and_clean_run():
    log = _log([
        CodeExecEvent(code="a", ok=True),
        CodeExecEvent(code="b", ok=False, error_type="AttributeError"),
        CodeExecEvent(code="c", ok=True),
    ])
    m = score(log)
    assert m.code_executions == 3
    assert m.code_errors == 1
    assert abs(m.error_rate - 1 / 3) < 1e-9
    assert m.clean_run is False


def test_clean_run_true_only_when_execs_and_no_errors():
    assert score(_log([CodeExecEvent(code="a", ok=True)])).clean_run is True
    # zero execs is NOT a clean run (nothing was built)
    assert score(_log([RagQueryEvent(query="x")])).clean_run is False
    assert score(_log([])).error_rate == 0.0


def test_query_before_call_rate_consumes_query_per_step():
    # query, exec (grounded) ; exec (not grounded, query already consumed)
    log = _log([
        RagQueryEvent(query="how to cube"),
        CodeExecEvent(code="cube", ok=True),
        CodeExecEvent(code="light", ok=True),
    ])
    assert query_before_call_rate(log) == 0.5
    assert score(log).query_before_call_rate == 0.5


def test_query_before_call_rate_zero_without_queries():
    log = _log([CodeExecEvent(code="a", ok=True), CodeExecEvent(code="b", ok=True)])
    assert query_before_call_rate(log) == 0.0


def test_query_before_call_rate_no_execs_is_zero():
    assert query_before_call_rate(_log([RagQueryEvent(query="x")])) == 0.0


def test_gotcha_counter_injection():
    log = _log([
        CodeExecEvent(code="BLENDER_EEVEE_NEXT", ok=True),
        CodeExecEvent(code="fine", ok=True),
    ])
    # fake detector: 1 gotcha if the marker substring is present
    counter = lambda c: 1 if "EEVEE_NEXT" in c else 0  # noqa: E731
    assert score(log, gotcha_counter=counter).gotcha_hits == 1
    assert score(log).gotcha_hits == 0  # no counter -> 0


def test_task_signal_rate_fraction_of_hints_realized():
    log = SessionLog(
        task_id="t",
        rag_enabled=True,
        success_hints=["BLENDER_EEVEE", "AgX", "principled"],
        events=[CodeExecEvent(code="engine='BLENDER_EEVEE'\nvt='AgX'", ok=True)],
    )
    assert abs(score(log).task_signal_rate - 2 / 3) < 1e-9


def test_task_signal_rate_zero_without_hints():
    log = _log([CodeExecEvent(code="anything", ok=True)])
    assert score(log).task_signal_rate == 0.0


def test_task_signal_rate_case_insensitive():
    log = SessionLog(
        task_id="t", rag_enabled=True, success_hints=["Principled"],
        events=[CodeExecEvent(code="bsdf = nodes.new('ShaderNodeBsdfPrincipled')", ok=True)],
    )
    assert score(log).task_signal_rate == 1.0


def test_counts_queries_iterations_scene():
    log = _log(
        [RagQueryEvent(query="x"), RagQueryEvent(query="y"), CodeExecEvent(code="a", ok=True)],
        final_scene=SceneSnapshot(objects=2, materials=1),
        completed=True,
    )
    m = score(log)
    assert m.rag_queries == 2
    assert m.iterations == 3
    assert m.scene_total == 3
    assert m.completed is True
