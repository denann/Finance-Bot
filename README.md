# Personal Finance Bot

Personal Finance Bot is a Telegram-based personal finance assistant built to make daily financial tracking easier, faster, and more natural.

The core idea is simple: users can write everyday finance inputs such as `beli kopi 25k`, `topup gopay 100k dari bsi`, or `Beli mie goreng 40k dibagi 2 sama Budi via DANA`. The backend parses the input, checks the risk level, shows a preview, lets the user edit or cancel, and only writes structured data to Google Sheets after confirmation.

> **Current language support**  
> The code documentation is written in English for an international audience. However, the current bot features, natural-language parser, examples, and user-facing messages are still optimized for Indonesian finance input. This is intentional for now because the product is built around Indonesian daily usage patterns.

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

| Area | Feature | What it does |
|---|---|---|
| Transaction input | Single input | Records one expense, income, or transfer from a natural chat message. |
| Transaction input | Multi input | Accepts multiple transactions in one message and previews them before saving. |
| Transaction input | Image input | Reads receipt or transaction images using Gemini Vision. Itemized receipts show OCR details first, convert selected rows into a detailed batch preview, ask for the account, then show a compact final summary before saving. |
| Transaction input | Date and account parsing | Reads dates, amounts, accounts, categories, and descriptions from Indonesian-style input. |
| Debt | Payable and receivable | Tracks personal debt and receivables, including payment and settlement flows. |
| Debt | Talangin / ditalangin | Handles cases where the user pays for someone else or someone else pays first for the user. |
| Split bill | Paid or unpaid split | Supports split bill flows where friends have already paid or still owe the user. |
| Planning | Pending expense | Stores future or planned expenses without immediately changing account balances. |
| Automation | Recurring rules | Creates recurring transaction rules and logs scheduled runs. |
| Control | Preview before write | Uses preview, edit, save, cancel, warning preview, and clarification before writing data. |
| Account | Set balance | Lets users set an account balance through `/set_saldo` with confirmation preview. |
| Reporting | Daily, weekly, monthly reports | Summarizes transactions by period, category, account, and spending type. |
| Net worth | Assets and snapshots | Tracks assets and creates net worth snapshots over time. |
| AI insight | Ask, audit, coach, insight | Uses Gemini to explain finance data based on structured context from Google Sheets. |
| Deployment | Polling-first setup | Runs locally with `python main.py` or 24/7 on Wispbyte without requiring webhook setup. |

## Tech Stack

| Layer | Tools | Role |
|---|---|---|
| Bot interface | Telegram Bot API, python-telegram-bot | Receives messages, commands, images, and button callbacks. |
| Runtime | Python | Runs parser logic, business rules, handlers, and services. |
| Optional API | FastAPI | Optional webhook runtime for advanced deployment. Polling is the default mode. |
| Data store | Google Sheets API, gspread | Stores transactions, accounts, debts, budgets, recurring rules, assets, and snapshots. |
| AI layer | Gemini API, LangChain | Helps with image parsing, finance insight, audit, coach, and Q&A. |
| Scheduler | APScheduler, JobQueue | Runs recurring jobs, exports, reminders, and automated summaries. |
| Deployment | Wispbyte, GitHub | Runs the bot 24/7 and manages project versioning. |

![Tech Stack Workflow](assets/tech-stack-workflow-personal-finance-assistant.png)

## System Architecture

![AI Finance Assistant Workflow](assets/workflow-ai-finance-assistant.png)

The system has two main flows.

First, the transaction flow: Telegram input is parsed by local rules or Gemini fallback, checked by parse safety, shown as a preview, and saved to Google Sheets only after user confirmation.

Second, the AI insight flow: commands such as `/ask`, `/audit`, `/coach`, and `/insight` build a structured finance context from Google Sheets before Gemini generates the response.

The LLM is not the final decision maker. Business logic stays in Python, while AI helps interpret input, read images, extract receipt details, and explain data.

## Installation

### 1. Clone and install dependencies

```bash
git clone <your-repository-url>
cd <your-project-folder>
python -m venv .venv
```

Activate the virtual environment.

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Create `.env`

Copy the example file:

```bash
cp .env.example .env
```

Minimum local setup:

```env
BOT_MODE=polling
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ALLOWED_USER_ID=your_telegram_user_id
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Setup Telegram

#### 3.1 Create a bot token with BotFather

1. Open Telegram.
2. Search for `@BotFather`.
3. Send `/start`.
4. Send `/newbot`.
5. Choose a bot display name, for example `Denan Finance Bot`.
6. Choose a unique username ending with `bot`, for example `denan_finance_bot`.
7. BotFather will return a token.
8. Copy the token into `.env`:

```env
TELEGRAM_BOT_TOKEN=123456789:AAExampleTokenHere
```

Keep this token private. Anyone with this token can control your bot.

#### 3.2 Get your Telegram user ID with RawDataBot

The bot uses `ALLOWED_USER_ID` so only your Telegram account can access your finance data.

1. Search for `@RawDataBot` on Telegram.
2. Send `/start`.
3. RawDataBot will return a JSON-like response.
4. Take the `id` inside the `from` object.

Masked example:

```json
{
  "update_id": "***masked***",
  "message": {
    "message_id": "***masked***",
    "from": {
      "id": "1234567890",
      "is_bot": false,
      "first_name": "Your First Name",
      "last_name": "Your Last Name",
      "username": "your_username",
      "language_code": "en"
    },
    "chat": {
      "id": "1234567890",
      "type": "private"
    },
    "text": "/start"
  }
}
```

Use that value in `.env`:

```env
ALLOWED_USER_ID=1234567890
```

### 4. Setup Google Sheets

#### 4.1 Create the spreadsheet

1. Open Google Sheets.
2. Create a blank spreadsheet.
3. Rename it, for example `Finance Bot Database`.
4. Copy the spreadsheet ID from the URL.

Example URL:

```text
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit#gid=0
```

Add it to `.env`:

```env
GOOGLE_SHEET_ID=SPREADSHEET_ID_HERE
```

#### 4.2 Create a Google Cloud project

1. Open Google Cloud Console.
2. Create a new project, for example `finance-bot-project`.
3. Open **APIs & Services**.
4. Enable these APIs:
   - Google Sheets API
   - Google Drive API

#### 4.3 Create a service account

1. Open **IAM & Admin → Service Accounts**.
2. Click **Create Service Account**.
3. Set a name, for example `finance-bot-service-account`.
4. Finish the setup.
5. Open the service account.
6. Go to **Keys**.
7. Click **Add key → Create new key**.
8. Choose JSON.
9. Download the JSON file.
10. Rename it to:

```text
service_account.json
```

Put it in the project root, then set:

```env
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
```

#### 4.4 Share the spreadsheet to the service account

Open `service_account.json` and find:

```json
"client_email": "finance-bot-service-account@your-project.iam.gserviceaccount.com"
```

Then:

1. Open your Google Sheet.
2. Click **Share**.
3. Paste the `client_email`.
4. Give **Editor** access.
5. Click **Send**.

This step is required. Without it, the bot can authenticate but cannot access your spreadsheet.

#### 4.5 Required sheet headers

The bot can create missing tabs and headers automatically when the spreadsheet is empty. If a sheet already has data, the bot will not reorder columns automatically to avoid damaging existing records.

Required tabs and headers:

```text
transactions:
id, date, type, amount, category, account, to_account, subject, description, catatan, tipe_pengeluaran, raw_input, parsed_by, hutang_id, tipe_hutang

accounts:
account_name, type, balance, currency, last_updated

budgets:
id, month, category, budget_amount, created_at, updated_at

debts:
id, type, person_name, original_amount, remaining_amount, description, due_date, is_settled, created_at, settled_at, source_transaction_id, cashflow_mode, fronting_mode

debt_payments:
id, debt_id, amount, date, note

categories:
category_name, type, emoji, aliases

monthly_summary:
month, total_income, total_expense, net, created_at, updated_at

recurring_rules:
id, name, type, amount, category, account, to_account, subject, description, catatan, tipe_pengeluaran, frequency, day_of_month, next_run_date, is_active, created_at, updated_at

recurring_logs:
id, rule_id, transaction_id, run_date, status, message, created_at

assets:
id, name, category, current_value, description, is_active, created_at, updated_at, asset_type, quantity, unit, price_source, price_per_unit, last_price_update, purchase_price_per_unit, purchase_date

pending_expenses:
id, due_date, month, due_precision, amount, category, account, subject, description, status, created_at, updated_at, paid_transaction_id, raw_input

net_worth_snapshots:
id, snapshot_date, total_accounts, total_assets, total_liabilities, net_worth, created_at
```

### 5. Setup Gemini

Gemini is used for image parsing, AI finance insight, audit, coach, and Q&A.

1. Open Google AI Studio.
2. Create an API key.
3. Copy the API key.
4. Add it to `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Optional model configuration:

```env
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_TEXT_MODEL=gemini-3.1-flash-lite
GEMINI_INTENT_MODEL=gemini-3.1-flash-lite
GEMINI_IMAGE_MODEL=gemini-3.1-flash-lite
GEMINI_INSIGHT_MODEL=gemini-3.1-flash-lite
```

At the moment, Gemini is the only LLM provider supported out of the box. Other providers need a new adapter or client implementation.

### 6. Check setup and run the bot

Run the setup checker:

```bash
python scripts/setup_check.py
```

Then run the bot:

```bash
python main.py
```

Open your bot on Telegram and send:

```text
/start
/quickstart
```

### 7. Deploy 24/7 with Wispbyte

For a simple 24/7 deployment, keep using polling mode.

Install command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python main.py
```

Recommended flow:

```text
Push project to GitHub
→ Connect the repository to Wispbyte
→ Add environment variables
→ Upload or configure service_account.json securely
→ Use python main.py as the start command
```

Do not run the same bot token on your laptop and Wispbyte at the same time.

## Usage

### First-time flow

Start with:

```text
/quickstart
```

Then check available accounts:

```text
/set_saldo
```

Set an initial balance:

```text
/set_saldo DANA 500k
/set_saldo BRI 2500000
```

`/set_saldo` does not create a transaction row. It only updates the selected account balance after confirmation.

### Transaction examples

```text
beli kopi 20k
beli kopi 20k dari DANA
gaji masuk 8jt ke BRI
BCA ke DANA 200k
```

### Multi input

```text
beli kopi 20k dari Cash, beli bensin 50k dari BRI, gaji masuk 8jt ke BCA
```

### Debt and receivable

```text
Budi minjem 50k dari DANA
saya pinjam 100k ke Budi
Budi bayar 25k ke DANA
saya bayar hutang Budi 50k dari BRI
```

### Talangin and ditalangin

```text
saya talangin Budi beli nasi 20k dari DANA
saya ditalangin Bagas beli nasi 15k
```

### Split bill

```text
Beli mie goreng 40k dibagi 2 sama Budi via DANA
makan 120k patungan bertiga sama Budi dan Rina dari BCA
```

If friends already paid, the saved expense should use only the user's net share. If they have not paid, the bot records the gross paid amount and creates receivable records.

### Pending expense

```text
nanti bayar wifi 285k bulan depan
/pending_add bayar wisuda 750k tgl 30
```

### AI insight

```text
/ask bulan ini boros di mana?
/audit
/coach
/insight
```

## Project Structure

```text
app/
├── api/                 # Optional FastAPI webhook endpoint
├── bot/                 # Telegram Application and handler modules
├── nlp/                 # Parser, normalizer, parse safety, and Gemini helpers
├── scheduler/           # APScheduler and JobQueue jobs
├── services/            # Finance business logic
└── sheets/              # Google Sheets client and schema handling

docs/                    # Technical documentation
scripts/                 # Setup, debug, and regression scripts
assets/                  # README diagrams
main.py                  # Application entry point
```

## Code Documentation

Folder-level and technical documentation are available in `docs/` and each major subfolder README.

Start here:

- `docs/01-project-map.md`
- `docs/02-runtime-entrypoint.md`
- `docs/03-telegram-bot-flow.md`
- `docs/04-parser-nlp-parse-safety.md`
- `docs/05-transaction-preview-flow.md`
- `docs/06-data-layer-services.md`
- `docs/07-ai-insight-layer.md`
- `docs/08-setup-debug-deployment.md`
- `docs/09-function-reference.md`
- `docs/10-glossary.md`

## Limitations and Troubleshooting

### Limitations

1. The current natural-language parser is optimized for Indonesian input.
2. Google Sheets is practical and transparent, but it is not a full transactional database.
3. This project is designed for personal use, not as a full SaaS multi-user product.
4. AI features depend on Gemini API availability and model quality.
5. Ambiguous inputs still need user confirmation, edit, or clarification.

### Troubleshooting

If the bot does not respond:

- Check whether `python main.py` is still running.
- Check `TELEGRAM_BOT_TOKEN`.
- Check `ALLOWED_USER_ID`.
- Make sure the same bot token is not running in two places.

If Google Sheets fails:

- Make sure the spreadsheet is shared to the service account `client_email`.
- Make sure Google Sheets API and Google Drive API are enabled.
- Run `python scripts/setup_check.py`.

If a slash command becomes a transaction preview:

- Apply the latest routing patch.
- Slash commands should never be parsed as expenses.
- Test `/set_saldo BRI 2500000` and `/set_sald BRI 2500000` as regression checks.

## Advanced Deployment

Webhook mode is optional. Use it only if your hosting environment supports a public HTTPS endpoint.

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

Polling mode is still the recommended default for local use and simple 24/7 deployment.

## Author

Built as a personal finance automation and AI assistant project. The project connects backend logic, Google Sheets data management, Telegram UX, and AI-assisted explanation into one practical daily-use workflow.
