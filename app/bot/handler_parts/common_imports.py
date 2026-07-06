"""Shared imports and helper utilities used across Telegram handler modules."""


# Import re for this module's local operations.
import re
# Import ast for this module's local operations.
import ast
# Import operator for this module's local operations.
import operator
# Import io for this module's local operations.
import io
# Import datetime so this module can use its helpers.
from datetime import datetime
# Import difflib so this module can use its helpers.
from difflib import SequenceMatcher
# Import telegram so this module can use its helpers.
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
# Import telegram.ext so this module can use its helpers.
from telegram.ext import ContextTypes
# Import telegram.helpers so this module can use its helpers.
from telegram.helpers import escape_markdown
# Import telegram.error so this module can use its helpers.
from telegram.error import BadRequest
# Import shlex for this module's local operations.
import shlex
# Import os for this module's local operations.
import os
# Import app.config so this module can use its helpers.
from app.config import (
    # Include this value in the surrounding collection or call.
    ALLOWED_USER_ID,
    # Include this value in the surrounding collection or call.
    SHEET_CATEGORIES,
    # Include this value in the surrounding collection or call.
    GEMINI_API_KEY,
    # Include this value in the surrounding collection or call.
    SHEET_TRANSACTIONS,
    # Include this value in the surrounding collection or call.
    SHEET_ACCOUNTS,
    # Include this value in the surrounding collection or call.
    SHEET_BUDGETS,
    # Include this value in the surrounding collection or call.
    SHEET_PENDING_EXPENSES,
    # Include this value in the surrounding collection or call.
    SHEET_DEBTS,
    # Include this value in the surrounding collection or call.
    SHEET_DEBT_PAYMENTS,
    # Include this value in the surrounding collection or call.
    WEBHOOK_URL,
    # Include this value in the surrounding collection or call.
    APP_PORT,
# Close the structure that was opened above.
)

# Import app.services.net_worth_service so this module can use its helpers.
from app.services.net_worth_service import (
    # Include this value in the surrounding collection or call.
    add_asset,
    # Include this value in the surrounding collection or call.
    get_assets,
    # Include this value in the surrounding collection or call.
    update_asset,
    # Include this value in the surrounding collection or call.
    deactivate_asset,
    # Include this value in the surrounding collection or call.
    calculate_net_worth,
    # Include this value in the surrounding collection or call.
    create_net_worth_snapshot,
    # Include this value in the surrounding collection or call.
    get_net_worth_snapshots,
    # Include this value in the surrounding collection or call.
    calculate_asset_gain,
# Close the structure that was opened above.
)

# Import app.bot.keyboards so this module can use its helpers.
from app.bot.keyboards import (
    # Include this value in the surrounding collection or call.
    account_keyboard,
    # Include this value in the surrounding collection or call.
    confirm_keyboard,
    # Include this value in the surrounding collection or call.
    cancel_keyboard,
    # Include this value in the surrounding collection or call.
    receipt_ownership_keyboard,
    # Include this value in the surrounding collection or call.
    SKIP_ACCOUNT_CALLBACK_VALUE,
    # Include this value in the surrounding collection or call.
    SKIP_ACCOUNT_NAME,
# Close the structure that was opened above.
)
# Import app.nlp.regex_parser so this module can use its helpers.
from app.nlp.regex_parser import parse_with_regex, parse_debt_input, detect_date, strip_date_phrases
# Import app.nlp.normalizer so this module can use its helpers.
from app.nlp.normalizer import extract_amount_from_text
# Import app.nlp.gemini_parser so this module can use its helpers.
from app.nlp.gemini_parser import parse_with_pending_fallback
# Import app.nlp.gemini_image_parser so this module can use its helpers.
from app.nlp.gemini_image_parser import parse_transactions_from_image
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import get_all_records, get_spreadsheet, rollback_current_sheets_transaction
# Import app.services.transaction_service so this module can use its helpers.
from app.services.transaction_service import (
    # Include this value in the surrounding collection or call.
    save_transaction,
    # Include this value in the surrounding collection or call.
    save_transactions_batch,
    # Include this value in the surrounding collection or call.
    get_all_accounts,
    # Include this value in the surrounding collection or call.
    get_account_balance,
    # Include this value in the surrounding collection or call.
    update_account_balance,
    # Include this value in the surrounding collection or call.
    get_recent_transactions,
    # Include this value in the surrounding collection or call.
    preview_delete_transactions_by_refs,
    # Include this value in the surrounding collection or call.
    delete_transactions_by_refs,
    # Include this value in the surrounding collection or call.
    preview_edit_transaction_by_ref,
    # Include this value in the surrounding collection or call.
    edit_transaction_by_ref,
    # Include this value in the surrounding collection or call.
    get_transactions_for_export,
    # Include this value in the surrounding collection or call.
    calculate_account_deltas,
    # Include this value in the surrounding collection or call.
    update_transaction_debt_relation,
    # Include this value in the surrounding collection or call.
    clear_transaction_debt_relation,
    # Include this value in the surrounding collection or call.
    EXPORT_TRANSACTION_COLUMNS,
# Close the structure that was opened above.
)

# Import app.nlp.gemini_intent_router so this module can use its helpers.
from app.nlp.gemini_intent_router import (
    # Include this value in the surrounding collection or call.
    should_try_gemini_intent_router,
    # Include this value in the surrounding collection or call.
    route_intent_with_gemini,
# Close the structure that was opened above.
)

# Import app.services.budget_service so this module can use its helpers.
from app.services.budget_service import (
    # Include this value in the surrounding collection or call.
    set_budget,
    # Include this value in the surrounding collection or call.
    get_budget_summary,
    # Include this value in the surrounding collection or call.
    check_budget_after_transaction,
    # Include this value in the surrounding collection or call.
    normalize_month,
    # Include this value in the surrounding collection or call.
    format_month_label,
    # Include this value in the surrounding collection or call.
    get_budget_months,
# Close the structure that was opened above.
)
# Import app.services.report_service so this module can use its helpers.
from app.services.report_service import (
    # Include this value in the surrounding collection or call.
    get_daily_report,
    # Include this value in the surrounding collection or call.
    get_weekly_report,
    # Include this value in the surrounding collection or call.
    get_monthly_report,
    # Include this value in the surrounding collection or call.
    get_account_report,
    # Include this value in the surrounding collection or call.
    search_transactions,
    # Include this value in the surrounding collection or call.
    parse_report_month_arg,
    # Include this value in the surrounding collection or call.
    parse_report_date_arg,
    # Include this value in the surrounding collection or call.
    split_report_period_and_category_arg,
    # Include this value in the surrounding collection or call.
    split_report_filter_args,
    # Include this value in the surrounding collection or call.
    split_account_period_arg,
    # Include this value in the surrounding collection or call.
    enrich_transactions_with_debt_info,
# Close the structure that was opened above.
)

# Import app.services.finance_insight_service so this module can use its helpers.
from app.services.finance_insight_service import (
    # Include this value in the surrounding collection or call.
    build_monthly_finance_context,
    # Include this value in the surrounding collection or call.
    build_ask_finance_context,
    # Include this value in the surrounding collection or call.
    build_audit_context,
    # Include this value in the surrounding collection or call.
    build_coach_context,
    # Include this value in the surrounding collection or call.
    normalize_month_arg as normalize_insight_month,
    # Include this value in the surrounding collection or call.
    should_handle_finance_question,
    # Include this value in the surrounding collection or call.
    route_finance_question_mode,
# Close the structure that was opened above.
)
# Import app.nlp.gemini_finance_insight so this module can use its helpers.
from app.nlp.gemini_finance_insight import generate_finance_insight

# Import app.services.debt_service so this module can use its helpers.
from app.services.debt_service import (
    # Include this value in the surrounding collection or call.
    add_debt,
    # Include this value in the surrounding collection or call.
    add_payment,
    # Include this value in the surrounding collection or call.
    add_payment_by_person,
    # Include this value in the surrounding collection or call.
    estimate_payment_outcome,
    # Include this value in the surrounding collection or call.
    summarize_debt_rows_for_settlement,
    # Include this value in the surrounding collection or call.
    settle_selected_debt_ids,
    # Include this value in the surrounding collection or call.
    format_debt_net_position_lines,
    # Include this value in the surrounding collection or call.
    parse_sheet_number,
    # Include this value in the surrounding collection or call.
    offset_debt_by_person,
    # Include this value in the surrounding collection or call.
    settle_opposite_debts_by_person,
    # Include this value in the surrounding collection or call.
    get_debt_summary,
    # Include this value in the surrounding collection or call.
    get_debt_person_summary,
    # Include this value in the surrounding collection or call.
    get_debt_person_detail,
    # Include this value in the surrounding collection or call.
    get_debt_by_person,
    # Include this value in the surrounding collection or call.
    get_debt_by_id_any_status,
    # Include this value in the surrounding collection or call.
    normalize_person_name,
    # Include this value in the surrounding collection or call.
    is_voided_debt,
    # Include this value in the surrounding collection or call.
    preview_void_debt,
    # Include this value in the surrounding collection or call.
    preview_void_debts_by_person,
    # Include this value in the surrounding collection or call.
    void_debt,
    # Include this value in the surrounding collection or call.
    void_debt_ids,
    # Include this value in the surrounding collection or call.
    void_debts_by_person,
    # Include this value in the surrounding collection or call.
    void_debts_for_transaction,
    # Include this value in the surrounding collection or call.
    update_debt,
# Close the structure that was opened above.
)
# Import csv for this module's local operations.
import csv
# Import tempfile for this module's local operations.
import tempfile
# Import app.services.recurring_service so this module can use its helpers.
from app.services.recurring_service import (
    # Include this value in the surrounding collection or call.
    add_recurring_rule,
    # Include this value in the surrounding collection or call.
    get_recurring_rules,
    # Include this value in the surrounding collection or call.
    disable_recurring_rule,
    # Include this value in the surrounding collection or call.
    process_due_recurring_rules,
    # Include this value in the surrounding collection or call.
    mark_recurring_rule_paid,
    # Include this value in the surrounding collection or call.
    edit_recurring_rule,
# Close the structure that was opened above.
)
# Import app.services.pending_expense_service so this module can use its helpers.
from app.services.pending_expense_service import (
    # Include this value in the surrounding collection or call.
    add_pending_expense_from_text,
    # Include this value in the surrounding collection or call.
    build_pending_expense_from_text,
    # Include this value in the surrounding collection or call.
    save_pending_expense,
    # Include this value in the surrounding collection or call.
    get_pending_expenses,
    # Include this value in the surrounding collection or call.
    mark_pending_paid,
    # Include this value in the surrounding collection or call.
    cancel_pending_expense,
    # Include this value in the surrounding collection or call.
    is_pending_expense_text,
# Close the structure that was opened above.
)

# ── Cross-part shared helpers ────────────────────────────────────────────────
# Implementation note for this project-specific finance flow.
# Keep normal imports working without relying on global variables from handlers.py.

# Prepare TELEGRAM SAFE MESSAGE LIMIT for the next step.
TELEGRAM_SAFE_MESSAGE_LIMIT = 3800
# Prepare GEMINI INTENT CONFIDENCE EXECUTE for the next step.
GEMINI_INTENT_CONFIDENCE_EXECUTE = 0.80
# Prepare GEMINI INTENT CONFIDENCE CLARIFY for the next step.
GEMINI_INTENT_CONFIDENCE_CLARIFY = 0.60


# Define format rupiah for callers in this flow.
def format_rupiah(amount: float) -> str:
    """Format data into a readable display for rupiah."""
    # Prepare raw amount for the next step.
    raw_amount = amount
    # Handle the case where isinstance(raw_amount, str).
    if isinstance(raw_amount, str):
        raw = raw_amount.strip().replace("Rp", "").replace("rp", "").replace(" ", "")
        if "," in raw and "." in raw:
            raw = raw.replace(".", "").replace(",", ".")
        elif "," in raw:
            raw = raw.replace(",", ".")
        # Prepare value for the next step.
        value = float(raw or 0)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare value for the next step.
        value = float(raw_amount or 0)
    # Handle the case where abs(value - round(value)) < 1e-9.
    if abs(value - round(value)) < 1e-9:
        return f"Rp{int(round(value)):,}".replace(",", ".")

    sign = "-" if value < 0 else ""
    # Prepare value for the next step.
    value = abs(value)
    # Prepare integer part for the next step.
    integer_part = int(value)
    decimal_part = (f"{value:.2f}".split(".", 1)[1]).rstrip("0")
    return f"Rp{sign}{integer_part:,}".replace(",", ".") + f",{decimal_part}"


# Define short debt id for callers in this flow.
def short_debt_id(debt_id: str) -> str:
    """Coordinate the short debt id logic in the Telegram handler layer.

    Args:
        debt_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    debt_id = str(debt_id or "")
    # Handle the case where len(debt_id) <= 18.
    if len(debt_id) <= 18:
        # Return debt_id to the caller.
        return debt_id
    return debt_id[:18] + "..."


# Define md safe for callers in this flow.
def md_safe(value) -> str:
    """Coordinate the md safe logic in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    return escape_markdown(str(value or "-"), version=1)


# Define md code text for callers in this flow.
def md_code_text(value) -> str:
    """Coordinate the md code text logic in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    return str(value or "-").replace("`", "'")


# Define short txn id for callers in this flow.
def short_txn_id(txn_id: str) -> str:
    """Coordinate the short txn id logic in the Telegram handler layer.

    Args:
        txn_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    txn_id = str(txn_id or "")
    # Handle the case where len(txn_id) <= 18.
    if len(txn_id) <= 18:
        # Return txn_id to the caller.
        return txn_id
    return txn_id[:18] + "..."





# Define normalize sheet date for display for callers in this flow.
def normalize_sheet_date_for_display(value) -> str:
    """Normalize Google Sheets date values before showing them to users.

    Google Sheets can return dates as serial numbers when old rows were written
    with USER_ENTERED. This keeps `/hutang`, reports, and audit output readable
    without changing stored historical data.
    """
    # Handle the case where value is None.
    if value is None:
        return ""

    # Prepare raw for the next step.
    raw = str(value).strip()
    if not raw or raw.lower() in {"-", "none", "nan"}:
        return ""

    match = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", raw)
    # Handle the case where match.
    if match:
        # Run this operation in a guarded block so failures can be handled.
        try:
            return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
        # Handle an expected failure from the guarded operation above.
        except Exception:
            return match.group(0).replace("/", "-")

    if re.fullmatch(r"\d+(?:\.0+)?", raw):
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare serial for the next step.
            serial = int(float(raw))
            # Handle the case where 20000 <= serial <= 80000.
            if 20000 <= serial <= 80000:
                # Import datetime so this module can use its helpers.
                from datetime import timedelta
                # Prepare dt for the next step.
                dt = datetime(1899, 12, 30) + timedelta(days=serial)
                return dt.strftime("%Y-%m-%d")
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass

    # Return raw to the caller.
    return raw

# Define format indonesian date group label for callers in this flow.
def format_indonesian_date_group_label(date_value) -> str:
    """Format data into a readable display for indonesian date group label."""
    # Prepare raw for the next step.
    raw = normalize_sheet_date_for_display(date_value)
    if not raw or raw.lower() in {"-", "none", "nan", "tanpa tanggal"}:
        return "🗓️ Tanpa tanggal:"

    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", raw)
    # Handle the case where match.
    if match:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare dt for the next step.
            dt = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            weekdays = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            # Open a multi-line structure for the values below.
            months = [
                "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                "Juli", "Agustus", "September", "Oktober", "November", "Desember",
            # Close the structure that was opened above.
            ]
            return f"🗓️ {weekdays[dt.weekday()]}, {dt.day} {months[dt.month - 1]} {dt.year}:"
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass

    return f"🗓️ {raw}:"


# Define safe float for display for callers in this flow.
def _safe_float_for_display(value, default: float = 0.0) -> float:
    """Coordinate the safe float for display logic in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.
        default: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Handle the case where isinstance(value, str).
        if isinstance(value, str):
            raw = value.strip().replace("Rp", "").replace("rp", "").replace(" ", "")
            if "." in raw and "," in raw:
                raw = raw.replace(".", "").replace(",", ".")
            elif "," in raw:
                raw = raw.replace(",", ".")
            elif "." in raw:
                parts = raw.split(".")
                # Handle the case where len(parts) > 1 and all(len(part) == 3 for part in parts[1:]).
                if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
                    raw = raw.replace(".", "")
            raw = re.sub(r"[^0-9.-]", "", raw)
            # Return float(raw or 0) to the caller.
            return float(raw or 0)
        # Return float(value or 0) to the caller.
        return float(value or 0)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return default to the caller.
        return default


# Define get transaction receivable parts for callers in this flow.
def get_transaction_receivable_parts(txn: dict) -> list[dict]:
    """Retrieve data needed by the get transaction receivable parts workflow in the Telegram handler layer.

    Args:
        txn: Transaction dict or transaction-like row from the finance data layer.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    parts = (txn or {}).get("debt_receivable_parts") or []
    # Handle the case where parts.
    if parts:
        # Return [ to the caller.
        return [
            # Open a multi-line structure for the values below.
            {
                "person_name": str((part or {}).get("person_name") or "Tanpa nama").strip(),
                "remaining_amount": _safe_float_for_display((part or {}).get("remaining_amount", 0)),
            # Close the structure that was opened above.
            }
            # Process each part in the current collection.
            for part in parts
            if _safe_float_for_display((part or {}).get("remaining_amount", 0)) > 0
        # Close the structure that was opened above.
        ]

    # Debt flow section
    receivable_by_person = {}
    for debt in (txn or {}).get("linked_debts") or []:
        debt_type = str((debt or {}).get("type", "") or "").strip().lower()
        if debt_type != "receivable":
            # Skip the rest of this loop iteration after handling this case.
            continue
        person = str((debt or {}).get("person_name") or "Tanpa nama").strip()
        amount = _safe_float_for_display((debt or {}).get("remaining_amount", 0))
        # Handle the case where amount > 0.
        if amount > 0:
            # Run this statement as part of the current workflow.
            receivable_by_person[person] = receivable_by_person.get(person, 0.0) + amount

    # Handle the case where receivable_by_person.
    if receivable_by_person:
        # Return [ to the caller.
        return [
            {"person_name": person, "remaining_amount": amount}
            # Process each person, amount in the current collection.
            for person, amount in receivable_by_person.items()
        # Close the structure that was opened above.
        ]

    receivable = _safe_float_for_display((txn or {}).get("debt_receivable_remaining", 0))
    people = [str(x).strip() for x in ((txn or {}).get("debt_people") or []) if str(x).strip()]
    # Handle the case where receivable > 0 and people.
    if receivable > 0 and people:
        # Handle the case where len(people) == 1.
        if len(people) == 1:
            return [{"person_name": people[0], "remaining_amount": receivable}]
        # Prepare share for the next step.
        share = receivable / len(people)
        return [{"person_name": person, "remaining_amount": share} for person in people]
    # Handle the case where receivable > 0.
    if receivable > 0:
        return [{"person_name": "Tanpa nama", "remaining_amount": receivable}]
    # Return [] to the caller.
    return []


# Define get transaction payable parts for callers in this flow.
def get_transaction_payable_parts(txn: dict) -> list[dict]:
    """Retrieve data needed by the get transaction payable parts workflow in the Telegram handler layer.

    Args:
        txn: Transaction dict or transaction-like row from the finance data layer.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    parts = (txn or {}).get("debt_payable_parts") or []
    # Handle the case where parts.
    if parts:
        # Return [ to the caller.
        return [
            # Open a multi-line structure for the values below.
            {
                "person_name": str((part or {}).get("person_name") or "Tanpa nama").strip(),
                "remaining_amount": _safe_float_for_display((part or {}).get("remaining_amount", 0)),
            # Close the structure that was opened above.
            }
            # Process each part in the current collection.
            for part in parts
            if _safe_float_for_display((part or {}).get("remaining_amount", 0)) > 0
        # Close the structure that was opened above.
        ]

    # Prepare payable by person for the next step.
    payable_by_person = {}
    for debt in (txn or {}).get("linked_debts") or []:
        debt_type = str((debt or {}).get("type", "") or "").strip().lower()
        if debt_type != "payable":
            # Skip the rest of this loop iteration after handling this case.
            continue
        person = str((debt or {}).get("person_name") or "Tanpa nama").strip()
        amount = _safe_float_for_display((debt or {}).get("remaining_amount", 0))
        # Handle the case where amount > 0.
        if amount > 0:
            # Run this statement as part of the current workflow.
            payable_by_person[person] = payable_by_person.get(person, 0.0) + amount

    # Return [ to the caller.
    return [
        {"person_name": person, "remaining_amount": amount}
        # Process each person, amount in the current collection.
        for person, amount in payable_by_person.items()
    # Close the structure that was opened above.
    ]


# Define get net expense after receivable for callers in this flow.
def get_net_expense_after_receivable(txn: dict) -> float:
    """Retrieve data needed by the get net expense after receivable workflow in the Telegram handler layer.

    Args:
        txn: Transaction dict or transaction-like row from the finance data layer.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    amount = _safe_float_for_display((txn or {}).get("amount", 0))
    # Open a multi-line structure for the values below.
    receivable = _safe_float_for_display(
        (txn or {}).get("debt_receivable_original", (txn or {}).get("debt_receivable_remaining", 0))
    # Close the structure that was opened above.
    )
    # Return max(amount - receivable, 0.0) to the caller.
    return max(amount - receivable, 0.0)


# Define build debt parts text for callers in this flow.
def build_debt_parts_text(parts: list[dict]) -> str:
    """Build the data structure or message text for debt parts text."""
    # Prepare chunks for the next step.
    chunks = []
    # Process each part in the current collection.
    for part in parts or []:
        person = md_safe((part or {}).get("person_name") or "Tanpa nama")
        amount = _safe_float_for_display((part or {}).get("remaining_amount", 0))
        # Handle the case where amount <= 0.
        if amount <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        chunks.append(f"{format_rupiah(amount)} ({person})")
    return ", ".join(chunks)


# Define has expense transactions for callers in this flow.
def has_expense_transactions(transactions: list[dict] | None) -> bool:
    """Evaluate the has expense transactions condition in the Telegram handler layer.

    Args:
        transactions: List of transaction dicts or transaction-like rows.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Return any( to the caller.
    return any(
        str((txn or {}).get("type", "") or "").strip().lower() == "expense"
        # Process each txn in the current collection.
        for txn in (transactions or [])
    # Close the structure that was opened above.
    )


# Define has net gross difference for callers in this flow.
def has_net_gross_difference(transactions: list[dict] | None) -> bool:
    """Evaluate the has net gross difference condition in the Telegram handler layer.

    Args:
        transactions: List of transaction dicts or transaction-like rows.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Process each txn in the current collection.
    for txn in transactions or []:
        txn_type = str((txn or {}).get("type", "") or "").strip().lower()
        if txn_type != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue
        gross = _safe_float_for_display((txn or {}).get("amount", 0))
        # Prepare net for the next step.
        net = get_net_expense_after_receivable(txn)
        # Handle the case where abs(gross - net) > 0.0001.
        if abs(gross - net) > 0.0001:
            # Return True to the caller.
            return True
    # Return False to the caller.
    return False


# Define append net gross note for callers in this flow.
def append_net_gross_note(lines: list[str], transactions: list[dict] | None = None, *, force: bool = False):
    """Apply the append net gross note operation in the Telegram handler layer.

    Args:
        lines: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        transactions: List of transaction dicts or transaction-like rows.
        force: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    # Handle the missing or empty force and not has_expense_transactions(transactions) case.
    if not force and not has_expense_transactions(transactions):
        # Return control to the caller.
        return
    lines.append("ℹ️ Catatan: nominal pengeluaran ditampilkan sebagai *Net (Gross)* jika ada piutang split bill terkait.\n")


# Define format expense net gross for callers in this flow.
def format_expense_net_gross(net_amount: float, gross_amount: float, *, always_show_gross: bool = False) -> str:
    """Format data into a readable display for expense net gross."""
    # Prepare net for the next step.
    net = _safe_float_for_display(net_amount)
    # Prepare gross for the next step.
    gross = _safe_float_for_display(gross_amount)
    # Handle the case where always_show_gross or abs(net - gross) > 0.0001.
    if always_show_gross or abs(net - gross) > 0.0001:
        return f"{format_rupiah(net)} ({format_rupiah(gross)})"
    # Return format_rupiah(gross) to the caller.
    return format_rupiah(gross)


# Define get transaction account text for callers in this flow.
def get_transaction_account_text(txn: dict) -> str:
    """Retrieve data needed by the get transaction account text workflow in the Telegram handler layer.

    Args:
        txn: Transaction dict or transaction-like row from the finance data layer.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    txn_type = str((txn or {}).get("type", "") or "").strip().lower()
    source_account = str((txn or {}).get("account", "") or "").strip()
    target_account = str((txn or {}).get("to_account", "") or "").strip()
    if txn_type == "transfer" and target_account:
        return f"{source_account or '-'} → {target_account}"
    return source_account or "-"


# Define build transaction display lines for callers in this flow.
def build_transaction_display_lines(
    # Include this value in the surrounding collection or call.
    txn: dict,
    # Include this value in the surrounding collection or call.
    *,
    # Include this value in the surrounding collection or call.
    index: int | None = None,
    # Include this value in the surrounding collection or call.
    include_date: bool = True,
    # Include this value in the surrounding collection or call.
    include_id: bool = False,
    # Include this value in the surrounding collection or call.
    contribution_pct: float | None = None,
    # Include this value in the surrounding collection or call.
    note: str | None = None,
# Close the structure that was opened above.
) -> list[str]:
    """Build the data structure or message text for transaction display lines."""
    # Prepare txn for the next step.
    txn = txn or {}
    txn_type = str(txn.get("type", "") or "").strip().lower()
    amount = _safe_float_for_display(txn.get("amount", 0))
    # Open a multi-line structure for the values below.
    icon = {
        "expense": "❌",
        "income": "✅",
        "transfer": "🔄",
    }.get(txn_type, "❓")

    prefix = f"{index}. " if index is not None else ""
    description = md_safe(txn.get("description") or txn.get("subject") or "-")
    date = str(txn.get("date", "") or "").strip()
    category = md_safe(txn.get("category") or "-")
    # Prepare account text for the next step.
    account_text = md_safe(get_transaction_account_text(txn))

    lines = [f"{prefix}{icon} *{description}*"]
    # Prepare meta for the next step.
    meta = []
    # Handle the case where include_date and date.
    if include_date and date:
        meta.append(f"📅 {md_safe(date)}")

    if txn_type == "expense":
        # Prepare net expense for the next step.
        net_expense = get_net_expense_after_receivable(txn)
        meta.append(f"💰 *{format_expense_net_gross(net_expense, amount)}*")
    elif txn_type == "income":
        meta.append(f"💰 *{format_rupiah(amount)}*")
    elif txn_type == "transfer":
        meta.append(f"🔁 *{format_rupiah(amount)}*")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        meta.append(f"💰 *{format_rupiah(amount)}*")

    # Update meta with the current value.
    meta.append(category)
    meta.append(f"🏦 {account_text}")
    lines.append(f"   {' | '.join(meta)}")

    # Prepare receivable parts for the next step.
    receivable_parts = get_transaction_receivable_parts(txn)
    # Prepare receivable text for the next step.
    receivable_text = build_debt_parts_text(receivable_parts)
    if txn_type == "expense" and receivable_text:
        lines.append(f"   ↳ 🤝 Piutang aktif: {receivable_text}")

    # Prepare payable parts for the next step.
    payable_parts = get_transaction_payable_parts(txn)
    # Prepare payable text for the next step.
    payable_text = build_debt_parts_text(payable_parts)
    # Handle the case where payable_text.
    if payable_text:
        lines.append(f"   ↳ 🔴 Utang terkait aktif: {payable_text}")

    # Handle the case where contribution_pct is not None.
    if contribution_pct is not None:
        lines.append(f"   ↳ 📊 {contribution_pct:.1f}% dari pengeluaran")

    # Handle the case where note.
    if note:
        lines.append(f"   📝 {md_safe(note)}")

    # Handle the case where include_id.
    if include_id:
        txn_id = str(txn.get("id", "") or "").strip()
        # Handle the case where txn_id.
        if txn_id:
            lines.append(f"   🔖 `{md_code_text(txn_id)}`")

    # Return lines to the caller.
    return lines


# Define build transactions full text shared for callers in this flow.
def build_transactions_full_text_shared(
    # Include this value in the surrounding collection or call.
    transactions: list[dict],
    # Include this value in the surrounding collection or call.
    title: str,
    # Include this value in the surrounding collection or call.
    account_filter: str | None = None,
    # Include this value in the surrounding collection or call.
    *,
    # Include this value in the surrounding collection or call.
    current_balance: float | None = None,
# Close the structure that was opened above.
) -> str:
    """Build full transaction history text with net/gross expense summaries.

    Args:
        transactions: Transaction rows to render. Rows may be raw or already
            enriched with linked debt metadata.
        title: Markdown title shown at the top of the message.
        account_filter: Optional account name. When provided, summary totals
            are calculated from that account's inflow, outflow, and transfers.
        current_balance: Optional current account balance shown only in account
            detail views.

    Returns:
        Markdown text grouped by transaction date. Expense and net values use
        net-after-receivable as the primary amount and show gross in
        parentheses when different.
    """
    # Prepare transactions for the next step.
    transactions = enrich_transactions_with_debt_info(transactions or [])
    lines = [f"🧾 *{md_safe(title)}*\n"]
    # Run this statement as part of the current workflow.
    append_net_gross_note(lines, transactions)

    # Prepare total income for the next step.
    total_income = 0.0
    # Prepare total expense for the next step.
    total_expense = 0.0
    # Prepare total net expense for the next step.
    total_net_expense = 0.0
    # Prepare total transfer for the next step.
    total_transfer = 0.0
    # Prepare total transfer in for the next step.
    total_transfer_in = 0.0
    # Prepare total transfer out for the next step.
    total_transfer_out = 0.0
    account_key = str(account_filter or "").strip().lower()

    # Prepare current date group for the next step.
    current_date_group = None
    # Process each i, txn in the current collection.
    for i, txn in enumerate(transactions, 1):
        txn_type = str(txn.get("type", "") or "").strip().lower()
        amount = _safe_float_for_display(txn.get("amount", 0))
        source_account = str(txn.get("account", "") or "").strip()
        target_account = str(txn.get("to_account", "") or "").strip()
        # Prepare source match for the next step.
        source_match = bool(account_key and source_account.lower() == account_key)
        # Prepare target match for the next step.
        target_match = bool(account_key and target_account.lower() == account_key)

        # Handle the case where account_key.
        if account_key:
            if txn_type == "income" and source_match:
                # Run this statement as part of the current workflow.
                total_income += amount
            elif txn_type == "expense" and source_match:
                # Run this statement as part of the current workflow.
                total_expense += amount
                # Run this statement as part of the current workflow.
                total_net_expense += get_net_expense_after_receivable(txn)
            elif txn_type == "transfer":
                # Handle the case where source_match.
                if source_match:
                    # Run this statement as part of the current workflow.
                    total_transfer_out += amount
                # Handle the case where target_match.
                if target_match:
                    # Run this statement as part of the current workflow.
                    total_transfer_in += amount
                # Handle the case where source_match or target_match.
                if source_match or target_match:
                    # Run this statement as part of the current workflow.
                    total_transfer += amount
        # Handle the fallback path after earlier conditions are skipped.
        else:
            if txn_type == "income":
                # Run this statement as part of the current workflow.
                total_income += amount
            elif txn_type == "expense":
                # Run this statement as part of the current workflow.
                total_expense += amount
                # Run this statement as part of the current workflow.
                total_net_expense += get_net_expense_after_receivable(txn)
            elif txn_type == "transfer":
                # Run this statement as part of the current workflow.
                total_transfer += amount

        date_group = str(txn.get("date", "") or "Tanpa tanggal").strip() or "Tanpa tanggal"
        # Handle the case where date_group != current_date_group.
        if date_group != current_date_group:
            lines.append(f"\n*{md_safe(format_indonesian_date_group_label(date_group))}*")
            # Prepare current date group for the next step.
            current_date_group = date_group

        # Update lines with the current value.
        lines.extend(build_transaction_display_lines(txn, index=i, include_date=False, include_id=True))

    # Handle the case where account_key.
    if account_key:
        # Prepare net gross for the next step.
        net_gross = total_income + total_transfer_in - total_expense - total_transfer_out
        # Prepare net after receivable for the next step.
        net_after_receivable = total_income + total_transfer_in - total_net_expense - total_transfer_out
        # Prepare expense text for the next step.
        expense_text = format_expense_net_gross(total_net_expense, total_expense)
        # Prepare net text for the next step.
        net_text = format_expense_net_gross(net_after_receivable, net_gross)
        # Open a multi-line structure for the values below.
        summary_lines = [
            "\n*Ringkasan Rekening:*",
        # Close the structure that was opened above.
        ]
        # Handle the case where current_balance is not None.
        if current_balance is not None:
            summary_lines.append(f"💰 Saldo Saat Ini : *{format_rupiah(current_balance)}*")
        # Open a multi-line structure for the values below.
        summary_lines.extend([
            f"✅ Income          : *{format_rupiah(total_income)}*",
            f"❌ Expense         : *{expense_text}*",
            f"🔁 Transfer Masuk  : *{format_rupiah(total_transfer_in)}*",
            f"🔁 Transfer Keluar : *{format_rupiah(total_transfer_out)}*",
            f"📊 Net Rekening    : *{net_text}*",
            f"📝 Total           : *{len(transactions)} transaksi*",
        # Close the structure that was opened above.
        ])
        lines.append("\n".join(summary_lines))
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare net gross for the next step.
        net_gross = total_income - total_expense
        # Prepare net after receivable for the next step.
        net_after_receivable = total_income - total_net_expense
        # Prepare expense text for the next step.
        expense_text = format_expense_net_gross(total_net_expense, total_expense)
        # Prepare net text for the next step.
        net_text = format_expense_net_gross(net_after_receivable, net_gross)
        # Open a multi-line structure for the values below.
        lines.append(
            "\n*Ringkasan:*\n"
            f"✅ Income   : *{format_rupiah(total_income)}*\n"
            f"❌ Expense  : *{expense_text}*\n"
            f"🔄 Transfer : *{format_rupiah(total_transfer)}*\n"
            f"📊 Net      : *{net_text}*\n"
            f"📝 Total    : *{len(transactions)} transaksi*"
        # Close the structure that was opened above.
        )

    # Open a multi-line structure for the values below.
    lines.append(
        "\nNomor di atas bisa dipakai untuk koreksi setelah command ini:\n"
        "`/delete_txn 1` atau `/edit_txn 1 amount=15000`"
    # Close the structure that was opened above.
    )

    return "\n".join(lines)


# Define is authorized for callers in this flow.
def is_authorized(update: Update) -> bool:
    """Check whether a condition is true for authorized."""
    # Handle the missing or empty update.effective_user case.
    if not update.effective_user:
        # Return False to the caller.
        return False
    # Return update.effective_user.id == ALLOWED_USER_ID to the caller.
    return update.effective_user.id == ALLOWED_USER_ID


# Handle the asynchronous reject unauthorized workflow.
async def reject_unauthorized(update: Update):
    """Handle the asynchronous reject unauthorized flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    user_id = update.effective_user.id if update.effective_user else "unknown"
    # Open a multi-line structure for the values below.
    message = (
        "⛔ Anda tidak punya akses ke bot ini.\n\n"
        f"User ID Anda: `{user_id}`\n\n"
        "Bot ini hanya bisa digunakan oleh user yang sudah diizinkan."
    # Close the structure that was opened above.
    )

    # Handle the case where update.message.
    if update.message:
        await update.message.reply_text(message, parse_mode="Markdown")
        # Return control to the caller.
        return

    # Handle the case where update.callback_query.
    if update.callback_query:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Wait for update.callback_query.answer before continuing this flow.
            await update.callback_query.answer(
                "⛔ Anda tidak punya akses.",
                # Prepare show alert for the next step.
                show_alert=True,
            # Close the structure that was opened above.
            )
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass
        # Return control to the caller.
        return


# Define split long message for callers in this flow.
def split_long_message(text: str, max_len: int = TELEGRAM_SAFE_MESSAGE_LIMIT) -> list[str]:
    """Coordinate the split long message logic in the Telegram handler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        max_len: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    text = str(text or "").strip()
    # Handle the missing or empty text case.
    if not text:
        return [""]
    # Handle the case where len(text) <= max_len.
    if len(text) <= max_len:
        # Return [text] to the caller.
        return [text]

    # Prepare chunks for the next step.
    chunks = []
    current = ""

    for block in text.split("\n\n"):
        # Prepare block for the next step.
        block = block.strip()
        # Handle the missing or empty block case.
        if not block:
            # Skip the rest of this loop iteration after handling this case.
            continue

        candidate = f"{current}\n\n{block}".strip() if current else block
        # Handle the case where len(candidate) <= max_len.
        if len(candidate) <= max_len:
            # Prepare current for the next step.
            current = candidate
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Handle the case where current.
        if current:
            # Update chunks with the current value.
            chunks.append(current)
            current = ""

        # Handle the case where len(block) <= max_len.
        if len(block) <= max_len:
            # Prepare current for the next step.
            current = block
            # Skip the rest of this loop iteration after handling this case.
            continue

        line_current = ""
        # Process each line in the current collection.
        for line in block.splitlines():
            candidate_line = f"{line_current}\n{line}".strip() if line_current else line
            # Handle the case where len(candidate_line) <= max_len.
            if len(candidate_line) <= max_len:
                # Prepare line current for the next step.
                line_current = candidate_line
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Handle the case where line_current.
                if line_current:
                    # Update chunks with the current value.
                    chunks.append(line_current)
                # Handle the case where len(line) > max_len.
                if len(line) > max_len:
                    # Process each i in the current collection.
                    for i in range(0, len(line), max_len):
                        # Update chunks with the current value.
                        chunks.append(line[i:i + max_len])
                    line_current = ""
                # Handle the fallback path after earlier conditions are skipped.
                else:
                    # Prepare line current for the next step.
                    line_current = line

        # Handle the case where line_current.
        if line_current:
            # Update chunks with the current value.
            chunks.append(line_current)

    # Handle the case where current.
    if current:
        # Update chunks with the current value.
        chunks.append(current)

    # Return chunks to the caller.
    return chunks


# Handle the asynchronous reply long markdown workflow.
async def reply_long_markdown(update: Update, text: str):
    """Handle the asynchronous reply long markdown flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Process each part in the current collection.
    for part in split_long_message(text):
        # Run this operation in a guarded block so failures can be handled.
        try:
            await update.message.reply_text(part, parse_mode="Markdown")
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(part)


# Handle the asynchronous reply message safely workflow.
async def reply_message_safely(message, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    """Handle the asynchronous reply message safely flow in the Telegram handler layer.

    Args:
        message: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        text: Raw text input to parse, normalize, validate, or display.
        parse_mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        reply_markup: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        **kwargs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    text = str(text or "").strip() or " "
    # Prepare chunks for the next step.
    chunks = split_long_message(text)
    # Process each idx, chunk in the current collection.
    for idx, chunk in enumerate(chunks):
        # Prepare markup for the next step.
        markup = reply_markup if idx == len(chunks) - 1 else None
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Wait for message.reply_text before continuing this flow.
            await message.reply_text(chunk, parse_mode=parse_mode, reply_markup=markup, **kwargs)
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Wait for message.reply_text before continuing this flow.
            await message.reply_text(chunk, reply_markup=markup, **kwargs)


# Handle the asynchronous reply update safely workflow.
async def reply_update_safely(update: Update, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    """Handle the asynchronous reply update safely flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        text: Raw text input to parse, normalize, validate, or display.
        parse_mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        reply_markup: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        **kwargs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the case where update.message.
    if update.message:
        # Wait for reply_message_safely before continuing this flow.
        await reply_message_safely(update.message, text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)


# Handle the asynchronous edit message safely workflow.
async def edit_message_safely(message, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    """Edit a Telegram message and split long follow-up text when needed.

    Args:
        message: Telegram message object to edit first.
        text: Text that should be shown to the user.
        parse_mode: Optional Telegram parse mode.
        reply_markup: Optional inline keyboard. For long text, the keyboard is
            attached to the last chunk so the user sees it after reading the
            details.

    Notes:
        Telegram has a hard message length limit. Receipt OCR output can become
        long, so this helper edits the status message with the first chunk and
        sends the remaining chunks as normal replies.
    """
    text = str(text or "").strip() or " "
    # Prepare chunks for the next step.
    chunks = split_long_message(text)

    # Handle the asynchronous edit workflow.
    async def _edit(payload: str, mode: str | None, markup):
        """Edit the target Telegram message with one prepared text chunk.

        Args:
            payload: Message text chunk that fits Telegram length limits.
            mode: Optional parse mode for this edit attempt.
            markup: Optional inline keyboard attached to this chunk.

        Returns:
            Telegram API result from `message.edit_text`.
        """
        # Return await message.edit_text( to the caller.
        return await message.edit_text(
            # Include this value in the surrounding collection or call.
            payload,
            # Prepare parse mode for the next step.
            parse_mode=mode,
            # Prepare reply markup for the next step.
            reply_markup=markup,
            # Include this value in the surrounding collection or call.
            **kwargs,
        # Close the structure that was opened above.
        )

    # Prepare first markup for the next step.
    first_markup = reply_markup if len(chunks) == 1 else None
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Wait for _edit before continuing this flow.
        await _edit(chunks[0], parse_mode, first_markup)
    # Handle an expected failure from the guarded operation above.
    except BadRequest:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Wait for _edit before continuing this flow.
            await _edit(chunks[0], None, first_markup)
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Wait for message.reply_text before continuing this flow.
            await message.reply_text(chunks[0], reply_markup=first_markup)

    # Process each idx, chunk in the current collection.
    for idx, chunk in enumerate(chunks[1:], start=1):
        # Prepare markup for the next step.
        markup = reply_markup if idx == len(chunks) - 1 else None
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Wait for message.reply_text before continuing this flow.
            await message.reply_text(chunk, parse_mode=parse_mode, reply_markup=markup)
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Wait for message.reply_text before continuing this flow.
            await message.reply_text(chunk, reply_markup=markup)


# Handle the asynchronous safe edit message workflow.
async def safe_edit_message(query, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    """Handle the asynchronous safe edit message flow in the Telegram handler layer.

    Args:
        query: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        text: Raw text input to parse, normalize, validate, or display.
        parse_mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        reply_markup: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        **kwargs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    text = str(text or "").strip() or " "
    # Prepare chunks for the next step.
    chunks = split_long_message(text)
    # Prepare first for the next step.
    first = chunks[0]

    # Handle the case where len(chunks) > 1.
    if len(chunks) > 1:
        suffix = "\n\n📄 *Pesan terlalu panjang, detail lanjutan dikirim di bawah.*"
        # Prepare max first len for the next step.
        max_first_len = TELEGRAM_SAFE_MESSAGE_LIMIT - len(suffix) - 10
        # Prepare first for the next step.
        first = first[:max_first_len].rstrip() + suffix

    # Handle the asynchronous edit workflow.
    async def _edit(payload: str, mode: str | None, markup):
        """Handle the asynchronous edit flow in the Telegram handler layer.

        Args:
            payload: Input value supplied by the caller; accepted shape follows the function signature and local validation.
            mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.
            markup: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

        Side effects:
            May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

        Flow constraints:
            Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
        """
        # Return await query.message.edit_text( to the caller.
        return await query.message.edit_text(
            # Include this value in the surrounding collection or call.
            payload,
            # Prepare parse mode for the next step.
            parse_mode=mode,
            # Prepare reply markup for the next step.
            reply_markup=markup,
            # Include this value in the surrounding collection or call.
            **kwargs,
        # Close the structure that was opened above.
        )

    # Prepare first markup for the next step.
    first_markup = reply_markup if len(chunks) == 1 else None

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Wait for _edit before continuing this flow.
        await _edit(first, parse_mode, first_markup)
    # Handle an expected failure from the guarded operation above.
    except BadRequest as exc:
        # Prepare err for the next step.
        err = str(exc).lower()
        if "message is not modified" in err:
            # Keep this intentionally empty block valid.
            pass
        elif "message_too_long" in err or "message is too long" in err or len(first) > 4096:
            safe_first = first[:3500].rstrip() + "\n\n📄 Pesan terlalu panjang, detail lanjutan dikirim di bawah."
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Wait for _edit before continuing this flow.
                await _edit(safe_first, None, first_markup)
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Wait for query.message.reply_text before continuing this flow.
                await query.message.reply_text(safe_first, reply_markup=first_markup)
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Wait for _edit before continuing this flow.
                await _edit(first, None, first_markup)
            # Handle an expected failure from the guarded operation above.
            except BadRequest:
                # Wait for query.message.reply_text before continuing this flow.
                await query.message.reply_text(first, reply_markup=first_markup)

    # Process each idx, chunk in the current collection.
    for idx, chunk in enumerate(chunks[1:], start=1):
        # Prepare chunk markup for the next step.
        chunk_markup = reply_markup if idx == len(chunks) - 1 else None
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Wait for query.message.reply_text before continuing this flow.
            await query.message.reply_text(chunk, parse_mode=parse_mode, reply_markup=chunk_markup)
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Wait for query.message.reply_text before continuing this flow.
            await query.message.reply_text(chunk, reply_markup=chunk_markup)


async def show_callback_loading(query, text: str = "⏳ *Memproses pilihan...*"):
    """Handle callback-related behavior in the Telegram bot flow."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        await safe_edit_message(query, text, parse_mode="Markdown")
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass


# Define build progress bar for callers in this flow.
def build_progress_bar(pct: float, length: int = 10) -> str:
    """Build the data structure or message text for progress bar."""
    # Prepare filled for the next step.
    filled = int(min(float(pct or 0), 100) / 100 * length)
    # Prepare empty for the next step.
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"


# Define parse human amount atom for callers in this flow.
def _parse_human_amount_atom(value: str | None) -> float:
    """Parse caller input for the parse human amount atom workflow in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = str(value or "").strip().lower()
    # Handle the missing or empty raw case.
    if not raw:
        # Return 0.0 to the caller.
        return 0.0

    # Prepare multiplier for the next step.
    multiplier = 1
    if re.search(r"(jt|juta)\b", raw):
        # Prepare multiplier for the next step.
        multiplier = 1_000_000
    elif re.search(r"(rb|ribu|k)\b", raw):
        # Prepare multiplier for the next step.
        multiplier = 1_000

    raw = re.sub(r"(jt|juta|rb|ribu|k)\b", "", raw).strip()

    # Handle the case where multiplier != 1.
    if multiplier != 1:
        raw = raw.replace(",", ".")
        raw = re.sub(r"[^0-9.]", "", raw)
        if raw.count(".") > 1:
            first, *rest = raw.split(".")
            raw = first + "." + "".join(rest)
        # Return float(raw or 0) * multiplier to the caller.
        return float(raw or 0) * multiplier

    raw = re.sub(r"[^0-9]", "", raw)
    # Return float(raw or 0) to the caller.
    return float(raw or 0)


# Define safe eval amount expression for callers in this flow.
def _safe_eval_amount_expression(expr: str) -> float:
    """Coordinate the safe eval amount expression logic in the Telegram handler layer.

    Args:
        expr: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Open a multi-line structure for the values below.
    allowed_ops = {
        # Include this value in the surrounding collection or call.
        ast.Add: operator.add,
        # Include this value in the surrounding collection or call.
        ast.Sub: operator.sub,
        # Include this value in the surrounding collection or call.
        ast.Mult: operator.mul,
        # Include this value in the surrounding collection or call.
        ast.Div: operator.truediv,
        # Include this value in the surrounding collection or call.
        ast.USub: operator.neg,
        # Include this value in the surrounding collection or call.
        ast.UAdd: operator.pos,
    # Close the structure that was opened above.
    }

    # Define eval for callers in this flow.
    def _eval(node):
        """Coordinate the eval logic in the Telegram handler layer.

        Args:
            node: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            Value produced by the existing return statements; shape is determined by the current implementation.

        Side effects:
            May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

        Flow constraints:
            Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
        """
        # Handle the case where isinstance(node, ast.Expression).
        if isinstance(node, ast.Expression):
            # Return _eval(node.body) to the caller.
            return _eval(node.body)
        # Handle the case where isinstance(node, ast.Constant) and isinstance(node.value, (in....
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            # Return float(node.value) to the caller.
            return float(node.value)
        # Handle the case where isinstance(node, ast.Num).
        if isinstance(node, ast.Num):
            # Return float(node.n) to the caller.
            return float(node.n)
        # Handle the case where isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops.
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
            # Return allowed_ops[type(node.op)](_eval(node.operand)) to the caller.
            return allowed_ops[type(node.op)](_eval(node.operand))
        # Handle the case where isinstance(node, ast.BinOp) and type(node.op) in allowed_ops.
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            # Prepare right for the next step.
            right = _eval(node.right)
            # Handle the case where isinstance(node.op, ast.Div) and right == 0.
            if isinstance(node.op, ast.Div) and right == 0:
                raise ValueError("division by zero")
            # Return allowed_ops[type(node.op)](_eval(node.left), right) to the caller.
            return allowed_ops[type(node.op)](_eval(node.left), right)
        raise ValueError("unsafe amount expression")

    tree = ast.parse(expr, mode="eval")
    # Return float(_eval(tree)) to the caller.
    return float(_eval(tree))


# Define parse human amount for callers in this flow.
def parse_human_amount(value: str | None) -> float:
    """Parse caller input for the parse human amount workflow in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = str(value or "").strip().lower()
    # Handle the missing or empty raw case.
    if not raw:
        # Return 0.0 to the caller.
        return 0.0

    if re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", raw):
        # Return _parse_human_amount_atom(raw) to the caller.
        return _parse_human_amount_atom(raw)

    has_math_operator = bool(re.search(r"[+*/x×:]|(?<=\s)-(?:\s|\d)", raw))
    # Handle the case where has_math_operator.
    if has_math_operator:
        token_pattern = re.compile(r"\d+(?:[.,]\d+)?\s*(?:jt|juta|rb|ribu|k)?", re.IGNORECASE)

        # Define repl for callers in this flow.
        def repl(match: re.Match) -> str:
            """Coordinate the repl logic in the Telegram handler layer.

            Args:
                match: Input value supplied by the caller; accepted shape follows the function signature and local validation.

            Returns:
                `str` value as defined by the function signature.

            Side effects:
                May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

            Flow constraints:
                Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
            """
            # Return str(_parse_human_amount_atom(match.group(0))) to the caller.
            return str(_parse_human_amount_atom(match.group(0)))

        # Prepare expr for the next step.
        expr = token_pattern.sub(repl, raw)
        expr = expr.replace("×", "*").replace("x", "*").replace(":", "/")
        expr = re.sub(r"\s+", "", expr)
        if re.fullmatch(r"[0-9.+\-*/()]+", expr):
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Prepare result for the next step.
                result = _safe_eval_amount_expression(expr)
                # Handle the case where result > 0.
                if result > 0:
                    # Return result to the caller.
                    return result
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Keep this intentionally empty block valid.
                pass

    # Return _parse_human_amount_atom(raw) to the caller.
    return _parse_human_amount_atom(raw)


# Define parse amount text for callers in this flow.
def parse_amount_text(value: str) -> float:
    """Parse caller input for the parse amount text workflow in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = str(value or "").strip().lower().replace(" ", "").replace(",", ".")
    # Handle the missing or empty raw case.
    if not raw:
        # Return 0 to the caller.
        return 0

    unit = ""
    for suffix in ["ribu", "rb", "juta", "jt", "miliar", "miliard", "milyard", "k", "m"]:
        # Handle the case where raw.endswith(suffix).
        if raw.endswith(suffix):
            # Prepare unit for the next step.
            unit = suffix
            # Prepare raw for the next step.
            raw = raw[: -len(suffix)]
            # Leave the loop after the target condition has been reached.
            break

    # Run this operation in a guarded block so failures can be handled.
    try:
        if unit in {"rb", "ribu", "k"}:
            # 331.063k means 331,063 rupiah here, not 331,063,000.
            if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
                return float(raw.replace(".", ""))
            # Return float(raw) * 1_000 to the caller.
            return float(raw) * 1_000
        if unit in {"jt", "juta", "m"}:
            # Return float(raw) * 1_000_000 to the caller.
            return float(raw) * 1_000_000
        if unit in {"miliar", "miliard", "milyard"}:
            # Return float(raw) * 1_000_000_000 to the caller.
            return float(raw) * 1_000_000_000
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
            return float(raw.replace(".", ""))
        # Return float(raw) to the caller.
        return float(raw)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return 0 to the caller.
        return 0

# Define extract split bill total amount for callers in this flow.
def extract_split_bill_total_amount(raw_text: str) -> float | None:
    """Extract the required part of input for split bill total amount."""
    text = str(raw_text or "").strip()
    amount_token = r"(?P<amount>\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m)?)"
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"

    # Open a multi-line structure for the values below.
    patterns = [
        rf"{amount_token}\s+{split_word}\s*(?:jadi\s*)?\d+",
        rf"{amount_token}\s+{friend_marker}\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{{0,80}}\s+{split_word}\s*(?:jadi\s*)?\d+",
    # Close the structure that was opened above.
    ]

    # Process each pattern in the current collection.
    for pattern in patterns:
        # Prepare match for the next step.
        match = re.search(pattern, text, flags=re.IGNORECASE)
        # Handle the case where match.
        if match:
            return parse_amount_text(match.group("amount"))

    # Return None to the caller.
    return None


# Handle the asynchronous clear tracked inline keyboard workflow.
async def clear_tracked_inline_keyboard(context: ContextTypes.DEFAULT_TYPE, chat_id, state_key: str) -> None:
    """Remove the inline keyboard from a previously tracked prompt message."""
    # Handle the case where context is None.
    if context is None:
        # Return control to the caller.
        return
    user_data = getattr(context, "user_data", {}) or {}
    # Prepare message id for the next step.
    message_id = user_data.pop(state_key, None)
    # Handle the missing or empty message_id or not chat_id case.
    if not message_id or not chat_id:
        # Return control to the caller.
        return
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Wait for context.bot.edit_message_reply_markup before continuing this flow.
        await context.bot.edit_message_reply_markup(
            # Prepare chat id for the next step.
            chat_id=chat_id,
            # Prepare message id for the next step.
            message_id=int(message_id),
            # Prepare reply markup for the next step.
            reply_markup=None,
        # Close the structure that was opened above.
        )
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass


# Handle the asynchronous reply tracked inline keyboard workflow.
async def reply_tracked_inline_keyboard(
    # Include this value in the surrounding collection or call.
    update: Update,
    # Include this value in the surrounding collection or call.
    context: ContextTypes.DEFAULT_TYPE,
    # Include this value in the surrounding collection or call.
    text: str,
    # Include this value in the surrounding collection or call.
    *,
    # Include this value in the surrounding collection or call.
    parse_mode: str | None = None,
    # Prepare reply markup for the next step.
    reply_markup=None,
    state_key: str = "last_inline_prompt_message_id",
    # Include this value in the surrounding collection or call.
    **kwargs,
# Close the structure that was opened above.
):
    """Reply with an inline keyboard and remember its message id for cleanup."""
    message = getattr(update, "message", None)
    # Handle the case where message is None.
    if message is None:
        # Return None to the caller.
        return None

    chat = getattr(update, "effective_chat", None)
    chat_id = getattr(chat, "id", None) or getattr(message, "chat_id", None)
    # Wait for clear_tracked_inline_keyboard before continuing this flow.
    await clear_tracked_inline_keyboard(context, chat_id, state_key)

    # Open a multi-line structure for the values below.
    sent = await message.reply_text(
        # Include this value in the surrounding collection or call.
        text,
        # Prepare parse mode for the next step.
        parse_mode=parse_mode,
        # Prepare reply markup for the next step.
        reply_markup=reply_markup,
        # Include this value in the surrounding collection or call.
        **kwargs,
    # Close the structure that was opened above.
    )
    # Handle the case where reply_markup is not None.
    if reply_markup is not None:
        context.user_data[state_key] = getattr(sent, "message_id", None)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Run this statement as part of the current workflow.
        context.user_data.pop(state_key, None)
    # Return sent to the caller.
    return sent
