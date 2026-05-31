from blender_rag.sceneval.aggregate import ablation
from blender_rag.sceneval.demo import demo_session
from blender_rag.sceneval.gotchas import count_gotchas
from blender_rag.sceneval.metrics import score
from blender_rag.sceneval.report import render_report


def _results(n=3):
    metrics = []
    for rag in (True, False):
        for i in range(n):
            log = demo_session("island", rag_enabled=rag, run_index=i)
            metrics.append(score(log, gotcha_counter=count_gotchas))
    return ablation(metrics)


def test_report_has_task_section_and_table():
    md = render_report(_results(), backend_label="fake", n_note="1 task x 3 runs.")
    assert "# Scene-eval report" in md
    assert "## island" in md
    assert "| metric | RAG-off | RAG-on | Δ (on−off) | |" in md
    assert "error_rate" in md and "gotcha_hits" in md


def test_fake_backend_is_marked_synthetic():
    md = render_report(_results(), backend_label="fake")
    assert "Synthetic backend" in md


def test_report_shows_rag_improvement_verdicts():
    md = render_report(_results(), backend_label="fake")
    # demo is rigged so RAG-on dodges gotchas and errors -> improvement marks present
    assert "✅" in md
    assert "RAG effect:" in md


def test_report_has_cross_task_summary_and_verdict():
    md = render_report(_results(), backend_label="fake")
    assert "## Summary" in md
    assert "RAG helped on" in md
    assert "| task | Δ error_rate" in md
    # the rigged demo helps -> a tick in the summary
    assert "✅" in md


def test_single_condition_renders_no_delta():
    metrics = [score(demo_session("solo", rag_enabled=True, run_index=0))]
    md = render_report(ablation(metrics), backend_label="fake")
    assert "Only one condition present" in md
