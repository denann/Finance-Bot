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
        "`/saldo`, `/harian`, `/mingguan`, `/bulanan`, `/last`, `/cari`\n"
        "`/edit_txn`, `/delete_txn`, `/download_data`\n\n"

        "🔁 *Budget & transaksi rutin*\n"
        "`/budget`, `/budget_history`, `/recurring`\n"
        "Recurring akan muncul sebagai reminder dengan tombol `Sudah bayar`.\n\n"

        "💼 *Net worth*\n"
        "`/assets`, `/liabilities`, `/networth`, `/networth_snapshot`\n\n"

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

        "*A. Fitur Inti*\n"
        "Bagian ini deterministic: bot mencatat, menghitung, dan mengubah data Google Sheets.\n\n"

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

        "*4. Utang/Piutang*\n"
        "`hutang ke Budi 500rb`\n"
        "`minjem uang Annisa 220k`\n"
        "`Budi minjem 300rb`\n"
        "`Budi bayar 100rb`\n"
        "`bayar hutang Budi 100rb`\n"
        "`saya talangin Sapto beli nasi kuning 12k` — uang Anda keluar, jadi piutang Sapto\n"
        "`saya ditalangin Alpat beli nasi uduk 10k` — dicatat utang tanpa cashflow\n"
        "`saya nitip Sapto beli nasi kuning 12k` — sama seperti ditalangin, tidak tanya rekening\n"
        "`/debt_void 1` — batalkan debt salah input dari hasil `/hutang`\n"
        "`/debt_edit 1 nominal 100k` — edit nominal utang/piutang\n"
        "`/debt_edit 1 nama Budi` — edit nama orang\n"
        "`/debt_edit 1 tipe piutang` — ubah arah jadi piutang\n\n"

        "*5. Input Banyak Sekaligus*\n"
        "`beli kopi 10k beli nasi 20k`\n"
        "`beli kopi 10k minjem Joko 50k`\n"
        "`hutang ke Budi 500k; hutang ke Joko 100k`\n\n"

        "*6. Split Bill*\n"
        "`Ayam dcelup 26k bagi 2 sama Sapto`\n"
        "Bot akan tanya apakah sudah dibayar. Kalau belum, bagian Sapto masuk piutang.\n\n"

        "*7. Laporan*\n"
        "`/saldo` — saldo semua rekening\n"
        "`/harian` — ringkasan hari ini\n"
        "`/harian 2026-06-01` — ringkasan tanggal tertentu\n"
        "`/mingguan` — ringkasan minggu ini\n"
        "`/mingguan 2026-06-01` — ringkasan minggu yang memuat tanggal itu\n"
        "`/bulanan` — ringkasan bulan ini + insight otomatis Gemini\n"
        "`/bulanan 2026-06` — ringkasan bulan tertentu + insight otomatis Gemini\n"
        "`/hutang` — utang/piutang aktif\n"
        "`/debt_void 1` — batalkan debt salah input\n"
        "`/debt_edit 1 nominal 100k` — edit utang/piutang aktif\n"
        "`/cari kopi` — cari transaksi dengan keyword kopi\n\n"

        "*8. Budget*\n"
        "`/budget` — lihat budget bulan berjalan\n"
        "`/budget 2026-06` — lihat budget bulan tertentu\n"
        "`/budget_history` — lihat daftar bulan yang punya budget\n"
        "`budget makan 1.5 juta` — otomatis map ke Food & Beverage\n"
        "`budget jajan 500rb` — buat budget custom Jajan\n"
        "`budget kebutuhan 2 juta` — buat budget custom Kebutuhan\n"
        "`budget transport 300rb 2026-07` — set budget bulan tertentu\n\n"

        "*9. Lihat & Koreksi Transaksi*\n"
        "`/last` — lihat 10 transaksi terakhir, urut tanggal terbaru\n"
        "`/last 20` — lihat 20 transaksi terakhir\n"
        "`/transaksi` — alias untuk melihat transaksi terakhir\n"
        "`/last today`, `/last week`, `/last month`, `/last 2026-06`\n"
        "`/delete_txn 1`, `/delete_txn 1 3 5`, `/delete_txn 1-4`\n"
        "`/edit_txn 2 amount=15000`\n"
        "`/edit_txn 2 desc=Kopi susu`\n"
        "`/edit_txn 2 account=BRI category=Food & Beverage`\n\n"

        "*10. Export, Recurring, Health*\n"
        "`/download_data`, `/download_data today`, `/download_data week`, `/download_data 2026-06`\n"
        "`/recurring` — lihat transaksi rutin\n"
        "`/recurring_add Netflix | expense | 65000 | Entertainment | DANA | monthly | 5 | Langganan Netflix`\n"
        "`/recurring_run`, `/recurring_edit ...`, `/recurring_off ...`\n"
        "Reminder otomatis akan menampilkan tombol `Sudah bayar`; klik tombol itu untuk mencatat transaksi dan menghentikan notifikasi sampai periode berikutnya.\n"
        "`/health` — cek status bot, env, Google Sheets, dan sheet utama\n\n"

        "*11. Net Worth, Aset, Liabilitas*\n"
        "`/networth` — lihat kekayaan bersih\n"
        "`/assets` — lihat daftar aset aktif\n"
        "`/liabilities` — lihat daftar liabilitas aktif\n"
        "`add emas 41 gram` — bot tanya harga 1 gram, lalu kalikan otomatis\n"
        "`add laptop 1 buah` — bot tanya harga 1 buah\n"
        "`/asset_add Laptop | 8000000 | Electronics | Laptop kerja`\n"
        "`/asset_update asset_id | unit_price=2420000`\n"
        "`/asset_update asset_id | value=9000000`\n"
        "`/asset_off asset_id`\n"
        "`/liability_add Paylater | 1200000 | Paylater | Cicilan aktif`\n"
        "`/liability_update liab_id | balance=500000`\n"
        "`/liability_off liab_id` — nonaktifkan liabilitas yang sudah lunas/tidak dipakai\n"
        "`/networth_snapshot`, `/networth_history`\n\n"

        "*12. Input Gambar / Struk*\n"
        "Kirim foto struk, nota, QRIS, atau screenshot transaksi.\n"
        "Bot membaca gambar dengan Gemini, lalu menampilkan preview sebelum disimpan.\n"
        "Caption opsional: `pakai BSI`, `ini pemasukan`, `total aja`.\n\n"

        "*B. Analisis Gemini / RAG Finance*\n"
        "Bagian ini read-only: bot mengambil data relevan dari Google Sheets, menghitung angka pakai Python, lalu Gemini menjelaskan insight.\n\n"

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
        "• Untuk `/delete_txn` dan `/edit_txn`, jalankan `/last` dulu.\n"
        "• Jika transaksi punya `hutang_id`, `/delete_txn` akan mencoba void debt terkait secara otomatis.\n"
        "• Data yang dikirim ke Gemini adalah ringkasan relevan, bukan seluruh spreadsheet mentah."
    )

    await reply_long_markdown(update, text)


async def send_finance_insight_reply(
    update: Update,
    mode: str,
    context_data: dict,
    question: str = "",
    prefix: str = "🤖 Insight Gemini",
):
    await update.message.reply_text("⏳ Mengambil data dan membuat insight...")
    answer = generate_finance_insight(mode, context_data, question=question)
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

    await send_finance_insight_reply(update, mode, data, question=question, prefix="💬 Jawaban Finance")


async def coach_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/coach [pertanyaan] — financial coach ringan."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    question = " ".join(context.args).strip() if context.args else "Kasih saran finansial ringan untuk bulan ini."
    data = build_coach_context(None, question=question)
    await send_finance_insight_reply(update, "coach", data, question=question, prefix="🧭 Finance Coach")


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

    await send_finance_insight_reply(update, mode, data, question=user_text, prefix="🤖 Analisis Finance")
    return True


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


async def harian_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    date_arg = " ".join(context.args).strip() if context.args else None

    try:
        report = get_daily_report(date_arg)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/harian`\n"
            "`/harian 2026-06-01`\n"
            "`/harian 01-06-2026`\n"
            "`/harian 1`",
            parse_mode="Markdown",
        )
        return

    date_str = report["date"]

    if report["count"] == 0:
        await update.message.reply_text(f"📭 Belum ada transaksi hari ini ({date_str}).")
        return

    lines = [f"📅 *Ringkasan Harian*\n_{date_str}_\n"]
    lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
    lines.append(f"❌ Pengeluaran: *{format_rupiah(report['total_expense'])}*")
    lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
    lines.append(f"📝 Transaksi : {report['count']} item\n")

    if report["by_category"]:
        lines.append("*Pengeluaran per Kategori:*")
        total_expense = float(report["total_expense"] or 0)

        for cat, amount in sorted(report["by_category"].items(), key=lambda x: x[1], reverse=True):
            pct = (float(amount) / total_expense) * 100 if total_expense else 0
            bar = build_progress_bar(pct)
            lines.append(f"  • {cat}: *{format_rupiah(amount)}*\n    {bar} {pct:.1f}%")

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

            lines.append(
                f"  {i}. {t.get('description', '-')}\n"
                f"     {t.get('category', '-')} - "
                f"*{format_rupiah(amount)}* | {contrib:.1f}% dari pengeluaran"
            )

    await reply_long_markdown(update, "\n".join(lines))


async def mingguan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    date_arg = " ".join(context.args).strip() if context.args else None

    try:
        report = get_weekly_report(date_arg)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/mingguan`\n"
            "`/mingguan 2026-06-01`\n"
            "`/mingguan 1`",
            parse_mode="Markdown",
        )
        return

    if report["count"] == 0:
        await update.message.reply_text(
            f"📭 Belum ada transaksi minggu ini.\n"
            f"({report['date_from']} s/d {report['date_to']})"
        )
        return

    lines = [
        f"📆 *Ringkasan Mingguan*\n"
        f"_{report['date_from']} s/d {report['date_to']}_\n"
    ]
    lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
    lines.append(f"❌ Pengeluaran: *{format_rupiah(report['total_expense'])}*")
    lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
    lines.append(f"📝 Transaksi : {report['count']} item\n")

    if report["by_category"]:
        lines.append("*Pengeluaran per Kategori:*")
        total_expense = float(report["total_expense"] or 0)

        for cat, amount in sorted(report["by_category"].items(), key=lambda x: x[1], reverse=True):
            pct = (float(amount) / total_expense) * 100 if total_expense else 0
            bar = build_progress_bar(pct)
            lines.append(f"  • {cat}: *{format_rupiah(amount)}*\n    {bar} {pct:.1f}%")

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

            lines.append(
                f"  {i}. {t.get('description', '-')}\n"
                f"     {t.get('category', '-')} - "
                f"*{format_rupiah(amount)}* | {contrib:.1f}% dari pengeluaran"
            )

    await reply_long_markdown(update, "\n".join(lines))


async def bulanan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    month_arg = " ".join(context.args).strip() if context.args else None

    try:
        year, month_num = parse_report_month_arg(month_arg)
        report = get_monthly_report(year, month_num)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/bulanan`\n"
            "`/bulanan 2026-06`\n"
            "`/bulanan 6`",
            parse_mode="Markdown",
        )
        return

    if report["count"] == 0:
        await update.message.reply_text("📭 Belum ada transaksi bulan ini.")
        return

    month_name = report.get("month", "-")

    lines = [f"📆 *Ringkasan Bulanan*\n_{month_name}_\n"]
    lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
    lines.append(f"❌ Pengeluaran: *{format_rupiah(report['total_expense'])}*")
    lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
    lines.append(f"📝 Transaksi : {report['count']} item\n")

    if report["by_category"]:
        lines.append("*Pengeluaran per Kategori:*")
        total_expense = float(report["total_expense"] or 0)

        for cat, amount in sorted(report["by_category"].items(), key=lambda x: x[1], reverse=True):
            pct = (float(amount) / total_expense) * 100 if total_expense else 0
            bar = build_progress_bar(pct)
            lines.append(f"  • {cat}: *{format_rupiah(amount)}*\n    {bar} {pct:.1f}%")

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

            lines.append(
                f"  {i}. {t.get('description', '-')}\n"
                f"     {t.get('category', '-')} - "
                f"*{format_rupiah(amount)}* | {contrib:.1f}% dari pengeluaran"
            )

    budget_summary = get_budget_summary()
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

    for t in results:
        icon = "➕" if t.get("type") == "income" else "➖" if t.get("type") == "expense" else "🔄"
        lines.append(
            f"{icon} {md_safe(t.get('date') or '-')} — {md_safe(t.get('description') or '-')}\n"
            f"   *{format_rupiah(float(t.get('amount', 0) or 0))}* | {md_safe(t.get('category') or '-')}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


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
    total_remaining = total_budget - total_actual
    total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0

    lines = [f"📊 *Budget {format_month_label(month)}*\n"]

    lines.append(f"💰 Total Budget : *{format_rupiah(total_budget)}*")
    lines.append(f"💸 Realisasi    : *{format_rupiah(total_actual)}*")
    lines.append(f"📌 Sisa         : *{format_rupiah(total_remaining)}*")
    lines.append(f"📈 Terpakai     : *{total_pct:.1f}%*\n")

    for item in summary:
        bar = build_progress_bar(item["pct_used"])
        remaining_label = "Sisa" if item["remaining"] >= 0 else "Over"

        lines.append(
            f"{item['emoji']} *{item['category']}*\n"
            f"  {bar} {item['pct_used']}%\n"
            f"  Pakai: {format_rupiah(item['actual'])} / {format_rupiah(item['budget'])}\n"
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


def build_debt_void_preview_text(preview: dict) -> str:
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
    /debt_void <nomor_dari_hutang_atau_debt_id>

    Membatalkan debt yang salah input secara aman:
    - debt ditandai settled/void
    - cashflow debt terkait dihapus
    - saldo rekening direverse
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Masukkan nomor debt atau debt ID.\n\n"
            "Contoh:\n"
            "`/hutang`\n"
            "`/debt_void 1`\n"
            "`/debt_void debt_20260610_123456_xxx`",
            parse_mode="Markdown",
        )
        return

    debt_ref = context.args[0].strip()
    last_debt_map = context.user_data.get("last_debt_map", {})

    preview = preview_void_debt(debt_ref, last_debt_map)

    if not preview.get("success"):
        lines = [f"❌ *Debt void tidak bisa diproses.*\n{preview.get('message')}"]

        candidates = preview.get("candidate_txns") or []
        if candidates:
            lines.append("\nCashflow kandidat yang ambigu:")
            for txn in candidates[:10]:
                lines.append(
                    f"• Row {txn.get('_row_index', '-')} — {txn.get('date', '-')} — "
                    f"{txn.get('description') or '-'} — {format_rupiah(float(txn.get('amount', 0) or 0))}"
                )

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
        )
        return

    context.user_data["pending_debt_void"] = {
        "debt_ref": debt_ref,
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


async def hutang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    summary = get_debt_summary()

    if not summary["payables"] and not summary["receivables"]:
        await update.message.reply_text("✅ Tidak ada utang atau piutang aktif.")
        return

    lines = ["💸 *Utang & Piutang Aktif*\n"]
    last_debt_map = {}
    display_no = 1

    if summary["payables"]:
        lines.append(f"🔴 *Utang Anda* (total: {format_rupiah(summary['total_payable'])})")
        for d in summary["payables"]:
            due = f" | jatuh tempo: {d.get('due_date')}" if d.get("due_date") else ""
            last_debt_map[str(display_no)] = {
                "debt_id": d.get("id"),
                "row_index": d.get("_row_index"),
            }
            desc = str(d.get("description") or "").strip()
            desc_line = f"\n     📝 {md_safe(desc[:70])}" if desc else ""
            debt_id_short = str(d.get("id") or "")[-8:]
            lines.append(
                f"  {display_no}. {md_safe(d.get('person_name'))} — "
                f"*{format_rupiah(float(d.get('remaining_amount', 0) or 0))}*"
                f"{due}"
                f" | ID: `{md_safe(debt_id_short)}`"
                f"{desc_line}"
            )
            display_no += 1

    if summary["payables"] and summary["receivables"]:
        lines.append("")

    if summary["receivables"]:
        lines.append(
            f"🟢 *Piutang Anda* (total: {format_rupiah(summary['total_receivable'])})"
        )
        for d in summary["receivables"]:
            last_debt_map[str(display_no)] = {
                "debt_id": d.get("id"),
                "row_index": d.get("_row_index"),
            }
            desc = str(d.get("description") or "").strip()
            desc_line = f"\n     📝 {md_safe(desc[:70])}" if desc else ""
            debt_id_short = str(d.get("id") or "")[-8:]
            lines.append(
                f"  {display_no}. {md_safe(d.get('person_name'))} — "
                f"*{format_rupiah(float(d.get('remaining_amount', 0) or 0))}*"
                f" | ID: `{md_safe(debt_id_short)}`"
                f"{desc_line}"
            )
            display_no += 1

    context.user_data["last_debt_map"] = last_debt_map

    net = summary["total_receivable"] - summary["total_payable"]
    net_label = "🟢 Anda lebih banyak dihutangi" if net >= 0 else "🔴 Anda lebih banyak berhutang"
    lines.append(f"\n{net_label}: *{format_rupiah(abs(net))}*")
    lines.append(
        "\nKelola debt dari daftar ini:\n"
        "`/debt_void 1` — batalkan debt salah input\n"
        "`/debt_edit 1 nominal 100k` — edit nominal\n"
        "`/debt_edit 1 nama Budi` — edit nama orang\n"
        "Angka mengikuti nomor dari hasil `/hutang` ini."
    )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Debt Message Handler ─────────────────────────────────────────────────────

