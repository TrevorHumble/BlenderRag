"""Mine Blender node graphs (shader / geometry / compositor) into legible text.

This is the structural-knowledge extractor the inventory flagged as missing
(`docs/SOURCES_AND_WEIGHTING.md`): the highest-leverage clean sources — the
**Blender Demo Files** (CC0/CC-BY, 5.x-current) and the open-movie production
`.blend`s (CC-BY) — carry their value as *node graphs*, which only become RAG text
once serialized. Docs and the API tell you a node *exists*; these show how nodes are
actually *wired* into a working material/effect.

Split for testability:
- ``serialize_node_graph`` — **pure**, turns a graph dict into readable text.
  Unit-tested; no bpy.
- ``node_tree_to_graph`` — the bpy walk that produces that dict from a live
  ``bpy.types.NodeTree``. Runs inside Blender (live-only); documented, not in CI.

Not wired into the build; ingestion gated (#49/#72). For Demo Files, re-save in 5.x
first so socket names are current; tag ``version_status`` from the file's version.
"""

from __future__ import annotations

from typing import Any


def serialize_node_graph(graph: dict[str, Any]) -> str:
    """Render a node-graph dict as legible text for retrieval.

    Expected shape (what ``node_tree_to_graph`` emits)::

        {
          "name": "Rock",
          "kind": "material",        # material | geometry | compositor
          "nodes": [
            {"name": "Principled BSDF", "type": "ShaderNodeBsdfPrincipled",
             "inputs": {"Roughness": 0.8, "Metallic": 0.0}},
            ...
          ],
          "links": [
            {"from_node": "Noise Texture", "from_socket": "Fac",
             "to_node": "Principled BSDF", "to_socket": "Roughness"},
          ],
        }
    """
    kind = graph.get("kind", "node")
    name = graph.get("name", "")
    lines = [f"{kind.capitalize()} node graph: {name}".rstrip(), "", "Nodes:"]
    for n in graph.get("nodes", []):
        inputs = n.get("inputs") or {}
        ins = ", ".join(f"{k}={_fmt(v)}" for k, v in inputs.items())
        suffix = f"  ({ins})" if ins else ""
        lines.append(f"  - {n.get('type', '?')} '{n.get('name', '')}'{suffix}")
    links = graph.get("links", [])
    if links:
        lines.append("")
        lines.append("Links:")
        for lk in links:
            lines.append(
                f"  - {lk.get('from_node', '?')}.{lk.get('from_socket', '?')}"
                f" -> {lk.get('to_node', '?')}.{lk.get('to_socket', '?')}"
            )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    """Compact a socket default_value (floats, short vectors) for text."""
    if isinstance(value, float):
        return f"{value:.3g}"
    if isinstance(value, (tuple, list)):
        if len(value) > 4:
            return f"[{len(value)} values]"
        return "(" + ", ".join(_fmt(x) for x in value) + ")"
    return str(value)


def node_tree_to_graph(node_tree: Any, *, kind: str = "node") -> dict[str, Any]:
    """Walk a live ``bpy.types.NodeTree`` into a graph dict. **Runs in Blender.**

    Live-only (needs bpy); not unit-tested. Kept tiny and defensive so it survives
    socket-API differences across node types: it reads ``default_value`` only for
    unlinked, simple-valued input sockets and skips anything it can't coerce.
    """
    nodes = []
    for node in getattr(node_tree, "nodes", []):
        inputs: dict[str, Any] = {}
        for sock in getattr(node, "inputs", []):
            if getattr(sock, "is_linked", False):
                continue
            val = getattr(sock, "default_value", None)
            if val is None:
                continue
            try:
                is_seq = hasattr(val, "__len__") and not isinstance(val, str)
                inputs[sock.name] = tuple(val) if is_seq else val
            except (TypeError, ValueError):
                continue
        nodes.append(
            {"name": node.name, "type": getattr(node, "bl_idname", node.type), "inputs": inputs}
        )
    links = [
        {
            "from_node": lk.from_node.name,
            "from_socket": lk.from_socket.name,
            "to_node": lk.to_node.name,
            "to_socket": lk.to_socket.name,
        }
        for lk in getattr(node_tree, "links", [])
    ]
    return {"name": getattr(node_tree, "name", ""), "kind": kind, "nodes": nodes, "links": links}
