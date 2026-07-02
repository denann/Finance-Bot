# 08. Setup, Debugging, and Deployment

This file explains the operational scripts and deployment path.

## Setup check

Run:

```bash
python scripts/setup_check.py
```

This script is built for new users. It checks whether the basic environment is ready before running the bot.

It validates:

- `.env` file,
- required environment variables,
- `ALLOWED_USER_ID`,
- service account JSON file,
- required Python packages,
- Google Sheets connection,
- Google Sheets schema.

## Debug check

Run:

```bash
python scripts/debug_check.py
```

This is deeper than setup check. It is useful for development and troubleshooting.

It checks:

- configuration,
- module imports,
- Google Sheets access,
- NLP parser,
- transaction service,
- report service,
- budget service,
- debt service,
- recurring service,
- net worth service,
- bot handlers,
- scheduler.

## Local run

Default runtime:

```env
BOT_MODE=polling
```

Run:

```bash
python main.py
```

The bot is active while the Python process is alive.

## Wispbyte polling deployment

For simple 24/7 deployment, keep polling mode.

Install command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python main.py
```

Important notes:

- Keep `BOT_MODE=polling`.
- Do not run the same bot token on your laptop and Wispbyte at the same time.
- Keep credentials private.
- Share the Google Sheets file with the service account email.

## Webhook deployment

Webhook mode is optional and more advanced.

```env
BOT_MODE=webhook
WEBHOOK_URL=https://your-domain.com
TELEGRAM_WEBHOOK_SECRET=your_secret
APP_PORT=8000
```

Run:

```bash
BOT_MODE=webhook python main.py
```

## Troubleshooting

| Problem | What to Check |
|---|---|
| Bot does not respond | Token, allowed user ID, running process, duplicate deployment |
| Google Sheets error | Sheet ID, service account file, sheet sharing access |
| Schema mismatch | Tab name and header order |
| Gemini error | API key and model name |
| Callback issue | `callback_handler.py` and user state in `context.user_data` |
