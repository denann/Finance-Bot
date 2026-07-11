# Testing and Observability Gaps

Tanggal audit: 2026-07-10

## Kondisi saat ini

- Tidak ada test suite yang dilacak Git. `.gitignore` bahkan mengabaikan direktori `tests/`.
- Dua `ai_command_tester.py` hampir identik dan lebih dekat ke diagnostic script daripada deterministic automated suite.
- Audit environment tidak memiliki `pytest`, `gspread`, dan dependency lengkap sesuai manifest.
- Logging ada, tetapi belum menjadi structured audit trail untuk update→preview→confirm→write.

## Verifikasi yang dijalankan

| Check | Hasil | Catatan |
|---|---|---|
| Compile seluruh 53 file Python di memory | PASS | Tidak membuat `.pyc`; memeriksa syntax, bukan behavior |
| `python -m pytest --collect-only -q` | FAIL/ENV | `No module named pytest` |
| `python scripts/ai_command_tester.py --sample` | FAIL/ENV | stub/import tidak memenuhi `gspread.exceptions`; script tidak terisolasi dari app dependency |
| Parser corpus offline | PASS dengan defect | routing utama masuk akal; invalid date menjadi tanggal hari audit (F-006) |
| Injected Sheets retry simulation | DEFECT CONFIRMED | ambiguous 500 menghasilkan dua write attempts (F-005) |
| Injected save/balance failure simulation | DEFECT CONFIRMED | service masih melaporkan success setelah balance exception (F-002) |
| Telegram/Sheets/Gemini end-to-end | NOT_RUN | menjaga audit read-only dan tidak memiliki staging credentials |

## Test pyramid yang dibutuhkan

### Unit tests

- Amount/date/account/category parser, termasuk invalid dan ambiguous inputs.
- Intent precedence: debt, receivable, transfer, split, set-balance sebelum expense/income.
- Callback codec dan immutable pending/action ID.
- Currency rounding, split allocation, and balance delta.
- Config parsing, timezone, retry classification, idempotency key.
- Formatter dan help examples sebagai golden tests.

### Service contract tests

- Fake Sheets client dengan failure injection pada setiap write boundary.
- Atomicity untuk transaction+balance+debt/receivable/split.
- Result-style failure harus dipromosikan menjadi transaction failure/rollback.
- Retry before commit, after ambiguous commit, quota, timeout, and permanent error.
- Duplicate callback dan duplicate scheduled job.

### Handler integration tests

- Update→clarification→preview→confirm/cancel untuk setiap state-changing command.
- Old callback setelah flow baru dimulai.
- Restart saat pending state; expired pending state; unrelated message saat pending.
- Bulk item clarification tanpa membuang item valid.
- Batal button tersedia dan benar-benar tidak menulis data.

### End-to-end staging tests

Gunakan bot token dan spreadsheet khusus staging, bukan spreadsheet produksi. Snapshot worksheet sebelum test, gunakan unique run ID, verifikasi exact rows/balances, lalu cleanup terkontrol. Test destructive rollback hanya setelah owner menyediakan staging contract.

## Critical untested contracts

| Contract | Risiko tanpa test | Finding |
|---|---|---|
| Preview terikat ke write yang sama | stale callback menulis action lain | F-001 |
| Save success berarti semua side effect konsisten | false success/corrupt balance | F-002 |
| Atomic multi-sheet mutation | partial debt/transaction state | F-003 |
| Recurring run exactly once | duplicate transaction | F-004 |
| Retry write exactly once | duplicate rows | F-005 |
| Invalid input never silently normalized | wrong transaction date/type | F-006 |
| Every public mutation has final confirmation | accidental write | F-007 |

## Observability gaps

- Tidak ada durable audit event dengan update ID, actor, action ID, preview hash, confirmation, sheet mutation IDs, dan final outcome.
- Tidak ada metric latency, Sheets call/retry, Gemini call/token/cost, scheduler overlap, or stale callback.
- Health endpoint hanya menjawab liveness dan tidak membuktikan Telegram/Sheets/Gemini readiness.
- Startup schema-check failure dapat ditelan sehingga process terlihat sehat.
- Raw exception dapat keluar melalui diagnostic endpoint; di sisi lain user-facing error belum selalu punya correlation ID untuk support.

## Logging minimum yang aman

Simpan event name, UTC timestamp, Asia/Jakarta display timestamp, update ID, hashed user/action ID, flow, state transition, duration, attempt, worksheet operation, row count, model, token count, outcome, dan normalized error class. Redact secrets, account credentials, raw descriptions, party names, receipt contents, prompt/context, dan monetary details bila tidak wajib.

## CI gate yang disarankan

1. `python -m compileall .` dan lint/import check.
2. Unit/service tests tanpa network.
3. Registered-command versus docs/tester inventory.
4. Callback uniqueness/replay and preview-before-write policy tests.
5. Dependency install from clean environment.
6. Optional owner-approved staging smoke; tidak dijalankan pada setiap PR bila berbiaya atau menulis eksternal.

## Acceptance criteria untuk menutup gap

- Critical paths F-001 sampai F-007 memiliki deterministic regression tests.
- Test suite dilacak Git dan dapat dijalankan dari clean install.
- External calls selalu mocked di unit/CI dan hanya memakai staging pada explicit smoke job.
- Operator dapat menelusuri satu update tanpa melihat data finansial mentah.
- Readiness dan scheduled-job ownership dapat dimonitor.
