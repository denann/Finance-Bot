"""Compatibility entry point for the canonical AI command tester."""

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scripts.ai_command_tester import main


if __name__ == "__main__":
    raise SystemExit(main())
