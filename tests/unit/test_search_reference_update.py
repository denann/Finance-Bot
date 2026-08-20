import sys
import types

sheets = types.ModuleType("app.sheets.client")
sheets.get_all_records = lambda *a, **k: []
_prior_sheets_client = sys.modules.get("app.sheets.client")
sys.modules["app.sheets.client"] = sheets

from app.services import report_service


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


def test_search_can_return_matches_after_number_ten_when_browser_requests_full_query(monkeypatch):
    records = [
        {
            "id": f"txn_{i:02d}", "date": f"2026-08-{i:02d}", "type": "expense", "amount": i,
            "description": f"kopi {i}", "category": "Food", "account": "Cash", "_row_index": i + 1,
        }
        for i in range(1, 16)
    ]
    monkeypatch.setattr(report_service, "get_transaction_records_for_report", lambda: records)
    monkeypatch.setattr(report_service, "enrich_transactions_with_debt_info", lambda rows: list(rows))

    legacy_default = report_service.search_transactions("kopi")
    browser_full = report_service.search_transactions("kopi", limit=None)

    assert len(legacy_default) == 10
    assert len(browser_full) == 15
    assert {x["id"] for x in browser_full} >= {"txn_11", "txn_15"}
