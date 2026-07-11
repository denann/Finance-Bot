# Phase 2 Boundary Map

## Purpose

This map records the verified Phase 2 starting architecture and the implemented extraction direction. Runtime code and tests remain authoritative when historical audit line numbers differ.

## Starting Dependency Direction

```text
app.bot.application
  -> app.bot.handlers compatibility facade
     -> handler_parts modules through wildcard re-exports
        -> common_imports wildcard facade
           -> Telegram, parser, services, Sheets

message_handler
  -> parsing, state coordination, preview construction, Telegram replies

callback_handler
  -> callback routing, state coordination, finance mutations, formatting

transaction_service <-> debt_service
  -> direct local imports in combined delete, edit, void, and reconciliation flows
```

The starting transaction/debt cycle and public contracts were captured by Checkpoint 2.1 tests before extraction.

## Implemented Dependency Direction

```text
app.bot.application
  -> explicit command registry and handler imports
  -> callback_dispatcher
     -> bulk_flow for the extracted bounded context
     -> legacy_callback_handler for intentionally untouched contexts

bulk_flow
  -> immutable app.application.bulk_input state
  -> existing preview contract

transaction/debt compatibility handlers
  -> app.application.transaction_debt
     -> transaction_service
     -> debt_service

shared presentation
  -> app.formatting
  -> common_imports safe-reply implementation
```

The transaction and debt services no longer import each other. Architecture tests enforce that direction and prevent Telegram or handler imports from entering the extracted application modules.

## Problematic Ownership

| Area | Current issue | Phase 2 target |
| :--- | :--- | :--- |
| Handler facade | Wildcard re-exports hide symbol ownership | Explicit compatibility exports |
| Callback routing | One function routes and performs many bounded operations | Thin dispatcher plus bounded callback modules |
| Multi-input | Failed items are discarded before pending batch state is created | Stable item state with ordered clarification |
| Transaction/debt | Services import each other for combined operations | Application use cases orchestrate both services |
| Results | Handlers inspect unrelated result dictionaries and exceptions | Typed results for extracted use cases |
| Formatting | Seven `format_rupiah` definitions | One canonical formatter with compatibility imports |
| Telegram reply safety | Logic duplicated in `common_imports.py` and `core.py` | One canonical Telegram reply module |
| Tester | Two copied implementations | One implementation and one historical wrapper |
| Liability | Dead service and handler symbols remain importable | Debt/payable is canonical; old commands return one tombstone response |

## Handler Bounded Contexts

| Context | Ownership during Phase 2 |
| :--- | :--- |
| Bulk clarification | New dedicated application state/use case and callback module |
| Transaction/debt combined mutation | New focused application use cases |
| Callback dispatch | New routing-focused dispatcher |
| Existing transaction preview/edit | Compatibility path retained unless needed by bulk extraction |
| Existing debt callbacks | Compatibility path retained while combined service calls move outward |
| Split bill | Existing implementation retained; bulk hands off only after item validation |
| Pending, recurring, assets, budget, category | Existing handlers retained |

## Ownership Direction

```text
Telegram dispatcher
  -> bounded handler / result translator
     -> application use case
        -> transaction service
        -> debt service
        -> repository adapters

domain/application calculations
  - no Telegram imports
  - no context.user_data access
  - no Telegram-formatted service errors
```

Transaction and debt services must not import each other. Combined mutation ordering and failure propagation belong to focused application use cases, not a generic finance manager.

## Compatibility Facades

| Facade | Temporary reason | Removal condition |
| :--- | :--- | :--- |
| `app.bot.handlers` | Stable import path used by application and external checks | Keep until all callers use owned modules |
| Legacy callback handler | Preserves untouched callback contexts | Remove context by context after behavior tests exist |
| Historical tester path | Existing developer commands may use either path | Retain as a thin wrapper indefinitely if useful |
| Formatter/reply re-exports | Avoid broad unrelated handler edits | Remove when each owner imports canonical modules directly |

The legacy callback facade is contained by `app.bot.callback_contracts`: only the audited legacy prefix and exact-value inventory reaches the large handler. Bulk callbacks remain owned by `bulk_flow`, and unknown callback data fails closed in the dispatcher without changing pending state.

## Extraction Order

1. Snapshot commands, callbacks, route precedence, imports, formatter output, tester paths, and liability response.
2. Add typed application results and item-level bulk session state.
3. Move transaction/debt combined orchestration into focused application use cases and enforce dependency direction.
4. Route new bulk callbacks through a bounded module and keep the final immutable mixed preview contract.
5. Consolidate formatter, Telegram reply helpers, tester implementation, and liability tombstones.

## Intentionally Unchanged

- Telegram command names and existing callback values.
- Google Sheets worksheet names and columns.
- Parser and finance calculation meaning outside extracted use cases.
- Pending action identity, expiry, and one-shot confirmation.
- Phase 1 observability, correlation, privacy, Gemini, readiness, and scheduler behavior.
- Existing pending, recurring, asset, budget, category, report, and AI handler internals unless a canonical import must be updated.
