"""Fixture-driven tests for the real parse-safety decision boundary."""

from __future__ import annotations

import pytest

from app.nlp.parse_safety import assess_parse_safety
from app.nlp.regex_parser import parse_with_regex
from tests.regression.case_loader import assert_partial, case_id, load_cases


CASES = load_cases("safety_cases.jsonl")


@pytest.mark.regression
@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_parse_safety_case(case: dict) -> None:
    """Assert safe action, risk level, and declared risk flags."""

    parsed = parse_with_regex(case["input"])
    actual = assess_parse_safety(case["input"], parsed)
    assert_partial(case["expected"]["safety"], actual, case=case, field="safety")

    if case["expected"].get("write_prohibited"):
        assert actual["recommended_action"] in {"clarification", "gemini_draft_preview", "warning_preview"}
