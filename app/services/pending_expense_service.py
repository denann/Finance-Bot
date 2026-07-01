from __future__ import annotations

import calendar
import re
import uuid
from datetime import datetime, timedelta, date

from app.config import SHEET_PENDING_EXPENSES
from app.nlp.normalizer import extract_amount_from_text
from app.nlp.regex_parser import (
    ACCOUNT_DISPLAY_NAMES,
    ACCOUNT_NAMES,
    CATEGORY_KEYWORDS,
    extract_description,
    parse_explicit_date,
    parse_with_regex,
)
from app.sheets.client import append_row_raw, get_all_records, update_cell
from app.services.transaction_service import save_transaction


PENDING_EXPENSE_COLUMNS = [
    "id",
    "due_date",
    "month",
    "due_precision",
    "amount",
    "category",
    "account",
    "subject",
    "description",
    "status",
    "created_at",
    "updated_at",
    "paid_transaction_id",
    "raw_input",
]

ACTIVE_STATUSES = {"pending", "planned", "confirmed"}
CLOSED_STATUSES = {"paid", "cancelled", "canceled", "void", "done"}

PENDING_INTENT_KEYWORDS = {
    "pending", "rencana", "planning", "plan", "nanti", "akan",
    "bakal", "perlu", "butuh", "kudu", "harus",
}
DEBT_LIKE_KEYWORDS = {
    "hutang", "utang", "piutang", "minjem", "pinjem", "pinjam",
    "dipinjem", "dipinjam", "talangin", "ditalangin", "dibayarin",
}
PAST_OR_ACTUAL_KEYWORDS = {
    "sudah", "udah", "sdh", "barusan", "tadi", "kemarin", "baru aja",
}

MONTH_ALIASES_ID = {
    "januari": 1,
    "jan": 1,
    "februari": 2,
    "feb": 2,
    "maret": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "mei": 5,
    "may": 5,
    "juni": 6,
    "jun": 6,
    "juli": 7,
    "jul": 7,
    "agustus": 8,
    "agus": 8,
    "agt": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "oktober": 10,
    "okt": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "desember": 12,
    "des": 12,
    "dec": 12,
}


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today() -> date:
    return datetime.now().date()


def current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def format_rupiah(amount: float) -> str:
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except Exception:
        return default


def generate_pending_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = uuid.uuid4().hex[:8]
    return f"pend_{timestamp}_{suffix}"


def normalize_month(month: str | None = None) -> str:
    if not month:
        return current_month()

    raw = str(month or "").strip().lower().replace("/", "-")
    raw = re.sub(r"\s+", " ", raw)

    if raw in {"bulan ini", "bulanini", "this month", "month", "sekarang"}:
        return current_month()
    if raw in {"bulan lalu", "bulanlalu", "last month"}:
        return add_months(current_month(), -1)
    if raw in {"bulan depan", "bulandepan", "next month"}:
        return add_months(current_month(), 1)

    match = re.fullmatch(r"(20\d{2})[-\s](0?[1-9]|1[0-2])", raw)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"

    # Juli 2026 / Jul 2026
    match = re.fullmatch(r"([a-zA-ZÀ-ÿ]+)\s+(20\d{2})", raw)
    if match:
        month_num = MONTH_ALIASES_ID.get(match.group(1).lower())
        if month_num:
            return f"{int(match.group(2)):04d}-{month_num:02d}"

    raise ValueError("Format bulan pending tidak dikenali. Gunakan YYYY-MM, bulan ini, bulan lalu, bulan depan, atau all.")


def add_months(month: str, delta: int) -> str:
    year, month_num = map(int, month.split("-"))
    month_num += delta
    while month_num <= 0:
        month_num += 12
        year -= 1
    while month_num > 12:
        month_num -= 12
        year += 1
    return f"{year:04d}-{month_num:02d}"


def month_last_day(year: int, month_num: int) -> int:
    return calendar.monthrange(year, month_num)[1]


def parse_day_current_or_next_month(day_raw: str) -> str | None:
    try:
        day_num = int(day_raw)
    except Exception:
        return None
    if day_num < 1 or day_num > 31:
        return None

    base = today()
    target_day = min(day_num, month_last_day(base.year, base.month))
    target = date(base.year, base.month, target_day)

    # Untuk pending, kalau tanggalnya sudah lewat jauh di bulan ini,
    # asumsi user maksud tanggal itu di bulan depan.
    if target < base:
        next_month = add_months(base.strftime("%Y-%m"), 1)
        y, m = map(int, next_month.split("-"))
        target_day = min(day_num, month_last_day(y, m))
        target = date(y, m, target_day)

    return target.strftime("%Y-%m-%d")


def parse_month_only_from_text(text: str) -> str | None:
    clean = str(text or "").strip().lower().replace("/", "-")

    if re.search(r"\bbulan\s+ini\b", clean):
        return current_month()
    if re.search(r"\bbulan\s+lalu\b", clean):
        return add_months(current_month(), -1)
    if re.search(r"\bbulan\s+depan\b", clean):
        return add_months(current_month(), 1)

    match = re.search(r"\b(20\d{2})[-\s](0?[1-9]|1[0-2])\b", clean)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"

    match = re.search(r"\b([a-zA-ZÀ-ÿ]+)\s+(20\d{2})\b", clean)
    if match:
        month_num = MONTH_ALIASES_ID.get(match.group(1).lower())
        if month_num:
            return f"{int(match.group(2)):04d}-{month_num:02d}"

    return None


def detect_pending_due(text: str) -> tuple[str, str, str]:
    """Kembalikan due_date, month, dan due_precision.

    due_precision:
    - exact   : due_date pasti
    - month   : hanya bulan/periode yang diketahui
    - unknown : tidak tahu tanggal pasti, default bucket bulan ini
    """
    clean = str(text or "").strip().lower().replace("/", "-")
    base = today()

    # Tanggal lengkap dengan prefix atau bare: 2026-07-05 / 05-07-2026
    prefixed = re.search(
        r"\b(?:tanggal|tgl|tg|date|pada tanggal)\s+"
        r"(20\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])|"
        r"(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]20\d{2})\b",
        clean,
        flags=re.IGNORECASE,
    )
    if prefixed:
        parsed = parse_explicit_date(prefixed.group(1))
        if parsed:
            return parsed, parsed[:7], "exact"

    bare = re.search(
        r"\b(20\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])|"
        r"(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]20\d{2})\b",
        clean,
        flags=re.IGNORECASE,
    )
    if bare:
        parsed = parse_explicit_date(bare.group(1))
        if parsed:
            return parsed, parsed[:7], "exact"

    # Prefix + angka hari saja: tgl 30 / tanggal 5
    day_only = re.search(r"\b(?:tanggal|tgl|tg|date|pada tanggal)\s+(0?[1-9]|[12]\d|3[01])\b", clean)
    if day_only:
        parsed = parse_day_current_or_next_month(day_only.group(1))
        if parsed:
            return parsed, parsed[:7], "exact"

    # Frasa tanggal masa depan.
    if re.search(r"\bbesok\b", clean):
        target = base + timedelta(days=1)
        return target.strftime("%Y-%m-%d"), target.strftime("%Y-%m"), "exact"
    if re.search(r"\blusa\b", clean):
        target = base + timedelta(days=2)
        return target.strftime("%Y-%m-%d"), target.strftime("%Y-%m"), "exact"
    if re.search(r"\bminggu\s+depan\b|\bpekan\s+depan\b", clean):
        target = base + timedelta(days=7)
        return target.strftime("%Y-%m-%d"), target.strftime("%Y-%m"), "exact"
    if re.search(r"\bakhir\s+bulan\b", clean):
        target = date(base.year, base.month, month_last_day(base.year, base.month))
        return target.strftime("%Y-%m-%d"), target.strftime("%Y-%m"), "exact"

    month_only = parse_month_only_from_text(clean)
    if month_only:
        return "", month_only, "month"

    return "", current_month(), "unknown"



def has_past_time_marker(text: str) -> bool:
    """True kalau teks jelas merujuk waktu yang sudah lewat.

    Ini dipakai sebagai guard agar natural pending tidak menimpa parser
    transaksi aktual. Contoh yang harus tetap transaksi aktual:
    - beli galon 24k kemarin
    - beli nasi 20k 2 hari lalu
    - beli token 500k 20-06-2026  (kalau hari ini setelah tanggal itu)
    - beli bensin 30k minggu lalu
    """
    clean = str(text or "").strip().lower().replace("/", "-")
    if not clean:
        return False

    # Frasa lampau eksplisit.
    if re.search(
        r"\b(kemarin|tadi|barusan|baru aja|minggu lalu|pekan lalu|bulan lalu|tahun lalu)\b",
        clean,
    ):
        return True

    # Pola relatif lampau: 2 hari lalu, 3 minggu yang lalu, dua hari lalu, dst.
    if re.search(
        r"\b(?:\d+|satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh)\s+"
        r"(?:hari|minggu|pekan|bulan|tahun)\s+(?:yang\s+)?lalu\b",
        clean,
    ):
        return True

    # Tanggal lengkap masa lampau, baik dengan prefix maupun bare.
    date_candidates = []
    for match in re.finditer(
        r"\b(?:tanggal|tgl|tg|date|pada tanggal)?\s*"
        r"(20\d{2}[-](?:0?[1-9]|1[0-2])[-](?:0?[1-9]|[12]\d|3[01])|"
        r"(?:0?[1-9]|[12]\d|3[01])[-](?:0?[1-9]|1[0-2])[-]20\d{2})\b",
        clean,
        flags=re.IGNORECASE,
    ):
        date_candidates.append(match.group(1))

    for candidate in date_candidates:
        parsed = parse_explicit_date(candidate)
        if parsed:
            try:
                parsed_date = datetime.strptime(parsed, "%Y-%m-%d").date()
                if parsed_date < today():
                    return True
            except Exception:
                pass

    return False

def clean_pending_text(text: str) -> str:
    clean = str(text or "").strip()
    clean = re.sub(r"^/(pending_add|pending|rencana)\b", "", clean, flags=re.IGNORECASE).strip()

    # Buang prefix natural yang menunjukkan ini rencana/pending, bukan transaksi aktual.
    # Contoh:
    # - nanti perlu bayar wisuda 750k -> bayar wisuda 750k
    # - perlu 750k buat bayar wisuda -> 750k buat bayar wisuda
    # - bakal service motor 300k -> service motor 300k
    clean = re.sub(
        r"^(pengeluaran\s+)?(?:pending|rencana|planning|plan|nanti|akan|bakal|perlu|butuh|kudu|harus)\b",
        "",
        clean,
        flags=re.IGNORECASE,
    ).strip()
    clean = re.sub(
        r"^(?:perlu|butuh|kudu|harus)\s+(?:bayar|beli|buat|untuk)\b",
        "",
        clean,
        flags=re.IGNORECASE,
    ).strip()
    return clean


def is_pending_expense_text(text: str) -> bool:
    """Deteksi input natural untuk pending expense.

    Guard:
    - Harus ada nominal.
    - Harus ada keyword future/planning yang cukup jelas.
    - Hindari bentrok dengan debt/hutang dan transaksi aktual/past-tense.
    """
    raw = str(text or "").strip()
    if not raw or raw.startswith("/"):
        return False

    clean = re.sub(r"\s+", " ", raw.lower()).strip()

    amount = extract_amount_from_text(clean)
    if not amount or amount <= 0:
        return False

    if any(keyword in clean for keyword in DEBT_LIKE_KEYWORDS):
        return False

    # Kalau user jelas menandai sudah terjadi / tanggalnya masa lampau,
    # biarkan masuk parser transaksi aktual. Ini mencegah pending overwrite
    # input seperti "kemarin", "2 hari lalu", atau "20-06-2026".
    if any(keyword in clean for keyword in PAST_OR_ACTUAL_KEYWORDS) or has_past_time_marker(clean):
        return False

    starts_with_pending = re.match(
        r"^(pending|rencana|planning|plan|nanti|akan|bakal|perlu|butuh|kudu|harus)\b",
        clean,
    )
    if starts_with_pending:
        return True

    # Jangan overwrite parser transaksi aktual.
    # Contoh: "beli galon 24k dibagi 4 ... tanggal 10" adalah transaksi aktual
    # bertanggal 10 bulan berjalan, bukan pending expense.
    if re.search(r"\b(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)\b", clean):
        return False

    # Bentuk lain yang boleh dianggap pending tanpa keyword pembuka hanya jika
    # marker waktunya jelas masa depan, misalnya:
    # - "bulan depan bayar wifi 285k"
    # - "minggu depan service motor 300k"
    # - "besok service motor 300k"
    #
    # Catatan penting: "tanggal 10" sengaja TIDAK dianggap future marker.
    # Di bot ini, tanggal angka saja berarti tanggal di bulan berjalan dan harus
    # tetap masuk parser transaksi normal.
    future_time_marker = re.search(
        r"\b(besok|lusa|minggu depan|pekan depan|bulan depan|akhir bulan)\b",
        clean,
    )
    action_marker = re.search(
        r"\b(bayar|beli|service|servis|buat|untuk|tagihan|iuran|perpanjang|top up|isi)\b",
        clean,
    )
    if future_time_marker and action_marker:
        return True

    return False


def strip_pending_time_phrases(text: str) -> str:
    clean = str(text or "")
    clean = re.sub(r"\b(?:besok|lusa|minggu depan|pekan depan|bulan depan|bulan ini|bulan lalu|akhir bulan)\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])(?:[-/](0?[1-9]|[12]\d|3[01]))?\b", " ", clean)
    clean = re.sub(r"\b(?:tanggal|tgl|tg|date|pada tanggal)\s+(?:0?[1-9]|[12]\d|3[01])\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def infer_category(text: str, parsed: dict | None = None) -> str:
    if parsed and parsed.get("category"):
        return str(parsed.get("category")).strip()

    clean = str(text or "").lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(str(keyword).lower() in clean for keyword in keywords):
            return category
    return "Other Expense"


def infer_account(text: str, parsed: dict | None = None) -> str:
    if parsed and parsed.get("account"):
        return str(parsed.get("account")).strip()

    clean = str(text or "").lower()
    found = []
    for account in sorted(ACCOUNT_NAMES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(account)}\b", clean):
            found.append(ACCOUNT_DISPLAY_NAMES.get(account, account.upper()))
    return found[0] if found else ""


def title_from_description(description: str) -> str:
    clean = str(description or "").strip()
    clean = re.sub(r"^(?:beli|bayar|buat|untuk|tagihan)\s+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean.title() if clean else "Pending Expense"


def build_pending_row(item: dict) -> list:
    return [item.get(col, "") for col in PENDING_EXPENSE_COLUMNS]


def build_pending_expense_from_text(text: str) -> dict:
    """Parsing input pending expense menjadi item, tanpa menyimpan ke Google Sheets.

    Dipakai untuk preview + tombol Simpan/Batal. Penyimpanan sebenarnya
    dilakukan oleh save_pending_expense() setelah user klik Simpan.
    """
    raw_input = str(text or "").strip()
    clean_text = clean_pending_text(raw_input)

    if not clean_text:
        raise ValueError("Tulis rencana/pending expense setelah command.")

    amount = extract_amount_from_text(clean_text)
    if not amount or amount <= 0:
        raise ValueError("Nominal pending expense belum terbaca. Contoh: /pending_add bayar wifi 285k")

    due_date, month, due_precision = detect_pending_due(clean_text)
    parsed = parse_with_regex(clean_text) or {}
    category = infer_category(clean_text, parsed)
    account = infer_account(clean_text, parsed)

    description = parsed.get("description") or extract_description(clean_text, amount) or clean_text
    description = strip_pending_time_phrases(description)
    description = re.sub(r"\s+", " ", description).strip()
    subject = parsed.get("subject") or title_from_description(description)

    created_at = now_str()
    return {
        "id": generate_pending_id(),
        "due_date": due_date,
        "month": month,
        "due_precision": due_precision,
        "amount": float(amount),
        "category": category,
        "account": account,
        "subject": subject,
        "description": description or subject,
        "status": "pending",
        "created_at": created_at,
        "updated_at": created_at,
        "paid_transaction_id": "",
        "raw_input": raw_input,
    }


def save_pending_expense(item: dict) -> dict:
    """Simpan item pending expense yang sudah dipreview/di-confirm user."""
    item = dict(item or {})
    if not item.get("id"):
        item["id"] = generate_pending_id()
    if not item.get("created_at"):
        item["created_at"] = now_str()
    item["updated_at"] = now_str()
    item["status"] = item.get("status") or "pending"
    item.setdefault("paid_transaction_id", "")
    append_row_raw(SHEET_PENDING_EXPENSES, build_pending_row(item))
    return item


def add_pending_expense_from_text(text: str) -> dict:
    """Parsing dan langsung simpan pending expense.

    Dipertahankan untuk kompatibilitas internal. Untuk flow Telegram user-facing,
    gunakan build_pending_expense_from_text() + save_pending_expense() agar ada
    preview Simpan/Batal.
    """
    return save_pending_expense(build_pending_expense_from_text(text))


def get_pending_expenses(period: str | None = None, active_only: bool = True) -> dict:
    records = get_all_records(SHEET_PENDING_EXPENSES)
    clean_period = str(period or "").strip().lower()

    filter_type = "month"
    label = current_month()
    month = current_month()

    if clean_period in {"all", "semua", "seluruh"}:
        filter_type = "all"
        label = "semua periode"
        month = ""
    elif clean_period in {"no_date", "tanpa_tanggal", "tanpa tanggal", "belum pasti", "unknown"}:
        filter_type = "unknown"
        label = "tanggal belum pasti"
        month = ""
    elif clean_period:
        month = normalize_month(clean_period)
        label = month
    else:
        month = current_month()
        label = month

    filtered = []
    for row in records:
        status = str(row.get("status", "pending") or "pending").strip().lower()
        if active_only and status in CLOSED_STATUSES:
            continue

        row_month = str(row.get("month", "") or "").strip()
        due_precision = str(row.get("due_precision", "") or "").strip().lower()

        if filter_type == "all":
            filtered.append(row)
        elif filter_type == "unknown":
            if due_precision == "unknown" or not str(row.get("due_date", "") or "").strip():
                filtered.append(row)
        else:
            if row_month == month:
                filtered.append(row)

    def sort_key(item: dict):
        due = str(item.get("due_date", "") or "")
        return (due == "", due or "9999-99-99", str(item.get("created_at", "")))

    filtered = sorted(filtered, key=sort_key)
    total = sum(safe_float(item.get("amount")) for item in filtered)

    return {
        "items": filtered,
        "total": total,
        "count": len(filtered),
        "filter_type": filter_type,
        "month": month,
        "label": label,
        "active_only": active_only,
    }


def find_pending_by_ref(ref: str) -> tuple[int | None, dict | None]:
    ref = str(ref or "").strip()
    if not ref:
        return None, None

    records = get_all_records(SHEET_PENDING_EXPENSES)
    for row_index, row in enumerate(records, start=2):
        pending_id = str(row.get("id", "") or "").strip()
        if pending_id == ref or pending_id.lower().startswith(ref.lower()):
            return row_index, row
    return None, None


def update_pending_status(row_index: int, status: str, paid_transaction_id: str = "") -> None:
    # Columns: status=10, updated_at=12, paid_transaction_id=13
    update_cell(SHEET_PENDING_EXPENSES, row_index, 10, status)
    update_cell(SHEET_PENDING_EXPENSES, row_index, 12, now_str())
    if paid_transaction_id:
        update_cell(SHEET_PENDING_EXPENSES, row_index, 13, paid_transaction_id)


def cancel_pending_expense(ref: str) -> dict:
    row_index, item = find_pending_by_ref(ref)
    if not item or not row_index:
        return {"success": False, "message": "Pending expense tidak ditemukan."}

    status = str(item.get("status", "pending") or "pending").strip().lower()
    if status in CLOSED_STATUSES:
        return {"success": False, "message": f"Pending expense sudah berstatus {status}."}

    update_pending_status(row_index, "cancelled")
    return {"success": True, "item": item, "message": "ok"}


def mark_pending_paid(ref: str, account: str | None = None, paid_date: str | None = None) -> dict:
    row_index, item = find_pending_by_ref(ref)
    if not item or not row_index:
        return {"success": False, "message": "Pending expense tidak ditemukan."}

    status = str(item.get("status", "pending") or "pending").strip().lower()
    if status in CLOSED_STATUSES:
        return {"success": False, "message": f"Pending expense sudah berstatus {status}."}

    paid_date = str(paid_date or "").strip() or datetime.now().strftime("%Y-%m-%d")
    txn_account = str(account or item.get("account") or "").strip()
    if not txn_account:
        return {
            "success": False,
            "message": "Rekening belum diketahui. Gunakan: /pending_paid pending_id BRI",
        }

    parsed = {
        "type": "expense",
        "amount": safe_float(item.get("amount")),
        "category": item.get("category") or "Other Expense",
        "account": txn_account,
        "to_account": "",
        "subject": item.get("subject") or item.get("description") or "Pending Expense",
        "description": item.get("description") or item.get("subject") or "Pending Expense",
        "catatan": f"Dibayar dari pending expense {item.get('id')}",
        "tipe_pengeluaran": "Bulanan",
        "date": paid_date,
        "parsed_by": "pending_expense",
    }

    result = save_transaction(parsed, item.get("raw_input") or parsed["description"])
    if not result.get("success"):
        return result

    txn_id = result.get("transaction_id") or ""
    update_pending_status(row_index, "paid", txn_id)
    return {
        "success": True,
        "item": item,
        "transaction_id": txn_id,
        "new_balance": result.get("new_balance"),
        "message": "ok",
    }
