"""Date parser tests for absent, valid, and explicitly invalid input."""

from __future__ import annotations

from tests.fakes.external_modules import install_external_stubs

install_external_stubs()

from app.nlp.parse_safety import CLARIFICATION, assess_parse_safety
from app.nlp.regex_parser import detect_date_result, parse_with_regex


def test_explicit_invalid_dates_are_not_replaced_with_today() -> None:
    """Calendar-invalid or out-of-range dates must remain invalid."""

    for value in ["31/02/2026", "2026-02-29", "31/04/2026", "2026-13-01"]:
        result = detect_date_result(f"beli kopi 10k {value}")
        assert result.status == "invalid"
        assert result.value is None

        parsed = parse_with_regex(f"beli kopi 10k dari Cash {value}")
        assert parsed is not None
        assert parsed["date"] is None
        assessment = assess_parse_safety(f"beli kopi 10k dari Cash {value}", parsed)
        assert assessment["recommended_action"] == CLARIFICATION
        assert "invalid_explicit_date" in assessment["risk_flags"]


def test_valid_leap_date_and_non_padded_date_are_accepted() -> None:
    """Valid leap-year and non-padded explicit dates keep their exact day."""

    assert detect_date_result("beli kopi 10k 29/02/2024").value == "2024-02-29"
    assert detect_date_result("beli kopi 10k 1/7/2026").value == "2026-07-01"


def test_absent_date_keeps_today_default() -> None:
    """Inputs without a date retain the existing business-date default."""

    result = detect_date_result("beli kopi 10k")
    assert result.status == "absent"
    assert result.value is not None


def test_debt_parser_invalid_date_is_never_today() -> None:
    """Debt intent may route early, but its explicit invalid date stays empty."""

    from app.nlp.regex_parser import parse_debt_input

    parsed = parse_debt_input("bayar hutang Budi 100rb dari BCA 31/02/2026")
    assert parsed is not None
    assert parsed["date"] is None
