# Persistence Options

## Comparison

| Criterion | A. Current Sheets | B. Spreadsheet per user | C. Hybrid DB + Sheets | D. Relational primary |
| :--- | :--- | :--- | :--- | :--- |
| Current scope fit | Best | Unneeded for one user | Excessive | Excessive |
| Atomicity | Compensating rollback, reconciliation | Same within each spreadsheet | DB core strong; sync remains complex | Strong relational transactions |
| Idempotency | Application IDs/run keys | Same, tenant mapping added | DB unique keys plus sync IDs | Unique constraints and transactions |
| Query performance | O(N) worksheet reads | O(N) per smaller tenant | Indexed DB queries | Indexed DB queries |
| Report/Sheets visibility | Native | Native per user | Preserved through controlled projection | Requires export/report integration |
| Privacy isolation | One owner only | Strong spreadsheet boundary if mapping is correct | Tenant DB plus projection controls | Tenant predicates/constraints required |
| Operations/deployment | Lowest | More credentials/spreadsheets | Highest sync operations | Migrations/backups/DB operations |
| Backup/recovery | Spreadsheet copies | Per-user copies | DB + Sheets coordinated recovery | DB backup/PITR plus exports |
| Export/deletion | Direct current flow | Per spreadsheet | Cross-store orchestration | Tenant-scoped DB operation |
| Scheduler | One in process | Tenant-aware single owner initially | Durable claims likely needed | Durable claims/queue likely needed |
| Migration effort | None | Medium authorization/routing work | Very high dual-system work | High schema/data/cutover work |
| Rollback difficulty | Lowest | Medium | Highest due synchronization | High during cutover |
| Maintenance burden | Lowest | Medium | Highest | Medium-high |

## Option Assessments

### A. Keep Current Architecture

One authorized user, one process, one spreadsheet, current schema, and one scheduler owner. It preserves visibility and all tested contracts. O(N) reads, quota dependence, and reconciliation limitations are accepted and monitored.

### B. Spreadsheet per User

This is the first compatibility candidate if a small number of private users is explicitly approved. A tenant registry maps identity to credentials/spreadsheet; current worksheet columns remain unchanged. It isolates rows without forcing a database, but adds credential lifecycle, tenant-aware caches/actions/jobs/logs, and operational overhead.

### C. Hybrid Persistence

A database becomes authoritative for identity and transactions while Sheets is a projection/export surface. This preserves visibility but creates synchronization, dual recovery, ordering, deletion, and reconciliation complexity. It is not justified without a strong reporting requirement plus proven relational triggers.

### D. Relational Primary Store

A relational database owns tenant-scoped finance records, constraints, indexes, migrations, and atomic mutations. Sheets becomes optional export/reporting. This best supports multi-user/concurrent queries but carries the largest compatibility and migration burden.

## Decision Input

No current RED trigger is proven. Option A has the lowest risk for the declared product. Option B is the preferred first design study if user two becomes a real requirement, not an automatic final architecture. Options C/D require explicit owner approval and measured evidence.
