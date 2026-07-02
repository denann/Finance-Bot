"""Local command router and typo resolver for commands and natural read-only inputs."""

# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *

def build_gemini_low_confidence_text(router_result: dict) -> str:
    """Build the data structure or message text for gemini low confidence text."""
    intent = router_result.get("intent", "unknown")
    confidence = float(router_result.get("confidence", 0) or 0)
    explanation = router_result.get("explanation", "")

    return (
        "🤔 Saya agak paham maksudnya, tapi belum cukup yakin.\n\n"
        f"Intent terbaca: `{intent}`\n"
        f"Confidence: `{confidence:.2f}`\n"
        f"Catatan: {explanation or '-'}\n\n"
        "Coba pakai command eksplisit, contoh:\n"
        "`/last today`\n"
        "`/delete_txn 2`\n"
        "`/edit_txn 2 amount=15000`\n"
        "`/cari kopi`"
    )


def build_gemini_fallback_text() -> str:
    """Build the data structure or message text for gemini fallback text."""
    return (
        "🤔 Maaf, saya belum bisa memahami maksud input tersebut.\n\n"
        "Coba format transaksi seperti:\n"
        "`beli kopi 25rb`\n"
        "`gaji masuk 8 juta`\n"
        "`hutang ke Budi 500rb`\n"
        "`Budi minjem 300k`\n"
        "`bayar hutang Joko 200k`\n\n"
        "Atau pakai command:\n"
        "`/last today`\n"
        "`/saldo`\n"
        "`/budget`\n"
        "`/hutang`\n"
        "`/help`"
    )


def router_args_to_last_filter(args: dict) -> tuple[int, str | None, str | None, str]:
    """Helper for router args to last filter in the Telegram bot flow."""
    period = args.get("period")
    month = args.get("month")
    limit = args.get("limit")

    try:
        limit = int(limit) if limit else 10
    except Exception:
        limit = 10

    limit = min(max(limit, 1), 30)

    if month:
        month = str(month).strip()
        if re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", month):
            return limit, None, month, f"Transaksi {month}"

    if period == "today":
        return limit, "today", None, "Transaksi Hari Ini"

    if period == "week":
        return limit, "week", None, "Transaksi Minggu Ini"

    if period == "month":
        return limit, "month", None, "Transaksi Bulan Ini"

    return limit, None, None, "Transaksi Terakhir"


def extract_edit_updates_from_router(args: dict) -> dict:
    """Extract the important part of the input for edit updates from router."""
    updates = args.get("updates", {}) or {}

    if not isinstance(updates, dict):
        return {}

    cleaned = {}

    for key, value in updates.items():
        if value is None:
            continue

        cleaned[str(key).strip()] = str(value).strip()

    return cleaned

def format_rupiah(amount: float) -> str:
    """Format rupiah into readable text."""
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")

def md_safe(value) -> str:
    """Helper for md safe in the Telegram bot flow."""
    return escape_markdown(str(value or "-"), version=1)

KNOWN_COMMANDS = {
    "start": {
        "description": "Mulai bot dan lihat ringkasan fitur.",
        "destructive": False,
    },
    "help": {
        "description": "Lihat panduan lengkap penggunaan bot.",
        "destructive": False,
    },
    "examples": {
        "description": "Lihat contoh input cepat untuk mencoba bot.",
        "destructive": False,
    },
    "contoh": {
        "description": "Alias /examples untuk contoh input cepat.",
        "destructive": False,
    },
    "saldo": {
        "description": "Lihat saldo semua rekening.",
        "destructive": False,
    },
    "rekening": {
        "description": "Lihat transaksi lengkap rekening tertentu.",
        "destructive": False,
    },
    "harian": {
        "description": "Lihat ringkasan transaksi hari ini.",
        "destructive": False,
    },
    "mingguan": {
        "description": "Lihat ringkasan transaksi minggu ini.",
        "destructive": False,
    },
    "bulanan": {
        "description": "Lihat ringkasan transaksi bulan ini.",
        "destructive": False,
    },
    "budget": {
        "description": "Lihat budget bulan berjalan atau bulan tertentu.",
        "destructive": False,
    },
    "budget_history": {
        "description": "Lihat daftar bulan yang punya data budget.",
        "destructive": False,
    },
    "pending": {
        "description": "Lihat pending expense/rencana pengeluaran aktif.",
        "destructive": False,
    },
    "pending_add": {
        "description": "Tambah pending expense/rencana pengeluaran.",
        "destructive": False,
    },
    "pending_paid": {
        "description": "Ubah pending expense menjadi transaksi aktual.",
        "destructive": True,
    },
    "pending_cancel": {
        "description": "Batalkan pending expense.",
        "destructive": True,
    },
    "hutang": {
        "description": "Lihat utang/piutang aktif.",
        "destructive": False,
    },
    "ringkasan_hutang": {
        "description": "Buat rekap hutang-piutang shareable tanpa ID/command internal.",
        "destructive": False,
    },
    "cari": {
        "description": "Cari transaksi berdasarkan keyword.",
        "destructive": False,
    },
    "last": {
        "description": "Lihat transaksi terakhir dengan filter.",
        "destructive": False,
    },
    "transaksi": {
        "description": "Lihat transaksi lengkap untuk hari/minggu/bulan/rekening tertentu.",
        "destructive": False,
    },
    "export": {
        "description": "Export data transaksi untuk backup atau analisis lanjutan.",
        "destructive": False,
    },
    "download_data": {
        "description": "Alias export data transaksi.",
        "destructive": False,
    },
    "delete_txn": {
        "description": "Hapus transaksi dari hasil /last atau berdasarkan ID.",
        "destructive": True,
    },
    "edit_txn": {
        "description": "Edit transaksi dari hasil /last atau berdasarkan ID.",
        "destructive": True,
    },
    "debt_void": {
        "description": "Batalkan utang/piutang salah input secara aman.",
        "destructive": True,
    },
    "debt_edit": {
        "description": "Edit utang/piutang aktif dari hasil /hutang.",
        "destructive": True,
    },
    "insight": {
        "description": "Buat insight/narasi finansial dengan Gemini.",
        "destructive": False,
    },
    "ask": {
        "description": "Tanya jawab finansial natural berbasis data sheet.",
        "destructive": False,
    },
    "audit": {
        "description": "Cek anomali dan kualitas data transaksi.",
        "destructive": False,
    },
    "coach": {
        "description": "Saran finansial ringan berbasis data.",
        "destructive": False,
    },
    "assets": {
        "description": "Lihat daftar aset aktif.",
        "destructive": False,
    },
    "networth": {
        "description": "Lihat kekayaan bersih.",
        "destructive": False,
    },
}


COMMAND_ALIASES = {
    "examples": "examples",
    "contoh": "examples",
    "sample": "examples",
    "export": "export",
    "download_data": "download_data",
    "download": "download_data",
    # laporan
    "hari": "harian",
    "hariini": "harian",
    "harian": "harian",

    "minggu": "mingguan",
    "minguan": "mingguan",
    "mingguang": "mingguan",
    "mingguan": "mingguan",

    "bulan": "bulanan",
    "bulanan": "bulanan",

    # budget
    "buget": "budget",
    "budjet": "budget",
    "budged": "budget",
    "bujet": "budget",
    "budget": "budget",

    "budgethistory": "budget_history",
    "budget_history": "budget_history",
    "budget_histori": "budget_history",
    "budgethistori": "budget_history",
    "histori_budget": "budget_history",

    # pending expense
    "pending": "pending",
    "rencana": "pending_add",
    "planning": "pending_add",
    "planned": "pending",
    "pending_add": "pending_add",
    "tambah_pending": "pending_add",
    "pending_paid": "pending_paid",
    "bayar_pending": "pending_paid",
    "pending_cancel": "pending_cancel",
    "cancel_pending": "pending_cancel",

    # hutang
    "utang": "hutang",
    "hutang": "hutang",
    "ringkasan_hutang": "ringkasan_hutang",
    "rekap_hutang": "ringkasan_hutang",
    "void_hutang": "debt_void",
    "void_utang": "debt_void",
    "void_piutang": "debt_void",
    "debt_void": "debt_void",

    # account
    "rekening": "rekening",
    "rek": "rekening",
    "akun": "rekening",
    "account": "rekening",

    # last/history
    "last": "last",
    "terakhir": "last",
    "histori": "last",
    "history": "last",
    "riwayat": "last",
    "transaksi": "transaksi",
    "mutasi": "transaksi",
    "riwayat_transaksi": "transaksi",

    # delete
    "delete": "delete_txn",
    "delete_txn": "delete_txn",
    "detele": "delete_txn",
    "delet": "delete_txn",
    "del": "delete_txn",
    "hapus": "delete_txn",
    "hapus_txn": "delete_txn",
    "hapus_transaksi": "delete_txn",

    # edit
    "edit": "edit_txn",
    "edit_txn": "edit_txn",
    "edt": "edit_txn",
    "ubah": "edit_txn",
    "ubah_txn": "edit_txn",
    "ubah_transaksi": "edit_txn",

    # search
    "search": "cari",
    "find": "cari",
    "carii": "cari",
    "cari": "cari",

    # AI routing note: keep transaction/debt inputs away from insight routing when they contain amounts.
    "insight": "insight",
    "analisis": "insight",
    "analisa": "insight",
    "narasi": "insight",
    "ask": "ask",
    "tanya": "ask",
    "audit": "audit",
    "anomali": "audit",
    "coach": "coach",
    "saran": "coach",

    # net worth
    "aset": "assets",
    "asset": "assets",
    "assets": "assets",
    "networth": "networth",
    "net_worth": "networth",
    "kekayaan": "networth",
}


UNAVAILABLE_COMMANDS = {
    "kuartalan": (
        "Fitur laporan kuartalan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    ),
    "quarter": (
        "Fitur laporan kuartalan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    ),
    "triwulan": (
        "Fitur laporan triwulan/kuartalan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    ),
    "tahunan": (
        "Fitur laporan tahunan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    ),
    "yearly": (
        "Fitur laporan tahunan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    ),
}


SIMILARITY_THRESHOLD = 0.78
SIMILARITY_MARGIN = 0.12


def clean_command_token(command_text: str) -> str:
    """Clean and standardize clean command token."""
    clean = str(command_text or "").strip().lower()
    clean = clean.lstrip("/")
    clean = clean.split("@")[0]
    clean = clean.strip()

    return clean


def command_description(command_name: str) -> str:
    """Helper for command description in the Telegram bot flow."""
    info = KNOWN_COMMANDS.get(command_name, {})
    return info.get("description", "")


def is_destructive_command(command_name: str) -> bool:
    """Check a boolean condition for is destructive command."""
    info = KNOWN_COMMANDS.get(command_name, {})
    return bool(info.get("destructive", False))


def similarity_score(a: str, b: str) -> float:
    """Helper for similarity score in the Telegram bot flow."""
    return SequenceMatcher(None, a, b).ratio()


def get_similarity_candidates(clean_command: str) -> list[dict]:
    """Retrieve data needed for similarity candidates."""
    candidates = []

    for command_name in KNOWN_COMMANDS.keys():
        score = similarity_score(clean_command, command_name)
        candidates.append({
            "command": command_name,
            "score": score,
        })

    candidates = sorted(
        candidates,
        key=lambda x: x["score"],
        reverse=True,
    )

    return candidates


def resolve_command_local(command_text: str) -> dict:
    """Resolve the final value for command local from possible inputs."""
    clean = clean_command_token(command_text)

    if not clean:
        return {
            "status": "unresolved",
            "input": clean,
            "command": None,
            "message": "Command kosong.",
            "score": None,
            "second_score": None,
        }

    # Implementation note for this project-specific finance flow.
    if clean in KNOWN_COMMANDS:
        return {
            "status": "exact",
            "input": clean,
            "command": clean,
            "message": "Command valid.",
            "score": 1.0,
            "second_score": None,
        }

    # Layer 2: unavailable exact
    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    if clean in UNAVAILABLE_COMMANDS:
        return {
            "status": "unavailable",
            "input": clean,
            "command": None,
            "message": UNAVAILABLE_COMMANDS[clean],
            "score": None,
            "second_score": None,
        }

    # Layer 3: alias exact
    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    if clean in COMMAND_ALIASES:
        target = COMMAND_ALIASES[clean]

        return {
            "status": "alias",
            "input": clean,
            "command": target,
            "message": f"Mungkin maksud Anda `/{target}`.",
            "score": 1.0,
            "second_score": None,
        }

    # Layer 4: similarity lokal
    candidates = get_similarity_candidates(clean)

    if not candidates:
        return {
            "status": "unresolved",
            "input": clean,
            "command": None,
            "message": "Tidak ada kandidat command.",
            "score": None,
            "second_score": None,
        }

    best = candidates[0]
    second = candidates[1] if len(candidates) > 1 else {"command": None, "score": 0}

    best_score = float(best["score"])
    second_score = float(second["score"])
    margin = best_score - second_score

    if best_score >= SIMILARITY_THRESHOLD and margin >= SIMILARITY_MARGIN:
        return {
            "status": "similarity",
            "input": clean,
            "command": best["command"],
            "message": f"Mungkin maksud Anda `/{best['command']}`.",
            "score": best_score,
            "second_score": second_score,
        }

    # Implementation note for this project-specific finance flow.
    if best_score >= SIMILARITY_THRESHOLD and margin < SIMILARITY_MARGIN:
        return {
            "status": "ambiguous",
            "input": clean,
            "command": None,
            "message": (
                "Command mirip dengan beberapa pilihan, tapi belum cukup yakin."
            ),
            "score": best_score,
            "second_score": second_score,
        }

    return {
        "status": "unresolved",
        "input": clean,
        "command": None,
        "message": "Command tidak dikenali.",
        "score": best_score,
        "second_score": second_score,
    }


def build_command_suggestion_text(resolved: dict, original_text: str) -> str:
    """Build the data structure or message text for command suggestion text."""
    status = resolved.get("status")
    clean = resolved.get("input") or clean_command_token(original_text)
    command = resolved.get("command")

    if status == "unavailable":
        return (
            f"❓ Fitur `/{clean}` belum tersedia.\n\n"
            f"{resolved.get('message')}\n\n"
            "Ketik `/help` untuk lihat fitur yang tersedia."
        )

    if status in ["alias", "similarity"] and command:
        description = command_description(command)

        if is_destructive_command(command):
            return (
                f"❓ Command `/{clean}` tidak dikenal.\n\n"
                f"Mungkin maksud Anda:\n"
                f"`/{command}` — {description}\n\n"
                "Catatan: command ini bisa mengubah data, jadi bot tidak akan menjalankannya otomatis.\n"
                "Ketik command yang benar secara manual."
            )

        return (
            f"❓ Command `/{clean}` tidak dikenal.\n\n"
            f"Mungkin maksud Anda:\n"
            f"`/{command}` — {description}\n\n"
            f"Ketik `/{command}` untuk menjalankan."
        )

    if status == "ambiguous":
        return (
            f"❓ Command `/{clean}` belum bisa saya pastikan.\n\n"
            "Command tersebut mirip dengan beberapa command lain, jadi saya tidak mau menebak.\n\n"
            "Command yang tersedia:\n"
            "`/saldo`, `/harian`, `/mingguan`, `/bulanan`, `/budget`, `/budget_history`, "
            "`/hutang`, `/pending`, `/cari`, `/last`, `/delete_txn`, `/edit_txn`, `/help`"
        )

    return (
        f"❓ Command `/{clean}` tidak tersedia.\n\n"
        "Command yang tersedia:\n"
        "`/saldo`, `/harian`, `/mingguan`, `/bulanan`, `/budget`, `/budget_history`, "
        "`/hutang`, `/pending`, `/cari`, `/last`, `/delete_txn`, `/edit_txn`, `/help`\n\n"
        "Ketik `/help` untuk panduan lengkap."
    )


def maybe_text_is_command_typo(text: str) -> str | None:
    """Try to detect text is command typo without forcing a final decision."""
    clean_text = str(text or "").strip().lower()

    if not clean_text:
        return None

    tokens = clean_text.split()

    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    if len(tokens) != 1:
        return None

    has_amount = bool(
        re.search(
            r"\b\d+(?:[.,]\d+)?\s*(rb|ribu|k|jt|juta)?\b",
            clean_text,
            flags=re.IGNORECASE,
        )
    )

    if has_amount:
        return None

    first_token = tokens[0].lstrip("/")
    resolved = resolve_command_local(first_token)
    status = resolved.get("status")

    if status == "exact":
        cmd = resolved.get("command")
        return (
            f"❓ Sepertinya Anda mau pakai command.\n\n"
            f"Gunakan:\n"
            f"`/{cmd}` — {command_description(cmd)}"
        )

    if status in ["alias", "similarity", "unavailable", "ambiguous"]:
        text_response = build_command_suggestion_text(resolved, first_token)

        return text_response.replace(
            "Command `/",
            "Input `"
        ).replace(
            "tidak dikenal.",
            "terlihat seperti command, tapi belum valid."
        )

    return None

async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Telegram request for unknown command."""
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    command_text = update.message.text.strip().split()[0]
    resolved = resolve_command_local(command_text)

    await update.message.reply_text(
        build_command_suggestion_text(resolved, command_text),
        parse_mode="Markdown",
    )

def short_txn_id(txn_id: str) -> str:
    """Helper for short txn id in the Telegram bot flow."""
    txn_id = str(txn_id or "")
    if len(txn_id) <= 18:
        return txn_id
    return txn_id[:18] + "..."


def expand_txn_refs(refs: list[str]) -> list[str]:
    """Helper for expand txn refs in the Telegram bot flow."""
    expanded = []

    for ref in refs or []:
        clean = str(ref or "").strip()
        if not clean:
            continue

        range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", clean)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            step = 1 if end >= start else -1
            expanded.extend(str(i) for i in range(start, end + step, step))
            continue

        expanded.append(clean)

    return expanded


def resolve_txn_refs_from_last(context: ContextTypes.DEFAULT_TYPE, refs: list[str]) -> dict:
    """Resolve the final value for txn refs from last from possible inputs."""
    last_map = context.user_data.get("last_txn_map", {})

    row_indices = []
    txn_ids = []
    invalid_refs = []

    for ref in expand_txn_refs(refs):
        clean = str(ref).strip()

        if not clean:
            continue

        if clean in last_map:
            mapped = last_map[clean]

            if isinstance(mapped, dict):
                row_index = mapped.get("row_index")

                if row_index:
                    row_indices.append(int(row_index))
                else:
                    invalid_refs.append(clean)

            else:
                # Legacy compatibility note for older records or older in-memory state.
                txn_ids.append(str(mapped))

        else:
            # Implementation note for this project-specific finance flow.
            # atau nomornya di luar hasil /last terakhir.
            if clean.isdigit():
                invalid_refs.append(clean)
            else:
                txn_ids.append(clean)

    unique_rows = []
    seen_rows = set()

    for row in row_indices:
        if row not in seen_rows:
            unique_rows.append(row)
            seen_rows.add(row)

    unique_ids = []
    seen_ids = set()

    for txn_id in txn_ids:
        if txn_id not in seen_ids:
            unique_ids.append(txn_id)
            seen_ids.add(txn_id)

    return {
        "row_indices": unique_rows,
        "txn_ids": unique_ids,
        "invalid_refs": invalid_refs,
    }

def build_last_transactions_text(transactions: list[dict], title: str) -> str:
    """Build the data structure or message text for last transactions text."""
    transactions = enrich_transactions_with_debt_info(transactions or [])
    lines = [f"🧾 *{md_safe(title)}*\n"]
    append_net_gross_note(lines, transactions)

    for i, txn in enumerate(transactions, 1):
        lines.extend(
            build_transaction_display_lines(
                txn,
                index=i,
                include_date=True,
                include_id=True,
            )
        )

    lines.append(
        "\nHapus transaksi:\n"
        "`/delete_txn 1`\n"
        "`/delete_txn 1 3 5`\n"
        "`/delete_txn 1-4`\n\n"
        "Angka mengikuti nomor dari hasil `/last` terakhir."
    )

    return "\n".join(lines)

def build_delete_preview_text(preview: dict) -> str:
    """Build the data structure or message text for delete preview text."""
    deletable = preview.get("deletable", [])
    blocked = preview.get("blocked", [])
    missing_ids = preview.get("missing_ids", [])
    missing_rows = preview.get("missing_rows", [])
    reverse_deltas = preview.get("reverse_deltas", {})

    lines = ["⚠️ *Preview Hapus Transaksi*\n"]

    if deletable:
        lines.append("*Akan dihapus:*")
        for txn in deletable:
            txn_type = str(txn.get("type", "")).strip()

            icon = {
                "expense": "❌",
                "income": "✅",
                "transfer": "🔄",
            }.get(txn_type, "❓")

            row_index = md_safe(txn.get("_row_index", "-"))
            date = md_safe(txn.get("date", "-"))
            desc = md_safe(txn.get("description") or "-")
            category = md_safe(txn.get("category") or "-")
            account = md_safe(txn.get("account") or "-")
            amount = float(txn.get("amount", 0) or 0)

            lines.append(
                f"• {icon} Row {row_index} — {date} — *{desc}*\n"
                f"  {format_rupiah(amount)} | {category} | {account}"
            )

    if reverse_deltas:
        lines.append("\n*Efek ke saldo:*")
        for account, delta in reverse_deltas.items():
            safe_account = md_safe(account)
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {safe_account}: {sign}{format_rupiah(abs(delta))}")

    if blocked:
        lines.append("\n🚫 *Diblok karena transaksi debt cashflow:*")
        for txn in blocked:
            row_index = md_safe(txn.get("_row_index", "-"))
            date = md_safe(txn.get("date", "-"))
            desc = md_safe(txn.get("description") or "-")
            category = md_safe(txn.get("category") or "-")

            lines.append(
                f"• Row {row_index} — {date} — {desc} "
                f"({category})"
            )

        lines.append(
            "\nTransaksi debt belum dihapus lewat fitur ini supaya sheet `debts` tidak inkonsisten."
        )

    if missing_ids:
        lines.append("\n❓ *ID tidak ditemukan:*")
        for txn_id in missing_ids:
            safe_txn_id = md_safe(txn_id)
            lines.append(f"• `{safe_txn_id}`")

    if missing_rows:
        lines.append("\n❓ *Nomor dari /last tidak valid / tidak ditemukan:*")
        for row in missing_rows:
            safe_row = md_safe(row)
            lines.append(f"• `{safe_row}`")

    if deletable:
        lines.append("\nLanjut hapus transaksi di atas?")
    else:
        lines.append("\nTidak ada transaksi yang bisa dihapus.")

    return "\n".join(lines)

def is_authorized(update: Update) -> bool:
    """Check a boolean condition for is authorized."""
    if not update.effective_user:
        return False

    user_id = update.effective_user.id
    return user_id == ALLOWED_USER_ID


async def reject_unauthorized(update: Update):
    """Helper for reject unauthorized in the Telegram bot flow."""
    user_id = update.effective_user.id if update.effective_user else "unknown"

    message = (
        "⛔ Anda tidak punya akses ke bot ini.\n\n"
        f"User ID Anda: `{user_id}`\n\n"
        "Bot ini hanya bisa digunakan oleh user yang sudah diizinkan."
    )

    if update.message:
        await update.message.reply_text(message, parse_mode="Markdown")
        return

    if update.callback_query:
        try:
            await update.callback_query.answer(
                "⛔ Anda tidak punya akses.",
                show_alert=True,
            )
        except Exception:
            pass
        return


