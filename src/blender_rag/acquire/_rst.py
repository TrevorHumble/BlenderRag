"""Minimal RST -> markdown conversion for the Blender manual.

The manual is Sphinx RST. Rather than a full docutils parse, we normalize the
constructs that matter for retrieval text:

* underline / over-underline headers -> markdown ``#`` headers (so the existing
  markdown chunker can split on them),
* inline roles (``:doc:`Label <target>```, ``:ref:`x```) -> their visible text,
* noisy directives (``toctree``, ``figure``, ``image``, ``include``) -> dropped
  with their indented blocks; admonitions (``note``, ``seealso``...) -> a bold
  label keeping their content.

It is deliberately lossy but produces clean, readable chunks.
"""

from __future__ import annotations

import re

_HEADER_CHARS = set("#*=-^\"~+`:.'_")
_ROLE_RE = re.compile(r":[a-zA-Z][\w:+-]*:`([^`<]+?)(?:\s*<[^>]*>)?`")
_LINK_RE = re.compile(r"`([^`<]+?)\s*<[^>]*>`_+")
_DROP_BLOCK = re.compile(r"^(\s*)\.\.\s+(toctree|figure|image|include|only|raw|index)::")
_DIRECTIVE = re.compile(r"^(\s*)\.\.\s+([a-zA-Z-]+)::(.*)$")
_OPTION = re.compile(r"^\s+:[\w-]+:.*$")
_COMMENT = re.compile(r"^\s*\.\.($|\s)")
_ADMONITIONS = {"note", "tip", "warning", "seealso", "admonition", "important", "hint"}


def _is_rule(line: str) -> bool:
    s = line.strip()
    return len(s) >= 3 and len(set(s)) == 1 and s[0] in _HEADER_CHARS


def clean_inline(text: str) -> str:
    text = _LINK_RE.sub(r"\1", text)
    text = _ROLE_RE.sub(r"\1", text)
    return text.replace("``", "`")


def rst_to_markdown(text: str) -> str:
    lines = text.split("\n")
    levels: dict[str, int] = {}
    out: list[str] = []
    i, n = 0, len(lines)

    def header(title: str, char: str) -> str:
        level = levels.setdefault(char, len(levels) + 1)
        return "#" * min(level, 6) + " " + clean_inline(title.strip())

    while i < n:
        line = lines[i]

        # over + underline header (e.g. *** / Title / ***)
        if (
            _is_rule(line)
            and i + 2 < n
            and lines[i + 1].strip()
            and _is_rule(lines[i + 2])
            and line.strip()[0] == lines[i + 2].strip()[0]
        ):
            out.append(header(lines[i + 1], line.strip()[0]))
            i += 3
            continue

        # underline header (Title / ===)
        if (
            line.strip()
            and not _is_rule(line)
            and i + 1 < n
            and _is_rule(lines[i + 1])
            and len(lines[i + 1].strip()) >= len(line.strip())
        ):
            out.append(header(line, lines[i + 1].strip()[0]))
            i += 2
            continue

        # noisy directive: drop it and its indented block
        m = _DROP_BLOCK.match(line)
        if m:
            indent = len(m.group(1))
            i += 1
            while i < n and (not lines[i].strip() or _indent(lines[i]) > indent):
                i += 1
            continue

        # other directive: keep admonition content under a bold label, else drop marker
        m = _DIRECTIVE.match(line)
        if m:
            name = m.group(2).lower()
            if name in _ADMONITIONS:
                label = f"**{name.capitalize()}:**"
                rest = clean_inline(m.group(3).strip())
                out.append(f"{label} {rest}".rstrip())
            i += 1
            continue

        if _OPTION.match(line) or _COMMENT.match(line):
            i += 1
            continue

        out.append(clean_inline(line))
        i += 1

    return "\n".join(out)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())
