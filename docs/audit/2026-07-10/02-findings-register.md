# Findings Register

## Urutan prioritas

Finding diurutkan berdasarkan severity, risiko integritas data, dampak pengguna, dependency, lalu effort. Status bukti memakai definisi owner: `CONFIRMED`, `STRONG_INDICATION`, `HYPOTHESIS`, atau `NOT_AN_ISSUE`.

## F-001 — Callback preview tidak terikat ke payload yang ditampilkan

- **Kategori / severity / confidence / status:** Data integrity, callback state / **Critical** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `app/bot/handler_parts/transaction_flow.py` — `save_edit_cancel_keyboard` 938–958; `app/bot/handler_parts/message_handlers.py` — `message_handler` 1731–1772; `app/bot/handler_parts/callback_handler.py` — `callback_handler` 4333–4348.
- **Bukti:** preview A dan B sama-sama memakai `confirm:pending`; hanya payload terakhir berada di `context.user_data["pending_parsed"]`; callback membaca payload terakhir tanpa nonce atau pengecekan `query.message.message_id`.
- **Reproduksi:** kirim transaksi A dan biarkan preview; kirim transaksi B; tekan `Simpan` pada pesan A. Call path deterministik membaca state B.
- **Expected / actual:** Expected tombol A hanya menyimpan A atau ditolak expired; actual tombol A dapat menyimpan B.
- **Dampak:** preview berbeda dengan row/saldo yang tersimpan; risiko salah transaksi.
- **Root cause:** callback contract hanya membawa tipe flow, bukan operation identity; satu slot state dipakai ulang.
- **Rekomendasi minimum:** simpan operation ID dan preview message ID; callback harus compare-and-consume sekali sebelum write.
- **Backward-compatible:** pertahankan prefix callback lama, tetapi bind message ID di server dan tolak tombol yang tidak cocok. **REQUIRES EXPLICIT OWNER APPROVAL** karena perilaku tombol lama berubah.
- **Breaking alternative:** callback `confirm:<scope>:<operation_id>` dan pending store keyed by operation ID. **REQUIRES EXPLICIT OWNER APPROVAL**.
- **Effort / risiko perubahan / dependency:** M / High karena semua callback / prerequisite F-004 dan F-017.
- **Test yang perlu ditambah:** dua preview paralel, old button, double-click, cancel old preview, restart.
- **Acceptance criteria:** tombol hanya dapat mengonsumsi payload yang ditampilkan, sekali; mismatch/expired tidak menulis sheet; callback legacy punya kebijakan eksplisit.

## F-002 — Balance write failure dapat dilaporkan sebagai save sukses

- **Kategori / severity / confidence / status:** Data integrity, error contract / **Critical** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `app/services/transaction_service.py` — `save_transaction` 798–866 dan `save_transactions_batch` 955–1015; `app/sheets/client.py` — `_execute_write` 485–508.
- **Bukti:** `_execute_write` menandai transaction gagal, menjalankan rollback, lalu melempar `SheetsAtomicWriteError`. `save_transaction` menangkap semua exception saat update saldo dan mengembalikan `success=True` plus transaction ID. Simulasi stub menghasilkan `reported_success True` dan `txn_simulated` saat balance write melempar exception.
- **Reproduksi:** inject failure pada `apply_account_deltas` setelah append berhasil; dalam outer `sheets_transaction`, failure write memicu rollback row; service tetap mengembalikan sukses.
- **Expected / actual:** Expected result gagal dan UI tidak mengklaim transaksi tersimpan; actual sukses palsu, state dihapus, dan row dapat sudah di-rollback.
- **Dampak:** pengguna percaya data tersimpan padahal tidak ada, atau balance tidak sinkron.
- **Root cause:** service membedakan "row tersimpan, saldo gagal" berdasarkan posisi try block, bukan metadata rollback/error type.
- **Rekomendasi minimum:** propagasikan atomic-write exception; hanya izinkan partial-success bila dibuktikan row masih ada dan tidak ada rollback.
- **Backward-compatible:** struktur result tetap, tetapi `success=False`, `atomicity_status`, dan pesan aman; output publik lama berubah makna sehingga perlu regression review.
- **Breaking alternative:** typed result/exception tunggal dengan commit state eksplisit.
- **Effort / risiko perubahan / dependency:** S–M / High / harus dikerjakan sebelum F-003 refactor.
- **Test yang perlu ditambah:** failure pada append, saldo cell pertama/kedua, rollback success/failure, batch.
- **Acceptance criteria:** tidak ada path yang mengembalikan sukses setelah transaction rollback/failed; UI sesuai keberadaan row dan saldo aktual.

## F-003 — Result-style failures melewati rollback dan meninggalkan multi-write parsial

- **Kategori / severity / confidence / status:** Data integrity, atomicity / **Critical** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `app/bot/application.py` — `atomic_bot_handler` 95–132; `app/services/transaction_service.py` — `delete_transactions_by_refs` 1699–1815; `app/bot/handler_parts/callback_handler.py` — debt save 3517–3727 dan mixed/debt batch 3927–4191.
- **Bukti:** wrapper rollback hanya aktif bila exception keluar. Delete membalik saldo lebih dulu lalu dapat `return success=False` bila debt sync gagal; debt callback menulis debt lebih dulu dan bila cashflow result gagal hanya menampilkan warning "Debt tersimpan, tapi cashflow gagal".
- **Reproduksi:** buat deletion dengan linked debt lalu stub debt void `success=False`; reverse saldo sudah tertulis, transaction row tetap ada, outer context selesai normal.
- **Expected / actual:** Expected seluruh logical operation commit atau rollback; actual partial state dianggap flow yang selesai.
- **Dampak:** saldo salah, debt/transaction tidak sinkron, manual repair diperlukan.
- **Root cause:** campuran exception dan result dict sebagai failure protocol; operation boundary berada di handler tetapi service menyerap failure.
- **Rekomendasi minimum:** definisikan `AtomicOperationError`; setiap failure setelah mutation harus raise atau eksplisit memanggil rollback dan menghentikan flow.
- **Backward-compatible:** pertahankan service result untuk pre-write validation; post-write failure wajib exception internal yang diterjemahkan di handler.
- **Breaking alternative:** unit-of-work/repository transaction API; schema audit ledger mungkin diperlukan dan **REQUIRES EXPLICIT OWNER APPROVAL**.
- **Effort / risiko perubahan / dependency:** L / Very High / bergantung F-002 dan regression suite F-014.
- **Test yang perlu ditambah:** failure injection pada setiap langkah debt, split, delete, edit, pending-paid, recurring.
- **Acceptance criteria:** matrix failure step menunjukkan invariant row/saldo/debt/payment; tidak ada normal return setelah unhandled partial mutation.

## F-004 — Tombol recurring dapat dipakai ulang dan membuat transaksi ganda

- **Kategori / severity / confidence / status:** Idempotency, recurring / **Critical** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `app/bot/handler_parts/callback_handler.py` — recurring callback 1677–1744; `app/services/recurring_service.py` — `mark_recurring_rule_paid` 966–1019.
- **Bukti:** callback hanya berisi `recurring_paid:<rule_id>`. Service memeriksa keberadaan dan `is_active`, tetapi tidak memastikan `next_run_date <= today`, tidak mencari recurring log, dan tidak mengonsumsi operation token. Rule tetap aktif setelah run.
- **Reproduksi:** tekan tombol reminder yang sama dua kali atau tekan lagi bulan berikutnya sebelum pesan dihapus; kedua call membuat transaction baru dan mengubah saldo.
- **Expected / actual:** Expected satu rule/run_date hanya menghasilkan satu transaction; actual setiap callback menghasilkan transaction selama rule aktif.
- **Dampak:** duplicate expense/income dan saldo salah.
- **Root cause:** tidak ada idempotency key `(rule_id, scheduled_run_date)` dan callback lama tetap valid.
- **Rekomendasi minimum:** validasi due date + unique run ledger sebelum save; consume state/idempotency record atomik.
- **Backward-compatible:** gunakan `recurring_logs` sebagai guard tanpa mengubah schema; old callback yang sudah processed ditolak. **REQUIRES EXPLICIT OWNER APPROVAL** untuk behavior callback.
- **Breaking alternative:** callback membawa run date/operation ID dan schema unique key. **REQUIRES EXPLICIT OWNER APPROVAL**.
- **Effort / risiko perubahan / dependency:** M / High / F-001, F-003, F-005.
- **Test yang perlu ditambah:** double-click, same rule same day, stale month button, process restart, failed log write.
- **Acceptance criteria:** maksimal satu transaction per rule/run; duplicate callback tidak mengubah saldo dan memberi pesan idempotent.

## F-005 — Retry write non-idempotent dapat menggandakan append

- **Kategori / severity / confidence / status:** Google Sheets, idempotency / **High** / High / `STRONG_INDICATION`.
- **Lokasi / symbol / line:** `app/sheets/client.py` — `_call_with_retry` 449–465; `append_row` 941–950; `append_rows` 1005–1017.
- **Bukti:** semua exception bertanda 500/503/429 di-retry, termasuk append. Simulasi offline failure "500 backend error after server-side commit" menghasilkan dua write attempts. Apakah server benar-benar commit sebelum error memerlukan telemetry produksi.
- **Reproduksi:** fault-inject ambiguous HTTP 500 setelah append diterima server; retry mengirim append kedua.
- **Expected / actual:** Expected non-idempotent write tidak diulang tanpa idempotency/reconciliation; actual helper mengulang tanpa lookup ID.
- **Dampak:** duplicate transaction, debt, log, budget, atau asset.
- **Root cause:** retry policy generik berdasarkan string exception.
- **Rekomendasi minimum:** retry reads/idempotent updates; untuk append, pre-generate ID lalu reconcile by ID sebelum retry.
- **Backward-compatible:** tidak mengubah schema karena semua row utama sudah memiliki ID; cek ID setelah ambiguous error.
- **Breaking alternative:** idempotency ledger/unique column. **REQUIRES EXPLICIT OWNER APPROVAL**.
- **Effort / risiko perubahan / dependency:** M / Medium / F-004 dan F-003.
- **Test yang perlu ditambah:** before-commit vs after-commit timeout, append batch partial, quota failure.
- **Acceptance criteria:** ambiguous error tidak menghasilkan dua row dengan logical ID yang sama; retry metrics tersedia.

## F-006 — Tanggal eksplisit invalid diam-diam menjadi hari ini

- **Kategori / severity / confidence / status:** Parser correctness / **High** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `app/nlp/regex_parser.py` — date parsing sekitar 1303–1560; `app/nlp/parse_safety.py` — `assess_parse_safety` sekitar 590; `app/services/transaction_service.py` — default date 328.
- **Bukti:** execution offline: `31/02/2026 beli kopi 20k dari Cash` dan `2026-02-29 ...` menghasilkan date `2026-07-10`, `normal_preview`, risk `low`.
- **Reproduksi:** jalankan `parse_with_regex` lalu `assess_parse_safety` pada input di atas.
- **Expected / actual:** Expected clarification "tanggal invalid"; actual fallback today tanpa warning.
- **Dampak:** laporan periode, budget, dan audit trail salah.
- **Root cause:** date detector menyatukan "tidak ada tanggal" dengan "tanggal ada tetapi invalid".
- **Rekomendasi minimum:** return structured date status (`absent`, `valid`, `invalid`) dan route invalid ke clarification.
- **Backward-compatible:** format input/output tetap; hanya invalid date ditolak. Tidak memerlukan schema change.
- **Breaking alternative:** parser result typed object; tidak diperlukan sekarang.
- **Effort / risiko perubahan / dependency:** S / Low–Medium / parse safety tests.
- **Test yang perlu ditambah:** leap year, day/month inversion, month/year boundary, explicit invalid + relative word.
- **Acceptance criteria:** setiap explicit invalid date tidak pernah berubah menjadi today; valid/absent behavior tetap.

## F-007 — Sejumlah command perubahan data tidak memakai final preview

- **Kategori / severity / confidence / status:** UX safety, protected contract / **High** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `command_handlers.py` — `pending_paid_handler` 2407–2483 dan `pending_cancel_handler` 2486–2535; `health_recurring_export.py` — recurring edit/run/off 1190–1242, 1451–1541; `networth_assets.py` — asset update/off 1797–1958 dan snapshot 2009–; callback recurring 1677–1680.
- **Bukti:** handlers memanggil write service langsung sebelum menampilkan hasil; tidak menyimpan pending preview atau menyediakan Batal.
- **Reproduksi:** panggil command dengan ID valid; write terjadi dalam handler command.
- **Expected / actual:** Expected preview + Simpan/Batal untuk semua write; actual command itu sendiri menjadi aksi final.
- **Dampak:** typo ID/amount langsung mengubah finance state; docs dan AGENTS contract tidak benar.
- **Root cause:** preview policy diterapkan per fitur, bukan middleware/command metadata.
- **Rekomendasi minimum:** inventaris write command dan tambahkan preview state/confirm callback.
- **Backward-compatible:** pertahankan command syntax; tambah satu confirmation step. **REQUIRES EXPLICIT OWNER APPROVAL** karena behavior publik berubah.
- **Breaking alternative:** command `--confirm`/new names; tidak direkomendasikan.
- **Effort / risiko perubahan / dependency:** L / High UX regression / F-001 harus selesai lebih dulu.
- **Test yang perlu ditambah:** setiap write command tidak menulis sebelum confirm; Batal; stale confirm.
- **Acceptance criteria:** seluruh public write entry point melewati final preview yang identik dengan saved payload.

## F-008 — Endpoint `/test-sheets` publik dapat membaca metadata dan memutasi schema

- **Kategori / severity / confidence / status:** Security, deployment / **High** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `main.py` — `test_sheets` 302–343; `app/sheets/client.py` — `ensure_spreadsheet_schema` 846–865.
- **Bukti:** endpoint GET tidak memiliki auth; memanggil schema ensure yang dapat membuat worksheet/header/default rows; mengembalikan spreadsheet title, tab names, schema actions, atau raw exception.
- **Reproduksi:** pada webhook deployment, GET `/test-sheets`; tidak diperlukan Telegram secret.
- **Expected / actual:** Expected diagnostic write hanya internal/authenticated; actual route publik melakukan write/read metadata.
- **Dampak:** information disclosure, schema mutation tak terotorisasi, quota consumption.
- **Root cause:** diagnostic endpoint dicampur dengan production app.
- **Rekomendasi minimum:** disable by default atau lindungi admin secret; pisahkan read-only readiness dari schema repair.
- **Backward-compatible:** feature flag default off dan authenticated legacy route. **REQUIRES EXPLICIT OWNER APPROVAL** untuk endpoint behavior.
- **Breaking alternative:** hapus route dan gunakan CLI setup check. **REQUIRES EXPLICIT OWNER APPROVAL**.
- **Effort / risiko perubahan / dependency:** S / Low / F-020 readiness.
- **Test yang perlu ditambah:** unauthorized 403/404, readiness no-write, error redaction.
- **Acceptance criteria:** anonymous request tidak memperoleh metadata dan tidak memicu Sheets write.

## F-009 — Blocking I/O dan backoff menahan event loop

- **Kategori / severity / confidence / status:** Performance, latency / **High** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `app/sheets/client.py` — sync gspread calls dan `time.sleep` 449–465; `gemini_langchain_client.py` — `llm.invoke` 127–129 dan 184–205; seluruh async handlers memanggilnya langsung.
- **Bukti:** synchronous network/read/write dan exponential sleep dieksekusi di coroutine handler tanpa `to_thread`/async client.
- **Reproduksi:** fault-inject 5 retry dengan base 1 detik; event loop tidak dapat memproses callback/reply lain selama sleep/call.
- **Expected / actual:** Expected external I/O tidak memblok event loop; actual satu slow Sheets/Gemini call menahan bot.
- **Dampak:** callback timeout, webhook retry, duplicate action risk, UX lambat.
- **Root cause:** sync clients ditempatkan langsung di async layer.
- **Rekomendasi minimum:** ukur dulu; bungkus blocking boundary terkontrol dengan timeout dan bounded executor.
- **Backward-compatible:** interface service tetap sinkron internal, adapter async di handler boundary.
- **Breaking alternative:** async repository/client menyeluruh; belum dibutuhkan sekarang.
- **Effort / risiko perubahan / dependency:** M / Medium / instrumentation F-012 lebih dulu.
- **Test yang perlu ditambah:** event-loop responsiveness, timeout, concurrent callback, retry duration.
- **Acceptance criteria:** slow external call tidak memblok health/cancel update; timeout dan latency metric tercatat.

## F-010 — Setiap save menulis ulang seluruh transaction sheet untuk sorting

- **Kategori / severity / confidence / status:** Performance, concurrency / **Medium** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `transaction_service.py` — save calls 800–801 dan 957–958; `sort_transactions_sheet_by_date` 1085–1134.
- **Bukti:** setelah append, code membaca `get_all_values`, sorts semua rows, lalu `sheet.update` seluruh `A2:...`; call ini tidak memakai retry/rollback wrapper dan result-nya diabaikan.
- **Reproduksi:** save satu transaction pada sheet N rows; operasi read/write tetap O(N).
- **Expected / actual:** Expected append kecil tidak memerlukan full rewrite; actual full-sheet round trip setiap save.
- **Dampak:** latency dan quota tumbuh linear; concurrent writer dapat menghasilkan urutan/stale rewrite.
- **Root cause:** physical row order dijadikan presentation order.
- **Rekomendasi minimum:** berhenti sort-on-write; sort in-memory pada read/report.
- **Backward-compatible:** output report tetap newest-first; physical sheet order berubah sehingga **REQUIRES EXPLICIT OWNER APPROVAL** sebagai protected visible behavior bila owner bergantung pada urutan sheet.
- **Breaking alternative:** database/index; belum diperlukan.
- **Effort / risiko perubahan / dependency:** S–M / Medium / report regression tests.
- **Test yang perlu ditambah:** append without sort, `/last` ordering, concurrent append, malformed date.
- **Acceptance criteria:** satu save tidak full-sheet rewrite; semua user-facing ordering tetap benar.

## F-011 — AI context melakukan repeated full-sheet reads

- **Kategori / severity / confidence / status:** Performance, Gemini latency / **Medium** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `finance_insight_service.py` — `get_month_transactions` 465–483, monthly context 1243–1281, relevant search 1327–1372, ask context 1405–1427.
- **Bukti:** monthly context membaca transactions untuk bulan kini dan sebelumnya, budgets, accounts, debts, assets; enrichment mengulang debt reads; `/ask` kembali membaca seluruh transactions untuk relevant search dan accounts lagi lewat net worth.
- **Reproduksi:** trace `build_ask_finance_context`; hitung `get_all_records` calls per sheet.
- **Expected / actual:** Expected satu request memakai snapshot/read set bersama; actual helper masing-masing membaca full sheet.
- **Dampak:** latency, quota, dan inconsistent snapshot antar-read.
- **Root cause:** composable helpers tidak menerima prefetched data/repository snapshot.
- **Rekomendasi minimum:** request-scoped snapshot/cache dengan TTL nol di luar request; pass records ke helpers.
- **Backward-compatible:** output/context schema tetap.
- **Breaking alternative:** database query layer; hanya sebelum scale.
- **Effort / risiko perubahan / dependency:** M / Medium / F-012 instrumentation.
- **Test yang perlu ditambah:** call-count assertions dan same-snapshot consistency.
- **Acceptance criteria:** call budget per command terdokumentasi dan `/ask` tidak membaca sheet yang sama berulang tanpa alasan.

## F-012 — Gemini tidak memiliki timeout, output cap, atau usage observability

- **Kategori / severity / confidence / status:** Gemini cost, observability, privacy / **Medium** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `gemini_langchain_client.py` 53–75 dan 104–129; `gemini_finance_insight.py` 136–181; `gemini_intent_router.py` 266–293.
- **Bukti:** client hanya mengatur model/key/temperature. Tidak ada timeout, max output tokens, token usage, model/latency/prompt-version logging, correlation ID, atau structured output schema native. Intent prompt memasukkan raw user text tanpa privacy redaction.
- **Reproduksi:** inspect constructor/invoke and logging search; tidak ada field terkait.
- **Expected / actual:** Expected bounded call dan telemetry biaya; actual call duration/output/cost tidak terukur.
- **Dampak:** handler dapat menggantung, biaya tidak dapat dihitung, prompt regression sulit dilacak; prompt injection hanya dibatasi oleh allow-list downstream.
- **Root cause:** wrapper hanya menyatukan invocation, belum menjadi governance boundary.
- **Rekomendasi minimum:** timeout, output cap, sanitized metadata log, prompt version, model, latency, token usage bila API menyediakan.
- **Backward-compatible:** tidak log prompt/finance payload mentah; output publik tetap.
- **Breaking alternative:** provider abstraction/model router; opsional setelah metrics.
- **Effort / risiko perubahan / dependency:** M / Low–Medium / F-013 optimization.
- **Test yang perlu ditambah:** timeout, oversized output, malformed JSON, prompt injection, redaction, telemetry fields.
- **Acceptance criteria:** setiap call bounded dan menghasilkan metric tanpa secret/data payload; biaya dapat dihitung dari usage + volume.

## F-013 — Fallback Gemini dapat berantai dan membesar per item

- **Kategori / severity / confidence / status:** Gemini cost, latency / **Medium** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `transaction_flow.py` — `parse_input` 19–43 dan `parse_mixed_item` 825–871; `message_handlers.py` 1668–1688; `gemini_langchain_client.py` image fallback 193–209.
- **Bukti:** regex miss memanggil Gemini parser; jika hasil pending, flow dapat memanggil Gemini intent router lagi. Multi-input memanggil `parse_input` untuk setiap line tanpa call budget. Image wrapper mengulang model dengan payload alternatif pada setiap exception.
- **Reproduksi:** input command-like yang gagal parser dapat menghasilkan dua model calls; N baris tidak terparse dapat menghasilkan N calls; image invocation failure menghasilkan call kedua.
- **Expected / actual:** Expected satu routed model call sesuai task atau budget eksplisit; actual chained/per-item calls.
- **Dampak:** latency dan biaya tak terkendali pada message Telegram panjang.
- **Root cause:** fallback lokal tidak berbagi decision/call budget dan image retry tidak mengklasifikasi error.
- **Rekomendasi minimum:** request-scoped AI call budget, route intent sebelum transaction Gemini untuk command-like input, batch parse atau fail-fast per multi-input, retry hanya compatibility error yang teridentifikasi.
- **Backward-compatible:** flow/output sama, hanya routing/call count berubah.
- **Breaking alternative:** satu structured router universal; tidak direkomendasikan karena memperbesar blast radius.
- **Effort / risiko perubahan / dependency:** M / Medium / F-012 metrics dahulu.
- **Test yang perlu ditambah:** exact model call counts per path, multi-input max, image auth/quota/format error.
- **Acceptance criteria:** maksimum calls per request terdokumentasi dan diuji; error non-retryable tidak memanggil model dua kali.

## F-014 — Regression suite formal tidak tersedia dan tester offline rusak

- **Kategori / severity / confidence / status:** Testing / **Medium** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `.gitignore` line 10 `tests/`; `scripts/ai_command_tester.py` stubs 182–351 dan CLI 1799–1810; tidak ada pytest config/test tracked.
- **Bukti:** `pytest` tidak terpasang; no tracked tests; sample tester gagal `No module named 'gspread.exceptions'; 'gspread' is not a package`. Script setup/debug dapat mengakses Sheets dan schema ensure.
- **Reproduksi:** `python scripts/ai_command_tester.py --sample` pada dependency-minimal environment.
- **Expected / actual:** Expected offline suite runnable tanpa production credential; actual import gagal sebelum cases.
- **Dampak:** perubahan pada finance flow tidak punya safety net; finding Critical sulit diperbaiki aman.
- **Root cause:** diagnostic script menggantikan unit/integration suite dan optional import stubs tidak mengikuti package structure.
- **Rekomendasi minimum:** unignore tracked tests, pytest unit suite dengan in-memory fake Sheets dan failure injection; perbaiki tester stub.
- **Backward-compatible:** tidak mengubah runtime/protected contract.
- **Breaking alternative:** tidak ada.
- **Effort / risiko perubahan / dependency:** M–L / Low / prerequisite Phase 0 changes.
- **Test yang perlu ditambah:** callback binding, atomic writes, retry, debt invariants, dates, recurring idempotency, command registry/help parity.
- **Acceptance criteria:** suite offline berjalan tanpa credential; critical flow matrix memiliki assertions; CI menjalankan suite.

## F-015 — Handler god-functions, wildcard imports, dan dependency cycle memperbesar blast radius

- **Kategori / severity / confidence / status:** Architecture, maintainability / **Medium** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `callback_handler.py` `callback_handler` 901–4461; `handlers.py` 5–21; semua handler parts import `common_imports.*`; `common_imports.py` 1–1305; cycle `transaction_service`/`debt_service`.
- **Bukti:** AST mengukur callback 3.561 baris; `common_imports` punya out-degree 17; wildcard re-export dan duplikasi helper membuat symbol ownership kabur.
- **Reproduksi:** AST function span/import graph yang dicatat di verification log.
- **Expected / actual:** Expected routing tipis dan business operation terisolasi; actual routing, preview, state, writes, formatting berada di fungsi sama.
- **Dampak:** review dan test sulit; perubahan satu flow berisiko memengaruhi flow lain.
- **Root cause:** pertumbuhan incremental melalui shared import facade dan callback monolith.
- **Rekomendasi minimum:** setelah Phase 0, ekstrak callback per bounded context dengan explicit imports; jangan refactor behavior bersamaan.
- **Backward-compatible:** facade `handlers.py` dan callback prefixes dipertahankan.
- **Breaking alternative:** rewrite state machine/framework; tidak dibutuhkan sekarang.
- **Effort / risiko perubahan / dependency:** XL / High / F-014 regression suite wajib.
- **Test yang perlu ditambah:** handler registry snapshot dan behavior tests sebelum/after extraction.
- **Acceptance criteria:** tidak ada wildcard baru; callback dispatcher kecil; modules punya ownership jelas tanpa cycle.

## F-016 — Bulk input masih menolak seluruh batch jika satu line gagal dipahami

- **Kategori / severity / confidence / status:** UX, bulk safety / **Medium** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `message_handlers.py` — multi-input loop 1554–1594.
- **Bukti:** setiap `failed` line dikumpulkan; bila `failed_lines` non-empty handler langsung reply dan return sebelum menyimpan queue item valid. Missing amount sudah di-queue per item, tetapi parse failure belum.
- **Reproduksi:** satu message berisi satu transaction valid dan satu line tidak dikenal.
- **Expected / actual:** Expected valid items tetap dipertahankan dan failed item diklarifikasi satu per satu sebelum final preview; actual seluruh batch dihentikan.
- **Dampak:** user harus mengulang item valid dan berisiko duplicate input manual.
- **Root cause:** dua failure mode (`missing_amount` vs `failed`) punya state strategy berbeda.
- **Rekomendasi minimum:** simpan mixed queue termasuk unresolved items, klarifikasi per item, lalu final preview.
- **Backward-compatible:** syntax dan callback contract tetap, tetapi perlu operation binding F-001.
- **Breaking alternative:** format batch baru; tidak diperlukan.
- **Effort / risiko perubahan / dependency:** M / Medium / F-001, F-014.
- **Test yang perlu ditambah:** valid+failed, multiple failed, cancel during clarification, final preview accuracy.
- **Acceptance criteria:** satu bad item tidak membuang parsed items valid; tidak ada write sebelum semua keputusan selesai.

## F-017 — Pending state tidak persistent dan tidak memiliki TTL

- **Kategori / severity / confidence / status:** State management, UX / **Medium** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `application.py` 362–370 builds Application tanpa persistence; `state_utils.py` 17–61; tidak ada timestamp/TTL check pada confirm paths.
- **Bukti:** seluruh state berada di `context.user_data` in-memory; restart menghapus pending dan `last_*_map`; selama proses hidup state dapat bertahan tanpa expiration.
- **Reproduksi:** restart di tengah preview; tombol memberi expired. Tanpa restart, biarkan wizard lama lalu gunakan callback generic setelah state berubah (terkait F-001).
- **Expected / actual:** Expected policy expiry deterministik dan recovery; actual lifecycle bergantung proses/command berikutnya.
- **Dampak:** user terjebak/kehilangan context; old keyboard tetap terlihat; numbered references hilang.
- **Root cause:** tidak ada persistence/TTL metadata.
- **Rekomendasi minimum:** TTL + message binding; persistence hanya untuk state yang memang aman direcover, bukan payload write tanpa revalidation.
- **Backward-compatible:** pesan expired tetap, tetapi lebih deterministik.
- **Breaking alternative:** durable workflow store; sebelum public/multi-instance saja.
- **Effort / risiko perubahan / dependency:** M / Medium / F-001.
- **Test yang perlu ditambah:** restart, TTL boundary, old button, last-map invalidation.
- **Acceptance criteria:** setiap pending flow punya creation/expiry policy; recovery/rejection tidak pernah menulis payload stale.

## F-018 — Business date memakai timezone proses, bukan Asia/Jakarta eksplisit

- **Kategori / severity / confidence / status:** Date/time correctness / **Medium** / Medium / `STRONG_INDICATION`.
- **Lokasi / symbol / line:** banyak `datetime.now()` di transaction, debt, budget, recurring, pending, report, Gemini prompts; hanya scheduler di `jobs.py` 445 dan export JobQueue `application.py` 352 yang memakai Jakarta.
- **Bukti:** grep menemukan puluhan naive `datetime.now()`; deployment timezone tidak ditetapkan dalam config/docs. Salah tanggal memerlukan host non-Jakarta dan boundary waktu.
- **Reproduksi:** jalankan host UTC pada 00:30 WIB; local date masih hari sebelumnya.
- **Expected / actual:** Expected semua finance date berbasis Asia/Jakarta; actual berbasis OS process timezone.
- **Dampak:** transaction date, due recurring, budget month, report period dapat bergeser.
- **Root cause:** timezone hanya diterapkan pada schedule trigger.
- **Rekomendasi minimum:** satu clock provider `ZoneInfo("Asia/Jakarta")`, injectable untuk test.
- **Backward-compatible:** stored format tetap `YYYY-MM-DD`; behavior boundary dikoreksi.
- **Breaking alternative:** timezone-aware timestamps/schema; **REQUIRES EXPLICIT OWNER APPROVAL** bila kolom berubah.
- **Effort / risiko perubahan / dependency:** M / Medium / date regression tests.
- **Test yang perlu ditambah:** WIB midnight/month/year/leap boundary.
- **Acceptance criteria:** semua default finance dates dan prompts memakai clock Jakarta yang sama.

## F-019 — Dokumentasi mengklaim safety yang tidak diimplementasikan

- **Kategori / severity / confidence / status:** Documentation drift / **Medium** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `README.md` features/system flow; `docs/help_manual.md` line 5; `docs/09-function-reference.md` duplicate `app/app/...`; `docs/08-setup-debug-deployment.md` setup checks.
- **Bukti:** manual menyatakan semua flow write memakai preview, bertentangan F-007; function reference punya section duplikat dan path non-existent; "check" schema dapat menulis; deployment Wispbyte tidak punya config artifact.
- **Reproduksi:** compare docs dengan handler registry/write call paths.
- **Expected / actual:** Expected docs menyatakan behavior aktual dan limitations; actual beberapa klaim absolut misleading.
- **Dampak:** owner/user salah menilai safety dan operator dapat menjalankan write saat mengira read-only check.
- **Root cause:** docs generated/updated tanpa executable parity checks.
- **Rekomendasi minimum:** setelah behavior decision, koreksi klaim per command dan regenerate function reference dari satu source.
- **Backward-compatible:** dokumentasi saja pada Phase 4; jangan mendokumentasikan target sebelum implementasi.
- **Breaking alternative:** tidak ada.
- **Effort / risiko perubahan / dependency:** M / Low / F-007 owner decision.
- **Test yang perlu ditambah:** command/help registry parity dan docs link/path check.
- **Acceptance criteria:** setiap doc mendapat status CURRENT; tidak ada path/symbol palsu atau klaim preview yang salah.

## F-020 — Readiness dan single-instance operational contract tidak dapat dibuktikan

- **Kategori / severity / confidence / status:** Operations, deployment / **Medium** / Medium / `STRONG_INDICATION`.
- **Lokasi / symbol / line:** `main.py` schema startup 106–132, health 282–299, global scheduler 51–58; `application.py` JobQueue 349–357; export temp path 1679–1714/1763–1806.
- **Bukti:** schema error hanya diprint lalu startup lanjut; `/health` selalu `ok`; dua scheduler start per process; tidak ada leader/single-instance guard; export memakai filename prediktif per period. Deployment artifact/CI/health policy tidak tersedia.
- **Reproduksi:** schema failure tetap menghasilkan health ok; multi-worker/multi-replica dapat mendaftarkan job per process; concurrent export target file sama.
- **Expected / actual:** Expected readiness mencerminkan dependency dan job ownership tunggal; actual liveness saja.
- **Dampak:** bot terlihat sehat ketika Sheets unusable; duplicate scheduled messages; export collision.
- **Root cause:** local single-process assumptions tidak diformalkan.
- **Rekomendasi minimum:** separate liveness/readiness, startup degraded state, documented single-instance constraint, unique temp file.
- **Backward-compatible:** health response dapat menambah fields; perubahan status/route **REQUIRES EXPLICIT OWNER APPROVAL** bila consumer bergantung.
- **Breaking alternative:** distributed lock/queue; hanya setelah multi-instance dibutuhkan.
- **Effort / risiko perubahan / dependency:** M / Medium / F-008.
- **Test yang perlu ditambah:** dependency-down readiness, duplicate scheduler startup, concurrent export.
- **Acceptance criteria:** operator dapat membedakan alive/ready; satu scheduler owner; temp files unik dan selalu dibersihkan.

## F-021 — Utility dan formatting logic diduplikasi

- **Kategori / severity / confidence / status:** Duplication / **Low** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `scripts/ai_command_tester.py` dan `app/scripts/ai_command_tester.py` berbeda hanya 2 insertions/2 deletions; `format_rupiah` ada di tujuh modul; safe reply helpers diduplikasi di `common_imports.py` dan `core.py`.
- **Bukti:** `git diff --no-index --numstat` menunjukkan tester hampir identik; AST duplicate-name inventory mengonfirmasi helper berulang.
- **Reproduksi:** compare files/functions.
- **Expected / actual:** Expected satu canonical utility; actual copy mudah drift.
- **Dampak:** bug fix dan format output dapat berbeda antar flow.
- **Root cause:** compatibility copies dan wildcard shared module.
- **Rekomendasi minimum:** tentukan canonical tester/formatter dan re-export tipis; lakukan setelah tests.
- **Backward-compatible:** pertahankan CLI path wrapper dan output format.
- **Breaking alternative:** hapus salah satu CLI path tanpa wrapper; tidak direkomendasikan.
- **Effort / risiko perubahan / dependency:** S–M / Medium / F-014.
- **Test yang perlu ditambah:** formatter golden cases dan both CLI entry points.
- **Acceptance criteria:** satu implementation per rule; compatibility path tidak menduplikasi logic.

## F-022 — Liability compatibility layer mati tetapi masih tersebar

- **Kategori / severity / confidence / status:** Dead code, documentation/test drift / **Low** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `net_worth_service.py` 68–71, `add_liability` 569–594, `get_liabilities` 647–662; `networth_assets.py` liability handlers; `application.py` tidak mendaftarkan command; tester `KNOWN_SLASH_COMMANDS` 388–394 masih memasukkannya.
- **Bukti:** service selalu raise/return empty, handlers unreachable, tester menganggap command known.
- **Reproduksi:** compare handler registry dengan symbols/tester list.
- **Expected / actual:** Expected removed feature punya satu tombstone yang jelas; actual dead implementation membebani audit dan tester.
- **Dampak:** maintainability dan false test confidence.
- **Root cause:** removal tidak menyelesaikan compatibility cleanup.
- **Rekomendasi minimum:** tentukan owner decision: hapus dead path atau restore feature; default audit menyarankan hapus bertahap karena message menyatakan removed.
- **Backward-compatible:** keep explicit unknown/help notice bila command pernah publik. **REQUIRES EXPLICIT OWNER APPROVAL** bila command contract pernah digunakan.
- **Breaking alternative:** delete handlers/services langsung.
- **Effort / risiko perubahan / dependency:** S–M / Low–Medium / registry tests.
- **Test yang perlu ditambah:** registered command inventory dan unavailable-command response.
- **Acceptance criteria:** tester, docs, registry, dan code sepakat liability aktif atau removed.

## F-023 — Configuration dan dependency surface tidak sepenuhnya reproducible

- **Kategori / severity / confidence / status:** Configuration, dependency hygiene / **Low** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `requirements.txt`; `.env.example`; `.env.webhook.example`; `app/sheets/client.py` 449–450; Gemini default constants.
- **Bukti:** retry env `SHEETS_MAX_RETRIES`/`SHEETS_RETRY_BASE_DELAY` tidak dicontohkan; docs/examples memakai Gemini 3.1 sementara code fallback 2.5; dependency pinning campuran tanpa lock/hash; audit environment memiliki PTB 21.11.1 versus manifest 22.7.
- **Reproduksi:** compare env lookups/docs/manifest dan local package metadata.
- **Expected / actual:** Expected seluruh public config terdokumentasi dan environment reproducible; actual hidden knobs/default drift.
- **Dampak:** behavior antar host berbeda dan debugging lebih sulit.
- **Root cause:** tidak ada config schema/lock workflow.
- **Rekomendasi minimum:** dokumentasikan semua env dengan safe defaults, validasi numeric retry config, pilih lock strategy.
- **Backward-compatible:** env names lama dipertahankan.
- **Breaking alternative:** typed settings package/new env names; tidak diperlukan sekarang.
- **Effort / risiko perubahan / dependency:** S / Low / Phase 4 docs.
- **Test yang perlu ditambah:** config parsing/default tests dan manifest smoke environment.
- **Acceptance criteria:** clean install memakai versi yang diharapkan; setiap env lookup ada di example/docs tanpa secret.

## F-024 — Arsitektur saat ini sengaja single-user dan belum punya tenant boundary

- **Kategori / severity / confidence / status:** Future readiness / **Informational** / High / `CONFIRMED`.
- **Lokasi / symbol / line:** `app/config.py` `ALLOWED_USER_ID` 50–56; `SHEET_SCHEMAS` tidak memiliki `user_id`; semua services membaca shared sheet.
- **Bukti:** satu allowed user, satu spreadsheet, global worksheet caches, schema tanpa tenant key.
- **Reproduksi:** system map/schema inspection.
- **Expected / actual:** Untuk personal bot, actual sesuai scope; untuk multi-user/public deployment, isolasi tidak ada.
- **Dampak:** bukan bug sekarang; blocker sebelum multi-user.
- **Root cause:** produk didesain personal-use.
- **Rekomendasi minimum:** jangan overengineer sekarang; dokumentasikan invariant single-user. Sebelum multi-user, tambahkan tenant boundary, authorization policy, migration, audit trail.
- **Backward-compatible:** spreadsheet-per-user adapter dapat menjaga schema lama.
- **Breaking alternative:** tambah `user_id` pada semua sheets/database migration. **REQUIRES EXPLICIT OWNER APPROVAL**.
- **Effort / risiko perubahan / dependency:** XL / Very High / setelah Phase 0–4.
- **Test yang perlu ditambah:** tenant isolation hanya ketika scope diperluas.
- **Acceptance criteria:** sebelum multi-user, setiap read/write scoped dan cross-user tests lulus; sampai saat itu deployment tetap single-user/single-instance terdokumentasi.

## Kandidat yang diperiksa dan bukan isu

- **N-001 (`NOT_AN_ISSUE`):** `bayar hutang Budi 100rb dari BCA` memang juga cocok regex expense, tetapi `message_handler` menjalankan `parse_debt_input` lebih awal dan mengarahkannya ke debt payment.
- **N-002 (`NOT_AN_ISSUE`):** transfer eksplisit `transfer 200k dari BRI ke DANA` diparse sebagai transfer dengan source/target berbeda pada execution offline.
- **N-003 (`NOT_AN_ISSUE`):** export manual/scheduled memiliki cleanup `finally`; risiko tersisa adalah filename collision di F-020, bukan file leak normal.

