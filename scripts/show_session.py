"""Pretty-print a saved scene-eval SessionLog as a readable transcript.

Usage:
  uv run python scripts/show_session.py path/to/island_on_0.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from blender_rag.sceneval.schema import SessionLog
from blender_rag.sceneval.transcript import render_transcript


def main() -> None:
    ap = argparse.ArgumentParser(description="Render a SessionLog JSON as a transcript")
    ap.add_argument("log", type=Path, help="path to a SessionLog JSON (from --logs)")
    ap.add_argument("--code-lines", type=int, default=6, help="max code lines per exec")
    args = ap.parse_args()

    if not args.log.is_file():
        sys.exit(f"no such file: {args.log}")
    log = SessionLog.model_validate_json(args.log.read_text(encoding="utf-8"))
    print(render_transcript(log, code_lines=args.code_lines))


if __name__ == "__main__":
    main()
