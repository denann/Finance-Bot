import ast
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

from app.application.bulk_input import (
    BulkItem,
    BulkItemStatus,
    create_bulk_session,
    make_bulk_item,
    replace_bulk_item,
    result_for_session,
)


SOURCE = Path("app/bot/handler_parts/bulk_flow.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def _load_helpers():
    names = {"_semantic_wait_item", "_classify_semantic_legacy_item"}
    nodes = [node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name in names]
    ns = {
        "deepcopy": deepcopy,
        "replace": replace,
        "MappingProxyType": MappingProxyType,
        "BulkItem": BulkItem,
        "BulkItemStatus": BulkItemStatus,
        "make_bulk_item": make_bulk_item,
        "detect_date_result": lambda raw: type("R", (), {"status": "valid"})(),
        "needs_account": lambda parsed: bool(parsed.get("requires_account")),
        "split_bill_needs_decision": lambda parsed: bool(parsed.get("split_bill") and not parsed["split_bill"].get("status")),
        "debt_uses_cashflow": lambda parsed: parsed.get("cashflow_mode", "cashflow") != "debt_only",
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "bulk_flow.py", "exec"), ns)
    return ns


def _item(item_id, index, raw, status=BulkItemStatus.READY, reason="", payload=None):
    return BulkItem(
        item_id=item_id,
        original_index=index,
        raw_input=raw,
        status=status,
        kind="transaction",
        parsed_payload=MappingProxyType(dict(payload or {})),
        clarification_reason=reason,
    )


def test_semantic_split_substates_stay_on_same_bulk_item_identity():
    helpers = _load_helpers()
    a = _item("a", 0, "kopi 10k", payload={"amount": 10000})
    b = _item("b", 1, "Budi bayar makan 100k", status=BulkItemStatus.NEEDS_CLARIFICATION, reason="ambiguous_parse", payload={"amount": 100000})
    c = _item("c", 2, "bensin 20k", payload={"amount": 20000})
    session = create_bulk_session([a, b, c], session_id="s1")
    waiting = helpers["_semantic_wait_item"](
        b,
        reason="semantic_split_payer",
        semantic_state={"raw": b.raw_input, "people": ["Budi"], "amount": 100000, "parsed": {"amount": 100000}},
    )
    updated = replace_bulk_item(session, waiting)
    assert [item.item_id for item in updated.items] == ["a", "b", "c"]
    assert updated.items[0] == a and updated.items[2] == c
    assert updated.items[1].clarification_reason == "semantic_split_payer"
    result = result_for_session(updated)
    assert result.payload["session"].awaiting_mode == "semantic_split_payer"
    assert result.payload["item"].item_id == "b"


def test_explicit_semantic_reclassification_skips_repeat_ambiguity_but_keeps_missing_account():
    helpers = _load_helpers()
    b = _item("b", 1, "Budi bayar makan 100k", status=BulkItemStatus.NEEDS_CLARIFICATION, reason="ambiguous_parse", payload={"amount": 100000})
    replacement = helpers["_classify_semantic_legacy_item"](
        b,
        {"kind": "transaction", "parsed": {"type": "expense", "amount": 100000, "requires_account": True}},
    )
    assert replacement.item_id == "b"
    assert replacement.status == BulkItemStatus.NEEDS_CLARIFICATION
    assert replacement.clarification_reason == "missing_account"


def test_bulk_ambiguity_exposes_single_flow_meanings_without_whole_batch_reparse_or_write():
    assert 'callback_data=f"{prefix}:debt_payment"' in SOURCE
    assert 'callback_data=f"{prefix}:payable"' in SOURCE
    assert 'callback_data=f"{prefix}:expense"' in SOURCE
    assert 'callback_data=f"{prefix}:no_cashflow"' in SOURCE
    assert 'callback_data=f"{prefix}:split"' in SOURCE
    assert 'callback_data=f"{prefix}:fronting"' in SOURCE
    assert "build_clarified_debt_payment" in SOURCE
    assert "build_clarified_expense" in SOURCE
    assert "build_clarified_fronting" in SOURCE

    handler = next(node for node in TREE.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "handle_bulk_callback")
    handler_source = ast.get_source_segment(SOURCE, handler)
    assert "assert_current_target(session, session_id, item_id)" in handler_source
    assert 'target.clarification_reason != "ambiguous_parse"' in handler_source
    assert "remove_bulk_item(session, item_id)" in handler_source
    assert "replace_bulk_item(session, replacement)" in handler_source
    assert "parse_mixed_items_batch" not in handler_source
    for forbidden in ("save_transaction(", "save_transactions_batch(", "update_row("):
        assert forbidden not in handler_source


def test_custom_split_allocation_is_item_local_and_returns_to_status_stage():
    source = SOURCE
    assert 'session.awaiting_mode == "semantic_split_custom_text"' in source
    assert "parse_meal_split_allocation" in source
    assert 'reason="semantic_split_status"' in source
    assert 'target.clarification_reason != "semantic_split_status"' in source
