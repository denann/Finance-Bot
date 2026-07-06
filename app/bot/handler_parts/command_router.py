"""Command routing and typo suggestion utilities for explicit slash commands and natural read-only requests."""

# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *

# Define build gemini low confidence text for callers in this flow.
def build_gemini_low_confidence_text(router_result: dict) -> str:
    """Build the data structure or message text for gemini low confidence text."""
    intent = router_result.get("intent", "unknown")
    confidence = float(router_result.get("confidence", 0) or 0)
    explanation = router_result.get("explanation", "")

    # Return ( to the caller.
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
    # Close the structure that was opened above.
    )


# Define build gemini fallback text for callers in this flow.
def build_gemini_fallback_text() -> str:
    """Build the data structure or message text for gemini fallback text."""
    # Return ( to the caller.
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
    # Close the structure that was opened above.
    )


# Define router args to last filter for callers in this flow.
def router_args_to_last_filter(args: dict) -> tuple[int, str | None, str | None, str]:
    """Coordinate the router args to last filter logic in the Telegram handler layer.

    Args:
        args: Command argument list or parsed argument values supplied by the caller.

    Returns:
        `tuple[int, str | None, str | None, str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    period = args.get("period")
    month = args.get("month")
    limit = args.get("limit")

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare limit for the next step.
        limit = int(limit) if limit else 10
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Prepare limit for the next step.
        limit = 10

    # Prepare limit for the next step.
    limit = min(max(limit, 1), 30)

    # Handle the case where month.
    if month:
        # Prepare month for the next step.
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


# Define extract edit updates from router for callers in this flow.
def extract_edit_updates_from_router(args: dict) -> dict:
    """Extract the required part of input for edit updates from router."""
    updates = args.get("updates", {}) or {}

    # Handle the missing or empty isinstance(updates, dict) case.
    if not isinstance(updates, dict):
        # Return {} to the caller.
        return {}

    # Prepare cleaned for the next step.
    cleaned = {}

    # Process each key, value in the current collection.
    for key, value in updates.items():
        # Handle the case where value is None.
        if value is None:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Run this statement as part of the current workflow.
        cleaned[str(key).strip()] = str(value).strip()

    # Return cleaned to the caller.
    return cleaned

# Define format rupiah for callers in this flow.
def format_rupiah(amount: float) -> str:
    """Format data into a readable display for rupiah."""
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")

# Define md safe for callers in this flow.
def md_safe(value) -> str:
    """Coordinate the md safe logic in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    return escape_markdown(str(value or "-"), version=1)

# Open a multi-line structure for the values below.
KNOWN_COMMANDS = {
    "start": {
        "description": "Mulai bot dan lihat ringkasan fitur.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "help": {
        "description": "Lihat panduan lengkap penggunaan bot.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "quickstart": {
        "description": "Panduan langkah awal untuk user baru.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "cancel": {
        "description": "Batalkan wizard, preview, atau konfirmasi yang sedang aktif.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "batal": {
        "description": "Batalkan flow aktif melalui command fallback.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "examples": {
        "description": "Lihat contoh input cepat untuk mencoba bot.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "contoh": {
        "description": "Alias /examples untuk contoh input cepat.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "saldo": {
        "description": "Lihat saldo semua rekening.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "set_saldo": {
        "description": "Set saldo rekening tertentu dengan preview konfirmasi.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "saldo_set": {
        "description": "Alias /set_saldo.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "set_balance": {
        "description": "Alias /set_saldo.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "rekening": {
        "description": "Lihat transaksi lengkap rekening tertentu.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "harian": {
        "description": "Lihat ringkasan transaksi hari ini.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "mingguan": {
        "description": "Lihat ringkasan transaksi minggu ini.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "bulanan": {
        "description": "Lihat ringkasan transaksi bulan ini.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "grafik": {
        "description": "Buat grafik bulanan: line/time series, bar, atau pie.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "budget": {
        "description": "Lihat budget bulan berjalan atau bulan tertentu.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "set_budget": {
        "description": "Set budget kategori tertentu dengan format natural.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "budget_history": {
        "description": "Lihat daftar bulan yang punya data budget.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "kategori": {
        "description": "Lihat daftar kategori, symbol, tipe, dan aliases.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    # Category add changes the categories sheet after its own preview confirm.
    "add_kategori": {
        "description": "Tambah kategori baru dengan aliases Gemini.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    # Category edit can update type, symbol, and aliases after confirmation.
    "edit_kategori": {
        "description": "Edit tipe, symbol, dan aliases kategori.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "pending": {
        "description": "Lihat pending expense/rencana pengeluaran aktif.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "pending_add": {
        "description": "Tambah pending expense/rencana pengeluaran.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "pending_paid": {
        "description": "Ubah pending expense menjadi transaksi aktual.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "pending_cancel": {
        "description": "Batalkan pending expense.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "hutang": {
        "description": "Lihat utang/piutang aktif.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "ringkasan_hutang": {
        "description": "Buat rekap hutang-piutang shareable tanpa ID/command internal.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "cari": {
        "description": "Cari transaksi berdasarkan keyword.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "last": {
        "description": "Lihat transaksi terakhir dengan filter.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "transaksi": {
        "description": "Lihat transaksi lengkap untuk hari/minggu/bulan/rekening tertentu.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "export": {
        "description": "Export data transaksi untuk backup atau analisis lanjutan.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "download_data": {
        "description": "Alias export data transaksi.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "delete_txn": {
        "description": "Hapus transaksi dari hasil /last atau berdasarkan ID.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "edit_txn": {
        "description": "Edit transaksi dari hasil /last atau berdasarkan ID.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "debt_void": {
        "description": "Batalkan utang/piutang salah input secara aman.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "debt_edit": {
        "description": "Edit utang/piutang aktif dari hasil /hutang.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "debt_settle": {
        "description": "Lunasi utang/piutang aktif dari hasil /hutang.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "recurring": {
        "description": "Lihat daftar recurring transaction.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "recurring_add": {
        "description": "Tambah recurring transaction baru.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "recurring_run": {
        "description": "Jalankan recurring transaction yang sudah jatuh tempo.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "recurring_edit": {
        "description": "Edit recurring transaction existing.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "recurring_off": {
        "description": "Nonaktifkan recurring transaction.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "insight": {
        "description": "Buat insight/narasi finansial dengan Gemini.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "ask": {
        "description": "Tanya jawab finansial natural berbasis data sheet.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "audit": {
        "description": "Cek anomali dan kualitas data transaksi.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "coach": {
        "description": "Saran finansial ringan berbasis data.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "assets": {
        "description": "Lihat daftar aset aktif.",
        "destructive": False,
    # Close the structure that was opened above.
    },
    "asset_add": {
        "description": "Tambah aset baru dengan wizard atau format pipe.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "asset_update": {
        "description": "Update nilai aset existing.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "asset_off": {
        "description": "Nonaktifkan aset existing.",
        "destructive": True,
    # Close the structure that was opened above.
    },
    "networth": {
        "description": "Lihat kekayaan bersih.",
        "destructive": False,
    # Close the structure that was opened above.
    },
# Close the structure that was opened above.
}


# Open a multi-line structure for the values below.
COMMAND_ALIASES = {
    "examples": "examples",
    "contoh": "examples",
    "sample": "examples",
    "cancel": "cancel",
    "batal": "cancel",
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
    "grafik": "grafik",
    "chart": "grafik",
    "grafik_bulanan": "grafik",

    # budget
    "buget": "budget",
    "budjet": "budget",
    "budged": "budget",
    "bujet": "budget",
    "budget": "budget",
    "set_budget": "set_budget",
    "budget_set": "set_budget",

    "budgethistory": "budget_history",
    "budget_history": "budget_history",
    "budget_histori": "budget_history",
    "budgethistori": "budget_history",
    "histori_budget": "budget_history",

    # Category management section
    # Category list is read-only and helps users inspect existing aliases.
    "kategori": "kategori",
    "categories": "kategori",
    "list_kategori": "kategori",
    "kategori_list": "kategori",
    # Natural Indonesian alias for adding a category.
    "add_kategori": "add_kategori",
    "tambah_kategori": "add_kategori",
    # English aliases are mapped into the same add wizard.
    "add_category": "add_kategori",
    "tambah_category": "add_kategori",
    "kategori_add": "add_kategori",
    # Edit aliases route to the edit wizard, not transaction parsing.
    "edit_kategori": "edit_kategori",
    "ubah_kategori": "edit_kategori",
    # English edit aliases are mapped into the same edit wizard.
    "edit_category": "edit_kategori",
    "kategori_edit": "edit_kategori",

    # Pending expense section
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

    # Debt flow section
    "utang": "hutang",
    "hutang": "hutang",
    "ringkasan_hutang": "ringkasan_hutang",
    "rekap_hutang": "ringkasan_hutang",
    "void_hutang": "debt_void",
    "void_utang": "debt_void",
    "void_piutang": "debt_void",
    "debt_void": "debt_void",
    "debt_edit": "debt_edit",
    "edit_hutang": "debt_edit",
    "debt_settle": "debt_settle",
    "lunasi_hutang": "debt_settle",

    # Recurring flow section
    "recurring": "recurring",
    "recurring_add": "recurring_add",
    "tambah_recurring": "recurring_add",
    "recurring_run": "recurring_run",
    "recurring_edit": "recurring_edit",
    "recurring_off": "recurring_off",

    # Account flow section
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

    # Implementation note for this project-specific finance flow.
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

    # Gemini / RAG finance
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
    "asset_add": "asset_add",
    "tambah_aset": "asset_add",
    "asset_update": "asset_update",
    "update_aset": "asset_update",
    "asset_off": "asset_off",
    "nonaktif_aset": "asset_off",
    "networth": "networth",
    "net_worth": "networth",
    "kekayaan": "networth",
# Close the structure that was opened above.
}


# Open a multi-line structure for the values below.
UNAVAILABLE_COMMANDS = {
    "kuartalan": (
        "Fitur laporan kuartalan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    # Close the structure that was opened above.
    ),
    "quarter": (
        "Fitur laporan kuartalan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    # Close the structure that was opened above.
    ),
    "triwulan": (
        "Fitur laporan triwulan/kuartalan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    # Close the structure that was opened above.
    ),
    "tahunan": (
        "Fitur laporan tahunan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    # Close the structure that was opened above.
    ),
    "yearly": (
        "Fitur laporan tahunan belum tersedia.\n"
        "Yang tersedia saat ini: `/harian`, `/mingguan`, `/bulanan`."
    # Close the structure that was opened above.
    ),
# Close the structure that was opened above.
}


# Prepare SIMILARITY THRESHOLD for the next step.
SIMILARITY_THRESHOLD = 0.78
# Prepare SIMILARITY MARGIN for the next step.
SIMILARITY_MARGIN = 0.12


# Define clean command token for callers in this flow.
def clean_command_token(command_text: str) -> str:
    """Coordinate the clean command token logic in the Telegram handler layer.

    Args:
        command_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    clean = str(command_text or "").strip().lower()
    clean = clean.lstrip("/")
    clean = clean.split("@")[0]
    # Prepare clean for the next step.
    clean = clean.strip()

    # Return clean to the caller.
    return clean


# Define command description for callers in this flow.
def command_description(command_name: str) -> str:
    """Coordinate the command description logic in the Telegram handler layer.

    Args:
        command_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Prepare info for the next step.
    info = KNOWN_COMMANDS.get(command_name, {})
    return info.get("description", "")


# Define is destructive command for callers in this flow.
def is_destructive_command(command_name: str) -> bool:
    """Check whether a condition is true for destructive command."""
    # Prepare info for the next step.
    info = KNOWN_COMMANDS.get(command_name, {})
    return bool(info.get("destructive", False))


# Define similarity score for callers in this flow.
def similarity_score(a: str, b: str) -> float:
    """Coordinate the similarity score logic in the Telegram handler layer.

    Args:
        a: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        b: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Return SequenceMatcher(None, a, b).ratio() to the caller.
    return SequenceMatcher(None, a, b).ratio()


# Define get similarity candidates for callers in this flow.
def get_similarity_candidates(clean_command: str) -> list[dict]:
    """Retrieve data needed by the get similarity candidates workflow in the Telegram handler layer.

    Args:
        clean_command: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Prepare candidates for the next step.
    candidates = []

    # Process each command_name in the current collection.
    for command_name in KNOWN_COMMANDS.keys():
        # Prepare score for the next step.
        score = similarity_score(clean_command, command_name)
        # Open a multi-line structure for the values below.
        candidates.append({
            "command": command_name,
            "score": score,
        # Close the structure that was opened above.
        })

    # Open a multi-line structure for the values below.
    candidates = sorted(
        # Include this value in the surrounding collection or call.
        candidates,
        key=lambda x: x["score"],
        # Prepare reverse for the next step.
        reverse=True,
    # Close the structure that was opened above.
    )

    # Return candidates to the caller.
    return candidates


# Define resolve command local for callers in this flow.
def resolve_command_local(command_text: str) -> dict:
    """Resolve a user input or reference for command local."""
    # Prepare clean for the next step.
    clean = clean_command_token(command_text)

    # Handle the missing or empty clean case.
    if not clean:
        # Return { to the caller.
        return {
            "status": "unresolved",
            "input": clean,
            "command": None,
            "message": "Command kosong.",
            "score": None,
            "second_score": None,
        # Close the structure that was opened above.
        }

    # Implementation note for this project-specific finance flow.
    if clean in KNOWN_COMMANDS:
        # Return { to the caller.
        return {
            "status": "exact",
            "input": clean,
            "command": clean,
            "message": "Command valid.",
            "score": 1.0,
            "second_score": None,
        # Close the structure that was opened above.
        }

    # Layer 2: unavailable exact
    # Must run before similarity matching so /kuartalan is not routed to /bulanan.
    if clean in UNAVAILABLE_COMMANDS:
        # Return { to the caller.
        return {
            "status": "unavailable",
            "input": clean,
            "command": None,
            "message": UNAVAILABLE_COMMANDS[clean],
            "score": None,
            "second_score": None,
        # Close the structure that was opened above.
        }

    # Layer 3: alias exact
    # Aliases must match exactly, not by contains.
    if clean in COMMAND_ALIASES:
        # Prepare target for the next step.
        target = COMMAND_ALIASES[clean]

        # Return { to the caller.
        return {
            "status": "alias",
            "input": clean,
            "command": target,
            "message": f"Mungkin maksud Anda `/{target}`.",
            "score": 1.0,
            "second_score": None,
        # Close the structure that was opened above.
        }

    # Layer 4: similarity lokal
    candidates = get_similarity_candidates(clean)

    # Handle the missing or empty candidates case.
    if not candidates:
        # Return { to the caller.
        return {
            "status": "unresolved",
            "input": clean,
            "command": None,
            "message": "Tidak ada kandidat command.",
            "score": None,
            "second_score": None,
        # Close the structure that was opened above.
        }

    # Prepare best for the next step.
    best = candidates[0]
    second = candidates[1] if len(candidates) > 1 else {"command": None, "score": 0}

    best_score = float(best["score"])
    second_score = float(second["score"])
    # Prepare margin for the next step.
    margin = best_score - second_score

    # Handle the case where best_score >= SIMILARITY_THRESHOLD and margin >= SIMILARITY_M....
    if best_score >= SIMILARITY_THRESHOLD and margin >= SIMILARITY_MARGIN:
        # Return { to the caller.
        return {
            "status": "similarity",
            "input": clean,
            "command": best["command"],
            "message": f"Mungkin maksud Anda `/{best['command']}`.",
            "score": best_score,
            "second_score": second_score,
        # Close the structure that was opened above.
        }

    # Implementation note for this project-specific finance flow.
    if best_score >= SIMILARITY_THRESHOLD and margin < SIMILARITY_MARGIN:
        # Return { to the caller.
        return {
            "status": "ambiguous",
            "input": clean,
            "command": None,
            "message": (
                "Command mirip dengan beberapa pilihan, tapi belum cukup yakin."
            # Close the structure that was opened above.
            ),
            "score": best_score,
            "second_score": second_score,
        # Close the structure that was opened above.
        }

    # Return { to the caller.
    return {
        "status": "unresolved",
        "input": clean,
        "command": None,
        "message": "Command tidak dikenali.",
        "score": best_score,
        "second_score": second_score,
    # Close the structure that was opened above.
    }


# Define build command suggestion text for callers in this flow.
def build_command_suggestion_text(resolved: dict, original_text: str) -> str:
    """Build the data structure or message text for command suggestion text."""
    status = resolved.get("status")
    clean = resolved.get("input") or clean_command_token(original_text)
    command = resolved.get("command")

    if status == "unavailable":
        # Return ( to the caller.
        return (
            f"❓ Fitur `/{clean}` belum tersedia.\n\n"
            f"{resolved.get('message')}\n\n"
            "Ketik `/help` untuk lihat fitur yang tersedia."
        # Close the structure that was opened above.
        )

    if status in ["alias", "similarity"] and command:
        # Prepare description for the next step.
        description = command_description(command)

        # Handle the case where is_destructive_command(command).
        if is_destructive_command(command):
            # Return ( to the caller.
            return (
                f"❓ Command `/{clean}` tidak dikenal.\n\n"
                f"Mungkin maksud Anda:\n"
                f"`/{command}` — {description}\n\n"
                "Catatan: command ini bisa mengubah data, jadi bot tidak akan menjalankannya otomatis.\n"
                "Ketik command yang benar secara manual."
            # Close the structure that was opened above.
            )

        # Return ( to the caller.
        return (
            f"❓ Command `/{clean}` tidak dikenal.\n\n"
            f"Mungkin maksud Anda:\n"
            f"`/{command}` — {description}\n\n"
            f"Ketik `/{command}` untuk menjalankan."
        # Close the structure that was opened above.
        )

    if status == "ambiguous":
        # Return ( to the caller.
        return (
            f"❓ Command `/{clean}` belum bisa saya pastikan.\n\n"
            "Command tersebut mirip dengan beberapa command lain, jadi saya tidak mau menebak.\n\n"
            "Command yang tersedia:\n"
            "`/saldo`, `/set_saldo`, `/quickstart`, `/harian`, `/mingguan`, `/bulanan`, `/grafik`, `/budget`, `/set_budget`, `/budget_history`, "
            "`/kategori`, `/add_kategori`, `/edit_kategori`, `/hutang`, `/pending`, `/recurring`, `/asset_add`, `/assets`, `/cari`, `/last`, `/delete_txn`, `/edit_txn`, `/help`"
        # Close the structure that was opened above.
        )

    # Return ( to the caller.
    return (
        f"❓ Command `/{clean}` tidak tersedia.\n\n"
        "Command yang tersedia:\n"
        "`/saldo`, `/set_saldo`, `/quickstart`, `/harian`, `/mingguan`, `/bulanan`, `/grafik`, `/budget`, `/budget_history`, "
        "`/kategori`, `/add_kategori`, `/edit_kategori`, `/hutang`, `/pending`, `/cari`, `/last`, `/delete_txn`, `/edit_txn`, `/help`\n\n"
        "Ketik `/help` untuk panduan lengkap."
    # Close the structure that was opened above.
    )


# Define maybe text is command typo for callers in this flow.
def maybe_text_is_command_typo(text: str) -> str | None:
    """Coordinate the maybe text is command typo logic in the Telegram handler layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str | None` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    clean_text = str(text or "").strip().lower()

    # Handle the missing or empty clean_text case.
    if not clean_text:
        # Return None to the caller.
        return None

    # Prepare tokens for the next step.
    tokens = clean_text.split()

    # Jangan handle multi-token di typo resolver.
    # Natural input section
    if len(tokens) != 1:
        # Return None to the caller.
        return None

    # Open a multi-line structure for the values below.
    has_amount = bool(
        # Open a multi-line structure for the values below.
        re.search(
            r"\b\d+(?:[.,]\d+)?\s*(rb|ribu|k|jt|juta)?\b",
            # Include this value in the surrounding collection or call.
            clean_text,
            # Prepare flags for the next step.
            flags=re.IGNORECASE,
        # Close the structure that was opened above.
        )
    # Close the structure that was opened above.
    )

    # Handle the case where has_amount.
    if has_amount:
        # Return None to the caller.
        return None

    first_token = tokens[0].lstrip("/")
    # Prepare resolved for the next step.
    resolved = resolve_command_local(first_token)
    status = resolved.get("status")

    if status == "exact":
        cmd = resolved.get("command")
        # Return ( to the caller.
        return (
            f"❓ Sepertinya Anda mau pakai command.\n\n"
            f"Gunakan:\n"
            f"`/{cmd}` — {command_description(cmd)}"
        # Close the structure that was opened above.
        )

    if status in ["alias", "similarity", "unavailable", "ambiguous"]:
        # Prepare text response for the next step.
        text_response = build_command_suggestion_text(resolved, first_token)

        # Return text_response.replace( to the caller.
        return text_response.replace(
            "Command `/",
            "Input `"
        # Close the structure that was opened above.
        ).replace(
            "tidak dikenal.",
            "terlihat seperti command, tapi belum valid."
        # Close the structure that was opened above.
        )

    # Return None to the caller.
    return None

# Handle the asynchronous unknown command handler workflow.
async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous unknown command handler flow in the Telegram handler layer.

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

    # Prepare command text for the next step.
    command_text = update.message.text.strip().split()[0]
    # Prepare resolved for the next step.
    resolved = resolve_command_local(command_text)

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_command_suggestion_text(resolved, command_text),
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )

# Define short txn id for callers in this flow.
def short_txn_id(txn_id: str) -> str:
    """Coordinate the short txn id logic in the Telegram handler layer.

    Args:
        txn_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    txn_id = str(txn_id or "")
    # Handle the case where len(txn_id) <= 18.
    if len(txn_id) <= 18:
        # Return txn_id to the caller.
        return txn_id
    return txn_id[:18] + "..."


# Define expand txn refs for callers in this flow.
def expand_txn_refs(refs: list[str]) -> list[str]:
    """Coordinate the expand txn refs logic in the Telegram handler layer.

    Args:
        refs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Prepare expanded for the next step.
    expanded = []

    # Process each ref in the current collection.
    for ref in refs or []:
        clean = str(ref or "").strip()
        # Handle the missing or empty clean case.
        if not clean:
            # Skip the rest of this loop iteration after handling this case.
            continue

        range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", clean)
        # Handle the case where range_match.
        if range_match:
            # Prepare start for the next step.
            start = int(range_match.group(1))
            # Prepare end for the next step.
            end = int(range_match.group(2))
            # Prepare step for the next step.
            step = 1 if end >= start else -1
            # Update expanded with the current value.
            expanded.extend(str(i) for i in range(start, end + step, step))
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Update expanded with the current value.
        expanded.append(clean)

    # Return expanded to the caller.
    return expanded


# Define resolve txn refs from last for callers in this flow.
def resolve_txn_refs_from_last(context: ContextTypes.DEFAULT_TYPE, refs: list[str]) -> dict:
    """Resolve a user input or reference for txn refs from last."""
    last_map = context.user_data.get("last_txn_map", {})

    # Prepare row indices for the next step.
    row_indices = []
    # Prepare txn ids for the next step.
    txn_ids = []
    # Prepare invalid refs for the next step.
    invalid_refs = []

    # Process each ref in the current collection.
    for ref in expand_txn_refs(refs):
        # Prepare clean for the next step.
        clean = str(ref).strip()

        # Handle the missing or empty clean case.
        if not clean:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Handle the case where clean in last_map.
        if clean in last_map:
            # Prepare mapped for the next step.
            mapped = last_map[clean]

            # Handle the case where isinstance(mapped, dict).
            if isinstance(mapped, dict):
                row_index = mapped.get("row_index")

                # Handle the case where row_index.
                if row_index:
                    # Update row indices with the current value.
                    row_indices.append(int(row_index))
                # Handle the fallback path after earlier conditions are skipped.
                else:
                    # Update invalid refs with the current value.
                    invalid_refs.append(clean)

            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Implementation note for this project-specific finance flow.
                txn_ids.append(str(mapped))

        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Implementation note for this project-specific finance flow.
            # atau nomornya di luar hasil /last terakhir.
            if clean.isdigit():
                # Update invalid refs with the current value.
                invalid_refs.append(clean)
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Update txn ids with the current value.
                txn_ids.append(clean)

    # Prepare unique rows for the next step.
    unique_rows = []
    # Prepare seen rows for the next step.
    seen_rows = set()

    # Process each row in the current collection.
    for row in row_indices:
        # Handle the case where row not in seen_rows.
        if row not in seen_rows:
            # Update unique rows with the current value.
            unique_rows.append(row)
            # Update seen rows with the current value.
            seen_rows.add(row)

    # Prepare unique ids for the next step.
    unique_ids = []
    # Prepare seen ids for the next step.
    seen_ids = set()

    # Process each txn_id in the current collection.
    for txn_id in txn_ids:
        # Handle the case where txn_id not in seen_ids.
        if txn_id not in seen_ids:
            # Update unique ids with the current value.
            unique_ids.append(txn_id)
            # Update seen ids with the current value.
            seen_ids.add(txn_id)

    # Return { to the caller.
    return {
        "row_indices": unique_rows,
        "txn_ids": unique_ids,
        "invalid_refs": invalid_refs,
    # Close the structure that was opened above.
    }

# Define build last transactions text for callers in this flow.
def build_last_transactions_text(transactions: list[dict], title: str) -> str:
    """Build the data structure or message text for last transactions text."""
    # Prepare transactions for the next step.
    transactions = enrich_transactions_with_debt_info(transactions or [])
    lines = [f"🧾 *{md_safe(title)}*\n"]
    # Run this statement as part of the current workflow.
    append_net_gross_note(lines, transactions)

    # Process each i, txn in the current collection.
    for i, txn in enumerate(transactions, 1):
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
            # Close the structure that was opened above.
            )
        # Close the structure that was opened above.
        )

    # Open a multi-line structure for the values below.
    lines.append(
        "\nHapus transaksi:\n"
        "`/delete_txn 1`\n"
        "`/delete_txn 1 3 5`\n"
        "`/delete_txn 1-4`\n\n"
        "Angka mengikuti nomor dari hasil `/last` terakhir."
    # Close the structure that was opened above.
    )

    return "\n".join(lines)

# Define build delete preview text for callers in this flow.
def build_delete_preview_text(preview: dict) -> str:
    """Build the data structure or message text for delete preview text."""
    deletable = preview.get("deletable", [])
    blocked = preview.get("blocked", [])
    missing_ids = preview.get("missing_ids", [])
    missing_rows = preview.get("missing_rows", [])
    reverse_deltas = preview.get("reverse_deltas", {})

    lines = ["⚠️ *Preview Hapus Transaksi*\n"]

    # Handle the case where deletable.
    if deletable:
        lines.append("*Akan dihapus:*")
        # Process each txn in the current collection.
        for txn in deletable:
            txn_type = str(txn.get("type", "")).strip()

            # Open a multi-line structure for the values below.
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

            # Open a multi-line structure for the values below.
            lines.append(
                f"• {icon} Row {row_index} — {date} — *{desc}*\n"
                f"  {format_rupiah(amount)} | {category} | {account}"
            # Close the structure that was opened above.
            )

    # Handle the case where reverse_deltas.
    if reverse_deltas:
        lines.append("\n*Efek ke saldo:*")
        # Process each account, delta in the current collection.
        for account, delta in reverse_deltas.items():
            # Prepare safe account for the next step.
            safe_account = md_safe(account)
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {safe_account}: {sign}{format_rupiah(abs(delta))}")

    # Handle the case where blocked.
    if blocked:
        lines.append("\n🚫 *Diblok karena transaksi debt cashflow:*")
        # Process each txn in the current collection.
        for txn in blocked:
            row_index = md_safe(txn.get("_row_index", "-"))
            date = md_safe(txn.get("date", "-"))
            desc = md_safe(txn.get("description") or "-")
            category = md_safe(txn.get("category") or "-")

            # Open a multi-line structure for the values below.
            lines.append(
                f"• Row {row_index} — {date} — {desc} "
                f"({category})"
            # Close the structure that was opened above.
            )

        # Open a multi-line structure for the values below.
        lines.append(
            "\nTransaksi debt belum dihapus lewat fitur ini supaya sheet `debts` tidak inkonsisten."
        # Close the structure that was opened above.
        )

    # Handle the case where missing_ids.
    if missing_ids:
        lines.append("\n❓ *ID tidak ditemukan:*")
        # Process each txn_id in the current collection.
        for txn_id in missing_ids:
            # Prepare safe txn id for the next step.
            safe_txn_id = md_safe(txn_id)
            lines.append(f"• `{safe_txn_id}`")

    # Handle the case where missing_rows.
    if missing_rows:
        lines.append("\n❓ *Nomor dari /last tidak valid / tidak ditemukan:*")
        # Process each row in the current collection.
        for row in missing_rows:
            # Prepare safe row for the next step.
            safe_row = md_safe(row)
            lines.append(f"• `{safe_row}`")

    # Handle the case where deletable.
    if deletable:
        lines.append("\nLanjut hapus transaksi di atas?")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.append("\nTidak ada transaksi yang bisa dihapus.")

    return "\n".join(lines)

# Define is authorized for callers in this flow.
def is_authorized(update: Update) -> bool:
    """Check whether a condition is true for authorized."""
    # Handle the missing or empty update.effective_user case.
    if not update.effective_user:
        # Return False to the caller.
        return False

    # Prepare user id for the next step.
    user_id = update.effective_user.id
    # Return user_id == ALLOWED_USER_ID to the caller.
    return user_id == ALLOWED_USER_ID


# Handle the asynchronous reject unauthorized workflow.
async def reject_unauthorized(update: Update):
    """Handle the asynchronous reject unauthorized flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    user_id = update.effective_user.id if update.effective_user else "unknown"

    # Open a multi-line structure for the values below.
    message = (
        "⛔ Anda tidak punya akses ke bot ini.\n\n"
        f"User ID Anda: `{user_id}`\n\n"
        "Bot ini hanya bisa digunakan oleh user yang sudah diizinkan."
    # Close the structure that was opened above.
    )

    # Handle the case where update.message.
    if update.message:
        await update.message.reply_text(message, parse_mode="Markdown")
        # Return control to the caller.
        return

    # Handle the case where update.callback_query.
    if update.callback_query:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Wait for update.callback_query.answer before continuing this flow.
            await update.callback_query.answer(
                "⛔ Anda tidak punya akses.",
                # Prepare show alert for the next step.
                show_alert=True,
            # Close the structure that was opened above.
            )
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass
        # Return control to the caller.
        return


