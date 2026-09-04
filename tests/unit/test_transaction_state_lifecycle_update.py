from pathlib import Path

from app.bot.handler_parts.state_utils import clear_pending_flow_state


def test_transient_selector_cleanup_preserves_long_lived_transaction_reference_context():
    class Context:
        user_data = {
            "transaction_ref_context": {"session_id": "A", "ordered_ids": ["txn_1", "txn_2"]},
            "transaction_browser_session": {"session_id": "A"},
            "pending_txn_selector": {"session_id": "S"},
            "pending_bulk_edit_staged": {"entries": []},
        }

    removed = clear_pending_flow_state(Context())

    assert "pending_txn_selector" in removed
    assert "pending_bulk_edit_staged" in removed
    assert Context.user_data["transaction_ref_context"]["session_id"] == "A"
    assert Context.user_data["transaction_browser_session"]["session_id"] == "A"


def test_selector_text_consumption_is_before_ordinary_transaction_parsing():
    source = Path("app/bot/handler_parts/message_handlers.py").read_text(encoding="utf-8")
    selector = source.index("handle_transaction_selector_text(update, context, user_text)")
    normal_parse = source.index("input_lines = split_user_inputs(user_text)", selector)
    assert selector < normal_parse
