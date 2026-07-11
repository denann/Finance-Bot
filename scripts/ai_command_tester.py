"""Historical CLI wrapper for the canonical app.scripts tester."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.scripts.ai_command_tester import main


if __name__ == "__main__":
    raise SystemExit(main())
