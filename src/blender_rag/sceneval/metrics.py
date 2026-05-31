"""Pure scoring of a :class:`SessionLog` into :class:`SessionMetrics`.

Every function here is a deterministic function of the log — no model, no
Blender, no I/O — so the entire measurement layer is unit-tested in isolation.
The gotcha count is injected as a callable so this module stays independent of
the detector (``gotchas.py``); the runner/aggregate wire the real one in.
"""

from __future__ import annotations

from collections.abc import Callable

from blender_rag.sceneval.schema import (
    CodeExecEvent,
    RagQueryEvent,
    SessionLog,
    SessionMetrics,
)

# A gotcha counter maps a code string to how many 5.x footguns it contains.
GotchaCounter = Callable[[str], int]


def _code_events(log: SessionLog) -> list[CodeExecEvent]:
    return [e for e in log.events if isinstance(e, CodeExecEvent)]


def query_before_call_rate(log: SessionLog) -> float:
    """Fraction of code execs preceded by a RAG query *for that step*.

    A query "counts" for the next code exec and is then consumed, so this
    rewards querying before each call rather than one query up front. Returns
    0.0 when there are no code executions.
    """
    execs = 0
    grounded = 0
    query_pending = False
    for ev in log.events:
        if isinstance(ev, RagQueryEvent):
            query_pending = True
        elif isinstance(ev, CodeExecEvent):
            execs += 1
            if query_pending:
                grounded += 1
                query_pending = False
    return grounded / execs if execs else 0.0


def score(log: SessionLog, *, gotcha_counter: GotchaCounter | None = None) -> SessionMetrics:
    """Reduce a session log to its scalar metrics."""
    execs = _code_events(log)
    n_exec = len(execs)
    n_err = sum(1 for e in execs if not e.ok)
    n_query = sum(1 for e in log.events if isinstance(e, RagQueryEvent))

    gotchas = 0
    if gotcha_counter is not None:
        gotchas = sum(gotcha_counter(e.code) for e in execs)

    return SessionMetrics(
        task_id=log.task_id,
        rag_enabled=log.rag_enabled,
        run_index=log.run_index,
        iterations=len(log.events),
        code_executions=n_exec,
        code_errors=n_err,
        error_rate=(n_err / n_exec) if n_exec else 0.0,
        clean_run=(n_exec > 0 and n_err == 0),
        rag_queries=n_query,
        query_before_call_rate=query_before_call_rate(log),
        gotcha_hits=gotchas,
        scene_total=log.final_scene.total if log.final_scene else 0,
        completed=log.completed,
    )
