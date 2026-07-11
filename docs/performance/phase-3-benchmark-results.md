# Phase 3 Benchmark Results — Corrected Measurement

> **OFFLINE SYNTHETIC.** `optimized` results below execute current application services against an instrumented in-memory Sheets adapter. `baseline` values are historical modelled profiles retained only for before/after comparison. Neither mode represents real Telegram, Google Sheets, Gemini, network, or production latency.

## Method

- Deterministic synthetic datasets: 100, 1,000, and 10,000 transactions.
- Five iterations per scenario.
- Optimized operation counts are observed from actual worksheet method calls made by the application.
- Baseline counts are explicitly labelled `historical_modelled`; they are not presented as executed current code.
- p50/p95/p99 are local Python timings and informational only.

## Key operation contracts

| Contract | Observed optimized result |
| :--- | :--- |
| Single transaction save | 2 worksheet operations: 1 append + 1 server-side sort; 0 transaction rows downloaded; 0 full-range rewrites |
| Five-item save | 2 worksheet operations: 1 batch append + 1 server-side sort; 5 rows written; 0 full-range rewrites |
| Same-request AI reads | 0 duplicate worksheet reads in all measured AI scenarios |
| Multi-input Gemini | 1 request-scoped call budget consumption |
| Image Gemini | 1 normal call; 2 only for compatibility scenario |

## 100 rows

| Scenario | Mode | Measurement | p50 ms | p95 ms | Sheets calls | Rows read | Rows written | Rewrites | Duplicate reads | Gemini | Context chars | Selected |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Single save | Baseline | `historical_modelled` | 0.007 | 0.014 | 3 | 101 | 100 | 1 | 0 | 0 | 0 | 0 |
| Single save | Optimized | `observed_application` | 0.691 | 11.576 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Five-item save | Baseline | `historical_modelled` | 0.007 | 0.008 | 3 | 101 | 100 | 1 | 0 | 0 | 0 | 0 |
| Five-item save | Optimized | `observed_application` | 0.740 | 1.242 | 2 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| /last | Baseline | `historical_modelled` | 0.007 | 0.008 | 1 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |
| /last | Optimized | `observed_application` | 1.047 | 1.478 | 1 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |
| Monthly report | Baseline | `historical_modelled` | 0.007 | 0.009 | 1 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |
| Monthly report | Optimized | `observed_application` | 1.177 | 1.363 | 2 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |
| Search | Baseline | `historical_modelled` | 0.007 | 0.008 | 1 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |
| Search | Optimized | `observed_application` | 0.752 | 1.148 | 2 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |
| Export | Baseline | `historical_modelled` | 0.007 | 0.008 | 1 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |
| Export | Optimized | `observed_application` | 0.872 | 0.927 | 1 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |
| /ask | Baseline | `historical_modelled` | 0.007 | 0.008 | 7 | 300 | 0 | 0 | 2 | 1 | 0 | 15 |
| /ask | Optimized | `observed_application` | 3.303 | 4.197 | 6 | 106 | 0 | 0 | 0 | 1 | 6808 | 15 |
| /insight | Baseline | `historical_modelled` | 0.007 | 0.008 | 6 | 200 | 0 | 0 | 1 | 1 | 0 | 15 |
| /insight | Optimized | `observed_application` | 1.877 | 2.161 | 6 | 106 | 0 | 0 | 0 | 1 | 2645 | 0 |
| /audit | Baseline | `historical_modelled` | 0.012 | 0.014 | 7 | 300 | 0 | 0 | 2 | 1 | 0 | 15 |
| /audit | Optimized | `observed_application` | 1.378 | 1.455 | 4 | 105 | 0 | 0 | 0 | 1 | 878 | 0 |
| /coach | Baseline | `historical_modelled` | 0.007 | 0.008 | 6 | 200 | 0 | 0 | 1 | 1 | 0 | 15 |
| /coach | Optimized | `observed_application` | 2.140 | 2.671 | 6 | 106 | 0 | 0 | 0 | 1 | 2709 | 0 |
| Multi unresolved | Baseline | `historical_modelled` | 0.007 | 0.008 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 |
| Multi unresolved | Optimized | `observed_application` | 0.106 | 0.135 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| Image success | Baseline | `historical_modelled` | 0.007 | 0.008 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| Image success | Optimized | `observed_application` | 0.101 | 0.117 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| Image compatibility | Baseline | `historical_modelled` | 0.007 | 0.008 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| Image compatibility | Optimized | `observed_application` | 0.099 | 0.114 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |

## 1,000 rows

| Scenario | Mode | Measurement | p50 ms | p95 ms | Sheets calls | Rows read | Rows written | Rewrites | Duplicate reads | Gemini | Context chars | Selected |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Single save | Baseline | `historical_modelled` | 0.083 | 0.212 | 3 | 1001 | 1000 | 1 | 0 | 0 | 0 | 0 |
| Single save | Optimized | `observed_application` | 1.505 | 2.144 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Five-item save | Baseline | `historical_modelled` | 0.084 | 0.092 | 3 | 1001 | 1000 | 1 | 0 | 0 | 0 | 0 |
| Five-item save | Optimized | `observed_application` | 1.351 | 1.562 | 2 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| /last | Baseline | `historical_modelled` | 0.087 | 0.126 | 1 | 1000 | 0 | 0 | 0 | 0 | 0 | 0 |
| /last | Optimized | `observed_application` | 13.300 | 67.545 | 1 | 1000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Monthly report | Baseline | `historical_modelled` | 0.085 | 0.095 | 1 | 1000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Monthly report | Optimized | `observed_application` | 12.411 | 13.575 | 2 | 1000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Search | Baseline | `historical_modelled` | 0.086 | 0.092 | 1 | 1000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Search | Optimized | `observed_application` | 8.444 | 8.917 | 2 | 1000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Export | Baseline | `historical_modelled` | 0.085 | 0.093 | 1 | 1000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Export | Optimized | `observed_application` | 7.492 | 8.478 | 1 | 1000 | 0 | 0 | 0 | 0 | 0 | 0 |
| /ask | Baseline | `historical_modelled` | 0.086 | 0.096 | 7 | 3000 | 0 | 0 | 2 | 1 | 0 | 15 |
| /ask | Optimized | `observed_application` | 31.259 | 36.930 | 6 | 1006 | 0 | 0 | 0 | 1 | 6879 | 15 |
| /insight | Baseline | `historical_modelled` | 0.086 | 0.107 | 6 | 2000 | 0 | 0 | 1 | 1 | 0 | 15 |
| /insight | Optimized | `observed_application` | 19.325 | 21.993 | 6 | 1006 | 0 | 0 | 0 | 1 | 10815 | 40 |
| /audit | Baseline | `historical_modelled` | 0.111 | 0.142 | 7 | 3000 | 0 | 0 | 2 | 1 | 0 | 15 |
| /audit | Optimized | `observed_application` | 10.778 | 12.087 | 4 | 1005 | 0 | 0 | 0 | 1 | 7542 | 24 |
| /coach | Baseline | `historical_modelled` | 0.087 | 0.128 | 6 | 2000 | 0 | 0 | 1 | 1 | 0 | 15 |
| /coach | Optimized | `observed_application` | 18.904 | 19.756 | 6 | 1006 | 0 | 0 | 0 | 1 | 10879 | 40 |
| Multi unresolved | Baseline | `historical_modelled` | 0.123 | 0.151 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 |
| Multi unresolved | Optimized | `observed_application` | 0.696 | 0.772 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| Image success | Baseline | `historical_modelled` | 0.086 | 0.163 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| Image success | Optimized | `observed_application` | 0.675 | 0.715 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| Image compatibility | Baseline | `historical_modelled` | 0.133 | 0.147 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| Image compatibility | Optimized | `observed_application` | 0.590 | 0.669 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |

## 10,000 rows

| Scenario | Mode | Measurement | p50 ms | p95 ms | Sheets calls | Rows read | Rows written | Rewrites | Duplicate reads | Gemini | Context chars | Selected |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Single save | Baseline | `historical_modelled` | 3.444 | 52.761 | 3 | 10001 | 10000 | 1 | 0 | 0 | 0 | 0 |
| Single save | Optimized | `observed_application` | 9.573 | 18.315 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Five-item save | Baseline | `historical_modelled` | 2.237 | 6.246 | 3 | 10001 | 10000 | 1 | 0 | 0 | 0 | 0 |
| Five-item save | Optimized | `observed_application` | 9.085 | 14.995 | 2 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| /last | Baseline | `historical_modelled` | 2.182 | 3.547 | 1 | 10000 | 0 | 0 | 0 | 0 | 0 | 0 |
| /last | Optimized | `observed_application` | 135.012 | 199.007 | 1 | 10000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Monthly report | Baseline | `historical_modelled` | 2.210 | 4.193 | 1 | 10000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Monthly report | Optimized | `observed_application` | 123.660 | 190.793 | 2 | 10000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Search | Baseline | `historical_modelled` | 2.082 | 2.243 | 1 | 10000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Search | Optimized | `observed_application` | 83.605 | 134.450 | 2 | 10000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Export | Baseline | `historical_modelled` | 2.063 | 2.110 | 1 | 10000 | 0 | 0 | 0 | 0 | 0 | 0 |
| Export | Optimized | `observed_application` | 73.244 | 108.146 | 1 | 10000 | 0 | 0 | 0 | 0 | 0 | 0 |
| /ask | Baseline | `historical_modelled` | 2.488 | 3.139 | 7 | 30000 | 0 | 0 | 2 | 1 | 0 | 15 |
| /ask | Optimized | `observed_application` | 306.021 | 359.963 | 6 | 10006 | 0 | 0 | 0 | 1 | 6865 | 15 |
| /insight | Baseline | `historical_modelled` | 2.263 | 2.574 | 6 | 20000 | 0 | 0 | 1 | 1 | 0 | 15 |
| /insight | Optimized | `observed_application` | 186.061 | 226.885 | 6 | 10006 | 0 | 0 | 0 | 1 | 11906 | 40 |
| /audit | Baseline | `historical_modelled` | 2.276 | 2.419 | 7 | 30000 | 0 | 0 | 2 | 1 | 0 | 15 |
| /audit | Optimized | `observed_application` | 96.702 | 130.695 | 4 | 10005 | 0 | 0 | 0 | 1 | 7815 | 40 |
| /coach | Baseline | `historical_modelled` | 2.096 | 2.448 | 6 | 20000 | 0 | 0 | 1 | 1 | 0 | 15 |
| /coach | Optimized | `observed_application` | 167.494 | 214.163 | 6 | 10006 | 0 | 0 | 0 | 1 | 11970 | 40 |
| Multi unresolved | Baseline | `historical_modelled` | 2.083 | 2.262 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 |
| Multi unresolved | Optimized | `observed_application` | 4.842 | 5.465 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| Image success | Baseline | `historical_modelled` | 2.050 | 2.136 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| Image success | Optimized | `observed_application` | 4.875 | 5.481 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| Image compatibility | Baseline | `historical_modelled` | 2.098 | 2.175 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| Image compatibility | Optimized | `observed_application` | 5.057 | 5.175 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |

## Interpretation

- The hard evidence is the observed operation count, not local runtime.
- Save-path sorting no longer scales row transfer or rewrite volume with worksheet size.
- Read-only report and AI preparation still perform O(N) first reads where the Google Sheets persistence model requires them.
- Request-scoped snapshots remove repeated transfers inside the same logical request.
- Real latency, API quotas, permissions, and server-side sort semantics still require dummy-Sheets staging.
