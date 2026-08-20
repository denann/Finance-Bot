"""Telegram translation layer for item-level bulk clarification."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from types import MappingProxyType

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.application.bulk_input import (
    BulkItem,
    BulkItemStatus,
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
    build_meal_split_custom_allocation_prompt,
    build_meal_split_final_payload,
    compute_equal_meal_split_shares,
    parse_meal_split_allocation,
)
from app.nlp.parse_safety import CLARIFICATION, assess_parse_safety, extract_person_candidate
from app.nlp.regex_parser import detect_date, detect_date_result


BULK_SESSION_KEY = "pending_bulk_session"
BULK_CALLBACK_PREFIXES = (
    "bulk_acc:",
    "bulk_split:",
    "bulk_rewrite:",
    "bulk_remove:",
    "bulk_cancel:",
    "bulk_sem:",
    "bulk_sem_payer:",
    "bulk_sem_alloc:",
    "bulk_sem_status:",
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


def _semantic_choice_keyboard(session: BulkSession, item: BulkItem) -> InlineKeyboardMarkup:
    """Show only semantic choices that can be built safely for this item."""

    from app.bot.handler_parts.callback_handler import (
        build_clarified_debt_payment,
        build_clarified_expense,
        build_clarified_fronting,
    )

    raw = item.raw_input
    parsed = dict(item.parsed_payload)
    prefix = f"bulk_sem:{session.session_id}:{item.item_id}"
    rows = []
    if build_clarified_debt_payment(raw, parsed):
        rows.append([InlineKeyboardButton("🟢 Orang ini bayar ke saya", callback_data=f"{prefix}:debt_payment")])
    person = extract_person_candidate(raw) or parsed.get("person_name") or parsed.get("subject")
    amount = float(parsed.get("amount") or parse_human_amount(raw) or 0)
    if person and amount > 0:
        rows.append([InlineKeyboardButton("🔴 Saya hutang ke orang ini", callback_data=f"{prefix}:payable")])
    if build_clarified_expense(raw, parsed):
        rows.append([InlineKeyboardButton("🧾 Pengeluaran biasa", callback_data=f"{prefix}:expense")])
    rows.append([InlineKeyboardButton("👤 Orang lain yang bayar", callback_data=f"{prefix}:no_cashflow")])
    if person and amount > 0:
        rows.append([InlineKeyboardButton("🤝 Split bill", callback_data=f"{prefix}:split")])
    if build_clarified_fronting(raw, parsed):
        rows.append([InlineKeyboardButton("🙋 Saya talangin", callback_data=f"{prefix}:fronting")])
    rows.append([
        InlineKeyboardButton("✍️ Tulis ulang", callback_data=f"bulk_rewrite:{session.session_id}:{item.item_id}"),
        InlineKeyboardButton("Hapus item", callback_data=f"bulk_remove:{session.session_id}:{item.item_id}"),
    ])
    rows.append([InlineKeyboardButton("Batal", callback_data=f"bulk_cancel:{session.session_id}")])
    return InlineKeyboardMarkup(rows)


def _semantic_split_keyboard(session: BulkSession, item: BulkItem, stage: str) -> InlineKeyboardMarkup:
    base = f"{session.session_id}:{item.item_id}"
    if stage == "payer":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🙋 Saya yang bayar", callback_data=f"bulk_sem_payer:{base}:self")],
            [InlineKeyboardButton("👤 Bukan saya yang bayar", callback_data=f"bulk_sem_payer:{base}:other")],
            [InlineKeyboardButton("Batal", callback_data=f"bulk_cancel:{session.session_id}")],
        ])
    if stage == "allocation":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⚖️ Bagi rata", callback_data=f"bulk_sem_alloc:{base}:equal")],
            [InlineKeyboardButton("📊 Atur pembagian", callback_data=f"bulk_sem_alloc:{base}:custom")],
            [InlineKeyboardButton("Batal", callback_data=f"bulk_cancel:{session.session_id}")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Sudah bayar", callback_data=f"bulk_sem_status:{base}:paid")],
        [InlineKeyboardButton("⏳ Belum bayar", callback_data=f"bulk_sem_status:{base}:unpaid")],
        [InlineKeyboardButton("Batal", callback_data=f"bulk_cancel:{session.session_id}")],
    ])


def _semantic_wait_item(item: BulkItem, *, reason: str, semantic_state: dict) -> BulkItem:
    parsed = deepcopy(dict(item.parsed_payload))
    parsed["_semantic_split"] = deepcopy(semantic_state)
    return replace(
        item,
        status=BulkItemStatus.NEEDS_CLARIFICATION,
        kind="transaction",
        parsed_payload=MappingProxyType(parsed),
        missing_fields=(),
        clarification_reason=reason,
        validation_errors=(),
    )


def _classify_semantic_legacy_item(item: BulkItem, legacy_item: dict) -> BulkItem:
    """Reclassify an explicitly chosen meaning without re-triggering ambiguity."""

    parsed = deepcopy(dict(legacy_item.get("parsed") or {}))
    kind = str(legacy_item.get("kind") or "failed")
    date_result = detect_date_result(item.raw_input)
    account_required = False
    split_required = False
    if kind == "transaction":
        account_required = needs_account(parsed)
        split_required = split_bill_needs_decision(parsed)
    elif kind == "debt":
        account_required = debt_uses_cashflow(parsed) and parsed.get("intent") != "offset_debt" and not parsed.get("account")
    return make_bulk_item(
        item_id=item.item_id,
        original_index=item.original_index,
        raw_input=item.raw_input,
        legacy_item={"kind": kind, "parsed": parsed, "raw": item.raw_input},
        invalid_date=date_result.status == "invalid",
        safety_requires_clarification=False,
        needs_account=account_required,
        needs_split_decision=split_required,
    )


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
        return f"{header}\n\nMakna item ini masih ambigu. Pilih makna finansial yang benar untuk item ini; item lain tetap dipertahankan."
    if item.clarification_reason == "semantic_split_payer":
        return f"{header}\n\nSiapa yang membayar transaksi split ini di awal?"
    if item.clarification_reason == "semantic_split_allocation":
        return f"{header}\n\nPembagian split bill-nya bagaimana?"
    if item.clarification_reason == "semantic_split_custom":
        return f"{header}\n\nTulis pembagian custom untuk item ini."
    if item.clarification_reason == "semantic_split_status":
        state = dict(item.parsed_payload).get("_semantic_split") or {}
        return f"{header}\n\n{'Apakah teman sudah bayar bagiannya?' if state.get('payer') == 'self' else 'Apakah kamu sudah bayar bagianmu?'}"
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
        if waiting.awaiting_mode == "semantic_split_payer":
            await _send_or_edit(update, _issue_text(item, position, total), _semantic_split_keyboard(waiting, item, "payer"))
            return
        if waiting.awaiting_mode == "semantic_split_allocation":
            await _send_or_edit(update, _issue_text(item, position, total), _semantic_split_keyboard(waiting, item, "allocation"))
            return
        if waiting.awaiting_mode == "semantic_split_custom_text":
            state = dict(item.parsed_payload).get("_semantic_split") or {}
            await _send_or_edit(
                update,
                f"{_issue_text(item, position, total)}\n\n{build_meal_split_custom_allocation_prompt(state)}",
                _cancel_keyboard(waiting),
            )
            return
        if waiting.awaiting_mode == "semantic_split_status":
            await _send_or_edit(update, _issue_text(item, position, total), _semantic_split_keyboard(waiting, item, "status"))
            return
        if item.clarification_reason == "ambiguous_parse":
            await _send_or_edit(update, _issue_text(item, position, total), _semantic_choice_keyboard(waiting, item))
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
    elif session.awaiting_mode == "semantic_split_custom_text":
        state = deepcopy(dict(target.parsed_payload).get("_semantic_split") or {})
        shares = parse_meal_split_allocation(user_text, float(state.get("amount") or 0), list(state.get("people") or []))
        if not shares:
            await _send_or_edit(
                update,
                "Pembagian belum terbaca. Gunakan format seperti `saya 30k, Budi 50k` atau `saya 100%, Budi 100%`.",
                _cancel_keyboard(session),
            )
            return True
        state["shares"] = shares
        state["allocation_mode"] = "custom"
        replacement = _semantic_wait_item(target, reason="semantic_split_status", semantic_state=state)
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
        if action == "bulk_sem" and rest:
            if target.clarification_reason != "ambiguous_parse":
                raise StaleBulkSession("Pilihan semantic lama sudah tidak berlaku.")
            choice = rest[0]
            from app.bot.handler_parts.callback_handler import (
                build_clarified_debt_payment,
                build_clarified_expense,
                build_clarified_fronting,
            )

            raw = target.raw_input
            parsed = dict(target.parsed_payload)
            if choice == "no_cashflow":
                updated = remove_bulk_item(session, item_id)
                context.user_data[BULK_SESSION_KEY] = updated
                await _advance_bulk_flow(update, context, updated)
                return
            if choice == "expense":
                clarified = build_clarified_expense(raw, parsed)
                if not clarified:
                    raise StaleBulkSession("Makna expense belum dapat dibangun dengan aman.")
                replacement = _classify_semantic_legacy_item(target, {"kind": "transaction", "parsed": clarified})
            elif choice == "debt_payment":
                clarified = build_clarified_debt_payment(raw, parsed)
                if not clarified:
                    raise StaleBulkSession("Makna pembayaran debt belum dapat dibangun dengan aman.")
                replacement = _classify_semantic_legacy_item(target, {"kind": "debt", "parsed": clarified})
            elif choice == "fronting":
                clarified = build_clarified_fronting(raw, parsed)
                if not clarified:
                    raise StaleBulkSession("Makna talangan belum dapat dibangun dengan aman.")
                replacement = _classify_semantic_legacy_item(target, {"kind": "debt", "parsed": clarified})
            elif choice == "payable":
                person = extract_person_candidate(raw) or parsed.get("person_name") or parsed.get("subject") or ""
                person = " ".join(str(person).split()).strip().title()
                amount = float(parsed.get("amount") or parse_human_amount(raw) or 0)
                if not person or amount <= 0:
                    raise StaleBulkSession("Nama orang atau nominal belum terbaca untuk hutang.")
                debt = {
                    "intent": "add_payable",
                    "person_name": person,
                    "amount": amount,
                    "description": f"Uang titipan/pinjaman dari {person}",
                    "date": detect_date(raw),
                    "raw_input": raw,
                    "cashflow_mode": "cashflow",
                    "fronting_mode": "clarified_payable_cash_in",
                }
                replacement = _classify_semantic_legacy_item(target, {"kind": "debt", "parsed": debt})
            elif choice == "split":
                person = extract_person_candidate(raw) or parsed.get("person_name") or parsed.get("subject") or ""
                person = " ".join(str(person).split()).strip().title()
                amount = float(parsed.get("amount") or parse_human_amount(raw) or 0)
                clarified = build_clarified_expense(raw, parsed)
                if not person or amount <= 0 or not clarified:
                    raise StaleBulkSession("Data split belum cukup untuk dipilih secara aman.")
                split_state = {
                    "raw": raw,
                    "people": [person],
                    "amount": amount,
                    "parsed": clarified,
                }
                replacement = _semantic_wait_item(target, reason="semantic_split_payer", semantic_state=split_state)
            else:
                raise StaleBulkSession("Pilihan semantic bulk tidak valid.")
            updated = replace_bulk_item(session, replacement)
            context.user_data[BULK_SESSION_KEY] = updated
            await _advance_bulk_flow(update, context, updated)
            return

        if action == "bulk_sem_payer" and rest and rest[0] in {"self", "other"}:
            if target.clarification_reason != "semantic_split_payer":
                raise StaleBulkSession("Pilihan payer lama sudah tidak berlaku.")
            state = deepcopy(dict(target.parsed_payload).get("_semantic_split") or {})
            if not state:
                raise StaleBulkSession("State split sudah tidak tersedia.")
            state["payer"] = rest[0]
            replacement = _semantic_wait_item(target, reason="semantic_split_allocation", semantic_state=state)
            updated = replace_bulk_item(session, replacement)
            context.user_data[BULK_SESSION_KEY] = updated
            await _advance_bulk_flow(update, context, updated)
            return

        if action == "bulk_sem_alloc" and rest and rest[0] in {"equal", "custom"}:
            if target.clarification_reason != "semantic_split_allocation":
                raise StaleBulkSession("Pilihan pembagian lama sudah tidak berlaku.")
            state = deepcopy(dict(target.parsed_payload).get("_semantic_split") or {})
            if not state:
                raise StaleBulkSession("State split sudah tidak tersedia.")
            if rest[0] == "equal":
                state["shares"] = compute_equal_meal_split_shares(float(state.get("amount") or 0), list(state.get("people") or []))
                state["allocation_mode"] = "equal"
                reason = "semantic_split_status"
            else:
                reason = "semantic_split_custom"
            replacement = _semantic_wait_item(target, reason=reason, semantic_state=state)
            updated = replace_bulk_item(session, replacement)
            context.user_data[BULK_SESSION_KEY] = updated
            await _advance_bulk_flow(update, context, updated)
            return

        if action == "bulk_sem_status" and rest and rest[0] in {"paid", "unpaid"}:
            if target.clarification_reason != "semantic_split_status":
                raise StaleBulkSession("Pilihan status split lama sudah tidak berlaku.")
            state = deepcopy(dict(target.parsed_payload).get("_semantic_split") or {})
            if not state:
                raise StaleBulkSession("State split sudah tidak tersedia.")
            state["status"] = rest[0]
            payload = build_meal_split_final_payload(state)
            if payload.get("mode") == "transaction":
                replacement = _classify_semantic_legacy_item(target, {"kind": "transaction", "parsed": payload.get("parsed") or {}})
            elif payload.get("mode") == "debt":
                replacement = _classify_semantic_legacy_item(target, {"kind": "debt", "parsed": payload.get("debt") or {}})
            else:
                raise StaleBulkSession("Hasil split tidak valid.")
            updated = replace_bulk_item(session, replacement)
            context.user_data[BULK_SESSION_KEY] = updated
            await _advance_bulk_flow(update, context, updated)
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
