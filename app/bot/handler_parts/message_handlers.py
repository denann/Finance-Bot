"""Natural message handler that routes text and image input into parser, preview, clarification, debt, split bill, pending, or AI flows."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *
# Import app.bot.handler_parts.common_imports so this module can use its helpers.
from app.bot.handler_parts.common_imports import _safe_float_for_display
# Import app.bot.handler_parts.state_utils so this module can use its helpers.
from app.bot.handler_parts.state_utils import BULK_EDIT_CATEGORY_DECISION_KEY, EDIT_CATEGORY_CHOICE_KEY
from app.services.chart_service import write_transaction_timeseries_png

# Import app.bot.handler_parts.networth_assets so this module can use its helpers.
from app.bot.handler_parts.networth_assets import (
    # Include this value in the surrounding collection or call.
    build_asset_confirm_preview,
    # Include this value in the surrounding collection or call.
    build_asset_unit_price_prompt,
    # Include this value in the surrounding collection or call.
    handle_pending_asset_add_flow,
    # Include this value in the surrounding collection or call.
    parse_natural_asset_add,
# Close the structure that was opened above.
)
# Import app.bot.handler_parts.health_recurring_export so this module can use its helpers.
from app.bot.handler_parts.health_recurring_export import handle_pending_recurring_add_flow
# Import app.bot.handler_parts.command_router so this module can use its helpers.
from app.bot.handler_parts.command_router import (
    # Include this value in the surrounding collection or call.
    build_delete_preview_text,
    # Include this value in the surrounding collection or call.
    build_gemini_fallback_text,
    # Include this value in the surrounding collection or call.
    build_gemini_low_confidence_text,
    # Include this value in the surrounding collection or call.
    build_last_transactions_text,
    # Include this value in the surrounding collection or call.
    extract_edit_updates_from_router,
    # Include this value in the surrounding collection or call.
    maybe_text_is_command_typo,
    # Include this value in the surrounding collection or call.
    resolve_txn_refs_from_last,
    # Include this value in the surrounding collection or call.
    router_args_to_last_filter,
# Close the structure that was opened above.
)
# Import app.bot.handler_parts.category_flow so this module can use its helpers.
from app.bot.handler_parts.category_flow import handle_pending_category_flow
# Import app.bot.handler_parts.transaction_flow so this module can use its helpers.
from app.bot.handler_parts.transaction_flow import (
    # Include this value in the surrounding collection or call.
    attach_split_bill_if_any,
    # Include this value in the surrounding collection or call.
    build_debt_account_prompt,
    # Include this value in the surrounding collection or call.
    build_debt_initial_preview,
    # Include this value in the surrounding collection or call.
    build_debt_only_confirm_preview,
    # Include this value in the surrounding collection or call.
    build_mixed_account_prompt,
    # Include this value in the surrounding collection or call.
    build_mixed_detail_preview,
    # Include this value in the surrounding collection or call.
    build_mixed_final_summary,
    # Include this value in the surrounding collection or call.
    build_single_account_prompt,
    # Include this value in the surrounding collection or call.
    build_missing_amount_prompt,
    # Include this value in the surrounding collection or call.
    build_mixed_preview,
    # Include this value in the surrounding collection or call.
    build_parse_clarification_prompt,
    # Include this value in the surrounding collection or call.
    build_preview_with_parse_safety,
    # Include this value in the surrounding collection or call.
    build_pending_expense_confirm_preview,
    # Include this value in the surrounding collection or call.
    build_mixed_split_bill_queue_prompt,
    # Include this value in the surrounding collection or call.
    build_preview,
    # Include this value in the surrounding collection or call.
    build_receipt_account_prompt,
    # Include this value in the surrounding collection or call.
    build_receipt_final_preview,
    # Include this value in the surrounding collection or call.
    build_receipt_partial_mixed_items,
    # Include this value in the surrounding collection or call.
    build_receipt_part_selection_prompt,
    # Include this value in the surrounding collection or call.
    build_receipt_review_text,
    # Include this value in the surrounding collection or call.
    build_receipt_selected_breakdown,
    # Include this value in the surrounding collection or call.
    parse_preview_direct_field_update,
    # Include this value in the surrounding collection or call.
    is_receipt_image_result,
    # Include this value in the surrounding collection or call.
    parse_receipt_divisor,
    # Include this value in the surrounding collection or call.
    parse_receipt_part_selection,
    # Include this value in the surrounding collection or call.
    receipt_extra_charge_net_amount,
    # Include this value in the surrounding collection or call.
    build_split_bill_prompt_from_parsed,
    # Include this value in the surrounding collection or call.
    debt_uses_cashflow,
    # Include this value in the surrounding collection or call.
    enrich_ditalangin_split_bill_if_any,
    # Include this value in the surrounding collection or call.
    edit_or_continue_keyboard,
    # Include this value in the surrounding collection or call.
    preview_action_keyboard,
    # Include this value in the surrounding collection or call.
    preview_action_question,
    # Include this value in the surrounding collection or call.
    single_ready_to_save,
    # Include this value in the surrounding collection or call.
    mixed_ready_to_save,
    # Include this value in the surrounding collection or call.
    debt_ready_to_save,
    # Include this value in the surrounding collection or call.
    handle_pending_missing_amount,
    # Include this value in the surrounding collection or call.
    handle_pending_preview_edit,
    # Include this value in the surrounding collection or call.
    mixed_needs_account,
    # Include this value in the surrounding collection or call.
    mixed_split_bill_keyboard,
    # Include this value in the surrounding collection or call.
    mixed_split_bill_needs_decision,
    # Include this value in the surrounding collection or call.
    needs_account,
    # Include this value in the surrounding collection or call.
    parse_clarification_keyboard,
    # Include this value in the surrounding collection or call.
    parse_income_missing_amount,
    # Include this value in the surrounding collection or call.
    parse_input,
    # Include this value in the surrounding collection or call.
    parse_mixed_item,
    # Include this value in the surrounding collection or call.
    split_bill_keyboard,
    # Include this value in the surrounding collection or call.
    split_bill_needs_decision,
    # Include this value in the surrounding collection or call.
    split_user_inputs,
    # Include this value in the surrounding collection or call.
    build_meal_split_custom_allocation_prompt,
    # Include this value in the surrounding collection or call.
    build_meal_split_status_prompt,
    # Include this value in the surrounding collection or call.
    build_social_spending_guard_prompt,
    # Include this value in the surrounding collection or call.
    detect_social_spending_ambiguity,
    # Include this value in the surrounding collection or call.
    meal_split_status_keyboard,
    # Include this value in the surrounding collection or call.
    parse_meal_split_allocation,
    # Include this value in the surrounding collection or call.
    social_spending_guard_keyboard,
# Close the structure that was opened above.
)
# Import app.bot.handler_parts.command_handlers so this module can use its helpers.
from app.bot.handler_parts.command_handlers import (
    # Include this value in the surrounding collection or call.
    budget_history_handler,
    # Include this value in the surrounding collection or call.
    build_pending_expense_lines,
    # Include this value in the surrounding collection or call.
    format_budget_net_gross,
    # Include this value in the surrounding collection or call.
    bulanan_handler,
    # Include this value in the surrounding collection or call.
    handle_natural_debt_settle,
    # Include this value in the surrounding collection or call.
    handle_natural_finance_question,
    # Include this value in the surrounding collection or call.
    harian_handler,
    # Include this value in the surrounding collection or call.
    help_handler,
    # Include this value in the surrounding collection or call.
    hutang_handler,
    # Include this value in the surrounding collection or call.
    mingguan_handler,
    # Include this value in the surrounding collection or call.
    saldo_handler,
# Close the structure that was opened above.
)
# Import app.nlp.gemini_parser so this module can use its helpers.
from app.nlp.gemini_parser import parse_with_gemini
# Import app.nlp.regex_parser so this module can use its helpers.
from app.nlp.regex_parser import detect_account, extract_debt_account
# Import app.nlp.parse_safety so this module can use its helpers.
from app.nlp.parse_safety import (
    # Include this value in the surrounding collection or call.
    CLARIFICATION,
    # Include this value in the surrounding collection or call.
    GEMINI_DRAFT_PREVIEW,
    # Include this value in the surrounding collection or call.
    WARNING_PREVIEW,
    # Include this value in the surrounding collection or call.
    assess_parse_safety,
# Close the structure that was opened above.
)
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import resolve_category_name

# Handle the asynchronous send parse clarification workflow.
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
    # Close the structure that was opened above.
    }
    context.user_data.pop("pending_parsed", None)
    context.user_data.pop("pending_raw", None)
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt", None)
    context.user_data.pop("pending_debt_batch", None)
    context.user_data.pop("pending_mixed", None)

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_parse_clarification_prompt(raw, assessment),
        parse_mode="Markdown",
        # Prepare reply markup for the next step.
        reply_markup=parse_clarification_keyboard(),
    # Close the structure that was opened above.
    )


# Define try gemini draft for parse safety for callers in this flow.
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
        # Prepare draft assessment for the next step.
        draft_assessment = dict(assessment or {})
        reasons = list(draft_assessment.get("reasons") or [])
        if "Draft transaksi dibuat oleh Gemini dan belum disimpan." not in reasons:
            reasons.append("Draft transaksi dibuat oleh Gemini dan belum disimpan.")
        draft_assessment["reasons"] = reasons
        draft_assessment["recommended_action"] = GEMINI_DRAFT_PREVIEW
        # Return fallback_parsed, draft_assessment, True to the caller.
        return fallback_parsed, draft_assessment, True

    # Prepare gemini parsed for the next step.
    gemini_parsed = parse_with_gemini(raw)
    # Handle the missing or empty gemini_parsed case.
    if not gemini_parsed:
        # Prepare fallback assessment for the next step.
        fallback_assessment = dict(assessment or {})
        reasons = list(fallback_assessment.get("reasons") or [])
        if "Gemini belum berhasil membuat draft, jadi preview memakai hasil parser lokal." not in reasons:
            reasons.append("Gemini belum berhasil membuat draft, jadi preview memakai hasil parser lokal.")
        fallback_assessment["reasons"] = reasons
        fallback_assessment["recommended_action"] = WARNING_PREVIEW
        # Return fallback_parsed, fallback_assessment, False to the caller.
        return fallback_parsed, fallback_assessment, False

    # Run this statement as part of the current workflow.
    attach_split_bill_if_any(gemini_parsed, raw)
    # Prepare draft assessment for the next step.
    draft_assessment = dict(assessment or {})
    reasons = list(draft_assessment.get("reasons") or [])
    if "Draft transaksi dibuat oleh Gemini dan belum disimpan." not in reasons:
        reasons.append("Draft transaksi dibuat oleh Gemini dan belum disimpan.")
    draft_assessment["reasons"] = reasons
    draft_assessment["recommended_action"] = GEMINI_DRAFT_PREVIEW
    # Return gemini_parsed, draft_assessment, True to the caller.
    return gemini_parsed, draft_assessment, True


# Handle the asynchronous debt message handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return True to the caller.
        return True

    # Prepare text for the next step.
    text = update.message.text.strip()
    # Prepare debt parsed for the next step.
    debt_parsed = parse_debt_input(text)

    # Handle the missing or empty debt_parsed case.
    if not debt_parsed:
        # Return False to the caller.
        return False

    # Debt flow section
    # Debt flow section
    # "ditalangin Alpat beli minyak 46k dibagi 4 sama Alpat Opik Sapto"
    # Split bill parsing note: separate the paid transaction from each person share.
    # Implementation section
    debt_parsed = enrich_ditalangin_split_bill_if_any(debt_parsed, text)
    if debt_parsed and not debt_parsed.get("account"):
        # Prepare debt account for the next step.
        debt_account = extract_debt_account(text) or detect_account(text)
        # Handle the case where debt_account.
        if debt_account:
            debt_parsed["account"] = debt_account

    person = debt_parsed.get("person_name")
    intent = debt_parsed.get("intent")

    # Handle the missing or empty person case.
    if not person:
        if intent == "add_payable":
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❓ Siapa yang Anda hutangi?\n"
                "Contoh: `hutang ke Budi 500rb buat makan`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        if intent == "add_receivable":
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❓ Siapa yang meminjam uang ke Anda?\n"
                "Contoh: `Budi minjem 300rb`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        if intent == "add_payment":
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❓ Pembayaran ini terkait siapa?\n"
                "Contoh: `Budi bayar 300rb` atau `bayar hutang Budi 300rb`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

    context.user_data["pending_debt"] = debt_parsed
    context.user_data.pop("pending_parsed", None)
    context.user_data.pop("pending_raw", None)
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt_batch", None)

    intent = debt_parsed.get("intent")
    if debt_uses_cashflow(debt_parsed) and intent != "offset_debt" and not debt_parsed.get("account"):
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_debt_account_prompt(debt_parsed),
            parse_mode="Markdown",
            reply_markup=account_keyboard("debt_acc"),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        f"{build_debt_initial_preview(debt_parsed)}\n\n{preview_action_question(True)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("debt", True),
    # Close the structure that was opened above.
    )

    # Return True to the caller.
    return True

# Handle the asynchronous handle gemini intent workflow.
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
    # Handle the missing or empty should_try_gemini_intent_router(user_text) case.
    if not should_try_gemini_intent_router(user_text):
        # Return False to the caller.
        return False

    # Prepare router result for the next step.
    router_result = route_intent_with_gemini(user_text)

    intent = router_result.get("intent", "unknown")
    confidence = float(router_result.get("confidence", 0) or 0)
    args = router_result.get("args", {}) or {}

    # Handle the case where confidence < GEMINI_INTENT_CONFIDENCE_CLARIFY.
    if confidence < GEMINI_INTENT_CONFIDENCE_CLARIFY:
        # Return False to the caller.
        return False

    # Handle the case where confidence < GEMINI_INTENT_CONFIDENCE_EXECUTE.
    if confidence < GEMINI_INTENT_CONFIDENCE_EXECUTE:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_gemini_low_confidence_text(router_result),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # ── Non-destructive intents ───────────────────────────────────────────────

    if intent == "help":
        # Wait for help_handler before continuing this flow.
        await help_handler(update, context)
        # Return True to the caller.
        return True

    if intent == "saldo":
        # Wait for saldo_handler before continuing this flow.
        await saldo_handler(update, context)
        # Return True to the caller.
        return True

    if intent == "harian":
        # Wait for harian_handler before continuing this flow.
        await harian_handler(update, context)
        # Return True to the caller.
        return True

    if intent == "mingguan":
        # Wait for mingguan_handler before continuing this flow.
        await mingguan_handler(update, context)
        # Return True to the caller.
        return True

    if intent == "bulanan":
        # Wait for bulanan_handler before continuing this flow.
        await bulanan_handler(update, context)
        # Return True to the caller.
        return True

    if intent == "hutang":
        # Wait for hutang_handler before continuing this flow.
        await hutang_handler(update, context)
        # Return True to the caller.
        return True

    if intent == "budget_history":
        # Wait for budget_history_handler before continuing this flow.
        await budget_history_handler(update, context)
        # Return True to the caller.
        return True

    if intent == "last":
        # Run this statement as part of the current workflow.
        limit, period, month, title = router_args_to_last_filter(args)

        # Open a multi-line structure for the values below.
        transactions = get_recent_transactions(
            # Prepare limit for the next step.
            limit=limit,
            # Prepare period for the next step.
            period=period,
            # Prepare month for the next step.
            month=month,
        # Close the structure that was opened above.
        )

        # Handle the missing or empty transactions case.
        if not transactions:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"📭 Tidak ada transaksi untuk filter: *{title}*",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Prepare last map for the next step.
        last_map = {}

        # Process each i, txn in the current collection.
        for i, txn in enumerate(transactions, 1):
            # Open a multi-line structure for the values below.
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            # Close the structure that was opened above.
            }

        context.user_data["last_txn_map"] = last_map

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_last_transactions_text(transactions, title),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    if intent == "cari":
        query = str(args.get("query") or "").strip()

        # Handle the missing or empty query case.
        if not query:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "🔍 Mau cari transaksi apa?\n\n"
                "Contoh:\n"
                "`cari kopi`\n"
                "`/cari kopi`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Prepare results for the next step.
        results = search_transactions(query)

        # Handle the missing or empty results case.
        if not results:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"🔍 Tidak ada transaksi dengan keyword *{md_safe(query)}*.",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        lines = [f"🔍 *Hasil pencarian: \"{md_safe(query)}\"*\n"]

        # Process each t in the current collection.
        for t in results:
            icon = "➕" if t.get("type") == "income" else "➖" if t.get("type") == "expense" else "🔄"
            # Open a multi-line structure for the values below.
            lines.append(
                f"{icon} {md_safe(t.get('date') or '-')} — {md_safe(t.get('description') or '-')}\n"
                f"   *{format_rupiah(float(t.get('amount', 0) or 0))}* | {md_safe(t.get('category') or '-')}"
            # Close the structure that was opened above.
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        # Return True to the caller.
        return True

    if intent == "budget":
        month = args.get("month")

        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare normalized month for the next step.
            normalized_month = normalize_month(month)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Prepare normalized month for the next step.
            normalized_month = normalize_month(None)

        # Prepare summary for the next step.
        summary = get_budget_summary(normalized_month)

        # Handle the missing or empty summary case.
        if not summary:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"📭 Belum ada budget untuk *{format_month_label(normalized_month)}*.\n\n"
                "Set budget dengan cara:\n"
                "`budget makan 1.5 juta`\n"
                "`budget transport 300rb`\n"
                "`budget makan 1.5 juta 2026-07`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        total_budget = sum(float(item.get("budget", 0) or 0) for item in summary)
        total_actual = sum(float(item.get("actual", 0) or 0) for item in summary)
        total_gross_actual = sum(float(item.get("actual_gross", item.get("actual", 0)) or 0) for item in summary)
        # Prepare total remaining for the next step.
        total_remaining = total_budget - total_actual
        # Prepare total pct for the next step.
        total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0

        lines = [f"📊 *Budget {format_month_label(normalized_month)}*\n"]
        lines.append(f"💰 Total Budget : *{format_rupiah(total_budget)}*")
        lines.append(f"💸 Realisasi Bersih (Gross): *{format_budget_net_gross(total_actual, total_gross_actual)}*")
        lines.append(f"📌 Sisa         : *{format_rupiah(total_remaining)}*")
        lines.append(f"📈 Terpakai     : *{total_pct:.1f}%*\n")

        # Process each item in the current collection.
        for item in summary:
            bar = build_progress_bar(item["pct_used"])
            remaining_label = "Sisa" if item["remaining"] >= 0 else "Over"

            # Open a multi-line structure for the values below.
            lines.append(
                f"{item['emoji']} *{item['category']}*\n"
                f"  {bar} {item['pct_used']}%\n"
                f"  Pakai Bersih (Gross): {format_budget_net_gross(item.get('actual', 0), item.get('actual_gross', item.get('actual', 0)))} / {format_rupiah(item['budget'])}\n"
                f"  {remaining_label}: {format_rupiah(abs(item['remaining']))}\n"
            # Close the structure that was opened above.
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        # Return True to the caller.
        return True

    # ── Destructive intents: preview only ─────────────────────────────────────

    if intent == "delete_txn":
        ref = str(args.get("ref") or "").strip()

        # Handle the missing or empty ref case.
        if not ref:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❌ Saya menangkap intent hapus transaksi, tapi nomor/ID transaksinya belum jelas.\n\n"
                "Contoh:\n"
                "`hapus transaksi nomor 2`\n"
                "`/delete_txn 2`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Prepare resolved for the next step.
        resolved = resolve_txn_refs_from_last(context, [ref])

        if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
                "Jalankan dulu:\n"
                "`/last`\n\n"
                "Lalu coba lagi:\n"
                "`hapus transaksi nomor 2`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Open a multi-line structure for the values below.
        preview = preview_delete_transactions_by_refs(
            row_indices=resolved["row_indices"],
            txn_ids=resolved["txn_ids"],
        # Close the structure that was opened above.
        )

        if not preview.get("deletable"):
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                # Include this value in the surrounding collection or call.
                build_delete_preview_text(preview),
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        context.user_data["pending_delete_refs"] = {
            "row_indices": [
                int(txn.get("_row_index"))
                for txn in preview.get("deletable", [])
                if txn.get("_row_index")
            # Close the structure that was opened above.
            ],
            "txn_ids": [],
        # Close the structure that was opened above.
        }

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_delete_preview_text(preview),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("delete_txns"),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    if intent == "edit_txn":
        ref = str(args.get("ref") or "").strip()
        # Prepare updates for the next step.
        updates = extract_edit_updates_from_router(args)

        # Handle the missing or empty ref case.
        if not ref:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❌ Saya menangkap intent edit transaksi, tapi nomor/ID transaksinya belum jelas.\n\n"
                "Contoh:\n"
                "`edit transaksi nomor 2 jadi 15000`\n"
                "`/edit_txn 2 amount=15000`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Handle the missing or empty updates case.
        if not updates:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❌ Saya menangkap intent edit transaksi, tapi field yang diedit belum jelas.\n\n"
                "Contoh:\n"
                "`edit transaksi nomor 2 jadi 15000`\n"
                "`edit transaksi nomor 2 deskripsinya Kopi susu`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Implementation note for this project-specific finance flow.
        # Split bill parsing note: separate the paid transaction from each person share.
        resolved = resolve_txn_refs_from_last(context, [ref])

        if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
                "Jalankan dulu:\n"
                "`/last`\n\n"
                "Lalu coba lagi:\n"
                "`edit transaksi nomor 2 jadi 15000`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        row_index = resolved["row_indices"][0] if resolved["row_indices"] else None
        txn_id = resolved["txn_ids"][0] if resolved["txn_ids"] else None

        # Run this operation in a guarded block so failures can be handled.
        try:
            # Open a multi-line structure for the values below.
            preview = preview_edit_transaction_by_ref(
                # Prepare updates for the next step.
                updates=updates,
                # Prepare row index for the next step.
                row_index=row_index,
                # Prepare txn id for the next step.
                txn_id=txn_id,
            # Close the structure that was opened above.
            )
        # Handle an expected failure from the guarded operation above.
        except NameError:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❌ Gemini sudah menangkap intent edit, tapi fitur `/edit_txn` belum terpasang penuh di kode.\n\n"
                "Pasang Phase `edit_txn` dulu, lalu fitur natural edit bisa aktif.",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        if not preview.get("success"):
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"❌ {preview.get('message')}",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Handle the case where await maybe_prompt_edit_category_choice(.
        if await maybe_prompt_edit_category_choice(
            # Include this value in the surrounding collection or call.
            update,
            # Include this value in the surrounding collection or call.
            context,
            # Prepare updates for the next step.
            updates=updates,
            # Prepare preview for the next step.
            preview=preview,
            # Prepare row index for the next step.
            row_index=row_index,
            # Prepare txn id for the next step.
            txn_id=txn_id,
            split_raw="",
            # Prepare has split bill for the next step.
            has_split_bill=False,
        # Close the structure that was opened above.
        ):
            # Return True to the caller.
            return True

        context.user_data["pending_edit_txn"] = {
            "row_index": row_index,
            "txn_id": txn_id,
            "updates": updates,
        # Close the structure that was opened above.
        }

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_edit_preview_text(preview),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("edit_txn"),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Return False to the caller.
    return False


# Define normalize text command for callers in this flow.
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
    # Return clean to the caller.
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
    # Prepare clean for the next step.
    clean = normalize_text_command(user_text)

    # Handle the missing or empty clean case.
    if not clean:
        # Return False to the caller.
        return False

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    has_amount = bool(
        # Open a multi-line structure for the values below.
        re.search(
            r"\b\d+(?:[.,]\d+)?\s*(rb|ribu|k|jt|juta)?\b",
            # Include this value in the surrounding collection or call.
            clean,
            # Prepare flags for the next step.
            flags=re.IGNORECASE,
        # Close the structure that was opened above.
        )
    # Close the structure that was opened above.
    )

    # Handle the case where has_amount.
    if has_amount:
        # Return False to the caller.
        return False

    # ── Balance flow ─────────────────────────────────────────────────────────────
    saldo_patterns = {
        "cek saldo",
        "lihat saldo",
        "tampilkan saldo",
        "saldo",
    # Close the structure that was opened above.
    }

    # Handle the case where clean in saldo_patterns.
    if clean in saldo_patterns:
        # Wait for saldo_handler before continuing this flow.
        await saldo_handler(update, context)
        # Return True to the caller.
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
    # Close the structure that was opened above.
    }

    # Handle the case where clean in hutang_patterns.
    if clean in hutang_patterns:
        # Wait for hutang_handler before continuing this flow.
        await hutang_handler(update, context)
        # Return True to the caller.
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
    # Close the structure that was opened above.
    }

    # Handle the case where clean in budget_patterns.
    if clean in budget_patterns:
        # Prepare summary for the next step.
        summary = get_budget_summary(normalize_month(None))

        # Handle the missing or empty summary case.
        if not summary:
            # Prepare month for the next step.
            month = normalize_month(None)
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"📭 Belum ada budget untuk *{format_month_label(month)}*.\n\n"
                "Set budget dengan cara:\n"
                "`budget makan 1.5 juta`\n"
                "`budget transport 300rb`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Prepare month for the next step.
        month = normalize_month(None)
        total_budget = sum(float(item.get("budget", 0) or 0) for item in summary)
        total_actual = sum(float(item.get("actual", 0) or 0) for item in summary)
        total_gross_actual = sum(float(item.get("actual_gross", item.get("actual", 0)) or 0) for item in summary)
        # Prepare total remaining for the next step.
        total_remaining = total_budget - total_actual
        # Prepare total pct for the next step.
        total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0

        lines = [f"📊 *Budget {format_month_label(month)}*\n"]
        lines.append(f"💰 Total Budget : *{format_rupiah(total_budget)}*")
        lines.append(f"💸 Realisasi Bersih (Gross): *{format_budget_net_gross(total_actual, total_gross_actual)}*")
        lines.append(f"📌 Sisa         : *{format_rupiah(total_remaining)}*")
        lines.append(f"📈 Terpakai     : *{total_pct:.1f}%*\n")

        # Process each item in the current collection.
        for item in summary:
            bar = build_progress_bar(item["pct_used"])
            remaining_label = "Sisa" if item["remaining"] >= 0 else "Over"

            # Open a multi-line structure for the values below.
            lines.append(
                f"{item['emoji']} *{md_safe(item['category'])}*\n"
                f"  {bar} {item['pct_used']}%\n"
                f"  Pakai Bersih (Gross): {format_budget_net_gross(item.get('actual', 0), item.get('actual_gross', item.get('actual', 0)))} / {format_rupiah(item['budget'])}\n"
                f"  {remaining_label}: {format_rupiah(abs(item['remaining']))}\n"
            # Close the structure that was opened above.
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        # Return True to the caller.
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
    # Close the structure that was opened above.
    }

    # Handle the case where clean in last_patterns.
    if clean in last_patterns:
        # Prepare transactions for the next step.
        transactions = get_recent_transactions(limit=10)

        # Handle the missing or empty transactions case.
        if not transactions:
            await update.message.reply_text("📭 Belum ada transaksi.")
            # Return True to the caller.
            return True

        # Prepare last map for the next step.
        last_map = {}
        # Process each i, txn in the current collection.
        for i, txn in enumerate(transactions, 1):
            # Open a multi-line structure for the values below.
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            # Close the structure that was opened above.
            }

        context.user_data["last_txn_map"] = last_map

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Terakhir"),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Open a multi-line structure for the values below.
    today_patterns = {
        "lihat transaksi hari ini",
        "tampilkan transaksi hari ini",
        "transaksi hari ini",
        "histori hari ini",
        "history hari ini",
    # Close the structure that was opened above.
    }

    # Handle the case where clean in today_patterns.
    if clean in today_patterns:
        transactions = get_recent_transactions(limit=10, period="today")

        # Handle the missing or empty transactions case.
        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi hari ini.")
            # Return True to the caller.
            return True

        # Prepare last map for the next step.
        last_map = {}
        # Process each i, txn in the current collection.
        for i, txn in enumerate(transactions, 1):
            # Open a multi-line structure for the values below.
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            # Close the structure that was opened above.
            }

        context.user_data["last_txn_map"] = last_map

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Hari Ini"),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Open a multi-line structure for the values below.
    week_patterns = {
        "lihat transaksi minggu ini",
        "tampilkan transaksi minggu ini",
        "transaksi minggu ini",
        "histori minggu ini",
        "history minggu ini",
    # Close the structure that was opened above.
    }

    # Handle the case where clean in week_patterns.
    if clean in week_patterns:
        transactions = get_recent_transactions(limit=10, period="week")

        # Handle the missing or empty transactions case.
        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi minggu ini.")
            # Return True to the caller.
            return True

        # Prepare last map for the next step.
        last_map = {}
        # Process each i, txn in the current collection.
        for i, txn in enumerate(transactions, 1):
            # Open a multi-line structure for the values below.
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            # Close the structure that was opened above.
            }

        context.user_data["last_txn_map"] = last_map

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Minggu Ini"),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Open a multi-line structure for the values below.
    month_patterns = {
        "lihat transaksi bulan ini",
        "tampilkan transaksi bulan ini",
        "transaksi bulan ini",
        "histori bulan ini",
        "history bulan ini",
    # Close the structure that was opened above.
    }

    # Handle the case where clean in month_patterns.
    if clean in month_patterns:
        transactions = get_recent_transactions(limit=10, period="month")

        # Handle the missing or empty transactions case.
        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi bulan ini.")
            # Return True to the caller.
            return True

        # Prepare last map for the next step.
        last_map = {}
        # Process each i, txn in the current collection.
        for i, txn in enumerate(transactions, 1):
            # Open a multi-line structure for the values below.
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            # Close the structure that was opened above.
            }

        context.user_data["last_txn_map"] = last_map

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Bulan Ini"),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # ── Transaction search flow ───────────────────────────────────────────────
    # Implementation note for this project-specific finance flow.
    # cari kopi
    # search kopi
    if clean.startswith("cari ") or clean.startswith("search "):
        keyword = clean.split(" ", 1)[1].strip()

        # Handle the missing or empty keyword case.
        if not keyword:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "🔍 Mau cari transaksi apa?\n\n"
                "Contoh:\n"
                "`cari kopi`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Prepare results for the next step.
        results = search_transactions(keyword)

        # Handle the missing or empty results case.
        if not results:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"🔍 Tidak ada transaksi dengan keyword *{md_safe(keyword)}*.",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        lines = [f"🔍 *Hasil pencarian: \"{md_safe(keyword)}\"*\n"]

        # Process each t in the current collection.
        for t in results:
            icon = "➕" if t.get("type") == "income" else "➖" if t.get("type") == "expense" else "🔄"
            # Open a multi-line structure for the values below.
            lines.append(
                f"{icon} {md_safe(t.get('date'))} — {md_safe(t.get('description', '-'))}\n"
                f"   *{format_rupiah(float(t.get('amount', 0) or 0))}* | {md_safe(t.get('category', '-'))}"
            # Close the structure that was opened above.
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        # Return True to the caller.
        return True

    # Return False to the caller.
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

    # Prepare preview for the next step.
    preview = build_mixed_detail_preview(mixed_items, receipt_context)
    # Wait for reply_update_safely before continuing this flow.
    await reply_update_safely(
        # Include this value in the surrounding collection or call.
        update,
        f"{preview}\n\n{preview_action_question(False)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("mixed", False),
    # Close the structure that was opened above.
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
    # Handle the case where divisor_state.
    if divisor_state:
        # Prepare divisor for the next step.
        divisor = parse_receipt_divisor(user_text)
        # Handle the case where divisor <= 0.
        if divisor <= 0:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❌ Jumlah pembaginya belum kebaca. Contoh: `dibagi 5`.",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        receipt = divisor_state.get("receipt") or {}
        selection_result = divisor_state.get("selection_result") or {}
        # Run this statement as part of the current workflow.
        mixed_items, receipt_context = build_receipt_partial_mixed_items(receipt, selection_result, divisor)
        # Wait for _continue_receipt_batch_after_selection before continuing this flow.
        await _continue_receipt_batch_after_selection(update, context, mixed_items, receipt_context)
        # Return True to the caller.
        return True

    selection_state = context.user_data.get("pending_receipt_part_selection")
    # Handle the missing or empty selection_state case.
    if not selection_state:
        # Return False to the caller.
        return False

    receipt = selection_state.get("receipt") or {}
    items = selection_state.get("items") or []
    # Prepare selection result for the next step.
    selection_result = parse_receipt_part_selection(user_text, items)

    if not selection_result.get("success"):
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ {selection_result.get('message')}\n\n{build_receipt_part_selection_prompt(receipt, items)}",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Handle the case where receipt_extra_charge_net_amount(receipt) > 0.
    if receipt_extra_charge_net_amount(receipt) > 0:
        context.user_data["pending_receipt_extra_divisor"] = {
            "receipt": receipt,
            "selection_result": selection_result,
        # Close the structure that was opened above.
        }
        context.user_data.pop("pending_receipt_part_selection", None)
        # Wait for reply_update_safely before continuing this flow.
        await reply_update_safely(
            # Include this value in the surrounding collection or call.
            update,
            # Include this value in the surrounding collection or call.
            build_receipt_selected_breakdown(receipt, selection_result),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Run this statement as part of the current workflow.
    mixed_items, receipt_context = build_receipt_partial_mixed_items(receipt, selection_result, divisor=1)
    # Wait for _continue_receipt_batch_after_selection before continuing this flow.
    await _continue_receipt_batch_after_selection(update, context, mixed_items, receipt_context)
    # Return True to the caller.
    return True


# ── Image / Receipt Handler ──────────────────────────────────────────────────

# Handle the asynchronous image handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare message for the next step.
    message = update.message
    # Handle the missing or empty message case.
    if not message:
        # Return control to the caller.
        return

    # Prepare photo for the next step.
    photo = message.photo[-1] if message.photo else None
    # Prepare document for the next step.
    document = message.document if message.document else None

    # Prepare file id for the next step.
    file_id = None
    mime_type = "image/jpeg"
    # Prepare file size for the next step.
    file_size = 0

    # Handle the case where photo.
    if photo:
        # Prepare file id for the next step.
        file_id = photo.file_id
        # Prepare file size for the next step.
        file_size = int(photo.file_size or 0)
        mime_type = "image/jpeg"
    elif document and str(document.mime_type or "").startswith("image/"):
        # Prepare file id for the next step.
        file_id = document.file_id
        # Prepare file size for the next step.
        file_size = int(document.file_size or 0)
        mime_type = document.mime_type or "image/jpeg"
    # Handle the fallback path after earlier conditions are skipped.
    else:
        await message.reply_text("❌ File yang dikirim belum terbaca sebagai gambar.")
        # Return control to the caller.
        return

    # Image parsing note: receipt output still goes through preview before saving.
    if file_size and file_size > 10 * 1024 * 1024:
        # Wait for message.reply_text before continuing this flow.
        await message.reply_text(
            "❌ Gambar terlalu besar. Kirim gambar di bawah 10 MB."
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Open a multi-line structure for the values below.
    status_msg = await message.reply_text(
        "🖼️ Membaca gambar dengan Gemini...\n"
        "Pastikan gambar tidak berisi data sensitif seperti nomor rekening lengkap, password, atau OTP."
    # Close the structure that was opened above.
    )

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare tg file for the next step.
        tg_file = await context.bot.get_file(file_id)
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare image bytes for the next step.
            image_bytes = await tg_file.download_as_bytearray()
        # Handle an expected failure from the guarded operation above.
        except AttributeError:
            # Prepare buffer for the next step.
            buffer = io.BytesIO()
            # Wait for tg_file.download_to_memory before continuing this flow.
            await tg_file.download_to_memory(buffer)
            # Prepare image bytes for the next step.
            image_bytes = buffer.getvalue()
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        await status_msg.edit_text(f"❌ Gagal download gambar dari Telegram: {str(e)}")
        # Return control to the caller.
        return

    caption = message.caption or ""
    # Open a multi-line structure for the values below.
    result = parse_transactions_from_image(
        # Include this value in the surrounding collection or call.
        bytes(image_bytes),
        # Prepare mime type for the next step.
        mime_type=mime_type,
        # Prepare caption for the next step.
        caption=caption,
    # Close the structure that was opened above.
    )

    if not result.get("success"):
        # Wait for status_msg.edit_text before continuing this flow.
        await status_msg.edit_text(
            "🤔 Gambar belum bisa saya ubah jadi transaksi.\n\n"
            f"Detail: {result.get('message') or '-'}\n\n"
            "Coba kirim foto yang lebih jelas, atau tambahkan caption seperti:\n"
            "`beli makan dari struk ini`\n"
            "`ini pemasukan`\n"
            "`pakai BSI`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    items = result.get("items", []) or []
    receipt = result.get("receipt") or {}

    # Handle the case where is_receipt_image_result(result, items).
    if is_receipt_image_result(result, items):
        context.user_data["pending_receipt"] = {
            "receipt": receipt,
            "items": items,
            "caption": caption or "[gambar]",
        # Close the structure that was opened above.
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

        # Wait for edit_message_safely before continuing this flow.
        await edit_message_safely(
            # Include this value in the surrounding collection or call.
            status_msg,
            # Include this value in the surrounding collection or call.
            build_receipt_review_text(receipt, items),
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=receipt_ownership_keyboard(),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Image parsing note: non-itemized images still use the regular single/mixed preview flow.
    if len(items) == 1:
        # Prepare parsed for the next step.
        parsed = items[0]
        attach_split_bill_if_any(parsed, caption or "")
        context.user_data["pending_parsed"] = parsed
        context.user_data["pending_raw"] = caption or "[gambar]"
        context.user_data.pop("pending_batch", None)
        context.user_data.pop("pending_debt", None)
        context.user_data.pop("pending_debt_batch", None)
        context.user_data.pop("pending_mixed", None)

        # Handle the case where split_bill_needs_decision(parsed).
        if split_bill_needs_decision(parsed):
            # Wait for status_msg.edit_text before continuing this flow.
            await status_msg.edit_text(
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
            # Wait for status_msg.edit_text before continuing this flow.
            await status_msg.edit_text(
                # Include this value in the surrounding collection or call.
                build_single_account_prompt(parsed),
                parse_mode="Markdown",
                reply_markup=account_keyboard("acc"),
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        # Prepare preview for the next step.
        preview = build_preview(parsed)
        # Wait for status_msg.edit_text before continuing this flow.
        await status_msg.edit_text(
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("single", True),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Image parsing note: receipt output still goes through preview before saving.
    mixed_items = []
    # Process each idx, parsed in the current collection.
    for idx, parsed in enumerate(items, 1):
        raw_item = f"gambar item {idx}"
        # Run this statement as part of the current workflow.
        attach_split_bill_if_any(parsed, caption or raw_item)
        # Open a multi-line structure for the values below.
        mixed_items.append({
            "kind": "transaction",
            "parsed": parsed,
            "raw": raw_item,
        # Close the structure that was opened above.
        })

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
        # Wait for edit_message_safely before continuing this flow.
        await edit_message_safely(
            # Include this value in the surrounding collection or call.
            status_msg,
            # Include this value in the surrounding collection or call.
            build_mixed_split_bill_queue_prompt(mixed_items),
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=mixed_split_bill_keyboard(mixed_items),
        # Close the structure that was opened above.
        )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Wait for edit_message_safely before continuing this flow.
        await edit_message_safely(
            # Include this value in the surrounding collection or call.
            status_msg,
            f"{preview}\n\n{preview_action_question(False)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", False),
        # Close the structure that was opened above.
        )

# Message handling section

# Implementation section
# Debt flow section

# Handle the asynchronous message handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare user text for the next step.
    user_text = update.message.text.strip()

    if user_text.startswith("/"):
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "⚠️ Input ini terlihat seperti command, jadi tidak saya parse sebagai transaksi.\n\n"
            "Cek command dengan `/help`, atau tulis transaksi tanpa awalan `/`." ,
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare receipt selection handled for the next step.
    receipt_selection_handled = await handle_pending_receipt_selection(update, context, user_text)
    # Handle the case where receipt_selection_handled.
    if receipt_selection_handled:
        # Return control to the caller.
        return

    # Prepare missing amount handled for the next step.
    missing_amount_handled = await handle_pending_missing_amount(update, context, user_text)
    # Handle the case where missing_amount_handled.
    if missing_amount_handled:
        # Return control to the caller.
        return

    meal_split_state = context.user_data.get("pending_meal_split") or {}
    if meal_split_state.get("stage") == "custom_allocation":
        # Open a multi-line structure for the values below.
        shares = parse_meal_split_allocation(
            # Include this value in the surrounding collection or call.
            user_text,
            float(meal_split_state.get("amount") or 0),
            meal_split_state.get("people") or [],
        # Close the structure that was opened above.
        )
        # Handle the missing or empty shares case.
        if not shares:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❌ Pembagian belum kebaca. Tulis dalam format seperti `saya 30k, Budi 50k` atau `saya 100%, Budi 100%`.",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        meal_split_state["shares"] = shares
        meal_split_state["allocation_mode"] = "custom"
        meal_split_state["stage"] = "status"
        context.user_data["pending_meal_split"] = meal_split_state
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_meal_split_status_prompt(meal_split_state),
            parse_mode="Markdown",
            reply_markup=meal_split_status_keyboard(meal_split_state.get("payer") or "self"),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare preview edit handled for the next step.
    preview_edit_handled = await handle_pending_preview_edit(update, context, user_text)
    # Handle the case where preview_edit_handled.
    if preview_edit_handled:
        # Return control to the caller.
        return

    # Category wizard consumes text replies before they can be parsed as transactions.
    category_flow_handled = await handle_pending_category_flow(update, context, user_text)
    # Handle the case where category_flow_handled.
    if category_flow_handled:
        # Return control to the caller.
        return

    # Prepare recurring add flow handled for the next step.
    recurring_add_flow_handled = await handle_pending_recurring_add_flow(update, context, user_text)
    # Handle the case where recurring_add_flow_handled.
    if recurring_add_flow_handled:
        # Return control to the caller.
        return

    # Prepare asset add flow handled for the next step.
    asset_add_flow_handled = await handle_pending_asset_add_flow(update, context, user_text)
    # Handle the case where asset_add_flow_handled.
    if asset_add_flow_handled:
        # Return control to the caller.
        return

    # Pending expense section
    pending_asset = context.user_data.get("pending_asset_price")
    # Handle the case where pending_asset.
    if pending_asset:
        # Prepare unit price for the next step.
        unit_price = parse_human_amount(user_text)

        # Handle the case where unit_price <= 0.
        if unit_price <= 0:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❌ Harga satuan belum valid.\n\n"
                "Balas dengan angka, contoh: `2410000`, `2.41 juta`, atau `8000000`.",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        pending_asset["price_per_unit"] = unit_price
        pending_asset["needs_unit_price"] = False

        quantity = float(pending_asset.get("quantity", 0) or 0)
        pending_asset["amount"] = quantity * unit_price

        context.user_data["pending_asset_confirm"] = pending_asset
        context.user_data.pop("pending_asset_price", None)

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"{build_asset_confirm_preview(pending_asset)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("asset", True),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Asset flow section
    natural_asset = parse_natural_asset_add(user_text)
    # Handle the case where natural_asset.
    if natural_asset:
        if natural_asset.get("needs_unit_price"):
            context.user_data["pending_asset_price"] = natural_asset
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                # Include this value in the surrounding collection or call.
                build_asset_unit_price_prompt(natural_asset),
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        context.user_data["pending_asset_confirm"] = natural_asset
        context.user_data.pop("pending_asset_price", None)
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"{build_asset_confirm_preview(natural_asset)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("asset", True),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare social guard for the next step.
    social_guard = detect_social_spending_ambiguity(user_text)
    # Handle the case where social_guard.
    if social_guard:
        context.user_data["pending_social_spending_guard"] = social_guard
        context.user_data.pop("pending_parsed", None)
        context.user_data.pop("pending_debt", None)
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_social_spending_guard_prompt(user_text, social_guard),
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=social_spending_guard_keyboard(),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
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
        # Include this value in the surrounding collection or call.
        update,
        # Include this value in the surrounding collection or call.
        context,
        # Include this value in the surrounding collection or call.
        user_text,
    # Close the structure that was opened above.
    )

    # Handle the case where local_natural_handled.
    if local_natural_handled:
        # Return control to the caller.
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
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare item for the next step.
            item = build_pending_expense_from_text(user_text)
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"❌ Gagal membaca pending expense: {md_safe(str(e))}\n\n"
                "Contoh:\n"
                "`nanti perlu bayar wisuda 750k`\n"
                "`nanti perlu service motor 300k tgl 30`\n"
                "`perlu 750k buat bayar wisuda`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        context.user_data["pending_expense_confirm"] = item
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"{build_pending_expense_confirm_preview(item, include_question=False)}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("pending_expense", True),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Debt flow section
    # Debt flow section
    # Implementation section
    selected_debt_settle_handled = await handle_natural_debt_settle(update, context, user_text)
    # Handle the case where selected_debt_settle_handled.
    if selected_debt_settle_handled:
        # Return control to the caller.
        return

    # Phase 2: explicit debt/split/talangin intent must win before parse safety.
    early_debt_parsed = parse_debt_input(user_text)
    # Handle the case where early_debt_parsed.
    if early_debt_parsed:
        # Prepare debt handled for the next step.
        debt_handled = await debt_message_handler(update, context)
        # Handle the case where debt_handled.
        if debt_handled:
            # Return control to the caller.
            return

    # Implementation section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    finance_question_handled = await handle_natural_finance_question(
        # Include this value in the surrounding collection or call.
        update,
        # Include this value in the surrounding collection or call.
        context,
        # Include this value in the surrounding collection or call.
        user_text,
    # Close the structure that was opened above.
    )

    # Handle the case where finance_question_handled.
    if finance_question_handled:
        # Return control to the caller.
        return

    # Implementation section
    # Example cleanup: remove the person prefix so the description stays focused on the expense item.
    pre_parse_assessment = assess_parse_safety(user_text, {})
    if pre_parse_assessment.get("recommended_action") == CLARIFICATION:
        # Wait for send_parse_clarification before continuing this flow.
        await send_parse_clarification(update, context, user_text, {}, pre_parse_assessment)
        # Return control to the caller.
        return

    has_explicit_separator = bool(re.search(r"[\n\r;,]", user_text))
    # Prepare input lines for the next step.
    input_lines = split_user_inputs(user_text)
    # Prepare is multi input for the next step.
    is_multi_input = has_explicit_separator or len(input_lines) > 1

    # Debt flow section
    if not is_multi_input:
        # Prepare full debt parsed for the next step.
        full_debt_parsed = parse_debt_input(user_text)
        # Handle the case where full_debt_parsed.
        if full_debt_parsed:
            # Prepare debt handled for the next step.
            debt_handled = await debt_message_handler(update, context)
            # Handle the case where debt_handled.
            if debt_handled:
                # Return control to the caller.
                return

    # Input multi / campuran
    if len(input_lines) > 1:
        # Prepare mixed items for the next step.
        mixed_items = []
        # Prepare failed lines for the next step.
        failed_lines = []
        # Prepare missing amount indices for the next step.
        missing_amount_indices = []

        # Process each line in the current collection.
        for line in input_lines:
            # Prepare item for the next step.
            item = parse_mixed_item(line)

            if item["kind"] == "failed":
                # Update failed lines with the current value.
                failed_lines.append(line)
                # Skip the rest of this loop iteration after handling this case.
                continue

            if item["kind"] == "missing_amount":
                # Update missing amount indices with the current value.
                missing_amount_indices.append(len(mixed_items))

            # Update mixed items with the current value.
            mixed_items.append(item)

        # Handle the case where failed_lines.
        if failed_lines:
            lines = ["🤔 Ada input yang belum bisa saya pahami:\n"]

            # Process each i, line in the current collection.
            for i, line in enumerate(failed_lines, 1):
                lines.append(f"{i}. `{line}`")

            # Open a multi-line structure for the values below.
            lines.append(
                "\nCoba format seperti:\n"
                "`beli kopi 25rb`\n"
                "`Budi minjem 300k`\n"
                "`minjem Joko 100k`\n"
                "`beli kopi 10k minjem Joko 10k`"
            # Close the structure that was opened above.
            )

            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
            # Return control to the caller.
            return

        # Handle the case where mixed_items.
        if mixed_items:
            # Handle the case where missing_amount_indices.
            if missing_amount_indices:
                context.user_data["pending_missing_amount"] = {
                    "scope": "mixed",
                    "mixed_items": mixed_items,
                    "missing_indices": missing_amount_indices,
                    "current": 0,
                # Close the structure that was opened above.
                }
                # Prepare first idx for the next step.
                first_idx = missing_amount_indices[0]
                # Prepare first item for the next step.
                first_item = mixed_items[first_idx]
                # Wait for update.message.reply_text before continuing this flow.
                await update.message.reply_text(
                    # Open a multi-line structure for the values below.
                    build_missing_amount_prompt(
                        first_item.get("raw", ""),
                        first_item.get("parsed", {}),
                        # Include this value in the surrounding collection or call.
                        1,
                        # Include this value in the surrounding collection or call.
                        len(missing_amount_indices),
                    # Close the structure that was opened above.
                    ),
                    parse_mode="Markdown",
                # Close the structure that was opened above.
                )
                # Return control to the caller.
                return

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
                # Wait for update.message.reply_text before continuing this flow.
                await update.message.reply_text(
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

            # Return control to the caller.
            return

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Debt flow section
    missing_amount_income = parse_income_missing_amount(user_text)
    # Handle the case where missing_amount_income.
    if missing_amount_income:
        context.user_data["pending_missing_amount"] = {
            "scope": "single",
            "item": {
                "kind": "missing_amount",
                "parsed": missing_amount_income,
                "raw": user_text,
            # Close the structure that was opened above.
            },
        # Close the structure that was opened above.
        }
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_missing_amount_prompt(user_text, missing_amount_income),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
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
            # Include this value in the surrounding collection or call.
            update,
            # Include this value in the surrounding collection or call.
            context,
            # Include this value in the surrounding collection or call.
            user_text,
        # Close the structure that was opened above.
        )

        # Handle the case where local_natural_handled.
        if local_natural_handled:
            # Return control to the caller.
            return

        # Debt flow section
        # Implementation section
        # Implementation note for this project-specific finance flow.
        # Implementation note for this project-specific finance flow.
        gemini_handled = await handle_gemini_intent(update, context, user_text)

        # Handle the case where gemini_handled.
        if gemini_handled:
            # Return control to the caller.
            return

        # Layer 5: local typo resolver pendek.
        # Implementation note for this project-specific finance flow.
        # - minguan
        # - mingguannn
        # - detele
        # - bugete
        command_typo_feedback = maybe_text_is_command_typo(user_text)

        # Handle the case where command_typo_feedback.
        if command_typo_feedback:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                # Include this value in the surrounding collection or call.
                command_typo_feedback,
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_gemini_fallback_text(),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Run this statement as part of the current workflow.
    attach_split_bill_if_any(parsed, user_text)

    # Prepare safety assessment for the next step.
    safety_assessment = assess_parse_safety(user_text, parsed)
    safety_action = safety_assessment.get("recommended_action")

    # Handle the case where safety_action == CLARIFICATION.
    if safety_action == CLARIFICATION:
        # Wait for send_parse_clarification before continuing this flow.
        await send_parse_clarification(update, context, user_text, parsed, safety_assessment)
        # Return control to the caller.
        return

    preview_mode = "normal"
    # Handle the case where safety_action == GEMINI_DRAFT_PREVIEW.
    if safety_action == GEMINI_DRAFT_PREVIEW:
        # Run this statement as part of the current workflow.
        parsed, safety_assessment, gemini_used = try_gemini_draft_for_parse_safety(user_text, parsed, safety_assessment)
        preview_mode = "gemini" if gemini_used else "warning"
    # Handle the alternate case where safety_action == WARNING_PREVIEW.
    elif safety_action == WARNING_PREVIEW:
        preview_mode = "warning"

    context.user_data["pending_parsed"] = parsed
    context.user_data["pending_raw"] = user_text
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt", None)
    context.user_data.pop("pending_debt_batch", None)
    context.user_data.pop("pending_mixed", None)
    context.user_data.pop("pending_parse_clarification", None)

    # Open a multi-line structure for the values below.
    preview = (
        # Run this statement as part of the current workflow.
        build_preview_with_parse_safety(parsed, safety_assessment, preview_mode)
        if preview_mode in {"warning", "gemini"}
        # Run this statement as part of the current workflow.
        else build_preview(parsed)
    # Close the structure that was opened above.
    )

    # Handle the case where split_bill_needs_decision(parsed).
    if split_bill_needs_decision(parsed):
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_split_bill_prompt_from_parsed(parsed),
            parse_mode="Markdown",
            reply_markup=split_bill_keyboard("single"),
        # Close the structure that was opened above.
        )
    # Handle the alternate case where needs_account(parsed).
    elif needs_account(parsed):
        # Wait for reply_update_safely before continuing this flow.
        await reply_update_safely(
            # Include this value in the surrounding collection or call.
            update,
            # Open a multi-line structure for the values below.
            build_single_account_prompt(
                # Include this value in the surrounding collection or call.
                parsed,
                preview_text=preview if preview_mode in {"warning", "gemini"} else None,
            # Close the structure that was opened above.
            ),
            parse_mode="Markdown",
            reply_markup=account_keyboard("acc"),
        # Close the structure that was opened above.
        )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Wait for reply_update_safely before continuing this flow.
        await reply_update_safely(
            # Include this value in the surrounding collection or call.
            update,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("single", True),
        # Close the structure that was opened above.
        )


# Define build transactions full text for callers in this flow.
def build_transactions_full_text(transactions: list[dict], title: str, account_filter: str | None = None) -> str:
    """Build the data structure or message text for transactions full text."""
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
        txn_type = str(txn.get("type", "")).strip().lower()
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
        lines.append(
            "\n*Ringkasan Rekening:*\n"
            f"✅ Income          : *{format_rupiah(total_income)}*\n"
            f"❌ Expense         : *{expense_text}*\n"
            f"🔁 Transfer Masuk  : *{format_rupiah(total_transfer_in)}*\n"
            f"🔁 Transfer Keluar : *{format_rupiah(total_transfer_out)}*\n"
            f"📊 Net Rekening    : *{net_text}*\n"
            f"📝 Total           : *{len(transactions)} transaksi*"
        # Close the structure that was opened above.
        )
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

# Define build transaction filter title for callers in this flow.
def build_transaction_filter_title(base_title: str, category_filter: str | None = None, account_filter: str | None = None) -> str:
    """Build the data structure or message text for transaction filter title."""
    # Prepare suffix for the next step.
    suffix = []
    # Handle the case where category_filter.
    if category_filter:
        suffix.append(f"Kategori {category_filter}")
    # Handle the case where account_filter.
    if account_filter:
        suffix.append(f"Rekening {account_filter}")
    # Handle the case where suffix.
    if suffix:
        return f"{base_title} — {' | '.join(suffix)}"
    # Return base_title to the caller.
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


# Define build transaksi prefixed period arg for callers in this flow.
def _build_transaksi_prefixed_period_arg(first: str, rest: str, mode: str) -> str | None:
    """Build the data structure or message text for transaksi prefixed period arg."""
    rest = str(rest or "").strip()
    # Handle the missing or empty rest case.
    if not rest:
        # Return None to the caller.
        return None

    # Prepare first rest for the next step.
    first_rest = rest.split()[0].strip().lower()

    if mode == "month" and first_rest in {"ini", "lalu", "depan"}:
        return f"{first} {rest}"

    if mode == "date" and first_rest in {"ini", "lalu", "depan"}:
        return f"{first} {rest}"

    # Return rest to the caller.
    return rest


# Define parse transaksi period for callers in this flow.
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
    # Prepare low for the next step.
    low = raw.lower()

    # Handle the missing or empty raw case.
    if not raw:
        # Run this statement as part of the current workflow.
        year, month_num = parse_report_month_arg(None)
        # Prepare report for the next step.
        report = get_monthly_report(year, month_num)
        return f"Transaksi Bulan {report.get('month', '-')}", report.get("transactions", []), "month", None

    # Prepare first for the next step.
    first = low.split()[0]
    rest = " ".join(raw.split()[1:]).strip()

    if first in ["rekening", "akun", "account", "rek"]:
        # Run this statement as part of the current workflow.
        account_arg, period_arg = split_account_period_arg(rest)
        # Handle the missing or empty account_arg case.
        if not account_arg:
            raise ValueError("Nama rekening belum diisi. Contoh: /transaksi rekening Cash")

        # Prepare report for the next step.
        report = get_account_report(account_arg, period_arg)
        account_filter = report.get("account_filter") or account_arg
        period_label = report.get("period_label") or report.get("month") or "-"
        # Return ( to the caller.
        return (
            f"Transaksi Rekening {account_filter} — {period_label}",
            report.get("transactions", []),
            "account",
            # Include this value in the surrounding collection or call.
            account_filter,
        # Close the structure that was opened above.
        )

    if first in ["hari", "harian", "tanggal", "tgl", "tg", "day", "daily"]:
        period_source = _build_transaksi_prefixed_period_arg(first, rest, "date")
        date_arg, category_arg, account_arg = split_report_filter_args(period_source, "date")
        # Prepare report for the next step.
        report = get_daily_report(date_arg, category_arg, account_arg)
        # Open a multi-line structure for the values below.
        title = build_transaction_filter_title(
            f"Transaksi Tanggal {report.get('date', '-')}",
            report.get("category_filter"),
            report.get("account_filter"),
        # Close the structure that was opened above.
        )
        return title, report.get("transactions", []), "day", report.get("account_filter")

    if first in ["minggu", "mingguan", "week", "weekly"]:
        period_source = _build_transaksi_prefixed_period_arg(first, rest, "date")
        date_arg, category_arg, account_arg = split_report_filter_args(period_source, "date")
        # Prepare report for the next step.
        report = get_weekly_report(date_arg, category_arg, account_arg)
        # Open a multi-line structure for the values below.
        title = build_transaction_filter_title(
            f"Transaksi Minggu {report.get('date_from', '-')} s/d {report.get('date_to', '-')}",
            report.get("category_filter"),
            report.get("account_filter"),
        # Close the structure that was opened above.
        )
        return title, report.get("transactions", []), "week", report.get("account_filter")

    if first in ["bulan", "bulanan", "month", "monthly"]:
        period_source = _build_transaksi_prefixed_period_arg(first, rest, "month")
        month_arg, category_arg, account_arg = split_report_filter_args(period_source, "month")
        # Run this statement as part of the current workflow.
        year, month_num = parse_report_month_arg(month_arg)
        # Prepare report for the next step.
        report = get_monthly_report(year, month_num, category_arg, account_arg)
        # Open a multi-line structure for the values below.
        title = build_transaction_filter_title(
            f"Transaksi Bulan {report.get('month', '-')}",
            report.get("category_filter"),
            report.get("account_filter"),
        # Close the structure that was opened above.
        )
        return title, report.get("transactions", []), "month", report.get("account_filter")

    if re.fullmatch(r"20\d{2}[-/]\d{1,2}[-/]\d{1,2}", low) or re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]20\d{2}", low):
        # Prepare report for the next step.
        report = get_daily_report(raw)
        return f"Transaksi Tanggal {report.get('date', '-')}", report.get("transactions", []), "day", None

    if re.fullmatch(r"20\d{2}[-/]\d{1,2}", low):
        # Run this statement as part of the current workflow.
        year, month_num = parse_report_month_arg(raw)
        # Prepare report for the next step.
        report = get_monthly_report(year, month_num)
        return f"Transaksi Bulan {report.get('month', '-')}", report.get("transactions", []), "month", None

    if re.fullmatch(r"\d{1,2}", low):
        # Prepare report for the next step.
        report = get_daily_report(raw)
        return f"Transaksi Tanggal {report.get('date', '-')}", report.get("transactions", []), "day", None

    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    # /transaction kemarin
    # /transaction minggu lalu
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    try:
        # Prepare date arg for the next step.
        date_arg = parse_report_date_arg(raw)
        # Prepare report for the next step.
        report = get_daily_report(date_arg)
        return f"Transaksi Tanggal {report.get('date', '-')}", report.get("transactions", []), "day", None
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass

    # Run this operation in a guarded block so failures can be handled.
    try:
        month_arg, category_arg, account_arg = split_report_filter_args(raw, "month")
        # Handle the case where month_arg or category_arg or account_arg.
        if month_arg or category_arg or account_arg:
            # Run this statement as part of the current workflow.
            year, month_num = parse_report_month_arg(month_arg)
            # Prepare report for the next step.
            report = get_monthly_report(year, month_num, category_arg, account_arg)
            # Open a multi-line structure for the values below.
            title = build_transaction_filter_title(
                f"Transaksi Bulan {report.get('month', '-')}",
                report.get("category_filter"),
                report.get("account_filter"),
            # Close the structure that was opened above.
            )
            return title, report.get("transactions", []), "month", report.get("account_filter")
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass

    # Raise a clear error so the caller can stop this invalid flow.
    raise ValueError(
        "Format /transaksi tidak dikenali. Contoh: /transaksi 2026-06, /transaksi bulan lalu, /transaksi Food & Beverage 2026-06, /transaksi rekening Cash bulan lalu."
    # Close the structure that was opened above.
    )


# Handle the asynchronous transaksi handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Run this statement as part of the current workflow.
        title, transactions, _period_type, account_filter = parse_transaksi_period(context.args)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Wait for update.message.reply_text before continuing this flow.
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
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Open a multi-line structure for the values below.
    transactions = sorted(
        # Include this value in the surrounding collection or call.
        transactions,
        key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)),
        # Prepare reverse for the next step.
        reverse=True,
    # Close the structure that was opened above.
    )

    # Handle the missing or empty transactions case.
    if not transactions:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"📭 Tidak ada transaksi untuk filter: *{md_safe(title)}*",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare last map for the next step.
    last_map = {}
    # Process each i, txn in the current collection.
    for i, txn in enumerate(transactions, 1):
        if txn.get("_row_index"):
            # Open a multi-line structure for the values below.
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            # Close the structure that was opened above.
            }

    context.user_data["last_txn_map"] = last_map
    # Wait for reply_long_markdown before continuing this flow.
    await reply_long_markdown(update, build_transactions_full_text(transactions, title, account_filter))
    # Send the matching read-only time-series chart after the transaction list.
    await send_transaction_timeseries_chart(update, transactions, title)


# Handle the asynchronous last handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare args for the next step.
    args = context.args

    # Prepare limit for the next step.
    limit = 10
    # Prepare period for the next step.
    period = None
    # Prepare month for the next step.
    month = None
    title = "Transaksi Terakhir"

    # Handle the case where args.
    if args:
        # Prepare arg1 for the next step.
        arg1 = args[0].strip().lower()

        # Handle the case where arg1.isdigit().
        if arg1.isdigit():
            # Prepare limit for the next step.
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

        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Wait for update.message.reply_text before continuing this flow.
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
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

    # Open a multi-line structure for the values below.
    transactions = get_recent_transactions(
        # Prepare limit for the next step.
        limit=limit,
        # Prepare period for the next step.
        period=period,
        # Prepare month for the next step.
        month=month,
    # Close the structure that was opened above.
    )

    # Handle the missing or empty transactions case.
    if not transactions:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"📭 Tidak ada transaksi untuk filter: *{title}*",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare last map for the next step.
    last_map = {}

    # Process each i, txn in the current collection.
    for i, txn in enumerate(transactions, 1):
        # Open a multi-line structure for the values below.
        last_map[str(i)] = {
            "id": str(txn.get("id", "")),
            "row_index": int(txn.get("_row_index")),
        # Close the structure that was opened above.
        }

    context.user_data["last_txn_map"] = last_map

    # Wait for reply_long_markdown before continuing this flow.
    await reply_long_markdown(update, build_last_transactions_text(transactions, title))
    # Send the matching read-only time-series chart after the transaction list.
    await send_transaction_timeseries_chart(update, transactions, title)


# Handle the asynchronous delete txn handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare refs for the next step.
    refs = context.args

    # Handle the missing or empty refs case.
    if not refs:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Masukkan nomor transaksi dari `/last` atau transaction ID.\n\n"
            "Contoh:\n"
            "`/last today`\n"
            "`/delete_txn 1`\n"
            "`/delete_txn 1 3 5`\n"
            "`/delete_txn txn_20260609_231132_123456_abcd1234`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare resolved for the next step.
    resolved = resolve_txn_refs_from_last(context, refs)

    invalid_refs = resolved.get("invalid_refs", [])

    if invalid_refs and not resolved["row_indices"] and not resolved["txn_ids"]:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
            "Jalankan dulu:\n"
            "`/last`\n\n"
            "Lalu hapus dengan:\n"
            "`/delete_txn 1`\n"
            "`/delete_txn 1 3 5`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Open a multi-line structure for the values below.
    preview = preview_delete_transactions_by_refs(
        row_indices=resolved["row_indices"],
        txn_ids=resolved["txn_ids"],
    # Close the structure that was opened above.
    )

    # Handle the case where invalid_refs.
    if invalid_refs:
        preview["missing_rows"] = preview.get("missing_rows", []) + invalid_refs

    if not preview.get("deletable"):
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_delete_preview_text(preview),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    context.user_data["pending_delete_refs"] = {
        "row_indices": [
            int(txn.get("_row_index"))
            for txn in preview.get("deletable", [])
            if txn.get("_row_index")
        # Close the structure that was opened above.
        ],
        "txn_ids": [],
    # Close the structure that was opened above.
    }

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_delete_preview_text(preview),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("delete_txns"),
    # Close the structure that was opened above.
    )

# Define parse edit updates for callers in this flow.
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
    # Handle the missing or empty args case.
    if not args:
        # Return {} to the caller.
        return {}

    # Handle the case where len(args) == 1.
    if len(args) == 1:
        # Prepare first for the next step.
        first = args[0].strip()
        if re.fullmatch(r"\d+(?:[.,]\d+)?(?:\s*(?:rb|ribu|k|jt|juta|m))?", first, flags=re.IGNORECASE):
            return {"amount": first.replace(",", ".")}

    split_words = {"dibagi", "bagi", "patungan", "split", "share"}
    # Prepare updates for the next step.
    updates = {}
    # Prepare i for the next step.
    i = 0

    # Repeat this block while i < len(args).
    while i < len(args):
        arg = str(args[i] or "").strip()
        # Prepare low for the next step.
        low = arg.lower()

        # Handle the missing or empty arg case.
        if not arg:
            # Run this statement as part of the current workflow.
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Split bill parsing note: separate the paid transaction from each person share.
        if low in split_words or low.replace("-", "") in {"dibagi"}:
            # Leave the loop after the target condition has been reached.
            break

        # Mendukung: amount = 500k
        if i + 2 < len(args) and args[i + 1] == "=":
            # Prepare key for the next step.
            key = arg
            # Prepare value for the next step.
            value = str(args[i + 2]).strip()
            # Run this statement as part of the current workflow.
            updates[key] = value
            # Run this statement as part of the current workflow.
            i += 3
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Supports both `amount=500k` and `amount= 500k`.
        if "=" in arg:
            key, value = arg.split("=", 1)
            # Prepare key for the next step.
            key = key.strip()
            # Prepare value for the next step.
            value = value.strip()
            if value == "" and i + 1 < len(args):
                # Prepare value for the next step.
                value = str(args[i + 1]).strip()
                # Run this statement as part of the current workflow.
                i += 2
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Run this statement as part of the current workflow.
                i += 1

            if not key or value == "":
                raise ValueError(f"Argumen `{arg}` tidak valid. Gunakan format key=value.")
            # Run this statement as part of the current workflow.
            updates[key] = value
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Implementation note for this project-specific finance flow.
        if not updates and re.fullmatch(r"\d+(?:[.,]\d+)?(?:\s*(?:rb|ribu|k|jt|juta|m))?", arg, flags=re.IGNORECASE):
            updates["amount"] = arg
            # Run this statement as part of the current workflow.
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Raise a clear error so the caller can stop this invalid flow.
        raise ValueError(
            f"Argumen `{arg}` tidak valid. Gunakan format key=value."
        # Close the structure that was opened above.
        )

    # Return updates to the caller.
    return updates


# Define edit args contain split bill for callers in this flow.
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


# Define normalize edit arg token for callers in this flow.
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


# Define parse edit debt payment conversion args for callers in this flow.
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
    # Handle the missing or empty args case.
    if not args:
        # Return None to the caller.
        return None

    raw_tokens = [str(x or "").strip() for x in args if str(x or "").strip()]
    # Handle the missing or empty raw_tokens case.
    if not raw_tokens:
        # Return None to the caller.
        return None

    target_type = ""
    explicit_person = ""
    # Run this statement as part of the current workflow.
    field_tokens: list[str] = []
    # Run this statement as part of the current workflow.
    person_tokens: list[str] = []
    # Prepare consume person for the next step.
    consume_person = False
    # Prepare found marker for the next step.
    found_marker = False

    # Prepare i for the next step.
    i = 0
    # Repeat this block while i < len(raw_tokens).
    while i < len(raw_tokens):
        # Prepare token for the next step.
        token = raw_tokens[i]
        # Prepare low for the next step.
        low = _normalize_edit_arg_token(token)

        # Explicit fields khusus conversion.
        if "=" in token:
            key, value = token.split("=", 1)
            key_low = key.strip().lower().replace("_", "-")
            # Prepare value clean for the next step.
            value_clean = value.strip()

            if key_low in {"debt", "debt-type", "tipe-hutang", "tipehutang", "hutang-type", "jenis-debt"}:
                # Prepare found marker for the next step.
                found_marker = True
                # Prepare value low for the next step.
                value_low = value_clean.lower()
                if value_low in {"payable", "utang", "hutang", "bayar-utang", "bayar-hutang"}:
                    target_type = "payable"
                elif value_low in {"receivable", "piutang", "bayar-piutang"}:
                    target_type = "receivable"
                # Handle the fallback path after earlier conditions are skipped.
                else:
                    raise ValueError("Nilai debt harus payable/utang/hutang atau receivable/piutang.")
                # Run this statement as part of the current workflow.
                i += 1
                # Skip the rest of this loop iteration after handling this case.
                continue

            if key_low in {"person", "orang", "nama", "ke", "dari", "sama"}:
                # Prepare explicit person for the next step.
                explicit_person = value_clean
                # Run this statement as part of the current workflow.
                i += 1
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Update field tokens with the current value.
            field_tokens.append(token)
            # Run this statement as part of the current workflow.
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Debt flow section
        compact = low.replace("-", "")
        if compact in {"bayarhutang", "bayarutang", "pembayaranhutang", "pembayaranutang", "hutang", "utang"}:
            target_type = "payable"
            # Prepare found marker for the next step.
            found_marker = True
            # Prepare consume person for the next step.
            consume_person = True
            # Run this statement as part of the current workflow.
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        if compact in {"bayarpiutang", "pembayaranpiutang", "piutang"}:
            target_type = "receivable"
            # Prepare found marker for the next step.
            found_marker = True
            # Prepare consume person for the next step.
            consume_person = True
            # Run this statement as part of the current workflow.
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Debt flow section
        next_low = _normalize_edit_arg_token(raw_tokens[i + 1]) if i + 1 < len(raw_tokens) else ""
        next_compact = next_low.replace("-", "")
        if compact in {"bayar", "pembayaran", "payment", "jadi", "menjadi", "ubah", "konversi", "convert"} and next_compact in {"hutang", "utang", "piutang"}:
            target_type = "receivable" if next_compact == "piutang" else "payable"
            # Prepare found marker for the next step.
            found_marker = True
            # Prepare consume person for the next step.
            consume_person = True
            # Run this statement as part of the current workflow.
            i += 2
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Split bill parsing note: separate the paid transaction from each person share.
        if consume_person and compact in {"ke", "dari", "sama", "dengan", "untuk", "sebagai"}:
            # Run this statement as part of the current workflow.
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Split bill parsing note: separate the paid transaction from each person share.
        if consume_person:
            # Update person tokens with the current value.
            person_tokens.append(token)
            # Run this statement as part of the current workflow.
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Update field tokens with the current value.
        field_tokens.append(token)
        # Run this statement as part of the current workflow.
        i += 1

    # Handle the missing or empty found_marker case.
    if not found_marker:
        # Return None to the caller.
        return None

    person = explicit_person or " ".join(person_tokens).strip()
    person = re.sub(r"\s+", " ", person).strip()
    person = re.sub(r"^(ke|dari|sama|dengan|untuk)\s+", "", person, flags=re.IGNORECASE).strip()

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    person = re.sub(r"\s+\w+\s*=.*$", "", person).strip()

    # Handle the missing or empty target_type case.
    if not target_type:
        raise ValueError("Tipe pembayaran debt belum jelas. Gunakan bayar_hutang atau bayar_piutang.")
    # Handle the missing or empty person case.
    if not person:
        raise ValueError("Nama orang belum jelas. Contoh: /edit_txn 2 bayar_hutang Sapto")

    # Prepare extra updates for the next step.
    extra_updates = parse_edit_updates(field_tokens) if field_tokens else {}

    # Return { to the caller.
    return {
        "target_type": target_type,
        "person_name": person.title(),
        "extra_updates": extra_updates,
    # Close the structure that was opened above.
    }


# Define build debt payment conversion updates for callers in this flow.
def build_debt_payment_conversion_updates(conversion: dict, old_txn: dict | None = None) -> dict:
    """Build the data structure or message text for debt payment conversion updates."""
    target_type = str(conversion.get("target_type") or "").strip().lower()
    person = str(conversion.get("person_name") or "").strip().title()
    updates = dict(conversion.get("extra_updates") or {})

    if target_type == "payable":
        # Open a multi-line structure for the values below.
        updates.update({
            "type": "expense",
            "category": "Bayar Utang",
            "subject": person,
            "description": f"Bayar utang ke {person}",
            "catatan": f"Dikonversi dari transaksi biasa menjadi pembayaran utang ke {person}",
        # Close the structure that was opened above.
        })
    elif target_type == "receivable":
        # Open a multi-line structure for the values below.
        updates.update({
            "type": "income",
            "category": "Pembayaran Piutang",
            "subject": person,
            "description": f"Pembayaran piutang dari {person}",
            "catatan": f"Dikonversi dari transaksi biasa menjadi pembayaran piutang dari {person}",
        # Close the structure that was opened above.
        })
    # Handle the fallback path after earlier conditions are skipped.
    else:
        raise ValueError("Tipe pembayaran debt tidak valid.")

    # Return updates to the caller.
    return updates


# Define validate edit debt payment conversion for callers in this flow.
def validate_edit_debt_payment_conversion(conversion: dict, amount: float) -> dict:
    """Validate data before it is used by edit debt payment conversion."""
    person = str(conversion.get("person_name") or "").strip().title()
    target_type = str(conversion.get("target_type") or "").strip().lower()
    label = "utang" if target_type == "payable" else "piutang"

    # Prepare debts for the next step.
    debts = get_debt_by_person(person)
    # Open a multi-line structure for the values below.
    target_debts = [
        # Run this statement as part of the current workflow.
        d for d in debts
        if str(d.get("type", "")).strip() == target_type
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
    # Close the structure that was opened above.
    ]
    total_remaining = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in target_debts)

    # Handle the missing or empty target_debts or total_remaining <= 0 case.
    if not target_debts or total_remaining <= 0:
        # Return { to the caller.
        return {
            "success": False,
            "message": f"Tidak ada {label} aktif dengan {person}.",
            "total_remaining": 0,
            "overpayment": 0,
        # Close the structure that was opened above.
        }

    # Prepare outcome for the next step.
    outcome = estimate_payment_outcome(person, amount, target_type)
    # Return { to the caller.
    return {
        "success": True,
        "message": "ok",
        "total_remaining": total_remaining,
        "opposite_remaining": outcome.get("opposite_remaining_before", 0),
        "net_payment_capacity": outcome.get("net_payment_capacity", total_remaining),
        "overpayment": outcome.get("overpayment", 0),
        "target_count": len(target_debts),
        "label": label,
    # Close the structure that was opened above.
    }


# Define build edit debt payment preview text for callers in this flow.
def build_edit_debt_payment_preview_text(preview: dict, conversion: dict, debt_check: dict) -> str:
    """Build the data structure or message text for edit debt payment preview text."""
    # Prepare text for the next step.
    text = build_edit_preview_text(preview)
    person = str(conversion.get("person_name") or "-").strip()
    target_type = str(conversion.get("target_type") or "").strip().lower()
    label = "utang" if target_type == "payable" else "piutang"
    amount = float((preview.get("new_txn") or {}).get("amount", 0) or 0)

    # Open a multi-line structure for the values below.
    text += (
        f"\n\n💸 *Konversi Debt:* transaksi ini akan dijadikan pembayaran {label}."
        f"\n👤 Orang: *{md_safe(person)}*"
        f"\n💰 Pembayaran: *{format_rupiah(amount)}*"
        f"\n📌 Sisa {label} aktif saat ini: *{format_rupiah(debt_check.get('total_remaining', 0))}*"
        f"\n📌 Sisa arah lawan saat ini: *{format_rupiah(debt_check.get('opposite_remaining', 0))}*"
        f"\n📊 Saldo net yang perlu dibayar: *{format_rupiah(debt_check.get('net_payment_capacity', debt_check.get('total_remaining', 0)))}*"
    # Close the structure that was opened above.
    )

    if float(debt_check.get("overpayment", 0) or 0) > 0:
        text += f"\n⚠️ Nominal melebihi saldo net debt: {format_rupiah(debt_check.get('overpayment', 0))}. Kelebihannya perlu diperlakukan sebagai bonus/lunas atau hutang lawan arah."

    # Return text to the caller.
    return text


# Define build edit split preview text for callers in this flow.
def build_edit_split_preview_text(preview: dict, split_parsed: dict | None = None) -> str:
    """Build the data structure or message text for edit split preview text."""
    # Prepare text for the next step.
    text = build_edit_preview_text(preview)
    split_bill = (split_parsed or {}).get("split_bill") or {}
    status = split_bill.get("status")
    # Handle the case where split_bill.
    if split_bill:
        total_receivable = float(split_bill.get("total_receivable", 0) or 0)
        if status == "unpaid":
            # Open a multi-line structure for the values below.
            text += (
                "\n\n🤝 *Split bill:* belum dibayar, jadi piutang baru akan dibuat "
                f"sebesar *{format_rupiah(total_receivable)}*."
            # Close the structure that was opened above.
            )
        elif status == "paid":
            text += "\n\n🤝 *Split bill:* sudah dibayar, transaksi disimpan sebesar bagian bersih kamu."
    # Return text to the caller.
    return text


# Define build edit preview text for callers in this flow.
def build_edit_preview_text(preview: dict) -> str:
    """Build the data structure or message text for edit preview text."""
    old_txn = preview.get("old_txn", {})
    new_txn = preview.get("new_txn", {})
    updates = preview.get("updates", {})
    net_deltas = preview.get("net_deltas", {})

    lines = ["✏️ *Preview Edit Transaksi*\n"]

    lines.append("*Sebelum:*")
    # Open a multi-line structure for the values below.
    lines.append(
        f"• {old_txn.get('date')} — *{old_txn.get('description') or '-'}*\n"
        f"  {format_rupiah(float(old_txn.get('amount', 0) or 0))} | "
        f"{old_txn.get('category') or '-'} | {old_txn.get('account') or '-'}"
    # Close the structure that was opened above.
    )

    lines.append("\n*Sesudah:*")
    # Open a multi-line structure for the values below.
    lines.append(
        f"• {new_txn.get('date')} — *{new_txn.get('description') or '-'}*\n"
        f"  {format_rupiah(float(new_txn.get('amount', 0) or 0))} | "
        f"{new_txn.get('category') or '-'} | {new_txn.get('account') or '-'}"
    # Close the structure that was opened above.
    )

    # Handle the case where updates.
    if updates:
        lines.append("\n*Field yang diubah:*")
        # Process each field, value in the current collection.
        for field, value in updates.items():
            lines.append(f"• {field}: `{value}`")

    # Handle the case where net_deltas.
    if net_deltas:
        lines.append("\n*Efek ke saldo:*")
        # Process each account, delta in the current collection.
        for account, delta in net_deltas.items():
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {account}: {sign}{format_rupiah(abs(delta))}")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.append("\n*Efek ke saldo:*")
        lines.append("• Tidak ada perubahan saldo")

    lines.append("\nSimpan perubahan ini?")

    return "\n".join(lines)


# Define build edit category choice keyboard for callers in this flow.
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
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Ikuti {label}", callback_data="edit_category_choice:use")],
        [InlineKeyboardButton("➕ Tambah kategori baru", callback_data="edit_category_choice:create")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:edit_txn")],
    # Close the structure that was opened above.
    ])


# Define build bulk edit category choice keyboard for callers in this flow.
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
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Ikuti {label}", callback_data="bulk_edit_category_choice:use")],
        [InlineKeyboardButton("➕ Tambah kategori baru", callback_data="bulk_edit_category_choice:create")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:bulk_edit_category")],
    # Close the structure that was opened above.
    ])


# Define build bulk edit category choice text for callers in this flow.
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
    # Return ( to the caller.
    return (
        f"Baris {line_no}: input kategori `{md_code_text(raw_category)}` cocok ke "
        f"`{md_code_text(suggested)}`. Mau ikuti kategori existing atau tambah kategori baru?\n\n"
        f"Decision {current_number}/{total}"
    # Close the structure that was opened above.
    )


# Define get edit category choice prompt for callers in this flow.
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
        # Return None to the caller.
        return None

    raw_category = str((updates or {}).get("category") or "").strip()
    # Handle the missing or empty raw_category case.
    if not raw_category:
        # Return None to the caller.
        return None

    new_txn = (preview or {}).get("new_txn") or {}
    old_txn = (preview or {}).get("old_txn") or {}
    txn_type = str((updates or {}).get("type") or new_txn.get("type") or old_txn.get("type") or "").strip().lower()
    if txn_type not in {"expense", "income"}:
        # Return None to the caller.
        return None

    # Prepare resolved for the next step.
    resolved = resolve_category_name(raw_category, txn_type, allow_create=False)
    status = str(resolved.get("status") or "").strip().lower()
    suggested = str(resolved.get("category_name") or "").strip()
    # Handle the missing or empty suggested case.
    if not suggested:
        # Return None to the caller.
        return None

    # Ask only when the resolver maps the user's text to a different existing category.
    if status in {"alias", "similar", "exact"} and raw_category.strip().lower() != suggested.strip().lower():
        # Return { to the caller.
        return {
            "raw_category": raw_category,
            "suggested_category": suggested,
            "status": status,
            "transaction_type": txn_type,
        # Close the structure that was opened above.
        }
    # Return None to the caller.
    return None


# Define build edit category choice text for callers in this flow.
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
    # Return ( to the caller.
    return (
        f"Input kategori kamu: `{md_code_text(raw_category)}`\n"
        f"Kategori yang sudah ada: *{md_safe(suggested)}* ({md_safe(reason)}).\n\n"
        f"Outputnya udah ada nih *{md_safe(suggested)}*, mau ngikutin atau nambah kategori?"
    # Close the structure that was opened above.
    )


# Handle the asynchronous maybe prompt edit category choice workflow.
async def maybe_prompt_edit_category_choice(
    # Include this value in the surrounding collection or call.
    update: Update,
    # Include this value in the surrounding collection or call.
    context: ContextTypes.DEFAULT_TYPE,
    # Include this value in the surrounding collection or call.
    *,
    # Include this value in the surrounding collection or call.
    updates: dict,
    # Include this value in the surrounding collection or call.
    preview: dict,
    # Include this value in the surrounding collection or call.
    row_index: int | None,
    # Include this value in the surrounding collection or call.
    txn_id: str | None,
    # Include this value in the surrounding collection or call.
    split_raw: str,
    # Include this value in the surrounding collection or call.
    has_split_bill: bool,
# Close the structure that was opened above.
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
    # Prepare choice for the next step.
    choice = get_edit_category_choice_prompt(updates, preview)
    # Handle the missing or empty choice case.
    if not choice:
        # Return False to the caller.
        return False

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    }
    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_edit_category_choice_text(choice),
        parse_mode="Markdown",
        reply_markup=build_edit_category_choice_keyboard(choice.get("suggested_category")),
    # Close the structure that was opened above.
    )
    # Return True to the caller.
    return True



# Define extract bulk edit txn lines for callers in this flow.
def extract_bulk_edit_txn_lines(raw_text: str) -> list[str]:
    """Extract the required part of input for bulk edit txn lines."""
    lines = [str(line or "").strip() for line in str(raw_text or "").splitlines()]
    # Prepare lines for the next step.
    lines = [line for line in lines if line]

    # Open a multi-line structure for the values below.
    edit_lines = [
        # Run this statement as part of the current workflow.
        line for line in lines
        if re.match(r"^/edit_txn(?:@\w+)?\b", line, flags=re.IGNORECASE)
    # Close the structure that was opened above.
    ]

    # Handle the case where len(edit_lines) >= 2 and len(edit_lines) == len(lines).
    if len(edit_lines) >= 2 and len(edit_lines) == len(lines):
        # Return edit_lines to the caller.
        return edit_lines

    # Return [] to the caller.
    return []


# Define format bulk edit value for callers in this flow.
def _format_bulk_edit_value(value) -> str:
    """Format data into a readable display for bulk edit value."""
    # Handle the case where isinstance(value, (int, float)).
    if isinstance(value, (int, float)):
        # Handle the case where float(value).is_integer().
        if float(value).is_integer():
            # Return format_rupiah(float(value)) if abs(float(value)) >= 1000 else... to the caller.
            return format_rupiah(float(value)) if abs(float(value)) >= 1000 else str(int(value))
        # Return str(value) to the caller.
        return str(value)
    return str(value if value is not None else "-").strip() or "-"


# Define build bulk edit preview text for callers in this flow.
def build_bulk_edit_preview_text(entries: list[dict]) -> str:
    """Build the data structure or message text for bulk edit preview text."""
    # Open a multi-line structure for the values below.
    lines = [
        "✏️ *Preview Bulk Edit Transaksi*",
        f"Akan mengedit *{len(entries)} transaksi* dari daftar terakhir.",
        "",
    # Close the structure that was opened above.
    ]

    # Prepare balance touch count for the next step.
    balance_touch_count = 0
    # Process each idx, entry in the current collection.
    for idx, entry in enumerate(entries, 1):
        preview = entry.get("preview") or {}
        old_txn = preview.get("old_txn") or {}
        new_txn = preview.get("new_txn") or {}
        updates = preview.get("updates") or {}
        net_deltas = preview.get("net_deltas") or {}
        # Handle the case where net_deltas.
        if net_deltas:
            # Run this statement as part of the current workflow.
            balance_touch_count += 1

        ref = str(entry.get("ref") or idx).strip()
        desc_before = str(old_txn.get("description") or old_txn.get("subject") or "-").strip()
        desc_after = str(new_txn.get("description") or new_txn.get("subject") or "-").strip()
        lines.append(f"{idx}. Ref `{md_code_text(ref)}` — *{md_safe(desc_before)}*")

        # Process each field, new_value in the current collection.
        for field, new_value in updates.items():
            old_value = old_txn.get(field, "")
            if field == "amount":
                # Prepare old text for the next step.
                old_text = format_rupiah(float(old_value or 0))
                # Prepare new text for the next step.
                new_text = format_rupiah(float(new_value or 0))
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Prepare old text for the next step.
                old_text = _format_bulk_edit_value(old_value)
                # Prepare new text for the next step.
                new_text = _format_bulk_edit_value(new_value)

            # Open a multi-line structure for the values below.
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
            # Close the structure that was opened above.
            }.get(str(field), str(field))

            lines.append(f"   • {label}: {md_safe(old_text)} → *{md_safe(new_text)}*")

        if desc_before != desc_after and "description" not in updates:
            lines.append(f"   • Desc hasil: {md_safe(desc_before)} → *{md_safe(desc_after)}*")

    # Handle the case where balance_touch_count.
    if balance_touch_count:
        # Open a multi-line structure for the values below.
        lines.append(
            f"\n⚠️ Ada *{balance_touch_count} edit* yang bisa mengubah saldo karena menyentuh nominal/rekening/type."
        # Close the structure that was opened above.
        )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.append("\nℹ️ Bulk edit ini tidak mengubah saldo karena hanya mengubah metadata transaksi.")

    lines.append("\nSimpan semua perubahan ini?")
    return "\n".join(lines)


# Define build bulk edit error text for callers in this flow.
def build_bulk_edit_error_text(errors: list[str]) -> str:
    """Build the data structure or message text for bulk edit error text."""
    lines = ["❌ *Bulk edit tidak bisa diproses.*", ""]
    lines.append("Perbaiki baris berikut dulu:")
    # Process each err in the current collection.
    for err in errors[:15]:
        lines.append(f"• {md_safe(err)}")
    # Handle the case where len(errors) > 15.
    if len(errors) > 15:
        lines.append(f"• ...dan {len(errors) - 15} error lain")
    # Open a multi-line structure for the values below.
    lines.append(
        "\nFormat contoh:\n"
        "`/edit_txn 1 category=\"Food & Beverage\"`\n"
        "`/edit_txn 2 category=\"Bills & Utilities\" desc=\"Wifi\"`"
    # Close the structure that was opened above.
    )
    return "\n".join(lines)


# Define build bulk edit confirm state for callers in this flow.
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
    # Return { to the caller.
    return {
        "entries": [
            # Open a multi-line structure for the values below.
            {
                "line_no": entry.get("line_no"),
                "line": entry.get("line"),
                "ref": entry.get("ref"),
                "row_index": entry.get("row_index"),
                "txn_id": entry.get("txn_id"),
                "updates": entry.get("updates") or {},
            # Close the structure that was opened above.
            }
            # Process each entry in the current collection.
            for entry in entries
        # Close the structure that was opened above.
        ]
    # Close the structure that was opened above.
    }


# Define build bulk edit category decision state for callers in this flow.
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
    # Return { to the caller.
    return {
        "entries": entries,
        "decisions": decisions,
        "current_index": 0,
        "paused_for_category_add": None,
    # Close the structure that was opened above.
    }


# Define get current bulk edit category decision for callers in this flow.
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
    # Prepare total for the next step.
    total = len(decisions)
    # Handle the case where current_index < 0 or current_index >= total.
    if current_index < 0 or current_index >= total:
        # Return None, current_index + 1, total to the caller.
        return None, current_index + 1, total
    # Return decisions[current_index], current_index + 1, total to the caller.
    return decisions[current_index], current_index + 1, total


# Define parse bulk edit txn entries for callers in this flow.
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
    # Run this statement as part of the current workflow.
    entries: list[dict] = []
    # Run this statement as part of the current workflow.
    errors: list[str] = []
    # Run this statement as part of the current workflow.
    category_decisions: list[dict] = []
    # Run this statement as part of the current workflow.
    seen_targets: set[str] = set()

    # Process each line_no, line in the current collection.
    for line_no, line in enumerate(lines, 1):
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare parts for the next step.
            parts = shlex.split(line)
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            errors.append(f"Baris {line_no}: format kutip tidak valid ({e}).")
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Handle the case where len(parts) < 3.
        if len(parts) < 3:
            errors.append(f"Baris {line_no}: format edit belum lengkap.")
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Prepare args for the next step.
        args = parts[1:]
        ref = str(args[0] or "").strip()
        # Prepare update args for the next step.
        update_args = args[1:]

        # Handle the case where edit_args_contain_split_bill(update_args).
        if edit_args_contain_split_bill(update_args):
            # Open a multi-line structure for the values below.
            errors.append(
                f"Baris {line_no}: edit split bill perlu dijalankan satu per satu karena butuh pilihan sudah bayar/belum."
            # Close the structure that was opened above.
            )
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare debt payment conversion for the next step.
            debt_payment_conversion = parse_edit_debt_payment_conversion_args(update_args)
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            errors.append(f"Baris {line_no}: {str(e)}")
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Handle the case where debt_payment_conversion.
        if debt_payment_conversion:
            # Open a multi-line structure for the values below.
            errors.append(
                f"Baris {line_no}: konversi bayar_hutang/bayar_piutang perlu dijalankan satu per satu."
            # Close the structure that was opened above.
            )
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Prepare resolved for the next step.
        resolved = resolve_txn_refs_from_last(context, [ref])
        if resolved.get("invalid_refs") and not resolved.get("row_indices") and not resolved.get("txn_ids"):
            errors.append(f"Baris {line_no}: nomor transaksi `{ref}` tidak ditemukan dari hasil terakhir.")
            # Skip the rest of this loop iteration after handling this case.
            continue

        row_index = resolved["row_indices"][0] if resolved.get("row_indices") else None
        txn_id = resolved["txn_ids"][0] if resolved.get("txn_ids") else None
        target_key = f"row:{row_index}" if row_index else f"id:{txn_id}"

        # Handle the case where target_key in seen_targets.
        if target_key in seen_targets:
            errors.append(f"Baris {line_no}: transaksi `{ref}` diedit lebih dari sekali dalam bulk edit ini.")
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Update seen targets with the current value.
        seen_targets.add(target_key)

        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare updates for the next step.
            updates = parse_edit_updates(update_args)
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            errors.append(f"Baris {line_no}: {str(e)}")
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Handle the missing or empty updates case.
        if not updates:
            errors.append(f"Baris {line_no}: tidak ada field yang diedit.")
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Open a multi-line structure for the values below.
        preview = preview_edit_transaction_by_ref(
            # Prepare updates for the next step.
            updates=updates,
            # Prepare row index for the next step.
            row_index=row_index,
            # Prepare txn id for the next step.
            txn_id=txn_id,
        # Close the structure that was opened above.
        )

        if not preview.get("success"):
            errors.append(f"Baris {line_no}: {preview.get('message') or 'Gagal preview edit.'}")
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Prepare category choice for the next step.
        category_choice = get_edit_category_choice_prompt(updates, preview)
        # Prepare entry index for the next step.
        entry_index = len(entries)
        # Open a multi-line structure for the values below.
        entries.append({
            "line_no": line_no,
            "line": line,
            "ref": ref,
            "row_index": row_index,
            "txn_id": txn_id,
            "updates": preview.get("updates") or updates,
            "preview": preview,
        # Close the structure that was opened above.
        })

        # Handle the case where category_choice.
        if category_choice:
            # Open a multi-line structure for the values below.
            category_decisions.append({
                "entry_index": entry_index,
                "line_no": line_no,
                "raw_category": category_choice.get("raw_category"),
                "suggested_category": category_choice.get("suggested_category"),
                "transaction_type": category_choice.get("transaction_type"),
                "status": category_choice.get("status"),
            # Close the structure that was opened above.
            })

    # Return entries, errors, category_decisions to the caller.
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
    # Run this statement as part of the current workflow.
    entries, errors, category_decisions = parse_bulk_edit_txn_entries(lines, context)

    # Handle the case where errors or not entries.
    if errors or not entries:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            build_bulk_edit_error_text(errors or ["Tidak ada baris edit valid."]),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Handle the case where category_decisions.
    if category_decisions:
        # Category decisions are resolved before final preview, preserving preview-before-write.
        state = build_bulk_edit_category_decision_state(entries, category_decisions)
        # Run this statement as part of the current workflow.
        context.user_data[BULK_EDIT_CATEGORY_DECISION_KEY] = state
        # Run this statement as part of the current workflow.
        decision, current_number, total = get_current_bulk_edit_category_decision(state)
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_bulk_edit_category_choice_text(decision, current_number, total),
            parse_mode="Markdown",
            reply_markup=build_bulk_edit_category_choice_keyboard(decision.get("suggested_category")),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    context.user_data["pending_bulk_edit_txns"] = build_bulk_edit_confirm_state(entries)

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_bulk_edit_preview_text(entries),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("edit_txns_bulk"),
    # Close the structure that was opened above.
    )

# Handle the asynchronous edit txn handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare raw text for the next step.
    raw_text = update.message.text.strip()

    # Prepare bulk lines for the next step.
    bulk_lines = extract_bulk_edit_txn_lines(raw_text)
    # Handle the case where bulk_lines.
    if bulk_lines:
        # Wait for bulk_edit_txn_handler before continuing this flow.
        await bulk_edit_txn_handler(update, context, bulk_lines)
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare parts for the next step.
        parts = shlex.split(raw_text)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Format edit tidak valid. Kalau ada spasi, pakai tanda kutip.\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Implementation note for this project-specific finance flow.
    args = parts[1:]

    # Handle the case where len(args) < 2.
    if len(args) < 2:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Format edit belum lengkap.\n\n"
            "Contoh:\n"
            "`/last`\n"
            "`/edit_txn 2 amount=15000`\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`\n"
            "`/edit_txn 2 account=BRI category=\"Food & Beverage\"`\n"
            "`/edit_txn 2 15000`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare ref for the next step.
    ref = args[0]
    # Prepare update args for the next step.
    update_args = args[1:]

    # Prepare resolved for the next step.
    resolved = resolve_txn_refs_from_last(context, [ref])

    if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
            "Jalankan dulu:\n"
            "`/last`\n\n"
            "Lalu edit dengan:\n"
            "`/edit_txn 2 amount=15000`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    row_index = resolved["row_indices"][0] if resolved["row_indices"] else None
    txn_id = resolved["txn_ids"][0] if resolved["txn_ids"] else None

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare debt payment conversion for the next step.
        debt_payment_conversion = parse_edit_debt_payment_conversion_args(update_args)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh konversi pembayaran debt:\n"
            "`/edit_txn 2 bayar_hutang Sapto`\n"
            "`/edit_txn 2 bayar_piutang Sapto`\n"
            "`/edit_txn 2 debt=payable person=Sapto`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Handle the case where debt_payment_conversion.
    if debt_payment_conversion:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare updates for the next step.
            updates = build_debt_payment_conversion_updates(debt_payment_conversion)
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            await update.message.reply_text(f"❌ {md_safe(str(e))}", parse_mode="Markdown")
            # Return control to the caller.
            return

        # Open a multi-line structure for the values below.
        preview = preview_edit_transaction_by_ref(
            # Prepare updates for the next step.
            updates=updates,
            # Prepare row index for the next step.
            row_index=row_index,
            # Prepare txn id for the next step.
            txn_id=txn_id,
        # Close the structure that was opened above.
        )

        if not preview.get("success"):
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"❌ {preview.get('message')}",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        # Open a multi-line structure for the values below.
        debt_check = validate_edit_debt_payment_conversion(
            # Include this value in the surrounding collection or call.
            debt_payment_conversion,
            float((preview.get("new_txn") or {}).get("amount", 0) or 0),
        # Close the structure that was opened above.
        )

        if not debt_check.get("success"):
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"❌ {md_safe(debt_check.get('message') or 'Debt aktif tidak ditemukan.')}",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        context.user_data["pending_edit_txn"] = {
            "row_index": row_index,
            "txn_id": txn_id,
            "updates": updates,
            "split_raw": "",
            "split_parsed": None,
            "debt_payment_conversion": debt_payment_conversion,
            "debt_check": debt_check,
        # Close the structure that was opened above.
        }

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_edit_debt_payment_preview_text(preview, debt_payment_conversion, debt_check),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("edit_txn"),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare updates for the next step.
        updates = parse_edit_updates(update_args)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000`\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`\n"
            "`/edit_txn 2 account=BRI category=\"Food & Beverage\"`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Handle the missing or empty updates case.
    if not updates:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Tidak ada field yang diedit.\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    row_index = resolved["row_indices"][0] if resolved["row_indices"] else None
    txn_id = resolved["txn_ids"][0] if resolved["txn_ids"] else None

    # Open a multi-line structure for the values below.
    preview = preview_edit_transaction_by_ref(
        # Prepare updates for the next step.
        updates=updates,
        # Prepare row index for the next step.
        row_index=row_index,
        # Prepare txn id for the next step.
        txn_id=txn_id,
    # Close the structure that was opened above.
    )

    if not preview.get("success"):
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ {preview.get('message')}",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    split_raw = " ".join(update_args)
    # Prepare has split bill for the next step.
    has_split_bill = edit_args_contain_split_bill(update_args)
    # Handle the case where await maybe_prompt_edit_category_choice(.
    if await maybe_prompt_edit_category_choice(
        # Include this value in the surrounding collection or call.
        update,
        # Include this value in the surrounding collection or call.
        context,
        # Prepare updates for the next step.
        updates=updates,
        # Prepare preview for the next step.
        preview=preview,
        # Prepare row index for the next step.
        row_index=row_index,
        # Prepare txn id for the next step.
        txn_id=txn_id,
        # Prepare split raw for the next step.
        split_raw=split_raw,
        # Prepare has split bill for the next step.
        has_split_bill=has_split_bill,
    # Close the structure that was opened above.
    ):
        # Return control to the caller.
        return

    # Prepare split parsed for the next step.
    split_parsed = None
    # Handle the case where has_split_bill.
    if has_split_bill:
        split_parsed = dict(preview.get("new_txn", {}) or {})
        # Run this statement as part of the current workflow.
        attach_split_bill_if_any(split_parsed, split_raw)

        # Handle the case where split_bill_needs_decision(split_parsed).
        if split_bill_needs_decision(split_parsed):
            context.user_data["pending_edit_txn"] = {
                "row_index": row_index,
                "txn_id": txn_id,
                "updates": updates,
                "split_raw": split_raw,
                "split_parsed": split_parsed,
            # Close the structure that was opened above.
            }
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                # Include this value in the surrounding collection or call.
                build_split_bill_prompt_from_parsed(split_parsed),
                parse_mode="Markdown",
                reply_markup=split_bill_keyboard("edit_txn"),
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

    context.user_data["pending_edit_txn"] = {
        "row_index": row_index,
        "txn_id": txn_id,
        "updates": updates,
        "split_raw": split_raw if split_parsed else "",
        "split_parsed": split_parsed,
    # Close the structure that was opened above.
    }

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_edit_split_preview_text(preview, split_parsed),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("edit_txn"),
    # Close the structure that was opened above.
    )


# ── Callback Handler ─────────────────────────────────────────────────────────

