"""Unit tests for the agent message-mapping (with a fake Anthropic client).

The live backends (InProcessRagSearcher, McpBlenderExecutor, the real Anthropic
call) need an index / Blender / API key and are exercised manually, not in CI.
Here we verify the pure conversation-threading logic of AnthropicSceneAgent.
"""

import json
from types import SimpleNamespace

from blender_rag.sceneval.backends import AnthropicSceneAgent
from blender_rag.sceneval.schema import CodeExecEvent, RagQueryEvent


def _tool_use(uid, name, inp):
    return SimpleNamespace(type="tool_use", id=uid, name=name, input=inp)


def _text(t):
    return SimpleNamespace(type="text", text=t)


def _reply(*blocks):
    return SimpleNamespace(content=list(blocks))


class _FakeMessages:
    def __init__(self, replies):
        self._replies = list(replies)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._replies.pop(0)


class _FakeClient:
    def __init__(self, replies):
        self.messages = _FakeMessages(replies)


def test_agent_maps_tool_use_to_actions_and_threads_results():
    client = _FakeClient([
        _reply(_tool_use("t1", "search_blender_docs", {"query": "add cube", "source_type": "api"})),
        _reply(_tool_use("t2", "execute_blender_code", {"code": "primitive_cube_add()"})),
        _reply(_text("All done.")),  # no tool_use -> session ends
    ])
    agent = AnthropicSceneAgent("Build a cube scene", client=client)

    a1 = agent.next_action([])
    assert a1.kind == "query"
    assert a1.query == "add cube"
    assert a1.source_type == "api"

    # runner would record this; feed a hit back through history
    history = [
        RagQueryEvent(
            query="add cube",
            n_hits=1,
            hits=[{
                "title": "primitive_cube_add",
                "source_url": "u",
                "source_type": "api",
                "text": "adds a cube primitive",
            }],
        )
    ]
    a2 = agent.next_action(history)
    assert a2.kind == "exec"
    assert "primitive_cube_add" in a2.code

    # the 2nd model call must carry a tool_result that relays the retrieved text
    second_messages = json.dumps(client.messages.calls[1]["messages"])
    assert "tool_result" in second_messages
    assert "t1" in second_messages
    assert "adds a cube primitive" in second_messages

    history.append(CodeExecEvent(code="bpy.ops.mesh.primitive_cube_add()", ok=True))
    a3 = agent.next_action(history)
    assert a3.kind == "done"


def test_agent_threads_exec_error_back_to_model():
    client = _FakeClient([
        _reply(_tool_use("e1", "execute_blender_code", {"code": "boom()"})),
        _reply(_text("ok I'll stop")),
    ])
    agent = AnthropicSceneAgent("task", client=client)
    agent.next_action([])
    history = [CodeExecEvent(code="boom()", ok=False, error_type="NameError", error_message="boom")]
    agent.next_action(history)
    second = json.dumps(client.messages.calls[1]["messages"])
    assert "ERROR NameError" in second


def test_agent_first_reply_without_tool_use_is_done_immediately():
    client = _FakeClient([_reply(_text("nothing to do"))])
    agent = AnthropicSceneAgent("task", client=client)
    assert agent.next_action([]).kind == "done"
