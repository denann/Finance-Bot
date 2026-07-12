# Phase 5 Current Scale Boundary

## Evidence Labels

- **VERIFIED:** supported by current code and passing offline tests.
- **INFERRED:** follows from the implementation but lacks runtime telemetry.
- **REQUIRES STAGING:** needs owner-approved dummy external services.
- **REQUIRES PRODUCT DECISION:** changes the declared product boundary.

## Evidence Inventory

| Area | Status | Current evidence | Boundary or unknown |
| :--- | :--- | :--- | :--- |
| Authorized user | VERIFIED | `is_authorized` compares Telegram user ID with one `ALLOWED_USER_ID` | No tenant registry or second-user isolation |
| Spreadsheet ownership | VERIFIED | One configured `GOOGLE_SHEET_ID` and one service-account path | Real sharing/permission isolation requires staging |
| Process count | VERIFIED | `APP_INSTANCE_COUNT` defaults to 1; scheduler policy rejects enabled multi-instance deployment | Multi-instance behavior is not implemented |
| Scheduler owner | VERIFIED | One in-process scheduler and readiness state; recurring run uses logical run keys | Durable lease/claim across processes does not exist |
| Pending state | VERIFIED | Per-user PTB memory, opaque action IDs, 15-minute default TTL, maximum retained actions, lost on restart | Durable pending actions require a product/architecture decision |
| Request snapshot | VERIFIED | Context-local, lazy per worksheet, invalidated after writes, discarded after request | No cross-request cache or tenant key |
| Sheets reads | VERIFIED | Read/report/search/export services use worksheet-level primitives; first transaction read is O(N) | Real network transfer, quota, and p95 require staging |
| Sheets writes | VERIFIED | Append/update/delete primitives, logical-ID reconciliation, compensating rollback | No cross-sheet ACID guarantee |
| Transaction save/sort | VERIFIED | Append plus server-side sort; no transaction-sheet full rewrite in default path | Real sort latency/permission requires staging |
| Reports/search | VERIFIED | Full transaction worksheet transfer followed by deterministic Python filtering/sorting | Indexing/pagination is absent |
| AI context | VERIFIED | Deterministic aggregation, request snapshot, max 40 selected records, max 100,000 prompt characters | First worksheet read remains O(N); provider timing requires staging |
| Rollback/reconciliation | VERIFIED | Typed known failure versus reconciliation-required outcomes and rollback tracking | Remote ambiguous outcomes cannot always be proven offline |
| Export/deletion | VERIFIED | Export reads selected rows; deletion previews, reverses dependencies, deletes by row, and can require reconciliation | Large export delivery and real deletion latency require staging |
| Logging/privacy | VERIFIED | Opaque correlation IDs, redacted structured metadata, no raw payload labels in tests | Operator log pipeline/privacy review requires staging |
| Current capacity | INFERRED | Suitable for declared one-user workload while measured triggers remain green | No universal row/user maximum is claimed |
| Second user/public onboarding | REQUIRES PRODUCT DECISION | Current schema and authorization have no tenant boundary | Must not be enabled without tenant design and owner approval |

## Current Product Decision Boundary

The current product is one authorized user, one process, one spreadsheet, and one scheduler owner. Google Sheets remains the persistence backend. This is a declared scope, not a claim that Sheets is universally scalable.

No current evidence proves a RED migration trigger. Real Telegram, gspread, Gemini, quota, network, and hosted-process behavior remains **REQUIRES STAGING**.

| Contract | Phase 5 action |
| :--- | :--- |
| Commands, callbacks, finance rules | No change |
| Worksheet names/columns | No change |
| Authorization/persistence/scheduler | No change |
| External calls | None |
