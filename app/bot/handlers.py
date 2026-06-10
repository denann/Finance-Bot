import re
from datetime import datetime
from difflib import SequenceMatcher
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
import shlex
import os
import google.generativeai as genai
from app.config import (
    ALLOWED_USER_ID,
    SHEET_CATEGORIES,
    GEMINI_API_KEY,
    SHEET_TRANSACTIONS,
    SHEET_ACCOUNTS,
    SHEET_BUDGETS,
    SHEET_DEBTS,
    SHEET_DEBT_PAYMENTS,
    WEBHOOK_URL,
    APP_PORT,
)

from app.services.net_worth_service import (
    add_asset,
    add_liability,
    get_assets,
    get_liabilities,
    update_asset,
    update_liability,
    deactivate_asset,
    deactivate_liability,
    calculate_net_worth,
    create_net_worth_snapshot,
    get_net_worth_snapshots,
)

from app.bot.keyboards import account_keyboard, confirm_keyboard
from app.nlp.regex_parser import parse_with_regex, parse_debt_input
from app.nlp.gemini_parser import parse_with_pending_fallback
from app.sheets.client import get_all_records, get_spreadsheet
from app.services.transaction_service import (
    save_transaction,
    save_transactions_batch,
    get_all_accounts,
    get_recent_transactions,
    preview_delete_transactions_by_refs,
    delete_transactions_by_refs,
    preview_edit_transaction_by_ref,
    edit_transaction_by_ref,
    get_transactions_for_export,
    EXPORT_TRANSACTION_COLUMNS,
)

from app.nlp.gemini_intent_router import (
    should_try_gemini_intent_router,
    route_intent_with_gemini,
)

from app.services.budget_service import (
    set_budget,
    get_budget_summary,
    check_budget_after_transaction,
    normalize_month,
    format_month_label,
    get_budget_months,
)
from app.services.report_service import (
    get_daily_report,
    get_weekly_report,
    get_monthly_report,
    search_transactions,
)

from app.services.debt_service import (
    add_debt,
    add_payment,
    get_debt_summary,
    get_debt_by_person,
)
import csv
import os
import tempfile
from app.services.recurring_service import (
    add_recurring_rule,
    get_recurring_rules,
    disable_recurring_rule,
    process_due_recurring_rules,
    edit_recurring_rule,
)


# ── Helper ────────────────────────────────────────────────────────────────────

def parse_pipe_add_args(args: list[str], item_type: str) -> dict:
    """
    Format:
    /asset_add Nama | value | category | description
    /liability_add Nama | balance | category | description
    """
    raw = " ".join(args).strip()

    if not raw:
        raise ValueError(
            f"Format kosong.\n\n"
            f"Contoh:\n"
            f"`/{item_type}_add Laptop | 8000000 | Electronics | Laptop kerja`"
        )

    parts = [p.strip() for p in raw.split("|")]

    if len(parts) < 2:
        raise ValueError(
            f"Format belum lengkap.\n\n"
            f"Format:\n"
            f"`/{item_type}_add Nama | nominal | kategori | deskripsi`"
        )

    name = parts[0]
    amount_raw = parts[1]
    category = parts[2] if len(parts) >= 3 else (
        "Other Asset" if item_type == "asset" else "Other Liability"
    )
    description = parts[3] if len(parts) >= 4 else ""

    try:
        amount = float(str(amount_raw).replace(".", "").replace(",", ""))
    except Exception:
        raise ValueError("Nominal harus angka. Contoh: `8000000`.")

    return {
        "name": name,
        "amount": amount,
        "category": category,
        "description": description,
    }


def parse_pipe_update_args(args: list[str], command_name: str) -> tuple[str, dict]:
    """
    Format:
    /asset_update asset_xxx | value=9000000 | category=Electronics
    /liability_update liab_xxx | balance=1000000
    """
    raw = " ".join(args).strip()

    if not raw:
        raise ValueError(
            f"Format kosong.\n\n"
            f"Contoh:\n"
            f"`/{command_name} id_xxx | value=9000000`"
        )

    parts = [p.strip() for p in raw.split("|") if p.strip()]

    if len(parts) < 2:
        raise ValueError(
            f"Format belum lengkap.\n\n"
            f"Contoh:\n"
            f"`/{command_name} id_xxx | value=9000000`"
        )

    record_id = parts[0]
    update_parts = parts[1:]

    updates = {}

    for part in update_parts:
        if "=" not in part:
            raise ValueError(f"Format `{part}` salah. Gunakan field=value.")

        field, value = part.split("=", 1)
        field = field.strip()
        value = value.strip()

        if not field or not value:
            raise ValueError(f"Format `{part}` salah. Field dan value wajib diisi.")

        updates[field] = value

    return record_id, updates


def short_networth_id(record_id: str) -> str:
    record_id = str(record_id or "")
    if len(record_id) <= 18:
        return record_id
    return record_id[:18] + "..."


def build_networth_text(summary: dict) -> str:
    total_accounts = summary.get("total_accounts", 0)
    total_assets = summary.get("total_assets", 0)
    total_liabilities = summary.get("total_liabilities", 0)
    net_worth = summary.get("net_worth", 0)

    accounts = summary.get("accounts", [])
    assets = summary.get("assets", [])
    liabilities = summary.get("liabilities", [])

    lines = ["💎 *Net Worth Tracker*\n"]

    lines.append(f"💰 Saldo rekening : *{format_rupiah(total_accounts)}*")
    lines.append(f"📦 Total aset     : *{format_rupiah(total_assets)}*")
    lines.append(f"💳 Liabilitas     : *{format_rupiah(total_liabilities)}*")
    lines.append(f"🏁 *Net Worth     : {format_rupiah(net_worth)}*\n")

    if accounts:
        lines.append("*Rekening:*")
        for acc in accounts:
            name = acc.get("account_name", "-")
            balance = float(acc.get("balance", 0) or 0)
            lines.append(f"• {name}: {format_rupiah(balance)}")

    if assets:
        lines.append("\n*Aset aktif:*")
        for asset in assets:
            lines.append(
                f"• {asset.get('name', '-')} "
                f"({asset.get('category', '-')}) — "
                f"{format_rupiah(float(asset.get('current_value', 0) or 0))}"
            )

    if liabilities:
        lines.append("\n*Liabilitas aktif:*")
        for liability in liabilities:
            lines.append(
                f"• {liability.get('name', '-')} "
                f"({liability.get('category', '-')}) — "
                f"{format_rupiah(float(liability.get('current_balance', 0) or 0))}"
            )

    lines.append(
        "\nCommand:\n"
        "`/asset_add Nama | nominal | kategori | deskripsi`\n"
        "`/asset_update asset_id | value=nominal`\n"
        "`/asset_off asset_id`\n"
        "`/liability_add Nama | nominal | kategori | deskripsi`\n"
        "`/liability_update liab_id | balance=nominal`\n"
        "`/liability_off liab_id`\n"
        "`/networth_snapshot`"
    )

    return "\n".join(lines)


def build_assets_text(assets: list[dict]) -> str:
    if not assets:
        return (
            "📭 Belum ada aset aktif.\n\n"
            "Tambah aset:\n"
            "`/asset_add Laptop | 8000000 | Electronics | Laptop kerja`"
        )

    lines = ["📦 *Daftar Aset Aktif*\n"]

    total = 0

    for i, asset in enumerate(assets, 1):
        value = float(asset.get("current_value", 0) or 0)
        total += value

        lines.append(
            f"{i}. *{asset.get('name', '-')}*\n"
            f"   💰 {format_rupiah(value)} | {asset.get('category', '-')}\n"
            f"   📝 {asset.get('description', '-') or '-'}\n"
            f"   🔖 `{asset.get('id', '-')}`"
        )

    lines.append(f"\n📦 Total aset aktif: *{format_rupiah(total)}*")

    return "\n".join(lines)


def build_liabilities_text(liabilities: list[dict]) -> str:
    if not liabilities:
        return (
            "📭 Belum ada liabilitas aktif.\n\n"
            "Tambah liabilitas:\n"
            "`/liability_add Paylater | 1200000 | Paylater | Cicilan aktif`"
        )

    lines = ["💳 *Daftar Liabilitas Aktif*\n"]

    total = 0

    for i, liability in enumerate(liabilities, 1):
        balance = float(liability.get("current_balance", 0) or 0)
        total += balance

        lines.append(
            f"{i}. *{liability.get('name', '-')}*\n"
            f"   💰 {format_rupiah(balance)} | {liability.get('category', '-')}\n"
            f"   📝 {liability.get('description', '-') or '-'}\n"
            f"   🔖 `{liability.get('id', '-')}`"
        )

    lines.append(f"\n💳 Total liabilitas aktif: *{format_rupiah(total)}*")

    return "\n".join(lines)


def build_update_result_text(result: dict, label: str) -> str:
    before = result.get("before", {}) or {}
    after = result.get("after", {}) or {}
    updates = result.get("updates", {}) or {}

    lines = [f"✅ {label} berhasil diupdate!\n"]

    lines.append(f"Nama: {after.get('name') or before.get('name') or '-'}")
    lines.append(f"ID: {after.get('id') or before.get('id') or '-'}")

    lines.append("\nField yang berubah:")

    for field in updates:
        if field == "updated_at":
            continue

        old_value = before.get(field, "-")
        new_value = after.get(field, updates.get(field, "-"))

        lines.append(f"- {field}: {old_value} → {new_value}")

    return "\n".join(lines)


def build_snapshots_text(snapshots: list[dict]) -> str:
    if not snapshots:
        return "📭 Belum ada snapshot net worth."

    lines = ["📈 *Riwayat Net Worth Snapshot*\n"]

    for snap in snapshots:
        lines.append(
            f"• `{snap.get('snapshot_date', '-')}` — "
            f"*{format_rupiah(float(snap.get('net_worth', 0) or 0))}*\n"
            f"  Rekening: {format_rupiah(float(snap.get('total_accounts', 0) or 0))} | "
            f"Aset: {format_rupiah(float(snap.get('total_assets', 0) or 0))} | "
            f"Liabilitas: {format_rupiah(float(snap.get('total_liabilities', 0) or 0))}"
        )

    return "\n".join(lines)

async def networth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /networth — lihat net worth summary
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    summary = calculate_net_worth()

    await update.message.reply_text(
        build_networth_text(summary),
        parse_mode="Markdown",
    )


async def assets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /assets — lihat daftar aset aktif
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    assets = get_assets(active_only=True)

    await update.message.reply_text(
        build_assets_text(assets),
        parse_mode="Markdown",
    )


async def liabilities_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /liabilities — lihat daftar liabilitas aktif
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    liabilities = get_liabilities(active_only=True)

    await update.message.reply_text(
        build_liabilities_text(liabilities),
        parse_mode="Markdown",
    )


async def asset_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /asset_add Nama | nominal | kategori | deskripsi
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        data = parse_pipe_add_args(context.args, "asset")

        asset = add_asset(
            name=data["name"],
            current_value=data["amount"],
            category=data["category"],
            description=data["description"],
        )

        await update.message.reply_text(
            "✅ *Aset berhasil ditambahkan!*\n\n"
            f"📦 Nama: *{asset.get('name')}*\n"
            f"💰 Nilai: *{format_rupiah(float(asset.get('current_value', 0) or 0))}*\n"
            f"📁 Kategori: *{asset.get('category')}*\n"
            f"📝 Deskripsi: {asset.get('description') or '-'}\n"
            f"🔖 ID: `{asset.get('id')}`",
            parse_mode="Markdown",
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Gagal tambah aset.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/asset_add Laptop | 8000000 | Electronics | Laptop kerja`",
            parse_mode="Markdown",
        )


async def liability_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /liability_add Nama | nominal | kategori | deskripsi
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        data = parse_pipe_add_args(context.args, "liability")

        liability = add_liability(
            name=data["name"],
            current_balance=data["amount"],
            category=data["category"],
            description=data["description"],
        )

        await update.message.reply_text(
            "✅ *Liabilitas berhasil ditambahkan!*\n\n"
            f"💳 Nama: *{liability.get('name')}*\n"
            f"💰 Nominal: *{format_rupiah(float(liability.get('current_balance', 0) or 0))}*\n"
            f"📁 Kategori: *{liability.get('category')}*\n"
            f"📝 Deskripsi: {liability.get('description') or '-'}\n"
            f"🔖 ID: `{liability.get('id')}`",
            parse_mode="Markdown",
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Gagal tambah liabilitas.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/liability_add Paylater | 1200000 | Paylater | Cicilan aktif`",
            parse_mode="Markdown",
        )


async def asset_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /asset_update asset_id | value=9000000 | category=Electronics
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        asset_id, updates = parse_pipe_update_args(context.args, "asset_update")
        result = update_asset(asset_id, updates)

        if not result.get("success"):
            await update.message.reply_text(
                f"❌ {result.get('message')}\n\n"
                "Cek ID dengan command:\n"
                "`/assets`",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            build_update_result_text(result, "Aset")
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Gagal update aset.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/asset_update asset_xxx | value=9000000`\n"
            "`/asset_update asset_xxx | name=Laptop Baru | category=Electronics`",
            parse_mode="Markdown",
        )


async def liability_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /liability_update liab_id | balance=1000000
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        liability_id, updates = parse_pipe_update_args(context.args, "liability_update")
        result = update_liability(liability_id, updates)

        if not result.get("success"):
            await update.message.reply_text(
                f"❌ {result.get('message')}\n\n"
                "Cek ID dengan command:\n"
                "`/liabilities`",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            build_update_result_text(result, "Liabilitas")
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Gagal update liabilitas.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/liability_update liab_xxx | balance=1000000`\n"
            "`/liability_update liab_xxx | name=Paylater Shopee | balance=500000`",
            parse_mode="Markdown",
        )


async def asset_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /asset_off asset_id
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Masukkan asset ID.\n\n"
            "Contoh:\n"
            "`/asset_off asset_xxx`",
            parse_mode="Markdown",
        )
        return

    asset_id = context.args[0].strip()
    success = deactivate_asset(asset_id)

    if not success:
        await update.message.reply_text("❌ Asset tidak ditemukan.")
        return

    await update.message.reply_text(
        f"✅ Asset berhasil dinonaktifkan:\n`{asset_id}`",
        parse_mode="Markdown",
    )


async def liability_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /liability_off liab_id
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Masukkan liability ID.\n\n"
            "Contoh:\n"
            "`/liability_off liab_xxx`",
            parse_mode="Markdown",
        )
        return

    liability_id = context.args[0].strip()
    success = deactivate_liability(liability_id)

    if not success:
        await update.message.reply_text("❌ Liability tidak ditemukan.")
        return

    await update.message.reply_text(
        f"✅ Liability berhasil dinonaktifkan:\n`{liability_id}`",
        parse_mode="Markdown",
    )


async def networth_snapshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /networth_snapshot — simpan snapshot net worth hari ini
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        snapshot = create_net_worth_snapshot()

        await update.message.reply_text(
            "✅ *Snapshot Net Worth berhasil disimpan!*\n\n"
            f"📅 Tanggal: `{snapshot.get('snapshot_date')}`\n"
            f"💰 Rekening: *{format_rupiah(float(snapshot.get('total_accounts', 0) or 0))}*\n"
            f"📦 Aset: *{format_rupiah(float(snapshot.get('total_assets', 0) or 0))}*\n"
            f"💳 Liabilitas: *{format_rupiah(float(snapshot.get('total_liabilities', 0) or 0))}*\n"
            f"🏁 Net Worth: *{format_rupiah(float(snapshot.get('net_worth', 0) or 0))}*",
            parse_mode="Markdown",
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Gagal menyimpan snapshot net worth: {str(e)}"
        )


async def networth_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /networth_history — lihat snapshot terakhir
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    snapshots = get_net_worth_snapshots(limit=12)

    await update.message.reply_text(
        build_snapshots_text(snapshots),
        parse_mode="Markdown",
    )

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
    /export
    /export today
    /export week
    /export month
    /export 2026-06
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
            "`/export`\n"
            "`/export today`\n"
            "`/export week`\n"
            "`/export month`\n"
            "`/export 2026-06`",
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

GEMINI_INTENT_CONFIDENCE_EXECUTE = 0.80
GEMINI_INTENT_CONFIDENCE_CLARIFY = 0.60


def build_gemini_low_confidence_text(router_result: dict) -> str:
    intent = router_result.get("intent", "unknown")
    confidence = float(router_result.get("confidence", 0) or 0)
    explanation = router_result.get("explanation", "")

    return (
        "🤔 Saya agak paham maksudnya, tapi belum cukup yakin.\n\n"
        f"Intent terbaca: `{intent}`\n"
        f"Confidence: `{confidence:.2f}`\n"
        f"Catatan: {explanation or '-'}\n\n"
        "Coba pakai command eksplisit, contoh:\n"
        "`/last today`\n"
        "`/delete_txn 2`\n"
        "`/edit_txn 2 amount=15000`\n"
        "`/cari kopi`"
    )


def build_gemini_fallback_text() -> str:
    return (
        "🤔 Maaf, saya belum bisa memahami maksud input tersebut.\n\n"
        "Coba format transaksi seperti:\n"
        "`beli kopi 25rb`\n"
        "`gaji masuk 8 juta`\n"
        "`hutang ke Budi 500rb`\n"
        "`Budi minjem 300k`\n"
        "`bayar hutang Joko 200k`\n\n"
        "Atau pakai command:\n"
        "`/last today`\n"
        "`/saldo`\n"
        "`/budget`\n"
        "`/hutang`\n"
        "`/help`"
    )


def router_args_to_last_filter(args: dict) -> tuple[int, str | None, str | None, str]:
    """
    Convert args Gemini ke parameter get_recent_transactions.
    Return: limit, period, month, title
    """
    period = args.get("period")
    month = args.get("month")
    limit = args.get("limit")

    try:
        limit = int(limit) if limit else 10
    except Exception:
        limit = 10

    limit = min(max(limit, 1), 30)

    if month:
        month = str(month).strip()
        if re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", month):
            return limit, None, month, f"Transaksi {month}"

    if period == "today":
        return limit, "today", None, "Transaksi Hari Ini"

    if period == "week":
        return limit, "week", None, "Transaksi Minggu Ini"

    if period == "month":
        return limit, "month", None, "Transaksi Bulan Ini"

    return limit, None, None, "Transaksi Terakhir"


def extract_edit_updates_from_router(args: dict) -> dict:
    updates = args.get("updates", {}) or {}

    if not isinstance(updates, dict):
        return {}

    cleaned = {}

    for key, value in updates.items():
        if value is None:
            continue

        cleaned[str(key).strip()] = str(value).strip()

    return cleaned

def format_rupiah(amount: float) -> str:
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")

def md_safe(value) -> str:
    """
    Escape teks dinamis agar aman untuk Telegram parse_mode='Markdown'.

    Wajib dipakai untuk data dari user/sheet:
    - description
    - category
    - account
    - subject
    - transaction id
    """
    return escape_markdown(str(value or "-"), version=1)

KNOWN_COMMANDS = {
    "start": {
        "description": "Mulai bot dan lihat ringkasan fitur.",
        "destructive": False,
    },
    "help": {
        "description": "Lihat panduan lengkap penggunaan bot.",
        "destructive": False,
    },
    "saldo": {
        "description": "Lihat saldo semua rekening.",
        "destructive": False,
    },
    "harian": {
        "description": "Lihat ringkasan transaksi hari ini.",
        "destructive": False,
    },
    "mingguan": {
        "description": "Lihat ringkasan transaksi minggu ini.",
        "destructive": False,
    },
    "bulanan": {
        "description": "Lihat ringkasan transaksi bulan ini.",
        "destructive": False,
    },
    "budget": {
        "description": "Lihat budget bulan berjalan atau bulan tertentu.",
        "destructive": False,
    },
    "budget_history": {
        "description": "Lihat daftar bulan yang punya data budget.",
        "destructive": False,
    },
    "hutang": {
        "description": "Lihat utang/piutang aktif.",
        "destructive": False,
    },
    "cari": {
        "description": "Cari transaksi berdasarkan keyword.",
        "destructive": False,
    },
    "last": {
        "description": "Lihat transaksi terakhir dengan filter.",
        "destructive": False,
    },
    "delete_txn": {
        "description": "Hapus transaksi dari hasil /last atau berdasarkan ID.",
        "destructive": True,
    },
    "edit_txn": {
        "description": "Edit transaksi dari hasil /last atau berdasarkan ID.",
        "destructive": True,
    },
}


COMMAND_ALIASES = {
    # laporan
    "hari": "harian",
    "hariini": "harian",
    "harian": "harian",

    "minggu": "mingguan",
    "minguan": "mingguan",
    "mingguang": "mingguan",
    "mingguan": "mingguan",

    "bulan": "bulanan",
    "bulanan": "bulanan",

    # budget
    "buget": "budget",
    "budjet": "budget",
    "budged": "budget",
    "bujet": "budget",
    "budget": "budget",

    "budgethistory": "budget_history",
    "budget_history": "budget_history",
    "budget_histori": "budget_history",
    "budgethistori": "budget_history",
    "histori_budget": "budget_history",

    # hutang
    "utang": "hutang",
    "hutang": "hutang",

    # last/history
    "last": "last",
    "terakhir": "last",
    "histori": "last",
    "history": "last",
    "riwayat": "last",

    # delete
    "delete": "delete_txn",
    "delete_txn": "delete_txn",
    "detele": "delete_txn",
    "delet": "delete_txn",
    "del": "delete_txn",
    "hapus": "delete_txn",
    "hapus_txn": "delete_txn",
    "hapus_transaksi": "delete_txn",

    # edit
    "edit": "edit_txn",
    "edit_txn": "edit_txn",
    "edt": "edit_txn",
    "ubah": "edit_txn",
    "ubah_txn": "edit_txn",
    "ubah_transaksi": "edit_txn",

    # search
    "search": "cari",
    "find": "cari",
    "carii": "cari",
    "cari": "cari",
}


UNAVAILABLE_COMMANDS = {
    "kuartalan": (
        "Fitur laporan kuartalan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    ),
    "quarter": (
        "Fitur laporan kuartalan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    ),
    "triwulan": (
        "Fitur laporan triwulan/kuartalan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    ),
    "tahunan": (
        "Fitur laporan tahunan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    ),
    "yearly": (
        "Fitur laporan tahunan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    ),
    "export": (
        "Fitur export belum aktif.\n"
        "Nanti akan tersedia sebagai `/export 2026-06`."
    ),
    "ekspor": (
        "Fitur export belum aktif.\n"
        "Nanti akan tersedia sebagai `/export 2026-06`."
    ),
    "csv": (
        "Fitur export CSV belum aktif.\n"
        "Nanti akan tersedia sebagai `/export 2026-06`."
    ),
    "recurring": (
        "Fitur recurring expense belum aktif.\n"
        "Nanti akan tersedia untuk mencatat langganan/cicilan rutin."
    ),
    "cicilan": (
        "Fitur cicilan otomatis belum aktif.\n"
        "Untuk sekarang, cicilan masih perlu dicatat manual sebagai transaksi biasa."
    ),
    "networth": (
        "Fitur net worth tracker belum aktif.\n"
        "Nanti akan menghitung saldo rekening + aset + piutang - utang."
    ),
    "net_worth": (
        "Fitur net worth tracker belum aktif.\n"
        "Nanti akan menghitung saldo rekening + aset + piutang - utang."
    ),
}


SIMILARITY_THRESHOLD = 0.78
SIMILARITY_MARGIN = 0.12


def clean_command_token(command_text: str) -> str:
    """
    Bersihkan command/token user.

    Contoh:
    /minguan -> minguan
    minguan -> minguan
    /delete_txn@MyBot -> delete_txn
    """
    clean = str(command_text or "").strip().lower()
    clean = clean.lstrip("/")
    clean = clean.split("@")[0]
    clean = clean.strip()

    return clean


def command_description(command_name: str) -> str:
    info = KNOWN_COMMANDS.get(command_name, {})
    return info.get("description", "")


def is_destructive_command(command_name: str) -> bool:
    info = KNOWN_COMMANDS.get(command_name, {})
    return bool(info.get("destructive", False))


def similarity_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def get_similarity_candidates(clean_command: str) -> list[dict]:
    """
    Hitung similarity terhadap command resmi saja.
    Alias tidak dimasukkan agar tidak bikin hasil bias.
    """
    candidates = []

    for command_name in KNOWN_COMMANDS.keys():
        score = similarity_score(clean_command, command_name)
        candidates.append({
            "command": command_name,
            "score": score,
        })

    candidates = sorted(
        candidates,
        key=lambda x: x["score"],
        reverse=True,
    )

    return candidates


def resolve_command_local(command_text: str) -> dict:
    """
    Resolver command lokal yang deterministic.

    Layer:
    1. exact command
    2. unavailable exact
    3. alias exact
    4. similarity with threshold + margin
    5. unresolved

    Return:
    {
        "status": "exact"|"unavailable"|"alias"|"similarity"|"ambiguous"|"unresolved",
        "input": "minguan",
        "command": "mingguan" | None,
        "message": str,
        "score": float | None,
        "second_score": float | None,
    }
    """
    clean = clean_command_token(command_text)

    if not clean:
        return {
            "status": "unresolved",
            "input": clean,
            "command": None,
            "message": "Command kosong.",
            "score": None,
            "second_score": None,
        }

    # Layer 1: exact command resmi
    if clean in KNOWN_COMMANDS:
        return {
            "status": "exact",
            "input": clean,
            "command": clean,
            "message": "Command valid.",
            "score": 1.0,
            "second_score": None,
        }

    # Layer 2: unavailable exact
    # Harus sebelum similarity supaya /kuartalan tidak diarahkan ke /bulanan.
    if clean in UNAVAILABLE_COMMANDS:
        return {
            "status": "unavailable",
            "input": clean,
            "command": None,
            "message": UNAVAILABLE_COMMANDS[clean],
            "score": None,
            "second_score": None,
        }

    # Layer 3: alias exact
    # Alias harus exact, bukan contains.
    if clean in COMMAND_ALIASES:
        target = COMMAND_ALIASES[clean]

        return {
            "status": "alias",
            "input": clean,
            "command": target,
            "message": f"Mungkin maksud Anda `/{target}`.",
            "score": 1.0,
            "second_score": None,
        }

    # Layer 4: similarity lokal
    candidates = get_similarity_candidates(clean)

    if not candidates:
        return {
            "status": "unresolved",
            "input": clean,
            "command": None,
            "message": "Tidak ada kandidat command.",
            "score": None,
            "second_score": None,
        }

    best = candidates[0]
    second = candidates[1] if len(candidates) > 1 else {"command": None, "score": 0}

    best_score = float(best["score"])
    second_score = float(second["score"])
    margin = best_score - second_score

    if best_score >= SIMILARITY_THRESHOLD and margin >= SIMILARITY_MARGIN:
        return {
            "status": "similarity",
            "input": clean,
            "command": best["command"],
            "message": f"Mungkin maksud Anda `/{best['command']}`.",
            "score": best_score,
            "second_score": second_score,
        }

    # Kalau score tinggi tapi margin rendah, jangan force.
    if best_score >= SIMILARITY_THRESHOLD and margin < SIMILARITY_MARGIN:
        return {
            "status": "ambiguous",
            "input": clean,
            "command": None,
            "message": (
                "Command mirip dengan beberapa pilihan, tapi belum cukup yakin."
            ),
            "score": best_score,
            "second_score": second_score,
        }

    return {
        "status": "unresolved",
        "input": clean,
        "command": None,
        "message": "Command tidak dikenali.",
        "score": best_score,
        "second_score": second_score,
    }


def build_command_suggestion_text(resolved: dict, original_text: str) -> str:
    """
    Bangun response untuk command typo / unknown command.
    """
    status = resolved.get("status")
    clean = resolved.get("input") or clean_command_token(original_text)
    command = resolved.get("command")

    if status == "unavailable":
        return (
            f"❓ Fitur `/{clean}` belum tersedia.\n\n"
            f"{resolved.get('message')}\n\n"
            "Ketik `/help` untuk lihat fitur yang tersedia."
        )

    if status in ["alias", "similarity"] and command:
        description = command_description(command)

        if is_destructive_command(command):
            return (
                f"❓ Command `/{clean}` tidak dikenal.\n\n"
                f"Mungkin maksud Anda:\n"
                f"`/{command}` — {description}\n\n"
                "Catatan: command ini bisa mengubah data, jadi bot tidak akan menjalankannya otomatis.\n"
                "Ketik command yang benar secara manual."
            )

        return (
            f"❓ Command `/{clean}` tidak dikenal.\n\n"
            f"Mungkin maksud Anda:\n"
            f"`/{command}` — {description}\n\n"
            f"Ketik `/{command}` untuk menjalankan."
        )

    if status == "ambiguous":
        return (
            f"❓ Command `/{clean}` belum bisa saya pastikan.\n\n"
            "Command tersebut mirip dengan beberapa command lain, jadi saya tidak mau menebak.\n\n"
            "Command yang tersedia:\n"
            "`/saldo`, `/harian`, `/mingguan`, `/bulanan`, `/budget`, `/budget_history`, "
            "`/hutang`, `/cari`, `/last`, `/delete_txn`, `/edit_txn`, `/help`"
        )

    return (
        f"❓ Command `/{clean}` tidak tersedia.\n\n"
        "Command yang tersedia:\n"
        "`/saldo`, `/harian`, `/mingguan`, `/bulanan`, `/budget`, `/budget_history`, "
        "`/hutang`, `/cari`, `/last`, `/delete_txn`, `/edit_txn`, `/help`\n\n"
        "Ketik `/help` untuk panduan lengkap."
    )


def maybe_text_is_command_typo(text: str) -> str | None:
    """
    Deteksi typo command pada input tanpa slash.

    Rule:
    - Hanya agresif untuk input 1 token.
    - Untuk multi-token, jangan jawab "Command /cek tidak tersedia".
    """
    clean_text = str(text or "").strip().lower()

    if not clean_text:
        return None

    tokens = clean_text.split()

    # Jangan handle multi-token di typo resolver.
    # Multi-token harusnya masuk local natural intent atau Gemini.
    if len(tokens) != 1:
        return None

    has_amount = bool(
        re.search(
            r"\b\d+(?:[.,]\d+)?\s*(rb|ribu|k|jt|juta)?\b",
            clean_text,
            flags=re.IGNORECASE,
        )
    )

    if has_amount:
        return None

    first_token = tokens[0].lstrip("/")
    resolved = resolve_command_local(first_token)
    status = resolved.get("status")

    if status == "exact":
        cmd = resolved.get("command")
        return (
            f"❓ Sepertinya Anda mau pakai command.\n\n"
            f"Gunakan:\n"
            f"`/{cmd}` — {command_description(cmd)}"
        )

    if status in ["alias", "similarity", "unavailable", "ambiguous"]:
        text_response = build_command_suggestion_text(resolved, first_token)

        return text_response.replace(
            "Command `/",
            "Input `"
        ).replace(
            "tidak dikenal.",
            "terlihat seperti command, tapi belum valid."
        )

    return None

async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle slash command yang tidak dikenali.
    Contoh:
    /minguan -> saran /mingguan
    /mingguannn -> similarity ke /mingguan
    /detele -> saran /delete_txn
    /kuartalan -> fitur belum tersedia
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    command_text = update.message.text.strip().split()[0]
    resolved = resolve_command_local(command_text)

    await update.message.reply_text(
        build_command_suggestion_text(resolved, command_text),
        parse_mode="Markdown",
    )

def short_txn_id(txn_id: str) -> str:
    txn_id = str(txn_id or "")
    if len(txn_id) <= 18:
        return txn_id
    return txn_id[:18] + "..."


def resolve_txn_refs_from_last(context: ContextTypes.DEFAULT_TYPE, refs: list[str]) -> dict:
    """
    Resolve argumen /delete_txn.

    Support:
    - angka dari hasil /last terakhir: 1 2 3
      -> resolve ke row_index, bukan transaction_id

    - transaction_id langsung: txn_...
      -> resolve sebagai txn_ids
    """
    last_map = context.user_data.get("last_txn_map", {})

    row_indices = []
    txn_ids = []
    invalid_refs = []

    for ref in refs:
        clean = str(ref).strip()

        if not clean:
            continue

        if clean in last_map:
            mapped = last_map[clean]

            if isinstance(mapped, dict):
                row_index = mapped.get("row_index")

                if row_index:
                    row_indices.append(int(row_index))
                else:
                    invalid_refs.append(clean)

            else:
                # Backward compatibility kalau last_map lama masih string ID.
                txn_ids.append(str(mapped))

        else:
            # Kalau angka tapi tidak ada di last_map, berarti user belum /last
            # atau nomornya di luar hasil /last terakhir.
            if clean.isdigit():
                invalid_refs.append(clean)
            else:
                txn_ids.append(clean)

    unique_rows = []
    seen_rows = set()

    for row in row_indices:
        if row not in seen_rows:
            unique_rows.append(row)
            seen_rows.add(row)

    unique_ids = []
    seen_ids = set()

    for txn_id in txn_ids:
        if txn_id not in seen_ids:
            unique_ids.append(txn_id)
            seen_ids.add(txn_id)

    return {
        "row_indices": unique_rows,
        "txn_ids": unique_ids,
        "invalid_refs": invalid_refs,
    }

def build_last_transactions_text(transactions: list[dict], title: str) -> str:
    lines = [f"🧾 *{md_safe(title)}*\n"]

    for i, txn in enumerate(transactions, 1):
        txn_type = str(txn.get("type", "")).strip()

        icon = {
            "expense": "❌",
            "income": "✅",
            "transfer": "🔄",
        }.get(txn_type, "❓")

        txn_id = str(txn.get("id", ""))
        date = md_safe(txn.get("date", "-"))
        desc = md_safe(txn.get("description") or "-")
        category = md_safe(txn.get("category") or "-")
        account = md_safe(txn.get("account") or "-")
        to_account = md_safe(txn.get("to_account") or "")
        amount = float(txn.get("amount", 0) or 0)

        account_text = account
        if txn_type == "transfer" and str(txn.get("to_account") or "").strip():
            account_text = f"{account} → {to_account}"

        safe_txn_id = md_safe(short_txn_id(txn_id))

        lines.append(
            f"{i}. {icon} *{desc}*\n"
            f"   💰 {format_rupiah(amount)} | {category}\n"
            f"   📅 {date} | 🏦 {account_text}\n"
            f"   🔖 `{safe_txn_id}`"
        )

    lines.append(
        "\nHapus transaksi:\n"
        "`/delete_txn 1`\n"
        "`/delete_txn 1 3 5`\n\n"
        "Angka mengikuti nomor dari hasil `/last` terakhir."
    )

    return "\n".join(lines)

def build_delete_preview_text(preview: dict) -> str:
    deletable = preview.get("deletable", [])
    blocked = preview.get("blocked", [])
    missing_ids = preview.get("missing_ids", [])
    missing_rows = preview.get("missing_rows", [])
    reverse_deltas = preview.get("reverse_deltas", {})

    lines = ["⚠️ *Preview Hapus Transaksi*\n"]

    if deletable:
        lines.append("*Akan dihapus:*")
        for txn in deletable:
            txn_type = str(txn.get("type", "")).strip()

            icon = {
                "expense": "❌",
                "income": "✅",
                "transfer": "🔄",
            }.get(txn_type, "❓")

            row_index = md_safe(txn.get("_row_index", "-"))
            date = md_safe(txn.get("date", "-"))
            desc = md_safe(txn.get("description") or "-")
            category = md_safe(txn.get("category") or "-")
            account = md_safe(txn.get("account") or "-")
            amount = float(txn.get("amount", 0) or 0)

            lines.append(
                f"• {icon} Row {row_index} — {date} — *{desc}*\n"
                f"  {format_rupiah(amount)} | {category} | {account}"
            )

    if reverse_deltas:
        lines.append("\n*Efek ke saldo:*")
        for account, delta in reverse_deltas.items():
            safe_account = md_safe(account)
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {safe_account}: {sign}{format_rupiah(abs(delta))}")

    if blocked:
        lines.append("\n🚫 *Diblok karena transaksi debt cashflow:*")
        for txn in blocked:
            row_index = md_safe(txn.get("_row_index", "-"))
            date = md_safe(txn.get("date", "-"))
            desc = md_safe(txn.get("description") or "-")
            category = md_safe(txn.get("category") or "-")

            lines.append(
                f"• Row {row_index} — {date} — {desc} "
                f"({category})"
            )

        lines.append(
            "\nTransaksi debt belum dihapus lewat fitur ini supaya sheet `debts` tidak inkonsisten."
        )

    if missing_ids:
        lines.append("\n❓ *ID tidak ditemukan:*")
        for txn_id in missing_ids:
            safe_txn_id = md_safe(txn_id)
            lines.append(f"• `{safe_txn_id}`")

    if missing_rows:
        lines.append("\n❓ *Nomor dari /last tidak valid / tidak ditemukan:*")
        for row in missing_rows:
            safe_row = md_safe(row)
            lines.append(f"• `{safe_row}`")

    if deletable:
        lines.append("\nLanjut hapus transaksi di atas?")
    else:
        lines.append("\nTidak ada transaksi yang bisa dihapus.")

    return "\n".join(lines)

def is_authorized(update: Update) -> bool:
    if not update.effective_user:
        return False

    user_id = update.effective_user.id
    return user_id == ALLOWED_USER_ID


async def reject_unauthorized(update: Update):
    user_id = update.effective_user.id if update.effective_user else "unknown"

    message = (
        "⛔ Anda tidak punya akses ke bot ini.\n\n"
        f"User ID Anda: `{user_id}`\n\n"
        "Bot ini hanya bisa digunakan oleh user yang sudah diizinkan."
    )

    if update.message:
        await update.message.reply_text(message, parse_mode="Markdown")
        return

    if update.callback_query:
        try:
            await update.callback_query.answer(
                "⛔ Anda tidak punya akses.",
                show_alert=True,
            )
        except Exception:
            pass
        return


def parse_input(text: str) -> dict:
    """Coba regex dulu, fallback ke Gemini."""
    result = parse_with_regex(text)
    if result is not None:
        return result

    return parse_with_pending_fallback(text)


def build_progress_bar(pct: float, length: int = 10) -> str:
    """Buat progress bar teks. Contoh: [████░░░░░░] 40%"""
    filled = int(min(float(pct or 0), 100) / 100 * length)
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"


def split_user_inputs(text: str) -> list[str]:
    """
    Pecah input user menjadi beberapa item.

    Support:
    - newline
    - koma
    - titik koma
    - "dan" sebelum item baru
    - transaksi biasa berulang:
      beli kopi 10k beli nasi 20k
    - campuran transaksi + debt:
      beli kopi 10k minjem joko 10k
      beli kopi 10k hutang ke joko 10k

    Catatan penting:
    - "Budi minjem 300k" jangan dipecah.
    - "bayar hutang Joko 200k" jangan dipecah jadi bayar/hutang.
    """
    if not text:
        return []

    raw = text.strip()
    raw = re.sub(r"\s+", " ", raw)

    # Separator eksplisit
    raw = re.sub(r"[\n\r;]+", " ||| ", raw)
    raw = re.sub(r"\s*,\s*", " ||| ", raw)

    # Starter transaksi biasa
    transaction_starters = [
        "beli", "bayar", "byr", "jajan", "makan", "minum",
        "transfer", "top up", "topup", "isi",
        "gaji", "dapat", "dapet", "terima", "masuk",
        "hutang", "utang",
    ]

    # Starter debt yang boleh jadi item baru jika muncul setelah item lain
    # Contoh: "beli kopi 10k minjem joko 10k"
    debt_starters = [
        "minjem", "pinjem", "pinjam",
        "hutang ke", "utang ke",
        "bayar hutang", "bayar utang",
    ]

    all_starters = transaction_starters + debt_starters
    starter_pattern = "|".join(re.escape(k) for k in sorted(all_starters, key=len, reverse=True))

    # Pecah "dan beli", "dan minjem", dst.
    raw = re.sub(
        rf"\s+dan\s+(?=({starter_pattern})\b)",
        " ||| ",
        raw,
        flags=re.IGNORECASE,
    )

    # Protect single debt payment:
    # "bayar hutang Joko 200k"
    protected_debt_payment = re.search(
        r"\b(bayar|byr|lunasi|lunas|cicil)\s+(hutang|utang)\b",
        raw,
        flags=re.IGNORECASE,
    )

    if protected_debt_payment and "|||" not in raw:
        return [raw.strip(" .,-;")]

    # Split item baru jika sebelum keyword ada nominal.
    # Ini mencegah "Budi minjem 300k" terpecah karena sebelum "minjem" bukan nominal.
    amount_before_pattern = r"(?:\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)?|\d{4,})"

    raw = re.sub(
        rf"({amount_before_pattern})\s+(?=({starter_pattern})\b)",
        r"\1 ||| ",
        raw,
        flags=re.IGNORECASE,
    )

    # Split transaksi biasa berulang tanpa nominal protection tambahan.
    # Contoh: "beli nasi 10k beli ayam 20k"
    normal_starter_pattern = "|".join(re.escape(k) for k in transaction_starters)

    raw = re.sub(
        rf"(?<!^)\s+(?=({normal_starter_pattern})\b)",
        " ||| ",
        raw,
        flags=re.IGNORECASE,
    )

    parts = []
    for part in raw.split("|||"):
        clean = part.strip(" .,-;")
        if clean:
            parts.append(clean)

    return parts

def needs_account(parsed: dict) -> bool:
    """
    Transaksi expense/income butuh account jika belum ada.
    Transfer tidak dipaksa di sini karena bisa punya account/to_account berbeda.
    """
    if parsed.get("type") in ["expense", "income"] and not parsed.get("account"):
        return True

    return False

def is_debt_item(parsed: dict) -> bool:
    return parsed.get("kind") == "debt"


def is_transaction_item(parsed: dict) -> bool:
    return parsed.get("kind") == "transaction"


def build_mixed_preview(mixed_items: list[dict]) -> str:
    """Preview untuk campuran transaksi biasa + debt."""
    lines = [f"🧾 *Ditemukan {len(mixed_items)} item:*\n"]

    total_expense = 0
    total_income = 0
    total_debt = 0

    for i, item in enumerate(mixed_items, 1):
        kind = item["kind"]
        raw = item["raw"]

        if kind == "transaction":
            parsed = item["parsed"]
            txn_type = parsed.get("type")
            amount = float(parsed.get("amount", 0) or 0)

            if txn_type == "expense":
                icon = "❌"
                total_expense += amount
            elif txn_type == "income":
                icon = "✅"
                total_income += amount
            else:
                icon = "🔄"

            lines.append(
                f"{i}. {icon} *Transaksi*\n"
                f"   📝 {parsed.get('description') or '-'}\n"
                f"   💰 {format_rupiah(amount)} | {parsed.get('category') or '-'}\n"
                f"   🏦 {parsed.get('account') or '-'}\n"
                f"   Input: `{raw}`"
            )

        elif kind == "debt":
            parsed = item["parsed"]
            intent = parsed.get("intent")
            person = parsed.get("person_name") or "-"
            amount = float(parsed.get("amount", 0) or 0)
            total_debt += amount

            if intent == "add_receivable":
                label = "🟢 Piutang Baru"
                effect = "cash out"
            elif intent == "add_payable":
                label = "🔴 Utang Baru"
                effect = "cash in"
            elif intent == "add_payment":
                label = "💸 Pembayaran Debt"
                effect = "mengikuti posisi debt aktif"
            else:
                label = "❓ Debt"
                effect = "-"

            lines.append(
                f"{i}. {label}\n"
                f"   👤 {person}\n"
                f"   💰 {format_rupiah(amount)}\n"
                f"   🏦 {parsed.get('account') or '-'}\n"
                f"   📌 {effect}\n"
                f"   Input: `{raw}`"
            )

    lines.append("\n*Ringkasan awal:*")
    lines.append(f"❌ Transaksi Expense: *{format_rupiah(total_expense)}*")
    lines.append(f"✅ Transaksi Income : *{format_rupiah(total_income)}*")
    lines.append(f"💸 Total Nominal Debt: *{format_rupiah(total_debt)}*")

    return "\n".join(lines)

def parse_mixed_item(line: str) -> dict:
    """
    Parse satu item sebagai debt dulu, lalu transaksi biasa.

    Return:
    {
        "kind": "debt"|"transaction"|"failed",
        "parsed": dict,
        "raw": str
    }
    """
    debt_parsed = parse_debt_input(line)
    if debt_parsed:
        return {
            "kind": "debt",
            "parsed": debt_parsed,
            "raw": line,
        }

    txn_parsed = parse_input(line)
    if txn_parsed and txn_parsed.get("type") != "pending":
        return {
            "kind": "transaction",
            "parsed": txn_parsed,
            "raw": line,
        }

    return {
        "kind": "failed",
        "parsed": {},
        "raw": line,
    }

def mixed_needs_account(mixed_items: list[dict]) -> bool:
    for item in mixed_items:
        parsed = item["parsed"]

        if item["kind"] == "transaction" and needs_account(parsed):
            return True

        if item["kind"] == "debt" and not parsed.get("account"):
            return True

    return False

def build_preview(parsed: dict) -> str:
    """Buat teks preview transaksi sebelum disimpan."""
    type_label = {
        "expense": "❌ Pengeluaran",
        "income": "✅ Pemasukan",
        "transfer": "🔄 Transfer",
    }.get(parsed.get("type"), "❓")

    lines = [
        f"*{type_label}*",
        f"💰 Nominal : {format_rupiah(parsed.get('amount', 0))}",
        f"📁 Kategori: {parsed.get('category') or '-'}",
        f"👤 Subjek  : {parsed.get('subject') or '-'}",
        f"📝 Deskripsi: {parsed.get('description') or '-'}",
    ]

    if parsed.get("catatan"):
        lines.append(f"🗒️ Catatan : {parsed.get('catatan')}")

    if parsed.get("tipe_pengeluaran"):
        lines.append(f"🏷️ Tipe    : {parsed.get('tipe_pengeluaran')}")

    lines.append(f"📅 Tanggal : {parsed.get('date') or '-'}")

    if parsed.get("account"):
        lines.append(f"🏦 Rekening: {parsed.get('account')}")

    if parsed.get("to_account"):
        lines.append(f"➡️ Ke Rekening: {parsed.get('to_account')}")

    return "\n".join(lines)


def build_batch_preview(parsed_items: list[dict]) -> str:
    """Buat preview untuk banyak transaksi sekaligus."""
    lines = [f"🧾 *Ditemukan {len(parsed_items)} transaksi:*\n"]

    total_expense = 0
    total_income = 0

    for i, item in enumerate(parsed_items, 1):
        parsed = item["parsed"]

        type_icon = {
            "expense": "❌",
            "income": "✅",
            "transfer": "🔄",
        }.get(parsed.get("type"), "❓")

        amount = float(parsed.get("amount", 0) or 0)

        if parsed.get("type") == "expense":
            total_expense += amount
        elif parsed.get("type") == "income":
            total_income += amount

        desc = parsed.get("description") or "-"
        category = parsed.get("category") or "-"
        account = parsed.get("account") or "-"
        subject = parsed.get("subject") or "-"
        spending_type = parsed.get("tipe_pengeluaran") or "-"

        lines.append(
            f"{i}. {type_icon} *{desc}*\n"
            f"   💰 {format_rupiah(amount)} | {category}\n"
            f"   👤 {subject} | 🏦 {account} | 🏷️ {spending_type}"
        )

        if parsed.get("catatan"):
            lines.append(f"   🗒️ {parsed.get('catatan')}")

    lines.append("\n*Ringkasan:*")
    lines.append(f"❌ Total Pengeluaran: *{format_rupiah(total_expense)}*")
    lines.append(f"✅ Total Pemasukan   : *{format_rupiah(total_income)}*")

    return "\n".join(lines)


def build_debt_cashflow_transaction(
    debt_parsed: dict,
    account: str,
    debt_type_for_payment: str | None = None,
) -> dict:
    """
    Ubah aktivitas utang/piutang menjadi transaksi cashflow.
    """
    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or ""
    amount = debt_parsed.get("amount") or 0
    raw = debt_parsed.get("raw_input") or ""
    today = datetime.now().strftime("%Y-%m-%d")

    if intent == "add_receivable":
        return {
            "type": "expense",
            "amount": amount,
            "category": "Piutang Diberikan",
            "account": account,
            "to_account": None,
            "subject": person,
            "description": f"Pinjaman ke {person}",
            "catatan": raw,
            "tipe_pengeluaran": "",
            "date": today,
            "parsed_by": "debt",
        }

    if intent == "add_payable":
        return {
            "type": "income",
            "amount": amount,
            "category": "Penerimaan Utang",
            "account": account,
            "to_account": None,
            "subject": person,
            "description": f"Pinjaman dari {person}",
            "catatan": raw,
            "tipe_pengeluaran": "",
            "date": today,
            "parsed_by": "debt",
        }

    if intent == "add_payment":
        if debt_type_for_payment == "payable":
            return {
                "type": "expense",
                "amount": amount,
                "category": "Bayar Utang",
                "account": account,
                "to_account": None,
                "subject": person,
                "description": f"Bayar utang ke {person}",
                "catatan": raw,
                "tipe_pengeluaran": "",
                "date": today,
                "parsed_by": "debt",
            }

        if debt_type_for_payment == "receivable":
            return {
                "type": "income",
                "amount": amount,
                "category": "Pembayaran Piutang",
                "account": account,
                "to_account": None,
                "subject": person,
                "description": f"Pembayaran piutang dari {person}",
                "catatan": raw,
                "tipe_pengeluaran": "",
                "date": today,
                "parsed_by": "debt",
            }

    return {
        "type": "pending",
        "amount": 0,
        "category": None,
        "account": account,
        "to_account": None,
        "subject": person,
        "description": "Debt cashflow tidak valid",
        "catatan": raw,
        "tipe_pengeluaran": "",
        "date": today,
        "parsed_by": "debt",
    }


def build_debt_account_prompt(debt_parsed: dict) -> str:
    """Preview debt sebelum memilih rekening."""
    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or "-"
    amount = debt_parsed.get("amount") or 0

    if intent == "add_receivable":
        title = "🟢 *Piutang Baru*"
        desc = f"{person} meminjam uang dari Anda."
        effect = "Cashflow: pengeluaran, kategori Piutang Diberikan"

    elif intent == "add_payable":
        title = "🔴 *Utang Baru*"
        desc = f"Anda punya utang ke {person}."
        effect = "Cashflow: pemasukan, kategori Penerimaan Utang"

    elif intent == "add_payment":
        title = "💸 *Pembayaran Utang/Piutang*"
        desc = f"Pembayaran terkait {person}."
        effect = "Cashflow akan mengikuti posisi aktif di sheet debts"

    else:
        title = "❓ *Debt*"
        desc = "Input debt terdeteksi."
        effect = "-"

    return (
        f"{title}\n\n"
        f"👤 Subjek : {person}\n"
        f"💰 Nominal: {format_rupiah(amount)}\n"
        f"📝 Detail : {desc}\n"
        f"📌 Efek  : {effect}\n\n"
        f"💳 Pilih rekening cashflow:"
    )

def build_debt_confirm_preview(
    debt_parsed: dict,
    account: str,
    debt_type_for_payment: str | None = None,
) -> str:
    """Preview debt setelah rekening dipilih, sebelum disimpan."""
    transaction_parsed = build_debt_cashflow_transaction(
        debt_parsed,
        account,
        debt_type_for_payment=debt_type_for_payment,
    )

    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or "-"
    amount = debt_parsed.get("amount") or 0
    raw = debt_parsed.get("raw_input") or "-"

    if intent == "add_receivable":
        title = "🟢 *Piutang Baru*"
        debt_effect = f"{person} meminjam uang dari Anda."
    elif intent == "add_payable":
        title = "🔴 *Utang Baru*"
        debt_effect = f"Anda meminjam / punya utang ke {person}."
    elif intent == "add_payment":
        title = "💸 *Pembayaran Utang/Piutang*"
        debt_effect = f"Pembayaran terkait saldo aktif dengan {person}."
    else:
        title = "❓ *Debt*"
        debt_effect = "-"

    cashflow_type = {
        "expense": "❌ Cash Out / Pengeluaran",
        "income": "✅ Cash In / Pemasukan",
        "transfer": "🔄 Transfer",
    }.get(transaction_parsed.get("type"), "❓")

    return (
        f"{title}\n\n"
        f"👤 Subjek : {person}\n"
        f"💰 Nominal: {format_rupiah(amount)}\n"
        f"🏦 Rekening: {account}\n"
        f"📝 Input  : `{raw}`\n\n"
        f"*Efek Debt:*\n"
        f"{debt_effect}\n\n"
        f"*Efek Transactions:*\n"
        f"{cashflow_type}\n"
        f"📁 Kategori: {transaction_parsed.get('category') or '-'}\n"
        f"📝 Deskripsi: {transaction_parsed.get('description') or '-'}\n\n"
        f"Simpan utang/piutang ini?"
    )

def build_debt_batch_confirm_preview(
    debt_items: list[dict],
    account: str,
) -> str:
    """Preview batch debt setelah rekening dipilih, sebelum disimpan."""
    lines = [f"🧾 *Preview Batch Utang/Piutang*\n"]

    total_cash_in = 0
    total_cash_out = 0

    for i, item in enumerate(debt_items, 1):
        parsed = item["parsed"]
        intent = parsed.get("intent")
        person = parsed.get("person_name") or "-"
        amount = float(parsed.get("amount", 0) or 0)
        raw = item.get("raw") or parsed.get("raw_input") or "-"

        debt_type_for_payment = parsed.get("debt_type_for_payment")
        transaction_parsed = build_debt_cashflow_transaction(
            parsed,
            account,
            debt_type_for_payment=debt_type_for_payment,
        )

        txn_type = transaction_parsed.get("type")
        category = transaction_parsed.get("category") or "-"

        if txn_type == "income":
            cashflow_label = "✅ Cash In"
            total_cash_in += amount
        elif txn_type == "expense":
            cashflow_label = "❌ Cash Out"
            total_cash_out += amount
        else:
            cashflow_label = "❓ Cashflow belum pasti"

        if intent == "add_receivable":
            debt_label = "🟢 Piutang Baru"
        elif intent == "add_payable":
            debt_label = "🔴 Utang Baru"
        elif intent == "add_payment":
            debt_label = "💸 Pembayaran"
        else:
            debt_label = "❓ Debt"

        lines.append(
            f"{i}. {debt_label}\n"
            f"   👤 Subjek : {person}\n"
            f"   💰 Nominal: {format_rupiah(amount)}\n"
            f"   🏦 Rekening: {account}\n"
            f"   📁 Kategori: {category}\n"
            f"   📌 Efek: {cashflow_label}\n"
            f"   📝 Input: `{raw}`"
        )

    lines.append("\n*Ringkasan Cashflow:*")
    lines.append(f"✅ Total Cash In : *{format_rupiah(total_cash_in)}*")
    lines.append(f"❌ Total Cash Out: *{format_rupiah(total_cash_out)}*")
    lines.append("\nSimpan semua utang/piutang ini?")

    return "\n".join(lines)

def build_debt_batch_account_prompt(debt_items: list[dict]) -> str:
    """Preview batch debt sebelum memilih rekening."""
    lines = [f"🧾 *Ditemukan {len(debt_items)} input utang/piutang:*\n"]

    total_cash_in = 0
    total_cash_out = 0

    for i, item in enumerate(debt_items, 1):
        parsed = item["parsed"]
        intent = parsed.get("intent")
        person = parsed.get("person_name") or "-"
        amount = float(parsed.get("amount", 0) or 0)

        if intent == "add_receivable":
            label = "🟢 Piutang Baru"
            effect = "cash out"
            total_cash_out += amount

        elif intent == "add_payable":
            label = "🔴 Utang Baru"
            effect = "cash in"
            total_cash_in += amount

        elif intent == "add_payment":
            label = "💸 Pembayaran"
            effect = "mengikuti posisi debt aktif"

        else:
            label = "❓ Debt"
            effect = "-"

        lines.append(
            f"{i}. {label}\n"
            f"   👤 {person}\n"
            f"   💰 {format_rupiah(amount)}\n"
            f"   📌 {effect}"
        )

    lines.append("\n*Estimasi cashflow awal:*")
    lines.append(f"✅ Cash In : *{format_rupiah(total_cash_in)}*")
    lines.append(f"❌ Cash Out: *{format_rupiah(total_cash_out)}*")
    lines.append("\n💳 Pilih rekening cashflow untuk semua item:")

    return "\n".join(lines)


# ── Command Handlers ──────────────────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    text = (
        "👋 Halo! Saya bot pencatat keuangan pribadi Anda.\n\n"
        "Ketik transaksi bebas seperti:\n"
        "• `beli kopi 25rb`\n"
        "• `gaji masuk 8 juta`\n"
        "• `Budi minjem 300k`\n\n"
        "Command cepat:\n"
        "`/saldo` — lihat saldo\n"
        "`/last` — lihat transaksi terakhir\n"
        "`/budget` — lihat budget\n"
        "`/hutang` — lihat utang/piutang\n"
        "`/export` — export transaksi CSV\n"
        "`/recurring` — transaksi rutin\n"
        "`/networth` — lihat kekayaan bersih\n"

        "`/health` — cek status bot\n\n"
        "Ketik `/help` untuk panduan lengkap."
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    text = (
        "📖 *Panduan Penggunaan Finance Bot*\n\n"

        "*1. Catat Pengeluaran*\n"
        "`beli kopi 25rb`\n"
        "`makan siang 35k`\n"
        "`bayar listrik 150.000 dari BRI`\n"
        "`jajan bakso 20k dari Cash`\n\n"

        "*2. Catat Pemasukan*\n"
        "`gaji masuk 8 juta ke BRI`\n"
        "`freelance project 500rb ke DANA`\n"
        "`dapet bonus 1 juta`\n\n"

        "*3. Transfer Antar Rekening*\n"
        "`transfer gopay 200rb dari BRI`\n"
        "`top up dana dari bri 500rb`\n"
        "`isi GoPay 100k dari Cash`\n\n"

        "*4. Utang/Piutang*\n"
        "`hutang ke Budi 500rb`\n"
        "`minjem Joko 100k`\n"
        "`Budi minjem 300rb`\n"
        "`Budi bayar 100rb`\n"
        "`bayar hutang Budi 100rb`\n\n"

        "*5. Input Banyak Sekaligus*\n"
        "`beli kopi 10k beli nasi 20k`\n"
        "`beli kopi 10k minjem Joko 50k`\n"
        "`hutang ke Budi 500k; hutang ke Joko 100k`\n\n"

        "*6. Laporan*\n"
        "`/saldo` — saldo semua rekening\n"
        "`/harian` — ringkasan hari ini\n"
        "`/mingguan` — ringkasan minggu ini\n"
        "`/bulanan` — ringkasan bulan ini\n"
        "`/hutang` — utang/piutang aktif\n"
        "`/cari kopi` — cari transaksi dengan keyword kopi\n\n"

        "*7. Budget*\n"
        "`/budget` — lihat budget bulan berjalan\n"
        "`/budget 2026-06` — lihat budget bulan tertentu\n"
        "`/budget_history` — lihat daftar bulan yang punya budget\n"
        "`budget makan 1.5 juta` — set budget bulan berjalan\n"
        "`budget transport 300rb 2026-07` — set budget bulan tertentu\n\n"

        "*8. Lihat & Koreksi Transaksi*\n"
        "`/last` — lihat 10 transaksi terakhir\n"
        "`/last 20` — lihat 20 transaksi terakhir\n"
        "`/last today` — lihat transaksi hari ini\n"
        "`/last week` — lihat transaksi minggu ini\n"
        "`/last month` — lihat transaksi bulan ini\n"
        "`/last 2026-06` — lihat transaksi bulan tertentu\n\n"

        "*9. Hapus Transaksi*\n"
        "`/delete_txn 1` — hapus transaksi nomor 1 dari hasil /last\n"
        "`/delete_txn 1 3 5` — hapus banyak transaksi sekaligus\n"
        "`/delete_txn txn_20260609_xxx` — hapus berdasarkan transaction ID\n\n"

        "*10. Edit Transaksi*\n"
        "`/edit_txn 2 amount=15000`\n"
        "`/edit_txn 2 desc=\"Kopi susu\"`\n"
        "`/edit_txn 2 account=BRI`\n"
        "`/edit_txn 2 category=\"Food & Beverage\"`\n"
        "`/edit_txn 2 date=2026-06-10`\n"
        "`/edit_txn 2 20000` — shortcut edit nominal\n\n"

        "*11. Export CSV*\n"
        "`/export` — export transaksi bulan berjalan\n"
        "`/export today` — export transaksi hari ini\n"
        "`/export week` — export transaksi minggu ini\n"
        "`/export month` — export transaksi bulan ini\n"
        "`/export 2026-06` — export transaksi bulan tertentu\n\n"

        "*12. Recurring Transaction*\n"
        "`/recurring` — lihat daftar transaksi rutin\n"
        "`/recurring_add Netflix | expense | 65000 | Entertainment | DANA | monthly | 5 | Langganan Netflix`\n"
        "`/recurring_edit <rule_id> | amount=75000 | day=10` — edit recurring rule\n"
        "`/recurring_run` — jalankan transaksi rutin yang jatuh tempo\n"
        "`/recurring_off <rule_id>` — nonaktifkan transaksi rutin\n\n"

        "*13. Health Check*\n"
        "`/health` — cek status bot, env, Google Sheets, dan sheet utama\n\n"

        "*14. Net Worth Tracker*\n"
        "`/networth` — lihat total kekayaan bersih\n"
        "`/assets` — lihat daftar aset aktif\n"
        "`/liabilities` — lihat daftar liabilitas aktif\n"
        "`/asset_add Laptop | 8000000 | Electronics | Laptop kerja` — tambah aset\n"
        "`/asset_update asset_id | value=9000000` — update nilai aset\n"
        "`/asset_off asset_id` — nonaktifkan aset\n"
        "`/liability_add Paylater | 1200000 | Paylater | Cicilan aktif` — tambah liabilitas\n"
        "`/liability_update liab_id | balance=500000` — update liabilitas\n"
        "`/liability_off liab_id` — nonaktifkan liabilitas\n"
        "`/networth_snapshot` — simpan snapshot net worth hari ini\n"
        "`/networth_history` — lihat riwayat snapshot net worth\n\n"

        "*Catatan penting:*\n"
        "• Untuk `/delete_txn` dan `/edit_txn`, jalankan `/last` dulu.\n"
        "• Angka `1`, `2`, `3` mengikuti nomor dari hasil `/last` terakhir.\n"
        "• Transaksi debt cashflow belum bisa diedit/hapus dari fitur transaksi biasa agar sheet debts tidak rusak.\n\n"


        "Kalau command typo, bot akan coba kasih saran.\n"
        "Contoh: `/minguan` akan diarahkan ke `/mingguan`."
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    accounts = get_all_accounts()
    if not accounts:
        await update.message.reply_text("❌ Tidak ada data rekening.")
        return

    total = sum(float(acc.get("balance", 0) or 0) for acc in accounts)
    lines = ["💰 *Saldo Rekening*\n"]

    emoji_map = {
        "cash": "💵",
        "bank": "🏦",
        "ewallet": "📱",
    }

    for acc in accounts:
        emoji = emoji_map.get(str(acc.get("type", "")).lower(), "💳")
        name = acc.get("account_name", "")
        balance = float(acc.get("balance", 0) or 0)
        lines.append(f"{emoji} {name}: *{format_rupiah(balance)}*")

    lines.append(f"\n📊 Total: *{format_rupiah(total)}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def harian_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    report = get_daily_report()
    date_str = report["date"]

    if report["count"] == 0:
        await update.message.reply_text(f"📭 Belum ada transaksi hari ini ({date_str}).")
        return

    lines = [f"📅 *Ringkasan Harian*\n_{date_str}_\n"]
    lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
    lines.append(f"❌ Pengeluaran: *{format_rupiah(report['total_expense'])}*")
    lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
    lines.append(f"📝 Transaksi : {report['count']} item\n")

    if report["by_category"]:
        lines.append("*Pengeluaran per Kategori:*")
        total_expense = float(report["total_expense"] or 0)

        for cat, amount in sorted(report["by_category"].items(), key=lambda x: x[1], reverse=True):
            pct = (float(amount) / total_expense) * 100 if total_expense else 0
            bar = build_progress_bar(pct)
            lines.append(f"  • {cat}: *{format_rupiah(amount)}*\n    {bar} {pct:.1f}%")

    top = sorted(
        [t for t in report.get("transactions", []) if t.get("type") == "expense"],
        key=lambda x: float(x.get("amount", 0) or 0),
        reverse=True,
    )[:3]

    if top:
        lines.append("\n*Top 3 Pengeluaran:*")
        total_expense = float(report["total_expense"] or 0)

        for i, t in enumerate(top, 1):
            amount = float(t.get("amount", 0) or 0)
            contrib = (amount / total_expense * 100) if total_expense else 0

            lines.append(
                f"  {i}. {t.get('description', '-')}\n"
                f"     {t.get('category', '-')} - "
                f"*{format_rupiah(amount)}* | {contrib:.1f}% dari pengeluaran"
            )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def mingguan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    report = get_weekly_report()

    if report["count"] == 0:
        await update.message.reply_text(
            f"📭 Belum ada transaksi minggu ini.\n"
            f"({report['date_from']} s/d {report['date_to']})"
        )
        return

    lines = [
        f"📆 *Ringkasan Mingguan*\n"
        f"_{report['date_from']} s/d {report['date_to']}_\n"
    ]
    lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
    lines.append(f"❌ Pengeluaran: *{format_rupiah(report['total_expense'])}*")
    lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
    lines.append(f"📝 Transaksi : {report['count']} item\n")

    if report["by_category"]:
        lines.append("*Pengeluaran per Kategori:*")
        total_expense = float(report["total_expense"] or 0)

        for cat, amount in sorted(report["by_category"].items(), key=lambda x: x[1], reverse=True):
            pct = (float(amount) / total_expense) * 100 if total_expense else 0
            bar = build_progress_bar(pct)
            lines.append(f"  • {cat}: *{format_rupiah(amount)}*\n    {bar} {pct:.1f}%")

    top = sorted(
        [t for t in report.get("transactions", []) if t.get("type") == "expense"],
        key=lambda x: float(x.get("amount", 0) or 0),
        reverse=True,
    )[:3]

    if top:
        lines.append("\n*Top 3 Pengeluaran:*")
        total_expense = float(report["total_expense"] or 0)

        for i, t in enumerate(top, 1):
            amount = float(t.get("amount", 0) or 0)
            contrib = (amount / total_expense * 100) if total_expense else 0

            lines.append(
                f"  {i}. {t.get('description', '-')}\n"
                f"     {t.get('category', '-')} - "
                f"*{format_rupiah(amount)}* | {contrib:.1f}% dari pengeluaran"
            )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def bulanan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    report = get_monthly_report()

    if report["count"] == 0:
        await update.message.reply_text("📭 Belum ada transaksi bulan ini.")
        return

    now = datetime.now()
    month_name = now.strftime("%B %Y")

    lines = [f"📆 *Ringkasan Bulanan*\n_{month_name}_\n"]
    lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
    lines.append(f"❌ Pengeluaran: *{format_rupiah(report['total_expense'])}*")
    lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
    lines.append(f"📝 Transaksi : {report['count']} item\n")

    if report["by_category"]:
        lines.append("*Pengeluaran per Kategori:*")
        total_expense = float(report["total_expense"] or 0)

        for cat, amount in sorted(report["by_category"].items(), key=lambda x: x[1], reverse=True):
            pct = (float(amount) / total_expense) * 100 if total_expense else 0
            bar = build_progress_bar(pct)
            lines.append(f"  • {cat}: *{format_rupiah(amount)}*\n    {bar} {pct:.1f}%")

    top = sorted(
        [t for t in report.get("transactions", []) if t.get("type") == "expense"],
        key=lambda x: float(x.get("amount", 0) or 0),
        reverse=True,
    )[:3]

    if top:
        lines.append("\n*Top 3 Pengeluaran:*")
        total_expense = float(report["total_expense"] or 0)

        for i, t in enumerate(top, 1):
            amount = float(t.get("amount", 0) or 0)
            contrib = (amount / total_expense * 100) if total_expense else 0

            lines.append(
                f"  {i}. {t.get('description', '-')}\n"
                f"     {t.get('category', '-')} - "
                f"*{format_rupiah(amount)}* | {contrib:.1f}% dari pengeluaran"
            )

    budget_summary = get_budget_summary()
    if budget_summary:
        lines.append("\n*Budget vs Realisasi:*")
        for item in budget_summary:
            bar = build_progress_bar(item["pct_used"])
            lines.append(
                f"{item['emoji']} {item['category']}\n"
                f"  {bar} {item['pct_used']}%"
            )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cari_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "🔍 Masukkan keyword pencarian.\n"
            "Contoh: `/cari kopi`",
            parse_mode="Markdown",
        )
        return

    keyword = " ".join(args)
    results = search_transactions(keyword)

    if not results:
        await update.message.reply_text(
            f"🔍 Tidak ada transaksi dengan keyword *{keyword}*.",
            parse_mode="Markdown",
        )
        return

    lines = [f"🔍 *Hasil pencarian: \"{keyword}\"*\n"]

    for t in results:
        icon = "➕" if t.get("type") == "income" else "➖" if t.get("type") == "expense" else "🔄"
        lines.append(
            f"{icon} {t.get('date')} — {t.get('description', '-')}\n"
            f"   *{format_rupiah(float(t.get('amount', 0) or 0))}* | {t.get('category', '-')}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /budget
    /budget 2026-06
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    month_arg = context.args[0] if context.args else None

    try:
        month = normalize_month(month_arg)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/budget`\n"
            "`/budget 2026-06`",
            parse_mode="Markdown",
        )
        return

    summary = get_budget_summary(month)

    if not summary:
        await update.message.reply_text(
            f"📭 Belum ada budget untuk *{format_month_label(month)}*.\n\n"
            "Set budget dengan cara:\n"
            "`budget makan 1.5 juta`\n"
            "`budget transport 300rb`\n"
            "`budget makan 1.5 juta 2026-07`\n\n"
            "Lihat histori bulan yang tersedia:\n"
            "`/budget_history`",
            parse_mode="Markdown",
        )
        return

    total_budget = sum(float(item.get("budget", 0) or 0) for item in summary)
    total_actual = sum(float(item.get("actual", 0) or 0) for item in summary)
    total_remaining = total_budget - total_actual
    total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0

    lines = [f"📊 *Budget {format_month_label(month)}*\n"]

    lines.append(f"💰 Total Budget : *{format_rupiah(total_budget)}*")
    lines.append(f"💸 Realisasi    : *{format_rupiah(total_actual)}*")
    lines.append(f"📌 Sisa         : *{format_rupiah(total_remaining)}*")
    lines.append(f"📈 Terpakai     : *{total_pct:.1f}%*\n")

    for item in summary:
        bar = build_progress_bar(item["pct_used"])
        remaining_label = "Sisa" if item["remaining"] >= 0 else "Over"

        lines.append(
            f"{item['emoji']} *{item['category']}*\n"
            f"  {bar} {item['pct_used']}%\n"
            f"  Pakai: {format_rupiah(item['actual'])} / {format_rupiah(item['budget'])}\n"
            f"  {remaining_label}: {format_rupiah(abs(item['remaining']))}\n"
        )

    lines.append(
        "Cek bulan lain:\n"
        f"`/budget {month}`"
    )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def budget_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /budget_history
    Tampilkan daftar bulan yang punya budget.
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    months = get_budget_months()

    if not months:
        await update.message.reply_text(
            "📭 Belum ada histori budget.\n\n"
            "Set budget dulu, contoh:\n"
            "`budget makan 1.5 juta`\n"
            "`budget makan 2 juta 2026-07`",
            parse_mode="Markdown",
        )
        return

    lines = ["🗂️ *Histori Budget Tersedia*\n"]

    for month in sorted(months, reverse=True):
        try:
            label = format_month_label(month)
        except Exception:
            label = month

        lines.append(f"• `{month}` — {label}")

    lines.append(
        "\nLihat detail dengan:\n"
        "`/budget 2026-06`"
    )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def set_budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Input bebas:
    budget makan 1.5 juta
    budget makan 1.5 juta 2026-07
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    text = update.message.text.strip()
    text_lower = text.lower()

    from app.nlp.normalizer import extract_amount_from_text

    amount = extract_amount_from_text(text_lower)
    if not amount:
        await update.message.reply_text(
            "❌ Nominal budget tidak ditemukan.\n"
            "Contoh:\n"
            "`budget makan 1.5 juta`\n"
            "`budget makan 1.5 juta 2026-07`",
            parse_mode="Markdown",
        )
        return

    month_match = re.search(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])\b", text_lower)

    if month_match:
        raw_month = f"{month_match.group(1)}-{month_match.group(2)}"
        try:
            month = normalize_month(raw_month)
        except ValueError as e:
            await update.message.reply_text(
                f"❌ {str(e)}\n"
                "Contoh bulan: `2026-07`",
                parse_mode="Markdown",
            )
            return
    else:
        month = normalize_month(None)

    categories = get_all_records(SHEET_CATEGORIES)
    matched_category = None

    # Hilangkan angka dan bulan dari teks agar matching kategori tidak keganggu
    text_for_category = re.sub(r"\b20\d{2}[-/](0?[1-9]|1[0-2])\b", " ", text_lower)
    text_for_category = re.sub(r"\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)?", " ", text_for_category)
    text_for_category = re.sub(r"\s+", " ", text_for_category).strip()

    for cat in categories:
        cat_name = str(cat.get("category_name", "")).strip()
        aliases_raw = str(cat.get("aliases", "")).strip()

        all_keywords = [cat_name.lower()]
        if aliases_raw:
            all_keywords += [a.strip().lower() for a in aliases_raw.split(",")]

        for keyword in all_keywords:
            if keyword and keyword in text_for_category:
                matched_category = cat_name
                break

        if matched_category:
            break

    if not matched_category:
        await update.message.reply_text(
            "❌ Kategori tidak dikenali.\n\n"
            "Contoh penggunaan:\n"
            "`budget makan 1.5 juta`\n"
            "`budget transport 300rb`\n"
            "`budget belanja 500rb 2026-07`\n"
            "`budget listrik 200rb 2027-01`",
            parse_mode="Markdown",
        )
        return

    result = set_budget(matched_category, amount, month=month)

    if not result.get("success"):
        await update.message.reply_text(f"❌ {result.get('message')}")
        return

    action_label = "diset" if result["action"] == "created" else "diupdate"

    await update.message.reply_text(
        f"✅ Budget *{matched_category}* {action_label}!\n"
        f"📅 Bulan: *{format_month_label(month)}*\n"
        f"💰 {format_rupiah(amount)} / bulan\n\n"
        f"Cek dengan:\n"
        f"`/budget {month}`",
        parse_mode="Markdown",
    )

async def hutang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    summary = get_debt_summary()

    if not summary["payables"] and not summary["receivables"]:
        await update.message.reply_text("✅ Tidak ada utang atau piutang aktif.")
        return

    lines = ["💸 *Utang & Piutang Aktif*\n"]

    if summary["payables"]:
        lines.append(f"🔴 *Utang Anda* (total: {format_rupiah(summary['total_payable'])})")
        for d in summary["payables"]:
            due = f" | jatuh tempo: {d.get('due_date')}" if d.get("due_date") else ""
            lines.append(
                f"  • {d.get('person_name')} — "
                f"*{format_rupiah(float(d.get('remaining_amount', 0) or 0))}*"
                f"{due}"
            )

    if summary["payables"] and summary["receivables"]:
        lines.append("")

    if summary["receivables"]:
        lines.append(
            f"🟢 *Piutang Anda* (total: {format_rupiah(summary['total_receivable'])})"
        )
        for d in summary["receivables"]:
            lines.append(
                f"  • {d.get('person_name')} — "
                f"*{format_rupiah(float(d.get('remaining_amount', 0) or 0))}*"
            )

    net = summary["total_receivable"] - summary["total_payable"]
    net_label = "🟢 Anda lebih banyak dihutangi" if net >= 0 else "🔴 Anda lebih banyak berhutang"
    lines.append(f"\n{net_label}: *{format_rupiah(abs(net))}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Debt Message Handler ─────────────────────────────────────────────────────

async def debt_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle input debt dari pesan bebas.

    Debt tidak langsung diproses.
    Bot akan tanya rekening dulu supaya aktivitas debt juga masuk transactions
    dan saldo rekening ikut berubah.
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return True

    text = update.message.text.strip()
    debt_parsed = parse_debt_input(text)

    if not debt_parsed:
        return False

    person = debt_parsed.get("person_name")
    intent = debt_parsed.get("intent")

    if not person:
        if intent == "add_payable":
            await update.message.reply_text(
                "❓ Siapa yang Anda hutangi?\n"
                "Contoh: `hutang ke Budi 500rb buat makan`",
                parse_mode="Markdown",
            )
            return True

        if intent == "add_receivable":
            await update.message.reply_text(
                "❓ Siapa yang meminjam uang ke Anda?\n"
                "Contoh: `Budi minjem 300rb`",
                parse_mode="Markdown",
            )
            return True

        if intent == "add_payment":
            await update.message.reply_text(
                "❓ Pembayaran ini terkait siapa?\n"
                "Contoh: `Budi bayar 300rb` atau `bayar hutang Budi 300rb`",
                parse_mode="Markdown",
            )
            return True

    context.user_data["pending_debt"] = debt_parsed
    context.user_data.pop("pending_parsed", None)
    context.user_data.pop("pending_raw", None)
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt_batch", None)

    await update.message.reply_text(
        build_debt_account_prompt(debt_parsed),
        parse_mode="Markdown",
        reply_markup=account_keyboard("debt_acc"),
    )

    return True

async def handle_gemini_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """
    Jalankan hasil Gemini intent router.

    Return:
    - True jika sudah di-handle
    - False jika harus lanjut fallback biasa

    Safety:
    - delete/edit tetap preview dan butuh tombol Simpan.
    - confidence rendah tidak dieksekusi.
    """
    if not should_try_gemini_intent_router(user_text):
        return False

    router_result = route_intent_with_gemini(user_text)

    intent = router_result.get("intent", "unknown")
    confidence = float(router_result.get("confidence", 0) or 0)
    args = router_result.get("args", {}) or {}

    if confidence < GEMINI_INTENT_CONFIDENCE_CLARIFY:
        return False

    if confidence < GEMINI_INTENT_CONFIDENCE_EXECUTE:
        await update.message.reply_text(
            build_gemini_low_confidence_text(router_result),
            parse_mode="Markdown",
        )
        return True

    # ── Non-destructive intents ───────────────────────────────────────────────

    if intent == "help":
        await help_handler(update, context)
        return True

    if intent == "saldo":
        await saldo_handler(update, context)
        return True

    if intent == "harian":
        await harian_handler(update, context)
        return True

    if intent == "mingguan":
        await mingguan_handler(update, context)
        return True

    if intent == "bulanan":
        await bulanan_handler(update, context)
        return True

    if intent == "hutang":
        await hutang_handler(update, context)
        return True

    if intent == "budget_history":
        await budget_history_handler(update, context)
        return True

    if intent == "last":
        limit, period, month, title = router_args_to_last_filter(args)

        transactions = get_recent_transactions(
            limit=limit,
            period=period,
            month=month,
        )

        if not transactions:
            await update.message.reply_text(
                f"📭 Tidak ada transaksi untuk filter: *{title}*",
                parse_mode="Markdown",
            )
            return True

        last_map = {}

        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, title),
            parse_mode="Markdown",
        )
        return True

    if intent == "cari":
        query = str(args.get("query") or "").strip()

        if not query:
            await update.message.reply_text(
                "🔍 Mau cari transaksi apa?\n\n"
                "Contoh:\n"
                "`cari kopi`\n"
                "`/cari kopi`",
                parse_mode="Markdown",
            )
            return True

        results = search_transactions(query)

        if not results:
            await update.message.reply_text(
                f"🔍 Tidak ada transaksi dengan keyword *{query}*.",
                parse_mode="Markdown",
            )
            return True

        lines = [f"🔍 *Hasil pencarian: \"{query}\"*\n"]

        for t in results:
            icon = "➕" if t.get("type") == "income" else "➖" if t.get("type") == "expense" else "🔄"
            lines.append(
                f"{icon} {t.get('date')} — {t.get('description', '-')}\n"
                f"   *{format_rupiah(float(t.get('amount', 0) or 0))}* | {t.get('category', '-')}"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    if intent == "budget":
        month = args.get("month")

        try:
            normalized_month = normalize_month(month)
        except Exception:
            normalized_month = normalize_month(None)

        summary = get_budget_summary(normalized_month)

        if not summary:
            await update.message.reply_text(
                f"📭 Belum ada budget untuk *{format_month_label(normalized_month)}*.\n\n"
                "Set budget dengan cara:\n"
                "`budget makan 1.5 juta`\n"
                "`budget transport 300rb`\n"
                "`budget makan 1.5 juta 2026-07`",
                parse_mode="Markdown",
            )
            return True

        total_budget = sum(float(item.get("budget", 0) or 0) for item in summary)
        total_actual = sum(float(item.get("actual", 0) or 0) for item in summary)
        total_remaining = total_budget - total_actual
        total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0

        lines = [f"📊 *Budget {format_month_label(normalized_month)}*\n"]
        lines.append(f"💰 Total Budget : *{format_rupiah(total_budget)}*")
        lines.append(f"💸 Realisasi    : *{format_rupiah(total_actual)}*")
        lines.append(f"📌 Sisa         : *{format_rupiah(total_remaining)}*")
        lines.append(f"📈 Terpakai     : *{total_pct:.1f}%*\n")

        for item in summary:
            bar = build_progress_bar(item["pct_used"])
            remaining_label = "Sisa" if item["remaining"] >= 0 else "Over"

            lines.append(
                f"{item['emoji']} *{item['category']}*\n"
                f"  {bar} {item['pct_used']}%\n"
                f"  Pakai: {format_rupiah(item['actual'])} / {format_rupiah(item['budget'])}\n"
                f"  {remaining_label}: {format_rupiah(abs(item['remaining']))}\n"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    # ── Destructive intents: preview only ─────────────────────────────────────

    if intent == "delete_txn":
        ref = str(args.get("ref") or "").strip()

        if not ref:
            await update.message.reply_text(
                "❌ Saya menangkap intent hapus transaksi, tapi nomor/ID transaksinya belum jelas.\n\n"
                "Contoh:\n"
                "`hapus transaksi nomor 2`\n"
                "`/delete_txn 2`",
                parse_mode="Markdown",
            )
            return True

        resolved = resolve_txn_refs_from_last(context, [ref])

        if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
            await update.message.reply_text(
                "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
                "Jalankan dulu:\n"
                "`/last`\n\n"
                "Lalu coba lagi:\n"
                "`hapus transaksi nomor 2`",
                parse_mode="Markdown",
            )
            return True

        preview = preview_delete_transactions_by_refs(
            row_indices=resolved["row_indices"],
            txn_ids=resolved["txn_ids"],
        )

        if not preview.get("deletable"):
            await update.message.reply_text(
                build_delete_preview_text(preview),
                parse_mode="Markdown",
            )
            return True

        context.user_data["pending_delete_refs"] = {
            "row_indices": [
                int(txn.get("_row_index"))
                for txn in preview.get("deletable", [])
                if txn.get("_row_index")
            ],
            "txn_ids": [],
        }

        await update.message.reply_text(
            build_delete_preview_text(preview),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("delete_txns"),
        )
        return True

    if intent == "edit_txn":
        ref = str(args.get("ref") or "").strip()
        updates = extract_edit_updates_from_router(args)

        if not ref:
            await update.message.reply_text(
                "❌ Saya menangkap intent edit transaksi, tapi nomor/ID transaksinya belum jelas.\n\n"
                "Contoh:\n"
                "`edit transaksi nomor 2 jadi 15000`\n"
                "`/edit_txn 2 amount=15000`",
                parse_mode="Markdown",
            )
            return True

        if not updates:
            await update.message.reply_text(
                "❌ Saya menangkap intent edit transaksi, tapi field yang diedit belum jelas.\n\n"
                "Contoh:\n"
                "`edit transaksi nomor 2 jadi 15000`\n"
                "`edit transaksi nomor 2 deskripsinya Kopi susu`",
                parse_mode="Markdown",
            )
            return True

        # Fitur ini butuh preview_edit_transaction_by_ref.
        # Kalau kamu belum pasang Phase edit_txn, bagian ini akan error saat import.
        resolved = resolve_txn_refs_from_last(context, [ref])

        if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
            await update.message.reply_text(
                "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
                "Jalankan dulu:\n"
                "`/last`\n\n"
                "Lalu coba lagi:\n"
                "`edit transaksi nomor 2 jadi 15000`",
                parse_mode="Markdown",
            )
            return True

        row_index = resolved["row_indices"][0] if resolved["row_indices"] else None
        txn_id = resolved["txn_ids"][0] if resolved["txn_ids"] else None

        try:
            preview = preview_edit_transaction_by_ref(
                updates=updates,
                row_index=row_index,
                txn_id=txn_id,
            )
        except NameError:
            await update.message.reply_text(
                "❌ Gemini sudah menangkap intent edit, tapi fitur `/edit_txn` belum terpasang penuh di kode.\n\n"
                "Pasang Phase `edit_txn` dulu, lalu fitur natural edit bisa aktif.",
                parse_mode="Markdown",
            )
            return True

        if not preview.get("success"):
            await update.message.reply_text(
                f"❌ {preview.get('message')}",
                parse_mode="Markdown",
            )
            return True

        context.user_data["pending_edit_txn"] = {
            "row_index": row_index,
            "txn_id": txn_id,
            "updates": updates,
        }

        await update.message.reply_text(
            build_edit_preview_text(preview),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("edit_txn"),
        )
        return True

    return False


def normalize_text_command(text: str) -> str:
    clean = str(text or "").strip().lower()
    clean = re.sub(r"\s+", " ", clean)
    return clean


async def handle_local_natural_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """
    Handle natural command sederhana secara lokal tanpa Gemini.

    Tujuan:
    - "cek saldo" jangan perlu Gemini
    - "cek hutang" jangan jatuh ke typo resolver "cek"
    - "cari kopi" langsung jadi pencarian
    - "lihat transaksi hari ini" langsung jadi /last today

    Return True kalau sudah di-handle.
    """
    clean = normalize_text_command(user_text)

    if not clean:
        return False

    # Jangan ganggu input yang mengandung nominal, karena kemungkinan transaksi.
    has_amount = bool(
        re.search(
            r"\b\d+(?:[.,]\d+)?\s*(rb|ribu|k|jt|juta)?\b",
            clean,
            flags=re.IGNORECASE,
        )
    )

    if has_amount:
        return False

    # ── Saldo ────────────────────────────────────────────────────────────────
    saldo_patterns = {
        "cek saldo",
        "lihat saldo",
        "tampilkan saldo",
        "saldo",
    }

    if clean in saldo_patterns:
        await saldo_handler(update, context)
        return True

    # ── Hutang / Utang / Piutang ─────────────────────────────────────────────
    hutang_patterns = {
        "cek hutang",
        "cek utang",
        "lihat hutang",
        "lihat utang",
        "tampilkan hutang",
        "tampilkan utang",
        "cek piutang",
        "lihat piutang",
        "tampilkan piutang",
        "cek hutang piutang",
        "lihat hutang piutang",
        "lihat utang piutang",
        "hutang",
        "utang",
        "piutang",
    }

    if clean in hutang_patterns:
        await hutang_handler(update, context)
        return True

    # ── Budget ───────────────────────────────────────────────────────────────
    budget_patterns = {
        "cek budget",
        "lihat budget",
        "tampilkan budget",
        "cek budget bulan ini",
        "lihat budget bulan ini",
        "tampilkan budget bulan ini",
        "budget bulan ini",
    }

    if clean in budget_patterns:
        summary = get_budget_summary(normalize_month(None))

        if not summary:
            month = normalize_month(None)
            await update.message.reply_text(
                f"📭 Belum ada budget untuk *{format_month_label(month)}*.\n\n"
                "Set budget dengan cara:\n"
                "`budget makan 1.5 juta`\n"
                "`budget transport 300rb`",
                parse_mode="Markdown",
            )
            return True

        month = normalize_month(None)
        total_budget = sum(float(item.get("budget", 0) or 0) for item in summary)
        total_actual = sum(float(item.get("actual", 0) or 0) for item in summary)
        total_remaining = total_budget - total_actual
        total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0

        lines = [f"📊 *Budget {format_month_label(month)}*\n"]
        lines.append(f"💰 Total Budget : *{format_rupiah(total_budget)}*")
        lines.append(f"💸 Realisasi    : *{format_rupiah(total_actual)}*")
        lines.append(f"📌 Sisa         : *{format_rupiah(total_remaining)}*")
        lines.append(f"📈 Terpakai     : *{total_pct:.1f}%*\n")

        for item in summary:
            bar = build_progress_bar(item["pct_used"])
            remaining_label = "Sisa" if item["remaining"] >= 0 else "Over"

            lines.append(
                f"{item['emoji']} *{md_safe(item['category'])}*\n"
                f"  {bar} {item['pct_used']}%\n"
                f"  Pakai: {format_rupiah(item['actual'])} / {format_rupiah(item['budget'])}\n"
                f"  {remaining_label}: {format_rupiah(abs(item['remaining']))}\n"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    # ── Last / histori transaksi ─────────────────────────────────────────────
    last_patterns = {
        "lihat transaksi",
        "lihat transaksi terakhir",
        "tampilkan transaksi",
        "tampilkan transaksi terakhir",
        "lihat histori",
        "lihat history",
        "histori transaksi",
        "history transaksi",
    }

    if clean in last_patterns:
        transactions = get_recent_transactions(limit=10)

        if not transactions:
            await update.message.reply_text("📭 Belum ada transaksi.")
            return True

        last_map = {}
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Terakhir"),
            parse_mode="Markdown",
        )
        return True

    today_patterns = {
        "lihat transaksi hari ini",
        "tampilkan transaksi hari ini",
        "transaksi hari ini",
        "histori hari ini",
        "history hari ini",
    }

    if clean in today_patterns:
        transactions = get_recent_transactions(limit=10, period="today")

        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi hari ini.")
            return True

        last_map = {}
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Hari Ini"),
            parse_mode="Markdown",
        )
        return True

    week_patterns = {
        "lihat transaksi minggu ini",
        "tampilkan transaksi minggu ini",
        "transaksi minggu ini",
        "histori minggu ini",
        "history minggu ini",
    }

    if clean in week_patterns:
        transactions = get_recent_transactions(limit=10, period="week")

        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi minggu ini.")
            return True

        last_map = {}
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Minggu Ini"),
            parse_mode="Markdown",
        )
        return True

    month_patterns = {
        "lihat transaksi bulan ini",
        "tampilkan transaksi bulan ini",
        "transaksi bulan ini",
        "histori bulan ini",
        "history bulan ini",
    }

    if clean in month_patterns:
        transactions = get_recent_transactions(limit=10, period="month")

        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi bulan ini.")
            return True

        last_map = {}
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Bulan Ini"),
            parse_mode="Markdown",
        )
        return True

    # ── Cari transaksi ───────────────────────────────────────────────────────
    # Contoh:
    # cari kopi
    # search kopi
    if clean.startswith("cari ") or clean.startswith("search "):
        keyword = clean.split(" ", 1)[1].strip()

        if not keyword:
            await update.message.reply_text(
                "🔍 Mau cari transaksi apa?\n\n"
                "Contoh:\n"
                "`cari kopi`",
                parse_mode="Markdown",
            )
            return True

        results = search_transactions(keyword)

        if not results:
            await update.message.reply_text(
                f"🔍 Tidak ada transaksi dengan keyword *{md_safe(keyword)}*.",
                parse_mode="Markdown",
            )
            return True

        lines = [f"🔍 *Hasil pencarian: \"{md_safe(keyword)}\"*\n"]

        for t in results:
            icon = "➕" if t.get("type") == "income" else "➖" if t.get("type") == "expense" else "🔄"
            lines.append(
                f"{icon} {md_safe(t.get('date'))} — {md_safe(t.get('description', '-'))}\n"
                f"   *{format_rupiah(float(t.get('amount', 0) or 0))}* | {md_safe(t.get('category', '-'))}"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    return False


# ── Message Handler ──────────────────────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    user_text = update.message.text.strip()

    # ── Layer 0: Local natural intent paling awal ────────────────────────────
    # WAJIB sebelum split/debt parser.
    # Ini untuk mencegah "cek hutang" ketangkep parse_debt_input().
    #
    # Aman karena handle_local_natural_intent() harus return False
    # kalau input mengandung nominal.
    #
    # Jadi:
    # - "cek hutang" -> /hutang
    # - "cek saldo" -> /saldo
    # - "cari kopi" -> search
    # - "Budi minjem 300k" -> tidak ke-handle di sini, lanjut debt parser
    local_natural_handled = await handle_local_natural_intent(
        update,
        context,
        user_text,
    )

    if local_natural_handled:
        return

    has_explicit_separator = bool(re.search(r"[\n\r;,]", user_text))
    input_lines = split_user_inputs(user_text)
    is_multi_input = has_explicit_separator or len(input_lines) > 1

    # Single debt only
    if not is_multi_input:
        full_debt_parsed = parse_debt_input(user_text)
        if full_debt_parsed:
            debt_handled = await debt_message_handler(update, context)
            if debt_handled:
                return

    # Multi / mixed input
    if len(input_lines) > 1:
        mixed_items = []
        failed_lines = []

        for line in input_lines:
            item = parse_mixed_item(line)

            if item["kind"] == "failed":
                failed_lines.append(line)
                continue

            mixed_items.append(item)

        if failed_lines:
            lines = ["🤔 Ada input yang belum bisa saya pahami:\n"]

            for i, line in enumerate(failed_lines, 1):
                lines.append(f"{i}. `{line}`")

            lines.append(
                "\nCoba format seperti:\n"
                "`beli kopi 25rb`\n"
                "`Budi minjem 300k`\n"
                "`minjem Joko 100k`\n"
                "`beli kopi 10k minjem Joko 10k`"
            )

            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
            return

        if mixed_items:
            context.user_data["pending_mixed"] = mixed_items
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_debt_batch", None)

            preview = build_mixed_preview(mixed_items)

            if mixed_needs_account(mixed_items):
                await update.message.reply_text(
                    f"{preview}\n\n💳 Pilih rekening untuk item yang belum punya rekening:",
                    parse_mode="Markdown",
                    reply_markup=account_keyboard("mixed_acc"),
                )
            else:
                await update.message.reply_text(
                    f"{preview}\n\nSimpan semua item ini?",
                    parse_mode="Markdown",
                    reply_markup=confirm_keyboard("mixed"),
                )

            return

    # Single transaction
    parsed = parse_input(user_text)

    if parsed.get("type") == "pending":
        # Layer 3.5: local natural intent shortcut.
        # Ini handle kasus sederhana tanpa Gemini:
        # - cek saldo
        # - cek hutang
        # - lihat budget bulan ini
        # - cari kopi
        # - lihat transaksi hari ini
        local_natural_handled = await handle_local_natural_intent(
            update,
            context,
            user_text,
        )

        if local_natural_handled:
            return

        # Layer 4: Gemini intent router.
        # Dipakai untuk natural command yang lebih fleksibel:
        # - hapus transaksi nomor 2
        # - edit transaksi nomor 2 deskripsinya Kopi susu
        gemini_handled = await handle_gemini_intent(update, context, user_text)

        if gemini_handled:
            return

        # Layer 5: local typo resolver pendek.
        # Contoh:
        # - minguan
        # - mingguannn
        # - detele
        # - bugete
        command_typo_feedback = maybe_text_is_command_typo(user_text)

        if command_typo_feedback:
            await update.message.reply_text(
                command_typo_feedback,
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            build_gemini_fallback_text(),
            parse_mode="Markdown",
        )
        return

    context.user_data["pending_parsed"] = parsed
    context.user_data["pending_raw"] = user_text
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt", None)
    context.user_data.pop("pending_debt_batch", None)
    context.user_data.pop("pending_mixed", None)

    preview = build_preview(parsed)

    if parsed.get("account") or parsed.get("type") == "transfer":
        await update.message.reply_text(
            f"{preview}\n\nSimpan transaksi ini?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("pending"),
        )
    else:
        await update.message.reply_text(
            f"{preview}\n\n💳 Dari rekening mana?",
            parse_mode="Markdown",
            reply_markup=account_keyboard("acc"),
        )

async def last_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /last
    /last 20
    /last today
    /last week
    /last month
    /last 2026-06
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    args = context.args

    limit = 10
    period = None
    month = None
    title = "Transaksi Terakhir"

    if args:
        arg1 = args[0].strip().lower()

        if arg1.isdigit():
            limit = min(max(int(arg1), 1), 30)
            title = f"{limit} Transaksi Terakhir"

        elif arg1 in ["today", "hariini", "harian"]:
            period = "today"
            title = "Transaksi Hari Ini"

        elif arg1 in ["week", "minggu", "mingguan"]:
            period = "week"
            title = "Transaksi Minggu Ini"

        elif arg1 in ["month", "bulan", "bulanan"]:
            period = "month"
            title = "Transaksi Bulan Ini"

        elif re.fullmatch(r"20\d{2}-(0?[1-9]|1[0-2])", arg1):
            year, month_num = arg1.split("-")
            month = f"{year}-{int(month_num):02d}"
            title = f"Transaksi {month}"

        else:
            await update.message.reply_text(
                "❌ Format /last tidak dikenali.\n\n"
                "Contoh:\n"
                "`/last`\n"
                "`/last 20`\n"
                "`/last today`\n"
                "`/last week`\n"
                "`/last month`\n"
                "`/last 2026-06`",
                parse_mode="Markdown",
            )
            return

    transactions = get_recent_transactions(
        limit=limit,
        period=period,
        month=month,
    )

    if not transactions:
        await update.message.reply_text(
            f"📭 Tidak ada transaksi untuk filter: *{title}*",
            parse_mode="Markdown",
        )
        return

    last_map = {}

    for i, txn in enumerate(transactions, 1):
        last_map[str(i)] = {
            "id": str(txn.get("id", "")),
            "row_index": int(txn.get("_row_index")),
        }

    context.user_data["last_txn_map"] = last_map

    await update.message.reply_text(
        build_last_transactions_text(transactions, title),
        parse_mode="Markdown",
    )


async def delete_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /delete_txn 1
    /delete_txn 1 3 5
    /delete_txn txn_...
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    refs = context.args

    if not refs:
        await update.message.reply_text(
            "❌ Masukkan nomor transaksi dari `/last` atau transaction ID.\n\n"
            "Contoh:\n"
            "`/last today`\n"
            "`/delete_txn 1`\n"
            "`/delete_txn 1 3 5`\n"
            "`/delete_txn txn_20260609_231132_123456_abcd1234`",
            parse_mode="Markdown",
        )
        return

    resolved = resolve_txn_refs_from_last(context, refs)

    invalid_refs = resolved.get("invalid_refs", [])

    if invalid_refs and not resolved["row_indices"] and not resolved["txn_ids"]:
        await update.message.reply_text(
            "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
            "Jalankan dulu:\n"
            "`/last`\n\n"
            "Lalu hapus dengan:\n"
            "`/delete_txn 1`\n"
            "`/delete_txn 1 3 5`",
            parse_mode="Markdown",
        )
        return

    preview = preview_delete_transactions_by_refs(
        row_indices=resolved["row_indices"],
        txn_ids=resolved["txn_ids"],
    )

    if invalid_refs:
        preview["missing_rows"] = preview.get("missing_rows", []) + invalid_refs

    if not preview.get("deletable"):
        await update.message.reply_text(
            build_delete_preview_text(preview),
            parse_mode="Markdown",
        )
        return

    context.user_data["pending_delete_refs"] = {
        "row_indices": [
            int(txn.get("_row_index"))
            for txn in preview.get("deletable", [])
            if txn.get("_row_index")
        ],
        "txn_ids": [],
    }

    await update.message.reply_text(
        build_delete_preview_text(preview),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("delete_txns"),
    )

def parse_edit_updates(args: list[str]) -> dict:
    """
    Parse argumen edit.

    Format utama:
    amount=15000
    account=Cash
    category="Food & Beverage"
    desc="Kopi susu"
    date=2026-06-10

    Shortcut:
    /edit_txn 2 15000
    -> amount=15000
    """
    if not args:
        return {}

    if len(args) == 1:
        first = args[0].strip()

        if re.fullmatch(r"\d+(?:[.,]\d+)?", first):
            return {
                "amount": first.replace(",", ".")
            }

    updates = {}

    for arg in args:
        if "=" not in arg:
            raise ValueError(
                f"Argumen `{arg}` tidak valid. Gunakan format key=value."
            )

        key, value = arg.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key or value == "":
            raise ValueError(
                f"Argumen `{arg}` tidak valid. Gunakan format key=value."
            )

        updates[key] = value

    return updates


def build_edit_preview_text(preview: dict) -> str:
    old_txn = preview.get("old_txn", {})
    new_txn = preview.get("new_txn", {})
    updates = preview.get("updates", {})
    net_deltas = preview.get("net_deltas", {})

    lines = ["✏️ *Preview Edit Transaksi*\n"]

    lines.append("*Sebelum:*")
    lines.append(
        f"• {old_txn.get('date')} — *{old_txn.get('description') or '-'}*\n"
        f"  {format_rupiah(float(old_txn.get('amount', 0) or 0))} | "
        f"{old_txn.get('category') or '-'} | {old_txn.get('account') or '-'}"
    )

    lines.append("\n*Sesudah:*")
    lines.append(
        f"• {new_txn.get('date')} — *{new_txn.get('description') or '-'}*\n"
        f"  {format_rupiah(float(new_txn.get('amount', 0) or 0))} | "
        f"{new_txn.get('category') or '-'} | {new_txn.get('account') or '-'}"
    )

    if updates:
        lines.append("\n*Field yang diubah:*")
        for field, value in updates.items():
            lines.append(f"• {field}: `{value}`")

    if net_deltas:
        lines.append("\n*Efek ke saldo:*")
        for account, delta in net_deltas.items():
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {account}: {sign}{format_rupiah(abs(delta))}")
    else:
        lines.append("\n*Efek ke saldo:*")
        lines.append("• Tidak ada perubahan saldo")

    lines.append("\nSimpan perubahan ini?")

    return "\n".join(lines)

async def edit_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /edit_txn 2 amount=15000
    /edit_txn 2 amount=15000 desc="Kopi susu"
    /edit_txn 2 account=BRI category="Food & Beverage"
    /edit_txn txn_... amount=20000
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    raw_text = update.message.text.strip()

    try:
        parts = shlex.split(raw_text)
    except Exception:
        await update.message.reply_text(
            "❌ Format edit tidak valid. Kalau ada spasi, pakai tanda kutip.\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`",
            parse_mode="Markdown",
        )
        return

    # parts[0] = /edit_txn
    args = parts[1:]

    if len(args) < 2:
        await update.message.reply_text(
            "❌ Format edit belum lengkap.\n\n"
            "Contoh:\n"
            "`/last`\n"
            "`/edit_txn 2 amount=15000`\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`\n"
            "`/edit_txn 2 account=BRI category=\"Food & Beverage\"`\n"
            "`/edit_txn 2 15000`",
            parse_mode="Markdown",
        )
        return

    ref = args[0]
    update_args = args[1:]

    resolved = resolve_txn_refs_from_last(context, [ref])

    if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
        await update.message.reply_text(
            "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
            "Jalankan dulu:\n"
            "`/last`\n\n"
            "Lalu edit dengan:\n"
            "`/edit_txn 2 amount=15000`",
            parse_mode="Markdown",
        )
        return

    try:
        updates = parse_edit_updates(update_args)
    except Exception as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000`\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`\n"
            "`/edit_txn 2 account=BRI category=\"Food & Beverage\"`",
            parse_mode="Markdown",
        )
        return

    if not updates:
        await update.message.reply_text(
            "❌ Tidak ada field yang diedit.\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000`",
            parse_mode="Markdown",
        )
        return

    row_index = resolved["row_indices"][0] if resolved["row_indices"] else None
    txn_id = resolved["txn_ids"][0] if resolved["txn_ids"] else None

    preview = preview_edit_transaction_by_ref(
        updates=updates,
        row_index=row_index,
        txn_id=txn_id,
    )

    if not preview.get("success"):
        await update.message.reply_text(
            f"❌ {preview.get('message')}",
            parse_mode="Markdown",
        )
        return

    context.user_data["pending_edit_txn"] = {
        "row_index": row_index,
        "txn_id": txn_id,
        "updates": updates,
    }

    await update.message.reply_text(
        build_edit_preview_text(preview),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("edit_txn"),
    )


# ── Callback Handler ─────────────────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("debt_batch_acc:"):
        account = data.split(":")[1]
        debt_batch = context.user_data.get("pending_debt_batch")

        if not debt_batch:
            await query.edit_message_text("❌ Sesi batch debt expired. Coba input ulang.")
            return

        prepared_batch = []
        failed_items = []

        for item in debt_batch:
            parsed = item["parsed"]
            raw = item["raw"]

            intent = parsed.get("intent")
            person = parsed.get("person_name")

            if not person:
                failed_items.append({
                    "raw": raw,
                    "message": "Nama orang tidak terdeteksi.",
                })
                continue

            if intent == "add_payment":
                debts = get_debt_by_person(person)

                if not debts:
                    failed_items.append({
                        "raw": raw,
                        "message": f"Tidak ada utang/piutang aktif dengan {person}.",
                    })
                    continue

                if len(debts) > 1:
                    failed_items.append({
                        "raw": raw,
                        "message": f"Ada lebih dari 1 saldo aktif dengan {person}. Rapikan data legacy dulu.",
                    })
                    continue

                parsed["target_debt_id"] = debts[0].get("id")
                parsed["debt_type_for_payment"] = debts[0].get("type")

            parsed["account"] = account
            prepared_batch.append({
                "parsed": parsed,
                "raw": raw,
            })

        if not prepared_batch:
            lines = ["❌ *Batch debt tidak bisa diproses.*\n"]

            if failed_items:
                lines.append("*Gagal:*")
                for item in failed_items:
                    lines.append(f"• `{item['raw']}` — {item['message']}")

            await query.edit_message_text(
                "\n".join(lines),
                parse_mode="Markdown",
            )
            context.user_data.pop("pending_debt_batch", None)
            return

        context.user_data["pending_debt_batch"] = prepared_batch

        preview = build_debt_batch_confirm_preview(
            prepared_batch,
            account,
        )

        if failed_items:
            preview += "\n\n⚠️ *Catatan item yang tidak masuk preview:*"
            for item in failed_items:
                preview += f"\n• `{item['raw']}` — {item['message']}"

        await query.edit_message_text(
            preview,
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("debt_batch"),
        )
        return

    if data.startswith("debt_acc:"):
        account = data.split(":")[1]
        debt_parsed = context.user_data.get("pending_debt")

        if not debt_parsed:
            await query.edit_message_text("❌ Sesi debt expired. Coba input ulang.")
            return

        intent = debt_parsed.get("intent")
        person = debt_parsed.get("person_name")
        debt_type_for_payment = None

        if intent == "add_payment":
            debts = get_debt_by_person(person)

            if not debts:
                await query.edit_message_text(
                    f"❓ Tidak ada utang/piutang aktif dengan *{person}*.",
                    parse_mode="Markdown",
                )
                context.user_data.pop("pending_debt", None)
                return

            if len(debts) > 1:
                await query.edit_message_text(
                    f"⚠️ Ada lebih dari 1 saldo aktif dengan *{person}*.\n\n"
                    f"Data lama masih duplicate. Rapikan dulu via /hutang "
                    f"atau nanti kita buat fitur merge debt legacy.",
                    parse_mode="Markdown",
                )
                context.user_data.pop("pending_debt", None)
                return

            debt_type_for_payment = debts[0].get("type")
            debt_parsed["target_debt_id"] = debts[0].get("id")
            debt_parsed["debt_type_for_payment"] = debt_type_for_payment

        debt_parsed["account"] = account
        context.user_data["pending_debt"] = debt_parsed

        preview = build_debt_confirm_preview(
            debt_parsed,
            account,
            debt_type_for_payment=debt_type_for_payment,
        )

        await query.edit_message_text(
            preview,
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("debt"),
        )
        return

    if data.startswith("mixed_acc:"):
        account = data.split(":")[1]
        mixed_items = context.user_data.get("pending_mixed")

        if not mixed_items:
            await query.edit_message_text("❌ Sesi mixed input expired. Coba input ulang.")
            return

        prepared_items = []
        failed_items = []

        for item in mixed_items:
            parsed = item["parsed"]
            raw = item["raw"]

            if item["kind"] == "transaction":
                if needs_account(parsed):
                    parsed["account"] = account

                prepared_items.append({
                    "kind": "transaction",
                    "parsed": parsed,
                    "raw": raw,
                })

            elif item["kind"] == "debt":
                intent = parsed.get("intent")
                person = parsed.get("person_name")

                if not person:
                    failed_items.append({
                        "raw": raw,
                        "message": "Nama orang tidak terdeteksi.",
                    })
                    continue

                if intent == "add_payment":
                    debts = get_debt_by_person(person)

                    if not debts:
                        failed_items.append({
                            "raw": raw,
                            "message": f"Tidak ada utang/piutang aktif dengan {person}.",
                        })
                        continue

                    if len(debts) > 1:
                        failed_items.append({
                            "raw": raw,
                            "message": f"Ada lebih dari 1 saldo aktif dengan {person}. Rapikan data legacy dulu.",
                        })
                        continue

                    parsed["target_debt_id"] = debts[0].get("id")
                    parsed["debt_type_for_payment"] = debts[0].get("type")

                parsed["account"] = account

                prepared_items.append({
                    "kind": "debt",
                    "parsed": parsed,
                    "raw": raw,
                })

        if not prepared_items:
            lines = ["❌ *Mixed input tidak bisa diproses.*\n"]

            if failed_items:
                lines.append("*Gagal:*")
                for item in failed_items:
                    lines.append(f"• `{item['raw']}` — {item['message']}")

            await query.edit_message_text(
                "\n".join(lines),
                parse_mode="Markdown",
            )
            context.user_data.pop("pending_mixed", None)
            return

        context.user_data["pending_mixed"] = prepared_items

        preview = build_mixed_preview(prepared_items)

        if failed_items:
            preview += "\n\n⚠️ *Catatan item yang tidak masuk preview:*"
            for item in failed_items:
                preview += f"\n• `{item['raw']}` — {item['message']}"

        await query.edit_message_text(
            f"{preview}\n\nSimpan semua item ini?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("mixed"),
        )
        return
    
    if data.startswith("batch_acc:"):
        account = data.split(":")[1]
        batch = context.user_data.get("pending_batch")

        if not batch:
            await query.edit_message_text("❌ Sesi batch expired. Coba input ulang.")
            return

        for item in batch:
            parsed = item["parsed"]
            if needs_account(parsed):
                parsed["account"] = account

        context.user_data["pending_batch"] = batch
        preview = build_batch_preview(batch)

        await query.edit_message_text(
            f"{preview}\n\nSimpan semua transaksi ini?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("batch"),
        )
        return

    if data.startswith("acc:"):
        account = data.split(":")[1]
        parsed = context.user_data.get("pending_parsed")

        if not parsed:
            await query.edit_message_text("❌ Sesi expired. Coba input ulang.")
            return

        parsed["account"] = account
        context.user_data["pending_parsed"] = parsed
        preview = build_preview(parsed)

        await query.edit_message_text(
            f"{preview}\n\nSimpan transaksi ini?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("pending"),
        )
        return

    if data.startswith("confirm:"):
        confirm_target = data.split(":")[1] if ":" in data else ""
        if confirm_target == "edit_txn":
            pending_edit = context.user_data.get("pending_edit_txn")

            if not pending_edit:
                await query.edit_message_text(
                    "❌ Sesi edit transaksi expired. Coba ulangi `/last`."
                )
                return

            await query.edit_message_text(
                "⏳ *Sedang mengedit transaksi dan memperbaiki saldo...*",
                parse_mode="Markdown",
            )

            result = edit_transaction_by_ref(
                updates=pending_edit.get("updates", {}),
                row_index=pending_edit.get("row_index"),
                txn_id=pending_edit.get("txn_id"),
            )

            if not result.get("success"):
                await query.edit_message_text(
                    f"❌ *Gagal edit transaksi.*\n{result.get('message')}",
                    parse_mode="Markdown",
                )
                context.user_data.pop("pending_edit_txn", None)
                return

            old_txn = result.get("old_txn", {})
            new_txn = result.get("new_txn", {})
            net_deltas = result.get("net_deltas", {})
            new_balances = result.get("new_balances", {})

            lines = ["✅ *Transaksi berhasil diedit!*\n"]

            lines.append("*Sebelum:*")
            lines.append(
                f"• {old_txn.get('date')} — {old_txn.get('description') or '-'}\n"
                f"  {format_rupiah(float(old_txn.get('amount', 0) or 0))} | "
                f"{old_txn.get('category') or '-'} | {old_txn.get('account') or '-'}"
            )

            lines.append("\n*Sesudah:*")
            lines.append(
                f"• {new_txn.get('date')} — {new_txn.get('description') or '-'}\n"
                f"  {format_rupiah(float(new_txn.get('amount', 0) or 0))} | "
                f"{new_txn.get('category') or '-'} | {new_txn.get('account') or '-'}"
            )

            if net_deltas:
                lines.append("\n🔁 *Penyesuaian saldo:*")
                for account, delta in net_deltas.items():
                    sign = "+" if delta >= 0 else "-"
                    lines.append(f"• {account}: {sign}{format_rupiah(abs(delta))}")

            if new_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                for account, balance in new_balances.items():
                    lines.append(f"• {account}: *{format_rupiah(balance)}*")

            await query.edit_message_text(
                "\n".join(lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_edit_txn", None)
            return
        if confirm_target == "delete_txns":
            pending_refs = context.user_data.get("pending_delete_refs", {})

            row_indices = pending_refs.get("row_indices", [])
            txn_ids = pending_refs.get("txn_ids", [])

            if not row_indices and not txn_ids:
                await query.edit_message_text(
                    "❌ Sesi hapus transaksi expired. Coba ulangi `/last`."
                )
                return

            await query.edit_message_text(
                "⏳ *Sedang menghapus transaksi dan memperbaiki saldo...*",
                parse_mode="Markdown",
            )

            result = delete_transactions_by_refs(
                row_indices=row_indices,
                txn_ids=txn_ids,
            )

            if not result.get("success"):
                lines = [
                    f"❌ *Gagal menghapus transaksi.*\n{result.get('message')}"
                ]

                if result.get("blocked"):
                    lines.append("\n🚫 *Transaksi diblok:*")
                    for txn in result["blocked"]:
                        lines.append(
                            f"• Row {txn.get('_row_index', '-')} — "
                            f"{txn.get('date')} — {txn.get('description') or '-'} "
                            f"({txn.get('category') or '-'})"
                        )

                if result.get("missing_ids"):
                    lines.append("\n❓ *ID tidak ditemukan:*")
                    for txn_id in result["missing_ids"]:
                        lines.append(f"• `{txn_id}`")

                if result.get("missing_rows"):
                    lines.append("\n❓ *Row tidak ditemukan:*")
                    for row in result["missing_rows"]:
                        lines.append(f"• `{row}`")

                await query.edit_message_text(
                    "\n".join(lines),
                    parse_mode="Markdown",
                )

                context.user_data.pop("pending_delete_refs", None)
                context.user_data.pop("pending_delete_txn_ids", None)
                return

            lines = [
                "✅ *Transaksi berhasil dihapus!*",
                f"🗑️ Terhapus: *{result.get('deleted_count', 0)} transaksi*",
            ]

            deleted_ids = result.get("deleted_ids", [])
            if deleted_ids:
                lines.append("\n🔖 *ID terhapus:*")
                for txn_id in deleted_ids:
                    lines.append(f"• `{short_txn_id(txn_id)}`")

            new_balances = result.get("new_balances", {})
            if new_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                for account, balance in new_balances.items():
                    lines.append(f"• {account}: *{format_rupiah(balance)}*")

            if result.get("blocked"):
                lines.append("\n🚫 *Diblok karena debt cashflow:*")
                for txn in result["blocked"]:
                    lines.append(
                        f"• Row {txn.get('_row_index', '-')} — "
                        f"{txn.get('date')} — {txn.get('description') or '-'} "
                        f"({txn.get('category') or '-'})"
                    )

            if result.get("missing_ids"):
                lines.append("\n❓ *ID tidak ditemukan:*")
                for txn_id in result["missing_ids"]:
                    lines.append(f"• `{txn_id}`")

            if result.get("missing_rows"):
                lines.append("\n❓ *Row tidak ditemukan:*")
                for row in result["missing_rows"]:
                    lines.append(f"• `{row}`")

            await query.edit_message_text(
                "\n".join(lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_delete_refs", None)
            context.user_data.pop("pending_delete_txn_ids", None)
            return
    
        if confirm_target == "mixed":
            mixed_items = context.user_data.get("pending_mixed")

            if not mixed_items:
                await query.edit_message_text("❌ Sesi mixed input expired. Coba input ulang.")
                return

            await query.edit_message_text(
                "⏳ *Sedang menyimpan semua item...*",
                parse_mode="Markdown",
            )

            normal_transaction_items = []
            debt_transaction_items = []
            failed_items = []
            result_lines = ["✅ *Mixed input diproses!*\n"]

            debt_success_count = 0
            transaction_success_count = 0

            for i, item in enumerate(mixed_items, 1):
                parsed = item["parsed"]
                raw = item["raw"]

                if item["kind"] == "transaction":
                    normal_transaction_items.append({
                        "parsed": parsed,
                        "raw": raw,
                    })
                    continue

                if item["kind"] != "debt":
                    failed_items.append({
                        "raw": raw,
                        "message": "Jenis item tidak valid.",
                    })
                    continue

                intent = parsed.get("intent")
                person = parsed.get("person_name")
                amount = parsed.get("amount")
                description = parsed.get("description") or ""
                account = parsed.get("account")
                debt_type_for_payment = parsed.get("debt_type_for_payment")

                if not person:
                    failed_items.append({
                        "raw": raw,
                        "message": "Nama orang tidak terdeteksi.",
                    })
                    continue

                debt_result = None

                if intent == "add_payable":
                    debt_result = add_debt("payable", person, amount, description)

                elif intent == "add_receivable":
                    debt_result = add_debt("receivable", person, amount, description)

                elif intent == "add_payment":
                    target_debt_id = parsed.get("target_debt_id")

                    if not target_debt_id:
                        failed_items.append({
                            "raw": raw,
                            "message": "Target debt tidak ditemukan.",
                        })
                        continue

                    debt_result = add_payment(target_debt_id, amount)

                else:
                    failed_items.append({
                        "raw": raw,
                        "message": "Intent debt tidak valid.",
                    })
                    continue

                if not debt_result or not debt_result.get("success"):
                    failed_items.append({
                        "raw": raw,
                        "message": debt_result.get("message") if debt_result else "Unknown error",
                    })
                    continue

                debt_success_count += 1

                if intent in ["add_payable", "add_receivable"]:
                    if debt_result.get("is_settled"):
                        result_lines.append(f"{i}. ✅ Debt *{person}* impas/lunas")
                    else:
                        direction = (
                            "🔴 Utang Anda"
                            if debt_result["type"] == "payable"
                            else "🟢 Piutang Anda"
                        )
                        result_lines.append(
                            f"{i}. {direction} dengan *{debt_result['person_name']}*\n"
                            f"   💰 Saldo: *{format_rupiah(debt_result['remaining'])}*"
                        )

                    debt_txn = build_debt_cashflow_transaction(
                        parsed,
                        account,
                    )

                elif intent == "add_payment":
                    if debt_result.get("is_settled"):
                        result_lines.append(f"{i}. ✅ Debt *{person}* lunas")
                    else:
                        direction = (
                            "🔴 Utang Anda"
                            if debt_type_for_payment == "payable"
                            else "🟢 Piutang Anda"
                        )
                        result_lines.append(
                            f"{i}. 💸 Pembayaran *{person}*\n"
                            f"   📌 Posisi: {direction}\n"
                            f"   📊 Sisa: *{format_rupiah(debt_result['remaining'])}*"
                        )

                    debt_txn = build_debt_cashflow_transaction(
                        parsed,
                        account,
                        debt_type_for_payment=debt_type_for_payment,
                    )

                else:
                    debt_txn = {"type": "pending"}

                if debt_txn.get("type") != "pending":
                    debt_transaction_items.append({
                        "parsed": debt_txn,
                        "raw": raw,
                    })

            all_transaction_items = normal_transaction_items + debt_transaction_items

            transaction_result = None
            if all_transaction_items:
                transaction_result = save_transactions_batch(all_transaction_items)

            if transaction_result:
                transaction_success_count = transaction_result.get("success_count", 0)

                result_lines.append("")
                result_lines.append(f"📝 Transactions tersimpan: *{transaction_success_count} item*")
                result_lines.append(f"💸 Debt diproses: *{debt_success_count} item*")

                new_balances = transaction_result.get("new_balances", {})
                if new_balances:
                    result_lines.append("\n💳 *Saldo terbaru:*")
                    for account_name, balance in new_balances.items():
                        result_lines.append(f"• {account_name}: *{format_rupiah(balance)}*")

                tx_failed = transaction_result.get("failed_items", [])
                if tx_failed:
                    failed_items.extend(tx_failed)

                if transaction_result.get("message") and transaction_result.get("message") != "ok":
                    result_lines.append(f"\n⚠️ {transaction_result['message']}")

            if failed_items:
                result_lines.append("\n❌ *Catatan/Gagal:*")
                for item in failed_items:
                    result_lines.append(f"• `{item['raw']}` — {item['message']}")

            await query.edit_message_text(
                "\n".join(result_lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_mixed", None)
            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_debt_batch", None)
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            return
        
        if confirm_target == "batch":
            batch = context.user_data.get("pending_batch")

            if not batch:
                await query.edit_message_text("❌ Sesi batch expired. Coba input ulang.")
                return

            await query.edit_message_text(
                "⏳ *Sedang menyimpan semua transaksi...*",
                parse_mode="Markdown",
            )

            result = save_transactions_batch(batch)

            lines = [
                "✅ *Batch selesai diproses!*",
                f"📝 Berhasil: {result.get('success_count', 0)} transaksi",
            ]

            saved_ids = result.get("saved_ids", [])
            if saved_ids:
                lines.append("\n🔖 *ID tersimpan:*")
                for txn_id in saved_ids:
                    lines.append(f"• `{txn_id}`")

            new_balances = result.get("new_balances", {})
            if new_balances:
                lines.append("\n💳 *Saldo terbaru:*")
                for account_name, balance in new_balances.items():
                    lines.append(f"• {account_name}: *{format_rupiah(balance)}*")

            failed_items = result.get("failed_items", [])
            if failed_items:
                lines.append("\n❌ *Catatan/Gagal:*")
                for item in failed_items:
                    lines.append(f"• `{item['raw']}` — {item['message']}")

            budget_messages = []
            checked_categories = set()

            for item in batch:
                parsed = item["parsed"]
                category = parsed.get("category")

                if parsed.get("type") != "expense" or not category:
                    continue

                if category in checked_categories:
                    continue

                checked_categories.add(category)

                budget_check = check_budget_after_transaction(category)
                if budget_check and budget_check.get("alert"):
                    budget_messages.append(
                        f"{budget_check['emoji']} *Budget {category}*: "
                        f"{budget_check['pct_used']}% terpakai"
                    )

            if budget_messages:
                lines.append("\n⚠️ *Budget Alert:*")
                lines.extend(budget_messages)

            if result.get("message") and result.get("message") != "ok":
                lines.append(f"\n⚠️ {result['message']}")

            await query.edit_message_text(
                "\n".join(lines),
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_debt_batch", None)
            return

        parsed = context.user_data.get("pending_parsed")
        raw = context.user_data.get("pending_raw", "")

        if not parsed:
            await query.edit_message_text("❌ Sesi expired. Coba input ulang.")
            return

        await query.edit_message_text(
            "⏳ *Sedang menyimpan transaksi...*",
            parse_mode="Markdown",
        )

        result = save_transaction(parsed, raw_input=raw)

        if result["success"]:
            balance_info = ""
            if result.get("new_balance") is not None:
                balance_info = (
                    f"\n💳 Saldo {parsed.get('account') or parsed.get('to_account')}: "
                    f"*{format_rupiah(result['new_balance'])}*"
                )

            budget_info = ""
            if parsed.get("type") == "expense" and parsed.get("category"):
                budget_check = check_budget_after_transaction(parsed["category"])
                if budget_check:
                    budget_info = (
                        f"\n\n{budget_check['emoji']} *Budget {parsed['category']}*\n"
                        f"Terpakai: {format_rupiah(budget_check['actual'])} "
                        f"/ {format_rupiah(budget_check['budget'])} "
                        f"({budget_check['pct_used']}%)\n"
                        f"Sisa: {format_rupiah(budget_check['remaining'])}"
                    )
                    if budget_check["alert"]:
                        budget_info += f"\n\n{budget_check['alert_msg']}"

            await query.edit_message_text(
                f"✅ *Transaksi tersimpan!*\n"
                f"🔖 ID: `{result['transaction_id']}`"
                f"{balance_info}"
                f"{budget_info}",
                parse_mode="Markdown",
            )

            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_debt_batch", None)
            return

        await query.edit_message_text(
            f"❌ Gagal menyimpan: {result['message']}"
        )
        return

    if data.startswith("cancel"):
        context.user_data.pop("pending_parsed", None)
        context.user_data.pop("pending_raw", None)
        context.user_data.pop("pending_batch", None)
        context.user_data.pop("pending_debt", None)
        context.user_data.pop("pending_debt_batch", None)
        context.user_data.pop("pending_mixed", None)
        context.user_data.pop("pending_payment", None)
        context.user_data.pop("pending_delete_refs", None)
        context.user_data.pop("pending_delete_txn_ids", None)
        context.user_data.pop("pending_edit_txn", None)

        await query.edit_message_text("❌ Input dibatalkan.")
        return

    if data.startswith("pay_debt:"):
        parts = data.split(":")
        debt_id = parts[1]
        amount = float(parts[2])

        result = add_payment(debt_id, amount)

        if result["success"]:
            pending = context.user_data.get("pending_payment", {})
            person = pending.get("person", "")

            if result["is_settled"]:
                msg = (
                    f"✅ *Hutang ke {person} LUNAS!*\n"
                    f"💰 Dibayar: {format_rupiah(amount)}"
                )
            else:
                msg = (
                    f"✅ *Pembayaran dicatat!*\n\n"
                    f"👤 Kepada : {person}\n"
                    f"💰 Dibayar: {format_rupiah(amount)}\n"
                    f"📊 Sisa   : {format_rupiah(result['remaining'])}"
                )

            await query.edit_message_text(msg, parse_mode="Markdown")
            context.user_data.pop("pending_payment", None)
            return

        await query.edit_message_text(
            f"❌ Gagal: {result['message']}"
        )
        return

    await query.edit_message_text("❌ Tombol tidak dikenali atau sesi sudah tidak valid.")

