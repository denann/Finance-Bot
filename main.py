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


# FastAPI tetap tersedia untuk mode deployment lanjutan.
# Untuk penggunaan lokal dan Wispbyte polling, default runtime project adalah polling mode.
app = FastAPI(title="Finance Bot")
app.include_router(webhook_router)

telegram_app = build_telegram_app()
set_telegram_app(telegram_app)

scheduler = create_scheduler()
_webhook_telegram_started = False


def validate_runtime_config(mode: str = BOT_MODE):
    """Validasi env wajib sesuai runtime mode yang dipilih."""
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
    """Siapkan schema Google Sheets jika credential dan akses sudah benar."""
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
        # Jangan matikan bot hanya karena Sheets belum siap.
        # Handler pertama yang butuh Sheets tetap akan mengangkat error yang jelas.
        print(f"⚠️ Google Sheets schema belum bisa dipastikan: {exc}")


def start_scheduler_once():
    if not scheduler.running:
        scheduler.start()
        print(f"✅ Scheduler started. Jobs: {[job.name for job in scheduler.get_jobs()]}")


def shutdown_scheduler_once():
    if scheduler.running:
        scheduler.shutdown()


# ── FastAPI startup & shutdown, hanya aktif saat webhook mode dijalankan ──────
@app.on_event("startup")
async def startup():
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
    global _webhook_telegram_started

    shutdown_scheduler_once()
    if _webhook_telegram_started:
        await telegram_app.stop()
        await telegram_app.shutdown()
        _webhook_telegram_started = False


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "ok", "mode": BOT_MODE}


@app.get("/test-sheets")
async def test_sheets():
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
# Polling adalah mode default untuk user GitHub/Wispbyte.
# delete_webhook() dipanggil dulu agar bot yang pernah memakai webhook bisa kembali menerima update lewat polling.

async def run_polling_mode():
    """Jalankan bot memakai Telegram long polling untuk setup lokal sederhana."""
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


# Webhook tetap disediakan untuk deployment advanced.
# Mode ini membutuhkan public URL dan FastAPI, berbeda dari polling yang cukup menjalankan proses Python.

def run_webhook_mode():
    """Jalankan FastAPI app untuk deployment webhook."""
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
