"""FastAPI webhook endpoint for receiving Telegram updates when webhook mode is enabled."""



# Import fastapi so this module can use its helpers.
from fastapi import APIRouter, Request, HTTPException, Header
# Import telegram so this module can use its helpers.
from telegram import Update
# Import telegram.ext so this module can use its helpers.
from telegram.ext import Application
# Import app.config so this module can use its helpers.
from app.config import TELEGRAM_WEBHOOK_SECRET

router = APIRouter()
_app: Application = None


# Helper for set telegram app.
def set_telegram_app(app: Application):
    """Coordinate the set telegram app logic in the API/webhook layer.

    Args:
        app: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May process webhook requests and interact with the configured Telegram application object.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    global _app
    _app = app


@router.post("/webhook")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    # Validasi secret token
    """Coordinate the webhook logic in the API/webhook layer.

    Args:
        request: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        x_telegram_bot_api_secret_token: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May process webhook requests and interact with the configured Telegram application object.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Handle x telegram bot api secret token != TELEGRAM WEBHOOK SECRET.
    if x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")

    data = await request.json()
    # Extract update for validation.
    update = Update.de_json(data, _app.bot)
    # Await  app.process update before continuing.
    await _app.process_update(update)
    # Keep this section separated from the surrounding flow.