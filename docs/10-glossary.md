# 10. Glossary

## Account

A wallet, bank account, or e-wallet used as a source or destination of money.

## Amount

The transaction value. Human input such as `20k`, `1.2jt`, or `2 juta` is normalized into a number.

## Atomic write

A best-effort pattern that groups several Google Sheets writes into one logical operation. If one write fails, the system tries to roll back previous writes.

## Callback

A Telegram event triggered by an inline button such as `Lanjut`, `Simpan`, or `Batal`.

## Clarification

A flow where the bot asks the user to clarify the meaning of an ambiguous input.

## Debt

A personal payable or receivable record.

## Ditalangin

An Indonesian finance term used when someone else pays first for the user. In this project, it usually creates a payable.

## Talangin

An Indonesian finance term used when the user pays first for someone else. In this project, it usually creates a receivable.

## Parse safety routing

The layer that decides whether parser output should go to normal preview, warning preview, Gemini draft, or clarification.

## Pending expense

A planned or incomplete expense that should not immediately change account balance.

## Polling mode

Runtime mode where the bot fetches updates from Telegram Bot API while the Python process is running.

## Preview before write

The safety principle that data should be reviewed by the user before it is saved to Google Sheets.

## Service layer

The layer that contains finance business logic, such as saving transactions, updating balances, settling debts, and calculating budgets.

## Split bill

A transaction shared with other people. The bot can create related debt records from the split.

## Webhook mode

Runtime mode where Telegram sends updates to a FastAPI endpoint.
