"""Structured event redaction, correlation, and aggregate metric tests."""

from __future__ import annotations

import json
import logging

import pytest

import app.observability as observability
from app.observability import (
    REDACTED,
    configure_logging,
    correlation_scope,
    emit_event,
    emit_transaction_saved,
    increment_metric,
    metrics_snapshot,
    observe_duration,
    reset_metrics_for_tests,
)


def _clear_observability_handlers() -> None:
    logger = logging.getLogger(observability.LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


@pytest.fixture(autouse=True)
def clean_observability_handlers():
    _clear_observability_handlers()
    yield
    _clear_observability_handlers()


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


def test_transaction_trace_keeps_raw_input_private_until_opted_in(monkeypatch: pytest.MonkeyPatch) -> None:
    """Transaction IDs remain traceable while finance text needs explicit opt-in."""

    monkeypatch.setattr(observability, "LOG_INCLUDE_FINANCE_DATA", False)
    record = emit_transaction_saved("txn-123", "beli kopi 25rb dari Cash")
    assert record["transaction_id"] == "txn-123"
    assert record["raw_input"] == REDACTED

    monkeypatch.setattr(observability, "LOG_INCLUDE_FINANCE_DATA", True)
    opted_in = emit_transaction_saved("txn-123", "beli kopi 25rb dari Cash")
    assert opted_in["raw_input"] == "beli kopi 25rb dari Cash"

    protected = emit_event("test", api_key="AIza" + "x" * 30)
    assert protected["api_key"] == REDACTED


def test_configure_logging_appends_json_events_to_file(tmp_path, monkeypatch) -> None:
    """LOG_FILE keeps terminal logging and appends structured events to disk."""

    log_path = tmp_path / "finance_bot.log"
    monkeypatch.setattr(observability, "LOG_FILE", str(log_path))

    configure_logging()
    with correlation_scope("file-log-test"):
        emit_event("file_logging_ready", raw_input="beli kopi 20k dari Cash")

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "file_logging_ready"
    assert record["correlation_id"] == "file-log-test"
    assert record["raw_input"] == REDACTED
    assert "kopi" not in lines[0].lower()


def test_configure_logging_does_not_duplicate_file_handlers(tmp_path, monkeypatch) -> None:
    """Repeated configure calls keep one handler per configured log file."""

    log_path = tmp_path / "finance_bot.log"
    monkeypatch.setattr(observability, "LOG_FILE", str(log_path))

    configure_logging()
    configure_logging()
    with correlation_scope("file-log-single-handler"):
        emit_event("single_file_handler")

    assert len(log_path.read_text(encoding="utf-8").splitlines()) == 1
