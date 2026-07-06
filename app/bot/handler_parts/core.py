"""Core Telegram helpers for authorization, safe replies, message splitting, and error handling."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *

# ── Helper ────────────────────────────────────────────────────────────────────

# Prepare TELEGRAM SAFE MESSAGE LIMIT for the next step.
TELEGRAM_SAFE_MESSAGE_LIMIT = 3800


# Define split long message for callers in this flow.
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
    # Handle the missing or empty text case.
    if not text:
        return [""]
    # Handle the case where len(text) <= max_len.
    if len(text) <= max_len:
        # Return [text] to the caller.
        return [text]

    # Prepare chunks for the next step.
    chunks = []
    current = ""

    for block in text.split("\n\n"):
        # Prepare block for the next step.
        block = block.strip()
        # Handle the missing or empty block case.
        if not block:
            # Skip the rest of this loop iteration after handling this case.
            continue

        candidate = f"{current}\n\n{block}".strip() if current else block
        # Handle the case where len(candidate) <= max_len.
        if len(candidate) <= max_len:
            # Prepare current for the next step.
            current = candidate
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Handle the case where current.
        if current:
            # Update chunks with the current value.
            chunks.append(current)
            current = ""

        # Handle the case where len(block) <= max_len.
        if len(block) <= max_len:
            # Prepare current for the next step.
            current = block
            # Skip the rest of this loop iteration after handling this case.
            continue

        line_current = ""
        # Process each line in the current collection.
        for line in block.splitlines():
            candidate_line = f"{line_current}\n{line}".strip() if line_current else line
            # Handle the case where len(candidate_line) <= max_len.
            if len(candidate_line) <= max_len:
                # Prepare line current for the next step.
                line_current = candidate_line
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Handle the case where line_current.
                if line_current:
                    # Update chunks with the current value.
                    chunks.append(line_current)
                # Handle the case where len(line) > max_len.
                if len(line) > max_len:
                    # Process each i in the current collection.
                    for i in range(0, len(line), max_len):
                        # Update chunks with the current value.
                        chunks.append(line[i:i + max_len])
                    line_current = ""
                # Handle the fallback path after earlier conditions are skipped.
                else:
                    # Prepare line current for the next step.
                    line_current = line

        # Handle the case where line_current.
        if line_current:
            # Update chunks with the current value.
            chunks.append(line_current)

    # Handle the case where current.
    if current:
        # Update chunks with the current value.
        chunks.append(current)

    # Return chunks to the caller.
    return chunks


# Handle the asynchronous reply long markdown workflow.
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
    # Process each part in the current collection.
    for part in split_long_message(text):
        # Run this operation in a guarded block so failures can be handled.
        try:
            await update.message.reply_text(part, parse_mode="Markdown")
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(part)


# Handle the asynchronous reply message safely workflow.
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
    # Prepare chunks for the next step.
    chunks = split_long_message(text)
    # Process each idx, chunk in the current collection.
    for idx, chunk in enumerate(chunks):
        # Prepare markup for the next step.
        markup = reply_markup if idx == len(chunks) - 1 else None
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Wait for message.reply_text before continuing this flow.
            await message.reply_text(chunk, parse_mode=parse_mode, reply_markup=markup, **kwargs)
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Wait for message.reply_text before continuing this flow.
            await message.reply_text(chunk, reply_markup=markup, **kwargs)


# Handle the asynchronous reply update safely workflow.
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
    # Handle the case where update.message.
    if update.message:
        # Wait for reply_message_safely before continuing this flow.
        await reply_message_safely(update.message, text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)


# Handle the asynchronous safe edit message workflow.
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
    # Handle the missing or empty text case.
    if not text:
        text = " "

    # Prepare chunks for the next step.
    chunks = split_long_message(text)
    # Prepare first for the next step.
    first = chunks[0]

    # Handle the case where len(chunks) > 1.
    if len(chunks) > 1:
        suffix = "\n\n📄 *Pesan terlalu panjang, detail lanjutan dikirim di bawah.*"
        # Prepare max first len for the next step.
        max_first_len = TELEGRAM_SAFE_MESSAGE_LIMIT - len(suffix) - 10
        # Prepare first for the next step.
        first = first[:max_first_len].rstrip() + suffix

    # Handle the asynchronous edit workflow.
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
        # Return await query.message.edit_text( to the caller.
        return await query.message.edit_text(
            # Include this value in the surrounding collection or call.
            payload,
            # Prepare parse mode for the next step.
            parse_mode=mode,
            # Prepare reply markup for the next step.
            reply_markup=markup,
            # Include this value in the surrounding collection or call.
            **kwargs,
        # Close the structure that was opened above.
        )

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Wait for _edit before continuing this flow.
        await _edit(first, parse_mode, reply_markup)
    # Handle an expected failure from the guarded operation above.
    except BadRequest as exc:
        # Prepare err for the next step.
        err = str(exc).lower()
        if "message is not modified" in err:
            # Keep this intentionally empty block valid.
            pass
        elif "message_too_long" in err or "message is too long" in err or len(first) > 4096:
            safe_first = first[:3500].rstrip() + "\n\n📄 Pesan terlalu panjang, detail lanjutan dikirim di bawah."
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Wait for _edit before continuing this flow.
                await _edit(safe_first, None, reply_markup)
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Wait for query.message.reply_text before continuing this flow.
                await query.message.reply_text(safe_first, reply_markup=reply_markup)
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Wait for _edit before continuing this flow.
                await _edit(first, None, reply_markup)
            # Handle an expected failure from the guarded operation above.
            except BadRequest:
                # Wait for query.message.reply_text before continuing this flow.
                await query.message.reply_text(first, reply_markup=reply_markup)

    # Process each chunk in the current collection.
    for chunk in chunks[1:]:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Wait for query.message.reply_text before continuing this flow.
            await query.message.reply_text(chunk, parse_mode=parse_mode)
        # Handle an expected failure from the guarded operation above.
        except BadRequest:
            # Wait for query.message.reply_text before continuing this flow.
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


# Handle the asynchronous error handler workflow.
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
        # Open a multi-line structure for the values below.
        user_msg = (
            "❌ *Terjadi error saat menampilkan pesan.*\n\n"
            "Output terlalu panjang untuk Telegram. Saya sudah menahan crash-nya, "
            "coba ulangi atau kirim input dalam beberapa batch yang lebih kecil."
        # Close the structure that was opened above.
        )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Open a multi-line structure for the values below.
        user_msg = (
            "❌ *Terjadi error saat memproses tombol/input.*\n\n"
            f"Detail: `{md_safe(err_text[:250])}`\n\n"
            "Coba ulangi dari step terakhir. Kalau masih muncul, kirim log ini untuk dicek."
        # Close the structure that was opened above.
        )

    # Run this operation in a guarded block so failures can be handled.
    try:
        effective_message = getattr(update, "effective_message", None)
        callback_query = getattr(update, "callback_query", None)

        # Handle the case where effective_message.
        if effective_message:
            await effective_message.reply_text(user_msg, parse_mode="Markdown")
        # Handle the alternate case where callback_query and callback_query.message.
        elif callback_query and callback_query.message:
            await callback_query.message.reply_text(user_msg, parse_mode="Markdown")
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass

    # Keep this section separated from the surrounding flow.
    print(f"[ERROR_HANDLER] {type(error).__name__ if error else 'Unknown'}: {err_text}")



