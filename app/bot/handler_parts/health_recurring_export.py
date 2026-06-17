# Split from app/bot/handlers.py for readability.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *

def health_status_icon(ok: bool) -> str:
    return "🟢" if ok else "🔴"


def health_warn_icon(ok: bool) -> str:
    return "🟢" if ok else "🟡"


def safe_health_check(label: str, check_func):
    """
    Jalankan satu health check dengan aman.
    Return:
    {
        "label": str,
        "ok": bool,
        "message": str
    }
    """
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
    spreadsheet = get_spreadsheet()

    if not spreadsheet:
        return False, "Spreadsheet tidak tersedia."

    title = getattr(spreadsheet, "title", "") or "Connected"
    return True, title


def check_sheet_readable(sheet_name: str):
    records = get_all_records(sheet_name)
    return True, f"{len(records)} row readable"

def check_wispybite():
    if not WEBHOOK_URL:
        return False, "Webhook Url kosong."

    return True, "Webhook Url tersedia"

def check_wispybite_port():
    if not APP_PORT:
        return False, "Port Webhook kosong."

    return True, "Port Webhook tersedia"

def check_gemini_config():
    if not GEMINI_API_KEY:
        return False, "GEMINI_API_KEY kosong."

    return True, "GEMINI_API_KEY tersedia"


def check_environment_config():
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
    """
    /health — cek status komponen utama bot.
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    await update.message.reply_text("⏳ Menjalankan health check...")

    sheet_names = {
        "transactions": "transactions",
        "accounts": "accounts",
        "budgets": "budgets",
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

def parse_recurring_add_args(args: list[str]) -> dict:
    """
    Format:
    /recurring_add Nama | type | amount | category | account | monthly | day | description

    Contoh:
    /recurring_add Netflix | expense | 65000 | Entertainment | DANA | monthly | 5 | Langganan Netflix
    /recurring_add Gaji | income | 8000000 | Salary | BRI | monthly | 25 | Gaji bulanan
    """
    raw = " ".join(args).strip()

    if not raw:
        raise ValueError(
            "Format kosong.\n\n"
            "Contoh:\n"
            "`/recurring_add Netflix | expense | 65000 | Entertainment | DANA | monthly | 5 | Langganan Netflix`"
        )

    parts = [p.strip() for p in raw.split("|")]

    if len(parts) < 7:
        raise ValueError(
            "Format recurring belum lengkap.\n\n"
            "Format:\n"
            "`/recurring_add Nama | type | amount | category | account | monthly | tanggal | deskripsi`\n\n"
            "Contoh:\n"
            "`/recurring_add Netflix | expense | 65000 | Entertainment | DANA | monthly | 5 | Langganan Netflix`"
        )

    name = parts[0]
    txn_type = parts[1].lower()
    amount_raw = parts[2]
    category = parts[3]
    account = parts[4]
    frequency = parts[5]
    day_of_month = parts[6]
    description = parts[7] if len(parts) >= 8 else name

    try:
        amount = float(str(amount_raw).replace(".", "").replace(",", ""))
    except Exception:
        raise ValueError("Amount harus angka. Contoh: `65000`, bukan `65rb` untuk command ini.")

    return {
        "name": name,
        "txn_type": txn_type,
        "amount": amount,
        "category": category,
        "account": account,
        "frequency": frequency,
        "day_of_month": day_of_month,
        "description": description,
    }

def parse_recurring_edit_args(args: list[str]) -> tuple[str, dict]:
    """
    Format:
    /recurring_edit <rule_id> | field=value | field=value

    Contoh:
    /recurring_edit rec_xxx | amount=75000
    /recurring_edit rec_xxx | day=10 | account=BRI
    """
    raw = " ".join(args).strip()

    if not raw:
        raise ValueError(
            "Format kosong.\n\n"
            "Contoh:\n"
            "/recurring_edit rec_xxx | amount=75000 | day=10"
        )

    parts = [p.strip() for p in raw.split("|") if p.strip()]

    if not parts:
        raise ValueError(
            "Format belum valid.\n\n"
            "Contoh:\n"
            "/recurring_edit rec_xxx | amount=75000 | day=10"
        )

    rule_id = parts[0].strip()

    if not rule_id:
        raise ValueError("Recurring rule ID wajib diisi.")

    update_parts = parts[1:]

    if not update_parts:
        raise ValueError(
            "Field edit belum diisi.\n\n"
            "Contoh:\n"
            "/recurring_edit rec_xxx | amount=75000 | day=10"
        )

    updates = {}

    for part in update_parts:
        if "=" not in part:
            raise ValueError(
                f"Format field `{part}` belum valid. Gunakan format field=value."
            )

        field, value = part.split("=", 1)
        field = field.strip()
        value = value.strip()

        if not field or not value:
            raise ValueError(
                f"Format field `{part}` belum valid. Field dan value wajib diisi."
            )

        updates[field] = value

    return rule_id, updates


def build_recurring_edit_result_text(result: dict) -> str:
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
    """
    /recurring_edit <rule_id> | field=value | field=value
    """
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
            "Contoh:\n"
            "/recurring_edit rec_xxx | amount=75000\n"
            "/recurring_edit rec_xxx | day=10 | account=BRI\n"
            "/recurring_edit rec_xxx | name=Netflix Premium | amount=75000 | day=5\n"
            "/recurring_edit rec_xxx | next_run_date=2026-06-11"
        )

def short_rule_id(rule_id: str) -> str:
    rule_id = str(rule_id or "")
    if len(rule_id) <= 18:
        return rule_id
    return rule_id


def build_recurring_rules_text(rules: list[dict]) -> str:
    if not rules:
        return (
            "📭 Belum ada recurring transaction.\n\n"
            "Tambah dengan format:\n"
            "`/recurring_add Netflix | expense | 65000 | Entertainment | DANA | monthly | 5 | Langganan Netflix`"
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
    """
    /recurring — list recurring rules
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    rules = get_recurring_rules(active_only=False)

    await update.message.reply_text(
        build_recurring_rules_text(rules),
        parse_mode="Markdown",
    )


async def recurring_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /recurring_add Nama | type | amount | category | account | monthly | day | description
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        data = parse_recurring_add_args(context.args)

        rule = add_recurring_rule(
            name=data["name"],
            txn_type=data["txn_type"],
            amount=data["amount"],
            category=data["category"],
            account=data["account"],
            frequency=data["frequency"],
            day_of_month=data["day_of_month"],
            description=data["description"],
        )

        await update.message.reply_text(
            "✅ *Recurring transaction berhasil dibuat!*\n\n"
            f"🔁 Nama: *{rule.get('name')}*\n"
            f"💰 Nominal: *{format_rupiah(float(rule.get('amount', 0) or 0))}*\n"
            f"📁 Kategori: *{rule.get('category')}*\n"
            f"🏦 Rekening: *{rule.get('account')}*\n"
            f"📅 Jadwal: setiap tanggal *{rule.get('day_of_month')}*\n"
            f"⏭️ Next run: `{rule.get('next_run_date')}`\n"
            f"🔖 ID: `{rule.get('id')}`",
            parse_mode="Markdown",
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Gagal membuat recurring transaction.\n\n{str(e)}",
            parse_mode="Markdown",
        )


async def recurring_run_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /recurring_run — jalankan recurring yang jatuh tempo secara manual
    """
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
    """
    /recurring_off <rule_id>
    """
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
    """
    Tulis records transaksi ke file CSV.
    """
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
    """
    /download_data
    /download_data today
    /download_data week
    /download_data month
    /download_data 2026-06
    """
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
    """
    Auto export transaksi untuk scheduler.

    period:
    - None      = export semua transaksi
    - "today"   = export transaksi hari ini
    - "week"    = export transaksi minggu ini
    - "month"   = export transaksi bulan ini
    - "2026-06" = export transaksi bulan tertentu
    """
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


