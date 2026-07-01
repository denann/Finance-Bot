"""Endpoint FastAPI untuk menerima update Telegram saat bot dijalankan dengan webhook mode."""

from fastapi import APIRouter, Request, HTTPException, Header
from telegram import Update
from telegram.ext import Application
from app.config import TELEGRAM_WEBHOOK_SECRET

router = APIRouter()
_app: Application = None


def set_telegram_app(app: Application):
    """Helper untuk set telegram app pada API/webhook."""
    global _app
    _app = app


@router.post("/webhook")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    # Validasi secret token
    """Helper untuk webhook pada API/webhook."""
    if x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")

    data = await request.json()
    update = Update.de_json(data, _app.bot)
    await _app.process_update(update)
    return {"ok": True}