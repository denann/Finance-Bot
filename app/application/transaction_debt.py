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


def prepare_delete_transactions(
    *,
    row_indices: list[int] | None = None,
    txn_ids: list[str] | None = None,
) -> UseCaseResult:
    """Build the exact delete/dependency preview used by bot flows.

    Transaction identity resolution stays in ``transaction_service`` while
    debt eligibility stays in ``debt_service``.  Payment transactions keep
    their dedicated reversal semantics; source-linked debt charges are
    prevalidated with the same primitive the writer uses.
    """
    result = transaction_service.preview_delete_transactions_by_refs(row_indices, txn_ids)
    deletable: list[dict] = []
    blocked = [dict(txn) for txn in result.get("blocked") or []]
    for txn in result.get("deletable") or []:
        category = str((txn or {}).get("category") or "").strip()
        if category in {"Pembayaran Piutang", "Bayar Utang"}:
            deletable.append(txn)
            continue
        txn_id = str((txn or {}).get("id") or "").strip()
        linked_ids = transaction_service.parse_transaction_debt_ids(txn)
        dependency = debt_service.preview_void_debts_for_transaction(txn_id, linked_ids)
        if dependency.get("success"):
            deletable.append(txn)
            continue
        blocked_txn = dict(txn)
        blocked_txn["_delete_block_reason"] = dependency.get("message") or "Dependency debt berubah."
        blocked.append(blocked_txn)

    result = dict(result)
    result["deletable"] = deletable
    result["blocked"] = blocked
    result["reverse_deltas"] = transaction_service.calculate_reverse_deltas_for_delete(deletable)
    return _result_from_legacy(result, preview=True)


def preview_delete_transactions_by_refs(
    row_indices: list[int] | None = None,
    txn_ids: list[str] | None = None,
) -> dict:
    """Compatibility facade for coordinated read-only delete preview."""
    return _legacy(prepare_delete_transactions(row_indices=row_indices, txn_ids=txn_ids))


def execute_delete_transactions(
    *,
    row_indices: list[int] | None = None,
    txn_ids: list[str] | None = None,
    expected_deletable_ids: list[str] | None = None,
    expected_blocked_ids: list[str] | None = None,
    expected_signatures: dict[str, tuple | list] | None = None,
    expected_dependency_signatures: dict[str, tuple | list] | None = None,
) -> UseCaseResult:
    """Delete transactions while coordinating linked debt reversal."""
    result = transaction_service.delete_transactions_by_refs(
        row_indices=row_indices,
        txn_ids=txn_ids,
        expected_deletable_ids=expected_deletable_ids,
        expected_blocked_ids=expected_blocked_ids,
        expected_signatures=expected_signatures,
        expected_dependency_signatures=expected_dependency_signatures,
        dependency_signature_fn=debt_service.transaction_debt_dependency_signature,
        void_debts_for_transaction_fn=debt_service.void_debts_for_transaction,
        reverse_debt_payment_transaction_fn=debt_service.reverse_debt_payment_transaction,
    )
    return _result_from_legacy(result)


def delete_transactions_by_refs(
    row_indices: list[int] | None = None,
    txn_ids: list[str] | None = None,
    *,
    expected_deletable_ids: list[str] | None = None,
    expected_blocked_ids: list[str] | None = None,
    expected_signatures: dict[str, tuple | list] | None = None,
    expected_dependency_signatures: dict[str, tuple | list] | None = None,
) -> dict:
    """Compatibility facade for the historical handler result contract."""
    return _legacy(execute_delete_transactions(
        row_indices=row_indices,
        txn_ids=txn_ids,
        expected_deletable_ids=expected_deletable_ids,
        expected_blocked_ids=expected_blocked_ids,
        expected_signatures=expected_signatures,
        expected_dependency_signatures=expected_dependency_signatures,
    ))


def execute_edit_transaction(
    updates: dict,
    *,
    row_index: int | None = None,
    txn_id: str | None = None,
    expected_signature: tuple | list | None = None,
    relation_transition: str | None = None,
) -> UseCaseResult:
    """Edit a transaction and coordinate linked debt effects at one boundary."""

    def edit_debt_payment(preview: dict) -> dict:
        return transaction_service.edit_debt_payment_transaction_amount(
            preview,
            reverse_debt_payment_transaction_fn=debt_service.reverse_debt_payment_transaction,
            add_payment_by_person_fn=debt_service.add_payment_by_person,
        )

    if relation_transition == "detach_pristine":
        from app.services.operation_errors import PartialMutationError
        try:
            current = transaction_service.get_single_transaction_by_ref(row_index=row_index, txn_id=txn_id)
        except ValueError as exc:
            return _result_from_legacy({"success": False, "message": str(exc), "stale": True})
        if not current:
            return _result_from_legacy({"success": False, "message": "Transaksi tidak ditemukan.", "stale": True})
        if expected_signature is not None and tuple(expected_signature) != transaction_service.transaction_material_signature(current):
            return _result_from_legacy({"success": False, "message": "Transaksi berubah sejak preview. Preview ulang diperlukan.", "stale": True})

        if updates:
            base_preview = transaction_service.preview_edit_transaction_by_ref(
                updates, row_index=row_index, txn_id=txn_id, expected_signature=expected_signature
            )
            if not base_preview.get("success"):
                return _result_from_legacy(base_preview)
        else:
            base_preview = {
                "success": True,
                "message": "ok",
                "old_txn": dict(current),
                "new_txn": dict(current),
                "updates": {},
                "net_deltas": {},
            }

        eligibility = debt_service.preview_pristine_relation_detach(base_preview.get("old_txn") or {})
        if not eligibility.get("success"):
            return _result_from_legacy(eligibility)

        # Relation detach is accounting-only. It deliberately performs no
        # account-balance mutation and therefore cannot replay historical cash.
        detach_result = debt_service.detach_pristine_relations_for_transaction(base_preview.get("old_txn") or {})
        if not detach_result.get("success"):
            return _result_from_legacy(detach_result)

        if updates:
            result = transaction_service.edit_transaction_by_ref(
                updates,
                row_index=row_index,
                txn_id=txn_id,
                edit_debt_payment_transaction_fn=edit_debt_payment,
                sync_debt_charges_from_transaction_edit_fn=debt_service.sync_debt_charges_from_transaction_edit,
                expected_signature=expected_signature,
                skip_debt_sync=True,
            )
            if not result.get("success"):
                raise PartialMutationError(result.get("message") or "Edit gagal setelah relation detach.", operation="edit_relation_transition")
        else:
            result = dict(base_preview)
            result["new_balances"] = {}

        target_id = str((result.get("new_txn") or current).get("id") or txn_id or "").strip()
        clear_result = transaction_service.clear_transaction_debt_relation(target_id)
        if not clear_result.get("success"):
            raise PartialMutationError(clear_result.get("message") or "Gagal clear relation transaksi.", operation="edit_relation_transition_clear")
        result["relation_transition"] = {**eligibility, **detach_result}
        result["new_txn"] = dict(result.get("new_txn") or current, hutang_id="", tipe_hutang="")
        result["success"] = True
        result["message"] = "ok"
        return _result_from_legacy(result)

    result = transaction_service.edit_transaction_by_ref(
        updates,
        row_index=row_index,
        txn_id=txn_id,
        edit_debt_payment_transaction_fn=edit_debt_payment,
        sync_debt_charges_from_transaction_edit_fn=debt_service.sync_debt_charges_from_transaction_edit,
        expected_signature=expected_signature,
    )
    return _result_from_legacy(result)


def edit_transaction_by_ref(
    updates: dict,
    row_index: int | None = None,
    txn_id: str | None = None,
    *,
    expected_signature: tuple | list | None = None,
    relation_transition: str | None = None,
) -> dict:
    """Compatibility facade for the historical handler result contract."""

    return _legacy(
        execute_edit_transaction(
            updates, row_index=row_index, txn_id=txn_id,
            expected_signature=expected_signature, relation_transition=relation_transition,
        )
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

    result = debt_service.void_debt_ids(
        debt_ids,
        void_debt_fn=void_debt,
        prevalidate_fn=lambda debt_id: preview_void_debt(debt_id, {}),
    )
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
