# Future Migration and Tenant Plan

This is a design only. It does not enable tenants, add users, change schemas, or implement migration.

## Tenant Boundary Before User Two

Define a durable tenant identity and authorization mapping before onboarding. Tenant scope must be present in action IDs/payload ownership, request snapshots/cache keys, every query/mutation, recurring jobs/run keys, structured logs/metrics, credential and spreadsheet mapping, export/deletion, privacy requests, and retention policy.

Current worksheet schemas must not receive an ad hoc tenant column. For a small approved private cohort, assess spreadsheet-per-user first: one logical tenant maps to one spreadsheet with the current tabs. This preserves worksheet visibility but still requires tenant-aware routing, credential isolation, lifecycle operations, and tests. It is not assumed to be the final solution.

## Relational Migration Plan

1. Freeze an immutable source backup and record spreadsheet/schema/application versions.
2. Map every worksheet/column to typed relational entities while preserving all immutable IDs.
3. Define Jakarta business-date and timestamp/UTC conversion explicitly.
4. Validate source rows, required fields, enums, numeric values, references, and duplicates.
5. Run an idempotent dry-run importer into an isolated database.
6. Produce reconciliation reports and resolve every mismatch before cutover.
7. Stop writers/scheduler, take final backup, import delta, and rerun reconciliation.
8. Cut over one reviewed application version with no dual-write ambiguity.
9. Keep the source spreadsheet immutable during the rollback window.
10. Roll back application and database together if acceptance fails; do not merge divergent writes manually.
11. Publish an audit report with counts, totals, exceptions, approvals, and backup locations.

## Required Reconciliation

- Worksheet coverage: `transactions`, `accounts`, `budgets`, `debts`, `debt_payments`, `categories`, `monthly_summary`, `recurring_rules`, `recurring_logs`, `assets`, `pending_expenses`, and `net_worth_snapshots`.
- Row counts for all 12 worksheets.
- Transaction counts by type, monthly totals, account totals, and duplicate IDs.
- Account balances versus ledger-derived expectations.
- Payable/receivable principal, debt-payment totals, settled/void status, and orphan links.
- Budget, category, pending, recurring rule/log, asset, and snapshot counts.
- Recurring `rule_id + due_at` uniqueness and transaction links.
- Asset values and net-worth snapshot totals.
- Orphan references and every preserved immutable ID.
- Export parity and tenant-scoped deletion results.

## Scheduler Evolution

Multi-instance operation requires either one durable scheduler owner or durable claim/lease semantics. Use a unique key such as `tenant_id + rule_id + due_at`; manual and scheduled execution must pass through the same idempotency gate. Claims need expiry/heartbeat, worker-failure recovery, committed-result lookup, and no blind replay after ambiguous mutation.

## Cutover and Rollback Acceptance

Cutover requires zero unexplained reconciliation mismatch, approved latency/reliability evidence, tested backup restore, tenant isolation tests, scheduler recovery tests, and owner sign-off. The current architecture remains active until a separate implementation phase satisfies these conditions.
