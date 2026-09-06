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
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

# Import app.bot.handlers so this module can use its helpers.
from app.bot.handlers import (
    ask_handler,
    add_kategori_handler,
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
    cancel_handler,
    cari_handler,
    coach_handler,
    debt_edit_handler,
    debt_settle_handler,
    debt_void_handler,
    delete_txn_handler,
    edit_txn_handler,
    edit_kategori_handler,
    error_handler,
    examples_handler,
    export_handler,
    grafik_handler,
    harian_handler,
    health_handler,
    help_handler,
    manual_handler,
    privacy_handler,
    quickstart_handler,
    set_saldo_handler,
    hutang_handler,
    image_handler,
    insight_handler,
    kategori_handler,
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
from app.bot.command_registry import (
    AI_COMMANDS,
    BASIC_COMMANDS,
    BUDGET_COMMANDS,
    CATEGORY_COMMANDS,
    DEBT_COMMANDS,
    EXPORT_COMMANDS,
    NET_WORTH_COMMANDS,
    PENDING_COMMANDS,
    RECURRING_COMMANDS,
    TRANSACTION_COMMANDS,
)
# Import app.config so this module can use its helpers.
from app.config import ALLOWED_USER_ID, TELEGRAM_BOT_TOKEN
# Import app.bot.handler_parts.state_utils so this module can use its helpers.
from app.bot.handler_parts.state_utils import clear_pending_flow_state_before_command
from app.bot.handler_parts.transaction_browser import prepare_transaction_browser_for_command
# Import immutable action request binding for preview keyboard creation.
from app.bot.pending_actions import pending_action_request_context
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import sheets_request_snapshot, sheets_transaction
from app.observability import (
    correlation_scope,
    emit_event,
    increment_metric,
    monotonic_ms,
    new_correlation_id,
    observe_duration,
)
from app.application.gemini_governance import gemini_request_scope
from app.bot.output import FinanceBot


# Wrapper ini menjaga setiap aksi Telegram berada dalam satu konteks rollback Sheets.
# Implementation note for this project-specific finance flow.

# Helper for atomic bot handler.
def atomic_bot_handler(callback):
    """Wrap a Telegram handler inside a best-effort Google Sheets transaction context."""

    # Apply this decorator before the callable is registered or executed.
    @wraps(callback)
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
        update_id = getattr(update, "update_id", None)
        correlation_id = f"tg-{int(update_id)}" if isinstance(update_id, int) else new_correlation_id("tg")
        started_ms = monotonic_ms()

        # Valid slash commands should start from a clean transient state.
        # Without this, an old wizard such as /asset_add can keep consuming the
        # next normal chat even after the user has already run /saldo, /last, or
        # another command. Keep /cancel and unknown commands excluded so they can
        # give the right feedback.
        message_text = str(getattr(getattr(update, "message", None), "text", "") or "").strip()
        if message_text.startswith("/") and callback_name not in {"cancel_handler", "unknown_command_handler"}:
            command_token = message_text.split()[0].lstrip("/").split("@", 1)[0].lower()
            clear_pending_flow_state_before_command(context, command_token)
            await prepare_transaction_browser_for_command(update, context, command_token, message_text)

        effective_user = getattr(update, "effective_user", None)
        owner_user_id = int(getattr(effective_user, "id", 0) or 0)
        callback_query = getattr(update, "callback_query", None)
        callback_message = getattr(callback_query, "message", None)
        preview_message_id = getattr(callback_message, "message_id", None)

        with correlation_scope(correlation_id):
            increment_metric(f"telegram.handler.{callback_name}.started")
            emit_event("telegram_handler_started", handler=callback_name)
            try:
                with gemini_request_scope():
                    with sheets_request_snapshot():
                        with pending_action_request_context(context.user_data, owner_user_id, preview_message_id):
                            with sheets_transaction(label=callback_name):
                                result = await callback(update, context, *args, **kwargs)
            except Exception as exc:
                duration_ms = monotonic_ms() - started_ms
                increment_metric(f"telegram.handler.{callback_name}.failed")
                observe_duration(f"telegram.handler.{callback_name}.latency_ms", duration_ms)
                emit_event(
                    "telegram_handler_failed",
                    handler=callback_name,
                    duration_ms=round(duration_ms, 3),
                    error_type=type(exc).__name__,
                )
                raise

            duration_ms = monotonic_ms() - started_ms
            increment_metric(f"telegram.handler.{callback_name}.completed")
            observe_duration(f"telegram.handler.{callback_name}.latency_ms", duration_ms)
            emit_event(
                "telegram_handler_completed",
                handler=callback_name,
                duration_ms=round(duration_ms, 3),
            )
            return result

    return wrapped


# Implementation note for this project-specific finance flow.
# Message handling section

# Helper for register handlers.
def register_handlers(telegram_app: Application) -> Application:
    """Register all Telegram commands, message handlers, callback handlers, and error handlers."""

    # Helper for add command.
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
        telegram_app.add_handler(CommandHandler(command_name, atomic_bot_handler(callback)))

    # Helper for add message.
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
        telegram_app.add_handler(MessageHandler(message_filter, atomic_bot_handler(callback)))

    def add_command_group(bindings) -> None:
        """Register one ordered group from the pure public command registry."""

        for command_name, callback_name in bindings:
            callback = globals().get(callback_name)
            if callback is None:
                raise RuntimeError(f"Handler registry tidak menemukan {callback_name}.")
            add_command(command_name, callback)

    # Basic commands for onboarding and bot checks.
    add_command_group(BASIC_COMMANDS)

    # Frequently used transaction and reporting commands.
    add_command_group(TRANSACTION_COMMANDS)

    # Export commands for backup or further analysis.
    add_command_group(EXPORT_COMMANDS)

    # Budget commands. The regex handler supports natural input such as "budget makan 1jt".
    add_command_group(BUDGET_COMMANDS)
    add_message(filters.Regex(r"(?i)^budget\b"), set_budget_handler)

    # Category management commands route add/edit kategori into the guided wizard.
    add_command_group(CATEGORY_COMMANDS)

    # Pending expense commands for planned expenses or unpaid bills.
    add_command_group(PENDING_COMMANDS)
    add_message(filters.Regex(r"(?i)^(pending|rencana)\b"), pending_add_handler)

    # Debt and settlement commands.
    add_command_group(DEBT_COMMANDS)

    # Recurring commands for repeated transactions or bills.
    add_command_group(RECURRING_COMMANDS)

    # Net worth and asset management commands.
    add_command_group(NET_WORTH_COMMANDS)

    # AI insight commands based on transaction data. These commands are read-only.
    add_command_group(AI_COMMANDS)

    # Fallback guard for slash commands that may not be caught by CommandHandler in some runtimes.
    # This prevents commands such as /set_saldo from being parsed as normal expenses.
    add_message(filters.Regex(r"(?i)^/(set_saldo|saldo_set|set_balance)(?:@\w+)?(?:\s|$)"), set_saldo_handler)
    add_message(filters.Regex(r"(?i)^/set_budget(?:@\w+)?(?:\s|$)"), set_budget_handler)
    add_message(filters.Regex(r"(?i)^/quickstart(?:@\w+)?(?:\s|$)"), quickstart_handler)
    add_message(filters.Regex(r"(?i)^/manual(?:@\w+)?(?:\s|$)"), manual_handler)
    add_message(filters.Regex(r"(?i)^/privacy(?:@\w+)?(?:\s|$)"), privacy_handler)
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
    add_message(filters.PHOTO | filters.Document.IMAGE, image_handler)
    add_message(filters.TEXT & ~filters.COMMAND, message_handler)

    telegram_app.add_handler(CallbackQueryHandler(atomic_bot_handler(callback_handler)))
    telegram_app.add_error_handler(error_handler)

    return telegram_app


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
        # Await scheduled export transactions before continuing.
        await scheduled_export_transactions(
            bot=context.bot,
            chat_id=int(ALLOWED_USER_ID),
            # Extract period for validation.
            period=None,
        )
    # Handle an expected failure from the guarded operation above.
    except Exception as exc:
        emit_event("scheduled_export_job_failed", error_type=type(exc).__name__)


# Helper for register job queue jobs.
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
    if telegram_app.job_queue:
        telegram_app.job_queue.run_daily(
            scheduled_data_export,
            time=time(hour=23, minute=55, tzinfo=ZoneInfo("Asia/Jakarta")),
            name="daily_data_export",
        )
    # Use the fallback path when no earlier branch matched.
    else:
        print("⚠️ JobQueue belum aktif. Install: python-telegram-bot[job-queue]")
    return telegram_app


# Helper for build telegram app.
def build_telegram_app() -> Application:
    """Create one configured Telegram Application instance with handlers and scheduled jobs."""
    # Validate missing TELEGRAM BOT TOKEN before continuing.
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi di .env.")

    telegram_app = Application.builder().bot(FinanceBot(token=TELEGRAM_BOT_TOKEN)).build()
    register_handlers(telegram_app)
    register_job_queue_jobs(telegram_app)
    return telegram_app
