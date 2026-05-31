"""Smoke test: the scene-eval CLI runs end-to-end (fake backend) and writes a
report. Guards the script wiring (arg parsing, task loading, run->score->
aggregate->report) that the unit tests don't cover. No model / no Blender."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_cli_fake_backend_writes_report_logs_and_json(tmp_path):
    out = tmp_path / "report.md"
    logs = tmp_path / "logs"
    results_json = tmp_path / "results.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "run_scene_eval.py"),
            "--backend", "fake",
            "--n", "1",
            "--out", str(out),
            "--json", str(results_json),
            "--logs", str(logs),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    report = out.read_text(encoding="utf-8")
    assert "# Scene-eval report" in report
    assert "## Summary" in report
    # logs were dumped, one JSON per session
    assert any(logs.glob("*.json"))
    # machine-readable aggregate is valid JSON with the expected shape
    data = json.loads(results_json.read_text(encoding="utf-8"))
    assert isinstance(data, list) and data
    assert {"task_id", "rag_on", "rag_off", "deltas"} <= set(data[0])
