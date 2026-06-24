# Split from app/bot/handlers.py for readability.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *
from app.bot.handler_parts.common_imports import _safe_float_for_display

from app.bot.handler_parts.networth_assets import (
    build_asset_confirm_preview,
    build_asset_unit_price_prompt,
    handle_pending_asset_add_flow,
    parse_natural_asset_add,
)
from app.bot.handler_parts.command_router import (
    build_delete_preview_text,
    build_gemini_fallback_text,
    build_gemini_low_confidence_text,
    build_last_transactions_text,
    extract_edit_updates_from_router,
    maybe_text_is_command_typo,
    resolve_txn_refs_from_last,
    router_args_to_last_filter,
)
from app.bot.handler_parts.transaction_flow import (
    attach_split_bill_if_any,
    build_debt_account_prompt,
    build_debt_only_confirm_preview,
    build_missing_amount_prompt,
    build_mixed_preview,
    build_mixed_split_bill_queue_prompt,
    build_preview,
    build_split_bill_prompt_from_parsed,
    debt_uses_cashflow,
    edit_or_continue_keyboard,
    handle_pending_missing_amount,
    handle_pending_preview_edit,
    mixed_needs_account,
    mixed_split_bill_keyboard,
    mixed_split_bill_needs_decision,
    needs_account,
    parse_income_missing_amount,
    parse_input,
    parse_mixed_item,
    split_bill_keyboard,
    split_bill_needs_decision,
    split_user_inputs,
)
from app.bot.handler_parts.command_handlers import (
    budget_history_handler,
    bulanan_handler,
    handle_natural_finance_question,
    harian_handler,
    help_handler,
    hutang_handler,
    mingguan_handler,
    saldo_handler,
)

async def debt_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle input debt dari pesan bebas.

    Debt tidak langsung diproses.
    Bot akan tanya rekening dulu supaya aktivitas debt juga masuk transactions
    dan saldo rekening ikut berubah.
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return True

    text = update.message.text.strip()
    debt_parsed = parse_debt_input(text)

    if not debt_parsed:
        return False

    person = debt_parsed.get("person_name")
    intent = debt_parsed.get("intent")

    if not person:
        if intent == "add_payable":
            await update.message.reply_text(
                "❓ Siapa yang Anda hutangi?\n"
                "Contoh: `hutang ke Budi 500rb buat makan`",
                parse_mode="Markdown",
            )
            return True

        if intent == "add_receivable":
            await update.message.reply_text(
                "❓ Siapa yang meminjam uang ke Anda?\n"
                "Contoh: `Budi minjem 300rb`",
                parse_mode="Markdown",
            )
            return True

        if intent == "add_payment":
            await update.message.reply_text(
                "❓ Pembayaran ini terkait siapa?\n"
                "Contoh: `Budi bayar 300rb` atau `bayar hutang Budi 300rb`",
                parse_mode="Markdown",
            )
            return True

    context.user_data["pending_debt"] = debt_parsed
    context.user_data.pop("pending_parsed", None)
    context.user_data.pop("pending_raw", None)
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt_batch", None)

    if intent == "offset_debt" or not debt_uses_cashflow(debt_parsed):
        await update.message.reply_text(
            build_debt_only_confirm_preview(debt_parsed),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("debt"),
        )
        return True

    await update.message.reply_text(
        build_debt_account_prompt(debt_parsed),
        parse_mode="Markdown",
        reply_markup=account_keyboard("debt_acc"),
    )

    return True

async def handle_gemini_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """
    Jalankan hasil Gemini intent router.

    Return:
    - True jika sudah di-handle
    - False jika harus lanjut fallback biasa

    Safety:
    - delete/edit tetap preview dan butuh tombol Simpan.
    - confidence rendah tidak dieksekusi.
    """
    if not should_try_gemini_intent_router(user_text):
        return False

    router_result = route_intent_with_gemini(user_text)

    intent = router_result.get("intent", "unknown")
    confidence = float(router_result.get("confidence", 0) or 0)
    args = router_result.get("args", {}) or {}

    if confidence < GEMINI_INTENT_CONFIDENCE_CLARIFY:
        return False

    if confidence < GEMINI_INTENT_CONFIDENCE_EXECUTE:
        await update.message.reply_text(
            build_gemini_low_confidence_text(router_result),
            parse_mode="Markdown",
        )
        return True

    # ── Non-destructive intents ───────────────────────────────────────────────

    if intent == "help":
        await help_handler(update, context)
        return True

    if intent == "saldo":
        await saldo_handler(update, context)
        return True

    if intent == "harian":
        await harian_handler(update, context)
        return True

    if intent == "mingguan":
        await mingguan_handler(update, context)
        return True

    if intent == "bulanan":
        await bulanan_handler(update, context)
        return True

    if intent == "hutang":
        await hutang_handler(update, context)
        return True

    if intent == "budget_history":
        await budget_history_handler(update, context)
        return True

    if intent == "last":
        limit, period, month, title = router_args_to_last_filter(args)

        transactions = get_recent_transactions(
            limit=limit,
            period=period,
            month=month,
        )

        if not transactions:
            await update.message.reply_text(
                f"📭 Tidak ada transaksi untuk filter: *{title}*",
                parse_mode="Markdown",
            )
            return True

        last_map = {}

        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, title),
            parse_mode="Markdown",
        )
        return True

    if intent == "cari":
        query = str(args.get("query") or "").strip()

        if not query:
            await update.message.reply_text(
                "🔍 Mau cari transaksi apa?\n\n"
                "Contoh:\n"
                "`cari kopi`\n"
                "`/cari kopi`",
                parse_mode="Markdown",
            )
            return True

        results = search_transactions(query)

        if not results:
            await update.message.reply_text(
                f"🔍 Tidak ada transaksi dengan keyword *{md_safe(query)}*.",
                parse_mode="Markdown",
            )
            return True

        lines = [f"🔍 *Hasil pencarian: \"{md_safe(query)}\"*\n"]

        for t in results:
            icon = "➕" if t.get("type") == "income" else "➖" if t.get("type") == "expense" else "🔄"
            lines.append(
                f"{icon} {md_safe(t.get('date') or '-')} — {md_safe(t.get('description') or '-')}\n"
                f"   *{format_rupiah(float(t.get('amount', 0) or 0))}* | {md_safe(t.get('category') or '-')}"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    if intent == "budget":
        month = args.get("month")

        try:
            normalized_month = normalize_month(month)
        except Exception:
            normalized_month = normalize_month(None)

        summary = get_budget_summary(normalized_month)

        if not summary:
            await update.message.reply_text(
                f"📭 Belum ada budget untuk *{format_month_label(normalized_month)}*.\n\n"
                "Set budget dengan cara:\n"
                "`budget makan 1.5 juta`\n"
                "`budget transport 300rb`\n"
                "`budget makan 1.5 juta 2026-07`",
                parse_mode="Markdown",
            )
            return True

        total_budget = sum(float(item.get("budget", 0) or 0) for item in summary)
        total_actual = sum(float(item.get("actual", 0) or 0) for item in summary)
        total_remaining = total_budget - total_actual
        total_pct = (total_actual / total_budget * 100) if total_budget > 0 else 0

        lines = [f"📊 *Budget {format_month_label(normalized_month)}*\n"]
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

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    # ── Destructive intents: preview only ─────────────────────────────────────

    if intent == "delete_txn":
        ref = str(args.get("ref") or "").strip()

        if not ref:
            await update.message.reply_text(
                "❌ Saya menangkap intent hapus transaksi, tapi nomor/ID transaksinya belum jelas.\n\n"
                "Contoh:\n"
                "`hapus transaksi nomor 2`\n"
                "`/delete_txn 2`",
                parse_mode="Markdown",
            )
            return True

        resolved = resolve_txn_refs_from_last(context, [ref])

        if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
            await update.message.reply_text(
                "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
                "Jalankan dulu:\n"
                "`/last`\n\n"
                "Lalu coba lagi:\n"
                "`hapus transaksi nomor 2`",
                parse_mode="Markdown",
            )
            return True

        preview = preview_delete_transactions_by_refs(
            row_indices=resolved["row_indices"],
            txn_ids=resolved["txn_ids"],
        )

        if not preview.get("deletable"):
            await update.message.reply_text(
                build_delete_preview_text(preview),
                parse_mode="Markdown",
            )
            return True

        context.user_data["pending_delete_refs"] = {
            "row_indices": [
                int(txn.get("_row_index"))
                for txn in preview.get("deletable", [])
                if txn.get("_row_index")
            ],
            "txn_ids": [],
        }

        await update.message.reply_text(
            build_delete_preview_text(preview),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("delete_txns"),
        )
        return True

    if intent == "edit_txn":
        ref = str(args.get("ref") or "").strip()
        updates = extract_edit_updates_from_router(args)

        if not ref:
            await update.message.reply_text(
                "❌ Saya menangkap intent edit transaksi, tapi nomor/ID transaksinya belum jelas.\n\n"
                "Contoh:\n"
                "`edit transaksi nomor 2 jadi 15000`\n"
                "`/edit_txn 2 amount=15000`",
                parse_mode="Markdown",
            )
            return True

        if not updates:
            await update.message.reply_text(
                "❌ Saya menangkap intent edit transaksi, tapi field yang diedit belum jelas.\n\n"
                "Contoh:\n"
                "`edit transaksi nomor 2 jadi 15000`\n"
                "`edit transaksi nomor 2 deskripsinya Kopi susu`",
                parse_mode="Markdown",
            )
            return True

        # Fitur ini butuh preview_edit_transaction_by_ref.
        # Kalau kamu belum pasang Phase edit_txn, bagian ini akan error saat import.
        resolved = resolve_txn_refs_from_last(context, [ref])

        if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
            await update.message.reply_text(
                "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
                "Jalankan dulu:\n"
                "`/last`\n\n"
                "Lalu coba lagi:\n"
                "`edit transaksi nomor 2 jadi 15000`",
                parse_mode="Markdown",
            )
            return True

        row_index = resolved["row_indices"][0] if resolved["row_indices"] else None
        txn_id = resolved["txn_ids"][0] if resolved["txn_ids"] else None

        try:
            preview = preview_edit_transaction_by_ref(
                updates=updates,
                row_index=row_index,
                txn_id=txn_id,
            )
        except NameError:
            await update.message.reply_text(
                "❌ Gemini sudah menangkap intent edit, tapi fitur `/edit_txn` belum terpasang penuh di kode.\n\n"
                "Pasang Phase `edit_txn` dulu, lalu fitur natural edit bisa aktif.",
                parse_mode="Markdown",
            )
            return True

        if not preview.get("success"):
            await update.message.reply_text(
                f"❌ {preview.get('message')}",
                parse_mode="Markdown",
            )
            return True

        context.user_data["pending_edit_txn"] = {
            "row_index": row_index,
            "txn_id": txn_id,
            "updates": updates,
        }

        await update.message.reply_text(
            build_edit_preview_text(preview),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("edit_txn"),
        )
        return True

    return False


def normalize_text_command(text: str) -> str:
    clean = str(text or "").strip().lower()
    clean = re.sub(r"\s+", " ", clean)
    return clean


async def handle_local_natural_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """
    Handle natural command sederhana secara lokal tanpa Gemini.

    Tujuan:
    - "cek saldo" jangan perlu Gemini
    - "cek hutang" jangan jatuh ke typo resolver "cek"
    - "cari kopi" langsung jadi pencarian
    - "lihat transaksi hari ini" langsung jadi /last today

    Return True kalau sudah di-handle.
    """
    clean = normalize_text_command(user_text)

    if not clean:
        return False

    # Jangan ganggu input yang mengandung nominal, karena kemungkinan transaksi.
    has_amount = bool(
        re.search(
            r"\b\d+(?:[.,]\d+)?\s*(rb|ribu|k|jt|juta)?\b",
            clean,
            flags=re.IGNORECASE,
        )
    )

    if has_amount:
        return False

    # ── Saldo ────────────────────────────────────────────────────────────────
    saldo_patterns = {
        "cek saldo",
        "lihat saldo",
        "tampilkan saldo",
        "saldo",
    }

    if clean in saldo_patterns:
        await saldo_handler(update, context)
        return True

    # ── Hutang / Utang / Piutang ─────────────────────────────────────────────
    hutang_patterns = {
        "cek hutang",
        "cek utang",
        "lihat hutang",
        "lihat utang",
        "tampilkan hutang",
        "tampilkan utang",
        "cek piutang",
        "lihat piutang",
        "tampilkan piutang",
        "cek hutang piutang",
        "lihat hutang piutang",
        "lihat utang piutang",
        "hutang",
        "utang",
        "piutang",
    }

    if clean in hutang_patterns:
        await hutang_handler(update, context)
        return True

    # ── Budget ───────────────────────────────────────────────────────────────
    budget_patterns = {
        "cek budget",
        "lihat budget",
        "tampilkan budget",
        "cek budget bulan ini",
        "lihat budget bulan ini",
        "tampilkan budget bulan ini",
        "budget bulan ini",
    }

    if clean in budget_patterns:
        summary = get_budget_summary(normalize_month(None))

        if not summary:
            month = normalize_month(None)
            await update.message.reply_text(
                f"📭 Belum ada budget untuk *{format_month_label(month)}*.\n\n"
                "Set budget dengan cara:\n"
                "`budget makan 1.5 juta`\n"
                "`budget transport 300rb`",
                parse_mode="Markdown",
            )
            return True

        month = normalize_month(None)
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
                f"{item['emoji']} *{md_safe(item['category'])}*\n"
                f"  {bar} {item['pct_used']}%\n"
                f"  Pakai: {format_rupiah(item['actual'])} / {format_rupiah(item['budget'])}\n"
                f"  {remaining_label}: {format_rupiah(abs(item['remaining']))}\n"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    # ── Last / histori transaksi ─────────────────────────────────────────────
    last_patterns = {
        "lihat transaksi",
        "lihat transaksi terakhir",
        "tampilkan transaksi",
        "tampilkan transaksi terakhir",
        "lihat histori",
        "lihat history",
        "histori transaksi",
        "history transaksi",
    }

    if clean in last_patterns:
        transactions = get_recent_transactions(limit=10)

        if not transactions:
            await update.message.reply_text("📭 Belum ada transaksi.")
            return True

        last_map = {}
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Terakhir"),
            parse_mode="Markdown",
        )
        return True

    today_patterns = {
        "lihat transaksi hari ini",
        "tampilkan transaksi hari ini",
        "transaksi hari ini",
        "histori hari ini",
        "history hari ini",
    }

    if clean in today_patterns:
        transactions = get_recent_transactions(limit=10, period="today")

        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi hari ini.")
            return True

        last_map = {}
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Hari Ini"),
            parse_mode="Markdown",
        )
        return True

    week_patterns = {
        "lihat transaksi minggu ini",
        "tampilkan transaksi minggu ini",
        "transaksi minggu ini",
        "histori minggu ini",
        "history minggu ini",
    }

    if clean in week_patterns:
        transactions = get_recent_transactions(limit=10, period="week")

        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi minggu ini.")
            return True

        last_map = {}
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Minggu Ini"),
            parse_mode="Markdown",
        )
        return True

    month_patterns = {
        "lihat transaksi bulan ini",
        "tampilkan transaksi bulan ini",
        "transaksi bulan ini",
        "histori bulan ini",
        "history bulan ini",
    }

    if clean in month_patterns:
        transactions = get_recent_transactions(limit=10, period="month")

        if not transactions:
            await update.message.reply_text("📭 Tidak ada transaksi bulan ini.")
            return True

        last_map = {}
        for i, txn in enumerate(transactions, 1):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

        context.user_data["last_txn_map"] = last_map

        await update.message.reply_text(
            build_last_transactions_text(transactions, "Transaksi Bulan Ini"),
            parse_mode="Markdown",
        )
        return True

    # ── Cari transaksi ───────────────────────────────────────────────────────
    # Contoh:
    # cari kopi
    # search kopi
    if clean.startswith("cari ") or clean.startswith("search "):
        keyword = clean.split(" ", 1)[1].strip()

        if not keyword:
            await update.message.reply_text(
                "🔍 Mau cari transaksi apa?\n\n"
                "Contoh:\n"
                "`cari kopi`",
                parse_mode="Markdown",
            )
            return True

        results = search_transactions(keyword)

        if not results:
            await update.message.reply_text(
                f"🔍 Tidak ada transaksi dengan keyword *{md_safe(keyword)}*.",
                parse_mode="Markdown",
            )
            return True

        lines = [f"🔍 *Hasil pencarian: \"{md_safe(keyword)}\"*\n"]

        for t in results:
            icon = "➕" if t.get("type") == "income" else "➖" if t.get("type") == "expense" else "🔄"
            lines.append(
                f"{icon} {md_safe(t.get('date'))} — {md_safe(t.get('description', '-'))}\n"
                f"   *{format_rupiah(float(t.get('amount', 0) or 0))}* | {md_safe(t.get('category', '-'))}"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    return False



# ── Image / Receipt Handler ──────────────────────────────────────────────────

async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle foto struk/nota/screenshot transaksi.

    Flow:
    - User kirim gambar.
    - Bot download gambar dari Telegram.
    - Gemini membaca gambar dan mengembalikan transaksi.
    - Hasil masuk ke flow preview + pilih rekening yang sama seperti input teks.
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    message = update.message
    if not message:
        return

    photo = message.photo[-1] if message.photo else None
    document = message.document if message.document else None

    file_id = None
    mime_type = "image/jpeg"
    file_size = 0

    if photo:
        file_id = photo.file_id
        file_size = int(photo.file_size or 0)
        mime_type = "image/jpeg"
    elif document and str(document.mime_type or "").startswith("image/"):
        file_id = document.file_id
        file_size = int(document.file_size or 0)
        mime_type = document.mime_type or "image/jpeg"
    else:
        await message.reply_text("❌ File yang dikirim belum terbaca sebagai gambar.")
        return

    # Batas aman supaya gambar besar tidak membebani memory/server.
    if file_size and file_size > 10 * 1024 * 1024:
        await message.reply_text(
            "❌ Gambar terlalu besar. Kirim gambar di bawah 10 MB."
        )
        return

    status_msg = await message.reply_text(
        "🖼️ Membaca gambar dengan Gemini...\n"
        "Pastikan gambar tidak berisi data sensitif seperti nomor rekening lengkap, password, atau OTP."
    )

    try:
        tg_file = await context.bot.get_file(file_id)
        try:
            image_bytes = await tg_file.download_as_bytearray()
        except AttributeError:
            buffer = io.BytesIO()
            await tg_file.download_to_memory(buffer)
            image_bytes = buffer.getvalue()
    except Exception as e:
        await status_msg.edit_text(f"❌ Gagal download gambar dari Telegram: {str(e)}")
        return

    caption = message.caption or ""
    result = parse_transactions_from_image(
        bytes(image_bytes),
        mime_type=mime_type,
        caption=caption,
    )

    if not result.get("success"):
        await status_msg.edit_text(
            "🤔 Gambar belum bisa saya ubah jadi transaksi.\n\n"
            f"Detail: {result.get('message') or '-'}\n\n"
            "Coba kirim foto yang lebih jelas, atau tambahkan caption seperti:\n"
            "`beli makan dari struk ini`\n"
            "`ini pemasukan`\n"
            "`pakai BSI`",
            parse_mode="Markdown",
        )
        return

    items = result.get("items", []) or []

    # Single transaction dari gambar.
    if len(items) == 1:
        parsed = items[0]
        context.user_data["pending_parsed"] = parsed
        context.user_data["pending_raw"] = caption or "[gambar]"
        context.user_data.pop("pending_batch", None)
        context.user_data.pop("pending_debt", None)
        context.user_data.pop("pending_debt_batch", None)
        context.user_data.pop("pending_mixed", None)

        preview = build_preview(parsed)

        if needs_account(parsed):
            await status_msg.edit_text(
                f"{preview}\n\n💳 Dari rekening mana?",
                parse_mode="Markdown",
                reply_markup=account_keyboard("acc"),
            )
        else:
            await status_msg.edit_text(
                f"{preview}\n\nSimpan transaksi dari gambar ini?",
                parse_mode="Markdown",
                reply_markup=confirm_keyboard("pending"),
            )
        return

    # Multiple transaction dari gambar.
    mixed_items = []
    for idx, parsed in enumerate(items, 1):
        mixed_items.append({
            "kind": "transaction",
            "parsed": parsed,
            "raw": f"gambar item {idx}",
        })

    context.user_data["pending_mixed"] = mixed_items
    context.user_data.pop("pending_parsed", None)
    context.user_data.pop("pending_raw", None)
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt", None)
    context.user_data.pop("pending_debt_batch", None)
    context.user_data.pop("mixed_review_preview_sent", None)

    preview = build_mixed_preview(mixed_items)

    if mixed_needs_account(mixed_items):
        await status_msg.edit_text(
            f"{preview}\n\n💳 Pilih rekening untuk item yang belum punya rekening:",
            parse_mode="Markdown",
            reply_markup=account_keyboard("mixed_acc"),
        )
    else:
        await status_msg.edit_text(
            f"{preview}\n\nSimpan semua transaksi dari gambar ini?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("mixed"),
        )

# ── Message Handler ──────────────────────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    user_text = update.message.text.strip()

    missing_amount_handled = await handle_pending_missing_amount(update, context, user_text)
    if missing_amount_handled:
        return

    preview_edit_handled = await handle_pending_preview_edit(update, context, user_text)
    if preview_edit_handled:
        return

    asset_add_flow_handled = await handle_pending_asset_add_flow(update, context, user_text)
    if asset_add_flow_handled:
        return

    # ── Pending asset unit price ─────────────────────────────────────────────
    pending_asset = context.user_data.get("pending_asset_price")
    if pending_asset:
        unit_price = parse_human_amount(user_text)

        if unit_price <= 0:
            await update.message.reply_text(
                "❌ Harga satuan belum valid.\n\n"
                "Balas dengan angka, contoh: `2410000`, `2.41 juta`, atau `8000000`.",
                parse_mode="Markdown",
            )
            return

        pending_asset["price_per_unit"] = unit_price
        pending_asset["needs_unit_price"] = False

        quantity = float(pending_asset.get("quantity", 0) or 0)
        pending_asset["amount"] = quantity * unit_price

        context.user_data["pending_asset_confirm"] = pending_asset
        context.user_data.pop("pending_asset_price", None)

        await update.message.reply_text(
            build_asset_confirm_preview(pending_asset),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("asset"),
        )
        return

    # ── Natural asset add ────────────────────────────────────────────────────
    natural_asset = parse_natural_asset_add(user_text)
    if natural_asset:
        context.user_data["pending_asset_price"] = natural_asset
        await update.message.reply_text(
            build_asset_unit_price_prompt(natural_asset),
            parse_mode="Markdown",
        )
        return

    # ── Layer 0: Local natural intent paling awal ────────────────────────────
    # WAJIB sebelum split/debt parser.
    # Ini untuk mencegah "cek hutang" ketangkep parse_debt_input().
    #
    # Aman karena handle_local_natural_intent() harus return False
    # kalau input mengandung nominal.
    #
    # Jadi:
    # - "cek hutang" -> /hutang
    # - "cek saldo" -> /saldo
    # - "cari kopi" -> search
    # - "Budi minjem 300k" -> tidak ke-handle di sini, lanjut debt parser
    local_natural_handled = await handle_local_natural_intent(
        update,
        context,
        user_text,
    )

    if local_natural_handled:
        return

    # ── RAG/Gemini finance question read-only ───────────────────────────────
    # Ditaruh sebelum parser transaksi, tapi hanya aktif untuk pertanyaan tanpa nominal.
    finance_question_handled = await handle_natural_finance_question(
        update,
        context,
        user_text,
    )

    if finance_question_handled:
        return

    has_explicit_separator = bool(re.search(r"[\n\r;,]", user_text))
    input_lines = split_user_inputs(user_text)
    is_multi_input = has_explicit_separator or len(input_lines) > 1

    # Single debt only
    if not is_multi_input:
        full_debt_parsed = parse_debt_input(user_text)
        if full_debt_parsed:
            debt_handled = await debt_message_handler(update, context)
            if debt_handled:
                return

    # Multi / mixed input
    if len(input_lines) > 1:
        mixed_items = []
        failed_lines = []
        missing_amount_indices = []

        for line in input_lines:
            item = parse_mixed_item(line)

            if item["kind"] == "failed":
                failed_lines.append(line)
                continue

            if item["kind"] == "missing_amount":
                missing_amount_indices.append(len(mixed_items))

            mixed_items.append(item)

        if failed_lines:
            lines = ["🤔 Ada input yang belum bisa saya pahami:\n"]

            for i, line in enumerate(failed_lines, 1):
                lines.append(f"{i}. `{line}`")

            lines.append(
                "\nCoba format seperti:\n"
                "`beli kopi 25rb`\n"
                "`Budi minjem 300k`\n"
                "`minjem Joko 100k`\n"
                "`beli kopi 10k minjem Joko 10k`"
            )

            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
            return

        if mixed_items:
            if missing_amount_indices:
                context.user_data["pending_missing_amount"] = {
                    "scope": "mixed",
                    "mixed_items": mixed_items,
                    "missing_indices": missing_amount_indices,
                    "current": 0,
                }
                first_idx = missing_amount_indices[0]
                first_item = mixed_items[first_idx]
                await update.message.reply_text(
                    build_missing_amount_prompt(
                        first_item.get("raw", ""),
                        first_item.get("parsed", {}),
                        1,
                        len(missing_amount_indices),
                    ),
                    parse_mode="Markdown",
                )
                return

            context.user_data["pending_mixed"] = mixed_items
            context.user_data.pop("pending_parsed", None)
            context.user_data.pop("pending_raw", None)
            context.user_data.pop("pending_batch", None)
            context.user_data.pop("pending_debt", None)
            context.user_data.pop("pending_debt_batch", None)
            context.user_data.pop("mixed_review_preview_sent", None)

            preview = build_mixed_preview(mixed_items)

            # Split bill harus diputuskan dulu sebelum pilih rekening/confirm.
            # Kalau tidak, input bulk seperti "22k dibagi 2 sama Sapto"
            # terlihat seperti transaksi biasa Rp22.000 dan tidak langsung
            # menanyakan apakah bagian teman sudah dibayar.
            if mixed_split_bill_needs_decision(mixed_items):
                await update.message.reply_text(
                    build_mixed_split_bill_queue_prompt(mixed_items),
                    parse_mode="Markdown",
                    reply_markup=mixed_split_bill_keyboard(mixed_items),
                )
            else:
                await reply_update_safely(
                    update,
                    f"{preview}\n\nMau edit dulu atau lanjut ke rekening/simpan?",
                    parse_mode="Markdown",
                    reply_markup=edit_or_continue_keyboard("mixed"),
                )

            return

    # Single income yang kurang nominal.
    # Contoh: "Transfer dari Sapto tgl 6" -> tanya nominal dulu,
    # bukan gagal parse dan bukan debt/payment.
    missing_amount_income = parse_income_missing_amount(user_text)
    if missing_amount_income:
        context.user_data["pending_missing_amount"] = {
            "scope": "single",
            "item": {
                "kind": "missing_amount",
                "parsed": missing_amount_income,
                "raw": user_text,
            },
        }
        await update.message.reply_text(
            build_missing_amount_prompt(user_text, missing_amount_income),
            parse_mode="Markdown",
        )
        return

    # Single transaction
    parsed = parse_input(user_text)

    if parsed.get("type") == "pending":
        # Layer 3.5: local natural intent shortcut.
        # Ini handle kasus sederhana tanpa Gemini:
        # - cek saldo
        # - cek hutang
        # - lihat budget bulan ini
        # - cari kopi
        # - lihat transaksi hari ini
        local_natural_handled = await handle_local_natural_intent(
            update,
            context,
            user_text,
        )

        if local_natural_handled:
            return

        # Layer 4: Gemini intent router.
        # Dipakai untuk natural command yang lebih fleksibel:
        # - hapus transaksi nomor 2
        # - edit transaksi nomor 2 deskripsinya Kopi susu
        gemini_handled = await handle_gemini_intent(update, context, user_text)

        if gemini_handled:
            return

        # Layer 5: local typo resolver pendek.
        # Contoh:
        # - minguan
        # - mingguannn
        # - detele
        # - bugete
        command_typo_feedback = maybe_text_is_command_typo(user_text)

        if command_typo_feedback:
            await update.message.reply_text(
                command_typo_feedback,
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            build_gemini_fallback_text(),
            parse_mode="Markdown",
        )
        return

    attach_split_bill_if_any(parsed, user_text)

    context.user_data["pending_parsed"] = parsed
    context.user_data["pending_raw"] = user_text
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt", None)
    context.user_data.pop("pending_debt_batch", None)
    context.user_data.pop("pending_mixed", None)

    preview = build_preview(parsed)

    # Untuk split bill, tanya status pembayaran teman dulu.
    # Setelah user memilih paid/unpaid, baru lanjut pilih rekening atau confirm.
    if split_bill_needs_decision(parsed):
        await update.message.reply_text(
            build_split_bill_prompt_from_parsed(parsed),
            parse_mode="Markdown",
            reply_markup=split_bill_keyboard("single"),
        )
    else:
        await reply_update_safely(
            update,
            f"{preview}\n\nMau edit dulu atau lanjut ke rekening/simpan?",
            parse_mode="Markdown",
            reply_markup=edit_or_continue_keyboard("single"),
        )


def build_transactions_full_text(transactions: list[dict], title: str, account_filter: str | None = None) -> str:
    transactions = enrich_transactions_with_debt_info(transactions or [])
    lines = [f"🧾 *{md_safe(title)}*\n"]
    append_net_gross_note(lines, transactions)

    total_income = 0.0
    total_expense = 0.0
    total_net_expense = 0.0
    total_transfer = 0.0
    total_transfer_in = 0.0
    total_transfer_out = 0.0
    account_key = str(account_filter or "").strip().lower()

    for i, txn in enumerate(transactions, 1):
        txn_type = str(txn.get("type", "")).strip().lower()
        amount = _safe_float_for_display(txn.get("amount", 0))
        source_account = str(txn.get("account", "") or "").strip()
        target_account = str(txn.get("to_account", "") or "").strip()
        source_match = bool(account_key and source_account.lower() == account_key)
        target_match = bool(account_key and target_account.lower() == account_key)

        if account_key:
            if txn_type == "income" and source_match:
                total_income += amount
            elif txn_type == "expense" and source_match:
                total_expense += amount
                total_net_expense += get_net_expense_after_receivable(txn)
            elif txn_type == "transfer":
                if source_match:
                    total_transfer_out += amount
                if target_match:
                    total_transfer_in += amount
                if source_match or target_match:
                    total_transfer += amount
        else:
            if txn_type == "income":
                total_income += amount
            elif txn_type == "expense":
                total_expense += amount
                total_net_expense += get_net_expense_after_receivable(txn)
            elif txn_type == "transfer":
                total_transfer += amount

        lines.extend(build_transaction_display_lines(txn, index=i, include_date=True, include_id=True))

    if account_key:
        net = total_income + total_transfer_in - total_expense - total_transfer_out
        expense_text = format_expense_net_gross(total_net_expense, total_expense)
        lines.append(
            "\n*Ringkasan Rekening:*\n"
            f"✅ Income          : *{format_rupiah(total_income)}*\n"
            f"❌ Expense         : *{expense_text}*\n"
            f"🔁 Transfer Masuk  : *{format_rupiah(total_transfer_in)}*\n"
            f"🔁 Transfer Keluar : *{format_rupiah(total_transfer_out)}*\n"
            f"📊 Net Rekening    : *{format_rupiah(net)}*\n"
            f"📝 Total           : *{len(transactions)} transaksi*"
        )
    else:
        net = total_income - total_expense
        expense_text = format_expense_net_gross(total_net_expense, total_expense)
        lines.append(
            "\n*Ringkasan:*\n"
            f"✅ Income   : *{format_rupiah(total_income)}*\n"
            f"❌ Expense  : *{expense_text}*\n"
            f"🔄 Transfer : *{format_rupiah(total_transfer)}*\n"
            f"📊 Net      : *{format_rupiah(net)}*\n"
            f"📝 Total    : *{len(transactions)} transaksi*"
        )

    lines.append(
        "\nNomor di atas bisa dipakai untuk koreksi setelah command ini:\n"
        "`/delete_txn 1` atau `/edit_txn 1 amount=15000`"
    )

    return "\n".join(lines)

def build_transaction_filter_title(base_title: str, category_filter: str | None = None, account_filter: str | None = None) -> str:
    suffix = []
    if category_filter:
        suffix.append(f"Kategori {category_filter}")
    if account_filter:
        suffix.append(f"Rekening {account_filter}")
    if suffix:
        return f"{base_title} — {' | '.join(suffix)}"
    return base_title


def _build_transaksi_prefixed_period_arg(first: str, rest: str, mode: str) -> str | None:
    """Bangun argumen periode+filter untuk /transaksi dengan prefix hari/minggu/bulan.

    Tujuan utamanya agar format natural seperti:
    - /transaksi bulan lalu Food & Beverage
    - /transaksi minggu lalu rekening Cash
    - /transaksi hari ini makan

    tetap bisa dibaca oleh split_report_filter_args().
    """
    rest = str(rest or "").strip()
    if not rest:
        return None

    first_rest = rest.split()[0].strip().lower()

    if mode == "month" and first_rest in {"ini", "lalu", "depan"}:
        return f"{first} {rest}"

    if mode == "date" and first_rest in {"ini", "lalu", "depan"}:
        return f"{first} {rest}"

    return rest


def parse_transaksi_period(args: list[str]) -> tuple[str, list[dict], str, str | None]:
    """Parse command /transaksi untuk full list hari/minggu/bulan/rekening tertentu."""
    raw = " ".join(args or []).strip()
    low = raw.lower()

    if not raw:
        year, month_num = parse_report_month_arg(None)
        report = get_monthly_report(year, month_num)
        return f"Transaksi Bulan {report.get('month', '-')}", report.get("transactions", []), "month", None

    first = low.split()[0]
    rest = " ".join(raw.split()[1:]).strip()

    if first in ["rekening", "akun", "account", "rek"]:
        account_arg, period_arg = split_account_period_arg(rest)
        if not account_arg:
            raise ValueError("Nama rekening belum diisi. Contoh: /transaksi rekening Cash")

        report = get_account_report(account_arg, period_arg)
        account_filter = report.get("account_filter") or account_arg
        period_label = report.get("period_label") or report.get("month") or "-"
        return (
            f"Transaksi Rekening {account_filter} — {period_label}",
            report.get("transactions", []),
            "account",
            account_filter,
        )

    if first in ["hari", "harian", "tanggal", "tgl", "tg", "day", "daily"]:
        period_source = _build_transaksi_prefixed_period_arg(first, rest, "date")
        date_arg, category_arg, account_arg = split_report_filter_args(period_source, "date")
        report = get_daily_report(date_arg, category_arg, account_arg)
        title = build_transaction_filter_title(
            f"Transaksi Tanggal {report.get('date', '-')}",
            report.get("category_filter"),
            report.get("account_filter"),
        )
        return title, report.get("transactions", []), "day", report.get("account_filter")

    if first in ["minggu", "mingguan", "week", "weekly"]:
        period_source = _build_transaksi_prefixed_period_arg(first, rest, "date")
        date_arg, category_arg, account_arg = split_report_filter_args(period_source, "date")
        report = get_weekly_report(date_arg, category_arg, account_arg)
        title = build_transaction_filter_title(
            f"Transaksi Minggu {report.get('date_from', '-')} s/d {report.get('date_to', '-')}",
            report.get("category_filter"),
            report.get("account_filter"),
        )
        return title, report.get("transactions", []), "week", report.get("account_filter")

    if first in ["bulan", "bulanan", "month", "monthly"]:
        period_source = _build_transaksi_prefixed_period_arg(first, rest, "month")
        month_arg, category_arg, account_arg = split_report_filter_args(period_source, "month")
        year, month_num = parse_report_month_arg(month_arg)
        report = get_monthly_report(year, month_num, category_arg, account_arg)
        title = build_transaction_filter_title(
            f"Transaksi Bulan {report.get('month', '-')}",
            report.get("category_filter"),
            report.get("account_filter"),
        )
        return title, report.get("transactions", []), "month", report.get("account_filter")

    if re.fullmatch(r"20\d{2}[-/]\d{1,2}[-/]\d{1,2}", low) or re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]20\d{2}", low):
        report = get_daily_report(raw)
        return f"Transaksi Tanggal {report.get('date', '-')}", report.get("transactions", []), "day", None

    if re.fullmatch(r"20\d{2}[-/]\d{1,2}", low):
        year, month_num = parse_report_month_arg(raw)
        report = get_monthly_report(year, month_num)
        return f"Transaksi Bulan {report.get('month', '-')}", report.get("transactions", []), "month", None

    if re.fullmatch(r"\d{1,2}", low):
        report = get_daily_report(raw)
        return f"Transaksi Tanggal {report.get('date', '-')}", report.get("transactions", []), "day", None

    # Alias natural tanpa prefix, misalnya:
    # /transaksi kemarin
    # /transaksi minggu lalu
    # /transaksi bulan lalu
    try:
        date_arg = parse_report_date_arg(raw)
        report = get_daily_report(date_arg)
        return f"Transaksi Tanggal {report.get('date', '-')}", report.get("transactions", []), "day", None
    except Exception:
        pass

    try:
        month_arg, category_arg, account_arg = split_report_filter_args(raw, "month")
        if month_arg or category_arg or account_arg:
            year, month_num = parse_report_month_arg(month_arg)
            report = get_monthly_report(year, month_num, category_arg, account_arg)
            title = build_transaction_filter_title(
                f"Transaksi Bulan {report.get('month', '-')}",
                report.get("category_filter"),
                report.get("account_filter"),
            )
            return title, report.get("transactions", []), "month", report.get("account_filter")
    except Exception:
        pass

    raise ValueError(
        "Format /transaksi tidak dikenali. Contoh: /transaksi 2026-06, /transaksi bulan lalu, /transaksi Food & Beverage 2026-06, /transaksi rekening Cash bulan lalu."
    )


async def transaksi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List transaksi full untuk hari/minggu/bulan tertentu."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        title, transactions, _period_type, account_filter = parse_transaksi_period(context.args)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/transaksi`\n"
            "`/transaksi 2026-06`\n"
            "`/transaksi bulan lalu`\n"
            "`/transaksi hari 2026-06-01`\n"
            "`/transaksi minggu lalu`\n"
            "`/transaksi Food & Beverage 2026-06`\n"
            "`/transaksi rekening Cash bulan lalu`",
            parse_mode="Markdown",
        )
        return

    transactions = sorted(
        transactions,
        key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)),
        reverse=True,
    )

    if not transactions:
        await update.message.reply_text(
            f"📭 Tidak ada transaksi untuk filter: *{md_safe(title)}*",
            parse_mode="Markdown",
        )
        return

    last_map = {}
    for i, txn in enumerate(transactions, 1):
        if txn.get("_row_index"):
            last_map[str(i)] = {
                "id": str(txn.get("id", "")),
                "row_index": int(txn.get("_row_index")),
            }

    context.user_data["last_txn_map"] = last_map
    await reply_long_markdown(update, build_transactions_full_text(transactions, title, account_filter))


async def last_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /last
    /last 20
    /last today
    /last week
    /last month
    /last 2026-06
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    args = context.args

    limit = 10
    period = None
    month = None
    title = "Transaksi Terakhir"

    if args:
        arg1 = args[0].strip().lower()

        if arg1.isdigit():
            limit = min(max(int(arg1), 1), 30)
            title = f"{limit} Transaksi Terakhir"

        elif arg1 in ["today", "hariini", "harian"]:
            period = "today"
            title = "Transaksi Hari Ini"

        elif arg1 in ["week", "minggu", "mingguan"]:
            period = "week"
            title = "Transaksi Minggu Ini"

        elif arg1 in ["month", "bulan", "bulanan"]:
            period = "month"
            title = "Transaksi Bulan Ini"

        elif re.fullmatch(r"20\d{2}-(0?[1-9]|1[0-2])", arg1):
            year, month_num = arg1.split("-")
            month = f"{year}-{int(month_num):02d}"
            title = f"Transaksi {month}"

        else:
            await update.message.reply_text(
                "❌ Format /last tidak dikenali.\n\n"
                "Contoh:\n"
                "`/last`\n"
                "`/last 20`\n"
                "`/last today`\n"
                "`/last week`\n"
                "`/last month`\n"
                "`/last 2026-06`",
                parse_mode="Markdown",
            )
            return

    transactions = get_recent_transactions(
        limit=limit,
        period=period,
        month=month,
    )

    if not transactions:
        await update.message.reply_text(
            f"📭 Tidak ada transaksi untuk filter: *{title}*",
            parse_mode="Markdown",
        )
        return

    last_map = {}

    for i, txn in enumerate(transactions, 1):
        last_map[str(i)] = {
            "id": str(txn.get("id", "")),
            "row_index": int(txn.get("_row_index")),
        }

    context.user_data["last_txn_map"] = last_map

    await reply_long_markdown(update, build_last_transactions_text(transactions, title))


async def delete_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /delete_txn 1
    /delete_txn 1 3 5
    /delete_txn txn_...
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    refs = context.args

    if not refs:
        await update.message.reply_text(
            "❌ Masukkan nomor transaksi dari `/last` atau transaction ID.\n\n"
            "Contoh:\n"
            "`/last today`\n"
            "`/delete_txn 1`\n"
            "`/delete_txn 1 3 5`\n"
            "`/delete_txn txn_20260609_231132_123456_abcd1234`",
            parse_mode="Markdown",
        )
        return

    resolved = resolve_txn_refs_from_last(context, refs)

    invalid_refs = resolved.get("invalid_refs", [])

    if invalid_refs and not resolved["row_indices"] and not resolved["txn_ids"]:
        await update.message.reply_text(
            "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
            "Jalankan dulu:\n"
            "`/last`\n\n"
            "Lalu hapus dengan:\n"
            "`/delete_txn 1`\n"
            "`/delete_txn 1 3 5`",
            parse_mode="Markdown",
        )
        return

    preview = preview_delete_transactions_by_refs(
        row_indices=resolved["row_indices"],
        txn_ids=resolved["txn_ids"],
    )

    if invalid_refs:
        preview["missing_rows"] = preview.get("missing_rows", []) + invalid_refs

    if not preview.get("deletable"):
        await update.message.reply_text(
            build_delete_preview_text(preview),
            parse_mode="Markdown",
        )
        return

    context.user_data["pending_delete_refs"] = {
        "row_indices": [
            int(txn.get("_row_index"))
            for txn in preview.get("deletable", [])
            if txn.get("_row_index")
        ],
        "txn_ids": [],
    }

    await update.message.reply_text(
        build_delete_preview_text(preview),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("delete_txns"),
    )

def parse_edit_updates(args: list[str]) -> dict:
    """
    Parse argumen edit.

    Format utama:
    amount=15000
    account=Cash
    category="Food & Beverage"
    desc="Kopi susu"
    date=2026-06-10

    Shortcut:
    /edit_txn 2 15000
    -> amount=15000
    """
    if not args:
        return {}

    if len(args) == 1:
        first = args[0].strip()

        if re.fullmatch(r"\d+(?:[.,]\d+)?", first):
            return {
                "amount": first.replace(",", ".")
            }

    updates = {}

    for arg in args:
        if "=" not in arg:
            raise ValueError(
                f"Argumen `{arg}` tidak valid. Gunakan format key=value."
            )

        key, value = arg.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key or value == "":
            raise ValueError(
                f"Argumen `{arg}` tidak valid. Gunakan format key=value."
            )

        updates[key] = value

    return updates


def build_edit_preview_text(preview: dict) -> str:
    old_txn = preview.get("old_txn", {})
    new_txn = preview.get("new_txn", {})
    updates = preview.get("updates", {})
    net_deltas = preview.get("net_deltas", {})

    lines = ["✏️ *Preview Edit Transaksi*\n"]

    lines.append("*Sebelum:*")
    lines.append(
        f"• {old_txn.get('date')} — *{old_txn.get('description') or '-'}*\n"
        f"  {format_rupiah(float(old_txn.get('amount', 0) or 0))} | "
        f"{old_txn.get('category') or '-'} | {old_txn.get('account') or '-'}"
    )

    lines.append("\n*Sesudah:*")
    lines.append(
        f"• {new_txn.get('date')} — *{new_txn.get('description') or '-'}*\n"
        f"  {format_rupiah(float(new_txn.get('amount', 0) or 0))} | "
        f"{new_txn.get('category') or '-'} | {new_txn.get('account') or '-'}"
    )

    if updates:
        lines.append("\n*Field yang diubah:*")
        for field, value in updates.items():
            lines.append(f"• {field}: `{value}`")

    if net_deltas:
        lines.append("\n*Efek ke saldo:*")
        for account, delta in net_deltas.items():
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {account}: {sign}{format_rupiah(abs(delta))}")
    else:
        lines.append("\n*Efek ke saldo:*")
        lines.append("• Tidak ada perubahan saldo")

    lines.append("\nSimpan perubahan ini?")

    return "\n".join(lines)

async def edit_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /edit_txn 2 amount=15000
    /edit_txn 2 amount=15000 desc="Kopi susu"
    /edit_txn 2 account=BRI category="Food & Beverage"
    /edit_txn txn_... amount=20000
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    raw_text = update.message.text.strip()

    try:
        parts = shlex.split(raw_text)
    except Exception:
        await update.message.reply_text(
            "❌ Format edit tidak valid. Kalau ada spasi, pakai tanda kutip.\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`",
            parse_mode="Markdown",
        )
        return

    # parts[0] = /edit_txn
    args = parts[1:]

    if len(args) < 2:
        await update.message.reply_text(
            "❌ Format edit belum lengkap.\n\n"
            "Contoh:\n"
            "`/last`\n"
            "`/edit_txn 2 amount=15000`\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`\n"
            "`/edit_txn 2 account=BRI category=\"Food & Beverage\"`\n"
            "`/edit_txn 2 15000`",
            parse_mode="Markdown",
        )
        return

    ref = args[0]
    update_args = args[1:]

    resolved = resolve_txn_refs_from_last(context, [ref])

    if resolved.get("invalid_refs") and not resolved["row_indices"] and not resolved["txn_ids"]:
        await update.message.reply_text(
            "❌ Nomor transaksi tidak ditemukan dari hasil `/last` terakhir.\n\n"
            "Jalankan dulu:\n"
            "`/last`\n\n"
            "Lalu edit dengan:\n"
            "`/edit_txn 2 amount=15000`",
            parse_mode="Markdown",
        )
        return

    try:
        updates = parse_edit_updates(update_args)
    except Exception as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000`\n"
            "`/edit_txn 2 amount=15000 desc=\"Kopi susu\"`\n"
            "`/edit_txn 2 account=BRI category=\"Food & Beverage\"`",
            parse_mode="Markdown",
        )
        return

    if not updates:
        await update.message.reply_text(
            "❌ Tidak ada field yang diedit.\n\n"
            "Contoh:\n"
            "`/edit_txn 2 amount=15000`",
            parse_mode="Markdown",
        )
        return

    row_index = resolved["row_indices"][0] if resolved["row_indices"] else None
    txn_id = resolved["txn_ids"][0] if resolved["txn_ids"] else None

    preview = preview_edit_transaction_by_ref(
        updates=updates,
        row_index=row_index,
        txn_id=txn_id,
    )

    if not preview.get("success"):
        await update.message.reply_text(
            f"❌ {preview.get('message')}",
            parse_mode="Markdown",
        )
        return

    context.user_data["pending_edit_txn"] = {
        "row_index": row_index,
        "txn_id": txn_id,
        "updates": updates,
    }

    await update.message.reply_text(
        build_edit_preview_text(preview),
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("edit_txn"),
    )


# ── Callback Handler ─────────────────────────────────────────────────────────

