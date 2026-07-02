# 01. Project Map

This project is a Telegram-based personal finance assistant.

The practical flow is simple:

```text
User Telegram message
→ Telegram Bot API
→ python-telegram-bot handler
→ Python business logic
→ Parser / Preview / Confirmation
→ Google Sheets
```

For AI features:

```text
User question or image
→ Telegram handler
→ context builder or parser
→ Gemini
→ response to user
```

## Main folders

```text
app/
├── api/                 # Optional FastAPI webhook endpoint
├── bot/                 # Telegram application, commands, messages, callbacks
├── nlp/                 # Regex parser, normalizer, Gemini parser, parse safety
├── scheduler/           # Scheduled jobs
├── services/            # Finance business logic
├── sheets/              # Google Sheets access, schema bootstrap, rollback helper
└── config.py            # Environment configuration

scripts/                 # Setup checks, debug checks, and local testers
docs/                    # Architecture and code documentation
assets/                  # README images and diagrams
main.py                  # Runtime entry point
```

## Layer responsibility

| Layer | Main Files | Responsibility |
|---|---|---|
| Runtime | `main.py` | Select polling or webhook mode, start scheduler, prepare Sheets schema |
| Config | `app/config.py` | Load environment variables and sheet names |
| Telegram App | `app/bot/application.py` | Build the Telegram Application and register handlers |
| Commands | `app/bot/handler_parts/command_handlers.py` | Handle explicit commands such as `/saldo`, `/budget`, `/ask`, `/audit` |
| Messages | `app/bot/handler_parts/message_handlers.py` | Handle natural-language text and image input |
| Callbacks | `app/bot/handler_parts/callback_handler.py` | Handle inline buttons such as edit, continue, save, and cancel |
| Parser | `app/nlp/` | Parse Indonesian finance input into structured data |
| Services | `app/services/` | Apply finance business rules and read/write records |
| Data Layer | `app/sheets/client.py` | Connect to Google Sheets, validate schema, retry writes, and rollback when possible |

## Mental model

The project intentionally separates three responsibilities:

1. **Handler layer** decides what the user is trying to do.
2. **Service layer** decides what finance data should change.
3. **Sheets layer** decides how data is read or written safely.

This makes debugging easier. If the parser reads an input incorrectly, start from `app/nlp/`. If a button flow is wrong, check `transaction_flow.py` or `callback_handler.py`. If saved data is wrong, check the relevant service file. If Sheets fails, check `app/sheets/client.py` and the environment setup.
