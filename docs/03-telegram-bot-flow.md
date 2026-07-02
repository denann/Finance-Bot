# 03. Telegram Bot Flow

Telegram logic lives in `app/bot/`.

The most important files are:

```text
app/bot/application.py
app/bot/handlers.py
app/bot/handler_parts/
```

## Why `application.py` exists

`application.py` builds the Telegram Application and registers every handler in one place.

This matters because polling mode and webhook mode should not have different handler behavior. Both modes use the same `build_telegram_app()` function.

High-level flow:

```text
build_telegram_app()
→ Application.builder().token(...).build()
→ register_handlers(telegram_app)
→ register_job_queue_jobs(telegram_app)
→ return telegram_app
```

## Atomic handler wrapper

Handlers are wrapped with `atomic_bot_handler()`.

The idea is practical: one Telegram input can trigger more than one Google Sheets write. For example, a split bill can save a transaction, create debt records, and update account balance. If one write fails, the wrapper allows the Sheets layer to attempt rollback.

## Commands

Main command handlers include:

| Command | Purpose |
|---|---|
| `/start` | Show welcome message |
| `/help` | Show help |
| `/examples`, `/contoh` | Show input examples |
| `/saldo` | Show account balances |
| `/transaksi` | Show transaction list |
| `/budget` | Show budget status |
| `/hutang` | Show debt summary |
| `/pending` | Show pending expenses |
| `/assets` | Show active assets |
| `/networth` | Show net worth summary |
| `/ask` | Ask a data-based finance question |
| `/audit` | Audit data quality and anomalies |
| `/coach` | Get finance coaching based on data |

## Message handlers

Message handlers are registered in this order:

```text
unknown command handler
→ image handler
→ text message handler
```

This order matters. Commands are handled differently from free text, images are routed to image parsing, and natural-language transaction inputs go to `message_handler()`.

## Callback handler

Inline buttons are handled by `callback_handler.py`.

Examples:

- `Edit dulu`
- `Lanjut`
- `Simpan`
- `Batal`
- account selection
- split bill decision
- debt decision
- clarification choice

The callback layer is where preview flow becomes an actual user decision.
