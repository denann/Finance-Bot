# Data Model

## Canonical Schema

`app/sheets/client.py::SHEET_SCHEMAS` is canonical. This document describes it; changing this page does not migrate a spreadsheet. Schema changes require owner approval, migration planning, backup, compatibility tests, and dummy-Sheets staging.

| Worksheet | Purpose and primary identifier | Columns in order | Important invariants and relations | Mutation owner and idempotency |
| :--- | :--- | :--- | :--- | :--- |
| `transactions` | Financial ledger; `id` | `id`, `date`, `type`, `amount`, `category`, `account`, `to_account`, `subject`, `description`, `catatan`, `tipe_pengeluaran`, `raw_input`, `parsed_by`, `hutang_id`, `tipe_hutang` | Account/category names are application-resolved; debt fields link ledger rows to debt records; transfers use source and destination accounts | Transaction application/service; immutable ID reconciliation prevents blind duplicate append |
| `accounts` | Account balances; `account_name` | `account_name`, `type`, `balance`, `currency`, `last_updated` | Names identify accounts; balances are changed only through confirmed finance flows | Transaction/resolver services; reconcile an ambiguous balance update before retry |
| `budgets` | Monthly category budgets; `id` | `id`, `month`, `category`, `budget_amount`, `created_at`, `updated_at` | Month/category identifies reporting intent; actuals are calculated from ledger data | Budget service; confirmed mutation with stable record ID |
| `debts` | Debt/receivable principal state; `id` | `id`, `type`, `person_name`, `original_amount`, `remaining_amount`, `description`, `due_date`, `is_settled`, `created_at`, `settled_at`, `source_transaction_id`, `cashflow_mode`, `fronting_mode` | Direction, remaining amount, source transaction, cashflow/fronting mode must remain consistent | Debt application/service; IDs and source links support reconciliation |
| `debt_payments` | Debt payment history; `id` | `id`, `debt_id`, `amount`, `date`, `note` | `debt_id` references `debts.id` in application logic; no database FK exists | Debt service; payment IDs and debt-state validation guard duplicates |
| `categories` | Category metadata; `category_name` | `category_name`, `type`, `emoji`, `aliases` | Aliases are comma-separated metadata; type/symbol/name/aliases move together | Resolver/category flow; name matching and confirmation control additions |
| `monthly_summary` | Optional persisted monthly aggregate; `month` | `month`, `total_income`, `total_expense`, `net`, `created_at`, `updated_at` | Derived values must match ledger calculation rules | Reporting/bootstrap owner; rebuild from source ledger when necessary |
| `recurring_rules` | Recurring templates; `id` | `id`, `name`, `type`, `amount`, `category`, `account`, `to_account`, `subject`, `description`, `catatan`, `tipe_pengeluaran`, `frequency`, `day_of_month`, `next_run_date`, `is_active`, `created_at`, `updated_at` | A rule is a template, not an already-paid transaction | Recurring service; rule ID plus scheduled date forms logical idempotency |
| `recurring_logs` | Recurring execution evidence; `id` | `id`, `rule_id`, `transaction_id`, `run_date`, `status`, `message`, `created_at` | Links rule/run date to transaction outcome | Recurring service; checked before creating the same scheduled occurrence |
| `assets` | Active/inactive asset holdings; `id` | `id`, `name`, `category`, `current_value`, `description`, `is_active`, `created_at`, `updated_at`, `asset_type`, `quantity`, `unit`, `price_source`, `price_per_unit`, `last_price_update`, `purchase_price_per_unit`, `purchase_date` | Quantity/pricing fields apply to supported asset modes; inactive records remain historical | Net-worth service; confirmed ID-addressed updates |
| `pending_expenses` | Future/planned expense state; `id` | `id`, `due_date`, `month`, `due_precision`, `amount`, `category`, `account`, `subject`, `description`, `status`, `created_at`, `updated_at`, `paid_transaction_id`, `raw_input` | Pending rows do not change balances; paid status links the created transaction | Pending-expense service; status and paid transaction ID prevent repeat payment |
| `net_worth_snapshots` | Historical net-worth point; `id` | `id`, `snapshot_date`, `total_accounts`, `total_assets`, `total_liabilities`, `net_worth`, `created_at` | Snapshot is derived evidence for a date, not a live balance source | Net-worth service; confirmed snapshot IDs/date checks |

## Persistence Limitations

- There is no tenant ID because the approved product is single user.
- Relationships are application-managed; Google Sheets does not enforce foreign keys.
- Idempotency and reconciliation are application-managed with logical IDs and status fields.
- Multi-sheet rollback is compensating behavior and can itself fail.
- Migrations are explicit owner-approved operations; the startup schema check may create/validate required tabs but does not authorize silent semantic schema changes.

| Schema verification | Result |
| :--- | :--- |
| Worksheets documented | 12 |
| Columns documented | 115 |
| Schema changes made in Phase 4 | None |
