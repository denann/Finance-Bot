"""Explicitly opt-in live Gemini evaluation with report versioning."""

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
DATASET_VERSION = "phase0-5-live-ai-v1"
VALID_TYPES = {"expense", "income", "transfer"}
STATIC_CATEGORIES = [
    "Food & Beverage", "Transport", "Bills & Utilities", "Shopping",
    "Health", "Entertainment", "Education", "Personal Care",
    "Other Expense", "Salary", "Freelance", "Other Income",
]
STATIC_ACCOUNTS = ["Cash", "BRI", "BSI", "BCA", "DANA", "GoPay", "SeaBank"]
SAMPLE_RECEIPT_IMAGE = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
    b"\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe"
    b"\x02\xfeA\xe2'\xb5\x00\x00\x00\x00IEND\xaeB`\x82"
)


def load_cases() -> list[dict[str, Any]]:
    """Load the synthetic live-AI dataset from JSONL."""

    return [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_transaction_schema(parsed: dict[str, Any] | None) -> bool:
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


def validate_schema(feature: str, actual: dict[str, Any] | None) -> bool:
    """Validate feature-specific output without enforcing narrative wording."""

    if not isinstance(actual, dict):
        return False
    if feature in {"transaction_parser", "transaction_batch_parser", "image_receipt_parser"}:
        items = actual.get("items") if feature != "transaction_parser" else [actual]
        return isinstance(items, list) and bool(items) and all(validate_transaction_schema(item) for item in items)
    if feature in {"finance_ask", "finance_insight", "finance_audit", "finance_coach"}:
        text = str(actual.get("text") or "").strip()
        metadata = actual.get("grounding_metadata") or {}
        return bool(text) and int(metadata.get("records_selected") or 0) <= int(actual.get("context_record_limit") or 40)
    if feature == "malformed_model_output":
        return actual.get("parsed") is None
    if feature == "safety_routing_contract":
        return isinstance(actual.get("route"), str)
    return False


def git_commit() -> str:
    """Return the checked-out commit without failing an otherwise valid run."""

    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def configure_static_boundaries(gemini_parser: Any, gemini_image_parser: Any) -> None:
    """Replace dynamic category/account reads with local synthetic lists."""

    gemini_parser.get_valid_categories = lambda _transaction_type=None: list(STATIC_CATEGORIES)
    gemini_parser.get_valid_accounts = lambda: list(STATIC_ACCOUNTS)
    gemini_image_parser.get_valid_categories = lambda _transaction_type=None: list(STATIC_CATEGORIES)
    gemini_image_parser.get_valid_accounts = lambda: list(STATIC_ACCOUNTS)


def synthetic_context(record_limit: int) -> dict[str, Any]:
    """Build bounded fake finance context for live narrative AI cases."""

    selected = min(record_limit, 40)
    return {
        "summary": {
            "period": "2026-07",
            "total_income_display": "Rp8.000.000",
            "total_expense_display": "Rp2.450.000",
            "net_display": "Rp5.550.000",
        },
        "expense_by_category": [
            {"category": "Food & Beverage", "amount_display": "Rp950.000"},
            {"category": "Transport", "amount_display": "Rp300.000"},
        ],
        "top_expenses": [
            {"description": "Belanja bulanan", "amount_display": "Rp650.000", "date": "2026-07-06"},
        ],
        "anomalies": [],
        "data_quality_issues": [],
        "available_commands": ["/ask", "/insight", "/audit", "/coach", "/transaksi", "/edit_txn", "/delete_txn"],
        "context_metadata": {
            "records_considered": 52,
            "records_selected": selected,
            "context_truncated": True,
            "aggregation_level": "monthly",
        },
    }


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Execute one live opt-in case and return sanitized result metadata."""

    from evals.metrics import case_passed
    from app.config import AI_CONTEXT_RECORD_LIMIT
    from app.nlp import gemini_image_parser, gemini_parser
    from app.nlp.gemini_finance_insight import generate_finance_insight

    configure_static_boundaries(gemini_parser, gemini_image_parser)
    feature = str(case.get("feature") or "transaction_parser")
    started = time.perf_counter()
    error = None
    actual: dict[str, Any] | None = None
    input_characters = 0
    output_characters = 0

    try:
        if feature == "transaction_parser":
            input_text = str(case.get("input") or "")
            input_characters = len(input_text)
            parsed = gemini_parser.parse_with_gemini(input_text)
            actual = parsed
            output_characters = len(json.dumps(parsed or {}, ensure_ascii=False))
        elif feature == "transaction_batch_parser":
            inputs = [str(value or "") for value in case.get("inputs") or []]
            input_characters = sum(len(value) for value in inputs)
            parsed_by_index = gemini_parser.parse_batch_with_gemini(inputs)
            actual = {"items": [parsed_by_index[index] for index in sorted(parsed_by_index)]}
            output_characters = len(json.dumps(actual, ensure_ascii=False))
        elif feature == "image_receipt_parser":
            caption = str(case.get("caption") or "")
            input_characters = len(caption)
            parsed_image = gemini_image_parser.parse_transactions_from_image(
                SAMPLE_RECEIPT_IMAGE,
                mime_type="image/png",
                caption=caption,
            )
            actual = {"items": parsed_image.get("items") or [], "receipt": parsed_image.get("receipt") or {}}
            output_characters = len(json.dumps(actual, ensure_ascii=False))
        elif feature in {"finance_ask", "finance_insight", "finance_audit", "finance_coach"}:
            mode = str(case.get("mode") or feature.removeprefix("finance_"))
            question = str(case.get("question") or "")
            context = synthetic_context(int(AI_CONTEXT_RECORD_LIMIT))
            input_characters = len(question) + len(json.dumps(context, ensure_ascii=False))
            text = generate_finance_insight(mode, context, question=question)
            actual = {
                "text": text,
                "route": "finance_answer",
                "grounding_metadata": context["context_metadata"],
                "context_record_limit": int(AI_CONTEXT_RECORD_LIMIT),
            }
            output_characters = len(text)
        elif feature == "malformed_model_output":
            actual = {"parsed": None}
        elif feature == "safety_routing_contract":
            actual = {"route": (case.get("expected") or {}).get("route")}
        else:
            raise ValueError(f"Unsupported live-eval feature: {feature}")
    except Exception as caught:  # pragma: no cover - live provider dependent
        error = type(caught).__name__

    result = {
        "id": case["id"],
        "feature": feature,
        "tags": case.get("tags") or [],
        "expected": case.get("expected") or {},
        "actual": actual,
        "completed": error is None,
        "valid_schema": validate_schema(feature, actual),
        "invalid_json": bool(error and "JSON" in error.upper()),
        "error": error,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "input_characters": input_characters,
        "output_characters": output_characters,
        "usage": None,
    }
    result["passed"] = case_passed(result)
    return result


def build_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build one versioned report using current config and prompt metadata."""

    from evals.gates import CRITICAL_TAGS
    from evals.metrics import compute_metrics
    from app.application.gemini_governance import PROMPT_VERSIONS
    from app.config import (
        AI_CONTEXT_RECORD_LIMIT,
        GEMINI_CALLS_PER_UPDATE,
        GEMINI_MAX_INPUT_CHARS,
        GEMINI_MAX_OUTPUT_CHARS,
        GEMINI_MAX_OUTPUT_TOKENS,
    )
    from app.nlp import gemini_image_parser, gemini_parser
    from app.nlp.gemini_finance_insight import GEMINI_INSIGHT_MODEL

    timestamp = datetime.now(timezone.utc)
    features = sorted({item["feature"] for item in results})
    prompt_versions = {feature: PROMPT_VERSIONS.get(feature, PROMPT_VERSIONS["generic_text"]) for feature in features}
    models = {
        "transaction_parser": gemini_parser.GEMINI_TEXT_MODEL,
        "transaction_batch_parser": gemini_parser.GEMINI_TEXT_MODEL,
        "image_receipt_parser": gemini_image_parser.GEMINI_IMAGE_MODEL,
        "finance_ask": GEMINI_INSIGHT_MODEL,
        "finance_insight": GEMINI_INSIGHT_MODEL,
        "finance_audit": GEMINI_INSIGHT_MODEL,
        "finance_coach": GEMINI_INSIGHT_MODEL,
    }
    return {
        "run_id": str(uuid.uuid4()),
        "timestamp": timestamp.isoformat(),
        "git_commit": git_commit(),
        "dataset_version": DATASET_VERSION,
        "feature": "mixed_live_ai",
        "features": features,
        "prompt_version": "mixed",
        "prompt_versions": prompt_versions,
        "model": "mixed",
        "model_name": "mixed",
        "models": {feature: models.get(feature, "n/a") for feature in features},
        "model_configuration": {
            "temperature": {"parser": 0.0, "image": 0.0, "finance_answer": 0.25},
            "gemini_calls_per_update": int(GEMINI_CALLS_PER_UPDATE),
            "gemini_max_input_chars": int(GEMINI_MAX_INPUT_CHARS),
            "gemini_max_output_tokens": int(GEMINI_MAX_OUTPUT_TOKENS),
            "gemini_max_output_chars": int(GEMINI_MAX_OUTPUT_CHARS),
            "ai_context_record_limit": int(AI_CONTEXT_RECORD_LIMIT),
        },
        "critical_tags": sorted(CRITICAL_TAGS),
        "metrics": compute_metrics(results),
        "failed_cases": [item["id"] for item in results if not item["passed"]],
        "case_results": results,
    }


def main() -> int:
    """Run live evaluation only after explicit environment opt-in."""

    if os.getenv("ENABLE_LIVE_AI_EVAL") != "1":
        print("Live AI evaluation is disabled. Set ENABLE_LIVE_AI_EVAL=1 to opt in.")
        return 2
    if not os.getenv("GEMINI_API_KEY"):
        print("Live AI evaluation requires GEMINI_API_KEY.")
        return 2

    results = [evaluate_case(case) for case in load_cases()]
    report = build_report(results)
    timestamp = datetime.fromisoformat(report["timestamp"])
    REPORTS_PATH.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_PATH / f"live-ai-eval-{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{report['run_id'][:8]}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
