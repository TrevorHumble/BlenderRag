import asyncio
import inspect

import pytest

# The MCP SDK lives in the `ml` dependency group; skip in the light CI tier.
pytest.importorskip("mcp")

from blender_rag import server  # noqa: E402


def test_search_tool_is_registered_and_callable():
    assert callable(server.search_blender_docs)
    sig = inspect.signature(server.search_blender_docs)
    assert set(sig.parameters) >= {"query", "top_k", "source_type", "blender_version"}


def test_server_has_name_and_instructions():
    assert server.mcp.name == "blender-docs"
    assert "Blender 5.1" in (server.mcp.instructions or "")


def test_list_tools_exposes_search_via_protocol():
    tools = asyncio.run(server.mcp.list_tools())
    by_name = {t.name: t for t in tools}
    assert "search_blender_docs" in by_name
    props = by_name["search_blender_docs"].inputSchema.get("properties", {})
    assert "query" in props
    assert "blender_version" in props
    assert "source_type" in props
