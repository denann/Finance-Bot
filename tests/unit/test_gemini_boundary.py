"""Bounded Gemini client configuration, output, and telemetry tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.nlp import gemini_langchain_client as client
from app.observability import metrics_snapshot, reset_metrics_for_tests


def test_client_receives_timeout_and_output_token_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every model instance must receive the configured provider bounds."""

    captured: dict = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    client.get_gemini_llm.cache_clear()
    monkeypatch.setattr(client, "ChatGoogleGenerativeAI", FakeClient)
    monkeypatch.setattr(client, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(client, "GEMINI_TIMEOUT_SECONDS", 12.5)
    monkeypatch.setattr(client, "GEMINI_MAX_OUTPUT_TOKENS", 777)
    client.get_gemini_llm("gemini-test", 0.2)

    assert captured["model"] == "gemini-test"
    assert captured["temperature"] == 0.2
    assert captured["timeout"] == 12.5
    assert captured["max_output_tokens"] == 777
    assert captured["google_api_key"] == "test-key"
    client.get_gemini_llm.cache_clear()


def test_text_output_is_hard_capped_and_usage_is_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Oversized provider output cannot pass the local boundary unchanged."""

    class FakeLlm:
        def invoke(self, _messages):
            return SimpleNamespace(
                content="x" * 100,
                usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            )

    reset_metrics_for_tests()
    monkeypatch.setattr(client, "GEMINI_MAX_OUTPUT_CHARS", 25)
    monkeypatch.setattr(client, "get_gemini_llm", lambda *_args, **_kwargs: FakeLlm())
    output = client.generate_text_with_gemini("synthetic prompt", model_name="gemini-test")

    assert output == "x" * 25
    snapshot = metrics_snapshot()
    assert snapshot["counters"]["gemini.calls"] == 1
    assert snapshot["counters"]["gemini.success"] == 1


def test_timeout_is_counted_and_propagated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeout failures remain visible to callers and operational metrics."""

    class TimeoutLlm:
        def invoke(self, _messages):
            raise TimeoutError("provider timeout")

    reset_metrics_for_tests()
    monkeypatch.setattr(client, "get_gemini_llm", lambda *_args, **_kwargs: TimeoutLlm())
    with pytest.raises(TimeoutError):
        client.generate_text_with_gemini("synthetic prompt", model_name="gemini-test")
    snapshot = metrics_snapshot()
    assert snapshot["counters"]["gemini.calls"] == 1
    assert snapshot["counters"]["gemini.errors"] == 1
