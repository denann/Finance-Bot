"""Natural message handler that routes text and image input into parser, preview, clarification, debt, split bill, pending, or AI flows."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import (
    ContextTypes,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    Update,
    account_keyboard,
    append_net_gross_note,
    build_pending_expense_from_text,
    build_progress_bar,
    build_transaction_display_lines,
    confirm_keyboard,
    detect_date_result,
    edit_message_safely,
    enrich_transactions_with_debt_info,
    estimate_payment_outcome,
    format_expense_net_gross,
    format_indonesian_date_group_label,
    format_month_label,
    format_rupiah,
    get_account_report,
    get_budget_summary,
    get_daily_report,
    get_debt_by_person,
    get_monthly_report,
    get_net_expense_after_receivable,
    get_recent_transactions,
    get_weekly_report,
    io,
    is_authorized,
    is_pending_expense_text,
    md_code_text,
    md_safe,
    normalize_month,
    os,
    parse_debt_input,
    parse_human_amount,
    parse_report_date_arg,
    parse_report_month_arg,
    parse_sheet_number,
    parse_transactions_from_image,
    preview_delete_transactions_by_refs,
    preview_edit_transaction_by_ref,
    re,
    receipt_ownership_keyboard,
    reject_unauthorized,
    reply_long_markdown,
    reply_update_safely,
    route_intent_with_gemini,
    search_transactions,
    shlex,
    should_try_gemini_intent_router,
    split_account_period_arg,
    split_report_filter_args,
)
# Import app.bot.handler_parts.common_imports so this module can use its helpers.
from app.bot.handler_parts.common_imports import _safe_float_for_display
# Import app.bot.handler_parts.state_utils so this module can use its helpers.
from app.bot.handler_parts.state_utils import BULK_EDIT_CATEGORY_DECISION_KEY, EDIT_CATEGORY_CHOICE_KEY
from app.services.chart_service import write_transaction_timeseries_png

# Import app.bot.handler_parts.networth_assets so this module can use its helpers.
from app.bot.handler_parts.networth_assets import (
    build_asset_confirm_preview,
    build_asset_unit_price_prompt,
    handle_pending_asset_add_flow,
    parse_natural_asset_add,
)
# Import app.bot.handler_parts.health_recurring_export so this module can use its helpers.
from app.bot.handler_parts.health_recurring_export import handle_pending_recurring_add_flow
# Import app.bot.handler_parts.command_router so this module can use its helpers.
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
# Import app.bot.handler_parts.category_flow so this module can use its helpers.
from app.bot.handler_parts.category_flow import handle_pending_category_flow
from app.bot.handler_parts.bulk_flow import handle_pending_bulk_text, start_bulk_flow
# Import app.bot.handler_parts.transaction_flow so this module can use its helpers.
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
# Import app.bot.handler_parts.command_handlers so this module can use its helpers.
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
# Import app.nlp.gemini_parser so this module can use its helpers.
from app.nlp.gemini_parser import parse_with_gemini
# Import app.nlp.regex_parser so this module can use its helpers.
from app.nlp.regex_parser import detect_account, extract_debt_account
# Import app.nlp.parse_safety so this module can use its helpers.
from app.nlp.parse_safety import (
    CLARIFICATION,
    GEMINI_DRAFT_PREVIEW,
    WARNING_PREVIEW,
    assess_parse_safety,
)
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import resolve_category_name

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

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_parse_clarification_prompt(raw, assessment),
        parse_mode="Markdown",
        reply_markup=parse_clarification_keyboard(),
    )


# Helper for try gemini draft for parse safety.
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
    # Validate missing gemini parsed before continuing.
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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return True

    # Prepare text from the incoming input.
    text = update.message.text.strip()
    debt_parsed = parse_debt_input(text)

    # Validate missing debt parsed before continuing.
    if not debt_parsed:
        return False

    # "ditalangin Alpat beli minyak 46k dibagi 4 sama Alpat Opik Sapto"
    # Split bill parsing note: separate the paid transaction from each person share.
    debt_parsed = enrich_ditalangin_split_bill_if_any(debt_parsed, text)
    if debt_parsed and not debt_parsed.get("account"):
        # Extract debt account for validation.
        debt_account = extract_debt_account(text) or detect_account(text)
        if debt_account:
            debt_parsed["account"] = debt_account

    person = debt_parsed.get("person_name")
    intent = debt_parsed.get("intent")

    # Validate missing person before continuing.
    if not person:
        if intent == "add_payable":
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                "❓ Siapa yang Anda hutangi?\n"
                "Contoh: `hutang ke Budi 500rb buat makan`",
                parse_mode="Markdown",
            )
            return True

        if intent == "add_receivable":
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                "❓ Siapa yang meminjam uang ke Anda?\n"
                "Contoh: `Budi minjem 300rb`",
                parse_mode="Markdown",
            )
            return True

        if intent == "add_payment":
            # Send the Telegram response before continuing.
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
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_debt_account_prompt(debt_parsed),
            parse_mode="Markdown",
            reply_markup=account_keyboard("debt_acc"),
        )
        return True

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        f"{build_debt_initial_preview(debt_parsed)}\n\n{preview_action_question(True)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("debt", True),
    )

    return True

async def handle_gemini_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Handle the asynchronous handle gemini intent flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.
        user_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing should try gemini intent router(user text) before continuing.
    if not should_try_gemini_intent_router(user_text):
        return False

    # Build router result for the response flow.
    router_result = route_intent_with_gemini(user_text)

    intent = router_result.get("intent", "unknown")
    confidence = float(router_result.get("confidence", 0) or 0)
    args = router_result.get("args", {}) or {}

    if confidence < GEMINI_INTENT_CONFIDENCE_CLARIFY:
        return False

    if confidence < GEMINI_INTENT_CONFIDENCE_EXECUTE:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_gemini_low_confidence_text(router_result),
            parse_mode="Markdown",
        )
        return True

    # ── Non-destructive intents ───────────────────────────────────────────────

    if intent == "help":
        # Await help handler before continuing.
        await help_handler(update, context)
        return True

    if intent == "saldo":
        # Await saldo handler before continuing.
        await saldo_handler(update, context)
        return True

    if intent == "harian":
        # Await harian handler before continuing.
        await harian_handler(update, context)
        return True

    if intent == "mingguan":
        # Await mingguan handler before continuing.
        await mingguan_handler(update, context)
        return True

    if intent == "bulanan":
        # Await bulanan handler before continuing.
        await bulanan_handler(update, context)
        return True

    if intent == "hutang":
        # Await hutang handler before continuing.
        await hutang_handler(update, context)
        return True

    if intent == "budget_history":
        # Await budget history handler before continuing.
        await budget_history_handler(update, context)
        return True

    if intent == "last":
        limit, period, month, title = router_args_to_last_filter(args)

        transactions = get_recent_transactions(
            limit=limit,
            # Extract period for validation.
            period=period,
            month=month,
        )

        # Validate missing transactions before continuing.
        if not transactions:
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                f"📭 Tidak ada transaksi untuk filter: *{title}*",
                parse_mode="Markdown",
            )
            return True

        last_map = {}

        # Iterate through each i, txn.
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_last_transactions_text(transactions, title),
            parse_mode="Markdown",
        )
        return True

    if intent == "cari":
        query = str(args.get("query") or "").strip()

        # Validate missing query before continuing.
        if not query:
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                "🔍 Mau cari transaksi apa?\n\n"
                "Contoh:\n"
                "`cari kopi`\n"
                "`/cari kopi`",
                parse_mode="Markdown",
            )
            return True

        # Build results for the response flow.
        results = search_transactions(query)

        # Validate missing results before continuing.
        if not results:
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                f"🔍 Tidak ada transaksi dengan keyword *{md_safe(query)}*.",
                parse_mode="Markdown",
            )
            return True

        lines = [f"🔍 *Hasil pencarian: \"{md_safe(query)}\"*\n"]

        # Iterate through each t.
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

        # Run this operation in a guarded block so failures can be handled.
        try:
            # Normalize normalized month before matching.
            normalized_month = normalize_month(month)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Normalize normalized month before matching.
            normalized_month = normalize_month(None)

        # Build summary for the response flow.
        summary = get_budget_summary(normalized_month)

        # Validate missing summary before continuing.
        if not summary:
            # Send the Telegram response before continuing.
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

        # Iterate through each item.
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

        # Validate missing ref before continuing.
        if not ref:
            # Send the Telegram response before continuing.
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
            # Send the Telegram response before continuing.
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
            # Send the Telegram response before continuing.
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

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_delete_preview_text(preview),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("delete_txns"),
        )
        return True

    if intent == "edit_txn":
        ref = str(args.get("ref") or "").strip()
        # Extract updates for validation.
        updates = extract_edit_updates_from_router(args)

        # Validate missing ref before continuing.
        if not ref:
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                "❌ Saya menangkap intent edit transaksi, tapi nomor/ID transaksinya belum jelas.\n\n"
                "Contoh:\n"
                "`edit transaksi nomor 2 jadi 15000`\n"
                "`/edit_txn 2 amount=15000`",
                parse_mode="Markdown",
            )
            return True

        # Validate missing updates before continuing.
        if not updates:
            # Send the Telegram response before continuing.
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
            # Send the Telegram response before continuing.
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

        # Run this operation in a guarded block so failures can be handled.
        try:
            preview = preview_edit_transaction_by_ref(
                # Extract updates for validation.
                updates=updates,
                row_index=row_index,
                txn_id=txn_id,
            )
        # Handle an expected failure from the guarded operation above.
        except NameError:
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                "❌ Gemini sudah menangkap intent edit, tapi fitur `/edit_txn` belum terpasang penuh di kode.\n\n"
                "Pasang Phase `edit_txn` dulu, lalu fitur natural edit bisa aktif.",
                parse_mode="Markdown",
            )
            return True

        if not preview.get("success"):
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                f"❌ {preview.get('message')}",
                parse_mode="Markdown",
            )
            return True

        if await maybe_prompt_edit_category_choice(
            update,
            context,
            # Extract updates for validation.
            updates=updates,
            # Build preview for the response flow.
            preview=preview,
            row_index=row_index,
            txn_id=txn_id,
            split_raw="",
            has_split_bill=False,
        ):
            return True

        context.user_data["pending_edit_txn"] = {
            "row_index": row_index,
            "txn_id": txn_id,
            "updates": updates,
        }

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_edit_preview_text(preview),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("edit_txn"),
        )
        return True

    return False


# Helper for normalize text command.
def normalize_text_command(text: str) -> str:
    """Normalize input values for the normalize text command workflow in the Telegram handler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    clean = str(text or "").strip().lower()
    clean = re.sub(r"\s+", " ", clean)
    return clean


# Handle the asynchronous handle local natural intent workflow.
async def handle_local_natural_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Handle the asynchronous handle local natural intent flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.
        user_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Normalize clean before matching.
    clean = normalize_text_command(user_text)

    # Validate missing clean before continuing.
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
        # Await saldo handler before continuing.
        await saldo_handler(update, context)
        return True

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
        # Await hutang handler before continuing.
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
        # Build summary for the response flow.
        summary = get_budget_summary(normalize_month(None))

        # Validate missing summary before continuing.
        if not summary:
            month = normalize_month(None)
            # Send the Telegram response before continuing.
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

        # Iterate through each item.
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
        # Load transactions for the current calculation.
        transactions = get_recent_transactions(limit=10)

        # Validate missing transactions before continuing.
        if not transactions:
            await update.message.reply_text("📭 Belum ada transaksi.")
            return True

        last_map = {}
        # Iterate through each i, txn.
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        # Send the Telegram response before continuing.
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

        # Validate missing transactions before continuing.
        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi hari ini.")
            return True

        last_map = {}
        # Iterate through each i, txn.
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        # Send the Telegram response before continuing.
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

        # Validate missing transactions before continuing.
        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi minggu ini.")
            return True

        last_map = {}
        # Iterate through each i, txn.
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        # Send the Telegram response before continuing.
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

        # Validate missing transactions before continuing.
        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi bulan ini.")
            return True

        last_map = {}
        # Iterate through each i, txn.
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        # Send the Telegram response before continuing.
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

        # Validate missing keyword before continuing.
        if not keyword:
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                "🔍 Mau cari transaksi apa?\n\n"
                "Contoh:\n"
                "`cari kopi`",
                parse_mode="Markdown",
            )
            return True

        # Build results for the response flow.
        results = search_transactions(keyword)

        # Validate missing results before continuing.
        if not results:
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                f"🔍 Tidak ada transaksi dengan keyword *{md_safe(keyword)}*.",
                parse_mode="Markdown",
            )
            return True

        lines = [f"🔍 *Hasil pencarian: \"{md_safe(keyword)}\"*\n"]

        # Iterate through each t.
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

# Handle the asynchronous continue receipt batch after selection workflow.
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

    # Build preview for the response flow.
    preview = build_mixed_detail_preview(mixed_items, receipt_context)
    # Send the Telegram response before continuing.
    await reply_update_safely(
        update,
        f"{preview}\n\n{preview_action_question(False)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("mixed", False),
    )


# Handle the asynchronous handle pending receipt selection workflow.
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
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                "❌ Jumlah pembaginya belum kebaca. Contoh: `dibagi 5`.",
                parse_mode="Markdown",
            )
            return True

        receipt = divisor_state.get("receipt") or {}
        selection_result = divisor_state.get("selection_result") or {}
        mixed_items, receipt_context = build_receipt_partial_mixed_items(receipt, selection_result, divisor)
        # Await  continue receipt batch after selection before continuing.
        await _continue_receipt_batch_after_selection(update, context, mixed_items, receipt_context)
        return True

    selection_state = context.user_data.get("pending_receipt_part_selection")
    # Validate missing selection state before continuing.
    if not selection_state:
        return False

    receipt = selection_state.get("receipt") or {}
    items = selection_state.get("items") or []
    # Build selection result for the response flow.
    selection_result = parse_receipt_part_selection(user_text, items)

    if not selection_result.get("success"):
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"❌ {selection_result.get('message')}\n\n{build_receipt_part_selection_prompt(receipt, items)}",
            parse_mode="Markdown",
        )
        return True

    # Handle receipt extra charge net amount(receipt) > 0.
    if receipt_extra_charge_net_amount(receipt) > 0:
        context.user_data["pending_receipt_extra_divisor"] = {
            "receipt": receipt,
            "selection_result": selection_result,
        }
        context.user_data.pop("pending_receipt_part_selection", None)
        # Send the Telegram response before continuing.
        await reply_update_safely(
            update,
            build_receipt_selected_breakdown(receipt, selection_result),
            parse_mode="Markdown",
        )
        return True

    mixed_items, receipt_context = build_receipt_partial_mixed_items(receipt, selection_result, divisor=1)
    # Await  continue receipt batch after selection before continuing.
    await _continue_receipt_batch_after_selection(update, context, mixed_items, receipt_context)
    return True


# ── Image / Receipt Handler ──────────────────────────────────────────────────

async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous image handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    message = update.message
    # Validate missing message before continuing.
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
    # Use the fallback path when no earlier branch matched.
    else:
        await message.reply_text("❌ File yang dikirim belum terbaca sebagai gambar.")
        return

    # Image parsing note: receipt output still goes through preview before saving.
    if file_size and file_size > 10 * 1024 * 1024:
        # Send the Telegram response before continuing.
        await message.reply_text(
            "❌ Gambar terlalu besar. Kirim gambar di bawah 10 MB."
        )
        return

    status_msg = await message.reply_text(
        "🖼️ Membaca gambar dengan Gemini...\n"
        "Pastikan gambar tidak berisi data sensitif seperti nomor rekening lengkap, password, atau OTP."
    )

    # Run this operation in a guarded block so failures can be handled.
    try:
        tg_file = await context.bot.get_file(file_id)
        # Run this operation in a guarded block so failures can be handled.
        try:
            image_bytes = await tg_file.download_as_bytearray()
        # Handle an expected failure from the guarded operation above.
        except AttributeError:
            buffer = io.BytesIO()
            # Await tg file.download to memory before continuing.
            await tg_file.download_to_memory(buffer)
            image_bytes = buffer.getvalue()
    # Handle an expected failure from the guarded operation above.
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
        # Await status msg.edit text before continuing.
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

        # Send the Telegram response before continuing.
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
            # Await status msg.edit text before continuing.
            await status_msg.edit_text(
                build_split_bill_prompt_from_parsed(parsed),
                parse_mode="Markdown",
                reply_markup=split_bill_keyboard("single"),
            )
            return

        if needs_account(parsed):
            # Await status msg.edit text before continuing.
            await status_msg.edit_text(
                build_single_account_prompt(parsed),
                parse_mode="Markdown",
                reply_markup=account_keyboard("acc"),
            )
            return

        # Build preview for the response flow.
        preview = build_preview(parsed)
        # Await status msg.edit text before continuing.
        await status_msg.edit_text(
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("single", True),
        )
        return

    # Image parsing note: receipt output still goes through preview before saving.
    mixed_items = []
    # Iterate through each idx, parsed.
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

    # Build preview for the response flow.
    preview = build_mixed_detail_preview(mixed_items)

    if mixed_split_bill_needs_decision(mixed_items):
        # Send the Telegram response before continuing.
        await edit_message_safely(
            status_msg,
            build_mixed_split_bill_queue_prompt(mixed_items),
            parse_mode="Markdown",
            reply_markup=mixed_split_bill_keyboard(mixed_items),
        )
    # Use the fallback path when no earlier branch matched.
    else:
        # Send the Telegram response before continuing.
        await edit_message_safely(
            status_msg,
            f"{preview}\n\n{preview_action_question(False)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", False),
        )

# Message handling section


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Prepare user text from the incoming input.
    user_text = update.message.text.strip()

    if user_text.startswith("/"):
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "⚠️ Input ini terlihat seperti command, jadi tidak saya parse sebagai transaksi.\n\n"
            "Cek command dengan `/help`, atau tulis transaksi tanpa awalan `/`." ,
            parse_mode="Markdown",
        )
        return

    input_lines = split_user_inputs(user_text)
    is_multi_input = bool(re.search(r"[\n\r;,]", user_text)) or len(input_lines) > 1

    explicit_date = detect_date_result(user_text)
    if not is_multi_input and explicit_date.status == "invalid":
        await update.message.reply_text(
            "❌ Tanggal yang ditulis tidak valid.\n\n"
            f"Input tanggal: `{md_code_text(explicit_date.explicit_input)}`\n"
            "Gunakan tanggal kalender yang benar, misalnya `29/02/2024` atau `2026-07-10`.",
            parse_mode="Markdown",
        )
        return

    receipt_selection_handled = await handle_pending_receipt_selection(update, context, user_text)
    if receipt_selection_handled:
        return

    bulk_text_handled = await handle_pending_bulk_text(update, context, user_text)
    if bulk_text_handled:
        return

    # Extract missing amount handled for validation.
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
        # Validate missing shares before continuing.
        if not shares:
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                "❌ Pembagian belum kebaca. Tulis dalam format seperti `saya 30k, Budi 50k` atau `saya 100%, Budi 100%`.",
                parse_mode="Markdown",
            )
            return

        meal_split_state["shares"] = shares
        meal_split_state["allocation_mode"] = "custom"
        meal_split_state["stage"] = "status"
        context.user_data["pending_meal_split"] = meal_split_state
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_meal_split_status_prompt(meal_split_state),
            parse_mode="Markdown",
            reply_markup=meal_split_status_keyboard(meal_split_state.get("payer") or "self"),
        )
        return

    # Build preview edit handled for the response flow.
    preview_edit_handled = await handle_pending_preview_edit(update, context, user_text)
    if preview_edit_handled:
        return

    # Category wizard consumes text replies before they can be parsed as transactions.
    category_flow_handled = await handle_pending_category_flow(update, context, user_text)
    if category_flow_handled:
        return

    recurring_add_flow_handled = await handle_pending_recurring_add_flow(update, context, user_text)
    if recurring_add_flow_handled:
        return

    asset_add_flow_handled = await handle_pending_asset_add_flow(update, context, user_text)
    if asset_add_flow_handled:
        return

    # Pending expense section
    pending_asset = context.user_data.get("pending_asset_price")
    if pending_asset:
        unit_price = parse_human_amount(user_text)

        if unit_price <= 0:
            # Send the Telegram response before continuing.
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

        # Send the Telegram response before continuing.
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
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                build_asset_unit_price_prompt(natural_asset),
                parse_mode="Markdown",
            )
            return

        context.user_data["pending_asset_confirm"] = natural_asset
        context.user_data.pop("pending_asset_price", None)
        # Send the Telegram response before continuing.
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
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_social_spending_guard_prompt(user_text, social_guard),
            parse_mode="Markdown",
            reply_markup=social_spending_guard_keyboard(),
        )
        return


    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.

    # Jadi:
    # Account flow section
    # - "cari kopi" -> search
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

    # Pending expense section
    if is_pending_expense_text(user_text):
        # Run this operation in a guarded block so failures can be handled.
        try:
            item = build_pending_expense_from_text(user_text)
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            # Send the Telegram response before continuing.
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
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"{build_pending_expense_confirm_preview(item, include_question=False)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("pending_expense", True),
        )
        return

    if is_multi_input and len(input_lines) > 1:
        await start_bulk_flow(update, context, input_lines)
        return

    selected_debt_settle_handled = await handle_natural_debt_settle(update, context, user_text)
    if selected_debt_settle_handled:
        return

    # Phase 2: explicit debt/split/talangin intent must win before parse safety.
    early_debt_parsed = parse_debt_input(user_text)
    if early_debt_parsed:
        debt_handled = await debt_message_handler(update, context)
        if debt_handled:
            return

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    finance_question_handled = await handle_natural_finance_question(
        update,
        context,
        user_text,
    )

    if finance_question_handled:
        return

    # Example cleanup: remove the person prefix so the description stays focused on the expense item.
    pre_parse_assessment = assess_parse_safety(user_text, {})
    if pre_parse_assessment.get("recommended_action") == CLARIFICATION:
        # Send the Telegram response before continuing.
        await send_parse_clarification(update, context, user_text, {}, pre_parse_assessment)
        return

    if not is_multi_input:
        full_debt_parsed = parse_debt_input(user_text)
        if full_debt_parsed:
            debt_handled = await debt_message_handler(update, context)
            if debt_handled:
                return

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
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
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_missing_amount_prompt(user_text, missing_amount_income),
            parse_mode="Markdown",
        )
        return

    # Single transaction
    parsed = parse_input(user_text)

    if parsed.get("type") == "pending":
        # Account flow section
        # - cari kopi
        # Date parsing note: keep explicit and relative Indonesian date formats predictable.
        local_natural_handled = await handle_local_natural_intent(
            update,
            context,
            user_text,
        )

        if local_natural_handled:
            return

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
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                command_typo_feedback,
                parse_mode="Markdown",
            )
            return

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_gemini_fallback_text(),
            parse_mode="Markdown",
        )
        return

    attach_split_bill_if_any(parsed, user_text)

    safety_assessment = assess_parse_safety(user_text, parsed)
    safety_action = safety_assessment.get("recommended_action")

    if safety_action == CLARIFICATION:
        # Send the Telegram response before continuing.
        await send_parse_clarification(update, context, user_text, parsed, safety_assessment)
        return

    preview_mode = "normal"
    if safety_action == GEMINI_DRAFT_PREVIEW:
        parsed, safety_assessment, gemini_used = try_gemini_draft_for_parse_safety(user_text, parsed, safety_assessment)
        preview_mode = "gemini" if gemini_used else "warning"
    # Fall back when safety action == WARNING PREVIEW.
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
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_split_bill_prompt_from_parsed(parsed),
            parse_mode="Markdown",
            reply_markup=split_bill_keyboard("single"),
        )
    # Fall back when needs account(parsed).
    elif needs_account(parsed):
        # Send the Telegram response before continuing.
        await reply_update_safely(
            update,
            build_single_account_prompt(
                parsed,
                preview_text=preview if preview_mode in {"warning", "gemini"} else None,
            ),
            parse_mode="Markdown",
            reply_markup=account_keyboard("acc"),
        )
    # Use the fallback path when no earlier branch matched.
    else:
        # Send the Telegram response before continuing.
        await reply_update_safely(
            update,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("single", True),
        )


# Helper for build transactions full text.
def build_transactions_full_text(transactions: list[dict], title: str, account_filter: str | None = None) -> str:
    """Build the data structure or message text for transactions full text."""
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
        lines.append(
            "\n*Ringkasan Rekening:*\n"
            f"✅ Income          : *{format_rupiah(total_income)}*\n"
            f"❌ Expense         : *{expense_text}*\n"
            f"🔁 Transfer Masuk  : *{format_rupiah(total_transfer_in)}*\n"
            f"🔁 Transfer Keluar : *{format_rupiah(total_transfer_out)}*\n"
            f"📊 Net Rekening    : *{net_text}*\n"
            f"📝 Total           : *{len(transactions)} transaksi*"
        )
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

# Helper for build transaction filter title.
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


# Handle the asynchronous send transaction timeseries chart workflow.
async def send_transaction_timeseries_chart(update: Update, transactions: list[dict], title: str) -> None:
    """Send an automatic PNG time-series chart for transaction list commands.

    Args:
        update: Telegram update used to send the PNG as a document.
        transactions: Transaction rows already displayed by `/transaksi` or
            `/last`.
        title: The same user-facing title used by the transaction list output.

    Returns:
        None. Failures are reported as a warning message after the transaction
        list, without blocking the list output itself.

    Side effects:
        Creates a temporary PNG file, sends it through Telegram, and deletes the
        file afterward. It does not write to Google Sheets.

    Flow constraints:
        The chart must represent the displayed rows only, so filtered
        transaction outputs receive filtered time-series charts.
    """
    chart_path = ""
    # Keep chart generation separate from the text list so list output remains primary.
    try:
        chart_path = write_transaction_timeseries_png(transactions, f"Time Series - {title}")
        filename = "grafik-transaksi-timeseries.png"
        caption = (
            f"📈 Grafik time series: {title}\n"
            "Basis angka: pengeluaran net dari transaksi yang ditampilkan."
        )
        # Open the generated file only while Telegram sends the document.
        with open(chart_path, "rb") as file_obj:
            await update.message.reply_document(
                document=InputFile(file_obj, filename=filename),
                caption=caption,
            )
    # Report chart-only failures without changing transaction list behavior.
    except Exception as e:
        await update.message.reply_text(f"⚠️ Transaksi sudah terkirim, tapi grafik time series gagal dibuat: {str(e)}")
    # Remove the temporary PNG after successful send or chart failure.
    finally:
        if chart_path:
            try:
                os.remove(chart_path)
            except OSError:
                pass


# Helper for build transaksi prefixed period arg.
def _build_transaksi_prefixed_period_arg(first: str, rest: str, mode: str) -> str | None:
    """Build the data structure or message text for transaksi prefixed period arg."""
    rest = str(rest or "").strip()
    # Validate missing rest before continuing.
    if not rest:
        return None

    first_rest = rest.split()[0].strip().lower()

    if mode == "month" and first_rest in {"ini", "lalu", "depan"}:
        return f"{first} {rest}"

    if mode == "date" and first_rest in {"ini", "lalu", "depan"}:
        return f"{first} {rest}"

    return rest


# Helper for parse transaksi period.
def parse_transaksi_period(args: list[str]) -> tuple[str, list[dict], str, str | None]:
    """Parse caller input for the parse transaksi period workflow in the Telegram handler layer.

    Args:
        args: Command argument list or parsed argument values supplied by the caller.

    Returns:
        `tuple[str, list[dict], str, str | None]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = " ".join(args or []).strip()
    low = raw.lower()

    # Validate missing raw before continuing.
    if not raw:
        year, month_num = parse_report_month_arg(None)
        report = get_monthly_report(year, month_num)
        return f"Transaksi Bulan {report.get('month', '-')}", report.get("transactions", []), "month", None

    first = low.split()[0]
    rest = " ".join(raw.split()[1:]).strip()

    if first in ["rekening", "akun", "account", "rek"]:
        account_arg, period_arg = split_account_period_arg(rest)
        # Validate missing account arg before continuing.
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
        # Extract date arg for validation.
        date_arg = parse_report_date_arg(raw)
        report = get_daily_report(date_arg)
        return f"Transaksi Tanggal {report.get('date', '-')}", report.get("transactions", []), "day", None
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass

    # Run this operation in a guarded block so failures can be handled.
    try:
        month_arg, category_arg, account_arg = split_report_filter_args(raw, "month")
        # Handle month arg or category arg or account arg.
        if month_arg or category_arg or account_arg:
            year, month_num = parse_report_month_arg(month_arg)
            report = get_monthly_report(year, month_num, category_arg, account_arg)
            title = build_transaction_filter_title(
                f"Transaksi Bulan {report.get('month', '-')}",
                report.get("category_filter"),
                report.get("account_filter"),
            )
            return title, report.get("transactions", []), "month", report.get("account_filter")
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass

    # Raise a clear error so the caller can stop this invalid flow.
    raise ValueError(
        "Format /transaksi tidak dikenali. Contoh: /transaksi 2026-06, /transaksi bulan lalu, /transaksi Food & Beverage 2026-06, /transaksi rekening Cash bulan lalu."
    )


async def transaksi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous transaksi handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        title, transactions, _period_type, account_filter = parse_transaksi_period(context.args)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Send the Telegram response before continuing.
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

    # Validate missing transactions before continuing.
    if not transactions:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"📭 Tidak ada transaksi untuk filter: *{md_safe(title)}*",
            parse_mode="Markdown",
        )
        return

    last_map = {}
    # Iterate through each i, txn.
    for i, txn in enumerate(transactions, 1):
        if txn.get("_row_index"):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

    context.user_data["last_txn_map"] = last_map
    # Send the Telegram response before continuing.
    await reply_long_markdown(update, build_transactions_full_text(transactions, title, account_filter))
    # Send the matching read-only time-series chart after the transaction list.
    await send_transaction_timeseries_chart(update, transactions, title)


async def last_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous last handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Prepare args from the incoming input.
    args = context.args

    limit = 10
    # Extract period for validation.
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

        # Use the fallback path when no earlier branch matched.
        else:
            # Send the Telegram response before continuing.
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
        # Extract period for validation.
        period=period,
        month=month,
    )

    # Validate missing transactions before continuing.
    if not transactions:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"📭 Tidak ada transaksi untuk filter: *{title}*",
            parse_mode="Markdown",
        )
        return

    last_map = {}

    # Iterate through each i, txn.
    for i, txn in enumerate(transactions, 1):
        last_map[str(i)] = {
            "id": str(txn.get("id", "")),
            "row_index": int(txn.get("_row_index")),
        }

    context.user_data["last_txn_map"] = last_map

    # Send the Telegram response before continuing.
    await reply_long_markdown(update, build_last_transactions_text(transactions, title))
    # Send the matching read-only time-series chart after the transaction list.
    await send_transaction_timeseries_chart(update, transactions, title)


async def delete_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous delete txn handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    refs = context.args

    # Validate missing refs before continuing.
    if not refs:
        # Send the Telegram response before continuing.
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
        # Send the Telegram response before continuing.
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
        # Send the Telegram response before continuing.
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

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_delete_preview_text(preview),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("delete_txns"),
    )

# Helper for parse edit updates.
def parse_edit_updates(args: list[str]) -> dict:
    """Parse caller input for the parse edit updates workflow in the Telegram handler layer.

    Args:
        args: Command argument list or parsed argument values supplied by the caller.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing args before continuing.
    if not args:
        return {}

    if len(args) == 1:
        first = args[0].strip()
        if re.fullmatch(r"\d+(?:[.,]\d+)?(?:\s*(?:rb|ribu|k|jt|juta|m))?", first, flags=re.IGNORECASE):
            return {"amount": first.replace(",", ".")}

    split_words = {"dibagi", "bagi", "patungan", "split", "share"}
    # Extract updates for validation.
    updates = {}
    i = 0

    # Repeat this block while i < len(args).
    while i < len(args):
        arg = str(args[i] or "").strip()
        low = arg.lower()

        # Validate missing arg before continuing.
        if not arg:
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Split bill parsing note: separate the paid transaction from each person share.
        if low in split_words or low.replace("-", "") in {"dibagi"}:
            # Leave the loop after the target condition has been reached.
            break

        # Mendukung: amount = 500k
        if i + 2 < len(args) and args[i + 1] == "=":
            key = arg
            value = str(args[i + 2]).strip()
            updates[key] = value
            i += 3
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Supports both `amount=500k` and `amount= 500k`.
        if "=" in arg:
            key, value = arg.split("=", 1)
            key = key.strip()
            value = value.strip()
            if value == "" and i + 1 < len(args):
                value = str(args[i + 1]).strip()
                i += 2
            # Use the fallback path when no earlier branch matched.
            else:
                i += 1

            if not key or value == "":
                raise ValueError(f"Argumen `{arg}` tidak valid. Gunakan format key=value.")
            updates[key] = value
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Implementation note for this project-specific finance flow.
        if not updates and re.fullmatch(r"\d+(?:[.,]\d+)?(?:\s*(?:rb|ribu|k|jt|juta|m))?", arg, flags=re.IGNORECASE):
            updates["amount"] = arg
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Raise a clear error so the caller can stop this invalid flow.
        raise ValueError(
            f"Argumen `{arg}` tidak valid. Gunakan format key=value."
        )

    return updates


# Helper for edit args contain split bill.
def edit_args_contain_split_bill(args: list[str]) -> bool:
    """Coordinate the edit args contain split bill logic in the Telegram handler layer.

    Args:
        args: Command argument list or parsed argument values supplied by the caller.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = " ".join(str(x or "") for x in args)
    return bool(re.search(r"\b(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)\b", raw, flags=re.IGNORECASE))


# Helper for normalize edit arg token.
def _normalize_edit_arg_token(token: str) -> str:
    """Normalize input values for the normalize edit arg token workflow in the Telegram handler layer.

    Args:
        token: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    return str(token or "").strip().lower().replace("_", "-")


# Helper for parse edit debt payment conversion args.
def parse_edit_debt_payment_conversion_args(args: list[str]) -> dict | None:
    """Parse caller input for the parse edit debt payment conversion args workflow in the Telegram handler layer.

    Args:
        args: Command argument list or parsed argument values supplied by the caller.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Validate missing args before continuing.
    if not args:
        return None

    raw_tokens = [str(x or "").strip() for x in args if str(x or "").strip()]
    # Validate missing raw tokens before continuing.
    if not raw_tokens:
        return None

    target_type = ""
    explicit_person = ""
    field_tokens: list[str] = []
    person_tokens: list[str] = []
    # Extract consume person for validation.
    consume_person = False
    found_marker = False

    i = 0
    # Repeat this block while i < len(raw_tokens).
    while i < len(raw_tokens):
        token = raw_tokens[i]
        low = _normalize_edit_arg_token(token)

        # Explicit fields khusus conversion.
        if "=" in token:
            key, value = token.split("=", 1)
            key_low = key.strip().lower().replace("_", "-")
            # Normalize value clean before matching.
            value_clean = value.strip()

            if key_low in {"debt", "debt-type", "tipe-hutang", "tipehutang", "hutang-type", "jenis-debt"}:
                found_marker = True
                value_low = value_clean.lower()
                if value_low in {"payable", "utang", "hutang", "bayar-utang", "bayar-hutang"}:
                    target_type = "payable"
                elif value_low in {"receivable", "piutang", "bayar-piutang"}:
                    target_type = "receivable"
                # Use the fallback path when no earlier branch matched.
                else:
                    raise ValueError("Nilai debt harus payable/utang/hutang atau receivable/piutang.")
                i += 1
                # Skip the rest of this loop iteration after handling this case.
                continue

            if key_low in {"person", "orang", "nama", "ke", "dari", "sama"}:
                # Extract explicit person for validation.
                explicit_person = value_clean
                i += 1
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Append the current value to field tokens.
            field_tokens.append(token)
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        compact = low.replace("-", "")
        if compact in {"bayarhutang", "bayarutang", "pembayaranhutang", "pembayaranutang", "hutang", "utang"}:
            target_type = "payable"
            found_marker = True
            # Extract consume person for validation.
            consume_person = True
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        if compact in {"bayarpiutang", "pembayaranpiutang", "piutang"}:
            target_type = "receivable"
            found_marker = True
            # Extract consume person for validation.
            consume_person = True
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        next_low = _normalize_edit_arg_token(raw_tokens[i + 1]) if i + 1 < len(raw_tokens) else ""
        next_compact = next_low.replace("-", "")
        if compact in {"bayar", "pembayaran", "payment", "jadi", "menjadi", "ubah", "konversi", "convert"} and next_compact in {"hutang", "utang", "piutang"}:
            target_type = "receivable" if next_compact == "piutang" else "payable"
            found_marker = True
            # Extract consume person for validation.
            consume_person = True
            i += 2
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Split bill parsing note: separate the paid transaction from each person share.
        if consume_person and compact in {"ke", "dari", "sama", "dengan", "untuk", "sebagai"}:
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Split bill parsing note: separate the paid transaction from each person share.
        if consume_person:
            # Append the current value to person tokens.
            person_tokens.append(token)
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Append the current value to field tokens.
        field_tokens.append(token)
        i += 1

    # Validate missing found marker before continuing.
    if not found_marker:
        return None

    person = explicit_person or " ".join(person_tokens).strip()
    person = re.sub(r"\s+", " ", person).strip()
    person = re.sub(r"^(ke|dari|sama|dengan|untuk)\s+", "", person, flags=re.IGNORECASE).strip()

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    person = re.sub(r"\s+\w+\s*=.*$", "", person).strip()

    # Validate missing target type before continuing.
    if not target_type:
        raise ValueError("Tipe pembayaran debt belum jelas. Gunakan bayar_hutang atau bayar_piutang.")
    # Validate missing person before continuing.
    if not person:
        raise ValueError("Nama orang belum jelas. Contoh: /edit_txn 2 bayar_hutang Sapto")

    # Extract extra updates for validation.
    extra_updates = parse_edit_updates(field_tokens) if field_tokens else {}

    return {
        "target_type": target_type,
        "person_name": person.title(),
        "extra_updates": extra_updates,
    }


# Helper for build debt payment conversion updates.
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
    # Use the fallback path when no earlier branch matched.
    else:
        raise ValueError("Tipe pembayaran debt tidak valid.")

    return updates


# Helper for validate edit debt payment conversion.
def validate_edit_debt_payment_conversion(conversion: dict, amount: float) -> dict:
    """Validate data before it is used by edit debt payment conversion."""
    person = str(conversion.get("person_name") or "").strip().title()
    target_type = str(conversion.get("target_type") or "").strip().lower()
    label = "utang" if target_type == "payable" else "piutang"

    # Load debts for the current calculation.
    debts = get_debt_by_person(person)
    target_debts = [
        d for d in debts
        if str(d.get("type", "")).strip() == target_type
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
    ]
    total_remaining = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in target_debts)

    # Validate missing target debts or total remaining <= 0 before continuing.
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


# Helper for build edit debt payment preview text.
def build_edit_debt_payment_preview_text(preview: dict, conversion: dict, debt_check: dict) -> str:
    """Build the data structure or message text for edit debt payment preview text."""
    # Prepare text from the incoming input.
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


# Helper for build edit split preview text.
def build_edit_split_preview_text(preview: dict, split_parsed: dict | None = None) -> str:
    """Build the data structure or message text for edit split preview text."""
    # Prepare text from the incoming input.
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


# Helper for build edit preview text.
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
        # Iterate through each field, value.
        for field, value in updates.items():
            lines.append(f"• {field}: `{value}`")

    if net_deltas:
        lines.append("\n*Efek ke saldo:*")
        # Iterate through each account, delta.
        for account, delta in net_deltas.items():
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {account}: {sign}{format_rupiah(abs(delta))}")
    # Use the fallback path when no earlier branch matched.
    else:
        lines.append("\n*Efek ke saldo:*")
        lines.append("• Tidak ada perubahan saldo")

    lines.append("\nSimpan perubahan ini?")

    return "\n".join(lines)


# Helper for build edit category choice keyboard.
def build_edit_category_choice_keyboard(suggested_category: str) -> InlineKeyboardMarkup:
    """Build the category match decision keyboard for `/edit_txn`.

    Args:
        suggested_category: Existing category name suggested by the resolver.

    Returns:
        Inline keyboard with two decision buttons: use existing category or
        start a new category flow, plus a cancel button.
    """
    # Telegram button text has a practical length limit, so long categories are trimmed.
    clean_suggestion = str(suggested_category or "-").strip()
    label = clean_suggestion if len(clean_suggestion) <= 34 else clean_suggestion[:31].rstrip() + "..."
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Ikuti {label}", callback_data="edit_category_choice:use")],
        [InlineKeyboardButton("➕ Tambah kategori baru", callback_data="edit_category_choice:create")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:edit_txn")],
    ])


# Helper for build bulk edit category choice keyboard.
def build_bulk_edit_category_choice_keyboard(suggested_category: str) -> InlineKeyboardMarkup:
    """Build the category decision keyboard for bulk `/edit_txn`.

    Args:
        suggested_category: Existing category name suggested by the resolver for
            the current bulk-edit line.

    Returns:
        Inline keyboard with `Ikuti`, `Tambah kategori baru`, and `Batal`.
        Callback data is intentionally scoped with `bulk_edit_category_choice`
        so it cannot be confused with the single edit category callback.
    """
    # Keep long category names readable inside Telegram button limits.
    clean_suggestion = str(suggested_category or "-").strip()
    label = clean_suggestion if len(clean_suggestion) <= 34 else clean_suggestion[:31].rstrip() + "..."
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Ikuti {label}", callback_data="bulk_edit_category_choice:use")],
        [InlineKeyboardButton("➕ Tambah kategori baru", callback_data="bulk_edit_category_choice:create")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:bulk_edit_category")],
    ])


# Helper for build bulk edit category choice text.
def build_bulk_edit_category_choice_text(decision: dict, current_number: int, total: int) -> str:
    """Build the per-line category decision prompt for bulk edit.

    Args:
        decision: Queue item with `line_no`, `raw_category`, and
            `suggested_category`.
        current_number: 1-based position of the active decision in the queue.
        total: Total number of category decisions in the queue.

    Returns:
        Markdown prompt matching the requested bulk category clarification
        wording.
    """
    line_no = int((decision or {}).get("line_no") or current_number)
    raw_category = str((decision or {}).get("raw_category") or "-").strip()
    suggested = str((decision or {}).get("suggested_category") or "-").strip()
    return (
        f"Baris {line_no}: input kategori `{md_code_text(raw_category)}` cocok ke "
        f"`{md_code_text(suggested)}`. Mau ikuti kategori existing atau tambah kategori baru?\n\n"
        f"Decision {current_number}/{total}"
    )


# Helper for get edit category choice prompt.
def get_edit_category_choice_prompt(updates: dict, preview: dict) -> dict | None:
    """Detect whether `/edit_txn category=...` needs category confirmation.

    Args:
        updates: Parsed edit updates from `parse_edit_updates`.
        preview: Preview dict from `preview_edit_transaction_by_ref`. The old
            and new transaction type are used to restrict category matching.

    Returns:
        A prompt payload containing raw category, suggested category, resolver
        status, and transaction type. Returns `None` when the category is exact
        or no category field is being edited.
    """
    if "category" not in (updates or {}):
        return None

    raw_category = str((updates or {}).get("category") or "").strip()
    # Validate missing raw category before continuing.
    if not raw_category:
        return None

    new_txn = (preview or {}).get("new_txn") or {}
    old_txn = (preview or {}).get("old_txn") or {}
    txn_type = str((updates or {}).get("type") or new_txn.get("type") or old_txn.get("type") or "").strip().lower()
    if txn_type not in {"expense", "income"}:
        return None

    resolved = resolve_category_name(raw_category, txn_type, allow_create=False)
    status = str(resolved.get("status") or "").strip().lower()
    suggested = str(resolved.get("category_name") or "").strip()
    # Validate missing suggested before continuing.
    if not suggested:
        return None

    # Ask only when the resolver maps the user's text to a different existing category.
    if status in {"alias", "similar", "exact"} and raw_category.strip().lower() != suggested.strip().lower():
        return {
            "raw_category": raw_category,
            "suggested_category": suggested,
            "status": status,
            "transaction_type": txn_type,
        }
    return None


# Helper for build edit category choice text.
def build_edit_category_choice_text(choice: dict) -> str:
    """Build the confirmation text for a matched edit category.

    Args:
        choice: Payload from `get_edit_category_choice_prompt`.

    Returns:
        Markdown text asking the user whether to use the existing category or
        add the typed category as a new one.
    """
    raw_category = str((choice or {}).get("raw_category") or "-").strip()
    suggested = str((choice or {}).get("suggested_category") or "-").strip()
    status = str((choice or {}).get("status") or "similar").strip()
    reason = "cocok dari aliases" if status == "alias" else "mirip dengan kategori existing"
    return (
        f"Input kategori kamu: `{md_code_text(raw_category)}`\n"
        f"Kategori yang sudah ada: *{md_safe(suggested)}* ({md_safe(reason)}).\n\n"
        f"Outputnya udah ada nih *{md_safe(suggested)}*, mau ngikutin atau nambah kategori?"
    )


# Handle the asynchronous maybe prompt edit category choice workflow.
async def maybe_prompt_edit_category_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    updates: dict,
    preview: dict,
    row_index: int | None,
    txn_id: str | None,
    split_raw: str,
    has_split_bill: bool,
) -> bool:
    """Ask the user to confirm a matched category before edit preview.

    Args:
        update: Telegram update used to send the decision prompt.
        context: Telegram context where the pending decision is stored.
        updates: Parsed edit updates. The `category` value is replaced only
            after the user presses a button.
        preview: Successful edit preview used to infer transaction type.
        row_index: Target sheet row index when the transaction was resolved from
            `/last` numbering.
        txn_id: Target transaction ID when row index is not available.
        split_raw: Raw edit args used later for split bill parsing.
        has_split_bill: Whether the same edit command also contains split bill
            syntax and may need a split status decision after category choice.

    Returns:
        True when a category decision prompt was sent and normal edit preview
        should stop for now. False when no prompt is needed.
    """
    choice = get_edit_category_choice_prompt(updates, preview)
    # Validate missing choice before continuing.
    if not choice:
        return False

    context.user_data[EDIT_CATEGORY_CHOICE_KEY] = {
        "row_index": row_index,
        "txn_id": txn_id,
        "updates": dict(updates or {}),
        "split_raw": split_raw,
        "has_split_bill": bool(has_split_bill),
        "raw_category": choice.get("raw_category"),
        "suggested_category": choice.get("suggested_category"),
        "transaction_type": choice.get("transaction_type"),
        "status": choice.get("status"),
    }
    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_edit_category_choice_text(choice),
        parse_mode="Markdown",
        reply_markup=build_edit_category_choice_keyboard(choice.get("suggested_category")),
    )
    return True



# Helper for extract bulk edit txn lines.
def extract_bulk_edit_txn_lines(raw_text: str) -> list[str]:
    """Extract the required part of input for bulk edit txn lines."""
    lines = [str(line or "").strip() for line in str(raw_text or "").splitlines()]
    # Build lines for the response flow.
    lines = [line for line in lines if line]

    edit_lines = [
        line for line in lines
        if re.match(r"^/edit_txn(?:@\w+)?\b", line, flags=re.IGNORECASE)
    ]

    # Handle len(edit lines) >= 2 and len(edit lines) == len(lines).
    if len(edit_lines) >= 2 and len(edit_lines) == len(lines):
        return edit_lines

    return []


# Helper for format bulk edit value.
def _format_bulk_edit_value(value) -> str:
    """Format data into a readable display for bulk edit value."""
    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return format_rupiah(float(value)) if abs(float(value)) >= 1000 else str(int(value))
        return str(value)
    return str(value if value is not None else "-").strip() or "-"


# Helper for build bulk edit preview text.
def build_bulk_edit_preview_text(entries: list[dict]) -> str:
    """Build the data structure or message text for bulk edit preview text."""
    lines = [
        "✏️ *Preview Bulk Edit Transaksi*",
        f"Akan mengedit *{len(entries)} transaksi* dari daftar terakhir.",
        "",
    ]

    balance_touch_count = 0
    # Iterate through each idx, entry.
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

        # Iterate through each field, new value.
        for field, new_value in updates.items():
            old_value = old_txn.get(field, "")
            if field == "amount":
                # Prepare old text from the incoming input.
                old_text = format_rupiah(float(old_value or 0))
                # Prepare new text from the incoming input.
                new_text = format_rupiah(float(new_value or 0))
            # Use the fallback path when no earlier branch matched.
            else:
                # Prepare old text from the incoming input.
                old_text = _format_bulk_edit_value(old_value)
                # Prepare new text from the incoming input.
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
    # Use the fallback path when no earlier branch matched.
    else:
        lines.append("\nℹ️ Bulk edit ini tidak mengubah saldo karena hanya mengubah metadata transaksi.")

    lines.append("\nSimpan semua perubahan ini?")
    return "\n".join(lines)


# Helper for build bulk edit error text.
def build_bulk_edit_error_text(errors: list[str]) -> str:
    """Build the data structure or message text for bulk edit error text."""
    lines = ["❌ *Bulk edit tidak bisa diproses.*", ""]
    lines.append("Perbaiki baris berikut dulu:")
    # Iterate through each err.
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


# Helper for build bulk edit confirm state.
def build_bulk_edit_confirm_state(entries: list[dict]) -> dict:
    """Build the pending confirm payload for bulk edit transactions.

    Args:
        entries: Parsed bulk edit entries. Each item should contain line number,
            ref, target row or transaction ID, and final updates.

    Returns:
        Dict stored in `context.user_data["pending_bulk_edit_txns"]`. Preview
        data is intentionally omitted because confirm only needs stable targets
        and updates.
    """
    return {
        "entries": [
            {
                "line_no": entry.get("line_no"),
                "line": entry.get("line"),
                "ref": entry.get("ref"),
                "row_index": entry.get("row_index"),
                "txn_id": entry.get("txn_id"),
                "updates": entry.get("updates") or {},
            }
            # Iterate through each entry.
            for entry in entries
        ]
    }


# Helper for build bulk edit category decision state.
def build_bulk_edit_category_decision_state(entries: list[dict], decisions: list[dict]) -> dict:
    """Build pending state for the bulk category clarification queue.

    Args:
        entries: All valid bulk edit entries, including rows that still need a
            category decision.
        decisions: Queue items generated from category alias/similarity matches.
            Each decision references `entry_index` in `entries`.

    Returns:
        Dict stored under `BULK_EDIT_CATEGORY_DECISION_KEY`. The state keeps all
        parsed rows in memory, advances one decision at a time, and only creates
        `pending_bulk_edit_txns` after every decision is resolved.
    """
    return {
        "entries": entries,
        "decisions": decisions,
        "current_index": 0,
        "paused_for_category_add": None,
    }


# Helper for get current bulk edit category decision.
def get_current_bulk_edit_category_decision(state: dict) -> tuple[dict | None, int, int]:
    """Return the active bulk category decision and queue counters.

    Args:
        state: Pending queue state from `BULK_EDIT_CATEGORY_DECISION_KEY`.

    Returns:
        Tuple `(decision, current_number, total)`. `decision` is `None` when the
        queue is empty or already complete.
    """
    decisions = (state or {}).get("decisions") or []
    current_index = int((state or {}).get("current_index") or 0)
    total = len(decisions)
    # Handle current index < 0 or current index >= total.
    if current_index < 0 or current_index >= total:
        return None, current_index + 1, total
    return decisions[current_index], current_index + 1, total


# Helper for parse bulk edit txn entries.
def parse_bulk_edit_txn_entries(lines: list[str], context: ContextTypes.DEFAULT_TYPE) -> tuple[list[dict], list[str], list[dict]]:
    """Parse caller input for the parse bulk edit txn entries workflow in the Telegram handler layer.

    Args:
        lines: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        `tuple[list[dict], list[str], list[dict]]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    entries: list[dict] = []
    errors: list[str] = []
    category_decisions: list[dict] = []
    seen_targets: set[str] = set()

    # Iterate through each line no, line.
    for line_no, line in enumerate(lines, 1):
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare parts from the incoming input.
            parts = shlex.split(line)
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            errors.append(f"Baris {line_no}: format kutip tidak valid ({e}).")
            # Skip the rest of this loop iteration after handling this case.
            continue

        if len(parts) < 3:
            errors.append(f"Baris {line_no}: format edit belum lengkap.")
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Prepare args from the incoming input.
        args = parts[1:]
        ref = str(args[0] or "").strip()
        # Extract update args for validation.
        update_args = args[1:]

        if edit_args_contain_split_bill(update_args):
            errors.append(
                f"Baris {line_no}: edit split bill perlu dijalankan satu per satu karena butuh pilihan sudah bayar/belum."
            )
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Run this operation in a guarded block so failures can be handled.
        try:
            debt_payment_conversion = parse_edit_debt_payment_conversion_args(update_args)
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            errors.append(f"Baris {line_no}: {str(e)}")
            # Skip the rest of this loop iteration after handling this case.
            continue

        if debt_payment_conversion:
            errors.append(
                f"Baris {line_no}: konversi bayar_hutang/bayar_piutang perlu dijalankan satu per satu."
            )
            # Skip the rest of this loop iteration after handling this case.
            continue

        resolved = resolve_txn_refs_from_last(context, [ref])
        if resolved.get("invalid_refs") and not resolved.get("row_indices") and not resolved.get("txn_ids"):
            errors.append(f"Baris {line_no}: nomor transaksi `{ref}` tidak ditemukan dari hasil terakhir.")
            # Skip the rest of this loop iteration after handling this case.
            continue

        row_index = resolved["row_indices"][0] if resolved.get("row_indices") else None
        txn_id = resolved["txn_ids"][0] if resolved.get("txn_ids") else None
        target_key = f"row:{row_index}" if row_index else f"id:{txn_id}"

        if target_key in seen_targets:
            errors.append(f"Baris {line_no}: transaksi `{ref}` diedit lebih dari sekali dalam bulk edit ini.")
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Append the current value to seen targets.
        seen_targets.add(target_key)

        # Run this operation in a guarded block so failures can be handled.
        try:
            # Extract updates for validation.
            updates = parse_edit_updates(update_args)
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            errors.append(f"Baris {line_no}: {str(e)}")
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Validate missing updates before continuing.
        if not updates:
            errors.append(f"Baris {line_no}: tidak ada field yang diedit.")
            # Skip the rest of this loop iteration after handling this case.
            continue

        preview = preview_edit_transaction_by_ref(
            # Extract updates for validation.
            updates=updates,
            row_index=row_index,
            txn_id=txn_id,
        )

        if not preview.get("success"):
            errors.append(f"Baris {line_no}: {preview.get('message') or 'Gagal preview edit.'}")
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Extract category choice for validation.
        category_choice = get_edit_category_choice_prompt(updates, preview)
        entry_index = len(entries)
        entries.append({
            "line_no": line_no,
            "line": line,
            "ref": ref,
            "row_index": row_index,
            "txn_id": txn_id,
            "updates": preview.get("updates") or updates,
            "preview": preview,
        })

        if category_choice:
            category_decisions.append({
                "entry_index": entry_index,
                "line_no": line_no,
                "raw_category": category_choice.get("raw_category"),
                "suggested_category": category_choice.get("suggested_category"),
                "transaction_type": category_choice.get("transaction_type"),
                "status": category_choice.get("status"),
            })

    return entries, errors, category_decisions


# Handle the asynchronous bulk edit txn handler workflow.
async def bulk_edit_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, lines: list[str]):
    """Handle the asynchronous bulk edit txn handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.
        lines: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    entries, errors, category_decisions = parse_bulk_edit_txn_entries(lines, context)

    if errors or not entries:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_bulk_edit_error_text(errors or ["Tidak ada baris edit valid."]),
            parse_mode="Markdown",
        )
        return

    if category_decisions:
        # Category decisions are resolved before final preview, preserving preview-before-write.
        state = build_bulk_edit_category_decision_state(entries, category_decisions)
        context.user_data[BULK_EDIT_CATEGORY_DECISION_KEY] = state
        decision, current_number, total = get_current_bulk_edit_category_decision(state)
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_bulk_edit_category_choice_text(decision, current_number, total),
            parse_mode="Markdown",
            reply_markup=build_bulk_edit_category_choice_keyboard(decision.get("suggested_category")),
        )
        return

    context.user_data["pending_bulk_edit_txns"] = build_bulk_edit_confirm_state(entries)

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_bulk_edit_preview_text(entries),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("edit_txns_bulk"),
    )

async def edit_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous edit txn handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Prepare raw text from the incoming input.
    raw_text = update.message.text.strip()

    # Build bulk lines for the response flow.
    bulk_lines = extract_bulk_edit_txn_lines(raw_text)
    if bulk_lines:
        # Await bulk edit txn handler before continuing.
        await bulk_edit_txn_handler(update, context, bulk_lines)
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare parts from the incoming input.
        parts = shlex.split(raw_text)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Send the Telegram response before continuing.
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
        # Send the Telegram response before continuing.
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
    # Extract update args for validation.
    update_args = args[1:]

    resolved = resolve_txn_refs_from_last(context, [ref])

    if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
        # Send the Telegram response before continuing.
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

    # Run this operation in a guarded block so failures can be handled.
    try:
        debt_payment_conversion = parse_edit_debt_payment_conversion_args(update_args)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
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
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Extract updates for validation.
            updates = build_debt_payment_conversion_updates(debt_payment_conversion)
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            await update.message.reply_text(f"❌ {md_safe(str(e))}", parse_mode="Markdown")
            return

        preview = preview_edit_transaction_by_ref(
            # Extract updates for validation.
            updates=updates,
            row_index=row_index,
            txn_id=txn_id,
        )

        if not preview.get("success"):
            # Send the Telegram response before continuing.
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
            # Send the Telegram response before continuing.
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

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_edit_debt_payment_preview_text(preview, debt_payment_conversion, debt_check),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("edit_txn"),
        )
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Extract updates for validation.
        updates = parse_edit_updates(update_args)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000`\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`\n"
            "`/edit_txn 2 account=BRI category=\"Food & Beverage\"`",
            parse_mode="Markdown",
        )
        return

    # Validate missing updates before continuing.
    if not updates:
        # Send the Telegram response before continuing.
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
        # Extract updates for validation.
        updates=updates,
        row_index=row_index,
        txn_id=txn_id,
    )

    if not preview.get("success"):
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"❌ {preview.get('message')}",
            parse_mode="Markdown",
        )
        return

    split_raw = " ".join(update_args)
    has_split_bill = edit_args_contain_split_bill(update_args)
    if await maybe_prompt_edit_category_choice(
        update,
        context,
        # Extract updates for validation.
        updates=updates,
        # Build preview for the response flow.
        preview=preview,
        row_index=row_index,
        txn_id=txn_id,
        # Prepare split raw from the incoming input.
        split_raw=split_raw,
        has_split_bill=has_split_bill,
    ):
        return

    split_parsed = None
    if has_split_bill:
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
            # Send the Telegram response before continuing.
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

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_edit_split_preview_text(preview, split_parsed),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("edit_txn"),
    )


# ── Callback Handler ─────────────────────────────────────────────────────────

