"""Modular Markdown help text for Finance Bot commands."""

HELP_TOPICS = (
    "input",
    "debt",
    "laporan",
    "transaksi",
    "pending",
    "budget",
    "kategori",
    "aset",
    "recurring",
    "export",
    "privacy",
    "ai",
    "commands",
)

HELP_INDEX_TEXT = """📖 *Panduan Finance Bot*

Finance Bot membantu catat transaksi, saldo, utang/piutang, split bill, budget, aset, recurring, export data, dan insight AI. Semua flow yang menyimpan data memakai preview sebelum simpan.

Gunakan `/quickstart` untuk panduan awal user baru.
Gunakan `/manual` untuk PDF panduan lengkap.
Gunakan `/privacy` untuk ringkasan data privacy dan keamanan credential.
Tombol *Batal* bisa membatalkan wizard atau preview aktif.

*Contoh input umum*
`beli kopi 20k dari Cash`
`gaji 8 juta ke BRI`
`transfer DANA 100k dari BCA`
`Budi minjem 50k`
`ayam 26k bagi 2 sama Raka`

*Command utama*
`/saldo` - lihat saldo rekening aktif.
`/bulanan` - ringkasan bulanan, insight Gemini, dan grafik time series.
`/grafik` - kirim grafik PNG untuk bulan berjalan atau bulan tertentu.
`/transaksi` - lihat transaksi dengan filter bulan, kategori, atau rekening.
`/last` - lihat transaksi terakhir; nomor dari output ini bisa dipakai untuk edit/hapus.
`/hutang` - lihat utang/piutang aktif dan nomor debt.
`/budget` - bandingkan budget dengan realisasi pengeluaran bersih.
`/assets` - lihat aset aktif yang masuk net worth.
`/pending` - lihat rencana pengeluaran yang belum dibayar.
`/ask` - tanya kondisi keuangan ke AI berdasarkan data yang tersedia.

*Help detail*
`/help input` - cara catat pengeluaran, pemasukan, transfer, multi input, dan transaksi historis.
`/help debt` - utang/piutang, talangin, ditalangin, split bill, potong silang, dan settle debt.
`/help laporan` - saldo, set saldo, rekening, harian, mingguan, bulanan, dan grafik.
`/help transaksi` - lihat, cari, edit, hapus, bulk edit, dan dependency nomor dari `/last`/`/transaksi`.
`/help pending` - pending expense, pending ID, paid, dan cancel pending.
`/help budget` - set budget, histori budget, realisasi bersih, dan Bersih (Gross).
`/help kategori` - lihat kategori, tambah kategori, edit kategori, symbol, tipe, dan aliases.
`/help aset` - net worth, asset add/update/off, guided input, dan asset ID.
`/help recurring` - transaksi rutin, reminder, run, edit, dan off.
`/help export` - download/export data transaksi.
`/help privacy` - data yang diproses, Google Sheets, Telegram, Gemini, export sensitif, dan credential.
`/help ai` - input gambar, Gemini/RAG, ask, insight, audit, dan coach.
`/help commands` - daftar semua command dan alias yang terdaftar."""

UNKNOWN_TOPIC_TEXT = """❌ Topik help belum dikenal.

Topik yang tersedia:
`/help input`
`/help debt`
`/help laporan`
`/help transaksi`
`/help pending`
`/help budget`
`/help kategori`
`/help aset`
`/help recurring`
`/help export`
`/help privacy`
`/help ai`
`/help commands`"""

HELP_TOPIC_TEXTS = {
    "input": """📥 *Help Input*

Input natural dipakai untuk mencatat transaksi tanpa format spreadsheet. Bot membaca nominal, tanggal, kategori, rekening, subjek, dan intent, lalu menampilkan preview sebelum data disimpan.

*Pengeluaran*
`beli kopi 25rb`
`makan siang 35k`
`bayar listrik 150.000 dari BRI`
`jajan bakso 20k dari Cash`

*Pemasukan*
`gaji masuk 8 juta ke BRI`
`freelance project 500rb ke DANA`
`dapet bonus 1 juta`

*Transfer antar rekening*
`transfer gopay 200rb dari BRI`
`top up dana dari bri 500rb`
`isi GoPay 100k dari Cash`

Transfer tidak dihitung sebagai expense/income biasa karena hanya memindahkan saldo antar rekening.

*Multi input*
Bisa dipisah enter, titik koma, atau kalimat natural.
`beli kopi 10k`
`beli nasi 20k`
`Dimas bayar hutang 20k kemarin`

Satu baris:
`beli kopi 10k; beli nasi 20k; Budi minjem 50k`

*Data historis*
Kalau transaksi sudah berlalu dan saldo tidak mau diubah, pilih tombol `Sudah berlalu / jangan ubah saldo`.
Transaksi tetap tercatat, tapi saldo rekening tidak berubah.""",
    "debt": """🤝 *Help Debt*

Debt dipakai untuk memisahkan utang/piutang dari transaksi biasa. Flow ini menjaga agar pembayaran, talangan, split bill, dan potong silang tidak tercampur dengan expense/income normal.

*Utang/piutang biasa*
`hutang ke Budi 500rb`
`catat utang ke Budi 200k`
`minjem uang Maya 220k`
`Budi minjem 300rb`
`piutang ke Dimas 31100`
`saya berutang ke Dimas 20k`
`Dimas berutang 50k`
`Budi bayar 100rb`
`bayar hutang Budi 100rb`

*Talangin / ditalangin*
`saya talangin Raka beli nasi kuning 12k`
`saya ditalangin Bagas beli nasi uduk 10k`
`saya nitip Raka beli nasi kuning 12k`
`ditalangin nasi uduk sama Bagas 10k kemarin`

*Split bill*
`Ayam dcelup 26k bagi 2 sama Raka`
`Beli tissue 10k dibagi 4 sama Raka Fajar Bagas`
`Beli token 500k dibagi 4 sama Raka:100% Fajar:80% Bagas:100%`
`Beli token 500k dibagi 4 sama Raka 125k Fajar 100k Bagas 125k`
Tanda `:` opsional. Kalau teman belum bayar, bagian teman masuk piutang aktif.

*Kompensasi / potong silang*
`potong piutang Dimas 20k buat badminton`
`kompensasi piutang Dimas 20k karena badminton`
`saya berutang ke Dimas 20k potong dari piutang`
Saldo rekening tidak berubah karena ini hanya mencatat relasi utang/piutang.

*Kelola debt*
`/hutang`
`/hutang Maya`
`/ringkasan_hutang`
`/debt_void 1`
`/debt_void Maya`
`/debt_void Maya 1`
`/debt_edit 1 nominal 100k`
`/debt_edit 1 nama Budi`
`/debt_edit 1 tipe piutang`
`/debt_settle Raka`
`/debt_settle Raka 1-17`
`/debt_settle Raka 1-17 amount=337063 account=DANA`
`Raka bayar hutang 337063 untuk debt 1-17`

Nomor debt berasal dari detail terakhir `/hutang nama`.
Jika terakhir membuka `/hutang Bagas`, lalu settle untuk Raka, bot akan menolak.
Kalau amount lebih besar dari net debt, bot memberi warning.""",
    "laporan": """📊 *Help Laporan*

Laporan dipakai untuk membaca saldo, transaksi per rekening, ringkasan harian/mingguan/bulanan, dan grafik. Command laporan tidak mengubah data kecuali `/set_saldo`.

*Saldo*
`/saldo` - menampilkan saldo rekening aktif.
`/set_saldo` - membuka flow set saldo.
`/set_saldo DANA 500k` - langsung set saldo rekening DANA menjadi Rp500.000.
`/saldo_set DANA 500k` - alias untuk `/set_saldo`.
`/set_balance DANA 500k` - alias untuk `/set_saldo`.
`/set_saldo` hanya mengubah saldo di sheet `accounts` dan tidak membuat row transaksi baru.

*Rekening*
`/rekening Cash` - mutasi rekening Cash bulan berjalan.
`/rekening Cash 2026-06` - mutasi rekening Cash pada Juni 2026.
`/rekening Cash all` - semua mutasi rekening Cash.

*Harian*
`/harian` - ringkasan hari ini.
`/harian 2026-06-01` - ringkasan tanggal tertentu.
`/harian Food & Beverage` - ringkasan harian untuk kategori tertentu.
`/harian rekening Cash` - ringkasan harian untuk rekening tertentu.

*Mingguan*
`/mingguan` - ringkasan minggu berjalan.
`/mingguan 2026-06-01` - minggu yang memuat tanggal tersebut.
`/mingguan Bills & Utilities` - ringkasan mingguan kategori tertentu.
`/mingguan rekening Dana` - ringkasan mingguan rekening tertentu.

*Bulanan*
`/bulanan` - ringkasan bulan berjalan, insight Gemini, dan grafik time series.
`/bulanan 2026-06` - ringkasan Juni 2026.
`/bulanan Food & Beverage` - ringkasan bulan berjalan untuk kategori.
`/bulanan rekening Cash` - ringkasan bulan berjalan untuk rekening.
`/bulanan 2026-06 rekening Cash` - ringkasan Juni 2026 untuk rekening Cash.
`/bulanan 2026-06 Food & Beverage rekening Cash` - filter bulan, kategori, dan rekening.

*Grafik*
`/grafik` - grafik PNG bulan berjalan.
`/grafik 2026-06` - grafik Juni 2026.
`/grafik line 2026-06` - grafik time series.
`/grafik timeseries 2026-06` - alias grafik time series.
`/grafik bar 2026-06` - grafik batang pengeluaran.
`/grafik pie 2026-06` - grafik kategori.
`/chart 2026-06` - alias untuk `/grafik`.

Tipe grafik: `line`/`timeseries`, `bar`, dan `pie`.
Kalau bulan tidak ditulis, bot memakai bulan berjalan.
`/transaksi` dan `/last` juga mengirim grafik time series PNG untuk transaksi yang tampil.""",
    "transaksi": """🧾 *Help Transaksi*

Command transaksi dipakai untuk melihat, mencari, mengedit, atau menghapus transaksi yang sudah tersimpan. Edit dan hapus berdasarkan nomor membutuhkan daftar transaksi terakhir dari `/last`, `/transaksi`, atau `/cari`.

*Lihat transaksi*
`/last` - transaksi terakhir dengan jumlah default.
`/last 20` - 20 transaksi terakhir.
`/last today` - transaksi hari ini.
`/last week` - transaksi minggu ini.
`/last month` - transaksi bulan ini.
`/last 2026-06` - transaksi bulan tertentu.

`/transaksi` - transaksi bulan berjalan.
`/transaksi 2026-06` - transaksi Juni 2026.
`/transaksi bulan lalu` - transaksi bulan sebelumnya.
`/transaksi Food & Beverage 2026-06` - transaksi kategori tertentu pada bulan tertentu.
`/transaksi rekening Cash` - transaksi rekening Cash bulan berjalan.
`/transaksi rekening Cash 2026-06` - transaksi rekening Cash pada bulan tertentu.
`/transaksi rekening Cash bulan lalu` - transaksi rekening Cash bulan lalu.
`/transaksi rekening Cash all` - semua transaksi rekening Cash.

`/cari kopi` - mencari transaksi dengan kata kunci.

*Hapus transaksi*
`/delete_txn 1`
`/delete_txn 1 3 5`
`/delete_txn 1-4`

*Edit transaksi*
`/edit_txn 2 amount=15000`
`/edit_txn 2 desc=Kopi susu`
`/edit_txn 2 account=BRI category=Food & Beverage`
`/edit_txn 1 category="Household & Supplies" desc="Galon"`
`/edit_txn 2 category="Food & Beverage"`
`/edit_txn txn_id amount=500k dibagi 4 sama Raka:125k Bagas:125k Fajar:100k`
`/edit_txn 2 bayar_hutang Raka`
`/edit_txn 2 bayar_piutang Raka`

Sebelum `/edit_txn` atau `/delete_txn`, jalankan `/last`, `/transaksi`, atau `/cari` dulu agar nomor transaksi tersedia.
Bulk edit bisa paste beberapa baris `/edit_txn` sekaligus.
Jika transaksi punya `hutang_id`, `/delete_txn` akan mencoba void debt terkait otomatis.
Output `/transaksi` dan `/last` otomatis mengirim grafik time series PNG dari transaksi yang tampil.""",
    "pending": """🕒 *Help Pending Expense*

Pending expense adalah rencana pengeluaran yang belum dibayar. Pending tidak mengubah saldo dan belum masuk pengeluaran aktual sampai ditandai paid.

`/pending` - daftar pending aktif.
`/pending 2026-07` - pending untuk bulan tertentu.
`/pending bulan depan` - pending bulan depan.
`/pending all` - semua pending.
`/pending tanpa tanggal` - pending yang belum punya tanggal.

`/pending_add bayar wifi 285k tgl 30 dari BRI`
`/rencana bayar wifi 285k tgl 30 dari BRI`
`pending beli token 500k`
`rencana beli sepatu 300k bulan depan`
`nanti perlu bayar wisuda 750k`
`nanti perlu service motor 300k tgl 30`
`perlu 750k buat bayar wisuda`

`/pending_paid pending_id BRI` - ubah pending menjadi transaksi aktual dari rekening BRI.
`/pending_cancel pending_id` - batalkan pending aktif.

Gunakan `/pending` untuk melihat `pending_id`.
`/pending_paid` mengubah pending menjadi transaksi aktual.
`/pending_cancel` membatalkan pending aktif.""",
    "budget": """🎯 *Help Budget*

Budget dipakai untuk membandingkan batas rencana pengeluaran dengan realisasi bersih. Jika ada split bill, output bisa menampilkan Bersih (Gross) agar nilai pribadi dan nilai transaksi tetap terlihat.

`/budget` - budget bulan berjalan.
`/budget 2026-06` - budget bulan tertentu.
`/set_budget` - membuka flow set budget.
`/budget_history` - histori budget.

`budget makan 1.5 juta`
`budget jajan 500rb`
`budget transport 300rb 2026-07`

Budget bisa otomatis map ke kategori.
Budget juga bisa custom.
`/budget` memakai realisasi pengeluaran bersih, bukan gross.""",
    "kategori": """🏷️ *Help Kategori*

Kategori dipakai untuk klasifikasi expense/income. Tiap kategori punya nama, tipe, symbol, dan aliases agar input natural seperti `kebutuhan rumah` bisa diarahkan ke kategori yang tepat.

`/kategori` - lihat daftar kategori.
`/categories` - alias untuk `/kategori`.
`/list_kategori` - alias untuk `/kategori`.

`/add_kategori` - tambah kategori lewat wizard.
`/tambah_kategori` - alias untuk `/add_kategori`.
`/add_category` - alias untuk `/add_kategori`.

Flow tambah kategori:
1. Bot tanya nama kategori.
2. Bot tanya tipe `Expense` atau `Income` dengan tombol.
3. Bot tanya symbol.
4. Gemini generate aliases.
5. Bot tampilkan preview sebelum simpan.

`/edit_kategori` - edit tipe, symbol, atau aliases.
`/ubah_kategori` - alias untuk `/edit_kategori`.
`/edit_category` - alias untuk `/edit_kategori`.

Kalau input kategori mirip kategori existing, bot akan tanya apakah mau ikut kategori existing atau tambah kategori baru.""",
    "aset": """💼 *Help Aset & Net Worth*

Aset dipakai untuk mencatat nilai aset aktif yang ikut dihitung di net worth. Net worth menggabungkan saldo rekening, aset aktif, dan kewajiban yang tersedia di data.

*Net worth*
`/networth` - ringkasan net worth saat ini.
`/networth_snapshot` - simpan snapshot net worth.
`/networth_history` - lihat histori snapshot.

*Aset*
`/assets` - daftar aset aktif dan `asset_id`.
`/asset_add` - tambah aset lewat wizard.
`/asset_add name=Laptop amount=8jt category=Electronics desc="Laptop kerja"`
`/asset_add name="Emas Antam" quantity=10 unit=gram price=1.5jt category=Emas`
`/asset_add Laptop`
`catet aset hp 10 juta`
`tambah aset laptop 8 juta`

`/asset_add` bisa mode tanya-jawab/guided input.
Bot akan menanyakan:
1. Nama aset
2. Jumlah/unit
3. Harga beli
4. Tanggal beli
5. Harga saat ini
6. Kategori
7. Deskripsi

Tanggal beli boleh dikosongkan dengan `lewati`, `kosong`, atau `-`.
Format `key=value` menjadi format satu baris utama. Mode guided dan natural tetap didukung.

`/asset_update asset_id unit_price=2420000`
`/asset_update asset_id harga_beli=2559000 tanggal_beli=2026-06-10`
`/asset_update asset_id amount=9000000`
`/asset_off asset_id`

Gunakan `/assets` untuk melihat `asset_id`.
`/asset_off` menonaktifkan aset dari daftar aset aktif.
Aset aktif ikut dihitung dalam `/networth`.""",
    "recurring": """🔁 *Help Recurring*

Recurring dipakai untuk transaksi rutin seperti langganan, cicilan, atau pemasukan berulang. Rule recurring tidak langsung menjadi transaksi sampai dijalankan atau ditandai sudah bayar.

`/recurring` - daftar recurring aktif.
`/recurring_add name=Netflix type=expense amount=65000 category=Entertainment account=DANA frequency=monthly day=5 description="Langganan Netflix"`
`/recurring_edit rec_xxx amount=300k day=20 account=DANA`
`/recurring_run` - proses recurring yang jatuh tempo.
`/recurring_off rec_xxx` - nonaktifkan recurring.

Field wajib `/recurring_add`: `name`, `type`, `amount`, `category`, `account`, `frequency`.
Field opsional: `day`, `description`.
Frequency yang didukung saat ini: `monthly` atau `bulanan`.

Recurring otomatis muncul sebagai reminder dengan tombol `Sudah bayar`.
Klik `Sudah bayar` akan mencatat transaksi dan menghentikan notifikasi sampai periode berikutnya.""",
    "export": """📤 *Help Export*

Export dipakai untuk mengunduh data transaksi agar bisa dicek di luar bot. Command ini tidak mengubah saldo, transaksi, budget, debt, atau aset.

`/download_data` - download data default.
`/download_data today` - download data hari ini.
`/download_data week` - download data minggu ini.
`/download_data 2026-06` - download data bulan tertentu.
`/export` - alias untuk `/download_data`.

File export berisi data finance pribadi. Simpan dan bagikan dengan hati-hati.
Export dipisah dari recurring karena tujuannya read-only: mengambil data, bukan membuat jadwal transaksi.""",
    "privacy": """🔐 *Help Privacy*

`/privacy` menampilkan ringkasan data privacy Finance Bot.

*Data yang diproses*
Bot memproses input chat, foto transaksi/struk, transaksi, saldo rekening, kategori, budget, utang/piutang, pending expense, recurring, aset, export, dan laporan.

*Penyimpanan dan jalur data*
Data finance utama disimpan di Google Sheets.
Telegram menjadi jalur input dan output untuk pesan, preview, laporan, dan file export.

*Gemini*
Gemini dipakai untuk AI finance, image parsing, parser draft, dan aliases kategori.
Konteks yang dikirim dibatasi ke data relevan untuk fitur tersebut, bukan credential, token, service account JSON, atau env value.

*Export dan credential*
File export sensitif karena berisi data finance pribadi.
User harus menjaga token Telegram, Gemini API key, service account JSON, `.env`, dan akses spreadsheet.""",
    "ai": """🤖 *Help AI, Gambar, dan RAG*

AI membantu membaca input gambar dan menjawab pertanyaan finance dari data yang tersedia. AI tidak menjadi final decision maker untuk simpan/edit data; preview dan tombol konfirmasi tetap dipakai.

*Input gambar*
Kirim foto struk, nota, QRIS, atau screenshot transaksi.
Bot membaca gambar dengan Gemini dan menampilkan preview sebelum disimpan.
Caption opsional: `pakai BSI`, `ini pemasukan`, `total aja`.

*AI/RAG*
`/insight`
`/insight 2026-06`
`/ask bulan ini boros di mana?`
`/ask kapan terakhir saya beli kopi?`
`/ask budget makan aman gak?`
`/audit`
`/coach`
`/coach gimana biar nabung 2 juta?`

Contoh pertanyaan:
`bulan ini boros di mana?`
`ada transaksi aneh bulan ini?`
`budget saya aman gak?`
`kasih saran pengeluaran bulan ini`

Fitur inti mengubah data. Gemini/RAG hanya membaca dan memberi insight.
Data yang dikirim ke Gemini adalah ringkasan relevan, bukan seluruh spreadsheet mentah.
`/ask` memakai session history terbatas agar paham pertanyaan lanjutan.
History bisa hilang jika bot restart.""",
    "commands": """📚 *Daftar Command Lengkap*

*Umum*
`/start`, `/quickstart`, `/cancel`, `/batal`, `/help`, `/manual`, `/privacy`, `/examples`, `/contoh`, `/health`

*Saldo dan laporan*
`/saldo`, `/set_saldo`, `/saldo_set`, `/set_balance`, `/rekening`, `/harian`, `/mingguan`, `/bulanan`, `/grafik`, `/chart`

*Transaksi*
`/cari`, `/last`, `/transaksi`, `/delete_txn`, `/edit_txn`

*Export*
`/download_data`, `/export`

*Budget*
`/budget`, `/set_budget`, `/budget_history`

*Kategori*
`/kategori`, `/categories`, `/list_kategori`, `/add_kategori`, `/tambah_kategori`, `/add_category`, `/edit_kategori`, `/ubah_kategori`, `/edit_category`

*Pending*
`/pending`, `/pending_add`, `/rencana`, `/pending_paid`, `/pending_cancel`

*Debt*
`/hutang`, `/ringkasan_hutang`, `/debt_void`, `/debt_edit`, `/debt_settle`

*Recurring*
`/recurring`, `/recurring_add`, `/recurring_run`, `/recurring_edit`, `/recurring_off`

*Net worth dan aset*
`/networth`, `/assets`, `/asset_add`, `/asset_update`, `/asset_off`, `/networth_snapshot`, `/networth_history`

*AI*
`/insight`, `/ask`, `/audit`, `/coach`""",
}


def build_help_text(topic: str | None = None) -> str:
    """Return the Markdown help text for an optional help topic.

    Args:
        topic: Optional topic name from `/help <topic>`. The expected shape is a
            short string such as `input`, `debt`, `laporan`, or an empty value
            for the index.

    Returns:
        Markdown text safe for the project's existing Telegram Markdown style.
        Unknown topics return the topic list instead of raising.

    Side effects:
        None.

    Flow constraints:
        Keep `/help` short. Put detailed guidance in topic pages or the PDF
        manual, and never document command formats that the code does not
        actually support.
    """
    normalized = str(topic or "").strip().lower()
    if not normalized:
        return HELP_INDEX_TEXT
    return HELP_TOPIC_TEXTS.get(normalized, UNKNOWN_TOPIC_TEXT)
