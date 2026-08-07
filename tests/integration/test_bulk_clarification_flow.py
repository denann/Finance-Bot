"""Telegram translation tests for item-level bulk clarification."""

from __future__ import annotations

import asyncio
import pytest

from app.application.bulk_input import BulkItemStatus, BulkSession
from app.bot.handler_parts import bulk_flow
from app.bot.handler_parts.transaction_flow import split_user_inputs
from app.bot.pending_actions import pending_action_request_context
from tests.fakes.telegram import FakeCallbackQuery, FakeContext, FakeMessage, FakeUpdate


def _run(coro):
    return asyncio.run(coro)


def _start(text: str) -> tuple[FakeUpdate, FakeContext]:
    update = FakeUpdate(message=FakeMessage(text=text, message_id=101), user_id=1)
    context = FakeContext()
    with pending_action_request_context(context.user_data, 1, None):
        _run(bulk_flow.start_bulk_flow(update, context, split_user_inputs(text)))
    return update, context


def _callback(data: str) -> FakeUpdate:
    query = FakeCallbackQuery(data=data, message=FakeMessage(message_id=101), from_user_id=1)
    return FakeUpdate(callback_query=query, user_id=1)


def test_valid_item_survives_unknown_item_and_unknown_is_clarified() -> None:
    update, context = _start("beli kopi 10k dari Cash; kalimat benar benar tidak dikenal")
    session = context.user_data[bulk_flow.BULK_SESSION_KEY]

    assert session.items[0].status == BulkItemStatus.READY
    assert session.items[1].status == BulkItemStatus.REJECTED
    assert session.awaiting_item_id == "i2"
    assert "Tulis ulang" in str(update.message.replies[-1]["reply_markup"])
    assert "Hapus item" in str(update.message.replies[-1]["reply_markup"])


@pytest.mark.parametrize(
    ("text", "expected_reason"),
    [
        (
            "beli kopi 10k; beli nasi 20k; Budi minjem 50k",
            "missing_account",
        ),
        (
            "beli kopi 10k minjem Joko 50k",
            "missing_account",
        ),
    ],
)
def test_approved_missing_account_examples_enter_item_queue(text: str, expected_reason: str) -> None:
    _, context = _start(text)
    session = context.user_data[bulk_flow.BULK_SESSION_KEY]
    assert session.items[0].clarification_reason == expected_reason
    assert len(session.items) >= 2


def test_approved_ready_example_goes_directly_to_final_preview() -> None:
    text = "beli kopi 10k dari Cash; beli nasi 20k dari Cash; gaji masuk 8jt ke BCA"
    update, context = _start(text)

    assert bulk_flow.BULK_SESSION_KEY not in context.user_data
    assert [item["raw"] for item in context.user_data["pending_mixed"]] == split_user_inputs(text)
    markup = update.message.replies[-1]["reply_markup"]
    callbacks = [button.callback_data for row in markup.inline_keyboard for button in row]
    assert any(value.startswith("confirm:a_") for value in callbacks)


def test_debt_with_explicit_dana_remains_ready_in_bulk() -> None:
    text = "beli kopi 10k dari Cash; Budi minjem 50k dari DANA"
    _, context = _start(text)
    assert bulk_flow.BULK_SESSION_KEY not in context.user_data
    assert context.user_data["pending_mixed"][1]["parsed"]["account"] == "DANA"


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("beli kopi 10k dari Cash; 31/02/2026 beli nasi 20k dari Cash", "invalid_date"),
        ("beli kopi 10k dari Cash; beli nasi dari Cash", "missing_amount"),
        ("beli kopi 10k dari Cash; beli nasi 20k", "missing_account"),
        ("beli kopi 10k dari Cash; makan 80k bagi dua sama Budi dari DANA", "split_decision"),
        ("beli kopi 10k dari Cash; bayar ke Budi 100k", "ambiguous_parse"),
    ],
)
def test_required_bulk_issue_types_are_item_scoped(text: str, reason: str) -> None:
    _, context = _start(text)
    session = context.user_data[bulk_flow.BULK_SESSION_KEY]
    assert session.items[0].status == BulkItemStatus.READY
    assert session.items[1].clarification_reason == reason


def test_missing_amount_then_account_resolves_one_item_at_a_time(monkeypatch) -> None:
    monkeypatch.setattr(bulk_flow, "is_authorized", lambda _update: True)
    _, context = _start("beli kopi dari Cash; beli nasi 20k")
    session = context.user_data[bulk_flow.BULK_SESSION_KEY]
    assert session.awaiting_item_id == "i1"

    amount_update = FakeUpdate(message=FakeMessage(text="10k", message_id=102), user_id=1)
    _run(bulk_flow.handle_pending_bulk_text(amount_update, context, "10k"))
    session = context.user_data[bulk_flow.BULK_SESSION_KEY]
    assert session.awaiting_item_id == "i2"
    assert session.awaiting_mode == "account"

    account_update = _callback(f"bulk_acc:{session.session_id}:i2:DANA")
    with pending_action_request_context(context.user_data, 1, 101):
        _run(bulk_flow.handle_bulk_callback(account_update, context))

    mixed = context.user_data["pending_mixed"]
    assert [item["original_index"] for item in mixed] == [0, 1]
    assert mixed[0]["parsed"]["amount"] == 10_000
    assert mixed[1]["parsed"]["account"] == "DANA"


def test_rejected_item_can_be_rewritten_without_losing_valid_item(monkeypatch) -> None:
    monkeypatch.setattr(bulk_flow, "is_authorized", lambda _update: True)
    _, context = _start("beli kopi 10k dari Cash; tidak dikenal sama sekali")
    session = context.user_data[bulk_flow.BULK_SESSION_KEY]

    rewrite_update = _callback(f"bulk_rewrite:{session.session_id}:i2")
    _run(bulk_flow.handle_bulk_callback(rewrite_update, context))
    rewritten = FakeUpdate(message=FakeMessage(text="beli nasi 20k dari DANA", message_id=103), user_id=1)
    with pending_action_request_context(context.user_data, 1, None):
        _run(bulk_flow.handle_pending_bulk_text(rewritten, context, rewritten.message.text))

    mixed = context.user_data["pending_mixed"]
    assert [item["raw"] for item in mixed] == ["beli kopi 10k dari Cash", "beli nasi 20k dari DANA"]


def test_rejected_item_removal_is_explicit_and_final_preview_keeps_edit(monkeypatch) -> None:
    monkeypatch.setattr(bulk_flow, "is_authorized", lambda _update: True)
    _, context = _start("beli kopi 10k dari Cash; tidak dikenal sama sekali")
    session = context.user_data[bulk_flow.BULK_SESSION_KEY]
    remove_update = _callback(f"bulk_remove:{session.session_id}:i2")

    with pending_action_request_context(context.user_data, 1, 101):
        _run(bulk_flow.handle_bulk_callback(remove_update, context))

    assert bulk_flow.BULK_SESSION_KEY not in context.user_data
    assert len(context.user_data["pending_mixed"]) == 1
    markup = remove_update.callback_query.message.edits[-1]["reply_markup"]
    callbacks = [button.callback_data for row in markup.inline_keyboard for button in row]
    assert any(value.startswith("confirm:a_") for value in callbacks)
    assert "editflow:edit:mixed" in callbacks
    assert any(value.startswith("cancel:a_") for value in callbacks)


def test_cancel_during_clarification_invalidates_complete_batch(monkeypatch) -> None:
    monkeypatch.setattr(bulk_flow, "is_authorized", lambda _update: True)
    _, context = _start("beli kopi 10k dari Cash; tidak dikenal sama sekali")
    session = context.user_data[bulk_flow.BULK_SESSION_KEY]
    cancel_update = _callback(f"bulk_cancel:{session.session_id}")

    _run(bulk_flow.handle_bulk_callback(cancel_update, context))

    assert bulk_flow.BULK_SESSION_KEY not in context.user_data
    assert "pending_mixed" not in context.user_data
    assert "Tidak ada data yang disimpan" in cancel_update.callback_query.message.edits[-1]["text"]


def test_stale_callback_cannot_change_newer_bulk_state(monkeypatch) -> None:
    monkeypatch.setattr(bulk_flow, "is_authorized", lambda _update: True)
    _, context = _start("beli kopi 10k; beli nasi 20k dari Cash")
    before: BulkSession = context.user_data[bulk_flow.BULK_SESSION_KEY]
    before_snapshot = before
    stale_update = _callback("bulk_acc:old-session:i1:DANA")

    _run(bulk_flow.handle_bulk_callback(stale_update, context))

    assert context.user_data[bulk_flow.BULK_SESSION_KEY] == before_snapshot
    assert "kedaluwarsa" in stale_update.callback_query.message.edits[-1]["text"]


def test_bulk_classification_and_clarification_perform_no_finance_write(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(bulk_flow, "is_authorized", lambda _update: True)
    _, context = _start("beli kopi 10k dari Cash; beli nasi dari Cash")
    amount_update = FakeUpdate(message=FakeMessage(text="20k", message_id=104), user_id=1)
    with pending_action_request_context(context.user_data, 1, None):
        _run(bulk_flow.handle_pending_bulk_text(amount_update, context, "20k"))

    assert calls == []
    assert "pending_mixed" in context.user_data
