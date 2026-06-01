"""Score a headless Haiku ablation run into the standard SCENEVAL report.

Input: a directory of session pairs, one per build. Each session is a ``.py``
file (the raw bpy script the agent wrote — no escaping) and a sibling ``.json``
metadata file ``{task_id, rag_enabled, run_index, queries, notes}``. Splitting
code from metadata avoids asking a subagent to hand-escape a multi-line script
into JSON. Sessions come from spawning Haiku subagents (the driver) with and
without the ``search_blender_docs`` RAG tool.

Each script is validated *statically* against the real 5.1 API symbol table (see
``static_exec``); the result feeds the same metrics/aggregate/report pipeline the
live ablation uses, so the output is directly comparable. Beyond the standard
report it appends a pooled, operator-level table that *names* the hallucinated
operators per condition — the gold for corpus-gap analysis.

Usage:
  uv run python scripts/score_haiku_ablation.py --runs-dir eval/sessions_haiku
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from blender_rag.config import REPO_ROOT
from blender_rag.sceneval.aggregate import ablation
from blender_rag.sceneval.gotchas import count_gotchas
from blender_rag.sceneval.metrics import score
from blender_rag.sceneval.report import render_report
from blender_rag.sceneval.schema import CodeExecEvent, RagQueryEvent, SessionLog
from blender_rag.sceneval.static_exec import (
    load_symbol_set,
    node_new_types,
    operator_calls,
    validate_code,
)


def load_sessions(runs_dir: Path) -> list[dict]:
    """Read paired ``<stem>.json`` (metadata) + ``<stem>.py`` (code) sessions."""
    sessions: list[dict] = []
    for meta_path in sorted(runs_dir.glob("*.json")):
        code_path = meta_path.with_suffix(".py")
        if not code_path.exists():
            print(f"  WARN: {meta_path.name} has no sibling .py — skipping")
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  WARN: {meta_path.name} is not valid JSON ({e}) — skipping")
            continue
        meta["code"] = code_path.read_text(encoding="utf-8")
        sessions.append(meta)
    return sessions


def _load_hints(tasks_path: Path) -> dict[str, list[str]]:
    hints: dict[str, list[str]] = {}
    for line in tasks_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            t = json.loads(line)
            hints[t["id"]] = t.get("success_hints", [])
    return hints


def _to_log(session: dict, hints: dict[str, list[str]], symbols: frozenset[str]) -> SessionLog:
    """One session dict -> SessionLog (queries + a single validated code event)."""
    events: list[RagQueryEvent | CodeExecEvent] = []
    for q in session.get("queries", []):
        events.append(
            RagQueryEvent(
                query=q.get("query", ""),
                source_type=q.get("source_type"),
                top_k=int(q.get("top_k", 6)),
                n_hits=int(q.get("n_hits", 0)),
            )
        )
    code = session.get("code", "")
    res = validate_code(code, symbols)
    events.append(
        CodeExecEvent(
            code=code, ok=res.ok, error_type=res.error_type, error_message=res.error_message
        )
    )
    return SessionLog(
        task_id=session["task_id"],
        rag_enabled=bool(session["rag_enabled"]),
        run_index=int(session.get("run_index", 0)),
        model=session.get("model", "claude-haiku (headless)"),
        events=events,
        final_scene=None,  # headless: no live scene census
        completed=True,
        success_hints=hints.get(session["task_id"], []),
    )


def _hallucination_table(
    sessions: list[dict], symbols: frozenset[str], *, kind: str
) -> str:
    """Pooled validity stats + the named hallucinations for ``kind`` in {ops, nodes}.

    ops:   ``bpy.ops.<module>.<op>`` checked against the symbol table.
    nodes: ``nodes.new('BlIdName')`` checked against ``bpy.types.<BlIdName>``.
    """
    if kind == "ops":
        title, unit = "Operator validity", "ops"
        extract = operator_calls
        valid = lambda x: x in symbols  # noqa: E731
        named_label = "hallucinated operators"
    else:
        title, unit = "Node-type validity (nodes.new bl_idname)", "node calls"
        extract = node_new_types
        valid = lambda x: f"bpy.types.{x}" in symbols  # noqa: E731
        named_label = "hallucinated node types"

    lines = ["", f"## {title} (pooled, headless static check)", ""]
    lines.append(f"| condition | scripts | total {unit} | invalid | invalid rate |")
    lines.append("|---|--:|--:|--:|--:|")
    halluc: dict[bool, Counter] = {True: Counter(), False: Counter()}
    for cond in (False, True):
        subset = [s for s in sessions if bool(s["rag_enabled"]) is cond]
        total = invalid = 0
        for s in subset:
            try:
                items = extract(s.get("code", ""))
            except SyntaxError:
                continue
            total += len(items)
            for it in items:
                if not valid(it):
                    invalid += 1
                    halluc[cond][it] += 1
        rate = f"{invalid / total:.0%}" if total else "—"
        label = "RAG-on" if cond else "RAG-off"
        lines.append(f"| {label} | {len(subset)} | {total} | {invalid} | {rate} |")
    for cond, label in ((False, "RAG-off"), (True, "RAG-on")):
        if halluc[cond]:
            named = ", ".join(f"`{x}`×{n}" for x, n in halluc[cond].most_common())
            lines.append("")
            lines.append(f"**{label} {named_label}:** {named}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Score a headless Haiku ablation run")
    ap.add_argument("--runs-dir", type=Path, default=REPO_ROOT / "eval" / "sessions_haiku")
    ap.add_argument("--tasks", type=Path, default=REPO_ROOT / "eval" / "scenes" / "tasks.jsonl")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "eval" / "SCENEVAL_haiku.md")
    ap.add_argument("--json", type=Path, default=None, help="machine-readable AblationResult JSON")
    args = ap.parse_args()

    sessions = load_sessions(args.runs_dir)
    hints = _load_hints(args.tasks)
    symbols = load_symbol_set()

    logs = [_to_log(s, hints, symbols) for s in sessions]
    metrics = [score(lg, gotcha_counter=count_gotchas) for lg in logs]
    results = ablation(metrics)

    n_on = sum(1 for s in sessions if s["rag_enabled"])
    n_off = len(sessions) - n_on
    report = render_report(
        results,
        backend_label="haiku-static (headless)",
        n_note=(
            f"{len({s['task_id'] for s in sessions})} tasks; {n_on} RAG-on + {n_off} RAG-off "
            "sessions. Driver: Claude Haiku subagents. Executor: static 5.1-API validation "
            "(syntax + operator + node-type existence) — a lower bound on real breakage "
            "(blind to wrong args / socket names); not live Blender."
        ),
    )
    report += _hallucination_table(sessions, symbols, kind="ops")
    report += _hallucination_table(sessions, symbols, kind="nodes")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"wrote {args.out}  ({len(logs)} sessions)")

    if args.json:
        args.json.write_text(
            json.dumps([r.model_dump() for r in results], indent=2), encoding="utf-8"
        )
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
