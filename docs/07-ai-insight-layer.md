# 07. AI Insight Layer

AI layer digunakan untuk membantu menjelaskan data finance, bukan menggantikan business logic lokal.

Command utama:

```text
/ask
/audit
/coach
/insight
```

File yang terlibat:

```text
app/bot/handler_parts/command_handlers.py
app/services/finance_insight_service.py
app/nlp/gemini_finance_insight.py
app/nlp/gemini_langchain_client.py
```

## Alur AI insight

```text
User menjalankan /ask, /audit, /coach, atau /insight
→ command handler menentukan mode
→ finance_insight_service membangun context data
→ gemini_finance_insight membangun prompt
→ gemini_langchain_client memanggil Gemini
→ jawaban dikirim ke Telegram
```

## Context builder

File:

```text
app/services/finance_insight_service.py
```

Fungsi penting:

| Fungsi | Tujuan |
|---|---|
| `build_monthly_finance_context()` | Context bulanan untuk report/insight |
| `build_ask_finance_context()` | Context relevan untuk pertanyaan natural |
| `build_audit_context()` | Context audit data quality dan anomali |
| `build_coach_context()` | Context untuk saran finance personal |
| `summarize_transactions()` | Ringkas transaksi per kategori/periode |
| `detect_anomalies()` | Cari transaksi yang anomali |
| `detect_data_quality_issues()` | Cari data quality issue |
| `search_relevant_transactions()` | Ambil transaksi relevan berdasarkan keyword |

## Prompt builder

File:

```text
app/nlp/gemini_finance_insight.py
```

Fungsi utama:

```python
build_finance_insight_prompt(mode, context_data, question)
generate_finance_insight(mode, context_data, question)
```

Mode yang dipakai:

| Mode | Fungsi |
|---|---|
| `ask` | Menjawab pertanyaan natural berdasarkan data |
| `audit` | Mengecek anomali dan kualitas data |
| `coach` | Memberi saran finance personal |
| `insight` | Membuat narasi insight bulanan |

## Gemini client

File:

```text
app/nlp/gemini_langchain_client.py
```

Fungsi utama:

```python
get_gemini_llm()
generate_text_with_gemini()
generate_text_from_image_with_gemini()
```

LLM provider saat ini:

```text
Gemini only
```

Model bisa diganti lewat `.env`, misalnya:

```env
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_TEXT_MODEL=gemini-3.1-flash-lite
GEMINI_INTENT_MODEL=gemini-3.1-flash-lite
GEMINI_IMAGE_MODEL=gemini-3.1-flash-lite
GEMINI_INSIGHT_MODEL=gemini-3.1-flash-lite
```

Provider lain seperti OpenAI, Llama, Groq, Ollama, atau OpenRouter belum otomatis didukung karena client masih menggunakan Gemini/LangChain Google integration.

## Image parser

File:

```text
app/nlp/gemini_image_parser.py
```

Dipakai oleh:

```text
image_handler()
```

Alur:

```text
user upload foto struk
→ image_handler download file
→ parse_transactions_from_image()
→ Gemini membaca gambar
→ hasil normalisasi item
→ masuk preview/edit/confirm flow
```

Hasil gambar tetap tidak langsung disimpan. User masih harus cek preview.

## Intent router

File:

```text
app/nlp/gemini_intent_router.py
```

Dipakai sebagai fallback ketika local natural intent tidak cukup.

Contoh:

```text
lihat pengeluaran kopi bulan ini
```

Gemini intent router bisa membantu menentukan apakah maksud user adalah search/report/edit/delete. Namun untuk aksi sensitif, handler tetap melakukan confirmation.

## Session history

Di `command_handlers.py` ada helper:

```python
add_session_chat_history()
get_session_chat_history()
attach_session_history()
```

Tujuannya agar `/ask` bisa memahami konteks follow-up dalam session Telegram, misalnya:

```text
User: /ask bulan ini boros di mana?
User: terus dibanding bulan lalu gimana?
```

## Prinsip keamanan AI layer

1. AI boleh membantu menjelaskan.
2. AI boleh membantu membuat draft untuk input non-sensitive.
3. AI tidak boleh langsung menyimpan transaksi.
4. AI tidak boleh menjadi final decision maker untuk hutang/piutang/saldo/delete/edit.
5. Data yang diberikan ke AI berasal dari context yang dibangun backend, bukan dari imajinasi model.
