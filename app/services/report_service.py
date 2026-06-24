from datetime import datetime, timedelta
import re

from app.sheets.client import get_all_records
from app.config import SHEET_TRANSACTIONS, SHEET_DEBTS, SHEET_ACCOUNTS


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


def normalize_account_key(value: str | None) -> str:
    """Normalisasi nama rekening untuk matching yang toleran spasi/simbol."""
    raw = str(value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def get_known_report_accounts(records: list[dict] | None = None) -> list[str]:
    """Gabungkan rekening dari sheet accounts dan transaksi."""
    accounts = []
    seen = set()

    def add(value):
        value = str(value or "").strip()
        key = normalize_account_key(value)
        if value and key and key not in seen:
            accounts.append(value)
            seen.add(key)

    try:
        for acc in get_all_records(SHEET_ACCOUNTS):
            add((acc or {}).get("account_name"))
    except Exception:
        pass

    for record in records or []:
        add((record or {}).get("account"))
        add((record or {}).get("to_account"))

    return accounts


def resolve_account_filter(account_query: str | None, records: list[dict] | None = None) -> str | None:
    """Resolve input rekening user ke nama rekening canonical jika memungkinkan."""
    query = str(account_query or "").strip()
    if not query:
        return None

    query_key = normalize_account_key(query)
    if not query_key:
        return None

    accounts = get_known_report_accounts(records)
    account_by_key = {normalize_account_key(acc): acc for acc in accounts}

    if query_key in account_by_key:
        return account_by_key[query_key]

    partial_matches = [
        acc for acc in accounts
        if query_key in normalize_account_key(acc) or normalize_account_key(acc) in query_key
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]

    # Fallback: tetap pakai input user supaya rekening baru/custom tetap bisa difilter.
    return query


def is_account_match(value: str | None, account_key: str | None) -> bool:
    if not account_key:
        return False
    return normalize_account_key(value) == account_key


def is_account_transaction(record: dict, account: str | None) -> bool:
    """Cek apakah transaksi menyentuh rekening tertentu."""
    account_key = normalize_account_key(account)
    if not account_key:
        return True

    txn_type = str((record or {}).get("type", "") or "").strip().lower()
    source_account = (record or {}).get("account")
    target_account = (record or {}).get("to_account")

    if txn_type == "transfer":
        return is_account_match(source_account, account_key) or is_account_match(target_account, account_key)

    return is_account_match(source_account, account_key)


def split_report_filter_args(value: str | None, mode: str) -> tuple[str | None, str | None, str | None]:
    """
    Pisahkan argumen report menjadi periode, kategori, dan rekening.

    Contoh:
    - `/bulanan Food & Beverage` -> (None, "Food & Beverage", None)
    - `/bulanan rekening Cash` -> (None, None, "Cash")
    - `/bulanan 2026-06 rekening Cash` -> ("2026-06", None, "Cash")
    - `/bulanan Food & Beverage rekening Cash` -> (None, "Food & Beverage", "Cash")
    - `/mingguan 2026-06-01 rekening Dana` -> ("2026-06-01", None, "Dana")
    """
    raw = str(value or "").strip()
    if not raw:
        return None, None, None

    tokens = raw.split()
    markers = {"rekening", "akun", "account", "rek"}

    for idx, token in enumerate(tokens):
        token_key = normalize_account_key(token)
        if token_key not in markers:
            continue

        before = " ".join(tokens[:idx]).strip()
        after = " ".join(tokens[idx + 1:]).strip()

        period_arg, category_arg = split_report_period_and_category_arg(before, mode)
        account_period_arg, account_arg = split_report_period_and_category_arg(after, mode)

        if not period_arg and account_period_arg:
            period_arg = account_period_arg

        account_arg = account_arg if account_period_arg else after
        return period_arg, category_arg, (account_arg or None)

    period_arg, category_arg = split_report_period_and_category_arg(raw, mode)
    return period_arg, category_arg, None


def split_account_period_arg(value: str | None) -> tuple[str | None, str]:
    """
    Parse argumen /rekening.

    Return: (account_arg, period_arg) dengan period_arg default `month`.
    Contoh:
    - `Cash` -> ("Cash", "month")
    - `Cash 2026-06` -> ("Cash", "2026-06")
    - `Cash all` -> ("Cash", "all")
    """
    raw = str(value or "").strip()
    if not raw:
        return None, "month"

    tokens = raw.split()
    low_tokens = [normalize_account_key(t) for t in tokens]

    for marker in ["rekening", "akun", "account", "rek"]:
        if low_tokens and low_tokens[0] == marker:
            tokens = tokens[1:]
            low_tokens = low_tokens[1:]
            raw = " ".join(tokens).strip()
            break

    if not raw:
        return None, "month"

    if low_tokens and low_tokens[-1] in {"all", "semua", "histori", "history"}:
        return " ".join(tokens[:-1]).strip() or None, "all"

    period_arg, account_arg = split_report_period_and_category_arg(raw, "month")
    if period_arg:
        return account_arg, period_arg

    return raw, "month"


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
        receivable_by_person = {}
        payable_by_person = {}

        for debt in linked_debts:
            amount = safe_float(debt.get("remaining_amount", 0))
            debt_type = str(debt.get("type", "") or "").strip().lower()
            person = str(debt.get("person_name", "") or "").strip() or "Tanpa nama"
            if person and person not in people:
                people.append(person)

            if debt_type == "receivable":
                receivable_remaining += amount
                receivable_by_person[person] = receivable_by_person.get(person, 0.0) + amount
            elif debt_type == "payable":
                payable_remaining += amount
                payable_by_person[person] = payable_by_person.get(person, 0.0) + amount

        expense_amount = safe_float(item.get("amount", 0))
        item["linked_debts"] = linked_debts
        item["debt_receivable_remaining"] = receivable_remaining
        item["debt_payable_remaining"] = payable_remaining
        item["debt_people"] = people
        item["debt_receivable_parts"] = [
            {"person_name": person, "remaining_amount": amount}
            for person, amount in receivable_by_person.items()
            if amount > 0
        ]
        item["debt_payable_parts"] = [
            {"person_name": person, "remaining_amount": amount}
            for person, amount in payable_by_person.items()
            if amount > 0
        ]
        item["net_expense_after_receivable"] = max(expense_amount - receivable_remaining, 0.0)
        enriched.append(item)

    return enriched


def calculate_net_expense_after_receivable(transactions: list[dict]) -> float:
    """Total pengeluaran bersih: gross expense dikurangi piutang aktif terkait transaksi."""
    total = 0.0
    for txn in transactions or []:
        txn_type = str((txn or {}).get("type", "") or "").strip().lower()
        if txn_type != "expense":
            continue
        amount = safe_float((txn or {}).get("amount", 0))
        receivable = safe_float((txn or {}).get("debt_receivable_remaining", 0))
        total += max(amount - receivable, 0.0)
    return total


def calculate_net_expense_by_category(transactions: list[dict]) -> dict:
    """Breakdown pengeluaran bersih per kategori."""
    result = {}
    for txn in transactions or []:
        txn_type = str((txn or {}).get("type", "") or "").strip().lower()
        if txn_type != "expense":
            continue
        category = str((txn or {}).get("category") or "Other").strip() or "Other"
        amount = safe_float((txn or {}).get("amount", 0))
        receivable = safe_float((txn or {}).get("debt_receivable_remaining", 0))
        result[category] = result.get(category, 0.0) + max(amount - receivable, 0.0)
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


def attach_enriched_transactions(summary: dict, transactions: list[dict]) -> dict:
    """Attach transaksi enriched + total pengeluaran bersih ke summary report."""
    enriched = enrich_transactions_with_debt_info(transactions)
    summary["transactions"] = enriched
    summary["total_net_expense_after_receivable"] = calculate_net_expense_after_receivable(enriched)
    summary["by_category_net"] = calculate_net_expense_by_category(enriched)
    return summary


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

    if raw in ["last week", "minggu lalu", "minggulalu", "pekan lalu", "pekanlalu"]:
        return (today - timedelta(days=7)).strftime("%Y-%m-%d")

    if raw in ["next week", "minggu depan", "minggudepan", "pekan depan", "pekandepan"]:
        return (today + timedelta(days=7)).strftime("%Y-%m-%d")

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

    if raw in ["month", "bulan", "bulanan", "bulanini", "bulan ini", "this month", "current month"]:
        return today.year, today.month

    if raw in ["last month", "bulan lalu", "bulanlalu", "bln lalu", "blnlalu", "month lalu"]:
        first_this_month = datetime(today.year, today.month, 1).date()
        last_month_date = first_this_month - timedelta(days=1)
        return last_month_date.year, last_month_date.month

    if raw in ["next month", "bulan depan", "bulandepan", "bln depan", "blndepan"]:
        if today.month == 12:
            return today.year + 1, 1
        return today.year, today.month + 1

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
    account: str | None = None,
) -> list[dict]:
    """Filter transaksi berdasarkan rentang tanggal, tipe, kategori, dan/atau rekening."""
    result = []
    category_key = normalize_category_key(category) if category else None
    account_filter = str(account or "").strip() or None

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
        if account_filter and not is_account_transaction(r, account_filter):
            continue

        result.append(r)

    return result


def summarize(transactions: list[dict], account: str | None = None) -> dict:
    """
    Hitung total income, expense, transfer, net, dan breakdown per kategori.

    Jika `account` diisi, transfer dihitung dari perspektif rekening tersebut:
    - transfer_in menambah net rekening
    - transfer_out mengurangi net rekening
    """
    account_key = normalize_account_key(account) if account else None
    total_income = 0.0
    total_expense = 0.0
    total_transfer = 0.0
    total_transfer_in = 0.0
    total_transfer_out = 0.0
    by_category = {}

    for t in transactions:
        amount = safe_float(t.get("amount", 0))
        txn_type = str(t.get("type", "")).strip().lower()
        category = str(t.get("category") or "Other").strip() or "Other"
        source_match = is_account_match(t.get("account"), account_key) if account_key else True
        target_match = is_account_match(t.get("to_account"), account_key) if account_key else False

        if txn_type == "income":
            if source_match:
                total_income += amount
        elif txn_type == "expense":
            if source_match:
                total_expense += amount
                by_category[category] = by_category.get(category, 0.0) + amount
        elif txn_type == "transfer":
            if account_key:
                if source_match:
                    total_transfer_out += amount
                if target_match:
                    total_transfer_in += amount
                if source_match or target_match:
                    total_transfer += amount
            else:
                total_transfer += amount

    if account_key:
        net = total_income + total_transfer_in - total_expense - total_transfer_out
    else:
        net = total_income - total_expense

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "total_transfer": total_transfer,
        "total_transfer_in": total_transfer_in,
        "total_transfer_out": total_transfer_out,
        "net": net,
        "by_category": dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True)),
        "count": len(transactions),
    }


# ── Report functions ──────────────────────────────────────────────────────────

def get_daily_report(date_str: str | None = None, category: str | None = None, account: str | None = None) -> dict:
    """Laporan harian untuk tanggal tertentu. Default: hari ini."""
    date_str = parse_report_date_arg(date_str)
    current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    previous_date = current_date - timedelta(days=1)
    previous_date_str = previous_date.strftime("%Y-%m-%d")

    records = get_transaction_records_for_report()
    category_filter = resolve_category_filter(category, records)
    account_filter = resolve_account_filter(account, records)
    transactions = filter_transactions(
        records,
        date_from=date_str,
        date_to=date_str,
        category=category_filter,
        account=account_filter,
    )
    transactions.sort(key=lambda x: int(x.get("_row_index", 0) or 0), reverse=True)

    previous_transactions = filter_transactions(
        records,
        date_from=previous_date_str,
        date_to=previous_date_str,
        category=category_filter,
        account=account_filter,
    )
    previous_summary = summarize(previous_transactions, account_filter)
    previous_available = len(previous_transactions) > 0

    summary = summarize(transactions, account_filter)
    summary["date"] = date_str
    summary["previous_date"] = previous_date_str
    summary["category_filter"] = category_filter
    summary["account_filter"] = account_filter
    summary["comparison"] = build_summary_comparison(summary, previous_summary, previous_available)
    summary["category_comparison"] = build_category_comparison(
        summary.get("by_category", {}),
        previous_summary.get("by_category", {}),
        previous_available,
    )
    attach_enriched_transactions(summary, transactions)
    return summary


def get_weekly_report(reference_date: str | None = None, category: str | None = None, account: str | None = None) -> dict:
    """Laporan mingguan — Senin sampai Minggu dari reference_date."""
    date_from, date_to = get_week_range(reference_date)
    current_start = datetime.strptime(date_from, "%Y-%m-%d").date()
    previous_start = current_start - timedelta(days=7)
    previous_end = current_start - timedelta(days=1)
    previous_from = previous_start.strftime("%Y-%m-%d")
    previous_to = previous_end.strftime("%Y-%m-%d")

    records = get_transaction_records_for_report()
    category_filter = resolve_category_filter(category, records)
    account_filter = resolve_account_filter(account, records)
    transactions = filter_transactions(
        records,
        date_from=date_from,
        date_to=date_to,
        category=category_filter,
        account=account_filter,
    )
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    previous_transactions = filter_transactions(
        records,
        date_from=previous_from,
        date_to=previous_to,
        category=category_filter,
        account=account_filter,
    )
    previous_summary = summarize(previous_transactions, account_filter)
    previous_available = len(previous_transactions) > 0

    summary = summarize(transactions, account_filter)
    summary["date_from"] = date_from
    summary["date_to"] = date_to
    summary["previous_date_from"] = previous_from
    summary["previous_date_to"] = previous_to
    summary["category_filter"] = category_filter
    summary["account_filter"] = account_filter
    summary["comparison"] = build_summary_comparison(summary, previous_summary, previous_available)
    summary["category_comparison"] = build_category_comparison(
        summary.get("by_category", {}),
        previous_summary.get("by_category", {}),
        previous_available,
    )
    attach_enriched_transactions(summary, transactions)
    return summary


def get_monthly_report(year: int | None = None, month: int | None = None, category: str | None = None, account: str | None = None) -> dict:
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
    account_filter = resolve_account_filter(account, records)
    transactions = filter_transactions(
        records,
        date_from=date_from,
        date_to=date_to,
        category=category_filter,
        account=account_filter,
    )
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    previous_transactions = filter_transactions(
        records,
        date_from=previous_from,
        date_to=previous_to,
        category=category_filter,
        account=account_filter,
    )
    previous_summary = summarize(previous_transactions, account_filter)
    previous_available = len(previous_transactions) > 0

    summary = summarize(transactions, account_filter)
    summary["date_from"] = date_from
    summary["date_to"] = date_to
    summary["month"] = month_label
    summary["previous_month"] = previous_from[:7]
    summary["category_filter"] = category_filter
    summary["account_filter"] = account_filter
    summary["comparison"] = build_summary_comparison(summary, previous_summary, previous_available)
    summary["category_comparison"] = build_category_comparison(
        summary.get("by_category", {}),
        previous_summary.get("by_category", {}),
        previous_available,
    )
    attach_enriched_transactions(summary, transactions)
    return summary


def get_account_balance(account_name: str) -> float | None:
    """Ambil saldo rekening dari sheet accounts."""
    account_key = normalize_account_key(account_name)
    if not account_key:
        return None

    try:
        for acc in get_all_records(SHEET_ACCOUNTS):
            if normalize_account_key((acc or {}).get("account_name")) == account_key:
                return safe_float((acc or {}).get("balance", 0))
    except Exception:
        pass

    return None


def get_account_monthly_report(account: str, month_arg: str | None = None) -> dict:
    """Ringkasan rekening untuk bulan tertentu."""
    year, month_num = parse_report_month_arg(month_arg)
    report = get_monthly_report(year, month_num, account=account)
    account_filter = report.get("account_filter") or account
    report["period_label"] = report.get("month", "-")
    report["period_type"] = "month"
    report["account_balance"] = get_account_balance(account_filter)
    return report


def get_account_all_report(account: str) -> dict:
    """Ringkasan rekening untuk seluruh histori transaksi."""
    records = get_transaction_records_for_report()
    account_filter = resolve_account_filter(account, records)
    transactions = filter_transactions(records, account=account_filter)
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    summary = summarize(transactions, account_filter)
    summary["period_label"] = "Semua histori"
    summary["period_type"] = "all"
    summary["account_filter"] = account_filter
    summary["category_filter"] = None
    summary["comparison"] = {}
    summary["category_comparison"] = {}
    attach_enriched_transactions(summary, transactions)
    summary["account_balance"] = get_account_balance(account_filter)
    return summary


def get_account_report(account: str, period_arg: str | None = "month") -> dict:
    """Dispatcher ringkasan rekening untuk /rekening."""
    normalized_period = str(period_arg or "month").strip().lower()
    if normalized_period in {"all", "semua", "histori", "history"}:
        return get_account_all_report(account)
    return get_account_monthly_report(account, None if normalized_period == "month" else period_arg)


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
    return enrich_transactions_with_debt_info(results[:limit])


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
