"""Explicit Asia/Jakarta business clock with deterministic test overrides."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timezone
from typing import Iterator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import APP_TIMEZONE


try:
    BUSINESS_TIMEZONE = ZoneInfo(APP_TIMEZONE)
except ZoneInfoNotFoundError as exc:
    raise ValueError(f"APP_TIMEZONE tidak valid: {APP_TIMEZONE}") from exc


_frozen_business_time: ContextVar[datetime | None] = ContextVar(
    "frozen_business_time",
    default=None,
)


def business_now() -> datetime:
    """Return one timezone-aware business timestamp in the configured zone.

    Returns:
        A timezone-aware datetime. Tests may override the value through
        ``freeze_business_time`` without changing the host timezone.

    Side effects:
        Reads the system UTC clock only when no test override is active.
    """

    frozen = _frozen_business_time.get()
    if frozen is not None:
        return frozen.astimezone(BUSINESS_TIMEZONE)
    return datetime.now(timezone.utc).astimezone(BUSINESS_TIMEZONE)


def business_today() -> date:
    """Return the current business date in the configured timezone."""

    return business_now().date()


@contextmanager
def freeze_business_time(value: datetime) -> Iterator[None]:
    """Temporarily override the business clock for deterministic tests.

    Args:
        value: A timezone-aware datetime. Naive values are rejected because
            their source timezone would otherwise be ambiguous.

    Side effects:
        Sets one context-local clock override and restores it on exit.
    """

    if value.tzinfo is None:
        raise ValueError("Frozen business time harus timezone-aware.")
    token = _frozen_business_time.set(value.astimezone(BUSINESS_TIMEZONE))
    try:
        yield
    finally:
        _frozen_business_time.reset(token)
