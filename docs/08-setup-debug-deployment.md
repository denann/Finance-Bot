# 08. Setup, Debugging, and Deployment

Use these scripts before manual Telegram testing.

## Setup check

```bash
python scripts/setup_check.py
```

Checks environment variables, service account file, imports, Google Sheets access, and schema readiness.

## Debug check

```bash
python scripts/debug_check.py
```

Runs deeper checks for developers.

## Dummy Google Sheet debugging

To debug safely, create a dummy spreadsheet, share it with the same service account, and change only this value:

```env
GOOGLE_SHEET_ID=dummy_spreadsheet_id
```

You do not need a new Google Sheets API project if the same service account is still valid.

## Regression checks

Use inputs such as:

```text
/set_saldo BRI 2500000
/set_sald BRI 2500000
beli kopi 20k
Beli mie goreng 40k dibagi 2 sama Budi via DANA
```

Slash commands must not become expense previews.

## Web health and Sheets diagnostic

`GET /health` is the cheap, read-only liveness endpoint. It does not create worksheets, repair headers, or prove Google Sheets readiness.

`GET /ready` is the deployment-readiness endpoint. It returns HTTP 200 only after runtime configuration, Google Sheets/schema startup, Telegram startup, and the enabled scheduler are ready. It returns HTTP 503 with generic component states while startup is incomplete or a required component is degraded. Neither endpoint exposes credentials or raw exceptions.

The legacy `GET /test-sheets` route is now hidden and disabled by default:

```dotenv
ENABLE_TEST_SHEETS_ROUTE=false
DIAGNOSTIC_ADMIN_SECRET=
```

If an administrator explicitly enables it, the caller must send the separate `X-Admin-Secret` header. The route performs only a connectivity open, returns generic status, and never returns spreadsheet title, tab names, schema actions, credential details, or raw exceptions. Schema setup remains an explicit startup/setup operation, not an anonymous HTTP diagnostic.

Keep the route disabled in production unless there is a specific operational need. Do not reuse the Telegram webhook secret as the diagnostic secret.

## Runtime policy

Use Python 3.12, which is also the version exercised by offline CI. Finance dates use `APP_TIMEZONE=Asia/Jakarta`; operational timestamps and pending-action TTL calculations remain UTC.

The scheduler currently has a single-instance contract:

```dotenv
APP_INSTANCE_COUNT=1
SCHEDULER_ENABLED=true
LOG_LEVEL=INFO
```

Startup rejects `APP_INSTANCE_COUNT` above 1 while the scheduler is enabled. Multi-instance deployment needs distributed locking or a separate scheduler worker before it is supported. Set `SCHEDULER_ENABLED=false` only when another approved instance or worker owns scheduled jobs.

Gemini calls and Google Sheets retries can be bounded with the documented defaults:

```dotenv
GEMINI_TIMEOUT_SECONDS=30
GEMINI_MAX_OUTPUT_TOKENS=2048
GEMINI_MAX_OUTPUT_CHARS=50000
SHEETS_MAX_RETRIES=3
SHEETS_RETRY_BASE_DELAY=0.5
```

## Test setup

Install runtime and development dependencies separately:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
python -m compileall app main.py tests
```

The Phase 0 suite uses fakes/stubs and must not require a Telegram token, service account, spreadsheet, Gemini key, or internet connection. See `docs/testing.md` for the test matrix and staging-only checks.
