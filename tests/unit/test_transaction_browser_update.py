import asyncio
import importlib
import sys
import types
from contextlib import contextmanager

import pytest


class Button:
    def __init__(self, text, callback_data=None, **kwargs):
        self.text = text
        self.callback_data = callback_data
        for key, value in kwargs.items():
            setattr(self, key, value)


class CopyTextButton:
    def __init__(self, text):
        self.text = text


class Markup:
    def __init__(self, rows):
        self.inline_keyboard = rows

telegram = types.ModuleType("telegram")
telegram.CopyTextButton = CopyTextButton

common = types.ModuleType("app.bot.handler_parts.common_imports")
common.InlineKeyboardButton = Button
common.InlineKeyboardMarkup = Markup
common.build_transaction_display_lines = lambda txn, **k: [f"ID {txn.get('id')}"]
common.enrich_transactions_with_debt_info = lambda rows: list(rows or [])
common.format_expense_net_gross = lambda net, gross: f"NET{int(net)} (GROSS{int(gross)})" if net != gross else f"Rp{int(gross)}"
common.format_indonesian_date_group_label = lambda value: f"DATE:{value}"
common.format_rupiah = lambda value: f"Rp{int(float(value or 0))}"
common.get_net_expense_after_receivable = lambda txn: float(txn.get("net", txn.get("amount", 0)) or 0)
common.get_transaction_account_text = lambda txn: (
    f"{txn.get('account')} → {txn.get('to_account')}" if txn.get("type") == "transfer" else str(txn.get("account") or "-")
)
common.get_transaction_payable_parts = lambda txn: txn.get("payables", [])
common.get_transaction_receivable_parts = lambda txn: txn.get("receivables", [])
common.get_account_report = lambda account, period="month": {"transactions": []}
common.get_daily_report = lambda date=None, category=None, account=None: {"transactions": []}
common.get_monthly_report = lambda year=None, month=None, category=None, account=None: {"transactions": []}
common.get_recent_transactions = lambda limit=10, period=None, month=None: []
common.get_weekly_report = lambda date=None, category=None, account=None: {"transactions": []}
common.search_transactions = lambda keyword, limit=None: []
def _summarize(rows, account=None):
    income = expense = gross = transfer = transfer_in = transfer_out = 0.0
    for txn in rows or []:
        amount = float(txn.get("amount", 0) or 0)
        kind = str(txn.get("type") or "")
        if kind == "income": income += amount
        elif kind == "expense":
            gross += amount
            expense += float(txn.get("net", amount) or 0)
        elif kind == "transfer":
            transfer += amount
            if account:
                if str(txn.get("account") or "").lower() == str(account).lower(): transfer_out += amount
                if str(txn.get("to_account") or "").lower() == str(account).lower(): transfer_in += amount
    net = income + transfer_in - expense - transfer_out if account else income - expense
    return {"total_income": income, "total_expense": expense, "total_gross_expense": gross,
            "total_transfer": transfer, "total_transfer_in": transfer_in, "total_transfer_out": transfer_out,
            "net": net, "count": len(rows or [])}
common.summarize = _summarize
common.is_authorized = lambda update: True
common.md_code_text = lambda value: str(value or "")
common.md_safe = lambda value: str(value or "")
common.preview_delete_transactions_by_refs = lambda **kwargs: {"deletable": [], "blocked": [], "missing_ids": [], "duplicate_ids": []}
common.reject_unauthorized = lambda update: None
async def _safe_edit(*a, **k): return None
common.safe_edit_message = _safe_edit
async def _clear_tracked(*a, **k): return False
common.clear_tracked_inline_keyboard = _clear_tracked
async def _reply_update(update, text, parse_mode=None, reply_markup=None, **kwargs):
    sent = await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    from app.bot.pending_actions import bind_current_action_message
    bind_current_action_message(reply_markup, getattr(sent, "message_id", None))
    return sent
common.reply_update_safely = _reply_update
async def _reply_tracked(update, context, text, parse_mode=None, reply_markup=None, state_key=None, **kwargs):
    sent = await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    if state_key and getattr(sent, "message_id", None):
        context.user_data[state_key] = sent.message_id
    return sent
common.reply_tracked_inline_keyboard = _reply_tracked

router = types.ModuleType("app.bot.handler_parts.command_router")
def expand(refs):
    out=[]
    for token in refs:
        if "-" in token and all(x.isdigit() for x in token.split("-",1)):
            a,b=map(int,token.split("-",1)); out.extend(str(x) for x in range(a,b+1))
        else: out.append(token)
    return out
router.expand_txn_refs = expand

keyboards = types.ModuleType("app.bot.keyboards")
keyboards.confirm_keyboard = lambda target: Markup([[Button("save", f"confirm:{target}")]])

external = types.ModuleType("app.application.external_io")
async def read(_name, fn, *args, **kwargs): return fn(*args, **kwargs)
external.run_sheets_read = read

txn_service = types.ModuleType("app.services.transaction_service")
txn_service.TRANSACTION_COLUMNS = ["date", "type", "amount", "category", "account", "description"]
txn_service.EDITABLE_TRANSACTION_FIELDS = set(txn_service.TRANSACTION_COLUMNS)
txn_service.transaction_material_signature = lambda txn: tuple(str(txn.get(k, "")) for k in txn_service.TRANSACTION_COLUMNS)
txn_service.get_transactions_with_row_index = lambda: []
txn_service.get_account_balance = lambda account: 0
txn_service.get_recent_transactions = lambda limit=100: []
txn_service.normalize_edit_updates = lambda updates: dict(updates)
txn_service.preview_edit_transaction_by_ref = lambda **kwargs: {"success": True, "updates": kwargs.get("updates", {}), "old_txn": {}, "new_txn": {}}
txn_service.preview_delete_transactions_by_refs = lambda **kwargs: {"deletable": [], "blocked": [], "missing_ids": [], "duplicate_ids": []}

debt_service = types.ModuleType("app.services.debt_service")
debt_service.transaction_debt_dependency_signature = lambda txn: ()

resolver_service = types.ModuleType("app.services.resolver_service")
resolver_service.assess_edit_category_choice = lambda updates, preview: None

transaction_chart = types.ModuleType("app.bot.handler_parts.transaction_chart")
async def _send_chart(bot, chat_id, transactions, title): return True, ""
transaction_chart.send_transaction_timeseries_chart_message = _send_chart

_MISSING = object()


@contextmanager
def _temporary_modules(replacements):
    """Install import stubs only while loading the browser module under test."""
    saved_modules = {}
    saved_attrs = {}
    try:
        for name, module in replacements.items():
            saved_modules[name] = sys.modules.get(name, _MISSING)
            parent_name, _, attr_name = name.rpartition(".")
            if parent_name:
                parent = importlib.import_module(parent_name)
                saved_attrs[name] = (parent, getattr(parent, attr_name, _MISSING))
                setattr(parent, attr_name, module)
            sys.modules[name] = module
        yield
    finally:
        for name in reversed(tuple(replacements)):
            parent_attr = saved_attrs.get(name)
            if parent_attr:
                parent, old_attr = parent_attr
                attr_name = name.rpartition(".")[2]
                if old_attr is _MISSING:
                    if getattr(parent, attr_name, _MISSING) is replacements[name]:
                        delattr(parent, attr_name)
                else:
                    setattr(parent, attr_name, old_attr)
            old_module = saved_modules[name]
            if old_module is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old_module


_BROWSER_MODULE = "app.bot.handler_parts.transaction_browser"
_BROWSER_STUBS = {
    "telegram": telegram,
    "app.bot.handler_parts.common_imports": common,
    "app.bot.handler_parts.command_router": router,
    "app.bot.keyboards": keyboards,
    "app.application.external_io": external,
    "app.services.transaction_service": txn_service,
    "app.services.debt_service": debt_service,
    "app.services.resolver_service": resolver_service,
    "app.bot.handler_parts.transaction_chart": transaction_chart,
}

# Load the module under test against local doubles, then restore *every* replaced
# sys.modules entry and parent-package attribute before other test modules collect.
with _temporary_modules(_BROWSER_STUBS):
    prior_browser = sys.modules.pop(_BROWSER_MODULE, _MISSING)
    browser_parent = importlib.import_module("app.bot.handler_parts")
    prior_browser_attr = getattr(browser_parent, "transaction_browser", _MISSING)
    if prior_browser_attr is not _MISSING:
        delattr(browser_parent, "transaction_browser")
    loaded_browser = _MISSING
    try:
        loaded_browser = importlib.import_module(_BROWSER_MODULE)
        browser = loaded_browser
    finally:
        if prior_browser is _MISSING:
            sys.modules.pop(_BROWSER_MODULE, None)
        else:
            sys.modules[_BROWSER_MODULE] = prior_browser
        if prior_browser_attr is _MISSING:
            if getattr(browser_parent, "transaction_browser", _MISSING) is loaded_browser:
                if hasattr(browser_parent, "transaction_browser"):
                    delattr(browser_parent, "transaction_browser")
        else:
            browser_parent.transaction_browser = prior_browser_attr


def _txns(n=32):
    return [
        {"id": f"txn_{i:02d}", "_row_index": i + 1, "date": "2026-08-08", "type": "expense", "amount": i * 1000, "net": i * 1000,
         "category": "Food", "account": "Cash", "description": f"Item {i}"}
        for i in range(1, n + 1)
    ]


def test_global_numbering_page_four_keeps_25_to_32():
    session = browser._build_session(_txns(), family="transaksi", title="August")
    ordered = browser._records_for_snapshot(session, _txns())
    text = browser.build_browser_text(session, ordered, 3)
    markup = browser.build_browser_keyboard(session, 3)

    assert "25." in text and "32." in text
    callbacks = [b.callback_data for row in markup.inline_keyboard[:2] for b in row]
    assert callbacks[0].endswith(":d:25")
    assert callbacks[-1].endswith(":d:32")


def test_cross_page_selection_all_invalid_and_duplicate_normalization():
    state = {"identities": browser._identities(_txns())}
    assert browser._parse_selection(state, "26") == ([26], None)
    assert browser._parse_selection(state, "2 10 26") == ([2, 10, 26], None)
    assert browser._parse_selection(state, "2 2 10 10") == ([2, 10], None)
    refs, error = browser._parse_selection(state, "2 10 99")
    assert refs == [] and "Tidak ada target" in error
    refs, error = browser._parse_selection(state, "kopi")
    assert refs == [] and "nomor/range" in error


def test_compact_rows_keep_net_gross_relation_and_transfer_direction():
    split = _txns(1)[0] | {"amount": 890000, "net": 420000, "receivables": [{"remaining_amount": 470000}]}
    line = browser.build_compact_transaction_line(1, split)
    assert "NET420000 (GROSS890000)" in line
    assert "Piutang 1" in line
    transfer = {"id": "t", "type": "transfer", "amount": 100000, "account": "BCA", "to_account": "DANA", "description": "Pindah"}
    assert "BCA → DANA" in browser.build_compact_transaction_line(2, transfer)


def test_new_browser_reference_context_replaces_legacy_map_without_full_records():
    class C: user_data = {"last_txn_map": {"1": {"row_index": 5}}}
    session = browser._build_session(_txns(3), family="cari", title="kopi", query={"keyword": "kopi"})
    browser.set_transaction_ref_context(C, session)
    assert "last_txn_map" not in C.user_data
    assert C.user_data[browser.REF_CONTEXT_KEY]["ordered_ids"] == ["txn_01", "txn_02", "txn_03"]
    assert "identities" not in C.user_data[browser.REF_CONTEXT_KEY]


def test_old_session_callback_fails_closed_after_new_browser_session():
    class Query:
        data = "txb:oldsid:d:3"
        def __init__(self): self.answers=[]
        async def answer(self, text=None, show_alert=False): self.answers.append((text, show_alert))
    class Update:
        def __init__(self): self.callback_query=Query()
    class Context:
        user_data={browser.BROWSER_STATE_KEY: {"session_id": "newsid"}}
    update=Update()
    asyncio.run(browser.handle_transaction_browser_callback(update, Context()))
    assert update.callback_query.answers
    assert update.callback_query.answers[0][1] is True
    assert "stale" in update.callback_query.answers[0][0].lower()


class _Message:
    def __init__(self, message_id=777):
        self.replies = []
        self.message_id = message_id
    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))
        return types.SimpleNamespace(message_id=self.message_id)


class _Context:
    def __init__(self, user_data=None, bot=None):
        self.user_data = user_data or {}
        self.bot = bot or types.SimpleNamespace()


def test_message_origin_staged_save_binds_exact_preview_message(monkeypatch):
    from app.bot.pending_actions import PendingActionError, consume_pending_action, pending_action_request_context

    txn = _txns(1)[0]
    sig = list(txn_service.transaction_material_signature(txn))
    state = {
        "session_id": "sel-bind",
        "mode": "edit",
        "stage": "wizard",
        "selected_ids": [txn["id"]],
        "selected_refs": [1],
        "wizard_index": 0,
        "drafts": {txn["id"]: {"amount": "15000"}},
        "baseline_signatures": {txn["id"]: sig},
        "origin_browser_session_id": None,
    }
    monkeypatch.setattr(
        txn_service,
        "preview_edit_transaction_by_ref",
        lambda **kwargs: {
            "success": True,
            "updates": dict(kwargs.get("updates") or {}),
            "old_txn": dict(txn),
            "new_txn": {**txn, **dict(kwargs.get("updates") or {})},
        },
    )
    message = _Message(message_id=777)
    update = types.SimpleNamespace(message=message)
    context = _Context({browser.SELECTOR_STATE_KEY: state})

    with pending_action_request_context(context.user_data, owner_user_id=77):
        asyncio.run(browser._show_combined_edit_preview(update, context, state))

    store = context.user_data.get("_pending_actions") or {}
    assert len(store) == 1
    action_id, action = next(iter(store.items()))
    assert action["preview_message_id"] == 777

    with pytest.raises(PendingActionError):
        consume_pending_action(
            context.user_data, action_id, owner_user_id=77, message_id=999, expected_flow="edit_txns_bulk_staged"
        )
    accepted = consume_pending_action(
        context.user_data, action_id, owner_user_id=77, message_id=777, expected_flow="edit_txns_bulk_staged"
    )
    assert accepted["status"] == "consumed"


def test_staged_wizard_performs_zero_financial_write_before_final_save(monkeypatch):
    txn = _txns(1)[0]
    sig = list(txn_service.transaction_material_signature(txn))
    state = {
        "session_id": "sel1",
        "mode": "edit",
        "stage": "wizard",
        "selected_ids": [txn["id"]],
        "selected_refs": [1],
        "wizard_index": 0,
        "drafts": {},
        "baseline_signatures": {txn["id"]: sig},
        "origin_browser_session_id": None,
    }
    preview_calls = []
    def preview(**kwargs):
        preview_calls.append(dict(kwargs))
        return {
            "success": True,
            "updates": dict(kwargs.get("updates") or {}),
            "old_txn": dict(txn),
            "new_txn": {**txn, **dict(kwargs.get("updates") or {})},
        }
    monkeypatch.setattr(txn_service, "preview_edit_transaction_by_ref", preview)
    # There is intentionally no mutation collaborator involved in staging.
    message = _Message()
    update = types.SimpleNamespace(message=message)
    context = _Context({browser.SELECTOR_STATE_KEY: state})

    asyncio.run(browser._handle_wizard_text(update, context, state, "amount=15000"))

    assert len(preview_calls) == 2  # per-target preview + combined final preview
    assert context.user_data[browser.STAGED_BULK_KEY]["entries"][0]["txn_id"] == txn["id"]
    assert context.user_data[browser.SELECTOR_STATE_KEY]["drafts"][txn["id"]]["amount"] == "15000"


def test_kembali_edit_keeps_staged_drafts(monkeypatch):
    txn = _txns(1)[0]
    state = {
        "session_id": "sel-return",
        "mode": "edit",
        "stage": "final",
        "selected_ids": [txn["id"]],
        "selected_refs": [1],
        "wizard_index": 1,
        "drafts": {txn["id"]: {"description": "Draft tetap"}},
        "baseline_signatures": {txn["id"]: list(txn_service.transaction_material_signature(txn))},
    }
    monkeypatch.setattr(txn_service, "get_transactions_with_row_index", lambda: [txn])

    class Query:
        data = "txs:sel-return:r:0"
        from_user = types.SimpleNamespace(id=1)
        message = _Message()
        async def answer(self, *a, **k): return None
    query = Query()
    update = types.SimpleNamespace(callback_query=query)
    context = _Context({browser.SELECTOR_STATE_KEY: state})

    asyncio.run(browser.handle_transaction_browser_callback(update, context))

    kept = context.user_data[browser.SELECTOR_STATE_KEY]
    assert kept["stage"] == "wizard"
    assert kept["wizard_index"] == 0
    assert kept["drafts"][txn["id"]] == {"description": "Draft tetap"}


def test_detail_keyboard_uses_native_copy_text_and_only_approved_top_level_actions():
    session = browser._build_session(_txns(3), family="transaksi", title="August")
    markup = browser._detail_keyboard(session, 2)
    labels = [[button.text for button in row] for row in markup.inline_keyboard]

    assert labels[0] == ["✏️ Edit", "🗑 Hapus"]
    assert labels[1] == ["📋 Copy ID"]
    assert labels[2] == ["◀️ Previous", "▶️ Next"]
    assert labels[3] == ["↩️ Kembali ke Daftar"]
    copy_button = markup.inline_keyboard[1][0]
    assert copy_button.callback_data is None
    assert copy_button.copy_text.text == "txn_02"


def test_staged_wizard_does_not_guess_category_alias(monkeypatch):
    txn = _txns(1)[0]
    state = {
        "session_id": "sel-category",
        "mode": "edit",
        "stage": "wizard",
        "selected_ids": [txn["id"]],
        "selected_refs": [1],
        "wizard_index": 0,
        "drafts": {},
        "baseline_signatures": {txn["id"]: list(txn_service.transaction_material_signature(txn))},
    }
    monkeypatch.setattr(
        txn_service,
        "preview_edit_transaction_by_ref",
        lambda **kwargs: {
            "success": True,
            "updates": dict(kwargs.get("updates") or {}),
            "old_txn": dict(txn),
            "new_txn": {**txn, **dict(kwargs.get("updates") or {})},
        },
    )
    monkeypatch.setattr(
        browser,
        "assess_edit_category_choice",
        lambda updates, preview: {
            "raw_category": "mkn",
            "suggested_category": "Food",
            "status": "alias",
            "transaction_type": "expense",
        },
    )
    message = _Message()
    update = types.SimpleNamespace(message=message)
    context = _Context({browser.SELECTOR_STATE_KEY: state})

    asyncio.run(browser._handle_wizard_text(update, context, state, "category=mkn"))

    kept = context.user_data[browser.SELECTOR_STATE_KEY]
    assert kept["wizard_index"] == 0
    assert kept["drafts"] == {}
    assert browser.STAGED_BULK_KEY not in context.user_data
    assert "Food" in message.replies[-1][0]
    assert "tidak ada write" in message.replies[-1][0]


def test_parent_browser_suspends_without_losing_long_lived_refs_and_gates_callbacks():
    session = browser._build_session(_txns(20), family="transaksi", title="August", query={"kind": "month", "month": "2026-08"})
    session["current_page"] = 1
    context = _Context({browser.BROWSER_STATE_KEY: session})
    browser.set_transaction_ref_context(context, session)
    sid = session["session_id"]

    assert browser.suspend_transaction_browser(context) == sid
    kept = context.user_data[browser.BROWSER_STATE_KEY]
    assert kept["status"] == "suspended"
    assert kept["child_parent_view"] == {"view": "list", "page": 1, "detail_ref": None, "detail_txn_id": None}
    assert context.user_data[browser.REF_CONTEXT_KEY]["ordered_ids"][10] == "txn_11"

    class Query:
        data = f"txb:{sid}:p:0"
        def __init__(self): self.answers = []
        async def answer(self, text=None, show_alert=False): self.answers.append((text, show_alert))
    update = types.SimpleNamespace(callback_query=Query())
    asyncio.run(browser.handle_transaction_browser_callback(update, context))
    assert update.callback_query.answers[-1][1] is True
    assert "selesaikan atau batalkan" in update.callback_query.answers[-1][0].lower()
    assert context.user_data[browser.BROWSER_STATE_KEY]["current_page"] == 1


def test_cancel_resumes_exact_prior_detail_view(monkeypatch):
    txns = _txns(12)
    session = browser._build_session(txns, family="transaksi", title="August")
    session.update({
        "current_page": 1,
        "current_view": "detail",
        "current_detail_ref": 11,
        "current_detail_txn_id": "txn_11",
    })
    context = _Context({browser.BROWSER_STATE_KEY: session})
    browser.set_transaction_ref_context(context, session)
    browser.suspend_transaction_browser(context)
    monkeypatch.setattr(browser, "_load_all_enriched", lambda: _async_value(txns))
    monkeypatch.setattr(browser, "_resolve_unique_ids", lambda ids: _async_value(([next(t for t in txns if t["id"] == ids[0])], [])))
    rendered = {}
    async def capture(query, ctx, current, text, markup):
        rendered["text"] = text
        rendered["markup"] = markup
    monkeypatch.setattr(browser, "_render_browser_control", capture)

    class Query:
        message = types.SimpleNamespace(message_id=900, chat_id=1)
        async def answer(self, *args, **kwargs): return None
    query = Query()
    assert asyncio.run(browser.resume_transaction_browser_after_cancel(query, context)) is True
    resumed = context.user_data[browser.BROWSER_STATE_KEY]
    assert resumed["status"] == "active"
    assert resumed["current_view"] == "detail"
    assert resumed["current_detail_ref"] == 11
    assert "Detail Transaksi #11" in rendered["text"]


def _async_value(value):
    async def inner(*args, **kwargs):
        return value
    return inner()


def test_refresh_parent_creates_new_session_and_replaces_ref_context(monkeypatch):
    old_txns = _txns(20)
    session = browser._build_session(
        old_txns,
        family="transaksi",
        title="Filtered",
        query={"kind": "month", "month": "2026-08", "category": "Food", "account": "Cash"},
    )
    session["current_page"] = 1
    context = _Context({browser.BROWSER_STATE_KEY: session})
    browser.set_transaction_ref_context(context, session)
    old_sid = session["session_id"]
    browser.suspend_transaction_browser(context)

    refreshed = [dict(txn) for txn in old_txns if txn["id"] != "txn_01"]
    monkeypatch.setattr(browser, "_refresh_transactions_for_session", lambda current: _async_value(refreshed))
    rendered = {}
    async def capture(query, ctx, current, text, markup):
        rendered["text"] = text
    monkeypatch.setattr(browser, "_render_browser_control", capture)
    query = types.SimpleNamespace(message=types.SimpleNamespace(message_id=901, chat_id=1))

    assert asyncio.run(browser.refresh_transaction_browser_after_child(
        query, context, mutation="edit", focus_txn_id="txn_11", success_notice="✅ Saved"
    )) is True
    new_session = context.user_data[browser.BROWSER_STATE_KEY]
    assert new_session["session_id"] != old_sid
    assert new_session["status"] == "active"
    assert context.user_data[browser.REF_CONTEXT_KEY]["session_id"] == new_session["session_id"]
    assert context.user_data[browser.REF_CONTEXT_KEY]["ordered_ids"] == [f"txn_{i:02d}" for i in range(20, 1, -1)]
    # txn_11 moved from old page 2 into its correct refreshed page, so old page is not blindly retained.
    assert new_session["current_page"] == 1
    assert "✅ Saved" in rendered["text"]


def test_refresh_filtered_query_uses_resolved_descriptor(monkeypatch):
    calls = []
    def monthly(year=None, month=None, category=None, account=None):
        calls.append((year, month, category, account))
        return {"transactions": _txns(2)}
    monkeypatch.setattr(browser, "get_monthly_report", monthly)
    session = browser._build_session(
        _txns(2), family="transaksi", title="Filtered",
        query={"kind": "month", "month": "2026-07", "category": "Food & Beverage", "account": "BCA"},
    )
    result = asyncio.run(browser._refresh_transactions_for_session(session))
    assert len(result) == 2
    assert calls == [(2026, 7, "Food & Beverage", "BCA")]


def test_retire_browser_preserves_refs_but_removes_browser_session(monkeypatch):
    session = browser._build_session(_txns(3), family="transaksi", title="August")
    context = _Context({browser.BROWSER_STATE_KEY: session, browser.BROWSER_CONTROL_MESSAGE_KEY: 55})
    browser.set_transaction_ref_context(context, session)
    cleared = []
    async def clear(ctx, chat_id, state_key):
        cleared.append((chat_id, state_key))
        ctx.user_data.pop(state_key, None)
    monkeypatch.setattr(browser, "clear_tracked_inline_keyboard", clear)
    update = types.SimpleNamespace(effective_chat=types.SimpleNamespace(id=1), message=None, callback_query=None)

    assert asyncio.run(browser.retire_transaction_browser(update, context, reason="saldo", preserve_refs=True)) is True
    assert browser.BROWSER_STATE_KEY not in context.user_data
    assert context.user_data[browser.REF_CONTEXT_KEY]["ordered_ids"] == ["txn_01", "txn_02", "txn_03"]
    assert cleared == [(1, browser.BROWSER_CONTROL_MESSAGE_KEY)]


def test_selector_inherits_active_browser_parent(monkeypatch):
    txns = _txns(32)
    session = browser._build_session(txns, family="transaksi", title="August")
    session["current_page"] = 3
    context = _Context({browser.BROWSER_STATE_KEY: session})
    monkeypatch.setattr(txn_service, "get_recent_transactions", lambda limit=100: txns)
    message = _Message(message_id=930)
    update = types.SimpleNamespace(message=message)

    asyncio.run(browser.start_transaction_selector(update, context, "edit"))
    state = context.user_data[browser.SELECTOR_STATE_KEY]
    assert state["origin_browser_session_id"] == session["session_id"]
    assert context.user_data[browser.BROWSER_STATE_KEY]["status"] == "suspended"
    assert context.user_data[browser.BROWSER_STATE_KEY]["child_parent_view"]["page"] == 3


def test_post_mutation_refresh_failure_retires_stale_browser_without_raising(monkeypatch):
    session = browser._build_session(_txns(3), family="transaksi", title="August", query={"kind": "month", "month": "2026-08"})
    context = _Context({browser.BROWSER_STATE_KEY: session})
    browser.set_transaction_ref_context(context, session)
    browser.suspend_transaction_browser(context)
    async def boom(_session):
        raise RuntimeError("read unavailable")
    monkeypatch.setattr(browser, "_refresh_transactions_for_session", boom)
    async def clear(ctx, chat_id, state_key):
        ctx.user_data.pop(state_key, None)
    monkeypatch.setattr(browser, "clear_tracked_inline_keyboard", clear)
    rendered = []
    async def safe(query, text, **kwargs):
        rendered.append(text)
    monkeypatch.setattr(browser, "safe_edit_message", safe)
    query = types.SimpleNamespace(message=types.SimpleNamespace(chat_id=1, message_id=88))

    handled = asyncio.run(browser.refresh_transaction_browser_after_child(
        query, context, mutation="edit", focus_txn_id="txn_01", success_notice="✅ Edit committed"
    ))
    assert handled is True
    assert browser.BROWSER_STATE_KEY not in context.user_data
    assert browser.REF_CONTEXT_KEY not in context.user_data
    assert rendered and "Mutation sudah berhasil" in rendered[-1]


def test_nested_category_child_can_resume_parent_as_fresh_message(monkeypatch):
    txns = _txns(12)
    session = browser._build_session(txns, family="transaksi", title="August")
    session.update({
        "current_page": 1,
        "current_view": "detail",
        "current_detail_ref": 11,
        "current_detail_txn_id": "txn_11",
    })
    context = _Context({browser.BROWSER_STATE_KEY: session, browser.BROWSER_CONTROL_MESSAGE_KEY: 41})
    browser.set_transaction_ref_context(context, session)
    browser.suspend_transaction_browser(context)
    monkeypatch.setattr(browser, "_load_all_enriched", lambda: _async_value(txns))
    monkeypatch.setattr(browser, "_resolve_unique_ids", lambda ids: _async_value(([next(t for t in txns if t["id"] == ids[0])], [])))
    async def clear(ctx, chat_id, state_key):
        ctx.user_data.pop(state_key, None)
    monkeypatch.setattr(browser, "clear_tracked_inline_keyboard", clear)

    class Message(_Message):
        chat_id = 1
    class Query:
        message = Message(message_id=944)
        async def answer(self, *args, **kwargs): return None

    query = Query()
    assert asyncio.run(browser.resume_transaction_browser_after_cancel(
        query,
        context,
        notice="Kategori selesai; browser kembali.",
        preserve_current_message=True,
    )) is True
    resumed = context.user_data[browser.BROWSER_STATE_KEY]
    assert resumed["status"] == "active"
    assert resumed["current_view"] == "detail"
    assert resumed["current_detail_ref"] == 11
    assert query.message.replies
    assert "Kategori selesai" in query.message.replies[-1][0]
    assert "Detail Transaksi #11" in query.message.replies[-1][0]
    assert context.user_data[browser.BROWSER_CONTROL_MESSAGE_KEY] == 944


def test_edit_leaving_parent_filter_explains_and_returns_truthful_list(monkeypatch):
    old_txns = _txns(10)
    session = browser._build_session(
        old_txns,
        family="transaksi",
        title="Food only",
        query={"kind": "month", "month": "2026-08", "category": "Food", "account": "Cash"},
    )
    session.update({"current_page": 1, "current_view": "detail", "current_detail_ref": 10, "current_detail_txn_id": "txn_10"})
    context = _Context({browser.BROWSER_STATE_KEY: session})
    browser.set_transaction_ref_context(context, session)
    browser.suspend_transaction_browser(context)
    refreshed = [txn for txn in old_txns if txn["id"] != "txn_10"]
    monkeypatch.setattr(browser, "_refresh_transactions_for_session", lambda current: _async_value(refreshed))
    rendered = {}
    async def capture(query, ctx, current, text, markup):
        rendered["text"] = text
        rendered["session"] = dict(current)
    monkeypatch.setattr(browser, "_render_browser_control", capture)
    query = types.SimpleNamespace(message=types.SimpleNamespace(message_id=945, chat_id=1))

    assert asyncio.run(browser.refresh_transaction_browser_after_child(
        query, context, mutation="edit", focus_txn_id="txn_10", success_notice="✅ Edit committed"
    )) is True
    new_session = context.user_data[browser.BROWSER_STATE_KEY]
    assert new_session["current_view"] == "list"
    assert new_session["current_page"] == 1  # nearest valid page for 9 results at 8/page
    assert "tidak lagi cocok dengan filter" in rendered["text"]
    assert "txn_10" not in context.user_data[browser.REF_CONTEXT_KEY]["ordered_ids"]


def test_delete_refresh_clamps_removed_last_page(monkeypatch):
    old_txns = _txns(17)
    session = browser._build_session(old_txns, family="transaksi", title="August", query={"kind": "month", "month": "2026-08"})
    session.update({"current_page": 2, "current_view": "list"})
    context = _Context({browser.BROWSER_STATE_KEY: session})
    browser.set_transaction_ref_context(context, session)
    browser.suspend_transaction_browser(context)
    refreshed = old_txns[:-1]  # 16 rows => only pages 0 and 1 remain
    monkeypatch.setattr(browser, "_refresh_transactions_for_session", lambda current: _async_value(refreshed))
    async def capture(query, ctx, current, text, markup): return None
    monkeypatch.setattr(browser, "_render_browser_control", capture)
    query = types.SimpleNamespace(message=types.SimpleNamespace(message_id=946, chat_id=1))

    assert asyncio.run(browser.refresh_transaction_browser_after_child(query, context, mutation="delete", success_notice="✅ Deleted")) is True
    new_session = context.user_data[browser.BROWSER_STATE_KEY]
    assert new_session["current_page"] == 1
    assert new_session["total_count"] == 16


def test_non_transaction_command_retires_controls_but_preserves_refs(monkeypatch):
    session = browser._build_session(_txns(4), family="transaksi", title="August")
    context = _Context({browser.BROWSER_STATE_KEY: session, browser.BROWSER_CONTROL_MESSAGE_KEY: 52})
    browser.set_transaction_ref_context(context, session)
    async def clear(ctx, chat_id, state_key):
        ctx.user_data.pop(state_key, None)
    monkeypatch.setattr(browser, "clear_tracked_inline_keyboard", clear)
    update = types.SimpleNamespace(effective_chat=types.SimpleNamespace(id=1), message=types.SimpleNamespace(text="/saldo"), callback_query=None)

    asyncio.run(browser.prepare_transaction_browser_for_command(update, context, "saldo", "/saldo"))
    assert browser.BROWSER_STATE_KEY not in context.user_data
    assert context.user_data[browser.REF_CONTEXT_KEY]["ordered_ids"] == ["txn_01", "txn_02", "txn_03", "txn_04"]


def test_terminal_delete_block_resumes_parent_without_write(monkeypatch):
    txns = _txns(3)
    session = browser._build_session(txns, family="transaksi", title="August")
    context = _Context({browser.BROWSER_STATE_KEY: session})
    browser.set_transaction_ref_context(context, session)
    browser.suspend_transaction_browser(context)
    state = {
        "session_id": "selector-delete-blocked",
        "mode": "delete",
        "stage": "selected",
        "selected_ids": ["txn_01"],
        "selected_refs": [1],
        "origin_browser_session_id": session["session_id"],
    }
    context.user_data[browser.SELECTOR_STATE_KEY] = state
    monkeypatch.setattr(browser, "preview_delete_transactions_by_refs", lambda **kwargs: {
        "deletable": [],
        "blocked": [txns[0]],
        "missing_ids": [],
        "duplicate_ids": [],
    })
    monkeypatch.setattr(browser, "_load_all_enriched", lambda: _async_value(txns))
    rendered = {}
    async def capture(query, ctx, current, text, markup):
        rendered["text"] = text
    monkeypatch.setattr(browser, "_render_browser_control", capture)

    class Query:
        message = types.SimpleNamespace(message_id=950, chat_id=1)
        async def answer(self, *args, **kwargs): return None
    query = Query()
    asyncio.run(browser._prepare_delete_final(query, context, state))
    assert browser.SELECTOR_STATE_KEY not in context.user_data
    assert context.user_data[browser.BROWSER_STATE_KEY]["status"] == "active"
    assert "diblok" in rendered["text"]


def test_transaction_browser_replacement_creates_new_ref_context_and_stales_old_callback(monkeypatch):
    old_session = browser._build_session(_txns(4), family="transaksi", title="August")
    context = _Context({browser.BROWSER_STATE_KEY: old_session, browser.BROWSER_CONTROL_MESSAGE_KEY: 60})
    browser.set_transaction_ref_context(context, old_session)
    old_sid = old_session["session_id"]
    async def clear(ctx, chat_id, state_key):
        ctx.user_data.pop(state_key, None)
    monkeypatch.setattr(browser, "clear_tracked_inline_keyboard", clear)
    command_update = types.SimpleNamespace(
        effective_chat=types.SimpleNamespace(id=1),
        message=types.SimpleNamespace(text="/cari kopi", chat_id=1),
        callback_query=None,
    )
    asyncio.run(browser.prepare_transaction_browser_for_command(command_update, context, "cari", "/cari kopi"))
    assert browser.BROWSER_STATE_KEY not in context.user_data
    # Retirement alone keeps the last useful refs until the valid replacement is built.
    assert context.user_data[browser.REF_CONTEXT_KEY]["session_id"] == old_sid

    message = _Message(message_id=961)
    update = types.SimpleNamespace(message=message)
    new_rows = _txns(2)
    new_session = asyncio.run(browser.start_transaction_browser(
        update,
        context,
        new_rows,
        family="cari",
        title='Hasil pencarian: "kopi"',
        query={"keyword": "kopi"},
    ))
    assert new_session["session_id"] != old_sid
    assert context.user_data[browser.REF_CONTEXT_KEY]["session_id"] == new_session["session_id"]
    assert context.user_data[browser.REF_CONTEXT_KEY]["ordered_ids"] == ["txn_01", "txn_02"]

    class OldQuery:
        data = f"txb:{old_sid}:p:0"
        def __init__(self): self.answers = []
        async def answer(self, text=None, show_alert=False): self.answers.append((text, show_alert))
    old_query = OldQuery()
    asyncio.run(browser.handle_transaction_browser_callback(types.SimpleNamespace(callback_query=old_query), context))
    assert old_query.answers and old_query.answers[-1][1] is True
    assert "stale" in old_query.answers[-1][0].lower()


def test_cancel_resumes_exact_prior_list_page(monkeypatch):
    txns = _txns(20)
    session = browser._build_session(txns, family="transaksi", title="August")
    session.update({"current_page": 1, "current_view": "list"})
    context = _Context({browser.BROWSER_STATE_KEY: session})
    browser.set_transaction_ref_context(context, session)
    browser.suspend_transaction_browser(context)
    monkeypatch.setattr(browser, "_load_all_enriched", lambda: _async_value(txns))
    rendered = {}
    async def capture(query, ctx, current, text, markup):
        rendered["text"] = text
        rendered["page"] = current["current_page"]
    monkeypatch.setattr(browser, "_render_browser_control", capture)

    class Query:
        message = types.SimpleNamespace(message_id=970, chat_id=1)
        async def answer(self, *args, **kwargs): return None
    assert asyncio.run(browser.resume_transaction_browser_after_cancel(Query(), context)) is True
    assert context.user_data[browser.BROWSER_STATE_KEY]["status"] == "active"
    assert context.user_data[browser.BROWSER_STATE_KEY]["current_page"] == 1
    assert rendered["page"] == 1
    assert "Halaman 2/3" in rendered["text"]


def test_delete_refresh_empty_query_renders_truthful_empty_state(monkeypatch):
    session = browser._build_session(_txns(1), family="transaksi", title="August", query={"kind": "month", "month": "2026-08"})
    context = _Context({browser.BROWSER_STATE_KEY: session})
    browser.set_transaction_ref_context(context, session)
    browser.suspend_transaction_browser(context)
    monkeypatch.setattr(browser, "_refresh_transactions_for_session", lambda current: _async_value([]))
    rendered = {}
    async def capture(query, ctx, current, text, markup):
        rendered["text"] = text
    monkeypatch.setattr(browser, "_render_browser_control", capture)
    query = types.SimpleNamespace(message=types.SimpleNamespace(message_id=971, chat_id=1))

    assert asyncio.run(browser.refresh_transaction_browser_after_child(query, context, mutation="delete", success_notice="✅ Deleted")) is True
    new_session = context.user_data[browser.BROWSER_STATE_KEY]
    assert new_session["total_count"] == 0
    assert context.user_data[browser.REF_CONTEXT_KEY]["ordered_ids"] == []
    assert "0 transaksi" in rendered["text"]
    assert "Tidak ada transaksi yang cocok" in rendered["text"]


def test_cancel_transaction_child_actions_cancels_nested_category_add_action():
    from app.bot.pending_actions import PendingActionError, consume_pending_action, create_pending_action

    context = _Context({
        "pending_category_add_flow": {
            "stage": "confirm",
            "origin_browser_session_id": "browser-parent",
        }
    })
    action = create_pending_action(
        context.user_data,
        owner_user_id=7,
        flow_type="category_add",
        payload={"legacy_target": "category_add", "user_state": {"pending_category_add_flow": {"stage": "confirm"}}},
        preview_message_id=700,
    )

    assert browser.cancel_transaction_child_actions(context) == 1
    with pytest.raises(PendingActionError) as exc_info:
        consume_pending_action(
            context.user_data,
            action["action_id"],
            owner_user_id=7,
            message_id=700,
            expected_flow="category_add",
        )
    assert exc_info.value.code == "canceled"


def test_monthly_summary_is_on_demand_and_charts_exact_snapshot(monkeypatch):
    rows = [
        {"id": "txn_a", "date": "2026-07-03", "type": "income", "amount": 100000, "account": "BCA"},
        {"id": "txn_b", "date": "2026-07-02", "type": "expense", "amount": 890000, "net": 420000, "account": "BCA"},
        {"id": "txn_t", "date": "2026-07-01", "type": "transfer", "amount": 250000, "account": "BCA", "to_account": "DANA"},
        {"id": "txn_outside", "date": "2026-06-01", "type": "expense", "amount": 999999, "net": 999999, "account": "BCA"},
    ]
    session = browser._build_session(
        rows[:3],
        family="transaksi",
        title="Transaksi 2026-07",
        query={"kind": "month", "month": "2026-07"},
        summary_label="📊 Ringkasan Bulanan",
    )
    original = dict(session)
    original["identities"] = [dict(item) for item in session["identities"]]

    async def forbidden_reload():
        raise AssertionError("summary/chart must use the exact frozen browser snapshot")
    captured = {}
    async def send_chart(bot, chat_id, transactions, title):
        captured["ids"] = [txn["id"] for txn in transactions]
        captured["title"] = title
        captured["chat_id"] = chat_id
        return True, ""
    monkeypatch.setattr(browser, "_load_all_enriched", forbidden_reload)
    monkeypatch.setattr(browser, "send_transaction_timeseries_chart_message", send_chart)

    message = _Message()
    query = types.SimpleNamespace(message=message)
    asyncio.run(browser._browser_summary(query, _Context(), session, chat_id=1))

    assert len(message.replies) == 1
    summary_text = message.replies[0][0]
    assert "Ringkasan Bulanan" in summary_text
    assert "Periode: *2026-07*" in summary_text
    assert "NET420000 (GROSS890000)" in summary_text
    assert "Transfer Antar Rekening" in summary_text and "non-P&L" in summary_text
    assert "Hasil Bersih Periode" in summary_text
    assert "Snapshot Aktif: *3 transaksi*" in summary_text
    assert "🔄 Transfer:" not in summary_text and "📊 Net:" not in summary_text
    assert captured["ids"] == ["txn_a", "txn_b", "txn_t"]
    assert session == original


def test_account_summary_distinguishes_balance_net_gross_and_transfer_direction(monkeypatch):
    rows = [
        {"id": "i", "date": "2026-07-04", "type": "income", "amount": 500000, "account": "BCA"},
        {"id": "e", "date": "2026-07-03", "type": "expense", "amount": 300000, "net": 200000, "account": "BCA"},
        {"id": "tin", "date": "2026-07-02", "type": "transfer", "amount": 170000, "account": "DANA", "to_account": "BCA"},
        {"id": "tout", "date": "2026-07-01", "type": "transfer", "amount": 70000, "account": "BCA", "to_account": "DANA"},
    ]
    session = browser._build_session(
        rows,
        family="rekening",
        title="Transaksi Rekening BCA — 2026-07",
        query={"account": "BCA", "period_type": "month", "month": "2026-07"},
        summary_label="📊 Ringkasan Rekening",
        account_filter="BCA",
    )
    async def forbidden_reload():
        raise AssertionError("account summary/chart must stay on the frozen filtered snapshot")
    captured = {}
    async def send_chart(bot, chat_id, transactions, title):
        captured["ids"] = [txn["id"] for txn in transactions]
        captured["chat_id"] = chat_id
        captured["title"] = title
        return True, ""
    monkeypatch.setattr(browser, "_load_all_enriched", forbidden_reload)
    monkeypatch.setattr(browser, "send_transaction_timeseries_chart_message", send_chart)
    monkeypatch.setattr(txn_service, "get_account_balance", lambda account: 1234567)

    message = _Message()
    query = types.SimpleNamespace(message=message)
    before = repr(session)
    asyncio.run(browser._browser_summary(query, _Context(), session, chat_id=1))
    text = message.replies[0][0]
    assert "Saldo Saat Ini" in text and "Rp1234567" in text
    assert "NET200000 (GROSS300000)" in text
    assert "Transfer Masuk" in text and "Rp170000" in text
    assert "Transfer Keluar" in text and "Rp70000" in text
    assert "Pergerakan Bersih Periode" in text and "Rp400000" in text
    assert "Snapshot Aktif: *4 transaksi*" in text
    assert captured["ids"] == ["i", "e", "tin", "tout"]
    assert captured["chat_id"] == 1
    assert "BCA" in captured["title"]
    assert repr(session) == before


def test_monthly_chart_failure_is_truthful_and_does_not_change_session(monkeypatch):
    rows = [{"id": "txn_a", "date": "2026-07-01", "type": "expense", "amount": 10000, "net": 10000}]
    session = browser._build_session(
        rows, family="transaksi", title="Transaksi 2026-07",
        query={"kind": "month", "month": "2026-07"}, summary_label="📊 Ringkasan Bulanan",
    )
    before = repr(session)
    async def load_rows(): return list(rows)
    async def fail_chart(*args, **kwargs): return False, "boom"
    monkeypatch.setattr(browser, "_load_all_enriched", load_rows)
    monkeypatch.setattr(browser, "send_transaction_timeseries_chart_message", fail_chart)
    message = _Message()
    query = types.SimpleNamespace(message=message)
    asyncio.run(browser._browser_summary(query, _Context(), session, chat_id=1))
    assert len(message.replies) == 2
    assert "grafik time series gagal" in message.replies[1][0].lower()
    assert repr(session) == before


def test_account_chart_failure_is_truthful_and_does_not_change_session(monkeypatch):
    rows = [{"id": "txn_a", "date": "2026-07-01", "type": "expense", "amount": 10000, "net": 10000, "account": "BCA"}]
    session = browser._build_session(
        rows, family="rekening", title="Transaksi Rekening BCA — 2026-07",
        query={"kind": "account", "period_type": "month", "month": "2026-07", "account": "BCA"},
        summary_label="📊 Ringkasan Rekening", account_filter="BCA",
    )
    before = repr(session)
    async def fail_chart(*args, **kwargs): return False, "send failed"
    monkeypatch.setattr(browser, "send_transaction_timeseries_chart_message", fail_chart)
    monkeypatch.setattr(txn_service, "get_account_balance", lambda account: 123)
    message = _Message()
    query = types.SimpleNamespace(message=message)
    asyncio.run(browser._browser_summary(query, _Context(), session, chat_id=1))
    assert len(message.replies) == 2
    assert "Ringkasan Rekening" in message.replies[0][0]
    assert "grafik time series gagal" in message.replies[1][0].lower()
    assert repr(session) == before


def test_account_summary_reports_unavailable_balance_without_fabricating_zero(monkeypatch):
    rows = [{"id": "e", "date": "2026-07-03", "type": "expense", "amount": 300000, "net": 200000, "account": "BCA"}]
    session = browser._build_session(
        rows,
        family="rekening",
        title="Transaksi Rekening BCA — 2026-07",
        query={"account": "BCA", "period_type": "month", "month": "2026-07"},
        summary_label="📊 Ringkasan Rekening",
        account_filter="BCA",
    )
    async def load_rows(): return list(rows)
    def fail_balance(account): raise RuntimeError("balance unavailable")
    monkeypatch.setattr(browser, "_load_all_enriched", load_rows)
    monkeypatch.setattr(txn_service, "get_account_balance", fail_balance)
    message = _Message()
    query = types.SimpleNamespace(message=message)
    asyncio.run(browser._browser_summary(query, _Context(), session, chat_id=1))
    text = message.replies[0][0]
    assert "Saldo Saat Ini: *tidak tersedia*" in text
    assert "Saldo Saat Ini: *Rp0*" not in text


@pytest.mark.parametrize("family", ["transaksi", "last", "rekening", "cari"])
def test_ctx049_transaction_family_pagination_uses_frozen_display_and_acks_before_render(monkeypatch, family):
    rows = _txns(32)
    session = browser._build_session(rows, family=family, title="Latency snapshot")
    context = _Context({browser.BROWSER_STATE_KEY: session})
    browser.set_transaction_ref_context(context, session)

    def forbidden_provider_reload(*args, **kwargs):
        raise AssertionError("pure page navigation must not reload Transactions/Debts providers")

    monkeypatch.setattr(browser, "_load_all_enriched", forbidden_provider_reload)
    events = []
    rendered = []

    async def capture_render(query, ctx, current, text, markup):
        events.append("render")
        rendered.append(text)

    monkeypatch.setattr(browser, "_render_browser_control", capture_render)

    class Query:
        def __init__(self, page):
            self.data = f"txb:{session['session_id']}:p:{page}"
            self.answers = []
            self.message = types.SimpleNamespace(message_id=1100 + page, chat_id=1)

        async def answer(self, text=None, show_alert=False):
            self.answers.append((text, show_alert))
            events.append("ack")

    # Repeated navigation must stay fully session-local after browser creation.
    for page in (1, 2, 1, 2, 3):
        events.clear()
        query = Query(page)
        asyncio.run(browser.handle_transaction_browser_callback(types.SimpleNamespace(callback_query=query), context))
        assert query.answers == [(None, False)]
        assert events == ["ack", "render"]

    assert "25." in rendered[-1] and "32." in rendered[-1]
    assert context.user_data[browser.REF_CONTEXT_KEY]["ordered_ids"][25] == "txn_26"


def test_ctx049_large_snapshot_page_turn_remains_provider_free(monkeypatch):
    rows = _txns(160)
    session = browser._build_session(rows, family="cari", title="Large search")
    context = _Context({browser.BROWSER_STATE_KEY: session})
    calls = {"reload": 0}

    async def provider_reload():
        calls["reload"] += 1
        return rows

    async def capture_render(*args, **kwargs):
        return None

    monkeypatch.setattr(browser, "_load_all_enriched", provider_reload)
    monkeypatch.setattr(browser, "_render_browser_control", capture_render)

    class Query:
        def __init__(self, page):
            self.data = f"txb:{session['session_id']}:p:{page}"
            self.message = types.SimpleNamespace(message_id=1200 + page, chat_id=1)
            self.answers = []

        async def answer(self, text=None, show_alert=False):
            self.answers.append((text, show_alert))

    for page in (1, 2, 1, 2, 10, 19):
        query = Query(page)
        asyncio.run(browser.handle_transaction_browser_callback(types.SimpleNamespace(callback_query=query), context))
        assert query.answers == [(None, False)]

    assert calls == {"reload": 0}
    assert context.user_data[browser.BROWSER_STATE_KEY]["current_page"] == 19


def test_ctx049_selector_pagination_reuses_selector_snapshot_and_acks_first(monkeypatch):
    rows = _txns(32)
    context = _Context()
    message = _Message(message_id=1300)
    update = types.SimpleNamespace(message=message)
    monkeypatch.setattr(txn_service, "get_recent_transactions", lambda limit=100: rows)

    # Exercise the real selector creation path so the regression proves the
    # frozen display data is actually stored before page callbacks begin.
    asyncio.run(browser.start_transaction_selector(update, context, "edit"))
    state = context.user_data[browser.SELECTOR_STATE_KEY]
    sid = state["session_id"]
    assert len(state["display_records"]) == 32
    events = []

    async def forbidden_reload():
        raise AssertionError("selector page turn must not reload full provider population")

    async def capture_edit(query, text, **kwargs):
        events.append("render")

    monkeypatch.setattr(browser, "_load_all_enriched", forbidden_reload)
    monkeypatch.setattr(browser, "safe_edit_message", capture_edit)

    class Query:
        def __init__(self, page):
            self.data = f"txs:{sid}:p:{page}"
            self.message = types.SimpleNamespace(message_id=1300 + page, chat_id=1)
            self.answers = []

        async def answer(self, text=None, show_alert=False):
            self.answers.append((text, show_alert))
            events.append("ack")

    for page in (1, 2, 1, 2):
        events.clear()
        query = Query(page)
        asyncio.run(browser.handle_transaction_browser_callback(types.SimpleNamespace(callback_query=query), context))
        assert query.answers == [(None, False)]
        assert events == ["ack", "render"]

    assert context.user_data[browser.SELECTOR_STATE_KEY]["identities"][25]["id"] == "txn_26"


def test_ctx049_read_only_detail_and_back_use_frozen_finance_aware_display(monkeypatch):
    rows = _txns(16)
    rows[8] = rows[8] | {
        "amount": 890000,
        "net": 420000,
        "receivables": [{"person_name": "Budi", "remaining_amount": 470000}],
        "account": "BCA",
        "description": "Fronting dinner",
    }
    rows[9] = rows[9] | {
        "type": "transfer",
        "amount": 100000,
        "account": "BCA",
        "to_account": "DANA",
        "description": "Pindah dana",
    }
    session = browser._build_session(rows, family="transaksi", title="Finance display")
    context = _Context({browser.BROWSER_STATE_KEY: session})
    rendered = []

    async def forbidden_reload():
        raise AssertionError("read-only detail/list navigation must not reload the full population")

    async def forbidden_unique(*args, **kwargs):
        raise AssertionError("read-only detail navigation must not use mutation revalidation reads")

    async def capture_render(query, ctx, current, text, markup):
        rendered.append(text)

    monkeypatch.setattr(browser, "_load_all_enriched", forbidden_reload)
    monkeypatch.setattr(browser, "_get_unique_snapshot_txn", forbidden_unique)
    monkeypatch.setattr(browser, "_render_browser_control", capture_render)

    class Query:
        def __init__(self, data):
            self.data = data
            self.answers = []
            self.message = types.SimpleNamespace(message_id=1400, chat_id=1)

        async def answer(self, text=None, show_alert=False):
            self.answers.append((text, show_alert))

    for action in ("d:9", "n:9", "b:10"):
        query = Query(f"txb:{session['session_id']}:{action}")
        asyncio.run(browser.handle_transaction_browser_callback(types.SimpleNamespace(callback_query=query), context))
        assert query.answers == [(None, False)]

    list_text = rendered[-1]
    assert "NET420000 (GROSS890000)" in list_text
    assert "Piutang 1" in list_text
    assert "BCA → DANA" in list_text


def test_ctx049_post_mutation_refresh_rebuilds_display_snapshot(monkeypatch):
    old_rows = _txns(12)
    session = browser._build_session(
        old_rows,
        family="transaksi",
        title="Refresh snapshot",
        query={"kind": "month", "month": "2026-08"},
    )
    context = _Context({browser.BROWSER_STATE_KEY: session})
    browser.set_transaction_ref_context(context, session)
    old_sid = session["session_id"]
    browser.suspend_transaction_browser(context)

    refreshed = [dict(row) for row in old_rows]
    refreshed[10]["description"] = "Updated after commit"
    monkeypatch.setattr(browser, "_refresh_transactions_for_session", lambda current: _async_value(refreshed))

    async def capture_render(*args, **kwargs):
        return None

    monkeypatch.setattr(browser, "_render_browser_control", capture_render)
    query = types.SimpleNamespace(message=types.SimpleNamespace(message_id=1500, chat_id=1))

    assert asyncio.run(browser.refresh_transaction_browser_after_child(
        query,
        context,
        mutation="edit",
        focus_txn_id="txn_11",
        success_notice="✅ Saved",
    )) is True

    new_session = context.user_data[browser.BROWSER_STATE_KEY]
    assert new_session["session_id"] != old_sid
    fresh_display = next(row for row in new_session["display_records"] if row["id"] == "txn_11")
    old_display = next(row for row in session["display_records"] if row["id"] == "txn_11")
    assert fresh_display["description"] == "Updated after commit"
    assert old_display["description"] != fresh_display["description"]


def test_transaction_summary_label_matches_actual_monthly_vs_account_behavior():
    assert browser.transaction_summary_label("month", None) == "📊 Ringkasan Bulanan"
    assert browser.transaction_summary_label("month", "BCA") == "📊 Ringkasan Rekening"
    assert browser.transaction_summary_label("account", "BCA") == "📊 Ringkasan Rekening"
    assert browser.transaction_summary_label("day", None) == "📊 Ringkasan Hasil"


def test_monthly_summary_callback_acks_before_summary_work(monkeypatch):
    rows = _txns(4)
    session = browser._build_session(
        rows,
        family="transaksi",
        title="Monthly",
        query={"kind": "month", "month": "2026-08"},
        summary_label="📊 Ringkasan Bulanan",
    )
    context = _Context({browser.BROWSER_STATE_KEY: session})
    events = []

    async def summary(query, ctx, current, *, chat_id=None):
        events.append("summary")
    monkeypatch.setattr(browser, "_browser_summary", summary)

    class Query:
        data = f"txb:{session['session_id']}:s:0"
        message = types.SimpleNamespace(message_id=1600, chat_id=1)
        async def answer(self, text=None, show_alert=False):
            events.append("ack")

    asyncio.run(browser.handle_transaction_browser_callback(types.SimpleNamespace(callback_query=Query(), effective_chat=types.SimpleNamespace(id=1)), context))
    assert events == ["ack", "summary"]


def test_monthly_summary_callback_reaches_actual_chart_helper_and_photo_response(monkeypatch):
    """Exercise callback -> production chart helper -> bot.send_photo response contract."""
    captured = {}

    class ActualInputFile:
        def __init__(self, obj, filename=None):
            self.obj = obj
            self.filename = filename

    prior_input_file = getattr(telegram, "InputFile", _MISSING)
    telegram.InputFile = ActualInputFile
    chart_service = types.ModuleType("app.services.chart_service")

    def build_png(rows, title):
        captured["chart_ids"] = [str(row.get("id") or "") for row in rows]
        captured["chart_title"] = title
        return b"\x89PNG\r\n\x1a\ncallback-visible-chart"

    chart_service.build_transaction_timeseries_png_bytes = build_png
    chart_name = "app.bot.handler_parts.transaction_chart"
    prior_chart = sys.modules.pop(chart_name, _MISSING)
    chart_parent = importlib.import_module("app.bot.handler_parts")
    prior_chart_attr = getattr(chart_parent, "transaction_chart", _MISSING)
    if prior_chart_attr is not _MISSING:
        delattr(chart_parent, "transaction_chart")
    loaded_chart = _MISSING
    try:
        with _temporary_modules({"telegram": telegram, "app.services.chart_service": chart_service}):
            loaded_chart = importlib.import_module(chart_name)
    finally:
        if prior_chart is _MISSING:
            sys.modules.pop(chart_name, None)
        else:
            sys.modules[chart_name] = prior_chart
        if prior_chart_attr is _MISSING:
            if getattr(chart_parent, "transaction_chart", _MISSING) is loaded_chart:
                delattr(chart_parent, "transaction_chart")
        else:
            chart_parent.transaction_chart = prior_chart_attr
        if prior_input_file is _MISSING:
            delattr(telegram, "InputFile")
        else:
            telegram.InputFile = prior_input_file

    monkeypatch.setattr(browser, "send_transaction_timeseries_chart_message", loaded_chart.send_transaction_timeseries_chart_message)

    rows = [
        {"id": "txn_a", "date": "2026-07-01", "type": "expense", "amount": 10000, "net": 8000, "account": "BCA"},
        {"id": "txn_b", "date": "2026-07-02", "type": "income", "amount": 20000, "account": "BCA"},
    ]
    session = browser._build_session(
        rows,
        family="transaksi",
        title="Transaksi Bulan 2026-07",
        query={"kind": "month", "month": "2026-07"},
        summary_label="📊 Ringkasan Bulanan",
    )

    class Bot:
        async def send_photo(self, **kwargs):
            captured["send_photo"] = kwargs
            assert kwargs["chat_id"] == 42
            assert kwargs["photo"].filename == "grafik-transaksi-timeseries.png"
            assert kwargs["photo"].obj.startswith(b"\x89PNG\r\n\x1a\n")
            return types.SimpleNamespace(photo=[types.SimpleNamespace(file_id="visible-photo")])

    context = _Context({browser.BROWSER_STATE_KEY: session}, bot=Bot())
    message = _Message(message_id=1700)
    message.chat_id = 42

    class Query:
        data = f"txb:{session['session_id']}:s:0"
        def __init__(self):
            self.message = message
            self.answers = []
        async def answer(self, text=None, show_alert=False):
            self.answers.append((text, show_alert))

    query = Query()
    update = types.SimpleNamespace(callback_query=query, effective_chat=types.SimpleNamespace(id=42))
    asyncio.run(browser.handle_transaction_browser_callback(update, context))

    assert query.answers == [(None, False)]
    assert message.replies and "Ringkasan Bulanan" in message.replies[0][0]
    assert captured["chart_ids"] == ["txn_a", "txn_b"]
    assert captured["chart_title"] == "Time Series - Transaksi Bulan 2026-07"
    assert captured["send_photo"]["chat_id"] == 42

    # Account-filtered summary must traverse the same real chart-delivery helper
    # using only that browser's frozen filtered rows.
    account_rows = [
        {"id": "acc_e", "date": "2026-07-03", "type": "expense", "amount": 30000, "net": 20000, "account": "BCA"},
        {"id": "acc_t", "date": "2026-07-04", "type": "transfer", "amount": 50000, "account": "DANA", "to_account": "BCA"},
    ]
    account_session = browser._build_session(
        account_rows,
        family="rekening",
        title="Transaksi Rekening BCA — 2026-07",
        query={"kind": "account", "period_type": "month", "month": "2026-07", "account": "BCA"},
        summary_label="📊 Ringkasan Rekening",
        account_filter="BCA",
    )
    account_context = _Context({browser.BROWSER_STATE_KEY: account_session}, bot=Bot())
    account_message = _Message(message_id=1701)
    account_message.chat_id = 42

    class AccountQuery:
        data = f"txb:{account_session['session_id']}:s:0"
        def __init__(self):
            self.message = account_message
            self.answers = []
        async def answer(self, text=None, show_alert=False):
            self.answers.append((text, show_alert))

    account_query = AccountQuery()
    account_update = types.SimpleNamespace(callback_query=account_query, effective_chat=types.SimpleNamespace(id=42))
    asyncio.run(browser.handle_transaction_browser_callback(account_update, account_context))

    assert account_query.answers == [(None, False)]
    assert account_message.replies and "Ringkasan Rekening" in account_message.replies[0][0]
    assert captured["chart_ids"] == ["acc_e", "acc_t"]
    assert captured["chart_title"] == "Time Series - Transaksi Rekening BCA — 2026-07"
    assert captured["send_photo"]["chat_id"] == 42
