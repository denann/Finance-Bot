"""Server-side transaction sorting and read-order parity tests."""

from __future__ import annotations

from app.services import transaction_service
from tests.fakes.sheets import FailurePlan, InMemoryWorksheet


def test_transaction_sort_uses_server_request_without_full_read_or_update(monkeypatch) -> None:
    monkeypatch.setattr(transaction_service, "TRANSACTION_SORT_MODE", "server")
    sheet = InMemoryWorksheet(
        "transactions",
        [["id", "date"], ["txn_1", "2026-01-01"], ["txn_2", "2026-02-01"]],
    )
    monkeypatch.setattr("app.sheets.client.get_sheet", lambda name: sheet)

    result = transaction_service.sort_transactions_sheet_by_date(desc=True)

    assert result["success"] is True
    assert sheet.failure_plan.calls == {"sort": 1}
    assert sheet.rows[1][0] == "txn_2"


def test_server_sort_excludes_header_and_uses_date_then_id_descending(monkeypatch) -> None:
    monkeypatch.setattr(transaction_service, "TRANSACTION_SORT_MODE", "server")
    sheet = InMemoryWorksheet(
        "transactions",
        [["id", "date"], ["txn_1", "2026-02-01"], ["txn_3", "2026-02-01"], ["txn_2", "2026-01-01"]],
    )
    monkeypatch.setattr("app.sheets.client.get_sheet", lambda name: sheet)
    result = transaction_service.sort_transactions_sheet_by_date()
    assert result["success"] is True
    assert sheet.rows[0] == ["id", "date"]
    assert [row[0] for row in sheet.rows[1:]] == ["txn_3", "txn_1", "txn_2"]


def test_sort_failure_does_not_retry_append_or_report_financial_failure(monkeypatch) -> None:
    append_calls = []
    monkeypatch.setattr(transaction_service, "validate_transaction", lambda parsed: (True, "ok"))
    monkeypatch.setattr(transaction_service, "ensure_category_for_transaction", lambda category, txn_type: category)
    monkeypatch.setattr(transaction_service, "calculate_account_deltas", lambda items: {})
    monkeypatch.setattr(transaction_service, "validate_accounts_exist", lambda deltas: (True, []))
    monkeypatch.setattr(transaction_service, "build_transaction_row", lambda parsed, raw: ("txn_once", ["txn_once", "2026-01-01"]))
    monkeypatch.setattr(transaction_service, "append_row", lambda sheet, row: append_calls.append(list(row)))
    monkeypatch.setattr(transaction_service, "sort_transactions_sheet_by_date", lambda desc=True: {"success": False, "message": "maintenance failed"})
    monkeypatch.setattr(transaction_service, "apply_account_deltas", lambda deltas: {"success": True, "new_balances": {}, "failed_accounts": []})

    result = transaction_service.save_transaction(
        {"type": "expense", "amount": 10_000, "category": "Food & Beverage", "account": "Cash"},
        "synthetic",
    )

    assert result["success"] is True
    assert len(append_calls) == 1


def test_recent_transactions_sorts_unsorted_and_malformed_physical_rows(monkeypatch) -> None:
    records = [
        {"id": "bad", "date": "not-a-date"},
        {"id": "old", "date": "2026-01-01"},
        {"id": "newer-a", "date": "2026-02-01"},
        {"id": "newer-b", "date": "2026-02-01"},
    ]
    monkeypatch.setattr(transaction_service, "get_all_records", lambda sheet: records)
    result = transaction_service.get_recent_transactions(limit=10)
    assert [row["id"] for row in result] == ["newer-b", "newer-a", "old", "bad"]


def test_legacy_sort_mode_is_explicit_and_preserves_ordering_parity(monkeypatch) -> None:
    sheet = InMemoryWorksheet(
        "transactions",
        [["id", "date"], ["txn_1", "2026-01-01"], ["txn_2", "2026-02-01"]],
    )
    rewrites = []

    def apply_rewrite(name, cell_range, values):
        rewrites.append((name, cell_range, values))
        sheet.rows[1:] = [list(row) for row in values]

    monkeypatch.setattr(transaction_service, "TRANSACTION_SORT_MODE", "legacy")
    monkeypatch.setattr(transaction_service, "get_sheet", lambda name: sheet)
    monkeypatch.setattr(transaction_service, "update_range", apply_rewrite)

    result = transaction_service.sort_transactions_sheet_by_date(desc=True)

    assert result["success"] is True
    assert [row[0] for row in sheet.rows[1:]] == ["txn_2", "txn_1"]
    assert sheet.failure_plan.calls == {"get_all_values": 1}
    assert [(name, cell_range) for name, cell_range, _values in rewrites] == [("transactions", "A2:B3")]


def _patch_real_transaction_save_dependencies(monkeypatch, sheet: InMemoryWorksheet, *, balance_result=None):
    from app.sheets import client as sheets_client

    monkeypatch.setattr(transaction_service, "TRANSACTION_SORT_MODE", "server")
    monkeypatch.setattr(sheets_client, "get_sheet", lambda name: sheet)
    monkeypatch.setattr(transaction_service, "validate_transaction", lambda parsed: (True, "ok"))
    monkeypatch.setattr(transaction_service, "ensure_category_for_transaction", lambda category, txn_type: category)
    monkeypatch.setattr(transaction_service, "calculate_account_deltas", lambda items: {"Cash": -10_000})
    monkeypatch.setattr(transaction_service, "validate_accounts_exist", lambda deltas: (True, []))
    monkeypatch.setattr(
        transaction_service,
        "build_transaction_row",
        lambda parsed, raw: ("txn_new", ["txn_new", "2026-03-01"]),
    )
    monkeypatch.setattr(
        transaction_service,
        "apply_account_deltas",
        lambda deltas: balance_result
        if balance_result is not None
        else {"success": True, "new_balances": {"Cash": 90_000}, "failed_accounts": []},
    )


def test_sort_is_deferred_until_financial_transaction_commits(monkeypatch) -> None:
    from app.sheets.client import sheets_transaction

    sheet = InMemoryWorksheet(
        "transactions",
        [["id", "date"], ["txn_old", "2026-01-01"]],
    )
    _patch_real_transaction_save_dependencies(monkeypatch, sheet)

    with sheets_transaction("save-with-post-commit-sort"):
        result = transaction_service.save_transaction(
            {"type": "expense", "amount": 10_000, "category": "Food & Beverage", "account": "Cash"},
            "kopi",
        )
        assert result["success"] is True
        assert sheet.failure_plan.calls.get("sort", 0) == 0

    assert sheet.failure_plan.calls.get("sort", 0) == 1
    assert [row[0] for row in sheet.rows[1:]] == ["txn_new", "txn_old"]


def test_balance_failure_rolls_back_new_logical_id_without_sorting(monkeypatch) -> None:
    from app.sheets.client import sheets_transaction

    sheet = InMemoryWorksheet(
        "transactions",
        [["id", "date"], ["txn_old_1", "2026-01-01"], ["txn_old_2", "2026-02-01"]],
    )
    _patch_real_transaction_save_dependencies(
        monkeypatch,
        sheet,
        balance_result={"success": False, "new_balances": {}, "failed_accounts": ["Cash"]},
    )

    with sheets_transaction("save-rollback-before-sort"):
        result = transaction_service.save_transaction(
            {"type": "expense", "amount": 10_000, "category": "Food & Beverage", "account": "Cash"},
            "kopi",
        )
        assert result["success"] is False
        assert result["rollback_status"] == "rollback_succeeded"

    assert [row[0] for row in sheet.rows] == ["id", "txn_old_1", "txn_old_2"]
    assert sheet.failure_plan.calls.get("sort", 0) == 0


def test_post_commit_sort_failure_keeps_committed_transaction(monkeypatch) -> None:
    from app.sheets.client import sheets_transaction

    sheet = InMemoryWorksheet(
        "transactions",
        [["id", "date"], ["txn_old", "2026-01-01"]],
        failure_plan=FailurePlan({("sort", 1): RuntimeError("sort unavailable")}),
    )
    _patch_real_transaction_save_dependencies(monkeypatch, sheet)

    with sheets_transaction("save-sort-maintenance-failure") as tx:
        result = transaction_service.save_transaction(
            {"type": "expense", "amount": 10_000, "category": "Food & Beverage", "account": "Cash"},
            "kopi",
        )
        assert result["success"] is True

    assert [row[0] for row in sheet.rows] == ["id", "txn_old", "txn_new"]
    assert tx.post_commit_errors
    assert sheet.failure_plan.calls.get("append_row", 0) == 1
    assert sheet.failure_plan.calls.get("sort", 0) == 1
