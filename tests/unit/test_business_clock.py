"""Timezone-explicit business clock tests around Jakarta day boundaries."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.clock import BUSINESS_TIMEZONE, business_now, business_today, freeze_business_time


def test_utc_evening_rolls_into_next_jakarta_business_date() -> None:
    """00:30 WIB must use the next Jakarta date even when UTC is still prior day."""

    utc_value = datetime(2026, 7, 10, 17, 30, tzinfo=timezone.utc)
    with freeze_business_time(utc_value):
        assert business_now().tzinfo == BUSINESS_TIMEZONE
        assert business_now().strftime("%Y-%m-%d %H:%M") == "2026-07-11 00:30"
        assert business_today().isoformat() == "2026-07-11"


def test_frozen_clock_restores_outer_context() -> None:
    """Nested deterministic clocks restore the previous business time."""

    first = datetime(2026, 12, 31, 16, 0, tzinfo=timezone.utc)
    second = datetime(2026, 12, 31, 18, 0, tzinfo=timezone.utc)
    with freeze_business_time(first):
        assert business_today().isoformat() == "2026-12-31"
        with freeze_business_time(second):
            assert business_today().isoformat() == "2027-01-01"
        assert business_today().isoformat() == "2026-12-31"


def test_naive_frozen_time_is_rejected() -> None:
    """Tests must state the source timezone instead of relying on host locale."""

    with pytest.raises(ValueError, match="timezone-aware"):
        with freeze_business_time(datetime(2026, 7, 10, 12, 0)):
            pass
