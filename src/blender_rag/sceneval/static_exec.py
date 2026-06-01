"""Headless, no-Blender validation of generated bpy code (Layer A, parallel arm).

The live ``McpBlenderExecutor`` runs code in Blender and reports real runtime
errors, but a single Blender instance can't be shared across parallel sessions.
This module is the parallel-friendly complement: it validates a generated script
*statically* against the real Blender 5.1 API symbol table (pulled from the
index), so many agent sessions can be scored at once with no Blender, no GPU, and
no cloud key.

**Scope — precision over recall, by design.** It checks three things, all sound:

1. **Syntax** — does the script ``compile()``?
2. **Operator validity** — does every ``bpy.ops.<module>.<op>(...)`` call name an
   operator that actually exists in 5.1? Operators are fully qualified in source
   and are the #1 hallucination surface (models invent or use removed/renamed
   operators), so this is a high-signal, false-positive-free check.
3. **Node-type validity** — does every ``...nodes.new('BlIdName')`` pass a node
   ``bl_idname`` that exists as a ``bpy.types`` class in 5.1? A wrong bl_idname
   (e.g. ``GeometryNodeRandomValue`` for the real ``FunctionNodeRandomValue``)
   raises at runtime, and node-graph work is exactly where 4.x-trained models
   guess wrong, so this is the geometry/shader-node analogue of operator validity.

It deliberately does **not** validate attribute access on runtime variables
(``mod.levels``) or ``bpy.data.*`` collections — those aren't fully qualified in
the symbol table, so flagging them would false-positive on valid code. So a
clean verdict here means "syntactically valid, no hallucinated operators or node
types," **not** "guaranteed to run" — wrong *arguments* or wrong socket *names*
on a real operator/node still pass. Treat the resulting error rate as a lower
bound on real breakage. The live executor remains the ground truth; this is the
cheap, parallel proxy for the hallucination dimension the RAG most directly targets.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from blender_rag.sceneval.runner import CodeResult

_CACHE = Path(__file__).resolve().parents[3] / "eval" / "api_symbols_5_1.json"


def load_symbol_set(
    *, index_path: str | None = None, cache_path: Path | None = None, refresh: bool = False
) -> frozenset[str]:
    """Return the set of valid 5.1 API symbols (e.g. ``bpy.ops.mesh.primitive_cube_add``).

    Reads the ``symbol`` column of every ``api`` row in the index. Cached to JSON
    so repeat runs don't reopen LanceDB; pass ``refresh=True`` to rebuild.
    """
    cache = cache_path or _CACHE
    if cache.exists() and not refresh:
        return frozenset(json.loads(cache.read_text(encoding="utf-8")))

    import lancedb

    from blender_rag.config import load_config
    from blender_rag.index import DOCS_TABLE

    cfg = load_config()
    db = lancedb.connect(index_path or str(cfg.path("index")))
    tb = db.open_table(DOCS_TABLE).to_arrow()
    st = tb.column("source_type").to_pylist()
    sym = tb.column("symbol").to_pylist()
    symbols = frozenset(s for s, t in zip(sym, st, strict=False) if t == "api" and s)

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(sorted(symbols)), encoding="utf-8")
    return symbols


def _dotted(node: ast.AST) -> str | None:
    """Reconstruct a dotted path from an Attribute/Name chain, or None."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def operator_calls(code: str) -> list[str]:
    """Every ``bpy.ops.<module>.<op>`` invoked in ``code`` (raises on syntax error)."""
    tree = ast.parse(code)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            path = _dotted(node.func)
            if path and path.startswith("bpy.ops.") and path.count(".") == 3:
                found.append(path)
    return found


def node_new_types(code: str) -> list[str]:
    """Every node ``bl_idname`` passed to a ``...nodes.new(...)`` call.

    The signature is ``Nodes.new(type)``, so it matches BOTH the positional form
    ``nodes.new('ShaderNodeX')`` AND the keyword form ``nodes.new(type='ShaderNodeX')``
    — the latter is the dominant real-world form, and missing it (the original bug)
    made the validator blind to ~75% of node calls. Owner may be an attribute
    (``node_tree.nodes``) or a bare name (``nodes``). Only literal string args are
    collected (a variable bl_idname can't be checked statically). Raises on syntax error.
    """
    tree = ast.parse(code)
    found: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "new":
            continue
        owner = node.func.value
        on_nodes = (isinstance(owner, ast.Attribute) and owner.attr == "nodes") or (
            isinstance(owner, ast.Name) and owner.id == "nodes"
        )
        if not on_nodes:
            continue
        # positional Nodes.new('X') ...
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(
            node.args[0].value, str
        ):
            found.append(node.args[0].value)
            continue
        # ... or keyword Nodes.new(type='X') (the canonical form)
        for kw in node.keywords:
            if kw.arg == "type" and isinstance(kw.value, ast.Constant) and isinstance(
                kw.value.value, str
            ):
                found.append(kw.value.value)
                break
    return found


def validate_code(code: str, symbols: frozenset[str]) -> CodeResult:
    """Statically validate one bpy script: syntax + operator + node-type existence.

    ``ok`` is True only if the code compiles, every ``bpy.ops`` call names a real
    5.1 operator, and every ``nodes.new('...')`` passes a real 5.1 node bl_idname.
    The error message lists the offenders so the eval report can show *what* the
    model hallucinated. Wrong args / socket names on a real symbol still pass.
    """
    try:
        ops = operator_calls(code)
        node_types = node_new_types(code)
    except SyntaxError as e:
        return CodeResult(ok=False, error_type="SyntaxError", error_message=str(e)[:300])

    bad_ops = sorted({op for op in ops if op not in symbols})
    if bad_ops:
        return CodeResult(
            ok=False,
            error_type="InvalidOperator",
            error_message="unknown 5.1 operators: " + ", ".join(bad_ops[:10]),
        )
    bad_nodes = sorted({n for n in node_types if f"bpy.types.{n}" not in symbols})
    if bad_nodes:
        return CodeResult(
            ok=False,
            error_type="InvalidNodeType",
            error_message="unknown 5.1 node bl_idnames: " + ", ".join(bad_nodes[:10]),
        )
    return CodeResult(ok=True)
