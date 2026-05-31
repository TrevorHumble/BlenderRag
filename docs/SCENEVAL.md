# Scene-eval (Layer A) — end-to-end RAG ablation harness

`scripts/eval.py` measures **retrieval** (does the right chunk rank top-k).
Scene-eval measures the **task**: does the RAG make a model build a Blender scene
with fewer API errors, fewer 5.x footguns, and more doc-grounded calls? It runs an
agent through an iterative build session **twice — RAG-on and RAG-off** — and
reports the difference. The control is the point; without it, it's a demo.

## Run it

```bash
# plumbing demo — no model, no Blender, deterministic
uv run python scripts/run_scene_eval.py --n 3 --backend fake

# real run — needs ANTHROPIC_API_KEY + Blender open with the BlenderMCP addon
uv run python scripts/run_scene_eval.py --n 5 --backend live --model claude-sonnet-4-5
```

Writes a markdown report to `eval/SCENEVAL.md` (per-task table of RAG-off vs RAG-on
means + on−off delta, with a ✅/⚠️ verdict per metric). `--logs DIR` dumps every
raw `SessionLog` as JSON for re-scoring.

## Metrics (pure, deterministic — `sceneval/metrics.py`)

| metric | better | meaning |
|--------|:------:|---------|
| `error_rate` | ↓ | failed `execute_blender_code` / total |
| `clean_run` | ↑ | ran ≥1 call with zero errors |
| `query_before_call_rate` | ↑ | execs preceded by a RAG query (consumed per step) |
| `gotcha_hits` | ↓ | known 5.x footguns in executed code (`sceneval/gotchas.py`) |
| `scene_total` | ↑ | object+mesh+material+node+light count (crude productivity proxy) |
| `completed`, `iterations`, `rag_queries`, `code_executions`, `code_errors` | — | context |

## Architecture

```
runner.run_session(agent, executor, searcher?, rag_enabled) -> SessionLog
   |                                                              |
   |  three Protocols (SceneAgent / RagSearcher / BlenderExecutor)|
   v                                                              v
fakes.py (CI, deterministic)              backends.py (live, optional, lazy)
                                            - InProcessRagSearcher (real index)
                                            - AnthropicSceneAgent  (Claude tool-use)
                                            - McpBlenderExecutor   (live Blender via MCP)
SessionLog --score--> SessionMetrics --aggregate.ablation--> AblationResult --report--> markdown
```

The **pure core** (`schema`, `metrics`, `gotchas`, `aggregate`) and the **fakes**
have full unit coverage and need no model/Blender — CI runs them. The **live
backends** are imported lazily and only when `--backend live` is chosen.

RAG-on vs RAG-off is simply: pass a `searcher`, or pass `None`. Each live session
starts from an empty scene (`wm.read_homefile(use_empty=True)`); state does not
leak between runs.

## Live requirements

- `ANTHROPIC_API_KEY` set (the agent), and the `anthropic` SDK installed.
- Blender open with the BlenderMCP addon + the bridge (`uvx blender-mcp`) reachable
  (the executor talks to `execute_blender_code` / `get_scene_info`).
- A built index (`scripts/build_all.py`) + the `ml` deps (the in-process searcher).

## Status / next (Layer B)

- Render-quality judging via the `art-critic` skill (a vision rubric on the final
  render) — the subjective dimension this objective layer deliberately omits.
- The live end-to-end path (Claude + Blender) is wired but not yet CI-verifiable;
  the agent message-mapping and the in-process searcher are tested/verified.
