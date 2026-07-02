# 06. Data Layer and Services

Google Sheets is the main data store.

The service layer contains finance business logic, while the Sheets layer handles low-level read and write operations.

## Main sheets

- `transactions`
- `accounts`
- `budgets`
- `debts`
- `debt_payments`
- `categories`
- `monthly_summary`
- `recurring_rules`
- `recurring_logs`
- `assets`
- `pending_expenses`
- `net_worth_snapshots`

## Important design

The parser does not save data. It only creates structured data. The service layer validates and applies business rules. The Sheets client writes the final data.
