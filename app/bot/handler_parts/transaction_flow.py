# Split from app/bot/handlers.py for readability.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *

def parse_input(text: str) -> dict:
    """Coba regex dulu, fallback ke Gemini."""
    result = parse_with_regex(text)
    if result is not None:
        return result

    return parse_with_pending_fallback(text)


def build_progress_bar(pct: float, length: int = 10) -> str:
    """Buat progress bar teks. Contoh: [████░░░░░░] 40%"""
    filled = int(min(float(pct or 0), 100) / 100 * length)
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"


def split_user_inputs(text: str) -> list[str]:
    """
    Pecah input user menjadi beberapa item.

    Support:
    - newline
    - koma
    - titik koma
    - "dan" sebelum item baru
    - transaksi biasa berulang:
      beli kopi 10k beli nasi 20k
    - campuran transaksi + debt:
      beli kopi 10k minjem joko 10k
      beli kopi 10k hutang ke joko 10k

    Catatan penting:
    - "Budi minjem 300k" jangan dipecah.
    - "bayar hutang Joko 200k" jangan dipecah jadi bayar/hutang.
    """
    if not text:
        return []

    raw = text.strip()

    # Separator eksplisit harus diproses SEBELUM normalisasi whitespace.
    # Kalau `re.sub(r"\s+", " ", raw)` dijalankan dulu, newline ikut
    # berubah jadi spasi dan input multi-baris akan dianggap 1 transaksi panjang.
    raw = re.sub(r"[\n\r;]+", " ||| ", raw)
    raw = re.sub(r"\s*,\s*", " ||| ", raw)
    raw = re.sub(r"[ \t]+", " ", raw)

    # Starter transaksi biasa
    transaction_starters = [
        "beli", "bayar", "byr", "jajan", "makan", "minum",
        "transfer", "top up", "topup", "isi", "ngisi",
        "gaji", "dapat", "dapet", "terima",
        # Jangan masukkan "masuk" sebagai starter split.
        # Contoh yang harus tetap satu item:
        # "gajian 5000k masuk BCA 01-06-2026".
        # Kata "masuk" tetap dikenali sebagai income di regex_parser.detect_type().
        "hutang", "utang",
    ]

    # Starter debt yang boleh jadi item baru jika muncul setelah item lain
    # Contoh: "beli kopi 10k minjem joko 10k"
    debt_starters = [
        "minjem", "pinjem", "pinjam",
        "hutang ke", "utang ke",
        "bayar hutang", "bayar utang",
        "saya talangin", "aku talangin", "gw talangin", "gue talangin",
        "saya ditalangin", "aku ditalangin", "gw ditalangin", "gue ditalangin",
        "talangin", "ditalangin", "nitip",
    ]

    all_starters = transaction_starters + debt_starters
    starter_pattern = "|".join(re.escape(k) for k in sorted(all_starters, key=len, reverse=True))

    # Pecah "dan beli", "dan minjem", dst.
    raw = re.sub(
        rf"\s+dan\s+(?=({starter_pattern})\b)",
        " ||| ",
        raw,
        flags=re.IGNORECASE,
    )

    # Protect single debt payment:
    # "bayar hutang Joko 200k"
    protected_debt_payment = re.search(
        r"\b(bayar|byr|lunasi|lunas|cicil)\s+(hutang|utang)\b",
        raw,
        flags=re.IGNORECASE,
    )

    if protected_debt_payment and "|||" not in raw:
        return [raw.strip(" .,-;")]

    # Split item baru jika sebelum keyword ada nominal.
    # Ini mencegah "Budi minjem 300k" terpecah karena sebelum "minjem" bukan nominal.
    amount_before_pattern = r"(?:\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)?|\d{4,})"

    raw = re.sub(
        rf"({amount_before_pattern})\s+(?=({starter_pattern})\b)",
        r"\1 ||| ",
        raw,
        flags=re.IGNORECASE,
    )

    # Tidak lagi memecah sebelum starter tanpa nominal di depannya.
    # Versi lama memecah "saya talangin Sapto beli nasi 12k" menjadi
    # "saya talangin Sapto" + "beli nasi 12k" karena kata "beli" dianggap
    # starter baru. Sekarang pemecahan otomatis cukup mengandalkan separator
    # eksplisit atau pola nominal-sebelum-starter di atas.

    parts = []
    for part in raw.split("|||"):
        clean = part.strip(" .,-;")
        if clean:
            parts.append(clean)

    return parts

def needs_account(parsed: dict) -> bool:
    """
    Transaksi expense/income wajib punya account.
    Transfer wajib punya account asal dan to_account.

    Catatan: account keyboard hanya mengisi account asal. Jika to_account
    belum terdeteksi, service layer akan menolak saat simpan agar data aman.
    """
    txn_type = parsed.get("type")

    if txn_type in ["expense", "income"] and not parsed.get("account"):
        return True

    if txn_type == "transfer" and (not parsed.get("account") or not parsed.get("to_account")):
        return True

    return False

def is_debt_item(parsed: dict) -> bool:
    return parsed.get("kind") == "debt"


def is_transaction_item(parsed: dict) -> bool:
    return parsed.get("kind") == "transaction"


def build_mixed_preview(mixed_items: list[dict]) -> str:
    """Preview untuk campuran transaksi biasa + debt."""
    lines = [f"🧾 *Ditemukan {len(mixed_items)} item:*\n"]

    total_expense = 0
    total_income = 0
    total_debt = 0

    for i, item in enumerate(mixed_items, 1):
        kind = item["kind"]
        raw = item["raw"]

        if kind == "transaction":
            parsed = item["parsed"]
            txn_type = parsed.get("type")
            amount = float(parsed.get("amount", 0) or 0)

            if txn_type == "expense":
                icon = "❌"
                total_expense += amount
            elif txn_type == "income":
                icon = "✅"
                total_income += amount
            else:
                icon = "🔄"

            desc = md_safe(parsed.get('description') or '-')
            category = md_safe(parsed.get('category') or '-')
            account = md_safe(parsed.get('account') or '-')
            date = md_safe(parsed.get('date') or '-')
            safe_raw = md_safe(raw)
            split_preview = format_split_bill_preview_line(parsed)
            split_line = f"   {md_safe(split_preview)}\n" if split_preview else ""

            lines.append(
                f"{i}. {icon} *Transaksi*\n"
                f"   📝 {desc}\n"
                f"   💰 {format_rupiah(amount)} | {category}\n"
                f"   📅 {date}\n"
                f"   🏦 {account}\n"
                f"{split_line}"
                f"   Input: `{safe_raw}`"
            )

        elif kind == "debt":
            parsed = item["parsed"]
            intent = parsed.get("intent")
            person = parsed.get("person_name") or "-"
            amount = float(parsed.get("amount", 0) or 0)
            total_debt += amount

            if intent == "add_receivable":
                label = "🟢 Piutang Baru"
                effect = "cash out"
            elif intent == "add_payable":
                label = "🔴 Utang Baru"
                effect = "cash in"
            elif intent == "add_payment":
                label = "💸 Pembayaran Debt"
                effect = "mengikuti posisi debt aktif"
            else:
                label = "❓ Debt"
                effect = "-"

            safe_person = md_safe(person)
            account = md_safe(parsed.get('account') or '-')
            date = md_safe(parsed.get('date') or parsed.get('transaction_date') or '-')
            safe_raw = md_safe(raw)

            lines.append(
                f"{i}. {label}\n"
                f"   👤 {safe_person}\n"
                f"   💰 {format_rupiah(amount)}\n"
                f"   📅 {date}\n"
                f"   🏦 {account}\n"
                f"   📌 {effect}\n"
                f"   Input: `{safe_raw}`"
            )

    lines.append("\n*Ringkasan awal:*")
    lines.append(f"❌ Transaksi Expense: *{format_rupiah(total_expense)}*")
    lines.append(f"✅ Transaksi Income : *{format_rupiah(total_income)}*")
    lines.append(f"💸 Total Nominal Debt: *{format_rupiah(total_debt)}*")

    account_summary = build_account_delta_summary_from_transaction_items(mixed_items)
    if account_summary:
        lines.append(account_summary)

    return "\n".join(lines)

def parse_income_missing_amount(line: str) -> dict | None:
    """Deteksi income masuk dari orang yang belum punya nominal.

    Contoh yang harus ditanya nominalnya:
    - Transfer dari Sapto tgl 6
    - Transaksi dari Annisa

    Ini sengaja tidak dianggap debt/payment. Debt hanya dari keyword utang/piutang/minjem
    atau split bill eksplisit.
    """
    raw = str(line or "").strip()
    if not raw:
        return None

    # Kalau setelah frasa tanggal dibuang masih ada nominal, biarkan parser normal yang handle.
    without_date = strip_date_phrases(raw)
    if parse_human_amount(without_date) > 0 and re.search(r"\d", without_date):
        return None

    # Jangan ambil internal transfer rekening: transfer dari BSI ke DANA.
    low = raw.lower()
    if re.search(r"\bdari\s+[^\n]+?\s+ke\s+", low):
        return None

    match = re.search(
        r"^\s*(?:transaksi|transfer(?:an)?|tf|trf|kiriman|uang)\s+(?:masuk\s+)?dari\s+(.+?)\s*$",
        raw,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    person_raw = match.group(1).strip()
    # Buang frasa tanggal dari nama orang.
    person_raw = re.sub(r"\b(?:tgl|tanggal)\s*\d{1,2}(?:[-/]\d{1,2}(?:[-/]\d{2,4})?)?\b", " ", person_raw, flags=re.IGNORECASE)
    person_raw = re.sub(r"\b(?:hari\s+ini|kemarin|besok)\b", " ", person_raw, flags=re.IGNORECASE)
    person = re.sub(r"\s+", " ", person_raw).strip(" .,-;")

    if not person:
        return None

    account_like = {"cash", "bri", "bsi", "bca", "dana", "gopay", "seabank", "sea bank"}
    if person.lower() in account_like:
        return None

    return {
        "type": "income",
        "amount": None,
        "category": "Other Income",
        "account": None,
        "to_account": None,
        "subject": person.title(),
        "description": person.title(),
        "catatan": raw,
        "tipe_pengeluaran": "",
        "date": detect_date(raw),
        "parsed_by": "missing_amount",
        "needs_amount": True,
    }


def build_missing_amount_prompt(raw: str, parsed: dict, current: int | None = None, total: int | None = None) -> str:
    prefix = ""
    if current is not None and total is not None and total > 1:
        prefix = f"🧩 *Nominal kurang {current}/{total}*\n\n"

    desc = md_safe(parsed.get("description") or raw)
    date = md_safe(parsed.get("date") or "-")
    return (
        f"{prefix}🤔 Saya mendeteksi income, tapi nominalnya belum ada.\n\n"
        f"📝 Item: *{desc}*\n"
        f"📅 Tanggal: *{date}*\n"
        f"📌 Input: `{md_safe(raw)}`\n\n"
        "Nominalnya berapa? Contoh: `13k`, `50000`, atau `94k/2`."
    )


def finalize_missing_amount_item(item: dict, amount: float) -> dict:
    parsed = dict(item.get("parsed") or {})
    parsed["amount"] = amount
    parsed.pop("needs_amount", None)
    parsed["parsed_by"] = parsed.get("parsed_by") or "missing_amount"
    return {
        "kind": "transaction",
        "parsed": parsed,
        "raw": item.get("raw") or parsed.get("catatan") or "",
    }


async def continue_after_missing_amount_mixed(update: Update, context: ContextTypes.DEFAULT_TYPE, mixed_items: list[dict]) -> None:
    context.user_data["pending_mixed"] = mixed_items
    context.user_data.pop("pending_parsed", None)
    context.user_data.pop("pending_raw", None)
    context.user_data.pop("pending_batch", None)
    context.user_data.pop("pending_debt", None)
    context.user_data.pop("pending_debt_batch", None)
    context.user_data.pop("mixed_review_preview_sent", None)

    preview = build_mixed_preview(mixed_items)

    if mixed_split_bill_needs_decision(mixed_items):
        await reply_update_safely(
            update,
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


async def handle_pending_missing_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    state = context.user_data.get("pending_missing_amount")
    if not state:
        return False

    amount = parse_human_amount(user_text)
    if not amount or amount <= 0:
        await update.message.reply_text(
            "❌ Nominalnya belum kebaca. Coba tulis seperti `13k`, `50000`, atau `94k/2`.",
            parse_mode="Markdown",
        )
        return True

    scope = state.get("scope")
    if scope == "mixed":
        mixed_items = state.get("mixed_items") or []
        missing_indices = state.get("missing_indices") or []
        current = int(state.get("current") or 0)

        if current >= len(missing_indices):
            context.user_data.pop("pending_missing_amount", None)
            await update.message.reply_text("❌ Tidak ada input kurang nominal yang sedang menunggu jawaban.")
            return True

        idx = missing_indices[current]
        if 0 <= idx < len(mixed_items):
            mixed_items[idx] = finalize_missing_amount_item(mixed_items[idx], amount)

        current += 1
        if current < len(missing_indices):
            state["mixed_items"] = mixed_items
            state["current"] = current
            context.user_data["pending_missing_amount"] = state
            next_idx = missing_indices[current]
            next_item = mixed_items[next_idx]
            await update.message.reply_text(
                build_missing_amount_prompt(next_item.get("raw", ""), next_item.get("parsed", {}), current + 1, len(missing_indices)),
                parse_mode="Markdown",
            )
            return True

        context.user_data.pop("pending_missing_amount", None)
        await continue_after_missing_amount_mixed(update, context, mixed_items)
        return True

    if scope == "single":
        item = state.get("item") or {}
        finalized = finalize_missing_amount_item(item, amount)
        parsed = finalized["parsed"]
        context.user_data["pending_parsed"] = parsed
        context.user_data["pending_raw"] = finalized.get("raw") or user_text
        context.user_data.pop("pending_missing_amount", None)
        context.user_data.pop("pending_batch", None)
        context.user_data.pop("pending_debt", None)
        context.user_data.pop("pending_debt_batch", None)
        context.user_data.pop("pending_mixed", None)

        preview = build_preview(parsed)
        await reply_update_safely(
            update,
            f"{preview}\n\nMau edit dulu atau lanjut ke rekening/simpan?",
            parse_mode="Markdown",
            reply_markup=edit_or_continue_keyboard("single"),
        )
        return True

    context.user_data.pop("pending_missing_amount", None)
    return False


def parse_mixed_item(line: str) -> dict:
    """
    Parse satu item sebagai debt dulu, lalu transaksi biasa.

    Return:
    {
        "kind": "debt"|"transaction"|"missing_amount"|"failed",
        "parsed": dict,
        "raw": str
    }
    """
    debt_parsed = parse_debt_input(line)
    if debt_parsed:
        return {
            "kind": "debt",
            "parsed": debt_parsed,
            "raw": line,
        }

    missing_amount_income = parse_income_missing_amount(line)
    if missing_amount_income:
        return {
            "kind": "missing_amount",
            "parsed": missing_amount_income,
            "raw": line,
        }

    txn_parsed = parse_input(line)
    if txn_parsed and txn_parsed.get("type") != "pending":
        attach_split_bill_if_any(txn_parsed, line)
        return {
            "kind": "transaction",
            "parsed": txn_parsed,
            "raw": line,
        }

    return {
        "kind": "failed",
        "parsed": {},
        "raw": line,
    }

def mixed_needs_account(mixed_items: list[dict]) -> bool:
    for item in mixed_items:
        parsed = item["parsed"]

        if item["kind"] == "transaction" and needs_account(parsed):
            return True

        if item["kind"] == "debt" and debt_uses_cashflow(parsed) and not parsed.get("account"):
            return True

    return False


def edit_or_continue_keyboard(scope: str) -> InlineKeyboardMarkup:
    """Keyboard setelah preview: edit dulu atau lanjut ke rekening/simpan."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Edit dulu", callback_data=f"editflow:edit:{scope}"),
            InlineKeyboardButton("➡️ Lanjut", callback_data=f"editflow:continue:{scope}"),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")],
    ])


def build_account_delta_summary_from_transaction_items(items: list[dict]) -> str:
    """Ringkasan dampak saldo per rekening dari item transaksi yang sudah punya account."""
    transaction_items = []
    for item in items or []:
        parsed = item.get("parsed", item) if isinstance(item, dict) else {}
        if isinstance(parsed, dict) and parsed.get("type") in ["expense", "income", "transfer"]:
            transaction_items.append({"parsed": parsed})

    deltas = calculate_account_deltas(transaction_items)
    if not deltas:
        return ""

    lines = ["\n💳 *Ringkasan per rekening:*"]
    for account_name, delta in deltas.items():
        sign = "+" if float(delta or 0) >= 0 else "-"
        lines.append(f"• {md_safe(account_name)}: {sign}{format_rupiah(abs(float(delta or 0)))}")
    return "\n".join(lines)


def build_mixed_short_summary(mixed_items: list[dict]) -> str:
    """Ringkasan pendek untuk transisi setelah preview panjang sudah pernah ditampilkan."""
    total_expense = 0.0
    total_income = 0.0
    total_transfer = 0.0
    total_debt = 0.0
    transaction_count = 0
    debt_count = 0

    for item in mixed_items or []:
        kind = item.get("kind")
        parsed = item.get("parsed", {}) or {}
        amount = float(parsed.get("amount", 0) or 0)
        if kind == "transaction":
            transaction_count += 1
            txn_type = parsed.get("type")
            if txn_type == "expense":
                total_expense += amount
            elif txn_type == "income":
                total_income += amount
            elif txn_type == "transfer":
                total_transfer += amount
        elif kind == "debt":
            debt_count += 1
            total_debt += amount

    lines = ["🧾 *Ringkasan batch:*"]
    lines.append(f"• Total item: *{len(mixed_items or [])}*")
    if transaction_count:
        lines.append(f"• Transaksi: *{transaction_count} item*")
    if total_expense:
        lines.append(f"• Expense: *{format_rupiah(total_expense)}*")
    if total_income:
        lines.append(f"• Income: *{format_rupiah(total_income)}*")
    if total_transfer:
        lines.append(f"• Transfer: *{format_rupiah(total_transfer)}*")
    if debt_count:
        lines.append(f"• Debt: *{debt_count} item* / {format_rupiah(total_debt)}")

    account_summary = build_account_delta_summary_from_transaction_items(mixed_items)
    if account_summary:
        lines.append(account_summary)

    return "\n".join(lines)


def build_single_short_summary(parsed: dict) -> str:
    """Ringkasan pendek untuk single transaction setelah preview awal sudah tampil."""
    if not isinstance(parsed, dict):
        return "🧾 *Ringkasan transaksi:* -"

    txn_type = parsed.get("type") or "transaction"
    description = md_safe(parsed.get("description") or parsed.get("subject") or "Transaksi")
    amount = float(parsed.get("amount", 0) or 0)
    category = md_safe(parsed.get("category") or "-")
    account = md_safe(parsed.get("account") or "-")

    lines = ["🧾 *Ringkasan transaksi:*"]
    lines.append(f"• Jenis: *{md_safe(txn_type)}*")
    lines.append(f"• Item: *{description}*")
    lines.append(f"• Nominal: *{format_rupiah(amount)}*")
    if category != "-":
        lines.append(f"• Kategori: *{category}*")
    if account != "-":
        lines.append(f"• Rekening: *{account}*")

    account_summary = build_account_delta_summary_from_transaction_items([{"parsed": parsed}])
    if account_summary:
        lines.append(account_summary)

    return "\n".join(lines)


def build_updated_item_summary(item: dict, index: int | None = None) -> str:
    """Ringkasan pendek item yang baru diedit."""
    prefix = f"Item {index}" if index else "Item"
    kind = item.get("kind") if isinstance(item, dict) else None
    parsed = item.get("parsed", {}) if isinstance(item, dict) else {}

    if kind == "transaction":
        label = md_safe(parsed.get("description") or parsed.get("subject") or "Transaksi")
        amount = float(parsed.get("amount", 0) or 0)
        category = md_safe(parsed.get("category") or "-")
        account = md_safe(parsed.get("account") or "-")
        return (
            f"✅ *{prefix} sudah diupdate.*\n"
            f"• {label}\n"
            f"• {format_rupiah(amount)} | {category}\n"
            f"• Rekening: {account}"
        )

    if kind == "debt":
        person = md_safe(parsed.get("person_name") or "-")
        amount = float(parsed.get("amount", 0) or 0)
        account = md_safe(parsed.get("account") or "-")
        return (
            f"✅ *{prefix} debt sudah diupdate.*\n"
            f"• {person}\n"
            f"• {format_rupiah(amount)}\n"
            f"• Rekening: {account}"
        )

    return f"✅ *{prefix} sudah diupdate.*"


def build_preview_edit_help(scope: str = "single") -> str:
    item_hint = "" if scope == "single" else "\nKamu sedang mengedit item yang dipilih."
    return (
        "✏️ *Mau edit apa?*" + item_hint + "\n\n"
        "Ketik salah satu format berikut:\n"
        "`nominal 25000`\n"
        "`kategori Food & Beverage`\n"
        "`deskripsi Kopi susu`\n"
        "`subjek Annisa`\n"
        "`tipe income` atau `tipe expense`\n"
        "`tanggal 2026-06-12`\n"
        "`rekening BCA`\n\n"
        "Bisa juga pakai `field=value`, contoh `category=Food & Beverage`."
    )


def build_mixed_edit_choose_prompt(mixed_items: list[dict]) -> str:
    lines = ["✏️ *Mau edit item nomor berapa?*\n"]
    for i, item in enumerate(mixed_items or [], 1):
        kind = item.get("kind")
        parsed = item.get("parsed", {})
        if kind == "transaction":
            label = parsed.get("description") or parsed.get("subject") or item.get("raw", "-")
            amount = parsed.get("amount", 0)
            lines.append(f"{i}. {md_safe(label)} — {format_rupiah(float(amount or 0))}")
        elif kind == "debt":
            label = parsed.get("person_name") or item.get("raw", "-")
            amount = parsed.get("amount", 0)
            lines.append(f"{i}. Debt {md_safe(label)} — {format_rupiah(float(amount or 0))}")
        else:
            lines.append(f"{i}. {md_safe(item.get('raw', '-'))}")
    lines.append("\nBalas dengan angka, contoh: `2`.")
    return "\n".join(lines)


def parse_preview_edit_updates(text: str) -> dict:
    """Parse update sederhana untuk preview sebelum simpan."""
    raw = str(text or "").strip()
    updates: dict = {}

    key_aliases = {
        "amount": "amount", "nominal": "amount", "jumlah": "amount",
        "category": "category", "kategori": "category",
        "description": "description", "desc": "description", "deskripsi": "description",
        "subject": "subject", "subjek": "subject",
        "type": "type", "tipe": "type", "jenis": "type",
        "date": "date", "tanggal": "date", "tgl": "date",
        "account": "account", "rekening": "account", "akun": "account",
        "to_account": "to_account", "ke_rekening": "to_account", "rekening_tujuan": "to_account",
        "catatan": "catatan", "note": "catatan",
        "tipe_pengeluaran": "tipe_pengeluaran", "pengeluaran": "tipe_pengeluaran",
    }

    eq_match = re.match(r"^([a-zA-Z_]+)\s*=\s*(.+)$", raw)
    if eq_match:
        key = key_aliases.get(eq_match.group(1).lower())
        value = eq_match.group(2).strip()
    else:
        natural_match = re.match(
            r"^(nominal|jumlah|amount|kategori|category|deskripsi|description|desc|subjek|subject|tipe|type|jenis|tanggal|tgl|date|rekening|account|akun|catatan|note|tipe_pengeluaran|pengeluaran|ke_rekening|to_account|rekening_tujuan)\s+(.+)$",
            raw,
            flags=re.IGNORECASE,
        )
        if not natural_match:
            return {}
        key = key_aliases.get(natural_match.group(1).lower())
        value = natural_match.group(2).strip()

    if not key or value == "":
        return {}

    if key == "amount":
        amount = parse_human_amount(value)
        if amount <= 0:
            return {}
        updates[key] = amount
    elif key == "type":
        normalized = value.lower().strip()
        type_aliases = {
            "income": "income", "pemasukan": "income", "masuk": "income",
            "expense": "expense", "pengeluaran": "expense", "keluar": "expense",
            "transfer": "transfer",
        }
        if normalized not in type_aliases:
            return {}
        updates[key] = type_aliases[normalized]
    elif key == "date":
        from app.nlp.regex_parser import parse_explicit_date
        parsed_date = parse_explicit_date(value) or value
        updates[key] = parsed_date
    elif key in ["account", "to_account"]:
        value_clean = value.strip()
        updates[key] = value_clean.upper() if value_clean.lower() in ["bca", "bri", "bsi", "dana"] else value_clean.title()
    else:
        updates[key] = value.strip()

    return updates


def apply_preview_edit_updates_to_parsed(parsed: dict, updates: dict) -> dict:
    if not isinstance(parsed, dict):
        return parsed

    parsed.update(updates)

    txn_type = parsed.get("type")
    if "type" in updates:
        if txn_type == "income" and (not parsed.get("category") or parsed.get("category") == "Other Expense"):
            parsed["category"] = "Other Income"
            parsed["tipe_pengeluaran"] = ""
        elif txn_type == "expense" and (not parsed.get("category") or parsed.get("category") == "Other Income"):
            parsed["category"] = "Other Expense"

    if "description" in updates and (not parsed.get("subject") or parsed.get("subject") in ["Pemasukan", "Transaksi"]):
        parsed["subject"] = updates["description"]

    return parsed


async def proceed_after_preview_edit(query, context: ContextTypes.DEFAULT_TYPE, scope: str):
    """Lanjutkan flow setelah user memilih 'Lanjut'."""
    context.user_data.pop("pending_preview_edit", None)

    if scope == "mixed":
        mixed_items = context.user_data.get("pending_mixed")
        if not mixed_items:
            await safe_edit_message(query, "❌ Sesi mixed input expired. Coba input ulang.")
            return

        if mixed_split_bill_needs_decision(mixed_items):
            await safe_edit_message(query, 
                build_mixed_split_bill_queue_prompt(mixed_items),
                parse_mode="Markdown",
                reply_markup=mixed_split_bill_keyboard(mixed_items),
            )
            return

        short_summary = build_mixed_short_summary(mixed_items)
        if mixed_needs_account(mixed_items):
            await safe_edit_message(query, 
                f"{short_summary}\n\n💳 Pilih rekening untuk item yang belum punya rekening:",
                parse_mode="Markdown",
                reply_markup=account_keyboard("mixed_acc"),
            )
            return

        await safe_edit_message(query, 
            f"{short_summary}\n\nSimpan semua item ini?",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("mixed"),
        )
        return

    parsed = context.user_data.get("pending_parsed")
    if not parsed:
        await safe_edit_message(query, "❌ Sesi transaksi expired. Coba input ulang.")
        return

    if split_bill_needs_decision(parsed):
        await safe_edit_message(query, 
            build_split_bill_prompt_from_parsed(parsed),
            parse_mode="Markdown",
            reply_markup=split_bill_keyboard("single"),
        )
        return

    short_summary = build_single_short_summary(parsed)
    if needs_account(parsed):
        await safe_edit_message(query, 
            f"{short_summary}\n\n💳 Dari rekening mana?",
            parse_mode="Markdown",
            reply_markup=account_keyboard("acc"),
        )
        return

    await safe_edit_message(query, 
        f"{short_summary}\n\nSimpan transaksi ini?",
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("pending"),
    )


async def handle_pending_preview_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Handle balasan user untuk edit preview sebelum pilih rekening/simpan."""
    state = context.user_data.get("pending_preview_edit")
    if not state:
        return False

    scope = state.get("scope")
    step = state.get("step")

    if scope == "mixed" and step == "choose_item":
        try:
            item_index = int(str(user_text).strip()) - 1
        except Exception:
            await update.message.reply_text("❌ Balas dengan nomor item, contoh: `2`.", parse_mode="Markdown")
            return True

        mixed_items = context.user_data.get("pending_mixed") or []
        if item_index < 0 or item_index >= len(mixed_items):
            await update.message.reply_text("❌ Nomor item tidak valid. Coba pilih nomor yang ada di preview.")
            return True

        state["step"] = "edit_item"
        state["index"] = item_index
        context.user_data["pending_preview_edit"] = state
        await update.message.reply_text(build_preview_edit_help("mixed"), parse_mode="Markdown")
        return True

    updates = parse_preview_edit_updates(user_text)
    if not updates:
        await update.message.reply_text(
            "❌ Format edit belum kebaca.\n\n" + build_preview_edit_help(scope or "single"),
            parse_mode="Markdown",
        )
        return True

    if scope == "mixed":
        mixed_items = context.user_data.get("pending_mixed") or []
        item_index = int(state.get("index", -1))
        if item_index < 0 or item_index >= len(mixed_items):
            context.user_data.pop("pending_preview_edit", None)
            await update.message.reply_text("❌ Sesi edit mixed tidak valid. Coba input ulang.")
            return True

        item = mixed_items[item_index]
        if item.get("kind") == "transaction":
            item["parsed"] = apply_preview_edit_updates_to_parsed(item.get("parsed", {}), updates)
        elif item.get("kind") == "debt":
            debt_updates = dict(updates)
            if "subject" in debt_updates:
                debt_updates["person_name"] = debt_updates.pop("subject")
            item.setdefault("parsed", {}).update(debt_updates)
        mixed_items[item_index] = item
        context.user_data["pending_mixed"] = mixed_items
        context.user_data.pop("pending_preview_edit", None)

        item_summary = build_updated_item_summary(item, item_index + 1)
        short_summary = build_mixed_short_summary(mixed_items)
        await reply_update_safely(
            update,
            f"{item_summary}\n\n{short_summary}\n\nMau edit lagi atau lanjut?",
            parse_mode="Markdown",
            reply_markup=edit_or_continue_keyboard("mixed"),
        )
        return True

    parsed = context.user_data.get("pending_parsed")
    if not parsed:
        context.user_data.pop("pending_preview_edit", None)
        await update.message.reply_text("❌ Sesi edit transaksi expired. Coba input ulang.")
        return True

    parsed = apply_preview_edit_updates_to_parsed(parsed, updates)
    context.user_data["pending_parsed"] = parsed
    context.user_data.pop("pending_preview_edit", None)

    short_summary = build_single_short_summary(parsed)
    await reply_update_safely(
        update,
        f"✅ Preview sudah diupdate.\n\n{short_summary}\n\nMau edit lagi atau lanjut?",
        parse_mode="Markdown",
        reply_markup=edit_or_continue_keyboard("single"),
    )
    return True


def format_split_bill_preview_line(parsed: dict) -> str:
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    if not split_bill:
        return ""

    total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share = float(split_bill.get("share_amount", 0) or 0)
    total_receivable = float(split_bill.get("total_receivable", 0) or 0)
    status = split_bill.get("status")

    if status == "paid":
        status_label = "sudah dibayar"
        receivable_display = 0
    elif status == "unpaid":
        status_label = "belum dibayar / masuk piutang"
        receivable_display = total_receivable
    else:
        status_label = "menunggu status"
        receivable_display = total_receivable

    return (
        f"🤝 Split: {status_label} | "
        f"total dibayar {format_rupiah(total)} | "
        f"bagian kamu {format_rupiah(share)} | "
        f"piutang {format_rupiah(receivable_display)}"
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
        f"👤 Subjek  : {parsed.get('subject') or '-'}",
        f"📝 Deskripsi: {parsed.get('description') or '-'}",
    ]

    split_preview = format_split_bill_preview_line(parsed)
    if split_preview:
        lines.append(split_preview)

    if parsed.get("catatan"):
        lines.append(f"🗒️ Catatan : {parsed.get('catatan')}")

    if parsed.get("tipe_pengeluaran"):
        lines.append(f"🏷️ Tipe    : {parsed.get('tipe_pengeluaran')}")

    lines.append(f"📅 Tanggal : {parsed.get('date') or '-'}")

    if parsed.get("account"):
        lines.append(f"🏦 Rekening: {parsed.get('account')}")

    if parsed.get("to_account"):
        lines.append(f"➡️ Ke Rekening: {parsed.get('to_account')}")

    account_summary = build_account_delta_summary_from_transaction_items([{"parsed": parsed}])
    if account_summary:
        lines.append(account_summary)

    return "\n".join(lines)


def build_batch_preview(parsed_items: list[dict]) -> str:
    """Buat preview untuk banyak transaksi sekaligus."""
    lines = [f"🧾 *Ditemukan {len(parsed_items)} transaksi:*\n"]

    total_expense = 0
    total_income = 0

    for i, item in enumerate(parsed_items, 1):
        parsed = item["parsed"]

        type_icon = {
            "expense": "❌",
            "income": "✅",
            "transfer": "🔄",
        }.get(parsed.get("type"), "❓")

        amount = float(parsed.get("amount", 0) or 0)

        if parsed.get("type") == "expense":
            total_expense += amount
        elif parsed.get("type") == "income":
            total_income += amount

        desc = parsed.get("description") or "-"
        category = parsed.get("category") or "-"
        account = parsed.get("account") or "-"
        subject = parsed.get("subject") or "-"
        spending_type = parsed.get("tipe_pengeluaran") or "-"

        date = parsed.get("date") or "-"

        lines.append(
            f"{i}. {type_icon} *{desc}*\n"
            f"   💰 {format_rupiah(amount)} | {category}\n"
            f"   📅 {date}\n"
            f"   👤 {subject} | 🏦 {account} | 🏷️ {spending_type}"
        )

        if parsed.get("catatan"):
            lines.append(f"   🗒️ {parsed.get('catatan')}")

    lines.append("\n*Ringkasan:*")
    lines.append(f"❌ Total Pengeluaran: *{format_rupiah(total_expense)}*")
    lines.append(f"✅ Total Pemasukan   : *{format_rupiah(total_income)}*")

    account_summary = build_account_delta_summary_from_transaction_items(parsed_items)
    if account_summary:
        lines.append(account_summary)

    return "\n".join(lines)


def strip_split_bill_phrase(text: str) -> str:
    clean = str(text or "")

    # Dipanggil setelah split bill terdeteksi, jadi aman membersihkan frasa
    # "bagi/dibagi ... sama ..." dari description. Description dari parser
    # sering sudah kehilangan angka pembagi, misalnya:
    # "Nasi Kuning Dibagi Sama Sapto".
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"
    name_chunk = r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{0,80}"

    clean = re.sub(
        rf"\b{split_word}\s*(?:jadi\s*)?\d*\s*(?:orang\s+)?{friend_marker}\s+{name_chunk}",
        " ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        rf"\b{friend_marker}\s+{name_chunk}\s+{split_word}\s*(?:jadi\s*)?\d*",
        " ",
        clean,
        flags=re.IGNORECASE,
    )
    # Support input tanpa marker "sama":
    # "Nasi kuning 22k dibagi 2 sapto".
    clean = re.sub(
        rf"\b{split_word}\s*(?:jadi\s*)?\d+\s*(?:orang\s+)?{name_chunk}",
        " ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(r"\s+", " ", clean).strip(" .,-")
    return clean or str(text or "").strip()


def split_split_bill_person_names(name_text: str) -> list[str]:
    """
    Ambil daftar nama teman dari frasa split bill.

    Contoh:
    - "Sapto" -> ["Sapto"]
    - "opik alpat sapto" -> ["Opik", "Alpat", "Sapto"]
    - "opik, alpat, dan sapto" -> ["Opik", "Alpat", "Sapto"]

    Catatan: untuk mode tanpa pemisah koma/dan, nama diasumsikan satu kata per orang.
    Ini sesuai gaya input user seperti: "bagi 4 sama opik alpat sapto".
    """
    clean = str(name_text or "").strip()

    # Stop sebelum frasa tanggal/status agar tidak ikut jadi nama.
    clean = re.split(
        r"\b(tanggal|tgl|tg|pada|date|kemarin|hari|minggu|bulan|udah|sudah|belum|dibayar|bayar|lunas|dari|ke)\b",
        clean,
        flags=re.IGNORECASE,
    )[0]

    clean = re.sub(r"[^A-Za-zÀ-ÿ,;&\s]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip(" ,;&")
    if not clean:
        return []

    # Kalau ada separator eksplisit, pakai itu.
    if re.search(r"[,;&]|\bdan\b|\band\b", clean, flags=re.IGNORECASE):
        raw_parts = re.split(r"\s*(?:,|;|&|\bdan\b|\band\b)\s*", clean, flags=re.IGNORECASE)
    else:
        # Tanpa separator, treat setiap token sebagai nama orang.
        raw_parts = clean.split()

    names = []
    seen = set()
    noise = {"sama", "ama", "dengan", "bareng", "dan", "and"}

    for part in raw_parts:
        part = re.sub(r"[^A-Za-zÀ-ÿ\s]", " ", str(part or ""))
        part = re.sub(r"\s+", " ", part).strip()
        if not part or part.lower() in noise:
            continue
        normalized = part.title()
        key = normalized.lower()
        if key not in seen:
            names.append(normalized)
            seen.add(key)

    return names


def clean_split_person_name(name: str) -> str:
    names = split_split_bill_person_names(name)
    return " ".join(names).title() if names else ""


def detect_split_bill(parsed: dict, raw: str) -> dict | None:
    """
    Deteksi input split bill sederhana.

    Contoh:
    - Ayam dcelup 26k bagi 2 sama Sapto
    - Tissue 10k bagi 4 sama opik alpat sapto

    Desain cashflow:
    - Transaksi utama tetap disimpan sebesar total yang kamu bayarkan.
    - Kalau teman belum bayar, dibuat piutang per orang sebesar amount / jumlah peserta
      TANPA cashflow tambahan.
    """
    if not parsed or parsed.get("type") != "expense":
        return None

    original_total = extract_split_bill_total_amount(raw)
    amount = float(original_total or parsed.get("amount", 0) or 0)
    if amount <= 0:
        return None

    text = str(raw or "")
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"
    name_chunk = r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s,;&]{0,80}"
    patterns = [
        # "dibagi 2 sama sapto"
        rf"\b{split_word}\s*(?:jadi\s*)?(\d+)\s*(?:orang)?\s+{friend_marker}\s+({name_chunk})",
        # "sama sapto dibagi 2"
        rf"\b{friend_marker}\s+({name_chunk})\s+{split_word}\s*(?:jadi\s*)?(\d+)",
        # "dibagi 2 sapto" tanpa marker sama/dengan.
        # Nama harus diawali huruf, jadi "dibagi 2 11-05-2026" tidak match.
        rf"\b{split_word}\s*(?:jadi\s*)?(\d+)\s*(?:orang)?\s+({name_chunk})",
    ]

    participants = None
    person_names = []

    for idx, pattern in enumerate(patterns):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        if idx in (0, 2):
            participants = int(match.group(1))
            person_names = split_split_bill_person_names(match.group(2))
        else:
            person_names = split_split_bill_person_names(match.group(1))
            participants = int(match.group(2))
        break

    if not participants or participants < 2 or not person_names:
        return None

    # Parser regex/LLM bisa saja sudah membagi "22k dibagi 2" menjadi 11k.
    # Setelah split bill valid, transaksi utama dikembalikan ke total yang dibayar,
    # sedangkan share/piutang dihitung terpisah. Jangan mutasi parsed kalau pola
    # split bill tidak valid, agar kasus gagal tidak tiba-tiba berubah nominal.
    parsed["amount"] = amount

    share_amount = amount / participants
    total_receivable = share_amount * len(person_names)

    # Bersihkan deskripsi/subject supaya tidak ikut menyimpan frasa
    # "bagi/dibagi 2 sama ...".
    desc = parsed.get("description") or ""
    clean_desc = strip_split_bill_phrase(desc)
    # Kalau parser regex sudah menghapus frasa "dibagi 2" lebih dulu, nama teman
    # bisa tersisa di akhir description, misalnya "Nasi Kuning Sapto".
    # Setelah split_bill valid, buang nama teman dari ujung description/subject.
    for person in person_names:
        clean_desc = re.sub(rf"\b{re.escape(person)}\b\s*$", "", clean_desc, flags=re.IGNORECASE).strip(" .,-")
    parsed["description"] = clean_desc

    subject = parsed.get("subject") or ""
    if subject:
        clean_subject = strip_split_bill_phrase(subject)
        for person in person_names:
            clean_subject = re.sub(rf"\b{re.escape(person)}\b\s*$", "", clean_subject, flags=re.IGNORECASE).strip(" .,-")
        # Subject biasanya mengikuti description. Kalau masih mengandung kata split,
        # atau nama teman tersisa di ujung, pakai versi bersih agar output/sheet
        # tidak menjadi "Nasi Kuning Sapto".
        if clean_subject != subject or re.search(split_word, subject, flags=re.IGNORECASE):
            parsed["subject"] = clean_subject or clean_desc

    return {
        "person_name": " ".join(person_names),  # backward compatibility
        "person_names": person_names,
        "participants": participants,
        "share_amount": share_amount,
        "total_receivable": total_receivable,
        "total_amount": amount,
        "status": None,  # paid / unpaid
    }


def attach_split_bill_if_any(parsed: dict, raw: str) -> dict:
    split_bill = detect_split_bill(parsed, raw)
    if split_bill:
        parsed["split_bill"] = split_bill
    return parsed


def split_bill_needs_decision(parsed: dict) -> bool:
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    return bool(split_bill) and not split_bill.get("status")


def mixed_split_bill_needs_decision(mixed_items: list[dict]) -> bool:
    for item in mixed_items or []:
        if item.get("kind") == "transaction" and split_bill_needs_decision(item.get("parsed", {})):
            return True
    return False


def split_bill_keyboard(scope: str = "single", item_index: int | None = None) -> InlineKeyboardMarkup:
    """Keyboard keputusan split bill.

    Untuk mixed/bulk, callback_data membawa index item split bill yang sedang
    ditampilkan. Ini membuat callback idempotent: jika user double-click atau
    Telegram mengirim callback lama lagi, klik lama tidak akan diam-diam
    diterapkan ke split bill berikutnya.
    """
    suffix = f":{item_index}" if item_index is not None else ""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Sudah dibayar", callback_data=f"split:paid:{scope}{suffix}"),
            InlineKeyboardButton("🟢 Belum, masuk piutang", callback_data=f"split:unpaid:{scope}{suffix}"),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{scope}")],
    ])


def mixed_split_bill_keyboard(mixed_items: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard split bill mixed dengan index item aktif di callback_data."""
    current_index = get_next_mixed_split_bill_index(mixed_items)
    return split_bill_keyboard("mixed", current_index)


def build_split_bill_prompt_from_parsed(parsed: dict) -> str:
    split_bill = parsed.get("split_bill", {}) or {}
    person_names = split_bill.get("person_names") or [split_bill.get("person_name", "-")]
    participants = int(split_bill.get("participants", 2) or 2)
    total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share = float(split_bill.get("share_amount", 0) or 0)
    total_receivable = float(split_bill.get("total_receivable", share * len(person_names)) or 0)
    friend_text = ", ".join(str(p) for p in person_names if p)

    return (
        "🤝 *Split bill terdeteksi*\n\n"
        f"📝 Item: *{md_safe(parsed.get('description') or '-')}*\n"
        f"💰 Total dibayar: *{format_rupiah(total)}*\n"
        f"👥 Dibagi: *{participants} orang*\n"
        f"👤 Teman: *{md_safe(friend_text)}*\n"
        f"📌 Bagian kamu/per orang: *{format_rupiah(share)}*\n"
        f"📌 Total piutang jika belum dibayar: *{format_rupiah(total_receivable)}*\n\n"
        f"{md_safe(friend_text)} sudah bayar bagian mereka?\n"
        "Kalau *sudah*, transaksi disimpan sebesar bagian kamu saja.\n"
        "Kalau *belum*, transaksi disimpan sebesar total yang kamu talangi dan bagian teman masuk piutang."
    )


def build_mixed_split_bill_prompt(mixed_items: list[dict]) -> str:
    split_items = [
        item for item in mixed_items or []
        if item.get("kind") == "transaction" and split_bill_needs_decision(item.get("parsed", {}))
    ]

    lines = [f"🤝 *Split bill terdeteksi di {len(split_items)} item*\n"]

    for i, item in enumerate(split_items, 1):
        parsed = item["parsed"]
        split_bill = parsed.get("split_bill", {}) or {}
        person_names = split_bill.get("person_names") or [split_bill.get("person_name", "-")]
        total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
        share = float(split_bill.get("share_amount", 0) or 0)
        total_receivable = float(split_bill.get("total_receivable", share * len(person_names)) or 0)
        friend_text = ", ".join(str(p) for p in person_names if p)
        lines.append(
            f"{i}. {md_safe(parsed.get('description') or '-')} — "
            f"total *{format_rupiah(total)}*, bagian kamu *{format_rupiah(share)}*, "
            f"{md_safe(friend_text)}: *{format_rupiah(total_receivable)}*"
        )

    lines.append(
        "\nApakah bagian teman-teman di item ini sudah dibayar?\n"
        "Pilih *Sudah dibayar* kalau transaksi cukup disimpan sebesar bagian kamu.\n"
        "Pilih *Belum* kalau kamu menalangi totalnya dan bagian teman otomatis masuk piutang."
    )
    return "\n".join(lines)


def get_mixed_split_bill_indexes(mixed_items: list[dict]) -> list[int]:
    """Return index item transaksi mixed yang memiliki split bill."""
    indexes = []
    for idx, item in enumerate(mixed_items or []):
        if item.get("kind") != "transaction":
            continue
        parsed = item.get("parsed", {})
        if isinstance(parsed, dict) and parsed.get("split_bill"):
            indexes.append(idx)
    return indexes


def get_next_mixed_split_bill_index(mixed_items: list[dict]) -> int | None:
    """Return index split bill pertama yang belum dipilih paid/unpaid."""
    for idx in get_mixed_split_bill_indexes(mixed_items):
        parsed = mixed_items[idx].get("parsed", {})
        if split_bill_needs_decision(parsed):
            return idx
    return None


def build_mixed_split_bill_queue_prompt(mixed_items: list[dict]) -> str:
    """
    Prompt split bill untuk bulk input, tapi ditanya satu-per-satu.

    Ini penting karena dalam satu bulk input bisa ada split bill yang sudah dibayar
    dan split bill lain yang belum dibayar. Jadi tombol paid/unpaid hanya berlaku
    untuk item yang sedang ditampilkan, bukan semua split bill sekaligus.
    """
    split_indexes = get_mixed_split_bill_indexes(mixed_items)
    current_index = get_next_mixed_split_bill_index(mixed_items)

    if current_index is None:
        return build_mixed_split_bill_queue_prompt(mixed_items)

    current_pos = split_indexes.index(current_index) + 1 if current_index in split_indexes else 1
    total_split = len(split_indexes)
    parsed = mixed_items[current_index].get("parsed", {})
    split_bill = parsed.get("split_bill", {}) or {}
    person_names = split_bill.get("person_names") or [split_bill.get("person_name", "-")]
    participants = int(split_bill.get("participants", 2) or 2)
    total = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share = float(split_bill.get("share_amount", 0) or 0)
    total_receivable = float(split_bill.get("total_receivable", share * len(person_names)) or 0)
    friend_text = ", ".join(str(p) for p in person_names if p)

    return (
        f"🤝 *Split bill {current_pos}/{total_split}*\n\n"
        f"📝 Item: *{md_safe(parsed.get('description') or '-')}*\n"
        f"💰 Total dibayar: *{format_rupiah(total)}*\n"
        f"👥 Dibagi: *{participants} orang*\n"
        f"👤 Teman: *{md_safe(friend_text)}*\n"
        f"📌 Bagian kamu/per orang: *{format_rupiah(share)}*\n"
        f"📌 Total piutang jika belum dibayar: *{format_rupiah(total_receivable)}*\n\n"
        f"{md_safe(friend_text)} sudah bayar bagian untuk item ini?\n"
        "Pilihan ini *hanya berlaku untuk item ini*. Setelah dijawab, saya lanjut ke split bill berikutnya."
    )


def apply_split_bill_decision_to_current_mixed(mixed_items: list[dict], status: str) -> tuple[list[dict], int | None]:
    """Terapkan paid/unpaid hanya ke split bill mixed yang sedang aktif."""
    current_index = get_next_mixed_split_bill_index(mixed_items)
    if current_index is None:
        return mixed_items, None
    mixed_items, decided_index, _ = apply_split_bill_decision_to_mixed_index(mixed_items, current_index, status)
    return mixed_items, decided_index


def apply_split_bill_decision_to_mixed_index(mixed_items: list[dict], item_index: int, status: str) -> tuple[list[dict], int | None, str]:
    """Terapkan paid/unpaid ke index split bill tertentu.

    Return: (mixed_items, decided_index, result_status)
    result_status:
    - applied: keputusan baru berhasil diterapkan
    - already_decided: callback duplicate/stale untuk item yang sudah diputuskan
    - invalid: index tidak valid atau item bukan split bill
    """
    if item_index is None or item_index < 0 or item_index >= len(mixed_items or []):
        return mixed_items, None, "invalid"

    item = mixed_items[item_index]
    if item.get("kind") != "transaction":
        return mixed_items, None, "invalid"

    parsed = item.get("parsed", {})
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    if not split_bill:
        return mixed_items, None, "invalid"

    if split_bill.get("status"):
        return mixed_items, item_index, "already_decided"

    apply_split_bill_decision_to_parsed(parsed, status)
    item["parsed"] = parsed
    mixed_items[item_index] = item
    return mixed_items, item_index, "applied"


def apply_split_bill_decision_to_parsed(parsed: dict, status: str) -> dict:
    """
    Terapkan keputusan split bill ke transaksi.

    - paid: teman sudah bayar, jadi transaksi yang disimpan cukup bagian user.
    - unpaid: user menalangi total dulu, jadi transaksi tetap total tagihan
      dan nanti dibuat piutang tanpa cashflow tambahan.
    """
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    if not split_bill:
        return parsed

    split_bill["status"] = status

    total_amount = float(split_bill.get("total_amount", parsed.get("amount", 0)) or 0)
    share_amount = float(split_bill.get("share_amount", 0) or 0)

    if status == "paid" and share_amount > 0:
        parsed["amount"] = share_amount
    elif status == "unpaid" and total_amount > 0:
        parsed["amount"] = total_amount

    return parsed


def apply_split_bill_decision_to_mixed(mixed_items: list[dict], status: str) -> list[dict]:
    for item in mixed_items or []:
        if item.get("kind") != "transaction":
            continue
        parsed = item.get("parsed", {})
        if parsed.get("split_bill"):
            apply_split_bill_decision_to_parsed(parsed, status)
    return mixed_items


def create_split_bill_debt(parsed: dict, raw: str = "", source_transaction_id: str = "") -> dict | None:
    split_bill = parsed.get("split_bill") if isinstance(parsed, dict) else None
    if not split_bill or split_bill.get("status") != "unpaid":
        return None

    person_names = split_bill.get("person_names") or [split_bill.get("person_name")]
    person_names = [str(p).strip().title() for p in person_names if str(p or "").strip()]
    share_amount = float(split_bill.get("share_amount", 0) or 0)
    if not person_names or share_amount <= 0:
        return None

    desc = f"Split bill: {parsed.get('description') or raw or '-'}"
    created = []
    failed = []

    for person in person_names:
        result = add_debt(
            "receivable",
            person,
            share_amount,
            desc,
            source_transaction_id=source_transaction_id,
            cashflow_mode="debt_only",
            fronting_mode="split_bill",
        )
        if result and result.get("success"):
            created.append({
                "person_name": person,
                "remaining": share_amount,
                "debt_id": result.get("debt_id"),
            })
        else:
            failed.append({
                "person_name": person,
                "message": (result or {}).get("message", "Gagal membuat piutang."),
            })

    if failed and not created:
        return {
            "success": False,
            "message": "; ".join(f"{x['person_name']}: {x['message']}" for x in failed),
            "created": created,
            "failed": failed,
        }

    return {
        "success": True,
        "person_name": ", ".join(x["person_name"] for x in created),
        "remaining": sum(float(x["remaining"] or 0) for x in created),
        "created": created,
        "failed": failed,
        "message": "ok" if not failed else "; ".join(f"{x['person_name']}: {x['message']}" for x in failed),
    }


def format_split_debt_result_lines(debt_result: dict) -> list[str]:
    """Format hasil create_split_bill_debt untuk output Telegram."""
    lines = []
    for item in (debt_result or {}).get("created", []) or []:
        lines.append(
            f"• {md_safe(item.get('person_name'))}: *{format_rupiah(float(item.get('remaining', 0) or 0))}*"
        )
    return lines


def summarize_saved_transaction_items(items: list[dict]) -> dict:
    total_expense = 0.0
    total_income = 0.0
    total_transfer = 0.0
    for item in items or []:
        parsed = item.get("parsed", {})
        amount = float(parsed.get("amount", 0) or 0)
        if parsed.get("type") == "expense":
            total_expense += amount
        elif parsed.get("type") == "income":
            total_income += amount
        elif parsed.get("type") == "transfer":
            total_transfer += amount
    return {
        "expense": total_expense,
        "income": total_income,
        "transfer": total_transfer,
        "net": total_income - total_expense,
    }


def append_saved_summary_lines(lines: list[str], items: list[dict], title: str = "Ringkasan tersimpan"):
    summary = summarize_saved_transaction_items(items)
    lines.append(f"\n📊 *{title}:*")
    lines.append(f"❌ Pengeluaran: *{format_rupiah(summary['expense'])}*")
    lines.append(f"✅ Pemasukan : *{format_rupiah(summary['income'])}*")
    if summary["transfer"]:
        lines.append(f"🔄 Transfer  : *{format_rupiah(summary['transfer'])}*")
    lines.append(f"📌 Net       : *{format_rupiah(summary['net'])}*")

def build_debt_cashflow_transaction(
    debt_parsed: dict,
    account: str,
    debt_type_for_payment: str | None = None,
) -> dict:
    """
    Ubah aktivitas utang/piutang menjadi transaksi cashflow.
    """
    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or ""
    amount = debt_parsed.get("amount") or 0
    raw = debt_parsed.get("raw_input") or ""
    transaction_date = debt_parsed.get("date") or datetime.now().strftime("%Y-%m-%d")
    hutang_id = debt_parsed.get("hutang_id") or debt_parsed.get("debt_id") or debt_parsed.get("target_debt_id") or ""
    tipe_hutang = debt_parsed.get("tipe_hutang") or ""
    if not tipe_hutang:
        if intent == "add_payable" or debt_type_for_payment == "payable":
            tipe_hutang = "utang"
        elif intent == "add_receivable" or debt_type_for_payment == "receivable":
            tipe_hutang = "piutang"


    if intent == "add_receivable":
        return {
            "type": "expense",
            "amount": amount,
            "category": "Piutang Diberikan",
            "account": account,
            "to_account": None,
            "subject": person,
            "description": f"Pinjaman ke {person}",
            "catatan": raw,
            "tipe_pengeluaran": "",
            "date": transaction_date,
            "hutang_id": hutang_id,
            "tipe_hutang": tipe_hutang,
            "parsed_by": "debt",
        }

    if intent == "add_payable":
        return {
            "type": "income",
            "amount": amount,
            "category": "Penerimaan Utang",
            "account": account,
            "to_account": None,
            "subject": person,
            "description": f"Pinjaman dari {person}",
            "catatan": raw,
            "tipe_pengeluaran": "",
            "date": transaction_date,
            "hutang_id": hutang_id,
            "tipe_hutang": tipe_hutang,
            "parsed_by": "debt",
        }

    if intent == "add_payment":
        if debt_type_for_payment == "payable":
            return {
                "type": "expense",
                "amount": amount,
                "category": "Bayar Utang",
                "account": account,
                "to_account": None,
                "subject": person,
                "description": f"Bayar utang ke {person}",
                "catatan": raw,
                "tipe_pengeluaran": "",
                "date": transaction_date,
                "hutang_id": hutang_id,
                "tipe_hutang": tipe_hutang,
                "parsed_by": "debt",
            }

        if debt_type_for_payment == "receivable":
            return {
                "type": "income",
                "amount": amount,
                "category": "Pembayaran Piutang",
                "account": account,
                "to_account": None,
                "subject": person,
                "description": f"Pembayaran piutang dari {person}",
                "catatan": raw,
                "tipe_pengeluaran": "",
                "date": transaction_date,
                "hutang_id": hutang_id,
                "tipe_hutang": tipe_hutang,
                "parsed_by": "debt",
            }

    return {
        "type": "pending",
        "amount": 0,
        "category": None,
        "account": account,
        "to_account": None,
        "subject": person,
        "description": "Debt cashflow tidak valid",
        "catatan": raw,
        "tipe_pengeluaran": "",
        "date": transaction_date,
        "hutang_id": hutang_id,
        "tipe_hutang": tipe_hutang,
        "parsed_by": "debt",
    }


def debt_uses_cashflow(debt_parsed: dict) -> bool:
    """Return True kalau aktivitas debt perlu dicatat juga sebagai cashflow."""
    return str(debt_parsed.get("cashflow_mode") or "cashflow") != "debt_only"


def build_debt_only_confirm_preview(debt_parsed: dict) -> str:
    """Preview untuk talangan/ditalangin yang hanya mengubah sheet debts."""
    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or "-"
    amount = debt_parsed.get("amount") or 0
    raw = debt_parsed.get("raw_input") or "-"
    fronting_mode = debt_parsed.get("fronting_mode") or "debt_only"

    if intent == "add_payable":
        title = "🟠 *Ditalangin / Utang Tanpa Cashflow*"
        debt_effect = f"Anda punya utang ke {md_safe(person)}."
    elif intent == "add_receivable":
        title = "🟢 *Talangin / Piutang Tanpa Cashflow*"
        debt_effect = f"{md_safe(person)} punya utang ke Anda."
    else:
        title = "💸 *Debt Tanpa Cashflow*"
        debt_effect = "Debt dicatat tanpa transaksi kas."

    return (
        f"{title}\n\n"
        f"👤 Subjek : {md_safe(person)}\n"
        f"💰 Nominal: {format_rupiah(amount)}\n"
        f"📝 Input  : `{md_safe(raw)}`\n\n"
        f"*Efek Debt:*\n"
        f"{debt_effect}\n\n"
        f"*Efek Transactions:*\n"
        f"Tidak ada cash in/cash out sekarang. Tidak akan menambah pemasukan/pengeluaran dulu.\n"
        f"Mode: `{md_safe(fronting_mode)}`\n\n"
        f"Simpan debt tanpa cashflow ini?"
    )


def build_debt_account_prompt(debt_parsed: dict) -> str:
    """Preview debt sebelum memilih rekening."""
    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or "-"
    amount = debt_parsed.get("amount") or 0

    if intent == "add_receivable":
        title = "🟢 *Piutang Baru*"
        desc = f"{md_safe(person)} meminjam uang dari Anda."
        effect = "Cashflow: pengeluaran, kategori Piutang Diberikan"

    elif intent == "add_payable":
        title = "🔴 *Utang Baru*"
        desc = f"Anda punya utang ke {md_safe(person)}."
        effect = "Cashflow: pemasukan, kategori Penerimaan Utang"

    elif intent == "add_payment":
        title = "💸 *Pembayaran Utang/Piutang*"
        desc = f"Pembayaran terkait {person}."
        effect = "Cashflow akan mengikuti posisi aktif di sheet debts"

    else:
        title = "❓ *Debt*"
        desc = "Input debt terdeteksi."
        effect = "-"

    return (
        f"{title}\n\n"
        f"👤 Subjek : {md_safe(person)}\n"
        f"💰 Nominal: {format_rupiah(amount)}\n"
        f"📝 Detail : {desc}\n"
        f"📌 Efek  : {effect}\n\n"
        f"💳 Pilih rekening cashflow:"
    )

def build_debt_confirm_preview(
    debt_parsed: dict,
    account: str,
    debt_type_for_payment: str | None = None,
) -> str:
    """Preview debt setelah rekening dipilih, sebelum disimpan."""
    transaction_parsed = build_debt_cashflow_transaction(
        debt_parsed,
        account,
        debt_type_for_payment=debt_type_for_payment,
    )

    intent = debt_parsed.get("intent")
    person = debt_parsed.get("person_name") or "-"
    amount = debt_parsed.get("amount") or 0
    raw = debt_parsed.get("raw_input") or "-"

    if intent == "add_receivable":
        title = "🟢 *Piutang Baru*"
        debt_effect = f"{md_safe(person)} meminjam uang dari Anda."
    elif intent == "add_payable":
        title = "🔴 *Utang Baru*"
        debt_effect = f"Anda meminjam / punya utang ke {md_safe(person)}."
    elif intent == "add_payment":
        title = "💸 *Pembayaran Utang/Piutang*"
        debt_effect = f"Pembayaran terkait saldo aktif dengan {md_safe(person)}."
    else:
        title = "❓ *Debt*"
        debt_effect = "-"

    cashflow_type = {
        "expense": "❌ Cash Out / Pengeluaran",
        "income": "✅ Cash In / Pemasukan",
        "transfer": "🔄 Transfer",
    }.get(transaction_parsed.get("type"), "❓")

    return (
        f"{title}\n\n"
        f"👤 Subjek : {md_safe(person)}\n"
        f"💰 Nominal: {format_rupiah(amount)}\n"
        f"🏦 Rekening: {md_safe(account)}\n"
        f"📝 Input  : `{md_safe(raw)}`\n\n"
        f"*Efek Debt:*\n"
        f"{debt_effect}\n\n"
        f"*Efek Transactions:*\n"
        f"{cashflow_type}\n"
        f"📁 Kategori: {md_safe(transaction_parsed.get('category') or '-')}\n"
        f"📝 Deskripsi: {md_safe(transaction_parsed.get('description') or '-')}\n\n"
        f"Simpan utang/piutang ini?"
    )

def build_debt_batch_confirm_preview(
    debt_items: list[dict],
    account: str,
) -> str:
    """Preview batch debt setelah rekening dipilih, sebelum disimpan."""
    lines = ["🧾 *Preview Batch Utang/Piutang*\n"]

    total_cash_in = 0
    total_cash_out = 0

    for i, item in enumerate(debt_items, 1):
        parsed = item["parsed"]
        intent = parsed.get("intent")
        person = parsed.get("person_name") or "-"
        amount = float(parsed.get("amount", 0) or 0)
        raw = item.get("raw") or parsed.get("raw_input") or "-"

        debt_type_for_payment = parsed.get("debt_type_for_payment")
        transaction_parsed = build_debt_cashflow_transaction(
            parsed,
            account,
            debt_type_for_payment=debt_type_for_payment,
        )

        txn_type = transaction_parsed.get("type")
        category = transaction_parsed.get("category") or "-"

        if txn_type == "income":
            cashflow_label = "✅ Cash In"
            total_cash_in += amount
        elif txn_type == "expense":
            cashflow_label = "❌ Cash Out"
            total_cash_out += amount
        else:
            cashflow_label = "❓ Cashflow belum pasti"

        if intent == "add_receivable":
            debt_label = "🟢 Piutang Baru"
        elif intent == "add_payable":
            debt_label = "🔴 Utang Baru"
        elif intent == "add_payment":
            debt_label = "💸 Pembayaran"
        else:
            debt_label = "❓ Debt"

        lines.append(
            f"{i}. {debt_label}\n"
            f"   👤 Subjek : {person}\n"
            f"   💰 Nominal: {format_rupiah(amount)}\n"
            f"   🏦 Rekening: {account}\n"
            f"   📁 Kategori: {category}\n"
            f"   📌 Efek: {cashflow_label}\n"
            f"   📝 Input: `{raw}`"
        )

    lines.append("\n*Ringkasan Cashflow:*")
    lines.append(f"✅ Total Cash In : *{format_rupiah(total_cash_in)}*")
    lines.append(f"❌ Total Cash Out: *{format_rupiah(total_cash_out)}*")
    lines.append("\nSimpan semua utang/piutang ini?")

    return "\n".join(lines)

def build_debt_batch_account_prompt(debt_items: list[dict]) -> str:
    """Preview batch debt sebelum memilih rekening."""
    lines = [f"🧾 *Ditemukan {len(debt_items)} input utang/piutang:*\n"]

    total_cash_in = 0
    total_cash_out = 0

    for i, item in enumerate(debt_items, 1):
        parsed = item["parsed"]
        intent = parsed.get("intent")
        person = parsed.get("person_name") or "-"
        amount = float(parsed.get("amount", 0) or 0)

        if intent == "add_receivable":
            label = "🟢 Piutang Baru"
            effect = "cash out"
            total_cash_out += amount

        elif intent == "add_payable":
            label = "🔴 Utang Baru"
            effect = "cash in"
            total_cash_in += amount

        elif intent == "add_payment":
            label = "💸 Pembayaran"
            effect = "mengikuti posisi debt aktif"

        else:
            label = "❓ Debt"
            effect = "-"

        lines.append(
            f"{i}. {label}\n"
            f"   👤 {person}\n"
            f"   💰 {format_rupiah(amount)}\n"
            f"   📌 {effect}"
        )

    lines.append("\n*Estimasi cashflow awal:*")
    lines.append(f"✅ Cash In : *{format_rupiah(total_cash_in)}*")
    lines.append(f"❌ Cash Out: *{format_rupiah(total_cash_out)}*")
    lines.append("\n💳 Pilih rekening cashflow untuk semua item:")

    return "\n".join(lines)


# ── Command Handlers ──────────────────────────────────────────────────────────

