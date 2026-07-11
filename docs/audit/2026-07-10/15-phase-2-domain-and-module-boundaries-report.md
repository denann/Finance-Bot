# Phase 2 Domain and Module Boundaries Report

- Date completed: 2026-07-11
- Baseline checkpoint: `cc537a7`
- Phase branch: `codex/phase-2-domain-boundaries`
- External services: not called
- Live AI evaluation: `NOT_RUN`

## What Changed

- Added a small typed application result contract for validation, clarification, immutable previews, committed mutations, failures, and reconciliation outcomes.
- Moved combined transaction/debt coordination into focused application use cases and removed direct service-to-service imports.
- Added a routing-focused callback dispatcher. The extracted bulk context has an owned callback module; unchanged contexts remain behind the legacy compatibility handler.
- Replaced batch-abort behavior with immutable, item-level bulk state that preserves valid items, resolves one issue at a time, retains original order, and produces one final confirmation preview.
- Consolidated Rupiah formatting, safe Telegram reply behavior, the command registry, and the AI command tester implementation.
- Removed the dead parallel liability implementation. Active payable debt is now the liability source used by net worth, while old liability commands receive one explicit `/hutang` compatibility response.

## Finding Status

### F-015 - Handler Ownership and Service Dependencies

- **Status:** Completed for the bounded contexts approved in Phase 2.
- **Evidence:** The callback entry point is an 11-line dispatcher; transaction and debt services have no direct import cycle; touched handler modules use explicit imports.
- **Files changed:** `app/application/transaction_debt.py`, `app/bot/handler_parts/callback_dispatcher.py`, `app/bot/handler_parts/bulk_flow.py`, `app/bot/handlers.py`, transaction and debt services.
- **Tests:** Architecture direction, handler import smoke, public callback snapshots, transaction/debt orchestration, and full regression tests.
- **Acceptance criteria:** Cycle removed, dispatcher routing-focused, extracted ownership explicit, prior behavior retained.
- **Residual risk:** `legacy_callback_handler` remains 3,702 lines and four wildcard imports remain in intentionally untouched broad handler contexts.

### F-016 - Item-Level Bulk Clarification

- **Status:** Completed.
- **Evidence:** Every input receives stable identity, original position, status, parsed state, validation details, and resolved fields. Unknown or unsafe items require rewrite, explicit removal, or cancellation.
- **Files changed:** `app/application/bulk_input.py`, `app/bot/handler_parts/bulk_flow.py`, `app/bot/handler_parts/message_handlers.py`, and bulk tests.
- **Tests:** Ready, unknown, invalid date, missing amount/account, split decision, debt ambiguity, multiple unresolved items, rewrite, removal, cancel, stale callback, ordering, no pre-confirm write, double-click, and write-failure coverage.
- **Acceptance criteria:** Valid items are retained once, unresolved items are handled sequentially, no write occurs before final confirmation, order remains stable, and cancellation mutates nothing.
- **Residual risk:** Real Telegram timing and real Sheets reconciliation still require opt-in staging verification.

### F-021 - Duplicate Utilities and Tester Implementations

- **Status:** Completed.
- **Evidence:** Formatter implementations reduced from seven to one, safe-reply implementation modules from two to one, and tester implementations from two to one. Historical tester paths invoke the same implementation.
- **Files changed:** `app/formatting.py`, formatter consumers, `app/bot/handler_parts/core.py`, `app/scripts/ai_command_tester.py`, `scripts/ai_command_tester.py`, and tester documentation.
- **Tests:** Currency golden outputs including historical decimal behavior, safe-reply architecture count, registry/tester agreement, and both tester CLI entry points.
- **Acceptance criteria:** One canonical implementation exists for each required utility/tester rule without visible currency-format changes.
- **Residual risk:** Compatibility re-exports remain where broad legacy imports still depend on them.

### F-022 - Liability Compatibility Cleanup

- **Status:** Completed.
- **Evidence:** Dead liability service methods and handlers were removed; public handler facade exposes no liability implementation; tester and command registry agree; payable debts remain included in net worth.
- **Files changed:** `app/services/net_worth_service.py`, `app/services/finance_insight_service.py`, `app/bot/handler_parts/networth_assets.py`, `app/bot/command_registry.py`, `app/bot/handler_parts/command_router.py`, and minimal docs.
- **Tests:** Unavailable-command behavior, registry parity, removed public symbols, and debt-backed net-worth liability calculations.
- **Acceptance criteria:** Liability is not a parallel domain, debt remains the source of truth, old commands direct users to `/hutang`, and no Sheets schema changed.
- **Residual risk:** Historical audit reports still describe the pre-cleanup implementation by design.

## Before and After Architecture

```text
Before
Telegram -> wildcard handler facade -> god handlers -> services/Sheets
                                      transaction_service <-> debt_service

After
Telegram -> explicit registry/dispatcher -> bounded Telegram translator
                                      -> typed application use case
                                      -> transaction_service
                                      -> debt_service
                                      -> Sheets adapters
```

Extracted application state and result modules do not import Telegram handlers or Sheets adapters. The detailed ownership map is in `docs/architecture/phase-2-boundary-map.md`.

## Review Metrics

| Metric | Before | After |
| :--- | ---: | ---: |
| Top callback dispatcher lines | 3,702 | 11 |
| Largest extracted callback bounded-handler lines | Not separated | 55 |
| Legacy callback fallback lines | 3,702 | 3,702 |
| Message handler lines | 470 | 381 |
| Production wildcard imports | 18 | 4 |
| Transaction/debt direct cycles | 1 | 0 |
| `format_rupiah` implementations | 7 | 1 |
| Safe-reply implementation modules | 2 | 1 |
| Tester implementation files | 2 | 1 |
| Liability-related reachable handler symbols | 5 | 0 |
| Offline tests | 170 | 223 |

The dispatcher reduction measures ownership, not deletion of all legacy behavior. Unchanged callback contexts intentionally remain behind the compatibility fallback.

## Protected Contracts

| Contract | Result |
| :--- | :--- |
| Telegram command names and syntax | Preserved; snapshot and runtime registry agree. |
| Existing callback data | Preserved; new `bulk_*` callbacks are isolated to the new flow. |
| Output copy | Existing copy retained except approved bulk clarification and liability-unavailable responses. |
| Sheets worksheets and columns | Unchanged. |
| Finance business rules and visible ordering | Preserved by regression and targeted tests. |
| Phase 0 action identity and one-shot confirmation | Preserved; final bulk action uses the existing pending confirmation contract. |
| Phase 1 observability and privacy | Preserved; no production observability behavior changed. |
| External-service isolation | Preserved; all tests ran under the default offline guard. |
| Gemini model and prompt behavior | Unchanged; live evaluation remains disabled. |

## Verification

| Command | Result |
| :--- | :--- |
| Baseline `python -m pytest -q` | 170 passed in 4.70 seconds. |
| Final `python -m pytest -q` | 223 passed, 1 cache warning in 10.76 seconds. |
| `python -m pytest -q tests/unit` | 50 passed, 1 cache warning in 2.37 seconds. |
| `python -m pytest -q tests/service` | 16 passed, 1 cache warning in 0.96 seconds. |
| `python -m pytest -q tests/integration` | 34 passed, 1 cache warning in 6.01 seconds. |
| `python -m pytest -q tests/regression` | 114 passed, 1 cache warning in 3.03 seconds. |
| `python -m pytest -q -k "bulk or multi"` | 37 passed, 186 deselected, 1 cache warning in 3.14 seconds. |
| `python -m pytest -q -k "debt or transaction"` | 18 passed, 205 deselected, 1 cache warning in 2.36 seconds. |
| `python -m pytest -q -k "registry or liability or tester"` | 3 passed, 220 deselected, 1 cache warning in 3.33 seconds. |
| `python -m pytest -q tests/architecture` | 5 passed, 1 cache warning in 3.95 seconds. |
| `python -m compileall -q app evals main.py tests` | Pass. |
| `git diff --check` | Pass; line-ending notices are informational. |
| `git status --short --branch` | On `codex/phase-2-domain-boundaries`; Phase 2 files are modified/untracked as expected and uncommitted. |

The warning is the existing Windows `.pytest_cache` creation warning and does not affect collection or execution. No production credential or real Telegram, Sheets, Gemini, HTTP, webhook, or scheduler service was used.

## Remaining Gaps

- The legacy callback fallback remains large; additional contexts should be extracted only with their own contract tests.
- Four wildcard imports remain in `transaction_flow.py`, `command_handlers.py`, `category_flow.py`, and `health_recurring_export.py`, all outside the bounded contexts changed here.
- Compatibility facades remain for `app.bot.handlers`, the legacy callback, safe-reply imports, formatter bindings, and the historical tester path.
- Real Telegram callback timing, Sheets mutation/reconciliation, and provider behavior remain staging-only checks.
- Phase 3 performance, Sheets-call reduction, and Gemini cost work were not started.
- Full README/manual synchronization and PDF regeneration remain deferred to Phase 4.

## Recommended Next Step

Proceed to **Phase 3 - Performance and Gemini Cost** after owner review. The Phase 2 acceptance criteria are complete; legacy extraction can continue incrementally when a later change touches those bounded contexts.

No commit or push was performed.
