"""Handlers for health checks, recurring transaction actions, and data export workflows."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *
# Import shlex for this module's local operations.
import shlex
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import resolve_account_name

# Define health status icon for callers in this flow.
def health_status_icon(ok: bool) -> str:
    """Coordinate the health status icon logic in the Telegram handler layer.

    Args:
        ok: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    return "🟢" if ok else "🔴"


# Define health warn icon for callers in this flow.
def health_warn_icon(ok: bool) -> str:
    """Coordinate the health warn icon logic in the Telegram handler layer.

    Args:
        ok: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    return "🟢" if ok else "🟡"


# Define safe health check for callers in this flow.
def safe_health_check(label: str, check_func):
    """Coordinate the safe health check logic in the Telegram handler layer.

    Args:
        label: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        check_func: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare result for the next step.
        result = check_func()

        # Handle the case where isinstance(result, tuple).
        if isinstance(result, tuple):
            # Run this statement as part of the current workflow.
            ok, message = result
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Prepare ok for the next step.
            ok = bool(result)
            message = "OK" if ok else "Failed"

        # Return { to the caller.
        return {
            "label": label,
            "ok": bool(ok),
            "message": str(message),
        # Close the structure that was opened above.
        }

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "label": label,
            "ok": False,
            "message": str(e),
        # Close the structure that was opened above.
        }


# Define check google sheets connection for callers in this flow.
def check_google_sheets_connection():
    """Validate conditions for the check google sheets connection workflow in the Telegram handler layer.

    Args:
        None.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Prepare spreadsheet for the next step.
    spreadsheet = get_spreadsheet()

    # Handle the missing or empty spreadsheet case.
    if not spreadsheet:
        return False, "Spreadsheet tidak tersedia."

    title = getattr(spreadsheet, "title", "") or "Connected"
    # Return True, title to the caller.
    return True, title


# Define check sheet readable for callers in this flow.
def check_sheet_readable(sheet_name: str):
    """Validate conditions for the check sheet readable workflow in the Telegram handler layer.

    Args:
        sheet_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Prepare records for the next step.
    records = get_all_records(sheet_name)
    return True, f"{len(records)} row readable"

# Define check wispybite for callers in this flow.
def check_wispybite():
    """Validate conditions for the check wispybite workflow in the Telegram handler layer.

    Args:
        None.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty WEBHOOK_URL case.
    if not WEBHOOK_URL:
        return False, "Webhook Url kosong."

    return True, "Webhook Url tersedia"

# Define check wispybite port for callers in this flow.
def check_wispybite_port():
    """Validate conditions for the check wispybite port workflow in the Telegram handler layer.

    Args:
        None.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty APP_PORT case.
    if not APP_PORT:
        return False, "Port Webhook kosong."

    return True, "Port Webhook tersedia"

# Define check gemini config for callers in this flow.
def check_gemini_config():
    """Validate conditions for the check gemini config workflow in the Telegram handler layer.

    Args:
        None.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty GEMINI_API_KEY case.
    if not GEMINI_API_KEY:
        return False, "GEMINI_API_KEY kosong."

    return True, "GEMINI_API_KEY tersedia"


# Define check environment config for callers in this flow.
def check_environment_config():
    """Validate conditions for the check environment config workflow in the Telegram handler layer.

    Args:
        None.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Open a multi-line structure for the values below.
    required_envs = [
        "TELEGRAM_BOT_TOKEN",
        "ALLOWED_USER_ID",
        "GOOGLE_SHEET_ID",
        "GEMINI_API_KEY",
    # Close the structure that was opened above.
    ]

    # Prepare missing for the next step.
    missing = []

    # Process each env_name in the current collection.
    for env_name in required_envs:
        # Handle the missing or empty os.getenv(env_name) case.
        if not os.getenv(env_name):
            # Update missing with the current value.
            missing.append(env_name)

    # Handle the case where missing.
    if missing:
        return False, "Missing: " + ", ".join(missing)

    return True, "Required env tersedia"


# Define build health report text for callers in this flow.
def build_health_report_text(results: list[dict]) -> str:
    """Build the data structure or message text for health report text."""
    # Prepare total for the next step.
    total = len(results)
    passed = sum(1 for r in results if r.get("ok"))
    # Prepare failed for the next step.
    failed = total - passed

    overall_icon = "🟢" if failed == 0 else "🟡" if passed > 0 else "🔴"

    # Open a multi-line structure for the values below.
    lines = [
        f"{overall_icon} *Health Check Finance Bot*\n",
        f"✅ Passed: *{passed}/{total}*",
        f"❌ Failed: *{failed}/{total}*\n",
    # Close the structure that was opened above.
    ]

    # Process each result in the current collection.
    for result in results:
        icon = health_status_icon(result.get("ok"))
        label = result.get("label", "-")
        message = result.get("message", "-")

        lines.append(f"{icon} *{label}*")
        lines.append(f"   `{message}`")

    # Handle the case where failed == 0.
    if failed == 0:
        lines.append("\n🚀 Semua komponen utama terlihat aman.")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.append("\n⚠️ Ada komponen yang perlu dicek.")

    return "\n".join(lines)

# Handle the asynchronous health handler workflow.
async def health_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous health handler flow in the Telegram handler layer.

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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    await update.message.reply_text("⏳ Menjalankan health check...")

    # Open a multi-line structure for the values below.
    sheet_names = {
        "transactions": "transactions",
        "accounts": "accounts",
        "budgets": "budgets",
        "pending_expenses": "pending_expenses",
        "debts": "debts",
        "debt_payments": "debt_payments",
        "recurring_rules": "recurring_rules",
        "recurring_logs": "recurring_logs",
    # Close the structure that was opened above.
    }

    # Prepare results for the next step.
    results = []

    # Open a multi-line structure for the values below.
    results.append(
        # Open a multi-line structure for the values below.
        safe_health_check(
            "Bot handler",
            lambda: (True, "Bot menerima command /health"),
        # Close the structure that was opened above.
        )
    # Close the structure that was opened above.
    )

    # Open a multi-line structure for the values below.
    results.append(
        # Open a multi-line structure for the values below.
        safe_health_check(
            "Environment config",
            # Include this value in the surrounding collection or call.
            check_environment_config,
        # Close the structure that was opened above.
        )
    # Close the structure that was opened above.
    )

    # Open a multi-line structure for the values below.
    results.append(
        # Open a multi-line structure for the values below.
        safe_health_check(
            "Google Sheets connection",
            # Include this value in the surrounding collection or call.
            check_google_sheets_connection,
        # Close the structure that was opened above.
        )
    # Close the structure that was opened above.
    )

    # Process each label, sheet_name in the current collection.
    for label, sheet_name in sheet_names.items():
        # Open a multi-line structure for the values below.
        results.append(
            # Open a multi-line structure for the values below.
            safe_health_check(
                f"Sheet: {label}",
                # Include this value in the surrounding collection or call.
                lambda sheet_name=sheet_name: check_sheet_readable(sheet_name),
            # Close the structure that was opened above.
            )
        # Close the structure that was opened above.
        )

    # Open a multi-line structure for the values below.
    results.append(
        # Open a multi-line structure for the values below.
        safe_health_check(
            "Gemini config",
            # Include this value in the surrounding collection or call.
            check_gemini_config,
        # Close the structure that was opened above.
        )
    # Close the structure that was opened above.
    )

    # Open a multi-line structure for the values below.
    results.append(
        # Open a multi-line structure for the values below.
        safe_health_check(
            "Webhook Url Config",
            # Include this value in the surrounding collection or call.
            check_wispybite,
        # Close the structure that was opened above.
        )
    # Close the structure that was opened above.
    )
    # Open a multi-line structure for the values below.
    results.append(
        # Open a multi-line structure for the values below.
        safe_health_check(
            "Webhook Port Config",
            # Include this value in the surrounding collection or call.
            check_wispybite_port,
        # Close the structure that was opened above.
        )
    # Close the structure that was opened above.
    )

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_health_report_text(results),
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )

RECURRING_ADD_FLOW_KEY = "pending_recurring_add_flow"
RECURRING_ADD_PROMPT_MESSAGE_KEY = "pending_recurring_add_prompt_message_id"
RECURRING_ADD_SKIP_WORDS = {"skip", "lewati", "kosong", "-", "tidak", "tidak ada", "ga ada", "gak ada", "nggak ada"}
RECURRING_ADD_STEPS = ["name", "txn_type", "amount", "category", "account", "frequency", "day_of_month", "description"]
RECURRING_ADD_OPTIONAL_STEPS = {"description"}


# Define recurring is skip for callers in this flow.
def _recurring_is_skip(text: str) -> bool:
    """Check whether the user wants to skip an optional recurring field."""
    return str(text or "").strip().lower() in RECURRING_ADD_SKIP_WORDS


# Define recurring add step keyboard for callers in this flow.
def recurring_add_step_keyboard(step: str) -> InlineKeyboardMarkup:
    """Build a per-step keyboard for recurring add wizard."""
    # Prepare rows for the next step.
    rows = []
    # Handle the case where step in RECURRING_ADD_OPTIONAL_STEPS.
    if step in RECURRING_ADD_OPTIONAL_STEPS:
        rows.append([InlineKeyboardButton("⏭️ Lewati", callback_data="recurring_add:skip")])
    rows.append([InlineKeyboardButton("🚫 Batal", callback_data="cancel:recurring_add")])
    # Return InlineKeyboardMarkup(rows) to the caller.
    return InlineKeyboardMarkup(rows)


# Define recurring step prompt for callers in this flow.
def _recurring_step_prompt(step: str, data: dict | None = None) -> str:
    """Build the prompt for one recurring add wizard step."""
    # Prepare data for the next step.
    data = data or {}
    # Open a multi-line structure for the values below.
    prompts = {
        "name": (
            "🔁 *Tambah Recurring — Step 1/8*\n\n"
            "Nama transaksi rutinnya apa?\n\n"
            "Contoh:\n"
            "`Netflix`\n"
            "`Internet rumah`"
        # Close the structure that was opened above.
        ),
        "txn_type": (
            "↕️ *Tambah Recurring — Step 2/8*\n\n"
            f"Nama: *{md_safe(data.get('name') or '-')}*\n\n"
            "Tipe transaksinya apa?\n\n"
            "Contoh: `expense` / `pengeluaran` atau `income` / `pemasukan`."
        # Close the structure that was opened above.
        ),
        "amount": (
            "💰 *Tambah Recurring — Step 3/8*\n\n"
            "Nominalnya berapa?\n\n"
            "Contoh: `65000`, `65k`, atau `1.5 juta`."
        # Close the structure that was opened above.
        ),
        "category": (
            "📁 *Tambah Recurring — Step 4/8*\n\n"
            "Kategorinya apa?\n\n"
            "Contoh: `Entertainment`, `Bills & Utilities`, atau `Food & Beverage`."
        # Close the structure that was opened above.
        ),
        "account": (
            "🏦 *Tambah Recurring — Step 5/8*\n\n"
            "Pakai rekening apa?\n\n"
            "Contoh: `DANA`, `BRI`, atau `Cash`."
        # Close the structure that was opened above.
        ),
        "frequency": (
            "📆 *Tambah Recurring — Step 6/8*\n\n"
            "Frekuensinya apa?\n\n"
            "Untuk sekarang isi `monthly` atau `bulanan`."
        # Close the structure that was opened above.
        ),
        "day_of_month": (
            "🗓️ *Tambah Recurring — Step 7/8*\n\n"
            "Setiap tanggal berapa?\n\n"
            "Contoh: `5`, `10`, atau `30`."
        # Close the structure that was opened above.
        ),
        "description": (
            "📝 *Tambah Recurring — Step 8/8*\n\n"
            "Deskripsinya apa?\n\n"
            "Contoh: `Langganan Netflix`.\n\n"
            "Kalau mau pakai nama transaksi saja, tekan `Lewati`."
        # Close the structure that was opened above.
        ),
    # Close the structure that was opened above.
    }
    suffix = "\n\nGunakan tombol di bawah, atau ketik `batal` untuk cancel."
    # Handle the case where step in RECURRING_ADD_OPTIONAL_STEPS.
    if step in RECURRING_ADD_OPTIONAL_STEPS:
        suffix += " Untuk field opsional, boleh tekan `Lewati`."
    return prompts.get(step, "Step recurring tidak dikenali.") + suffix


# Handle the asynchronous send recurring add step prompt workflow.
async def send_recurring_add_step_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, step: str, data: dict | None = None):
    """Send a recurring wizard prompt and clean the previous wizard keyboard."""
    # Return await reply_tracked_inline_keyboard( to the caller.
    return await reply_tracked_inline_keyboard(
        # Include this value in the surrounding collection or call.
        update,
        # Include this value in the surrounding collection or call.
        context,
        # Include this value in the surrounding collection or call.
        _recurring_step_prompt(step, data),
        parse_mode="Markdown",
        # Prepare reply markup for the next step.
        reply_markup=recurring_add_step_keyboard(step),
        # Prepare state key for the next step.
        state_key=RECURRING_ADD_PROMPT_MESSAGE_KEY,
    # Close the structure that was opened above.
    )


# Handle the asynchronous clear recurring add step keyboard workflow.
async def clear_recurring_add_step_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the active recurring wizard step keyboard after user answers."""
    chat = getattr(update, "effective_chat", None)
    chat_id = getattr(chat, "id", None) or getattr(getattr(update, "message", None), "chat_id", None)
    # Wait for clear_tracked_inline_keyboard before continuing this flow.
    await clear_tracked_inline_keyboard(context, chat_id, RECURRING_ADD_PROMPT_MESSAGE_KEY)


def start_recurring_add_flow(context: ContextTypes.DEFAULT_TYPE, initial_data: dict | None = None, step: str = "name") -> None:
    """Start recurring add wizard with optional prefilled fields."""
    context.user_data.pop("pending_recurring_confirm", None)
    # Open a multi-line structure for the values below.
    context.user_data[RECURRING_ADD_FLOW_KEY] = {
        "step": step or "name",
        "data": dict(initial_data or {}),
    # Close the structure that was opened above.
    }


# Define normalize recurring txn type for callers in this flow.
def _normalize_recurring_txn_type(value: str) -> str | None:
    """Normalize input values for the normalize recurring txn type workflow in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str | None` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    clean = str(value or "").strip().lower()
    # Open a multi-line structure for the values below.
    aliases = {
        "expense": "expense",
        "pengeluaran": "expense",
        "keluar": "expense",
        "income": "income",
        "pemasukan": "income",
        "masuk": "income",
    # Close the structure that was opened above.
    }
    # Return aliases.get(clean) to the caller.
    return aliases.get(clean)


# Define normalize recurring frequency text for callers in this flow.
def _normalize_recurring_frequency_text(value: str) -> str | None:
    """Normalize recurring frequency aliases supported by the service."""
    clean = str(value or "").strip().lower()
    # Open a multi-line structure for the values below.
    aliases = {
        "monthly": "monthly",
        "bulan": "monthly",
        "bulanan": "monthly",
        "setiap bulan": "monthly",
    # Close the structure that was opened above.
    }
    # Return aliases.get(clean) to the caller.
    return aliases.get(clean)


# Define resolve recurring account for callers in this flow.
def _resolve_recurring_account(value: str) -> str:
    """Use account resolver when possible, but keep typed value as fallback."""
    raw = str(value or "").strip()
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare resolved for the next step.
        resolved = resolve_account_name(raw)
        if resolved.get("status") == "exact":
            return str(resolved.get("account_name") or raw).strip()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass
    # Return raw to the caller.
    return raw


# Define next missing recurring step for callers in this flow.
def _next_missing_recurring_step(data: dict) -> str | None:
    """Return the first recurring wizard field that is still missing."""
    # Process each step in the current collection.
    for step in RECURRING_ADD_STEPS:
        if step == "description":
            # Skip the rest of this loop iteration after handling this case.
            continue
        if data.get(step) in [None, ""]:
            # Return step to the caller.
            return step
    return "description" if "description" not in data else None


# Define build recurring confirm preview for callers in this flow.
def build_recurring_confirm_preview(data: dict) -> str:
    """Build structured output for the build recurring confirm preview workflow in the Telegram handler layer.

    Args:
        data: Structured input data used by the current flow.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Return ( to the caller.
    return (
        "🔁 *Preview Tambah Recurring*\n\n"
        f"Nama: *{md_safe(data.get('name') or '-')}*\n"
        f"Tipe: *{md_safe(data.get('txn_type') or '-')}*\n"
        f"Nominal: *{format_rupiah(float(data.get('amount', 0) or 0))}*\n"
        f"Kategori: *{md_safe(data.get('category') or '-')}*\n"
        f"Rekening: *{md_safe(data.get('account') or '-')}*\n"
        f"Jadwal: *{md_safe(data.get('frequency') or 'monthly')}*, setiap tanggal *{md_safe(data.get('day_of_month') or '-')}*\n"
        f"Deskripsi: {md_safe(data.get('description') or data.get('name') or '-')}\n\n"
        "Mau simpan atau batal?"
    # Close the structure that was opened above.
    )


# Define build recurring saved text for callers in this flow.
def build_recurring_saved_text(rule: dict) -> str:
    """Build structured output for the build recurring saved text workflow in the Telegram handler layer.

    Args:
        rule: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Return ( to the caller.
    return (
        "✅ *Recurring transaction berhasil dibuat!*\n\n"
        f"🔁 Nama: *{md_safe(rule.get('name') or '-')}*\n"
        f"💰 Nominal: *{format_rupiah(float(rule.get('amount', 0) or 0))}*\n"
        f"📁 Kategori: *{md_safe(rule.get('category') or '-')}*\n"
        f"🏦 Rekening: *{md_safe(rule.get('account') or '-')}*\n"
        f"📅 Jadwal: setiap tanggal *{md_safe(rule.get('day_of_month') or '-')}*\n"
        f"⏭️ Next run: `{md_code_text(rule.get('next_run_date') or '-')}`\n"
        f"🔖 ID: `{md_code_text(rule.get('id') or '-')}`"
    # Close the structure that was opened above.
    )


# Define save pending recurring rule for callers in this flow.
def save_pending_recurring_rule(data: dict) -> dict:
    """Persist a pending recurring rule using the existing recurring service."""
    # Return add_recurring_rule( to the caller.
    return add_recurring_rule(
        name=data["name"],
        txn_type=data["txn_type"],
        amount=data["amount"],
        category=data["category"],
        account=data["account"],
        frequency=data.get("frequency") or "monthly",
        day_of_month=data["day_of_month"],
        description=data.get("description") or data.get("name"),
    # Close the structure that was opened above.
    )


# Define partial recurring data from args for callers in this flow.
def _partial_recurring_data_from_args(args: list[str]) -> dict:
    """Read partial /recurring_add args without forcing the old full pipe format."""
    raw = " ".join(args or []).strip()
    # Handle the missing or empty raw case.
    if not raw:
        # Return {} to the caller.
        return {}
    if "|" not in raw:
        return {"name": raw}

    parts = [p.strip() for p in raw.split("|")]
    keys = ["name", "txn_type", "amount", "category", "account", "frequency", "day_of_month", "description"]
    # Prepare data for the next step.
    data = {}
    # Process each key, value in the current collection.
    for key, value in zip(keys, parts):
        # Handle the missing or empty value case.
        if not value:
            # Skip the rest of this loop iteration after handling this case.
            continue
        if key == "txn_type":
            # Prepare normalized for the next step.
            normalized = _normalize_recurring_txn_type(value)
            # Handle the case where normalized.
            if normalized:
                # Run this statement as part of the current workflow.
                data[key] = normalized
        elif key == "amount":
            # Prepare amount for the next step.
            amount = parse_human_amount(value)
            # Handle the case where amount > 0.
            if amount > 0:
                # Run this statement as part of the current workflow.
                data[key] = amount
        elif key == "frequency":
            # Prepare normalized for the next step.
            normalized = _normalize_recurring_frequency_text(value)
            # Handle the case where normalized.
            if normalized:
                # Run this statement as part of the current workflow.
                data[key] = normalized
        elif key == "day_of_month":
            # Run this statement as part of the current workflow.
            data[key] = value
        elif key == "account":
            # Run this statement as part of the current workflow.
            data[key] = _resolve_recurring_account(value)
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Run this statement as part of the current workflow.
            data[key] = value
    # Return data to the caller.
    return data


# Handle the asynchronous finish recurring add flow workflow.
async def _finish_recurring_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> bool:
    """Handle the asynchronous finish recurring add flow flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.
        data: Structured input data used by the current flow.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    if not data.get("description"):
        data["description"] = data.get("name") or ""
    context.user_data["pending_recurring_confirm"] = dict(data)
    # Run this statement as part of the current workflow.
    context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)
    # Run this statement as part of the current workflow.
    context.user_data.pop(RECURRING_ADD_PROMPT_MESSAGE_KEY, None)
    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_recurring_confirm_preview(data),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("recurring"),
    # Close the structure that was opened above.
    )
    # Return True to the caller.
    return True


# Handle the asynchronous handle pending recurring add flow workflow.
async def handle_pending_recurring_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Handle the asynchronous handle pending recurring add flow flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.
        user_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Prepare flow for the next step.
    flow = context.user_data.get(RECURRING_ADD_FLOW_KEY)
    # Handle the missing or empty flow case.
    if not flow:
        # Return False to the caller.
        return False

    text = str(user_text or "").strip()
    # Wait for clear_recurring_add_step_keyboard before continuing this flow.
    await clear_recurring_add_step_keyboard(update, context)

    if text.lower() in {"batal", "cancel", "/cancel"}:
        # Run this statement as part of the current workflow.
        context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)
        # Run this statement as part of the current workflow.
        context.user_data.pop(RECURRING_ADD_PROMPT_MESSAGE_KEY, None)
        context.user_data.pop("pending_recurring_confirm", None)
        await update.message.reply_text("❌ Tambah recurring dibatalkan.")
        # Return True to the caller.
        return True

    step = flow.get("step", "name")
    data = flow.setdefault("data", {})

    if step == "name":
        # Handle the missing or empty text case.
        if not text:
            await send_recurring_add_step_prompt(update, context, "name", data)
            # Return True to the caller.
            return True
        data["name"] = text
        flow["step"] = "txn_type"
        await send_recurring_add_step_prompt(update, context, "txn_type", data)
        # Return True to the caller.
        return True

    if step == "txn_type":
        # Prepare txn type for the next step.
        txn_type = _normalize_recurring_txn_type(text)
        # Handle the missing or empty txn_type case.
        if not txn_type:
            await update.message.reply_text("❌ Tipe belum valid. Isi `expense` atau `income`.", parse_mode="Markdown")
            await send_recurring_add_step_prompt(update, context, "txn_type", data)
            # Return True to the caller.
            return True
        data["txn_type"] = txn_type
        flow["step"] = "amount"
        await send_recurring_add_step_prompt(update, context, "amount", data)
        # Return True to the caller.
        return True

    if step == "amount":
        # Prepare amount for the next step.
        amount = parse_human_amount(text)
        # Handle the case where amount <= 0.
        if amount <= 0:
            await update.message.reply_text("❌ Nominal belum valid. Contoh: `65000`, `65k`, atau `1.5 juta`.", parse_mode="Markdown")
            await send_recurring_add_step_prompt(update, context, "amount", data)
            # Return True to the caller.
            return True
        data["amount"] = amount
        flow["step"] = "category"
        await send_recurring_add_step_prompt(update, context, "category", data)
        # Return True to the caller.
        return True

    if step == "category":
        # Handle the missing or empty text case.
        if not text:
            await send_recurring_add_step_prompt(update, context, "category", data)
            # Return True to the caller.
            return True
        data["category"] = text
        flow["step"] = "account"
        await send_recurring_add_step_prompt(update, context, "account", data)
        # Return True to the caller.
        return True

    if step == "account":
        # Handle the missing or empty text case.
        if not text:
            await send_recurring_add_step_prompt(update, context, "account", data)
            # Return True to the caller.
            return True
        data["account"] = _resolve_recurring_account(text)
        flow["step"] = "frequency"
        await send_recurring_add_step_prompt(update, context, "frequency", data)
        # Return True to the caller.
        return True

    if step == "frequency":
        # Prepare frequency for the next step.
        frequency = _normalize_recurring_frequency_text(text)
        # Handle the missing or empty frequency case.
        if not frequency:
            await update.message.reply_text("❌ Frekuensi belum valid. Saat ini gunakan `monthly` atau `bulanan`.", parse_mode="Markdown")
            await send_recurring_add_step_prompt(update, context, "frequency", data)
            # Return True to the caller.
            return True
        data["frequency"] = frequency
        flow["step"] = "day_of_month"
        await send_recurring_add_step_prompt(update, context, "day_of_month", data)
        # Return True to the caller.
        return True

    if step == "day_of_month":
        # Run this operation in a guarded block so failures can be handled.
        try:
            day_int = int(re.sub(r"[^0-9]", "", text))
            # Handle the case where day_int < 1 or day_int > 31.
            if day_int < 1 or day_int > 31:
                # Raise a clear error so the caller can stop this invalid flow.
                raise ValueError
        # Handle an expected failure from the guarded operation above.
        except Exception:
            await update.message.reply_text("❌ Tanggal recurring harus angka 1 sampai 31.", parse_mode="Markdown")
            await send_recurring_add_step_prompt(update, context, "day_of_month", data)
            # Return True to the caller.
            return True
        data["day_of_month"] = day_int
        flow["step"] = "description"
        await send_recurring_add_step_prompt(update, context, "description", data)
        # Return True to the caller.
        return True

    if step == "description":
        data["description"] = data.get("name") if _recurring_is_skip(text) else text
        # Return await _finish_recurring_add_flow(update, context, data) to the caller.
        return await _finish_recurring_add_flow(update, context, data)

    # Run this statement as part of the current workflow.
    context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)
    await update.message.reply_text("❌ Sesi recurring tidak valid. Coba ulangi `/recurring_add`.", parse_mode="Markdown")
    # Return True to the caller.
    return True


# Handle the asynchronous handle recurring add skip callback workflow.
async def handle_recurring_add_skip_callback(query, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle the asynchronous handle recurring add skip callback flow in the Telegram handler layer.

    Args:
        query: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Prepare flow for the next step.
    flow = context.user_data.get(RECURRING_ADD_FLOW_KEY)
    # Handle the missing or empty flow case.
    if not flow:
        await safe_edit_message(query, "❌ Sesi recurring expired. Coba ulangi `/recurring_add`.", parse_mode="Markdown")
        # Return True to the caller.
        return True
    step = flow.get("step", "")
    data = flow.setdefault("data", {})
    if step != "description":
        await safe_edit_message(query, "❌ Step ini tidak bisa dilewati.", parse_mode="Markdown")
        # Return True to the caller.
        return True
    data["description"] = data.get("name") or ""
    context.user_data["pending_recurring_confirm"] = dict(data)
    # Run this statement as part of the current workflow.
    context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)
    # Run this statement as part of the current workflow.
    context.user_data.pop(RECURRING_ADD_PROMPT_MESSAGE_KEY, None)
    # Wait for safe_edit_message before continuing this flow.
    await safe_edit_message(
        # Include this value in the surrounding collection or call.
        query,
        # Include this value in the surrounding collection or call.
        build_recurring_confirm_preview(data),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("recurring"),
    # Close the structure that was opened above.
    )
    # Return True to the caller.
    return True




# Open a multi-line structure for the values below.
RECURRING_ADD_USAGE_TEXT = (
    "Format key=value:\n"
    "`/recurring_add name=Netflix type=expense amount=65000 category=Entertainment account=DANA frequency=monthly day=5 description=\"Langganan Netflix\"`"
# Close the structure that was opened above.
)

# Open a multi-line structure for the values below.
RECURRING_EDIT_USAGE_TEXT = (
    "Contoh:\n"
    "`/recurring_edit rec_xxx amount=75000 day=10`\n"
    "`/recurring_edit rec_xxx day=10 account=BRI`\n"
    "`/recurring_edit rec_xxx name=\"Netflix Premium\" amount=75000 day=5`\n"
    "`/recurring_edit rec_xxx next_run_date=2026-06-11`"
# Close the structure that was opened above.
)


# Define parse key value tokens for callers in this flow.
def _parse_key_value_tokens(tokens: list[str]) -> dict:
    """Parse key=value tokens and allow unquoted continuation words until the next key=value."""
    # Prepare updates for the next step.
    updates = {}
    # Prepare i for the next step.
    i = 0
    # Repeat this block while i < len(tokens).
    while i < len(tokens):
        token = str(tokens[i] or "").strip()
        # Handle the missing or empty token case.
        if not token:
            # Run this statement as part of the current workflow.
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue
        if "=" not in token:
            raise ValueError(f"Format `{token}` belum valid. Gunakan `field=value`.")

        field, value = token.split("=", 1)
        # Prepare field for the next step.
        field = field.strip().lower()
        # Prepare value parts for the next step.
        value_parts = [value.strip()] if value.strip() else []
        # Run this statement as part of the current workflow.
        i += 1

        while i < len(tokens) and "=" not in str(tokens[i] or ""):
            continuation = str(tokens[i] or "").strip()
            # Handle the case where continuation.
            if continuation:
                # Update value parts with the current value.
                value_parts.append(continuation)
            # Run this statement as part of the current workflow.
            i += 1

        value = " ".join(value_parts).strip()
        # Handle the missing or empty field or not value case.
        if not field or not value:
            raise ValueError(f"Format `{token}` belum valid. Field dan value wajib diisi.")
        # Run this statement as part of the current workflow.
        updates[field] = value

    # Return updates to the caller.
    return updates


# Define tokenize command args for callers in this flow.
def _tokenize_command_args(raw: str) -> list[str]:
    """Coordinate the tokenize command args logic in the Telegram handler layer.

    Args:
        raw: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        return shlex.split(str(raw or "").replace("|", " "))
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return str(raw or "").replace("|", " ").split()


# Define recurring command args from update for callers in this flow.
def _recurring_command_args_from_update(update: Update, context: ContextTypes.DEFAULT_TYPE, command_name: str) -> list[str]:
    """Read recurring command arguments from the original Telegram message.

    Args:
        update: Telegram update that may come from `CommandHandler` or the
            fallback regex `MessageHandler`.
        context: Telegram callback context. `context.args` is used only when
            the original text does not contain the requested slash command.
        command_name: Slash command without `/`, for example `recurring_add`.

    Returns:
        A list suitable for the existing recurring parser. When possible the
        function returns the raw command tail as a single item so quoted values
        such as `category="Bills & Utilities"` remain intact.

    Side effects:
        None. This helper only reads the incoming message and context.

    Flow constraints:
        Keep recurring add/edit parsing preview-before-save; this helper must
        not save recurring rules or mutate Google Sheets.
    """
    message = getattr(update, "message", None)
    text = str(getattr(message, "text", "") or "").strip()
    pattern = rf"^/{re.escape(command_name)}(?:@\w+)?(?:\s+(.*))?$"
    match = re.match(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    # Prefer the original command tail so shell-like quotes survive fallback routing.
    if match:
        raw_tail = str(match.group(1) or "").strip()
        return [raw_tail] if raw_tail else []
    # Fall back to python-telegram-bot command args for normal CommandHandler calls.
    return list(getattr(context, "args", None) or [])


# Define normalize recurring key values for callers in this flow.
def _normalize_recurring_key_values(values: dict) -> dict:
    """Normalize recurring key=value fields into recurring service keys."""
    # Open a multi-line structure for the values below.
    aliases = {
        "type": "txn_type",
        "txn_type": "txn_type",
        "tipe": "txn_type",
        "jenis": "txn_type",
        "amount": "amount",
        "nominal": "amount",
        "jumlah": "amount",
        "harga": "amount",
        "category": "category",
        "kategori": "category",
        "account": "account",
        "rekening": "account",
        "akun": "account",
        "frequency": "frequency",
        "freq": "frequency",
        "jadwal": "frequency",
        "day": "day_of_month",
        "tanggal": "day_of_month",
        "day_of_month": "day_of_month",
        "description": "description",
        "desc": "description",
        "deskripsi": "description",
        "name": "name",
        "nama": "name",
    # Close the structure that was opened above.
    }
    # Prepare normalized for the next step.
    normalized = {}
    # Process each field, value in the current collection.
    for field, value in (values or {}).items():
        key = aliases.get(str(field or "").strip().lower())
        # Handle the case where key.
        if key:
            # Run this statement as part of the current workflow.
            normalized[key] = value
    # Return normalized to the caller.
    return normalized


# Define coerce recurring data for callers in this flow.
def _coerce_recurring_data(data: dict) -> dict:
    """Coordinate the coerce recurring data logic in the Telegram handler layer.

    Args:
        data: Structured input data used by the current flow.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Prepare coerced for the next step.
    coerced = dict(data or {})
    if coerced.get("txn_type"):
        txn_type = _normalize_recurring_txn_type(coerced.get("txn_type"))
        # Handle the missing or empty txn_type case.
        if not txn_type:
            raise ValueError("Tipe belum valid. Isi `type=expense` atau `type=income`.")
        coerced["txn_type"] = txn_type

    if coerced.get("amount") not in [None, ""]:
        amount = parse_human_amount(str(coerced.get("amount")))
        # Handle the case where amount <= 0.
        if amount <= 0:
            raise ValueError("Nominal belum valid. Contoh: `amount=65000`, `amount=65k`, atau `amount=1.5 juta`.")
        coerced["amount"] = amount

    if coerced.get("frequency"):
        frequency = _normalize_recurring_frequency_text(coerced.get("frequency"))
        # Handle the missing or empty frequency case.
        if not frequency:
            raise ValueError("Frekuensi belum valid. Saat ini gunakan `frequency=monthly` atau `frequency=bulanan`.")
        coerced["frequency"] = frequency

    if coerced.get("account"):
        coerced["account"] = _resolve_recurring_account(coerced.get("account"))

    if coerced.get("day_of_month") not in [None, ""]:
        day_raw = str(coerced.get("day_of_month"))
        # Run this operation in a guarded block so failures can be handled.
        try:
            day_int = int(re.sub(r"[^0-9]", "", day_raw))
            # Handle the case where day_int < 1 or day_int > 31.
            if day_int < 1 or day_int > 31:
                # Raise a clear error so the caller can stop this invalid flow.
                raise ValueError
        # Handle an expected failure from the guarded operation above.
        except Exception:
            raise ValueError("Tanggal recurring harus angka 1 sampai 31. Contoh: `day=5`.")
        coerced["day_of_month"] = day_int

    if not coerced.get("description") and coerced.get("name"):
        coerced["description"] = coerced.get("name")

    # Return coerced to the caller.
    return coerced

# Define parse recurring add args for callers in this flow.
def parse_recurring_add_args(args: list[str]) -> dict:
    """Parse /recurring_add args in key=value format, while keeping old pipe input readable."""
    raw = " ".join(args).strip()

    # Handle the missing or empty raw case.
    if not raw:
        raise ValueError("Format kosong.\n\n" + RECURRING_ADD_USAGE_TEXT)

    if "=" in raw:
        # Prepare tokens for the next step.
        tokens = _tokenize_command_args(raw)
        # Prepare key values for the next step.
        key_values = _parse_key_value_tokens(tokens)
        # Prepare data for the next step.
        data = _normalize_recurring_key_values(key_values)
        # Prepare data for the next step.
        data = _coerce_recurring_data(data)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        parts = [p.strip() for p in raw.split("|")]
        # Handle the case where len(parts) < 7.
        if len(parts) < 7:
            raise ValueError("Format recurring belum lengkap.\n\n" + RECURRING_ADD_USAGE_TEXT)

        # Open a multi-line structure for the values below.
        data = _coerce_recurring_data({
            "name": parts[0],
            "txn_type": parts[1],
            "amount": parts[2],
            "category": parts[3],
            "account": parts[4],
            "frequency": parts[5],
            "day_of_month": parts[6],
            "description": parts[7] if len(parts) >= 8 else parts[0],
        # Close the structure that was opened above.
        })

    required = ["name", "txn_type", "amount", "category", "account", "frequency", "day_of_month"]
    missing = [field for field in required if data.get(field) in [None, ""]]
    # Handle the case where missing.
    if missing:
        # Raise a clear error so the caller can stop this invalid flow.
        raise ValueError(
            "Field recurring belum lengkap: " + ", ".join(missing) + ".\n\n" + RECURRING_ADD_USAGE_TEXT
        # Close the structure that was opened above.
        )

    # Return data to the caller.
    return data


# Define parse recurring edit args for callers in this flow.
def parse_recurring_edit_args(args: list[str]) -> tuple[str, dict]:
    """Parse /recurring_edit args using key=value format; old pipe input is still accepted."""
    raw = " ".join(args).strip()

    # Handle the missing or empty raw case.
    if not raw:
        raise ValueError("Format kosong.\n\n" + RECURRING_EDIT_USAGE_TEXT)

    # Prepare tokens for the next step.
    tokens = _tokenize_command_args(raw)
    # Handle the missing or empty tokens case.
    if not tokens:
        raise ValueError("Format belum valid.\n\n" + RECURRING_EDIT_USAGE_TEXT)

    # Prepare rule id for the next step.
    rule_id = tokens[0].strip()
    # Handle the missing or empty rule_id case.
    if not rule_id:
        raise ValueError("Recurring rule ID wajib diisi.")

    # Handle the case where len(tokens) < 2.
    if len(tokens) < 2:
        raise ValueError("Field edit belum diisi.\n\n" + RECURRING_EDIT_USAGE_TEXT)

    # Prepare updates for the next step.
    updates = _parse_key_value_tokens(tokens[1:])

    # Handle the missing or empty updates case.
    if not updates:
        raise ValueError("Field edit belum diisi.\n\n" + RECURRING_EDIT_USAGE_TEXT)

    # Return rule_id, updates to the caller.
    return rule_id, updates


# Define build recurring edit result text for callers in this flow.
def build_recurring_edit_result_text(result: dict) -> str:
    """Build the data structure or message text for recurring edit result text."""
    before = result.get("rule_before", {}) or {}
    after = result.get("rule_after", {}) or {}
    updates = result.get("updates", {}) or {}

    lines = ["✅ Recurring rule berhasil diupdate!\n"]

    lines.append(f"Nama: {after.get('name') or before.get('name') or '-'}")
    lines.append(f"ID: {after.get('id') or before.get('id') or '-'}")

    lines.append("\nField yang berubah:")

    # Process each field in the current collection.
    for field in updates:
        if field == "updated_at":
            # Skip the rest of this loop iteration after handling this case.
            continue

        old_value = before.get(field, "-")
        new_value = after.get(field, updates.get(field, "-"))

        lines.append(f"- {field}: {old_value} → {new_value}")

    lines.append(f"\nNext run: {after.get('next_run_date', '-')}")
    lines.append(f"Status: {after.get('is_active', '-')}")

    return "\n".join(lines)

# Handle the asynchronous recurring edit handler workflow.
async def recurring_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous recurring edit handler flow in the Telegram handler layer.

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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Read args from the original text so fallback routing keeps quoted values intact.
        command_args = _recurring_command_args_from_update(update, context, "recurring_edit")
        # Run this statement as part of the current workflow.
        rule_id, updates = parse_recurring_edit_args(command_args)

        # Prepare result for the next step.
        result = edit_recurring_rule(rule_id, updates)

        if not result.get("success"):
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"❌ {result.get('message')}\n\n"
                "Cek ID dengan command:\n"
                "/recurring"
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Run this statement as part of the current workflow.
            build_recurring_edit_result_text(result)
        # Close the structure that was opened above.
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Gagal edit recurring rule.\n\n"
            f"{str(e)}\n\n"
            # Run this statement as part of the current workflow.
            + RECURRING_EDIT_USAGE_TEXT
        # Close the structure that was opened above.
        )

# Define short rule id for callers in this flow.
def short_rule_id(rule_id: str) -> str:
    """Coordinate the short rule id logic in the Telegram handler layer.

    Args:
        rule_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    rule_id = str(rule_id or "")
    # Handle the case where len(rule_id) <= 18.
    if len(rule_id) <= 18:
        # Return rule_id to the caller.
        return rule_id
    # Return rule_id to the caller.
    return rule_id


# Define build recurring rules text for callers in this flow.
def build_recurring_rules_text(rules: list[dict]) -> str:
    """Build the data structure or message text for recurring rules text."""
    # Handle the missing or empty rules case.
    if not rules:
        # Return ( to the caller.
        return (
            "📭 Belum ada recurring transaction.\n\n"
            "Tambah dengan format:\n"
            "`/recurring_add name=Netflix type=expense amount=65000 category=Entertainment account=DANA frequency=monthly day=5 description=\"Langganan Netflix\"`"
        # Close the structure that was opened above.
        )

    lines = ["🔁 *Recurring Transaction*\n"]

    # Process each i, rule in the current collection.
    for i, rule in enumerate(rules, 1):
        is_active = str(rule.get("is_active", "")).strip().upper() == "TRUE"
        status_icon = "✅" if is_active else "⛔"

        txn_type = str(rule.get("type", "")).strip()
        type_icon = "❌" if txn_type == "expense" else "✅" if txn_type == "income" else "❓"

        # Open a multi-line structure for the values below.
        lines.append(
            f"{i}. {status_icon} {type_icon} *{rule.get('name', '-')}*\n"
            f"   💰 {format_rupiah(float(rule.get('amount', 0) or 0))} | {rule.get('category', '-')}\n"
            f"   🏦 {rule.get('account', '-')}\n"
            f"   🔁 {rule.get('frequency', '-')} tanggal {rule.get('day_of_month', '-')}\n"
            f"   📅 Next run: `{rule.get('next_run_date', '-')}`\n"
            f"   🔖 `{short_rule_id(rule.get('id', ''))}`"
        # Close the structure that was opened above.
        )

    # Open a multi-line structure for the values below.
    lines.append(
        "\nCommand:\n"
        "`/recurring_add ...` — tambah recurring\n"
        "`/recurring_run` — jalankan recurring yang sudah jatuh tempo\n"
        "`/recurring_off <rule_id>` — nonaktifkan recurring"
    # Close the structure that was opened above.
    )

    return "\n".join(lines)


# Define build recurring run text for callers in this flow.
def build_recurring_run_text(result: dict) -> str:
    """Build the data structure or message text for recurring run text."""
    # Open a multi-line structure for the values below.
    lines = [
        "🔁 *Recurring Run Result*\n",
        f"📅 Tanggal run: `{result.get('run_date')}`",
        f"📌 Rule jatuh tempo: *{result.get('count_due', 0)}*",
    # Close the structure that was opened above.
    ]

    success = result.get("success", [])
    failed = result.get("failed", [])

    # Handle the case where success.
    if success:
        lines.append("\n✅ *Berhasil dibuat:*")

        # Process each item in the current collection.
        for item in success:
            rule = item.get("rule", {})
            # Open a multi-line structure for the values below.
            lines.append(
                f"• {rule.get('name', '-')}: "
                f"{format_rupiah(float(rule.get('amount', 0) or 0))} "
                f"→ next `{item.get('next_run_date', '-')}`"
            # Close the structure that was opened above.
            )

    # Handle the case where failed.
    if failed:
        lines.append("\n❌ *Gagal:*")

        # Process each item in the current collection.
        for item in failed:
            rule = item.get("rule", {})
            # Open a multi-line structure for the values below.
            lines.append(
                f"• {rule.get('name', '-')} — {item.get('message', '-')}"
            # Close the structure that was opened above.
            )

    # Handle the missing or empty success and not failed case.
    if not success and not failed:
        lines.append("\n📭 Tidak ada recurring yang jatuh tempo.")

    return "\n".join(lines)

# Handle the asynchronous recurring handler workflow.
async def recurring_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous recurring handler flow in the Telegram handler layer.

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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare rules for the next step.
    rules = get_recurring_rules(active_only=False)

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_recurring_rules_text(rules),
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )


# Handle the asynchronous recurring add handler workflow.
async def recurring_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /recurring_add with guided wizard or old pipe format preview."""
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Read args from the original text so fallback routing keeps quoted values intact.
        command_args = _recurring_command_args_from_update(update, context, "recurring_add")
        # Start the wizard when the command has no inline arguments.
        if not command_args:
            # Run this statement as part of the current workflow.
            start_recurring_add_flow(context)
            await send_recurring_add_step_prompt(update, context, "name", {})
            # Return control to the caller.
            return

        raw_arg = " ".join(command_args).strip()

        if "=" in raw_arg:
            # Prepare data for the next step.
            data = parse_recurring_add_args(command_args)
            data["account"] = _resolve_recurring_account(data.get("account"))
            context.user_data["pending_recurring_confirm"] = data
            # Run this statement as part of the current workflow.
            context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)

            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                # Include this value in the surrounding collection or call.
                build_recurring_confirm_preview(data),
                parse_mode="Markdown",
                reply_markup=confirm_keyboard("recurring"),
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        if "|" not in raw_arg:
            start_recurring_add_flow(context, {"name": raw_arg}, step="txn_type")
            await send_recurring_add_step_prompt(update, context, "txn_type", {"name": raw_arg})
            # Return control to the caller.
            return

        # Prepare partial for the next step.
        partial = _partial_recurring_data_from_args(command_args)
        # Prepare missing step for the next step.
        missing_step = _next_missing_recurring_step(partial)

        if missing_step and missing_step != "description":
            # Run this statement as part of the current workflow.
            start_recurring_add_flow(context, partial, step=missing_step)
            # Wait for send_recurring_add_step_prompt before continuing this flow.
            await send_recurring_add_step_prompt(update, context, missing_step, partial)
            # Return control to the caller.
            return

        if missing_step == "description":
            start_recurring_add_flow(context, partial, step="description")
            await send_recurring_add_step_prompt(update, context, "description", partial)
            # Return control to the caller.
            return

        # Prepare data for the next step.
        data = parse_recurring_add_args(command_args)
        data["account"] = _resolve_recurring_account(data.get("account"))
        context.user_data["pending_recurring_confirm"] = data
        # Run this statement as part of the current workflow.
        context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_recurring_confirm_preview(data),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("recurring"),
        # Close the structure that was opened above.
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ Gagal membuat recurring transaction.\n\n{str(e)}",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )


# Handle the asynchronous recurring run handler workflow.
async def recurring_run_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous recurring run handler flow in the Telegram handler layer.

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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare result for the next step.
        result = process_due_recurring_rules()

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_recurring_run_text(result),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ Gagal menjalankan recurring: {str(e)}"
        # Close the structure that was opened above.
        )


# Handle the asynchronous recurring off handler workflow.
async def recurring_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous recurring off handler flow in the Telegram handler layer.

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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Handle the missing or empty context.args case.
    if not context.args:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Masukkan recurring rule ID.\n\n"
            "Contoh:\n"
            "`/recurring_off rec_20260610_123456_xxxxxx`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare rule id for the next step.
    rule_id = context.args[0].strip()

    # Prepare success for the next step.
    success = disable_recurring_rule(rule_id)

    # Handle the missing or empty success case.
    if not success:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Recurring rule tidak ditemukan."
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        f"✅ Recurring rule berhasil dinonaktifkan:\n`{rule_id}`",
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )

# Define write transactions to csv for callers in this flow.
def write_transactions_to_csv(records: list[dict], file_path: str):
    """Apply the write transactions to csv operation in the Telegram handler layer.

    Args:
        records: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        file_path: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
        # Open a multi-line structure for the values below.
        writer = csv.DictWriter(
            # Include this value in the surrounding collection or call.
            f,
            # Prepare fieldnames for the next step.
            fieldnames=EXPORT_TRANSACTION_COLUMNS,
            extrasaction="ignore",
        # Close the structure that was opened above.
        )

        # Run this statement as part of the current workflow.
        writer.writeheader()

        # Process each record in the current collection.
        for record in records:
            # Prepare row for the next step.
            row = {}

            # Process each col in the current collection.
            for col in EXPORT_TRANSACTION_COLUMNS:
                row[col] = record.get(col, "")

            # Run this statement as part of the current workflow.
            writer.writerow(row)


# Define build export caption for callers in this flow.
def build_export_caption(export_result: dict) -> str:
    """Build the data structure or message text for export caption."""
    filter_info = export_result.get("filter", {})
    summary = export_result.get("summary", {})

    label = filter_info.get("label", "-")
    count = summary.get("count", 0)
    total_income = summary.get("total_income", 0)
    total_expense = summary.get("total_expense", 0)
    total_transfer = summary.get("total_transfer", 0)
    net = summary.get("net", 0)

    # Return ( to the caller.
    return (
        f"✅ *Export transaksi berhasil!*\n\n"
        f"📅 Periode: *{label}*\n"
        f"📝 Jumlah transaksi: *{count}*\n"
        f"✅ Total pemasukan: *{format_rupiah(total_income)}*\n"
        f"❌ Total pengeluaran: *{format_rupiah(total_expense)}*\n"
        f"🔄 Total transfer: *{format_rupiah(total_transfer)}*\n"
        f"📊 Net: *{format_rupiah(net)}*"
    # Close the structure that was opened above.
    )


def build_export_privacy_warning() -> str:
    """Build the short privacy warning shown before sending an export file.

    Args:
        None.

    Returns:
        Telegram Markdown text warning that CSV export contains personal
        finance data.

    Side effects:
        None. The helper only returns static text and does not create, read, or
        modify export files.

    Flow constraints:
        Keep the export file format unchanged. This warning is informational and
        does not open a confirmation flow, so it does not need a Batal button.
    """
    return "File export berisi data finance pribadi. Simpan dan bagikan dengan hati-hati."


# Handle the asynchronous export handler workflow.
async def export_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous export handler flow in the Telegram handler layer.

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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare period for the next step.
    period = context.args[0] if context.args else None

    # Prepare export result for the next step.
    export_result = get_transactions_for_export(period)

    if not export_result.get("success"):
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ {export_result.get('message')}\n\n"
            "Contoh:\n"
            "`/download_data`\n"
            "`/download_data today`\n"
            "`/download_data week`\n"
            "`/download_data month`\n"
            "`/download_data 2026-06`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    records = export_result.get("records", [])
    filter_info = export_result.get("filter", {})

    # Handle the missing or empty records case.
    if not records:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"📭 Tidak ada transaksi untuk periode *{filter_info.get('label', '-')}*.",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    filename_suffix = filter_info.get("filename_suffix", datetime.now().strftime("%Y-%m"))
    filename = f"transactions_{filename_suffix}.csv"

    # Prepare temp dir for the next step.
    temp_dir = tempfile.gettempdir()
    # Prepare file path for the next step.
    file_path = os.path.join(temp_dir, filename)

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Run this statement as part of the current workflow.
        write_transactions_to_csv(records, file_path)

        # Warn before sending the sensitive finance export file.
        await update.message.reply_text(build_export_privacy_warning(), parse_mode="Markdown")

        with open(file_path, "rb") as f:
            # Wait for update.message.reply_document before continuing this flow.
            await update.message.reply_document(
                # Prepare document for the next step.
                document=InputFile(f, filename=filename),
                # Prepare filename for the next step.
                filename=filename,
                # Prepare caption for the next step.
                caption=build_export_caption(export_result),
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ Gagal membuat file CSV: {str(e)}"
        # Close the structure that was opened above.
        )

    # Run cleanup that must happen after the guarded operation.
    finally:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Handle the case where os.path.exists(file_path).
            if os.path.exists(file_path):
                # Update os with the current value.
                os.remove(file_path)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass

# Handle the asynchronous scheduled export transactions workflow.
async def scheduled_export_transactions(bot, chat_id: int, period=None):
    """Handle the asynchronous scheduled export transactions flow in the Telegram handler layer.

    Args:
        bot: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        chat_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        period: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Prepare export result for the next step.
    export_result = get_transactions_for_export(period)

    if not export_result.get("success"):
        # Wait for bot.send_message before continuing this flow.
        await bot.send_message(
            # Prepare chat id for the next step.
            chat_id=chat_id,
            text=f"❌ Auto export gagal.\n{export_result.get('message')}",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    records = export_result.get("records", [])
    filter_info = export_result.get("filter", {})

    # Handle the missing or empty records case.
    if not records:
        # Wait for bot.send_message before continuing this flow.
        await bot.send_message(
            # Prepare chat id for the next step.
            chat_id=chat_id,
            # Open a multi-line structure for the values below.
            text=(
                "📭 Auto export: tidak ada transaksi untuk periode "
                f"{filter_info.get('label', '-')}."
            # Close the structure that was opened above.
            ),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Open a multi-line structure for the values below.
    filename_suffix = filter_info.get(
        "filename_suffix",
        datetime.now().strftime("%Y-%m"),
    # Close the structure that was opened above.
    )
    filename = f"transactions_{filename_suffix}.csv"

    # Prepare temp dir for the next step.
    temp_dir = tempfile.gettempdir()
    # Prepare file path for the next step.
    file_path = os.path.join(temp_dir, filename)

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Run this statement as part of the current workflow.
        write_transactions_to_csv(records, file_path)

        with open(file_path, "rb") as f:
            # Wait for bot.send_document before continuing this flow.
            await bot.send_document(
                # Prepare chat id for the next step.
                chat_id=chat_id,
                # Prepare document for the next step.
                document=InputFile(f, filename=filename),
                # Prepare filename for the next step.
                filename=filename,
                # Open a multi-line structure for the values below.
                caption=(
                    "⏰ *Auto Export Data Finance*\n"
                    "Jadwal: 23:55 WIB\n\n"
                    # Include the same sensitivity note used by manual exports.
                    f"{build_export_caption(export_result)}\n\n"
                    f"{build_export_privacy_warning()}"
                # Close the structure that was opened above.
                ),
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for bot.send_message before continuing this flow.
        await bot.send_message(
            # Prepare chat id for the next step.
            chat_id=chat_id,
            text=f"❌ Auto export gagal membuat file CSV: {str(e)}",
        # Close the structure that was opened above.
        )

    # Run cleanup that must happen after the guarded operation.
    finally:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Handle the case where os.path.exists(file_path).
            if os.path.exists(file_path):
                # Update os with the current value.
                os.remove(file_path)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass


# Prepare GEMINI INTENT CONFIDENCE EXECUTE for the next step.
GEMINI_INTENT_CONFIDENCE_EXECUTE = 0.80
# Prepare GEMINI INTENT CONFIDENCE CLARIFY for the next step.
GEMINI_INTENT_CONFIDENCE_CLARIFY = 0.60


