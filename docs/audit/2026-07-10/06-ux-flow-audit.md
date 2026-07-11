# UX and Interaction Flow Audit

Tanggal audit: 2026-07-10

## Prinsip yang digunakan

Audit menilai flow terhadap kontrak repo: intent ambigu harus diklarifikasi, setiap mutasi memiliki preview final, write hanya setelah konfirmasi eksplisit, cancel tersedia sebagai tombol, dan preview harus sama dengan data yang akhirnya disimpan.

## Ringkasan

Flow transaksi dasar telah menunjukkan pola clarification→account/category→preview→confirm, tetapi pola itu belum universal. Sebagian command recurring, pending payment, dan asset melakukan mutasi langsung. Callback generic mengambil state terbaru dari `user_data`, sehingga tombol preview lama tidak selalu menunjuk action yang semula ditampilkan. Masalah ini bukan hanya usability; ini adalah data-integrity risk.

## Flow map

| Flow | Entry | Klarifikasi | Preview final | Batal | State binding | Status |
|---|---|---|---|---|---|---|
| Expense/income single | text/message | amount/account/category bila perlu | Ada | Umumnya ada | generic scope/state | `PARTIAL` — F-001 |
| Multi-input | multiline | sebagian input missing amount di-queue | Ada setelah validasi | Ada pada jalur utama | shared user state | `PARTIAL` — satu invalid line dapat abort batch, F-016 |
| Transfer | text/command | source/target | Ada | Ada | pending state | `PARTIAL` — regression tests tidak ada |
| Set balance | text/command | account/amount | Ada pada flow utama | Ada | pending state | `PARTIAL` — tests tidak ada |
| Debt/receivable create | text/command | type/person/account | Ada pada banyak jalur | Ada | beberapa callback/action state | `PARTIAL` — atomicity F-003 |
| Debt/receivable payment/edit/settle | command/callback | record/account | Bervariasi | Bervariasi | mixed id/state | `RISK` — F-001/F-003 |
| Split bill | text/command | participant/mode | Ada | Ada | pending state | `PARTIAL` — rounding/edge tests tidak ada |
| Pending paid/cancel | command | selector | Tidak selalu ada | Tidak universal | command args/current list | `FAIL` — F-007 |
| Recurring add | command/text | rule fields | Ada pada create flow | Ada | pending state | `PARTIAL` |
| Recurring run/off/edit | callback/command | rule selection | Mutasi langsung pada beberapa jalur | Tidak universal | rule id, tanpa consume/log guard cukup | `FAIL` — F-004/F-007 |
| Asset add | command | fields | Flow preview tersedia | Ada | pending state | `PARTIAL` |
| Asset update/off/snapshot | command/callback | asset selection | Tidak universal | Tidak universal | mixed | `FAIL` — F-007 |
| Category add/edit | command/callback | existing/similar/new | Bervariasi | Ada pada banyak jalur | pending state | `PARTIAL` — similarity contract perlu tests |
| Report/search/export | command | period/filter | Read-only, preview tidak diperlukan | N/A | request-local | `PASS` secara kontrak write |
| AI ask/audit/coach | command/text | prompt/period | Read-only response | N/A | request-local | `PARTIAL` — grounding/redaction F-012 |

## Temuan UX terverifikasi

### Tombol lama dapat mengeksekusi state baru

Keyboard konfirmasi memakai callback seperti `confirm:pending`, sedangkan action detail berada di mutable `context.user_data`. Jika user membuka preview A, memulai flow B, lalu menekan tombol A, handler dapat membaca B. UI mengatakan A tetapi write dapat menjadi B. Solusi minimal adalah callback berisi opaque action ID, server-side immutable preview snapshot/hash, owner, expiry, dan consumed flag.

Perubahan callback format adalah protected contract dan **REQUIRES EXPLICIT OWNER APPROVAL**. Selama migrasi, handler dapat mengenali format lama hanya untuk menolak dengan pesan “preview sudah kedaluwarsa”, bukan menulis data.

### Konfirmasi tidak konsisten

Command untuk menandai/membatalkan pending, menjalankan/mematikan/mengedit recurring, dan sebagian asset action dapat menulis setelah satu command/callback tanpa preview final yang menggambarkan exact mutation. Ini bertentangan dengan kontrak finance safety repo. Menambah preview akan menambah satu langkah tetapi mengurangi accidental writes.

### Batch terlalu mudah gagal total

Multi-input sudah memiliki mekanisme queue untuk sebagian kekurangan, tetapi jalur `failed_lines` dapat menghentikan seluruh batch. UX yang lebih aman: simpan seluruh item sebagai pending, tandai tiap item `ready/needs_clarification/rejected`, selesaikan satu per satu, lalu tampilkan satu final batch preview. Tidak ada write parsial sebelum final confirm.

### State tidak punya lifecycle yang terlihat

`user_data` in-memory tidak memiliki TTL/persistence formal. Restart menghilangkan pending action; preview lama di chat tetap dapat ditekan; user tidak diberi indikator bahwa action expired. Semua terminal path perlu consume/clear state secara konsisten dan tombol lama perlu jawaban aman.

## Copy dan interaction recommendations

- Tampilkan action, nominal, tanggal, akun asal/tujuan, kategori, pihak, serta efek saldo pada preview.
- Gunakan tombol `Simpan`/`Jalankan` yang spesifik, bukan `Ya` generik; selalu pasangkan `Batal`.
- Untuk stale callback: “Preview ini sudah kedaluwarsa. Buat preview baru agar data tetap aman.”
- Untuk invalid date: tunjukkan input salah dan format valid; jangan mengganti diam-diam dengan hari ini.
- Untuk partial batch: tampilkan indeks/baris dan alasan, tanpa membuang item valid.
- Untuk remote write ambiguity: jangan mengatakan gagal lalu mengajak retry sebelum reconciliation; beri correlation ID dan status “perlu dicek”.

## Protected UX contracts

Butuh persetujuan owner sebelum perubahan:

- format callback dan kompatibilitas pesan lama;
- semantics command yang saat ini langsung menulis;
- urutan langkah command publik;
- copy help/start yang menjadi kontrak user-facing;
- behavior bulk partial clarification;
- schema/state persistence yang menyimpan preview/action ID.

## Acceptance criteria UX

1. Setiap mutasi memiliki preview final exact dan tombol Batal.
2. Tombol hanya dapat menjalankan action yang ditampilkan, oleh user yang sama, satu kali, sebelum expiry.
3. Invalid/ambiguous input tidak pernah berubah menjadi nilai default tersembunyi.
4. Batch menyelesaikan klarifikasi per item dan baru menulis setelah final confirmation.
5. Restart, timeout, retry, dan double click menghasilkan pesan aman tanpa duplicate write.
