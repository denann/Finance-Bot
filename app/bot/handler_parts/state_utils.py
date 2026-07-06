"""Small utilities for cleaning pending Telegram conversation state."""

from __future__ import annotations

from typing import Any

# Single edit category ambiguity state.
EDIT_CATEGORY_CHOICE_KEY = "pending_edit_category_choice"
# Bulk edit category ambiguity queue state.
BULK_EDIT_CATEGORY_DECISION_KEY = "pending_bulk_edit_category_decision"

# Only transient flow keys are listed here. Long-lived helper state such as
# `last_txn_map` must stay untouched because /last numbers are reused by
# /edit_txn and /delete_txn.
PENDING_FLOW_KEYS = (
    "pending_parsed",
    "pending_raw",
    "pending_batch",
    "pending_mixed",
    "pending_debt",
    "pending_debt_batch",
    "pending_payment",
    "pending_delete_refs",
    "pending_delete_txn_ids",
    "pending_edit_txn",
    EDIT_CATEGORY_CHOICE_KEY,
    BULK_EDIT_CATEGORY_DECISION_KEY,
    "pending_bulk_edit_txns",
    "pending_debt_void",
    "pending_debt_settle",
    "pending_asset_price",
    "pending_asset_confirm",
    "pending_asset_add_flow",
    "pending_expense_confirm",
    "pending_set_balance",
    "pending_set_balance_suggestion",
    "pending_preview_edit",
    "pending_missing_amount",
    "pending_parse_clarification",
    "pending_social_spending_guard",
    "pending_meal_split",
    "pending_receipt",
    "pending_receipt_context",
    "pending_receipt_part_selection",
    "pending_receipt_extra_divisor",
    "pending_budget_confirm",
    # Category add wizard state must clear on cancel or a new slash command.
    "pending_category_add_flow",
    # Category edit wizard state must clear separately from add flow.
    "pending_category_edit_flow",
    # Category inline prompt id is tracked so old keyboards can be cleaned.
    "pending_category_prompt_message_id",
    "pending_recurring_confirm",
    "pending_recurring_add_flow",
    "pending_asset_add_prompt_message_id",
    "pending_recurring_add_prompt_message_id",
    "pending_preview_edit_prompt_message_id",
    "mixed_review_preview_sent",
)

FLOW_LABELS = {
    "pending_parsed": "preview transaksi",
    "pending_batch": "preview batch transaksi",
    "pending_mixed": "preview mixed input",
    "pending_debt": "preview hutang/piutang",
    "pending_debt_batch": "preview batch hutang/piutang",
    "pending_payment": "preview pembayaran hutang/piutang",
    "pending_delete_refs": "preview hapus transaksi",
    "pending_delete_txn_ids": "preview hapus transaksi",
    "pending_edit_txn": "preview edit transaksi",
    EDIT_CATEGORY_CHOICE_KEY: "pilihan kategori edit transaksi",
    BULK_EDIT_CATEGORY_DECISION_KEY: "pilihan kategori bulk edit transaksi",
    "pending_bulk_edit_txns": "preview edit banyak transaksi",
    "pending_debt_void": "preview void hutang/piutang",
    "pending_debt_settle": "preview pelunasan hutang/piutang",
    "pending_asset_price": "input harga aset",
    "pending_asset_confirm": "preview aset",
    "pending_asset_add_flow": "wizard tambah aset",
    "pending_expense_confirm": "preview pending expense",
    "pending_set_balance": "preview set saldo",
    "pending_set_balance_suggestion": "klarifikasi rekening set saldo",
    "pending_preview_edit": "mode edit preview",
    "pending_missing_amount": "input nominal yang kurang",
    "pending_parse_clarification": "klarifikasi parse transaksi",
    "pending_social_spending_guard": "klarifikasi makan bareng/split bill",
    "pending_meal_split": "wizard split bill makan bareng",
    "pending_receipt": "review foto struk",
    "pending_receipt_context": "review foto struk",
    "pending_receipt_part_selection": "pemilihan item struk",
    "pending_receipt_extra_divisor": "pembagian biaya struk",
    # Human-readable label for unfinished add category wizard.
    "pending_category_add_flow": "wizard tambah kategori",
    # Human-readable label for unfinished edit category wizard.
    "pending_category_edit_flow": "wizard edit kategori",
    # Human-readable label for the category type keyboard prompt.
    "pending_category_prompt_message_id": "keyboard kategori",
    "pending_preview_edit_prompt_message_id": "keyboard edit preview",
    "pending_recurring_add_prompt_message_id": "keyboard wizard recurring_add",
    "pending_asset_add_prompt_message_id": "keyboard wizard tambah aset",
    "pending_recurring_add_flow": "wizard recurring_add",
    "pending_recurring_confirm": "preview recurring transaction",
    "pending_budget_confirm": "preview set budget",
}


def active_pending_flow_keys(context: Any) -> list[str]:
    """Return pending flow keys that currently exist in `context.user_data`."""
    user_data = getattr(context, "user_data", {}) or {}
    return [key for key in PENDING_FLOW_KEYS if key in user_data]


def has_active_pending_flow(context: Any) -> bool:
    """Check whether the user has an unfinished wizard, preview, or confirmation flow."""
    return bool(active_pending_flow_keys(context))


def describe_active_pending_flow(context: Any) -> str:
    """Build a short human-readable label for the current active flow."""
    keys = active_pending_flow_keys(context)
    if not keys:
        return ""

    labels = []
    seen = set()
    for key in keys:
        label = FLOW_LABELS.get(key, key)
        if label not in seen:
            labels.append(label)
            seen.add(label)

    if len(labels) == 1:
        return labels[0]
    if len(labels) <= 3:
        return ", ".join(labels)
    return ", ".join(labels[:3]) + f", dan {len(labels) - 3} state lain"


def clear_pending_flow_state(context: Any) -> list[str]:
    """Remove all transient pending flow state and return the removed keys."""
    removed = []
    user_data = getattr(context, "user_data", None)
    if user_data is None:
        return removed

    for key in PENDING_FLOW_KEYS:
        if key in user_data:
            user_data.pop(key, None)
            removed.append(key)
    return removed


def clear_pending_flow_state_before_command(context: Any, command_name: str | None = None) -> list[str]:
    """Clear stale wizard state before a new explicit slash command runs.

    Args:
        context: Telegram context whose user_data should be cleaned.
        command_name: Slash command name without the leading slash. The value is
            only informational for now, but the argument keeps the helper easy to
            extend if a future command needs to preserve state.

    Returns:
        List of removed context.user_data keys.
    """
    _ = command_name
    return clear_pending_flow_state(context)
