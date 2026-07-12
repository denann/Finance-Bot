# Phase 5 Scale Staging

**NOT EXECUTED.** This owner-run procedure requires dummy services and explicit approval.

## Environment

- Dedicated Telegram test bot and authorized test user.
- Dummy spreadsheet and dummy service account with no production access.
- One isolated application process and scheduler owner.
- Reviewed commit, environment snapshot, redacted log destination, and spreadsheet backup.
- Synthetic generator only; no real names, accounts, merchants, IDs, or finance values.

## Dataset Runs

Run 100, 1,000, 10,000, then controlled 25,000/50,000/100,000 row datasets only while host memory/quota remains safe. For each size collect at least 30 samples for `/last`, monthly report, search, export preparation, transaction save, server-side sort, and bounded AI context preparation.

## Procedure

1. Record environment/date/commit/config and seed deterministic synthetic rows.
2. Verify all 12 schemas and row counts.
3. Measure read/report/search p50/p95/p99, rows transferred, retries, quota incidents, and errors.
4. Save transactions and measure end-to-end preview-to-confirm latency, append count, balance result, physical order, and sort maintenance.
5. Verify AI context selected rows/call budget; live Gemini is a separate explicit opt-in step.
6. Verify one scheduler owner, recurring run-key deduplication, and no duplicate after restart.
7. Restart during pending preview and confirm stale action fails closed.
8. Inject fake/controlled failures for read timeout and reconciliation-required mutation handling without production data.
9. Export data and verify row/order/schema parity plus Telegram file handling.
10. Inspect structured logs for credentials, prompts, finance text, names, account labels, IDs, or receipt bytes.
11. Compare results with GREEN/AMBER/RED recurrence rules.
12. Stop processes, revoke dummy credentials, delete the test bot token from local config, and archive/delete dummy data per owner policy.

## Result Template

| Field | Value |
| :--- | :--- |
| Environment / date / commit | |
| Data size / scenario / sample count | |
| p50 / p95 / p99 | |
| Error / retry count | |
| Sheets calls / rows transferred / rows written | |
| Quota incidents | |
| Reconciliation incidents | |
| Peak host memory | |
| Sort/order result | |
| Scheduler/restart result | |
| Export/privacy result | |
| GREEN/AMBER/RED impact | |
| Owner decision | |

## Safety and Stop Conditions

Stop on production credential exposure, unexpected schema change, unexplained financial mismatch, repeated reconciliation, unsafe memory pressure, or quota behavior that could affect another project. Do not convert one staging failure directly into migration implementation; apply the documented recurrence rule and request owner approval.
