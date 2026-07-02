"""Shared handler utilities for formatting messages, reports, health checks, and common imports."""


import re
import ast
import operator
import io
from datetime import datetime
from difflib import SequenceMatcher
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from telegram.error import BadRequest
import shlex
import os
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

from app.bot.keyboards import (
    account_keyboard,
    confirm_keyboard,
    cancel_keyboard,
    SKIP_ACCOUNT_CALLBACK_VALUE,
    SKIP_ACCOUNT_NAME,
)
from app.nlp.regex_parser import parse_with_regex, parse_debt_input, detect_date, strip_date_phrases
from app.nlp.gemini_parser import parse_with_pending_fallback
from app.nlp.gemini_image_parser import parse_transactions_from_image
from app.sheets.client import get_all_records, get_spreadsheet, rollback_current_sheets_transaction
from app.services.transaction_service import (
    save_transaction,
    save_transactions_batch,
    get_all_accounts,
    get_recent_transactions,
    preview_delete_transactions_by_refs,
    delete_transactions_by_refs,
    preview_edit_transaction_by_ref,
    edit_transaction_by_ref,
    get_transactions_for_export,
    calculate_account_deltas,
    update_transaction_debt_relation,
    clear_transaction_debt_relation,
    EXPORT_TRANSACTION_COLUMNS,
)

from app.nlp.gemini_intent_router import (
    should_try_gemini_intent_router,
    route_intent_with_gemini,
)

from app.services.budget_service import (
    set_budget,
    get_budget_summary,
    check_budget_after_transaction,
    normalize_month,
    format_month_label,
    get_budget_months,
)
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
)

from app.services.finance_insight_service import (
    build_monthly_finance_context,
    build_ask_finance_context,
    build_audit_context,
    build_coach_context,
    normalize_month_arg as normalize_insight_month,
    should_handle_finance_question,
    route_finance_question_mode,
)
from app.nlp.gemini_finance_insight import generate_finance_insight

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
    preview_void_debt,
    preview_void_debts_by_person,
    void_debt,
    void_debt_ids,
    void_debts_by_person,
    void_debts_for_transaction,
    update_debt,
)
import csv
import tempfile
from app.services.recurring_service import (
    add_recurring_rule,
    get_recurring_rules,
    disable_recurring_rule,
    process_due_recurring_rules,
    mark_recurring_rule_paid,
    edit_recurring_rule,
)
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
# Implementation note for this project-specific finance flow.

TELEGRAM_SAFE_MESSAGE_LIMIT = 3800
GEMINI_INTENT_CONFIDENCE_EXECUTE = 0.80
GEMINI_INTENT_CONFIDENCE_CLARIFY = 0.60


def format_rupiah(amount: float) -> str:
    """Format rupiah into readable text."""
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
    if abs(value - round(value)) < 1e-9:
        return f"Rp{int(round(value)):,}".replace(",", ".")

    sign = "-" if value < 0 else ""
    value = abs(value)
    integer_part = int(value)
    decimal_part = (f"{value:.2f}".split(".", 1)[1]).rstrip("0")
    return f"Rp{sign}{integer_part:,}".replace(",", ".") + f",{decimal_part}"


def short_debt_id(debt_id: str) -> str:
    """Helper for short debt id in the Telegram bot flow."""
    debt_id = str(debt_id or "")
    if len(debt_id) <= 18:
        return debt_id
    return debt_id[:18] + "..."


def md_safe(value) -> str:
    """Helper for md safe in the Telegram bot flow."""
    return escape_markdown(str(value or "-"), version=1)


def md_code_text(value) -> str:
    """Helper for md code text in the Telegram bot flow."""
    return str(value or "-").replace("`", "'")


def short_txn_id(txn_id: str) -> str:
    """Helper for short txn id in the Telegram bot flow."""
    txn_id = str(txn_id or "")
    if len(txn_id) <= 18:
        return txn_id
    return txn_id[:18] + "..."




def format_indonesian_date_group_label(date_value) -> str:
    """Format indonesian date group label into readable text."""
    raw = str(date_value or "").strip()
    if not raw or raw.lower() in {"-", "none", "nan", "tanpa tanggal"}:
        return "🗓️ Tanpa tanggal:"

    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", raw)
    if match:
        try:
            dt = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            weekdays = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            months = [
                "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                "Juli", "Agustus", "September", "Oktober", "November", "Desember",
            ]
            return f"🗓️ {weekdays[dt.weekday()]}, {dt.day} {months[dt.month - 1]} {dt.year}:"
        except Exception:
            pass

    return f"🗓️ {raw}:"


def _safe_float_for_display(value, default: float = 0.0) -> float:
    """Helper for safe float for display in the Telegram bot flow."""
    try:
        if isinstance(value, str):
            raw = value.strip().replace("Rp", "").replace("rp", "").replace(" ", "")
            if "." in raw and "," in raw:
                raw = raw.replace(".", "").replace(",", ".")
            elif "," in raw:
                raw = raw.replace(",", ".")
            elif "." in raw:
                parts = raw.split(".")
                if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
                    raw = raw.replace(".", "")
            raw = re.sub(r"[^0-9.-]", "", raw)
            return float(raw or 0)
        return float(value or 0)
    except Exception:
        return default


def get_transaction_receivable_parts(txn: dict) -> list[dict]:
    """Retrieve data needed for transaction receivable parts."""
    parts = (txn or {}).get("debt_receivable_parts") or []
    if parts:
        return [
            {
                "person_name": str((part or {}).get("person_name") or "Tanpa nama").strip(),
                "remaining_amount": _safe_float_for_display((part or {}).get("remaining_amount", 0)),
            }
            for part in parts
            if _safe_float_for_display((part or {}).get("remaining_amount", 0)) > 0
        ]

    # Legacy compatibility note for older records or older in-memory state.
    receivable_by_person = {}
    for debt in (txn or {}).get("linked_debts") or []:
        debt_type = str((debt or {}).get("type", "") or "").strip().lower()
        if debt_type != "receivable":
            continue
        person = str((debt or {}).get("person_name") or "Tanpa nama").strip()
        amount = _safe_float_for_display((debt or {}).get("remaining_amount", 0))
        if amount > 0:
            receivable_by_person[person] = receivable_by_person.get(person, 0.0) + amount

    if receivable_by_person:
        return [
            {"person_name": person, "remaining_amount": amount}
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


def get_transaction_payable_parts(txn: dict) -> list[dict]:
    """Retrieve data needed for transaction payable parts."""
    parts = (txn or {}).get("debt_payable_parts") or []
    if parts:
        return [
            {
                "person_name": str((part or {}).get("person_name") or "Tanpa nama").strip(),
                "remaining_amount": _safe_float_for_display((part or {}).get("remaining_amount", 0)),
            }
            for part in parts
            if _safe_float_for_display((part or {}).get("remaining_amount", 0)) > 0
        ]

    payable_by_person = {}
    for debt in (txn or {}).get("linked_debts") or []:
        debt_type = str((debt or {}).get("type", "") or "").strip().lower()
        if debt_type != "payable":
            continue
        person = str((debt or {}).get("person_name") or "Tanpa nama").strip()
        amount = _safe_float_for_display((debt or {}).get("remaining_amount", 0))
        if amount > 0:
            payable_by_person[person] = payable_by_person.get(person, 0.0) + amount

    return [
        {"person_name": person, "remaining_amount": amount}
        for person, amount in payable_by_person.items()
    ]


def get_net_expense_after_receivable(txn: dict) -> float:
    """Retrieve data needed for net expense after receivable."""
    amount = _safe_float_for_display((txn or {}).get("amount", 0))
    receivable = _safe_float_for_display(
        (txn or {}).get("debt_receivable_original", (txn or {}).get("debt_receivable_remaining", 0))
    )
    return max(amount - receivable, 0.0)


def build_debt_parts_text(parts: list[dict]) -> str:
    """Build the data structure or message text for debt parts text."""
    chunks = []
    for part in parts or []:
        person = md_safe((part or {}).get("person_name") or "Tanpa nama")
        amount = _safe_float_for_display((part or {}).get("remaining_amount", 0))
        if amount <= 0:
            continue
        chunks.append(f"{format_rupiah(amount)} ({person})")
    return ", ".join(chunks)


def has_expense_transactions(transactions: list[dict] | None) -> bool:
    """Check a boolean condition for has expense transactions."""
    return any(
        str((txn or {}).get("type", "") or "").strip().lower() == "expense"
        for txn in (transactions or [])
    )


def has_net_gross_difference(transactions: list[dict] | None) -> bool:
    """Check a boolean condition for has net gross difference."""
    for txn in transactions or []:
        txn_type = str((txn or {}).get("type", "") or "").strip().lower()
        if txn_type != "expense":
            continue
        gross = _safe_float_for_display((txn or {}).get("amount", 0))
        net = get_net_expense_after_receivable(txn)
        if abs(gross - net) > 0.0001:
            return True
    return False


def append_net_gross_note(lines: list[str], transactions: list[dict] | None = None, *, force: bool = False):
    """Append data or text to net gross note."""
    if not force and not has_expense_transactions(transactions):
        return
    lines.append("ℹ️ Catatan: nominal pengeluaran ditampilkan sebagai *Net (Gross)* jika ada piutang split bill terkait.\n")


def format_expense_net_gross(net_amount: float, gross_amount: float, *, always_show_gross: bool = False) -> str:
    """Format expense net gross into readable text."""
    net = _safe_float_for_display(net_amount)
    gross = _safe_float_for_display(gross_amount)
    if always_show_gross or abs(net - gross) > 0.0001:
        return f"{format_rupiah(net)} ({format_rupiah(gross)})"
    return format_rupiah(gross)


def get_transaction_account_text(txn: dict) -> str:
    """Retrieve data needed for transaction account text."""
    txn_type = str((txn or {}).get("type", "") or "").strip().lower()
    source_account = str((txn or {}).get("account", "") or "").strip()
    target_account = str((txn or {}).get("to_account", "") or "").strip()
    if txn_type == "transfer" and target_account:
        return f"{source_account or '-'} → {target_account}"
    return source_account or "-"


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
    else:
        meta.append(f"💰 *{format_rupiah(amount)}*")

    meta.append(category)
    meta.append(f"🏦 {account_text}")
    lines.append(f"   {' | '.join(meta)}")

    receivable_parts = get_transaction_receivable_parts(txn)
    receivable_text = build_debt_parts_text(receivable_parts)
    if txn_type == "expense" and receivable_text:
        lines.append(f"   ↳ 🤝 Piutang aktif: {receivable_text}")

    payable_parts = get_transaction_payable_parts(txn)
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


def build_transactions_full_text_shared(
    transactions: list[dict],
    title: str,
    account_filter: str | None = None,
    *,
    current_balance: float | None = None,
) -> str:
    """Build the data structure or message text for transactions full text shared."""
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

    current_date_group = None
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
            current_date_group = date_group

        lines.extend(build_transaction_display_lines(txn, index=i, include_date=False, include_id=True))

    if account_key:
        net = total_income + total_transfer_in - total_expense - total_transfer_out
        expense_text = format_expense_net_gross(total_net_expense, total_expense)
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
            f"📊 Net Rekening    : *{format_rupiah(net)}*",
            f"📝 Total           : *{len(transactions)} transaksi*",
        ])
        lines.append("\n".join(summary_lines))
    else:
        net = total_income - total_expense
        expense_text = format_expense_net_gross(total_net_expense, total_expense)
        lines.append(
            "\n*Ringkasan:*\n"
            f"✅ Income   : *{format_rupiah(total_income)}*\n"
            f"❌ Expense  : *{expense_text}*\n"
            f"🔄 Transfer : *{format_rupiah(total_transfer)}*\n"
            f"📊 Net      : *{format_rupiah(net)}*\n"
            f"📝 Total    : *{len(transactions)} transaksi*"
        )

    lines.append(
        "\nNomor di atas bisa dipakai untuk koreksi setelah command ini:\n"
        "`/delete_txn 1` atau `/edit_txn 1 amount=15000`"
    )

    return "\n".join(lines)


def is_authorized(update: Update) -> bool:
    """Check a boolean condition for is authorized."""
    if not update.effective_user:
        return False
    return update.effective_user.id == ALLOWED_USER_ID


async def reject_unauthorized(update: Update):
    """Helper for reject unauthorized in the Telegram bot flow."""
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
        try:
            await update.callback_query.answer(
                "⛔ Anda tidak punya akses.",
                show_alert=True,
            )
        except Exception:
            pass
        return


def split_long_message(text: str, max_len: int = TELEGRAM_SAFE_MESSAGE_LIMIT) -> list[str]:
    """Helper for split long message in the Telegram bot flow."""
    text = str(text or "").strip()
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""

    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue

        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= max_len:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(block) <= max_len:
            current = block
            continue

        line_current = ""
        for line in block.splitlines():
            candidate_line = f"{line_current}\n{line}".strip() if line_current else line
            if len(candidate_line) <= max_len:
                line_current = candidate_line
            else:
                if line_current:
                    chunks.append(line_current)
                if len(line) > max_len:
                    for i in range(0, len(line), max_len):
                        chunks.append(line[i:i + max_len])
                    line_current = ""
                else:
                    line_current = line

        if line_current:
            chunks.append(line_current)

    if current:
        chunks.append(current)

    return chunks


async def reply_long_markdown(update: Update, text: str):
    """Send a Telegram response for reply long markdown."""
    for part in split_long_message(text):
        try:
            await update.message.reply_text(part, parse_mode="Markdown")
        except BadRequest:
            await update.message.reply_text(part)


async def reply_message_safely(message, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    """Send a Telegram response for reply message safely."""
    text = str(text or "").strip() or " "
    chunks = split_long_message(text)
    for idx, chunk in enumerate(chunks):
        markup = reply_markup if idx == len(chunks) - 1 else None
        try:
            await message.reply_text(chunk, parse_mode=parse_mode, reply_markup=markup, **kwargs)
        except BadRequest:
            await message.reply_text(chunk, reply_markup=markup, **kwargs)


async def reply_update_safely(update: Update, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    """Send a Telegram response for reply update safely."""
    if update.message:
        await reply_message_safely(update.message, text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)


async def safe_edit_message(query, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    """Helper for safe edit message in the Telegram bot flow."""
    text = str(text or "").strip() or " "
    chunks = split_long_message(text)
    first = chunks[0]

    if len(chunks) > 1:
        suffix = "\n\n📄 *Pesan terlalu panjang, detail lanjutan dikirim di bawah.*"
        max_first_len = TELEGRAM_SAFE_MESSAGE_LIMIT - len(suffix) - 10
        first = first[:max_first_len].rstrip() + suffix

    async def _edit(payload: str, mode: str | None, markup):
        """Helper for edit in the Telegram bot flow."""
        return await query.message.edit_text(
            payload,
            parse_mode=mode,
            reply_markup=markup,
            **kwargs,
        )

    try:
        await _edit(first, parse_mode, reply_markup)
    except BadRequest as exc:
        err = str(exc).lower()
        if "message is not modified" in err:
            pass
        elif "message_too_long" in err or "message is too long" in err or len(first) > 4096:
            safe_first = first[:3500].rstrip() + "\n\n📄 Pesan terlalu panjang, detail lanjutan dikirim di bawah."
            try:
                await _edit(safe_first, None, reply_markup)
            except Exception:
                await query.message.reply_text(safe_first, reply_markup=reply_markup)
        else:
            try:
                await _edit(first, None, reply_markup)
            except BadRequest:
                await query.message.reply_text(first, reply_markup=reply_markup)

    for chunk in chunks[1:]:
        try:
            await query.message.reply_text(chunk, parse_mode=parse_mode)
        except BadRequest:
            await query.message.reply_text(chunk)


async def show_callback_loading(query, text: str = "⏳ *Memproses pilihan...*"):
    """Handle Telegram inline-button callbacks for the Telegram bot flow."""
    try:
        await safe_edit_message(query, text, parse_mode="Markdown")
    except Exception:
        pass


def build_progress_bar(pct: float, length: int = 10) -> str:
    """Build the data structure or message text for progress bar."""
    filled = int(min(float(pct or 0), 100) / 100 * length)
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"


def _parse_human_amount_atom(value: str | None) -> float:
    """Parse input into structured data for the Telegram bot flow."""
    raw = str(value or "").strip().lower()
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


def _safe_eval_amount_expression(expr: str) -> float:
    """Helper for safe eval amount expression in the Telegram bot flow."""
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _eval(node):
        """Helper for eval in the Telegram bot flow."""
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


def parse_human_amount(value: str | None) -> float:
    """Parse input into structured data for the Telegram bot flow."""
    raw = str(value or "").strip().lower()
    if not raw:
        return 0.0

    if re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", raw):
        return _parse_human_amount_atom(raw)

    has_math_operator = bool(re.search(r"[+*/x×:]|(?<=\s)-(?:\s|\d)", raw))
    if has_math_operator:
        token_pattern = re.compile(r"\d+(?:[.,]\d+)?\s*(?:jt|juta|rb|ribu|k)?", re.IGNORECASE)

        def repl(match: re.Match) -> str:
            """Helper for repl in the Telegram bot flow."""
            return str(_parse_human_amount_atom(match.group(0)))

        expr = token_pattern.sub(repl, raw)
        expr = expr.replace("×", "*").replace("x", "*").replace(":", "/")
        expr = re.sub(r"\s+", "", expr)
        if re.fullmatch(r"[0-9.+\-*/()]+", expr):
            try:
                result = _safe_eval_amount_expression(expr)
                if result > 0:
                    return result
            except Exception:
                pass

    return _parse_human_amount_atom(raw)


def parse_amount_text(value: str) -> float:
    """Parse input into structured data for the Telegram bot flow."""
    raw = str(value or "").strip().lower().replace(" ", "").replace(",", ".")
    if not raw:
        return 0

    unit = ""
    for suffix in ["ribu", "rb", "juta", "jt", "miliar", "miliard", "milyard", "k", "m"]:
        if raw.endswith(suffix):
            unit = suffix
            raw = raw[: -len(suffix)]
            break

    try:
        if unit in {"rb", "ribu", "k"}:
            # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
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
    except Exception:
        return 0
    
def extract_split_bill_total_amount(raw_text: str) -> float | None:
    """Extract the important part of the input for split bill total amount."""
    text = str(raw_text or "").strip()
    amount_token = r"(?P<amount>\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m)?)"
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"

    patterns = [
        rf"{amount_token}\s+{split_word}\s*(?:jadi\s*)?\d+",
        rf"{amount_token}\s+{friend_marker}\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{{0,80}}\s+{split_word}\s*(?:jadi\s*)?\d+",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_amount_text(match.group("amount"))

    return None
