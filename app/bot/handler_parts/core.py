"""Core Telegram helpers for authorization, safe replies, message splitting, and error handling."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *

# ── Helper ────────────────────────────────────────────────────────────────────

TELEGRAM_SAFE_MESSAGE_LIMIT = 3800


# Helper for split long message.
def split_long_message(text: str, max_len: int = TELEGRAM_SAFE_MESSAGE_LIMIT) -> list[str]:
    """Coordinate the split long message logic in the Telegram handler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        max_len: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    text = str(text or "").strip()
    # Validate missing text before continuing.
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""

    for block in text.split("\n\n"):
        block = block.strip()
        # Validate missing block before continuing.
        if not block:
            # Skip the rest of this loop iteration after handling this case.
            continue

        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= max_len:
            current = candidate
            # Skip the rest of this loop iteration after handling this case.
            continue

        if current:
            # Append the current value to chunks.
            chunks.append(current)
            current = ""

        if len(block) <= max_len:
            current = block
            # Skip the rest of this loop iteration after handling this case.
            continue

        line_current = ""
        # Iterate through each line.
        for line in block.splitlines():
            candidate_line = f"{line_current}\n{line}".strip() if line_current else line
            if len(candidate_line) <= max_len:
                line_current = candidate_line
            # Use the fallback path when no earlier branch matched.
            else:
                if line_current:
                    # Append the current value to chunks.
                    chunks.append(line_current)
                if len(line) > max_len:
                    # Iterate through each i.
                    for i in range(0, len(line), max_len):
                        # Append the current value to chunks.
                        chunks.append(line[i:i + max_len])
                    line_current = ""
                # Use the fallback path when no earlier branch matched.
                else:
                    line_current = line

        if line_current:
            # Append the current value to chunks.
            chunks.append(line_current)

    if current:
        # Append the current value to chunks.
        chunks.append(current)

    return chunks


async def reply_long_markdown(update: Update, text: str):
    """Handle the asynchronous reply long markdown flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Iterate through each part.
    for part in split_long_message(text):
        # Run this operation in a guarded block so failures can be handled.
        try:
            await update.message.reply_text(part, parse_mode="Markdown")
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Send the Telegram response before continuing.
            await update.message.reply_text(part)


async def reply_message_safely(message, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    """Handle the asynchronous reply message safely flow in the Telegram handler layer.

    Args:
        message: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        text: Raw text input to parse, normalize, validate, or display.
        parse_mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        reply_markup: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        **kwargs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    text = str(text or "").strip() or " "
    chunks = split_long_message(text)
    # Iterate through each idx, chunk.
    for idx, chunk in enumerate(chunks):
        markup = reply_markup if idx == len(chunks) - 1 else None
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Send the Telegram response before continuing.
            await message.reply_text(chunk, parse_mode=parse_mode, reply_markup=markup, **kwargs)
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Send the Telegram response before continuing.
            await message.reply_text(chunk, reply_markup=markup, **kwargs)


async def reply_update_safely(update: Update, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    """Handle the asynchronous reply update safely flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        text: Raw text input to parse, normalize, validate, or display.
        parse_mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        reply_markup: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        **kwargs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    if update.message:
        # Send the Telegram response before continuing.
        await reply_message_safely(update.message, text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)


async def safe_edit_message(query, text: str, parse_mode: str | None = None, reply_markup=None, **kwargs):
    """Handle the asynchronous safe edit message flow in the Telegram handler layer.

    Args:
        query: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        text: Raw text input to parse, normalize, validate, or display.
        parse_mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        reply_markup: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        **kwargs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    text = str(text or "").strip()
    # Validate missing text before continuing.
    if not text:
        text = " "

    chunks = split_long_message(text)
    first = chunks[0]

    if len(chunks) > 1:
        suffix = "\n\n📄 *Pesan terlalu panjang, detail lanjutan dikirim di bawah.*"
        max_first_len = TELEGRAM_SAFE_MESSAGE_LIMIT - len(suffix) - 10
        first = first[:max_first_len].rstrip() + suffix

    async def _edit(payload: str, mode: str | None, markup):
        """Handle the asynchronous edit flow in the Telegram handler layer.

        Args:
            payload: Input value supplied by the caller; accepted shape follows the function signature and local validation.
            mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.
            markup: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

        Side effects:
            May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

        Flow constraints:
            Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
        """
        return await query.message.edit_text(
            payload,
            parse_mode=mode,
            reply_markup=markup,
            **kwargs,
        )

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Await  edit before continuing.
        await _edit(first, parse_mode, reply_markup)
    # Handle an expected failure from the guarded operation above.
    except BadRequest as exc:
        err = str(exc).lower()
        if "message is not modified" in err:
            # Keep this intentionally empty block valid.
            pass
        elif "message_too_long" in err or "message is too long" in err or len(first) > 4096:
            safe_first = first[:3500].rstrip() + "\n\n📄 Pesan terlalu panjang, detail lanjutan dikirim di bawah."
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Await  edit before continuing.
                await _edit(safe_first, None, reply_markup)
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Send the Telegram response before continuing.
                await query.message.reply_text(safe_first, reply_markup=reply_markup)
        # Use the fallback path when no earlier branch matched.
        else:
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Await  edit before continuing.
                await _edit(first, None, reply_markup)
            # Handle an expected failure from the guarded operation above.
            except BadRequest:
                # Send the Telegram response before continuing.
                await query.message.reply_text(first, reply_markup=reply_markup)

    # Iterate through each chunk.
    for chunk in chunks[1:]:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Send the Telegram response before continuing.
            await query.message.reply_text(chunk, parse_mode=parse_mode)
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Send the Telegram response before continuing.
            await query.message.reply_text(chunk)


async def show_callback_loading(query, text: str = "⏳ *Memproses pilihan...*"):
    """Handle callback-related behavior in the Telegram bot flow."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        await safe_edit_message(query, text, parse_mode="Markdown")
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Loading feedback must never break the main action.
        pass


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous error handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    error = getattr(context, "error", None)
    err_text = str(error or "Unknown error")

    if isinstance(error, BadRequest) and ("Message_too_long" in err_text or "Message is too long" in err_text):
        user_msg = (
            "❌ *Terjadi error saat menampilkan pesan.*\n\n"
            "Output terlalu panjang untuk Telegram. Saya sudah menahan crash-nya, "
            "coba ulangi atau kirim input dalam beberapa batch yang lebih kecil."
        )
    # Use the fallback path when no earlier branch matched.
    else:
        user_msg = (
            "❌ *Terjadi error saat memproses tombol/input.*\n\n"
            f"Detail: `{md_safe(err_text[:250])}`\n\n"
            "Coba ulangi dari step terakhir. Kalau masih muncul, kirim log ini untuk dicek."
        )

    # Run this operation in a guarded block so failures can be handled.
    try:
        effective_message = getattr(update, "effective_message", None)
        callback_query = getattr(update, "callback_query", None)

        if effective_message:
            await effective_message.reply_text(user_msg, parse_mode="Markdown")
        # Fall back when callback query and callback query.
        elif callback_query and callback_query.message:
            await callback_query.message.reply_text(user_msg, parse_mode="Markdown")
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass

    # Keep this section separated from the surrounding flow.
    print(f"[ERROR_HANDLER] {type(error).__name__ if error else 'Unknown'}: {err_text}")



