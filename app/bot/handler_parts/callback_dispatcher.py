"""Routing-focused callback entry point with bounded compatibility fallback."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.callback_contracts import is_legacy_callback_data
from app.bot.handler_parts.bulk_flow import handle_bulk_callback, is_bulk_callback_data
from app.bot.handler_parts.callback_handler import legacy_callback_handler
from app.bot.handler_parts.common_imports import (
    is_authorized,
    reject_unauthorized,
    safe_edit_message,
    show_callback_loading,
)


async def reject_unknown_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Fail closed for callback data outside the audited callback inventory."""

    del context
    if not is_authorized(update):
        await reject_unauthorized(update)
        return
    query = update.callback_query
    await show_callback_loading(query)
    await safe_edit_message(query, "❌ Tombol tidak dikenali atau sesi sudah tidak valid.")


async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Dispatch callback data to a bounded handler or the legacy fallback."""

    data = str(getattr(getattr(update, "callback_query", None), "data", "") or "")
    if is_bulk_callback_data(data):
        await handle_bulk_callback(update, context)
        return
    if is_legacy_callback_data(data):
        await legacy_callback_handler(update, context)
        return
    await reject_unknown_callback(update, context)
