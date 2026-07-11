"""Regression tests for transaction commit and rollback result semantics."""

from __future__ import annotations

from unittest.mock import patch

from tests.fakes.external_modules import install_external_stubs

install_external_stubs()

from app.services import transaction_service
from app.sheets.client import SheetsAtomicWriteError


def _parsed_expense() -> dict:
    return {
        "type": "expense",
        "amount": 10_000,
        "category": "Food & Beverage",
        "account": "Cash",
        "description": "Kopi",
        "date": "2026-07-10",
    }


def test_save_transaction_is_not_success_after_atomic_balance_rollback() -> None:
    """A rolled-back balance failure must never be reported as saved."""

    error = SheetsAtomicWriteError("balance failed", rollback_ok=True)
    with (
        patch.object(transaction_service, "validate_transaction", return_value=(True, "ok")),
        patch.object(transaction_service, "ensure_category_for_transaction", return_value="Food & Beverage"),
        patch.object(transaction_service, "calculate_account_deltas", return_value={"Cash": -10_000}),
        patch.object(transaction_service, "validate_accounts_exist", return_value=(True, [])),
        patch.object(transaction_service, "build_transaction_row", return_value=("txn_test", ["txn_test"])),
        patch.object(transaction_service, "append_row"),
        patch.object(transaction_service, "sort_transactions_sheet_by_date"),
        patch.object(transaction_service, "apply_account_deltas", side_effect=error),
    ):
        result = transaction_service.save_transaction(_parsed_expense(), "beli kopi 10k")

    assert result["success"] is False
    assert result["transaction_id"] is None
    assert result["commit_status"] == "commit_failed"
    assert result["rollback_status"] == "rollback_succeeded"


def test_save_batch_is_not_success_when_balance_outcome_is_unknown() -> None:
    """An unverified balance exception must request reconciliation, not success."""

    with (
        patch.object(transaction_service, "validate_transaction", return_value=(True, "ok")),
        patch.object(transaction_service, "ensure_category_for_transaction", return_value="Food & Beverage"),
        patch.object(transaction_service, "calculate_account_deltas", return_value={"Cash": -10_000}),
        patch.object(transaction_service, "validate_accounts_exist", return_value=(True, [])),
        patch.object(transaction_service, "build_transaction_row", return_value=("txn_test", ["txn_test"])),
        patch.object(transaction_service, "append_rows"),
        patch.object(transaction_service, "sort_transactions_sheet_by_date"),
        patch.object(transaction_service, "apply_account_deltas", side_effect=RuntimeError("connection lost")),
    ):
        result = transaction_service.save_transactions_batch([{"parsed": _parsed_expense(), "raw": "kopi"}])

    assert result["success"] is False
    assert result["success_count"] == 0
    assert result["commit_status"] == "commit_outcome_unknown"
    assert result["reconciliation_required"] is True
