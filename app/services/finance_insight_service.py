"""Context builder service for AI finance insight, audit, coach, and ask commands."""

# Import __future__ so this module can use its helpers.
from __future__ import annotations

from functools import partial

from app.formatting import format_rupiah as _format_rupiah


format_rupiah = partial(_format_rupiah, preserve_decimals=False)

# Import re for this module's local operations.
import re
# Import collections so this module can use its helpers.
from collections import Counter, defaultdict
# Import datetime so this module can use its helpers.
from datetime import datetime, timedelta
from app.clock import business_now
# Import statistics so this module can use its helpers.
from statistics import mean, median

# Import app.config so this module can use its helpers.
from app.config import (
    AI_CONTEXT_RECORD_LIMIT,
    SHEET_ACCOUNTS,
    SHEET_ASSETS,
    SHEET_BUDGETS,
    SHEET_CATEGORIES,
    SHEET_DEBTS,
    SHEET_TRANSACTIONS,
)
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import get_all_records
# Import app.services.report_service so this module can use its helpers.
from app.services.report_service import enrich_transactions_with_debt_info

DEBT_CASHFLOW_CATEGORIES = {
    "Piutang Diberikan",
    "Pembayaran Piutang",
    "Penerimaan Utang",
    "Bayar Utang",
}

FINANCE_QUESTION_KEYWORDS = [
    "insight", "analisis", "ringkasan", "laporan", "narasi",
    "boros", "hemat", "pengeluaran", "pemasukan", "income", "expense",
    "budget", "anggaran", "sisa budget", "jebol", "aman gak", "aman nggak",
    "anomali", "aneh", "tidak biasa", "audit", "data quality", "duplikat",
    "transaksi terbesar", "terakhir", "kapan", "berapa total", "total", "cari transaksi",
    "saran", "coach", "rekomendasi", "nabung", "tabung", "kurangi",
    "pending", "rencana", "pengeluaran akan datang",
    "saldo", "utang", "hutang", "piutang", "net worth", "aset",
]

AVAILABLE_COMMANDS_FOR_AI = [
    "/saldo",
    "/rekening",
    "/harian",
    "/mingguan",
    "/bulanan",
    "/grafik",
    "/cari",
    "/last",
    "/transaksi",
    "/edit_txn",
    "/delete_txn",
    "/kategori",
    "/add_kategori",
    "/edit_kategori",
    "/budget",
    "/pending",
    "/hutang",
    "/debt_edit",
    "/debt_void",
    "/insight",
    "/ask",
    "/audit",
    "/coach",
    "/privacy",
]

STOPWORDS = {
    "aku", "saya", "gue", "gua", "gw", "bulan", "ini", "itu", "di", "ke", "dari", "yang",
    "dan", "atau", "untuk", "berapa", "total", "transaksi", "pengeluaran", "pemasukan",
    "makan", "budget", "aman", "gak", "nggak", "ga", "dong", "ya", "apa", "aja",
    "kapan", "terakhir", "cari", "lihat", "cek", "tolong", "kasih", "saran", "saya",
    "hari", "minggu", "tahun", "periode", "saldo", "rekening", "kenapa", "turun", "naik",
    "bulanini", "hariini", "mingguini",
}

CATEGORY_HINTS = {
    "makan": "Food & Beverage",
    "jajan": "Food & Beverage",
    "kopi": "Food & Beverage",
    "minum": "Food & Beverage",
    "food": "Food & Beverage",
    "transport": "Transport",
    "ojol": "Transport",
    "gojek": "Transport",
    "grab": "Transport",
    "bensin": "Transport",
    "listrik": "Bills & Utilities",
    "token": "Bills & Utilities",
    "internet": "Bills & Utilities",
    "wifi": "Bills & Utilities",
    "belanja": "Shopping",
    "shopping": "Shopping",
    "skincare": "Personal Care",
    "obat": "Health",
    "dokter": "Health",
}


# Helper for safe float.
def safe_float(value, default: float = 0.0) -> float:
    """Coordinate the safe float logic in the service layer.

    Args:
        value: Raw value supplied by the caller.
        default: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    if value is None or value == "":
        return default

    if isinstance(value, (int, float)):
        return float(value)

    # Prepare raw from the incoming input.
    raw = str(value).strip()
    # Validate missing raw before continuing.
    if not raw:
        return default

    raw = raw.replace("Rp", "").replace("rp", "").replace("IDR", "").replace("idr", "")
    raw = raw.replace(" ", "")

    if "," in raw and "." in raw:
        # Format Indonesia: 427.500,5
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        parts = raw.split(",")
        # 427500,5 atau 427500,50 = desimal; 427,500 = ribuan.
        if len(parts) == 2 and len(parts[-1]) in {1, 2}:
            raw = raw.replace(",", ".")
        # Use the fallback path when no earlier branch matched.
        else:
            raw = raw.replace(",", "")
    elif "." in raw:
        parts = raw.split(".")
        # 427.500 atau 1.427.500 = ribuan.
        if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
            raw = raw.replace(".", "")

    raw = re.sub(r"[^0-9.-]", "", raw)

    # Run this operation in a guarded block so failures can be handled.
    try:
        return float(raw)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return default


# Helper for current month.
def current_month() -> str:
    """Coordinate the current month logic in the service layer.

    Args:
        None.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return business_now().strftime("%Y-%m")


# Helper for normalize month arg.
def normalize_month_arg(value: str | None = None) -> str:
    """Normalize input values for the normalize month arg workflow in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    today = business_now()
    # Validate missing value before continuing.
    if not value:
        return current_month()

    raw = str(value).strip().lower().replace("/", "-")
    raw = re.sub(r"\s+", " ", raw)

    if raw in {"bulan ini", "bulanini", "month", "current", "sekarang"}:
        return current_month()

    m = re.search(r"(20\d{2})[-\s](0?[1-9]|1[0-2])", raw)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"

    m = re.fullmatch(r"(0?[1-9]|1[0-2])", raw)
    if m:
        return f"{today.year}-{int(m.group(1)):02d}"

    return current_month()


# Helper for previous month.
def previous_month(month: str) -> str:
    """Coordinate the previous month logic in the service layer.

    Args:
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    year, month_num = map(int, month.split("-"))
    if month_num == 1:
        return f"{year - 1}-12"
    return f"{year}-{month_num - 1:02d}"


# Helper for month bounds.
def month_bounds(month: str) -> tuple[str, str]:
    """Coordinate the month bounds logic in the service layer.

    Args:
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `tuple[str, str]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    year, month_num = map(int, month.split("-"))
    first = datetime(year, month_num, 1)
    if month_num == 12:
        next_first = datetime(year + 1, 1, 1)
    # Use the fallback path when no earlier branch matched.
    else:
        next_first = datetime(year, month_num + 1, 1)
    last = next_first - timedelta(days=1)
    return first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d")


# Helper for parse period from text.
def parse_period_from_text(text: str) -> dict:
    """Parse caller input for the parse period from text workflow in the service layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    raw = str(text or "").lower()
    today = business_now().date()

    m = re.search(r"(20\d{2})[-/](0?[1-9]|1[0-2])", raw)
    if m:
        month = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
        start, end = month_bounds(month)
        return {"type": "month", "month": month, "date_from": start, "date_to": end, "label": month}

    m = re.search(r"\b(0?[1-9]|1[0-2])[-/](20\d{2})\b", raw)
    if m:
        month = f"{int(m.group(2)):04d}-{int(m.group(1)):02d}"
        start, end = month_bounds(month)
        return {"type": "month", "month": month, "date_from": start, "date_to": end, "label": month}

    if any(k in raw for k in ["hari ini", "hariini", "today"]):
        d = today.strftime("%Y-%m-%d")
        return {"type": "day", "month": d[:7], "date_from": d, "date_to": d, "label": d}

    if any(k in raw for k in ["kemarin", "yesterday"]):
        d = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        return {"type": "day", "month": d[:7], "date_from": d, "date_to": d, "label": d}

    if any(k in raw for k in ["minggu ini", "mingguini", "week"]):
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        return {
            "type": "week",
            "month": today.strftime("%Y-%m"),
            "date_from": monday.strftime("%Y-%m-%d"),
            "date_to": sunday.strftime("%Y-%m-%d"),
            "label": f"{monday} s/d {sunday}",
        }

    if any(k in raw for k in ["bulan lalu", "last month"]):
        month = previous_month(current_month())
        start, end = month_bounds(month)
        return {"type": "month", "month": month, "date_from": start, "date_to": end, "label": month}

    month = current_month()
    start, end = month_bounds(month)
    return {"type": "month", "month": month, "date_from": start, "date_to": end, "label": month}


# Helper for normalize text.
def normalize_text(value: str) -> str:
    """Normalize input values for the normalize text workflow in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()




# Helper for normalize sheet date value.
def normalize_sheet_date_value(value) -> str:
    """Normalize Google Sheets date values before filtering or auditing."""
    if value is None:
        return ""
    # Prepare raw from the incoming input.
    raw = str(value).strip()
    if not raw or raw.lower() in {"-", "none", "nan"}:
        return ""

    match = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", raw)
    if match:
        # Run this operation in a guarded block so failures can be handled.
        try:
            return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
        # Handle an expected failure from the guarded operation above.
        except Exception:
            return match.group(0).replace("/", "-")

    if re.fullmatch(r"\d+(?:\.0+)?", raw):
        # Run this operation in a guarded block so failures can be handled.
        try:
            serial = int(float(raw))
            if 20000 <= serial <= 80000:
                dt = datetime(1899, 12, 30) + timedelta(days=serial)
                return dt.strftime("%Y-%m-%d")
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass

    return raw


# Helper for is valid id text.
def is_valid_id_text(value: str, prefixes: tuple[str, ...]) -> bool:
    """Check whether an ID field still looks like bot-generated plain text."""
    raw = str(value or "").strip()
    return bool(raw) and raw.startswith(prefixes) and "e+" not in raw.lower()


# Helper for get existing category names.
def get_existing_category_names() -> set[str]:
    """Read category names from sheet categories for audit checks."""
    names = set()
    # Iterate through each row.
    for row in get_all_records(SHEET_CATEGORIES):
        name = str(row.get("category_name") or row.get("name") or "").strip()
        if name:
            # Append the current value to names.
            names.add(name)
    return names


# Helper for get existing account names.
def get_existing_account_names() -> set[str]:
    """Read account names from sheet accounts for audit checks."""
    names = set()
    # Iterate through each row.
    for row in get_all_records(SHEET_ACCOUNTS):
        name = str(row.get("account_name") or row.get("name") or "").strip()
        if name:
            # Append the current value to names.
            names.add(name)
    return names

# Helper for is date between.
def is_date_between(date_value: str, date_from: str | None, date_to: str | None) -> bool:
    """Check whether a condition is true for date between."""
    # Extract date value for validation.
    date_value = normalize_sheet_date_value(date_value)
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", date_value):
        return False
    # Handle date from and date value < date from.
    if date_from and date_value < date_from:
        return False
    # Handle date to and date value > date to.
    if date_to and date_value > date_to:
        return False
    return True


# Helper for filter records by period.
def filter_records_by_period(records: list[dict], date_from: str | None, date_to: str | None) -> list[dict]:
    """Coordinate the filter records by period logic in the service layer.

    Args:
        records: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        date_from: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        date_to: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return [r for r in records if is_date_between(r.get("date", ""), date_from, date_to)]


# Helper for get month transactions.
def get_month_transactions(month: str) -> list[dict]:
    """Retrieve data needed by the get month transactions workflow in the service layer.

    Args:
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    date_from, date_to = month_bounds(month)
    # Load records for the current calculation.
    records = get_all_records(SHEET_TRANSACTIONS)
    return filter_records_by_period(records, date_from, date_to)


# Helper for enrich finance transactions.
def enrich_finance_transactions(records: list[dict]) -> list[dict]:
    """Coordinate the enrich finance transactions logic in the service layer.

    Args:
        records: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Load records for the current calculation.
    records = records or []
    if any(
        str((r or {}).get("type", "")).strip().lower() == "expense"
        and "net_expense_after_receivable" in (r or {})
        # Iterate through each r.
        for r in records
    ):
        return records
    return enrich_transactions_with_debt_info(records)


# Helper for get effective expense amount.
def get_effective_expense_amount(record: dict) -> float:
    """Retrieve data needed by the get effective expense amount workflow in the service layer.

    Args:
        record: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    amount = safe_float((record or {}).get("amount"))
    if str((record or {}).get("type", "")).strip().lower() != "expense":
        return amount

    if "net_expense_after_receivable" in (record or {}):
        return max(safe_float((record or {}).get("net_expense_after_receivable")), 0.0)

    receivable = safe_float(
        (record or {}).get("debt_receivable_original", (record or {}).get("debt_receivable_remaining", 0))
    )
    return max(amount - receivable, 0.0)


# Helper for summarize transactions.
def summarize_transactions(records: list[dict]) -> dict:
    """Coordinate the summarize transactions logic in the service layer.

    Args:
        records: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    total_income = 0.0
    total_expense = 0.0  # Net expense after split bill receivables.
    total_transfer = 0.0
    # Extract expense by category for validation.
    expense_by_category = defaultdict(float)
    # Extract income by category for validation.
    income_by_category = defaultdict(float)
    # Extract expense by account for validation.
    expense_by_account = defaultdict(float)
    # Extract income by account for validation.
    income_by_account = defaultdict(float)
    # Extract cash out by account for validation.
    cash_out_by_account = defaultdict(float)
    # Extract cash in by account for validation.
    cash_in_by_account = defaultdict(float)

    # Load records for the current calculation.
    records = enrich_finance_transactions(records)

    # Iterate through each r.
    for r in records:
        txn_type = str(r.get("type", "")).strip().lower()
        amount = safe_float(r.get("amount"))
        # Extract effective amount for validation.
        effective_amount = get_effective_expense_amount(r)
        category = str(r.get("category") or "Uncategorized").strip() or "Uncategorized"
        account = str(r.get("account") or "-").strip() or "-"
        to_account = str(r.get("to_account") or "").strip()

        if txn_type == "income":
            total_income += amount
            income_by_category[category] += amount
            income_by_account[account] += amount
            cash_in_by_account[account] += amount
        elif txn_type == "expense":
            total_expense += effective_amount
            expense_by_category[category] += effective_amount
            expense_by_account[account] += effective_amount
            cash_out_by_account[account] += effective_amount
        elif txn_type == "transfer":
            total_transfer += amount
            cash_out_by_account[account] += amount
            if to_account:
                cash_in_by_account[to_account] += amount

    # Helper for sorted items.
    def sorted_items(d: dict) -> list[dict]:
        """Coordinate the sorted items logic in the service layer.

        Args:
            d: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `list[dict]` value as defined by the function signature.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
        """
        return [
            {"name": k, "amount": v, "amount_display": format_rupiah(v)}
            # Iterate through each k, v.
            for k, v in sorted(d.items(), key=lambda x: x[1], reverse=True)
            if abs(v) > 0.0001
        ]

    return {
        "count": len(records),
        "amount_basis": "expense_amount_is_net_after_receivable",
        "total_income": total_income,
        "total_income_display": format_rupiah(total_income),
        "total_expense": total_expense,
        "total_expense_display": format_rupiah(total_expense),
        "total_transfer": total_transfer,
        "total_transfer_display": format_rupiah(total_transfer),
        "net": total_income - total_expense,
        "net_display": format_rupiah(total_income - total_expense),
        "expense_by_category": sorted_items(expense_by_category),
        "income_by_category": sorted_items(income_by_category),
        "expense_by_account": sorted_items(expense_by_account),
        "income_by_account": sorted_items(income_by_account),
        "cash_out_by_account": sorted_items(cash_out_by_account),
        "cash_in_by_account": sorted_items(cash_in_by_account),
    }


# Helper for add contribution.
def add_contribution(items: list[dict], total: float, limit: int = 8) -> list[dict]:
    """Coordinate the add contribution logic in the service layer.

    Args:
        items: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        total: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        limit: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Build result for the response flow.
    result = []
    # Iterate through each item.
    for item in items[:limit]:
        amount = float(item.get("amount", 0) or 0)
        result.append({
            **item,
            "contribution_pct": round((amount / total * 100), 1) if total else 0,
        })
    return result


# Helper for compact transaction.
def compact_transaction(r: dict) -> dict:
    """Coordinate the compact transaction logic in the service layer.

    Args:
        r: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Extract amount for validation.
    amount = get_effective_expense_amount(r)
    item = {
        "date": normalize_sheet_date_value(r.get("date", "")),
        "type": r.get("type", ""),
        "amount": amount,
        "amount_display": format_rupiah(amount),
        "category": r.get("category", ""),
        "account": r.get("account", ""),
        "to_account": r.get("to_account", ""),
        "subject": r.get("subject", ""),
        "description": r.get("description", ""),
        "catatan": r.get("catatan", ""),
        "id": r.get("id", ""),
    }
    if str(r.get("type", "")).strip().lower() == "expense":
        item["amount_basis"] = "net_after_receivable"
    return item


def get_top_transactions(records: list[dict], txn_type: str | None = "expense", limit: int = 8) -> list[dict]:
    """Retrieve data needed by the get top transactions workflow in the service layer.

    Args:
        records: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        txn_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        limit: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Load records for the current calculation.
    records = enrich_finance_transactions(records)
    # Extract candidates for validation.
    candidates = []
    # Iterate through each r.
    for r in records:
        if txn_type and str(r.get("type", "")).strip().lower() != txn_type:
            # Skip the rest of this loop iteration after handling this case.
            continue
        amount = get_effective_expense_amount(r) if str(r.get("type", "")).strip().lower() == "expense" else safe_float(r.get("amount"))
        if amount <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Append the current value to candidates.
        candidates.append(r)
    candidates.sort(
        key=lambda x: get_effective_expense_amount(x) if str(x.get("type", "")).strip().lower() == "expense" else safe_float(x.get("amount")),
        reverse=True,
    )
    return [compact_transaction(r) for r in candidates[:limit]]


# Helper for get budget status.
def get_budget_status(month: str, transactions: list[dict]) -> list[dict]:
    """Retrieve data needed by the get budget status workflow in the service layer.

    Args:
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        transactions: List of transaction dicts or transaction-like rows.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    budgets = [
        b for b in get_all_records(SHEET_BUDGETS)
        if str(b.get("month", "")).strip() == month
    ]
    # Validate missing budgets before continuing.
    if not budgets:
        return []

    # Extract expense by category for validation.
    expense_by_category = defaultdict(float)
    # Iterate through each r.
    for r in enrich_finance_transactions(transactions):
        if str(r.get("type", "")).strip().lower() != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue
        category = str(r.get("category") or "Uncategorized").strip()
        expense_by_category[category.lower()] += get_effective_expense_amount(r)

    # Build result for the response flow.
    result = []
    # Iterate through each b.
    for b in budgets:
        category = str(b.get("category") or "").strip()
        budget_amount = safe_float(b.get("budget_amount"))
        actual = expense_by_category.get(category.lower(), 0.0)
        remaining = budget_amount - actual
        pct = (actual / budget_amount * 100) if budget_amount else 0
        result.append({
            "category": category,
            "budget": budget_amount,
            "budget_display": format_rupiah(budget_amount),
            "actual": actual,
            "actual_display": format_rupiah(actual),
            "remaining": remaining,
            "remaining_display": format_rupiah(remaining),
            "usage_pct": round(pct, 1),
            "status": "over" if remaining < 0 else "warning" if pct >= 80 else "ok",
        })

    result.sort(key=lambda x: x["usage_pct"], reverse=True)
    return result


# Helper for get accounts summary.
def get_accounts_summary() -> dict:
    """Retrieve data needed by the get accounts summary workflow in the service layer.

    Args:
        None.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Extract accounts for validation.
    accounts = []
    total = 0.0
    # Iterate through each acc.
    for acc in get_all_records(SHEET_ACCOUNTS):
        balance = safe_float(acc.get("balance"))
        total += balance
        accounts.append({
            "name": acc.get("account_name") or acc.get("name") or "-",
            "balance": balance,
            "balance_display": format_rupiah(balance),
            "type": acc.get("type", ""),
        })
    accounts.sort(key=lambda x: x["balance"], reverse=True)
    return {"total": total, "total_display": format_rupiah(total), "accounts": accounts}


# Helper for get debt summary compact.
def get_debt_summary_compact() -> dict:
    """Retrieve data needed by the get debt summary compact workflow in the service layer.

    Args:
        None.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Load debts for the current calculation.
    debts = get_all_records(SHEET_DEBTS)
    active = []
    totals = defaultdict(float)
    # Iterate through each d.
    for d in debts:
        status = str(d.get("status") or d.get("is_active") or "").strip().lower()
        remaining = safe_float(d.get("remaining_amount") or d.get("amount"))
        if remaining <= 0 or status in {"settled", "closed", "void", "false"}:
            # Skip the rest of this loop iteration after handling this case.
            continue
        debt_type = str(d.get("type") or d.get("debt_type") or "").strip().lower()
        # Validate missing debt type before continuing.
        if not debt_type:
            # Legacy compatibility note for older records or older in-memory state.
            text = normalize_text(" ".join(str(d.get(k, "")) for k in ["category", "description", "catatan"]))
            debt_type = "receivable" if "piutang" in text else "payable" if "utang" in text or "hutang" in text else "unknown"
        totals[debt_type] += remaining
        active.append({
            "person": d.get("person") or d.get("person_name") or d.get("subject") or "-",
            "type": debt_type,
            "remaining_amount": remaining,
            "remaining_amount_display": format_rupiah(remaining),
            "description": d.get("description", ""),
            "id": d.get("id", ""),
        })
    active.sort(key=lambda x: x["remaining_amount"], reverse=True)
    return {
        "total_payable": totals.get("payable", 0.0),
        "total_payable_display": format_rupiah(totals.get("payable", 0.0)),
        "total_receivable": totals.get("receivable", 0.0),
        "total_receivable_display": format_rupiah(totals.get("receivable", 0.0)),
        "active_count": len(active),
        "top_active": active[:8],
    }


# Helper for get net worth compact.
def get_net_worth_compact() -> dict:
    """Retrieve data needed by the get net worth compact workflow in the service layer.

    Args:
        None.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    assets = get_all_records(SHEET_ASSETS)
    active_assets = []

    total_assets = 0.0

    # Iterate through each a.
    for a in assets:
        is_active = str(a.get("is_active", "TRUE")).strip().upper() != "FALSE"
        # Validate missing is active before continuing.
        if not is_active:
            # Skip the rest of this loop iteration after handling this case.
            continue
        value = safe_float(a.get("current_value"))
        total_assets += value
        active_assets.append({
            "name": a.get("name", "-"),
            "value": value,
            "value_display": format_rupiah(value),
            "category": a.get("category", ""),
            "quantity": a.get("quantity", ""),
            "unit": a.get("unit", ""),
            "price_per_unit": safe_float(a.get("price_per_unit")),
            "price_per_unit_display": format_rupiah(safe_float(a.get("price_per_unit"))),
        })

    # Extract accounts for validation.
    accounts = get_accounts_summary()
    debts = get_debt_summary_compact()
    total_liabilities = float(debts.get("total_payable") or 0)
    net_worth = accounts["total"] + total_assets - total_liabilities
    return {
        "total_accounts": accounts["total"],
        "total_accounts_display": format_rupiah(accounts["total"]),
        "total_assets": total_assets,
        "total_assets_display": format_rupiah(total_assets),
        "total_liabilities": total_liabilities,
        "total_liabilities_display": format_rupiah(total_liabilities),
        "net_worth": net_worth,
        "net_worth_display": format_rupiah(net_worth),
        "top_assets": sorted(active_assets, key=lambda x: x["value"], reverse=True)[:8],
        "top_liabilities": [
            debt for debt in debts.get("top_active", []) if debt.get("type") == "payable"
        ],
        "note": "Liability net worth berasal dari debt payable aktif yang dikelola melalui /hutang.",
    }


# Helper for detect anomalies.
def detect_anomalies(records: list[dict], month_summary: dict | None = None) -> list[dict]:
    """Coordinate the detect anomalies logic in the service layer.

    Args:
        records: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        month_summary: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Load records for the current calculation.
    records = enrich_finance_transactions(records)
    expenses = [r for r in records if str(r.get("type", "")).strip().lower() == "expense"]
    # Extract amounts for validation.
    amounts = [get_effective_expense_amount(r) for r in expenses if get_effective_expense_amount(r) > 0]
    anomalies = []

    if amounts:
        med = median(amounts)
        avg = mean(amounts)
        threshold = max(200_000, med * 3, avg * 2)
        # Iterate through each r.
        for r in expenses:
            # Extract amount for validation.
            amount = get_effective_expense_amount(r)
            if amount >= threshold:
                anomalies.append({
                    "type": "large_expense",
                    "severity": "warning",
                    "message": "Nominal pengeluaran net jauh lebih besar dari transaksi biasa.",
                    "transaction": compact_transaction(r),
                    "threshold": threshold,
                    "threshold_display": format_rupiah(threshold),
                    "amount_basis": "net_after_receivable",
                })

    # Potential duplicates: same date + amount + normalized description.
    bucket = defaultdict(list)
    # Iterate through each r.
    for r in records:
        key = (
            normalize_sheet_date_value(r.get("date", "")),
            str(r.get("type", "")),
            int(get_effective_expense_amount(r) if str(r.get("type", "")).strip().lower() == "expense" else safe_float(r.get("amount"))),
            normalize_text(str(r.get("description", "")))[:40],
        )
        if key[2] > 0 and key[3]:
            bucket[key].append(r)
    # Iterate through each items.
    for items in bucket.values():
        if len(items) > 1:
            anomalies.append({
                "type": "possible_duplicate",
                "severity": "warning",
                "message": "Ada transaksi yang tanggal, nominal, dan deskripsinya mirip.",
                "transactions": [compact_transaction(x) for x in items[:5]],
            })

    # Category spikes vs share.
    if month_summary:
        total_expense = month_summary.get("total_expense", 0) or 0
        for item in month_summary.get("expense_by_category", [])[:5]:
            amount = item.get("amount", 0)
            pct = (amount / total_expense * 100) if total_expense else 0
            if total_expense and pct >= 45:
                anomalies.append({
                    "type": "category_concentration",
                    "severity": "info",
                    "message": f"Kategori {item.get('name')} menyumbang {pct:.1f}% dari pengeluaran.",
                    "category": item.get("name"),
                    "amount": amount,
                    "amount_display": format_rupiah(amount),
                    "contribution_pct": round(pct, 1),
                })

    return anomalies[:12]


# Helper for detect data quality issues.
def detect_data_quality_issues(records: list[dict]) -> list[dict]:
    """Detect transaction data quality issues against sheet accounts/categories."""
    issues = []
    counters = Counter()
    examples = defaultdict(list)

    # Extract category names for validation.
    category_names = get_existing_category_names()
    # Extract category lookup for validation.
    category_lookup = {normalize_text(name): name for name in category_names}
    # Extract account names for validation.
    account_names = get_existing_account_names()
    # Extract account lookup for validation.
    account_lookup = {normalize_text(name): name for name in account_names}

    # Helper for find similar name.
    def find_similar_name(name: str, lookup: dict[str, str]) -> str | None:
        """Resolve a loose name against normalized sheet names.

        Args:
            name: Raw category or account text from a transaction record.
            lookup: Mapping of normalized names to canonical sheet names.

        Returns:
            Canonical name when the raw value matches exactly or by containment;
            otherwise `None`.

        Flow constraints:
            This helper is read-only and only supports data quality reporting.
            It must not create new categories/accounts or mutate records.
        """
        # Normalize clean before matching.
        clean = normalize_text(name)
        # Validate missing clean before continuing.
        if not clean:
            return None
        if clean in lookup:
            return lookup[clean]
        # Iterate through each key, original.
        for key, original in lookup.items():
            # Accept partial matches between the user text and lookup keys.
            if clean in key or key in clean:
                return original
        return None

    # Iterate through each r.
    for r in records:
        txn_type = str(r.get("type", "")).strip().lower()
        amount = safe_float(r.get("amount"))
        raw_date = str(r.get("date", "")).strip()
        # Normalize normalized date before matching.
        normalized_date = normalize_sheet_date_value(raw_date)
        account = str(r.get("account") or "").strip()
        to_account = str(r.get("to_account") or "").strip()
        category = str(r.get("category") or "").strip()
        txn_id = str(r.get("id") or "").strip()
        raw_input = str(r.get("raw_input") or "").strip()
        subject = str(r.get("subject") or "").strip()
        description = str(r.get("description") or "").strip()

        # Helper for add issue.
        def add_issue(key: str, extra: dict | None = None):
            """Coordinate the add issue logic in the service layer.

            Args:
                key: Input value supplied by the caller; accepted shape follows the function signature and local validation.
                extra: Input value supplied by the caller; accepted shape follows the function signature and local validation.

            Returns:
                `None` after completing the operation.

            Side effects:
                None beyond the side effects already performed by the existing implementation.

            Flow constraints:
                Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
            """
            counters[key] += 1
            if len(examples[key]) < 5:
                example = compact_transaction({**r, "date": normalized_date})
                if extra:
                    # Append the current value to example.
                    example.update(extra)
                examples[key].append(example)

        if txn_type not in {"expense", "income", "transfer", "debt_offset", "debt_only"}:
            add_issue("type tidak valid/kosong")
        if amount <= 0:
            add_issue("amount kosong/0")
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", normalized_date):
            add_issue("tanggal invalid/kosong")
        # Fall back when raw date != normalized date.
        elif raw_date != normalized_date:
            add_issue("tanggal tersimpan sebagai serial/format non-standar", {"normalized_date": normalized_date, "raw_date": raw_date})

        if txn_id and not is_valid_id_text(txn_id, ("txn_",)):
            add_issue("transaction_id berubah format")
        if re.fullmatch(r"\d+(?:\.0+)?", raw_input):
            add_issue("raw_input terlihat berubah jadi angka")
        if subject and re.fullmatch(r"\d+(?:\.0+)?", subject):
            add_issue("subject terlihat berubah jadi angka")
        if description and re.fullmatch(r"\d+(?:\.0+)?", description):
            add_issue("description terlihat berubah jadi angka")

        if txn_type in {"expense", "income", "transfer"} and not account:
            add_issue("account kosong")
        # Fall back when account and normalize text(account) not in account lookup.
        elif account and normalize_text(account) not in account_lookup:
            if str(account).lower() not in {"sudah berlalu", "tanpa rekening", "debt only", "debt offset"}:
                similar = find_similar_name(account, account_lookup)
                issue_name = "account mirip tapi tidak persis dengan sheet accounts" if similar else "account tidak ada di sheet accounts"
                add_issue(issue_name, {"account_input": account, "suggestion": similar or ""})

        if txn_type == "transfer":
            # Validate missing to account before continuing.
            if not to_account:
                add_issue("transfer tanpa to_account")
            # Fall back when normalize text(to account) not in account lookup.
            elif normalize_text(to_account) not in account_lookup:
                similar = find_similar_name(to_account, account_lookup)
                issue_name = "to_account mirip tapi tidak persis dengan sheet accounts" if similar else "to_account tidak ada di sheet accounts"
                add_issue(issue_name, {"to_account_input": to_account, "suggestion": similar or ""})

        if txn_type in {"expense", "income"} and to_account:
            add_issue("income/expense punya to_account")

        if txn_type == "expense" and not category:
            add_issue("expense tanpa category")
        elif txn_type == "expense":
            # Extract category key for validation.
            category_key = normalize_text(category)
            if category_key not in category_lookup:
                similar = find_similar_name(category, category_lookup)
                issue_name = "kategori mirip tapi tidak persis dengan sheet categories" if similar else "kategori tidak ada di sheet categories"
                add_issue(issue_name, {"category_input": category, "suggestion": similar or ""})
            if category == "Other Expense":
                add_issue("expense masih Other Expense")
            if category == "Utang Tanpa Cashflow":
                add_issue("expense kategori Utang Tanpa Cashflow")

    # Iterate through each key, count.
    for key, count in counters.most_common():
        issues.append({"issue": key, "count": count, "examples": examples[key]})

    return issues

# Helper for compare summaries.
def compare_summaries(current: dict, previous: dict) -> dict:
    """Coordinate the compare summaries logic in the service layer.

    Args:
        current: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        previous: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Helper for diff.
    def diff(key: str) -> dict:
        """Coordinate the diff logic in the service layer.

        Args:
            key: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `dict` value as defined by the function signature.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
        """
        cur = float(current.get(key, 0) or 0)
        prev = float(previous.get(key, 0) or 0)
        delta = cur - prev
        pct = (delta / prev * 100) if prev else None
        return {
            "current": cur,
            "current_display": format_rupiah(cur),
            "previous": prev,
            "previous_display": format_rupiah(prev),
            "delta": delta,
            "delta_display": format_rupiah(delta),
            "delta_pct": round(pct, 1) if pct is not None else None,
        }

    return {
        "income": diff("total_income"),
        "expense": diff("total_expense"),
        "net": diff("net"),
    }


# Helper for build monthly finance context.
def build_monthly_finance_context(month: str | None = None) -> dict:
    """Build the data structure or message text for monthly finance context."""
    month = normalize_month_arg(month)
    prev_month = previous_month(month)

    # Load records for the current calculation.
    records = get_month_transactions(month)
    # Load prev records for the current calculation.
    prev_records = get_month_transactions(prev_month)
    # Build summary for the response flow.
    summary = summarize_transactions(records)
    # Build prev summary for the response flow.
    prev_summary = summarize_transactions(prev_records)

    summary["expense_by_category"] = add_contribution(
        summary["expense_by_category"],
        summary["total_expense"],
        limit=10,
    )
    summary["income_by_category"] = add_contribution(
        summary["income_by_category"],
        summary["total_income"],
        limit=8,
    )

    considered = len(records) + len(prev_records)
    return {
        "period": {"type": "month", "month": month, "previous_month": prev_month},
        "summary": summary,
        "comparison_vs_previous_month": compare_summaries(summary, prev_summary),
        "budget_status": get_budget_status(month, records),
        "top_expenses": get_top_transactions(records, "expense", 10),
        "top_income": get_top_transactions(records, "income", 6),
        "anomalies": detect_anomalies(records, summary),
        "data_quality_issues": detect_data_quality_issues(records),
        "accounts": get_accounts_summary(),
        "debts": get_debt_summary_compact(),
        "net_worth": get_net_worth_compact(),
        "available_commands": AVAILABLE_COMMANDS_FOR_AI,
        "context_metadata": {
            "records_considered": considered,
            "records_selected": min(considered, AI_CONTEXT_RECORD_LIMIT),
            "context_truncated": considered > AI_CONTEXT_RECORD_LIMIT,
            "date_range": {"month": month, "previous_month": prev_month},
            "aggregation_level": "monthly_aggregates_with_ranked_examples",
        },
    }


# Helper for extract keywords.
def extract_keywords(question: str) -> list[str]:
    """Extract the required part of input for keywords."""
    # Normalize clean before matching.
    clean = normalize_text(question)
    # Keep meaningful multi-token known phrases.
    keywords = []
    for phrase in ["food beverage", "other expense", "kopi kenangan", "nasi padang", "ptpt"]:
        if phrase in clean:
            # Append the current value to keywords.
            keywords.append(phrase)
    # Iterate through each token.
    for token in clean.split():
        if len(token) < 3:
            # Skip the rest of this loop iteration after handling this case.
            continue
        if token in STOPWORDS:
            # Skip the rest of this loop iteration after handling this case.
            continue
        if re.fullmatch(r"\d+", token):
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Append the current value to keywords.
        keywords.append(token)
    # category hint expansion
    for token in list(keywords):
        if token in CATEGORY_HINTS:
            # Append the current value to keywords.
            keywords.append(normalize_text(CATEGORY_HINTS[token]))
    # unique preserve order
    seen = set()
    unique = []
    # Iterate through each k.
    for k in keywords:
        if k not in seen:
            # Append the current value to unique.
            unique.append(k)
            # Append the current value to seen.
            seen.add(k)
    return unique[:8]


# Helper for search relevant transactions.
def search_relevant_transactions(question: str, date_from: str | None = None, date_to: str | None = None, limit: int = 12) -> list[dict]:
    """Coordinate the search relevant transactions logic in the service layer.

    Args:
        question: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        date_from: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        date_to: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        limit: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Load records for the current calculation.
    records = get_all_records(SHEET_TRANSACTIONS)
    # Load records for the current calculation.
    records = filter_records_by_period(records, date_from, date_to) if (date_from or date_to) else records
    # Load records for the current calculation.
    records = enrich_finance_transactions(records)
    keywords = extract_keywords(question)
    # Validate missing keywords before continuing.
    if not keywords:
        return []

    scored = []
    # Iterate through each r.
    for r in records:
        haystack = normalize_text(" ".join(str(r.get(k, "")) for k in [
            "description", "subject", "category", "catatan", "raw_input", "account", "to_account"
        ]))
        score = 0
        # Iterate through each kw.
        for kw in keywords:
            if kw and kw in haystack:
                score += 2 if len(kw) > 4 else 1
        if score:
            scored_amount = get_effective_expense_amount(r) if str(r.get("type", "")).strip().lower() == "expense" else safe_float(r.get("amount"))
            scored.append((score, str(r.get("date", "")), scored_amount, r))

    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return [compact_transaction(r) for _, _, _, r in scored[:limit]]


# Helper for has explicit period.
def has_explicit_period(question: str) -> bool:
    """Evaluate the has explicit period condition in the service layer.

    Args:
        question: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    raw = str(question or "").lower()
    if re.search(r"20\d{2}[-/](0?[1-9]|1[0-2])", raw):
        return True
    if re.search(r"\b(0?[1-9]|1[0-2])[-/](20\d{2})\b", raw):
        return True
    period_words = [
        "hari ini", "hariini", "today", "kemarin", "yesterday",
        "minggu ini", "mingguini", "week", "bulan ini", "bulanini",
        "bulan lalu", "last month", "juni", "july", "juli", "mei",
    ]
    return any(w in raw for w in period_words)


# Helper for build ask finance context.
def build_ask_finance_context(question: str) -> dict:
    """Build the data structure or message text for ask finance context."""
    # Extract period for validation.
    period = parse_period_from_text(question)
    month_context = build_monthly_finance_context(period.get("month"))

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    explicit_period = has_explicit_period(question)
    relevant = search_relevant_transactions(
        question,
        date_from=period.get("date_from") if explicit_period else None,
        date_to=period.get("date_to") if explicit_period else None,
        limit=min(15, AI_CONTEXT_RECORD_LIMIT),
    )

    metadata = dict(month_context.get("context_metadata") or {})
    metadata.update({
        "records_selected": len(relevant),
        "context_truncated": bool(metadata.get("context_truncated")) or len(relevant) >= AI_CONTEXT_RECORD_LIMIT,
        "aggregation_level": "monthly_aggregates_with_relevant_records",
    })
    return {
        "question": question,
        "period_requested": period,
        "explicit_period": explicit_period,
        "monthly_context": month_context,
        "relevant_transactions": relevant,
        "keyword_used": extract_keywords(question),
        "context_metadata": metadata,
    }


# Helper for build audit context.
def build_audit_context(month: str | None = None) -> dict:
    """Build the data structure or message text for audit context."""
    month = normalize_month_arg(month)
    # Load records for the current calculation.
    records = get_month_transactions(month)
    # Build summary for the response flow.
    summary = summarize_transactions(records)
    # Extract category names for validation.
    category_names = sorted(get_existing_category_names())
    # Extract account names for validation.
    account_names = sorted(get_existing_account_names())
    return {
        "period": {"type": "month", "month": month},
        "summary": summary,
        "anomalies": detect_anomalies(records, summary),
        "data_quality_issues": detect_data_quality_issues(records),
        "top_expenses": get_top_transactions(records, "expense", 8),
        "known_categories": category_names,
        "known_accounts": account_names,
        "audit_scope": "kategori transaksi vs sheet categories, rekening transaksi vs sheet accounts, date/ID/plain-text fields",
        "context_metadata": {
            "records_considered": len(records),
            "records_selected": min(len(records), AI_CONTEXT_RECORD_LIMIT),
            "context_truncated": len(records) > AI_CONTEXT_RECORD_LIMIT,
            "date_range": {"month": month},
            "aggregation_level": "audit_aggregates_with_bounded_examples",
        },
    }


def build_coach_context(month: str | None = None, question: str = "") -> dict:
    """Build the data structure or message text for coach context."""
    # Prepare context from the incoming input.
    context = build_monthly_finance_context(month)
    target_saving = None
    raw = str(question or "").lower()
    m = re.search(r"(?:nabung|tabung|saving|hemat)\s+(\d+(?:[.,]\d+)?)\s*(juta|jt|rb|ribu|k)?", raw)
    if m:
        value = float(m.group(1).replace(",", "."))
        unit = m.group(2) or ""
        if unit in {"juta", "jt"}:
            value *= 1_000_000
        elif unit in {"rb", "ribu", "k"}:
            value *= 1_000
        target_saving = value

    context["goal"] = {"target_saving": target_saving}
    context["question"] = question
    return context


# Helper for should handle finance question.
def should_handle_finance_question(text: str) -> bool:
    """Decide whether the flow should handle finance question."""
    raw = str(text or "").strip().lower()
    # Validate missing raw before continuing.
    if not raw:
        return False
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Account flow section
    has_amount = bool(re.search(r"\b\d+(?:[.,]\d+)?\s*(rb|ribu|k|jt|juta)?\b", raw))
    transaction_or_debt_markers = [
        "ditalangin", "ditalangi", "dibayarin", "duluin", "nitip",
        "talangin", "talangi", "nalangin", "ngetalangin",
        "minjem", "pinjem", "pinjam", "hutang", "utang", "piutang",
        "beli", "bayar", "byr", "jajan", "makan", "minum",
        "transfer", "topup", "top up", "isi", "ngisi",
        "gaji", "dapat", "dapet", "terima", "masuk", "keluar",
    ]
    # Handle has amount and any(k in raw for k in transaction or debt mark.
    if has_amount and any(k in raw for k in transaction_or_debt_markers):
        return False

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Only trigger this when the sentence clearly asks for advice, target, or budget guidance.
    if has_amount and not any(k in raw for k in ["nabung", "tabung", "target", "budget", "saran", "coach", "hemat"]):
        return False
    if len(raw.split()) == 1 and raw not in {"insight", "audit", "coach"}:
        return False
    return any(k in raw for k in FINANCE_QUESTION_KEYWORDS)


# Helper for route finance question mode.
def route_finance_question_mode(text: str) -> str:
    """Coordinate the route finance question mode logic in the service layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    raw = str(text or "").lower()
    if any(k in raw for k in ["audit", "anomali", "aneh", "duplikat", "data quality", "data yang salah"]):
        return "audit"
    if any(k in raw for k in ["coach", "saran", "rekomendasi", "nabung", "tabung", "hemat", "kurangi"]):
        return "coach"
    if any(k in raw for k in ["budget", "anggaran", "jebol", "sisa budget"]):
        return "budget_assistant"
    if any(k in raw for k in ["insight", "analisis", "narasi", "ringkasan", "laporan"]):
        return "monthly_insight"
    return "ask"


# Helper for deterministic audit text.
def deterministic_audit_text(context: dict) -> str:
    """Coordinate the deterministic audit text logic in the service layer.

    Args:
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    lines = [f"🧹 Audit Data {context.get('period', {}).get('month', '-')}"]
    issues = context.get("data_quality_issues", [])
    anomalies = context.get("anomalies", [])

    # Validate missing issues and not anomalies before continuing.
    if not issues and not anomalies:
        return (
            "✅ Tidak ada anomali bulan ini.\n"
            "Data transaksi, kategori, rekening, dan format utama terlihat aman."
        )

    if issues:
        lines.append("\nMasalah kualitas data:")
        # Iterate through each item.
        for item in issues[:8]:
            lines.append(f"• {item.get('issue')}: {item.get('count')} transaksi")
            examples = item.get("examples") or []
            if examples:
                example = examples[0]
                extra = ""
                if example.get("suggestion"):
                    extra = f" → kemungkinan maksudnya {example.get('suggestion')}"
                lines.append(
                    f"  Contoh: {example.get('date') or '-'} — {example.get('description') or example.get('subject') or '-'} "
                    f"({example.get('amount_display') or '-'}){extra}"
                )

    if anomalies:
        lines.append("\nAnomali yang perlu dicek:")
        # Iterate through each item.
        for item in anomalies[:8]:
            if item.get("transaction"):
                txn = item["transaction"]
                lines.append(
                    f"• {item.get('message')} — {txn.get('date')} {txn.get('description')} {format_rupiah(txn.get('amount', 0))}"
                )
            # Use the fallback path when no earlier branch matched.
            else:
                lines.append(f"• {item.get('message')}")

    return "\n".join(lines)


# Helper for deterministic monthly text.
def deterministic_monthly_text(context: dict) -> str:
    """Coordinate the deterministic monthly text logic in the service layer.

    Args:
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    period = context.get("period", {})
    summary = context.get("summary", {})
    lines = [f"📌 Insight {period.get('month', '-')}"]
    lines.append(f"Pemasukan: {format_rupiah(summary.get('total_income', 0))}")
    lines.append(f"Pengeluaran: {format_rupiah(summary.get('total_expense', 0))}")
    lines.append(f"Net: {format_rupiah(summary.get('net', 0))}")

    cats = summary.get("expense_by_category", [])[:3]
    if cats:
        lines.append("\nDriver pengeluaran terbesar:")
        # Iterate through each cat.
        for cat in cats:
            lines.append(
                f"• {cat.get('name')}: {format_rupiah(cat.get('amount', 0))} ({cat.get('contribution_pct', 0)}%)"
            )

    budgets = context.get("budget_status", [])[:3]
    if budgets:
        lines.append("\nBudget yang perlu dipantau:")
        # Iterate through each b.
        for b in budgets:
            # Keep this section separated from the surrounding flow.
            lines.append(f"• {b.get('category')}: {b.get('usage_pct')}% terpakai")

    # Keep this section separated from the surrounding flow.
    return "\n".join(lines)
