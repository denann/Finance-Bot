# 03. Telegram Bot Flow

The Telegram layer lives in `app/bot`.

## Main flow

```text
Telegram update
→ Application handler
→ command/message/callback handler
→ parser or service
→ reply to user
```

## Handler types

- Command handler: handles slash commands such as `/saldo`, `/quickstart`, `/set_saldo`, and `/ask`.
- Message handler: handles natural text input and image input.
- Callback handler: handles inline buttons such as save, edit, cancel, account choice, and split bill decisions.

## Important rule

Slash commands should never be parsed as transactions. If a message starts with `/`, it must go to command handling or unknown command handling, not to the expense parser.
