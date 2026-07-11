"""High-value regression expansion from historical Telegram bugs and gap review."""

from __future__ import annotations

import json
import re
from datetime import datetime as RealDateTime
from datetime import timedelta, timezone
from pathlib import Path

import pytest

from app.bot.handler_parts.transaction_flow import (
    attach_split_bill_if_any,
    mixed_needs_account,
    mixed_split_bill_needs_decision,
    parse_mixed_item,
    split_bill_needs_decision,
    split_user_inputs,
)
from app.bot.pending_actions import PendingActionError, consume_pending_action, create_pending_action
from app.nlp import regex_parser
from app.nlp.parse_safety import assess_parse_safety
from tests.regression.case_loader import assert_partial, load_cases


CASES = load_cases("expansion_cases.jsonl")
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
NOW = RealDateTime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)


class FixedDateTime(RealDateTime):
    """Provide the reference date declared by each fixture."""

    current = RealDateTime(2026, 7, 10, 12, 0, 0)

    @classmethod
    def now(cls, tz=None):
        value = cls.current
        return value.replace(tzinfo=tz) if tz else value


def _case_params() -> list[pytest.ParameterSet]:
    """Mark unresolved target behavior as strict expected failures."""

    params = []
    for case in CASES:
        marks = [pytest.mark.regression]
        if case.get("status") == "known_gap":
            marks.append(
                pytest.mark.xfail(
                    strict=True,
                    reason=str(case.get("xfail_reason") or "Tracked regression gap"),
                )
            )
        params.append(pytest.param(case, id=case["id"], marks=marks))
    return params


def _normalize_input(value: str) -> str:
    """Normalize only case and whitespace for exact-input duplicate checks."""

    return re.sub(r"\s+", " ", value.strip()).casefold()


@pytest.mark.parametrize("case", _case_params())
def test_expansion_case(case: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """Dispatch each expansion case to the real parser, safety, split, or state helper."""

    reference_date = RealDateTime.fromisoformat(case.get("reference_date", "2026-07-10"))
    FixedDateTime.current = reference_date
    monkeypatch.setattr(regex_parser, "business_now", lambda: FixedDateTime.current)

    layer = case["layer"]
    expected = case["expected"]

    if layer == "transaction_parser":
        actual = regex_parser.parse_with_regex(case["input"])
        if expected.get("parser_returns_none"):
            assert actual is None, (
                f"Case ID: {case['id']}\nRaw input: {case['input']}\n"
                f"Expected parser result: None\nActual: {actual!r}"
            )
            return
        assert actual is not None
        assert_partial(expected["parsed"], actual, case=case, field="parsed")
        return

    if layer == "debt_parser":
        actual = regex_parser.parse_debt_input(case["input"])
        assert actual is not None, f"Case ID: {case['id']}\nDebt parser returned None"
        assert_partial(expected["parsed"], actual, case=case, field="parsed")
        return

    if layer == "date_parser":
        result = regex_parser.detect_date_result(case["input"])
        actual = {"status": result.status, "value": result.value, "raw": result.explicit_input}
        assert_partial(expected["parsed"], actual, case=case, field="parsed")
        return

    if layer in {"safety", "safety_after_split"}:
        parsed = regex_parser.parse_with_regex(case["input"])
        if layer == "safety_after_split" and parsed is not None:
            attach_split_bill_if_any(parsed, case["input"])
        actual = assess_parse_safety(case["input"], parsed)
        assert_partial(expected["safety"], actual, case=case, field="safety")
        return

    if layer in {"split", "split_with_safety"}:
        parsed = regex_parser.parse_with_regex(case["input"])
        assert parsed is not None
        attach_split_bill_if_any(parsed, case["input"])
        assert_partial(expected["parsed"], parsed, case=case, field="parsed")
        assert split_bill_needs_decision(parsed) is expected["split_decision"]
        if layer == "split_with_safety":
            safety = assess_parse_safety(case["input"], parsed)
            assert_partial(expected["safety"], safety, case=case, field="safety")
        return

    if layer == "multi":
        lines = split_user_inputs(case["input"])
        items = [parse_mixed_item(line) for line in lines]
        assert len(lines) == expected["line_count"]
        assert [item["kind"] for item in items] == expected["kinds"]
        assert mixed_needs_account(items) is expected["needs_account"]
        assert mixed_split_bill_needs_decision(items) is expected["split_decision"]
        for index, item_expected in enumerate(expected.get("items", [])):
            assert_partial(item_expected, items[index], case=case, field=f"items[{index}]")
        return

    if layer == "pending_action_scenario":
        user_data: dict = {}
        captured: dict[str, dict] = {}
        mutations: list[dict] = []

        for index, step in enumerate(case["steps"], 1):
            try:
                if step["action"] == "preview":
                    record = create_pending_action(
                        user_data,
                        owner_user_id=123,
                        flow_type=step.get("flow", "single"),
                        payload=step["payload"],
                        now=NOW,
                    )
                    captured[step["capture"]] = record
                elif step["action"] == "save":
                    target = captured[step["target"]]
                    consumed = consume_pending_action(
                        user_data,
                        target["action_id"],
                        owner_user_id=123,
                        message_id=step.get("message_id"),
                        now=NOW + timedelta(seconds=step.get("after_seconds", 0)),
                    )
                    mutations.append(consumed["payload"])
                else:
                    raise AssertionError(f"Unsupported scenario action: {step['action']}")
            except PendingActionError as error:
                assert error.code == step.get("expect_error"), (
                    f"Case ID: {case['id']}\nStep: {index}\n"
                    f"Expected error: {step.get('expect_error')}\nActual: {error.code}"
                )
            else:
                assert not step.get("expect_error"), (
                    f"Case ID: {case['id']}\nStep: {index}\n"
                    f"Expected error: {step.get('expect_error')}\nActual: <none>"
                )

        assert len(mutations) == expected["mutation_count"]
        assert_partial(expected["saved_payload"], mutations[0], case=case, field="saved_payload")
        return

    raise AssertionError(f"Unsupported expansion layer: {layer}")


def test_expansion_fixture_has_unique_ids_and_no_legacy_input_duplicates() -> None:
    """Keep every added input distinct from the pre-existing fixture corpus."""

    ids: set[str] = set()
    legacy_inputs: dict[str, tuple[str, str]] = {}

    for fixture in FIXTURE_ROOT.glob("*.jsonl"):
        if fixture.name == "expansion_cases.jsonl":
            continue
        for raw_line in fixture.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            item = json.loads(raw_line)
            raw_input = item.get("input")
            if raw_input:
                legacy_inputs[_normalize_input(raw_input)] = (fixture.name, item["id"])

    expansion_inputs: set[str] = set()
    for case in CASES:
        assert case["id"] not in ids, f"Duplicate expansion ID: {case['id']}"
        ids.add(case["id"])
        assert case.get("status") in {"active", "known_gap"}
        assert isinstance(case.get("tags"), list) and case["tags"]

        raw_input = case.get("input")
        if not raw_input:
            continue
        normalized = _normalize_input(raw_input)
        assert normalized not in expansion_inputs, f"Duplicate expansion input: {raw_input}"
        assert normalized not in legacy_inputs, (
            f"Expansion input duplicates {legacy_inputs[normalized]}: {raw_input}"
        )
        expansion_inputs.add(normalized)
