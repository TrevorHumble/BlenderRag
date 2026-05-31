"""Render :class:`AblationResult` list into a readable markdown report.

Each metric is annotated with its "good" direction so the delta column reads as
a verdict (did the RAG move it the right way?) rather than a raw number.
"""

from __future__ import annotations

from blender_rag.sceneval.aggregate import METRIC_FIELDS, AblationResult

# Which way is "better" for each metric. neutral = context, no verdict mark.
DIRECTION: dict[str, str] = {
    "error_rate": "down",
    "clean_run": "up",
    "query_before_call_rate": "up",
    "gotcha_hits": "down",
    "scene_total": "up",
    "completed": "up",
    "code_executions": "neutral",
    "code_errors": "down",
    "rag_queries": "neutral",
    "iterations": "neutral",
}


def _verdict(metric: str, delta: float) -> str:
    direction = DIRECTION.get(metric, "neutral")
    if direction == "neutral" or abs(delta) < 1e-9:
        return "·"
    improved = (delta < 0) if direction == "down" else (delta > 0)
    return "✅" if improved else "⚠️"


def _fmt(x: float) -> str:
    return f"{x:+.3f}" if x else "0"


def render_report(
    results: list[AblationResult], *, backend_label: str = "", n_note: str = ""
) -> str:
    lines: list[str] = ["# Scene-eval report (Layer A)", ""]
    if backend_label:
        lines.append(f"Backend: **{backend_label}**. {n_note}".rstrip())
    if backend_label.lower().startswith("fake"):
        lines += [
            "",
            "> ⚠️ **Synthetic backend** — this exercises the harness plumbing, "
            "not a real measurement. Real numbers require the live backend.",
        ]
    lines.append("")

    for res in results:
        on = res.rag_on
        off = res.rag_off
        n_on = on.n_runs if on else 0
        n_off = off.n_runs if off else 0
        lines.append(f"## {res.task_id}  (RAG-on n={n_on}, RAG-off n={n_off})")
        lines.append("")
        if not (on and off):
            lines.append("_Only one condition present — no delta._")
            lines.append("")
            continue
        lines.append("| metric | RAG-off | RAG-on | Δ (on−off) | |")
        lines.append("|--------|--------:|-------:|-----------:|:--:|")
        for f in METRIC_FIELDS:
            off_mean = off.metrics[f].mean
            on_mean = on.metrics[f].mean
            delta = res.deltas.get(f, 0.0)
            lines.append(
                f"| {f} | {off_mean:.3f} | {on_mean:.3f} | {_fmt(delta)} | {_verdict(f, delta)} |"
            )
        lines.append("")
        lines.append(_headline(res))
        lines.append("")
    return "\n".join(lines)


def _headline(res: AblationResult) -> str:
    d = res.deltas
    bits: list[str] = []
    if d.get("error_rate", 0) < 0:
        bits.append(f"error rate {d['error_rate']:+.2f}")
    if d.get("gotcha_hits", 0) < 0:
        bits.append(f"gotchas {d['gotcha_hits']:+.2f}")
    if d.get("query_before_call_rate", 0) > 0:
        bits.append(f"grounding {d['query_before_call_rate']:+.2f}")
    if not bits:
        return "_RAG showed no clear benefit on this task._"
    return "**RAG effect:** " + ", ".join(bits) + " (negative error/gotchas = better)."
