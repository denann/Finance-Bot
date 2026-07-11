# Finance Bot Manual

Panduan ini menjelaskan cara memakai Finance Bot Telegram untuk mencatat transaksi, saldo, utang/piutang, split bill, laporan, budget, kategori, pending expense, recurring, export data, aset, input gambar, dan insight AI.

Semua flow yang menyimpan atau mengubah data memakai preview sebelum simpan. Tombol `Batal` dipakai untuk membatalkan wizard atau preview aktif.

Preview final berlaku satu kali dan kedaluwarsa otomatis. Tombol dari preview lama, tombol yang sudah dipakai, atau preview yang hilang setelah bot restart akan ditolak tanpa menulis data. Command `/pending_paid`, `/pending_cancel`, `/recurring_run`, `/recurring_edit`, `/recurring_off`, `/asset_update`, `/asset_off`, dan `/networth_snapshot` tetap memakai syntax yang sama, tetapi sekarang memerlukan satu konfirmasi `Simpan` tambahan.

## Daftar Isi

- [Quickstart](#quickstart)
- [Input transaksi](#input-transaksi)
- [Utang, piutang, dan split bill](#utang-piutang-dan-split-bill)
- [Laporan dan grafik](#laporan-dan-grafik)
- [Lihat dan koreksi transaksi](#lihat-dan-koreksi-transaksi)
- [Pending expense](#pending-expense)
- [Budget](#budget)
- [Kategori](#kategori)
- [Recurring](#recurring)
- [Export data](#export-data)
- [Data privacy](#data-privacy)
- [Net worth dan aset](#net-worth-dan-aset)
- [Input gambar](#input-gambar)
- [AI/RAG insight](#airag-insight)
- [Troubleshooting](#troubleshooting)
- [Daftar command lengkap](#daftar-command-lengkap)

## Quickstart

Quickstart adalah alur paling pendek untuk user baru. Pakai ini untuk mulai mencatat data tanpa membaca semua fitur.

1. Catat transaksi: `beli kopi 20k dari Cash`
2. Cek saldo: `/saldo`
3. Cek laporan: `/bulanan`
4. Cek utang/piutang: `/hutang`
5. Baca panduan ringkas: `/help`

Command terkait:

- `/start` - pesan awal bot.
- `/quickstart` - panduan awal singkat.
- `/help` - index help Telegram.
- `/manual` - kirim manual PDF ini.
- `/privacy` - ringkasan data privacy dan keamanan credential.
- `/examples` atau `/contoh` - contoh input.
- `/cancel` atau `/batal` - batal flow aktif.
- `/health` - cek status bot, env, Google Sheets, dan sheet utama.

## Input Transaksi

Input transaksi bisa ditulis natural. Bot membaca nominal, rekening, kategori, tanggal, dan intent, lalu menampilkan preview sebelum simpan.

Pengeluaran:

- `beli kopi 25rb`
- `makan siang 35k`
- `bayar listrik 150.000 dari BRI`
- `jajan bakso 20k dari Cash`
- `beli token listrik 300k dari DANA tanggal 2026-07-05`
- `ongkir paket 18rb dari ShopeePay kemarin`
- `service motor 250k kategori Transport dari BCA`

Pemasukan:

- `gaji masuk 8 juta ke BRI`
- `freelance project 500rb ke DANA`
- `dapet bonus 1 juta`
- `refund tokopedia 75k ke DANA`
- `bunga bank 12.500 ke BRI tanggal 2026-07-01`
- `Annisa transfer 200k ke BCA buat patungan`

Transfer:

- `transfer gopay 200rb dari BRI`
- `top up dana dari bri 500rb`
- `isi GoPay 100k dari Cash`
- `pindahin 1 juta dari BRI ke BCA`
- `tarik tunai 300k dari BCA ke Cash`
- `top up e-wallet 150k dari DANA ke GoPay`

Transfer tidak dihitung sebagai expense atau income biasa karena hanya memindahkan saldo antar rekening.

Multi input bisa dipisah enter atau titik koma:

`beli kopi 10k; beli nasi 20k; Budi minjem 50k`

Contoh multi input beda intent:

`gaji 8 juta ke BRI; bayar kos 1.5 juta dari BCA; top up DANA 300k dari BRI`

Contoh dengan tanggal:

`kemarin beli bensin 50k dari Cash; 2026-07-01 bayar internet 285k dari BRI`

Jika transaksi historis tidak boleh mengubah saldo, pilih tombol `Sudah berlalu / jangan ubah saldo`.

## Utang, Piutang, dan Split Bill

Debt flow memisahkan utang/piutang dari transaksi normal. Ini penting supaya pembayaran utang, talangan, split bill, dan potong silang tidak tercatat sebagai expense/income yang salah.

Contoh utang/piutang:

- `hutang ke Budi 500rb`
- `catat utang ke Budi 200k`
- `minjem uang Maya 220k`
- `Budi minjem 300rb`
- `piutang ke Dimas 31100`
- `saya berutang ke Dimas 20k`
- `Dimas berutang 50k`
- `Budi bayar 100rb`
- `bayar hutang Budi 100rb`
- `Maya balikin 75k ke DANA`
- `bayar utang ke Annisa 200k dari BCA`
- `Raka nyicil hutang 50k`
- `catat piutang ke Bagas 120k buat tiket`

Talangin dan ditalangin:

- `saya talangin Raka beli nasi kuning 12k`
- `saya ditalangin Bagas beli nasi uduk 10k`
- `saya nitip Raka beli nasi kuning 12k`
- `ditalangin nasi uduk sama Bagas 10k kemarin`
- `talangin Maya tiket konser 350k dari BCA`
- `ditalangin Raka parkir 20k dari Cash`

Split bill:

- `Ayam dcelup 26k bagi 2 sama Raka`
- `Beli tissue 10k dibagi 4 sama Raka Fajar Bagas`
- `Beli token 500k dibagi 4 sama Raka:100% Fajar:80% Bagas:100%`
- `Beli token 500k dibagi 4 sama Raka 125k Fajar 100k Bagas 125k`
- `makan steak 400k dibagi 2 sama Budi dari DANA`
- `hotel 900k dibagi 3 sama Raka Maya tanggal 2026-07-06`
- `belanja dapur 300k dibagi 4 sama Budi Joko Maya dari BRI`

Kalau teman belum bayar, bagian teman masuk piutang aktif.

Kompensasi atau potong silang tidak mengubah saldo rekening:

- `potong piutang Dimas 20k buat badminton`
- `kompensasi piutang Dimas 20k karena badminton`
- `saya berutang ke Dimas 20k potong dari piutang`
- `potong piutang ke Maya 100k buat tabungan`
- `kompensasi utang ke Budi 50k dari piutang makan`

Kelola debt:

- `/hutang` - lihat semua utang/piutang aktif.
- `/hutang Maya` - detail debt untuk satu nama dan nomor debt.
- `/ringkasan_hutang` - ringkasan utang/piutang.
- `/debt_void 1` - void satu debt dari detail terakhir.
- `/debt_void Maya` - void debt untuk nama tertentu sesuai flow.
- `/debt_void Maya 1` - void nomor debt tertentu.
- `/debt_edit 1 nominal 100k` - edit nominal debt.
- `/debt_edit 1 nama Budi` - edit nama debt.
- `/debt_edit 1 tipe piutang` - edit tipe debt.
- `/debt_settle Raka` - settle seluruh debt Raka sesuai preview.
- `/debt_settle Raka 1-17` - settle range nomor debt Raka.
- `/debt_settle Raka 1-17 amount=337063 account=DANA` - settle dengan amount dan rekening eksplisit.
- `/debt_settle Maya 1 3 5` - settle nomor debt tertentu.

Nomor debt berasal dari detail terakhir `/hutang nama`. Jika terakhir membuka `/hutang Bagas`, lalu settle untuk Raka, bot akan menolak agar tidak salah orang.

## Laporan dan Grafik

Laporan membaca data transaksi dan saldo. Hanya `/set_saldo` yang mengubah data saldo, dan command itu tidak membuat row transaksi baru.

Saldo:

- `/saldo` - tampilkan saldo rekening aktif.
- `/set_saldo` - buka flow set saldo.
- `/set_saldo DANA 500k` - set saldo DANA menjadi Rp500.000.
- `/saldo_set DANA 500k` - alias `/set_saldo`.
- `/set_balance DANA 500k` - alias `/set_saldo`.
- `/set_saldo Cash 1.250.000` - set saldo Cash dengan format titik ribuan.
- `/set_balance BCA 2 juta` - set saldo BCA dengan format natural.

Rekening:

- `/rekening Cash` - mutasi rekening Cash bulan berjalan.
- `/rekening Cash 2026-06` - mutasi rekening Cash pada Juni 2026.
- `/rekening Cash all` - semua mutasi rekening Cash.
- `/rekening BRI 2026-07` - mutasi BRI pada Juli 2026.

Harian:

- `/harian` - ringkasan hari ini.
- `/harian 2026-06-01` - ringkasan tanggal tertentu.
- `/harian Food & Beverage` - ringkasan harian kategori tertentu.
- `/harian rekening Cash` - ringkasan harian rekening tertentu.
- `/harian Transport` - ringkasan harian untuk kategori transport.
- `/harian rekening DANA` - ringkasan harian untuk rekening DANA.

Mingguan:

- `/mingguan` - ringkasan minggu berjalan.
- `/mingguan 2026-06-01` - minggu yang memuat tanggal itu.
- `/mingguan Bills & Utilities` - ringkasan mingguan kategori tertentu.
- `/mingguan rekening Dana` - ringkasan mingguan rekening tertentu.
- `/mingguan Food & Beverage` - ringkasan mingguan kategori makan.
- `/mingguan rekening BRI` - ringkasan mingguan rekening BRI.

Bulanan:

- `/bulanan` - ringkasan bulan berjalan, insight Gemini, dan grafik time series.
- `/bulanan 2026-06` - ringkasan Juni 2026.
- `/bulanan Food & Beverage` - ringkasan bulan berjalan untuk kategori.
- `/bulanan rekening Cash` - ringkasan bulan berjalan untuk rekening.
- `/bulanan 2026-06 rekening Cash` - ringkasan Juni 2026 untuk rekening Cash.
- `/bulanan 2026-06 Food & Beverage rekening Cash` - filter bulan, kategori, dan rekening.
- `/bulanan bulan lalu` - ringkasan bulan sebelumnya.
- `/bulanan 2026-07 Bills & Utilities` - ringkasan kategori tagihan pada Juli 2026.
- `/bulanan 2026-07 rekening DANA` - ringkasan Juli 2026 untuk DANA.

Grafik:

- `/grafik` - grafik PNG bulan berjalan.
- `/grafik 2026-06` - grafik Juni 2026.
- `/grafik line 2026-06` - grafik time series.
- `/grafik timeseries 2026-06` - alias grafik time series.
- `/grafik bar 2026-06` - grafik batang pengeluaran.
- `/grafik pie 2026-06` - grafik kategori.
- `/chart 2026-06` - alias `/grafik`.
- `/grafik bar` - grafik batang bulan berjalan.
- `/grafik pie` - komposisi kategori bulan berjalan.
- `/chart line 2026-07` - alias grafik time series Juli 2026.

Tipe grafik yang didukung: `line`/`timeseries`, `bar`, dan `pie`. Jika bulan tidak ditulis, bot memakai bulan berjalan. `/transaksi` dan `/last` juga mengirim grafik time series PNG dari transaksi yang tampil.

## Lihat dan Koreksi Transaksi

Command transaksi dipakai untuk melihat, mencari, mengedit, atau menghapus transaksi. Edit dan hapus berdasarkan nomor membutuhkan daftar transaksi terakhir dari `/last`, `/transaksi`, atau `/cari`.

Lihat transaksi:

- `/last` - transaksi terakhir dengan jumlah default.
- `/last 20` - 20 transaksi terakhir.
- `/last today` - transaksi hari ini.
- `/last week` - transaksi minggu ini.
- `/last month` - transaksi bulan ini.
- `/last 2026-06` - transaksi bulan tertentu.
- `/transaksi` - transaksi bulan berjalan.
- `/transaksi 2026-06` - transaksi Juni 2026.
- `/transaksi bulan lalu` - transaksi bulan sebelumnya.
- `/transaksi Food & Beverage 2026-06` - transaksi kategori tertentu pada bulan tertentu.
- `/transaksi rekening Cash` - transaksi rekening Cash bulan berjalan.
- `/transaksi rekening Cash 2026-06` - transaksi rekening Cash pada bulan tertentu.
- `/transaksi rekening Cash bulan lalu` - transaksi rekening Cash bulan lalu.
- `/transaksi rekening Cash all` - semua transaksi rekening Cash.
- `/cari kopi` - cari transaksi dengan kata kunci.
- `/cari token` - cari transaksi token/listrik.
- `/cari 2026-07 DANA` - cari transaksi dengan kata kunci periode atau rekening jika terbaca.

Hapus transaksi:

- `/delete_txn 1`
- `/delete_txn 1 3 5`
- `/delete_txn 1-4`
- `/delete_txn 2-4 7` - hapus range dan nomor tertentu setelah preview.

Edit transaksi:

- `/edit_txn 2 amount=15000`
- `/edit_txn 2 desc=Kopi susu`
- `/edit_txn 2 account=BRI category=Food & Beverage`
- `/edit_txn 1 category="Household & Supplies" desc="Galon"`
- `/edit_txn 2 category="Food & Beverage"`
- `/edit_txn txn_id amount=500k dibagi 4 sama Raka:125k Bagas:125k Fajar:100k`
- `/edit_txn 2 bayar_hutang Raka`
- `/edit_txn 2 bayar_piutang Raka`
- `/edit_txn 3 date=2026-07-06`
- `/edit_txn 4 type=income account=BRI`
- `/edit_txn 5 category=Transport desc="Bensin motor"`

Jalankan `/last`, `/transaksi`, atau `/cari` dulu agar nomor transaksi tersedia. Jika transaksi punya `hutang_id`, `/delete_txn` akan mencoba void debt terkait otomatis.

## Pending Expense

Pending expense adalah pengeluaran yang akan ada, tapi belum dibayar. Pending tidak mengubah saldo dan belum masuk pengeluaran aktual.

- `/pending` - daftar pending aktif.
- `/pending 2026-07` - pending bulan tertentu.
- `/pending bulan depan` - pending bulan depan.
- `/pending all` - semua pending.
- `/pending tanpa tanggal` - pending tanpa tanggal.
- `/pending_add bayar wifi 285k tgl 30 dari BRI` - tambah pending dari command eksplisit.
- `/rencana bayar wifi 285k tgl 30 dari BRI` - alias `/pending_add`.
- `pending beli token 500k` - tambah pending dari input natural.
- `rencana beli sepatu 300k bulan depan` - tambah pending bulan depan.
- `nanti perlu bayar wisuda 750k` - tambah pending dari kalimat natural.
- `perlu 750k buat bayar wisuda` - tambah pending dari kalimat natural.
- `nanti bayar pajak motor 450k tanggal 2026-08-15 dari BCA` - pending dengan tanggal eksplisit.
- `perlu servis AC 300k minggu depan` - pending dengan waktu relatif.
- `/pending_paid pending_id BRI` - ubah pending menjadi transaksi aktual dari rekening BRI.
- `/pending_cancel pending_id` - batalkan pending aktif.

Gunakan `/pending` untuk melihat `pending_id`.

## Budget

Budget dipakai untuk membandingkan batas rencana pengeluaran dengan realisasi bersih.

- `/budget` - budget bulan berjalan.
- `/budget 2026-06` - budget bulan tertentu.
- `/set_budget` - buka flow set budget.
- `/budget_history` - histori budget.
- `budget makan 1.5 juta`
- `budget jajan 500rb`
- `budget transport 300rb 2026-07`
- `budget listrik 700k 2026-07`
- `budget belanja rumah 1 juta`
- `/set_budget Food & Beverage 2000000 2026-07`

Budget bisa otomatis map ke kategori atau menjadi budget custom. `/budget` memakai realisasi bersih. Jika ada split bill, output tampil sebagai Bersih (Gross).

## Kategori

Kategori menyimpan nama, tipe `expense`/`income`, symbol, dan aliases. Aliases membantu bot mencocokkan input seperti `kebutuhan rumah` ke kategori existing seperti `Household & Supplies`.

- `/kategori` - lihat daftar kategori.
- `/categories` - alias `/kategori`.
- `/list_kategori` - alias `/kategori`.
- `/add_kategori` - tambah kategori lewat wizard.
- `/tambah_kategori` - alias `/add_kategori`.
- `/add_category` - alias `/add_kategori`.
- `/edit_kategori` - edit tipe, symbol, atau aliases.
- `/ubah_kategori` - alias `/edit_kategori`.
- `/edit_category` - alias `/edit_kategori`.

Contoh kategori:

- Tambah kategori `Household & Supplies` dengan tipe `Expense`, symbol sesuai pilihan user, dan aliases dari Gemini.
- Tambah kategori `Salary` dengan tipe `Income` untuk pemasukan rutin.
- Edit aliases kategori `Food & Beverage` agar variasi seperti `makan`, `kopi`, dan `resto` tetap masuk kategori yang sama.
- Saat edit transaksi memakai `kebutuhan rumah`, bot bisa menyarankan `Household & Supplies` jika cocok dengan name/alias/similarity.

Flow tambah kategori:

1. Bot tanya nama kategori.
2. Bot tanya tipe `Expense` atau `Income` dengan tombol.
3. Bot tanya symbol.
4. Gemini generate aliases.
5. Bot tampilkan preview sebelum simpan.

Jika input kategori cocok dengan kategori existing lewat nama, alias, atau similarity, bot akan bertanya apakah ingin memakai kategori existing atau menambah kategori baru.

## Recurring

Recurring dipakai untuk transaksi rutin seperti langganan, cicilan, atau pemasukan berulang. Rule recurring tidak langsung menjadi transaksi sampai dijalankan atau ditandai sudah bayar.

- `/recurring` - daftar recurring aktif.
- `/recurring_add name=Netflix type=expense amount=65000 category=Entertainment account=DANA frequency=monthly day=5 description="Langganan Netflix"` - tambah recurring.
- `/recurring_edit rec_xxx amount=300k day=20 account=DANA` - edit recurring.
- `/recurring_run` - proses recurring yang jatuh tempo.
- `/recurring_off rec_xxx` - nonaktifkan recurring.
- `/recurring_add name=Wifi type=expense amount=300k category="Bills & Utilities" account=DANA frequency=monthly day=20 description="Langganan Wifi Bulanan"` - recurring expense bulanan.
- `/recurring_add name=Gaji type=income amount=8000000 category=Salary account=BRI frequency=monthly day=25 description="Gaji bulanan"` - recurring income.
- `/recurring_edit rec_xxx category="Bills & Utilities" description="Internet rumah"` - edit kategori dan deskripsi recurring.

Field wajib recurring: `name`, `type`, `amount`, `category`, `account`, `frequency`. Field opsional: `day`, `description`. Frequency yang didukung saat ini: `monthly` atau `bulanan`.

Recurring otomatis muncul sebagai reminder dengan tombol `Sudah bayar`.

## Export Data

Export dipakai untuk mengunduh data transaksi agar bisa dicek di luar bot. Export bersifat read-only dan tidak mengubah saldo, transaksi, budget, debt, atau aset.

- `/download_data` - download data default.
- `/download_data today` - download data hari ini.
- `/download_data week` - download data minggu ini.
- `/download_data 2026-06` - download data bulan tertentu.
- `/export` - alias `/download_data`.
- `/export today` - alias export data hari ini.
- `/export 2026-07` - alias export bulan tertentu.

Export dipisah dari recurring karena recurring membuat atau menjalankan jadwal transaksi, sementara export hanya mengambil data.

## Data Privacy

Finance Bot memproses data finance pribadi seperti input chat, foto struk, transaksi, saldo rekening, kategori, budget, utang/piutang, pending expense, recurring, aset, laporan, dan export.

Data utama disimpan di Google Sheets yang terhubung ke bot. Telegram menjadi jalur input dan output untuk pesan, preview, laporan, dan file export.

Gemini dipakai untuk fitur AI, image parsing, parser draft, dan aliases kategori. Konteks yang dikirim ke Gemini dibatasi ke data yang relevan untuk fitur tersebut. Bot tidak perlu mengirim credential, token, service account JSON, private key, atau nilai `.env` ke Gemini.

File export berisi data finance pribadi. Simpan dan bagikan dengan hati-hati. User tetap perlu menjaga token Telegram, Gemini API key, service account JSON, `.env`, dan akses Google Spreadsheet.

Command terkait:

- `/privacy` - tampilkan ringkasan privacy di Telegram.
- `/help privacy` - panduan privacy singkat.
- `/download_data` atau `/export` - export transaksi dengan warning data sensitif.

## Net Worth dan Aset

Net worth menggabungkan saldo rekening, aset aktif, dan kewajiban yang tersedia di data.

Net worth:

- `/networth` - ringkasan net worth saat ini.
- `/networth_snapshot` - simpan snapshot net worth.
- `/networth_history` - lihat histori snapshot.

Aset:

- `/assets` - daftar aset aktif dan `asset_id`.
- `/asset_add` - tambah aset lewat wizard.
- `/asset_add name=Laptop amount=8jt category=Electronics desc="Laptop kerja"`
- `/asset_add name="Emas Antam" quantity=10 unit=gram price=1.5jt category=Emas`
- `/asset_add Laptop`
- `catet aset hp 10 juta`
- `tambah aset laptop 8 juta`
- `/asset_add name="Motor Beat" amount=15000000 category=Vehicle desc="Motor harian"`
- `/asset_add name="Reksadana Pasar Uang" amount=2500000 category=Investment`
- `/asset_add name="Emas Antam" quantity=5 unit=gram price=1600000 category=Gold desc="Emas fisik"`
- `/asset_update asset_id unit_price=2420000`
- `/asset_update asset_id harga_beli=2559000 tanggal_beli=2026-06-10`
- `/asset_update asset_id amount=9000000`
- `/asset_off asset_id`
- `/asset_update asset_id quantity=12 unit_price=1550000`

`/asset_add` mendukung format satu baris `key=value`, mode tanya-jawab/guided input, dan input natural. Dalam guided input, bot akan menanyakan nama aset, jumlah/unit, harga beli, tanggal beli, harga saat ini, kategori, dan deskripsi. Tanggal beli boleh dikosongkan dengan `lewati`, `kosong`, atau `-`.

## Input Gambar

User bisa kirim foto struk, nota, QRIS, atau screenshot transaksi. Bot membaca gambar dengan Gemini dan menampilkan preview sebelum disimpan.

Caption opsional:

- `pakai BSI`
- `ini pemasukan`
- `total aja`
- `kategori Food & Beverage`
- `tanggal 2026-07-06`
- `jangan ubah saldo`

AI membantu ekstraksi, tetapi preview tetap menjadi sumber konfirmasi sebelum data ditulis.

## AI/RAG Insight

AI insight membaca data yang tersedia dan memberi jawaban finance. Jika data kurang, bot harus menjawab bahwa data tidak cukup.

- `/insight` - insight bulan berjalan.
- `/insight 2026-06` - insight bulan tertentu.
- `/ask bulan ini boros di mana?` - tanya finance ke AI.
- `/ask kapan terakhir saya beli kopi?`
- `/ask budget makan aman gak?`
- `/audit` - audit data/keuangan.
- `/coach` - saran finance.
- `/coach gimana biar nabung 2 juta?`
- `/ask pengeluaran Food & Beverage bulan Juni berapa?`
- `/ask sampai akhir bulan ini kira-kira expense saya aman gak berdasarkan data yang ada?`
- `/ask rekening mana yang paling sering dipakai bulan ini?`
- `/audit 2026-06`
- `/coach fokus hemat kategori apa minggu ini?`

Fitur inti mengubah data. Gemini/RAG hanya membaca dan memberi insight. Data yang dikirim ke Gemini adalah ringkasan relevan, bukan seluruh spreadsheet mentah. `/ask` memakai session history terbatas; history bisa hilang jika bot restart.

## Troubleshooting

- Jika format command tidak terbaca, cek `/help <topik>` sesuai fitur.
- Jika nomor transaksi tidak tersedia, jalankan `/last`, `/transaksi`, atau `/cari` dulu.
- Jika `pending_id`, `asset_id`, atau `rec_xxx` tidak diketahui, jalankan command list terkait.
- Jika manual PDF belum tersedia, generate ulang dengan `python scripts/generate_help_manual_pdf.py`.
- Jika font Poppins belum terpasang, generator PDF memakai fallback font sans-serif yang tersedia.

## Daftar Command Lengkap

Umum:

- `/start`
- `/quickstart`
- `/cancel`
- `/batal`
- `/help`
- `/manual`
- `/privacy`
- `/examples`
- `/contoh`
- `/health`

Saldo dan laporan:

- `/saldo`
- `/set_saldo`
- `/saldo_set`
- `/set_balance`
- `/rekening`
- `/harian`
- `/mingguan`
- `/bulanan`
- `/grafik`
- `/chart`

Transaksi:

- `/cari`
- `/last`
- `/transaksi`
- `/delete_txn`
- `/edit_txn`

Export:

- `/download_data`
- `/export`

Budget:

- `/budget`
- `/set_budget`
- `/budget_history`

Kategori:

- `/kategori`
- `/categories`
- `/list_kategori`
- `/add_kategori`
- `/tambah_kategori`
- `/add_category`
- `/edit_kategori`
- `/ubah_kategori`
- `/edit_category`

Pending:

- `/pending`
- `/pending_add`
- `/rencana`
- `/pending_paid`
- `/pending_cancel`

Debt:

- `/hutang`
- `/ringkasan_hutang`
- `/debt_void`
- `/debt_edit`
- `/debt_settle`

Recurring:

- `/recurring`
- `/recurring_add`
- `/recurring_run`
- `/recurring_edit`
- `/recurring_off`

Net worth dan aset:

- `/networth`
- `/assets`
- `/asset_add`
- `/asset_update`
- `/asset_off`
- `/networth_snapshot`
- `/networth_history`

AI:

- `/insight`
- `/ask`
- `/audit`
- `/coach`
