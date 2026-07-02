# 02. Runtime and Entrypoint

The main entrypoint is `main.py`.

The bot supports two runtime modes:

- `polling`: default and recommended for local setup or simple 24/7 deployment.
- `webhook`: optional advanced mode using FastAPI.

## Polling mode

```bash
python main.py
```

Polling mode starts the Telegram Application, removes old webhook configuration, starts the scheduler, and keeps reading updates from Telegram.

## Webhook mode

Webhook mode is used only when the deployment platform provides a public HTTPS endpoint.

```env
BOT_MODE=webhook
WEBHOOK_URL=https://your-domain.com
TELEGRAM_WEBHOOK_SECRET=your_secret
```

## Startup responsibilities

Startup validates config, prepares Google Sheets schema, initializes Telegram handlers, and starts scheduled jobs.
