# Phase 3 Independent Correction Pass

## Executive summary

This correction pass was performed after an independent audit found that the first Phase 3 implementation was only partially complete despite a green test suite. The pass fixes the unsafe sort/rollback interaction, closes the worker-timeout concurrency leak, routes covered synchronous Sheets/Gemini/scheduler reads through bounded workers, implements a real one-call batch Gemini path for unresolved multi-input, and replaces hard-coded optimized benchmark profiles with observed application execution.

Latest verification must be read from the final command output packaged with this repository. No external Telegram, Google Sheets, Gemini, or scheduler service was called.

## Corrected issues

### 1. Transaction sort and rollback safety

**Previous defect:** transaction rows were sorted before all financial mutations completed, while rollback retained a physical row number. A later balance failure could therefore delete an older transaction after the new row moved.

**Correction:**

- sorting inside a `SheetsTransaction` is registered as deduplicated post-commit maintenance;
- post-commit maintenance runs outside the financial rollback context;
- append rollback prefers immutable first-column logical IDs rather than stale row positions;
- sort failure after commit is logged as maintenance failure and does not retry append or roll back committed finance data.

**Regression coverage:**

- sort is not executed before commit;
- balance failure removes the newly appended logical ID and preserves historical rows;
- post-commit sort failure keeps the committed transaction and performs no duplicate append.

### 2. Worker timeout capacity leak

**Previous defect:** `asyncio.wait_for(asyncio.to_thread(...))` released the semaphore when the awaiting coroutine timed out, although the thread continued running. Repeated timeouts could exceed the configured worker limit.

**Correction:**

- the semaphore slot belongs to the underlying thread-backed task;
- timeout shields the worker from cancellation;
- capacity is released only by the worker task completion callback;
- late worker exceptions are consumed safely;
- mutation timeout remains classified as reconciliation-required.

**Regression coverage:** a limit of one remains one even after caller timeout, and a subsequent request saturates instead of starting another underlying worker.

### 3. Remaining async blocking paths

Covered synchronous external calls in async Telegram and scheduler flows now use the governed worker boundary, including:

- normal transaction Gemini fallback;
- category-alias Gemini generation;
- report, balance, budget, debt, pending, recurring, asset, net-worth, edit-preview, search, and export reads touched by this phase;
- legacy callback read-only lookups audited in this pass;
- recurring, daily, weekly, monthly, and debt-reminder scheduler reads.

Financial mutations remain synchronous intentionally because a timed-out worker cannot prove a remote write stopped. Correctness and reconciliation remain higher priority than response latency.

An AST architecture test prevents the covered synchronous Sheets/Gemini functions from being called directly inside async functions.

### 4. Real batch Gemini parsing

**Previous behavior:** a shared budget limited total calls, but unresolved multi-input lines were not parsed in a real batch. The first unresolved item could consume the call while later items remained unresolved only because the budget was exhausted.

**Correction:**

- deterministic parsing runs for every item first;
- all unresolved lines are collected;
- one structured batch prompt is sent through one governed Gemini call;
- model results are merged by stable batch index without reordering local valid items;
- malformed, missing, out-of-range, and duplicate indexes are ignored;
- worker saturation or timeout leaves items in the existing clarification flow rather than inventing transactions.

### 5. Benchmark validity

**Previous defect:** optimized call counts were returned from a hard-coded `_operation_profile` instead of being observed from the application.

**Correction:**

- optimized mode invokes current transaction, report, export, finance-context, and request-budget code against instrumented in-memory worksheets;
- worksheet method calls, rows read/written, full rewrites, and duplicate reads are counted from actual adapter usage;
- baseline mode is explicitly labelled `historical_modelled`;
- optimized mode is labelled `observed_application`;
- 100, 1,000, and 10,000-row runs are reproducible and credential-free.

## Finding status after correction

| Finding | Corrected status | Evidence |
| :--- | :--- | :--- |
| F-009 | **PARTIALLY CLOSED** | Covered read/Gemini/scheduled paths are bounded and non-blocking; financial mutations intentionally remain synchronous pending reconciliation-safe offloading. Timeout capacity no longer leaks. |
| F-010 | **CLOSED OFFLINE** | Server sort is post-commit maintenance; rollback uses logical identity; failure-injection tests protect historical rows and prevent duplicate append. Real Sheets staging remains required. |
| F-011 | **CLOSED OFFLINE** | Request-scoped snapshots deduplicate measured same-request reads; benchmark records zero duplicate reads for measured AI scenarios. First reads remain O(N). |
| F-012 | **CLOSED OFFLINE** | Existing input/output limits, prompt versions, context cap, redacted telemetry, and usage handling remain intact. |
| F-013 | **CLOSED OFFLINE** | Real unresolved multi-input batching uses one governed call; image compatibility remains the only permitted second-call path. |

## Protected contracts

The correction pass does not intentionally change:

- Telegram command names or callback data;
- Google Sheets worksheet names or columns;
- preview-before-write and one-shot action semantics;
- transaction, debt, split, budget, pending, recurring, asset, or net-worth calculations;
- Gemini model selection, temperature, visible answer contract, or prompt meaning;
- Asia/Jakarta business dates;
- Phase 0 rollback/idempotency/reconciliation guarantees;
- Phase 1 observability and redaction guarantees;
- Phase 2 callback ownership and compatibility routing.

## Remaining risks and staging requirements

1. Real Google Sheets server-side sort permissions, range behavior, and tie ordering require dummy-sheet staging.
2. Financial mutation operations can still block the event loop while Google Sheets is slow; this is an explicit safety tradeoff, not an accidental omission.
3. A timed-out read/Gemini thread continues until the underlying SDK call returns; capacity now remains reserved, but Python cannot forcibly stop the thread.
4. First worksheet reads and local report transforms remain O(N).
5. Gemini provider timeout behavior and usage metadata must be verified with opt-in staging calls.
6. No production or staging external service was called during this correction pass.

## Recommended next step

Run the owner-approved Telegram plus dummy Google Sheets staging checklist before production deployment. Do not attempt mutation offloading merely to mark F-009 closed unless a reconciliation-safe completion protocol is designed and tested first.

## Final offline verification

```text
Full suite:        314 passed
Unit:               74 passed
Service:            29 passed
Integration:        38 passed
Regression:        164 passed
Failed:               0
Xfailed:              0
Xpassed:              0
Skipped:              0
compileall:       passed
Optimized benchmark (100/1,000/10,000 rows): passed
External services called: none
```

Commands executed:

```powershell
python -m pytest -q
python -m pytest -q tests/unit
python -m pytest -q tests/service
python -m pytest -q tests/integration
python -m pytest -q tests/regression
python -m compileall -q app evals main.py tests benchmarks
python benchmarks/phase3_synthetic.py --sizes 100 1000 10000 --iterations 1 --mode optimized --json
```
