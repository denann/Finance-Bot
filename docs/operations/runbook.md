# Operations Runbook

## Pre-Deployment

1. Confirm `git status` contains only reviewed changes.
2. Run pytest, documentation checks, compileall, and `git diff --check`.
3. Validate `.env` with `python scripts/setup_check.py` without printing secrets.
4. Confirm one application instance and one scheduler owner.
5. Back up the spreadsheet and record its recovery location.
6. Complete dummy-Sheets staging before production.

## Deploy and Verify

1. Stop the previous process cleanly.
2. Deploy the reviewed version and required environment variables.
3. Start `python main.py` in polling or configured webhook mode.
4. Verify `/health` responds and `/ready` reports ready where HTTP is exposed.
5. Send `/health`, `/start`, and `/saldo` from the authorized Telegram user.
6. Create then cancel a dummy preview; confirm no write occurred.
7. Save one approved dummy transaction and inspect ID, balance, and physical sort order.
8. Verify scheduler job count once, then one opt-in Gemini feature if approved.
9. Inspect logs for opaque correlation IDs and absence of raw finance/credential data.

## Incident Matrix

| Incident | Immediate action | Recovery |
| :--- | :--- | :--- |
| Sheets unavailable | Stop repeated mutations; keep process/liveness separate from readiness | Check sharing, key path, quota, schema, and `/ready`; retry reads only after dependency recovery |
| Gemini unavailable | Do not repeat image/text calls outside budget | Use deterministic fallback/clarification; verify key/model/quota privately |
| Reconciliation required | Stop the affected flow and do not retry | Inspect candidate IDs, ledger, account, debt/payment rows; repair through approved flow |
| Duplicate-looking transaction | Pause recurring/manual repetition | Compare immutable IDs, raw intent, timestamps, recurring logs, and balances before deletion |
| Stale callback | Do not recreate mutation from old button | Start a new preview; expected after expiry/restart/consumption |
| Scheduler duplication | Stop extra processes immediately | Restore one instance/owner; reconcile recurring logs and generated transaction IDs |
| Transaction sort failed | Do not repeat append | Verify transaction exists, use read-side ordering, retry maintenance separately; use `legacy` only as approved rollback |
| Readiness 503 | Keep liveness diagnosis separate | Inspect generic component status and startup logs without exposing secrets |

## Backup and Restore

Before restore, stop every writer and export a copy of the current damaged state for evidence. Restore the approved spreadsheet backup, re-share with the service account, verify all 12 worksheet headers, inspect latest IDs and balances, then run read-only reports before enabling mutations or scheduler jobs.

## Application Rollback

Deploy the last reviewed application version without reverting the spreadsheet automatically. Configuration rollback units include server sort (`TRANSACTION_SORT_MODE=legacy` only when approved), worker limits/timeouts, snapshot wiring, and Gemini governance wiring. Never lower write safety merely to make readiness green.

## Restart Procedure

1. Stop gracefully so Telegram and scheduler shutdown handlers run.
2. Confirm no second process owns the token or scheduler.
3. Start the reviewed version.
4. Expect old pending-action buttons to fail closed because pending state is in memory.
5. Verify readiness and scheduler once.

## Log and Privacy Review

Search structured events by opaque correlation ID, feature, operation, duration, outcome, and error type. Do not paste full logs into public channels until checking for Telegram messages, finance descriptions, names, account labels, IDs, receipt content, tokens, private keys, service-account fields, and spreadsheet identifiers.

## Post-Deployment

- Health/readiness and Telegram smoke checks passed.
- One scheduler owner confirmed.
- Dummy write, balance, sort, report, and reconciliation telemetry verified.
- Gemini opt-in call count/usage metadata checked when approved.
- Logs and exported files handled as sensitive.
- Backup and rollback version remain available.

Production rollout requires explicit owner approval after real staging. This runbook does not authorize use of production credentials by automated tests.

| Runbook area | Status |
| :--- | :--- |
| Deployment and smoke test | Documented |
| Sheets/Gemini/reconciliation incidents | Documented |
| Backup, restore, rollback, restart | Documented |
| Real staging execution | Not performed |
