# Future Architecture Assessment

Tanggal audit: 2026-07-10

## Kesimpulan

Arsitektur sekarang masih masuk akal untuk bot personal dengan satu user, satu process, trafik rendah, dan Google Sheets sebagai data store yang dapat dilihat langsung. Masalah mendesak bukan mengganti seluruh stack, melainkan memperjelas transaction boundary, action identity, idempotency, timeouts, tests, dan module ownership. Migrasi database atau microservices sekarang akan memperluas risiko tanpa lebih dulu memperbaiki kontrak data-safety.

## Current architecture

| Layer | Kondisi | Kekuatan | Batas |
|---|---|---|---|
| Telegram application | PTB handlers, polling/webhook | feature-rich, direct interaction | registrasi/routing tersebar, state in-memory |
| Handlers | beberapa file sangat besar | seluruh behavior tersedia | mixed parsing, presentation, state, orchestration |
| Services | domain modules untuk transaction/debt/etc. | ada pemisahan awal | error contract tidak seragam; import cycle |
| Sheets client | shared Google Sheets access dan atomic wrapper | cocok untuk personal transparency | no true transaction, retry/idempotency hazard |
| Gemini | parsing/intent/insight | fallback untuk natural language | cost, timeout, grounding, privacy belum terukur |
| Scheduler | in-process | sederhana | duplicate ownership saat scale-out |

## Batas kapasitas dan triggers

Jangan memilih migrasi berdasarkan jumlah fitur saja. Instrumentasikan dahulu, lalu gunakan trigger:

- p95 interactive latency melewati SLO akibat full-sheet reads/writes;
- quota/retry Sheets menjadi recurring incident;
- reconciliation/atomic multi-entity write tidak dapat dijamin;
- lebih dari satu user/process diperlukan;
- query/report membutuhkan indexing, pagination, atau historical volume yang Sheets tidak layani;
- scheduler/background jobs perlu durable queue.

## Target evolution yang disarankan

### Tahap A — Stabilkan kontrak dalam arsitektur sekarang

- Immutable pending action dengan ID, owner, hash, expiry, consumed status.
- Satu application-level command/result/error contract.
- Idempotency key dan mutation journal untuk setiap external write.
- Explicit unit-of-work orchestrator yang menganggap `False`/error result sebagai failure.
- Tests, observability, timeout, and single-process invariant.

Ini memberi manfaat data safety tanpa schema rewrite besar. Protected callback/schema changes tetap memerlukan owner approval.

### Tahap B — Modular monolith

Pisahkan per feature menjadi empat boundary konseptual:

1. command/intent parsing dan validation;
2. application use case yang menghasilkan preview/action;
3. domain calculation tanpa Telegram/Sheets;
4. repository/adapters untuk Sheets, Gemini, Telegram, clock, dan scheduler.

Tidak perlu satu package per fungsi. Targetnya dependency direction satu arah dan handler tipis. Pecah hotspot berdasarkan use case, bukan line count semata.

### Tahap C — Persistence abstraction

Definisikan repository contract berdasarkan kebutuhan domain (`save_transaction`, `apply_balance_delta`, `list_period`, `claim_recurring_run`) dan jangan expose worksheet primitives ke handler. Sheets adapter dapat tetap default. Tambahkan contract tests yang sama untuk future database adapter.

### Tahap D — Database/worker hanya ketika trigger terpenuhi

Database relasional memberi transaction, unique constraints, tenant key, indexes, dan migrations. Background queue memberi durable retries/scheduler ownership. Namun migrasi harus mempunyai dual-read/reconciliation plan, data-quality validation, cutover, dan rollback; tidak boleh hanya copy rows.

## Multi-user readiness

Sebelum menerima user kedua:

- authentication/authorization bukan satu global ID;
- setiap action, row, cache, query, report, job, dan log memiliki tenant scope;
- credentials/spreadsheet mapping terisolasi;
- rate/budget quota per tenant;
- cross-tenant negative tests;
- privacy, retention, export, and deletion policy.

Pilihan evolusi paling compatible adalah spreadsheet-per-user di balik repository adapter, kemudian database bila scale/query membutuhkannya. Menambah `user_id` langsung ke setiap existing worksheet adalah breaking schema migration.

## Gemini boundary masa depan

Gemini sebaiknya tidak memutuskan write. Model hanya menghasilkan typed proposal plus confidence/evidence; deterministic validator dan application use case menentukan clarification/preview. Kirim agregat minimum, version prompt/schema, enforce timeouts/token/call budget, dan simpan telemetry tanpa raw financial data.

## Scheduler architecture

Selama satu process, dokumentasikan single owner dan job id. Untuk multi-instance, gunakan claim/lease dengan unique run key (`rule_id + due_at`) atau durable queue. Callback manual run dan scheduler harus melewati use case/idempotency gate yang sama.

## Yang tidak direkomendasikan sekarang

- Microservices untuk setiap finance domain.
- Event sourcing penuh sebelum action IDs dan tests tersedia.
- Vector database hanya untuk `/ask` tanpa retrieval quality evidence.
- Multiple web workers dengan scheduler aktif di semuanya.
- Mengganti Sheets dan framework sekaligus dengan critical bug fixes.
- Membuat public multi-user mode di atas global worksheet/schema sekarang.

## Protected contracts dan migration gates

Owner approval wajib untuk callback format, Google Sheets schema, command semantics, persistence backend, tenant model, Gemini model/prompt output, timezone interpretation, dan deletion/history behavior. Setiap gate membutuhkan backward-compatibility plan, data migration rehearsal, regression suite, observability, dan rollback/reconciliation plan.

## Target success state

- Handler hanya menerjemahkan Telegram update ke use case dan merender result.
- Preview snapshot yang dikonfirmasi identik dengan mutation request.
- Satu mutation dapat dibuktikan exactly-once secara application-level.
- Domain rules dapat diuji tanpa Telegram, Sheets, atau Gemini.
- Sheets tetap dapat digunakan sampai metric menunjukkan alasan migrasi.
- Scale-out/multi-user tidak dimulai sebelum isolation dan job ownership terbukti.
