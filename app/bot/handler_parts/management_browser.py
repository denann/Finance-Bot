"""Compact, domain-specific read-only browsers for management commands.

Each domain keeps its own session key and callback namespace.  Pure list/detail
navigation is served only from the frozen command snapshot; action callbacks
re-read the authoritative domain record before starting the existing mutation
or edit flow.
"""
from __future__ import annotations

import secrets
from types import SimpleNamespace

from app.application.external_io import run_sheets_read
from app.bot.handler_parts.common_imports import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    format_rupiah,
    is_authorized,
    md_code_text,
    md_safe,
    reject_unauthorized,
    safe_edit_message,
    send_financial_mutation_preview,
)
from app.services.debt_service import get_debt_by_id_any_status
from app.services.net_worth_service import get_assets
from app.services.pending_expense_service import find_pending_by_ref
from app.services.recurring_service import get_due_recurring_rules, get_recurring_rule_by_id


PAGE_SIZE = 6
DEBT_BROWSER_KEY = "debt_compact_browser"
PENDING_BROWSER_KEY = "pending_compact_browser"
RECURRING_BROWSER_KEY = "recurring_compact_browser"
ASSET_BROWSER_KEY = "asset_compact_browser"


def _sid() -> str:
    return secrets.token_hex(4)


def _bounds(total: int, page: int) -> tuple[int, int, int]:
    pages = max(1, (max(0, int(total)) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(int(page), 0), pages - 1)
    start = page * PAGE_SIZE
    return start, min(start + PAGE_SIZE, int(total)), pages


def _compact_button(text: str) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= 54 else text[:51] + "..."


def _is_active_value(value) -> bool:
    return str(value or "").strip().upper() in {"TRUE", "1", "YES", "Y", "ACTIVE"}


def _callback_update(update):
    """Reuse command preview helpers from a callback without inventing a new mutation path."""
    query = update.callback_query
    return SimpleNamespace(
        message=query.message,
        effective_user=getattr(update, "effective_user", None) or getattr(query, "from_user", None),
        effective_chat=getattr(update, "effective_chat", None),
    )


def _page_keyboard(prefix: str, state: dict, *, detail_buttons: list[list] | None = None) -> InlineKeyboardMarkup:
    rows = list(detail_buttons or [])
    page = int(state.get("page") or 0)
    _start, _end, pages = _bounds(len(state.get("records") or []), page)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Previous", callback_data=f"{prefix}:{state['session_id']}:p:{page - 1}"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"{prefix}:{state['session_id']}:p:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(f"Hal {page + 1}/{pages}", callback_data=f"{prefix}:{state['session_id']}:z:0")])
    return InlineKeyboardMarkup(rows)


def _list_keyboard(prefix: str, state: dict, label_fn) -> InlineKeyboardMarkup:
    records = state.get("records") or []
    start, end, _pages = _bounds(len(records), int(state.get("page") or 0))
    rows = [
        [InlineKeyboardButton(_compact_button(label_fn(i + 1, records[i])), callback_data=f"{prefix}:{state['session_id']}:d:{i}")]
        for i in range(start, end)
    ]
    return _page_keyboard(prefix, state, detail_buttons=rows)


def _selected(state: dict, raw_index: str) -> tuple[int, dict | None]:
    try:
        index = int(raw_index)
    except Exception:
        return -1, None
    records = state.get("records") or []
    if index < 0 or index >= len(records):
        return -1, None
    return index, records[index]


def _debt_record(item: dict) -> dict:
    return {key: (item or {}).get(key) for key in (
        "id", "person_name", "type", "remaining_amount", "original_amount",
        "description", "created_at", "status", "source_transaction_id",
    )}


def _pending_record(item: dict) -> dict:
    return {key: (item or {}).get(key) for key in (
        "id", "subject", "description", "amount", "category", "account",
        "due_date", "due_precision", "month", "status",
    )}


def _recurring_record(item: dict) -> dict:
    return {key: (item or {}).get(key) for key in (
        "id", "name", "type", "amount", "category", "account", "frequency",
        "day_of_month", "next_run_date", "description", "is_active",
    )}


def _asset_record(item: dict) -> dict:
    return {key: (item or {}).get(key) for key in (
        "id", "name", "category", "current_value", "quantity", "unit",
        "price_per_unit", "purchase_price", "purchase_date", "description",
        "is_active", "last_price_update",
    )}


def _debt_list_text(state: dict) -> str:
    records = state.get("records") or []
    start, end, pages = _bounds(len(records), int(state.get("page") or 0))
    title = str(state.get("title") or "Utang & Piutang Aktif")
    lines = [f"💸 *{md_safe(title)}*", f"Halaman {int(state.get('page') or 0) + 1}/{pages} · {len(records)} rincian"]
    overview = str(state.get("overview") or "").strip()
    if overview:
        lines.append(overview)
    for index in range(start, end):
        item = records[index]
        payable = str(item.get("type") or "").lower() == "payable"
        icon = "🔴" if payable else "🟢"
        direction = "Anda hutang" if payable else "Piutang"
        lines.append(
            f"{index + 1}. {icon} *{md_safe(item.get('person_name') or '-')}* · {direction} *{format_rupiah(item.get('remaining_amount', 0))}*\n"
            f"   {md_safe(item.get('description') or '-')}"
        )
    lines.append("\nPilih rincian untuk detail dan aksi Settle/Edit/Void.")
    return "\n".join(lines)


def _debt_detail_text(item: dict, number: int) -> str:
    payable = str(item.get("type") or "").lower() == "payable"
    direction = "Anda hutang" if payable else "Piutang Anda"
    return (
        f"💸 *Detail Debt #{number}*\n\n"
        f"👤 {md_safe(item.get('person_name') or '-')}\n"
        f"↔️ {direction}\n"
        f"💰 Sisa: *{format_rupiah(item.get('remaining_amount', 0))}* / awal {format_rupiah(item.get('original_amount', 0))}\n"
        f"📝 {md_safe(item.get('description') or '-')}\n"
        f"📅 {md_safe(item.get('created_at') or '-')}\n"
        f"🔖 `{md_code_text(item.get('id') or '-')}`"
    )


async def start_debt_browser(
    update,
    context,
    debts: list[dict],
    *,
    title: str = "Utang & Piutang Aktif",
    overview: str = "",
) -> None:
    records = [_debt_record(item) for item in debts or [] if str((item or {}).get("id") or "").strip()]
    if not records:
        await update.message.reply_text("✅ Tidak ada utang atau piutang aktif.")
        return
    state = {
        "session_id": _sid(),
        "records": records,
        "page": 0,
        "title": str(title or "Utang & Piutang Aktif"),
        "overview": str(overview or ""),
    }
    context.user_data[DEBT_BROWSER_KEY] = state
    await update.message.reply_text(
        _debt_list_text(state), parse_mode="Markdown",
        reply_markup=_list_keyboard("deb", state, lambda n, x: f"{n}. {x.get('person_name') or '-'} · {format_rupiah(x.get('remaining_amount', 0))}"),
    )


def _pending_due(item: dict) -> str:
    due = str(item.get("due_date") or "").strip()
    if due:
        return due
    if str(item.get("due_precision") or "").lower() == "month":
        return f"{item.get('month') or '-'} (tanggal belum pasti)"
    return "Belum pasti"


def _pending_list_text(state: dict) -> str:
    records = state.get("records") or []
    start, end, pages = _bounds(len(records), int(state.get("page") or 0))
    total = sum(float(item.get("amount", 0) or 0) for item in records)
    label = str(state.get("label") or "").strip()
    heading = f"🕒 *Pending Expense — {md_safe(label)}*" if label else "🕒 *Pending Expense*"
    lines = [heading, f"Halaman {int(state.get('page') or 0) + 1}/{pages} · {len(records)} item · *{format_rupiah(total)}*"]
    for index in range(start, end):
        item = records[index]
        lines.append(
            f"{index + 1}. 🕒 *{md_safe(item.get('subject') or 'Pending Expense')}* · *{format_rupiah(item.get('amount', 0))}*\n"
            f"   📅 {md_safe(_pending_due(item))} · 🏦 {md_safe(item.get('account') or '-')}"
        )
    lines.append("\nPilih item untuk detail lalu Paid atau Cancel.")
    return "\n".join(lines)


def _pending_detail_text(item: dict, number: int) -> str:
    return (
        f"🕒 *Detail Pending #{number}*\n\n"
        f"📝 {md_safe(item.get('subject') or item.get('description') or '-')}\n"
        f"💰 *{format_rupiah(item.get('amount', 0))}*\n"
        f"📅 {md_safe(_pending_due(item))}\n"
        f"📁 {md_safe(item.get('category') or '-')}\n"
        f"🏦 {md_safe(item.get('account') or '-')}\n"
        f"Status: `{md_code_text(item.get('status') or 'pending')}`\n"
        f"🔖 `{md_code_text(item.get('id') or '-')}`"
    )


async def start_pending_browser(update, context, items: list[dict], *, label: str = "") -> None:
    records = [_pending_record(item) for item in items or [] if str((item or {}).get("id") or "").strip()]
    if not records:
        suffix = f" untuk {label}" if label else ""
        await update.message.reply_text(f"📭 Belum ada pending expense aktif{suffix}.")
        return
    state = {"session_id": _sid(), "records": records, "page": 0, "label": str(label or "")}
    context.user_data[PENDING_BROWSER_KEY] = state
    await update.message.reply_text(
        _pending_list_text(state), parse_mode="Markdown",
        reply_markup=_list_keyboard("pen", state, lambda n, x: f"{n}. {x.get('subject') or 'Pending'} · {format_rupiah(x.get('amount', 0))}"),
    )


def _recurring_list_text(state: dict) -> str:
    records = state.get("records") or []
    start, end, pages = _bounds(len(records), int(state.get("page") or 0))
    lines = ["🔁 *Recurring Transaction*", f"Halaman {int(state.get('page') or 0) + 1}/{pages} · {len(records)} rule"]
    for index in range(start, end):
        item = records[index]
        active = str(item.get("is_active") or "").upper() == "TRUE"
        lines.append(
            f"{index + 1}. {'✅' if active else '⛔'} *{md_safe(item.get('name') or '-')}* · *{format_rupiah(item.get('amount', 0))}*\n"
            f"   {md_safe(item.get('frequency') or '-')} · next `{md_code_text(item.get('next_run_date') or '-')}`"
        )
    lines.append("\nPilih rule untuk detail dan aksi Edit/Off/Run.")
    return "\n".join(lines)


def _recurring_detail_text(item: dict, number: int) -> str:
    active = str(item.get("is_active") or "").upper() == "TRUE"
    return (
        f"🔁 *Detail Recurring #{number}*\n\n"
        f"{'✅ Aktif' if active else '⛔ Nonaktif'} · {md_safe(item.get('type') or '-')}\n"
        f"📌 *{md_safe(item.get('name') or '-')}*\n"
        f"💰 *{format_rupiah(item.get('amount', 0))}* · {md_safe(item.get('category') or '-')}\n"
        f"🏦 {md_safe(item.get('account') or '-')}\n"
        f"🔁 {md_safe(item.get('frequency') or '-')} tanggal {md_safe(item.get('day_of_month') or '-')}\n"
        f"📅 Next run: `{md_code_text(item.get('next_run_date') or '-')}`\n"
        f"📝 {md_safe(item.get('description') or '-')}\n"
        f"🔖 `{md_code_text(item.get('id') or '-')}`"
    )


async def start_recurring_browser(update, context, rules: list[dict]) -> None:
    records = [_recurring_record(item) for item in rules or [] if str((item or {}).get("id") or "").strip()]
    if not records:
        await update.message.reply_text("📭 Belum ada recurring transaction.")
        return
    state = {"session_id": _sid(), "records": records, "page": 0}
    context.user_data[RECURRING_BROWSER_KEY] = state
    await update.message.reply_text(
        _recurring_list_text(state), parse_mode="Markdown",
        reply_markup=_list_keyboard("recb", state, lambda n, x: f"{n}. {x.get('name') or '-'} · {format_rupiah(x.get('amount', 0))}"),
    )


def _asset_list_text(state: dict) -> str:
    records = state.get("records") or []
    start, end, pages = _bounds(len(records), int(state.get("page") or 0))
    total = sum(float(item.get("current_value", 0) or 0) for item in records)
    lines = ["📦 *Daftar Aset Aktif*", f"Halaman {int(state.get('page') or 0) + 1}/{pages} · {len(records)} aset · *{format_rupiah(total)}*"]
    for index in range(start, end):
        item = records[index]
        lines.append(
            f"{index + 1}. 📦 *{md_safe(item.get('name') or '-')}* · *{format_rupiah(item.get('current_value', 0))}*\n"
            f"   {md_safe(item.get('category') or '-')}"
        )
    lines.append("\nPilih aset untuk detail lalu Update atau Off.")
    return "\n".join(lines)


def _asset_detail_text(item: dict, number: int) -> str:
    quantity = str(item.get("quantity") or "").strip()
    unit = str(item.get("unit") or "").strip()
    quantity_line = f"\n🔢 {md_safe(quantity)} {md_safe(unit)}" if quantity and unit else ""
    price_line = f"\n🏷️ {format_rupiah(item.get('price_per_unit', 0))}/{md_safe(unit)}" if quantity and unit else ""
    return (
        f"📦 *Detail Aset #{number}*\n\n"
        f"📌 *{md_safe(item.get('name') or '-')}*\n"
        f"📁 {md_safe(item.get('category') or '-')}"
        f"{quantity_line}{price_line}\n"
        f"💰 Nilai saat ini: *{format_rupiah(item.get('current_value', 0))}*\n"
        f"📝 {md_safe(item.get('description') or '-')}\n"
        f"🔖 `{md_code_text(item.get('id') or '-')}`"
    )


async def start_asset_browser(update, context, assets: list[dict]) -> None:
    records = [_asset_record(item) for item in assets or [] if str((item or {}).get("id") or "").strip()]
    if not records:
        await update.message.reply_text("📭 Belum ada aset aktif.")
        return
    state = {"session_id": _sid(), "records": records, "page": 0}
    context.user_data[ASSET_BROWSER_KEY] = state
    await update.message.reply_text(
        _asset_list_text(state), parse_mode="Markdown",
        reply_markup=_list_keyboard("asb", state, lambda n, x: f"{n}. {x.get('name') or '-'} · {format_rupiah(x.get('current_value', 0))}"),
    )


def is_management_browser_callback_data(data: str) -> bool:
    return str(data or "").startswith(("deb:", "pen:", "recb:", "asb:"))


async def _handle_debt(update, context, sid: str, action: str, raw: str) -> None:
    query = update.callback_query
    state = context.user_data.get(DEBT_BROWSER_KEY) or {}
    if not state or sid != str(state.get("session_id") or ""):
        await query.answer("Sesi debt browser sudah stale. Jalankan /hutang lagi.", show_alert=True)
        return
    if action == "z":
        await query.answer(); return
    if action == "p":
        page = int(raw); _start, _end, pages = _bounds(len(state.get("records") or []), page)
        if page < 0 or page >= pages:
            await query.answer(); return
        await query.answer(); state["page"] = page
        await safe_edit_message(query, _debt_list_text(state), parse_mode="Markdown", reply_markup=_list_keyboard("deb", state, lambda n, x: f"{n}. {x.get('person_name') or '-'} · {format_rupiah(x.get('remaining_amount', 0))}")); return
    index, item = _selected(state, raw)
    if not item:
        await query.answer("Rincian debt tidak ada di snapshot ini.", show_alert=True); return
    if action == "d":
        await query.answer()
        rows = [[InlineKeyboardButton("💸 Settle", callback_data=f"deb:{sid}:s:{index}"), InlineKeyboardButton("✏️ Edit", callback_data=f"deb:{sid}:e:{index}"), InlineKeyboardButton("🗑 Void", callback_data=f"deb:{sid}:v:{index}")], [InlineKeyboardButton("↩️ Kembali", callback_data=f"deb:{sid}:b:{index}")]]
        await safe_edit_message(query, _debt_detail_text(item, index + 1), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows)); return
    if action == "b":
        await query.answer(); state["page"] = index // PAGE_SIZE
        await safe_edit_message(query, _debt_list_text(state), parse_mode="Markdown", reply_markup=_list_keyboard("deb", state, lambda n, x: f"{n}. {x.get('person_name') or '-'} · {format_rupiah(x.get('remaining_amount', 0))}")); return
    if action not in {"s", "e", "v"}:
        await query.answer("Aksi debt tidak dikenali.", show_alert=True); return

    await query.answer()
    debt_id = str(item.get("id") or "")
    _row, current = await run_sheets_read("management_debt_revalidate", get_debt_by_id_any_status, debt_id)
    if not current or float(current.get("remaining_amount", 0) or 0) <= 0:
        await query.message.reply_text("❌ Debt sudah berubah/lunas. Buka /hutang lagi sebelum melakukan aksi."); return
    if action == "e":
        await query.message.reply_text(
            "✏️ *Edit debt*\n\n"
            f"Target sudah direvalidasi: `{md_code_text(debt_id)}`\n"
            f"Gunakan misalnya:\n`/debt_edit {md_code_text(debt_id)} nominal 100k`\n"
            f"`/debt_edit {md_code_text(debt_id)} deskripsi Koreksi`",
            parse_mode="Markdown",
        ); return

    from app.bot.handler_parts.command_handlers import debt_settle_handler, debt_void_handler
    proxy = _callback_update(update)
    old_args = list(getattr(context, "args", []) or [])
    try:
        if action == "v":
            context.args = [debt_id]
            await debt_void_handler(proxy, context)
        else:
            person = str(current.get("person_name") or item.get("person_name") or "").strip()
            context.user_data["last_debt_map"] = {"1": {"debt_id": debt_id, "person_name": person, "type": current.get("type"), "remaining_amount": current.get("remaining_amount")}}
            context.user_data["last_debt_person"] = person
            context.args = [person, "1"]
            await debt_settle_handler(proxy, context)
    finally:
        context.args = old_args


async def _handle_pending(update, context, sid: str, action: str, raw: str) -> None:
    query = update.callback_query
    state = context.user_data.get(PENDING_BROWSER_KEY) or {}
    if not state or sid != str(state.get("session_id") or ""):
        await query.answer("Sesi pending browser sudah stale. Jalankan /pending lagi.", show_alert=True); return
    if action == "z": await query.answer(); return
    if action == "p":
        page = int(raw); _s, _e, pages = _bounds(len(state.get("records") or []), page)
        if page < 0 or page >= pages: await query.answer(); return
        await query.answer(); state["page"] = page
        await safe_edit_message(query, _pending_list_text(state), parse_mode="Markdown", reply_markup=_list_keyboard("pen", state, lambda n, x: f"{n}. {x.get('subject') or 'Pending'} · {format_rupiah(x.get('amount', 0))}")); return
    index, item = _selected(state, raw)
    if not item: await query.answer("Item pending tidak ada di snapshot ini.", show_alert=True); return
    if action == "d":
        await query.answer(); rows = [[InlineKeyboardButton("✅ Paid", callback_data=f"pen:{sid}:a:{index}"), InlineKeyboardButton("❌ Cancel", callback_data=f"pen:{sid}:c:{index}")], [InlineKeyboardButton("↩️ Kembali", callback_data=f"pen:{sid}:b:{index}")]]
        await safe_edit_message(query, _pending_detail_text(item, index + 1), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows)); return
    if action == "b":
        await query.answer(); state["page"] = index // PAGE_SIZE
        await safe_edit_message(query, _pending_list_text(state), parse_mode="Markdown", reply_markup=_list_keyboard("pen", state, lambda n, x: f"{n}. {x.get('subject') or 'Pending'} · {format_rupiah(x.get('amount', 0))}")); return
    if action not in {"a", "c"}: await query.answer("Aksi pending tidak dikenali.", show_alert=True); return
    await query.answer()
    pending_id = str(item.get("id") or "")
    _row, current = await run_sheets_read("management_pending_revalidate", find_pending_by_ref, pending_id)
    status = str((current or {}).get("status") or "pending").lower()
    if not current or status in {"paid", "cancelled", "canceled", "done", "selesai"}:
        await query.message.reply_text("❌ Pending sudah berubah/selesai. Jalankan /pending lagi."); return
    if action == "a":
        account = str(current.get("account") or "").strip()
        if not account:
            await query.message.reply_text(f"❌ Rekening belum diketahui. Gunakan `/pending_paid {md_code_text(pending_id)} BRI`.", parse_mode="Markdown"); return
        operation, payload, title = "pending_paid", {"pending_id": pending_id, "account": account}, "tandai pending paid"
    else:
        operation, payload, title = "pending_cancel", {"pending_id": pending_id}, "batalkan pending expense"
    await send_financial_mutation_preview(
        _callback_update(update), context, operation=operation, payload=payload,
        preview_text=(f"🧾 *Preview final — {title}*\n\n🔖 `{md_code_text(pending_id)}`\n📝 {md_safe(current.get('description') or current.get('subject') or '-')}\n💰 *{format_rupiah(current.get('amount', 0))}*" + (f"\n🏦 *{md_safe(payload.get('account'))}*" if payload.get("account") else "") + "\n\nSimpan perubahan ini atau batal?"),
    )


async def _handle_recurring(update, context, sid: str, action: str, raw: str) -> None:
    query = update.callback_query
    state = context.user_data.get(RECURRING_BROWSER_KEY) or {}
    if not state or sid != str(state.get("session_id") or ""):
        await query.answer("Sesi recurring browser sudah stale. Jalankan /recurring lagi.", show_alert=True); return
    if action == "z": await query.answer(); return
    if action == "p":
        page = int(raw); _s, _e, pages = _bounds(len(state.get("records") or []), page)
        if page < 0 or page >= pages: await query.answer(); return
        await query.answer(); state["page"] = page
        await safe_edit_message(query, _recurring_list_text(state), parse_mode="Markdown", reply_markup=_list_keyboard("recb", state, lambda n, x: f"{n}. {x.get('name') or '-'} · {format_rupiah(x.get('amount', 0))}")); return
    index, item = _selected(state, raw)
    if not item: await query.answer("Recurring rule tidak ada di snapshot ini.", show_alert=True); return
    if action == "d":
        await query.answer()
        action_row = [InlineKeyboardButton("✏️ Edit", callback_data=f"recb:{sid}:e:{index}")]
        rows = [action_row]
        if _is_active_value(item.get("is_active")):
            action_row.append(InlineKeyboardButton("⛔ Off", callback_data=f"recb:{sid}:o:{index}"))
            rows.append([InlineKeyboardButton("▶️ Run Semua Jatuh Tempo", callback_data=f"recb:{sid}:r:{index}")])
        rows.append([InlineKeyboardButton("↩️ Kembali", callback_data=f"recb:{sid}:b:{index}")])
        await safe_edit_message(query, _recurring_detail_text(item, index + 1), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows)); return
    if action == "b":
        await query.answer(); state["page"] = index // PAGE_SIZE
        await safe_edit_message(query, _recurring_list_text(state), parse_mode="Markdown", reply_markup=_list_keyboard("recb", state, lambda n, x: f"{n}. {x.get('name') or '-'} · {format_rupiah(x.get('amount', 0))}")); return
    if action not in {"e", "o", "r"}: await query.answer("Aksi recurring tidak dikenali.", show_alert=True); return
    await query.answer()
    rule_id = str(item.get("id") or "")
    current = await run_sheets_read("management_recurring_revalidate", get_recurring_rule_by_id, rule_id)
    if not current:
        await query.message.reply_text("❌ Recurring rule sudah berubah/hilang. Jalankan /recurring lagi."); return
    if action in {"o", "r"} and not _is_active_value(current.get("is_active")):
        await query.message.reply_text("❌ Recurring rule sudah nonaktif. Jalankan /recurring lagi sebelum melakukan aksi."); return
    if action == "e":
        await query.message.reply_text(
            "✏️ *Edit recurring*\n\n"
            f"Target sudah direvalidasi: `{md_code_text(rule_id)}`\n"
            f"Gunakan misalnya:\n`/recurring_edit {md_code_text(rule_id)} amount=75000 day=10`",
            parse_mode="Markdown",
        ); return
    if action == "o":
        await send_financial_mutation_preview(
            _callback_update(update), context, operation="recurring_off", payload={"rule_id": rule_id},
            preview_text=f"🧾 *Preview final — nonaktifkan recurring*\n\n📌 {md_safe(current.get('name') or '-')}\n🔖 `{md_code_text(rule_id)}`\n\nSimpan perubahan ini atau batal?",
        ); return
    due = await run_sheets_read("management_recurring_due_revalidate", get_due_recurring_rules)
    await send_financial_mutation_preview(
        _callback_update(update), context, operation="recurring_run", payload={},
        preview_text=f"🧾 *Preview final — jalankan recurring jatuh tempo*\n\nRule jatuh tempo saat ini: *{len(due)}*\nAksi ini menjalankan semua rule yang memang jatuh tempo, bukan hanya rule detail di atas.\n\nSimpan atau batal?",
    )


async def _handle_asset(update, context, sid: str, action: str, raw: str) -> None:
    query = update.callback_query
    state = context.user_data.get(ASSET_BROWSER_KEY) or {}
    if not state or sid != str(state.get("session_id") or ""):
        await query.answer("Sesi asset browser sudah stale. Jalankan /assets lagi.", show_alert=True); return
    if action == "z": await query.answer(); return
    if action == "p":
        page = int(raw); _s, _e, pages = _bounds(len(state.get("records") or []), page)
        if page < 0 or page >= pages: await query.answer(); return
        await query.answer(); state["page"] = page
        await safe_edit_message(query, _asset_list_text(state), parse_mode="Markdown", reply_markup=_list_keyboard("asb", state, lambda n, x: f"{n}. {x.get('name') or '-'} · {format_rupiah(x.get('current_value', 0))}")); return
    index, item = _selected(state, raw)
    if not item: await query.answer("Aset tidak ada di snapshot ini.", show_alert=True); return
    if action == "d":
        await query.answer(); rows = [[InlineKeyboardButton("✏️ Update", callback_data=f"asb:{sid}:u:{index}"), InlineKeyboardButton("⛔ Off", callback_data=f"asb:{sid}:o:{index}")], [InlineKeyboardButton("↩️ Kembali", callback_data=f"asb:{sid}:b:{index}")]]
        await safe_edit_message(query, _asset_detail_text(item, index + 1), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows)); return
    if action == "b":
        await query.answer(); state["page"] = index // PAGE_SIZE
        await safe_edit_message(query, _asset_list_text(state), parse_mode="Markdown", reply_markup=_list_keyboard("asb", state, lambda n, x: f"{n}. {x.get('name') or '-'} · {format_rupiah(x.get('current_value', 0))}")); return
    if action not in {"u", "o"}: await query.answer("Aksi asset tidak dikenali.", show_alert=True); return
    await query.answer()
    asset_id = str(item.get("id") or "")
    assets = await run_sheets_read("management_asset_revalidate", get_assets, active_only=False, refresh_gold=False)
    current = next((row for row in assets or [] if str(row.get("id") or "") == asset_id), None)
    if not current:
        await query.message.reply_text("❌ Aset sudah berubah/hilang. Jalankan /assets lagi."); return
    if action == "o" and not _is_active_value(current.get("is_active")):
        await query.message.reply_text("❌ Aset sudah nonaktif. Jalankan /assets lagi sebelum melakukan aksi."); return
    if action == "u":
        await query.message.reply_text(
            "✏️ *Update aset*\n\n"
            f"Target sudah direvalidasi: `{md_code_text(asset_id)}`\n"
            f"Gunakan misalnya:\n`/asset_update {md_code_text(asset_id)} amount=9000000`\n"
            f"`/asset_update {md_code_text(asset_id)} unit_price=2420000`",
            parse_mode="Markdown",
        ); return
    await send_financial_mutation_preview(
        _callback_update(update), context, operation="asset_off", payload={"asset_id": asset_id},
        preview_text=f"🧾 *Preview final — nonaktifkan aset*\n\n📌 {md_safe(current.get('name') or '-')}\n🔖 `{md_code_text(asset_id)}`\n\nSimpan perubahan ini atau batal?",
    )


async def handle_management_browser_callback(update, context) -> None:
    if not is_authorized(update):
        await reject_unauthorized(update); return
    query = update.callback_query
    try:
        prefix, sid, action, raw = str(query.data or "").split(":", 3)
    except ValueError:
        await query.answer("Callback management tidak valid.", show_alert=True); return
    if prefix == "deb":
        await _handle_debt(update, context, sid, action, raw)
    elif prefix == "pen":
        await _handle_pending(update, context, sid, action, raw)
    elif prefix == "recb":
        await _handle_recurring(update, context, sid, action, raw)
    elif prefix == "asb":
        await _handle_asset(update, context, sid, action, raw)
    else:
        await query.answer("Callback management tidak dikenali.", show_alert=True)
