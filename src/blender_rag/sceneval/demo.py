"""Synthetic session generator for the fake backend.

Produces plausible RAG-on / RAG-off :class:`SessionLog`s without any model or
Blender, so ``scripts/run_scene_eval.py`` runs end-to-end and the report shape
can be inspected. This is **plumbing, not measurement** — the RAG-on advantage
here is hard-coded by construction. Real numbers come from the live backend.

A little per-run variation keeps the aggregated distributions non-degenerate.
"""

from __future__ import annotations

from blender_rag.sceneval.fakes import FakeExecutor, FakeSearcher, ScriptedAgent
from blender_rag.sceneval.runner import AgentAction, run_session
from blender_rag.sceneval.schema import SceneSnapshot, SessionLog

_CLEAN = "scene.render.engine = 'BLENDER_EEVEE'"
_FOOTGUN_A = "scene.render.engine = 'BLENDER_EEVEE_NEXT'"
_FOOTGUN_B = "node.sky_type = 'NISHITA'"


def demo_session(task_id: str, *, rag_enabled: bool, run_index: int = 0) -> SessionLog:
    if rag_enabled:
        actions = [
            AgentAction(kind="query", query=f"{task_id} engine setup", source_type="api"),
            AgentAction(kind="exec", code=_CLEAN),
            AgentAction(kind="query", query=f"{task_id} materials", source_type="manual"),
            AgentAction(kind="exec", code="# clean material setup"),
        ]
        executor = FakeExecutor(
            snapshot=SceneSnapshot(objects=4, meshes=4, materials=3, material_nodes=12, lights=2)
        )
        return run_session(
            task_id=task_id, agent=ScriptedAgent(actions), executor=executor,
            searcher=FakeSearcher(3), rag_enabled=True, run_index=run_index, model="fake",
        )

    # RAG-off: reaches for 4.x footguns; an extra failure on odd runs (variation).
    actions = [
        AgentAction(kind="exec", code=_FOOTGUN_A),
        AgentAction(kind="exec", code=_FOOTGUN_B),
        AgentAction(kind="exec", code="BAD_CALL deprecated op"),
    ]
    if run_index % 2 == 1:
        actions.append(AgentAction(kind="exec", code="BAD_CALL again"))
    executor = FakeExecutor(
        fail_markers=["BAD_CALL"],
        error_type="AttributeError",
        snapshot=SceneSnapshot(objects=2, meshes=2, materials=1, material_nodes=3, lights=1),
    )
    return run_session(
        task_id=task_id, agent=ScriptedAgent(actions), executor=executor,
        searcher=None, rag_enabled=False, run_index=run_index, model="fake",
    )
