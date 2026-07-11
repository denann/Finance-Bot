"""Expected-failure reproductions for Phase 0 risks not closed in 0.1."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.fakes.external_modules import install_external_stubs

install_external_stubs()

from app.services import recurring_service
from app.sheets import client as sheets_client


ROOT = Path(__file__).resolve().parents[2]


def test_transaction_preview_callback_contains_opaque_action_identity() -> None:
    """The current static callback proves two previews can share one target."""

    source = (ROOT / "app/bot/handler_parts/transaction_flow.py").read_text(encoding="utf-8")
    assert 'callback_data=f"confirm:{action_id}"' in source


def test_post_mutation_result_failure_uses_typed_operation_error() -> None:
    """Delete currently returns a failure dictionary after reversing balance."""

    source = (ROOT / "app/services/transaction_service.py").read_text(encoding="utf-8")
    assert "raise PartialMutationError" in source


def test_same_recurring_occurrence_is_saved_only_once() -> None:
    """Calling the current service twice reproduces duplicate logical runs."""

    rule = {
        "id": "rec_1",
        "name": "Internet",
        "type": "expense",
        "amount": 100_000,
        "category": "Bills & Utilities",
        "account": "BRI",
        "next_run_date": "2026-07-10",
        "frequency": "monthly",
        "day_of_month": 10,
        "is_active": "TRUE",
    }
    saved: list[str] = []
    logs: list[dict] = []

    def save_once(_parsed, raw_input):
        saved.append(raw_input)
        return {"success": True, "transaction_id": f"txn_{len(saved)}", "new_balances": {}}

    def find_run(rule_id, run_date):
        return next((row for row in logs if row["rule_id"] == rule_id and row["run_date"] == run_date), None)

    def log_run(**kwargs):
        row = {**kwargs, "id": "log_1"}
        logs.append(row)
        return row

    with (
        patch.object(recurring_service, "get_recurring_rule_by_id", return_value=rule),
        patch.object(recurring_service, "save_transaction", side_effect=save_once),
        patch.object(recurring_service, "find_processed_recurring_run", side_effect=find_run),
        patch.object(recurring_service, "update_recurring_rule_cells", return_value=True),
        patch.object(recurring_service, "log_recurring_run", side_effect=log_run),
    ):
        recurring_service.mark_recurring_rule_paid("rec_1", date(2026, 7, 10))
        recurring_service.mark_recurring_rule_paid("rec_1", date(2026, 7, 10))

    assert len(saved) == 1


def test_ambiguous_append_is_not_blindly_retried() -> None:
    """The generic retry currently invokes an ambiguous append twice."""

    calls = 0

    def ambiguous_append():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("500 backend error after server-side commit")
        return "ok"

    with (
        patch.object(sheets_client.time, "sleep"),
        patch.object(sheets_client.random, "uniform", return_value=0),
    ):
        result = sheets_client._call_with_retry(
            ambiguous_append,
            max_retries=2,
            operation="non_idempotent_write",
            reconcile=lambda: "reconciled",
        )

    assert calls == 1
    assert result == "reconciled"
