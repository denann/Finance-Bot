# 02. Runtime & Entrypoint

The main entry point is `main.py`.

This file is responsible for running the bot in one of two modes:

1. **Polling mode**, which is the default and simplest path.
2. **Webhook mode**, which is optional and uses FastAPI.

## Runtime mode

Runtime mode is controlled by:

```env
BOT_MODE=polling
```

or:

```env
BOT_MODE=webhook
```

`app/config.py` validates this value so the app only accepts supported modes.

## Polling mode

Polling mode runs when the user executes:

```bash
python main.py
```

The high-level flow is:

```text
validate_runtime_config("polling")
→ ensure_schema_on_startup()
→ telegram_app.initialize()
→ delete_webhook(drop_pending_updates=True)
→ telegram_app.start()
→ start_scheduler_once()
→ updater.start_polling()
```

Important details:

- `delete_webhook()` prevents conflicts with an old webhook setup.
- `ensure_schema_on_startup()` prepares Google Sheets tabs and headers.
- Scheduler jobs still run in polling mode.
- The bot stays active as long as the Python process stays alive.

## Webhook mode

Webhook mode runs FastAPI:

```bash
BOT_MODE=webhook python main.py
```

or:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Startup flow:

```text
validate_runtime_config("webhook")
→ telegram_app.initialize()
→ telegram_app.start()
→ ensure_schema_on_startup()
→ set_webhook(WEBHOOK_URL + "/webhook")
→ start_scheduler_once()
```

Webhook mode requires:

```env
WEBHOOK_URL=https://your-domain.com
TELEGRAM_WEBHOOK_SECRET=your_secret
```

## Scheduler lifecycle

The scheduler is created once and started only when needed:

```text
create_scheduler()
→ start_scheduler_once()
```

This prevents duplicate scheduler starts when the app is initialized more than once.

## Operational endpoints

| Endpoint | Purpose |
|---|---|
| `/health` | Confirms that the app is running and shows the current mode |
| `/test-sheets` | Checks Google Sheets access and schema readiness |

These endpoints are mainly useful in webhook or hosted environments.
