# Phase 5 Scale and Persistence Decision Report

## Executive Decision

**KEEP CURRENT ARCHITECTURE.**

Retain one authorized user, one process, one Google Spreadsheet, one scheduler owner, and the current schema/backend. No measured RED trigger exists. This decision is limited to the declared product scope and must be reviewed before user two or multi-instance operation.

## Current Evidence

- Baseline and final offline suites pass with protected contracts intact.
- Transaction save performs 2 measured Sheets operations, transfers 0 transaction rows, writes 1 row, and performs no full rewrite.
- `/last`, report, search, export, and first AI context preparation transfer O(N) transaction rows.
- Request snapshots remove duplicate reads; AI records remain bounded (current `/ask` selection 15, configured cap 40).
- The default 50,000-row request budget rejects `/ask` at 50,006 transferred rows and 100,000-row full reads. This is AMBER guard evidence, not a universal Sheets limit.
- Offline peak allocation grows linearly, reaching approximately 190-301 MB for 100,000-row read/export/AI scenarios in one run.
- Correctness uses immutable IDs, one-shot actions, idempotency/run keys, compensating rollback, and explicit reconciliation-required outcomes, not database ACID.
- Real network latency, quotas, provider behavior, and hosted memory require staging.

## Finding Status

| Finding | Status | Evidence/current risk | Trigger/decision | Remaining validation |
| :--- | :--- | :--- | :--- | :--- |
| F-024 tenant boundary | ACCEPTED CURRENT CONSTRAINT | One allowed user, one sheet, no tenant ID/registry | Second approved user is RED; retain current scope | Product decision before user two |
| F-009 scale aspect | PARTIALLY MITIGATED | Covered reads are bounded workers; reconciliation-sensitive mutations may still block one event loop | Recurrent latency/correctness breach is AMBER/RED | Dummy latency and mutation incident evidence |
| F-011 scale aspect | PARTIALLY MITIGATED | Duplicate reads removed and AI context bounded; first full reads remain O(N) | Repeated report/search/transfer breach triggers optimization/migration design | Real rows/latency/quota telemetry |
| F-018 scale aspect | RESOLVED FOR CURRENT SCOPE | Asia/Jakarta business clock is explicit and tested | Multi-tenant timezone requirements require new product decision | No current validation gap; future tenant policy needed |
| F-020 scale aspect | RESOLVED FOR CURRENT SCOPE | Readiness and single-instance scheduler policy are tested | Required overlapping/multiple instances are RED | Hosted readiness and scheduler staging |

## Options Evaluated

| Option | Decision |
| :--- | :--- |
| A. Current Sheets | Selected for current one-user product; lowest complexity and preserves visibility |
| B. Spreadsheet per user | First compatibility design to assess if a small private user cohort is approved |
| C. Hybrid DB + Sheets | Deferred; synchronization/dual recovery burden is not justified |
| D. Relational primary | Deferred; strongest tenant/query/atomicity foundation but requires approved migration |

## ADR Result

ADR-001 is accepted: Google Sheets is sufficient for the current declared scope until a measured trigger is reached. It is not declared universally sufficient. Review on a RED event, staging evidence, material incident, or by 2027-01-12.

## Migration Triggers

- **GREEN:** one user/process/scheduler remains sufficient; p95 objectives and correctness/reliability hold.
- **AMBER:** row budget, latency, memory, quota, retries, or reconciliation show isolated pressure; collect evidence or optimize the adapter.
- **RED:** second/public/team user scope, required multi-instance/durable scheduler, repeated unsafe reconciliation, or recurring latency/quota/query failure after measured windows.

Latency triggers require three controlled staging runs with at least 30 samples each or repeated evidence in an agreed 14-day/100-sample operational window. A row count or local timing alone is insufficient.

## Future Migration Plan

Before user two, define tenant identity/authorization, scoped actions/caches/queries/jobs/logs/credentials/export/deletion/privacy/retention. Spreadsheet-per-user is the first compatibility path to assess. A relational migration requires immutable backup, schema/ID/date mapping, dry runs, duplicate/reference validation, balance/debt/recurring/asset/net-worth reconciliation, controlled cutover, rollback window, and audit report. Multi-instance scheduling requires a durable owner or claim/lease keyed by tenant, rule, and due time.

## Staging Package

`docs/testing/phase-5-scale-staging.md` provides dedicated dummy bot/sheet/service-account setup, 100 through 100,000-row controlled runs, latency/call/row/quota/retry/reconciliation templates, scheduler/restart/export/privacy checks, and cleanup. It was not executed.

## Automated Checks

Six tests prove benchmark evidence labels, current operation shape, modelled projection labels, ADR/review trigger, absence of tenant config/schema, all-worksheet reconciliation coverage, staging scenarios, current index coverage, and future-only wording.

## Protected Contracts

- No command, syntax, callback, finance rule, ID, debt/split, confirmation, timezone, report, export, Gemini, scheduler, authorization, persistence, or schema change.
- No tenant/user/database/queue/multi-instance behavior implemented.
- No external services or credentials used.

## Verification

| Check | Result |
| :--- | :--- |
| Baseline / final | 317 / 323 passed |
| Failed / skipped / xfailed / xpassed | 0 / 0 / 0 / 0 |
| Unit / service / integration / regression | 83 / 29 / 38 / 164 passed |
| Documentation / compileall / diff check | Passed / passed / passed |
| Phase 5 scale runner | Completed at 100, 1k, 10k, 25k, 50k, 100k using isolated large runs |

## Residual Risks and Owner Decisions

- Dummy-Sheets staging is not executed; real quota/network/SLO evidence is unknown.
- Real multi-instance behavior is not implemented.
- No universal row limit is declared.
- Migration/cutover/rollback has not been rehearsed.
- Owner approval is required before a second user, tenant selection, schema/backend change, or migration implementation.

## Recommended Next Step

Execute the owner-approved dummy-data staging checklist and continue feature development within the documented single-user boundary. Request explicit approval before implementing any RED-trigger migration design.
