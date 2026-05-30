"""JSONL read/write helpers for pydantic models (Documents, Chunks)."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


def write_jsonl(path: str | Path, models: Iterable[BaseModel]) -> int:
    """Write ``models`` to ``path`` as one JSON object per line. Returns count."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for m in models:
            f.write(m.model_dump_json())
            f.write("\n")
            n += 1
    return n


def read_jsonl(path: str | Path, model: type[M]) -> Iterator[M]:
    """Yield validated ``model`` instances from a JSONL file."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield model.model_validate_json(line)
