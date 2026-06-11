# Image Input Gemini Patch

Patch ini menambahkan kemampuan input gambar untuk Finance Bot.

## File yang berubah

- `main.py`
- `app/bot/handlers.py`
- `app/nlp/gemini_image_parser.py` (file baru)

## Cara pakai

Kirim foto struk, nota, QRIS, atau screenshot transaksi ke bot Telegram.

Opsional tambahkan caption untuk membantu parser:

```text
pakai BSI
ini pemasukan
struk makan hari ini
```

Bot akan:

1. Download gambar dari Telegram.
2. Kirim gambar ke Gemini.
3. Minta Gemini mengembalikan JSON transaksi.
4. Menampilkan preview transaksi.
5. Meminta rekening jika belum terbaca.
6. Menyimpan transaksi setelah konfirmasi.

## Environment variable opsional

```env
GEMINI_IMAGE_MODEL=gemini-3.1-flash
```

Kalau tidak diisi, default-nya `gemini-3.1-flash`.

## Catatan privasi

Gambar yang dikirim akan diproses oleh Gemini API. Jangan kirim gambar yang berisi OTP, password, nomor rekening lengkap, NIK, atau dokumen identitas.

## Test minimal

```bash
python -m py_compile main.py
python -m py_compile app\bot\handlers.py
python -m py_compile app\nlp\gemini_image_parser.py
```

Lalu test di Telegram:

1. Kirim foto struk.
2. Kirim screenshot QRIS/payment.
3. Kirim gambar dengan caption `pakai BSI`.
