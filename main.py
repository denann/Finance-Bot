import uvicorn
from fastapi import FastAPI
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from app.config import (
    APP_PORT,
    TELEGRAM_BOT_TOKEN,
    WEBHOOK_URL,
    TELEGRAM_WEBHOOK_SECRET,
)
from app.sheets.client import get_spreadsheet
from app.api.webhook import router as webhook_router, set_telegram_app
from app.bot.handlers import (
    start_handler,
    help_handler,
    saldo_handler,
    harian_handler,
    mingguan_handler,
    bulanan_handler,
    budget_handler,
    budget_history_handler,
    set_budget_handler,
    cari_handler,
    hutang_handler,
    debt_void_handler,
    last_handler,
    delete_txn_handler,
    edit_txn_handler,
    unknown_command_handler,
    message_handler,
    image_handler,
    callback_handler,
    export_handler,
    recurring_handler,
    recurring_add_handler,
    recurring_run_handler,
    recurring_off_handler,
    recurring_edit_handler,
    health_handler,
    networth_handler,
    assets_handler,
    liabilities_handler,
    asset_add_handler,
    asset_update_handler,
    asset_off_handler,
    liability_add_handler,
    liability_update_handler,
    liability_off_handler,
    networth_snapshot_handler,
    networth_history_handler,
    insight_handler,
    ask_handler,
    audit_handler,
    coach_handler,
)
from app.scheduler.jobs import create_scheduler

# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="Finance Bot")
app.include_router(webhook_router)

# ── Telegram ──────────────────────────────────────────────────────────────────
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

telegram_app.add_handler(CommandHandler("start", start_handler))
telegram_app.add_handler(CommandHandler("help", help_handler))
telegram_app.add_handler(CommandHandler("saldo", saldo_handler))
telegram_app.add_handler(CommandHandler("harian", harian_handler))
telegram_app.add_handler(CommandHandler("mingguan", mingguan_handler))
telegram_app.add_handler(CommandHandler("bulanan", bulanan_handler))
telegram_app.add_handler(CommandHandler("budget", budget_handler))
telegram_app.add_handler(CommandHandler("budget_history", budget_history_handler))
telegram_app.add_handler(CommandHandler("hutang", hutang_handler))
telegram_app.add_handler(CommandHandler("debt_void", debt_void_handler))
telegram_app.add_handler(CommandHandler("cari", cari_handler))
telegram_app.add_handler(CommandHandler("last", last_handler))
telegram_app.add_handler(CommandHandler("delete_txn", delete_txn_handler))
telegram_app.add_handler(CommandHandler("edit_txn", edit_txn_handler))
telegram_app.add_handler(CommandHandler("export", export_handler))
telegram_app.add_handler(MessageHandler(filters.Regex(r"(?i)^budget\b"), set_budget_handler))
telegram_app.add_handler(CommandHandler("recurring", recurring_handler))
telegram_app.add_handler(CommandHandler("recurring_add", recurring_add_handler))
telegram_app.add_handler(CommandHandler("recurring_run", recurring_run_handler))
telegram_app.add_handler(CommandHandler("recurring_edit", recurring_edit_handler))
telegram_app.add_handler(CommandHandler("recurring_off", recurring_off_handler))
telegram_app.add_handler(CommandHandler("health", health_handler))
telegram_app.add_handler(CommandHandler("networth", networth_handler))
telegram_app.add_handler(CommandHandler("assets", assets_handler))
telegram_app.add_handler(CommandHandler("liabilities", liabilities_handler))

telegram_app.add_handler(CommandHandler("asset_add", asset_add_handler))
telegram_app.add_handler(CommandHandler("asset_update", asset_update_handler))
telegram_app.add_handler(CommandHandler("asset_off", asset_off_handler))

telegram_app.add_handler(CommandHandler("liability_add", liability_add_handler))
telegram_app.add_handler(CommandHandler("liability_update", liability_update_handler))
telegram_app.add_handler(CommandHandler("liability_off", liability_off_handler))

telegram_app.add_handler(CommandHandler("networth_snapshot", networth_snapshot_handler))
telegram_app.add_handler(CommandHandler("networth_history", networth_history_handler))

# Gemini / RAG finance insight (read-only)
telegram_app.add_handler(CommandHandler("insight", insight_handler))
telegram_app.add_handler(CommandHandler("ask", ask_handler))
telegram_app.add_handler(CommandHandler("audit", audit_handler))
telegram_app.add_handler(CommandHandler("coach", coach_handler))

telegram_app.add_handler(MessageHandler(filters.COMMAND, unknown_command_handler))
telegram_app.add_handler(
    MessageHandler(filters.PHOTO | filters.Document.IMAGE, image_handler)
)
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
)
telegram_app.add_handler(CallbackQueryHandler(callback_handler))
set_telegram_app(telegram_app)

# ── Scheduler ─────────────────────────────────────────────────────────────────
scheduler = create_scheduler()


# ── Startup & shutdown ────────────────────────────────────────────────────────
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
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=APP_PORT, reload=False)