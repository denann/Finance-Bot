"""Manual single and multi-field preview edit regressions."""

from __future__ import annotations

import pytest

from app.bot.handler_parts.transaction_flow import (
    apply_preview_edit_updates_to_parsed,
    parse_preview_edit_updates,
)


BASE = {
    "type": "expense",
    "amount": 20_000,
    "category": "Food & Beverage",
    "account": "Cash",
    "description": "Kopi",
    "catatan": "",
    "date": "2026-07-10",
}


@pytest.mark.regression
@pytest.mark.parametrize(
    ("case_id", "raw", "expected"),
    [
        ("mx21_01_single_amount", "nominal 15k", {"amount": 15_000.0, "account": "Cash"}),
        (
            "mx21_02_multi_field",
            "nominal: 15k, kategori: Food & Beverage, rekening: DANA",
            {"amount": 15_000.0, "category": "Food & Beverage", "account": "DANA", "description": "Kopi"},
        ),
        (
            "mx21_03_description_note",
            "deskripsi: Kopi susu, catatan: debug test",
            {"description": "Kopi susu", "catatan": "debug test", "amount": 20_000},
        ),
    ],
)
def test_manual_edit_preserves_undeclared_fields(case_id: str, raw: str, expected: dict) -> None:
    """Apply declared updates and keep every unrelated preview field unchanged."""

    updates = parse_preview_edit_updates(raw)
    actual = apply_preview_edit_updates_to_parsed(dict(BASE), updates)
    for field, value in expected.items():
        assert actual[field] == value, f"Case ID: {case_id}\nField: {field}\nExpected: {value!r}\nActual: {actual[field]!r}"


def test_invalid_manual_edit_does_not_change_or_save_preview() -> None:
    """Unknown edit text yields no updates and cannot create a mutation."""

    updates = parse_preview_edit_updates("abc random tidak jelas")
    mutations: list[dict] = []
    assert updates == {}
    assert apply_preview_edit_updates_to_parsed(dict(BASE), updates) == BASE
    assert mutations == []
