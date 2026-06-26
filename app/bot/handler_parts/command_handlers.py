# Split from app/bot/handlers.py for readability.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    text = (
        "👋 Halo! Saya Finance Bot pribadi Anda.\n\n"
        "Saya bisa bantu mencatat, mengoreksi, dan menganalisis keuangan dari Google Sheets.\n\n"

        "🧾 *Catat transaksi*\n"
        "• `beli kopi 25rb`\n"
        "• `gaji masuk 8 juta`\n"
        "• `transfer GoPay 200rb dari BRI`\n"
        "• kirim foto struk / QRIS\n\n"

        "🤝 *Utang, piutang, split bill*\n"
        "• `Budi minjem 300k`\n"
        "• `saya talangin Sapto beli nasi kuning 12k`\n"
        "• `saya ditalangin Alpat beli nasi uduk 10k`\n"
        "• `nasi goreng 30k bagi 3 sama Akmal Sapto`\n\n"

        "📊 *Laporan & koreksi data*\n"
        "`/saldo`, `/rekening`, `/harian`, `/mingguan`, `/bulanan`, `/last`, `/cari`\n"
        "`/transaksi`, `/edit_txn`, `/delete_txn`, `/download_data`\n\n"

        "🕒 *Pending, budget & transaksi rutin*\n"
        "`/pending`, `/pending_add`, `/budget`, `/budget_history`, `/recurring`\n"
        "Pending tidak mengubah saldo sampai ditandai `/pending_paid`. Recurring akan muncul sebagai reminder dengan tombol `Sudah bayar`.\n\n"

        "💼 *Net worth*\n"
        "`/assets`, `/networth`, `/networth_snapshot`\n\n"

        "🤖 *Analisis Gemini / RAG Finance*\n"
        "`/insight`, `/ask`, `/audit`, `/coach`\n\n"

        "Ketik `/help` untuk panduan lengkap."
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    text = (
        "📖 *Panduan Penggunaan Finance Bot*\n\n"
        "`/start` — ringkasan fitur utama bot\n"
        "`/help` — panduan lengkap ini\n\n"

        "*A. Cara Input Utama*\n"
        "Bot bisa menerima 1 transaksi, banyak transaksi sekaligus, foto struk/QRIS, atau command.\n\n"

        "*1. Catat Pengeluaran*\n"
        "`beli kopi 25rb`\n"
        "`makan siang 35k`\n"
        "`bayar listrik 150.000 dari BRI`\n"
        "`jajan bakso 20k dari Cash`\n\n"

        "*2. Catat Pemasukan*\n"
        "`gaji masuk 8 juta ke BRI`\n"
        "`freelance project 500rb ke DANA`\n"
        "`dapet bonus 1 juta`\n\n"

        "*3. Transfer Antar Rekening*\n"
        "`transfer gopay 200rb dari BRI`\n"
        "`top up dana dari bri 500rb`\n"
        "`isi GoPay 100k dari Cash`\n\n"

        "*4. Multi Input*\n"
        "Bisa tulis beberapa transaksi dalam satu pesan, dipisah enter, titik koma, atau kalimat natural.\n"
        "Contoh:\n"
        "`beli kopi 10k`\n"
        "`beli nasi 20k`\n"
        "`Akmal bayar hutang 20k kemarin`\n\n"
        "Contoh satu baris:\n"
        "`beli kopi 10k; beli nasi 20k; Budi minjem 50k`\n"
        "`beli kopi 10k minjem Joko 50k`\n\n"

        "*5. Rekening Opsional untuk Data Historis*\n"
        "Kalau transaksi sudah berlalu dan Anda tidak mau mengubah saldo rekening, pilih tombol:\n"
        "`Sudah berlalu / jangan ubah saldo`\n"
        "Contoh:\n"
        "`Beli tissue 10k dibagi 4 sama Sapto Opik Alpat`\n"
        "Debt/split bill tetap tercatat, tapi saldo rekening tidak berubah.\n\n"

        "*B. Utang, Piutang, Split Bill*\n\n"
        "*6. Utang/Piutang Biasa*\n"
        "`hutang ke Budi 500rb` — Anda punya utang ke Budi\n"
        "`minjem uang Annisa 220k` — Anda punya utang ke Annisa\n"
        "`Budi minjem 300rb` — Budi punya utang ke Anda / piutang Anda\n"
        "`piutang ke Akmal 31100` — Akmal punya utang ke Anda\n"
        "`saya berutang ke Akmal 20k` — Anda punya utang ke Akmal\n"
        "`Akmal berutang 50k` — piutang Anda ke Akmal\n"
        "`Budi bayar 100rb` — pembayaran piutang dari Budi\n"
        "`bayar hutang Budi 100rb` — pembayaran utang Anda ke Budi\n\n"

        "*7. Talangin / Ditalangin*\n"
        "`saya talangin Sapto beli nasi kuning 12k` — uang Anda keluar, jadi piutang Sapto\n"
        "`saya ditalangin Alpat beli nasi uduk 10k` — utang Anda ke Alpat tanpa cashflow rekening\n"
        "`saya nitip Sapto beli nasi kuning 12k` — sama seperti ditalangin\n"
        "`ditalangin nasi uduk sama Alpat 10k kemarin` — Alpat menalangi Anda\n\n"

        "*8. Split Bill*\n"
        "`Ayam dcelup 26k bagi 2 sama Sapto`\n"
        "`Beli tissue 10k dibagi 4 sama Sapto Opik Alpat`\n"
        "`Beli token 500k dibagi 4 sama Sapto:100% Opik:80% Alpat:100%`\n"
        "`Beli token 500k dibagi 4 sama Sapto 125k Opik 100k Alpat 125k`\n"
        "Tanda `:` opsional. Kalau belum dibayar, bagian teman masuk piutang.\n\n"

        "*9. Kompensasi / Potong Silang Hutang-Piutang*\n"
        "Dipakai kalau tidak ada uang keluar/masuk rekening, tapi saldo hutang-piutang berubah.\n"
        "`potong piutang Akmal 20k buat badminton`\n"
        "`kompensasi piutang Akmal 20k karena badminton`\n"
        "`saya berutang ke Akmal 20k potong dari piutang`\n"
        "Tetap masuk sheet `transactions` sebagai fact table, tapi saldo rekening tidak berubah.\n\n"

        "*10. Kelola Debt*\n"
        "`/hutang` — ringkasan utang/piutang aktif per orang\n"
        "`/hutang Annisa` — detail rincian aktif Annisa + debt ID\n"
        "`/debt_void 1` — batalkan rincian dari detail terakhir\n"
        "`/debt_void Annisa` — batalkan semua debt aktif Annisa setelah konfirmasi\n"
        "`/debt_void Annisa 1` — batalkan rincian nomor 1 milik Annisa\n"
        "`/debt_edit 1 nominal 100k` — edit nominal rincian\n"
        "`/debt_edit 1 nama Budi` — edit nama orang\n"
        "`/debt_edit 1 tipe piutang` — ubah arah debt\n"
        "Detail `/hutang nama` dikelompokkan per tanggal dibuat, menampilkan tanggal dan debt ID full.\n\n"

        "*C. Laporan, Budget, Koreksi Data*\n\n"
        "*11. Laporan*\n"
        "`/saldo` — saldo semua rekening\n"
        "`/rekening Cash` — ringkasan rekening Cash bulan ini\n"
        "`/rekening Cash 2026-06` — ringkasan rekening bulan tertentu\n"
        "`/rekening Cash all` — ringkasan seluruh histori rekening\n"
        "`/harian` — ringkasan hari ini\n"
        "`/harian 2026-06-01` — ringkasan tanggal tertentu\n"
        "`/harian Food & Beverage` — list transaksi kategori hari ini\n"
        "`/harian rekening Cash` — ringkasan hari ini khusus rekening Cash\n"
        "`/mingguan` — ringkasan minggu ini\n"
        "`/mingguan 2026-06-01` — ringkasan minggu yang memuat tanggal itu\n"
        "`/mingguan Bills & Utilities` — list transaksi kategori minggu ini\n"
        "`/mingguan rekening Dana` — ringkasan minggu ini khusus rekening Dana\n"
        "`/bulanan` — ringkasan bulan ini + insight Gemini\n"
        "`/bulanan 2026-06` — ringkasan bulan tertentu + insight Gemini\n"
        "`/bulanan Food & Beverage` — list transaksi kategori bulan ini\n"
        "`/bulanan rekening Cash` — ringkasan bulan ini khusus rekening Cash\n"
        "`/bulanan 2026-06 rekening Cash` — ringkasan rekening bulan tertentu\n"
        "`/bulanan 2026-06 Food & Beverage rekening Cash` — list kategori + rekening bulan tertentu\n"
        "Report utama menampilkan tren vs periode sebelumnya, termasuk tren per kategori. Jika periode sebelumnya belum ada data, bot tampilkan `~`.\n"
        "Nominal pengeluaran yang punya piutang aktif ditampilkan sebagai `Net (Gross)`, misalnya `Rp16.000 (Rp32.000)`.\n"
        "`/cari kopi` — cari transaksi dengan keyword kopi\n\n"

        "*12. Lihat & Koreksi Transaksi*\n"
        "`/last` — lihat 10 transaksi terakhir, urut tanggal terbaru\n"
        "`/last 20` — lihat 20 transaksi terakhir\n"
        "`/transaksi` — list transaksi bulan ini\n"
        "`/transaksi 2026-06` — list transaksi bulan tertentu\n"
        "`/transaksi bulan lalu` — list transaksi bulan sebelumnya\n"
        "`/transaksi Food & Beverage 2026-06` — list transaksi kategori bulan tertentu\n"
        "`/transaksi rekening Cash` — list transaksi Cash bulan ini\n"
        "`/transaksi rekening Cash 2026-06` — list transaksi Cash bulan tertentu\n"
        "`/transaksi rekening Cash bulan lalu` — list transaksi Cash bulan sebelumnya\n"
        "`/transaksi rekening Cash all` — seluruh transaksi Cash\n"
        "Output `/transaksi` dikelompokkan per tanggal terbaru ke terlama.\n"
        "`/last today`, `/last week`, `/last month`, `/last 2026-06`\n"
        "`/delete_txn 1`, `/delete_txn 1 3 5`, `/delete_txn 1-4`\n"
        "`/edit_txn 2 amount=15000`\n"
        "`/edit_txn 2 desc=Kopi susu`\n"
        "`/edit_txn 2 account=BRI category=Food & Beverage`\n"
        "`/edit_txn txn_id amount=500k dibagi 4 sama Sapto:125k Alpat:125k Opik:100k`\n"
        "`/edit_txn 2 bayar_hutang Sapto` — ubah transaksi jadi pembayaran utang ke Sapto\n"
        "`/edit_txn 2 bayar_piutang Sapto` — ubah transaksi jadi pembayaran piutang dari Sapto\n"
        "Jika transaksi punya `hutang_id`, `/delete_txn` akan mencoba void debt terkait otomatis.\n\n"

        "*13. Pending Expense / Rencana Pengeluaran*\n"
        "Pending expense dipakai untuk pengeluaran yang akan ada, tapi belum dibayar. Tidak mengubah saldo dan belum masuk pengeluaran aktual.\n"
        "`/pending` — lihat pending expense bulan ini\n"
        "`/pending 2026-07` — lihat pending bulan tertentu\n"
        "`/pending bulan depan` — lihat pending bulan depan\n"
        "`/pending all` — lihat semua pending aktif\n"
        "`/pending tanpa tanggal` — lihat pending yang tanggalnya belum pasti\n"
        "`/pending_add bayar wifi 285k tgl 30 dari BRI` — preview pending dengan tanggal pasti\n"
        "`pending beli token 500k` — preview pending tanpa tanggal pasti\n"
        "`rencana beli sepatu 300k bulan depan` — tambah pending dengan bulan, tanggal belum pasti\n"
        "`nanti perlu bayar wisuda 750k` — preview pending natural tanpa command\n"
        "`nanti perlu service motor 300k tgl 30` — pending natural dengan tanggal pasti\n"
        "`perlu 750k buat bayar wisuda` — pending natural tanpa tanggal pasti\n"
        "`/pending_paid pending_id BRI` — ubah pending menjadi transaksi aktual\n"
        "`/pending_cancel pending_id` — batalkan pending expense\n\n"

        "*14. Budget*\n"
        "`/budget` — lihat budget bulan berjalan\n"
        "`/budget 2026-06` — lihat budget bulan tertentu\n"
        "`/budget_history` — lihat daftar bulan yang punya budget\n"
        "`budget makan 1.5 juta` — otomatis map ke Food & Beverage\n"
        "`budget jajan 500rb` — buat budget custom Jajan\n"
        "`budget transport 300rb 2026-07` — set budget bulan tertentu\n"
        "Catatan: `/budget` memakai realisasi bersih. Jika ada split bill, output tampil sebagai Bersih (Gross).\n\n"

        "*15. Export, Recurring, Health*\n"
        "`/download_data`, `/download_data today`, `/download_data week`, `/download_data 2026-06`\n"
        "`/recurring` — lihat transaksi rutin\n"
        "`/recurring_add Netflix | expense | 65000 | Entertainment | DANA | monthly | 5 | Langganan Netflix`\n"
        "`/recurring_run`, `/recurring_edit ...`, `/recurring_off ...`\n"
        "Recurring otomatis muncul sebagai reminder dengan tombol `Sudah bayar`. Klik tombol itu untuk mencatat transaksi dan menghentikan notifikasi sampai periode berikutnya.\n"
        "`/health` — cek status bot, env, Google Sheets, dan sheet utama\n\n"

        "*D. Net Worth & Aset*\n\n"
        "*16. Net Worth*\n"
        "`/networth` — lihat kekayaan bersih dari saldo rekening + aset aktif\n"
        "`/networth_snapshot` — simpan snapshot net worth hari ini\n"
        "`/networth_history` — lihat riwayat snapshot\n\n"

        "*17. Aset*\n"
        "`/assets` — lihat daftar aset aktif\n"
        "`/asset_add` — tambah aset mode tanya-jawab/guided input\n"
        "Format lama tetap bisa dipakai:\n"
        "`/asset_add Laptop | 8000000 | Electronics | Laptop kerja`\n"
        "`/asset_add Emas Antam | 41 gram | Gold | Tabungan emas | harga_beli=2559000 | tanggal_beli=2026-06-10`\n"
        "Dalam mode guided, bot akan tanya nama aset, jumlah/unit, harga beli, tanggal beli, harga saat ini, kategori, dan deskripsi.\n"
        "Tanggal beli boleh dikosongkan dengan mengetik `lewati`, `kosong`, atau `-`.\n"
        "Setiap step punya tombol `Batal`.\n"
        "`/asset_update asset_id | unit_price=2420000`\n"
        "`/asset_update asset_id | harga_beli=2559000 | tanggal_beli=2026-06-10`\n"
        "`/asset_update asset_id | value=9000000`\n"
        "`/asset_off asset_id`\n\n"

        "*E. Input Gambar & Analisis Gemini/RAG*\n\n"
        "*18. Input Gambar / Struk*\n"
        "Kirim foto struk, nota, QRIS, atau screenshot transaksi.\n"
        "Bot membaca gambar dengan Gemini, lalu menampilkan preview sebelum disimpan.\n"
        "Caption opsional: `pakai BSI`, `ini pemasukan`, `total aja`.\n\n"

        "*19. Analisis Gemini / RAG Finance*\n"
        "Bagian ini read-only: bot mengambil data relevan dari Google Sheets, menghitung angka pakai Python, lalu Gemini menjelaskan insight.\n"
        "`/insight` — monthly narrative report bulan ini\n"
        "`/insight 2026-06` — insight bulan tertentu\n"
        "`/ask bulan ini boros di mana?` — tanya jawab finansial natural\n"
        "`/ask kapan terakhir saya beli kopi?` — tanya transaksi spesifik\n"
        "`/ask budget makan aman gak?` — budget assistant\n"
        "`/audit` — deteksi anomali + data quality checker\n"
        "`/coach` — financial coach ringan\n"
        "`/coach gimana biar nabung 2 juta?`\n\n"

        "Contoh pertanyaan natural tanpa command:\n"
        "`bulan ini boros di mana?`\n"
        "`ada transaksi aneh bulan ini?`\n"
        "`budget saya aman gak?`\n"
        "`kasih saran pengeluaran bulan ini`\n\n"

        "*Catatan penting:*\n"
        "• Fitur inti mengubah data, fitur Gemini/RAG hanya membaca dan memberi insight.\n"
        "• Sheet `transactions` dipakai sebagai fact table utama, termasuk debt-only dan debt offset.\n"
        "• Untuk `/delete_txn` dan `/edit_txn`, jalankan `/last` dulu.\n"
        "• Data yang dikirim ke Gemini adalah ringkasan relevan, bukan seluruh spreadsheet mentah.\n"
        "• `/ask` memakai session history terbatas agar paham pertanyaan lanjutan; history hilang jika bot restart."
    )

    await reply_long_markdown(update, text)


def add_session_chat_history(context: ContextTypes.DEFAULT_TYPE, role: str, text: str, limit: int = 10):
    """Simpan riwayat tanya-jawab finance di session Telegram user.

    Catatan:
    - Tidak persistent; hilang jika bot restart/redeploy.
    - Dipakai hanya sebagai konteks percakapan untuk /ask/natural finance question.
    - Angka faktual tetap harus berasal dari context Google Sheets, bukan dari history.
    """
    if context is None:
        return

    clean_text = str(text or "").strip()
    if not clean_text:
        return

    history = context.user_data.get("finance_chat_history", [])
    history.append({
        "role": str(role or "user"),
        "text": clean_text[:1200],
    })
    context.user_data["finance_chat_history"] = history[-limit:]


def get_session_chat_history(context: ContextTypes.DEFAULT_TYPE, limit: int = 8) -> list[dict]:
    """Ambil beberapa pesan terakhir untuk membantu /ask memahami konteks lanjutan."""
    if context is None:
        return []
    history = context.user_data.get("finance_chat_history", [])
    return history[-limit:]


def attach_session_history(context: ContextTypes.DEFAULT_TYPE, context_data: dict) -> dict:
    """Tambahkan chat history session ke context JSON yang dikirim ke Gemini."""
    data = dict(context_data or {})
    history = get_session_chat_history(context)
    if history:
        data["chat_history"] = history
        data["chat_history_note"] = (
            "Riwayat ini hanya untuk memahami konteks pertanyaan lanjutan. "
            "Jangan jadikan chat_history sebagai sumber angka utama; angka faktual harus dari monthly_context/relevant_transactions."
        )
    return data


async def send_finance_insight_reply(
    update: Update,
    mode: str,
    context_data: dict,
    question: str = "",
    prefix: str = "🤖 Insight Gemini",
    context: ContextTypes.DEFAULT_TYPE | None = None,
    remember_history: bool = False,
):
    await update.message.reply_text("⏳ Mengambil data dan membuat insight...")
    answer = generate_finance_insight(mode, context_data, question=question)

    if remember_history and context is not None:
        add_session_chat_history(context, "user", question)
        add_session_chat_history(context, "assistant", answer)

    await update.message.reply_text(f"{prefix}\n\n{answer}")


async def insight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/insight [YYYY-MM] — monthly narrative report."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    month_arg = " ".join(context.args).strip() if context.args else None
    month = normalize_insight_month(month_arg)
    data = build_monthly_finance_context(month)
    await send_finance_insight_reply(
        update,
        "monthly_insight",
        data,
        question=f"Buat insight/narasi keuangan untuk {month}",
        prefix=f"📌 Insight Finance {month}",
    )


async def audit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/audit [YYYY-MM] — cek data quality dan anomali."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    month_arg = " ".join(context.args).strip() if context.args else None
    month = normalize_insight_month(month_arg)
    data = build_audit_context(month)
    await send_finance_insight_reply(
        update,
        "audit",
        data,
        question=f"Audit data finance dan anomali untuk {month}",
        prefix=f"🧹 Audit Finance {month}",
    )


async def ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ask <pertanyaan> — tanya jawab finansial natural."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    question = " ".join(context.args).strip()
    if not question:
        await update.message.reply_text(
            "❌ Tulis pertanyaannya setelah `/ask`.\n\n"
            "Contoh:\n"
            "`/ask bulan ini boros di mana?`\n"
            "`/ask kapan terakhir saya beli kopi?`\n"
            "`/ask budget makan aman gak?`",
            parse_mode="Markdown",
        )
        return

    mode = route_finance_question_mode(question)
    if mode == "audit":
        data = build_audit_context(None)
    elif mode == "coach":
        data = build_coach_context(None, question=question)
    else:
        data = build_ask_finance_context(question)

    data = attach_session_history(context, data)
    await send_finance_insight_reply(
        update,
        mode,
        data,
        question=question,
        prefix="💬 Jawaban Finance",
        context=context,
        remember_history=True,
    )


async def coach_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/coach [pertanyaan] — financial coach ringan."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    question = " ".join(context.args).strip() if context.args else "Kasih saran finansial ringan untuk bulan ini."
    data = build_coach_context(None, question=question)
    data = attach_session_history(context, data)
    await send_finance_insight_reply(
        update,
        "coach",
        data,
        question=question,
        prefix="🧭 Finance Coach",
        context=context,
        remember_history=True,
    )


async def handle_natural_finance_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Handle pertanyaan finance natural tanpa command, read-only."""
    if not should_handle_finance_question(user_text):
        return False

    mode = route_finance_question_mode(user_text)
    if mode == "audit":
        data = build_audit_context(None)
    elif mode == "coach":
        data = build_coach_context(None, question=user_text)
    else:
        data = build_ask_finance_context(user_text)

    data = attach_session_history(context, data)
    await send_finance_insight_reply(
        update,
        mode,
        data,
        question=user_text,
        prefix="🤖 Analisis Finance",
        context=context,
        remember_history=True,
    )
    return True


def format_report_delta(delta_info: dict, *, positive_when_up: bool, as_count: bool = False) -> str:
    """Format delta vs periode sebelumnya dengan indikator hijau/merah berbasis emoji."""
    if not delta_info or delta_info.get("available") is False or delta_info.get("delta") is None:
        return "~"

    delta = float(delta_info.get("delta", 0) or 0)
    pct = delta_info.get("pct")

    if abs(delta) < 0.0001:
        value_text = "0 item" if as_count else format_rupiah(0)
        return f"⚪= {value_text}"

    arrow = "▲" if delta > 0 else "▼"
    is_good = (delta > 0) if positive_when_up else (delta < 0)
    color = "🟢" if is_good else "🔴"
    sign = "+" if delta > 0 else "-"

    if as_count:
        value_text = f"{sign}{abs(int(round(delta)))} item"
    else:
        value_text = f"{sign}{format_rupiah(abs(delta))}"

    pct_text = ""
    if pct is not None:
        pct_text = f" ({pct:+.1f}%)"

    return f"{color}{arrow} {value_text}{pct_text}"


def append_report_comparison_lines(lines: list[str], report: dict, label: str):
    comparison = (report or {}).get("comparison") or {}
    if not comparison:
        return

    lines.append(f"📈 Vs {label}:")
    lines.append(f"   ✅ Pemasukan : {format_report_delta(comparison.get('total_income'), positive_when_up=True)}")
    lines.append(f"   ❌ Pengeluaran: {format_report_delta(comparison.get('total_expense'), positive_when_up=False)}")
    lines.append(f"   📊 Net       : {format_report_delta(comparison.get('net'), positive_when_up=True)}")
    lines.append(f"   📝 Transaksi : {format_report_delta(comparison.get('count'), positive_when_up=False, as_count=True)}\n")


def get_report_expense_display(report: dict) -> str:
    """Format total expense report sebagai Net (Gross) jika ada piutang aktif."""
    gross = float((report or {}).get("total_expense", 0) or 0)
    net = (report or {}).get("total_net_expense_after_receivable")
    if net is None:
        net = gross
    return format_expense_net_gross(float(net or 0), gross)


def append_report_metric_lines(lines: list[str], report: dict):
    """Tambahkan metrik ringkasan; jika filter rekening aktif, transfer dihitung masuk/keluar."""
    account_filter = (report or {}).get("account_filter")
    if account_filter:
        lines.append(f"🏦 Rekening : *{md_safe(account_filter)}*")
        category_filter = (report or {}).get("category_filter")
        if category_filter:
            lines.append(f"📁 Kategori : *{md_safe(category_filter)}*")
        lines.append(f"✅ Pemasukan      : *{format_rupiah(report.get('total_income', 0))}*")
        lines.append(f"❌ Pengeluaran    : *{get_report_expense_display(report)}*")
        lines.append(f"🔁 Transfer Masuk : *{format_rupiah(report.get('total_transfer_in', 0))}*")
        lines.append(f"🔁 Transfer Keluar: *{format_rupiah(report.get('total_transfer_out', 0))}*")
        lines.append(f"📊 Net Rekening   : *{format_rupiah(report.get('net', 0))}*")
        lines.append(f"📝 Transaksi      : {report.get('count', 0)} item")
        return

    lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
    lines.append(f"❌ Pengeluaran: *{get_report_expense_display(report)}*")
    lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
    lines.append(f"📝 Transaksi : {report['count']} item")


def append_account_report_lines(lines: list[str], report: dict):
    account = (report or {}).get("account_filter") or "-"
    balance = (report or {}).get("account_balance")
    lines.append(f"🏦 Rekening : *{md_safe(account)}*")
    if balance is not None:
        lines.append(f"💰 Saldo Saat Ini : *{format_rupiah(balance)}*")
    lines.append(f"✅ Pemasukan      : *{format_rupiah(report.get('total_income', 0))}*")
    lines.append(f"❌ Pengeluaran    : *{get_report_expense_display(report)}*")
    lines.append(f"🔁 Transfer Masuk : *{format_rupiah(report.get('total_transfer_in', 0))}*")
    lines.append(f"🔁 Transfer Keluar: *{format_rupiah(report.get('total_transfer_out', 0))}*")
    lines.append(f"📊 Pergerakan Bersih: *{format_rupiah(report.get('net', 0))}*")
    lines.append(f"📝 Transaksi      : {report.get('count', 0)} item")


def append_recent_account_transaction_lines(lines: list[str], report: dict, limit: int = 8):
    transactions = (report or {}).get("transactions") or []
    if not transactions:
        return

    lines.append("\n*Transaksi Terbaru Rekening:*")
    for i, txn in enumerate(transactions[:limit], 1):
        lines.extend(build_transaction_display_lines(txn, index=i, include_date=True, include_id=True))

def append_report_category_breakdown_lines(lines: list[str], report: dict, comparison_label: str):
    by_category = (report or {}).get("by_category") or {}
    if not by_category:
        return

    lines.append("*Pengeluaran per Kategori:*")
    total_expense = float((report or {}).get("total_expense", 0) or 0)
    category_comparison = (report or {}).get("category_comparison") or {}
    by_category_net = (report or {}).get("by_category_net") or {}

    for cat, amount in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        pct = (float(amount) / total_expense) * 100 if total_expense else 0
        bar = build_progress_bar(pct)
        trend = format_report_delta(category_comparison.get(cat), positive_when_up=False)
        trend_text = f" | vs {comparison_label}: {trend}" if comparison_label else ""
        net_amount = by_category_net.get(cat, amount)
        amount_text = format_expense_net_gross(float(net_amount or 0), float(amount or 0))
        lines.append(
            f"  • {md_safe(cat)}: *{amount_text}*\n"
            f"    {bar} {pct:.1f}%{trend_text}"
        )


def build_top_expense_debt_lines(txn: dict, amount: float) -> list[str]:
    """Compatibility wrapper. Detail debt sekarang diformat oleh build_transaction_display_lines."""
    return []

def is_category_detail_report(report: dict) -> bool:
    return bool((report or {}).get("category_filter"))


def get_category_list_title(category: str) -> str:
    category_lower = str(category or "").strip().lower()
    if category_lower == "food & beverage":
        return "🍽 *Daftar Makanan/Minuman:*"
    return f"📋 *Daftar Transaksi {md_safe(category)}:*"


def append_category_detail_summary(lines: list[str], report: dict, comparison_label: str):
    category = (report or {}).get("category_filter") or "-"
    account = (report or {}).get("account_filter")
    total_income = float((report or {}).get("total_income", 0) or 0)
    total_expense = float((report or {}).get("total_expense", 0) or 0)
    total_transfer = float((report or {}).get("total_transfer", 0) or 0)

    lines.append(f"📁 Kategori : *{md_safe(category)}*")
    if account:
        lines.append(f"🏦 Rekening : *{md_safe(account)}*")
    if total_income > 0:
        lines.append(f"✅ Pemasukan : *{format_rupiah(total_income)}*")
    if total_expense > 0 or total_income == 0:
        lines.append(f"❌ Pengeluaran: *{get_report_expense_display(report)}*")
    if account:
        transfer_in = float((report or {}).get("total_transfer_in", 0) or 0)
        transfer_out = float((report or {}).get("total_transfer_out", 0) or 0)
        if transfer_in > 0:
            lines.append(f"🔁 Transfer Masuk : *{format_rupiah(transfer_in)}*")
        if transfer_out > 0:
            lines.append(f"🔁 Transfer Keluar: *{format_rupiah(transfer_out)}*")
    elif total_transfer > 0:
        lines.append(f"🔄 Transfer   : *{format_rupiah(total_transfer)}*")
    if total_income > 0 and total_expense > 0:
        lines.append(f"📊 Net       : *{format_rupiah((report or {}).get('net', 0))}*")
    lines.append(f"📝 Transaksi : {(report or {}).get('count', 0)} item")
    append_report_comparison_lines(lines, report, comparison_label)


def append_category_transaction_lines(lines: list[str], report: dict, *, include_date: bool):
    category = (report or {}).get("category_filter") or "-"
    transactions = (report or {}).get("transactions") or []
    if not transactions:
        return

    lines.append(get_category_list_title(category))

    for i, t in enumerate(transactions, 1):
        note = str(t.get("catatan", "") or "").strip()
        lines.extend(
            build_transaction_display_lines(
                t,
                index=i,
                include_date=include_date,
                include_id=True,
                note=note or None,
            )
        )



async def saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    accounts = get_all_accounts()
    if not accounts:
        await update.message.reply_text("❌ Tidak ada data rekening.")
        return

    total = sum(float(acc.get("balance", 0) or 0) for acc in accounts)
    lines = ["💰 *Saldo Rekening*\n"]

    emoji_map = {
        "cash": "💵",
        "bank": "🏦",
        "ewallet": "📱",
    }

    for acc in accounts:
        emoji = emoji_map.get(str(acc.get("type", "")).lower(), "💳")
        name = acc.get("account_name", "")
        balance = float(acc.get("balance", 0) or 0)
        lines.append(f"{emoji} {name}: *{format_rupiah(balance)}*")

    lines.append(f"\n📊 Total: *{format_rupiah(total)}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def rekening_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /rekening
    /rekening Cash
    /rekening Cash 2026-06
    /rekening Cash all
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    raw_arg = " ".join(context.args).strip() if context.args else ""

    # Tanpa argumen, jadikan alias yang lebih informatif untuk /saldo.
    if not raw_arg:
        await saldo_handler(update, context)
        return

    account_arg, period_arg = split_account_period_arg(raw_arg)
    if not account_arg:
        await saldo_handler(update, context)
        return

    try:
        report = get_account_report(account_arg, period_arg)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/rekening Cash`\n"
            "`/rekening Dana 2026-06`\n"
            "`/rekening BCA all`",
            parse_mode="Markdown",
        )
        return

    account = report.get("account_filter") or account_arg
    period_label = report.get("period_label") or report.get("month") or "-"

    if report.get("count", 0) == 0:
        lines = [
            f"🏦 *Ringkasan Rekening*\n_{md_safe(period_label)}_\n",
            f"🏦 Rekening : *{md_safe(account)}*",
        ]
        balance = report.get("account_balance")
        if balance is not None:
            lines.append(f"💰 Saldo Saat Ini : *{format_rupiah(balance)}*")
        lines.append("📭 Belum ada transaksi rekening ini pada periode tersebut.")
        await reply_long_markdown(update, "\n".join(lines))
        return

    lines = [f"🏦 *Ringkasan Rekening*\n_{md_safe(period_label)}_\n"]
    append_net_gross_note(lines, report.get("transactions"))
    append_account_report_lines(lines, report)
    category_compare_label = "bulan lalu" if report.get("period_type") != "all" else None
    append_report_category_breakdown_lines(lines, report, category_compare_label)
    append_recent_account_transaction_lines(lines, report)

    await reply_long_markdown(update, "\n".join(lines))


async def harian_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    raw_arg = " ".join(context.args).strip() if context.args else None
    date_arg, category_arg, account_arg = split_report_filter_args(raw_arg, "date")

    try:
        report = get_daily_report(date_arg, category_arg, account_arg)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/harian`\n"
            "`/harian 2026-06-01`\n"
            "`/harian 01-06-2026`\n"
            "`/harian 1`\n"
            "`/harian Food & Beverage`\n"
            "`/harian rekening Cash`\n"
            "`/harian 2026-06-01 rekening Cash`\n"
            "`/harian 2026-06-01 Food & Beverage rekening Cash`",
            parse_mode="Markdown",
        )
        return

    date_str = report["date"]
    category_filter = report.get("category_filter")
    account_filter = report.get("account_filter")

    if report["count"] == 0:
        if category_filter or account_filter:
            filter_bits = []
            if category_filter:
                filter_bits.append(f"kategori *{md_safe(category_filter)}*")
            if account_filter:
                filter_bits.append(f"rekening *{md_safe(account_filter)}*")
            await update.message.reply_text(
                f"📭 Tidak ada transaksi {' dan '.join(filter_bits)} pada {date_str}.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(f"📭 Belum ada transaksi hari ini ({date_str}).")
        return

    if is_category_detail_report(report):
        lines = [f"📅 *Detail Harian*\n_{date_str}_\n"]
        append_net_gross_note(lines, report.get("transactions"))
        append_category_detail_summary(lines, report, "hari sebelumnya")
        append_category_transaction_lines(lines, report, include_date=False)
        await reply_long_markdown(update, "\n".join(lines))
        return

    lines = [f"📅 *Ringkasan Harian*\n_{date_str}_\n"]
    append_net_gross_note(lines, report.get("transactions"))
    append_report_metric_lines(lines, report)
    append_report_comparison_lines(lines, report, "hari sebelumnya")

    append_report_category_breakdown_lines(lines, report, "hari sebelumnya")

    top = sorted(
        [t for t in report.get("transactions", []) if t.get("type") == "expense"],
        key=lambda x: float(x.get("amount", 0) or 0),
        reverse=True,
    )[:3]

    if top:
        lines.append("\n*Top 3 Pengeluaran:*")
        total_expense = float(report["total_expense"] or 0)

        for i, t in enumerate(top, 1):
            amount = float(t.get("amount", 0) or 0)
            contrib = (amount / total_expense * 100) if total_expense else 0

            lines.extend(
                build_transaction_display_lines(
                    t,
                    index=i,
                    include_date=True,
                    include_id=True,
                    contribution_pct=contrib,
                )
            )

    await reply_long_markdown(update, "\n".join(lines))


async def mingguan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    raw_arg = " ".join(context.args).strip() if context.args else None
    date_arg, category_arg, account_arg = split_report_filter_args(raw_arg, "date")

    try:
        report = get_weekly_report(date_arg, category_arg, account_arg)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/mingguan`\n"
            "`/mingguan 2026-06-01`\n"
            "`/mingguan 1`\n"
            "`/mingguan Food & Beverage`\n"
            "`/mingguan rekening Dana`\n"
            "`/mingguan 2026-06-01 rekening Dana`\n"
            "`/mingguan 2026-06-01 Bills & Utilities rekening Dana`",
            parse_mode="Markdown",
        )
        return

    category_filter = report.get("category_filter")
    account_filter = report.get("account_filter")

    if report["count"] == 0:
        if category_filter or account_filter:
            filter_bits = []
            if category_filter:
                filter_bits.append(f"kategori *{md_safe(category_filter)}*")
            if account_filter:
                filter_bits.append(f"rekening *{md_safe(account_filter)}*")
            await update.message.reply_text(
                f"📭 Tidak ada transaksi {' dan '.join(filter_bits)} minggu ini.\n"
                f"({report['date_from']} s/d {report['date_to']})",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"📭 Belum ada transaksi minggu ini.\n"
                f"({report['date_from']} s/d {report['date_to']})"
            )
        return

    if is_category_detail_report(report):
        lines = [
            f"📆 *Detail Mingguan*\n"
            f"_{report['date_from']} s/d {report['date_to']}_\n"
        ]
        append_net_gross_note(lines, report.get("transactions"))
        append_category_detail_summary(lines, report, "minggu sebelumnya")
        append_category_transaction_lines(lines, report, include_date=True)
        await reply_long_markdown(update, "\n".join(lines))
        return

    lines = [
        f"📆 *Ringkasan Mingguan*\n"
        f"_{report['date_from']} s/d {report['date_to']}_\n"
    ]
    append_net_gross_note(lines, report.get("transactions"))
    append_report_metric_lines(lines, report)
    append_report_comparison_lines(lines, report, "minggu sebelumnya")

    append_report_category_breakdown_lines(lines, report, "minggu sebelumnya")

    top = sorted(
        [t for t in report.get("transactions", []) if t.get("type") == "expense"],
        key=lambda x: float(x.get("amount", 0) or 0),
        reverse=True,
    )[:3]

    if top:
        lines.append("\n*Top 3 Pengeluaran:*")
        total_expense = float(report["total_expense"] or 0)

        for i, t in enumerate(top, 1):
            amount = float(t.get("amount", 0) or 0)
            contrib = (amount / total_expense * 100) if total_expense else 0

            lines.extend(
                build_transaction_display_lines(
                    t,
                    index=i,
                    include_date=True,
                    include_id=True,
                    contribution_pct=contrib,
                )
            )

    await reply_long_markdown(update, "\n".join(lines))


async def bulanan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    raw_arg = " ".join(context.args).strip() if context.args else None
    month_arg, category_arg, account_arg = split_report_filter_args(raw_arg, "month")

    try:
        year, month_num = parse_report_month_arg(month_arg)
        report = get_monthly_report(year, month_num, category_arg, account_arg)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/bulanan`\n"
            "`/bulanan 2026-06`\n"
            "`/bulanan 6`\n"
            "`/bulanan Food & Beverage`\n"
            "`/bulanan rekening Cash`\n"
            "`/bulanan 2026-06 rekening Cash`\n"
            "`/bulanan 2026-06 Food & Beverage rekening Cash`",
            parse_mode="Markdown",
        )
        return

    month_name = report.get("month", "-")
    category_filter = report.get("category_filter")
    account_filter = report.get("account_filter")

    if report["count"] == 0:
        if category_filter or account_filter:
            filter_bits = []
            if category_filter:
                filter_bits.append(f"kategori *{md_safe(category_filter)}*")
            if account_filter:
                filter_bits.append(f"rekening *{md_safe(account_filter)}*")
            await update.message.reply_text(
                f"📭 Tidak ada transaksi {' dan '.join(filter_bits)} pada {month_name}.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("📭 Belum ada transaksi bulan ini.")
        return

    if is_category_detail_report(report):
        lines = [f"📆 *Detail Bulanan*\n_{month_name}_\n"]
        append_net_gross_note(lines, report.get("transactions"))
        append_category_detail_summary(lines, report, "bulan lalu")
        append_category_transaction_lines(lines, report, include_date=True)
        await reply_long_markdown(update, "\n".join(lines))
        return

    lines = [f"📆 *Ringkasan Bulanan*\n_{month_name}_\n"]
    append_net_gross_note(lines, report.get("transactions"))
    append_report_metric_lines(lines, report)
    append_report_comparison_lines(lines, report, "bulan lalu")

    append_report_category_breakdown_lines(lines, report, "bulan lalu")

    top = sorted(
        [t for t in report.get("transactions", []) if t.get("type") == "expense"],
        key=lambda x: float(x.get("amount", 0) or 0),
        reverse=True,
    )[:3]

    if top:
        lines.append("\n*Top 3 Pengeluaran:*")
        total_expense = float(report["total_expense"] or 0)

        for i, t in enumerate(top, 1):
            amount = float(t.get("amount", 0) or 0)
            contrib = (amount / total_expense * 100) if total_expense else 0

            lines.extend(
                build_transaction_display_lines(
                    t,
                    index=i,
                    include_date=True,
                    include_id=True,
                    contribution_pct=contrib,
                )
            )

    budget_summary = get_budget_summary(month_name)
    if budget_summary:
        lines.append("\n*Budget vs Realisasi:*")
        for item in budget_summary:
            bar = build_progress_bar(item["pct_used"])
            lines.append(
                f"{item['emoji']} {item['category']}\n"
                f"  {bar} {item['pct_used']}%"
            )

    await reply_long_markdown(update, "\n".join(lines))

    # Insight otomatis setelah /bulanan.
    # Dikirim sebagai pesan terpisah tanpa parse_mode agar output Gemini tidak merusak Markdown Telegram.
    try:
        insight_data = build_monthly_finance_context(month_name)
        insight_text = generate_finance_insight(
            "monthly_auto",
            insight_data,
            question=f"Buat insight singkat otomatis setelah laporan bulanan {month_name}",
        )
        await update.message.reply_text(f"🤖 Insight Bulanan Gemini\n\n{insight_text}")
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Ringkasan bulanan berhasil, tapi insight Gemini gagal dibuat: {str(e)}"
        )


async def cari_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "🔍 Masukkan keyword pencarian.\n"
            "Contoh: `/cari kopi`",
            parse_mode="Markdown",
        )
        return

    keyword = " ".join(args)
    results = search_transactions(keyword)

    if not results:
        await update.message.reply_text(
            f"🔍 Tidak ada transaksi dengan keyword *{md_safe(keyword)}*.",
            parse_mode="Markdown",
        )
        return

    lines = [f"🔍 *Hasil pencarian: \"{md_safe(keyword)}\"*\n"]
    append_net_gross_note(lines, results)

    for i, t in enumerate(results, 1):
        lines.extend(build_transaction_display_lines(t, index=i, include_date=True, include_id=True))

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def format_budget_net_gross(net_amount: float, gross_amount: float) -> str:
    """Format budget realisasi sebagai Bersih (Gross)."""
    net = float(net_amount or 0)
    gross = float(gross_amount or 0)
    if abs(net - gross) > 0.0001:
        return f"{format_rupiah(net)} ({format_rupiah(gross)})"
    return format_rupiah(net)

async def budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /budget
    /budget 2026-06
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    month_arg = context.args[0] if context.args else None

    try:
        month = normalize_month(month_arg)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/budget`\n"
            "`/budget 2026-06`",
            parse_mode="Markdown",
        )
        return

    summary = get_budget_summary(month)

    if not summary:
        await update.message.reply_text(
            f"📭 Belum ada budget untuk *{format_month_label(month)}*.\n\n"
            "Set budget dengan cara:\n"
            "`budget makan 1.5 juta`\n"
            "`budget transport 300rb`\n"
            "`budget makan 1.5 juta 2026-07`\n\n"
            "Lihat histori bulan yang tersedia:\n"
            "`/budget_history`",
            parse_mode="Markdown",
        )
        return

    total_budget = sum(float(item.get("budget", 0) or 0) for item in summary)
    total_actual = sum(float(item.get("actual", 0) or 0) for item in summary)
    total_gross_actual = sum(float(item.get("actual_gross", item.get("actual", 0)) or 0) for item in summary)
    total_remaining = total_budget - total_actual
    total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0

    lines = [f"📊 *Budget {format_month_label(month)}*\n"]

    lines.append(f"💰 Total Budget : *{format_rupiah(total_budget)}*")
    lines.append(f"💸 Realisasi Bersih (Gross): *{format_budget_net_gross(total_actual, total_gross_actual)}*")
    lines.append(f"📌 Sisa         : *{format_rupiah(total_remaining)}*")
    lines.append(f"📈 Terpakai     : *{total_pct:.1f}%*\n")

    for item in summary:
        bar = build_progress_bar(item["pct_used"])
        remaining_label = "Sisa" if item["remaining"] >= 0 else "Over"

        lines.append(
            f"{item['emoji']} *{item['category']}*\n"
            f"  {bar} {item['pct_used']}%\n"
            f"  Pakai Bersih (Gross): {format_budget_net_gross(item.get('actual', 0), item.get('actual_gross', item.get('actual', 0)))} / {format_rupiah(item['budget'])}\n"
            f"  {remaining_label}: {format_rupiah(abs(item['remaining']))}\n"
        )

    lines.append(
        "Cek bulan lain:\n"
        f"`/budget {month}`"
    )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def budget_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /budget_history
    Tampilkan daftar bulan yang punya budget.
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    months = get_budget_months()

    if not months:
        await update.message.reply_text(
            "📭 Belum ada histori budget.\n\n"
            "Set budget dulu, contoh:\n"
            "`budget makan 1.5 juta`\n"
            "`budget makan 2 juta 2026-07`",
            parse_mode="Markdown",
        )
        return

    lines = ["🗂️ *Histori Budget Tersedia*\n"]

    for month in sorted(months, reverse=True):
        try:
            label = format_month_label(month)
        except Exception:
            label = month

        lines.append(f"• `{month}` — {label}")

    lines.append(
        "\nLihat detail dengan:\n"
        "`/budget 2026-06`"
    )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

def build_pending_expense_lines(items: list[dict], title: str, total: float | None = None) -> list[str]:
    lines = [f"🕒 *{md_safe(title)}*\n"]

    if not items:
        lines.append(
            "📭 Belum ada pending expense aktif.\n\n"
            "Tambah dengan:\n"
            "`/pending_add bayar wifi 285k tgl 30 dari BRI`\n"
            "`pending beli token 500k`\n"
            "`rencana beli sepatu 300k bulan depan`\n"
            "`nanti perlu bayar wisuda 750k`\n"
            "`perlu 750k buat bayar wisuda`"
        )
        return lines

    if total is None:
        total = sum(float(item.get("amount", 0) or 0) for item in items)

    lines.append(f"💰 Total pending: *{format_rupiah(total)}*")
    lines.append(f"📝 Item: {len(items)}\n")

    for i, item in enumerate(items, 1):
        due_date = str(item.get("due_date", "") or "").strip()
        due_precision = str(item.get("due_precision", "") or "unknown").strip().lower()
        month = str(item.get("month", "") or "-").strip()

        if due_date:
            due_text = due_date
        elif due_precision == "month":
            due_text = f"{month} (tanggal belum pasti)"
        else:
            due_text = "Belum pasti"

        account = str(item.get("account", "") or "-").strip() or "-"
        category = str(item.get("category", "") or "Other Expense").strip()
        status = str(item.get("status", "pending") or "pending").strip()
        subject = str(item.get("subject", "Pending Expense") or "Pending Expense").strip()
        amount = float(item.get("amount", 0) or 0)
        pending_id = str(item.get("id", "") or "").strip()

        lines.append(
            f"{i}. 🕒 *{md_safe(subject)}*\n"
            f"   📅 {md_safe(due_text)} | 💰 *{format_rupiah(amount)}* | {md_safe(category)} | 🏦 {md_safe(account)}\n"
            f"   Status: `{md_safe(status)}`\n"
            f"   🔖 `{md_code_text(pending_id)}`"
        )

    lines.append(
        "\nTandai sudah dibayar:\n"
        "`/pending_paid pending_id BRI`\n"
        "Batalkan:\n"
        "`/pending_cancel pending_id`"
    )
    return lines


async def pending_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /pending [YYYY-MM|bulan ini|bulan lalu|bulan depan|all|tanpa tanggal]
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    period = " ".join(context.args).strip() if context.args else None

    try:
        result = get_pending_expenses(period=period, active_only=True)
    except Exception as e:
        await update.message.reply_text(
            f"❌ Gagal membaca pending expense: {md_safe(str(e))}",
            parse_mode="Markdown",
        )
        return

    label = result.get("label") or "bulan ini"
    title = f"Pending Expense — {label}"
    lines = build_pending_expense_lines(result.get("items") or [], title, result.get("total", 0))
    await reply_long_markdown(update, "\n".join(lines))


async def pending_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /pending_add bayar wifi 285k tgl 30 dari BRI
    Bisa juga dipanggil dari MessageHandler regex: pending/rencana ...
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    raw_text = update.message.text.strip()
    if raw_text.lower().startswith("/pending_add"):
        raw_text = re.sub(r"^/pending_add(?:@\w+)?\s*", "", raw_text, flags=re.IGNORECASE).strip()
    elif raw_text.lower().startswith("/rencana"):
        raw_text = re.sub(r"^/rencana(?:@\w+)?\s*", "", raw_text, flags=re.IGNORECASE).strip()

    if not raw_text:
        await update.message.reply_text(
            "❌ Tulis pending expense-nya.\n\n"
            "Contoh:\n"
            "`/pending_add bayar wifi 285k tgl 30 dari BRI`\n"
            "`/pending_add beli token 500k`\n"
            "`rencana beli sepatu 300k bulan depan`\n"
            "`nanti perlu bayar wisuda 750k`\n"
            "`perlu 750k buat bayar wisuda`",
            parse_mode="Markdown",
        )
        return

    try:
        item = build_pending_expense_from_text(raw_text)
    except Exception as e:
        await update.message.reply_text(
            f"❌ Gagal membaca pending expense: {md_safe(str(e))}\n\n"
            "Contoh:\n"
            "`/pending_add bayar wifi 285k tgl 30 dari BRI`\n"
            "`pending beli token 500k`\n"
            "`nanti perlu bayar wisuda 750k`\n"
            "`perlu 750k buat bayar wisuda`",
            parse_mode="Markdown",
        )
        return

    context.user_data["pending_expense_confirm"] = item
    lines = ["🕒 *Preview Pending Expense*\n"]
    lines.extend(build_pending_expense_lines([item], "Detail Pending", float(item.get("amount", 0) or 0))[2:-1])
    lines.append(
        "\nCatatan: pending expense tidak mengubah saldo dan belum masuk pengeluaran aktual.\n"
        "Simpan pending expense ini?"
    )
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("pending_expense"),
    )


async def pending_paid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pending_paid pending_id [rekening]"""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Masukkan pending ID.\n\n"
            "Contoh:\n"
            "`/pending_paid pend_20260626_123456_xxxxxxxx BRI`",
            parse_mode="Markdown",
        )
        return

    pending_id = context.args[0].strip()
    account = context.args[1].strip() if len(context.args) >= 2 else None

    result = mark_pending_paid(pending_id, account=account)
    if not result.get("success"):
        await update.message.reply_text(
            f"❌ {md_safe(result.get('message', 'Gagal menandai pending sebagai paid.'))}",
            parse_mode="Markdown",
        )
        return

    lines = [
        "✅ *Pending expense sudah dicatat sebagai transaksi aktual.*",
        f"🔖 Transaction ID: `{md_code_text(result.get('transaction_id'))}`",
    ]
    if result.get("new_balance") is not None:
        lines.append(f"💰 Saldo baru: *{format_rupiah(result.get('new_balance'))}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def pending_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pending_cancel pending_id"""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Masukkan pending ID.\n\n"
            "Contoh:\n"
            "`/pending_cancel pend_20260626_123456_xxxxxxxx`",
            parse_mode="Markdown",
        )
        return

    result = cancel_pending_expense(context.args[0])
    if not result.get("success"):
        await update.message.reply_text(
            f"❌ {md_safe(result.get('message', 'Gagal membatalkan pending expense.'))}",
            parse_mode="Markdown",
        )
        return

    item = result.get("item") or {}
    await update.message.reply_text(
        "✅ Pending expense dibatalkan.\n"
        f"🔖 `{md_code_text(item.get('id'))}`",
        parse_mode="Markdown",
    )


def parse_amount_text(value: str) -> float:
    raw = str(value or "").strip().lower()
    raw = raw.replace(" ", "")

    multiplier = 1

    if raw.endswith(("rb", "ribu", "k")):
        multiplier = 1_000
        raw = re.sub(r"(rb|ribu|k)$", "", raw)
    elif raw.endswith(("jt", "juta", "m")):
        multiplier = 1_000_000
        raw = re.sub(r"(jt|juta|m)$", "", raw)

    raw = raw.replace(",", ".")

    try:
        return float(raw) * multiplier
    except Exception:
        return 0
    
def extract_split_bill_total_amount(raw_text: str) -> float | None:
    """
    Ambil nominal asli dari input split bill.

    Contoh:
    - Tissue 10k bagi 4 sama opik alpat sapto -> 10000
    - Ayam 26k dibagi 2 sama sapto -> 26000
    - Ayam 26k sama sapto dibagi 2 -> 26000
    """
    text = str(raw_text or "").strip()
    amount_token = r"(?P<amount>\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m)?)"
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"

    patterns = [
        # 22k dibagi 2 sama sapto
        rf"{amount_token}\s+{split_word}\s*(?:jadi\s*)?\d+",
        # 22k sama sapto dibagi 2
        rf"{amount_token}\s+{friend_marker}\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{{0,80}}\s+{split_word}\s*(?:jadi\s*)?\d+",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_amount_text(match.group("amount"))

    return None

async def set_budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Input bebas:
    budget makan 1.5 juta
    budget jajan 500rb
    budget kebutuhan 2 juta 2026-07

    Rule:
    - Alias kuat seperti makan -> Food & Beverage.
    - Label lain disimpan apa adanya sebagai budget custom.
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    text = update.message.text.strip()
    text_lower = text.lower()

    from app.nlp.normalizer import extract_amount_from_text

    amount = extract_amount_from_text(text_lower)
    if not amount:
        await update.message.reply_text(
            "❌ Nominal budget tidak ditemukan.\n"
            "Contoh:\n"
            "`budget makan 1.5 juta`\n"
            "`budget jajan 500rb`\n"
            "`budget kebutuhan 2 juta 2026-07`",
            parse_mode="Markdown",
        )
        return

    month_match = re.search(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])\b", text_lower)

    if month_match:
        raw_month = f"{month_match.group(1)}-{month_match.group(2)}"
        try:
            month = normalize_month(raw_month)
        except ValueError as e:
            await update.message.reply_text(
                f"❌ {str(e)}\n"
                "Contoh bulan: `2026-07`",
                parse_mode="Markdown",
            )
            return
    else:
        month = normalize_month(None)

    # Ambil label setelah kata budget, lalu buang nominal dan bulan.
    label_text = re.sub(r"^\s*budget\s+", "", text_lower).strip()
    label_text = re.sub(r"\b20\d{2}[-/](0?[1-9]|1[0-2])\b", " ", label_text)
    label_text = re.sub(r"\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)?", " ", label_text)
    label_text = re.sub(r"\b(per\s+bulan|bulan|untuk|buat|sebesar|senilai)\b", " ", label_text)
    label_text = re.sub(r"\s+", " ", label_text).strip(" .,-")

    if not label_text:
        await update.message.reply_text(
            "❌ Nama budget belum kebaca.\n\n"
            "Contoh:\n"
            "`budget makan 1.5 juta`\n"
            "`budget jajan 500rb`\n"
            "`budget kebutuhan 2 juta`",
            parse_mode="Markdown",
        )
        return

    alias_to_category = {
        # Sengaja TIDAK memasukkan 'jajan' supaya bisa jadi budget custom.
        "makan": "Food & Beverage",
        "makanan": "Food & Beverage",
        "minum": "Food & Beverage",
        "food": "Food & Beverage",
        "fnb": "Food & Beverage",
        "transport": "Transport",
        "transportasi": "Transport",
        "bensin": "Transport",
        "ojol": "Transport",
        "grab": "Transport",
        "gojek": "Transport",
        "listrik": "Bills & Utilities",
        "token": "Bills & Utilities",
        "pln": "Bills & Utilities",
        "air": "Bills & Utilities",
        "internet": "Bills & Utilities",
        "pulsa": "Bills & Utilities",
        "belanja": "Shopping",
        "shopping": "Shopping",
        "obat": "Health",
        "dokter": "Health",
        "hiburan": "Entertainment",
        "entertainment": "Entertainment",
        "pendidikan": "Education",
        "edukasi": "Education",
        "kos": "Kos & Utilities",
        "sedekah": "Zakat & Sedekah",
        "zakat": "Zakat & Sedekah",
        "investasi": "Investasi",
    }

    tokens = set(label_text.split())
    matched_category = None

    # Exact phrase dulu, lalu token-level alias.
    if label_text in alias_to_category:
        matched_category = alias_to_category[label_text]
    else:
        for token in tokens:
            if token in alias_to_category:
                matched_category = alias_to_category[token]
                break

    budget_label = matched_category or label_text.title()

    result = set_budget(budget_label, amount, month=month)

    if not result.get("success"):
        await update.message.reply_text(f"❌ {result.get('message')}")
        return

    action_label = "diset" if result["action"] == "created" else "diupdate"
    source_note = "kategori resmi" if matched_category else "budget custom"

    await update.message.reply_text(
        f"✅ Budget *{budget_label}* {action_label}!\n"
        f"📅 Bulan: *{format_month_label(month)}*\n"
        f"💰 {format_rupiah(amount)} / bulan\n"
        f"🏷️ Tipe: {source_note}\n\n"
        f"Cek dengan:\n"
        f"`/budget {month}`",
        parse_mode="Markdown",
    )


def short_debt_id(debt_id: str) -> str:
    debt_id = str(debt_id or "")
    if len(debt_id) <= 18:
        return debt_id
    return debt_id[:18] + "..."



def parse_debt_void_args(args: list[str]) -> dict:
    """
    Parsing argumen /debt_void yang lebih ramah user.

    Support:
    - /debt_void 1
    - /debt_void debt_xxx
    - /debt_void Annisa
    - /debt_void Annisa 1
    - /debt_void Cash Annisa 1
    """
    args = [str(a or "").strip() for a in (args or []) if str(a or "").strip()]
    if not args:
        return {"mode": "empty"}

    if len(args) == 1:
        token = args[0]
        if token.isdigit() or token.lower().startswith("debt_"):
            return {"mode": "single", "debt_ref": token}
        return {"mode": "person", "person_name": token, "detail_ref": None}

    if args[-1].isdigit() or args[-1].lower().startswith("debt_"):
        return {
            "mode": "person",
            "person_name": " ".join(args[:-1]).strip(),
            "detail_ref": args[-1],
        }

    return {"mode": "person", "person_name": " ".join(args).strip(), "detail_ref": None}


def build_debt_void_preview_text(preview: dict) -> str:
    if preview.get("bulk"):
        person = md_safe(preview.get("person_name") or "-")
        scope = preview.get("scope") or "person_all"
        detail_ref = str(preview.get("detail_ref") or "").strip()
        targets = preview.get("targets") or []
        reverse_deltas = preview.get("reverse_deltas", {}) or {}
        cashflow_txns = preview.get("cashflow_txns") or []
        total_remaining = float(preview.get("total_remaining") or 0)

        if scope == "person_detail" and detail_ref:
            title = f"⚠️ *Preview Void Rincian Debt {person} #{md_safe(detail_ref)}*\n"
        else:
            title = f"⚠️ *Preview Void SEMUA Debt Aktif {person}*\n"

        lines = [title]
        lines.append(f"👤 Nama: *{person}*")
        lines.append(f"📌 Jumlah rincian: *{len(targets)}*")
        lines.append(f"💰 Total yang akan di-void: *{format_rupiah(total_remaining)}*")

        lines.append("\n*Rincian yang akan di-void:*")
        for i, debt in enumerate(targets, 1):
            debt_type = str(debt.get("type") or "").strip()
            icon = "🔴" if debt_type == "payable" else "🟢"
            direction = "Anda hutang" if debt_type == "payable" else f"{preview.get('person_name') or 'Orang ini'} hutang"
            desc = md_safe(str(debt.get("description") or "-").strip()[:90])
            debt_id = md_safe(short_debt_id(debt.get("id", "-")))
            remaining = format_rupiah(debt.get("remaining_amount", 0))
            original = format_rupiah(debt.get("original_amount", 0))
            lines.append(
                f"{i}. {icon} *{desc}*\n"
                f"   {direction}: *{remaining}* / awal {original}\n"
                f"   Debt ID: `{debt_id}`"
            )

        if cashflow_txns:
            lines.append("\n*Cashflow terkait yang akan dihapus:*")
            for txn in cashflow_txns[:10]:
                txn_desc = md_safe(txn.get("description") or "-")
                txn_date = md_safe(txn.get("date") or "-")
                txn_amount = format_rupiah(float(txn.get("amount", 0) or 0))
                txn_account = md_safe(txn.get("account") or "-")
                lines.append(f"• {txn_date} — {txn_desc} — {txn_amount} | {txn_account}")
            if len(cashflow_txns) > 10:
                lines.append(f"• ...dan {len(cashflow_txns) - 10} cashflow lain")
        else:
            lines.append("\n*Cashflow terkait:* tidak ada / tidak perlu dihapus.")
            lines.append("Debt akan di-void tanpa mengubah saldo rekening.")

        if reverse_deltas:
            lines.append("\n*Efek balik ke saldo rekening:*")
            for account, delta in reverse_deltas.items():
                sign = "+" if delta >= 0 else "-"
                lines.append(f"• {md_safe(account)}: {sign}{format_rupiah(abs(delta))}")

        lines.append(
            "\nLanjut void target ini?\n"
            "Kalau klik Simpan, debt akan ditandai settled/void. Jika ada cashflow terkait, cashflow akan dihapus dan saldo direverse."
        )
        return "\n".join(lines)

    debt = preview.get("debt") or {}
    cashflow_txn = preview.get("cashflow_txn") or {}
    reverse_deltas = preview.get("reverse_deltas", {}) or {}

    debt_type = str(debt.get("type", "")).strip()
    direction = "🔴 Utang Anda" if debt_type == "payable" else "🟢 Piutang Anda"
    person = md_safe(debt.get("person_name", "-"))
    debt_id = md_safe(short_debt_id(debt.get("id", "-")))
    amount = float(debt.get("remaining_amount", 0) or 0)

    lines = ["⚠️ *Preview Void Debt*\n"]
    lines.append(f"{direction} dengan *{person}*")
    lines.append(f"💰 Nominal: *{format_rupiah(amount)}*")
    lines.append(f"🔖 Debt ID: `{debt_id}`")

    if cashflow_txn:
        txn_desc = md_safe(cashflow_txn.get("description") or "-")
        txn_date = md_safe(cashflow_txn.get("date") or "-")
        txn_category = md_safe(cashflow_txn.get("category") or "-")
        txn_account = md_safe(cashflow_txn.get("account") or "-")
        txn_amount = float(cashflow_txn.get("amount", 0) or 0)
        txn_row = md_safe(cashflow_txn.get("_row_index", "-"))

        lines.append("\n*Cashflow terkait yang akan dihapus:*")
        lines.append(
            f"• Row {txn_row} — {txn_date} — *{txn_desc}*\n"
            f"  {format_rupiah(txn_amount)} | {txn_category} | {txn_account}"
        )
    else:
        lines.append("\n*Cashflow terkait:* tidak ada.")
        lines.append("Debt/piutang ini akan divoid tanpa mengubah saldo rekening.")

    if reverse_deltas:
        lines.append("\n*Efek balik ke saldo rekening:*")
        for account, delta in reverse_deltas.items():
            safe_account = md_safe(account)
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {safe_account}: {sign}{format_rupiah(abs(delta))}")

    if preview.get("warning"):
        lines.append(f"\n⚠️ {md_safe(preview.get('warning'))}")

    lines.append(
        "\nLanjut void debt ini?\n"
        "Debt akan ditandai settled/void. Jika ada cashflow terkait, cashflow akan dihapus dan saldo direverse."
    )

    return "\n".join(lines)


async def debt_void_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /debt_void <nomor|debt_id|nama|nama nomor>

    Membatalkan debt yang salah input secara aman:
    - debt ditandai settled/void
    - cashflow debt terkait dihapus jika memang ada
    - saldo rekening direverse jika cashflow terkait ditemukan
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Masukkan nomor debt, debt ID, atau nama orang.\n\n"
            "Contoh:\n"
            "`/hutang Annisa`\n"
            "`/debt_void 1` — void nomor dari detail terakhir\n"
            "`/debt_void Annisa` — void semua debt aktif Annisa\n"
            "`/debt_void Annisa 1` — void rincian nomor 1 milik Annisa\n"
            "`/debt_void debt_20260610_123456_xxx`",
            parse_mode="Markdown",
        )
        return

    parsed = parse_debt_void_args(context.args or [])
    last_debt_map = context.user_data.get("last_debt_map", {})

    if parsed.get("mode") == "person":
        person_name = parsed.get("person_name") or ""
        detail_ref = parsed.get("detail_ref")
        preview = preview_void_debts_by_person(person_name, detail_ref)
    else:
        debt_ref = parsed.get("debt_ref")
        preview = preview_void_debt(debt_ref, last_debt_map)

    if not preview.get("success"):
        lines = [f"❌ *Debt void tidak bisa diproses.*\n{md_safe(preview.get('message'))}"]

        candidates = preview.get("candidate_txns") or []
        if candidates:
            lines.append("\nCashflow kandidat yang ambigu:")
            for txn in candidates[:10]:
                lines.append(
                    f"• Row {txn.get('_row_index', '-')} — {txn.get('date', '-')} — "
                    f"{md_safe(txn.get('description') or '-')} — {format_rupiah(float(txn.get('amount', 0) or 0))}"
                )

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
        )
        return

    if preview.get("bulk"):
        context.user_data["pending_debt_void"] = {
            "mode": "bulk",
            "person_name": preview.get("person_name"),
            "detail_ref": preview.get("detail_ref"),
            "target_debt_ids": preview.get("target_debt_ids") or [],
        }
    else:
        debt = preview.get("debt") or {}
        context.user_data["pending_debt_void"] = {
            "mode": "single",
            "debt_ref": str(debt.get("id") or parsed.get("debt_ref") or "").strip(),
        }

    await update.message.reply_text(
        build_debt_void_preview_text(preview),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("debt_void"),
    )


def normalize_debt_edit_type(value: str) -> str | None:
    text = str(value or "").strip().lower()
    mapping = {
        "payable": "payable",
        "utang": "payable",
        "hutang": "payable",
        "saya hutang": "payable",
        "utang saya": "payable",
        "receivable": "receivable",
        "piutang": "receivable",
        "dihutangi": "receivable",
        "diutangin": "receivable",
        "orang hutang": "receivable",
    }
    return mapping.get(text)


def parse_debt_edit_args(args: list[str]) -> tuple[str | None, dict, str | None]:
    if len(args) < 3:
        return None, {}, (
            "Format edit debt belum lengkap.\n\n"
            "Contoh:\n"
            "`/debt_edit 5 nominal 100k`\n"
            "`/debt_edit 5 nama Akmal`\n"
            "`/debt_edit 5 tipe piutang`\n"
            "`/debt_edit 5 deskripsi Split bill wifi`\n"
            "`/debt_edit 5 jatuh_tempo 2026-06-30`"
        )

    debt_ref = args[0].strip()
    field = args[1].strip().lower().replace("-", "_")
    value = " ".join(args[2:]).strip()

    aliases = {
        "nominal": "amount",
        "amount": "amount",
        "jumlah": "amount",
        "sisa": "amount",
        "nama": "person_name",
        "orang": "person_name",
        "person": "person_name",
        "person_name": "person_name",
        "tipe": "type",
        "type": "type",
        "jenis": "type",
        "deskripsi": "description",
        "description": "description",
        "catatan": "description",
        "keterangan": "description",
        "jatuh_tempo": "due_date",
        "duedate": "due_date",
        "due_date": "due_date",
        "tempo": "due_date",
        "tanggal": "due_date",
    }

    normalized_field = aliases.get(field)
    if not normalized_field:
        return debt_ref, {}, (
            "Field edit debt tidak dikenali.\n"
            "Field yang bisa diedit: `nominal`, `nama`, `tipe`, `deskripsi`, `jatuh_tempo`."
        )

    updates = {}
    if normalized_field == "amount":
        amount = parse_amount_text(value)
        if not amount or amount <= 0:
            return debt_ref, {}, "Nominal tidak valid. Contoh: `/debt_edit 5 nominal 100k`"
        updates["amount"] = amount
    elif normalized_field == "type":
        debt_type = normalize_debt_edit_type(value)
        if not debt_type:
            return debt_ref, {}, "Tipe tidak valid. Gunakan `utang/payable` atau `piutang/receivable`."
        updates["type"] = debt_type
    elif normalized_field == "due_date":
        detected = detect_date(value)
        updates["due_date"] = detected or value
    elif normalized_field == "person_name":
        if not value:
            return debt_ref, {}, "Nama orang tidak boleh kosong."
        updates["person_name"] = value
    elif normalized_field == "description":
        updates["description"] = value

    return debt_ref, updates, None


def build_debt_edit_result_text(result: dict) -> str:
    debt = result.get("debt") or {}
    changed = result.get("changed") or {}
    debt_type = str(debt.get("type") or "").strip()
    type_label = "Utang Anda" if debt_type == "payable" else "Piutang Anda"

    lines = ["✅ *Debt berhasil diedit!*\n"]
    lines.append(f"👤 Nama: *{md_safe(debt.get('person_name', '-'))}*")
    lines.append(f"📌 Tipe: *{md_safe(type_label)}*")
    lines.append(f"💰 Sisa: *{format_rupiah(float(debt.get('remaining_amount', 0) or 0))}*")
    due_date = str(debt.get("due_date") or "").strip()
    if due_date:
        lines.append(f"📅 Jatuh tempo: `{md_safe(due_date)}`")

    if changed:
        lines.append("\nField yang berubah:")
        for field, diff in changed.items():
            old = diff.get("old")
            new = diff.get("new")
            if field == "amount":
                old = format_rupiah(float(old or 0))
                new = format_rupiah(float(new or 0))
            lines.append(f"• `{field}`: {md_safe(old)} → *{md_safe(new)}*")

    lines.append("\nCek ulang dengan `/hutang`.")
    return "\n".join(lines)


async def debt_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /debt_edit <nomor_dari_hutang_atau_debt_id> <field> <value>
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    debt_ref, updates, error = parse_debt_edit_args(context.args or [])
    if error:
        await update.message.reply_text(f"❌ {error}", parse_mode="Markdown")
        return

    last_debt_map = context.user_data.get("last_debt_map", {})
    result = update_debt(debt_ref, updates, last_debt_map)
    if not result.get("success"):
        await update.message.reply_text(
            f"❌ *Debt gagal diedit.*\n{md_safe(result.get('message'))}",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        build_debt_edit_result_text(result),
        parse_mode="Markdown",
    )


def format_debt_created_date_for_display(debt: dict) -> str:
    """Ambil tanggal dibuat debt/piutang untuk grouping /hutang <nama>."""
    raw = str((debt or {}).get("created_at", "") or "").strip()
    if not raw:
        return "Tanpa tanggal"

    match = re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", raw)
    if match:
        parts = match.group(0).replace("/", "-").split("-")
        try:
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        except Exception:
            return match.group(0).replace("/", "-")

    # Fallback kalau created_at tersimpan sebagai date serial/string lain.
    return raw


async def hutang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    args = getattr(context, "args", []) or []
    person_query = " ".join(args).strip()

    # /hutang <nama> = detail rincian per orang
    if person_query:
        detail = get_debt_person_detail(person_query, include_settled=True)
        active_details = detail.get("active_details") or []
        all_details = detail.get("details") or []

        if not all_details:
            await update.message.reply_text(
                f"✅ Tidak ada riwayat utang/piutang untuk *{md_safe(person_query.title())}*.",
                parse_mode="Markdown",
            )
            return

        person = detail.get("person_name") or person_query.title()
        net_remaining = float(detail.get("net_remaining") or 0)
        net_type = detail.get("net_type")

        if net_type == "receivable":
            header = f"🟢 *{md_safe(person)} hutang ke Anda: {format_rupiah(abs(net_remaining))}*"
        elif net_type == "payable":
            header = f"🔴 *Anda hutang ke {md_safe(person)}: {format_rupiah(abs(net_remaining))}*"
        else:
            header = f"⚪ *Debt dengan {md_safe(person)} sudah netral/lunas.*"

        lines = [header, ""]
        lines.append("*Rincian aktif:*")

        last_debt_map = {}
        if active_details:
            current_debt_date_group = None
            for i, d in enumerate(active_details, 1):
                last_debt_map[str(i)] = {
                    "debt_id": d.get("id"),
                    "row_index": d.get("_row_index"),
                }
                created_date = format_debt_created_date_for_display(d)
                if created_date != current_debt_date_group:
                    lines.append(f"\n*{md_safe(format_indonesian_date_group_label(created_date))}*")
                    current_debt_date_group = created_date

                debt_type = str(d.get("type") or "").strip()
                icon = "🔴" if debt_type == "payable" else "🟢"
                direction = "Anda hutang" if debt_type == "payable" else f"{md_safe(person)} hutang"
                desc = str(d.get("description") or "-").strip()
                remaining = format_rupiah(d.get("remaining_amount", 0))
                original = format_rupiah(d.get("original_amount", 0))
                debt_id = str(d.get("id", "-") or "-").strip()
                lines.append(
                    f"{i}. {icon} {md_safe(desc)}\n"
                    f"   {direction}: *{remaining}* / awal {original}\n"
                    f"   ID: `{md_code_text(debt_id)}`"
                )
        else:
            lines.append("Tidak ada rincian aktif.")

        recv = detail.get("receivable") or {}
        pay = detail.get("payable") or {}

        if float(recv.get("original") or 0) > 0:
            pct = float(recv.get("paid_pct") or 0)
            lines.append(
                "\n*Progress piutang:*\n"
                f"Sudah bayar: *{format_rupiah(recv.get('paid', 0))}* / {format_rupiah(recv.get('original', 0))} "
                f"({pct:.1f}%)"
            )

        if float(pay.get("original") or 0) > 0:
            pct = float(pay.get("paid_pct") or 0)
            lines.append(
                "\n*Progress utang Anda:*\n"
                f"Sudah dibayar: *{format_rupiah(pay.get('paid', 0))}* / {format_rupiah(pay.get('original', 0))} "
                f"({pct:.1f}%)"
            )

        context.user_data["last_debt_map"] = last_debt_map
        if last_debt_map:
            lines.append(
                "\nKelola rincian dari daftar ini:\n"
                "`/debt_void 1` — batalkan rincian dari detail terakhir\n"
                f"`/debt_void {md_safe(person)}` — batalkan semua rincian aktif {md_safe(person)}\n"
                f"`/debt_void {md_safe(person)} 1` — batalkan rincian nomor 1 milik {md_safe(person)}\n"
                "`/debt_edit 1 nominal 100k` — edit nominal rincian\n"
                "Angka mengikuti nomor dari hasil detail `/hutang nama`."
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # /hutang = ringkasan agregat per orang
    summary = get_debt_person_summary()

    if not summary["payables"] and not summary["receivables"] and not summary.get("balanced"):
        await update.message.reply_text("✅ Tidak ada utang atau piutang aktif.")
        return

    lines = ["💸 *Utang & Piutang Aktif per Orang*\n"]

    if summary["payables"]:
        lines.append(f"🔴 *Utang Anda* (net total: {format_rupiah(summary['total_payable'])})")
        for i, d in enumerate(summary["payables"], 1):
            person = d.get("person_name") or "-"
            count = int(d.get("debt_count") or 0)
            lines.append(
                f"  {i}. {md_safe(person)} — *{format_rupiah(d.get('remaining_amount', 0))}* "
                f"({count} rincian)\n"
                f"     Detail: `/hutang {md_safe(person)}`"
            )

    if summary["payables"] and summary["receivables"]:
        lines.append("")

    if summary["receivables"]:
        lines.append(f"🟢 *Piutang Anda* (net total: {format_rupiah(summary['total_receivable'])})")
        for i, d in enumerate(summary["receivables"], 1):
            person = d.get("person_name") or "-"
            count = int(d.get("debt_count") or 0)
            lines.append(
                f"  {i}. {md_safe(person)} — *{format_rupiah(d.get('remaining_amount', 0))}* "
                f"({count} rincian)\n"
                f"     Detail: `/hutang {md_safe(person)}`"
            )

    if summary.get("balanced"):
        lines.append("\n⚪ *Netral tapi masih ada rincian aktif*")
        for d in summary["balanced"]:
            person = d.get("person_name") or "-"
            lines.append(f"  • {md_safe(person)} — cek `/hutang {md_safe(person)}`")

    net = summary["total_receivable"] - summary["total_payable"]
    net_label = "🟢 Anda lebih banyak dihutangi" if net >= 0 else "🔴 Anda lebih banyak berhutang"
    lines.append(f"\n{net_label}: *{format_rupiah(abs(net))}*")
    lines.append(
        "\nContoh pembayaran/pengurangan:\n"
        "`Sapto bayar 5k` — mengurangi piutang Sapto\n"
        "`bayar hutang Sapto 10k` — mengurangi debt aktif sesuai net Sapto\n"
        "`potong hutang Sapto 500k` — mengurangi hutang Sapto ke Anda\n"
        "`potong piutang Akmal 20k buat badminton` — kompensasi tanpa rekening"
    )

    # /debt_void dan /debt_edit sekarang lebih aman dipakai dari /hutang <nama>,
    # karena /hutang utama sudah agregat per orang.
    context.user_data["last_debt_map"] = {}
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Debt Message Handler ─────────────────────────────────────────────────────

