"""Offline tests for live-evaluation metrics, comparison, and gates."""

from __future__ import annotations

from evals.compare_runs import compare_reports
from evals.gates import evaluate_gates
from evals.metrics import compute_metrics


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
        "passed": passed,
        "usage": None,
    }


def test_metrics_do_not_fabricate_usage_or_cost() -> None:
    """Missing provider usage remains explicit instead of becoming zero cost."""

    metrics = compute_metrics([_result("pass", passed=True, latency=100), _result("fail", passed=False, latency=300)])
    assert metrics["total_cases"] == 2
    assert metrics["transaction_type_accuracy"] == 0.5
    assert metrics["amount_accuracy"] == 1.0
    assert metrics["p50_latency_ms"] == 200.0
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
