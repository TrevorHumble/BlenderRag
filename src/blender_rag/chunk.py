"""Structure-aware chunking.

Two strategies, routed by ``source_type``:

* **Markdown/RST/prose** (manual, release_notes, dev_docs, api) — split on the
  header hierarchy so each chunk is a coherent section, prefixed with its header
  breadcrumb (e.g. ``Python API > Changes``) so it reads standalone. Oversized
  sections are packed into ~``max_chars`` windows on paragraph boundaries with
  overlap.
* **Python** (code, blendermcp) — tree-sitter splits on function/class
  boundaries so a chunk is never a half-defined symbol.

Budgets are in characters (≈ ``tokens * 4``) to keep this module in the light
dependency tier — no tokenizer/torch needed, so it runs in CI.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

from blender_rag.config import Config, load_config
from blender_rag.schema import Chunk, Document, SourceType

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_PARA_SPLIT = re.compile(r"\n\s*\n")

_MARKDOWN_TYPES = {
    SourceType.MANUAL,
    SourceType.RELEASE_NOTES,
    SourceType.DEV_DOCS,
    SourceType.API,
}
_CODE_TYPES = {SourceType.CODE, SourceType.BLENDERMCP}

_PY_LANGUAGE = Language(tspython.language())
_PY_NODE_TYPES = {"function_definition", "class_definition", "decorated_definition"}


def approx_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token). For stats, not exactness."""
    return max(1, len(text) // 4)


# --------------------------------------------------------------------------- #
# Markdown / prose
# --------------------------------------------------------------------------- #
def split_markdown_sections(text: str) -> list[tuple[tuple[str, ...], str]]:
    """Split markdown into ``(header_path, body)`` sections.

    ``header_path`` is the breadcrumb of enclosing headers (outermost first).
    Header lines are consumed into the path; bodies exclude them.
    """
    sections: list[tuple[tuple[str, ...], str]] = []
    stack: dict[int, str] = {}
    buf: list[str] = []
    cur_path: tuple[str, ...] = ()

    def flush() -> None:
        body = "\n".join(buf).strip()
        if body:
            sections.append((cur_path, body))

    for line in text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            flush()
            buf = []
            level = len(m.group(1))
            stack[level] = m.group(2).strip()
            for deeper in [lvl for lvl in stack if lvl > level]:
                del stack[deeper]
            cur_path = tuple(stack[lvl] for lvl in sorted(stack))
        else:
            buf.append(line)
    flush()
    return sections


def _hard_split(text: str, max_chars: int) -> list[str]:
    """Last resort: split an oversized paragraph on whitespace near the budget."""
    out: list[str] = []
    while len(text) > max_chars:
        cut = text.rfind(" ", 0, max_chars)
        if cut <= 0:
            cut = max_chars
        out.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        out.append(text)
    return out


def pack_section(
    path: tuple[str, ...],
    body: str,
    *,
    max_chars: int,
    overlap_chars: int,
    min_chars: int,
) -> list[str]:
    """Pack a section body into <=``max_chars`` chunks, each prefixed with the
    header breadcrumb. Splits on paragraph boundaries with a tail overlap."""
    breadcrumb = " > ".join(path)
    prefix = f"{breadcrumb}\n\n" if breadcrumb else ""
    budget = max(1, max_chars - len(prefix))

    if len(body) <= budget:
        full = prefix + body
        return [full] if len(full.strip()) >= min_chars else []

    paras: list[str] = []
    for para in _PARA_SPLIT.split(body):
        para = para.strip()
        if not para:
            continue
        if len(para) > budget:
            paras.extend(_hard_split(para, budget))
        else:
            paras.append(para)

    chunks: list[str] = []
    cur = ""
    for para in paras:
        candidate = f"{cur}\n\n{para}" if cur else para
        if cur and len(candidate) > budget:
            chunks.append(cur)
            tail = cur[-overlap_chars:].lstrip() if overlap_chars else ""
            cur = f"{tail}\n\n{para}" if tail else para
        else:
            cur = candidate
    if cur.strip():
        chunks.append(cur)

    full_chunks = (prefix + c for c in chunks)
    return [fc for fc in full_chunks if len(fc.strip()) >= min_chars]


def chunk_markdown(
    doc: Document, *, max_chars: int, overlap_chars: int, min_chars: int
) -> Iterator[Chunk]:
    idx = 0
    for path, body in split_markdown_sections(doc.text):
        for text in pack_section(
            path, body, max_chars=max_chars, overlap_chars=overlap_chars, min_chars=min_chars
        ):
            yield Chunk.from_document(
                doc, text, idx, extra={"section": " > ".join(path)}
            )
            idx += 1


# --------------------------------------------------------------------------- #
# Python code
# --------------------------------------------------------------------------- #
def _node_name(node) -> str:
    target = node
    if node.type == "decorated_definition":
        target = node.child_by_field_name("definition") or node
    name = target.child_by_field_name("name")
    return name.text.decode("utf-8") if name is not None else target.type


def split_python_symbols(source: str) -> list[tuple[str, str, int]]:
    """Return ``(symbol_name, code, start_line)`` for top-level defs/classes.

    Top-level statements between definitions (imports, constants) are grouped
    into a synthetic ``<module>`` preamble chunk so nothing is dropped.
    """
    parser = Parser(_PY_LANGUAGE)
    tree = parser.parse(bytes(source, "utf-8"))
    root = tree.root_node

    out: list[tuple[str, str, int]] = []
    preamble: list[str] = []
    for node in root.children:
        text = node.text.decode("utf-8")
        if node.type in _PY_NODE_TYPES:
            out.append((_node_name(node), text, node.start_point[0] + 1))
        elif text.strip():
            preamble.append(text)
    if preamble:
        out.insert(0, ("<module>", "\n".join(preamble), 1))
    return out


def chunk_python(doc: Document) -> Iterator[Chunk]:
    for idx, (name, code, line) in enumerate(split_python_symbols(doc.text)):
        yield Chunk.from_document(doc, code, idx, extra={"symbol": name, "line": line})


# --------------------------------------------------------------------------- #
# Routing
# --------------------------------------------------------------------------- #
def chunk_document(doc: Document, cfg: Config | None = None) -> Iterator[Chunk]:
    cfg = cfg or load_config()
    max_tokens = int(cfg.section("chunking", "max_tokens", default=512))
    overlap_tokens = int(cfg.section("chunking", "overlap_tokens", default=64))
    min_chars = int(cfg.section("chunking", "min_chunk_chars", default=64))
    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4

    if doc.source_type in _CODE_TYPES:
        yield from chunk_python(doc)
    else:  # markdown/prose is the default
        yield from chunk_markdown(
            doc, max_chars=max_chars, overlap_chars=overlap_chars, min_chars=min_chars
        )


def chunk_corpus(docs: Iterable[Document], cfg: Config | None = None) -> Iterator[Chunk]:
    cfg = cfg or load_config()
    for doc in docs:
        yield from chunk_document(doc, cfg)
