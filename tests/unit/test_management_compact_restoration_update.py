import ast
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
        for k, v in kwargs.items():
            setattr(self, k, v)


class Markup:
    def __init__(self, rows):
        self.inline_keyboard = rows


class Message:
    def __init__(self):
        self.replies = []
        self.message_id = 101
        self.chat_id = 1

    async def reply_text(self, text, parse_mode=None, reply_markup=None, **kwargs):
        self.replies.append((text, parse_mode, reply_markup))
        return types.SimpleNamespace(message_id=1000 + len(self.replies))


class Query:
    def __init__(self, data, message=None, events=None):
        self.data = data
        self.message = message or Message()
        self.from_user = types.SimpleNamespace(id=7)
        self.answers = []
        self.events = events if events is not None else []

    async def answer(self, text=None, show_alert=False):
        self.answers.append((text, show_alert))
        self.events.append("ack")


class Context:
    def __init__(self):
        self.user_data = {}
        self.args = []


_MISSING = object()


@contextmanager
def _temporary_modules(replacements):
    saved, attrs = {}, {}
    try:
        for name, module in replacements.items():
            saved[name] = sys.modules.get(name, _MISSING)
            parent_name, _, attr = name.rpartition(".")
            if parent_name:
                parent = importlib.import_module(parent_name)
                attrs[name] = (parent, getattr(parent, attr, _MISSING))
                setattr(parent, attr, module)
            sys.modules[name] = module
        yield
    finally:
        for name in reversed(tuple(replacements)):
            if name in attrs:
                parent, old = attrs[name]
                attr = name.rpartition(".")[2]
                if old is _MISSING:
                    if getattr(parent, attr, _MISSING) is replacements[name]:
                        delattr(parent, attr)
                else:
                    setattr(parent, attr, old)
            old = saved[name]
            if old is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


def _load_management_module():
    common = types.ModuleType("app.bot.handler_parts.common_imports")
    common.InlineKeyboardButton = Button
    common.InlineKeyboardMarkup = Markup
    common.format_rupiah = lambda value: f"Rp{int(float(value or 0))}"
    common.is_authorized = lambda update: True
    common.md_code_text = lambda value: str(value or "")
    common.md_safe = lambda value: str(value or "")
    async def reject(update): return None
    common.reject_unauthorized = reject
    async def safe_edit(query, text, parse_mode=None, reply_markup=None, **kwargs):
        query.events.append("render")
        query.message.replies.append((text, parse_mode, reply_markup))
    common.safe_edit_message = safe_edit
    async def send_preview(update, context, **kwargs):
        update.message.replies.append((kwargs["preview_text"], "Markdown", kwargs))
        return kwargs
    common.send_financial_mutation_preview = send_preview

    external = types.ModuleType("app.application.external_io")
    async def run_read(name, fn, *args, **kwargs):
        return fn(*args, **kwargs)
    external.run_sheets_read = run_read

    debt = types.ModuleType("app.services.debt_service")
    debt.get_debt_by_id_any_status = lambda debt_id: (2, {"id": debt_id, "person_name": "Raka", "type": "receivable", "remaining_amount": 50000})
    pending = types.ModuleType("app.services.pending_expense_service")
    pending.find_pending_by_ref = lambda pending_id: (2, {"id": pending_id, "subject": "Wifi", "description": "Wifi", "status": "pending", "amount": 10000, "account": "BCA"})
    recurring = types.ModuleType("app.services.recurring_service")
    recurring.get_recurring_rule_by_id = lambda rule_id: {"id": rule_id, "name": "Netflix", "amount": 65000, "is_active": "TRUE"}
    recurring.get_due_recurring_rules = lambda: []
    assets = types.ModuleType("app.services.net_worth_service")
    assets.get_assets = lambda active_only=False, refresh_gold=False: [{"id": "asset_1", "name": "Laptop", "current_value": 8000000}]

    name = "app.bot.handler_parts.management_browser"
    old = sys.modules.pop(name, None)
    try:
        with _temporary_modules({
            "app.bot.handler_parts.common_imports": common,
            "app.application.external_io": external,
            "app.services.debt_service": debt,
            "app.services.pending_expense_service": pending,
            "app.services.recurring_service": recurring,
            "app.services.net_worth_service": assets,
        }):
            module = importlib.import_module(name)
    finally:
        if old is not None:
            sys.modules[name] = old
        else:
            sys.modules.pop(name, None)
    return module


mgmt = _load_management_module()


def _update(message=None, query=None):
    return types.SimpleNamespace(
        message=message,
        callback_query=query,
        effective_user=types.SimpleNamespace(id=7),
        effective_chat=types.SimpleNamespace(id=1),
    )


def _debt_rows(n=14):
    return [{"id": f"debt_{i}", "person_name": f"P{i}", "type": "receivable", "remaining_amount": 1000 + i, "original_amount": 2000 + i, "description": f"Debt {i}"} for i in range(n)]


def _pending_rows(n=14):
    return [{"id": f"pend_{i}", "subject": f"Pending {i}", "amount": 1000 + i, "status": "pending", "account": "BCA"} for i in range(n)]


def _recurring_rows(n=14):
    return [{"id": f"rec_{i}", "name": f"Rule {i}", "amount": 1000 + i, "is_active": "TRUE", "frequency": "monthly", "next_run_date": "2026-08-10"} for i in range(n)]


def _asset_rows(n=14):
    return [{"id": f"asset_{i}", "name": f"Asset {i}", "current_value": 1000 + i, "category": "Other"} for i in range(n)]


@pytest.mark.parametrize(
    "start,key,prefix,rows",
    [
        (mgmt.start_debt_browser, mgmt.DEBT_BROWSER_KEY, "deb", _debt_rows()),
        (mgmt.start_pending_browser, mgmt.PENDING_BROWSER_KEY, "pen", _pending_rows()),
        (mgmt.start_recurring_browser, mgmt.RECURRING_BROWSER_KEY, "recb", _recurring_rows()),
        (mgmt.start_asset_browser, mgmt.ASSET_BROWSER_KEY, "asb", _asset_rows()),
    ],
)
def test_domain_browsers_are_compact_paginated_and_pure_navigation_is_provider_free(monkeypatch, start, key, prefix, rows):
    context, message = Context(), Message()
    if start is mgmt.start_pending_browser:
        asyncio.run(start(_update(message=message), context, rows, label="2026-08"))
    else:
        asyncio.run(start(_update(message=message), context, rows))
    state = context.user_data[key]
    assert len(state["records"]) == 14
    first_markup = message.replies[-1][2]
    # Six selectable rows + navigation/page indicator, not a huge static wall of text.
    selectable = [btn for row in first_markup.inline_keyboard for btn in row if getattr(btn, "callback_data", "").startswith(f"{prefix}:{state['session_id']}:d:")]
    assert len(selectable) == 6

    async def forbidden_read(*args, **kwargs):
        raise AssertionError("pure management pagination must not reread provider")
    monkeypatch.setattr(mgmt, "run_sheets_read", forbidden_read)
    events = []
    query = Query(f"{prefix}:{state['session_id']}:p:1", message=message, events=events)
    asyncio.run(mgmt.handle_management_browser_callback(_update(query=query), context))
    assert events == ["ack", "render"]
    assert query.answers == [(None, False)]


def test_pending_cancel_action_acks_then_fresh_revalidates_stable_id_before_preview(monkeypatch):
    context, message = Context(), Message()
    asyncio.run(mgmt.start_pending_browser(_update(message=message), context, _pending_rows(2)))
    state = context.user_data[mgmt.PENDING_BROWSER_KEY]
    events = []

    async def read(name, fn, pending_id):
        events.append(("read", name, pending_id))
        return 2, {"id": pending_id, "subject": "Fresh", "status": "pending", "amount": 7777, "account": "BCA"}
    async def preview(update, ctx, **kwargs):
        events.append(("preview", kwargs["operation"], kwargs["payload"]))
    monkeypatch.setattr(mgmt, "run_sheets_read", read)
    monkeypatch.setattr(mgmt, "send_financial_mutation_preview", preview)

    query = Query(f"pen:{state['session_id']}:c:1", message=message, events=events)
    asyncio.run(mgmt.handle_management_browser_callback(_update(query=query), context))
    assert events[0] == "ack"
    assert events[1] == ("read", "management_pending_revalidate", "pend_1")
    assert events[2] == ("preview", "pending_cancel", {"pending_id": "pend_1"})


def test_debt_edit_action_revalidates_id_and_does_not_mutate_from_snapshot(monkeypatch):
    context, message = Context(), Message()
    asyncio.run(mgmt.start_debt_browser(_update(message=message), context, _debt_rows(2)))
    state = context.user_data[mgmt.DEBT_BROWSER_KEY]
    calls = []
    async def read(name, fn, debt_id):
        calls.append((name, debt_id))
        return 4, {"id": debt_id, "person_name": "Fresh Person", "type": "receivable", "remaining_amount": 3333}
    monkeypatch.setattr(mgmt, "run_sheets_read", read)
    query = Query(f"deb:{state['session_id']}:e:0", message=message)
    asyncio.run(mgmt.handle_management_browser_callback(_update(query=query), context))
    assert calls == [("management_debt_revalidate", "debt_0")]
    assert "/debt_edit debt_0" in message.replies[-1][0]


@pytest.mark.parametrize("prefix,key,start,rows,action,expected_operation", [
    ("recb", mgmt.RECURRING_BROWSER_KEY, mgmt.start_recurring_browser, _recurring_rows(2), "o", "recurring_off"),
    ("asb", mgmt.ASSET_BROWSER_KEY, mgmt.start_asset_browser, _asset_rows(2), "o", "asset_off"),
])
def test_recurring_and_asset_mutation_actions_fresh_revalidate_then_preview(monkeypatch, prefix, key, start, rows, action, expected_operation):
    context, message = Context(), Message()
    asyncio.run(start(_update(message=message), context, rows))
    state = context.user_data[key]
    reads, previews = [], []
    async def read(name, fn, *args, **kwargs):
        reads.append((name, args))
        if prefix == "recb":
            return {"id": args[0], "name": "Fresh Rule", "amount": 1, "is_active": "TRUE"}
        return [{"id": args[0] if args else "asset_0", "name": "Fresh Asset", "current_value": 1, "is_active": "TRUE"}]
    async def preview(update, ctx, **kwargs): previews.append(kwargs)
    monkeypatch.setattr(mgmt, "run_sheets_read", read)
    monkeypatch.setattr(mgmt, "send_financial_mutation_preview", preview)
    query = Query(f"{prefix}:{state['session_id']}:{action}:0", message=message)
    asyncio.run(mgmt.handle_management_browser_callback(_update(query=query), context))
    assert reads and previews
    assert previews[0]["operation"] == expected_operation


def test_replaced_domain_session_rejects_old_callback():
    context, message = Context(), Message()
    asyncio.run(mgmt.start_asset_browser(_update(message=message), context, _asset_rows(2)))
    old_sid = context.user_data[mgmt.ASSET_BROWSER_KEY]["session_id"]
    asyncio.run(mgmt.start_asset_browser(_update(message=message), context, _asset_rows(2)))
    query = Query(f"asb:{old_sid}:p:0", message=message)
    asyncio.run(mgmt.handle_management_browser_callback(_update(query=query), context))
    assert query.answers and query.answers[0][1] is True
    assert "stale" in (query.answers[0][0] or "").lower()


def test_category_listing_remains_proportional_without_forced_browser_state():
    source = open("app/bot/handler_parts/category_flow.py", encoding="utf-8").read()
    body = source[source.index("async def kategori_handler"):source.index("async def edit_kategori_handler")]
    assert "get_category_records_safe" in body
    assert "compact_browser" not in body
    assert "pagination" not in body


def test_management_command_and_callback_wiring_uses_domain_specific_browser_entrypoints():
    wiring = {
        "app/bot/handler_parts/command_handlers.py": (
            "start_pending_browser(update, context, result.get(\"items\") or [], label=label)",
            "start_debt_browser(update, context, active_debts)",
        ),
        "app/bot/handler_parts/health_recurring_export.py": (
            "start_recurring_browser(update, context, rules)",
        ),
        "app/bot/handler_parts/networth_assets.py": (
            "start_asset_browser(update, context, assets)",
        ),
        "app/bot/handler_parts/callback_dispatcher.py": (
            "is_management_browser_callback_data(data)",
            "handle_management_browser_callback(update, context)",
        ),
    }
    for path, needles in wiring.items():
        source = open(path, encoding="utf-8").read()
        for needle in needles:
            assert needle in source, f"missing management browser wiring in {path}: {needle}"


def test_debt_settle_and_void_actions_bridge_exact_stable_id_to_existing_handlers(monkeypatch):
    context, message = Context(), Message()
    rows = _debt_rows(2)
    rows[0]["person_name"] = "John Doe"
    asyncio.run(mgmt.start_debt_browser(_update(message=message), context, rows))
    state = context.user_data[mgmt.DEBT_BROWSER_KEY]

    async def read(name, fn, debt_id):
        return 4, {
            "id": debt_id,
            "person_name": "John Doe",
            "type": "receivable",
            "remaining_amount": 3333,
        }
    monkeypatch.setattr(mgmt, "run_sheets_read", read)

    captured = []
    handlers = types.ModuleType("app.bot.handler_parts.command_handlers")
    async def settle(update, ctx):
        captured.append(("settle", list(ctx.args), dict(ctx.user_data.get("last_debt_map") or {}), ctx.user_data.get("last_debt_person")))
    async def void(update, ctx):
        captured.append(("void", list(ctx.args)))
    handlers.debt_settle_handler = settle
    handlers.debt_void_handler = void

    context.args = ["original"]
    with _temporary_modules({"app.bot.handler_parts.command_handlers": handlers}):
        q1 = Query(f"deb:{state['session_id']}:s:0", message=message)
        asyncio.run(mgmt.handle_management_browser_callback(_update(query=q1), context))
        q2 = Query(f"deb:{state['session_id']}:v:0", message=message)
        asyncio.run(mgmt.handle_management_browser_callback(_update(query=q2), context))

    assert captured[0][0] == "settle"
    assert captured[0][1] == ["John Doe", "1"]
    assert captured[0][2]["1"]["debt_id"] == "debt_0"
    assert captured[0][3] == "John Doe"
    assert captured[1] == ("void", ["debt_0"])
    assert context.args == ["original"]


def test_recurring_inactive_detail_hides_off_and_run_actions():
    context, message = Context(), Message()
    rows = _recurring_rows(1)
    rows[0]["is_active"] = "FALSE"
    asyncio.run(mgmt.start_recurring_browser(_update(message=message), context, rows))
    state = context.user_data[mgmt.RECURRING_BROWSER_KEY]
    query = Query(f"recb:{state['session_id']}:d:0", message=message)
    asyncio.run(mgmt.handle_management_browser_callback(_update(query=query), context))
    markup = message.replies[-1][2]
    callbacks = [getattr(btn, "callback_data", "") for row in markup.inline_keyboard for btn in row]
    assert not any(":o:" in value for value in callbacks)
    assert not any(":r:" in value for value in callbacks)
    assert any(":e:" in value for value in callbacks)


def test_asset_off_rejects_authoritatively_inactive_row(monkeypatch):
    context, message = Context(), Message()
    rows = _asset_rows(1)
    rows[0]["is_active"] = "TRUE"
    asyncio.run(mgmt.start_asset_browser(_update(message=message), context, rows))
    state = context.user_data[mgmt.ASSET_BROWSER_KEY]

    async def read(name, fn, *args, **kwargs):
        return [{"id": "asset_0", "name": "Fresh Asset", "current_value": 1, "is_active": "FALSE"}]
    async def forbidden_preview(*args, **kwargs):
        raise AssertionError("inactive asset must not reach mutation preview")
    monkeypatch.setattr(mgmt, "run_sheets_read", read)
    monkeypatch.setattr(mgmt, "send_financial_mutation_preview", forbidden_preview)

    query = Query(f"asb:{state['session_id']}:o:0", message=message)
    asyncio.run(mgmt.handle_management_browser_callback(_update(query=query), context))
    assert "nonaktif" in message.replies[-1][0].lower()


@pytest.mark.parametrize(
    "start,key,prefix,rows",
    [
        (mgmt.start_debt_browser, mgmt.DEBT_BROWSER_KEY, "deb", _debt_rows(8)),
        (mgmt.start_pending_browser, mgmt.PENDING_BROWSER_KEY, "pen", _pending_rows(8)),
        (mgmt.start_recurring_browser, mgmt.RECURRING_BROWSER_KEY, "recb", _recurring_rows(8)),
        (mgmt.start_asset_browser, mgmt.ASSET_BROWSER_KEY, "asb", _asset_rows(8)),
    ],
)
def test_domain_detail_and_back_navigation_are_session_local(monkeypatch, start, key, prefix, rows):
    context, message = Context(), Message()
    if start is mgmt.start_pending_browser:
        asyncio.run(start(_update(message=message), context, rows, label="2026-08"))
    else:
        asyncio.run(start(_update(message=message), context, rows))
    state = context.user_data[key]

    async def forbidden_read(*args, **kwargs):
        raise AssertionError("read-only management detail/back must not reread provider")
    monkeypatch.setattr(mgmt, "run_sheets_read", forbidden_read)

    detail = Query(f"{prefix}:{state['session_id']}:d:6", message=message)
    asyncio.run(mgmt.handle_management_browser_callback(_update(query=detail), context))
    back = Query(f"{prefix}:{state['session_id']}:b:6", message=message)
    asyncio.run(mgmt.handle_management_browser_callback(_update(query=back), context))
    assert detail.answers == [(None, False)]
    assert back.answers == [(None, False)]
    assert context.user_data[key]["page"] == 1


def test_pending_browser_preserves_requested_period_label_in_compact_view():
    context, message = Context(), Message()
    asyncio.run(mgmt.start_pending_browser(_update(message=message), context, _pending_rows(2), label="September 2026"))
    assert "September 2026" in message.replies[-1][0]



def _load_exact_hutang_functions(run_read):
    """Compile only the exact Repair command functions with controlled seams."""
    source = open("app/bot/handler_parts/command_handlers.py", encoding="utf-8").read()
    tree = ast.parse(source)
    wanted = {"_build_debt_overview_text", "_active_debts_from_person_summary", "hutang_handler"}
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted]
    namespace = {
        "Update": object,
        "ContextTypes": types.SimpleNamespace(DEFAULT_TYPE=object),
        "is_authorized": lambda update: True,
        "reject_unauthorized": lambda update: None,
        "run_sheets_read": run_read,
        "get_debt_person_detail": object(),
        "get_debt_person_summary": object(),
        "debt_detail_sort_key_for_display": lambda debt: (str(debt.get("created_at") or ""), int(debt.get("_row_index") or 0)),
        "format_rupiah": lambda value: f"Rp{int(float(value or 0))}",
        "md_safe": lambda value: str(value or ""),
        "start_debt_browser": mgmt.start_debt_browser,
    }
    module = ast.Module(body=nodes, type_ignores=[])
    exec(compile(module, "command_handlers.py", "exec"), namespace)
    return namespace


def test_bare_hutang_preserves_aggregate_overview_and_reuses_same_summary_rows_for_browser():
    payable = {"id": "debt_p", "person_name": "Raka", "type": "payable", "remaining_amount": 100000, "original_amount": 100000, "description": "Pinjam", "created_at": "2026-08-01"}
    receivable = {"id": "debt_r", "person_name": "Dimas", "type": "receivable", "remaining_amount": 250000, "original_amount": 250000, "description": "Talang", "created_at": "2026-08-02"}
    summary = {
        "total_payable": 100000,
        "total_receivable": 250000,
        "payables": [{"person_name": "Raka", "remaining_amount": 100000, "debt_count": 1, "details": [payable]}],
        "receivables": [{"person_name": "Dimas", "remaining_amount": 250000, "debt_count": 1, "details": [receivable]}],
        "balanced": [],
    }
    calls = []
    async def run_read(name, fn, *args, **kwargs):
        calls.append((name, args, kwargs))
        assert name == "get_debt_person_summary"
        return summary

    ns = _load_exact_hutang_functions(run_read)
    context, message = Context(), Message()
    context.args = []
    asyncio.run(ns["hutang_handler"](_update(message=message), context))

    assert len(calls) == 1
    assert len(message.replies) == 2
    overview = message.replies[0][0]
    assert "Utang Anda" in overview and "Rp100000" in overview
    assert "Piutang Anda" in overview and "Rp250000" in overview
    assert "lebih banyak dihutangi" in overview and "Rp150000" in overview
    state = context.user_data[mgmt.DEBT_BROWSER_KEY]
    assert [row["id"] for row in state["records"]] == ["debt_r", "debt_p"]
    assert "Utang & Piutang Aktif" in message.replies[1][0]


def test_hutang_person_enters_compact_browser_and_pagination_stays_provider_free(monkeypatch):
    rows = [
        {"id": f"john_{i}", "person_name": "John Doe", "type": "receivable", "remaining_amount": 1000 + i, "original_amount": 2000 + i, "description": f"Debt {i}", "created_at": f"2026-08-{i+1:02d}", "_row_index": i + 2}
        for i in range(8)
    ]
    detail = {
        "person_name": "John Doe",
        "details": list(rows),
        "active_details": list(rows),
        "net_remaining": sum(row["remaining_amount"] for row in rows),
        "net_type": "receivable",
        "receivable": {"original": 0, "paid": 0, "paid_pct": 0},
        "payable": {"original": 0, "paid": 0, "paid_pct": 0},
    }
    calls = []
    async def run_read(name, fn, *args, **kwargs):
        calls.append((name, args, kwargs))
        assert name == "get_debt_person_detail"
        assert args == ("John Doe",)
        assert kwargs == {"include_settled": True}
        return detail

    ns = _load_exact_hutang_functions(run_read)
    context, message = Context(), Message()
    context.args = ["John", "Doe"]
    asyncio.run(ns["hutang_handler"](_update(message=message), context))

    assert len(calls) == 1
    assert len(message.replies) == 1
    state = context.user_data[mgmt.DEBT_BROWSER_KEY]
    assert state["title"] == "Utang & Piutang — John Doe"
    assert len(state["records"]) == 8
    assert context.user_data["last_debt_person"] == "John Doe"
    assert context.user_data["last_debt_map"]["8"]["debt_id"] == "john_0"
    assert "Halaman 1/2" in message.replies[0][0]
    assert "John Doe hutang ke Anda" in message.replies[0][0]

    async def forbidden_read(*args, **kwargs):
        raise AssertionError("pure /hutang <person> pagination must stay session-local")
    monkeypatch.setattr(mgmt, "run_sheets_read", forbidden_read)
    query = Query(f"deb:{state['session_id']}:p:1", message=message)
    asyncio.run(mgmt.handle_management_browser_callback(_update(query=query), context))
    assert query.answers == [(None, False)]
    assert "Halaman 2/2" in message.replies[-1][0]


def _compile_exact_function(path: str, name: str, namespace: dict):
    """Compile one production function so the regression can control only its external seams."""
    source = open(path, encoding="utf-8").read()
    tree = ast.parse(source)
    node = next(
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )
    module = ast.Module(body=[node], type_ignores=[])
    exec(compile(module, path, "exec"), namespace)
    return namespace[name]


def _binding_aware_debt_handlers():
    """Load the exact debt preview functions with the real pending-action binding contract."""
    class BadRequest(Exception):
        pass

    reply_ns = {
        "split_long_message": lambda text: [str(text)],
        "BadRequest": BadRequest,
    }
    reply_message_safely = _compile_exact_function(
        "app/bot/handler_parts/common_imports.py", "reply_message_safely", reply_ns
    )

    keyboard_ns = {"InlineKeyboardButton": Button, "InlineKeyboardMarkup": Markup}
    confirm_keyboard = _compile_exact_function(
        "app/bot/keyboards.py", "confirm_keyboard", keyboard_ns
    )

    async def reject(_update):
        return None

    async def run_read(_name, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def preview_void_debt(debt_ref, _last_map):
        return {
            "success": True,
            "debt": {
                "id": debt_ref,
                "person_name": "John Doe",
                "type": "receivable",
                "remaining_amount": 3333,
            },
        }

    void_ns = {
        "Update": object,
        "ContextTypes": types.SimpleNamespace(DEFAULT_TYPE=object),
        "is_authorized": lambda _update: True,
        "reject_unauthorized": reject,
        "parse_debt_void_args": lambda args: {"mode": "ref", "debt_ref": args[0]},
        "run_sheets_read": run_read,
        "preview_void_debts_by_person": lambda *_a, **_k: None,
        "preview_void_debt": preview_void_debt,
        "build_debt_void_preview_text": lambda _preview: "Void preview",
        "md_safe": lambda value: str(value or ""),
        "format_rupiah": lambda value: f"Rp{int(float(value or 0))}",
        "confirm_keyboard": confirm_keyboard,
        "reply_message_safely": reply_message_safely,
    }
    debt_void_handler = _compile_exact_function(
        "app/bot/handler_parts/command_handlers.py", "debt_void_handler", void_ns
    )

    async def prepare_settle(_context, _parsed):
        return {
            "success": True,
            "person_name": "John Doe",
            "selection": "1",
            "debt_ids": ["debt_0"],
            "summary": {"net_type": "receivable", "net_abs": 3333},
            "net_type": "receivable",
            "amount": 3333,
            "shortage": 0,
            "overpayment": 0,
            "account": "BCA",
        }

    settle_ns = {
        "Update": object,
        "ContextTypes": types.SimpleNamespace(DEFAULT_TYPE=object),
        "is_authorized": lambda _update: True,
        "reject_unauthorized": reject,
        "parse_debt_settle_command_args": lambda _args: {},
        "prepare_selected_debt_settle_payload": prepare_settle,
        "build_selected_debt_settle_preview_text": lambda _payload: "Settle preview",
        "cancel_keyboard": lambda: Markup([]),
        "account_keyboard": lambda *_a, **_k: Markup([]),
        "selected_debt_settle_overpay_keyboard": lambda: Markup([]),
        "confirm_keyboard": confirm_keyboard,
        "reply_message_safely": reply_message_safely,
    }
    debt_settle_handler = _compile_exact_function(
        "app/bot/handler_parts/command_handlers.py", "debt_settle_handler", settle_ns
    )

    handlers = types.ModuleType("app.bot.handler_parts.command_handlers")
    handlers.debt_void_handler = debt_void_handler
    handlers.debt_settle_handler = debt_settle_handler
    return handlers


class _PreviewBindingMessage(Message):
    """Represent browser message 101 whose reply preview is Telegram message 202."""
    def __init__(self):
        super().__init__()
        self.message_id = 101

    async def reply_text(self, text, parse_mode=None, reply_markup=None, **kwargs):
        self.replies.append((text, parse_mode, reply_markup))
        return types.SimpleNamespace(message_id=202)


def _debt_browser_state_for_binding(context: Context) -> dict:
    state = {
        "session_id": "debt-bind",
        "records": [{
            "id": "debt_0",
            "person_name": "John Doe",
            "type": "receivable",
            "remaining_amount": 3333,
            "original_amount": 3333,
            "description": "Talangan",
        }],
        "page": 0,
        "title": "Utang & Piutang — John Doe",
        "overview": "",
    }
    context.user_data[mgmt.DEBT_BROWSER_KEY] = state
    return state


def _assert_preview_action_is_exact_message_bound(context: Context, *, expected_flow: str):
    from app.bot.pending_actions import PendingActionError, consume_pending_action, get_pending_action

    store = context.user_data.get("_pending_actions") or {}
    assert len(store) == 1
    action_id = next(iter(store))
    assert get_pending_action(context.user_data, action_id)["preview_message_id"] == 202

    with pytest.raises(PendingActionError) as wrong:
        consume_pending_action(
            context.user_data,
            action_id,
            owner_user_id=7,
            message_id=101,
            expected_flow=expected_flow,
        )
    assert wrong.value.code == "wrong_message"

    accepted = consume_pending_action(
        context.user_data,
        action_id,
        owner_user_id=7,
        message_id=202,
        expected_flow=expected_flow,
    )
    assert accepted["status"] == "consumed"

    with pytest.raises(PendingActionError) as duplicate:
        consume_pending_action(
            context.user_data,
            action_id,
            owner_user_id=7,
            message_id=202,
            expected_flow=expected_flow,
        )
    assert duplicate.value.code == "consumed"


def test_debt_browser_void_preview_binds_confirmation_to_actual_preview_message(monkeypatch):
    """browser 101 -> Void -> preview 202 -> only confirm 202 may consume once."""
    from app.bot.pending_actions import pending_action_request_context

    context, message = Context(), _PreviewBindingMessage()
    state = _debt_browser_state_for_binding(context)

    async def read(_name, _fn, debt_id):
        return 4, {
            "id": debt_id,
            "person_name": "John Doe",
            "type": "receivable",
            "remaining_amount": 3333,
        }

    monkeypatch.setattr(mgmt, "run_sheets_read", read)
    handlers = _binding_aware_debt_handlers()
    query = Query(f"deb:{state['session_id']}:v:0", message=message)

    with _temporary_modules({"app.bot.handler_parts.command_handlers": handlers}):
        with pending_action_request_context(context.user_data, owner_user_id=7, preview_message_id=101):
            asyncio.run(mgmt.handle_management_browser_callback(_update(query=query), context))

    assert query.answers == [(None, False)]
    assert message.replies[-1][0] == "Void preview"
    _assert_preview_action_is_exact_message_bound(context, expected_flow="debt_void")


def test_debt_browser_settle_sibling_preview_uses_same_exact_message_binding(monkeypatch):
    """Immediate debt-settle confirmation shares the same binding-aware reply boundary."""
    from app.bot.pending_actions import pending_action_request_context

    context, message = Context(), _PreviewBindingMessage()
    state = _debt_browser_state_for_binding(context)

    async def read(_name, _fn, debt_id):
        return 4, {
            "id": debt_id,
            "person_name": "John Doe",
            "type": "receivable",
            "remaining_amount": 3333,
        }

    monkeypatch.setattr(mgmt, "run_sheets_read", read)
    handlers = _binding_aware_debt_handlers()
    query = Query(f"deb:{state['session_id']}:s:0", message=message)

    with _temporary_modules({"app.bot.handler_parts.command_handlers": handlers}):
        with pending_action_request_context(context.user_data, owner_user_id=7, preview_message_id=101):
            asyncio.run(mgmt.handle_management_browser_callback(_update(query=query), context))

    assert query.answers == [(None, False)]
    assert message.replies[-1][0] == "Settle preview"
    assert context.user_data["last_debt_map"]["1"]["debt_id"] == "debt_0"
    _assert_preview_action_is_exact_message_bound(context, expected_flow="debt_settle")
