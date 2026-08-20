import sys
import types

import pytest


class _SheetsAtomicWriteError(RuntimeError):
    rollback_ok = None


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

from app.services import transaction_service


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


def _txn(txn_id="txn_1", row=5, amount=100):
    return {
        "id": txn_id,
        "date": "2026-08-08",
        "type": "expense",
        "amount": amount,
        "category": "Food & Beverage",
        "account": "Cash",
        "to_account": "",
        "subject": "",
        "description": "Kopi",
        "catatan": "",
        "tipe_pengeluaran": "",
        "raw_input": "kopi 100",
        "parsed_by": "regex",
        "hutang_id": "",
        "tipe_hutang": "",
        "_row_index": row,
    }


def test_canonical_id_survives_row_shift_without_retargeting(monkeypatch):
    current = _txn(row=20)
    stale_row_occupant = _txn("txn_other", row=5)
    monkeypatch.setattr(transaction_service, "get_transactions_by_ids", lambda ids: [current])
    monkeypatch.setattr(transaction_service, "get_transactions_by_row_indices", lambda rows: [stale_row_occupant])

    resolved = transaction_service.get_single_transaction_by_ref(row_index=5, txn_id="txn_1")

    assert resolved["id"] == "txn_1"
    assert resolved["_row_index"] == 20


def test_duplicate_transaction_id_fails_closed_even_with_row_hint(monkeypatch):
    monkeypatch.setattr(transaction_service, "get_transactions_by_ids", lambda ids: [_txn(row=5), _txn(row=20)])
    monkeypatch.setattr(transaction_service, "get_transactions_by_row_indices", lambda rows: [_txn(row=5)])

    with pytest.raises(ValueError, match="duplikat"):
        transaction_service.get_single_transaction_by_ref(row_index=5, txn_id="txn_1")


def test_delete_preview_excludes_duplicate_id_from_deletable_set(monkeypatch):
    records = [_txn("dup", row=5), _txn("dup", row=7), _txn("ok", row=9)]
    monkeypatch.setattr(transaction_service, "get_transactions_with_row_index", lambda: records)

    preview = transaction_service.preview_delete_transactions_by_refs(txn_ids=["dup", "ok"])

    assert preview["duplicate_ids"] == ["dup"]
    assert [x["id"] for x in preview["deletable"]] == ["ok"]
    assert "dup" not in preview["missing_ids"]


def test_expected_signature_detects_material_change_not_row_change(monkeypatch):
    before = _txn(row=5, amount=100)
    moved = _txn(row=20, amount=100)
    changed = _txn(row=20, amount=200)
    signature = transaction_service.transaction_material_signature(before)

    monkeypatch.setattr(transaction_service, "get_transactions_by_ids", lambda ids: [moved])
    monkeypatch.setattr(transaction_service, "get_transactions_by_row_indices", lambda rows: [_txn("other", row=5)])
    ok = transaction_service.preview_edit_transaction_by_ref(
        {"description": "Kopi baru"}, row_index=5, txn_id="txn_1", expected_signature=signature
    )
    assert ok["success"] is True
    assert ok["old_txn"]["_row_index"] == 20

    monkeypatch.setattr(transaction_service, "get_transactions_by_ids", lambda ids: [changed])
    stale = transaction_service.preview_edit_transaction_by_ref(
        {"description": "Kopi baru"}, row_index=5, txn_id="txn_1", expected_signature=signature
    )
    assert stale["success"] is False
    assert stale.get("stale") is True


def test_delete_revalidation_aborts_when_deletable_blocked_composition_changes(monkeypatch):
    txn = _txn("txn_1", row=9)
    monkeypatch.setattr(transaction_service, "preview_delete_transactions_by_refs", lambda *a, **k: {
        "success": True,
        "deletable": [],
        "blocked": [txn],
        "missing_ids": [],
        "missing_rows": [],
        "duplicate_ids": [],
        "reverse_deltas": {},
    })
    monkeypatch.setattr(
        transaction_service,
        "apply_account_deltas",
        lambda *_a, **_k: pytest.fail("delete wrote balance after eligibility changed"),
    )

    result = transaction_service.delete_transactions_by_refs(
        txn_ids=["txn_1"],
        expected_deletable_ids=["txn_1"],
        expected_blocked_ids=[],
        expected_signatures={"txn_1": transaction_service.transaction_material_signature(txn)},
    )

    assert result["success"] is False
    assert result.get("stale") is True
    assert "Komposisi" in result["message"] or "Eligibility" in result["message"]


def test_delete_post_balance_failure_is_typed_for_outer_rollback(monkeypatch):
    txn = _txn("txn_1", row=9)
    monkeypatch.setattr(transaction_service, "preview_delete_transactions_by_refs", lambda *a, **k: {
        "success": True,
        "deletable": [txn],
        "blocked": [],
        "missing_ids": [],
        "missing_rows": [],
        "duplicate_ids": [],
        "reverse_deltas": {"Cash": 100},
    })
    monkeypatch.setattr(transaction_service, "apply_account_deltas", lambda _d: {"failed_accounts": [], "new_balances": {"Cash": 1000}})
    monkeypatch.setattr(
        transaction_service,
        "delete_rows",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("row delete failed")),
    )

    with pytest.raises(Exception) as exc:
        transaction_service.delete_transactions_by_refs(
            txn_ids=["txn_1"],
            expected_deletable_ids=["txn_1"],
            expected_blocked_ids=[],
            void_debts_for_transaction_fn=lambda *_a, **_k: {"success": True, "voided_ids": []},
        )
    assert type(exc.value).__name__ == "PartialMutationError"
    assert "Row transaksi gagal dihapus" in str(exc.value)


def test_delete_dependency_drift_aborts_before_balance_write(monkeypatch):
    txn = _txn("txn_dep", row=11)
    monkeypatch.setattr(transaction_service, "preview_delete_transactions_by_refs", lambda *a, **k: {
        "success": True,
        "deletable": [txn],
        "blocked": [],
        "missing_ids": [],
        "missing_rows": [],
        "duplicate_ids": [],
        "reverse_deltas": {"Cash": 100},
    })
    monkeypatch.setattr(
        transaction_service,
        "apply_account_deltas",
        lambda *_a, **_k: pytest.fail("balance write occurred after dependency drift"),
    )

    result = transaction_service.delete_transactions_by_refs(
        txn_ids=["txn_dep"],
        expected_deletable_ids=["txn_dep"],
        expected_blocked_ids=[],
        expected_dependency_signatures={"txn_dep": (("old",),)},
        dependency_signature_fn=lambda _txn: (("new",),),
    )

    assert result["success"] is False
    assert result.get("stale") is True
    assert "Dependency debt" in result["message"]
