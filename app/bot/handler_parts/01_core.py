# Auto-split from app/bot/handlers.py for readability.
# Loaded by app/bot/handlers.py into one shared namespace.
# Common imports are centralized here so every part has explicit dependencies.
from app.bot.handler_parts.common_imports import *

# ── Helper ────────────────────────────────────────────────────────────────────

TELEGRAM_SAFE_MESSAGE_LIMIT = 3800


def split_long_message(text: str, max_len: int = TELEGRAM_SAFE_MESSAGE_LIMIT) -> list[str]:
    """Split pesan panjang Telegram menjadi beberapa bagian aman."""
    text = str(text or "").strip()
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""

    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue

        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= max_len:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(block) <= max_len:
            current = block
            continue

        line_current = ""
        for line in block.splitlines():
            candidate_line = f"{line_current}\n{line}".strip() if line_current else line
            if len(candidate_line) <= max_len:
                line_current = candidate_line
            else:
                if line_current:
                    chunks.append(line_current)
                if len(line) > max_len:
                    for i in range(0, len(line), max_len):
                        chunks.append(line[i:i + max_len])
                    line_current = ""
                else:
                    line_current = line

        if line_current:
            chunks.append(line_current)

    if current:
        chunks.append(current)

    return chunks


async def reply_long_markdown(update: Update, text: str):
    """Kirim Markdown panjang dengan fallback plain text kalau Markdown error."""
    for part in split_long_message(text):
        try:
            await update.message.reply_text(part, parse_mode="Markdown")
        except BadRequest:
            await update.message.reply_text(part)


async def reply_message_safely(message, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    """Kirim pesan biasa secara aman, termasuk pesan panjang dan Markdown error.

    Jika pesan di-split, tombol ditempel di chunk terakhir supaya user baca dulu
    lalu tombol muncul di bawah.
    """
    text = str(text or "").strip() or " "
    chunks = split_long_message(text)
    for idx, chunk in enumerate(chunks):
        markup = reply_markup if idx == len(chunks) - 1 else None
        try:
            await message.reply_text(chunk, parse_mode=parse_mode, reply_markup=markup, **kwargs)
        except BadRequest:
            await message.reply_text(chunk, reply_markup=markup, **kwargs)


async def reply_update_safely(update: Update, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    if update.message:
        await reply_message_safely(update.message, text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)


async def safe_edit_message(query, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    """Edit pesan callback secara aman.

    Telegram membatasi panjang edit_message_text sekitar 4096 karakter.
    Kalau pesan terlalu panjang, bagian pertama akan diedit ke message lama,
    sisanya dikirim sebagai reply lanjutan supaya callback tidak crash.
    Markdown error juga otomatis fallback ke plain text.
    """
    text = str(text or "").strip()
    if not text:
        text = " "

    chunks = split_long_message(text)
    first = chunks[0]

    if len(chunks) > 1:
        suffix = "\n\n📄 *Pesan terlalu panjang, detail lanjutan dikirim di bawah.*"
        max_first_len = TELEGRAM_SAFE_MESSAGE_LIMIT - len(suffix) - 10
        first = first[:max_first_len].rstrip() + suffix

    async def _edit(payload: str, mode: str | None, markup):
        return await query.message.edit_text(
            payload,
            parse_mode=mode,
            reply_markup=markup,
            **kwargs,
        )

    try:
        await _edit(first, parse_mode, reply_markup)
    except BadRequest as exc:
        err = str(exc).lower()
        if "message is not modified" in err:
            pass
        elif "message_too_long" in err or "message is too long" in err or len(first) > 4096:
            safe_first = first[:3500].rstrip() + "\n\n📄 Pesan terlalu panjang, detail lanjutan dikirim di bawah."
            try:
                await _edit(safe_first, None, reply_markup)
            except Exception:
                await query.message.reply_text(safe_first, reply_markup=reply_markup)
        else:
            try:
                await _edit(first, None, reply_markup)
            except BadRequest:
                await query.message.reply_text(first, reply_markup=reply_markup)

    for chunk in chunks[1:]:
        try:
            await query.message.reply_text(chunk, parse_mode=parse_mode)
        except BadRequest:
            await query.message.reply_text(chunk)


async def show_callback_loading(query, text: str = "⏳ *Memproses pilihan...*"):
    """Tampilkan loading singkat dan hapus inline keyboard agar tombol tidak double-click."""
    try:
        await safe_edit_message(query, text, parse_mode="Markdown")
    except Exception:
        # Loading tidak boleh menggagalkan action utama.
        pass


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Error handler global agar exception callback tetap diberi tahu ke Telegram."""
    error = getattr(context, "error", None)
    err_text = str(error or "Unknown error")

    if isinstance(error, BadRequest) and ("Message_too_long" in err_text or "Message is too long" in err_text):
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



