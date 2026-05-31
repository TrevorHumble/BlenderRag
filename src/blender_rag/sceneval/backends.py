"""Real, optional backends for the scene-eval runner.

These satisfy the runner Protocols against live systems. They are import-light at
module load (heavy deps are imported lazily inside ``__init__``) so importing
this module never drags in torch / the anthropic SDK / an MCP client unless a
backend is actually constructed — the pure core and the fake backend stay
CI-friendly.

- ``InProcessRagSearcher`` — the real RAG, in-process (Embedder + hybrid_search
  over the LanceDB index). No subprocess; the fastest way to put real retrieval
  in the loop. Verifiable wherever the index + ml deps exist.
- ``McpBlenderExecutor`` — runs code against a live Blender via the ``blender``
  MCP server (``execute_blender_code`` + ``get_scene_info``). Live-only.
- ``AnthropicSceneAgent`` — a Claude tool-use agent that decides each action.
  Needs ``ANTHROPIC_API_KEY``. The message-mapping is unit-tested with a fake
  client; the live call is the only unverified-in-CI part.
"""

from __future__ import annotations

from typing import Any

from blender_rag.sceneval.runner import AgentAction, CodeResult
from blender_rag.sceneval.schema import SceneSnapshot, SessionEvent


class InProcessRagSearcher:
    """The real knowledge base, in-process. Satisfies ``RagSearcher``."""

    def __init__(self, *, index_path: str | None = None, device: str = "auto"):
        from blender_rag.config import load_config
        from blender_rag.embed import Embedder
        from blender_rag.index import DOCS_TABLE, open_table

        cfg = load_config()
        self._embedder = Embedder(cfg.section("embedding", "prose_model"), device=device)
        self._table = open_table(index_path or str(cfg.path("index")), DOCS_TABLE)

    def search(
        self, query: str, *, top_k: int, source_type: str | None
    ) -> list[dict[str, Any]]:
        from blender_rag.index import hybrid_search

        return hybrid_search(
            self._table, self._embedder, query, top_k=top_k, source_type=source_type
        )


# --------------------------------------------------------------------------- #
# Anthropic agent
# --------------------------------------------------------------------------- #
_SYSTEM = (
    "You are an expert Blender 5.1 technical artist scripting a scene in Python "
    "(bpy). Blender's API changed in 5.x and your training is largely 4.x, so "
    "BEFORE writing a call, use search_blender_docs to confirm the operator / "
    "type / property and version-specific behavior. Then run execute_blender_code "
    "with small, incremental snippets. When the scene satisfies the brief, stop."
)


def _tool_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": "search_blender_docs",
            "description": "Search the local Blender 5.1 knowledge base before writing bpy.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "source_type": {"type": "string"},
                    "top_k": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "execute_blender_code",
            "description": "Run Python (bpy) in the live Blender session.",
            "input_schema": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        },
    ]


def _first_tool_use(reply: Any) -> Any | None:
    for block in getattr(reply, "content", []) or []:
        if getattr(block, "type", None) == "tool_use":
            return block
    return None


def _content_blocks(reply: Any) -> list[dict[str, Any]]:
    """Serialize a reply's content blocks so they can be re-sent as an assistant turn."""
    out: list[dict[str, Any]] = []
    for b in getattr(reply, "content", []) or []:
        if getattr(b, "type", None) == "tool_use":
            out.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
        elif getattr(b, "type", None) == "text":
            out.append({"type": "text", "text": b.text})
    return out


def _result_text_for(event: SessionEvent | None, tool_name: str) -> str:
    """Build the tool_result content fed back to the model from the latest event."""
    if event is None:
        return "(no result)"
    etype = getattr(event, "type", None)
    if tool_name == "search_blender_docs" and etype == "rag_query":
        if not event.hits:
            return "No results."
        return "\n\n".join(
            f"[{h.get('source_type')}] {h.get('title')} ({h.get('source_url')})\n{h.get('text')}"
            for h in event.hits
        )
    if tool_name == "execute_blender_code" and etype == "code_exec":
        if event.ok:
            return "Executed OK."
        return f"ERROR {event.error_type}: {event.error_message}"
    return "(result unavailable)"


def _block_to_action(block: Any) -> AgentAction:
    name = block.name
    args = block.input or {}
    if name == "search_blender_docs":
        return AgentAction(
            kind="query",
            query=str(args.get("query", "")),
            source_type=args.get("source_type"),
            top_k=int(args.get("top_k", 6)),
        )
    if name == "execute_blender_code":
        return AgentAction(kind="exec", code=str(args.get("code", "")))
    return AgentAction(kind="done")


class AnthropicSceneAgent:
    """A Claude tool-use agent that drives the build. Satisfies ``SceneAgent``.

    The runner executes the tools and records events; this agent maps the runner's
    history back into the Anthropic conversation and asks the model for the next
    action. ``client`` is injectable so the message-mapping is unit-tested with a
    fake; the live path needs ``ANTHROPIC_API_KEY``.
    """

    def __init__(
        self,
        task_prompt: str,
        *,
        client: Any | None = None,
        model: str = "claude-sonnet-4-5",
        max_tokens: int = 2048,
    ):
        self._client = client or _lazy_anthropic_client()
        self._model = model
        self._max_tokens = max_tokens
        self._messages: list[dict[str, Any]] = [{"role": "user", "content": task_prompt}]
        self._pending_assistant: list[dict[str, Any]] | None = None
        self._pending_tool_use_id: str | None = None
        self._pending_tool_name: str = ""

    def next_action(self, history: list[SessionEvent]) -> AgentAction:
        # Feed the previous tool's result back into the conversation.
        if self._pending_tool_use_id is not None:
            latest = history[-1] if history else None
            result = _result_text_for(latest, self._pending_tool_name)
            self._messages.append({"role": "assistant", "content": self._pending_assistant})
            self._messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": self._pending_tool_use_id,
                            "content": result,
                        }
                    ],
                }
            )
            self._pending_tool_use_id = None

        reply = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=_SYSTEM,
            tools=_tool_specs(),
            messages=self._messages,
        )
        block = _first_tool_use(reply)
        if block is None:
            return AgentAction(kind="done")

        self._pending_assistant = _content_blocks(reply)
        self._pending_tool_use_id = block.id
        self._pending_tool_name = block.name
        return _block_to_action(block)


def _lazy_anthropic_client() -> Any:
    import os

    import anthropic

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set; cannot use the live agent.")
    return anthropic.Anthropic()


# --------------------------------------------------------------------------- #
# Live Blender executor (MCP) — live-only, not exercised in CI
# --------------------------------------------------------------------------- #
def _mcp_result_text(res: Any) -> str:
    return "".join(getattr(c, "text", "") for c in getattr(res, "content", []) or [])


def _guess_error_type(text: str) -> str:
    import re

    m = re.search(r"\b(\w*Error)\b", text)
    return m.group(1) if m else "RuntimeError"


def _parse_snapshot(text: str) -> SceneSnapshot:
    """Best-effort scene census from get_scene_info JSON (graceful on mismatch)."""
    import json

    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return SceneSnapshot()
    objects = data.get("objects", []) if isinstance(data, dict) else []
    n_obj = data.get("object_count", len(objects)) if isinstance(data, dict) else 0
    meshes = sum(1 for o in objects if isinstance(o, dict) and o.get("type") == "MESH")
    lights = sum(1 for o in objects if isinstance(o, dict) and o.get("type") == "LIGHT")
    mats = data.get("material_count", 0) if isinstance(data, dict) else 0
    return SceneSnapshot(objects=n_obj, meshes=meshes, materials=mats, lights=lights)


class McpBlenderExecutor:
    """Runs code against a live Blender via the ``blender`` MCP server.

    Live-only: needs Blender open with the BlenderMCP addon and the bridge
    command available (default ``uvx blender-mcp``). Holds one persistent stdio
    session on a background event loop so scene state survives across execs.
    Satisfies ``BlenderExecutor``.
    """

    def __init__(
        self,
        *,
        command: str = "uvx",
        args: tuple[str, ...] = ("blender-mcp",),
        connect_timeout: float = 90.0,
    ):
        import asyncio
        import threading

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._session: Any = None
        fut = asyncio.run_coroutine_threadsafe(
            self._connect(command, list(args)), self._loop
        )
        fut.result(timeout=connect_timeout)

    async def _connect(self, command: str, args: list[str]) -> None:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(command=command, args=args)
        self._client_cm = stdio_client(params)
        read, write = await self._client_cm.__aenter__()
        self._session_cm = ClientSession(read, write)
        self._session = await self._session_cm.__aenter__()
        await self._session.initialize()

    def _call(self, name: str, args: dict[str, Any], *, timeout: float = 180.0) -> Any:
        import asyncio

        fut = asyncio.run_coroutine_threadsafe(
            self._session.call_tool(name, args), self._loop
        )
        return fut.result(timeout=timeout)

    def execute(self, code: str) -> CodeResult:
        res = self._call("execute_blender_code", {"code": code})
        text = _mcp_result_text(res)
        is_error = bool(getattr(res, "isError", False))
        if is_error or "Traceback" in text or "Error:" in text:
            return CodeResult(
                ok=False, error_type=_guess_error_type(text), error_message=text[:500]
            )
        return CodeResult(ok=True)

    def snapshot(self) -> SceneSnapshot:
        try:
            return _parse_snapshot(_mcp_result_text(self._call("get_scene_info", {})))
        except Exception:  # noqa: BLE001 — snapshot is best-effort telemetry
            return SceneSnapshot()
