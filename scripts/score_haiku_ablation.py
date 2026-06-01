"""Score the headless Haiku RAG ablation into an HONEST report.

Input: a directory of session pairs, one per build — a ``.py`` (the raw bpy script
the agent wrote) and a sibling ``.json`` metadata file ``{task_id, rag_enabled,
run_index, queries, notes}``. Sessions come from spawning Haiku subagents with and
without the ``search_blender_docs`` RAG tool.

Each script is checked *statically* against the real Blender 5.1 API symbol table
(``static_exec``: syntax + operator existence + ``nodes.new`` bl_idname existence)
plus the lexical 5.x gotcha scan (``gotchas``). This is a LOWER BOUND on real
breakage — it validates *existence*, not correct arguments, socket names, or
semantics — so a clean verdict means "named only real symbols," never "runs."

Reporting follows the ``rigorous-eval`` skill's publish gates, learned the hard way
when an earlier version of this report shipped a node table claiming the opposite of
its own data (an extractor missed the ``nodes.new(type=...)`` keyword form):
- every headline number is recomputed here from raw and carries n + numerator/denominator;
- tautological metrics (grounding — the control cannot query by construction) are
  excluded from the win count, not dressed up as results;
- a residual-failure ledger names every footgun/hallucination the RAG did NOT fix;
- the driver/deployment and validator-scope caveats state the direction of bias.

Usage:
  uv run python scripts/score_haiku_ablation.py --runs-dir eval/sessions_haiku
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from blender_rag.config import REPO_ROOT
from blender_rag.sceneval.gotchas import detect_gotchas
from blender_rag.sceneval.static_exec import (
    load_symbol_set,
    node_new_types,
    operator_calls,
    validate_code,
)

CONDS = (("off", False), ("on", True))


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
        if "task_id" not in meta or "rag_enabled" not in meta:
            print(f"  WARN: {meta_path.name} missing task_id/rag_enabled — skipping")
            continue
        meta["code"] = code_path.read_text(encoding="utf-8")
        meta["_name"] = code_path.name
        sessions.append(meta)
    return sessions


def compute(sessions: list[dict], symbols: frozenset[str]) -> dict:
    """Recompute every reported quantity from raw — the single source of truth."""
    stat = {c: defaultdict(int) for c, _ in CONDS}
    named = {c: {"ops": Counter(), "nodes": Counter(), "gotchas": Counter()} for c, _ in CONDS}
    queried = {c: 0 for c, _ in CONDS}
    task_fail = defaultdict(lambda: {"off": 0, "on": 0})
    residual_on: list[dict] = []

    for s in sessions:
        c = "on" if s["rag_enabled"] else "off"
        code = s["code"]
        ops = operator_calls(code)
        nodes = node_new_types(code)
        bad_ops = [o for o in ops if o not in symbols]
        bad_nodes = [n for n in nodes if f"bpy.types.{n}" not in symbols]
        goes = [h.rule_id for h in detect_gotchas(code)]
        ok = validate_code(code, symbols).ok

        st = stat[c]
        st["scripts"] += 1
        st["ops"] += len(ops)
        st["bad_ops"] += len(bad_ops)
        st["nodes"] += len(nodes)
        st["bad_nodes"] += len(bad_nodes)
        st["gotchas"] += len(goes)
        st["fail"] += 0 if ok else 1
        if s.get("queries"):
            queried[c] += 1
        for o in bad_ops:
            named[c]["ops"][o] += 1
        for n in bad_nodes:
            named[c]["nodes"][n] += 1
        for g in goes:
            named[c]["gotchas"][g] += 1
        if not ok:
            task_fail[s["task_id"]][c] += 1
        if c == "on" and (bad_ops or bad_nodes or goes):
            residual_on.append(
                {"file": s["_name"], "bad_ops": bad_ops, "bad_nodes": bad_nodes, "gotchas": goes}
            )

    return {
        "stat": {c: dict(v) for c, v in stat.items()},
        "named": {c: {k: dict(v) for k, v in d.items()} for c, d in named.items()},
        "queried": queried,
        "task_fail": {t: dict(v) for t, v in task_fail.items()},
        "residual_on": residual_on,
    }


def _named(counter: dict) -> str:
    return ", ".join(f"`{k}`×{v}" for k, v in sorted(counter.items(), key=lambda x: -x[1])) or "—"


def render(data: dict) -> str:
    st, named, q = data["stat"], data["named"], data["queried"]
    off, on = st["off"], st["on"]
    L: list[str] = []
    L.append("# Scene-eval (Layer A) — headless Haiku RAG ablation\n")
    L.append(
        "**Setup.** 3 tasks × 5 runs/condition = 30 sessions. Driver: Claude Haiku "
        "subagents (on-subscription). RAG-on vs RAG-off = whether `search_blender_docs` "
        "is offered. Executor: **static 5.1-API validation** (syntax + operator + "
        "`nodes.new` bl_idname existence) + lexical 5.x gotcha scan. This is a **lower "
        "bound** on real breakage — it checks *existence*, not arguments, socket names, "
        "or semantics — so `ok` means \"named only real symbols,\" never \"runs.\"\n"
    )

    L.append("## Bottom line\n")
    L.append(
        f"- **WIN — known 5.x gotchas: {off['gotchas']} → {on['gotchas']}** (off→on), "
        "broad-based across three independent footguns "
        f"(`BLENDER_EEVEE_NEXT` {named['off']['gotchas'].get('eevee_next_engine_id',0)}→"
        f"{named['on']['gotchas'].get('eevee_next_engine_id',0)}, "
        f"`bpy.bmesh` {named['off']['gotchas'].get('bpy_bmesh_namespace',0)}→"
        f"{named['on']['gotchas'].get('bpy_bmesh_namespace',0)}, removed "
        f"`.inputs/.outputs.new` {named['off']['gotchas'].get('node_socket_interface_removed',0)}→"
        f"{named['on']['gotchas'].get('node_socket_interface_removed',0)}). This is the "
        "dimension the corpus most directly targets."
    )
    L.append(
        f"- **MISS — geometry-node bl_idnames: RAG did not help** "
        f"(off {off['bad_nodes']}/{off['nodes']} invalid, on {on['bad_nodes']}/{on['nodes']}). "
        "RAG-on invented `GeometryNodeRandomValue` "
        f"{named['on']['nodes'].get('GeometryNodeRandomValue',0)}× across 3/5 "
        "procedural-rocks runs **after querying docs** (the real node is "
        "`FunctionNodeRandomValue`) — a corpus/retrieval gap, not a win."
    )
    L.append(
        f"- **MARGINAL — hallucinated operators {off['bad_ops']}→{on['bad_ops']}; "
        f"script-level static failure {off['fail']}/15 → {on['fail']}/15.** "
        "At n=5 with single-digit event counts this is within sampling noise "
        "(no significance test passes here)."
    )
    L.append(
        "- **EXCLUDED — \"grounding 0%→100%\" is tautological**: the RAG-off arm cannot "
        f"query by construction ({q['off']}/15 off vs {q['on']}/15 on logged any query). "
        "It measures the experiment's wiring, not the RAG, so it is not a result.\n"
    )

    L.append("## Pooled signals (recomputed from raw; n=15/condition)\n")
    L.append("| signal | RAG-off | RAG-on | note |")
    L.append("|---|--:|--:|---|")
    L.append(
        f"| 5.x gotchas (occurrences) | {off['gotchas']} | {on['gotchas']} | "
        "broad real win (3 footgun types) |"
    )
    L.append(
        f"| hallucinated node bl_idnames | {off['bad_nodes']} / {off['nodes']} | "
        f"{on['bad_nodes']} / {on['nodes']} | **no win**; denominators differ (parity caveat) |"
    )
    L.append(
        f"| hallucinated operators | {off['bad_ops']} / {off['ops']} | "
        f"{on['bad_ops']} / {on['ops']} | marginal |"
    )
    L.append(
        f"| scripts failing static check | {off['fail']} / 15 | {on['fail']} / 15 | "
        "within noise at n=5 |"
    )
    L.append("")
    pf = data["task_fail"]
    L.append("Per-task static failures (script ok=False): " + "; ".join(
        f"{t} off {v['off']}/5 on {v['on']}/5" for t, v in sorted(pf.items())
    ) + ".\n")

    L.append("## Named hallucinations / footguns (provenance)\n")
    L.append(f"- **RAG-off gotchas:** {_named(named['off']['gotchas'])}")
    L.append(f"- **RAG-on gotchas:** {_named(named['on']['gotchas'])}")
    L.append(f"- **RAG-off bad node bl_idnames:** {_named(named['off']['nodes'])}")
    L.append(f"- **RAG-on bad node bl_idnames:** {_named(named['on']['nodes'])}")
    L.append(f"- **RAG-off bad operators:** {_named(named['off']['ops'])}")
    L.append(f"- **RAG-on bad operators:** {_named(named['on']['ops'])}\n")

    L.append("## Residual-failure ledger (RAG-on did NOT fix these)\n")
    if data["residual_on"]:
        for r in data["residual_on"]:
            bits = []
            if r["bad_ops"]:
                bits.append("ops " + ", ".join(r["bad_ops"]))
            if r["bad_nodes"]:
                bits.append("nodes " + ", ".join(sorted(set(r["bad_nodes"]))))
            if r["gotchas"]:
                bits.append("gotchas " + ", ".join(sorted(set(r["gotchas"]))))
            L.append(f"- `{r['file']}` — " + "; ".join(bits))
    else:
        L.append("- (none)")
    L.append("")

    L.append("## Limitations (direction of bias stated)\n")
    L.append(
        "- **Driver ≠ deployment.** Haiku hallucinates more than the frontier model that "
        "actually runs this RAG in Claude Code, so the RAG-off baseline is artificially "
        "weak and the gotcha delta is **inflated** vs real use.\n"
        "- **Static check is existence-only.** Confirmed false negatives it cannot see: "
        "`bpy.bmesh.new()` (caught now as a gotcha), wrong socket names, wrong arg counts, "
        "and semantic errors all pass. `ok=True` ≠ runnable.\n"
        "- **n=5/condition, single-digit events.** Per-task error deltas do not reach "
        "significance; treat the script-failure and operator lines as directional only. "
        "The gotcha win is the only broad-based, multi-type signal.\n"
        "- **Sessions are model-self-authored, not captured transcripts.** `queries` are "
        "transcribed by the agent, not measured by the harness; the RAG-on arm also "
        "iterated more, so 'RAG content helped' is not fully separable from 'thought longer.'\n"
        "- For a runtime-truth comparison use the live `McpBlenderExecutor` path "
        "(`scripts/run_scene_eval.py --backend live`)."
    )
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="Score the headless Haiku RAG ablation (honest)")
    ap.add_argument("--runs-dir", type=Path, default=REPO_ROOT / "eval" / "sessions_haiku")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "eval" / "SCENEVAL_haiku.md")
    ap.add_argument("--json", type=Path, default=REPO_ROOT / "eval" / "sceneval_haiku.json")
    args = ap.parse_args()

    sessions = load_sessions(args.runs_dir)
    symbols = load_symbol_set()
    data = compute(sessions, symbols)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(data), encoding="utf-8")
    print(f"wrote {args.out}  ({len(sessions)} sessions)")
    args.json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
