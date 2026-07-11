"""Preview readiness and immutable confirmation schema regressions."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.bot.pending_actions import create_pending_action
from app.nlp.regex_parser import parse_with_regex
from tests.regression.case_loader import case_id, load_cases


CASES = load_cases("preview_cases.jsonl")
NOW = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)


def _needs_account(parsed: dict) -> bool:
    """Mirror the public account requirement without importing handler state."""

    if parsed.get("type") in {"expense", "income"}:
        return not bool(parsed.get("account"))
    if parsed.get("type") == "transfer":
        return not bool(parsed.get("account") and parsed.get("to_account"))
    return False


@pytest.mark.regression
@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_preview_readiness_case(case: dict) -> None:
    """Prevent final save availability while required account data is missing."""

    parsed = parse_with_regex(case["input"])
    assert parsed is not None
    actual_flow = "PREVIEW_EDIT_CONTINUE_CANCEL" if _needs_account(parsed) else "PREVIEW_SAVE_EDIT_CANCEL"
    assert actual_flow == case["expected"]["flow"], (
        f"Case ID: {case['id']}\nRaw input: {case['input']}\nField: flow\n"
        f"Expected: {case['expected']['flow']}\nActual: {actual_flow}"
    )


def test_final_preview_action_has_strict_lifecycle_schema() -> None:
    """Keep dynamic IDs out of fixture comparisons while enforcing their types."""

    action = create_pending_action(
        {}, owner_user_id=123, flow_type="single",
        payload={"user_state": {"pending_parsed": {"amount": 20_000}}}, now=NOW,
    )
    required = {
        "action_id": str,
        "owner_user_id": int,
        "flow_type": str,
        "payload": dict,
        "created_at": str,
        "expires_at": str,
        "status": str,
    }
    for field, field_type in required.items():
        assert field in action
        assert isinstance(action[field], field_type)
    assert action["action_id"].startswith("a_")
    assert action["status"] == "pending"
