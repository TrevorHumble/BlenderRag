"""The session runner: drive an agent through an iterative Blender build loop and
record a :class:`SessionLog`.

The runner is backend-agnostic. It talks to three small interfaces — a
``SceneAgent`` (decides the next action), an optional ``RagSearcher`` (the
knowledge base), and a ``BlenderExecutor`` (runs code, snapshots the scene) — so
the same loop runs against fakes in CI and against a real model + live Blender in
production. RAG-on vs RAG-off is just: pass a searcher, or pass ``None``.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel

from blender_rag.sceneval.schema import (
    CodeExecEvent,
    RagQueryEvent,
    SceneSnapshot,
    SessionEvent,
    SessionLog,
)


class AgentAction(BaseModel):
    """One decision from the agent: search, run code, or stop."""

    kind: Literal["query", "exec", "done"]
    query: str = ""
    source_type: str | None = None
    top_k: int = 6
    code: str = ""


class CodeResult(BaseModel):
    """Outcome of executing a code action."""

    ok: bool
    error_type: str | None = None
    error_message: str | None = None


@runtime_checkable
class SceneAgent(Protocol):
    def next_action(self, history: list[SessionEvent]) -> AgentAction: ...


@runtime_checkable
class RagSearcher(Protocol):
    def search(
        self, query: str, *, top_k: int, source_type: str | None
    ) -> list[dict[str, Any]]: ...


@runtime_checkable
class BlenderExecutor(Protocol):
    def execute(self, code: str) -> CodeResult: ...
    def snapshot(self) -> SceneSnapshot: ...


def _trim_hit(hit: dict[str, Any], *, max_text: int = 600) -> dict[str, Any]:
    """Keep just what an agent needs to relay a hit (and to keep logs small)."""
    text = str(hit.get("text", ""))[:max_text]
    return {
        "title": hit.get("title"),
        "source_url": hit.get("source_url"),
        "source_type": hit.get("source_type"),
        "text": text,
    }


def run_session(
    *,
    task_id: str,
    agent: SceneAgent,
    executor: BlenderExecutor,
    searcher: RagSearcher | None = None,
    rag_enabled: bool,
    model: str = "",
    run_index: int = 0,
    max_iterations: int = 50,
) -> SessionLog:
    """Run one build session and return its log.

    ``rag_enabled`` records the condition; the RAG tool is only actually invoked
    when ``rag_enabled`` is true *and* a ``searcher`` was supplied. A ``query``
    action in the RAG-off condition is recorded with ``n_hits=0`` (the tool was
    unavailable), so the agent's intent is still visible in the log.
    """
    events: list[SessionEvent] = []
    completed = False

    for _ in range(max_iterations):
        action = agent.next_action(events)
        if action.kind == "done":
            completed = True
            break
        if action.kind == "query":
            hits: list[dict[str, Any]] = []
            if rag_enabled and searcher is not None:
                hits = searcher.search(
                    action.query, top_k=action.top_k, source_type=action.source_type
                )
            events.append(
                RagQueryEvent(
                    query=action.query,
                    source_type=action.source_type,
                    top_k=action.top_k,
                    n_hits=len(hits),
                    hits=[_trim_hit(h) for h in hits],
                )
            )
        elif action.kind == "exec":
            result = executor.execute(action.code)
            events.append(
                CodeExecEvent(
                    code=action.code,
                    ok=result.ok,
                    error_type=result.error_type,
                    error_message=result.error_message,
                )
            )

    return SessionLog(
        task_id=task_id,
        rag_enabled=rag_enabled,
        run_index=run_index,
        model=model,
        events=events,
        final_scene=executor.snapshot(),
        completed=completed,
    )
