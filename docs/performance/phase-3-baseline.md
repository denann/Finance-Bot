# Phase 3 Performance Baseline

## Method

This baseline is **OFFLINE SYNTHETIC**. It uses deterministic 100, 1,000, and 10,000-row datasets. Baseline operation profiles are historical modelled values retained for comparison; optimized mode executes current services against instrumented in-memory worksheets. Timing values describe local Python work only. They do not represent Telegram, Google Sheets, Gemini, or production latency.

Run it with:

```powershell
python -m benchmarks.phase3_synthetic --mode baseline --sizes 100 1000 10000
```

## Hot-Path Inventory

| Entry point / context | Real synchronous operation | R/W | Resource / feature | Baseline call and row shape | Timeout / retry owner | Event-loop risk | Baseline telemetry |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Confirm single transaction | append, account reads/writes, transaction full read, Python sort, full update | R/W | transactions and accounts | transaction path 3 calls; N+1 read; N rewritten | Sheets client retry only; no handler timeout | High | adapter operation/duration only |
| Confirm five-item transaction | batch append, account reads/writes, transaction full read/update | R/W | transactions and accounts | transaction path 3 calls; N+1 read; N rewritten | Sheets client retry only; no handler timeout | High | adapter operation/duration only |
| `/last`, report, search | `get_all_records` plus local transforms | R | transactions and dependent sheets | one full read per helper; repeats possible in nested context | Sheets retry; no handler timeout | High | adapter operation/duration only |
| Export preparation | `get_all_records` plus CSV preparation | R | selected worksheet/filesystem | one full worksheet read | Sheets retry; no handler timeout | High | export outcome plus adapter metrics |
| `/ask` | multiple context helper reads then `llm.invoke` | R | transactions, accounts, budgets, debts, assets, Gemini ask | 5-7 Sheets calls; up to 3N transaction transfer; 1 Gemini | Gemini timeout/output bounds; Sheets retry | High | Gemini Phase 1B metrics, no request call budget |
| `/insight`, `/audit`, `/coach` | context helper reads then `llm.invoke` | R | finance context and Gemini feature | 5-7 Sheets calls; N-3N transfer; 1 Gemini | Gemini timeout/output bounds; Sheets retry | High | Gemini Phase 1B metrics |
| Text regex miss / intent fallback | `llm.invoke` | R | transaction parser and intent router | parser and router can chain | Gemini timeout; provider call has no request-wide budget | High | per invocation only |
| Multi-input unresolved items | parser fallback per unresolved line | R | Gemini parser | up to one call per item | Gemini timeout per call | High | per invocation only |
| Image receipt | image `llm.invoke`, broad fallback invoke | R | Gemini receipt parser | 1 normally; 2 after any first exception | Gemini timeout per attempt | High | per invocation only |
| Sheets adapter retry | synchronous request plus `time.sleep` exponential backoff | R/W | all worksheets | retry multiplies one logical operation | `SHEETS_MAX_RETRIES` and base delay | High when called directly by async handler | retry count and outcome |
| Scheduled export/report work | full read plus transform/send | R | Sheets/filesystem/Telegram | competes with handler-side synchronous work | single scheduler owner only | Medium | job outcome |

## Baseline Operation Counts

| Scenario | Sheets calls | Rows read at N rows | Rows written | Full rewrites | Duplicate reads | Gemini calls |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Single transaction save | 3 | N + header | N | 1 | 0 | 0 |
| Five-item save | 3 | N + header | N | 1 | 0 | 0 |
| `/last`, monthly report, search, export | 1 | N | 0 | 0 | 0 | 0 |
| AI context preparation | 5-7 | N to 3N transaction-row transfers | 0 | 0 | 1-2 | 1 |
| Five unresolved multi-input items | 0 | 0 | 0 | 0 | 0 | up to 5 |
| Image success / compatibility fallback | 0 | 0 | 0 | 0 | 0 | 1 / 2 |

Hard regression assertions use operation counts. Percentile timings emitted by the runner are informational only.

The generated rows are deterministic and contain multiple accounts, income, expenses, transfers, debt-marked rows, categories, multiple months, duplicate descriptions, stable IDs/dates, and empty or malformed optional fields. No real finance data is included.

| Documentation update | Status |
| :--- | :--- |
| Blocking and amplification inventory | Recorded |
| Baseline operation counts | Recorded |
| Synthetic fixture scope | Recorded |
| External calls | None |
