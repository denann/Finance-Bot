"""Lifecycle and immutable payload tests for one-shot preview actions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.bot.pending_actions import (
    PendingActionError,
    bind_action_message,
    cancel_pending_action,
    consume_pending_action,
    create_pending_action,
    get_pending_action,
)


NOW = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)


def _create(user_data: dict, payload: dict, **kwargs):
    return create_pending_action(
        user_data,
        owner_user_id=123,
        flow_type="single",
        payload=payload,
        now=NOW,
        **kwargs,
    )


def test_preview_a_and_b_keep_independent_immutable_payloads() -> None:
    """Confirming A after creating B must still return A's snapshot."""

    user_data: dict = {}
    payload_a = {"user_state": {"pending_parsed": {"description": "A"}}}
    action_a = _create(user_data, payload_a)
    payload_a["user_state"]["pending_parsed"]["description"] = "mutated"
    action_b = _create(user_data, {"user_state": {"pending_parsed": {"description": "B"}}})

    consumed_a = consume_pending_action(user_data, action_a["action_id"], owner_user_id=123, now=NOW)
    assert consumed_a["payload"]["user_state"]["pending_parsed"]["description"] == "A"
    assert get_pending_action(user_data, action_b["action_id"])["status"] == "pending"


def test_action_can_be_consumed_only_once() -> None:
    """A duplicate confirmation cannot pass the compare-and-consume gate."""

    user_data: dict = {}
    action = _create(user_data, {"value": 1})
    consume_pending_action(user_data, action["action_id"], owner_user_id=123, now=NOW)

    with pytest.raises(PendingActionError) as error:
        consume_pending_action(user_data, action["action_id"], owner_user_id=123, now=NOW)
    assert error.value.code == "consumed"


def test_canceled_action_cannot_be_confirmed_and_confirmed_action_cannot_be_canceled() -> None:
    """Canceled and consumed actions are terminal states."""

    user_data: dict = {}
    canceled = _create(user_data, {"value": "cancel"})
    cancel_pending_action(user_data, canceled["action_id"], owner_user_id=123, now=NOW)
    with pytest.raises(PendingActionError) as canceled_error:
        consume_pending_action(user_data, canceled["action_id"], owner_user_id=123, now=NOW)
    assert canceled_error.value.code == "canceled"

    consumed = _create(user_data, {"value": "confirm"})
    consume_pending_action(user_data, consumed["action_id"], owner_user_id=123, now=NOW)
    with pytest.raises(PendingActionError) as consumed_error:
        cancel_pending_action(user_data, consumed["action_id"], owner_user_id=123, now=NOW)
    assert consumed_error.value.code == "consumed"


def test_expired_wrong_user_and_wrong_message_are_rejected() -> None:
    """TTL, owner, and message binding are all enforced before consumption."""

    user_data: dict = {}
    expired = _create(user_data, {"value": 1}, ttl_seconds=1)
    with pytest.raises(PendingActionError) as expired_error:
        consume_pending_action(user_data, expired["action_id"], owner_user_id=123, now=NOW + timedelta(seconds=2))
    assert expired_error.value.code == "expired"

    owned = _create(user_data, {"value": 2})
    with pytest.raises(PendingActionError) as owner_error:
        consume_pending_action(user_data, owned["action_id"], owner_user_id=999, now=NOW)
    assert owner_error.value.code == "wrong_owner"

    bound = _create(user_data, {"value": 3})
    bind_action_message(user_data, bound["action_id"], 42)
    with pytest.raises(PendingActionError) as message_error:
        consume_pending_action(user_data, bound["action_id"], owner_user_id=123, message_id=43, now=NOW)
    assert message_error.value.code == "wrong_message"


def test_restart_or_lost_store_fails_safe() -> None:
    """An action lost after restart is rejected instead of reading new state."""

    with pytest.raises(PendingActionError) as error:
        consume_pending_action({}, "a_missing", owner_user_id=123, now=NOW)
    assert error.value.code == "not_found"
