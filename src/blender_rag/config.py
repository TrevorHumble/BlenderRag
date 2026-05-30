"""Load and access ``config.yaml`` (the pipeline's single source of truth)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    """Thin typed accessor over the parsed config dict."""

    data: dict[str, Any]
    root: Path = field(default=REPO_ROOT)

    @property
    def blender_version(self) -> str:
        return self.data["blender_version"]

    def path(self, key: str) -> Path:
        """Resolve a ``paths.<key>`` entry to an absolute Path under the repo."""
        return (self.root / self.data["paths"][key]).resolve()

    def section(self, *keys: str, default: Any = None) -> Any:
        """Walk nested keys, e.g. ``section("sources", "manual", "branch")``."""
        node: Any = self.data
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node


@lru_cache(maxsize=4)
def load_config(path: str | Path | None = None) -> Config:
    cfg_path = Path(path) if path else REPO_ROOT / "config.yaml"
    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(data=data, root=cfg_path.resolve().parent)
