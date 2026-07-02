# 06. Data Layer & Services

The project uses Google Sheets as the operational data store.

The data layer is split into two parts:

```text
app/services/      # business logic
app/sheets/        # low-level Google Sheets access
```

## Google Sheets tabs

The required tabs are:

```text
transactions
accounts
budgets
debts
debt_payments
categories
monthly_summary
recurring_rules
recurring_logs
assets
pending_expenses
net_worth_snapshots
```

`ensure_spreadsheet_schema()` creates missing tabs and writes headers when a sheet is empty.

## Sheets client

`app/sheets/client.py` handles:

- spreadsheet connection,
- worksheet lookup,
- schema validation,
- default row seeding,
- reads and writes,
- retry handling,
- best-effort rollback.

Google Sheets is transparent and easy to inspect, but it is not a transactional database. Because of that, rollback is implemented as a best-effort compensation strategy.

## Service layer

| File | Responsibility |
|---|---|
| `transaction_service.py` | Save, edit, delete, batch write, account balance update, and transaction-debt relation |
| `debt_service.py` | Debt creation, payment, settlement, void, edit, offset, and summaries |
| `budget_service.py` | Monthly budget setup, actual spending, and remaining budget |
| `report_service.py` | Daily, weekly, monthly, account, search, and category summaries |
| `pending_expense_service.py` | Pending expense creation, paid status, and cancellation |
| `recurring_service.py` | Recurring rules, next run date, recurring logs, and automatic transaction creation |
| `net_worth_service.py` | Assets, net worth summary, snapshots, and history |
| `finance_insight_service.py` | Finance context building for AI insight commands |

## Why service layer matters

Handlers should not directly manipulate spreadsheet rows. They should call services.

This keeps the system easier to maintain:

```text
Telegram handler
→ service function
→ Sheets client
```

If a bug happens, the layer boundary helps identify whether the issue is in user flow, finance logic, or data writing.
