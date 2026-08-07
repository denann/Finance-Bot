"""Regression tests for one-call Gemini parsing of unresolved bulk inputs."""

from __future__ import annotations

import asyncio

from app.application.external_io import ExternalIOTimeout
from app.bot.handler_parts import transaction_flow


def test_bulk_local_success_uses_zero_gemini_calls(monkeypatch) -> None:
    monkeypatch.setattr(
        transaction_flow,
        "parse_mixed_item_local",
        lambda line: {"kind": "transaction", "parsed": {"description": line}, "raw": line},
    )
    calls = []

    async def fake_run_gemini(*args, **kwargs):
        calls.append((args, kwargs))
        return {}

    monkeypatch.setattr(transaction_flow, "run_gemini", fake_run_gemini)

    result = asyncio.run(transaction_flow.parse_mixed_items_batch(["one", "two"]))

    assert [item["parsed"]["description"] for item in result] == ["one", "two"]
    assert calls == []


def test_multiple_unresolved_items_use_one_batch_call_and_keep_order(monkeypatch) -> None:
    monkeypatch.setattr(
        transaction_flow,
        "parse_mixed_item_local",
        lambda line: {"kind": "failed", "parsed": {}, "raw": line},
    )
    calls = []

    async def fake_run_gemini(operation, function, unresolved_inputs):
        calls.append((operation, function, list(unresolved_inputs)))
        return {
            1: {"type": "income", "amount": 20_000, "date": "2026-07-11", "description": "second"},
            0: {"type": "expense", "amount": 10_000, "date": "2026-07-11", "description": "first"},
        }

    monkeypatch.setattr(transaction_flow, "run_gemini", fake_run_gemini)
    monkeypatch.setattr(transaction_flow, "attach_split_bill_if_any", lambda parsed, raw: None)

    result = asyncio.run(transaction_flow.parse_mixed_items_batch(["raw first", "raw second"]))

    assert len(calls) == 1
    assert calls[0][0] == "transaction_batch_parser"
    assert calls[0][2] == ["raw first", "raw second"]
    assert [item["parsed"]["description"] for item in result] == ["first", "second"]
    assert [item["raw"] for item in result] == ["raw first", "raw second"]


def test_batch_output_only_replaces_matching_unresolved_positions(monkeypatch) -> None:
    def local(line):
        if line == "local":
            return {"kind": "transaction", "parsed": {"description": "local"}, "raw": line}
        return {"kind": "failed", "parsed": {}, "raw": line}

    monkeypatch.setattr(transaction_flow, "parse_mixed_item_local", local)

    async def fake_run_gemini(_operation, _function, unresolved_inputs):
        assert unresolved_inputs == ["unknown-a", "unknown-b"]
        return {1: {"type": "expense", "amount": 1, "date": "2026-07-11", "description": "resolved-b"}}

    monkeypatch.setattr(transaction_flow, "run_gemini", fake_run_gemini)
    monkeypatch.setattr(transaction_flow, "attach_split_bill_if_any", lambda parsed, raw: None)

    result = asyncio.run(transaction_flow.parse_mixed_items_batch(["unknown-a", "local", "unknown-b"]))

    assert [item["kind"] for item in result] == ["failed", "transaction", "transaction"]
    assert result[1]["parsed"]["description"] == "local"
    assert result[2]["parsed"]["description"] == "resolved-b"


def test_batch_worker_timeout_falls_back_to_item_clarification(monkeypatch) -> None:
    monkeypatch.setattr(
        transaction_flow,
        "parse_mixed_item_local",
        lambda line: {"kind": "failed", "parsed": {}, "raw": line},
    )

    async def fake_run_gemini(*_args, **_kwargs):
        raise ExternalIOTimeout("timeout")

    monkeypatch.setattr(transaction_flow, "run_gemini", fake_run_gemini)

    result = asyncio.run(transaction_flow.parse_mixed_items_batch(["unknown-a", "unknown-b"]))

    assert [item["kind"] for item in result] == ["failed", "failed"]
