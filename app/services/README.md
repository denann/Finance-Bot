# app/services

This folder contains the finance business logic.

Handlers should stay focused on Telegram interaction. Services handle the actual finance operations, such as saving transactions, updating balances, managing debts, calculating reports, and preparing AI context.

## Main services

- `transaction_service.py`: save, edit, delete, batch transactions, and account balance updates.
- `debt_service.py`: debt, receivable, payment, settlement, void, and edit logic.
- `budget_service.py`: budget setup and budget realization.
- `report_service.py`: transaction reports and search.
- `chart_service.py`: read-only transaction and category chart generation.
- `pending_expense_service.py`: planned expenses and future bills.
- `recurring_service.py`: recurring rules and logs.
- `net_worth_service.py`: assets and net worth snapshots.
- `finance_insight_service.py`: structured context for AI insight.
- `resolver_service.py`: deterministic account and category resolution used by services.
- `privacy_service.py`: user-facing privacy summary content.
- `operation_errors.py`: shared mutation outcome and partial-failure contracts.

## Ownership Contract

Services own deterministic finance validation, calculations, row construction, and feature persistence contracts. Telegram objects, command routing, provider prompts, and cross-domain import cycles do not belong here. Application use cases coordinate domains; the Sheets client owns remote mechanics. Service and regression tests verify these contracts.
