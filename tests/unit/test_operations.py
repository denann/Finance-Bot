"""Operational readiness and scheduler ownership policy tests."""

from __future__ import annotations

import pytest

from app.operations import RuntimeStateStore, validate_instance_policy


def test_readiness_distinguishes_alive_from_dependency_ready() -> None:
    """Readiness remains false until every required startup component is ready."""

    state = RuntimeStateStore("webhook", scheduler_enabled=True)
    assert state.snapshot()["status"] == "not_ready"
    state.update(config_ready=True, telegram_ready=True, scheduler_ready=True, startup_complete=True)
    degraded = state.snapshot()
    assert degraded["status"] == "not_ready"
    assert degraded["components"]["sheets"] == "not_ready"
    assert state.update(sheets_ready=True)["status"] == "ready"


def test_disabled_scheduler_is_not_a_readiness_failure() -> None:
    """Explicit scheduler disablement remains visible without blocking readiness."""

    state = RuntimeStateStore("polling", scheduler_enabled=False)
    snapshot = state.update(
        config_ready=True,
        sheets_ready=True,
        telegram_ready=True,
        startup_complete=True,
    )
    assert snapshot["status"] == "ready"
    assert snapshot["components"]["scheduler"] == "disabled"


def test_scheduler_rejects_multi_instance_deployment() -> None:
    """Without distributed ownership, only one scheduler instance is allowed."""

    validate_instance_policy(1, True)
    validate_instance_policy(3, False)
    with pytest.raises(RuntimeError, match="satu instance"):
        validate_instance_policy(2, True)
