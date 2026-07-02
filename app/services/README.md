# app/services

This folder contains the finance business logic.

Handlers should not directly change spreadsheet rows. They should call services. This keeps the project easier to debug because user interaction, finance logic, and data writing stay separated.

## Files

| File | Purpose |
|---|---|
| `transaction_service.py` | Transactions, account balance, edit, delete, and batch save |
| `debt_service.py` | Debt creation, payment, settlement, void, and edit |
| `budget_service.py` | Budget setup, actual spending, and remaining budget |
| `report_service.py` | Reports, search, account summaries, and category summaries |
| `pending_expense_service.py` | Planned or incomplete expenses |
| `recurring_service.py` | Recurring rules and logs |
| `net_worth_service.py` | Assets, snapshots, and net worth calculation |
| `finance_insight_service.py` | Context building for AI insight commands |

If a saved value is wrong, this folder is usually the best place to inspect first.
