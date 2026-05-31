from blender_rag.sceneval.aggregate import (
    ablation,
    aggregate_condition,
    summarize,
)
from blender_rag.sceneval.schema import SessionMetrics


def _m(task, rag, **kw):
    return SessionMetrics(task_id=task, rag_enabled=rag, **kw)


def test_summarize_basic():
    s = summarize([1.0, 2.0, 3.0])
    assert s.n == 3
    assert s.mean == 2.0
    assert s.median == 2.0
    assert s.min == 1.0 and s.max == 3.0
    assert s.stdev > 0


def test_summarize_empty_is_zero():
    s = summarize([])
    assert s.n == 0 and s.mean == 0.0 and s.stdev == 0.0


def test_summarize_single_value_zero_stdev():
    assert summarize([5.0]).stdev == 0.0


def test_aggregate_condition_counts_runs():
    agg = aggregate_condition([
        _m("island", True, error_rate=0.0, gotcha_hits=0),
        _m("island", True, error_rate=0.5, gotcha_hits=2),
    ])
    assert agg.n_runs == 2
    assert agg.rag_enabled is True
    assert agg.metrics["error_rate"].mean == 0.25
    assert agg.metrics["gotcha_hits"].mean == 1.0


def test_bool_fields_become_rates():
    agg = aggregate_condition([
        _m("t", True, clean_run=True, completed=True),
        _m("t", True, clean_run=False, completed=True),
    ])
    assert agg.metrics["clean_run"].mean == 0.5  # 1 of 2 clean
    assert agg.metrics["completed"].mean == 1.0


def test_ablation_computes_on_minus_off_delta():
    metrics = [
        # RAG on: low error, dodges gotchas
        _m("island", True, error_rate=0.1, gotcha_hits=0),
        _m("island", True, error_rate=0.1, gotcha_hits=0),
        # RAG off: higher error, more gotchas
        _m("island", False, error_rate=0.5, gotcha_hits=3),
        _m("island", False, error_rate=0.5, gotcha_hits=1),
    ]
    [res] = ablation(metrics)
    assert res.task_id == "island"
    assert res.rag_on.n_runs == 2 and res.rag_off.n_runs == 2
    assert abs(res.deltas["error_rate"] - (0.1 - 0.5)) < 1e-9  # RAG lowers error
    assert res.deltas["gotcha_hits"] == (0.0 - 2.0)  # RAG dodges gotchas


def test_ablation_no_delta_when_condition_missing():
    [res] = ablation([_m("solo", True, error_rate=0.2)])
    assert res.rag_on is not None
    assert res.rag_off is None
    assert res.deltas == {}


def test_ablation_groups_and_sorts_by_task():
    res = ablation([_m("b", True), _m("a", False)])
    assert [r.task_id for r in res] == ["a", "b"]
