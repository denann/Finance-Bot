"""Central live-evaluation regression thresholds and gate evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


THRESHOLDS = {
    "valid_schema_rate_max_decrease": 0.0,
    "invalid_json_rate_max_increase": 0.0,
    "routing_accuracy_max_decrease": 0.02,
    "critical_case_regressions_allowed": 0,
}

CRITICAL_TAGS = {
    "transfer",
    "debt",
    "split_bill",
    "invalid_date",
    "future_intent",
    "cancellation",
    "confirmation_security",
    "multi_input",
}


def evaluate_gates(baseline: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    """Return human-readable gate failures for one candidate report."""

    failures: list[str] = []
    baseline_metrics = baseline.get("metrics") or {}
    candidate_metrics = candidate.get("metrics") or {}

    valid_delta = float(candidate_metrics.get("valid_schema_rate", 0)) - float(baseline_metrics.get("valid_schema_rate", 0))
    if valid_delta < -THRESHOLDS["valid_schema_rate_max_decrease"]:
        failures.append(f"valid_schema_rate decreased by {abs(valid_delta):.6f}")

    invalid_delta = float(candidate_metrics.get("invalid_json_rate", 0)) - float(baseline_metrics.get("invalid_json_rate", 0))
    if invalid_delta > THRESHOLDS["invalid_json_rate_max_increase"]:
        failures.append(f"invalid_json_rate increased by {invalid_delta:.6f}")

    routing_delta = float(candidate_metrics.get("routing_accuracy", 0)) - float(baseline_metrics.get("routing_accuracy", 0))
    if routing_delta < -THRESHOLDS["routing_accuracy_max_decrease"]:
        failures.append(f"routing_accuracy decreased by {abs(routing_delta):.6f}")

    baseline_pass = {item["id"] for item in baseline.get("case_results", []) if item.get("passed")}
    critical_regressions = []
    for item in candidate.get("case_results", []):
        tags = set(item.get("tags") or [])
        if item.get("id") in baseline_pass and not item.get("passed") and tags.intersection(CRITICAL_TAGS):
            critical_regressions.append(item["id"])
    if len(critical_regressions) > THRESHOLDS["critical_case_regressions_allowed"]:
        failures.append("critical cases regressed: " + ", ".join(sorted(critical_regressions)))
    return failures


def main(argv: list[str] | None = None) -> int:
    """Evaluate two JSON reports and return non-zero when a gate fails."""

    args = list(argv or sys.argv[1:])
    if len(args) != 2:
        print("Usage: python evals/gates.py baseline.json candidate.json")
        return 2
    baseline = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    candidate = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    failures = evaluate_gates(baseline, candidate)
    if failures:
        print("Gate failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
