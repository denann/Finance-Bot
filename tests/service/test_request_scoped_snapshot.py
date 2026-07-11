"""Request-scoped Sheets cache and row-budget contracts."""

from __future__ import annotations

import pytest

from app.application.finance_snapshot import FinanceDataSnapshot
from app.sheets import client
from tests.fakes.sheets import InMemoryWorksheet


def test_same_worksheet_is_loaded_once_and_returns_defensive_copies(monkeypatch) -> None:
    sheet = InMemoryWorksheet("transactions", [["id", "amount"], ["one", 1], ["two", 2]])
    monkeypatch.setattr(client, "get_sheet", lambda name: sheet)
    with client.sheets_request_snapshot() as snapshot:
        first = client.get_all_records("transactions")
        first[0]["amount"] = 999
        second = client.get_all_records("transactions")
    assert second[0]["amount"] == 1
    assert sheet.failure_plan.calls["get_all_records"] == 1
    assert snapshot.rows_read == 2
    assert snapshot.calls_by_sheet == {"transactions": 1}


def test_snapshot_does_not_survive_another_request(monkeypatch) -> None:
    sheet = InMemoryWorksheet("transactions", [["id"], ["one"]])
    monkeypatch.setattr(client, "get_sheet", lambda name: sheet)
    with client.sheets_request_snapshot():
        client.get_all_records("transactions")
    with client.sheets_request_snapshot():
        client.get_all_records("transactions")
    assert sheet.failure_plan.calls["get_all_records"] == 2


def test_mutation_invalidates_request_snapshot(monkeypatch) -> None:
    sheet = InMemoryWorksheet("transactions", [["id"], ["one"]])
    monkeypatch.setattr(client, "get_sheet", lambda name: sheet)
    with client.sheets_request_snapshot():
        assert len(client.get_all_records("transactions")) == 1
        client.append_row_raw("transactions", ["two"])
        assert len(client.get_all_records("transactions")) == 2
    assert sheet.failure_plan.calls["get_all_records"] == 2


def test_row_budget_fails_with_typed_error(monkeypatch) -> None:
    sheet = InMemoryWorksheet("transactions", [["id"], ["one"], ["two"]])
    monkeypatch.setattr(client, "get_sheet", lambda name: sheet)
    with client.sheets_request_snapshot(row_budget=1):
        with pytest.raises(client.SheetsReadBudgetExceeded):
            client.get_all_records("transactions")


def test_typed_finance_snapshot_loads_each_sheet_lazily_once() -> None:
    calls: list[str] = []
    snapshot = FinanceDataSnapshot(loader=lambda name: calls.append(name) or [{"sheet": name}])
    assert snapshot.records("transactions") == [{"sheet": "transactions"}]
    assert snapshot.records("transactions") == [{"sheet": "transactions"}]
    assert snapshot.records("accounts") == [{"sheet": "accounts"}]
    assert calls == ["transactions", "accounts"]
