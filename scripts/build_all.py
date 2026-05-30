"""Run the whole offline pipeline end to end: acquire -> chunk -> embed/index.

Usage: ``uv run python scripts/build_all.py``  (needs the ``ml`` dep group)

Each stage is a separate process so a failure stops the run with a clear error.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
STAGES = ["build_corpus.py", "build_chunks.py", "build_index.py"]


def main() -> None:
    for stage in STAGES:
        print(f"\n=== {stage} ===", flush=True)
        result = subprocess.run([sys.executable, str(SCRIPTS / stage)])
        if result.returncode != 0:
            sys.exit(f"pipeline stopped: {stage} failed (exit {result.returncode})")
    print("\npipeline complete — index ready. Start the MCP server or run scripts/search.py.")


if __name__ == "__main__":
    main()
