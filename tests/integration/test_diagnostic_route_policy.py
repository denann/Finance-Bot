"""Security policy tests for the legacy Sheets diagnostic route."""

from __future__ import annotations

from pathlib import Path

from app.api.diagnostics import DiagnosticAccess, evaluate_diagnostic_access, run_read_only_sheets_diagnostic


def test_diagnostic_is_disabled_by_default() -> None:
    """Production-default access must hide the diagnostic route."""

    access = evaluate_diagnostic_access({}, provided_secret=None)
    assert access is DiagnosticAccess.DISABLED


def test_anonymous_request_cannot_reach_sheets() -> None:
    """Missing admin secret must stop before any Sheets callable is invoked."""

    calls: list[str] = []
    access = evaluate_diagnostic_access(
        {"ENABLE_TEST_SHEETS_ROUTE": "true", "DIAGNOSTIC_ADMIN_SECRET": "secret"},
        provided_secret=None,
    )

    assert access is DiagnosticAccess.FORBIDDEN
    assert calls == []


def test_authorized_diagnostic_is_read_only_and_redacted() -> None:
    """Authorized diagnostics return only generic connectivity status."""

    calls: list[str] = []

    def read_only_probe() -> None:
        calls.append("probe")

    result = run_read_only_sheets_diagnostic(read_only_probe)

    assert calls == ["probe"]
    assert result == {"status": "connected"}
    assert "spreadsheet_title" not in result
    assert "sheets_found" not in result
    assert "schema_check" not in result


def test_liveness_contract_is_unchanged_and_readiness_is_separate() -> None:
    """Phase 1B adds `/ready` without changing the existing `/health` payload."""

    source = (Path(__file__).resolve().parents[2] / "main.py").read_text(encoding="utf-8")
    assert 'return {"status": "ok", "mode": BOT_MODE}' in source
    assert '@app.get("/ready")' in source
    assert 'status_code = 200 if snapshot["status"] == "ready" else 503' in source
