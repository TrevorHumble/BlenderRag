"""Data contracts for the scene-eval harness.

A :class:`SessionLog` is the full record of one agentic Blender build session:
an ordered list of events (the agent's RAG queries and code executions), a final
scene snapshot, and a completion flag. Every metric is a pure function over this
log, so the measurement layer is testable without a model or a live Blender.

Events are a discriminated union on the ``type`` field so a log round-trips
through JSON losslessly (sessions are persisted for later re-scoring).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# Event-type discriminator values (module constants so callers don't hardcode).
RAG_QUERY = "rag_query"
CODE_EXEC = "code_exec"


class RagQueryEvent(BaseModel):
    """The agent searched the knowledge base."""

    type: Literal["rag_query"] = RAG_QUERY
    query: str
    source_type: str | None = None
    top_k: int = 6
    n_hits: int = 0


class CodeExecEvent(BaseModel):
    """The agent ran ``execute_blender_code`` (real or simulated)."""

    type: Literal["code_exec"] = CODE_EXEC
    code: str
    ok: bool
    error_type: str | None = None  # e.g. "AttributeError", "RuntimeError"
    error_message: str | None = None


# Discriminated union: pydantic picks the model from the ``type`` field.
SessionEvent = Annotated[
    RagQueryEvent | CodeExecEvent, Field(discriminator="type")
]


class SceneSnapshot(BaseModel):
    """Coarse final-scene census — a crude productivity proxy.

    Counts only; deliberately cheap to gather from a live Blender (``bpy.data``)
    or to fake in tests. Not a quality measure — quality judging is Layer B.
    """

    objects: int = 0
    meshes: int = 0
    materials: int = 0
    material_nodes: int = 0
    lights: int = 0

    @property
    def total(self) -> int:
        """Single scalar 'how much got built' proxy."""
        return self.objects + self.meshes + self.materials + self.material_nodes + self.lights


class SessionLog(BaseModel):
    """The record of one build session under one condition (rag on/off)."""

    task_id: str
    rag_enabled: bool
    run_index: int = 0
    model: str = ""
    events: list[SessionEvent] = Field(default_factory=list)
    final_scene: SceneSnapshot | None = None
    completed: bool = False
    # Optional free-form notes (e.g. why the session stopped).
    note: str = ""


class SessionMetrics(BaseModel):
    """Scored result of one :class:`SessionLog` (output of ``metrics.score``)."""

    task_id: str
    rag_enabled: bool
    run_index: int = 0
    iterations: int = 0  # total agent steps (events)
    code_executions: int = 0
    code_errors: int = 0
    error_rate: float = 0.0  # code_errors / code_executions (0 if none)
    clean_run: bool = False  # no code errors
    rag_queries: int = 0
    query_before_call_rate: float = 0.0  # execs preceded by a query this step
    gotcha_hits: int = 0  # known 5.x footguns in executed code
    scene_total: int = 0  # SceneSnapshot.total (0 if no snapshot)
    completed: bool = False
