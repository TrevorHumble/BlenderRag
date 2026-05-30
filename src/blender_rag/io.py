"""JSONL read/write helpers for pydantic models (Documents, Chunks)."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

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
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                yield model.model_validate_json(line)
            except ValidationError as e:
                raise ValueError(
                    f"{path}:{lineno}: invalid {model.__name__} row"
                ) from e
