# 08. Setup, Debugging, dan Deployment

Dokumentasi ini menjelaskan script operasional dan cara debugging.

## Setup check

File:

```text
scripts/setup_check.py
```

Command:

```bash
python scripts/setup_check.py
```

Script ini cocok untuk user GitHub karena output-nya lebih ramah dibanding traceback Python.

Yang dicek:

- file `.env` ada atau tidak,
- env wajib sudah terisi,
- `ALLOWED_USER_ID` berupa angka,
- `service_account.json` ada,
- package utama bisa di-import,
- Google Sheets bisa diakses,
- schema Google Sheets bisa disiapkan otomatis.

Contoh hasil yang diharapkan:

```text
✅ .env ditemukan
✅ TELEGRAM_BOT_TOKEN tersedia
✅ GOOGLE_SHEET_ID tersedia
✅ service_account.json ditemukan
✅ Google Sheets bisa diakses
```

## Debug check

File:

```text
scripts/debug_check.py
```

Command:

```bash
python scripts/debug_check.py
```

Script ini lebih lengkap dan cocok untuk developer.

Yang dicek:

- environment,
- import module,
- config,
- Google Sheets,
- NLP parser,
- transaction service,
- report service,
- budget service,
- debt service,
- recurring service,
- net worth service,
- bot handler,
- scheduler,
- regression command.

## Local run

Default mode:

```env
BOT_MODE=polling
```

Command:

```bash
python main.py
```

Bot akan aktif selama terminal/proses Python tetap hidup.

## Wispbyte polling 24/7

Wispbyte bisa dipakai untuk menjalankan polling mode 24/7.

Start command:

```bash
python main.py
```

Install command:

```bash
pip install -r requirements.txt
```

Kunci penting:

- tetap pakai `BOT_MODE=polling`,
- tidak perlu webhook URL,
- tidak perlu FastAPI config,
- proses Python harus tetap hidup,
- jangan jalankan bot token yang sama di laptop dan Wispbyte bersamaan.

## Deployment via GitHub

Alur:

```text
push ke GitHub
→ Wispbyte pull repository
→ install dependencies
→ run python main.py
```

Kelebihan:

- update lebih rapi,
- tinggal push commit,
- cocok untuk project portfolio.

## Deployment upload manual

Alur:

```text
zip/folder project
→ upload/import ke Wispbyte
→ install dependencies
→ run python main.py
```

Kelebihan:

- cepat untuk coba awal,
- tidak perlu setup GitHub dulu.

Kekurangan:

- setiap update perlu upload ulang.

## FastAPI webhook mode

Webhook mode tetap tersedia sebagai advanced option.

Env:

```env
BOT_MODE=webhook
WEBHOOK_URL=https://your-domain.com
TELEGRAM_WEBHOOK_SECRET=your_secret
APP_PORT=8000
```

Command:

```bash
BOT_MODE=webhook python main.py
```

Atau:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Troubleshooting cepat

### Bot tidak merespons

Cek:

- `python main.py` masih berjalan,
- `TELEGRAM_BOT_TOKEN` benar,
- `ALLOWED_USER_ID` sesuai user Telegram kamu,
- tidak ada proses lain memakai token bot yang sama,
- jika pernah webhook, pastikan polling menghapus webhook lama.

### Google Sheets error

Cek:

- `GOOGLE_SHEET_ID` benar,
- file `service_account.json` ada,
- Google Sheets sudah di-share ke `client_email`,
- akses service account adalah Editor.

### Gemini error

Cek:

- `GEMINI_API_KEY` benar,
- model Gemini tersedia,
- env model tidak typo.

### Callback tombol error

Cek:

- log terminal,
- `callback_handler.py`,
- apakah context user_data masih lengkap,
- apakah callback data cocok dengan branch handler.

### Data setengah tersimpan

Cek:

- apakah handler sudah dibungkus `atomic_bot_handler`,
- apakah write dilakukan via `app/sheets/client.py`,
- apakah ada write langsung ke gspread tanpa transaction wrapper.
