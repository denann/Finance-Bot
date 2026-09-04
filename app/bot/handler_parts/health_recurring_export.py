"""Handlers for health checks, recurring transaction actions, and data export workflows."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *
from app.clock import business_now
# Import shlex for this module's local operations.
import shlex
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import resolve_account_name
from app.services.recurring_service import get_due_recurring_rules, get_recurring_rule_by_id
from app.observability import emit_event
from app.application.external_io import run_scheduled, run_sheets_read
from app.bot.handler_parts.management_browser import start_recurring_browser


def create_unique_export_temp_path() -> str:
    """Create one collision-resistant CSV path for a single export attempt.

    Returns:
        Absolute temporary path owned by the caller. The caller must remove it
        in ``finally`` after Telegram delivery succeeds or fails.

    Side effects:
        Creates one empty temporary file without exposing finance metadata in
        its filename.
    """

    descriptor, file_path = tempfile.mkstemp(prefix="finance_export_", suffix=".csv")
    os.close(descriptor)
    return file_path

# Helper for health status icon.
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


# Helper for health warn icon.
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


# Helper for safe health check.
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
        # Build result for the response flow.
        result = check_func()

        if isinstance(result, tuple):
            ok, message = result
        # Use the fallback path when no earlier branch matched.
        else:
            ok = bool(result)
            message = "OK" if ok else "Failed"

        return {
            "label": label,
            "ok": bool(ok),
            "message": str(message),
        }

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {
            "label": label,
            "ok": False,
            "message": str(e),
        }


# Helper for check google sheets connection.
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
    spreadsheet = get_spreadsheet()

    # Validate missing spreadsheet before continuing.
    if not spreadsheet:
        return False, "Spreadsheet tidak tersedia."

    title = getattr(spreadsheet, "title", "") or "Connected"
    return True, title


# Helper for check sheet readable.
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
    # Load records for the current calculation.
    records = get_all_records(sheet_name)
    return True, f"{len(records)} row readable"

# Helper for check wispybite.
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
    # Validate missing WEBHOOK URL before continuing.
    if not WEBHOOK_URL:
        return False, "Webhook Url kosong."

    return True, "Webhook Url tersedia"

# Helper for check wispybite port.
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
    # Validate missing APP PORT before continuing.
    if not APP_PORT:
        return False, "Port Webhook kosong."

    return True, "Port Webhook tersedia"

# Helper for check gemini config.
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
    # Validate missing GEMINI API KEY before continuing.
    if not GEMINI_API_KEY:
        return False, "GEMINI_API_KEY kosong."

    return True, "GEMINI_API_KEY tersedia"


# Helper for check environment config.
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
    required_envs = [
        "TELEGRAM_BOT_TOKEN",
        "ALLOWED_USER_ID",
        "GOOGLE_SHEET_ID",
        "GEMINI_API_KEY",
    ]

    missing = []

    # Iterate through each env name.
    for env_name in required_envs:
        # Validate missing os.getenv(env name) before continuing.
        if not os.getenv(env_name):
            # Append the current value to missing.
            missing.append(env_name)

    if missing:
        return False, "Missing: " + ", ".join(missing)

    return True, "Required env tersedia"


# Helper for build health report text.
def build_health_report_text(results: list[dict]) -> str:
    """Build the data structure or message text for health report text."""
    total = len(results)
    passed = sum(1 for r in results if r.get("ok"))
    failed = total - passed

    overall_icon = "🟢" if failed == 0 else "🟡" if passed > 0 else "🔴"

    lines = [
        f"{overall_icon} *Health Check Finance Bot*\n",
        f"✅ Passed: *{passed}/{total}*",
        f"❌ Failed: *{failed}/{total}*\n",
    ]

    # Iterate through each result.
    for result in results:
        icon = health_status_icon(result.get("ok"))
        label = result.get("label", "-")
        message = result.get("message", "-")

        lines.append(f"{icon} *{label}*")
        lines.append(f"   `{message}`")

    if failed == 0:
        lines.append("\n🚀 Semua komponen utama terlihat aman.")
    # Use the fallback path when no earlier branch matched.
    else:
        lines.append("\n⚠️ Ada komponen yang perlu dicek.")

    return "\n".join(lines)

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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    await update.message.reply_text("⏳ Menjalankan health check...")

    sheet_names = {
        "transactions": "transactions",
        "accounts": "accounts",
        "budgets": "budgets",
        "pending_expenses": "pending_expenses",
        "debts": "debts",
        "debt_payments": "debt_payments",
        "recurring_rules": "recurring_rules",
        "recurring_logs": "recurring_logs",
    }

    # Build results for the response flow.
    results = []

    results.append(
        safe_health_check(
            "Bot handler",
            lambda: (True, "Bot menerima command /health"),
        )
    )

    results.append(
        safe_health_check(
            "Environment config",
            check_environment_config,
        )
    )

    results.append(
        safe_health_check(
            "Google Sheets connection",
            check_google_sheets_connection,
        )
    )

    # Iterate through each label, sheet name.
    for label, sheet_name in sheet_names.items():
        results.append(
            safe_health_check(
                f"Sheet: {label}",
                lambda sheet_name=sheet_name: check_sheet_readable(sheet_name),
            )
        )

    results.append(
        safe_health_check(
            "Gemini config",
            check_gemini_config,
        )
    )

    results.append(
        safe_health_check(
            "Webhook Url Config",
            check_wispybite,
        )
    )
    results.append(
        safe_health_check(
            "Webhook Port Config",
            check_wispybite_port,
        )
    )

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_health_report_text(results),
        parse_mode="Markdown",
    )

RECURRING_ADD_FLOW_KEY = "pending_recurring_add_flow"
RECURRING_ADD_PROMPT_MESSAGE_KEY = "pending_recurring_add_prompt_message_id"
RECURRING_ADD_SKIP_WORDS = {"skip", "lewati", "kosong", "-", "tidak", "tidak ada", "ga ada", "gak ada", "nggak ada"}
RECURRING_ADD_STEPS = ["name", "txn_type", "amount", "category", "account", "frequency", "day_of_month", "description"]
RECURRING_ADD_OPTIONAL_STEPS = {"description"}


# Helper for recurring is skip.
def _recurring_is_skip(text: str) -> bool:
    """Check whether the user wants to skip an optional recurring field."""
    return str(text or "").strip().lower() in RECURRING_ADD_SKIP_WORDS


# Helper for recurring add step keyboard.
def recurring_add_step_keyboard(step: str) -> InlineKeyboardMarkup:
    """Build a per-step keyboard for recurring add wizard."""
    # Load rows for the current calculation.
    rows = []
    if step in RECURRING_ADD_OPTIONAL_STEPS:
        rows.append([InlineKeyboardButton("⏭️ Lewati", callback_data="recurring_add:skip")])
    rows.append([InlineKeyboardButton("🚫 Batal", callback_data="cancel:recurring_add")])
    return InlineKeyboardMarkup(rows)


# Helper for recurring step prompt.
def _recurring_step_prompt(step: str, data: dict | None = None) -> str:
    """Build the prompt for one recurring add wizard step."""
    data = data or {}
    prompts = {
        "name": (
            "🔁 *Tambah Recurring — Step 1/8*\n\n"
            "Nama transaksi rutinnya apa?\n\n"
            "Contoh:\n"
            "`Netflix`\n"
            "`Internet rumah`"
        ),
        "txn_type": (
            "↕️ *Tambah Recurring — Step 2/8*\n\n"
            f"Nama: *{md_safe(data.get('name') or '-')}*\n\n"
            "Tipe transaksinya apa?\n\n"
            "Contoh: `expense` / `pengeluaran` atau `income` / `pemasukan`."
        ),
        "amount": (
            "💰 *Tambah Recurring — Step 3/8*\n\n"
            "Nominalnya berapa?\n\n"
            "Contoh: `65000`, `65k`, atau `1.5 juta`."
        ),
        "category": (
            "📁 *Tambah Recurring — Step 4/8*\n\n"
            "Kategorinya apa?\n\n"
            "Contoh: `Entertainment`, `Bills & Utilities`, atau `Food & Beverage`."
        ),
        "account": (
            "🏦 *Tambah Recurring — Step 5/8*\n\n"
            "Pakai rekening apa?\n\n"
            "Contoh: `DANA`, `BRI`, atau `Cash`."
        ),
        "frequency": (
            "📆 *Tambah Recurring — Step 6/8*\n\n"
            "Frekuensinya apa?\n\n"
            "Untuk sekarang isi `monthly` atau `bulanan`."
        ),
        "day_of_month": (
            "🗓️ *Tambah Recurring — Step 7/8*\n\n"
            "Setiap tanggal berapa?\n\n"
            "Contoh: `5`, `10`, atau `30`."
        ),
        "description": (
            "📝 *Tambah Recurring — Step 8/8*\n\n"
            "Deskripsinya apa?\n\n"
            "Contoh: `Langganan Netflix`.\n\n"
            "Kalau mau pakai nama transaksi saja, tekan `Lewati`."
        ),
    }
    suffix = "\n\nGunakan tombol di bawah, atau ketik `batal` untuk cancel."
    if step in RECURRING_ADD_OPTIONAL_STEPS:
        suffix += " Untuk field opsional, boleh tekan `Lewati`."
    return prompts.get(step, "Step recurring tidak dikenali.") + suffix


# Handle the asynchronous send recurring add step prompt workflow.
async def send_recurring_add_step_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, step: str, data: dict | None = None):
    """Send a recurring wizard prompt and clean the previous wizard keyboard."""
    return await reply_tracked_inline_keyboard(
        update,
        context,
        _recurring_step_prompt(step, data),
        parse_mode="Markdown",
        reply_markup=recurring_add_step_keyboard(step),
        state_key=RECURRING_ADD_PROMPT_MESSAGE_KEY,
    )


# Handle the asynchronous clear recurring add step keyboard workflow.
async def clear_recurring_add_step_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the active recurring wizard step keyboard after user answers."""
    chat = getattr(update, "effective_chat", None)
    chat_id = getattr(chat, "id", None) or getattr(getattr(update, "message", None), "chat_id", None)
    # Await clear tracked inline keyboard before continuing.
    await clear_tracked_inline_keyboard(context, chat_id, RECURRING_ADD_PROMPT_MESSAGE_KEY)


def start_recurring_add_flow(context: ContextTypes.DEFAULT_TYPE, initial_data: dict | None = None, step: str = "name") -> None:
    """Start recurring add wizard with optional prefilled fields."""
    context.user_data.pop("pending_recurring_confirm", None)
    context.user_data[RECURRING_ADD_FLOW_KEY] = {
        "step": step or "name",
        "data": dict(initial_data or {}),
    }


# Helper for normalize recurring txn type.
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
    aliases = {
        "expense": "expense",
        "pengeluaran": "expense",
        "keluar": "expense",
        "income": "income",
        "pemasukan": "income",
        "masuk": "income",
    }
    return aliases.get(clean)


# Helper for normalize recurring frequency text.
def _normalize_recurring_frequency_text(value: str) -> str | None:
    """Normalize recurring frequency aliases supported by the service."""
    clean = str(value or "").strip().lower()
    aliases = {
        "monthly": "monthly",
        "bulan": "monthly",
        "bulanan": "monthly",
        "setiap bulan": "monthly",
    }
    return aliases.get(clean)


# Helper for resolve recurring account.
def _resolve_recurring_account(value: str) -> str:
    """Use account resolver when possible, but keep typed value as fallback."""
    raw = str(value or "").strip()
    # Run this operation in a guarded block so failures can be handled.
    try:
        resolved = resolve_account_name(raw)
        if resolved.get("status") == "exact":
            return str(resolved.get("account_name") or raw).strip()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass
    return raw


# Helper for next missing recurring step.
def _next_missing_recurring_step(data: dict) -> str | None:
    """Return the first recurring wizard field that is still missing."""
    # Iterate through each step.
    for step in RECURRING_ADD_STEPS:
        if step == "description":
            # Skip the rest of this loop iteration after handling this case.
            continue
        if data.get(step) in [None, ""]:
            return step
    return "description" if "description" not in data else None


# Helper for build recurring confirm preview.
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
    )


# Helper for build recurring saved text.
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
    return (
        "✅ *Recurring transaction berhasil dibuat!*\n\n"
        f"🔁 Nama: *{md_safe(rule.get('name') or '-')}*\n"
        f"💰 Nominal: *{format_rupiah(float(rule.get('amount', 0) or 0))}*\n"
        f"📁 Kategori: *{md_safe(rule.get('category') or '-')}*\n"
        f"🏦 Rekening: *{md_safe(rule.get('account') or '-')}*\n"
        f"📅 Jadwal: setiap tanggal *{md_safe(rule.get('day_of_month') or '-')}*\n"
        f"⏭️ Next run: `{md_code_text(rule.get('next_run_date') or '-')}`\n"
        f"🔖 ID: `{md_code_text(rule.get('id') or '-')}`"
    )


# Helper for save pending recurring rule.
def save_pending_recurring_rule(data: dict) -> dict:
    """Persist a pending recurring rule using the existing recurring service."""
    return add_recurring_rule(
        name=data["name"],
        txn_type=data["txn_type"],
        amount=data["amount"],
        category=data["category"],
        account=data["account"],
        frequency=data.get("frequency") or "monthly",
        day_of_month=data["day_of_month"],
        description=data.get("description") or data.get("name"),
    )


# Helper for partial recurring data from args.
def _partial_recurring_data_from_args(args: list[str]) -> dict:
    """Read partial /recurring_add args without forcing the old full pipe format."""
    raw = " ".join(args or []).strip()
    # Validate missing raw before continuing.
    if not raw:
        return {}
    if "|" not in raw:
        return {"name": raw}

    parts = [p.strip() for p in raw.split("|")]
    keys = ["name", "txn_type", "amount", "category", "account", "frequency", "day_of_month", "description"]
    data = {}
    # Iterate through each key, value.
    for key, value in zip(keys, parts):
        # Validate missing value before continuing.
        if not value:
            # Skip the rest of this loop iteration after handling this case.
            continue
        if key == "txn_type":
            # Normalize normalized before matching.
            normalized = _normalize_recurring_txn_type(value)
            if normalized:
                data[key] = normalized
        elif key == "amount":
            # Extract amount for validation.
            amount = parse_human_amount(value)
            if amount > 0:
                data[key] = amount
        elif key == "frequency":
            # Normalize normalized before matching.
            normalized = _normalize_recurring_frequency_text(value)
            if normalized:
                data[key] = normalized
        elif key == "day_of_month":
            data[key] = value
        elif key == "account":
            data[key] = _resolve_recurring_account(value)
        # Use the fallback path when no earlier branch matched.
        else:
            data[key] = value
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
    context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)
    context.user_data.pop(RECURRING_ADD_PROMPT_MESSAGE_KEY, None)
    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_recurring_confirm_preview(data),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("recurring"),
    )
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
    flow = context.user_data.get(RECURRING_ADD_FLOW_KEY)
    # Validate missing flow before continuing.
    if not flow:
        return False

    text = str(user_text or "").strip()
    # Await clear recurring add step keyboard before continuing.
    await clear_recurring_add_step_keyboard(update, context)

    if text.lower() in {"batal", "cancel", "/cancel"}:
        context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)
        context.user_data.pop(RECURRING_ADD_PROMPT_MESSAGE_KEY, None)
        context.user_data.pop("pending_recurring_confirm", None)
        await update.message.reply_text("❌ Tambah recurring dibatalkan.")
        return True

    step = flow.get("step", "name")
    data = flow.setdefault("data", {})

    if step == "name":
        # Validate missing text before continuing.
        if not text:
            await send_recurring_add_step_prompt(update, context, "name", data)
            return True
        data["name"] = text
        flow["step"] = "txn_type"
        await send_recurring_add_step_prompt(update, context, "txn_type", data)
        return True

    if step == "txn_type":
        txn_type = _normalize_recurring_txn_type(text)
        # Validate missing txn type before continuing.
        if not txn_type:
            await update.message.reply_text("❌ Tipe belum valid. Isi `expense` atau `income`.", parse_mode="Markdown")
            await send_recurring_add_step_prompt(update, context, "txn_type", data)
            return True
        data["txn_type"] = txn_type
        flow["step"] = "amount"
        await send_recurring_add_step_prompt(update, context, "amount", data)
        return True

    if step == "amount":
        # Extract amount for validation.
        amount = parse_human_amount(text)
        if amount <= 0:
            await update.message.reply_text("❌ Nominal belum valid. Contoh: `65000`, `65k`, atau `1.5 juta`.", parse_mode="Markdown")
            await send_recurring_add_step_prompt(update, context, "amount", data)
            return True
        data["amount"] = amount
        flow["step"] = "category"
        await send_recurring_add_step_prompt(update, context, "category", data)
        return True

    if step == "category":
        # Validate missing text before continuing.
        if not text:
            await send_recurring_add_step_prompt(update, context, "category", data)
            return True
        data["category"] = text
        flow["step"] = "account"
        await send_recurring_add_step_prompt(update, context, "account", data)
        return True

    if step == "account":
        # Validate missing text before continuing.
        if not text:
            await send_recurring_add_step_prompt(update, context, "account", data)
            return True
        data["account"] = _resolve_recurring_account(text)
        flow["step"] = "frequency"
        await send_recurring_add_step_prompt(update, context, "frequency", data)
        return True

    if step == "frequency":
        frequency = _normalize_recurring_frequency_text(text)
        # Validate missing frequency before continuing.
        if not frequency:
            await update.message.reply_text("❌ Frekuensi belum valid. Saat ini gunakan `monthly` atau `bulanan`.", parse_mode="Markdown")
            await send_recurring_add_step_prompt(update, context, "frequency", data)
            return True
        data["frequency"] = frequency
        flow["step"] = "day_of_month"
        await send_recurring_add_step_prompt(update, context, "day_of_month", data)
        return True

    if step == "day_of_month":
        # Run this operation in a guarded block so failures can be handled.
        try:
            day_int = int(re.sub(r"[^0-9]", "", text))
            # Handle day int < 1 or day int > 31.
            if day_int < 1 or day_int > 31:
                # Raise a clear error so the caller can stop this invalid flow.
                raise ValueError
        # Handle an expected failure from the guarded operation above.
        except Exception:
            await update.message.reply_text("❌ Tanggal recurring harus angka 1 sampai 31.", parse_mode="Markdown")
            await send_recurring_add_step_prompt(update, context, "day_of_month", data)
            return True
        data["day_of_month"] = day_int
        flow["step"] = "description"
        await send_recurring_add_step_prompt(update, context, "description", data)
        return True

    if step == "description":
        data["description"] = data.get("name") if _recurring_is_skip(text) else text
        return await _finish_recurring_add_flow(update, context, data)

    context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)
    await update.message.reply_text("❌ Sesi recurring tidak valid. Coba ulangi `/recurring_add`.", parse_mode="Markdown")
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
    flow = context.user_data.get(RECURRING_ADD_FLOW_KEY)
    # Validate missing flow before continuing.
    if not flow:
        await safe_edit_message(query, "❌ Sesi recurring expired. Coba ulangi `/recurring_add`.", parse_mode="Markdown")
        return True
    step = flow.get("step", "")
    data = flow.setdefault("data", {})
    if step != "description":
        await safe_edit_message(query, "❌ Step ini tidak bisa dilewati.", parse_mode="Markdown")
        return True
    data["description"] = data.get("name") or ""
    context.user_data["pending_recurring_confirm"] = dict(data)
    context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)
    context.user_data.pop(RECURRING_ADD_PROMPT_MESSAGE_KEY, None)
    # Send the Telegram response before continuing.
    await safe_edit_message(
        query,
        build_recurring_confirm_preview(data),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("recurring"),
    )
    return True




RECURRING_ADD_USAGE_TEXT = (
    "Format key=value:\n"
    "`/recurring_add name=Netflix type=expense amount=65000 category=Entertainment account=DANA frequency=monthly day=5 description=\"Langganan Netflix\"`"
)

RECURRING_EDIT_USAGE_TEXT = (
    "Contoh:\n"
    "`/recurring_edit rec_xxx amount=75000 day=10`\n"
    "`/recurring_edit rec_xxx day=10 account=BRI`\n"
    "`/recurring_edit rec_xxx name=\"Netflix Premium\" amount=75000 day=5`\n"
    "`/recurring_edit rec_xxx next_run_date=2026-06-11`"
)


# Helper for parse key value tokens.
def _parse_key_value_tokens(tokens: list[str]) -> dict:
    """Parse key=value tokens and allow unquoted continuation words until the next key=value."""
    # Extract updates for validation.
    updates = {}
    i = 0
    # Repeat this block while i < len(tokens).
    while i < len(tokens):
        token = str(tokens[i] or "").strip()
        # Validate missing token before continuing.
        if not token:
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue
        if "=" not in token:
            raise ValueError(f"Format `{token}` belum valid. Gunakan `field=value`.")

        field, value = token.split("=", 1)
        field = field.strip().lower()
        # Prepare value parts from the incoming input.
        value_parts = [value.strip()] if value.strip() else []
        i += 1

        while i < len(tokens) and "=" not in str(tokens[i] or ""):
            continuation = str(tokens[i] or "").strip()
            if continuation:
                # Append the current value to value parts.
                value_parts.append(continuation)
            i += 1

        value = " ".join(value_parts).strip()
        # Validate missing field or not value before continuing.
        if not field or not value:
            raise ValueError(f"Format `{token}` belum valid. Field dan value wajib diisi.")
        updates[field] = value

    return updates


# Helper for tokenize command args.
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


# Helper for recurring command args from update.
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


# Helper for normalize recurring key values.
def _normalize_recurring_key_values(values: dict) -> dict:
    """Normalize recurring key=value fields into recurring service keys."""
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
    }
    # Normalize normalized before matching.
    normalized = {}
    # Iterate through each field, value.
    for field, value in (values or {}).items():
        key = aliases.get(str(field or "").strip().lower())
        if key:
            normalized[key] = value
    return normalized


# Helper for coerce recurring data.
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
    coerced = dict(data or {})
    if coerced.get("txn_type"):
        txn_type = _normalize_recurring_txn_type(coerced.get("txn_type"))
        # Validate missing txn type before continuing.
        if not txn_type:
            raise ValueError("Tipe belum valid. Isi `type=expense` atau `type=income`.")
        coerced["txn_type"] = txn_type

    if coerced.get("amount") not in [None, ""]:
        amount = parse_human_amount(str(coerced.get("amount")))
        if amount <= 0:
            raise ValueError("Nominal belum valid. Contoh: `amount=65000`, `amount=65k`, atau `amount=1.5 juta`.")
        coerced["amount"] = amount

    if coerced.get("frequency"):
        frequency = _normalize_recurring_frequency_text(coerced.get("frequency"))
        # Validate missing frequency before continuing.
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
            # Handle day int < 1 or day int > 31.
            if day_int < 1 or day_int > 31:
                # Raise a clear error so the caller can stop this invalid flow.
                raise ValueError
        # Handle an expected failure from the guarded operation above.
        except Exception:
            raise ValueError("Tanggal recurring harus angka 1 sampai 31. Contoh: `day=5`.")
        coerced["day_of_month"] = day_int

    if not coerced.get("description") and coerced.get("name"):
        coerced["description"] = coerced.get("name")

    return coerced

# Helper for parse recurring add args.
def parse_recurring_add_args(args: list[str]) -> dict:
    """Parse /recurring_add args in key=value format, while keeping old pipe input readable."""
    raw = " ".join(args).strip()

    # Validate missing raw before continuing.
    if not raw:
        raise ValueError("Format kosong.\n\n" + RECURRING_ADD_USAGE_TEXT)

    if "=" in raw:
        # Prepare tokens from the incoming input.
        tokens = _tokenize_command_args(raw)
        key_values = _parse_key_value_tokens(tokens)
        data = _normalize_recurring_key_values(key_values)
        data = _coerce_recurring_data(data)
    # Use the fallback path when no earlier branch matched.
    else:
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) < 7:
            raise ValueError("Format recurring belum lengkap.\n\n" + RECURRING_ADD_USAGE_TEXT)

        data = _coerce_recurring_data({
            "name": parts[0],
            "txn_type": parts[1],
            "amount": parts[2],
            "category": parts[3],
            "account": parts[4],
            "frequency": parts[5],
            "day_of_month": parts[6],
            "description": parts[7] if len(parts) >= 8 else parts[0],
        })

    required = ["name", "txn_type", "amount", "category", "account", "frequency", "day_of_month"]
    missing = [field for field in required if data.get(field) in [None, ""]]
    if missing:
        # Raise a clear error so the caller can stop this invalid flow.
        raise ValueError(
            "Field recurring belum lengkap: " + ", ".join(missing) + ".\n\n" + RECURRING_ADD_USAGE_TEXT
        )

    return data


# Helper for parse recurring edit args.
def parse_recurring_edit_args(args: list[str]) -> tuple[str, dict]:
    """Parse /recurring_edit args using key=value format; old pipe input is still accepted."""
    raw = " ".join(args).strip()

    # Validate missing raw before continuing.
    if not raw:
        raise ValueError("Format kosong.\n\n" + RECURRING_EDIT_USAGE_TEXT)

    # Prepare tokens from the incoming input.
    tokens = _tokenize_command_args(raw)
    # Validate missing tokens before continuing.
    if not tokens:
        raise ValueError("Format belum valid.\n\n" + RECURRING_EDIT_USAGE_TEXT)

    rule_id = tokens[0].strip()
    # Validate missing rule id before continuing.
    if not rule_id:
        raise ValueError("Recurring rule ID wajib diisi.")

    if len(tokens) < 2:
        raise ValueError("Field edit belum diisi.\n\n" + RECURRING_EDIT_USAGE_TEXT)

    # Extract updates for validation.
    updates = _parse_key_value_tokens(tokens[1:])

    # Validate missing updates before continuing.
    if not updates:
        raise ValueError("Field edit belum diisi.\n\n" + RECURRING_EDIT_USAGE_TEXT)

    return rule_id, updates


# Helper for build recurring edit result text.
def build_recurring_edit_result_text(result: dict) -> str:
    """Build the data structure or message text for recurring edit result text."""
    before = result.get("rule_before", {}) or {}
    after = result.get("rule_after", {}) or {}
    updates = result.get("updates", {}) or {}

    lines = ["✅ Recurring rule berhasil diupdate!\n"]

    lines.append(f"Nama: {after.get('name') or before.get('name') or '-'}")
    lines.append(f"ID: {after.get('id') or before.get('id') or '-'}")

    lines.append("\nField yang berubah:")

    # Iterate through each field.
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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Read args from the original text so fallback routing keeps quoted values intact.
        command_args = _recurring_command_args_from_update(update, context, "recurring_edit")
        rule_id, updates = parse_recurring_edit_args(command_args)

        rule = await run_sheets_read("get_recurring_rule_by_id", get_recurring_rule_by_id, rule_id)
        if not rule:
            await update.message.reply_text("❌ Recurring rule tidak ditemukan.\n\nCek ID dengan command:\n/recurring")
            return
        lines = [
            "🧾 *Preview final — edit recurring*",
            "",
            f"🔖 Rule ID: `{md_code_text(rule_id)}`",
            f"📌 Nama: {md_safe(rule.get('name') or '-')}",
            "",
            "*Perubahan:*",
        ]
        for field, value in updates.items():
            lines.append(f"• {md_safe(field)}: `{md_code_text(rule.get(field, '-'))}` → `{md_code_text(value)}`")
        lines.append("\nSimpan perubahan ini atau batal?")
        await send_financial_mutation_preview(
            update,
            context,
            operation="recurring_edit",
            payload={"rule_id": rule_id, "updates": updates},
            preview_text="\n".join(lines),
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Gagal edit recurring rule.\n\n"
            f"{str(e)}\n\n"
            + RECURRING_EDIT_USAGE_TEXT
        )

# Helper for short rule id.
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
    if len(rule_id) <= 18:
        return rule_id
    return rule_id


# Helper for build recurring rules text.
def build_recurring_rules_text(rules: list[dict]) -> str:
    """Build the data structure or message text for recurring rules text."""
    # Validate missing rules before continuing.
    if not rules:
        return (
            "📭 Belum ada recurring transaction.\n\n"
            "Tambah dengan format:\n"
            "`/recurring_add name=Netflix type=expense amount=65000 category=Entertainment account=DANA frequency=monthly day=5 description=\"Langganan Netflix\"`"
        )

    lines = ["🔁 *Recurring Transaction*\n"]

    # Iterate through each i, rule.
    for i, rule in enumerate(rules, 1):
        is_active = str(rule.get("is_active", "")).strip().upper() == "TRUE"
        status_icon = "✅" if is_active else "⛔"

        txn_type = str(rule.get("type", "")).strip()
        type_icon = "-" if txn_type == "expense" else "+" if txn_type == "income" else "❓"

        lines.append(
            f"{i}. {status_icon} {type_icon} *{rule.get('name', '-')}*\n"
            f"   💰 {format_rupiah(float(rule.get('amount', 0) or 0))} | {rule.get('category', '-')}\n"
            f"   🏦 {rule.get('account', '-')}\n"
            f"   🔁 {rule.get('frequency', '-')} tanggal {rule.get('day_of_month', '-')}\n"
            f"   📅 Next run: `{rule.get('next_run_date', '-')}`\n"
            f"   🔖 `{short_rule_id(rule.get('id', ''))}`"
        )

    lines.append(
        "\nCommand:\n"
        "`/recurring_add ...` — tambah recurring\n"
        "`/recurring_run` — jalankan recurring yang sudah jatuh tempo\n"
        "`/recurring_off <rule_id>` — nonaktifkan recurring"
    )

    return "\n".join(lines)


# Helper for build recurring run text.
def build_recurring_run_text(result: dict) -> str:
    """Build the data structure or message text for recurring run text."""
    lines = [
        "🔁 *Recurring Run Result*\n",
        f"📅 Tanggal run: `{result.get('run_date')}`",
        f"📌 Rule jatuh tempo: *{result.get('count_due', 0)}*",
    ]

    success = result.get("success", [])
    failed = result.get("failed", [])

    if success:
        lines.append("\n✅ *Berhasil dibuat:*")

        # Iterate through each item.
        for item in success:
            rule = item.get("rule", {})
            lines.append(
                f"• {rule.get('name', '-')}: "
                f"{format_rupiah(float(rule.get('amount', 0) or 0))} "
                f"→ next `{item.get('next_run_date', '-')}`"
            )

    if failed:
        lines.append("\n❌ *Gagal:*")

        # Iterate through each item.
        for item in failed:
            rule = item.get("rule", {})
            lines.append(
                f"• {rule.get('name', '-')} — {item.get('message', '-')}"
            )

    # Validate missing success and not failed before continuing.
    if not success and not failed:
        lines.append("\n📭 Tidak ada recurring yang jatuh tempo.")

    return "\n".join(lines)

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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    rules = await run_sheets_read("get_recurring_rules", get_recurring_rules, active_only=False)

    await start_recurring_browser(update, context, rules)


async def recurring_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /recurring_add with guided wizard or old pipe format preview."""
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Read args from the original text so fallback routing keeps quoted values intact.
        command_args = _recurring_command_args_from_update(update, context, "recurring_add")
        # Start the wizard when the command has no inline arguments.
        if not command_args:
            start_recurring_add_flow(context)
            await send_recurring_add_step_prompt(update, context, "name", {})
            return

        raw_arg = " ".join(command_args).strip()

        if "=" in raw_arg:
            data = parse_recurring_add_args(command_args)
            data["account"] = _resolve_recurring_account(data.get("account"))
            context.user_data["pending_recurring_confirm"] = data
            context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)

            # Send the Telegram response before continuing.
            await update.message.reply_text(
                build_recurring_confirm_preview(data),
                parse_mode="Markdown",
                reply_markup=confirm_keyboard("recurring"),
            )
            return

        if "|" not in raw_arg:
            start_recurring_add_flow(context, {"name": raw_arg}, step="txn_type")
            await send_recurring_add_step_prompt(update, context, "txn_type", {"name": raw_arg})
            return

        partial = _partial_recurring_data_from_args(command_args)
        missing_step = _next_missing_recurring_step(partial)

        if missing_step and missing_step != "description":
            start_recurring_add_flow(context, partial, step=missing_step)
            # Send the Telegram response before continuing.
            await send_recurring_add_step_prompt(update, context, missing_step, partial)
            return

        if missing_step == "description":
            start_recurring_add_flow(context, partial, step="description")
            await send_recurring_add_step_prompt(update, context, "description", partial)
            return

        data = parse_recurring_add_args(command_args)
        data["account"] = _resolve_recurring_account(data.get("account"))
        context.user_data["pending_recurring_confirm"] = data
        context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_recurring_confirm_preview(data),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("recurring"),
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"❌ Gagal membuat recurring transaction.\n\n{str(e)}",
            parse_mode="Markdown",
        )


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        due_rules = await run_sheets_read("get_due_recurring_rules", get_due_recurring_rules)
        lines = [
            "🧾 *Preview final — jalankan recurring jatuh tempo*",
            "",
            f"📌 Rule jatuh tempo: *{len(due_rules)}*",
        ]
        for rule in due_rules:
            lines.append(
                f"• {md_safe(rule.get('name') or '-')} — {format_rupiah(float(rule.get('amount') or 0))} "
                f"(`{md_code_text(rule.get('id'))}`)"
            )
        lines.append("\nTidak ada transaksi dibuat sebelum Anda menekan Simpan.")
        await send_financial_mutation_preview(
            update,
            context,
            operation="recurring_run",
            payload={},
            preview_text="\n".join(lines),
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"❌ Gagal menjalankan recurring: {str(e)}"
        )


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Validate missing context.args before continuing.
    if not context.args:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Masukkan recurring rule ID.\n\n"
            "Contoh:\n"
            "`/recurring_off rec_20260610_123456_xxxxxx`",
            parse_mode="Markdown",
        )
        return

    rule_id = context.args[0].strip()
    rule = await run_sheets_read("get_recurring_rule_by_id", get_recurring_rule_by_id, rule_id)
    if not rule:
        await update.message.reply_text("❌ Recurring rule tidak ditemukan.")
        return

    await send_financial_mutation_preview(
        update,
        context,
        operation="recurring_off",
        payload={"rule_id": rule_id},
        preview_text=(
            "🧾 *Preview final — nonaktifkan recurring*\n\n"
            f"🔖 Rule ID: `{md_code_text(rule_id)}`\n"
            f"📌 Nama: {md_safe(rule.get('name') or '-')}\n"
            f"💰 Nominal: *{format_rupiah(float(rule.get('amount') or 0))}*\n\n"
            "Simpan perubahan ini atau batal?"
        ),
    )

# Helper for write transactions to csv.
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
        writer = csv.DictWriter(
            f,
            fieldnames=EXPORT_TRANSACTION_COLUMNS,
            extrasaction="ignore",
        )

        writer.writeheader()

        # Iterate through each record.
        for record in records:
            row = {}

            # Iterate through each col.
            for col in EXPORT_TRANSACTION_COLUMNS:
                row[col] = record.get(col, "")

            writer.writerow(row)


# Helper for build export caption.
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

    return (
        f"✅ *Export transaksi berhasil!*\n\n"
        f"📅 Periode: *{label}*\n"
        f"📝 Jumlah transaksi: *{count}*\n"
        f"✅ Total pemasukan: *{format_rupiah(total_income)}*\n"
        f"❌ Total pengeluaran: *{format_rupiah(total_expense)}*\n"
        f"🔄 Total transfer: *{format_rupiah(total_transfer)}*\n"
        f"📊 Net: *{format_rupiah(net)}*"
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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Extract period for validation.
    period = context.args[0] if context.args else None

    # Build export result for the response flow.
    export_result = await run_sheets_read("manual_export_read", get_transactions_for_export, period)

    if not export_result.get("success"):
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"❌ {export_result.get('message')}\n\n"
            "Contoh:\n"
            "`/download_data`\n"
            "`/download_data today`\n"
            "`/download_data week`\n"
            "`/download_data month`\n"
            "`/download_data 2026-06`",
            parse_mode="Markdown",
        )
        return

    records = export_result.get("records", [])
    filter_info = export_result.get("filter", {})

    # Validate missing records before continuing.
    if not records:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"📭 Tidak ada transaksi untuk periode *{filter_info.get('label', '-')}*.",
            parse_mode="Markdown",
        )
        return

    filename_suffix = filter_info.get("filename_suffix", business_now().strftime("%Y-%m"))
    filename = f"transactions_{filename_suffix}.csv"

    file_path = create_unique_export_temp_path()

    # Run this operation in a guarded block so failures can be handled.
    try:
        write_transactions_to_csv(records, file_path)

        # Warn before sending the sensitive finance export file.
        await update.message.reply_text(build_export_privacy_warning(), parse_mode="Markdown")

        with open(file_path, "rb") as f:
            # Send the Telegram response before continuing.
            await update.message.reply_document(
                document=InputFile(f, filename=filename),
                filename=filename,
                caption=build_export_caption(export_result),
                parse_mode="Markdown",
            )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        emit_event("manual_export_failed", error_type=type(e).__name__)
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Gagal membuat file CSV. Silakan coba lagi atau cek log operasional."
        )

    # Run cleanup that must happen after the guarded operation.
    finally:
        # Run this operation in a guarded block so failures can be handled.
        try:
            if os.path.exists(file_path):
                # Append the current value to os.
                os.remove(file_path)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass

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
    # Build export result for the response flow.
    export_result = await run_scheduled("scheduled_export_read", get_transactions_for_export, period)

    if not export_result.get("success"):
        # Send the Telegram response before continuing.
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ Auto export gagal.\n{export_result.get('message')}",
        )
        return

    records = export_result.get("records", [])
    filter_info = export_result.get("filter", {})

    # Validate missing records before continuing.
    if not records:
        # Send the Telegram response before continuing.
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "📭 Auto export: tidak ada transaksi untuk periode "
                f"{filter_info.get('label', '-')}."
            ),
        )
        return

    filename_suffix = filter_info.get(
        "filename_suffix",
        business_now().strftime("%Y-%m"),
    )
    filename = f"transactions_{filename_suffix}.csv"

    file_path = create_unique_export_temp_path()

    # Run this operation in a guarded block so failures can be handled.
    try:
        write_transactions_to_csv(records, file_path)

        with open(file_path, "rb") as f:
            # Send the Telegram response before continuing.
            await bot.send_document(
                chat_id=chat_id,
                document=InputFile(f, filename=filename),
                filename=filename,
                caption=(
                    "⏰ *Auto Export Data Finance*\n"
                    "Jadwal: 23:55 WIB\n\n"
                    # Include the same sensitivity note used by manual exports.
                    f"{build_export_caption(export_result)}\n\n"
                    f"{build_export_privacy_warning()}"
                ),
                parse_mode="Markdown",
            )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        emit_event("scheduled_export_failed", error_type=type(e).__name__)
        # Send the Telegram response before continuing.
        await bot.send_message(
            chat_id=chat_id,
            text="❌ Auto export gagal membuat file CSV. Cek log operasional.",
        )

    # Run cleanup that must happen after the guarded operation.
    finally:
        # Run this operation in a guarded block so failures can be handled.
        try:
            if os.path.exists(file_path):
                # Append the current value to os.
                os.remove(file_path)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass


GEMINI_INTENT_CONFIDENCE_EXECUTE = 0.80
GEMINI_INTENT_CONFIDENCE_CLARIFY = 0.60


