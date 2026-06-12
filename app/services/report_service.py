from datetime import datetime, timedelta
import re

from app.sheets.client import get_all_records
from app.config import SHEET_TRANSACTIONS


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_transaction_records_for_report() -> list[dict]:
    """
    Ambil semua transaksi untuk laporan.

    Penting:
    - Tambahkan _row_index supaya hasil /transaksi bisa dipakai oleh /delete_txn dan /edit_txn.
    - Row index Google Sheets dimulai dari 1, sedangkan row 1 adalah header, jadi data pertama = row 2.
    """
    records = get_all_records(SHEET_TRANSACTIONS)
    result = []

    for i, record in enumerate(records, start=2):
        item = dict(record or {})
        item["_row_index"] = i
        result.append(item)

    return result


def format_rupiah(amount: float) -> str:
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")


def safe_float(value, default: float = 0.0) -> float:
    """Parse amount dari number/string Google Sheets secara aman."""
    if value is None or value == "":
        return default

    if isinstance(value, (int, float)):
        return float(value)

    raw = str(value).strip()
    if not raw:
        return default

    # Format Indonesia umum: 10.000, 10,000, Rp10.000
    raw = raw.replace("Rp", "").replace("rp", "").strip()

    # Kalau ada titik dan koma, asumsi titik ribuan, koma desimal.
    if "." in raw and "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    # Kalau hanya koma, gunakan sebagai desimal kalau tampak desimal; selain itu ribuan.
    elif "," in raw:
        parts = raw.split(",")
        if len(parts[-1]) == 2:
            raw = raw.replace(",", ".")
        else:
            raw = raw.replace(",", "")
    # Kalau hanya titik dan bagian belakang 3 digit, anggap ribuan.
    elif "." in raw:
        parts = raw.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            raw = raw.replace(".", "")

    raw = re.sub(r"[^0-9.-]", "", raw)

    try:
        return float(raw)
    except Exception:
        return default


def parse_report_date_arg(value: str | None = None) -> str:
    """
    Normalize argumen tanggal laporan ke YYYY-MM-DD.

    Support:
    - None / kosong -> hari ini
    - today / hariini / hari ini
    - yesterday / kemarin
    - 2026-06-01
    - 01-06-2026 / 01/06/2026
    - 1 / tanggal 1 / tgl 1 -> bulan & tahun sekarang
    """
    today = datetime.now().date()

    if not value:
        return today.strftime("%Y-%m-%d")

    raw = str(value).strip().lower()
    raw = re.sub(r"^(tanggal|tgl|tg)\s+", "", raw).strip()
    raw = raw.replace("/", "-")

    if raw in ["today", "hariini", "hari ini", "sekarang"]:
        return today.strftime("%Y-%m-%d")

    if raw in ["yesterday", "kemarin"]:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    m = re.fullmatch(r"(20\d{2})-(\d{1,2})-(\d{1,2})", raw)
    if m:
        dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
        return dt.strftime("%Y-%m-%d")

    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(20\d{2})", raw)
    if m:
        dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date()
        return dt.strftime("%Y-%m-%d")

    if re.fullmatch(r"\d{1,2}", raw):
        day = int(raw)
        dt = datetime(today.year, today.month, day).date()
        return dt.strftime("%Y-%m-%d")

    raise ValueError("Format tanggal tidak dikenali. Contoh: 2026-06-01, 01-06-2026, atau 1.")


def parse_report_month_arg(value: str | None = None) -> tuple[int, int]:
    """Normalize argumen bulan laporan ke (year, month)."""
    today = datetime.now().date()

    if not value:
        return today.year, today.month

    raw = str(value).strip().lower().replace("/", "-")

    if raw in ["month", "bulan", "bulanan", "bulanini", "bulan ini"]:
        return today.year, today.month

    m = re.fullmatch(r"(20\d{2})-(\d{1,2})", raw)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        if not 1 <= month <= 12:
            raise ValueError("Bulan harus antara 1 sampai 12.")
        return year, month

    m = re.fullmatch(r"(\d{1,2})-(20\d{2})", raw)
    if m:
        month = int(m.group(1))
        year = int(m.group(2))
        if not 1 <= month <= 12:
            raise ValueError("Bulan harus antara 1 sampai 12.")
        return year, month

    if re.fullmatch(r"\d{1,2}", raw):
        month = int(raw)
        if not 1 <= month <= 12:
            raise ValueError("Bulan harus antara 1 sampai 12.")
        return today.year, month

    raise ValueError("Format bulan tidak dikenali. Contoh: 2026-06 atau 6.")


def get_week_range(reference_date: str | None = None) -> tuple[str, str]:
    """Return (monday, sunday) minggu dari reference_date dalam format YYYY-MM-DD."""
    base_date = datetime.strptime(parse_report_date_arg(reference_date), "%Y-%m-%d").date()
    monday = base_date - timedelta(days=base_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def get_month_range(year: int | None = None, month: int | None = None) -> tuple[str, str]:
    """Return (first_day, last_day) bulan dalam format YYYY-MM-DD."""
    now = datetime.now()
    year = int(year or now.year)
    month = int(month or now.month)

    if not 1 <= month <= 12:
        raise ValueError("Bulan harus antara 1 sampai 12.")

    first_dt = datetime(year, month, 1)
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    last_dt = next_month - timedelta(days=1)
    return first_dt.strftime("%Y-%m-%d"), last_dt.strftime("%Y-%m-%d")


def filter_transactions(
    records: list[dict],
    date_from: str | None = None,
    date_to: str | None = None,
    txn_type: str | None = None,
) -> list[dict]:
    """Filter transaksi berdasarkan rentang tanggal dan/atau tipe."""
    result = []

    for r in records:
        date = str(r.get("date", "")).strip()
        record_type = str(r.get("type", "")).strip().lower()

        if not date:
            continue
        if date_from and date < date_from:
            continue
        if date_to and date > date_to:
            continue
        if txn_type and record_type != str(txn_type).strip().lower():
            continue

        result.append(r)

    return result


def summarize(transactions: list[dict]) -> dict:
    """
    Hitung total income, expense, transfer, net, dan breakdown per kategori.
    """
    total_income = 0.0
    total_expense = 0.0
    total_transfer = 0.0
    by_category = {}

    for t in transactions:
        amount = safe_float(t.get("amount", 0))
        txn_type = str(t.get("type", "")).strip().lower()
        category = str(t.get("category") or "Other").strip() or "Other"

        if txn_type == "income":
            total_income += amount
        elif txn_type == "expense":
            total_expense += amount
            by_category[category] = by_category.get(category, 0.0) + amount
        elif txn_type == "transfer":
            total_transfer += amount

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "total_transfer": total_transfer,
        "net": total_income - total_expense,
        "by_category": dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True)),
        "count": len(transactions),
    }


# ── Report functions ──────────────────────────────────────────────────────────

def get_daily_report(date_str: str | None = None) -> dict:
    """Laporan harian untuk tanggal tertentu. Default: hari ini."""
    date_str = parse_report_date_arg(date_str)
    records = get_transaction_records_for_report()
    transactions = filter_transactions(records, date_from=date_str, date_to=date_str)
    transactions.sort(key=lambda x: int(x.get("_row_index", 0) or 0), reverse=True)

    summary = summarize(transactions)
    summary["date"] = date_str
    summary["transactions"] = transactions
    return summary


def get_weekly_report(reference_date: str | None = None) -> dict:
    """Laporan mingguan — Senin sampai Minggu dari reference_date."""
    date_from, date_to = get_week_range(reference_date)
    records = get_transaction_records_for_report()
    transactions = filter_transactions(records, date_from=date_from, date_to=date_to)
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    summary = summarize(transactions)
    summary["date_from"] = date_from
    summary["date_to"] = date_to
    summary["transactions"] = transactions
    return summary


def get_monthly_report(year: int | None = None, month: int | None = None) -> dict:
    """Laporan bulanan."""
    date_from, date_to = get_month_range(year, month)
    month_label = date_from[:7]

    records = get_transaction_records_for_report()
    transactions = filter_transactions(records, date_from=date_from, date_to=date_to)
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    summary = summarize(transactions)
    summary["date_from"] = date_from
    summary["date_to"] = date_to
    summary["month"] = month_label
    summary["transactions"] = transactions
    return summary


def search_transactions(keyword: str, limit: int = 10) -> list[dict]:
    """
    Cari transaksi berdasarkan keyword di kolom description, subject, category, atau raw_input.
    Return max `limit` hasil terbaru.
    """
    keyword_lower = str(keyword or "").strip().lower()
    if not keyword_lower:
        return []

    records = get_transaction_records_for_report()
    results = []

    for r in records:
        searchable = " ".join([
            str(r.get("description", "")),
            str(r.get("subject", "")),
            str(r.get("category", "")),
            str(r.get("account", "")),
            str(r.get("to_account", "")),
            str(r.get("raw_input", "")),
        ]).lower()

        if keyword_lower in searchable:
            results.append(r)

    results.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)
    return results[:limit]


def get_top_expenses(month: str | None = None, top_n: int = 5) -> list[dict]:
    """Ambil N transaksi expense terbesar dalam sebulan."""
    if not month:
        month = datetime.now().strftime("%Y-%m")

    records = get_transaction_records_for_report()
    expenses = [
        r for r in records
        if str(r.get("type", "")).strip().lower() == "expense"
        and str(r.get("date", "")).startswith(str(month))
    ]

    expenses.sort(key=lambda x: safe_float(x.get("amount", 0)), reverse=True)
    return expenses[:top_n]
