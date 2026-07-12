# Project Overview

## Purpose and Audience

Finance Bot is a private Telegram assistant for one owner who tracks personal income, expenses, transfers, balances, budgets, debts, receivables, split bills, pending expenses, recurring activity, assets, net worth, and reports in Google Sheets. Indonesian natural-language input is the primary interaction style.

## Design Principles

- Financial writes require an owner-visible preview and explicit confirmation.
- Deterministic parsing, validation, and calculation take precedence over AI guesses.
- Ambiguous input asks for clarification instead of silently creating a transaction.
- Immutable action IDs, one-shot callbacks, idempotency checks, rollback attempts, and explicit reconciliation states protect mutations.
- Logs and metrics contain bounded metadata, not raw finance text, credentials, prompts, or receipt bytes.

## Product Boundary

The approved deployment is single user, single process, and one scheduler owner. Google Sheets is the persistence layer and does not provide database foreign keys or multi-sheet ACID transactions. Application services therefore own validation, relationships, idempotency, rollback attempts, and reconciliation guidance.

## Deterministic and AI-Assisted Work

Local rules handle finance classification, totals, date ranges, account/category resolution, safety routing, and context aggregation. Gemini is a bounded fallback for selected parsing, image receipt interpretation, category aliases, and finance insight. It does not replace confirmation or write directly to Sheets.

## Deployment Model

Polling is the primary local and hosted mode. Webhook/FastAPI remains supported with separate `/health` liveness and `/ready` dependency readiness. A deployment with the scheduler enabled must use exactly one application instance.

## Current Limitations

- No tenant identifier or multi-user isolation model.
- First report and search reads remain proportional to worksheet size.
- Some reconciliation-safe financial mutations remain synchronous because a timed-out worker cannot prove a remote write stopped.
- Google Sheets quota, latency, and atomicity limitations still apply.
- Gemini availability and model output quality affect AI-only features; deterministic fallbacks remain available where implemented.
- Real dummy-data staging is required before production rollout.

## Related Documents

- [Architecture](02-architecture.md)
- [User Flows](04-user-flows.md)
- [Safety and Confirmation](05-safety-and-confirmation.md)
- [Configuration and Deployment](08-configuration-and-deployment.md)
- [Operations Runbook](operations/runbook.md)

| Documentation update | Status |
| :--- | :--- |
| Product purpose and intended user | Current |
| Single-user and persistence boundaries | Current |
| AI and deterministic responsibilities | Current |
