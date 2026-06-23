from datetime import datetime, timedelta
import re

from app.sheets.client import get_all_records
from app.config import SHEET_TRANSACTIONS, SHEET_DEBTS


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



def normalize_category_key(value: str | None) -> str:
    """Normalisasi nama kategori untuk matching yang toleran spasi/simbol."""
    raw = str(value or "").strip().lower()
    raw = raw.replace("&", " and ")
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


DEFAULT_REPORT_CATEGORIES = [
    "Food & Beverage",
    "Transport",
    "Bills & Utilities",
    "Shopping",
    "Health",
    "Entertainment",
    "Education",
    "Other Expense",
    "Salary",
    "Freelance",
    "Other Income",
    "Piutang Diberikan",
    "Penerimaan Utang",
    "Bayar Utang",
    "Pembayaran Piutang",
    "Utang Tanpa Cashflow",
    "Piutang Tanpa Cashflow",
    "Pembayaran Debt Tanpa Cashflow",
    "Debt Tanpa Cashflow",
    "Kompensasi Hutang/Piutang",
]

CATEGORY_ALIASES = {
    "food": "Food & Beverage",
    "fnb": "Food & Beverage",
    "f b": "Food & Beverage",
    "fb": "Food & Beverage",
    "makan": "Food & Beverage",
    "makanan": "Food & Beverage",
    "minum": "Food & Beverage",
    "minuman": "Food & Beverage",
    "transportasi": "Transport",
    "tagihan": "Bills & Utilities",
    "bills": "Bills & Utilities",
    "utilities": "Bills & Utilities",
    "utilitas": "Bills & Utilities",
    "belanja": "Shopping",
    "kesehatan": "Health",
    "hiburan": "Entertainment",
    "pendidikan": "Education",
    "other": "Other Expense",
    "lainnya": "Other Expense",
    "piutang": "Piutang Diberikan",
    "utang": "Bayar Utang",
}


def get_known_report_categories(records: list[dict] | None = None) -> list[str]:
    """Gabungkan kategori default dan kategori yang benar-benar ada di sheet transaksi."""
    categories = []
    seen = set()

    def add(value):
        value = str(value or "").strip()
        key = normalize_category_key(value)
        if value and key and key not in seen:
            categories.append(value)
            seen.add(key)

    for cat in DEFAULT_REPORT_CATEGORIES:
        add(cat)

    for record in records or []:
        add((record or {}).get("category"))

    return categories


def resolve_category_filter(category_query: str | None, records: list[dict] | None = None) -> str | None:
    """Resolve input kategori user ke nama kategori canonical jika memungkinkan."""
    query = str(category_query or "").strip()
    if not query:
        return None

    query_key = normalize_category_key(query)
    if not query_key:
        return None

    alias_category = CATEGORY_ALIASES.get(query_key)
    if alias_category:
        return alias_category

    categories = get_known_report_categories(records)
    category_by_key = {normalize_category_key(cat): cat for cat in categories}

    if query_key in category_by_key:
        return category_by_key[query_key]

    # Support input pendek seperti `/bulanan food` atau `/bulanan bills`.
    partial_matches = [
        cat for cat in categories
        if query_key in normalize_category_key(cat) or normalize_category_key(cat) in query_key
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]

    # Fallback: tetap pakai input user supaya custom category tetap bisa difilter.
    return query


def split_report_period_and_category_arg(value: str | None, mode: str) -> tuple[str | None, str | None]:
    """
    Pisahkan argumen report menjadi periode dan kategori.

    Contoh:
    - `/bulanan Food & Beverage` -> (None, "Food & Beverage")
    - `/bulanan 2026-06 Food & Beverage` -> ("2026-06", "Food & Beverage")
    - `/mingguan 2026-06-01 Bills & Utilities` -> ("2026-06-01", "Bills & Utilities")
    - `/harian kemarin makan` -> ("kemarin", "makan")
    """
    raw = str(value or "").strip()
    if not raw:
        return None, None

    parser = parse_report_month_arg if mode == "month" else parse_report_date_arg
    tokens = raw.split()
    max_prefix = min(len(tokens), 3)

    # Coba periode di depan argumen. Longest first supaya "hari ini" / "bulan ini" kebaca.
    for n in range(max_prefix, 0, -1):
        candidate = " ".join(tokens[:n]).strip()
        rest = " ".join(tokens[n:]).strip() or None
        try:
            parser(candidate)
            return candidate, rest
        except Exception:
            pass

    # Coba periode di belakang argumen. Ini membuat `/bulanan Food & Beverage 2026-06` tetap bisa.
    for n in range(max_prefix, 0, -1):
        candidate = " ".join(tokens[-n:]).strip()
        rest = " ".join(tokens[:-n]).strip() or None
        try:
            parser(candidate)
            return candidate, rest
        except Exception:
            pass

    return None, raw


def is_truthy_sheet_value(value) -> bool:
    raw = str(value or "").strip().lower()
    return raw in {"true", "yes", "y", "1", "settled", "lunas", "void", "voided"}


def parse_transaction_debt_ids_from_record(txn: dict) -> list[str]:
    """Ambil daftar debt id dari kolom transactions.hutang_id."""
    raw = str((txn or {}).get("hutang_id", "") or "").strip()
    if not raw:
        return []
    return [part.strip() for part in re.split(r"[,;\s]+", raw) if part.strip()]


def build_debt_lookup(active_only: bool = True) -> dict:
    """Index debts berdasarkan id dan source_transaction_id untuk laporan."""
    try:
        records = get_all_records(SHEET_DEBTS)
    except Exception:
        records = []

    by_id = {}
    by_source_txn = {}

    for debt in records:
        item = dict(debt or {})
        debt_id = str(item.get("id", "") or "").strip()
        if not debt_id:
            continue

        settled = is_truthy_sheet_value(item.get("is_settled", "FALSE"))
        remaining = safe_float(item.get("remaining_amount", 0))
        if active_only and (settled or remaining <= 0):
            continue

        by_id[debt_id] = item

        source_txn_id = str(item.get("source_transaction_id", "") or "").strip()
        if source_txn_id:
            by_source_txn.setdefault(source_txn_id, []).append(item)

    return {"by_id": by_id, "by_source_txn": by_source_txn}


def get_linked_debts_for_transaction(txn: dict, lookup: dict) -> list[dict]:
    """Cari debt aktif yang terhubung ke transaksi dari hutang_id atau source_transaction_id."""
    by_id = (lookup or {}).get("by_id", {}) or {}
    by_source_txn = (lookup or {}).get("by_source_txn", {}) or {}

    linked = []
    seen = set()

    for debt_id in parse_transaction_debt_ids_from_record(txn):
        debt = by_id.get(debt_id)
        if debt and debt_id not in seen:
            linked.append(debt)
            seen.add(debt_id)

    txn_id = str((txn or {}).get("id", "") or "").strip()
    for debt in by_source_txn.get(txn_id, []) or []:
        debt_id = str(debt.get("id", "") or "").strip()
        if debt_id and debt_id not in seen:
            linked.append(debt)
            seen.add(debt_id)

    return linked


def enrich_transactions_with_debt_info(transactions: list[dict]) -> list[dict]:
    """Tambahkan ringkasan debt aktif ke setiap transaksi laporan."""
    lookup = build_debt_lookup(active_only=True)
    enriched = []

    for txn in transactions or []:
        item = dict(txn or {})
        linked_debts = get_linked_debts_for_transaction(item, lookup)

        receivable_remaining = 0.0
        payable_remaining = 0.0
        people = []

        for debt in linked_debts:
            amount = safe_float(debt.get("remaining_amount", 0))
            debt_type = str(debt.get("type", "") or "").strip().lower()
            person = str(debt.get("person_name", "") or "").strip()
            if person and person not in people:
                people.append(person)

            if debt_type == "receivable":
                receivable_remaining += amount
            elif debt_type == "payable":
                payable_remaining += amount

        expense_amount = safe_float(item.get("amount", 0))
        item["linked_debts"] = linked_debts
        item["debt_receivable_remaining"] = receivable_remaining
        item["debt_payable_remaining"] = payable_remaining
        item["debt_people"] = people
        item["net_expense_after_receivable"] = max(expense_amount - receivable_remaining, 0.0)
        enriched.append(item)

    return enriched


def build_delta_info(current_value, previous_value, previous_available: bool = True) -> dict:
    """Buat metadata delta yang aman saat data periode sebelumnya belum ada."""
    cur = safe_float(current_value, 0)

    if not previous_available:
        return {
            "current": cur,
            "previous": None,
            "delta": None,
            "pct": None,
            "available": False,
        }

    prev = safe_float(previous_value, 0)
    delta = cur - prev
    pct = (delta / prev * 100) if prev else None

    return {
        "current": cur,
        "previous": prev,
        "delta": delta,
        "pct": pct,
        "available": True,
    }


def build_summary_comparison(current: dict, previous: dict, previous_available: bool = True) -> dict:
    """Buat delta current vs periode sebelumnya."""
    current = current or {}
    previous = previous or {}
    keys = ["total_income", "total_expense", "net", "count"]

    return {
        key: build_delta_info(current.get(key, 0), previous.get(key, 0), previous_available)
        for key in keys
    }


def build_category_comparison(current: dict, previous: dict, previous_available: bool = True) -> dict:
    """Buat delta pengeluaran per kategori vs periode sebelumnya."""
    current = current or {}
    previous = previous or {}
    previous_keys = {normalize_category_key(cat): cat for cat in previous.keys()}
    result = {}

    for category, current_amount in current.items():
        category_key = normalize_category_key(category)
        has_previous_category = previous_available and category_key in previous_keys
        previous_category = previous_keys.get(category_key)
        previous_amount = previous.get(previous_category, 0) if previous_category else 0

        result[category] = build_delta_info(
            current_amount,
            previous_amount,
            previous_available=has_previous_category,
        )

    return result

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
    category: str | None = None,
) -> list[dict]:
    """Filter transaksi berdasarkan rentang tanggal, tipe, dan/atau kategori."""
    result = []
    category_key = normalize_category_key(category) if category else None

    for r in records:
        date = str(r.get("date", "")).strip()
        record_type = str(r.get("type", "")).strip().lower()
        record_category_key = normalize_category_key(r.get("category"))

        if not date:
            continue
        if date_from and date < date_from:
            continue
        if date_to and date > date_to:
            continue
        if txn_type and record_type != str(txn_type).strip().lower():
            continue
        if category_key and record_category_key != category_key:
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

def get_daily_report(date_str: str | None = None, category: str | None = None) -> dict:
    """Laporan harian untuk tanggal tertentu. Default: hari ini."""
    date_str = parse_report_date_arg(date_str)
    current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    previous_date = current_date - timedelta(days=1)
    previous_date_str = previous_date.strftime("%Y-%m-%d")

    records = get_transaction_records_for_report()
    category_filter = resolve_category_filter(category, records)
    transactions = filter_transactions(records, date_from=date_str, date_to=date_str, category=category_filter)
    transactions.sort(key=lambda x: int(x.get("_row_index", 0) or 0), reverse=True)

    previous_transactions = filter_transactions(
        records,
        date_from=previous_date_str,
        date_to=previous_date_str,
        category=category_filter,
    )
    previous_summary = summarize(previous_transactions)
    previous_available = len(previous_transactions) > 0

    summary = summarize(transactions)
    summary["date"] = date_str
    summary["previous_date"] = previous_date_str
    summary["category_filter"] = category_filter
    summary["comparison"] = build_summary_comparison(summary, previous_summary, previous_available)
    summary["category_comparison"] = build_category_comparison(
        summary.get("by_category", {}),
        previous_summary.get("by_category", {}),
        previous_available,
    )
    summary["transactions"] = enrich_transactions_with_debt_info(transactions)
    return summary


def get_weekly_report(reference_date: str | None = None, category: str | None = None) -> dict:
    """Laporan mingguan — Senin sampai Minggu dari reference_date."""
    date_from, date_to = get_week_range(reference_date)
    current_start = datetime.strptime(date_from, "%Y-%m-%d").date()
    previous_start = current_start - timedelta(days=7)
    previous_end = current_start - timedelta(days=1)
    previous_from = previous_start.strftime("%Y-%m-%d")
    previous_to = previous_end.strftime("%Y-%m-%d")

    records = get_transaction_records_for_report()
    category_filter = resolve_category_filter(category, records)
    transactions = filter_transactions(records, date_from=date_from, date_to=date_to, category=category_filter)
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    previous_transactions = filter_transactions(
        records,
        date_from=previous_from,
        date_to=previous_to,
        category=category_filter,
    )
    previous_summary = summarize(previous_transactions)
    previous_available = len(previous_transactions) > 0

    summary = summarize(transactions)
    summary["date_from"] = date_from
    summary["date_to"] = date_to
    summary["previous_date_from"] = previous_from
    summary["previous_date_to"] = previous_to
    summary["category_filter"] = category_filter
    summary["comparison"] = build_summary_comparison(summary, previous_summary, previous_available)
    summary["category_comparison"] = build_category_comparison(
        summary.get("by_category", {}),
        previous_summary.get("by_category", {}),
        previous_available,
    )
    summary["transactions"] = enrich_transactions_with_debt_info(transactions)
    return summary


def get_monthly_report(year: int | None = None, month: int | None = None, category: str | None = None) -> dict:
    """Laporan bulanan."""
    date_from, date_to = get_month_range(year, month)
    month_label = date_from[:7]
    current_start = datetime.strptime(date_from, "%Y-%m-%d")

    if current_start.month == 1:
        previous_year, previous_month = current_start.year - 1, 12
    else:
        previous_year, previous_month = current_start.year, current_start.month - 1

    previous_from, previous_to = get_month_range(previous_year, previous_month)

    records = get_transaction_records_for_report()
    category_filter = resolve_category_filter(category, records)
    transactions = filter_transactions(records, date_from=date_from, date_to=date_to, category=category_filter)
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    previous_transactions = filter_transactions(
        records,
        date_from=previous_from,
        date_to=previous_to,
        category=category_filter,
    )
    previous_summary = summarize(previous_transactions)
    previous_available = len(previous_transactions) > 0

    summary = summarize(transactions)
    summary["date_from"] = date_from
    summary["date_to"] = date_to
    summary["month"] = month_label
    summary["previous_month"] = previous_from[:7]
    summary["category_filter"] = category_filter
    summary["comparison"] = build_summary_comparison(summary, previous_summary, previous_available)
    summary["category_comparison"] = build_category_comparison(
        summary.get("by_category", {}),
        previous_summary.get("by_category", {}),
        previous_available,
    )
    summary["transactions"] = enrich_transactions_with_debt_info(transactions)
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
