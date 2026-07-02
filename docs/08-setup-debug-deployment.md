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
