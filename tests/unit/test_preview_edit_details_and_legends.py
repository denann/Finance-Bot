"""Regressions for pending batch edits, category decisions, and Telegram legends."""

import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ExtBot
from telegram.error import TelegramError

from app.bot.handler_parts import transaction_flow as flow
from app.bot.handler_parts import message_handlers
from app.bot.handler_parts.common_imports import safe_edit_message
from app.bot.output import FinanceBot, icon_legend, _wire_length
from app.services import resolver_service as resolver
from tests.fakes.telegram import FakeMessage, FakeContext, FakeUpdate, FakeCallbackQuery


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setattr(resolver, "get_all_records", lambda name: resolver.DEFAULT_CATEGORY_ROWS if name == resolver.SHEET_CATEGORIES else [{"account_name": "BSI"}, {"account_name": "DANA"}])


def batch():
    return [
        {"kind": "transaction", "parsed": {"type": "expense", "description": name, "amount": amount, "category": category, "account": "BSI", "date": date, "tipe_pengeluaran": "Harian"}}
        for name, amount, category, date in [
            ("Momoyo Cilebut", 35000, "Other Expense", "2026-08-08"),
            ("Sayur", 20000, "Food & Beverage", "2026-08-09"),
            ("Breadcast", 6600, "Jajan", "2026-08-13"),
        ]
    ]


def test_selector_and_edit_return_full_updated_batch(offline):
    items = batch()
    selector = flow.build_mixed_edit_choose_prompt(items)
    for value in ("1. - *Momoyo Cilebut*", "2. - *Sayur*", "📅 2026-08-09", "📁 Food & Beverage", "🏦 BSI", "🏷️ Harian", "📝 Sayur"):
        assert value in selector
    context = FakeContext(user_data={"pending_mixed": items, "pending_preview_edit": {"scope": "mixed", "step": "direct_field", "field": "category", "index": 1}})
    update = FakeUpdate(message=FakeMessage())
    untouched = deepcopy([items[0], items[2]])
    asyncio.run(flow.handle_pending_preview_edit(update, context, "Jajan"))
    output = update.message.replies[-1]["text"]
    assert "2. - *Sayur*" in output and "📁 Jajan" in output
    assert "1. - *Momoyo Cilebut*" in output and "3. - *Breadcast*" in output
    assert "Ringkasan batch" not in output
    assert [items[0], items[2]] == untouched
    assert "pending_preview_edit" not in context.user_data
    assert update.message.replies[-1]["reply_markup"] is not None


def test_category_alias_waits_then_resumes_exact_item_and_other_edits(offline):
    items = batch()
    context = FakeContext(user_data={"pending_mixed": items, "pending_preview_edit": {"scope": "mixed", "step": "edit_item", "index": 1}})
    update = FakeUpdate(message=FakeMessage())
    asyncio.run(flow.handle_pending_preview_edit(update, context, "kategori: other, nominal: 25k"))
    assert items[1]["parsed"]["category"] == "Food & Beverage"
    assert items[1]["parsed"]["amount"] == 20000
    choice = context.user_data["pending_preview_edit"]["category_choice"]
    assert choice["suggested_category"] == "Other Expense"
    query = FakeCallbackQuery("unused")
    callback_update = FakeUpdate(callback_query=query)
    asyncio.run(flow.handle_preview_category_choice(callback_update, context, "mixed", "use", choice["id"]))
    assert items[1]["parsed"]["category"] == "Other Expense"
    assert items[1]["parsed"]["amount"] == 25000
    assert "2. - *Sayur*" in query.message.replies[-1]["text"]
    saved = deepcopy(items)
    asyncio.run(flow.handle_preview_category_choice(callback_update, context, "mixed", "use", choice["id"]))
    assert items == saved
    assert "tidak berlaku" in query.answers[-1]["text"]


def test_category_rewrite_keeps_other_staged_fields(offline):
    context = FakeContext(user_data={"pending_parsed": batch()[1]["parsed"], "pending_preview_edit": {"scope": "single", "step": "edit_item"}})
    update = FakeUpdate(message=FakeMessage())
    asyncio.run(flow.handle_pending_preview_edit(update, context, "kategori: other, nominal: 25k"))
    choice_id = context.user_data["pending_preview_edit"]["category_choice"]["id"]
    asyncio.run(flow.handle_preview_category_choice(FakeUpdate(callback_query=FakeCallbackQuery("unused")), context, "single", "rewrite", choice_id))
    asyncio.run(flow.handle_pending_preview_edit(update, context, "Jajan"))
    assert context.user_data["pending_parsed"]["amount"] == 25000
    assert context.user_data["pending_parsed"]["category"] == "Jajan"


def test_pending_expense_uses_expense_category_resolver(offline):
    pending = {"description": "Sayur", "amount": 20000, "category": "Food & Beverage", "due_date": "2026-08-09"}
    context = FakeContext(user_data={"pending_expense_confirm": pending, "pending_preview_edit": {"scope": "pending_expense", "step": "direct_field", "field": "category"}})
    asyncio.run(flow.handle_pending_preview_edit(FakeUpdate(message=FakeMessage()), context, "other"))
    choice = context.user_data["pending_preview_edit"]["category_choice"]
    assert choice["suggested_category"] == "Other Expense"
    assert pending["category"] == "Food & Beverage"
    asyncio.run(flow.handle_preview_category_choice(FakeUpdate(callback_query=FakeCallbackQuery("unused")), context, "pending_expense", "use", choice["id"]))
    assert pending["category"] == "Other Expense"
    assert "type" not in pending


def test_long_edit_prompt_preserves_every_character_and_final_keyboard():
    query = FakeCallbackQuery("unused")
    text = "x" * 3790 + "\n\n" + "y" * 100
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🚫 Batal", callback_data="cancel")]])
    asyncio.run(safe_edit_message(query, text, reply_markup=markup))
    messages = query.message.edits + query.message.replies
    assert "\n\n".join(message["text"] for message in messages) == text
    assert messages[0]["reply_markup"] is None
    assert messages[-1]["reply_markup"] == markup


def test_old_values_belong_to_selected_item():
    data = {"pending_mixed": batch()}
    current = flow.current_preview_edit_payload(data, {"scope": "mixed", "index": 1})
    assert "Nilai lama: *Food & Beverage*" in flow.build_preview_field_value_prompt("mixed", "category", current)
    assert "Contoh:" in flow.build_preview_field_value_prompt("mixed", "category", current)
    assert "Nilai lama: *BSI*" in flow.build_preview_field_value_prompt("mixed", "account", current)
    assert "Belum diisi" in flow.build_preview_field_value_prompt("single", "catatan", {})


def test_reported_debt_preview_displays_detected_account(offline, monkeypatch):
    monkeypatch.setattr(message_handlers, "is_authorized", lambda update: True)
    update = FakeUpdate(message=FakeMessage(text="Minjem tabungan naca 900k via bsi tanggal 18 agustus"))
    context = FakeContext()
    asyncio.run(message_handlers.debt_message_handler(update, context))
    assert context.user_data["pending_debt"]["account"] == "BSI"
    text = update.message.replies[-1]["text"]
    assert "🏦 Rekening: BSI" in text and "Rp900.000" in text
    assert "akan meminta rekening" not in text
    assert "belum disimpan" in text


def test_mixed_debt_keeps_account_and_own_identity(offline):
    item = flow.parse_mixed_item_local("Minjem tabungan naca 900k via bsi tanggal 18 agustus")
    assert item["parsed"]["account"] == "BSI"
    text = flow.build_mixed_edit_choose_prompt([batch()[0], item])
    assert "2. *🔴 Utang baru*" in text
    assert "Tabungan Naca" in text and "Rp900.000" in text


def test_legend_matches_text_and_buttons_without_treating_dates_as_expenses():
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🚫 Batal", callback_data="cancel")]])
    legend = icon_legend("2. - *Sayur* • Rp20.000\n📁 Jajan • 🏦 BSI\n📅 2026-08-09", markup)
    for expected in ("- = Pengeluaran", "📁 = Kategori", "🏦 = Rekening", "🚫 = Batal"):
        assert expected in legend
    assert "+ =" not in legend
    assert "- =" not in icon_legend("📅 2026-08-09")
    assert "- =" not in icon_legend("- Kategori: Jajan\n- Tipe: expense")
    assert "- = Pengeluaran" in icon_legend("1. *- Pengeluaran*")
    assert "+ = Pemasukan" in icon_legend(r"\+ Pemasukan")


@pytest.mark.parametrize("endpoint,field", [("sendMessage", "text"), ("editMessageText", "text"), ("sendPhoto", "caption"), ("editMessageCaption", "caption"), ("sendDocument", "caption")])
def test_transport_adds_legend_preserving_callbacks_and_entities(monkeypatch, endpoint, field):
    calls = []
    async def post(self, endpoint, data, **kwargs):
        calls.append((endpoint, data))
        return {"message_id": 42}
    monkeypatch.setattr(ExtBot, "_do_post", post)
    bot = FinanceBot("12345:TEST")
    payload = {"chat_id": 1, field: "📁 Jajan", "entities": [{"offset": 0, "length": 2, "type": "bold"}], "reply_markup": {"inline_keyboard": [[{"text": "✅ Simpan", "callback_data": "confirm:a_123"}]]}}
    original = deepcopy(payload)
    result = asyncio.run(bot._do_post(endpoint, payload))
    assert result["message_id"] == 42
    assert "Legenda ikon:" in calls[0][1][field]
    assert "✅ =" in calls[0][1][field]
    assert calls[0][1]["reply_markup"] == original["reply_markup"]
    assert calls[0][1]["entities"] == original["entities"]
    assert payload == original


def test_legend_overflow_preserves_original_and_returns_original_message_id(monkeypatch):
    calls = []
    async def post(self, endpoint, data, **kwargs):
        calls.append((endpoint, data))
        if len(calls) > 1:
            raise TelegramError("offline failure")
        return {"message_id": 42}
    monkeypatch.setattr(ExtBot, "_do_post", post)
    bot = FinanceBot("12345:TEST")
    text = "📁 " + "x" * 4080
    result = asyncio.run(bot._do_post("sendMessage", {"chat_id": 1, "text": text}))
    assert result["message_id"] == 42
    assert calls[0][1]["text"] == text
    assert calls[1][0] == "sendMessage"
    assert calls[1][1]["text"].startswith("Legenda ikon:")
    assert _wire_length(calls[1][1]["text"]) <= 4096


@pytest.mark.parametrize("mode,source,expected", [
    ("Markdown", "- *Sayur*", "- = Pengeluaran"),
    ("MarkdownV2", r"\- Sayur\n📁 Jajan", "📁 \\= Kategori"),
    ("HTML", "<b>📁 Jajan</b>", "📁 = Kategori"),
])
def test_public_send_message_api_preserves_format_and_message_id(monkeypatch, mode, source, expected):
    calls = []
    async def post(self, endpoint, data, **kwargs):
        calls.append(data)
        return {"message_id": 42, "date": 0, "chat": {"id": 1, "type": "private"}, "text": data["text"]}
    monkeypatch.setattr(ExtBot, "_do_post", post)
    bot = FinanceBot("12345:TEST")
    result = asyncio.run(bot.send_message(1, source, parse_mode=mode))
    assert result.message_id == 42
    assert calls[0]["text"].startswith(source + "\n\n")
    assert expected in calls[0]["text"]
    assert calls[0]["parse_mode"] == mode


def test_media_group_legends_follow_album_and_preserve_topic(monkeypatch):
    calls = []
    result = [{"message_id": 42}, {"message_id": 43}]
    async def post(self, endpoint, data, **kwargs):
        calls.append((endpoint, data))
        return result if endpoint == "sendMediaGroup" else {"message_id": 44}
    monkeypatch.setattr(ExtBot, "_do_post", post)
    bot = FinanceBot("12345:TEST")
    media = [InputMediaPhoto("photo1", caption="📊 Ringkasan"), {"type": "photo", "media": "photo2", "caption": "🏦 BSI"}]
    returned = asyncio.run(bot._do_post("sendMediaGroup", {"chat_id": 1, "message_thread_id": 10, "media": media}))
    assert returned is result
    assert calls[0][1]["media"] is media
    assert calls[1][0] == "sendMessage"
    assert calls[1][1]["message_thread_id"] == 10
    assert "📊 =" in calls[1][1]["text"] and "🏦 =" in calls[1][1]["text"]
