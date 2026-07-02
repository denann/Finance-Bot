"""Application entry point. This module starts the bot in polling mode or webhook mode and prepares the scheduler and Google Sheets schema."""


from __future__ import annotations

import asyncio

import uvicorn
from fastapi import FastAPI

from app.api.webhook import router as webhook_router, set_telegram_app
from app.bot.application import build_telegram_app
from app.config import (
    ALLOWED_USER_ID,
    APP_PORT,
    BOT_MODE,
    GEMINI_API_KEY,
    GOOGLE_SERVICE_ACCOUNT_JSON,
    GOOGLE_SHEET_ID,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_WEBHOOK_SECRET,
    WEBHOOK_URL,
)
from app.scheduler.jobs import create_scheduler
from app.sheets.client import get_spreadsheet, ensure_spreadsheet_schema


# Implementation section
# Implementation section
app = FastAPI(title="Finance Bot")
app.include_router(webhook_router)

telegram_app = build_telegram_app()
set_telegram_app(telegram_app)

scheduler = create_scheduler()
_webhook_telegram_started = False


def validate_runtime_config(mode: str = BOT_MODE):
    """Validate data before it is used by runtime config."""
    missing = []

    base_required = {
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "ALLOWED_USER_ID": ALLOWED_USER_ID,
        "GOOGLE_SHEET_ID": GOOGLE_SHEET_ID,
        "GOOGLE_SERVICE_ACCOUNT_JSON": GOOGLE_SERVICE_ACCOUNT_JSON,
        "GEMINI_API_KEY": GEMINI_API_KEY,
    }
    for key, value in base_required.items():
        if value in (None, "", 0):
            missing.append(key)

    if mode == "webhook":
        webhook_required = {
            "WEBHOOK_URL": WEBHOOK_URL,
            "TELEGRAM_WEBHOOK_SECRET": TELEGRAM_WEBHOOK_SECRET,
        }
        for key, value in webhook_required.items():
            if value in (None, ""):
                missing.append(key)

    if missing:
        raise RuntimeError(
            "Konfigurasi .env belum lengkap untuk "
            f"BOT_MODE={mode}: {', '.join(missing)}"
        )


def ensure_schema_on_startup():
    """Ensure that setup is ready for schema on startup."""
    try:
        schema_results = ensure_spreadsheet_schema()
        changed = [
            result
            for result in schema_results
            if result.get("actions") != ["no_change"]
        ]
        print(
            "✅ Google Sheets schema siap."
            f" Tabs dicek: {len(schema_results)}."
            f" Perubahan: {len(changed)}."
        )
    except Exception as exc:
        # Schema compatibility note for Google Sheets headers and rows.
        # Schema compatibility note for Google Sheets headers and rows.
        print(f"⚠️ Google Sheets schema belum bisa dipastikan: {exc}")


def start_scheduler_once():
    """Helper for start scheduler once in the application."""
    if not scheduler.running:
        scheduler.start()
        print(f"✅ Scheduler started. Jobs: {[job.name for job in scheduler.get_jobs()]}")


def shutdown_scheduler_once():
    """Helper for shutdown scheduler once in the application."""
    if scheduler.running:
        scheduler.shutdown()


# ── FastAPI startup & shutdown, only active when webhook mode is used ──────
@app.on_event("startup")
async def startup():
    """Helper for startup in the application."""
    global _webhook_telegram_started

    if BOT_MODE != "webhook":
        print("ℹ️ FastAPI app aktif, tetapi BOT_MODE bukan webhook. Webhook tidak diset.")
        return

    validate_runtime_config("webhook")

    await telegram_app.initialize()
    await telegram_app.start()
    _webhook_telegram_started = True
    ensure_schema_on_startup()

    await telegram_app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        secret_token=TELEGRAM_WEBHOOK_SECRET,
    )

    start_scheduler_once()
    print(f"✅ Bot started. Webhook: {WEBHOOK_URL}/webhook")


@app.on_event("shutdown")
async def shutdown():
    """Helper for shutdown in the application."""
    global _webhook_telegram_started

    shutdown_scheduler_once()
    if _webhook_telegram_started:
        await telegram_app.stop()
        await telegram_app.shutdown()
        _webhook_telegram_started = False


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Helper for health check in the application."""
    return {"status": "ok", "mode": BOT_MODE}


@app.get("/test-sheets")
async def test_sheets():
    """Helper for test sheets in the application."""
    try:
        schema_results = ensure_spreadsheet_schema()
        spreadsheet = get_spreadsheet()
        sheets = [ws.title for ws in spreadsheet.worksheets()]

        return {
            "status": "connected",
            "spreadsheet_title": spreadsheet.title,
            "sheets_found": sheets,
            "schema_check": schema_results,
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


# ── Polling mode ──────────────────────────────────────────────────────────────
# Implementation section
# Date parsing note: keep explicit and relative Indonesian date formats predictable.

async def run_polling_mode():
    """Run the process for polling mode."""
    validate_runtime_config("polling")
    ensure_schema_on_startup()

    await telegram_app.initialize()
    await telegram_app.bot.delete_webhook(drop_pending_updates=True)
    await telegram_app.start()
    start_scheduler_once()

    if not telegram_app.updater:
        raise RuntimeError("Telegram updater tidak tersedia untuk polling mode.")

    await telegram_app.updater.start_polling(drop_pending_updates=True)
    print("✅ Bot started in polling mode. Tekan Ctrl+C untuk stop.")

    try:
        await asyncio.Event().wait()
    finally:
        if telegram_app.updater.running:
            await telegram_app.updater.stop()
        shutdown_scheduler_once()
        await telegram_app.stop()
        await telegram_app.shutdown()


# Implementation section
# Implementation section

def run_webhook_mode():
    """Run the process for webhook mode."""
    validate_runtime_config("webhook")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=APP_PORT,
        reload=False,
    )


# ── Local Run ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if BOT_MODE == "polling":
        try:
            asyncio.run(run_polling_mode())
        except KeyboardInterrupt:
            print("\n👋 Bot stopped.")
    elif BOT_MODE == "webhook":
        run_webhook_mode()
    else:
        raise RuntimeError("BOT_MODE harus 'polling' atau 'webhook'.")
