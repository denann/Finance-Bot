# Performance, Latency, and Gemini Cost Audit

Tanggal audit: 2026-07-10

## Ringkasan

Hot path saat ini menggabungkan handler async Telegram dengan operasi sinkron Google Sheets, Gemini, dan `time.sleep`. Risiko terbesar bukan micro-optimization, tetapi event loop yang terblokir, pembacaan ulang seluruh worksheet, rewrite/sort seluruh transaksi, serta jumlah panggilan Gemini yang belum diukur. Audit tidak membuat estimasi biaya nominal karena volume token, model efektif, cache, dan trafik produksi tidak tersedia.

## Call-flow dan sumber latency

| Flow | Operasi berpotensi mahal | Pola | Risiko | Finding |
|---|---|---|---|---|
| Regex transaction save | append transaction, balance update, sort/rewrite | sinkron dalam handler async | semua update Telegram tertahan | F-002, F-009, F-010 |
| Multi-input | parse per baris, lookup account/category, batch write | linear terhadap jumlah baris | latency panjang dan partial-failure ambiguity | F-009, F-016 |
| Debt/payment | debt sheet + transaction/balance | multi-sheet serial | partial write dan long critical section | F-003, F-009 |
| Reports/search/export | full-sheet reads dan transform | O(rows), tanpa pagination/cache formal | melambat saat history tumbuh | F-009, F-011 |
| AI intent | context reads + Gemini | network + token proportional | latency dan cost tidak terlihat | F-011, F-012 |
| Regex miss | Gemini parser lalu intent router | dapat menjadi dua call berantai | cost/latency berlipat | F-013 |
| Image receipt | image Gemini, retry pada exception | hingga dua request | duplikasi biaya pada error ambigu | F-012, F-013 |
| Sheets retry | sync call + exponential sleep | event loop blocked | head-of-line blocking | F-005, F-009 |
| Scheduled reports | full reads + send | sama dengan user request | contention dengan interactive traffic | F-020 |

## Temuan utama

### Event loop blocking

`gspread`, Gemini calls, dan retry sleep dipanggil dari jalur async tanpa batas concurrency atau executor yang konsisten. Satu request lambat dapat menahan update lain. Minimum safe improvement adalah membungkus I/O sinkron di worker thread dengan timeout, cancellation policy, dan concurrency limit; bukan sekadar menambah worker process karena scheduler dan shared sheet belum multi-instance safe.

### Read/write amplification

- Save transaksi dapat memicu rewrite/sort seluruh transaction sheet.
- Report, search, AI context, dan net-worth flow membaca range besar berulang kali.
- Cache worksheet object bukan cache data; jumlah API call tetap tumbuh bersama fitur dan row count.
- Google Sheets tetap layak untuk personal, low-volume use, tetapi perlu target ukuran dan latency yang eksplisit.

### Gemini call amplification

Kemungkinan call chain yang terverifikasi secara statik:

1. regex parser gagal → Gemini parser;
2. hasil masih pending/ambigu → intent routing Gemini;
3. AI insight → full data context + Gemini;
4. image exception → retry request.

Tidak ada counter yang menunjukkan berapa call per update, input/output token, cache hit, timeout, atau biaya per feature. Karena itu, cost regression tidak dapat dideteksi.

## Instrumentasi minimum

Catat structured event tanpa menyimpan raw message/receipt:

| Metric | Labels minimum | Tujuan |
|---|---|---|
| `telegram_update_duration_ms` | handler, outcome | latency end-to-end |
| `sheets_call_duration_ms` | worksheet, operation, outcome | hotspot API |
| `sheets_rows_read/written` | worksheet, operation | amplification |
| `sheets_retry_total` | operation, error_class | retry storm/duplicate risk |
| `gemini_call_total` | feature, model, outcome | call amplification |
| `gemini_duration_ms` | feature, model | latency |
| `gemini_input/output_tokens` | feature, model | cost attribution |
| `gemini_fallback_total` | source, target | model/parser drift |
| `scheduler_job_duration_ms` | job, outcome | overlap detection |
| `pending_state_age_seconds` | flow, terminal_outcome | stale state |

Tambahkan correlation/update ID, transaction/pending ID yang di-hash, model ID, prompt version, dan retry attempt. Jangan log token, credential, raw financial message, receipt image, atau full Gemini prompt/context.

## Guardrail yang disarankan

- Timeout eksplisit per Sheets/Gemini call dan deadline end-to-end per update.
- Concurrency limit terpisah untuk interactive, AI, dan scheduled work.
- Idempotency key sebelum retry non-idempotent write.
- Per-request Gemini budget: maksimum call, maksimum input rows, dan maksimum output token.
- Pagination/aggregation untuk report dan AI context; jangan selalu kirim history mentah.
- Threshold berbasis pengukuran untuk memindahkan workload dari Sheets ke database/worker.

## Benchmark plan

Gunakan fixture sintetis 100, 1.000, dan 10.000 transaksi tanpa data pengguna. Ukur p50/p95/p99 untuk parse-only, preview, save, report, export, dan AI-context preparation; ukur API-call count dan rows transferred. Mock external APIs untuk CI, lalu lakukan smoke benchmark terkontrol pada staging sheet setelah persetujuan owner.

## Keputusan owner yang diperlukan

- SLO latency interactive dan batas biaya Gemini bulanan/per feature.
- Apakah raw AI features boleh menerima seluruh history atau hanya agregat terpilih.
- Apakah deployment tetap single-process; scale-out sebelum locking adalah tidak aman.
- Perubahan model default, prompt contract, timeout, atau retry behavior memerlukan approval karena dapat mengubah output publik.
