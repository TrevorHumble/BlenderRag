"""Integration: drive a full run_session with the real AnthropicSceneAgent
(fake client) + fake searcher/executor. Proves the live-shaped loop —
agent decides -> runner executes -> result threads back -> next decision —
works end to end, not just the isolated message-mapping unit.
"""

from types import SimpleNamespace

from blender_rag.sceneval.backends import AnthropicSceneAgent
from blender_rag.sceneval.fakes import FakeExecutor, FakeSearcher
from blender_rag.sceneval.metrics import score
from blender_rag.sceneval.runner import run_session
from blender_rag.sceneval.schema import CodeExecEvent, RagQueryEvent, SceneSnapshot


def _tool_use(uid, name, inp):
    return SimpleNamespace(type="tool_use", id=uid, name=name, input=inp)


def _text(t):
    return SimpleNamespace(type="text", text=t)


def _reply(*blocks):
    return SimpleNamespace(content=list(blocks))


class _FakeClient:
    def __init__(self, replies):
        self._replies = list(replies)
        self.calls = []

    class _M:
        def __init__(self, outer):
            self._outer = outer

        def create(self, **kwargs):
            self._outer.calls.append(kwargs)
            return self._outer._replies.pop(0)

    @property
    def messages(self):
        return _FakeClient._M(self)


def test_agent_drives_full_session_through_runner():
    client = _FakeClient([
        _reply(_tool_use("q1", "search_blender_docs", {"query": "eevee", "source_type": "api"})),
        _reply(_tool_use("x1", "execute_blender_code", {"code": "engine='BLENDER_EEVEE'"})),
        _reply(_text("Scene complete.")),
    ])
    agent = AnthropicSceneAgent("Set the render engine to EEVEE", client=client)
    log = run_session(
        task_id="island",
        agent=agent,
        executor=FakeExecutor(snapshot=SceneSnapshot(objects=1)),
        searcher=FakeSearcher(hits_per_query=2),
        rag_enabled=True,
        success_hints=["BLENDER_EEVEE"],
        max_iterations=10,
    )

    # the loop produced: query -> exec -> done
    assert [type(e) for e in log.events] == [RagQueryEvent, CodeExecEvent]
    assert log.events[0].n_hits == 2  # real searcher ran and threaded results
    assert log.events[1].ok is True
    assert log.completed is True

    m = score(log)
    assert m.query_before_call_rate == 1.0  # the exec was preceded by a query
    assert m.task_signal_rate == 1.0  # 'BLENDER_EEVEE' realized in code


def test_rag_off_agent_still_runs_but_ungrounded():
    # agent tries to search, but rag is off -> 0 hits, then execs
    client = _FakeClient([
        _reply(_tool_use("q1", "search_blender_docs", {"query": "anything"})),
        _reply(_tool_use("x1", "execute_blender_code", {"code": "ok()"})),
        _reply(_text("done")),
    ])
    agent = AnthropicSceneAgent("task", client=client)
    log = run_session(
        task_id="t", agent=agent, executor=FakeExecutor(),
        searcher=None, rag_enabled=False, max_iterations=10,
    )
    assert log.events[0].n_hits == 0  # tool unavailable in RAG-off
    assert log.completed is True
