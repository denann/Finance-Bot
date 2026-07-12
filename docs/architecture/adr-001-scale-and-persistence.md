# ADR-001: Scale and Persistence

## Status

**ACCEPTED FOR CURRENT PRODUCT SCOPE**, 2026-07-12.

## Context

Finance Bot serves one authorized owner through one process, one Google Spreadsheet, and one scheduler owner. Correctness, preview/confirmation, visible Sheets data, and simple operation matter more than horizontal scale. Offline service evidence shows bounded transaction save but O(N) report/search/export/context preparation.

## Constraints

No command, callback, finance rule, worksheet schema, persistence backend, authorization behavior, scheduler ownership, or external dependency may change in Phase 5. Real network/quota evidence is not available offline.

## Options Considered

A. Keep current Sheets architecture. B. Spreadsheet per user. C. Hybrid database/Sheets. D. Relational database primary. See `persistence-options.md`.

## Decision

**KEEP GOOGLE SHEETS, SINGLE USER, AND SINGLE PROCESS FOR THE CURRENT PRODUCT.**

Google Sheets is sufficient for the declared scope until measured evidence reaches a documented RED trigger. This is not a universal statement about Sheets capacity and does not authorize a second user.

## Reasons

- No approved multi-user requirement or tenant boundary exists.
- Current save avoids full-sheet transfer/rewrite and preserves ordering.
- Request snapshots remove duplicate reads and AI context is bounded.
- Current correctness tests and reconciliation contracts are extensive.
- Database/hybrid options add migration, synchronization, backup, deployment, and rollback risk without a proven current need.

## Consequences and Accepted Risks

- Reports, search, export, and first AI context reads remain O(N).
- Google Sheets quota/network behavior and multi-sheet atomicity remain limitations.
- One process and one scheduler owner remain mandatory.
- Pending actions remain in memory and are lost on restart.
- Real staging must validate latency, sort, quota, retries, memory, and reconciliation.

## Migration Triggers

GREEN/AMBER/RED triggers and recurrence rules are canonical in `scale-and-migration-triggers.md`. A second approved user or required multi-instance operation is RED before expansion.

## Review

Review on a RED event, after dummy-data staging, after a material incident, or by 2027-01-12. Migration implementation requires a separate owner decision and ADR.
