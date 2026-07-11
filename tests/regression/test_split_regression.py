"""Split-bill parsing and decision regressions from the debug matrix."""

from __future__ import annotations

import pytest

from app.bot.handler_parts.transaction_flow import (
    apply_split_bill_decision_to_parsed,
    attach_split_bill_if_any,
    split_bill_needs_decision,
)
from app.nlp.regex_parser import parse_with_regex
from tests.regression.case_loader import assert_partial, case_id, load_cases


CASES = load_cases("split_cases.jsonl")


@pytest.mark.regression
@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_split_parser_case(case: dict) -> None:
    """Verify participants, account, allocation, and decision requirement."""

    parsed = parse_with_regex(case["input"])
    assert parsed is not None
    attach_split_bill_if_any(parsed, case["input"])
    assert_partial(case["expected"]["parsed"], parsed, case=case, field="parsed")
    assert split_bill_needs_decision(parsed)

    account = str(parsed.get("account") or "").casefold()
    people = [str(name).casefold() for name in parsed["split_bill"]["person_names"]]
    assert account not in people, (
        f"Case ID: {case['id']}\nRaw input: {case['input']}\n"
        f"Invariant: account must not become split participant\nActual participants: {people}"
    )


def test_split_paid_and_unpaid_amount_contract() -> None:
    """Protect the matrix cases for paid user share versus unpaid gross amount."""

    raw = "Beli Mie Goreng 40k dibagi 2 sama Budi via Dana"
    paid = parse_with_regex(raw)
    unpaid = parse_with_regex(raw)
    assert paid is not None and unpaid is not None
    attach_split_bill_if_any(paid, raw)
    attach_split_bill_if_any(unpaid, raw)

    apply_split_bill_decision_to_parsed(paid, "paid")
    apply_split_bill_decision_to_parsed(unpaid, "unpaid")

    assert paid["amount"] == 20_000
    assert paid["split_bill"]["status"] == "paid"
    assert unpaid["amount"] == 40_000
    assert unpaid["split_bill"]["status"] == "unpaid"
    assert unpaid["split_bill"]["total_receivable"] == 20_000
