"""Modular Markdown help text for Finance Bot commands."""

HELP_TOPICS = (
    "input",
    "debt",
    "laporan",
    "transaksi",
    "pending",
    "budget",
    "aset",
    "recurring",
    "ai",
)

HELP_INDEX_TEXT = """📖 *Panduan Finance Bot*

Gunakan `/quickstart` untuk panduan awal user baru.
Gunakan `/manual` untuk PDF panduan lengkap.
Tombol *Batal* bisa membatalkan wizard atau preview aktif.

*Contoh input umum*
`beli kopi 20k dari Cash`
`gaji 8 juta ke BRI`
`transfer DANA 100k dari BCA`
`Budi minjem 50k`
`ayam 26k bagi 2 sama Raka`

*Command utama*
`/saldo` — cek saldo rekening
`/bulanan` — ringkasan bulanan + insight + grafik
`/grafik` — grafik bulan berjalan
`/transaksi` — list transaksi
`/last` — transaksi terakhir
`/hutang` — utang/piutang aktif
`/budget` — budget vs realisasi
`/assets` — aset aktif
`/pending` — rencana pengeluaran
`/ask` — tanya finance ke AI

*Help detail*
`/help input` — cara catat pengeluaran, pemasukan, transfer, multi input, dan data historis
`/help debt` — utang/piutang, talangin, ditalangin, split bill, potong silang, dan settle debt
`/help laporan` — saldo, set saldo, rekening, harian, mingguan, bulanan, dan grafik
`/help transaksi` — lihat, cari, edit, hapus, dan bulk edit transaksi
`/help pending` — rencana pengeluaran, pending ID, paid, dan cancel pending
`/help budget` — set budget, histori budget, realisasi bersih, dan Bersih (Gross)
`/help aset` — net worth, asset add/update/off, guided input, dan asset ID
`/help recurring` — export data, transaksi rutin, reminder, run, edit, dan off
`/help ai` — input gambar, Gemini/RAG, ask, insight, audit, dan coach"""

UNKNOWN_TOPIC_TEXT = """❌ Topik help belum dikenal.

Topik yang tersedia:
`/help input`
`/help debt`
`/help laporan`
`/help transaksi`
`/help pending`
`/help budget`
`/help aset`
`/help recurring`
`/help ai`"""

HELP_TOPIC_TEXTS = {
    "input": """📥 *Help Input*

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
Tanda `:` opsional. Kalau belum dibayar, bagian teman masuk piutang.

*Kompensasi / potong silang*
`potong piutang Dimas 20k buat badminton`
`kompensasi piutang Dimas 20k karena badminton`
`saya berutang ke Dimas 20k potong dari piutang`
Saldo rekening tidak berubah.

*Kelola debt*
`/hutang`
`/hutang Maya`
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

`/saldo`
`/set_saldo`
`/set_saldo DANA 500k`
`/set_saldo` hanya mengubah saldo di sheet `accounts` dan tidak membuat row transaksi baru.

`/rekening Cash`
`/rekening Cash 2026-06`
`/rekening Cash all`

`/harian`
`/harian 2026-06-01`
`/harian Food & Beverage`
`/harian rekening Cash`

`/mingguan`
`/mingguan 2026-06-01`
`/mingguan Bills & Utilities`
`/mingguan rekening Dana`

`/bulanan`
`/bulanan 2026-06`
`/bulanan Food & Beverage`
`/bulanan rekening Cash`
`/bulanan 2026-06 rekening Cash`
`/bulanan 2026-06 Food & Beverage rekening Cash`

`/grafik`
`/grafik 2026-06`
`/grafik line 2026-06`
`/grafik bar 2026-06`
`/grafik pie 2026-06`

Tipe grafik: `line`/`timeseries`, `bar`, dan `pie`.
Kalau bulan tidak ditulis, bot memakai bulan berjalan.
`/bulanan` menampilkan ringkasan, insight Gemini, dan grafik time series.""",
    "transaksi": """🧾 *Help Transaksi*

`/last`
`/last 20`
`/last today`
`/last week`
`/last month`
`/last 2026-06`

`/transaksi`
`/transaksi 2026-06`
`/transaksi bulan lalu`
`/transaksi Food & Beverage 2026-06`
`/transaksi rekening Cash`
`/transaksi rekening Cash 2026-06`
`/transaksi rekening Cash bulan lalu`
`/transaksi rekening Cash all`

`/cari kopi`

`/delete_txn 1`
`/delete_txn 1 3 5`
`/delete_txn 1-4`

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

Pending expense adalah pengeluaran yang akan ada, tapi belum dibayar.
Pending tidak mengubah saldo dan belum masuk pengeluaran aktual.

`/pending`
`/pending 2026-07`
`/pending bulan depan`
`/pending all`
`/pending tanpa tanggal`

`/pending_add bayar wifi 285k tgl 30 dari BRI`
`pending beli token 500k`
`rencana beli sepatu 300k bulan depan`
`nanti perlu bayar wisuda 750k`
`nanti perlu service motor 300k tgl 30`
`perlu 750k buat bayar wisuda`

`/pending_paid pending_id BRI`
`/pending_cancel pending_id`

Gunakan `/pending` untuk melihat `pending_id`.
`/pending_paid` mengubah pending menjadi transaksi aktual.
`/pending_cancel` membatalkan pending aktif.""",
    "budget": """🎯 *Help Budget*

`/budget`
`/budget 2026-06`
`/budget_history`

`budget makan 1.5 juta`
`budget jajan 500rb`
`budget transport 300rb 2026-07`

Budget bisa otomatis map ke kategori.
Budget juga bisa custom.
`/budget` memakai realisasi bersih.
Jika ada split bill, output tampil sebagai Bersih (Gross).""",
    "aset": """💼 *Help Aset & Net Worth*

*Net worth*
`/networth`
`/networth_snapshot`
`/networth_history`

*Aset*
`/assets`
`/asset_add`
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
Format `key=value` sekarang menjadi format satu baris utama. Mode guided dan natural tetap didukung.

`/asset_update asset_id unit_price=2420000`
`/asset_update asset_id harga_beli=2559000 tanggal_beli=2026-06-10`
`/asset_update asset_id amount=9000000`
`/asset_off asset_id`

Gunakan `/assets` untuk melihat `asset_id`.
`/asset_off` menonaktifkan aset dari daftar aset aktif.
Aset aktif ikut dihitung dalam `/networth`.""",
    "recurring": """🔁 *Help Recurring & Export*

`/download_data`
`/download_data today`
`/download_data week`
`/download_data 2026-06`

`/recurring`
`/recurring_add name=Netflix type=expense amount=65000 category=Entertainment account=DANA frequency=monthly day=5 description="Langganan Netflix"`
`/recurring_edit rec_xxx amount=300k day=20 account=DANA`
`/recurring_run`
`/recurring_off rec_xxx`

Field wajib `/recurring_add`: `name`, `type`, `amount`, `category`, `account`, `frequency`.
Field opsional: `day`, `description`.
Frequency yang didukung saat ini: `monthly` atau `bulanan`.

Recurring otomatis muncul sebagai reminder dengan tombol `Sudah bayar`.
Klik `Sudah bayar` akan mencatat transaksi dan menghentikan notifikasi sampai periode berikutnya.

`/health` dipakai untuk cek status bot, env, Google Sheets, dan sheet utama.""",
    "ai": """🤖 *Help AI, Gambar, dan RAG*

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
