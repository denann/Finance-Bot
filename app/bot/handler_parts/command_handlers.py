"""Telegram command handlers for onboarding, reports, account balances, budgets, debt, pending expenses, assets, exports, and AI insights."""

# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *
from app.clock import business_now
from app.services.pending_expense_service import find_pending_by_ref
from app.bot.handler_parts.management_browser import start_debt_browser, start_pending_browser
# Import pathlib so /manual can resolve docs relative to the project root.
from pathlib import Path
# Import modular help content so /help stays short and topic-based.
from app.bot.handler_parts.help_content import build_help_text
# Import app.bot.handler_parts.transaction_flow so this module can use its helpers.
from app.bot.handler_parts.transaction_flow import build_pending_expense_confirm_preview, edit_or_continue_keyboard, preview_action_keyboard, preview_action_question
# Import app.bot.handler_parts.state_utils so this module can use its helpers.
from app.bot.handler_parts.state_utils import clear_pending_flow_state, describe_active_pending_flow, has_active_pending_flow
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import resolve_account_name
# Import app.services.chart_service so this module can use its helpers.
from app.services.chart_service import write_monthly_chart_png
# Import privacy notice builder for the read-only /privacy command.
from app.services.privacy_service import build_privacy_notice_text
from app.application.external_io import run_gemini, run_sheets_read
from app.bot.handler_parts.transaction_browser import (
    cancel_transaction_child_actions,
    resume_transaction_browser_after_cancel,
    start_transaction_browser,
)


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    text = (
        "👋 Halo! Saya *Finance Bot* pribadi Anda.\n\n"
        "Saya bisa membantu mencatat, mengecek, dan merapikan keuangan Anda di Google Sheets. Cukup tulis dengan bahasa sehari-hari.\n\n"
        "🚀 *Baru pertama kali pakai?*\n"
        "1. Cek rekening: `/rekening`\n"
        "2. Atur saldo awal: `/set_saldo Cash 500000`\n"
        "3. Catat transaksi: `beli kopi 25rb dari Cash`\n\n"
        "Sebelum data disimpan, bot akan menampilkan preview. Periksa dulu nominal, rekening, kategori, dan tanggalnya. Setelah itu pilih *Simpan* atau *Batal*.\n\n"
        "🧾 *Catat transaksi*\n"
        "• `beli kopi 25rb dari Cash`\n"
        "• `gaji masuk 8 juta ke BRI`\n"
        "• `transfer 200rb dari BRI ke DANA`\n"
        "• kirim foto struk atau QRIS\n\n"
        "🤝 *Utang, piutang, dan split bill*\n"
        "• `Budi minjem 300k`\n"
        "• `catat utang ke Budi 200k`\n"
        "• `nasi goreng 30k bagi 3 sama Dimas Raka`\n\n"
        "📊 *Laporan dan koreksi*\n"
        "`/saldo`, `/harian`, `/mingguan`, `/bulanan`, `/grafik`, `/last`, `/cari`\n"
        "`/transaksi`, `/edit_txn`, `/delete_txn`, `/download_data`\n\n"
        "🕒 *Rencana dan transaksi rutin*\n"
        "`/pending`, `/budget`, `/kategori`, `/recurring`\n"
        "Pending belum mengubah saldo sampai ditandai sudah dibayar.\n\n"
        "💼 *Aset dan analisis*\n"
        "`/assets`, `/networth`, `/insight`, `/ask`, `/audit`, `/coach`\n\n"
        "Butuh panduan? Buka `/quickstart` untuk setup singkat, `/help` untuk bantuan per topik, atau `/manual` untuk panduan lengkap."
    )

    await update.message.reply_text(text, parse_mode="Markdown")




# Helper for format account name list.
def _format_account_name_list(accounts: list[dict]) -> list[str]:
    """Format data into a readable display for account name list."""
    names = []
    # Iterate through each account.
    for account in accounts or []:
        name = str(account.get("account_name") or "").strip()
        if name:
            # Append the current value to names.
            names.append(name)
    return names


# Helper for format accounts table for message.
def _format_accounts_table_for_message(accounts: list[dict]) -> str:
    """Format data into a readable display for accounts table for message."""
    # Validate missing accounts before continuing.
    if not accounts:
        return "Belum ada rekening di sheet `accounts`."

    # Build lines for the response flow.
    lines = []
    # Iterate through each account.
    for account in accounts:
        name = str(account.get("account_name") or "-").strip()
        account_type = str(account.get("type") or "-").strip()
        balance = float(account.get("balance", 0) or 0)
        lines.append(f"• `{md_code_text(name)}` — {md_safe(account_type)} — *{format_rupiah(balance)}*")
    return "\n".join(lines)


# Helper for resolve account name from sheet.
def _resolve_account_name_from_sheet(input_name: str, accounts: list[dict]) -> tuple[str | None, list[str]]:
    """Resolve a user input or reference for account name from sheet."""
    clean = str(input_name or "").strip().strip('"').strip("'")
    # Validate missing clean before continuing.
    if not clean:
        return None, []

    resolved = resolve_account_name(clean)
    if resolved.get("status") == "exact":
        return str(resolved.get("account_name") or "").strip(), []

    if resolved.get("status") == "similar":
        return None, list(resolved.get("suggestions") or [])[:5]

    # Keep a local fallback in case resolver reads fallback accounts but caller already
    # supplied a more specific account list.
    exact_names = _format_account_name_list(accounts)
    suggestions = [name for name in exact_names if clean.lower() in name.lower() or name.lower() in clean.lower()]
    return None, suggestions[:5]


# Helper for guess account type.
def _guess_account_type(account_name: str) -> str:
    """Guess a simple account type for a new account row."""
    clean = str(account_name or "").strip().lower()
    if clean == "cash":
        return "cash"
    if clean in {"dana", "gopay", "ovo", "shopeepay", "linkaja"} or "wallet" in clean:
        return "ewallet"
    return "bank"


# Helper for build set balance preview text.
def _build_set_balance_preview_text(account_name: str, current_balance: float, new_balance: float, *, create_missing: bool = False) -> str:
    """Build the preview text for setting an account balance."""
    delta = float(new_balance or 0) - float(current_balance or 0)
    sign = "+" if delta >= 0 else "-"

    title = "⚠️ *Preview Tambah Rekening dan Set Saldo*" if create_missing else "⚠️ *Preview Set Saldo Rekening*"
    action_note = (
        "Aksi ini akan menambahkan rekening baru ke sheet `accounts`, lalu mengisi saldo awalnya. Tidak akan membuat row transaksi baru."
        if create_missing
        else "Aksi ini akan menimpa saldo rekening di sheet `accounts`. Tidak akan membuat row transaksi baru."
    )
    current_label = "Saldo awal" if create_missing else "Saldo sekarang"

    return (
        f"{title}\n\n"
        f"{action_note}\n\n"
        f"🏦 Rekening: *{md_safe(account_name)}*\n"
        f"💰 {current_label}: *{format_rupiah(current_balance)}*\n"
        f"🎯 Saldo baru: *{format_rupiah(new_balance)}*\n"
        f"🔁 Selisih: *{sign}{format_rupiah(abs(delta))}*\n\n"
        "Klik *Simpan* kalau sudah benar, atau *Batal* kalau masih mau cek lagi."
    )


# Helper for set balance similarity keyboard.
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
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Pakai rekening existing", callback_data="set_balance_similar:use_existing")],
        [InlineKeyboardButton("➕ Tetap buat rekening baru", callback_data="set_balance_similar:create_new")],
        [InlineKeyboardButton("✍️ Tulis ulang", callback_data="cancel:set_balance_rewrite")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:set_balance")],
    ])


# Helper for parse set balance args.
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
    # Validate missing raw before continuing.
    if not raw:
        return "", None

    # Extract amount for validation.
    amount = extract_amount_from_text(raw)
    if amount is None:
        return raw, None

    # Use the last detected amount as the new balance; the remaining text is treated as the account name.
    amount_pattern = re.compile(
        r"(?:rp\.?\s*)?\d[\d.,]*(?:\s*(?:rb|ribu|k|jt|juta|m|mio))?",
        flags=re.IGNORECASE,
    )
    matches = list(amount_pattern.finditer(raw))
    # Extract account text for validation.
    account_text = raw
    if matches:
        match = matches[-1]
        account_text = (raw[:match.start()] + " " + raw[match.end():]).strip()

    account_text = re.sub(
        r"\b(?:saldo|rekening|akun|account|balance|set|jadi|sebesar|ke|to)\b",
        " ",
        account_text,
        flags=re.IGNORECASE,
    )
    account_text = re.sub(r"\s+", " ", account_text).strip().strip('"').strip("'")
    return account_text, float(amount)


async def quickstart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a first-use checklist that guides users through account setup, balance setup, and basic test inputs."""
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    await update.message.reply_text(
        "🚀 *Quickstart Finance Bot*\n\n"
        "1. Catat transaksi: `beli kopi 20k dari Cash`\n"
        "2. Cek saldo: `/saldo`\n"
        "3. Cek laporan: `/bulanan`\n"
        "4. Cek utang/piutang: `/hutang`\n"
        "5. Baca panduan: `/help` atau `/manual`",
        parse_mode="Markdown",
    )
    return

    # Extract accounts for validation.
    accounts = await run_sheets_read("get_all_accounts", get_all_accounts)
    # Extract account names for validation.
    account_names = _format_account_name_list(accounts)
    account_text = ", ".join(f"`{md_code_text(name)}`" for name in account_names) if account_names else "belum ada rekening"

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
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any active wizard, preview, or pending confirmation state."""
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    active_label = describe_active_pending_flow(context)
    removed = clear_pending_flow_state(context)
    canceled_actions = cancel_transaction_child_actions(context)

    if await resume_transaction_browser_after_cancel(update, context):
        return

    if removed or canceled_actions:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "🚫 *Flow aktif dibatalkan.*\n\n"
            f"State yang dibersihkan: *{md_safe(active_label or 'pending flow')}*\n\n"
            "Tidak ada data yang disimpan.",
            parse_mode="Markdown",
        )
        return

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        "ℹ️ Tidak ada flow aktif yang perlu dibatalkan.",
        parse_mode="Markdown",
    )


async def set_saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /set_saldo and prepare a confirmation preview before updating an account balance."""
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Extract accounts for validation.
    accounts = await run_sheets_read("get_all_accounts", get_all_accounts)
    raw_arg = " ".join(context.args).strip() if context.args else ""

    # Regex fallback path: MessageHandler does not populate context.args, so parse the raw Telegram text.
    if not raw_arg:
        raw_text = getattr(getattr(update, "message", None), "text", "") or ""
        match = re.match(r"^/(?:set_saldo|saldo_set|set_balance)(?:@\w+)?\s*(.*)$", raw_text.strip(), flags=re.IGNORECASE)
        if match:
            # Prepare raw arg from the incoming input.
            raw_arg = match.group(1).strip()

    # Validate missing raw arg before continuing.
    if not raw_arg:
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
        )
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    account_arg, new_balance = _parse_set_balance_args(raw_arg)
    if new_balance is None:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Nominal saldo belum terbaca.\n\n"
            "Contoh yang benar:\n"
            "`/set_saldo DANA 500k`\n"
            "`/set_saldo BRI 2500000`",
            parse_mode="Markdown",
        )
        return

    account_name, suggestions = _resolve_account_name_from_sheet(account_arg, accounts)
    # Validate missing account name and suggestions before continuing.
    if not account_name and suggestions:
        suggested_name = suggestions[0]
        context.user_data["pending_set_balance_suggestion"] = {
            "input_account_name": account_arg,
            "suggested_account_name": suggested_name,
            "new_balance": float(new_balance),
            "account_type": _guess_account_type(account_arg),
        }
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "⚠️ *Kemungkinan rekening duplikat*\n\n"
            f"Input rekening: `{md_code_text(account_arg or '-')}`\n"
            f"Mirip dengan rekening existing: *{md_safe(suggested_name)}*\n\n"
            "Pilih salah satu supaya saldo tidak pecah ke dua nama rekening yang maksudnya sama.",
            parse_mode="Markdown",
            reply_markup=_set_balance_similarity_keyboard(),
        )
        return

    # Validate missing account name before continuing.
    if not account_name:
        context.user_data["pending_set_balance"] = {
            "account_name": account_arg,
            "current_balance": 0.0,
            "new_balance": float(new_balance),
            "delta": float(new_balance),
            "create_missing": True,
            "account_type": _guess_account_type(account_arg),
        }

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            _build_set_balance_preview_text(account_arg, 0.0, float(new_balance), create_missing=True),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("set_balance"),
        )
        return

    current_balance = await run_sheets_read("get_account_balance", get_account_balance, account_name)
    if current_balance is None:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"❌ Saldo rekening `{md_code_text(account_name)}` belum bisa dibaca dari sheet `accounts`.",
            parse_mode="Markdown",
        )
        return

    delta = float(new_balance) - float(current_balance)
    sign = "+" if delta >= 0 else "-"

    context.user_data["pending_set_balance"] = {
        "account_name": account_name,
        "current_balance": float(current_balance),
        "new_balance": float(new_balance),
        "delta": float(delta),
    }

    # Prepare text from the incoming input.
    text = _build_set_balance_preview_text(account_name, current_balance, float(new_balance), create_missing=False)

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=confirm_keyboard("set_balance"))

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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    topic = " ".join(context.args or []).strip()
    await reply_long_markdown(update, build_help_text(topic))
    return

async def manual_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the generated Finance Bot manual PDF.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context for this command. It is accepted for
            handler compatibility and is not mutated by this read-only flow.

    Returns:
        `None` after sending the PDF or a fallback message.

    Side effects:
        Sends `docs/help_manual.pdf` as a Telegram document when the file exists.

    Flow constraints:
        Keep this read-only. Do not generate the PDF inside the bot process, do
        not write to Google Sheets, and do not hardcode absolute local paths.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    manual_path = Path(__file__).resolve().parents[3] / "docs" / "help_manual.pdf"
    # Show a safe fallback if the generated manual file is not present.
    if not manual_path.exists():
        await update.message.reply_text(
            "❌ Manual PDF belum tersedia. Silakan hubungi admin atau generate ulang file manual.",
            parse_mode="Markdown",
        )
        return

    # Send the PDF as a document without mutating any finance data.
    with manual_path.open("rb") as file_obj:
        await update.message.reply_document(
            document=InputFile(file_obj, filename="help_manual.pdf"),
            caption="📖 Manual lengkap Finance Bot.",
        )


async def privacy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the Finance Bot data privacy notice.

    Args:
        update: Telegram Update object supplied by python-telegram-bot for the
            `/privacy` command.
        context: Telegram context supplied by the framework. The handler keeps
            the standard signature but does not read or mutate user state.

    Returns:
        `None` after sending the privacy message.

    Side effects:
        Sends one Telegram message. It does not read Google Sheets, write Google
        Sheets, call Gemini, export files, or store new privacy data.

    Flow constraints:
        Keep the command read-only. Do not add a Batal button because the output
        does not open a wizard, preview, or confirmation flow.
    """
    if not is_authorized(update):
        # Keep privacy details visible only to the configured bot user.
        await reject_unauthorized(update)
        return

    # Send informational text only; no pending state is created.
    await update.message.reply_text(build_privacy_notice_text(), parse_mode="Markdown")


# Helper for add session chat history.
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
    if context is None:
        return

    clean_text = str(text or "").strip()
    # Validate missing clean text before continuing.
    if not clean_text:
        return

    history = context.user_data.get("finance_chat_history", [])
    history.append({
        "role": str(role or "user"),
        "text": clean_text[:1200],
    })
    context.user_data["finance_chat_history"] = history[-limit:]


# Helper for get session chat history.
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
    if context is None:
        return []
    history = context.user_data.get("finance_chat_history", [])
    return history[-limit:]


# Helper for attach session history.
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
    data = dict(context_data or {})
    history = get_session_chat_history(context)
    if history:
        data["chat_history"] = history
        data["chat_history_note"] = (
            "Riwayat ini hanya untuk memahami konteks pertanyaan lanjutan. "
            "Jangan jadikan chat_history sebagai sumber angka utama; angka faktual harus dari monthly_context/relevant_transactions."
        )
    return data


# Helper for normalize ai insight for telegram.
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
    # Validate missing clean before continuing.
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
    }
    # Iterate through each raw key, label.
    for raw_key, label in key_labels.items():
        # Normalize clean before matching.
        clean = clean.replace(raw_key, label)

    # Humanize any remaining snake_case key that slipped through.
    clean = re.sub(
        r"\b([A-Za-z]+(?:_[A-Za-z0-9]+)+)\b",
        lambda match: match.group(1).replace("_", " "),
        clean,
    )

    # Reduce over-nested spacing from Gemini.
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    clean = re.sub(r"(?m)^•\s+\*([^*]+)\*:\s*", r"• *\1:* ", clean)
    return clean.strip()


# Handle the asynchronous send finance insight reply workflow.
async def send_finance_insight_reply(
    update: Update,
    mode: str,
    context_data: dict,
    question: str = "",
    prefix: str = "🤖 Insight Gemini",
    context: ContextTypes.DEFAULT_TYPE | None = None,
    remember_history: bool = False,
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
    answer = await run_gemini(
        f"finance_{mode}",
        generate_finance_insight,
        mode,
        context_data,
        question=question,
    )

    # Handle remember history and context is not None.
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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

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
    )
    await update.message.reply_text(text, parse_mode="Markdown")


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    month_arg = " ".join(context.args).strip() if context.args else None
    month = normalize_insight_month(month_arg)
    data = await run_sheets_read("build_monthly_finance_context", build_monthly_finance_context, month)
    # Send the Telegram response before continuing.
    await send_finance_insight_reply(
        update,
        "monthly_insight",
        data,
        question=f"Buat insight/narasi keuangan untuk {month}",
        prefix=f"📌 Insight Finance {month}",
    )


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    month_arg = " ".join(context.args).strip() if context.args else None
    month = normalize_insight_month(month_arg)
    data = await run_sheets_read("build_audit_context", build_audit_context, month)
    # Send the Telegram response before continuing.
    await send_finance_insight_reply(
        update,
        "audit",
        data,
        question=f"Audit data finance dan anomali untuk {month}",
        prefix=f"🧹 Audit Finance {month}",
    )


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    question = " ".join(context.args).strip()
    # Validate missing question before continuing.
    if not question:
        # Send the Telegram response before continuing.
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
        data = await run_sheets_read("build_audit_context", build_audit_context, None)
    elif mode == "coach":
        data = await run_sheets_read("build_coach_context", build_coach_context, None, question=question)
    # Use the fallback path when no earlier branch matched.
    else:
        data = await run_sheets_read("build_ask_finance_context", build_ask_finance_context, question)

    data = attach_session_history(context, data)
    # Send the Telegram response before continuing.
    await send_finance_insight_reply(
        update,
        mode,
        data,
        question=question,
        prefix="💬 Jawaban Finance",
        # Prepare context from the incoming input.
        context=context,
        remember_history=True,
    )


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    question = " ".join(context.args).strip() if context.args else "Kasih saran finansial ringan untuk bulan ini."
    data = await run_sheets_read("build_coach_context", build_coach_context, None, question=question)
    data = attach_session_history(context, data)
    # Send the Telegram response before continuing.
    await send_finance_insight_reply(
        update,
        "coach",
        data,
        question=question,
        prefix="🧭 Finance Coach",
        # Prepare context from the incoming input.
        context=context,
        remember_history=True,
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
    # Validate missing should handle finance question(user text) before continuing.
    if not should_handle_finance_question(user_text):
        return False

    mode = route_finance_question_mode(user_text)
    if mode == "audit":
        data = await run_sheets_read("build_audit_context", build_audit_context, None)
    elif mode == "coach":
        data = await run_sheets_read("build_coach_context", build_coach_context, None, question=user_text)
    # Use the fallback path when no earlier branch matched.
    else:
        data = await run_sheets_read("build_ask_finance_context", build_ask_finance_context, user_text)

    data = attach_session_history(context, data)
    # Send the Telegram response before continuing.
    await send_finance_insight_reply(
        update,
        mode,
        data,
        question=user_text,
        prefix="🤖 Analisis Finance",
        # Prepare context from the incoming input.
        context=context,
        remember_history=True,
    )
    return True


# Helper for format report delta.
def format_report_delta(delta_info: dict, *, positive_when_up: bool, as_count: bool = False) -> str:
    """Format data into a readable display for report delta."""
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
    # Use the fallback path when no earlier branch matched.
    else:
        # Prepare value text from the incoming input.
        value_text = f"{sign}{format_rupiah(abs(delta))}"

    pct_text = ""
    if pct is not None:
        pct_text = f" ({pct:+.1f}%)"

    return f"{color}{arrow} {value_text}{pct_text}"


# Helper for append report comparison lines.
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
    # Validate missing comparison before continuing.
    if not comparison:
        return

    lines.append(f"📈 Vs {label}:")
    lines.append(f"   ✅ Pemasukan : {format_report_delta(comparison.get('total_income'), positive_when_up=True)}")
    lines.append(f"   ❌ Pengeluaran: {format_report_delta(comparison.get('total_expense'), positive_when_up=False)}")
    lines.append(f"   📊 Net       : {format_report_delta(comparison.get('net'), positive_when_up=True)}")
    lines.append(f"   📝 Transaksi : {format_report_delta(comparison.get('count'), positive_when_up=False, as_count=True)}\n")


# Helper for get report expense display.
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
    return format_expense_net_gross(float(net or 0), gross)


# Helper for append report metric lines.
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


# Helper for append account report lines.
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
    if balance is not None:
        lines.append(f"💰 Saldo Saat Ini : *{format_rupiah(balance)}*")
    lines.append(f"✅ Pemasukan      : *{format_rupiah(report.get('total_income', 0))}*")
    lines.append(f"❌ Pengeluaran    : *{get_report_expense_display(report)}*")
    lines.append(f"🔁 Transfer Masuk : *{format_rupiah(report.get('total_transfer_in', 0))}*")
    lines.append(f"🔁 Transfer Keluar: *{format_rupiah(report.get('total_transfer_out', 0))}*")
    lines.append(f"📊 Pergerakan Bersih: *{format_rupiah(report.get('net', 0))}*")
    lines.append(f"📝 Transaksi      : {report.get('count', 0)} item")


# Helper for append recent account transaction lines.
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
    # Validate missing transactions before continuing.
    if not transactions:
        return

    lines.append("\n*Transaksi Terbaru Rekening:*")
    # Iterate through each i, txn.
    for i, txn in enumerate(transactions[:limit], 1):
        # Append the current value to lines.
        lines.extend(build_transaction_display_lines(txn, index=i, include_date=True, include_id=True))

# Helper for append report category breakdown lines.
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
    # Validate missing by category before continuing.
    if not by_category:
        return

    lines.append("*Pengeluaran per Kategori:*")
    total_expense = float((report or {}).get("total_expense", 0) or 0)
    category_comparison = (report or {}).get("category_comparison") or {}
    by_category_gross = (report or {}).get("by_category_gross") or {}

    # Iterate through each cat, amount.
    for cat, amount in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        pct = (float(amount) / total_expense) * 100 if total_expense else 0
        bar = build_progress_bar(pct)
        trend = format_report_delta(category_comparison.get(cat), positive_when_up=False)
        trend_text = f" | vs {comparison_label}: {trend}" if comparison_label else ""
        # Extract gross amount for validation.
        gross_amount = by_category_gross.get(cat, amount)
        # Extract amount text for validation.
        amount_text = format_expense_net_gross(float(amount or 0), float(gross_amount or 0))
        lines.append(
            f"  • {md_safe(cat)}: *{amount_text}*\n"
            f"    {bar} {pct:.1f}%{trend_text}"
        )


# Helper for build top expense debt lines.
def build_top_expense_debt_lines(txn: dict, amount: float) -> list[str]:
    """Build the data structure or message text for top expense debt lines."""
    return []


# Helper for get top expense transactions.
def get_top_expense_transactions(report: dict, limit: int = 3) -> list[dict]:
    """Return expense transactions sorted by net expense amount.

    Args:
        report: Report dict from `/harian`, `/mingguan`, or `/bulanan`.
        limit: Maximum number of transactions to return.

    Returns:
        Expense rows sorted descending by net amount after receivable shares.
    """
    expenses = [
        t for t in (report or {}).get("transactions", [])
        if str((t or {}).get("type", "")).strip().lower() == "expense"
        and get_net_expense_after_receivable(t) > 0
    ]
    return sorted(expenses, key=get_net_expense_after_receivable, reverse=True)[:limit]


# Helper for append top expense lines.
def append_top_expense_lines(lines: list[str], report: dict):
    """Append Top 3 expense lines using net expense contribution.

    Args:
        lines: Mutable Markdown line list for the report response.
        report: Daily, weekly, or monthly report dict with enriched
            `transactions` and net-based `total_expense`.

    Returns:
        None. The function mutates `lines` in place only when expenses exist.
    """
    top = get_top_expense_transactions(report, limit=3)
    # Validate missing top before continuing.
    if not top:
        return

    lines.append("\n*Top 3 Pengeluaran:*")
    total_expense = float((report or {}).get("total_expense", 0) or 0)

    # Iterate through each i, txn.
    for i, txn in enumerate(top, 1):
        # Extract amount for validation.
        amount = get_net_expense_after_receivable(txn)
        contrib = (amount / total_expense * 100) if total_expense else 0
        lines.extend(
            build_transaction_display_lines(
                txn,
                index=i,
                # Extract include date for validation.
                include_date=True,
                include_id=True,
                contribution_pct=contrib,
            )
        )


# Helper for normalize chart type.
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
    return None


# Helper for parse grafik args.
def parse_grafik_args(args: list[str] | None) -> tuple[str, str | None]:
    """Parse `/grafik` arguments into chart type and month argument.

    Args:
        args: Telegram command args after `/grafik`.

    Returns:
        Tuple of `(chart_type, month_arg)`. Chart type defaults to `timeseries`;
        month argument defaults to `None`, which means current month.
    """
    chart_type = "timeseries"
    # Prepare month tokens from the incoming input.
    month_tokens = []
    # Iterate through each token.
    for token in args or []:
        # Normalize normalized type before matching.
        normalized_type = normalize_chart_type(token)
        if normalized_type:
            chart_type = normalized_type
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Append the current value to month tokens.
        month_tokens.append(token)
    month_arg = " ".join(month_tokens).strip() or None
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
    chart_path = write_monthly_chart_png(report, chart_type)
    month_label = str((report or {}).get("month") or "bulan").replace("/", "-")
    filename = f"grafik-{chart_type}-{month_label}.png"
    caption = (
        f"📈 Grafik {chart_type} {month_label}\n"
        "Basis angka: pengeluaran net setelah piutang split bill/talangan."
    )
    # Run this operation in a guarded block so failures can be handled.
    try:
        with open(chart_path, "rb") as file_obj:
            # Send the Telegram response before continuing.
            await update.message.reply_document(
                document=InputFile(file_obj, filename=filename),
                caption=caption,
            )
    # Run cleanup that must happen after the guarded operation.
    finally:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Append the current value to os.
            os.remove(chart_path)
        # Handle an expected failure from the guarded operation above.
        except OSError:
            # Keep this intentionally empty block valid.
            pass


# Helper for is category detail report.
def is_category_detail_report(report: dict) -> bool:
    """Check whether a condition is true for category detail report."""
    return bool((report or {}).get("category_filter"))


# Helper for get category list title.
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


# Helper for append category detail summary.
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
    if account:
        lines.append(f"🏦 Rekening : *{md_safe(account)}*")
    if total_income > 0:
        lines.append(f"✅ Pemasukan : *{format_rupiah(total_income)}*")
    # Handle total expense > 0 or total income == 0.
    if total_expense > 0 or total_income == 0:
        lines.append(f"❌ Pengeluaran: *{get_report_expense_display(report)}*")
    if account:
        transfer_in = float((report or {}).get("total_transfer_in", 0) or 0)
        transfer_out = float((report or {}).get("total_transfer_out", 0) or 0)
        if transfer_in > 0:
            lines.append(f"🔁 Transfer Masuk : *{format_rupiah(transfer_in)}*")
        if transfer_out > 0:
            lines.append(f"🔁 Transfer Keluar: *{format_rupiah(transfer_out)}*")
    # Fall back when total transfer > 0.
    elif total_transfer > 0:
        lines.append(f"🔄 Transfer   : *{format_rupiah(total_transfer)}*")
    # Handle total income > 0 and total expense > 0.
    if total_income > 0 and total_expense > 0:
        lines.append(f"📊 Net       : *{format_rupiah((report or {}).get('net', 0))}*")
    lines.append(f"📝 Transaksi : {(report or {}).get('count', 0)} item")
    append_report_comparison_lines(lines, report, comparison_label)


# Helper for append category transaction lines.
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
    # Validate missing transactions before continuing.
    if not transactions:
        return

    # Append the current value to lines.
    lines.append(get_category_list_title(category))

    # Iterate through each i, t.
    for i, t in enumerate(transactions, 1):
        note = str(t.get("catatan", "") or "").strip()
        lines.extend(
            build_transaction_display_lines(
                t,
                index=i,
                # Extract include date for validation.
                include_date=include_date,
                include_id=True,
                note=note or None,
            )
        )



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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Extract accounts for validation.
    accounts = await run_sheets_read("get_all_accounts", get_all_accounts)
    # Validate missing accounts before continuing.
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

    # Iterate through each acc.
    for acc in accounts:
        emoji = emoji_map.get(str(acc.get("type", "")).lower(), "💳")
        name = acc.get("account_name", "")
        balance = float(acc.get("balance", 0) or 0)
        lines.append(f"{emoji} {name}: *{format_rupiah(balance)}*")

    lines.append(f"\n📊 Total: *{format_rupiah(total)}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    raw_arg = " ".join(context.args).strip() if context.args else ""

    # Implementation note for this project-specific finance flow.
    if not raw_arg:
        # Await saldo handler before continuing.
        await saldo_handler(update, context)
        return

    account_arg, period_arg = split_account_period_arg(raw_arg)
    # Validate missing account arg before continuing.
    if not account_arg:
        # Await saldo handler before continuing.
        await saldo_handler(update, context)
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        report = await run_sheets_read("get_account_report", get_account_report, account_arg, period_arg)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Send the Telegram response before continuing.
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

    transactions = sorted(
        report.get("transactions", []) or [],
        key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)),
        reverse=True,
    )

    title = f"Transaksi Rekening {account} — {period_label}"
    await start_transaction_browser(
        update, context, transactions, family="rekening", title=title,
        query={
            "account": str(report.get("account_filter") or account),
            "period_type": str(report.get("period_type") or "month"),
            "month": str(report.get("month") or ""),
        },
        summary_label="📊 Ringkasan Rekening", account_filter=account,
    )



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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    raw_arg = " ".join(context.args).strip() if context.args else None
    date_arg, category_arg, account_arg = split_report_filter_args(raw_arg, "date")

    # Run this operation in a guarded block so failures can be handled.
    try:
        report = await run_sheets_read("get_daily_report", get_daily_report, date_arg, category_arg, account_arg)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Send the Telegram response before continuing.
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
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                f"📭 Tidak ada transaksi {' dan '.join(filter_bits)} pada {date_str}.",
                parse_mode="Markdown",
            )
        # Use the fallback path when no earlier branch matched.
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

    append_top_expense_lines(lines, report)

    await reply_long_markdown(update, "\n".join(lines))


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    raw_arg = " ".join(context.args).strip() if context.args else None
    date_arg, category_arg, account_arg = split_report_filter_args(raw_arg, "date")

    # Run this operation in a guarded block so failures can be handled.
    try:
        report = await run_sheets_read("get_weekly_report", get_weekly_report, date_arg, category_arg, account_arg)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Send the Telegram response before continuing.
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
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                f"📭 Tidak ada transaksi {' dan '.join(filter_bits)} minggu ini.\n"
                f"({report['date_from']} s/d {report['date_to']})",
                parse_mode="Markdown",
            )
        # Use the fallback path when no earlier branch matched.
        else:
            # Send the Telegram response before continuing.
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

    append_top_expense_lines(lines, report)

    await reply_long_markdown(update, "\n".join(lines))


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    chart_type, month_arg = parse_grafik_args(context.args)

    # Run this operation in a guarded block so failures can be handled.
    try:
        year, month_num = parse_report_month_arg(month_arg)
        report = await run_sheets_read("get_monthly_report", get_monthly_report, year, month_num)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/grafik`\n"
            "`/grafik 2026-06`\n"
            "`/grafik line 2026-06`\n"
            "`/grafik bar 2026-06`\n"
            "`/grafik pie 2026-06`",
            parse_mode="Markdown",
        )
        return

    if report.get("count", 0) == 0:
        await update.message.reply_text(f"📭 Belum ada transaksi untuk {report.get('month', '-')}.")
        return

    # Send the Telegram response before continuing.
    await send_monthly_chart_document(update, report, chart_type)


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    raw_arg = " ".join(context.args).strip() if context.args else None
    month_arg, category_arg, account_arg = split_report_filter_args(raw_arg, "month")

    # Run this operation in a guarded block so failures can be handled.
    try:
        year, month_num = parse_report_month_arg(month_arg)
        report = await run_sheets_read("get_monthly_report", get_monthly_report, year, month_num, category_arg, account_arg)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Send the Telegram response before continuing.
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
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                f"📭 Tidak ada transaksi {' dan '.join(filter_bits)} pada {month_name}.",
                parse_mode="Markdown",
            )
        # Use the fallback path when no earlier branch matched.
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

    append_top_expense_lines(lines, report)

    # Build budget summary for the response flow.
    budget_summary = await run_sheets_read("get_budget_summary", get_budget_summary, month_name)
    if budget_summary:
        lines.append("\n*Budget vs Realisasi:*")
        # Iterate through each item.
        for item in budget_summary:
            bar = build_progress_bar(item["pct_used"])
            lines.append(
                f"{item['emoji']} {item['category']}\n"
                f"  {bar} {item['pct_used']}%"
            )

    await reply_long_markdown(update, "\n".join(lines))

    # Automatic insight after /bulanan.
    # Message handling section
    try:
        insight_data = await run_sheets_read("build_monthly_finance_context", build_monthly_finance_context, month_name)
        insight_text = await run_gemini(
            "finance_monthly_auto",
            generate_finance_insight,
            "monthly_auto",
            insight_data,
            question=f"Buat insight singkat otomatis setelah laporan bulanan {month_name}",
        )
        await update.message.reply_text(f"🤖 Insight Bulanan Gemini\n\n{insight_text}")
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"⚠️ Ringkasan bulanan berhasil, tapi insight Gemini gagal dibuat: {str(e)}"
        )


    # Send the Telegram response before continuing.
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
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"⚠️ Ringkasan dan insight sudah terkirim, tapi grafik time series gagal dibuat: {str(e)}"
        )


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Prepare args from the incoming input.
    args = context.args
    # Validate missing args before continuing.
    if not args:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "🔍 Masukkan keyword pencarian.\n"
            "Contoh: `/cari kopi`",
            parse_mode="Markdown",
        )
        return

    keyword = " ".join(args)
    # Build results for the response flow.
    results = await run_sheets_read("search_transactions", search_transactions, keyword, limit=None)

    # Validate missing results before continuing.
    if not results:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"🔍 Tidak ada transaksi dengan keyword *{md_safe(keyword)}*.",
            parse_mode="Markdown",
        )
        return

    await start_transaction_browser(
        update, context, results, family="cari",
        title=f'Hasil pencarian: "{keyword}"',
        query={"keyword": keyword}, summary_label="📊 Ringkasan Hasil",
    )


# Helper for format budget net gross.
def format_budget_net_gross(net_amount: float, gross_amount: float) -> str:
    """Format data into a readable display for budget net gross."""
    net = float(net_amount or 0)
    gross = float(gross_amount or 0)
    if abs(net - gross) > 0.0001:
        return f"{format_rupiah(net)} ({format_rupiah(gross)})"
    return format_rupiah(net)

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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    month_arg = context.args[0] if context.args else None

    # Run this operation in a guarded block so failures can be handled.
    try:
        month = normalize_month(month_arg)
    # Handle an expected failure from the guarded operation above.
    except ValueError as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/budget`\n"
            "`/budget 2026-06`",
            parse_mode="Markdown",
        )
        return

    # Build summary for the response flow.
    summary = await run_sheets_read("get_budget_summary", get_budget_summary, month)

    # Validate missing summary before continuing.
    if not summary:
        # Send the Telegram response before continuing.
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

    # Iterate through each item.
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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    months = await run_sheets_read("get_budget_months", get_budget_months)

    # Validate missing months before continuing.
    if not months:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "📭 Belum ada histori budget.\n\n"
            "Set budget dulu, contoh:\n"
            "`budget makan 1.5 juta`\n"
            "`budget makan 2 juta 2026-07`",
            parse_mode="Markdown",
        )
        return

    lines = ["🗂️ *Histori Budget Tersedia*\n"]

    # Iterate through each month.
    for month in sorted(months, reverse=True):
        # Run this operation in a guarded block so failures can be handled.
        try:
            label = format_month_label(month)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            label = month

        lines.append(f"• `{month}` — {label}")

    lines.append(
        "\nLihat detail dengan:\n"
        "`/budget 2026-06`"
    )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# Helper for build pending expense lines.
def build_pending_expense_lines(items: list[dict], title: str, total: float | None = None) -> list[str]:
    """Build the data structure or message text for pending expense lines."""
    lines = [f"🕒 *{md_safe(title)}*\n"]

    # Validate missing items before continuing.
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

    # Iterate through each i, item.
    for i, item in enumerate(items, 1):
        due_date = str(item.get("due_date", "") or "").strip()
        due_precision = str(item.get("due_precision", "") or "unknown").strip().lower()
        month = str(item.get("month", "") or "-").strip()

        if due_date:
            # Prepare due text from the incoming input.
            due_text = due_date
        elif due_precision == "month":
            due_text = f"{month} (tanggal belum pasti)"
        # Use the fallback path when no earlier branch matched.
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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    period = " ".join(context.args).strip() if context.args else None

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Build result for the response flow.
        result = await run_sheets_read("get_pending_expenses", get_pending_expenses, period=period, active_only=True)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"❌ Gagal membaca pending expense: {md_safe(str(e))}",
            parse_mode="Markdown",
        )
        return

    label = result.get("label") or "bulan ini"
    await start_pending_browser(update, context, result.get("items") or [], label=label)


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Prepare raw text from the incoming input.
    raw_text = update.message.text.strip()
    if raw_text.lower().startswith("/pending_add"):
        raw_text = re.sub(r"^/pending_add(?:@\w+)?\s*", "", raw_text, flags=re.IGNORECASE).strip()
    elif raw_text.lower().startswith("/rencana"):
        raw_text = re.sub(r"^/rencana(?:@\w+)?\s*", "", raw_text, flags=re.IGNORECASE).strip()

    # Validate missing raw text before continuing.
    if not raw_text:
        # Send the Telegram response before continuing.
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

    # Run this operation in a guarded block so failures can be handled.
    try:
        item = build_pending_expense_from_text(raw_text)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
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
    # Send the Telegram response before continuing.
    await update.message.reply_text(
        f"{build_pending_expense_confirm_preview(item, include_question=False)}\n\n{preview_action_question(True)}",
        parse_mode="Markdown",
        reply_markup=preview_action_keyboard("pending_expense", True),
    )


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Validate missing context.args before continuing.
    if not context.args:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Masukkan pending ID.\n\n"
            "Contoh:\n"
            "`/pending_paid pend_20260626_123456_xxxxxxxx BRI`",
            parse_mode="Markdown",
        )
        return

    pending_id = context.args[0].strip()
    # Extract account for validation.
    account = context.args[1].strip() if len(context.args) >= 2 else None

    _, item = await run_sheets_read("find_pending_by_ref", find_pending_by_ref, pending_id)
    if not item:
        await update.message.reply_text("❌ Pending expense tidak ditemukan.")
        return
    status = str(item.get("status") or "pending").strip().lower()
    if status in {"paid", "cancelled", "canceled", "done", "selesai"}:
        await update.message.reply_text(f"❌ Pending expense sudah berstatus {md_safe(status)}.", parse_mode="Markdown")
        return
    account_display = account or item.get("account") or ""
    if not account_display:
        await update.message.reply_text("❌ Rekening belum diketahui. Gunakan: `/pending_paid pending_id BRI`", parse_mode="Markdown")
        return

    await send_financial_mutation_preview(
        update,
        context,
        operation="pending_paid",
        payload={"pending_id": pending_id, "account": account_display},
        preview_text=(
            "🧾 *Preview final — tandai pending paid*\n\n"
            f"🔖 Pending ID: `{md_code_text(pending_id)}`\n"
            f"📝 Deskripsi: {md_safe(item.get('description') or item.get('subject') or '-')}\n"
            f"💳 Rekening: *{md_safe(account_display)}*\n"
            f"💰 Transaksi keluar: *-{format_rupiah(float(item.get('amount') or 0))}*\n\n"
            "Simpan perubahan ini atau batal?"
        ),
    )


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Validate missing context.args before continuing.
    if not context.args:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Masukkan pending ID.\n\n"
            "Contoh:\n"
            "`/pending_cancel pend_20260626_123456_xxxxxxxx`",
            parse_mode="Markdown",
        )
        return

    pending_id = context.args[0].strip()
    _, item = await run_sheets_read("find_pending_by_ref", find_pending_by_ref, pending_id)
    if not item:
        await update.message.reply_text("❌ Pending expense tidak ditemukan.")
        return
    status = str(item.get("status") or "pending").strip().lower()
    if status in {"paid", "cancelled", "canceled", "done", "selesai"}:
        await update.message.reply_text(f"❌ Pending expense sudah berstatus {md_safe(status)}.", parse_mode="Markdown")
        return

    await send_financial_mutation_preview(
        update,
        context,
        operation="pending_cancel",
        payload={"pending_id": pending_id},
        preview_text=(
            "🧾 *Preview final — batalkan pending expense*\n\n"
            f"🔖 Pending ID: `{md_code_text(pending_id)}`\n"
            f"📝 Deskripsi: {md_safe(item.get('description') or item.get('subject') or '-')}\n"
            f"💰 Nominal: *{format_rupiah(float(item.get('amount') or 0))}*\n\n"
            "Simpan perubahan pembatalan ini atau batal?"
        ),
    )


# Helper for parse amount text.
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
    # Validate missing raw before continuing.
    if not raw:
        return 0

    unit = ""
    for suffix in ["ribu", "rb", "juta", "jt", "miliar", "miliard", "milyard", "k", "m"]:
        if raw.endswith(suffix):
            unit = suffix
            # Prepare raw from the incoming input.
            raw = raw[: -len(suffix)]
            # Leave the loop after the target condition has been reached.
            break

    # Run this operation in a guarded block so failures can be handled.
    try:
        if unit in {"rb", "ribu", "k"}:
            # 331.063k means 331,063 rupiah here, not 331,063,000.
            if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
                return float(raw.replace(".", ""))
            return float(raw) * 1_000
        if unit in {"jt", "juta", "m"}:
            return float(raw) * 1_000_000
        if unit in {"miliar", "miliard", "milyard"}:
            return float(raw) * 1_000_000_000
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
            return float(raw.replace(".", ""))
        return float(raw)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return 0

# Helper for extract split bill total amount.
def extract_split_bill_total_amount(raw_text: str) -> float | None:
    """Extract the required part of input for split bill total amount."""
    text = str(raw_text or "").strip()
    amount_token = r"(?P<amount>\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m)?)"
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"

    patterns = [
        # 22k dibagi 2 sama raka
        rf"{amount_token}\s+{split_word}\s*(?:jadi\s*)?\d+",
        # 22k sama raka dibagi 2
        rf"{amount_token}\s+{friend_marker}\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{{0,80}}\s+{split_word}\s*(?:jadi\s*)?\d+",
    ]

    # Iterate through each pattern.
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_amount_text(match.group("amount"))

    return None

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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Prepare text from the incoming input.
    text = update.message.text.strip()
    text = re.sub(r"^/(?:set_budget)(?:@\w+)?\s*", "budget ", text, flags=re.IGNORECASE).strip()
    # Normalize text lower before matching.
    text_lower = text.lower()

    # Import app.nlp.normalizer so this module can use its helpers.
    from app.nlp.normalizer import extract_amount_from_text

    # Extract amount for validation.
    amount = extract_amount_from_text(text_lower)
    # Validate missing amount before continuing.
    if not amount:
        # Send the Telegram response before continuing.
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
        # Run this operation in a guarded block so failures can be handled.
        try:
            month = normalize_month(raw_month)
        # Handle an expected failure from the guarded operation above.
        except ValueError as e:
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                f"❌ {str(e)}\n"
                "Contoh bulan: `2026-07`",
                parse_mode="Markdown",
            )
            return
    # Use the fallback path when no earlier branch matched.
    else:
        month = normalize_month(None)

    # Take the label after the word budget, then remove amount and month tokens.
    label_text = re.sub(r"^\s*budget\s+", "", text_lower).strip()
    label_text = re.sub(r"\b20\d{2}[-/](0?[1-9]|1[0-2])\b", " ", label_text)
    label_text = re.sub(r"\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)?", " ", label_text)
    label_text = re.sub(r"\b(per\s+bulan|bulan|untuk|buat|sebesar|senilai)\b", " ", label_text)
    label_text = re.sub(r"\s+", " ", label_text).strip(" .,-")

    # Validate missing label text before continuing.
    if not label_text:
        # Send the Telegram response before continuing.
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

    # Prepare tokens from the incoming input.
    tokens = set(label_text.split())
    # Extract matched category for validation.
    matched_category = None

    # Exact phrase dulu, lalu token-level alias.
    if label_text in alias_to_category:
        # Extract matched category for validation.
        matched_category = alias_to_category[label_text]
    # Use the fallback path when no earlier branch matched.
    else:
        # Iterate through each token.
        for token in tokens:
            if token in alias_to_category:
                # Extract matched category for validation.
                matched_category = alias_to_category[token]
                # Leave the loop after the target condition has been reached.
                break

    budget_label = matched_category or label_text.title()

    source_note = "kategori resmi" if matched_category else "budget custom"
    context.user_data["pending_budget_confirm"] = {
        "category": budget_label,
        "amount": float(amount),
        "month": month,
        "source_note": source_note,
    }

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        "📊 *Preview Set Budget*\n\n"
        f"Kategori: *{md_safe(budget_label)}*\n"
        f"Bulan: *{format_month_label(month)}*\n"
        f"Nominal: *{format_rupiah(amount)} / bulan*\n"
        f"Tipe: {md_safe(source_note)}\n\n"
        "Mau simpan budget ini?",
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("budget"),
    )


# Helper for short debt id.
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
    if len(debt_id) <= 18:
        return debt_id
    return debt_id[:18] + "..."



# Helper for parse debt void args.
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
    # Validate missing args before continuing.
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


# Helper for build debt void preview text.
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
        # Use the fallback path when no earlier branch matched.
        else:
            title = f"⚠️ *Preview Void SEMUA Debt Aktif {person}*\n"

        # Build lines for the response flow.
        lines = [title]
        lines.append(f"👤 Nama: *{person}*")
        lines.append(f"📌 Jumlah rincian: *{len(targets)}*")
        lines.append(f"💰 Total yang akan di-void: *{format_rupiah(total_remaining)}*")

        lines.append("\n*Rincian yang akan di-void:*")
        # Iterate through each i, debt.
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
            # Iterate through each txn.
            for txn in cashflow_txns[:10]:
                txn_desc = md_safe(txn.get("description") or "-")
                txn_date = md_safe(txn.get("date") or "-")
                txn_amount = format_rupiah(float(txn.get("amount", 0) or 0))
                txn_account = md_safe(txn.get("account") or "-")
                lines.append(f"• {txn_date} — {txn_desc} — {txn_amount} | {txn_account}")
            if len(cashflow_txns) > 10:
                lines.append(f"• ...dan {len(cashflow_txns) - 10} cashflow lain")
        # Use the fallback path when no earlier branch matched.
        else:
            lines.append("\n*Cashflow terkait:* tidak ada / tidak perlu dihapus.")
            lines.append("Debt akan di-void tanpa mengubah saldo rekening.")

        if reverse_deltas:
            lines.append("\n*Efek balik ke saldo rekening:*")
            # Iterate through each account, delta.
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
    # Use the fallback path when no earlier branch matched.
    else:
        lines.append("\n*Cashflow terkait:* tidak ada.")
        lines.append("Debt/piutang ini akan divoid tanpa mengubah saldo rekening.")

    if reverse_deltas:
        lines.append("\n*Efek balik ke saldo rekening:*")
        # Iterate through each account, delta.
        for account, delta in reverse_deltas.items():
            # Extract safe account for validation.
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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Validate missing context.args before continuing.
    if not context.args:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Masukkan nomor debt, debt ID, atau nama orang.\n\n"
            "Contoh:\n"
            "`/hutang Maya`\n"
            "`/debt_void 1` — void nomor dari detail terakhir\n"
            "`/debt_void Maya` — void semua debt aktif Maya\n"
            "`/debt_void Maya 1` — void rincian nomor 1 milik Maya\n"
            "`/debt_void debt_20260610_123456_xxx`",
            parse_mode="Markdown",
        )
        return

    parsed = parse_debt_void_args(context.args or [])
    last_debt_map = context.user_data.get("last_debt_map", {})

    if parsed.get("mode") == "person":
        person_name = parsed.get("person_name") or ""
        detail_ref = parsed.get("detail_ref")
        # Build preview for the response flow.
        preview = await run_sheets_read("preview_void_debts_by_person", preview_void_debts_by_person, person_name, detail_ref)
    # Use the fallback path when no earlier branch matched.
    else:
        debt_ref = parsed.get("debt_ref")
        # Build preview for the response flow.
        preview = await run_sheets_read("preview_void_debt", preview_void_debt, debt_ref, last_debt_map)

    if not preview.get("success"):
        lines = [f"❌ *Debt void tidak bisa diproses.*\n{md_safe(preview.get('message'))}"]

        candidates = preview.get("candidate_txns") or []
        if candidates:
            lines.append("\nCashflow kandidat yang ambigu:")
            # Iterate through each txn.
            for txn in candidates[:10]:
                lines.append(
                    f"• Row {txn.get('_row_index', '-')} — {txn.get('date', '-')} — "
                    f"{md_safe(txn.get('description') or '-')} — {format_rupiah(float(txn.get('amount', 0) or 0))}"
                )

        # Send the Telegram response before continuing.
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
    # Use the fallback path when no earlier branch matched.
    else:
        debt = preview.get("debt") or {}
        context.user_data["pending_debt_void"] = {
            "mode": "single",
            "debt_ref": str(debt.get("id") or parsed.get("debt_ref") or "").strip(),
        }

    # Send the Telegram response before continuing.
    await reply_message_safely(
        update.message,
        build_debt_void_preview_text(preview),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("debt_void"),
    )


# Helper for normalize debt edit type.
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


# Helper for parse debt edit args.
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
    if len(args) < 3:
        return None, {}, (
            "Format edit debt belum lengkap.\n\n"
            "Contoh:\n"
            "`/debt_edit 5 nominal 100k`\n"
            "`/debt_edit 5 nama Dimas`\n"
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

    # Normalize normalized field before matching.
    normalized_field = aliases.get(field)
    # Validate missing normalized field before continuing.
    if not normalized_field:
        return debt_ref, {}, (
            "Field edit debt tidak dikenali.\n"
            "Field yang bisa diedit: `nominal`, `nama`, `tipe`, `deskripsi`, `jatuh_tempo`."
        )

    # Extract updates for validation.
    updates = {}
    if normalized_field == "amount":
        # Extract amount for validation.
        amount = parse_amount_text(value)
        # Validate missing amount or amount <= 0 before continuing.
        if not amount or amount <= 0:
            return debt_ref, {}, "Nominal tidak valid. Contoh: `/debt_edit 5 nominal 100k`"
        updates["amount"] = amount
    elif normalized_field == "type":
        debt_type = normalize_debt_edit_type(value)
        # Validate missing debt type before continuing.
        if not debt_type:
            return debt_ref, {}, "Tipe tidak valid. Gunakan `utang/payable` atau `piutang/receivable`."
        updates["type"] = debt_type
    elif normalized_field == "due_date":
        detected = detect_date(value)
        updates["due_date"] = detected or value
    elif normalized_field == "person_name":
        # Validate missing value before continuing.
        if not value:
            return debt_ref, {}, "Nama orang tidak boleh kosong."
        updates["person_name"] = value
    elif normalized_field == "description":
        updates["description"] = value

    return debt_ref, updates, None


# Helper for build debt edit result text.
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
    if due_date:
        lines.append(f"📅 Jatuh tempo: `{md_safe(due_date)}`")

    if changed:
        lines.append("\nField yang berubah:")
        # Iterate through each field, diff.
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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    debt_ref, updates, error = parse_debt_edit_args(context.args or [])
    if error:
        await update.message.reply_text(f"❌ {error}", parse_mode="Markdown")
        return

    last_debt_map = context.user_data.get("last_debt_map", {})
    # Build result for the response flow.
    result = update_debt(debt_ref, updates, last_debt_map)
    if not result.get("success"):
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"❌ *Debt gagal diedit.*\n{md_safe(result.get('message'))}",
            parse_mode="Markdown",
        )
        return

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_debt_edit_result_text(result),
        parse_mode="Markdown",
    )


# Helper for format debt created date for display.
def format_debt_created_date_for_display(debt: dict) -> str:
    """Format debt created_at safely, including Google Sheets date serials."""
    raw = normalize_sheet_date_for_display((debt or {}).get("created_at", ""))
    return raw or "Tanpa tanggal"


# Helper for debt detail sort key for display.
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
    # Extract created date for validation.
    created_date = format_debt_created_date_for_display(debt)
    debt_id = str((debt or {}).get("id", "") or "").strip()
    # Run this operation in a guarded block so failures can be handled.
    try:
        row_index = int((debt or {}).get("_row_index", 0) or 0)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        row_index = 0
    return (created_date, debt_id, row_index)





# Helper for parse debt number selection.
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
    # Validate missing raw before continuing.
    if not raw:
        return []
    numbers: list[int] = []
    for token in re.split(r"[,\s]+", raw):
        token = token.strip()
        # Validate missing token before continuing.
        if not token:
            # Skip the rest of this loop iteration after handling this case.
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", token)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            # Handle start <= 0 or end <= 0.
            if start <= 0 or end <= 0:
                # Skip the rest of this loop iteration after handling this case.
                continue
            step = 1 if end >= start else -1
            # Append the current value to numbers.
            numbers.extend(range(start, end + step, step))
            # Skip the rest of this loop iteration after handling this case.
            continue
        if token.isdigit():
            n = int(token)
            if n > 0:
                # Append the current value to numbers.
                numbers.append(n)
    seen = set()
    ordered = []
    # Iterate through each n.
    for n in numbers:
        if n not in seen:
            # Append the current value to seen.
            seen.add(n)
            # Append the current value to ordered.
            ordered.append(str(n))
    return ordered


# Helper for parse debt settle command args.
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
    result = {
        "person_name": "",
        "selection": "",
        "numbers": [],
        "amount": None,
        "account": "",
        "scope": "",
        "error": "",
    }
    if len(args) < 1:
        result["error"] = (
            "Format: `/debt_settle Nama` atau `/debt_settle Nama 1-3`\n"
            "Opsional: `amount=337063 account=DANA`"
        )
        return result

    amount_raw = ""
    account = ""
    positional = []
    i = 0
    # Repeat this block while i < len(args).
    while i < len(args):
        token = args[i]
        low = token.lower()
        if low.startswith("amount=") or low.startswith("nominal="):
            amount_raw = token.split("=", 1)[1]
        elif low in {"amount", "nominal"} and i + 1 < len(args):
            i += 1
            # Extract amount raw for validation.
            amount_raw = args[i]
        elif low.startswith("account=") or low.startswith("rekening=") or low.startswith("akun="):
            account = token.split("=", 1)[1]
        elif low in {"account", "rekening", "akun", "dari", "ke"} and i + 1 < len(args):
            i += 1
            # Extract account for validation.
            account = args[i]
        # Use the fallback path when no earlier branch matched.
        else:
            # Append the current value to positional.
            positional.append(token)
        i += 1

    # Number selection is optional; without it the command targets all active debt for the person.
    selection_idx = None
    # Iterate through each idx, token.
    for idx, token in enumerate(positional):
        if re.fullmatch(r"\d+(?:-\d+)?(?:[,\s]+\d+(?:-\d+)?)*", token):
            selection_idx = idx
            # Leave the loop after the target condition has been reached.
            break
    if selection_idx is None:
        # Extract person parts for validation.
        person_parts = positional
        selection = ""
    # Use the fallback path when no earlier branch matched.
    else:
        # Extract person parts for validation.
        person_parts = positional[:selection_idx]
        selection = " ".join(positional[selection_idx:]).strip()

    # Validate missing person parts before continuing.
    if not person_parts:
        result["error"] = "Nama debt belum lengkap. Contoh: `/debt_settle Raka` atau `/debt_settle Raka 1-3`."
        return result

    # Extract amount for validation.
    amount = None
    if amount_raw:
        # Extract amount for validation.
        amount = parse_human_amount(amount_raw)
        if amount <= 0:
            result["error"] = "Nominal tidak valid. Contoh: `amount=337063`."
            return result

    numbers = []
    if selection:
        numbers = parse_debt_number_selection(selection)
        # Validate missing numbers before continuing.
        if not numbers:
            result["error"] = "Nomor/range debt tidak valid. Contoh: `1-17` atau `1 3 5`."
            return result

    result.update({
        "person_name": normalize_person_name(" ".join(person_parts)),
        "selection": selection,
        "numbers": numbers,
        "amount": amount,
        "account": account.strip(),
        "scope": "selected" if numbers else "person_all",
    })
    return result


# Helper for parse natural debt settle text.
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
    # Validate missing raw before continuing.
    if not raw:
        return None
    pattern = re.compile(
        r"^(?P<person>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s.'-]{0,60}?)\s+"
        r"bayar\s+(?:h?utang|utang)\s+"
        r"(?P<amount>\d[\d.,]*(?:\s*(?:k|rb|ribu|jt|juta))?)\s+"
        r"(?:untuk|buat)\s+(?:debt|hutang|piutang)\s+"
        r"(?P<selection>\d+(?:\s*-\s*\d+)?(?:[,\s]+\d+(?:\s*-\s*\d+)?)*)"
        r"(?:\s+(?:dari|ke|account=|rekening=|akun=)\s*(?P<account>[A-Za-z0-9 _-]+))?\s*$",
        re.IGNORECASE,
    )
    m = pattern.match(raw)
    # Validate missing m before continuing.
    if not m:
        return None
    amount = parse_human_amount(m.group("amount"))
    numbers = parse_debt_number_selection(m.group("selection"))
    if amount <= 0 or not numbers:
        return None
    return {
        "person_name": normalize_person_name(m.group("person")),
        "selection": m.group("selection").strip(),
        "numbers": numbers,
        "amount": amount,
        "account": (m.group("account") or "").strip(),
        "raw": raw,
        "source": "natural",
    }


# Helper for resolve selected debts from last detail.
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
    # Extract person for validation.
    person = normalize_person_name(person_name)
    last_person = normalize_person_name(context.user_data.get("last_debt_person", ""))
    last_map = context.user_data.get("last_debt_map") or {}
    # Validate missing last map or not last person before continuing.
    if not last_map or not last_person:
        return {
            "success": False,
            "message": f"Jalankan `/hutang {md_safe(person)}` dulu, baru pakai nomor debt dari output itu.",
        }
    if last_person != person:
        return {
            "success": False,
            "message": (
                f"Nomor debt terakhir berasal dari `/hutang {md_safe(last_person)}`, "
                f"bukan `/hutang {md_safe(person)}`. Jalankan `/hutang {md_safe(person)}` dulu."
            ),
        }

    selected = []
    debt_ids = []
    missing = []
    # Iterate through each n.
    for n in numbers:
        mapped = last_map.get(str(n))
        if not mapped or not mapped.get("debt_id"):
            # Append the current value to missing.
            missing.append(str(n))
            # Skip the rest of this loop iteration after handling this case.
            continue
        debt_id = str(mapped.get("debt_id") or "").strip()
        row, debt = get_debt_by_id_any_status(debt_id)
        # Validate missing debt before continuing.
        if not debt:
            # Append the current value to missing.
            missing.append(str(n))
            # Skip the rest of this loop iteration after handling this case.
            continue
        if normalize_person_name(debt.get("person_name", "")) != person:
            return {
                "success": False,
                "message": f"Debt nomor {n} bukan milik {md_safe(person)}. Jalankan ulang `/hutang {md_safe(person)}`.",
            }
        if is_voided_debt(debt):
            return {"success": False, "message": f"Debt nomor {n} sudah void, tidak bisa disettle."}
        remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        if remaining <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        debt = dict(debt)
        debt["_row_index"] = row
        debt["_display_no"] = str(n)
        # Append the current value to selected.
        selected.append(debt)
        # Append the current value to debt ids.
        debt_ids.append(debt_id)

    if missing:
        return {
            "success": False,
            "message": "Nomor debt tidak ditemukan di output /hutang terakhir: " + ", ".join(missing),
        }
    # Validate missing selected before continuing.
    if not selected:
        return {"success": False, "message": "Debt terpilih sudah tidak aktif/lunas."}

    # Build summary for the response flow.
    summary = summarize_debt_rows_for_settlement(selected)
    return {
        "success": True,
        "person_name": person,
        "selected": selected,
        "debt_ids": debt_ids,
        "summary": summary,
    }


# Helper for resolve all active debts for person.
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
    # Extract person for validation.
    person = normalize_person_name(person_name)
    # Validate missing person before continuing.
    if not person:
        return {"success": False, "message": "Nama debt belum lengkap."}

    selected = []
    debt_ids = []
    # Iterate through each debt.
    for debt in get_debt_by_person(person):
        if is_voided_debt(debt):
            # Skip the rest of this loop iteration after handling this case.
            continue
        remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        debt_id = str(debt.get("id") or "").strip()
        # Handle remaining <= 0 or not debt id.
        if remaining <= 0 or not debt_id:
            # Skip the rest of this loop iteration after handling this case.
            continue
        item = dict(debt)
        item["remaining_amount"] = remaining
        # Append the current value to selected.
        selected.append(item)
        # Append the current value to debt ids.
        debt_ids.append(debt_id)

    # Validate missing selected before continuing.
    if not selected:
        return {"success": False, "message": f"Tidak ada debt aktif dengan {md_safe(person)}."}

    # Build summary for the response flow.
    summary = summarize_debt_rows_for_settlement(selected)
    return {
        "success": True,
        "person_name": person,
        "selected": selected,
        "debt_ids": debt_ids,
        "summary": summary,
    }


# Helper for build selected debt total text.
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
    lines = [
        "🧮 *Total Debt Terpilih*\n",
        f"👤 Subjek: *{md_safe(person)}*",
        f"📌 Nomor dari `/hutang {md_safe(person)}`: *{md_safe(selection)}*",
        f"🟢 Piutang Anda: *{format_rupiah(summary.get('total_receivable', 0))}*",
        f"🔴 Utang Anda: *{format_rupiah(summary.get('total_payable', 0))}*",
    ]
    net = float(summary.get("net_amount", 0) or 0)
    if net > 0:
        lines.append(f"📊 Net: *{md_safe(person)} harus bayar Anda {format_rupiah(net)}*")
    # Fall back when net < 0.
    elif net < 0:
        lines.append(f"📊 Net: *Anda harus bayar {md_safe(person)} {format_rupiah(abs(net))}*")
    # Use the fallback path when no earlier branch matched.
    else:
        lines.append("📊 Net: *impas / tidak perlu cashflow*")
    lines.append(
        "\nUntuk settle dari range ini:\n"
        f"`/debt_settle {md_safe(person)} {md_safe(selection)} amount={summary.get('net_abs', 0)} account=DANA`"
    )
    return "\n".join(lines)


# Helper for build selected debt settle preview text.
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
    lines = [
        "🧾 *Preview Settle Debt Terpilih*\n",
        f"👤 Subjek: *{md_safe(person)}*",
        f"📌 Rincian dipilih: *{md_safe(selection)}*",
        f"🟢 Piutang Anda: *{format_rupiah(summary.get('total_receivable', 0))}*",
        f"🔴 Utang Anda: *{format_rupiah(summary.get('total_payable', 0))}*",
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
    # Use the fallback path when no earlier branch matched.
    else:
        lines.append("📊 Net: *impas / tidak perlu cashflow*")
        lines.append("💰 Cashflow: *tidak ada transaksi saldo rekening*")

    if shortage > 0:
        lines.append(
            f"\n❌ *Nominal kurang {format_rupiah(shortage)}.* "
            "Karena ini `/debt_settle`, debt terpilih hanya bisa ditutup kalau nominal minimal sama dengan net terpilih."
        )
        return "\n".join(lines)

    if overpayment > 0:
        lines.append(
            f"\n⚠️ *Pembayaran melebihi net debt terpilih sebesar {format_rupiah(overpayment)}.*"
        )
        policy = str(payload.get("overpayment_policy") or "").strip()
        if policy == "bonus":
            lines.append("ℹ️ Kelebihan akan dianggap lunas/bonus, tidak jadi hutang baru.")
        elif policy == "opposite_debt":
            if net_type == "receivable":
                lines.append(f"ℹ️ Kelebihan akan dicatat sebagai utang Anda ke {md_safe(person)}.")
            # Use the fallback path when no earlier branch matched.
            else:
                lines.append(f"ℹ️ Kelebihan akan dicatat sebagai piutang Anda ke {md_safe(person)}.")
        # Use the fallback path when no earlier branch matched.
        else:
            lines.append(
                "Pilih perlakuan untuk uang lebihnya:\n"
                "1. *Anggap lunas/bonus*\n"
                "2. *Catat sebagai hutang lawan arah*"
            )
            return "\n".join(lines)

    lines.append("\nEfek jika disimpan:")
    if payload.get("scope") == "person_all":
        lines.append("✅ Semua debt aktif untuk subjek ini disettle")
    # Use the fallback path when no earlier branch matched.
    else:
        lines.append("✅ Hanya debt nomor terpilih yang disettle")
        lines.append("✅ Debt lain di luar range/list tidak disentuh")
    if float(payload.get("amount", 0) or 0) > 0:
        lines.append("✅ Cashflow tersimpan di transactions")
        lines.append("✅ Relasi debt disimpan supaya `/delete_txn` bisa membuka lagi debt terpilih")
    # Use the fallback path when no earlier branch matched.
    else:
        lines.append("✅ Tidak ada transaksi saldo rekening karena net impas")
    lines.append("\nSimpan settlement ini?")
    return "\n".join(lines)


# Helper for build selected settle catatan.
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
    allocs = []
    for item in result.get("settled") or result.get("allocations") or []:
        debt_id = str(item.get("debt_id") or "").strip()
        amount = item.get("amount")
        # Store allocation notes only when both debt id and amount are present.
        if debt_id and amount is not None:
            allocs.append(f"{debt_id}:{float(amount)}")
    if allocs:
        parts.append("debt_allocations=" + ";".join(allocs))
    overpayment = float(result.get("overpayment", 0) or 0)
    if overpayment > 0:
        parts.append(f"overpayment={overpayment}")
        policy = result.get("overpayment_policy") or payload.get("overpayment_policy") or ""
        if policy:
            parts.append(f"overpayment_policy={policy}")
        created = result.get("overpayment_created") or {}
        if created.get("debt_id"):
            parts.append(f"overpayment_debt_id={created.get('debt_id')}")
    return " | ".join([p for p in parts if p]).strip(" |")


# Helper for prepare selected debt settle payload.
async def prepare_selected_debt_settle_payload(context: ContextTypes.DEFAULT_TYPE, parsed: dict) -> dict:
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
        resolved = resolve_selected_debts_from_last_detail(
            context,
            parsed.get("person_name", ""),
            parsed.get("numbers") or [],
        )
    # Use the fallback path when no earlier branch matched.
    else:
        resolved = await run_sheets_read(
            "resolve_all_active_debts_for_person",
            resolve_all_active_debts_for_person,
            parsed.get("person_name", ""),
        )
    if not resolved.get("success"):
        return {"success": False, "message": resolved.get("message", "Gagal resolve debt terpilih.")}
    summary = resolved.get("summary") or {}
    manual_amount = parsed.get("amount")
    # Extract amount for validation.
    amount = manual_amount
    # Extract amount auto for validation.
    amount_auto = amount is None
    if amount_auto:
        amount = float(summary.get("net_abs", 0) or 0)
    selection = parsed.get("selection") or ("semua debt aktif" if scope == "person_all" else ", ".join(parsed.get("numbers") or []))
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
    }
    required = float(summary.get("net_abs", 0) or 0)
    payload["overpayment"] = max(0.0, float(amount or 0) - required)
    payload["shortage"] = max(0.0, required - float(amount or 0))
    return payload


# Helper for selected debt settle overpay keyboard.
def selected_debt_settle_overpay_keyboard() -> InlineKeyboardMarkup:
    """Build the overpayment decision keyboard for selected debt settlement.

    Returns:
        Inline keyboard with bonus, opposite-debt, and Batal choices.

    Flow constraints:
        Used only when manual amount exceeds selected net debt. It does not
        write data; the choice updates pending settlement state.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Anggap lunas / bonus", callback_data="debt_settle_overpay:bonus")],
        [InlineKeyboardButton("🔴 Catat sebagai hutang lawan arah", callback_data="debt_settle_overpay:opposite_debt")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:debt_settle")],
    ])


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    parsed = parse_debt_settle_command_args(context.args or [])
    if parsed.get("error"):
        await update.message.reply_text(f"❌ {parsed['error']}", parse_mode="Markdown")
        return

    # Build payload for the response flow.
    payload = await prepare_selected_debt_settle_payload(context, parsed)
    if not payload.get("success"):
        await update.message.reply_text(f"❌ {payload.get('message')}", parse_mode="Markdown")
        return

    if float(payload.get("shortage", 0) or 0) > 0:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_selected_debt_settle_preview_text(payload),
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )
        return

    if float(payload.get("amount", 0) or 0) > 0 and not payload.get("account"):
        context.user_data["pending_debt_settle"] = payload
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_selected_debt_settle_preview_text(payload) + "\n\nPilih rekening cashflow:",
            parse_mode="Markdown",
            reply_markup=account_keyboard("debt_settle_acc", include_skip=False),
        )
        return

    context.user_data["pending_debt_settle"] = payload
    if float(payload.get("overpayment", 0) or 0) > 0 and not payload.get("overpayment_policy"):
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_selected_debt_settle_preview_text(payload),
            parse_mode="Markdown",
            reply_markup=selected_debt_settle_overpay_keyboard(),
        )
        return

    # Send the Telegram response before continuing.
    await reply_message_safely(
        update.message,
        build_selected_debt_settle_preview_text(payload),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("debt_settle"),
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
    parsed = parse_natural_debt_settle_text(text)
    # Validate missing parsed before continuing.
    if not parsed:
        return False

    # Build payload for the response flow.
    payload = await prepare_selected_debt_settle_payload(context, parsed)
    if not payload.get("success"):
        await update.message.reply_text(f"❌ {payload.get('message')}", parse_mode="Markdown")
        return True

    if float(payload.get("shortage", 0) or 0) > 0:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_selected_debt_settle_preview_text(payload),
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )
        return True

    if float(payload.get("amount", 0) or 0) > 0 and not payload.get("account"):
        context.user_data["pending_debt_settle"] = payload
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_selected_debt_settle_preview_text(payload) + "\n\nPilih rekening cashflow:",
            parse_mode="Markdown",
            reply_markup=account_keyboard("debt_settle_acc", include_skip=False),
        )
        return True

    context.user_data["pending_debt_settle"] = payload
    if float(payload.get("overpayment", 0) or 0) > 0 and not payload.get("overpayment_policy"):
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_selected_debt_settle_preview_text(payload),
            parse_mode="Markdown",
            reply_markup=selected_debt_settle_overpay_keyboard(),
        )
        return True

    # Send the Telegram response before continuing.
    await reply_message_safely(
        update.message,
        build_selected_debt_settle_preview_text(payload),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("debt_settle"),
    )
    return True


# Helper for build selected debt settle transaction.
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
    # Use the fallback path when no earlier branch matched.
    else:
        txn_type = "income"
        category = "Pembayaran Piutang"
        tipe_hutang = "piutang"
        desc = f"Pembayaran piutang terpilih dari {person}"
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
        "date": business_now().strftime("%Y-%m-%d"),
        "hutang_id": ", ".join([x for x in affected_ids if x]),
        "tipe_hutang": tipe_hutang,
        "parsed_by": "debt_settle",
    }



# Helper for collect known debt person names.
async def _collect_known_debt_person_names() -> list[str]:
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
    names = []
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Build summary for the response flow.
        summary = await run_sheets_read("get_debt_person_summary", get_debt_person_summary) or {}
        for key in ("payables", "receivables", "balanced"):
            # Iterate through each item.
            for item in summary.get(key) or []:
                name = str(item.get("person_name") or "").strip()
                if name and name not in names:
                    # Append the current value to names.
                    names.append(name)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass
    return names


# Helper for strip trailing known names for summary.
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
    # Validate missing clean or not known names before continuing.
    if not clean or not known_names:
        return clean

    ordered = sorted(
        [str(name or "").strip() for name in known_names if str(name or "").strip()],
        key=len,
        reverse=True,
    )

    changed = True
    # Repeat this block while changed and clean.
    while changed and clean:
        changed = False
        new_clean = re.sub(r"\b(?:sama|ama|dengan|bareng|dan)\s*$", "", clean, flags=re.IGNORECASE).strip(" .,-")
        if new_clean != clean:
            # Normalize clean before matching.
            clean = new_clean
            changed = True

        # Iterate through each name.
        for name in ordered:
            pattern = rf"(?:^|[\s,;&]+){re.escape(name)}\s*$"
            new_clean = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip(" .,-")
            if new_clean != clean:
                # Normalize clean before matching.
                clean = new_clean
                changed = True
                # Leave the loop after the target condition has been reached.
                break

    return clean


# Helper for clean debt description for share.
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
    # Validate missing raw before continuing.
    if not raw:
        return "-"

    person_text = str(person or "").strip()
    known_names = known_names or []

    # Implementation note for this project-specific finance flow.
    # Implementation note for this project-specific finance flow.
    if person_text:
        m = re.match(rf"^\s*Ditalangin\s+(.+?)\s*:\s*(?:ke|kepada)\s+{re.escape(person_text)}\s*$", raw, flags=re.IGNORECASE)
        if m:
            # Prepare raw from the incoming input.
            raw = m.group(1).strip()
        # Use the fallback path when no earlier branch matched.
        else:
            m = re.match(rf"^\s*Ditalangin\s+{re.escape(person_text)}\s*:\s*(.+?)\s*$", raw, flags=re.IGNORECASE)
            if m:
                # Prepare raw from the incoming input.
                raw = m.group(1).strip()

    raw = re.sub(r"^\s*Split\s*bill(?:\s+ditalangin\s+[^:]+)?\s*:\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^\s*Ditalangin\s+[^:]+\s*:\s*", "", raw, flags=re.IGNORECASE)

    # Implementation note for this project-specific finance flow.
    raw = re.sub(r"\b(?:di\s*-?\s*bagi|dibagi|bagi|split|share|patungan)\b.*$", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\b(?:ke|kepada)\s+" + re.escape(person_text) + r"\s*$", "", raw, flags=re.IGNORECASE) if person_text else raw
    # Prepare raw from the incoming input.
    raw = _strip_trailing_known_names_for_summary(raw, known_names + ([person_text] if person_text else []))

    raw = re.sub(r"\s+", " ", raw).strip(" .,-:")
    return raw or str(desc or "-").strip() or "-"


# Helper for format shareable date heading.
def _format_shareable_date_heading(date_value) -> str:
    """Format data into a readable display for shareable date heading."""
    label = format_indonesian_date_group_label(date_value)
    return label.rstrip(":")


# Helper for group debts for shareable summary.
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
    # Validate missing debts before continuing.
    if not debts:
        return ["Tidak ada rincian aktif."]

    # Build lines for the response flow.
    lines = []
    # Extract current date for validation.
    current_date = None
    item_no = 1
    # Iterate through each debt.
    for debt in sorted(debts or [], key=debt_detail_sort_key_for_display, reverse=True):
        # Extract created date for validation.
        created_date = format_debt_created_date_for_display(debt)
        if created_date != current_date:
            if lines:
                lines.append("")
            lines.append(f"*{md_safe(_format_shareable_date_heading(created_date))}*")
            # Extract current date for validation.
            current_date = created_date

        desc = _clean_debt_description_for_share(debt.get("description"), person, known_names)
        amount = parse_sheet_number(debt.get("remaining_amount", 0))
        lines.append(f"{item_no}. {md_safe(desc)} - *{format_rupiah(amount)}*")
        item_no += 1

    return lines


# Helper for build shareable debt summary text.
async def build_shareable_debt_summary_text(person_query: str) -> str:
    """Build the data structure or message text for shareable debt summary text."""
    detail = await run_sheets_read("get_debt_person_detail", get_debt_person_detail, person_query, include_settled=True)
    person = detail.get("person_name") or str(person_query or "").strip().title()
    active_details = detail.get("active_details") or []

    # Validate missing active details before continuing.
    if not active_details:
        return f"✅ Tidak ada hutang-piutang aktif dengan *{md_safe(person)}*."

    receivable_details = [
        d for d in active_details
        if str(d.get("type") or "").strip().lower() == "receivable"
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
    ]
    payable_details = [
        d for d in active_details
        if str(d.get("type") or "").strip().lower() == "payable"
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
    ]

    total_receivable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in receivable_details)
    total_payable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in payable_details)
    net = total_receivable - total_payable

    known_names = await _collect_known_debt_person_names()

    lines = [
        f"📌 *Rekap Hutang-Piutang Denan & {md_safe(person)}*",
        "",
        f"🟢 {md_safe(person)} ke Denan: *{format_rupiah(total_receivable)}*",
        f"🔴 Denan ke {md_safe(person)}: *{format_rupiah(total_payable)}*",
        "",
        "💰 *Total akhir:*",
    ]

    if net > 0:
        lines.append(f"{md_safe(person)} bayar ke Denan *{format_rupiah(net)}*")
    # Fall back when net < 0.
    elif net < 0:
        lines.append(f"Denan bayar ke {md_safe(person)} *{format_rupiah(abs(net))}*")
    # Use the fallback path when no earlier branch matched.
    else:
        lines.append("Sudah impas / netral")

    lines.extend([
        "",
        "",
        f"*Rincian {md_safe(person)} ke Denan:*",
        "",
    ])
    # Append the current value to lines.
    lines.extend(_group_debts_for_shareable_summary(receivable_details, person, known_names))
    lines.extend([
        "",
        f"📊 *Subtotal {md_safe(person)} ke Denan: {format_rupiah(total_receivable)}*",
        "",
        "",
        f"*Rincian Denan ke {md_safe(person)}:*",
        "",
    ])
    # Append the current value to lines.
    lines.extend(_group_debts_for_shareable_summary(payable_details, person, known_names))
    lines.extend([
        "",
        f"📊 *Subtotal Denan ke {md_safe(person)}: {format_rupiah(total_payable)}*",
        "",
        "",
        "🎯 *Jadi total akhirnya:*",
    ])

    if net > 0:
        lines.append(f"✅ {md_safe(person)} bayar ke Denan *{format_rupiah(net)}*")
    # Fall back when net < 0.
    elif net < 0:
        lines.append(f"✅ Denan bayar ke {md_safe(person)} *{format_rupiah(abs(net))}*")
    # Use the fallback path when no earlier branch matched.
    else:
        lines.append("✅ Sudah impas / netral")

    return "\n".join(lines)


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    person_query = " ".join(getattr(context, "args", []) or []).strip()
    # Validate missing person query before continuing.
    if not person_query:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "Format: `/ringkasan_hutang Nama`\nContoh: `/ringkasan_hutang Raka`",
            parse_mode="Markdown",
        )
        return

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        await build_shareable_debt_summary_text(person_query),
        parse_mode="Markdown",
    )

def _build_debt_overview_text(summary: dict) -> str:
    """Preserve the pre-browser aggregate meaning of bare `/hutang`."""
    lines = ["💸 *Utang & Piutang Aktif per Orang*\n"]
    if summary.get("payables"):
        lines.append(f"🔴 *Utang Anda* (net total: {format_rupiah(summary.get('total_payable', 0))})")
        for i, item in enumerate(summary.get("payables") or [], 1):
            person = item.get("person_name") or "-"
            count = int(item.get("debt_count") or 0)
            lines.append(
                f"  {i}. {md_safe(person)} — *{format_rupiah(item.get('remaining_amount', 0))}* "
                f"({count} rincian)"
            )
    if summary.get("payables") and summary.get("receivables"):
        lines.append("")
    if summary.get("receivables"):
        lines.append(f"🟢 *Piutang Anda* (net total: {format_rupiah(summary.get('total_receivable', 0))})")
        for i, item in enumerate(summary.get("receivables") or [], 1):
            person = item.get("person_name") or "-"
            count = int(item.get("debt_count") or 0)
            lines.append(
                f"  {i}. {md_safe(person)} — *{format_rupiah(item.get('remaining_amount', 0))}* "
                f"({count} rincian)"
            )
    if summary.get("balanced"):
        lines.append("\n⚪ *Netral tapi masih ada rincian aktif*")
        for item in summary.get("balanced") or []:
            lines.append(f"  • {md_safe(item.get('person_name') or '-')}")
    net = float(summary.get("total_receivable", 0) or 0) - float(summary.get("total_payable", 0) or 0)
    net_label = "🟢 Anda lebih banyak dihutangi" if net >= 0 else "🔴 Anda lebih banyak berhutang"
    lines.append(f"\n{net_label}: *{format_rupiah(abs(net))}*")
    lines.append("\nPilih rincian pada browser debt di bawah untuk Settle / Edit / Void.")
    return "\n".join(lines)


def _active_debts_from_person_summary(summary: dict) -> list[dict]:
    """Reuse the rows already loaded for aggregate summary; do not reread Debts."""
    rows: list[dict] = []
    seen: set[str] = set()
    for group_name in ("payables", "receivables", "balanced"):
        for group in summary.get(group_name) or []:
            for debt in group.get("details") or []:
                debt_id = str((debt or {}).get("id") or "").strip()
                if debt_id and debt_id not in seen:
                    rows.append(debt)
                    seen.add(debt_id)
    return sorted(rows, key=debt_detail_sort_key_for_display, reverse=True)


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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    args = getattr(context, "args", []) or []
    person_query = " ".join(args).strip()

    if person_query:
        detail = await run_sheets_read(
            "get_debt_person_detail",
            get_debt_person_detail,
            person_query,
            include_settled=True,
        )
        active_details = sorted(
            detail.get("active_details") or [],
            key=debt_detail_sort_key_for_display,
            reverse=True,
        )
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

        context.user_data["last_debt_map"] = {
            str(i): {
                "debt_id": debt.get("id"),
                "row_index": debt.get("_row_index"),
                "person_name": person,
                "type": debt.get("type"),
                "remaining_amount": debt.get("remaining_amount"),
            }
            for i, debt in enumerate(active_details, 1)
        }
        context.user_data["last_debt_person"] = person

        if active_details:
            await start_debt_browser(
                update,
                context,
                active_details,
                title=f"Utang & Piutang — {person}",
                overview=header,
            )
            return

        # Preserve historical/progress meaning when the person has debt history
        # but no active row that can be selected for a mutation.
        lines = [header, "", "Tidak ada rincian aktif."]
        recv = detail.get("receivable") or {}
        pay = detail.get("payable") or {}
        if float(recv.get("original") or 0) > 0:
            lines.append(
                "\n*Progress piutang:*\n"
                f"Sudah bayar: *{format_rupiah(recv.get('paid', 0))}* / {format_rupiah(recv.get('original', 0))} "
                f"({float(recv.get('paid_pct') or 0):.1f}%)"
            )
        if float(pay.get("original") or 0) > 0:
            lines.append(
                "\n*Progress utang Anda:*\n"
                f"Sudah dibayar: *{format_rupiah(pay.get('paid', 0))}* / {format_rupiah(pay.get('original', 0))} "
                f"({float(pay.get('paid_pct') or 0):.1f}%)"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    summary = await run_sheets_read("get_debt_person_summary", get_debt_person_summary)
    if not summary.get("payables") and not summary.get("receivables") and not summary.get("balanced"):
        await update.message.reply_text("✅ Tidak ada utang atau piutang aktif.")
        return

    active_debts = _active_debts_from_person_summary(summary)
    context.user_data["last_debt_map"] = {}
    context.user_data.pop("last_debt_person", None)
    await update.message.reply_text(_build_debt_overview_text(summary), parse_mode="Markdown")
    await start_debt_browser(update, context, active_debts)


# Message handling section
