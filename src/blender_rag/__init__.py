"""Blender RAG — a local Blender 5.1 knowledge base for Claude Code.

Pipeline: acquire -> normalize -> chunk -> contextualize -> embed -> index,
served to Claude Code through a FastMCP `search_blender_docs` tool.
"""

from blender_rag.schema import Chunk, Document, SourceType, stable_id

__version__ = "0.1.0"

__all__ = ["Chunk", "Document", "SourceType", "stable_id", "__version__"]
