# 03. Telegram Bot Flow

Layer Telegram berada di folder `app/bot/`.

File terpenting:

```text
app/bot/application.py
app/bot/handlers.py
app/bot/handler_parts/
```

## Kenapa ada `application.py`?

`application.py` dibuat agar proses register handler tidak ditulis ulang untuk polling dan webhook.

Fungsi utamanya:

```python
build_telegram_app()
```

Alurnya:

```text
build_telegram_app()
→ Application.builder().token(...).build()
→ register_handlers(telegram_app)
→ register_job_queue_jobs(telegram_app)
→ return telegram_app
```

Dengan pola ini, runtime polling dan webhook memakai Telegram Application yang sama.

## Atomic wrapper untuk setiap handler

Di `application.py`, setiap command/message handler dibungkus oleh:

```python
atomic_bot_handler(callback)
```

Tujuannya:

```text
setiap handler Telegram
→ masuk context sheets_transaction(...)
→ semua write Google Sheets bisa rollback kalau ada error
```

Ini penting karena satu input user bisa menyebabkan beberapa write sekaligus, misalnya:

- transaksi expense tersimpan
- saldo account berubah
- debt baru dibuat
- relasi hutang_id ditulis ke transaction

Jika salah satu gagal, sistem berusaha rollback agar data tidak setengah tersimpan.

## Register command

`register_handlers()` memakai helper internal:

```python
def add_command(command_name: str, callback):
    telegram_app.add_handler(CommandHandler(command_name, atomic_bot_handler(callback)))
```

Contoh command yang didaftarkan:

| Command | Handler | Fungsi |
|---|---|---|
| `/start` | `start_handler` | Pesan awal |
| `/help` | `help_handler` | Bantuan command |
| `/examples`, `/contoh` | `examples_handler` | Contoh input bot |
| `/saldo` | `saldo_handler` | Lihat saldo rekening |
| `/transaksi` | `transaksi_handler` | Lihat transaksi |
| `/budget` | `budget_handler` | Lihat budget |
| `/hutang` | `hutang_handler` | Lihat ringkasan hutang/piutang |
| `/ask` | `ask_handler` | Tanya jawab finance berbasis data |
| `/audit` | `audit_handler` | Audit data quality dan anomali |
| `/coach` | `coach_handler` | Saran finance personal |

## Register message handler

Selain command eksplisit, bot juga menerima pesan bebas.

Urutan message handler penting:

```python
add_message(filters.COMMAND, unknown_command_handler)
add_message(filters.PHOTO | filters.Document.IMAGE, image_handler)
add_message(filters.TEXT & ~filters.COMMAND, message_handler)
```

Artinya:

1. Command yang tidak dikenal masuk ke typo/suggestion handler.
2. Foto atau dokumen gambar masuk ke image parser.
3. Teks biasa masuk ke natural language transaction flow.

## Callback handler

Semua tombol inline Telegram masuk ke:

```python
CallbackQueryHandler(atomic_bot_handler(callback_handler))
```

`callback_handler.py` menangani callback seperti:

- pilih rekening
- edit dulu
- lanjut
- simpan
- batal
- split bill decision
- debt payment decision
- parse clarification choice
- recurring action
- asset confirmation

## Handler facade: `app/bot/handlers.py`

`handlers.py` bukan tempat logic utama. File ini hanya re-export dari modul kecil:

```python
from app.bot.handler_parts.core import *
from app.bot.handler_parts.networth_assets import *
from app.bot.handler_parts.health_recurring_export import *
from app.bot.handler_parts.command_router import *
from app.bot.handler_parts.transaction_flow import *
from app.bot.handler_parts.command_handlers import *
from app.bot.handler_parts.message_handlers import *
from app.bot.handler_parts.callback_handler import *
```

Tujuannya menjaga kompatibilitas import lama:

```python
from app.bot.handlers import saldo_handler, message_handler, callback_handler
```

Namun logic sebenarnya ada di `app/bot/handler_parts/`.

## File dalam `handler_parts`

| File | Tanggung jawab |
|---|---|
| `core.py` | Reply aman, split long message, error handler |
| `common_imports.py` | Helper shared: format rupiah, markdown safe, transaction display |
| `command_handlers.py` | Command utama dan AI finance commands |
| `command_router.py` | Typo resolver, natural command routing, delete/edit refs |
| `message_handlers.py` | Input teks bebas, gambar, Gemini intent fallback |
| `transaction_flow.py` | Preview, edit dulu, mixed transaction, parse safety UI |
| `callback_handler.py` | Semua callback button dan final execution |
| `health_recurring_export.py` | Health check, recurring, export |
| `networth_assets.py` | Net worth, asset, liability flow |
