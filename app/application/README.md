# app/application

## Purpose

Application orchestration sits between Telegram adapters and finance services. It owns typed use-case results, cross-domain transaction/debt coordination, stable bulk-item state, request snapshots, external-work governance, and Gemini request budgets.

## Dependency Direction

Telegram handlers may call application use cases; application code may coordinate services; finance services must not import Telegram handlers. Provider clients and worksheet access stay behind their governed boundaries.

## Public Entry Points and Invariants

- `transaction_debt.py`: cross-domain preview/commit orchestration.
- `bulk_input.py`: ordered stable item identities and clarification.
- `results.py`: immutable typed outcomes.
- `finance_snapshot.py`: one logical request, no cross-request cache.
- `external_io.py`: separate bounded worker classes; timed-out threads retain capacity until exit.
- `gemini_governance.py`: one shared per-update budget.

Tests live under `tests/unit`, `tests/service`, and `tests/integration`. Telegram rendering, raw gspread calls, and new finance rules do not belong here.
