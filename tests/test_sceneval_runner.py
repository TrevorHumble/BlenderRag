from blender_rag.sceneval.fakes import FakeExecutor, FakeSearcher, ScriptedAgent
from blender_rag.sceneval.gotchas import count_gotchas
from blender_rag.sceneval.metrics import score
from blender_rag.sceneval.runner import (
    AgentAction,
    BlenderExecutor,
    RagSearcher,
    SceneAgent,
    run_session,
)
from blender_rag.sceneval.schema import CodeExecEvent, RagQueryEvent, SceneSnapshot


def _q(query="how", **kw):
    return AgentAction(kind="query", query=query, **kw)


def _x(code):
    return AgentAction(kind="exec", code=code)


def test_protocols_are_satisfied_by_fakes():
    assert isinstance(ScriptedAgent([]), SceneAgent)
    assert isinstance(FakeSearcher(), RagSearcher)
    assert isinstance(FakeExecutor(), BlenderExecutor)


def test_run_session_records_events_and_snapshot():
    agent = ScriptedAgent(
        [_q("add cube", source_type="api"), _x("bpy.ops..."), AgentAction(kind="done")]
    )
    log = run_session(
        task_id="island",
        agent=agent,
        executor=FakeExecutor(snapshot=SceneSnapshot(objects=2)),
        searcher=FakeSearcher(hits_per_query=3),
        rag_enabled=True,
    )
    assert log.completed is True
    assert isinstance(log.events[0], RagQueryEvent)
    assert log.events[0].n_hits == 3
    assert isinstance(log.events[1], CodeExecEvent)
    assert log.events[1].ok is True
    assert log.final_scene.objects == 2


def test_rag_off_query_records_zero_hits():
    # same agent script, but rag disabled + no searcher -> query yields 0 hits
    agent = ScriptedAgent([_q("add cube"), _x("ok")])
    log = run_session(
        task_id="t", agent=agent, executor=FakeExecutor(), searcher=None, rag_enabled=False
    )
    assert log.events[0].n_hits == 0


def test_executor_failure_is_recorded():
    agent = ScriptedAgent([_x("good"), _x("BAD_CALL"), _x("good2")])
    log = run_session(
        task_id="t",
        agent=agent,
        executor=FakeExecutor(fail_markers=["BAD_CALL"], error_type="AttributeError"),
        rag_enabled=False,
    )
    m = score(log)
    assert m.code_executions == 3
    assert m.code_errors == 1
    assert log.events[1].error_type == "AttributeError"


def test_max_iterations_bounds_runaway_agent():
    # an agent that never says done: loop must stop at max_iterations
    class Loop:
        def next_action(self, history):
            return AgentAction(kind="exec", code="x")

    log = run_session(
        task_id="t", agent=Loop(), executor=FakeExecutor(), rag_enabled=False, max_iterations=5
    )
    assert len(log.events) == 5
    assert log.completed is False


def test_end_to_end_rag_on_vs_off_metrics():
    # RAG-on agent: queries before each call, writes clean 5.x code
    on_actions = [_q("engine"), _x("scene.render.engine = 'BLENDER_EEVEE'"),
                  _q("sky"), _x("# good sky setup")]
    # RAG-off agent: no queries, reaches for 4.x footguns + an error
    off_actions = [_x("scene.render.engine = 'BLENDER_EEVEE_NEXT'"),
                   _x("node.sky_type = 'NISHITA'"),
                   _x("BAD_CALL")]
    on = run_session(
        task_id="island", agent=ScriptedAgent(on_actions),
        executor=FakeExecutor(snapshot=SceneSnapshot(objects=3, materials=2)),
        searcher=FakeSearcher(), rag_enabled=True,
    )
    off = run_session(
        task_id="island", agent=ScriptedAgent(off_actions),
        executor=FakeExecutor(fail_markers=["BAD_CALL"]),
        rag_enabled=False,
    )
    m_on = score(on, gotcha_counter=count_gotchas)
    m_off = score(off, gotcha_counter=count_gotchas)
    assert m_on.query_before_call_rate == 1.0
    assert m_on.gotcha_hits == 0
    assert m_on.clean_run is True
    assert m_off.query_before_call_rate == 0.0
    assert m_off.gotcha_hits == 2  # EEVEE_NEXT + NISHITA
    assert m_off.code_errors == 1
