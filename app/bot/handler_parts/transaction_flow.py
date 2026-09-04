"""Preview and state helpers for transaction, mixed input, debt, split bill, pending expense, asset, and edit flows."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *
from app.clock import business_now
from app.application.external_io import ExternalIOError, run_gemini
from app.nlp.gemini_parser import parse_batch_with_gemini, parse_with_pending_fallback
# Import app.bot.handler_parts.networth_assets so this module can use its helpers.
from app.bot.handler_parts.networth_assets import build_asset_confirm_preview
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import resolve_parsed_transaction
from app.services.debt_service import create_split_bill_receivables, validate_split_bill_receivables
# Import app.nlp.regex_parser so this module can use its helpers.
from app.nlp.regex_parser import detect_category, detect_account
# Import app.nlp.normalizer so this module can use its helpers.
from app.nlp.normalizer import normalize_text


# Helper for parse input.
def parse_input_local(text: str) -> dict | None:
    """Parse only deterministic local rules without invoking Gemini."""

    result = parse_with_regex(text)
    if isinstance(result, dict) and result.get("type") in {"expense", "income", "transfer"}:
        return resolve_parsed_transaction(result, text)
    return result


def parse_input(text: str) -> dict:
    """Backward-compatible synchronous parser used by CLI and offline callers."""

    result = parse_input_local(text)
    if result is None:
        result = parse_with_pending_fallback(text)
    return result


async def parse_input_async(text: str) -> dict:
    """Parse one Telegram input while keeping Gemini off the event loop."""

    result = parse_input_local(text)
    if result is not None:
        return result
    return await run_gemini("transaction_parser", parse_with_pending_fallback, text)


# Helper for build progress bar.
def build_progress_bar(pct: float, length: int = 10) -> str:
    """Build the data structure or message text for progress bar."""
    filled = int(min(float(pct or 0), 100) / 100 * length)
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"


# Helper for split user inputs.
def split_user_inputs(text: str) -> list[str]:
    """Coordinate the split user inputs logic in the Telegram handler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing text before continuing.
    if not text:
        return []

    # Prepare raw from the incoming input.
    raw = text.strip()

    raw = re.sub(r"[\n\r;]+", " ||| ", raw)
    raw = re.sub(r"\s*,\s*", " ||| ", raw)
    raw = re.sub(r"[ \t]+", " ", raw)

    # Starter transaction biasa
    transaction_starters = [
        "beli", "bayar", "byr", "jajan", "makan", "minum",
        "transfer", "top up", "topup", "isi", "ngisi",
        "gaji", "dapat", "dapet", "terima",
        "hutang", "utang",
    ]

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
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.

    # Prepare parts from the incoming input.
    parts = []
    for part in raw.split("|||"):
        clean = part.strip(" .,-;")
        if clean:
            # Append the current value to parts.
            parts.append(clean)

    return parts

# Helper for needs account.
def needs_account(parsed: dict) -> bool:
    """Evaluate the needs account condition in the Telegram handler layer.

    Args:
        parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    txn_type = parsed.get("type")

    if parsed.get("skip_account") and txn_type in ["expense", "income"]:
        return False

    if txn_type in ["expense", "income"] and not parsed.get("account"):
        return True

    if txn_type == "transfer" and (not parsed.get("account") or not parsed.get("to_account")):
        return True

    return False

# Helper for is debt item.
def is_debt_item(parsed: dict) -> bool:
    """Check whether a condition is true for debt item."""
    return parsed.get("kind") == "debt"


# Helper for is transaction item.
def is_transaction_item(parsed: dict) -> bool:
    """Check whether a condition is true for transaction item."""
    return parsed.get("kind") == "transaction"


# Helper for build mixed preview.
def build_mixed_preview(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed preview."""
    lines = [f"🧾 *Ditemukan {len(mixed_items)} item:*\n"]

    total_expense = 0
    total_income = 0
    total_debt = 0

    # Iterate through each i, item.
    for i, item in enumerate(mixed_items, 1):
        kind = item["kind"]
        raw = item["raw"]

        if kind == "transaction":
            parsed = item["parsed"]
            txn_type = parsed.get("type")
            amount = _receipt_amount(parsed.get("amount"), 0)

            if txn_type == "expense":
                icon = "❌"
                total_expense += amount
            elif txn_type == "income":
                icon = "✅"
                total_income += amount
            # Use the fallback path when no earlier branch matched.
            else:
                icon = "🔄"

            desc = md_safe(parsed.get('description') or '-')
            category = md_safe(parsed.get('category') or '-')
            account = md_safe(parsed.get('account') or '-')
            date = md_safe(parsed.get('date') or '-')
            # Prepare safe raw from the incoming input.
            safe_raw = md_safe(raw)
            # Build split preview for the response flow.
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
            amount = _receipt_amount(parsed.get("amount"), 0)
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
            # Use the fallback path when no earlier branch matched.
            else:
                label = "❓ Debt"
                effect = "-"

            # Extract safe person for validation.
            safe_person = md_safe(person)
            account = md_safe(parsed.get('account') or '-')
            date = md_safe(parsed.get('date') or parsed.get('transaction_date') or '-')
            # Prepare safe raw from the incoming input.
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
    lines.append(f"- Transaksi Expense: *{format_rupiah(total_expense)}*")
    lines.append(f"+ Transaksi Income : *{format_rupiah(total_income)}*")
    lines.append(f"💸 Total Nominal Debt: *{format_rupiah(total_debt)}*")

    # Extract account summary for validation.
    account_summary = build_account_delta_summary_from_transaction_items(mixed_items)
    if account_summary:
        # Append the current value to lines.
        lines.append(account_summary)

    return "\n".join(lines)



# Helper for mixed transaction totals.
def _mixed_transaction_totals(mixed_items: list[dict]) -> dict:
    """Summarize transaction and debt totals for a mixed preview."""
    totals = {
        "expense": 0.0,
        "income": 0.0,
        "transfer": 0.0,
        "debt": 0.0,
        "transaction_count": 0,
        "debt_count": 0,
    }
    # Iterate through each item.
    for item in mixed_items or []:
        kind = item.get("kind") if isinstance(item, dict) else None
        parsed = item.get("parsed", {}) if isinstance(item, dict) else {}
        amount = _receipt_amount(parsed.get("amount"), 0)
        if kind == "transaction":
            totals["transaction_count"] += 1
            txn_type = parsed.get("type")
            if txn_type == "expense":
                totals["expense"] += amount
            elif txn_type == "income":
                totals["income"] += amount
            elif txn_type == "transfer":
                totals["transfer"] += amount
        elif kind == "debt":
            totals["debt_count"] += 1
            totals["debt"] += amount
    return totals


# Helper for build mixed category summary.
def build_mixed_category_summary(mixed_items: list[dict]) -> str:
    """Build a compact category summary for the final mixed preview."""
    summary: dict[str, dict[str, float | int]] = {}
    # Iterate through each item.
    for item in mixed_items or []:
        if not isinstance(item, dict) or item.get("kind") != "transaction":
            # Skip the rest of this loop iteration after handling this case.
            continue
        parsed = item.get("parsed", {}) or {}
        if parsed.get("type") not in ["expense", "income"]:
            # Skip the rest of this loop iteration after handling this case.
            continue
        category = str(parsed.get("category") or "Tanpa kategori").strip() or "Tanpa kategori"
        bucket = summary.setdefault(category, {"amount": 0.0, "count": 0})
        bucket["amount"] = float(bucket["amount"] or 0) + _receipt_amount(parsed.get("amount"), 0)
        bucket["count"] = int(bucket["count"] or 0) + 1

    # Validate missing summary before continuing.
    if not summary:
        return ""

    lines = ["📁 *Ringkasan kategori:*"]
    # Iterate through each category, data.
    for category, data in sorted(summary.items(), key=lambda kv: str(kv[0]).lower()):
        lines.append(
            f"• {md_safe(category)}: *{format_rupiah(float(data['amount'] or 0))}* "
            f"({int(data['count'] or 0)} item)"
        )
    return "\n".join(lines)


# Helper for mixed item detail lines.
def _mixed_item_detail_lines(item: dict, index: int) -> list[str]:
    """Build detailed lines for one mixed item before account selection."""
    kind = item.get("kind") if isinstance(item, dict) else None
    parsed = item.get("parsed", {}) if isinstance(item, dict) else {}

    if kind == "transaction":
        type_label = {
            "expense": "- Pengeluaran",
            "income": "+ Pemasukan",
            "transfer": "🔄 Transfer",
        }.get(parsed.get("type"), "❓ Transaksi")
        lines = [f"{index}. *{type_label}*"]
        lines.append(f"   💰 Nominal : {format_rupiah(_receipt_amount(parsed.get('amount'), 0))}")
        lines.append(f"   📁 Kategori: {md_safe(parsed.get('category') or '-')}")
        lines.append(f"   👤 Subjek  : {md_safe(parsed.get('subject') or '-')}")
        lines.append(f"   📝 Deskripsi: {md_safe(parsed.get('description') or '-')}")
        # Build split preview for the response flow.
        split_preview = format_split_bill_preview_line(parsed)
        if split_preview:
            lines.append(f"   {md_safe(split_preview)}")
        if parsed.get("catatan"):
            lines.append(f"   🗒️ Catatan : {md_safe(parsed.get('catatan'))}")
        if parsed.get("tipe_pengeluaran"):
            lines.append(f"   🏷️ Tipe    : {md_safe(parsed.get('tipe_pengeluaran'))}")
        lines.append(f"   📅 Tanggal : {md_safe(parsed.get('date') or '-')}")
        lines.append(f"   🏦 Rekening: {md_safe(parsed.get('account') or '-')}")
        if parsed.get("to_account"):
            lines.append(f"   ➡️ Ke Rekening: {md_safe(parsed.get('to_account'))}")
        return lines

    if kind == "debt":
        intent = parsed.get("intent")
        label = {
            "add_receivable": "🟢 Piutang baru",
            "add_payable": "🔴 Utang baru",
            "add_payment": "💸 Pembayaran debt",
            "offset_debt": "🔁 Kompensasi debt",
        }.get(intent, "💸 Debt")
        return [
            f"{index}. *{label}*",
            f"   👤 Orang   : {md_safe(parsed.get('person_name') or '-')}",
            f"   💰 Nominal : {format_rupiah(_receipt_amount(parsed.get('amount'), 0))}",
            f"   📝 Deskripsi: {md_safe(parsed.get('description') or '-')}",
            f"   📅 Tanggal : {md_safe(parsed.get('date') or parsed.get('transaction_date') or '-')}",
            f"   🏦 Rekening: {md_safe(parsed.get('account') or '-')}",
        ]

    return [f"{index}. {md_safe(item.get('raw') or '-')}"]


# Helper for build mixed detail preview.
def build_mixed_detail_preview(mixed_items: list[dict], receipt_context: dict | None = None) -> str:
    """Build the detailed multi-input preview shown before rekening selection."""
    # Prepare receipt context from the incoming input.
    receipt_context = receipt_context or {}

    # Natural multi-input should use the compact preview format from the flow doc.
    # Keep receipt/batch preview below because receipt mode still needs merchant and extra-charge details.
    if not receipt_context:
        return build_batch_preview(mixed_items)

    receipt = receipt_context.get("receipt") or {}
    merchant = _receipt_merchant(receipt, [item.get("parsed", {}) for item in mixed_items])
    totals = _mixed_transaction_totals(mixed_items)

    mode_label = "semua struk" if receipt_context.get("mode") == "all" else "bagian struk"
    lines = [f"🧾 *Preview detail batch dari {mode_label}*"]
    lines.append(f"• Merchant: *{md_safe(merchant)}*")

    lines.append(f"• Total item: *{len(mixed_items or [])}*")
    if totals["expense"]:
        lines.append(f"• Expense: *{format_rupiah(totals['expense'])}*")
    if totals["income"]:
        lines.append(f"• Income: *{format_rupiah(totals['income'])}*")
    if totals["transfer"]:
        lines.append(f"• Transfer: *{format_rupiah(totals['transfer'])}*")
    if totals["debt_count"]:
        lines.append(f"• Debt: *{int(totals['debt_count'])} item* / {format_rupiah(totals['debt'])}")

    if receipt_context.get("mode") == "partial":
        lines.append(f"• Subtotal item kamu: {format_rupiah(receipt_context.get('subtotal_items', 0))}")
        lines.append(f"• Biaya tambahan kamu: {format_rupiah(receipt_context.get('extra_charge_amount', 0))}")

    # Extract category summary for validation.
    category_summary = build_mixed_category_summary(mixed_items)
    if category_summary:
        lines.extend(["", category_summary])

    lines.append("")
    lines.append("📋 *Rincian transaksi yang akan disimpan:*")
    # Iterate through each idx, item.
    for idx, item in enumerate(mixed_items or [], 1):
        # Append the current value to lines.
        lines.extend(_mixed_item_detail_lines(item, idx))
        if idx != len(mixed_items or []):
            lines.append("")

    charges = _receipt_extra_charges(receipt)
    if charges:
        lines.extend(["", "💳 *Rincian biaya tambahan di output:*"])
        divisor = receipt_context.get("extra_charge_divisor")
        # Iterate through each charge.
        for charge in charges:
            amount = int(charge.get("amount", 0) or 0)
            sign = "-" if charge.get("is_discount") else ""
            if divisor and divisor > 1:
                share = int(round(amount / divisor))
                lines.append(
                    f"• {md_safe(charge.get('label'))}: {sign}{format_rupiah(amount)} / {divisor} = {sign}{format_rupiah(share)}"
                )
            # Use the fallback path when no earlier branch matched.
            else:
                lines.append(f"• {md_safe(charge.get('label'))}: {sign}{format_rupiah(amount)}")
        lines.append(f"• Total biaya tambahan kamu: *{format_rupiah(receipt_context.get('extra_charge_amount', 0))}*")
        lines.append("\nCatatan: saat disimpan, service/PPN/diskon digabung menjadi satu transaksi biaya tambahan.")

    return "\n".join(lines)


# Helper for build mixed final summary.
def build_mixed_final_summary(mixed_items: list[dict], receipt_context: dict | None = None, account_label: str | None = None) -> str:
    """Build a compact final confirmation summary for mixed or receipt batches."""
    # Prepare receipt context from the incoming input.
    receipt_context = receipt_context or {}
    receipt = receipt_context.get("receipt") or {}
    merchant = _receipt_merchant(receipt, [item.get("parsed", {}) for item in mixed_items]) if receipt_context else ""
    totals = _mixed_transaction_totals(mixed_items)

    if receipt_context:
        mode_label = "semua struk" if receipt_context.get("mode") == "all" else "bagian struk"
        lines = [f"🧾 *Ringkasan batch dari {mode_label}*"]
        lines.append(f"• Merchant: *{md_safe(merchant)}*")
    # Use the fallback path when no earlier branch matched.
    else:
        lines = ["🧾 *Ringkasan batch:*"]

    lines.append(f"• Total item: *{len(mixed_items or [])}*")
    if totals["transaction_count"]:
        lines.append(f"• Transaksi: *{int(totals['transaction_count'])} item*")
    if totals["expense"]:
        lines.append(f"• Expense: *{format_rupiah(totals['expense'])}*")
    if totals["income"]:
        lines.append(f"• Income: *{format_rupiah(totals['income'])}*")
    if totals["transfer"]:
        lines.append(f"• Transfer: *{format_rupiah(totals['transfer'])}*")
    if totals["debt_count"]:
        lines.append(f"• Debt: *{int(totals['debt_count'])} item* / {format_rupiah(totals['debt'])}")

    # Extract account for validation.
    account = account_label
    # Validate missing account before continuing.
    if not account:
        # Iterate through each item.
        for item in mixed_items or []:
            parsed = item.get("parsed", {}) if isinstance(item, dict) else {}
            if parsed.get("account"):
                account = parsed.get("account")
                # Leave the loop after the target condition has been reached.
                break
    if account:
        lines.append(f"• Rekening: {md_safe(account)}")

    # Extract category summary for validation.
    category_summary = build_mixed_category_summary(mixed_items)
    if category_summary:
        lines.extend(["", category_summary])

    # Extract account summary for validation.
    account_summary = build_account_delta_summary_from_transaction_items(mixed_items)
    if account_summary:
        lines.extend(["", account_summary])

    return "\n".join(lines)

# Helper for parse income missing amount.
def parse_income_missing_amount(line: str) -> dict | None:
    """Parse caller input for the parse income missing amount workflow in the Telegram handler layer.

    Args:
        line: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = str(line or "").strip()
    # Validate missing raw before continuing.
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
    # Validate missing match before continuing.
    if not match:
        expense_like = re.search(
            r"\b(?:beli|bayar|byr|jajan|makan|minum|ngopi|belanja|isi|top\s*up|topup)\b",
            raw,
            flags=re.IGNORECASE,
        )
        # Validate missing expense like before continuing.
        if not expense_like:
            return None

        description = strip_date_phrases(raw)
        description = re.sub(r"\b(?:dari|via|pakai|pake|ke|rekening)\s+[A-Za-zÀ-ÿ0-9\s]+$", " ", description, flags=re.IGNORECASE)
        description = re.sub(r"^\s*(?:beli|bayar|byr|jajan|makan|minum|ngopi|belanja|isi|top\s*up|topup)\s+", " ", description, flags=re.IGNORECASE)
        description = re.sub(r"\s+", " ", description).strip(" .,-;") or "Expense"
        return {
            "type": "expense",
            "amount": None,
            "category": detect_category(raw, "expense"),
            "account": detect_account(raw),
            "to_account": None,
            "subject": description.title(),
            "description": description.title(),
            "catatan": raw,
            "tipe_pengeluaran": "Harian",
            "date": detect_date(raw),
            "parsed_by": "missing_amount",
            "needs_amount": True,
        }

    # Extract person raw for validation.
    person_raw = match.group(1).strip()
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    person_raw = re.sub(r"\b(?:tgl|tanggal)\s*\d{1,2}(?:[-/]\d{1,2}(?:[-/]\d{2,4})?)?\b", " ", person_raw, flags=re.IGNORECASE)
    person_raw = re.sub(r"\b(?:hari\s+ini|kemarin|besok)\b", " ", person_raw, flags=re.IGNORECASE)
    person = re.sub(r"\s+", " ", person_raw).strip(" .,-;")

    # Validate missing person before continuing.
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


# Helper for build missing amount prompt.
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
    # Handle current is not None and total is not None and total > 1.
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


# Helper for finalize missing amount item.
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


# Handle the asynchronous continue after missing amount mixed workflow.
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

    # Build preview for the response flow.
    preview = build_mixed_detail_preview(mixed_items)

    if mixed_split_bill_needs_decision(mixed_items):
        # Send the Telegram response before continuing.
        await reply_update_safely(
            update,
            build_mixed_split_bill_queue_prompt(mixed_items),
            parse_mode="Markdown",
            reply_markup=mixed_split_bill_keyboard(mixed_items),
        )
    # Use the fallback path when no earlier branch matched.
    else:
        # Send the Telegram response before continuing.
        await reply_update_safely(
            update,
            f"{preview}\n\n{preview_action_question(False)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", False),
        )


# Handle the asynchronous handle pending missing amount workflow.
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
    # Validate missing state before continuing.
    if not state:
        return False

    # Extract amount for validation.
    amount = parse_human_amount(user_text)
    # Validate missing amount or amount <= 0 before continuing.
    if not amount or amount <= 0:
        # Send the Telegram response before continuing.
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
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                build_missing_amount_prompt(next_item.get("raw", ""), next_item.get("parsed", {}), current + 1, len(missing_indices)),
                parse_mode="Markdown",
            )
            return True

        context.user_data.pop("pending_missing_amount", None)
        # Await continue after missing amount mixed before continuing.
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
            # Send the Telegram response before continuing.
            await reply_update_safely(
                update,
                build_single_account_prompt(parsed),
                parse_mode="Markdown",
                reply_markup=account_keyboard("acc"),
            )
            return True

        # Build preview for the response flow.
        preview = build_preview(parsed)
        # Send the Telegram response before continuing.
        await reply_update_safely(
            update,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("single", True),
        )
        return True

    context.user_data.pop("pending_missing_amount", None)
    return False


# Helper for parse mixed item.
def parse_mixed_item_local(line: str) -> dict:
    """Parse one mixed item without invoking Gemini."""

    clean = normalize_text(line)
    if re.search(r"^(?:tidak\s+jadi|nggak\s+jadi|ga\s+jadi|batal)\b|\b(?:tapi|namun)\s+batal\b|\bbatal\s*$", clean):
        return {"kind": "ignored", "parsed": {}, "raw": line}

    debt_parsed = parse_debt_input(line)
    if debt_parsed:
        debt_parsed = enrich_ditalangin_split_bill_if_any(debt_parsed, line)
        return {"kind": "debt", "parsed": debt_parsed, "raw": line}

    missing_amount_income = parse_income_missing_amount(line)
    if missing_amount_income:
        return {"kind": "missing_amount", "parsed": missing_amount_income, "raw": line}

    txn_parsed = parse_input_local(line)
    if txn_parsed and txn_parsed.get("type") != "pending":
        attach_split_bill_if_any(txn_parsed, line)
        return {"kind": "transaction", "parsed": txn_parsed, "raw": line}

    return {"kind": "failed", "parsed": {}, "raw": line}


def parse_mixed_item(line: str) -> dict:
    """Backward-compatible mixed parser with a synchronous Gemini fallback."""

    local = parse_mixed_item_local(line)
    if local.get("kind") != "failed":
        return local
    txn_parsed = parse_input(line)
    if txn_parsed and txn_parsed.get("type") != "pending":
        attach_split_bill_if_any(txn_parsed, line)
        return {"kind": "transaction", "parsed": txn_parsed, "raw": line}
    return local


async def parse_mixed_item_async(line: str) -> dict:
    """Parse one rewritten bulk item without blocking the event loop."""

    local = parse_mixed_item_local(line)
    if local.get("kind") != "failed":
        return local
    txn_parsed = await run_gemini("transaction_parser", parse_with_pending_fallback, line)
    if txn_parsed and txn_parsed.get("type") != "pending":
        attach_split_bill_if_any(txn_parsed, line)
        return {"kind": "transaction", "parsed": txn_parsed, "raw": line}
    return local


async def parse_mixed_items_batch(input_lines: list[str]) -> list[dict]:
    """Parse unresolved bulk lines with one shared Gemini batch invocation."""

    items = [parse_mixed_item_local(line) for line in input_lines]
    unresolved_positions = [index for index, item in enumerate(items) if item.get("kind") == "failed"]
    if not unresolved_positions:
        return items

    unresolved_inputs = [input_lines[index] for index in unresolved_positions]
    try:
        parsed_by_position = await run_gemini(
            "transaction_batch_parser",
            parse_batch_with_gemini,
            unresolved_inputs,
        )
    except ExternalIOError:
        # Keep unresolved items in the normal clarification flow when the
        # governed Gemini worker is unavailable, saturated, or times out.
        return items
    for batch_index, parsed in parsed_by_position.items():
        if batch_index < 0 or batch_index >= len(unresolved_positions):
            continue
        original_index = unresolved_positions[batch_index]
        attach_split_bill_if_any(parsed, input_lines[original_index])
        items[original_index] = {
            "kind": "transaction",
            "parsed": parsed,
            "raw": input_lines[original_index],
        }
    return items


# Helper for mixed needs account.
def mixed_needs_account(mixed_items: list[dict]) -> bool:
    """Check whether a mixed input still needs a rekening selection.

    Args:
        mixed_items: Parsed mixed items from one user input. Each item may be a
            normal transaction or a debt-related item.

    Returns:
        True if at least one cashflow item has no rekening yet, otherwise False.
    """
    # Iterate through each item.
    for item in mixed_items:
        parsed = item["parsed"]

        if item["kind"] == "transaction" and needs_account(parsed):
            return True

        if item["kind"] == "debt" and debt_uses_cashflow(parsed) and not parsed.get("account"):
            return True

    return False


# Helper for edit or continue keyboard.
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


# Helper for confirm target for edit scope.
def _confirm_target_for_edit_scope(scope: str) -> str:
    """Map a preview edit scope to the confirm callback target.

    Args:
        scope: Current preview scope. The `single` scope is stored as
            `pending_parsed`, but its save callback still uses `confirm:pending`.

    Returns:
        Callback target used by the save button.
    """
    return "pending" if scope == "single" else scope


# Helper for save edit cancel keyboard.
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
    from app.bot.pending_actions import create_bound_preview_action

    action = create_bound_preview_action(scope, confirm_target)
    if action:
        action_id = action["action_id"]
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Simpan", callback_data=f"confirm:{action_id}"),
                InlineKeyboardButton("✏️ Edit dulu", callback_data=f"editflow:edit:{scope}"),
            ],
            [InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{action_id}")],
        ])

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Simpan", callback_data=f"confirm:{confirm_target}"),
            InlineKeyboardButton("✏️ Edit dulu", callback_data=f"editflow:edit:{scope}"),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")],
    ])


# Helper for preview action keyboard.
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


# Helper for preview action question.
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


# Helper for single ready to save.
def single_ready_to_save(parsed: dict) -> bool:
    """Check whether a single transaction preview can be saved.

    Args:
        parsed: Parsed transaction candidate.

    Returns:
        True when the transaction no longer needs split bill or rekening
        decisions.
    """
    return not split_bill_needs_decision(parsed) and not needs_account(parsed)


# Helper for mixed ready to save.
def mixed_ready_to_save(mixed_items: list[dict]) -> bool:
    """Check whether a mixed input preview can be saved.

    Args:
        mixed_items: Parsed items from a multi-line or mixed natural input.

    Returns:
        True when every item has completed the required split bill and rekening
        decisions.
    """
    return not mixed_split_bill_needs_decision(mixed_items) and not mixed_needs_account(mixed_items)


# Helper for debt ready to save.
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
    # Use the fallback path when no earlier branch matched.
    else:
        lines = ["⚠️ *Saya agak ragu dengan hasil parsing ini.*"]

    if reasons:
        lines.append("\n*Alasan:*")
        # Iterate through each reason.
        for reason in reasons[:4]:
            lines.append(f"• {md_safe(reason)}")

    return "\n".join(lines)


def build_preview_with_parse_safety(parsed: dict, assessment: dict, mode: str = "warning") -> str:
    """Build the data structure or message text for preview with parse safety."""
    return f"{build_parse_safety_notice(assessment, mode)}\n\n{build_preview(parsed)}"


# Helper for build pending expense confirm preview.
def build_pending_expense_confirm_preview(item: dict, include_question: bool = True) -> str:
    """Build the data structure or message text for pending expense confirm preview."""
    item = dict(item or {})
    due_date = str(item.get("due_date") or "").strip()
    due_precision = str(item.get("due_precision") or "unknown").strip().lower()
    month = str(item.get("month") or "-").strip()
    if due_date:
        # Prepare due text from the incoming input.
        due_text = due_date
    elif due_precision == "month":
        due_text = f"{month} (tanggal belum pasti)"
    # Use the fallback path when no earlier branch matched.
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


# Helper for parse clarification keyboard.
def parse_clarification_keyboard() -> InlineKeyboardMarkup:
    """Parse caller input for the parse clarification keyboard workflow in the Telegram handler layer.

    Args:
        None.

    Returns:
        `InlineKeyboardMarkup` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("+ Orang ini bayar ke saya", callback_data="clarify_parse:debt_payment")],
        [InlineKeyboardButton("- Saya hutang ke orang ini", callback_data="clarify_parse:payable")],
        [InlineKeyboardButton("- Pengeluaran biasa", callback_data="clarify_parse:expense")],
        [InlineKeyboardButton("∅ Orang lain yang bayar", callback_data="clarify_parse:no_cashflow")],
        [InlineKeyboardButton("🤝 Split bill", callback_data="clarify_parse:split")],
        [InlineKeyboardButton("🙋 Saya talangin", callback_data="clarify_parse:fronting")],
        [InlineKeyboardButton("✍️ Tulis ulang", callback_data="clarify_parse:rewrite")],
        [InlineKeyboardButton("🚫 Batal", callback_data="cancel:clarification")],
    ])


# Helper for build parse clarification prompt.
def build_parse_clarification_prompt(raw: str, assessment: dict | None = None) -> str:
    """Build the data structure or message text for parse clarification prompt."""
    # Prepare safe raw from the incoming input.
    safe_raw = md_safe(raw)
    lines = [
        "🤔 *Saya belum yakin maksud input ini:*",
        "",
        f'"{safe_raw}"',
    ]

    reasons = [str(r).strip() for r in (assessment or {}).get("reasons", []) if str(r).strip()]
    if reasons:
        lines.append("\n*Kenapa ditanya dulu:*")
        # Iterate through each reason.
        for reason in reasons[:3]:
            lines.append(f"• {md_safe(reason)}")

    lines.extend([
        "",
        "Maksudnya yang mana?",
        "• 🟢 Orang ini bayar ke saya",
        "• 🔴 Saya hutang ke orang ini",
        "• 🧾 Pengeluaran biasa",
        "• 👤 Orang lain yang bayar",
        "• 🤝 Split bill",
        "• 🙋 Saya talangin",
        "• ✍️ Tulis ulang",
        "• 🚫 Batal",
    ])
    return "\n".join(lines)



# ── Phase 2: social-money ambiguity and split bill wizard helpers ─────────────

SOCIAL_MEAL_KEYWORDS = r"(?:makan|minum|ngopi|lunch|dinner|brunch|jajan)"
SOCIAL_FRIEND_MARKER = r"(?:bareng|sama|dengan|ama)"


# Helper for extract people from social input.
def extract_people_from_social_input(raw: str) -> list[str]:
    """Coordinate the extract people from social input logic in the Telegram handler layer.

    Args:
        raw: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    clean = str(raw or "").strip()
    # Validate missing clean before continuing.
    if not clean:
        return []

    match = re.search(
        rf"\b{SOCIAL_FRIEND_MARKER}\s+(?P<names>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{{0,100}}?)(?=\s*(?:\d|rp|idr|tanggal|tgl|kemarin|hari\s+ini|besok|dari|via|pakai|pake|$))",
        clean,
        flags=re.IGNORECASE,
    )
    # Validate missing match before continuing.
    if not match:
        match = re.search(
            rf"\b{SOCIAL_MEAL_KEYWORDS}\s+{SOCIAL_FRIEND_MARKER}\s+(?P<names>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{{0,100}}?)(?=\s*(?:\d|rp|idr|tanggal|tgl|kemarin|hari\s+ini|besok|dari|via|pakai|pake|$))",
            clean,
            flags=re.IGNORECASE,
        )
    # Validate missing match before continuing.
    if not match:
        return []

    names = split_split_bill_person_names(match.group("names") or "")
    noise = {"makan", "minum", "ngopi", "lunch", "dinner", "brunch", "jajan"}
    # Build result for the response flow.
    result = []
    seen = set()
    # Iterate through each name.
    for name in names:
        key = normalize_text(name)
        # Validate missing key or key in noise or key in seen before continuing.
        if not key or key in noise or key in seen:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Append the current value to result.
        result.append(str(name).strip().title())
        # Append the current value to seen.
        seen.add(key)
    return result


# Helper for detect social spending ambiguity.
def detect_social_spending_ambiguity(raw: str) -> dict | None:
    """Detect inputs like `Makan bareng Budi 80k` that need a guard."""
    # Normalize clean before matching.
    clean = normalize_text(raw)
    # Validate missing clean or not extract amount from text(clean) before continuing.
    if not clean or not extract_amount_from_text(clean):
        return None

    # Explicit intent should stay in the debt/split flow and not be caught here.
    if re.search(r"\b(?:hutang|utang|piutang|minjem|pinjem|pinjam|talangin|ditalangin|nitip|dibayarin|duluin|bayar\s+(?:hutang|utang)|split\s*bill|split|ptpt|patungan|dibagi|bagi|berdua|bertiga|berempat)\b", clean, flags=re.IGNORECASE):
        return None

    has_social_phrase = bool(re.search(rf"\b{SOCIAL_MEAL_KEYWORDS}\b.*\b{SOCIAL_FRIEND_MARKER}\b|\b{SOCIAL_FRIEND_MARKER}\s+[a-zA-ZÀ-ÿ]+", clean, flags=re.IGNORECASE))
    # Validate missing has social phrase before continuing.
    if not has_social_phrase:
        return None

    people = extract_people_from_social_input(raw)
    # Validate missing people before continuing.
    if not people:
        return None

    parsed = parse_with_regex(raw) or {}
    if parsed.get("type") != "expense":
        return None

    amount = float(parsed.get("amount") or parse_human_amount(raw) or 0)
    if amount <= 0:
        return None

    return {
        "raw": raw,
        "people": people,
        "amount": amount,
        "parsed": parsed,
    }


# Helper for social spending guard keyboard.
def social_spending_guard_keyboard() -> InlineKeyboardMarkup:
    """Coordinate the social spending guard keyboard logic in the Telegram handler layer.

    Args:
        None.

    Returns:
        `InlineKeyboardMarkup` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤝 Split bill", callback_data="meal_guard:split")],
        [InlineKeyboardButton("- Pengeluaran biasa", callback_data="meal_guard:expense")],
        [InlineKeyboardButton("✍️ Tulis ulang", callback_data="meal_guard:rewrite")],
        [InlineKeyboardButton("🚫 Batal", callback_data="cancel:meal_guard")],
    ])


# Helper for build social spending guard prompt.
def build_social_spending_guard_prompt(raw: str, guard: dict) -> str:
    """Build a concise guard prompt for ambiguous social spending."""
    people_text = ", ".join(guard.get("people") or []) or "teman"
    amount = float(guard.get("amount") or 0)
    return (
        "🤔 *Input ini terlihat seperti makan/bareng orang lain.*\n\n"
        f"Input: `{md_safe(raw)}`\n"
        f"Total: *{format_rupiah(amount)}*\n"
        f"Orang terdeteksi: *kamu dan {md_safe(people_text)}*\n\n"
        "Mau dicatat sebagai split bill atau pengeluaran biasa?\n\n"
        "Kalau pengeluaran biasa, transaksi akan dicatat sebagai pengeluaran pribadi "
        f"dengan catatan makan bareng/traktir {md_safe(people_text)}."
    )


# Helper for build social spending expense.
def build_social_spending_expense(raw: str, guard: dict) -> dict:
    """Convert ambiguous social spending into a normal personal expense."""
    parsed = dict((guard or {}).get("parsed") or parse_with_regex(raw) or {})
    amount = float(parsed.get("amount") or (guard or {}).get("amount") or parse_human_amount(raw) or 0)
    people = (guard or {}).get("people") or extract_people_from_social_input(raw)
    people_text = ", ".join(people) if people else "teman"
    subject = f"Makan bareng {people_text}" if people else (parsed.get("subject") or "Makan bareng")

    parsed.update({
        "type": "expense",
        "amount": amount,
        "category": parsed.get("category") or detect_category(raw, "expense"),
        "subject": subject,
        "description": subject,
        "catatan": f"Dicatat sebagai pengeluaran biasa / traktir {people_text}",
        "date": parsed.get("date") or detect_date(raw),
        "parsed_by": parsed.get("parsed_by") or "social_guard",
    })
    parsed.pop("split_bill", None)
    return parsed


# Helper for meal split payer keyboard.
def split_wizard_keyboard(
    stage: str,
    callbacks: dict[str, str],
    *,
    cancel_callback: str,
    rewrite_callback: str | None = None,
) -> InlineKeyboardMarkup:
    """Build the shared split-bill wizard keyboard for single and bulk flows.

    Args:
        stage: One of ``payer``, ``allocation``, or ``status``.
        callbacks: Callback data keyed by the choices available at that stage.
        cancel_callback: Callback data for cancelling the active flow.
        rewrite_callback: Optional callback data for rewriting the source input.

    Returns:
        A consistent Telegram keyboard for the requested wizard stage.

    Side effects:
        None.

    Flow constraints:
        This helper only builds controls. Callers retain their own scoped state
        and must still show a final preview before any finance write.
    """
    choices = {
        "payer": [("🙋 Saya yang bayar", "self"), ("👤 Bukan saya yang bayar", "other")],
        "allocation": [("⚖️ Bagi rata", "equal"), ("📊 Atur pembagian", "custom")],
        "status": [("✅ Sudah dibayar", "paid"), ("⏳ Belum dibayar", "unpaid")],
    }.get(stage)
    if choices is None:
        raise ValueError(f"Tahap split bill tidak dikenal: {stage}")

    if stage == "status":
        rows = [[InlineKeyboardButton(label, callback_data=callbacks[key]) for label, key in choices]]
    else:
        rows = [[InlineKeyboardButton(label, callback_data=callbacks[key])] for label, key in choices]
    if rewrite_callback:
        rows.append([InlineKeyboardButton("✍️ Tulis ulang", callback_data=rewrite_callback)])
    rows.append([InlineKeyboardButton("🚫 Batal", callback_data=cancel_callback)])
    return InlineKeyboardMarkup(rows)


# Helper for meal split payer keyboard.
def meal_split_payer_keyboard() -> InlineKeyboardMarkup:
    """Coordinate the meal split payer keyboard logic in the Telegram handler layer.

    Args:
        None.

    Returns:
        `InlineKeyboardMarkup` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    return split_wizard_keyboard(
        "payer",
        {"self": "meal_split:payer:self", "other": "meal_split:payer:other"},
        cancel_callback="cancel:meal_split",
        rewrite_callback="meal_guard:rewrite",
    )


# Helper for build meal split payer prompt.
def build_meal_split_payer_prompt(guard: dict) -> str:
    """Prompt for payer step in social split bill."""
    people = guard.get("people") or []
    people_text = ", ".join(people) or "teman"
    return (
        "Siapa yang membayar transaksi ini di awal?\n\n"
        f"Total transaksi: *{format_rupiah(guard.get('amount') or 0)}*\n"
        f"Orang yang terdeteksi: *kamu dan {md_safe(people_text)}*"
    )


# Helper for meal split allocation keyboard.
def meal_split_allocation_keyboard() -> InlineKeyboardMarkup:
    """Ask whether split bill is equal or custom."""
    return split_wizard_keyboard(
        "allocation",
        {"equal": "meal_split:allocation:equal", "custom": "meal_split:allocation:custom"},
        cancel_callback="cancel:meal_split",
        rewrite_callback="meal_guard:rewrite",
    )


# Helper for build meal split allocation prompt.
def build_meal_split_allocation_prompt(state: dict) -> str:
    """Prompt for allocation step in social split bill."""
    people = state.get("people") or []
    people_text = ", ".join(people) or "teman"
    return (
        "Pembagiannya gimana?\n\n"
        f"Total transaksi: *{format_rupiah(state.get('amount') or 0)}*\n"
        f"Orang yang terdeteksi: *kamu dan {md_safe(people_text)}*"
    )


# Helper for build meal split custom allocation prompt.
def build_meal_split_custom_allocation_prompt(state: dict) -> str:
    """Build structured output for the build meal split custom allocation prompt workflow in the Telegram handler layer.

    Args:
        state: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    people = state.get("people") or []
    people_text = ", ".join(people) or "Budi"
    return (
        "Tulis pembagiannya dalam satu pesan.\n\n"
        "Bisa pakai bobot persen atau nominal langsung.\n\n"
        f"Contoh bobot:\n`saya 100%, {people_text} 100%`\n\n"
        f"Contoh nominal:\n`saya 30k, {people_text} 50k`\n\n"
        "Catatan:\n"
        "Angka persen di sini adalah bobot pembagian, bukan total yang harus berjumlah 100%.\n"
        "Contohnya kalau saya 100% dan Budi 100%, berarti dibagi rata. "
        "Kalau saya 100% dan Budi 80%, berarti bagian Budi lebih kecil dari bagian saya."
    )


# Helper for compute equal meal split shares.
def compute_equal_meal_split_shares(amount: float, people: list[str]) -> dict:
    """Compute equal split shares for user and friends."""
    participant_count = max(len(people or []) + 1, 1)
    share = float(amount or 0) / participant_count
    shares = {"Kamu": share}
    # Iterate through each person.
    for person in people or []:
        shares[str(person).strip().title()] = share
    return shares


# Helper for parse meal split allocation.
def parse_meal_split_allocation(text: str, amount: float, people: list[str]) -> dict | None:
    """Parse custom social split allocation using weighted percent or nominal values."""
    raw = str(text or "").strip()
    # Validate missing raw before continuing.
    if not raw:
        return None

    aliases = {"saya": "Kamu", "aku": "Kamu", "gw": "Kamu", "gue": "Kamu", "gua": "Kamu", "kamu": "Kamu"}
    # Iterate through each person.
    for person in people or []:
        aliases[normalize_text(person)] = str(person).strip().title()

    pattern = r"(?P<name>saya|aku|gw|gue|gua|kamu|[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{0,40}?)\s*:?\s*(?P<value>\d+(?:[.,]\d+)?\s*(?:%|rb|ribu|k|jt|juta|m)?)"
    entries = []
    # Iterate through each match.
    for match in re.finditer(pattern, raw, flags=re.IGNORECASE):
        name_raw = re.sub(r"\s+", " ", match.group("name") or "").strip()
        value_raw = str(match.group("value") or "").strip()
        key = normalize_text(name_raw)
        name = aliases.get(key) or name_raw.title()
        if name not in {"Kamu", *[str(p).strip().title() for p in people or []]}:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Append the current value to entries.
        entries.append((name, value_raw))

    # Validate missing entries before continuing.
    if not entries:
        return None

    has_percent = any(value.strip().endswith("%") for _, value in entries)
    has_nominal = any(not value.strip().endswith("%") for _, value in entries)
    if has_percent and has_nominal:
        return None

    seen = {}
    # Iterate through each name, value.
    for name, value in entries:
        seen[name] = value

    expected_names = ["Kamu"] + [str(p).strip().title() for p in people or [] if str(p).strip()]
    if has_percent:
        weights = {}
        # Iterate through each name.
        for name in expected_names:
            raw_value = str(seen.get(name) or "").strip()
            if raw_value.endswith("%"):
                # Run this operation in a guarded block so failures can be handled.
                try:
                    weights[name] = max(float(raw_value[:-1].replace(",", ".").strip()), 0.0)
                # Handle an expected failure from the guarded operation above.
                except Exception:
                    weights[name] = 0.0
            # Use the fallback path when no earlier branch matched.
            else:
                weights[name] = 0.0
        total_weight = sum(weights.values())
        if total_weight <= 0:
            return None
        return {name: float(amount or 0) * weight / total_weight for name, weight in weights.items()}

    shares = {}
    # Iterate through each name.
    for name in expected_names:
        raw_value = str(seen.get(name) or "").strip()
        shares[name] = parse_human_amount(raw_value) if raw_value else 0.0
    total_shares = sum(shares.values())
    if total_shares <= 0:
        return None
    return shares


# Helper for meal split status keyboard.
def meal_split_status_keyboard(payer: str) -> InlineKeyboardMarkup:
    """Ask whether the relevant share has already been paid."""
    return split_wizard_keyboard(
        "status",
        {"paid": "meal_split:status:paid", "unpaid": "meal_split:status:unpaid"},
        cancel_callback="cancel:meal_split",
    )


# Helper for build meal split status prompt.
def build_meal_split_status_prompt(state: dict) -> str:
    """Prompt for payment status in social split bill."""
    people = state.get("people") or []
    people_text = ", ".join(people) or "teman"
    if state.get("payer") == "self":
        return f"Apakah {md_safe(people_text)} sudah bayar bagian dia ke kamu?"
    return "Apakah kamu sudah bayar bagian kamu?"


# Helper for build meal split final payload.
def build_meal_split_final_payload(state: dict) -> dict:
    """Build pending parsed/debt payload from the social split bill wizard."""
    amount = float(state.get("amount") or 0)
    people = [str(p).strip().title() for p in (state.get("people") or []) if str(p).strip()]
    shares = state.get("shares") or compute_equal_meal_split_shares(amount, people)
    user_share = float(shares.get("Kamu", 0) or 0)
    # Extract person shares for validation.
    person_shares = {person: float(shares.get(person, 0) or 0) for person in people}
    total_receivable = sum(person_shares.values())
    payer = state.get("payer") or "self"
    status = state.get("status") or "unpaid"
    parsed = dict(state.get("parsed") or {})
    raw = state.get("raw") or parsed.get("raw_input") or ""
    people_text = ", ".join(people) or "teman"
    description = f"Makan bareng {people_text}"
    category = parsed.get("category") or detect_category(raw, "expense")
    date = parsed.get("date") or detect_date(raw)

    if payer == "self":
        cashflow_amount = amount if status == "unpaid" else user_share
        parsed.update({
            "type": "expense",
            "amount": cashflow_amount,
            "category": category,
            "subject": description,
            "description": description,
            "catatan": "Split bill: saya yang bayar; " + ("teman belum bayar" if status == "unpaid" else "teman sudah bayar"),
            "date": date,
            "parsed_by": parsed.get("parsed_by") or "meal_split",
            "split_bill": {
                "person_name": " ".join(people),
                "person_names": people,
                "participants": len(people) + 1,
                "share_amount": user_share,
                "user_share_amount": user_share,
                "base_share_amount": amount / max(len(people) + 1, 1),
                "person_shares": person_shares,
                "has_custom_share": bool(state.get("allocation_mode") == "custom"),
                "total_receivable": total_receivable if status == "unpaid" else 0,
                "total_amount": amount,
                "status": "unpaid" if status == "unpaid" else "paid",
            },
        })
        return {"mode": "transaction", "parsed": parsed, "cashflow_amount": cashflow_amount}

    payer_name = people[0] if people else "Teman"
    if status == "unpaid":
        return {
            "mode": "debt",
            "debt": {
                "intent": "add_payable",
                "person_name": payer_name,
                "amount": user_share,
                "description": f"Split bill {description}",
                "date": date,
                "raw_input": raw,
                "cashflow_mode": "debt_only",
                "fronting_mode": "split_bill_orang_lain_bayar",
            },
            "cashflow_amount": 0,
        }

    parsed.update({
        "type": "expense",
        "amount": user_share,
        "category": category,
        "subject": description,
        "description": description,
        "catatan": f"Split bill: {payer_name} yang bayar; saya sudah bayar bagian saya",
        "date": date,
        "parsed_by": parsed.get("parsed_by") or "meal_split",
    })
    parsed.pop("split_bill", None)
    return {"mode": "transaction", "parsed": parsed, "cashflow_amount": user_share}


# Helper for build meal split detail preview.
def build_meal_split_detail_preview(state: dict, payload: dict | None = None) -> str:
    """Build preview detail before account selection in social split bill."""
    amount = float(state.get("amount") or 0)
    people = state.get("people") or []
    shares = state.get("shares") or compute_equal_meal_split_shares(amount, people)
    payer = state.get("payer") or "self"
    status = state.get("status") or "unpaid"
    allocation_label = "Bagi rata" if state.get("allocation_mode") != "custom" else "Atur pembagian"

    lines = [
        "🤝 *Preview split bill*\n",
        f"Total transaksi: *{format_rupiah(amount)}*",
        f"Pembagian: *{md_safe(allocation_label)}*",
        f"Orang terlibat: *kamu dan {md_safe(', '.join(people) or 'teman')}*",
        "",
        "📋 *Rincian bagian:*",
    ]
    # Iterate through each name, share.
    for name, share in shares.items():
        label = "Kamu" if name == "Kamu" else name
        lines.append(f"• {md_safe(label)}: *{format_rupiah(share)}*")

    lines.extend(["", "💸 *Status:*"])
    if payer == "self":
        lines.append("• Pembayar awal: Saya")
        # Iterate through each person.
        for person in people:
            lines.append(f"• {md_safe(person)} {'belum bayar' if status == 'unpaid' else 'sudah bayar'}")
        if status == "unpaid":
            lines.append(f"• Piutang teman: *{format_rupiah(sum(float(shares.get(p, 0) or 0) for p in people))}*")
            lines.append(f"• Saldo keluar dari rekening saya: *{format_rupiah(amount)}*")
        # Use the fallback path when no earlier branch matched.
        else:
            lines.append(f"• Expense pribadi: *{format_rupiah(float(shares.get('Kamu', 0) or 0))}*")
            lines.append(f"• Saldo keluar dari rekening saya: *{format_rupiah(float(shares.get('Kamu', 0) or 0))}*")
    # Use the fallback path when no earlier branch matched.
    else:
        payer_name = people[0] if people else "Teman"
        lines.append(f"• Pembayar awal: {md_safe(payer_name)}")
        if status == "unpaid":
            lines.append(f"• Kamu belum bayar ke {md_safe(payer_name)}")
            lines.append(f"• Utang kamu: *{format_rupiah(float(shares.get('Kamu', 0) or 0))}*")
            lines.append("• Tidak ada saldo rekening yang berubah sekarang")
        # Use the fallback path when no earlier branch matched.
        else:
            lines.append(f"• Kamu sudah bayar ke {md_safe(payer_name)}")
            lines.append(f"• Expense pribadi: *{format_rupiah(float(shares.get('Kamu', 0) or 0))}*")
            lines.append(f"• Saldo keluar dari rekening saya: *{format_rupiah(float(shares.get('Kamu', 0) or 0))}*")

    lines.append("\nMau lanjut, edit dulu, atau batal?")
    return "\n".join(lines)


# Helper for meal split continue keyboard.
def meal_split_continue_keyboard() -> InlineKeyboardMarkup:
    """Coordinate the meal split continue keyboard logic in the Telegram handler layer.

    Args:
        None.

    Returns:
        `InlineKeyboardMarkup` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ Lanjut", callback_data="meal_split:continue")],
        [InlineKeyboardButton("✏️ Edit dulu", callback_data="meal_guard:rewrite")],
        [InlineKeyboardButton("🚫 Batal", callback_data="cancel:meal_split")],
    ])


# Helper for build meal split final summary.
def build_meal_split_final_summary(parsed_or_debt: dict, mode: str) -> str:
    """Build final ringkas summary for social split bill after rekening/debt decision."""
    if mode == "debt":
        return build_debt_only_confirm_preview(parsed_or_debt)

    parsed = parsed_or_debt
    split_bill = parsed.get("split_bill") or {}
    total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    user_share = float(split_bill.get("user_share_amount", parsed.get("amount", 0)) or 0)
    total_receivable = float(split_bill.get("total_receivable", 0) or 0)
    lines = [
        "🧾 *Ringkasan split bill:*",
        f"• Total transaksi: *{format_rupiah(total)}*",
        f"• Expense pribadi: *{format_rupiah(user_share)}*",
    ]
    if total_receivable > 0:
        names = ", ".join(split_bill.get("person_names") or []) or "teman"
        lines.append(f"• Piutang {md_safe(names)}: *{format_rupiah(total_receivable)}*")
    lines.append(f"• Rekening: *{md_safe(parsed.get('account') or '-')}*")
    account_summary = build_account_delta_summary_from_transaction_items([{"parsed": parsed}])
    if account_summary:
        lines.extend(["", account_summary])
    return "\n".join(lines)

# Helper for parse participant count.
def parse_participant_count(value: str) -> int | None:
    """Parse caller input for the parse participant count workflow in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `int | None` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
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
    # Run this operation in a guarded block so failures can be handled.
    try:
        value_int = int(clean)
        return value_int if value_int > 0 else None
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return None


# Helper for build account delta summary from transaction items.
def build_account_delta_summary_from_transaction_items(items: list[dict]) -> str:
    """Build the data structure or message text for account delta summary from transaction items."""
    transaction_items = []
    # Iterate through each item.
    for item in items or []:
        parsed = item.get("parsed", item) if isinstance(item, dict) else {}
        if isinstance(parsed, dict) and parsed.get("type") in ["expense", "income", "transfer"]:
            transaction_items.append({"parsed": parsed})

    deltas = calculate_account_deltas(transaction_items)
    # Validate missing deltas before continuing.
    if not deltas:
        return ""

    lines = ["\n💳 *Ringkasan per rekening:*"]
    # Iterate through each account name, delta.
    for account_name, delta in deltas.items():
        sign = "+" if float(delta or 0) >= 0 else "-"
        lines.append(f"• {md_safe(account_name)}: {sign}{format_rupiah(abs(float(delta or 0)))}")
    return "\n".join(lines)


# Helper for build mixed short summary.
def build_mixed_short_summary(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed short summary."""
    total_expense = 0.0
    total_income = 0.0
    total_transfer = 0.0
    total_debt = 0.0
    transaction_count = 0
    debt_count = 0

    # Iterate through each item.
    for item in mixed_items or []:
        kind = item.get("kind")
        parsed = item.get("parsed", {}) or {}
        amount = _receipt_amount(parsed.get("amount"), 0)
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

    # Extract account summary for validation.
    account_summary = build_account_delta_summary_from_transaction_items(mixed_items)
    if account_summary:
        # Append the current value to lines.
        lines.append(account_summary)

    return "\n".join(lines)


# Helper for build single short summary.
def build_single_short_summary(parsed: dict) -> str:
    """Build the data structure or message text for single short summary."""
    # Validate missing isinstance(parsed, dict) before continuing.
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
        # Append the current value to lines.
        lines.append(account_summary)

    return "\n".join(lines)


# Helper for build single split bill final summary.
def build_single_split_bill_final_summary(parsed: dict, account_label: str | None = None) -> str:
    """Build the compact final save preview for one split bill transaction.

    Args:
        parsed: Parsed single transaction that already has `split_bill` status
            and an account decision. Expected keys include `type`, `amount`,
            `category`, `account`, `description`, and nested `split_bill`.
        account_label: Optional display label from the selected rekening
            callback. When omitted, the function falls back to `parsed.account`.

    Returns:
        Markdown text with the final split bill summary, category summary, and
        account delta summary. This function only formats text and never writes
        to Google Sheets.

    Flow constraints:
        Use this only after split bill status and rekening are selected, so the
        next button row can be `Simpan / Edit dulu / Batal`.
    """
    # Read split metadata defensively because older pending sessions may not carry every key.
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else {}
    split_bill = split_bill or {}
    # Calculate the split amounts that must stay visible before the final save.
    total_paid = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    user_share = float(split_bill.get("user_share_amount", split_bill.get("share_amount", 0)) or 0)
    total_receivable = float(split_bill.get("total_receivable", 0) or 0)
    # Show the friend names so the receivable context is clear in the compact preview.
    person_names = split_bill.get("person_names") or [split_bill.get("person_name")]
    people_text = ", ".join(str(name) for name in person_names if str(name or "").strip()) or "-"
    # Convert the stored status into the same wording used by the detailed split preview.
    status = str(split_bill.get("status") or "").strip().lower()
    status_label = "belum dibayar / masuk piutang" if status == "unpaid" else "sudah dibayar"
    # Prefer the freshly selected account label so skip-account display stays accurate.
    account = account_label or parsed.get("account") or "-"

    # Keep the final split preview compact like other final batch confirmations.
    lines = ["🧾 *Ringkasan split bill:*"]
    lines.append("• Total item: *1*")
    lines.append("• Transaksi: *1 item*")
    lines.append(f"• Expense: *{format_rupiah(float(parsed.get('amount', 0) or 0))}*")
    lines.append(f"• Rekening: {md_safe(account)}")
    lines.append(f"• Status split: *{md_safe(status_label)}*")
    lines.append(f"• Total dibayar: *{format_rupiah(total_paid)}*")
    lines.append(f"• Bagian kamu: *{format_rupiah(user_share)}*")
    if total_receivable:
        lines.append(f"• Piutang aktif: *{format_rupiah(total_receivable)}*")
    lines.append(f"• Teman: {md_safe(people_text)}")

    # Reuse mixed summary helpers so category and account totals stay consistent.
    mixed_like_items = [{"kind": "transaction", "parsed": parsed, "raw": parsed.get("raw_input", "")}]
    category_summary = build_mixed_category_summary(mixed_like_items)
    # Add the category block when the transaction has a reportable category.
    if category_summary:
        lines.extend(["", category_summary])

    account_summary = build_account_delta_summary_from_transaction_items(mixed_like_items)
    # Add account impact so the user sees the balance effect before confirming save.
    if account_summary:
        lines.extend(["", account_summary])

    return "\n".join(lines)


# Helper for build single account prompt.
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
    # Build summary for the response flow.
    summary = preview_text or build_single_short_summary(parsed)
    return (
        f"{summary}\n\n"
        "💳 Dari rekening mana?\n"
        "Atau pilih *Sudah berlalu* jika transaksi hanya catatan historis dan tidak mau mengubah saldo."
    )


# Helper for build mixed account prompt.
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


# Helper for build updated item summary.
def build_updated_item_summary(item: dict, index: int | None = None) -> str:
    """Build the data structure or message text for updated item summary."""
    prefix = f"Item {index}" if index else "Item"
    kind = item.get("kind") if isinstance(item, dict) else None
    parsed = item.get("parsed", {}) if isinstance(item, dict) else {}

    if kind == "transaction":
        label = md_safe(parsed.get("description") or parsed.get("subject") or "Transaksi")
        amount = _receipt_amount(parsed.get("amount"), 0)
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
        amount = _receipt_amount(parsed.get("amount"), 0)
        account = md_safe(parsed.get("account") or "-")
        return (
            f"✅ *{prefix} debt sudah diupdate.*\n"
            f"• {person}\n"
            f"• {format_rupiah(amount)}\n"
            f"• Rekening: {account}"
        )

    return f"✅ *{prefix} sudah diupdate.*"


# Helper for preview edit fields for scope.
def _preview_edit_fields_for_scope(scope: str) -> list[tuple[str, str]]:
    """Coordinate the preview edit fields for scope logic in the Telegram handler layer.

    Args:
        scope: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[tuple[str, str]]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
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
    # Load rows for the current calculation.
    rows = []
    # Iterate through each i.
    for i in range(0, len(fields), 2):
        row = []
        # Iterate through each label, field.
        for label, field in fields[i:i + 2]:
            row.append(InlineKeyboardButton(label, callback_data=f"editflow:field:{scope}:{field}"))
        # Append the current value to rows.
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")])
    return InlineKeyboardMarkup(rows)


# Helper for build preview field help.
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




# Helper for build preview field value prompt.
def build_preview_field_value_prompt(scope: str, field: str) -> str:
    """Build the direct-value prompt after the user taps one edit field."""
    examples = {
        "amount": ("Nominal", "Tulis nominal yang kamu mau.", "20k"),
        "category": ("Kategori", "Tulis kategori yang kamu mau.", "Jajan"),
        "description": ("Deskripsi", "Tulis deskripsi yang kamu mau.", "Kopi susu"),
        "subject": ("Subjek", "Tulis subjek yang kamu mau.", "Mie Goreng"),
        "person_name": ("Orang", "Tulis nama orang yang kamu mau.", "Budi"),
        "type": ("Tipe transaksi", "Tulis tipe transaksi yang kamu mau.", "expense"),
        "date": ("Tanggal", "Tulis tanggal yang kamu mau.", "2026-07-03"),
        "due_date": ("Tanggal jatuh tempo", "Tulis tanggal jatuh tempo yang kamu mau.", "2026-07-30"),
        "month": ("Bulan", "Tulis bulan yang kamu mau.", "2026-07"),
        "account": ("Rekening", "Tulis rekening yang kamu mau.", "DANA"),
        "to_account": ("Rekening tujuan", "Tulis rekening tujuan yang kamu mau.", "BCA"),
        "catatan": ("Catatan", "Tulis catatan yang kamu mau.", "sudah dicek manual"),
        "name": ("Nama", "Tulis nama yang kamu mau.", "Laptop kerja"),
        "quantity": ("Jumlah", "Tulis jumlah yang kamu mau.", "2"),
        "unit": ("Satuan", "Tulis satuan yang kamu mau.", "gram"),
        "price_per_unit": ("Harga per unit", "Tulis harga per unit yang kamu mau.", "2594000"),
        "purchase_price_per_unit": ("Harga beli per unit", "Tulis harga beli per unit yang kamu mau.", "2559000"),
        "purchase_date": ("Tanggal beli", "Tulis tanggal beli yang kamu mau.", "2026-06-10"),
    }
    title, instruction, example = examples.get(
        field,
        (field.replace("_", " ").title(), "Tulis nilai baru yang kamu mau.", "nilai baru"),
    )
    return (
        f"✏️ *Edit {md_safe(title)}*\n\n"
        f"{instruction}\n\n"
        f"Contoh: `{md_code_text(example)}`"
    )


# Helper for parse preview direct field update.
def parse_preview_direct_field_update(field: str, value: str) -> dict:
    """Parse a raw value for one field selected from the edit keyboard."""
    canonical = PREVIEW_EDIT_KEY_ALIASES.get(str(field or "").strip().lower(), str(field or "").strip())
    # Validate missing canonical before continuing.
    if not canonical:
        return {}
    return _parse_preview_edit_pair(f"{canonical}: {value}")

def build_preview_edit_help(scope: str = "single") -> str:
    """Build the data structure or message text for preview edit help."""
    if scope == "pending_expense":
        examples = (
            "`nominal: 285k, kategori: Bills & Utilities, rekening: BRI`\n"
            "`deskripsi: Wifi rumah, tanggal: 2026-07-30`"
        )
    elif scope == "asset":
        examples = (
            "`nama: Laptop kerja, nominal: 8jt, kategori: Electronics`\n"
            "`jumlah: 41, unit: gram, harga_satuan: 2594000`"
        )
    elif scope == "debt":
        examples = (
            "`nominal: 50k, orang: Budi, rekening: DANA`\n"
            "`deskripsi: Talang makan, tanggal: 2026-07-02`"
        )
    # Use the fallback path when no earlier branch matched.
    else:
        examples = (
            "`nominal: 20k, kategori: Other Expense, rekening: DANA`\n"
            "`deskripsi: Mie Goreng, tanggal: 2026-07-02`"
        )

    item_hint = "" if scope == "single" else "\nItem yang dipilih akan diedit."
    # Show concise edit guidance before the user sends manual field changes.
    return (
        "✏️ *Edit transaksi*" + item_hint + "\n\n"
        "Pilih field di tombol bawah, atau ketik langsung:\n\n"
        "`nominal 20k`\n"
        "`kategori Other Expense`\n"
        "`rekening DANA`\n\n"
        "Bisa edit beberapa field sekaligus:\n"
        f"{examples}"
    )


# Helper for build mixed edit choose prompt.
def build_mixed_edit_choose_prompt(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed edit choose prompt."""
    lines = ["✏️ *Mau edit item nomor berapa?*\n"]
    # Iterate through each i, item.
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
        # Use the fallback path when no earlier branch matched.
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


# Helper for split preview edit segments.
def _split_preview_edit_segments(raw: str) -> list[str]:
    """Coordinate the split preview edit segments logic in the Telegram handler layer.

    Args:
        raw: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    segments: list[str] = []
    buffer: list[str] = []
    quote_char = ""

    for char in str(raw or ""):
        if char in {"'", '"'}:
            if quote_char == char:
                quote_char = ""
            # Fall back when not quote char.
            elif not quote_char:
                quote_char = char
            # Append the current value to buffer.
            buffer.append(char)
            # Skip the rest of this loop iteration after handling this case.
            continue

        if char in {",", ";", "\n", "\r"} and not quote_char:
            part = "".join(buffer).strip()
            if part:
                # Append the current value to segments.
                segments.append(part)
            buffer = []
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Append the current value to buffer.
        buffer.append(char)

    last = "".join(buffer).strip()
    if last:
        # Append the current value to segments.
        segments.append(last)
    return segments


# Helper for strip preview edit value.
def _strip_preview_edit_value(value: str) -> str:
    """Coordinate the strip preview edit value logic in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    clean = str(value or "").strip()
    if len(clean) >= 2 and clean[0] == clean[-1] and clean[0] in {"'", '"'}:
        return clean[1:-1].strip()
    return clean


# Helper for parse preview edit pair.
def _parse_preview_edit_pair(segment: str) -> dict:
    """Parse caller input for the parse preview edit pair workflow in the Telegram handler layer.

    Args:
        segment: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = str(segment or "").strip()
    # Validate missing raw before continuing.
    if not raw:
        return {}

    key_pattern = "|".join(re.escape(k) for k in sorted(PREVIEW_EDIT_KEY_ALIASES, key=len, reverse=True))
    match = re.match(
        rf"^({key_pattern})\s*(?:=|:)\s*(.+)$",
        raw,
        flags=re.IGNORECASE,
    )
    # Validate missing match before continuing.
    if not match:
        match = re.match(
            rf"^({key_pattern})\s+(.+)$",
            raw,
            flags=re.IGNORECASE,
        )
    # Validate missing match before continuing.
    if not match:
        return {}

    key = PREVIEW_EDIT_KEY_ALIASES.get(match.group(1).lower())
    value = _strip_preview_edit_value(match.group(2))
    if not key or value == "":
        return {}

    updates: dict = {}
    if key in {"amount", "quantity", "price_per_unit", "purchase_price_per_unit"}:
        # Extract amount for validation.
        amount = parse_human_amount(value)
        if amount <= 0:
            return {}
        updates[key] = amount
    elif key == "type":
        # Normalize normalized before matching.
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
        # Reuse the canonical date detector so invalid raw strings cannot leak
        # into a later save path. This intentionally aligns only the shared
        # date-integrity invariant; pending/saved edit remain separate flows.
        from app.nlp.regex_parser import detect_date_result
        date_result = detect_date_result(value)
        if date_result.status != "valid" or not date_result.value:
            return {}
        updates[key] = date_result.value
    elif key == "month":
        updates[key] = value.strip()
    elif key in ["account", "to_account"]:
        # Normalize value clean before matching.
        value_clean = value.strip()
        updates[key] = value_clean.upper() if value_clean.lower() in ["bca", "bri", "bsi", "dana"] else value_clean.title()
    # Use the fallback path when no earlier branch matched.
    else:
        updates[key] = value.strip()

    return updates


# Helper for parse preview edit updates.
def parse_preview_edit_updates(text: str) -> dict:
    """Parse caller input for the parse preview edit updates workflow in the Telegram handler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = str(text or "").strip()
    # Validate missing raw before continuing.
    if not raw:
        return {}

    segments = _split_preview_edit_segments(raw)
    # Validate missing segments before continuing.
    if not segments:
        return {}

    updates: dict = {}
    # Iterate through each segment.
    for segment in segments:
        parsed_segment = _parse_preview_edit_pair(segment)
        # Validate missing parsed segment before continuing.
        if not parsed_segment:
            if len(segments) == 1:
                return {}
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Append the current value to updates.
        updates.update(parsed_segment)

    return updates


# Helper for apply preview edit updates to parsed.
def apply_preview_edit_updates_to_parsed(parsed: dict, updates: dict) -> dict:
    """Parse caller input for the apply preview edit updates to parsed workflow in the Telegram handler layer.

    Args:
        parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        updates: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing isinstance(parsed, dict) before continuing.
    if not isinstance(parsed, dict):
        return parsed

    # Append the current value to parsed.
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


# Handle the asynchronous proceed after preview edit workflow.
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
        # Validate missing mixed items before continuing.
        if not mixed_items:
            await safe_edit_message(query, "❌ Sesi mixed input expired. Coba input ulang.")
            return

        if mixed_split_bill_needs_decision(mixed_items):
            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                build_mixed_split_bill_queue_prompt(mixed_items),
                parse_mode="Markdown",
                reply_markup=mixed_split_bill_keyboard(mixed_items),
            )
            return

        if mixed_needs_account(mixed_items):
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                build_mixed_account_prompt(mixed_items),
                parse_mode="Markdown",
                reply_markup=account_keyboard("mixed_acc"),
            )
            return

        receipt_context = context.user_data.get("pending_receipt_context")
        # Build final summary for the response flow.
        final_summary = build_mixed_final_summary(mixed_items, receipt_context)
        # Send the Telegram response before continuing.
        await safe_edit_message(query,
            f"{final_summary}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", True),
        )
        return

    if scope == "debt":
        debt_parsed = context.user_data.get("pending_debt")
        # Validate missing debt parsed before continuing.
        if not debt_parsed:
            await safe_edit_message(query, "❌ Sesi debt expired. Coba input ulang.")
            return

        intent = debt_parsed.get("intent")
        if debt_uses_cashflow(debt_parsed) and intent != "offset_debt" and not debt_parsed.get("account"):
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                build_debt_account_prompt(debt_parsed),
                parse_mode="Markdown",
                reply_markup=account_keyboard("debt_acc"),
            )
            return

        if debt_uses_cashflow(debt_parsed) and intent != "offset_debt":
            account_label = debt_parsed.get("account") or "-"
            # Build preview for the response flow.
            preview = build_debt_confirm_preview(debt_parsed, account_label)
        # Use the fallback path when no earlier branch matched.
        else:
            # Build preview for the response flow.
            preview = build_debt_only_confirm_preview(debt_parsed)

        # Send the Telegram response before continuing.
        await safe_edit_message(
            query,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("debt", True),
        )
        return

    if scope == "pending_expense":
        item = context.user_data.get("pending_expense_confirm")
        # Validate missing item before continuing.
        if not item:
            await safe_edit_message(query, "❌ Sesi pending expense expired. Coba input ulang.")
            return

        # Send the Telegram response before continuing.
        await safe_edit_message(
            query,
            build_pending_expense_confirm_preview(item, include_question=True),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("pending_expense"),
        )
        return

    if scope == "asset":
        asset = context.user_data.get("pending_asset_confirm")
        # Validate missing asset before continuing.
        if not asset:
            await safe_edit_message(query, "❌ Sesi tambah aset expired. Coba input ulang.")
            return

        # Send the Telegram response before continuing.
        await safe_edit_message(
            query,
            build_asset_confirm_preview(asset),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("asset"),
        )
        return

    parsed = context.user_data.get("pending_parsed")
    # Validate missing parsed before continuing.
    if not parsed:
        await safe_edit_message(query, "❌ Sesi transaksi expired. Coba input ulang.")
        return

    if split_bill_needs_decision(parsed):
        # Send the Telegram response before continuing.
        await safe_edit_message(query,
            build_split_bill_prompt_from_parsed(parsed),
            parse_mode="Markdown",
            reply_markup=split_bill_keyboard("single"),
        )
        return

    if needs_account(parsed):
        # Send the Telegram response before continuing.
        await safe_edit_message(
            query,
            build_single_account_prompt(parsed),
            parse_mode="Markdown",
            reply_markup=account_keyboard("acc"),
        )
        return

    # Build short summary for the response flow.
    short_summary = build_single_short_summary(parsed)
    # Build preview for the response flow.
    preview = build_preview(parsed)
    # Send the Telegram response before continuing.
    await safe_edit_message(query,
        f"{preview}\n\n{preview_action_question(True)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("single", True),
    )


# Handle the asynchronous handle pending preview edit workflow.
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
    # Validate missing state before continuing.
    if not state:
        return False

    chat = getattr(update, "effective_chat", None)
    chat_id = getattr(chat, "id", None) or getattr(getattr(update, "message", None), "chat_id", None)
    await clear_tracked_inline_keyboard(context, chat_id, "pending_preview_edit_prompt_message_id")

    scope = state.get("scope")
    step = state.get("step")

    if scope == "mixed" and step == "choose_item":
        # Run this operation in a guarded block so failures can be handled.
        try:
            item_index = int(str(user_text).strip()) - 1
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                "Balas dengan nomor item, contoh: `2`.",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard(),
            )
            return True

        mixed_items = context.user_data.get("pending_mixed") or []
        # Handle item index < 0 or item index >= len(mixed items).
        if item_index < 0 or item_index >= len(mixed_items):
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                "Nomor item tidak valid. Coba pilih nomor yang ada di preview.",
                reply_markup=cancel_keyboard(),
            )
            return True

        state["step"] = "edit_item"
        state["index"] = item_index
        context.user_data["pending_preview_edit"] = state
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_preview_edit_help("mixed"),
            parse_mode="Markdown",
            reply_markup=build_preview_edit_keyboard("mixed"),
        )
        return True

    direct_field = state.get("field") if step == "direct_field" else None
    updates = (
        parse_preview_direct_field_update(direct_field, user_text)
        # Handle direct field else parse preview edit updates(user text).
        if direct_field else parse_preview_edit_updates(user_text)
    )
    # Validate missing updates before continuing.
    if not updates:
        help_text = (
            build_preview_field_value_prompt(scope or "single", direct_field)
            if direct_field else build_preview_edit_help(scope or "single")
        )
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Format edit belum kebaca.\n\n" + help_text,
            parse_mode="Markdown",
        )
        return True

    if scope == "mixed":
        mixed_items = context.user_data.get("pending_mixed") or []
        item_index = int(state.get("index", -1))
        # Handle item index < 0 or item index >= len(mixed items).
        if item_index < 0 or item_index >= len(mixed_items):
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit mixed tidak valid. Coba input ulang.")
            return True

        item = mixed_items[item_index]
        if item.get("kind") == "transaction":
            item["parsed"] = apply_preview_edit_updates_to_parsed(item.get("parsed", {}), updates)
        elif item.get("kind") == "debt":
            # Extract debt updates for validation.
            debt_updates = dict(updates)
            if "subject" in debt_updates:
                debt_updates["person_name"] = debt_updates.pop("subject")
            item.setdefault("parsed", {}).update(debt_updates)
        mixed_items[item_index] = item
        context.user_data["pending_mixed"] = mixed_items
        context.user_data.pop("pending_preview_edit", None)

        # Build item summary for the response flow.
        item_summary = build_updated_item_summary(item, item_index + 1)
        receipt_context = context.user_data.get("pending_receipt_context")
        if mixed_needs_account(mixed_items):
            # Build detail preview for the response flow.
            detail_preview = build_mixed_detail_preview(mixed_items, receipt_context)
            # Send the Telegram response before continuing.
            await reply_update_safely(
                update,
                f"{item_summary}\n\n{detail_preview}\n\n{preview_action_question(False)}",
                parse_mode="Markdown",
                reply_markup=preview_action_keyboard("mixed", False),
            )
            return True

        # Build final summary for the response flow.
        final_summary = build_mixed_final_summary(mixed_items, receipt_context)
        # Send the Telegram response before continuing.
        await reply_update_safely(
            update,
            f"{item_summary}\n\n{final_summary}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", True),
        )
        return True

    if scope == "debt":
        debt_parsed = context.user_data.get("pending_debt")
        # Validate missing debt parsed before continuing.
        if not debt_parsed:
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit debt expired. Coba input ulang.")
            return True

        # Extract debt updates for validation.
        debt_updates = dict(updates)
        if "subject" in debt_updates:
            debt_updates["person_name"] = debt_updates.pop("subject")
        # `type` belongs to normal transactions, so ignore it for debt preview edits.
        debt_updates.pop("type", None)
        # Append the current value to debt parsed.
        debt_parsed.update(debt_updates)
        context.user_data["pending_debt"] = debt_parsed
        context.user_data.pop("pending_preview_edit", None)

        intent = debt_parsed.get("intent")
        if debt_uses_cashflow(debt_parsed) and intent != "offset_debt" and not debt_parsed.get("account"):
            # Send the Telegram response before continuing.
            await reply_update_safely(
                update,
                f"✅ Preview debt sudah diupdate.\n\n{build_debt_account_prompt(debt_parsed)}",
                parse_mode="Markdown",
                reply_markup=account_keyboard("debt_acc"),
            )
            return True

        # Build short summary for the response flow.
        short_summary = build_debt_short_summary(debt_parsed)
        # Send the Telegram response before continuing.
        await reply_update_safely(
            update,
            f"✅ Preview debt sudah diupdate.\n\n{short_summary}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("debt", True),
        )
        return True

    if scope == "pending_expense":
        item = context.user_data.get("pending_expense_confirm")
        # Validate missing item before continuing.
        if not item:
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit pending expense expired. Coba input ulang.")
            return True

        # Extract pending updates for validation.
        pending_updates = dict(updates)
        if "date" in pending_updates:
            pending_updates["due_date"] = pending_updates.pop("date")
        pending_updates.pop("type", None)
        pending_updates.pop("to_account", None)

        # Append the current value to item.
        item.update(pending_updates)
        if "due_date" in pending_updates and pending_updates.get("due_date"):
            item["due_precision"] = "date"
        if "month" in pending_updates and pending_updates.get("month") and not item.get("due_date"):
            item["due_precision"] = "month"
        if "description" in pending_updates and not pending_updates.get("subject"):
            item["subject"] = pending_updates["description"]

        context.user_data["pending_expense_confirm"] = item
        context.user_data.pop("pending_preview_edit", None)

        # Send the Telegram response before continuing.
        await reply_update_safely(
            update,
            f"✅ Preview pending expense sudah diupdate.\n\n{build_pending_expense_confirm_preview(item, include_question=False)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("pending_expense", True),
        )
        return True

    if scope == "asset":
        asset = context.user_data.get("pending_asset_confirm")
        # Validate missing asset before continuing.
        if not asset:
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit aset expired. Coba input ulang.")
            return True

        # Extract asset updates for validation.
        asset_updates = dict(updates)
        if "amount" in asset_updates:
            asset_updates["amount"] = asset_updates["amount"]
        if "description" in asset_updates and not asset_updates.get("name") and not asset.get("name"):
            asset_updates["name"] = asset_updates["description"]

        # Append the current value to asset.
        asset.update(asset_updates)
        if asset.get("quantity") not in [None, ""] and asset.get("price_per_unit"):
            # Run this operation in a guarded block so failures can be handled.
            try:
                asset["amount"] = float(asset.get("quantity") or 0) * float(asset.get("price_per_unit") or 0)
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Keep this intentionally empty block valid.
                pass

        context.user_data["pending_asset_confirm"] = asset
        context.user_data.pop("pending_preview_edit", None)

        # Send the Telegram response before continuing.
        await reply_update_safely(
            update,
            f"✅ Preview aset sudah diupdate.\n\n{build_asset_confirm_preview(asset)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("asset", True),
        )
        return True

    parsed = context.user_data.get("pending_parsed")
    # Validate missing parsed before continuing.
    if not parsed:
        context.user_data.pop("pending_preview_edit", None)
        await update.message.reply_text("❌ Sesi edit transaksi expired. Coba input ulang.")
        return True

    parsed = apply_preview_edit_updates_to_parsed(parsed, updates)
    context.user_data["pending_parsed"] = parsed
    context.user_data.pop("pending_preview_edit", None)

    if parsed.get("split_bill") and not split_bill_needs_decision(parsed) and needs_account(parsed):
        # Return split bill edits to the detailed preview before asking for rekening.
        preview = build_preview(parsed)
        await reply_update_safely(
            update,
            f"✅ Preview sudah diupdate.\n\n{preview}\n\n{preview_action_question(False)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("single", False),
        )
        return True

    if needs_account(parsed):
        # Send the Telegram response before continuing.
        await reply_update_safely(
            update,
            f"✅ Preview sudah diupdate.\n\n{build_single_account_prompt(parsed)}",
            parse_mode="Markdown",
            reply_markup=account_keyboard("acc"),
        )
        return True

    # Build short summary for the response flow.
    short_summary = build_single_short_summary(parsed)
    # Build preview for the response flow.
    preview = build_preview(parsed)
    # Send the Telegram response before continuing.
    await reply_update_safely(
        update,
        f"✅ Preview sudah diupdate.\n\n{preview}\n\n{preview_action_question(True)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("single", True),
    )
    return True


# Helper for format split bill preview line.
def format_split_bill_preview_line(parsed: dict) -> str:
    """Format data into a readable display for split bill preview line."""
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    # Validate missing split bill before continuing.
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
    # Use the fallback path when no earlier branch matched.
    else:
        status_label = "menunggu status"
        receivable_display = total_receivable

    return (
        f"🤝 Split: {status_label} | "
        f"total dibayar {format_rupiah(total)} | "
        f"bagian kamu {format_rupiah(share)} | "
        f"piutang aktif {format_rupiah(receivable_display)}"
    )

# Helper for build preview.
def build_preview(parsed: dict) -> str:
    """Build the data structure or message text for preview."""
    type_label = {
        "expense": "- Pengeluaran",
        "income": "+ Pemasukan",
        "transfer": "🔄 Transfer",
    }.get(parsed.get("type"), "❓")

    lines = [
        f"*{type_label}*",
        f"💰 Nominal : {format_rupiah(parsed.get('amount', 0))}",
        f"📁 Kategori: {parsed.get('category') or '-'}",
        f"👤 Subjek  : {parsed.get('subject') or '-'}",
        f"📝 Deskripsi: {parsed.get('description') or '-'}",
    ]

    # Build split preview for the response flow.
    split_preview = format_split_bill_preview_line(parsed)
    if split_preview:
        # Append the current value to lines.
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
        # Append the current value to lines.
        lines.append(account_summary)

    return "\n".join(lines)


# Helper for build batch preview.
def build_batch_preview(parsed_items: list[dict]) -> str:
    """Build a compact multi-transaction preview without changing save logic.

    Args:
        parsed_items: Parsed transaction items. Each item is expected to contain
            a `parsed` dict with transaction fields such as `type`, `amount`,
            `description`, `subject`, `category`, `account`, and
            `tipe_pengeluaran`.

    Returns:
        Markdown text for the batch preview. The primary row title prioritizes
        `description` over `subject` because `subject` may contain payer/person
        metadata or, in some parser outputs, an account-like token.
    """
    total_count = len(parsed_items or [])
    lines = [f"🧾 *Preview ({total_count} transaksi)*", ""]

    total_expense = 0.0
    total_income = 0.0
    category_summary: dict[str, dict[str, float | int]] = {}
    grouped_by_date: dict[str, list[tuple[int, dict]]] = {}

    # Iterate through each idx, item.
    for idx, item in enumerate(parsed_items or [], 1):
        parsed = item.get("parsed", {}) or {}
        amount = _receipt_amount(parsed.get("amount"), 0)
        txn_type = parsed.get("type")

        if txn_type == "expense":
            total_expense += amount
        elif txn_type == "income":
            total_income += amount

        category = str(parsed.get("category") or "-").strip() or "-"
        cat_data = category_summary.setdefault(category, {"count": 0, "amount": 0.0})
        cat_data["count"] = int(cat_data.get("count", 0)) + 1
        cat_data["amount"] = float(cat_data.get("amount", 0) or 0) + amount

        date_key = str(parsed.get("date") or "-").strip() or "-"
        grouped_by_date.setdefault(date_key, []).append((idx, parsed))

    lines.append(f"- Expense : {format_rupiah(total_expense)}")
    lines.append(f"+ Income  : {format_rupiah(total_income)}")

    if category_summary:
        lines.extend(["", "📊 *Kategori*"])
        # Iterate through each category, data.
        for category, data in sorted(
            category_summary.items(),
            key=lambda pair: float(pair[1].get("amount", 0) or 0),
            reverse=True,
        ):
            lines.append(
                f"• {md_safe(category)} ({int(data.get('count', 0))}): "
                f"{format_rupiah(float(data.get('amount', 0) or 0))}"
            )

    lines.extend(["", "──────────────────"])

    # Iterate through each date key.
    for date_key in sorted(grouped_by_date.keys()):
        lines.append(f"📅 {md_safe(date_key)}")
        lines.append("")

        # Iterate through each idx, parsed.
        for idx, parsed in grouped_by_date[date_key]:
            txn_type = parsed.get("type")
            type_icon = {
                "expense": "-",
                "income": "+",
                "transfer": "🔄",
            }.get(txn_type, "❓")
            amount = _receipt_amount(parsed.get("amount"), 0)
            # Preview title should describe the item, not rekening/person metadata.
            subject = str(parsed.get("description") or parsed.get("subject") or "-").strip() or "-"
            description = str(parsed.get("description") or "").strip()
            category = str(parsed.get("category") or "-").strip() or "-"
            account = str(parsed.get("account") or "-").strip() or "-"
            spending_type = str(parsed.get("tipe_pengeluaran") or "-").strip() or "-"

            lines.append(f"{idx}. {type_icon} *{md_safe(subject)}* • {format_rupiah(amount)}")
            lines.append(
                f"   📁 {md_safe(category)} • 🏦 {md_safe(account)} • 🏷️ {md_safe(spending_type)}"
            )

            if description:
                lines.append(f"   📝 {md_safe(description)}")

            if parsed.get("catatan"):
                lines.append(f"   🗒️ {md_safe(parsed.get('catatan'))}")

            lines.append("")

    if lines and lines[-1] == "":
        # Append the current value to lines.
        lines.pop()
    lines.append("──────────────────")

    lines.extend(["", "Lanjut ke rekening/simpan?"])
    return "\n".join(lines)


# ── Receipt / Image Selection Flow ────────────────────────────────────────────

RECEIPT_NUMBER_WORDS = {
    "nol": 0,
    "satu": 1,
    "se": 1,
    "dua": 2,
    "tiga": 3,
    "empat": 4,
    "lima": 5,
    "enam": 6,
    "tujuh": 7,
    "delapan": 8,
    "sembilan": 9,
    "sepuluh": 10,
    "sebelas": 11,
    "dua belas": 12,
}


# Helper for is receipt image result.
def is_receipt_image_result(result: dict, items: list[dict]) -> bool:
    """Check whether Gemini output should enter the receipt review flow.

    Args:
        result: Parsed image result from the NLP layer.
        items: Normalized transaction items from the image.

    Returns:
        True when the image behaves like an itemized receipt, otherwise False.
    """
    receipt = (result or {}).get("receipt") or {}
    return bool(receipt.get("is_receipt")) and len(items or []) > 0


# Helper for receipt merchant.
def _receipt_merchant(receipt: dict, items: list[dict] | None = None) -> str:
    """Resolve the merchant name used in receipt previews."""
    merchant = str((receipt or {}).get("merchant") or "").strip()
    if merchant:
        return merchant
    # Iterate through each item.
    for item in items or []:
        subject = str(item.get("subject") or "").strip()
        if subject:
            return subject
    return "Struk"




# Helper for receipt amount.
def _receipt_amount(value, default: float = 0.0) -> float:
    """Parse receipt amount fields that may use Indonesian thousand separators."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        if isinstance(value, str):
            raw = value.strip().replace("Rp", "").replace("rp", "").replace(" ", "")
            raw = re.sub(r"[^0-9.,-]", "", raw)
            if "," in raw and "." in raw:
                raw = raw.replace(".", "").replace(",", ".")
            elif "," in raw:
                raw = raw.replace(",", ".")
            elif "." in raw:
                parts = raw.split(".")
                # Handle len(parts) > 1 and all(len(part) == 3 for part in parts[1:]).
                if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
                    raw = raw.replace(".", "")
            return float(raw or default)
        return float(value or default)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return float(default)

# Helper for receipt item quantity.
def _receipt_item_quantity(item: dict) -> float:
    """Return the receipt item quantity with a safe fallback."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        quantity = float(item.get("quantity", 1) or 1)
        return quantity if quantity > 0 else 1.0
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return 1.0


# Helper for receipt extra charges.
def _receipt_extra_charges(receipt: dict) -> list[dict]:
    """Return normalized extra charge components from receipt metadata."""
    charges = []
    for charge in (receipt or {}).get("extra_charges") or []:
        # Validate missing isinstance(charge, dict) before continuing.
        if not isinstance(charge, dict):
            # Skip the rest of this loop iteration after handling this case.
            continue
        amount = _receipt_amount(charge.get("amount"), 0)
        if amount <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        charges.append({
            "label": str(charge.get("label") or "Biaya tambahan").strip(),
            "amount": int(round(amount)),
            "is_discount": bool(charge.get("is_discount")),
        })
    return charges


# Helper for receipt extra charge net amount.
def receipt_extra_charge_net_amount(receipt: dict) -> int:
    """Calculate net extra charge from service, tax, other charges, and discount."""
    total = 0
    # Iterate through each charge.
    for charge in _receipt_extra_charges(receipt):
        amount = int(charge.get("amount", 0) or 0)
        total += -amount if charge.get("is_discount") else amount
    return int(round(total))


# Helper for receipt extra charge detail.
def _receipt_extra_charge_detail(receipt: dict, divisor: int | None = None) -> str:
    """Build a compact note for the combined extra charge transaction."""
    # Prepare parts from the incoming input.
    parts = []
    # Iterate through each charge.
    for charge in _receipt_extra_charges(receipt):
        label = charge.get("label") or "Biaya tambahan"
        amount = int(charge.get("amount", 0) or 0)
        sign = "-" if charge.get("is_discount") else ""
        if divisor and divisor > 1:
            share = int(round(amount / divisor))
            parts.append(f"{label} {sign}{format_rupiah(amount)} dibagi {divisor} = {sign}{format_rupiah(share)}")
        # Use the fallback path when no earlier branch matched.
        else:
            parts.append(f"{label} {sign}{format_rupiah(amount)}")
    return "; ".join(parts)


# Helper for receipt extra charge description.
def _receipt_extra_charge_description(receipt: dict, merchant: str) -> str:
    """Build the saved description for the combined receipt extra charge."""
    labels = [str(charge.get("label") or "").strip().lower() for charge in _receipt_extra_charges(receipt)]
    has_service = any("service" in label or "layanan" in label for label in labels)
    has_tax = any("ppn" in label or "tax" in label or "pajak" in label for label in labels)
    has_discount = any(charge.get("is_discount") for charge in _receipt_extra_charges(receipt))

    # Handle has service and has tax and has discount.
    if has_service and has_tax and has_discount:
        prefix = "Service, PPN & Diskon"
    # Fall back when has service and has tax.
    elif has_service and has_tax:
        prefix = "Service & PPN"
    # Fall back when has discount.
    elif has_discount:
        prefix = "Biaya tambahan & Diskon"
    # Use the fallback path when no earlier branch matched.
    else:
        prefix = "Biaya tambahan"

    return f"{prefix} {merchant}".strip()[:80]


# Helper for build receipt review text.
def build_receipt_review_text(receipt: dict, items: list[dict]) -> str:
    """Build the first OCR review text for receipt images.

    Args:
        receipt: Receipt-level metadata from Gemini Vision.
        items: Itemized receipt rows parsed from the image.

    Returns:
        Markdown text that shows OCR details before the user chooses whether all
        items or only part of the receipt should be recorded.
    """
    merchant = _receipt_merchant(receipt, items)
    date = (receipt or {}).get("date") or (items[0].get("date") if items else "-")
    item_total = sum(_receipt_amount(item.get("amount"), 0) for item in items)
    net_extra = receipt_extra_charge_net_amount(receipt)
    total = float((receipt or {}).get("total") or 0) or item_total + net_extra

    lines = [
        "🧾 *Struk berhasil dibaca.*",
        "",
        f"Merchant: *{md_safe(merchant)}*",
        f"Tanggal : {md_safe(date)}",
        f"Total   : *{format_rupiah(total)}*",
        "",
        "📋 *Rincian item:*",
    ]

    # Iterate through each idx, item.
    for idx, item in enumerate(items, 1):
        desc = md_safe(item.get("description") or item.get("subject") or f"Item {idx}")
        qty = _receipt_item_quantity(item)
        amount = _receipt_amount(item.get("amount"), 0)
        unit_price = _receipt_amount(item.get("unit_price"), 0) or (amount / qty if qty else amount)
        lines.extend([
            f"{idx}. *{desc}*",
            f"   Qty: {qty:g}",
            f"   Total: {format_rupiah(amount)}",
            f"   Harga satuan: {format_rupiah(unit_price)}",
        ])

    charges = _receipt_extra_charges(receipt)
    if charges:
        lines.extend(["", "💳 *Biaya tambahan:*"])
        # Iterate through each charge.
        for charge in charges:
            label = md_safe(charge.get("label") or "Biaya tambahan")
            sign = "-" if charge.get("is_discount") else ""
            lines.append(f"• {label}: {sign}{format_rupiah(charge.get('amount', 0))}")
        lines.append(f"• Total biaya tambahan: *{format_rupiah(net_extra)}*")

    lines.extend([
        "",
        "🧮 *Pengecekan total:*",
        f"• Subtotal item: {format_rupiah(item_total)}",
        f"• Biaya tambahan net: {format_rupiah(net_extra)}",
        f"• Total struk: *{format_rupiah(total)}*",
        "",
        "Apakah semua item di struk ini masuk ke pengeluaran kamu?",
    ])
    return "\n".join(lines)


# Helper for build receipt part selection prompt.
def build_receipt_part_selection_prompt(receipt: dict, items: list[dict]) -> str:
    """Build instructions for selecting only part of a receipt."""
    lines = [
        "🧩 *Pilih item yang menjadi bagian kamu.*",
        "",
        "Gunakan nomor item dari daftar struk.",
        "",
        "Contoh:",
        "`4 beli 1`",
        "`5 beli 1 dibagi 2`",
        "",
        "Daftar item:",
    ]

    # Iterate through each idx, item.
    for idx, item in enumerate(items, 1):
        desc = md_safe(item.get("description") or item.get("subject") or f"Item {idx}")
        qty = _receipt_item_quantity(item)
        amount = _receipt_amount(item.get("amount"), 0)
        unit_price = _receipt_amount(item.get("unit_price"), 0) or (amount / qty if qty else amount)
        lines.append(
            f"{idx}. {desc} | Qty {qty:g} | Total {format_rupiah(amount)} | Satuan {format_rupiah(unit_price)}"
        )

    return "\n".join(lines)


# Helper for parse receipt number.
def _parse_receipt_number(value: str | None, default: float = 1.0) -> float:
    """Parse a small quantity or divisor from natural Indonesian text."""
    raw = str(value or "").strip().lower()
    # Validate missing raw before continuing.
    if not raw:
        return default

    if raw in RECEIPT_NUMBER_WORDS:
        return float(RECEIPT_NUMBER_WORDS[raw])

    match = re.search(r"\d+(?:[.,]\d+)?", raw)
    if match:
        return float(match.group(0).replace(",", "."))

    return default


# Helper for parse receipt part selection.
def parse_receipt_part_selection(user_text: str, items: list[dict]) -> dict:
    """Parse the user's selected receipt rows and shares.

    Args:
        user_text: Natural text such as `4 beli 1` or `5 beli 1 dibagi 2`.
        items: Receipt items shown to the user.

    Returns:
        Dict with `success`, selected parts, and total amount. No data is saved
        here; this only prepares the next receipt step.
    """
    selected = []
    # Build failed lines for the response flow.
    failed_lines = []

    for raw_line in re.split(r"[\n;]+", str(user_text or "")):
        line = raw_line.strip(" .,-")
        # Validate missing line before continuing.
        if not line:
            # Skip the rest of this loop iteration after handling this case.
            continue

        index_match = re.match(r"^\s*(\d+)\b", line)
        # Validate missing index match before continuing.
        if not index_match:
            # Append the current value to failed lines.
            failed_lines.append(line)
            # Skip the rest of this loop iteration after handling this case.
            continue

        item_index = int(index_match.group(1)) - 1
        # Handle item index < 0 or item index >= len(items).
        if item_index < 0 or item_index >= len(items):
            # Append the current value to failed lines.
            failed_lines.append(line)
            # Skip the rest of this loop iteration after handling this case.
            continue

        qty_match = re.search(
            r"\b(?:beli|ambil|porsi|qty|x)\s+([\w.,]+(?:\s+belas)?)",
            line,
            flags=re.IGNORECASE,
        )
        take_qty = _parse_receipt_number(qty_match.group(1) if qty_match else "1", 1)
        if take_qty <= 0:
            # Append the current value to failed lines.
            failed_lines.append(line)
            # Skip the rest of this loop iteration after handling this case.
            continue

        divisor_match = re.search(
            r"\b(?:di\s*-?\s*bagi|dibagi|bagi|split|share)\s+([\w.,]+(?:\s+belas)?)",
            line,
            flags=re.IGNORECASE,
        )
        share_divisor = int(round(_parse_receipt_number(divisor_match.group(1), 1))) if divisor_match else 1
        share_divisor = max(1, share_divisor)

        item = items[item_index]
        receipt_qty = _receipt_item_quantity(item)
        line_amount = _receipt_amount(item.get("amount"), 0)
        # Extract unit amount for validation.
        unit_amount = line_amount / receipt_qty if receipt_qty else line_amount
        before_share = unit_amount * take_qty
        # Extract amount for validation.
        amount = int(round(before_share / share_divisor))

        selected.append({
            "item_index": item_index,
            "item": item,
            "take_qty": take_qty,
            "receipt_qty": receipt_qty,
            "share_divisor": share_divisor,
            "unit_amount": unit_amount,
            "before_share": before_share,
            "amount": amount,
            "raw": line,
        })

    # Validate missing selected before continuing.
    if not selected:
        return {
            "success": False,
            "message": "Pilihan item belum kebaca. Coba tulis seperti `4 beli 1` atau `5 beli 1 dibagi 2`.",
            "failed_lines": failed_lines,
            "selected": [],
            "subtotal": 0,
        }

    return {
        "success": True,
        "message": "ok",
        "failed_lines": failed_lines,
        "selected": selected,
        "subtotal": sum(part["amount"] for part in selected),
    }


# Helper for build receipt selected breakdown.
def build_receipt_selected_breakdown(receipt: dict, selection_result: dict) -> str:
    """Build the selected receipt item breakdown before asking extra charge split."""
    lines = ["🧮 *Bagian kamu dari item struk:*", ""]

    for idx, part in enumerate(selection_result.get("selected") or [], 1):
        item = part["item"]
        desc = md_safe(item.get("description") or item.get("subject") or f"Item {idx}")
        lines.append(f"{idx}. *{desc}*")
        lines.append(f"   Ambil: {part['take_qty']:g} dari {part['receipt_qty']:g} qty")
        lines.append(f"   Hitung item: {format_rupiah(item.get('amount', 0))} / {part['receipt_qty']:g} x {part['take_qty']:g}")
        if part["share_divisor"] > 1:
            lines.append(f"   Dibagi lagi: {format_rupiah(part['before_share'])} / {part['share_divisor']}")
        lines.append(f"   Bagian kamu: *{format_rupiah(part['amount'])}*")
        lines.append("")

    lines.append(f"Subtotal item kamu: *{format_rupiah(selection_result.get('subtotal', 0))}*")

    charges = _receipt_extra_charges(receipt)
    if charges:
        lines.extend(["", "💳 *Biaya tambahan di struk:*"])
        # Iterate through each charge.
        for charge in charges:
            sign = "-" if charge.get("is_discount") else ""
            lines.append(f"• {md_safe(charge.get('label'))}: {sign}{format_rupiah(charge.get('amount', 0))}")
        lines.append("")
        lines.append("Biaya tambahan ini dibagi berapa orang?")
    # Use the fallback path when no earlier branch matched.
    else:
        lines.extend(["", "Tidak ada biaya tambahan yang terbaca."])

    failed_lines = selection_result.get("failed_lines") or []
    if failed_lines:
        lines.extend(["", "⚠️ Baris yang belum kebaca:"])
        # Iterate through each line.
        for line in failed_lines[:5]:
            lines.append(f"• `{md_code_text(line)}`")

    return "\n".join(lines).strip()


# Helper for parse receipt divisor.
def parse_receipt_divisor(user_text: str) -> int:
    """Parse the divisor used for receipt service/tax sharing."""
    match = re.search(
        r"\b(?:di\s*-?\s*bagi|dibagi|bagi|split|share)\s+([\w.,]+(?:\s+belas)?)",
        str(user_text or ""),
        flags=re.IGNORECASE,
    )
    divisor = _parse_receipt_number(match.group(1) if match else user_text, 0)
    return max(0, int(round(divisor)))


# Helper for receipt transaction item.
def _receipt_transaction_item(parsed: dict, raw: str, amount: int | None = None, catatan: str | None = None) -> dict:
    """Create one mixed transaction item from a receipt row."""
    data = dict(parsed or {})
    if amount is not None:
        data["amount"] = int(round(amount))
    if catatan is not None:
        old_note = str(data.get("catatan") or "").strip()
        data["catatan"] = f"{catatan} | {old_note}".strip(" |")
    data["parsed_by"] = data.get("parsed_by") or "gemini_image"
    return {"kind": "transaction", "parsed": data, "raw": raw}


# Helper for receipt extra charge item.
def _receipt_extra_charge_item(receipt: dict, items: list[dict], amount: int, divisor: int | None = None) -> dict | None:
    """Coordinate the receipt extra charge item logic in the Telegram handler layer.

    Args:
        receipt: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        items: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        amount: Numeric amount or amount-like user input to parse or format.
        divisor: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    if amount <= 0:
        return None

    merchant = _receipt_merchant(receipt, items)
    base_item = items[0] if items else {}
    description = _receipt_extra_charge_description(receipt, merchant)
    note = _receipt_extra_charge_detail(receipt, divisor=divisor)

    parsed = {
        "type": "expense",
        "amount": int(round(amount)),
        "category": base_item.get("category") or "Food & Beverage",
        "account": base_item.get("account"),
        "to_account": None,
        "subject": merchant,
        "description": description,
        "catatan": note,
        "tipe_pengeluaran": base_item.get("tipe_pengeluaran") or "Harian",
        "date": (receipt or {}).get("date") or base_item.get("date"),
        "parsed_by": "gemini_image",
    }
    return {"kind": "transaction", "parsed": parsed, "raw": f"biaya tambahan struk {merchant}"}


# Helper for build receipt all mixed items.
def build_receipt_all_mixed_items(receipt: dict, items: list[dict]) -> tuple[list[dict], dict]:
    """Build mixed items when all receipt rows belong to the user."""
    mixed_items = []
    # Iterate through each idx, item.
    for idx, item in enumerate(items, 1):
        desc = item.get("description") or item.get("subject") or f"Item {idx}"
        mixed_items.append(_receipt_transaction_item(item, f"struk item {idx}: {desc}"))

    net_extra = receipt_extra_charge_net_amount(receipt)
    extra_item = _receipt_extra_charge_item(receipt, items, net_extra)
    if extra_item:
        # Append the current value to mixed items.
        mixed_items.append(extra_item)

    context = {
        "mode": "all",
        "receipt": receipt,
        "extra_charge_amount": max(0, net_extra),
        "extra_charge_divisor": None,
        "selected_parts": [],
    }
    return mixed_items, context


# Helper for build receipt partial mixed items.
def build_receipt_partial_mixed_items(receipt: dict, selection_result: dict, divisor: int) -> tuple[list[dict], dict]:
    """Build mixed items when only selected receipt rows belong to the user."""
    selected_parts = selection_result.get("selected") or []
    selected_items = [part["item"] for part in selected_parts]
    mixed_items = []

    # Iterate through each idx, part.
    for idx, part in enumerate(selected_parts, 1):
        item = part["item"]
        desc = item.get("description") or item.get("subject") or f"Item {idx}"
        if part["share_divisor"] > 1:
            note = f"{part['take_qty']:g} dari {part['receipt_qty']:g} qty, lalu dibagi {part['share_divisor']} orang"
        # Use the fallback path when no earlier branch matched.
        else:
            note = f"{part['take_qty']:g} dari {part['receipt_qty']:g} qty"
        mixed_items.append(
            _receipt_transaction_item(
                item,
                f"bagian struk item {part['item_index'] + 1}: {desc}",
                amount=part["amount"],
                catatan=note,
            )
        )

    net_extra = receipt_extra_charge_net_amount(receipt)
    extra_share = int(round(net_extra / divisor)) if divisor > 0 else 0
    extra_item = _receipt_extra_charge_item(receipt, selected_items, max(0, extra_share), divisor=divisor)
    if extra_item:
        # Append the current value to mixed items.
        mixed_items.append(extra_item)

    context = {
        "mode": "partial",
        "receipt": receipt,
        "extra_charge_amount": max(0, extra_share),
        "extra_charge_divisor": divisor,
        "selected_parts": selected_parts,
        "subtotal_items": selection_result.get("subtotal", 0),
    }
    return mixed_items, context


# Helper for build receipt account prompt.
def build_receipt_account_prompt(mixed_items: list[dict], receipt_context: dict) -> str:
    """Build the rekening prompt after receipt rows are converted to mixed items."""
    receipt = (receipt_context or {}).get("receipt") or {}
    merchant = _receipt_merchant(receipt, [item.get("parsed", {}) for item in mixed_items])
    total = sum(_receipt_amount(item.get("parsed", {}).get("amount"), 0) for item in mixed_items)
    mode = (receipt_context or {}).get("mode")
    mode_label = "semua item" if mode == "all" else "bagian kamu"

    lines = [
        f"🧾 Struk *{md_safe(merchant)}* sudah diproses sebagai batch ({mode_label}).",
        f"• Total item disimpan: *{len(mixed_items)}*",
        f"• Total expense: *{format_rupiah(total)}*",
        "",
    ]

    if mode == "partial":
        lines.append(f"• Subtotal item kamu: {format_rupiah((receipt_context or {}).get('subtotal_items', 0))}")
        lines.append(f"• Biaya tambahan kamu: {format_rupiah((receipt_context or {}).get('extra_charge_amount', 0))}")
        lines.append("")

    lines.append("💳 Dari rekening mana?")
    lines.append("Atau pilih *Sudah berlalu* jika transaksi hanya catatan historis dan tidak mau mengubah saldo.")
    return "\n".join(lines)


# Helper for build receipt final preview.
def build_receipt_final_preview(mixed_items: list[dict], receipt_context: dict, account_label: str | None = None) -> str:
    """Build the final receipt batch preview before save."""
    # Prepare receipt context from the incoming input.
    receipt_context = receipt_context or {}
    receipt = receipt_context.get("receipt") or {}
    merchant = _receipt_merchant(receipt, [item.get("parsed", {}) for item in mixed_items])
    total = sum(_receipt_amount(item.get("parsed", {}).get("amount"), 0) for item in mixed_items)
    category = "-"
    account = account_label or "-"
    # Iterate through each item.
    for item in mixed_items:
        parsed = item.get("parsed", {})
        if parsed.get("category") and category == "-":
            category = parsed.get("category")
        if parsed.get("account") and (not account_label):
            account = parsed.get("account")

    mode = receipt_context.get("mode")
    mode_label = "semua struk" if mode == "all" else "bagian struk"

    lines = [
        f"🧾 *Ringkasan batch dari {mode_label}*",
        f"• Merchant: *{md_safe(merchant)}*",
        f"• Total item: *{len(mixed_items)}*",
        f"• Expense: *{format_rupiah(total)}*",
        f"• Kategori: {md_safe(category)}",
        f"• Rekening: {md_safe(account)}",
        "",
        "📋 *Rincian transaksi yang akan disimpan:*",
    ]

    # Iterate through each idx, item.
    for idx, item in enumerate(mixed_items, 1):
        parsed = item.get("parsed", {})
        desc = md_safe(parsed.get("description") or parsed.get("subject") or f"Item {idx}")
        amount = _receipt_amount(parsed.get("amount"), 0)
        lines.append(f"{idx}. {desc}: *{format_rupiah(amount)}*")
        note = parsed.get("catatan")
        if note:
            lines.append(f"   Catatan: {md_safe(note)}")

    charges = _receipt_extra_charges(receipt)
    if charges:
        lines.extend(["", "💳 *Rincian biaya tambahan:*"])
        divisor = receipt_context.get("extra_charge_divisor")
        # Iterate through each charge.
        for charge in charges:
            amount = int(charge.get("amount", 0) or 0)
            sign = "-" if charge.get("is_discount") else ""
            if divisor and divisor > 1:
                share = int(round(amount / divisor))
                lines.append(
                    f"• {md_safe(charge.get('label'))}: {sign}{format_rupiah(amount)} / {divisor} = {sign}{format_rupiah(share)}"
                )
            # Use the fallback path when no earlier branch matched.
            else:
                lines.append(f"• {md_safe(charge.get('label'))}: {sign}{format_rupiah(amount)}")
        lines.append(f"• Total biaya tambahan kamu: *{format_rupiah(receipt_context.get('extra_charge_amount', 0))}*")

    # Extract account summary for validation.
    account_summary = build_account_delta_summary_from_transaction_items(mixed_items)
    if account_summary:
        lines.extend(["", account_summary])

    return "\n".join(lines)


# Helper for strip split bill phrase.
def strip_split_bill_phrase(text: str) -> str:
    """Coordinate the strip split bill phrase logic in the Telegram handler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    clean = str(text or "")

    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    # sering already kehilangan angka pembagi, misalnya:
    # "Nasi Kuning Dibagi Sama Raka".
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|ptpt|split\s*bill|split|share)"
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


# Helper for strip trailing split person names.
def strip_trailing_split_person_names(text: str, person_names: list[str]) -> str:
    """Coordinate the strip trailing split person names logic in the Telegram handler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        person_names: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    clean = str(text or "").strip(" .,-")
    # Validate missing clean or not person names before continuing.
    if not clean or not person_names:
        return clean

    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    ordered_names = sorted(
        [str(name or "").strip() for name in person_names if str(name or "").strip()],
        key=len,
        reverse=True,
    )

    changed = True
    # Repeat this block while changed and clean.
    while changed and clean:
        changed = False
        clean = clean.strip(" .,-")

        # Split bill parsing note: separate the paid transaction from each person share.
        new_clean = re.sub(r"\b(?:sama|ama|dengan|bareng|dan)\s*$", "", clean, flags=re.IGNORECASE).strip(" .,-")
        if new_clean != clean:
            # Normalize clean before matching.
            clean = new_clean
            changed = True

        # Iterate through each person.
        for person in ordered_names:
            pattern = rf"(?:^|[\s,;&]+){re.escape(person)}\s*$"
            new_clean = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip(" .,-")
            if new_clean != clean:
                # Normalize clean before matching.
                clean = new_clean
                changed = True
                # Leave the loop after the target condition has been reached.
                break

    return clean


SPLIT_BILL_ACCOUNT_TAIL_PATTERN = (
    r"\s+\b(?:via|pakai|pake|menggunakan|lewat|dari|from|using)\s+"
    r"(?:cash|bri|bsi|bca|dana|gopay|go\s*pay|seabank|sea\s*bank)\b.*$"
)


# Helper for strip split bill account tail.
def strip_split_bill_account_tail(name_text: str) -> str:
    """Coordinate the strip split bill account tail logic in the Telegram handler layer.

    Args:
        name_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    clean = str(name_text or "").strip()
    clean = re.sub(SPLIT_BILL_ACCOUNT_TAIL_PATTERN, "", clean, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", clean).strip(" ,;&")


# Helper for limit split bill friends to participants.
def limit_split_bill_friends_to_participants(
    person_names: list[str],
    person_shares: dict,
    participants: int,
    base_share_amount: float,
) -> tuple[list[str], dict]:
    """Coordinate the limit split bill friends to participants logic in the Telegram handler layer.

    Args:
        person_names: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        person_shares: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        participants: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        base_share_amount: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `tuple[list[str], dict]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    max_friends = max(int(participants or 0) - 1, 0)
    clean_names = [str(name or "").strip().title() for name in person_names or [] if str(name or "").strip()]

    # Handle max friends and len(clean names) > max friends.
    if max_friends and len(clean_names) > max_friends:
        # Normalize clean names before matching.
        clean_names = clean_names[:max_friends]

    # Normalize clean shares before matching.
    clean_shares = {}
    # Iterate through each name.
    for name in clean_names:
        clean_shares[name] = float((person_shares or {}).get(name, base_share_amount) or 0)

    return clean_names, clean_shares


# Helper for split split bill person names.
def split_split_bill_person_names(name_text: str) -> list[str]:
    """Coordinate the split split bill person names logic in the Telegram handler layer.

    Args:
        name_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Normalize clean before matching.
    clean = strip_split_bill_account_tail(name_text)

    # Stop before date/status words so they do not become friend names.
    clean = re.split(
        r"\b(tanggal|tgl|tg|pada|date|kemarin|hari|minggu|bulan|udah|sudah|belum|dibayar|bayar|lunas|ke)\b",
        clean,
        flags=re.IGNORECASE,
    )[0]

    clean = re.sub(r"[^A-Za-zÀ-ÿ,;&\s]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip(" ,;&")
    # Validate missing clean before continuing.
    if not clean:
        return []

    if re.search(r"[,;&]|\bdan\b|\band\b", clean, flags=re.IGNORECASE):
        raw_parts = re.split(r"\s*(?:,|;|&|\bdan\b|\band\b)\s*", clean, flags=re.IGNORECASE)
    # Use the fallback path when no earlier branch matched.
    else:
        # Split bill parsing note: separate the paid transaction from each person share.
        raw_parts = clean.split()

    names = []
    seen = set()
    noise = {"sama", "ama", "dengan", "bareng", "dan", "and", "via", "pakai", "pake", "menggunakan", "lewat"}

    # Iterate through each part.
    for part in raw_parts:
        part = re.sub(r"[^A-Za-zÀ-ÿ\s]", " ", str(part or ""))
        part = re.sub(r"\s+", " ", part).strip()
        # Validate missing part or part.lower() in noise before continuing.
        if not part or part.lower() in noise:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Normalize normalized before matching.
        normalized = part.title()
        key = normalized.lower()
        if key not in seen:
            # Append the current value to names.
            names.append(normalized)
            # Append the current value to seen.
            seen.add(key)

    return names



# Helper for strip split bill name tail.
def strip_split_bill_name_tail(name_text: str) -> str:
    """Coordinate the strip split bill name tail logic in the Telegram handler layer.

    Args:
        name_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Normalize clean before matching.
    clean = strip_split_bill_account_tail(name_text)
    clean = re.split(
        r"\b(tanggal|tgl|tg|pada|date|kemarin|hari|minggu|bulan|udah|sudah|belum|dibayar|bayar|lunas|ke)\b",
        clean,
        flags=re.IGNORECASE,
    )[0]
    return re.sub(r"\s+", " ", clean).strip(" ,;&")


# Helper for is split bill allocation token.
def is_split_bill_allocation_token(value: str) -> bool:
    """Check whether a condition is true for split bill allocation token."""
    raw = str(value or "").strip().lower().rstrip(".,;)")
    # Validate missing raw before continuing.
    if not raw:
        return False
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)?\s*(?:%|rb|ribu|k|jt|juta|m)?", raw))


# Helper for parse split bill share value.
def parse_split_bill_share_value(value: str, base_share: float) -> float:
    """Parse caller input for the parse split bill share value workflow in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.
        base_share: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = str(value or "").strip().lower().rstrip(".,;)")
    # Validate missing raw before continuing.
    if not raw:
        return 0.0

    if raw.endswith("%"):
        # Run this operation in a guarded block so failures can be handled.
        try:
            pct = float(raw[:-1].replace(",", ".").strip())
            return max(base_share * pct / 100, 0.0)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            return 0.0

    return max(parse_amount_text(raw), 0.0)


# Helper for parse split bill people and shares.
def parse_split_bill_people_and_shares(name_text: str, total_amount: float, participants: int) -> dict:
    """Parse caller input for the parse split bill people and shares workflow in the Telegram handler layer.

    Args:
        name_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        total_amount: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        participants: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    base_share = float(total_amount or 0) / int(participants or 1)
    # Normalize clean before matching.
    clean = strip_split_bill_name_tail(name_text)
    clean = clean.replace("=", ":")
    clean = re.sub(r"\s*:\s*", ":", clean)
    clean = re.sub(r"\s*(?:,|;|&|\bdan\b|\band\b)\s*", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Validate missing clean before continuing.
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

    # Repeat this block while i < len(tokens).
    while i < len(tokens):
        token = tokens[i].strip()
        low = token.lower()

        # Validate missing token or low in noise before continuing.
        if not token or low in noise:
            i += 1
            # Skip the rest of this loop iteration after handling this case.
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
                # Fall back when not value part and i + 1 < len(tokens) and is split bill allo.
                elif not value_part and i + 1 < len(tokens) and is_split_bill_allocation_token(tokens[i + 1]):
                    value = tokens[i + 1]
                    has_custom_share = True
                    i += 1
        # Fall back when i + 1 < len(tokens) and is split bill allocation token(tokens.
        elif i + 1 < len(tokens) and is_split_bill_allocation_token(tokens[i + 1]):
            name_part = re.sub(r"[^A-Za-zÀ-ÿ\s]", " ", token).strip()
            if name_part:
                name = name_part
                value = tokens[i + 1]
                has_custom_share = True
                i += 1
        # Fall back when is split bill allocation token(token).
        elif is_split_bill_allocation_token(token):
            # Split bill parsing note: separate the paid transaction from each person share.
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Use the fallback path when no earlier branch matched.
        else:
            name_part = re.sub(r"[^A-Za-zÀ-ÿ\s]", " ", token).strip()
            if name_part:
                name = name_part

        if name:
            normalized_name = re.sub(r"\s+", " ", name).strip().title()
            if normalized_name and normalized_name.lower() not in noise:
                # Append the current value to entries.
                entries.append((normalized_name, value))

        i += 1

    # Extract person names for validation.
    person_names = []
    # Extract person shares for validation.
    person_shares = {}
    seen = set()

    # Iterate through each name, value.
    for name, value in entries:
        key = name.lower()
        if key in seen:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Append the current value to seen.
        seen.add(key)
        # Append the current value to person names.
        person_names.append(name)
        person_shares[name] = parse_split_bill_share_value(value, base_share) if value else base_share

    return {
        "person_names": person_names,
        "person_shares": person_shares,
        "base_share_amount": base_share,
        "has_custom_share": has_custom_share,
    }


# Helper for format split bill person shares.
def format_split_bill_person_shares(split_bill: dict) -> str:
    """Format data into a readable display for split bill person shares."""
    shares = (split_bill or {}).get("person_shares") or {}
    person_names = (split_bill or {}).get("person_names") or []
    # Validate missing shares and person names before continuing.
    if not shares and person_names:
        fallback = float((split_bill or {}).get("base_share_amount", (split_bill or {}).get("share_amount", 0)) or 0)
        shares = {str(name): fallback for name in person_names if str(name or "").strip()}

    # Prepare parts from the incoming input.
    parts = []
    # Iterate through each name.
    for name in person_names:
        if not str(name or "").strip():
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Extract amount for validation.
        amount = float(shares.get(name, 0) or 0)
        parts.append(f"{name}: {format_rupiah(amount)}")

    return ", ".join(parts)

# Helper for clean split person name.
def clean_split_person_name(name: str) -> str:
    """Coordinate the clean split person name logic in the Telegram handler layer.

    Args:
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    names = split_split_bill_person_names(name)
    return " ".join(names).title() if names else ""


def build_split_bill_item_description_from_raw(raw: str, fallback: str = "") -> str:
    """Build the data structure or message text for split bill item description from raw."""
    text = normalize_slash_split_syntax(str(raw or ""))
    # Prepare text from the incoming input.
    text = strip_date_phrases(text)
    text = re.sub(r"\b(?:rp|idr)?\s*\d[\d.,]*\s*(?:rb|ribu|k|jt|juta|m|miliar)?\b", " ", text, flags=re.IGNORECASE)

    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|ptpt|split\s*bill|split|share)"
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
    # Iterate through each pattern.
    for pattern in cleanup_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    text = re.sub(r"^(?:beli|bayar|buat|untuk|jajan)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^A-Za-zÀ-ÿ0-9\s&/+.-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ./,-")

    if text and text not in {"/", "-"}:
        return text.title()

    # Normalize fallback clean before matching.
    fallback_clean = strip_split_bill_phrase(fallback)
    fallback_clean = re.sub(r"^[\s/.-]+$", "", fallback_clean).strip()
    if re.match(r"^[\s/.-]*(?:sama|ama|dengan|bareng)\b", fallback_clean, flags=re.IGNORECASE):
        fallback_clean = ""
    if fallback_clean.startswith(("/", ".", "-")):
        fallback_clean = ""
    return fallback_clean.title() if fallback_clean else "Split Bill"


# Helper for detect split bill.
def detect_split_bill(parsed: dict, raw: str) -> dict | None:
    """Coordinate the detect split bill logic in the Telegram handler layer.

    Args:
        parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        raw: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    if not parsed or parsed.get("type") != "expense":
        return None

    normalized_raw = normalize_slash_split_syntax(str(raw or ""))
    original_total = extract_split_bill_total_amount(normalized_raw)
    amount = float(original_total or parsed.get("amount", 0) or 0)
    if amount <= 0:
        return None

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Split bill parsing note: separate the paid transaction from each person share.
    text = normalize_slash_split_syntax(str(raw or ""))
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|ptpt|split\s*bill|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"
    participant_token = r"(?:\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|berdua|bertiga|berempat|berlima|berenam)"
    name_chunk = r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s,;&:%./]{0,140}"

    payer_match = re.search(
        r"^(?P<item>.+?)\s+sama\s+(?P<person>[A-Za-zÀ-ÿ]+)\s+"
        r"(?:rp\s*)?\d[\d.,]*\s*(?:rb|ribu|k|jt|juta|m)?\s+"
        r"(?P<payer>saya|aku|gw|gue|gua|[A-Za-zÀ-ÿ]+)\s+yang\s+bayar",
        text,
        flags=re.IGNORECASE,
    )
    if payer_match:
        person = payer_match.group("person").strip().title()
        payer = normalize_text(payer_match.group("payer"))
        payer_role = "user" if payer in {"saya", "aku", "gw", "gue", "gua"} else "other"
        item = re.sub(r"^(?:beli|bayar)\s+", "", payer_match.group("item"), flags=re.IGNORECASE).strip().title()
        participants = 2
        base_share_amount = amount / participants
        parsed["amount"] = amount
        parsed["subject"] = item
        parsed["description"] = item
        return {
            "person_name": person,
            "person_names": [person],
            "participants": participants,
            "payer_role": payer_role,
            "payer_name": person if payer_role == "other" else "",
            "share_amount": base_share_amount,
            "user_share_amount": base_share_amount,
            "base_share_amount": base_share_amount,
            "person_shares": {person: base_share_amount},
            "has_custom_share": False,
            "total_receivable": base_share_amount if payer_role == "user" else 0.0,
            "total_amount": amount,
            "status": None,
        }

    # Phase 2 compact split: `split bill makan Budi 80k` or `ptpt makan 80k sama Budi`.
    compact_patterns_early = [
        rf"\b(?:split\s*bill|split|patungan|ptpt)\b\s+(?P<body>.+?)\s+(?:sama|ama|dengan|bareng)\s+(?P<names>{name_chunk})(?=\s*(?:tanggal|tgl|kemarin|hari\s+ini|besok|via|pakai|pake|dari|\d|rp|idr|$))",
        rf"\b(?:split\s*bill|split|patungan|ptpt)\b\s+(?P<body>.+?)\s+(?P<names>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{{0,80}}?)(?=\s*(?:\d|rp|idr|$))",
    ]
    # Iterate through each compact pattern.
    for compact_pattern in compact_patterns_early:
        compact_match = re.search(compact_pattern, text, flags=re.IGNORECASE)
        # Validate missing compact match before continuing.
        if not compact_match:
            # Skip the rest of this loop iteration after handling this case.
            continue
        compact_names = split_split_bill_person_names(compact_match.group("names") or "")
        compact_names = [
            name for name in compact_names
            if normalize_text(name) not in {"makan", "minum", "ngopi", "lunch", "dinner", "brunch", "jajan"}
        ]
        # Validate missing compact names before continuing.
        if not compact_names:
            # Skip the rest of this loop iteration after handling this case.
            continue

        participants = len(compact_names) + 1
        # Extract base share amount for validation.
        base_share_amount = amount / participants
        # Extract person shares for validation.
        person_shares = {person: base_share_amount for person in compact_names}
        parsed["amount"] = amount
        clean_desc = build_split_bill_item_description_from_raw(raw, parsed.get("description") or "")
        # Normalize clean desc before matching.
        clean_desc = strip_trailing_split_person_names(clean_desc, compact_names)
        parsed["description"] = clean_desc
        if parsed.get("subject"):
            parsed["subject"] = clean_desc

        return {
            "person_name": " ".join(compact_names),
            "person_names": compact_names,
            "participants": participants,
            "share_amount": base_share_amount,
            "user_share_amount": base_share_amount,
            "base_share_amount": base_share_amount,
            "person_shares": person_shares,
            "has_custom_share": False,
            "total_receivable": sum(float(v or 0) for v in person_shares.values()),
            "total_amount": amount,
            "status": None,
        }

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
    # Extract person names for validation.
    person_names = []
    # Extract person shares for validation.
    person_shares = {}
    # Extract base share amount for validation.
    base_share_amount = 0.0
    has_custom_share = False

    # Iterate through each idx, pattern.
    for idx, pattern in enumerate(patterns):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        # Validate missing match before continuing.
        if not match:
            # Skip the rest of this loop iteration after handling this case.
            continue

        if idx in (0, 2, 3):
            participants = parse_participant_count(match.group(1))
            # Prepare name text from the incoming input.
            name_text = match.group(2)
        # Use the fallback path when no earlier branch matched.
        else:
            # Prepare name text from the incoming input.
            name_text = match.group(1)
            participants = parse_participant_count(match.group(2))

        # Validate missing participants before continuing.
        if not participants:
            # Skip the rest of this loop iteration after handling this case.
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
        # Leave the loop after the target condition has been reached.
        break

    # Validate missing participants or participants < 2 or not person names before continuing.
    if not participants or participants < 2 or not person_names:
        # Phase 2: support compact input such as `split bill makan Budi 80k`
        # or `ptpt makan 80k sama Budi`. If no participant count is written,
        # treat the user + detected friend(s) as the participants.
        compact_patterns = [
            rf"\b(?:split\s*bill|split|patungan|ptpt)\b\s+(?P<body>.+?)\s+(?:sama|ama|dengan|bareng)\s+(?P<names>{name_chunk})(?=\s*(?:tanggal|tgl|kemarin|hari\s+ini|besok|via|pakai|pake|dari|\d|rp|idr|$))",
            rf"\b(?:split\s*bill|split|patungan|ptpt)\b\s+(?P<body>.+?)\s+(?P<names>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{0,80}?)(?=\s*(?:\d|rp|idr|$))",
        ]
        # Iterate through each pattern.
        for pattern in compact_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            # Validate missing match before continuing.
            if not match:
                # Skip the rest of this loop iteration after handling this case.
                continue
            raw_names = match.group("names") or ""
            # Extract person names for validation.
            person_names = split_split_bill_person_names(raw_names)
            person_names = [name for name in person_names if normalize_text(name) not in {"makan", "ngopi", "lunch", "dinner"}]
            # Validate missing person names before continuing.
            if not person_names:
                # Skip the rest of this loop iteration after handling this case.
                continue
            participants = len(person_names) + 1
            # Extract base share amount for validation.
            base_share_amount = amount / participants
            # Extract person shares for validation.
            person_shares = {person: base_share_amount for person in person_names}
            has_custom_share = False
            # Leave the loop after the target condition has been reached.
            break

    # Validate missing participants or participants < 2 or not person names before continuing.
    if not participants or participants < 2 or not person_names:
        return None

    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    parsed["amount"] = amount

    # Validate missing person shares before continuing.
    if not person_shares:
        # Extract base share amount for validation.
        base_share_amount = amount / participants
        # Extract person shares for validation.
        person_shares = {person: base_share_amount for person in person_names}

    total_receivable = sum(float(v or 0) for v in person_shares.values())
    # Handle total receivable > amount and total receivable > 0.
    if total_receivable > amount and total_receivable > 0:
        scale = amount / total_receivable
        # Extract person shares for validation.
        person_shares = {person: float(value or 0) * scale for person, value in person_shares.items()}
        total_receivable = amount
    # Extract user share amount for validation.
    user_share_amount = max(amount - total_receivable, 0.0)
    # Extract share amount for validation.
    share_amount = user_share_amount  # Backward-compatible field: now represents the user share.

    # Split bill parsing note: separate the paid transaction from each person share.
    clean_desc = build_split_bill_item_description_from_raw(raw, parsed.get("description") or "")
    # Normalize clean desc before matching.
    clean_desc = strip_trailing_split_person_names(clean_desc, person_names)
    parsed["description"] = clean_desc

    subject = parsed.get("subject") or ""
    if subject:
        # Normalize clean subject before matching.
        clean_subject = build_split_bill_item_description_from_raw(raw, subject)
        # Normalize clean subject before matching.
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


# Helper for attach split bill if any.
def attach_split_bill_if_any(parsed: dict, raw: str) -> dict:
    """Coordinate the attach split bill if any logic in the Telegram handler layer.

    Args:
        parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        raw: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    split_bill = detect_split_bill(parsed, raw)
    if split_bill:
        parsed["split_bill"] = split_bill
    return parsed


# Helper for split bill needs decision.
def split_bill_needs_decision(parsed: dict) -> bool:
    """Coordinate the split bill needs decision logic in the Telegram handler layer.

    Args:
        parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    return bool(split_bill) and not split_bill.get("status")


# Helper for mixed split bill needs decision.
def mixed_split_bill_needs_decision(mixed_items: list[dict]) -> bool:
    """Coordinate the mixed split bill needs decision logic in the Telegram handler layer.

    Args:
        mixed_items: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Iterate through each item.
    for item in mixed_items or []:
        if item.get("kind") == "transaction" and split_bill_needs_decision(item.get("parsed", {})):
            return True
    return False


def split_bill_keyboard(scope: str = "single", item_index: int | None = None) -> InlineKeyboardMarkup:
    """Coordinate the split bill keyboard logic in the Telegram handler layer.

    Args:
        scope: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        item_index: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `InlineKeyboardMarkup` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    suffix = f":{item_index}" if item_index is not None else ""
    return split_wizard_keyboard(
        "status",
        {
            "paid": f"split:paid:{scope}{suffix}",
            "unpaid": f"split:unpaid:{scope}{suffix}",
        },
        cancel_callback=f"cancel:{scope}",
    )


# Helper for mixed split bill keyboard.
def mixed_split_bill_keyboard(mixed_items: list[dict]) -> InlineKeyboardMarkup:
    """Coordinate the mixed split bill keyboard logic in the Telegram handler layer.

    Args:
        mixed_items: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `InlineKeyboardMarkup` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    current_index = get_next_mixed_split_bill_index(mixed_items)
    return split_bill_keyboard("mixed", current_index)


# Helper for build split bill prompt from parsed.
def build_split_bill_prompt_from_parsed(parsed: dict) -> str:
    """Build the data structure or message text for split bill prompt from parsed."""
    split_bill = parsed.get("split_bill", {}) or {}
    person_names = split_bill.get("person_names") or [split_bill.get("person_name", "-")]
    participants = int(split_bill.get("participants", 2) or 2)
    total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share = float(split_bill.get("share_amount", 0) or 0)
    total_receivable = float(split_bill.get("total_receivable", share * len(person_names)) or 0)
    friend_text = ", ".join(str(p) for p in person_names if p)
    # Prepare detail text from the incoming input.
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


# Helper for build mixed split bill prompt.
def build_mixed_split_bill_prompt(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed split bill prompt."""
    split_items = [
        item for item in mixed_items or []
        if item.get("kind") == "transaction" and split_bill_needs_decision(item.get("parsed", {}))
    ]

    lines = [f"🤝 *Split bill terdeteksi di {len(split_items)} item*\n"]

    # Iterate through each i, item.
    for i, item in enumerate(split_items, 1):
        parsed = item["parsed"]
        split_bill = parsed.get("split_bill", {}) or {}
        person_names = split_bill.get("person_names") or [split_bill.get("person_name", "-")]
        total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
        share = float(split_bill.get("share_amount", 0) or 0)
        total_receivable = float(split_bill.get("total_receivable", share * len(person_names)) or 0)
        friend_text = ", ".join(str(p) for p in person_names if p)
        # Prepare detail text from the incoming input.
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


# Helper for get mixed split bill indexes.
def get_mixed_split_bill_indexes(mixed_items: list[dict]) -> list[int]:
    """Retrieve data needed by the get mixed split bill indexes workflow in the Telegram handler layer.

    Args:
        mixed_items: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[int]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    indexes = []
    # Iterate through each idx, item.
    for idx, item in enumerate(mixed_items or []):
        if item.get("kind") != "transaction":
            # Skip the rest of this loop iteration after handling this case.
            continue
        parsed = item.get("parsed", {})
        if isinstance(parsed, dict) and parsed.get("split_bill"):
            # Append the current value to indexes.
            indexes.append(idx)
    return indexes


# Helper for get next mixed split bill index.
def get_next_mixed_split_bill_index(mixed_items: list[dict]) -> int | None:
    """Retrieve data needed by the get next mixed split bill index workflow in the Telegram handler layer.

    Args:
        mixed_items: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `int | None` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Iterate through each idx.
    for idx in get_mixed_split_bill_indexes(mixed_items):
        parsed = mixed_items[idx].get("parsed", {})
        if split_bill_needs_decision(parsed):
            return idx
    return None


# Helper for build mixed split bill queue prompt.
def build_mixed_split_bill_queue_prompt(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed split bill queue prompt."""
    split_indexes = get_mixed_split_bill_indexes(mixed_items)
    current_index = get_next_mixed_split_bill_index(mixed_items)

    if current_index is None:
        return build_mixed_detail_preview(mixed_items)

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
    # Prepare detail text from the incoming input.
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


# Helper for apply split bill decision to current mixed.
def apply_split_bill_decision_to_current_mixed(mixed_items: list[dict], status: str) -> tuple[list[dict], int | None]:
    """Coordinate the apply split bill decision to current mixed logic in the Telegram handler layer.

    Args:
        mixed_items: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        status: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `tuple[list[dict], int | None]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    current_index = get_next_mixed_split_bill_index(mixed_items)
    if current_index is None:
        return mixed_items, None
    mixed_items, decided_index, _ = apply_split_bill_decision_to_mixed_index(mixed_items, current_index, status)
    return mixed_items, decided_index


# Helper for apply split bill decision to mixed index.
def apply_split_bill_decision_to_mixed_index(mixed_items: list[dict], item_index: int, status: str) -> tuple[list[dict], int | None, str]:
    """Coordinate the apply split bill decision to mixed index logic in the Telegram handler layer.

    Args:
        mixed_items: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        item_index: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        status: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `tuple[list[dict], int | None, str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle item index is None or item index < 0 or item index >= len(mix.
    if item_index is None or item_index < 0 or item_index >= len(mixed_items or []):
        return mixed_items, None, "invalid"

    item = mixed_items[item_index]
    if item.get("kind") != "transaction":
        return mixed_items, None, "invalid"

    parsed = item.get("parsed", {})
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    # Validate missing split bill before continuing.
    if not split_bill:
        return mixed_items, None, "invalid"

    if split_bill.get("status"):
        return mixed_items, item_index, "already_decided"

    apply_split_bill_decision_to_parsed(parsed, status)
    item["parsed"] = parsed
    mixed_items[item_index] = item
    return mixed_items, item_index, "applied"


# Split bill parsing note: separate the paid transaction from each person share.

# Helper for apply split bill decision to parsed.
def apply_split_bill_decision_to_parsed(parsed: dict, status: str) -> dict:
    """Parse caller input for the apply split bill decision to parsed workflow in the Telegram handler layer.

    Args:
        parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        status: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    # Validate missing split bill before continuing.
    if not split_bill:
        return parsed

    split_bill["status"] = status

    total_amount = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share_amount = float(split_bill.get("user_share_amount", split_bill.get("share_amount", 0)) or 0)

    if status == "paid":
        # Handle share amount <= 0 and total amount > 0.
        if share_amount <= 0 and total_amount > 0:
            participants = int(split_bill.get("participants", 0) or 0)
            if participants > 0:
                # Extract share amount for validation.
                share_amount = total_amount / participants
                split_bill["share_amount"] = share_amount
                split_bill["user_share_amount"] = share_amount
        if share_amount > 0:
            parsed["amount"] = share_amount
    elif status == "unpaid" and total_amount > 0:
        parsed["amount"] = total_amount

    return parsed


# Helper for apply split bill decision to mixed.
def apply_split_bill_decision_to_mixed(mixed_items: list[dict], status: str) -> list[dict]:
    """Coordinate the apply split bill decision to mixed logic in the Telegram handler layer.

    Args:
        mixed_items: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        status: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Iterate through each item.
    for item in mixed_items or []:
        if item.get("kind") != "transaction":
            # Skip the rest of this loop iteration after handling this case.
            continue
        parsed = item.get("parsed", {})
        if parsed.get("split_bill"):
            apply_split_bill_decision_to_parsed(parsed, status)
    return mixed_items


def preview_split_bill_debt(parsed: dict) -> dict | None:
    """Validate the confirmed split participant/share set without any write."""
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    if not split_bill or split_bill.get("status") != "unpaid":
        return None
    person_names = split_bill.get("person_names") or [split_bill.get("person_name")]
    person_names = [str(p).strip().title() for p in person_names if str(p or "").strip()]
    person_shares = {str(k).strip().casefold(): v for k, v in (split_bill.get("person_shares") or {}).items()}
    fallback_share = split_bill.get("base_share_amount", split_bill.get("share_amount", 0))
    participants = [
        (person, person_shares.get(person.casefold(), fallback_share))
        for person in person_names
    ]
    return validate_split_bill_receivables(participants)


def create_split_bill_debt(parsed: dict, raw: str = "", source_transaction_id: str = "") -> dict | None:
    """Create the complete required receivable set for an unpaid split bill."""
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    if not split_bill or split_bill.get("status") != "unpaid":
        return None

    person_names = split_bill.get("person_names") or [split_bill.get("person_name")]
    person_names = [str(p).strip().title() for p in person_names if str(p or "").strip()]
    person_shares = {str(k).strip().casefold(): v for k, v in (split_bill.get("person_shares") or {}).items()}
    fallback_share = split_bill.get("base_share_amount", split_bill.get("share_amount", 0))
    participants = [(person, person_shares.get(person.casefold(), fallback_share)) for person in person_names]
    return create_split_bill_receivables(
        participants,
        description=f"Split bill: {parsed.get('description') or raw or '-'}",
        source_transaction_id=source_transaction_id,
    )


# Helper for format split debt result lines.
def format_split_debt_result_lines(debt_result: dict) -> list[str]:
    """Format data into a readable display for split debt result lines."""
    # Build lines for the response flow.
    lines = []
    for item in (debt_result or {}).get("created", []) or []:
        lines.append(
            f"• {md_safe(item.get('person_name'))}: *{format_rupiah(float(item.get('remaining', 0) or 0))}*"
        )
    return lines


# Helper for summarize saved transaction items.
def summarize_saved_transaction_items(items: list[dict]) -> dict:
    """Coordinate the summarize saved transaction items logic in the Telegram handler layer.

    Args:
        items: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    total_expense = 0.0
    total_income = 0.0
    total_transfer = 0.0
    # Iterate through each item.
    for item in items or []:
        parsed = item.get("parsed", {})
        amount = _receipt_amount(parsed.get("amount"), 0)
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
    """Apply the append saved summary lines operation in the Telegram handler layer.

    Args:
        lines: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        items: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        title: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    # Build summary for the response flow.
    summary = summarize_saved_transaction_items(items)
    lines.append(f"\n📊 *{title}:*")
    lines.append(f"- Pengeluaran: *{format_rupiah(summary['expense'])}*")
    lines.append(f"+ Pemasukan : *{format_rupiah(summary['income'])}*")
    if summary["transfer"]:
        lines.append(f"🔄 Transfer  : *{format_rupiah(summary['transfer'])}*")
    lines.append(f"📌 Net       : *{format_rupiah(summary['net'])}*")

def _clean_fronting_item_text(text: str, person: str = "") -> str:
    """Coordinate the clean fronting item text logic in the Telegram handler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        person: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
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


# Helper for fronting expense description.
def _fronting_expense_description(debt_parsed: dict) -> str:
    """Coordinate the fronting expense description logic in the Telegram handler layer.

    Args:
        debt_parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
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


# Helper for fronting expense category.
def _fronting_expense_category(debt_parsed: dict) -> str:
    """Coordinate the fronting expense category logic in the Telegram handler layer.

    Args:
        debt_parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep category name, type, symbol, and alias behavior consistent with the documented category flow.
    """
    raw = str(debt_parsed.get("raw_input") or "").strip()
    if raw:
        # Run this operation in a guarded block so failures can be handled.
        try:
            parsed = parse_with_regex(raw)
            category = str((parsed or {}).get("category") or "").strip()
            txn_type = str((parsed or {}).get("type") or "").strip().lower()
            if txn_type == "expense" and category:
                return category
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass
    return str(debt_parsed.get("category") or "Other Expense").strip() or "Other Expense"


# Helper for is ditalangin expense without balance.
def is_ditalangin_expense_without_balance(debt_parsed: dict) -> bool:
    """Check whether a condition is true for ditalangin expense without balance."""
    return (
        str(debt_parsed.get("cashflow_mode") or "").strip() == "debt_only"
        and str(debt_parsed.get("fronting_mode") or "").strip().lower() == "ditalangin"
        and str(debt_parsed.get("intent") or "").strip() == "add_payable"
    )


# Helper for normalize slash split syntax.
def normalize_slash_split_syntax(raw: str) -> str:
    """Normalize input values for the normalize slash split syntax workflow in the Telegram handler layer.

    Args:
        raw: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    text = str(raw or "")
    return re.sub(
        r"(\d+[\d.,]*\s*(?:rb|ribu|k|jt|juta)?)\s*/\s*(\d+)",
        r"\1 dibagi \2",
        text,
        flags=re.IGNORECASE,
    )


# Helper for enrich ditalangin split bill if any.
def enrich_ditalangin_split_bill_if_any(debt_parsed: dict, raw: str | None = None) -> dict:
    """Coordinate the enrich ditalangin split bill if any logic in the Telegram handler layer.

    Args:
        debt_parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        raw: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing isinstance(debt parsed, dict) or not is ditalangin expense wi before continuing.
    if not isinstance(debt_parsed, dict) or not is_ditalangin_expense_without_balance(debt_parsed):
        return debt_parsed

    raw_text = str(raw or debt_parsed.get("raw_input") or "")
    # Validate missing raw text before continuing.
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
    # Validate missing split bill before continuing.
    if not split_bill:
        return debt_parsed

    user_share = float(split_bill.get("user_share_amount", 0) or 0)
    total_amount = float(split_bill.get("total_amount", amount) or amount)
    participants = int(split_bill.get("participants", 0) or 0)

    # Handle user share <= 0 and participants > 0.
    if user_share <= 0 and participants > 0:
        user_share = total_amount / participants
    if user_share <= 0:
        return debt_parsed

    person_shares = split_bill.get("person_shares") or {}
    total_receivable = float(split_bill.get("total_receivable", 0) or 0)

    # Extract updated for validation.
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


# Helper for debt payment catatan.
def _debt_payment_catatan(debt_parsed: dict, raw: str) -> str:
    """Coordinate the debt payment catatan logic in the Telegram handler layer.

    Args:
        debt_parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        raw: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    parts = [str(raw or "").strip()]
    allocations = debt_parsed.get("debt_allocations") or []
    # Prepare alloc parts from the incoming input.
    alloc_parts = []
    # Iterate through each item.
    for item in allocations:
        debt_id = str(item.get("debt_id") or "").strip()
        amount = item.get("amount")
        # Store allocation notes only when both debt id and amount are present.
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


# Helper for build debt cashflow transaction.
def build_debt_cashflow_transaction(
    debt_parsed: dict,
    account: str,
    debt_type_for_payment: str | None = None,
) -> dict:
    """Build the transaction row payload for a parsed debt action.

    Args:
        debt_parsed: Parsed debt payload from `parse_debt_input`, including
            `intent`, `person_name`, `amount`, optional `cashflow_mode`, and
            optional debt identifiers created during save.
        account: Selected account name for debt actions that really move cash.
            Debt-only and offset actions ignore this value and set
            `skip_account=True`.
        debt_type_for_payment: Optional resolved payment direction. Use
            `payable` when the user pays their own debt and `receivable` when
            another person pays the user's receivable.

    Returns:
        A transaction dict ready for `save_transaction` or batch saving. When
        `cashflow_mode` is `debt_only`, the returned type is `debt_only` and
        the account balance must not change.
    """
    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or ""
    amount = debt_parsed.get("amount") or 0
    raw = debt_parsed.get("raw_input") or ""
    transaction_date = debt_parsed.get("date") or business_now().strftime("%Y-%m-%d")
    hutang_id = debt_parsed.get("hutang_id") or debt_parsed.get("debt_id") or debt_parsed.get("target_debt_id") or ""
    tipe_hutang = debt_parsed.get("tipe_hutang") or ""
    # Validate missing tipe hutang before continuing.
    if not tipe_hutang:
        if intent == "add_payable" or debt_type_for_payment == "payable":
            tipe_hutang = "utang"
        elif intent == "add_receivable" or debt_type_for_payment == "receivable":
            tipe_hutang = "piutang"


    if str(debt_parsed.get("cashflow_mode") or "").strip() == "debt_only":
        # Debt-only rows preserve the audit trail while deliberately skipping
        # account balance mutation.
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
            category = "Utang Tanpa Ubah Saldo"
            description = f"Catat utang ke {person} tanpa ubah saldo: {debt_parsed.get('description') or raw}"
        elif intent == "add_receivable":
            category = "Piutang Tanpa Ubah Saldo"
            description = f"Catat piutang ke {person} tanpa ubah saldo: {debt_parsed.get('description') or raw}"
        elif intent == "add_payment":
            category = "Pembayaran Debt Tanpa Ubah Saldo"
            description = f"Catat pembayaran debt {person} tanpa ubah saldo: {debt_parsed.get('description') or raw}"
        # Use the fallback path when no earlier branch matched.
        else:
            category = "Debt Tanpa Ubah Saldo"
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


# Helper for debt uses cashflow.
def debt_uses_cashflow(debt_parsed: dict) -> bool:
    """Coordinate the debt uses cashflow logic in the Telegram handler layer.

    Args:
        debt_parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    return str(debt_parsed.get("cashflow_mode") or "cashflow") != "debt_only"


# Helper for build debt only confirm preview.
def build_debt_only_confirm_preview(debt_parsed: dict) -> str:
    """Build a confirmation preview for debt actions without account movement.

    Args:
        debt_parsed: Parsed debt payload. The preview expects
            `cashflow_mode="debt_only"` for normal debt-only facts, or
            `intent="offset_debt"` for compensation without a bank account.

    Returns:
        Markdown text explaining the debt effect, transaction row effect, and
        the fact that account balances will not change before the user confirms
        the save action.
    """
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
            # Use the fallback path when no earlier branch matched.
            else:
                debt_effect = f"Anda punya utang ke {md_safe(person)}."
                transaction_effect = (
                    "Dicatat sebagai *pengeluaran* di sheet transactions agar masuk /harian, /mingguan, /bulanan, dan /budget.\n"
                    "Saldo rekening *tidak berubah* karena uang belum keluar dari rekening Anda."
                )
        # Use the fallback path when no earlier branch matched.
        else:
            title = "🟠 *Catat Utang Tanpa Ubah Saldo*"
            debt_effect = f"Anda punya utang ke {md_safe(person)}."
            transaction_effect = "Tetap dicatat di sheet transactions sebagai fact table, tetapi saldo rekening tidak berubah."
    elif intent == "add_receivable":
        title = "🟢 *Talangin / Piutang Tanpa Ubah Saldo*"
        debt_effect = f"{md_safe(person)} punya utang ke Anda."
        transaction_effect = "Tetap dicatat di sheet transactions sebagai fact table, tetapi saldo rekening tidak berubah."
    elif intent == "offset_debt":
        title = "🔁 *Kompensasi Hutang/Piutang*"
        target_label = "piutang" if debt_parsed.get("target_debt_type") == "receivable" else "utang"
        debt_effect = f"Memotong {target_label} aktif dengan {md_safe(person)} tanpa rekening."
        transaction_effect = "Tetap dicatat sebagai debt offset tanpa mengubah saldo rekening."
    # Use the fallback path when no earlier branch matched.
    else:
        title = "💸 *Debt Tanpa Ubah Saldo*"
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


# Helper for build debt initial preview.
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
    # Use the fallback path when no earlier branch matched.
    else:
        title = "💸 *Preview Debt*"
        effect = "Input debt terdeteksi."

    if debt_uses_cashflow(debt_parsed) and intent != "offset_debt":
        next_step = "Jika lanjut, bot akan meminta rekening cashflow sebelum konfirmasi simpan."
    # Use the fallback path when no earlier branch matched.
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


# Helper for build debt short summary.
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

# Helper for build debt account prompt.
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

    # Use the fallback path when no earlier branch matched.
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

# Helper for build debt confirm preview.
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
    # Use the fallback path when no earlier branch matched.
    else:
        title = "❓ *Debt*"
        debt_effect = "-"

    cashflow_type = {
        "expense": "- Pengeluaran",
        "income": "+ Cash In / Pemasukan",
        "transfer": "🔄 Transfer",
        "debt_offset": "🔁 Debt Offset / Tanpa Rekening",
        "debt_only": "📝 Debt Fact / Tanpa Rekening",
    }.get(transaction_parsed.get("type"), "❓")
    if transaction_parsed.get("type") == "expense" and transaction_parsed.get("skip_account"):
        cashflow_type = "- Pengeluaran / tanpa update saldo rekening"

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

# Helper for build debt batch confirm preview.
def build_debt_batch_confirm_preview(
    debt_items: list[dict],
    account: str,
) -> str:
    """Build the data structure or message text for debt batch confirm preview."""
    lines = ["🧾 *Preview Batch Utang/Piutang*\n"]

    total_cash_in = 0
    total_cash_out = 0

    # Iterate through each i, item.
    for i, item in enumerate(debt_items, 1):
        parsed = item["parsed"]
        intent = parsed.get("intent")
        person = parsed.get("person_name") or "-"
        amount = _receipt_amount(parsed.get("amount"), 0)
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
            cashflow_label = "+ Cash In"
            total_cash_in += amount
        elif txn_type == "expense":
            if transaction_parsed.get("skip_account"):
                cashflow_label = "- Expense fact / tanpa update saldo"
            # Use the fallback path when no earlier branch matched.
            else:
                cashflow_label = "- Cash Out"
                total_cash_out += amount
        elif txn_type == "debt_offset":
            cashflow_label = "🔁 Debt Offset / tanpa rekening"
        elif txn_type == "debt_only":
            cashflow_label = "📝 Debt fact / tanpa rekening"
        # Use the fallback path when no earlier branch matched.
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
        # Use the fallback path when no earlier branch matched.
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
    lines.append(f"+ Total Cash In : *{format_rupiah(total_cash_in)}*")
    lines.append(f"- Total Cash Out: *{format_rupiah(total_cash_out)}*")
    lines.append("\nSimpan semua utang/piutang ini?")

    return "\n".join(lines)

# Helper for build debt batch account prompt.
def build_debt_batch_account_prompt(debt_items: list[dict]) -> str:
    """Build the data structure or message text for debt batch account prompt."""
    lines = [f"🧾 *Ditemukan {len(debt_items)} input utang/piutang:*\n"]

    total_cash_in = 0
    total_cash_out = 0

    # Iterate through each i, item.
    for i, item in enumerate(debt_items, 1):
        parsed = item["parsed"]
        intent = parsed.get("intent")
        person = parsed.get("person_name") or "-"
        amount = _receipt_amount(parsed.get("amount"), 0)

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

        # Use the fallback path when no earlier branch matched.
        else:
            label = "❓ Debt"
            effect = "-"

        lines.append(
            f"{i}. {label}\n"
            f"   👤 {person}\n"
            f"   💰 {format_rupiah(amount)}\n"
            f"   📌 {effect}"
        )

    # Keep this section separated from the surrounding flow.
    lines.append("\n*Estimasi cashflow awal:*")
    # Keep this section separated from the surrounding flow.
    lines.append(f"+ Cash In : *{format_rupiah(total_cash_in)}*")
    # Keep this section separated from the surrounding flow.
    lines.append(f"- Cash Out: *{format_rupiah(total_cash_out)}*")
    # Keep this section separated from the surrounding flow.
    lines.append("\n💳 Pilih rekening cashflow untuk semua item, atau pilih *Sudah berlalu* jika hanya ingin mencatat debt tanpa mengubah saldo:")

    # Keep this section separated from the surrounding flow.
    return "\n".join(lines)


# ── Command Handlers ──────────────────────────────────────────────────────────

