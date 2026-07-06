"""Preview and state helpers for transaction, mixed input, debt, split bill, pending expense, asset, and edit flows."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *
# Import app.bot.handler_parts.networth_assets so this module can use its helpers.
from app.bot.handler_parts.networth_assets import build_asset_confirm_preview
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import resolve_parsed_transaction
# Import app.nlp.regex_parser so this module can use its helpers.
from app.nlp.regex_parser import detect_category, detect_account
# Import app.nlp.normalizer so this module can use its helpers.
from app.nlp.normalizer import normalize_text


# Define parse input for callers in this flow.
def parse_input(text: str) -> dict:
    """Parse caller input for the parse input workflow in the Telegram handler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Prepare result for the next step.
    result = parse_with_regex(text)
    # Handle the case where result is None.
    if result is None:
        # Prepare result for the next step.
        result = parse_with_pending_fallback(text)

    if isinstance(result, dict) and result.get("type") in {"expense", "income", "transfer"}:
        # Return resolve_parsed_transaction(result, text) to the caller.
        return resolve_parsed_transaction(result, text)

    # Return result to the caller.
    return result


# Define build progress bar for callers in this flow.
def build_progress_bar(pct: float, length: int = 10) -> str:
    """Build the data structure or message text for progress bar."""
    # Prepare filled for the next step.
    filled = int(min(float(pct or 0), 100) / 100 * length)
    # Prepare empty for the next step.
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"


# Define split user inputs for callers in this flow.
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
    # Handle the missing or empty text case.
    if not text:
        # Return [] to the caller.
        return []

    # Prepare raw for the next step.
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
    # Close the structure that was opened above.
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
    # Close the structure that was opened above.
    ]

    # Prepare all starters for the next step.
    all_starters = transaction_starters + debt_starters
    starter_pattern = "|".join(re.escape(k) for k in sorted(all_starters, key=len, reverse=True))

    # Pecah "dan beli", "dan minjem", dst.
    raw = re.sub(
        rf"\s+dan\s+(?=({starter_pattern})\b)",
        " ||| ",
        # Include this value in the surrounding collection or call.
        raw,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Debt flow section
    # Debt flow section
    protected_debt_payment = re.search(
        r"\b(bayar|byr|lunasi|lunas|cicil)\s+(hutang|utang)\b",
        # Include this value in the surrounding collection or call.
        raw,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    if protected_debt_payment and "|||" not in raw:
        return [raw.strip(" .,-;")]

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    amount_before_pattern = r"(?:\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)?|\d{4,})"

    # Open a multi-line structure for the values below.
    raw = re.sub(
        rf"({amount_before_pattern})\s+(?=({starter_pattern})\b)",
        r"\1 ||| ",
        # Include this value in the surrounding collection or call.
        raw,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Account flow section
    # Account flow section
    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.

    # Prepare parts for the next step.
    parts = []
    for part in raw.split("|||"):
        clean = part.strip(" .,-;")
        # Handle the case where clean.
        if clean:
            # Update parts with the current value.
            parts.append(clean)

    # Return parts to the caller.
    return parts

# Define needs account for callers in this flow.
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
        # Return False to the caller.
        return False

    if txn_type in ["expense", "income"] and not parsed.get("account"):
        # Return True to the caller.
        return True

    if txn_type == "transfer" and (not parsed.get("account") or not parsed.get("to_account")):
        # Return True to the caller.
        return True

    # Return False to the caller.
    return False

# Define is debt item for callers in this flow.
def is_debt_item(parsed: dict) -> bool:
    """Check whether a condition is true for debt item."""
    return parsed.get("kind") == "debt"


# Define is transaction item for callers in this flow.
def is_transaction_item(parsed: dict) -> bool:
    """Check whether a condition is true for transaction item."""
    return parsed.get("kind") == "transaction"


# Define build mixed preview for callers in this flow.
def build_mixed_preview(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed preview."""
    lines = [f"🧾 *Ditemukan {len(mixed_items)} item:*\n"]

    # Prepare total expense for the next step.
    total_expense = 0
    # Prepare total income for the next step.
    total_income = 0
    # Prepare total debt for the next step.
    total_debt = 0

    # Process each i, item in the current collection.
    for i, item in enumerate(mixed_items, 1):
        kind = item["kind"]
        raw = item["raw"]

        if kind == "transaction":
            parsed = item["parsed"]
            txn_type = parsed.get("type")
            amount = _receipt_amount(parsed.get("amount"), 0)

            if txn_type == "expense":
                icon = "❌"
                # Run this statement as part of the current workflow.
                total_expense += amount
            elif txn_type == "income":
                icon = "✅"
                # Run this statement as part of the current workflow.
                total_income += amount
            # Handle the fallback path after earlier conditions are skipped.
            else:
                icon = "🔄"

            desc = md_safe(parsed.get('description') or '-')
            category = md_safe(parsed.get('category') or '-')
            account = md_safe(parsed.get('account') or '-')
            date = md_safe(parsed.get('date') or '-')
            # Prepare safe raw for the next step.
            safe_raw = md_safe(raw)
            # Prepare split preview for the next step.
            split_preview = format_split_bill_preview_line(parsed)
            split_line = f"   {md_safe(split_preview)}\n" if split_preview else ""

            # Open a multi-line structure for the values below.
            lines.append(
                f"{i}. {icon} *Transaksi*\n"
                f"   📝 {desc}\n"
                f"   💰 {format_rupiah(amount)} | {category}\n"
                f"   📅 {date}\n"
                f"   🏦 {account}\n"
                # Run this statement as part of the current workflow.
                f"{split_line}"
                f"   Input: `{safe_raw}`"
            # Close the structure that was opened above.
            )

        elif kind == "debt":
            parsed = item["parsed"]
            intent = parsed.get("intent")
            person = parsed.get("person_name") or "-"
            amount = _receipt_amount(parsed.get("amount"), 0)
            # Run this statement as part of the current workflow.
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
            # Handle the fallback path after earlier conditions are skipped.
            else:
                label = "❓ Debt"
                effect = "-"

            # Prepare safe person for the next step.
            safe_person = md_safe(person)
            account = md_safe(parsed.get('account') or '-')
            date = md_safe(parsed.get('date') or parsed.get('transaction_date') or '-')
            # Prepare safe raw for the next step.
            safe_raw = md_safe(raw)

            # Open a multi-line structure for the values below.
            lines.append(
                f"{i}. {label}\n"
                f"   👤 {safe_person}\n"
                f"   💰 {format_rupiah(amount)}\n"
                f"   📅 {date}\n"
                f"   🏦 {account}\n"
                f"   📌 {effect}\n"
                f"   Input: `{safe_raw}`"
            # Close the structure that was opened above.
            )

    lines.append("\n*Ringkasan awal:*")
    lines.append(f"❌ Transaksi Expense: *{format_rupiah(total_expense)}*")
    lines.append(f"✅ Transaksi Income : *{format_rupiah(total_income)}*")
    lines.append(f"💸 Total Nominal Debt: *{format_rupiah(total_debt)}*")

    # Prepare account summary for the next step.
    account_summary = build_account_delta_summary_from_transaction_items(mixed_items)
    # Handle the case where account_summary.
    if account_summary:
        # Update lines with the current value.
        lines.append(account_summary)

    return "\n".join(lines)



# Define mixed transaction totals for callers in this flow.
def _mixed_transaction_totals(mixed_items: list[dict]) -> dict:
    """Summarize transaction and debt totals for a mixed preview."""
    # Open a multi-line structure for the values below.
    totals = {
        "expense": 0.0,
        "income": 0.0,
        "transfer": 0.0,
        "debt": 0.0,
        "transaction_count": 0,
        "debt_count": 0,
    # Close the structure that was opened above.
    }
    # Process each item in the current collection.
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
    # Return totals to the caller.
    return totals


# Define build mixed category summary for callers in this flow.
def build_mixed_category_summary(mixed_items: list[dict]) -> str:
    """Build a compact category summary for the final mixed preview."""
    # Run this statement as part of the current workflow.
    summary: dict[str, dict[str, float | int]] = {}
    # Process each item in the current collection.
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

    # Handle the missing or empty summary case.
    if not summary:
        return ""

    lines = ["📁 *Ringkasan kategori:*"]
    # Process each category, data in the current collection.
    for category, data in sorted(summary.items(), key=lambda kv: str(kv[0]).lower()):
        # Open a multi-line structure for the values below.
        lines.append(
            f"• {md_safe(category)}: *{format_rupiah(float(data['amount'] or 0))}* "
            f"({int(data['count'] or 0)} item)"
        # Close the structure that was opened above.
        )
    return "\n".join(lines)


# Define mixed item detail lines for callers in this flow.
def _mixed_item_detail_lines(item: dict, index: int) -> list[str]:
    """Build detailed lines for one mixed item before account selection."""
    kind = item.get("kind") if isinstance(item, dict) else None
    parsed = item.get("parsed", {}) if isinstance(item, dict) else {}

    if kind == "transaction":
        # Open a multi-line structure for the values below.
        type_label = {
            "expense": "❌ Pengeluaran",
            "income": "✅ Pemasukan",
            "transfer": "🔄 Transfer",
        }.get(parsed.get("type"), "❓ Transaksi")
        lines = [f"{index}. *{type_label}*"]
        lines.append(f"   💰 Nominal : {format_rupiah(_receipt_amount(parsed.get('amount'), 0))}")
        lines.append(f"   📁 Kategori: {md_safe(parsed.get('category') or '-')}")
        lines.append(f"   👤 Subjek  : {md_safe(parsed.get('subject') or '-')}")
        lines.append(f"   📝 Deskripsi: {md_safe(parsed.get('description') or '-')}")
        # Prepare split preview for the next step.
        split_preview = format_split_bill_preview_line(parsed)
        # Handle the case where split_preview.
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
        # Return lines to the caller.
        return lines

    if kind == "debt":
        intent = parsed.get("intent")
        # Open a multi-line structure for the values below.
        label = {
            "add_receivable": "🟢 Piutang baru",
            "add_payable": "🔴 Utang baru",
            "add_payment": "💸 Pembayaran debt",
            "offset_debt": "🔁 Kompensasi debt",
        }.get(intent, "💸 Debt")
        # Return [ to the caller.
        return [
            f"{index}. *{label}*",
            f"   👤 Orang   : {md_safe(parsed.get('person_name') or '-')}",
            f"   💰 Nominal : {format_rupiah(_receipt_amount(parsed.get('amount'), 0))}",
            f"   📝 Deskripsi: {md_safe(parsed.get('description') or '-')}",
            f"   📅 Tanggal : {md_safe(parsed.get('date') or parsed.get('transaction_date') or '-')}",
            f"   🏦 Rekening: {md_safe(parsed.get('account') or '-')}",
        # Close the structure that was opened above.
        ]

    return [f"{index}. {md_safe(item.get('raw') or '-')}"]


# Define build mixed detail preview for callers in this flow.
def build_mixed_detail_preview(mixed_items: list[dict], receipt_context: dict | None = None) -> str:
    """Build the detailed multi-input preview shown before rekening selection."""
    # Prepare receipt context for the next step.
    receipt_context = receipt_context or {}

    # Natural multi-input should use the compact preview format from the flow doc.
    # Keep receipt/batch preview below because receipt mode still needs merchant and extra-charge details.
    if not receipt_context:
        # Return build_batch_preview(mixed_items) to the caller.
        return build_batch_preview(mixed_items)

    receipt = receipt_context.get("receipt") or {}
    merchant = _receipt_merchant(receipt, [item.get("parsed", {}) for item in mixed_items])
    # Prepare totals for the next step.
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

    # Prepare category summary for the next step.
    category_summary = build_mixed_category_summary(mixed_items)
    # Handle the case where category_summary.
    if category_summary:
        lines.extend(["", category_summary])

    lines.append("")
    lines.append("📋 *Rincian transaksi yang akan disimpan:*")
    # Process each idx, item in the current collection.
    for idx, item in enumerate(mixed_items or [], 1):
        # Update lines with the current value.
        lines.extend(_mixed_item_detail_lines(item, idx))
        # Handle the case where idx != len(mixed_items or []).
        if idx != len(mixed_items or []):
            lines.append("")

    # Prepare charges for the next step.
    charges = _receipt_extra_charges(receipt)
    # Handle the case where charges.
    if charges:
        lines.extend(["", "💳 *Rincian biaya tambahan di output:*"])
        divisor = receipt_context.get("extra_charge_divisor")
        # Process each charge in the current collection.
        for charge in charges:
            amount = int(charge.get("amount", 0) or 0)
            sign = "-" if charge.get("is_discount") else ""
            # Handle the case where divisor and divisor > 1.
            if divisor and divisor > 1:
                # Prepare share for the next step.
                share = int(round(amount / divisor))
                # Open a multi-line structure for the values below.
                lines.append(
                    f"• {md_safe(charge.get('label'))}: {sign}{format_rupiah(amount)} / {divisor} = {sign}{format_rupiah(share)}"
                # Close the structure that was opened above.
                )
            # Handle the fallback path after earlier conditions are skipped.
            else:
                lines.append(f"• {md_safe(charge.get('label'))}: {sign}{format_rupiah(amount)}")
        lines.append(f"• Total biaya tambahan kamu: *{format_rupiah(receipt_context.get('extra_charge_amount', 0))}*")
        lines.append("\nCatatan: saat disimpan, service/PPN/diskon digabung menjadi satu transaksi biaya tambahan.")

    return "\n".join(lines)


# Define build mixed final summary for callers in this flow.
def build_mixed_final_summary(mixed_items: list[dict], receipt_context: dict | None = None, account_label: str | None = None) -> str:
    """Build a compact final confirmation summary for mixed or receipt batches."""
    # Prepare receipt context for the next step.
    receipt_context = receipt_context or {}
    receipt = receipt_context.get("receipt") or {}
    merchant = _receipt_merchant(receipt, [item.get("parsed", {}) for item in mixed_items]) if receipt_context else ""
    # Prepare totals for the next step.
    totals = _mixed_transaction_totals(mixed_items)

    # Handle the case where receipt_context.
    if receipt_context:
        mode_label = "semua struk" if receipt_context.get("mode") == "all" else "bagian struk"
        lines = [f"🧾 *Ringkasan batch dari {mode_label}*"]
        lines.append(f"• Merchant: *{md_safe(merchant)}*")
    # Handle the fallback path after earlier conditions are skipped.
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

    # Prepare account for the next step.
    account = account_label
    # Handle the missing or empty account case.
    if not account:
        # Process each item in the current collection.
        for item in mixed_items or []:
            parsed = item.get("parsed", {}) if isinstance(item, dict) else {}
            if parsed.get("account"):
                account = parsed.get("account")
                # Leave the loop after the target condition has been reached.
                break
    # Handle the case where account.
    if account:
        lines.append(f"• Rekening: {md_safe(account)}")

    # Prepare category summary for the next step.
    category_summary = build_mixed_category_summary(mixed_items)
    # Handle the case where category_summary.
    if category_summary:
        lines.extend(["", category_summary])

    # Prepare account summary for the next step.
    account_summary = build_account_delta_summary_from_transaction_items(mixed_items)
    # Handle the case where account_summary.
    if account_summary:
        lines.extend(["", account_summary])

    return "\n".join(lines)

# Define parse income missing amount for callers in this flow.
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
    # Handle the missing or empty raw case.
    if not raw:
        # Return None to the caller.
        return None

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    without_date = strip_date_phrases(raw)
    if parse_human_amount(without_date) > 0 and re.search(r"\d", without_date):
        # Return None to the caller.
        return None

    # Account flow section
    low = raw.lower()
    if re.search(r"\bdari\s+[^\n]+?\s+ke\s+", low):
        # Return None to the caller.
        return None

    # Open a multi-line structure for the values below.
    match = re.search(
        r"^\s*(?:transaksi|transfer(?:an)?|tf|trf|kiriman|uang)\s+(?:masuk\s+)?dari\s+(.+?)\s*$",
        # Include this value in the surrounding collection or call.
        raw,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the missing or empty match case.
    if not match:
        # Open a multi-line structure for the values below.
        expense_like = re.search(
            r"\b(?:beli|bayar|byr|jajan|makan|minum|ngopi|belanja|isi|top\s*up|topup)\b",
            # Include this value in the surrounding collection or call.
            raw,
            # Prepare flags for the next step.
            flags=re.IGNORECASE,
        # Close the structure that was opened above.
        )
        # Handle the missing or empty expense_like case.
        if not expense_like:
            # Return None to the caller.
            return None

        # Prepare description for the next step.
        description = strip_date_phrases(raw)
        description = re.sub(r"\b(?:dari|via|pakai|pake|ke|rekening)\s+[A-Za-zÀ-ÿ0-9\s]+$", " ", description, flags=re.IGNORECASE)
        description = re.sub(r"^\s*(?:beli|bayar|byr|jajan|makan|minum|ngopi|belanja|isi|top\s*up|topup)\s+", " ", description, flags=re.IGNORECASE)
        description = re.sub(r"\s+", " ", description).strip(" .,-;") or "Expense"
        # Return { to the caller.
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
        # Close the structure that was opened above.
        }

    # Prepare person raw for the next step.
    person_raw = match.group(1).strip()
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    person_raw = re.sub(r"\b(?:tgl|tanggal)\s*\d{1,2}(?:[-/]\d{1,2}(?:[-/]\d{2,4})?)?\b", " ", person_raw, flags=re.IGNORECASE)
    person_raw = re.sub(r"\b(?:hari\s+ini|kemarin|besok)\b", " ", person_raw, flags=re.IGNORECASE)
    person = re.sub(r"\s+", " ", person_raw).strip(" .,-;")

    # Handle the missing or empty person case.
    if not person:
        # Return None to the caller.
        return None

    account_like = {"cash", "bri", "bsi", "bca", "dana", "gopay", "seabank", "sea bank"}
    # Handle the case where person.lower() in account_like.
    if person.lower() in account_like:
        # Return None to the caller.
        return None

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }


# Define build missing amount prompt for callers in this flow.
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
    # Handle the case where current is not None and total is not None and total > 1.
    if current is not None and total is not None and total > 1:
        prefix = f"🧩 *Nominal kurang {current}/{total}*\n\n"

    desc = md_safe(parsed.get("description") or raw)
    date = md_safe(parsed.get("date") or "-")
    # Return ( to the caller.
    return (
        f"{prefix}🤔 Saya mendeteksi income, tapi nominalnya belum ada.\n\n"
        f"📝 Item: *{desc}*\n"
        f"📅 Tanggal: *{date}*\n"
        f"📌 Input: `{md_safe(raw)}`\n\n"
        "Nominalnya berapa? Contoh: `13k`, `50000`, atau `94k/2`."
    # Close the structure that was opened above.
    )


# Define finalize missing amount item for callers in this flow.
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
    # Return { to the caller.
    return {
        "kind": "transaction",
        "parsed": parsed,
        "raw": item.get("raw") or parsed.get("catatan") or "",
    # Close the structure that was opened above.
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

    # Prepare preview for the next step.
    preview = build_mixed_detail_preview(mixed_items)

    # Handle the case where mixed_split_bill_needs_decision(mixed_items).
    if mixed_split_bill_needs_decision(mixed_items):
        # Wait for reply_update_safely before continuing this flow.
        await reply_update_safely(
            # Include this value in the surrounding collection or call.
            update,
            # Include this value in the surrounding collection or call.
            build_mixed_split_bill_queue_prompt(mixed_items),
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=mixed_split_bill_keyboard(mixed_items),
        # Close the structure that was opened above.
        )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Wait for reply_update_safely before continuing this flow.
        await reply_update_safely(
            # Include this value in the surrounding collection or call.
            update,
            f"{preview}\n\n{preview_action_question(False)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", False),
        # Close the structure that was opened above.
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
    # Handle the missing or empty state case.
    if not state:
        # Return False to the caller.
        return False

    # Prepare amount for the next step.
    amount = parse_human_amount(user_text)
    # Handle the missing or empty amount or amount <= 0 case.
    if not amount or amount <= 0:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Nominalnya belum kebaca. Coba tulis seperti `13k`, `50000`, atau `94k/2`.",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    scope = state.get("scope")
    if scope == "mixed":
        mixed_items = state.get("mixed_items") or []
        missing_indices = state.get("missing_indices") or []
        current = int(state.get("current") or 0)

        # Handle the case where current >= len(missing_indices).
        if current >= len(missing_indices):
            context.user_data.pop("pending_missing_amount", None)
            await update.message.reply_text("❌ Tidak ada input kurang nominal yang sedang menunggu jawaban.")
            # Return True to the caller.
            return True

        # Prepare idx for the next step.
        idx = missing_indices[current]
        # Handle the case where 0 <= idx < len(mixed_items).
        if 0 <= idx < len(mixed_items):
            # Run this statement as part of the current workflow.
            mixed_items[idx] = finalize_missing_amount_item(mixed_items[idx], amount)

        # Run this statement as part of the current workflow.
        current += 1
        # Handle the case where current < len(missing_indices).
        if current < len(missing_indices):
            state["mixed_items"] = mixed_items
            state["current"] = current
            context.user_data["pending_missing_amount"] = state
            # Prepare next idx for the next step.
            next_idx = missing_indices[current]
            # Prepare next item for the next step.
            next_item = mixed_items[next_idx]
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                build_missing_amount_prompt(next_item.get("raw", ""), next_item.get("parsed", {}), current + 1, len(missing_indices)),
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        context.user_data.pop("pending_missing_amount", None)
        # Wait for continue_after_missing_amount_mixed before continuing this flow.
        await continue_after_missing_amount_mixed(update, context, mixed_items)
        # Return True to the caller.
        return True

    if scope == "single":
        item = state.get("item") or {}
        # Prepare finalized for the next step.
        finalized = finalize_missing_amount_item(item, amount)
        parsed = finalized["parsed"]
        context.user_data["pending_parsed"] = parsed
        context.user_data["pending_raw"] = finalized.get("raw") or user_text
        context.user_data.pop("pending_missing_amount", None)
        context.user_data.pop("pending_batch", None)
        context.user_data.pop("pending_debt", None)
        context.user_data.pop("pending_debt_batch", None)
        context.user_data.pop("pending_mixed", None)

        # Handle the case where needs_account(parsed).
        if needs_account(parsed):
            # Wait for reply_update_safely before continuing this flow.
            await reply_update_safely(
                # Include this value in the surrounding collection or call.
                update,
                # Include this value in the surrounding collection or call.
                build_single_account_prompt(parsed),
                parse_mode="Markdown",
                reply_markup=account_keyboard("acc"),
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Prepare preview for the next step.
        preview = build_preview(parsed)
        # Wait for reply_update_safely before continuing this flow.
        await reply_update_safely(
            # Include this value in the surrounding collection or call.
            update,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("single", True),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    context.user_data.pop("pending_missing_amount", None)
    # Return False to the caller.
    return False


# Define parse mixed item for callers in this flow.
def parse_mixed_item(line: str) -> dict:
    """Parse caller input for the parse mixed item workflow in the Telegram handler layer.

    Args:
        line: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Prepare debt parsed for the next step.
    debt_parsed = parse_debt_input(line)
    # Handle the case where debt_parsed.
    if debt_parsed:
        # Prepare debt parsed for the next step.
        debt_parsed = enrich_ditalangin_split_bill_if_any(debt_parsed, line)
        # Return { to the caller.
        return {
            "kind": "debt",
            "parsed": debt_parsed,
            "raw": line,
        # Close the structure that was opened above.
        }

    # Prepare missing amount income for the next step.
    missing_amount_income = parse_income_missing_amount(line)
    # Handle the case where missing_amount_income.
    if missing_amount_income:
        # Return { to the caller.
        return {
            "kind": "missing_amount",
            "parsed": missing_amount_income,
            "raw": line,
        # Close the structure that was opened above.
        }

    # Prepare txn parsed for the next step.
    txn_parsed = parse_input(line)
    if txn_parsed and txn_parsed.get("type") != "pending":
        # Run this statement as part of the current workflow.
        attach_split_bill_if_any(txn_parsed, line)
        # Return { to the caller.
        return {
            "kind": "transaction",
            "parsed": txn_parsed,
            "raw": line,
        # Close the structure that was opened above.
        }

    # Return { to the caller.
    return {
        "kind": "failed",
        "parsed": {},
        "raw": line,
    # Close the structure that was opened above.
    }

# Define mixed needs account for callers in this flow.
def mixed_needs_account(mixed_items: list[dict]) -> bool:
    """Check whether a mixed input still needs a rekening selection.

    Args:
        mixed_items: Parsed mixed items from one user input. Each item may be a
            normal transaction or a debt-related item.

    Returns:
        True if at least one cashflow item has no rekening yet, otherwise False.
    """
    # Process each item in the current collection.
    for item in mixed_items:
        parsed = item["parsed"]

        if item["kind"] == "transaction" and needs_account(parsed):
            # Return True to the caller.
            return True

        if item["kind"] == "debt" and debt_uses_cashflow(parsed) and not parsed.get("account"):
            # Return True to the caller.
            return True

    # Return False to the caller.
    return False


# Define edit or continue keyboard for callers in this flow.
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
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        # Open a multi-line structure for the values below.
        [
            InlineKeyboardButton("✏️ Edit dulu", callback_data=f"editflow:edit:{scope}"),
            InlineKeyboardButton("➡️ Lanjut", callback_data=f"editflow:continue:{scope}"),
        # Close the structure that was opened above.
        ],
        [InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")],
    # Close the structure that was opened above.
    ])


# Define confirm target for edit scope for callers in this flow.
def _confirm_target_for_edit_scope(scope: str) -> str:
    """Map a preview edit scope to the confirm callback target.

    Args:
        scope: Current preview scope. The `single` scope is stored as
            `pending_parsed`, but its save callback still uses `confirm:pending`.

    Returns:
        Callback target used by the save button.
    """
    return "pending" if scope == "single" else scope


# Define save edit cancel keyboard for callers in this flow.
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
    # Prepare confirm target for the next step.
    confirm_target = _confirm_target_for_edit_scope(scope)
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        # Open a multi-line structure for the values below.
        [
            InlineKeyboardButton("✅ Simpan", callback_data=f"confirm:{confirm_target}"),
            InlineKeyboardButton("✏️ Edit dulu", callback_data=f"editflow:edit:{scope}"),
        # Close the structure that was opened above.
        ],
        [InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")],
    # Close the structure that was opened above.
    ])


# Define preview action keyboard for callers in this flow.
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
    # Return save_edit_cancel_keyboard(scope) if ready_to_save else edit_o... to the caller.
    return save_edit_cancel_keyboard(scope) if ready_to_save else edit_or_continue_keyboard(scope)


# Define preview action question for callers in this flow.
def preview_action_question(ready_to_save: bool) -> str:
    """Return the short question shown below a preview.

    Args:
        ready_to_save: Whether the preview can be saved immediately.

    Returns:
        User-facing question for the current preview state.
    """
    # Handle the case where ready_to_save.
    if ready_to_save:
        return "Mau simpan, edit dulu, atau batal?"
    return "Mau edit dulu atau lanjut ke rekening/simpan?"


# Define single ready to save for callers in this flow.
def single_ready_to_save(parsed: dict) -> bool:
    """Check whether a single transaction preview can be saved.

    Args:
        parsed: Parsed transaction candidate.

    Returns:
        True when the transaction no longer needs split bill or rekening
        decisions.
    """
    # Return not split_bill_needs_decision(parsed) and not needs_account(p... to the caller.
    return not split_bill_needs_decision(parsed) and not needs_account(parsed)


# Define mixed ready to save for callers in this flow.
def mixed_ready_to_save(mixed_items: list[dict]) -> bool:
    """Check whether a mixed input preview can be saved.

    Args:
        mixed_items: Parsed items from a multi-line or mixed natural input.

    Returns:
        True when every item has completed the required split bill and rekening
        decisions.
    """
    # Return not mixed_split_bill_needs_decision(mixed_items) and not mixe... to the caller.
    return not mixed_split_bill_needs_decision(mixed_items) and not mixed_needs_account(mixed_items)


# Define debt ready to save for callers in this flow.
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
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines = ["⚠️ *Saya agak ragu dengan hasil parsing ini.*"]

    # Handle the case where reasons.
    if reasons:
        lines.append("\n*Alasan:*")
        # Process each reason in the current collection.
        for reason in reasons[:4]:
            lines.append(f"• {md_safe(reason)}")

    return "\n".join(lines)


def build_preview_with_parse_safety(parsed: dict, assessment: dict, mode: str = "warning") -> str:
    """Build the data structure or message text for preview with parse safety."""
    return f"{build_parse_safety_notice(assessment, mode)}\n\n{build_preview(parsed)}"


# Define build pending expense confirm preview for callers in this flow.
def build_pending_expense_confirm_preview(item: dict, include_question: bool = True) -> str:
    """Build the data structure or message text for pending expense confirm preview."""
    # Prepare item for the next step.
    item = dict(item or {})
    due_date = str(item.get("due_date") or "").strip()
    due_precision = str(item.get("due_precision") or "unknown").strip().lower()
    month = str(item.get("month") or "-").strip()
    # Handle the case where due_date.
    if due_date:
        # Prepare due text for the next step.
        due_text = due_date
    elif due_precision == "month":
        due_text = f"{month} (tanggal belum pasti)"
    # Handle the fallback path after earlier conditions are skipped.
    else:
        due_text = "Belum pasti"

    account = str(item.get("account") or "-").strip() or "-"
    category = str(item.get("category") or "Other Expense").strip()
    status = str(item.get("status") or "pending").strip()
    subject = str(item.get("subject") or item.get("description") or "Pending Expense").strip()
    description = str(item.get("description") or subject).strip()
    amount = float(item.get("amount", 0) or 0)

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    ]
    # Handle the case where include_question.
    if include_question:
        lines.append("Simpan pending expense ini?")
    return "\n".join(lines)


# Define parse clarification keyboard for callers in this flow.
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
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Orang ini bayar ke saya", callback_data="clarify_parse:debt_payment")],
        [InlineKeyboardButton("🔴 Saya hutang ke orang ini", callback_data="clarify_parse:payable")],
        [InlineKeyboardButton("🧾 Pengeluaran biasa", callback_data="clarify_parse:expense")],
        [InlineKeyboardButton("👤 Orang lain yang bayar", callback_data="clarify_parse:no_cashflow")],
        [InlineKeyboardButton("🤝 Split bill", callback_data="clarify_parse:split")],
        [InlineKeyboardButton("🙋 Saya talangin", callback_data="clarify_parse:fronting")],
        [InlineKeyboardButton("✍️ Tulis ulang", callback_data="clarify_parse:rewrite")],
        [InlineKeyboardButton("🚫 Batal", callback_data="cancel:clarification")],
    # Close the structure that was opened above.
    ])


# Define build parse clarification prompt for callers in this flow.
def build_parse_clarification_prompt(raw: str, assessment: dict | None = None) -> str:
    """Build the data structure or message text for parse clarification prompt."""
    # Prepare safe raw for the next step.
    safe_raw = md_safe(raw)
    # Open a multi-line structure for the values below.
    lines = [
        "🤔 *Saya belum yakin maksud input ini:*",
        "",
        f'"{safe_raw}"',
    # Close the structure that was opened above.
    ]

    reasons = [str(r).strip() for r in (assessment or {}).get("reasons", []) if str(r).strip()]
    # Handle the case where reasons.
    if reasons:
        lines.append("\n*Kenapa ditanya dulu:*")
        # Process each reason in the current collection.
        for reason in reasons[:3]:
            lines.append(f"• {md_safe(reason)}")

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    ])
    return "\n".join(lines)



# ── Phase 2: social-money ambiguity and split bill wizard helpers ─────────────

SOCIAL_MEAL_KEYWORDS = r"(?:makan|minum|ngopi|lunch|dinner|brunch|jajan)"
SOCIAL_FRIEND_MARKER = r"(?:bareng|sama|dengan|ama)"


# Define extract people from social input for callers in this flow.
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
    # Handle the missing or empty clean case.
    if not clean:
        # Return [] to the caller.
        return []

    # Open a multi-line structure for the values below.
    match = re.search(
        rf"\b{SOCIAL_FRIEND_MARKER}\s+(?P<names>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{{0,100}}?)(?=\s*(?:\d|rp|idr|tanggal|tgl|kemarin|hari\s+ini|besok|dari|via|pakai|pake|$))",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the missing or empty match case.
    if not match:
        # Open a multi-line structure for the values below.
        match = re.search(
            rf"\b{SOCIAL_MEAL_KEYWORDS}\s+{SOCIAL_FRIEND_MARKER}\s+(?P<names>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{{0,100}}?)(?=\s*(?:\d|rp|idr|tanggal|tgl|kemarin|hari\s+ini|besok|dari|via|pakai|pake|$))",
            # Include this value in the surrounding collection or call.
            clean,
            # Prepare flags for the next step.
            flags=re.IGNORECASE,
        # Close the structure that was opened above.
        )
    # Handle the missing or empty match case.
    if not match:
        # Return [] to the caller.
        return []

    names = split_split_bill_person_names(match.group("names") or "")
    noise = {"makan", "minum", "ngopi", "lunch", "dinner", "brunch", "jajan"}
    # Prepare result for the next step.
    result = []
    # Prepare seen for the next step.
    seen = set()
    # Process each name in the current collection.
    for name in names:
        # Prepare key for the next step.
        key = normalize_text(name)
        # Handle the missing or empty key or key in noise or key in seen case.
        if not key or key in noise or key in seen:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Update result with the current value.
        result.append(str(name).strip().title())
        # Update seen with the current value.
        seen.add(key)
    # Return result to the caller.
    return result


# Define detect social spending ambiguity for callers in this flow.
def detect_social_spending_ambiguity(raw: str) -> dict | None:
    """Detect inputs like `Makan bareng Budi 80k` that need a guard."""
    # Prepare clean for the next step.
    clean = normalize_text(raw)
    # Handle the missing or empty clean or not extract_amount_from_text(clean) case.
    if not clean or not extract_amount_from_text(clean):
        # Return None to the caller.
        return None

    # Explicit intent should stay in the debt/split flow and not be caught here.
    if re.search(r"\b(?:hutang|utang|piutang|minjem|pinjem|pinjam|talangin|ditalangin|nitip|dibayarin|duluin|bayar\s+(?:hutang|utang)|split\s*bill|split|ptpt|patungan|dibagi|bagi|berdua|bertiga|berempat)\b", clean, flags=re.IGNORECASE):
        # Return None to the caller.
        return None

    has_social_phrase = bool(re.search(rf"\b{SOCIAL_MEAL_KEYWORDS}\b.*\b{SOCIAL_FRIEND_MARKER}\b|\b{SOCIAL_FRIEND_MARKER}\s+[a-zA-ZÀ-ÿ]+", clean, flags=re.IGNORECASE))
    # Handle the missing or empty has_social_phrase case.
    if not has_social_phrase:
        # Return None to the caller.
        return None

    # Prepare people for the next step.
    people = extract_people_from_social_input(raw)
    # Handle the missing or empty people case.
    if not people:
        # Return None to the caller.
        return None

    # Prepare parsed for the next step.
    parsed = parse_with_regex(raw) or {}
    if parsed.get("type") != "expense":
        # Return None to the caller.
        return None

    amount = float(parsed.get("amount") or parse_human_amount(raw) or 0)
    # Handle the case where amount <= 0.
    if amount <= 0:
        # Return None to the caller.
        return None

    # Return { to the caller.
    return {
        "raw": raw,
        "people": people,
        "amount": amount,
        "parsed": parsed,
    # Close the structure that was opened above.
    }


# Define social spending guard keyboard for callers in this flow.
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
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤝 Split bill", callback_data="meal_guard:split")],
        [InlineKeyboardButton("🧾 Pengeluaran biasa", callback_data="meal_guard:expense")],
        [InlineKeyboardButton("✍️ Tulis ulang", callback_data="meal_guard:rewrite")],
        [InlineKeyboardButton("🚫 Batal", callback_data="cancel:meal_guard")],
    # Close the structure that was opened above.
    ])


# Define build social spending guard prompt for callers in this flow.
def build_social_spending_guard_prompt(raw: str, guard: dict) -> str:
    """Build a concise guard prompt for ambiguous social spending."""
    people_text = ", ".join(guard.get("people") or []) or "teman"
    amount = float(guard.get("amount") or 0)
    # Return ( to the caller.
    return (
        "🤔 *Input ini terlihat seperti makan/bareng orang lain.*\n\n"
        f"Input: `{md_safe(raw)}`\n"
        f"Total: *{format_rupiah(amount)}*\n"
        f"Orang terdeteksi: *kamu dan {md_safe(people_text)}*\n\n"
        "Mau dicatat sebagai split bill atau pengeluaran biasa?\n\n"
        "Kalau pengeluaran biasa, transaksi akan dicatat sebagai pengeluaran pribadi "
        f"dengan catatan makan bareng/traktir {md_safe(people_text)}."
    # Close the structure that was opened above.
    )


# Define build social spending expense for callers in this flow.
def build_social_spending_expense(raw: str, guard: dict) -> dict:
    """Convert ambiguous social spending into a normal personal expense."""
    parsed = dict((guard or {}).get("parsed") or parse_with_regex(raw) or {})
    amount = float(parsed.get("amount") or (guard or {}).get("amount") or parse_human_amount(raw) or 0)
    people = (guard or {}).get("people") or extract_people_from_social_input(raw)
    people_text = ", ".join(people) if people else "teman"
    subject = f"Makan bareng {people_text}" if people else (parsed.get("subject") or "Makan bareng")

    # Open a multi-line structure for the values below.
    parsed.update({
        "type": "expense",
        "amount": amount,
        "category": parsed.get("category") or detect_category(raw, "expense"),
        "subject": subject,
        "description": subject,
        "catatan": f"Dicatat sebagai pengeluaran biasa / traktir {people_text}",
        "date": parsed.get("date") or detect_date(raw),
        "parsed_by": parsed.get("parsed_by") or "social_guard",
    # Close the structure that was opened above.
    })
    parsed.pop("split_bill", None)
    # Return parsed to the caller.
    return parsed


# Define meal split payer keyboard for callers in this flow.
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
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🙋 Saya yang bayar", callback_data="meal_split:payer:self")],
        [InlineKeyboardButton("👤 Bukan saya yang bayar", callback_data="meal_split:payer:other")],
        [InlineKeyboardButton("✍️ Tulis ulang", callback_data="meal_guard:rewrite")],
        [InlineKeyboardButton("🚫 Batal", callback_data="cancel:meal_split")],
    # Close the structure that was opened above.
    ])


# Define build meal split payer prompt for callers in this flow.
def build_meal_split_payer_prompt(guard: dict) -> str:
    """Prompt for payer step in social split bill."""
    people = guard.get("people") or []
    people_text = ", ".join(people) or "teman"
    # Return ( to the caller.
    return (
        "Siapa yang membayar transaksi ini di awal?\n\n"
        f"Total transaksi: *{format_rupiah(guard.get('amount') or 0)}*\n"
        f"Orang yang terdeteksi: *kamu dan {md_safe(people_text)}*"
    # Close the structure that was opened above.
    )


# Define meal split allocation keyboard for callers in this flow.
def meal_split_allocation_keyboard() -> InlineKeyboardMarkup:
    """Ask whether split bill is equal or custom."""
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚖️ Bagi rata", callback_data="meal_split:allocation:equal")],
        [InlineKeyboardButton("📊 Atur pembagian", callback_data="meal_split:allocation:custom")],
        [InlineKeyboardButton("✍️ Tulis ulang", callback_data="meal_guard:rewrite")],
        [InlineKeyboardButton("🚫 Batal", callback_data="cancel:meal_split")],
    # Close the structure that was opened above.
    ])


# Define build meal split allocation prompt for callers in this flow.
def build_meal_split_allocation_prompt(state: dict) -> str:
    """Prompt for allocation step in social split bill."""
    people = state.get("people") or []
    people_text = ", ".join(people) or "teman"
    # Return ( to the caller.
    return (
        "Pembagiannya gimana?\n\n"
        f"Total transaksi: *{format_rupiah(state.get('amount') or 0)}*\n"
        f"Orang yang terdeteksi: *kamu dan {md_safe(people_text)}*"
    # Close the structure that was opened above.
    )


# Define build meal split custom allocation prompt for callers in this flow.
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
    # Return ( to the caller.
    return (
        "Tulis pembagiannya dalam satu pesan.\n\n"
        "Bisa pakai bobot persen atau nominal langsung.\n\n"
        f"Contoh bobot:\n`saya 100%, {people_text} 100%`\n\n"
        f"Contoh nominal:\n`saya 30k, {people_text} 50k`\n\n"
        "Catatan:\n"
        "Angka persen di sini adalah bobot pembagian, bukan total yang harus berjumlah 100%.\n"
        "Contohnya kalau saya 100% dan Budi 100%, berarti dibagi rata. "
        "Kalau saya 100% dan Budi 80%, berarti bagian Budi lebih kecil dari bagian saya."
    # Close the structure that was opened above.
    )


# Define compute equal meal split shares for callers in this flow.
def compute_equal_meal_split_shares(amount: float, people: list[str]) -> dict:
    """Compute equal split shares for user and friends."""
    # Prepare participant count for the next step.
    participant_count = max(len(people or []) + 1, 1)
    # Prepare share for the next step.
    share = float(amount or 0) / participant_count
    shares = {"Kamu": share}
    # Process each person in the current collection.
    for person in people or []:
        # Run this statement as part of the current workflow.
        shares[str(person).strip().title()] = share
    # Return shares to the caller.
    return shares


# Define parse meal split allocation for callers in this flow.
def parse_meal_split_allocation(text: str, amount: float, people: list[str]) -> dict | None:
    """Parse custom social split allocation using weighted percent or nominal values."""
    raw = str(text or "").strip()
    # Handle the missing or empty raw case.
    if not raw:
        # Return None to the caller.
        return None

    aliases = {"saya": "Kamu", "aku": "Kamu", "gw": "Kamu", "gue": "Kamu", "gua": "Kamu", "kamu": "Kamu"}
    # Process each person in the current collection.
    for person in people or []:
        # Run this statement as part of the current workflow.
        aliases[normalize_text(person)] = str(person).strip().title()

    pattern = r"(?P<name>saya|aku|gw|gue|gua|kamu|[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{0,40}?)\s*:?\s*(?P<value>\d+(?:[.,]\d+)?\s*(?:%|rb|ribu|k|jt|juta|m)?)"
    # Prepare entries for the next step.
    entries = []
    # Process each match in the current collection.
    for match in re.finditer(pattern, raw, flags=re.IGNORECASE):
        name_raw = re.sub(r"\s+", " ", match.group("name") or "").strip()
        value_raw = str(match.group("value") or "").strip()
        # Prepare key for the next step.
        key = normalize_text(name_raw)
        # Prepare name for the next step.
        name = aliases.get(key) or name_raw.title()
        if name not in {"Kamu", *[str(p).strip().title() for p in people or []]}:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Update entries with the current value.
        entries.append((name, value_raw))

    # Handle the missing or empty entries case.
    if not entries:
        # Return None to the caller.
        return None

    has_percent = any(value.strip().endswith("%") for _, value in entries)
    has_nominal = any(not value.strip().endswith("%") for _, value in entries)
    # Handle the case where has_percent and has_nominal.
    if has_percent and has_nominal:
        # Return None to the caller.
        return None

    # Prepare seen for the next step.
    seen = {}
    # Process each name, value in the current collection.
    for name, value in entries:
        # Run this statement as part of the current workflow.
        seen[name] = value

    expected_names = ["Kamu"] + [str(p).strip().title() for p in people or [] if str(p).strip()]
    # Handle the case where has_percent.
    if has_percent:
        # Prepare weights for the next step.
        weights = {}
        # Process each name in the current collection.
        for name in expected_names:
            raw_value = str(seen.get(name) or "").strip()
            if raw_value.endswith("%"):
                # Run this operation in a guarded block so failures can be handled.
                try:
                    weights[name] = max(float(raw_value[:-1].replace(",", ".").strip()), 0.0)
                # Handle an expected failure from the guarded operation above.
                except Exception:
                    # Run this statement as part of the current workflow.
                    weights[name] = 0.0
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Run this statement as part of the current workflow.
                weights[name] = 0.0
        # Prepare total weight for the next step.
        total_weight = sum(weights.values())
        # Handle the case where total_weight <= 0.
        if total_weight <= 0:
            # Return None to the caller.
            return None
        # Return {name: float(amount or 0) * weight / total_weight for name, w... to the caller.
        return {name: float(amount or 0) * weight / total_weight for name, weight in weights.items()}

    # Prepare shares for the next step.
    shares = {}
    # Process each name in the current collection.
    for name in expected_names:
        raw_value = str(seen.get(name) or "").strip()
        # Run this statement as part of the current workflow.
        shares[name] = parse_human_amount(raw_value) if raw_value else 0.0
    # Prepare total shares for the next step.
    total_shares = sum(shares.values())
    # Handle the case where total_shares <= 0.
    if total_shares <= 0:
        # Return None to the caller.
        return None
    # Return shares to the caller.
    return shares


# Define meal split status keyboard for callers in this flow.
def meal_split_status_keyboard(payer: str) -> InlineKeyboardMarkup:
    """Ask whether the relevant share has already been paid."""
    if payer == "self":
        paid_label = "✅ Sudah bayar"
        unpaid_label = "⏳ Belum bayar"
    # Handle the fallback path after earlier conditions are skipped.
    else:
        paid_label = "✅ Sudah bayar"
        unpaid_label = "⏳ Belum bayar"
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(paid_label, callback_data="meal_split:status:paid")],
        [InlineKeyboardButton(unpaid_label, callback_data="meal_split:status:unpaid")],
        [InlineKeyboardButton("🚫 Batal", callback_data="cancel:meal_split")],
    # Close the structure that was opened above.
    ])


# Define build meal split status prompt for callers in this flow.
def build_meal_split_status_prompt(state: dict) -> str:
    """Prompt for payment status in social split bill."""
    people = state.get("people") or []
    people_text = ", ".join(people) or "teman"
    if state.get("payer") == "self":
        return f"Apakah {md_safe(people_text)} sudah bayar bagian dia ke kamu?"
    return "Apakah kamu sudah bayar bagian kamu?"


# Define build meal split final payload for callers in this flow.
def build_meal_split_final_payload(state: dict) -> dict:
    """Build pending parsed/debt payload from the social split bill wizard."""
    amount = float(state.get("amount") or 0)
    people = [str(p).strip().title() for p in (state.get("people") or []) if str(p).strip()]
    shares = state.get("shares") or compute_equal_meal_split_shares(amount, people)
    user_share = float(shares.get("Kamu", 0) or 0)
    # Prepare person shares for the next step.
    person_shares = {person: float(shares.get(person, 0) or 0) for person in people}
    # Prepare total receivable for the next step.
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
        # Open a multi-line structure for the values below.
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
            # Close the structure that was opened above.
            },
        # Close the structure that was opened above.
        })
        return {"mode": "transaction", "parsed": parsed, "cashflow_amount": cashflow_amount}

    payer_name = people[0] if people else "Teman"
    if status == "unpaid":
        # Return { to the caller.
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
            # Close the structure that was opened above.
            },
            "cashflow_amount": 0,
        # Close the structure that was opened above.
        }

    # Open a multi-line structure for the values below.
    parsed.update({
        "type": "expense",
        "amount": user_share,
        "category": category,
        "subject": description,
        "description": description,
        "catatan": f"Split bill: {payer_name} yang bayar; saya sudah bayar bagian saya",
        "date": date,
        "parsed_by": parsed.get("parsed_by") or "meal_split",
    # Close the structure that was opened above.
    })
    parsed.pop("split_bill", None)
    return {"mode": "transaction", "parsed": parsed, "cashflow_amount": user_share}


# Define build meal split detail preview for callers in this flow.
def build_meal_split_detail_preview(state: dict, payload: dict | None = None) -> str:
    """Build preview detail before account selection in social split bill."""
    amount = float(state.get("amount") or 0)
    people = state.get("people") or []
    shares = state.get("shares") or compute_equal_meal_split_shares(amount, people)
    payer = state.get("payer") or "self"
    status = state.get("status") or "unpaid"
    allocation_label = "Bagi rata" if state.get("allocation_mode") != "custom" else "Atur pembagian"

    # Open a multi-line structure for the values below.
    lines = [
        "🤝 *Preview split bill*\n",
        f"Total transaksi: *{format_rupiah(amount)}*",
        f"Pembagian: *{md_safe(allocation_label)}*",
        f"Orang terlibat: *kamu dan {md_safe(', '.join(people) or 'teman')}*",
        "",
        "📋 *Rincian bagian:*",
    # Close the structure that was opened above.
    ]
    # Process each name, share in the current collection.
    for name, share in shares.items():
        label = "Kamu" if name == "Kamu" else name
        lines.append(f"• {md_safe(label)}: *{format_rupiah(share)}*")

    lines.extend(["", "💸 *Status:*"])
    if payer == "self":
        lines.append("• Pembayar awal: Saya")
        # Process each person in the current collection.
        for person in people:
            lines.append(f"• {md_safe(person)} {'belum bayar' if status == 'unpaid' else 'sudah bayar'}")
        if status == "unpaid":
            lines.append(f"• Piutang teman: *{format_rupiah(sum(float(shares.get(p, 0) or 0) for p in people))}*")
            lines.append(f"• Saldo keluar dari rekening saya: *{format_rupiah(amount)}*")
        # Handle the fallback path after earlier conditions are skipped.
        else:
            lines.append(f"• Expense pribadi: *{format_rupiah(float(shares.get('Kamu', 0) or 0))}*")
            lines.append(f"• Saldo keluar dari rekening saya: *{format_rupiah(float(shares.get('Kamu', 0) or 0))}*")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        payer_name = people[0] if people else "Teman"
        lines.append(f"• Pembayar awal: {md_safe(payer_name)}")
        if status == "unpaid":
            lines.append(f"• Kamu belum bayar ke {md_safe(payer_name)}")
            lines.append(f"• Utang kamu: *{format_rupiah(float(shares.get('Kamu', 0) or 0))}*")
            lines.append("• Tidak ada saldo rekening yang berubah sekarang")
        # Handle the fallback path after earlier conditions are skipped.
        else:
            lines.append(f"• Kamu sudah bayar ke {md_safe(payer_name)}")
            lines.append(f"• Expense pribadi: *{format_rupiah(float(shares.get('Kamu', 0) or 0))}*")
            lines.append(f"• Saldo keluar dari rekening saya: *{format_rupiah(float(shares.get('Kamu', 0) or 0))}*")

    lines.append("\nMau lanjut, edit dulu, atau batal?")
    return "\n".join(lines)


# Define meal split continue keyboard for callers in this flow.
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
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ Lanjut", callback_data="meal_split:continue")],
        [InlineKeyboardButton("✏️ Edit dulu", callback_data="meal_guard:rewrite")],
        [InlineKeyboardButton("🚫 Batal", callback_data="cancel:meal_split")],
    # Close the structure that was opened above.
    ])


# Define build meal split final summary for callers in this flow.
def build_meal_split_final_summary(parsed_or_debt: dict, mode: str) -> str:
    """Build final ringkas summary for social split bill after rekening/debt decision."""
    if mode == "debt":
        # Return build_debt_only_confirm_preview(parsed_or_debt) to the caller.
        return build_debt_only_confirm_preview(parsed_or_debt)

    # Prepare parsed for the next step.
    parsed = parsed_or_debt
    split_bill = parsed.get("split_bill") or {}
    total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    user_share = float(split_bill.get("user_share_amount", parsed.get("amount", 0)) or 0)
    total_receivable = float(split_bill.get("total_receivable", 0) or 0)
    # Open a multi-line structure for the values below.
    lines = [
        "🧾 *Ringkasan split bill:*",
        f"• Total transaksi: *{format_rupiah(total)}*",
        f"• Expense pribadi: *{format_rupiah(user_share)}*",
    # Close the structure that was opened above.
    ]
    # Handle the case where total_receivable > 0.
    if total_receivable > 0:
        names = ", ".join(split_bill.get("person_names") or []) or "teman"
        lines.append(f"• Piutang {md_safe(names)}: *{format_rupiah(total_receivable)}*")
    lines.append(f"• Rekening: *{md_safe(parsed.get('account') or '-')}*")
    account_summary = build_account_delta_summary_from_transaction_items([{"parsed": parsed}])
    # Handle the case where account_summary.
    if account_summary:
        lines.extend(["", account_summary])
    return "\n".join(lines)

# Define parse participant count for callers in this flow.
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
    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    }
    # Handle the case where clean in mapping.
    if clean in mapping:
        # Return mapping[clean] to the caller.
        return mapping[clean]
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare value int for the next step.
        value_int = int(clean)
        # Return value_int if value_int > 0 else None to the caller.
        return value_int if value_int > 0 else None
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return None to the caller.
        return None


# Define build account delta summary from transaction items for callers in this flow.
def build_account_delta_summary_from_transaction_items(items: list[dict]) -> str:
    """Build the data structure or message text for account delta summary from transaction items."""
    # Prepare transaction items for the next step.
    transaction_items = []
    # Process each item in the current collection.
    for item in items or []:
        parsed = item.get("parsed", item) if isinstance(item, dict) else {}
        if isinstance(parsed, dict) and parsed.get("type") in ["expense", "income", "transfer"]:
            transaction_items.append({"parsed": parsed})

    # Prepare deltas for the next step.
    deltas = calculate_account_deltas(transaction_items)
    # Handle the missing or empty deltas case.
    if not deltas:
        return ""

    lines = ["\n💳 *Ringkasan per rekening:*"]
    # Process each account_name, delta in the current collection.
    for account_name, delta in deltas.items():
        sign = "+" if float(delta or 0) >= 0 else "-"
        lines.append(f"• {md_safe(account_name)}: {sign}{format_rupiah(abs(float(delta or 0)))}")
    return "\n".join(lines)


# Define build mixed short summary for callers in this flow.
def build_mixed_short_summary(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed short summary."""
    # Prepare total expense for the next step.
    total_expense = 0.0
    # Prepare total income for the next step.
    total_income = 0.0
    # Prepare total transfer for the next step.
    total_transfer = 0.0
    # Prepare total debt for the next step.
    total_debt = 0.0
    # Prepare transaction count for the next step.
    transaction_count = 0
    # Prepare debt count for the next step.
    debt_count = 0

    # Process each item in the current collection.
    for item in mixed_items or []:
        kind = item.get("kind")
        parsed = item.get("parsed", {}) or {}
        amount = _receipt_amount(parsed.get("amount"), 0)
        if kind == "transaction":
            # Run this statement as part of the current workflow.
            transaction_count += 1
            txn_type = parsed.get("type")
            if txn_type == "expense":
                # Run this statement as part of the current workflow.
                total_expense += amount
            elif txn_type == "income":
                # Run this statement as part of the current workflow.
                total_income += amount
            elif txn_type == "transfer":
                # Run this statement as part of the current workflow.
                total_transfer += amount
        elif kind == "debt":
            # Run this statement as part of the current workflow.
            debt_count += 1
            # Run this statement as part of the current workflow.
            total_debt += amount

    lines = ["🧾 *Ringkasan batch:*"]
    lines.append(f"• Total item: *{len(mixed_items or [])}*")
    # Handle the case where transaction_count.
    if transaction_count:
        lines.append(f"• Transaksi: *{transaction_count} item*")
    # Handle the case where total_expense.
    if total_expense:
        lines.append(f"• Expense: *{format_rupiah(total_expense)}*")
    # Handle the case where total_income.
    if total_income:
        lines.append(f"• Income: *{format_rupiah(total_income)}*")
    # Handle the case where total_transfer.
    if total_transfer:
        lines.append(f"• Transfer: *{format_rupiah(total_transfer)}*")
    # Handle the case where debt_count.
    if debt_count:
        lines.append(f"• Debt: *{debt_count} item* / {format_rupiah(total_debt)}")

    # Prepare account summary for the next step.
    account_summary = build_account_delta_summary_from_transaction_items(mixed_items)
    # Handle the case where account_summary.
    if account_summary:
        # Update lines with the current value.
        lines.append(account_summary)

    return "\n".join(lines)


# Define build single short summary for callers in this flow.
def build_single_short_summary(parsed: dict) -> str:
    """Build the data structure or message text for single short summary."""
    # Handle the missing or empty isinstance(parsed, dict) case.
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
    # Handle the case where account_summary.
    if account_summary:
        # Update lines with the current value.
        lines.append(account_summary)

    return "\n".join(lines)


# Define build single account prompt for callers in this flow.
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
    # Prepare summary for the next step.
    summary = preview_text or build_single_short_summary(parsed)
    # Return ( to the caller.
    return (
        f"{summary}\n\n"
        "💳 Dari rekening mana?\n"
        "Atau pilih *Sudah berlalu* jika transaksi hanya catatan historis dan tidak mau mengubah saldo."
    # Close the structure that was opened above.
    )


# Define build mixed account prompt for callers in this flow.
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
    # Return ( to the caller.
    return (
        f"{build_mixed_short_summary(mixed_items)}\n\n"
        "💳 Pilih rekening untuk item yang belum punya rekening, atau pilih "
        "*Sudah berlalu* jika tidak mau mengubah saldo:"
    # Close the structure that was opened above.
    )


# Define build updated item summary for callers in this flow.
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
        # Return ( to the caller.
        return (
            f"✅ *{prefix} sudah diupdate.*\n"
            f"• {label}\n"
            f"• {format_rupiah(amount)} | {category}\n"
            f"• Rekening: {account}"
        # Close the structure that was opened above.
        )

    if kind == "debt":
        person = md_safe(parsed.get("person_name") or "-")
        amount = _receipt_amount(parsed.get("amount"), 0)
        account = md_safe(parsed.get("account") or "-")
        # Return ( to the caller.
        return (
            f"✅ *{prefix} debt sudah diupdate.*\n"
            f"• {person}\n"
            f"• {format_rupiah(amount)}\n"
            f"• Rekening: {account}"
        # Close the structure that was opened above.
        )

    return f"✅ *{prefix} sudah diupdate.*"


# Define preview edit fields for scope for callers in this flow.
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
        # Return [ to the caller.
        return [
            ("💰 Nominal", "amount"),
            ("📁 Kategori", "category"),
            ("👤 Subjek", "subject"),
            ("📝 Deskripsi", "description"),
            ("🏦 Rekening", "account"),
            ("📅 Tanggal", "due_date"),
            ("🗓️ Bulan", "month"),
        # Close the structure that was opened above.
        ]

    if scope == "asset":
        # Return [ to the caller.
        return [
            ("🏷️ Nama", "name"),
            ("💰 Nominal", "amount"),
            ("📁 Kategori", "category"),
            ("📝 Deskripsi", "description"),
            ("🔢 Jumlah", "quantity"),
            ("📏 Unit", "unit"),
            ("🏷️ Harga/unit", "price_per_unit"),
            ("📅 Tanggal beli", "purchase_date"),
        # Close the structure that was opened above.
        ]

    if scope == "debt":
        # Return [ to the caller.
        return [
            ("💰 Nominal", "amount"),
            ("👤 Orang", "person_name"),
            ("📝 Deskripsi", "description"),
            ("🏦 Rekening", "account"),
            ("📅 Tanggal", "date"),
        # Close the structure that was opened above.
        ]

    # Return [ to the caller.
    return [
        ("💰 Nominal", "amount"),
        ("📁 Kategori", "category"),
        ("👤 Subjek", "subject"),
        ("📝 Deskripsi", "description"),
        ("🏦 Rekening", "account"),
        ("🔁 Tipe", "type"),
        ("📅 Tanggal", "date"),
        ("🗒️ Catatan", "catatan"),
    # Close the structure that was opened above.
    ]


def build_preview_edit_keyboard(scope: str = "single") -> InlineKeyboardMarkup:
    """Build the data structure or message text for preview edit keyboard."""
    # Prepare fields for the next step.
    fields = _preview_edit_fields_for_scope(scope)
    # Prepare rows for the next step.
    rows = []
    # Process each i in the current collection.
    for i in range(0, len(fields), 2):
        # Prepare row for the next step.
        row = []
        # Process each label, field in the current collection.
        for label, field in fields[i:i + 2]:
            row.append(InlineKeyboardButton(label, callback_data=f"editflow:field:{scope}:{field}"))
        # Update rows with the current value.
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")])
    # Return InlineKeyboardMarkup(rows) to the caller.
    return InlineKeyboardMarkup(rows)


# Define build preview field help for callers in this flow.
def build_preview_field_help(scope: str, field: str) -> str:
    """Build the data structure or message text for preview field help."""
    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    }
    title, example = examples.get(field, (field.replace("_", " ").title(), f"`{field}: nilai baru`"))
    # Return ( to the caller.
    return (
        f"✏️ *Edit {md_safe(title)}*\n\n"
        f"Ketik nilai barunya dengan format:\n{example}\n\n"
        "Kamu juga bisa edit banyak field sekaligus, contoh:\n"
        "`nominal: 20k, kategori: Other Expense, rekening: DANA`"
    # Close the structure that was opened above.
    )




# Define build preview field value prompt for callers in this flow.
def build_preview_field_value_prompt(scope: str, field: str) -> str:
    """Build the direct-value prompt after the user taps one edit field."""
    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    }
    # Open a multi-line structure for the values below.
    title, instruction, example = examples.get(
        # Include this value in the surrounding collection or call.
        field,
        (field.replace("_", " ").title(), "Tulis nilai baru yang kamu mau.", "nilai baru"),
    # Close the structure that was opened above.
    )
    # Return ( to the caller.
    return (
        f"✏️ *Edit {md_safe(title)}*\n\n"
        f"{instruction}\n\n"
        f"Contoh: `{md_code_text(example)}`"
    # Close the structure that was opened above.
    )


# Define parse preview direct field update for callers in this flow.
def parse_preview_direct_field_update(field: str, value: str) -> dict:
    """Parse a raw value for one field selected from the edit keyboard."""
    canonical = PREVIEW_EDIT_KEY_ALIASES.get(str(field or "").strip().lower(), str(field or "").strip())
    # Handle the missing or empty canonical case.
    if not canonical:
        # Return {} to the caller.
        return {}
    return _parse_preview_edit_pair(f"{canonical}: {value}")

def build_preview_edit_help(scope: str = "single") -> str:
    """Build the data structure or message text for preview edit help."""
    if scope == "pending_expense":
        fields = "nominal, kategori, subjek, deskripsi, rekening, tanggal, bulan"
        # Open a multi-line structure for the values below.
        examples = (
            "`nominal: 285k, kategori: Bills & Utilities, rekening: BRI`\n"
            "`deskripsi: Wifi rumah, tanggal: 2026-07-30`"
        # Close the structure that was opened above.
        )
    elif scope == "asset":
        fields = "nama, nominal, kategori, deskripsi, jumlah, unit, harga_satuan, harga_beli, tanggal_beli"
        # Open a multi-line structure for the values below.
        examples = (
            "`nama: Laptop kerja, nominal: 8jt, kategori: Electronics`\n"
            "`jumlah: 41, unit: gram, harga_satuan: 2594000`"
        # Close the structure that was opened above.
        )
    elif scope == "debt":
        fields = "nominal, orang, deskripsi, rekening, tanggal"
        # Open a multi-line structure for the values below.
        examples = (
            "`nominal: 50k, orang: Budi, rekening: DANA`\n"
            "`deskripsi: Talang makan, tanggal: 2026-07-02`"
        # Close the structure that was opened above.
        )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        fields = "nominal, kategori, deskripsi, subjek, tipe, tanggal, rekening, catatan"
        # Open a multi-line structure for the values below.
        examples = (
            "`nominal: 20k, kategori: Other Expense, rekening: DANA`\n"
            "`deskripsi: Mie Goreng, tanggal: 2026-07-02`"
        # Close the structure that was opened above.
        )

    item_hint = "" if scope == "single" else "\nKamu sedang mengedit item yang dipilih."
    # Return ( to the caller.
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
    # Close the structure that was opened above.
    )


# Define build mixed edit choose prompt for callers in this flow.
def build_mixed_edit_choose_prompt(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed edit choose prompt."""
    lines = ["✏️ *Mau edit item nomor berapa?*\n"]
    # Process each i, item in the current collection.
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
        # Handle the fallback path after earlier conditions are skipped.
        else:
            lines.append(f"{i}. {md_safe(item.get('raw', '-'))}")
    lines.append("\nBalas dengan angka, contoh: `2`.")
    return "\n".join(lines)


# Open a multi-line structure for the values below.
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
# Close the structure that was opened above.
}


# Define split preview edit segments for callers in this flow.
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
    # Run this statement as part of the current workflow.
    segments: list[str] = []
    # Run this statement as part of the current workflow.
    buffer: list[str] = []
    quote_char = ""

    for char in str(raw or ""):
        if char in {"'", '"'}:
            # Handle the case where quote_char == char.
            if quote_char == char:
                quote_char = ""
            # Handle the alternate case where not quote_char.
            elif not quote_char:
                # Prepare quote char for the next step.
                quote_char = char
            # Update buffer with the current value.
            buffer.append(char)
            # Skip the rest of this loop iteration after handling this case.
            continue

        if char in {",", ";", "\n", "\r"} and not quote_char:
            part = "".join(buffer).strip()
            # Handle the case where part.
            if part:
                # Update segments with the current value.
                segments.append(part)
            # Prepare buffer for the next step.
            buffer = []
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Update buffer with the current value.
        buffer.append(char)

    last = "".join(buffer).strip()
    # Handle the case where last.
    if last:
        # Update segments with the current value.
        segments.append(last)
    # Return segments to the caller.
    return segments


# Define strip preview edit value for callers in this flow.
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
        # Return clean[1:-1].strip() to the caller.
        return clean[1:-1].strip()
    # Return clean to the caller.
    return clean


# Define parse preview edit pair for callers in this flow.
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
    # Handle the missing or empty raw case.
    if not raw:
        # Return {} to the caller.
        return {}

    key_pattern = "|".join(re.escape(k) for k in sorted(PREVIEW_EDIT_KEY_ALIASES, key=len, reverse=True))
    # Open a multi-line structure for the values below.
    match = re.match(
        rf"^({key_pattern})\s*(?:=|:)\s*(.+)$",
        # Include this value in the surrounding collection or call.
        raw,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the missing or empty match case.
    if not match:
        # Open a multi-line structure for the values below.
        match = re.match(
            rf"^({key_pattern})\s+(.+)$",
            # Include this value in the surrounding collection or call.
            raw,
            # Prepare flags for the next step.
            flags=re.IGNORECASE,
        # Close the structure that was opened above.
        )
    # Handle the missing or empty match case.
    if not match:
        # Return {} to the caller.
        return {}

    # Prepare key for the next step.
    key = PREVIEW_EDIT_KEY_ALIASES.get(match.group(1).lower())
    # Prepare value for the next step.
    value = _strip_preview_edit_value(match.group(2))
    if not key or value == "":
        # Return {} to the caller.
        return {}

    # Run this statement as part of the current workflow.
    updates: dict = {}
    if key in {"amount", "quantity", "price_per_unit", "purchase_price_per_unit"}:
        # Prepare amount for the next step.
        amount = parse_human_amount(value)
        # Handle the case where amount <= 0.
        if amount <= 0:
            # Return {} to the caller.
            return {}
        # Run this statement as part of the current workflow.
        updates[key] = amount
    elif key == "type":
        # Prepare normalized for the next step.
        normalized = value.lower().strip()
        # Open a multi-line structure for the values below.
        type_aliases = {
            "income": "income", "pemasukan": "income", "masuk": "income",
            "expense": "expense", "pengeluaran": "expense", "keluar": "expense",
            "transfer": "transfer",
        # Close the structure that was opened above.
        }
        # Handle the case where normalized not in type_aliases.
        if normalized not in type_aliases:
            # Return {} to the caller.
            return {}
        # Run this statement as part of the current workflow.
        updates[key] = type_aliases[normalized]
    elif key in {"date", "due_date", "purchase_date"}:
        # Import app.nlp.regex_parser so this module can use its helpers.
        from app.nlp.regex_parser import parse_explicit_date
        # Prepare parsed date for the next step.
        parsed_date = parse_explicit_date(value) or value
        # Run this statement as part of the current workflow.
        updates[key] = parsed_date
    elif key == "month":
        # Run this statement as part of the current workflow.
        updates[key] = value.strip()
    elif key in ["account", "to_account"]:
        # Prepare value clean for the next step.
        value_clean = value.strip()
        updates[key] = value_clean.upper() if value_clean.lower() in ["bca", "bri", "bsi", "dana"] else value_clean.title()
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Run this statement as part of the current workflow.
        updates[key] = value.strip()

    # Return updates to the caller.
    return updates


# Define parse preview edit updates for callers in this flow.
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
    # Handle the missing or empty raw case.
    if not raw:
        # Return {} to the caller.
        return {}

    # Prepare segments for the next step.
    segments = _split_preview_edit_segments(raw)
    # Handle the missing or empty segments case.
    if not segments:
        # Return {} to the caller.
        return {}

    # Run this statement as part of the current workflow.
    updates: dict = {}
    # Process each segment in the current collection.
    for segment in segments:
        # Prepare parsed segment for the next step.
        parsed_segment = _parse_preview_edit_pair(segment)
        # Handle the missing or empty parsed_segment case.
        if not parsed_segment:
            # Handle the case where len(segments) == 1.
            if len(segments) == 1:
                # Return {} to the caller.
                return {}
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Update updates with the current value.
        updates.update(parsed_segment)

    # Return updates to the caller.
    return updates


# Define apply preview edit updates to parsed for callers in this flow.
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
    # Handle the missing or empty isinstance(parsed, dict) case.
    if not isinstance(parsed, dict):
        # Return parsed to the caller.
        return parsed

    # Update parsed with the current value.
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

    # Return parsed to the caller.
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
        # Handle the missing or empty mixed_items case.
        if not mixed_items:
            await safe_edit_message(query, "❌ Sesi mixed input expired. Coba input ulang.")
            # Return control to the caller.
            return

        # Handle the case where mixed_split_bill_needs_decision(mixed_items).
        if mixed_split_bill_needs_decision(mixed_items):
            # Wait for safe_edit_message before continuing this flow.
            await safe_edit_message(query,
                # Include this value in the surrounding collection or call.
                build_mixed_split_bill_queue_prompt(mixed_items),
                parse_mode="Markdown",
                # Prepare reply markup for the next step.
                reply_markup=mixed_split_bill_keyboard(mixed_items),
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        # Handle the case where mixed_needs_account(mixed_items).
        if mixed_needs_account(mixed_items):
            # Wait for safe_edit_message before continuing this flow.
            await safe_edit_message(
                # Include this value in the surrounding collection or call.
                query,
                # Include this value in the surrounding collection or call.
                build_mixed_account_prompt(mixed_items),
                parse_mode="Markdown",
                reply_markup=account_keyboard("mixed_acc"),
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        receipt_context = context.user_data.get("pending_receipt_context")
        # Prepare final summary for the next step.
        final_summary = build_mixed_final_summary(mixed_items, receipt_context)
        # Wait for safe_edit_message before continuing this flow.
        await safe_edit_message(query,
            f"{final_summary}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", True),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    if scope == "debt":
        debt_parsed = context.user_data.get("pending_debt")
        # Handle the missing or empty debt_parsed case.
        if not debt_parsed:
            await safe_edit_message(query, "❌ Sesi debt expired. Coba input ulang.")
            # Return control to the caller.
            return

        intent = debt_parsed.get("intent")
        if debt_uses_cashflow(debt_parsed) and intent != "offset_debt" and not debt_parsed.get("account"):
            # Wait for safe_edit_message before continuing this flow.
            await safe_edit_message(
                # Include this value in the surrounding collection or call.
                query,
                # Include this value in the surrounding collection or call.
                build_debt_account_prompt(debt_parsed),
                parse_mode="Markdown",
                reply_markup=account_keyboard("debt_acc"),
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        if debt_uses_cashflow(debt_parsed) and intent != "offset_debt":
            account_label = debt_parsed.get("account") or "-"
            # Prepare preview for the next step.
            preview = build_debt_confirm_preview(debt_parsed, account_label)
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Prepare preview for the next step.
            preview = build_debt_only_confirm_preview(debt_parsed)

        # Wait for safe_edit_message before continuing this flow.
        await safe_edit_message(
            # Include this value in the surrounding collection or call.
            query,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("debt", True),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    if scope == "pending_expense":
        item = context.user_data.get("pending_expense_confirm")
        # Handle the missing or empty item case.
        if not item:
            await safe_edit_message(query, "❌ Sesi pending expense expired. Coba input ulang.")
            # Return control to the caller.
            return

        # Wait for safe_edit_message before continuing this flow.
        await safe_edit_message(
            # Include this value in the surrounding collection or call.
            query,
            # Include this value in the surrounding collection or call.
            build_pending_expense_confirm_preview(item, include_question=True),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("pending_expense"),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    if scope == "asset":
        asset = context.user_data.get("pending_asset_confirm")
        # Handle the missing or empty asset case.
        if not asset:
            await safe_edit_message(query, "❌ Sesi tambah aset expired. Coba input ulang.")
            # Return control to the caller.
            return

        # Wait for safe_edit_message before continuing this flow.
        await safe_edit_message(
            # Include this value in the surrounding collection or call.
            query,
            # Include this value in the surrounding collection or call.
            build_asset_confirm_preview(asset),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("asset"),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    parsed = context.user_data.get("pending_parsed")
    # Handle the missing or empty parsed case.
    if not parsed:
        await safe_edit_message(query, "❌ Sesi transaksi expired. Coba input ulang.")
        # Return control to the caller.
        return

    # Handle the case where split_bill_needs_decision(parsed).
    if split_bill_needs_decision(parsed):
        # Wait for safe_edit_message before continuing this flow.
        await safe_edit_message(query,
            # Include this value in the surrounding collection or call.
            build_split_bill_prompt_from_parsed(parsed),
            parse_mode="Markdown",
            reply_markup=split_bill_keyboard("single"),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Handle the case where needs_account(parsed).
    if needs_account(parsed):
        # Wait for safe_edit_message before continuing this flow.
        await safe_edit_message(
            # Include this value in the surrounding collection or call.
            query,
            # Include this value in the surrounding collection or call.
            build_single_account_prompt(parsed),
            parse_mode="Markdown",
            reply_markup=account_keyboard("acc"),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare short summary for the next step.
    short_summary = build_single_short_summary(parsed)
    # Prepare preview for the next step.
    preview = build_preview(parsed)
    # Wait for safe_edit_message before continuing this flow.
    await safe_edit_message(query,
        f"{preview}\n\n{preview_action_question(True)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("single", True),
    # Close the structure that was opened above.
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
    # Handle the missing or empty state case.
    if not state:
        # Return False to the caller.
        return False

    chat = getattr(update, "effective_chat", None)
    chat_id = getattr(chat, "id", None) or getattr(getattr(update, "message", None), "chat_id", None)
    await clear_tracked_inline_keyboard(context, chat_id, "pending_preview_edit_prompt_message_id")

    scope = state.get("scope")
    step = state.get("step")

    if scope == "mixed" and step == "choose_item":
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare item index for the next step.
            item_index = int(str(user_text).strip()) - 1
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "Balas dengan nomor item, contoh: `2`.",
                parse_mode="Markdown",
                # Prepare reply markup for the next step.
                reply_markup=cancel_keyboard(),
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        mixed_items = context.user_data.get("pending_mixed") or []
        # Handle the case where item_index < 0 or item_index >= len(mixed_items).
        if item_index < 0 or item_index >= len(mixed_items):
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "Nomor item tidak valid. Coba pilih nomor yang ada di preview.",
                # Prepare reply markup for the next step.
                reply_markup=cancel_keyboard(),
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        state["step"] = "edit_item"
        state["index"] = item_index
        context.user_data["pending_preview_edit"] = state
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            build_preview_edit_help("mixed"),
            parse_mode="Markdown",
            reply_markup=build_preview_edit_keyboard("mixed"),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    direct_field = state.get("field") if step == "direct_field" else None
    # Open a multi-line structure for the values below.
    updates = (
        # Run this statement as part of the current workflow.
        parse_preview_direct_field_update(direct_field, user_text)
        # Handle the case where direct_field else parse_preview_edit_updates(user_text).
        if direct_field else parse_preview_edit_updates(user_text)
    # Close the structure that was opened above.
    )
    # Handle the missing or empty updates case.
    if not updates:
        # Open a multi-line structure for the values below.
        help_text = (
            build_preview_field_value_prompt(scope or "single", direct_field)
            if direct_field else build_preview_edit_help(scope or "single")
        # Close the structure that was opened above.
        )
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Format edit belum kebaca.\n\n" + help_text,
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    if scope == "mixed":
        mixed_items = context.user_data.get("pending_mixed") or []
        item_index = int(state.get("index", -1))
        # Handle the case where item_index < 0 or item_index >= len(mixed_items).
        if item_index < 0 or item_index >= len(mixed_items):
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit mixed tidak valid. Coba input ulang.")
            # Return True to the caller.
            return True

        # Prepare item for the next step.
        item = mixed_items[item_index]
        if item.get("kind") == "transaction":
            item["parsed"] = apply_preview_edit_updates_to_parsed(item.get("parsed", {}), updates)
        elif item.get("kind") == "debt":
            # Prepare debt updates for the next step.
            debt_updates = dict(updates)
            if "subject" in debt_updates:
                debt_updates["person_name"] = debt_updates.pop("subject")
            item.setdefault("parsed", {}).update(debt_updates)
        # Run this statement as part of the current workflow.
        mixed_items[item_index] = item
        context.user_data["pending_mixed"] = mixed_items
        context.user_data.pop("pending_preview_edit", None)

        # Prepare item summary for the next step.
        item_summary = build_updated_item_summary(item, item_index + 1)
        receipt_context = context.user_data.get("pending_receipt_context")
        # Handle the case where mixed_needs_account(mixed_items).
        if mixed_needs_account(mixed_items):
            # Prepare detail preview for the next step.
            detail_preview = build_mixed_detail_preview(mixed_items, receipt_context)
            # Wait for reply_update_safely before continuing this flow.
            await reply_update_safely(
                # Include this value in the surrounding collection or call.
                update,
                f"{item_summary}\n\n{detail_preview}\n\n{preview_action_question(False)}",
                parse_mode="Markdown",
                reply_markup=preview_action_keyboard("mixed", False),
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Prepare final summary for the next step.
        final_summary = build_mixed_final_summary(mixed_items, receipt_context)
        # Wait for reply_update_safely before continuing this flow.
        await reply_update_safely(
            # Include this value in the surrounding collection or call.
            update,
            f"{item_summary}\n\n{final_summary}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", True),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    if scope == "debt":
        debt_parsed = context.user_data.get("pending_debt")
        # Handle the missing or empty debt_parsed case.
        if not debt_parsed:
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit debt expired. Coba input ulang.")
            # Return True to the caller.
            return True

        # Prepare debt updates for the next step.
        debt_updates = dict(updates)
        if "subject" in debt_updates:
            debt_updates["person_name"] = debt_updates.pop("subject")
        # `type` belongs to normal transactions, so ignore it for debt preview edits.
        debt_updates.pop("type", None)
        # Update debt parsed with the current value.
        debt_parsed.update(debt_updates)
        context.user_data["pending_debt"] = debt_parsed
        context.user_data.pop("pending_preview_edit", None)

        intent = debt_parsed.get("intent")
        if debt_uses_cashflow(debt_parsed) and intent != "offset_debt" and not debt_parsed.get("account"):
            # Wait for reply_update_safely before continuing this flow.
            await reply_update_safely(
                # Include this value in the surrounding collection or call.
                update,
                f"✅ Preview debt sudah diupdate.\n\n{build_debt_account_prompt(debt_parsed)}",
                parse_mode="Markdown",
                reply_markup=account_keyboard("debt_acc"),
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Prepare short summary for the next step.
        short_summary = build_debt_short_summary(debt_parsed)
        # Wait for reply_update_safely before continuing this flow.
        await reply_update_safely(
            # Include this value in the surrounding collection or call.
            update,
            f"✅ Preview debt sudah diupdate.\n\n{short_summary}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("debt", True),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    if scope == "pending_expense":
        item = context.user_data.get("pending_expense_confirm")
        # Handle the missing or empty item case.
        if not item:
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit pending expense expired. Coba input ulang.")
            # Return True to the caller.
            return True

        # Prepare pending updates for the next step.
        pending_updates = dict(updates)
        if "date" in pending_updates:
            pending_updates["due_date"] = pending_updates.pop("date")
        pending_updates.pop("type", None)
        pending_updates.pop("to_account", None)

        # Update item with the current value.
        item.update(pending_updates)
        if "due_date" in pending_updates and pending_updates.get("due_date"):
            item["due_precision"] = "date"
        if "month" in pending_updates and pending_updates.get("month") and not item.get("due_date"):
            item["due_precision"] = "month"
        if "description" in pending_updates and not pending_updates.get("subject"):
            item["subject"] = pending_updates["description"]

        context.user_data["pending_expense_confirm"] = item
        context.user_data.pop("pending_preview_edit", None)

        # Wait for reply_update_safely before continuing this flow.
        await reply_update_safely(
            # Include this value in the surrounding collection or call.
            update,
            f"✅ Preview pending expense sudah diupdate.\n\n{build_pending_expense_confirm_preview(item, include_question=False)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("pending_expense", True),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    if scope == "asset":
        asset = context.user_data.get("pending_asset_confirm")
        # Handle the missing or empty asset case.
        if not asset:
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit aset expired. Coba input ulang.")
            # Return True to the caller.
            return True

        # Prepare asset updates for the next step.
        asset_updates = dict(updates)
        if "amount" in asset_updates:
            asset_updates["amount"] = asset_updates["amount"]
        if "description" in asset_updates and not asset_updates.get("name") and not asset.get("name"):
            asset_updates["name"] = asset_updates["description"]

        # Update asset with the current value.
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

        # Wait for reply_update_safely before continuing this flow.
        await reply_update_safely(
            # Include this value in the surrounding collection or call.
            update,
            f"✅ Preview aset sudah diupdate.\n\n{build_asset_confirm_preview(asset)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("asset", True),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    parsed = context.user_data.get("pending_parsed")
    # Handle the missing or empty parsed case.
    if not parsed:
        context.user_data.pop("pending_preview_edit", None)
        await update.message.reply_text("❌ Sesi edit transaksi expired. Coba input ulang.")
        # Return True to the caller.
        return True

    # Prepare parsed for the next step.
    parsed = apply_preview_edit_updates_to_parsed(parsed, updates)
    context.user_data["pending_parsed"] = parsed
    context.user_data.pop("pending_preview_edit", None)

    # Handle the case where needs_account(parsed).
    if needs_account(parsed):
        # Wait for reply_update_safely before continuing this flow.
        await reply_update_safely(
            # Include this value in the surrounding collection or call.
            update,
            f"✅ Preview sudah diupdate.\n\n{build_single_account_prompt(parsed)}",
            parse_mode="Markdown",
            reply_markup=account_keyboard("acc"),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Prepare short summary for the next step.
    short_summary = build_single_short_summary(parsed)
    # Prepare preview for the next step.
    preview = build_preview(parsed)
    # Wait for reply_update_safely before continuing this flow.
    await reply_update_safely(
        # Include this value in the surrounding collection or call.
        update,
        f"✅ Preview sudah diupdate.\n\n{preview}\n\n{preview_action_question(True)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("single", True),
    # Close the structure that was opened above.
    )
    # Return True to the caller.
    return True


# Define format split bill preview line for callers in this flow.
def format_split_bill_preview_line(parsed: dict) -> str:
    """Format data into a readable display for split bill preview line."""
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    # Handle the missing or empty split_bill case.
    if not split_bill:
        return ""

    total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share = float(split_bill.get("share_amount", 0) or 0)
    total_receivable = float(split_bill.get("total_receivable", 0) or 0)
    status = split_bill.get("status")

    if status == "paid":
        status_label = "sudah dibayar"
        # Prepare receivable display for the next step.
        receivable_display = 0
    elif status == "unpaid":
        status_label = "belum dibayar / masuk piutang"
        # Prepare receivable display for the next step.
        receivable_display = total_receivable
    # Handle the fallback path after earlier conditions are skipped.
    else:
        status_label = "menunggu status"
        # Prepare receivable display for the next step.
        receivable_display = total_receivable

    # Return ( to the caller.
    return (
        f"🤝 Split: {status_label} | "
        f"total dibayar {format_rupiah(total)} | "
        f"bagian kamu {format_rupiah(share)} | "
        f"piutang aktif {format_rupiah(receivable_display)}"
    # Close the structure that was opened above.
    )

# Define build preview for callers in this flow.
def build_preview(parsed: dict) -> str:
    """Build the data structure or message text for preview."""
    # Open a multi-line structure for the values below.
    type_label = {
        "expense": "❌ Pengeluaran",
        "income": "✅ Pemasukan",
        "transfer": "🔄 Transfer",
    }.get(parsed.get("type"), "❓")

    # Open a multi-line structure for the values below.
    lines = [
        f"*{type_label}*",
        f"💰 Nominal : {format_rupiah(parsed.get('amount', 0))}",
        f"📁 Kategori: {parsed.get('category') or '-'}",
        f"👤 Subjek  : {parsed.get('subject') or '-'}",
        f"📝 Deskripsi: {parsed.get('description') or '-'}",
    # Close the structure that was opened above.
    ]

    # Prepare split preview for the next step.
    split_preview = format_split_bill_preview_line(parsed)
    # Handle the case where split_preview.
    if split_preview:
        # Update lines with the current value.
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
    # Handle the case where account_summary.
    if account_summary:
        # Update lines with the current value.
        lines.append(account_summary)

    return "\n".join(lines)


# Define build batch preview for callers in this flow.
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
    # Prepare total count for the next step.
    total_count = len(parsed_items or [])
    lines = [f"🧾 *Preview ({total_count} transaksi)*", ""]

    # Prepare total expense for the next step.
    total_expense = 0.0
    # Prepare total income for the next step.
    total_income = 0.0
    # Run this statement as part of the current workflow.
    category_summary: dict[str, dict[str, float | int]] = {}
    # Run this statement as part of the current workflow.
    grouped_by_date: dict[str, list[tuple[int, dict]]] = {}

    # Process each idx, item in the current collection.
    for idx, item in enumerate(parsed_items or [], 1):
        parsed = item.get("parsed", {}) or {}
        amount = _receipt_amount(parsed.get("amount"), 0)
        txn_type = parsed.get("type")

        if txn_type == "expense":
            # Run this statement as part of the current workflow.
            total_expense += amount
        elif txn_type == "income":
            # Run this statement as part of the current workflow.
            total_income += amount

        category = str(parsed.get("category") or "-").strip() or "-"
        cat_data = category_summary.setdefault(category, {"count": 0, "amount": 0.0})
        cat_data["count"] = int(cat_data.get("count", 0)) + 1
        cat_data["amount"] = float(cat_data.get("amount", 0) or 0) + amount

        date_key = str(parsed.get("date") or "-").strip() or "-"
        # Run this statement as part of the current workflow.
        grouped_by_date.setdefault(date_key, []).append((idx, parsed))

    lines.append(f"❌ Expense : {format_rupiah(total_expense)}")
    lines.append(f"✅ Income  : {format_rupiah(total_income)}")

    # Handle the case where category_summary.
    if category_summary:
        lines.extend(["", "📊 *Kategori*"])
        # Process each category, data in the current collection.
        for category, data in sorted(
            # Include this value in the surrounding collection or call.
            category_summary.items(),
            key=lambda pair: float(pair[1].get("amount", 0) or 0),
            # Prepare reverse for the next step.
            reverse=True,
        # Close the structure that was opened above.
        ):
            # Open a multi-line structure for the values below.
            lines.append(
                f"• {md_safe(category)} ({int(data.get('count', 0))}): "
                f"{format_rupiah(float(data.get('amount', 0) or 0))}"
            # Close the structure that was opened above.
            )

    lines.extend(["", "──────────────────"])

    # Process each date_key in the current collection.
    for date_key in sorted(grouped_by_date.keys()):
        lines.append(f"📅 {md_safe(date_key)}")
        lines.append("")

        # Process each idx, parsed in the current collection.
        for idx, parsed in grouped_by_date[date_key]:
            txn_type = parsed.get("type")
            # Open a multi-line structure for the values below.
            type_icon = {
                "expense": "❌",
                "income": "✅",
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
            # Open a multi-line structure for the values below.
            lines.append(
                f"   📁 {md_safe(category)} • 🏦 {md_safe(account)} • 🏷️ {md_safe(spending_type)}"
            # Close the structure that was opened above.
            )

            # Handle the case where description.
            if description:
                lines.append(f"   📝 {md_safe(description)}")

            if parsed.get("catatan"):
                lines.append(f"   🗒️ {md_safe(parsed.get('catatan'))}")

            lines.append("")

    if lines and lines[-1] == "":
        # Update lines with the current value.
        lines.pop()
    lines.append("──────────────────")

    lines.extend(["", "Lanjut ke rekening/simpan?"])
    return "\n".join(lines)


# ── Receipt / Image Selection Flow ────────────────────────────────────────────

# Open a multi-line structure for the values below.
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
# Close the structure that was opened above.
}


# Define is receipt image result for callers in this flow.
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


# Define receipt merchant for callers in this flow.
def _receipt_merchant(receipt: dict, items: list[dict] | None = None) -> str:
    """Resolve the merchant name used in receipt previews."""
    merchant = str((receipt or {}).get("merchant") or "").strip()
    # Handle the case where merchant.
    if merchant:
        # Return merchant to the caller.
        return merchant
    # Process each item in the current collection.
    for item in items or []:
        subject = str(item.get("subject") or "").strip()
        # Handle the case where subject.
        if subject:
            # Return subject to the caller.
            return subject
    return "Struk"




# Define receipt amount for callers in this flow.
def _receipt_amount(value, default: float = 0.0) -> float:
    """Parse receipt amount fields that may use Indonesian thousand separators."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Handle the case where isinstance(value, str).
        if isinstance(value, str):
            raw = value.strip().replace("Rp", "").replace("rp", "").replace(" ", "")
            raw = re.sub(r"[^0-9.,-]", "", raw)
            if "," in raw and "." in raw:
                raw = raw.replace(".", "").replace(",", ".")
            elif "," in raw:
                raw = raw.replace(",", ".")
            elif "." in raw:
                parts = raw.split(".")
                # Handle the case where len(parts) > 1 and all(len(part) == 3 for part in parts[1:]).
                if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
                    raw = raw.replace(".", "")
            # Return float(raw or default) to the caller.
            return float(raw or default)
        # Return float(value or default) to the caller.
        return float(value or default)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return float(default) to the caller.
        return float(default)

# Define receipt item quantity for callers in this flow.
def _receipt_item_quantity(item: dict) -> float:
    """Return the receipt item quantity with a safe fallback."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        quantity = float(item.get("quantity", 1) or 1)
        # Return quantity if quantity > 0 else 1.0 to the caller.
        return quantity if quantity > 0 else 1.0
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return 1.0 to the caller.
        return 1.0


# Define receipt extra charges for callers in this flow.
def _receipt_extra_charges(receipt: dict) -> list[dict]:
    """Return normalized extra charge components from receipt metadata."""
    # Prepare charges for the next step.
    charges = []
    for charge in (receipt or {}).get("extra_charges") or []:
        # Handle the missing or empty isinstance(charge, dict) case.
        if not isinstance(charge, dict):
            # Skip the rest of this loop iteration after handling this case.
            continue
        amount = _receipt_amount(charge.get("amount"), 0)
        # Handle the case where amount <= 0.
        if amount <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Open a multi-line structure for the values below.
        charges.append({
            "label": str(charge.get("label") or "Biaya tambahan").strip(),
            "amount": int(round(amount)),
            "is_discount": bool(charge.get("is_discount")),
        # Close the structure that was opened above.
        })
    # Return charges to the caller.
    return charges


# Define receipt extra charge net amount for callers in this flow.
def receipt_extra_charge_net_amount(receipt: dict) -> int:
    """Calculate net extra charge from service, tax, other charges, and discount."""
    # Prepare total for the next step.
    total = 0
    # Process each charge in the current collection.
    for charge in _receipt_extra_charges(receipt):
        amount = int(charge.get("amount", 0) or 0)
        total += -amount if charge.get("is_discount") else amount
    # Return int(round(total)) to the caller.
    return int(round(total))


# Define receipt extra charge detail for callers in this flow.
def _receipt_extra_charge_detail(receipt: dict, divisor: int | None = None) -> str:
    """Build a compact note for the combined extra charge transaction."""
    # Prepare parts for the next step.
    parts = []
    # Process each charge in the current collection.
    for charge in _receipt_extra_charges(receipt):
        label = charge.get("label") or "Biaya tambahan"
        amount = int(charge.get("amount", 0) or 0)
        sign = "-" if charge.get("is_discount") else ""
        # Handle the case where divisor and divisor > 1.
        if divisor and divisor > 1:
            # Prepare share for the next step.
            share = int(round(amount / divisor))
            parts.append(f"{label} {sign}{format_rupiah(amount)} dibagi {divisor} = {sign}{format_rupiah(share)}")
        # Handle the fallback path after earlier conditions are skipped.
        else:
            parts.append(f"{label} {sign}{format_rupiah(amount)}")
    return "; ".join(parts)


# Define receipt extra charge description for callers in this flow.
def _receipt_extra_charge_description(receipt: dict, merchant: str) -> str:
    """Build the saved description for the combined receipt extra charge."""
    labels = [str(charge.get("label") or "").strip().lower() for charge in _receipt_extra_charges(receipt)]
    has_service = any("service" in label or "layanan" in label for label in labels)
    has_tax = any("ppn" in label or "tax" in label or "pajak" in label for label in labels)
    has_discount = any(charge.get("is_discount") for charge in _receipt_extra_charges(receipt))

    # Handle the case where has_service and has_tax and has_discount.
    if has_service and has_tax and has_discount:
        prefix = "Service, PPN & Diskon"
    # Handle the alternate case where has_service and has_tax.
    elif has_service and has_tax:
        prefix = "Service & PPN"
    # Handle the alternate case where has_discount.
    elif has_discount:
        prefix = "Biaya tambahan & Diskon"
    # Handle the fallback path after earlier conditions are skipped.
    else:
        prefix = "Biaya tambahan"

    return f"{prefix} {merchant}".strip()[:80]


# Define build receipt review text for callers in this flow.
def build_receipt_review_text(receipt: dict, items: list[dict]) -> str:
    """Build the first OCR review text for receipt images.

    Args:
        receipt: Receipt-level metadata from Gemini Vision.
        items: Itemized receipt rows parsed from the image.

    Returns:
        Markdown text that shows OCR details before the user chooses whether all
        items or only part of the receipt should be recorded.
    """
    # Prepare merchant for the next step.
    merchant = _receipt_merchant(receipt, items)
    date = (receipt or {}).get("date") or (items[0].get("date") if items else "-")
    item_total = sum(_receipt_amount(item.get("amount"), 0) for item in items)
    # Prepare net extra for the next step.
    net_extra = receipt_extra_charge_net_amount(receipt)
    total = float((receipt or {}).get("total") or 0) or item_total + net_extra

    # Open a multi-line structure for the values below.
    lines = [
        "🧾 *Struk berhasil dibaca.*",
        "",
        f"Merchant: *{md_safe(merchant)}*",
        f"Tanggal : {md_safe(date)}",
        f"Total   : *{format_rupiah(total)}*",
        "",
        "📋 *Rincian item:*",
    # Close the structure that was opened above.
    ]

    # Process each idx, item in the current collection.
    for idx, item in enumerate(items, 1):
        desc = md_safe(item.get("description") or item.get("subject") or f"Item {idx}")
        # Prepare qty for the next step.
        qty = _receipt_item_quantity(item)
        amount = _receipt_amount(item.get("amount"), 0)
        unit_price = _receipt_amount(item.get("unit_price"), 0) or (amount / qty if qty else amount)
        # Open a multi-line structure for the values below.
        lines.extend([
            f"{idx}. *{desc}*",
            f"   Qty: {qty:g}",
            f"   Total: {format_rupiah(amount)}",
            f"   Harga satuan: {format_rupiah(unit_price)}",
        # Close the structure that was opened above.
        ])

    # Prepare charges for the next step.
    charges = _receipt_extra_charges(receipt)
    # Handle the case where charges.
    if charges:
        lines.extend(["", "💳 *Biaya tambahan:*"])
        # Process each charge in the current collection.
        for charge in charges:
            label = md_safe(charge.get("label") or "Biaya tambahan")
            sign = "-" if charge.get("is_discount") else ""
            lines.append(f"• {label}: {sign}{format_rupiah(charge.get('amount', 0))}")
        lines.append(f"• Total biaya tambahan: *{format_rupiah(net_extra)}*")

    # Open a multi-line structure for the values below.
    lines.extend([
        "",
        "🧮 *Pengecekan total:*",
        f"• Subtotal item: {format_rupiah(item_total)}",
        f"• Biaya tambahan net: {format_rupiah(net_extra)}",
        f"• Total struk: *{format_rupiah(total)}*",
        "",
        "Apakah semua item di struk ini masuk ke pengeluaran kamu?",
    # Close the structure that was opened above.
    ])
    return "\n".join(lines)


# Define build receipt part selection prompt for callers in this flow.
def build_receipt_part_selection_prompt(receipt: dict, items: list[dict]) -> str:
    """Build instructions for selecting only part of a receipt."""
    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    ]

    # Process each idx, item in the current collection.
    for idx, item in enumerate(items, 1):
        desc = md_safe(item.get("description") or item.get("subject") or f"Item {idx}")
        # Prepare qty for the next step.
        qty = _receipt_item_quantity(item)
        amount = _receipt_amount(item.get("amount"), 0)
        unit_price = _receipt_amount(item.get("unit_price"), 0) or (amount / qty if qty else amount)
        # Open a multi-line structure for the values below.
        lines.append(
            f"{idx}. {desc} | Qty {qty:g} | Total {format_rupiah(amount)} | Satuan {format_rupiah(unit_price)}"
        # Close the structure that was opened above.
        )

    return "\n".join(lines)


# Define parse receipt number for callers in this flow.
def _parse_receipt_number(value: str | None, default: float = 1.0) -> float:
    """Parse a small quantity or divisor from natural Indonesian text."""
    raw = str(value or "").strip().lower()
    # Handle the missing or empty raw case.
    if not raw:
        # Return default to the caller.
        return default

    # Handle the case where raw in RECEIPT_NUMBER_WORDS.
    if raw in RECEIPT_NUMBER_WORDS:
        # Return float(RECEIPT_NUMBER_WORDS[raw]) to the caller.
        return float(RECEIPT_NUMBER_WORDS[raw])

    match = re.search(r"\d+(?:[.,]\d+)?", raw)
    # Handle the case where match.
    if match:
        return float(match.group(0).replace(",", "."))

    # Return default to the caller.
    return default


# Define parse receipt part selection for callers in this flow.
def parse_receipt_part_selection(user_text: str, items: list[dict]) -> dict:
    """Parse the user's selected receipt rows and shares.

    Args:
        user_text: Natural text such as `4 beli 1` or `5 beli 1 dibagi 2`.
        items: Receipt items shown to the user.

    Returns:
        Dict with `success`, selected parts, and total amount. No data is saved
        here; this only prepares the next receipt step.
    """
    # Prepare selected for the next step.
    selected = []
    # Prepare failed lines for the next step.
    failed_lines = []

    for raw_line in re.split(r"[\n;]+", str(user_text or "")):
        line = raw_line.strip(" .,-")
        # Handle the missing or empty line case.
        if not line:
            # Skip the rest of this loop iteration after handling this case.
            continue

        index_match = re.match(r"^\s*(\d+)\b", line)
        # Handle the missing or empty index_match case.
        if not index_match:
            # Update failed lines with the current value.
            failed_lines.append(line)
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Prepare item index for the next step.
        item_index = int(index_match.group(1)) - 1
        # Handle the case where item_index < 0 or item_index >= len(items).
        if item_index < 0 or item_index >= len(items):
            # Update failed lines with the current value.
            failed_lines.append(line)
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Open a multi-line structure for the values below.
        qty_match = re.search(
            r"\b(?:beli|ambil|porsi|qty|x)\s+([\w.,]+(?:\s+belas)?)",
            # Include this value in the surrounding collection or call.
            line,
            # Prepare flags for the next step.
            flags=re.IGNORECASE,
        # Close the structure that was opened above.
        )
        take_qty = _parse_receipt_number(qty_match.group(1) if qty_match else "1", 1)
        # Handle the case where take_qty <= 0.
        if take_qty <= 0:
            # Update failed lines with the current value.
            failed_lines.append(line)
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Open a multi-line structure for the values below.
        divisor_match = re.search(
            r"\b(?:di\s*-?\s*bagi|dibagi|bagi|split|share)\s+([\w.,]+(?:\s+belas)?)",
            # Include this value in the surrounding collection or call.
            line,
            # Prepare flags for the next step.
            flags=re.IGNORECASE,
        # Close the structure that was opened above.
        )
        # Prepare share divisor for the next step.
        share_divisor = int(round(_parse_receipt_number(divisor_match.group(1), 1))) if divisor_match else 1
        # Prepare share divisor for the next step.
        share_divisor = max(1, share_divisor)

        # Prepare item for the next step.
        item = items[item_index]
        # Prepare receipt qty for the next step.
        receipt_qty = _receipt_item_quantity(item)
        line_amount = _receipt_amount(item.get("amount"), 0)
        # Prepare unit amount for the next step.
        unit_amount = line_amount / receipt_qty if receipt_qty else line_amount
        # Prepare before share for the next step.
        before_share = unit_amount * take_qty
        # Prepare amount for the next step.
        amount = int(round(before_share / share_divisor))

        # Open a multi-line structure for the values below.
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
        # Close the structure that was opened above.
        })

    # Handle the missing or empty selected case.
    if not selected:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Pilihan item belum kebaca. Coba tulis seperti `4 beli 1` atau `5 beli 1 dibagi 2`.",
            "failed_lines": failed_lines,
            "selected": [],
            "subtotal": 0,
        # Close the structure that was opened above.
        }

    # Return { to the caller.
    return {
        "success": True,
        "message": "ok",
        "failed_lines": failed_lines,
        "selected": selected,
        "subtotal": sum(part["amount"] for part in selected),
    # Close the structure that was opened above.
    }


# Define build receipt selected breakdown for callers in this flow.
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

    # Prepare charges for the next step.
    charges = _receipt_extra_charges(receipt)
    # Handle the case where charges.
    if charges:
        lines.extend(["", "💳 *Biaya tambahan di struk:*"])
        # Process each charge in the current collection.
        for charge in charges:
            sign = "-" if charge.get("is_discount") else ""
            lines.append(f"• {md_safe(charge.get('label'))}: {sign}{format_rupiah(charge.get('amount', 0))}")
        lines.append("")
        lines.append("Biaya tambahan ini dibagi berapa orang?")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.extend(["", "Tidak ada biaya tambahan yang terbaca."])

    failed_lines = selection_result.get("failed_lines") or []
    # Handle the case where failed_lines.
    if failed_lines:
        lines.extend(["", "⚠️ Baris yang belum kebaca:"])
        # Process each line in the current collection.
        for line in failed_lines[:5]:
            lines.append(f"• `{md_code_text(line)}`")

    return "\n".join(lines).strip()


# Define parse receipt divisor for callers in this flow.
def parse_receipt_divisor(user_text: str) -> int:
    """Parse the divisor used for receipt service/tax sharing."""
    # Open a multi-line structure for the values below.
    match = re.search(
        r"\b(?:di\s*-?\s*bagi|dibagi|bagi|split|share)\s+([\w.,]+(?:\s+belas)?)",
        str(user_text or ""),
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Prepare divisor for the next step.
    divisor = _parse_receipt_number(match.group(1) if match else user_text, 0)
    # Return max(0, int(round(divisor))) to the caller.
    return max(0, int(round(divisor)))


# Define receipt transaction item for callers in this flow.
def _receipt_transaction_item(parsed: dict, raw: str, amount: int | None = None, catatan: str | None = None) -> dict:
    """Create one mixed transaction item from a receipt row."""
    # Prepare data for the next step.
    data = dict(parsed or {})
    # Handle the case where amount is not None.
    if amount is not None:
        data["amount"] = int(round(amount))
    # Handle the case where catatan is not None.
    if catatan is not None:
        old_note = str(data.get("catatan") or "").strip()
        data["catatan"] = f"{catatan} | {old_note}".strip(" |")
    data["parsed_by"] = data.get("parsed_by") or "gemini_image"
    return {"kind": "transaction", "parsed": data, "raw": raw}


# Define receipt extra charge item for callers in this flow.
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
    # Handle the case where amount <= 0.
    if amount <= 0:
        # Return None to the caller.
        return None

    # Prepare merchant for the next step.
    merchant = _receipt_merchant(receipt, items)
    # Prepare base item for the next step.
    base_item = items[0] if items else {}
    # Prepare description for the next step.
    description = _receipt_extra_charge_description(receipt, merchant)
    # Prepare note for the next step.
    note = _receipt_extra_charge_detail(receipt, divisor=divisor)

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    }
    return {"kind": "transaction", "parsed": parsed, "raw": f"biaya tambahan struk {merchant}"}


# Define build receipt all mixed items for callers in this flow.
def build_receipt_all_mixed_items(receipt: dict, items: list[dict]) -> tuple[list[dict], dict]:
    """Build mixed items when all receipt rows belong to the user."""
    # Prepare mixed items for the next step.
    mixed_items = []
    # Process each idx, item in the current collection.
    for idx, item in enumerate(items, 1):
        desc = item.get("description") or item.get("subject") or f"Item {idx}"
        mixed_items.append(_receipt_transaction_item(item, f"struk item {idx}: {desc}"))

    # Prepare net extra for the next step.
    net_extra = receipt_extra_charge_net_amount(receipt)
    # Prepare extra item for the next step.
    extra_item = _receipt_extra_charge_item(receipt, items, net_extra)
    # Handle the case where extra_item.
    if extra_item:
        # Update mixed items with the current value.
        mixed_items.append(extra_item)

    # Open a multi-line structure for the values below.
    context = {
        "mode": "all",
        "receipt": receipt,
        "extra_charge_amount": max(0, net_extra),
        "extra_charge_divisor": None,
        "selected_parts": [],
    # Close the structure that was opened above.
    }
    # Return mixed_items, context to the caller.
    return mixed_items, context


# Define build receipt partial mixed items for callers in this flow.
def build_receipt_partial_mixed_items(receipt: dict, selection_result: dict, divisor: int) -> tuple[list[dict], dict]:
    """Build mixed items when only selected receipt rows belong to the user."""
    selected_parts = selection_result.get("selected") or []
    selected_items = [part["item"] for part in selected_parts]
    # Prepare mixed items for the next step.
    mixed_items = []

    # Process each idx, part in the current collection.
    for idx, part in enumerate(selected_parts, 1):
        item = part["item"]
        desc = item.get("description") or item.get("subject") or f"Item {idx}"
        if part["share_divisor"] > 1:
            note = f"{part['take_qty']:g} dari {part['receipt_qty']:g} qty, lalu dibagi {part['share_divisor']} orang"
        # Handle the fallback path after earlier conditions are skipped.
        else:
            note = f"{part['take_qty']:g} dari {part['receipt_qty']:g} qty"
        # Open a multi-line structure for the values below.
        mixed_items.append(
            # Open a multi-line structure for the values below.
            _receipt_transaction_item(
                # Include this value in the surrounding collection or call.
                item,
                f"bagian struk item {part['item_index'] + 1}: {desc}",
                amount=part["amount"],
                # Prepare catatan for the next step.
                catatan=note,
            # Close the structure that was opened above.
            )
        # Close the structure that was opened above.
        )

    # Prepare net extra for the next step.
    net_extra = receipt_extra_charge_net_amount(receipt)
    # Prepare extra share for the next step.
    extra_share = int(round(net_extra / divisor)) if divisor > 0 else 0
    # Prepare extra item for the next step.
    extra_item = _receipt_extra_charge_item(receipt, selected_items, max(0, extra_share), divisor=divisor)
    # Handle the case where extra_item.
    if extra_item:
        # Update mixed items with the current value.
        mixed_items.append(extra_item)

    # Open a multi-line structure for the values below.
    context = {
        "mode": "partial",
        "receipt": receipt,
        "extra_charge_amount": max(0, extra_share),
        "extra_charge_divisor": divisor,
        "selected_parts": selected_parts,
        "subtotal_items": selection_result.get("subtotal", 0),
    # Close the structure that was opened above.
    }
    # Return mixed_items, context to the caller.
    return mixed_items, context


# Define build receipt account prompt for callers in this flow.
def build_receipt_account_prompt(mixed_items: list[dict], receipt_context: dict) -> str:
    """Build the rekening prompt after receipt rows are converted to mixed items."""
    receipt = (receipt_context or {}).get("receipt") or {}
    merchant = _receipt_merchant(receipt, [item.get("parsed", {}) for item in mixed_items])
    total = sum(_receipt_amount(item.get("parsed", {}).get("amount"), 0) for item in mixed_items)
    mode = (receipt_context or {}).get("mode")
    mode_label = "semua item" if mode == "all" else "bagian kamu"

    # Open a multi-line structure for the values below.
    lines = [
        f"🧾 Struk *{md_safe(merchant)}* sudah diproses sebagai batch ({mode_label}).",
        f"• Total item disimpan: *{len(mixed_items)}*",
        f"• Total expense: *{format_rupiah(total)}*",
        "",
    # Close the structure that was opened above.
    ]

    if mode == "partial":
        lines.append(f"• Subtotal item kamu: {format_rupiah((receipt_context or {}).get('subtotal_items', 0))}")
        lines.append(f"• Biaya tambahan kamu: {format_rupiah((receipt_context or {}).get('extra_charge_amount', 0))}")
        lines.append("")

    lines.append("💳 Dari rekening mana?")
    lines.append("Atau pilih *Sudah berlalu* jika transaksi hanya catatan historis dan tidak mau mengubah saldo.")
    return "\n".join(lines)


# Define build receipt final preview for callers in this flow.
def build_receipt_final_preview(mixed_items: list[dict], receipt_context: dict, account_label: str | None = None) -> str:
    """Build the final receipt batch preview before save."""
    # Prepare receipt context for the next step.
    receipt_context = receipt_context or {}
    receipt = receipt_context.get("receipt") or {}
    merchant = _receipt_merchant(receipt, [item.get("parsed", {}) for item in mixed_items])
    total = sum(_receipt_amount(item.get("parsed", {}).get("amount"), 0) for item in mixed_items)
    category = "-"
    account = account_label or "-"
    # Process each item in the current collection.
    for item in mixed_items:
        parsed = item.get("parsed", {})
        if parsed.get("category") and category == "-":
            category = parsed.get("category")
        if parsed.get("account") and (not account_label):
            account = parsed.get("account")

    mode = receipt_context.get("mode")
    mode_label = "semua struk" if mode == "all" else "bagian struk"

    # Open a multi-line structure for the values below.
    lines = [
        f"🧾 *Ringkasan batch dari {mode_label}*",
        f"• Merchant: *{md_safe(merchant)}*",
        f"• Total item: *{len(mixed_items)}*",
        f"• Expense: *{format_rupiah(total)}*",
        f"• Kategori: {md_safe(category)}",
        f"• Rekening: {md_safe(account)}",
        "",
        "📋 *Rincian transaksi yang akan disimpan:*",
    # Close the structure that was opened above.
    ]

    # Process each idx, item in the current collection.
    for idx, item in enumerate(mixed_items, 1):
        parsed = item.get("parsed", {})
        desc = md_safe(parsed.get("description") or parsed.get("subject") or f"Item {idx}")
        amount = _receipt_amount(parsed.get("amount"), 0)
        lines.append(f"{idx}. {desc}: *{format_rupiah(amount)}*")
        note = parsed.get("catatan")
        # Handle the case where note.
        if note:
            lines.append(f"   Catatan: {md_safe(note)}")

    # Prepare charges for the next step.
    charges = _receipt_extra_charges(receipt)
    # Handle the case where charges.
    if charges:
        lines.extend(["", "💳 *Rincian biaya tambahan:*"])
        divisor = receipt_context.get("extra_charge_divisor")
        # Process each charge in the current collection.
        for charge in charges:
            amount = int(charge.get("amount", 0) or 0)
            sign = "-" if charge.get("is_discount") else ""
            # Handle the case where divisor and divisor > 1.
            if divisor and divisor > 1:
                # Prepare share for the next step.
                share = int(round(amount / divisor))
                # Open a multi-line structure for the values below.
                lines.append(
                    f"• {md_safe(charge.get('label'))}: {sign}{format_rupiah(amount)} / {divisor} = {sign}{format_rupiah(share)}"
                # Close the structure that was opened above.
                )
            # Handle the fallback path after earlier conditions are skipped.
            else:
                lines.append(f"• {md_safe(charge.get('label'))}: {sign}{format_rupiah(amount)}")
        lines.append(f"• Total biaya tambahan kamu: *{format_rupiah(receipt_context.get('extra_charge_amount', 0))}*")

    # Prepare account summary for the next step.
    account_summary = build_account_delta_summary_from_transaction_items(mixed_items)
    # Handle the case where account_summary.
    if account_summary:
        lines.extend(["", account_summary])

    return "\n".join(lines)


# Define strip split bill phrase for callers in this flow.
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

    # Open a multi-line structure for the values below.
    clean = re.sub(
        rf"\b{split_word}\s*(?:jadi\s*)?{participant_token}?\s*(?:orang\s+)?{friend_marker}\s+{name_chunk}",
        " ",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Open a multi-line structure for the values below.
    clean = re.sub(
        rf"\b{friend_marker}\s+{name_chunk}\s+{split_word}\s*(?:jadi\s*)?{participant_token}?",
        " ",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Debt flow section
    # "Nasi kuning 22k dibagi 2 raka".
    clean = re.sub(
        rf"\b{split_word}\s*(?:jadi\s*)?{participant_token}\s*(?:orang\s+)?{name_chunk}",
        " ",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Legacy compatibility note for older records or older in-memory state.
    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    clean = re.sub(
        rf"\b{split_word}\b.*$",
        " ",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    clean = re.sub(r"\s+", " ", clean).strip(" .,-")
    return clean or str(text or "").strip()


# Define strip trailing split person names for callers in this flow.
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
    # Handle the missing or empty clean or not person_names case.
    if not clean or not person_names:
        # Return clean to the caller.
        return clean

    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    ordered_names = sorted(
        [str(name or "").strip() for name in person_names if str(name or "").strip()],
        # Prepare key for the next step.
        key=len,
        # Prepare reverse for the next step.
        reverse=True,
    # Close the structure that was opened above.
    )

    # Prepare changed for the next step.
    changed = True
    # Repeat this block while changed and clean.
    while changed and clean:
        # Prepare changed for the next step.
        changed = False
        clean = clean.strip(" .,-")

        # Split bill parsing note: separate the paid transaction from each person share.
        new_clean = re.sub(r"\b(?:sama|ama|dengan|bareng|dan)\s*$", "", clean, flags=re.IGNORECASE).strip(" .,-")
        # Handle the case where new_clean != clean.
        if new_clean != clean:
            # Prepare clean for the next step.
            clean = new_clean
            # Prepare changed for the next step.
            changed = True

        # Process each person in the current collection.
        for person in ordered_names:
            pattern = rf"(?:^|[\s,;&]+){re.escape(person)}\s*$"
            new_clean = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip(" .,-")
            # Handle the case where new_clean != clean.
            if new_clean != clean:
                # Prepare clean for the next step.
                clean = new_clean
                # Prepare changed for the next step.
                changed = True
                # Leave the loop after the target condition has been reached.
                break

    # Return clean to the caller.
    return clean


# Open a multi-line structure for the values below.
SPLIT_BILL_ACCOUNT_TAIL_PATTERN = (
    r"\s+\b(?:via|pakai|pake|menggunakan|lewat|dari|from|using)\s+"
    r"(?:cash|bri|bsi|bca|dana|gopay|go\s*pay|seabank|sea\s*bank)\b.*$"
# Close the structure that was opened above.
)


# Define strip split bill account tail for callers in this flow.
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


# Define limit split bill friends to participants for callers in this flow.
def limit_split_bill_friends_to_participants(
    # Include this value in the surrounding collection or call.
    person_names: list[str],
    # Include this value in the surrounding collection or call.
    person_shares: dict,
    # Include this value in the surrounding collection or call.
    participants: int,
    # Include this value in the surrounding collection or call.
    base_share_amount: float,
# Close the structure that was opened above.
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
    # Prepare max friends for the next step.
    max_friends = max(int(participants or 0) - 1, 0)
    clean_names = [str(name or "").strip().title() for name in person_names or [] if str(name or "").strip()]

    # Handle the case where max_friends and len(clean_names) > max_friends.
    if max_friends and len(clean_names) > max_friends:
        # Prepare clean names for the next step.
        clean_names = clean_names[:max_friends]

    # Prepare clean shares for the next step.
    clean_shares = {}
    # Process each name in the current collection.
    for name in clean_names:
        # Run this statement as part of the current workflow.
        clean_shares[name] = float((person_shares or {}).get(name, base_share_amount) or 0)

    # Return clean_names, clean_shares to the caller.
    return clean_names, clean_shares


# Define split split bill person names for callers in this flow.
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
    # Prepare clean for the next step.
    clean = strip_split_bill_account_tail(name_text)

    # Stop before date/status words so they do not become friend names.
    clean = re.split(
        r"\b(tanggal|tgl|tg|pada|date|kemarin|hari|minggu|bulan|udah|sudah|belum|dibayar|bayar|lunas|ke)\b",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )[0]

    clean = re.sub(r"[^A-Za-zÀ-ÿ,;&\s]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip(" ,;&")
    # Handle the missing or empty clean case.
    if not clean:
        # Return [] to the caller.
        return []

    # Debt flow section
    if re.search(r"[,;&]|\bdan\b|\band\b", clean, flags=re.IGNORECASE):
        raw_parts = re.split(r"\s*(?:,|;|&|\bdan\b|\band\b)\s*", clean, flags=re.IGNORECASE)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Split bill parsing note: separate the paid transaction from each person share.
        raw_parts = clean.split()

    # Prepare names for the next step.
    names = []
    # Prepare seen for the next step.
    seen = set()
    noise = {"sama", "ama", "dengan", "bareng", "dan", "and", "via", "pakai", "pake", "menggunakan", "lewat"}

    # Process each part in the current collection.
    for part in raw_parts:
        part = re.sub(r"[^A-Za-zÀ-ÿ\s]", " ", str(part or ""))
        part = re.sub(r"\s+", " ", part).strip()
        # Handle the missing or empty part or part.lower() in noise case.
        if not part or part.lower() in noise:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Prepare normalized for the next step.
        normalized = part.title()
        # Prepare key for the next step.
        key = normalized.lower()
        # Handle the case where key not in seen.
        if key not in seen:
            # Update names with the current value.
            names.append(normalized)
            # Update seen with the current value.
            seen.add(key)

    # Return names to the caller.
    return names



# Define strip split bill name tail for callers in this flow.
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
    # Prepare clean for the next step.
    clean = strip_split_bill_account_tail(name_text)
    # Open a multi-line structure for the values below.
    clean = re.split(
        r"\b(tanggal|tgl|tg|pada|date|kemarin|hari|minggu|bulan|udah|sudah|belum|dibayar|bayar|lunas|ke)\b",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )[0]
    return re.sub(r"\s+", " ", clean).strip(" ,;&")


# Define is split bill allocation token for callers in this flow.
def is_split_bill_allocation_token(value: str) -> bool:
    """Check whether a condition is true for split bill allocation token."""
    raw = str(value or "").strip().lower().rstrip(".,;)")
    # Handle the missing or empty raw case.
    if not raw:
        # Return False to the caller.
        return False
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)?\s*(?:%|rb|ribu|k|jt|juta|m)?", raw))


# Define parse split bill share value for callers in this flow.
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
    # Handle the missing or empty raw case.
    if not raw:
        # Return 0.0 to the caller.
        return 0.0

    if raw.endswith("%"):
        # Run this operation in a guarded block so failures can be handled.
        try:
            pct = float(raw[:-1].replace(",", ".").strip())
            # Return max(base_share * pct / 100, 0.0) to the caller.
            return max(base_share * pct / 100, 0.0)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Return 0.0 to the caller.
            return 0.0

    # Return max(parse_amount_text(raw), 0.0) to the caller.
    return max(parse_amount_text(raw), 0.0)


# Define parse split bill people and shares for callers in this flow.
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
    # Prepare base share for the next step.
    base_share = float(total_amount or 0) / int(participants or 1)
    # Prepare clean for the next step.
    clean = strip_split_bill_name_tail(name_text)
    clean = clean.replace("=", ":")
    clean = re.sub(r"\s*:\s*", ":", clean)
    clean = re.sub(r"\s*(?:,|;|&|\bdan\b|\band\b)\s*", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Handle the missing or empty clean case.
    if not clean:
        # Return { to the caller.
        return {
            "person_names": [],
            "person_shares": {},
            "base_share_amount": base_share,
            "has_custom_share": False,
        # Close the structure that was opened above.
        }

    tokens = [t.strip(" ,;&") for t in clean.split() if t.strip(" ,;&")]
    noise = {"sama", "ama", "dengan", "bareng", "dan", "and", "via", "pakai", "pake", "menggunakan", "lewat"}
    # Prepare entries for the next step.
    entries = []
    # Prepare has custom share for the next step.
    has_custom_share = False
    # Prepare i for the next step.
    i = 0

    # Repeat this block while i < len(tokens).
    while i < len(tokens):
        # Prepare token for the next step.
        token = tokens[i].strip()
        # Prepare low for the next step.
        low = token.lower()

        # Handle the missing or empty token or low in noise case.
        if not token or low in noise:
            # Run this statement as part of the current workflow.
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        name = ""
        # Prepare value for the next step.
        value = None

        if ":" in token:
            name_part, value_part = token.split(":", 1)
            name_part = re.sub(r"[^A-Za-zÀ-ÿ\s]", " ", name_part).strip()
            # Prepare value part for the next step.
            value_part = value_part.strip()

            # Handle the case where name_part.
            if name_part:
                # Prepare name for the next step.
                name = name_part
                # Handle the case where is_split_bill_allocation_token(value_part).
                if is_split_bill_allocation_token(value_part):
                    # Prepare value for the next step.
                    value = value_part
                    # Prepare has custom share for the next step.
                    has_custom_share = True
                # Handle the alternate case where not value_part and i + 1 < len(tokens) and is_split_bill_allo....
                elif not value_part and i + 1 < len(tokens) and is_split_bill_allocation_token(tokens[i + 1]):
                    # Prepare value for the next step.
                    value = tokens[i + 1]
                    # Prepare has custom share for the next step.
                    has_custom_share = True
                    # Run this statement as part of the current workflow.
                    i += 1
        # Handle the alternate case where i + 1 < len(tokens) and is_split_bill_allocation_token(tokens....
        elif i + 1 < len(tokens) and is_split_bill_allocation_token(tokens[i + 1]):
            name_part = re.sub(r"[^A-Za-zÀ-ÿ\s]", " ", token).strip()
            # Handle the case where name_part.
            if name_part:
                # Prepare name for the next step.
                name = name_part
                # Prepare value for the next step.
                value = tokens[i + 1]
                # Prepare has custom share for the next step.
                has_custom_share = True
                # Run this statement as part of the current workflow.
                i += 1
        # Handle the alternate case where is_split_bill_allocation_token(token).
        elif is_split_bill_allocation_token(token):
            # Split bill parsing note: separate the paid transaction from each person share.
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the fallback path after earlier conditions are skipped.
        else:
            name_part = re.sub(r"[^A-Za-zÀ-ÿ\s]", " ", token).strip()
            # Handle the case where name_part.
            if name_part:
                # Prepare name for the next step.
                name = name_part

        # Handle the case where name.
        if name:
            normalized_name = re.sub(r"\s+", " ", name).strip().title()
            # Handle the case where normalized_name and normalized_name.lower() not in noise.
            if normalized_name and normalized_name.lower() not in noise:
                # Update entries with the current value.
                entries.append((normalized_name, value))

        # Run this statement as part of the current workflow.
        i += 1

    # Prepare person names for the next step.
    person_names = []
    # Prepare person shares for the next step.
    person_shares = {}
    # Prepare seen for the next step.
    seen = set()

    # Process each name, value in the current collection.
    for name, value in entries:
        # Prepare key for the next step.
        key = name.lower()
        # Handle the case where key in seen.
        if key in seen:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Update seen with the current value.
        seen.add(key)
        # Update person names with the current value.
        person_names.append(name)
        # Run this statement as part of the current workflow.
        person_shares[name] = parse_split_bill_share_value(value, base_share) if value else base_share

    # Return { to the caller.
    return {
        "person_names": person_names,
        "person_shares": person_shares,
        "base_share_amount": base_share,
        "has_custom_share": has_custom_share,
    # Close the structure that was opened above.
    }


# Define format split bill person shares for callers in this flow.
def format_split_bill_person_shares(split_bill: dict) -> str:
    """Format data into a readable display for split bill person shares."""
    shares = (split_bill or {}).get("person_shares") or {}
    person_names = (split_bill or {}).get("person_names") or []
    # Handle the missing or empty shares and person_names case.
    if not shares and person_names:
        fallback = float((split_bill or {}).get("base_share_amount", (split_bill or {}).get("share_amount", 0)) or 0)
        shares = {str(name): fallback for name in person_names if str(name or "").strip()}

    # Prepare parts for the next step.
    parts = []
    # Process each name in the current collection.
    for name in person_names:
        if not str(name or "").strip():
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Prepare amount for the next step.
        amount = float(shares.get(name, 0) or 0)
        parts.append(f"{name}: {format_rupiah(amount)}")

    return ", ".join(parts)

# Define clean split person name for callers in this flow.
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
    # Prepare names for the next step.
    names = split_split_bill_person_names(name)
    return " ".join(names).title() if names else ""


def build_split_bill_item_description_from_raw(raw: str, fallback: str = "") -> str:
    """Build the data structure or message text for split bill item description from raw."""
    text = normalize_slash_split_syntax(str(raw or ""))
    # Prepare text for the next step.
    text = strip_date_phrases(text)
    text = re.sub(r"\b(?:rp|idr)?\s*\d[\d.,]*\s*(?:rb|ribu|k|jt|juta|m|miliar)?\b", " ", text, flags=re.IGNORECASE)

    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|ptpt|split\s*bill|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"
    participant_token = r"(?:\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|berdua|bertiga|berempat|berlima|berenam)"
    name_chunk = r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s,;&:%./]{0,140}"

    # Open a multi-line structure for the values below.
    cleanup_patterns = [
        rf"\b{split_word}\s*(?:jadi\s*)?{participant_token}?\s*(?:orang\s+)?{friend_marker}\s+{name_chunk}",
        rf"\b{friend_marker}\s+{name_chunk}\s+{split_word}\s*(?:jadi\s*)?{participant_token}?",
        rf"\b{split_word}\s*(?:jadi\s*)?{participant_token}\s*(?:orang\s+)?{name_chunk}",
        rf"\b{participant_token}\s+{friend_marker}\s+{name_chunk}",
        rf"\b{split_word}\b.*$",
    # Close the structure that was opened above.
    ]
    # Process each pattern in the current collection.
    for pattern in cleanup_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    text = re.sub(r"^(?:beli|bayar|buat|untuk|jajan)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^A-Za-zÀ-ÿ0-9\s&/+.-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ./,-")

    if text and text not in {"/", "-"}:
        # Return text.title() to the caller.
        return text.title()

    # Prepare fallback clean for the next step.
    fallback_clean = strip_split_bill_phrase(fallback)
    fallback_clean = re.sub(r"^[\s/.-]+$", "", fallback_clean).strip()
    if re.match(r"^[\s/.-]*(?:sama|ama|dengan|bareng)\b", fallback_clean, flags=re.IGNORECASE):
        fallback_clean = ""
    if fallback_clean.startswith(("/", ".", "-")):
        fallback_clean = ""
    return fallback_clean.title() if fallback_clean else "Split Bill"


# Define detect split bill for callers in this flow.
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
        # Return None to the caller.
        return None

    normalized_raw = normalize_slash_split_syntax(str(raw or ""))
    # Prepare original total for the next step.
    original_total = extract_split_bill_total_amount(normalized_raw)
    amount = float(original_total or parsed.get("amount", 0) or 0)
    # Handle the case where amount <= 0.
    if amount <= 0:
        # Return None to the caller.
        return None

    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Split bill parsing note: separate the paid transaction from each person share.
    text = normalize_slash_split_syntax(str(raw or ""))
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|ptpt|split\s*bill|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"
    participant_token = r"(?:\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|berdua|bertiga|berempat|berlima|berenam)"
    name_chunk = r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s,;&:%./]{0,140}"

    # Phase 2 compact split: `split bill makan Budi 80k` or `ptpt makan 80k sama Budi`.
    compact_patterns_early = [
        rf"\b(?:split\s*bill|split|patungan|ptpt)\b\s+(?P<body>.+?)\s+(?:sama|ama|dengan|bareng)\s+(?P<names>{name_chunk})(?=\s*(?:tanggal|tgl|kemarin|hari\s+ini|besok|via|pakai|pake|dari|\d|rp|idr|$))",
        rf"\b(?:split\s*bill|split|patungan|ptpt)\b\s+(?P<body>.+?)\s+(?P<names>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{{0,80}}?)(?=\s*(?:\d|rp|idr|$))",
    # Close the structure that was opened above.
    ]
    # Process each compact_pattern in the current collection.
    for compact_pattern in compact_patterns_early:
        # Prepare compact match for the next step.
        compact_match = re.search(compact_pattern, text, flags=re.IGNORECASE)
        # Handle the missing or empty compact_match case.
        if not compact_match:
            # Skip the rest of this loop iteration after handling this case.
            continue
        compact_names = split_split_bill_person_names(compact_match.group("names") or "")
        # Open a multi-line structure for the values below.
        compact_names = [
            # Run this statement as part of the current workflow.
            name for name in compact_names
            if normalize_text(name) not in {"makan", "minum", "ngopi", "lunch", "dinner", "brunch", "jajan"}
        # Close the structure that was opened above.
        ]
        # Handle the missing or empty compact_names case.
        if not compact_names:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Prepare participants for the next step.
        participants = len(compact_names) + 1
        # Prepare base share amount for the next step.
        base_share_amount = amount / participants
        # Prepare person shares for the next step.
        person_shares = {person: base_share_amount for person in compact_names}
        parsed["amount"] = amount
        clean_desc = build_split_bill_item_description_from_raw(raw, parsed.get("description") or "")
        # Prepare clean desc for the next step.
        clean_desc = strip_trailing_split_person_names(clean_desc, compact_names)
        parsed["description"] = clean_desc
        if parsed.get("subject"):
            parsed["subject"] = clean_desc

        # Return { to the caller.
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
        # Close the structure that was opened above.
        }

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    ]

    # Prepare participants for the next step.
    participants = None
    # Prepare person names for the next step.
    person_names = []
    # Prepare person shares for the next step.
    person_shares = {}
    # Prepare base share amount for the next step.
    base_share_amount = 0.0
    # Prepare has custom share for the next step.
    has_custom_share = False

    # Process each idx, pattern in the current collection.
    for idx, pattern in enumerate(patterns):
        # Prepare match for the next step.
        match = re.search(pattern, text, flags=re.IGNORECASE)
        # Handle the missing or empty match case.
        if not match:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Handle the case where idx in (0, 2, 3).
        if idx in (0, 2, 3):
            # Prepare participants for the next step.
            participants = parse_participant_count(match.group(1))
            # Prepare name text for the next step.
            name_text = match.group(2)
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Prepare name text for the next step.
            name_text = match.group(1)
            # Prepare participants for the next step.
            participants = parse_participant_count(match.group(2))

        # Handle the missing or empty participants case.
        if not participants:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Prepare share parse for the next step.
        share_parse = parse_split_bill_people_and_shares(name_text, amount, participants)
        person_names = share_parse.get("person_names") or []
        person_shares = share_parse.get("person_shares") or {}
        base_share_amount = float(share_parse.get("base_share_amount", 0) or 0)
        # Open a multi-line structure for the values below.
        person_names, person_shares = limit_split_bill_friends_to_participants(
            # Include this value in the surrounding collection or call.
            person_names,
            # Include this value in the surrounding collection or call.
            person_shares,
            # Include this value in the surrounding collection or call.
            participants,
            # Include this value in the surrounding collection or call.
            base_share_amount,
        # Close the structure that was opened above.
        )
        has_custom_share = bool(share_parse.get("has_custom_share"))
        # Leave the loop after the target condition has been reached.
        break

    # Handle the missing or empty participants or participants < 2 or not person_names case.
    if not participants or participants < 2 or not person_names:
        # Phase 2: support compact input such as `split bill makan Budi 80k`
        # or `ptpt makan 80k sama Budi`. If no participant count is written,
        # treat the user + detected friend(s) as the participants.
        compact_patterns = [
            rf"\b(?:split\s*bill|split|patungan|ptpt)\b\s+(?P<body>.+?)\s+(?:sama|ama|dengan|bareng)\s+(?P<names>{name_chunk})(?=\s*(?:tanggal|tgl|kemarin|hari\s+ini|besok|via|pakai|pake|dari|\d|rp|idr|$))",
            rf"\b(?:split\s*bill|split|patungan|ptpt)\b\s+(?P<body>.+?)\s+(?P<names>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{0,80}?)(?=\s*(?:\d|rp|idr|$))",
        # Close the structure that was opened above.
        ]
        # Process each pattern in the current collection.
        for pattern in compact_patterns:
            # Prepare match for the next step.
            match = re.search(pattern, text, flags=re.IGNORECASE)
            # Handle the missing or empty match case.
            if not match:
                # Skip the rest of this loop iteration after handling this case.
                continue
            raw_names = match.group("names") or ""
            # Prepare person names for the next step.
            person_names = split_split_bill_person_names(raw_names)
            person_names = [name for name in person_names if normalize_text(name) not in {"makan", "ngopi", "lunch", "dinner"}]
            # Handle the missing or empty person_names case.
            if not person_names:
                # Skip the rest of this loop iteration after handling this case.
                continue
            # Prepare participants for the next step.
            participants = len(person_names) + 1
            # Prepare base share amount for the next step.
            base_share_amount = amount / participants
            # Prepare person shares for the next step.
            person_shares = {person: base_share_amount for person in person_names}
            # Prepare has custom share for the next step.
            has_custom_share = False
            # Leave the loop after the target condition has been reached.
            break

    # Handle the missing or empty participants or participants < 2 or not person_names case.
    if not participants or participants < 2 or not person_names:
        # Return None to the caller.
        return None

    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    parsed["amount"] = amount

    # Handle the missing or empty person_shares case.
    if not person_shares:
        # Prepare base share amount for the next step.
        base_share_amount = amount / participants
        # Prepare person shares for the next step.
        person_shares = {person: base_share_amount for person in person_names}

    # Prepare total receivable for the next step.
    total_receivable = sum(float(v or 0) for v in person_shares.values())
    # Handle the case where total_receivable > amount and total_receivable > 0.
    if total_receivable > amount and total_receivable > 0:
        # Prepare scale for the next step.
        scale = amount / total_receivable
        # Prepare person shares for the next step.
        person_shares = {person: float(value or 0) * scale for person, value in person_shares.items()}
        # Prepare total receivable for the next step.
        total_receivable = amount
    # Prepare user share amount for the next step.
    user_share_amount = max(amount - total_receivable, 0.0)
    # Prepare share amount for the next step.
    share_amount = user_share_amount  # Backward-compatible field: now represents the user share.

    # Debt flow section
    # Split bill parsing note: separate the paid transaction from each person share.
    # Debt flow section
    # Debt flow section
    clean_desc = build_split_bill_item_description_from_raw(raw, parsed.get("description") or "")
    # Prepare clean desc for the next step.
    clean_desc = strip_trailing_split_person_names(clean_desc, person_names)
    parsed["description"] = clean_desc

    subject = parsed.get("subject") or ""
    # Handle the case where subject.
    if subject:
        # Prepare clean subject for the next step.
        clean_subject = build_split_bill_item_description_from_raw(raw, subject)
        # Prepare clean subject for the next step.
        clean_subject = strip_trailing_split_person_names(clean_subject, person_names)
        # Handle the case where clean_subject != subject or re.search(split_word, subject, fl....
        if clean_subject != subject or re.search(split_word, subject, flags=re.IGNORECASE):
            parsed["subject"] = clean_subject or clean_desc

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }


# Define attach split bill if any for callers in this flow.
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
    # Prepare split bill for the next step.
    split_bill = detect_split_bill(parsed, raw)
    # Handle the case where split_bill.
    if split_bill:
        parsed["split_bill"] = split_bill
    # Return parsed to the caller.
    return parsed


# Define split bill needs decision for callers in this flow.
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


# Define mixed split bill needs decision for callers in this flow.
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
    # Process each item in the current collection.
    for item in mixed_items or []:
        if item.get("kind") == "transaction" and split_bill_needs_decision(item.get("parsed", {})):
            # Return True to the caller.
            return True
    # Return False to the caller.
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
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        # Open a multi-line structure for the values below.
        [
            InlineKeyboardButton("✅ Sudah dibayar", callback_data=f"split:paid:{scope}{suffix}"),
            InlineKeyboardButton("🟢 Belum, masuk piutang", callback_data=f"split:unpaid:{scope}{suffix}"),
        # Close the structure that was opened above.
        ],
        [InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")],
    # Close the structure that was opened above.
    ])


# Define mixed split bill keyboard for callers in this flow.
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
    # Prepare current index for the next step.
    current_index = get_next_mixed_split_bill_index(mixed_items)
    return split_bill_keyboard("mixed", current_index)


# Define build split bill prompt from parsed for callers in this flow.
def build_split_bill_prompt_from_parsed(parsed: dict) -> str:
    """Build the data structure or message text for split bill prompt from parsed."""
    split_bill = parsed.get("split_bill", {}) or {}
    person_names = split_bill.get("person_names") or [split_bill.get("person_name", "-")]
    participants = int(split_bill.get("participants", 2) or 2)
    total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share = float(split_bill.get("share_amount", 0) or 0)
    total_receivable = float(split_bill.get("total_receivable", share * len(person_names)) or 0)
    friend_text = ", ".join(str(p) for p in person_names if p)
    # Prepare detail text for the next step.
    detail_text = format_split_bill_person_shares(split_bill)
    detail_line = f"📌 Rincian teman: *{md_safe(detail_text)}*\n" if detail_text else ""
    date_text = parsed.get("date") or "-"

    # Return ( to the caller.
    return (
        "🤝 *Split bill terdeteksi*\n\n"
        f"📝 Item: *{md_safe(parsed.get('description') or '-')}*\n"
        f"📅 Tanggal: *{md_safe(date_text)}*\n"
        f"💰 Total dibayar: *{format_rupiah(total)}*\n"
        f"👥 Dibagi: *{participants} orang*\n"
        f"👤 Teman: *{md_safe(friend_text)}*\n"
        f"📌 Bagian kamu: *{format_rupiah(share)}*\n"
        # Run this statement as part of the current workflow.
        f"{detail_line}"
        f"📌 Total piutang jika belum dibayar: *{format_rupiah(total_receivable)}*\n\n"
        f"{md_safe(friend_text)} sudah bayar bagian mereka?\n"
        "Kalau *sudah*, transaksi disimpan sebesar bagian kamu saja.\n"
        "Kalau *belum*, transaksi disimpan sebesar total yang kamu talangi dan bagian teman masuk piutang."
    # Close the structure that was opened above.
    )


# Define build mixed split bill prompt for callers in this flow.
def build_mixed_split_bill_prompt(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed split bill prompt."""
    # Open a multi-line structure for the values below.
    split_items = [
        # Run this statement as part of the current workflow.
        item for item in mixed_items or []
        if item.get("kind") == "transaction" and split_bill_needs_decision(item.get("parsed", {}))
    # Close the structure that was opened above.
    ]

    lines = [f"🤝 *Split bill terdeteksi di {len(split_items)} item*\n"]

    # Process each i, item in the current collection.
    for i, item in enumerate(split_items, 1):
        parsed = item["parsed"]
        split_bill = parsed.get("split_bill", {}) or {}
        person_names = split_bill.get("person_names") or [split_bill.get("person_name", "-")]
        total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
        share = float(split_bill.get("share_amount", 0) or 0)
        total_receivable = float(split_bill.get("total_receivable", share * len(person_names)) or 0)
        friend_text = ", ".join(str(p) for p in person_names if p)
        # Prepare detail text for the next step.
        detail_text = format_split_bill_person_shares(split_bill)
        detail_suffix = f" | {md_safe(detail_text)}" if detail_text else ""
        date_text = parsed.get("date") or "-"
        # Open a multi-line structure for the values below.
        lines.append(
            f"{i}. {md_safe(parsed.get('description') or '-')} "
            f"(*{md_safe(date_text)}*) — "
            f"total *{format_rupiah(total)}*, bagian kamu *{format_rupiah(share)}*, "
            f"piutang *{format_rupiah(total_receivable)}*{detail_suffix}"
        # Close the structure that was opened above.
        )

    # Open a multi-line structure for the values below.
    lines.append(
        "\nApakah bagian teman-teman di item ini sudah dibayar?\n"
        "Pilih *Sudah dibayar* kalau transaksi cukup disimpan sebesar bagian kamu.\n"
        "Pilih *Belum* kalau kamu menalangi totalnya dan bagian teman otomatis masuk piutang."
    # Close the structure that was opened above.
    )
    return "\n".join(lines)


# Define get mixed split bill indexes for callers in this flow.
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
    # Prepare indexes for the next step.
    indexes = []
    # Process each idx, item in the current collection.
    for idx, item in enumerate(mixed_items or []):
        if item.get("kind") != "transaction":
            # Skip the rest of this loop iteration after handling this case.
            continue
        parsed = item.get("parsed", {})
        if isinstance(parsed, dict) and parsed.get("split_bill"):
            # Update indexes with the current value.
            indexes.append(idx)
    # Return indexes to the caller.
    return indexes


# Define get next mixed split bill index for callers in this flow.
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
    # Process each idx in the current collection.
    for idx in get_mixed_split_bill_indexes(mixed_items):
        parsed = mixed_items[idx].get("parsed", {})
        # Handle the case where split_bill_needs_decision(parsed).
        if split_bill_needs_decision(parsed):
            # Return idx to the caller.
            return idx
    # Return None to the caller.
    return None


# Define build mixed split bill queue prompt for callers in this flow.
def build_mixed_split_bill_queue_prompt(mixed_items: list[dict]) -> str:
    """Build the data structure or message text for mixed split bill queue prompt."""
    # Prepare split indexes for the next step.
    split_indexes = get_mixed_split_bill_indexes(mixed_items)
    # Prepare current index for the next step.
    current_index = get_next_mixed_split_bill_index(mixed_items)

    # Handle the case where current_index is None.
    if current_index is None:
        # Return build_mixed_detail_preview(mixed_items) to the caller.
        return build_mixed_detail_preview(mixed_items)

    # Prepare current pos for the next step.
    current_pos = split_indexes.index(current_index) + 1 if current_index in split_indexes else 1
    # Prepare total split for the next step.
    total_split = len(split_indexes)
    parsed = mixed_items[current_index].get("parsed", {})
    split_bill = parsed.get("split_bill", {}) or {}
    person_names = split_bill.get("person_names") or [split_bill.get("person_name", "-")]
    participants = int(split_bill.get("participants", 2) or 2)
    total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share = float(split_bill.get("share_amount", 0) or 0)
    total_receivable = float(split_bill.get("total_receivable", share * len(person_names)) or 0)
    friend_text = ", ".join(str(p) for p in person_names if p)
    # Prepare detail text for the next step.
    detail_text = format_split_bill_person_shares(split_bill)
    detail_line = f"📌 Rincian teman: *{md_safe(detail_text)}*\n" if detail_text else ""
    date_text = parsed.get("date") or "-"

    # Return ( to the caller.
    return (
        f"🤝 *Split bill {current_pos}/{total_split}*\n\n"
        f"📝 Item: *{md_safe(parsed.get('description') or '-')}*\n"
        f"📅 Tanggal: *{md_safe(date_text)}*\n"
        f"💰 Total dibayar: *{format_rupiah(total)}*\n"
        f"👥 Dibagi: *{participants} orang*\n"
        f"👤 Teman: *{md_safe(friend_text)}*\n"
        f"📌 Bagian kamu: *{format_rupiah(share)}*\n"
        # Run this statement as part of the current workflow.
        f"{detail_line}"
        f"📌 Total piutang jika belum dibayar: *{format_rupiah(total_receivable)}*\n\n"
        f"{md_safe(friend_text)} sudah bayar bagian untuk item ini?\n"
        "Pilihan ini *hanya berlaku untuk item ini*. Setelah dijawab, saya lanjut ke split bill berikutnya."
    # Close the structure that was opened above.
    )


# Define apply split bill decision to current mixed for callers in this flow.
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
    # Prepare current index for the next step.
    current_index = get_next_mixed_split_bill_index(mixed_items)
    # Handle the case where current_index is None.
    if current_index is None:
        # Return mixed_items, None to the caller.
        return mixed_items, None
    # Run this statement as part of the current workflow.
    mixed_items, decided_index, _ = apply_split_bill_decision_to_mixed_index(mixed_items, current_index, status)
    # Return mixed_items, decided_index to the caller.
    return mixed_items, decided_index


# Define apply split bill decision to mixed index for callers in this flow.
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
    # Handle the case where item_index is None or item_index < 0 or item_index >= len(mix....
    if item_index is None or item_index < 0 or item_index >= len(mixed_items or []):
        return mixed_items, None, "invalid"

    # Prepare item for the next step.
    item = mixed_items[item_index]
    if item.get("kind") != "transaction":
        return mixed_items, None, "invalid"

    parsed = item.get("parsed", {})
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    # Handle the missing or empty split_bill case.
    if not split_bill:
        return mixed_items, None, "invalid"

    if split_bill.get("status"):
        return mixed_items, item_index, "already_decided"

    # Run this statement as part of the current workflow.
    apply_split_bill_decision_to_parsed(parsed, status)
    item["parsed"] = parsed
    # Run this statement as part of the current workflow.
    mixed_items[item_index] = item
    return mixed_items, item_index, "applied"


# Split bill parsing note: separate the paid transaction from each person share.
# Debt flow section

# Define apply split bill decision to parsed for callers in this flow.
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
    # Handle the missing or empty split_bill case.
    if not split_bill:
        # Return parsed to the caller.
        return parsed

    split_bill["status"] = status

    total_amount = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share_amount = float(split_bill.get("user_share_amount", split_bill.get("share_amount", 0)) or 0)

    if status == "paid":
        # Handle the case where share_amount <= 0 and total_amount > 0.
        if share_amount <= 0 and total_amount > 0:
            participants = int(split_bill.get("participants", 0) or 0)
            # Handle the case where participants > 0.
            if participants > 0:
                # Prepare share amount for the next step.
                share_amount = total_amount / participants
                split_bill["share_amount"] = share_amount
                split_bill["user_share_amount"] = share_amount
        # Handle the case where share_amount > 0.
        if share_amount > 0:
            parsed["amount"] = share_amount
    elif status == "unpaid" and total_amount > 0:
        parsed["amount"] = total_amount

    # Return parsed to the caller.
    return parsed


# Define apply split bill decision to mixed for callers in this flow.
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
    # Process each item in the current collection.
    for item in mixed_items or []:
        if item.get("kind") != "transaction":
            # Skip the rest of this loop iteration after handling this case.
            continue
        parsed = item.get("parsed", {})
        if parsed.get("split_bill"):
            # Run this statement as part of the current workflow.
            apply_split_bill_decision_to_parsed(parsed, status)
    # Return mixed_items to the caller.
    return mixed_items


def create_split_bill_debt(parsed: dict, raw: str = "", source_transaction_id: str = "") -> dict | None:
    """Coordinate the create split bill debt logic in the Telegram handler layer.

    Args:
        parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        raw: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        source_transaction_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    if not split_bill or split_bill.get("status") != "unpaid":
        # Return None to the caller.
        return None

    person_names = split_bill.get("person_names") or [split_bill.get("person_name")]
    person_names = [str(p).strip().title() for p in person_names if str(p or "").strip()]
    person_shares = split_bill.get("person_shares") or {}
    fallback_share = float(split_bill.get("base_share_amount", split_bill.get("share_amount", 0)) or 0)

    # Handle the missing or empty person_names case.
    if not person_names:
        # Return None to the caller.
        return None

    desc = f"Split bill: {parsed.get('description') or raw or '-'}"
    # Prepare created for the next step.
    created = []
    # Prepare failed for the next step.
    failed = []

    # Process each person in the current collection.
    for person in person_names:
        # Prepare share amount for the next step.
        share_amount = float(person_shares.get(person, fallback_share) or 0)
        # Handle the case where share_amount <= 0.
        if share_amount <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Open a multi-line structure for the values below.
        result = add_debt(
            "receivable",
            # Include this value in the surrounding collection or call.
            person,
            # Include this value in the surrounding collection or call.
            share_amount,
            # Include this value in the surrounding collection or call.
            desc,
            # Prepare source transaction id for the next step.
            source_transaction_id=source_transaction_id,
            cashflow_mode="debt_only",
            fronting_mode="split_bill",
        # Close the structure that was opened above.
        )
        if result and result.get("success"):
            # Open a multi-line structure for the values below.
            created.append({
                "person_name": person,
                "remaining": share_amount,
                "debt_id": result.get("debt_id"),
            # Close the structure that was opened above.
            })
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Open a multi-line structure for the values below.
            failed.append({
                "person_name": person,
                "message": (result or {}).get("message", "Gagal membuat piutang."),
            # Close the structure that was opened above.
            })

    # Handle the case where failed and not created.
    if failed and not created:
        # Return { to the caller.
        return {
            "success": False,
            "message": "; ".join(f"{x['person_name']}: {x['message']}" for x in failed),
            "created": created,
            "failed": failed,
        # Close the structure that was opened above.
        }

    # Return { to the caller.
    return {
        "success": True,
        "person_name": ", ".join(x["person_name"] for x in created),
        "remaining": sum(float(x["remaining"] or 0) for x in created),
        "created": created,
        "failed": failed,
        "message": "ok" if not failed else "; ".join(f"{x['person_name']}: {x['message']}" for x in failed),
    # Close the structure that was opened above.
    }


# Define format split debt result lines for callers in this flow.
def format_split_debt_result_lines(debt_result: dict) -> list[str]:
    """Format data into a readable display for split debt result lines."""
    # Prepare lines for the next step.
    lines = []
    for item in (debt_result or {}).get("created", []) or []:
        # Open a multi-line structure for the values below.
        lines.append(
            f"• {md_safe(item.get('person_name'))}: *{format_rupiah(float(item.get('remaining', 0) or 0))}*"
        # Close the structure that was opened above.
        )
    # Return lines to the caller.
    return lines


# Define summarize saved transaction items for callers in this flow.
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
    # Prepare total expense for the next step.
    total_expense = 0.0
    # Prepare total income for the next step.
    total_income = 0.0
    # Prepare total transfer for the next step.
    total_transfer = 0.0
    # Process each item in the current collection.
    for item in items or []:
        parsed = item.get("parsed", {})
        amount = _receipt_amount(parsed.get("amount"), 0)
        if parsed.get("type") == "expense":
            # Run this statement as part of the current workflow.
            total_expense += amount
        elif parsed.get("type") == "income":
            # Run this statement as part of the current workflow.
            total_income += amount
        elif parsed.get("type") == "transfer":
            # Run this statement as part of the current workflow.
            total_transfer += amount
    # Return { to the caller.
    return {
        "expense": total_expense,
        "income": total_income,
        "transfer": total_transfer,
        "net": total_income - total_expense,
    # Close the structure that was opened above.
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
    # Prepare summary for the next step.
    summary = summarize_saved_transaction_items(items)
    lines.append(f"\n📊 *{title}:*")
    lines.append(f"❌ Pengeluaran: *{format_rupiah(summary['expense'])}*")
    lines.append(f"✅ Pemasukan : *{format_rupiah(summary['income'])}*")
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
    # Handle the case where person.
    if person:
        item = re.sub(rf"\b(?:sama|oleh|ke|dari)?\s*(?:si\s+)?{re.escape(person)}\b", " ", item, flags=re.IGNORECASE)
    item = re.sub(r"\b(?:tanggal|tgl|kemarin|hari\s+ini|besok|bulan\s+depan|minggu\s+depan)\b.*$", " ", item, flags=re.IGNORECASE)
    item = re.sub(r"\b(?:rp|idr)?\s*\d+[\d.,]*\s*(?:rb|ribu|k|jt|juta)?(?:\s*/\s*\d+)?\b", " ", item, flags=re.IGNORECASE)
    # Prepare item for the next step.
    item = strip_split_bill_phrase(item)
    # Legacy compatibility note for older records or older in-memory state.
    # Clean leftover split-bill phrases so subject and description stay readable.
    # "Minyak Dibagi", "Minyak Dibagi Fajar Raka", "Minyak Dibagi Sama Fajar Raka".
    item = re.sub(r"\b(?:di\s*-?\s*bagi|dibagi|bagi|split|share|patungan)\b.*$", " ", item, flags=re.IGNORECASE)
    item = re.sub(r"^\s*(?:beli|bayar|byr|jajan|makan|minum)\b", " ", item, flags=re.IGNORECASE)
    item = re.sub(r"\s+", " ", item).strip(" .,-:")
    return item.title() if item else ""


# Define fronting expense description for callers in this flow.
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
        # Handle the case where item.
        if item:
            # Return item to the caller.
            return item

    raw = str(debt_parsed.get("raw_input") or "").strip()

    item = re.sub(r"\b(?:saya|aku|gw|gue)?\s*(?:nitip|ditalangin|ditalangi|dibayarin|duluin)\b", " ", raw, flags=re.IGNORECASE)
    # Prepare item for the next step.
    item = _clean_fronting_item_text(item, person)
    return item if item else (description or "Ditalangin")


# Define fronting expense category for callers in this flow.
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
    # Handle the case where raw.
    if raw:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare parsed for the next step.
            parsed = parse_with_regex(raw)
            category = str((parsed or {}).get("category") or "").strip()
            txn_type = str((parsed or {}).get("type") or "").strip().lower()
            if txn_type == "expense" and category:
                # Return category to the caller.
                return category
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass
    return str(debt_parsed.get("category") or "Other Expense").strip() or "Other Expense"


# Define is ditalangin expense without balance for callers in this flow.
def is_ditalangin_expense_without_balance(debt_parsed: dict) -> bool:
    """Check whether a condition is true for ditalangin expense without balance."""
    # Return ( to the caller.
    return (
        str(debt_parsed.get("cashflow_mode") or "").strip() == "debt_only"
        and str(debt_parsed.get("fronting_mode") or "").strip().lower() == "ditalangin"
        and str(debt_parsed.get("intent") or "").strip() == "add_payable"
    # Close the structure that was opened above.
    )


# Define normalize slash split syntax for callers in this flow.
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
    # Return re.sub( to the caller.
    return re.sub(
        r"(\d+[\d.,]*\s*(?:rb|ribu|k|jt|juta)?)\s*/\s*(\d+)",
        r"\1 dibagi \2",
        # Include this value in the surrounding collection or call.
        text,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )


# Define enrich ditalangin split bill if any for callers in this flow.
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
    # Handle the missing or empty isinstance(debt_parsed, dict) or not is_ditalangin_expense_wi... case.
    if not isinstance(debt_parsed, dict) or not is_ditalangin_expense_without_balance(debt_parsed):
        # Return debt_parsed to the caller.
        return debt_parsed

    raw_text = str(raw or debt_parsed.get("raw_input") or "")
    # Handle the missing or empty raw_text case.
    if not raw_text:
        # Return debt_parsed to the caller.
        return debt_parsed

    amount = float(debt_parsed.get("amount") or 0)
    # Handle the case where amount <= 0.
    if amount <= 0:
        # Return debt_parsed to the caller.
        return debt_parsed

    # Prepare item desc for the next step.
    item_desc = _fronting_expense_description(debt_parsed)
    # Open a multi-line structure for the values below.
    temp_parsed = {
        "type": "expense",
        "amount": amount,
        "category": _fronting_expense_category(debt_parsed),
        "subject": item_desc,
        "description": item_desc,
    # Close the structure that was opened above.
    }

    # Prepare split bill for the next step.
    split_bill = detect_split_bill(temp_parsed, normalize_slash_split_syntax(raw_text))
    # Handle the missing or empty split_bill case.
    if not split_bill:
        # Return debt_parsed to the caller.
        return debt_parsed

    user_share = float(split_bill.get("user_share_amount", 0) or 0)
    total_amount = float(split_bill.get("total_amount", amount) or amount)
    participants = int(split_bill.get("participants", 0) or 0)

    # Handle the case where user_share <= 0 and participants > 0.
    if user_share <= 0 and participants > 0:
        # Prepare user share for the next step.
        user_share = total_amount / participants
    # Handle the case where user_share <= 0.
    if user_share <= 0:
        # Return debt_parsed to the caller.
        return debt_parsed

    person_shares = split_bill.get("person_shares") or {}
    total_receivable = float(split_bill.get("total_receivable", 0) or 0)

    # Prepare updated for the next step.
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
    # Return updated to the caller.
    return updated


# Define debt payment catatan for callers in this flow.
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
    # Prepare alloc parts for the next step.
    alloc_parts = []
    # Process each item in the current collection.
    for item in allocations:
        debt_id = str(item.get("debt_id") or "").strip()
        amount = item.get("amount")
        # Handle the case where debt_id and amount is not None.
        if debt_id and amount is not None:
            alloc_parts.append(f"{debt_id}:{float(amount)}")
    # Handle the case where alloc_parts.
    if alloc_parts:
        parts.append("debt_allocations=" + ";".join(alloc_parts))
    if debt_parsed.get("net_settlement"):
        parts.append("net_settle=1")
    overpayment = float(debt_parsed.get("overpayment", 0) or 0)
    # Handle the case where overpayment > 0.
    if overpayment > 0:
        parts.append(f"overpayment={overpayment}")
        if debt_parsed.get("overpayment_policy"):
            parts.append(f"overpayment_policy={debt_parsed.get('overpayment_policy')}")
        if debt_parsed.get("overpayment_debt_id"):
            parts.append(f"overpayment_debt_id={debt_parsed.get('overpayment_debt_id')}")
    return " | ".join([p for p in parts if p]).strip(" |")


# Define build debt cashflow transaction for callers in this flow.
def build_debt_cashflow_transaction(
    # Include this value in the surrounding collection or call.
    debt_parsed: dict,
    # Include this value in the surrounding collection or call.
    account: str,
    # Include this value in the surrounding collection or call.
    debt_type_for_payment: str | None = None,
# Close the structure that was opened above.
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
    transaction_date = debt_parsed.get("date") or datetime.now().strftime("%Y-%m-%d")
    hutang_id = debt_parsed.get("hutang_id") or debt_parsed.get("debt_id") or debt_parsed.get("target_debt_id") or ""
    tipe_hutang = debt_parsed.get("tipe_hutang") or ""
    # Handle the missing or empty tipe_hutang case.
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
                # Open a multi-line structure for the values below.
                catatan_parts.append(
                    f"gross dibayarkan orang lain {format_rupiah(debt_parsed.get('fronted_gross_amount', amount))}; "
                    f"bagian user {format_rupiah(debt_parsed.get('fronted_user_share', amount))}; "
                    f"piutang teman {format_rupiah(debt_parsed.get('fronted_total_receivable', 0))}"
                # Close the structure that was opened above.
                )
            # Return { to the caller.
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
            # Close the structure that was opened above.
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
        # Handle the fallback path after earlier conditions are skipped.
        else:
            category = "Debt Tanpa Ubah Saldo"
            description = debt_parsed.get("description") or raw

        # Return { to the caller.
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
        # Close the structure that was opened above.
        }

    if intent == "add_receivable":
        # Return { to the caller.
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
        # Close the structure that was opened above.
        }

    if intent == "add_payable":
        # Return { to the caller.
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
        # Close the structure that was opened above.
        }

    if intent == "add_payment":
        if debt_type_for_payment == "payable":
            # Return { to the caller.
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
            # Close the structure that was opened above.
            }

        if debt_type_for_payment == "receivable":
            # Return { to the caller.
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
            # Close the structure that was opened above.
            }

    if intent == "offset_debt":
        target_label = "piutang" if debt_parsed.get("target_debt_type") == "receivable" else "utang"
        # Return { to the caller.
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
        # Close the structure that was opened above.
        }

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }


# Define debt uses cashflow for callers in this flow.
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


# Define build debt only confirm preview for callers in this flow.
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
        # Handle the case where is_ditalangin_expense_without_balance(debt_parsed).
        if is_ditalangin_expense_without_balance(debt_parsed):
            title = "🟠 *Ditalangin / Pengeluaran Ditanggung Dulu*"
            if debt_parsed.get("fronted_split_bill"):
                split_people = debt_parsed.get("fronted_split_people") or []
                people_text = ", ".join(str(x) for x in split_people if str(x).strip()) or "-"
                # Open a multi-line structure for the values below.
                debt_effect = (
                    f"Anda punya utang ke {md_safe(person)} sebesar *gross yang ditalangi*: "
                    f"{format_rupiah(debt_parsed.get('fronted_gross_amount', amount))}.\n"
                    f"Bagian Anda dalam PTPT: {format_rupiah(debt_parsed.get('fronted_user_share', 0))}."
                # Close the structure that was opened above.
                )
                # Open a multi-line structure for the values below.
                transaction_effect = (
                    "Dicatat sebagai *pengeluaran gross* di sheet transactions agar PTPT bulanan tetap penuh.\n"
                    f"Piutang share dibuat ke: {md_safe(people_text)} dengan total "
                    f"{format_rupiah(debt_parsed.get('fronted_total_receivable', 0))}.\n"
                    "Saldo rekening *tidak berubah* karena uang belum keluar dari rekening Anda."
                # Close the structure that was opened above.
                )
            # Handle the fallback path after earlier conditions are skipped.
            else:
                debt_effect = f"Anda punya utang ke {md_safe(person)}."
                # Open a multi-line structure for the values below.
                transaction_effect = (
                    "Dicatat sebagai *pengeluaran* di sheet transactions agar masuk /harian, /mingguan, /bulanan, dan /budget.\n"
                    "Saldo rekening *tidak berubah* karena uang belum keluar dari rekening Anda."
                # Close the structure that was opened above.
                )
        # Handle the fallback path after earlier conditions are skipped.
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
    # Handle the fallback path after earlier conditions are skipped.
    else:
        title = "💸 *Debt Tanpa Ubah Saldo*"
        debt_effect = "Debt dicatat tanpa transaksi kas."
        transaction_effect = "Tetap dicatat di sheet transactions sebagai fact table, tetapi saldo rekening tidak berubah."

    # Return ( to the caller.
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
    # Close the structure that was opened above.
    )


# Define build debt initial preview for callers in this flow.
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
    # Handle the fallback path after earlier conditions are skipped.
    else:
        title = "💸 *Preview Debt*"
        effect = "Input debt terdeteksi."

    if debt_uses_cashflow(debt_parsed) and intent != "offset_debt":
        next_step = "Jika lanjut, bot akan meminta rekening cashflow sebelum konfirmasi simpan."
    # Handle the fallback path after earlier conditions are skipped.
    else:
        next_step = "Jika lanjut, bot akan menampilkan konfirmasi simpan tanpa mengubah saldo rekening."

    # Open a multi-line structure for the values below.
    lines = [
        # Include this value in the surrounding collection or call.
        title,
        "",
        f"👤 Subjek : {md_safe(person)}",
        f"💰 Nominal: {format_rupiah(amount)}",
        f"📅 Tanggal: {md_safe(date)}",
        f"📝 Detail : {md_safe(description)}",
        f"🧾 Input  : `{md_safe(raw)}`",
        "",
        "*Efek debt:*",
        # Include this value in the surrounding collection or call.
        effect,
    # Close the structure that was opened above.
    ]
    # Handle the case where fronting_mode.
    if fronting_mode:
        lines.append(f"Mode: `{md_safe(fronting_mode)}`")
    # Open a multi-line structure for the values below.
    lines.extend([
        "",
        f"ℹ️ {next_step}",
        "",
        "Data ini *belum disimpan*.",
    # Close the structure that was opened above.
    ])
    return "\n".join(lines)


# Define build debt short summary for callers in this flow.
def build_debt_short_summary(debt_parsed: dict) -> str:
    """Build the data structure or message text for debt short summary."""
    intent = debt_parsed.get("intent") or "debt"
    person = md_safe(debt_parsed.get("person_name") or "-")
    amount = float(debt_parsed.get("amount", 0) or 0)
    description = md_safe(debt_parsed.get("description") or "-")
    account = md_safe(debt_parsed.get("account") or "-")

    # Open a multi-line structure for the values below.
    labels = {
        "add_payable": "Utang baru",
        "add_receivable": "Piutang baru",
        "add_payment": "Pembayaran debt",
        "offset_debt": "Kompensasi debt",
    # Close the structure that was opened above.
    }
    lines = ["💸 *Ringkasan debt:*"]
    lines.append(f"• Jenis: *{md_safe(labels.get(intent, intent))}*")
    lines.append(f"• Subjek: *{person}*")
    lines.append(f"• Nominal: *{format_rupiah(amount)}*")
    lines.append(f"• Detail: {description}")
    if account != "-":
        lines.append(f"• Rekening: *{account}*")
    return "\n".join(lines)

# Define build debt account prompt for callers in this flow.
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

    # Handle the fallback path after earlier conditions are skipped.
    else:
        title = "❓ *Debt*"
        desc = "Input debt terdeteksi."
        effect = "-"

    # Return ( to the caller.
    return (
        f"{title}\n\n"
        f"👤 Subjek : {md_safe(person)}\n"
        f"💰 Nominal: {format_rupiah(amount)}\n"
        f"📝 Detail : {desc}\n"
        f"📌 Efek  : {effect}\n\n"
        f"💳 Pilih rekening cashflow, atau pilih *Sudah berlalu* jika hanya ingin mencatat debt tanpa mengubah saldo:"
    # Close the structure that was opened above.
    )

# Define build debt confirm preview for callers in this flow.
def build_debt_confirm_preview(
    # Include this value in the surrounding collection or call.
    debt_parsed: dict,
    # Include this value in the surrounding collection or call.
    account: str,
    # Include this value in the surrounding collection or call.
    debt_type_for_payment: str | None = None,
# Close the structure that was opened above.
) -> str:
    """Build the data structure or message text for debt confirm preview."""
    # Open a multi-line structure for the values below.
    transaction_parsed = build_debt_cashflow_transaction(
        # Include this value in the surrounding collection or call.
        debt_parsed,
        # Include this value in the surrounding collection or call.
        account,
        # Prepare debt type for payment for the next step.
        debt_type_for_payment=debt_type_for_payment,
    # Close the structure that was opened above.
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
    # Handle the fallback path after earlier conditions are skipped.
    else:
        title = "❓ *Debt*"
        debt_effect = "-"

    # Open a multi-line structure for the values below.
    cashflow_type = {
        "expense": "❌ Pengeluaran",
        "income": "✅ Cash In / Pemasukan",
        "transfer": "🔄 Transfer",
        "debt_offset": "🔁 Debt Offset / Tanpa Rekening",
        "debt_only": "📝 Debt Fact / Tanpa Rekening",
    }.get(transaction_parsed.get("type"), "❓")
    if transaction_parsed.get("type") == "expense" and transaction_parsed.get("skip_account"):
        cashflow_type = "❌ Pengeluaran / tanpa update saldo rekening"

    # Return ( to the caller.
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
    # Close the structure that was opened above.
    )

# Define build debt batch confirm preview for callers in this flow.
def build_debt_batch_confirm_preview(
    # Include this value in the surrounding collection or call.
    debt_items: list[dict],
    # Include this value in the surrounding collection or call.
    account: str,
# Close the structure that was opened above.
) -> str:
    """Build the data structure or message text for debt batch confirm preview."""
    lines = ["🧾 *Preview Batch Utang/Piutang*\n"]

    # Prepare total cash in for the next step.
    total_cash_in = 0
    # Prepare total cash out for the next step.
    total_cash_out = 0

    # Process each i, item in the current collection.
    for i, item in enumerate(debt_items, 1):
        parsed = item["parsed"]
        intent = parsed.get("intent")
        person = parsed.get("person_name") or "-"
        amount = _receipt_amount(parsed.get("amount"), 0)
        raw = item.get("raw") or parsed.get("raw_input") or "-"

        debt_type_for_payment = parsed.get("debt_type_for_payment")
        # Open a multi-line structure for the values below.
        transaction_parsed = build_debt_cashflow_transaction(
            # Include this value in the surrounding collection or call.
            parsed,
            # Include this value in the surrounding collection or call.
            account,
            # Prepare debt type for payment for the next step.
            debt_type_for_payment=debt_type_for_payment,
        # Close the structure that was opened above.
        )

        txn_type = transaction_parsed.get("type")
        category = transaction_parsed.get("category") or "-"

        if txn_type == "income":
            cashflow_label = "✅ Cash In"
            # Run this statement as part of the current workflow.
            total_cash_in += amount
        elif txn_type == "expense":
            if transaction_parsed.get("skip_account"):
                cashflow_label = "❌ Expense fact / tanpa update saldo"
            # Handle the fallback path after earlier conditions are skipped.
            else:
                cashflow_label = "❌ Cash Out"
                # Run this statement as part of the current workflow.
                total_cash_out += amount
        elif txn_type == "debt_offset":
            cashflow_label = "🔁 Debt Offset / tanpa rekening"
        elif txn_type == "debt_only":
            cashflow_label = "📝 Debt fact / tanpa rekening"
        # Handle the fallback path after earlier conditions are skipped.
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
        # Handle the fallback path after earlier conditions are skipped.
        else:
            debt_label = "❓ Debt"

        # Open a multi-line structure for the values below.
        lines.append(
            f"{i}. {debt_label}\n"
            f"   👤 Subjek : {person}\n"
            f"   💰 Nominal: {format_rupiah(amount)}\n"
            f"   🏦 Rekening: {account}\n"
            f"   📁 Kategori: {category}\n"
            f"   📌 Efek: {cashflow_label}\n"
            f"   📝 Input: `{raw}`"
        # Close the structure that was opened above.
        )

    lines.append("\n*Ringkasan Cashflow:*")
    lines.append(f"✅ Total Cash In : *{format_rupiah(total_cash_in)}*")
    lines.append(f"❌ Total Cash Out: *{format_rupiah(total_cash_out)}*")
    lines.append("\nSimpan semua utang/piutang ini?")

    return "\n".join(lines)

# Define build debt batch account prompt for callers in this flow.
def build_debt_batch_account_prompt(debt_items: list[dict]) -> str:
    """Build the data structure or message text for debt batch account prompt."""
    lines = [f"🧾 *Ditemukan {len(debt_items)} input utang/piutang:*\n"]

    # Prepare total cash in for the next step.
    total_cash_in = 0
    # Prepare total cash out for the next step.
    total_cash_out = 0

    # Process each i, item in the current collection.
    for i, item in enumerate(debt_items, 1):
        parsed = item["parsed"]
        intent = parsed.get("intent")
        person = parsed.get("person_name") or "-"
        amount = _receipt_amount(parsed.get("amount"), 0)

        if intent == "add_receivable":
            label = "🟢 Piutang Baru"
            effect = "cash out"
            # Run this statement as part of the current workflow.
            total_cash_out += amount

        elif intent == "add_payable":
            label = "🔴 Utang Baru"
            effect = "cash in"
            # Run this statement as part of the current workflow.
            total_cash_in += amount

        elif intent == "add_payment":
            label = "💸 Pembayaran"
            effect = "mengikuti posisi debt aktif"

        elif intent == "offset_debt":
            label = "🔁 Kompensasi Debt"
            effect = "tanpa rekening, tetap masuk transactions"

        # Handle the fallback path after earlier conditions are skipped.
        else:
            label = "❓ Debt"
            effect = "-"

        # Open a multi-line structure for the values below.
        lines.append(
            f"{i}. {label}\n"
            f"   👤 {person}\n"
            f"   💰 {format_rupiah(amount)}\n"
            f"   📌 {effect}"
        # Close the structure that was opened above.
        )

    # Keep this section separated from the surrounding flow.
    lines.append("\n*Estimasi cashflow awal:*")
    # Keep this section separated from the surrounding flow.
    lines.append(f"✅ Cash In : *{format_rupiah(total_cash_in)}*")
    # Keep this section separated from the surrounding flow.
    lines.append(f"❌ Cash Out: *{format_rupiah(total_cash_out)}*")
    # Keep this section separated from the surrounding flow.
    lines.append("\n💳 Pilih rekening cashflow untuk semua item, atau pilih *Sudah berlalu* jika hanya ingin mencatat debt tanpa mengubah saldo:")

    # Keep this section separated from the surrounding flow.
    return "\n".join(lines)


# ── Command Handlers ──────────────────────────────────────────────────────────

