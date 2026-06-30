import uvicorn
from functools import wraps
from datetime import time
from zoneinfo import ZoneInfo
from fastapi import FastAPI
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.api.webhook import router as webhook_router, set_telegram_app
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
from app.config import (
    ALLOWED_USER_ID,
    APP_PORT,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_WEBHOOK_SECRET,
    WEBHOOK_URL,
)
from app.scheduler.jobs import create_scheduler
from app.sheets.client import get_spreadsheet, sheets_transaction


# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="Finance Bot")
app.include_router(webhook_router)


# ── Telegram ──────────────────────────────────────────────────────────────────
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()




def atomic_bot_handler(callback):
    """Jalankan setiap Telegram handler dalam satu operasi Sheets all-or-nothing."""
    @wraps(callback)
    async def wrapped(update, context, *args, **kwargs):
        with sheets_transaction(label=getattr(callback, "__name__", "telegram_handler")):
            return await callback(update, context, *args, **kwargs)

    return wrapped


def add_command(command_name: str, callback):
    telegram_app.add_handler(CommandHandler(command_name, atomic_bot_handler(callback)))


def add_message(message_filter, callback):
    telegram_app.add_handler(MessageHandler(message_filter, atomic_bot_handler(callback)))


# ── Basic Commands ────────────────────────────────────────────────────────────
add_command("start", start_handler)
add_command("help", help_handler)
add_command("health", health_handler)


# ── Transaction Commands ──────────────────────────────────────────────────────
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


# ── Export Commands ───────────────────────────────────────────────────────────
add_command("download_data", export_handler)


# ── Budget Commands ───────────────────────────────────────────────────────────
add_command("budget", budget_handler)
add_command("budget_history", budget_history_handler)
add_message(filters.Regex(r"(?i)^budget\b"), set_budget_handler)


# ── Pending Expense Commands ─────────────────────────────────────────────────
add_command("pending", pending_handler)
add_command("pending_add", pending_add_handler)
add_command("rencana", pending_add_handler)
add_command("pending_paid", pending_paid_handler)
add_command("pending_cancel", pending_cancel_handler)
add_message(filters.Regex(r"(?i)^(pending|rencana)\b"), pending_add_handler)


# ── Debt Commands ─────────────────────────────────────────────────────────────
add_command("hutang", hutang_handler)
add_command("ringkasan_hutang", ringkasan_hutang_handler)
add_command("debt_void", debt_void_handler)
add_command("debt_edit", debt_edit_handler)
add_command("debt_settle", debt_settle_handler)


# ── Recurring Transaction Commands ────────────────────────────────────────────
add_command("recurring", recurring_handler)
add_command("recurring_add", recurring_add_handler)
add_command("recurring_run", recurring_run_handler)
add_command("recurring_edit", recurring_edit_handler)
add_command("recurring_off", recurring_off_handler)


# ── Net Worth Commands ────────────────────────────────────────────────────────
add_command("networth", networth_handler)
add_command("assets", assets_handler)

add_command("asset_add", asset_add_handler)
add_command("asset_update", asset_update_handler)
add_command("asset_off", asset_off_handler)


add_command("networth_snapshot", networth_snapshot_handler)
add_command("networth_history", networth_history_handler)


# ── Gemini / RAG Finance Insight Commands ─────────────────────────────────────
add_command("insight", insight_handler)
add_command("ask", ask_handler)
add_command("audit", audit_handler)
add_command("coach", coach_handler)


# ── Message & Callback Handlers ───────────────────────────────────────────────
add_message(filters.COMMAND, unknown_command_handler)

add_message(filters.PHOTO | filters.Document.IMAGE, image_handler)

add_message(filters.TEXT & ~filters.COMMAND, message_handler)

telegram_app.add_handler(CallbackQueryHandler(atomic_bot_handler(callback_handler)))
telegram_app.add_error_handler(error_handler)

set_telegram_app(telegram_app)


# ── Daily Telegram Export Job ─────────────────────────────────────────────────
async def scheduled_data_export(context):
    try:
        await scheduled_export_transactions(
            bot=context.bot,
            chat_id=int(ALLOWED_USER_ID),
            period=None,
        )
    except Exception as e:
        print(f"[AUTO EXPORT ERROR] {e}")


if telegram_app.job_queue:
    telegram_app.job_queue.run_daily(
        scheduled_data_export,
        time=time(hour=23, minute=55, tzinfo=ZoneInfo("Asia/Jakarta")),
        name="daily_data_export",
    )
else:
    print("⚠️ JobQueue belum aktif. Install: python-telegram-bot[job-queue]")


# ── Scheduler ─────────────────────────────────────────────────────────────────
scheduler = create_scheduler()


# ── Startup & Shutdown ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.start()

    await telegram_app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        secret_token=TELEGRAM_WEBHOOK_SECRET,
    )

    scheduler.start()

    print(f"✅ Bot started. Webhook: {WEBHOOK_URL}/webhook")
    print(f"✅ Scheduler started. Jobs: {[job.name for job in scheduler.get_jobs()]}")


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()
    await telegram_app.stop()
    await telegram_app.shutdown()


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/test-sheets")
async def test_sheets():
    try:
        spreadsheet = get_spreadsheet()
        sheets = [ws.title for ws in spreadsheet.worksheets()]

        return {
            "status": "connected",
            "spreadsheet_title": spreadsheet.title,
            "sheets_found": sheets,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


# ── Local Run ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=APP_PORT,
        reload=False,
    )
