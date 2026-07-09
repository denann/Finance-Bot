"""Application entry point for Finance Bot.

This module validates runtime configuration, prepares the Telegram application,
checks Google Sheets schema, starts scheduled jobs, and runs either polling mode
or FastAPI webhook mode.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

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
from app.sheets.client import ensure_spreadsheet_schema, get_spreadsheet


# Share one Telegram app and scheduler across polling and webhook runtimes.
telegram_app = build_telegram_app()
set_telegram_app(telegram_app)

scheduler = create_scheduler()
_webhook_telegram_started = False


def validate_runtime_config(mode: str = BOT_MODE):
    """Validate environment values required by the selected runtime.

    Args:
        mode: Runtime mode to validate. Expected values are `polling` or
            `webhook`.

    Returns:
        None.

    Side effects:
        Raises `RuntimeError` when required environment values are missing.

    Flow constraints:
        Keep validation read-only and never print credential values. Error text
        only contains missing environment variable names.
    """
    missing = []

    base_required = {
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "ALLOWED_USER_ID": ALLOWED_USER_ID,
        "GOOGLE_SHEET_ID": GOOGLE_SHEET_ID,
        "GOOGLE_SERVICE_ACCOUNT_JSON": GOOGLE_SERVICE_ACCOUNT_JSON,
        "GEMINI_API_KEY": GEMINI_API_KEY,
    }
    # Report only variable names so secret values never leak into logs.
    for key, value in base_required.items():
        if value in (None, "", 0):
            missing.append(key)

    if mode == "webhook":
        webhook_required = {
            "WEBHOOK_URL": WEBHOOK_URL,
            "TELEGRAM_WEBHOOK_SECRET": TELEGRAM_WEBHOOK_SECRET,
        }
        # Webhook mode needs a public URL and webhook secret in addition to base config.
        for key, value in webhook_required.items():
            if value in (None, ""):
                missing.append(key)

    if missing:
        raise RuntimeError(
            "Konfigurasi .env belum lengkap untuk "
            f"BOT_MODE={mode}: {', '.join(missing)}"
        )


def ensure_schema_on_startup():
    """Check Google Sheets schema during startup.

    Args:
        None.

    Returns:
        None.

    Side effects:
        May create or repair expected Google Sheets tabs through
        `ensure_spreadsheet_schema`, then prints a startup summary.

    Flow constraints:
        Keep startup resilient. If schema verification fails, log the issue and
        let the bot continue so the operator can inspect credentials/network.
    """
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
        # Keep startup debuggable when Sheets is temporarily unavailable.
        print(f"⚠️ Google Sheets schema belum bisa dipastikan: {exc}")


def start_scheduler_once():
    """Start the shared scheduler if it is not already running.

    Args:
        None.

    Returns:
        None.

    Side effects:
        Starts scheduled jobs and prints active job names.

    Flow constraints:
        Avoid duplicate scheduler starts across polling and webhook lifecycle
        paths.
    """
    if not scheduler.running:
        scheduler.start()
        print(f"✅ Scheduler started. Jobs: {[job.name for job in scheduler.get_jobs()]}")


def shutdown_scheduler_once():
    """Shut down the shared scheduler if it is running.

    Args:
        None.

    Returns:
        None.

    Side effects:
        Stops scheduled jobs.

    Flow constraints:
        Keep shutdown idempotent so multiple cleanup paths can call it safely.
    """
    if scheduler.running:
        scheduler.shutdown()


async def startup():
    """Start the Telegram webhook runtime.

    Args:
        None.

    Returns:
        None.

    Side effects:
        Initializes Telegram, checks Sheets schema, sets the webhook, and starts
        scheduled jobs.

    Flow constraints:
        Run webhook setup only when `BOT_MODE=webhook`; otherwise leave FastAPI
        alive for health checks without touching Telegram webhook state.
    """
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


async def shutdown():
    """Stop webhook runtime resources cleanly.

    Args:
        None.

    Returns:
        None.

    Side effects:
        Stops scheduled jobs and Telegram resources when webhook startup
        completed.

    Flow constraints:
        Avoid stopping Telegram resources that were never started in webhook
        mode.
    """
    global _webhook_telegram_started

    shutdown_scheduler_once()
    if _webhook_telegram_started:
        await telegram_app.stop()
        await telegram_app.shutdown()
        _webhook_telegram_started = False


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """Run startup and shutdown through FastAPI lifespan hooks."""
    await startup()
    try:
        yield
    finally:
        await shutdown()


app = FastAPI(title="Finance Bot", lifespan=lifespan)
app.include_router(webhook_router)


@app.get("/health")
async def health_check():
    """Return a lightweight runtime health response.

    Args:
        None.

    Returns:
        JSON-serializable dict containing service status and active bot mode.

    Side effects:
        None.

    Flow constraints:
        Keep this endpoint read-only and safe for deployment health checks.
    """
    return {"status": "ok", "mode": BOT_MODE}


@app.get("/test-sheets")
async def test_sheets():
    """Check Google Sheets connectivity and schema from an HTTP endpoint.

    Args:
        None.

    Returns:
        JSON-serializable dict with connection status, spreadsheet title,
        worksheet names, and schema check result.

    Side effects:
        May create or repair expected Google Sheets tabs through
        `ensure_spreadsheet_schema`.

    Flow constraints:
        Do not expose credential values in the response.
    """
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


async def run_polling_mode():
    """Run the Telegram bot with long polling.

    Args:
        None.

    Returns:
        None. The coroutine blocks until interrupted.

    Side effects:
        Initializes Telegram polling, checks Sheets schema, starts scheduled
        jobs, and shuts resources down on cancellation.

    Flow constraints:
        Delete webhook state before polling so Telegram does not deliver updates
        to both webhook and polling runtimes.
    """
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
        # Keep the process alive until Ctrl+C or external cancellation.
        await asyncio.Event().wait()
    finally:
        if telegram_app.updater.running:
            await telegram_app.updater.stop()
        shutdown_scheduler_once()
        await telegram_app.stop()
        await telegram_app.shutdown()


def run_webhook_mode():
    """Run the FastAPI webhook server with uvicorn.

    Args:
        None.

    Returns:
        None.

    Side effects:
        Starts uvicorn and uses FastAPI lifespan hooks to manage bot resources.

    Flow constraints:
        Keep reload disabled for stable bot runtime behavior.
    """
    validate_runtime_config("webhook")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=APP_PORT,
        reload=False,
    )


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
