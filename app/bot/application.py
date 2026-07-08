"""Telegram Application builder. This module registers commands, message handlers, callbacks, and scheduled jobs in one place."""

# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import datetime so this module can use its helpers.
from datetime import time
# Import functools so this module can use its helpers.
from functools import wraps
# Import zoneinfo so this module can use its helpers.
from zoneinfo import ZoneInfo

# Import telegram.ext so this module can use its helpers.
from telegram.ext import (
    # Include this value in the surrounding collection or call.
    Application,
    # Include this value in the surrounding collection or call.
    CallbackQueryHandler,
    # Include this value in the surrounding collection or call.
    CommandHandler,
    # Include this value in the surrounding collection or call.
    MessageHandler,
    # Include this value in the surrounding collection or call.
    filters,
# Close the structure that was opened above.
)

# Import app.bot.handlers so this module can use its helpers.
from app.bot.handlers import (
    # Include this value in the surrounding collection or call.
    ask_handler,
    # Include this value in the surrounding collection or call.
    add_kategori_handler,
    # Include this value in the surrounding collection or call.
    asset_add_handler,
    # Include this value in the surrounding collection or call.
    asset_off_handler,
    # Include this value in the surrounding collection or call.
    asset_update_handler,
    # Include this value in the surrounding collection or call.
    assets_handler,
    # Include this value in the surrounding collection or call.
    audit_handler,
    # Include this value in the surrounding collection or call.
    budget_handler,
    # Include this value in the surrounding collection or call.
    budget_history_handler,
    # Include this value in the surrounding collection or call.
    pending_add_handler,
    # Include this value in the surrounding collection or call.
    pending_cancel_handler,
    # Include this value in the surrounding collection or call.
    pending_handler,
    # Include this value in the surrounding collection or call.
    pending_paid_handler,
    # Include this value in the surrounding collection or call.
    bulanan_handler,
    # Include this value in the surrounding collection or call.
    callback_handler,
    # Include this value in the surrounding collection or call.
    cancel_handler,
    # Include this value in the surrounding collection or call.
    cari_handler,
    # Include this value in the surrounding collection or call.
    coach_handler,
    # Include this value in the surrounding collection or call.
    debt_edit_handler,
    # Include this value in the surrounding collection or call.
    debt_settle_handler,
    # Include this value in the surrounding collection or call.
    debt_void_handler,
    # Include this value in the surrounding collection or call.
    delete_txn_handler,
    # Include this value in the surrounding collection or call.
    edit_txn_handler,
    # Include this value in the surrounding collection or call.
    edit_kategori_handler,
    # Include this value in the surrounding collection or call.
    error_handler,
    # Include this value in the surrounding collection or call.
    examples_handler,
    # Include this value in the surrounding collection or call.
    export_handler,
    # Include this value in the surrounding collection or call.
    grafik_handler,
    # Include this value in the surrounding collection or call.
    harian_handler,
    # Include this value in the surrounding collection or call.
    health_handler,
    # Include this value in the surrounding collection or call.
    help_handler,
    # Include this value in the surrounding collection or call.
    manual_handler,
    # Include this value in the surrounding collection or call.
<<<<<<< HEAD
=======
    privacy_handler,
    # Include this value in the surrounding collection or call.
>>>>>>> codex/jelaskan-proyek-ini
    quickstart_handler,
    # Include this value in the surrounding collection or call.
    set_saldo_handler,
    # Include this value in the surrounding collection or call.
    hutang_handler,
    # Include this value in the surrounding collection or call.
    image_handler,
    # Include this value in the surrounding collection or call.
    insight_handler,
    # Include this value in the surrounding collection or call.
    kategori_handler,
    # Include this value in the surrounding collection or call.
    last_handler,
    # Include this value in the surrounding collection or call.
    message_handler,
    # Include this value in the surrounding collection or call.
    mingguan_handler,
    # Include this value in the surrounding collection or call.
    networth_handler,
    # Include this value in the surrounding collection or call.
    networth_history_handler,
    # Include this value in the surrounding collection or call.
    networth_snapshot_handler,
    # Include this value in the surrounding collection or call.
    recurring_add_handler,
    # Include this value in the surrounding collection or call.
    recurring_edit_handler,
    # Include this value in the surrounding collection or call.
    recurring_handler,
    # Include this value in the surrounding collection or call.
    recurring_off_handler,
    # Include this value in the surrounding collection or call.
    recurring_run_handler,
    # Include this value in the surrounding collection or call.
    rekening_handler,
    # Include this value in the surrounding collection or call.
    ringkasan_hutang_handler,
    # Include this value in the surrounding collection or call.
    saldo_handler,
    # Include this value in the surrounding collection or call.
    scheduled_export_transactions,
    # Include this value in the surrounding collection or call.
    set_budget_handler,
    # Include this value in the surrounding collection or call.
    start_handler,
    # Include this value in the surrounding collection or call.
    transaksi_handler,
    # Include this value in the surrounding collection or call.
    unknown_command_handler,
# Close the structure that was opened above.
)
# Import app.config so this module can use its helpers.
from app.config import ALLOWED_USER_ID, TELEGRAM_BOT_TOKEN
# Import app.bot.handler_parts.state_utils so this module can use its helpers.
from app.bot.handler_parts.state_utils import clear_pending_flow_state_before_command
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import sheets_transaction


# Wrapper ini menjaga setiap aksi Telegram berada dalam satu konteks rollback Sheets.
# Implementation note for this project-specific finance flow.

# Define atomic bot handler for callers in this flow.
def atomic_bot_handler(callback):
    """Wrap a Telegram handler inside a best-effort Google Sheets transaction context."""

    # Apply this decorator before the callable is registered or executed.
    @wraps(callback)
    # Handle the asynchronous wrapped workflow.
    async def wrapped(update, context, *args, **kwargs):
        """Handle the asynchronous wrapped flow in the Telegram bot layer.

        Args:
            update: Telegram Update object supplied by python-telegram-bot.
            context: Telegram callback context containing args, bot data, user data, and job data.
            *args: Command argument list or parsed argument values supplied by the caller.
            **kwargs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

        Side effects:
            May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

        Flow constraints:
            Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
        """
        callback_name = getattr(callback, "__name__", "telegram_handler")

        # Valid slash commands should start from a clean transient state.
        # Without this, an old wizard such as /asset_add can keep consuming the
        # next normal chat even after the user has already run /saldo, /last, or
        # another command. Keep /cancel and unknown commands excluded so they can
        # give the right feedback.
        message_text = str(getattr(getattr(update, "message", None), "text", "") or "").strip()
        if message_text.startswith("/") and callback_name not in {"cancel_handler", "unknown_command_handler"}:
            command_token = message_text.split()[0].lstrip("/").split("@", 1)[0].lower()
            # Run this statement as part of the current workflow.
            clear_pending_flow_state_before_command(context, command_token)

        # Use a managed resource so it is closed after this operation.
        with sheets_transaction(label=callback_name):
            # Return await callback(update, context, *args, **kwargs) to the caller.
            return await callback(update, context, *args, **kwargs)

    # Return wrapped to the caller.
    return wrapped


# Implementation note for this project-specific finance flow.
# Message handling section

# Define register handlers for callers in this flow.
def register_handlers(telegram_app: Application) -> Application:
    """Register all Telegram commands, message handlers, callback handlers, and error handlers."""

    # Define add command for callers in this flow.
    def add_command(command_name: str, callback):
        """Coordinate the add command logic in the Telegram bot layer.

        Args:
            command_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
            callback: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `None` after completing the operation.

        Side effects:
            May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

        Flow constraints:
            Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
        """
        # Run this statement as part of the current workflow.
        telegram_app.add_handler(CommandHandler(command_name, atomic_bot_handler(callback)))

    # Define add message for callers in this flow.
    def add_message(message_filter, callback):
        """Coordinate the add message logic in the Telegram bot layer.

        Args:
            message_filter: Input value supplied by the caller; accepted shape follows the function signature and local validation.
            callback: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `None` after completing the operation.

        Side effects:
            May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

        Flow constraints:
            Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
        """
        # Run this statement as part of the current workflow.
        telegram_app.add_handler(MessageHandler(message_filter, atomic_bot_handler(callback)))

    # Basic commands for onboarding and bot checks.
    add_command("start", start_handler)
    add_command("quickstart", quickstart_handler)
    add_command("cancel", cancel_handler)
    add_command("batal", cancel_handler)
    add_command("help", help_handler)
    add_command("manual", manual_handler)
<<<<<<< HEAD
=======
    add_command("privacy", privacy_handler)
>>>>>>> codex/jelaskan-proyek-ini
    add_command("examples", examples_handler)
    add_command("contoh", examples_handler)
    add_command("health", health_handler)

    # Frequently used transaction and reporting commands.
    add_command("saldo", saldo_handler)
    add_command("set_saldo", set_saldo_handler)
    add_command("saldo_set", set_saldo_handler)
    add_command("set_balance", set_saldo_handler)
    add_command("rekening", rekening_handler)
    add_command("harian", harian_handler)
    add_command("mingguan", mingguan_handler)
    add_command("bulanan", bulanan_handler)
    add_command("grafik", grafik_handler)
    add_command("chart", grafik_handler)
    add_command("cari", cari_handler)
    add_command("last", last_handler)
    add_command("transaksi", transaksi_handler)
    add_command("delete_txn", delete_txn_handler)
    add_command("edit_txn", edit_txn_handler)

    # Export commands for backup or further analysis.
    add_command("download_data", export_handler)
    add_command("export", export_handler)

    # Budget commands. The regex handler supports natural input such as "budget makan 1jt".
    add_command("budget", budget_handler)
    add_command("set_budget", set_budget_handler)
    add_command("budget_history", budget_history_handler)
    add_message(filters.Regex(r"(?i)^budget\b"), set_budget_handler)

    # Category management commands route add/edit kategori into the guided wizard.
    add_command("kategori", kategori_handler)
    add_command("categories", kategori_handler)
    add_command("list_kategori", kategori_handler)
    add_command("add_kategori", add_kategori_handler)
    add_command("tambah_kategori", add_kategori_handler)
    add_command("add_category", add_kategori_handler)
    # Edit category aliases/type/symbol uses a separate wizard from add flow.
    add_command("edit_kategori", edit_kategori_handler)
    add_command("ubah_kategori", edit_kategori_handler)
    add_command("edit_category", edit_kategori_handler)

    # Pending expense commands for planned expenses or unpaid bills.
    add_command("pending", pending_handler)
    add_command("pending_add", pending_add_handler)
    add_command("rencana", pending_add_handler)
    add_command("pending_paid", pending_paid_handler)
    add_command("pending_cancel", pending_cancel_handler)
    add_message(filters.Regex(r"(?i)^(pending|rencana)\b"), pending_add_handler)

    # Debt and settlement commands.
    add_command("hutang", hutang_handler)
    add_command("ringkasan_hutang", ringkasan_hutang_handler)
    add_command("debt_void", debt_void_handler)
    add_command("debt_edit", debt_edit_handler)
    add_command("debt_settle", debt_settle_handler)

    # Recurring commands for repeated transactions or bills.
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

    # AI insight commands based on transaction data. These commands are read-only.
    add_command("insight", insight_handler)
    add_command("ask", ask_handler)
    add_command("audit", audit_handler)
    add_command("coach", coach_handler)

    # Fallback guard for slash commands that may not be caught by CommandHandler in some runtimes.
    # This prevents commands such as /set_saldo from being parsed as normal expenses.
    add_message(filters.Regex(r"(?i)^/(set_saldo|saldo_set|set_balance)(?:@\w+)?(?:\s|$)"), set_saldo_handler)
    add_message(filters.Regex(r"(?i)^/set_budget(?:@\w+)?(?:\s|$)"), set_budget_handler)
    add_message(filters.Regex(r"(?i)^/quickstart(?:@\w+)?(?:\s|$)"), quickstart_handler)
    add_message(filters.Regex(r"(?i)^/manual(?:@\w+)?(?:\s|$)"), manual_handler)
<<<<<<< HEAD
=======
    add_message(filters.Regex(r"(?i)^/privacy(?:@\w+)?(?:\s|$)"), privacy_handler)
>>>>>>> codex/jelaskan-proyek-ini
    # Route pending and asset slash commands explicitly if CommandHandler misses underscore commands.
    add_message(filters.Regex(r"(?i)^/pending_add(?:@\w+)?(?:\s|$)"), pending_add_handler)
    add_message(filters.Regex(r"(?i)^/pending_paid(?:@\w+)?(?:\s|$)"), pending_paid_handler)
    add_message(filters.Regex(r"(?i)^/pending_cancel(?:@\w+)?(?:\s|$)"), pending_cancel_handler)
    add_message(filters.Regex(r"(?i)^/asset_add(?:@\w+)?(?:\s|$)"), asset_add_handler)
    add_message(filters.Regex(r"(?i)^/asset_update(?:@\w+)?(?:\s|$)"), asset_update_handler)
    add_message(filters.Regex(r"(?i)^/asset_off(?:@\w+)?(?:\s|$)"), asset_off_handler)
    add_message(filters.Regex(r"(?i)^/networth_snapshot(?:@\w+)?(?:\s|$)"), networth_snapshot_handler)
    add_message(filters.Regex(r"(?i)^/networth_history(?:@\w+)?(?:\s|$)"), networth_history_handler)
    # Route recurring slash commands explicitly if CommandHandler misses underscore commands.
    add_message(filters.Regex(r"(?i)^/recurring_add(?:@\w+)?(?:\s|$)"), recurring_add_handler)
    add_message(filters.Regex(r"(?i)^/recurring_run(?:@\w+)?(?:\s|$)"), recurring_run_handler)
    add_message(filters.Regex(r"(?i)^/recurring_edit(?:@\w+)?(?:\s|$)"), recurring_edit_handler)
    add_message(filters.Regex(r"(?i)^/recurring_off(?:@\w+)?(?:\s|$)"), recurring_off_handler)
    add_message(filters.Regex(r"(?i)^/recurring(?:@\w+)?(?:\s|$)"), recurring_handler)

    # Generic handlers stay at the end so specific commands are processed first.
    add_message(filters.COMMAND, unknown_command_handler)
    # Run this statement as part of the current workflow.
    add_message(filters.PHOTO | filters.Document.IMAGE, image_handler)
    # Run this statement as part of the current workflow.
    add_message(filters.TEXT & ~filters.COMMAND, message_handler)

    # Run this statement as part of the current workflow.
    telegram_app.add_handler(CallbackQueryHandler(atomic_bot_handler(callback_handler)))
    # Run this statement as part of the current workflow.
    telegram_app.add_error_handler(error_handler)

    # Return telegram_app to the caller.
    return telegram_app


# Handle the asynchronous scheduled data export workflow.
async def scheduled_data_export(context):
    """Handle the asynchronous scheduled data export flow in the Telegram bot layer.

    Args:
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Wait for scheduled_export_transactions before continuing this flow.
        await scheduled_export_transactions(
            # Prepare bot for the next step.
            bot=context.bot,
            # Prepare chat id for the next step.
            chat_id=int(ALLOWED_USER_ID),
            # Prepare period for the next step.
            period=None,
        # Close the structure that was opened above.
        )
    # Handle an expected failure from the guarded operation above.
    except Exception as exc:
        print(f"[AUTO EXPORT ERROR] {exc}")


# Define register job queue jobs for callers in this flow.
def register_job_queue_jobs(telegram_app: Application) -> Application:
    """Coordinate the register job queue jobs logic in the Telegram bot layer.

    Args:
        telegram_app: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `Application` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the case where telegram_app.job_queue.
    if telegram_app.job_queue:
        # Open a multi-line structure for the values below.
        telegram_app.job_queue.run_daily(
            # Include this value in the surrounding collection or call.
            scheduled_data_export,
            time=time(hour=23, minute=55, tzinfo=ZoneInfo("Asia/Jakarta")),
            name="daily_data_export",
        # Close the structure that was opened above.
        )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        print("⚠️ JobQueue belum aktif. Install: python-telegram-bot[job-queue]")
    # Return telegram_app to the caller.
    return telegram_app


# Define build telegram app for callers in this flow.
def build_telegram_app() -> Application:
    """Create one configured Telegram Application instance with handlers and scheduled jobs."""
    # Handle the missing or empty TELEGRAM_BOT_TOKEN case.
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi di .env.")

    # Prepare telegram app for the next step.
    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    # Run this statement as part of the current workflow.
    register_handlers(telegram_app)
    # Run this statement as part of the current workflow.
    register_job_queue_jobs(telegram_app)
    # Return telegram_app to the caller.
    return telegram_app
