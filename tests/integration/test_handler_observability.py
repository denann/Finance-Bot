"""Handler correlation and aggregate metric integration tests."""

from __future__ import annotations

import asyncio

from app.bot.application import atomic_bot_handler
from app.observability import current_correlation_id, metrics_snapshot, reset_metrics_for_tests
from tests.fakes.telegram import FakeContext, FakeMessage, FakeUpdate


def test_atomic_handler_binds_update_correlation_without_finance_text() -> None:
    """One Telegram update keeps one opaque correlation ID through its handler."""

    seen: dict[str, str] = {}

    async def sample_handler(_update, _context):
        seen["correlation_id"] = current_correlation_id()
        return "ok"

    reset_metrics_for_tests()
    update = FakeUpdate(message=FakeMessage(text="beli kopi 20k dari Cash"), user_id=1)
    update.update_id = 456
    result = asyncio.run(atomic_bot_handler(sample_handler)(update, FakeContext()))

    assert result == "ok"
    assert seen["correlation_id"] == "tg-456"
    snapshot = metrics_snapshot()
    assert snapshot["counters"]["telegram.handler.sample_handler.completed"] == 1
    assert "kopi" not in str(snapshot).lower()
