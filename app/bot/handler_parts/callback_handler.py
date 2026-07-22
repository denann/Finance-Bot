"""Central callback handler for inline buttons such as preview, edit, save, cancel, debt, split bill, recurring, and asset flows."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import (
    ContextTypes,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    SKIP_ACCOUNT_CALLBACK_VALUE,
    SKIP_ACCOUNT_NAME,
    Update,
    account_keyboard,
    add_asset,
    add_debt,
    add_payment,
    add_payment_by_person,
    build_pending_expense_from_text,
    calculate_account_deltas,
    cancel_keyboard,
    check_budget_after_transaction,
    clear_transaction_debt_relation,
    confirm_keyboard,
    datetime,
    delete_transactions_by_refs,
    detect_date,
    edit_transaction_by_ref,
    estimate_payment_outcome,
    format_debt_net_position_lines,
    format_month_label,
    format_rupiah,
    get_account_balance,
    get_debt_by_person,
    is_authorized,
    md_code_text,
    md_safe,
    normalize_month,
    offset_debt_by_person,
    parse_debt_input,
    parse_human_amount,
    parse_sheet_number,
    parse_with_regex,
    preview_edit_transaction_by_ref,
    re,
    reject_unauthorized,
    safe_edit_message,
    save_pending_expense,
    save_transaction,
    save_transactions_batch,
    set_budget,
    settle_selected_debt_ids,
    short_debt_id,
    show_callback_loading,
    strip_date_phrases,
    update_account_balance,
    update_transaction_debt_relation,
    void_debt,
    void_debt_ids,
    void_debts_for_transaction,
)
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import create_account
from app.services.operation_errors import PartialMutationError
from app.services.recurring_service import get_recurring_rule_by_id
# Import app.bot.handler_parts.state_utils so this module can use its helpers.
from app.bot.handler_parts.state_utils import BULK_EDIT_CATEGORY_DECISION_KEY, EDIT_CATEGORY_CHOICE_KEY, clear_pending_flow_state
from app.application.external_io import run_sheets_read
# Import app.bot.handler_parts.networth_assets so this module can use its helpers.
from app.bot.handler_parts.networth_assets import build_asset_added_text, handle_asset_add_skip_callback
# Import app.bot.handler_parts.category_flow so this module can use its helpers.
from app.bot.handler_parts.category_flow import CATEGORY_ADD_FLOW_KEY, handle_category_confirm_callback, handle_category_type_callback
# Import app.bot.handler_parts.command_router so this module can use its helpers.
from app.bot.handler_parts.command_router import short_txn_id
# Import app.bot.handler_parts.message_handlers so this module can use its helpers.
from app.bot.handler_parts.message_handlers import (
    build_bulk_edit_category_choice_keyboard,
    build_bulk_edit_category_choice_text,
    build_bulk_edit_confirm_state,
    build_bulk_edit_preview_text,
    get_current_bulk_edit_category_decision,
)
# Import app.bot.handler_parts.health_recurring_export so this module can use its helpers.
from app.bot.handler_parts.health_recurring_export import (
    build_recurring_saved_text,
    handle_recurring_add_skip_callback,
    save_pending_recurring_rule,
)
# Import app.bot.handler_parts.transaction_flow so this module can use its helpers.
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
    build_mixed_account_prompt,
    build_mixed_detail_preview,
    build_mixed_edit_choose_prompt,
    build_mixed_final_summary,
    build_mixed_preview,
    build_mixed_short_summary,
    build_mixed_split_bill_queue_prompt,
    build_preview,
    build_preview_edit_help,
    build_preview_edit_keyboard,
    build_preview_field_help,
    build_preview_field_value_prompt,
    build_receipt_account_prompt,
    build_receipt_all_mixed_items,
    build_receipt_final_preview,
    build_receipt_part_selection_prompt,
    build_single_account_prompt,
    build_single_split_bill_final_summary,
    parse_preview_direct_field_update,
    build_single_short_summary,
    build_split_bill_prompt_from_parsed,
    create_split_bill_debt,
    debt_uses_cashflow,
    edit_or_continue_keyboard,
    preview_action_keyboard,
    preview_action_question,
    single_ready_to_save,
    mixed_ready_to_save,
    debt_ready_to_save,
    format_split_debt_result_lines,
    mixed_needs_account,
    mixed_split_bill_keyboard,
    mixed_split_bill_needs_decision,
    needs_account,
    proceed_after_preview_edit,
    split_bill_keyboard,
    split_bill_needs_decision,
    build_debt_only_confirm_preview,
    build_pending_expense_confirm_preview,
    build_meal_split_allocation_prompt,
    build_meal_split_detail_preview,
    build_meal_split_final_payload,
    build_meal_split_final_summary,
    build_meal_split_payer_prompt,
    build_social_spending_expense,
    compute_equal_meal_split_shares,
    meal_split_allocation_keyboard,
    meal_split_continue_keyboard,
    meal_split_payer_keyboard,
    meal_split_status_keyboard,
    build_meal_split_status_prompt,
    build_meal_split_custom_allocation_prompt,
)
# Import app.nlp.parse_safety so this module can use its helpers.
from app.nlp.parse_safety import extract_person_candidate
# Import app.nlp.regex_parser so this module can use its helpers.
from app.nlp.regex_parser import detect_category
# Import app.nlp.normalizer so this module can use its helpers.
from app.nlp.normalizer import normalize_text


# Helper for is skip account choice.
def is_skip_account_choice(account: str) -> bool:
    """Check whether an account callback means `Sudah berlalu`.

    Args:
        account: Account value from callback data.

    Returns:
        True when the callback asks the bot not to update any account balance.
    """
    return str(account or "").strip() == SKIP_ACCOUNT_CALLBACK_VALUE


# Helper for mark transaction as historical.
def mark_transaction_as_historical(parsed: dict) -> dict:
    """Mark a transaction as historical without balance mutation.

    Args:
        parsed: Pending transaction payload.

    Returns:
        The same transaction payload with historical flags and account label.

    Notes:
        This mutates the provided dict because the pending transaction is stored
        in `context.user_data`.
    """
    parsed["skip_account"] = True
    parsed["account"] = SKIP_ACCOUNT_NAME
    parsed["catatan"] = (str(parsed.get("catatan") or "").strip() + " | sudah berlalu/tanpa update saldo").strip(" |")
    return parsed


# Helper for mark debt as historical.
def mark_debt_as_historical(debt_parsed: dict) -> dict:
    """Mark a debt flow as debt-only without rekening cashflow.

    Args:
        debt_parsed: Pending debt payload.

    Returns:
        The same debt payload with debt-only mode and historical account label.

    Notes:
        This mutates the provided dict so later callbacks keep the same state.
    """
    debt_parsed["cashflow_mode"] = "debt_only"
    debt_parsed["fronting_mode"] = debt_parsed.get("fronting_mode") or "sudah_berlalu"
    debt_parsed["account"] = SKIP_ACCOUNT_NAME
    debt_parsed["catatan"] = (str(debt_parsed.get("catatan") or "").strip() + " | sudah berlalu/tanpa update saldo").strip(" |")
    return debt_parsed


# Helper for split debt id text.
def _split_debt_id_text(value) -> list[str]:
    """Coordinate the split debt id text logic in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Validate missing value before continuing.
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        # Prepare raw items from the incoming input.
        raw_items = value
    # Use the fallback path when no earlier branch matched.
    else:
        raw_items = str(value).split(",")
    seen = set()
    # Build result for the response flow.
    result = []
    # Iterate through each item.
    for item in raw_items:
        debt_id = str(item or "").strip()
        # Handle debt id and debt id not in seen.
        if debt_id and debt_id not in seen:
            # Append the current value to result.
            result.append(debt_id)
            # Append the current value to seen.
            seen.add(debt_id)
    return result


# Helper for merge debt ids.
def _merge_debt_ids(*values) -> str:
    """Coordinate the merge debt ids logic in the Telegram handler layer.

    Args:
        *values: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    merged = []
    seen = set()
    # Iterate through each value.
    for value in values:
        # Iterate through each debt id.
        for debt_id in _split_debt_id_text(value):
            if debt_id not in seen:
                # Append the current value to merged.
                merged.append(debt_id)
                # Append the current value to seen.
                seen.add(debt_id)
    return ", ".join(merged)


# Helper for create fronted split receivable debts.
def create_fronted_split_receivable_debts(debt_parsed: dict) -> dict:
    """Coordinate the create fronted split receivable debts logic in the Telegram handler layer.

    Args:
        debt_parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    if not debt_parsed or debt_parsed.get("intent") != "add_payable":
        return {"created": [], "failed": []}

    split_bill = debt_parsed.get("fronted_split_bill") or {}
    # Validate missing split bill before continuing.
    if not split_bill:
        return {"created": [], "failed": []}

    person_shares = split_bill.get("person_shares") or debt_parsed.get("fronted_person_shares") or {}
    # Validate missing person shares before continuing.
    if not person_shares:
        return {"created": [], "failed": []}

    payer = str(debt_parsed.get("person_name") or "").strip()
    item_desc = str(debt_parsed.get("expense_description") or debt_parsed.get("description") or "Ditalangin").strip()
    description = f"Split bill ditalangin {payer}: {item_desc}" if payer else f"Split bill ditalangin: {item_desc}"

    created = []
    failed = []
    # Iterate through each person, share.
    for person, share in person_shares.items():
        person_name = str(person or "").strip()
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Extract amount for validation.
            amount = float(share or 0)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Extract amount for validation.
            amount = 0.0
        # Validate missing person name or amount <= 0 before continuing.
        if not person_name or amount <= 0:
            # Skip the rest of this loop iteration after handling this case.
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
        # Use the fallback path when no earlier branch matched.
        else:
            failed.append({
                "person_name": person_name,
                "amount": amount,
                "message": result.get("message") if result else "Unknown error",
            })

    return {"created": created, "failed": failed}


# Helper for attach fronted split debt relations.
def attach_fronted_split_debt_relations(debt_parsed: dict, debt_result: dict, split_result: dict) -> dict:
    """Coordinate the attach fronted split debt relations logic in the Telegram handler layer.

    Args:
        debt_parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        debt_result: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        split_result: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
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
    """Apply the append fronted split result lines operation in the Telegram handler layer.

    Args:
        lines: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        split_result: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        indent: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    created = (split_result or {}).get("created", [])
    failed = (split_result or {}).get("failed", [])
    if created:
        total = sum(float(x.get("amount", 0) or 0) for x in created)
        detail = ", ".join(
            f"{x.get('person_name')}: {format_rupiah(x.get('amount', 0))}"
            # Iterate through each x.
            for x in created
        )
        lines.append(f"{indent}🤝 Piutang PTPT dibuat: *{format_rupiah(total)}* ({md_safe(detail)})")
    # Iterate through each item.
    for item in failed:
        lines.append(
            f"{indent}⚠️ Piutang PTPT gagal untuk {md_safe(item.get('person_name'))}: "
            f"{md_safe(item.get('message'))}"
        )



# Helper for build edit txn preview text for callback.
def build_edit_txn_preview_text_for_callback(preview: dict, split_parsed: dict | None = None) -> str:
    """Handle callback-related behavior in the Telegram bot flow."""
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
        # Iterate through each field, value.
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
        # Iterate through each account, delta.
        for account, delta in net_deltas.items():
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {md_safe(account)}: {sign}{format_rupiah(abs(delta))}")
    # Use the fallback path when no earlier branch matched.
    else:
        lines.append("\n*Efek ke saldo:*\n• Tidak ada perubahan saldo")

    lines.append("\nSimpan perubahan ini?")
    return "\n".join(lines)


# Helper for parse debt ids from txn record for edit.
def parse_debt_ids_from_txn_record_for_edit(txn: dict) -> list[str]:
    """Parse caller input for the parse debt ids from txn record for edit workflow in the Telegram handler layer.

    Args:
        txn: Transaction dict or transaction-like row from the finance data layer.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    raw = str((txn or {}).get("hutang_id", "") or "").strip()
    # Validate missing raw before continuing.
    if not raw:
        return []
    return [part.strip() for part in re.split(r"[,;\s]+", raw) if part.strip()]


# Helper for overpayment decision keyboard.
def overpayment_decision_keyboard() -> InlineKeyboardMarkup:
    """Coordinate the overpayment decision keyboard logic in the Telegram handler layer.

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
        [InlineKeyboardButton("✅ Anggap lunas / bonus", callback_data="debt_overpay:bonus")],
        [InlineKeyboardButton("🔴 Catat sebagai hutang saya", callback_data="debt_overpay:opposite_debt")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:debt")],
    ])


# Helper for build overpayment decision text.
def build_overpayment_decision_text(parsed: dict, outcome: dict) -> str:
    """Build the data structure or message text for overpayment decision text."""
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


# Helper for resolve payment target type.
def resolve_payment_target_type(parsed: dict, debts: list[dict]) -> tuple[str | None, str | None]:
    """Resolve a user input or reference for payment target type."""
    target = str(parsed.get("target_debt_type") or "").strip().lower()
    if target == "auto":
        target = ""

    debt_types = {str(d.get("type", "")).strip() for d in debts if str(d.get("type", "")).strip()}

    if target not in {"payable", "receivable"}:
        total_payable = sum(
            parse_sheet_number(d.get("remaining_amount", 0))
            # Iterate through each d.
            for d in debts
            if str(d.get("type", "")).strip() == "payable"
        )
        total_receivable = sum(
            parse_sheet_number(d.get("remaining_amount", 0))
            # Iterate through each d.
            for d in debts
            if str(d.get("type", "")).strip() == "receivable"
        )

        if total_receivable > total_payable:
            target = "receivable"
        # Fall back when total payable > total receivable.
        elif total_payable > total_receivable:
            target = "payable"
        # Fall back when len(debt types) == 1.
        elif len(debt_types) == 1:
            target = next(iter(debt_types))
        # Use the fallback path when no earlier branch matched.
        else:
            return None, "Saldo utang dan piutang sama besar. Pakai input lebih spesifik."

    if not any(str(d.get("type", "")).strip() == target for d in debts):
        label = "utang" if target == "payable" else "piutang"
        return None, f"Tidak ada {label} aktif untuk arah pembayaran ini."

    return target, None


# Helper for clear parse clarification state.
def clear_parse_clarification_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parse caller input for the clear parse clarification state workflow in the Telegram handler layer.

    Args:
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        `None` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    context.user_data.pop("pending_parse_clarification", None)


# Helper for infer clarified payment target type.
def infer_clarified_payment_target_type(raw: str) -> str:
    """Coordinate the infer clarified payment target type logic in the Telegram handler layer.

    Args:
        raw: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Normalize clean before matching.
    clean = normalize_text(raw)
    if re.search(r"^\s*(?:saya|aku|gw|gue|gua)\s+(?:bayar|byr)\b", clean):
        return "payable"
    if re.search(r"^\s*(?:bayar|byr)\s+(?:ke\s+)?[a-zA-ZÀ-ÿ]", clean):
        return "payable"
    return "receivable"


# Helper for build clarified debt payment.
def build_clarified_debt_payment(raw: str, parsed: dict | None = None) -> dict | None:
    """Build the data structure or message text for clarified debt payment."""
    parsed = parsed or {}
    amount = float(parsed.get("amount") or parse_human_amount(raw) or 0)
    person = extract_person_candidate(raw) or parsed.get("person_name") or parsed.get("subject") or ""
    person = re.sub(r"\s+", " ", str(person or "")).strip().title()
    # Validate missing person or amount <= 0 before continuing.
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


# Helper for build expense candidate raw.
def build_expense_candidate_raw(raw: str) -> str:
    """Build the data structure or message text for expense candidate raw."""
    clean = str(raw or "").strip()
    # Example cleanup: remove the person prefix so the description stays focused on the expense item.
    # Example cleanup: remove the person prefix so the description stays focused on the expense item.
    clean = re.sub(
        r"^\s*(?!saya\b|aku\b|gw\b|gue\b|gua\b)([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{0,30}?)\s+(?:bayar|byr)\s+",
        "bayar ",
        clean,
        flags=re.IGNORECASE,
    )
    return clean


# Helper for build clarified expense.
def build_clarified_expense(raw: str, parsed: dict | None = None) -> dict | None:
    """Build the data structure or message text for clarified expense."""
    parsed = dict(parsed or {})
    # Prepare expense raw from the incoming input.
    expense_raw = build_expense_candidate_raw(raw)
    # Extract candidate for validation.
    candidate = parse_with_regex(expense_raw) or parse_with_regex(raw)
    if candidate and candidate.get("type") in {"expense", "income", "transfer"}:
        parsed = dict(candidate)
    # Use the fallback path when no earlier branch matched.
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


# Helper for build clarified fronting.
def build_clarified_fronting(raw: str, parsed: dict | None = None) -> dict | None:
    """Build the data structure or message text for clarified fronting."""
    parsed = parsed or {}
    amount = float(parsed.get("amount") or parse_human_amount(raw) or 0)
    person = extract_person_candidate(raw) or parsed.get("person_name") or parsed.get("subject") or ""
    person = re.sub(r"\s+", " ", str(person or "")).strip().title()
    # Validate missing person or amount <= 0 before continuing.
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


# callback_data routes the user back to the correct flow without saving before confirmation.

# Helper for build set balance callback preview.
def _build_set_balance_callback_preview(account_name: str, current_balance: float, new_balance: float, *, create_missing: bool = False) -> str:
    """Build set balance preview text from callback state."""
    delta = float(new_balance or 0) - float(current_balance or 0)
    sign = "+" if delta >= 0 else "-"
    title = "⚠️ *Preview Tambah Rekening dan Set Saldo*" if create_missing else "⚠️ *Preview Set Saldo Rekening*"
    action_note = (
        "Aksi ini akan menambahkan rekening baru ke sheet `accounts`, lalu mengisi saldo awalnya. Tidak akan membuat row transaksi baru."
        if create_missing
        else "Aksi ini akan menimpa saldo rekening di sheet `accounts`. Tidak akan membuat row transaksi baru."
    )
    current_label = "Saldo awal" if create_missing else "Saldo sekarang"
    return (
        f"{title}\n\n"
        f"{action_note}\n\n"
        f"🏦 Rekening: *{md_safe(account_name)}*\n"
        f"💰 {current_label}: *{format_rupiah(current_balance)}*\n"
        f"🎯 Saldo baru: *{format_rupiah(new_balance)}*\n"
        f"🔁 Selisih: *{sign}{format_rupiah(abs(delta))}*\n\n"
        "Klik *Simpan* kalau sudah benar, atau *Batal* kalau masih mau cek lagi."
    )


# Helper for build saved account balance info.
def _build_saved_account_balance_info(parsed: dict, result: dict) -> str:
    """Build saved account balance details, including both sides of transfer."""
    new_balances = result.get("new_balances") or {}
    deltas = calculate_account_deltas([{"parsed": parsed or {}}])

    if deltas and new_balances:
        lines = ["\n💳 *Ringkasan per rekening:*"]
        # Iterate through each account name, delta.
        for account_name, delta in deltas.items():
            balance = None
            display_name = account_name
            # Iterate through each saved name, saved balance.
            for saved_name, saved_balance in new_balances.items():
                if str(saved_name).strip().lower() == str(account_name).strip().lower():
                    display_name = saved_name
                    balance = saved_balance
                    # Leave the loop after the target condition has been reached.
                    break

            sign = "+" if float(delta or 0) >= 0 else "-"
            if balance is not None:
                lines.append(
                    f"• {md_safe(display_name)}: {sign}{format_rupiah(abs(float(delta or 0)))} → saldo *{format_rupiah(balance)}*"
                )
            # Use the fallback path when no earlier branch matched.
            else:
                lines.append(
                    f"• {md_safe(display_name)}: {sign}{format_rupiah(abs(float(delta or 0)))}"
                )
        return "\n" + "\n".join(lines)

    if result.get("new_balance") is not None:
        balance_account = (
            result.get("new_balance_account")
            or (parsed or {}).get("to_account")
            or (parsed or {}).get("account")
            or "-"
        )
        return (
            f"\n💳 Saldo {md_safe(balance_account)}: "
            f"*{format_rupiah(result['new_balance'])}*"
        )

    return ""


# Helper for apply bulk edit category decision.
async def apply_bulk_edit_category_decision(state: dict, decision: dict, category_name: str) -> dict:
    """Apply one resolved category decision to pending bulk edit state.

    Args:
        state: Pending queue stored under `BULK_EDIT_CATEGORY_DECISION_KEY`.
            Expected keys are `entries`, `decisions`, and `current_index`.
        decision: Current queue item. It must contain `entry_index`, pointing to
            the affected row in `state["entries"]`.
        category_name: Final category chosen for that row. This can be the
            suggested existing category or the raw category after the add-category
            wizard finishes.

    Returns:
        Result dict with `success`, optional `message`, and updated `state`.

    Notes:
        This rebuilds preview data only. It does not write to Google Sheets; the
        write still requires the final `confirm:edit_txns_bulk` callback.
    """
    entries = (state or {}).get("entries") or []
    entry_index = int((decision or {}).get("entry_index") or -1)
    # Handle entry index < 0 or entry index >= len(entries).
    if entry_index < 0 or entry_index >= len(entries):
        return {"success": False, "message": "Index baris bulk edit tidak valid.", "state": state}

    entry = entries[entry_index]
    updates = dict(entry.get("updates") or {})
    updates["category"] = str(category_name or "").strip()

    preview = await run_sheets_read(
        "preview_edit_transaction_by_ref",
        preview_edit_transaction_by_ref,
        updates=updates,
        row_index=entry.get("row_index"),
        txn_id=entry.get("txn_id"),
    )
    if not preview.get("success"):
        return {
            "success": False,
            "message": preview.get("message") or "Gagal preview ulang bulk edit.",
            "state": state,
        }

    entry["updates"] = preview.get("updates") or updates
    entry["preview"] = preview
    entries[entry_index] = entry
    state["entries"] = entries
    state["current_index"] = int(state.get("current_index") or 0) + 1
    state["paused_for_category_add"] = None
    return {"success": True, "state": state}


# Handle the asynchronous show next or final bulk edit category decision workflow.
async def show_next_or_final_bulk_edit_category_decision(query, context: ContextTypes.DEFAULT_TYPE, state: dict) -> None:
    """Show the next bulk category decision or the final bulk edit preview.

    Args:
        query: Telegram callback query whose message should be edited.
        context: Telegram context used to move state from the category queue to
            final bulk edit confirmation.
        state: Updated pending bulk category decision queue.

    Returns:
        None. When all decisions are resolved, this function creates
        `pending_bulk_edit_txns` and shows the existing Simpan/Batal preview.
    """
    decision, current_number, total = get_current_bulk_edit_category_decision(state)
    # Validate missing decision before continuing.
    if not decision:
        entries = (state or {}).get("entries") or []
        context.user_data.pop(BULK_EDIT_CATEGORY_DECISION_KEY, None)
        context.user_data["pending_bulk_edit_txns"] = build_bulk_edit_confirm_state(entries)
        # Send the Telegram response before continuing.
        await safe_edit_message(
            query,
            build_bulk_edit_preview_text(entries),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("edit_txns_bulk"),
        )
        return

    context.user_data[BULK_EDIT_CATEGORY_DECISION_KEY] = state
    # Send the Telegram response before continuing.
    await safe_edit_message(
        query,
        build_bulk_edit_category_choice_text(decision, current_number, total),
        parse_mode="Markdown",
        reply_markup=build_bulk_edit_category_choice_keyboard(decision.get("suggested_category")),
    )


# Handle the asynchronous start bulk edit category add wizard workflow.
async def start_bulk_edit_category_add_wizard(query, context: ContextTypes.DEFAULT_TYPE, state: dict, decision: dict) -> None:
    """Pause bulk category decisions and start add-category wizard.

    Args:
        query: Telegram callback query from `Tambah kategori baru`.
        context: Telegram context used to keep both the paused bulk queue and
            the category add wizard state.
        state: Pending bulk category queue that should be paused.
        decision: Current queue item whose raw category becomes the new category
            name.

    Returns:
        None. The function asks for the category symbol and leaves transaction
        edits unwritten until the final bulk preview is confirmed.
    """
    raw_category = str((decision or {}).get("raw_category") or "").strip()
    transaction_type = str((decision or {}).get("transaction_type") or "expense").strip().lower()
    transaction_type = transaction_type if transaction_type in {"expense", "income"} else "expense"

    # Keep queue position stable so the user can resume after category save.
    state["paused_for_category_add"] = int(state.get("current_index") or 0)
    context.user_data[BULK_EDIT_CATEGORY_DECISION_KEY] = state
    context.user_data[CATEGORY_ADD_FLOW_KEY] = {
        "stage": "symbol",
        "mode": "add",
        "category_name": raw_category,
        "type": transaction_type,
    }
    # Send the Telegram response before continuing.
    await safe_edit_message(
        query,
        "Oke, kita tambah kategori baru dulu.\n\n"
        f"Kategori: *{md_safe(raw_category or '-')}*\n"
        f"Tipe: *{md_safe(transaction_type)}*\n\n"
        "Symbolnya apa?",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def legacy_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route Telegram inline button callbacks to the right pending flow.

    Args:
        update: Telegram update that contains the callback query.
        context: Telegram context used to read and update pending flow state.

    Notes:
        Callback data is the routing contract for this bot. The handler may
        update `context.user_data`, edit Telegram messages, save confirmed data,
        or cancel pending sessions depending on the callback prefix.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    query = update.callback_query

    data = query.data or ""
    # Await show callback loading before continuing.
    await show_callback_loading(query)

    if data.startswith("cancel:a_"):
        from app.bot.pending_actions import PendingActionError, cancel_pending_action

        action_id = data.split(":", 1)[1]
        try:
            cancel_pending_action(
                context.user_data,
                action_id,
                owner_user_id=int(getattr(query.from_user, "id", 0) or 0),
                message_id=getattr(query.message, "message_id", None),
            )
        except PendingActionError:
            await safe_edit_message(query, "❌ Preview ini sudah kedaluwarsa, sudah dipakai, atau bukan milik Anda. Tidak ada data yang diubah.")
            return

        await safe_edit_message(query, "🚫 Input dibatalkan. Tidak ada data yang disimpan.")
        return

    # Category wizard type selection: expense/income button, no sheet write yet.
    if data.startswith("category_type:"):
        handled = await handle_category_type_callback(query, context, data)
        if handled:
            return

    # Category choice for /edit_txn: use existing category or start add-category wizard.
    if data.startswith("edit_category_choice:"):
        action = data.split(":", 1)[1]
        pending_choice = context.user_data.get(EDIT_CATEGORY_CHOICE_KEY) or {}
        # Validate missing pending choice before continuing.
        if not pending_choice:
            await safe_edit_message(query, "❌ Sesi pilihan kategori expired. Coba ulangi `/edit_txn`.", parse_mode="Markdown")
            return

        raw_category = str(pending_choice.get("raw_category") or "").strip()
        suggested_category = str(pending_choice.get("suggested_category") or "").strip()
        transaction_type = str(pending_choice.get("transaction_type") or "expense").strip().lower()

        if action == "create":
            context.user_data.pop(EDIT_CATEGORY_CHOICE_KEY, None)
            context.user_data[CATEGORY_ADD_FLOW_KEY] = {
                "stage": "symbol",
                "mode": "add",
                "category_name": raw_category,
                "type": transaction_type if transaction_type in {"expense", "income"} else "expense",
            }
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                "Oke, kita tambah kategori baru dulu.\n\n"
                f"Kategori: *{md_safe(raw_category or '-')}*\n"
                f"Tipe: *{md_safe(transaction_type if transaction_type in {'expense', 'income'} else 'expense')}*\n\n"
                "Symbolnya apa?\n\n"
                "Setelah kategori tersimpan, ulangi `/edit_txn` untuk memakai kategori baru itu di transaksi.",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard(),
            )
            return

        if action != "use":
            await safe_edit_message(query, "❌ Pilihan kategori tidak valid.", parse_mode="Markdown")
            return

        updates = dict(pending_choice.get("updates") or {})
        updates["category"] = suggested_category
        preview = await run_sheets_read(
            "preview_edit_transaction_by_ref",
            preview_edit_transaction_by_ref,
            updates=updates,
            row_index=pending_choice.get("row_index"),
            txn_id=pending_choice.get("txn_id"),
        )
        if not preview.get("success"):
            context.user_data.pop(EDIT_CATEGORY_CHOICE_KEY, None)
            await safe_edit_message(query, f"❌ {preview.get('message') or 'Gagal preview edit.'}", parse_mode="Markdown")
            return

        split_parsed = None
        split_raw = str(pending_choice.get("split_raw") or "").strip()
        if bool(pending_choice.get("has_split_bill")):
            split_parsed = dict(preview.get("new_txn", {}) or {})
            attach_split_bill_if_any(split_parsed, split_raw)
            if split_bill_needs_decision(split_parsed):
                context.user_data.pop(EDIT_CATEGORY_CHOICE_KEY, None)
                context.user_data["pending_edit_txn"] = {
                    "row_index": pending_choice.get("row_index"),
                    "txn_id": pending_choice.get("txn_id"),
                    "updates": updates,
                    "split_raw": split_raw,
                    "split_parsed": split_parsed,
                }
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_split_bill_prompt_from_parsed(split_parsed),
                    parse_mode="Markdown",
                    reply_markup=split_bill_keyboard("edit_txn"),
                )
                return

        context.user_data.pop(EDIT_CATEGORY_CHOICE_KEY, None)
        context.user_data["pending_edit_txn"] = {
            "row_index": pending_choice.get("row_index"),
            "txn_id": pending_choice.get("txn_id"),
            "updates": updates,
            "split_raw": split_raw if split_parsed else "",
            "split_parsed": split_parsed,
        }
        # Send the Telegram response before continuing.
        await safe_edit_message(
            query,
            build_edit_txn_preview_text_for_callback(preview, split_parsed),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("edit_txn"),
        )
        return

    # Bulk category queue: resolve one category ambiguity per callback.
    if data.startswith("bulk_edit_category_choice:"):
        action = data.split(":", 1)[1]
        state = context.user_data.get(BULK_EDIT_CATEGORY_DECISION_KEY) or {}
        # Validate missing state before continuing.
        if not state:
            await safe_edit_message(query, "❌ Sesi pilihan kategori bulk edit expired. Coba ulangi bulk `/edit_txn`.", parse_mode="Markdown")
            return

        decision, _, _ = get_current_bulk_edit_category_decision(state)
        if action == "resume":
            paused_index = state.get("paused_for_category_add")
            current_index = int(state.get("current_index") or 0)
            # Handle paused index is None or int(paused index) != current index or.
            if paused_index is None or int(paused_index) != current_index or not decision:
                await safe_edit_message(query, "❌ Sesi lanjut bulk edit tidak valid. Coba ulangi bulk `/edit_txn`.", parse_mode="Markdown")
                context.user_data.pop(BULK_EDIT_CATEGORY_DECISION_KEY, None)
                return
            result = await apply_bulk_edit_category_decision(state, decision, decision.get("raw_category"))
            if not result.get("success"):
                context.user_data.pop(BULK_EDIT_CATEGORY_DECISION_KEY, None)
                await safe_edit_message(query, f"❌ {md_safe(result.get('message') or 'Gagal lanjut bulk edit.')}", parse_mode="Markdown")
                return
            await show_next_or_final_bulk_edit_category_decision(query, context, result.get("state") or state)
            return

        # Validate missing decision before continuing.
        if not decision:
            # Await show next or final bulk edit category decision before continuing.
            await show_next_or_final_bulk_edit_category_decision(query, context, state)
            return

        if action == "create":
            # Await start bulk edit category add wizard before continuing.
            await start_bulk_edit_category_add_wizard(query, context, state, decision)
            return

        if action != "use":
            await safe_edit_message(query, "❌ Pilihan kategori bulk edit tidak valid.", parse_mode="Markdown")
            return

        result = await apply_bulk_edit_category_decision(state, decision, decision.get("suggested_category"))
        if not result.get("success"):
            context.user_data.pop(BULK_EDIT_CATEGORY_DECISION_KEY, None)
            await safe_edit_message(query, f"❌ {md_safe(result.get('message') or 'Gagal preview bulk edit.')}", parse_mode="Markdown")
            return

        await show_next_or_final_bulk_edit_category_decision(query, context, result.get("state") or state)
        return

    if data == "asset_add:skip":
        # Await handle asset add skip callback before continuing.
        await handle_asset_add_skip_callback(query, context)
        return

    if data == "recurring_add:skip":
        # Await handle recurring add skip callback before continuing.
        await handle_recurring_add_skip_callback(query, context)
        return

    if data.startswith("set_balance_similar:"):
        action = data.split(":", 1)[1]
        pending = context.user_data.get("pending_set_balance_suggestion") or {}

        # Validate missing pending before continuing.
        if not pending:
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                "❌ Sesi set saldo expired. Jalankan `/set_saldo` lagi.",
                parse_mode="Markdown",
            )
            return

        new_balance = float(pending.get("new_balance", 0) or 0)

        if action == "use_existing":
            account_name = str(pending.get("suggested_account_name") or "").strip()
            current_balance = await run_sheets_read("get_account_balance", get_account_balance, account_name)
            if current_balance is None:
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    f"❌ Saldo rekening `{md_code_text(account_name)}` belum bisa dibaca dari sheet `accounts`.",
                    parse_mode="Markdown",
                )
                return

            context.user_data["pending_set_balance"] = {
                "account_name": account_name,
                "current_balance": float(current_balance),
                "new_balance": new_balance,
                "delta": new_balance - float(current_balance),
                "create_missing": False,
            }
            context.user_data.pop("pending_set_balance_suggestion", None)

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                _build_set_balance_callback_preview(account_name, float(current_balance), new_balance, create_missing=False),
                parse_mode="Markdown",
                reply_markup=confirm_keyboard("set_balance"),
            )
            return

        if action == "create_new":
            account_name = str(pending.get("input_account_name") or "").strip()
            context.user_data["pending_set_balance"] = {
                "account_name": account_name,
                "current_balance": 0.0,
                "new_balance": new_balance,
                "delta": new_balance,
                "create_missing": True,
                "account_type": pending.get("account_type") or "bank",
            }
            context.user_data.pop("pending_set_balance_suggestion", None)

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                _build_set_balance_callback_preview(account_name, 0.0, new_balance, create_missing=True),
                parse_mode="Markdown",
                reply_markup=confirm_keyboard("set_balance"),
            )
            return

        await safe_edit_message(query, "❌ Pilihan set saldo tidak valid.")
        return

    if data == "receipt:all":
        pending_receipt = context.user_data.get("pending_receipt") or {}
        receipt = pending_receipt.get("receipt") or {}
        items = pending_receipt.get("items") or []

        # Validate missing items before continuing.
        if not items:
            await safe_edit_message(query, "❌ Sesi struk expired. Coba kirim gambar ulang.")
            return

        mixed_items, receipt_context = build_receipt_all_mixed_items(receipt, items)
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
        await safe_edit_message(
            query,
            f"{preview}\n\n{preview_action_question(False)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", False),
        )
        return

    if data == "receipt:part":
        pending_receipt = context.user_data.get("pending_receipt") or {}
        receipt = pending_receipt.get("receipt") or {}
        items = pending_receipt.get("items") or []

        # Validate missing items before continuing.
        if not items:
            await safe_edit_message(query, "❌ Sesi struk expired. Coba kirim gambar ulang.")
            return

        context.user_data["pending_receipt_part_selection"] = {
            "receipt": receipt,
            "items": items,
        }
        context.user_data.pop("pending_receipt_extra_divisor", None)
        # Send the Telegram response before continuing.
        await safe_edit_message(
            query,
            build_receipt_part_selection_prompt(receipt, items),
            parse_mode="Markdown",
        )
        return

    if data.startswith("clarify_parse:"):
        choice = data.split(":", 1)[1].strip()
        pending = context.user_data.get("pending_parse_clarification") or {}
        raw = pending.get("raw") or ""
        parsed = pending.get("parsed") or {}

        # Validate missing raw before continuing.
        if not raw:
            clear_parse_clarification_state(context)
            await safe_edit_message(query, "❌ Sesi klarifikasi expired. Coba input ulang.")
            return

        if choice == "rewrite":
            clear_parse_clarification_state(context)
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                "✍️ Oke. Silakan tulis ulang inputnya dengan format yang lebih jelas.",
                parse_mode="Markdown",
            )
            return

        if choice == "no_cashflow":
            clear_parse_clarification_state(context)
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                "✅ Oke, tidak ada data yang disimpan karena ini dianggap tidak memengaruhi cashflow Anda.",
                parse_mode="Markdown",
            )
            return

        if choice == "pending_expense":
            # Run this operation in a guarded block so failures can be handled.
            try:
                item = build_pending_expense_from_text(raw)
            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                clear_parse_clarification_state(context)
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    f"❌ Pending expense belum kebaca: {md_safe(str(e))}\n\nSilakan tulis ulang dengan format yang lebih jelas, misalnya `pending wifi bulan depan 285k`.",
                    parse_mode="Markdown",
                )
                return

            context.user_data["pending_expense_confirm"] = item
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_debt_batch", None)
            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_mixed", None)
            clear_parse_clarification_state(context)
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                f"{build_pending_expense_confirm_preview(item, include_question=False)}\n\n{preview_action_question(True)}",
                parse_mode="Markdown",
                reply_markup=preview_action_keyboard("pending_expense", True),
            )
            return

        if choice == "payable":
            amount = float(parsed.get("amount") or parse_human_amount(raw) or 0)
            person = extract_person_candidate(raw) or parsed.get("person_name") or parsed.get("subject") or ""
            person = re.sub(r"\s+", " ", str(person or "")).strip().title()
            # Validate missing person or amount <= 0 before continuing.
            if not person or amount <= 0:
                clear_parse_clarification_state(context)
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    "❌ Nama orang atau nominal belum kebaca. Silakan tulis ulang inputnya.",
                    parse_mode="Markdown",
                )
                return
            debt_parsed = {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": f"Uang titipan/pinjaman dari {person}",
                "date": detect_date(raw),
                "raw_input": raw,
                "cashflow_mode": "cashflow",
                "fronting_mode": "clarified_payable_cash_in",
            }
            context.user_data["pending_debt"] = debt_parsed
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_mixed", None)
            clear_parse_clarification_state(context)
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                build_debt_account_prompt(debt_parsed),
                parse_mode="Markdown",
                reply_markup=account_keyboard("debt_acc"),
            )
            return

        if choice == "split":
            amount = float(parsed.get("amount") or parse_human_amount(raw) or 0)
            person = extract_person_candidate(raw) or parsed.get("person_name") or parsed.get("subject") or ""
            person = re.sub(r"\s+", " ", str(person or "")).strip().title()
            # Validate missing person or amount <= 0 before continuing.
            if not person or amount <= 0:
                clear_parse_clarification_state(context)
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    "❌ Nama orang atau nominal belum kebaca untuk split bill. Silakan tulis ulang inputnya.",
                    parse_mode="Markdown",
                )
                return
            guard = {
                "raw": raw,
                "people": [person],
                "amount": amount,
                "parsed": build_clarified_expense(raw, parsed) or parsed,
            }
            context.user_data["pending_social_spending_guard"] = guard
            context.user_data["pending_meal_split"] = {
                "raw": raw,
                "people": [person],
                "amount": amount,
                "parsed": guard["parsed"],
                "stage": "payer",
            }
            clear_parse_clarification_state(context)
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                build_meal_split_payer_prompt(context.user_data["pending_meal_split"]),
                parse_mode="Markdown",
                reply_markup=meal_split_payer_keyboard(),
            )
            return

        if choice == "debt_payment":
            debt_parsed = build_clarified_debt_payment(raw, parsed)
            # Validate missing debt parsed before continuing.
            if not debt_parsed:
                clear_parse_clarification_state(context)
                # Send the Telegram response before continuing.
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

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                f"{build_debt_initial_preview(debt_parsed)}\n\n{preview_action_question(True)}",
                parse_mode="Markdown",
                reply_markup=preview_action_keyboard("debt", True),
            )
            return

        if choice == "fronting":
            debt_parsed = build_clarified_fronting(raw, parsed)
            # Validate missing debt parsed before continuing.
            if not debt_parsed:
                clear_parse_clarification_state(context)
                # Send the Telegram response before continuing.
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

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                f"{build_debt_initial_preview(debt_parsed)}\n\n{preview_action_question(True)}",
                parse_mode="Markdown",
                reply_markup=preview_action_keyboard("debt", True),
            )
            return

        if choice == "expense":
            clarified = build_clarified_expense(raw, parsed)
            # Validate missing clarified before continuing.
            if not clarified:
                clear_parse_clarification_state(context)
                # Send the Telegram response before continuing.
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
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_split_bill_prompt_from_parsed(clarified),
                    parse_mode="Markdown",
                    reply_markup=split_bill_keyboard("single"),
                )
                return

            if needs_account(clarified):
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_single_account_prompt(clarified),
                    parse_mode="Markdown",
                    reply_markup=account_keyboard("acc"),
                )
                return

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                f"{build_preview(clarified)}\n\n{preview_action_question(True)}",
                parse_mode="Markdown",
                reply_markup=preview_action_keyboard("single", True),
            )
            return

        await safe_edit_message(query, "❌ Pilihan klarifikasi tidak valid.")
        return


    if data.startswith("meal_guard:"):
        choice = data.split(":", 1)[1].strip()
        guard = context.user_data.get("pending_social_spending_guard") or {}
        raw = guard.get("raw") or ""

        if choice == "rewrite":
            context.user_data.pop("pending_social_spending_guard", None)
            context.user_data.pop("pending_meal_split", None)
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                "✍️ Oke. Silakan tulis ulang inputnya dengan format yang lebih jelas.",
                parse_mode="Markdown",
            )
            return

        # Validate missing guard or not raw before continuing.
        if not guard or not raw:
            await safe_edit_message(query, "❌ Sesi makan bareng expired. Coba input ulang.")
            return

        if choice == "expense":
            parsed = build_social_spending_expense(raw, guard)
            context.user_data["pending_parsed"] = parsed
            context.user_data["pending_raw"] = raw
            context.user_data.pop("pending_social_spending_guard", None)
            context.user_data.pop("pending_meal_split", None)

            if needs_account(parsed):
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_single_account_prompt(parsed),
                    parse_mode="Markdown",
                    reply_markup=account_keyboard("acc"),
                )
                return

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                f"{build_preview(parsed)}\n\n{preview_action_question(True)}",
                parse_mode="Markdown",
                reply_markup=preview_action_keyboard("single", True),
            )
            return

        if choice == "split":
            state = {
                "raw": raw,
                "people": guard.get("people") or [],
                "amount": guard.get("amount") or 0,
                "parsed": guard.get("parsed") or {},
                "stage": "payer",
            }
            context.user_data["pending_meal_split"] = state
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                build_meal_split_payer_prompt(state),
                parse_mode="Markdown",
                reply_markup=meal_split_payer_keyboard(),
            )
            return

        await safe_edit_message(query, "❌ Pilihan makan bareng tidak valid.")
        return

    if data.startswith("meal_split:"):
        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        value = parts[2] if len(parts) > 2 else ""
        state = context.user_data.get("pending_meal_split") or {}

        # Validate missing state before continuing.
        if not state:
            await safe_edit_message(query, "❌ Sesi split bill expired. Coba input ulang.")
            return

        if action == "payer":
            if value not in {"self", "other"}:
                await safe_edit_message(query, "❌ Pilihan pembayar tidak valid.")
                return
            state["payer"] = value
            state["stage"] = "allocation"
            context.user_data["pending_meal_split"] = state
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                build_meal_split_allocation_prompt(state),
                parse_mode="Markdown",
                reply_markup=meal_split_allocation_keyboard(),
            )
            return

        if action == "allocation":
            if value == "equal":
                state["shares"] = compute_equal_meal_split_shares(
                    float(state.get("amount") or 0),
                    state.get("people") or [],
                )
                state["allocation_mode"] = "equal"
                state["stage"] = "status"
                context.user_data["pending_meal_split"] = state
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_meal_split_status_prompt(state),
                    parse_mode="Markdown",
                    reply_markup=meal_split_status_keyboard(state.get("payer") or "self"),
                )
                return

            if value == "custom":
                state["stage"] = "custom_allocation"
                context.user_data["pending_meal_split"] = state
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_meal_split_custom_allocation_prompt(state),
                    parse_mode="Markdown",
                )
                return

            await safe_edit_message(query, "❌ Pilihan pembagian tidak valid.")
            return

        if action == "status":
            if value not in {"paid", "unpaid"}:
                await safe_edit_message(query, "❌ Pilihan status pembayaran tidak valid.")
                return
            state["status"] = value
            state["stage"] = "detail_preview"
            # Build payload for the response flow.
            payload = build_meal_split_final_payload(state)
            state["payload"] = payload
            context.user_data["pending_meal_split"] = state
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                build_meal_split_detail_preview(state, payload),
                parse_mode="Markdown",
                reply_markup=meal_split_continue_keyboard(),
            )
            return

        if action == "continue":
            payload = state.get("payload") or build_meal_split_final_payload(state)
            mode = payload.get("mode")
            raw = state.get("raw") or ""
            context.user_data.pop("pending_social_spending_guard", None)

            if mode == "debt":
                debt_parsed = payload.get("debt") or {}
                context.user_data["pending_debt"] = debt_parsed
                context.user_data.pop("pending_parsed", None)
                context.user_data.pop("pending_raw", None)
                context.user_data.pop("pending_meal_split", None)
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    f"{build_debt_only_confirm_preview(debt_parsed)}\n\n{preview_action_question(True)}",
                    parse_mode="Markdown",
                    reply_markup=preview_action_keyboard("debt", True),
                )
                return

            parsed = payload.get("parsed") or {}
            context.user_data["pending_parsed"] = parsed
            context.user_data["pending_raw"] = raw
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_meal_split", None)

            if needs_account(parsed):
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_single_account_prompt(parsed, preview_text=build_meal_split_final_summary(parsed, "transaction")),
                    parse_mode="Markdown",
                    reply_markup=account_keyboard("acc"),
                )
                return

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                f"{build_meal_split_final_summary(parsed, 'transaction')}\n\n{preview_action_question(True)}",
                parse_mode="Markdown",
                reply_markup=preview_action_keyboard("single", True),
            )
            return

        await safe_edit_message(query, "❌ Pilihan split bill tidak valid.")
        return

    if data.startswith("recurring_paid:"):
        parts = data.split(":")
        if len(parts) != 3:
            await safe_edit_message(
                query,
                "❌ Tombol recurring lama sudah kedaluwarsa. Gunakan reminder terbaru agar transaksi tidak tercatat ganda.",
            )
            return
        rule_id = parts[1].strip()
        try:
            scheduled_run_date = datetime.strptime(parts[2].strip(), "%Y-%m-%d").date()
        except ValueError:
            await safe_edit_message(query, "❌ Tanggal occurrence recurring tidak valid. Tidak ada data yang diubah.")
            return
        rule = await run_sheets_read("get_recurring_rule_by_id", get_recurring_rule_by_id, rule_id)
        if not rule:
            await safe_edit_message(query, "❌ Recurring rule tidak ditemukan. Tidak ada data yang diubah.")
            return
        if str(rule.get("next_run_date") or "").strip() != scheduled_run_date.strftime("%Y-%m-%d"):
            await safe_edit_message(query, "❌ Reminder recurring ini sudah kedaluwarsa. Gunakan reminder terbaru.")
            return

        from app.bot.pending_actions import create_pending_action

        action = create_pending_action(
            context.user_data,
            owner_user_id=int(getattr(query.from_user, "id", 0) or 0),
            flow_type="command_mutation",
            payload={
                "operation": "recurring_occurrence_paid",
                "arguments": {
                    "rule_id": rule_id,
                    "scheduled_run_date": scheduled_run_date.strftime("%Y-%m-%d"),
                },
            },
            preview_message_id=getattr(query.message, "message_id", None),
        )
        action_id = action["action_id"]
        await safe_edit_message(
            query,
            "🧾 *Preview final — recurring sudah dibayar*\n\n"
            f"📌 {md_safe(rule.get('name') or '-')}\n"
            f"📅 Occurrence: {scheduled_run_date.strftime('%Y-%m-%d')}\n"
            f"💰 Nominal: *{format_rupiah(float(rule.get('amount') or 0))}*\n"
            f"💳 Rekening: *{md_safe(rule.get('account') or '-')}*\n\n"
            "Tekan Simpan untuk membuat satu transaksi, atau Batal.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Simpan", callback_data=f"confirm:{action_id}"),
                InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{action_id}"),
            ]]),
        )
        return
        # Build result for the response flow.
        result = {"success": False, "message": "unreachable legacy rendering block"}

        if result.get("success") and result.get("duplicate"):
            await safe_edit_message(
                query,
                "✅ Occurrence recurring ini sudah pernah diproses. Tidak ada transaksi atau saldo yang ditambahkan lagi.",
            )
        elif result.get("success"):
            rule = result.get("rule") or {}
            # Build balance lines for the response flow.
            balance_lines = []
            txn_type = str(result.get("type") or rule.get("type") or "").strip().lower()
            amount = float(result.get("amount") or rule.get("amount") or 0)
            account = result.get("account") or rule.get("account") or "-"
            to_account = result.get("to_account") or rule.get("to_account") or ""
            new_balances = result.get("new_balances") or {}

            if new_balances:
                balance_lines.append("\n💳 *Ringkasan per rekening:*")
                if txn_type == "transfer":
                    balance_deltas = {account: -amount, to_account: amount}
                elif txn_type == "income":
                    balance_deltas = {account: amount}
                # Use the fallback path when no earlier branch matched.
                else:
                    balance_deltas = {account: -amount}

                # Iterate through each balance account, delta.
                for balance_account, delta in balance_deltas.items():
                    if not str(balance_account or "").strip():
                        # Skip the rest of this loop iteration after handling this case.
                        continue
                    saved_balance = None
                    # Extract display account for validation.
                    display_account = balance_account
                    # Iterate through each saved account, balance.
                    for saved_account, balance in new_balances.items():
                        if str(saved_account).strip().lower() == str(balance_account).strip().lower():
                            # Extract display account for validation.
                            display_account = saved_account
                            saved_balance = balance
                            # Leave the loop after the target condition has been reached.
                            break
                    sign = "+" if delta >= 0 else "-"
                    if saved_balance is not None:
                        balance_lines.append(
                            f"• {md_safe(display_account)}: {sign}{format_rupiah(abs(delta))} → saldo *{format_rupiah(saved_balance)}*"
                        )
                    # Use the fallback path when no earlier branch matched.
                    else:
                        balance_lines.append(f"• {md_safe(display_account)}: {sign}{format_rupiah(abs(delta))}")

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                "✅ *Recurring ditandai sudah bayar.*\n\n"
                f"📌 {md_safe(rule.get('name') or '-')}\n"
                f"📝 Transaksi tersimpan: `{result.get('transaction_id')}`\n"
                f"🔕 Notifikasi berikutnya: `{result.get('next_run_date')}`"
                f"{''.join(balance_lines)}",
                parse_mode="Markdown",
            )
        # Use the fallback path when no earlier branch matched.
        else:
            # Send the Telegram response before continuing.
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
            # Await proceed after preview edit before continuing.
            await proceed_after_preview_edit(query, context, scope)
            return

        if action == "field":
            field = parts[3] if len(parts) > 3 else ""
            state = context.user_data.get("pending_preview_edit") or {"scope": scope, "step": "edit_item"}
            state["scope"] = scope
            if scope == "mixed" and "index" not in state:
                mixed_items = context.user_data.get("pending_mixed") or []
                context.user_data["pending_preview_edit"] = {"scope": "mixed", "step": "choose_item"}
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_mixed_edit_choose_prompt(mixed_items),
                    parse_mode="Markdown",
                    reply_markup=cancel_keyboard(),
                )
                return

            state["step"] = "direct_field"
            state["field"] = field
            context.user_data["pending_preview_edit"] = state
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                build_preview_field_value_prompt(scope, field),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")]]),
            )
            context.user_data["pending_preview_edit_prompt_message_id"] = getattr(query.message, "message_id", None)
            return

        if action == "edit":
            if scope == "mixed":
                mixed_items = context.user_data.get("pending_mixed")
                # Validate missing mixed items before continuing.
                if not mixed_items:
                    await safe_edit_message(query, "❌ Sesi mixed input expired. Coba input ulang.")
                    return
                context.user_data["pending_preview_edit"] = {"scope": "mixed", "step": "choose_item"}
                # Send the Telegram response before continuing.
                await safe_edit_message(query,
                    build_mixed_edit_choose_prompt(mixed_items),
                    parse_mode="Markdown",
                    reply_markup=cancel_keyboard(),
                )
                return

            if scope == "debt":
                if not context.user_data.get("pending_debt"):
                    await safe_edit_message(query, "❌ Sesi debt expired. Coba input ulang.")
                    return
                context.user_data["pending_preview_edit"] = {"scope": "debt", "step": "edit_item"}
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_preview_edit_help("debt"),
                    parse_mode="Markdown",
                    reply_markup=build_preview_edit_keyboard("debt"),
                )
                context.user_data["pending_preview_edit_prompt_message_id"] = getattr(query.message, "message_id", None)
                return

            if scope == "pending_expense":
                if not context.user_data.get("pending_expense_confirm"):
                    await safe_edit_message(query, "❌ Sesi pending expense expired. Coba input ulang.")
                    return
                context.user_data["pending_preview_edit"] = {"scope": "pending_expense", "step": "edit_item"}
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_preview_edit_help("pending_expense"),
                    parse_mode="Markdown",
                    reply_markup=build_preview_edit_keyboard("pending_expense"),
                )
                context.user_data["pending_preview_edit_prompt_message_id"] = getattr(query.message, "message_id", None)
                return

            if scope == "asset":
                if not context.user_data.get("pending_asset_confirm"):
                    await safe_edit_message(query, "❌ Sesi tambah aset expired. Coba input ulang.")
                    return
                context.user_data["pending_preview_edit"] = {"scope": "asset", "step": "edit_item"}
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_preview_edit_help("asset"),
                    parse_mode="Markdown",
                    reply_markup=build_preview_edit_keyboard("asset"),
                )
                context.user_data["pending_preview_edit_prompt_message_id"] = getattr(query.message, "message_id", None)
                return

            if not context.user_data.get("pending_parsed"):
                await safe_edit_message(query, "❌ Sesi transaksi expired. Coba input ulang.")
                return
            context.user_data["pending_preview_edit"] = {"scope": "single", "step": "edit_item"}
            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                build_preview_edit_help("single"),
                parse_mode="Markdown",
                reply_markup=build_preview_edit_keyboard("single"),
            )
            context.user_data["pending_preview_edit_prompt_message_id"] = getattr(query.message, "message_id", None)
            return

        await safe_edit_message(query, "❌ Aksi edit tidak valid.")
        return

    if data.startswith("debt_overpay:"):
        policy = data.split(":", 1)[1].strip()
        debt_parsed = context.user_data.get("pending_debt")
        # Validate missing debt parsed before continuing.
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
        # Use the fallback path when no earlier branch matched.
        else:
            preview += "\n\nℹ️ Kelebihan bayar akan dicatat sebagai hutang Anda ke orang tersebut."

        await safe_edit_message(query, f"{preview}\n\n{preview_action_question(True)}", parse_mode="Markdown", reply_markup=preview_action_keyboard("debt", True))
        return

    if data.startswith("debt_settle_acc:"):
        account = data.split(":", 1)[1].strip()
        payload = context.user_data.get("pending_debt_settle")
        # Validate missing payload before continuing.
        if not payload:
            await safe_edit_message(query, "❌ Sesi debt settle expired. Coba ulangi `/hutang Nama` lalu `/debt_settle ...`.", parse_mode="Markdown")
            return
        payload["account"] = account
        context.user_data["pending_debt_settle"] = payload

        # Import app.bot.handler_parts.command_handlers so this module can use its helpers.
        from app.bot.handler_parts.command_handlers import (
            build_selected_debt_settle_preview_text,
            selected_debt_settle_overpay_keyboard,
        )
        if float(payload.get("shortage", 0) or 0) > 0:
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                build_selected_debt_settle_preview_text(payload),
                parse_mode="Markdown",
                reply_markup=cancel_keyboard(),
            )
            return
        if float(payload.get("overpayment", 0) or 0) > 0 and not payload.get("overpayment_policy"):
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                build_selected_debt_settle_preview_text(payload),
                parse_mode="Markdown",
                reply_markup=selected_debt_settle_overpay_keyboard(),
            )
            return
        # Send the Telegram response before continuing.
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
        # Validate missing payload before continuing.
        if not payload:
            await safe_edit_message(query, "❌ Sesi overpaid debt settle expired. Coba input ulang.")
            return
        if policy not in {"bonus", "opposite_debt"}:
            await safe_edit_message(query, "❌ Pilihan overpaid tidak valid. Coba input ulang.")
            return
        payload["overpayment_policy"] = policy
        context.user_data["pending_debt_settle"] = payload
        # Import app.bot.handler_parts.command_handlers so this module can use its helpers.
        from app.bot.handler_parts.command_handlers import build_selected_debt_settle_preview_text
        # Send the Telegram response before continuing.
        await safe_edit_message(
            query,
            build_selected_debt_settle_preview_text(payload),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("debt_settle"),
        )
        return


    if data.startswith("debt_batch_acc:"):
        account = data.split(":")[1]
        # Extract skip account for validation.
        skip_account = is_skip_account_choice(account)
        # Extract account label for validation.
        account_label = SKIP_ACCOUNT_NAME if skip_account else account
        debt_batch = context.user_data.get("pending_debt_batch")

        # Validate missing debt batch before continuing.
        if not debt_batch:
            await safe_edit_message(query, "❌ Sesi batch debt expired. Coba input ulang.")
            return

        prepared_batch = []
        failed_items = []

        # Iterate through each item.
        for item in debt_batch:
            parsed = item["parsed"]
            raw = item["raw"]

            intent = parsed.get("intent")
            person = parsed.get("person_name")

            # Validate missing person before continuing.
            if not person:
                failed_items.append({
                    "raw": raw,
                    "message": "Nama orang tidak terdeteksi.",
                })
                # Skip the rest of this loop iteration after handling this case.
                continue

            if intent == "add_payment":
                # Load debts for the current calculation.
                debts = await run_sheets_read("get_debt_by_person", get_debt_by_person, person)

                # Validate missing debts before continuing.
                if not debts:
                    failed_items.append({
                        "raw": raw,
                        "message": f"Tidak ada utang/piutang aktif dengan {person}.",
                    })
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                debt_type_for_payment, err = resolve_payment_target_type(parsed, debts)
                if err:
                    failed_items.append({
                        "raw": raw,
                        "message": err,
                    })
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                target_debts = [
                    d for d in debts
                    if str(d.get("type", "")).strip() == debt_type_for_payment
                ]
                opposite_type = "payable" if debt_type_for_payment == "receivable" else "receivable"
                has_opposite_debt = any(
                    str(d.get("type", "")).strip() == opposite_type
                    and parse_sheet_number(d.get("remaining_amount", 0)) > 0
                    # Iterate through each d.
                    for d in debts
                )
                parsed["target_debt_id"] = target_debts[0].get("id") if len(target_debts) == 1 and not has_opposite_debt else ""
                parsed["debt_type_for_payment"] = debt_type_for_payment
                parsed["target_debt_type"] = debt_type_for_payment

            if debt_uses_cashflow(parsed) and intent != "offset_debt":
                if skip_account:
                    mark_debt_as_historical(parsed)
                # Use the fallback path when no earlier branch matched.
                else:
                    parsed["account"] = account
            prepared_batch.append({
                "parsed": parsed,
                "raw": raw,
            })

        # Validate missing prepared batch before continuing.
        if not prepared_batch:
            lines = ["❌ *Batch debt tidak bisa diproses.*\n"]

            if failed_items:
                lines.append("*Gagal:*")
                # Iterate through each item.
                for item in failed_items:
                    lines.append(f"• `{item['raw']}` — {item['message']}")

            # Send the Telegram response before continuing.
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
            # Iterate through each item.
            for item in failed_items:
                preview += f"\n• `{item['raw']}` — {item['message']}"

        # Send the Telegram response before continuing.
        await safe_edit_message(query,
            preview,
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("debt_batch"),
        )
        return

    if data.startswith("debt_acc:"):
        account = data.split(":")[1]
        # Extract skip account for validation.
        skip_account = is_skip_account_choice(account)
        # Extract account label for validation.
        account_label = SKIP_ACCOUNT_NAME if skip_account else account
        debt_parsed = context.user_data.get("pending_debt")

        # Validate missing debt parsed before continuing.
        if not debt_parsed:
            await safe_edit_message(query, "❌ Sesi debt expired. Coba input ulang.")
            return

        intent = debt_parsed.get("intent")
        person = debt_parsed.get("person_name")
        debt_type_for_payment = None

        if intent == "add_payment":
            # Load debts for the current calculation.
            debts = await run_sheets_read("get_debt_by_person", get_debt_by_person, person)

            # Validate missing debts before continuing.
            if not debts:
                # Send the Telegram response before continuing.
                await safe_edit_message(query,
                    f"❓ Tidak ada utang/piutang aktif dengan *{person}*.",
                    parse_mode="Markdown",
                )
                context.user_data.pop("pending_debt", None)
                return

            debt_type_for_payment, err = resolve_payment_target_type(debt_parsed, debts)
            if err:
                # Send the Telegram response before continuing.
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
                # Iterate through each d.
                for d in debts
            )
            # Keep target empty when direction is ambiguous or multiple active debts exist.
            debt_parsed["target_debt_id"] = ""
            debt_parsed["debt_type_for_payment"] = debt_type_for_payment
            debt_parsed["target_debt_type"] = debt_type_for_payment

            outcome = estimate_payment_outcome(person, debt_parsed.get("amount", 0), debt_type_for_payment)
            if float(outcome.get("overpayment", 0) or 0) > 0 and not debt_parsed.get("overpayment_policy"):
                if skip_account:
                    mark_debt_as_historical(debt_parsed)
                # Use the fallback path when no earlier branch matched.
                else:
                    debt_parsed["account"] = account
                debt_parsed["overpayment_outcome"] = outcome
                context.user_data["pending_debt"] = debt_parsed
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_overpayment_decision_text(debt_parsed, outcome),
                    parse_mode="Markdown",
                    reply_markup=overpayment_decision_keyboard(),
                )
                return

        if skip_account:
            mark_debt_as_historical(debt_parsed)
        # Use the fallback path when no earlier branch matched.
        else:
            debt_parsed["account"] = account
        context.user_data["pending_debt"] = debt_parsed

        if skip_account:
            # Build preview for the response flow.
            preview = build_debt_only_confirm_preview(debt_parsed)
        # Use the fallback path when no earlier branch matched.
        else:
            preview = build_debt_confirm_preview(
                debt_parsed,
                account_label,
                debt_type_for_payment=debt_type_for_payment,
            )

        # Send the Telegram response before continuing.
        await safe_edit_message(query,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("debt", True),
        )
        return

    if data.startswith("mixed_acc:"):
        account = data.split(":")[1]
        # Extract skip account for validation.
        skip_account = is_skip_account_choice(account)
        # Extract account label for validation.
        account_label = SKIP_ACCOUNT_NAME if skip_account else account
        mixed_items = context.user_data.get("pending_mixed")

        # Validate missing mixed items before continuing.
        if not mixed_items:
            await safe_edit_message(query, "❌ Sesi mixed input expired. Coba input ulang.")
            return

        prepared_items = []
        failed_items = []

        # Iterate through each item.
        for item in mixed_items:
            parsed = item["parsed"]
            raw = item["raw"]

            if item["kind"] == "transaction":
                if needs_account(parsed):
                    if skip_account:
                        mark_transaction_as_historical(parsed)
                    # Use the fallback path when no earlier branch matched.
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

                # Validate missing person before continuing.
                if not person:
                    failed_items.append({
                        "raw": raw,
                        "message": "Nama orang tidak terdeteksi.",
                    })
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                if intent == "add_payment":
                    # Load debts for the current calculation.
                    debts = await run_sheets_read("get_debt_by_person", get_debt_by_person, person)

                    # Validate missing debts before continuing.
                    if not debts:
                        failed_items.append({
                            "raw": raw,
                            "message": f"Tidak ada utang/piutang aktif dengan {person}.",
                        })
                        # Skip the rest of this loop iteration after handling this case.
                        continue

                    debt_type_for_payment, err = resolve_payment_target_type(parsed, debts)
                    if err:
                        failed_items.append({
                            "raw": raw,
                            "message": err,
                        })
                        # Skip the rest of this loop iteration after handling this case.
                        continue

                    target_debts = [
                        d for d in debts
                        if str(d.get("type", "")).strip() == debt_type_for_payment
                    ]
                    opposite_type = "payable" if debt_type_for_payment == "receivable" else "receivable"
                    has_opposite_debt = any(
                        str(d.get("type", "")).strip() == opposite_type
                        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
                        # Iterate through each d.
                        for d in debts
                    )
                    parsed["target_debt_id"] = target_debts[0].get("id") if len(target_debts) == 1 and not has_opposite_debt else ""
                    parsed["debt_type_for_payment"] = debt_type_for_payment
                    parsed["target_debt_type"] = debt_type_for_payment

                if debt_uses_cashflow(parsed) and intent != "offset_debt":
                    if skip_account:
                        mark_debt_as_historical(parsed)
                    # Use the fallback path when no earlier branch matched.
                    else:
                        parsed["account"] = account

                prepared_items.append({
                    "kind": "debt",
                    "parsed": parsed,
                    "raw": raw,
                })

        # Validate missing prepared items before continuing.
        if not prepared_items:
            lines = ["❌ *Mixed input tidak bisa diproses.*\n"]

            if failed_items:
                lines.append("*Gagal:*")
                # Iterate through each item.
                for item in failed_items:
                    lines.append(f"• `{item['raw']}` — {item['message']}")

            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                "\n".join(lines),
                parse_mode="Markdown",
            )
            context.user_data.pop("pending_mixed", None)
            return

        context.user_data["pending_mixed"] = prepared_items

        if mixed_split_bill_needs_decision(prepared_items):
            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                build_mixed_split_bill_queue_prompt(prepared_items),
                parse_mode="Markdown",
                reply_markup=mixed_split_bill_keyboard(prepared_items),
            )
            return

        receipt_context = context.user_data.get("pending_receipt_context")
        # Build final summary for the response flow.
        final_summary = build_mixed_final_summary(prepared_items, receipt_context, account_label=account_label)

        if failed_items:
            final_summary += "\n\n⚠️ *Catatan item yang tidak masuk:*"
            # Iterate through each item.
            for item in failed_items[:5]:
                final_summary += f"\n• `{md_safe(item['raw'])}` — {md_safe(item['message'])}"
            if len(failed_items) > 5:
                final_summary += f"\n• ...dan {len(failed_items) - 5} item lain."

        # Send the Telegram response before continuing.
        await safe_edit_message(query,
            f"✅ Pilihan rekening: *{md_safe(account_label)}*.\n\n{final_summary}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("mixed", True),
        )
        return

    if data.startswith("batch_acc:"):
        account = data.split(":")[1]
        # Extract skip account for validation.
        skip_account = is_skip_account_choice(account)
        batch = context.user_data.get("pending_batch")

        # Validate missing batch before continuing.
        if not batch:
            await safe_edit_message(query, "❌ Sesi batch expired. Coba input ulang.")
            return

        # Iterate through each item.
        for item in batch:
            parsed = item["parsed"]
            if needs_account(parsed):
                if skip_account:
                    mark_transaction_as_historical(parsed)
                # Use the fallback path when no earlier branch matched.
                else:
                    parsed["account"] = account

        context.user_data["pending_batch"] = batch
        # Build preview for the response flow.
        preview = build_batch_preview(batch)

        if any(split_bill_needs_decision(item.get("parsed", {})) for item in batch):
            mixed_like = [{"kind": "transaction", "parsed": item["parsed"], "raw": item.get("raw", "")} for item in batch]
            context.user_data["pending_mixed"] = mixed_like
            context.user_data.pop("pending_batch", None)
            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                build_mixed_split_bill_queue_prompt(mixed_like),
                parse_mode="Markdown",
                reply_markup=mixed_split_bill_keyboard(mixed_like),
            )
            return

        # Send the Telegram response before continuing.
        await safe_edit_message(query,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("batch", True),
        )
        return

    if data.startswith("acc:"):
        account = data.split(":")[1]
        # Extract skip account for validation.
        skip_account = is_skip_account_choice(account)
        # Extract account label for validation.
        account_label = SKIP_ACCOUNT_NAME if skip_account else account
        parsed = context.user_data.get("pending_parsed")

        # Validate missing parsed before continuing.
        if not parsed:
            await safe_edit_message(query, "❌ Sesi expired. Coba input ulang.")
            return

        if skip_account:
            mark_transaction_as_historical(parsed)
        # Use the fallback path when no earlier branch matched.
        else:
            parsed["account"] = account
        context.user_data["pending_parsed"] = parsed

        if split_bill_needs_decision(parsed):
            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                build_split_bill_prompt_from_parsed(parsed),
                parse_mode="Markdown",
                reply_markup=split_bill_keyboard("single"),
            )
            return

        # Build short summary for the response flow.
        short_summary = build_single_short_summary(parsed)
        if str(parsed.get("parsed_by") or "").strip() == "meal_split":
            preview = build_meal_split_final_summary(parsed, "transaction")
        elif parsed.get("split_bill"):
            # Keep single split bill final confirmation compact after rekening selection.
            preview = build_single_split_bill_final_summary(parsed, account_label=account_label)
        # Use the fallback path when no earlier branch matched.
        else:
            # Build preview for the response flow.
            preview = build_preview(parsed)
        # Send the Telegram response before continuing.
        await safe_edit_message(query,
            f"✅ Pilihan rekening: *{md_safe(account_label)}*.\n\n{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("single", True),
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
            # Validate missing mixed items before continuing.
            if not mixed_items:
                await safe_edit_message(query, "❌ Sesi split bill expired. Coba input ulang.")
                return

            # Guard against stale split callbacks so an old button cannot overwrite the final preview.
            expected_index = None
            if len(parts) > 3:
                # Run this operation in a guarded block so failures can be handled.
                try:
                    expected_index = int(parts[3])
                # Handle an expected failure from the guarded operation above.
                except Exception:
                    expected_index = None

            if expected_index is not None:
                mixed_items, decided_index, decision_result = apply_split_bill_decision_to_mixed_index(
                    mixed_items,
                    expected_index,
                    status,
                )
            # Use the fallback path when no earlier branch matched.
            else:
                mixed_items, decided_index = apply_split_bill_decision_to_current_mixed(mixed_items, status)
                decision_result = "applied" if decided_index is not None else "invalid"

            context.user_data["pending_mixed"] = mixed_items

            if decision_result == "invalid" and not mixed_split_bill_needs_decision(mixed_items):
                # The split state is already complete, so the stale callback can be ignored safely.
                pass
            elif decision_result == "invalid":
                # Send the Telegram response before continuing.
                await safe_edit_message(query,
                    build_mixed_split_bill_queue_prompt(mixed_items),
                    parse_mode="Markdown",
                    reply_markup=mixed_split_bill_keyboard(mixed_items),
                )
                return

            if mixed_split_bill_needs_decision(mixed_items):
                # Send the Telegram response before continuing.
                await safe_edit_message(query,
                    build_mixed_split_bill_queue_prompt(mixed_items),
                    parse_mode="Markdown",
                    reply_markup=mixed_split_bill_keyboard(mixed_items),
                )
                return

            # Build preview for the response flow.
            preview = build_mixed_detail_preview(mixed_items)
            context.user_data["mixed_review_preview_sent"] = True

            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                f"✅ Split bill sudah diproses.\n\n{preview}\n\n{preview_action_question(False)}",
                parse_mode="Markdown",
                reply_markup=preview_action_keyboard("mixed", False),
            )
            return

        if scope == "edit_txn":
            pending_edit = context.user_data.get("pending_edit_txn") or {}
            split_parsed = pending_edit.get("split_parsed") or {}
            # Validate missing pending edit or not split parsed before continuing.
            if not pending_edit or not split_parsed:
                await safe_edit_message(query, "❌ Sesi edit split bill expired. Coba ulangi `/edit_txn`.")
                return

            apply_split_bill_decision_to_parsed(split_parsed, status)
            updates = dict(pending_edit.get("updates", {}) or {})
            updates["amount"] = split_parsed.get("amount")

            preview = await run_sheets_read(
                "preview_edit_transaction_by_ref",
                preview_edit_transaction_by_ref,
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

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                build_edit_txn_preview_text_for_callback(preview, split_parsed),
                parse_mode="Markdown",
                reply_markup=confirm_keyboard("edit_txn"),
            )
            return

        parsed = context.user_data.get("pending_parsed")
        # Validate missing parsed before continuing.
        if not parsed:
            await safe_edit_message(query, "❌ Sesi split bill expired. Coba input ulang.")
            return

        if parsed.get("split_bill"):
            apply_split_bill_decision_to_parsed(parsed, status)
        context.user_data["pending_parsed"] = parsed
        # Build preview for the response flow.
        preview = build_preview(parsed)

        if needs_account(parsed):
            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                f"{preview}\n\n{preview_action_question(False)}",
                parse_mode="Markdown",
                reply_markup=preview_action_keyboard("single", False),
            )
            return

        # Send the Telegram response before continuing.
        await safe_edit_message(query,
            f"{preview}\n\n{preview_action_question(True)}",
            parse_mode="Markdown",
            reply_markup=preview_action_keyboard("single", True),
        )
        return

    if data.startswith("confirm:"):
        confirm_target = data.split(":")[1] if ":" in data else ""
        confirmed_action = None
        if confirm_target.startswith("a_"):
            from app.bot.pending_actions import PendingActionError, consume_pending_action, restore_pending_state

            try:
                confirmed_action = consume_pending_action(
                    context.user_data,
                    confirm_target,
                    owner_user_id=int(getattr(query.from_user, "id", 0) or 0),
                    message_id=getattr(query.message, "message_id", None),
                )
            except PendingActionError:
                await safe_edit_message(
                    query,
                    "❌ Preview ini sudah kedaluwarsa, sudah dipakai, atau tidak cocok dengan pesan ini. Buat preview baru; tidak ada data yang diubah.",
                )
                return

            action_payload = confirmed_action.get("payload") or {}
            if confirmed_action.get("flow_type") == "command_mutation":
                from app.bot.command_mutations import execute_command_mutation

                mutation_result = execute_command_mutation(
                    str(action_payload.get("operation") or ""),
                    dict(action_payload.get("arguments") or {}),
                )
                await safe_edit_message(
                    query,
                    mutation_result.get("display_text") or "❌ Mutasi gagal tanpa detail.",
                    parse_mode="Markdown",
                )
                return

            restore_pending_state(context.user_data, action_payload.get("user_state") or {})
            confirm_target = str(action_payload.get("legacy_target") or "").strip()
            if not confirm_target:
                await safe_edit_message(query, "❌ Jenis preview tidak valid. Tidak ada data yang diubah.")
                return
        else:
            await safe_edit_message(
                query,
                "❌ Tombol konfirmasi lama sudah tidak berlaku. Buat preview baru agar perubahan terikat ke data yang ditampilkan.",
            )
            return
        # Category add/edit writes to Sheets only after this preview confirmation.
        if confirm_target in {"category_add", "category_edit"}:
            handled = await handle_category_confirm_callback(query, context, confirm_target)
            if handled:
                return

        if confirm_target == "set_balance":
            pending_balance = context.user_data.get("pending_set_balance") or {}

            # Validate missing pending balance before continuing.
            if not pending_balance:
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    "❌ Sesi set saldo expired. Jalankan `/set_saldo` lagi.",
                    parse_mode="Markdown",
                )
                return

            account_name = str(pending_balance.get("account_name") or "").strip()
            new_balance = float(pending_balance.get("new_balance", 0) or 0)
            old_balance = float(pending_balance.get("current_balance", 0) or 0)
            delta = new_balance - old_balance
            sign = "+" if delta >= 0 else "-"

            create_missing = bool(pending_balance.get("create_missing"))

            # Run this operation in a guarded block so failures can be handled.
            try:
                if create_missing:
                    create_result = create_account(
                        account_name,
                        initial_balance=new_balance,
                        account_type=str(pending_balance.get("account_type") or "bank"),
                    )
                    success = bool(create_result.get("success"))
                    # Validate missing success before continuing.
                    if not success:
                        raise RuntimeError(create_result.get("message") or "Gagal membuat rekening baru.")
                # Use the fallback path when no earlier branch matched.
                else:
                    success = update_account_balance(account_name, new_balance)
            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    f"❌ *Gagal set saldo.*\n{md_safe(str(e))}",
                    parse_mode="Markdown",
                )
                return

            # Validate missing success before continuing.
            if not success:
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    f"❌ Rekening `{md_code_text(account_name)}` tidak ditemukan di sheet `accounts`.",
                    parse_mode="Markdown",
                )
                context.user_data.pop("pending_set_balance", None)
                return

            context.user_data.pop("pending_set_balance", None)
            context.user_data.pop("pending_set_balance_suggestion", None)

            success_title = "✅ *Rekening baru berhasil dibuat dan saldo diset!*" if create_missing else "✅ *Saldo rekening berhasil diupdate!*"

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                f"{success_title}\n\n"
                f"🏦 Rekening: *{md_safe(account_name)}*\n"
                f"💰 {'Saldo awal' if create_missing else 'Saldo lama'}: *{format_rupiah(old_balance)}*\n"
                f"🎯 Saldo baru: *{format_rupiah(new_balance)}*\n"
                f"🔁 Selisih: *{sign}{format_rupiah(abs(delta))}*\n\n"
                "Catatan: ini hanya mengubah saldo di sheet `accounts`, tidak membuat row transaksi baru.",
                parse_mode="Markdown",
            )
            return

        if confirm_target == "budget":
            pending_budget = context.user_data.get("pending_budget_confirm") or {}

            # Validate missing pending budget before continuing.
            if not pending_budget:
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    "❌ Sesi set budget expired. Jalankan `/set_budget` lagi.",
                    parse_mode="Markdown",
                )
                return

            category = str(pending_budget.get("category") or "").strip()
            amount = float(pending_budget.get("amount", 0) or 0)
            month = str(pending_budget.get("month") or normalize_month(None)).strip()
            source_note = str(pending_budget.get("source_note") or "budget").strip()

            # Build result for the response flow.
            result = set_budget(category, amount, month=month)
            if not result.get("success"):
                await safe_edit_message(query, f"❌ {md_safe(result.get('message') or 'Gagal menyimpan budget.')}", parse_mode="Markdown")
                return

            action_label = "diset" if result.get("action") == "created" else "diupdate"
            context.user_data.pop("pending_budget_confirm", None)

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                f"✅ Budget *{md_safe(category)}* {md_safe(action_label)}!\n"
                f"📅 Bulan: *{format_month_label(month)}*\n"
                f"💰 {format_rupiah(amount)} / bulan\n"
                f"🏷️ Tipe: {md_safe(source_note)}\n\n"
                f"Cek dengan:\n"
                f"`/budget {md_code_text(month)}`",
                parse_mode="Markdown",
            )
            return

        if confirm_target == "recurring":
            pending_recurring = context.user_data.get("pending_recurring_confirm") or {}

            # Validate missing pending recurring before continuing.
            if not pending_recurring:
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    "❌ Sesi recurring transaction expired. Jalankan `/recurring_add` lagi.",
                    parse_mode="Markdown",
                )
                return

            # Run this operation in a guarded block so failures can be handled.
            try:
                rule = save_pending_recurring_rule(pending_recurring)
            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                await safe_edit_message(query, f"❌ Gagal menyimpan recurring transaction: {md_safe(str(e))}", parse_mode="Markdown")
                return

            context.user_data.pop("pending_recurring_confirm", None)
            context.user_data.pop("pending_recurring_add_flow", None)
            context.user_data.pop("pending_recurring_add_prompt_message_id", None)

            await safe_edit_message(query, build_recurring_saved_text(rule), parse_mode="Markdown")
            return

        if confirm_target == "asset":
            pending_asset = context.user_data.get("pending_asset_confirm")

            # Validate missing pending asset before continuing.
            if not pending_asset:
                await safe_edit_message(query, "❌ Sesi tambah aset expired. Coba input ulang.")
                return

            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                "⏳ *Sedang menyimpan aset...*",
                parse_mode="Markdown",
            )

            # Run this operation in a guarded block so failures can be handled.
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
            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                await safe_edit_message(query, f"❌ Gagal menyimpan aset: {str(e)}")
                context.user_data.pop("pending_asset_confirm", None)
                return

            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                build_asset_added_text(asset),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_asset_confirm", None)
            context.user_data.pop("pending_asset_price", None)
            return

        if confirm_target == "pending_expense":
            item = context.user_data.get("pending_expense_confirm")

            # Validate missing item before continuing.
            if not item:
                await safe_edit_message(query, "❌ Sesi pending expense expired. Coba input ulang.")
                return

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                "⏳ *Sedang menyimpan pending expense...*",
                parse_mode="Markdown",
            )

            # Run this operation in a guarded block so failures can be handled.
            try:
                saved_item = save_pending_expense(item)
            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                # Send the Telegram response before continuing.
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
                # Prepare due text from the incoming input.
                due_text = due_date
            elif due_precision == "month":
                due_text = f"{month} (tanggal belum pasti)"
            # Use the fallback path when no earlier branch matched.
            else:
                due_text = "Belum pasti"

            account = str(saved_item.get("account") or "-").strip() or "-"
            category = str(saved_item.get("category") or "Other Expense").strip()
            amount = float(saved_item.get("amount", 0) or 0)
            pending_id = str(saved_item.get("id") or "").strip()

            # Send the Telegram response before continuing.
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

            # Validate missing entries before continuing.
            if not entries:
                await safe_edit_message(query, "❌ Sesi bulk edit transaksi expired. Coba ulangi dari daftar transaksi terakhir.")
                return

            # Send the Telegram response before continuing.
            await safe_edit_message(
                query,
                "⏳ *Sedang mengedit beberapa transaksi...*",
                parse_mode="Markdown",
            )

            # Build success results for the response flow.
            success_results = []
            # Build failed results for the response flow.
            failed_results = []
            aggregate_deltas = {}
            latest_balances = {}
            synced_debt_count = 0
            overpaid_count = 0

            # Iterate through each entry.
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
                # Use the fallback path when no earlier branch matched.
                else:
                    failed_results.append({"entry": entry, "result": result})

            lines = [
                "✅ *Bulk edit transaksi selesai!*" if not failed_results else "⚠️ *Bulk edit transaksi selesai sebagian.*",
                f"Berhasil: *{len(success_results)}* / *{len(entries)}* transaksi",
            ]

            if success_results:
                lines.append("\n*Berhasil diedit:*")
                # Iterate through each item.
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
                # Iterate through each item.
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
                # Iterate through each account, delta.
                for account, delta in aggregate_deltas.items():
                    sign = "+" if delta >= 0 else "-"
                    lines.append(f"• {md_safe(account)}: {sign}{format_rupiah(abs(delta))}")

            if latest_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                # Iterate through each account, balance.
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

            # Validate missing pending edit before continuing.
            if not pending_edit:
                # Send the Telegram response before continuing.
                await safe_edit_message(query,
                    "❌ Sesi edit transaksi expired. Coba ulangi `/last`."
                )
                return

            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                "⏳ *Sedang mengedit transaksi dan memperbaiki saldo...*",
                parse_mode="Markdown",
            )

            split_parsed = pending_edit.get("split_parsed") or None
            split_status = (split_parsed or {}).get("split_bill", {}).get("status") if split_parsed else None
            target_txn_id = str(pending_edit.get("txn_id") or "").strip()

            if split_parsed:
                preview_before_edit = await run_sheets_read(
                    "preview_edit_transaction_by_ref",
                    preview_edit_transaction_by_ref,
                    updates=pending_edit.get("updates", {}),
                    row_index=pending_edit.get("row_index"),
                    txn_id=pending_edit.get("txn_id"),
                )
                old_txn_for_debt = preview_before_edit.get("old_txn", {}) if preview_before_edit.get("success") else {}
                target_txn_id = target_txn_id or str(old_txn_for_debt.get("id") or "").strip()
                linked_ids = parse_debt_ids_from_txn_record_for_edit(old_txn_for_debt)
                void_result = void_debts_for_transaction(target_txn_id, linked_ids) if target_txn_id else {"success": True}
                if not void_result.get("success"):
                    # Send the Telegram response before continuing.
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
                # Send the Telegram response before continuing.
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
                # Iterate through each account, delta.
                for account, delta in net_deltas.items():
                    sign = "+" if delta >= 0 else "-"
                    lines.append(f"• {account}: {sign}{format_rupiah(abs(delta))}")

            if new_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                # Iterate through each account, balance.
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
                        relation_result = update_transaction_debt_relation(target_txn_id, debt_ids, tipe_hutang=tipe_hutang)
                        if not relation_result.get("success"):
                            raise PartialMutationError(
                                relation_result.get("message", "Gagal menghubungkan transaksi dengan debt payment."),
                                operation="edit_transaction_payment_relation",
                            )

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
                        # Iterate through each alloc.
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
                # Use the fallback path when no earlier branch matched.
                else:
                    raise PartialMutationError(
                        payment_result.get("message", "Pembayaran debt gagal setelah transaksi diedit."),
                        operation="edit_transaction_payment_conversion",
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
                            relation_result = update_transaction_debt_relation(target_txn_id, debt_ids, tipe_hutang="piutang")
                            if not relation_result.get("success"):
                                raise PartialMutationError(
                                    relation_result.get("message", "Gagal menghubungkan split bill dengan transaksi."),
                                    operation="edit_transaction_split_relation",
                                )
                        lines.append("\n🤝 *Piutang split bill baru dibuat:*")
                        # Append the current value to lines.
                        lines.extend(format_split_debt_result_lines(split_debt))
                    # Fall back when split debt.
                    elif split_debt:
                        raise PartialMutationError(
                            split_debt.get("message", "Gagal membuat piutang split bill baru."),
                            operation="edit_transaction_split_debt",
                        )
                elif split_status == "paid":
                    clear_result = clear_transaction_debt_relation(target_txn_id)
                    if not clear_result.get("success"):
                        raise PartialMutationError(
                            clear_result.get("message", "Gagal menghapus relasi split bill."),
                            operation="edit_transaction_clear_split_relation",
                        )
                    lines.append("\n🤝 Split bill ditandai sudah dibayar, jadi tidak ada piutang aktif baru.")

            # Send the Telegram response before continuing.
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

            # Validate missing row indices and not txn ids before continuing.
            if not row_indices and not txn_ids:
                # Send the Telegram response before continuing.
                await safe_edit_message(query,
                    "❌ Sesi hapus transaksi expired. Coba ulangi `/last`."
                )
                return

            # Send the Telegram response before continuing.
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

                # Send the Telegram response before continuing.
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
                # Iterate through each txn id.
                for txn_id in deleted_ids:
                    lines.append(f"• `{short_txn_id(txn_id)}`")

            new_balances = result.get("new_balances", {})
            if new_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                # Iterate through each account, balance.
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

            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                "\n".join(lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_delete_refs", None)
            context.user_data.pop("pending_delete_txn_ids", None)
            return

        if confirm_target == "debt_settle":
            payload = context.user_data.get("pending_debt_settle")
            # Validate missing payload before continuing.
            if not payload:
                await safe_edit_message(query, "❌ Sesi debt settle expired. Coba ulangi `/hutang Nama` lalu `/debt_settle ...`.", parse_mode="Markdown")
                return

            if float(payload.get("shortage", 0) or 0) > 0:
                # Import app.bot.handler_parts.command_handlers so this module can use its helpers.
                from app.bot.handler_parts.command_handlers import build_selected_debt_settle_preview_text
                # Send the Telegram response before continuing.
                await safe_edit_message(
                    query,
                    build_selected_debt_settle_preview_text(payload),
                    parse_mode="Markdown",
                    reply_markup=cancel_keyboard(),
                )
                return

            if float(payload.get("overpayment", 0) or 0) > 0 and not payload.get("overpayment_policy"):
                # Import app.bot.handler_parts.command_handlers so this module can use its helpers.
                from app.bot.handler_parts.command_handlers import (
                    build_selected_debt_settle_preview_text,
                    selected_debt_settle_overpay_keyboard,
                )
                # Send the Telegram response before continuing.
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

            txn = None
            if float(payload.get("amount", 0) or 0) > 0:
                # Import app.bot.handler_parts.command_handlers so this module can use its helpers.
                from app.bot.handler_parts.command_handlers import build_selected_debt_settle_transaction
                txn = build_selected_debt_settle_transaction(payload, result)
                txn_result = save_transaction(txn, raw_input=payload.get("raw") or f"/debt_settle {payload.get('person_name')} {payload.get('selection')}")
            # Use the fallback path when no earlier branch matched.
            else:
                # Net impas settlement has no account movement, so no zero-amount transaction is saved.
                txn_result = {
                    "success": True,
                    "transaction_id": None,
                    "new_balance": None,
                    "new_balance_account": None,
                    "skip_cashflow": True,
                }

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
                # Use the fallback path when no earlier branch matched.
                else:
                    lines.append(f"ℹ️ Kelebihan *{format_rupiah(overpayment)}* dianggap lunas/bonus.")

            lines.append("\n*Posisi akhir hutang-piutang:*")
            # Iterate through each line.
            for line in format_debt_net_position_lines(
                payload.get("person_name") or "-",
                result.get("remaining_payable", 0),
                result.get("remaining_receivable", 0),
            ):
                # Append the current value to lines.
                lines.append(md_safe(line))

            if txn_result.get("success"):
                if txn_result.get("skip_cashflow"):
                    lines.append("\n📝 Net impas, jadi tidak ada transaksi cashflow.")
                # Use the fallback path when no earlier branch matched.
                else:
                    lines.append("\n📝 Cashflow tersimpan di transactions.")
                if txn_result.get("transaction_id"):
                    lines.append(f"🔖 ID: `{txn_result.get('transaction_id')}`")
                if txn_result.get("new_balance") is not None:
                    balance_account = txn_result.get("new_balance_account") or payload.get("account") or payload.get("to_account") or "-"
                    lines.append(f"💳 Saldo {md_safe(balance_account)}: *{format_rupiah(txn_result.get('new_balance'))}*")
            # Use the fallback path when no earlier branch matched.
            else:
                # Run this operation in a guarded block so failures can be handled.
                try:
                    # Import app.services.debt_service so this module can use its helpers.
                    from app.services.debt_service import reverse_debt_payment_transaction
                    # Build reverse result for the response flow.
                    reverse_result = reverse_debt_payment_transaction(txn)
                # Handle an expected failure from the guarded operation above.
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

            # Validate missing pending void before continuing.
            if not pending_void:
                await safe_edit_message(query, "❌ Sesi debt void expired. Coba ulangi `/hutang Nama` lalu `/debt_void 1` atau `/debt_void Nama`.")
                return

            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                "⏳ *Sedang membatalkan debt dan memperbaiki saldo...*",
                parse_mode="Markdown",
            )

            if pending_void.get("mode") == "bulk":
                result = void_debt_ids(pending_void.get("target_debt_ids") or [])
            # Use the fallback path when no earlier branch matched.
            else:
                debt_ref = pending_void.get("debt_ref")
                last_debt_map = context.user_data.get("last_debt_map", {})
                # Build result for the response flow.
                result = void_debt(debt_ref, last_debt_map)

            if not result.get("success"):
                lines = [f"❌ *Gagal void debt.*\n{md_safe(result.get('message'))}"]
                success_results = result.get("success_results") or []
                if success_results:
                    lines.append("\n⚠️ Sebagian debt sudah terlanjur berhasil di-void:")
                    # Iterate through each r.
                    for r in success_results:
                        debt = r.get("debt") or {}
                        lines.append(f"• `{md_safe(short_debt_id(debt.get('id', '-')))}` — {md_safe(debt.get('description') or '-')}")
                # Send the Telegram response before continuing.
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
                # Iterate through each i, debt.
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
                    # Iterate through each txn.
                    for txn in cashflow_txns[:10]:
                        lines.append(
                            f"• Row {txn.get('_row_index', '-')} — {md_safe(txn.get('description') or '-')} — "
                            f"{format_rupiah(float(txn.get('amount', 0) or 0))}"
                        )
                    if len(cashflow_txns) > 10:
                        lines.append(f"• ...dan {len(cashflow_txns) - 10} cashflow lain")
            # Use the fallback path when no earlier branch matched.
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
                # Iterate through each account, delta.
                for account, delta in reverse_deltas.items():
                    sign = "+" if delta >= 0 else "-"
                    lines.append(f"• {md_safe(account)}: {sign}{format_rupiah(abs(delta))}")

            if new_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                # Iterate through each account, balance.
                for account, balance in new_balances.items():
                    lines.append(f"• {md_safe(account)}: *{format_rupiah(balance)}*")

            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                "\n".join(lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_debt_void", None)
            return

        if confirm_target == "debt":
            debt_parsed = context.user_data.get("pending_debt")

            # Validate missing debt parsed before continuing.
            if not debt_parsed:
                await safe_edit_message(query, "❌ Sesi debt expired. Coba input ulang.")
                return

            # Send the Telegram response before continuing.
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

            # Validate missing person before continuing.
            if not person:
                await safe_edit_message(query, "❌ Nama orang tidak terdeteksi. Coba input ulang.")
                context.user_data.pop("pending_debt", None)
                return

            # Build debt result for the response flow.
            debt_result = None

            if intent == "add_payable":
                # Preserve debt-only metadata so later void/edit logic knows no
                # account balance was changed for this debt.
                debt_result = add_debt(
                    "payable",
                    person,
                    amount,
                    description,
                    cashflow_mode=debt_parsed.get("cashflow_mode", ""),
                    fronting_mode=debt_parsed.get("fronting_mode", ""),
                )

            elif intent == "add_receivable":
                # Preserve debt-only metadata for receivable facts created
                # without immediate account movement.
                debt_result = add_debt(
                    "receivable",
                    person,
                    amount,
                    description,
                    cashflow_mode=debt_parsed.get("cashflow_mode", ""),
                    fronting_mode=debt_parsed.get("fronting_mode", ""),
                )

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

            # Use the fallback path when no earlier branch matched.
            else:
                await safe_edit_message(query, "❌ Intent debt tidak valid. Coba input ulang.")
                context.user_data.pop("pending_debt", None)
                return

            if not debt_result or not debt_result.get("success"):
                if (
                    intent == "add_payment"
                    and debt_result
                    and float(debt_result.get("overpayment", 0) or 0) > 0
                    and not debt_parsed.get("overpayment_policy")
                ):
                    debt_parsed["overpayment_outcome"] = debt_result
                    debt_parsed["debt_type_for_payment"] = debt_result.get("type") or debt_type_for_payment or debt_parsed.get("target_debt_type")
                    debt_parsed["target_debt_type"] = debt_parsed["debt_type_for_payment"]
                    context.user_data["pending_debt"] = debt_parsed
                    # Send the Telegram response before continuing.
                    await safe_edit_message(
                        query,
                        build_overpayment_decision_text(debt_parsed, debt_result),
                        parse_mode="Markdown",
                        reply_markup=overpayment_decision_keyboard(),
                    )
                    return

                message = debt_result.get("message") if debt_result else "Unknown error"
                await safe_edit_message(query, f"❌ Gagal menyimpan debt: {md_safe(message)}", parse_mode="Markdown")
                context.user_data.pop("pending_debt", None)
                return

            # Build fronted split result for the response flow.
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
                # Use the fallback path when no earlier branch matched.
                else:
                    debt_parsed["tipe_hutang"] = "utang" if debt_result.get("type") == "payable" else "piutang"

            debt_txn = build_debt_cashflow_transaction(
                debt_parsed,
                account,
                debt_type_for_payment=debt_type_for_payment,
            )
            # Build transaction result for the response flow.
            transaction_result = None
            if debt_txn.get("type") != "pending":
                # Build transaction result for the response flow.
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
                # Use the fallback path when no earlier branch matched.
                else:
                    direction = "🔴 Utang Anda" if debt_result.get("type") == "payable" else "🟢 Piutang Anda"
                    remaining_amount = float(debt_result.get("remaining", 0) or 0)
                    fronted_receivable_total = sum(
                        float(x.get("amount", 0) or 0)
                        for x in (fronted_split_result or {}).get("created", []) or []
                    )
                    lines.append(f"{direction} dengan *{md_safe(debt_result.get('person_name', person))}*")
                    if fronted_receivable_total > 0 and debt_result.get("type") == "payable":
                        # Extract net amount for validation.
                        net_amount = remaining_amount - fronted_receivable_total
                        lines.append(
                            f"💰 Net: *{format_rupiah(net_amount)}* "
                            f"(utang {format_rupiah(remaining_amount)} - piutang PTPT {format_rupiah(fronted_receivable_total)})"
                        )
                    # Use the fallback path when no earlier branch matched.
                    else:
                        lines.append(f"💰 Net: *{format_rupiah(remaining_amount)}*")
                append_fronted_split_result_lines(lines, fronted_split_result)

            elif intent == "add_payment":
                target_label = "utang Anda" if debt_type_for_payment == "payable" else "piutang Anda"
                lines.append(f"📌 Pembayaran mengurangi *{md_safe(target_label)}* dengan *{md_safe(person)}*")
                lines.append(f"📊 Sisa arah ini: *{format_rupiah(debt_result.get('remaining', 0))}*")

                remaining_payable = float(debt_result.get("remaining_payable", 0) or 0)
                remaining_receivable = float(debt_result.get("remaining_receivable", 0) or 0)
                lines.append("\n*Posisi akhir hutang-piutang:*")
                # Iterate through each line.
                for line in format_debt_net_position_lines(person, remaining_payable, remaining_receivable):
                    # Append the current value to lines.
                    lines.append(md_safe(line))

                overpayment = float(debt_result.get("overpayment", 0) or 0)
                if overpayment > 0:
                    if debt_result.get("overpayment_created"):
                        lines.append(f"\n⚠️ Kelebihan bayar *{format_rupiah(overpayment)}* dicatat sebagai debt lawan arah.")
                    # Use the fallback path when no earlier branch matched.
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
                    account_deltas = transaction_result.get("account_deltas") or {}
                    new_balances = transaction_result.get("new_balances") or {}
                    if account_deltas:
                        lines.append("💳 Ringkasan per rekening:")
                        # Iterate through each balance account, delta.
                        for balance_account, delta in account_deltas.items():
                            sign = "+" if float(delta or 0) >= 0 else "-"
                            if balance_account in new_balances:
                                lines.append(
                                    f"• {md_safe(balance_account)}: {sign}{format_rupiah(abs(float(delta or 0)))} → saldo {format_rupiah(new_balances[balance_account])}"
                                )
                            # Use the fallback path when no earlier branch matched.
                            else:
                                lines.append(
                                    f"• {md_safe(balance_account)}: {sign}{format_rupiah(abs(float(delta or 0)))}"
                                )
                    elif transaction_result.get("new_balance") is not None:
                        balance_account = transaction_result.get("new_balance_account") or account or debt_parsed.get("to_account") or "-"
                        lines.append(f"💳 {md_safe(balance_account)}: saldo {format_rupiah(transaction_result['new_balance'])}")
                # Use the fallback path when no earlier branch matched.
                else:
                    raise PartialMutationError(
                        f"Cashflow debt gagal setelah debt ditulis: {transaction_result.get('message')}",
                        operation="debt_with_cashflow",
                    )
            # Fall back when not debt uses cashflow(debt parsed).
            elif not debt_uses_cashflow(debt_parsed):
                lines.append("\n📝 Cashflow tidak dicatat karena ini mode talangan/ditalangin tanpa uang masuk/keluar dari rekening Anda.")

            # Send the Telegram response before continuing.
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

            # Validate missing debt batch before continuing.
            if not debt_batch:
                await safe_edit_message(query, "❌ Sesi batch debt expired. Coba input ulang.")
                return

            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                "⏳ *Sedang menyimpan batch debt dan cashflow...*",
                parse_mode="Markdown",
            )

            debt_transaction_items = []
            failed_items = []
            result_lines = ["✅ *Batch debt diproses!*\n"]
            debt_success_count = 0

            # Iterate through each i, item.
            for i, item in enumerate(debt_batch, 1):
                parsed = item["parsed"]
                raw = item["raw"]

                intent = parsed.get("intent")
                person = parsed.get("person_name")
                amount = parsed.get("amount")
                description = parsed.get("description") or ""
                account = parsed.get("account")
                debt_type_for_payment = parsed.get("debt_type_for_payment")

                # Validate missing person before continuing.
                if not person:
                    failed_items.append({"raw": raw, "message": "Nama orang tidak terdeteksi."})
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                # Build debt result for the response flow.
                debt_result = None

                if intent == "add_payable":
                    # Batch debt-only items must keep the same metadata as the
                    # single-input save path.
                    debt_result = add_debt(
                        "payable",
                        person,
                        amount,
                        description,
                        cashflow_mode=parsed.get("cashflow_mode", ""),
                        fronting_mode=parsed.get("fronting_mode", ""),
                    )
                elif intent == "add_receivable":
                    # Batch receivable facts also carry the original no-balance
                    # marker when the parser set one.
                    debt_result = add_debt(
                        "receivable",
                        person,
                        amount,
                        description,
                        cashflow_mode=parsed.get("cashflow_mode", ""),
                        fronting_mode=parsed.get("fronting_mode", ""),
                    )
                elif intent == "add_payment":
                    target_debt_id = parsed.get("target_debt_id")
                    if target_debt_id:
                        # Build debt result for the response flow.
                        debt_result = add_payment(target_debt_id, amount)
                    # Use the fallback path when no earlier branch matched.
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
                # Use the fallback path when no earlier branch matched.
                else:
                    failed_items.append({"raw": raw, "message": "Intent debt tidak valid."})
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                if not debt_result or not debt_result.get("success"):
                    failed_items.append({
                        "raw": raw,
                        "message": debt_result.get("message") if debt_result else "Unknown error",
                    })
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                # Build fronted split result for the response flow.
                fronted_split_result = create_fronted_split_receivable_debts(parsed)
                attach_fronted_split_debt_relations(parsed, debt_result, fronted_split_result)

                if not parsed.get("hutang_id") and debt_result.get("debt_id"):
                    parsed["hutang_id"] = debt_result.get("debt_id")
                if not parsed.get("tipe_hutang") and debt_result.get("type"):
                    if debt_result.get("type") == "offset":
                        parsed["tipe_hutang"] = "offset"
                    # Use the fallback path when no earlier branch matched.
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

            # Build transaction result for the response flow.
            transaction_result = None
            if debt_transaction_items:
                # Build transaction result for the response flow.
                transaction_result = save_transactions_batch(debt_transaction_items)

            result_lines.append("")
            result_lines.append(f"💸 Debt diproses: *{debt_success_count} item*")

            if transaction_result:
                result_lines.append(f"📝 Cashflow tersimpan: *{transaction_result.get('success_count', 0)} item*")
                new_balances = transaction_result.get("new_balances", {})
                if new_balances:
                    result_lines.append("\n💳 *Saldo terbaru:*")
                    # Iterate through each account name, balance.
                    for account_name, balance in new_balances.items():
                        result_lines.append(f"• {account_name}: *{format_rupiah(balance)}*")

                tx_failed = transaction_result.get("failed_items", [])
                if tx_failed:
                    # Append the current value to failed items.
                    failed_items.extend(tx_failed)

                if transaction_result.get("message") and transaction_result.get("message") != "ok":
                    result_lines.append(f"\n⚠️ {transaction_result['message']}")

            if failed_items:
                result_lines.append("\n❌ *Catatan/Gagal:*")
                # Iterate through each item.
                for item in failed_items:
                    result_lines.append(f"• `{item['raw']}` — {item['message']}")

            # Send the Telegram response before continuing.
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

            # Validate missing mixed items before continuing.
            if not mixed_items:
                await safe_edit_message(query, "❌ Sesi mixed input expired. Coba input ulang.")
                return

            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                "⏳ *Sedang menyimpan semua item...*",
                parse_mode="Markdown",
            )

            # Normalize normal transaction items before matching.
            normal_transaction_items = []
            debt_transaction_items = []
            failed_items = []
            result_lines = ["✅ *Mixed input diproses!*\n"]

            debt_success_count = 0
            transaction_success_count = 0

            # Iterate through each i, item.
            for i, item in enumerate(mixed_items, 1):
                parsed = item["parsed"]
                raw = item["raw"]

                if item["kind"] == "transaction":
                    normal_transaction_items.append({
                        "parsed": parsed,
                        "raw": raw,
                    })
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                if item["kind"] != "debt":
                    failed_items.append({
                        "raw": raw,
                        "message": "Jenis item tidak valid.",
                    })
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                intent = parsed.get("intent")
                person = parsed.get("person_name")
                amount = parsed.get("amount")
                description = parsed.get("description") or ""
                account = parsed.get("account")
                debt_type_for_payment = parsed.get("debt_type_for_payment")

                # Validate missing person before continuing.
                if not person:
                    failed_items.append({
                        "raw": raw,
                        "message": "Nama orang tidak terdeteksi.",
                    })
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                # Build debt result for the response flow.
                debt_result = None

                if intent == "add_payable":
                    # Keep metadata aligned in the mixed-input save path.
                    debt_result = add_debt(
                        "payable",
                        person,
                        amount,
                        description,
                        cashflow_mode=parsed.get("cashflow_mode", ""),
                        fronting_mode=parsed.get("fronting_mode", ""),
                    )

                elif intent == "add_receivable":
                    # Keep metadata aligned in the mixed-input save path.
                    debt_result = add_debt(
                        "receivable",
                        person,
                        amount,
                        description,
                        cashflow_mode=parsed.get("cashflow_mode", ""),
                        fronting_mode=parsed.get("fronting_mode", ""),
                    )

                elif intent == "add_payment":
                    target_debt_id = parsed.get("target_debt_id")

                    if target_debt_id:
                        # Build debt result for the response flow.
                        debt_result = add_payment(target_debt_id, amount)
                    # Use the fallback path when no earlier branch matched.
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

                # Use the fallback path when no earlier branch matched.
                else:
                    failed_items.append({
                        "raw": raw,
                        "message": "Intent debt tidak valid.",
                    })
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                if not debt_result or not debt_result.get("success"):
                    failed_items.append({
                        "raw": raw,
                        "message": debt_result.get("message") if debt_result else "Unknown error",
                    })
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                # Build fronted split result for the response flow.
                fronted_split_result = create_fronted_split_receivable_debts(parsed)
                attach_fronted_split_debt_relations(parsed, debt_result, fronted_split_result)

                if not parsed.get("hutang_id") and debt_result.get("debt_id"):
                    parsed["hutang_id"] = debt_result.get("debt_id")
                if not parsed.get("tipe_hutang") and debt_result.get("type"):
                    if debt_result.get("type") == "offset":
                        parsed["tipe_hutang"] = "offset"
                    # Use the fallback path when no earlier branch matched.
                    else:
                        parsed["tipe_hutang"] = "utang" if debt_result.get("type") == "payable" else "piutang"

                debt_success_count += 1

                if intent in ["add_payable", "add_receivable"]:
                    if debt_result.get("is_settled"):
                        result_lines.append(f"{i}. ✅ Debt *{person}* impas/lunas")
                    # Use the fallback path when no earlier branch matched.
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
                    # Use the fallback path when no earlier branch matched.
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

                # Use the fallback path when no earlier branch matched.
                else:
                    debt_txn = {"type": "pending"}

                if debt_txn.get("type") != "pending":
                    debt_transaction_items.append({
                        "parsed": debt_txn,
                        "raw": raw,
                    })

            all_transaction_items = normal_transaction_items + debt_transaction_items

            # Build transaction result for the response flow.
            transaction_result = None
            if all_transaction_items:
                # Build transaction result for the response flow.
                transaction_result = save_transactions_batch(all_transaction_items)

            if transaction_result:
                transaction_success_count = transaction_result.get("success_count", 0)

                result_lines.append("")
                result_lines.append(f"📝 Transactions tersimpan: *{transaction_success_count} item*")
                result_lines.append(f"💸 Debt diproses: *{debt_success_count} item*")
                append_saved_summary_lines(result_lines, all_transaction_items)

                # Build split debt lines for the response flow.
                split_debt_lines = []
                saved_ids = transaction_result.get("saved_ids", []) if transaction_result else []
                # Normalize normal idx before matching.
                normal_idx = 0
                # Iterate through each item.
                for item in normal_transaction_items:
                    source_txn_id = saved_ids[normal_idx] if normal_idx < len(saved_ids) else ""
                    normal_idx += 1
                    debt_result = create_split_bill_debt(item.get("parsed", {}), item.get("raw", ""), source_transaction_id=source_txn_id)
                    if debt_result and debt_result.get("success"):
                        # Append the current value to split debt lines.
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
                                raise PartialMutationError(
                                    f"Relasi split bill gagal: {relation_result.get('message')}",
                                    operation="mixed_split_relation",
                                )
                    # Fall back when debt result.
                    elif debt_result:
                        raise PartialMutationError(
                            debt_result.get("message", "Gagal membuat piutang split bill."),
                            operation="mixed_split_debt",
                        )

                if split_debt_lines:
                    result_lines.append("\n🤝 *Piutang split bill dibuat:*")
                    # Append the current value to result lines.
                    result_lines.extend(split_debt_lines)

                new_balances = transaction_result.get("new_balances", {})
                if new_balances:
                    result_lines.append("\n💳 *Saldo terbaru:*")
                    # Iterate through each account name, balance.
                    for account_name, balance in new_balances.items():
                        result_lines.append(f"• {account_name}: *{format_rupiah(balance)}*")

                tx_failed = transaction_result.get("failed_items", [])
                if tx_failed:
                    # Append the current value to failed items.
                    failed_items.extend(tx_failed)

                if transaction_result.get("message") and transaction_result.get("message") != "ok":
                    result_lines.append(f"\n⚠️ {transaction_result['message']}")

            if failed_items:
                result_lines.append("\n❌ *Catatan/Gagal:*")
                # Iterate through each item.
                for item in failed_items:
                    result_lines.append(f"• `{item['raw']}` — {item['message']}")

            # Send the Telegram response before continuing.
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
            context.user_data.pop("pending_receipt", None)
            context.user_data.pop("pending_receipt_context", None)
            context.user_data.pop("pending_receipt_part_selection", None)
            context.user_data.pop("pending_receipt_extra_divisor", None)
            return

        if confirm_target == "batch":
            batch = context.user_data.get("pending_batch")

            # Validate missing batch before continuing.
            if not batch:
                await safe_edit_message(query, "❌ Sesi batch expired. Coba input ulang.")
                return

            # Send the Telegram response before continuing.
            await safe_edit_message(query,
                "⏳ *Sedang menyimpan semua transaksi...*",
                parse_mode="Markdown",
            )

            # Build result for the response flow.
            result = save_transactions_batch(batch)

            lines = [
                "✅ *Batch selesai diproses!*",
                f"📝 Berhasil: {result.get('success_count', 0)} transaksi",
            ]

            saved_ids = result.get("saved_ids", [])
            if saved_ids:
                lines.append("\n🔖 *ID tersimpan:*")
                # Iterate through each txn id.
                for txn_id in saved_ids:
                    lines.append(f"• `{txn_id}`")

            append_saved_summary_lines(lines, batch)

            # Build split debt lines for the response flow.
            split_debt_lines = []
            # Iterate through each idx, item.
            for idx, item in enumerate(batch):
                source_txn_id = saved_ids[idx] if idx < len(saved_ids) else ""
                debt_result = create_split_bill_debt(item.get("parsed", {}), item.get("raw", ""), source_transaction_id=source_txn_id)
                if debt_result and debt_result.get("success"):
                    # Append the current value to split debt lines.
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
                            raise PartialMutationError(
                                f"Relasi split bill gagal: {relation_result.get('message')}",
                                operation="batch_split_relation",
                            )
                # Fall back when debt result.
                elif debt_result:
                    raise PartialMutationError(
                        debt_result.get("message", "Gagal membuat piutang split bill."),
                        operation="batch_split_debt",
                    )

            if split_debt_lines:
                lines.append("\n🤝 *Piutang split bill dibuat:*")
                # Append the current value to lines.
                lines.extend(split_debt_lines)

            new_balances = result.get("new_balances", {})
            if new_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                # Iterate through each account name, balance.
                for account_name, balance in new_balances.items():
                    lines.append(f"• {account_name}: *{format_rupiah(balance)}*")

            failed_items = result.get("failed_items", [])
            if failed_items:
                lines.append("\n❌ *Catatan/Gagal:*")
                # Iterate through each item.
                for item in failed_items:
                    lines.append(f"• `{item['raw']}` — {item['message']}")

            budget_messages = []
            checked_categories = set()

            # Iterate through each item.
            for item in batch:
                parsed = item["parsed"]
                category = parsed.get("category")

                if parsed.get("type") != "expense" or not category:
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                if category in checked_categories:
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                # Append the current value to checked categories.
                checked_categories.add(category)

                budget_check = check_budget_after_transaction(category)
                if budget_check and budget_check.get("alert"):
                    budget_messages.append(
                        f"{budget_check['emoji']} *Budget {category}*: "
                        f"{budget_check['pct_used']}% terpakai"
                    )

            if budget_messages:
                lines.append("\n⚠️ *Budget Alert:*")
                # Append the current value to lines.
                lines.extend(budget_messages)

            if result.get("message") and result.get("message") != "ok":
                lines.append(f"\n⚠️ {result['message']}")

            # Send the Telegram response before continuing.
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

        # Validate missing parsed before continuing.
        if not parsed:
            await safe_edit_message(query, "❌ Sesi expired. Coba input ulang.")
            return

        # Send the Telegram response before continuing.
        await safe_edit_message(query,
            "⏳ *Sedang menyimpan transaksi...*",
            parse_mode="Markdown",
        )

        # Build result for the response flow.
        result = save_transaction(parsed, raw_input=raw)

        if result["success"]:
            balance_info = _build_saved_account_balance_info(parsed, result)

            split_info = ""
            split_debt = create_split_bill_debt(parsed, raw, source_transaction_id=result.get("transaction_id", ""))
            if split_debt and split_debt.get("success"):
                # Build split lines for the response flow.
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
                        raise PartialMutationError(
                            f"Relasi split bill gagal: {relation_result.get('message')}",
                            operation="single_split_relation",
                        )
            # Fall back when split debt.
            elif split_debt:
                raise PartialMutationError(
                    split_debt.get("message", "Gagal membuat piutang split bill."),
                    operation="single_split_debt",
                )

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

            # Send the Telegram response before continuing.
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

        # Send the Telegram response before continuing.
        await safe_edit_message(query,
            f"❌ Gagal menyimpan: {result['message']}"
        )
        return

    if data.startswith("cancel"):
        clear_pending_flow_state(context)

        await safe_edit_message(query, "🚫 Input dibatalkan. Tidak ada data yang disimpan.")
        return

    if data.startswith("pay_debt:"):
        parts = data.split(":")
        debt_id = parts[1]
        # Extract amount for validation.
        amount = float(parts[2])

        # Build result for the response flow.
        result = add_payment(debt_id, amount)

        if result["success"]:
            pending = context.user_data.get("pending_payment", {})
            person = pending.get("person", "")

            if result["is_settled"]:
                msg = (
                    f"✅ *Hutang ke {person} LUNAS!*\n"
                    f"💰 Dibayar: {format_rupiah(amount)}"
                )
            # Use the fallback path when no earlier branch matched.
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

        # Send the Telegram response before continuing.
        await safe_edit_message(query,
            f"❌ Gagal: {result['message']}"
        )
        return

    # Keep this section separated from the surrounding flow.
    await safe_edit_message(query, "❌ Tombol tidak dikenali atau sesi sudah tidak valid.")

