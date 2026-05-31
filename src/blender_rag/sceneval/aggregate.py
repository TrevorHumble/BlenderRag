"""Aggregate many :class:`SessionMetrics` into per-condition distributions and
RAG-on vs RAG-off deltas — the step that turns N noisy runs into a verdict.

Pure and stdlib-only (``statistics``). Creative + LLM sessions are high-variance,
so a single run proves nothing; this reduces N runs per condition to mean/median/
spread and reports the on-minus-off delta per metric.
"""

from __future__ import annotations

import statistics
from collections import defaultdict

from pydantic import BaseModel

from blender_rag.sceneval.schema import SessionMetrics

# Numeric/bool fields of SessionMetrics we summarize (bool -> 0/1 rate over runs).
METRIC_FIELDS: tuple[str, ...] = (
    "error_rate",
    "clean_run",
    "query_before_call_rate",
    "gotcha_hits",
    "scene_total",
    "completed",
    "code_executions",
    "code_errors",
    "rag_queries",
    "iterations",
)


class MetricSummary(BaseModel):
    n: int
    mean: float
    median: float
    min: float
    max: float
    stdev: float  # population stdev (0.0 for n<2)


class ConditionAggregate(BaseModel):
    task_id: str
    rag_enabled: bool
    n_runs: int
    metrics: dict[str, MetricSummary]


class AblationResult(BaseModel):
    """One task: the RAG-on aggregate, the RAG-off aggregate, and on-off deltas."""

    task_id: str
    rag_on: ConditionAggregate | None = None
    rag_off: ConditionAggregate | None = None
    deltas: dict[str, float] = {}  # rag_on.mean - rag_off.mean (only if both present)


def summarize(values: list[float]) -> MetricSummary:
    if not values:
        return MetricSummary(n=0, mean=0.0, median=0.0, min=0.0, max=0.0, stdev=0.0)
    return MetricSummary(
        n=len(values),
        mean=statistics.fmean(values),
        median=statistics.median(values),
        min=min(values),
        max=max(values),
        stdev=statistics.pstdev(values) if len(values) > 1 else 0.0,
    )


def aggregate_condition(metrics: list[SessionMetrics]) -> ConditionAggregate:
    """Summarize a set of metrics assumed to share task_id + rag_enabled."""
    summaries = {
        field: summarize([float(getattr(m, field)) for m in metrics])
        for field in METRIC_FIELDS
    }
    head = metrics[0] if metrics else None
    return ConditionAggregate(
        task_id=head.task_id if head else "",
        rag_enabled=head.rag_enabled if head else False,
        n_runs=len(metrics),
        metrics=summaries,
    )


def ablation(metrics: list[SessionMetrics]) -> list[AblationResult]:
    """Group metrics by task, split by RAG condition, and compute on-off deltas."""
    by_task: dict[str, dict[bool, list[SessionMetrics]]] = defaultdict(
        lambda: {True: [], False: []}
    )
    for m in metrics:
        by_task[m.task_id][m.rag_enabled].append(m)

    results: list[AblationResult] = []
    for task_id in sorted(by_task):
        on_runs = by_task[task_id][True]
        off_runs = by_task[task_id][False]
        on = aggregate_condition(on_runs) if on_runs else None
        off = aggregate_condition(off_runs) if off_runs else None
        deltas: dict[str, float] = {}
        if on and off:
            deltas = {
                f: on.metrics[f].mean - off.metrics[f].mean for f in METRIC_FIELDS
            }
        results.append(
            AblationResult(task_id=task_id, rag_on=on, rag_off=off, deltas=deltas)
        )
    return results
