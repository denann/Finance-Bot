"""Multi-step confirmation scenarios driven by JSONL fixtures."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.bot.pending_actions import (
    PendingActionError,
    bind_action_message,
    cancel_pending_action,
    consume_pending_action,
    create_pending_action,
)
from tests.regression.case_loader import case_id, load_cases


CASES = load_cases("scenario_cases.jsonl")
NOW = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)


@pytest.mark.regression
@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_confirmation_scenario(case: dict) -> None:
    """Execute create, bind, save, cancel, expiry, and stale-message steps."""

    user_data: dict = {}
    captured: dict[str, dict] = {}
    mutations: list[dict] = []

    for index, step in enumerate(case["steps"], 1):
        action = step["action"]
        capture = step.get("capture")
        try:
            if action == "preview":
                record = create_pending_action(
                    user_data,
                    owner_user_id=123,
                    flow_type=step.get("flow", "single"),
                    payload=step["payload"],
                    ttl_seconds=step.get("ttl_seconds", 900),
                    now=NOW,
                )
                if step.get("message_id"):
                    bind_action_message(user_data, record["action_id"], step["message_id"])
                if capture:
                    captured[capture] = record
            elif action == "save":
                target = captured[step["target"]]
                consumed = consume_pending_action(
                    user_data,
                    target["action_id"],
                    owner_user_id=123,
                    message_id=step.get("message_id"),
                    now=NOW + timedelta(seconds=step.get("after_seconds", 0)),
                )
                mutations.append(consumed["payload"])
            elif action == "cancel":
                target = captured[step["target"]]
                cancel_pending_action(
                    user_data,
                    target["action_id"],
                    owner_user_id=123,
                    message_id=step.get("message_id"),
                    now=NOW + timedelta(seconds=step.get("after_seconds", 0)),
                )
            else:
                raise AssertionError(f"Unsupported scenario action: {action}")
        except PendingActionError as error:
            if error.code != step.get("expect_error"):
                raise AssertionError(
                    f"Case ID: {case['id']}\nScenario step: {index}\n"
                    f"Expected error: {step.get('expect_error')}\nActual error: {error.code}"
                ) from error
        else:
            if step.get("expect_error"):
                raise AssertionError(
                    f"Case ID: {case['id']}\nScenario step: {index}\n"
                    f"Expected error: {step['expect_error']}\nActual error: <none>"
                )

    expected = case["expected"]
    assert len(mutations) == expected["mutation_count"]
    if expected.get("saved_subject"):
        assert mutations[0]["subject"] == expected["saved_subject"]
    if expected.get("saved_amount"):
        assert mutations[0]["amount"] == expected["saved_amount"]
