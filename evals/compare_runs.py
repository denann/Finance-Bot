"""Compare two parser evaluation reports without contacting any service."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def compare_reports(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Return metric deltas and case pass/fail transitions."""

    baseline_metrics = baseline.get("metrics") or {}
    candidate_metrics = candidate.get("metrics") or {}
    deltas = {}
    for key in sorted(set(baseline_metrics).intersection(candidate_metrics)):
        old = baseline_metrics[key]
        new = candidate_metrics[key]
        if isinstance(old, (int, float)) and isinstance(new, (int, float)):
            deltas[key] = round(float(new) - float(old), 6)

    baseline_cases = {item["id"]: bool(item.get("passed")) for item in baseline.get("case_results", [])}
    candidate_cases = {item["id"]: bool(item.get("passed")) for item in candidate.get("case_results", [])}
    regressed = sorted(case_id for case_id, passed in baseline_cases.items() if passed and not candidate_cases.get(case_id, False))
    improved = sorted(case_id for case_id, passed in baseline_cases.items() if not passed and candidate_cases.get(case_id, False))

    baseline_by_id = {item["id"]: item for item in baseline.get("case_results", [])}
    candidate_by_id = {item["id"]: item for item in candidate.get("case_results", [])}
    schema_regressions = sorted(
        case_id
        for case_id, item in baseline_by_id.items()
        if item.get("valid_schema") and not (candidate_by_id.get(case_id) or {}).get("valid_schema")
    )
    critical_tags = set(candidate.get("critical_tags") or baseline.get("critical_tags") or [])
    critical_tag_regressions = sorted(
        case_id
        for case_id in regressed
        if set((candidate_by_id.get(case_id) or baseline_by_id.get(case_id) or {}).get("tags") or []).intersection(critical_tags)
    )
    latency_change = {
        key: deltas[key]
        for key in ("average_latency_ms", "p50_latency_ms", "p95_latency_ms")
        if key in deltas
    }

    lower_is_better_markers = ("latency", "error_rate", "invalid_json_rate")
    metric_improvements = {}
    metric_degradations = {}
    for key, value in deltas.items():
        lower_is_better = any(marker in key for marker in lower_is_better_markers)
        if (lower_is_better and value < 0) or (not lower_is_better and value > 0):
            metric_improvements[key] = value
        elif (lower_is_better and value > 0) or (not lower_is_better and value < 0):
            metric_degradations[key] = value
    return {
        "metric_deltas": deltas,
        "metric_improvements": metric_improvements,
        "metric_degradations": metric_degradations,
        "regressed_cases": regressed,
        "improved_cases": improved,
        "pass_to_fail_cases": regressed,
        "fail_to_pass_cases": improved,
        "schema_regressions": schema_regressions,
        "critical_tag_regressions": critical_tag_regressions,
        "latency_change": latency_change,
    }


def main(argv: list[str] | None = None) -> int:
    """Print one JSON comparison for two report paths."""

    args = list(argv or sys.argv[1:])
    if len(args) != 2:
        print("Usage: python evals/compare_runs.py baseline.json candidate.json")
        return 2
    baseline = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    candidate = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    print(json.dumps(compare_reports(baseline, candidate), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
