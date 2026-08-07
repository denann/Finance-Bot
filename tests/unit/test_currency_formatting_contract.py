"""Golden output for the canonical Rupiah formatter contract."""

from __future__ import annotations

import pytest

from app.formatting import format_rupiah
from app.services import debt_service, report_service


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "Rp0"),
        (1234, "Rp1.234"),
        (123456789, "Rp123.456.789"),
        (-1500, "Rp-1.500"),
        (None, "Rp0"),
    ],
)
def test_format_rupiah_golden(value: object, expected: str) -> None:
    assert format_rupiah(value) == expected


def test_format_rupiah_invalid_value_preserves_current_error_contract() -> None:
    with pytest.raises(ValueError):
        format_rupiah("not-money")


def test_consolidated_formatter_preserves_historical_decimal_modes() -> None:
    assert debt_service.format_rupiah(1.5) == "Rp1,5"
    assert report_service.format_rupiah(1.5) == "Rp1"
