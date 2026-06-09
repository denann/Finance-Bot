import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.config import ALLOWED_USER_ID
from app.bot.keyboards import account_keyboard, confirm_keyboard
from app.nlp.regex_parser import parse_with_regex
from app.nlp.gemini_parser import parse_with_pending_fallback
from app.services.transaction_service import save_transaction, get_all_accounts
from app.services.budget_service import (
    set_budget,
    get_budget_summary,
    check_budget_after_transaction,
)
from app.config import SHEET_CATEGORIES
from app.sheets.client import get_all_records
from app.services.report_service import (
    get_daily_report,
    get_weekly_report,
    get_monthly_report,
    search_transactions,
    get_top_expenses,
    format_rupiah,
)

from app.services.debt_service import (
    add_debt,
    add_payment,
    get_debt_summary,
    get_debt_by_person,
)
from app.nlp.regex_parser import parse_debt_input

# ── Helper ────────────────────────────────────────────────────────────────────

def format_rupiah(amount: float) -> str:
    return f"Rp{int(amount):,}".replace(",", ".")


def is_authorized(update: Update) -> bool:
    user_id = update.effective_user.id
    return user_id == ALLOWED_USER_ID


def parse_input(text: str) -> dict:
    """Coba regex dulu, fallback ke Gemini."""
    result = parse_with_regex(text)
    if result is not None:
        return result
    return parse_with_pending_fallback(text)

def build_progress_bar(pct: float, length: int = 10) -> str:
    """Buat progress bar teks. Contoh: [████░░░░░░] 40%"""
    filled = int(min(pct, 100) / 100 * length)
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"

# ── Command Handlers ──────────────────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    text = (
        "👋 Halo! Saya bot pencatat keuangan pribadi Anda.\n\n"
        "Ketik transaksi bebas, contoh:\n"
        "• `beli kopi 25rb`\n"
        "• `gaji masuk 8 juta`\n"
        "• `transfer gopay 200rb`\n\n"
        "Perintah tersedia:\n"
        "/saldo — lihat saldo semua rekening\n"
        "/harian — ringkasan hari ini\n"
        "/mingguan — ringksasan minggu ini\n"
        "/bulanan — ringkasan bulan ini\n"
        "/cari xxx— mencari histori berdasarkan kata kunci xxx\n"
        "/help — bantuan lengkap"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    text = (
        "📖 *Panduan Penggunaan*\n\n"
        "*Catat Pengeluaran:*\n"
        "`beli kopi 25rb`\n"
        "`makan siang 35k`\n"
        "`bayar listrik 150.000`\n\n"
        "*Catat Pemasukan:*\n"
        "`gaji masuk 8 juta`\n"
        "`freelance project 500rb`\n\n"
        "*Transfer Antar Rekening:*\n"
        "`transfer gopay 200rb`\n"
        "`top up dana dari bri 500rb`\n\n"
        "*Lihat Laporan:*\n"
        "/saldo — saldo semua rekening\n"
        "/harian — pengeluaran hari ini\n"
        "/mingguan — ringksasan minggu ini\n"
        "/bulanan — ringkasan bulan ini\n"
        "/cari xxx— mencari histori berdasarkan kata kunci xxx\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    accounts = get_all_accounts()
    if not accounts:
        await update.message.reply_text("❌ Tidak ada data rekening.")
        return

    total = sum(float(acc.get("balance", 0)) for acc in accounts)
    lines = ["💰 *Saldo Rekening*\n"]

    emoji_map = {
        "cash": "💵",
        "bank": "🏦",
        "ewallet": "📱",
    }

    for acc in accounts:
        emoji = emoji_map.get(acc.get("type", ""), "💳")
        name = acc.get("account_name", "")
        balance = float(acc.get("balance", 0))
        lines.append(f"{emoji} {name}: *{format_rupiah(balance)}*")

    lines.append(f"\n📊 Total: *{format_rupiah(total)}*")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def harian_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    report = get_daily_report()
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
        total_expense = float(report["total_expense"])

        for cat, amount in sorted(report["by_category"].items(), key=lambda x: x[1], reverse=True):
            pct = (float(amount) / total_expense) * 100 if total_expense else 0
            bar = build_progress_bar(pct)
            lines.append(f"  • {cat}: *{format_rupiah(amount)}*\n    {bar} {pct:.1f}%")

    top = sorted(
        [t for t in report.get("transactions", []) if t.get("type") == "expense"],
        key=lambda x: float(x.get("amount", 0)),
        reverse=True
    )[:3]

    if top:
        lines.append("\n*Top 3 Pengeluaran:*")
        total_expense = float(report["total_expense"])

        for i, t in enumerate(top, 1):
            amount = float(t.get("amount", 0))
            contrib = (amount / total_expense * 100) if total_expense else 0

            lines.append(
                f"  {i}. {t.get('description', '-')}\n"
                f"     {t.get('category', '-')} - "
                f"*{format_rupiah(amount)}* | {contrib:.1f}% dari pengeluaran"
            )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def mingguan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    report = get_weekly_report()

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
        total_expense = float(report["total_expense"])

        for cat, amount in sorted(report["by_category"].items(), key=lambda x: x[1], reverse=True):
            pct = (float(amount) / total_expense) * 100 if total_expense else 0
            bar = build_progress_bar(pct)
            lines.append(f"  • {cat}: *{format_rupiah(amount)}*\n    {bar} {pct:.1f}%")

    top = sorted(
        [t for t in report.get("transactions", []) if t.get("type") == "expense"],
        key=lambda x: float(x.get("amount", 0)),
        reverse=True
    )[:3]

    if top:
        lines.append("\n*Top 3 Pengeluaran:*")
        total_expense = float(report["total_expense"])

        for i, t in enumerate(top, 1):
            amount = float(t.get("amount", 0))
            contrib = (amount / total_expense * 100) if total_expense else 0

            lines.append(
                f"  {i}. {t.get('description', '-')}\n"
                f"     {t.get('category', '-')} - "
                f"*{format_rupiah(amount)}* | {contrib:.1f}% dari pengeluaran"
            )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def bulanan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    report = get_monthly_report()
    from app.services.budget_service import get_budget_summary

    if report["count"] == 0:
        await update.message.reply_text("📭 Belum ada transaksi bulan ini.")
        return

    now = datetime.now()
    month_name = now.strftime("%B %Y")

    lines = [f"📆 *Ringkasan Bulanan*\n_{month_name}_\n"]
    lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
    lines.append(f"❌ Pengeluaran: *{format_rupiah(report['total_expense'])}*")
    lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
    lines.append(f"📝 Transaksi : {report['count']} item\n")

    if report["by_category"]:
        lines.append("*Pengeluaran per Kategori:*")
        total_expense = float(report["total_expense"])

        for cat, amount in sorted(report["by_category"].items(), key=lambda x: x[1], reverse=True):
            pct = (float(amount) / total_expense) * 100 if total_expense else 0
            bar = build_progress_bar(pct)
            lines.append(f"  • {cat}: *{format_rupiah(amount)}*\n    {bar} {pct:.1f}%")

    top = sorted(
        [t for t in report.get("transactions", []) if t.get("type") == "expense"],
        key=lambda x: float(x.get("amount", 0)),
        reverse=True
    )[:3]

    if top:
        lines.append("\n*Top 3 Pengeluaran:*")
        total_expense = float(report["total_expense"])

        for i, t in enumerate(top, 1):
            amount = float(t.get("amount", 0))
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

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cari_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /cari <keyword> — cari transaksi berdasarkan keyword.
    Contoh: /cari kopi
    """
    if not is_authorized(update):
        return

    # Ambil keyword dari argumen command
    args = context.args
    if not args:
        await update.message.reply_text(
            "🔍 Masukkan keyword pencarian.\n"
            "Contoh: `/cari kopi`",
            parse_mode="Markdown"
        )
        return

    keyword = " ".join(args)
    results = search_transactions(keyword)

    if not results:
        await update.message.reply_text(
            f"🔍 Tidak ada transaksi dengan keyword *{keyword}*.",
            parse_mode="Markdown"
        )
        return

    lines = [f"🔍 *Hasil pencarian: \"{keyword}\"*\n"]
    for t in results:
        icon = "➕" if t.get("type") == "income" else "➖" if t.get("type") == "expense" else "🔄"
        lines.append(
            f"{icon} {t.get('date')} — {t.get('description', '-')}\n"
            f"   *{format_rupiah(float(t.get('amount', 0)))}* | {t.get('category', '-')}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Message Handler (input bebas) ─────────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    user_text = update.message.text.strip()

    # Cek debt input dulu sebelum transaksi biasa
    debt_handled = await debt_message_handler(update, context)
    if debt_handled:
        return

    # Lanjut ke parsing transaksi biasa
    parsed = parse_input(user_text)

    if parsed.get("type") == "pending":
        await update.message.reply_text(
            "🤔 Maaf, saya tidak bisa memahami input tersebut.\n\n"
            "Coba format seperti:\n"
            "`beli kopi 25rb`\n"
            "`gaji masuk 8 juta`\n"
            "`hutang ke Budi 500rb`",
            parse_mode="Markdown"
        )
        return

    context.user_data["pending_parsed"] = parsed
    context.user_data["pending_raw"] = user_text

    preview = build_preview(parsed)

    if parsed.get("account") or parsed.get("type") == "transfer":
        await update.message.reply_text(
            f"{preview}\n\nSimpan transaksi ini?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("pending")
        )
    else:
        await update.message.reply_text(
            f"{preview}\n\n💳 Dari rekening mana?",
            parse_mode="Markdown",
            reply_markup=account_keyboard("acc")
        )


def build_preview(parsed: dict) -> str:
    """Buat teks preview transaksi sebelum disimpan."""
    type_label = {
        "expense": "❌ Pengeluaran",
        "income": "✅ Pemasukan",
        "transfer": "🔄 Transfer",
    }.get(parsed.get("type"), "❓")

    lines = [
        f"*{type_label}*",
        f"💰 Nominal : {format_rupiah(parsed.get('amount', 0))}",
        f"📁 Kategori: {parsed.get('category') or '-'}",
        f"📝 Deskripsi: {parsed.get('description') or '-'}",
        f"📅 Tanggal : {parsed.get('date') or '-'}",
    ]

    if parsed.get("account"):
        lines.append(f"🏦 Rekening: {parsed.get('account')}")
    if parsed.get("to_account"):
        lines.append(f"➡️ Ke Rekening: {parsed.get('to_account')}")

    return "\n".join(lines)


# ── Callback Handler (tombol inline) ─────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    query = update.callback_query
    await query.answer()

    data = query.data

    # ── Pilih rekening untuk transaksi biasa ─────────────────────────────────
    if data.startswith("acc:"):
        account = data.split(":")[1]
        parsed = context.user_data.get("pending_parsed")
        if not parsed:
            await query.edit_message_text("❌ Sesi expired. Coba input ulang.")
            return

        parsed["account"] = account
        context.user_data["pending_parsed"] = parsed
        preview = build_preview(parsed)

        await query.edit_message_text(
            f"{preview}\n\nSimpan transaksi ini?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("pending")

        )

    # ── Konfirmasi simpan ─────────────────────────────────────────────────────
    elif data.startswith("confirm:"):
        parsed = context.user_data.get("pending_parsed")
        raw = context.user_data.get("pending_raw", "")

        if not parsed:
            await query.edit_message_text("❌ Sesi expired. Coba input ulang.")
            return

        result = save_transaction(parsed, raw_input=raw)
 
        if result["success"]:
            balance_info = ""
            if result.get("new_balance") is not None:
                balance_info = (
                    f"\n💳 Saldo {parsed.get('account') or parsed.get('to_account')}: "
                    f"*{format_rupiah(result['new_balance'])}*"
                )

            # Cek budget setelah transaksi expense
            budget_info = ""
            if parsed.get("type") == "expense" and parsed.get("category"):
                budget_check = check_budget_after_transaction(parsed["category"])
                if budget_check:
                    budget_info = (
                        f"\n\n{budget_check['emoji']} *Budget {parsed['category']}*\n"
                        f"Terpakai: {format_rupiah(budget_check['actual'])} "
                        f"/ {format_rupiah(budget_check['budget'])} "
                        f"({budget_check['pct_used']}%)\n"
                        f"Sisa: {format_rupiah(budget_check['remaining'])}"
                    )
                    if budget_check["alert"]:
                        budget_info += f"\n\n{budget_check['alert_msg']}"

            await query.edit_message_text(
                f"✅ *Transaksi tersimpan!*\n"
                f"🔖 ID: `{result['transaction_id']}`"
                f"{balance_info}"
                f"{budget_info}",
                parse_mode="Markdown"
            )

            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
        else:
            await query.edit_message_text(
                f"❌ Gagal menyimpan: {result['message']}"
            )

    # ── Batalkan ─────────────────────────────────────────────────────────────
    elif data.startswith("cancel"):
        context.user_data.pop("pending_parsed", None)
        context.user_data.pop("pending_raw", None)
        await query.edit_message_text("❌ Transaksi dibatalkan.")

    # ── Pilih debt untuk dibayar ──────────────────────────────────────────────
    elif data.startswith("pay_debt:"):
        parts = data.split(":")
        debt_id = parts[1]
        amount = float(parts[2])

        result = add_payment(debt_id, amount)

        if result["success"]:
            pending = context.user_data.get("pending_payment", {})
            person = pending.get("person", "")

            if result["is_settled"]:
                msg = (
                    f"✅ *Hutang ke {person} LUNAS!*\n"
                    f"💰 Dibayar: {format_rupiah(amount)}"
                )
            else:
                msg = (
                    f"✅ *Pembayaran dicatat!*\n\n"
                    f"👤 Kepada : {person}\n"
                    f"💰 Dibayar: {format_rupiah(amount)}\n"
                    f"📊 Sisa   : {format_rupiah(result['remaining'])}"
                )
            await query.edit_message_text(msg, parse_mode="Markdown")
            context.user_data.pop("pending_payment", None)
        else:
            await query.edit_message_text(
                f"❌ Gagal: {result['message']}"
            )

async def budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /budget — tampilkan ringkasan budget vs realisasi bulan ini.
    """
    if not is_authorized(update):
        return

    summary = get_budget_summary()

    if not summary:
        await update.message.reply_text(
            "📭 Belum ada budget yang diset bulan ini.\n\n"
            "Set budget dengan cara:\n"
            "`budget makan 1.5 juta`\n"
            "`budget transport 300rb`",
            parse_mode="Markdown"
        )
        return

    now = datetime.now()
    month_name = now.strftime("%B %Y")
    lines = [f"📊 *Budget {month_name}*\n"]

    for item in summary:
        bar = build_progress_bar(item["pct_used"])
        lines.append(
            f"{item['emoji']} *{item['category']}*\n"
            f"  {bar} {item['pct_used']}%\n"
            f"  Pakai: {format_rupiah(item['actual'])} / {format_rupiah(item['budget'])}\n"
            f"  Sisa : {format_rupiah(item['remaining'])}\n"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")





async def set_budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    text = update.message.text.strip()
    text_lower = text.lower()

    from app.nlp.normalizer import extract_amount_from_text

    # Ekstrak nominal
    amount = extract_amount_from_text(text_lower)
    if not amount:
        await update.message.reply_text(
            "❌ Nominal budget tidak ditemukan.\n"
            "Contoh: `budget makan 1.5 juta`",
            parse_mode="Markdown"
        )
        return

    # Deteksi kategori dari sheet categories + kolom aliases
    categories = get_all_records(SHEET_CATEGORIES)
    matched_category = None

    for cat in categories:
        cat_name = cat.get("category_name", "")
        aliases_raw = cat.get("aliases", "")

        # Gabungkan nama kategori + aliases jadi satu list
        all_keywords = [cat_name.lower()]
        if aliases_raw:
            all_keywords += [a.strip().lower() for a in aliases_raw.split(",")]

        # Cek apakah ada keyword yang match di teks user
        for keyword in all_keywords:
            if keyword and keyword in text_lower:
                matched_category = cat_name
                break

        if matched_category:
            break

    if not matched_category:
        await update.message.reply_text(
            "❌ Kategori tidak dikenali.\n\n"
            "Contoh penggunaan:\n"
            "`budget makan 1.5 juta`\n"
            "`budget transport 300rb`\n"
            "`budget belanja 500rb`\n"
            "`budget listrik 200rb`",
            parse_mode="Markdown"
        )
        return

    result = set_budget(matched_category, amount)
    action_label = "diset" if result["action"] == "created" else "diupdate"

    await update.message.reply_text(
        f"✅ Budget *{matched_category}* {action_label}!\n"
        f"💰 {format_rupiah(amount)} / bulan\n\n"
        f"Ketik /budget untuk lihat semua budget.",
        parse_mode="Markdown"
    )

async def hutang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/hutang — tampilkan semua utang & piutang aktif."""
    if not is_authorized(update):
        return

    summary = get_debt_summary()

    if not summary["payables"] and not summary["receivables"]:
        await update.message.reply_text(
            "✅ Tidak ada utang atau piutang aktif."
        )
        return

    lines = ["💸 *Utang & Piutang Aktif*\n"]

    # Utang Anda
    if summary["payables"]:
        lines.append(f"🔴 *Utang Anda* (total: {format_rupiah(summary['total_payable'])})")
        for d in summary["payables"]:
            due = f" | jatuh tempo: {d.get('due_date')}" if d.get("due_date") else ""
            lines.append(
                f"  • {d.get('person_name')} — "
                f"*{format_rupiah(float(d.get('remaining_amount', 0)))}*"
                f"{due}"
            )

    if summary["payables"] and summary["receivables"]:
        lines.append("")

    # Piutang Anda
    if summary["receivables"]:
        lines.append(
            f"🟢 *Piutang Anda* (total: {format_rupiah(summary['total_receivable'])})"
        )
        for d in summary["receivables"]:
            lines.append(
                f"  • {d.get('person_name')} — "
                f"*{format_rupiah(float(d.get('remaining_amount', 0)))}*"
            )

    # Net position
    net = summary["total_receivable"] - summary["total_payable"]
    net_label = "🟢 Anda lebih banyak dihutangi" if net >= 0 else "🔴 Anda lebih banyak berhutang"
    lines.append(f"\n{net_label}: *{format_rupiah(abs(net))}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def debt_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle input debt dari pesan bebas."""
    if not is_authorized(update):
        return

    text = update.message.text.strip()
    debt_parsed = parse_debt_input(text)

    if not debt_parsed:
        return False  # Bukan input debt, lanjut ke handler lain

    intent = debt_parsed["intent"]
    person = debt_parsed["person_name"]
    amount = debt_parsed["amount"]
    description = debt_parsed["description"]

    if intent == "add_payable":
        if not person:
            await update.message.reply_text(
                "❓ Siapa yang Anda hutangi?\n"
                "Contoh: `hutang ke Budi 500rb buat makan`",
                parse_mode="Markdown"
            )
            return True

        result = add_debt("payable", person, amount, description)
        if result["success"]:
            await update.message.reply_text(
                f"📝 *Utang dicatat!*\n\n"
                f"👤 Kepada  : {person}\n"
                f"💰 Nominal : {format_rupiah(amount)}\n"
                f"📝 Keterangan: {description}\n\n"
                f"Ketik /hutang untuk lihat semua utang.",
                parse_mode="Markdown"
            )

    elif intent == "add_receivable":
        result = add_debt("receivable", person, amount, description)
        if result["success"]:
            await update.message.reply_text(
                f"📝 *Piutang dicatat!*\n\n"
                f"👤 Dari    : {person}\n"
                f"💰 Nominal : {format_rupiah(amount)}\n"
                f"📝 Keterangan: {description}\n\n"
                f"Ketik /hutang untuk lihat semua piutang.",
                parse_mode="Markdown"
            )

    elif intent == "add_payment":
        # Cari debt berdasarkan nama orang
        if not person:
            await update.message.reply_text(
                "❓ Bayar hutang ke siapa?\n"
                "Contoh: `bayar hutang Budi 200rb`",
                parse_mode="Markdown"
            )
            return True

        debts = get_debt_by_person(person)
        if not debts:
            await update.message.reply_text(
                f"❓ Tidak ada hutang aktif dengan *{person}*.",
                parse_mode="Markdown"
            )
            return True

        # Jika hanya ada satu debt, langsung proses
        if len(debts) == 1:
            debt = debts[0]
            result = add_payment(debt["id"], amount)

            if result["success"]:
                if result["is_settled"]:
                    msg = (
                        f"✅ *Hutang ke {person} LUNAS!*\n"
                        f"💰 Dibayar: {format_rupiah(amount)}"
                    )
                else:
                    msg = (
                        f"✅ *Pembayaran dicatat!*\n\n"
                        f"👤 Kepada  : {person}\n"
                        f"💰 Dibayar : {format_rupiah(amount)}\n"
                        f"📊 Sisa    : {format_rupiah(result['remaining'])}"
                    )
                await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            # Ada multiple debt dengan orang yang sama
            # Simpan ke context untuk dipilih user
            context.user_data["pending_payment"] = {
                "person": person,
                "amount": amount,
                "debts": debts,
            }

            lines = [f"📋 Ada {len(debts)} hutang dengan *{person}*. Pilih yang mana?\n"]
            keyboard = []
            for d in debts:
                label = (
                    f"{d.get('description', '-')} — "
                    f"{format_rupiah(float(d.get('remaining_amount', 0)))}"
                )
                lines.append(f"• {label}")
                keyboard.append([
                    InlineKeyboardButton(
                        label,
                        callback_data=f"pay_debt:{d['id']}:{amount}"
                    )
                ])

            await update.message.reply_text(
                "\n".join(lines),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    return True