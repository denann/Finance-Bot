"""Retry policy tests for logical-ID reconciliation of Sheets appends."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.fakes.external_modules import install_external_stubs
from tests.fakes.sheets import InMemoryWorksheet

install_external_stubs()

from app.sheets import client


def test_ambiguous_append_reconciles_existing_id_without_second_row() -> None:
    """A server-side commit followed by 500 is recognized by logical ID."""

    sheet = InMemoryWorksheet("transactions", [["id"]])
    attempts = 0

    def ambiguous_append(row, **_kwargs):
        nonlocal attempts
        attempts += 1
        sheet.rows.append(list(row))
        raise RuntimeError("500 backend error after server-side commit")

    sheet.append_row = ambiguous_append
    with (
        patch.object(client, "get_sheet", return_value=sheet),
        patch.object(client.time, "sleep"),
        patch.object(client.random, "uniform", return_value=0),
    ):
        response = client.append_row("transactions", ["txn_1", "2026-07-10"])

    assert attempts == 1
    assert [row[0] for row in sheet.rows].count("txn_1") == 1
    assert response["reconciled"] is True


def test_non_idempotent_write_without_logical_id_returns_unknown() -> None:
    """Blind append retry is forbidden when reconciliation is impossible."""

    with pytest.raises(client.SheetsCommitOutcomeUnknownError):
        client._call_with_retry(
            lambda: (_ for _ in ()).throw(RuntimeError("500 backend error")),
            max_retries=2,
            operation="non_idempotent_write",
        )


def test_partial_batch_reconciliation_returns_unknown_instead_of_reappend() -> None:
    """A partially visible batch is not assumed all-or-nothing or retried."""

    sheet = InMemoryWorksheet("transactions", [["id"], ["txn_1"]])
    with pytest.raises(client.SheetsCommitOutcomeUnknownError):
        client._reconcile_batch_append(sheet, ["txn_1", "txn_2"])
