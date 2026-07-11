"""Structured event redaction, correlation, and aggregate metric tests."""

from __future__ import annotations

from app.observability import (
    REDACTED,
    correlation_scope,
    emit_event,
    increment_metric,
    metrics_snapshot,
    observe_duration,
    reset_metrics_for_tests,
)


def test_event_redacts_credentials_and_raw_finance_payload() -> None:
    """Structured logs retain operational metadata but no secret or raw payload."""

    with correlation_scope("test-correlation"):
        record = emit_event(
            "parser_completed",
            model="gemini-test",
            api_key="AIza" + "x" * 30,
            raw_input="beli kopi 20k dari Cash",
            nested={"telegram_token": "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"},
        )

    assert record["correlation_id"] == "test-correlation"
    assert record["model"] == "gemini-test"
    assert record["api_key"] == REDACTED
    assert record["raw_input"] == REDACTED
    assert record["nested"]["telegram_token"] == REDACTED


def test_metrics_are_aggregate_and_resettable() -> None:
    """Metrics expose no user labels or finance text."""

    reset_metrics_for_tests()
    increment_metric("gemini.calls")
    increment_metric("gemini.calls")
    observe_duration("gemini.latency", 125.5)
    observe_duration("gemini.latency", 74.5)
    snapshot = metrics_snapshot()

    assert snapshot["counters"]["gemini.calls"] == 2
    assert snapshot["durations"]["gemini.latency"] == {
        "count": 2.0,
        "total_ms": 200.0,
        "max_ms": 125.5,
    }
    assert "user" not in str(snapshot).lower()
