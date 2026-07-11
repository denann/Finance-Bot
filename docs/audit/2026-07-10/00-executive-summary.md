# Executive Summary

## Kesimpulan umum

Codebase ini kaya fitur dan memiliki niat keselamatan yang kuat: otorisasi Telegram diterapkan pada seluruh entry point publik, transaksi normal memakai preview, parser debt diprioritaskan sebelum expense, schema Sheets dipusatkan, serta ada mekanisme retry dan rollback best-effort. Namun, implementasi keselamatan belum konsisten pada batas terpenting: identitas preview/callback, hasil rollback, dan operasi lintas-sheet.

Audit menemukan **24 finding**: **4 Critical, 5 High, 11 Medium, 3 Low, dan 1 Informational**. Empat finding Critical dapat menghasilkan preview yang tidak sama dengan data tersimpan, laporan sukses palsu setelah rollback, saldo/debt parsial, atau transaksi recurring ganda.

## Kekuatan codebase

- Semua command, message, image, dan callback handler publik yang diperiksa melakukan pemeriksaan `ALLOWED_USER_ID`.
- Jalur utama transaksi normal memisahkan parse, clarification, preview, account selection, dan save.
- Contoh sensitif `bayar hutang Budi 100rb dari BCA` diprioritaskan sebagai debt payment pada alur utama; regex expense yang juga cocok tidak menjadi rute final.
- Schema Sheets terpusat dan schema repair menolak reorder otomatis ketika sheet berisi data dengan header tidak kompatibel.
- Context Gemini memiliki sanitasi credential untuk parser, image caption, dan finance insight.
- Export temporary file dibersihkan dalam `finally`.

## Risiko terbesar

1. **F-001 — stale callback dapat menyimpan payload preview lain.** Callback generik tidak membawa nonce/message binding.
2. **F-002 — save dapat melaporkan sukses setelah balance write gagal dan rollback sudah berjalan.**
3. **F-003 — multi-entity operations dapat keluar normal dengan perubahan parsial.** Status `success=False` tidak memicu rollback wrapper.
4. **F-004 — tombol recurring lama/dobel dapat membuat transaksi lagi.** `mark_recurring_rule_paid` tidak memeriksa due date atau run ledger.
5. **F-005 — retry non-idempotent dapat menduplikasi append.** Simulasi offline membuktikan helper mengulang write bertanda 500.

## Lima prioritas utama

1. Ikat setiap preview ke operation ID/message ID dan konsumsi secara atomik (**F-001, F-004**).
2. Samakan kontrak error/rollback; jangan ubah kegagalan atomic write menjadi `success=True` (**F-002, F-003**).
3. Tambahkan idempotency key/ledger untuk transaksi, recurring run, dan Telegram `update_id` (**F-004, F-005**).
4. Bangun regression suite untuk failure injection lintas-sheet sebelum refactor (**F-014**).
5. Tutup atau lindungi endpoint `/test-sheets`, lalu tambahkan readiness yang benar (**F-008, F-020**).

## Jumlah finding per severity

| Severity | Jumlah | Finding |
| :--- | ---: | :--- |
| Critical | 4 | F-001–F-004 |
| High | 5 | F-005–F-009 |
| Medium | 11 | F-010–F-020 |
| Low | 3 | F-021–F-023 |
| Informational | 1 | F-024 |

## Keterbatasan audit

- Tidak ada credential produksi atau external API yang dipakai; Google Sheets, Telegram, dan Gemini tidak dipanggil.
- Environment lokal tidak cocok dengan manifest: Python 3.14.6 memiliki `python-telegram-bot 21.11.1`, tidak memiliki `pytest`, `gspread`, atau sebagian dependency lain.
- `python -m pytest --collect-only -q` tidak dapat berjalan karena `pytest` tidak terpasang.
- Tester sample bawaan gagal saat import karena stub `gspread` tidak menyediakan `gspread.exceptions`.
- Seluruh 53 file Python berhasil dikompilasi in-memory. Beberapa finding dibuktikan lewat call path deterministik dan simulasi stub, bukan spreadsheet nyata.
- Latency, token, volume request, dan billing aktual tidak tersedia; tidak ada estimasi biaya Gemini yang dibuat.

## Keputusan owner yang diperlukan

- **REQUIRES EXPLICIT OWNER APPROVAL:** perubahan callback data/behavior atau penolakan tombol legacy (**F-001, F-004**).
- **REQUIRES EXPLICIT OWNER APPROVAL:** perubahan flow command publik agar selalu preview-before-write (**F-007**).
- **REQUIRES EXPLICIT OWNER APPROVAL:** proteksi/penghapusan `/test-sheets` dan perubahan output publik endpoint (**F-008**).
- **REQUIRES EXPLICIT OWNER APPROVAL:** penambahan idempotency/user/operation columns pada schema Google Sheets. Alternatif backward-compatible adalah ledger terpisah atau metadata persistent tanpa mengubah kolom lama.

## Rekomendasi phase pertama

Mulai dari **Phase 0 — Stabilization and data integrity** di `10-improvement-roadmap.md`. Jangan memulai structural cleanup atau optimasi Gemini sebelum failure semantics dan idempotency aman.

