"""Application orchestration tests for transaction/debt combined operations."""

from __future__ import annotations

from unittest.mock import patch

from app.application.results import MutationCommitted, ValidationFailure
from app.application import transaction_debt
from app.services import debt_service, transaction_service


def test_delete_use_case_injects_debt_collaborators() -> None:
    captured: dict = {}

    def fake_delete(**kwargs):
        captured.update(kwargs)
        return {"success": True, "message": "ok", "deleted_ids": ["txn_1"]}

    with patch.object(transaction_service, "delete_transactions_by_refs", side_effect=fake_delete):
        result = transaction_debt.execute_delete_transactions(txn_ids=["txn_1"])

    assert isinstance(result, MutationCommitted)
    assert captured["void_debts_for_transaction_fn"] is debt_service.void_debts_for_transaction
    assert captured["reverse_debt_payment_transaction_fn"] is debt_service.reverse_debt_payment_transaction


def test_pre_mutation_failure_remains_typed_validation_result() -> None:
    with patch.object(
        transaction_service,
        "delete_transactions_by_refs",
        return_value={"success": False, "message": "Tidak ada transaksi."},
    ):
        result = transaction_debt.execute_delete_transactions(txn_ids=["missing"])

    assert isinstance(result, ValidationFailure)
    assert result.message == "Tidak ada transaksi."


def test_application_use_case_has_no_telegram_or_context_dependency() -> None:
    source = (transaction_debt.__file__ and open(transaction_debt.__file__, encoding="utf-8").read()) or ""
    assert "telegram" not in source.lower()
    assert "context.user_data" not in source

