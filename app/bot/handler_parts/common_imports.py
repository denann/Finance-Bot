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
from app.formatting import format_rupiah
# Import shlex for this module's local operations.
import shlex
# Import os for this module's local operations.
import os
# Import app.config so this module can use its helpers.
from app.config import (
    ALLOWED_USER_ID,
    SHEET_CATEGORIES,
    GEMINI_API_KEY,
    SHEET_TRANSACTIONS,
    SHEET_ACCOUNTS,
    SHEET_BUDGETS,
    SHEET_PENDING_EXPENSES,
    SHEET_DEBTS,
    SHEET_DEBT_PAYMENTS,
    WEBHOOK_URL,
    APP_PORT,
)

# Import app.services.net_worth_service so this module can use its helpers.
from app.services.net_worth_service import (
    add_asset,
    get_assets,
    update_asset,
    deactivate_asset,
    calculate_net_worth,
    create_net_worth_snapshot,
    get_net_worth_snapshots,
    calculate_asset_gain,
)

# Import app.bot.keyboards so this module can use its helpers.
from app.bot.keyboards import (
    account_keyboard,
    confirm_keyboard,
    cancel_keyboard,
    receipt_ownership_keyboard,
    SKIP_ACCOUNT_CALLBACK_VALUE,
    SKIP_ACCOUNT_NAME,
)
# Import app.nlp.regex_parser so this module can use its helpers.
from app.nlp.regex_parser import parse_with_regex, parse_debt_input, detect_date, detect_date_result, strip_date_phrases
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
    save_transaction,
    save_transactions_batch,
    get_all_accounts,
    get_account_balance,
    update_account_balance,
    get_recent_transactions,
    preview_edit_transaction_by_ref,
    get_transactions_for_export,
    calculate_account_deltas,
    update_transaction_debt_relation,
    clear_transaction_debt_relation,
    EXPORT_TRANSACTION_COLUMNS,
)

# Import app.nlp.gemini_intent_router so this module can use its helpers.
from app.nlp.gemini_intent_router import (
    should_try_gemini_intent_router,
    route_intent_with_gemini,
)

# Import app.services.budget_service so this module can use its helpers.
from app.services.budget_service import (
    set_budget,
    get_budget_summary,
    check_budget_after_transaction,
    normalize_month,
    format_month_label,
    get_budget_months,
)
# Import app.services.report_service so this module can use its helpers.
from app.services.report_service import (
    get_daily_report,
    get_weekly_report,
    get_monthly_report,
    get_account_report,
    search_transactions,
    parse_report_month_arg,
    parse_report_date_arg,
    split_report_period_and_category_arg,
    split_report_filter_args,
    split_account_period_arg,
    enrich_transactions_with_debt_info,
    summarize,
)

# Import app.services.finance_insight_service so this module can use its helpers.
from app.services.finance_insight_service import (
    build_monthly_finance_context,
    build_ask_finance_context,
    build_audit_context,
    build_coach_context,
    normalize_month_arg as normalize_insight_month,
    should_handle_finance_question,
    route_finance_question_mode,
)
# Import app.nlp.gemini_finance_insight so this module can use its helpers.
from app.nlp.gemini_finance_insight import generate_finance_insight

# Import app.services.debt_service so this module can use its helpers.
from app.services.debt_service import (
    add_debt,
    add_payment,
    add_payment_by_person,
    estimate_payment_outcome,
    summarize_debt_rows_for_settlement,
    settle_selected_debt_ids,
    format_debt_net_position_lines,
    parse_sheet_number,
    offset_debt_by_person,
    settle_opposite_debts_by_person,
    get_debt_summary,
    get_debt_person_summary,
    get_debt_person_detail,
    get_debt_by_person,
    get_debt_by_id_any_status,
    normalize_person_name,
    is_voided_debt,
    void_debts_for_transaction,
    update_debt,
)
from app.application.transaction_debt import (
    delete_transactions_by_refs,
    preview_delete_transactions_by_refs,
    edit_transaction_by_ref,
    preview_void_debt,
    preview_void_debts_by_person,
    void_debt,
    void_debt_ids,
    void_debts_by_person,
)
# Import csv for this module's local operations.
import csv
# Import tempfile for this module's local operations.
import tempfile
# Import app.services.recurring_service so this module can use its helpers.
from app.services.recurring_service import (
    add_recurring_rule,
    get_recurring_rules,
    disable_recurring_rule,
    process_due_recurring_rules,
    mark_recurring_rule_paid,
    edit_recurring_rule,
)
# Import app.services.pending_expense_service so this module can use its helpers.
from app.services.pending_expense_service import (
    add_pending_expense_from_text,
    build_pending_expense_from_text,
    save_pending_expense,
    get_pending_expenses,
    mark_pending_paid,
    cancel_pending_expense,
    is_pending_expense_text,
)

# ── Cross-part shared helpers ────────────────────────────────────────────────
# Implementation note for this project-specific finance flow.
# Keep normal imports working without relying on global variables from handlers.py.

TELEGRAM_SAFE_MESSAGE_LIMIT = 3800
GEMINI_INTENT_CONFIDENCE_EXECUTE = 0.80
GEMINI_INTENT_CONFIDENCE_CLARIFY = 0.60


# Helper for short debt id.
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
    if len(debt_id) <= 18:
        return debt_id
    return debt_id[:18] + "..."


# Helper for md safe.
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


# Helper for md code text.
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


# Helper for short txn id.
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
    if len(txn_id) <= 18:
        return txn_id
    return txn_id[:18] + "..."





# Helper for normalize sheet date for display.
def normalize_sheet_date_for_display(value) -> str:
    """Normalize Google Sheets date values before showing them to users.

    Google Sheets can return dates as serial numbers when old rows were written
    with USER_ENTERED. This keeps `/hutang`, reports, and audit output readable
    without changing stored historical data.
    """
    if value is None:
        return ""

    # Prepare raw from the incoming input.
    raw = str(value).strip()
    if not raw or raw.lower() in {"-", "none", "nan"}:
        return ""

    match = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", raw)
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
            serial = int(float(raw))
            if 20000 <= serial <= 80000:
                # Import datetime so this module can use its helpers.
                from datetime import timedelta
                dt = datetime(1899, 12, 30) + timedelta(days=serial)
                return dt.strftime("%Y-%m-%d")
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass

    return raw

# Helper for format indonesian date group label.
def format_indonesian_date_group_label(date_value) -> str:
    """Format data into a readable display for indonesian date group label."""
    # Prepare raw from the incoming input.
    raw = normalize_sheet_date_for_display(date_value)
    if not raw or raw.lower() in {"-", "none", "nan", "tanpa tanggal"}:
        return "🗓️ Tanpa tanggal:"

    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", raw)
    if match:
        # Run this operation in a guarded block so failures can be handled.
        try:
            dt = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            weekdays = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            months = [
                "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                "Juli", "Agustus", "September", "Oktober", "November", "Desember",
            ]
            return f"🗓️ {weekdays[dt.weekday()]}, {dt.day} {months[dt.month - 1]} {dt.year}:"
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass

    return f"🗓️ {raw}:"


# Helper for safe float for display.
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
        if isinstance(value, str):
            raw = value.strip().replace("Rp", "").replace("rp", "").replace(" ", "")
            if "." in raw and "," in raw:
                raw = raw.replace(".", "").replace(",", ".")
            elif "," in raw:
                raw = raw.replace(",", ".")
            elif "." in raw:
                parts = raw.split(".")
                # Handle len(parts) > 1 and all(len(part) == 3 for part in parts[1:]).
                if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
                    raw = raw.replace(".", "")
            raw = re.sub(r"[^0-9.-]", "", raw)
            return float(raw or 0)
        return float(value or 0)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return default


# Helper for get transaction receivable parts.
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
    if parts:
        return [
            {
                "person_name": str((part or {}).get("person_name") or "Tanpa nama").strip(),
                "remaining_amount": _safe_float_for_display((part or {}).get("remaining_amount", 0)),
            }
            # Iterate through each part.
            for part in parts
            if _safe_float_for_display((part or {}).get("remaining_amount", 0)) > 0
        ]

    receivable_by_person = {}
    for debt in (txn or {}).get("linked_debts") or []:
        debt_type = str((debt or {}).get("type", "") or "").strip().lower()
        if debt_type != "receivable":
            # Skip the rest of this loop iteration after handling this case.
            continue
        person = str((debt or {}).get("person_name") or "Tanpa nama").strip()
        amount = _safe_float_for_display((debt or {}).get("remaining_amount", 0))
        if amount > 0:
            receivable_by_person[person] = receivable_by_person.get(person, 0.0) + amount

    if receivable_by_person:
        return [
            {"person_name": person, "remaining_amount": amount}
            # Iterate through each person, amount.
            for person, amount in receivable_by_person.items()
        ]

    receivable = _safe_float_for_display((txn or {}).get("debt_receivable_remaining", 0))
    people = [str(x).strip() for x in ((txn or {}).get("debt_people") or []) if str(x).strip()]
    if receivable > 0 and people:
        if len(people) == 1:
            return [{"person_name": people[0], "remaining_amount": receivable}]
        share = receivable / len(people)
        return [{"person_name": person, "remaining_amount": share} for person in people]
    if receivable > 0:
        return [{"person_name": "Tanpa nama", "remaining_amount": receivable}]
    return []


# Helper for get transaction payable parts.
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
    if parts:
        return [
            {
                "person_name": str((part or {}).get("person_name") or "Tanpa nama").strip(),
                "remaining_amount": _safe_float_for_display((part or {}).get("remaining_amount", 0)),
            }
            # Iterate through each part.
            for part in parts
            if _safe_float_for_display((part or {}).get("remaining_amount", 0)) > 0
        ]

    # Extract payable by person for validation.
    payable_by_person = {}
    for debt in (txn or {}).get("linked_debts") or []:
        debt_type = str((debt or {}).get("type", "") or "").strip().lower()
        if debt_type != "payable":
            # Skip the rest of this loop iteration after handling this case.
            continue
        person = str((debt or {}).get("person_name") or "Tanpa nama").strip()
        amount = _safe_float_for_display((debt or {}).get("remaining_amount", 0))
        if amount > 0:
            payable_by_person[person] = payable_by_person.get(person, 0.0) + amount

    return [
        {"person_name": person, "remaining_amount": amount}
        # Iterate through each person, amount.
        for person, amount in payable_by_person.items()
    ]


# Helper for get net expense after receivable.
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
    receivable = _safe_float_for_display(
        (txn or {}).get("debt_receivable_original", (txn or {}).get("debt_receivable_remaining", 0))
    )
    return max(amount - receivable, 0.0)


# Helper for build debt parts text.
def build_debt_parts_text(parts: list[dict]) -> str:
    """Build the data structure or message text for debt parts text."""
    chunks = []
    # Iterate through each part.
    for part in parts or []:
        person = md_safe((part or {}).get("person_name") or "Tanpa nama")
        amount = _safe_float_for_display((part or {}).get("remaining_amount", 0))
        if amount <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        chunks.append(f"{format_rupiah(amount)} ({person})")
    return ", ".join(chunks)


# Helper for has expense transactions.
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
    return any(
        str((txn or {}).get("type", "") or "").strip().lower() == "expense"
        # Iterate through each txn.
        for txn in (transactions or [])
    )


# Helper for has net gross difference.
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
    # Iterate through each txn.
    for txn in transactions or []:
        txn_type = str((txn or {}).get("type", "") or "").strip().lower()
        if txn_type != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue
        gross = _safe_float_for_display((txn or {}).get("amount", 0))
        net = get_net_expense_after_receivable(txn)
        if abs(gross - net) > 0.0001:
            return True
    return False


# Helper for append net gross note.
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
    # Validate missing force and not has expense transactions(transactions) before continuing.
    if not force and not has_expense_transactions(transactions):
        return
    lines.append("ℹ️ Catatan: nominal pengeluaran ditampilkan sebagai *Net (Gross)* jika ada piutang split bill terkait.\n")


# Helper for format expense net gross.
def format_expense_net_gross(net_amount: float, gross_amount: float, *, always_show_gross: bool = False) -> str:
    """Format data into a readable display for expense net gross."""
    net = _safe_float_for_display(net_amount)
    gross = _safe_float_for_display(gross_amount)
    # Handle always show gross or abs(net - gross) > 0.
    if always_show_gross or abs(net - gross) > 0.0001:
        return f"{format_rupiah(net)} ({format_rupiah(gross)})"
    return format_rupiah(gross)


# Helper for get transaction account text.
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


# Helper for build transaction display lines.
def build_transaction_display_lines(
    txn: dict,
    *,
    index: int | None = None,
    include_date: bool = True,
    include_id: bool = False,
    contribution_pct: float | None = None,
    note: str | None = None,
) -> list[str]:
    """Build the data structure or message text for transaction display lines."""
    txn = txn or {}
    txn_type = str(txn.get("type", "") or "").strip().lower()
    amount = _safe_float_for_display(txn.get("amount", 0))
    icon = {
        "expense": "❌",
        "income": "✅",
        "transfer": "🔄",
    }.get(txn_type, "❓")

    prefix = f"{index}. " if index is not None else ""
    description = md_safe(txn.get("description") or txn.get("subject") or "-")
    date = str(txn.get("date", "") or "").strip()
    category = md_safe(txn.get("category") or "-")
    # Extract account text for validation.
    account_text = md_safe(get_transaction_account_text(txn))

    lines = [f"{prefix}{icon} *{description}*"]
    meta = []
    if include_date and date:
        meta.append(f"📅 {md_safe(date)}")

    if txn_type == "expense":
        net_expense = get_net_expense_after_receivable(txn)
        meta.append(f"💰 *{format_expense_net_gross(net_expense, amount)}*")
    elif txn_type == "income":
        meta.append(f"💰 *{format_rupiah(amount)}*")
    elif txn_type == "transfer":
        meta.append(f"🔁 *{format_rupiah(amount)}*")
    # Use the fallback path when no earlier branch matched.
    else:
        meta.append(f"💰 *{format_rupiah(amount)}*")

    # Append the current value to meta.
    meta.append(category)
    meta.append(f"🏦 {account_text}")
    lines.append(f"   {' | '.join(meta)}")

    # Prepare receivable parts from the incoming input.
    receivable_parts = get_transaction_receivable_parts(txn)
    # Prepare receivable text from the incoming input.
    receivable_text = build_debt_parts_text(receivable_parts)
    if txn_type == "expense" and receivable_text:
        lines.append(f"   ↳ 🤝 Piutang aktif: {receivable_text}")

    # Prepare payable parts from the incoming input.
    payable_parts = get_transaction_payable_parts(txn)
    # Prepare payable text from the incoming input.
    payable_text = build_debt_parts_text(payable_parts)
    if payable_text:
        lines.append(f"   ↳ 🔴 Utang terkait aktif: {payable_text}")

    if contribution_pct is not None:
        lines.append(f"   ↳ 📊 {contribution_pct:.1f}% dari pengeluaran")

    if note:
        lines.append(f"   📝 {md_safe(note)}")

    if include_id:
        txn_id = str(txn.get("id", "") or "").strip()
        if txn_id:
            lines.append(f"   🔖 `{md_code_text(txn_id)}`")

    return lines


# Helper for build transactions full text shared.
def build_transactions_full_text_shared(
    transactions: list[dict],
    title: str,
    account_filter: str | None = None,
    *,
    current_balance: float | None = None,
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
    # Load transactions for the current calculation.
    transactions = enrich_transactions_with_debt_info(transactions or [])
    lines = [f"🧾 *{md_safe(title)}*\n"]
    append_net_gross_note(lines, transactions)

    total_income = 0.0
    total_expense = 0.0
    total_net_expense = 0.0
    total_transfer = 0.0
    total_transfer_in = 0.0
    total_transfer_out = 0.0
    account_key = str(account_filter or "").strip().lower()

    # Extract current date group for validation.
    current_date_group = None
    # Iterate through each i, txn.
    for i, txn in enumerate(transactions, 1):
        txn_type = str(txn.get("type", "") or "").strip().lower()
        amount = _safe_float_for_display(txn.get("amount", 0))
        source_account = str(txn.get("account", "") or "").strip()
        target_account = str(txn.get("to_account", "") or "").strip()
        source_match = bool(account_key and source_account.lower() == account_key)
        target_match = bool(account_key and target_account.lower() == account_key)

        if account_key:
            if txn_type == "income" and source_match:
                total_income += amount
            elif txn_type == "expense" and source_match:
                total_expense += amount
                total_net_expense += get_net_expense_after_receivable(txn)
            elif txn_type == "transfer":
                if source_match:
                    total_transfer_out += amount
                if target_match:
                    total_transfer_in += amount
                if source_match or target_match:
                    total_transfer += amount
        # Use the fallback path when no earlier branch matched.
        else:
            if txn_type == "income":
                total_income += amount
            elif txn_type == "expense":
                total_expense += amount
                total_net_expense += get_net_expense_after_receivable(txn)
            elif txn_type == "transfer":
                total_transfer += amount

        date_group = str(txn.get("date", "") or "Tanpa tanggal").strip() or "Tanpa tanggal"
        if date_group != current_date_group:
            lines.append(f"\n*{md_safe(format_indonesian_date_group_label(date_group))}*")
            # Extract current date group for validation.
            current_date_group = date_group

        # Append the current value to lines.
        lines.extend(build_transaction_display_lines(txn, index=i, include_date=False, include_id=True))

    if account_key:
        net_gross = total_income + total_transfer_in - total_expense - total_transfer_out
        net_after_receivable = total_income + total_transfer_in - total_net_expense - total_transfer_out
        # Prepare expense text from the incoming input.
        expense_text = format_expense_net_gross(total_net_expense, total_expense)
        # Prepare net text from the incoming input.
        net_text = format_expense_net_gross(net_after_receivable, net_gross)
        summary_lines = [
            "\n*Ringkasan Rekening:*",
        ]
        if current_balance is not None:
            summary_lines.append(f"💰 Saldo Saat Ini : *{format_rupiah(current_balance)}*")
        summary_lines.extend([
            f"✅ Income          : *{format_rupiah(total_income)}*",
            f"❌ Expense         : *{expense_text}*",
            f"🔁 Transfer Masuk  : *{format_rupiah(total_transfer_in)}*",
            f"🔁 Transfer Keluar : *{format_rupiah(total_transfer_out)}*",
            f"📊 Net Rekening    : *{net_text}*",
            f"📝 Total           : *{len(transactions)} transaksi*",
        ])
        lines.append("\n".join(summary_lines))
    # Use the fallback path when no earlier branch matched.
    else:
        net_gross = total_income - total_expense
        net_after_receivable = total_income - total_net_expense
        # Prepare expense text from the incoming input.
        expense_text = format_expense_net_gross(total_net_expense, total_expense)
        # Prepare net text from the incoming input.
        net_text = format_expense_net_gross(net_after_receivable, net_gross)
        lines.append(
            "\n*Ringkasan:*\n"
            f"✅ Income   : *{format_rupiah(total_income)}*\n"
            f"❌ Expense  : *{expense_text}*\n"
            f"🔄 Transfer : *{format_rupiah(total_transfer)}*\n"
            f"📊 Net      : *{net_text}*\n"
            f"📝 Total    : *{len(transactions)} transaksi*"
        )

    lines.append(
        "\nNomor di atas bisa dipakai untuk koreksi setelah command ini:\n"
        "`/delete_txn 1` atau `/edit_txn 1 amount=15000`"
    )

    return "\n".join(lines)


# Helper for is authorized.
def is_authorized(update: Update) -> bool:
    """Check whether a condition is true for authorized."""
    # Validate missing update.effective user before continuing.
    if not update.effective_user:
        return False
    return update.effective_user.id == ALLOWED_USER_ID


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
    message = (
        "⛔ Anda tidak punya akses ke bot ini.\n\n"
        f"User ID Anda: `{user_id}`\n\n"
        "Bot ini hanya bisa digunakan oleh user yang sudah diizinkan."
    )

    if update.message:
        await update.message.reply_text(message, parse_mode="Markdown")
        return

    if update.callback_query:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Await update.callback query.answer before continuing.
            await update.callback_query.answer(
                "⛔ Anda tidak punya akses.",
                show_alert=True,
            )
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass
        return


# Helper for split long message.
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
    # Validate missing text before continuing.
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""

    for block in text.split("\n\n"):
        block = block.strip()
        # Validate missing block before continuing.
        if not block:
            # Skip the rest of this loop iteration after handling this case.
            continue

        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= max_len:
            current = candidate
            # Skip the rest of this loop iteration after handling this case.
            continue

        if current:
            # Append the current value to chunks.
            chunks.append(current)
            current = ""

        if len(block) <= max_len:
            current = block
            # Skip the rest of this loop iteration after handling this case.
            continue

        line_current = ""
        # Iterate through each line.
        for line in block.splitlines():
            candidate_line = f"{line_current}\n{line}".strip() if line_current else line
            if len(candidate_line) <= max_len:
                line_current = candidate_line
            # Use the fallback path when no earlier branch matched.
            else:
                if line_current:
                    # Append the current value to chunks.
                    chunks.append(line_current)
                if len(line) > max_len:
                    # Iterate through each i.
                    for i in range(0, len(line), max_len):
                        # Append the current value to chunks.
                        chunks.append(line[i:i + max_len])
                    line_current = ""
                # Use the fallback path when no earlier branch matched.
                else:
                    line_current = line

        if line_current:
            # Append the current value to chunks.
            chunks.append(line_current)

    if current:
        # Append the current value to chunks.
        chunks.append(current)

    return chunks


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
    # Iterate through each part.
    for part in split_long_message(text):
        # Run this operation in a guarded block so failures can be handled.
        try:
            await update.message.reply_text(part, parse_mode="Markdown")
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Send the Telegram response before continuing.
            await update.message.reply_text(part)


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
    chunks = split_long_message(text)
    sent_message = None
    # Iterate through each idx, chunk.
    for idx, chunk in enumerate(chunks):
        markup = reply_markup if idx == len(chunks) - 1 else None
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Send the Telegram response before continuing.
            sent_message = await message.reply_text(chunk, parse_mode=parse_mode, reply_markup=markup, **kwargs)
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Send the Telegram response before continuing.
            sent_message = await message.reply_text(chunk, reply_markup=markup, **kwargs)

    if reply_markup is not None and sent_message is not None:
        from app.bot.pending_actions import bind_current_action_message

        bind_current_action_message(reply_markup, getattr(sent_message, "message_id", None))
    return sent_message


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
    if update.message:
        # Send the Telegram response before continuing.
        return await reply_message_safely(update.message, text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    return None


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
    chunks = split_long_message(text)

    async def _edit(payload: str, mode: str | None, markup):
        """Edit the target Telegram message with one prepared text chunk.

        Args:
            payload: Message text chunk that fits Telegram length limits.
            mode: Optional parse mode for this edit attempt.
            markup: Optional inline keyboard attached to this chunk.

        Returns:
            Telegram API result from `message.edit_text`.
        """
        return await message.edit_text(
            payload,
            parse_mode=mode,
            reply_markup=markup,
            **kwargs,
        )

    first_markup = reply_markup if len(chunks) == 1 else None
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Await  edit before continuing.
        await _edit(chunks[0], parse_mode, first_markup)
    # Handle an expected failure from the guarded operation above.
    except BadRequest:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Await  edit before continuing.
            await _edit(chunks[0], None, first_markup)
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Send the Telegram response before continuing.
            await message.reply_text(chunks[0], reply_markup=first_markup)

    # Iterate through each idx, chunk.
    for idx, chunk in enumerate(chunks[1:], start=1):
        markup = reply_markup if idx == len(chunks) - 1 else None
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Send the Telegram response before continuing.
            await message.reply_text(chunk, parse_mode=parse_mode, reply_markup=markup)
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Send the Telegram response before continuing.
            await message.reply_text(chunk, reply_markup=markup)


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
    chunks = split_long_message(text)
    first = chunks[0]

    if len(chunks) > 1:
        suffix = "\n\n📄 *Pesan terlalu panjang, detail lanjutan dikirim di bawah.*"
        max_first_len = TELEGRAM_SAFE_MESSAGE_LIMIT - len(suffix) - 10
        first = first[:max_first_len].rstrip() + suffix

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
        return await query.message.edit_text(
            payload,
            parse_mode=mode,
            reply_markup=markup,
            **kwargs,
        )

    first_markup = reply_markup if len(chunks) == 1 else None

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Await  edit before continuing.
        await _edit(first, parse_mode, first_markup)
    # Handle an expected failure from the guarded operation above.
    except BadRequest as exc:
        err = str(exc).lower()
        if "message is not modified" in err:
            # Keep this intentionally empty block valid.
            pass
        elif "message_too_long" in err or "message is too long" in err or len(first) > 4096:
            safe_first = first[:3500].rstrip() + "\n\n📄 Pesan terlalu panjang, detail lanjutan dikirim di bawah."
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Await  edit before continuing.
                await _edit(safe_first, None, first_markup)
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Send the Telegram response before continuing.
                await query.message.reply_text(safe_first, reply_markup=first_markup)
        # Use the fallback path when no earlier branch matched.
        else:
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Await  edit before continuing.
                await _edit(first, None, first_markup)
            # Handle an expected failure from the guarded operation above.
            except BadRequest:
                # Send the Telegram response before continuing.
                await query.message.reply_text(first, reply_markup=first_markup)

    # Iterate through each idx, chunk.
    for idx, chunk in enumerate(chunks[1:], start=1):
        chunk_markup = reply_markup if idx == len(chunks) - 1 else None
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Send the Telegram response before continuing.
            await query.message.reply_text(chunk, parse_mode=parse_mode, reply_markup=chunk_markup)
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Send the Telegram response before continuing.
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


# Helper for build progress bar.
def build_progress_bar(pct: float, length: int = 10) -> str:
    """Build the data structure or message text for progress bar."""
    filled = int(min(float(pct or 0), 100) / 100 * length)
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"


# Helper for parse human amount atom.
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
    # Validate missing raw before continuing.
    if not raw:
        return 0.0

    multiplier = 1
    if re.search(r"(jt|juta)\b", raw):
        multiplier = 1_000_000
    elif re.search(r"(rb|ribu|k)\b", raw):
        multiplier = 1_000

    raw = re.sub(r"(jt|juta|rb|ribu|k)\b", "", raw).strip()

    if multiplier != 1:
        raw = raw.replace(",", ".")
        raw = re.sub(r"[^0-9.]", "", raw)
        if raw.count(".") > 1:
            first, *rest = raw.split(".")
            raw = first + "." + "".join(rest)
        return float(raw or 0) * multiplier

    raw = re.sub(r"[^0-9]", "", raw)
    return float(raw or 0)


# Helper for safe eval amount expression.
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
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # Helper for eval.
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
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Num):
            return float(node.n)
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            right = _eval(node.right)
            if isinstance(node.op, ast.Div) and right == 0:
                raise ValueError("division by zero")
            return allowed_ops[type(node.op)](_eval(node.left), right)
        raise ValueError("unsafe amount expression")

    tree = ast.parse(expr, mode="eval")
    return float(_eval(tree))


# Helper for parse human amount.
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
    # Validate missing raw before continuing.
    if not raw:
        return 0.0

    if re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", raw):
        return _parse_human_amount_atom(raw)

    has_math_operator = bool(re.search(r"[+*/x×:]|(?<=\s)-(?:\s|\d)", raw))
    if has_math_operator:
        token_pattern = re.compile(r"\d+(?:[.,]\d+)?\s*(?:jt|juta|rb|ribu|k)?", re.IGNORECASE)

        # Helper for repl.
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
            return str(_parse_human_amount_atom(match.group(0)))

        expr = token_pattern.sub(repl, raw)
        expr = expr.replace("×", "*").replace("x", "*").replace(":", "/")
        expr = re.sub(r"\s+", "", expr)
        if re.fullmatch(r"[0-9.+\-*/()]+", expr):
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Build result for the response flow.
                result = _safe_eval_amount_expression(expr)
                if result > 0:
                    return result
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Keep this intentionally empty block valid.
                pass

    return _parse_human_amount_atom(raw)


# Helper for parse amount text.
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
    # Validate missing raw before continuing.
    if not raw:
        return 0

    unit = ""
    for suffix in ["ribu", "rb", "juta", "jt", "miliar", "miliard", "milyard", "k", "m"]:
        if raw.endswith(suffix):
            unit = suffix
            # Prepare raw from the incoming input.
            raw = raw[: -len(suffix)]
            # Leave the loop after the target condition has been reached.
            break

    # Run this operation in a guarded block so failures can be handled.
    try:
        if unit in {"rb", "ribu", "k"}:
            # 331.063k means 331,063 rupiah here, not 331,063,000.
            if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
                return float(raw.replace(".", ""))
            return float(raw) * 1_000
        if unit in {"jt", "juta", "m"}:
            return float(raw) * 1_000_000
        if unit in {"miliar", "miliard", "milyard"}:
            return float(raw) * 1_000_000_000
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
            return float(raw.replace(".", ""))
        return float(raw)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return 0

# Helper for extract split bill total amount.
def extract_split_bill_total_amount(raw_text: str) -> float | None:
    """Extract the required part of input for split bill total amount."""
    text = str(raw_text or "").strip()
    amount_token = r"(?P<amount>\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m)?)"
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"

    patterns = [
        rf"{amount_token}\s+{split_word}\s*(?:jadi\s*)?\d+",
        rf"{amount_token}\s+{friend_marker}\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{{0,80}}\s+{split_word}\s*(?:jadi\s*)?\d+",
    ]

    # Iterate through each pattern.
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_amount_text(match.group("amount"))

    return None


# Handle the asynchronous clear tracked inline keyboard workflow.
async def clear_tracked_inline_keyboard(context: ContextTypes.DEFAULT_TYPE, chat_id, state_key: str) -> None:
    """Remove the inline keyboard from a previously tracked prompt message."""
    if context is None:
        return
    user_data = getattr(context, "user_data", {}) or {}
    message_id = user_data.pop(state_key, None)
    # Validate missing message id or not chat id before continuing.
    if not message_id or not chat_id:
        return
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Send the Telegram response before continuing.
        await context.bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=int(message_id),
            reply_markup=None,
        )
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass


# Handle the asynchronous reply tracked inline keyboard workflow.
async def reply_tracked_inline_keyboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    *,
    parse_mode: str | None = None,
    reply_markup=None,
    state_key: str = "last_inline_prompt_message_id",
    **kwargs,
):
    """Reply with an inline keyboard and remember its message id for cleanup."""
    message = getattr(update, "message", None)
    if message is None:
        return None

    chat = getattr(update, "effective_chat", None)
    chat_id = getattr(chat, "id", None) or getattr(message, "chat_id", None)
    # Await clear tracked inline keyboard before continuing.
    await clear_tracked_inline_keyboard(context, chat_id, state_key)

    sent = await message.reply_text(
        text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        **kwargs,
    )
    if reply_markup is not None:
        context.user_data[state_key] = getattr(sent, "message_id", None)
    # Use the fallback path when no earlier branch matched.
    else:
        context.user_data.pop(state_key, None)
    return sent


async def send_financial_mutation_preview(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    operation: str,
    payload: dict,
    preview_text: str,
):
    """Create and send a one-shot final preview for a command mutation.

    Args:
        update: Telegram command update used to send the preview.
        context: Per-user PTB state that holds the in-memory action store.
        operation: Stable command mutation name routed on confirmation.
        payload: Exact validated arguments represented by ``preview_text``.
        preview_text: Markdown-safe final preview shown before any write.

    Returns:
        The created immutable action record.

    Side effects:
        Stores only an in-memory action snapshot and sends Telegram output. It
        does not call any financial write service.
    """

    from app.bot.pending_actions import bind_action_message, create_pending_action

    owner_user_id = int(getattr(getattr(update, "effective_user", None), "id", 0) or 0)
    action = create_pending_action(
        context.user_data,
        owner_user_id=owner_user_id,
        flow_type="command_mutation",
        payload={"operation": operation, "arguments": payload},
    )
    action_id = action["action_id"]
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Simpan", callback_data=f"confirm:{action_id}"),
            InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{action_id}"),
        ]
    ])
    sent = await update.message.reply_text(preview_text, parse_mode="Markdown", reply_markup=keyboard)
    bind_action_message(context.user_data, action_id, getattr(sent, "message_id", None))
    return action
