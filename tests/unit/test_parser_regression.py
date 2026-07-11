"""Small corpus protecting valid transaction intent and amount behavior."""

from __future__ import annotations

from tests.fakes.external_modules import install_external_stubs

install_external_stubs()

from app.nlp.regex_parser import parse_debt_input, parse_with_regex


def test_valid_expense_income_and_transfer_inputs_keep_existing_behavior() -> None:
    """Phase 0 date safety must not change established valid parsing."""

    expense = parse_with_regex("beli kopi 10k dari Cash")
    income = parse_with_regex("gaji 5jt ke BCA")
    transfer = parse_with_regex("transfer 200k dari BRI ke DANA")

    assert expense and expense["type"] == "expense" and expense["amount"] == 10_000
    assert income and income["type"] == "income" and income["amount"] == 5_000_000
    assert transfer and transfer["type"] == "transfer"
    assert transfer["account"] == "BRI"
    assert transfer["to_account"] == "DANA"


def test_explicit_debt_payment_still_wins_over_generic_expense() -> None:
    """Debt intent precedence remains compatible with the audited behavior."""

    debt = parse_debt_input("bayar hutang Budi 100rb dari BCA")
    assert debt and debt["intent"] == "add_payment"
    assert debt["target_debt_type"] == "payable"
