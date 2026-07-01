# 01. Project Map

Project ini adalah Telegram personal finance bot. Secara sederhana, alurnya adalah:

```text
User Telegram
→ Telegram Bot API
→ python-telegram-bot handler
→ Python business logic
→ Parser / Preview / Confirmation
→ Google Sheets
```

Untuk fitur AI:

```text
User question / image
→ handler Telegram
→ context builder / parser
→ Gemini
→ jawaban ke user
```

## Struktur folder utama

```text
app/
├── api/                 # FastAPI webhook endpoint, hanya untuk mode webhook
├── bot/                 # Telegram Application, command handler, message handler, callback flow
├── nlp/                 # Regex parser, normalizer, Gemini parser, image parser, intent router, parse safety
├── scheduler/           # APScheduler jobs untuk reminder, summary, recurring task
├── services/            # Business logic finansial: transaksi, debt, budget, report, net worth, dst.
├── sheets/              # Google Sheets client, schema bootstrap, atomic write/rollback
└── config.py            # Load konfigurasi dari environment variable

scripts/
├── setup_check.py       # Cek setup awal untuk user GitHub
└── debug_check.py       # Diagnostic lebih lengkap untuk developer

main.py                  # Entrypoint runtime polling/webhook
README.md                # Dokumentasi utama untuk user
.env.example             # Env minimal untuk polling mode
.env.webhook.example     # Env tambahan untuk webhook mode
```

## Layer dan tanggung jawab

| Layer | File utama | Tanggung jawab |
|---|---|---|
| Runtime | `main.py` | Memilih mode `polling` atau `webhook`, startup scheduler, setup schema Sheets |
| Config | `app/config.py` | Membaca `.env`, validasi mode, nama sheet |
| Telegram app | `app/bot/application.py` | Membuat Telegram Application dan register semua handler |
| Handler facade | `app/bot/handlers.py` | Re-export handler dari file kecil di `handler_parts` |
| Command handler | `app/bot/handler_parts/command_handlers.py` | `/start`, `/help`, `/saldo`, `/ask`, `/audit`, `/budget`, dll. |
| Message handler | `app/bot/handler_parts/message_handlers.py` | Input natural language, gambar, Gemini intent fallback |
| Callback handler | `app/bot/handler_parts/callback_handler.py` | Tombol inline: lanjut, simpan, batal, edit, account choice, debt decision |
| Transaction flow | `app/bot/handler_parts/transaction_flow.py` | Preview, edit dulu, mixed transaction, parse safety preview |
| NLP/parser | `app/nlp/` | Regex parser, normalisasi nominal, Gemini parser, parse safety routing |
| Service layer | `app/services/` | Operasi bisnis yang mengubah/membaca data finance |
| Sheets layer | `app/sheets/client.py` | Read/write Google Sheets, auto schema, retry, rollback |

## Mental model paling penting

Project ini sengaja memisahkan tiga hal:

1. **Handler** menjawab: user sedang mengirim apa?
2. **Service** menjawab: perubahan data finance apa yang harus terjadi?
3. **Sheets client** menjawab: bagaimana data ditulis ke Google Sheets dengan aman?

Jadi kalau ada bug, jangan langsung ubah semua file. Cari dulu bug-nya ada di layer mana.

Contoh:

- Input salah dibaca → cek `app/nlp/regex_parser.py`, `normalizer.py`, atau `parse_safety.py`.
- Preview/tombol tidak sesuai → cek `transaction_flow.py` atau `callback_handler.py`.
- Data tersimpan salah → cek service terkait, misalnya `transaction_service.py` atau `debt_service.py`.
- Error Google Sheets → cek `app/sheets/client.py` dan env credential.
