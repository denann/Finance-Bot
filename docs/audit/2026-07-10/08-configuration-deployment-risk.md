# Configuration and Deployment Risk

Tanggal audit: 2026-07-10

## Deployment profile yang terverifikasi

- Aplikasi mendukung polling dan webhook, dengan FastAPI route pada mode webhook.
- Authorization utama menggunakan satu `ALLOWED_USER_ID` dan satu Google Spreadsheet.
- Scheduler berada dalam process aplikasi melalui PTB JobQueue/APScheduler.
- Local state conversation berada di memory; tidak ada durable PTB persistence yang teridentifikasi.
- Audit worktree berada pada detached HEAD commit `1f07bd213659dd1fab5699589b3876cd8d213523`.

## Risk register

| Risiko | Kondisi pemicu | Dampak | Severity | Mitigasi minimum | Approval |
|---|---|---|---|---|---|
| Public mutable diagnostic endpoint | webhook server reachable; `/test-sheets` dipanggil | schema mutation, metadata/error disclosure | High / F-008 | remove/disable prod, auth, read-only readiness | route behavior approval |
| False readiness | process alive tetapi Sheets/Gemini/startup schema gagal | traffic masuk ke instance rusak | Medium / F-020 | split liveness/readiness; degraded state | additive fields biasanya compatible |
| Duplicate scheduler | lebih dari satu process/worker | duplicate reminder/report/write | Medium / F-020 | single instance invariant atau distributed lock | deployment decision |
| Lost pending state | restart/deploy saat preview aktif | user action hilang; old chat buttons membingungkan | Medium / F-017 | TTL/persistence + expired callback response | state storage approval |
| Retry duplicate write | ambiguous Sheets response | row/transaksi ganda | High / F-005 | idempotency/reconciliation | schema/contract approval bila key baru |
| Environment drift | unpinned/mixed dependencies | behavior berbeda antar host | Low / F-023 | clean lock/install smoke | owner memilih lock strategy |
| Hidden retry knobs | env tidak ada di examples | unsafe value/behavior tak terlihat | Low / F-023 | typed validation + documented defaults | backward compatible |
| Model drift | docs/env/code memilih model berbeda | output/cost/latency berubah | Medium / F-012/F-023 | explicit required/default model + startup log | model approval |
| Temp export collision | concurrent export predictable path | overwrite/send wrong artifact | Medium / F-020 | unique tempfile per request | compatible |
| Naive timezone | host bukan Asia/Jakarta | wrong date/due/scheduler behavior | Medium / F-018 | aware datetime and explicit TZ | date contract approval |
| Secrets/financial data in logs | raw exceptions/prompts/messages | privacy exposure | Medium / F-012 | structured redaction policy | no behavior break |
| No tenant boundary | public/multi-user expansion | cross-user data exposure | Informational / F-024 | remain single-user; design before expansion | architecture approval |

## Configuration inventory gap

`.env.example` dan `.env.webhook.example` belum menjadi complete schema. Minimal config catalogue perlu menyatakan required/optional, type, safe default, secret classification, accepted range, dan restart requirement untuk:

- Telegram token, allowed user, polling/webhook selector dan webhook secret/path;
- spreadsheet credential/source, spreadsheet ID/name, worksheet assumptions;
- Gemini API key, model, feature enablement, timeout, token/call budgets;
- `SHEETS_MAX_RETRIES` dan `SHEETS_RETRY_BASE_DELAY` dengan numeric bounds;
- timezone dan scheduler enable/ownership;
- log level, environment name, readiness policy, dan temporary/export directory.

Tidak ada secret value yang dibaca atau disalin ke laporan.

## Dependency reproducibility

Manifest mencampur exact dan non-exact pins serta tidak menyediakan lock/hash artifact. Audit interpreter Python 3.14.6 memiliki `python-telegram-bot` 21.11.1, sementara manifest meminta 22.7; `pytest` dan `gspread` tidak tersedia. Ini bukan bukti deployment produksi salah, tetapi membuktikan checkout saja belum cukup untuk mereproduksi environment audit.

Safe target: documented Python range, clean virtual environment, deterministic dependency resolution, import/compile smoke, dan dependency update policy. Jangan memperbarui package bersamaan dengan critical flow fix kecuali diperlukan.

## Polling/webhook dan process ownership

- Polling harus satu consumer untuk token yang sama.
- Webhook harus memverifikasi request/secret dan tidak menjalankan scheduler di setiap web worker.
- Scheduler membutuhkan satu elected owner atau service terpisah sebelum scale-out.
- `/health` sebaiknya murah dan read-only; readiness boleh menguji dependency secara bounded tanpa schema write.
- `/test-sheets` tidak layak menjadi public production route dalam bentuk saat ini.

## Deployment checklist yang belum diformalkan

1. Pastikan commit/branch dan environment name yang akan dirilis.
2. Validasi required config tanpa menampilkan secret.
3. Jalankan tests dan migration/schema compatibility check yang read-only.
4. Pastikan hanya satu polling/scheduler owner.
5. Verifikasi readiness terhadap staging/target dependency.
6. Deploy dengan rollback artifact yang sama versinya.
7. Smoke read-only, lalu owner-approved write canary pada staging.
8. Monitor duplicate writes, retries, scheduler overlap, and Gemini cost.

## Rollback/recovery gap

Rollback code tidak otomatis membatalkan row yang mungkin sudah ditulis akibat ambiguous retry. Runbook perlu membedakan deploy rollback dari data reconciliation. Untuk setiap mutation, simpan action/idempotency ID dan before/after evidence agar operator dapat memperbaiki duplicate atau partial write tanpa menebak.

## Keputusan owner

- Tetap single-process/single-user atau rencanakan scale-out.
- Nonaktifkan atau lindungi `/test-sheets` di produksi.
- Pilih dependency locking dan supported Python version.
- Tetapkan timezone contract dan Gemini model/budget.
- Izinkan schema addition untuk idempotency/audit key atau pilih external action store.
