"""Fixture-driven parser regressions for transactions, transfers, and debt."""

from __future__ import annotations

from datetime import datetime as RealDateTime

import pytest

from app.nlp import regex_parser
from tests.regression.case_loader import assert_partial, case_id, load_cases


CASES = load_cases("parser_cases.jsonl")


class FixedDateTime(RealDateTime):
    """Return the fixture reference date for relative and absent-date parsing."""

    current = RealDateTime(2026, 7, 10, 12, 0, 0)

    @classmethod
    def now(cls, tz=None):
        value = cls.current
        return value.replace(tzinfo=tz) if tz else value


@pytest.mark.regression
@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_parser_case(case: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert only the parsed fields explicitly declared by each case."""

    reference_date = RealDateTime.fromisoformat(case.get("reference_date", "2026-07-10"))
    FixedDateTime.current = reference_date
    monkeypatch.setattr(regex_parser, "business_now", lambda: FixedDateTime.current)

    parser_name = case.get("parser", "transaction")
    if parser_name == "debt":
        actual = regex_parser.parse_debt_input(case["input"])
    elif parser_name == "date":
        result = regex_parser.detect_date_result(case["input"])
        actual = {
            "status": result.status,
            "value": result.value,
            "raw": result.explicit_input,
        }
    else:
        actual = regex_parser.parse_with_regex(case["input"])

    assert actual is not None, f"Case ID: {case['id']}\nRaw input: {case['input']}\nParser returned None"
    assert_partial(case["expected"]["parsed"], actual, case=case, field="parsed")


def test_parser_fixture_schema_contract() -> None:
    """Require stable IDs, traceability, reference dates, tags, and expectations."""

    ids: set[str] = set()
    for case in CASES:
        assert isinstance(case.get("id"), str) and case["id"]
        assert case["id"] not in ids
        ids.add(case["id"])
        assert case.get("source", {}).get("document") == "finance_bot_debug_input_matrix_v2.md"
        assert isinstance(case.get("source", {}).get("section"), str)
        assert isinstance(case.get("source", {}).get("case"), int)
        assert RealDateTime.fromisoformat(case["reference_date"])
        assert isinstance(case.get("tags"), list) and case["tags"]
        assert isinstance(case.get("expected", {}).get("parsed"), dict)


def test_fixture_failure_message_contains_case_and_field() -> None:
    """A fixture mismatch must expose the case ID, raw input, and field path."""

    from tests.regression.case_loader import assert_partial

    case = {
        "id": "diagnostic_case",
        "input": "beli kopi 20k",
        "expected": {"route": "transaction", "flow": "PREVIEW"},
    }
    with pytest.raises(AssertionError) as error:
        assert_partial({"amount": 20_000}, {"amount": 10_000}, case=case, field="parsed")
    message = str(error.value)
    assert "Case ID: diagnostic_case" in message
    assert "Raw input: beli kopi 20k" in message
    assert "Field or invariant: parsed.amount" in message
