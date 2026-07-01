# Denan Finance Bot

Denan Finance Bot adalah Telegram personal finance assistant untuk mencatat, mengelola, dan menganalisis keuangan pribadi langsung dari chat.

Project ini dibuat untuk menyelesaikan masalah pencatatan keuangan harian yang sering terasa ribet, tidak konsisten, dan mudah terlupakan. Alih-alih membuka spreadsheet manual setiap kali ada transaksi, user cukup mengetik input natural seperti `beli kopi 25k`, `topup gopay 100k dari bsi`, atau `ditalangin Budi bayar makan 100k`.

Bot akan membaca input tersebut, mem-parse tanggal, nominal, rekening, kategori, utang/piutang, split bill, hingga transaksi berulang, lalu menyimpannya ke Google Sheets. Selain pencatatan, bot juga menyediakan ringkasan keuangan, budgeting, net worth tracking, export data, dan AI finance insight menggunakan Gemini.

## Outline

- [Features](#features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Limitations](#limitations)
- [Author](#author)

## Features

<table style="border-collapse: collapse; width: 100%; border: none;">
  <thead>
    <tr>
      <th align="left" style="border: none; border-bottom: 2px solid #d0d7de; padding: 8px 12px;">Group</th>
      <th align="left" style="border: none; border-bottom: 2px solid #d0d7de; padding: 8px 12px;">Feature</th>
      <th align="left" style="border: none; border-bottom: 2px solid #d0d7de; padding: 8px 12px;">Description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td rowspan="7" align="center" valign="middle" style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;"><strong>Input</strong></td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Single Input</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Mencatat satu transaksi dari pesan natural language.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Multiple Input</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Mencatat beberapa transaksi sekaligus dalam satu pesan.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Parser Tanggal, Nominal, Rekening, dan Kategori</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Membaca tanggal relatif, nominal seperti <code>25k</code>/<code>1.5 juta</code>, rekening, dan kategori transaksi.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Utang, Piutang, Talangin, dan Ditalangin</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Mendukung pencatatan utang/piutang personal, termasuk transaksi yang ditalangin atau menalangi orang lain.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Split Bill</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Membagi transaksi ke beberapa orang dan otomatis membuat piutang terkait.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Pending Expense</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Menyimpan transaksi yang belum lengkap untuk dilengkapi kemudian.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Input Gambar</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Membaca struk atau gambar transaksi menggunakan Gemini Vision.</td>
    </tr>
    <tr>
      <td rowspan="2" align="center" valign="middle" style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;"><strong>Manajemen</strong></td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Debt Void, Debt Edit, Debt Settle</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Mengelola status utang/piutang, membatalkan debt, mengubah data debt, dan menyelesaikan pembayaran.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Delete Txn dan Edit Txn</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Menghapus atau mengedit transaksi yang sudah tersimpan.</td>
    </tr>
    <tr>
      <td rowspan="6" align="center" valign="middle" style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;"><strong>Ringkasan</strong></td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Saldo</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Menampilkan saldo seluruh rekening.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Rekening</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Menampilkan transaksi lengkap dan saldo untuk rekening tertentu.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Harian, Mingguan, Bulanan</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Menampilkan laporan transaksi berdasarkan periode.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Cari</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Mencari transaksi berdasarkan keyword.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Last dan Transaksi</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Melihat transaksi terakhir atau daftar transaksi lengkap.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Ringkasan Hutang</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Menampilkan total utang dan piutang aktif.</td>
    </tr>
    <tr>
      <td rowspan="2" align="center" valign="middle" style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;"><strong>Budgeting</strong></td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Add Budget</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Menambahkan budget bulanan per kategori.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Budget History</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Melihat histori budget dan realisasi pengeluaran.</td>
    </tr>
    <tr>
      <td align="center" valign="middle" style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;"><strong>Recurring Transaction</strong></td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Recurring Transaction</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Mencatat transaksi berulang seperti wifi, token, langganan, atau iuran.</td>
    </tr>
    <tr>
      <td align="center" valign="middle" style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;"><strong>Export Data</strong></td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Export Data</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Export data transaksi untuk backup atau analisis lanjutan.</td>
    </tr>
    <tr>
      <td align="center" valign="middle" style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;"><strong>Net Worth dan Aset</strong></td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Net Worth dan Aset</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Melacak aset aktif dan menghitung net worth berdasarkan saldo rekening dan aset.</td>
    </tr>
    <tr>
      <td rowspan="4" align="center" valign="middle" style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;"><strong>Gemini RAG Finance Insight</strong></td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Coach</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Memberikan saran keuangan personal berdasarkan data transaksi.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Audit</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Mengecek data quality, anomali, dan potensi kesalahan input.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Ask</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Menjawab pertanyaan natural seperti “bulan ini boros di mana?”.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Insight</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Memberikan insight pola pengeluaran dan prioritas perbaikan.</td>
    </tr>
    <tr>
      <td rowspan="2" align="center" valign="middle" style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;"><strong>Supporting</strong></td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Typo Handling</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Membantu menangani typo pada command atau input transaksi.</td>
    </tr>
    <tr>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Scheduler</td>
      <td style="border: none; border-bottom: 1px solid #d0d7de; padding: 8px 12px;">Menjalankan job otomatis seperti recurring transaction dan export terjadwal.</td>
    </tr>
  </tbody>
</table>

Contoh penggunaan bot tersedia di bagian [Usage](#usage).

## Tech Stack

- Python
- Telegram Bot API
- FastAPI
- Google Sheets API
- Gemini API
- LangChain
- APScheduler
- gspread
- python-telegram-bot
- Google Service Account
- Wispbyte / Webhook Deployment
- Git & GitHub

## System Architecture

<p align="center">
  <img src="assets/workflow-ai-finance-assistant.png" alt="Workflow AI Finance Assistant" width="900">
</p>

Sistem ini memiliki dua alur utama. Pertama, **alur pencatatan transaksi**, yaitu input dari Telegram diproses oleh parser, divalidasi melalui preview, lalu disimpan ke Google Sheets sebagai data layer utama. Kedua, **alur AI insight**, yaitu user dapat bertanya melalui `/ask`, `/audit`, `/coach`, atau `/insight`, lalu backend mengambil konteks data yang relevan sebelum Gemini membantu menyusun penjelasan.

Prinsip utama dari arsitektur ini adalah AI tidak langsung mengambil keputusan finansial sendiri. Business logic tetap dikontrol oleh backend, sedangkan Gemini digunakan untuk membantu memahami input, membaca gambar, dan menjelaskan insight berdasarkan data yang sudah tersedia.

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/username/denan-finance-bot.git
cd denan-finance-bot
```

Ganti `username` dengan username GitHub kamu.

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

Aktifkan virtual environment.

Windows:

```bash
.venv\Scripts\activate
```

Mac/Linux:

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` File

Copy file `.env.example` menjadi `.env`.

```bash
cp .env.example .env
```

Jika menggunakan Windows Command Prompt:

```cmd
copy .env.example .env
```

Lalu buka file `.env` dan isi semua konfigurasi berikut.

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_SECRET=your_random_secret_here
ALLOWED_USER_ID=your_telegram_user_id_here

# Google Sheets
GOOGLE_SHEET_ID=your_spreadsheet_id_here
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json

# Gemini
GEMINI_API_KEY=your_gemini_api_key_here

# App
WEBHOOK_URL=https://your-domain.com
APP_PORT=8000
```

### 5. Setup Telegram Bot Token

`TELEGRAM_BOT_TOKEN` adalah token utama agar aplikasi Python bisa terhubung ke bot Telegram.

Cara mengisinya:

1. Buka Telegram.
2. Cari `@BotFather`.
3. Jalankan command:

```text
/newbot
```

4. Ikuti instruksi BotFather untuk membuat nama dan username bot.
5. Setelah bot dibuat, BotFather akan memberikan token.
6. Copy token tersebut ke `.env`.

Contoh:

```env
TELEGRAM_BOT_TOKEN=1234567890:AAExampleTelegramBotToken
```

### 6. Setup Webhook Secret

`TELEGRAM_WEBHOOK_SECRET` digunakan sebagai secret tambahan agar webhook bot tidak mudah ditembak dari luar.

Isi dengan random string bebas.

Contoh:

```env
TELEGRAM_WEBHOOK_SECRET=denan-finance-secret-2026
```

Untuk production, gunakan string yang lebih random.

Contoh lebih aman:

```env
TELEGRAM_WEBHOOK_SECRET=9f1c2b8e7a4d4c0aa123456789xyz
```

### 7. Setup Allowed Telegram User ID

`ALLOWED_USER_ID` digunakan agar bot hanya bisa dipakai oleh user tertentu.

Cara mendapatkan Telegram user ID:

1. Buka Telegram.
2. Cari bot pengecek user ID, misalnya `@RawDataBot` atau bot sejenis.
3. Start bot tersebut.
4. Copy angka user ID dari field `message.from.id`.
5. Masukkan angka tersebut ke `.env`.

Contoh output dari bot pengecek user ID:

```json
{
  "message": {
    "from": {
      "id": 123456789,
      "is_bot": false,
      "first_name": "Your First Name",
      "last_name": "Your Last Name",
      "username": "your_username"
    },
    "chat": {
      "id": 123456789,
      "type": "private"
    },
    "text": "/start"
  }
}
```

Yang perlu diambil adalah angka ini:

```env
ALLOWED_USER_ID=123456789
```

Jika bot ingin dipakai beberapa user, sesuaikan implementasi authorization di project.

### 8. Setup Google Sheets

`GOOGLE_SHEET_ID` adalah ID spreadsheet yang digunakan sebagai database utama bot.

Cara mengisinya:

1. Buat Google Sheets baru.
2. Copy Spreadsheet ID dari URL.

Contoh URL:

```text
https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890/edit#gid=0
```

Spreadsheet ID-nya adalah bagian ini:

```text
1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
```

Masukkan ke `.env`:

```env
GOOGLE_SHEET_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
```

### 9. Setup Google Service Account

`GOOGLE_SERVICE_ACCOUNT_JSON` adalah path menuju file credential service account Google Cloud.

Cara setup:

1. Buka Google Cloud Console.
2. Buat project baru atau gunakan project yang sudah ada.
3. Aktifkan **Google Sheets API**.
4. Masuk ke menu **IAM & Admin**.
5. Buka **Service Accounts**.
6. Buat service account baru.
7. Buat key baru dengan format JSON.
8. Download file JSON tersebut.
9. Simpan file JSON di root project.

Contoh nama file:

```text
service_account.json
```

Lalu isi `.env`:

```env
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
```

Pastikan file `service_account.json` tidak di-commit ke GitHub.

Tambahkan ke `.gitignore`:

```gitignore
service_account.json
.env
```

### 10. Share Google Sheets ke Service Account

Bot tidak akan bisa membaca atau menulis Google Sheets sebelum spreadsheet dibagikan ke email service account.

Cara share:

1. Buka file `service_account.json`.
2. Cari field `client_email`.

Contoh:

```json
{
  "client_email": "denan-finance-bot@project-id.iam.gserviceaccount.com"
}
```

3. Copy email tersebut.
4. Buka Google Sheets yang dipakai sebagai database.
5. Klik **Share**.
6. Paste email service account.
7. Berikan akses **Editor**.
8. Klik **Send** atau **Share**.

Tanpa step ini, bot tidak bisa membaca dan menulis data ke Google Sheets.

### 11. Setup Gemini API Key

`GEMINI_API_KEY` digunakan untuk fitur AI parser, image parser, dan finance insight.

Cara mengisinya:

1. Buka Google AI Studio.
2. Buat API key Gemini.
3. Copy API key tersebut.
4. Masukkan ke `.env`.

Contoh:

```env
GEMINI_API_KEY=AIzaSyExampleGeminiApiKey
```

### 12. Setup App URL and Port

`APP_PORT` adalah port yang digunakan aplikasi saat berjalan.

Untuk local development, port bisa dibiarkan seperti ini:

```env
APP_PORT=8000
```

`WEBHOOK_URL` adalah URL publik yang digunakan Telegram untuk mengirim update ke aplikasi bot.

Untuk local development tanpa webhook publik, kamu bisa isi sementara dengan placeholder:

```env
WEBHOOK_URL=https://your-domain.com
```

Untuk production, isi dengan domain deploy yang aktif.

Contoh jika menggunakan custom domain:

```env
WEBHOOK_URL=https://your-domain.com
```

Contoh jika menggunakan Wispbyte:

```env
WEBHOOK_URL=https://your-app-name.wispbyte.com
```

Pastikan tidak ada slash di akhir URL.

Benar:

```env
WEBHOOK_URL=https://your-app-name.wispbyte.com
```

**Hindari:**

```env
WEBHOOK_URL=https://your-app-name.wispbyte.com/
```

### 13. Final `.env` Example

Setelah semua step selesai, file `.env` kurang lebih akan terlihat seperti ini:

```env
# Telegram
TELEGRAM_BOT_TOKEN=1234567890:AAExampleTelegramBotToken
TELEGRAM_WEBHOOK_SECRET=9f1c2b8e7a4d4c0aa123456789xyz
ALLOWED_USER_ID=123456789

# Google Sheets
GOOGLE_SHEET_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json

# Gemini
GEMINI_API_KEY=AIzaSyExampleGeminiApiKey

# App
WEBHOOK_URL=https://your-app-name.wispbyte.com
APP_PORT=8000
```

### 14. Run Locally

Jalankan aplikasi:

```bash
python main.py
```

Atau menggunakan Uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Jika berhasil, aplikasi akan berjalan di:

```text
http://localhost:8000
```

### 15. Deploy and Run Webhook

Jika menggunakan deployment seperti Wispbyte atau server lain:

1. Upload project ke server.
2. Pastikan `.env` sudah terisi.
3. Pastikan `service_account.json` tersedia di server.
4. Install dependencies.
5. Jalankan aplikasi.
6. Pastikan `WEBHOOK_URL` mengarah ke domain aktif.
7. Cek apakah bot sudah bisa menerima pesan dari Telegram.

## Usage

### Input Transaksi Harian

```text
beli kopi 25k
beli nasi padang 17k pakai cash
gaji masuk 8 juta ke bsi
topup gopay 100k dari bsi
transfer 250k dari bsi ke dana
```

### Input Banyak Transaksi

```text
beli nasi 17k
beli kopi 20k
beli bensin 40k pakai cash
```

### Input dengan Tanggal

```text
beli kopi 25k kemarin
beli bensin 40k tanggal 12
beli token 100k 2026-06-15
```

### Utang dan Piutang

```text
minjem uang ke Budi 100k
Budi bayar hutang 50k
pinjemin Raka 75k
Raka bayar piutang 25k
```

### Talangin dan Ditalangin

```text
talangin Budi beli makan 100k
ditalangin Raka bayar parkir 20k
```

### Split Bill

```text
beli galon 24k dibagi 4 sama Budi Raka Dimas
makan 120k split sama Budi Raka
```

### Pending Expense

```text
pending beli token 100k
```

### Budget

```text
budget makan 1.5 juta
budget transport 300k
/budget
/budget_history
```

### Ringkasan dan Laporan

```text
/saldo
/rekening Cash
/harian
/mingguan
/bulanan
/transaksi
/last
/cari kopi
/ringkasan_hutang
```

### Debt Management

```text
/hutang
/hutang Budi
/debt_void Budi
/debt_edit
/debt_settle
```

### Net Worth dan Aset

```text
/assets
/asset_add
/asset_update
/networth
```

### Export Data

```text
/export
```

### AI Finance Insight

```text
/coach
/audit
/insight
/ask bulan ini boros di mana?
/ask pengeluaran terbesar bulan ini apa?
```

## Project Structure

```text
.
├── app/
│   ├── api/
│   │   └── webhook.py
│   ├── bot/
│   │   ├── handlers.py
│   │   ├── keyboards.py
│   │   └── handler_parts/
│   │       ├── callback_handler.py
│   │       ├── command_handlers.py
│   │       ├── command_router.py
│   │       ├── common_imports.py
│   │       ├── core.py
│   │       ├── health_recurring_export.py
│   │       ├── message_handlers.py
│   │       ├── networth_assets.py
│   │       └── transaction_flow.py
│   ├── nlp/
│   │   ├── gemini_finance_insight.py
│   │   ├── gemini_image_parser.py
│   │   ├── gemini_intent_router.py
│   │   ├── gemini_langchain_client.py
│   │   ├── gemini_parser.py
│   │   ├── normalizer.py
│   │   └── regex_parser.py
│   ├── scheduler/
│   │   └── jobs.py
│   ├── services/
│   │   ├── budget_service.py
│   │   ├── debt_service.py
│   │   ├── finance_insight_service.py
│   │   ├── net_worth_service.py
│   │   ├── pending_expense_service.py
│   │   ├── recurring_service.py
│   │   ├── report_service.py
│   │   └── transaction_service.py
│   ├── sheets/
│   │   └── client.py
│   └── config.py
├── assets/
│   └── workflow-ai-finance-assistant.png
├── scripts/
│   └── debug_check.py
├── .env.example
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

## Limitations

Beberapa batasan project saat ini:

1. **Google Sheets bukan database transaksional penuh**  
   Project ini menggunakan Google Sheets sebagai database. Sudah ada retry dan rollback handling, tetapi tetap tidak sekuat database seperti PostgreSQL untuk transaksi berskala besar.

2. **Parsing natural language belum selalu sempurna**  
   Input yang terlalu ambigu masih bisa salah dibaca, terutama jika nominal, rekening, atau orang yang terlibat tidak jelas.

3. **AI insight bergantung pada kualitas data**  
   Insight dari Gemini akan lebih akurat jika kategori, rekening, tanggal, dan tipe transaksi sudah rapi.

4. **Belum multi-user penuh**  
   Bot ini dirancang sebagai personal finance bot, bukan aplikasi SaaS multi-user.

5. **Google Sheets quota limit**  
   Jika terlalu banyak operasi read/write dalam waktu singkat, bot dapat terkena limit API Google Sheets.

6. **Image parser bergantung pada kualitas gambar**  
   Struk yang buram, terpotong, atau terlalu gelap dapat membuat hasil parsing kurang akurat.

7. **Command dan business logic masih berkembang**  
   Beberapa fitur seperti recurring, net worth, debt management, dan AI insight masih bisa terus disempurnakan sesuai kebutuhan pemakaian harian.

## Author

**Denanda Aufadlan Tsaqif**

- LinkedIn: `https://www.linkedin.com/in/your-linkedin`
- Portfolio: `https://your-portfolio.com`
- GitHub: `https://github.com/your-username`
