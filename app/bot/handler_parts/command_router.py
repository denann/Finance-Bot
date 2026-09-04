"""Command routing and typo suggestion utilities for explicit slash commands and natural read-only requests."""

# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import (
    ALLOWED_USER_ID,
    ContextTypes,
    SequenceMatcher,
    Update,
    append_net_gross_note,
    build_transaction_display_lines,
    enrich_transactions_with_debt_info,
    escape_markdown,
    re,
)
from functools import partial

from app.formatting import format_rupiah as _format_rupiah
from app.bot.command_registry import LIABILITY_UNAVAILABLE_COMMANDS


format_rupiah = partial(_format_rupiah, preserve_decimals=False)

# Helper for build gemini low confidence text.
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


# Helper for build gemini fallback text.
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


# Helper for router args to last filter.
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
        limit = int(limit) if limit else 10
    # Handle an expected failure from the guarded operation above.
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


# Helper for extract edit updates from router.
def extract_edit_updates_from_router(args: dict) -> dict:
    """Extract the required part of input for edit updates from router."""
    updates = args.get("updates", {}) or {}

    # Validate missing isinstance(updates, dict) before continuing.
    if not isinstance(updates, dict):
        return {}

    # Normalize cleaned before matching.
    cleaned = {}

    # Iterate through each key, value.
    for key, value in updates.items():
        if value is None:
            # Skip the rest of this loop iteration after handling this case.
            continue

        cleaned[str(key).strip()] = str(value).strip()

    return cleaned

# Helper for md safe.
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

KNOWN_COMMANDS = {
    "start": {
        "description": "Mulai bot dan lihat ringkasan fitur.",
        "destructive": False,
    },
    "help": {
        "description": "Lihat panduan lengkap penggunaan bot.",
        "destructive": False,
    },
    "privacy": {
        "description": "Lihat ringkasan data privacy dan keamanan credential.",
        "destructive": False,
    },
    "quickstart": {
        "description": "Panduan langkah awal untuk user baru.",
        "destructive": False,
    },
    "cancel": {
        "description": "Batalkan wizard, preview, atau konfirmasi yang sedang aktif.",
        "destructive": False,
    },
    "batal": {
        "description": "Batalkan flow aktif melalui command fallback.",
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
    "set_saldo": {
        "description": "Set saldo rekening tertentu dengan preview konfirmasi.",
        "destructive": True,
    },
    "saldo_set": {
        "description": "Alias /set_saldo.",
        "destructive": True,
    },
    "set_balance": {
        "description": "Alias /set_saldo.",
        "destructive": True,
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
    "grafik": {
        "description": "Buat grafik bulanan: line/time series, bar, atau pie.",
        "destructive": False,
    },
    "budget": {
        "description": "Lihat budget bulan berjalan atau bulan tertentu.",
        "destructive": False,
    },
    "set_budget": {
        "description": "Set budget kategori tertentu dengan format natural.",
        "destructive": True,
    },
    "budget_history": {
        "description": "Lihat daftar bulan yang punya data budget.",
        "destructive": False,
    },
    "kategori": {
        "description": "Lihat daftar kategori, symbol, tipe, dan aliases.",
        "destructive": False,
    },
    # Category add changes the categories sheet after its own preview confirm.
    "add_kategori": {
        "description": "Tambah kategori baru dengan aliases Gemini.",
        "destructive": True,
    },
    # Category edit can update type, symbol, and aliases after confirmation.
    "edit_kategori": {
        "description": "Edit tipe, symbol, dan aliases kategori.",
        "destructive": True,
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
    "debt_settle": {
        "description": "Lunasi utang/piutang aktif dari hasil /hutang.",
        "destructive": True,
    },
    "recurring": {
        "description": "Lihat daftar recurring transaction.",
        "destructive": False,
    },
    "recurring_add": {
        "description": "Tambah recurring transaction baru.",
        "destructive": True,
    },
    "recurring_run": {
        "description": "Jalankan recurring transaction yang sudah jatuh tempo.",
        "destructive": True,
    },
    "recurring_edit": {
        "description": "Edit recurring transaction existing.",
        "destructive": True,
    },
    "recurring_off": {
        "description": "Nonaktifkan recurring transaction.",
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
    "asset_add": {
        "description": "Tambah aset baru dengan wizard atau format pipe.",
        "destructive": True,
    },
    "asset_update": {
        "description": "Update nilai aset existing.",
        "destructive": True,
    },
    "asset_off": {
        "description": "Nonaktifkan aset existing.",
        "destructive": True,
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
    "cancel": "cancel",
    "batal": "cancel",
    "export": "export",
    "download_data": "download_data",
    "download": "download_data",
    "privacy": "privacy",
    "privasi": "privacy",
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
}


UNAVAILABLE_COMMANDS = {
    **LIABILITY_UNAVAILABLE_COMMANDS,
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


# Helper for clean command token.
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
    # Normalize clean before matching.
    clean = clean.strip()

    return clean


# Helper for command description.
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
    info = KNOWN_COMMANDS.get(command_name, {})
    return info.get("description", "")


# Helper for is destructive command.
def is_destructive_command(command_name: str) -> bool:
    """Check whether a condition is true for destructive command."""
    info = KNOWN_COMMANDS.get(command_name, {})
    return bool(info.get("destructive", False))


# Helper for similarity score.
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
    return SequenceMatcher(None, a, b).ratio()


# Helper for get similarity candidates.
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
    # Extract candidates for validation.
    candidates = []

    # Iterate through each command name.
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


# Helper for resolve command local.
def resolve_command_local(command_text: str) -> dict:
    """Resolve a user input or reference for command local."""
    # Normalize clean before matching.
    clean = clean_command_token(command_text)

    # Validate missing clean before continuing.
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
    # Must run before similarity matching so /kuartalan is not routed to /bulanan.
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
    # Aliases must match exactly, not by contains.
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

    # Validate missing candidates before continuing.
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

    # Handle best score >= SIMILARITY THRESHOLD and margin >= SIMILARITY M.
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


# Helper for build command suggestion text.
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
            "`/saldo`, `/set_saldo`, `/quickstart`, `/harian`, `/mingguan`, `/bulanan`, `/grafik`, `/budget`, `/set_budget`, `/budget_history`, "
            "`/kategori`, `/add_kategori`, `/edit_kategori`, `/hutang`, `/pending`, `/recurring`, `/asset_add`, `/assets`, `/cari`, `/last`, `/delete_txn`, `/edit_txn`, `/help`"
        )

    return (
        f"❓ Command `/{clean}` tidak tersedia.\n\n"
        "Command yang tersedia:\n"
        "`/saldo`, `/set_saldo`, `/quickstart`, `/harian`, `/mingguan`, `/bulanan`, `/grafik`, `/budget`, `/budget_history`, "
        "`/kategori`, `/add_kategori`, `/edit_kategori`, `/hutang`, `/pending`, `/cari`, `/last`, `/delete_txn`, `/edit_txn`, `/help`\n\n"
        "Ketik `/help` untuk panduan lengkap."
    )


# Helper for maybe text is command typo.
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

    # Validate missing clean text before continuing.
    if not clean_text:
        return None

    # Prepare tokens from the incoming input.
    tokens = clean_text.split()

    # Jangan handle multi-token di typo resolver.
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
        # Prepare text response from the incoming input.
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
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Prepare command text from the incoming input.
    command_text = update.message.text.strip().split()[0]
    resolved = resolve_command_local(command_text)

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_command_suggestion_text(resolved, command_text),
        parse_mode="Markdown",
    )

# Helper for short txn id.
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
    if len(txn_id) <= 18:
        return txn_id
    return txn_id[:18] + "..."


# Helper for expand txn refs.
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
    expanded = []

    # Iterate through each ref.
    for ref in refs or []:
        clean = str(ref or "").strip()
        # Validate missing clean before continuing.
        if not clean:
            # Skip the rest of this loop iteration after handling this case.
            continue

        range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", clean)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            step = 1 if end >= start else -1
            # Append the current value to expanded.
            expanded.extend(str(i) for i in range(start, end + step, step))
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Append the current value to expanded.
        expanded.append(clean)

    return expanded


# Helper for resolve txn refs from last.
def resolve_txn_refs_from_last(context: ContextTypes.DEFAULT_TYPE, refs: list[str]) -> dict:
    """Resolve stable numeric refs from the latest transaction-family snapshot.

    Numeric refs never create a fresh query. Full transaction IDs remain usable
    directly; mutation services still enforce unique-ID resolution.
    """
    ref_context = context.user_data.get("transaction_ref_context") or {}
    ordered_ids = list(ref_context.get("ordered_ids") or [])
    txn_ids: list[str] = []
    invalid_refs: list[str] = []
    seen_ids: set[str] = set()
    for ref in expand_txn_refs(refs):
        clean = str(ref or "").strip()
        if not clean:
            continue
        if clean.isdigit():
            number = int(clean)
            if number < 1 or number > len(ordered_ids):
                invalid_refs.append(clean)
                continue
            txn_id = str(ordered_ids[number - 1] or "").strip()
            if not txn_id:
                invalid_refs.append(clean)
                continue
        else:
            txn_id = clean
        if txn_id not in seen_ids:
            txn_ids.append(txn_id)
            seen_ids.add(txn_id)
    return {
        "row_indices": [],
        "txn_ids": txn_ids,
        "invalid_refs": invalid_refs,
        "reference_session_id": ref_context.get("session_id"),
    }


# Helper for build last transactions text.
def build_last_transactions_text(transactions: list[dict], title: str) -> str:
    """Build the data structure or message text for last transactions text."""
    # Load transactions for the current calculation.
    transactions = enrich_transactions_with_debt_info(transactions or [])
    lines = [f"🧾 *{md_safe(title)}*\n"]
    append_net_gross_note(lines, transactions)

    # Iterate through each i, txn.
    for i, txn in enumerate(transactions, 1):
        lines.extend(
            build_transaction_display_lines(
                txn,
                index=i,
                # Extract include date for validation.
                include_date=True,
                include_id=True,
            )
        )

    lines.append(
        "\nHapus transaksi:\n"
        "`/delete_txn 1`\n"
        "`/delete_txn 1 3 5`\n"
        "`/delete_txn 1-4`\n\n"
        "Angka pada helper legacy ini mengikuti snapshot transaction-reference yang sedang aktif."
    )

    return "\n".join(lines)

# Helper for build delete preview text.
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
        # Iterate through each txn.
        for txn in deletable:
            txn_type = str(txn.get("type", "")).strip()

            icon = {
                "expense": "-",
                "income": "+",
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
        # Iterate through each account, delta.
        for account, delta in reverse_deltas.items():
            # Extract safe account for validation.
            safe_account = md_safe(account)
            sign = "+" if delta >= 0 else "-"
            lines.append(f"• {safe_account}: {sign}{format_rupiah(abs(delta))}")

    if blocked:
        lines.append("\n🚫 *Diblok karena transaksi debt cashflow:*")
        # Iterate through each txn.
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
        # Iterate through each txn id.
        for txn_id in missing_ids:
            safe_txn_id = md_safe(txn_id)
            lines.append(f"• `{safe_txn_id}`")

    if missing_rows:
        lines.append("\n❓ *Referensi transaksi tidak valid / tidak ditemukan:*")
        # Iterate through each row.
        for row in missing_rows:
            safe_row = md_safe(row)
            lines.append(f"• `{safe_row}`")

    if deletable:
        lines.append("\nLanjut hapus transaksi di atas?")
    # Use the fallback path when no earlier branch matched.
    else:
        lines.append("\nTidak ada transaksi yang bisa dihapus.")

    return "\n".join(lines)

# Helper for is authorized.
def is_authorized(update: Update) -> bool:
    """Check whether a condition is true for authorized."""
    # Validate missing update.effective user before continuing.
    if not update.effective_user:
        return False

    user_id = update.effective_user.id
    return user_id == ALLOWED_USER_ID


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

    message = (
        "⛔ Anda tidak punya akses ke bot ini.\n\n"
        f"User ID Anda: `{user_id}`\n\n"
        "Bot ini hanya bisa digunakan oleh user yang sudah diizinkan."
    )

    if update.message:
        await update.message.reply_text(message, parse_mode="Markdown")
        return

    if update.callback_query:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Await update.callback query.answer before continuing.
            await update.callback_query.answer(
                "⛔ Anda tidak punya akses.",
                show_alert=True,
            )
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass
        return


