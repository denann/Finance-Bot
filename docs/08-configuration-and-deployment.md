# Configuration and Deployment

## Configuration Contract

`.env.example` is a safe template. `app/config.py` owns central settings; the Sheets adapter and diagnostic route own a small number of direct environment reads. Never commit `.env`, service-account JSON, tokens, private keys, or production identifiers.

| Name | Req/default | Allowed values | Sensitive | Purpose and guidance |
| :--- | :--- | :--- | :--- | :--- |
| `BOT_MODE` | Optional; `polling` | `polling`, `webhook` | No | Polling is primary; webhook runs FastAPI/uvicorn |
| `APP_PORT` | Optional; `8000` | Positive integer | No | Web server port |
| `APP_TIMEZONE` | Optional; `Asia/Jakarta` | IANA timezone | No | Business-time configuration; current finance behavior assumes Jakarta |
| `APP_INSTANCE_COUNT` | Optional; `1` | Positive integer | No | Must be `1` when scheduler is enabled |
| `SCHEDULER_ENABLED` | Optional; `true` | Boolean | No | One in-process scheduler owner |
| `LOG_LEVEL` | Optional; `INFO` | Python log level | No | Structured log threshold |
| `LOG_FILE` | Optional; `logs/finance_bot.log` | Relative or absolute file path; empty disables file logging | No | Appends one structured JSON event per line while keeping console output |
| `TELEGRAM_BOT_TOKEN` | Required at runtime | BotFather token | Yes | Telegram authentication; use dummy/fake values only in offline tests |
| `ALLOWED_USER_ID` | Required for private use; default `0` | Integer Telegram user ID | Personal | Single authorized owner |
| `TELEGRAM_WEBHOOK_SECRET` | Required in webhook mode | Opaque secret | Yes | Verifies Telegram webhook header |
| `WEBHOOK_URL` | Required in webhook mode | Public HTTPS base URL | Operational | Webhook registration target |
| `GOOGLE_SHEET_ID` | Required | Spreadsheet ID | Yes | Persistence target |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Optional path; `service_account.json` | Local JSON path | Yes | Service-account credentials path |
| `SHEETS_MAX_RETRIES` | Optional; adapter default `5` | Non-negative integer | No | One adapter-owned retry policy |
| `SHEETS_RETRY_BASE_DELAY` | Optional; adapter default `1.0` | Positive seconds | No | Exponential backoff base |
| `SHEETS_TIMEOUT_SECONDS` | Optional; `20` | Positive seconds | No | Bounded read/scheduled wait |
| `SHEETS_INTERACTIVE_CONCURRENCY` | Optional; `2` | Positive integer | No | Interactive worker capacity |
| `SCHEDULED_WORK_CONCURRENCY` | Optional; `1` | Positive integer | No | Separate scheduled capacity |
| `SHEETS_REQUEST_ROW_BUDGET` | Optional; `50000` | Positive integer | No | Per-request transferred-row ceiling |
| `TRANSACTION_SORT_MODE` | Optional; `server` | `server`, `legacy` | No | Server sort default; legacy emergency rollback only |
| `GEMINI_API_KEY` | Required only for live AI | Provider key | Yes | Gemini authentication |
| `GEMINI_MODEL` | Optional | Supported configured model ID | No | General text model |
| `GEMINI_TEXT_MODEL` | Optional | Supported configured model ID | No | Transaction parser model |
| `GEMINI_INTENT_MODEL` | Optional | Supported configured model ID | No | Intent router model |
| `GEMINI_IMAGE_MODEL` | Optional | Supported configured model ID | No | Image parser model |
| `GEMINI_INSIGHT_MODEL` | Optional | Supported configured model ID | No | Finance answer model |
| `GEMINI_TIMEOUT_SECONDS` | Optional; `30` | Positive seconds | No | AI worker timeout |
| `GEMINI_CONCURRENCY` | Optional; `1` | Positive integer | No | Gemini worker capacity |
| `GEMINI_MAX_INPUT_CHARS` | Optional; `100000` | Positive integer | No | Hard prompt-size bound |
| `GEMINI_MAX_OUTPUT_TOKENS` | Optional; `2048` | Positive integer | No | Provider output-token request bound |
| `GEMINI_MAX_OUTPUT_CHARS` | Optional; `50000` | Positive integer | No | Extracted output bound |
| `GEMINI_CALLS_PER_UPDATE` | Optional; `1` | Positive integer | No | Shared primary call budget |
| `AI_CONTEXT_RECORD_LIMIT` | Optional; `40` | Positive integer | No | Relevant transaction cap |
| `ENABLE_TEST_SHEETS_ROUTE` | Optional; `false` | Boolean text | No | Enables hidden read-only diagnostic route; keep false in production |
| `DIAGNOSTIC_ADMIN_SECRET` | Required if diagnostic route enabled | Opaque secret | Yes | Authenticates `/test-sheets` |

## Local Development

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python scripts/setup_check.py
python main.py
```

Use a dummy spreadsheet and keep `BOT_MODE=polling`. Startup validates configuration, initializes Telegram, checks Sheets schema readiness, starts one scheduler when enabled, and shuts Telegram/scheduler down on exit.

## Webhook and FastAPI

Webhook mode requires `WEBHOOK_URL`, `TELEGRAM_WEBHOOK_SECRET`, and `APP_PORT`. `GET /health` is liveness only. `GET /ready` returns 200 only when generic configuration, Sheets/schema, Telegram, enabled scheduler, and startup state are ready; otherwise 503. The hidden `/test-sheets` route is disabled by default and requires its own admin secret.

## Wispbyte and Hosted Deployment

Use the repository startup command `python main.py`, configure secrets in the host environment, keep one instance, and do not run the same bot token concurrently on a laptop. Polling remains the simplest supported Wispbyte path. Webhook deployment additionally needs a stable HTTPS URL and correct port exposure.

## Staging and Production Smoke Test

1. Run all offline tests and documentation checks.
2. Back up the target spreadsheet.
3. Use dummy Sheets and a dedicated test bot first.
4. Verify `/health`, `/ready`, one natural transaction preview/cancel, one confirmed dummy transaction, physical sort order, reports, scheduler ownership, and opt-in AI.
5. Inspect redacted logs and reconciliation indicators.
6. Promote the same configuration shape with production secrets stored only in the platform.

Real staging is required; offline tests do not establish Telegram delivery, gspread latency, provider timeout, or production SLOs.

| Documentation update | Status |
| :--- | :--- |
| Supported variables | Documented |
| Polling/webhook and health/readiness | Documented |
| Single process and scheduler owner | Documented |
| Secrets | Placeholder guidance only |
