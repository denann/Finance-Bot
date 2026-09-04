"""Regression coverage for shared split wizard and button presentation rules."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from app.application.bulk_input import BulkItemStatus, create_bulk_session
from app.bot.handler_parts.bulk_flow import (
    _classify_legacy_item,
    _mark_split,
    _semantic_choice_keyboard,
    _semantic_split_keyboard,
    _split_keyboard,
)
from app.bot.handler_parts.management_browser import _list_keyboard
from app.bot.handler_parts.transaction_flow import (
    meal_split_status_keyboard,
    parse_clarification_keyboard,
    parse_mixed_item,
    social_spending_guard_keyboard,
    split_bill_keyboard,
)


ROOT = Path(__file__).resolve().parents[2]


def _labels(markup) -> list[list[str]]:
    return [[button.text for button in row] for row in markup.inline_keyboard]


def test_reported_bulk_split_input_keeps_gross_amount_and_exits_status_wizard():
    """Paid/unpaid choices must resolve each reported item exactly once."""

    cases = [
        ("Bayar wifi 285.550k via dana bagi 4 sapto Alpat Opik tanggal 19 Agustus", 285_550),
        ("Bayar air pam 266.400k via dana bagi 4 sapto alpat opik tanggal 19 agustus", 266_400),
    ]
    for index, (raw, gross) in enumerate(cases):
        item = _classify_legacy_item(
            raw,
            parse_mixed_item(raw),
            original_index=index,
            item_id=f"i{index + 1}",
        )
        assert item.status == BulkItemStatus.NEEDS_CLARIFICATION
        assert item.clarification_reason == "split_decision"
        assert dict(item.parsed_payload)["split_bill"]["total_amount"] == gross

        paid = _mark_split(item, "paid")
        unpaid = _mark_split(item, "unpaid")
        assert paid.status == BulkItemStatus.READY
        assert unpaid.status == BulkItemStatus.READY
        assert paid.clarification_reason == unpaid.clarification_reason == ""
        assert dict(unpaid.parsed_payload)["amount"] == gross


def test_all_split_status_paths_share_the_same_buttons():
    """Single, bulk, and ambiguous-bulk split stages use one UI contract."""

    item = _classify_legacy_item(
        "beli kopi 40k bagi 2 Budi",
        parse_mixed_item("beli kopi 40k bagi 2 Budi"),
        original_index=0,
        item_id="i1",
    )
    session = create_bulk_session([item], session_id="split1")
    expected = [["✅ Sudah dibayar", "⏳ Belum dibayar"], ["🚫 Batal"]]

    assert _labels(meal_split_status_keyboard("self")) == expected
    assert _labels(split_bill_keyboard("single")) == expected
    assert _labels(_split_keyboard(session, item)) == expected
    assert _labels(_semantic_split_keyboard(session, item, "status")) == expected


def test_ambiguous_meaning_choices_keep_contextual_symbols():
    """Ambiguity choices use semantic icons instead of cashflow report signs."""

    expected = [
        "🟢 Orang ini bayar ke saya",
        "🔴 Saya hutang ke orang ini",
        "🧾 Pengeluaran biasa",
        "👤 Orang lain yang bayar",
    ]
    assert [row[0] for row in _labels(parse_clarification_keyboard())[:4]] == expected
    assert _labels(social_spending_guard_keyboard())[1] == ["🧾 Pengeluaran biasa"]

    item = _classify_legacy_item(
        "Bayar air pam 266.400k via DANA bagi 4 Sapto Alpat Opik tanggal 19 Agustus",
        parse_mixed_item("Bayar air pam 266.400k via DANA bagi 4 Sapto Alpat Opik tanggal 19 Agustus"),
        original_index=0,
        item_id="i1",
    )
    session = create_bulk_session([item], session_id="ambiguous1")
    labels = [row[0] for row in _labels(_semantic_choice_keyboard(session, item)) if len(row) == 1]
    for label in expected:
        assert label in labels


def test_debt_selector_is_number_only_in_two_rows_of_three():
    """The six-item debt page stays compact without names or amounts in buttons."""

    state = {
        "session_id": "debt1",
        "page": 0,
        "records": [{"id": str(index)} for index in range(6)],
    }
    labels = _labels(_list_keyboard("deb", state, lambda number, _item: str(number), columns=3))
    assert labels[:2] == [["1", "2", "3"], ["4", "5", "6"]]
    assert labels[-1] == ["📄 Hal 1/1"]


def test_literal_inline_buttons_never_start_with_plain_words():
    """Catch new word-only buttons while allowing intentional number selectors."""

    offenders: list[str] = []
    for path in (ROOT / "app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name != "InlineKeyboardButton" or not node.args:
                continue
            first = node.args[0]
            text = first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else ""
            if text and text.lstrip()[:1].isalpha():
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}:{text}")
    assert offenders == []


def test_cashflow_outputs_do_not_restore_legacy_income_expense_icons():
    """Income and expense presentation must use plain plus/minus signs."""

    legacy = re.compile(r"(?:✅|❌|➕|➖).*(?:Income|Expense|Pemasukan|Pengeluaran|Cash In|Cash Out)")
    offenders = []
    for path in (ROOT / "app").rglob("*.py"):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if legacy.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{line_number}:{line.strip()}")
    assert offenders == []
