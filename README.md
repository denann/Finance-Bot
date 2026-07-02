# Personal Finance Bot

Personal Finance Bot is a Telegram-based personal finance assistant built to make daily financial tracking easier and more natural.

The project solves a practical problem: many people want to track their spending, debt, budget, and assets, but manual spreadsheet input often feels too slow and inconsistent. With this bot, users can send everyday transaction messages such as `beli kopi 25k`, `topup gopay 100k dari bsi`, or `ditalangin Budi bayar makan 100k`. The backend parses the input, validates the transaction logic, shows a preview, and saves structured records to Google Sheets only after user confirmation.

This project is useful for two types of users: people who want a lightweight personal finance assistant through chat, and developers who want to learn how Telegram Bot, Google Sheets, rule-based parsing, automation, and LLM-based assistance can work together in a real productivity use case.

> **Current language support:** the documentation is written in English for an international audience, but the bot features and natural-language transaction inputs are currently optimized for Indonesian. Examples such as `beli kopi 25k`, `utang`, `piutang`, `talangin`, and `ditalangin` are intentionally kept in Indonesian because they reflect the current product behavior.

## Outline

- [Features](#features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Code Documentation](#code-documentation)
- [Limitations and Troubleshooting](#limitations-and-troubleshooting)
- [Advanced Deployment](#advanced-deployment)
- [Author](#author)

## Features

| Group | Feature | Description |
|---|---|---|
| Input | Single Input | Records one transaction from a natural-language message. |
| Input | Multiple Input | Records several transactions from one message. |
| Input | Date, Amount, Account, and Category Parser | Reads relative dates, human amounts such as `25k` or `1.5 juta`, accounts, and categories. |
| Input | Utang, Piutang, Talangin, and Ditalangin | Supports personal payable/receivable tracking, including fronting money for others or being covered by someone else. |
| Input | Split Bill | Splits one transaction across several people and creates the related debt records. |
| Input | Pending Expense | Stores planned or incomplete expenses without immediately changing the account balance. |
| Input | Image Input | Reads receipts or transaction images using Gemini Vision. |
| Management | Debt Void, Debt Edit, Debt Settle | Manages debt status, cancellation, edits, and settlement. |
| Management | Delete Txn and Edit Txn | Edits or deletes existing transactions with controlled confirmation flow. |
| Summary | Balance | Shows the current balance across all accounts. |
| Summary | Account Report | Shows transactions and balance for a specific account. |
| Summary | Daily, Weekly, Monthly Report | Shows transaction summaries by period. |
| Summary | Search | Searches transactions by keyword. |
| Summary | Last and Transactions | Shows the latest transactions or a full transaction list. |
| Summary | Debt Summary | Shows active payable and receivable totals. |
| Budgeting | Add Budget | Adds monthly budget by category. |
| Budgeting | Budget History | Shows budget history and actual spending. |
| Recurring Transaction | Recurring Transaction | Handles recurring items such as Wi-Fi, token, subscriptions, or monthly fees. |
| Export Data | Export Data | Exports transaction data for backup or further analysis. |
| Net Worth and Assets | Net Worth and Assets | Tracks active assets and calculates net worth from account balance and assets. |
| Gemini RAG Finance Insight | Coach | Gives personal finance suggestions based on transaction data. |
| Gemini RAG Finance Insight | Audit | Checks data quality, anomalies, and possible input mistakes. |
| Gemini RAG Finance Insight | Ask | Answers natural questions such as “bulan ini boros di mana?”. |
| Gemini RAG Finance Insight | Insight | Explains spending patterns and improvement priorities. |
| Supporting | Typo Handling | Helps resolve typos in commands or transaction inputs. |
| Supporting | Scheduler | Runs scheduled jobs such as recurring transactions and exports. |

## Tech Stack

| Layer | Tools | Role in Project |
|---|---|---|
| Chat Interface | Telegram Bot API, python-telegram-bot | Receives messages, commands, images, and callback buttons from users. |
| Core Backend | Python | Runs parser logic, business rules, parse safety routing, preview flow, debt flow, split bill, pending expense, and transaction validation. |
| AI Layer | Gemini API, LangChain | Supports image parsing, finance insight, audit, coach, and data-based Q&A. The current LLM provider support is Gemini only. |
| Data Layer | Google Sheets API, gspread, Google Service Account | Stores transactions, accounts, budgets, debt, assets, pending expenses, recurring logs, and supporting data. |
| Automation | APScheduler | Runs recurring reminders, recurring transactions, exports, and scheduled jobs. |
| Deployment & Versioning | Wispbyte, FastAPI, Git, GitHub | Git and GitHub are used for version control. Wispbyte can run polling mode 24/7. FastAPI is available as an advanced webhook deployment option. |

<p align="center">
  <img src="assets/tech-stack-workflow-personal-finance-assistant.png" alt="Tech Stack Workflow of Personal Finance Assistant" width="1000">
</p>

The image summarizes how the tools work together. In the default setup, the main path is Telegram Bot API → python-telegram-bot → Python business logic → Google Sheets. FastAPI is optional and mainly exists for advanced webhook deployment.

## System Architecture

<p align="center">
  <img src="assets/workflow-ai-finance-assistant.png" alt="Workflow AI Finance Assistant" width="900">
</p>

The system has two main flows.

The first flow is **transaction recording**. Input from Telegram is processed by the parser, checked through parse safety routing, validated through preview, and saved to Google Sheets after user confirmation.

The second flow is **AI finance insight**. Users can ask through `/ask`, `/audit`, `/coach`, or `/insight`. The backend retrieves relevant financial context first, then Gemini helps explain the result based on that data.

The default runtime is **polling**. This means the Python process fetches updates from Telegram Bot API while the application is running. This approach is easier for local setup and can still run 24/7 on Wispbyte or another hosting provider as long as `python main.py` stays alive.

AI does not make final financial decisions by itself. The backend keeps control over business logic, while Gemini helps understand input, read images, and explain insights from available data.

## Installation

### 1. Clone and install dependencies

```bash
git clone https://github.com/username/denan-finance-bot.git
cd denan-finance-bot
python -m venv .venv
```

Activate the virtual environment.

Windows:

```bash
.venv\Scripts\activate
```

Mac/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Create `.env`

Copy `.env.example` to `.env`.

```bash
cp .env.example .env
```

Windows Command Prompt:

```cmd
copy .env.example .env
```

Minimum configuration:

```env
BOT_MODE=polling
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ALLOWED_USER_ID=your_telegram_user_id
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Set up Telegram

1. Open BotFather on Telegram.
2. Create a bot.
3. Copy the bot token.
4. Put it in `TELEGRAM_BOT_TOKEN`.
5. Put your Telegram user ID in `ALLOWED_USER_ID`.

`ALLOWED_USER_ID` is used so the bot only responds to the intended user.

### 4. Set up Google Sheets

1. Create a Google Sheets file.
2. Copy the spreadsheet ID from the URL.
3. Put it in `GOOGLE_SHEET_ID`.
4. Create a Google Service Account.
5. Download the service account JSON file.
6. Save it as `service_account.json` in the project root.
7. Share the Google Sheets file with the service account `client_email` as Editor.

Required tabs are prepared automatically:

```text
transactions
accounts
budgets
debts
debt_payments
categories
monthly_summary
recurring_rules
recurring_logs
assets
pending_expenses
net_worth_snapshots
```

The `accounts` sheet is seeded with default accounts when empty:

```text
Cash, BRI, BSI, BCA, DANA, GoPay, Seabank
```

The starting balances can be edited directly in Google Sheets.

### 5. Set up Gemini

`GEMINI_API_KEY` is used for AI parser, image parser, audit, coach, and finance insight features.

1. Open Google AI Studio.
2. Create a Gemini API key.
3. Copy the key.
4. Put it in `.env`.

Notes:

- The project currently supports Gemini as the LLM provider.
- Gemini model names can be changed through `.env`.
- Other providers such as Llama, OpenAI, Groq, Ollama, or OpenRouter are not supported out of the box and require a new adapter/client.

### 6. Check setup and run the bot

Run the setup check:

```bash
python scripts/setup_check.py
```

Run the bot:

```bash
python main.py
```

In polling mode, the bot runs as long as the Python process is alive.

### 7. Deploy 24/7 with Wispbyte (optional)

Wispbyte can run this bot using polling mode, so webhook setup is not required for the default deployment path.

Use:

```bash
pip install -r requirements.txt
python main.py
```

Important notes:

- Keep `BOT_MODE=polling`.
- Do not run the same bot token locally and on Wispbyte at the same time.
- Keep `service_account.json` private.
- If Wispbyte supports file secrets, store the service account JSON there instead of committing it to GitHub.

## Usage

### Example Inputs

| Input | Expected Meaning |
|---|---|
| `beli kopi 20k dari Cash` | Expense from Cash |
| `gaji masuk 8jt ke BCA` | Income to BCA |
| `BCA ke DANA 200k` | Transfer from BCA to DANA |
| `Budi minjem 50k` | Receivable from Budi |
| `ditalangin Budi bayar makan 100k` | Payable because Budi covered the user first |
| `makan 80k bagi dua sama Budi` | Split bill |
| `wifi bulan depan 285k` | Pending expense |

### Main Commands

```text
/start
/help
/examples
/saldo
/transaksi
/last
/cari
/budget
/hutang
/pending
/assets
/networth
/ask
/audit
/coach
/insight
/export
```

## Project Structure

```text
app/
├── api/                 # Optional FastAPI webhook endpoint
├── bot/                 # Telegram application and handler flow
├── nlp/                 # Parser, normalizer, Gemini parser, and parse safety
├── scheduler/           # Scheduled jobs
├── services/            # Finance business logic
├── sheets/              # Google Sheets client and schema bootstrap
└── config.py            # Environment-based configuration

scripts/
├── setup_check.py       # Lightweight setup checker
├── debug_check.py       # Developer diagnostic script
└── ai_command_tester.py # Local parser/command tester

docs/                    # Code and architecture documentation
assets/                  # README images and diagrams
main.py                  # Runtime entry point
```

## Code Documentation

Internal documentation is available in [`docs/`](docs/README.md).

Start from:

- [`docs/01-project-map.md`](docs/01-project-map.md) to understand the folder structure and layer responsibilities.
- [`docs/02-runtime-entrypoint.md`](docs/02-runtime-entrypoint.md) to understand polling mode, webhook mode, scheduler, and startup.
- [`docs/03-telegram-bot-flow.md`](docs/03-telegram-bot-flow.md) to understand Telegram handlers, commands, messages, and callbacks.
- [`docs/04-parser-nlp-parse-safety.md`](docs/04-parser-nlp-parse-safety.md) to understand regex parser, Gemini parser, and parse safety routing.
- [`docs/05-transaction-preview-flow.md`](docs/05-transaction-preview-flow.md) to understand preview, edit, confirmation, debt, split bill, pending expense, and asset flow.
- [`docs/06-data-layer-services.md`](docs/06-data-layer-services.md) to understand service layer, Google Sheets, schema bootstrap, and atomic write.
- [`docs/09-function-reference.md`](docs/09-function-reference.md) for a function and class index.

## Limitations and Troubleshooting

### Current limitations

- Natural-language features are currently optimized for Indonesian.
- The active LLM provider is Gemini.
- Google Sheets is used as the operational data store, so it is practical and transparent but not a full transactional database.
- Webhook deployment is optional and more advanced than polling mode.

### Common issues

| Issue | What to Check |
|---|---|
| Bot does not respond | Check `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_ID`, and whether `python main.py` is still running. |
| Google Sheets access error | Check `GOOGLE_SHEET_ID`, service account file, and whether the sheet is shared with `client_email`. |
| Schema mismatch | Check whether the sheet tabs and headers match the required schema. |
| Gemini error | Check `GEMINI_API_KEY` and selected Gemini model names. |
| Duplicate runtime | Do not run the same bot token locally and on hosting at the same time. |

## Advanced Deployment

Webhook mode is available for users who want to deploy with FastAPI.

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

or:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

For most users, polling mode is simpler and recommended as the default path.

## Author

Built as a personal productivity and AI finance assistant project. The project focuses on a practical workflow: natural chat input, backend validation, structured data storage, and AI-assisted financial explanation.
