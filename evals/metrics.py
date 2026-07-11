"""Deterministic field and latency metrics for parser evaluation reports."""

from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any


ACCURACY_FIELDS = (
    "type",
    "amount",
    "account",
    "to_account",
    "category",
    "route",
)


def percentile(values: list[float], fraction: float) -> float:
    """Return a nearest-rank percentile without optional numeric libraries."""

    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate schema, field, error, tag, and latency metrics."""

    total = len(results)
    completed = [item for item in results if item.get("completed")]
    latencies = [float(item.get("latency_ms", 0)) for item in completed]
    field_totals: Counter[str] = Counter()
    field_passes: Counter[str] = Counter()
    failures_by_tag: Counter[str] = Counter()
    failures_by_field: Counter[str] = Counter()
    input_tokens = 0
    output_tokens = 0
    usage_available = False

    for item in results:
        expected = item.get("expected") or {}
        actual = item.get("actual") or {}
        failed_fields: list[str] = []
        for field in ACCURACY_FIELDS:
            if field not in expected:
                continue
            field_totals[field] += 1
            if expected[field] == actual.get(field):
                field_passes[field] += 1
            else:
                failed_fields.append(field)
                failures_by_field[field] += 1
        if not item.get("valid_schema"):
            failed_fields.append("schema")
            failures_by_field["schema"] += 1
        if failed_fields or item.get("error"):
            for tag in item.get("tags") or ["untagged"]:
                failures_by_tag[str(tag)] += 1
        usage = item.get("usage") or {}
        if usage.get("input_tokens") is not None and usage.get("output_tokens") is not None:
            usage_available = True
            input_tokens += int(usage["input_tokens"])
            output_tokens += int(usage["output_tokens"])

    def rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 6) if denominator else 0.0

    metrics: dict[str, Any] = {
        "total_cases": total,
        "completed_cases": len(completed),
        "valid_schema_rate": rate(sum(bool(item.get("valid_schema")) for item in results), total),
        "invalid_json_rate": rate(sum(bool(item.get("invalid_json")) for item in results), total),
        "error_rate": rate(sum(bool(item.get("error")) for item in results), total),
        "average_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        "p50_latency_ms": round(median(latencies), 3) if latencies else 0.0,
        "p95_latency_ms": round(percentile(latencies, 0.95), 3),
        "failure_breakdown_by_tag": dict(sorted(failures_by_tag.items())),
        "failure_breakdown_by_field": dict(sorted(failures_by_field.items())),
    }
    for field in ACCURACY_FIELDS:
        metric_name = "routing_accuracy" if field == "route" else f"{field}_accuracy"
        metrics[metric_name] = rate(field_passes[field], field_totals[field])
    metrics["destination_account_accuracy"] = metrics.pop("to_account_accuracy")
    metrics["transaction_type_accuracy"] = metrics.pop("type_accuracy")
    metrics["input_tokens"] = input_tokens if usage_available else None
    metrics["output_tokens"] = output_tokens if usage_available else None
    return metrics


def case_passed(result: dict[str, Any]) -> bool:
    """Return whether one result completed with schema and all declared fields."""

    if result.get("error") or not result.get("valid_schema"):
        return False
    expected = result.get("expected") or {}
    actual = result.get("actual") or {}
    return all(actual.get(field) == value for field, value in expected.items())
