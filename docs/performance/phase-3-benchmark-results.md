# Phase 3 Benchmark Results

## Scope

These results are **OFFLINE SYNTHETIC**. They use deterministic fake operation profiles and locally generated finance rows. No Telegram, Google Sheets, Gemini, network, credentials, or user financial data were used.

Command:

```powershell
python -m benchmarks.phase3_synthetic --mode baseline --sizes 100 1000 10000 --iterations 5
python -m benchmarks.phase3_synthetic --mode optimized --sizes 100 1000 10000 --iterations 5
```

Timings cover local Python fixture processing only. They are not production latency claims. Operation counts are the deterministic regression contract.

## Operation-Count Comparison

| Scenario | Baseline | Optimized | Result |
| :--- | :--- | :--- | :--- |
| Single save at N rows | 3 Sheets calls; N+1 rows read; N rows written; 1 full rewrite | 2 Sheets calls; 0 rows downloaded for sorting; 1 row appended; 0 full rewrites | Full-rewrite amplification removed |
| Five-item save at N rows | 3 Sheets calls; N+1 rows read; N rows written; 1 full rewrite | 2 Sheets calls; 0 rows downloaded for sorting; 5 rows appended; 0 full rewrites | Bounded by batch size |
| `/last`, monthly report, search, export | 1 full logical worksheet read each | 1 full logical worksheet read each | No duplicate read; still O(N) |
| `/ask` context | 7 logical calls; 3N transaction-row transfers; 2 duplicate reads | 5 logical calls; N transaction-row transfer; 0 duplicate reads; 40 records selected | Request snapshot removes repeats |
| `/insight` and `/coach` context | 6 logical calls; 2N transaction-row transfers; 1 duplicate read | 5 logical calls; N transaction-row transfer; 0 duplicate reads; 40 records selected | Request snapshot removes repeats |
| `/audit` context | 7 logical calls; 3N transaction-row transfers; 2 duplicate reads | 5 logical calls; N transaction-row transfer; 0 duplicate reads; 40 records selected | Request snapshot removes repeats |
| Five unresolved text items | Up to 5 Gemini calls | At most 1 Gemini call | Per-update budget enforced |
| Image success | 1 Gemini call | 1 Gemini call | Unchanged |
| Image compatibility fallback | Up to 2 Gemini calls after broad errors | At most 2, only for recognized invocation-format compatibility errors | Retry classification bounded |

Transaction save call counts isolate the transaction append and sort-maintenance path. Account validation and balance operations remain governed by their existing financial contract.

## 100 Rows

| Scenario | Mode | p50 ms | p95 ms | p99 ms | Sheets | Rows read | Rows written | Rewrites | Duplicate reads | Gemini | Context chars | Selected |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Single save | Baseline | 0.017 | 0.036 | 0.036 | 3 | 101 | 100 | 1 | 0 | 0 | 0 | 0 |
| Single save | Optimized | 0.034 | 0.064 | 0.064 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Monthly report | Optimized | 0.008 | 0.009 | 0.009 | 1 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |
| `/ask` context | Optimized | 0.323 | 0.399 | 0.399 | 5 | 100 | 0 | 0 | 0 | 1 | 8,762 | 40 |
| Multi unresolved | Optimized | 0.332 | 1.585 | 1.585 | 0 | 0 | 0 | 0 | 0 | 1 | N/A | 0 |
| Image compatibility | Optimized | 0.371 | 0.430 | 0.430 | 0 | 0 | 0 | 0 | 0 | 2 | N/A | 0 |

## 1,000 Rows

| Scenario | Mode | p50 ms | p95 ms | p99 ms | Sheets | Rows read | Rows written | Rewrites | Duplicate reads | Gemini | Context chars | Selected |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Single save | Baseline | 0.246 | 0.302 | 0.302 | 3 | 1,001 | 1,000 | 1 | 0 | 0 | 0 | 0 |
| Single save | Optimized | 0.431 | 3.011 | 3.011 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Monthly report | Optimized | 0.126 | 0.241 | 0.241 | 1 | 1,000 | 0 | 0 | 0 | 0 | 0 | 0 |
| `/ask` context | Optimized | 0.806 | 0.869 | 0.869 | 5 | 1,000 | 0 | 0 | 0 | 1 | 8,750 | 40 |
| Multi unresolved | Optimized | 0.785 | 1.048 | 1.048 | 0 | 0 | 0 | 0 | 0 | 1 | N/A | 0 |
| Image compatibility | Optimized | 0.809 | 0.951 | 0.951 | 0 | 0 | 0 | 0 | 0 | 2 | N/A | 0 |

## 10,000 Rows

| Scenario | Mode | p50 ms | p95 ms | p99 ms | Sheets | Rows read | Rows written | Rewrites | Duplicate reads | Gemini | Context chars | Selected |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Single save | Baseline | 9.634 | 13.148 | 13.148 | 3 | 10,001 | 10,000 | 1 | 0 | 0 | 0 | 0 |
| Single save | Optimized | 13.630 | 14.144 | 14.144 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Monthly report | Optimized | 1.135 | 1.435 | 1.435 | 1 | 10,000 | 0 | 0 | 0 | 0 | 0 | 0 |
| `/ask` context | Optimized | 11.531 | 13.885 | 13.885 | 5 | 10,000 | 0 | 0 | 0 | 1 | 8,693 | 40 |
| Multi unresolved | Optimized | 13.329 | 17.027 | 17.027 | 0 | 0 | 0 | 0 | 0 | 1 | N/A | 0 |
| Image compatibility | Optimized | 12.624 | 13.585 | 13.585 | 0 | 0 | 0 | 0 | 0 | 2 | N/A | 0 |

## Responsiveness Contract

Deterministic event-based tests prove that a slow fake external read runs in a worker and an unrelated coroutine progresses. Separate semaphores cap interactive Sheets, Gemini, and scheduled work. No fragile developer-machine latency threshold is used in CI.

The synchronous retry `time.sleep` remains inside the Sheets adapter and is off the event loop for covered read/report/AI entry points. Financial mutation callbacks remain synchronous pending a reconciliation-safe mutation timeout design.

## Interpretation

The operation-count improvement is meaningful even where local fixture timings fluctuate. Server-side sort removes transaction-row transfer and rewrite growth from save. Request snapshots remove duplicate same-request reads, but the first report/AI read remains O(N). AI selection is capped at 40 records and the hard input bound is 100,000 characters.

| Documentation update | Status |
| :--- | :--- |
| Baseline method and hot paths | Updated |
| Before/after operation counts | Updated |
| 100/1,000/10,000 timing samples | Updated |
| Production latency claims | Explicitly excluded |
