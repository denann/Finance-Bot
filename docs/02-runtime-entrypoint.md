# 02. Runtime & Entrypoint

Entrypoint utama project adalah `main.py`.

`main.py` bertugas menjalankan bot dalam dua mode:

1. **Polling mode**: default untuk local setup dan Wispbyte 24/7.
2. **Webhook mode**: optional advanced mode menggunakan FastAPI.

## Runtime mode

Mode dibaca dari environment variable:

```env
BOT_MODE=polling
```

atau:

```env
BOT_MODE=webhook
```

Validasi nilai dilakukan di `app/config.py`:

```python
BOT_MODE = os.getenv("BOT_MODE", "polling").strip().lower()
if BOT_MODE not in {"polling", "webhook"}:
    raise ValueError("BOT_MODE harus 'polling' atau 'webhook'.")
```

## Polling mode

Polling mode dijalankan saat user menjalankan:

```bash
python main.py
```

Jika `BOT_MODE=polling`, maka `main.py` memanggil:

```python
asyncio.run(run_polling_mode())
```

Fungsi `run_polling_mode()` melakukan beberapa langkah:

```text
validate_runtime_config("polling")
→ ensure_schema_on_startup()
→ telegram_app.initialize()
→ delete_webhook(drop_pending_updates=True)
→ telegram_app.start()
→ start_scheduler_once()
→ updater.start_polling()
```

Poin penting:

- `delete_webhook()` dipanggil supaya polling tidak bentrok dengan webhook lama.
- `ensure_schema_on_startup()` mencoba memastikan struktur Google Sheets siap.
- Scheduler tetap aktif di polling mode.
- Bot aktif selama proses Python hidup.

## Webhook mode

Webhook mode digunakan untuk deployment FastAPI:

```env
BOT_MODE=webhook
```

Saat mode webhook aktif, `main.py` menjalankan:

```python
uvicorn.run("main:app", host="0.0.0.0", port=APP_PORT, reload=False)
```

FastAPI app tetap dibuat di level module:

```python
app = FastAPI(title="Finance Bot")
app.include_router(webhook_router)
```

Ini membuat `uvicorn main:app` tetap valid.

## Startup FastAPI

Event startup FastAPI hanya benar-benar mengaktifkan webhook jika `BOT_MODE=webhook`.

Langkah startup webhook:

```text
validate_runtime_config("webhook")
→ telegram_app.initialize()
→ telegram_app.start()
→ ensure_schema_on_startup()
→ set_webhook(WEBHOOK_URL + "/webhook")
→ start_scheduler_once()
```

Jika `BOT_MODE` bukan webhook, startup FastAPI tidak akan set webhook.

## Runtime config validation

`validate_runtime_config()` memastikan env dasar sudah ada:

- `TELEGRAM_BOT_TOKEN`
- `ALLOWED_USER_ID`
- `GOOGLE_SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GEMINI_API_KEY`

Jika mode webhook, tambahan yang wajib:

- `WEBHOOK_URL`
- `TELEGRAM_WEBHOOK_SECRET`

## Scheduler lifecycle

Scheduler dibuat sekali:

```python
scheduler = create_scheduler()
```

Lalu dinyalakan dengan:

```python
start_scheduler_once()
```

Agar tidak double start, fungsi ini mengecek:

```python
if not scheduler.running:
    scheduler.start()
```

Saat shutdown, `shutdown_scheduler_once()` mematikan scheduler jika masih running.

## Endpoint operasional

`main.py` juga menyediakan endpoint:

| Endpoint | Fungsi |
|---|---|
| `/health` | Mengecek status app dan mode runtime |
| `/test-sheets` | Mengecek koneksi Google Sheets dan schema |

Endpoint ini paling relevan saat app dijalankan dalam mode webhook/ASGI server.
