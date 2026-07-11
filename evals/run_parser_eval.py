"""Explicitly opt-in live Gemini parser evaluation with report versioning."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATASET_PATH = ROOT / "evals/cases/gemini_parser_cases.jsonl"
REPORTS_PATH = ROOT / "evals/reports"
DATASET_VERSION = "phase1a-v1"
PROMPT_VERSION = "gemini-text-parser-phase1a-v1"
DEFAULT_MODEL = "gemini-2.5-flash-lite"
VALID_TYPES = {"expense", "income", "transfer"}
STATIC_CATEGORIES = [
    "Food & Beverage", "Transport", "Bills & Utilities", "Shopping",
    "Health", "Entertainment", "Education", "Personal Care",
    "Other Expense", "Salary", "Freelance", "Other Income",
]
STATIC_ACCOUNTS = ["Cash", "BRI", "BSI", "BCA", "DANA", "GoPay", "SeaBank"]


def load_cases() -> list[dict[str, Any]]:
    """Load the synthetic live-AI dataset from JSONL."""

    return [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_schema(parsed: dict[str, Any] | None) -> bool:
    """Validate the parser fields required for evaluation scoring."""

    if not isinstance(parsed, dict):
        return False
    if parsed.get("type") not in VALID_TYPES:
        return False
    if not isinstance(parsed.get("amount"), int) or parsed["amount"] <= 0:
        return False
    if not isinstance(parsed.get("date"), str):
        return False
    return parsed.get("type") == "transfer" or isinstance(parsed.get("category"), str)


def git_commit() -> str:
    """Return the checked-out commit without failing an otherwise valid run."""

    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> int:
    """Run live parser drafts only after explicit environment opt-in."""

    if os.getenv("ENABLE_LIVE_AI_EVAL") != "1":
        print("Live AI evaluation is disabled. Set ENABLE_LIVE_AI_EVAL=1 to opt in.")
        return 2
    if not os.getenv("GEMINI_API_KEY"):
        print("Live AI evaluation requires GEMINI_API_KEY.")
        return 2

    from evals.metrics import case_passed, compute_metrics
    from app.nlp import gemini_parser

    gemini_parser.get_valid_categories = lambda _transaction_type=None: list(STATIC_CATEGORIES)
    gemini_parser.get_valid_accounts = lambda: list(STATIC_ACCOUNTS)

    results: list[dict[str, Any]] = []
    for case in load_cases():
        started = time.perf_counter()
        error = None
        actual = None
        invalid_json = False
        try:
            actual = gemini_parser.parse_with_gemini(case["input"])
        except Exception as caught:
            error = type(caught).__name__
            invalid_json = "JSON" in error.upper()
        result = {
            "id": case["id"],
            "tags": case.get("tags") or [],
            "expected": case.get("expected") or {},
            "actual": actual,
            "completed": error is None,
            "valid_schema": validate_schema(actual),
            "invalid_json": invalid_json,
            "error": error,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "usage": None,
        }
        result["passed"] = case_passed(result)
        results.append(result)

    timestamp = datetime.now(timezone.utc)
    report = {
        "run_id": str(uuid.uuid4()),
        "timestamp": timestamp.isoformat(),
        "git_commit": git_commit(),
        "dataset_version": DATASET_VERSION,
        "prompt_version": PROMPT_VERSION,
        "model_name": os.getenv("GEMINI_TEXT_MODEL", os.getenv("GEMINI_MODEL", DEFAULT_MODEL)),
        "model_configuration": {"temperature": 0.0},
        "metrics": compute_metrics(results),
        "failed_cases": [item["id"] for item in results if not item["passed"]],
        "case_results": results,
    }
    REPORTS_PATH.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_PATH / f"parser-eval-{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{report['run_id'][:8]}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
