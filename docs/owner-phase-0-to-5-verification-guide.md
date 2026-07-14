# Owner Guide: Cara Mengecek Hasil Phase 0-5 dan Mengevaluasi Performa

Dokumen ini dibuat untuk owner project. Tujuannya sederhana: kamu punya satu tempat untuk mengecek apakah hasil Phase 0 sampai Phase 5 masih aman, bagaimana membaca hasilnya, dan kapan perlu melakukan evaluasi performa lebih lanjut.

Gunakan panduan ini dari root repo:

```powershell
cd "C:\Users\Administrator\.codex\worktrees\75ad\Chatbot Pengeluaran Pemasukan"
```

## Ringkasan Cepat

Kalau kamu hanya mau cek kondisi umum, jalankan ini:

```powershell
python -m pytest -q
python scripts\check_docs.py
python -m compileall -q app evals tests scripts
git diff --check
git status --short
```

Hasil yang sehat:

- pytest: semua test `passed`, tidak ada `failed`;
- documentation check: `Documentation checks passed.`;
- compileall: tidak ada output error;
- diff check: tidak ada whitespace error;
- git status: hanya file perubahan yang memang kamu expect.

Catatan: jumlah test bisa naik dari waktu ke waktu. Jangan anggap angka test sebagai angka permanen. Yang penting adalah `0 failed`.

## Step 1 - Cek Worktree Sebelum Menilai Hasil

Tujuannya untuk tahu file apa saja yang sedang berubah.

```powershell
git status --short
git diff --stat
```

Cara membaca:

- `M` berarti file modified.
- `??` berarti file baru belum tracked.
- Kalau ada file yang tidak kamu kenal, cek dulu sebelum commit.
- Jangan jalankan `git reset --hard`, `git clean`, atau restore massal kalau belum yakin.

Untuk melihat isi perubahan:

```powershell
git diff
```

Kalau output terlalu panjang, pakai Git GUI lebih enak.

## Step 2 - Cek Semua Test Offline

Ini pengecekan paling penting untuk Phase 0-5.

```powershell
python -m pytest -q
```

Yang dicek:

- Phase 0: confirmation, rollback, idempotency, stale callback, invalid date.
- Phase 1: regression suite, external-call guard, observability.
- Phase 2: boundary module, callback routing, parser hardening.
- Phase 3: Gemini governance, batch parser, worker boundaries.
- Phase 4: documentation drift tests.
- Phase 5: scale decision contracts.

Hasil yang sehat:

```text
... passed
0 failed
```

Kalau ada warning `.pytest_cache`, itu biasanya bukan kegagalan aplikasi. Yang penting tidak ada `failed`.

## Step 3 - Cek Regression Suite Saja

Kalau kamu baru mengubah parsing, flow transaksi, split bill, debt, tanggal, atau preview, jalankan ini:

```powershell
python -m pytest -q tests\regression
```

Yang dicek:

- input transaksi normal;
- transfer;
- debt dan piutang;
- split bill;
- tanggal invalid;
- future intent;
- cancellation;
- multi-input;
- preview dan scenario confirmation.

Kalau regression suite gagal, jangan langsung ubah expected value. Cek dulu apakah behavior yang gagal memang bug atau perubahan produk yang kamu setujui.

## Step 4 - Cek Dokumentasi Tidak Drift

Jalankan:

```powershell
python scripts\check_docs.py
```

Yang dicek:

- link Markdown tidak rusak;
- README docs memuat dokumen utama;
- command registry selaras dengan help/manual;
- `.env.example` selaras dengan environment variable di code;
- schema Google Sheets di docs selaras dengan source;
- historical docs dilabeli sebagai historical;
- tidak ada pola credential di dokumentasi.

Kalau gagal, output biasanya menunjukkan file dan alasan. Perbaiki file yang disebut, lalu ulangi command.

## Step 5 - Cek Compile / Import Dasar

Jalankan:

```powershell
python -m compileall -q app evals tests scripts
```

Hasil sehat: tidak ada output error.

Command ini tidak membuktikan business logic benar, tapi membantu menangkap syntax/import error sebelum run bot.

## Step 6 - Cek Whitespace dan Status Git

Jalankan:

```powershell
git diff --check
git status --short
```

Hasil sehat:

- `git diff --check` tidak menampilkan whitespace error;
- `git status --short` hanya menampilkan perubahan yang kamu memang mau review/commit.

Line-ending warning seperti `LF will be replaced by CRLF` di Windows biasanya bukan kegagalan.

## Step 7 - Cek Log File Otomatis

Sekarang aplikasi otomatis append structured log ke:

```text
logs/finance_bot.log
```

Cek apakah file log dibuat:

```powershell
Get-ChildItem logs
Get-Content logs\finance_bot.log -Tail 20
```

Yang sehat:

- log berupa JSON per baris;
- ada `correlation_id`;
- tidak ada raw token, API key, private key, prompt mentah, atau teks finansial pribadi yang sensitif.

Untuk melihatnya sebagai tabel rapi, bukan JSON mentah:

```powershell
python scripts/view_logs.py
python scripts/view_logs.py --summary
python scripts/view_logs.py --errors-only
python scripts/view_logs.py --transaction-id txn_your_transaction_id
```

Untuk membuka semua hasil di Excel sebagai tabel, buat CSV:

```powershell
python scripts/view_logs.py --csv logs/finance_bot_readable.csv
```

File CSV tersebut hanya dibuat dari log lokal. Jangan ikut membagikannya jika
berisi metadata operasional yang tidak ingin Anda sebarkan.

Secara default, log transaksi menyimpan `transaction_id` tetapi menyensor input
asli. Untuk debugging pribadi saja, tambahkan `LOG_INCLUDE_FINANCE_DATA=true`
ke `.env`, restart bot, lalu jangan bagikan file log atau CSV-nya.

Cek `logs/` tidak ikut Git:

```powershell
git check-ignore logs\finance_bot.log
```

Hasil sehat:

```text
logs\finance_bot.log
```

Kalau ingin matikan file logging sementara:

```env
LOG_FILE=
```

## Step 8 - Cek Phase 0-5 Summary

Baca ringkasan utama:

```text
docs/phase-0-to-5/README.md
```

Gunakan file itu untuk melihat:

- apa masalah awal tiap phase;
- implementasi utama;
- efek ke user;
- efek ke backend;
- area code penting;
- limitasi yang masih ada.

Kalau kamu butuh detail historis, buka laporan phase di:

```text
docs/audit/2026-07-10/
```

Ingat: folder audit adalah historical evidence. Untuk behavior saat ini, tetap prioritaskan test yang passing dan code sekarang.

## Step 9 - Evaluasi Performa Offline

Untuk evaluasi performa tanpa Google Sheets/Gemini asli, jalankan benchmark sintetis.

### Phase 3 Synthetic Benchmark

```powershell
python -m benchmarks.phase3_synthetic
```

Gunanya:

- cek operation count;
- cek row transfer;
- cek tidak ada full rewrite yang tidak diinginkan;
- cek behavior tetap stabil untuk dataset sintetis.

### Phase 5 Scale Benchmark

```powershell
python -m benchmarks.phase5_scale
```

Gunanya:

- melihat bagaimana operasi tumbuh saat row makin besar;
- membedakan operasi O(1) dan O(N);
- melihat estimasi memory lokal;
- mengecek row budget dan bounded AI context.

Cara membaca hasil:

- `Single save` seharusnya tetap bounded dan tidak membaca semua transaksi.
- `/last`, report, search, export biasanya O(N), artinya makin besar data makin banyak row dibaca.
- `/ask` context tetap memilih record terbatas, tapi persiapan awal masih membaca data transaksi.
- Hasil ini offline synthetic, bukan bukti performa Google Sheets asli.

Dokumen referensi:

```text
docs/performance/phase-5-scale-evidence.md
```

## Step 10 - Evaluasi Live AI Gemini

Default-nya live AI evaluation tidak jalan. Ini sengaja dibuat aman.

Cek default disabled:

```powershell
python evals\run_parser_eval.py
```

Hasil sehat tanpa opt-in:

```text
Live AI evaluation is disabled. Set ENABLE_LIVE_AI_EVAL=1 to opt in.
```

Kalau kamu mau menjalankan live eval, gunakan test key, bukan production key:

```powershell
$env:ENABLE_LIVE_AI_EVAL = "1"
$env:GEMINI_API_KEY = "<test-key>"
python evals\run_parser_eval.py
```

Report akan dibuat di:

```text
evals/reports/
```

Live eval ini mengecek:

- transaction parser;
- batch parser;
- image receipt parser;
- malformed output;
- safety-routing contracts;
- `/ask`;
- `/insight`;
- `/audit`;
- `/coach`;
- bounded context.

Yang perlu diperhatikan:

- Jangan pakai data pribadi asli.
- Jangan pakai screenshot receipt asli.
- Jangan paste API key ke report atau chat.
- Token usage hanya dicatat kalau provider metadata tersedia.
- Tidak ada estimasi biaya yang di-hard-code.

## Step 11 - Bandingkan Report Live AI

Kalau kamu sudah punya baseline dan candidate report:

```powershell
python evals\compare_runs.py evals\reports\baseline.json evals\reports\candidate.json
python evals\gates.py evals\reports\baseline.json evals\reports\candidate.json
```

Cara membaca:

- `metric_improvements`: metrik membaik.
- `metric_degradations`: metrik memburuk.
- `pass_to_fail_cases`: case yang sebelumnya pass sekarang fail.
- `fail_to_pass_cases`: case yang sebelumnya fail sekarang pass.
- `schema_regressions`: output tidak lagi sesuai schema.
- `critical_tag_regressions`: regression di area penting seperti transfer, debt, split bill, invalid date, future intent, cancellation, confirmation security, atau multi-input.

Hasil sehat untuk gate:

```text
Gate passed.
```

Kalau gate gagal, jangan turunkan threshold dulu. Baca case yang gagal dan tentukan apakah itu bug, perubahan prompt yang disengaja, atau dataset expectation yang memang perlu disetujui ulang.

## Step 12 - Evaluasi Staging dengan Dummy Telegram dan Dummy Sheets

Offline test tidak membuktikan Telegram, Google Sheets, atau Gemini asli berjalan cepat dan stabil. Untuk itu perlu staging.

Gunakan hanya:

- test Telegram bot;
- dummy spreadsheet;
- dummy service account;
- synthetic data;
- satu proses aplikasi;
- log redacted.

Panduan lengkap ada di:

```text
docs/testing/phase-5-scale-staging.md
```

Minimal yang perlu kamu ukur:

- p50, p95, p99 latency;
- retry/error count;
- Sheets calls;
- rows transferred;
- rows written;
- quota incidents;
- reconciliation incidents;
- memory host;
- scheduler duplicate;
- export parity;
- privacy di log.

Stop staging kalau:

- production credential tidak sengaja kepakai;
- schema berubah tanpa approval;
- ada mismatch finansial;
- ada repeated reconciliation;
- memory atau quota mulai tidak aman.

## Step 13 - Jalankan Bot Lokal Setelah Semua Offline Check Aman

Kalau test dan config sudah aman:

```powershell
python main.py
```

Cek terminal:

- bot started;
- scheduler started kalau `SCHEDULER_ENABLED=true`;
- tidak ada error credential;
- tidak ada `SpreadsheetNotFound`;
- log masuk ke `logs/finance_bot.log`.

Cek Telegram dengan data dummy:

1. `/start`
2. `/help`
3. `/rekening`
4. `beli kopi 25rb dari Cash`
5. pastikan preview muncul;
6. tekan `Batal`;
7. ulangi dengan dummy transaksi lalu `Simpan`;
8. cek Google Sheets row dan saldo.

Jangan langsung test dengan transaksi pribadi asli sebelum dummy flow aman.

## Checklist Cepat Sebelum Commit

```powershell
python -m pytest -q
python scripts\check_docs.py
python -m compileall -q app evals tests scripts
git diff --check
git status --short
```

Commit hanya kalau:

- semua check penting pass;
- file yang berubah sudah kamu pahami;
- tidak ada file secret ikut Git;
- `logs/` tetap ignored;
- live eval report, kalau ada, tidak berisi data pribadi.

## Kapan Hasil Dianggap Aman?

Untuk development lokal, hasil bisa dianggap aman kalau:

- full pytest pass;
- regression pass;
- docs check pass;
- compileall pass;
- diff check pass;
- tidak ada external call saat default verification;
- log file tidak menyimpan credential atau raw data sensitif;
- git status hanya berisi perubahan yang memang mau kamu simpan.

Untuk production confidence, belum cukup hanya offline test. Kamu tetap butuh dummy staging untuk Telegram, Google Sheets, scheduler, dan optional live Gemini.

## Kapan Perlu Curiga Performa Bermasalah?

Perhatikan tanda ini:

- report/search/export mulai lambat saat rows banyak;
- `/ask` sering kena row budget;
- Google Sheets sering timeout atau quota;
- banyak retry;
- muncul reconciliation-required;
- scheduler membuat duplicate-looking transaction;
- memory host naik tajam saat export/report besar;
- p95/p99 staging buruk secara berulang.

Kalau terjadi sekali, jangan langsung migrasi database. Catat evidence dulu. Phase 5 memutuskan Google Sheets tetap dipakai sampai ada trigger yang jelas dan berulang.

## Urutan Paling Aman

1. Cek `git status`.
2. Jalankan full offline test.
3. Jalankan regression test.
4. Jalankan docs check.
5. Jalankan compileall dan diff check.
6. Baca log file dan pastikan privacy aman.
7. Jalankan benchmark offline kalau menyentuh performa.
8. Jalankan live AI eval hanya dengan opt-in dan test key.
9. Jalankan dummy staging sebelum production.
10. Commit setelah semua hasil sesuai ekspektasi.
