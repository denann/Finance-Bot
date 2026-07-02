# app/api

This folder contains the optional FastAPI API layer.

The project uses polling mode by default, so this folder is not required for the simplest setup. It exists for advanced webhook deployment, where Telegram sends updates to a public endpoint instead of being fetched by polling.

## Files

| File | Purpose |
|---|---|
| `webhook.py` | Receives Telegram webhook requests and forwards them to the Telegram Application |

Use this folder when deploying the bot with `BOT_MODE=webhook`.
