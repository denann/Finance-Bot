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

The legacy `GET /test-sheets` route is now hidden and disabled by default:

```dotenv
ENABLE_TEST_SHEETS_ROUTE=false
DIAGNOSTIC_ADMIN_SECRET=
```

If an administrator explicitly enables it, the caller must send the separate `X-Admin-Secret` header. The route performs only a connectivity open, returns generic status, and never returns spreadsheet title, tab names, schema actions, credential details, or raw exceptions. Schema setup remains an explicit startup/setup operation, not an anonymous HTTP diagnostic.

Keep the route disabled in production unless there is a specific operational need. Do not reuse the Telegram webhook secret as the diagnostic secret.

## Test setup

Install runtime and development dependencies separately:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
python -m compileall app main.py tests
```

The Phase 0 suite uses fakes/stubs and must not require a Telegram token, service account, spreadsheet, Gemini key, or internet connection. See `docs/testing.md` for the test matrix and staging-only checks.
