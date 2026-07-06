"""FastAPI webhook endpoint for receiving Telegram updates when webhook mode is enabled."""



# Import fastapi so this module can use its helpers.
from fastapi import APIRouter, Request, HTTPException, Header
# Import telegram so this module can use its helpers.
from telegram import Update
# Import telegram.ext so this module can use its helpers.
from telegram.ext import Application
# Import app.config so this module can use its helpers.
from app.config import TELEGRAM_WEBHOOK_SECRET

# Prepare router for the next step.
router = APIRouter()
# Run this statement as part of the current workflow.
_app: Application = None


# Define set telegram app for callers in this flow.
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
    # Run this statement as part of the current workflow.
    global _app
    # Prepare app for the next step.
    _app = app


@router.post("/webhook")
# Handle the asynchronous webhook workflow.
async def webhook(
    # Include this value in the surrounding collection or call.
    request: Request,
    # Run this statement as part of the current workflow.
    x_telegram_bot_api_secret_token: str = Header(None)
# Close the structure that was opened above.
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
    # Handle the case where x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET.
    if x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Prepare data for the next step.
    data = await request.json()
    # Prepare update for the next step.
    update = Update.de_json(data, _app.bot)
    # Wait for _app.process_update before continuing this flow.
    await _app.process_update(update)
    # Keep this section separated from the surrounding flow.