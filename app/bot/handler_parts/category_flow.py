"""Telegram wizard for adding and editing category metadata.

This module owns the user-facing flow for `/add_kategori` and
`/edit_kategori`. It only stores temporary wizard state in
`context.user_data` until the user presses the final `Simpan` button. The
actual Google Sheets write happens in `handle_category_confirm_callback`.
"""

# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import app.bot.handler_parts.common_imports so this module can use its helpers.
from app.bot.handler_parts.common_imports import *
# Import app.bot.handler_parts.state_utils so this module can use its helpers.
from app.bot.handler_parts.state_utils import BULK_EDIT_CATEGORY_DECISION_KEY, clear_pending_flow_state
# Import app.nlp.gemini_category_aliases so this module can use its helpers.
from app.nlp.gemini_category_aliases import generate_category_alias_candidates
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import (
    # Include this value in the surrounding collection or call.
    create_category,
    # Include this value in the surrounding collection or call.
    find_category_by_name,
    # Include this value in the surrounding collection or call.
    get_category_records_safe,
    # Include this value in the surrounding collection or call.
    normalize_category_aliases,
    # Include this value in the surrounding collection or call.
    update_category,
# Close the structure that was opened above.
)


# Context key for the active `/add_kategori` wizard.
CATEGORY_ADD_FLOW_KEY = "pending_category_add_flow"
# Context key for the active `/edit_kategori` wizard.
CATEGORY_EDIT_FLOW_KEY = "pending_category_edit_flow"
# Context key for removing the previous category inline keyboard.
CATEGORY_PROMPT_MESSAGE_KEY = "pending_category_prompt_message_id"


# Define clean category name for callers in this flow.
def _clean_category_name(value: str) -> str:
    """Clean a Telegram text value into a category name.

    Args:
        value: Raw category text from command args or a message reply. Expected
            examples are `Belanja Online`, `Freelance`, or quoted names such as
            `"Food & Beverage"`.

    Returns:
        A stripped category name without surrounding single or double quotes.
        Empty or `None` input returns an empty string.
    """
    # Normalize optional quoting from command args or manual text replies.
    return str(value or "").strip().strip('"').strip("'").strip()


# Define category flow keyboard for callers in this flow.
def _category_flow_keyboard(mode: str) -> InlineKeyboardMarkup:
    """Build the category type keyboard requested by the user.

    Args:
        mode: Flow mode used in callback data. Must be `add` or `edit`.

    Returns:
        An inline keyboard with one row and two columns for `Expense` and
        `Income`, plus one cancel row. The callback format for type buttons is
        `category_type:{mode}:{type}`.
    """
    # Keep the requested layout: one row, two columns.
    return InlineKeyboardMarkup([
        # Open a multi-line structure for the values below.
        [
            InlineKeyboardButton("Expense", callback_data=f"category_type:{mode}:expense"),
            InlineKeyboardButton("Income", callback_data=f"category_type:{mode}:income"),
        # Close the structure that was opened above.
        ],
        [InlineKeyboardButton("❌ Batal", callback_data=f"cancel:category_{mode}")],
    # Close the structure that was opened above.
    ])


# Define get category flow for callers in this flow.
def _get_category_flow(context: ContextTypes.DEFAULT_TYPE) -> tuple[str | None, str | None, dict | None]:
    """Read the active add/edit category wizard from Telegram user state.

    Args:
        context: Telegram context containing `user_data`.

    Returns:
        A tuple of `(mode, state_key, state)`. `mode` is `add` or `edit`,
        `state_key` is the matching `context.user_data` key, and `state` is the
        mutable wizard payload. If no category wizard is active, all values are
        `None`.
    """
    # Add flow takes priority because only one category wizard should be active.
    add_state = context.user_data.get(CATEGORY_ADD_FLOW_KEY)
    # Handle the case where add_state.
    if add_state:
        return "add", CATEGORY_ADD_FLOW_KEY, add_state

    # Edit flow is checked after add flow for the same single-wizard rule.
    edit_state = context.user_data.get(CATEGORY_EDIT_FLOW_KEY)
    # Handle the case where edit_state.
    if edit_state:
        return "edit", CATEGORY_EDIT_FLOW_KEY, edit_state

    # No category wizard is active, so normal message parsing can continue.
    return None, None, None


# Define format category rows for help for callers in this flow.
def _format_category_rows_for_help(limit: int = 18) -> str:
    """Format existing categories for the `/edit_kategori` name prompt.

    Args:
        limit: Maximum number of category rows to show. The value should stay
            small enough for Telegram messages.

    Returns:
        Markdown text containing category symbol, category name, and type. If no
        category is available, returns a short empty-state sentence.
    """
    # Prepare rows for the next step.
    rows = []
    # Read only a limited number of rows so the prompt stays short.
    for record in get_category_records_safe()[:limit]:
        # Sheet records use the existing category_name/type/emoji schema.
        name = str((record or {}).get("category_name") or "").strip()
        txn_type = str((record or {}).get("type") or "-").strip()
        emoji = str((record or {}).get("emoji") or "").strip()
        # Blank category names are skipped because they cannot be edited safely.
        if name:
            rows.append(f"- {emoji} `{md_code_text(name)}` ({md_safe(txn_type)})")
    # Show an empty-state message if the sheet has no readable category names.
    return "\n".join(rows) if rows else "Belum ada kategori di sheet `categories`."


# Define format alias preview for callers in this flow.
def _format_alias_preview(aliases: str, *, max_items: int = 8, max_len: int = 120) -> str:
    """Format aliases into a short readable list for `/kategori`.

    Args:
        aliases: Raw comma-separated value from the `categories.aliases` column.
        max_items: Maximum alias count shown for one category row.
        max_len: Maximum displayed character length after joining aliases.

    Returns:
        A comma-separated alias preview or `-` when aliases are empty.
    """
    # Split the existing sheet format without changing the stored value.
    items = [part.strip() for part in str(aliases or "").split(",") if part.strip()]
    # Handle the missing or empty items case.
    if not items:
        return "-"
    preview = ", ".join(items[:max_items])
    # Handle the case where len(items) > max_items.
    if len(items) > max_items:
        preview += ", ..."
    # Handle the case where len(preview) > max_len.
    if len(preview) > max_len:
        preview = preview[: max_len - 3].rstrip(", ") + "..."
    # Return preview to the caller.
    return preview


# Define build category list text for callers in this flow.
def _build_category_list_text(records: list[dict]) -> str:
    """Build the `/kategori` category listing message.

    Args:
        records: Category records from `get_category_records_safe()`. Expected
            keys are `category_name`, `type`, `emoji`, and `aliases`.

    Returns:
        Markdown text grouped by expense and income. Each row shows symbol,
        category name, and a short aliases preview.
    """
    grouped = {"expense": [], "income": [], "other": []}
    # Process each record in the current collection.
    for record in records or []:
        # Ignore blank names because they cannot be selected or edited safely.
        name = str((record or {}).get("category_name") or "").strip()
        # Handle the missing or empty name case.
        if not name:
            # Skip the rest of this loop iteration after handling this case.
            continue
        txn_type = str((record or {}).get("type") or "other").strip().lower()
        group_key = txn_type if txn_type in {"expense", "income"} else "other"
        # Run this statement as part of the current workflow.
        grouped[group_key].append(record)

    # Handle the missing or empty any(grouped.values()) case.
    if not any(grouped.values()):
        return "ðŸ“ *Daftar Kategori*\n\nBelum ada kategori yang bisa dibaca dari sheet `categories`."

    # Open a multi-line structure for the values below.
    lines = [
        "ðŸ“ *Daftar Kategori*",
        "Basis: sheet `categories`. Aliases ditampilkan ringkas untuk bantu cek mapping.",
    # Close the structure that was opened above.
    ]
    for group_key, title in [("expense", "Expense"), ("income", "Income"), ("other", "Lainnya")]:
        # Prepare rows for the next step.
        rows = grouped.get(group_key) or []
        # Handle the missing or empty rows case.
        if not rows:
            # Skip the rest of this loop iteration after handling this case.
            continue
        lines.append(f"\n*{title}*")
        for record in sorted(rows, key=lambda item: str(item.get("category_name") or "").lower()):
            name = str(record.get("category_name") or "").strip()
            symbol = str(record.get("emoji") or "-").strip() or "-"
            aliases = _format_alias_preview(str(record.get("aliases") or ""))
            lines.append(f"- {md_safe(symbol)} *{md_safe(name)}*")
            lines.append(f"  Aliases: `{md_code_text(aliases)}`")
    return "\n".join(lines)


def _build_type_prompt(category_name: str, *, current_type: str = "") -> str:
    """Build the message that asks whether a category is expense or income.

    Args:
        category_name: Clean category name being added or edited.
        current_type: Existing sheet value for edit mode. Use an empty string
            for add mode.

    Returns:
        Markdown text for Telegram. The actual choice is collected through the
        `_category_flow_keyboard` inline buttons.
    """
    # Edit mode shows the current type so the user can compare before changing.
    current_note = f"\nTipe sekarang: *{md_safe(current_type)}*" if current_type else ""
    # The answer is collected by inline button, not free text.
    return (
        f"Kategori: *{md_safe(category_name)}*{current_note}\n\n"
        "Tipe kategori ini apa?\n"
        "Pilih salah satu tombol di bawah."
    # Close the structure that was opened above.
    )


# Define build symbol prompt for callers in this flow.
def _build_symbol_prompt(state: dict, *, edit_mode: bool = False) -> str:
    """Build the text prompt that asks the user for a category symbol.

    Args:
        state: Category wizard state. Expected keys are `category_name`, `type`,
            and optionally `current` for edit mode.
        edit_mode: Whether the prompt is used by `/edit_kategori`. In edit mode,
            the user may type `sama`, `tetap`, `skip`, `lewati`, or `-` to keep
            the existing symbol.

    Returns:
        Markdown text for Telegram. The answer is expected to be a short text
        value, usually an emoji or short label, and will be stored in the sheet
        column named `emoji`.
    """
    # Category name and current symbol are pulled from wizard state.
    name = str(state.get("category_name") or "").strip()
    current = str((state.get("current") or {}).get("emoji") or "").strip()
    # Edit mode allows preserving the old symbol without retyping it.
    keep_note = "\nKetik `sama` kalau mau mempertahankan symbol sekarang." if edit_mode and current else ""
    current_note = f"\nSymbol sekarang: {md_safe(current)}" if edit_mode and current else ""
    # The reply is expected as text, because Telegram symbols can be emoji or labels.
    return (
        f"Kategori: *{md_safe(name)}*\n"
        f"Tipe: *{md_safe(state.get('type') or '-')}*{current_note}\n\n"
        f"Symbolnya apa?{keep_note}"
    # Close the structure that was opened above.
    )


# Define build alias prompt for callers in this flow.
def _build_alias_prompt(state: dict) -> str:
    """Build the text prompt that asks for edited aliases.

    Args:
        state: Edit wizard state. Expected keys are `category_name`, `type`,
            `emoji`, and `current.aliases`.

    Returns:
        Markdown text explaining the accepted alias inputs:
        comma-separated aliases for manual edit, `auto` for Gemini
        regeneration, or `sama` to keep the existing aliases unchanged.
    """
    # Existing aliases are displayed so the user can decide keep/manual/auto.
    current_aliases = str((state.get("current") or {}).get("aliases") or "").strip()
    current_text = f"\n\nAliases sekarang:\n`{md_code_text(current_aliases or '-')}`"
    # Edit mode accepts manual aliases, Gemini regeneration, or keep-current input.
    return (
        f"Kategori: *{md_safe(state.get('category_name') or '-')}*\n"
        f"Tipe: *{md_safe(state.get('type') or '-')}*\n"
        f"Symbol: {md_safe(state.get('emoji') or '-')}"
        f"{current_text}\n\n"
        "Aliases barunya apa?\n"
        "Ketik daftar dipisah koma, ketik `auto` untuk generate ulang via Gemini, atau ketik `sama` untuk mempertahankan."
    # Close the structure that was opened above.
    )


# Define generate aliases for callers in this flow.
def _generate_aliases(category_name: str, transaction_type: str) -> tuple[str, str]:
    """Generate normalized aliases for a category.

    Args:
        category_name: Clean category name, for example `Belanja Online`.
        transaction_type: Category type. Only `income` is treated as income;
            every other value falls back to expense semantics.

    Returns:
        A tuple `(aliases, source)`. `aliases` is a comma-separated string ready
        for the `categories.aliases` sheet column. `source` is `Gemini` when the
        model succeeds, otherwise `fallback`.

    Notes:
        Gemini output is never written directly. It is normalized by
        `normalize_category_aliases` so the final format stays compatible with
        the existing resolver.
    """
    # Gemini is attempted first because the user asked for auto-generated aliases.
    try:
        # Prepare candidates for the next step.
        candidates = generate_category_alias_candidates(category_name, transaction_type)
        # Prepare aliases for the next step.
        aliases = normalize_category_aliases(candidates, category_name)
        # Only non-empty normalized aliases are accepted from Gemini.
        if aliases:
            return aliases, "Gemini"
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Gemini errors should not break the category wizard.
        pass

    # Fallback keeps at least the category name as an alias candidate.
    return normalize_category_aliases([], category_name), "fallback"


# Define format aliases for message for callers in this flow.
def _format_aliases_for_message(aliases: str, *, max_len: int = 900) -> str:
    """Trim alias text so Telegram preview messages stay readable.

    Args:
        aliases: Comma-separated aliases from manual input, Gemini, or the
            current sheet row.
        max_len: Maximum displayed characters before truncation.

    Returns:
        Alias text as-is when short enough, or a shortened version ending with
        `...`. Empty input returns `-`.
    """
    # Empty aliases are displayed as a dash in Telegram output.
    text = str(aliases or "-").strip() or "-"
    # Short alias strings can be shown without truncation.
    if len(text) <= max_len:
        # Return text to the caller.
        return text
    # Long alias strings are trimmed so preview messages remain readable.
    return text[: max_len - 3].rstrip(", ") + "..."


# Define category confirm target for callers in this flow.
def _category_confirm_target(mode: str) -> str:
    """Map a category flow mode to the final confirmation callback target.

    Args:
        mode: `add` for `/add_kategori`; `edit` for `/edit_kategori`.

    Returns:
        `category_add` or `category_edit`, matching `confirm:{target}` callback
        data handled by `callback_handler`.
    """
    # The callback target distinguishes append flow from update flow.
    return "category_edit" if mode == "edit" else "category_add"


# Define build category preview text for callers in this flow.
def _build_category_preview_text(state: dict, *, mode: str) -> str:
    """Build the final preview shown before any category write.

    Args:
        state: Wizard state containing `category_name`, `type`, `emoji`,
            `aliases`, and `alias_source`. Edit mode also expects `current`
            with the old sheet row.
        mode: `add` or `edit`.

    Returns:
        Markdown preview text. Add mode shows the new row that will be appended.
        Edit mode shows a before/after comparison for type, symbol, and aliases.

    Notes:
        This function does not write to Google Sheets. It exists to keep the
        AGENTS.md preview-before-save rule explicit.
    """
    # Read final values from the pending wizard state.
    name = str(state.get("category_name") or "-").strip()
    txn_type = str(state.get("type") or "-").strip()
    symbol = str(state.get("emoji") or "-").strip()
    aliases = _format_aliases_for_message(str(state.get("aliases") or "").strip())
    alias_source = str(state.get("alias_source") or "-").strip()

    # Edit preview shows before/after values for review.
    if mode == "edit":
        current = state.get("current") or {}
        current_type = str(current.get("type") or "-").strip()
        current_symbol = str(current.get("emoji") or "-").strip()
        current_aliases = _format_aliases_for_message(str(current.get("aliases") or "").strip())
        # Return ( to the caller.
        return (
            "*Preview Edit Kategori*\n\n"
            f"Kategori: *{md_safe(name)}*\n\n"
            "*Sebelum:*\n"
            f"- Tipe: *{md_safe(current_type)}*\n"
            f"- Symbol: {md_safe(current_symbol)}\n"
            f"- Aliases:\n`{md_code_text(current_aliases)}`\n\n"
            "*Sesudah:*\n"
            f"- Tipe: *{md_safe(txn_type)}*\n"
            f"- Symbol: {md_safe(symbol)}\n"
            f"- Aliases ({md_safe(alias_source)}):\n`{md_code_text(aliases)}`\n\n"
            "Klik *Simpan* kalau sudah benar, atau *Batal* kalau mau membatalkan."
        # Close the structure that was opened above.
        )

    # Add preview shows the exact row data before append.
    return (
        "*Preview Tambah Kategori*\n\n"
        "Kategori baru belum disimpan ke sheet `categories`.\n\n"
        f"- Kategori: *{md_safe(name)}*\n"
        f"- Tipe: *{md_safe(txn_type)}*\n"
        f"- Symbol: {md_safe(symbol)}\n"
        f"- Aliases ({md_safe(alias_source)}):\n`{md_code_text(aliases)}`\n\n"
        "Klik *Simpan* kalau sudah benar, atau *Batal* kalau mau membatalkan."
    # Close the structure that was opened above.
    )


# Handle the asynchronous show category preview workflow.
async def _show_category_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, state: dict, *, mode: str) -> None:
    """Store pending category data and send the final confirmation preview.

    Args:
        update: Telegram update whose message receives the preview.
        context: Telegram context used to keep the pending wizard state.
        state: Complete category payload prepared by the wizard.
        mode: `add` or `edit`, used to select the pending state key and
            confirmation target.

    Returns:
        None. The function updates `context.user_data` and sends a Telegram
        message with a `Simpan` / `Batal` keyboard.
    """
    key = CATEGORY_EDIT_FLOW_KEY if mode == "edit" else CATEGORY_ADD_FLOW_KEY
    # This is the last non-writing state before the user confirms the save.
    state["stage"] = "confirm"
    # Run this statement as part of the current workflow.
    context.user_data[key] = state

    # The confirm keyboard is the only path to the final category write.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        _build_category_preview_text(state, mode=mode),
        parse_mode="Markdown",
        # Prepare reply markup for the next step.
        reply_markup=confirm_keyboard(_category_confirm_target(mode)),
    # Close the structure that was opened above.
    )


# Handle the asynchronous add kategori handler workflow.
async def add_kategori_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start `/add_kategori` and collect the category name.

    Args:
        update: Telegram command update. The command may be sent as
            `/add_kategori` or `/add_kategori Nama Kategori`.
        context: Telegram context. `context.args` may contain the category name.

    Returns:
        None. The function either asks for the category name or, when the name
        is already provided in the command, asks for type through inline buttons.

    Flow:
        1. Clear stale pending flows.
        2. Store `pending_category_add_flow`.
        3. Ask `Kategorinya apa?` or move directly to the type step.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # A new explicit command starts from a clean transient state.
    clear_pending_flow_state(context)
    # Command args can prefill the category name.
    raw_name = _clean_category_name(" ".join(context.args or []))
    # Add flow starts at name stage unless args already provide the name.
    state = {"stage": "name", "mode": "add"}
    # Run this statement as part of the current workflow.
    context.user_data[CATEGORY_ADD_FLOW_KEY] = state

    # If the name is already present, skip directly to type selection.
    if raw_name:
        state["category_name"] = raw_name
        state["stage"] = "type"
        # Wait for reply_tracked_inline_keyboard before continuing this flow.
        await reply_tracked_inline_keyboard(
            # Include this value in the surrounding collection or call.
            update,
            # Include this value in the surrounding collection or call.
            context,
            # Include this value in the surrounding collection or call.
            _build_type_prompt(raw_name),
            parse_mode="Markdown",
            reply_markup=_category_flow_keyboard("add"),
            # Prepare state key for the next step.
            state_key=CATEGORY_PROMPT_MESSAGE_KEY,
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Without args, ask the user for the category name first.
    await update.message.reply_text(
        "Kategorinya apa?\n\n"
        "Contoh: `Belanja Online`, `Freelance`, `Kucing`, `Investasi`.",
        parse_mode="Markdown",
        # Prepare reply markup for the next step.
        reply_markup=cancel_keyboard(),
    # Close the structure that was opened above.
    )


# Handle the asynchronous kategori handler workflow.
async def kategori_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the current category list from the categories sheet.

    Args:
        update: Telegram command update for `/kategori`.
        context: Telegram context. This handler does not require command args
            and does not mutate `context.user_data`.

    Returns:
        None. The function sends a grouped Markdown list of existing categories,
        including symbol and a short aliases preview.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # This is read-only; it never writes to Google Sheets.
    records = get_category_records_safe()
    # Wait for reply_message_safely before continuing this flow.
    await reply_message_safely(
        # Include this value in the surrounding collection or call.
        update.message,
        # Include this value in the surrounding collection or call.
        _build_category_list_text(records),
        parse_mode="Markdown",
        # Prepare reply markup for the next step.
        reply_markup=cancel_keyboard(),
    # Close the structure that was opened above.
    )


# Handle the asynchronous edit kategori handler workflow.
async def edit_kategori_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start `/edit_kategori` and collect the target category name.

    Args:
        update: Telegram command update. The command may be sent as
            `/edit_kategori` or `/edit_kategori Nama Kategori`.
        context: Telegram context. `context.args` may contain the target
            category name.

    Returns:
        None. The function asks for the category name or validates the provided
        name before continuing to the type step.

    Flow:
        1. Clear stale pending flows.
        2. Store `pending_category_edit_flow`.
        3. Ask which category to edit, showing a small category list as help.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # A new edit command should not inherit an unfinished add/edit wizard.
    clear_pending_flow_state(context)
    # Command args can prefill the target category name.
    raw_name = _clean_category_name(" ".join(context.args or []))
    # Edit flow starts by resolving the target category row.
    state = {"stage": "name", "mode": "edit"}
    # Run this statement as part of the current workflow.
    context.user_data[CATEGORY_EDIT_FLOW_KEY] = state

    # If the target name is provided, validate it immediately.
    if raw_name:
        await _accept_category_name(update, context, state, raw_name, mode="edit")
        # Return control to the caller.
        return

    # Without args, show category examples from the sheet to guide the user.
    await update.message.reply_text(
        "Kategori mana yang mau diedit?\n\n"
        "Ketik nama kategori persis seperti di sheet `categories`.\n\n"
        # Include this value in the surrounding collection or call.
        f"{_format_category_rows_for_help()}",
        parse_mode="Markdown",
        # Prepare reply markup for the next step.
        reply_markup=cancel_keyboard(),
    # Close the structure that was opened above.
    )


# Handle the asynchronous accept category name workflow.
async def _accept_category_name(
    # Include this value in the surrounding collection or call.
    update: Update,
    # Include this value in the surrounding collection or call.
    context: ContextTypes.DEFAULT_TYPE,
    # Include this value in the surrounding collection or call.
    state: dict,
    # Include this value in the surrounding collection or call.
    category_name: str,
    # Include this value in the surrounding collection or call.
    *,
    # Include this value in the surrounding collection or call.
    mode: str,
# Close the structure that was opened above.
) -> None:
    """Validate and store a category name before asking for category type.

    Args:
        update: Telegram update used to reply with validation errors or the
            next prompt.
        context: Telegram context that stores the wizard state.
        state: Mutable wizard payload for add or edit mode.
        category_name: Raw category name from command args or message text.
        mode: `add` to accept a new name, or `edit` to require an existing
            category row.

    Returns:
        None. On success, the function stores `category_name`, sets stage to
        `type`, and sends the expense/income keyboard. On edit validation
        failure, it keeps the wizard active and asks for another name.
    """
    # Prepare clean name for the next step.
    clean_name = _clean_category_name(category_name)
    # Empty names cannot be added or resolved for editing.
    if not clean_name:
        await update.message.reply_text("Nama kategori belum kebaca. Coba ketik lagi.", reply_markup=cancel_keyboard())
        # Return control to the caller.
        return

    if mode == "edit":
        # Edit mode must target a real row so the final update is deterministic.
        found = find_category_by_name(clean_name)
        # Missing categories keep the wizard open so the user can retry.
        if not found.get("found"):
            suggestions = found.get("suggestions") or []
            suggestion_text = ""
            # Suggestions are displayed as hints, never auto-applied.
            if suggestions:
                suggestion_text = "\n\nMungkin maksudnya:\n" + "\n".join(f"- `{md_code_text(item)}`" for item in suggestions)
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"Kategori `{md_code_text(clean_name)}` tidak ditemukan di sheet `categories`."
                f"{suggestion_text}\n\n"
                "Ketik nama kategori lain, atau tekan *Batal* untuk membatalkan.",
                parse_mode="Markdown",
                # Prepare reply markup for the next step.
                reply_markup=cancel_keyboard(),
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        # Use the canonical sheet name after a successful lookup.
        record = found.get("record") or {}
        clean_name = str(record.get("category_name") or clean_name).strip()
        state["current"] = record
        current_type = str(record.get("type") or "").strip().lower()
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Add mode has no current type because the row does not exist yet.
        current_type = ""

    state["category_name"] = clean_name
    state["stage"] = "type"
    target_key = CATEGORY_EDIT_FLOW_KEY if mode == "edit" else CATEGORY_ADD_FLOW_KEY
    # Run this statement as part of the current workflow.
    context.user_data[target_key] = state

    # The next step must use the requested expense/income button layout.
    await reply_tracked_inline_keyboard(
        # Include this value in the surrounding collection or call.
        update,
        # Include this value in the surrounding collection or call.
        context,
        # Include this value in the surrounding collection or call.
        _build_type_prompt(clean_name, current_type=current_type),
        parse_mode="Markdown",
        # Prepare reply markup for the next step.
        reply_markup=_category_flow_keyboard(mode),
        # Prepare state key for the next step.
        state_key=CATEGORY_PROMPT_MESSAGE_KEY,
    # Close the structure that was opened above.
    )


# Handle the asynchronous handle category type callback workflow.
async def handle_category_type_callback(query, context: ContextTypes.DEFAULT_TYPE, data: str) -> bool:
    """Handle the expense/income inline button for category flows.

    Args:
        query: Telegram callback query from the type keyboard.
        context: Telegram context containing the pending category state.
        data: Callback data. Expected format is
            `category_type:{mode}:{txn_type}`, where `mode` is `add` or `edit`
            and `txn_type` is `expense` or `income`.

    Returns:
        `True` when the callback belongs to this category flow and has been
        handled, including validation errors. `False` when the callback data is
        unrelated.
    """
    if not str(data or "").startswith("category_type:"):
        # Return False to the caller.
        return False

    # Callback data is the routing contract; invalid shapes stop here.
    parts = str(data or "").split(":")
    # Handle the case where len(parts) != 3.
    if len(parts) != 3:
        await safe_edit_message(query, "Pilihan tipe kategori tidak valid.")
        # Return True to the caller.
        return True

    # Extract mode and selected transaction type from callback data.
    _, mode, txn_type = parts
    # Only category add/edit modes are valid for this callback.
    if mode not in {"add", "edit"}:
        await safe_edit_message(query, "Mode kategori tidak valid.")
        # Return True to the caller.
        return True

    # Select the pending state bucket that matches the callback mode.
    key = CATEGORY_ADD_FLOW_KEY if mode == "add" else CATEGORY_EDIT_FLOW_KEY
    # Prepare state for the next step.
    state = context.user_data.get(key) or {}
    # Expired callbacks should not write or advance any flow.
    if not state:
        await safe_edit_message(query, f"Sesi kategori expired. Jalankan `/{mode}_kategori` lagi.", parse_mode="Markdown")
        # Return True to the caller.
        return True

    # The user requested only expense/income choices for category type.
    if txn_type not in {"expense", "income"}:
        await safe_edit_message(query, "Tipe kategori harus `expense` atau `income`.", parse_mode="Markdown")
        # Return True to the caller.
        return True

    state["type"] = txn_type
    state["stage"] = "symbol"
    # Run this statement as part of the current workflow.
    context.user_data[key] = state

    # Symbol is collected as text after the type button.
    await safe_edit_message(
        # Include this value in the surrounding collection or call.
        query,
        _build_symbol_prompt(state, edit_mode=(mode == "edit")),
        parse_mode="Markdown",
        # Prepare reply markup for the next step.
        reply_markup=cancel_keyboard(),
    # Close the structure that was opened above.
    )
    # Return True to the caller.
    return True


# Handle the asynchronous handle pending category flow workflow.
async def handle_pending_category_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Continue a pending add/edit category wizard from normal text messages.

    Args:
        update: Telegram message update containing the user's text reply.
        context: Telegram context with `pending_category_add_flow` or
            `pending_category_edit_flow`.
        user_text: Raw text from the user. Expected content depends on stage:
            category name for `name`, short symbol for `symbol`, and manual
            aliases / `auto` / `sama` for `aliases`.

    Returns:
        `True` when a category wizard is active and this message was consumed.
        `False` when no category wizard is active, so the normal transaction
        parser can continue.
    """
    # Run this statement as part of the current workflow.
    mode, key, state = _get_category_flow(context)
    # No category state means this text belongs to normal bot handling.
    if not state:
        # Return False to the caller.
        return False

    stage = str(state.get("stage") or "name").strip().lower()
    # Stage 1: category name, either from command args or the next message.
    if stage == "name":
        # Wait for _accept_category_name before continuing this flow.
        await _accept_category_name(update, context, state, user_text, mode=mode)
        # Return True to the caller.
        return True

    # Stage 3 in the requested flow: user chooses the symbol manually.
    if stage == "symbol":
        # Symbol can be an emoji or a short text label.
        clean_symbol = str(user_text or "").strip()
        # Edit flow supports keeping the current symbol by keyword.
        if mode == "edit" and clean_symbol.lower() in {"sama", "tetap", "skip", "lewati", "-"}:
            clean_symbol = str((state.get("current") or {}).get("emoji") or "").strip()

        # Empty symbol is rejected because user explicitly wanted to choose it.
        if not clean_symbol:
            await update.message.reply_text("Symbol belum kebaca. Ketik symbol untuk kategori ini.", reply_markup=cancel_keyboard())
            # Return True to the caller.
            return True
        # Keep symbol short so the categories sheet stays readable.
        if len(clean_symbol) > 20:
            await update.message.reply_text("Symbol terlalu panjang. Pakai emoji atau label pendek saja.", reply_markup=cancel_keyboard())
            # Return True to the caller.
            return True

        state["emoji"] = clean_symbol
        # Run this statement as part of the current workflow.
        context.user_data[key] = state

        # Add mode auto-generates aliases immediately after symbol input.
        if mode == "add":
            # Wait for _prepare_new_category_preview before continuing this flow.
            await _prepare_new_category_preview(update, context, state)
            # Return True to the caller.
            return True

        # Edit mode needs one extra aliases step: manual, auto, or keep current.
        state["stage"] = "aliases"
        # Run this statement as part of the current workflow.
        context.user_data[key] = state
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            _build_alias_prompt(state),
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=cancel_keyboard(),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Edit aliases stage accepts manual aliases, auto generation, or keep current.
    if stage == "aliases":
        # Wait for _prepare_edited_category_preview before continuing this flow.
        await _prepare_edited_category_preview(update, context, state, user_text)
        # Return True to the caller.
        return True

    # Confirm stage does not consume extra values; user must press a button.
    if stage == "confirm":
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "Preview kategori sudah siap. Klik *Simpan* untuk menyimpan ke sheet, atau *Batal* untuk membatalkan.",
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=confirm_keyboard(_category_confirm_target(mode)),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Unknown stage is blocked so it cannot fall through into transaction parsing.
    await update.message.reply_text("State kategori tidak dikenali. Tekan *Batal*, lalu coba lagi.", parse_mode="Markdown", reply_markup=cancel_keyboard())
    # Return True to the caller.
    return True


# Handle the asynchronous prepare new category preview workflow.
async def _prepare_new_category_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, state: dict) -> None:
    """Generate aliases for a new category and show a save preview.

    Args:
        update: Telegram message update used to send progress and preview text.
        context: Telegram context containing the add wizard state.
        state: Add wizard state. Expected keys are `category_name`, `type`, and
            `emoji`.

    Returns:
        None. The function adds `aliases`, `alias_source`, and
        `aliases_changed` to state, then calls `_show_category_preview`.
    """
    # Pull category name and type collected by previous wizard steps.
    category_name = str(state.get("category_name") or "").strip()
    txn_type = str(state.get("type") or "expense").strip().lower()

    # Tell the user why there may be a short wait before preview appears.
    await update.message.reply_text("Gemini sedang generate aliases untuk kategori ini...")
    # Run this statement as part of the current workflow.
    aliases, source = _generate_aliases(category_name, txn_type)

    state["aliases"] = aliases
    state["alias_source"] = source
    state["aliases_changed"] = True
    await _show_category_preview(update, context, state, mode="add")


# Handle the asynchronous prepare edited category preview workflow.
async def _prepare_edited_category_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, state: dict, raw_aliases: str) -> None:
    """Prepare aliases for an edited category and show a save preview.

    Args:
        update: Telegram message update used to send progress and preview text.
        context: Telegram context containing the edit wizard state.
        state: Edit wizard state. Expected keys are `category_name`, `type`,
            `emoji`, and `current`.
        raw_aliases: User text for aliases. Accepted forms are comma-separated
            aliases, `auto`/`gemini`/`generate` to regenerate with Gemini, or
            `sama`/`tetap`/`skip`/`lewati`/`-` to keep the current aliases.

    Returns:
        None. The function updates the pending state and shows the preview. It
        does not write to Google Sheets.
    """
    # Pull edited category identity and type from prior wizard steps.
    category_name = str(state.get("category_name") or "").strip()
    txn_type = str(state.get("type") or "expense").strip().lower()
    # Normalize free-text alias command before branching.
    clean_input = str(raw_aliases or "").strip()
    # Prepare clean low for the next step.
    clean_low = clean_input.lower()

    # Manual input is the default unless the user asks to keep or auto-generate.
    source = "manual"
    # Prepare aliases changed for the next step.
    aliases_changed = True
    # Keep current aliases without writing column D when the user asks for it.
    if clean_low in {"sama", "tetap", "skip", "lewati", "-"}:
        # Reuse current sheet aliases and avoid updating column D.
        aliases = str((state.get("current") or {}).get("aliases") or "").strip()
        source = "dipertahankan"
        # Prepare aliases changed for the next step.
        aliases_changed = False
    elif clean_low in {"auto", "gemini", "generate", "regenerate", "buat otomatis"}:
        # Regenerate aliases through Gemini for the edited category.
        await update.message.reply_text("Gemini sedang generate ulang aliases untuk kategori ini...")
        # Run this statement as part of the current workflow.
        aliases, source = _generate_aliases(category_name, txn_type)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Manual aliases must stay in the same comma-separated sheet format.
        aliases = normalize_category_aliases(clean_input, category_name)

    # Manual or auto alias changes must produce at least one usable alias.
    if not aliases and aliases_changed:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "Aliases belum valid. Ketik daftar dipisah koma, `auto`, atau `sama`.",
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=cancel_keyboard(),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    state["aliases"] = aliases
    state["alias_source"] = source
    state["aliases_changed"] = aliases_changed
    await _show_category_preview(update, context, state, mode="edit")


# Handle the asynchronous handle category confirm callback workflow.
async def handle_category_confirm_callback(query, context: ContextTypes.DEFAULT_TYPE, confirm_target: str) -> bool:
    """Save pending category data after the user confirms the preview.

    Args:
        query: Telegram callback query from `confirm:category_add` or
            `confirm:category_edit`.
        context: Telegram context containing the pending category state.
        confirm_target: Confirmation target extracted by the central callback
            handler. Expected values are `category_add` or `category_edit`.

    Returns:
        `True` when this callback target belongs to category flow and was
        handled. `False` when the target is unrelated.

    Sheet writes:
        Add mode appends one row to `categories` using
        `category_name,type,emoji,aliases`. Edit mode updates only type, emoji,
        and aliases for the existing row. This is the only function in the
        category wizard that writes to Google Sheets.
    """
    # Ignore unrelated confirmation callbacks.
    if confirm_target not in {"category_add", "category_edit"}:
        # Return False to the caller.
        return False

    # Map callback target back into category wizard mode and state key.
    mode = "edit" if confirm_target == "category_edit" else "add"
    key = CATEGORY_EDIT_FLOW_KEY if mode == "edit" else CATEGORY_ADD_FLOW_KEY
    # Prepare state for the next step.
    state = context.user_data.get(key) or {}
    # A valid save must come from a prepared preview state.
    if not state or str(state.get("stage") or "") != "confirm":
        # Wait for safe_edit_message before continuing this flow.
        await safe_edit_message(
            # Include this value in the surrounding collection or call.
            query,
            f"Sesi kategori expired. Jalankan `/{'edit_kategori' if mode == 'edit' else 'add_kategori'}` lagi.",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Pull final values from preview state; no new user text is parsed here.
    category_name = str(state.get("category_name") or "").strip()
    txn_type = str(state.get("type") or "expense").strip().lower()
    symbol = str(state.get("emoji") or "").strip()
    aliases = str(state.get("aliases") or "").strip()
    source = str(state.get("alias_source") or "-").strip()

    # Let the user know the confirmed write is now being processed.
    await safe_edit_message(query, "Sedang menyimpan kategori ke sheet `categories`...", parse_mode="Markdown")

    # Add mode appends a new category row only after final confirmation.
    if mode == "add":
        # Prepare result for the next step.
        result = create_category(category_name, txn_type, symbol, aliases)
        # Clear add wizard state after the append attempt.
        context.user_data.pop(CATEGORY_ADD_FLOW_KEY, None)
        # Run this statement as part of the current workflow.
        context.user_data.pop(CATEGORY_PROMPT_MESSAGE_KEY, None)

        # Surface sheet/service errors without claiming success.
        if not result.get("success"):
            await safe_edit_message(query, f"Gagal menambahkan kategori: {md_safe(result.get('message') or '-')}", parse_mode="Markdown")
            # Return True to the caller.
            return True

        # Existing or similar categories are reported without appending a duplicate.
        if not result.get("created"):
            detected_category = str(result.get("category_name") or category_name).strip()
            # Prepare bulk state for the next step.
            bulk_state = context.user_data.get(BULK_EDIT_CATEGORY_DECISION_KEY) or {}
            # Prepare duplicate markup for the next step.
            duplicate_markup = None
            if bulk_state.get("paused_for_category_add") is not None:
                # Let paused bulk edit continue by using the detected existing category.
                current_index = int(bulk_state.get("current_index") or 0)
                decisions = bulk_state.get("decisions") or []
                # Handle the case where 0 <= current_index < len(decisions).
                if 0 <= current_index < len(decisions):
                    decisions[current_index]["suggested_category"] = detected_category
                    bulk_state["decisions"] = decisions
                    # Run this statement as part of the current workflow.
                    context.user_data[BULK_EDIT_CATEGORY_DECISION_KEY] = bulk_state
                label = detected_category if len(detected_category) <= 34 else detected_category[:31].rstrip() + "..."
                # Open a multi-line structure for the values below.
                duplicate_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"Ikuti {label}", callback_data="bulk_edit_category_choice:use")],
                    [InlineKeyboardButton("❌ Batal", callback_data="cancel:bulk_edit_category")],
                # Close the structure that was opened above.
                ])
            # Wait for safe_edit_message before continuing this flow.
            await safe_edit_message(
                # Include this value in the surrounding collection or call.
                query,
                "Kategori tidak ditambahkan karena sudah ada atau mirip kategori existing.\n\n"
                f"Kategori terdeteksi: *{md_safe(detected_category)}*",
                parse_mode="Markdown",
                # Prepare reply markup for the next step.
                reply_markup=duplicate_markup,
            # Close the structure that was opened above.
            )
            # Return True to the caller.
            return True

        # Fallback source gets an explicit note so aliases origin is transparent.
        source_note = "" if source == "Gemini" else "\n\nCatatan: Gemini gagal, jadi aliases fallback minimal dipakai."
        # Prepare bulk state for the next step.
        bulk_state = context.user_data.get(BULK_EDIT_CATEGORY_DECISION_KEY) or {}
        # Prepare resume markup for the next step.
        resume_markup = None
        if bulk_state.get("paused_for_category_add") is not None:
            # Resume is explicit so category write and transaction bulk preview stay separated.
            resume_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Lanjut bulk edit", callback_data="bulk_edit_category_choice:resume")],
                [InlineKeyboardButton("❌ Batal", callback_data="cancel:bulk_edit_category")],
            # Close the structure that was opened above.
            ])
        # Wait for safe_edit_message before continuing this flow.
        await safe_edit_message(
            # Include this value in the surrounding collection or call.
            query,
            "Kategori baru berhasil ditambahkan.\n\n"
            f"Kategori: *{md_safe(category_name)}*\n"
            f"Tipe: *{md_safe(txn_type)}*\n"
            f"Symbol: {md_safe(symbol)}\n"
            f"Aliases ({md_safe(source)}):\n"
            f"`{md_code_text(_format_aliases_for_message(aliases))}`"
            # Include this value in the surrounding collection or call.
            f"{source_note}",
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=resume_markup,
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Edit mode writes only the fields collected in the wizard.
    aliases_for_update = aliases if bool(state.get("aliases_changed")) else None
    # Open a multi-line structure for the values below.
    result = update_category(
        # Include this value in the surrounding collection or call.
        category_name,
        # Prepare transaction type for the next step.
        transaction_type=txn_type,
        # Prepare emoji for the next step.
        emoji=symbol,
        # Prepare aliases for the next step.
        aliases=aliases_for_update,
    # Close the structure that was opened above.
    )
    # Clear edit wizard state after the update attempt.
    context.user_data.pop(CATEGORY_EDIT_FLOW_KEY, None)
    # Run this statement as part of the current workflow.
    context.user_data.pop(CATEGORY_PROMPT_MESSAGE_KEY, None)

    # Surface update errors without claiming success.
    if not result.get("success"):
        await safe_edit_message(query, f"Gagal edit kategori: {md_safe(result.get('message') or '-')}", parse_mode="Markdown")
        # Return True to the caller.
        return True

    # Final success message mirrors the saved values.
    await safe_edit_message(
        # Include this value in the surrounding collection or call.
        query,
        "Kategori berhasil diupdate.\n\n"
        f"Kategori: *{md_safe(result.get('category_name') or category_name)}*\n"
        f"Tipe: *{md_safe(txn_type)}*\n"
        f"Symbol: {md_safe(symbol)}\n"
        f"Aliases ({md_safe(source)}):\n"
        f"`{md_code_text(_format_aliases_for_message(aliases))}`",
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )
    # Return True to the caller.
    return True
