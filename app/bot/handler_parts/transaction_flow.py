"""Preview and state helpers for transaction, mixed input, debt, split bill, pending expense, asset, and edit flows."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *
from app.bot.handler_parts.networth_assets import build_asset_confirm_preview


def parse_input(text: str) -> dict:
    """Parse input into structured data for input."""
    result = parse_with_regex(text)
    if result is not None:
        return result

    return parse_with_pending_fallback(text)


def build_progress_bar(pct: float, length: int = 10) -> str:
    """Build the data structure or message text for progress bar."""
    filled = int(min(float(pct or 0), 100) / 100 * length)
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"


def split_user_inputs(text: str) -> list[str]:
    """Helper for split user inputs in the Telegram bot flow."""
    if not text:
        return []

    raw = text.strip()

    # Debt flow section
    # Debt flow section
    # Debt flow section
    raw = re.sub(r"[\n\r;]+", " ||| ", raw)
    raw = re.sub(r"\s*,\s*", " ||| ", raw)
    raw = re.sub(r"[ \t]+", " ", raw)

    # Starter transaction biasa
    transaction_starters = [
        "beli", "bayar", "byr", "jajan", "makan", "minum",
        "transfer", "top up", "topup", "isi", "ngisi",
        "gaji", "dapat", "dapet", "terima",
        # Debt flow section
        # Debt flow section
        # Debt flow section
        # Debt flow section
        "hutang", "utang",
    ]

    # Debt flow section
    # Implementation note for this project-specific finance flow.
    debt_starters = [
        "minjem", "pinjem", "pinjam",
        "hutang ke", "utang ke",
        "bayar hutang", "bayar utang",
        "saya talangin", "aku talangin", "gw talangin", "gue talangin",
        "saya ditalangin", "aku ditalangin", "gw ditalangin", "gue ditalangin",
        "talangin", "ditalangin", "nitip",
    ]

    all_starters = transaction_starters + debt_starters
    starter_pattern = "|".join(re.escape(k) for k in sorted(all_starters, key=len, reverse=True))

    # Pecah "dan beli", "dan minjem", dst.
    raw = re.sub(
        rf"\s+dan\s+(?=({starter_pattern})\b)",
        " ||| ",
        raw,
        flags=re.IGNORECASE,
    )

    # Debt flow section
    # Debt flow section
    protected_debt_payment = re.search(
        r"\b(bayar|byr|lunasi|lunas|cicil)\s+(hutang|utang)\b",
        raw,
        flags=re.IGNORECASE,
    )

    if protected_debt_payment and "|||" not in raw:
        return [raw.strip(" .,-;")]

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    amount_before_pattern = r"(?:\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)?|\d{4,})"

    raw = re.sub(
        rf"({amount_before_pattern})\s+(?=({starter_pattern})\b)",
        r"\1 ||| ",
        raw,
        flags=re.IGNORECASE,
    )

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Account flow section
    # Account flow section
    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.

    parts = []
    for part in raw.split("|||"):
        clean = part.strip(" .,-;")
        if clean:
            parts.append(clean)

    return parts

def needs_account(parsed: dict) -> bool:
    """Helper for needs account in the Telegram bot flow."""
    txn_type = parsed.get("type")

    if parsed.get("skip_account") and txn_type in ["expense", "income"]:
        return False

    if txn_type in ["expense", "income"] and not parsed.get("account"):
        return True

    if txn_type == "transfer" and (not parsed.get("account") or not parsed.get("to_account")):
        return True

    return False

def is_debt_item(parsed: dict) -> bool:
    """Check whether a condition is true for debt item."""
    return parsed.get("kind") == "debt"


def is_transaction_item(parsed: dict) -> bool:
    """Check whether a condition is true for transaction item."""
    return parsed.get("kind") == "transaction"


def build_mixed_preview(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed preview."""
    lines = [f"🧾 *Ditemukan {len(mixed_items)} item:*\n"]

    total_expense = 0
    total_income = 0
    total_debt = 0

    for i, item in enumerate(mixed_items, 1):
        kind = item["kind"]
        raw = item["raw"]

        if kind == "transaction":
            parsed = item["parsed"]
            txn_type = parsed.get("type")
            amount = float(parsed.get("amount", 0) or 0)

            if txn_type == "expense":
                icon = "❌"
                total_expense += amount
            elif txn_type == "income":
                icon = "✅"
                total_income += amount
            else:
                icon = "🔄"

            desc = md_safe(parsed.get('description') or '-')
            category = md_safe(parsed.get('category') or '-')
            account = md_safe(parsed.get('account') or '-')
            date = md_safe(parsed.get('date') or '-')
            safe_raw = md_safe(raw)
            split_preview = format_split_bill_preview_line(parsed)
            split_line = f"   {md_safe(split_preview)}\n" if split_preview else ""

            lines.append(
                f"{i}. {icon} *Transaksi*\n"
                f"   📝 {desc}\n"
                f"   💰 {format_rupiah(amount)} | {category}\n"
                f"   📅 {date}\n"
                f"   🏦 {account}\n"
                f"{split_line}"
                f"   Input: `{safe_raw}`"
            )

        elif kind == "debt":
            parsed = item["parsed"]
            intent = parsed.get("intent")
            person = parsed.get("person_name") or "-"
            amount = float(parsed.get("amount", 0) or 0)
            total_debt += amount

            if intent == "add_receivable":
                label = "🟢 Piutang Baru"
                effect = "cash out"
            elif intent == "add_payable":
                label = "🔴 Utang Baru"
                effect = "cash in"
            elif intent == "add_payment":
                label = "💸 Pembayaran Debt"
                effect = "mengikuti posisi debt aktif"
            elif intent == "offset_debt":
                label = "🔁 Kompensasi Debt"
                target_label = "piutang" if parsed.get("target_debt_type") == "receivable" else "utang"
                effect = f"potong {target_label}, tanpa rekening"
            else:
                label = "❓ Debt"
                effect = "-"

            safe_person = md_safe(person)
            account = md_safe(parsed.get('account') or '-')
            date = md_safe(parsed.get('date') or parsed.get('transaction_date') or '-')
            safe_raw = md_safe(raw)

            lines.append(
                f"{i}. {label}\n"
                f"   👤 {safe_person}\n"
                f"   💰 {format_rupiah(amount)}\n"
                f"   📅 {date}\n"
                f"   🏦 {account}\n"
                f"   📌 {effect}\n"
                f"   Input: `{safe_raw}`"
            )

    lines.append("\n*Ringkasan awal:*")
    lines.append(f"❌ Transaksi Expense: *{format_rupiah(total_expense)}*")
    lines.append(f"✅ Transaksi Income : *{format_rupiah(total_income)}*")
    lines.append(f"💸 Total Nominal Debt: *{format_rupiah(total_debt)}*")

    account_summary = build_account_delta_summary_from_transaction_items(mixed_items)
    if account_summary:
        lines.append(account_summary)

    return "\n".join(lines)

def parse_income_missing_amount(line: str) -> dict | None:
    """Parse input into structured data for income missing amount."""
    raw = str(line or "").strip()
    if not raw:
        return None

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    without_date = strip_date_phrases(raw)
    if parse_human_amount(without_date) > 0 and re.search(r"\d", without_date):
        return None

    # Account flow section
    low = raw.lower()
    if re.search(r"\bdari\s+[^\n]+?\s+ke\s+", low):
        return None

    match = re.search(
        r"^\s*(?:transaksi|transfer(?:an)?|tf|trf|kiriman|uang)\s+(?:masuk\s+)?dari\s+(.+?)\s*$",
        raw,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    person_raw = match.group(1).strip()
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    person_raw = re.sub(r"\b(?:tgl|tanggal)\s*\d{1,2}(?:[-/]\d{1,2}(?:[-/]\d{2,4})?)?\b", " ", person_raw, flags=re.IGNORECASE)
    person_raw = re.sub(r"\b(?:hari\s+ini|kemarin|besok)\b", " ", person_raw, flags=re.IGNORECASE)
    person = re.sub(r"\s+", " ", person_raw).strip(" .,-;")

    if not person:
        return None

    account_like = {"cash", "bri", "bsi", "bca", "dana", "gopay", "seabank", "sea bank"}
    if person.lower() in account_like:
        return None

    return {
        "type": "income",
        "amount": None,
        "category": "Other Income",
        "account": None,
        "to_account": None,
        "subject": person.title(),
        "description": person.title(),
        "catatan": raw,
        "tipe_pengeluaran": "",
        "date": detect_date(raw),
        "parsed_by": "missing_amount",
        "needs_amount": True,
    }


def build_missing_amount_prompt(raw: str, parsed: dict, current: int | None = None, total: int | None = None) -> str:
    """Build the prompt used when an income input has no nominal yet.

    Args:
        raw: Original user input.
        parsed: Partial parsed transaction.
        current: Current missing amount index for mixed input, if any.
        total: Total missing amount items for mixed input, if any.

    Returns:
        Markdown text asking the user to provide a valid nominal.
    """
    prefix = ""
    if current is not None and total is not None and total > 1:
        prefix = f"🧩 *Nominal kurang {current}/{total}*\n\n"

    desc = md_safe(parsed.get("description") or raw)
    date = md_safe(parsed.get("date") or "-")
    return (
        f"{prefix}🤔 Saya mendeteksi income, tapi nominalnya belum ada.\n\n"
        f"📝 Item: *{desc}*\n"
        f"📅 Tanggal: *{date}*\n"
        f"📌 Input: `{md_safe(raw)}`\n\n"
        "Nominalnya berapa? Contoh: `13k`, `50000`, atau `94k/2`."
    )


def finalize_missing_amount_item(item: dict, amount: float) -> dict:
    """Attach a user-provided nominal to a partial transaction item.

    Args:
        item: Pending item stored from the missing amount flow.
        amount: Parsed nominal from the user's follow-up message.

    Returns:
        Normalized transaction item ready to continue through the preview flow.
    """
    parsed = dict(item.get("parsed") or {})
    parsed["amount"] = amount
    parsed.pop("needs_amount", None)
    parsed["parsed_by"] = parsed.get("parsed_by") or "missing_amount"
    return {
        "kind": "transaction",
        "parsed": parsed,
        "raw": item.get("raw") or parsed.get("catatan") or "",
    }


async def continue_after_missing_amount_mixed(update: Update, context: ContextTypes.DEFAULT_TYPE, mixed_items: list[dict]) -> None:
    """Continue the mixed flow after all missing nominals are filled.

    Args:
        update: Telegram update used to reply to the user.
        context: Telegram context where pending mixed state is stored.
        mixed_items: Mixed items after missing nominal values are completed.

    Notes:
        This function updates `context.user_data` and sends the next Telegram
        prompt. It does not save transactions.
    """
    context.user_data["pending_mixed"] = mixed_items
    context.user_data.pop("pending_parsed", None)
    context.user_data.pop("pending_raw", None)
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt", None)
    context.user_data.pop("pending_debt_batch", None)
    context.user_data.pop("mixed_review_preview_sent", None)

    preview = build_mixed_preview(mixed_items)

    if mixed_split_bill_needs_decision(mixed_items):
        await reply_update_safely(
            update,
            build_mixed_split_bill_queue_prompt(mixed_items),
            parse_mode="Markdown",
            reply_markup=mixed_split_bill_keyboard(mixed_items),
        )
    elif mixed_needs_account(mixed_items):
        await reply_update_safely(
            update,
            build_mixed_account_prompt(mixed_items),
            parse_mode="Markdown",
            reply_markup=account_keyboard("mixed_acc"),
        )
    else:
        await reply_update_safely(
            update,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", True),
        )


async def handle_pending_missing_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Handle the user's answer for a pending missing nominal question.

    Args:
        update: Telegram update that contains the follow-up message.
        context: Telegram context where `pending_missing_amount` is stored.
        user_text: User's answer, expected to contain a nominal.

    Returns:
        True when this function consumes the message, otherwise False.

    Notes:
        The function may update pending transaction state and send the next
        prompt. It does not save the transaction.
    """
    state = context.user_data.get("pending_missing_amount")
    if not state:
        return False

    amount = parse_human_amount(user_text)
    if not amount or amount <= 0:
        await update.message.reply_text(
            "❌ Nominalnya belum kebaca. Coba tulis seperti `13k`, `50000`, atau `94k/2`.",
            parse_mode="Markdown",
        )
        return True

    scope = state.get("scope")
    if scope == "mixed":
        mixed_items = state.get("mixed_items") or []
        missing_indices = state.get("missing_indices") or []
        current = int(state.get("current") or 0)

        if current >= len(missing_indices):
            context.user_data.pop("pending_missing_amount", None)
            await update.message.reply_text("❌ Tidak ada input kurang nominal yang sedang menunggu jawaban.")
            return True

        idx = missing_indices[current]
        if 0 <= idx < len(mixed_items):
            mixed_items[idx] = finalize_missing_amount_item(mixed_items[idx], amount)

        current += 1
        if current < len(missing_indices):
            state["mixed_items"] = mixed_items
            state["current"] = current
            context.user_data["pending_missing_amount"] = state
            next_idx = missing_indices[current]
            next_item = mixed_items[next_idx]
            await update.message.reply_text(
                build_missing_amount_prompt(next_item.get("raw", ""), next_item.get("parsed", {}), current + 1, len(missing_indices)),
                parse_mode="Markdown",
            )
            return True

        context.user_data.pop("pending_missing_amount", None)
        await continue_after_missing_amount_mixed(update, context, mixed_items)
        return True

    if scope == "single":
        item = state.get("item") or {}
        finalized = finalize_missing_amount_item(item, amount)
        parsed = finalized["parsed"]
        context.user_data["pending_parsed"] = parsed
        context.user_data["pending_raw"] = finalized.get("raw") or user_text
        context.user_data.pop("pending_missing_amount", None)
        context.user_data.pop("pending_batch", None)
        context.user_data.pop("pending_debt", None)
        context.user_data.pop("pending_debt_batch", None)
        context.user_data.pop("pending_mixed", None)

        if needs_account(parsed):
            await reply_update_safely(
                update,
                build_single_account_prompt(parsed),
                parse_mode="Markdown",
                reply_markup=account_keyboard("acc"),
            )
            return True

        preview = build_preview(parsed)
        await reply_update_safely(
            update,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("single", True),
        )
        return True

    context.user_data.pop("pending_missing_amount", None)
    return False


def parse_mixed_item(line: str) -> dict:
    """Parse input into structured data for mixed item."""
    debt_parsed = parse_debt_input(line)
    if debt_parsed:
        debt_parsed = enrich_ditalangin_split_bill_if_any(debt_parsed, line)
        return {
            "kind": "debt",
            "parsed": debt_parsed,
            "raw": line,
        }

    missing_amount_income = parse_income_missing_amount(line)
    if missing_amount_income:
        return {
            "kind": "missing_amount",
            "parsed": missing_amount_income,
            "raw": line,
        }

    txn_parsed = parse_input(line)
    if txn_parsed and txn_parsed.get("type") != "pending":
        attach_split_bill_if_any(txn_parsed, line)
        return {
            "kind": "transaction",
            "parsed": txn_parsed,
            "raw": line,
        }

    return {
        "kind": "failed",
        "parsed": {},
        "raw": line,
    }

def mixed_needs_account(mixed_items: list[dict]) -> bool:
    """Check whether a mixed input still needs a rekening selection.

    Args:
        mixed_items: Parsed mixed items from one user input. Each item may be a
            normal transaction or a debt-related item.

    Returns:
        True if at least one cashflow item has no rekening yet, otherwise False.
    """
    for item in mixed_items:
        parsed = item["parsed"]

        if item["kind"] == "transaction" and needs_account(parsed):
            return True

        if item["kind"] == "debt" and debt_uses_cashflow(parsed) and not parsed.get("account"):
            return True

    return False


def edit_or_continue_keyboard(scope: str) -> InlineKeyboardMarkup:
    """Build the fallback preview keyboard before the next required decision.

    Args:
        scope: Flow scope used in the callback route, for example `single`,
            `mixed`, or `debt`.

    Returns:
        Inline keyboard that lets the user edit the preview, continue the flow,
        or cancel the current session.

    Notes:
        This keyboard is kept as a fallback for flows that still need a manual
        continue step. Missing rekening flows should route directly to the
        rekening picker instead of showing this keyboard first.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Edit dulu", callback_data=f"editflow:edit:{scope}"),
            InlineKeyboardButton("➡️ Lanjut", callback_data=f"editflow:continue:{scope}"),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")],
    ])


def _confirm_target_for_edit_scope(scope: str) -> str:
    """Map a preview edit scope to the confirm callback target.

    Args:
        scope: Current preview scope. The `single` scope is stored as
            `pending_parsed`, but its save callback still uses `confirm:pending`.

    Returns:
        Callback target used by the save button.
    """
    return "pending" if scope == "single" else scope


def save_edit_cancel_keyboard(scope: str) -> InlineKeyboardMarkup:
    """Build the final action keyboard for data that is ready to save.

    Args:
        scope: Flow scope used to route save, edit, and cancel callbacks.

    Returns:
        Inline keyboard with Simpan, Edit dulu, and Batal actions.

    Notes:
        This function only builds callback buttons. It does not save data or
        change balances by itself.
    """
    confirm_target = _confirm_target_for_edit_scope(scope)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Simpan", callback_data=f"confirm:{confirm_target}"),
            InlineKeyboardButton("✏️ Edit dulu", callback_data=f"editflow:edit:{scope}"),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")],
    ])


def preview_action_keyboard(scope: str, ready_to_save: bool) -> InlineKeyboardMarkup:
    """Choose the right preview action keyboard for the current validation state.

    Args:
        scope: Flow scope used in callback data.
        ready_to_save: Whether the current preview already has all required
            decisions, such as split bill status and rekening.

    Returns:
        Final save/edit/cancel keyboard when ready, otherwise the fallback
        edit/continue/cancel keyboard.
    """
    return save_edit_cancel_keyboard(scope) if ready_to_save else edit_or_continue_keyboard(scope)


def preview_action_question(ready_to_save: bool) -> str:
    """Return the short question shown below a preview.

    Args:
        ready_to_save: Whether the preview can be saved immediately.

    Returns:
        User-facing question for the current preview state.
    """
    if ready_to_save:
        return "Mau simpan, edit dulu, atau batal?"
    return "Mau edit dulu atau lanjut ke rekening/simpan?"


def single_ready_to_save(parsed: dict) -> bool:
    """Check whether a single transaction preview can be saved.

    Args:
        parsed: Parsed transaction candidate.

    Returns:
        True when the transaction no longer needs split bill or rekening
        decisions.
    """
    return not split_bill_needs_decision(parsed) and not needs_account(parsed)


def mixed_ready_to_save(mixed_items: list[dict]) -> bool:
    """Check whether a mixed input preview can be saved.

    Args:
        mixed_items: Parsed items from a multi-line or mixed natural input.

    Returns:
        True when every item has completed the required split bill and rekening
        decisions.
    """
    return not mixed_split_bill_needs_decision(mixed_items) and not mixed_needs_account(mixed_items)


def debt_ready_to_save(debt_parsed: dict) -> bool:
    """Check whether a debt preview can be saved without another decision.

    Args:
        debt_parsed: Parsed debt candidate.

    Returns:
        True when the debt flow does not need a rekening selection before save.

    Notes:
        Debt offset does not use a rekening, while debt cashflow items still
        need one unless they are marked as historical.
    """
    intent = (debt_parsed or {}).get("intent")
    return not (debt_uses_cashflow(debt_parsed or {}) and intent != "offset_debt" and not (debt_parsed or {}).get("account"))


def build_parse_safety_notice(assessment: dict, mode: str = "warning") -> str:
    """Build the data structure or message text for parse safety notice."""
    reasons = [str(r).strip() for r in (assessment or {}).get("reasons", []) if str(r).strip()]

    if mode == "gemini":
        lines = ["🤖 *Saya pakai Gemini untuk bantu menafsirkan input ini, tapi tetap perlu dicek.*"]
    else:
        lines = ["⚠️ *Saya agak ragu dengan hasil parsing ini.*"]

    if reasons:
        lines.append("\n*Alasan:*")
        for reason in reasons[:4]:
            lines.append(f"• {md_safe(reason)}")

    return "\n".join(lines)


def build_preview_with_parse_safety(parsed: dict, assessment: dict, mode: str = "warning") -> str:
    """Build the data structure or message text for preview with parse safety."""
    return f"{build_parse_safety_notice(assessment, mode)}\n\n{build_preview(parsed)}"


def build_pending_expense_confirm_preview(item: dict, include_question: bool = True) -> str:
    """Build the data structure or message text for pending expense confirm preview."""
    item = dict(item or {})
    due_date = str(item.get("due_date") or "").strip()
    due_precision = str(item.get("due_precision") or "unknown").strip().lower()
    month = str(item.get("month") or "-").strip()
    if due_date:
        due_text = due_date
    elif due_precision == "month":
        due_text = f"{month} (tanggal belum pasti)"
    else:
        due_text = "Belum pasti"

    account = str(item.get("account") or "-").strip() or "-"
    category = str(item.get("category") or "Other Expense").strip()
    status = str(item.get("status") or "pending").strip()
    subject = str(item.get("subject") or item.get("description") or "Pending Expense").strip()
    description = str(item.get("description") or subject).strip()
    amount = float(item.get("amount", 0) or 0)

    lines = [
        "🕒 *Preview Pending Expense*\n",
        f"📝 *{md_safe(subject)}*",
        f"📄 Deskripsi: {md_safe(description)}",
        f"📅 Jatuh tempo: *{md_safe(due_text)}*",
        f"💰 Nominal: *{format_rupiah(amount)}*",
        f"🏷️ Kategori: *{md_safe(category)}*",
        f"🏦 Rekening rencana: *{md_safe(account)}*",
        f"Status: `{md_safe(status)}`",
        "\nCatatan: pending expense tidak mengubah saldo dan belum masuk pengeluaran aktual.",
    ]
    if include_question:
        lines.append("Simpan pending expense ini?")
    return "\n".join(lines)


def parse_clarification_keyboard() -> InlineKeyboardMarkup:
    """Parse input into structured data for clarification keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ Debt payment", callback_data="clarify_parse:debt_payment")],
        [InlineKeyboardButton("2️⃣ Expense saya", callback_data="clarify_parse:expense")],
        [InlineKeyboardButton("3️⃣ No cashflow", callback_data="clarify_parse:no_cashflow")],
        [InlineKeyboardButton("4️⃣ Saya talangin", callback_data="clarify_parse:fronting")],
        [InlineKeyboardButton("5️⃣ Tulis ulang", callback_data="clarify_parse:rewrite")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:clarification")],
    ])


def build_parse_clarification_prompt(raw: str, assessment: dict | None = None) -> str:
    """Build the data structure or message text for parse clarification prompt."""
    safe_raw = md_safe(raw)
    lines = [
        "🤔 *Saya belum yakin maksud input ini:*",
        "",
        f'"{safe_raw}"',
    ]

    reasons = [str(r).strip() for r in (assessment or {}).get("reasons", []) if str(r).strip()]
    if reasons:
        lines.append("\n*Kenapa ditanya dulu:*")
        for reason in reasons[:3]:
            lines.append(f"• {md_safe(reason)}")

    lines.extend([
        "",
        "Maksudnya yang mana?",
        "1. Budi/orang ini bayar hutang/piutang ke saya",
        "2. Saya mencatat pengeluaran biasa",
        "3. Orang lain yang membayar, tidak perlu mengubah saldo saya",
        "4. Saya talangin orang ini",
        "5. Saya tulis ulang inputnya",
    ])
    return "\n".join(lines)


def parse_participant_count(value: str) -> int | None:
    """Parse input into structured data for participant count."""
    clean = str(value or "").strip().lower()
    mapping = {
        "dua": 2, "2": 2, "berdua": 2,
        "tiga": 3, "3": 3, "bertiga": 3,
        "empat": 4, "4": 4, "berempat": 4,
        "lima": 5, "5": 5, "berlima": 5,
        "enam": 6, "6": 6, "berenam": 6,
        "tujuh": 7, "7": 7,
        "delapan": 8, "8": 8,
        "sembilan": 9, "9": 9,
        "sepuluh": 10, "10": 10,
    }
    if clean in mapping:
        return mapping[clean]
    try:
        value_int = int(clean)
        return value_int if value_int > 0 else None
    except Exception:
        return None


def build_account_delta_summary_from_transaction_items(items: list[dict]) -> str:
    """Build the data structure or message text for account delta summary from transaction items."""
    transaction_items = []
    for item in items or []:
        parsed = item.get("parsed", item) if isinstance(item, dict) else {}
        if isinstance(parsed, dict) and parsed.get("type") in ["expense", "income", "transfer"]:
            transaction_items.append({"parsed": parsed})

    deltas = calculate_account_deltas(transaction_items)
    if not deltas:
        return ""

    lines = ["\n💳 *Ringkasan per rekening:*"]
    for account_name, delta in deltas.items():
        sign = "+" if float(delta or 0) >= 0 else "-"
        lines.append(f"• {md_safe(account_name)}: {sign}{format_rupiah(abs(float(delta or 0)))}")
    return "\n".join(lines)


def build_mixed_short_summary(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed short summary."""
    total_expense = 0.0
    total_income = 0.0
    total_transfer = 0.0
    total_debt = 0.0
    transaction_count = 0
    debt_count = 0

    for item in mixed_items or []:
        kind = item.get("kind")
        parsed = item.get("parsed", {}) or {}
        amount = float(parsed.get("amount", 0) or 0)
        if kind == "transaction":
            transaction_count += 1
            txn_type = parsed.get("type")
            if txn_type == "expense":
                total_expense += amount
            elif txn_type == "income":
                total_income += amount
            elif txn_type == "transfer":
                total_transfer += amount
        elif kind == "debt":
            debt_count += 1
            total_debt += amount

    lines = ["🧾 *Ringkasan batch:*"]
    lines.append(f"• Total item: *{len(mixed_items or [])}*")
    if transaction_count:
        lines.append(f"• Transaksi: *{transaction_count} item*")
    if total_expense:
        lines.append(f"• Expense: *{format_rupiah(total_expense)}*")
    if total_income:
        lines.append(f"• Income: *{format_rupiah(total_income)}*")
    if total_transfer:
        lines.append(f"• Transfer: *{format_rupiah(total_transfer)}*")
    if debt_count:
        lines.append(f"• Debt: *{debt_count} item* / {format_rupiah(total_debt)}")

    account_summary = build_account_delta_summary_from_transaction_items(mixed_items)
    if account_summary:
        lines.append(account_summary)

    return "\n".join(lines)


def build_single_short_summary(parsed: dict) -> str:
    """Build the data structure or message text for single short summary."""
    if not isinstance(parsed, dict):
        return "🧾 *Ringkasan transaksi:* -"

    txn_type = parsed.get("type") or "transaction"
    description = md_safe(parsed.get("description") or parsed.get("subject") or "Transaksi")
    amount = float(parsed.get("amount", 0) or 0)
    category = md_safe(parsed.get("category") or "-")
    account = md_safe(parsed.get("account") or "-")

    lines = ["🧾 *Ringkasan transaksi:*"]
    lines.append(f"• Jenis: *{md_safe(txn_type)}*")
    lines.append(f"• Item: *{description}*")
    lines.append(f"• Nominal: *{format_rupiah(amount)}*")
    if category != "-":
        lines.append(f"• Kategori: *{category}*")
    if account != "-":
        lines.append(f"• Rekening: *{account}*")

    account_summary = build_account_delta_summary_from_transaction_items([{"parsed": parsed}])
    if account_summary:
        lines.append(account_summary)

    return "\n".join(lines)


def build_single_account_prompt(parsed: dict, preview_text: str | None = None) -> str:
    """Build the rekening selection prompt for a single transaction.

    Args:
        parsed: Parsed transaction that still needs an account decision.
        preview_text: Optional preview text to keep warnings or Gemini draft
            notices visible before asking for rekening.

    Returns:
        Markdown text containing the transaction summary and rekening question.

    Notes:
        This function only formats the prompt. The selected rekening is applied
        later by the `acc:*` callback route.
    """
    summary = preview_text or build_single_short_summary(parsed)
    return (
        f"{summary}\n\n"
        "💳 Dari rekening mana?\n"
        "Atau pilih *Sudah berlalu* jika transaksi hanya catatan historis dan tidak mau mengubah saldo."
    )


def build_mixed_account_prompt(mixed_items: list[dict]) -> str:
    """Build the rekening selection prompt for mixed input.

    Args:
        mixed_items: Parsed mixed items that may contain transactions and debt
            items.

    Returns:
        Markdown text with a compact mixed summary and rekening question.

    Notes:
        The selected rekening is applied only to cashflow items that still have
        no rekening. Items that already have a rekening are left unchanged.
    """
    return (
        f"{build_mixed_short_summary(mixed_items)}\n\n"
        "💳 Pilih rekening untuk item yang belum punya rekening, atau pilih "
        "*Sudah berlalu* jika tidak mau mengubah saldo:"
    )


def build_updated_item_summary(item: dict, index: int | None = None) -> str:
    """Build the data structure or message text for updated item summary."""
    prefix = f"Item {index}" if index else "Item"
    kind = item.get("kind") if isinstance(item, dict) else None
    parsed = item.get("parsed", {}) if isinstance(item, dict) else {}

    if kind == "transaction":
        label = md_safe(parsed.get("description") or parsed.get("subject") or "Transaksi")
        amount = float(parsed.get("amount", 0) or 0)
        category = md_safe(parsed.get("category") or "-")
        account = md_safe(parsed.get("account") or "-")
        return (
            f"✅ *{prefix} sudah diupdate.*\n"
            f"• {label}\n"
            f"• {format_rupiah(amount)} | {category}\n"
            f"• Rekening: {account}"
        )

    if kind == "debt":
        person = md_safe(parsed.get("person_name") or "-")
        amount = float(parsed.get("amount", 0) or 0)
        account = md_safe(parsed.get("account") or "-")
        return (
            f"✅ *{prefix} debt sudah diupdate.*\n"
            f"• {person}\n"
            f"• {format_rupiah(amount)}\n"
            f"• Rekening: {account}"
        )

    return f"✅ *{prefix} sudah diupdate.*"


def _preview_edit_fields_for_scope(scope: str) -> list[tuple[str, str]]:
    """Helper for preview edit fields for scope in the Telegram bot flow."""
    if scope == "pending_expense":
        return [
            ("💰 Nominal", "amount"),
            ("📁 Kategori", "category"),
            ("👤 Subjek", "subject"),
            ("📝 Deskripsi", "description"),
            ("🏦 Rekening", "account"),
            ("📅 Tanggal", "due_date"),
            ("🗓️ Bulan", "month"),
        ]

    if scope == "asset":
        return [
            ("🏷️ Nama", "name"),
            ("💰 Nominal", "amount"),
            ("📁 Kategori", "category"),
            ("📝 Deskripsi", "description"),
            ("🔢 Jumlah", "quantity"),
            ("📏 Unit", "unit"),
            ("🏷️ Harga/unit", "price_per_unit"),
            ("📅 Tanggal beli", "purchase_date"),
        ]

    if scope == "debt":
        return [
            ("💰 Nominal", "amount"),
            ("👤 Orang", "person_name"),
            ("📝 Deskripsi", "description"),
            ("🏦 Rekening", "account"),
            ("📅 Tanggal", "date"),
        ]

    return [
        ("💰 Nominal", "amount"),
        ("📁 Kategori", "category"),
        ("👤 Subjek", "subject"),
        ("📝 Deskripsi", "description"),
        ("🏦 Rekening", "account"),
        ("🔁 Tipe", "type"),
        ("📅 Tanggal", "date"),
        ("🗒️ Catatan", "catatan"),
    ]


def build_preview_edit_keyboard(scope: str = "single") -> InlineKeyboardMarkup:
    """Build the data structure or message text for preview edit keyboard."""
    fields = _preview_edit_fields_for_scope(scope)
    rows = []
    for i in range(0, len(fields), 2):
        row = []
        for label, field in fields[i:i + 2]:
            row.append(InlineKeyboardButton(label, callback_data=f"editflow:field:{scope}:{field}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")])
    return InlineKeyboardMarkup(rows)


def build_preview_field_help(scope: str, field: str) -> str:
    """Build the data structure or message text for preview field help."""
    examples = {
        "amount": ("Nominal", "`nominal: 20000` atau `nominal 20k`"),
        "category": ("Kategori", "`kategori: Other Expense`"),
        "description": ("Deskripsi", "`deskripsi: Kopi susu`"),
        "subject": ("Subjek", "`subjek: Mie Goreng`"),
        "person_name": ("Orang", "`orang: Budi`"),
        "type": ("Tipe transaksi", "`tipe: expense`, `tipe: income`, atau `tipe: transfer`"),
        "date": ("Tanggal", "`tanggal: 2026-07-02`"),
        "due_date": ("Tanggal jatuh tempo", "`tanggal: 2026-07-30`"),
        "month": ("Bulan", "`bulan: 2026-07`"),
        "account": ("Rekening", "`rekening: DANA`"),
        "to_account": ("Rekening tujuan", "`to_account: BCA`"),
        "catatan": ("Catatan", "`catatan: sudah dicek manual`"),
        "name": ("Nama", "`nama: Laptop kerja`"),
        "quantity": ("Jumlah unit", "`jumlah: 41`"),
        "unit": ("Satuan", "`unit: gram`"),
        "price_per_unit": ("Harga per unit", "`harga_satuan: 2594000`"),
        "purchase_price_per_unit": ("Harga beli per unit", "`harga_beli: 2559000`"),
        "purchase_date": ("Tanggal beli", "`tanggal_beli: 2026-06-10`"),
    }
    title, example = examples.get(field, (field.replace("_", " ").title(), f"`{field}: nilai baru`"))
    return (
        f"✏️ *Edit {md_safe(title)}*\n\n"
        f"Ketik nilai barunya dengan format:\n{example}\n\n"
        "Kamu juga bisa edit banyak field sekaligus, contoh:\n"
        "`nominal: 20k, kategori: Other Expense, rekening: DANA`"
    )


def build_preview_edit_help(scope: str = "single") -> str:
    """Build the data structure or message text for preview edit help."""
    if scope == "pending_expense":
        fields = "nominal, kategori, subjek, deskripsi, rekening, tanggal, bulan"
        examples = (
            "`nominal: 285k, kategori: Bills & Utilities, rekening: BRI`\n"
            "`deskripsi: Wifi rumah, tanggal: 2026-07-30`"
        )
    elif scope == "asset":
        fields = "nama, nominal, kategori, deskripsi, jumlah, unit, harga_satuan, harga_beli, tanggal_beli"
        examples = (
            "`nama: Laptop kerja, nominal: 8jt, kategori: Electronics`\n"
            "`jumlah: 41, unit: gram, harga_satuan: 2594000`"
        )
    elif scope == "debt":
        fields = "nominal, orang, deskripsi, rekening, tanggal"
        examples = (
            "`nominal: 50k, orang: Budi, rekening: DANA`\n"
            "`deskripsi: Talang makan, tanggal: 2026-07-02`"
        )
    else:
        fields = "nominal, kategori, deskripsi, subjek, tipe, tanggal, rekening, catatan"
        examples = (
            "`nominal: 20k, kategori: Other Expense, rekening: DANA`\n"
            "`deskripsi: Mie Goreng, tanggal: 2026-07-02`"
        )

    item_hint = "" if scope == "single" else "\nKamu sedang mengedit item yang dipilih."
    return (
        "✏️ *Mau edit apa?*" + item_hint + "\n\n"
        "Kamu bisa pilih tombol field di bawah, atau langsung ketik manual.\n\n"
        f"Field yang umum diedit: {md_safe(fields)}.\n\n"
        "Format manual bisa satu field:\n"
        "`nominal 20k`\n"
        "`kategori Other Expense`\n"
        "`rekening DANA`\n\n"
        "Bisa juga multi edit sekaligus pakai koma, titik koma, atau baris baru:\n"
        f"{examples}\n\n"
        "Format `field=value` juga tetap bisa, contoh `category=Food & Beverage`."
    )


def build_mixed_edit_choose_prompt(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed edit choose prompt."""
    lines = ["✏️ *Mau edit item nomor berapa?*\n"]
    for i, item in enumerate(mixed_items or [], 1):
        kind = item.get("kind")
        parsed = item.get("parsed", {})
        if kind == "transaction":
            label = parsed.get("description") or parsed.get("subject") or item.get("raw", "-")
            amount = parsed.get("amount", 0)
            lines.append(f"{i}. {md_safe(label)} — {format_rupiah(float(amount or 0))}")
        elif kind == "debt":
            label = parsed.get("person_name") or item.get("raw", "-")
            amount = parsed.get("amount", 0)
            lines.append(f"{i}. Debt {md_safe(label)} — {format_rupiah(float(amount or 0))}")
        else:
            lines.append(f"{i}. {md_safe(item.get('raw', '-'))}")
    lines.append("\nBalas dengan angka, contoh: `2`.")
    return "\n".join(lines)


PREVIEW_EDIT_KEY_ALIASES = {
    "amount": "amount", "nominal": "amount", "jumlah": "amount",
    "category": "category", "kategori": "category",
    "description": "description", "desc": "description", "deskripsi": "description",
    "subject": "subject", "subjek": "subject",
    "person": "person_name", "person_name": "person_name", "orang": "person_name", "teman": "person_name", "nama_orang": "person_name",
    "type": "type", "tipe": "type", "jenis": "type",
    "date": "date", "tanggal": "date", "tgl": "date",
    "account": "account", "rekening": "account", "akun": "account",
    "to_account": "to_account", "ke_rekening": "to_account", "rekening_tujuan": "to_account",
    "catatan": "catatan", "note": "catatan",
    "tipe_pengeluaran": "tipe_pengeluaran", "pengeluaran": "tipe_pengeluaran",
    "due_date": "due_date", "tanggal_jatuh_tempo": "due_date", "jatuh_tempo": "due_date", "tenggat": "due_date",
    "month": "month", "bulan": "month",
    "name": "name", "nama": "name",
    "quantity": "quantity", "jumlah_unit": "quantity", "jumlah_aset": "quantity",
    "unit": "unit", "satuan": "unit",
    "price_per_unit": "price_per_unit", "harga_satuan": "price_per_unit", "harga_sekarang": "price_per_unit",
    "purchase_price_per_unit": "purchase_price_per_unit", "harga_beli": "purchase_price_per_unit", "modal": "purchase_price_per_unit",
    "purchase_date": "purchase_date", "tanggal_beli": "purchase_date",
    "asset_type": "asset_type", "tipe_aset": "asset_type",
}


def _split_preview_edit_segments(raw: str) -> list[str]:
    """Helper for split preview edit segments in the Telegram bot flow."""
    segments: list[str] = []
    buffer: list[str] = []
    quote_char = ""

    for char in str(raw or ""):
        if char in {"'", '"'}:
            if quote_char == char:
                quote_char = ""
            elif not quote_char:
                quote_char = char
            buffer.append(char)
            continue

        if char in {",", ";", "\n", "\r"} and not quote_char:
            part = "".join(buffer).strip()
            if part:
                segments.append(part)
            buffer = []
            continue

        buffer.append(char)

    last = "".join(buffer).strip()
    if last:
        segments.append(last)
    return segments


def _strip_preview_edit_value(value: str) -> str:
    """Helper for strip preview edit value in the Telegram bot flow."""
    clean = str(value or "").strip()
    if len(clean) >= 2 and clean[0] == clean[-1] and clean[0] in {"'", '"'}:
        return clean[1:-1].strip()
    return clean


def _parse_preview_edit_pair(segment: str) -> dict:
    """Parse input into structured data for preview edit pair."""
    raw = str(segment or "").strip()
    if not raw:
        return {}

    key_pattern = "|".join(re.escape(k) for k in sorted(PREVIEW_EDIT_KEY_ALIASES, key=len, reverse=True))
    match = re.match(
        rf"^({key_pattern})\s*(?:=|:)\s*(.+)$",
        raw,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.match(
            rf"^({key_pattern})\s+(.+)$",
            raw,
            flags=re.IGNORECASE,
        )
    if not match:
        return {}

    key = PREVIEW_EDIT_KEY_ALIASES.get(match.group(1).lower())
    value = _strip_preview_edit_value(match.group(2))
    if not key or value == "":
        return {}

    updates: dict = {}
    if key in {"amount", "quantity", "price_per_unit", "purchase_price_per_unit"}:
        amount = parse_human_amount(value)
        if amount <= 0:
            return {}
        updates[key] = amount
    elif key == "type":
        normalized = value.lower().strip()
        type_aliases = {
            "income": "income", "pemasukan": "income", "masuk": "income",
            "expense": "expense", "pengeluaran": "expense", "keluar": "expense",
            "transfer": "transfer",
        }
        if normalized not in type_aliases:
            return {}
        updates[key] = type_aliases[normalized]
    elif key in {"date", "due_date", "purchase_date"}:
        from app.nlp.regex_parser import parse_explicit_date
        parsed_date = parse_explicit_date(value) or value
        updates[key] = parsed_date
    elif key == "month":
        updates[key] = value.strip()
    elif key in ["account", "to_account"]:
        value_clean = value.strip()
        updates[key] = value_clean.upper() if value_clean.lower() in ["bca", "bri", "bsi", "dana"] else value_clean.title()
    else:
        updates[key] = value.strip()

    return updates


def parse_preview_edit_updates(text: str) -> dict:
    """Parse input into structured data for preview edit updates."""
    raw = str(text or "").strip()
    if not raw:
        return {}

    segments = _split_preview_edit_segments(raw)
    if not segments:
        return {}

    updates: dict = {}
    for segment in segments:
        parsed_segment = _parse_preview_edit_pair(segment)
        if not parsed_segment:
            if len(segments) == 1:
                return {}
            continue
        updates.update(parsed_segment)

    return updates


def apply_preview_edit_updates_to_parsed(parsed: dict, updates: dict) -> dict:
    """Apply changes for preview edit updates to parsed."""
    if not isinstance(parsed, dict):
        return parsed

    parsed.update(updates)

    txn_type = parsed.get("type")
    if "type" in updates:
        if txn_type == "income" and (not parsed.get("category") or parsed.get("category") == "Other Expense"):
            parsed["category"] = "Other Income"
            parsed["tipe_pengeluaran"] = ""
        elif txn_type == "expense" and (not parsed.get("category") or parsed.get("category") == "Other Income"):
            parsed["category"] = "Other Expense"

    if "description" in updates and (not parsed.get("subject") or parsed.get("subject") in ["Pemasukan", "Transaksi"]):
        parsed["subject"] = updates["description"]

    return parsed


async def proceed_after_preview_edit(query, context: ContextTypes.DEFAULT_TYPE, scope: str):
    """Continue a pending preview after the user taps `Lanjut`.

    Args:
        query: Telegram callback query from the inline button.
        context: Telegram context that stores the pending preview state.
        scope: Current flow scope, such as `single`, `mixed`, `debt`,
            `pending_expense`, or `asset`.

    Notes:
        This function decides the next required step. If rekening is still
        missing, it routes directly to the rekening picker. It does not save
        data unless a later confirmation callback is triggered.
    """
    context.user_data.pop("pending_preview_edit", None)

    if scope == "mixed":
        mixed_items = context.user_data.get("pending_mixed")
        if not mixed_items:
            await safe_edit_message(query, "❌ Sesi mixed input expired. Coba input ulang.")
            return

        if mixed_split_bill_needs_decision(mixed_items):
            await safe_edit_message(query, 
                build_mixed_split_bill_queue_prompt(mixed_items),
                parse_mode="Markdown",
                reply_markup=mixed_split_bill_keyboard(mixed_items),
            )
            return

        if mixed_needs_account(mixed_items):
            await safe_edit_message(
                query,
                build_mixed_account_prompt(mixed_items),
                parse_mode="Markdown",
                reply_markup=account_keyboard("mixed_acc"),
            )
            return

        short_summary = build_mixed_short_summary(mixed_items)
        await safe_edit_message(query, 
            f"{short_summary}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", True),
        )
        return

    if scope == "debt":
        debt_parsed = context.user_data.get("pending_debt")
        if not debt_parsed:
            await safe_edit_message(query, "❌ Sesi debt expired. Coba input ulang.")
            return

        intent = debt_parsed.get("intent")
        if debt_uses_cashflow(debt_parsed) and intent != "offset_debt" and not debt_parsed.get("account"):
            await safe_edit_message(
                query,
                build_debt_account_prompt(debt_parsed),
                parse_mode="Markdown",
                reply_markup=account_keyboard("debt_acc"),
            )
            return

        if debt_uses_cashflow(debt_parsed) and intent != "offset_debt":
            account_label = debt_parsed.get("account") or "-"
            preview = build_debt_confirm_preview(debt_parsed, account_label)
        else:
            preview = build_debt_only_confirm_preview(debt_parsed)

        await safe_edit_message(
            query,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("debt", True),
        )
        return

    if scope == "pending_expense":
        item = context.user_data.get("pending_expense_confirm")
        if not item:
            await safe_edit_message(query, "❌ Sesi pending expense expired. Coba input ulang.")
            return

        await safe_edit_message(
            query,
            build_pending_expense_confirm_preview(item, include_question=True),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("pending_expense"),
        )
        return

    if scope == "asset":
        asset = context.user_data.get("pending_asset_confirm")
        if not asset:
            await safe_edit_message(query, "❌ Sesi tambah aset expired. Coba input ulang.")
            return

        await safe_edit_message(
            query,
            build_asset_confirm_preview(asset),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("asset"),
        )
        return

    parsed = context.user_data.get("pending_parsed")
    if not parsed:
        await safe_edit_message(query, "❌ Sesi transaksi expired. Coba input ulang.")
        return

    if split_bill_needs_decision(parsed):
        await safe_edit_message(query, 
            build_split_bill_prompt_from_parsed(parsed),
            parse_mode="Markdown",
            reply_markup=split_bill_keyboard("single"),
        )
        return

    if needs_account(parsed):
        await safe_edit_message(
            query,
            build_single_account_prompt(parsed),
            parse_mode="Markdown",
            reply_markup=account_keyboard("acc"),
        )
        return

    short_summary = build_single_short_summary(parsed)
    preview = build_preview(parsed)
    await safe_edit_message(query, 
        f"{preview}\n\n{preview_action_question(True)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("single", True),
    )


async def handle_pending_preview_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Handle text replies used to edit a pending preview.

    Args:
        update: Telegram update that contains the edit instruction.
        context: Telegram context where pending preview state is stored.
        user_text: Edit instruction, for example `amount=20000` or
            `account=Cash`.

    Returns:
        True when the edit session consumes the message, otherwise False.

    Notes:
        This function only changes pending state and shows the next prompt. It
        does not save data to the sheet.
    """
    state = context.user_data.get("pending_preview_edit")
    if not state:
        return False

    scope = state.get("scope")
    step = state.get("step")

    if scope == "mixed" and step == "choose_item":
        try:
            item_index = int(str(user_text).strip()) - 1
        except Exception:
            await update.message.reply_text("❌ Balas dengan nomor item, contoh: `2`.", parse_mode="Markdown")
            return True

        mixed_items = context.user_data.get("pending_mixed") or []
        if item_index < 0 or item_index >= len(mixed_items):
            await update.message.reply_text("❌ Nomor item tidak valid. Coba pilih nomor yang ada di preview.")
            return True

        state["step"] = "edit_item"
        state["index"] = item_index
        context.user_data["pending_preview_edit"] = state
        await update.message.reply_text(
            build_preview_edit_help("mixed"),
            parse_mode="Markdown",
            reply_markup=build_preview_edit_keyboard("mixed"),
        )
        return True

    updates = parse_preview_edit_updates(user_text)
    if not updates:
        await update.message.reply_text(
            "❌ Format edit belum kebaca.\n\n" + build_preview_edit_help(scope or "single"),
            parse_mode="Markdown",
        )
        return True

    if scope == "mixed":
        mixed_items = context.user_data.get("pending_mixed") or []
        item_index = int(state.get("index", -1))
        if item_index < 0 or item_index >= len(mixed_items):
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit mixed tidak valid. Coba input ulang.")
            return True

        item = mixed_items[item_index]
        if item.get("kind") == "transaction":
            item["parsed"] = apply_preview_edit_updates_to_parsed(item.get("parsed", {}), updates)
        elif item.get("kind") == "debt":
            debt_updates = dict(updates)
            if "subject" in debt_updates:
                debt_updates["person_name"] = debt_updates.pop("subject")
            item.setdefault("parsed", {}).update(debt_updates)
        mixed_items[item_index] = item
        context.user_data["pending_mixed"] = mixed_items
        context.user_data.pop("pending_preview_edit", None)

        item_summary = build_updated_item_summary(item, item_index + 1)
        if mixed_needs_account(mixed_items):
            await reply_update_safely(
                update,
                f"{item_summary}\n\n{build_mixed_account_prompt(mixed_items)}",
                parse_mode="Markdown",
                reply_markup=account_keyboard("mixed_acc"),
            )
            return True

        short_summary = build_mixed_short_summary(mixed_items)
        await reply_update_safely(
            update,
            f"{item_summary}\n\n{short_summary}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", True),
        )
        return True

    if scope == "debt":
        debt_parsed = context.user_data.get("pending_debt")
        if not debt_parsed:
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit debt expired. Coba input ulang.")
            return True

        debt_updates = dict(updates)
        if "subject" in debt_updates:
            debt_updates["person_name"] = debt_updates.pop("subject")
        # `type` belongs to normal transactions, so ignore it for debt preview edits.
        debt_updates.pop("type", None)
        debt_parsed.update(debt_updates)
        context.user_data["pending_debt"] = debt_parsed
        context.user_data.pop("pending_preview_edit", None)

        intent = debt_parsed.get("intent")
        if debt_uses_cashflow(debt_parsed) and intent != "offset_debt" and not debt_parsed.get("account"):
            await reply_update_safely(
                update,
                f"✅ Preview debt sudah diupdate.\n\n{build_debt_account_prompt(debt_parsed)}",
                parse_mode="Markdown",
                reply_markup=account_keyboard("debt_acc"),
            )
            return True

        short_summary = build_debt_short_summary(debt_parsed)
        await reply_update_safely(
            update,
            f"✅ Preview debt sudah diupdate.\n\n{short_summary}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("debt", True),
        )
        return True

    if scope == "pending_expense":
        item = context.user_data.get("pending_expense_confirm")
        if not item:
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit pending expense expired. Coba input ulang.")
            return True

        pending_updates = dict(updates)
        if "date" in pending_updates:
            pending_updates["due_date"] = pending_updates.pop("date")
        pending_updates.pop("type", None)
        pending_updates.pop("to_account", None)

        item.update(pending_updates)
        if "due_date" in pending_updates and pending_updates.get("due_date"):
            item["due_precision"] = "date"
        if "month" in pending_updates and pending_updates.get("month") and not item.get("due_date"):
            item["due_precision"] = "month"
        if "description" in pending_updates and not pending_updates.get("subject"):
            item["subject"] = pending_updates["description"]

        context.user_data["pending_expense_confirm"] = item
        context.user_data.pop("pending_preview_edit", None)

        await reply_update_safely(
            update,
            f"✅ Preview pending expense sudah diupdate.\n\n{build_pending_expense_confirm_preview(item, include_question=False)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("pending_expense", True),
        )
        return True

    if scope == "asset":
        asset = context.user_data.get("pending_asset_confirm")
        if not asset:
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit aset expired. Coba input ulang.")
            return True

        asset_updates = dict(updates)
        if "amount" in asset_updates:
            asset_updates["amount"] = asset_updates["amount"]
        if "description" in asset_updates and not asset_updates.get("name") and not asset.get("name"):
            asset_updates["name"] = asset_updates["description"]

        asset.update(asset_updates)
        if asset.get("quantity") not in [None, ""] and asset.get("price_per_unit"):
            try:
                asset["amount"] = float(asset.get("quantity") or 0) * float(asset.get("price_per_unit") or 0)
            except Exception:
                pass

        context.user_data["pending_asset_confirm"] = asset
        context.user_data.pop("pending_preview_edit", None)

        await reply_update_safely(
            update,
            f"✅ Preview aset sudah diupdate.\n\n{build_asset_confirm_preview(asset)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("asset", True),
        )
        return True

    parsed = context.user_data.get("pending_parsed")
    if not parsed:
        context.user_data.pop("pending_preview_edit", None)
        await update.message.reply_text("❌ Sesi edit transaksi expired. Coba input ulang.")
        return True

    parsed = apply_preview_edit_updates_to_parsed(parsed, updates)
    context.user_data["pending_parsed"] = parsed
    context.user_data.pop("pending_preview_edit", None)

    if needs_account(parsed):
        await reply_update_safely(
            update,
            f"✅ Preview sudah diupdate.\n\n{build_single_account_prompt(parsed)}",
            parse_mode="Markdown",
            reply_markup=account_keyboard("acc"),
        )
        return True

    short_summary = build_single_short_summary(parsed)
    preview = build_preview(parsed)
    await reply_update_safely(
        update,
        f"✅ Preview sudah diupdate.\n\n{preview}\n\n{preview_action_question(True)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("single", True),
    )
    return True


def format_split_bill_preview_line(parsed: dict) -> str:
    """Format data into a readable display for split bill preview line."""
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    if not split_bill:
        return ""

    total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share = float(split_bill.get("share_amount", 0) or 0)
    total_receivable = float(split_bill.get("total_receivable", 0) or 0)
    status = split_bill.get("status")

    if status == "paid":
        status_label = "sudah dibayar"
        receivable_display = 0
    elif status == "unpaid":
        status_label = "belum dibayar / masuk piutang"
        receivable_display = total_receivable
    else:
        status_label = "menunggu status"
        receivable_display = total_receivable

    return (
        f"🤝 Split: {status_label} | "
        f"total dibayar {format_rupiah(total)} | "
        f"bagian kamu {format_rupiah(share)} | "
        f"piutang aktif {format_rupiah(receivable_display)}"
    )

def build_preview(parsed: dict) -> str:
    """Build the data structure or message text for preview."""
    type_label = {
        "expense": "❌ Pengeluaran",
        "income": "✅ Pemasukan",
        "transfer": "🔄 Transfer",
    }.get(parsed.get("type"), "❓")

    lines = [
        f"*{type_label}*",
        f"💰 Nominal : {format_rupiah(parsed.get('amount', 0))}",
        f"📁 Kategori: {parsed.get('category') or '-'}",
        f"👤 Subjek  : {parsed.get('subject') or '-'}",
        f"📝 Deskripsi: {parsed.get('description') or '-'}",
    ]

    split_preview = format_split_bill_preview_line(parsed)
    if split_preview:
        lines.append(split_preview)

    if parsed.get("catatan"):
        lines.append(f"🗒️ Catatan : {parsed.get('catatan')}")

    if parsed.get("tipe_pengeluaran"):
        lines.append(f"🏷️ Tipe    : {parsed.get('tipe_pengeluaran')}")

    lines.append(f"📅 Tanggal : {parsed.get('date') or '-'}")

    if parsed.get("account"):
        lines.append(f"🏦 Rekening: {parsed.get('account')}")

    if parsed.get("to_account"):
        lines.append(f"➡️ Ke Rekening: {parsed.get('to_account')}")

    account_summary = build_account_delta_summary_from_transaction_items([{"parsed": parsed}])
    if account_summary:
        lines.append(account_summary)

    return "\n".join(lines)


def build_batch_preview(parsed_items: list[dict]) -> str:
    """Build the data structure or message text for batch preview."""
    lines = [f"🧾 *Ditemukan {len(parsed_items)} transaksi:*\n"]

    total_expense = 0
    total_income = 0

    for i, item in enumerate(parsed_items, 1):
        parsed = item["parsed"]

        type_icon = {
            "expense": "❌",
            "income": "✅",
            "transfer": "🔄",
        }.get(parsed.get("type"), "❓")

        amount = float(parsed.get("amount", 0) or 0)

        if parsed.get("type") == "expense":
            total_expense += amount
        elif parsed.get("type") == "income":
            total_income += amount

        desc = parsed.get("description") or "-"
        category = parsed.get("category") or "-"
        account = parsed.get("account") or "-"
        subject = parsed.get("subject") or "-"
        spending_type = parsed.get("tipe_pengeluaran") or "-"

        date = parsed.get("date") or "-"

        lines.append(
            f"{i}. {type_icon} *{desc}*\n"
            f"   💰 {format_rupiah(amount)} | {category}\n"
            f"   📅 {date}\n"
            f"   👤 {subject} | 🏦 {account} | 🏷️ {spending_type}"
        )

        if parsed.get("catatan"):
            lines.append(f"   🗒️ {parsed.get('catatan')}")

    lines.append("\n*Ringkasan:*")
    lines.append(f"❌ Total Pengeluaran: *{format_rupiah(total_expense)}*")
    lines.append(f"✅ Total Pemasukan   : *{format_rupiah(total_income)}*")

    account_summary = build_account_delta_summary_from_transaction_items(parsed_items)
    if account_summary:
        lines.append(account_summary)

    return "\n".join(lines)


def strip_split_bill_phrase(text: str) -> str:
    """Helper for strip split bill phrase in the Telegram bot flow."""
    clean = str(text or "")

    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    # sering already kehilangan angka pembagi, misalnya:
    # "Nasi Kuning Dibagi Sama Raka".
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"
    participant_token = r"(?:\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|berdua|bertiga|berempat|berlima|berenam)"
    name_chunk = r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s,;&:%./]{0,140}"

    clean = re.sub(
        rf"\b{split_word}\s*(?:jadi\s*)?{participant_token}?\s*(?:orang\s+)?{friend_marker}\s+{name_chunk}",
        " ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        rf"\b{friend_marker}\s+{name_chunk}\s+{split_word}\s*(?:jadi\s*)?{participant_token}?",
        " ",
        clean,
        flags=re.IGNORECASE,
    )
    # Debt flow section
    # "Nasi kuning 22k dibagi 2 raka".
    clean = re.sub(
        rf"\b{split_word}\s*(?:jadi\s*)?{participant_token}\s*(?:orang\s+)?{name_chunk}",
        " ",
        clean,
        flags=re.IGNORECASE,
    )
    # Legacy compatibility note for older records or older in-memory state.
    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    clean = re.sub(
        rf"\b{split_word}\b.*$",
        " ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(r"\s+", " ", clean).strip(" .,-")
    return clean or str(text or "").strip()


def strip_trailing_split_person_names(text: str, person_names: list[str]) -> str:
    """Helper for strip trailing split person names in the Telegram bot flow."""
    clean = str(text or "").strip(" .,-")
    if not clean or not person_names:
        return clean

    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    ordered_names = sorted(
        [str(name or "").strip() for name in person_names if str(name or "").strip()],
        key=len,
        reverse=True,
    )

    changed = True
    while changed and clean:
        changed = False
        clean = clean.strip(" .,-")

        # Split bill parsing note: separate the paid transaction from each person share.
        new_clean = re.sub(r"\b(?:sama|ama|dengan|bareng|dan)\s*$", "", clean, flags=re.IGNORECASE).strip(" .,-")
        if new_clean != clean:
            clean = new_clean
            changed = True

        for person in ordered_names:
            pattern = rf"(?:^|[\s,;&]+){re.escape(person)}\s*$"
            new_clean = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip(" .,-")
            if new_clean != clean:
                clean = new_clean
                changed = True
                break

    return clean


SPLIT_BILL_ACCOUNT_TAIL_PATTERN = (
    r"\s+\b(?:via|pakai|pake|menggunakan|lewat|dari|from|using)\s+"
    r"(?:cash|bri|bsi|bca|dana|gopay|go\s*pay|seabank|sea\s*bank)\b.*$"
)


def strip_split_bill_account_tail(name_text: str) -> str:
    """Helper for strip split bill account tail in the Telegram bot flow."""
    clean = str(name_text or "").strip()
    clean = re.sub(SPLIT_BILL_ACCOUNT_TAIL_PATTERN, "", clean, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", clean).strip(" ,;&")


def limit_split_bill_friends_to_participants(
    person_names: list[str],
    person_shares: dict,
    participants: int,
    base_share_amount: float,
) -> tuple[list[str], dict]:
    """Helper for limit split bill friends to participants in the Telegram bot flow."""
    max_friends = max(int(participants or 0) - 1, 0)
    clean_names = [str(name or "").strip().title() for name in person_names or [] if str(name or "").strip()]

    if max_friends and len(clean_names) > max_friends:
        clean_names = clean_names[:max_friends]

    clean_shares = {}
    for name in clean_names:
        clean_shares[name] = float((person_shares or {}).get(name, base_share_amount) or 0)

    return clean_names, clean_shares


def split_split_bill_person_names(name_text: str) -> list[str]:
    """Helper for split split bill person names in the Telegram bot flow."""
    clean = strip_split_bill_account_tail(name_text)

    # Stop before date/status words so they do not become friend names.
    clean = re.split(
        r"\b(tanggal|tgl|tg|pada|date|kemarin|hari|minggu|bulan|udah|sudah|belum|dibayar|bayar|lunas|ke)\b",
        clean,
        flags=re.IGNORECASE,
    )[0]

    clean = re.sub(r"[^A-Za-zÀ-ÿ,;&\s]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip(" ,;&")
    if not clean:
        return []

    # Debt flow section
    if re.search(r"[,;&]|\bdan\b|\band\b", clean, flags=re.IGNORECASE):
        raw_parts = re.split(r"\s*(?:,|;|&|\bdan\b|\band\b)\s*", clean, flags=re.IGNORECASE)
    else:
        # Split bill parsing note: separate the paid transaction from each person share.
        raw_parts = clean.split()

    names = []
    seen = set()
    noise = {"sama", "ama", "dengan", "bareng", "dan", "and", "via", "pakai", "pake", "menggunakan", "lewat"}

    for part in raw_parts:
        part = re.sub(r"[^A-Za-zÀ-ÿ\s]", " ", str(part or ""))
        part = re.sub(r"\s+", " ", part).strip()
        if not part or part.lower() in noise:
            continue
        normalized = part.title()
        key = normalized.lower()
        if key not in seen:
            names.append(normalized)
            seen.add(key)

    return names



def strip_split_bill_name_tail(name_text: str) -> str:
    """Helper for strip split bill name tail in the Telegram bot flow."""
    clean = strip_split_bill_account_tail(name_text)
    clean = re.split(
        r"\b(tanggal|tgl|tg|pada|date|kemarin|hari|minggu|bulan|udah|sudah|belum|dibayar|bayar|lunas|ke)\b",
        clean,
        flags=re.IGNORECASE,
    )[0]
    return re.sub(r"\s+", " ", clean).strip(" ,;&")


def is_split_bill_allocation_token(value: str) -> bool:
    """Check whether a condition is true for split bill allocation token."""
    raw = str(value or "").strip().lower().rstrip(".,;)")
    if not raw:
        return False
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)?\s*(?:%|rb|ribu|k|jt|juta|m)?", raw))


def parse_split_bill_share_value(value: str, base_share: float) -> float:
    """Parse input into structured data for split bill share value."""
    raw = str(value or "").strip().lower().rstrip(".,;)")
    if not raw:
        return 0.0

    if raw.endswith("%"):
        try:
            pct = float(raw[:-1].replace(",", ".").strip())
            return max(base_share * pct / 100, 0.0)
        except Exception:
            return 0.0

    return max(parse_amount_text(raw), 0.0)


def parse_split_bill_people_and_shares(name_text: str, total_amount: float, participants: int) -> dict:
    """Parse input into structured data for split bill people and shares."""
    base_share = float(total_amount or 0) / int(participants or 1)
    clean = strip_split_bill_name_tail(name_text)
    clean = clean.replace("=", ":")
    clean = re.sub(r"\s*:\s*", ":", clean)
    clean = re.sub(r"\s*(?:,|;|&|\bdan\b|\band\b)\s*", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()

    if not clean:
        return {
            "person_names": [],
            "person_shares": {},
            "base_share_amount": base_share,
            "has_custom_share": False,
        }

    tokens = [t.strip(" ,;&") for t in clean.split() if t.strip(" ,;&")]
    noise = {"sama", "ama", "dengan", "bareng", "dan", "and", "via", "pakai", "pake", "menggunakan", "lewat"}
    entries = []
    has_custom_share = False
    i = 0

    while i < len(tokens):
        token = tokens[i].strip()
        low = token.lower()

        if not token or low in noise:
            i += 1
            continue

        name = ""
        value = None

        if ":" in token:
            name_part, value_part = token.split(":", 1)
            name_part = re.sub(r"[^A-Za-zÀ-ÿ\s]", " ", name_part).strip()
            value_part = value_part.strip()

            if name_part:
                name = name_part
                if is_split_bill_allocation_token(value_part):
                    value = value_part
                    has_custom_share = True
                elif not value_part and i + 1 < len(tokens) and is_split_bill_allocation_token(tokens[i + 1]):
                    value = tokens[i + 1]
                    has_custom_share = True
                    i += 1
        elif i + 1 < len(tokens) and is_split_bill_allocation_token(tokens[i + 1]):
            name_part = re.sub(r"[^A-Za-zÀ-ÿ\s]", " ", token).strip()
            if name_part:
                name = name_part
                value = tokens[i + 1]
                has_custom_share = True
                i += 1
        elif is_split_bill_allocation_token(token):
            # Split bill parsing note: separate the paid transaction from each person share.
            i += 1
            continue
        else:
            name_part = re.sub(r"[^A-Za-zÀ-ÿ\s]", " ", token).strip()
            if name_part:
                name = name_part

        if name:
            normalized_name = re.sub(r"\s+", " ", name).strip().title()
            if normalized_name and normalized_name.lower() not in noise:
                entries.append((normalized_name, value))

        i += 1

    person_names = []
    person_shares = {}
    seen = set()

    for name, value in entries:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        person_names.append(name)
        person_shares[name] = parse_split_bill_share_value(value, base_share) if value else base_share

    return {
        "person_names": person_names,
        "person_shares": person_shares,
        "base_share_amount": base_share,
        "has_custom_share": has_custom_share,
    }


def format_split_bill_person_shares(split_bill: dict) -> str:
    """Format data into a readable display for split bill person shares."""
    shares = (split_bill or {}).get("person_shares") or {}
    person_names = (split_bill or {}).get("person_names") or []
    if not shares and person_names:
        fallback = float((split_bill or {}).get("base_share_amount", (split_bill or {}).get("share_amount", 0)) or 0)
        shares = {str(name): fallback for name in person_names if str(name or "").strip()}

    parts = []
    for name in person_names:
        if not str(name or "").strip():
            continue
        amount = float(shares.get(name, 0) or 0)
        parts.append(f"{name}: {format_rupiah(amount)}")

    return ", ".join(parts)

def clean_split_person_name(name: str) -> str:
    """Clean input values for split person name."""
    names = split_split_bill_person_names(name)
    return " ".join(names).title() if names else ""


def build_split_bill_item_description_from_raw(raw: str, fallback: str = "") -> str:
    """Build the data structure or message text for split bill item description from raw."""
    text = normalize_slash_split_syntax(str(raw or ""))
    text = strip_date_phrases(text)
    text = re.sub(r"\b(?:rp|idr)?\s*\d[\d.,]*\s*(?:rb|ribu|k|jt|juta|m|miliar)?\b", " ", text, flags=re.IGNORECASE)

    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"
    participant_token = r"(?:\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|berdua|bertiga|berempat|berlima|berenam)"
    name_chunk = r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s,;&:%./]{0,140}"

    cleanup_patterns = [
        rf"\b{split_word}\s*(?:jadi\s*)?{participant_token}?\s*(?:orang\s+)?{friend_marker}\s+{name_chunk}",
        rf"\b{friend_marker}\s+{name_chunk}\s+{split_word}\s*(?:jadi\s*)?{participant_token}?",
        rf"\b{split_word}\s*(?:jadi\s*)?{participant_token}\s*(?:orang\s+)?{name_chunk}",
        rf"\b{participant_token}\s+{friend_marker}\s+{name_chunk}",
        rf"\b{split_word}\b.*$",
    ]
    for pattern in cleanup_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    text = re.sub(r"^(?:beli|bayar|buat|untuk|jajan)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^A-Za-zÀ-ÿ0-9\s&/+.-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ./,-")

    if text and text not in {"/", "-"}:
        return text.title()

    fallback_clean = strip_split_bill_phrase(fallback)
    fallback_clean = re.sub(r"^[\s/.-]+$", "", fallback_clean).strip()
    if re.match(r"^[\s/.-]*(?:sama|ama|dengan|bareng)\b", fallback_clean, flags=re.IGNORECASE):
        fallback_clean = ""
    if fallback_clean.startswith(("/", ".", "-")):
        fallback_clean = ""
    return fallback_clean.title() if fallback_clean else "Split Bill"


def detect_split_bill(parsed: dict, raw: str) -> dict | None:
    """Helper for detect split bill in the Telegram bot flow."""
    if not parsed or parsed.get("type") != "expense":
        return None

    normalized_raw = normalize_slash_split_syntax(str(raw or ""))
    original_total = extract_split_bill_total_amount(normalized_raw)
    amount = float(original_total or parsed.get("amount", 0) or 0)
    if amount <= 0:
        return None

    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Split bill parsing note: separate the paid transaction from each person share.
    text = normalize_slash_split_syntax(str(raw or ""))
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"
    participant_token = r"(?:\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|berdua|bertiga|berempat|berlima|berenam)"
    name_chunk = r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s,;&:%./]{0,140}"
    patterns = [
        # "dibagi 2 sama raka" / "bagi dua sama raka" / "patungan berempat sama ..."
        rf"\b{split_word}\s*(?:jadi\s*)?({participant_token})\s*(?:orang)?\s+{friend_marker}\s+({name_chunk})",
        # "sama raka dibagi 2" / "bareng raka bagi dua"
        rf"\b{friend_marker}\s+({name_chunk})\s+{split_word}\s*(?:jadi\s*)?({participant_token})",
        # Split bill parsing note: separate the paid transaction from each person share.
        # Split bill parsing note: separate the paid transaction from each person share.
        rf"\b{split_word}\s*(?:jadi\s*)?({participant_token})\s*(?:orang)?\s+({name_chunk})",
        # "berdua sama raka" / "bertiga bareng raka fajar".
        rf"\b({participant_token})\s+{friend_marker}\s+({name_chunk})",
    ]

    participants = None
    person_names = []
    person_shares = {}
    base_share_amount = 0.0
    has_custom_share = False

    for idx, pattern in enumerate(patterns):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        if idx in (0, 2, 3):
            participants = parse_participant_count(match.group(1))
            name_text = match.group(2)
        else:
            name_text = match.group(1)
            participants = parse_participant_count(match.group(2))

        if not participants:
            continue

        share_parse = parse_split_bill_people_and_shares(name_text, amount, participants)
        person_names = share_parse.get("person_names") or []
        person_shares = share_parse.get("person_shares") or {}
        base_share_amount = float(share_parse.get("base_share_amount", 0) or 0)
        person_names, person_shares = limit_split_bill_friends_to_participants(
            person_names,
            person_shares,
            participants,
            base_share_amount,
        )
        has_custom_share = bool(share_parse.get("has_custom_share"))
        break

    if not participants or participants < 2 or not person_names:
        return None

    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    parsed["amount"] = amount

    if not person_shares:
        base_share_amount = amount / participants
        person_shares = {person: base_share_amount for person in person_names}

    total_receivable = sum(float(v or 0) for v in person_shares.values())
    if total_receivable > amount and total_receivable > 0:
        scale = amount / total_receivable
        person_shares = {person: float(value or 0) * scale for person, value in person_shares.items()}
        total_receivable = amount
    user_share_amount = max(amount - total_receivable, 0.0)
    share_amount = user_share_amount  # Backward-compatible field: now represents the user share.

    # Debt flow section
    # Split bill parsing note: separate the paid transaction from each person share.
    # Debt flow section
    # Debt flow section
    clean_desc = build_split_bill_item_description_from_raw(raw, parsed.get("description") or "")
    clean_desc = strip_trailing_split_person_names(clean_desc, person_names)
    parsed["description"] = clean_desc

    subject = parsed.get("subject") or ""
    if subject:
        clean_subject = build_split_bill_item_description_from_raw(raw, subject)
        clean_subject = strip_trailing_split_person_names(clean_subject, person_names)
        if clean_subject != subject or re.search(split_word, subject, flags=re.IGNORECASE):
            parsed["subject"] = clean_subject or clean_desc

    return {
        "person_name": " ".join(person_names),  # backward compatibility
        "person_names": person_names,
        "participants": participants,
        "share_amount": share_amount,
        "user_share_amount": user_share_amount,
        "base_share_amount": base_share_amount,
        "person_shares": person_shares,
        "has_custom_share": has_custom_share,
        "total_receivable": total_receivable,
        "total_amount": amount,
        "status": None,  # paid / unpaid
    }


def attach_split_bill_if_any(parsed: dict, raw: str) -> dict:
    """Helper for attach split bill if any in the Telegram bot flow."""
    split_bill = detect_split_bill(parsed, raw)
    if split_bill:
        parsed["split_bill"] = split_bill
    return parsed


def split_bill_needs_decision(parsed: dict) -> bool:
    """Helper for split bill needs decision in the Telegram bot flow."""
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    return bool(split_bill) and not split_bill.get("status")


def mixed_split_bill_needs_decision(mixed_items: list[dict]) -> bool:
    """Helper for mixed split bill needs decision in the Telegram bot flow."""
    for item in mixed_items or []:
        if item.get("kind") == "transaction" and split_bill_needs_decision(item.get("parsed", {})):
            return True
    return False


def split_bill_keyboard(scope: str = "single", item_index: int | None = None) -> InlineKeyboardMarkup:
    """Helper for split bill keyboard in the Telegram bot flow."""
    suffix = f":{item_index}" if item_index is not None else ""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Sudah dibayar", callback_data=f"split:paid:{scope}{suffix}"),
            InlineKeyboardButton("🟢 Belum, masuk piutang", callback_data=f"split:unpaid:{scope}{suffix}"),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")],
    ])


def mixed_split_bill_keyboard(mixed_items: list[dict]) -> InlineKeyboardMarkup:
    """Helper for mixed split bill keyboard in the Telegram bot flow."""
    current_index = get_next_mixed_split_bill_index(mixed_items)
    return split_bill_keyboard("mixed", current_index)


def build_split_bill_prompt_from_parsed(parsed: dict) -> str:
    """Build the data structure or message text for split bill prompt from parsed."""
    split_bill = parsed.get("split_bill", {}) or {}
    person_names = split_bill.get("person_names") or [split_bill.get("person_name", "-")]
    participants = int(split_bill.get("participants", 2) or 2)
    total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share = float(split_bill.get("share_amount", 0) or 0)
    total_receivable = float(split_bill.get("total_receivable", share * len(person_names)) or 0)
    friend_text = ", ".join(str(p) for p in person_names if p)
    detail_text = format_split_bill_person_shares(split_bill)
    detail_line = f"📌 Rincian teman: *{md_safe(detail_text)}*\n" if detail_text else ""
    date_text = parsed.get("date") or "-"

    return (
        "🤝 *Split bill terdeteksi*\n\n"
        f"📝 Item: *{md_safe(parsed.get('description') or '-')}*\n"
        f"📅 Tanggal: *{md_safe(date_text)}*\n"
        f"💰 Total dibayar: *{format_rupiah(total)}*\n"
        f"👥 Dibagi: *{participants} orang*\n"
        f"👤 Teman: *{md_safe(friend_text)}*\n"
        f"📌 Bagian kamu: *{format_rupiah(share)}*\n"
        f"{detail_line}"
        f"📌 Total piutang jika belum dibayar: *{format_rupiah(total_receivable)}*\n\n"
        f"{md_safe(friend_text)} sudah bayar bagian mereka?\n"
        "Kalau *sudah*, transaksi disimpan sebesar bagian kamu saja.\n"
        "Kalau *belum*, transaksi disimpan sebesar total yang kamu talangi dan bagian teman masuk piutang."
    )


def build_mixed_split_bill_prompt(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed split bill prompt."""
    split_items = [
        item for item in mixed_items or []
        if item.get("kind") == "transaction" and split_bill_needs_decision(item.get("parsed", {}))
    ]

    lines = [f"🤝 *Split bill terdeteksi di {len(split_items)} item*\n"]

    for i, item in enumerate(split_items, 1):
        parsed = item["parsed"]
        split_bill = parsed.get("split_bill", {}) or {}
        person_names = split_bill.get("person_names") or [split_bill.get("person_name", "-")]
        total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
        share = float(split_bill.get("share_amount", 0) or 0)
        total_receivable = float(split_bill.get("total_receivable", share * len(person_names)) or 0)
        friend_text = ", ".join(str(p) for p in person_names if p)
        detail_text = format_split_bill_person_shares(split_bill)
        detail_suffix = f" | {md_safe(detail_text)}" if detail_text else ""
        date_text = parsed.get("date") or "-"
        lines.append(
            f"{i}. {md_safe(parsed.get('description') or '-')} "
            f"(*{md_safe(date_text)}*) — "
            f"total *{format_rupiah(total)}*, bagian kamu *{format_rupiah(share)}*, "
            f"piutang *{format_rupiah(total_receivable)}*{detail_suffix}"
        )

    lines.append(
        "\nApakah bagian teman-teman di item ini sudah dibayar?\n"
        "Pilih *Sudah dibayar* kalau transaksi cukup disimpan sebesar bagian kamu.\n"
        "Pilih *Belum* kalau kamu menalangi totalnya dan bagian teman otomatis masuk piutang."
    )
    return "\n".join(lines)


def get_mixed_split_bill_indexes(mixed_items: list[dict]) -> list[int]:
    """Get data needed for mixed split bill indexes."""
    indexes = []
    for idx, item in enumerate(mixed_items or []):
        if item.get("kind") != "transaction":
            continue
        parsed = item.get("parsed", {})
        if isinstance(parsed, dict) and parsed.get("split_bill"):
            indexes.append(idx)
    return indexes


def get_next_mixed_split_bill_index(mixed_items: list[dict]) -> int | None:
    """Get data needed for next mixed split bill index."""
    for idx in get_mixed_split_bill_indexes(mixed_items):
        parsed = mixed_items[idx].get("parsed", {})
        if split_bill_needs_decision(parsed):
            return idx
    return None


def build_mixed_split_bill_queue_prompt(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed split bill queue prompt."""
    split_indexes = get_mixed_split_bill_indexes(mixed_items)
    current_index = get_next_mixed_split_bill_index(mixed_items)

    if current_index is None:
        return build_mixed_preview(mixed_items)

    current_pos = split_indexes.index(current_index) + 1 if current_index in split_indexes else 1
    total_split = len(split_indexes)
    parsed = mixed_items[current_index].get("parsed", {})
    split_bill = parsed.get("split_bill", {}) or {}
    person_names = split_bill.get("person_names") or [split_bill.get("person_name", "-")]
    participants = int(split_bill.get("participants", 2) or 2)
    total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share = float(split_bill.get("share_amount", 0) or 0)
    total_receivable = float(split_bill.get("total_receivable", share * len(person_names)) or 0)
    friend_text = ", ".join(str(p) for p in person_names if p)
    detail_text = format_split_bill_person_shares(split_bill)
    detail_line = f"📌 Rincian teman: *{md_safe(detail_text)}*\n" if detail_text else ""
    date_text = parsed.get("date") or "-"

    return (
        f"🤝 *Split bill {current_pos}/{total_split}*\n\n"
        f"📝 Item: *{md_safe(parsed.get('description') or '-')}*\n"
        f"📅 Tanggal: *{md_safe(date_text)}*\n"
        f"💰 Total dibayar: *{format_rupiah(total)}*\n"
        f"👥 Dibagi: *{participants} orang*\n"
        f"👤 Teman: *{md_safe(friend_text)}*\n"
        f"📌 Bagian kamu: *{format_rupiah(share)}*\n"
        f"{detail_line}"
        f"📌 Total piutang jika belum dibayar: *{format_rupiah(total_receivable)}*\n\n"
        f"{md_safe(friend_text)} sudah bayar bagian untuk item ini?\n"
        "Pilihan ini *hanya berlaku untuk item ini*. Setelah dijawab, saya lanjut ke split bill berikutnya."
    )


def apply_split_bill_decision_to_current_mixed(mixed_items: list[dict], status: str) -> tuple[list[dict], int | None]:
    """Apply changes for split bill decision to current mixed."""
    current_index = get_next_mixed_split_bill_index(mixed_items)
    if current_index is None:
        return mixed_items, None
    mixed_items, decided_index, _ = apply_split_bill_decision_to_mixed_index(mixed_items, current_index, status)
    return mixed_items, decided_index


def apply_split_bill_decision_to_mixed_index(mixed_items: list[dict], item_index: int, status: str) -> tuple[list[dict], int | None, str]:
    """Apply changes for split bill decision to mixed index."""
    if item_index is None or item_index < 0 or item_index >= len(mixed_items or []):
        return mixed_items, None, "invalid"

    item = mixed_items[item_index]
    if item.get("kind") != "transaction":
        return mixed_items, None, "invalid"

    parsed = item.get("parsed", {})
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    if not split_bill:
        return mixed_items, None, "invalid"

    if split_bill.get("status"):
        return mixed_items, item_index, "already_decided"

    apply_split_bill_decision_to_parsed(parsed, status)
    item["parsed"] = parsed
    mixed_items[item_index] = item
    return mixed_items, item_index, "applied"


# Split bill parsing note: separate the paid transaction from each person share.
# Debt flow section

def apply_split_bill_decision_to_parsed(parsed: dict, status: str) -> dict:
    """Apply changes for split bill decision to parsed."""
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    if not split_bill:
        return parsed

    split_bill["status"] = status

    total_amount = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share_amount = float(split_bill.get("user_share_amount", split_bill.get("share_amount", 0)) or 0)

    if status == "paid":
        if share_amount <= 0 and total_amount > 0:
            participants = int(split_bill.get("participants", 0) or 0)
            if participants > 0:
                share_amount = total_amount / participants
                split_bill["share_amount"] = share_amount
                split_bill["user_share_amount"] = share_amount
        if share_amount > 0:
            parsed["amount"] = share_amount
    elif status == "unpaid" and total_amount > 0:
        parsed["amount"] = total_amount

    return parsed


def apply_split_bill_decision_to_mixed(mixed_items: list[dict], status: str) -> list[dict]:
    """Apply changes for split bill decision to mixed."""
    for item in mixed_items or []:
        if item.get("kind") != "transaction":
            continue
        parsed = item.get("parsed", {})
        if parsed.get("split_bill"):
            apply_split_bill_decision_to_parsed(parsed, status)
    return mixed_items


def create_split_bill_debt(parsed: dict, raw: str = "", source_transaction_id: str = "") -> dict | None:
    """Create a new data object for split bill debt."""
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    if not split_bill or split_bill.get("status") != "unpaid":
        return None

    person_names = split_bill.get("person_names") or [split_bill.get("person_name")]
    person_names = [str(p).strip().title() for p in person_names if str(p or "").strip()]
    person_shares = split_bill.get("person_shares") or {}
    fallback_share = float(split_bill.get("base_share_amount", split_bill.get("share_amount", 0)) or 0)

    if not person_names:
        return None

    desc = f"Split bill: {parsed.get('description') or raw or '-'}"
    created = []
    failed = []

    for person in person_names:
        share_amount = float(person_shares.get(person, fallback_share) or 0)
        if share_amount <= 0:
            continue

        result = add_debt(
            "receivable",
            person,
            share_amount,
            desc,
            source_transaction_id=source_transaction_id,
            cashflow_mode="debt_only",
            fronting_mode="split_bill",
        )
        if result and result.get("success"):
            created.append({
                "person_name": person,
                "remaining": share_amount,
                "debt_id": result.get("debt_id"),
            })
        else:
            failed.append({
                "person_name": person,
                "message": (result or {}).get("message", "Gagal membuat piutang."),
            })

    if failed and not created:
        return {
            "success": False,
            "message": "; ".join(f"{x['person_name']}: {x['message']}" for x in failed),
            "created": created,
            "failed": failed,
        }

    return {
        "success": True,
        "person_name": ", ".join(x["person_name"] for x in created),
        "remaining": sum(float(x["remaining"] or 0) for x in created),
        "created": created,
        "failed": failed,
        "message": "ok" if not failed else "; ".join(f"{x['person_name']}: {x['message']}" for x in failed),
    }


def format_split_debt_result_lines(debt_result: dict) -> list[str]:
    """Format data into a readable display for split debt result lines."""
    lines = []
    for item in (debt_result or {}).get("created", []) or []:
        lines.append(
            f"• {md_safe(item.get('person_name'))}: *{format_rupiah(float(item.get('remaining', 0) or 0))}*"
        )
    return lines


def summarize_saved_transaction_items(items: list[dict]) -> dict:
    """Summarize data for saved transaction items."""
    total_expense = 0.0
    total_income = 0.0
    total_transfer = 0.0
    for item in items or []:
        parsed = item.get("parsed", {})
        amount = float(parsed.get("amount", 0) or 0)
        if parsed.get("type") == "expense":
            total_expense += amount
        elif parsed.get("type") == "income":
            total_income += amount
        elif parsed.get("type") == "transfer":
            total_transfer += amount
    return {
        "expense": total_expense,
        "income": total_income,
        "transfer": total_transfer,
        "net": total_income - total_expense,
    }


def append_saved_summary_lines(lines: list[str], items: list[dict], title: str = "Ringkasan tersimpan"):
    """Append data to saved summary lines."""
    summary = summarize_saved_transaction_items(items)
    lines.append(f"\n📊 *{title}:*")
    lines.append(f"❌ Pengeluaran: *{format_rupiah(summary['expense'])}*")
    lines.append(f"✅ Pemasukan : *{format_rupiah(summary['income'])}*")
    if summary["transfer"]:
        lines.append(f"🔄 Transfer  : *{format_rupiah(summary['transfer'])}*")
    lines.append(f"📌 Net       : *{format_rupiah(summary['net'])}*")

def _clean_fronting_item_text(text: str, person: str = "") -> str:
    """Clean input values for fronting item text."""
    item = str(text or "").strip()
    if person:
        item = re.sub(rf"\b(?:sama|oleh|ke|dari)?\s*(?:si\s+)?{re.escape(person)}\b", " ", item, flags=re.IGNORECASE)
    item = re.sub(r"\b(?:tanggal|tgl|kemarin|hari\s+ini|besok|bulan\s+depan|minggu\s+depan)\b.*$", " ", item, flags=re.IGNORECASE)
    item = re.sub(r"\b(?:rp|idr)?\s*\d+[\d.,]*\s*(?:rb|ribu|k|jt|juta)?(?:\s*/\s*\d+)?\b", " ", item, flags=re.IGNORECASE)
    item = strip_split_bill_phrase(item)
    # Legacy compatibility note for older records or older in-memory state.
    # Clean leftover split-bill phrases so subject and description stay readable.
    # "Minyak Dibagi", "Minyak Dibagi Fajar Raka", "Minyak Dibagi Sama Fajar Raka".
    item = re.sub(r"\b(?:di\s*-?\s*bagi|dibagi|bagi|split|share|patungan)\b.*$", " ", item, flags=re.IGNORECASE)
    item = re.sub(r"^\s*(?:beli|bayar|byr|jajan|makan|minum)\b", " ", item, flags=re.IGNORECASE)
    item = re.sub(r"\s+", " ", item).strip(" .,-:")
    return item.title() if item else ""


def _fronting_expense_description(debt_parsed: dict) -> str:
    """Helper for fronting expense description in the Telegram bot flow."""
    description = str(debt_parsed.get("description") or "").strip()
    person = str(debt_parsed.get("person_name") or "").strip()

    if ":" in description:
        item = _clean_fronting_item_text(description.split(":", 1)[1].strip(), person)
        if item:
            return item

    raw = str(debt_parsed.get("raw_input") or "").strip()

    item = re.sub(r"\b(?:saya|aku|gw|gue)?\s*(?:nitip|ditalangin|ditalangi|dibayarin|duluin)\b", " ", raw, flags=re.IGNORECASE)
    item = _clean_fronting_item_text(item, person)
    return item if item else (description or "Ditalangin")


def _fronting_expense_category(debt_parsed: dict) -> str:
    """Helper for fronting expense category in the Telegram bot flow."""
    raw = str(debt_parsed.get("raw_input") or "").strip()
    if raw:
        try:
            parsed = parse_with_regex(raw)
            category = str((parsed or {}).get("category") or "").strip()
            txn_type = str((parsed or {}).get("type") or "").strip().lower()
            if txn_type == "expense" and category:
                return category
        except Exception:
            pass
    return str(debt_parsed.get("category") or "Other Expense").strip() or "Other Expense"


def is_ditalangin_expense_without_balance(debt_parsed: dict) -> bool:
    """Check whether a condition is true for ditalangin expense without balance."""
    return (
        str(debt_parsed.get("cashflow_mode") or "").strip() == "debt_only"
        and str(debt_parsed.get("fronting_mode") or "").strip().lower() == "ditalangin"
        and str(debt_parsed.get("intent") or "").strip() == "add_payable"
    )


def normalize_slash_split_syntax(raw: str) -> str:
    """Normalize and clean input for slash split syntax."""
    text = str(raw or "")
    return re.sub(
        r"(\d+[\d.,]*\s*(?:rb|ribu|k|jt|juta)?)\s*/\s*(\d+)",
        r"\1 dibagi \2",
        text,
        flags=re.IGNORECASE,
    )


def enrich_ditalangin_split_bill_if_any(debt_parsed: dict, raw: str | None = None) -> dict:
    """Helper for enrich ditalangin split bill if any in the Telegram bot flow."""
    if not isinstance(debt_parsed, dict) or not is_ditalangin_expense_without_balance(debt_parsed):
        return debt_parsed

    raw_text = str(raw or debt_parsed.get("raw_input") or "")
    if not raw_text:
        return debt_parsed

    amount = float(debt_parsed.get("amount") or 0)
    if amount <= 0:
        return debt_parsed

    item_desc = _fronting_expense_description(debt_parsed)
    temp_parsed = {
        "type": "expense",
        "amount": amount,
        "category": _fronting_expense_category(debt_parsed),
        "subject": item_desc,
        "description": item_desc,
    }

    split_bill = detect_split_bill(temp_parsed, normalize_slash_split_syntax(raw_text))
    if not split_bill:
        return debt_parsed

    user_share = float(split_bill.get("user_share_amount", 0) or 0)
    total_amount = float(split_bill.get("total_amount", amount) or amount)
    participants = int(split_bill.get("participants", 0) or 0)

    if user_share <= 0 and participants > 0:
        user_share = total_amount / participants
    if user_share <= 0:
        return debt_parsed

    person_shares = split_bill.get("person_shares") or {}
    total_receivable = float(split_bill.get("total_receivable", 0) or 0)

    updated = dict(debt_parsed)
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    updated["amount"] = total_amount
    updated["fronted_split_bill"] = split_bill
    updated["fronted_gross_amount"] = total_amount
    updated["fronted_user_share"] = user_share
    updated["fronted_total_receivable"] = total_receivable
    updated["fronted_participants"] = participants
    updated["fronted_split_people"] = split_bill.get("person_names") or []
    updated["fronted_person_shares"] = person_shares
    updated["expense_description"] = temp_parsed.get("description") or item_desc
    updated["description"] = f"Ditalangin {updated.get('person_name')}: {temp_parsed.get('description') or item_desc}"
    return updated


def _debt_payment_catatan(debt_parsed: dict, raw: str) -> str:
    """Helper for debt payment catatan in the Telegram bot flow."""
    parts = [str(raw or "").strip()]
    allocations = debt_parsed.get("debt_allocations") or []
    alloc_parts = []
    for item in allocations:
        debt_id = str(item.get("debt_id") or "").strip()
        amount = item.get("amount")
        if debt_id and amount is not None:
            alloc_parts.append(f"{debt_id}:{float(amount)}")
    if alloc_parts:
        parts.append("debt_allocations=" + ";".join(alloc_parts))
    if debt_parsed.get("net_settlement"):
        parts.append("net_settle=1")
    overpayment = float(debt_parsed.get("overpayment", 0) or 0)
    if overpayment > 0:
        parts.append(f"overpayment={overpayment}")
        if debt_parsed.get("overpayment_policy"):
            parts.append(f"overpayment_policy={debt_parsed.get('overpayment_policy')}")
        if debt_parsed.get("overpayment_debt_id"):
            parts.append(f"overpayment_debt_id={debt_parsed.get('overpayment_debt_id')}")
    return " | ".join([p for p in parts if p]).strip(" |")


def build_debt_cashflow_transaction(
    debt_parsed: dict,
    account: str,
    debt_type_for_payment: str | None = None,
) -> dict:
    """Build the data structure or message text for debt cashflow transaction."""
    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or ""
    amount = debt_parsed.get("amount") or 0
    raw = debt_parsed.get("raw_input") or ""
    transaction_date = debt_parsed.get("date") or datetime.now().strftime("%Y-%m-%d")
    hutang_id = debt_parsed.get("hutang_id") or debt_parsed.get("debt_id") or debt_parsed.get("target_debt_id") or ""
    tipe_hutang = debt_parsed.get("tipe_hutang") or ""
    if not tipe_hutang:
        if intent == "add_payable" or debt_type_for_payment == "payable":
            tipe_hutang = "utang"
        elif intent == "add_receivable" or debt_type_for_payment == "receivable":
            tipe_hutang = "piutang"


    if str(debt_parsed.get("cashflow_mode") or "").strip() == "debt_only":
        # Account flow section
        # Account flow section
        # Natural input section
        # Account flow section
        if is_ditalangin_expense_without_balance(debt_parsed):
            item_desc = str(debt_parsed.get("expense_description") or "").strip() or _fronting_expense_description(debt_parsed)
            catatan_parts = [str(raw or "").strip(), "ditalangin/tanpa update saldo rekening"]
            if debt_parsed.get("fronted_split_bill"):
                catatan_parts.append(
                    f"gross dibayarkan orang lain {format_rupiah(debt_parsed.get('fronted_gross_amount', amount))}; "
                    f"bagian user {format_rupiah(debt_parsed.get('fronted_user_share', amount))}; "
                    f"piutang teman {format_rupiah(debt_parsed.get('fronted_total_receivable', 0))}"
                )
            return {
                "type": "expense",
                "amount": amount,
                "category": _fronting_expense_category(debt_parsed),
                "account": "Ditalangin",
                "to_account": None,
                "subject": item_desc,
                "description": item_desc,
                "catatan": " | ".join([p for p in catatan_parts if p]).strip(" |"),
                "tipe_pengeluaran": "",
                "date": transaction_date,
                "hutang_id": hutang_id,
                "tipe_hutang": tipe_hutang or "utang",
                "parsed_by": "debt",
                "skip_account": True,
            }

        if intent == "add_payable":
            category = "Utang Tanpa Cashflow"
            description = f"Utang tanpa cashflow ke {person}: {debt_parsed.get('description') or raw}"
        elif intent == "add_receivable":
            category = "Piutang Tanpa Cashflow"
            description = f"Piutang tanpa cashflow ke {person}: {debt_parsed.get('description') or raw}"
        elif intent == "add_payment":
            category = "Pembayaran Debt Tanpa Cashflow"
            description = f"Pembayaran debt tanpa cashflow {person}: {debt_parsed.get('description') or raw}"
        else:
            category = "Debt Tanpa Cashflow"
            description = debt_parsed.get("description") or raw

        return {
            "type": "debt_only",
            "amount": amount,
            "category": category,
            "account": "Debt Only",
            "to_account": None,
            "subject": person,
            "description": description,
            "catatan": raw,
            "tipe_pengeluaran": "",
            "date": transaction_date,
            "hutang_id": hutang_id,
            "tipe_hutang": tipe_hutang,
            "parsed_by": "debt_only",
            "skip_account": True,
        }

    if intent == "add_receivable":
        return {
            "type": "expense",
            "amount": amount,
            "category": "Piutang Diberikan",
            "account": account,
            "to_account": None,
            "subject": person,
            "description": f"Pinjaman ke {person}",
            "catatan": raw,
            "tipe_pengeluaran": "",
            "date": transaction_date,
            "hutang_id": hutang_id,
            "tipe_hutang": tipe_hutang,
            "parsed_by": "debt",
        }

    if intent == "add_payable":
        return {
            "type": "income",
            "amount": amount,
            "category": "Penerimaan Utang",
            "account": account,
            "to_account": None,
            "subject": person,
            "description": f"Pinjaman dari {person}",
            "catatan": raw,
            "tipe_pengeluaran": "",
            "date": transaction_date,
            "hutang_id": hutang_id,
            "tipe_hutang": tipe_hutang,
            "parsed_by": "debt",
        }

    if intent == "add_payment":
        if debt_type_for_payment == "payable":
            return {
                "type": "expense",
                "amount": amount,
                "category": "Bayar Utang",
                "account": account,
                "to_account": None,
                "subject": person,
                "description": f"Bayar utang ke {person}",
                "catatan": _debt_payment_catatan(debt_parsed, raw),
                "tipe_pengeluaran": "",
                "date": transaction_date,
                "hutang_id": hutang_id,
                "tipe_hutang": tipe_hutang,
                "parsed_by": "debt",
            }

        if debt_type_for_payment == "receivable":
            return {
                "type": "income",
                "amount": amount,
                "category": "Pembayaran Piutang",
                "account": account,
                "to_account": None,
                "subject": person,
                "description": f"Pembayaran piutang dari {person}",
                "catatan": _debt_payment_catatan(debt_parsed, raw),
                "tipe_pengeluaran": "",
                "date": transaction_date,
                "hutang_id": hutang_id,
                "tipe_hutang": tipe_hutang,
                "parsed_by": "debt",
            }

    if intent == "offset_debt":
        target_label = "piutang" if debt_parsed.get("target_debt_type") == "receivable" else "utang"
        return {
            "type": "debt_offset",
            "amount": amount,
            "category": "Kompensasi Hutang/Piutang",
            "account": "Debt Offset",
            "to_account": None,
            "subject": person,
            "description": f"Kompensasi {target_label} {person}: {debt_parsed.get('description') or raw}",
            "catatan": raw,
            "tipe_pengeluaran": "",
            "date": transaction_date,
            "hutang_id": hutang_id,
            "tipe_hutang": "offset",
            "parsed_by": "debt_offset",
            "skip_account": True,
        }

    return {
        "type": "pending",
        "amount": 0,
        "category": None,
        "account": account,
        "to_account": None,
        "subject": person,
        "description": "Debt cashflow tidak valid",
        "catatan": raw,
        "tipe_pengeluaran": "",
        "date": transaction_date,
        "hutang_id": hutang_id,
        "tipe_hutang": tipe_hutang,
        "parsed_by": "debt",
    }


def debt_uses_cashflow(debt_parsed: dict) -> bool:
    """Helper for debt uses cashflow in the Telegram bot flow."""
    return str(debt_parsed.get("cashflow_mode") or "cashflow") != "debt_only"


def build_debt_only_confirm_preview(debt_parsed: dict) -> str:
    """Build the data structure or message text for debt only confirm preview."""
    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or "-"
    amount = debt_parsed.get("amount") or 0
    raw = debt_parsed.get("raw_input") or "-"
    fronting_mode = debt_parsed.get("fronting_mode") or "debt_only"
    transaction_parsed = build_debt_cashflow_transaction(debt_parsed, account="Debt Only")

    if intent == "add_payable":
        if is_ditalangin_expense_without_balance(debt_parsed):
            title = "🟠 *Ditalangin / Pengeluaran Ditanggung Dulu*"
            if debt_parsed.get("fronted_split_bill"):
                split_people = debt_parsed.get("fronted_split_people") or []
                people_text = ", ".join(str(x) for x in split_people if str(x).strip()) or "-"
                debt_effect = (
                    f"Anda punya utang ke {md_safe(person)} sebesar *gross yang ditalangi*: "
                    f"{format_rupiah(debt_parsed.get('fronted_gross_amount', amount))}.\n"
                    f"Bagian Anda dalam PTPT: {format_rupiah(debt_parsed.get('fronted_user_share', 0))}."
                )
                transaction_effect = (
                    "Dicatat sebagai *pengeluaran gross* di sheet transactions agar PTPT bulanan tetap penuh.\n"
                    f"Piutang share dibuat ke: {md_safe(people_text)} dengan total "
                    f"{format_rupiah(debt_parsed.get('fronted_total_receivable', 0))}.\n"
                    "Saldo rekening *tidak berubah* karena uang belum keluar dari rekening Anda."
                )
            else:
                debt_effect = f"Anda punya utang ke {md_safe(person)}."
                transaction_effect = (
                    "Dicatat sebagai *pengeluaran* di sheet transactions agar masuk /harian, /mingguan, /bulanan, dan /budget.\n"
                    "Saldo rekening *tidak berubah* karena uang belum keluar dari rekening Anda."
                )
        else:
            title = "🟠 *Utang Tanpa Cashflow*"
            debt_effect = f"Anda punya utang ke {md_safe(person)}."
            transaction_effect = "Tetap dicatat di sheet transactions sebagai fact table, tetapi saldo rekening tidak berubah."
    elif intent == "add_receivable":
        title = "🟢 *Talangin / Piutang Tanpa Cashflow*"
        debt_effect = f"{md_safe(person)} punya utang ke Anda."
        transaction_effect = "Tetap dicatat di sheet transactions sebagai fact table, tetapi saldo rekening tidak berubah."
    elif intent == "offset_debt":
        title = "🔁 *Kompensasi Hutang/Piutang*"
        target_label = "piutang" if debt_parsed.get("target_debt_type") == "receivable" else "utang"
        debt_effect = f"Memotong {target_label} aktif dengan {md_safe(person)} tanpa rekening."
        transaction_effect = "Tetap dicatat sebagai debt offset tanpa mengubah saldo rekening."
    else:
        title = "💸 *Debt Tanpa Cashflow*"
        debt_effect = "Debt dicatat tanpa transaksi kas."
        transaction_effect = "Tetap dicatat di sheet transactions sebagai fact table, tetapi saldo rekening tidak berubah."

    return (
        f"{title}\n\n"
        f"👤 Subjek : {md_safe(person)}\n"
        f"💰 Nominal: {format_rupiah(amount)}\n"
        f"📝 Input  : `{md_safe(raw)}`\n\n"
        f"*Efek Debt:*\n"
        f"{debt_effect}\n\n"
        f"*Efek Transactions:*\n"
        f"{transaction_effect}\n"
        f"📌 Tipe: `{md_safe(transaction_parsed.get('type') or '-')}`\n"
        f"📁 Kategori: {md_safe(transaction_parsed.get('category') or '-')}\n"
        f"📝 Deskripsi: {md_safe(transaction_parsed.get('description') or '-')}\n"
        f"Mode: `{md_safe(fronting_mode)}`\n\n"
        f"Simpan utang/piutang ini?"
    )


def build_debt_initial_preview(debt_parsed: dict) -> str:
    """Build the data structure or message text for debt initial preview."""
    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or "-"
    amount = debt_parsed.get("amount") or 0
    description = debt_parsed.get("description") or "-"
    raw = debt_parsed.get("raw_input") or "-"
    date = debt_parsed.get("date") or "-"
    fronting_mode = debt_parsed.get("fronting_mode") or ""

    if intent == "add_receivable":
        title = "🟢 *Preview Piutang Baru*"
        effect = f"{md_safe(person)} punya utang ke Anda."
    elif intent == "add_payable":
        title = "🔴 *Preview Utang Baru*"
        effect = f"Anda punya utang ke {md_safe(person)}."
    elif intent == "add_payment":
        title = "💸 *Preview Pembayaran Utang/Piutang*"
        effect = f"Pembayaran terkait saldo aktif dengan {md_safe(person)}."
    elif intent == "offset_debt":
        title = "🔁 *Preview Kompensasi Hutang/Piutang*"
        effect = "Debt akan dikompensasi tanpa uang masuk/keluar rekening."
    else:
        title = "💸 *Preview Debt*"
        effect = "Input debt terdeteksi."

    if debt_uses_cashflow(debt_parsed) and intent != "offset_debt":
        next_step = "Jika lanjut, bot akan meminta rekening cashflow sebelum konfirmasi simpan."
    else:
        next_step = "Jika lanjut, bot akan menampilkan konfirmasi simpan tanpa mengubah saldo rekening."

    lines = [
        title,
        "",
        f"👤 Subjek : {md_safe(person)}",
        f"💰 Nominal: {format_rupiah(amount)}",
        f"📅 Tanggal: {md_safe(date)}",
        f"📝 Detail : {md_safe(description)}",
        f"🧾 Input  : `{md_safe(raw)}`",
        "",
        "*Efek debt:*",
        effect,
    ]
    if fronting_mode:
        lines.append(f"Mode: `{md_safe(fronting_mode)}`")
    lines.extend([
        "",
        f"ℹ️ {next_step}",
        "",
        "Data ini *belum disimpan*.",
    ])
    return "\n".join(lines)


def build_debt_short_summary(debt_parsed: dict) -> str:
    """Build the data structure or message text for debt short summary."""
    intent = debt_parsed.get("intent") or "debt"
    person = md_safe(debt_parsed.get("person_name") or "-")
    amount = float(debt_parsed.get("amount", 0) or 0)
    description = md_safe(debt_parsed.get("description") or "-")
    account = md_safe(debt_parsed.get("account") or "-")

    labels = {
        "add_payable": "Utang baru",
        "add_receivable": "Piutang baru",
        "add_payment": "Pembayaran debt",
        "offset_debt": "Kompensasi debt",
    }
    lines = ["💸 *Ringkasan debt:*"]
    lines.append(f"• Jenis: *{md_safe(labels.get(intent, intent))}*")
    lines.append(f"• Subjek: *{person}*")
    lines.append(f"• Nominal: *{format_rupiah(amount)}*")
    lines.append(f"• Detail: {description}")
    if account != "-":
        lines.append(f"• Rekening: *{account}*")
    return "\n".join(lines)

def build_debt_account_prompt(debt_parsed: dict) -> str:
    """Build the data structure or message text for debt account prompt."""
    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or "-"
    amount = debt_parsed.get("amount") or 0

    if intent == "add_receivable":
        title = "🟢 *Piutang Baru*"
        desc = f"{md_safe(person)} meminjam uang dari Anda."
        effect = "Cashflow: pengeluaran, kategori Piutang Diberikan"

    elif intent == "add_payable":
        title = "🔴 *Utang Baru*"
        desc = f"Anda punya utang ke {md_safe(person)}."
        effect = "Cashflow: pemasukan, kategori Penerimaan Utang"

    elif intent == "add_payment":
        title = "💸 *Pembayaran Utang/Piutang*"
        desc = f"Pembayaran terkait {person}."
        effect = "Cashflow akan mengikuti posisi aktif di sheet debts"

    elif intent == "offset_debt":
        title = "🔁 *Kompensasi Hutang/Piutang*"
        target_label = "piutang" if debt_parsed.get("target_debt_type") == "receivable" else "utang"
        desc = f"Potong {target_label} aktif dengan {md_safe(person)}."
        effect = "Tidak pakai rekening; tetap masuk transactions sebagai debt_offset"

    else:
        title = "❓ *Debt*"
        desc = "Input debt terdeteksi."
        effect = "-"

    return (
        f"{title}\n\n"
        f"👤 Subjek : {md_safe(person)}\n"
        f"💰 Nominal: {format_rupiah(amount)}\n"
        f"📝 Detail : {desc}\n"
        f"📌 Efek  : {effect}\n\n"
        f"💳 Pilih rekening cashflow, atau pilih *Sudah berlalu* jika hanya ingin mencatat debt tanpa mengubah saldo:"
    )

def build_debt_confirm_preview(
    debt_parsed: dict,
    account: str,
    debt_type_for_payment: str | None = None,
) -> str:
    """Build the data structure or message text for debt confirm preview."""
    transaction_parsed = build_debt_cashflow_transaction(
        debt_parsed,
        account,
        debt_type_for_payment=debt_type_for_payment,
    )

    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or "-"
    amount = debt_parsed.get("amount") or 0
    raw = debt_parsed.get("raw_input") or "-"

    if intent == "add_receivable":
        title = "🟢 *Piutang Baru*"
        debt_effect = f"{md_safe(person)} meminjam uang dari Anda."
    elif intent == "add_payable":
        title = "🔴 *Utang Baru*"
        debt_effect = f"Anda meminjam / punya utang ke {md_safe(person)}."
    elif intent == "add_payment":
        title = "💸 *Pembayaran Utang/Piutang*"
        debt_effect = f"Pembayaran terkait saldo aktif dengan {md_safe(person)}."
    elif intent == "offset_debt":
        title = "🔁 *Kompensasi Hutang/Piutang*"
        target_label = "piutang" if debt_parsed.get("target_debt_type") == "receivable" else "utang"
        debt_effect = f"Memotong {target_label} aktif dengan {md_safe(person)} tanpa uang masuk/keluar."
    else:
        title = "❓ *Debt*"
        debt_effect = "-"

    cashflow_type = {
        "expense": "❌ Pengeluaran",
        "income": "✅ Cash In / Pemasukan",
        "transfer": "🔄 Transfer",
        "debt_offset": "🔁 Debt Offset / Tanpa Rekening",
        "debt_only": "📝 Debt Fact / Tanpa Rekening",
    }.get(transaction_parsed.get("type"), "❓")
    if transaction_parsed.get("type") == "expense" and transaction_parsed.get("skip_account"):
        cashflow_type = "❌ Pengeluaran / tanpa update saldo rekening"

    return (
        f"{title}\n\n"
        f"👤 Subjek : {md_safe(person)}\n"
        f"💰 Nominal: {format_rupiah(amount)}\n"
        f"🏦 Rekening: {md_safe(account)}\n"
        f"📝 Input  : `{md_safe(raw)}`\n\n"
        f"*Efek Debt:*\n"
        f"{debt_effect}\n\n"
        f"*Efek Transactions:*\n"
        f"{cashflow_type}\n"
        f"📁 Kategori: {md_safe(transaction_parsed.get('category') or '-')}\n"
        f"📝 Deskripsi: {md_safe(transaction_parsed.get('description') or '-')}\n\n"
        f"Simpan utang/piutang ini?"
    )

def build_debt_batch_confirm_preview(
    debt_items: list[dict],
    account: str,
) -> str:
    """Build the data structure or message text for debt batch confirm preview."""
    lines = ["🧾 *Preview Batch Utang/Piutang*\n"]

    total_cash_in = 0
    total_cash_out = 0

    for i, item in enumerate(debt_items, 1):
        parsed = item["parsed"]
        intent = parsed.get("intent")
        person = parsed.get("person_name") or "-"
        amount = float(parsed.get("amount", 0) or 0)
        raw = item.get("raw") or parsed.get("raw_input") or "-"

        debt_type_for_payment = parsed.get("debt_type_for_payment")
        transaction_parsed = build_debt_cashflow_transaction(
            parsed,
            account,
            debt_type_for_payment=debt_type_for_payment,
        )

        txn_type = transaction_parsed.get("type")
        category = transaction_parsed.get("category") or "-"

        if txn_type == "income":
            cashflow_label = "✅ Cash In"
            total_cash_in += amount
        elif txn_type == "expense":
            if transaction_parsed.get("skip_account"):
                cashflow_label = "❌ Expense fact / tanpa update saldo"
            else:
                cashflow_label = "❌ Cash Out"
                total_cash_out += amount
        elif txn_type == "debt_offset":
            cashflow_label = "🔁 Debt Offset / tanpa rekening"
        elif txn_type == "debt_only":
            cashflow_label = "📝 Debt fact / tanpa rekening"
        else:
            cashflow_label = "❓ Cashflow belum pasti"

        if intent == "add_receivable":
            debt_label = "🟢 Piutang Baru"
        elif intent == "add_payable":
            debt_label = "🔴 Utang Baru"
        elif intent == "add_payment":
            debt_label = "💸 Pembayaran"
        elif intent == "offset_debt":
            debt_label = "🔁 Kompensasi Debt"
        else:
            debt_label = "❓ Debt"

        lines.append(
            f"{i}. {debt_label}\n"
            f"   👤 Subjek : {person}\n"
            f"   💰 Nominal: {format_rupiah(amount)}\n"
            f"   🏦 Rekening: {account}\n"
            f"   📁 Kategori: {category}\n"
            f"   📌 Efek: {cashflow_label}\n"
            f"   📝 Input: `{raw}`"
        )

    lines.append("\n*Ringkasan Cashflow:*")
    lines.append(f"✅ Total Cash In : *{format_rupiah(total_cash_in)}*")
    lines.append(f"❌ Total Cash Out: *{format_rupiah(total_cash_out)}*")
    lines.append("\nSimpan semua utang/piutang ini?")

    return "\n".join(lines)

def build_debt_batch_account_prompt(debt_items: list[dict]) -> str:
    """Build the data structure or message text for debt batch account prompt."""
    lines = [f"🧾 *Ditemukan {len(debt_items)} input utang/piutang:*\n"]

    total_cash_in = 0
    total_cash_out = 0

    for i, item in enumerate(debt_items, 1):
        parsed = item["parsed"]
        intent = parsed.get("intent")
        person = parsed.get("person_name") or "-"
        amount = float(parsed.get("amount", 0) or 0)

        if intent == "add_receivable":
            label = "🟢 Piutang Baru"
            effect = "cash out"
            total_cash_out += amount

        elif intent == "add_payable":
            label = "🔴 Utang Baru"
            effect = "cash in"
            total_cash_in += amount

        elif intent == "add_payment":
            label = "💸 Pembayaran"
            effect = "mengikuti posisi debt aktif"

        elif intent == "offset_debt":
            label = "🔁 Kompensasi Debt"
            effect = "tanpa rekening, tetap masuk transactions"

        else:
            label = "❓ Debt"
            effect = "-"

        lines.append(
            f"{i}. {label}\n"
            f"   👤 {person}\n"
            f"   💰 {format_rupiah(amount)}\n"
            f"   📌 {effect}"
        )

    lines.append("\n*Estimasi cashflow awal:*")
    lines.append(f"✅ Cash In : *{format_rupiah(total_cash_in)}*")
    lines.append(f"❌ Cash Out: *{format_rupiah(total_cash_out)}*")
    lines.append("\n💳 Pilih rekening cashflow untuk semua item, atau pilih *Sudah berlalu* jika hanya ingin mencatat debt tanpa mengubah saldo:")

    return "\n".join(lines)


# ── Command Handlers ──────────────────────────────────────────────────────────

