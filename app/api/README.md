# app/api

This folder contains the optional FastAPI layer for webhook deployment.

Polling is the default runtime for this project. The API layer is useful only when the bot is deployed with a public HTTPS webhook.

## Main files

- `webhook.py`: receives Telegram updates and forwards them to the Telegram Application.
- `diagnostics.py`: owns the disabled-by-default authenticated diagnostic route and sanitized checks.

## When to use it

Use this folder when you want an advanced deployment setup with `BOT_MODE=webhook`. For local development or simple Wispbyte deployment, use polling mode instead.

## Operational endpoints

- `GET /health`: liveness only; a running process can answer even when a dependency is not ready.
- `GET /ready`: returns 200 when configuration, Sheets/schema startup, Telegram, and the enabled scheduler are ready; otherwise returns 503.

Responses contain only generic component states. Raw provider errors, credentials, spreadsheet metadata, and finance input are not returned.

## Ownership Contract

The API owns HTTP adaptation only. Public entry points are webhook delivery, liveness, readiness, and the disabled-by-default authenticated diagnostic. It must not implement finance rules, expose raw dependency errors, or bypass confirmation. Integration and operational tests own verification.
