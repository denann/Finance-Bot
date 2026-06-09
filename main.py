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
    set_budget_handler,
    cari_handler,
    hutang_handler,
    message_handler,
    callback_handler,
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
telegram_app.add_handler(CommandHandler("cari", cari_handler))
telegram_app.add_handler(CommandHandler("hutang", hutang_handler))
telegram_app.add_handler(CallbackQueryHandler(callback_handler))

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(
            r"(?i)^(budget|set budget)"
        ),
        set_budget_handler,
    )
)
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
)

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


@app.get("/test-scheduler/{job_name}")
async def test_scheduler(job_name: str):
    """
    Trigger scheduler job secara manual untuk testing.
    job_name: daily | weekly | monthly | debt
    """
    from app.scheduler.jobs import (
        job_daily_summary,
        job_weekly_summary,
        job_monthly_summary,
        job_debt_reminder,
    )

    jobs = {
        "daily": job_daily_summary,
        "weekly": job_weekly_summary,
        "monthly": job_monthly_summary,
        "debt": job_debt_reminder,
    }

    if job_name not in jobs:
        return {"error": f"Job '{job_name}' tidak dikenal. Pilihan: {list(jobs.keys())}"}

    try:
        await jobs[job_name]()
        return {"status": "ok", "job": job_name, "message": "Job berhasil dijalankan. Cek Telegram!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=APP_PORT, reload=False)