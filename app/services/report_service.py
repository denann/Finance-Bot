from datetime import datetime, timedelta
import re
from app.sheets.client import get_all_records
from app.config import SHEET_TRANSACTIONS, SHEET_ACCOUNTS


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_transaction_records_for_report() -> list[dict]:
    """Ambil transaksi dengan _row_index agar hasil /transaksi bisa dipakai delete/edit."""
    records = get_transaction_records_for_report()
    result = []
    for i, record in enumerate(records):
        item = dict(record)
        item["_row_index"] = i + 2
        result.append(item)
    return result



def format_rupiah(amount: float) -> str:
    return f"Rp{int(amount):,}".replace(",", ".")


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

    if raw in ["today", "hariini", "hari ini"]:
        return today.strftime("%Y-%m-%d")

    if raw in ["yesterday", "kemarin"]:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    m = re.fullmatch(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", raw)
    if m:
        dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
        return dt.strftime("%Y-%m-%d")

    m = re.fullmatch(r"(\d{1,2})[-/](\d{1,2})[-/](20\d{2})", raw)
    if m:
        dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date()
        return dt.strftime("%Y-%m-%d")

    m = re.fullmatch(r"\d{1,2}", raw)
    if m:
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
        return int(m.group(1)), int(m.group(2))

    m = re.fullmatch(r"(\d{1,2})-(20\d{2})", raw)
    if m:
        return int(m.group(2)), int(m.group(1))

    m = re.fullmatch(r"\d{1,2}", raw)
    if m:
        return today.year, int(raw)

    raise ValueError("Format bulan tidak dikenali. Contoh: 2026-06 atau 6.")


def get_week_range(reference_date: str | None = None) -> tuple[str, str]:
    """Return (monday, sunday) minggu dari reference_date dalam format YYYY-MM-DD."""
    if reference_date:
        base = datetime.strptime(parse_report_date_arg(reference_date), "%Y-%m-%d")
    else:
        base = datetime.now()

    monday = base - timedelta(days=base.weekday())
    sunday = monday + timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def get_month_range(year: int = None, month: int = None) -> tuple[str, str]:
    """Return (first_day, last_day) bulan ini dalam format YYYY-MM-DD."""
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    first = f"{year}-{month:02d}-01"

    # Last day of month
    if month == 12:
        last = f"{year}-12-31"
    else:
        last = (datetime(year, month + 1, 1) - timedelta(days=1)).strftime("%Y-%m-%d")

    return first, last


def filter_transactions(
    records: list[dict],
    date_from: str = None,
    date_to: str = None,
    txn_type: str = None,
) -> list[dict]:
    """Filter transaksi berdasarkan rentang tanggal dan/atau tipe."""
    result = []
    for r in records:
        date = str(r.get("date", ""))

        if date_from and date < date_from:
            continue
        if date_to and date > date_to:
            continue
        if txn_type and r.get("type") != txn_type:
            continue

        result.append(r)
    return result


def summarize(transactions: list[dict]) -> dict:
    """
    Hitung total income, expense, net, dan breakdown per kategori.

    Return:
    {
        "total_income": float,
        "total_expense": float,
        "net": float,
        "by_category": {"Food & Beverage": 250000, ...},
        "count": int,
    }
    """
    total_income = 0.0
    total_expense = 0.0
    by_category = {}

    for t in transactions:
        amount = float(t.get("amount", 0))
        txn_type = t.get("type")
        category = t.get("category") or "Other"

        if txn_type == "income":
            total_income += amount
        elif txn_type == "expense":
            total_expense += amount
            by_category[category] = by_category.get(category, 0) + amount

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net": total_income - total_expense,
        "by_category": dict(
            sorted(by_category.items(), key=lambda x: x[1], reverse=True)
        ),
        "count": len(transactions),
    }


# ── Report functions ──────────────────────────────────────────────────────────

def get_daily_report(date_str: str = None) -> dict:
    """Laporan harian untuk tanggal tertentu. Default: hari ini."""
    date_str = parse_report_date_arg(date_str)

    records = get_transaction_records_for_report()
    transactions = filter_transactions(records, date_from=date_str, date_to=date_str)
    summary = summarize(transactions)
    summary["date"] = date_str
    summary["transactions"] = transactions
    return summary


def get_weekly_report(reference_date: str = None) -> dict:
    """Laporan mingguan — Senin sampai Minggu dari reference_date."""
    date_from, date_to = get_week_range(reference_date)
    records = get_transaction_records_for_report()
    transactions = filter_transactions(records, date_from=date_from, date_to=date_to)
    summary = summarize(transactions)
    summary["date_from"] = date_from
    summary["date_to"] = date_to
    summary["transactions"] = transactions
    return summary


def get_monthly_report(year: int = None, month: int = None) -> dict:
    """Laporan bulanan."""
    now = datetime.now()
    year = now.year if year is None else year
    month = now.month if month is None else month
    date_from, date_to = get_month_range(year, month)

    records = get_transaction_records_for_report()
    transactions = filter_transactions(records, date_from=date_from, date_to=date_to)
    summary = summarize(transactions)
    summary["date_from"] = date_from
    summary["date_to"] = date_to
    summary["month"] = f"{year}-{month:02d}"
    summary["transactions"] = transactions
    return summary


def search_transactions(keyword: str, limit: int = 10) -> list[dict]:
    """
    Cari transaksi berdasarkan keyword di kolom description atau category.
    Return max `limit` hasil terbaru.
    """
    keyword_lower = keyword.lower()
    records = get_transaction_records_for_report()
    results = []

    for r in records:
        desc = str(r.get("description", "")).lower()
        cat = str(r.get("category", "")).lower()
        raw = str(r.get("raw_input", "")).lower()

        if keyword_lower in desc or keyword_lower in cat or keyword_lower in raw:
            results.append(r)

    # Sort terbaru dulu, ambil limit teratas
    results.sort(key=lambda x: str(x.get("date", "")), reverse=True)
    return results[:limit]


def get_top_expenses(month: str = None, top_n: int = 5) -> list[dict]:
    """
    Ambil N transaksi expense terbesar dalam sebulan.
    """
    if not month:
        month = datetime.now().strftime("%Y-%m")

    records = get_transaction_records_for_report()
    expenses = [
        r for r in records
        if r.get("type") == "expense"
        and str(r.get("date", "")).startswith(month)
    ]

    expenses.sort(key=lambda x: float(x.get("amount", 0)), reverse=True)
    return expenses[:top_n]