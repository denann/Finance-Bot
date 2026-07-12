# Persistence Contract Assessment

## Conclusion

Current services expose many Sheets primitives directly, but their behavioral contracts are identifiable. A broad repository interface would add indirection without removing a current defect. Phase 5 therefore documents the future contract and makes no production refactor.

## Operation Map

| Domain operation | Current owner | Sheets primitives | Transaction/idempotency/order requirements | Reconciliation | Future tenant scope |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Save transaction | transaction service | append row, account lookup/update, server sort | One logical unit; immutable transaction ID; newest-first physical/read order | Candidate ID and balance outcome must be checked | Tenant/spreadsheet required |
| Save multiple | transaction service | append rows, account updates, server sort | Batch unit; every candidate ID preserved; stable input order | Reconcile each ID and dependent balance | Tenant required |
| Apply balance delta | transaction service | read accounts, update cells | Dependent write; account name unique in current sheet | Ambiguous update requires reconciliation | Tenant account namespace |
| Find transaction by ID | transaction service | full records read/filter | Immutable ID uniqueness | Read-only | Tenant query predicate |
| List by period / recent | transaction/report service | full records read/filter/sort | Deterministic date/ID order | Read-only | Tenant predicate/index |
| Search transactions | report service | full records read/filter | Relevance plus deterministic order | Read-only | Tenant predicate/index |
| Save debt | debt service/application coordinator | append debt, optional linked transaction/account writes | Cross-sheet logical unit; debt/source IDs | Rollback or reconciliation on partial outcome | Tenant debt and person namespace |
| Apply debt payment | debt service | append payment, update debt, linked transaction/account writes | Payment/debt IDs; remaining amount invariant | Multi-sheet reconciliation required | Tenant predicate and unique IDs |
| List balances | transaction service | full account records read | Account-name order/display | Read-only | Tenant predicate |
| Save budget | budget service | read, append/update cells | Month/category logical uniqueness | Confirm current row after ambiguous write | Tenant predicate/unique key |
| Claim recurring execution | recurring service | read rules/logs, append/update | `rule_id + scheduled date` exactly-once key | Existing log/transaction checked before retry | Tenant included in claim key |
| Save recurring log | recurring service | append log | Stable log/run/transaction IDs | Reconcile by run key | Tenant predicate |
| Save/update asset | net-worth service | append/update asset | Immutable asset ID; active/history state | Reconcile target ID/value | Tenant predicate |
| Save net-worth snapshot | net-worth service | append snapshot | Snapshot ID/date and derived totals | Reconcile ID/date | Tenant predicate |
| Export user data | handler/transaction service | full selected records read | Stable schema/order; read-only | None | Export exactly one tenant |
| Delete/void safely | transaction/debt application coordinator | read dependencies, reverse updates, delete/update rows | Previewed IDs; dependency order; no orphan links | Partial reverse/delete requires reconciliation | Tenant predicate on every lookup/write |

## Future Adapter Contract

A future adapter must support tenant-scoped read/query, immutable-ID uniqueness, atomic transaction boundaries where available, conditional/optimistic updates, deterministic ordering, idempotent recurring claims, bulk export/deletion, and auditable reconciliation. It must not expose raw row numbers as domain identity.

## Current Leaks and Decision

Services know worksheet names, row indices, column positions, and append/update/delete primitives. Those are real Sheets leaks, but replacing all of them now would be broad and speculative. A future migration should extract one vertical use case at a time with parity tests after an owner-approved persistence decision.

| Assessment | Result |
| :--- | :--- |
| Alternate adapter possible from current contracts | Yes, with staged extraction |
| Broad interface justified now | No |
| Production code changed | No |
| Schema changed | No |
