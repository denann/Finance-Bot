import ast
from pathlib import Path
import re
from typing import Any


SOURCE = Path("app/services/resolver_service.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
NAMES = {
    "normalize_lookup_key",
    "_default_category_type",
    "_default_category_name",
    "_raw_contains_normalized_phrase",
    "resolve_learned_category_from_raw",
    "extract_category_learning_alias",
    "assess_category_learning_candidate",
    "learn_category_alias",
    "resolve_parsed_transaction",
}
NODES = [node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name in NAMES]


def _load(extra=None):
    ns = {"re": re, "Any": Any, "SHEET_CATEGORIES": "categories"}
    ns.update(extra or {})
    exec(compile(ast.Module(body=NODES, type_ignores=[]), "resolver_service.py", "exec"), ns)
    return ns


def _rows(alias_food="makan", alias_other="lainnya"):
    return [
        {"category_name": "Food & Beverage", "type": "expense", "aliases": alias_food},
        {"category_name": "Other Expense", "type": "expense", "aliases": alias_other},
        {"category_name": "Salary", "type": "income", "aliases": "gaji"},
    ]


def test_learning_candidate_uses_bounded_descriptive_phrase_after_explicit_auto_correction():
    rows = _rows()
    ns = _load({
        "get_account_names_from_sheet": lambda: ["BCA", "DANA"],
        "get_category_records_safe": lambda: rows,
        "find_category_by_name": lambda name: {"found": True, "record": rows[0]} if name == "Food & Beverage" else {"found": False},
    })
    candidate = ns["assess_category_learning_candidate"](
        {"id": "txn1", "type": "expense", "category": "Other Expense", "raw_input": "sop iga 50k dari BCA", "parsed_by": "regex"},
        {"id": "txn1", "type": "expense", "category": "Food & Beverage"},
        {"category": "Food & Beverage"},
    )
    assert candidate["alias"] == "sop iga"
    assert candidate["target_category"] == "Food & Beverage"
    assert candidate["transaction_type"] == "expense"

    # Not an explicit category correction / not parser-origin => no offer.
    assert ns["assess_category_learning_candidate"](
        {"type": "expense", "category": "Other Expense", "raw_input": "sop iga 50k", "parsed_by": "manual"},
        {"type": "expense", "category": "Food & Beverage"},
        {"category": "Food & Beverage"},
    ) is None
    assert ns["assess_category_learning_candidate"](
        {"type": "expense", "category": "Other Expense", "raw_input": "sop iga 50k", "parsed_by": "regex"},
        {"type": "expense", "category": "Food & Beverage"},
        {"amount": 50000},
    ) is None


def test_alias_learning_merges_existing_aliases_and_collision_is_not_row_order_dependent():
    captured = []
    rows = _rows(alias_food="makan,minum")
    ns = _load({
        "get_all_records": lambda sheet: list(rows),
        "update_category": lambda category_name, **kwargs: captured.append((category_name, kwargs)) or {"success": True, "category_name": category_name},
    })
    result = ns["learn_category_alias"](alias="sop iga", target_category="Food & Beverage", transaction_type="expense")
    assert result["success"] is True
    assert captured == [("Food & Beverage", {"aliases": ["makan", "minum", "sop iga"]})]

    collision_rows = [
        {"category_name": "Other Expense", "type": "expense", "aliases": "sop iga"},
        {"category_name": "Food & Beverage", "type": "expense", "aliases": "makan"},
    ]
    captured.clear()
    ns = _load({
        "get_all_records": lambda sheet: list(collision_rows),
        "update_category": lambda *args, **kwargs: captured.append((args, kwargs)) or {"success": True},
    })
    result = ns["learn_category_alias"](alias="sop iga", target_category="Food & Beverage", transaction_type="expense")
    assert result["success"] is False and result.get("collision") is True
    assert captured == []


def test_learned_raw_alias_is_fallback_only_type_aware_and_phrase_safe():
    rows = _rows(alias_food="makan,sop iga")
    ns = _load({
        "get_category_records_safe": lambda: rows,
        "get_account_names_from_sheet": lambda: ["BCA"],
        "resolve_account_for_parser": lambda value: value,
        "ensure_category_for_transaction": lambda category, txn_type: category or ("Other Income" if txn_type == "income" else "Other Expense"),
    })
    fallback = {"type": "expense", "category": "Other Expense"}
    assert ns["resolve_parsed_transaction"](dict(fallback), "sop iga 60k") ["category"] == "Food & Beverage"

    strong = {"type": "expense", "category": "Transport"}
    assert ns["resolve_parsed_transaction"](dict(strong), "sop iga naik taksi 60k")["category"] == "Transport"

    income = {"type": "income", "category": "Other Income"}
    assert ns["resolve_parsed_transaction"](dict(income), "sop iga 60k")["category"] == "Other Income"

    assert ns["resolve_learned_category_from_raw"]("kesop igaan 60k", "expense")["status"] == "missing"


def test_category_learning_is_post_commit_separate_action_and_failure_cannot_rollback_edit():
    callback = Path("app/bot/handler_parts/callback_handler.py").read_text(encoding="utf-8")
    edit_block = callback[callback.index('if confirm_target == "edit_txn":'):callback.index('if confirm_target == "delete_txns":')]
    commit_call = edit_block.index("result = edit_transaction_by_ref(")
    success_gate = edit_block.index('if not result.get("success"):', commit_call)
    offer_call = edit_block.index("_offer_category_learning_after_committed_edit", success_gate)
    assert commit_call < success_gate < offer_call
    assert 'flow_type="category_learning"' in callback
    assert 'expected_flow="category_learning"' in callback
    assert "learn_category_alias(" in callback
    assert "Transaksi tetap sudah tersimpan, tetapi learning kategori gagal" in callback

    contracts = Path("app/bot/callback_contracts.py").read_text(encoding="utf-8")
    assert '"category_learn:"' in contracts


def test_category_learning_write_exception_returns_bounded_post_commit_failure():
    rows = _rows(alias_food="makan,minum")

    def _write_boom(*args, **kwargs):
        raise RuntimeError("sheet write boom")

    ns = _load({
        "get_all_records": lambda sheet: list(rows),
        "update_category": _write_boom,
    })
    result = ns["learn_category_alias"](
        alias="sop iga",
        target_category="Food & Beverage",
        transaction_type="expense",
    )
    assert result["success"] is False
    assert "Gagal menyimpan alias kategori" in result["message"]
    assert "sheet write boom" in result["message"]

    callback = Path("app/bot/handler_parts/callback_handler.py").read_text(encoding="utf-8")
    assert "Transaksi tetap sudah tersimpan, tetapi learning kategori gagal" in callback
