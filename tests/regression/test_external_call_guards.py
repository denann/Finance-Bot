"""Explicit checks for the offline external-service guard."""

from __future__ import annotations

import socket

import pytest

from app.nlp.parse_safety import assess_parse_safety
from app.nlp.regex_parser import parse_with_regex


@pytest.mark.external_guard
def test_network_socket_is_blocked_by_default() -> None:
    """A surprise network connection must fail the default test run."""

    with pytest.raises(AssertionError, match="Unexpected external service call"):
        socket.create_connection(("example.com", 443))


@pytest.mark.external_guard
def test_real_gspread_authorization_is_blocked_by_default() -> None:
    """Tests cannot construct a production gspread client."""

    import gspread

    with pytest.raises(AssertionError, match="Unexpected external service call"):
        gspread.authorize(object())


@pytest.mark.external_guard
def test_deterministic_parser_and_safety_need_no_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    """A clear transaction remains entirely inside deterministic boundaries."""

    import app.nlp.gemini_parser as gemini_parser

    monkeypatch.setattr(
        gemini_parser,
        "parse_with_gemini",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Gemini called")),
    )
    parsed = parse_with_regex("beli kopi 20k dari Cash")
    assessment = assess_parse_safety("beli kopi 20k dari Cash", parsed)
    assert assessment["recommended_action"] == "normal_preview"
