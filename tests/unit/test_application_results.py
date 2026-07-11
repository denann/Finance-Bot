"""Typed application result contract tests."""

from __future__ import annotations

import pytest

from app.application.results import (
    ClarificationRequired,
    MutationCommitted,
    OperationFailed,
    PreviewReady,
    ReconciliationRequired,
    UseCaseResult,
    ValidationFailure,
    immutable_payload,
)


def test_result_contract_has_explicit_variants() -> None:
    assert isinstance(ValidationFailure(errors=("amount",)), UseCaseResult)
    assert isinstance(ClarificationRequired(reason="missing_account"), UseCaseResult)
    assert isinstance(PreviewReady(payload=immutable_payload({"amount": 10_000})), UseCaseResult)
    assert isinstance(MutationCommitted(), UseCaseResult)
    assert isinstance(OperationFailed(operation="save"), UseCaseResult)
    assert isinstance(ReconciliationRequired(operation="save"), OperationFailed)


def test_preview_payload_is_detached_and_read_only() -> None:
    source = {"parsed": {"amount": 10_000}, "items": [{"kind": "expense"}]}
    result = PreviewReady(payload=immutable_payload(source))
    source["parsed"]["amount"] = 20_000

    assert result.payload["parsed"]["amount"] == 10_000
    with pytest.raises(TypeError):
        result.payload["new"] = True  # type: ignore[index]
    with pytest.raises(TypeError):
        result.payload["parsed"]["amount"] = 30_000  # type: ignore[index]
    with pytest.raises(TypeError):
        result.payload["items"][0]["kind"] = "income"  # type: ignore[index]


def test_application_results_do_not_import_telegram_or_sheets() -> None:
    import app.application.results as results

    names = set(results.__dict__)
    assert "telegram" not in names
    assert "gspread" not in names
