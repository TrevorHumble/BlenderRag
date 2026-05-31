"""Static detector for known Blender 5.x bpy footguns in generated code.

Seeded from ``corpus/curated/blender_5x_gotchas.md`` and the blender-mcp skill:
these are API/enum changes in 5.x that *silently* produce wrong results or raise,
and that a model trained largely on 4.x will reach for by default. Counting them
in a session's executed code is a direct, objective signal of whether the RAG
steered the model onto 5.x-correct calls.

This is intentionally a cheap *lexical* scan (regex / substring), not an AST or a
live check — it errs toward high-confidence, low-false-positive patterns. It is
pure and reusable: it doubles as a lint for any generated bpy snippet.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel


class GotchaHit(BaseModel):
    """One detected footgun occurrence."""

    rule_id: str
    message: str
    fix: str
    match: str


def _regex_finder(pattern: str, flags: int = 0) -> Callable[[str], list[str]]:
    rx = re.compile(pattern, flags)
    return lambda code: [m.group(0) for m in rx.finditer(code)]


def _agx_casing_finder(code: str) -> list[str]:
    """view_transform must be exactly 'AgX' in 5.x; any other casing is wrong."""
    rx = re.compile(r"""view_transform\s*=\s*['"]([^'"]+)['"]""")
    return [
        m.group(0)
        for m in rx.finditer(code)
        if m.group(1).lower() == "agx" and m.group(1) != "AgX"
    ]


def _new_effect_missing_length_finder(code: str) -> list[str]:
    """VSE ``strips.new_effect(...)`` requires the 5.x ``length=`` keyword.

    The arg pattern balances one level of nested parens so a call like
    ``new_effect(type='X', frame_end=foo(1), length=10)`` isn't truncated at the
    first ``)`` and mis-flagged as missing length. [review #4]
    """
    rx = re.compile(r"new_effect\s*\((?:[^()]|\([^()]*\))*\)")
    return [m.group(0) for m in rx.finditer(code) if "length=" not in m.group(0)]


@dataclass(frozen=True)
class GotchaRule:
    id: str
    message: str
    fix: str
    finder: Callable[[str], list[str]]


# High-confidence, low-false-positive rules. Each maps a 4.x habit to its 5.x fix.
RULES: tuple[GotchaRule, ...] = (
    GotchaRule(
        "eevee_next_engine_id",
        "BLENDER_EEVEE_NEXT is not a valid engine id in 5.x.",
        "Use scene.render.engine = 'BLENDER_EEVEE'.",
        _regex_finder(r"\bBLENDER_EEVEE_NEXT\b"),
    ),
    GotchaRule(
        "nishita_sky_removed",
        "The NISHITA sky model was removed in Blender 5.0.",
        "Use the new Sky Texture node options (no 'NISHITA' sky_type).",
        _regex_finder(r"\bNISHITA\b"),
    ),
    GotchaRule(
        "agx_view_transform_casing",
        "view_transform is case-sensitive; only 'AgX' is valid.",
        "Set view_transform = 'AgX' (capital A, capital X).",
        _agx_casing_finder,
    ),
    GotchaRule(
        "glare_type_attribute",
        "Glare node config moved to input sockets in 5.x; .glare_type is unreliable.",
        "Set the Glare values via node.inputs[...] sockets, not a .glare_type attr.",
        _regex_finder(r"\.glare_type\b"),
    ),
    GotchaRule(
        "bgl_module_removed",
        "The bgl module was removed; it is replaced by the gpu module.",
        "Port bgl draw code to the gpu / gpu_extras modules.",
        _regex_finder(r"\bimport\s+bgl\b|\bbgl\."),
    ),
    GotchaRule(
        "register_module_removed",
        "register_module / unregister_module were removed after 2.7x.",
        "Register classes explicitly with bpy.utils.register_class.",
        _regex_finder(r"\b(?:un)?register_module\b"),
    ),
    GotchaRule(
        "new_effect_missing_length",
        "VSE new_effect() requires the length= keyword in 5.x.",
        "Pass length= (and frame_start/frame_end) to strips.new_effect(...).",
        _new_effect_missing_length_finder,
    ),
)


def _strip_line_comments(code: str) -> str:
    """Drop ``#`` line comments so a self-aware note ("# avoid NISHITA") isn't
    counted as a footgun. Conservative: only strips ``#`` that is not inside a
    quoted string on that line (the footgun *values* live in strings, so we must
    not strip those)."""
    out: list[str] = []
    for line in code.splitlines():
        in_str: str | None = None
        cut = len(line)
        for i, ch in enumerate(line):
            if in_str:
                if ch == in_str:
                    in_str = None
            elif ch in "'\"":
                in_str = ch
            elif ch == "#":
                cut = i
                break
        out.append(line[:cut])
    return "\n".join(out)


def detect_gotchas(code: str) -> list[GotchaHit]:
    """Return every 5.x footgun occurrence in ``code`` (one hit per match).

    Line comments are stripped first so commentary doesn't inflate the count;
    string contents are preserved (the footgun enum values live in strings).
    """
    code = _strip_line_comments(code)
    hits: list[GotchaHit] = []
    for rule in RULES:
        for match in rule.finder(code):
            hits.append(
                GotchaHit(rule_id=rule.id, message=rule.message, fix=rule.fix, match=match)
            )
    return hits


def count_gotchas(code: str) -> int:
    """Total footgun occurrences in ``code`` (the ``GotchaCounter`` for metrics)."""
    return len(detect_gotchas(code))
