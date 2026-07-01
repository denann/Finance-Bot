# 06. Data Layer & Services

Data utama project disimpan di Google Sheets.

Layer data terdiri dari dua bagian:

```text
app/services/      # business operation
app/sheets/        # low-level Google Sheets read/write
```

## Google Sheets sebagai operational data store

Sheet yang dipakai:

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
pending_expenses
net_worth_snapshots
```

Auto-setup schema dilakukan oleh:

```python
ensure_spreadsheet_schema()
```

File:

```text
app/sheets/client.py
```

## Sheets client

`app/sheets/client.py` adalah wrapper untuk Google Sheets API/gspread.

Tanggung jawab utama:

- koneksi spreadsheet,
- ambil worksheet,
- buat worksheet jika belum ada,
- tulis header jika kosong,
- seed default account,
- read records,
- append row,
- update cell/range,
- delete row,
- retry write/read,
- best-effort rollback.

## Auto schema bootstrap

Saat startup, `main.py` memanggil:

```python
ensure_schema_on_startup()
```

Di dalamnya:

```python
schema_results = ensure_spreadsheet_schema()
```

Jika spreadsheet kosong atau belum lengkap, sistem menyiapkan:

- tab sheet,
- header,
- default rows untuk sheet tertentu.

Default account yang dibuat jika `accounts` kosong:

```text
Cash, BRI, BSI, BCA, DANA, GoPay, Seabank
```

## Atomic write dan rollback

Class penting:

```python
class SheetsTransaction
```

Context manager:

```python
with sheets_transaction(label="telegram_handler"):
    ...
```

Handler Telegram dibungkus oleh `atomic_bot_handler()` di `application.py`, sehingga setiap handler berjalan di dalam context ini.

Tujuannya:

```text
jika operasi write ke Google Sheets gagal
→ sistem berusaha rollback write sebelumnya
→ data tidak setengah jadi
```

Catatan: rollback Google Sheets bersifat best-effort, karena Google Sheets bukan database transaksi ACID.

## Service layer

Service layer menyimpan business logic yang tidak cocok ditaruh di handler.

| File | Tanggung jawab |
|---|---|
| `transaction_service.py` | Save transaksi, update saldo, edit/delete transaksi, export data |
| `debt_service.py` | Hutang/piutang, payment, settlement, void, edit, offset |
| `budget_service.py` | Set budget, actual expense, status budget |
| `report_service.py` | Harian, mingguan, bulanan, transaksi terakhir, filter rekening/kategori |
| `pending_expense_service.py` | Pending/rencana expense, mark paid, cancel |
| `recurring_service.py` | Rule recurring, next run, recurring logs |
| `net_worth_service.py` | Aset, liability, snapshot net worth, gold price helper |
| `finance_insight_service.py` | Build context finance untuk Gemini insight |

## Transaction service

File:

```text
app/services/transaction_service.py
```

Fungsi inti:

| Fungsi | Tujuan |
|---|---|
| `validate_transaction()` | Validasi field wajib sebelum save |
| `build_transaction_row()` | Membentuk row sesuai header sheet |
| `calculate_account_deltas()` | Hitung perubahan saldo account |
| `apply_account_deltas()` | Terapkan perubahan saldo rekening |
| `save_transaction()` | Save satu transaksi |
| `save_transactions_batch()` | Save beberapa transaksi sekaligus |
| `get_recent_transactions()` | Ambil transaksi terakhir |
| `update_transaction_by_id()` | Edit transaksi |
| `delete_transaction_by_id()` | Delete transaksi |

Prinsip penting:

```text
parser menghasilkan dict
service memvalidasi dict
sheets client menulis data
```

## Debt service

File:

```text
app/services/debt_service.py
```

Konsep debt:

| Konsep | Makna |
|---|---|
| receivable/piutang | Orang lain berutang ke user |
| payable/utang | User berutang ke orang lain |
| payment | Pembayaran sebagian/penuh |
| settlement | Penyelesaian debt |
| offset | Kompensasi utang dan piutang antar orang |
| void | Pembatalan debt |

Fungsi inti:

- `add_debt()`
- `add_payment()`
- `add_payment_by_person()`
- `settle_selected_debt_ids()`
- `offset_debt_by_person()`
- `void_debt()`
- `edit_debt()`

## Budget service

File:

```text
app/services/budget_service.py
```

Tugas utama:

- set/update budget kategori,
- hitung actual expense dari transaksi,
- buat summary budget,
- cek status budget setelah transaksi.

## Report service

File:

```text
app/services/report_service.py
```

Tugas utama:

- filter transaksi berdasarkan periode,
- filter rekening/kategori,
- hitung net expense setelah piutang split bill,
- buat summary per hari/minggu/bulan,
- enrich transaksi dengan debt info.

## Pending expense service

File:

```text
app/services/pending_expense_service.py
```

Tugas utama:

- deteksi kalimat rencana/tagihan,
- menentukan due date,
- save pending expense,
- mark paid,
- cancel.

## Recurring service

File:

```text
app/services/recurring_service.py
```

Tugas utama:

- menyimpan recurring rule,
- menghitung next run,
- membuat transaksi dari recurring rule,
- menulis recurring log,
- disable recurring.

## Net worth service

File:

```text
app/services/net_worth_service.py
```

Tugas utama:

- simpan aset,
- simpan liability,
- hitung net worth,
- snapshot histori,
- update/off asset,
- kalkulasi gain/loss.

## Finance insight service

File:

```text
app/services/finance_insight_service.py
```

Tugas utama:

- mengambil transaksi bulan/periode tertentu,
- meringkas expense/income,
- mengambil status budget,
- mengambil debt summary,
- mengambil net worth,
- mendeteksi anomali dan data quality issue,
- membuat context JSON untuk Gemini.
