"""Canonical presentation formatting shared by bot and finance services."""

from __future__ import annotations


def format_rupiah(amount: object, *, preserve_decimals: bool = True) -> str:
    """Format a numeric or Indonesian-formatted value as Rupiah."""

    raw_amount = amount
    if isinstance(raw_amount, str):
        raw = raw_amount.strip().replace("Rp", "").replace("rp", "").replace(" ", "")
        if "," in raw and "." in raw:
            raw = raw.replace(".", "").replace(",", ".")
        elif "," in raw:
            raw = raw.replace(",", ".")
        value = float(raw or 0)
    else:
        value = float(raw_amount or 0)

    if not preserve_decimals:
        return f"Rp{int(value):,}".replace(",", ".")

    if abs(value - round(value)) < 1e-9:
        return f"Rp{int(round(value)):,}".replace(",", ".")

    sign = "-" if value < 0 else ""
    value = abs(value)
    integer_part = int(value)
    decimal_part = (f"{value:.2f}".split(".", 1)[1]).rstrip("0")
    return f"Rp{sign}{integer_part:,}".replace(",", ".") + f",{decimal_part}"
