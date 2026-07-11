"""Strict operational environment parsing tests."""

from __future__ import annotations

import pytest

from app.config import _parse_bool_env, _parse_float_env, _parse_int_env


def test_boolean_environment_values_are_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Common explicit forms are accepted while ambiguous values are rejected."""

    monkeypatch.setenv("TEST_BOOLEAN", "yes")
    assert _parse_bool_env("TEST_BOOLEAN", False) is True
    monkeypatch.setenv("TEST_BOOLEAN", "off")
    assert _parse_bool_env("TEST_BOOLEAN", True) is False
    monkeypatch.setenv("TEST_BOOLEAN", "sometimes")
    with pytest.raises(ValueError, match="true/false"):
        _parse_bool_env("TEST_BOOLEAN", True)


def test_positive_float_environment_rejects_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeout and retry delay values must be finite positive numbers."""

    monkeypatch.setenv("TEST_FLOAT", "1.25")
    assert _parse_float_env("TEST_FLOAT", 2.0) == 1.25
    monkeypatch.setenv("TEST_FLOAT", "0")
    with pytest.raises(ValueError, match="lebih dari 0"):
        _parse_float_env("TEST_FLOAT", 2.0)


def test_integer_environment_reports_invalid_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid integer configuration fails during startup instead of drifting."""

    monkeypatch.setenv("TEST_INTEGER", "abc")
    with pytest.raises(ValueError, match="angka"):
        _parse_int_env("TEST_INTEGER", 1)
