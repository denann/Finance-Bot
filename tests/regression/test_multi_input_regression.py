"""Multi-input ordering, item-kind, and continuation regressions."""

from __future__ import annotations

import pytest

from app.bot.handler_parts.transaction_flow import (
    mixed_needs_account,
    mixed_split_bill_needs_decision,
    parse_mixed_item,
    split_user_inputs,
)
from tests.regression.case_loader import case_id, load_cases


CASES = load_cases("multi_cases.jsonl")


@pytest.mark.regression
@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_multi_input_case(case: dict) -> None:
    """Keep item order while exposing per-item clarification requirements."""

    lines = split_user_inputs(case["input"])
    items = [parse_mixed_item(line) for line in lines]
    expected = case["expected"]
    assert len(lines) == expected["line_count"]
    assert [item["raw"] for item in items] == lines
    assert [item["kind"] for item in items] == expected["kinds"]
    assert mixed_needs_account(items) is expected["needs_account"]
    assert mixed_split_bill_needs_decision(items) is expected["split_decision"]


def test_multi_input_helpers_do_not_mutate_storage() -> None:
    """Parsing and decision detection must remain read-only before confirmation."""

    mutations: list[dict] = []
    lines = split_user_inputs("beli kopi 10k dari Cash; beli nasi 20k dari DANA")
    items = [parse_mixed_item(line) for line in lines]
    assert len(items) == 2
    assert mutations == []
