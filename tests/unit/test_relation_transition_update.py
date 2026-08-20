import sys
import types

import pytest


class _SheetsAtomicWriteError(RuntimeError):
    rollback_ok = None


# The archive omits gspread; isolate only the external Sheets boundary while
# exercising the real application/service coordinator.
sheets = types.ModuleType("app.sheets.client")
sheets.SheetsAtomicWriteError = _SheetsAtomicWriteError
for name in [
    "append_row", "append_row_raw", "append_rows", "delete_rows", "find_row_index", "get_all_records",
    "get_sheet", "get_current_sheets_transaction", "rollback_current_sheets_transaction",
    "sort_range", "update_cell", "update_range", "update_row",
]:
    setattr(sheets, name, lambda *a, **k: [] if name == "get_all_records" else None)
_prior_sheets_client = sys.modules.get("app.sheets.client")
sys.modules["app.sheets.client"] = sheets

from app.application import transaction_debt
from app.services.operation_errors import PartialMutationError


def _restore_sheets_stub_after_import():
    # Do not poison collection of unrelated repository tests. Imported service
    # modules keep the bound test doubles they need, while later imports of the
    # Sheets module see the real repository module (and its real environment).
    import app.sheets as _sheets_pkg
    if _prior_sheets_client is None:
        sys.modules.pop("app.sheets.client", None)
        if getattr(_sheets_pkg, "client", None) is sheets:
            delattr(_sheets_pkg, "client")
    else:
        sys.modules["app.sheets.client"] = _prior_sheets_client
        _sheets_pkg.client = _prior_sheets_client


_restore_sheets_stub_after_import()


def _gross_split_txn():
    return {
        "id": "txn_gross_890",
        "date": "2026-08-01",
        "type": "expense",
        "amount": 890_000,
        "category": "Food & Beverage",
        "account": "BCA",
        "to_account": "",
        "subject": "",
        "description": "Makan bareng",
        "catatan": "",
        "tipe_pengeluaran": "",
        "raw_input": "",
        "parsed_by": "regex",
        "hutang_id": "debt_470",
        "tipe_hutang": "piutang",
        "_row_index": 5,
    }


def test_pristine_relation_only_conversion_keeps_id_and_never_replays_cash(monkeypatch):
    txn = _gross_split_txn()
    signature = ("stable",)
    monkeypatch.setattr(transaction_debt.transaction_service, "get_single_transaction_by_ref", lambda **_: dict(txn))
    monkeypatch.setattr(transaction_debt.transaction_service, "transaction_material_signature", lambda _: signature)
    # Any ordinary transaction writer here could apply account deltas. A pure
    # relation conversion must not call it at all.
    monkeypatch.setattr(
        transaction_debt.transaction_service,
        "edit_transaction_by_ref",
        lambda *a, **k: pytest.fail("relation-only conversion replayed transaction/account write"),
    )
    monkeypatch.setattr(
        transaction_debt.debt_service,
        "preview_pristine_relation_detach",
        lambda _: {"success": True, "debt_ids": ["debt_470"], "debts": [{"id": "debt_470"}]},
    )
    detached = []
    monkeypatch.setattr(
        transaction_debt.debt_service,
        "detach_pristine_relations_for_transaction",
        lambda _: detached.append("debt_470") or {"success": True, "voided": ["debt_470"]},
    )
    cleared = []
    monkeypatch.setattr(
        transaction_debt.transaction_service,
        "clear_transaction_debt_relation",
        lambda txn_id: cleared.append(txn_id) or {"success": True},
    )

    result = transaction_debt.edit_transaction_by_ref(
        {}, txn_id=txn["id"], row_index=txn["_row_index"],
        expected_signature=signature, relation_transition="detach_pristine",
    )

    assert result["success"] is True
    assert result["new_txn"]["id"] == "txn_gross_890"
    assert result["new_txn"]["amount"] == 890_000
    assert result["new_txn"]["hutang_id"] == ""
    assert result["new_balances"] == {}
    assert detached == ["debt_470"]
    assert cleared == ["txn_gross_890"]


def test_non_pristine_relation_blocks_before_detach_or_transaction_write(monkeypatch):
    txn = _gross_split_txn()
    monkeypatch.setattr(transaction_debt.transaction_service, "get_single_transaction_by_ref", lambda **_: dict(txn))
    monkeypatch.setattr(transaction_debt.transaction_service, "transaction_material_signature", lambda _: ("stable",))
    monkeypatch.setattr(
        transaction_debt.debt_service,
        "preview_pristine_relation_detach",
        lambda _: {"success": False, "message": "Relation has payment history", "repair_required": False},
    )
    monkeypatch.setattr(
        transaction_debt.debt_service,
        "detach_pristine_relations_for_transaction",
        lambda _: pytest.fail("non-pristine relation was detached"),
    )
    monkeypatch.setattr(
        transaction_debt.transaction_service,
        "edit_transaction_by_ref",
        lambda *a, **k: pytest.fail("transaction write happened before eligibility"),
    )

    result = transaction_debt.edit_transaction_by_ref(
        {}, txn_id=txn["id"], expected_signature=("stable",), relation_transition="detach_pristine",
    )

    assert result["success"] is False
    assert "payment history" in result["message"]


def test_failure_after_relation_detach_is_promoted_to_partial_mutation(monkeypatch):
    txn = _gross_split_txn()
    monkeypatch.setattr(transaction_debt.transaction_service, "get_single_transaction_by_ref", lambda **_: dict(txn))
    monkeypatch.setattr(transaction_debt.transaction_service, "transaction_material_signature", lambda _: ("stable",))
    monkeypatch.setattr(transaction_debt.debt_service, "preview_pristine_relation_detach", lambda _: {"success": True, "debt_ids": ["debt_470"]})
    monkeypatch.setattr(transaction_debt.debt_service, "detach_pristine_relations_for_transaction", lambda _: {"success": True})
    monkeypatch.setattr(transaction_debt.transaction_service, "clear_transaction_debt_relation", lambda _: {"success": False, "message": "clear failed"})

    with pytest.raises(PartialMutationError, match="clear failed"):
        transaction_debt.edit_transaction_by_ref(
            {}, txn_id=txn["id"], expected_signature=("stable",), relation_transition="detach_pristine",
        )


def test_coordinated_delete_preview_blocks_changed_source_debt_before_write(monkeypatch):
    txn = _gross_split_txn() | {"hutang_id": "", "tipe_hutang": ""}
    base = {
        "success": True,
        "deletable": [dict(txn)],
        "blocked": [],
        "missing_ids": [],
        "missing_rows": [],
        "duplicate_ids": [],
        "reverse_deltas": {"BCA": 890_000},
    }
    monkeypatch.setattr(transaction_debt.transaction_service, "preview_delete_transactions_by_refs", lambda *a, **k: dict(base))
    monkeypatch.setattr(transaction_debt.transaction_service, "parse_transaction_debt_ids", lambda _txn: [])
    monkeypatch.setattr(
        transaction_debt.transaction_service,
        "calculate_reverse_deltas_for_delete",
        lambda rows: {"BCA": sum(float(x.get("amount", 0)) for x in rows)},
    )
    monkeypatch.setattr(
        transaction_debt.debt_service,
        "preview_void_debts_for_transaction",
        lambda txn_id, debt_ids: {"success": False, "message": "Debt sudah punya pembayaran/mutasi."},
    )

    preview = transaction_debt.preview_delete_transactions_by_refs(txn_ids=[txn["id"]])

    assert preview["deletable"] == []
    assert [x["id"] for x in preview["blocked"]] == [txn["id"]]
    assert "pembayaran/mutasi" in preview["blocked"][0]["_delete_block_reason"]
    assert preview["reverse_deltas"] == {"BCA": 0}


def test_coordinated_delete_preview_keeps_debt_payment_on_dedicated_reversal_path(monkeypatch):
    txn = _gross_split_txn() | {"category": "Bayar Utang", "hutang_id": "debt_pay", "tipe_hutang": "utang"}
    base = {
        "success": True, "deletable": [dict(txn)], "blocked": [],
        "missing_ids": [], "missing_rows": [], "duplicate_ids": [], "reverse_deltas": {},
    }
    monkeypatch.setattr(transaction_debt.transaction_service, "preview_delete_transactions_by_refs", lambda *a, **k: dict(base))
    monkeypatch.setattr(transaction_debt.transaction_service, "calculate_reverse_deltas_for_delete", lambda rows: {})
    monkeypatch.setattr(
        transaction_debt.debt_service,
        "preview_void_debts_for_transaction",
        lambda *a, **k: pytest.fail("payment transaction must keep its dedicated reversal semantics"),
    )

    preview = transaction_debt.preview_delete_transactions_by_refs(txn_ids=[txn["id"]])

    assert [x["id"] for x in preview["deletable"]] == [txn["id"]]
    assert preview["blocked"] == []
