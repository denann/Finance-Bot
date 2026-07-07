"""Telegram command handlers for onboarding, reports, account balances, budgets, debt, pending expenses, assets, exports, and AI insights."""

# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *
# Import app.bot.handler_parts.transaction_flow so this module can use its helpers.
from app.bot.handler_parts.transaction_flow import build_pending_expense_confirm_preview, edit_or_continue_keyboard, preview_action_keyboard, preview_action_question
# Import app.bot.handler_parts.state_utils so this module can use its helpers.
from app.bot.handler_parts.state_utils import clear_pending_flow_state, describe_active_pending_flow, has_active_pending_flow
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import resolve_account_name
# Import app.services.chart_service so this module can use its helpers.
from app.services.chart_service import write_monthly_chart_png


# Handle the asynchronous start handler workflow.
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous start handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Open a multi-line structure for the values below.
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
        "• `catat utang ke Budi 200k`\n"
        "• `saya talangin Raka beli nasi kuning 12k`\n"
        "• `saya ditalangin Bagas beli nasi uduk 10k`\n"
        "• `nasi goreng 30k bagi 3 sama Dimas Raka`\n\n"

        "📊 *Laporan & koreksi data*\n"
        "`/saldo`, `/rekening`, `/harian`, `/mingguan`, `/bulanan`, `/grafik`, `/last`, `/cari`\n"
        "`/transaksi`, `/edit_txn`, `/delete_txn`, `/debt_settle`, `/download_data`\n\n"

        "🕒 *Pending, budget & transaksi rutin*\n"
        "`/pending`, `/pending_add`, `/budget`, `/budget_history`, `/kategori`, `/add_kategori`, `/edit_kategori`, `/recurring`\n"
        "Pending tidak mengubah saldo sampai ditandai `/pending_paid`. Recurring akan muncul sebagai reminder dengan tombol `Sudah bayar`.\n\n"

        "💼 *Net worth*\n"
        "`/assets`, `/networth`, `/networth_snapshot`\n\n"

        "🤖 *Analisis Gemini / RAG Finance*\n"
        "`/insight`, `/ask`, `/audit`, `/coach`\n\n"

        "🚀 *Baru pertama kali pakai bot ini?*\n"
        "Mulai dari `/quickstart` supaya setup rekening, saldo awal, dan contoh inputnya tidak loncat-loncat.\n\n"
        "Ketik `/examples` untuk contoh input cepat, atau `/help` untuk panduan lengkap."
    # Close the structure that was opened above.
    )

    await update.message.reply_text(text, parse_mode="Markdown")




# Define format account name list for callers in this flow.
def _format_account_name_list(accounts: list[dict]) -> list[str]:
    """Format data into a readable display for account name list."""
    # Prepare names for the next step.
    names = []
    # Process each account in the current collection.
    for account in accounts or []:
        name = str(account.get("account_name") or "").strip()
        # Handle the case where name.
        if name:
            # Update names with the current value.
            names.append(name)
    # Return names to the caller.
    return names


# Define format accounts table for message for callers in this flow.
def _format_accounts_table_for_message(accounts: list[dict]) -> str:
    """Format data into a readable display for accounts table for message."""
    # Handle the missing or empty accounts case.
    if not accounts:
        return "Belum ada rekening di sheet `accounts`."

    # Prepare lines for the next step.
    lines = []
    # Process each account in the current collection.
    for account in accounts:
        name = str(account.get("account_name") or "-").strip()
        account_type = str(account.get("type") or "-").strip()
        balance = float(account.get("balance", 0) or 0)
        lines.append(f"• `{md_code_text(name)}` — {md_safe(account_type)} — *{format_rupiah(balance)}*")
    return "\n".join(lines)


# Define resolve account name from sheet for callers in this flow.
def _resolve_account_name_from_sheet(input_name: str, accounts: list[dict]) -> tuple[str | None, list[str]]:
    """Resolve a user input or reference for account name from sheet."""
    clean = str(input_name or "").strip().strip('"').strip("'")
    # Handle the missing or empty clean case.
    if not clean:
        # Return None, [] to the caller.
        return None, []

    # Prepare resolved for the next step.
    resolved = resolve_account_name(clean)
    if resolved.get("status") == "exact":
        return str(resolved.get("account_name") or "").strip(), []

    if resolved.get("status") == "similar":
        return None, list(resolved.get("suggestions") or [])[:5]

    # Keep a local fallback in case resolver reads fallback accounts but caller already
    # supplied a more specific account list.
    exact_names = _format_account_name_list(accounts)
    # Prepare suggestions for the next step.
    suggestions = [name for name in exact_names if clean.lower() in name.lower() or name.lower() in clean.lower()]
    # Return None, suggestions[:5] to the caller.
    return None, suggestions[:5]


# Define guess account type for callers in this flow.
def _guess_account_type(account_name: str) -> str:
    """Guess a simple account type for a new account row."""
    clean = str(account_name or "").strip().lower()
    if clean == "cash":
        return "cash"
    if clean in {"dana", "gopay", "ovo", "shopeepay", "linkaja"} or "wallet" in clean:
        return "ewallet"
    return "bank"


# Define build set balance preview text for callers in this flow.
def _build_set_balance_preview_text(account_name: str, current_balance: float, new_balance: float, *, create_missing: bool = False) -> str:
    """Build the preview text for setting an account balance."""
    # Prepare delta for the next step.
    delta = float(new_balance or 0) - float(current_balance or 0)
    sign = "+" if delta >= 0 else "-"

    title = "⚠️ *Preview Tambah Rekening dan Set Saldo*" if create_missing else "⚠️ *Preview Set Saldo Rekening*"
    # Open a multi-line structure for the values below.
    action_note = (
        "Aksi ini akan menambahkan rekening baru ke sheet `accounts`, lalu mengisi saldo awalnya. Tidak akan membuat row transaksi baru."
        # Handle the case where create_missing.
        if create_missing
        else "Aksi ini akan menimpa saldo rekening di sheet `accounts`. Tidak akan membuat row transaksi baru."
    # Close the structure that was opened above.
    )
    current_label = "Saldo awal" if create_missing else "Saldo sekarang"

    # Return ( to the caller.
    return (
        f"{title}\n\n"
        f"{action_note}\n\n"
        f"🏦 Rekening: *{md_safe(account_name)}*\n"
        f"💰 {current_label}: *{format_rupiah(current_balance)}*\n"
        f"🎯 Saldo baru: *{format_rupiah(new_balance)}*\n"
        f"🔁 Selisih: *{sign}{format_rupiah(abs(delta))}*\n\n"
        "Klik *Simpan* kalau sudah benar, atau *Batal* kalau masih mau cek lagi."
    # Close the structure that was opened above.
    )


# Define set balance similarity keyboard for callers in this flow.
def _set_balance_similarity_keyboard() -> InlineKeyboardMarkup:
    """Coordinate the set balance similarity keyboard logic in the Telegram handler layer.

    Args:
        None.

    Returns:
        `InlineKeyboardMarkup` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Pakai rekening existing", callback_data="set_balance_similar:use_existing")],
        [InlineKeyboardButton("➕ Tetap buat rekening baru", callback_data="set_balance_similar:create_new")],
        [InlineKeyboardButton("✍️ Tulis ulang", callback_data="cancel:set_balance_rewrite")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:set_balance")],
    # Close the structure that was opened above.
    ])


# Define parse set balance args for callers in this flow.
def _parse_set_balance_args(raw_arg: str) -> tuple[str, float | None]:
    """Parse caller input for the parse set balance args workflow in the Telegram handler layer.

    Args:
        raw_arg: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `tuple[str, float | None]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = str(raw_arg or "").strip()
    # Handle the missing or empty raw case.
    if not raw:
        return "", None

    # Prepare amount for the next step.
    amount = extract_amount_from_text(raw)
    # Handle the case where amount is None.
    if amount is None:
        # Return raw, None to the caller.
        return raw, None

    # Use the last detected amount as the new balance; the remaining text is treated as the account name.
    amount_pattern = re.compile(
        r"(?:rp\.?\s*)?\d[\d.,]*(?:\s*(?:rb|ribu|k|jt|juta|m|mio))?",
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Prepare matches for the next step.
    matches = list(amount_pattern.finditer(raw))
    # Prepare account text for the next step.
    account_text = raw
    # Handle the case where matches.
    if matches:
        # Prepare match for the next step.
        match = matches[-1]
        account_text = (raw[:match.start()] + " " + raw[match.end():]).strip()

    # Open a multi-line structure for the values below.
    account_text = re.sub(
        r"\b(?:saldo|rekening|akun|account|balance|set|jadi|sebesar|ke|to)\b",
        " ",
        # Include this value in the surrounding collection or call.
        account_text,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    account_text = re.sub(r"\s+", " ", account_text).strip().strip('"').strip("'")
    # Return account_text, float(amount) to the caller.
    return account_text, float(amount)


# Handle the asynchronous quickstart handler workflow.
async def quickstart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a first-use checklist that guides users through account setup, balance setup, and basic test inputs."""
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare accounts for the next step.
    accounts = get_all_accounts()
    # Prepare account names for the next step.
    account_names = _format_account_name_list(accounts)
    account_text = ", ".join(f"`{md_code_text(name)}`" for name in account_names) if account_names else "belum ada rekening"

    # Open a multi-line structure for the values below.
    text = (
        "🚀 *Quickstart Finance Bot*\n\n"
        "Gunakan checklist ini saat pertama kali memakai bot. Tujuannya sederhana: pastikan rekening, saldo awal, dan contoh input sudah benar sebelum dipakai harian.\n\n"
        "*1. Cek rekening yang tersedia*\n"
        "Jalankan:\n"
        "`/saldo`\n\n"
        "Nama rekening yang saat ini terbaca dari sheet `accounts`:\n"
        f"{account_text}\n\n"
        "Pakai nama rekening yang sama persis agar data tidak pecah karena beda penamaan. Contoh: gunakan `DANA`, bukan kadang `Dana` atau `dana wallet`.\n\n"
        "*2. Set saldo awal rekening*\n"
        "Gunakan format:\n"
        "`/set_saldo NamaRekening Nominal`\n\n"
        "Contoh:\n"
        "`/set_saldo Cash 100k`\n"
        "`/set_saldo DANA 500k`\n"
        "`/set_saldo BRI 2500000`\n\n"
        "Kalau lupa nama rekening yang tersedia, jalankan `/set_saldo` tanpa argumen. Bot akan menampilkan daftar rekening dari sheet `accounts`.\n\n"
        "*3. Coba input transaksi kecil*\n"
        "Contoh:\n"
        "`beli kopi 20k dari Cash`\n"
        "`gaji masuk 8jt ke BRI`\n"
        "`BCA ke DANA 200k`\n\n"
        "*4. Coba flow yang lebih kompleks*\n"
        "Contoh:\n"
        "`Budi minjem 50k dari DANA`\n"
        "`Beli mie goreng 40k dibagi 2 sama Budi via DANA`\n"
        "`saya ditalangin Bagas beli nasi 15k`\n\n"
        "*5. Cek hasilnya*\n"
        "Gunakan:\n"
        "`/saldo`\n"
        "`/last`\n"
        "`/hutang`\n"
        "`/bulanan`\n\n"
        "Kalau flow dasar ini sudah aman, baru lanjut pakai fitur lain seperti `/budget`, `/kategori`, `/add_kategori`, `/pending`, `/recurring`, `/assets`, `/ask`, dan `/audit`."
    # Close the structure that was opened above.
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# Handle the asynchronous cancel handler workflow.
async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any active wizard, preview, or pending confirmation state."""
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare active label for the next step.
    active_label = describe_active_pending_flow(context)
    # Prepare removed for the next step.
    removed = clear_pending_flow_state(context)

    # Handle the case where removed.
    if removed:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "🚫 *Flow aktif dibatalkan.*\n\n"
            f"State yang dibersihkan: *{md_safe(active_label or 'pending flow')}*\n\n"
            "Tidak ada data yang disimpan.",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        "ℹ️ Tidak ada flow aktif yang perlu dibatalkan.",
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )


# Handle the asynchronous set saldo handler workflow.
async def set_saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /set_saldo and prepare a confirmation preview before updating an account balance."""
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare accounts for the next step.
    accounts = get_all_accounts()
    raw_arg = " ".join(context.args).strip() if context.args else ""

    # Regex fallback path: MessageHandler does not populate context.args, so parse the raw Telegram text.
    if not raw_arg:
        raw_text = getattr(getattr(update, "message", None), "text", "") or ""
        match = re.match(r"^/(?:set_saldo|saldo_set|set_balance)(?:@\w+)?\s*(.*)$", raw_text.strip(), flags=re.IGNORECASE)
        # Handle the case where match.
        if match:
            # Prepare raw arg for the next step.
            raw_arg = match.group(1).strip()

    # Handle the missing or empty raw_arg case.
    if not raw_arg:
        # Open a multi-line structure for the values below.
        text = (
            "💳 *Set Saldo Rekening*\n\n"
            "Command ini dipakai untuk menyesuaikan saldo awal atau koreksi saldo rekening tertentu di sheet `accounts`.\n\n"
            "*Rekening yang tersedia:*\n"
            f"{_format_accounts_table_for_message(accounts)}\n\n"
            "Gunakan nama rekening yang sama persis dengan daftar di atas supaya tidak ada penamaan yang pecah.\n\n"
            "*Format:*\n"
            "`/set_saldo NamaRekening Nominal`\n\n"
            "*Contoh:*\n"
            "`/set_saldo Cash 100k`\n"
            "`/set_saldo DANA 500k`\n"
            "`/set_saldo BRI 2500000`"
        # Close the structure that was opened above.
        )
        await update.message.reply_text(text, parse_mode="Markdown")
        # Return control to the caller.
        return

    # Run this statement as part of the current workflow.
    account_arg, new_balance = _parse_set_balance_args(raw_arg)
    # Handle the case where new_balance is None.
    if new_balance is None:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Nominal saldo belum terbaca.\n\n"
            "Contoh yang benar:\n"
            "`/set_saldo DANA 500k`\n"
            "`/set_saldo BRI 2500000`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Run this statement as part of the current workflow.
    account_name, suggestions = _resolve_account_name_from_sheet(account_arg, accounts)
    # Handle the missing or empty account_name and suggestions case.
    if not account_name and suggestions:
        # Prepare suggested name for the next step.
        suggested_name = suggestions[0]
        context.user_data["pending_set_balance_suggestion"] = {
            "input_account_name": account_arg,
            "suggested_account_name": suggested_name,
            "new_balance": float(new_balance),
            "account_type": _guess_account_type(account_arg),
        # Close the structure that was opened above.
        }
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "⚠️ *Kemungkinan rekening duplikat*\n\n"
            f"Input rekening: `{md_code_text(account_arg or '-')}`\n"
            f"Mirip dengan rekening existing: *{md_safe(suggested_name)}*\n\n"
            "Pilih salah satu supaya saldo tidak pecah ke dua nama rekening yang maksudnya sama.",
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=_set_balance_similarity_keyboard(),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Handle the missing or empty account_name case.
    if not account_name:
        context.user_data["pending_set_balance"] = {
            "account_name": account_arg,
            "current_balance": 0.0,
            "new_balance": float(new_balance),
            "delta": float(new_balance),
            "create_missing": True,
            "account_type": _guess_account_type(account_arg),
        # Close the structure that was opened above.
        }

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            _build_set_balance_preview_text(account_arg, 0.0, float(new_balance), create_missing=True),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("set_balance"),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare current balance for the next step.
    current_balance = get_account_balance(account_name)
    # Handle the case where current_balance is None.
    if current_balance is None:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ Saldo rekening `{md_code_text(account_name)}` belum bisa dibaca dari sheet `accounts`.",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare delta for the next step.
    delta = float(new_balance) - float(current_balance)
    sign = "+" if delta >= 0 else "-"

    context.user_data["pending_set_balance"] = {
        "account_name": account_name,
        "current_balance": float(current_balance),
        "new_balance": float(new_balance),
        "delta": float(delta),
    # Close the structure that was opened above.
    }

    # Prepare text for the next step.
    text = _build_set_balance_preview_text(account_name, current_balance, float(new_balance), create_missing=False)

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=confirm_keyboard("set_balance"))

# Handle the asynchronous help handler workflow.
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous help handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Open a multi-line structure for the values below.
    text = (
        "📖 *Panduan Penggunaan Finance Bot*\n\n"
        "`/start` — ringkasan fitur utama bot\n"
        "`/quickstart` — panduan langkah awal untuk user baru\n"
        "`/help` — panduan lengkap ini\n"
        "Gunakan tombol *Batal* untuk membatalkan wizard/preview yang sedang aktif.\n\n"

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
        "`Dimas bayar hutang 20k kemarin`\n\n"
        "Contoh satu baris:\n"
        "`beli kopi 10k; beli nasi 20k; Budi minjem 50k`\n"
        "`beli kopi 10k minjem Joko 50k`\n\n"

        "*5. Rekening Opsional untuk Data Historis*\n"
        "Kalau transaksi sudah berlalu dan Anda tidak mau mengubah saldo rekening, pilih tombol:\n"
        "`Sudah berlalu / jangan ubah saldo`\n"
        "Contoh:\n"
        "`Beli tissue 10k dibagi 4 sama Raka Fajar Bagas`\n"
        "Debt/split bill tetap tercatat, tapi saldo rekening tidak berubah.\n\n"

        "*B. Utang, Piutang, Split Bill*\n\n"
        "*6. Utang/Piutang Biasa*\n"
        "`hutang ke Budi 500rb` — Anda punya utang ke Budi\n"
        "`catat utang ke Budi 200k` — catat utang tanpa menambah saldo rekening\n"
        "`minjem uang Maya 220k` — Anda punya utang ke Maya\n"
        "`Budi minjem 300rb` — Budi punya utang ke Anda / piutang Anda\n"
        "`piutang ke Dimas 31100` — Dimas punya utang ke Anda\n"
        "`saya berutang ke Dimas 20k` — Anda punya utang ke Dimas\n"
        "`Dimas berutang 50k` — piutang Anda ke Dimas\n"
        "`Budi bayar 100rb` — pembayaran piutang dari Budi\n"
        "`bayar hutang Budi 100rb` — pembayaran utang Anda ke Budi\n\n"

        "*7. Talangin / Ditalangin*\n"
        "`saya talangin Raka beli nasi kuning 12k` — uang Anda keluar, jadi piutang Raka\n"
        "`saya ditalangin Bagas beli nasi uduk 10k` — utang Anda ke Bagas tanpa cashflow rekening\n"
        "`saya nitip Raka beli nasi kuning 12k` — sama seperti ditalangin\n"
        "`ditalangin nasi uduk sama Bagas 10k kemarin` — Bagas menalangi Anda\n"
        "`ditalangin Bagas beli minyak 46k dibagi 4 sama Bagas Fajar Raka` — PTPT: Anda hutang full 46k ke Bagas, lalu Bagas/Fajar/Raka masing-masing hutang share ke Anda\n\n"

        "*8. Split Bill*\n"
        "`Ayam dcelup 26k bagi 2 sama Raka`\n"
        "`Beli tissue 10k dibagi 4 sama Raka Fajar Bagas`\n"
        "`Beli token 500k dibagi 4 sama Raka:100% Fajar:80% Bagas:100%`\n"
        "`Beli token 500k dibagi 4 sama Raka 125k Fajar 100k Bagas 125k`\n"
        "Tanda `:` opsional. Kalau belum dibayar, bagian teman masuk piutang.\n\n"

        "*9. Kompensasi / Potong Silang Hutang-Piutang*\n"
        "Dipakai kalau tidak ada uang keluar/masuk rekening, tapi saldo hutang-piutang berubah.\n"
        "`potong piutang Dimas 20k buat badminton`\n"
        "`kompensasi piutang Dimas 20k karena badminton`\n"
        "`saya berutang ke Dimas 20k potong dari piutang`\n"
        "Tetap masuk sheet `transactions` sebagai fact table, tapi saldo rekening tidak berubah.\n\n"

        "*10. Kelola Debt*\n"
        "`/hutang` — ringkasan utang/piutang aktif per orang\n"
        "`/hutang Maya` — detail rincian aktif Maya + debt ID\n"
        "`/debt_void 1` — batalkan rincian dari detail terakhir\n"
        "`/debt_void Maya` — batalkan semua debt aktif Maya setelah konfirmasi\n"
        "`/debt_void Maya 1` — batalkan rincian nomor 1 milik Maya\n"
        "`/debt_edit 1 nominal 100k` — edit nominal rincian\n"
        "`/debt_edit 1 nama Budi` — edit nama orang\n"
        "`/debt_edit 1 tipe piutang` — ubah arah debt\n"
        "`/debt_settle Raka` — settle semua debt aktif Raka pakai nominal net otomatis setelah preview\n"
        "`/debt_settle Raka 1-17` — settle nomor 1-17 dari output terakhir `/hutang Raka` pakai nominal net otomatis\n"
        "`/debt_settle Raka 1-17 amount=337063 account=DANA` — settle hanya nomor 1-17, debt lain tidak disentuh\n"
        "`Raka bayar hutang 337063 untuk debt 1-17` — versi natural dari settle debt terpilih\n"
        "Nomor `1-17` wajib berasal dari detail terakhir `/hutang nama`. Jika terakhir buka `/hutang Bagas`, bot akan menolak settle untuk Raka.\n"
        "Jika amount lebih besar dari net debt terpilih, bot memberi warning dan pilihan: anggap bonus/lunas atau catat sebagai hutang lawan arah.\n"
        "Pembayaran global seperti `Raka bayar hutang 373063` juga dicek terhadap posisi net: piutang - utang Anda. Jadi overpaid tidak lagi dihitung dari satu arah saja.\n"
        "Detail `/hutang nama` dikelompokkan per tanggal dibuat, menampilkan debt ID full, dan tidak auto-settle tanpa perintah Anda.\n\n"

        "*C. Laporan, Budget, Koreksi Data*\n\n"
        "*11. Laporan*\n"
        "`/saldo` — saldo semua rekening\n"
        "`/set_saldo` — lihat nama rekening yang tersedia di sheet accounts\n"
        "`/set_saldo DANA 500k` — set saldo rekening tertentu dengan preview konfirmasi\n"
        "`/rekening Cash` — list transaksi lengkap rekening Cash bulan ini\n"
        "`/rekening Cash 2026-06` — list transaksi lengkap rekening bulan tertentu\n"
        "`/rekening Cash all` — seluruh transaksi rekening Cash\n"
        "`/harian` — ringkasan hari ini\n"
        "`/harian 2026-06-01` — ringkasan tanggal tertentu\n"
        "`/harian Food & Beverage` — list transaksi kategori hari ini\n"
        "`/harian rekening Cash` — ringkasan hari ini khusus rekening Cash\n"
        "`/mingguan` — ringkasan minggu ini\n"
        "`/mingguan 2026-06-01` — ringkasan minggu yang memuat tanggal itu\n"
        "`/mingguan Bills & Utilities` — list transaksi kategori minggu ini\n"
        "`/mingguan rekening Dana` — ringkasan minggu ini khusus rekening Dana\n"
        "`/bulanan` — ringkasan bulan ini + insight Gemini + grafik time series\n"
        "`/bulanan 2026-06` — ringkasan bulan tertentu + insight Gemini + grafik time series\n"
        "`/bulanan Food & Beverage` — list transaksi kategori bulan ini\n"
        "`/bulanan rekening Cash` — ringkasan bulan ini khusus rekening Cash\n"
        "`/bulanan 2026-06 rekening Cash` — ringkasan rekening bulan tertentu\n"
        "`/bulanan 2026-06 Food & Beverage rekening Cash` — list kategori + rekening bulan tertentu\n"
        "`/grafik` — grafik time series pengeluaran net bulan ini\n"
        "`/grafik 2026-06` — grafik time series pengeluaran net bulan tertentu\n"
        "`/grafik line 2026-06` — sama seperti `/grafik 2026-06`, eksplisit time series harian\n"
        "`/grafik bar 2026-06` — bar chart pengeluaran net per kategori\n"
        "`/grafik pie 2026-06` — pie chart kategori berdasarkan pengeluaran net\n"
        "Tipe grafik yang didukung: `line`/`timeseries`, `bar`, dan `pie`. Jika bulan tidak ditulis, bot memakai bulan berjalan.\n"
        "Report utama menampilkan tren vs periode sebelumnya, termasuk tren per kategori. Jika periode sebelumnya belum ada data, bot tampilkan `~`.\n"
        "Nominal dan ranking pengeluaran memakai basis net; jika ada piutang aktif ditampilkan sebagai `Net (Gross)`, misalnya `Rp16.000 (Rp32.000)`.\n"
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
        "Output `/transaksi` dikelompokkan per tanggal terbaru ke terlama dan otomatis mengirim grafik time series PNG sesuai transaksi yang ditampilkan.\n"
        "`/last today`, `/last week`, `/last month`, `/last 2026-06`\n"
        "Output `/last` juga otomatis mengirim grafik time series PNG dari transaksi yang tampil.\n"
        "`/delete_txn 1`, `/delete_txn 1 3 5`, `/delete_txn 1-4`\n"
        "`/edit_txn 2 amount=15000`\n"
        "`/edit_txn 2 desc=Kopi susu`\n"
        "`/edit_txn 2 account=BRI category=Food & Beverage`\n"
        "Bulk edit juga bisa dengan paste beberapa baris `/edit_txn` sekaligus setelah `/last`, `/transaksi`, atau `/cari`. Bot akan kasih preview Simpan/Batal.\n"
        "`/edit_txn 1 category=\"Household & Supplies\" desc=\"Galon\"`\n"
        "`/edit_txn 2 category=\"Food & Beverage\"`\n"
        "`/edit_txn txn_id amount=500k dibagi 4 sama Raka:125k Bagas:125k Fajar:100k`\n"
        "`/edit_txn 2 bayar_hutang Raka` — ubah transaksi jadi pembayaran utang ke Raka\n"
        "`/edit_txn 2 bayar_piutang Raka` — ubah transaksi jadi pembayaran piutang dari Raka\n"
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

        "*15. Kategori*\n"
        "`/kategori` — lihat daftar kategori, tipe, symbol, dan aliases\n"
        "`/add_kategori` — tambah kategori baru dengan wizard\n"
        "`/add_kategori Belanja Online` — langsung isi nama kategori, lalu pilih tipe\n"
        "`/edit_kategori` — edit tipe, symbol, dan aliases kategori existing\n"
        "Saat tambah kategori, bot akan tanya nama, tipe `expense`/`income`, symbol, generate aliases via Gemini, lalu tampilkan preview sebelum save.\n"
        "Saat edit aliases, ketik daftar dipisah koma, `auto` untuk generate ulang via Gemini, atau `sama` untuk mempertahankan. Perubahan tetap lewat preview sebelum save.\n\n"

        "*16. Export, Recurring, Health*\n"
        "`/download_data`, `/download_data today`, `/download_data week`, `/download_data 2026-06`\n"
        "`/recurring` — lihat transaksi rutin\n"
        "`/recurring_add name=Netflix type=expense amount=65000 category=Entertainment account=DANA frequency=monthly day=5 description=\"Langganan Netflix\"`\n"
        "`/recurring_edit rec_xxx amount=300k day=20 account=DANA` — edit recurring dengan format key=value\n"
        "`/recurring_run`, `/recurring_off rec_xxx`\n"
        "Recurring otomatis muncul sebagai reminder dengan tombol `Sudah bayar`. Klik tombol itu untuk mencatat transaksi dan menghentikan notifikasi sampai periode berikutnya.\n"
        "`/health` — cek status bot, env, Google Sheets, dan sheet utama\n\n"

        "*D. Net Worth & Aset*\n\n"
        "*17. Net Worth*\n"
        "`/networth` — lihat kekayaan bersih dari saldo rekening + aset aktif\n"
        "`/networth_snapshot` — simpan snapshot net worth hari ini\n"
        "`/networth_history` — lihat riwayat snapshot\n\n"

        "*18. Aset*\n"
        "`/assets` — lihat daftar aset aktif\n"
        "`/asset_add` — tambah aset mode tanya-jawab/guided input\n"
        "Format utama:\n"
        "`/asset_add Laptop`\n"
        "`catet aset hp 10 juta`\n"
        "`tambah aset laptop 8 juta`\n"
        "Dalam mode guided, bot akan tanya nama aset, jumlah/unit, harga beli, tanggal beli, harga saat ini, kategori, dan deskripsi.\n"
        "Tanggal beli boleh dikosongkan dengan mengetik `lewati`, `kosong`, atau `-`.\n"
        "Setiap step punya tombol `Batal`.\n"
        "`/asset_update asset_id unit_price=2420000`\n"
        "`/asset_update asset_id harga_beli=2559000 tanggal_beli=2026-06-10`\n"
        "`/asset_update asset_id amount=9000000`\n"
        "`/asset_off asset_id`\n\n"

        "*E. Input Gambar & Analisis Gemini/RAG*\n\n"
        "*19. Input Gambar / Struk*\n"
        "Kirim foto struk, nota, QRIS, atau screenshot transaksi.\n"
        "Bot membaca gambar dengan Gemini, lalu menampilkan preview sebelum disimpan.\n"
        "Caption opsional: `pakai BSI`, `ini pemasukan`, `total aja`.\n\n"

        "*20. Analisis Gemini / RAG Finance*\n"
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
    # Close the structure that was opened above.
    )

    # Wait for reply_long_markdown before continuing this flow.
    await reply_long_markdown(update, text)


# Define add session chat history for callers in this flow.
def add_session_chat_history(context: ContextTypes.DEFAULT_TYPE, role: str, text: str, limit: int = 10):
    """Coordinate the add session chat history logic in the Telegram handler layer.

    Args:
        context: Telegram callback context containing args, bot data, user data, and job data.
        role: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        text: Raw text input to parse, normalize, validate, or display.
        limit: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the case where context is None.
    if context is None:
        # Return control to the caller.
        return

    clean_text = str(text or "").strip()
    # Handle the missing or empty clean_text case.
    if not clean_text:
        # Return control to the caller.
        return

    history = context.user_data.get("finance_chat_history", [])
    # Open a multi-line structure for the values below.
    history.append({
        "role": str(role or "user"),
        "text": clean_text[:1200],
    # Close the structure that was opened above.
    })
    context.user_data["finance_chat_history"] = history[-limit:]


# Define get session chat history for callers in this flow.
def get_session_chat_history(context: ContextTypes.DEFAULT_TYPE, limit: int = 8) -> list[dict]:
    """Retrieve data needed by the get session chat history workflow in the Telegram handler layer.

    Args:
        context: Telegram callback context containing args, bot data, user data, and job data.
        limit: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the case where context is None.
    if context is None:
        # Return [] to the caller.
        return []
    history = context.user_data.get("finance_chat_history", [])
    # Return history[-limit:] to the caller.
    return history[-limit:]


# Define attach session history for callers in this flow.
def attach_session_history(context: ContextTypes.DEFAULT_TYPE, context_data: dict) -> dict:
    """Coordinate the attach session history logic in the Telegram handler layer.

    Args:
        context: Telegram callback context containing args, bot data, user data, and job data.
        context_data: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Prepare data for the next step.
    data = dict(context_data or {})
    # Prepare history for the next step.
    history = get_session_chat_history(context)
    # Handle the case where history.
    if history:
        data["chat_history"] = history
        data["chat_history_note"] = (
            "Riwayat ini hanya untuk memahami konteks pertanyaan lanjutan. "
            "Jangan jadikan chat_history sebagai sumber angka utama; angka faktual harus dari monthly_context/relevant_transactions."
        # Close the structure that was opened above.
        )
    # Return data to the caller.
    return data


# Define normalize ai insight for telegram for callers in this flow.
def normalize_ai_insight_for_telegram(text: str) -> str:
    """Normalize input values for the normalize ai insight for telegram workflow in the Telegram handler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    clean = str(text or "").strip()
    # Handle the missing or empty clean case.
    if not clean:
        return "Data belum cukup untuk membuat insight."

    # Telegram Markdown uses single asterisks for bold. Gemini often returns GitHub-style **bold**.
    clean = re.sub(r"\*\*(.+?)\*\*", r"*\1*", clean, flags=re.DOTALL)
    clean = re.sub(r"(?m)^\s*#{1,6}\s*(.+?)\s*$", r"*\1*", clean)

    # Convert Markdown list markers into a readable Telegram bullet.
    clean = re.sub(r"(?m)^\s*[-*]\s+", "• ", clean)
    clean = re.sub(r"(?m)^\s{2,}([•0-9])", r"\1", clean)
    clean = re.sub(r"(?m)^•\s+", "• ", clean)

    # Avoid raw JSON/key names leaking to user-facing text.
    key_labels = {
        "total_payable": "total utang",
        "total_receivable": "total piutang",
        "data_quality_issues": "masalah data quality",
        "top_expenses": "transaksi terbesar",
        "expense_by_category": "kategori pengeluaran",
        "monthly_context": "data bulanan",
        "relevant_transactions": "transaksi relevan",
    # Close the structure that was opened above.
    }
    # Process each raw_key, label in the current collection.
    for raw_key, label in key_labels.items():
        # Prepare clean for the next step.
        clean = clean.replace(raw_key, label)

    # Humanize any remaining snake_case key that slipped through.
    clean = re.sub(
        r"\b([A-Za-z]+(?:_[A-Za-z0-9]+)+)\b",
        lambda match: match.group(1).replace("_", " "),
        # Include this value in the surrounding collection or call.
        clean,
    # Close the structure that was opened above.
    )

    # Reduce over-nested spacing from Gemini.
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    clean = re.sub(r"(?m)^•\s+\*([^*]+)\*:\s*", r"• *\1:* ", clean)
    # Return clean.strip() to the caller.
    return clean.strip()


# Handle the asynchronous send finance insight reply workflow.
async def send_finance_insight_reply(
    # Include this value in the surrounding collection or call.
    update: Update,
    # Include this value in the surrounding collection or call.
    mode: str,
    # Include this value in the surrounding collection or call.
    context_data: dict,
    question: str = "",
    prefix: str = "🤖 Insight Gemini",
    # Include this value in the surrounding collection or call.
    context: ContextTypes.DEFAULT_TYPE | None = None,
    # Include this value in the surrounding collection or call.
    remember_history: bool = False,
# Close the structure that was opened above.
):
    """Handle the asynchronous send finance insight reply flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        context_data: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        question: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        prefix: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        context: Telegram callback context containing args, bot data, user data, and job data.
        remember_history: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    await update.message.reply_text("⏳ Mengambil data dan membuat insight...")
    # Prepare answer for the next step.
    answer = generate_finance_insight(mode, context_data, question=question)

    # Handle the case where remember_history and context is not None.
    if remember_history and context is not None:
        add_session_chat_history(context, "user", question)
        add_session_chat_history(context, "assistant", answer)

    text = f"{prefix}\n\n{normalize_ai_insight_for_telegram(answer)}"
    # Run this operation in a guarded block so failures can be handled.
    try:
        await update.message.reply_text(text, parse_mode="Markdown")
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Fallback keeps the answer readable if Gemini returns malformed Markdown.
        await update.message.reply_text(re.sub(r"[*`]", "", text))



# Handle the asynchronous examples handler workflow.
async def examples_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous examples handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Open a multi-line structure for the values below.
    text = (
        "🧪 *Contoh Input Cepat*\n\n"
        "Coba kirim salah satu contoh ini:\n\n"
        "*Transaksi biasa*\n"
        "• `beli kopi 20k dari Cash`\n"
        "• `bayar listrik 150k dari BRI`\n"
        "• `gaji masuk 8jt ke BCA`\n\n"
        "*Transfer*\n"
        "• `BCA ke DANA 200k`\n"
        "• `tf gopay 100k dari BRI`\n\n"
        "*Utang, piutang, dan talangan*\n"
        "• `Budi minjem 50k`\n"
        "• `catat utang ke Budi 200k`\n"
        "• `Budi bayar hutang 100k Cash`\n"
        "• `saya talangin Rina beli makan 40k`\n\n"
        "*Split bill*\n"
        "• `galon 24k dibagi 4`\n"
        "• `makan 80k bagi dua sama Budi`\n\n"
        "*AI finance insight*\n"
        "• `/ask bulan ini boros di mana?`\n"
        "• `/audit`\n"
        "• `/coach`\n"
        "• `/grafik bar 2026-06`\n\n"
        "Catatan: input yang ambigu akan diminta klarifikasi atau ditampilkan sebagai warning preview sebelum disimpan."
    # Close the structure that was opened above.
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# Handle the asynchronous insight handler workflow.
async def insight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous insight handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    month_arg = " ".join(context.args).strip() if context.args else None
    # Prepare month for the next step.
    month = normalize_insight_month(month_arg)
    # Prepare data for the next step.
    data = build_monthly_finance_context(month)
    # Wait for send_finance_insight_reply before continuing this flow.
    await send_finance_insight_reply(
        # Include this value in the surrounding collection or call.
        update,
        "monthly_insight",
        # Include this value in the surrounding collection or call.
        data,
        question=f"Buat insight/narasi keuangan untuk {month}",
        prefix=f"📌 Insight Finance {month}",
    # Close the structure that was opened above.
    )


# Handle the asynchronous audit handler workflow.
async def audit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous audit handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    month_arg = " ".join(context.args).strip() if context.args else None
    # Prepare month for the next step.
    month = normalize_insight_month(month_arg)
    # Prepare data for the next step.
    data = build_audit_context(month)
    # Wait for send_finance_insight_reply before continuing this flow.
    await send_finance_insight_reply(
        # Include this value in the surrounding collection or call.
        update,
        "audit",
        # Include this value in the surrounding collection or call.
        data,
        question=f"Audit data finance dan anomali untuk {month}",
        prefix=f"🧹 Audit Finance {month}",
    # Close the structure that was opened above.
    )


# Handle the asynchronous ask handler workflow.
async def ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous ask handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    question = " ".join(context.args).strip()
    # Handle the missing or empty question case.
    if not question:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Tulis pertanyaannya setelah `/ask`.\n\n"
            "Contoh:\n"
            "`/ask bulan ini boros di mana?`\n"
            "`/ask kapan terakhir saya beli kopi?`\n"
            "`/ask budget makan aman gak?`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare mode for the next step.
    mode = route_finance_question_mode(question)
    if mode == "audit":
        # Prepare data for the next step.
        data = build_audit_context(None)
    elif mode == "coach":
        # Prepare data for the next step.
        data = build_coach_context(None, question=question)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare data for the next step.
        data = build_ask_finance_context(question)

    # Prepare data for the next step.
    data = attach_session_history(context, data)
    # Wait for send_finance_insight_reply before continuing this flow.
    await send_finance_insight_reply(
        # Include this value in the surrounding collection or call.
        update,
        # Include this value in the surrounding collection or call.
        mode,
        # Include this value in the surrounding collection or call.
        data,
        # Prepare question for the next step.
        question=question,
        prefix="💬 Jawaban Finance",
        # Prepare context for the next step.
        context=context,
        # Prepare remember history for the next step.
        remember_history=True,
    # Close the structure that was opened above.
    )


# Handle the asynchronous coach handler workflow.
async def coach_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous coach handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    question = " ".join(context.args).strip() if context.args else "Kasih saran finansial ringan untuk bulan ini."
    # Prepare data for the next step.
    data = build_coach_context(None, question=question)
    # Prepare data for the next step.
    data = attach_session_history(context, data)
    # Wait for send_finance_insight_reply before continuing this flow.
    await send_finance_insight_reply(
        # Include this value in the surrounding collection or call.
        update,
        "coach",
        # Include this value in the surrounding collection or call.
        data,
        # Prepare question for the next step.
        question=question,
        prefix="🧭 Finance Coach",
        # Prepare context for the next step.
        context=context,
        # Prepare remember history for the next step.
        remember_history=True,
    # Close the structure that was opened above.
    )


# Handle the asynchronous handle natural finance question workflow.
async def handle_natural_finance_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Handle the asynchronous handle natural finance question flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.
        user_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty should_handle_finance_question(user_text) case.
    if not should_handle_finance_question(user_text):
        # Return False to the caller.
        return False

    # Prepare mode for the next step.
    mode = route_finance_question_mode(user_text)
    if mode == "audit":
        # Prepare data for the next step.
        data = build_audit_context(None)
    elif mode == "coach":
        # Prepare data for the next step.
        data = build_coach_context(None, question=user_text)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare data for the next step.
        data = build_ask_finance_context(user_text)

    # Prepare data for the next step.
    data = attach_session_history(context, data)
    # Wait for send_finance_insight_reply before continuing this flow.
    await send_finance_insight_reply(
        # Include this value in the surrounding collection or call.
        update,
        # Include this value in the surrounding collection or call.
        mode,
        # Include this value in the surrounding collection or call.
        data,
        # Prepare question for the next step.
        question=user_text,
        prefix="🤖 Analisis Finance",
        # Prepare context for the next step.
        context=context,
        # Prepare remember history for the next step.
        remember_history=True,
    # Close the structure that was opened above.
    )
    # Return True to the caller.
    return True


# Define format report delta for callers in this flow.
def format_report_delta(delta_info: dict, *, positive_when_up: bool, as_count: bool = False) -> str:
    """Format data into a readable display for report delta."""
    if not delta_info or delta_info.get("available") is False or delta_info.get("delta") is None:
        return "~"

    delta = float(delta_info.get("delta", 0) or 0)
    pct = delta_info.get("pct")

    # Handle the case where abs(delta) < 0.0001.
    if abs(delta) < 0.0001:
        value_text = "0 item" if as_count else format_rupiah(0)
        return f"⚪= {value_text}"

    arrow = "▲" if delta > 0 else "▼"
    # Prepare is good for the next step.
    is_good = (delta > 0) if positive_when_up else (delta < 0)
    color = "🟢" if is_good else "🔴"
    sign = "+" if delta > 0 else "-"

    # Handle the case where as_count.
    if as_count:
        value_text = f"{sign}{abs(int(round(delta)))} item"
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare value text for the next step.
        value_text = f"{sign}{format_rupiah(abs(delta))}"

    pct_text = ""
    # Handle the case where pct is not None.
    if pct is not None:
        pct_text = f" ({pct:+.1f}%)"

    return f"{color}{arrow} {value_text}{pct_text}"


# Define append report comparison lines for callers in this flow.
def append_report_comparison_lines(lines: list[str], report: dict, label: str):
    """Apply the append report comparison lines operation in the Telegram handler layer.

    Args:
        lines: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        report: Report dict produced by the report service.
        label: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    comparison = (report or {}).get("comparison") or {}
    # Handle the missing or empty comparison case.
    if not comparison:
        # Return control to the caller.
        return

    lines.append(f"📈 Vs {label}:")
    lines.append(f"   ✅ Pemasukan : {format_report_delta(comparison.get('total_income'), positive_when_up=True)}")
    lines.append(f"   ❌ Pengeluaran: {format_report_delta(comparison.get('total_expense'), positive_when_up=False)}")
    lines.append(f"   📊 Net       : {format_report_delta(comparison.get('net'), positive_when_up=True)}")
    lines.append(f"   📝 Transaksi : {format_report_delta(comparison.get('count'), positive_when_up=False, as_count=True)}\n")


# Define get report expense display for callers in this flow.
def get_report_expense_display(report: dict) -> str:
    """Retrieve data needed by the get report expense display workflow in the Telegram handler layer.

    Args:
        report: Report dict produced by the report service.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    net = float((report or {}).get("total_expense", 0) or 0)
    gross = float((report or {}).get("total_gross_expense", net) or 0)
    # Return format_expense_net_gross(float(net or 0), gross) to the caller.
    return format_expense_net_gross(float(net or 0), gross)


# Define append report metric lines for callers in this flow.
def append_report_metric_lines(lines: list[str], report: dict):
    """Apply the append report metric lines operation in the Telegram handler layer.

    Args:
        lines: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        report: Report dict produced by the report service.

    Returns:
        `None` after completing the operation.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    account_filter = (report or {}).get("account_filter")
    # Handle the case where account_filter.
    if account_filter:
        lines.append(f"🏦 Rekening : *{md_safe(account_filter)}*")
        category_filter = (report or {}).get("category_filter")
        # Handle the case where category_filter.
        if category_filter:
            lines.append(f"📁 Kategori : *{md_safe(category_filter)}*")
        lines.append(f"✅ Pemasukan      : *{format_rupiah(report.get('total_income', 0))}*")
        lines.append(f"❌ Pengeluaran    : *{get_report_expense_display(report)}*")
        lines.append(f"🔁 Transfer Masuk : *{format_rupiah(report.get('total_transfer_in', 0))}*")
        lines.append(f"🔁 Transfer Keluar: *{format_rupiah(report.get('total_transfer_out', 0))}*")
        lines.append(f"📊 Net Rekening   : *{format_rupiah(report.get('net', 0))}*")
        lines.append(f"📝 Transaksi      : {report.get('count', 0)} item")
        # Return control to the caller.
        return

    lines.append(f"✅ Pemasukan : *{format_rupiah(report['total_income'])}*")
    lines.append(f"❌ Pengeluaran: *{get_report_expense_display(report)}*")
    lines.append(f"📊 Net       : *{format_rupiah(report['net'])}*")
    lines.append(f"📝 Transaksi : {report['count']} item")


# Define append account report lines for callers in this flow.
def append_account_report_lines(lines: list[str], report: dict):
    """Apply the append account report lines operation in the Telegram handler layer.

    Args:
        lines: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        report: Report dict produced by the report service.

    Returns:
        `None` after completing the operation.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    account = (report or {}).get("account_filter") or "-"
    balance = (report or {}).get("account_balance")
    lines.append(f"🏦 Rekening : *{md_safe(account)}*")
    # Handle the case where balance is not None.
    if balance is not None:
        lines.append(f"💰 Saldo Saat Ini : *{format_rupiah(balance)}*")
    lines.append(f"✅ Pemasukan      : *{format_rupiah(report.get('total_income', 0))}*")
    lines.append(f"❌ Pengeluaran    : *{get_report_expense_display(report)}*")
    lines.append(f"🔁 Transfer Masuk : *{format_rupiah(report.get('total_transfer_in', 0))}*")
    lines.append(f"🔁 Transfer Keluar: *{format_rupiah(report.get('total_transfer_out', 0))}*")
    lines.append(f"📊 Pergerakan Bersih: *{format_rupiah(report.get('net', 0))}*")
    lines.append(f"📝 Transaksi      : {report.get('count', 0)} item")


# Define append recent account transaction lines for callers in this flow.
def append_recent_account_transaction_lines(lines: list[str], report: dict, limit: int = 8):
    """Apply the append recent account transaction lines operation in the Telegram handler layer.

    Args:
        lines: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        report: Report dict produced by the report service.
        limit: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    transactions = (report or {}).get("transactions") or []
    # Handle the missing or empty transactions case.
    if not transactions:
        # Return control to the caller.
        return

    lines.append("\n*Transaksi Terbaru Rekening:*")
    # Process each i, txn in the current collection.
    for i, txn in enumerate(transactions[:limit], 1):
        # Update lines with the current value.
        lines.extend(build_transaction_display_lines(txn, index=i, include_date=True, include_id=True))

# Define append report category breakdown lines for callers in this flow.
def append_report_category_breakdown_lines(lines: list[str], report: dict, comparison_label: str):
    """Apply the append report category breakdown lines operation in the Telegram handler layer.

    Args:
        lines: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        report: Report dict produced by the report service.
        comparison_label: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Keep category name, type, symbol, and alias behavior consistent with the documented category flow.
    """
    by_category = (report or {}).get("by_category") or {}
    # Handle the missing or empty by_category case.
    if not by_category:
        # Return control to the caller.
        return

    lines.append("*Pengeluaran per Kategori:*")
    total_expense = float((report or {}).get("total_expense", 0) or 0)
    category_comparison = (report or {}).get("category_comparison") or {}
    by_category_gross = (report or {}).get("by_category_gross") or {}

    # Process each cat, amount in the current collection.
    for cat, amount in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        # Prepare pct for the next step.
        pct = (float(amount) / total_expense) * 100 if total_expense else 0
        # Prepare bar for the next step.
        bar = build_progress_bar(pct)
        # Prepare trend for the next step.
        trend = format_report_delta(category_comparison.get(cat), positive_when_up=False)
        trend_text = f" | vs {comparison_label}: {trend}" if comparison_label else ""
        # Prepare gross amount for the next step.
        gross_amount = by_category_gross.get(cat, amount)
        # Prepare amount text for the next step.
        amount_text = format_expense_net_gross(float(amount or 0), float(gross_amount or 0))
        # Open a multi-line structure for the values below.
        lines.append(
            f"  • {md_safe(cat)}: *{amount_text}*\n"
            f"    {bar} {pct:.1f}%{trend_text}"
        # Close the structure that was opened above.
        )


# Define build top expense debt lines for callers in this flow.
def build_top_expense_debt_lines(txn: dict, amount: float) -> list[str]:
    """Build the data structure or message text for top expense debt lines."""
    # Return [] to the caller.
    return []


# Define get top expense transactions for callers in this flow.
def get_top_expense_transactions(report: dict, limit: int = 3) -> list[dict]:
    """Return expense transactions sorted by net expense amount.

    Args:
        report: Report dict from `/harian`, `/mingguan`, or `/bulanan`.
        limit: Maximum number of transactions to return.

    Returns:
        Expense rows sorted descending by net amount after receivable shares.
    """
    # Open a multi-line structure for the values below.
    expenses = [
        t for t in (report or {}).get("transactions", [])
        if str((t or {}).get("type", "")).strip().lower() == "expense"
        # Run this statement as part of the current workflow.
        and get_net_expense_after_receivable(t) > 0
    # Close the structure that was opened above.
    ]
    # Return sorted(expenses, key=get_net_expense_after_receivable, revers... to the caller.
    return sorted(expenses, key=get_net_expense_after_receivable, reverse=True)[:limit]


# Define append top expense lines for callers in this flow.
def append_top_expense_lines(lines: list[str], report: dict):
    """Append Top 3 expense lines using net expense contribution.

    Args:
        lines: Mutable Markdown line list for the report response.
        report: Daily, weekly, or monthly report dict with enriched
            `transactions` and net-based `total_expense`.

    Returns:
        None. The function mutates `lines` in place only when expenses exist.
    """
    # Prepare top for the next step.
    top = get_top_expense_transactions(report, limit=3)
    # Handle the missing or empty top case.
    if not top:
        # Return control to the caller.
        return

    lines.append("\n*Top 3 Pengeluaran:*")
    total_expense = float((report or {}).get("total_expense", 0) or 0)

    # Process each i, txn in the current collection.
    for i, txn in enumerate(top, 1):
        # Prepare amount for the next step.
        amount = get_net_expense_after_receivable(txn)
        # Prepare contrib for the next step.
        contrib = (amount / total_expense * 100) if total_expense else 0
        # Open a multi-line structure for the values below.
        lines.extend(
            # Open a multi-line structure for the values below.
            build_transaction_display_lines(
                # Include this value in the surrounding collection or call.
                txn,
                # Prepare index for the next step.
                index=i,
                # Prepare include date for the next step.
                include_date=True,
                # Prepare include id for the next step.
                include_id=True,
                # Prepare contribution pct for the next step.
                contribution_pct=contrib,
            # Close the structure that was opened above.
            )
        # Close the structure that was opened above.
        )


# Define normalize chart type for callers in this flow.
def normalize_chart_type(value: str | None) -> str | None:
    """Normalize user chart type input into a supported chart type.

    Args:
        value: Raw chart token such as `line`, `bar`, `pie`, or Indonesian
            aliases such as `kategori`.

    Returns:
        `timeseries`, `bar`, `pie`, or `None` when the token is not a chart
        type.
    """
    raw = str(value or "").strip().lower()
    if raw in {"line", "time", "timeseries", "time_series", "series", "tren", "trend"}:
        return "timeseries"
    if raw in {"bar", "barchart", "bar_chart", "batang", "pengeluaran"}:
        return "bar"
    if raw in {"pie", "piechart", "pie_chart", "kategori", "category"}:
        return "pie"
    # Return None to the caller.
    return None


# Define parse grafik args for callers in this flow.
def parse_grafik_args(args: list[str] | None) -> tuple[str, str | None]:
    """Parse `/grafik` arguments into chart type and month argument.

    Args:
        args: Telegram command args after `/grafik`.

    Returns:
        Tuple of `(chart_type, month_arg)`. Chart type defaults to `timeseries`;
        month argument defaults to `None`, which means current month.
    """
    chart_type = "timeseries"
    # Prepare month tokens for the next step.
    month_tokens = []
    # Process each token in the current collection.
    for token in args or []:
        # Prepare normalized type for the next step.
        normalized_type = normalize_chart_type(token)
        # Handle the case where normalized_type.
        if normalized_type:
            # Prepare chart type for the next step.
            chart_type = normalized_type
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Update month tokens with the current value.
        month_tokens.append(token)
    month_arg = " ".join(month_tokens).strip() or None
    # Return chart_type, month_arg to the caller.
    return chart_type, month_arg


async def send_monthly_chart_document(update: Update, report: dict, chart_type: str = "timeseries"):
    """Generate and send a monthly PNG chart, then remove its temp file.

    Args:
        update: Telegram update used to reply with a document.
        report: Monthly report dict used as chart data source.
        chart_type: `timeseries`, `bar`, or `pie`.

    Returns:
        None. The generated file is sent as a Telegram document and then
        removed from the local temporary directory.
    """
    # Prepare chart path for the next step.
    chart_path = write_monthly_chart_png(report, chart_type)
    month_label = str((report or {}).get("month") or "bulan").replace("/", "-")
    filename = f"grafik-{chart_type}-{month_label}.png"
    # Open a multi-line structure for the values below.
    caption = (
        f"📈 Grafik {chart_type} {month_label}\n"
        "Basis angka: pengeluaran net setelah piutang split bill/talangan."
    # Close the structure that was opened above.
    )
    # Run this operation in a guarded block so failures can be handled.
    try:
        with open(chart_path, "rb") as file_obj:
            # Wait for update.message.reply_document before continuing this flow.
            await update.message.reply_document(
                # Prepare document for the next step.
                document=InputFile(file_obj, filename=filename),
                # Prepare caption for the next step.
                caption=caption,
            # Close the structure that was opened above.
            )
    # Run cleanup that must happen after the guarded operation.
    finally:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Update os with the current value.
            os.remove(chart_path)
        # Handle an expected failure from the guarded operation above.
        except OSError:
            # Keep this intentionally empty block valid.
            pass


# Define is category detail report for callers in this flow.
def is_category_detail_report(report: dict) -> bool:
    """Check whether a condition is true for category detail report."""
    return bool((report or {}).get("category_filter"))


# Define get category list title for callers in this flow.
def get_category_list_title(category: str) -> str:
    """Retrieve data needed by the get category list title workflow in the Telegram handler layer.

    Args:
        category: Category name or category-like value from user input or sheet data.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep category name, type, symbol, and alias behavior consistent with the documented category flow.
    """
    category_lower = str(category or "").strip().lower()
    if category_lower == "food & beverage":
        return "🍽 *Daftar Makanan/Minuman:*"
    return f"📋 *Daftar Transaksi {md_safe(category)}:*"


# Define append category detail summary for callers in this flow.
def append_category_detail_summary(lines: list[str], report: dict, comparison_label: str):
    """Apply the append category detail summary operation in the Telegram handler layer.

    Args:
        lines: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        report: Report dict produced by the report service.
        comparison_label: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Keep category name, type, symbol, and alias behavior consistent with the documented category flow.
    """
    category = (report or {}).get("category_filter") or "-"
    account = (report or {}).get("account_filter")
    total_income = float((report or {}).get("total_income", 0) or 0)
    total_expense = float((report or {}).get("total_expense", 0) or 0)
    total_transfer = float((report or {}).get("total_transfer", 0) or 0)

    lines.append(f"📁 Kategori : *{md_safe(category)}*")
    # Handle the case where account.
    if account:
        lines.append(f"🏦 Rekening : *{md_safe(account)}*")
    # Handle the case where total_income > 0.
    if total_income > 0:
        lines.append(f"✅ Pemasukan : *{format_rupiah(total_income)}*")
    # Handle the case where total_expense > 0 or total_income == 0.
    if total_expense > 0 or total_income == 0:
        lines.append(f"❌ Pengeluaran: *{get_report_expense_display(report)}*")
    # Handle the case where account.
    if account:
        transfer_in = float((report or {}).get("total_transfer_in", 0) or 0)
        transfer_out = float((report or {}).get("total_transfer_out", 0) or 0)
        # Handle the case where transfer_in > 0.
        if transfer_in > 0:
            lines.append(f"🔁 Transfer Masuk : *{format_rupiah(transfer_in)}*")
        # Handle the case where transfer_out > 0.
        if transfer_out > 0:
            lines.append(f"🔁 Transfer Keluar: *{format_rupiah(transfer_out)}*")
    # Handle the alternate case where total_transfer > 0.
    elif total_transfer > 0:
        lines.append(f"🔄 Transfer   : *{format_rupiah(total_transfer)}*")
    # Handle the case where total_income > 0 and total_expense > 0.
    if total_income > 0 and total_expense > 0:
        lines.append(f"📊 Net       : *{format_rupiah((report or {}).get('net', 0))}*")
    lines.append(f"📝 Transaksi : {(report or {}).get('count', 0)} item")
    # Run this statement as part of the current workflow.
    append_report_comparison_lines(lines, report, comparison_label)


# Define append category transaction lines for callers in this flow.
def append_category_transaction_lines(lines: list[str], report: dict, *, include_date: bool):
    """Apply the append category transaction lines operation in the Telegram handler layer.

    Args:
        lines: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        report: Report dict produced by the report service.
        include_date: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Keep category name, type, symbol, and alias behavior consistent with the documented category flow.
    """
    category = (report or {}).get("category_filter") or "-"
    transactions = (report or {}).get("transactions") or []
    # Handle the missing or empty transactions case.
    if not transactions:
        # Return control to the caller.
        return

    # Update lines with the current value.
    lines.append(get_category_list_title(category))

    # Process each i, t in the current collection.
    for i, t in enumerate(transactions, 1):
        note = str(t.get("catatan", "") or "").strip()
        # Open a multi-line structure for the values below.
        lines.extend(
            # Open a multi-line structure for the values below.
            build_transaction_display_lines(
                # Include this value in the surrounding collection or call.
                t,
                # Prepare index for the next step.
                index=i,
                # Prepare include date for the next step.
                include_date=include_date,
                # Prepare include id for the next step.
                include_id=True,
                # Prepare note for the next step.
                note=note or None,
            # Close the structure that was opened above.
            )
        # Close the structure that was opened above.
        )



# Handle the asynchronous saldo handler workflow.
async def saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous saldo handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare accounts for the next step.
    accounts = get_all_accounts()
    # Handle the missing or empty accounts case.
    if not accounts:
        await update.message.reply_text("❌ Tidak ada data rekening.")
        # Return control to the caller.
        return

    total = sum(float(acc.get("balance", 0) or 0) for acc in accounts)
    lines = ["💰 *Saldo Rekening*\n"]

    # Open a multi-line structure for the values below.
    emoji_map = {
        "cash": "💵",
        "bank": "🏦",
        "ewallet": "📱",
    # Close the structure that was opened above.
    }

    # Process each acc in the current collection.
    for acc in accounts:
        emoji = emoji_map.get(str(acc.get("type", "")).lower(), "💳")
        name = acc.get("account_name", "")
        balance = float(acc.get("balance", 0) or 0)
        lines.append(f"{emoji} {name}: *{format_rupiah(balance)}*")

    lines.append(f"\n📊 Total: *{format_rupiah(total)}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# Handle the asynchronous rekening handler workflow.
async def rekening_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous rekening handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    raw_arg = " ".join(context.args).strip() if context.args else ""

    # Implementation note for this project-specific finance flow.
    if not raw_arg:
        # Wait for saldo_handler before continuing this flow.
        await saldo_handler(update, context)
        # Return control to the caller.
        return

    # Run this statement as part of the current workflow.
    account_arg, period_arg = split_account_period_arg(raw_arg)
    # Handle the missing or empty account_arg case.
    if not account_arg:
        # Wait for saldo_handler before continuing this flow.
        await saldo_handler(update, context)
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare report for the next step.
        report = get_account_report(account_arg, period_arg)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/rekening Cash`\n"
            "`/rekening Dana 2026-06`\n"
            "`/rekening BCA all`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    account = report.get("account_filter") or account_arg
    period_label = report.get("period_label") or report.get("month") or "-"

    if report.get("count", 0) == 0:
        # Open a multi-line structure for the values below.
        lines = [
            f"🏦 *Ringkasan Rekening*\n_{md_safe(period_label)}_\n",
            f"🏦 Rekening : *{md_safe(account)}*",
        # Close the structure that was opened above.
        ]
        balance = report.get("account_balance")
        # Handle the case where balance is not None.
        if balance is not None:
            lines.append(f"💰 Saldo Saat Ini : *{format_rupiah(balance)}*")
        lines.append("📭 Belum ada transaksi rekening ini pada periode tersebut.")
        await reply_long_markdown(update, "\n".join(lines))
        # Return control to the caller.
        return

    # Open a multi-line structure for the values below.
    transactions = sorted(
        report.get("transactions", []) or [],
        key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)),
        # Prepare reverse for the next step.
        reverse=True,
    # Close the structure that was opened above.
    )

    # Prepare last map for the next step.
    last_map = {}
    # Process each i, txn in the current collection.
    for i, txn in enumerate(transactions, 1):
        if txn.get("_row_index"):
            # Open a multi-line structure for the values below.
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            # Close the structure that was opened above.
            }
    context.user_data["last_txn_map"] = last_map

    title = f"Transaksi Rekening {account} — {period_label}"
    # Wait for reply_long_markdown before continuing this flow.
    await reply_long_markdown(
        # Include this value in the surrounding collection or call.
        update,
        # Open a multi-line structure for the values below.
        build_transactions_full_text_shared(
            # Include this value in the surrounding collection or call.
            transactions,
            # Include this value in the surrounding collection or call.
            title,
            # Include this value in the surrounding collection or call.
            account,
            current_balance=report.get("account_balance"),
        # Close the structure that was opened above.
        ),
    # Close the structure that was opened above.
    )



# Handle the asynchronous harian handler workflow.
async def harian_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous harian handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    raw_arg = " ".join(context.args).strip() if context.args else None
    date_arg, category_arg, account_arg = split_report_filter_args(raw_arg, "date")

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare report for the next step.
        report = get_daily_report(date_arg, category_arg, account_arg)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Wait for update.message.reply_text before continuing this flow.
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
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    date_str = report["date"]
    category_filter = report.get("category_filter")
    account_filter = report.get("account_filter")

    if report["count"] == 0:
        # Handle the case where category_filter or account_filter.
        if category_filter or account_filter:
            # Prepare filter bits for the next step.
            filter_bits = []
            # Handle the case where category_filter.
            if category_filter:
                filter_bits.append(f"kategori *{md_safe(category_filter)}*")
            # Handle the case where account_filter.
            if account_filter:
                filter_bits.append(f"rekening *{md_safe(account_filter)}*")
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"📭 Tidak ada transaksi {' dan '.join(filter_bits)} pada {date_str}.",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
        # Handle the fallback path after earlier conditions are skipped.
        else:
            await update.message.reply_text(f"📭 Belum ada transaksi hari ini ({date_str}).")
        # Return control to the caller.
        return

    # Handle the case where is_category_detail_report(report).
    if is_category_detail_report(report):
        lines = [f"📅 *Detail Harian*\n_{date_str}_\n"]
        append_net_gross_note(lines, report.get("transactions"))
        append_category_detail_summary(lines, report, "hari sebelumnya")
        # Run this statement as part of the current workflow.
        append_category_transaction_lines(lines, report, include_date=False)
        await reply_long_markdown(update, "\n".join(lines))
        # Return control to the caller.
        return

    lines = [f"📅 *Ringkasan Harian*\n_{date_str}_\n"]
    append_net_gross_note(lines, report.get("transactions"))
    # Run this statement as part of the current workflow.
    append_report_metric_lines(lines, report)
    append_report_comparison_lines(lines, report, "hari sebelumnya")

    append_report_category_breakdown_lines(lines, report, "hari sebelumnya")

    # Run this statement as part of the current workflow.
    append_top_expense_lines(lines, report)

    await reply_long_markdown(update, "\n".join(lines))


# Handle the asynchronous mingguan handler workflow.
async def mingguan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous mingguan handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    raw_arg = " ".join(context.args).strip() if context.args else None
    date_arg, category_arg, account_arg = split_report_filter_args(raw_arg, "date")

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare report for the next step.
        report = get_weekly_report(date_arg, category_arg, account_arg)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Wait for update.message.reply_text before continuing this flow.
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
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    category_filter = report.get("category_filter")
    account_filter = report.get("account_filter")

    if report["count"] == 0:
        # Handle the case where category_filter or account_filter.
        if category_filter or account_filter:
            # Prepare filter bits for the next step.
            filter_bits = []
            # Handle the case where category_filter.
            if category_filter:
                filter_bits.append(f"kategori *{md_safe(category_filter)}*")
            # Handle the case where account_filter.
            if account_filter:
                filter_bits.append(f"rekening *{md_safe(account_filter)}*")
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"📭 Tidak ada transaksi {' dan '.join(filter_bits)} minggu ini.\n"
                f"({report['date_from']} s/d {report['date_to']})",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"📭 Belum ada transaksi minggu ini.\n"
                f"({report['date_from']} s/d {report['date_to']})"
            # Close the structure that was opened above.
            )
        # Return control to the caller.
        return

    # Handle the case where is_category_detail_report(report).
    if is_category_detail_report(report):
        # Open a multi-line structure for the values below.
        lines = [
            f"📆 *Detail Mingguan*\n"
            f"_{report['date_from']} s/d {report['date_to']}_\n"
        # Close the structure that was opened above.
        ]
        append_net_gross_note(lines, report.get("transactions"))
        append_category_detail_summary(lines, report, "minggu sebelumnya")
        # Run this statement as part of the current workflow.
        append_category_transaction_lines(lines, report, include_date=True)
        await reply_long_markdown(update, "\n".join(lines))
        # Return control to the caller.
        return

    # Open a multi-line structure for the values below.
    lines = [
        f"📆 *Ringkasan Mingguan*\n"
        f"_{report['date_from']} s/d {report['date_to']}_\n"
    # Close the structure that was opened above.
    ]
    append_net_gross_note(lines, report.get("transactions"))
    # Run this statement as part of the current workflow.
    append_report_metric_lines(lines, report)
    append_report_comparison_lines(lines, report, "minggu sebelumnya")

    append_report_category_breakdown_lines(lines, report, "minggu sebelumnya")

    # Run this statement as part of the current workflow.
    append_top_expense_lines(lines, report)

    await reply_long_markdown(update, "\n".join(lines))


# Handle the asynchronous grafik handler workflow.
async def grafik_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle `/grafik` monthly chart requests.

    Accepted input examples:
        `/grafik`
        `/grafik 2026-06`
        `/grafik bar 2026-06`
        `/grafik pie 2026-06`

    The command never writes to Google Sheets. It only reads the monthly report
    and sends a PNG chart document.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Run this statement as part of the current workflow.
    chart_type, month_arg = parse_grafik_args(context.args)

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Run this statement as part of the current workflow.
        year, month_num = parse_report_month_arg(month_arg)
        # Prepare report for the next step.
        report = get_monthly_report(year, month_num)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/grafik`\n"
            "`/grafik 2026-06`\n"
            "`/grafik line 2026-06`\n"
            "`/grafik bar 2026-06`\n"
            "`/grafik pie 2026-06`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    if report.get("count", 0) == 0:
        await update.message.reply_text(f"📭 Belum ada transaksi untuk {report.get('month', '-')}.")
        # Return control to the caller.
        return

    # Wait for send_monthly_chart_document before continuing this flow.
    await send_monthly_chart_document(update, report, chart_type)


# Handle the asynchronous bulanan handler workflow.
async def bulanan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous bulanan handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    raw_arg = " ".join(context.args).strip() if context.args else None
    month_arg, category_arg, account_arg = split_report_filter_args(raw_arg, "month")

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Run this statement as part of the current workflow.
        year, month_num = parse_report_month_arg(month_arg)
        # Prepare report for the next step.
        report = get_monthly_report(year, month_num, category_arg, account_arg)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Wait for update.message.reply_text before continuing this flow.
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
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    month_name = report.get("month", "-")
    category_filter = report.get("category_filter")
    account_filter = report.get("account_filter")

    if report["count"] == 0:
        # Handle the case where category_filter or account_filter.
        if category_filter or account_filter:
            # Prepare filter bits for the next step.
            filter_bits = []
            # Handle the case where category_filter.
            if category_filter:
                filter_bits.append(f"kategori *{md_safe(category_filter)}*")
            # Handle the case where account_filter.
            if account_filter:
                filter_bits.append(f"rekening *{md_safe(account_filter)}*")
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"📭 Tidak ada transaksi {' dan '.join(filter_bits)} pada {month_name}.",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
        # Handle the fallback path after earlier conditions are skipped.
        else:
            await update.message.reply_text("📭 Belum ada transaksi bulan ini.")
        # Return control to the caller.
        return

    # Handle the case where is_category_detail_report(report).
    if is_category_detail_report(report):
        lines = [f"📆 *Detail Bulanan*\n_{month_name}_\n"]
        append_net_gross_note(lines, report.get("transactions"))
        append_category_detail_summary(lines, report, "bulan lalu")
        # Run this statement as part of the current workflow.
        append_category_transaction_lines(lines, report, include_date=True)
        await reply_long_markdown(update, "\n".join(lines))
        # Return control to the caller.
        return

    lines = [f"📆 *Ringkasan Bulanan*\n_{month_name}_\n"]
    append_net_gross_note(lines, report.get("transactions"))
    # Run this statement as part of the current workflow.
    append_report_metric_lines(lines, report)
    append_report_comparison_lines(lines, report, "bulan lalu")

    append_report_category_breakdown_lines(lines, report, "bulan lalu")

    # Run this statement as part of the current workflow.
    append_top_expense_lines(lines, report)

    # Prepare budget summary for the next step.
    budget_summary = get_budget_summary(month_name)
    # Handle the case where budget_summary.
    if budget_summary:
        lines.append("\n*Budget vs Realisasi:*")
        # Process each item in the current collection.
        for item in budget_summary:
            bar = build_progress_bar(item["pct_used"])
            # Open a multi-line structure for the values below.
            lines.append(
                f"{item['emoji']} {item['category']}\n"
                f"  {bar} {item['pct_used']}%"
            # Close the structure that was opened above.
            )

    await reply_long_markdown(update, "\n".join(lines))

    # Automatic insight after /bulanan.
    # Message handling section
    try:
        # Prepare insight data for the next step.
        insight_data = build_monthly_finance_context(month_name)
        # Open a multi-line structure for the values below.
        insight_text = generate_finance_insight(
            "monthly_auto",
            # Include this value in the surrounding collection or call.
            insight_data,
            question=f"Buat insight singkat otomatis setelah laporan bulanan {month_name}",
        # Close the structure that was opened above.
        )
        await update.message.reply_text(f"🤖 Insight Bulanan Gemini\n\n{insight_text}")
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"⚠️ Ringkasan bulanan berhasil, tapi insight Gemini gagal dibuat: {str(e)}"
        # Close the structure that was opened above.
        )


    # Wait for send_bulanan_timeseries_chart before continuing this flow.
    await send_bulanan_timeseries_chart(update, report)


# Handle the asynchronous send bulanan timeseries chart workflow.
async def send_bulanan_timeseries_chart(update: Update, report: dict):
    """Send the third `/bulanan` output: monthly net expense time series.

    Args:
        update: Telegram update used to send the chart document or warning.
        report: Monthly report dict that already powers the text summary.

    Returns:
        None. Failures are reported to the user without blocking the already
        delivered monthly summary and Gemini insight.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        await send_monthly_chart_document(update, report, "timeseries")
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"⚠️ Ringkasan dan insight sudah terkirim, tapi grafik time series gagal dibuat: {str(e)}"
        # Close the structure that was opened above.
        )


# Handle the asynchronous cari handler workflow.
async def cari_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous cari handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare args for the next step.
    args = context.args
    # Handle the missing or empty args case.
    if not args:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "🔍 Masukkan keyword pencarian.\n"
            "Contoh: `/cari kopi`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    keyword = " ".join(args)
    # Prepare results for the next step.
    results = search_transactions(keyword)

    # Handle the missing or empty results case.
    if not results:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"🔍 Tidak ada transaksi dengan keyword *{md_safe(keyword)}*.",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    lines = [f"🔍 *Hasil pencarian: \"{md_safe(keyword)}\"*\n"]
    # Run this statement as part of the current workflow.
    append_net_gross_note(lines, results)

    # Process each i, t in the current collection.
    for i, t in enumerate(results, 1):
        # Update lines with the current value.
        lines.extend(build_transaction_display_lines(t, index=i, include_date=True, include_id=True))

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# Define format budget net gross for callers in this flow.
def format_budget_net_gross(net_amount: float, gross_amount: float) -> str:
    """Format data into a readable display for budget net gross."""
    # Prepare net for the next step.
    net = float(net_amount or 0)
    # Prepare gross for the next step.
    gross = float(gross_amount or 0)
    # Handle the case where abs(net - gross) > 0.0001.
    if abs(net - gross) > 0.0001:
        return f"{format_rupiah(net)} ({format_rupiah(gross)})"
    # Return format_rupiah(net) to the caller.
    return format_rupiah(net)

# Handle the asynchronous budget handler workflow.
async def budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous budget handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare month arg for the next step.
    month_arg = context.args[0] if context.args else None

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare month for the next step.
        month = normalize_month(month_arg)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/budget`\n"
            "`/budget 2026-06`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare summary for the next step.
    summary = get_budget_summary(month)

    # Handle the missing or empty summary case.
    if not summary:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"📭 Belum ada budget untuk *{format_month_label(month)}*.\n\n"
            "Set budget dengan cara:\n"
            "`budget makan 1.5 juta`\n"
            "`budget transport 300rb`\n"
            "`budget makan 1.5 juta 2026-07`\n\n"
            "Lihat histori bulan yang tersedia:\n"
            "`/budget_history`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    total_budget = sum(float(item.get("budget", 0) or 0) for item in summary)
    total_actual = sum(float(item.get("actual", 0) or 0) for item in summary)
    total_gross_actual = sum(float(item.get("actual_gross", item.get("actual", 0)) or 0) for item in summary)
    # Prepare total remaining for the next step.
    total_remaining = total_budget - total_actual
    # Prepare total pct for the next step.
    total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0

    lines = [f"📊 *Budget {format_month_label(month)}*\n"]

    lines.append(f"💰 Total Budget : *{format_rupiah(total_budget)}*")
    lines.append(f"💸 Realisasi Bersih (Gross): *{format_budget_net_gross(total_actual, total_gross_actual)}*")
    lines.append(f"📌 Sisa         : *{format_rupiah(total_remaining)}*")
    lines.append(f"📈 Terpakai     : *{total_pct:.1f}%*\n")

    # Process each item in the current collection.
    for item in summary:
        bar = build_progress_bar(item["pct_used"])
        remaining_label = "Sisa" if item["remaining"] >= 0 else "Over"

        # Open a multi-line structure for the values below.
        lines.append(
            f"{item['emoji']} *{item['category']}*\n"
            f"  {bar} {item['pct_used']}%\n"
            f"  Pakai Bersih (Gross): {format_budget_net_gross(item.get('actual', 0), item.get('actual_gross', item.get('actual', 0)))} / {format_rupiah(item['budget'])}\n"
            f"  {remaining_label}: {format_rupiah(abs(item['remaining']))}\n"
        # Close the structure that was opened above.
        )

    # Open a multi-line structure for the values below.
    lines.append(
        "Cek bulan lain:\n"
        f"`/budget {month}`"
    # Close the structure that was opened above.
    )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# Handle the asynchronous budget history handler workflow.
async def budget_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous budget history handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare months for the next step.
    months = get_budget_months()

    # Handle the missing or empty months case.
    if not months:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "📭 Belum ada histori budget.\n\n"
            "Set budget dulu, contoh:\n"
            "`budget makan 1.5 juta`\n"
            "`budget makan 2 juta 2026-07`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    lines = ["🗂️ *Histori Budget Tersedia*\n"]

    # Process each month in the current collection.
    for month in sorted(months, reverse=True):
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare label for the next step.
            label = format_month_label(month)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Prepare label for the next step.
            label = month

        lines.append(f"• `{month}` — {label}")

    # Open a multi-line structure for the values below.
    lines.append(
        "\nLihat detail dengan:\n"
        "`/budget 2026-06`"
    # Close the structure that was opened above.
    )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# Define build pending expense lines for callers in this flow.
def build_pending_expense_lines(items: list[dict], title: str, total: float | None = None) -> list[str]:
    """Build the data structure or message text for pending expense lines."""
    lines = [f"🕒 *{md_safe(title)}*\n"]

    # Handle the missing or empty items case.
    if not items:
        # Open a multi-line structure for the values below.
        lines.append(
            "📭 Belum ada pending expense aktif.\n\n"
            "Tambah dengan:\n"
            "`/pending_add bayar wifi 285k tgl 30 dari BRI`\n"
            "`pending beli token 500k`\n"
            "`rencana beli sepatu 300k bulan depan`\n"
            "`nanti perlu bayar wisuda 750k`\n"
            "`perlu 750k buat bayar wisuda`"
        # Close the structure that was opened above.
        )
        # Return lines to the caller.
        return lines

    # Handle the case where total is None.
    if total is None:
        total = sum(float(item.get("amount", 0) or 0) for item in items)

    lines.append(f"💰 Total pending: *{format_rupiah(total)}*")
    lines.append(f"📝 Item: {len(items)}\n")

    # Process each i, item in the current collection.
    for i, item in enumerate(items, 1):
        due_date = str(item.get("due_date", "") or "").strip()
        due_precision = str(item.get("due_precision", "") or "unknown").strip().lower()
        month = str(item.get("month", "") or "-").strip()

        # Handle the case where due_date.
        if due_date:
            # Prepare due text for the next step.
            due_text = due_date
        elif due_precision == "month":
            due_text = f"{month} (tanggal belum pasti)"
        # Handle the fallback path after earlier conditions are skipped.
        else:
            due_text = "Belum pasti"

        account = str(item.get("account", "") or "-").strip() or "-"
        category = str(item.get("category", "") or "Other Expense").strip()
        status = str(item.get("status", "pending") or "pending").strip()
        subject = str(item.get("subject", "Pending Expense") or "Pending Expense").strip()
        amount = float(item.get("amount", 0) or 0)
        pending_id = str(item.get("id", "") or "").strip()

        # Open a multi-line structure for the values below.
        lines.append(
            f"{i}. 🕒 *{md_safe(subject)}*\n"
            f"   📅 {md_safe(due_text)} | 💰 *{format_rupiah(amount)}* | {md_safe(category)} | 🏦 {md_safe(account)}\n"
            f"   Status: `{md_safe(status)}`\n"
            f"   🔖 `{md_code_text(pending_id)}`"
        # Close the structure that was opened above.
        )

    # Open a multi-line structure for the values below.
    lines.append(
        "\nTandai sudah dibayar:\n"
        "`/pending_paid pending_id BRI`\n"
        "Batalkan:\n"
        "`/pending_cancel pending_id`"
    # Close the structure that was opened above.
    )
    # Return lines to the caller.
    return lines


# Handle the asynchronous pending handler workflow.
async def pending_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous pending handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    period = " ".join(context.args).strip() if context.args else None

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare result for the next step.
        result = get_pending_expenses(period=period, active_only=True)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ Gagal membaca pending expense: {md_safe(str(e))}",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    label = result.get("label") or "bulan ini"
    title = f"Pending Expense — {label}"
    lines = build_pending_expense_lines(result.get("items") or [], title, result.get("total", 0))
    await reply_long_markdown(update, "\n".join(lines))


# Handle the asynchronous pending add handler workflow.
async def pending_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous pending add handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare raw text for the next step.
    raw_text = update.message.text.strip()
    if raw_text.lower().startswith("/pending_add"):
        raw_text = re.sub(r"^/pending_add(?:@\w+)?\s*", "", raw_text, flags=re.IGNORECASE).strip()
    elif raw_text.lower().startswith("/rencana"):
        raw_text = re.sub(r"^/rencana(?:@\w+)?\s*", "", raw_text, flags=re.IGNORECASE).strip()

    # Handle the missing or empty raw_text case.
    if not raw_text:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Tulis pending expense-nya.\n\n"
            "Contoh:\n"
            "`/pending_add bayar wifi 285k tgl 30 dari BRI`\n"
            "`/pending_add beli token 500k`\n"
            "`rencana beli sepatu 300k bulan depan`\n"
            "`nanti perlu bayar wisuda 750k`\n"
            "`perlu 750k buat bayar wisuda`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare item for the next step.
        item = build_pending_expense_from_text(raw_text)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ Gagal membaca pending expense: {md_safe(str(e))}\n\n"
            "Contoh:\n"
            "`/pending_add bayar wifi 285k tgl 30 dari BRI`\n"
            "`pending beli token 500k`\n"
            "`nanti perlu bayar wisuda 750k`\n"
            "`perlu 750k buat bayar wisuda`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    context.user_data["pending_expense_confirm"] = item
    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        f"{build_pending_expense_confirm_preview(item, include_question=False)}\n\n{preview_action_question(True)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("pending_expense", True),
    # Close the structure that was opened above.
    )


# Handle the asynchronous pending paid handler workflow.
async def pending_paid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous pending paid handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Handle the missing or empty context.args case.
    if not context.args:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Masukkan pending ID.\n\n"
            "Contoh:\n"
            "`/pending_paid pend_20260626_123456_xxxxxxxx BRI`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare pending id for the next step.
    pending_id = context.args[0].strip()
    # Prepare account for the next step.
    account = context.args[1].strip() if len(context.args) >= 2 else None

    # Prepare result for the next step.
    result = mark_pending_paid(pending_id, account=account)
    if not result.get("success"):
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ {md_safe(result.get('message', 'Gagal menandai pending sebagai paid.'))}",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    item = result.get("item") or {}
    pending_id_display = result.get("pending_id") or item.get("id") or pending_id
    account_display = result.get("account") or account or item.get("account") or "-"
    amount = float(result.get("amount") or item.get("amount") or 0)
    new_balance = result.get("new_balance")
    new_balances = result.get("new_balances") or {}

    # Handle the case where new_balance is None and account_display.
    if new_balance is None and account_display:
        # Process each saved_account, saved_balance in the current collection.
        for saved_account, saved_balance in new_balances.items():
            # Handle the case where str(saved_account).strip().lower() == str(account_display).st....
            if str(saved_account).strip().lower() == str(account_display).strip().lower():
                # Prepare new balance for the next step.
                new_balance = saved_balance
                # Prepare account display for the next step.
                account_display = saved_account
                # Leave the loop after the target condition has been reached.
                break

    # Open a multi-line structure for the values below.
    lines = [
        "✅ *Pending expense sudah dicatat sebagai transaksi aktual.*",
        "",
        f"🔖 Pending ID: `{md_code_text(pending_id_display)}`",
        f"🔖 Transaction ID: `{md_code_text(result.get('transaction_id'))}`",
        f"💳 Rekening: *{md_safe(account_display)}*",
        f"💰 Nominal keluar: *-{format_rupiah(amount)}*",
    # Close the structure that was opened above.
    ]
    # Handle the case where new_balance is not None.
    if new_balance is not None:
        lines.append(f"🏦 Saldo {md_safe(account_display)} sekarang: *{format_rupiah(new_balance)}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# Handle the asynchronous pending cancel handler workflow.
async def pending_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous pending cancel handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Handle the missing or empty context.args case.
    if not context.args:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Masukkan pending ID.\n\n"
            "Contoh:\n"
            "`/pending_cancel pend_20260626_123456_xxxxxxxx`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare result for the next step.
    result = cancel_pending_expense(context.args[0])
    if not result.get("success"):
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ {md_safe(result.get('message', 'Gagal membatalkan pending expense.'))}",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    item = result.get("item") or {}
    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        "✅ Pending expense dibatalkan.\n"
        f"🔖 `{md_code_text(item.get('id'))}`",
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )


# Define parse amount text for callers in this flow.
def parse_amount_text(value: str) -> float:
    """Parse caller input for the parse amount text workflow in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = str(value or "").strip().lower().replace(" ", "").replace(",", ".")
    # Handle the missing or empty raw case.
    if not raw:
        # Return 0 to the caller.
        return 0

    unit = ""
    for suffix in ["ribu", "rb", "juta", "jt", "miliar", "miliard", "milyard", "k", "m"]:
        # Handle the case where raw.endswith(suffix).
        if raw.endswith(suffix):
            # Prepare unit for the next step.
            unit = suffix
            # Prepare raw for the next step.
            raw = raw[: -len(suffix)]
            # Leave the loop after the target condition has been reached.
            break

    # Run this operation in a guarded block so failures can be handled.
    try:
        if unit in {"rb", "ribu", "k"}:
            # 331.063k means 331,063 rupiah here, not 331,063,000.
            if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
                return float(raw.replace(".", ""))
            # Return float(raw) * 1_000 to the caller.
            return float(raw) * 1_000
        if unit in {"jt", "juta", "m"}:
            # Return float(raw) * 1_000_000 to the caller.
            return float(raw) * 1_000_000
        if unit in {"miliar", "miliard", "milyard"}:
            # Return float(raw) * 1_000_000_000 to the caller.
            return float(raw) * 1_000_000_000
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
            return float(raw.replace(".", ""))
        # Return float(raw) to the caller.
        return float(raw)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return 0 to the caller.
        return 0

# Define extract split bill total amount for callers in this flow.
def extract_split_bill_total_amount(raw_text: str) -> float | None:
    """Extract the required part of input for split bill total amount."""
    text = str(raw_text or "").strip()
    amount_token = r"(?P<amount>\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m)?)"
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"

    # Open a multi-line structure for the values below.
    patterns = [
        # 22k dibagi 2 sama raka
        rf"{amount_token}\s+{split_word}\s*(?:jadi\s*)?\d+",
        # 22k sama raka dibagi 2
        rf"{amount_token}\s+{friend_marker}\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{{0,80}}\s+{split_word}\s*(?:jadi\s*)?\d+",
    # Close the structure that was opened above.
    ]

    # Process each pattern in the current collection.
    for pattern in patterns:
        # Prepare match for the next step.
        match = re.search(pattern, text, flags=re.IGNORECASE)
        # Handle the case where match.
        if match:
            return parse_amount_text(match.group("amount"))

    # Return None to the caller.
    return None

# Handle the asynchronous set budget handler workflow.
async def set_budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous set budget handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare text for the next step.
    text = update.message.text.strip()
    text = re.sub(r"^/(?:set_budget)(?:@\w+)?\s*", "budget ", text, flags=re.IGNORECASE).strip()
    # Prepare text lower for the next step.
    text_lower = text.lower()

    # Import app.nlp.normalizer so this module can use its helpers.
    from app.nlp.normalizer import extract_amount_from_text

    # Prepare amount for the next step.
    amount = extract_amount_from_text(text_lower)
    # Handle the missing or empty amount case.
    if not amount:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Nominal budget tidak ditemukan.\n"
            "Contoh:\n"
            "`budget makan 1.5 juta`\n"
            "`budget jajan 500rb`\n"
            "`budget kebutuhan 2 juta 2026-07`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    month_match = re.search(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])\b", text_lower)

    # Handle the case where month_match.
    if month_match:
        raw_month = f"{month_match.group(1)}-{month_match.group(2)}"
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare month for the next step.
            month = normalize_month(raw_month)
        # Handle an expected failure from the guarded operation above.
        except ValueError as e:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"❌ {str(e)}\n"
                "Contoh bulan: `2026-07`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare month for the next step.
        month = normalize_month(None)

    # Take the label after the word budget, then remove amount and month tokens.
    label_text = re.sub(r"^\s*budget\s+", "", text_lower).strip()
    label_text = re.sub(r"\b20\d{2}[-/](0?[1-9]|1[0-2])\b", " ", label_text)
    label_text = re.sub(r"\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)?", " ", label_text)
    label_text = re.sub(r"\b(per\s+bulan|bulan|untuk|buat|sebesar|senilai)\b", " ", label_text)
    label_text = re.sub(r"\s+", " ", label_text).strip(" .,-")

    # Handle the missing or empty label_text case.
    if not label_text:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Nama budget belum kebaca.\n\n"
            "Contoh:\n"
            "`budget makan 1.5 juta`\n"
            "`budget jajan 500rb`\n"
            "`budget kebutuhan 2 juta`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    }

    # Prepare tokens for the next step.
    tokens = set(label_text.split())
    # Prepare matched category for the next step.
    matched_category = None

    # Exact phrase dulu, lalu token-level alias.
    if label_text in alias_to_category:
        # Prepare matched category for the next step.
        matched_category = alias_to_category[label_text]
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Process each token in the current collection.
        for token in tokens:
            # Handle the case where token in alias_to_category.
            if token in alias_to_category:
                # Prepare matched category for the next step.
                matched_category = alias_to_category[token]
                # Leave the loop after the target condition has been reached.
                break

    # Prepare budget label for the next step.
    budget_label = matched_category or label_text.title()

    source_note = "kategori resmi" if matched_category else "budget custom"
    context.user_data["pending_budget_confirm"] = {
        "category": budget_label,
        "amount": float(amount),
        "month": month,
        "source_note": source_note,
    # Close the structure that was opened above.
    }

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        "📊 *Preview Set Budget*\n\n"
        f"Kategori: *{md_safe(budget_label)}*\n"
        f"Bulan: *{format_month_label(month)}*\n"
        f"Nominal: *{format_rupiah(amount)} / bulan*\n"
        f"Tipe: {md_safe(source_note)}\n\n"
        "Mau simpan budget ini?",
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("budget"),
    # Close the structure that was opened above.
    )


# Define short debt id for callers in this flow.
def short_debt_id(debt_id: str) -> str:
    """Coordinate the short debt id logic in the Telegram handler layer.

    Args:
        debt_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    debt_id = str(debt_id or "")
    # Handle the case where len(debt_id) <= 18.
    if len(debt_id) <= 18:
        # Return debt_id to the caller.
        return debt_id
    return debt_id[:18] + "..."



# Define parse debt void args for callers in this flow.
def parse_debt_void_args(args: list[str]) -> dict:
    """Parse caller input for the parse debt void args workflow in the Telegram handler layer.

    Args:
        args: Command argument list or parsed argument values supplied by the caller.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    args = [str(a or "").strip() for a in (args or []) if str(a or "").strip()]
    # Handle the missing or empty args case.
    if not args:
        return {"mode": "empty"}

    # Handle the case where len(args) == 1.
    if len(args) == 1:
        # Prepare token for the next step.
        token = args[0]
        if token.isdigit() or token.lower().startswith("debt_"):
            return {"mode": "single", "debt_ref": token}
        return {"mode": "person", "person_name": token, "detail_ref": None}

    if args[-1].isdigit() or args[-1].lower().startswith("debt_"):
        # Return { to the caller.
        return {
            "mode": "person",
            "person_name": " ".join(args[:-1]).strip(),
            "detail_ref": args[-1],
        # Close the structure that was opened above.
        }

    return {"mode": "person", "person_name": " ".join(args).strip(), "detail_ref": None}


# Define build debt void preview text for callers in this flow.
def build_debt_void_preview_text(preview: dict) -> str:
    """Build the data structure or message text for debt void preview text."""
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
        # Handle the fallback path after earlier conditions are skipped.
        else:
            title = f"⚠️ *Preview Void SEMUA Debt Aktif {person}*\n"

        # Prepare lines for the next step.
        lines = [title]
        lines.append(f"👤 Nama: *{person}*")
        lines.append(f"📌 Jumlah rincian: *{len(targets)}*")
        lines.append(f"💰 Total yang akan di-void: *{format_rupiah(total_remaining)}*")

        lines.append("\n*Rincian yang akan di-void:*")
        # Process each i, debt in the current collection.
        for i, debt in enumerate(targets, 1):
            debt_type = str(debt.get("type") or "").strip()
            icon = "🔴" if debt_type == "payable" else "🟢"
            direction = "Anda hutang" if debt_type == "payable" else f"{preview.get('person_name') or 'Orang ini'} hutang"
            desc = md_safe(str(debt.get("description") or "-").strip()[:90])
            debt_id = md_safe(short_debt_id(debt.get("id", "-")))
            remaining = format_rupiah(debt.get("remaining_amount", 0))
            original = format_rupiah(debt.get("original_amount", 0))
            # Open a multi-line structure for the values below.
            lines.append(
                f"{i}. {icon} *{desc}*\n"
                f"   {direction}: *{remaining}* / awal {original}\n"
                f"   Debt ID: `{debt_id}`"
            # Close the structure that was opened above.
            )

        # Handle the case where cashflow_txns.
        if cashflow_txns:
            lines.append("\n*Cashflow terkait yang akan dihapus:*")
            # Process each txn in the current collection.
            for txn in cashflow_txns[:10]:
                txn_desc = md_safe(txn.get("description") or "-")
                txn_date = md_safe(txn.get("date") or "-")
                txn_amount = format_rupiah(float(txn.get("amount", 0) or 0))
                txn_account = md_safe(txn.get("account") or "-")
                lines.append(f"• {txn_date} — {txn_desc} — {txn_amount} | {txn_account}")
            # Handle the case where len(cashflow_txns) > 10.
            if len(cashflow_txns) > 10:
                lines.append(f"• ...dan {len(cashflow_txns) - 10} cashflow lain")
        # Handle the fallback path after earlier conditions are skipped.
        else:
            lines.append("\n*Cashflow terkait:* tidak ada / tidak perlu dihapus.")
            lines.append("Debt akan di-void tanpa mengubah saldo rekening.")

        # Handle the case where reverse_deltas.
        if reverse_deltas:
            lines.append("\n*Efek balik ke saldo rekening:*")
            # Process each account, delta in the current collection.
            for account, delta in reverse_deltas.items():
                sign = "+" if delta >= 0 else "-"
                lines.append(f"• {md_safe(account)}: {sign}{format_rupiah(abs(delta))}")

        # Open a multi-line structure for the values below.
        lines.append(
            "\nLanjut void target ini?\n"
            "Kalau klik Simpan, debt akan ditandai settled/void. Jika ada cashflow terkait, cashflow akan dihapus dan saldo direverse."
        # Close the structure that was opened above.
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

    # Handle the case where cashflow_txn.
    if cashflow_txn:
        txn_desc = md_safe(cashflow_txn.get("description") or "-")
        txn_date = md_safe(cashflow_txn.get("date") or "-")
        txn_category = md_safe(cashflow_txn.get("category") or "-")
        txn_account = md_safe(cashflow_txn.get("account") or "-")
        txn_amount = float(cashflow_txn.get("amount", 0) or 0)
        txn_row = md_safe(cashflow_txn.get("_row_index", "-"))

        lines.append("\n*Cashflow terkait yang akan dihapus:*")
        # Open a multi-line structure for the values below.
        lines.append(
            f"• Row {txn_row} — {txn_date} — *{txn_desc}*\n"
            f"  {format_rupiah(txn_amount)} | {txn_category} | {txn_account}"
        # Close the structure that was opened above.
        )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.append("\n*Cashflow terkait:* tidak ada.")
        lines.append("Debt/piutang ini akan divoid tanpa mengubah saldo rekening.")

    # Handle the case where reverse_deltas.
    if reverse_deltas:
        lines.append("\n*Efek balik ke saldo rekening:*")
        # Process each account, delta in the current collection.
        for account, delta in reverse_deltas.items():
            # Prepare safe account for the next step.
            safe_account = md_safe(account)
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {safe_account}: {sign}{format_rupiah(abs(delta))}")

    if preview.get("warning"):
        lines.append(f"\n⚠️ {md_safe(preview.get('warning'))}")

    # Open a multi-line structure for the values below.
    lines.append(
        "\nLanjut void debt ini?\n"
        "Debt akan ditandai settled/void. Jika ada cashflow terkait, cashflow akan dihapus dan saldo direverse."
    # Close the structure that was opened above.
    )

    return "\n".join(lines)


# Handle the asynchronous debt void handler workflow.
async def debt_void_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous debt void handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Handle the missing or empty context.args case.
    if not context.args:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Masukkan nomor debt, debt ID, atau nama orang.\n\n"
            "Contoh:\n"
            "`/hutang Maya`\n"
            "`/debt_void 1` — void nomor dari detail terakhir\n"
            "`/debt_void Maya` — void semua debt aktif Maya\n"
            "`/debt_void Maya 1` — void rincian nomor 1 milik Maya\n"
            "`/debt_void debt_20260610_123456_xxx`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare parsed for the next step.
    parsed = parse_debt_void_args(context.args or [])
    last_debt_map = context.user_data.get("last_debt_map", {})

    if parsed.get("mode") == "person":
        person_name = parsed.get("person_name") or ""
        detail_ref = parsed.get("detail_ref")
        # Prepare preview for the next step.
        preview = preview_void_debts_by_person(person_name, detail_ref)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        debt_ref = parsed.get("debt_ref")
        # Prepare preview for the next step.
        preview = preview_void_debt(debt_ref, last_debt_map)

    if not preview.get("success"):
        lines = [f"❌ *Debt void tidak bisa diproses.*\n{md_safe(preview.get('message'))}"]

        candidates = preview.get("candidate_txns") or []
        # Handle the case where candidates.
        if candidates:
            lines.append("\nCashflow kandidat yang ambigu:")
            # Process each txn in the current collection.
            for txn in candidates[:10]:
                # Open a multi-line structure for the values below.
                lines.append(
                    f"• Row {txn.get('_row_index', '-')} — {txn.get('date', '-')} — "
                    f"{md_safe(txn.get('description') or '-')} — {format_rupiah(float(txn.get('amount', 0) or 0))}"
                # Close the structure that was opened above.
                )

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    if preview.get("bulk"):
        context.user_data["pending_debt_void"] = {
            "mode": "bulk",
            "person_name": preview.get("person_name"),
            "detail_ref": preview.get("detail_ref"),
            "target_debt_ids": preview.get("target_debt_ids") or [],
        # Close the structure that was opened above.
        }
    # Handle the fallback path after earlier conditions are skipped.
    else:
        debt = preview.get("debt") or {}
        context.user_data["pending_debt_void"] = {
            "mode": "single",
            "debt_ref": str(debt.get("id") or parsed.get("debt_ref") or "").strip(),
        # Close the structure that was opened above.
        }

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_debt_void_preview_text(preview),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("debt_void"),
    # Close the structure that was opened above.
    )


# Define normalize debt edit type for callers in this flow.
def normalize_debt_edit_type(value: str) -> str | None:
    """Normalize input values for the normalize debt edit type workflow in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str | None` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    text = str(value or "").strip().lower()
    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    }
    # Return mapping.get(text) to the caller.
    return mapping.get(text)


# Define parse debt edit args for callers in this flow.
def parse_debt_edit_args(args: list[str]) -> tuple[str | None, dict, str | None]:
    """Parse caller input for the parse debt edit args workflow in the Telegram handler layer.

    Args:
        args: Command argument list or parsed argument values supplied by the caller.

    Returns:
        `tuple[str | None, dict, str | None]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Handle the case where len(args) < 3.
    if len(args) < 3:
        # Return None, {}, ( to the caller.
        return None, {}, (
            "Format edit debt belum lengkap.\n\n"
            "Contoh:\n"
            "`/debt_edit 5 nominal 100k`\n"
            "`/debt_edit 5 nama Dimas`\n"
            "`/debt_edit 5 tipe piutang`\n"
            "`/debt_edit 5 deskripsi Split bill wifi`\n"
            "`/debt_edit 5 jatuh_tempo 2026-06-30`"
        # Close the structure that was opened above.
        )

    # Prepare debt ref for the next step.
    debt_ref = args[0].strip()
    field = args[1].strip().lower().replace("-", "_")
    value = " ".join(args[2:]).strip()

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    }

    # Prepare normalized field for the next step.
    normalized_field = aliases.get(field)
    # Handle the missing or empty normalized_field case.
    if not normalized_field:
        # Return debt_ref, {}, ( to the caller.
        return debt_ref, {}, (
            "Field edit debt tidak dikenali.\n"
            "Field yang bisa diedit: `nominal`, `nama`, `tipe`, `deskripsi`, `jatuh_tempo`."
        # Close the structure that was opened above.
        )

    # Prepare updates for the next step.
    updates = {}
    if normalized_field == "amount":
        # Prepare amount for the next step.
        amount = parse_amount_text(value)
        # Handle the missing or empty amount or amount <= 0 case.
        if not amount or amount <= 0:
            return debt_ref, {}, "Nominal tidak valid. Contoh: `/debt_edit 5 nominal 100k`"
        updates["amount"] = amount
    elif normalized_field == "type":
        # Prepare debt type for the next step.
        debt_type = normalize_debt_edit_type(value)
        # Handle the missing or empty debt_type case.
        if not debt_type:
            return debt_ref, {}, "Tipe tidak valid. Gunakan `utang/payable` atau `piutang/receivable`."
        updates["type"] = debt_type
    elif normalized_field == "due_date":
        # Prepare detected for the next step.
        detected = detect_date(value)
        updates["due_date"] = detected or value
    elif normalized_field == "person_name":
        # Handle the missing or empty value case.
        if not value:
            return debt_ref, {}, "Nama orang tidak boleh kosong."
        updates["person_name"] = value
    elif normalized_field == "description":
        updates["description"] = value

    # Return debt_ref, updates, None to the caller.
    return debt_ref, updates, None


# Define build debt edit result text for callers in this flow.
def build_debt_edit_result_text(result: dict) -> str:
    """Build the data structure or message text for debt edit result text."""
    debt = result.get("debt") or {}
    changed = result.get("changed") or {}
    debt_type = str(debt.get("type") or "").strip()
    type_label = "Utang Anda" if debt_type == "payable" else "Piutang Anda"

    lines = ["✅ *Debt berhasil diedit!*\n"]
    lines.append(f"👤 Nama: *{md_safe(debt.get('person_name', '-'))}*")
    lines.append(f"📌 Tipe: *{md_safe(type_label)}*")
    lines.append(f"💰 Sisa: *{format_rupiah(float(debt.get('remaining_amount', 0) or 0))}*")
    due_date = str(debt.get("due_date") or "").strip()
    # Handle the case where due_date.
    if due_date:
        lines.append(f"📅 Jatuh tempo: `{md_safe(due_date)}`")

    # Handle the case where changed.
    if changed:
        lines.append("\nField yang berubah:")
        # Process each field, diff in the current collection.
        for field, diff in changed.items():
            old = diff.get("old")
            new = diff.get("new")
            if field == "amount":
                # Prepare old for the next step.
                old = format_rupiah(float(old or 0))
                # Prepare new for the next step.
                new = format_rupiah(float(new or 0))
            lines.append(f"• `{field}`: {md_safe(old)} → *{md_safe(new)}*")

    lines.append("\nCek ulang dengan `/hutang`.")
    return "\n".join(lines)


# Handle the asynchronous debt edit handler workflow.
async def debt_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous debt edit handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Run this statement as part of the current workflow.
    debt_ref, updates, error = parse_debt_edit_args(context.args or [])
    # Handle the case where error.
    if error:
        await update.message.reply_text(f"❌ {error}", parse_mode="Markdown")
        # Return control to the caller.
        return

    last_debt_map = context.user_data.get("last_debt_map", {})
    # Prepare result for the next step.
    result = update_debt(debt_ref, updates, last_debt_map)
    if not result.get("success"):
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ *Debt gagal diedit.*\n{md_safe(result.get('message'))}",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_debt_edit_result_text(result),
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )


# Define format debt created date for display for callers in this flow.
def format_debt_created_date_for_display(debt: dict) -> str:
    """Format debt created_at safely, including Google Sheets date serials."""
    raw = normalize_sheet_date_for_display((debt or {}).get("created_at", ""))
    return raw or "Tanpa tanggal"


# Define debt detail sort key for display for callers in this flow.
def debt_detail_sort_key_for_display(debt: dict) -> tuple[str, str, int]:
    """Coordinate the debt detail sort key for display logic in the Telegram handler layer.

    Args:
        debt: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `tuple[str, str, int]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Prepare created date for the next step.
    created_date = format_debt_created_date_for_display(debt)
    debt_id = str((debt or {}).get("id", "") or "").strip()
    # Run this operation in a guarded block so failures can be handled.
    try:
        row_index = int((debt or {}).get("_row_index", 0) or 0)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Prepare row index for the next step.
        row_index = 0
    # Return (created_date, debt_id, row_index) to the caller.
    return (created_date, debt_id, row_index)




# Debt flow section

# Define parse debt number selection for callers in this flow.
def parse_debt_number_selection(selection: str) -> list[str]:
    """Parse a debt detail number/range selection into ordered unique numbers.

    Args:
        selection: User input such as `1`, `1-3`, `1 3 5`, or `1,3,5`.

    Returns:
        A list of positive number strings in user order with duplicates removed.
        Invalid tokens are ignored. An empty input or fully invalid input returns
        an empty list.
    """
    raw = str(selection or "").strip()
    # Handle the missing or empty raw case.
    if not raw:
        # Return [] to the caller.
        return []
    # Run this statement as part of the current workflow.
    numbers: list[int] = []
    for token in re.split(r"[,\s]+", raw):
        # Prepare token for the next step.
        token = token.strip()
        # Handle the missing or empty token case.
        if not token:
            # Skip the rest of this loop iteration after handling this case.
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", token)
        # Handle the case where m.
        if m:
            # Run this statement as part of the current workflow.
            start, end = int(m.group(1)), int(m.group(2))
            # Handle the case where start <= 0 or end <= 0.
            if start <= 0 or end <= 0:
                # Skip the rest of this loop iteration after handling this case.
                continue
            # Prepare step for the next step.
            step = 1 if end >= start else -1
            # Update numbers with the current value.
            numbers.extend(range(start, end + step, step))
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the case where token.isdigit().
        if token.isdigit():
            # Prepare n for the next step.
            n = int(token)
            # Handle the case where n > 0.
            if n > 0:
                # Update numbers with the current value.
                numbers.append(n)
    # Prepare seen for the next step.
    seen = set()
    # Prepare ordered for the next step.
    ordered = []
    # Process each n in the current collection.
    for n in numbers:
        # Handle the case where n not in seen.
        if n not in seen:
            # Update seen with the current value.
            seen.add(n)
            # Update ordered with the current value.
            ordered.append(str(n))
    # Return ordered to the caller.
    return ordered


# Define parse debt settle command args for callers in this flow.
def parse_debt_settle_command_args(args: list[str]) -> dict:
    """Parse `/debt_settle` arguments into a settlement payload seed.

    Args:
        args: Telegram command arguments after `/debt_settle`. Supported shapes:
            `Nama`, `Nama 1-3`, `Nama 1 3 5`, and optional
            `amount=100000`/`nominal=100000` plus
            `account=DANA`/`rekening=DANA`/`dari DANA`/`ke DANA`.

    Returns:
        Dict with `person_name`, optional `selection`, parsed `numbers`,
        optional manual `amount`, optional `account`, `scope`, and `error`.
        `scope=person_all` means all active debts for that person should be
        settled by net amount. `scope=selected` means the number selection must
        resolve against the latest `/hutang Nama` detail output.

    Flow constraints:
        This parser only normalizes user input. It must not read or write
        Google Sheets and must not settle debt directly.
    """
    args = [str(a or "").strip() for a in (args or []) if str(a or "").strip()]
    # Open a multi-line structure for the values below.
    result = {
        "person_name": "",
        "selection": "",
        "numbers": [],
        "amount": None,
        "account": "",
        "scope": "",
        "error": "",
    # Close the structure that was opened above.
    }
    # Handle the case where len(args) < 1.
    if len(args) < 1:
        result["error"] = (
            "Format: `/debt_settle Nama` atau `/debt_settle Nama 1-3`\n"
            "Opsional: `amount=337063 account=DANA`"
        # Close the structure that was opened above.
        )
        # Return result to the caller.
        return result

    amount_raw = ""
    account = ""
    # Prepare positional for the next step.
    positional = []
    # Prepare i for the next step.
    i = 0
    # Repeat this block while i < len(args).
    while i < len(args):
        # Prepare token for the next step.
        token = args[i]
        # Prepare low for the next step.
        low = token.lower()
        if low.startswith("amount=") or low.startswith("nominal="):
            amount_raw = token.split("=", 1)[1]
        elif low in {"amount", "nominal"} and i + 1 < len(args):
            # Run this statement as part of the current workflow.
            i += 1
            # Prepare amount raw for the next step.
            amount_raw = args[i]
        elif low.startswith("account=") or low.startswith("rekening=") or low.startswith("akun="):
            account = token.split("=", 1)[1]
        elif low in {"account", "rekening", "akun", "dari", "ke"} and i + 1 < len(args):
            # Run this statement as part of the current workflow.
            i += 1
            # Prepare account for the next step.
            account = args[i]
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Update positional with the current value.
            positional.append(token)
        # Run this statement as part of the current workflow.
        i += 1

    # Number selection is optional; without it the command targets all active debt for the person.
    selection_idx = None
    # Process each idx, token in the current collection.
    for idx, token in enumerate(positional):
        if re.fullmatch(r"\d+(?:-\d+)?(?:[,\s]+\d+(?:-\d+)?)*", token):
            # Prepare selection idx for the next step.
            selection_idx = idx
            # Leave the loop after the target condition has been reached.
            break
    # Handle the case where selection_idx is None.
    if selection_idx is None:
        # Prepare person parts for the next step.
        person_parts = positional
        selection = ""
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare person parts for the next step.
        person_parts = positional[:selection_idx]
        selection = " ".join(positional[selection_idx:]).strip()

    # Handle the missing or empty person_parts case.
    if not person_parts:
        result["error"] = "Nama debt belum lengkap. Contoh: `/debt_settle Raka` atau `/debt_settle Raka 1-3`."
        # Return result to the caller.
        return result

    # Prepare amount for the next step.
    amount = None
    # Handle the case where amount_raw.
    if amount_raw:
        # Prepare amount for the next step.
        amount = parse_human_amount(amount_raw)
        # Handle the case where amount <= 0.
        if amount <= 0:
            result["error"] = "Nominal tidak valid. Contoh: `amount=337063`."
            # Return result to the caller.
            return result

    # Prepare numbers for the next step.
    numbers = []
    # Handle the case where selection.
    if selection:
        # Prepare numbers for the next step.
        numbers = parse_debt_number_selection(selection)
        # Handle the missing or empty numbers case.
        if not numbers:
            result["error"] = "Nomor/range debt tidak valid. Contoh: `1-17` atau `1 3 5`."
            # Return result to the caller.
            return result

    # Open a multi-line structure for the values below.
    result.update({
        "person_name": normalize_person_name(" ".join(person_parts)),
        "selection": selection,
        "numbers": numbers,
        "amount": amount,
        "account": account.strip(),
        "scope": "selected" if numbers else "person_all",
    # Close the structure that was opened above.
    })
    # Return result to the caller.
    return result


# Define parse natural debt settle text for callers in this flow.
def parse_natural_debt_settle_text(text: str) -> dict | None:
    """Parse natural-language selected debt settlement text.

    Args:
        text: User message such as `Raka bayar hutang 100000 untuk debt 1-3`
            with optional account suffix.

    Returns:
        Parsed dict containing `person_name`, `selection`, `numbers`, `amount`,
        optional `account`, raw text, and source marker; or `None` when the text
        is not a natural selected-settlement command.

    Flow constraints:
        This parser only supports explicit amount + numbered debt selections.
        It does not settle debt or write to Sheets.
    """
    raw = str(text or "").strip()
    # Handle the missing or empty raw case.
    if not raw:
        # Return None to the caller.
        return None
    # Open a multi-line structure for the values below.
    pattern = re.compile(
        r"^(?P<person>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s.'-]{0,60}?)\s+"
        r"bayar\s+(?:h?utang|utang)\s+"
        r"(?P<amount>\d[\d.,]*(?:\s*(?:k|rb|ribu|jt|juta))?)\s+"
        r"(?:untuk|buat)\s+(?:debt|hutang|piutang)\s+"
        r"(?P<selection>\d+(?:\s*-\s*\d+)?(?:[,\s]+\d+(?:\s*-\s*\d+)?)*)"
        r"(?:\s+(?:dari|ke|account=|rekening=|akun=)\s*(?P<account>[A-Za-z0-9 _-]+))?\s*$",
        # Include this value in the surrounding collection or call.
        re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Prepare m for the next step.
    m = pattern.match(raw)
    # Handle the missing or empty m case.
    if not m:
        # Return None to the caller.
        return None
    amount = parse_human_amount(m.group("amount"))
    numbers = parse_debt_number_selection(m.group("selection"))
    # Handle the case where amount <= 0 or not numbers.
    if amount <= 0 or not numbers:
        # Return None to the caller.
        return None
    # Return { to the caller.
    return {
        "person_name": normalize_person_name(m.group("person")),
        "selection": m.group("selection").strip(),
        "numbers": numbers,
        "amount": amount,
        "account": (m.group("account") or "").strip(),
        "raw": raw,
        "source": "natural",
    # Close the structure that was opened above.
    }


# Define resolve selected debts from last detail for callers in this flow.
def resolve_selected_debts_from_last_detail(context: ContextTypes.DEFAULT_TYPE, person_name: str, numbers: list[str]) -> dict:
    """Resolve numbered debt selections from the latest `/hutang Nama` detail.

    Args:
        context: Telegram context containing `last_debt_person` and
            `last_debt_map` from the most recent debt detail output.
        person_name: Counterparty name typed in `/debt_settle`.
        numbers: Parsed detail numbers such as `["1", "2", "3"]`.

    Returns:
        Success dict with normalized `person_name`, selected debt rows,
        `debt_ids`, and settlement `summary`, or failure dict with `message`.

    Flow constraints:
        Numbered settlement is anchored to the latest `/hutang Nama` output so
        a range like `1-3` cannot silently refer to another person's debt list.
    """
    # Prepare person for the next step.
    person = normalize_person_name(person_name)
    last_person = normalize_person_name(context.user_data.get("last_debt_person", ""))
    last_map = context.user_data.get("last_debt_map") or {}
    # Handle the missing or empty last_map or not last_person case.
    if not last_map or not last_person:
        # Return { to the caller.
        return {
            "success": False,
            "message": f"Jalankan `/hutang {md_safe(person)}` dulu, baru pakai nomor debt dari output itu.",
        # Close the structure that was opened above.
        }
    # Handle the case where last_person != person.
    if last_person != person:
        # Return { to the caller.
        return {
            "success": False,
            "message": (
                f"Nomor debt terakhir berasal dari `/hutang {md_safe(last_person)}`, "
                f"bukan `/hutang {md_safe(person)}`. Jalankan `/hutang {md_safe(person)}` dulu."
            # Close the structure that was opened above.
            ),
        # Close the structure that was opened above.
        }

    # Prepare selected for the next step.
    selected = []
    # Prepare debt ids for the next step.
    debt_ids = []
    # Prepare missing for the next step.
    missing = []
    # Process each n in the current collection.
    for n in numbers:
        # Prepare mapped for the next step.
        mapped = last_map.get(str(n))
        if not mapped or not mapped.get("debt_id"):
            # Update missing with the current value.
            missing.append(str(n))
            # Skip the rest of this loop iteration after handling this case.
            continue
        debt_id = str(mapped.get("debt_id") or "").strip()
        # Run this statement as part of the current workflow.
        row, debt = get_debt_by_id_any_status(debt_id)
        # Handle the missing or empty debt case.
        if not debt:
            # Update missing with the current value.
            missing.append(str(n))
            # Skip the rest of this loop iteration after handling this case.
            continue
        if normalize_person_name(debt.get("person_name", "")) != person:
            # Return { to the caller.
            return {
                "success": False,
                "message": f"Debt nomor {n} bukan milik {md_safe(person)}. Jalankan ulang `/hutang {md_safe(person)}`.",
            # Close the structure that was opened above.
            }
        # Handle the case where is_voided_debt(debt).
        if is_voided_debt(debt):
            return {"success": False, "message": f"Debt nomor {n} sudah void, tidak bisa disettle."}
        remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        # Handle the case where remaining <= 0.
        if remaining <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Prepare debt for the next step.
        debt = dict(debt)
        debt["_row_index"] = row
        debt["_display_no"] = str(n)
        # Update selected with the current value.
        selected.append(debt)
        # Update debt ids with the current value.
        debt_ids.append(debt_id)

    # Handle the case where missing.
    if missing:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Nomor debt tidak ditemukan di output /hutang terakhir: " + ", ".join(missing),
        # Close the structure that was opened above.
        }
    # Handle the missing or empty selected case.
    if not selected:
        return {"success": False, "message": "Debt terpilih sudah tidak aktif/lunas."}

    # Prepare summary for the next step.
    summary = summarize_debt_rows_for_settlement(selected)
    # Return { to the caller.
    return {
        "success": True,
        "person_name": person,
        "selected": selected,
        "debt_ids": debt_ids,
        "summary": summary,
    # Close the structure that was opened above.
    }


# Define resolve all active debts for person for callers in this flow.
def resolve_all_active_debts_for_person(person_name: str) -> dict:
    """Resolve all active debt rows for one counterparty.

    Args:
        person_name: Counterparty name from `/debt_settle Nama`. The lookup uses
            the existing debt service matching behavior for person debt detail.

    Returns:
        Success dict with normalized `person_name`, active selected debt rows,
        `debt_ids`, and settlement `summary`, or failure dict with `message`.

    Flow constraints:
        This helper only reads active debt rows. It does not mutate Sheets and
        does not create cashflow. The caller must still show a preview and wait
        for explicit confirmation before settlement.
    """
    # Prepare person for the next step.
    person = normalize_person_name(person_name)
    # Handle the missing or empty person case.
    if not person:
        return {"success": False, "message": "Nama debt belum lengkap."}

    # Prepare selected for the next step.
    selected = []
    # Prepare debt ids for the next step.
    debt_ids = []
    # Process each debt in the current collection.
    for debt in get_debt_by_person(person):
        # Handle the case where is_voided_debt(debt).
        if is_voided_debt(debt):
            # Skip the rest of this loop iteration after handling this case.
            continue
        remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        debt_id = str(debt.get("id") or "").strip()
        # Handle the case where remaining <= 0 or not debt_id.
        if remaining <= 0 or not debt_id:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Prepare item for the next step.
        item = dict(debt)
        item["remaining_amount"] = remaining
        # Update selected with the current value.
        selected.append(item)
        # Update debt ids with the current value.
        debt_ids.append(debt_id)

    # Handle the missing or empty selected case.
    if not selected:
        return {"success": False, "message": f"Tidak ada debt aktif dengan {md_safe(person)}."}

    # Prepare summary for the next step.
    summary = summarize_debt_rows_for_settlement(selected)
    # Return { to the caller.
    return {
        "success": True,
        "person_name": person,
        "selected": selected,
        "debt_ids": debt_ids,
        "summary": summary,
    # Close the structure that was opened above.
    }


# Define build selected debt total text for callers in this flow.
def build_selected_debt_total_text(payload: dict) -> str:
    """Build an informational total message for selected debt rows.

    Args:
        payload: Prepared debt settlement payload containing `person_name`,
            `selection`, `numbers`, and settlement `summary`.

    Returns:
        Markdown text that explains receivable, payable, and net amount.

    Flow constraints:
        This message is informational only and must not be used as confirmation
        text for a write operation.
    """
    person = payload.get("person_name") or "-"
    numbers = payload.get("numbers") or []
    selection = payload.get("selection") or ", ".join(numbers)
    summary = payload.get("summary") or {}
    # Open a multi-line structure for the values below.
    lines = [
        "🧮 *Total Debt Terpilih*\n",
        f"👤 Subjek: *{md_safe(person)}*",
        f"📌 Nomor dari `/hutang {md_safe(person)}`: *{md_safe(selection)}*",
        f"🟢 Piutang Anda: *{format_rupiah(summary.get('total_receivable', 0))}*",
        f"🔴 Utang Anda: *{format_rupiah(summary.get('total_payable', 0))}*",
    # Close the structure that was opened above.
    ]
    net = float(summary.get("net_amount", 0) or 0)
    # Handle the case where net > 0.
    if net > 0:
        lines.append(f"📊 Net: *{md_safe(person)} harus bayar Anda {format_rupiah(net)}*")
    # Handle the alternate case where net < 0.
    elif net < 0:
        lines.append(f"📊 Net: *Anda harus bayar {md_safe(person)} {format_rupiah(abs(net))}*")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.append("📊 Net: *impas / tidak perlu cashflow*")
    # Open a multi-line structure for the values below.
    lines.append(
        "\nUntuk settle dari range ini:\n"
        f"`/debt_settle {md_safe(person)} {md_safe(selection)} amount={summary.get('net_abs', 0)} account=DANA`"
    # Close the structure that was opened above.
    )
    return "\n".join(lines)


# Define build selected debt settle preview text for callers in this flow.
def build_selected_debt_settle_preview_text(payload: dict) -> str:
    """Build the final preview text before selected debt settlement is saved.

    Args:
        payload: Prepared settlement payload with person, selected debt IDs,
            summary totals, settlement amount, account, scope, and optional
            overpayment handling.

    Returns:
        Markdown preview that states the selected scope, net amount, cashflow
        direction, account when required, and save effects.

    Flow constraints:
        The returned text must be paired with confirmation/cancel buttons before
        any Google Sheets write happens.
    """
    person = payload.get("person_name") or "-"
    selection = payload.get("selection") or ", ".join(payload.get("numbers") or [])
    summary = payload.get("summary") or {}
    amount = float(payload.get("amount", 0) or 0)
    account = payload.get("account") or "-"
    overpayment = max(0.0, float(payload.get("overpayment", 0) or 0))
    shortage = max(0.0, float(payload.get("shortage", 0) or 0))
    net_type = payload.get("net_type") or summary.get("net_type")
    # Open a multi-line structure for the values below.
    lines = [
        "🧾 *Preview Settle Debt Terpilih*\n",
        f"👤 Subjek: *{md_safe(person)}*",
        f"📌 Rincian dipilih: *{md_safe(selection)}*",
        f"🟢 Piutang Anda: *{format_rupiah(summary.get('total_receivable', 0))}*",
        f"🔴 Utang Anda: *{format_rupiah(summary.get('total_payable', 0))}*",
    # Close the structure that was opened above.
    ]
    if payload.get("amount_auto"):
        lines.append(f"ℹ️ Nominal settlement otomatis: *{format_rupiah(amount)}*")
    if net_type == "receivable":
        lines.append(f"📊 Net yang harus dibayar {md_safe(person)}: *{format_rupiah(summary.get('net_abs', 0))}*")
        lines.append(f"💰 Pembayaran diterima: *{format_rupiah(amount)}*")
        lines.append(f"🏦 Masuk ke: *{md_safe(account)}*")
    elif net_type == "payable":
        lines.append(f"📊 Net yang harus Anda bayar ke {md_safe(person)}: *{format_rupiah(summary.get('net_abs', 0))}*")
        lines.append(f"💰 Pembayaran keluar: *{format_rupiah(amount)}*")
        lines.append(f"🏦 Keluar dari: *{md_safe(account)}*")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.append("📊 Net: *impas / tidak perlu cashflow*")
        lines.append("💰 Cashflow: *tidak ada transaksi saldo rekening*")

    # Handle the case where shortage > 0.
    if shortage > 0:
        # Open a multi-line structure for the values below.
        lines.append(
            f"\n❌ *Nominal kurang {format_rupiah(shortage)}.* "
            "Karena ini `/debt_settle`, debt terpilih hanya bisa ditutup kalau nominal minimal sama dengan net terpilih."
        # Close the structure that was opened above.
        )
        return "\n".join(lines)

    # Handle the case where overpayment > 0.
    if overpayment > 0:
        # Open a multi-line structure for the values below.
        lines.append(
            f"\n⚠️ *Pembayaran melebihi net debt terpilih sebesar {format_rupiah(overpayment)}.*"
        # Close the structure that was opened above.
        )
        policy = str(payload.get("overpayment_policy") or "").strip()
        if policy == "bonus":
            lines.append("ℹ️ Kelebihan akan dianggap lunas/bonus, tidak jadi hutang baru.")
        elif policy == "opposite_debt":
            if net_type == "receivable":
                lines.append(f"ℹ️ Kelebihan akan dicatat sebagai utang Anda ke {md_safe(person)}.")
            # Handle the fallback path after earlier conditions are skipped.
            else:
                lines.append(f"ℹ️ Kelebihan akan dicatat sebagai piutang Anda ke {md_safe(person)}.")
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Open a multi-line structure for the values below.
            lines.append(
                "Pilih perlakuan untuk uang lebihnya:\n"
                "1. *Anggap lunas/bonus*\n"
                "2. *Catat sebagai hutang lawan arah*"
            # Close the structure that was opened above.
            )
            return "\n".join(lines)

    lines.append("\nEfek jika disimpan:")
    if payload.get("scope") == "person_all":
        lines.append("✅ Semua debt aktif untuk subjek ini disettle")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.append("✅ Hanya debt nomor terpilih yang disettle")
        lines.append("✅ Debt lain di luar range/list tidak disentuh")
    if float(payload.get("amount", 0) or 0) > 0:
        lines.append("✅ Cashflow tersimpan di transactions")
        lines.append("✅ Relasi debt disimpan supaya `/delete_txn` bisa membuka lagi debt terpilih")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.append("✅ Tidak ada transaksi saldo rekening karena net impas")
    lines.append("\nSimpan settlement ini?")
    return "\n".join(lines)


# Define build selected settle catatan for callers in this flow.
def build_selected_settle_catatan(payload: dict, result: dict) -> str:
    """Build transaction note metadata for selected debt settlement.

    Args:
        payload: Pending settlement preview state.
        result: Settlement result from `settle_selected_debt_ids`.

    Returns:
        Compact `catatan` string containing raw input, selected-settle marker,
        debt allocations, and optional overpayment metadata.

    Flow constraints:
        The note must remain parseable by debt reversal logic when a settlement
        transaction is deleted.
    """
    raw = str(payload.get("raw") or "").strip()
    parts = [raw, "selected_settle=1"]
    # Prepare allocs for the next step.
    allocs = []
    for item in result.get("settled") or result.get("allocations") or []:
        debt_id = str(item.get("debt_id") or "").strip()
        amount = item.get("amount")
        # Handle the case where debt_id and amount is not None.
        if debt_id and amount is not None:
            allocs.append(f"{debt_id}:{float(amount)}")
    # Handle the case where allocs.
    if allocs:
        parts.append("debt_allocations=" + ";".join(allocs))
    overpayment = float(result.get("overpayment", 0) or 0)
    # Handle the case where overpayment > 0.
    if overpayment > 0:
        parts.append(f"overpayment={overpayment}")
        policy = result.get("overpayment_policy") or payload.get("overpayment_policy") or ""
        # Handle the case where policy.
        if policy:
            parts.append(f"overpayment_policy={policy}")
        created = result.get("overpayment_created") or {}
        if created.get("debt_id"):
            parts.append(f"overpayment_debt_id={created.get('debt_id')}")
    return " | ".join([p for p in parts if p]).strip(" |")


# Define prepare selected debt settle payload for callers in this flow.
def prepare_selected_debt_settle_payload(context: ContextTypes.DEFAULT_TYPE, parsed: dict) -> dict:
    """Prepare a debt settlement preview payload from parsed command input.

    Args:
        context: Telegram context used only when numbered settlement must
            resolve against the latest `/hutang Nama` detail map.
        parsed: Dict from `parse_debt_settle_command_args` or
            `parse_natural_debt_settle_text`. It may contain manual `amount`,
            `account`, `numbers`, `scope`, and `source`.

    Returns:
        Success payload with selected debt IDs, summary totals, final amount,
        account, scope, and shortage/overpayment fields; or failure dict with a
        user-facing `message`.

    Flow constraints:
        This function only prepares state for preview. It never writes to Google
        Sheets. If `amount` is omitted, it automatically uses the net selected
        debt amount so `/debt_settle Nama` and `/debt_settle Nama 1-3` can move
        directly to preview/confirmation.
    """
    scope = parsed.get("scope") or ("selected" if parsed.get("numbers") else "person_all")
    if scope == "selected":
        # Open a multi-line structure for the values below.
        resolved = resolve_selected_debts_from_last_detail(
            # Include this value in the surrounding collection or call.
            context,
            parsed.get("person_name", ""),
            parsed.get("numbers") or [],
        # Close the structure that was opened above.
        )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        resolved = resolve_all_active_debts_for_person(parsed.get("person_name", ""))
    if not resolved.get("success"):
        return {"success": False, "message": resolved.get("message", "Gagal resolve debt terpilih.")}
    summary = resolved.get("summary") or {}
    manual_amount = parsed.get("amount")
    # Prepare amount for the next step.
    amount = manual_amount
    # Prepare amount auto for the next step.
    amount_auto = amount is None
    # Handle the case where amount_auto.
    if amount_auto:
        amount = float(summary.get("net_abs", 0) or 0)
    selection = parsed.get("selection") or ("semua debt aktif" if scope == "person_all" else ", ".join(parsed.get("numbers") or []))
    # Open a multi-line structure for the values below.
    payload = {
        "success": True,
        "person_name": resolved.get("person_name"),
        "selection": selection,
        "numbers": parsed.get("numbers") or [],
        "debt_ids": resolved.get("debt_ids") or [],
        "summary": summary,
        "amount": amount,
        "amount_auto": amount_auto,
        "account": parsed.get("account") or "",
        "raw": parsed.get("raw") or "",
        "source": parsed.get("source") or "command",
        "scope": scope,
        "net_type": summary.get("net_type"),
    # Close the structure that was opened above.
    }
    required = float(summary.get("net_abs", 0) or 0)
    payload["overpayment"] = max(0.0, float(amount or 0) - required)
    payload["shortage"] = max(0.0, required - float(amount or 0))
    # Return payload to the caller.
    return payload


# Define selected debt settle overpay keyboard for callers in this flow.
def selected_debt_settle_overpay_keyboard() -> InlineKeyboardMarkup:
    """Build the overpayment decision keyboard for selected debt settlement.

    Returns:
        Inline keyboard with bonus, opposite-debt, and Batal choices.

    Flow constraints:
        Used only when manual amount exceeds selected net debt. It does not
        write data; the choice updates pending settlement state.
    """
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Anggap lunas / bonus", callback_data="debt_settle_overpay:bonus")],
        [InlineKeyboardButton("🔴 Catat sebagai hutang lawan arah", callback_data="debt_settle_overpay:opposite_debt")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:debt_settle")],
    # Close the structure that was opened above.
    ])


# Handle the asynchronous debt settle handler workflow.
async def debt_settle_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle `/debt_settle` command input and start preview confirmation.

    Args:
        update: Telegram update containing the command message.
        context: Telegram context with command args and temporary user state.

    Side effects:
        May store `pending_debt_settle` in `context.user_data` and send a
        preview, account-selection keyboard, overpayment decision keyboard, or
        validation error. It does not write debt or transaction rows directly.

    Flow constraints:
        `/debt_settle Nama` targets all active debt for the person.
        `/debt_settle Nama 1-3` targets numbered details from the latest
        `/hutang Nama` output. Both forms auto-fill amount from net debt when
        the user does not provide `amount=...`.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare parsed for the next step.
    parsed = parse_debt_settle_command_args(context.args or [])
    if parsed.get("error"):
        await update.message.reply_text(f"❌ {parsed['error']}", parse_mode="Markdown")
        # Return control to the caller.
        return

    # Prepare payload for the next step.
    payload = prepare_selected_debt_settle_payload(context, parsed)
    if not payload.get("success"):
        await update.message.reply_text(f"❌ {payload.get('message')}", parse_mode="Markdown")
        # Return control to the caller.
        return

    if float(payload.get("shortage", 0) or 0) > 0:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_selected_debt_settle_preview_text(payload),
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=cancel_keyboard(),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    if float(payload.get("amount", 0) or 0) > 0 and not payload.get("account"):
        context.user_data["pending_debt_settle"] = payload
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            build_selected_debt_settle_preview_text(payload) + "\n\nPilih rekening cashflow:",
            parse_mode="Markdown",
            reply_markup=account_keyboard("debt_settle_acc", include_skip=False),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    context.user_data["pending_debt_settle"] = payload
    if float(payload.get("overpayment", 0) or 0) > 0 and not payload.get("overpayment_policy"):
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_selected_debt_settle_preview_text(payload),
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=selected_debt_settle_overpay_keyboard(),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_selected_debt_settle_preview_text(payload),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("debt_settle"),
    # Close the structure that was opened above.
    )


# Handle the asynchronous handle natural debt settle workflow.
async def handle_natural_debt_settle(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    """Handle natural-language selected debt settlement text.

    Args:
        update: Telegram update containing the user message.
        context: Telegram context with the latest debt detail map and pending
            settlement state.
        text: User text such as `Raka bayar hutang 100000 untuk debt 1-3`.

    Returns:
        `True` when the text matched and the debt settlement flow handled it,
        otherwise `False` so other routers can continue.

    Flow constraints:
        Natural settlement remains an explicit-amount selected-detail flow. It
        still requires preview confirmation before any Sheets write.
    """
    # Prepare parsed for the next step.
    parsed = parse_natural_debt_settle_text(text)
    # Handle the missing or empty parsed case.
    if not parsed:
        # Return False to the caller.
        return False

    # Prepare payload for the next step.
    payload = prepare_selected_debt_settle_payload(context, parsed)
    if not payload.get("success"):
        await update.message.reply_text(f"❌ {payload.get('message')}", parse_mode="Markdown")
        # Return True to the caller.
        return True

    if float(payload.get("shortage", 0) or 0) > 0:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_selected_debt_settle_preview_text(payload),
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=cancel_keyboard(),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    if float(payload.get("amount", 0) or 0) > 0 and not payload.get("account"):
        context.user_data["pending_debt_settle"] = payload
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            build_selected_debt_settle_preview_text(payload) + "\n\nPilih rekening cashflow:",
            parse_mode="Markdown",
            reply_markup=account_keyboard("debt_settle_acc", include_skip=False),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    context.user_data["pending_debt_settle"] = payload
    if float(payload.get("overpayment", 0) or 0) > 0 and not payload.get("overpayment_policy"):
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            # Include this value in the surrounding collection or call.
            build_selected_debt_settle_preview_text(payload),
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=selected_debt_settle_overpay_keyboard(),
        # Close the structure that was opened above.
        )
        # Return True to the caller.
        return True

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_selected_debt_settle_preview_text(payload),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("debt_settle"),
    # Close the structure that was opened above.
    )
    # Return True to the caller.
    return True


# Define build selected debt settle transaction for callers in this flow.
def build_selected_debt_settle_transaction(payload: dict, result: dict) -> dict:
    """Build the cashflow transaction for a confirmed debt settlement.

    Args:
        payload: Confirmed pending settlement state containing person, amount,
            account, net type, selection, and summary.
        result: Settlement result containing affected debt IDs and allocation
            metadata.

    Returns:
        Parsed transaction dict for `save_transaction`, using `expense` and
        `Bayar Utang` when the user pays, or `income` and `Pembayaran Piutang`
        when the user receives payment.

    Flow constraints:
        This only builds the transaction payload. The caller must save it after
        debt settlement succeeds and must skip it for net-impas amount `0`.
    """
    person = payload.get("person_name") or ""
    amount = float(payload.get("amount", 0) or 0)
    account = payload.get("account") or ""
    net_type = payload.get("net_type") or (payload.get("summary") or {}).get("net_type")
    affected_ids = result.get("affected_debt_ids") or payload.get("debt_ids") or []
    description = f"Settlement debt terpilih {person} nomor {payload.get('selection') or '-'}"
    if net_type == "payable":
        txn_type = "expense"
        category = "Bayar Utang"
        tipe_hutang = "utang"
        desc = f"Bayar utang terpilih ke {person}"
    # Handle the fallback path after earlier conditions are skipped.
    else:
        txn_type = "income"
        category = "Pembayaran Piutang"
        tipe_hutang = "piutang"
        desc = f"Pembayaran piutang terpilih dari {person}"
    # Return { to the caller.
    return {
        "type": txn_type,
        "amount": amount,
        "category": category,
        "account": account,
        "to_account": None,
        "subject": person,
        "description": desc,
        "catatan": build_selected_settle_catatan(payload, result),
        "tipe_pengeluaran": "",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "hutang_id": ", ".join([x for x in affected_ids if x]),
        "tipe_hutang": tipe_hutang,
        "parsed_by": "debt_settle",
    # Close the structure that was opened above.
    }


# Debt flow section

# Define collect known debt person names for callers in this flow.
def _collect_known_debt_person_names() -> list[str]:
    """Coordinate the collect known debt person names logic in the Telegram handler layer.

    Args:
        None.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Prepare names for the next step.
    names = []
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare summary for the next step.
        summary = get_debt_person_summary() or {}
        for key in ("payables", "receivables", "balanced"):
            # Process each item in the current collection.
            for item in summary.get(key) or []:
                name = str(item.get("person_name") or "").strip()
                # Handle the case where name and name not in names.
                if name and name not in names:
                    # Update names with the current value.
                    names.append(name)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass
    # Return names to the caller.
    return names


# Define strip trailing known names for summary for callers in this flow.
def _strip_trailing_known_names_for_summary(text: str, known_names: list[str]) -> str:
    """Coordinate the strip trailing known names for summary logic in the Telegram handler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        known_names: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    clean = str(text or "").strip(" .,-")
    # Handle the missing or empty clean or not known_names case.
    if not clean or not known_names:
        # Return clean to the caller.
        return clean

    # Open a multi-line structure for the values below.
    ordered = sorted(
        [str(name or "").strip() for name in known_names if str(name or "").strip()],
        # Prepare key for the next step.
        key=len,
        # Prepare reverse for the next step.
        reverse=True,
    # Close the structure that was opened above.
    )

    # Prepare changed for the next step.
    changed = True
    # Repeat this block while changed and clean.
    while changed and clean:
        # Prepare changed for the next step.
        changed = False
        new_clean = re.sub(r"\b(?:sama|ama|dengan|bareng|dan)\s*$", "", clean, flags=re.IGNORECASE).strip(" .,-")
        # Handle the case where new_clean != clean.
        if new_clean != clean:
            # Prepare clean for the next step.
            clean = new_clean
            # Prepare changed for the next step.
            changed = True

        # Process each name in the current collection.
        for name in ordered:
            pattern = rf"(?:^|[\s,;&]+){re.escape(name)}\s*$"
            new_clean = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip(" .,-")
            # Handle the case where new_clean != clean.
            if new_clean != clean:
                # Prepare clean for the next step.
                clean = new_clean
                # Prepare changed for the next step.
                changed = True
                # Leave the loop after the target condition has been reached.
                break

    # Return clean to the caller.
    return clean


# Define clean debt description for share for callers in this flow.
def _clean_debt_description_for_share(desc: str, person: str, known_names: list[str] | None = None) -> str:
    """Coordinate the clean debt description for share logic in the Telegram handler layer.

    Args:
        desc: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        person: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        known_names: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    raw = str(desc or "").strip()
    # Handle the missing or empty raw case.
    if not raw:
        return "-"

    person_text = str(person or "").strip()
    # Prepare known names for the next step.
    known_names = known_names or []

    # Implementation note for this project-specific finance flow.
    # Implementation note for this project-specific finance flow.
    if person_text:
        m = re.match(rf"^\s*Ditalangin\s+(.+?)\s*:\s*(?:ke|kepada)\s+{re.escape(person_text)}\s*$", raw, flags=re.IGNORECASE)
        # Handle the case where m.
        if m:
            # Prepare raw for the next step.
            raw = m.group(1).strip()
        # Handle the fallback path after earlier conditions are skipped.
        else:
            m = re.match(rf"^\s*Ditalangin\s+{re.escape(person_text)}\s*:\s*(.+?)\s*$", raw, flags=re.IGNORECASE)
            # Handle the case where m.
            if m:
                # Prepare raw for the next step.
                raw = m.group(1).strip()

    # Debt flow section
    raw = re.sub(r"^\s*Split\s*bill(?:\s+ditalangin\s+[^:]+)?\s*:\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^\s*Ditalangin\s+[^:]+\s*:\s*", "", raw, flags=re.IGNORECASE)

    # Implementation note for this project-specific finance flow.
    raw = re.sub(r"\b(?:di\s*-?\s*bagi|dibagi|bagi|split|share|patungan)\b.*$", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\b(?:ke|kepada)\s+" + re.escape(person_text) + r"\s*$", "", raw, flags=re.IGNORECASE) if person_text else raw
    # Prepare raw for the next step.
    raw = _strip_trailing_known_names_for_summary(raw, known_names + ([person_text] if person_text else []))

    raw = re.sub(r"\s+", " ", raw).strip(" .,-:")
    return raw or str(desc or "-").strip() or "-"


# Define format shareable date heading for callers in this flow.
def _format_shareable_date_heading(date_value) -> str:
    """Format data into a readable display for shareable date heading."""
    # Prepare label for the next step.
    label = format_indonesian_date_group_label(date_value)
    return label.rstrip(":")


# Define group debts for shareable summary for callers in this flow.
def _group_debts_for_shareable_summary(debts: list[dict], person: str, known_names: list[str]) -> list[str]:
    """Coordinate the group debts for shareable summary logic in the Telegram handler layer.

    Args:
        debts: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        person: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        known_names: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Handle the missing or empty debts case.
    if not debts:
        return ["Tidak ada rincian aktif."]

    # Prepare lines for the next step.
    lines = []
    # Prepare current date for the next step.
    current_date = None
    # Prepare item no for the next step.
    item_no = 1
    # Process each debt in the current collection.
    for debt in sorted(debts or [], key=debt_detail_sort_key_for_display, reverse=True):
        # Prepare created date for the next step.
        created_date = format_debt_created_date_for_display(debt)
        # Handle the case where created_date != current_date.
        if created_date != current_date:
            # Handle the case where lines.
            if lines:
                lines.append("")
            lines.append(f"*{md_safe(_format_shareable_date_heading(created_date))}*")
            # Prepare current date for the next step.
            current_date = created_date

        desc = _clean_debt_description_for_share(debt.get("description"), person, known_names)
        amount = parse_sheet_number(debt.get("remaining_amount", 0))
        lines.append(f"{item_no}. {md_safe(desc)} - *{format_rupiah(amount)}*")
        # Run this statement as part of the current workflow.
        item_no += 1

    # Return lines to the caller.
    return lines


# Define build shareable debt summary text for callers in this flow.
def build_shareable_debt_summary_text(person_query: str) -> str:
    """Build the data structure or message text for shareable debt summary text."""
    # Prepare detail for the next step.
    detail = get_debt_person_detail(person_query, include_settled=True)
    person = detail.get("person_name") or str(person_query or "").strip().title()
    active_details = detail.get("active_details") or []

    # Handle the missing or empty active_details case.
    if not active_details:
        return f"✅ Tidak ada hutang-piutang aktif dengan *{md_safe(person)}*."

    # Open a multi-line structure for the values below.
    receivable_details = [
        # Run this statement as part of the current workflow.
        d for d in active_details
        if str(d.get("type") or "").strip().lower() == "receivable"
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
    # Close the structure that was opened above.
    ]
    # Open a multi-line structure for the values below.
    payable_details = [
        # Run this statement as part of the current workflow.
        d for d in active_details
        if str(d.get("type") or "").strip().lower() == "payable"
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
    # Close the structure that was opened above.
    ]

    total_receivable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in receivable_details)
    total_payable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in payable_details)
    # Prepare net for the next step.
    net = total_receivable - total_payable

    # Prepare known names for the next step.
    known_names = _collect_known_debt_person_names()

    # Open a multi-line structure for the values below.
    lines = [
        f"📌 *Rekap Hutang-Piutang Denan & {md_safe(person)}*",
        "",
        f"🟢 {md_safe(person)} ke Denan: *{format_rupiah(total_receivable)}*",
        f"🔴 Denan ke {md_safe(person)}: *{format_rupiah(total_payable)}*",
        "",
        "💰 *Total akhir:*",
    # Close the structure that was opened above.
    ]

    # Handle the case where net > 0.
    if net > 0:
        lines.append(f"{md_safe(person)} bayar ke Denan *{format_rupiah(net)}*")
    # Handle the alternate case where net < 0.
    elif net < 0:
        lines.append(f"Denan bayar ke {md_safe(person)} *{format_rupiah(abs(net))}*")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.append("Sudah impas / netral")

    # Open a multi-line structure for the values below.
    lines.extend([
        "",
        "",
        f"*Rincian {md_safe(person)} ke Denan:*",
        "",
    # Close the structure that was opened above.
    ])
    # Update lines with the current value.
    lines.extend(_group_debts_for_shareable_summary(receivable_details, person, known_names))
    # Open a multi-line structure for the values below.
    lines.extend([
        "",
        f"📊 *Subtotal {md_safe(person)} ke Denan: {format_rupiah(total_receivable)}*",
        "",
        "",
        f"*Rincian Denan ke {md_safe(person)}:*",
        "",
    # Close the structure that was opened above.
    ])
    # Update lines with the current value.
    lines.extend(_group_debts_for_shareable_summary(payable_details, person, known_names))
    # Open a multi-line structure for the values below.
    lines.extend([
        "",
        f"📊 *Subtotal Denan ke {md_safe(person)}: {format_rupiah(total_payable)}*",
        "",
        "",
        "🎯 *Jadi total akhirnya:*",
    # Close the structure that was opened above.
    ])

    # Handle the case where net > 0.
    if net > 0:
        lines.append(f"✅ {md_safe(person)} bayar ke Denan *{format_rupiah(net)}*")
    # Handle the alternate case where net < 0.
    elif net < 0:
        lines.append(f"✅ Denan bayar ke {md_safe(person)} *{format_rupiah(abs(net))}*")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.append("✅ Sudah impas / netral")

    return "\n".join(lines)


# Handle the asynchronous ringkasan hutang handler workflow.
async def ringkasan_hutang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous ringkasan hutang handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    person_query = " ".join(getattr(context, "args", []) or []).strip()
    # Handle the missing or empty person_query case.
    if not person_query:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "Format: `/ringkasan_hutang Nama`\nContoh: `/ringkasan_hutang Raka`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_shareable_debt_summary_text(person_query),
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )

# Handle the asynchronous hutang handler workflow.
async def hutang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous hutang handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    args = getattr(context, "args", []) or []
    person_query = " ".join(args).strip()

    # Debt flow section
    if person_query:
        # Debt flow section
        # Implementation note for this project-specific finance flow.
        # Debt flow section
        netting_result = {"success": False, "offset_amount": 0}
        # Prepare detail for the next step.
        detail = get_debt_person_detail(person_query, include_settled=True)
        # Open a multi-line structure for the values below.
        active_details = sorted(
            detail.get("active_details") or [],
            # Prepare key for the next step.
            key=debt_detail_sort_key_for_display,
            # Prepare reverse for the next step.
            reverse=True,
        # Close the structure that was opened above.
        )
        all_details = detail.get("details") or []

        # Handle the missing or empty all_details case.
        if not all_details:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"✅ Tidak ada riwayat utang/piutang untuk *{md_safe(person_query.title())}*.",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        person = detail.get("person_name") or person_query.title()
        net_remaining = float(detail.get("net_remaining") or 0)
        net_type = detail.get("net_type")

        if net_type == "receivable":
            header = f"🟢 *{md_safe(person)} hutang ke Anda: {format_rupiah(abs(net_remaining))}*"
        elif net_type == "payable":
            header = f"🔴 *Anda hutang ke {md_safe(person)}: {format_rupiah(abs(net_remaining))}*"
        # Handle the fallback path after earlier conditions are skipped.
        else:
            header = f"⚪ *Debt dengan {md_safe(person)} sudah netral/lunas.*"

        lines = [header, ""]
        if netting_result.get("success") and float(netting_result.get("offset_amount", 0) or 0) > 0:
            # Open a multi-line structure for the values below.
            lines.append(
                f"🔁 Auto-netting hutang/piutang: *{format_rupiah(netting_result.get('offset_amount', 0))}* "
                "sudah saling menghapus tanpa mengubah transaksi sumber.\n"
            # Close the structure that was opened above.
            )
        lines.append("*Rincian aktif:*")

        # Prepare last debt map for the next step.
        last_debt_map = {}
        # Handle the case where active_details.
        if active_details:
            # Prepare current debt date group for the next step.
            current_debt_date_group = None
            # Process each i, d in the current collection.
            for i, d in enumerate(active_details, 1):
                # Open a multi-line structure for the values below.
                last_debt_map[str(i)] = {
                    "debt_id": d.get("id"),
                    "row_index": d.get("_row_index"),
                    "person_name": person,
                    "type": d.get("type"),
                    "remaining_amount": d.get("remaining_amount"),
                # Close the structure that was opened above.
                }
                # Prepare created date for the next step.
                created_date = format_debt_created_date_for_display(d)
                # Handle the case where created_date != current_debt_date_group.
                if created_date != current_debt_date_group:
                    lines.append(f"\n*{md_safe(format_indonesian_date_group_label(created_date))}*")
                    # Prepare current debt date group for the next step.
                    current_debt_date_group = created_date

                debt_type = str(d.get("type") or "").strip()
                icon = "🔴" if debt_type == "payable" else "🟢"
                direction = "Anda hutang" if debt_type == "payable" else f"{md_safe(person)} hutang"
                desc = str(d.get("description") or "-").strip()
                remaining = format_rupiah(d.get("remaining_amount", 0))
                original = format_rupiah(d.get("original_amount", 0))
                debt_id = str(d.get("id", "-") or "-").strip()
                # Open a multi-line structure for the values below.
                lines.append(
                    f"{i}. {icon} {md_safe(desc)}\n"
                    f"   {direction}: *{remaining}* / awal {original}\n"
                    f"   ID: `{md_code_text(debt_id)}`"
                # Close the structure that was opened above.
                )
        # Handle the fallback path after earlier conditions are skipped.
        else:
            lines.append("Tidak ada rincian aktif.")

        recv = detail.get("receivable") or {}
        pay = detail.get("payable") or {}

        if float(recv.get("original") or 0) > 0:
            pct = float(recv.get("paid_pct") or 0)
            # Open a multi-line structure for the values below.
            lines.append(
                "\n*Progress piutang:*\n"
                f"Sudah bayar: *{format_rupiah(recv.get('paid', 0))}* / {format_rupiah(recv.get('original', 0))} "
                f"({pct:.1f}%)"
            # Close the structure that was opened above.
            )

        if float(pay.get("original") or 0) > 0:
            pct = float(pay.get("paid_pct") or 0)
            # Open a multi-line structure for the values below.
            lines.append(
                "\n*Progress utang Anda:*\n"
                f"Sudah dibayar: *{format_rupiah(pay.get('paid', 0))}* / {format_rupiah(pay.get('original', 0))} "
                f"({pct:.1f}%)"
            # Close the structure that was opened above.
            )

        context.user_data["last_debt_map"] = last_debt_map
        context.user_data["last_debt_person"] = person
        # Handle the case where last_debt_map.
        if last_debt_map:
            # Open a multi-line structure for the values below.
            lines.append(
                "\nKelola rincian dari daftar ini:\n"
                "`/debt_void 1` — batalkan rincian dari detail terakhir\n"
                f"`/debt_void {md_safe(person)}` — batalkan semua rincian aktif {md_safe(person)}\n"
                f"`/debt_void {md_safe(person)} 1` — batalkan rincian nomor 1 milik {md_safe(person)}\n"
                "`/debt_edit 1 nominal 100k` — edit nominal rincian\n"
                f"`/debt_settle {md_safe(person)}` — settle semua debt aktif {md_safe(person)} pakai nominal net otomatis\n"
                f"`/debt_settle {md_safe(person)} 1-3` — settle nomor 1-3 pakai nominal net otomatis\n"
                f"`/debt_settle {md_safe(person)} 1-3 amount=100000 account=DANA` — settle debt nomor 1-3 saja\n"
                f"`{md_safe(person)} bayar hutang 100000 untuk debt 1-3` — versi natural settle debt terpilih\n"
                "Angka mengikuti nomor dari hasil detail `/hutang nama`."
            # Close the structure that was opened above.
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        # Return control to the caller.
        return

    # Debt flow section
    summary = get_debt_person_summary()

    if not summary["payables"] and not summary["receivables"] and not summary.get("balanced"):
        await update.message.reply_text("✅ Tidak ada utang atau piutang aktif.")
        # Return control to the caller.
        return

    lines = ["💸 *Utang & Piutang Aktif per Orang*\n"]

    if summary["payables"]:
        lines.append(f"🔴 *Utang Anda* (net total: {format_rupiah(summary['total_payable'])})")
        for i, d in enumerate(summary["payables"], 1):
            person = d.get("person_name") or "-"
            count = int(d.get("debt_count") or 0)
            # Open a multi-line structure for the values below.
            lines.append(
                f"  {i}. {md_safe(person)} — *{format_rupiah(d.get('remaining_amount', 0))}* "
                f"({count} rincian)\n"
                f"     Detail: `/hutang {md_safe(person)}`"
            # Close the structure that was opened above.
            )

    if summary["payables"] and summary["receivables"]:
        lines.append("")

    if summary["receivables"]:
        lines.append(f"🟢 *Piutang Anda* (net total: {format_rupiah(summary['total_receivable'])})")
        for i, d in enumerate(summary["receivables"], 1):
            person = d.get("person_name") or "-"
            count = int(d.get("debt_count") or 0)
            # Open a multi-line structure for the values below.
            lines.append(
                f"  {i}. {md_safe(person)} — *{format_rupiah(d.get('remaining_amount', 0))}* "
                f"({count} rincian)\n"
                f"     Detail: `/hutang {md_safe(person)}`"
            # Close the structure that was opened above.
            )

    if summary.get("balanced"):
        lines.append("\n⚪ *Netral tapi masih ada rincian aktif*")
        for d in summary["balanced"]:
            person = d.get("person_name") or "-"
            lines.append(f"  • {md_safe(person)} — cek `/hutang {md_safe(person)}`")

    net = summary["total_receivable"] - summary["total_payable"]
    net_label = "🟢 Anda lebih banyak dihutangi" if net >= 0 else "🔴 Anda lebih banyak berhutang"
    lines.append(f"\n{net_label}: *{format_rupiah(abs(net))}*")
    # Open a multi-line structure for the values below.
    lines.append(
        "\nContoh pembayaran/pengurangan:\n"
        "`Raka bayar 5k` — mengurangi piutang Raka secara eksplisit\n"
        "`bayar hutang Raka 10k` — mengurangi utang Anda secara eksplisit\n"
        "`potong hutang Raka 500k` — kompensasi tanpa rekening/manual offset\n"
        "`potong piutang Dimas 20k buat badminton` — kompensasi tanpa rekening\n"
        "`/debt_void 1` — hanya untuk input salah; boleh rollback transaksi sumber ke gross"
    # Close the structure that was opened above.
    )

    # Debt flow section
    # Debt flow section
    # Keep this section separated from the surrounding flow.
    context.user_data["last_debt_map"] = {}
    # Keep this section separated from the surrounding flow.
    context.user_data.pop("last_debt_person", None)
    # Keep this section separated from the surrounding flow.
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# Message handling section

