"""Focused use cases that coordinate transaction and debt services."""

from __future__ import annotations

from typing import Any

from app.application.results import (
    MutationCommitted,
    PreviewReady,
    UseCaseResult,
    ValidationFailure,
    immutable_payload,
    mutable_payload,
)
from app.services import debt_service, transaction_service


def _result_from_legacy(result: dict, *, preview: bool = False) -> UseCaseResult:
    """Translate an existing service result at the application boundary."""

    payload = immutable_payload(result)
    message = str(result.get("message") or "")
    if result.get("success"):
        result_type = PreviewReady if preview else MutationCommitted
        return result_type(message=message, payload=payload)
    return ValidationFailure(message=message, payload=payload, errors=(message,) if message else ())


def _legacy(result: UseCaseResult) -> dict[str, Any]:
    """Return a detached dict for compatibility handlers not yet extracted."""

    return mutable_payload(result.payload)


def execute_delete_transactions(
    *,
    row_indices: list[int] | None = None,
    txn_ids: list[str] | None = None,
) -> UseCaseResult:
    """Delete transactions while coordinating linked debt reversal."""

    result = transaction_service.delete_transactions_by_refs(
        row_indices=row_indices,
        txn_ids=txn_ids,
        void_debts_for_transaction_fn=debt_service.void_debts_for_transaction,
        reverse_debt_payment_transaction_fn=debt_service.reverse_debt_payment_transaction,
    )
    return _result_from_legacy(result)


def delete_transactions_by_refs(
    row_indices: list[int] | None = None,
    txn_ids: list[str] | None = None,
) -> dict:
    """Compatibility facade for the historical handler result contract."""

    return _legacy(execute_delete_transactions(row_indices=row_indices, txn_ids=txn_ids))


def execute_edit_transaction(
    updates: dict,
    *,
    row_index: int | None = None,
    txn_id: str | None = None,
) -> UseCaseResult:
    """Edit a transaction and coordinate any linked debt effects."""

    def edit_debt_payment(preview: dict) -> dict:
        return transaction_service.edit_debt_payment_transaction_amount(
            preview,
            reverse_debt_payment_transaction_fn=debt_service.reverse_debt_payment_transaction,
            add_payment_by_person_fn=debt_service.add_payment_by_person,
        )

    result = transaction_service.edit_transaction_by_ref(
        updates,
        row_index=row_index,
        txn_id=txn_id,
        edit_debt_payment_transaction_fn=edit_debt_payment,
        sync_debt_charges_from_transaction_edit_fn=debt_service.sync_debt_charges_from_transaction_edit,
    )
    return _result_from_legacy(result)


def edit_transaction_by_ref(
    updates: dict,
    row_index: int | None = None,
    txn_id: str | None = None,
) -> dict:
    """Compatibility facade for the historical handler result contract."""

    return _legacy(
        execute_edit_transaction(updates, row_index=row_index, txn_id=txn_id)
    )


def prepare_void_debt(debt_ref: str, last_debt_map: dict | None = None) -> UseCaseResult:
    """Build a debt-void preview using transaction data supplied by the use case."""

    result = debt_service.preview_void_debt(
        debt_ref,
        last_debt_map,
        transactions=transaction_service.get_transactions_with_row_index(),
        is_debt_cashflow_transaction_fn=transaction_service.is_debt_cashflow_transaction,
        calculate_reverse_deltas_for_delete_fn=transaction_service.calculate_reverse_deltas_for_delete,
    )
    return _result_from_legacy(result, preview=True)


def preview_void_debt(debt_ref: str, last_debt_map: dict | None = None) -> dict:
    """Compatibility facade for the historical debt preview contract."""

    return _legacy(prepare_void_debt(debt_ref, last_debt_map))


def prepare_void_debts_by_person(
    person_name: str,
    detail_ref: str | None = None,
) -> UseCaseResult:
    """Build an ordered multi-debt void preview for one person."""

    result = debt_service.preview_void_debts_by_person(
        person_name,
        detail_ref,
        transactions=transaction_service.get_transactions_with_row_index(),
        is_debt_cashflow_transaction_fn=transaction_service.is_debt_cashflow_transaction,
        calculate_reverse_deltas_for_delete_fn=transaction_service.calculate_reverse_deltas_for_delete,
    )
    return _result_from_legacy(result, preview=True)


def preview_void_debts_by_person(person_name: str, detail_ref: str | None = None) -> dict:
    """Compatibility facade for the historical person preview contract."""

    return _legacy(prepare_void_debts_by_person(person_name, detail_ref))


def execute_void_debt(debt_ref: str, last_debt_map: dict | None = None) -> UseCaseResult:
    """Void one debt after preparing its linked transaction effects."""

    preview = preview_void_debt(debt_ref, last_debt_map)
    result = debt_service.void_debt(
        debt_ref,
        last_debt_map,
        preview=preview,
        apply_account_deltas_fn=transaction_service.apply_account_deltas,
    )
    return _result_from_legacy(result)


def void_debt(debt_ref: str, last_debt_map: dict | None = None) -> dict:
    """Compatibility facade for the historical single-debt writer."""

    return _legacy(execute_void_debt(debt_ref, last_debt_map))


def execute_void_debt_ids(debt_ids: list[str]) -> UseCaseResult:
    """Void selected debt IDs through the same single-debt use case."""

    result = debt_service.void_debt_ids(debt_ids, void_debt_fn=void_debt)
    return _result_from_legacy(result)


def void_debt_ids(debt_ids: list[str]) -> dict:
    """Compatibility facade for selected debt IDs."""

    return _legacy(execute_void_debt_ids(debt_ids))


def execute_void_debts_by_person(
    person_name: str,
    detail_ref: str | None = None,
) -> UseCaseResult:
    """Void all explicitly selected debts for one person."""

    result = debt_service.void_debts_by_person(
        person_name,
        detail_ref,
        preview_void_debts_by_person_fn=preview_void_debts_by_person,
        void_debt_ids_fn=void_debt_ids,
    )
    return _result_from_legacy(result)


def void_debts_by_person(person_name: str, detail_ref: str | None = None) -> dict:
    """Compatibility facade for the historical person-level writer."""

    return _legacy(execute_void_debts_by_person(person_name, detail_ref))
