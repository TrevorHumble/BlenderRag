"""Render a :class:`SessionLog` as a human-readable transcript.

The JSON logs (``--logs``) are for machines; this is for eyes — when a live
ablation run does something surprising, you want to read what the agent searched,
what it ran, where it errored, and which 5.x footguns slipped through, in order.
Pure (``render_transcript``); ``scripts/show_session.py`` is the thin CLI.
"""

from __future__ import annotations

from blender_rag.sceneval.gotchas import count_gotchas, detect_gotchas
from blender_rag.sceneval.metrics import score
from blender_rag.sceneval.schema import CodeExecEvent, RagQueryEvent, SessionLog


def _indent(text: str, prefix: str = "      ") -> str:
    return "\n".join(prefix + ln for ln in text.splitlines())


def render_transcript(log: SessionLog, *, code_lines: int = 6) -> str:
    cond = "RAG-on" if log.rag_enabled else "RAG-off"
    out: list[str] = [
        f"=== {log.task_id}  [{cond}]  run {log.run_index}"
        f"{('  model=' + log.model) if log.model else ''} ===",
    ]
    if log.success_hints:
        out.append(f"brief concepts: {', '.join(log.success_hints)}")
    out.append("")

    # ASCII-only markers: this prints to a terminal (Windows consoles are cp1252).
    for i, ev in enumerate(log.events, 1):
        if isinstance(ev, RagQueryEvent):
            st = f" [{ev.source_type}]" if ev.source_type else ""
            out.append(f"{i:>3}. SEARCH{st}: {ev.query}  -> {ev.n_hits} hits")
        elif isinstance(ev, CodeExecEvent):
            mark = "OK" if ev.ok else f"ERR {ev.error_type}"
            out.append(f"{i:>3}. EXEC [{mark}]")
            snippet = "\n".join(ev.code.splitlines()[:code_lines])
            if snippet.strip():
                out.append(_indent(snippet))
            if not ev.ok and ev.error_message:
                out.append(_indent(f"! {ev.error_message}", "      "))
            for hit in detect_gotchas(ev.code):
                out.append(_indent(f"GOTCHA[{hit.severity}] {hit.rule_id}: {hit.fix}"))

    m = score(log, gotcha_counter=count_gotchas)
    out += [
        "",
        f"summary: {m.code_executions} execs, {m.code_errors} errors "
        f"(rate {m.error_rate:.2f}), {m.rag_queries} queries, "
        f"grounding {m.query_before_call_rate:.2f}, gotchas {m.gotcha_hits}, "
        f"task-signal {m.task_signal_rate:.2f}, "
        f"completed={m.completed}",
    ]
    return "\n".join(out)
