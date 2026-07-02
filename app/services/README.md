# app/services

This folder contains the finance business logic.

Handlers should stay focused on Telegram interaction. Services handle the actual finance operations, such as saving transactions, updating balances, managing debts, calculating reports, and preparing AI context.

## Main services

- `transaction_service.py`: save, edit, delete, batch transactions, and account balance updates.
- `debt_service.py`: debt, receivable, payment, settlement, void, and edit logic.
- `budget_service.py`: budget setup and budget realization.
- `report_service.py`: transaction reports and search.
- `pending_expense_service.py`: planned expenses and future bills.
- `recurring_service.py`: recurring rules and logs.
- `net_worth_service.py`: assets and net worth snapshots.
- `finance_insight_service.py`: structured context for AI insight.
