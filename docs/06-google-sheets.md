# Google Sheets Guide

## Setup

1. Create a Google Cloud service account and download its JSON key outside the repository.
2. Set `GOOGLE_SERVICE_ACCOUNT_JSON` to that local file and `GOOGLE_SHEET_ID` to the target spreadsheet ID.
3. Share the spreadsheet with the service-account email as editor.
4. Run `python scripts/setup_check.py` locally without committing secrets.
5. Start against a dummy spreadsheet first. Startup validates/bootstraps required worksheet headers from `SHEET_SCHEMAS`.

Never paste service-account JSON, private keys, spreadsheet URLs, or real IDs into documentation, logs, tests, or issue reports.

## Ownership

Services own finance validation and row construction. `app/sheets/client.py` owns gspread access, retry classification, schema checks, request snapshots, rollback registration, and server-side sort requests. Handlers must not write directly before confirmation.

## Reads and Snapshots

A logical Telegram request or scheduled job gets one request-scoped snapshot. The first `get_all_records` or `get_all_values` for a worksheet is cached for that request; successful writes invalidate it. No finance snapshot survives into another request. The default transferred-row budget is `SHEETS_REQUEST_ROW_BUDGET=50000`.

The first report/search/export read remains O(N). Snapshot reuse removes duplicate same-request transfers, not the initial worksheet read.

## Writes, Balances, and Ordering

Transactions append with immutable IDs. Account balance changes are dependent mutations and may require reconciliation if their outcome cannot be verified. The default `TRANSACTION_SORT_MODE=server` sends a date/ID sort request for `A2:Z`, preserving the header and visible newest-first order without downloading/replacing the full transaction range. A sort failure is maintenance failure and must not repeat the append.

`TRANSACTION_SORT_MODE=legacy` is an emergency, non-default rollback that performs the old full read/rewrite. Remove it only after owner-approved staging proves server-sort parity.

## Retry-Safety Matrix

| Operation | Retry safety | Required handling |
| :--- | :--- | :--- |
| Worksheet read | Usually retryable | Bounded adapter retry and handler timeout |
| Transaction append | Not blindly retryable | Reconcile immutable transaction ID before another append |
| Balance update | Potentially ambiguous | Inspect/reconcile account and ledger before retry |
| Server-side sort | Maintenance operation | Log failure; do not repeat transaction append |
| Report calculation | Retryable after fresh snapshot | No mutation; discard failed request snapshot |
| Batch append | Ambiguous after partial transport failure | Reconcile all candidate IDs; never append the whole batch blindly |

The synchronous adapter owns exponential retry sleep. Covered read/report/AI paths run it in a bounded worker. A timeout does not prove a running mutation stopped.

## Rollback and Reconciliation

Supported writes register compensating actions inside the request transaction scope. Rollback success can establish that the operation did not remain committed. Rollback failure or an unverified remote outcome produces a reconciliation-required result. See [Safety and Confirmation](05-safety-and-confirmation.md) and the [Runbook](operations/runbook.md).

## Quota, Backup, and Recovery

- Keep interactive Sheets concurrency conservative (`2` by default) and scheduled work separate (`1`).
- Back up the spreadsheet before deployment, schema work, bulk repair, or migration.
- Use dummy worksheets for load/sort tests at 100, 1,000, and controlled larger row counts.
- Restore from a known backup only after recording the current spreadsheet and stopping writers.
- Validate schema, balances, debt links, recurring logs, and latest transaction IDs after recovery.

## Staging Evidence Required

Real gspread latency, quota behavior, server-side sort permissions/order, and timeout behavior are not proven by offline fakes. Execute staging only with explicit owner approval and dummy credentials.

| Documentation update | Status |
| :--- | :--- |
| Schema source | `SHEET_SCHEMAS` |
| Retry and timeout semantics | Documented |
| Server sorting and snapshot budgets | Documented |
| Real staging | Required, not executed |
