"""Transaction-only browser, stable reference snapshot, and staged selector flows.

This module intentionally serves only the transaction family. Frozen snapshots
store stable identity/query state plus the bounded display data needed for
read-only navigation. Mutation-sensitive actions still re-read by stable
transaction ID before preview/revalidation/write decisions.
"""
from __future__ import annotations

import secrets
import shlex
from math import ceil

from telegram import CopyTextButton

from app.bot.handler_parts.common_imports import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    build_transaction_display_lines,
    clear_tracked_inline_keyboard,
    enrich_transactions_with_debt_info,
    format_expense_net_gross,
    format_indonesian_date_group_label,
    format_rupiah,
    get_account_report,
    get_daily_report,
    get_net_expense_after_receivable,
    get_monthly_report,
    get_recent_transactions,
    get_transaction_account_text,
    get_transaction_payable_parts,
    get_transaction_receivable_parts,
    get_weekly_report,
    is_authorized,
    md_code_text,
    md_safe,
    preview_delete_transactions_by_refs,
    reject_unauthorized,
    reply_tracked_inline_keyboard,
    reply_update_safely,
    safe_edit_message,
    search_transactions,
    summarize,
)
from app.bot.handler_parts.command_router import expand_txn_refs
from app.bot.handler_parts.transaction_chart import send_transaction_timeseries_chart_message
from app.bot.keyboards import confirm_keyboard
from app.bot.pending_actions import cancel_pending_actions_by_flow, create_bound_preview_action
from app.application.external_io import run_sheets_read
from app.services import transaction_service
from app.services.debt_service import transaction_debt_dependency_signature
from app.services.operation_errors import PartialMutationError
from app.services.resolver_service import assess_edit_category_choice


BROWSER_STATE_KEY = "transaction_browser_session"
REF_CONTEXT_KEY = "transaction_ref_context"
SELECTOR_STATE_KEY = "pending_txn_selector"
STAGED_BULK_KEY = "pending_bulk_edit_staged"
BROWSER_CONTROL_MESSAGE_KEY = "transaction_browser_control_message_id"
PAGE_SIZE = 8
SELECTOR_LIMIT = 100

# Keep browser-session display state deliberately smaller than the service row.
# These are the only fields consumed by compact/detail transaction rendering.
DISPLAY_SNAPSHOT_FIELDS = frozenset({
    "id",
    "date",
    "type",
    "amount",
    "category",
    "account",
    "to_account",
    "description",
    "subject",
    "catatan",
    "debt_receivable_remaining",
    "debt_payable_remaining",
    "debt_receivable_original",
    "debt_payable_original",
    "debt_people",
    "debt_receivable_parts",
    "debt_payable_parts",
    "net_expense_after_receivable",
    # Existing render helpers/test harnesses may expose already-computed aliases.
    "net",
    "receivables",
    "payables",
})

TRANSACTION_CHILD_ACTION_FLOWS = frozenset({
    "edit_txn",
    "edit_txns_bulk",
    "edit_txns_bulk_staged",
    "delete_txns",
    # Saved Edit can temporarily enter the existing add-category wizard.
    # Explicit child cancellation must retire that immutable confirmation too.
    "category_add",
})
TRANSACTION_CHILD_STATE_KEYS = frozenset({
    SELECTOR_STATE_KEY,
    STAGED_BULK_KEY,
    "pending_edit_txn",
    "pending_edit_category_choice",
    "pending_bulk_edit_category_decision",
    "pending_bulk_edit_txns",
    "pending_delete_refs",
    "pending_delete_txn_ids",
})


def _new_sid() -> str:
    return secrets.token_hex(4)


def transaction_summary_label(period_type: str, account_filter: str | None = None) -> str:
    """Return a truthful summary label for the actual summary behavior."""
    if str(account_filter or "").strip():
        return "📊 Ringkasan Rekening"
    if str(period_type or "").strip().lower() == "month":
        return "📊 Ringkasan Bulanan"
    return "📊 Ringkasan Hasil"


def _identities(transactions: list[dict]) -> list[dict]:
    result = []
    for txn in transactions or []:
        txn_id = str((txn or {}).get("id") or "").strip()
        if not txn_id:
            continue
        row_hint = int((txn or {}).get("_row_index") or 0) or None
        result.append({"id": txn_id, "row_hint": row_hint})
    return result


def _freeze_display_record(txn: dict) -> dict:
    """Project one transaction into the bounded immutable-by-convention UI view."""
    source = dict(txn or {})
    frozen = {key: source.get(key) for key in DISPLAY_SNAPSHOT_FIELDS if key in source}
    frozen["id"] = str(source.get("id") or "").strip()
    for key in ("debt_people",):
        if isinstance(frozen.get(key), list):
            frozen[key] = list(frozen[key])
    for key in ("debt_receivable_parts", "debt_payable_parts", "receivables", "payables"):
        if isinstance(frozen.get(key), list):
            frozen[key] = [dict(item or {}) for item in frozen[key]]
    return frozen


def _freeze_display_snapshot(transactions: list[dict]) -> list[dict]:
    return [_freeze_display_record(txn) for txn in transactions or [] if str((txn or {}).get("id") or "").strip()]


def _stored_display_records(session: dict) -> list[dict | None]:
    """Return frozen display records in canonical identity order without provider I/O."""
    return _records_for_snapshot(session, list(session.get("display_records") or []))


def _get_snapshot_display_txn(session: dict, ref_no: int) -> tuple[dict | None, str | None]:
    identities = session.get("identities") or []
    if ref_no < 1 or ref_no > len(identities):
        return None, "Nomor transaksi tidak ada di snapshot ini."
    txn_id = str(identities[ref_no - 1].get("id") or "").strip()
    if not txn_id:
        return None, "Identity transaksi snapshot tidak valid."
    if sum(1 for identity in identities if str(identity.get("id") or "").strip() == txn_id) != 1:
        return None, "Transaction ID di snapshot tidak unik; detail diblok."
    ordered = _stored_display_records(session)
    txn = ordered[ref_no - 1] if ref_no - 1 < len(ordered) else None
    if not txn:
        return None, "Transaksi tidak tersedia di frozen display snapshot ini."
    return txn, None


def set_transaction_ref_context(context, session: dict) -> None:
    """Replace the long-lived numeric transaction reference context."""
    context.user_data[REF_CONTEXT_KEY] = {
        "session_id": session.get("session_id"),
        "family": session.get("family"),
        "query": dict(session.get("query") or {}),
        "ordered_ids": [str(item.get("id") or "") for item in session.get("identities") or []],
        "total_count": len(session.get("identities") or []),
    }
    # Remove the legacy row-authoritative map so new mutation flows cannot
    # accidentally fall back to stale sheet positions.
    context.user_data.pop("last_txn_map", None)


def invalidate_transaction_browser(context, *, reason: str = "mutation", clear_refs: bool = True) -> None:
    """Invalidate browser state, optionally preserving long-lived numeric refs.

    ``clear_refs=True`` preserves the old fail-closed mutation behavior for
    callers that truly need both lifecycles discarded.  Browser retirement
    uses ``clear_refs=False`` so CTX-033 can keep the last useful numeric
    transaction-reference snapshot after the inline controls are retired.
    """
    context.user_data.pop(BROWSER_STATE_KEY, None)
    if clear_refs:
        context.user_data.pop(REF_CONTEXT_KEY, None)
    context.user_data["transaction_browser_invalidated_reason"] = reason


def get_transaction_browser(context) -> dict:
    return dict((getattr(context, "user_data", {}) or {}).get(BROWSER_STATE_KEY) or {})


def transaction_browser_is_suspended(context) -> bool:
    return str(get_transaction_browser(context).get("status") or "active") == "suspended"


def clear_transaction_child_state(context) -> None:
    """Clear only Edit/Delete child-flow mutable state, never browser/refs."""
    user_data = getattr(context, "user_data", {}) or {}
    for key in TRANSACTION_CHILD_STATE_KEYS:
        user_data.pop(key, None)


def cancel_transaction_child_actions(context) -> int:
    user_data = getattr(context, "user_data", {}) or {}
    return cancel_pending_actions_by_flow(user_data, TRANSACTION_CHILD_ACTION_FLOWS)


def suspend_transaction_browser(context, *, expected_session_id: str | None = None) -> str | None:
    """Mark the current transaction browser as the suspended parent of a child flow."""
    session = (getattr(context, "user_data", {}) or {}).get(BROWSER_STATE_KEY)
    if not isinstance(session, dict) or not session:
        return None
    sid = str(session.get("session_id") or "")
    if expected_session_id and sid != str(expected_session_id):
        return None
    session["status"] = "suspended"
    session["child_parent_view"] = {
        "view": str(session.get("current_view") or "list"),
        "page": int(session.get("current_page") or 0),
        "detail_ref": int(session.get("current_detail_ref") or 0) or None,
        "detail_txn_id": str(session.get("current_detail_txn_id") or "") or None,
    }
    context.user_data[BROWSER_STATE_KEY] = session
    return sid or None


def _reactivate_transaction_browser_state(context) -> dict | None:
    session = (getattr(context, "user_data", {}) or {}).get(BROWSER_STATE_KEY)
    if not isinstance(session, dict) or not session:
        return None
    session["status"] = "active"
    session.pop("child_parent_view", None)
    context.user_data[BROWSER_STATE_KEY] = session
    return session


def _chat_id_from_update(update) -> int | None:
    chat = getattr(update, "effective_chat", None)
    value = getattr(chat, "id", None)
    if value:
        return int(value)
    message = getattr(update, "message", None)
    value = getattr(message, "chat_id", None)
    if value:
        return int(value)
    query = getattr(update, "callback_query", None)
    qmsg = getattr(query, "message", None)
    value = getattr(qmsg, "chat_id", None)
    return int(value) if value else None


async def retire_transaction_browser(update, context, *, reason: str, preserve_refs: bool = True) -> bool:
    """Retire browser controls/session while optionally preserving numeric refs."""
    if not (getattr(context, "user_data", {}) or {}).get(BROWSER_STATE_KEY):
        return False
    await clear_tracked_inline_keyboard(context, _chat_id_from_update(update), BROWSER_CONTROL_MESSAGE_KEY)
    invalidate_transaction_browser(context, reason=reason, clear_refs=not preserve_refs)
    return True


def _is_rekening_browser_invocation(message_text: str) -> bool:
    parts = str(message_text or "").strip().split(maxsplit=1)
    return len(parts) > 1 and bool(parts[1].strip())


async def prepare_transaction_browser_for_command(update, context, command_name: str, message_text: str) -> None:
    """Apply parent/retire/replace lifecycle before an explicit slash command."""
    command = str(command_name or "").strip().lower()
    if command in {"edit_txn", "delete_txn"}:
        # A new child command replaces any older child; keep the browser parent.
        cancel_transaction_child_actions(context)
        if transaction_browser_is_suspended(context):
            _reactivate_transaction_browser_state(context)
        return

    if command in {"transaksi", "last", "cari"} or (command == "rekening" and _is_rekening_browser_invocation(message_text)):
        cancel_transaction_child_actions(context)
        await retire_transaction_browser(update, context, reason="browser_replaced", preserve_refs=True)
        return

    # Bare /rekening is saldo behavior, and every other explicit command leaves
    # transaction browsing context.  Controls retire but useful numeric refs stay.
    cancel_transaction_child_actions(context)
    await retire_transaction_browser(update, context, reason=f"context_switch:{command or 'command'}", preserve_refs=True)


async def retire_transaction_browser_for_new_message(update, context) -> bool:
    """Retire browser controls when non-command text starts a new finance context."""
    cancel_transaction_child_actions(context)
    clear_transaction_child_state(context)
    return await retire_transaction_browser(update, context, reason="new_message_context", preserve_refs=True)


def _build_session(
    transactions: list[dict],
    *,
    family: str,
    title: str,
    query: dict | None = None,
    summary_label: str = "📊 Ringkasan Hasil",
    account_filter: str | None = None,
    page_size: int = PAGE_SIZE,
    bounded_note: str = "",
) -> dict:
    identities = _identities(transactions)
    return {
        "session_id": _new_sid(),
        "family": family,
        "title": str(title or "Transaksi"),
        "query": dict(query or {}),
        "summary_label": str(summary_label or "📊 Ringkasan Hasil"),
        "account_filter": str(account_filter or ""),
        "identities": identities,
        "display_records": _freeze_display_snapshot(transactions),
        "total_count": len(identities),
        "page_size": int(page_size or PAGE_SIZE),
        "current_page": 0,
        "current_view": "list",
        "current_detail_ref": None,
        "current_detail_txn_id": None,
        "status": "active",
        "bounded_note": str(bounded_note or ""),
    }


async def _refresh_transactions_for_session(session: dict) -> list[dict]:
    """Re-run the exact normalized query descriptor stored by a browser session."""
    family = str(session.get("family") or "")
    query = dict(session.get("query") or {})
    if family == "cari":
        return await run_sheets_read(
            "transaction_browser_refresh_search",
            search_transactions,
            str(query.get("keyword") or ""),
            limit=None,
        )
    if family == "last":
        return await run_sheets_read(
            "transaction_browser_refresh_last",
            get_recent_transactions,
            limit=int(query.get("limit") or 10),
            period=str(query.get("period") or "") or None,
            month=str(query.get("month") or "") or None,
        )
    if family == "rekening":
        account = str(query.get("account") or session.get("account_filter") or "")
        period_type = str(query.get("period_type") or "month")
        period_arg = "all" if period_type == "all" else (str(query.get("month") or "") or "month")
        report = await run_sheets_read(
            "transaction_browser_refresh_account",
            get_account_report,
            account,
            period_arg,
        )
        return list(report.get("transactions") or [])
    if family == "transaksi":
        kind = str(query.get("kind") or query.get("period_type") or "month")
        category = str(query.get("category") or "") or None
        account = str(query.get("account") or query.get("account_filter") or "") or None
        if kind == "day":
            report = await run_sheets_read(
                "transaction_browser_refresh_day",
                get_daily_report,
                str(query.get("date") or "") or None,
                category,
                account,
            )
        elif kind == "week":
            report = await run_sheets_read(
                "transaction_browser_refresh_week",
                get_weekly_report,
                str(query.get("date_from") or "") or None,
                category,
                account,
            )
        elif kind == "account":
            account = str(query.get("account") or session.get("account_filter") or "")
            period_type = str(query.get("period_type") or "month")
            period_arg = "all" if period_type == "all" else (str(query.get("month") or "") or "month")
            report = await run_sheets_read(
                "transaction_browser_refresh_transaksi_account",
                get_account_report,
                account,
                period_arg,
            )
        else:
            month_value = str(query.get("month") or "")
            year = month = None
            if month_value and "-" in month_value:
                year_text, month_text = month_value.split("-", 1)
                year, month = int(year_text), int(month_text)
            report = await run_sheets_read(
                "transaction_browser_refresh_month",
                get_monthly_report,
                year,
                month,
                category,
                account,
            )
        return list(report.get("transactions") or [])
    raise ValueError(f"Browser family `{family}` tidak punya refresh descriptor yang didukung.")


async def _render_browser_control(query, context, session: dict, text: str, markup) -> None:
    """Render a browser control into the current callback message and retire the older control message."""
    current_message = getattr(query, "message", None)
    current_id = getattr(current_message, "message_id", None)
    old_id = (getattr(context, "user_data", {}) or {}).get(BROWSER_CONTROL_MESSAGE_KEY)
    chat_id = getattr(current_message, "chat_id", None)
    if old_id and current_id and int(old_id) != int(current_id) and chat_id:
        try:
            await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=int(old_id), reply_markup=None)
        except Exception:
            pass
    await safe_edit_message(query, text, parse_mode="Markdown", reply_markup=markup)
    if current_id:
        context.user_data[BROWSER_CONTROL_MESSAGE_KEY] = int(current_id)


async def _render_parent_snapshot(query, context, session: dict, *, notice: str = "") -> bool:
    """Render the stored parent list/detail view without changing its frozen snapshot."""
    parent_view = dict(session.get("child_parent_view") or {})
    view = str(parent_view.get("view") or session.get("current_view") or "list")
    if view == "detail":
        txn_id = str(parent_view.get("detail_txn_id") or session.get("current_detail_txn_id") or "")
        identities = session.get("identities") or []
        ref_no = next((i + 1 for i, item in enumerate(identities) if str(item.get("id") or "") == txn_id), 0)
        if ref_no:
            txn, error = _get_snapshot_display_txn(session, ref_no)
            if txn and not error:
                session["current_view"] = "detail"
                session["current_detail_ref"] = ref_no
                session["current_detail_txn_id"] = txn_id
                _reactivate_transaction_browser_state(context)
                text = (notice + "\n\n" if notice else "") + _detail_text(ref_no, txn)
                await _render_browser_control(query, context, session, text, _detail_keyboard(session, ref_no))
                return True
    page = int(parent_view.get("page") if parent_view.get("page") is not None else session.get("current_page") or 0)
    ordered = _stored_display_records(session)
    _start, _end, pages = _page_bounds(session, page)
    page = min(max(page, 0), pages - 1)
    session["current_page"] = page
    session["current_view"] = "list"
    session["current_detail_ref"] = None
    session["current_detail_txn_id"] = None
    _reactivate_transaction_browser_state(context)
    text = (notice + "\n\n" if notice else "") + build_browser_text(session, ordered, page)
    await _render_browser_control(query, context, session, text, build_browser_keyboard(session, page))
    return True


async def _reply_parent_snapshot(message, context, session: dict, *, notice: str = "") -> bool:
    """Send the suspended parent as a fresh tracked browser message."""
    if message is None:
        return False
    chat_id = getattr(message, "chat_id", None)
    await clear_tracked_inline_keyboard(context, chat_id, BROWSER_CONTROL_MESSAGE_KEY)
    parent_view = dict(session.get("child_parent_view") or {})
    view = str(parent_view.get("view") or session.get("current_view") or "list")
    if view == "detail":
        txn_id = str(parent_view.get("detail_txn_id") or session.get("current_detail_txn_id") or "")
        identities = session.get("identities") or []
        ref_no = next((i + 1 for i, item in enumerate(identities) if str(item.get("id") or "") == txn_id), 0)
        if ref_no:
            txn, error = _get_snapshot_display_txn(session, ref_no)
            if txn and not error:
                session["current_view"] = "detail"
                session["current_detail_ref"] = ref_no
                session["current_detail_txn_id"] = txn_id
                _reactivate_transaction_browser_state(context)
                sent = await message.reply_text(
                    (notice + "\n\n" if notice else "") + _detail_text(ref_no, txn),
                    parse_mode="Markdown",
                    reply_markup=_detail_keyboard(session, ref_no),
                )
                context.user_data[BROWSER_CONTROL_MESSAGE_KEY] = getattr(sent, "message_id", None)
                return True
    ordered = _stored_display_records(session)
    page = int(parent_view.get("page") if parent_view.get("page") is not None else session.get("current_page") or 0)
    _start, _end, pages = _page_bounds(session, page)
    page = min(max(page, 0), pages - 1)
    session["current_page"] = page
    session["current_view"] = "list"
    session["current_detail_ref"] = None
    session["current_detail_txn_id"] = None
    _reactivate_transaction_browser_state(context)
    sent = await message.reply_text(
        (notice + "\n\n" if notice else "") + build_browser_text(session, ordered, page),
        parse_mode="Markdown",
        reply_markup=build_browser_keyboard(session, page),
    )
    context.user_data[BROWSER_CONTROL_MESSAGE_KEY] = getattr(sent, "message_id", None)
    return True


async def resume_transaction_browser_after_cancel(
    update_or_query,
    context,
    *,
    notice: str = "🚫 Flow transaksi dibatalkan. Tidak ada data yang disimpan.",
    preserve_current_message: bool = False,
) -> bool:
    """Resume a suspended parent browser at its exact prior list/detail view.

    ``preserve_current_message=True`` is used when a nested non-transaction
    child (for example add-category launched from saved Edit) has its own result
    message that should stay visible. The parent is then sent as a fresh tracked
    message instead of replacing that result.
    """
    session = (getattr(context, "user_data", {}) or {}).get(BROWSER_STATE_KEY)
    if not isinstance(session, dict) or str(session.get("status") or "active") != "suspended":
        return False
    query = getattr(update_or_query, "callback_query", None) or (update_or_query if hasattr(update_or_query, "message") and hasattr(update_or_query, "answer") else None)
    if query is not None and not preserve_current_message:
        return await _render_parent_snapshot(query, context, session, notice=notice)

    message = getattr(query, "message", None) if query is not None else getattr(update_or_query, "message", None)
    return await _reply_parent_snapshot(message, context, session, notice=notice)


async def _refresh_transaction_browser_after_child_inner(
    query,
    context,
    *,
    mutation: str,
    focus_txn_id: str | None = None,
    success_notice: str = "",
) -> bool:
    """Refresh a suspended parent query into a new session after successful mutation."""
    old = (getattr(context, "user_data", {}) or {}).get(BROWSER_STATE_KEY)
    if not isinstance(old, dict) or str(old.get("status") or "active") != "suspended":
        return False
    previous_page = int((old.get("child_parent_view") or {}).get("page") if (old.get("child_parent_view") or {}).get("page") is not None else old.get("current_page") or 0)
    previous_view = str((old.get("child_parent_view") or {}).get("view") or old.get("current_view") or "list")
    refreshed = await _refresh_transactions_for_session(old)
    refreshed = sorted(
        list(refreshed or []),
        key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)),
        reverse=True,
    )
    refreshed_display = enrich_transactions_with_debt_info(refreshed)
    new_session = _build_session(
        refreshed_display,
        family=str(old.get("family") or "transaksi"),
        title=str(old.get("title") or "Transaksi"),
        query=dict(old.get("query") or {}),
        summary_label=str(old.get("summary_label") or "📊 Ringkasan Hasil"),
        account_filter=str(old.get("account_filter") or "") or None,
        page_size=int(old.get("page_size") or PAGE_SIZE),
        bounded_note=str(old.get("bounded_note") or ""),
    )
    context.user_data[BROWSER_STATE_KEY] = new_session
    set_transaction_ref_context(context, new_session)

    identities = new_session.get("identities") or []
    focus_ref = next((i + 1 for i, item in enumerate(identities) if str(item.get("id") or "") == str(focus_txn_id or "")), 0)
    notice = success_notice.strip()
    if mutation == "edit" and focus_txn_id and not focus_ref:
        note = "ℹ️ Transaksi yang diedit tidak lagi cocok dengan filter browser ini. Menampilkan hasil terbaru."
        notice = (notice + "\n\n" + note).strip()

    if mutation == "edit" and focus_ref:
        target_page = (focus_ref - 1) // int(new_session.get("page_size") or PAGE_SIZE)
        if previous_view == "detail":
            txn, error = _get_snapshot_display_txn(new_session, focus_ref)
            if txn and not error:
                new_session["current_page"] = target_page
                new_session["current_view"] = "detail"
                new_session["current_detail_ref"] = focus_ref
                new_session["current_detail_txn_id"] = str(focus_txn_id)
                context.user_data[BROWSER_STATE_KEY] = new_session
                text = (notice + "\n\n" if notice else "") + _detail_text(focus_ref, txn)
                await _render_browser_control(query, context, new_session, text, _detail_keyboard(new_session, focus_ref))
                return True
        previous_page = target_page

    ordered = _stored_display_records(new_session)
    _start, _end, pages = _page_bounds(new_session, previous_page)
    page = min(max(previous_page, 0), pages - 1)
    new_session["current_page"] = page
    new_session["current_view"] = "list"
    context.user_data[BROWSER_STATE_KEY] = new_session
    text = (notice + "\n\n" if notice else "") + build_browser_text(new_session, ordered, page)
    await _render_browser_control(query, context, new_session, text, build_browser_keyboard(new_session, page))
    return True


async def refresh_transaction_browser_after_child(
    query,
    context,
    *,
    mutation: str,
    focus_txn_id: str | None = None,
    success_notice: str = "",
) -> bool:
    """Refresh a browser parent after a committed child mutation without endangering the commit.

    Browser refresh is a read/render concern that runs after the financial writer
    has already reported success.  A refresh/provider/render failure must not
    escape into the outer Sheets transaction and turn a successful mutation into
    a rollback/reconciliation attempt.  When faithful refresh is unavailable,
    retire the stale snapshot and refs explicitly instead of pretending it is
    still current.
    """
    old = (getattr(context, "user_data", {}) or {}).get(BROWSER_STATE_KEY)
    if not isinstance(old, dict) or str(old.get("status") or "active") != "suspended":
        return False
    try:
        return await _refresh_transaction_browser_after_child_inner(
            query,
            context,
            mutation=mutation,
            focus_txn_id=focus_txn_id,
            success_notice=success_notice,
        )
    except Exception:
        # The financial mutation already succeeded. Do not let a read/UI failure
        # bubble into the Sheets rollback boundary. The old mapping is unsafe to
        # present as current after an edit/delete, so retire both browser + refs.
        chat_id = getattr(getattr(query, "message", None), "chat_id", None)
        await clear_tracked_inline_keyboard(context, chat_id, BROWSER_CONTROL_MESSAGE_KEY)
        invalidate_transaction_browser(context, reason="post_mutation_refresh_failed", clear_refs=True)
        warning = (
            (success_notice.strip() + "\n\n") if success_notice.strip() else ""
        ) + (
            "⚠️ Mutation sudah berhasil, tetapi browser tidak dapat direfresh dengan aman. "
            "Snapshot lama dinonaktifkan agar tidak dianggap current."
        )
        try:
            await safe_edit_message(query, warning, parse_mode="Markdown")
        except Exception:
            pass
        return True


def _index_current_records(records: list[dict]) -> tuple[dict[int, dict], dict[str, list[dict]]]:
    by_row: dict[int, dict] = {}
    by_id: dict[str, list[dict]] = {}
    for txn in records or []:
        item = dict(txn or {})
        row = int(item.get("_row_index") or 0)
        txn_id = str(item.get("id") or "").strip()
        if row:
            by_row[row] = item
        if txn_id:
            by_id.setdefault(txn_id, []).append(item)
    return by_row, by_id


def _records_for_snapshot(session: dict, records: list[dict]) -> list[dict | None]:
    """Return records in frozen order without silently closing missing gaps."""
    by_row, by_id = _index_current_records(records)
    ordered: list[dict | None] = []
    for identity in session.get("identities") or []:
        txn_id = str(identity.get("id") or "").strip()
        row_hint = int(identity.get("row_hint") or 0)
        hinted = by_row.get(row_hint) if row_hint else None
        if hinted and str(hinted.get("id") or "").strip() == txn_id:
            ordered.append(hinted)
            continue
        matches = by_id.get(txn_id, [])
        ordered.append(matches[0] if len(matches) == 1 else None)
    return ordered


def _compact_relation_text(txn: dict) -> str:
    receivable = get_transaction_receivable_parts(txn)
    payable = get_transaction_payable_parts(txn)
    parts = []
    if receivable:
        total = sum(float(x.get("remaining_amount") or 0) for x in receivable)
        parts.append(f"Piutang {len(receivable)} · {format_rupiah(total)}")
    if payable:
        total = sum(float(x.get("remaining_amount") or 0) for x in payable)
        parts.append(f"Utang {len(payable)} · {format_rupiah(total)}")
    return " · ".join(parts)


def build_compact_transaction_line(ref_no: int, txn: dict | None) -> str:
    if not txn:
        return f"{ref_no}. ⚠️ Transaksi tidak tersedia / identity tidak unik"
    txn_type = str(txn.get("type") or "").strip().lower()
    desc = md_safe(txn.get("description") or txn.get("subject") or "-")
    category = md_safe(txn.get("category") or "-")
    account = md_safe(get_transaction_account_text(txn))
    amount = float(txn.get("amount") or 0)
    relation = _compact_relation_text(txn)
    suffix = f" · {md_safe(relation)}" if relation else ""
    if txn_type == "expense":
        net = get_net_expense_after_receivable(txn)
        amount_text = format_expense_net_gross(net, amount)
        return f"{ref_no}. ❌ {desc} — *{amount_text}* · {category} · {account}{suffix}"
    if txn_type == "income":
        return f"{ref_no}. ✅ {desc} — *{format_rupiah(amount)}* · {category} · {account}{suffix}"
    if txn_type == "transfer":
        return f"{ref_no}. 🔄 {desc} — *{format_rupiah(amount)}* · {account}{suffix}"
    return f"{ref_no}. ❓ {desc} — *{format_rupiah(amount)}* · {category} · {account}{suffix}"


def _page_bounds(session: dict, page: int) -> tuple[int, int, int]:
    total = int(session.get("total_count") or 0)
    page_size = int(session.get("page_size") or PAGE_SIZE)
    pages = max(1, ceil(total / page_size))
    page = min(max(int(page or 0), 0), pages - 1)
    start = page * page_size
    end = min(start + page_size, total)
    return start, end, pages


def build_browser_text(session: dict, ordered_records: list[dict | None], page: int) -> str:
    start, end, pages = _page_bounds(session, page)
    lines = [
        f"🧾 *{md_safe(session.get('title') or 'Transaksi')}*",
        f"*{int(session.get('total_count') or 0)} transaksi* · Halaman {page + 1}/{pages}",
    ]
    if session.get("bounded_note"):
        lines.append(f"_{md_safe(session.get('bounded_note'))}_")
    if int(session.get("total_count") or 0) == 0:
        lines.append("\n📭 Tidak ada transaksi yang cocok dengan query/filter ini.")
    current_date = None
    for idx in range(start, end):
        txn = ordered_records[idx] if idx < len(ordered_records) else None
        date_value = str((txn or {}).get("date") or "Tanpa tanggal")
        if date_value != current_date:
            lines.append(f"\n*{md_safe(format_indonesian_date_group_label(date_value))}*")
            current_date = date_value
        lines.append(build_compact_transaction_line(idx + 1, txn))
    lines.append("\n✏️ `/edit_txn` · `/edit_txn 3` · `/edit_txn 3 amount=15000`")
    lines.append("Bulk pilih: `/edit_txn 1` + `/edit_txn 3` + `/edit_txn 8` dalam satu pesan")
    lines.append("🗑 `/delete_txn` · `/delete_txn 3` · `/delete_txn 1 3 5` · `/delete_txn 1-5`")
    fields = [name for name in transaction_service.TRANSACTION_COLUMNS if name in transaction_service.EDITABLE_TRANSACTION_FIELDS]
    if fields:
        lines.append("Field edit: `" + " ".join(fields) + "`")
    return "\n".join(lines)


def build_browser_keyboard(session: dict, page: int) -> InlineKeyboardMarkup:
    sid = session["session_id"]
    start, end, pages = _page_bounds(session, page)
    number_buttons = [InlineKeyboardButton(str(idx + 1), callback_data=f"txb:{sid}:d:{idx + 1}") for idx in range(start, end)]
    keyboard = [number_buttons[i:i + 4] for i in range(0, len(number_buttons), 4)]
    prev_data = f"txb:{sid}:p:{page - 1}" if page > 0 else f"txb:{sid}:z:0"
    next_data = f"txb:{sid}:p:{page + 1}" if page + 1 < pages else f"txb:{sid}:z:0"
    keyboard.append([
        InlineKeyboardButton("◀️", callback_data=prev_data),
        InlineKeyboardButton(f"{page + 1} / {pages}", callback_data=f"txb:{sid}:z:0"),
        InlineKeyboardButton("▶️", callback_data=next_data),
    ])
    keyboard.append([InlineKeyboardButton(session.get("summary_label") or "📊 Ringkasan Hasil", callback_data=f"txb:{sid}:s:0")])
    return InlineKeyboardMarkup(keyboard)


async def _load_all_enriched() -> list[dict]:
    records = await run_sheets_read(
        "transaction_browser_records",
        transaction_service.get_transactions_with_row_index,
    )
    return enrich_transactions_with_debt_info(records or [])


async def start_transaction_browser(
    update,
    context,
    transactions: list[dict],
    *,
    family: str,
    title: str,
    query: dict | None = None,
    summary_label: str = "📊 Ringkasan Hasil",
    account_filter: str | None = None,
    bounded_note: str = "",
) -> dict:
    enriched = enrich_transactions_with_debt_info(transactions or [])
    session = _build_session(
        enriched,
        family=family,
        title=title,
        query=query,
        summary_label=summary_label,
        account_filter=account_filter,
        bounded_note=bounded_note,
    )
    context.user_data[BROWSER_STATE_KEY] = session
    set_transaction_ref_context(context, session)
    ordered = _stored_display_records(session)
    text = build_browser_text(session, ordered, 0)
    await reply_tracked_inline_keyboard(
        update,
        context,
        text,
        parse_mode="Markdown",
        reply_markup=build_browser_keyboard(session, 0),
        state_key=BROWSER_CONTROL_MESSAGE_KEY,
    )
    return session


def _selector_keyboard(state: dict) -> InlineKeyboardMarkup:
    sid = state["session_id"]
    page = int(state.get("page") or 0)
    total = len(state.get("identities") or [])
    pages = max(1, ceil(total / PAGE_SIZE))
    prev_data = f"txs:{sid}:p:{page - 1}" if page > 0 else f"txs:{sid}:z:0"
    next_data = f"txs:{sid}:p:{page + 1}" if page + 1 < pages else f"txs:{sid}:z:0"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("◀️", callback_data=prev_data),
            InlineKeyboardButton(f"{page + 1} / {pages}", callback_data=f"txs:{sid}:z:0"),
            InlineKeyboardButton("▶️", callback_data=next_data),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data=f"txs:{sid}:c:0")],
    ])


def _selector_text(state: dict, ordered: list[dict | None]) -> str:
    page = int(state.get("page") or 0)
    session = {
        "total_count": len(state.get("identities") or []),
        "page_size": PAGE_SIZE,
    }
    start, end, pages = _page_bounds(session, page)
    verb = "diedit" if state.get("mode") == "edit" else "dihapus"
    lines = [
        f"{'✏️' if state.get('mode') == 'edit' else '🗑️'} *Pilih transaksi yang akan {verb}*",
        f"Menampilkan hingga {SELECTOR_LIMIT} transaksi terbaru · Halaman {page + 1}/{pages}",
        "Ketik nomor, beberapa nomor, atau range. Contoh: `3`, `2 10 26`, `1-5`.",
    ]
    current_date = None
    for idx in range(start, end):
        txn = ordered[idx] if idx < len(ordered) else None
        date_value = str((txn or {}).get("date") or "Tanpa tanggal")
        if date_value != current_date:
            lines.append(f"\n*{md_safe(format_indonesian_date_group_label(date_value))}*")
            current_date = date_value
        lines.append(build_compact_transaction_line(idx + 1, txn))
    return "\n".join(lines)


async def start_transaction_selector(update, context, mode: str) -> None:
    transactions = await run_sheets_read(
        "transaction_selector_recent",
        transaction_service.get_recent_transactions,
        limit=SELECTOR_LIMIT,
    )
    if not transactions:
        await update.message.reply_text("📭 Belum ada transaksi untuk dipilih.")
        return
    enriched = enrich_transactions_with_debt_info(transactions)
    origin_browser_session_id = suspend_transaction_browser(context)
    state = {
        "session_id": _new_sid(),
        "mode": mode,
        "stage": "select",
        "identities": _identities(transactions),
        "display_records": _freeze_display_snapshot(enriched),
        "page": 0,
        "origin_browser_session_id": origin_browser_session_id,
    }
    context.user_data[SELECTOR_STATE_KEY] = state
    ordered = _records_for_snapshot({"identities": state["identities"]}, state["display_records"])
    await update.message.reply_text(_selector_text(state, ordered), parse_mode="Markdown", reply_markup=_selector_keyboard(state))


def _parse_selection(state: dict, text: str) -> tuple[list[int], str | None]:
    tokens = [token for token in str(text or "").replace(",", " ").split() if token]
    expanded = expand_txn_refs(tokens)
    if not expanded or any(not str(ref).isdigit() for ref in expanded):
        return [], "Ketik nomor/range dari selector, misalnya `3`, `2 10 26`, atau `1-5`."
    total = len(state.get("identities") or [])
    result: list[int] = []
    seen: set[int] = set()
    for ref in expanded:
        number = int(ref)
        if number < 1 or number > total:
            return [], f"Nomor `{number}` tidak ada di snapshot selector ini. Tidak ada target yang diproses."
        if number not in seen:
            result.append(number)
            seen.add(number)
    return result, None


async def _resolve_unique_ids(txn_ids: list[str]) -> tuple[list[dict], list[str]]:
    all_records = await run_sheets_read("transaction_selector_resolve", transaction_service.get_transactions_with_row_index)
    _, by_id = _index_current_records(all_records or [])
    resolved: list[dict] = []
    errors: list[str] = []
    for txn_id in txn_ids:
        matches = by_id.get(str(txn_id), [])
        if len(matches) != 1:
            if not matches:
                errors.append(f"`{md_code_text(txn_id)}` sudah tidak ditemukan")
            else:
                errors.append(f"`{md_code_text(txn_id)}` duplikat; mutation diblok")
            continue
        resolved.append(matches[0])
    return enrich_transactions_with_debt_info(resolved), errors


def _selected_preview_text(mode: str, refs: list[int], txns: list[dict]) -> str:
    verb = "diedit" if mode == "edit" else "dihapus"
    lines = [f"{'✏️' if mode == 'edit' else '🗑️'} *Transaksi berikut akan {verb}:*"]
    for ref, txn in zip(refs, txns):
        lines.append(build_compact_transaction_line(ref, txn))
    lines.append("\nLanjutkan ke tahap berikutnya?")
    return "\n".join(lines)


def _selected_keyboard(state: dict) -> InlineKeyboardMarkup:
    sid = state["session_id"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ Lanjut", callback_data=f"txs:{sid}:g:0")],
        [InlineKeyboardButton("❌ Batal", callback_data=f"txs:{sid}:c:0")],
    ])


async def begin_selected_targets(
    update,
    context,
    *,
    mode: str,
    refs: list[int],
    txn_ids: list[str],
    origin_browser_session_id: str | None = None,
) -> bool:
    txns, errors = await _resolve_unique_ids(txn_ids)
    if errors or len(txns) != len(txn_ids):
        text = "❌ Target tidak lagi aman dipilih:\n" + "\n".join(f"• {x}" for x in errors)
        if update.callback_query:
            await safe_edit_message(update.callback_query, text, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, parse_mode="Markdown")
        return False
    if origin_browser_session_id:
        origin_browser_session_id = suspend_transaction_browser(
            context,
            expected_session_id=origin_browser_session_id,
        )
    else:
        origin_browser_session_id = suspend_transaction_browser(context)
    state = {
        "session_id": _new_sid(),
        "mode": mode,
        "stage": "selected",
        "identities": [{"id": txn_id, "row_hint": int(txn.get("_row_index") or 0) or None} for txn_id, txn in zip(txn_ids, txns)],
        "selected_refs": list(refs),
        "selected_ids": list(txn_ids),
        "baseline_signatures": {
            txn_id: list(transaction_service.transaction_material_signature(txn))
            for txn_id, txn in zip(txn_ids, txns)
        },
        "origin_browser_session_id": origin_browser_session_id,
        "page": 0,
    }
    context.user_data[SELECTOR_STATE_KEY] = state
    text = _selected_preview_text(mode, refs, txns)
    if update.callback_query:
        await safe_edit_message(update.callback_query, text, parse_mode="Markdown", reply_markup=_selected_keyboard(state))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=_selected_keyboard(state))
    return True


async def handle_transaction_selector_text(update, context, text: str) -> bool:
    """Consume every non-command text while a transaction selector/wizard is active."""
    state = context.user_data.get(SELECTOR_STATE_KEY) or {}
    if not state:
        return False
    stage = state.get("stage")
    if stage == "select":
        refs, error = _parse_selection(state, text)
        if error:
            await update.message.reply_text(f"❌ {error}\n\nSelector tetap aktif; silakan coba lagi.", parse_mode="Markdown")
            return True
        ids = [str(state["identities"][ref - 1].get("id") or "") for ref in refs]
        await begin_selected_targets(
            update,
            context,
            mode=state.get("mode") or "edit",
            refs=refs,
            txn_ids=ids,
            origin_browser_session_id=state.get("origin_browser_session_id"),
        )
        return True
    if stage == "wizard":
        await _handle_wizard_text(update, context, state, text)
        return True
    # Selected/final-preview states only accept their buttons; still consume text
    # so it cannot fall through into the ordinary finance parser.
    await update.message.reply_text("ℹ️ Gunakan tombol pada preview aktif, atau `/cancel` untuk membatalkan.", parse_mode="Markdown")
    return True


def _wizard_prompt(state: dict, txn: dict) -> str:
    idx = int(state.get("wizard_index") or 0)
    total = len(state.get("selected_ids") or [])
    ref = state.get("selected_refs", [])[idx]
    draft = (state.get("drafts") or {}).get(str(txn.get("id") or "")) or {}
    lines = [
        f"✏️ *Edit {idx + 1} dari {total}* · ref `{ref}`",
        build_compact_transaction_line(ref, txn),
        "\nKetik satu atau beberapa `field=value` dalam satu pesan.",
        "Contoh: `amount=15000 category=Food description=\"Kopi susu\"`",
    ]
    if draft:
        lines.append("Draft saat ini: " + " ".join(f"`{k}={md_code_text(v)}`" for k, v in draft.items()))
        lines.append("Ketik `keep` untuk mempertahankan draft ini.")
    return "\n".join(lines)


def _parse_wizard_updates(text: str) -> dict:
    parts = shlex.split(str(text or "").strip())
    if not parts:
        raise ValueError("Tidak ada field yang diedit.")
    raw: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            raise ValueError("Wizard memakai format `field=value`. Anda bisa mengubah beberapa field sekaligus.")
        key, value = part.split("=", 1)
        if not key.strip() or value == "":
            raise ValueError(f"Argumen `{part}` tidak valid.")
        raw[key.strip()] = value
    return transaction_service.normalize_edit_updates(raw)


async def _start_edit_wizard(query, context, state: dict) -> None:
    state["stage"] = "wizard"
    state["wizard_index"] = 0
    state.setdefault("drafts", {})
    context.user_data[SELECTOR_STATE_KEY] = state
    txns, errors = await _resolve_unique_ids(state.get("selected_ids") or [])
    if errors or not txns:
        msg = "❌ Target berubah sebelum wizard dimulai. Tidak ada write; browser parent dikembalikan jika masih tersedia."
        context.user_data.pop(SELECTOR_STATE_KEY, None)
        if state.get("origin_browser_session_id") and await resume_transaction_browser_after_cancel(query, context, notice=msg):
            return
        await safe_edit_message(query, msg)
        return
    first = txns[0]
    expected = tuple((state.get("baseline_signatures") or {}).get(str(first.get("id") or ""), []))
    if expected and expected != transaction_service.transaction_material_signature(first):
        msg = "❌ Transaksi berubah sejak preview. Tidak ada write; browser parent dikembalikan jika masih tersedia."
        context.user_data.pop(SELECTOR_STATE_KEY, None)
        if state.get("origin_browser_session_id") and await resume_transaction_browser_after_cancel(query, context, notice=msg):
            return
        await safe_edit_message(query, msg)
        return
    await safe_edit_message(query, _wizard_prompt(state, first), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data=f"txs:{state['session_id']}:c:0")]]))


async def _handle_wizard_text(update, context, state: dict, text: str) -> None:
    idx = int(state.get("wizard_index") or 0)
    ids = state.get("selected_ids") or []
    if idx < 0 or idx >= len(ids):
        msg = "❌ Sesi wizard tidak valid. Tidak ada write; browser parent dikembalikan jika masih tersedia."
        context.user_data.pop(SELECTOR_STATE_KEY, None)
        if state.get("origin_browser_session_id") and await resume_transaction_browser_after_cancel(update, context, notice=msg):
            return
        await update.message.reply_text(msg)
        return
    txn_id = str(ids[idx])
    drafts = state.setdefault("drafts", {})
    if str(text or "").strip().lower() == "keep":
        updates = drafts.get(txn_id)
        if not updates:
            await update.message.reply_text("❌ Belum ada draft untuk transaksi ini. Masukkan `field=value`.", parse_mode="Markdown")
            return
    else:
        try:
            updates = _parse_wizard_updates(text)
        except Exception as exc:
            await update.message.reply_text(f"❌ {md_safe(str(exc))}\nWizard tetap aktif.", parse_mode="Markdown")
            return

    expected = (state.get("baseline_signatures") or {}).get(txn_id)
    preview = await run_sheets_read(
        "transaction_wizard_preview_edit",
        transaction_service.preview_edit_transaction_by_ref,
        updates=updates,
        txn_id=txn_id,
        expected_signature=expected,
    )
    if not preview.get("success"):
        await update.message.reply_text(f"❌ {md_safe(preview.get('message') or 'Preview edit gagal.')}\nTidak ada write dilakukan.", parse_mode="Markdown")
        return
    category_choice = await run_sheets_read(
        "transaction_wizard_category_choice",
        assess_edit_category_choice,
        updates,
        preview,
    )
    if category_choice:
        suggested = str(category_choice.get("suggested_category") or "").strip()
        raw = str(category_choice.get("raw_category") or "").strip()
        await update.message.reply_text(
            f"⚠️ Kategori `{md_code_text(raw)}` cocok ke existing `{md_code_text(suggested)}`.\n"
            "Untuk bulk wizard, ketik nama kategori existing itu secara exact atau gunakan single edit untuk memilih/tambah kategori. "
            "Wizard tetap aktif dan tidak ada write dilakukan.",
            parse_mode="Markdown",
        )
        return
    # High-risk relation transitions are intentionally not expressible through
    # this key=value wizard; existing relation sync semantics remain active.
    drafts[txn_id] = dict(preview.get("updates") or updates)
    state["drafts"] = drafts
    idx += 1
    state["wizard_index"] = idx
    context.user_data[SELECTOR_STATE_KEY] = state
    if idx < len(ids):
        txns, errors = await _resolve_unique_ids([ids[idx]])
        if errors or not txns:
            msg = "❌ Target berikutnya berubah/hilang. Wizard dibatalkan tanpa write."
            context.user_data.pop(SELECTOR_STATE_KEY, None)
            if state.get("origin_browser_session_id") and await resume_transaction_browser_after_cancel(update, context, notice=msg):
                return
            await update.message.reply_text(msg)
            return
        await update.message.reply_text(_wizard_prompt(state, txns[0]), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data=f"txs:{state['session_id']}:c:0")]]))
        return
    await _show_combined_edit_preview(update, context, state)


async def _show_combined_edit_preview(update, context, state: dict, *, query=None) -> None:
    entries = []
    lines = ["🧾 *Combined Final Preview*", "Belum ada financial write yang dilakukan.\n"]
    for ref, txn_id in zip(state.get("selected_refs") or [], state.get("selected_ids") or []):
        updates = (state.get("drafts") or {}).get(txn_id) or {}
        expected = (state.get("baseline_signatures") or {}).get(txn_id)
        preview = await run_sheets_read(
            "transaction_wizard_final_preview",
            transaction_service.preview_edit_transaction_by_ref,
            updates=updates,
            txn_id=txn_id,
            expected_signature=expected,
        )
        if not preview.get("success"):
            msg = "❌ Target berubah sejak staging. Batch tidak bisa disimpan; preview ulang diperlukan."
            if query:
                await safe_edit_message(query, msg)
            else:
                await update.message.reply_text(msg)
            return
        old_txn = preview.get("old_txn") or {}
        new_txn = preview.get("new_txn") or {}
        entries.append({
            "ref": ref,
            "txn_id": txn_id,
            "updates": dict(preview.get("updates") or updates),
            "expected_signature": list(expected or []),
        })
        lines.append(f"*Ref {ref}* · `{md_code_text(txn_id)}`")
        for field in (preview.get("updates") or {}).keys():
            lines.append(f"• {field}: `{md_code_text(old_txn.get(field))}` → *`{md_code_text(new_txn.get(field))}`*")
    state["stage"] = "final"
    context.user_data[SELECTOR_STATE_KEY] = state
    context.user_data[STAGED_BULK_KEY] = {
        "entries": entries,
        "origin_browser_session_id": state.get("origin_browser_session_id"),
        "selector_session_id": state.get("session_id"),
    }
    action = create_bound_preview_action("edit_txns_bulk_staged", "edit_txns_bulk_staged")
    target = action["action_id"] if action else "edit_txns_bulk_staged"
    label = "✅ Simpan" if len(entries) == 1 else "✅ Simpan Semua"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"confirm:{target}")],
        [InlineKeyboardButton("✏️ Kembali Edit", callback_data=f"txs:{state['session_id']}:r:0")],
        [InlineKeyboardButton("❌ Batal", callback_data=f"txs:{state['session_id']}:c:0")],
    ])
    text = "\n".join(lines)
    if query:
        await safe_edit_message(query, text, parse_mode="Markdown", reply_markup=markup)
    else:
        await reply_update_safely(update, text, parse_mode="Markdown", reply_markup=markup)


async def _prepare_delete_final(query, context, state: dict) -> None:
    selected_ids = list(state.get("selected_ids") or [])
    preview = await run_sheets_read(
        "transaction_selector_delete_preview",
        preview_delete_transactions_by_refs,
        txn_ids=selected_ids,
    )
    if preview.get("missing_ids") or preview.get("duplicate_ids"):
        msg = "❌ Target delete berubah/tidak unik. Tidak ada subset yang diproses."
        context.user_data.pop(SELECTOR_STATE_KEY, None)
        if state.get("origin_browser_session_id") and await resume_transaction_browser_after_cancel(query, context, notice=msg):
            return
        await safe_edit_message(query, msg)
        return
    deletable = preview.get("deletable") or []
    blocked = preview.get("blocked") or []
    if not deletable:
        msg = "🚫 Semua target valid tetapi diblok oleh dependency/debt rule. Tidak ada yang dihapus."
        context.user_data.pop(SELECTOR_STATE_KEY, None)
        if state.get("origin_browser_session_id") and await resume_transaction_browser_after_cancel(query, context, notice=msg):
            return
        await safe_edit_message(query, msg)
        return
    deletable_ids = [str(txn.get("id") or "") for txn in deletable]
    blocked_ids = [str(txn.get("id") or "") for txn in blocked]
    signatures = {str(txn.get("id") or ""): list(transaction_service.transaction_material_signature(txn)) for txn in deletable + blocked}
    dependency_signatures = {}
    for txn in deletable + blocked:
        txn_id = str(txn.get("id") or "")
        dependency_signatures[txn_id] = await run_sheets_read(
            "transaction_delete_dependency_signature",
            transaction_debt_dependency_signature,
            txn,
        )
    context.user_data["pending_delete_refs"] = {
        "row_indices": [],
        "txn_ids": deletable_ids,
        "selected_txn_ids": selected_ids,
        "expected_deletable_ids": deletable_ids,
        "expected_blocked_ids": blocked_ids,
        "expected_signatures": signatures,
        "expected_dependency_signatures": dependency_signatures,
        "origin_browser_session_id": state.get("origin_browser_session_id"),
    }
    lines = ["🗑️ *Final Preview Hapus*", f"Akan dihapus: *{len(deletable_ids)} transaksi*."]
    for txn in deletable:
        ref = (state.get("selected_refs") or [])[selected_ids.index(str(txn.get("id") or ""))]
        lines.append(build_compact_transaction_line(ref, txn))
    if blocked:
        lines.append("\n🚫 *Valid tetapi diblok business rule (tidak akan dihapus):*")
        for txn in blocked:
            reason = str(txn.get("_delete_block_reason") or "dependency/debt rule")
            lines.append(
                f"• `{md_code_text(txn.get('id'))}` · {md_safe(txn.get('description') or txn.get('subject') or '-')}"
                f" — {md_safe(reason)}"
            )
    lines.append("\nSubset di atas akan direvalidasi lagi saat konfirmasi.")
    await safe_edit_message(query, "\n".join(lines), parse_mode="Markdown", reply_markup=confirm_keyboard("delete_txns"))


def _detail_keyboard(session: dict, ref_no: int) -> InlineKeyboardMarkup:
    sid = session["session_id"]
    total = int(session.get("total_count") or 0)
    identities = session.get("identities") or []
    txn_id = str(identities[ref_no - 1].get("id") or "") if 1 <= ref_no <= len(identities) else ""
    nav = []
    if ref_no > 1:
        nav.append(InlineKeyboardButton("◀️ Previous", callback_data=f"txb:{sid}:v:{ref_no}"))
    if ref_no < total:
        nav.append(InlineKeyboardButton("▶️ Next", callback_data=f"txb:{sid}:n:{ref_no}"))
    rows = [
        [InlineKeyboardButton("✏️ Edit", callback_data=f"txb:{sid}:e:{ref_no}"), InlineKeyboardButton("🗑 Hapus", callback_data=f"txb:{sid}:x:{ref_no}")],
        [InlineKeyboardButton("📋 Copy ID", copy_text=CopyTextButton(txn_id))],
    ]
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("↩️ Kembali ke Daftar", callback_data=f"txb:{sid}:b:{ref_no}")])
    return InlineKeyboardMarkup(rows)


def _detail_text(ref_no: int, txn: dict) -> str:
    lines = [f"🧾 *Detail Transaksi #{ref_no}*"]
    lines.extend(build_transaction_display_lines(txn, include_date=True, include_id=True, note=str(txn.get("catatan") or "") or None))
    txn_id = str(txn.get("id") or "")
    if txn_id and not any(txn_id in line for line in lines):
        lines.append(f"🔖 `{md_code_text(txn_id)}`")
    return "\n".join(lines)


async def _get_unique_snapshot_txn(session: dict, ref_no: int) -> tuple[dict | None, str | None]:
    identities = session.get("identities") or []
    if ref_no < 1 or ref_no > len(identities):
        return None, "Nomor transaksi tidak ada di snapshot ini."
    txn_id = str(identities[ref_no - 1].get("id") or "")
    txns, errors = await _resolve_unique_ids([txn_id])
    if errors or not txns:
        return None, errors[0] if errors else "Transaksi tidak tersedia."
    return txns[0], None


async def _browser_summary(query, context, session: dict, *, chat_id: int | None = None) -> None:
    # Summary/chart must represent the exact frozen browser snapshot, not a
    # newly loaded population that happens to contain the same IDs.
    ordered = [txn for txn in _stored_display_records(session) if txn]
    account = str(session.get("account_filter") or "").strip() or None
    report = summarize(ordered, account)
    label = str(session.get("summary_label") or "📊 Ringkasan Hasil")
    lines = [label, ""]
    query_desc = dict(session.get("query") or {})
    period_label = str(query_desc.get("month") or "").strip()
    if not period_label and str(query_desc.get("period_type") or "").strip().lower() == "all":
        period_label = "Semua histori"
    if period_label:
        lines.append(f"🗓 Periode: *{md_safe(period_label)}*")
    category_filter = str(query_desc.get("category") or "").strip()
    if category_filter:
        lines.append(f"📁 Kategori: *{md_safe(category_filter)}*")

    if account:
        balance = None
        balance_error = ""
        try:
            balance = await run_sheets_read(
                "transaction_browser_account_balance",
                transaction_service.get_account_balance,
                account,
            )
        except Exception as exc:
            balance_error = str(exc)
        lines.append(f"🏦 Rekening: *{md_safe(account)}*")
        if balance is not None:
            lines.append(f"💰 Saldo Saat Ini: *{format_rupiah(balance)}*")
        elif balance_error:
            lines.append("⚠️ Saldo Saat Ini: *tidak tersedia*")
        lines.extend([
            f"+ Pemasukan: *{format_rupiah(report.get('total_income', 0))}*",
            f"- Pengeluaran: *{format_expense_net_gross(report.get('total_expense', 0), report.get('total_gross_expense', 0))}*",
            f"🔁 Transfer Masuk: *{format_rupiah(report.get('total_transfer_in', 0))}*",
            f"🔁 Transfer Keluar: *{format_rupiah(report.get('total_transfer_out', 0))}*",
            f"📊 Pergerakan Bersih Periode: *{format_rupiah(report.get('net', 0))}*",
            f"📝 Snapshot Aktif: *{report.get('count', 0)} transaksi*",
        ])
    else:
        lines.extend([
            f"+ Pemasukan: *{format_rupiah(report.get('total_income', 0))}*",
            f"- Pengeluaran: *{format_expense_net_gross(report.get('total_expense', 0), report.get('total_gross_expense', 0))}*",
            f"🔁 Transfer Antar Rekening: *{format_rupiah(report.get('total_transfer', 0))}* _(non-P&L)_",
            f"📊 Hasil Bersih Periode: *{format_rupiah(report.get('net', 0))}*",
            f"📝 Snapshot Aktif: *{report.get('count', 0)} transaksi*",
        ])
    text = "\n".join(lines)
    await query.message.reply_text(text, parse_mode="Markdown")

    is_monthly_browser = (
        str(session.get("family") or "") == "transaksi"
        and str(query_desc.get("kind") or query_desc.get("period_type") or "month") == "month"
        and not account
    )
    should_send_chart = bool(account) or is_monthly_browser
    if should_send_chart:
        resolved_chat_id = chat_id
        if resolved_chat_id is None:
            resolved_chat_id = getattr(getattr(query, "message", None), "chat_id", None)
        if resolved_chat_id is None:
            resolved_chat_id = getattr(getattr(getattr(query, "message", None), "chat", None), "id", None)
        if resolved_chat_id is None:
            ok, error = False, "Chat tujuan grafik tidak tersedia pada callback."
        else:
            ok, error = await send_transaction_timeseries_chart_message(
                context.bot,
                int(resolved_chat_id),
                ordered,
                str(session.get("title") or "Transaksi Bulanan"),
            )
        if not ok:
            await query.message.reply_text(
                f"⚠️ Ringkasan teks berhasil, tapi grafik time series gagal dibuat atau dikirim: {md_safe(error)}",
                parse_mode="Markdown",
            )


def is_transaction_browser_callback_data(data: str) -> bool:
    return str(data or "").startswith(("txb:", "txs:"))


async def handle_transaction_browser_callback(update, context) -> None:
    if not is_authorized(update):
        await reject_unauthorized(update)
        return
    query = update.callback_query
    data = str(query.data or "")
    try:
        prefix, sid, action, raw_value = data.split(":", 3)
    except ValueError:
        await query.answer("Callback transaction tidak valid.", show_alert=True)
        return

    if prefix == "txb":
        session = context.user_data.get(BROWSER_STATE_KEY) or {}
        if not session or sid != str(session.get("session_id") or ""):
            await query.answer("Sesi daftar ini sudah stale. Buka command transaksi lagi.", show_alert=True)
            return
        if str(session.get("status") or "active") == "suspended":
            await query.answer(
                "Edit/Hapus sedang aktif. Selesaikan atau batalkan flow itu dulu.",
                show_alert=True,
            )
            return
        if action == "z":
            await query.answer()
            return
        if action == "p":
            page = int(raw_value)
            start, end, pages = _page_bounds(session, page)
            if page < 0 or page >= pages:
                await query.answer()
                return
            await query.answer()
            session["current_page"] = page
            session["current_view"] = "list"
            session["current_detail_ref"] = None
            session["current_detail_txn_id"] = None
            context.user_data[BROWSER_STATE_KEY] = session
            ordered = _stored_display_records(session)
            await _render_browser_control(query, context, session, build_browser_text(session, ordered, page), build_browser_keyboard(session, page))
            return
        if action == "s":
            await query.answer()
            effective_chat = getattr(update, "effective_chat", None)
            await _browser_summary(
                query,
                context,
                session,
                chat_id=getattr(effective_chat, "id", None),
            )
            return
        ref_no = int(raw_value)
        if action == "v":
            ref_no -= 1
            action = "d"
        elif action == "n":
            ref_no += 1
            action = "d"
        if action == "b":
            page = (ref_no - 1) // int(session.get("page_size") or PAGE_SIZE)
            await query.answer()
            session["current_page"] = page
            session["current_view"] = "list"
            session["current_detail_ref"] = None
            session["current_detail_txn_id"] = None
            context.user_data[BROWSER_STATE_KEY] = session
            ordered = _stored_display_records(session)
            await _render_browser_control(query, context, session, build_browser_text(session, ordered, page), build_browser_keyboard(session, page))
            return
        if action == "d":
            txn, error = _get_snapshot_display_txn(session, ref_no)
            if error:
                await query.answer(error, show_alert=True)
                return
            await query.answer()
            session["current_page"] = (ref_no - 1) // int(session.get("page_size") or PAGE_SIZE)
            session["current_view"] = "detail"
            session["current_detail_ref"] = ref_no
            session["current_detail_txn_id"] = str(txn.get("id") or "")
            context.user_data[BROWSER_STATE_KEY] = session
            await _render_browser_control(query, context, session, _detail_text(ref_no, txn), _detail_keyboard(session, ref_no))
            return
        if action in {"e", "x"}:
            txn, error = await _get_unique_snapshot_txn(session, ref_no)
            if error:
                await query.answer(error, show_alert=True)
                return
            await begin_selected_targets(
                update,
                context,
                mode="edit" if action == "e" else "delete",
                refs=[ref_no],
                txn_ids=[str(txn.get("id") or "")],
                origin_browser_session_id=sid,
            )
            return
        await query.answer("Aksi transaction tidak dikenali.", show_alert=True)
        return

    state = context.user_data.get(SELECTOR_STATE_KEY) or {}
    if not state or sid != str(state.get("session_id") or ""):
        await query.answer("Selector/wizard ini sudah stale.", show_alert=True)
        return
    if action == "z":
        await query.answer()
        return
    if action == "c":
        await query.answer()
        clear_transaction_child_state(context)
        cancel_transaction_child_actions(context)
        if await resume_transaction_browser_after_cancel(query, context):
            return
        await safe_edit_message(query, "❌ Flow transaksi dibatalkan. Tidak ada mutation baru dari flow ini.")
        return
    if action == "p" and state.get("stage") == "select":
        page = int(raw_value)
        total = len(state.get("identities") or [])
        pages = max(1, ceil(total / PAGE_SIZE))
        if page < 0 or page >= pages:
            await query.answer()
            return
        await query.answer()
        state["page"] = page
        context.user_data[SELECTOR_STATE_KEY] = state
        ordered = _records_for_snapshot({"identities": state["identities"]}, list(state.get("display_records") or []))
        await safe_edit_message(query, _selector_text(state, ordered), parse_mode="Markdown", reply_markup=_selector_keyboard(state))
        return
    if action == "g" and state.get("stage") == "selected":
        if state.get("mode") == "edit":
            await _start_edit_wizard(query, context, state)
        else:
            await _prepare_delete_final(query, context, state)
        return
    if action == "r" and state.get("mode") == "edit":
        state["stage"] = "wizard"
        state["wizard_index"] = 0
        context.user_data[SELECTOR_STATE_KEY] = state
        txns, errors = await _resolve_unique_ids([state.get("selected_ids", [""])[0]])
        if errors or not txns:
            await safe_edit_message(query, "❌ Target pertama sudah berubah/hilang. Ulangi selector.")
            return
        await safe_edit_message(query, _wizard_prompt(state, txns[0]), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data=f"txs:{sid}:c:0")]]))
        return
    await query.answer("Aksi selector tidak valid untuk stage ini.", show_alert=True)
