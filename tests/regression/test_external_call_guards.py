"""Explicit checks for the offline external-service guard."""

from __future__ import annotations

import asyncio
import socket

import pytest

from app.nlp.parse_safety import assess_parse_safety
from app.nlp.regex_parser import parse_with_regex
from tests.conftest import _is_loopback_socket_address


@pytest.mark.external_guard
def test_asyncio_event_loop_can_start_with_offline_guard() -> None:
    """Windows may use loopback sockets internally to emulate socketpair."""

    async def local_only() -> str:
        await asyncio.sleep(0)
        return "closed-cleanly"

    assert asyncio.run(local_only()) == "closed-cleanly"


@pytest.mark.external_guard
@pytest.mark.parametrize(
    "address",
    [
        ("127.0.0.1", 1),
        ("127.42.0.9", 1),
        ("::1", 1, 0, 0),
        ("localhost", 1),
        ("LOCALHOST.", 1),
    ],
)
def test_only_explicit_loopback_addresses_are_classified_local(address) -> None:
    """IPv4, IPv6, and localhost forms required by OS internals are local."""

    assert _is_loopback_socket_address(address) is True


@pytest.mark.external_guard
def test_network_socket_is_blocked_by_default() -> None:
    """A surprise network connection must fail the default test run."""

    with pytest.raises(AssertionError, match="Unexpected external service call"):
        socket.create_connection(("203.0.113.1", 443))


@pytest.mark.external_guard
def test_real_gspread_authorization_is_blocked_by_default() -> None:
    """Tests cannot construct a production gspread client."""

    import gspread

    with pytest.raises(AssertionError, match="Unexpected external service call"):
        gspread.authorize(object())


@pytest.mark.external_guard
def test_localhost_http_still_hits_the_http_adapter_guard() -> None:
    """Loopback socket support must not permit arbitrary HTTP requests."""

    import httpx

    with pytest.raises(AssertionError, match="Unexpected external service call"):
        httpx.Client.request(object(), "GET", "http://localhost:8765/internal")


@pytest.mark.external_guard
def test_telegram_adapter_is_blocked_before_transport() -> None:
    """Telegram remains blocked independently of the loopback exception."""

    from telegram import Bot

    with pytest.raises(AssertionError, match="Unexpected external service call"):
        asyncio.run(Bot._post(object(), "sendMessage"))


@pytest.mark.external_guard
def test_gemini_adapter_is_blocked_before_transport() -> None:
    """Gemini client construction remains an explicit offline boundary."""

    import langchain_google_genai

    with pytest.raises(AssertionError, match="Unexpected external service call"):
        langchain_google_genai.ChatGoogleGenerativeAI(model="gemini-test")


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
