import sys
import types

import pytest


# This archive intentionally omits gspread. Stub only the Sheets boundary so the
# service module itself can be exercised with deterministic in-memory fakes.
sheets = types.ModuleType("app.sheets.client")
class _SheetsAtomicWriteError(RuntimeError):
    rollback_ok = None
sheets.SheetsAtomicWriteError = _SheetsAtomicWriteError
for _name in [
    "append_row", "append_row_raw", "append_rows", "delete_rows", "find_row_index",
    "get_all_records", "get_sheet", "get_current_sheets_transaction",
    "rollback_current_sheets_transaction", "sort_range", "update_cell", "update_range", "update_row",
]:
    setattr(sheets, _name, lambda *a, _n=_name, **k: [] if _n == "get_all_records" else None)
_prior_sheets_client = sys.modules.get("app.sheets.client")
sys.modules["app.sheets.client"] = sheets

from app.services import debt_service
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


def test_split_prevalidation_rejects_invalid_required_share_before_writer(monkeypatch):
    calls = []
    monkeypatch.setattr(debt_service, "add_debt", lambda *a, **k: calls.append((a, k)) or {"success": True})

    result = debt_service.create_split_bill_receivables([("A", 100), ("B", 0)])

    assert result["success"] is False
    assert calls == []


def test_split_failure_after_writer_invocation_raises_partial_mutation(monkeypatch):
    calls = []

    def fake_add(_kind, person, amount, **kwargs):
        calls.append((person, amount))
        if person == "B":
            return {"success": False, "message": "second write failed"}
        return {"success": True, "debt_id": f"debt_{person}", "person_name": person, "remaining": amount}

    monkeypatch.setattr(debt_service, "add_debt", fake_add)

    with pytest.raises(PartialMutationError, match="second write failed"):
        debt_service.create_split_bill_receivables([("A", 100), ("B", 200)])
    assert calls == [("A", 100.0), ("B", 200.0)]


def test_multi_debt_void_prevalidates_whole_set_before_first_write():
    writes = []

    def preview(debt_id):
        if debt_id == "B":
            return {"success": False, "message": "B changed"}
        return {"success": True}

    result = debt_service.void_debt_ids(
        ["A", "B"],
        prevalidate_fn=preview,
        void_debt_fn=lambda debt_id, _: writes.append(debt_id) or {"success": True},
    )

    assert result["success"] is False
    assert writes == []


def test_multi_debt_void_later_writer_failure_reaches_outer_boundary():
    writes = []

    def writer(debt_id, _):
        writes.append(debt_id)
        if debt_id == "B":
            return {"success": False, "message": "B writer failed"}
        return {"success": True, "debt": {"id": debt_id, "original_amount": 100, "remaining_amount": 0}}

    with pytest.raises(PartialMutationError, match="B writer failed"):
        debt_service.void_debt_ids(
            ["A", "B"],
            prevalidate_fn=lambda _: {"success": True},
            void_debt_fn=writer,
        )
    assert writes == ["A", "B"]


def _pristine_debt(txn_id="txn_1"):
    return {
        "id": "debt_1",
        "type": "receivable",
        "person_name": "Raka",
        "original_amount": 470_000,
        "remaining_amount": 470_000,
        "is_settled": "FALSE",
        "source_transaction_id": txn_id,
    }


def test_pristine_relation_allowed_but_payment_history_blocks(monkeypatch):
    txn = {"id": "txn_1", "hutang_id": "debt_1", "tipe_hutang": "piutang"}
    debt = _pristine_debt()
    monkeypatch.setattr(debt_service, "build_debts_index", lambda active_only=False: {
        "items": [debt], "by_id": {"debt_1": debt}, "by_source_txn": {"txn_1": [debt]}
    })
    monkeypatch.setattr(debt_service, "get_debts_linked_to_transaction_record", lambda *a, **k: [debt])

    monkeypatch.setattr(debt_service, "get_all_records", lambda sheet: [
        {"debt_id": "debt_1", "note": "[add_receivable] initial"}
    ])
    ok = debt_service.preview_pristine_relation_detach(txn)
    assert ok["success"] is True

    monkeypatch.setattr(debt_service, "get_all_records", lambda sheet: [
        {"debt_id": "debt_1", "note": "[add_receivable] initial"},
        {"debt_id": "debt_1", "note": "[payment] cicilan"},
    ])
    blocked = debt_service.preview_pristine_relation_detach(txn)
    assert blocked["success"] is False
    assert blocked["repair_required"] is False


def test_consistent_multi_relation_split_remains_eligible_when_both_sides_agree(monkeypatch):
    txn = {"id": "txn_1", "hutang_id": "debt_A,debt_B", "tipe_hutang": "piutang"}
    debt_a = _pristine_debt("txn_1") | {"id": "debt_A"}
    debt_b = _pristine_debt("txn_1") | {"id": "debt_B", "person_name": "Bima", "original_amount": 220_000, "remaining_amount": 220_000}
    monkeypatch.setattr(debt_service, "build_debts_index", lambda active_only=False: {
        "items": [debt_a, debt_b],
        "by_id": {"debt_A": debt_a, "debt_B": debt_b},
        "by_source_txn": {"txn_1": [debt_a, debt_b]},
    })
    monkeypatch.setattr(debt_service, "get_all_records", lambda _sheet: [
        {"debt_id": "debt_A", "note": "[add_receivable] initial"},
        {"debt_id": "debt_B", "note": "[add_receivable] initial"},
    ])

    preview = debt_service.preview_pristine_relation_detach(txn)

    assert preview["success"] is True
    assert preview["debt_ids"] == ["debt_A", "debt_B"]


def test_inconsistent_two_sided_relation_fails_closed_before_detach(monkeypatch):
    txn = {"id": "txn_1", "hutang_id": "debt_A", "tipe_hutang": "piutang"}
    debt_a = _pristine_debt("txn_1") | {"id": "debt_A"}
    debt_b = _pristine_debt("txn_1") | {"id": "debt_B", "person_name": "Bima"}
    monkeypatch.setattr(debt_service, "build_debts_index", lambda active_only=False: {
        "items": [debt_a, debt_b],
        "by_id": {"debt_A": debt_a, "debt_B": debt_b},
        "by_source_txn": {"txn_1": [debt_a, debt_b]},
    })
    monkeypatch.setattr(debt_service, "get_all_records", lambda _sheet: [])

    preview = debt_service.preview_pristine_relation_detach(txn)

    assert preview["success"] is False
    assert preview["repair_required"] is True
    assert preview["transaction_side_ids"] == ["debt_A"]
    assert preview["debt_side_ids"] == ["debt_A", "debt_B"]
    assert "berbeda" in preview["message"]


def test_relation_only_detach_never_calls_account_delta_writer(monkeypatch):
    txn = {"id": "txn_1", "hutang_id": "debt_1", "tipe_hutang": "piutang", "amount": 890_000}
    debt = _pristine_debt() | {"_row_index": 7}
    monkeypatch.setattr(debt_service, "preview_pristine_relation_detach", lambda _txn: {
        "success": True, "debt_ids": ["debt_1"], "debts": [debt]
    })
    voided = []
    monkeypatch.setattr(debt_service, "void_linked_debt_only", lambda debt_id, reason="": voided.append(debt_id) or {
        "success": True, "debt_id": debt_id, "skipped": False
    })
    source_clears = []
    monkeypatch.setattr(
        debt_service, "update_cell",
        lambda sheet, row, col, value: source_clears.append((sheet, row, col, value)),
    )

    result = debt_service.detach_pristine_relations_for_transaction(txn)

    assert result["success"] is True
    assert voided == ["debt_1"]
    assert source_clears == [(debt_service.SHEET_DEBTS, 7, debt_service.DEBT_SOURCE_TRANSACTION_ID_COL, "")]
    # The relation-detach service has no account-balance collaborator at all;
    # historical gross cash (e.g. 890k) cannot be posted again here.
    assert "new_balances" not in result


def test_delete_dependency_signature_detects_debt_side_relation_and_history(monkeypatch):
    txn = {"id": "txn_dep", "hutang_id": "", "tipe_hutang": ""}
    monkeypatch.setattr(debt_service, "build_debts_index", lambda active_only=False: {
        "items": [], "by_id": {}, "by_source_txn": {}
    })
    monkeypatch.setattr(debt_service, "get_all_records", lambda _sheet: [])
    before = debt_service.transaction_debt_dependency_signature(txn)

    linked = _pristine_debt("txn_dep") | {"_row_index": 8}
    monkeypatch.setattr(debt_service, "build_debts_index", lambda active_only=False: {
        "items": [linked], "by_id": {"debt_1": linked}, "by_source_txn": {"txn_dep": [linked]}
    })
    monkeypatch.setattr(debt_service, "get_all_records", lambda _sheet: [
        {"id": "pay_1", "debt_id": "debt_1", "amount": 1, "date": "2026-08-08", "note": "[payment] changed"}
    ])
    after = debt_service.transaction_debt_dependency_signature(txn)

    assert before != after
    assert after[0][0][0] == "debt_1"
    assert after[1][0][1] == "debt_1"


def test_delete_debt_prevalidation_includes_settled_debt_side_relation(monkeypatch):
    settled = _pristine_debt("txn_delete") | {"is_settled": "TRUE", "remaining_amount": 0}
    monkeypatch.setattr(
        debt_service,
        "get_debts_by_source_transaction_id",
        lambda txn_id, active_only=False: [settled] if txn_id == "txn_delete" and active_only is False else [],
    )
    monkeypatch.setattr(debt_service, "build_debts_index", lambda active_only=False: {
        "items": [settled], "by_id": {"debt_1": settled}, "by_source_txn": {"txn_delete": [settled]}
    })

    result = debt_service.preview_void_debts_for_transaction("txn_delete", [])

    assert result["success"] is False
    assert result["failed"][0]["reason"] == "settled"


def test_delete_debt_prevalidation_pristine_relation_matches_writer_target_set(monkeypatch):
    pristine = _pristine_debt("txn_delete")
    monkeypatch.setattr(
        debt_service,
        "get_debts_by_source_transaction_id",
        lambda txn_id, active_only=False: [pristine] if txn_id == "txn_delete" and active_only is False else [],
    )
    monkeypatch.setattr(debt_service, "build_debts_index", lambda active_only=False: {
        "items": [pristine], "by_id": {"debt_1": pristine}, "by_source_txn": {"txn_delete": [pristine]}
    })

    result = debt_service.preview_void_debts_for_transaction("txn_delete", [])

    assert result == {"success": True, "message": "ok", "debt_ids": ["debt_1"], "failed": []}
