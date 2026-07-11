"""Pytest bootstrap that prevents optional external imports and network calls."""

from __future__ import annotations

import socket

import pytest

from tests.fakes.external_modules import install_external_stubs

install_external_stubs()


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

    for name in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "GOOGLE_SHEET_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "ENABLE_LIVE_AI_EVAL",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)

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
        from telegram import Bot

        monkeypatch.setattr(Bot, "_post", blocked_async)
    except ImportError:
        pass

    yield
