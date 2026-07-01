# Dipisah dari app/bot/handlers.py agar file utama tidak terlalu besar.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *

from app.bot.handler_parts.networth_assets import build_asset_added_text
from app.bot.handler_parts.command_router import short_txn_id
from app.bot.handler_parts.transaction_flow import (
    append_saved_summary_lines,
    apply_split_bill_decision_to_current_mixed,
    apply_split_bill_decision_to_mixed_index,
    apply_split_bill_decision_to_parsed,
    attach_split_bill_if_any,
    build_batch_preview,
    build_debt_batch_confirm_preview,
    build_debt_cashflow_transaction,
    build_debt_confirm_preview,
    build_debt_account_prompt,
    build_debt_initial_preview,
    build_mixed_edit_choose_prompt,
    build_mixed_preview,
    build_mixed_short_summary,
    build_mixed_split_bill_queue_prompt,
    build_preview,
    build_preview_edit_help,
    build_single_short_summary,
    build_split_bill_prompt_from_parsed,
    create_split_bill_debt,
    debt_uses_cashflow,
    edit_or_continue_keyboard,
    format_split_debt_result_lines,
    mixed_split_bill_keyboard,
    mixed_split_bill_needs_decision,
    needs_account,
    proceed_after_preview_edit,
    split_bill_keyboard,
    split_bill_needs_decision,
    build_debt_only_confirm_preview,
)
from app.nlp.parse_safety import extract_person_candidate
from app.nlp.regex_parser import detect_category
from app.nlp.normalizer import normalize_text


def is_skip_account_choice(account: str) -> bool:
    return str(account or "").strip() == SKIP_ACCOUNT_CALLBACK_VALUE


def mark_transaction_as_historical(parsed: dict) -> dict:
    """Catat transaksi tanpa mengubah saldo rekening."""
    parsed["skip_account"] = True
    parsed["account"] = SKIP_ACCOUNT_NAME
    parsed["catatan"] = (str(parsed.get("catatan") or "").strip() + " | sudah berlalu/tanpa update saldo").strip(" |")
    return parsed


def mark_debt_as_historical(debt_parsed: dict) -> dict:
    """Catat debt tanpa membuat cashflow transaksi."""
    debt_parsed["cashflow_mode"] = "debt_only"
    debt_parsed["fronting_mode"] = debt_parsed.get("fronting_mode") or "sudah_berlalu"
    debt_parsed["account"] = SKIP_ACCOUNT_NAME
    debt_parsed["catatan"] = (str(debt_parsed.get("catatan") or "").strip() + " | sudah berlalu/tanpa update saldo").strip(" |")
    return debt_parsed


def _split_debt_id_text(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = str(value).split(",")
    seen = set()
    result = []
    for item in raw_items:
        debt_id = str(item or "").strip()
        if debt_id and debt_id not in seen:
            result.append(debt_id)
            seen.add(debt_id)
    return result


def _merge_debt_ids(*values) -> str:
    merged = []
    seen = set()
    for value in values:
        for debt_id in _split_debt_id_text(value):
            if debt_id not in seen:
                merged.append(debt_id)
                seen.add(debt_id)
    return ", ".join(merged)


def create_fronted_split_receivable_debts(debt_parsed: dict) -> dict:
    """
    Untuk kasus PTPT: user ditalangin full oleh seseorang, tetapi itemnya
    dibagi lagi. Main debt tetap payable full ke penalang; helper ini membuat
    receivable share ke daftar teman yang disebut pada split bill.
    """
    if not debt_parsed or debt_parsed.get("intent") != "add_payable":
        return {"created": [], "failed": []}

    split_bill = debt_parsed.get("fronted_split_bill") or {}
    if not split_bill:
        return {"created": [], "failed": []}

    person_shares = split_bill.get("person_shares") or debt_parsed.get("fronted_person_shares") or {}
    if not person_shares:
        return {"created": [], "failed": []}

    payer = str(debt_parsed.get("person_name") or "").strip()
    item_desc = str(debt_parsed.get("expense_description") or debt_parsed.get("description") or "Ditalangin").strip()
    description = f"Split bill ditalangin {payer}: {item_desc}" if payer else f"Split bill ditalangin: {item_desc}"

    created = []
    failed = []
    for person, share in person_shares.items():
        person_name = str(person or "").strip()
        try:
            amount = float(share or 0)
        except Exception:
            amount = 0.0
        if not person_name or amount <= 0:
            continue

        result = add_debt(
            "receivable",
            person_name,
            amount,
            description,
            cashflow_mode="debt_only",
            fronting_mode="ditalangin_split_share",
        )
        if result and result.get("success"):
            created.append({
                "person_name": result.get("person_name", person_name),
                "amount": amount,
                "debt_id": result.get("debt_id"),
            })
        else:
            failed.append({
                "person_name": person_name,
                "amount": amount,
                "message": result.get("message") if result else "Unknown error",
            })

    return {"created": created, "failed": failed}


def attach_fronted_split_debt_relations(debt_parsed: dict, debt_result: dict, split_result: dict) -> dict:
    primary_id = debt_result.get("debt_id") if debt_result else ""
    receivable_ids = [x.get("debt_id") for x in (split_result or {}).get("created", []) if x.get("debt_id")]
    debt_parsed["hutang_id"] = _merge_debt_ids(debt_parsed.get("hutang_id"), primary_id, receivable_ids)
    if receivable_ids and primary_id:
        debt_parsed["tipe_hutang"] = "utang,piutang"
    elif primary_id and (debt_result or {}).get("type") == "payable":
        debt_parsed["tipe_hutang"] = "utang"
    elif primary_id and (debt_result or {}).get("type") == "receivable":
        debt_parsed["tipe_hutang"] = "piutang"
    return debt_parsed


def append_fronted_split_result_lines(lines: list[str], split_result: dict, *, indent: str = "") -> None:
    created = (split_result or {}).get("created", [])
    failed = (split_result or {}).get("failed", [])
    if created:
        total = sum(float(x.get("amount", 0) or 0) for x in created)
        detail = ", ".join(
            f"{x.get('person_name')}: {format_rupiah(x.get('amount', 0))}"
            for x in created
        )
        lines.append(f"{indent}🤝 Piutang PTPT dibuat: *{format_rupiah(total)}* ({md_safe(detail)})")
    for item in failed:
        lines.append(
            f"{indent}⚠️ Piutang PTPT gagal untuk {md_safe(item.get('person_name'))}: "
            f"{md_safe(item.get('message'))}"
        )



def build_edit_txn_preview_text_for_callback(preview: dict, split_parsed: dict | None = None) -> str:
    """Preview edit transaksi untuk alur split bill di callback_handler."""
    old_txn = preview.get("old_txn", {}) or {}
    new_txn = preview.get("new_txn", {}) or {}
    updates = preview.get("updates", {}) or {}
    net_deltas = preview.get("net_deltas", {}) or {}

    lines = ["✏️ *Preview Edit Transaksi*\n"]
    lines.append("*Sebelum:*")
    lines.append(
        f"• {old_txn.get('date')} — *{md_safe(old_txn.get('description') or '-')}*\n"
        f"  {format_rupiah(float(old_txn.get('amount', 0) or 0))} | "
        f"{md_safe(old_txn.get('category') or '-')} | {md_safe(old_txn.get('account') or '-')}"
    )

    lines.append("\n*Sesudah:*")
    lines.append(
        f"• {new_txn.get('date')} — *{md_safe(new_txn.get('description') or '-')}*\n"
        f"  {format_rupiah(float(new_txn.get('amount', 0) or 0))} | "
        f"{md_safe(new_txn.get('category') or '-')} | {md_safe(new_txn.get('account') or '-')}"
    )

    if updates:
        lines.append("\n*Field yang diubah:*")
        for field, value in updates.items():
            lines.append(f"• {md_safe(field)}: `{md_code_text(value)}`")

    split_bill = (split_parsed or {}).get("split_bill") or {}
    if split_bill:
        total_receivable = float(split_bill.get("total_receivable", 0) or 0)
        if split_bill.get("status") == "unpaid":
            lines.append(
                f"\n🤝 *Split bill:* belum dibayar, piutang baru akan dibuat sebesar *{format_rupiah(total_receivable)}*."
            )
        elif split_bill.get("status") == "paid":
            lines.append("\n🤝 *Split bill:* sudah dibayar, tidak membuat piutang baru.")

    if net_deltas:
        lines.append("\n*Efek ke saldo:*")
        for account, delta in net_deltas.items():
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {md_safe(account)}: {sign}{format_rupiah(abs(delta))}")
    else:
        lines.append("\n*Efek ke saldo:*\n• Tidak ada perubahan saldo")

    lines.append("\nSimpan perubahan ini?")
    return "\n".join(lines)


def parse_debt_ids_from_txn_record_for_edit(txn: dict) -> list[str]:
    raw = str((txn or {}).get("hutang_id", "") or "").strip()
    if not raw:
        return []
    return [part.strip() for part in re.split(r"[,;\s]+", raw) if part.strip()]


def overpayment_decision_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Anggap lunas / bonus", callback_data="debt_overpay:bonus")],
        [InlineKeyboardButton("🔴 Catat sebagai hutang saya", callback_data="debt_overpay:opposite_debt")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:debt")],
    ])


def build_overpayment_decision_text(parsed: dict, outcome: dict) -> str:
    person = parsed.get("person_name") or outcome.get("person_name") or "-"
    target_type = outcome.get("target_debt_type")
    target_label = "piutang" if target_type == "receivable" else "utang Anda"
    opposite_label = "utang Anda" if target_type == "receivable" else "piutang"
    overpaid = float(outcome.get("overpayment", 0) or 0)
    lines = [
        "⚠️ *Pembayaran melebihi saldo net debt aktif*\n",
        f"👤 Subjek: *{md_safe(person)}*",
        f"💰 Nominal input: *{format_rupiah(outcome.get('amount', 0))}*",
        f"📌 Sisa {target_label} sebelum bayar: *{format_rupiah(outcome.get('target_remaining_before', 0))}*",
        f"📌 Sisa {opposite_label} sebelum bayar: *{format_rupiah(outcome.get('opposite_remaining_before', 0))}*",
        f"📊 Saldo net yang perlu dibayar: *{format_rupiah(outcome.get('net_payment_capacity', 0))}*",
        f"➕ Kelebihan bayar: *{format_rupiah(overpaid)}*",
        "",
        "Pilih perlakuan untuk uang lebihnya:",
        "1. *Anggap lunas/bonus* → debt lama ditutup, kelebihan tidak jadi hutang baru.",
        "2. *Catat sebagai hutang saya* → kelebihan jadi utang Anda ke orang tersebut.",
    ]
    return "\n".join(lines)


def resolve_payment_target_type(parsed: dict, debts: list[dict]) -> tuple[str | None, str | None]:
    """Tentukan arah debt untuk pembayaran by person tanpa memblokir mixed arah.

    Output: (target_type, error_message).
    """
    target = str(parsed.get("target_debt_type") or "").strip().lower()
    if target == "auto":
        target = ""

    debt_types = {str(d.get("type", "")).strip() for d in debts if str(d.get("type", "")).strip()}

    if target not in {"payable", "receivable"}:
        total_payable = sum(
            parse_sheet_number(d.get("remaining_amount", 0))
            for d in debts
            if str(d.get("type", "")).strip() == "payable"
        )
        total_receivable = sum(
            parse_sheet_number(d.get("remaining_amount", 0))
            for d in debts
            if str(d.get("type", "")).strip() == "receivable"
        )

        if total_receivable > total_payable:
            target = "receivable"
        elif total_payable > total_receivable:
            target = "payable"
        elif len(debt_types) == 1:
            target = next(iter(debt_types))
        else:
            return None, "Saldo utang dan piutang sama besar. Pakai input lebih spesifik."

    if not any(str(d.get("type", "")).strip() == target for d in debts):
        label = "utang" if target == "payable" else "piutang"
        return None, f"Tidak ada {label} aktif untuk arah pembayaran ini."

    return target, None


def clear_parse_clarification_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("pending_parse_clarification", None)


def infer_clarified_payment_target_type(raw: str) -> str:
    clean = normalize_text(raw)
    if re.search(r"^\s*(?:saya|aku|gw|gue|gua)\s+(?:bayar|byr)\b", clean):
        return "payable"
    if re.search(r"^\s*(?:bayar|byr)\s+(?:ke\s+)?[a-zA-ZÀ-ÿ]", clean):
        return "payable"
    return "receivable"


def build_clarified_debt_payment(raw: str, parsed: dict | None = None) -> dict | None:
    parsed = parsed or {}
    amount = float(parsed.get("amount") or parse_human_amount(raw) or 0)
    person = extract_person_candidate(raw) or parsed.get("person_name") or parsed.get("subject") or ""
    person = re.sub(r"\s+", " ", str(person or "")).strip().title()
    if not person or amount <= 0:
        return None

    target_type = infer_clarified_payment_target_type(raw)
    label = "Bayar hutang ke" if target_type == "payable" else "Pembayaran piutang dari"
    return {
        "intent": "add_payment",
        "person_name": person,
        "amount": amount,
        "description": f"{label} {person}",
        "date": detect_date(raw),
        "raw_input": raw,
        "target_debt_type": target_type,
    }


def build_expense_candidate_raw(raw: str) -> str:
    clean = str(raw or "").strip()
    # "Budi bayar makan 100k" -> "bayar makan 100k" agar description tidak
    # bocor menjadi "Budi Bayar Makan" saat user memilih expense biasa.
    clean = re.sub(
        r"^\s*(?!saya\b|aku\b|gw\b|gue\b|gua\b)([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{0,30}?)\s+(?:bayar|byr)\s+",
        "bayar ",
        clean,
        flags=re.IGNORECASE,
    )
    return clean


def build_clarified_expense(raw: str, parsed: dict | None = None) -> dict | None:
    parsed = dict(parsed or {})
    expense_raw = build_expense_candidate_raw(raw)
    candidate = parse_with_regex(expense_raw) or parse_with_regex(raw)
    if candidate and candidate.get("type") in {"expense", "income", "transfer"}:
        parsed = dict(candidate)
    else:
        amount = float(parsed.get("amount") or parse_human_amount(raw) or 0)
        if amount <= 0:
            return None
        description = strip_date_phrases(expense_raw)
        description = re.sub(r"\b(?:rp|idr)?\s*\d[\d.,]*\s*(?:rb|ribu|k|jt|juta)?\b", " ", description, flags=re.IGNORECASE)
        description = re.sub(r"\s+", " ", description).strip(" .,-") or "Expense"
        parsed = {
            "type": "expense",
            "amount": amount,
            "category": detect_category(expense_raw, "expense"),
            "account": None,
            "to_account": None,
            "subject": description.title(),
            "description": description.title(),
            "catatan": "",
            "tipe_pengeluaran": "Harian",
            "date": detect_date(raw),
            "parsed_by": "clarification",
        }

    if parsed.get("type") != "expense":
        parsed["type"] = "expense"
        parsed["category"] = detect_category(expense_raw, "expense")
        parsed["to_account"] = None
    parsed["raw_input"] = raw
    parsed["parsed_by"] = parsed.get("parsed_by") or "clarification"
    attach_split_bill_if_any(parsed, raw)
    return parsed


def build_clarified_fronting(raw: str, parsed: dict | None = None) -> dict | None:
    parsed = parsed or {}
    amount = float(parsed.get("amount") or parse_human_amount(raw) or 0)
    person = extract_person_candidate(raw) or parsed.get("person_name") or parsed.get("subject") or ""
    person = re.sub(r"\s+", " ", str(person or "")).strip().title()
    if not person or amount <= 0:
        return None

    desc_source = build_expense_candidate_raw(raw)
    desc_source = strip_date_phrases(desc_source)
    desc_source = re.sub(r"\b(?:rp|idr)?\s*\d[\d.,]*\s*(?:rb|ribu|k|jt|juta)?\b", " ", desc_source, flags=re.IGNORECASE)
    desc_source = re.sub(r"\b(?:bayar|byr|ke|sama)\b", " ", desc_source, flags=re.IGNORECASE)
    desc_source = re.sub(r"\s+", " ", desc_source).strip(" .,-") or "Talangan"

    synthetic = f"talangin {person} buat {desc_source} {int(amount)}"
    debt_parsed = parse_debt_input(synthetic)
    if debt_parsed:
        debt_parsed["raw_input"] = raw
        return debt_parsed

    return {
        "intent": "add_receivable",
        "person_name": person,
        "amount": amount,
        "description": f"Talangin {person}: {desc_source.title()}",
        "date": detect_date(raw),
        "raw_input": raw,
        "cashflow_mode": "cashflow",
        "fronting_mode": "talangin",
    }


# Handler pusat untuk semua tombol inline Telegram.
# callback_data dipakai untuk mengembalikan user ke flow yang tepat tanpa menyimpan data sebelum konfirmasi.

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    query = update.callback_query

    data = query.data or ""
    await show_callback_loading(query)

    if data.startswith("clarify_parse:"):
        choice = data.split(":", 1)[1].strip()
        pending = context.user_data.get("pending_parse_clarification") or {}
        raw = pending.get("raw") or ""
        parsed = pending.get("parsed") or {}

        if not raw:
            clear_parse_clarification_state(context)
            await safe_edit_message(query, "❌ Sesi klarifikasi expired. Coba input ulang.")
            return

        if choice == "rewrite":
            clear_parse_clarification_state(context)
            await safe_edit_message(
                query,
                "✍️ Oke. Silakan tulis ulang inputnya dengan format yang lebih jelas.",
                parse_mode="Markdown",
            )
            return

        if choice == "no_cashflow":
            clear_parse_clarification_state(context)
            await safe_edit_message(
                query,
                "✅ Oke, tidak ada data yang disimpan karena ini dianggap tidak memengaruhi cashflow Anda.",
                parse_mode="Markdown",
            )
            return

        if choice == "debt_payment":
            debt_parsed = build_clarified_debt_payment(raw, parsed)
            if not debt_parsed:
                clear_parse_clarification_state(context)
                await safe_edit_message(
                    query,
                    "❌ Nama orang atau nominal belum kebaca. Silakan tulis ulang inputnya dengan kata hutang/utang/piutang.",
                    parse_mode="Markdown",
                )
                return

            context.user_data["pending_debt"] = debt_parsed
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_mixed", None)
            clear_parse_clarification_state(context)

            await safe_edit_message(
                query,
                f"{build_debt_initial_preview(debt_parsed)}\n\nMau edit dulu atau lanjut ke rekening/simpan?",
                parse_mode="Markdown",
                reply_markup=edit_or_continue_keyboard("debt"),
            )
            return

        if choice == "fronting":
            debt_parsed = build_clarified_fronting(raw, parsed)
            if not debt_parsed:
                clear_parse_clarification_state(context)
                await safe_edit_message(
                    query,
                    "❌ Nama orang atau nominal belum kebaca. Contoh: `saya talangin Budi makan 100k`.",
                    parse_mode="Markdown",
                )
                return

            context.user_data["pending_debt"] = debt_parsed
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_mixed", None)
            clear_parse_clarification_state(context)

            await safe_edit_message(
                query,
                f"{build_debt_initial_preview(debt_parsed)}\n\nMau edit dulu atau lanjut ke rekening/simpan?",
                parse_mode="Markdown",
                reply_markup=edit_or_continue_keyboard("debt"),
            )
            return

        if choice == "expense":
            clarified = build_clarified_expense(raw, parsed)
            if not clarified:
                clear_parse_clarification_state(context)
                await safe_edit_message(
                    query,
                    "❌ Nominal transaksi belum kebaca. Silakan tulis ulang inputnya.",
                    parse_mode="Markdown",
                )
                return

            context.user_data["pending_parsed"] = clarified
            context.user_data["pending_raw"] = raw
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_debt_batch", None)
            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_mixed", None)
            clear_parse_clarification_state(context)

            if split_bill_needs_decision(clarified):
                await safe_edit_message(
                    query,
                    build_split_bill_prompt_from_parsed(clarified),
                    parse_mode="Markdown",
                    reply_markup=split_bill_keyboard("single"),
                )
                return

            await safe_edit_message(
                query,
                f"{build_preview(clarified)}\n\nMau edit dulu atau lanjut ke rekening/simpan?",
                parse_mode="Markdown",
                reply_markup=edit_or_continue_keyboard("single"),
            )
            return

        await safe_edit_message(query, "❌ Pilihan klarifikasi tidak valid.")
        return

    if data.startswith("recurring_paid:"):
        rule_id = data.split(":", 1)[1].strip()
        result = mark_recurring_rule_paid(rule_id)

        if result.get("success"):
            rule = result.get("rule") or {}
            await safe_edit_message(
                query,
                "✅ *Recurring ditandai sudah bayar.*\n\n"
                f"📌 {md_safe(rule.get('name') or '-')}\n"
                f"📝 Transaksi tersimpan: `{result.get('transaction_id')}`\n"
                f"🔕 Notifikasi berikutnya: `{result.get('next_run_date')}`",
                parse_mode="Markdown",
            )
        else:
            await safe_edit_message(
                query,
                f"❌ Gagal menandai recurring sudah bayar.\n\n{md_safe(result.get('message') or '-')}",
                parse_mode="Markdown",
            )
        return

    if data.startswith("editflow:"):
        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        scope = parts[2] if len(parts) > 2 else "single"

        if action == "continue":
            await proceed_after_preview_edit(query, context, scope)
            return

        if action == "edit":
            if scope == "mixed":
                mixed_items = context.user_data.get("pending_mixed")
                if not mixed_items:
                    await safe_edit_message(query, "❌ Sesi mixed input expired. Coba input ulang.")
                    return
                context.user_data["pending_preview_edit"] = {"scope": "mixed", "step": "choose_item"}
                await safe_edit_message(query, 
                    build_mixed_edit_choose_prompt(mixed_items),
                    parse_mode="Markdown",
                )
                return

            if scope == "debt":
                if not context.user_data.get("pending_debt"):
                    await safe_edit_message(query, "❌ Sesi debt expired. Coba input ulang.")
                    return
                context.user_data["pending_preview_edit"] = {"scope": "debt", "step": "edit_item"}
                await safe_edit_message(
                    query,
                    build_preview_edit_help("debt"),
                    parse_mode="Markdown",
                )
                return

            if scope == "pending_expense":
                if not context.user_data.get("pending_expense_confirm"):
                    await safe_edit_message(query, "❌ Sesi pending expense expired. Coba input ulang.")
                    return
                context.user_data["pending_preview_edit"] = {"scope": "pending_expense", "step": "edit_item"}
                await safe_edit_message(
                    query,
                    build_preview_edit_help("pending_expense"),
                    parse_mode="Markdown",
                )
                return

            if scope == "asset":
                if not context.user_data.get("pending_asset_confirm"):
                    await safe_edit_message(query, "❌ Sesi tambah aset expired. Coba input ulang.")
                    return
                context.user_data["pending_preview_edit"] = {"scope": "asset", "step": "edit_item"}
                await safe_edit_message(
                    query,
                    build_preview_edit_help("asset"),
                    parse_mode="Markdown",
                )
                return

            if not context.user_data.get("pending_parsed"):
                await safe_edit_message(query, "❌ Sesi transaksi expired. Coba input ulang.")
                return
            context.user_data["pending_preview_edit"] = {"scope": "single", "step": "edit_item"}
            await safe_edit_message(query, 
                build_preview_edit_help("single"),
                parse_mode="Markdown",
            )
            return

        await safe_edit_message(query, "❌ Aksi edit tidak valid.")
        return

    if data.startswith("debt_overpay:"):
        policy = data.split(":", 1)[1].strip()
        debt_parsed = context.user_data.get("pending_debt")
        if not debt_parsed:
            await safe_edit_message(query, "❌ Sesi overpaid expired. Coba input ulang.")
            return

        if policy not in {"bonus", "opposite_debt"}:
            await safe_edit_message(query, "❌ Pilihan overpaid tidak valid. Coba input ulang.")
            return

        debt_parsed["overpayment_policy"] = policy
        context.user_data["pending_debt"] = debt_parsed

        account = debt_parsed.get("account") or "-"
        preview = build_debt_confirm_preview(
            debt_parsed,
            account,
            debt_type_for_payment=debt_parsed.get("debt_type_for_payment"),
        )
        if policy == "bonus":
            preview += "\n\nℹ️ Kelebihan bayar akan dianggap lunas/bonus, tidak jadi hutang baru."
        else:
            preview += "\n\nℹ️ Kelebihan bayar akan dicatat sebagai hutang Anda ke orang tersebut."

        await safe_edit_message(query, preview, parse_mode="Markdown", reply_markup=confirm_keyboard("debt"))
        return

    if data.startswith("debt_settle_acc:"):
        account = data.split(":", 1)[1].strip()
        payload = context.user_data.get("pending_debt_settle")
        if not payload:
            await safe_edit_message(query, "❌ Sesi debt settle expired. Coba ulangi `/hutang Nama` lalu `/debt_settle ...`.", parse_mode="Markdown")
            return
        payload["account"] = account
        context.user_data["pending_debt_settle"] = payload

        from app.bot.handler_parts.command_handlers import (
            build_selected_debt_settle_preview_text,
            selected_debt_settle_overpay_keyboard,
        )
        if float(payload.get("shortage", 0) or 0) > 0:
            await safe_edit_message(query, build_selected_debt_settle_preview_text(payload), parse_mode="Markdown")
            return
        if float(payload.get("overpayment", 0) or 0) > 0 and not payload.get("overpayment_policy"):
            await safe_edit_message(
                query,
                build_selected_debt_settle_preview_text(payload),
                parse_mode="Markdown",
                reply_markup=selected_debt_settle_overpay_keyboard(),
            )
            return
        await safe_edit_message(
            query,
            build_selected_debt_settle_preview_text(payload),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("debt_settle"),
        )
        return

    if data.startswith("debt_settle_overpay:"):
        policy = data.split(":", 1)[1].strip()
        payload = context.user_data.get("pending_debt_settle")
        if not payload:
            await safe_edit_message(query, "❌ Sesi overpaid debt settle expired. Coba input ulang.")
            return
        if policy not in {"bonus", "opposite_debt"}:
            await safe_edit_message(query, "❌ Pilihan overpaid tidak valid. Coba input ulang.")
            return
        payload["overpayment_policy"] = policy
        context.user_data["pending_debt_settle"] = payload
        from app.bot.handler_parts.command_handlers import build_selected_debt_settle_preview_text
        await safe_edit_message(
            query,
            build_selected_debt_settle_preview_text(payload),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("debt_settle"),
        )
        return


    if data.startswith("debt_batch_acc:"):
        account = data.split(":")[1]
        skip_account = is_skip_account_choice(account)
        account_label = SKIP_ACCOUNT_NAME if skip_account else account
        debt_batch = context.user_data.get("pending_debt_batch")

        if not debt_batch:
            await safe_edit_message(query, "❌ Sesi batch debt expired. Coba input ulang.")
            return

        prepared_batch = []
        failed_items = []

        for item in debt_batch:
            parsed = item["parsed"]
            raw = item["raw"]

            intent = parsed.get("intent")
            person = parsed.get("person_name")

            if not person:
                failed_items.append({
                    "raw": raw,
                    "message": "Nama orang tidak terdeteksi.",
                })
                continue

            if intent == "add_payment":
                debts = get_debt_by_person(person)

                if not debts:
                    failed_items.append({
                        "raw": raw,
                        "message": f"Tidak ada utang/piutang aktif dengan {person}.",
                    })
                    continue

                debt_type_for_payment, err = resolve_payment_target_type(parsed, debts)
                if err:
                    failed_items.append({
                        "raw": raw,
                        "message": err,
                    })
                    continue

                target_debts = [
                    d for d in debts
                    if str(d.get("type", "")).strip() == debt_type_for_payment
                ]
                opposite_type = "payable" if debt_type_for_payment == "receivable" else "receivable"
                has_opposite_debt = any(
                    str(d.get("type", "")).strip() == opposite_type
                    and parse_sheet_number(d.get("remaining_amount", 0)) > 0
                    for d in debts
                )
                parsed["target_debt_id"] = target_debts[0].get("id") if len(target_debts) == 1 and not has_opposite_debt else ""
                parsed["debt_type_for_payment"] = debt_type_for_payment
                parsed["target_debt_type"] = debt_type_for_payment

            if debt_uses_cashflow(parsed) and intent != "offset_debt":
                if skip_account:
                    mark_debt_as_historical(parsed)
                else:
                    parsed["account"] = account
            prepared_batch.append({
                "parsed": parsed,
                "raw": raw,
            })

        if not prepared_batch:
            lines = ["❌ *Batch debt tidak bisa diproses.*\n"]

            if failed_items:
                lines.append("*Gagal:*")
                for item in failed_items:
                    lines.append(f"• `{item['raw']}` — {item['message']}")

            await safe_edit_message(query, 
                "\n".join(lines),
                parse_mode="Markdown",
            )
            context.user_data.pop("pending_debt_batch", None)
            return

        context.user_data["pending_debt_batch"] = prepared_batch

        preview = build_debt_batch_confirm_preview(
            prepared_batch,
            account_label,
        )

        if failed_items:
            preview += "\n\n⚠️ *Catatan item yang tidak masuk preview:*"
            for item in failed_items:
                preview += f"\n• `{item['raw']}` — {item['message']}"

        await safe_edit_message(query, 
            preview,
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("debt_batch"),
        )
        return

    if data.startswith("debt_acc:"):
        account = data.split(":")[1]
        skip_account = is_skip_account_choice(account)
        account_label = SKIP_ACCOUNT_NAME if skip_account else account
        debt_parsed = context.user_data.get("pending_debt")

        if not debt_parsed:
            await safe_edit_message(query, "❌ Sesi debt expired. Coba input ulang.")
            return

        intent = debt_parsed.get("intent")
        person = debt_parsed.get("person_name")
        debt_type_for_payment = None

        if intent == "add_payment":
            debts = get_debt_by_person(person)

            if not debts:
                await safe_edit_message(query, 
                    f"❓ Tidak ada utang/piutang aktif dengan *{person}*.",
                    parse_mode="Markdown",
                )
                context.user_data.pop("pending_debt", None)
                return

            debt_type_for_payment, err = resolve_payment_target_type(debt_parsed, debts)
            if err:
                await safe_edit_message(query, 
                    f"⚠️ {md_safe(err)}\n\n"
                    f"Contoh: `Sapto bayar 5k` untuk mengurangi piutang, atau `saya bayar hutang Sapto 5k` untuk mengurangi utang Anda.",
                    parse_mode="Markdown",
                )
                context.user_data.pop("pending_debt", None)
                return

            target_debts = [
                d for d in debts
                if str(d.get("type", "")).strip() == debt_type_for_payment
            ]
            opposite_type = "payable" if debt_type_for_payment == "receivable" else "receivable"
            has_opposite_debt = any(
                str(d.get("type", "")).strip() == opposite_type
                and parse_sheet_number(d.get("remaining_amount", 0)) > 0
                for d in debts
            )
            # Pembayaran selalu dialokasikan global per orang sesuai arah input.
            # Jangan menargetkan 1 debt langsung, supaya output dan edit/delete pembayaran
            # konsisten sebagai ledger per orang.
            debt_parsed["target_debt_id"] = ""
            debt_parsed["debt_type_for_payment"] = debt_type_for_payment
            debt_parsed["target_debt_type"] = debt_type_for_payment

            outcome = estimate_payment_outcome(person, debt_parsed.get("amount", 0), debt_type_for_payment)
            if float(outcome.get("overpayment", 0) or 0) > 0 and not debt_parsed.get("overpayment_policy"):
                if skip_account:
                    mark_debt_as_historical(debt_parsed)
                else:
                    debt_parsed["account"] = account
                debt_parsed["overpayment_outcome"] = outcome
                context.user_data["pending_debt"] = debt_parsed
                await safe_edit_message(
                    query,
                    build_overpayment_decision_text(debt_parsed, outcome),
                    parse_mode="Markdown",
                    reply_markup=overpayment_decision_keyboard(),
                )
                return

        if skip_account:
            mark_debt_as_historical(debt_parsed)
        else:
            debt_parsed["account"] = account
        context.user_data["pending_debt"] = debt_parsed

        if skip_account:
            preview = build_debt_only_confirm_preview(debt_parsed)
        else:
            preview = build_debt_confirm_preview(
                debt_parsed,
                account_label,
                debt_type_for_payment=debt_type_for_payment,
            )

        await safe_edit_message(query, 
            preview,
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("debt"),
        )
        return

    if data.startswith("mixed_acc:"):
        account = data.split(":")[1]
        skip_account = is_skip_account_choice(account)
        account_label = SKIP_ACCOUNT_NAME if skip_account else account
        mixed_items = context.user_data.get("pending_mixed")

        if not mixed_items:
            await safe_edit_message(query, "❌ Sesi mixed input expired. Coba input ulang.")
            return

        prepared_items = []
        failed_items = []

        for item in mixed_items:
            parsed = item["parsed"]
            raw = item["raw"]

            if item["kind"] == "transaction":
                if needs_account(parsed):
                    if skip_account:
                        mark_transaction_as_historical(parsed)
                    else:
                        parsed["account"] = account

                prepared_items.append({
                    "kind": "transaction",
                    "parsed": parsed,
                    "raw": raw,
                })

            elif item["kind"] == "debt":
                intent = parsed.get("intent")
                person = parsed.get("person_name")

                if not person:
                    failed_items.append({
                        "raw": raw,
                        "message": "Nama orang tidak terdeteksi.",
                    })
                    continue

                if intent == "add_payment":
                    debts = get_debt_by_person(person)

                    if not debts:
                        failed_items.append({
                            "raw": raw,
                            "message": f"Tidak ada utang/piutang aktif dengan {person}.",
                        })
                        continue

                    debt_type_for_payment, err = resolve_payment_target_type(parsed, debts)
                    if err:
                        failed_items.append({
                            "raw": raw,
                            "message": err,
                        })
                        continue

                    target_debts = [
                        d for d in debts
                        if str(d.get("type", "")).strip() == debt_type_for_payment
                    ]
                    opposite_type = "payable" if debt_type_for_payment == "receivable" else "receivable"
                    has_opposite_debt = any(
                        str(d.get("type", "")).strip() == opposite_type
                        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
                        for d in debts
                    )
                    parsed["target_debt_id"] = target_debts[0].get("id") if len(target_debts) == 1 and not has_opposite_debt else ""
                    parsed["debt_type_for_payment"] = debt_type_for_payment
                    parsed["target_debt_type"] = debt_type_for_payment

                if debt_uses_cashflow(parsed) and intent != "offset_debt":
                    if skip_account:
                        mark_debt_as_historical(parsed)
                    else:
                        parsed["account"] = account

                prepared_items.append({
                    "kind": "debt",
                    "parsed": parsed,
                    "raw": raw,
                })

        if not prepared_items:
            lines = ["❌ *Mixed input tidak bisa diproses.*\n"]

            if failed_items:
                lines.append("*Gagal:*")
                for item in failed_items:
                    lines.append(f"• `{item['raw']}` — {item['message']}")

            await safe_edit_message(query, 
                "\n".join(lines),
                parse_mode="Markdown",
            )
            context.user_data.pop("pending_mixed", None)
            return

        context.user_data["pending_mixed"] = prepared_items

        if mixed_split_bill_needs_decision(prepared_items):
            await safe_edit_message(query, 
                build_mixed_split_bill_queue_prompt(prepared_items),
                parse_mode="Markdown",
                reply_markup=mixed_split_bill_keyboard(prepared_items),
            )
            return

        short_summary = build_mixed_short_summary(prepared_items)

        if failed_items:
            short_summary += "\n\n⚠️ *Catatan item yang tidak masuk:*"
            for item in failed_items[:5]:
                short_summary += f"\n• `{md_safe(item['raw'])}` — {md_safe(item['message'])}"
            if len(failed_items) > 5:
                short_summary += f"\n• ...dan {len(failed_items) - 5} item lain."

        await safe_edit_message(query, 
            f"✅ Pilihan rekening: *{md_safe(account_label)}*.\n\n{short_summary}\n\nSimpan semua item ini?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("mixed"),
        )
        return
    
    if data.startswith("batch_acc:"):
        account = data.split(":")[1]
        skip_account = is_skip_account_choice(account)
        batch = context.user_data.get("pending_batch")

        if not batch:
            await safe_edit_message(query, "❌ Sesi batch expired. Coba input ulang.")
            return

        for item in batch:
            parsed = item["parsed"]
            if needs_account(parsed):
                if skip_account:
                    mark_transaction_as_historical(parsed)
                else:
                    parsed["account"] = account

        context.user_data["pending_batch"] = batch
        preview = build_batch_preview(batch)

        if any(split_bill_needs_decision(item.get("parsed", {})) for item in batch):
            mixed_like = [{"kind": "transaction", "parsed": item["parsed"], "raw": item.get("raw", "")} for item in batch]
            context.user_data["pending_mixed"] = mixed_like
            context.user_data.pop("pending_batch", None)
            await safe_edit_message(query, 
                build_mixed_split_bill_queue_prompt(mixed_like),
                parse_mode="Markdown",
                reply_markup=mixed_split_bill_keyboard(mixed_like),
            )
            return

        await safe_edit_message(query, 
            f"{preview}\n\nSimpan semua transaksi ini?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("batch"),
        )
        return

    if data.startswith("acc:"):
        account = data.split(":")[1]
        skip_account = is_skip_account_choice(account)
        account_label = SKIP_ACCOUNT_NAME if skip_account else account
        parsed = context.user_data.get("pending_parsed")

        if not parsed:
            await safe_edit_message(query, "❌ Sesi expired. Coba input ulang.")
            return

        if skip_account:
            mark_transaction_as_historical(parsed)
        else:
            parsed["account"] = account
        context.user_data["pending_parsed"] = parsed

        if split_bill_needs_decision(parsed):
            await safe_edit_message(query, 
                build_split_bill_prompt_from_parsed(parsed),
                parse_mode="Markdown",
                reply_markup=split_bill_keyboard("single"),
            )
            return

        short_summary = build_single_short_summary(parsed)

        await safe_edit_message(query, 
            f"✅ Pilihan rekening: *{md_safe(account_label)}*.\n\n{short_summary}\n\nSimpan transaksi ini?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("pending"),
        )
        return

    if data.startswith("split:"):
        parts = data.split(":")
        status = parts[1] if len(parts) > 1 else ""
        scope = parts[2] if len(parts) > 2 else "single"

        if status not in ["paid", "unpaid"]:
            await safe_edit_message(query, "❌ Pilihan split bill tidak valid.")
            return

        if scope == "mixed":
            mixed_items = context.user_data.get("pending_mixed")
            if not mixed_items:
                await safe_edit_message(query, "❌ Sesi split bill expired. Coba input ulang.")
                return

            # Untuk bulk input, paid/unpaid harus diterapkan satu-per-satu.
            # Callback mixed sekarang membawa index item aktif. Ini mencegah bug
            # double-click/callback lama: klik lama tidak boleh otomatis
            # memutuskan split bill berikutnya, dan callback duplikat tidak boleh
            # menimpa preview akhir dengan pesan "Tidak ada split bill...".
            expected_index = None
            if len(parts) > 3:
                try:
                    expected_index = int(parts[3])
                except Exception:
                    expected_index = None

            if expected_index is not None:
                mixed_items, decided_index, decision_result = apply_split_bill_decision_to_mixed_index(
                    mixed_items,
                    expected_index,
                    status,
                )
            else:
                mixed_items, decided_index = apply_split_bill_decision_to_current_mixed(mixed_items, status)
                decision_result = "applied" if decided_index is not None else "invalid"

            context.user_data["pending_mixed"] = mixed_items

            if decision_result == "invalid" and not mixed_split_bill_needs_decision(mixed_items):
                # Semua split bill sudah selesai. Kemungkinan ini callback duplikat
                # dari tombol lama. Jangan tampilkan error; lanjutkan ke preview agar
                # user tetap bisa menyimpan data.
                pass
            elif decision_result == "invalid":
                await safe_edit_message(query, 
                    build_mixed_split_bill_queue_prompt(mixed_items),
                    parse_mode="Markdown",
                    reply_markup=mixed_split_bill_keyboard(mixed_items),
                )
                return

            if mixed_split_bill_needs_decision(mixed_items):
                await safe_edit_message(query, 
                    build_mixed_split_bill_queue_prompt(mixed_items),
                    parse_mode="Markdown",
                    reply_markup=mixed_split_bill_keyboard(mixed_items),
                )
                return

            if context.user_data.get("mixed_review_preview_sent"):
                short_summary = build_mixed_short_summary(mixed_items)
                await safe_edit_message(query, 
                    f"✅ Split bill sudah diproses.\n\n{short_summary}\n\nMau edit dulu atau lanjut ke rekening/simpan?",
                    parse_mode="Markdown",
                    reply_markup=edit_or_continue_keyboard("mixed"),
                )
                return

            preview = build_mixed_preview(mixed_items)
            context.user_data["mixed_review_preview_sent"] = True

            await safe_edit_message(query, 
                f"{preview}\n\nMau edit dulu atau lanjut ke rekening/simpan?",
                parse_mode="Markdown",
                reply_markup=edit_or_continue_keyboard("mixed"),
            )
            return

        if scope == "edit_txn":
            pending_edit = context.user_data.get("pending_edit_txn") or {}
            split_parsed = pending_edit.get("split_parsed") or {}
            if not pending_edit or not split_parsed:
                await safe_edit_message(query, "❌ Sesi edit split bill expired. Coba ulangi `/edit_txn`.")
                return

            apply_split_bill_decision_to_parsed(split_parsed, status)
            updates = dict(pending_edit.get("updates", {}) or {})
            updates["amount"] = split_parsed.get("amount")

            preview = preview_edit_transaction_by_ref(
                updates=updates,
                row_index=pending_edit.get("row_index"),
                txn_id=pending_edit.get("txn_id"),
            )
            if not preview.get("success"):
                await safe_edit_message(query, f"❌ {preview.get('message')}", parse_mode="Markdown")
                context.user_data.pop("pending_edit_txn", None)
                return

            pending_edit["updates"] = updates
            pending_edit["split_parsed"] = split_parsed
            pending_edit["split_status"] = status
            context.user_data["pending_edit_txn"] = pending_edit

            await safe_edit_message(
                query,
                build_edit_txn_preview_text_for_callback(preview, split_parsed),
                parse_mode="Markdown",
                reply_markup=confirm_keyboard("edit_txn"),
            )
            return

        parsed = context.user_data.get("pending_parsed")
        if not parsed:
            await safe_edit_message(query, "❌ Sesi split bill expired. Coba input ulang.")
            return

        if parsed.get("split_bill"):
            apply_split_bill_decision_to_parsed(parsed, status)
        context.user_data["pending_parsed"] = parsed
        preview = build_preview(parsed)

        await safe_edit_message(query, 
            f"{preview}\n\nMau edit dulu atau lanjut ke rekening/simpan?",
            parse_mode="Markdown",
            reply_markup=edit_or_continue_keyboard("single"),
        )
        return

    if data.startswith("confirm:"):
        confirm_target = data.split(":")[1] if ":" in data else ""

        if confirm_target == "asset":
            pending_asset = context.user_data.get("pending_asset_confirm")

            if not pending_asset:
                await safe_edit_message(query, "❌ Sesi tambah aset expired. Coba input ulang.")
                return

            await safe_edit_message(query, 
                "⏳ *Sedang menyimpan aset...*",
                parse_mode="Markdown",
            )

            try:
                asset = add_asset(
                    name=pending_asset["name"],
                    current_value=pending_asset.get("amount"),
                    category=pending_asset.get("category", "Other Asset"),
                    description=pending_asset.get("description", ""),
                    asset_type=pending_asset.get("asset_type", "manual"),
                    quantity=pending_asset.get("quantity"),
                    unit=pending_asset.get("unit", ""),
                    price_source=pending_asset.get("price_source", "manual"),
                    price_per_unit=pending_asset.get("price_per_unit"),
                    purchase_price_per_unit=pending_asset.get("purchase_price_per_unit"),
                    purchase_date=pending_asset.get("purchase_date", ""),
                )
            except Exception as e:
                await safe_edit_message(query, f"❌ Gagal menyimpan aset: {str(e)}")
                context.user_data.pop("pending_asset_confirm", None)
                return

            await safe_edit_message(query, 
                build_asset_added_text(asset),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_asset_confirm", None)
            context.user_data.pop("pending_asset_price", None)
            return

        if confirm_target == "pending_expense":
            item = context.user_data.get("pending_expense_confirm")

            if not item:
                await safe_edit_message(query, "❌ Sesi pending expense expired. Coba input ulang.")
                return

            await safe_edit_message(
                query,
                "⏳ *Sedang menyimpan pending expense...*",
                parse_mode="Markdown",
            )

            try:
                saved_item = save_pending_expense(item)
            except Exception as e:
                await safe_edit_message(
                    query,
                    f"❌ Gagal menyimpan pending expense: {md_safe(str(e))}",
                    parse_mode="Markdown",
                )
                return

            subject = str(saved_item.get("subject") or saved_item.get("description") or "Pending Expense")
            due_date = str(saved_item.get("due_date") or "").strip()
            due_precision = str(saved_item.get("due_precision") or "unknown").strip().lower()
            month = str(saved_item.get("month") or "-").strip()
            if due_date:
                due_text = due_date
            elif due_precision == "month":
                due_text = f"{month} (tanggal belum pasti)"
            else:
                due_text = "Belum pasti"

            account = str(saved_item.get("account") or "-").strip() or "-"
            category = str(saved_item.get("category") or "Other Expense").strip()
            amount = float(saved_item.get("amount", 0) or 0)
            pending_id = str(saved_item.get("id") or "").strip()

            await safe_edit_message(
                query,
                "✅ *Pending expense tersimpan!*\n\n"
                f"🕒 *{md_safe(subject)}*\n"
                f"📅 {md_safe(due_text)} | 💰 *{format_rupiah(amount)}* | {md_safe(category)} | 🏦 {md_safe(account)}\n"
                f"🔖 `{md_code_text(pending_id)}`\n\n"
                "Catatan: pending expense tidak mengubah saldo dan belum masuk pengeluaran aktual.\n"
                "Kalau sudah dibayar, pakai:\n"
                f"`/pending_paid {md_code_text(pending_id)} {md_safe(account if account != '-' else 'BRI')}`",
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_expense_confirm", None)
            return

        if confirm_target == "edit_txns_bulk":
            pending_bulk = context.user_data.get("pending_bulk_edit_txns") or {}
            entries = pending_bulk.get("entries") or []

            if not entries:
                await safe_edit_message(query, "❌ Sesi bulk edit transaksi expired. Coba ulangi dari daftar transaksi terakhir.")
                return

            await safe_edit_message(
                query,
                "⏳ *Sedang mengedit beberapa transaksi...*",
                parse_mode="Markdown",
            )

            success_results = []
            failed_results = []
            aggregate_deltas = {}
            latest_balances = {}
            synced_debt_count = 0
            overpaid_count = 0

            for entry in entries:
                result = edit_transaction_by_ref(
                    updates=entry.get("updates", {}),
                    row_index=entry.get("row_index"),
                    txn_id=entry.get("txn_id"),
                )

                if result.get("success"):
                    success_results.append({"entry": entry, "result": result})

                    for account, delta in (result.get("net_deltas") or {}).items():
                        aggregate_deltas[account] = aggregate_deltas.get(account, 0) + float(delta or 0)

                    debt_sync = result.get("debt_sync") or {}
                    synced_debt_count += len(debt_sync.get("updated") or [])
                    overpaid_count += len(debt_sync.get("overpaid") or [])

                    for account, balance in (result.get("new_balances") or {}).items():
                        latest_balances[account] = balance
                else:
                    failed_results.append({"entry": entry, "result": result})

            lines = [
                "✅ *Bulk edit transaksi selesai!*" if not failed_results else "⚠️ *Bulk edit transaksi selesai sebagian.*",
                f"Berhasil: *{len(success_results)}* / *{len(entries)}* transaksi",
            ]

            if success_results:
                lines.append("\n*Berhasil diedit:*")
                for item in success_results[:20]:
                    entry = item.get("entry") or {}
                    result = item.get("result") or {}
                    old_txn = result.get("old_txn") or {}
                    new_txn = result.get("new_txn") or {}
                    ref = str(entry.get("ref") or "-").strip()
                    old_desc = str(old_txn.get("description") or old_txn.get("subject") or "-").strip()
                    new_desc = str(new_txn.get("description") or new_txn.get("subject") or "-").strip()
                    old_cat = str(old_txn.get("category") or "-").strip()
                    new_cat = str(new_txn.get("category") or "-").strip()
                    lines.append(f"• `{md_code_text(ref)}` {md_safe(old_desc)}")
                    if old_cat != new_cat:
                        lines.append(f"  Kategori: {md_safe(old_cat)} → *{md_safe(new_cat)}*")
                    if old_desc != new_desc:
                        lines.append(f"  Desc: {md_safe(old_desc)} → *{md_safe(new_desc)}*")

                if len(success_results) > 20:
                    lines.append(f"• ...dan {len(success_results) - 20} transaksi lain")

            if failed_results:
                lines.append("\n*Gagal diedit:*")
                for item in failed_results[:10]:
                    entry = item.get("entry") or {}
                    result = item.get("result") or {}
                    lines.append(
                        f"• `{md_code_text(entry.get('ref') or '-')}`: {md_safe(result.get('message') or 'Gagal edit.')}"
                    )
                if len(failed_results) > 10:
                    lines.append(f"• ...dan {len(failed_results) - 10} gagal lain")

            if aggregate_deltas:
                lines.append("\n🔁 *Total penyesuaian saldo:*")
                for account, delta in aggregate_deltas.items():
                    sign = "+" if delta >= 0 else "-"
                    lines.append(f"• {md_safe(account)}: {sign}{format_rupiah(abs(delta))}")

            if latest_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                for account, balance in latest_balances.items():
                    lines.append(f"• {md_safe(account)}: *{format_rupiah(balance)}*")

            if synced_debt_count:
                lines.append(f"\n🧾 Debt charge ikut di-sync: *{synced_debt_count} item*")
            if overpaid_count:
                lines.append(f"⚠️ Overpaid adjustment dibuat/diupdate: *{overpaid_count} item*")

            context.user_data.pop("pending_bulk_edit_txns", None)
            await safe_edit_message(query, "\n".join(lines), parse_mode="Markdown")
            return

        if confirm_target == "edit_txn":
            pending_edit = context.user_data.get("pending_edit_txn")

            if not pending_edit:
                await safe_edit_message(query, 
                    "❌ Sesi edit transaksi expired. Coba ulangi `/last`."
                )
                return

            await safe_edit_message(query, 
                "⏳ *Sedang mengedit transaksi dan memperbaiki saldo...*",
                parse_mode="Markdown",
            )

            split_parsed = pending_edit.get("split_parsed") or None
            split_status = (split_parsed or {}).get("split_bill", {}).get("status") if split_parsed else None
            target_txn_id = str(pending_edit.get("txn_id") or "").strip()

            if split_parsed:
                preview_before_edit = preview_edit_transaction_by_ref(
                    updates=pending_edit.get("updates", {}),
                    row_index=pending_edit.get("row_index"),
                    txn_id=pending_edit.get("txn_id"),
                )
                old_txn_for_debt = preview_before_edit.get("old_txn", {}) if preview_before_edit.get("success") else {}
                target_txn_id = target_txn_id or str(old_txn_for_debt.get("id") or "").strip()
                linked_ids = parse_debt_ids_from_txn_record_for_edit(old_txn_for_debt)
                void_result = void_debts_for_transaction(target_txn_id, linked_ids) if target_txn_id else {"success": True}
                if not void_result.get("success"):
                    await safe_edit_message(
                        query,
                        "❌ *Gagal edit split bill.*\n"
                        "Debt/piutang lama tidak bisa dibatalkan otomatis, kemungkinan sudah ada pembayaran/mutasi.\n\n"
                        f"Detail: {md_safe(void_result.get('message') or '-')}",
                        parse_mode="Markdown",
                    )
                    context.user_data.pop("pending_edit_txn", None)
                    return

            result = edit_transaction_by_ref(
                updates=pending_edit.get("updates", {}),
                row_index=pending_edit.get("row_index"),
                txn_id=pending_edit.get("txn_id"),
            )

            if not result.get("success"):
                await safe_edit_message(query, 
                    f"❌ *Gagal edit transaksi.*\n{result.get('message')}",
                    parse_mode="Markdown",
                )
                context.user_data.pop("pending_edit_txn", None)
                return

            old_txn = result.get("old_txn", {})
            new_txn = result.get("new_txn", {})
            net_deltas = result.get("net_deltas", {})
            new_balances = result.get("new_balances", {})

            lines = ["✅ *Transaksi berhasil diedit!*\n"]

            lines.append("*Sebelum:*")
            lines.append(
                f"• {old_txn.get('date')} — {old_txn.get('description') or '-'}\n"
                f"  {format_rupiah(float(old_txn.get('amount', 0) or 0))} | "
                f"{old_txn.get('category') or '-'} | {old_txn.get('account') or '-'}"
            )

            lines.append("\n*Sesudah:*")
            lines.append(
                f"• {new_txn.get('date')} — {new_txn.get('description') or '-'}\n"
                f"  {format_rupiah(float(new_txn.get('amount', 0) or 0))} | "
                f"{new_txn.get('category') or '-'} | {new_txn.get('account') or '-'}"
            )

            if net_deltas:
                lines.append("\n🔁 *Penyesuaian saldo:*")
                for account, delta in net_deltas.items():
                    sign = "+" if delta >= 0 else "-"
                    lines.append(f"• {account}: {sign}{format_rupiah(abs(delta))}")

            if new_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                for account, balance in new_balances.items():
                    lines.append(f"• {account}: *{format_rupiah(balance)}*")

            debt_sync = result.get("debt_sync") or {}
            if debt_sync.get("updated"):
                lines.append("\n🧾 *Debt charge ikut di-sync dari transaksi:*")
                for item in debt_sync.get("updated", [])[:8]:
                    person = item.get("person_name") or "-"
                    lines.append(
                        f"• {md_safe(person)}: "
                        f"{format_rupiah(item.get('old_original', 0))} → "
                        f"*{format_rupiah(item.get('new_original', 0))}*, "
                        f"sudah bayar {format_rupiah(item.get('paid_amount', 0))}, "
                        f"sisa {format_rupiah(item.get('new_remaining', 0))}"
                    )
            if debt_sync.get("overpaid"):
                lines.append("\n⚠️ *Overpaid terdeteksi dan dicatat sebagai debt lawan arah:*")
                for item in debt_sync.get("overpaid", [])[:8]:
                    lines.append(
                        f"• {md_safe(item.get('person_name') or '-')}: "
                        f"{format_rupiah(item.get('amount', 0))}"
                    )
            if debt_sync and debt_sync.get("success") is False:
                lines.append(f"\n⚠️ Sync debt perlu dicek: {md_safe(debt_sync.get('message') or '-')}")

            debt_payment_conversion = pending_edit.get("debt_payment_conversion") or None
            if debt_payment_conversion:
                target_type = str(debt_payment_conversion.get("target_type") or "").strip().lower()
                person = str(debt_payment_conversion.get("person_name") or "").strip().title()
                label = "utang" if target_type == "payable" else "piutang"
                payment_amount = float(new_txn.get("amount", 0) or 0)
                target_txn_id = target_txn_id or str(new_txn.get("id") or "").strip()

                payment_result = add_payment_by_person(
                    person,
                    payment_amount,
                    note=f"Konversi dari transaksi {target_txn_id}",
                    target_debt_type=target_type,
                )

                if payment_result.get("success"):
                    allocations = payment_result.get("allocations") or []
                    debt_ids = [a.get("debt_id") for a in allocations if a.get("debt_id")]
                    if debt_ids and target_txn_id:
                        tipe_hutang = "utang" if target_type == "payable" else "piutang"
                        update_transaction_debt_relation(target_txn_id, debt_ids, tipe_hutang=tipe_hutang)

                    lines.append(f"\n💸 *Pembayaran {label.title()} tercatat:*")
                    lines.append(f"• Orang: {md_safe(person)}")
                    lines.append(f"• Nominal: *{format_rupiah(payment_amount)}*")
                    netting = payment_result.get("netting") or None
                    if netting and float(netting.get("offset_amount", 0) or 0) > 0:
                        lines.append(
                            f"• Auto-netting: *{format_rupiah(netting.get('offset_amount', 0))}* "
                            "hutang/piutang saling menghapus tanpa rollback transaksi sumber"
                        )
                    if allocations:
                        lines.append("• Alokasi debt:")
                        for alloc in allocations:
                            lines.append(
                                f"  - `{md_code_text(alloc.get('debt_id') or '-')}`: "
                                f"{format_rupiah(float(alloc.get('amount', 0) or 0))}"
                            )
                    if float(payment_result.get("overpayment", 0) or 0) > 0:
                        lines.append(
                            f"⚠️ Kelebihan pembayaran: {format_rupiah(payment_result.get('overpayment', 0))}. "
                            "Kelebihan tidak mengurangi debt."
                        )
                    lines.append(f"• Sisa {label}: *{format_rupiah(payment_result.get('remaining', 0))}*")
                else:
                    lines.append(
                        "\n⚠️ *Transaksi sudah diedit, tapi pembayaran debt gagal dicatat.*\n"
                        f"Detail: {md_safe(payment_result.get('message') or '-')}\n"
                        "Cek sheet debts/debt_payments secara manual."
                    )

            if split_parsed and target_txn_id:
                if split_status == "unpaid":
                    split_debt = create_split_bill_debt(
                        split_parsed,
                        pending_edit.get("split_raw", "edit split bill"),
                        source_transaction_id=target_txn_id,
                    )
                    if split_debt and split_debt.get("success"):
                        debt_ids = [
                            item.get("debt_id")
                            for item in split_debt.get("created", [])
                            if item.get("debt_id")
                        ]
                        if debt_ids:
                            update_transaction_debt_relation(target_txn_id, debt_ids, tipe_hutang="piutang")
                        lines.append("\n🤝 *Piutang split bill baru dibuat:*")
                        lines.extend(format_split_debt_result_lines(split_debt))
                    elif split_debt:
                        lines.append(f"\n⚠️ Gagal membuat piutang split bill baru: {md_safe(split_debt.get('message') or '-')}")
                elif split_status == "paid":
                    clear_transaction_debt_relation(target_txn_id)
                    lines.append("\n🤝 Split bill ditandai sudah dibayar, jadi tidak ada piutang aktif baru.")

            await safe_edit_message(query, 
                "\n".join(lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_edit_txn", None)
            return
        if confirm_target == "delete_txns":
            pending_refs = context.user_data.get("pending_delete_refs", {})

            row_indices = pending_refs.get("row_indices", [])
            txn_ids = pending_refs.get("txn_ids", [])

            if not row_indices and not txn_ids:
                await safe_edit_message(query, 
                    "❌ Sesi hapus transaksi expired. Coba ulangi `/last`."
                )
                return

            await safe_edit_message(query, 
                "⏳ *Sedang menghapus transaksi dan memperbaiki saldo...*",
                parse_mode="Markdown",
            )

            result = delete_transactions_by_refs(
                row_indices=row_indices,
                txn_ids=txn_ids,
            )

            if not result.get("success"):
                lines = [
                    f"❌ *Gagal menghapus transaksi.*\n{result.get('message')}"
                ]

                if result.get("blocked"):
                    lines.append("\n🚫 *Transaksi diblok:*")
                    for txn in result["blocked"]:
                        lines.append(
                            f"• Row {txn.get('_row_index', '-')} — "
                            f"{txn.get('date')} — {txn.get('description') or '-'} "
                            f"({txn.get('category') or '-'})"
                        )

                if result.get("missing_ids"):
                    lines.append("\n❓ *ID tidak ditemukan:*")
                    for txn_id in result["missing_ids"]:
                        lines.append(f"• `{txn_id}`")

                if result.get("missing_rows"):
                    lines.append("\n❓ *Row tidak ditemukan:*")
                    for row in result["missing_rows"]:
                        lines.append(f"• `{row}`")

                await safe_edit_message(query, 
                    "\n".join(lines),
                    parse_mode="Markdown",
                )

                context.user_data.pop("pending_delete_refs", None)
                context.user_data.pop("pending_delete_txn_ids", None)
                return

            lines = [
                "✅ *Transaksi berhasil dihapus!*",
                f"🗑️ Terhapus: *{result.get('deleted_count', 0)} transaksi*",
            ]

            deleted_ids = result.get("deleted_ids", [])
            if deleted_ids:
                lines.append("\n🔖 *ID terhapus:*")
                for txn_id in deleted_ids:
                    lines.append(f"• `{short_txn_id(txn_id)}`")

            new_balances = result.get("new_balances", {})
            if new_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                for account, balance in new_balances.items():
                    lines.append(f"• {account}: *{format_rupiah(balance)}*")

            if result.get("linked_debts_voided"):
                lines.append("\n🔗 *Debt terkait ikut di-void karena transaksi sumber dihapus:*")
                for debt_id in result.get("linked_debts_voided") or []:
                    lines.append(f"• `{md_code_text(debt_id)}`")

            if result.get("reversed_payment_debts"):
                lines.append("\n↩️ *Pembayaran debt terkait ikut dibalikkan:*")
                for item in result.get("reversed_payment_debts") or []:
                    lines.append(f"• `{md_code_text(item.get('debt_id'))}` +{format_rupiah(item.get('amount', 0))}")

            if result.get("blocked"):
                lines.append("\n🚫 *Diblok karena debt cashflow:*")
                for txn in result["blocked"]:
                    lines.append(
                        f"• Row {txn.get('_row_index', '-')} — "
                        f"{txn.get('date')} — {txn.get('description') or '-'} "
                        f"({txn.get('category') or '-'})"
                    )

            if result.get("missing_ids"):
                lines.append("\n❓ *ID tidak ditemukan:*")
                for txn_id in result["missing_ids"]:
                    lines.append(f"• `{txn_id}`")

            if result.get("missing_rows"):
                lines.append("\n❓ *Row tidak ditemukan:*")
                for row in result["missing_rows"]:
                    lines.append(f"• `{row}`")

            await safe_edit_message(query, 
                "\n".join(lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_delete_refs", None)
            context.user_data.pop("pending_delete_txn_ids", None)
            return
    
        if confirm_target == "debt_settle":
            payload = context.user_data.get("pending_debt_settle")
            if not payload:
                await safe_edit_message(query, "❌ Sesi debt settle expired. Coba ulangi `/hutang Nama` lalu `/debt_settle ...`.", parse_mode="Markdown")
                return

            if float(payload.get("shortage", 0) or 0) > 0:
                from app.bot.handler_parts.command_handlers import build_selected_debt_settle_preview_text
                await safe_edit_message(query, build_selected_debt_settle_preview_text(payload), parse_mode="Markdown")
                return

            if float(payload.get("overpayment", 0) or 0) > 0 and not payload.get("overpayment_policy"):
                from app.bot.handler_parts.command_handlers import (
                    build_selected_debt_settle_preview_text,
                    selected_debt_settle_overpay_keyboard,
                )
                await safe_edit_message(
                    query,
                    build_selected_debt_settle_preview_text(payload),
                    parse_mode="Markdown",
                    reply_markup=selected_debt_settle_overpay_keyboard(),
                )
                return

            await safe_edit_message(query, "⏳ *Sedang settle debt terpilih...*", parse_mode="Markdown")

            result = settle_selected_debt_ids(
                payload.get("person_name"),
                payload.get("debt_ids") or [],
                note=payload.get("raw") or f"Settlement debt {payload.get('selection') or ''}",
                overpayment_amount=float(payload.get("overpayment", 0) or 0),
                overpayment_policy=payload.get("overpayment_policy"),
                net_type=payload.get("net_type"),
            )
            if not result.get("success"):
                await safe_edit_message(query, f"❌ *Gagal settle debt.*\n{md_safe(result.get('message') or '-')}", parse_mode="Markdown")
                context.user_data.pop("pending_debt_settle", None)
                return

            from app.bot.handler_parts.command_handlers import build_selected_debt_settle_transaction
            txn = build_selected_debt_settle_transaction(payload, result)
            txn_result = save_transaction(txn, raw_input=payload.get("raw") or f"/debt_settle {payload.get('person_name')} {payload.get('selection')}")

            lines = ["✅ *Debt terpilih berhasil disettle!*\n"]
            lines.append(f"👤 Subjek: *{md_safe(payload.get('person_name') or '-')}*")
            lines.append(f"📌 Rincian: *{md_safe(payload.get('selection') or '-')}*")
            lines.append(f"🧾 Debt disettle: *{len(result.get('settled') or [])} rincian*")
            summary = payload.get("summary") or {}
            lines.append(f"🟢 Piutang terpilih: *{format_rupiah(summary.get('total_receivable', 0))}*")
            lines.append(f"🔴 Utang terpilih: *{format_rupiah(summary.get('total_payable', 0))}*")
            lines.append(f"💰 Cashflow: *{format_rupiah(payload.get('amount', 0))}* via *{md_safe(payload.get('account') or '-')}*")

            overpayment = float(result.get("overpayment", 0) or 0)
            if overpayment > 0:
                if result.get("overpayment_created"):
                    lines.append(f"⚠️ Kelebihan *{format_rupiah(overpayment)}* dicatat sebagai debt lawan arah.")
                else:
                    lines.append(f"ℹ️ Kelebihan *{format_rupiah(overpayment)}* dianggap lunas/bonus.")

            lines.append("\n*Posisi akhir hutang-piutang:*")
            for line in format_debt_net_position_lines(
                payload.get("person_name") or "-",
                result.get("remaining_payable", 0),
                result.get("remaining_receivable", 0),
            ):
                lines.append(md_safe(line))

            if txn_result.get("success"):
                lines.append("\n📝 Cashflow tersimpan di transactions.")
                if txn_result.get("transaction_id"):
                    lines.append(f"🔖 ID: `{txn_result.get('transaction_id')}`")
                if txn_result.get("new_balance") is not None:
                    balance_account = txn_result.get("new_balance_account") or payload.get("account") or payload.get("to_account") or "-"
                    lines.append(f"💳 Saldo {md_safe(balance_account)}: *{format_rupiah(txn_result.get('new_balance'))}*")
            else:
                try:
                    from app.services.debt_service import reverse_debt_payment_transaction
                    reverse_result = reverse_debt_payment_transaction(txn)
                except Exception as e:
                    reverse_result = {"success": False, "message": str(e)}
                lines = [
                    f"❌ *Cashflow gagal disimpan, settlement debt dibatalkan ulang.*\n{md_safe(txn_result.get('message') or '-')}"
                ]
                if not reverse_result.get("success"):
                    lines.append(
                        "\n⚠️ Gagal membuka ulang sebagian debt otomatis. "
                        f"Detail: {md_safe(reverse_result.get('message') or '-')}"
                    )

            await safe_edit_message(query, "\n".join(lines), parse_mode="Markdown")
            context.user_data.pop("pending_debt_settle", None)
            return

        if confirm_target == "debt_void":
            pending_void = context.user_data.get("pending_debt_void")

            if not pending_void:
                await safe_edit_message(query, "❌ Sesi debt void expired. Coba ulangi `/hutang Nama` lalu `/debt_void 1` atau `/debt_void Nama`.")
                return

            await safe_edit_message(query, 
                "⏳ *Sedang membatalkan debt dan memperbaiki saldo...*",
                parse_mode="Markdown",
            )

            if pending_void.get("mode") == "bulk":
                result = void_debt_ids(pending_void.get("target_debt_ids") or [])
            else:
                debt_ref = pending_void.get("debt_ref")
                last_debt_map = context.user_data.get("last_debt_map", {})
                result = void_debt(debt_ref, last_debt_map)

            if not result.get("success"):
                lines = [f"❌ *Gagal void debt.*\n{md_safe(result.get('message'))}"]
                success_results = result.get("success_results") or []
                if success_results:
                    lines.append("\n⚠️ Sebagian debt sudah terlanjur berhasil di-void:")
                    for r in success_results:
                        debt = r.get("debt") or {}
                        lines.append(f"• `{md_safe(short_debt_id(debt.get('id', '-')))}` — {md_safe(debt.get('description') or '-')}")
                await safe_edit_message(query, 
                    "\n".join(lines),
                    parse_mode="Markdown",
                )
                context.user_data.pop("pending_debt_void", None)
                return

            is_bulk = pending_void.get("mode") == "bulk"
            new_balances = result.get("new_balances", {}) or {}
            reverse_deltas = result.get("reverse_deltas", {}) or {}

            if is_bulk:
                debts = result.get("debts") or []
                cashflow_txns = result.get("cashflow_txns") or []
                person_name = pending_void.get("person_name") or (debts[0].get("person_name") if debts else "-")
                lines = ["✅ *Debt berhasil di-void!*\n"]
                lines.append(f"👤 Nama: *{md_safe(person_name)}*")
                lines.append(f"📌 Rincian divoid: *{len(debts)}*")
                lines.append(f"💰 Total nominal awal: *{format_rupiah(float(result.get('total_original', 0) or 0))}*")

                lines.append("\n*Rincian:*")
                for i, debt in enumerate(debts, 1):
                    debt_type = str(debt.get("type") or "").strip()
                    icon = "🔴" if debt_type == "payable" else "🟢"
                    lines.append(
                        f"{i}. {icon} {md_safe(debt.get('description') or '-')}\n"
                        f"   Debt ID: `{md_safe(short_debt_id(debt.get('id', '-')))}`\n"
                        f"   Nominal: *{format_rupiah(float(debt.get('original_amount', 0) or 0))}*"
                    )

                if cashflow_txns:
                    lines.append("\n🗑️ *Cashflow terkait dihapus:*")
                    for txn in cashflow_txns[:10]:
                        lines.append(
                            f"• Row {txn.get('_row_index', '-')} — {md_safe(txn.get('description') or '-')} — "
                            f"{format_rupiah(float(txn.get('amount', 0) or 0))}"
                        )
                    if len(cashflow_txns) > 10:
                        lines.append(f"• ...dan {len(cashflow_txns) - 10} cashflow lain")
            else:
                debt = result.get("debt", {}) or {}
                txn = result.get("cashflow_txn", {}) or {}
                direction = "🔴 Utang Anda" if debt.get("type") == "payable" else "🟢 Piutang Anda"
                lines = ["✅ *Debt berhasil di-void!*\n"]
                lines.append(f"{direction} dengan *{md_safe(debt.get('person_name', '-'))}*")
                lines.append(f"💰 Nominal: *{format_rupiah(float(debt.get('original_amount', 0) or 0))}*")
                lines.append(f"🔖 Debt ID: `{md_safe(short_debt_id(debt.get('id', '-')))}`")

                if txn:
                    lines.append("\n🗑️ *Cashflow terkait dihapus:*")
                    lines.append(
                        f"• Row {txn.get('_row_index', '-')} — {md_safe(txn.get('description') or '-')} — "
                        f"{format_rupiah(float(txn.get('amount', 0) or 0))}"
                    )

            if reverse_deltas:
                lines.append("\n🔁 *Penyesuaian saldo:*")
                for account, delta in reverse_deltas.items():
                    sign = "+" if delta >= 0 else "-"
                    lines.append(f"• {md_safe(account)}: {sign}{format_rupiah(abs(delta))}")

            if new_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                for account, balance in new_balances.items():
                    lines.append(f"• {md_safe(account)}: *{format_rupiah(balance)}*")

            await safe_edit_message(query, 
                "\n".join(lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_debt_void", None)
            return

        if confirm_target == "debt":
            debt_parsed = context.user_data.get("pending_debt")

            if not debt_parsed:
                await safe_edit_message(query, "❌ Sesi debt expired. Coba input ulang.")
                return

            await safe_edit_message(query, 
                "⏳ *Sedang menyimpan debt dan cashflow...*",
                parse_mode="Markdown",
            )

            intent = debt_parsed.get("intent")
            person = debt_parsed.get("person_name")
            amount = debt_parsed.get("amount")
            description = debt_parsed.get("description") or ""
            account = debt_parsed.get("account")
            debt_type_for_payment = debt_parsed.get("debt_type_for_payment")
            raw = debt_parsed.get("raw_input") or ""

            if not person:
                await safe_edit_message(query, "❌ Nama orang tidak terdeteksi. Coba input ulang.")
                context.user_data.pop("pending_debt", None)
                return

            debt_result = None

            if intent == "add_payable":
                debt_result = add_debt("payable", person, amount, description)

            elif intent == "add_receivable":
                debt_result = add_debt("receivable", person, amount, description)

            elif intent == "add_payment":
                debt_result = add_payment_by_person(
                    person,
                    amount,
                    note=description or raw or f"Pembayaran debt {person}",
                    target_debt_type=debt_type_for_payment or debt_parsed.get("target_debt_type"),
                    overpayment_policy=debt_parsed.get("overpayment_policy"),
                )

            elif intent == "offset_debt":
                debt_result = offset_debt_by_person(
                    person,
                    amount,
                    description,
                    target_debt_type=debt_parsed.get("target_debt_type") or "receivable",
                    resulting_debt_type=debt_parsed.get("resulting_debt_type") or "payable",
                )

            else:
                await safe_edit_message(query, "❌ Intent debt tidak valid. Coba input ulang.")
                context.user_data.pop("pending_debt", None)
                return

            if not debt_result or not debt_result.get("success"):
                message = debt_result.get("message") if debt_result else "Unknown error"
                await safe_edit_message(query, f"❌ Gagal menyimpan debt: {message}")
                context.user_data.pop("pending_debt", None)
                return

            fronted_split_result = create_fronted_split_receivable_debts(debt_parsed)
            attach_fronted_split_debt_relations(debt_parsed, debt_result, fronted_split_result)

            if intent == "add_payment":
                debt_parsed["debt_allocations"] = debt_result.get("allocations") or []
                debt_parsed["overpayment"] = debt_result.get("overpayment") or 0
                debt_parsed["overpayment_policy"] = debt_result.get("overpayment_policy") or debt_parsed.get("overpayment_policy") or ""
                if debt_result.get("net_settlement"):
                    debt_parsed["net_settlement"] = True
                overpayment_created = debt_result.get("overpayment_created") or {}
                if overpayment_created.get("debt_id"):
                    debt_parsed["overpayment_debt_id"] = overpayment_created.get("debt_id")
                if debt_result.get("affected_debt_ids"):
                    debt_parsed["hutang_id"] = ", ".join([x for x in debt_result.get("affected_debt_ids") or [] if x])

            if not debt_parsed.get("hutang_id") and debt_result.get("debt_id"):
                debt_parsed["hutang_id"] = debt_result.get("debt_id")
            if not debt_parsed.get("tipe_hutang") and debt_result.get("type"):
                if debt_result.get("type") == "offset":
                    debt_parsed["tipe_hutang"] = "offset"
                else:
                    debt_parsed["tipe_hutang"] = "utang" if debt_result.get("type") == "payable" else "piutang"

            debt_txn = build_debt_cashflow_transaction(
                debt_parsed,
                account,
                debt_type_for_payment=debt_type_for_payment,
            )
            transaction_result = None
            if debt_txn.get("type") != "pending":
                transaction_result = save_transaction(debt_txn, raw_input=raw)

            lines = ["✅ *Debt berhasil diproses!*\n"]

            netting = (debt_result or {}).get("netting") or None
            if netting and float(netting.get("offset_amount", 0) or 0) > 0:
                lines.append(
                    f"🔁 Auto-netting hutang/piutang: *{format_rupiah(netting.get('offset_amount', 0))}* "
                    "sudah saling menghapus tanpa mengubah transaksi sumber.\n"
                )

            if intent in ["add_payable", "add_receivable"]:
                if debt_result.get("is_settled"):
                    lines.append(f"📌 Debt *{person}* impas/lunas")
                else:
                    direction = "🔴 Utang Anda" if debt_result.get("type") == "payable" else "🟢 Piutang Anda"
                    lines.append(f"{direction} dengan *{debt_result.get('person_name', person)}*")
                    lines.append(f"💰 Saldo: *{format_rupiah(debt_result.get('remaining', 0))}*")
                append_fronted_split_result_lines(lines, fronted_split_result)

            elif intent == "add_payment":
                target_label = "utang Anda" if debt_type_for_payment == "payable" else "piutang Anda"
                lines.append(f"📌 Pembayaran mengurangi *{md_safe(target_label)}* dengan *{md_safe(person)}*")
                lines.append(f"📊 Sisa arah ini: *{format_rupiah(debt_result.get('remaining', 0))}*")

                remaining_payable = float(debt_result.get("remaining_payable", 0) or 0)
                remaining_receivable = float(debt_result.get("remaining_receivable", 0) or 0)
                lines.append("\n*Posisi akhir hutang-piutang:*")
                for line in format_debt_net_position_lines(person, remaining_payable, remaining_receivable):
                    lines.append(md_safe(line))

                overpayment = float(debt_result.get("overpayment", 0) or 0)
                if overpayment > 0:
                    if debt_result.get("overpayment_created"):
                        lines.append(f"\n⚠️ Kelebihan bayar *{format_rupiah(overpayment)}* dicatat sebagai debt lawan arah.")
                    else:
                        lines.append(f"\nℹ️ Kelebihan bayar *{format_rupiah(overpayment)}* dianggap lunas/bonus.")

            elif intent == "offset_debt":
                target_label = "piutang" if debt_result.get("target_debt_type") == "receivable" else "utang"
                lines.append(f"🔁 Kompensasi dengan *{person}*")
                lines.append(f"➖ Potong {target_label}: *{format_rupiah(debt_result.get('offset_applied', amount))}*")
                if debt_result.get("overage", 0):
                    new_label = "utang" if debt_result.get("resulting_debt_type") == "payable" else "piutang"
                    lines.append(f"⚠️ Sisa menjadi {new_label} baru: *{format_rupiah(debt_result.get('overage', 0))}*")
                lines.append(f"📊 Sisa piutang: *{format_rupiah(debt_result.get('remaining_receivable', 0))}*")
                lines.append(f"📊 Sisa utang: *{format_rupiah(debt_result.get('remaining_payable', 0))}*")

            if transaction_result:
                if transaction_result.get("success"):
                    lines.append("\n📝 Cashflow tersimpan di transactions.")
                    if transaction_result.get("transaction_id"):
                        lines.append(f"🔖 ID: `{transaction_result['transaction_id']}`")
                    if transaction_result.get("new_balance") is not None:
                        balance_account = transaction_result.get("new_balance_account") or account or debt_parsed.get("to_account") or "-"
                        lines.append(f"💳 Saldo {md_safe(balance_account)}: *{format_rupiah(transaction_result['new_balance'])}*")
                else:
                    lines.append(f"\n⚠️ Debt tersimpan, tapi cashflow gagal: {md_safe(transaction_result.get('message'))}")
            elif not debt_uses_cashflow(debt_parsed):
                lines.append("\n📝 Cashflow tidak dicatat karena ini mode talangan/ditalangin tanpa uang masuk/keluar dari rekening Anda.")

            await safe_edit_message(query, 
                "\n".join(lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_debt_batch", None)
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            context.user_data.pop("pending_batch", None)
            return

        if confirm_target == "debt_batch":
            debt_batch = context.user_data.get("pending_debt_batch")

            if not debt_batch:
                await safe_edit_message(query, "❌ Sesi batch debt expired. Coba input ulang.")
                return

            await safe_edit_message(query, 
                "⏳ *Sedang menyimpan batch debt dan cashflow...*",
                parse_mode="Markdown",
            )

            debt_transaction_items = []
            failed_items = []
            result_lines = ["✅ *Batch debt diproses!*\n"]
            debt_success_count = 0

            for i, item in enumerate(debt_batch, 1):
                parsed = item["parsed"]
                raw = item["raw"]

                intent = parsed.get("intent")
                person = parsed.get("person_name")
                amount = parsed.get("amount")
                description = parsed.get("description") or ""
                account = parsed.get("account")
                debt_type_for_payment = parsed.get("debt_type_for_payment")

                if not person:
                    failed_items.append({"raw": raw, "message": "Nama orang tidak terdeteksi."})
                    continue

                debt_result = None

                if intent == "add_payable":
                    debt_result = add_debt("payable", person, amount, description)
                elif intent == "add_receivable":
                    debt_result = add_debt("receivable", person, amount, description)
                elif intent == "add_payment":
                    target_debt_id = parsed.get("target_debt_id")
                    if target_debt_id:
                        debt_result = add_payment(target_debt_id, amount)
                    else:
                        debt_result = add_payment_by_person(
                            person,
                            amount,
                            target_debt_type=debt_type_for_payment or parsed.get("target_debt_type"),
                        )
                elif intent == "offset_debt":
                    debt_result = offset_debt_by_person(
                        person,
                        amount,
                        description,
                        target_debt_type=parsed.get("target_debt_type") or "receivable",
                        resulting_debt_type=parsed.get("resulting_debt_type") or "payable",
                    )
                else:
                    failed_items.append({"raw": raw, "message": "Intent debt tidak valid."})
                    continue

                if not debt_result or not debt_result.get("success"):
                    failed_items.append({
                        "raw": raw,
                        "message": debt_result.get("message") if debt_result else "Unknown error",
                    })
                    continue

                fronted_split_result = create_fronted_split_receivable_debts(parsed)
                attach_fronted_split_debt_relations(parsed, debt_result, fronted_split_result)

                if not parsed.get("hutang_id") and debt_result.get("debt_id"):
                    parsed["hutang_id"] = debt_result.get("debt_id")
                if not parsed.get("tipe_hutang") and debt_result.get("type"):
                    if debt_result.get("type") == "offset":
                        parsed["tipe_hutang"] = "offset"
                    else:
                        parsed["tipe_hutang"] = "utang" if debt_result.get("type") == "payable" else "piutang"

                debt_success_count += 1
                result_lines.append(f"{i}. ✅ Debt *{person}* diproses")
                append_fronted_split_result_lines(result_lines, fronted_split_result, indent="   ")

                debt_txn = build_debt_cashflow_transaction(
                    parsed,
                    account,
                    debt_type_for_payment=debt_type_for_payment,
                )

                if debt_txn.get("type") != "pending":
                    debt_transaction_items.append({"parsed": debt_txn, "raw": raw})
                    if debt_txn.get("type") in ["debt_only", "debt_offset"]:
                        result_lines.append("   📝 Masuk transactions tanpa update saldo rekening")

            transaction_result = None
            if debt_transaction_items:
                transaction_result = save_transactions_batch(debt_transaction_items)

            result_lines.append("")
            result_lines.append(f"💸 Debt diproses: *{debt_success_count} item*")

            if transaction_result:
                result_lines.append(f"📝 Cashflow tersimpan: *{transaction_result.get('success_count', 0)} item*")
                new_balances = transaction_result.get("new_balances", {})
                if new_balances:
                    result_lines.append("\n💳 *Saldo terbaru:*")
                    for account_name, balance in new_balances.items():
                        result_lines.append(f"• {account_name}: *{format_rupiah(balance)}*")

                tx_failed = transaction_result.get("failed_items", [])
                if tx_failed:
                    failed_items.extend(tx_failed)

                if transaction_result.get("message") and transaction_result.get("message") != "ok":
                    result_lines.append(f"\n⚠️ {transaction_result['message']}")

            if failed_items:
                result_lines.append("\n❌ *Catatan/Gagal:*")
                for item in failed_items:
                    result_lines.append(f"• `{item['raw']}` — {item['message']}")

            await safe_edit_message(query, 
                "\n".join(result_lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_debt_batch", None)
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            context.user_data.pop("pending_batch", None)
            return

        if confirm_target == "mixed":
            mixed_items = context.user_data.get("pending_mixed")

            if not mixed_items:
                await safe_edit_message(query, "❌ Sesi mixed input expired. Coba input ulang.")
                return

            await safe_edit_message(query, 
                "⏳ *Sedang menyimpan semua item...*",
                parse_mode="Markdown",
            )

            normal_transaction_items = []
            debt_transaction_items = []
            failed_items = []
            result_lines = ["✅ *Mixed input diproses!*\n"]

            debt_success_count = 0
            transaction_success_count = 0

            for i, item in enumerate(mixed_items, 1):
                parsed = item["parsed"]
                raw = item["raw"]

                if item["kind"] == "transaction":
                    normal_transaction_items.append({
                        "parsed": parsed,
                        "raw": raw,
                    })
                    continue

                if item["kind"] != "debt":
                    failed_items.append({
                        "raw": raw,
                        "message": "Jenis item tidak valid.",
                    })
                    continue

                intent = parsed.get("intent")
                person = parsed.get("person_name")
                amount = parsed.get("amount")
                description = parsed.get("description") or ""
                account = parsed.get("account")
                debt_type_for_payment = parsed.get("debt_type_for_payment")

                if not person:
                    failed_items.append({
                        "raw": raw,
                        "message": "Nama orang tidak terdeteksi.",
                    })
                    continue

                debt_result = None

                if intent == "add_payable":
                    debt_result = add_debt("payable", person, amount, description)

                elif intent == "add_receivable":
                    debt_result = add_debt("receivable", person, amount, description)

                elif intent == "add_payment":
                    target_debt_id = parsed.get("target_debt_id")

                    if target_debt_id:
                        debt_result = add_payment(target_debt_id, amount)
                    else:
                        debt_result = add_payment_by_person(
                            person,
                            amount,
                            target_debt_type=debt_type_for_payment or parsed.get("target_debt_type"),
                        )

                elif intent == "offset_debt":
                    debt_result = offset_debt_by_person(
                        person,
                        amount,
                        description,
                        target_debt_type=parsed.get("target_debt_type") or "receivable",
                        resulting_debt_type=parsed.get("resulting_debt_type") or "payable",
                    )

                else:
                    failed_items.append({
                        "raw": raw,
                        "message": "Intent debt tidak valid.",
                    })
                    continue

                if not debt_result or not debt_result.get("success"):
                    failed_items.append({
                        "raw": raw,
                        "message": debt_result.get("message") if debt_result else "Unknown error",
                    })
                    continue

                fronted_split_result = create_fronted_split_receivable_debts(parsed)
                attach_fronted_split_debt_relations(parsed, debt_result, fronted_split_result)

                if not parsed.get("hutang_id") and debt_result.get("debt_id"):
                    parsed["hutang_id"] = debt_result.get("debt_id")
                if not parsed.get("tipe_hutang") and debt_result.get("type"):
                    if debt_result.get("type") == "offset":
                        parsed["tipe_hutang"] = "offset"
                    else:
                        parsed["tipe_hutang"] = "utang" if debt_result.get("type") == "payable" else "piutang"

                debt_success_count += 1

                if intent in ["add_payable", "add_receivable"]:
                    if debt_result.get("is_settled"):
                        result_lines.append(f"{i}. ✅ Debt *{person}* impas/lunas")
                    else:
                        direction = (
                            "🔴 Utang Anda"
                            if debt_result["type"] == "payable"
                            else "🟢 Piutang Anda"
                        )
                        result_lines.append(
                            f"{i}. {direction} dengan *{debt_result['person_name']}*\n"
                            f"   💰 Saldo: *{format_rupiah(debt_result['remaining'])}*"
                        )
                    append_fronted_split_result_lines(result_lines, fronted_split_result, indent="   ")

                    debt_txn = build_debt_cashflow_transaction(
                        parsed,
                        account,
                    )
                    if debt_txn.get("type") in ["debt_only", "debt_offset"]:
                        result_lines.append("   📝 Masuk transactions tanpa update saldo rekening")

                elif intent == "add_payment":
                    if debt_result.get("is_settled"):
                        result_lines.append(f"{i}. ✅ Debt *{person}* lunas")
                    else:
                        direction = (
                            "🔴 Utang Anda"
                            if debt_type_for_payment == "payable"
                            else "🟢 Piutang Anda"
                        )
                        result_lines.append(
                            f"{i}. 💸 Pembayaran *{person}*\n"
                            f"   📌 Posisi: {direction}\n"
                            f"   📊 Sisa: *{format_rupiah(debt_result['remaining'])}*"
                        )

                    debt_txn = build_debt_cashflow_transaction(
                        parsed,
                        account,
                        debt_type_for_payment=debt_type_for_payment,
                    )

                elif intent == "offset_debt":
                    target_label = "piutang" if debt_result.get("target_debt_type") == "receivable" else "utang"
                    result_lines.append(
                        f"{i}. 🔁 Kompensasi *{person}*\n"
                        f"   ➖ Potong {target_label}: *{format_rupiah(debt_result.get('offset_applied', amount))}*\n"
                        f"   📊 Sisa piutang: *{format_rupiah(debt_result.get('remaining_receivable', 0))}*\n"
                        f"   📊 Sisa utang: *{format_rupiah(debt_result.get('remaining_payable', 0))}*"
                    )
                    debt_txn = build_debt_cashflow_transaction(parsed, account)

                else:
                    debt_txn = {"type": "pending"}

                if debt_txn.get("type") != "pending":
                    debt_transaction_items.append({
                        "parsed": debt_txn,
                        "raw": raw,
                    })

            all_transaction_items = normal_transaction_items + debt_transaction_items

            transaction_result = None
            if all_transaction_items:
                transaction_result = save_transactions_batch(all_transaction_items)

            if transaction_result:
                transaction_success_count = transaction_result.get("success_count", 0)

                result_lines.append("")
                result_lines.append(f"📝 Transactions tersimpan: *{transaction_success_count} item*")
                result_lines.append(f"💸 Debt diproses: *{debt_success_count} item*")
                append_saved_summary_lines(result_lines, all_transaction_items)

                split_debt_lines = []
                saved_ids = transaction_result.get("saved_ids", []) if transaction_result else []
                normal_idx = 0
                for item in normal_transaction_items:
                    source_txn_id = saved_ids[normal_idx] if normal_idx < len(saved_ids) else ""
                    normal_idx += 1
                    debt_result = create_split_bill_debt(item.get("parsed", {}), item.get("raw", ""), source_transaction_id=source_txn_id)
                    if debt_result and debt_result.get("success"):
                        split_debt_lines.extend(format_split_debt_result_lines(debt_result))
                        debt_ids = [
                            x.get("debt_id")
                            for x in debt_result.get("created", [])
                            if x.get("debt_id")
                        ]
                        if source_txn_id and debt_ids:
                            relation_result = update_transaction_debt_relation(
                                source_txn_id,
                                debt_ids,
                                tipe_hutang="piutang",
                            )
                            if not relation_result.get("success"):
                                failed_items.append({
                                    "raw": item.get("raw", "split bill"),
                                    "message": f"Piutang dibuat, tapi relasi transaksi gagal: {relation_result.get('message')}",
                                })
                    elif debt_result:
                        failed_items.append({
                            "raw": item.get("raw", "split bill"),
                            "message": debt_result.get("message", "Gagal membuat piutang split bill."),
                        })

                if split_debt_lines:
                    result_lines.append("\n🤝 *Piutang split bill dibuat:*")
                    result_lines.extend(split_debt_lines)

                new_balances = transaction_result.get("new_balances", {})
                if new_balances:
                    result_lines.append("\n💳 *Saldo terbaru:*")
                    for account_name, balance in new_balances.items():
                        result_lines.append(f"• {account_name}: *{format_rupiah(balance)}*")

                tx_failed = transaction_result.get("failed_items", [])
                if tx_failed:
                    failed_items.extend(tx_failed)

                if transaction_result.get("message") and transaction_result.get("message") != "ok":
                    result_lines.append(f"\n⚠️ {transaction_result['message']}")

            if failed_items:
                result_lines.append("\n❌ *Catatan/Gagal:*")
                for item in failed_items:
                    result_lines.append(f"• `{item['raw']}` — {item['message']}")

            await safe_edit_message(query, 
                "\n".join(result_lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_mixed", None)
            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_debt_batch", None)
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            return
        
        if confirm_target == "batch":
            batch = context.user_data.get("pending_batch")

            if not batch:
                await safe_edit_message(query, "❌ Sesi batch expired. Coba input ulang.")
                return

            await safe_edit_message(query, 
                "⏳ *Sedang menyimpan semua transaksi...*",
                parse_mode="Markdown",
            )

            result = save_transactions_batch(batch)

            lines = [
                "✅ *Batch selesai diproses!*",
                f"📝 Berhasil: {result.get('success_count', 0)} transaksi",
            ]

            saved_ids = result.get("saved_ids", [])
            if saved_ids:
                lines.append("\n🔖 *ID tersimpan:*")
                for txn_id in saved_ids:
                    lines.append(f"• `{txn_id}`")

            append_saved_summary_lines(lines, batch)

            split_debt_lines = []
            for idx, item in enumerate(batch):
                source_txn_id = saved_ids[idx] if idx < len(saved_ids) else ""
                debt_result = create_split_bill_debt(item.get("parsed", {}), item.get("raw", ""), source_transaction_id=source_txn_id)
                if debt_result and debt_result.get("success"):
                    split_debt_lines.extend(format_split_debt_result_lines(debt_result))
                    debt_ids = [
                        x.get("debt_id")
                        for x in debt_result.get("created", [])
                        if x.get("debt_id")
                    ]
                    if source_txn_id and debt_ids:
                        relation_result = update_transaction_debt_relation(
                            source_txn_id,
                            debt_ids,
                            tipe_hutang="piutang",
                        )
                        if not relation_result.get("success"):
                            result.setdefault("failed_items", []).append({
                                "raw": item.get("raw", "split bill"),
                                "message": f"Piutang dibuat, tapi relasi transaksi gagal: {relation_result.get('message')}",
                            })
                elif debt_result:
                    result.setdefault("failed_items", []).append({
                        "raw": item.get("raw", "split bill"),
                        "message": debt_result.get("message", "Gagal membuat piutang split bill."),
                    })

            if split_debt_lines:
                lines.append("\n🤝 *Piutang split bill dibuat:*")
                lines.extend(split_debt_lines)

            new_balances = result.get("new_balances", {})
            if new_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                for account_name, balance in new_balances.items():
                    lines.append(f"• {account_name}: *{format_rupiah(balance)}*")

            failed_items = result.get("failed_items", [])
            if failed_items:
                lines.append("\n❌ *Catatan/Gagal:*")
                for item in failed_items:
                    lines.append(f"• `{item['raw']}` — {item['message']}")

            budget_messages = []
            checked_categories = set()

            for item in batch:
                parsed = item["parsed"]
                category = parsed.get("category")

                if parsed.get("type") != "expense" or not category:
                    continue

                if category in checked_categories:
                    continue

                checked_categories.add(category)

                budget_check = check_budget_after_transaction(category)
                if budget_check and budget_check.get("alert"):
                    budget_messages.append(
                        f"{budget_check['emoji']} *Budget {category}*: "
                        f"{budget_check['pct_used']}% terpakai"
                    )

            if budget_messages:
                lines.append("\n⚠️ *Budget Alert:*")
                lines.extend(budget_messages)

            if result.get("message") and result.get("message") != "ok":
                lines.append(f"\n⚠️ {result['message']}")

            await safe_edit_message(query, 
                "\n".join(lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_debt_batch", None)
            return

        parsed = context.user_data.get("pending_parsed")
        raw = context.user_data.get("pending_raw", "")

        if not parsed:
            await safe_edit_message(query, "❌ Sesi expired. Coba input ulang.")
            return

        await safe_edit_message(query, 
            "⏳ *Sedang menyimpan transaksi...*",
            parse_mode="Markdown",
        )

        result = save_transaction(parsed, raw_input=raw)

        if result["success"]:
            balance_info = ""
            if result.get("new_balance") is not None:
                balance_account = (
                    result.get("new_balance_account")
                    or parsed.get("to_account")
                    or parsed.get("account")
                    or "-"
                )
                balance_info = (
                    f"\n💳 Saldo {md_safe(balance_account)}: "
                    f"*{format_rupiah(result['new_balance'])}*"
                )

            split_info = ""
            split_debt = create_split_bill_debt(parsed, raw, source_transaction_id=result.get("transaction_id", ""))
            if split_debt and split_debt.get("success"):
                split_lines = format_split_debt_result_lines(split_debt)
                split_info = "\n\n🤝 *Piutang split bill dibuat*\n" + "\n".join(split_lines)

                debt_ids = [
                    x.get("debt_id")
                    for x in split_debt.get("created", [])
                    if x.get("debt_id")
                ]
                if result.get("transaction_id") and debt_ids:
                    relation_result = update_transaction_debt_relation(
                        result.get("transaction_id"),
                        debt_ids,
                        tipe_hutang="piutang",
                    )
                    if not relation_result.get("success"):
                        split_info += (
                            "\n⚠️ Piutang dibuat, tapi relasi transaksi gagal: "
                            f"{relation_result.get('message')}"
                        )
            elif split_debt:
                split_info = f"\n\n⚠️ Gagal membuat piutang split bill: {split_debt.get('message')}"

            budget_info = ""
            if parsed.get("type") == "expense" and parsed.get("category"):
                budget_check = check_budget_after_transaction(parsed["category"])
                if budget_check:
                    budget_info = (
                        f"\n\n{budget_check['emoji']} *Budget {parsed['category']}*\n"
                        f"Terpakai: {format_rupiah(budget_check['actual'])} "
                        f"/ {format_rupiah(budget_check['budget'])} "
                        f"({budget_check['pct_used']}%)\n"
                        f"Sisa: {format_rupiah(budget_check['remaining'])}"
                    )
                    if budget_check["alert"]:
                        budget_info += f"\n\n{budget_check['alert_msg']}"

            await safe_edit_message(query, 
                f"✅ *Transaksi tersimpan!*\n"
                f"🔖 ID: `{result['transaction_id']}`"
                f"{balance_info}"
                f"{split_info}"
                f"{budget_info}",
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_debt_batch", None)
            return

        await safe_edit_message(query, 
            f"❌ Gagal menyimpan: {result['message']}"
        )
        return

    if data.startswith("cancel"):
        context.user_data.pop("pending_parsed", None)
        context.user_data.pop("pending_raw", None)
        context.user_data.pop("pending_batch", None)
        context.user_data.pop("pending_debt", None)
        context.user_data.pop("pending_debt_batch", None)
        context.user_data.pop("pending_mixed", None)
        context.user_data.pop("pending_payment", None)
        context.user_data.pop("pending_delete_refs", None)
        context.user_data.pop("pending_delete_txn_ids", None)
        context.user_data.pop("pending_edit_txn", None)
        context.user_data.pop("pending_bulk_edit_txns", None)
        context.user_data.pop("pending_debt_void", None)
        context.user_data.pop("pending_debt_settle", None)
        context.user_data.pop("pending_asset_price", None)
        context.user_data.pop("pending_asset_confirm", None)
        context.user_data.pop("pending_asset_add_flow", None)
        context.user_data.pop("pending_expense_confirm", None)
        context.user_data.pop("pending_preview_edit", None)
        context.user_data.pop("pending_missing_amount", None)
        context.user_data.pop("pending_parse_clarification", None)
        context.user_data.pop("mixed_review_preview_sent", None)

        await safe_edit_message(query, "❌ Input dibatalkan.")
        return

    if data.startswith("pay_debt:"):
        parts = data.split(":")
        debt_id = parts[1]
        amount = float(parts[2])

        result = add_payment(debt_id, amount)

        if result["success"]:
            pending = context.user_data.get("pending_payment", {})
            person = pending.get("person", "")

            if result["is_settled"]:
                msg = (
                    f"✅ *Hutang ke {person} LUNAS!*\n"
                    f"💰 Dibayar: {format_rupiah(amount)}"
                )
            else:
                msg = (
                    f"✅ *Pembayaran dicatat!*\n\n"
                    f"👤 Kepada : {person}\n"
                    f"💰 Dibayar: {format_rupiah(amount)}\n"
                    f"📊 Sisa   : {format_rupiah(result['remaining'])}"
                )

            await safe_edit_message(query, msg, parse_mode="Markdown")
            context.user_data.pop("pending_payment", None)
            return

        await safe_edit_message(query, 
            f"❌ Gagal: {result['message']}"
        )
        return

    await safe_edit_message(query, "❌ Tombol tidak dikenali atau sesi sudah tidak valid.")

