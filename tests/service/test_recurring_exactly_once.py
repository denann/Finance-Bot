"""Recurring occurrence idempotency and failure tests for single-process mode."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from tests.fakes.external_modules import install_external_stubs

install_external_stubs()

from app.services import recurring_service


def _rule(next_run_date: str = "2026-07-10") -> dict:
    return {
        "id": "rec_1",
        "name": "Internet",
        "type": "expense",
        "amount": 100_000,
        "category": "Bills & Utilities",
        "account": "BRI",
        "next_run_date": next_run_date,
        "frequency": "monthly",
        "day_of_month": 10,
        "is_active": "TRUE",
    }


def test_duplicate_occurrence_returns_idempotent_result_without_second_save() -> None:
    """Two callbacks for one rule/due-date produce at most one transaction."""

    logs: list[dict] = []
    saves: list[str] = []

    def find_run(rule_id, run_date):
        return next((row for row in logs if row["rule_id"] == rule_id and row["run_date"] == run_date), None)

    def save_transaction(_parsed, raw_input):
        saves.append(raw_input)
        return {"success": True, "transaction_id": "txn_1", "new_balances": {}}

    def log_run(**kwargs):
        row = {**kwargs, "id": "log_1"}
        logs.append(row)
        return row

    with (
        patch.object(recurring_service, "get_recurring_rule_by_id", return_value=_rule()),
        patch.object(recurring_service, "find_processed_recurring_run", side_effect=find_run),
        patch.object(recurring_service, "save_transaction", side_effect=save_transaction),
        patch.object(recurring_service, "update_recurring_rule_cells", return_value=True),
        patch.object(recurring_service, "log_recurring_run", side_effect=log_run),
    ):
        first = recurring_service.mark_recurring_rule_paid(
            "rec_1", date(2026, 7, 10), scheduled_run_date=date(2026, 7, 10)
        )
        second = recurring_service.mark_recurring_rule_paid(
            "rec_1", date(2026, 7, 10), scheduled_run_date=date(2026, 7, 10)
        )

    assert first["success"] is True and first["duplicate"] is False
    assert second["success"] is True and second["duplicate"] is True
    assert saves == ["recurring:rec_1"]


def test_stale_or_not_due_occurrence_is_rejected_before_write() -> None:
    """Old reminder months and future occurrences never reach transaction save."""

    with (
        patch.object(recurring_service, "get_recurring_rule_by_id", return_value=_rule("2026-08-10")),
        patch.object(recurring_service, "save_transaction") as save,
    ):
        stale = recurring_service.mark_recurring_rule_paid(
            "rec_1", date(2026, 8, 10), scheduled_run_date=date(2026, 7, 10)
        )
        not_due = recurring_service.mark_recurring_rule_paid(
            "rec_1", date(2026, 7, 10), scheduled_run_date=date(2026, 8, 10)
        )

    assert stale["success"] is False and stale["stale"] is True
    assert not_due["success"] is False and not_due["not_due"] is True
    save.assert_not_called()


def test_transaction_or_log_failure_does_not_report_recurring_success() -> None:
    """Failure before or after transaction creation returns an explicit failure."""

    with (
        patch.object(recurring_service, "get_recurring_rule_by_id", return_value=_rule()),
        patch.object(recurring_service, "find_processed_recurring_run", return_value=None),
        patch.object(recurring_service, "save_transaction", return_value={"success": False, "message": "save failed"}),
        patch.object(recurring_service, "rollback_current_sheets_transaction", return_value=True),
    ):
        transaction_failure = recurring_service.mark_recurring_rule_paid(
            "rec_1", date(2026, 7, 10), scheduled_run_date=date(2026, 7, 10)
        )

    with (
        patch.object(recurring_service, "get_recurring_rule_by_id", return_value=_rule()),
        patch.object(recurring_service, "find_processed_recurring_run", return_value=None),
        patch.object(recurring_service, "save_transaction", return_value={"success": True, "transaction_id": "txn_1"}),
        patch.object(recurring_service, "update_recurring_rule_cells", return_value=True),
        patch.object(recurring_service, "log_recurring_run", side_effect=RuntimeError("log failed")),
        patch.object(recurring_service, "rollback_current_sheets_transaction", return_value=True),
    ):
        log_failure = recurring_service.mark_recurring_rule_paid(
            "rec_1", date(2026, 7, 10), scheduled_run_date=date(2026, 7, 10)
        )

    assert transaction_failure["success"] is False
    assert transaction_failure["commit_status"] == "rolled_back"
    assert log_failure["success"] is False
    assert log_failure["commit_status"] == "rolled_back"
