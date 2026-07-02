# app/bot

This folder contains the Telegram bot layer.

Its job is to receive user messages, commands, images, and button callbacks, then route them into the correct parser or service flow.

## Files and folders

| Item | Purpose |
|---|---|
| `application.py` | Builds the Telegram Application and registers all handlers |
| `handlers.py` | Re-export facade for handler modules |
| `keyboards.py` | Inline keyboard helpers |
| `handler_parts/` | Smaller handler modules grouped by feature |

The bot layer should focus on user interaction. Finance logic should stay in `app/services/`, and low-level data writing should stay in `app/sheets/`.
