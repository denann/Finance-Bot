"""Telegram translation layer for item-level bulk clarification."""

from __future__ import annotations

from copy import deepcopy

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.application.bulk_input import (
    BulkItem,
    BulkSession,
    StaleBulkSession,
    assert_current_target,
    await_rewrite,
    cancel_bulk_session,
    create_bulk_session,
    make_bulk_item,
    remove_bulk_item,
    replace_bulk_item,
    result_for_session,
)
from app.application.results import ClarificationRequired, PreviewReady, mutable_payload
from app.bot.handler_parts.command_router import is_authorized, reject_unauthorized
from app.bot.handler_parts.common_imports import (
    SKIP_ACCOUNT_CALLBACK_VALUE,
    SKIP_ACCOUNT_NAME,
    account_keyboard,
    md_safe,
    parse_human_amount,
    reply_update_safely,
    safe_edit_message,
)
from app.bot.handler_parts.state_utils import clear_pending_flow_state
from app.bot.handler_parts.transaction_flow import (
    apply_split_bill_decision_to_parsed,
    build_missing_amount_prompt,
    build_mixed_detail_preview,
    debt_uses_cashflow,
    finalize_missing_amount_item,
    mixed_ready_to_save,
    needs_account,
    parse_mixed_item,
    parse_mixed_item_async,
    parse_mixed_items_batch,
    preview_action_keyboard,
    preview_action_question,
    split_bill_needs_decision,
)
from app.nlp.parse_safety import CLARIFICATION, assess_parse_safety
from app.nlp.regex_parser import detect_date_result


BULK_SESSION_KEY = "pending_bulk_session"
BULK_CALLBACK_PREFIXES = (
    "bulk_acc:",
    "bulk_split:",
    "bulk_rewrite:",
    "bulk_remove:",
    "bulk_cancel:",
)


def is_bulk_callback_data(data: str) -> bool:
    """Return whether callback data belongs to the bounded bulk flow."""

    return str(data or "").startswith(BULK_CALLBACK_PREFIXES)


def _classify_legacy_item(
    raw: str,
    legacy_item: dict,
    *,
    original_index: int,
    item_id: str,
) -> BulkItem:
    """Translate current parser output into the pure application item model."""

    parsed = legacy_item.get("parsed") or {}
    kind = legacy_item.get("kind")
    date_result = detect_date_result(raw)
    safety = assess_parse_safety(raw, parsed) if kind == "transaction" else {}
    account_required = False
    split_required = False
    if kind == "transaction":
        account_required = needs_account(parsed)
        split_required = split_bill_needs_decision(parsed)
    elif kind == "debt":
        account_required = (
            debt_uses_cashflow(parsed)
            and parsed.get("intent") != "offset_debt"
            and not parsed.get("account")
        )

    return make_bulk_item(
        item_id=item_id,
        original_index=original_index,
        raw_input=raw,
        legacy_item=legacy_item,
        invalid_date=date_result.status == "invalid",
        safety_requires_clarification=safety.get("recommended_action") == CLARIFICATION,
        needs_account=account_required,
        needs_split_decision=split_required,
    )


async def _classify_lines(input_lines: list[str]) -> list[BulkItem]:
    """Parse all lines while sharing one Gemini call across unresolved items."""

    legacy_items = await parse_mixed_items_batch(input_lines)
    return [
        _classify_legacy_item(
            line,
            legacy_items[index],
            original_index=index,
            item_id=f"i{index + 1}",
        )
        for index, line in enumerate(input_lines)
    ]


def _cancel_keyboard(session: BulkSession) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Batal", callback_data=f"bulk_cancel:{session.session_id}"),
    ]])


def _rewrite_remove_keyboard(session: BulkSession, item: BulkItem) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "Tulis ulang",
                callback_data=f"bulk_rewrite:{session.session_id}:{item.item_id}",
            ),
            InlineKeyboardButton(
                "Hapus item",
                callback_data=f"bulk_remove:{session.session_id}:{item.item_id}",
            ),
        ],
        [InlineKeyboardButton("Batal", callback_data=f"bulk_cancel:{session.session_id}")],
    ])


def _account_keyboard(session: BulkSession, item: BulkItem) -> InlineKeyboardMarkup:
    prefix = f"bulk_acc:{session.session_id}:{item.item_id}"
    base = account_keyboard(prefix)
    rows = [list(row) for row in base.inline_keyboard[:-1]]
    rows.append([InlineKeyboardButton("Batal", callback_data=f"bulk_cancel:{session.session_id}")])
    return InlineKeyboardMarkup(rows)


def _split_keyboard(session: BulkSession, item: BulkItem) -> InlineKeyboardMarkup:
    base = f"bulk_split:{session.session_id}:{item.item_id}"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Sudah dibayar", callback_data=f"{base}:paid"),
            InlineKeyboardButton("Belum dibayar", callback_data=f"{base}:unpaid"),
        ],
        [InlineKeyboardButton("Batal", callback_data=f"bulk_cancel:{session.session_id}")],
    ])


def _issue_text(item: BulkItem, position: int, total: int) -> str:
    """Build concise owner-visible context for the current unresolved item."""

    header = f"Item {position}/{total}: `{md_safe(item.raw_input)}`"
    if item.clarification_reason == "missing_account":
        return f"{header}\n\nPilih rekening untuk item ini. Item lain tetap disimpan dalam batch."
    if item.clarification_reason == "split_decision":
        return f"{header}\n\nStatus split bill untuk item ini sudah dibayar atau belum?"
    if item.clarification_reason == "invalid_date":
        return f"{header}\n\nTanggal item ini tidak valid. Tulis ulang, hapus item, atau batalkan seluruh batch."
    if item.clarification_reason == "ambiguous_parse":
        return f"{header}\n\nMakna item ini masih ambigu. Tulis ulang, hapus item, atau batalkan seluruh batch."
    return f"{header}\n\nItem ini belum dapat dipahami dengan aman. Tulis ulang, hapus item, atau batalkan seluruh batch."


async def _send_or_edit(update: Update, text: str, reply_markup) -> None:
    query = update.callback_query
    if query is not None:
        await safe_edit_message(query, text, parse_mode="Markdown", reply_markup=reply_markup)
        return
    await reply_update_safely(update, text, parse_mode="Markdown", reply_markup=reply_markup)


async def _advance_bulk_flow(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: BulkSession,
) -> None:
    """Show exactly one unresolved item or the final immutable batch preview."""

    result = result_for_session(session)
    if isinstance(result, ClarificationRequired):
        waiting = result.payload["session"]
        item = result.payload["item"]
        context.user_data[BULK_SESSION_KEY] = waiting
        total = len([candidate for candidate in waiting.items if candidate.status.value != "removed"])
        position = item.original_index + 1

        if waiting.awaiting_mode == "amount":
            text = build_missing_amount_prompt(item.raw_input, dict(item.parsed_payload), position, total)
            await _send_or_edit(update, text, _cancel_keyboard(waiting))
            return
        if waiting.awaiting_mode == "account":
            await _send_or_edit(update, _issue_text(item, position, total), _account_keyboard(waiting, item))
            return
        if waiting.awaiting_mode == "split":
            await _send_or_edit(update, _issue_text(item, position, total), _split_keyboard(waiting, item))
            return
        await _send_or_edit(update, _issue_text(item, position, total), _rewrite_remove_keyboard(waiting, item))
        return

    if not isinstance(result, PreviewReady):
        raise RuntimeError("Hasil bulk tidak dikenali.")

    mixed_items = mutable_payload(result.payload["mixed_items"])
    context.user_data.pop(BULK_SESSION_KEY, None)
    if not mixed_items:
        context.user_data.pop("pending_mixed", None)
        await _send_or_edit(update, "Tidak ada item tersisa. Batch dibatalkan tanpa menyimpan data.", None)
        return

    context.user_data["pending_mixed"] = mixed_items
    preview = build_mixed_detail_preview(mixed_items)
    ready = mixed_ready_to_save(mixed_items)
    await _send_or_edit(
        update,
        f"{preview}\n\n{preview_action_question(ready)}",
        preview_action_keyboard("mixed", ready),
    )


async def start_bulk_flow(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    input_lines: list[str],
) -> bool:
    """Start item-level clarification for a parsed multi-input message."""

    if len(input_lines) <= 1:
        return False
    clear_pending_flow_state(context)
    session = create_bulk_session(await _classify_lines(input_lines))
    context.user_data[BULK_SESSION_KEY] = session
    await _advance_bulk_flow(update, context, session)
    return True


async def handle_pending_bulk_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_text: str,
) -> bool:
    """Resolve amount or rewritten text for the currently targeted bulk item."""

    session = context.user_data.get(BULK_SESSION_KEY)
    if not isinstance(session, BulkSession) or not session.awaiting_item_id:
        return False

    target = next(item for item in session.items if item.item_id == session.awaiting_item_id)
    if session.awaiting_mode == "amount":
        amount = parse_human_amount(user_text)
        if not amount or amount <= 0:
            await _send_or_edit(
                update,
                "Nominal belum terbaca. Tulis seperti `13k`, `50000`, atau `94k/2`.",
                _cancel_keyboard(session),
            )
            return True
        legacy = finalize_missing_amount_item(
            {"kind": target.kind, "parsed": dict(target.parsed_payload), "raw": target.raw_input},
            amount,
        )
        replacement = _classify_legacy_item(
            target.raw_input,
            legacy,
            original_index=target.original_index,
            item_id=target.item_id,
        )
    elif session.awaiting_mode == "rewrite_text":
        replacement = _classify_legacy_item(
            user_text,
            await parse_mixed_item_async(user_text),
            original_index=target.original_index,
            item_id=target.item_id,
        )
    else:
        return False

    updated = replace_bulk_item(session, replacement)
    context.user_data[BULK_SESSION_KEY] = updated
    await _advance_bulk_flow(update, context, updated)
    return True


def _mark_account(item: BulkItem, account: str) -> BulkItem:
    parsed = deepcopy(dict(item.parsed_payload))
    if account == SKIP_ACCOUNT_CALLBACK_VALUE:
        parsed["account"] = SKIP_ACCOUNT_NAME
        parsed["skip_account"] = True
        if item.kind == "debt":
            parsed["cashflow_mode"] = "debt_only"
        parsed["catatan"] = (
            str(parsed.get("catatan") or "").strip() + " | sudah berlalu/tanpa update saldo"
        ).strip(" |")
    else:
        parsed["account"] = account
    legacy = {"kind": item.kind, "parsed": parsed, "raw": item.raw_input}
    return _classify_legacy_item(
        item.raw_input,
        legacy,
        original_index=item.original_index,
        item_id=item.item_id,
    )


def _mark_split(item: BulkItem, status: str) -> BulkItem:
    parsed = deepcopy(dict(item.parsed_payload))
    apply_split_bill_decision_to_parsed(parsed, status)
    legacy = {"kind": item.kind, "parsed": parsed, "raw": item.raw_input}
    return _classify_legacy_item(
        item.raw_input,
        legacy,
        original_index=item.original_index,
        item_id=item.item_id,
    )


async def handle_bulk_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle bounded bulk clarification callbacks without finance writes."""

    if not is_authorized(update):
        await reject_unauthorized(update)
        return
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    data = str(query.data or "")
    session = context.user_data.get(BULK_SESSION_KEY)
    if not isinstance(session, BulkSession):
        await safe_edit_message(query, "Sesi bulk sudah tidak aktif. Kirim input batch baru.")
        return

    try:
        if data.startswith("bulk_cancel:"):
            session_id = data.split(":", 1)[1]
            assert_current_target(session, session_id)
            context.user_data[BULK_SESSION_KEY] = cancel_bulk_session(session)
            clear_pending_flow_state(context)
            await safe_edit_message(query, "Batch dibatalkan. Tidak ada data yang disimpan.")
            return

        action, session_id, item_id, *rest = data.split(":", 3)
        assert_current_target(session, session_id, item_id)
        target = next(item for item in session.items if item.item_id == item_id)

        if action == "bulk_rewrite":
            updated = await_rewrite(session, item_id)
            context.user_data[BULK_SESSION_KEY] = updated
            await safe_edit_message(
                query,
                f"Tulis ulang item `{md_safe(target.raw_input)}` dengan format yang lebih jelas.",
                parse_mode="Markdown",
                reply_markup=_cancel_keyboard(updated),
            )
            return
        if action == "bulk_remove":
            updated = remove_bulk_item(session, item_id)
        elif action == "bulk_acc" and rest:
            updated = replace_bulk_item(session, _mark_account(target, rest[0]))
        elif action == "bulk_split" and rest and rest[0] in {"paid", "unpaid"}:
            updated = replace_bulk_item(session, _mark_split(target, rest[0]))
        else:
            raise StaleBulkSession("Pilihan klarifikasi tidak valid.")

        context.user_data[BULK_SESSION_KEY] = updated
        await _advance_bulk_flow(update, context, updated)
    except StaleBulkSession:
        await safe_edit_message(query, "Pilihan ini sudah kedaluwarsa. Gunakan prompt bulk terbaru.")
