# RAG Finance / Gemini Insight Patch

## Konsep
Fitur ini tidak memakai vector database dulu. Alurnya:

1. Bot ambil data relevan dari Google Sheets.
2. Python menghitung angka penting secara deterministic.
3. Gemini hanya menjelaskan insight, narasi, saran, dan jawaban natural.

Dengan desain ini, angka tetap berasal dari sheet dan logic Python, bukan karangan Gemini.

## Fitur baru

### 1. Tanya jawab finansial natural
Command:

```text
/ask bulan ini boros di mana?
/ask kapan terakhir saya beli kopi?
/ask budget makan aman gak?
```

Natural text tanpa command juga didukung untuk pertanyaan finance tanpa format transaksi, contoh:

```text
bulan ini boros di mana?
ada transaksi aneh bulan ini?
budget saya aman gak?
kasih saran pengeluaran bulan ini
```

### 2. Insight otomatis setelah /bulanan
`/bulanan` dan `/bulanan 2026-06` tetap menampilkan laporan biasa, lalu mengirim pesan kedua berisi insight Gemini.

### 3. Deteksi anomali pengeluaran
Command:

```text
/audit
/audit 2026-06
```

Mendeteksi nominal besar, duplikat potensial, kategori yang terlalu dominan, dan masalah data.

### 4. Budget assistant
Gunakan:

```text
/ask budget makan aman gak?
/ask budget saya jebol gak?
```

### 5. Financial coach ringan
Gunakan:

```text
/coach
/coach gimana biar nabung 2 juta?
```

### 6. Tanya transaksi spesifik
Gunakan:

```text
/ask kapan terakhir saya beli kopi?
/ask total ptpt bulan ini berapa?
/ask transfer ke Annisa totalnya berapa?
```

### 7. Data quality checker
Masuk ke `/audit`.

### 8. Monthly narrative report
Gunakan:

```text
/insight
/insight 2026-06
```

## File yang berubah

```text
main.py
app/bot/handlers.py
app/services/finance_insight_service.py
app/nlp/gemini_finance_insight.py
app/nlp/gemini_image_parser.py
```

## ENV opsional

```env
GEMINI_INSIGHT_MODEL=gemini-2.5-flash
GEMINI_IMAGE_MODEL=gemini-2.5-flash
```

Kalau env tidak diisi, default sudah `gemini-2.5-flash`.

## Compile check

```bash
python -m py_compile main.py
python -m py_compile app\bot\handlers.py
python -m py_compile app\services\finance_insight_service.py
python -m py_compile app\nlp\gemini_finance_insight.py
python -m py_compile app\nlp\gemini_image_parser.py
```

## Test minimal Telegram

```text
/insight
/ask bulan ini boros di mana?
/audit
/coach
/bulanan
bulan ini boros di mana?
ada transaksi aneh bulan ini?
```
