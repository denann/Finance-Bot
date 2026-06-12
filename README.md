# Finance Bot

Telegram Personal Finance Bot untuk mencatat, mengelola, dan menganalisis keuangan pribadi menggunakan natural language, Google Sheets, dan Gemini.

Bot ini dirancang sebagai personal finance assistant: user cukup mengetik transaksi seperti `beli kopi 25k`, `gaji masuk 8 juta`, `Tissue 10k bagi 4 sama Opik Alpat Sapto`, atau mengirim gambar struk. Bot akan mem-parse input, meminta konfirmasi, menyimpan data ke Google Sheets, memperbarui saldo, dan menyediakan laporan serta insight keuangan.

---

## Tech Stack

- **Telegram Bot**: `python-telegram-bot`
- **Backend/Webhook**: FastAPI
- **Database**: Google Sheets
- **AI/NLP**: Gemini via LangChain untuk fallback parser, image receipt parser, dan finance insight
- **Deployment**: Wispbyte
- **Version Control**: GitHub

---

## Main Features

### 1. Transaction Tracking

Mendukung pencatatan transaksi:

- `expense`
- `income`
- `transfer`

Contoh input:

```text
beli kopi 25k
gaji masuk 8 juta
transfer 100k dari BRI ke DANA
beli nasi 10k tanggal 1
beli vaseline 37.5k tanggal 09-06-2026
```

Saldo rekening otomatis berubah berdasarkan jenis transaksi:

- Expense: saldo rekening berkurang
- Income: saldo rekening bertambah
- Transfer: saldo rekening asal berkurang dan rekening tujuan bertambah

---

### 2. Multi Input

Bot bisa membaca beberapa transaksi dalam satu pesan.

Contoh:

```text
beli nasi 17k tanggal 01-06-2026
beli kopi 21k tanggal 01-06-2026
beli vaseline 37.5k tanggal 09-06-2026
```

Bot akan menampilkan preview batch, meminta rekening bila ada item yang belum punya rekening, lalu menyimpan semua item setelah konfirmasi.

---

### 3. Date Parser

Support format tanggal:

```text
tanggal 1
tgl 1
tg 1
01-06-2026
2026-06-01
kemarin
dua hari yang lalu
2 minggu yang lalu
```

Untuk `tanggal 1` atau `tgl 1`, bulan dan tahun mengikuti tanggal saat ini.

---

### 4. Account & Balance

Command utama:

```text
/saldo
```

Data rekening disimpan di sheet `accounts`.

Untuk saldo awal, disarankan input manual langsung di Google Sheets agar tidak tercampur sebagai pemasukan bulanan.

---

### 5. Budget

Command:

```text
/budget
/budget 2026-06
/budget_history
```

Natural input:

```text
budget makan 1.5 juta
budget transport 300rb 2026-07
budget jajan 500rb
budget kebutuhan 2 juta
```

Budget dibuat per bulan. Bot bisa mapping budget umum seperti `makan` ke `Food & Beverage`, tetapi juga mendukung budget custom seperti `Jajan` dan `Kebutuhan`.

---

### 6. Hutang / Piutang

Bot mendukung utang, piutang, dan pembayaran.

Contoh:

```text
Budi minjem 300k
minjem uang Annisa 220k
hutang ke Budi 300k
Budi bayar 100k
bayar hutang Budi 100k
minjemin ke Akmal 70.100k - 19k 15-05-2026
```

Command:

```text
/hutang
/debt_void 1
```

Catatan:

- Transaksi debt cashflow masuk ke `transactions`, tetapi tidak dihapus melalui `/delete_txn` agar sheet `debts` tidak inkonsisten.
- Gunakan `/debt_void` untuk membatalkan debt secara aman.
- `/debt_void` mendukung utang dan piutang, termasuk piutang dari split bill.

---

### 7. Split Bill

Contoh:

```text
Tissue 10k bagi 4 sama Opik Alpat Sapto 11-06-2026
Ayam dcelup 26k bagi 2 sama Sapto
```

Bot akan menghitung bagian per orang dan bertanya apakah teman sudah bayar.

Jika belum, bot akan mencatat piutang per orang tanpa cashflow tambahan.

Contoh expected:

```text
Tissue 10k bagi 4 sama Opik Alpat Sapto
Total: Rp10.000
Bagian per orang: Rp2.500
Piutang:
- Opik Rp2.500
- Alpat Rp2.500
- Sapto Rp2.500
```

---

### 8. Reports & Transaction History

Command ringkasan:

```text
/harian
/harian 2026-06-11
/harian 11

/mingguan
/mingguan 2026-06-11
/mingguan 11

/bulanan
/bulanan 2026-06
/bulanan 6
```

Command transaksi full:

```text
/transaksi
/transaksi hari 2026-06-11
/transaksi minggu 2026-06-11
/transaksi bulan 2026-06
```

Command last:

```text
/last
/last 20
/last today
/last week
/last month
/last 2026-06
```

Catatan:

- `/last` dan `/transaksi` menyimpan mapping nomor transaksi ke `context.user_data`, sehingga bisa dilanjutkan dengan `/delete_txn` atau `/edit_txn`.
- Output panjang dipecah otomatis agar tidak terkena limit Telegram.

---

### 9. Delete & Edit Transaction

Command:

```text
/delete_txn 1
/delete_txn 1 3 5
/delete_txn 1-4
/delete_txn txn_id
```

Command edit:

```text
/edit_txn 2 amount=15000
/edit_txn 2 description=Kopi susu
/edit_txn 2 account=BRI category="Food & Beverage"
/edit_txn 2 date=2026-06-10
```

Untuk transaksi debt cashflow, gunakan `/debt_void`, bukan `/delete_txn`.

---

### 10. Export CSV

Command:

```text
/export
/export today
/export week
/export month
/export 2026-06
```

Export bersifat read-only dan menghasilkan file CSV transaksi.

---

### 11. Recurring Transaction

Command:

```text
/recurring
/recurring_add Netflix | expense | 65000 | Entertainment | DANA | monthly | 5 | Langganan Netflix
/recurring_edit rec_xxx | amount=75000 | day=10
/recurring_run
/recurring_off rec_xxx
```

Sheet terkait:

- `recurring_rules`
- `recurring_logs`

---

### 12. Assets, Liabilities & Net Worth

Command:

```text
/networth
/assets
/liabilities
/networth_snapshot
/networth_history
```

Tambah aset nominal langsung:

```text
/asset_add Laptop | 8000000 | Electronics | Laptop kerja
```

Tambah aset berbasis unit:

```text
add emas 41 gram
add laptop 1 buah
/asset_add Emas Antam | 41 gram | Gold | Tabungan emas
```

Flow aset berbasis unit:

```text
add emas 41 gram
→ bot tanya harga 1 gram
→ user balas 2.41 juta
→ bot preview Simpan/Batal
→ current_value = quantity × price_per_unit
```

Edit harga satuan:

```text
/asset_update asset_xxx | unit_price=2420000
/asset_update asset_xxx | harga_satuan=2.42 juta
```

Formula net worth:

```text
Net Worth = total saldo rekening + total aset aktif - total liabilitas aktif
```

---

### 13. Image Receipt Parser

Bot dapat menerima gambar struk/nota/screenshot transaksi.

Flow:

```text
kirim gambar struk
→ bot download gambar dari Telegram
→ Gemini membaca gambar
→ bot ekstrak transaksi
→ bot tampilkan preview
→ user pilih rekening dan konfirmasi
```

Caption opsional:

```text
pakai BSI
total aja
ini pemasukan
```

Jika struk punya rincian item, default-nya bot mencoba membuat multi-item. Jika ingin satu transaksi total, gunakan caption `total aja`.

---

### 14. Gemini / RAG Finance Insight

Command:

```text
/insight
/insight 2026-06

/ask bulan ini boros di mana?
/ask kapan terakhir saya beli kopi?
/ask budget makan aman gak?

/audit
/audit 2026-06

/coach
/coach gimana biar nabung 2 juta?
```

Natural question juga bisa diarahkan ke RAG finance:

```text
bulan ini boros di mana?
ada transaksi aneh bulan ini?
budget saya aman gak?
kasih saran pengeluaran bulan ini
```

Desain RAG finance:

1. Bot membaca data relevan dari Google Sheets.
2. Python menghitung summary, top categories, budget status, anomaly, dan transaksi relevan.
3. Gemini hanya menerima context ringkas, bukan seluruh spreadsheet mentah.
4. Gemini menjelaskan insight, audit, atau saran finansial.

---

### 15. Health Check

Command:

```text
/health
```

Cek:

- Environment variables
- Google Sheets connection
- Sheet utama
- Gemini API key
- Webhook URL
- App port

Health check tidak melakukan generate content Gemini agar tidak boros token.

---

## Google Sheets Tabs

Tab utama yang digunakan:

```text
transactions
accounts
budgets
debts
debt_payments
categories
monthly_summary
recurring_rules
recurring_logs
assets
liabilities
net_worth_snapshots
```

---

## Environment Variables

Contoh `.env`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ALLOWED_USER_ID=your_telegram_user_id
GOOGLE_SHEET_ID=your_google_sheet_id
GEMINI_API_KEY=your_gemini_api_key
WEBHOOK_URL=https://your-wispbyte-domain.app/
APP_PORT=8000
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret

GEMINI_MODEL=gemini-2.5-flash
GEMINI_TEXT_MODEL=gemini-2.5-flash-lite
GEMINI_INTENT_MODEL=gemini-2.5-flash-lite
GEMINI_IMAGE_MODEL=gemini-2.5-flash
GEMINI_INSIGHT_MODEL=gemini-2.5-flash
```

---

## Security Notes

Jangan commit file sensitif:

```gitignore
.env
*.env
service-account.json
credentials.json
token.json
__pycache__/
*.pyc
.venv/
venv/
Venv/
.local/
```

Jika credential sudah terlanjur tracked:

```bash
git rm --cached .env
git rm --cached service-account.json
```

---

## Local Checks Before Commit

```bash
python -m py_compile main.py
python -m py_compile app/bot/handlers.py
python -m py_compile app/services/transaction_service.py
python -m py_compile app/services/budget_service.py
python -m py_compile app/services/debt_service.py
python -m py_compile app/services/report_service.py
python -m py_compile app/services/recurring_service.py
python -m py_compile app/services/net_worth_service.py
python -m py_compile app/nlp/regex_parser.py
python -m py_compile app/nlp/gemini_parser.py
python -m py_compile app/nlp/gemini_image_parser.py
python -m py_compile app/nlp/gemini_finance_insight.py
```

Run debug script:

```bash
python scripts/debug_check.py
```

---

## Git Workflow

```bash
git status
git add .
git commit -m "Update finance bot"
git push origin main
```

Jika push ditolak karena remote lebih baru:

```bash
git pull --rebase origin main
git push origin main
```

---

## Build ZIP Release

Cara paling aman:

```powershell
git archive --format=zip --output financebot_release.zip HEAD
```

Ini hanya memasukkan file yang sudah tracked Git, sehingga `.env` atau file credential yang tidak di-track tidak ikut.

---

## Deployment Notes for Wispbyte

Pastikan:

- Branch deploy adalah `main`
- `WEBHOOK_URL` adalah public HTTPS URL
- Requirements sudah kompatibel
- File baru sudah di-commit dan push
- Redeploy/rebuild dilakukan, bukan hanya restart

Jika memakai LangChain Gemini, hindari dependency yang konflik. Gunakan versi di `requirements.txt` sebagai source of truth.
