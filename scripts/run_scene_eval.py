"""Run the scene-eval ablation harness (Layer A) and write a markdown report.

Each task runs N sessions RAG-on and N RAG-off; results are scored, aggregated,
and rendered to a report. The default ``fake`` backend needs no model or Blender
(plumbing demo). The ``live`` backend (a real model + live Blender MCP) is added
in a later PR.

Usage:
  uv run python scripts/run_scene_eval.py --n 3 --backend fake
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from blender_rag.config import REPO_ROOT
from blender_rag.sceneval.aggregate import ablation
from blender_rag.sceneval.demo import demo_session
from blender_rag.sceneval.gotchas import count_gotchas
from blender_rag.sceneval.metrics import score
from blender_rag.sceneval.report import render_report
from blender_rag.sceneval.runner import run_session
from blender_rag.sceneval.schema import SessionLog

_RESET_CODE = "import bpy\nbpy.ops.wm.read_homefile(use_empty=True)"


def load_tasks(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def run_fake(tasks: list[dict], n: int) -> list[SessionLog]:
    logs: list[SessionLog] = []
    for task in tasks:
        for rag_enabled in (True, False):
            for run_index in range(n):
                logs.append(
                    demo_session(
                        task["id"],
                        rag_enabled=rag_enabled,
                        run_index=run_index,
                        success_hints=task.get("success_hints", []),
                    )
                )
    return logs


def run_live(tasks: list[dict], n: int, *, model: str, max_iter: int) -> list[SessionLog]:
    # Heavy + optional deps imported only on the live path.
    from blender_rag.sceneval.backends import (
        AnthropicSceneAgent,
        InProcessRagSearcher,
        McpBlenderExecutor,
    )

    searcher = InProcessRagSearcher()  # the real RAG, loaded once
    executor = McpBlenderExecutor()  # one persistent live-Blender session
    logs: list[SessionLog] = []
    for task in tasks:
        for rag_enabled in (True, False):
            for run_index in range(n):
                executor.execute(_RESET_CODE)  # fresh scene per session (not logged)
                agent = AnthropicSceneAgent(task["prompt"], model=model)
                logs.append(
                    run_session(
                        task_id=task["id"],
                        agent=agent,
                        executor=executor,
                        searcher=searcher if rag_enabled else None,
                        rag_enabled=rag_enabled,
                        run_index=run_index,
                        model=model,
                        max_iterations=max_iter,
                        success_hints=task.get("success_hints", []),
                    )
                )
    return logs


def main() -> None:
    ap = argparse.ArgumentParser(description="Scene-eval ablation harness (Layer A)")
    ap.add_argument("--tasks", type=Path, default=REPO_ROOT / "eval" / "scenes" / "tasks.jsonl")
    ap.add_argument("--n", type=int, default=3, help="runs per condition per task")
    ap.add_argument("--backend", choices=["fake", "live"], default="fake")
    ap.add_argument("--model", default="claude-sonnet-4-5", help="live backend model")
    ap.add_argument("--max-iter", type=int, default=40, help="max agent steps per session")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "eval" / "SCENEVAL.md")
    ap.add_argument("--logs", type=Path, default=None, help="optional dir for raw session logs")
    args = ap.parse_args()

    tasks = load_tasks(args.tasks)
    if args.backend == "live":
        logs = run_live(tasks, args.n, model=args.model, max_iter=args.max_iter)
    else:
        logs = run_fake(tasks, args.n)
    all_metrics = [score(lg, gotcha_counter=count_gotchas) for lg in logs]

    results = ablation(all_metrics)
    report = render_report(
        results,
        backend_label=args.backend,
        n_note=f"{len(tasks)} tasks x {args.n} runs/condition.",
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"wrote {args.out}  ({len(all_metrics)} sessions over {len(tasks)} tasks)")

    if args.logs:
        args.logs.mkdir(parents=True, exist_ok=True)
        for lg in logs:
            fn = args.logs / f"{lg.task_id}_{'on' if lg.rag_enabled else 'off'}_{lg.run_index}.json"
            fn.write_text(lg.model_dump_json(indent=2), encoding="utf-8")
        print(f"wrote {len(logs)} session logs -> {args.logs}")


if __name__ == "__main__":
    main()
