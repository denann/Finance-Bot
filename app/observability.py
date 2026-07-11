"""Structured redacted events, correlation context, and in-memory metrics."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Iterator

from app.config import LOG_LEVEL


LOGGER_NAME = "finance_bot"
REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = {
    "token",
    "secret",
    "password",
    "credential",
    "private_key",
    "api_key",
    "service_account",
    "prompt",
    "raw_input",
    "message_text",
    "finance_text",
    "payload",
}
SECRET_PATTERNS = (
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
)


_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")
_metrics_lock = threading.Lock()
_metric_counters: dict[str, int] = {}
_metric_durations: dict[str, dict[str, float]] = {}


def configure_logging() -> logging.Logger:
    """Configure the application logger for one JSON event per line."""

    logger = logging.getLogger(LOGGER_NAME)
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def new_correlation_id(prefix: str = "op") -> str:
    """Create a short opaque correlation ID without user or finance data."""

    clean_prefix = re.sub(r"[^a-zA-Z0-9_-]", "", str(prefix or "op"))[:16] or "op"
    return f"{clean_prefix}-{uuid.uuid4().hex[:12]}"


def current_correlation_id() -> str:
    """Return the current request correlation ID."""

    return _correlation_id.get()


@contextmanager
def correlation_scope(correlation_id: str | None = None) -> Iterator[str]:
    """Bind one correlation ID to nested handler and service events."""

    value = str(correlation_id or new_correlation_id()).strip() or new_correlation_id()
    token = _correlation_id.set(value)
    try:
        yield value
    finally:
        _correlation_id.reset(token)


def redact_value(key: str, value: Any) -> Any:
    """Remove secret-like and raw finance values from structured event fields."""

    normalized_key = str(key or "").strip().lower()
    if any(part in normalized_key for part in SENSITIVE_KEY_PARTS):
        return REDACTED
    if isinstance(value, dict):
        return {str(child_key): redact_value(str(child_key), child_value) for child_key, child_value in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact_value(normalized_key, item) for item in value]
    if isinstance(value, str):
        sanitized = value
        for pattern in SECRET_PATTERNS:
            sanitized = pattern.sub(REDACTED, sanitized)
        return sanitized[:500]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:200]


def emit_event(event: str, *, level: int = logging.INFO, **fields: Any) -> dict[str, Any]:
    """Emit one redacted JSON event and return the serialized structure."""

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": str(event or "unknown_event"),
        "correlation_id": current_correlation_id(),
    }
    for key, value in fields.items():
        record[str(key)] = redact_value(str(key), value)
    configure_logging().log(level, json.dumps(record, ensure_ascii=True, sort_keys=True))
    return record


def increment_metric(name: str, amount: int = 1) -> None:
    """Increment one bounded-name in-memory counter."""

    metric_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(name or "unknown"))[:100]
    with _metrics_lock:
        _metric_counters[metric_name] = _metric_counters.get(metric_name, 0) + int(amount)


def observe_duration(name: str, duration_ms: float) -> None:
    """Record count, total, and max duration without storing request labels."""

    metric_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(name or "unknown"))[:100]
    value = max(0.0, float(duration_ms))
    with _metrics_lock:
        bucket = _metric_durations.setdefault(metric_name, {"count": 0.0, "total_ms": 0.0, "max_ms": 0.0})
        bucket["count"] += 1
        bucket["total_ms"] += value
        bucket["max_ms"] = max(bucket["max_ms"], value)


def metrics_snapshot() -> dict[str, Any]:
    """Return a defensive aggregate snapshot without user-level labels."""

    with _metrics_lock:
        return {
            "counters": dict(_metric_counters),
            "durations": {name: dict(values) for name, values in _metric_durations.items()},
        }


def reset_metrics_for_tests() -> None:
    """Clear process metrics for deterministic tests only."""

    with _metrics_lock:
        _metric_counters.clear()
        _metric_durations.clear()


def monotonic_ms() -> float:
    """Return a monotonic millisecond value for latency measurement."""

    return time.perf_counter() * 1000.0
