"""Smoke test: the scene-eval CLI runs end-to-end (fake backend) and writes a
report. Guards the script wiring (arg parsing, task loading, run->score->
aggregate->report) that the unit tests don't cover. No model / no Blender."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_cli_fake_backend_writes_report(tmp_path):
    out = tmp_path / "report.md"
    logs = tmp_path / "logs"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "run_scene_eval.py"),
            "--backend", "fake",
            "--n", "1",
            "--out", str(out),
            "--logs", str(logs),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    report = out.read_text(encoding="utf-8")
    assert "# Scene-eval report" in report
    assert "## Summary" in report
    # logs were dumped, one JSON per session
    assert any(logs.glob("*.json"))
