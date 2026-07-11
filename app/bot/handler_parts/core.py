"""Core Telegram error handler and compatibility reply exports."""

from telegram.error import BadRequest
from telegram.ext import ContextTypes

from app.bot.handler_parts.common_imports import (
    TELEGRAM_SAFE_MESSAGE_LIMIT,
    edit_message_safely,
    md_safe,
    reply_long_markdown,
    reply_message_safely,
    reply_update_safely,
    safe_edit_message,
    show_callback_loading,
    split_long_message,
)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Translate handler failures into the existing safe Telegram response."""

    error = getattr(context, "error", None)
    err_text = str(error or "Unknown error")

    from app.services.operation_errors import AtomicOperationError

    if isinstance(error, AtomicOperationError):
        if error.reconciliation_required:
            user_msg = (
                "❌ *Hasil penyimpanan belum dapat dipastikan.*\n\n"
                "Jangan ulangi aksi ini sebelum data diperiksa atau direkonsiliasi."
            )
        else:
            user_msg = (
                "❌ *Penyimpanan gagal dan operasi dibatalkan.*\n\n"
                "Tidak ada hasil sukses yang dinyatakan. Buat preview baru sebelum mencoba lagi."
            )
    elif isinstance(error, BadRequest) and (
        "Message_too_long" in err_text or "Message is too long" in err_text
    ):
        user_msg = (
            "❌ *Terjadi error saat menampilkan pesan.*\n\n"
            "Output terlalu panjang untuk Telegram. Saya sudah menahan crash-nya, "
            "coba ulangi atau kirim input dalam beberapa batch yang lebih kecil."
        )
    else:
        user_msg = (
            "❌ *Terjadi error saat memproses tombol/input.*\n\n"
            f"Detail: `{md_safe(err_text[:250])}`\n\n"
            "Coba ulangi dari step terakhir. Kalau masih muncul, kirim log ini untuk dicek."
        )

    try:
        effective_message = getattr(update, "effective_message", None)
        callback_query = getattr(update, "callback_query", None)
        if effective_message:
            await effective_message.reply_text(user_msg, parse_mode="Markdown")
        elif callback_query and callback_query.message:
            await callback_query.message.reply_text(user_msg, parse_mode="Markdown")
    except Exception:
        pass

    print(f"[ERROR_HANDLER] {type(error).__name__ if error else 'Unknown'}: {err_text}")


__all__ = [
    "TELEGRAM_SAFE_MESSAGE_LIMIT",
    "edit_message_safely",
    "error_handler",
    "reply_long_markdown",
    "reply_message_safely",
    "reply_update_safely",
    "safe_edit_message",
    "show_callback_loading",
    "split_long_message",
]

