# app/api

This folder contains the optional FastAPI layer for webhook deployment.

Polling is the default runtime for this project. The API layer is useful only when the bot is deployed with a public HTTPS webhook.

## Main file

- `webhook.py`: receives Telegram updates and forwards them to the Telegram Application.

## When to use it

Use this folder when you want an advanced deployment setup with `BOT_MODE=webhook`. For local development or simple Wispbyte deployment, use polling mode instead.
