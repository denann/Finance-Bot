"""Shared imports for split Telegram handler parts.

Each handler part imports this module with ``from ...common_imports import *``
to avoid copying a long import block while keeping dependencies visible.
"""

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
    SHEET_DEBTS,
    SHEET_DEBT_PAYMENTS,
    WEBHOOK_URL,
    APP_PORT,
)

from app.services.net_worth_service import (
    add_asset,
    add_liability,
    get_assets,
    get_liabilities,
    update_asset,
    update_liability,
    deactivate_asset,
    deactivate_liability,
    calculate_net_worth,
    create_net_worth_snapshot,
    get_net_worth_snapshots,
)

from app.bot.keyboards import account_keyboard, confirm_keyboard
from app.nlp.regex_parser import parse_with_regex, parse_debt_input, detect_date, strip_date_phrases
from app.nlp.gemini_parser import parse_with_pending_fallback
from app.nlp.gemini_image_parser import parse_transactions_from_image
from app.sheets.client import get_all_records, get_spreadsheet
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
    search_transactions,
    parse_report_month_arg,
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
    get_debt_summary,
    get_debt_by_person,
    preview_void_debt,
    void_debt,
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

# ── Cross-part shared helpers ────────────────────────────────────────────────
# These are intentionally defined in common_imports so split handler parts can
# be imported as normal modules without relying on app.bot.handlers globals.

TELEGRAM_SAFE_MESSAGE_LIMIT = 3800
GEMINI_INTENT_CONFIDENCE_EXECUTE = 0.80
GEMINI_INTENT_CONFIDENCE_CLARIFY = 0.60


def format_rupiah(amount: float) -> str:
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")


def md_safe(value) -> str:
    return escape_markdown(str(value or "-"), version=1)


def is_authorized(update: Update) -> bool:
    if not update.effective_user:
        return False
    return update.effective_user.id == ALLOWED_USER_ID


async def reject_unauthorized(update: Update):
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
    for part in split_long_message(text):
        try:
            await update.message.reply_text(part, parse_mode="Markdown")
        except BadRequest:
            await update.message.reply_text(part)


async def reply_message_safely(message, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    text = str(text or "").strip() or " "
    chunks = split_long_message(text)
    for idx, chunk in enumerate(chunks):
        markup = reply_markup if idx == len(chunks) - 1 else None
        try:
            await message.reply_text(chunk, parse_mode=parse_mode, reply_markup=markup, **kwargs)
        except BadRequest:
            await message.reply_text(chunk, reply_markup=markup, **kwargs)


async def reply_update_safely(update: Update, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    if update.message:
        await reply_message_safely(update.message, text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)


async def safe_edit_message(query, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    text = str(text or "").strip() or " "
    chunks = split_long_message(text)
    first = chunks[0]

    if len(chunks) > 1:
        suffix = "\n\n📄 *Pesan terlalu panjang, detail lanjutan dikirim di bawah.*"
        max_first_len = TELEGRAM_SAFE_MESSAGE_LIMIT - len(suffix) - 10
        first = first[:max_first_len].rstrip() + suffix

    async def _edit(payload: str, mode: str | None, markup):
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
    try:
        await safe_edit_message(query, text, parse_mode="Markdown")
    except Exception:
        pass


def build_progress_bar(pct: float, length: int = 10) -> str:
    filled = int(min(float(pct or 0), 100) / 100 * length)
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"


def _parse_human_amount_atom(value: str | None) -> float:
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
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _eval(node):
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
    raw = str(value or "").strip().lower()
    if not raw:
        return 0.0

    if re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", raw):
        return _parse_human_amount_atom(raw)

    has_math_operator = bool(re.search(r"[+*/x×:]|(?<=\s)-(?:\s|\d)", raw))
    if has_math_operator:
        token_pattern = re.compile(r"\d+(?:[.,]\d+)?\s*(?:jt|juta|rb|ribu|k)?", re.IGNORECASE)

        def repl(match: re.Match) -> str:
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
    raw = str(value or "").strip().lower().replace(" ", "")
    multiplier = 1

    if raw.endswith(("rb", "ribu", "k")):
        multiplier = 1_000
        raw = re.sub(r"(rb|ribu|k)$", "", raw)
    elif raw.endswith(("jt", "juta", "m")):
        multiplier = 1_000_000
        raw = re.sub(r"(jt|juta|m)$", "", raw)

    raw = raw.replace(",", ".")

    try:
        return float(raw) * multiplier
    except Exception:
        return 0


def extract_split_bill_total_amount(raw_text: str) -> float | None:
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
