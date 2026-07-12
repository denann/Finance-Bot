# Phase 5 Scale Evidence

## Method

`python -m benchmarks.phase5_scale` runs current application service paths against the Phase 3 instrumented in-memory Sheets adapter. Each observation uses one deterministic synthetic dataset and records actual adapter calls, rows transferred/written, duplicate reads, rewrites, selected AI records, context characters, and Python peak allocation via `tracemalloc`.

Results are **OFFLINE SYNTHETIC OBSERVED APPLICATION**. Local milliseconds and memory are developer-machine evidence, not Telegram, gspread, Gemini, quota, or production latency. Workload growth scenarios are separately labelled **MODELLED WORKLOAD PROJECTION**.

## Dataset

Rows contain stable IDs/dates, multiple accounts/categories/months, income, expenses, transfers, debt-marked entries, repeated descriptions, and empty/malformed optional values. Sizes: 100, 1,000, 10,000, 25,000, 50,000, and 100,000 transactions.

## Observed Operation Growth

| Scenario | Sheets calls | Rows transferred at N | Rows written | Growth | Default 50k row budget |
| :--- | ---: | ---: | ---: | :--- | :--- |
| Single save | 2 | 0 | 1 | O(1) application row transfer | Not reached by transaction sort path |
| `/last` | 1 | N | 0 | O(N) | Reached above 50,000 |
| Monthly report | 2 | N | 0 | O(N) | Reached above 50,000 |
| Search | 2 | N | 0 | O(N) | Reached above 50,000 |
| Export | 1 | N | 0 | O(N) | Reached above 50,000 |
| `/ask` context | 6 | N + 6 supporting rows | 0 | O(N) first read; selected context bounded | Reached at 50,000 because total is 50,006 |

All observed scenarios had zero duplicate worksheet reads and zero full-range transaction rewrites. `/ask` selected 15 relevant records in the current path, below the configured hard cap of 40.

## Peak Python Allocation

| Rows | Save | `/last`/report/search | Export | `/ask` |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 1.3 MB | 0.2-0.4 MB | 0.2 MB | 0.3 MB |
| 1,000 | 2.1 MB | 2.3 MB | 1.9 MB | 3.0 MB |
| 10,000 | 10.0 MB | 23.1 MB | 18.7 MB | 30.1 MB |
| 25,000 | 23.3 MB | 57.7 MB | 47.4 MB | 75.1 MB |
| 50,000 | 45.4 MB | 116.6 MB | 96.0 MB | 151.4 MB |
| 100,000 | 89.5 MB | 231.7 MB | 190.6 MB | 301.3 MB |

Values are rounded from one run and include synthetic construction/fake-adapter copies. They show linear allocation growth, not a production memory limit.

## Modelled Workload Projections

| Transactions/month | 1 year | 3 years | 5 years |
| ---: | ---: | ---: | ---: |
| 100 | 1,200 | 3,600 | 6,000 |
| 500 | 6,000 | 18,000 | 30,000 |
| 2,000 | 24,000 | 72,000 | 120,000 |

These are arithmetic planning scenarios, not observed owner workload and not capacity claims.

## Other Shapes

- Account and debt mutations touch bounded logical records but may scan worksheets to resolve rows; cross-sheet correctness matters more than raw call count.
- Scheduler currently registers a fixed set of in-process jobs. Recurring execution growth depends on active rules and remains single-owner.
- Pending actions are bounded in per-user memory and expire; they are not durable workload storage.
- Export transfers every selected row and creates a CSV, so transfer and memory scale with retained history.
- AI prompt records are bounded, but deterministic preparation still requires the first transaction worksheet read.

## Evidence Still Required

Dummy external staging must measure real read/report/save latency, row-transfer behavior, server sort, retries, quota incidents, scheduler runs, Telegram delivery, and provider completion. No universal maximum user or row count is declared.

| Bottleneck | Evidence decision |
| :--- | :--- |
| O(N) report/search/export transfer | Verified offline; monitor/stage |
| 50k request row guard | Verified application behavior; not a migration trigger alone |
| Save amplification | Bounded after Phase 3 |
| Real Sheets quota/network | Unknown until staging |
