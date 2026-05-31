"""Scene-eval (Layer A): objective, ablation-based end-to-end RAG evaluation.

The existing eval (``scripts/eval.py``) measures *retrieval* — does the right
chunk rank top-k. This package measures the *task*: does the RAG make a model
build a Blender scene with fewer API errors, fewer 5.x footguns, and more
doc-grounded calls? It runs an agent through an iterative build session twice —
RAG-on and RAG-off — and reports the difference.

The measurement core (``schema``, ``metrics``, ``gotchas``, ``aggregate``) is
pure and unit-tested with fakes; model / live-Blender backends are pluggable and
optional, mirroring the ``Contextualizer`` / ``Embedder`` pattern.
"""

from __future__ import annotations

from blender_rag.sceneval.schema import (
    CodeExecEvent,
    RagQueryEvent,
    SceneSnapshot,
    SessionLog,
    SessionMetrics,
)

__all__ = [
    "CodeExecEvent",
    "RagQueryEvent",
    "SceneSnapshot",
    "SessionLog",
    "SessionMetrics",
]
