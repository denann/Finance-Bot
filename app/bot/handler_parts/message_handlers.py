"""Natural message handler that routes text and image input into parser, preview, clarification, debt, split bill, pending, or AI flows."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *
from app.bot.handler_parts.common_imports import _safe_float_for_display

from app.bot.handler_parts.networth_assets import (
    build_asset_confirm_preview,
    build_asset_unit_price_prompt,
    handle_pending_asset_add_flow,
    parse_natural_asset_add,
)
from app.bot.handler_parts.command_router import (
    build_delete_preview_text,
    build_gemini_fallback_text,
    build_gemini_low_confidence_text,
    build_last_transactions_text,
    extract_edit_updates_from_router,
    maybe_text_is_command_typo,
    resolve_txn_refs_from_last,
    router_args_to_last_filter,
)
from app.bot.handler_parts.transaction_flow import (
    attach_split_bill_if_any,
    build_debt_account_prompt,
    build_debt_initial_preview,
    build_debt_only_confirm_preview,
    build_mixed_account_prompt,
    build_mixed_detail_preview,
    build_mixed_final_summary,
    build_single_account_prompt,
    build_missing_amount_prompt,
    build_mixed_preview,
    build_parse_clarification_prompt,
    build_preview_with_parse_safety,
    build_pending_expense_confirm_preview,
    build_mixed_split_bill_queue_prompt,
    build_preview,
    build_receipt_account_prompt,
    build_receipt_final_preview,
    build_receipt_partial_mixed_items,
    build_receipt_part_selection_prompt,
    build_receipt_review_text,
    build_receipt_selected_breakdown,
    parse_preview_direct_field_update,
    is_receipt_image_result,
    parse_receipt_divisor,
    parse_receipt_part_selection,
    receipt_extra_charge_net_amount,
    build_split_bill_prompt_from_parsed,
    debt_uses_cashflow,
    enrich_ditalangin_split_bill_if_any,
    edit_or_continue_keyboard,
    preview_action_keyboard,
    preview_action_question,
    single_ready_to_save,
    mixed_ready_to_save,
    debt_ready_to_save,
    handle_pending_missing_amount,
    handle_pending_preview_edit,
    mixed_needs_account,
    mixed_split_bill_keyboard,
    mixed_split_bill_needs_decision,
    needs_account,
    parse_clarification_keyboard,
    parse_income_missing_amount,
    parse_input,
    parse_mixed_item,
    split_bill_keyboard,
    split_bill_needs_decision,
    split_user_inputs,
    build_meal_split_custom_allocation_prompt,
    build_meal_split_status_prompt,
    build_social_spending_guard_prompt,
    detect_social_spending_ambiguity,
    meal_split_status_keyboard,
    parse_meal_split_allocation,
    social_spending_guard_keyboard,
)
from app.bot.handler_parts.command_handlers import (
    budget_history_handler,
    build_pending_expense_lines,
    format_budget_net_gross,
    bulanan_handler,
    handle_natural_debt_settle,
    handle_natural_finance_question,
    harian_handler,
    help_handler,
    hutang_handler,
    mingguan_handler,
    saldo_handler,
)
from app.nlp.gemini_parser import parse_with_gemini
from app.nlp.regex_parser import detect_account, extract_debt_account
from app.nlp.parse_safety import (
    CLARIFICATION,
    GEMINI_DRAFT_PREVIEW,
    WARNING_PREVIEW,
    assess_parse_safety,
)

async def send_parse_clarification(update: Update, context: ContextTypes.DEFAULT_TYPE, raw: str, parsed: dict | None, assessment: dict) -> None:
    """Ask the user to clarify a risky or ambiguous parse result.

    Args:
        update: Telegram update that contains the original user message.
        context: Telegram context used to store the clarification session.
        raw: Original user input.
        parsed: Parser output available before clarification, if any.
        assessment: Parse safety result that explains why clarification is needed.

    Notes:
        This function updates `context.user_data` and sends a Telegram message.
        It does not save transactions.
    """
    context.user_data["pending_parse_clarification"] = {
        "raw": raw,
        "parsed": parsed or {},
        "assessment": assessment or {},
    }
    context.user_data.pop("pending_parsed", None)
    context.user_data.pop("pending_raw", None)
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt", None)
    context.user_data.pop("pending_debt_batch", None)
    context.user_data.pop("pending_mixed", None)

    await update.message.reply_text(
        build_parse_clarification_prompt(raw, assessment),
        parse_mode="Markdown",
        reply_markup=parse_clarification_keyboard(),
    )


def try_gemini_draft_for_parse_safety(raw: str, fallback_parsed: dict, assessment: dict) -> tuple[dict, dict, bool]:
    """Try Gemini as a draft parser when parse safety asks for a safer preview.

    Args:
        raw: Original user input.
        fallback_parsed: Local parser result used when Gemini cannot produce a
            better draft.
        assessment: Existing parse safety assessment.

    Returns:
        A tuple of `(parsed, updated_assessment, gemini_used)`.

    Notes:
        Gemini output is still treated as a draft. The user must confirm it
        before anything is saved.
    """
    if str((fallback_parsed or {}).get("parsed_by") or "").strip().lower() == "gemini":
        draft_assessment = dict(assessment or {})
        reasons = list(draft_assessment.get("reasons") or [])
        if "Draft transaksi dibuat oleh Gemini dan belum disimpan." not in reasons:
            reasons.append("Draft transaksi dibuat oleh Gemini dan belum disimpan.")
        draft_assessment["reasons"] = reasons
        draft_assessment["recommended_action"] = GEMINI_DRAFT_PREVIEW
        return fallback_parsed, draft_assessment, True

    gemini_parsed = parse_with_gemini(raw)
    if not gemini_parsed:
        fallback_assessment = dict(assessment or {})
        reasons = list(fallback_assessment.get("reasons") or [])
        if "Gemini belum berhasil membuat draft, jadi preview memakai hasil parser lokal." not in reasons:
            reasons.append("Gemini belum berhasil membuat draft, jadi preview memakai hasil parser lokal.")
        fallback_assessment["reasons"] = reasons
        fallback_assessment["recommended_action"] = WARNING_PREVIEW
        return fallback_parsed, fallback_assessment, False

    attach_split_bill_if_any(gemini_parsed, raw)
    draft_assessment = dict(assessment or {})
    reasons = list(draft_assessment.get("reasons") or [])
    if "Draft transaksi dibuat oleh Gemini dan belum disimpan." not in reasons:
        reasons.append("Draft transaksi dibuat oleh Gemini dan belum disimpan.")
    draft_assessment["reasons"] = reasons
    draft_assessment["recommended_action"] = GEMINI_DRAFT_PREVIEW
    return gemini_parsed, draft_assessment, True


async def debt_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle natural-language debt input before it reaches the normal parser.

    Args:
        update: Telegram update that contains the user message.
        context: Telegram context used to store pending debt state.

    Returns:
        True when the input is handled as debt, otherwise False.

    Notes:
        This handler only creates a pending preview or asks for missing
        information. Saving debt and cashflow still happens later through
        confirmation callbacks.
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return True

    text = update.message.text.strip()
    debt_parsed = parse_debt_input(text)

    if not debt_parsed:
        return False

    # Debt flow section
    # Debt flow section
    # "ditalangin Alpat beli minyak 46k dibagi 4 sama Alpat Opik Sapto"
    # Split bill parsing note: separate the paid transaction from each person share.
    # Implementation section
    debt_parsed = enrich_ditalangin_split_bill_if_any(debt_parsed, text)
    if debt_parsed and not debt_parsed.get("account"):
        debt_account = extract_debt_account(text) or detect_account(text)
        if debt_account:
            debt_parsed["account"] = debt_account

    person = debt_parsed.get("person_name")
    intent = debt_parsed.get("intent")

    if not person:
        if intent == "add_payable":
            await update.message.reply_text(
                "❓ Siapa yang Anda hutangi?\n"
                "Contoh: `hutang ke Budi 500rb buat makan`",
                parse_mode="Markdown",
            )
            return True

        if intent == "add_receivable":
            await update.message.reply_text(
                "❓ Siapa yang meminjam uang ke Anda?\n"
                "Contoh: `Budi minjem 300rb`",
                parse_mode="Markdown",
            )
            return True

        if intent == "add_payment":
            await update.message.reply_text(
                "❓ Pembayaran ini terkait siapa?\n"
                "Contoh: `Budi bayar 300rb` atau `bayar hutang Budi 300rb`",
                parse_mode="Markdown",
            )
            return True

    context.user_data["pending_debt"] = debt_parsed
    context.user_data.pop("pending_parsed", None)
    context.user_data.pop("pending_raw", None)
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt_batch", None)

    intent = debt_parsed.get("intent")
    if debt_uses_cashflow(debt_parsed) and intent != "offset_debt" and not debt_parsed.get("account"):
        await update.message.reply_text(
            build_debt_account_prompt(debt_parsed),
            parse_mode="Markdown",
            reply_markup=account_keyboard("debt_acc"),
        )
        return True

    await update.message.reply_text(
        f"{build_debt_initial_preview(debt_parsed)}\n\n{preview_action_question(True)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("debt", True),
    )

    return True

async def handle_gemini_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Helper for handle gemini intent in the Telegram bot flow."""
    if not should_try_gemini_intent_router(user_text):
        return False

    router_result = route_intent_with_gemini(user_text)

    intent = router_result.get("intent", "unknown")
    confidence = float(router_result.get("confidence", 0) or 0)
    args = router_result.get("args", {}) or {}

    if confidence < GEMINI_INTENT_CONFIDENCE_CLARIFY:
        return False

    if confidence < GEMINI_INTENT_CONFIDENCE_EXECUTE:
        await update.message.reply_text(
            build_gemini_low_confidence_text(router_result),
            parse_mode="Markdown",
        )
        return True

    # ── Non-destructive intents ───────────────────────────────────────────────

    if intent == "help":
        await help_handler(update, context)
        return True

    if intent == "saldo":
        await saldo_handler(update, context)
        return True

    if intent == "harian":
        await harian_handler(update, context)
        return True

    if intent == "mingguan":
        await mingguan_handler(update, context)
        return True

    if intent == "bulanan":
        await bulanan_handler(update, context)
        return True

    if intent == "hutang":
        await hutang_handler(update, context)
        return True

    if intent == "budget_history":
        await budget_history_handler(update, context)
        return True

    if intent == "last":
        limit, period, month, title = router_args_to_last_filter(args)

        transactions = get_recent_transactions(
            limit=limit,
            period=period,
            month=month,
        )

        if not transactions:
            await update.message.reply_text(
                f"📭 Tidak ada transaksi untuk filter: *{title}*",
                parse_mode="Markdown",
            )
            return True

        last_map = {}

        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, title),
            parse_mode="Markdown",
        )
        return True

    if intent == "cari":
        query = str(args.get("query") or "").strip()

        if not query:
            await update.message.reply_text(
                "🔍 Mau cari transaksi apa?\n\n"
                "Contoh:\n"
                "`cari kopi`\n"
                "`/cari kopi`",
                parse_mode="Markdown",
            )
            return True

        results = search_transactions(query)

        if not results:
            await update.message.reply_text(
                f"🔍 Tidak ada transaksi dengan keyword *{md_safe(query)}*.",
                parse_mode="Markdown",
            )
            return True

        lines = [f"🔍 *Hasil pencarian: \"{md_safe(query)}\"*\n"]

        for t in results:
            icon = "➕" if t.get("type") == "income" else "➖" if t.get("type") == "expense" else "🔄"
            lines.append(
                f"{icon} {md_safe(t.get('date') or '-')} — {md_safe(t.get('description') or '-')}\n"
                f"   *{format_rupiah(float(t.get('amount', 0) or 0))}* | {md_safe(t.get('category') or '-')}"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    if intent == "budget":
        month = args.get("month")

        try:
            normalized_month = normalize_month(month)
        except Exception:
            normalized_month = normalize_month(None)

        summary = get_budget_summary(normalized_month)

        if not summary:
            await update.message.reply_text(
                f"📭 Belum ada budget untuk *{format_month_label(normalized_month)}*.\n\n"
                "Set budget dengan cara:\n"
                "`budget makan 1.5 juta`\n"
                "`budget transport 300rb`\n"
                "`budget makan 1.5 juta 2026-07`",
                parse_mode="Markdown",
            )
            return True

        total_budget = sum(float(item.get("budget", 0) or 0) for item in summary)
        total_actual = sum(float(item.get("actual", 0) or 0) for item in summary)
        total_gross_actual = sum(float(item.get("actual_gross", item.get("actual", 0)) or 0) for item in summary)
        total_remaining = total_budget - total_actual
        total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0

        lines = [f"📊 *Budget {format_month_label(normalized_month)}*\n"]
        lines.append(f"💰 Total Budget : *{format_rupiah(total_budget)}*")
        lines.append(f"💸 Realisasi Bersih (Gross): *{format_budget_net_gross(total_actual, total_gross_actual)}*")
        lines.append(f"📌 Sisa         : *{format_rupiah(total_remaining)}*")
        lines.append(f"📈 Terpakai     : *{total_pct:.1f}%*\n")

        for item in summary:
            bar = build_progress_bar(item["pct_used"])
            remaining_label = "Sisa" if item["remaining"] >= 0 else "Over"

            lines.append(
                f"{item['emoji']} *{item['category']}*\n"
                f"  {bar} {item['pct_used']}%\n"
                f"  Pakai Bersih (Gross): {format_budget_net_gross(item.get('actual', 0), item.get('actual_gross', item.get('actual', 0)))} / {format_rupiah(item['budget'])}\n"
                f"  {remaining_label}: {format_rupiah(abs(item['remaining']))}\n"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    # ── Destructive intents: preview only ─────────────────────────────────────

    if intent == "delete_txn":
        ref = str(args.get("ref") or "").strip()

        if not ref:
            await update.message.reply_text(
                "❌ Saya menangkap intent hapus transaksi, tapi nomor/ID transaksinya belum jelas.\n\n"
                "Contoh:\n"
                "`hapus transaksi nomor 2`\n"
                "`/delete_txn 2`",
                parse_mode="Markdown",
            )
            return True

        resolved = resolve_txn_refs_from_last(context, [ref])

        if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
            await update.message.reply_text(
                "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
                "Jalankan dulu:\n"
                "`/last`\n\n"
                "Lalu coba lagi:\n"
                "`hapus transaksi nomor 2`",
                parse_mode="Markdown",
            )
            return True

        preview = preview_delete_transactions_by_refs(
            row_indices=resolved["row_indices"],
            txn_ids=resolved["txn_ids"],
        )

        if not preview.get("deletable"):
            await update.message.reply_text(
                build_delete_preview_text(preview),
                parse_mode="Markdown",
            )
            return True

        context.user_data["pending_delete_refs"] = {
            "row_indices": [
                int(txn.get("_row_index"))
                for txn in preview.get("deletable", [])
                if txn.get("_row_index")
            ],
            "txn_ids": [],
        }

        await update.message.reply_text(
            build_delete_preview_text(preview),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("delete_txns"),
        )
        return True

    if intent == "edit_txn":
        ref = str(args.get("ref") or "").strip()
        updates = extract_edit_updates_from_router(args)

        if not ref:
            await update.message.reply_text(
                "❌ Saya menangkap intent edit transaksi, tapi nomor/ID transaksinya belum jelas.\n\n"
                "Contoh:\n"
                "`edit transaksi nomor 2 jadi 15000`\n"
                "`/edit_txn 2 amount=15000`",
                parse_mode="Markdown",
            )
            return True

        if not updates:
            await update.message.reply_text(
                "❌ Saya menangkap intent edit transaksi, tapi field yang diedit belum jelas.\n\n"
                "Contoh:\n"
                "`edit transaksi nomor 2 jadi 15000`\n"
                "`edit transaksi nomor 2 deskripsinya Kopi susu`",
                parse_mode="Markdown",
            )
            return True

        # Implementation note for this project-specific finance flow.
        # Split bill parsing note: separate the paid transaction from each person share.
        resolved = resolve_txn_refs_from_last(context, [ref])

        if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
            await update.message.reply_text(
                "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
                "Jalankan dulu:\n"
                "`/last`\n\n"
                "Lalu coba lagi:\n"
                "`edit transaksi nomor 2 jadi 15000`",
                parse_mode="Markdown",
            )
            return True

        row_index = resolved["row_indices"][0] if resolved["row_indices"] else None
        txn_id = resolved["txn_ids"][0] if resolved["txn_ids"] else None

        try:
            preview = preview_edit_transaction_by_ref(
                updates=updates,
                row_index=row_index,
                txn_id=txn_id,
            )
        except NameError:
            await update.message.reply_text(
                "❌ Gemini sudah menangkap intent edit, tapi fitur `/edit_txn` belum terpasang penuh di kode.\n\n"
                "Pasang Phase `edit_txn` dulu, lalu fitur natural edit bisa aktif.",
                parse_mode="Markdown",
            )
            return True

        if not preview.get("success"):
            await update.message.reply_text(
                f"❌ {preview.get('message')}",
                parse_mode="Markdown",
            )
            return True

        context.user_data["pending_edit_txn"] = {
            "row_index": row_index,
            "txn_id": txn_id,
            "updates": updates,
        }

        await update.message.reply_text(
            build_edit_preview_text(preview),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("edit_txn"),
        )
        return True

    return False


def normalize_text_command(text: str) -> str:
    """Normalize and clean input for text command."""
    clean = str(text or "").strip().lower()
    clean = re.sub(r"\s+", " ", clean)
    return clean


async def handle_local_natural_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Helper for handle local natural intent in the Telegram bot flow."""
    clean = normalize_text_command(user_text)

    if not clean:
        return False

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    has_amount = bool(
        re.search(
            r"\b\d+(?:[.,]\d+)?\s*(rb|ribu|k|jt|juta)?\b",
            clean,
            flags=re.IGNORECASE,
        )
    )

    if has_amount:
        return False

    # ── Balance flow ─────────────────────────────────────────────────────────────
    saldo_patterns = {
        "cek saldo",
        "lihat saldo",
        "tampilkan saldo",
        "saldo",
    }

    if clean in saldo_patterns:
        await saldo_handler(update, context)
        return True

    # Debt flow section
    hutang_patterns = {
        "cek hutang",
        "cek utang",
        "lihat hutang",
        "lihat utang",
        "tampilkan hutang",
        "tampilkan utang",
        "cek piutang",
        "lihat piutang",
        "tampilkan piutang",
        "cek hutang piutang",
        "lihat hutang piutang",
        "lihat utang piutang",
        "hutang",
        "utang",
        "piutang",
    }

    if clean in hutang_patterns:
        await hutang_handler(update, context)
        return True

    # ── Budget ───────────────────────────────────────────────────────────────
    budget_patterns = {
        "cek budget",
        "lihat budget",
        "tampilkan budget",
        "cek budget bulan ini",
        "lihat budget bulan ini",
        "tampilkan budget bulan ini",
        "budget bulan ini",
    }

    if clean in budget_patterns:
        summary = get_budget_summary(normalize_month(None))

        if not summary:
            month = normalize_month(None)
            await update.message.reply_text(
                f"📭 Belum ada budget untuk *{format_month_label(month)}*.\n\n"
                "Set budget dengan cara:\n"
                "`budget makan 1.5 juta`\n"
                "`budget transport 300rb`",
                parse_mode="Markdown",
            )
            return True

        month = normalize_month(None)
        total_budget = sum(float(item.get("budget", 0) or 0) for item in summary)
        total_actual = sum(float(item.get("actual", 0) or 0) for item in summary)
        total_gross_actual = sum(float(item.get("actual_gross", item.get("actual", 0)) or 0) for item in summary)
        total_remaining = total_budget - total_actual
        total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0

        lines = [f"📊 *Budget {format_month_label(month)}*\n"]
        lines.append(f"💰 Total Budget : *{format_rupiah(total_budget)}*")
        lines.append(f"💸 Realisasi Bersih (Gross): *{format_budget_net_gross(total_actual, total_gross_actual)}*")
        lines.append(f"📌 Sisa         : *{format_rupiah(total_remaining)}*")
        lines.append(f"📈 Terpakai     : *{total_pct:.1f}%*\n")

        for item in summary:
            bar = build_progress_bar(item["pct_used"])
            remaining_label = "Sisa" if item["remaining"] >= 0 else "Over"

            lines.append(
                f"{item['emoji']} *{md_safe(item['category'])}*\n"
                f"  {bar} {item['pct_used']}%\n"
                f"  Pakai Bersih (Gross): {format_budget_net_gross(item.get('actual', 0), item.get('actual_gross', item.get('actual', 0)))} / {format_rupiah(item['budget'])}\n"
                f"  {remaining_label}: {format_rupiah(abs(item['remaining']))}\n"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    # ── Latest transaction history flow ───────────────────────────────────────
    last_patterns = {
        "lihat transaksi",
        "lihat transaksi terakhir",
        "tampilkan transaksi",
        "tampilkan transaksi terakhir",
        "lihat histori",
        "lihat history",
        "histori transaksi",
        "history transaksi",
    }

    if clean in last_patterns:
        transactions = get_recent_transactions(limit=10)

        if not transactions:
            await update.message.reply_text("📭 Belum ada transaksi.")
            return True

        last_map = {}
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Terakhir"),
            parse_mode="Markdown",
        )
        return True

    today_patterns = {
        "lihat transaksi hari ini",
        "tampilkan transaksi hari ini",
        "transaksi hari ini",
        "histori hari ini",
        "history hari ini",
    }

    if clean in today_patterns:
        transactions = get_recent_transactions(limit=10, period="today")

        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi hari ini.")
            return True

        last_map = {}
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Hari Ini"),
            parse_mode="Markdown",
        )
        return True

    week_patterns = {
        "lihat transaksi minggu ini",
        "tampilkan transaksi minggu ini",
        "transaksi minggu ini",
        "histori minggu ini",
        "history minggu ini",
    }

    if clean in week_patterns:
        transactions = get_recent_transactions(limit=10, period="week")

        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi minggu ini.")
            return True

        last_map = {}
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Minggu Ini"),
            parse_mode="Markdown",
        )
        return True

    month_patterns = {
        "lihat transaksi bulan ini",
        "tampilkan transaksi bulan ini",
        "transaksi bulan ini",
        "histori bulan ini",
        "history bulan ini",
    }

    if clean in month_patterns:
        transactions = get_recent_transactions(limit=10, period="month")

        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi bulan ini.")
            return True

        last_map = {}
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Bulan Ini"),
            parse_mode="Markdown",
        )
        return True

    # ── Transaction search flow ───────────────────────────────────────────────
    # Implementation note for this project-specific finance flow.
    # cari kopi
    # search kopi
    if clean.startswith("cari ") or clean.startswith("search "):
        keyword = clean.split(" ", 1)[1].strip()

        if not keyword:
            await update.message.reply_text(
                "🔍 Mau cari transaksi apa?\n\n"
                "Contoh:\n"
                "`cari kopi`",
                parse_mode="Markdown",
            )
            return True

        results = search_transactions(keyword)

        if not results:
            await update.message.reply_text(
                f"🔍 Tidak ada transaksi dengan keyword *{md_safe(keyword)}*.",
                parse_mode="Markdown",
            )
            return True

        lines = [f"🔍 *Hasil pencarian: \"{md_safe(keyword)}\"*\n"]

        for t in results:
            icon = "➕" if t.get("type") == "income" else "➖" if t.get("type") == "expense" else "🔄"
            lines.append(
                f"{icon} {md_safe(t.get('date'))} — {md_safe(t.get('description', '-'))}\n"
                f"   *{format_rupiah(float(t.get('amount', 0) or 0))}* | {md_safe(t.get('category', '-'))}"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    return False



# ── Receipt Selection Follow-up Handler ───────────────────────────────────────

async def _continue_receipt_batch_after_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, mixed_items: list[dict], receipt_context: dict) -> None:
    """Continue a receipt-derived batch after item selection is complete."""
    context.user_data["pending_mixed"] = mixed_items
    context.user_data["pending_receipt_context"] = receipt_context
    context.user_data.pop("pending_parsed", None)
    context.user_data.pop("pending_raw", None)
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt", None)
    context.user_data.pop("pending_debt_batch", None)
    context.user_data.pop("pending_receipt_part_selection", None)
    context.user_data.pop("pending_receipt_extra_divisor", None)
    context.user_data.pop("mixed_review_preview_sent", None)

    preview = build_mixed_detail_preview(mixed_items, receipt_context)
    await reply_update_safely(
        update,
        f"{preview}\n\n{preview_action_question(False)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("mixed", False),
    )


async def handle_pending_receipt_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Handle text replies for the partial receipt flow.

    Args:
        update: Telegram update that contains the user's selection or divisor.
        context: Telegram context where pending receipt state is stored.
        user_text: User reply for selected receipt items or extra-charge divisor.

    Returns:
        True when this function consumes the message, otherwise False.
    """
    divisor_state = context.user_data.get("pending_receipt_extra_divisor")
    if divisor_state:
        divisor = parse_receipt_divisor(user_text)
        if divisor <= 0:
            await update.message.reply_text(
                "❌ Jumlah pembaginya belum kebaca. Contoh: `dibagi 5`.",
                parse_mode="Markdown",
            )
            return True

        receipt = divisor_state.get("receipt") or {}
        selection_result = divisor_state.get("selection_result") or {}
        mixed_items, receipt_context = build_receipt_partial_mixed_items(receipt, selection_result, divisor)
        await _continue_receipt_batch_after_selection(update, context, mixed_items, receipt_context)
        return True

    selection_state = context.user_data.get("pending_receipt_part_selection")
    if not selection_state:
        return False

    receipt = selection_state.get("receipt") or {}
    items = selection_state.get("items") or []
    selection_result = parse_receipt_part_selection(user_text, items)

    if not selection_result.get("success"):
        await update.message.reply_text(
            f"❌ {selection_result.get('message')}\n\n{build_receipt_part_selection_prompt(receipt, items)}",
            parse_mode="Markdown",
        )
        return True

    if receipt_extra_charge_net_amount(receipt) > 0:
        context.user_data["pending_receipt_extra_divisor"] = {
            "receipt": receipt,
            "selection_result": selection_result,
        }
        context.user_data.pop("pending_receipt_part_selection", None)
        await reply_update_safely(
            update,
            build_receipt_selected_breakdown(receipt, selection_result),
            parse_mode="Markdown",
        )
        return True

    mixed_items, receipt_context = build_receipt_partial_mixed_items(receipt, selection_result, divisor=1)
    await _continue_receipt_batch_after_selection(update, context, mixed_items, receipt_context)
    return True


# ── Image / Receipt Handler ──────────────────────────────────────────────────

async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Telegram request for image."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    message = update.message
    if not message:
        return

    photo = message.photo[-1] if message.photo else None
    document = message.document if message.document else None

    file_id = None
    mime_type = "image/jpeg"
    file_size = 0

    if photo:
        file_id = photo.file_id
        file_size = int(photo.file_size or 0)
        mime_type = "image/jpeg"
    elif document and str(document.mime_type or "").startswith("image/"):
        file_id = document.file_id
        file_size = int(document.file_size or 0)
        mime_type = document.mime_type or "image/jpeg"
    else:
        await message.reply_text("❌ File yang dikirim belum terbaca sebagai gambar.")
        return

    # Image parsing note: receipt output still goes through preview before saving.
    if file_size and file_size > 10 * 1024 * 1024:
        await message.reply_text(
            "❌ Gambar terlalu besar. Kirim gambar di bawah 10 MB."
        )
        return

    status_msg = await message.reply_text(
        "🖼️ Membaca gambar dengan Gemini...\n"
        "Pastikan gambar tidak berisi data sensitif seperti nomor rekening lengkap, password, atau OTP."
    )

    try:
        tg_file = await context.bot.get_file(file_id)
        try:
            image_bytes = await tg_file.download_as_bytearray()
        except AttributeError:
            buffer = io.BytesIO()
            await tg_file.download_to_memory(buffer)
            image_bytes = buffer.getvalue()
    except Exception as e:
        await status_msg.edit_text(f"❌ Gagal download gambar dari Telegram: {str(e)}")
        return

    caption = message.caption or ""
    result = parse_transactions_from_image(
        bytes(image_bytes),
        mime_type=mime_type,
        caption=caption,
    )

    if not result.get("success"):
        await status_msg.edit_text(
            "🤔 Gambar belum bisa saya ubah jadi transaksi.\n\n"
            f"Detail: {result.get('message') or '-'}\n\n"
            "Coba kirim foto yang lebih jelas, atau tambahkan caption seperti:\n"
            "`beli makan dari struk ini`\n"
            "`ini pemasukan`\n"
            "`pakai BSI`",
            parse_mode="Markdown",
        )
        return

    items = result.get("items", []) or []
    receipt = result.get("receipt") or {}

    if is_receipt_image_result(result, items):
        context.user_data["pending_receipt"] = {
            "receipt": receipt,
            "items": items,
            "caption": caption or "[gambar]",
        }
        context.user_data.pop("pending_parsed", None)
        context.user_data.pop("pending_raw", None)
        context.user_data.pop("pending_batch", None)
        context.user_data.pop("pending_debt", None)
        context.user_data.pop("pending_debt_batch", None)
        context.user_data.pop("pending_mixed", None)
        context.user_data.pop("pending_receipt_context", None)
        context.user_data.pop("pending_receipt_part_selection", None)
        context.user_data.pop("pending_receipt_extra_divisor", None)
        context.user_data.pop("mixed_review_preview_sent", None)

        await edit_message_safely(
            status_msg,
            build_receipt_review_text(receipt, items),
            parse_mode="Markdown",
            reply_markup=receipt_ownership_keyboard(),
        )
        return

    # Image parsing note: non-itemized images still use the regular single/mixed preview flow.
    if len(items) == 1:
        parsed = items[0]
        attach_split_bill_if_any(parsed, caption or "")
        context.user_data["pending_parsed"] = parsed
        context.user_data["pending_raw"] = caption or "[gambar]"
        context.user_data.pop("pending_batch", None)
        context.user_data.pop("pending_debt", None)
        context.user_data.pop("pending_debt_batch", None)
        context.user_data.pop("pending_mixed", None)

        if split_bill_needs_decision(parsed):
            await status_msg.edit_text(
                build_split_bill_prompt_from_parsed(parsed),
                parse_mode="Markdown",
                reply_markup=split_bill_keyboard("single"),
            )
            return

        if needs_account(parsed):
            await status_msg.edit_text(
                build_single_account_prompt(parsed),
                parse_mode="Markdown",
                reply_markup=account_keyboard("acc"),
            )
            return

        preview = build_preview(parsed)
        await status_msg.edit_text(
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("single", True),
        )
        return

    # Image parsing note: receipt output still goes through preview before saving.
    mixed_items = []
    for idx, parsed in enumerate(items, 1):
        raw_item = f"gambar item {idx}"
        attach_split_bill_if_any(parsed, caption or raw_item)
        mixed_items.append({
            "kind": "transaction",
            "parsed": parsed,
            "raw": raw_item,
        })

    context.user_data["pending_mixed"] = mixed_items
    context.user_data.pop("pending_parsed", None)
    context.user_data.pop("pending_raw", None)
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt", None)
    context.user_data.pop("pending_debt_batch", None)
    context.user_data.pop("mixed_review_preview_sent", None)

    preview = build_mixed_detail_preview(mixed_items)

    if mixed_split_bill_needs_decision(mixed_items):
        await edit_message_safely(
            status_msg,
            build_mixed_split_bill_queue_prompt(mixed_items),
            parse_mode="Markdown",
            reply_markup=mixed_split_bill_keyboard(mixed_items),
        )
    else:
        await edit_message_safely(
            status_msg,
            f"{preview}\n\n{preview_action_question(False)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", False),
        )

# Message handling section

# Implementation section
# Debt flow section

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route natural text input into the correct bot flow.

    Args:
        update: Telegram update that contains the user message.
        context: Telegram context used to store pending flow state.

    Notes:
        This handler routes input into edit sessions, asset flow, debt flow,
        pending expense, parser flow, parse safety, or AI fallback. It may send
        Telegram replies and update `context.user_data`, but transaction saving
        still requires a confirmation callback.
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    user_text = update.message.text.strip()

    if user_text.startswith("/"):
        await update.message.reply_text(
            "⚠️ Input ini terlihat seperti command, jadi tidak saya parse sebagai transaksi.\n\n"
            "Cek command dengan `/help`, atau tulis transaksi tanpa awalan `/`." ,
            parse_mode="Markdown",
        )
        return

    receipt_selection_handled = await handle_pending_receipt_selection(update, context, user_text)
    if receipt_selection_handled:
        return

    missing_amount_handled = await handle_pending_missing_amount(update, context, user_text)
    if missing_amount_handled:
        return

    meal_split_state = context.user_data.get("pending_meal_split") or {}
    if meal_split_state.get("stage") == "custom_allocation":
        shares = parse_meal_split_allocation(
            user_text,
            float(meal_split_state.get("amount") or 0),
            meal_split_state.get("people") or [],
        )
        if not shares:
            await update.message.reply_text(
                "❌ Pembagian belum kebaca. Tulis dalam format seperti `saya 30k, Budi 50k` atau `saya 100%, Budi 100%`.",
                parse_mode="Markdown",
            )
            return

        meal_split_state["shares"] = shares
        meal_split_state["allocation_mode"] = "custom"
        meal_split_state["stage"] = "status"
        context.user_data["pending_meal_split"] = meal_split_state
        await update.message.reply_text(
            build_meal_split_status_prompt(meal_split_state),
            parse_mode="Markdown",
            reply_markup=meal_split_status_keyboard(meal_split_state.get("payer") or "self"),
        )
        return

    preview_edit_handled = await handle_pending_preview_edit(update, context, user_text)
    if preview_edit_handled:
        return

    asset_add_flow_handled = await handle_pending_asset_add_flow(update, context, user_text)
    if asset_add_flow_handled:
        return

    # Pending expense section
    pending_asset = context.user_data.get("pending_asset_price")
    if pending_asset:
        unit_price = parse_human_amount(user_text)

        if unit_price <= 0:
            await update.message.reply_text(
                "❌ Harga satuan belum valid.\n\n"
                "Balas dengan angka, contoh: `2410000`, `2.41 juta`, atau `8000000`.",
                parse_mode="Markdown",
            )
            return

        pending_asset["price_per_unit"] = unit_price
        pending_asset["needs_unit_price"] = False

        quantity = float(pending_asset.get("quantity", 0) or 0)
        pending_asset["amount"] = quantity * unit_price

        context.user_data["pending_asset_confirm"] = pending_asset
        context.user_data.pop("pending_asset_price", None)

        await update.message.reply_text(
            f"{build_asset_confirm_preview(pending_asset)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("asset", True),
        )
        return

    # Asset flow section
    natural_asset = parse_natural_asset_add(user_text)
    if natural_asset:
        if natural_asset.get("needs_unit_price"):
            context.user_data["pending_asset_price"] = natural_asset
            await update.message.reply_text(
                build_asset_unit_price_prompt(natural_asset),
                parse_mode="Markdown",
            )
            return

        context.user_data["pending_asset_confirm"] = natural_asset
        context.user_data.pop("pending_asset_price", None)
        await update.message.reply_text(
            f"{build_asset_confirm_preview(natural_asset)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("asset", True),
        )
        return

    social_guard = detect_social_spending_ambiguity(user_text)
    if social_guard:
        context.user_data["pending_social_spending_guard"] = social_guard
        context.user_data.pop("pending_parsed", None)
        context.user_data.pop("pending_debt", None)
        await update.message.reply_text(
            build_social_spending_guard_prompt(user_text, social_guard),
            parse_mode="Markdown",
            reply_markup=social_spending_guard_keyboard(),
        )
        return

    # Natural input section
    # Implementation section
    # Debt flow section
    #
    # Implementation section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    #
    # Jadi:
    # Debt flow section
    # Account flow section
    # - "cari kopi" -> search
    # Implementation section
    local_natural_handled = await handle_local_natural_intent(
        update,
        context,
        user_text,
    )

    if local_natural_handled:
        return

    # Pending expense section
    # Implementation note for this project-specific finance flow.
    # - nanti perlu bayar wisuda 750k
    # - perlu 750k create bayar wisuda
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    #
    # Implementation section
    # Pending expense section
    if is_pending_expense_text(user_text):
        try:
            item = build_pending_expense_from_text(user_text)
        except Exception as e:
            await update.message.reply_text(
                f"❌ Gagal membaca pending expense: {md_safe(str(e))}\n\n"
                "Contoh:\n"
                "`nanti perlu bayar wisuda 750k`\n"
                "`nanti perlu service motor 300k tgl 30`\n"
                "`perlu 750k buat bayar wisuda`",
                parse_mode="Markdown",
            )
            return

        context.user_data["pending_expense_confirm"] = item
        await update.message.reply_text(
            f"{build_pending_expense_confirm_preview(item, include_question=False)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("pending_expense", True),
        )
        return

    # Debt flow section
    # Debt flow section
    # Implementation section
    selected_debt_settle_handled = await handle_natural_debt_settle(update, context, user_text)
    if selected_debt_settle_handled:
        return

    # Phase 2: explicit debt/split/talangin intent must win before parse safety.
    early_debt_parsed = parse_debt_input(user_text)
    if early_debt_parsed:
        debt_handled = await debt_message_handler(update, context)
        if debt_handled:
            return

    # Implementation section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    finance_question_handled = await handle_natural_finance_question(
        update,
        context,
        user_text,
    )

    if finance_question_handled:
        return

    # Implementation section
    # Example cleanup: remove the person prefix so the description stays focused on the expense item.
    pre_parse_assessment = assess_parse_safety(user_text, {})
    if pre_parse_assessment.get("recommended_action") == CLARIFICATION:
        await send_parse_clarification(update, context, user_text, {}, pre_parse_assessment)
        return

    has_explicit_separator = bool(re.search(r"[\n\r;,]", user_text))
    input_lines = split_user_inputs(user_text)
    is_multi_input = has_explicit_separator or len(input_lines) > 1

    # Debt flow section
    if not is_multi_input:
        full_debt_parsed = parse_debt_input(user_text)
        if full_debt_parsed:
            debt_handled = await debt_message_handler(update, context)
            if debt_handled:
                return

    # Input multi / campuran
    if len(input_lines) > 1:
        mixed_items = []
        failed_lines = []
        missing_amount_indices = []

        for line in input_lines:
            item = parse_mixed_item(line)

            if item["kind"] == "failed":
                failed_lines.append(line)
                continue

            if item["kind"] == "missing_amount":
                missing_amount_indices.append(len(mixed_items))

            mixed_items.append(item)

        if failed_lines:
            lines = ["🤔 Ada input yang belum bisa saya pahami:\n"]

            for i, line in enumerate(failed_lines, 1):
                lines.append(f"{i}. `{line}`")

            lines.append(
                "\nCoba format seperti:\n"
                "`beli kopi 25rb`\n"
                "`Budi minjem 300k`\n"
                "`minjem Joko 100k`\n"
                "`beli kopi 10k minjem Joko 10k`"
            )

            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
            return

        if mixed_items:
            if missing_amount_indices:
                context.user_data["pending_missing_amount"] = {
                    "scope": "mixed",
                    "mixed_items": mixed_items,
                    "missing_indices": missing_amount_indices,
                    "current": 0,
                }
                first_idx = missing_amount_indices[0]
                first_item = mixed_items[first_idx]
                await update.message.reply_text(
                    build_missing_amount_prompt(
                        first_item.get("raw", ""),
                        first_item.get("parsed", {}),
                        1,
                        len(missing_amount_indices),
                    ),
                    parse_mode="Markdown",
                )
                return

            context.user_data["pending_mixed"] = mixed_items
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_debt_batch", None)
            context.user_data.pop("mixed_review_preview_sent", None)

            preview = build_mixed_detail_preview(mixed_items)

            if mixed_split_bill_needs_decision(mixed_items):
                await update.message.reply_text(
                    build_mixed_split_bill_queue_prompt(mixed_items),
                    parse_mode="Markdown",
                    reply_markup=mixed_split_bill_keyboard(mixed_items),
                )
            else:
                await reply_update_safely(
                    update,
                    f"{preview}\n\n{preview_action_question(False)}",
                    parse_mode="Markdown",
                    reply_markup=preview_action_keyboard("mixed", False),
                )

            return

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Debt flow section
    missing_amount_income = parse_income_missing_amount(user_text)
    if missing_amount_income:
        context.user_data["pending_missing_amount"] = {
            "scope": "single",
            "item": {
                "kind": "missing_amount",
                "parsed": missing_amount_income,
                "raw": user_text,
            },
        }
        await update.message.reply_text(
            build_missing_amount_prompt(user_text, missing_amount_income),
            parse_mode="Markdown",
        )
        return

    # Single transaction
    parsed = parse_input(user_text)

    if parsed.get("type") == "pending":
        # Natural input section
        # Debt flow section
        # Account flow section
        # Debt flow section
        # Natural input section
        # - cari kopi
        # Date parsing note: keep explicit and relative Indonesian date formats predictable.
        local_natural_handled = await handle_local_natural_intent(
            update,
            context,
            user_text,
        )

        if local_natural_handled:
            return

        # Debt flow section
        # Implementation section
        # Implementation note for this project-specific finance flow.
        # Implementation note for this project-specific finance flow.
        gemini_handled = await handle_gemini_intent(update, context, user_text)

        if gemini_handled:
            return

        # Layer 5: local typo resolver pendek.
        # Implementation note for this project-specific finance flow.
        # - minguan
        # - mingguannn
        # - detele
        # - bugete
        command_typo_feedback = maybe_text_is_command_typo(user_text)

        if command_typo_feedback:
            await update.message.reply_text(
                command_typo_feedback,
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            build_gemini_fallback_text(),
            parse_mode="Markdown",
        )
        return

    attach_split_bill_if_any(parsed, user_text)

    safety_assessment = assess_parse_safety(user_text, parsed)
    safety_action = safety_assessment.get("recommended_action")

    if safety_action == CLARIFICATION:
        await send_parse_clarification(update, context, user_text, parsed, safety_assessment)
        return

    preview_mode = "normal"
    if safety_action == GEMINI_DRAFT_PREVIEW:
        parsed, safety_assessment, gemini_used = try_gemini_draft_for_parse_safety(user_text, parsed, safety_assessment)
        preview_mode = "gemini" if gemini_used else "warning"
    elif safety_action == WARNING_PREVIEW:
        preview_mode = "warning"

    context.user_data["pending_parsed"] = parsed
    context.user_data["pending_raw"] = user_text
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt", None)
    context.user_data.pop("pending_debt_batch", None)
    context.user_data.pop("pending_mixed", None)
    context.user_data.pop("pending_parse_clarification", None)

    preview = (
        build_preview_with_parse_safety(parsed, safety_assessment, preview_mode)
        if preview_mode in {"warning", "gemini"}
        else build_preview(parsed)
    )

    if split_bill_needs_decision(parsed):
        await update.message.reply_text(
            build_split_bill_prompt_from_parsed(parsed),
            parse_mode="Markdown",
            reply_markup=split_bill_keyboard("single"),
        )
    elif needs_account(parsed):
        await reply_update_safely(
            update,
            build_single_account_prompt(
                parsed,
                preview_text=preview if preview_mode in {"warning", "gemini"} else None,
            ),
            parse_mode="Markdown",
            reply_markup=account_keyboard("acc"),
        )
    else:
        await reply_update_safely(
            update,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("single", True),
        )


def build_transactions_full_text(transactions: list[dict], title: str, account_filter: str | None = None) -> str:
    """Build the data structure or message text for transactions full text."""
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
        txn_type = str(txn.get("type", "")).strip().lower()
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
        net_gross = total_income + total_transfer_in - total_expense - total_transfer_out
        net_after_receivable = total_income + total_transfer_in - total_net_expense - total_transfer_out
        expense_text = format_expense_net_gross(total_net_expense, total_expense)
        net_text = format_expense_net_gross(net_after_receivable, net_gross)
        lines.append(
            "\n*Ringkasan Rekening:*\n"
            f"✅ Income          : *{format_rupiah(total_income)}*\n"
            f"❌ Expense         : *{expense_text}*\n"
            f"🔁 Transfer Masuk  : *{format_rupiah(total_transfer_in)}*\n"
            f"🔁 Transfer Keluar : *{format_rupiah(total_transfer_out)}*\n"
            f"📊 Net Rekening    : *{net_text}*\n"
            f"📝 Total           : *{len(transactions)} transaksi*"
        )
    else:
        net_gross = total_income - total_expense
        net_after_receivable = total_income - total_net_expense
        expense_text = format_expense_net_gross(total_net_expense, total_expense)
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

def build_transaction_filter_title(base_title: str, category_filter: str | None = None, account_filter: str | None = None) -> str:
    """Build the data structure or message text for transaction filter title."""
    suffix = []
    if category_filter:
        suffix.append(f"Kategori {category_filter}")
    if account_filter:
        suffix.append(f"Rekening {account_filter}")
    if suffix:
        return f"{base_title} — {' | '.join(suffix)}"
    return base_title


def _build_transaksi_prefixed_period_arg(first: str, rest: str, mode: str) -> str | None:
    """Build the data structure or message text for transaksi prefixed period arg."""
    rest = str(rest or "").strip()
    if not rest:
        return None

    first_rest = rest.split()[0].strip().lower()

    if mode == "month" and first_rest in {"ini", "lalu", "depan"}:
        return f"{first} {rest}"

    if mode == "date" and first_rest in {"ini", "lalu", "depan"}:
        return f"{first} {rest}"

    return rest


def parse_transaksi_period(args: list[str]) -> tuple[str, list[dict], str, str | None]:
    """Parse input into structured data for transaksi period."""
    raw = " ".join(args or []).strip()
    low = raw.lower()

    if not raw:
        year, month_num = parse_report_month_arg(None)
        report = get_monthly_report(year, month_num)
        return f"Transaksi Bulan {report.get('month', '-')}", report.get("transactions", []), "month", None

    first = low.split()[0]
    rest = " ".join(raw.split()[1:]).strip()

    if first in ["rekening", "akun", "account", "rek"]:
        account_arg, period_arg = split_account_period_arg(rest)
        if not account_arg:
            raise ValueError("Nama rekening belum diisi. Contoh: /transaksi rekening Cash")

        report = get_account_report(account_arg, period_arg)
        account_filter = report.get("account_filter") or account_arg
        period_label = report.get("period_label") or report.get("month") or "-"
        return (
            f"Transaksi Rekening {account_filter} — {period_label}",
            report.get("transactions", []),
            "account",
            account_filter,
        )

    if first in ["hari", "harian", "tanggal", "tgl", "tg", "day", "daily"]:
        period_source = _build_transaksi_prefixed_period_arg(first, rest, "date")
        date_arg, category_arg, account_arg = split_report_filter_args(period_source, "date")
        report = get_daily_report(date_arg, category_arg, account_arg)
        title = build_transaction_filter_title(
            f"Transaksi Tanggal {report.get('date', '-')}",
            report.get("category_filter"),
            report.get("account_filter"),
        )
        return title, report.get("transactions", []), "day", report.get("account_filter")

    if first in ["minggu", "mingguan", "week", "weekly"]:
        period_source = _build_transaksi_prefixed_period_arg(first, rest, "date")
        date_arg, category_arg, account_arg = split_report_filter_args(period_source, "date")
        report = get_weekly_report(date_arg, category_arg, account_arg)
        title = build_transaction_filter_title(
            f"Transaksi Minggu {report.get('date_from', '-')} s/d {report.get('date_to', '-')}",
            report.get("category_filter"),
            report.get("account_filter"),
        )
        return title, report.get("transactions", []), "week", report.get("account_filter")

    if first in ["bulan", "bulanan", "month", "monthly"]:
        period_source = _build_transaksi_prefixed_period_arg(first, rest, "month")
        month_arg, category_arg, account_arg = split_report_filter_args(period_source, "month")
        year, month_num = parse_report_month_arg(month_arg)
        report = get_monthly_report(year, month_num, category_arg, account_arg)
        title = build_transaction_filter_title(
            f"Transaksi Bulan {report.get('month', '-')}",
            report.get("category_filter"),
            report.get("account_filter"),
        )
        return title, report.get("transactions", []), "month", report.get("account_filter")

    if re.fullmatch(r"20\d{2}[-/]\d{1,2}[-/]\d{1,2}", low) or re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]20\d{2}", low):
        report = get_daily_report(raw)
        return f"Transaksi Tanggal {report.get('date', '-')}", report.get("transactions", []), "day", None

    if re.fullmatch(r"20\d{2}[-/]\d{1,2}", low):
        year, month_num = parse_report_month_arg(raw)
        report = get_monthly_report(year, month_num)
        return f"Transaksi Bulan {report.get('month', '-')}", report.get("transactions", []), "month", None

    if re.fullmatch(r"\d{1,2}", low):
        report = get_daily_report(raw)
        return f"Transaksi Tanggal {report.get('date', '-')}", report.get("transactions", []), "day", None

    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    # /transaction kemarin
    # /transaction minggu lalu
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    try:
        date_arg = parse_report_date_arg(raw)
        report = get_daily_report(date_arg)
        return f"Transaksi Tanggal {report.get('date', '-')}", report.get("transactions", []), "day", None
    except Exception:
        pass

    try:
        month_arg, category_arg, account_arg = split_report_filter_args(raw, "month")
        if month_arg or category_arg or account_arg:
            year, month_num = parse_report_month_arg(month_arg)
            report = get_monthly_report(year, month_num, category_arg, account_arg)
            title = build_transaction_filter_title(
                f"Transaksi Bulan {report.get('month', '-')}",
                report.get("category_filter"),
                report.get("account_filter"),
            )
            return title, report.get("transactions", []), "month", report.get("account_filter")
    except Exception:
        pass

    raise ValueError(
        "Format /transaksi tidak dikenali. Contoh: /transaksi 2026-06, /transaksi bulan lalu, /transaksi Food & Beverage 2026-06, /transaksi rekening Cash bulan lalu."
    )


async def transaksi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Telegram request for transaksi."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        title, transactions, _period_type, account_filter = parse_transaksi_period(context.args)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/transaksi`\n"
            "`/transaksi 2026-06`\n"
            "`/transaksi bulan lalu`\n"
            "`/transaksi hari 2026-06-01`\n"
            "`/transaksi minggu lalu`\n"
            "`/transaksi Food & Beverage 2026-06`\n"
            "`/transaksi rekening Cash bulan lalu`",
            parse_mode="Markdown",
        )
        return

    transactions = sorted(
        transactions,
        key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)),
        reverse=True,
    )

    if not transactions:
        await update.message.reply_text(
            f"📭 Tidak ada transaksi untuk filter: *{md_safe(title)}*",
            parse_mode="Markdown",
        )
        return

    last_map = {}
    for i, txn in enumerate(transactions, 1):
        if txn.get("_row_index"):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

    context.user_data["last_txn_map"] = last_map
    await reply_long_markdown(update, build_transactions_full_text(transactions, title, account_filter))


async def last_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Telegram request for last."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    args = context.args

    limit = 10
    period = None
    month = None
    title = "Transaksi Terakhir"

    if args:
        arg1 = args[0].strip().lower()

        if arg1.isdigit():
            limit = min(max(int(arg1), 1), 30)
            title = f"{limit} Transaksi Terakhir"

        elif arg1 in ["today", "hariini", "harian"]:
            period = "today"
            title = "Transaksi Hari Ini"

        elif arg1 in ["week", "minggu", "mingguan"]:
            period = "week"
            title = "Transaksi Minggu Ini"

        elif arg1 in ["month", "bulan", "bulanan"]:
            period = "month"
            title = "Transaksi Bulan Ini"

        elif re.fullmatch(r"20\d{2}-(0?[1-9]|1[0-2])", arg1):
            year, month_num = arg1.split("-")
            month = f"{year}-{int(month_num):02d}"
            title = f"Transaksi {month}"

        else:
            await update.message.reply_text(
                "❌ Format /last tidak dikenali.\n\n"
                "Contoh:\n"
                "`/last`\n"
                "`/last 20`\n"
                "`/last today`\n"
                "`/last week`\n"
                "`/last month`\n"
                "`/last 2026-06`",
                parse_mode="Markdown",
            )
            return

    transactions = get_recent_transactions(
        limit=limit,
        period=period,
        month=month,
    )

    if not transactions:
        await update.message.reply_text(
            f"📭 Tidak ada transaksi untuk filter: *{title}*",
            parse_mode="Markdown",
        )
        return

    last_map = {}

    for i, txn in enumerate(transactions, 1):
        last_map[str(i)] = {
            "id": str(txn.get("id", "")),
            "row_index": int(txn.get("_row_index")),
        }

    context.user_data["last_txn_map"] = last_map

    await reply_long_markdown(update, build_last_transactions_text(transactions, title))


async def delete_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Telegram request for delete txn."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    refs = context.args

    if not refs:
        await update.message.reply_text(
            "❌ Masukkan nomor transaksi dari `/last` atau transaction ID.\n\n"
            "Contoh:\n"
            "`/last today`\n"
            "`/delete_txn 1`\n"
            "`/delete_txn 1 3 5`\n"
            "`/delete_txn txn_20260609_231132_123456_abcd1234`",
            parse_mode="Markdown",
        )
        return

    resolved = resolve_txn_refs_from_last(context, refs)

    invalid_refs = resolved.get("invalid_refs", [])

    if invalid_refs and not resolved["row_indices"] and not resolved["txn_ids"]:
        await update.message.reply_text(
            "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
            "Jalankan dulu:\n"
            "`/last`\n\n"
            "Lalu hapus dengan:\n"
            "`/delete_txn 1`\n"
            "`/delete_txn 1 3 5`",
            parse_mode="Markdown",
        )
        return

    preview = preview_delete_transactions_by_refs(
        row_indices=resolved["row_indices"],
        txn_ids=resolved["txn_ids"],
    )

    if invalid_refs:
        preview["missing_rows"] = preview.get("missing_rows", []) + invalid_refs

    if not preview.get("deletable"):
        await update.message.reply_text(
            build_delete_preview_text(preview),
            parse_mode="Markdown",
        )
        return

    context.user_data["pending_delete_refs"] = {
        "row_indices": [
            int(txn.get("_row_index"))
            for txn in preview.get("deletable", [])
            if txn.get("_row_index")
        ],
        "txn_ids": [],
    }

    await update.message.reply_text(
        build_delete_preview_text(preview),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("delete_txns"),
    )

def parse_edit_updates(args: list[str]) -> dict:
    """Parse input into structured data for edit updates."""
    if not args:
        return {}

    if len(args) == 1:
        first = args[0].strip()
        if re.fullmatch(r"\d+(?:[.,]\d+)?(?:\s*(?:rb|ribu|k|jt|juta|m))?", first, flags=re.IGNORECASE):
            return {"amount": first.replace(",", ".")}

    split_words = {"dibagi", "bagi", "patungan", "split", "share"}
    updates = {}
    i = 0

    while i < len(args):
        arg = str(args[i] or "").strip()
        low = arg.lower()

        if not arg:
            i += 1
            continue

        # Split bill parsing note: separate the paid transaction from each person share.
        if low in split_words or low.replace("-", "") in {"dibagi"}:
            break

        # Mendukung: amount = 500k
        if i + 2 < len(args) and args[i + 1] == "=":
            key = arg
            value = str(args[i + 2]).strip()
            updates[key] = value
            i += 3
            continue

        # Supports both `amount=500k` and `amount= 500k`.
        if "=" in arg:
            key, value = arg.split("=", 1)
            key = key.strip()
            value = value.strip()
            if value == "" and i + 1 < len(args):
                value = str(args[i + 1]).strip()
                i += 2
            else:
                i += 1

            if not key or value == "":
                raise ValueError(f"Argumen `{arg}` tidak valid. Gunakan format key=value.")
            updates[key] = value
            continue

        # Implementation note for this project-specific finance flow.
        if not updates and re.fullmatch(r"\d+(?:[.,]\d+)?(?:\s*(?:rb|ribu|k|jt|juta|m))?", arg, flags=re.IGNORECASE):
            updates["amount"] = arg
            i += 1
            continue

        raise ValueError(
            f"Argumen `{arg}` tidak valid. Gunakan format key=value."
        )

    return updates


def edit_args_contain_split_bill(args: list[str]) -> bool:
    """Helper for edit args contain split bill in the Telegram bot flow."""
    raw = " ".join(str(x or "") for x in args)
    return bool(re.search(r"\b(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)\b", raw, flags=re.IGNORECASE))


def _normalize_edit_arg_token(token: str) -> str:
    """Normalize and clean input for edit arg token."""
    return str(token or "").strip().lower().replace("_", "-")


def parse_edit_debt_payment_conversion_args(args: list[str]) -> dict | None:
    """Parse input into structured data for edit debt payment conversion args."""
    if not args:
        return None

    raw_tokens = [str(x or "").strip() for x in args if str(x or "").strip()]
    if not raw_tokens:
        return None

    target_type = ""
    explicit_person = ""
    field_tokens: list[str] = []
    person_tokens: list[str] = []
    consume_person = False
    found_marker = False

    i = 0
    while i < len(raw_tokens):
        token = raw_tokens[i]
        low = _normalize_edit_arg_token(token)

        # Explicit fields khusus conversion.
        if "=" in token:
            key, value = token.split("=", 1)
            key_low = key.strip().lower().replace("_", "-")
            value_clean = value.strip()

            if key_low in {"debt", "debt-type", "tipe-hutang", "tipehutang", "hutang-type", "jenis-debt"}:
                found_marker = True
                value_low = value_clean.lower()
                if value_low in {"payable", "utang", "hutang", "bayar-utang", "bayar-hutang"}:
                    target_type = "payable"
                elif value_low in {"receivable", "piutang", "bayar-piutang"}:
                    target_type = "receivable"
                else:
                    raise ValueError("Nilai debt harus payable/utang/hutang atau receivable/piutang.")
                i += 1
                continue

            if key_low in {"person", "orang", "nama", "ke", "dari", "sama"}:
                explicit_person = value_clean
                i += 1
                continue

            field_tokens.append(token)
            i += 1
            continue

        # Debt flow section
        compact = low.replace("-", "")
        if compact in {"bayarhutang", "bayarutang", "pembayaranhutang", "pembayaranutang", "hutang", "utang"}:
            target_type = "payable"
            found_marker = True
            consume_person = True
            i += 1
            continue

        if compact in {"bayarpiutang", "pembayaranpiutang", "piutang"}:
            target_type = "receivable"
            found_marker = True
            consume_person = True
            i += 1
            continue

        # Debt flow section
        next_low = _normalize_edit_arg_token(raw_tokens[i + 1]) if i + 1 < len(raw_tokens) else ""
        next_compact = next_low.replace("-", "")
        if compact in {"bayar", "pembayaran", "payment", "jadi", "menjadi", "ubah", "konversi", "convert"} and next_compact in {"hutang", "utang", "piutang"}:
            target_type = "receivable" if next_compact == "piutang" else "payable"
            found_marker = True
            consume_person = True
            i += 2
            continue

        # Split bill parsing note: separate the paid transaction from each person share.
        if consume_person and compact in {"ke", "dari", "sama", "dengan", "untuk", "sebagai"}:
            i += 1
            continue

        # Split bill parsing note: separate the paid transaction from each person share.
        if consume_person:
            person_tokens.append(token)
            i += 1
            continue

        field_tokens.append(token)
        i += 1

    if not found_marker:
        return None

    person = explicit_person or " ".join(person_tokens).strip()
    person = re.sub(r"\s+", " ", person).strip()
    person = re.sub(r"^(ke|dari|sama|dengan|untuk)\s+", "", person, flags=re.IGNORECASE).strip()

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    person = re.sub(r"\s+\w+\s*=.*$", "", person).strip()

    if not target_type:
        raise ValueError("Tipe pembayaran debt belum jelas. Gunakan bayar_hutang atau bayar_piutang.")
    if not person:
        raise ValueError("Nama orang belum jelas. Contoh: /edit_txn 2 bayar_hutang Sapto")

    extra_updates = parse_edit_updates(field_tokens) if field_tokens else {}

    return {
        "target_type": target_type,
        "person_name": person.title(),
        "extra_updates": extra_updates,
    }


def build_debt_payment_conversion_updates(conversion: dict, old_txn: dict | None = None) -> dict:
    """Build the data structure or message text for debt payment conversion updates."""
    target_type = str(conversion.get("target_type") or "").strip().lower()
    person = str(conversion.get("person_name") or "").strip().title()
    updates = dict(conversion.get("extra_updates") or {})

    if target_type == "payable":
        updates.update({
            "type": "expense",
            "category": "Bayar Utang",
            "subject": person,
            "description": f"Bayar utang ke {person}",
            "catatan": f"Dikonversi dari transaksi biasa menjadi pembayaran utang ke {person}",
        })
    elif target_type == "receivable":
        updates.update({
            "type": "income",
            "category": "Pembayaran Piutang",
            "subject": person,
            "description": f"Pembayaran piutang dari {person}",
            "catatan": f"Dikonversi dari transaksi biasa menjadi pembayaran piutang dari {person}",
        })
    else:
        raise ValueError("Tipe pembayaran debt tidak valid.")

    return updates


def validate_edit_debt_payment_conversion(conversion: dict, amount: float) -> dict:
    """Validate data before it is used by edit debt payment conversion."""
    person = str(conversion.get("person_name") or "").strip().title()
    target_type = str(conversion.get("target_type") or "").strip().lower()
    label = "utang" if target_type == "payable" else "piutang"

    debts = get_debt_by_person(person)
    target_debts = [
        d for d in debts
        if str(d.get("type", "")).strip() == target_type
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
    ]
    total_remaining = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in target_debts)

    if not target_debts or total_remaining <= 0:
        return {
            "success": False,
            "message": f"Tidak ada {label} aktif dengan {person}.",
            "total_remaining": 0,
            "overpayment": 0,
        }

    outcome = estimate_payment_outcome(person, amount, target_type)
    return {
        "success": True,
        "message": "ok",
        "total_remaining": total_remaining,
        "opposite_remaining": outcome.get("opposite_remaining_before", 0),
        "net_payment_capacity": outcome.get("net_payment_capacity", total_remaining),
        "overpayment": outcome.get("overpayment", 0),
        "target_count": len(target_debts),
        "label": label,
    }


def build_edit_debt_payment_preview_text(preview: dict, conversion: dict, debt_check: dict) -> str:
    """Build the data structure or message text for edit debt payment preview text."""
    text = build_edit_preview_text(preview)
    person = str(conversion.get("person_name") or "-").strip()
    target_type = str(conversion.get("target_type") or "").strip().lower()
    label = "utang" if target_type == "payable" else "piutang"
    amount = float((preview.get("new_txn") or {}).get("amount", 0) or 0)

    text += (
        f"\n\n💸 *Konversi Debt:* transaksi ini akan dijadikan pembayaran {label}."
        f"\n👤 Orang: *{md_safe(person)}*"
        f"\n💰 Pembayaran: *{format_rupiah(amount)}*"
        f"\n📌 Sisa {label} aktif saat ini: *{format_rupiah(debt_check.get('total_remaining', 0))}*"
        f"\n📌 Sisa arah lawan saat ini: *{format_rupiah(debt_check.get('opposite_remaining', 0))}*"
        f"\n📊 Saldo net yang perlu dibayar: *{format_rupiah(debt_check.get('net_payment_capacity', debt_check.get('total_remaining', 0)))}*"
    )

    if float(debt_check.get("overpayment", 0) or 0) > 0:
        text += f"\n⚠️ Nominal melebihi saldo net debt: {format_rupiah(debt_check.get('overpayment', 0))}. Kelebihannya perlu diperlakukan sebagai bonus/lunas atau hutang lawan arah."

    return text


def build_edit_split_preview_text(preview: dict, split_parsed: dict | None = None) -> str:
    """Build the data structure or message text for edit split preview text."""
    text = build_edit_preview_text(preview)
    split_bill = (split_parsed or {}).get("split_bill") or {}
    status = split_bill.get("status")
    if split_bill:
        total_receivable = float(split_bill.get("total_receivable", 0) or 0)
        if status == "unpaid":
            text += (
                "\n\n🤝 *Split bill:* belum dibayar, jadi piutang baru akan dibuat "
                f"sebesar *{format_rupiah(total_receivable)}*."
            )
        elif status == "paid":
            text += "\n\n🤝 *Split bill:* sudah dibayar, transaksi disimpan sebesar bagian bersih kamu."
    return text


def build_edit_preview_text(preview: dict) -> str:
    """Build the data structure or message text for edit preview text."""
    old_txn = preview.get("old_txn", {})
    new_txn = preview.get("new_txn", {})
    updates = preview.get("updates", {})
    net_deltas = preview.get("net_deltas", {})

    lines = ["✏️ *Preview Edit Transaksi*\n"]

    lines.append("*Sebelum:*")
    lines.append(
        f"• {old_txn.get('date')} — *{old_txn.get('description') or '-'}*\n"
        f"  {format_rupiah(float(old_txn.get('amount', 0) or 0))} | "
        f"{old_txn.get('category') or '-'} | {old_txn.get('account') or '-'}"
    )

    lines.append("\n*Sesudah:*")
    lines.append(
        f"• {new_txn.get('date')} — *{new_txn.get('description') or '-'}*\n"
        f"  {format_rupiah(float(new_txn.get('amount', 0) or 0))} | "
        f"{new_txn.get('category') or '-'} | {new_txn.get('account') or '-'}"
    )

    if updates:
        lines.append("\n*Field yang diubah:*")
        for field, value in updates.items():
            lines.append(f"• {field}: `{value}`")

    if net_deltas:
        lines.append("\n*Efek ke saldo:*")
        for account, delta in net_deltas.items():
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {account}: {sign}{format_rupiah(abs(delta))}")
    else:
        lines.append("\n*Efek ke saldo:*")
        lines.append("• Tidak ada perubahan saldo")

    lines.append("\nSimpan perubahan ini?")

    return "\n".join(lines)



def extract_bulk_edit_txn_lines(raw_text: str) -> list[str]:
    """Extract the required part of input for bulk edit txn lines."""
    lines = [str(line or "").strip() for line in str(raw_text or "").splitlines()]
    lines = [line for line in lines if line]

    edit_lines = [
        line for line in lines
        if re.match(r"^/edit_txn(?:@\w+)?\b", line, flags=re.IGNORECASE)
    ]

    if len(edit_lines) >= 2 and len(edit_lines) == len(lines):
        return edit_lines

    return []


def _format_bulk_edit_value(value) -> str:
    """Format data into a readable display for bulk edit value."""
    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return format_rupiah(float(value)) if abs(float(value)) >= 1000 else str(int(value))
        return str(value)
    return str(value if value is not None else "-").strip() or "-"


def build_bulk_edit_preview_text(entries: list[dict]) -> str:
    """Build the data structure or message text for bulk edit preview text."""
    lines = [
        "✏️ *Preview Bulk Edit Transaksi*",
        f"Akan mengedit *{len(entries)} transaksi* dari daftar terakhir.",
        "",
    ]

    balance_touch_count = 0
    for idx, entry in enumerate(entries, 1):
        preview = entry.get("preview") or {}
        old_txn = preview.get("old_txn") or {}
        new_txn = preview.get("new_txn") or {}
        updates = preview.get("updates") or {}
        net_deltas = preview.get("net_deltas") or {}
        if net_deltas:
            balance_touch_count += 1

        ref = str(entry.get("ref") or idx).strip()
        desc_before = str(old_txn.get("description") or old_txn.get("subject") or "-").strip()
        desc_after = str(new_txn.get("description") or new_txn.get("subject") or "-").strip()
        lines.append(f"{idx}. Ref `{md_code_text(ref)}` — *{md_safe(desc_before)}*")

        for field, new_value in updates.items():
            old_value = old_txn.get(field, "")
            if field == "amount":
                old_text = format_rupiah(float(old_value or 0))
                new_text = format_rupiah(float(new_value or 0))
            else:
                old_text = _format_bulk_edit_value(old_value)
                new_text = _format_bulk_edit_value(new_value)

            label = {
                "description": "Desc",
                "category": "Kategori",
                "amount": "Nominal",
                "account": "Rekening",
                "to_account": "Rekening tujuan",
                "date": "Tanggal",
                "type": "Tipe",
                "subject": "Subject",
                "catatan": "Catatan",
                "tipe_pengeluaran": "Tipe pengeluaran",
            }.get(str(field), str(field))

            lines.append(f"   • {label}: {md_safe(old_text)} → *{md_safe(new_text)}*")

        if desc_before != desc_after and "description" not in updates:
            lines.append(f"   • Desc hasil: {md_safe(desc_before)} → *{md_safe(desc_after)}*")

    if balance_touch_count:
        lines.append(
            f"\n⚠️ Ada *{balance_touch_count} edit* yang bisa mengubah saldo karena menyentuh nominal/rekening/type."
        )
    else:
        lines.append("\nℹ️ Bulk edit ini tidak mengubah saldo karena hanya mengubah metadata transaksi.")

    lines.append("\nSimpan semua perubahan ini?")
    return "\n".join(lines)


def build_bulk_edit_error_text(errors: list[str]) -> str:
    """Build the data structure or message text for bulk edit error text."""
    lines = ["❌ *Bulk edit tidak bisa diproses.*", ""]
    lines.append("Perbaiki baris berikut dulu:")
    for err in errors[:15]:
        lines.append(f"• {md_safe(err)}")
    if len(errors) > 15:
        lines.append(f"• ...dan {len(errors) - 15} error lain")
    lines.append(
        "\nFormat contoh:\n"
        "`/edit_txn 1 category=\"Food & Beverage\"`\n"
        "`/edit_txn 2 category=\"Bills & Utilities\" desc=\"Wifi\"`"
    )
    return "\n".join(lines)


def parse_bulk_edit_txn_entries(lines: list[str], context: ContextTypes.DEFAULT_TYPE) -> tuple[list[dict], list[str]]:
    """Parse input into structured data for bulk edit txn entries."""
    entries: list[dict] = []
    errors: list[str] = []
    seen_targets: set[str] = set()

    for line_no, line in enumerate(lines, 1):
        try:
            parts = shlex.split(line)
        except Exception as e:
            errors.append(f"Baris {line_no}: format kutip tidak valid ({e}).")
            continue

        if len(parts) < 3:
            errors.append(f"Baris {line_no}: format edit belum lengkap.")
            continue

        args = parts[1:]
        ref = str(args[0] or "").strip()
        update_args = args[1:]

        if edit_args_contain_split_bill(update_args):
            errors.append(
                f"Baris {line_no}: edit split bill perlu dijalankan satu per satu karena butuh pilihan sudah bayar/belum."
            )
            continue

        try:
            debt_payment_conversion = parse_edit_debt_payment_conversion_args(update_args)
        except Exception as e:
            errors.append(f"Baris {line_no}: {str(e)}")
            continue

        if debt_payment_conversion:
            errors.append(
                f"Baris {line_no}: konversi bayar_hutang/bayar_piutang perlu dijalankan satu per satu."
            )
            continue

        resolved = resolve_txn_refs_from_last(context, [ref])
        if resolved.get("invalid_refs") and not resolved.get("row_indices") and not resolved.get("txn_ids"):
            errors.append(f"Baris {line_no}: nomor transaksi `{ref}` tidak ditemukan dari hasil terakhir.")
            continue

        row_index = resolved["row_indices"][0] if resolved.get("row_indices") else None
        txn_id = resolved["txn_ids"][0] if resolved.get("txn_ids") else None
        target_key = f"row:{row_index}" if row_index else f"id:{txn_id}"

        if target_key in seen_targets:
            errors.append(f"Baris {line_no}: transaksi `{ref}` diedit lebih dari sekali dalam bulk edit ini.")
            continue
        seen_targets.add(target_key)

        try:
            updates = parse_edit_updates(update_args)
        except Exception as e:
            errors.append(f"Baris {line_no}: {str(e)}")
            continue

        if not updates:
            errors.append(f"Baris {line_no}: tidak ada field yang diedit.")
            continue

        preview = preview_edit_transaction_by_ref(
            updates=updates,
            row_index=row_index,
            txn_id=txn_id,
        )

        if not preview.get("success"):
            errors.append(f"Baris {line_no}: {preview.get('message') or 'Gagal preview edit.'}")
            continue

        entries.append({
            "line_no": line_no,
            "line": line,
            "ref": ref,
            "row_index": row_index,
            "txn_id": txn_id,
            "updates": preview.get("updates") or updates,
            "preview": preview,
        })

    return entries, errors


async def bulk_edit_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, lines: list[str]):
    """Handle the Telegram request for bulk edit txn."""
    entries, errors = parse_bulk_edit_txn_entries(lines, context)

    if errors or not entries:
        await update.message.reply_text(
            build_bulk_edit_error_text(errors or ["Tidak ada baris edit valid."]),
            parse_mode="Markdown",
        )
        return

    context.user_data["pending_bulk_edit_txns"] = {
        "entries": [
            {
                "line_no": entry.get("line_no"),
                "line": entry.get("line"),
                "ref": entry.get("ref"),
                "row_index": entry.get("row_index"),
                "txn_id": entry.get("txn_id"),
                "updates": entry.get("updates") or {},
            }
            for entry in entries
        ]
    }

    await update.message.reply_text(
        build_bulk_edit_preview_text(entries),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("edit_txns_bulk"),
    )

async def edit_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Telegram request for edit txn."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    raw_text = update.message.text.strip()

    bulk_lines = extract_bulk_edit_txn_lines(raw_text)
    if bulk_lines:
        await bulk_edit_txn_handler(update, context, bulk_lines)
        return

    try:
        parts = shlex.split(raw_text)
    except Exception:
        await update.message.reply_text(
            "❌ Format edit tidak valid. Kalau ada spasi, pakai tanda kutip.\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`",
            parse_mode="Markdown",
        )
        return

    # Implementation note for this project-specific finance flow.
    args = parts[1:]

    if len(args) < 2:
        await update.message.reply_text(
            "❌ Format edit belum lengkap.\n\n"
            "Contoh:\n"
            "`/last`\n"
            "`/edit_txn 2 amount=15000`\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`\n"
            "`/edit_txn 2 account=BRI category=\"Food & Beverage\"`\n"
            "`/edit_txn 2 15000`",
            parse_mode="Markdown",
        )
        return

    ref = args[0]
    update_args = args[1:]

    resolved = resolve_txn_refs_from_last(context, [ref])

    if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
        await update.message.reply_text(
            "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
            "Jalankan dulu:\n"
            "`/last`\n\n"
            "Lalu edit dengan:\n"
            "`/edit_txn 2 amount=15000`",
            parse_mode="Markdown",
        )
        return

    row_index = resolved["row_indices"][0] if resolved["row_indices"] else None
    txn_id = resolved["txn_ids"][0] if resolved["txn_ids"] else None

    try:
        debt_payment_conversion = parse_edit_debt_payment_conversion_args(update_args)
    except Exception as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh konversi pembayaran debt:\n"
            "`/edit_txn 2 bayar_hutang Sapto`\n"
            "`/edit_txn 2 bayar_piutang Sapto`\n"
            "`/edit_txn 2 debt=payable person=Sapto`",
            parse_mode="Markdown",
        )
        return

    if debt_payment_conversion:
        try:
            updates = build_debt_payment_conversion_updates(debt_payment_conversion)
        except Exception as e:
            await update.message.reply_text(f"❌ {md_safe(str(e))}", parse_mode="Markdown")
            return

        preview = preview_edit_transaction_by_ref(
            updates=updates,
            row_index=row_index,
            txn_id=txn_id,
        )

        if not preview.get("success"):
            await update.message.reply_text(
                f"❌ {preview.get('message')}",
                parse_mode="Markdown",
            )
            return

        debt_check = validate_edit_debt_payment_conversion(
            debt_payment_conversion,
            float((preview.get("new_txn") or {}).get("amount", 0) or 0),
        )

        if not debt_check.get("success"):
            await update.message.reply_text(
                f"❌ {md_safe(debt_check.get('message') or 'Debt aktif tidak ditemukan.')}",
                parse_mode="Markdown",
            )
            return

        context.user_data["pending_edit_txn"] = {
            "row_index": row_index,
            "txn_id": txn_id,
            "updates": updates,
            "split_raw": "",
            "split_parsed": None,
            "debt_payment_conversion": debt_payment_conversion,
            "debt_check": debt_check,
        }

        await update.message.reply_text(
            build_edit_debt_payment_preview_text(preview, debt_payment_conversion, debt_check),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("edit_txn"),
        )
        return

    try:
        updates = parse_edit_updates(update_args)
    except Exception as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000`\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`\n"
            "`/edit_txn 2 account=BRI category=\"Food & Beverage\"`",
            parse_mode="Markdown",
        )
        return

    if not updates:
        await update.message.reply_text(
            "❌ Tidak ada field yang diedit.\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000`",
            parse_mode="Markdown",
        )
        return

    row_index = resolved["row_indices"][0] if resolved["row_indices"] else None
    txn_id = resolved["txn_ids"][0] if resolved["txn_ids"] else None

    preview = preview_edit_transaction_by_ref(
        updates=updates,
        row_index=row_index,
        txn_id=txn_id,
    )

    if not preview.get("success"):
        await update.message.reply_text(
            f"❌ {preview.get('message')}",
            parse_mode="Markdown",
        )
        return

    split_parsed = None
    split_raw = " ".join(update_args)
    if edit_args_contain_split_bill(update_args):
        split_parsed = dict(preview.get("new_txn", {}) or {})
        attach_split_bill_if_any(split_parsed, split_raw)

        if split_bill_needs_decision(split_parsed):
            context.user_data["pending_edit_txn"] = {
                "row_index": row_index,
                "txn_id": txn_id,
                "updates": updates,
                "split_raw": split_raw,
                "split_parsed": split_parsed,
            }
            await update.message.reply_text(
                build_split_bill_prompt_from_parsed(split_parsed),
                parse_mode="Markdown",
                reply_markup=split_bill_keyboard("edit_txn"),
            )
            return

    context.user_data["pending_edit_txn"] = {
        "row_index": row_index,
        "txn_id": txn_id,
        "updates": updates,
        "split_raw": split_raw if split_parsed else "",
        "split_parsed": split_parsed,
    }

    await update.message.reply_text(
        build_edit_split_preview_text(preview, split_parsed),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("edit_txn"),
    )


# ── Callback Handler ─────────────────────────────────────────────────────────

