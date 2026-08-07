"""Item-level bulk clarification state tests."""

from __future__ import annotations

import pytest

from app.application.bulk_input import (
    BulkItemStatus,
    StaleBulkSession,
    assert_current_target,
    await_rewrite,
    cancel_bulk_session,
    create_bulk_session,
    current_issue,
    make_bulk_item,
    remove_bulk_item,
    replace_bulk_item,
    resolve_bulk_item,
    result_for_session,
)
from app.application.results import ClarificationRequired, PreviewReady


def _item(index: int, *, kind: str = "transaction", amount: float = 10_000, **flags):
    legacy = {"kind": kind, "parsed": {"type": "expense", "amount": amount}, "raw": f"item {index}"}
    return make_bulk_item(
        item_id=f"i{index + 1}",
        original_index=index,
        raw_input=legacy["raw"],
        legacy_item=legacy,
        **flags,
    )


def test_valid_item_is_preserved_when_an_unknown_item_is_rejected() -> None:
    valid = _item(0)
    unknown = make_bulk_item(
        item_id="i2", original_index=1, raw_input="???", legacy_item={"kind": "failed", "parsed": {}},
    )
    session = create_bulk_session([valid, unknown], "s1")
    result = result_for_session(session)

    assert isinstance(result, ClarificationRequired)
    assert result.payload["session"].items[0].status == BulkItemStatus.READY
    assert result.payload["item"].item_id == "i2"


@pytest.mark.parametrize(
    ("flags", "reason"),
    [
        ({"invalid_date": True}, "invalid_date"),
        ({"needs_account": True}, "missing_account"),
        ({"needs_split_decision": True}, "split_decision"),
        ({"safety_requires_clarification": True}, "ambiguous_parse"),
    ],
)
def test_item_level_reasons_are_explicit(flags: dict, reason: str) -> None:
    session = create_bulk_session([_item(0), _item(1, **flags)], "s1")
    assert current_issue(session).clarification_reason == reason


def test_missing_amount_is_resolved_without_changing_other_items() -> None:
    missing = _item(0, kind="missing_amount", amount=0)
    ready = _item(1)
    session = result_for_session(create_bulk_session([missing, ready], "s1")).payload["session"]
    resolved = resolve_bulk_item(
        session,
        "i1",
        parsed_payload={"type": "expense", "amount": 25_000},
        kind="transaction",
        resolved_field="amount",
    )

    assert resolved.items[0].parsed_payload["amount"] == 25_000
    assert resolved.items[1] == ready


def test_multiple_issues_are_queued_in_original_order() -> None:
    session = create_bulk_session([
        _item(2, invalid_date=True),
        _item(0, needs_account=True),
        _item(1, kind="missing_amount", amount=0),
    ], "s1")
    first = result_for_session(session).payload["session"]
    assert first.awaiting_item_id == "i1"

    first_resolved = resolve_bulk_item(
        first, "i1", parsed_payload={"type": "expense", "amount": 10_000, "account": "Cash"}, resolved_field="account",
    )
    second = result_for_session(first_resolved).payload["session"]
    assert second.awaiting_item_id == "i2"


def test_rewrite_and_remove_are_explicit_state_transitions() -> None:
    rejected = _item(0, invalid_date=True)
    waiting = result_for_session(create_bulk_session([rejected, _item(1)], "s1")).payload["session"]
    rewrite = await_rewrite(waiting, "i1")
    assert rewrite.awaiting_mode == "rewrite_text"

    replacement = _item(0)
    replaced = replace_bulk_item(rewrite, replacement)
    removed = remove_bulk_item(
        result_for_session(create_bulk_session([rejected, _item(1)], "s2")).payload["session"],
        "i1",
    )
    assert replaced.items[0].status == BulkItemStatus.READY
    assert removed.items[0].status == BulkItemStatus.REMOVED


def test_cancel_invalidates_complete_batch() -> None:
    session = cancel_bulk_session(create_bulk_session([_item(0), _item(1)], "s1"))
    assert session.cancelled is True
    with pytest.raises(StaleBulkSession):
        assert_current_target(session, "s1")


def test_stale_callback_cannot_target_new_session_or_item() -> None:
    waiting = result_for_session(create_bulk_session([_item(0, needs_account=True)], "new")).payload["session"]
    with pytest.raises(StaleBulkSession):
        assert_current_target(waiting, "old", "i1")
    with pytest.raises(StaleBulkSession):
        assert_current_target(waiting, "new", "i2")


def test_final_preview_preserves_original_order_and_has_no_mutation() -> None:
    mutations: list[dict] = []
    session = create_bulk_session([_item(2), _item(0), _item(1)], "s1")
    result = result_for_session(session)

    assert isinstance(result, PreviewReady)
    assert [item["original_index"] for item in result.payload["mixed_items"]] == [0, 1, 2]
    assert mutations == []

