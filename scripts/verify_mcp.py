"""End-to-end MCP verification: launch the server as a real stdio subprocess,
do the protocol handshake, list tools, and call search_blender_docs.

This proves a Claude-Code-style client can actually use the server (beyond the
in-process unit tests). Usage: ``uv run python scripts/verify_mcp.py``
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from blender_rag.config import REPO_ROOT, load_config


async def main() -> None:
    cfg = load_config()
    env = dict(os.environ)
    env["INDEX_PATH"] = str(cfg.path("index"))

    # Launch the venv python directly (sys.executable). Wrapping with `uv run`
    # can leak uv's startup output onto stdout and corrupt the JSON-RPC stream.
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(REPO_ROOT / "src" / "blender_rag" / "server.py")],
        env=env,
        cwd=str(REPO_ROOT),
    )

    errlog = open(REPO_ROOT / "data" / "mcp_server.err", "w", encoding="utf-8")
    async with stdio_client(params, errlog=errlog) as (read, write):
        async with ClientSession(read, write) as session:
            print("connecting -> initialize ...", flush=True)
            await asyncio.wait_for(session.initialize(), timeout=90)
            print("initialized", flush=True)

            tools = await asyncio.wait_for(session.list_tools(), timeout=30)
            names = [t.name for t in tools.tools]
            print(f"TOOLS: {names}")
            assert "search_blender_docs" in names

            print("calling search_blender_docs ...", flush=True)
            result = await asyncio.wait_for(
                session.call_tool(
                    "search_blender_docs",
                    {
                        "query": "add a subdivision surface modifier in python",
                        "top_k": 3,
                        "blender_version": "5.1",
                    },
                ),
                timeout=180,
            )
            print(f"isError: {result.isError}")
            payload = result.structuredContent or {}
            hits = payload.get("result") if isinstance(payload, dict) else None
            if hits is None:
                # fall back to text content
                text = "".join(getattr(c, "text", "") for c in result.content)
                hits = json.loads(text) if text.strip().startswith("[") else text
            print(f"HITS: {len(hits) if isinstance(hits, list) else 'n/a'}")
            if isinstance(hits, list):
                for h in hits:
                    print(
                        f"  - {h.get('title')} | v{h.get('blender_version')}"
                        f" | {h.get('source_type')}"
                    )
            print("MCP VERIFY: OK")


if __name__ == "__main__":
    asyncio.run(main())
