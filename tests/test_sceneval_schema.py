from blender_rag.sceneval.schema import (
    CodeExecEvent,
    RagQueryEvent,
    SceneSnapshot,
    SessionLog,
    SessionMetrics,
)


def test_scene_snapshot_total():
    snap = SceneSnapshot(objects=3, meshes=2, materials=1, material_nodes=8, lights=1)
    assert snap.total == 15


def test_scene_snapshot_defaults_zero():
    assert SceneSnapshot().total == 0


def test_session_log_roundtrips_discriminated_union():
    log = SessionLog(
        task_id="island",
        rag_enabled=True,
        events=[
            RagQueryEvent(query="add cube", source_type="api", n_hits=3),
            CodeExecEvent(code="bpy.ops.mesh.primitive_cube_add()", ok=True),
            CodeExecEvent(code="bad()", ok=False, error_type="NameError"),
        ],
        final_scene=SceneSnapshot(objects=1),
        completed=True,
    )
    dumped = log.model_dump_json()
    restored = SessionLog.model_validate_json(dumped)
    assert restored == log
    # the union picked the right concrete types back out
    assert isinstance(restored.events[0], RagQueryEvent)
    assert isinstance(restored.events[1], CodeExecEvent)
    assert restored.events[2].error_type == "NameError"


def test_event_type_discriminators_are_fixed():
    assert RagQueryEvent(query="x").type == "rag_query"
    assert CodeExecEvent(code="x", ok=True).type == "code_exec"


def test_session_metrics_defaults():
    m = SessionMetrics(task_id="t", rag_enabled=False)
    assert m.error_rate == 0.0
    assert m.clean_run is False
    assert m.gotcha_hits == 0
