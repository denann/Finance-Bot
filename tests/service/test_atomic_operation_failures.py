"""Failure-injection tests for result-style and multi-step mutations."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.fakes.external_modules import install_external_stubs

install_external_stubs()

from app.services import debt_service, transaction_service
from app.services.operation_errors import PartialMutationError, require_success_after_write
from app.sheets.client import sheets_transaction


def test_result_style_failure_after_write_is_typed_exception() -> None:
    """A downstream ``success=False`` cannot leave normal control flow."""

    with pytest.raises(PartialMutationError):
        require_success_after_write(
            {"success": False, "message": "linked debt failed"},
            operation="linked_debt",
            default_message="failed",
        )


def test_outer_sheets_transaction_rolls_back_on_typed_partial_failure() -> None:
    """Typed failures escape to the existing rollback boundary."""

    rolled_back: list[str] = []
    with pytest.raises(PartialMutationError):
        with sheets_transaction("test") as transaction:
            transaction.add_rollback("undo", lambda: rolled_back.append("undo"))
            raise PartialMutationError("downstream failed", operation="test")

    assert rolled_back == ["undo"]


def test_delete_debt_result_failure_raises_after_balance_reverse() -> None:
    """A linked-debt failure after balance reversal is never returned normally."""

    transaction = {
        "id": "txn_1",
        "_row_index": 2,
        "type": "expense",
        "amount": 10_000,
        "account": "Cash",
        "category": "Food & Beverage",
        "hutang_id": "debt_1",
    }
    preview = {
        "deletable": [transaction],
        "blocked": [],
        "missing_ids": [],
        "missing_rows": [],
        "reverse_deltas": {"Cash": 10_000},
    }
    with (
        patch.object(transaction_service, "preview_delete_transactions_by_refs", return_value=preview),
        patch.object(transaction_service, "apply_account_deltas", return_value={"failed_accounts": [], "new_balances": {"Cash": 20_000}}),
        patch.object(debt_service, "void_debts_for_transaction", return_value={"success": False, "message": "debt failed"}),
    ):
        with pytest.raises(PartialMutationError) as error:
            transaction_service.delete_transactions_by_refs(txn_ids=["txn_1"])

    assert error.value.operation == "delete_transaction_void_linked_debt"


def test_edit_row_failure_after_balance_update_raises() -> None:
    """A row update failure after balance correction requests rollback."""

    old = {"id": "txn_1", "_row_index": 2, "raw_input": "kopi"}
    new = {**old, "amount": 20_000}
    preview = {"success": True, "old_txn": old, "new_txn": new, "net_deltas": {"Cash": -10_000}}
    with (
        patch.object(transaction_service, "preview_edit_transaction_by_ref", return_value=preview),
        patch.object(transaction_service, "apply_account_deltas", return_value={"failed_accounts": [], "new_balances": {"Cash": 0}}),
        patch.object(transaction_service, "build_transaction_row_from_record", return_value=["txn_1"]),
        patch.object(transaction_service, "update_row", side_effect=RuntimeError("row failed")),
    ):
        with pytest.raises(PartialMutationError) as error:
            transaction_service.edit_transaction_by_ref({"amount": 20_000}, txn_id="txn_1")

    assert error.value.operation == "edit_transaction_row"
