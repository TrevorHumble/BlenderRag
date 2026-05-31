"""Deterministic fakes for the session runner — used in CI and for dry-runs.

These let the whole harness (runner -> metrics -> aggregate) be exercised
end-to-end with zero external dependencies. ``ScriptedAgent`` replays a fixed
action list; ``FakeExecutor`` fails code containing any configured marker and
returns a fixed scene snapshot; ``FakeSearcher`` returns N stub hits.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from blender_rag.sceneval.runner import AgentAction, CodeResult
from blender_rag.sceneval.schema import SceneSnapshot, SessionEvent


class ScriptedAgent:
    """Replays ``actions`` in order; returns a ``done`` action when exhausted."""

    def __init__(self, actions: Sequence[AgentAction]):
        self._actions = list(actions)
        self._i = 0

    def next_action(self, history: list[SessionEvent]) -> AgentAction:  # noqa: ARG002
        if self._i >= len(self._actions):
            return AgentAction(kind="done")
        action = self._actions[self._i]
        self._i += 1
        return action


class FakeExecutor:
    """Code fails iff it contains any ``fail_markers`` substring."""

    def __init__(
        self,
        *,
        fail_markers: Iterable[str] = (),
        error_type: str = "RuntimeError",
        snapshot: SceneSnapshot | None = None,
    ):
        self._fail = tuple(fail_markers)
        self._error_type = error_type
        self._snapshot = snapshot or SceneSnapshot()

    def execute(self, code: str) -> CodeResult:
        for marker in self._fail:
            if marker in code:
                return CodeResult(
                    ok=False,
                    error_type=self._error_type,
                    error_message=f"failed on marker {marker!r}",
                )
        return CodeResult(ok=True)

    def snapshot(self) -> SceneSnapshot:
        return self._snapshot


class FakeSearcher:
    """Returns ``hits_per_query`` stub hits for any query."""

    def __init__(self, hits_per_query: int = 3):
        self._n = hits_per_query

    def search(
        self, query: str, *, top_k: int, source_type: str | None
    ) -> list[dict[str, Any]]:
        n = min(self._n, top_k)
        return [{"title": f"{query[:20]}#{i}", "source_type": source_type} for i in range(n)]
