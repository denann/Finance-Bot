"""Explicit callback ownership contracts for dispatcher containment."""

from __future__ import annotations


LEGACY_CALLBACK_PREFIXES = (
    "acc:",
    "batch_acc:",
    "bulk_edit_category_choice:",
    "cancel",
    "cancel:a_",
    "category_type:",
    "clarify_parse:",
    "confirm:",
    "debt_acc:",
    "debt_batch_acc:",
    "debt_overpay:",
    "debt_settle_acc:",
    "debt_settle_overpay:",
    "edit_category_choice:",
    "editflow:",
    "meal_guard:",
    "meal_split:",
    "mixed_acc:",
    "pay_debt:",
    "recurring_paid:",
    "set_balance_similar:",
    "split:",
)

LEGACY_EXACT_CALLBACKS = frozenset(
    {
        "asset_add:skip",
        "receipt:all",
        "receipt:part",
        "recurring_add:skip",
    }
)


def is_legacy_callback_data(data: object) -> bool:
    """Return whether callback data belongs to the audited legacy inventory."""

    value = str(data or "")
    return value in LEGACY_EXACT_CALLBACKS or value.startswith(LEGACY_CALLBACK_PREFIXES)
