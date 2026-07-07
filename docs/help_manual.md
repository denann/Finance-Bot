# Finance Bot Manual

Panduan ini merangkum cara memakai Finance Bot Telegram untuk mencatat transaksi, utang/piutang, split bill, laporan, budget, aset, recurring, input gambar, dan insight AI.

## Quickstart

1. Catat transaksi: `beli kopi 20k dari Cash`
2. Cek saldo: `/saldo`
3. Cek laporan: `/bulanan`
4. Cek utang/piutang: `/hutang`
5. Baca panduan ringkas: `/help`

## Daftar Isi

- Input transaksi
- Utang, piutang, dan split bill
- Laporan dan grafik
- Lihat dan koreksi transaksi
- Pending expense
- Budget
- Kategori
- Recurring dan export
- Net worth dan aset
- Input gambar
- AI/RAG insight
- Troubleshooting
- Daftar command lengkap

## Input Transaksi

Pengeluaran:

- `beli kopi 25rb`
- `makan siang 35k`
- `bayar listrik 150.000 dari BRI`
- `jajan bakso 20k dari Cash`

Pemasukan:

- `gaji masuk 8 juta ke BRI`
- `freelance project 500rb ke DANA`
- `dapet bonus 1 juta`

Transfer:

- `transfer gopay 200rb dari BRI`
- `top up dana dari bri 500rb`
- `isi GoPay 100k dari Cash`

Multi input bisa dipisah enter atau titik koma:

`beli kopi 10k; beli nasi 20k; Budi minjem 50k`

Jika transaksi historis tidak boleh mengubah saldo, pilih tombol `Sudah berlalu / jangan ubah saldo`.

## Utang, Piutang, dan Split Bill

Contoh utang/piutang:

- `hutang ke Budi 500rb`
- `catat utang ke Budi 200k`
- `minjem uang Maya 220k`
- `Budi minjem 300rb`
- `Budi bayar 100rb`
- `bayar hutang Budi 100rb`

Talangin dan ditalangin:

- `saya talangin Raka beli nasi kuning 12k`
- `saya ditalangin Bagas beli nasi uduk 10k`
- `saya nitip Raka beli nasi kuning 12k`

Split bill:

- `Ayam dcelup 26k bagi 2 sama Raka`
- `Beli tissue 10k dibagi 4 sama Raka Fajar Bagas`
- `Beli token 500k dibagi 4 sama Raka:100% Fajar:80% Bagas:100%`
- `Beli token 500k dibagi 4 sama Raka 125k Fajar 100k Bagas 125k`

Kompensasi atau potong silang tidak mengubah saldo rekening:

- `potong piutang Dimas 20k buat badminton`
- `kompensasi piutang Dimas 20k karena badminton`

Kelola debt:

- `/hutang`
- `/hutang Maya`
- `/debt_void 1`
- `/debt_void Maya`
- `/debt_edit 1 nominal 100k`
- `/debt_settle Raka`
- `/debt_settle Raka 1-17`
- `/debt_settle Raka 1-17 amount=337063 account=DANA`

Nomor debt berasal dari detail terakhir `/hutang nama`.

## Laporan dan Grafik

Saldo:

- `/saldo`
- `/set_saldo`
- `/set_saldo DANA 500k`

`/set_saldo` hanya mengubah saldo di sheet `accounts`. Command ini tidak membuat row transaksi baru.

Laporan:

- `/rekening Cash`
- `/rekening Cash 2026-06`
- `/rekening Cash all`
- `/harian`
- `/harian 2026-06-01`
- `/mingguan`
- `/mingguan 2026-06-01`
- `/bulanan`
- `/bulanan 2026-06`
- `/bulanan 2026-06 rekening Cash`
- `/bulanan 2026-06 Food & Beverage rekening Cash`

Grafik:

- `/grafik`
- `/grafik 2026-06`
- `/grafik line 2026-06`
- `/grafik bar 2026-06`
- `/grafik pie 2026-06`

Tipe grafik yang didukung: line/timeseries, bar, dan pie. Jika bulan tidak ditulis, bot memakai bulan berjalan. `/bulanan` menampilkan ringkasan, insight Gemini, dan grafik time series.

## Lihat dan Koreksi Transaksi

- `/last`
- `/last 20`
- `/last today`
- `/last week`
- `/last month`
- `/last 2026-06`
- `/transaksi`
- `/transaksi 2026-06`
- `/transaksi bulan lalu`
- `/transaksi Food & Beverage 2026-06`
- `/transaksi rekening Cash`
- `/cari kopi`

Hapus transaksi:

- `/delete_txn 1`
- `/delete_txn 1 3 5`
- `/delete_txn 1-4`

Edit transaksi:

- `/edit_txn 2 amount=15000`
- `/edit_txn 2 desc=Kopi susu`
- `/edit_txn 2 account=BRI category=Food & Beverage`
- `/edit_txn 1 category="Household & Supplies" desc="Galon"`
- `/edit_txn txn_id amount=500k dibagi 4 sama Raka:125k Bagas:125k Fajar:100k`
- `/edit_txn 2 bayar_hutang Raka`
- `/edit_txn 2 bayar_piutang Raka`

Jalankan `/last`, `/transaksi`, atau `/cari` dulu agar nomor transaksi tersedia. Jika transaksi punya `hutang_id`, `/delete_txn` akan mencoba void debt terkait otomatis.

## Pending Expense

Pending expense adalah pengeluaran yang akan ada, tapi belum dibayar. Pending tidak mengubah saldo dan belum masuk pengeluaran aktual.

- `/pending`
- `/pending 2026-07`
- `/pending bulan depan`
- `/pending all`
- `/pending tanpa tanggal`
- `/pending_add bayar wifi 285k tgl 30 dari BRI`
- `pending beli token 500k`
- `rencana beli sepatu 300k bulan depan`
- `nanti perlu bayar wisuda 750k`
- `/pending_paid pending_id BRI`
- `/pending_cancel pending_id`

Gunakan `/pending` untuk melihat `pending_id`.

## Budget

- `/budget`
- `/budget 2026-06`
- `/budget_history`
- `budget makan 1.5 juta`
- `budget jajan 500rb`
- `budget transport 300rb 2026-07`

Budget bisa otomatis map ke kategori atau menjadi budget custom. `/budget` memakai realisasi bersih. Jika ada split bill, output tampil sebagai Bersih (Gross).

## Kategori

- `/kategori`
- `/add_kategori`
- `/edit_kategori`

Kategori menyimpan nama, tipe expense/income, symbol, dan aliases. Perubahan kategori memakai preview sebelum disimpan.

## Recurring dan Export

Export:

- `/download_data`
- `/download_data today`
- `/download_data week`
- `/download_data 2026-06`

Recurring:

- `/recurring`
- `/recurring_add name=Netflix type=expense amount=65000 category=Entertainment account=DANA frequency=monthly day=5 description="Langganan Netflix"`
- `/recurring_edit rec_xxx amount=300k day=20 account=DANA`
- `/recurring_run`
- `/recurring_off rec_xxx`

Field wajib recurring: `name`, `type`, `amount`, `category`, `account`, `frequency`. Field opsional: `day`, `description`. Frequency yang didukung saat ini: `monthly` atau `bulanan`.

Recurring otomatis muncul sebagai reminder dengan tombol `Sudah bayar`.

## Net Worth dan Aset

Net worth:

- `/networth`
- `/networth_snapshot`
- `/networth_history`

Aset:

- `/assets`
- `/asset_add`
- `/asset_add name=Laptop amount=8jt category=Electronics desc="Laptop kerja"`
- `/asset_add name="Emas Antam" quantity=10 unit=gram price=1.5jt category=Emas`
- `/asset_add Laptop`
- `catet aset hp 10 juta`
- `tambah aset laptop 8 juta`
- `/asset_update asset_id unit_price=2420000`
- `/asset_update asset_id harga_beli=2559000 tanggal_beli=2026-06-10`
- `/asset_update asset_id amount=9000000`
- `/asset_off asset_id`

`/asset_add` sekarang mendukung format satu baris `key=value`, mode tanya-jawab/guided input, dan input natural. Dalam guided input, bot akan menanyakan nama aset, jumlah/unit, harga beli, tanggal beli, harga saat ini, kategori, dan deskripsi. Tanggal beli boleh dikosongkan dengan `lewati`, `kosong`, atau `-`.

## Input Gambar

User bisa kirim foto struk, nota, QRIS, atau screenshot transaksi. Bot membaca gambar dengan Gemini dan menampilkan preview sebelum disimpan.

Caption opsional:

- `pakai BSI`
- `ini pemasukan`
- `total aja`

## AI/RAG Insight

- `/insight`
- `/insight 2026-06`
- `/ask bulan ini boros di mana?`
- `/ask kapan terakhir saya beli kopi?`
- `/ask budget makan aman gak?`
- `/audit`
- `/coach`
- `/coach gimana biar nabung 2 juta?`

Fitur inti mengubah data. Gemini/RAG hanya membaca dan memberi insight. Data yang dikirim ke Gemini adalah ringkasan relevan, bukan seluruh spreadsheet mentah. `/ask` memakai session history terbatas; history bisa hilang jika bot restart.

## Troubleshooting

- Jika format command tidak terbaca, cek `/help <topik>` sesuai fitur.
- Jika nomor transaksi tidak tersedia, jalankan `/last`, `/transaksi`, atau `/cari` dulu.
- Jika `pending_id`, `asset_id`, atau `rec_xxx` tidak diketahui, jalankan command list terkait.
- Jika manual PDF belum tersedia, generate ulang dengan `python scripts/generate_help_manual_pdf.py`.

## Daftar Command Lengkap

`/quickstart`, `/help`, `/manual`, `/saldo`, `/set_saldo`, `/rekening`, `/harian`, `/mingguan`, `/bulanan`, `/grafik`, `/last`, `/transaksi`, `/cari`, `/delete_txn`, `/edit_txn`, `/hutang`, `/debt_void`, `/debt_edit`, `/debt_settle`, `/pending`, `/pending_add`, `/pending_paid`, `/pending_cancel`, `/budget`, `/budget_history`, `/kategori`, `/add_kategori`, `/edit_kategori`, `/download_data`, `/recurring`, `/recurring_add`, `/recurring_edit`, `/recurring_run`, `/recurring_off`, `/health`, `/networth`, `/networth_snapshot`, `/networth_history`, `/assets`, `/asset_add`, `/asset_update`, `/asset_off`, `/insight`, `/ask`, `/audit`, `/coach`.
