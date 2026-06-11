# Finance Bot Development Patch

Patch ini menggabungkan pengembangan terbaru:

1. `/last` diurutkan berdasarkan tanggal transaksi terbaru, bukan urutan row input.
2. Sheet `transactions` auto-sort berdasarkan tanggal terbaru setiap transaksi baru disimpan dan setelah edit transaksi.
3. Ringkasan harian sudah ada; sekarang `/harian`, `/mingguan`, `/bulanan` bisa menerima argumen periode tertentu.
4. Flow hutang/piutang tetap langsung terkoneksi ke sheet `debts`.
5. Budget lebih fleksibel: alias kuat seperti `makan` tetap map ke `Food & Beverage`, sedangkan `jajan`, `kebutuhan`, dll disimpan sebagai budget custom.
6. Setelah simpan multi input, total pemasukan, pengeluaran, transfer, dan net tetap ditampilkan.
7. Split bill sederhana didukung: `Ayam dcelup 26k bagi 2 sama Sapto` akan bertanya apakah sudah dibayar. Kalau belum, dibuat piutang ke Sapto tanpa cashflow tambahan.
8. Ringkasan periode tertentu:
   - `/harian 2026-06-01`
   - `/harian 1`
   - `/mingguan 2026-06-01`
   - `/bulanan 2026-06`
   - `/bulanan 6`

## Files changed

- `app/bot/handlers.py`
- `app/services/transaction_service.py`
- `app/services/budget_service.py`
- `app/services/report_service.py`

Patch zip juga menyertakan file key terbaru agar tidak kehilangan fitur patch sebelumnya:

- `main.py`
- `app/services/debt_service.py`
- `app/services/net_worth_service.py`
- `app/nlp/regex_parser.py`

## Suggested compile test

```bash
python -m py_compile main.py
python -m py_compile app\bot\handlers.py
python -m py_compile app\services\transaction_service.py
python -m py_compile app\services\budget_service.py
python -m py_compile app\services\report_service.py
python -m py_compile app\services\debt_service.py
python -m py_compile app\services\net_worth_service.py
python -m py_compile app\nlp\regex_parser.py
```

## Suggested Telegram tests

```text
/last
/last today
/harian 1
/mingguan 2026-06-01
/bulanan 2026-06
budget makan 1.5 juta
budget jajan 500rb
Ayam dcelup 26k bagi 2 sama Sapto
Beli kopi 10k
Uang ptpt bulanan dari Opik 200k kemarin
```
