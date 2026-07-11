# Phase 3 Performance and Gemini Cost Report

## Executive Summary

Phase 3 adds one bounded application boundary for blocking external reads, Gemini work, and scheduled work; replaces transaction full-sheet rewrite sorting with a server-side range sort; adds request-scoped Sheets snapshots and row budgets; and enforces request-scoped Gemini call, input, context, retry, prompt-version, and telemetry contracts.

The owner baseline was `276 passed`. Final offline verification is recorded below after all checks complete. The synthetic benchmark shows transaction sort transfer changing from N+1 rows read and N rows rewritten to zero rows downloaded for sorting and one appended row. AI context duplicate reads fall from one or two to zero, with 40 selected records by default.

F-009 remains partially closed. Covered read/report/AI/scheduled paths leave the event loop, but existing financial mutation callbacks remain synchronous because timing out a worker thread cannot prove a remote write stopped. Moving them without a reconciliation-safe completion protocol would weaken the Phase 0 contract.

## Finding Status

### F-009 - Blocking I/O and retry backoff hold the event loop

- **Status:** PARTIALLY CLOSED
- **Evidence:** `run_external_work` uses `asyncio.to_thread`, per-class semaphores, operation timeouts, typed timeout/saturation outcomes, copied correlation context, and duration/outcome metrics. Covered handler reads, Gemini calls, and scheduled export use it.
- **Files changed:** `app/application/external_io.py`, command/message/export handlers, `app/config.py`.
- **Tests:** deterministic responsiveness, concurrency cap, scheduled isolation, typed timeout, and correlation propagation tests.
- **Before metrics:** covered synchronous calls and retry sleep could execute directly in async handler flows; no concurrency class limits.
- **After metrics:** interactive Sheets concurrency 2, Gemini concurrency 1, scheduled concurrency 1; read timeout 20 seconds; unrelated coroutine progresses during fake slow external work.
- **Acceptance criteria:** met for covered reads, Gemini, and scheduled work; not met for every financial mutation path.
- **Residual risks:** synchronous mutation callbacks can still block the event loop. The Sheets adapter still owns `time.sleep`, which is safe only when reached inside a worker.
- **Staging verification required:** delayed dummy Sheets read and real provider timeout behavior.

### F-010 - Transaction save rewrites the full transaction sheet

- **Status:** CLOSED
- **Evidence:** default `TRANSACTION_SORT_MODE=server` issues a server-side sort over `A2:Z`, ordered by date then timestamp-prefixed transaction ID, excluding the header. Read-side ordering handles delayed sort and malformed dates.
- **Files changed:** `app/sheets/client.py`, `app/services/transaction_service.py`, fake Sheets adapter, `.env.example`.
- **Tests:** server request contract, header exclusion, tie ordering, malformed dates, sort failure after commit, no duplicate append, and explicit legacy parity.
- **Before metrics:** 3 modeled transaction-path Sheets calls, N+1 rows read, N rows rewritten, one full-range rewrite per save.
- **After metrics:** 2 modeled transaction-path calls, zero rows downloaded for sorting, one appended row for single save or five for batch, zero full rewrites.
- **Acceptance criteria:** met offline with fake adapter and ordering tests.
- **Residual risks:** real gspread/Google Sheets sort semantics and permissions require staging confirmation.
- **Staging verification required:** physical order at 100, 1,000, and controlled larger dummy row counts.

### F-011 - AI/report context repeatedly reads full worksheets

- **Status:** CLOSED
- **Evidence:** one request-scoped `SheetsRequestSnapshot` caches records/values by worksheet, returns defensive copies, tracks row transfers, enforces a 50,000-row request budget, and invalidates after mutation. `FinanceDataSnapshot` provides a typed lazy facade.
- **Files changed:** `app/sheets/client.py`, `app/application/finance_snapshot.py`, `app/bot/application.py`, finance insight service and handlers.
- **Tests:** same-request deduplication, request isolation, mutation invalidation, row budget, typed facade, and bounded AI context.
- **Before metrics:** AI context transferred transaction rows up to 2N-3N due to one or two duplicate reads.
- **After metrics:** one transaction worksheet transfer per request, zero duplicate reads, and at most 40 relevant records selected for model context.
- **Acceptance criteria:** met for prioritized AI/report/search/export paths; no cross-request finance cache exists.
- **Residual risks:** first worksheet reads and report transforms remain O(N); the 50,000-row request budget must be tuned from staging telemetry.
- **Staging verification required:** worksheet call counts and snapshot invalidation with dummy data.

### F-012 - Gemini governance, usage, bounds, and privacy boundary

- **Status:** CLOSED
- **Evidence:** a shared request budget, 100,000-character input bound, 40-record context cap, stable prompt versions, existing output token/character bounds, usage extraction only when provider metadata exists, and redacted structured events are consolidated at the Gemini client boundary.
- **Files changed:** `app/application/gemini_governance.py`, Gemini client and feature adapters, finance insight service, observability, config.
- **Tests:** oversized input, usage absence/numeric extraction coverage in existing tests, feature/version/character metadata, context cap, and no raw prompt logging.
- **Before metrics:** timeout/output bounds existed from Phase 1B, but input size, prompt versions, and request-wide call ownership were not centralized.
- **After metrics:** one shared budget per update; input <=100,000 characters; selected records <=40; feature/model/call/input/output/duration/outcome/version/attempt/fallback attribution without currency-price assumptions.
- **Acceptance criteria:** met offline; model, temperature, prompt meaning, structured output, and visible answer format are unchanged.
- **Residual risks:** provider usage metadata shape and timeout behavior vary by Gemini SDK response.
- **Staging verification required:** one opt-in call per AI feature and provider usage metadata inspection.

### F-013 - Gemini fallback calls can chain or multiply per item

- **Status:** CLOSED
- **Evidence:** one mutable `GeminiCallBudget` is installed at the atomic update boundary and copied into worker context. Text generation consumes one call. Image attempt two is permitted only for recognized invocation/schema compatibility errors; auth, permission, quota, timeout, server, malformed, and unknown failures do not retry.
- **Files changed:** `app/application/gemini_governance.py`, Gemini client, parser/router/image adapters, bot application.
- **Tests:** one-call text budget, exhausted-budget rejection, one-call multi unresolved profile, image success, exact two-call compatibility fallback, and exact one-call non-compatible failures.
- **Before metrics:** text fallbacks could chain and five unresolved items could model up to five calls; broad image failure could make a second call.
- **After metrics:** maximum text calls 1, multi-input calls 1, image calls normally 1 and at most 2 for named compatibility failures.
- **Acceptance criteria:** met offline with deterministic call-count contracts.
- **Residual risks:** compatibility error classification depends on stable exception type/message signals from the SDK.
- **Staging verification required:** controlled image compatibility path without receipt-content logging.

## Protected-Contract Verification

| Contract | Result |
| :--- | :--- |
| Public commands and aliases | Unchanged |
| Callback data, ownership, and action IDs | Unchanged |
| Worksheet names and columns | Unchanged |
| Physical transaction order | Preserved by default server-side date/ID descending sort |
| Report totals, ranges, and ordering | Existing regression suite passes |
| Gemini model, temperature, prompt meaning, and answer format | Unchanged |
| Rollback, reconciliation, and idempotency | Preserved; mutation timeout conversion deliberately deferred |
| Privacy and redaction | Prompt, finance text, credentials, IDs, and image bytes are not logged |
| Asia/Jakarta business date | Unchanged |
| Readiness, liveness, and scheduler ownership | Unchanged |

## Benchmark Methodology

The benchmark is **OFFLINE SYNTHETIC**. It generates deterministic 100, 1,000, and 10,000-row datasets with multiple accounts, income, expenses, transfers, debt-marked rows, categories, dates, duplicate descriptions, and malformed/empty optional values. Five local iterations produce informational p50/p95/p99 values. Fake profiles count Sheets calls, row transfers, writes, rewrites, duplicate reads, Gemini calls, context characters, and selected records.

No timing is presented as Telegram, Google Sheets, Gemini, network, staging, or production latency. Deterministic operation counts and tests are the hard evidence. Full tables are in `docs/performance/phase-3-benchmark-results.md`.

## Before and After

| Dataset | Single-save rows read | Single-save rows written | Full rewrites | `/ask` transaction rows transferred | `/ask` duplicate reads | Max multi Gemini calls |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 100 | 101 -> 0 | 100 -> 1 | 1 -> 0 | 300 -> 100 | 2 -> 0 | 5 -> 1 |
| 1,000 | 1,001 -> 0 | 1,000 -> 1 | 1 -> 0 | 3,000 -> 1,000 | 2 -> 0 | 5 -> 1 |
| 10,000 | 10,001 -> 0 | 10,000 -> 1 | 1 -> 0 | 30,000 -> 10,000 | 2 -> 0 | 5 -> 1 |

## External-Call Budget

| Feature | Default budget |
| :--- | :--- |
| Regex-success transaction | 0 Gemini calls |
| Text parser/router fallback | At most 1 total Gemini call per update |
| `/ask`, `/insight`, `/audit`, `/coach` | Exactly one generation when provider invocation is reached |
| Multi-input unresolved batch | At most 1 total Gemini call |
| Image success | 1 Gemini call |
| Image compatibility invocation error | At most 2 total Gemini calls |
| Other image errors | Exactly 1 attempted call, no compatibility retry |
| AI relevant transaction context | At most 40 records by default |
| Gemini input | At most 100,000 characters |
| Sheets rows transferred in one request | At most 50,000 by default |
| Interactive Sheets / Gemini / scheduled concurrency | 2 / 1 / 1 |

## Rollback Mechanisms

- **Blocking-I/O boundary:** handler integrations are isolated calls to `run_sheets_read`, `run_gemini`, and `run_scheduled`; rollback is an isolated wiring revert. No second executor exists.
- **Server-side sort:** set the single canonical `TRANSACTION_SORT_MODE=legacy`. The named full-rewrite compatibility path is non-default, parity-tested, and should be removed after staging sort parity is verified.
- **Request snapshot:** the snapshot is request-local and entered once at the atomic handler boundary; removing that context restores uncached reads without data persistence changes.
- **Gemini call budget:** `GEMINI_CALLS_PER_UPDATE` is the single call-limit setting. Reverting governance wiring is isolated from prompts/models.
- **Image retry classification:** compatibility detection is contained in the Gemini image client; no duplicate default implementation is active.

## Remaining Gaps

- Real gspread latency, server-side sort behavior, quotas, and row-transfer telemetry are unverified.
- Real Gemini timeout cancellation and usage metadata shape are unverified.
- Telegram delivery latency and provisional staging SLOs are unverified.
- Financial mutation callbacks can still block the event loop; adding worker timeouts requires a reconciliation-safe completion design.
- Report/search/export still perform O(N) first reads and local transforms.
- The `legacy` sort compatibility mode remains until staging parity is accepted.
- A database or scale-architecture decision remains outside this single-user, single-process phase.

## Staging Checklist - Do Not Execute Without Owner Approval

1. Verify Telegram responsiveness while a dummy Sheets read is deliberately delayed.
2. Save a dummy transaction and inspect physical sheet order and transaction identity.
3. Verify server-side sort with 100, 1,000, and a controlled larger dummy dataset.
4. Capture Sheets API-call, row-transfer, duration, retry, and outcome telemetry.
5. Verify request-scoped deduplication and post-mutation invalidation.
6. Run one opt-in `/ask`, `/insight`, `/audit`, and `/coach` using dummy finance data.
7. Verify provider timeout behavior and confirm no blind retry.
8. Inspect real provider usage metadata without inventing missing token values.
9. Exercise a controlled image compatibility fallback and non-retryable error.
10. Confirm logs contain no raw financial text, prompt, credentials, IDs, or receipt content.

## Verification

All testing was offline and the default external-call guard remained active.

| Check | Result |
| :--- | :--- |
| Owner baseline | 276 passed |
| Full suite | 304 passed; 0 failed; 0 xfailed; 0 xpassed; 0 skipped |
| Total collected | 304 |
| Unit | 68 passed |
| Service | 26 passed |
| Integration | 37 passed |
| Regression | 164 passed |
| Performance/latency/concurrency/timeout filter | 4 passed; 300 deselected |
| Sheets/snapshot/report/export filter | 19 passed; 285 deselected |
| Gemini/AI budget/image filter | 15 passed; 289 deselected |
| Transaction-sort filter | 5 passed; 299 deselected |
| `compileall` | Passed |
| `git diff --check` | Passed |
| External services | Not called |

Pytest emitted one non-fatal Windows cache warning because `.pytest_cache` could not be created. Test execution and collection completed normally.

## Recommended Next Step

Run a **Phase 3 follow-up** for reconciliation-safe mutation offloading and the owner-approved staging checklist. Do not begin Phase 4 until F-009 residual mutation blocking is explicitly accepted or resolved.

| Documentation update | Status |
| :--- | :--- |
| Phase 3 findings F-009 through F-013 | Updated |
| Protected contracts and rollback | Updated |
| Offline benchmark methodology | Updated |
| Staging checklist | Produced, not executed |
