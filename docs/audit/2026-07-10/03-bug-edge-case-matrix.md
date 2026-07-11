# Bug and Edge-Case Matrix

Tanggal audit: 2026-07-10  
Mode: read-only terhadap source dan layanan eksternal

Legenda hasil: `PASS` berarti perilaku dibuktikan melalui inspeksi atau eksekusi offline; `FAIL` berarti defect terkonfirmasi; `GAP` berarti belum ada bukti pengujian memadai; `NOT_RUN` berarti perlu kredensial/layanan eksternal atau berpotensi menulis data.

| Area / skenario | Happy path yang diperiksa | Edge case utama | Bukti/cakupan saat audit | Hasil | Severity / finding | Test wajib berikutnya |
|---|---|---|---|---|---|---|
| Expense tunggal | `beli kopi 10k dari Cash` | akun tidak ada/ambigu | Parser offline + routing inspection | PASS/GAP | F-014 | integration preview→confirm→sheet |
| Income tunggal | `gaji 5jt ke BCA` | income tanpa akun | Parser offline | PASS/GAP | F-014 | account clarification dan preview |
| Multi-input | beberapa baris valid | satu baris invalid/ambigu | `message_handlers.py` inspection | FAIL | Medium / F-016 | batch parsial, queue klarifikasi, final preview |
| Transfer | BRI ke DANA | source=target, akun invalid | Parser offline | PASS/GAP | N-002 / F-014 | reject same account dan saldo konsisten |
| Set balance | nominal dan akun eksplisit | teks cocok regex expense | Parser offline menunjukkan safety clarification | PASS/GAP | F-014 | ensure tidak tersimpan sebagai expense/income |
| Amount parsing | `10k`, `100rb`, `331.063k` | nol, negatif, separator campuran | Parser offline | PASS/GAP | F-014 | property-based amount cases |
| Date parsing | tanggal valid | `31/02/2026`, `2026-02-29` | Parser offline | FAIL | High / F-006 | invalid date harus meminta koreksi |
| Account matching | nama akun eksplisit | typo/similar/unknown | Static inspection | GAP | F-014 | exact, alias, similarity, unknown |
| Category matching | kategori existing | alias/similar/new category | Static inspection | GAP | F-014 | existing-vs-new decision dan cancel |
| Parsing safety | debt/transfer/set balance signals | loose keyword collision | Parser offline + route order | PASS/GAP | N-001, F-006 | adversarial intent corpus |
| Gemini parser fallback | regex miss | timeout, malformed JSON, quota | Static inspection only | GAP | F-012, F-013 | mocked timeout/schema/quota/fallback |
| Debt create | pihak, nilai, tipe jelas | pihak/arah ambigu | Static inspection | GAP | F-003, F-014 | preview, save, cashflow consistency |
| Debt payment | `bayar hutang ...` | payment > outstanding | Parser offline + static route | PASS/GAP | N-001, F-003 | rollback across debt+transaction |
| Receivable payment | penerimaan piutang | pihak tidak ditemukan | Static inspection | GAP | F-003 | no partial write on failure |
| Debt settle/void/edit | record valid | stale callback/concurrent edit | Static inspection | GAP | F-001, F-003 | optimistic concurrency/id-bound callback |
| Debt offset | dua posisi dapat dioffset | currency/party mismatch | Static inspection | GAP | F-003 | atomic two-sided update |
| Split equal | anggota dan total valid | pembulatan sisa | Static inspection | GAP | F-014 | deterministic remainder allocation |
| Split nominal | jumlah per anggota | total tidak sama | Static inspection | GAP | F-014 | reject/clarify before preview |
| Split percentage | persentase valid | total bukan 100% | Static inspection | GAP | F-014 | boundary and rounding cases |
| Talangin/ditalangin | arah eksplisit | frasa ambigu seperti makan bareng | Parser offline meminta clarification | PASS/GAP | F-014 | direction and participant matrix |
| Pending payment | mark paid/cancel | command langsung mengubah data | Static inspection | FAIL | High / F-007 | final preview + cancel button |
| Recurring add/run/off/edit | create rule | double click, old button, rule not due | Static inspection | FAIL | Critical / F-004, High / F-007 | idempotency key, due/log assertion |
| Budget | add/edit/check | overlap period/category | Static inspection | GAP | F-014 | boundary dates and overspend |
| Asset | add/update/off | direct write command | Static inspection | FAIL/GAP | High / F-007 | preview and snapshot consistency |
| Net worth | report from assets/accounts | liability compatibility dead | Static inspection | GAP | Low / F-022 | source reconciliation |
| Edit transaction | preview/edit/confirm | callback preview lama | Static inspection | FAIL | Critical / F-001 | callback binds immutable pending id |
| Delete transaction | reverse balance then debt sync | downstream result-style failure | Static inspection | FAIL | Critical / F-003 | injected failure and rollback |
| Image receipt | image→Gemini→preview | any exception causes retry | Static inspection | GAP | F-012, F-013 | call count, timeout, invalid image |
| Search | query/filter | large sheet, invalid date range | Static inspection | GAP | F-009, F-011 | scale fixture and pagination |
| Summary/report/chart | period valid | empty/incomplete data | Static inspection | GAP | F-009, F-011 | numeric truth fixtures |
| Export | export succeeds | concurrent requests same filename | Static inspection | GAP | Medium / F-020 | unique tempfile + cleanup concurrency |
| AI ask/audit/coach | context tersedia | empty data, prompt injection, PII | Static inspection | GAP | F-012 | redaction, grounding, usage capture |
| Scheduler | one process | two workers/process restarts | Static inspection | FAIL/GAP | F-018, F-020 | single-owner lock and timezone matrix |
| Callback/session | callback terbaru | old message clicked after new flow | Static inspection | FAIL | Critical / F-001 | stale/replay/cross-flow callback tests |
| Restart recovery | normal session | restart saat pending preview | Static inspection | GAP | Medium / F-017 | persistence/TTL/restart behavior |
| Sheets retry | transient error before commit | 500 after server-side commit | Offline injected simulation | FAIL | High / F-005 | idempotency/reconciliation test |
| Balance write failure | all writes succeed | balance helper raises after row write | Offline injected simulation | FAIL | Critical / F-002 | transaction must fail/rollback |
| Timezone/DST | Asia/Jakarta host | host TZ berbeda/naive time | Static inspection | GAP | Medium / F-018 | freeze time in UTC/Jakarta |

## Prioritas regression suite

1. Callback harus terikat pada record/pending action immutable dan hanya dapat digunakan sekali.
2. Semua operasi multi-sheet harus gagal atomik pada exception maupun result-style failure.
3. Append yang di-retry harus idempotent atau direkonsiliasi sebelum retry.
4. Semua state-changing command harus berakhir pada preview final dan konfirmasi eksplisit.
5. Invalid date, amount, account, category, dan intent tidak boleh dipaksa menjadi transaksi normal.

## Batas verifikasi

- Tidak ada transaksi sungguhan, callback Telegram, Google Sheets, atau Gemini yang dijalankan.
- Matriks `GAP` tidak menyatakan flow rusak; status itu menyatakan bukti otomatis belum tersedia.
- Perubahan kontrak callback, command, dan schema untuk memperbaiki matriks ini memerlukan persetujuan owner.
