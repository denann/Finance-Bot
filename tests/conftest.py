"""Pytest bootstrap that prevents optional external imports and network calls."""

from __future__ import annotations

import ipaddress
import socket
from typing import Any

import pytest

from tests.fakes.external_modules import install_external_stubs

install_external_stubs()


def _is_loopback_socket_address(address: Any) -> bool:
    """Return whether a socket address is an explicit local loopback target.

    Hostnames other than ``localhost`` are not resolved here. This keeps the
    offline guard from performing DNS while allowing Windows asyncio's local
    socketpair fallback and equivalent IPv4/IPv6 loopback addresses.
    """

    host = address[0] if isinstance(address, tuple) and address else address
    if isinstance(host, bytes):
        try:
            host = host.decode("ascii")
        except UnicodeDecodeError:
            return False
    if not isinstance(host, str):
        return False

    normalized = host.strip().lower().rstrip(".")
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def block_external_services(monkeypatch: pytest.MonkeyPatch):
    """Fail every test that unexpectedly reaches an external service boundary.

    The guard is active for the complete default suite. Tests may replace one
    boundary with an explicit fake after this fixture has been applied.
    """

    def blocked(*_args, **_kwargs):
        raise AssertionError("Unexpected external service call during offline pytest.")

    async def blocked_async(*_args, **_kwargs):
        raise AssertionError("Unexpected external service call during offline pytest.")

    original_create_connection = socket.create_connection
    original_socket_connect = socket.socket.connect

    def guarded_create_connection(address, *args, **kwargs):
        if not _is_loopback_socket_address(address):
            return blocked(address, *args, **kwargs)
        return original_create_connection(address, *args, **kwargs)

    def guarded_socket_connect(sock, address, *args, **kwargs):
        if not _is_loopback_socket_address(address):
            return blocked(sock, address, *args, **kwargs)
        return original_socket_connect(sock, address, *args, **kwargs)

    for name in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "GOOGLE_SHEET_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "ENABLE_LIVE_AI_EVAL",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)
    monkeypatch.setattr(socket.socket, "connect", guarded_socket_connect)

    try:
        import gspread

        monkeypatch.setattr(gspread, "authorize", blocked)
    except ImportError:
        pass

    try:
        import httpx

        monkeypatch.setattr(httpx.Client, "request", blocked)
        monkeypatch.setattr(httpx.AsyncClient, "request", blocked_async)
    except ImportError:
        pass

    try:
        import requests

        monkeypatch.setattr(requests.sessions.Session, "request", blocked)
    except ImportError:
        pass

    try:
        import langchain_google_genai
        import app.nlp.gemini_langchain_client as gemini_client

        monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", blocked)
        monkeypatch.setattr(gemini_client, "ChatGoogleGenerativeAI", blocked)
        gemini_client.get_gemini_llm.cache_clear()
    except ImportError:
        pass

    try:
        from telegram import Bot

        monkeypatch.setattr(Bot, "_post", blocked_async)
    except ImportError:
        pass

    yield
