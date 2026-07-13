"""Offline tests for live-evaluation metrics, comparison, and gates."""

from __future__ import annotations

import json

from evals.compare_runs import compare_reports
from evals.gates import evaluate_gates, main as gates_main
from evals.metrics import compute_metrics
from evals.run_parser_eval import DATASET_VERSION, build_report, load_cases, main as run_eval_main


def _result(case_id: str, *, passed: bool, latency: float, tags: list[str] | None = None) -> dict:
    """Build one compact synthetic evaluation result."""

    expected = {"type": "expense", "amount": 20_000, "route": "transaction"}
    actual = dict(expected) if passed else {"type": "income", "amount": 20_000, "route": "transaction"}
    return {
        "id": case_id,
        "tags": tags or [],
        "expected": expected,
        "actual": actual,
        "completed": True,
        "valid_schema": True,
        "invalid_json": False,
        "error": None,
        "latency_ms": latency,
        "input_characters": 20,
        "output_characters": 40,
        "passed": passed,
        "usage": None,
    }


def test_metrics_do_not_fabricate_usage_or_cost() -> None:
    """Missing provider usage remains explicit instead of becoming zero cost."""

    metrics = compute_metrics([_result("pass", passed=True, latency=100), _result("fail", passed=False, latency=300)])
    assert metrics["total_cases"] == 2
    assert metrics["passed_cases"] == 1
    assert metrics["failed_cases"] == 1
    assert metrics["transaction_type_accuracy"] == 0.5
    assert metrics["amount_accuracy"] == 1.0
    assert metrics["p50_latency_ms"] == 200.0
    assert metrics["input_characters"] == 40
    assert metrics["output_characters"] == 80
    assert metrics["input_tokens"] is None
    assert metrics["output_tokens"] is None
    assert "estimated_cost" not in metrics


def test_compare_reports_lists_case_transitions_and_metric_deltas() -> None:
    """Comparison identifies both regressions and recovered cases."""

    baseline = {
        "metrics": {"valid_schema_rate": 1.0, "p95_latency_ms": 100},
        "case_results": [{"id": "a", "passed": True}, {"id": "b", "passed": False}],
    }
    candidate = {
        "metrics": {"valid_schema_rate": 0.9, "p95_latency_ms": 120},
        "case_results": [{"id": "a", "passed": False}, {"id": "b", "passed": True}],
    }
    comparison = compare_reports(baseline, candidate)
    assert comparison["metric_deltas"]["valid_schema_rate"] == -0.1
    assert comparison["regressed_cases"] == ["a"]
    assert comparison["improved_cases"] == ["b"]
    assert comparison["pass_to_fail_cases"] == ["a"]
    assert comparison["fail_to_pass_cases"] == ["b"]
    assert comparison["schema_regressions"] == []
    assert comparison["latency_change"]["p95_latency_ms"] == 20.0
    assert comparison["metric_degradations"]["valid_schema_rate"] == -0.1
    assert comparison["metric_degradations"]["p95_latency_ms"] == 20.0


def test_critical_case_regression_fails_gate() -> None:
    """A previously passing critical transfer case cannot become optional."""

    baseline = {
        "metrics": {"valid_schema_rate": 1.0, "invalid_json_rate": 0.0, "routing_accuracy": 1.0},
        "case_results": [{"id": "critical", "passed": True, "tags": ["transfer"]}],
    }
    candidate = {
        "metrics": {"valid_schema_rate": 1.0, "invalid_json_rate": 0.0, "routing_accuracy": 1.0},
        "case_results": [{"id": "critical", "passed": False, "tags": ["transfer"]}],
    }
    assert evaluate_gates(baseline, candidate) == ["critical cases regressed: critical"]


def test_gate_cli_returns_nonzero_for_synthetic_regression(tmp_path) -> None:
    """Gate mode must fail closed when a critical passing case regresses."""

    baseline = {
        "metrics": {"valid_schema_rate": 1.0, "invalid_json_rate": 0.0, "routing_accuracy": 1.0},
        "case_results": [{"id": "critical", "passed": True, "tags": ["multi_input"]}],
    }
    candidate = {
        "metrics": {"valid_schema_rate": 1.0, "invalid_json_rate": 0.0, "routing_accuracy": 1.0},
        "case_results": [{"id": "critical", "passed": False, "tags": ["multi_input"]}],
    }
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

    assert gates_main([str(baseline_path), str(candidate_path)]) == 1


def test_live_eval_is_default_disabled_and_requires_credentials(monkeypatch) -> None:
    """The live runner exits before importing provider paths unless explicitly enabled."""

    monkeypatch.delenv("ENABLE_LIVE_AI_EVAL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert run_eval_main() == 2

    monkeypatch.setenv("ENABLE_LIVE_AI_EVAL", "1")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert run_eval_main() == 2


def test_live_eval_dataset_and_report_metadata_are_phase_current() -> None:
    """Dataset and report metadata cover Phase 0-5 contracts without credentials."""

    cases = load_cases()
    tags = {tag for case in cases for tag in case.get("tags", [])}
    features = {case.get("feature") for case in cases}

    assert DATASET_VERSION == "phase0-5-live-ai-v1"
    assert {"transfer", "debt", "split_bill", "invalid_date", "future_intent", "cancellation", "multi_input"}.issubset(tags)
    assert {"transaction_parser", "transaction_batch_parser", "image_receipt_parser", "finance_ask", "finance_audit", "finance_coach"}.issubset(features)

    report = build_report([
        {
            "id": "sample",
            "feature": "transaction_parser",
            "tags": ["transfer"],
            "expected": {"type": "transfer"},
            "actual": {"type": "transfer", "amount": 1, "date": "2026-07-13", "category": None},
            "completed": True,
            "valid_schema": True,
            "invalid_json": False,
            "error": None,
            "latency_ms": 1.0,
            "input_characters": 10,
            "output_characters": 20,
            "usage": None,
            "passed": True,
        }
    ])
    assert report["dataset_version"] == DATASET_VERSION
    assert report["prompt_versions"]["transaction_parser"] == "transaction-parser-v1"
    assert report["model_configuration"]["gemini_calls_per_update"] == 1
    assert "transfer" in report["critical_tags"]
