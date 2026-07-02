"""Telegram Application builder. This keeps polling and webhook mode using the same registered handlers."""

from __future__ import annotations

from datetime import time
from functools import wraps
from zoneinfo import ZoneInfo

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.bot.handlers import (
    ask_handler,
    asset_add_handler,
    asset_off_handler,
    asset_update_handler,
    assets_handler,
    audit_handler,
    budget_handler,
    budget_history_handler,
    pending_add_handler,
    pending_cancel_handler,
    pending_handler,
    pending_paid_handler,
    bulanan_handler,
    callback_handler,
    cari_handler,
    coach_handler,
    debt_edit_handler,
    debt_settle_handler,
    debt_void_handler,
    delete_txn_handler,
    edit_txn_handler,
    error_handler,
    examples_handler,
    export_handler,
    harian_handler,
    health_handler,
    help_handler,
    hutang_handler,
    image_handler,
    insight_handler,
    last_handler,
    message_handler,
    mingguan_handler,
    networth_handler,
    networth_history_handler,
    networth_snapshot_handler,
    recurring_add_handler,
    recurring_edit_handler,
    recurring_handler,
    recurring_off_handler,
    recurring_run_handler,
    rekening_handler,
    ringkasan_hutang_handler,
    saldo_handler,
    scheduled_export_transactions,
    set_budget_handler,
    start_handler,
    transaksi_handler,
    unknown_command_handler,
)
from app.config import ALLOWED_USER_ID, TELEGRAM_BOT_TOKEN
from app.sheets.client import sheets_transaction


# This wrapper keeps one Telegram action inside a best-effort Sheets rollback context.
# Implementation note for this project-specific finance flow.

def atomic_bot_handler(callback):
    """Wrap a Telegram handler in a Sheets transaction so failed writes can be rolled back."""

    @wraps(callback)
    async def wrapped(update, context, *args, **kwargs):
        """Helper for wrapped in the Telegram bot flow."""
        with sheets_transaction(label=getattr(callback, "__name__", "telegram_handler")):
            return await callback(update, context, *args, **kwargs)

    return wrapped


# Handler order matters: specific commands must be registered before generic message handlers.

def register_handlers(telegram_app: Application) -> Application:
    """Register all command, message, callback, and error handlers in one place."""

    def add_command(command_name: str, callback):
        """Helper for add command in the Telegram bot flow."""
        telegram_app.add_handler(CommandHandler(command_name, atomic_bot_handler(callback)))

    def add_message(message_filter, callback):
        """Helper for add message in the Telegram bot flow."""
        telegram_app.add_handler(MessageHandler(message_filter, atomic_bot_handler(callback)))

    # Basic onboarding and bot-check commands.
    add_command("start", start_handler)
    add_command("help", help_handler)
    add_command("examples", examples_handler)
    add_command("contoh", examples_handler)
    add_command("health", health_handler)

    # Common transaction and reporting commands.
    add_command("saldo", saldo_handler)
    add_command("rekening", rekening_handler)
    add_command("harian", harian_handler)
    add_command("mingguan", mingguan_handler)
    add_command("bulanan", bulanan_handler)
    add_command("cari", cari_handler)
    add_command("last", last_handler)
    add_command("transaksi", transaksi_handler)
    add_command("delete_txn", delete_txn_handler)
    add_command("edit_txn", edit_txn_handler)

    # Data export command for backup or further analysis.
    add_command("download_data", export_handler)
    add_command("export", export_handler)

    # Budget command note: regex handling supports natural phrases such as `budget makan 1jt`.
    add_command("budget", budget_handler)
    add_command("budget_history", budget_history_handler)
    add_message(filters.Regex(r"(?i)^budget\b"), set_budget_handler)

    # Pending expense note: planned items should not be recorded as actual transactions yet.
    add_command("pending", pending_handler)
    add_command("pending_add", pending_add_handler)
    add_command("rencana", pending_add_handler)
    add_command("pending_paid", pending_paid_handler)
    add_command("pending_cancel", pending_cancel_handler)
    add_message(filters.Regex(r"(?i)^(pending|rencana)\b"), pending_add_handler)

    # Debt commands for payable, receivable, and settlement flows.
    add_command("hutang", hutang_handler)
    add_command("ringkasan_hutang", ringkasan_hutang_handler)
    add_command("debt_void", debt_void_handler)
    add_command("debt_edit", debt_edit_handler)
    add_command("debt_settle", debt_settle_handler)

    # Recurring command note: this handles repeated bills or scheduled transactions.
    add_command("recurring", recurring_handler)
    add_command("recurring_add", recurring_add_handler)
    add_command("recurring_run", recurring_run_handler)
    add_command("recurring_edit", recurring_edit_handler)
    add_command("recurring_off", recurring_off_handler)

    # Net worth and asset management commands.
    add_command("networth", networth_handler)
    add_command("assets", assets_handler)
    add_command("asset_add", asset_add_handler)
    add_command("asset_update", asset_update_handler)
    add_command("asset_off", asset_off_handler)
    add_command("networth_snapshot", networth_snapshot_handler)
    add_command("networth_history", networth_history_handler)

    # Data-based AI insight commands. These commands are read-only.
    add_command("insight", insight_handler)
    add_command("ask", ask_handler)
    add_command("audit", audit_handler)
    add_command("coach", coach_handler)

    # Handler order matters: specific commands must be registered before generic message handlers.
    add_message(filters.COMMAND, unknown_command_handler)
    add_message(filters.PHOTO | filters.Document.IMAGE, image_handler)
    add_message(filters.TEXT & ~filters.COMMAND, message_handler)

    telegram_app.add_handler(CallbackQueryHandler(atomic_bot_handler(callback_handler)))
    telegram_app.add_error_handler(error_handler)

    return telegram_app


async def scheduled_data_export(context):
    """Run the scheduled transaction export job from the Telegram JobQueue."""
    try:
        await scheduled_export_transactions(
            bot=context.bot,
            chat_id=int(ALLOWED_USER_ID),
            period=None,
        )
    except Exception as exc:
        print(f"[AUTO EXPORT ERROR] {exc}")


def register_job_queue_jobs(telegram_app: Application) -> Application:
    """Register daily jobs managed by python-telegram-bot JobQueue."""
    if telegram_app.job_queue:
        telegram_app.job_queue.run_daily(
            scheduled_data_export,
            time=time(hour=23, minute=55, tzinfo=ZoneInfo("Asia/Jakarta")),
            name="daily_data_export",
        )
    else:
        print("⚠️ JobQueue belum aktif. Install: python-telegram-bot[job-queue]")
    return telegram_app


def build_telegram_app() -> Application:
    """Build the Telegram Application with all handlers and scheduled jobs."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi di .env.")

    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    register_handlers(telegram_app)
    register_job_queue_jobs(telegram_app)
    return telegram_app
