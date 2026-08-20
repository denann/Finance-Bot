import pytest

from app.bot.pending_actions import (
    PendingActionError,
    consume_pending_action,
    create_pending_action,
    restore_pending_state,
)


def test_save_all_confirmation_is_consumable_once_and_restores_exact_preview_payload():
    user_data = {"pending_bulk_edit_staged": {"entries": [{"txn_id": "txn_1", "updates": {"amount": 20}}]}}
    action = create_pending_action(
        user_data,
        owner_user_id=77,
        flow_type="edit_txns_bulk_staged",
        payload={"legacy_target": "edit_txns_bulk_staged", "user_state": {"pending_bulk_edit_staged": user_data["pending_bulk_edit_staged"]}},
        preview_message_id=123,
    )

    # Mutable flow state may change after preview; the confirmation returns the
    # immutable approved snapshot, not the newer slot.
    user_data["pending_bulk_edit_staged"]["entries"][0]["updates"]["amount"] = 999
    consumed = consume_pending_action(
        user_data,
        action["action_id"],
        owner_user_id=77,
        message_id=123,
        expected_flow="edit_txns_bulk_staged",
    )
    restore_pending_state(user_data, consumed["payload"]["user_state"])
    assert user_data["pending_bulk_edit_staged"]["entries"][0]["updates"]["amount"] == 20

    with pytest.raises(PendingActionError):
        consume_pending_action(
            user_data,
            action["action_id"],
            owner_user_id=77,
            message_id=123,
            expected_flow="edit_txns_bulk_staged",
        )


def test_delete_confirmation_is_also_one_shot_and_message_bound():
    user_data = {"pending_delete_refs": {"selected_txn_ids": ["txn_a", "txn_b"]}}
    action = create_pending_action(
        user_data,
        owner_user_id=77,
        flow_type="delete_txns",
        payload={"legacy_target": "delete_txns", "user_state": {"pending_delete_refs": user_data["pending_delete_refs"]}},
        preview_message_id=456,
    )

    with pytest.raises(PendingActionError):
        consume_pending_action(user_data, action["action_id"], owner_user_id=77, message_id=999, expected_flow="delete_txns")

    first = consume_pending_action(user_data, action["action_id"], owner_user_id=77, message_id=456, expected_flow="delete_txns")
    assert first["payload"]["user_state"]["pending_delete_refs"]["selected_txn_ids"] == ["txn_a", "txn_b"]
    with pytest.raises(PendingActionError):
        consume_pending_action(user_data, action["action_id"], owner_user_id=77, message_id=456, expected_flow="delete_txns")


def test_child_flow_cleanup_cancels_only_transaction_mutation_actions():
    from app.bot.pending_actions import cancel_pending_actions_by_flow

    user_data = {}
    edit = create_pending_action(user_data, owner_user_id=77, flow_type="edit_txn", payload={})
    delete = create_pending_action(user_data, owner_user_id=77, flow_type="delete_txns", payload={})
    unrelated = create_pending_action(user_data, owner_user_id=77, flow_type="set_balance", payload={})

    canceled = cancel_pending_actions_by_flow(user_data, {"edit_txn", "delete_txns"})
    assert canceled == 2
    with pytest.raises(PendingActionError):
        consume_pending_action(user_data, edit["action_id"], owner_user_id=77, expected_flow="edit_txn")
    with pytest.raises(PendingActionError):
        consume_pending_action(user_data, delete["action_id"], owner_user_id=77, expected_flow="delete_txns")
    # A non-transaction confirmation remains pending and consumable.
    consumed = consume_pending_action(user_data, unrelated["action_id"], owner_user_id=77, expected_flow="set_balance")
    assert consumed["flow_type"] == "set_balance"
