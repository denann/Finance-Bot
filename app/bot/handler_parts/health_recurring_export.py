"""Handlers for health checks, recurring transaction actions, and data export workflows."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *
import shlex
from app.services.resolver_service import resolve_account_name

def health_status_icon(ok: bool) -> str:
    """Helper for health status icon in the Telegram bot flow."""
    return "🟢" if ok else "🔴"


def health_warn_icon(ok: bool) -> str:
    """Helper for health warn icon in the Telegram bot flow."""
    return "🟢" if ok else "🟡"


def safe_health_check(label: str, check_func):
    """Helper for safe health check in the Telegram bot flow."""
    try:
        result = check_func()

        if isinstance(result, tuple):
            ok, message = result
        else:
            ok = bool(result)
            message = "OK" if ok else "Failed"

        return {
            "label": label,
            "ok": bool(ok),
            "message": str(message),
        }

    except Exception as e:
        return {
            "label": label,
            "ok": False,
            "message": str(e),
        }


def check_google_sheets_connection():
    """Helper for check google sheets connection in the Telegram bot flow."""
    spreadsheet = get_spreadsheet()

    if not spreadsheet:
        return False, "Spreadsheet tidak tersedia."

    title = getattr(spreadsheet, "title", "") or "Connected"
    return True, title


def check_sheet_readable(sheet_name: str):
    """Helper for check sheet readable in the Telegram bot flow."""
    records = get_all_records(sheet_name)
    return True, f"{len(records)} row readable"

def check_wispybite():
    """Helper for check wispybite in the Telegram bot flow."""
    if not WEBHOOK_URL:
        return False, "Webhook Url kosong."

    return True, "Webhook Url tersedia"

def check_wispybite_port():
    """Helper for check wispybite port in the Telegram bot flow."""
    if not APP_PORT:
        return False, "Port Webhook kosong."

    return True, "Port Webhook tersedia"

def check_gemini_config():
    """Helper for check gemini config in the Telegram bot flow."""
    if not GEMINI_API_KEY:
        return False, "GEMINI_API_KEY kosong."

    return True, "GEMINI_API_KEY tersedia"


def check_environment_config():
    """Helper for check environment config in the Telegram bot flow."""
    required_envs = [
        "TELEGRAM_BOT_TOKEN",
        "ALLOWED_USER_ID",
        "GOOGLE_SHEET_ID",
        "GEMINI_API_KEY",
    ]

    missing = []

    for env_name in required_envs:
        if not os.getenv(env_name):
            missing.append(env_name)

    if missing:
        return False, "Missing: " + ", ".join(missing)

    return True, "Required env tersedia"


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

    for result in results:
        icon = health_status_icon(result.get("ok"))
        label = result.get("label", "-")
        message = result.get("message", "-")

        lines.append(f"{icon} *{label}*")
        lines.append(f"   `{message}`")

    if failed == 0:
        lines.append("\n🚀 Semua komponen utama terlihat aman.")
    else:
        lines.append("\n⚠️ Ada komponen yang perlu dicek.")

    return "\n".join(lines)

async def health_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Telegram request for health."""
    if not is_authorized(update):
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

    await update.message.reply_text(
        build_health_report_text(results),
        parse_mode="Markdown",
    )

RECURRING_ADD_FLOW_KEY = "pending_recurring_add_flow"
RECURRING_ADD_PROMPT_MESSAGE_KEY = "pending_recurring_add_prompt_message_id"
RECURRING_ADD_SKIP_WORDS = {"skip", "lewati", "kosong", "-", "tidak", "tidak ada", "ga ada", "gak ada", "nggak ada"}
RECURRING_ADD_STEPS = ["name", "txn_type", "amount", "category", "account", "frequency", "day_of_month", "description"]
RECURRING_ADD_OPTIONAL_STEPS = {"description"}


def _recurring_is_skip(text: str) -> bool:
    """Check whether the user wants to skip an optional recurring field."""
    return str(text or "").strip().lower() in RECURRING_ADD_SKIP_WORDS


def recurring_add_step_keyboard(step: str) -> InlineKeyboardMarkup:
    """Build a per-step keyboard for recurring add wizard."""
    rows = []
    if step in RECURRING_ADD_OPTIONAL_STEPS:
        rows.append([InlineKeyboardButton("⏭️ Lewati", callback_data="recurring_add:skip")])
    rows.append([InlineKeyboardButton("🚫 Batal", callback_data="cancel:recurring_add")])
    return InlineKeyboardMarkup(rows)


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


async def clear_recurring_add_step_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the active recurring wizard step keyboard after user answers."""
    chat = getattr(update, "effective_chat", None)
    chat_id = getattr(chat, "id", None) or getattr(getattr(update, "message", None), "chat_id", None)
    await clear_tracked_inline_keyboard(context, chat_id, RECURRING_ADD_PROMPT_MESSAGE_KEY)


def start_recurring_add_flow(context: ContextTypes.DEFAULT_TYPE, initial_data: dict | None = None, step: str = "name") -> None:
    """Start recurring add wizard with optional prefilled fields."""
    context.user_data.pop("pending_recurring_confirm", None)
    context.user_data[RECURRING_ADD_FLOW_KEY] = {
        "step": step or "name",
        "data": dict(initial_data or {}),
    }


def _normalize_recurring_txn_type(value: str) -> str | None:
    """Normalize Indonesian and English recurring type aliases."""
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


def _resolve_recurring_account(value: str) -> str:
    """Use account resolver when possible, but keep typed value as fallback."""
    raw = str(value or "").strip()
    try:
        resolved = resolve_account_name(raw)
        if resolved.get("status") == "exact":
            return str(resolved.get("account_name") or raw).strip()
    except Exception:
        pass
    return raw


def _next_missing_recurring_step(data: dict) -> str | None:
    """Return the first recurring wizard field that is still missing."""
    for step in RECURRING_ADD_STEPS:
        if step == "description":
            continue
        if data.get(step) in [None, ""]:
            return step
    return "description" if "description" not in data else None


def build_recurring_confirm_preview(data: dict) -> str:
    """Build recurring add preview before saving."""
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


def build_recurring_saved_text(rule: dict) -> str:
    """Build recurring saved confirmation text."""
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


def _partial_recurring_data_from_args(args: list[str]) -> dict:
    """Read partial /recurring_add args without forcing the old full pipe format."""
    raw = " ".join(args or []).strip()
    if not raw:
        return {}
    if "|" not in raw:
        return {"name": raw}

    parts = [p.strip() for p in raw.split("|")]
    keys = ["name", "txn_type", "amount", "category", "account", "frequency", "day_of_month", "description"]
    data = {}
    for key, value in zip(keys, parts):
        if not value:
            continue
        if key == "txn_type":
            normalized = _normalize_recurring_txn_type(value)
            if normalized:
                data[key] = normalized
        elif key == "amount":
            amount = parse_human_amount(value)
            if amount > 0:
                data[key] = amount
        elif key == "frequency":
            normalized = _normalize_recurring_frequency_text(value)
            if normalized:
                data[key] = normalized
        elif key == "day_of_month":
            data[key] = value
        elif key == "account":
            data[key] = _resolve_recurring_account(value)
        else:
            data[key] = value
    return data


async def _finish_recurring_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> bool:
    """Move recurring wizard to final preview."""
    if not data.get("description"):
        data["description"] = data.get("name") or ""
    context.user_data["pending_recurring_confirm"] = dict(data)
    context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)
    context.user_data.pop(RECURRING_ADD_PROMPT_MESSAGE_KEY, None)
    await update.message.reply_text(
        build_recurring_confirm_preview(data),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("recurring"),
    )
    return True


async def handle_pending_recurring_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Handle text replies for recurring add wizard."""
    flow = context.user_data.get(RECURRING_ADD_FLOW_KEY)
    if not flow:
        return False

    text = str(user_text or "").strip()
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
        if not text:
            await send_recurring_add_step_prompt(update, context, "name", data)
            return True
        data["name"] = text
        flow["step"] = "txn_type"
        await send_recurring_add_step_prompt(update, context, "txn_type", data)
        return True

    if step == "txn_type":
        txn_type = _normalize_recurring_txn_type(text)
        if not txn_type:
            await update.message.reply_text("❌ Tipe belum valid. Isi `expense` atau `income`.", parse_mode="Markdown")
            await send_recurring_add_step_prompt(update, context, "txn_type", data)
            return True
        data["txn_type"] = txn_type
        flow["step"] = "amount"
        await send_recurring_add_step_prompt(update, context, "amount", data)
        return True

    if step == "amount":
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
        if not text:
            await send_recurring_add_step_prompt(update, context, "category", data)
            return True
        data["category"] = text
        flow["step"] = "account"
        await send_recurring_add_step_prompt(update, context, "account", data)
        return True

    if step == "account":
        if not text:
            await send_recurring_add_step_prompt(update, context, "account", data)
            return True
        data["account"] = _resolve_recurring_account(text)
        flow["step"] = "frequency"
        await send_recurring_add_step_prompt(update, context, "frequency", data)
        return True

    if step == "frequency":
        frequency = _normalize_recurring_frequency_text(text)
        if not frequency:
            await update.message.reply_text("❌ Frekuensi belum valid. Saat ini gunakan `monthly` atau `bulanan`.", parse_mode="Markdown")
            await send_recurring_add_step_prompt(update, context, "frequency", data)
            return True
        data["frequency"] = frequency
        flow["step"] = "day_of_month"
        await send_recurring_add_step_prompt(update, context, "day_of_month", data)
        return True

    if step == "day_of_month":
        try:
            day_int = int(re.sub(r"[^0-9]", "", text))
            if day_int < 1 or day_int > 31:
                raise ValueError
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


async def handle_recurring_add_skip_callback(query, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle inline Lewati button for recurring wizard."""
    flow = context.user_data.get(RECURRING_ADD_FLOW_KEY)
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


def _parse_key_value_tokens(tokens: list[str]) -> dict:
    """Parse key=value tokens and allow unquoted continuation words until the next key=value."""
    updates = {}
    i = 0
    while i < len(tokens):
        token = str(tokens[i] or "").strip()
        if not token:
            i += 1
            continue
        if "=" not in token:
            raise ValueError(f"Format `{token}` belum valid. Gunakan `field=value`.")

        field, value = token.split("=", 1)
        field = field.strip().lower()
        value_parts = [value.strip()] if value.strip() else []
        i += 1

        while i < len(tokens) and "=" not in str(tokens[i] or ""):
            continuation = str(tokens[i] or "").strip()
            if continuation:
                value_parts.append(continuation)
            i += 1

        value = " ".join(value_parts).strip()
        if not field or not value:
            raise ValueError(f"Format `{token}` belum valid. Field dan value wajib diisi.")
        updates[field] = value

    return updates


def _tokenize_command_args(raw: str) -> list[str]:
    """Tokenize command args while preserving quoted values."""
    try:
        return shlex.split(str(raw or "").replace("|", " "))
    except Exception:
        return str(raw or "").replace("|", " ").split()


def _normalize_recurring_key_values(values: dict) -> dict:
    """Normalize recurring key=value fields into recurring service keys."""
    aliases = {
        "type": "txn_type",
        "txn_type": "txn_type",
        "jenis": "txn_type",
        "nominal": "amount",
        "harga": "amount",
        "category": "category",
        "kategori": "category",
        "account": "account",
        "rekening": "account",
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
    normalized = {}
    for field, value in (values or {}).items():
        key = aliases.get(str(field or "").strip().lower())
        if key:
            normalized[key] = value
    return normalized


def _coerce_recurring_data(data: dict) -> dict:
    """Validate and coerce recurring command data."""
    coerced = dict(data or {})
    if coerced.get("txn_type"):
        txn_type = _normalize_recurring_txn_type(coerced.get("txn_type"))
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
        if not frequency:
            raise ValueError("Frekuensi belum valid. Saat ini gunakan `frequency=monthly` atau `frequency=bulanan`.")
        coerced["frequency"] = frequency

    if coerced.get("account"):
        coerced["account"] = _resolve_recurring_account(coerced.get("account"))

    if coerced.get("day_of_month") not in [None, ""]:
        day_raw = str(coerced.get("day_of_month"))
        try:
            day_int = int(re.sub(r"[^0-9]", "", day_raw))
            if day_int < 1 or day_int > 31:
                raise ValueError
        except Exception:
            raise ValueError("Tanggal recurring harus angka 1 sampai 31. Contoh: `day=5`.")
        coerced["day_of_month"] = day_int

    if not coerced.get("description") and coerced.get("name"):
        coerced["description"] = coerced.get("name")

    return coerced

def parse_recurring_add_args(args: list[str]) -> dict:
    """Parse /recurring_add args in key=value format, while keeping old pipe input readable."""
    raw = " ".join(args).strip()

    if not raw:
        raise ValueError("Format kosong.\n\n" + RECURRING_ADD_USAGE_TEXT)

    if "=" in raw:
        tokens = _tokenize_command_args(raw)
        key_values = _parse_key_value_tokens(tokens)
        data = _normalize_recurring_key_values(key_values)
        data = _coerce_recurring_data(data)
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
        raise ValueError(
            "Field recurring belum lengkap: " + ", ".join(missing) + ".\n\n" + RECURRING_ADD_USAGE_TEXT
        )

    return data


def parse_recurring_edit_args(args: list[str]) -> tuple[str, dict]:
    """Parse /recurring_edit args using key=value format; old pipe input is still accepted."""
    raw = " ".join(args).strip()

    if not raw:
        raise ValueError("Format kosong.\n\n" + RECURRING_EDIT_USAGE_TEXT)

    tokens = _tokenize_command_args(raw)
    if not tokens:
        raise ValueError("Format belum valid.\n\n" + RECURRING_EDIT_USAGE_TEXT)

    rule_id = tokens[0].strip()
    if not rule_id:
        raise ValueError("Recurring rule ID wajib diisi.")

    if len(tokens) < 2:
        raise ValueError("Field edit belum diisi.\n\n" + RECURRING_EDIT_USAGE_TEXT)

    updates = _parse_key_value_tokens(tokens[1:])

    if not updates:
        raise ValueError("Field edit belum diisi.\n\n" + RECURRING_EDIT_USAGE_TEXT)

    return rule_id, updates


def build_recurring_edit_result_text(result: dict) -> str:
    """Build the data structure or message text for recurring edit result text."""
    before = result.get("rule_before", {}) or {}
    after = result.get("rule_after", {}) or {}
    updates = result.get("updates", {}) or {}

    lines = ["✅ Recurring rule berhasil diupdate!\n"]

    lines.append(f"Nama: {after.get('name') or before.get('name') or '-'}")
    lines.append(f"ID: {after.get('id') or before.get('id') or '-'}")

    lines.append("\nField yang berubah:")

    for field in updates:
        if field == "updated_at":
            continue

        old_value = before.get(field, "-")
        new_value = after.get(field, updates.get(field, "-"))

        lines.append(f"- {field}: {old_value} → {new_value}")

    lines.append(f"\nNext run: {after.get('next_run_date', '-')}")
    lines.append(f"Status: {after.get('is_active', '-')}")

    return "\n".join(lines)

async def recurring_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Telegram request for recurring edit."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        rule_id, updates = parse_recurring_edit_args(context.args)

        result = edit_recurring_rule(rule_id, updates)

        if not result.get("success"):
            await update.message.reply_text(
                f"❌ {result.get('message')}\n\n"
                "Cek ID dengan command:\n"
                "/recurring"
            )
            return

        await update.message.reply_text(
            build_recurring_edit_result_text(result)
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Gagal edit recurring rule.\n\n"
            f"{str(e)}\n\n"
            + RECURRING_EDIT_USAGE_TEXT
        )

def short_rule_id(rule_id: str) -> str:
    """Helper for short rule id in the Telegram bot flow."""
    rule_id = str(rule_id or "")
    if len(rule_id) <= 18:
        return rule_id
    return rule_id


def build_recurring_rules_text(rules: list[dict]) -> str:
    """Build the data structure or message text for recurring rules text."""
    if not rules:
        return (
            "📭 Belum ada recurring transaction.\n\n"
            "Tambah dengan format:\n"
            "`/recurring_add name=Netflix type=expense amount=65000 category=Entertainment account=DANA frequency=monthly day=5 description=\"Langganan Netflix\"`"
        )

    lines = ["🔁 *Recurring Transaction*\n"]

    for i, rule in enumerate(rules, 1):
        is_active = str(rule.get("is_active", "")).strip().upper() == "TRUE"
        status_icon = "✅" if is_active else "⛔"

        txn_type = str(rule.get("type", "")).strip()
        type_icon = "❌" if txn_type == "expense" else "✅" if txn_type == "income" else "❓"

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

        for item in success:
            rule = item.get("rule", {})
            lines.append(
                f"• {rule.get('name', '-')}: "
                f"{format_rupiah(float(rule.get('amount', 0) or 0))} "
                f"→ next `{item.get('next_run_date', '-')}`"
            )

    if failed:
        lines.append("\n❌ *Gagal:*")

        for item in failed:
            rule = item.get("rule", {})
            lines.append(
                f"• {rule.get('name', '-')} — {item.get('message', '-')}"
            )

    if not success and not failed:
        lines.append("\n📭 Tidak ada recurring yang jatuh tempo.")

    return "\n".join(lines)

async def recurring_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Telegram request for recurring."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    rules = get_recurring_rules(active_only=False)

    await update.message.reply_text(
        build_recurring_rules_text(rules),
        parse_mode="Markdown",
    )


async def recurring_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /recurring_add with guided wizard or old pipe format preview."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        if not context.args:
            start_recurring_add_flow(context)
            await send_recurring_add_step_prompt(update, context, "name", {})
            return

        raw_arg = " ".join(context.args).strip()

        if "=" in raw_arg:
            data = parse_recurring_add_args(context.args)
            data["account"] = _resolve_recurring_account(data.get("account"))
            context.user_data["pending_recurring_confirm"] = data
            context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)

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

        partial = _partial_recurring_data_from_args(context.args)
        missing_step = _next_missing_recurring_step(partial)

        if missing_step and missing_step != "description":
            start_recurring_add_flow(context, partial, step=missing_step)
            await send_recurring_add_step_prompt(update, context, missing_step, partial)
            return

        if missing_step == "description":
            start_recurring_add_flow(context, partial, step="description")
            await send_recurring_add_step_prompt(update, context, "description", partial)
            return

        data = parse_recurring_add_args(context.args)
        data["account"] = _resolve_recurring_account(data.get("account"))
        context.user_data["pending_recurring_confirm"] = data
        context.user_data.pop(RECURRING_ADD_FLOW_KEY, None)

        await update.message.reply_text(
            build_recurring_confirm_preview(data),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("recurring"),
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Gagal membuat recurring transaction.\n\n{str(e)}",
            parse_mode="Markdown",
        )


async def recurring_run_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Telegram request for recurring run."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        result = process_due_recurring_rules()

        await update.message.reply_text(
            build_recurring_run_text(result),
            parse_mode="Markdown",
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Gagal menjalankan recurring: {str(e)}"
        )


async def recurring_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Telegram request for recurring off."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Masukkan recurring rule ID.\n\n"
            "Contoh:\n"
            "`/recurring_off rec_20260610_123456_xxxxxx`",
            parse_mode="Markdown",
        )
        return

    rule_id = context.args[0].strip()

    success = disable_recurring_rule(rule_id)

    if not success:
        await update.message.reply_text(
            "❌ Recurring rule tidak ditemukan."
        )
        return

    await update.message.reply_text(
        f"✅ Recurring rule berhasil dinonaktifkan:\n`{rule_id}`",
        parse_mode="Markdown",
    )

def write_transactions_to_csv(records: list[dict], file_path: str):
    """Helper for write transactions to csv in the Telegram bot flow."""
    with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=EXPORT_TRANSACTION_COLUMNS,
            extrasaction="ignore",
        )

        writer.writeheader()

        for record in records:
            row = {}

            for col in EXPORT_TRANSACTION_COLUMNS:
                row[col] = record.get(col, "")

            writer.writerow(row)


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

async def export_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Telegram request for export."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    period = context.args[0] if context.args else None

    export_result = get_transactions_for_export(period)

    if not export_result.get("success"):
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

    if not records:
        await update.message.reply_text(
            f"📭 Tidak ada transaksi untuk periode *{filter_info.get('label', '-')}*.",
            parse_mode="Markdown",
        )
        return

    filename_suffix = filter_info.get("filename_suffix", datetime.now().strftime("%Y-%m"))
    filename = f"transactions_{filename_suffix}.csv"

    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, filename)

    try:
        write_transactions_to_csv(records, file_path)

        with open(file_path, "rb") as f:
            await update.message.reply_document(
                document=InputFile(f, filename=filename),
                filename=filename,
                caption=build_export_caption(export_result),
                parse_mode="Markdown",
            )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Gagal membuat file CSV: {str(e)}"
        )

    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

async def scheduled_export_transactions(bot, chat_id: int, period=None):
    """Helper for scheduled export transactions in the Telegram bot flow."""
    export_result = get_transactions_for_export(period)

    if not export_result.get("success"):
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ Auto export gagal.\n{export_result.get('message')}",
        )
        return

    records = export_result.get("records", [])
    filter_info = export_result.get("filter", {})

    if not records:
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
        datetime.now().strftime("%Y-%m"),
    )
    filename = f"transactions_{filename_suffix}.csv"

    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, filename)

    try:
        write_transactions_to_csv(records, file_path)

        with open(file_path, "rb") as f:
            await bot.send_document(
                chat_id=chat_id,
                document=InputFile(f, filename=filename),
                filename=filename,
                caption=(
                    "⏰ *Auto Export Data Finance*\n"
                    "Jadwal: 23:55 WIB\n\n"
                    f"{build_export_caption(export_result)}"
                ),
                parse_mode="Markdown",
            )

    except Exception as e:
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ Auto export gagal membuat file CSV: {str(e)}",
        )

    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


GEMINI_INTENT_CONFIDENCE_EXECUTE = 0.80
GEMINI_INTENT_CONFIDENCE_CLARIFY = 0.60


