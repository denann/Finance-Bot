"""Application entry point. This module starts the bot in polling mode or webhook mode and prepares the scheduler and Google Sheets schema."""


# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import asyncio for this module's local operations.
import asyncio
# Import contextlib so this module can use its helpers.
from contextlib import asynccontextmanager

# Import uvicorn for this module's local operations.
import uvicorn
# Import fastapi so this module can use its helpers.
from fastapi import FastAPI

# Import app.api.webhook so this module can use its helpers.
from app.api.webhook import router as webhook_router, set_telegram_app
# Import app.bot.application so this module can use its helpers.
from app.bot.application import build_telegram_app
# Import app.config so this module can use its helpers.
from app.config import (
    # Include this value in the surrounding collection or call.
    ALLOWED_USER_ID,
    # Include this value in the surrounding collection or call.
    APP_PORT,
    # Include this value in the surrounding collection or call.
    BOT_MODE,
    # Include this value in the surrounding collection or call.
    GEMINI_API_KEY,
    # Include this value in the surrounding collection or call.
    GOOGLE_SERVICE_ACCOUNT_JSON,
    # Include this value in the surrounding collection or call.
    GOOGLE_SHEET_ID,
    # Include this value in the surrounding collection or call.
    TELEGRAM_BOT_TOKEN,
    # Include this value in the surrounding collection or call.
    TELEGRAM_WEBHOOK_SECRET,
    # Include this value in the surrounding collection or call.
    WEBHOOK_URL,
# Close the structure that was opened above.
)
# Import app.scheduler.jobs so this module can use its helpers.
from app.scheduler.jobs import create_scheduler
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import get_spreadsheet, ensure_spreadsheet_schema


# Implementation section
# Implementation section
telegram_app = build_telegram_app()
# Run this statement as part of the current workflow.
set_telegram_app(telegram_app)

# Prepare scheduler for the next step.
scheduler = create_scheduler()
# Prepare webhook telegram started for the next step.
_webhook_telegram_started = False


# Define validate runtime config for callers in this flow.
def validate_runtime_config(mode: str = BOT_MODE):
    """Validate data before it is used by runtime config."""
    # Prepare missing for the next step.
    missing = []

    # Open a multi-line structure for the values below.
    base_required = {
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "ALLOWED_USER_ID": ALLOWED_USER_ID,
        "GOOGLE_SHEET_ID": GOOGLE_SHEET_ID,
        "GOOGLE_SERVICE_ACCOUNT_JSON": GOOGLE_SERVICE_ACCOUNT_JSON,
        "GEMINI_API_KEY": GEMINI_API_KEY,
    # Close the structure that was opened above.
    }
    # Process each key, value in the current collection.
    for key, value in base_required.items():
        if value in (None, "", 0):
            # Update missing with the current value.
            missing.append(key)

    if mode == "webhook":
        # Open a multi-line structure for the values below.
        webhook_required = {
            "WEBHOOK_URL": WEBHOOK_URL,
            "TELEGRAM_WEBHOOK_SECRET": TELEGRAM_WEBHOOK_SECRET,
        # Close the structure that was opened above.
        }
        # Process each key, value in the current collection.
        for key, value in webhook_required.items():
            if value in (None, ""):
                # Update missing with the current value.
                missing.append(key)

    # Handle the case where missing.
    if missing:
        # Raise a clear error so the caller can stop this invalid flow.
        raise RuntimeError(
            "Konfigurasi .env belum lengkap untuk "
            f"BOT_MODE={mode}: {', '.join(missing)}"
        # Close the structure that was opened above.
        )


# Define ensure schema on startup for callers in this flow.
def ensure_schema_on_startup():
    """Ensure that setup is ready for schema on startup."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare schema results for the next step.
        schema_results = ensure_spreadsheet_schema()
        # Open a multi-line structure for the values below.
        changed = [
            # Run this statement as part of the current workflow.
            result
            # Process each result in the current collection.
            for result in schema_results
            if result.get("actions") != ["no_change"]
        # Close the structure that was opened above.
        ]
        # Open a multi-line structure for the values below.
        print(
            "✅ Google Sheets schema siap."
            f" Tabs dicek: {len(schema_results)}."
            f" Perubahan: {len(changed)}."
        # Close the structure that was opened above.
        )
    # Handle an expected failure from the guarded operation above.
    except Exception as exc:
        # Schema compatibility note for Google Sheets headers and rows.
        # Schema compatibility note for Google Sheets headers and rows.
        print(f"⚠️ Google Sheets schema belum bisa dipastikan: {exc}")


# Define start scheduler once for callers in this flow.
def start_scheduler_once():
    """Coordinate the start scheduler once logic in the application layer.

    Args:
        None.

    Returns:
        `None` after completing the operation.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Handle the missing or empty scheduler.running case.
    if not scheduler.running:
        # Run this statement as part of the current workflow.
        scheduler.start()
        print(f"✅ Scheduler started. Jobs: {[job.name for job in scheduler.get_jobs()]}")


# Define shutdown scheduler once for callers in this flow.
def shutdown_scheduler_once():
    """Coordinate the shutdown scheduler once logic in the application layer.

    Args:
        None.

    Returns:
        `None` after completing the operation.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Handle the case where scheduler.running.
    if scheduler.running:
        # Run this statement as part of the current workflow.
        scheduler.shutdown()


# ── FastAPI startup & shutdown, only active when webhook mode is used ──────
async def startup():
    """Coordinate the startup logic in the application layer.

    Args:
        None.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this statement as part of the current workflow.
    global _webhook_telegram_started

    if BOT_MODE != "webhook":
        print("ℹ️ FastAPI app aktif, tetapi BOT_MODE bukan webhook. Webhook tidak diset.")
        # Return control to the caller.
        return

    validate_runtime_config("webhook")

    # Wait for telegram_app.initialize before continuing this flow.
    await telegram_app.initialize()
    # Wait for telegram_app.start before continuing this flow.
    await telegram_app.start()
    # Prepare webhook telegram started for the next step.
    _webhook_telegram_started = True
    # Run this statement as part of the current workflow.
    ensure_schema_on_startup()

    # Wait for telegram_app.bot.set_webhook before continuing this flow.
    await telegram_app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        # Prepare secret token for the next step.
        secret_token=TELEGRAM_WEBHOOK_SECRET,
    # Close the structure that was opened above.
    )

    # Run this statement as part of the current workflow.
    start_scheduler_once()
    print(f"✅ Bot started. Webhook: {WEBHOOK_URL}/webhook")


# Handle the asynchronous shutdown workflow.
async def shutdown():
    """Coordinate the shutdown logic in the application layer.

    Args:
        None.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this statement as part of the current workflow.
    global _webhook_telegram_started

    # Run this statement as part of the current workflow.
    shutdown_scheduler_once()
    # Handle the case where _webhook_telegram_started.
    if _webhook_telegram_started:
        # Wait for telegram_app.stop before continuing this flow.
        await telegram_app.stop()
        # Wait for telegram_app.shutdown before continuing this flow.
        await telegram_app.shutdown()
        # Prepare webhook telegram started for the next step.
        _webhook_telegram_started = False


# Apply this decorator before the callable is registered or executed.
@asynccontextmanager
# Handle the asynchronous lifespan workflow.
async def lifespan(app_instance: FastAPI):
    """Run webhook startup and shutdown without deprecated FastAPI event hooks."""
    # Wait for startup before continuing this flow.
    await startup()
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Run this statement as part of the current workflow.
        yield
    # Run cleanup that must happen after the guarded operation.
    finally:
        # Wait for shutdown before continuing this flow.
        await shutdown()


app = FastAPI(title="Finance Bot", lifespan=lifespan)
# Run this statement as part of the current workflow.
app.include_router(webhook_router)


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
# Handle the asynchronous health check workflow.
async def health_check():
    """Coordinate the health check logic in the application layer.

    Args:
        None.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    return {"status": "ok", "mode": BOT_MODE}


@app.get("/test-sheets")
# Handle the asynchronous test sheets workflow.
async def test_sheets():
    """Coordinate the test sheets logic in the application layer.

    Args:
        None.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare schema results for the next step.
        schema_results = ensure_spreadsheet_schema()
        # Prepare spreadsheet for the next step.
        spreadsheet = get_spreadsheet()
        # Prepare sheets for the next step.
        sheets = [ws.title for ws in spreadsheet.worksheets()]

        # Return { to the caller.
        return {
            "status": "connected",
            "spreadsheet_title": spreadsheet.title,
            "sheets_found": sheets,
            "schema_check": schema_results,
        # Close the structure that was opened above.
        }

    # Handle an expected failure from the guarded operation above.
    except Exception as exc:
        # Return { to the caller.
        return {
            "status": "error",
            "message": str(exc),
        # Close the structure that was opened above.
        }


# ── Polling mode ──────────────────────────────────────────────────────────────
# Implementation section
# Date parsing note: keep explicit and relative Indonesian date formats predictable.

# Handle the asynchronous run polling mode workflow.
async def run_polling_mode():
    """Coordinate the run polling mode logic in the application layer.

    Args:
        None.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    validate_runtime_config("polling")
    # Run this statement as part of the current workflow.
    ensure_schema_on_startup()

    # Wait for telegram_app.initialize before continuing this flow.
    await telegram_app.initialize()
    # Wait for telegram_app.bot.delete_webhook before continuing this flow.
    await telegram_app.bot.delete_webhook(drop_pending_updates=True)
    # Wait for telegram_app.start before continuing this flow.
    await telegram_app.start()
    # Run this statement as part of the current workflow.
    start_scheduler_once()

    # Handle the missing or empty telegram_app.updater case.
    if not telegram_app.updater:
        raise RuntimeError("Telegram updater tidak tersedia untuk polling mode.")

    # Wait for telegram_app.updater.start_polling before continuing this flow.
    await telegram_app.updater.start_polling(drop_pending_updates=True)
    print("✅ Bot started in polling mode. Tekan Ctrl+C untuk stop.")

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Wait for asyncio.Event before continuing this flow.
        await asyncio.Event().wait()
    # Run cleanup that must happen after the guarded operation.
    finally:
        # Handle the case where telegram_app.updater.running.
        if telegram_app.updater.running:
            # Wait for telegram_app.updater.stop before continuing this flow.
            await telegram_app.updater.stop()
        # Run this statement as part of the current workflow.
        shutdown_scheduler_once()
        # Wait for telegram_app.stop before continuing this flow.
        await telegram_app.stop()
        # Wait for telegram_app.shutdown before continuing this flow.
        await telegram_app.shutdown()


# Implementation section
# Implementation section

# Define run webhook mode for callers in this flow.
def run_webhook_mode():
    """Coordinate the run webhook mode logic in the application layer.

    Args:
        None.

    Returns:
        `None` after completing the operation.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    validate_runtime_config("webhook")
    # Open a multi-line structure for the values below.
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        # Prepare port for the next step.
        port=APP_PORT,
        # Prepare reload for the next step.
        reload=False,
    # Close the structure that was opened above.
    )


# ── Local Run ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if BOT_MODE == "polling":
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Run this statement as part of the current workflow.
            asyncio.run(run_polling_mode())
        # Handle an expected failure from the guarded operation above.
        except KeyboardInterrupt:
            print("\n👋 Bot stopped.")
    elif BOT_MODE == "webhook":
        # Run this statement as part of the current workflow.
        run_webhook_mode()
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Keep this section separated from the surrounding flow.
        raise RuntimeError("BOT_MODE harus 'polling' atau 'webhook'.")
