"""Request budgets, image fallback classification, and context bounds."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.gemini_governance import (
    GeminiBudgetExceeded,
    GeminiInputTooLarge,
    gemini_request_scope,
)
from app.nlp import gemini_langchain_client as client
from app.nlp import gemini_finance_insight
from app.services import finance_insight_service


class _SuccessLlm:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, _messages):
        self.calls += 1
        return SimpleNamespace(content="ok", usage_metadata={})


def test_text_budget_allows_one_call_and_blocks_chaining(monkeypatch) -> None:
    llm = _SuccessLlm()
    monkeypatch.setattr(client, "get_gemini_llm", lambda *_args, **_kwargs: llm)
    with gemini_request_scope(max_primary_calls=1) as budget:
        assert client.generate_text_with_gemini("first", feature="transaction_parser") == "ok"
        with pytest.raises(GeminiBudgetExceeded):
            client.generate_text_with_gemini("second", feature="intent_router")
    assert llm.calls == 1
    assert budget.total_calls == 1


def test_image_compatibility_error_allows_exactly_one_fallback(monkeypatch) -> None:
    class CompatibilityLlm:
        def __init__(self) -> None:
            self.calls = 0

        def invoke(self, _messages):
            self.calls += 1
            if self.calls == 1:
                raise TypeError("image_url schema invocation format")
            return SimpleNamespace(content="image-ok", usage_metadata={})

    llm = CompatibilityLlm()
    monkeypatch.setattr(client, "get_gemini_llm", lambda *_args, **_kwargs: llm)
    with gemini_request_scope() as budget:
        result = client.generate_text_from_image_with_gemini("schema", b"image")
    assert result == "image-ok"
    assert llm.calls == 2
    assert budget.total_calls == 2


@pytest.mark.parametrize("error", [PermissionError("permission"), TimeoutError("timeout"), RuntimeError("quota 429"), RuntimeError("provider 500")])
def test_non_compatibility_image_errors_never_retry(monkeypatch, error: Exception) -> None:
    class FailedLlm:
        calls = 0

        def invoke(self, _messages):
            self.calls += 1
            raise error

    llm = FailedLlm()
    monkeypatch.setattr(client, "get_gemini_llm", lambda *_args, **_kwargs: llm)
    with gemini_request_scope():
        with pytest.raises(type(error)):
            client.generate_text_from_image_with_gemini("schema", b"image")
    assert llm.calls == 1


def test_oversized_input_is_rejected_before_provider_call(monkeypatch) -> None:
    llm = _SuccessLlm()
    monkeypatch.setattr(client, "GEMINI_MAX_INPUT_CHARS", 5)
    monkeypatch.setattr(client, "get_gemini_llm", lambda *_args, **_kwargs: llm)
    with pytest.raises(GeminiInputTooLarge):
        client.generate_text_with_gemini("123456", feature="finance_ask")
    assert llm.calls == 0


def test_gemini_event_has_version_and_counts_without_prompt(monkeypatch) -> None:
    events = []
    llm = _SuccessLlm()
    monkeypatch.setattr(client, "get_gemini_llm", lambda *_args, **_kwargs: llm)
    monkeypatch.setattr(client, "emit_event", lambda event, **fields: events.append({"event": event, **fields}))
    client.generate_text_with_gemini("private finance sentence", feature="finance_ask")
    completed = next(record for record in events if record.get("event") == "gemini_call_completed")
    assert completed["feature"] == "finance_ask"
    assert completed["prompt_version"] == "finance-ask-v1"
    assert completed["input_characters"] == len("private finance sentence")
    assert completed["usage_available"] is False
    assert "private finance sentence" not in repr(events)


def test_finance_context_metrics_are_bounded_and_exclude_finance_payload(monkeypatch) -> None:
    events = []
    context = {
        "context_metadata": {
            "records_considered": 1000,
            "records_selected": 40,
            "context_truncated": True,
            "aggregation_level": "monthly_aggregates_with_relevant_records",
        },
        "relevant_transactions": [{"description": "private merchant text"}],
    }
    monkeypatch.setattr(gemini_finance_insight, "GEMINI_API_KEY", "configured")
    monkeypatch.setattr(gemini_finance_insight, "emit_event", lambda event, **fields: events.append({"event": event, **fields}))
    monkeypatch.setattr(gemini_finance_insight, "generate_text_with_gemini", lambda *args, **kwargs: "bounded answer")

    assert gemini_finance_insight.generate_finance_insight("ask", context, "private question") == "bounded answer"
    assert events == [{
        "event": "gemini_context_prepared",
        "feature": "finance_ask",
        "prompt_version": "finance-ask-v1",
        "records_considered": 1000,
        "records_selected": 40,
        "context_truncated": True,
        "aggregation_level": "monthly_aggregates_with_relevant_records",
    }]
    assert "private merchant text" not in repr(events)
    assert "private question" not in repr(events)


def test_ask_context_applies_configured_record_cap(monkeypatch) -> None:
    captured = {}
    monkeypatch.setattr(finance_insight_service, "AI_CONTEXT_RECORD_LIMIT", 3)
    monkeypatch.setattr(
        finance_insight_service,
        "build_monthly_finance_context",
        lambda month: {"context_metadata": {"records_considered": 10, "context_truncated": True}},
    )
    monkeypatch.setattr(finance_insight_service, "parse_period_from_text", lambda question: {"month": "2026-07", "date_from": None, "date_to": None})
    monkeypatch.setattr(finance_insight_service, "has_explicit_period", lambda question: False)

    def fake_search(question, **kwargs):
        captured.update(kwargs)
        return [{"id": str(index)} for index in range(kwargs["limit"])]

    monkeypatch.setattr(finance_insight_service, "search_relevant_transactions", fake_search)
    monkeypatch.setattr(finance_insight_service, "extract_keywords", lambda question: [])
    result = finance_insight_service.build_ask_finance_context("synthetic question")
    assert captured["limit"] == 3
    assert result["context_metadata"]["records_selected"] == 3
    assert result["context_metadata"]["context_truncated"] is True
