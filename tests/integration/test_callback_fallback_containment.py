"""Regression coverage for the contained legacy callback fallback."""

from __future__ import annotations

import asyncio

from app.bot import callback_contracts
from app.bot.handler_parts import callback_dispatcher
from tests.fakes.telegram import FakeCallbackQuery, FakeContext, FakeUpdate


def test_audited_legacy_inventory_accepts_known_and_rejects_unknown_data() -> None:
    assert callback_contracts.is_legacy_callback_data("confirm:a_example")
    assert callback_contracts.is_legacy_callback_data("receipt:all")
    assert not callback_contracts.is_legacy_callback_data("bulk_acc:session:item:Cash")
    assert not callback_contracts.is_legacy_callback_data("unknown:write")


def test_dispatcher_routes_known_legacy_callback_without_changing_data(monkeypatch) -> None:
    seen: list[str] = []

    async def fake_legacy(update, context) -> None:
        del context
        seen.append(update.callback_query.data)

    monkeypatch.setattr(callback_dispatcher, "legacy_callback_handler", fake_legacy)
    update = FakeUpdate(callback_query=FakeCallbackQuery("confirm:a_example"))

    asyncio.run(callback_dispatcher.callback_handler(update, FakeContext()))

    assert seen == ["confirm:a_example"]


def test_unknown_callback_is_rejected_before_legacy_fallback(monkeypatch) -> None:
    legacy_calls: list[str] = []

    async def fake_legacy(update, context) -> None:
        del context
        legacy_calls.append(update.callback_query.data)

    monkeypatch.setattr(callback_dispatcher, "legacy_callback_handler", fake_legacy)
    monkeypatch.setattr(callback_dispatcher, "is_authorized", lambda update: True)
    update = FakeUpdate(callback_query=FakeCallbackQuery("unknown:write"))
    context = FakeContext(user_data={"pending_parsed": {"amount": 10_000}})

    asyncio.run(callback_dispatcher.callback_handler(update, context))

    assert legacy_calls == []
    assert context.user_data == {"pending_parsed": {"amount": 10_000}}
    assert len(update.callback_query.message.edits) == 2
    assert "Memproses" in update.callback_query.message.edits[0]["text"]
    assert update.callback_query.message.edits[-1]["text"] == "❌ Tombol tidak dikenali atau sesi sudah tidak valid."
