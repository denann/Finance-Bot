"""Context builder service for AI finance insight, audit, coach, and ask commands."""


# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import re for this module's local operations.
import re
# Import collections so this module can use its helpers.
from collections import Counter, defaultdict
# Import datetime so this module can use its helpers.
from datetime import datetime, timedelta
# Import statistics so this module can use its helpers.
from statistics import mean, median

# Import app.config so this module can use its helpers.
from app.config import (
    # Include this value in the surrounding collection or call.
    SHEET_ACCOUNTS,
    # Include this value in the surrounding collection or call.
    SHEET_ASSETS,
    # Include this value in the surrounding collection or call.
    SHEET_BUDGETS,
    # Include this value in the surrounding collection or call.
    SHEET_CATEGORIES,
    # Include this value in the surrounding collection or call.
    SHEET_DEBTS,
    # Include this value in the surrounding collection or call.
    SHEET_TRANSACTIONS,
# Close the structure that was opened above.
)
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import get_all_records
# Import app.services.report_service so this module can use its helpers.
from app.services.report_service import enrich_transactions_with_debt_info

# Open a multi-line structure for the values below.
DEBT_CASHFLOW_CATEGORIES = {
    "Piutang Diberikan",
    "Pembayaran Piutang",
    "Penerimaan Utang",
    "Bayar Utang",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
FINANCE_QUESTION_KEYWORDS = [
    "insight", "analisis", "ringkasan", "laporan", "narasi",
    "boros", "hemat", "pengeluaran", "pemasukan", "income", "expense",
    "budget", "anggaran", "sisa budget", "jebol", "aman gak", "aman nggak",
    "anomali", "aneh", "tidak biasa", "audit", "data quality", "duplikat",
    "transaksi terbesar", "terakhir", "kapan", "berapa total", "total", "cari transaksi",
    "saran", "coach", "rekomendasi", "nabung", "tabung", "kurangi",
    "pending", "rencana", "pengeluaran akan datang",
    "saldo", "utang", "hutang", "piutang", "net worth", "aset",
# Close the structure that was opened above.
]

# Open a multi-line structure for the values below.
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
# Close the structure that was opened above.
]

# Open a multi-line structure for the values below.
STOPWORDS = {
    "aku", "saya", "gue", "gua", "gw", "bulan", "ini", "itu", "di", "ke", "dari", "yang",
    "dan", "atau", "untuk", "berapa", "total", "transaksi", "pengeluaran", "pemasukan",
    "makan", "budget", "aman", "gak", "nggak", "ga", "dong", "ya", "apa", "aja",
    "kapan", "terakhir", "cari", "lihat", "cek", "tolong", "kasih", "saran", "saya",
    "hari", "minggu", "tahun", "periode", "saldo", "rekening", "kenapa", "turun", "naik",
    "bulanini", "hariini", "mingguini",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
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
# Close the structure that was opened above.
}


# Define safe float for callers in this flow.
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
        # Return default to the caller.
        return default

    # Handle the case where isinstance(value, (int, float)).
    if isinstance(value, (int, float)):
        # Return float(value) to the caller.
        return float(value)

    # Prepare raw for the next step.
    raw = str(value).strip()
    # Handle the missing or empty raw case.
    if not raw:
        # Return default to the caller.
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
        # Handle the fallback path after earlier conditions are skipped.
        else:
            raw = raw.replace(",", "")
    elif "." in raw:
        parts = raw.split(".")
        # 427.500 atau 1.427.500 = ribuan.
        # Implementation section
        if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
            raw = raw.replace(".", "")

    raw = re.sub(r"[^0-9.-]", "", raw)

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Return float(raw) to the caller.
        return float(raw)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return default to the caller.
        return default


# Define format rupiah for callers in this flow.
def format_rupiah(amount: float) -> str:
    """Format data into a readable display for rupiah."""
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")


# Define current month for callers in this flow.
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
    return datetime.now().strftime("%Y-%m")


# Define normalize month arg for callers in this flow.
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
    # Prepare today for the next step.
    today = datetime.now()
    # Handle the missing or empty value case.
    if not value:
        # Return current_month() to the caller.
        return current_month()

    raw = str(value).strip().lower().replace("/", "-")
    raw = re.sub(r"\s+", " ", raw)

    if raw in {"bulan ini", "bulanini", "month", "current", "sekarang"}:
        # Return current_month() to the caller.
        return current_month()

    m = re.search(r"(20\d{2})[-\s](0?[1-9]|1[0-2])", raw)
    # Handle the case where m.
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"

    m = re.fullmatch(r"(0?[1-9]|1[0-2])", raw)
    # Handle the case where m.
    if m:
        return f"{today.year}-{int(m.group(1)):02d}"

    # Return current_month() to the caller.
    return current_month()


# Define previous month for callers in this flow.
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
    # Handle the case where month_num == 1.
    if month_num == 1:
        return f"{year - 1}-12"
    return f"{year}-{month_num - 1:02d}"


# Define month bounds for callers in this flow.
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
    # Prepare first for the next step.
    first = datetime(year, month_num, 1)
    # Handle the case where month_num == 12.
    if month_num == 12:
        # Prepare next first for the next step.
        next_first = datetime(year + 1, 1, 1)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare next first for the next step.
        next_first = datetime(year, month_num + 1, 1)
    # Prepare last for the next step.
    last = next_first - timedelta(days=1)
    return first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d")


# Define parse period from text for callers in this flow.
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
    # Prepare today for the next step.
    today = datetime.now().date()

    m = re.search(r"(20\d{2})[-/](0?[1-9]|1[0-2])", raw)
    # Handle the case where m.
    if m:
        month = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
        # Run this statement as part of the current workflow.
        start, end = month_bounds(month)
        return {"type": "month", "month": month, "date_from": start, "date_to": end, "label": month}

    m = re.search(r"\b(0?[1-9]|1[0-2])[-/](20\d{2})\b", raw)
    # Handle the case where m.
    if m:
        month = f"{int(m.group(2)):04d}-{int(m.group(1)):02d}"
        # Run this statement as part of the current workflow.
        start, end = month_bounds(month)
        return {"type": "month", "month": month, "date_from": start, "date_to": end, "label": month}

    if any(k in raw for k in ["hari ini", "hariini", "today"]):
        d = today.strftime("%Y-%m-%d")
        return {"type": "day", "month": d[:7], "date_from": d, "date_to": d, "label": d}

    if any(k in raw for k in ["kemarin", "yesterday"]):
        d = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        return {"type": "day", "month": d[:7], "date_from": d, "date_to": d, "label": d}

    if any(k in raw for k in ["minggu ini", "mingguini", "week"]):
        # Prepare monday for the next step.
        monday = today - timedelta(days=today.weekday())
        # Prepare sunday for the next step.
        sunday = monday + timedelta(days=6)
        # Return { to the caller.
        return {
            "type": "week",
            "month": today.strftime("%Y-%m"),
            "date_from": monday.strftime("%Y-%m-%d"),
            "date_to": sunday.strftime("%Y-%m-%d"),
            "label": f"{monday} s/d {sunday}",
        # Close the structure that was opened above.
        }

    if any(k in raw for k in ["bulan lalu", "last month"]):
        # Prepare month for the next step.
        month = previous_month(current_month())
        # Run this statement as part of the current workflow.
        start, end = month_bounds(month)
        return {"type": "month", "month": month, "date_from": start, "date_to": end, "label": month}

    # Prepare month for the next step.
    month = current_month()
    # Run this statement as part of the current workflow.
    start, end = month_bounds(month)
    return {"type": "month", "month": month, "date_from": start, "date_to": end, "label": month}


# Define normalize text for callers in this flow.
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




# Define normalize sheet date value for callers in this flow.
def normalize_sheet_date_value(value) -> str:
    """Normalize Google Sheets date values before filtering or auditing."""
    # Handle the case where value is None.
    if value is None:
        return ""
    # Prepare raw for the next step.
    raw = str(value).strip()
    if not raw or raw.lower() in {"-", "none", "nan"}:
        return ""

    match = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", raw)
    # Handle the case where match.
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
            # Prepare serial for the next step.
            serial = int(float(raw))
            # Handle the case where 20000 <= serial <= 80000.
            if 20000 <= serial <= 80000:
                # Prepare dt for the next step.
                dt = datetime(1899, 12, 30) + timedelta(days=serial)
                return dt.strftime("%Y-%m-%d")
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass

    # Return raw to the caller.
    return raw


# Define is valid id text for callers in this flow.
def is_valid_id_text(value: str, prefixes: tuple[str, ...]) -> bool:
    """Check whether an ID field still looks like bot-generated plain text."""
    raw = str(value or "").strip()
    return bool(raw) and raw.startswith(prefixes) and "e+" not in raw.lower()


# Define get existing category names for callers in this flow.
def get_existing_category_names() -> set[str]:
    """Read category names from sheet categories for audit checks."""
    # Prepare names for the next step.
    names = set()
    # Process each row in the current collection.
    for row in get_all_records(SHEET_CATEGORIES):
        name = str(row.get("category_name") or row.get("name") or "").strip()
        # Handle the case where name.
        if name:
            # Update names with the current value.
            names.add(name)
    # Return names to the caller.
    return names


# Define get existing account names for callers in this flow.
def get_existing_account_names() -> set[str]:
    """Read account names from sheet accounts for audit checks."""
    # Prepare names for the next step.
    names = set()
    # Process each row in the current collection.
    for row in get_all_records(SHEET_ACCOUNTS):
        name = str(row.get("account_name") or row.get("name") or "").strip()
        # Handle the case where name.
        if name:
            # Update names with the current value.
            names.add(name)
    # Return names to the caller.
    return names

# Define is date between for callers in this flow.
def is_date_between(date_value: str, date_from: str | None, date_to: str | None) -> bool:
    """Check whether a condition is true for date between."""
    # Prepare date value for the next step.
    date_value = normalize_sheet_date_value(date_value)
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", date_value):
        # Return False to the caller.
        return False
    # Handle the case where date_from and date_value < date_from.
    if date_from and date_value < date_from:
        # Return False to the caller.
        return False
    # Handle the case where date_to and date_value > date_to.
    if date_to and date_value > date_to:
        # Return False to the caller.
        return False
    # Return True to the caller.
    return True


# Define filter records by period for callers in this flow.
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


# Define get month transactions for callers in this flow.
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
    # Run this statement as part of the current workflow.
    date_from, date_to = month_bounds(month)
    # Prepare records for the next step.
    records = get_all_records(SHEET_TRANSACTIONS)
    # Return filter_records_by_period(records, date_from, date_to) to the caller.
    return filter_records_by_period(records, date_from, date_to)


# Define enrich finance transactions for callers in this flow.
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
    # Prepare records for the next step.
    records = records or []
    # Handle the case where any(.
    if any(
        str((r or {}).get("type", "")).strip().lower() == "expense"
        and "net_expense_after_receivable" in (r or {})
        # Process each r in the current collection.
        for r in records
    # Close the structure that was opened above.
    ):
        # Return records to the caller.
        return records
    # Return enrich_transactions_with_debt_info(records) to the caller.
    return enrich_transactions_with_debt_info(records)


# Define get effective expense amount for callers in this flow.
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
        # Return amount to the caller.
        return amount

    if "net_expense_after_receivable" in (record or {}):
        return max(safe_float((record or {}).get("net_expense_after_receivable")), 0.0)

    # Open a multi-line structure for the values below.
    receivable = safe_float(
        (record or {}).get("debt_receivable_original", (record or {}).get("debt_receivable_remaining", 0))
    # Close the structure that was opened above.
    )
    # Return max(amount - receivable, 0.0) to the caller.
    return max(amount - receivable, 0.0)


# Define summarize transactions for callers in this flow.
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
    # Prepare total income for the next step.
    total_income = 0.0
    # Prepare total expense for the next step.
    total_expense = 0.0  # Net expense after split bill receivables.
    # Prepare total transfer for the next step.
    total_transfer = 0.0
    # Prepare expense by category for the next step.
    expense_by_category = defaultdict(float)
    # Prepare income by category for the next step.
    income_by_category = defaultdict(float)
    # Prepare expense by account for the next step.
    expense_by_account = defaultdict(float)
    # Prepare income by account for the next step.
    income_by_account = defaultdict(float)
    # Prepare cash out by account for the next step.
    cash_out_by_account = defaultdict(float)
    # Prepare cash in by account for the next step.
    cash_in_by_account = defaultdict(float)

    # Prepare records for the next step.
    records = enrich_finance_transactions(records)

    # Process each r in the current collection.
    for r in records:
        txn_type = str(r.get("type", "")).strip().lower()
        amount = safe_float(r.get("amount"))
        # Prepare effective amount for the next step.
        effective_amount = get_effective_expense_amount(r)
        category = str(r.get("category") or "Uncategorized").strip() or "Uncategorized"
        account = str(r.get("account") or "-").strip() or "-"
        to_account = str(r.get("to_account") or "").strip()

        if txn_type == "income":
            # Run this statement as part of the current workflow.
            total_income += amount
            # Run this statement as part of the current workflow.
            income_by_category[category] += amount
            # Run this statement as part of the current workflow.
            income_by_account[account] += amount
            # Run this statement as part of the current workflow.
            cash_in_by_account[account] += amount
        elif txn_type == "expense":
            # Debt flow section
            # Debt flow section
            total_expense += effective_amount
            # Run this statement as part of the current workflow.
            expense_by_category[category] += effective_amount
            # Run this statement as part of the current workflow.
            expense_by_account[account] += effective_amount
            # Run this statement as part of the current workflow.
            cash_out_by_account[account] += effective_amount
        elif txn_type == "transfer":
            # Run this statement as part of the current workflow.
            total_transfer += amount
            # Run this statement as part of the current workflow.
            cash_out_by_account[account] += amount
            # Handle the case where to_account.
            if to_account:
                # Run this statement as part of the current workflow.
                cash_in_by_account[to_account] += amount

    # Define sorted items for callers in this flow.
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
        # Return [ to the caller.
        return [
            {"name": k, "amount": v, "amount_display": format_rupiah(v)}
            # Process each k, v in the current collection.
            for k, v in sorted(d.items(), key=lambda x: x[1], reverse=True)
            # Handle the case where abs(v) > 0.0001.
            if abs(v) > 0.0001
        # Close the structure that was opened above.
        ]

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }


# Define add contribution for callers in this flow.
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
    # Prepare result for the next step.
    result = []
    # Process each item in the current collection.
    for item in items[:limit]:
        amount = float(item.get("amount", 0) or 0)
        # Open a multi-line structure for the values below.
        result.append({
            # Include this value in the surrounding collection or call.
            **item,
            "contribution_pct": round((amount / total * 100), 1) if total else 0,
        # Close the structure that was opened above.
        })
    # Return result to the caller.
    return result


# Define compact transaction for callers in this flow.
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
    # Prepare amount for the next step.
    amount = get_effective_expense_amount(r)
    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    }
    if str(r.get("type", "")).strip().lower() == "expense":
        item["amount_basis"] = "net_after_receivable"
    # Return item to the caller.
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
    # Prepare records for the next step.
    records = enrich_finance_transactions(records)
    # Prepare candidates for the next step.
    candidates = []
    # Process each r in the current collection.
    for r in records:
        if txn_type and str(r.get("type", "")).strip().lower() != txn_type:
            # Skip the rest of this loop iteration after handling this case.
            continue
        amount = get_effective_expense_amount(r) if str(r.get("type", "")).strip().lower() == "expense" else safe_float(r.get("amount"))
        # Handle the case where amount <= 0.
        if amount <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Update candidates with the current value.
        candidates.append(r)
    # Open a multi-line structure for the values below.
    candidates.sort(
        key=lambda x: get_effective_expense_amount(x) if str(x.get("type", "")).strip().lower() == "expense" else safe_float(x.get("amount")),
        # Prepare reverse for the next step.
        reverse=True,
    # Close the structure that was opened above.
    )
    # Return [compact_transaction(r) for r in candidates[:limit]] to the caller.
    return [compact_transaction(r) for r in candidates[:limit]]


# Define get budget status for callers in this flow.
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
    # Open a multi-line structure for the values below.
    budgets = [
        # Run this statement as part of the current workflow.
        b for b in get_all_records(SHEET_BUDGETS)
        if str(b.get("month", "")).strip() == month
    # Close the structure that was opened above.
    ]
    # Handle the missing or empty budgets case.
    if not budgets:
        # Return [] to the caller.
        return []

    # Prepare expense by category for the next step.
    expense_by_category = defaultdict(float)
    # Process each r in the current collection.
    for r in enrich_finance_transactions(transactions):
        if str(r.get("type", "")).strip().lower() != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue
        category = str(r.get("category") or "Uncategorized").strip()
        # Run this statement as part of the current workflow.
        expense_by_category[category.lower()] += get_effective_expense_amount(r)

    # Prepare result for the next step.
    result = []
    # Process each b in the current collection.
    for b in budgets:
        category = str(b.get("category") or "").strip()
        budget_amount = safe_float(b.get("budget_amount"))
        # Prepare actual for the next step.
        actual = expense_by_category.get(category.lower(), 0.0)
        # Prepare remaining for the next step.
        remaining = budget_amount - actual
        # Prepare pct for the next step.
        pct = (actual / budget_amount * 100) if budget_amount else 0
        # Open a multi-line structure for the values below.
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
        # Close the structure that was opened above.
        })

    result.sort(key=lambda x: x["usage_pct"], reverse=True)
    # Return result to the caller.
    return result


# Define get accounts summary for callers in this flow.
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
    # Prepare accounts for the next step.
    accounts = []
    # Prepare total for the next step.
    total = 0.0
    # Process each acc in the current collection.
    for acc in get_all_records(SHEET_ACCOUNTS):
        balance = safe_float(acc.get("balance"))
        # Run this statement as part of the current workflow.
        total += balance
        # Open a multi-line structure for the values below.
        accounts.append({
            "name": acc.get("account_name") or acc.get("name") or "-",
            "balance": balance,
            "balance_display": format_rupiah(balance),
            "type": acc.get("type", ""),
        # Close the structure that was opened above.
        })
    accounts.sort(key=lambda x: x["balance"], reverse=True)
    return {"total": total, "total_display": format_rupiah(total), "accounts": accounts}


# Define get debt summary compact for callers in this flow.
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
    # Prepare debts for the next step.
    debts = get_all_records(SHEET_DEBTS)
    # Prepare active for the next step.
    active = []
    # Prepare totals for the next step.
    totals = defaultdict(float)
    # Process each d in the current collection.
    for d in debts:
        status = str(d.get("status") or d.get("is_active") or "").strip().lower()
        remaining = safe_float(d.get("remaining_amount") or d.get("amount"))
        if remaining <= 0 or status in {"settled", "closed", "void", "false"}:
            # Skip the rest of this loop iteration after handling this case.
            continue
        debt_type = str(d.get("type") or d.get("debt_type") or "").strip().lower()
        # Handle the missing or empty debt_type case.
        if not debt_type:
            # Legacy compatibility note for older records or older in-memory state.
            text = normalize_text(" ".join(str(d.get(k, "")) for k in ["category", "description", "catatan"]))
            debt_type = "receivable" if "piutang" in text else "payable" if "utang" in text or "hutang" in text else "unknown"
        # Run this statement as part of the current workflow.
        totals[debt_type] += remaining
        # Open a multi-line structure for the values below.
        active.append({
            "person": d.get("person") or d.get("person_name") or d.get("subject") or "-",
            "type": debt_type,
            "remaining_amount": remaining,
            "remaining_amount_display": format_rupiah(remaining),
            "description": d.get("description", ""),
            "id": d.get("id", ""),
        # Close the structure that was opened above.
        })
    active.sort(key=lambda x: x["remaining_amount"], reverse=True)
    # Return { to the caller.
    return {
        "total_payable": totals.get("payable", 0.0),
        "total_payable_display": format_rupiah(totals.get("payable", 0.0)),
        "total_receivable": totals.get("receivable", 0.0),
        "total_receivable_display": format_rupiah(totals.get("receivable", 0.0)),
        "active_count": len(active),
        "top_active": active[:8],
    # Close the structure that was opened above.
    }


# Define get net worth compact for callers in this flow.
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
    # Prepare assets for the next step.
    assets = get_all_records(SHEET_ASSETS)
    # Prepare active assets for the next step.
    active_assets = []

    # Prepare total assets for the next step.
    total_assets = 0.0

    # Process each a in the current collection.
    for a in assets:
        is_active = str(a.get("is_active", "TRUE")).strip().upper() != "FALSE"
        # Handle the missing or empty is_active case.
        if not is_active:
            # Skip the rest of this loop iteration after handling this case.
            continue
        value = safe_float(a.get("current_value"))
        # Run this statement as part of the current workflow.
        total_assets += value
        # Open a multi-line structure for the values below.
        active_assets.append({
            "name": a.get("name", "-"),
            "value": value,
            "value_display": format_rupiah(value),
            "category": a.get("category", ""),
            "quantity": a.get("quantity", ""),
            "unit": a.get("unit", ""),
            "price_per_unit": safe_float(a.get("price_per_unit")),
            "price_per_unit_display": format_rupiah(safe_float(a.get("price_per_unit"))),
        # Close the structure that was opened above.
        })

    # Prepare accounts for the next step.
    accounts = get_accounts_summary()
    # Return { to the caller.
    return {
        "total_accounts": accounts["total"],
        "total_accounts_display": format_rupiah(accounts["total"]),
        "total_assets": total_assets,
        "total_assets_display": format_rupiah(total_assets),
        "total_liabilities": 0.0,
        "total_liabilities_display": format_rupiah(0),
        "net_worth": accounts["total"] + total_assets,
        "net_worth_display": format_rupiah(accounts["total"] + total_assets),
        "top_assets": sorted(active_assets, key=lambda x: x["value"], reverse=True)[:8],
        "top_liabilities": [],
        "note": "Liabilities sudah dihapus dari fitur net worth; kewajiban antar orang dikelola via /hutang.",
    # Close the structure that was opened above.
    }


# Define detect anomalies for callers in this flow.
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
    # Prepare records for the next step.
    records = enrich_finance_transactions(records)
    expenses = [r for r in records if str(r.get("type", "")).strip().lower() == "expense"]
    # Prepare amounts for the next step.
    amounts = [get_effective_expense_amount(r) for r in expenses if get_effective_expense_amount(r) > 0]
    # Prepare anomalies for the next step.
    anomalies = []

    # Handle the case where amounts.
    if amounts:
        # Prepare med for the next step.
        med = median(amounts)
        # Prepare avg for the next step.
        avg = mean(amounts)
        # Prepare threshold for the next step.
        threshold = max(200_000, med * 3, avg * 2)
        # Process each r in the current collection.
        for r in expenses:
            # Prepare amount for the next step.
            amount = get_effective_expense_amount(r)
            # Handle the case where amount >= threshold.
            if amount >= threshold:
                # Open a multi-line structure for the values below.
                anomalies.append({
                    "type": "large_expense",
                    "severity": "warning",
                    "message": "Nominal pengeluaran net jauh lebih besar dari transaksi biasa.",
                    "transaction": compact_transaction(r),
                    "threshold": threshold,
                    "threshold_display": format_rupiah(threshold),
                    "amount_basis": "net_after_receivable",
                # Close the structure that was opened above.
                })

    # Potential duplicates: same date + amount + normalized description.
    bucket = defaultdict(list)
    # Process each r in the current collection.
    for r in records:
        # Open a multi-line structure for the values below.
        key = (
            normalize_sheet_date_value(r.get("date", "")),
            str(r.get("type", "")),
            int(get_effective_expense_amount(r) if str(r.get("type", "")).strip().lower() == "expense" else safe_float(r.get("amount"))),
            normalize_text(str(r.get("description", "")))[:40],
        # Close the structure that was opened above.
        )
        # Handle the case where key[2] > 0 and key[3].
        if key[2] > 0 and key[3]:
            # Run this statement as part of the current workflow.
            bucket[key].append(r)
    # Process each items in the current collection.
    for items in bucket.values():
        # Handle the case where len(items) > 1.
        if len(items) > 1:
            # Open a multi-line structure for the values below.
            anomalies.append({
                "type": "possible_duplicate",
                "severity": "warning",
                "message": "Ada transaksi yang tanggal, nominal, dan deskripsinya mirip.",
                "transactions": [compact_transaction(x) for x in items[:5]],
            # Close the structure that was opened above.
            })

    # Category spikes vs share.
    if month_summary:
        total_expense = month_summary.get("total_expense", 0) or 0
        for item in month_summary.get("expense_by_category", [])[:5]:
            amount = item.get("amount", 0)
            # Prepare pct for the next step.
            pct = (amount / total_expense * 100) if total_expense else 0
            # Handle the case where total_expense and pct >= 45.
            if total_expense and pct >= 45:
                # Open a multi-line structure for the values below.
                anomalies.append({
                    "type": "category_concentration",
                    "severity": "info",
                    "message": f"Kategori {item.get('name')} menyumbang {pct:.1f}% dari pengeluaran.",
                    "category": item.get("name"),
                    "amount": amount,
                    "amount_display": format_rupiah(amount),
                    "contribution_pct": round(pct, 1),
                # Close the structure that was opened above.
                })

    # Return anomalies[:12] to the caller.
    return anomalies[:12]


# Define detect data quality issues for callers in this flow.
def detect_data_quality_issues(records: list[dict]) -> list[dict]:
    """Detect transaction data quality issues against sheet accounts/categories."""
    # Prepare issues for the next step.
    issues = []
    # Prepare counters for the next step.
    counters = Counter()
    # Prepare examples for the next step.
    examples = defaultdict(list)

    # Prepare category names for the next step.
    category_names = get_existing_category_names()
    # Prepare category lookup for the next step.
    category_lookup = {normalize_text(name): name for name in category_names}
    # Prepare account names for the next step.
    account_names = get_existing_account_names()
    # Prepare account lookup for the next step.
    account_lookup = {normalize_text(name): name for name in account_names}

    # Define find similar name for callers in this flow.
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
        # Prepare clean for the next step.
        clean = normalize_text(name)
        # Handle the missing or empty clean case.
        if not clean:
            # Return None to the caller.
            return None
        # Handle the case where clean in lookup.
        if clean in lookup:
            # Return lookup[clean] to the caller.
            return lookup[clean]
        # Process each key, original in the current collection.
        for key, original in lookup.items():
            # Handle the case where clean in key or key in clean.
            if clean in key or key in clean:
                # Return original to the caller.
                return original
        # Return None to the caller.
        return None

    # Process each r in the current collection.
    for r in records:
        txn_type = str(r.get("type", "")).strip().lower()
        amount = safe_float(r.get("amount"))
        raw_date = str(r.get("date", "")).strip()
        # Prepare normalized date for the next step.
        normalized_date = normalize_sheet_date_value(raw_date)
        account = str(r.get("account") or "").strip()
        to_account = str(r.get("to_account") or "").strip()
        category = str(r.get("category") or "").strip()
        txn_id = str(r.get("id") or "").strip()
        raw_input = str(r.get("raw_input") or "").strip()
        subject = str(r.get("subject") or "").strip()
        description = str(r.get("description") or "").strip()

        # Define add issue for callers in this flow.
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
            # Run this statement as part of the current workflow.
            counters[key] += 1
            # Handle the case where len(examples[key]) < 5.
            if len(examples[key]) < 5:
                example = compact_transaction({**r, "date": normalized_date})
                # Handle the case where extra.
                if extra:
                    # Update example with the current value.
                    example.update(extra)
                # Run this statement as part of the current workflow.
                examples[key].append(example)

        if txn_type not in {"expense", "income", "transfer", "debt_offset", "debt_only"}:
            add_issue("type tidak valid/kosong")
        # Handle the case where amount <= 0.
        if amount <= 0:
            add_issue("amount kosong/0")
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", normalized_date):
            add_issue("tanggal invalid/kosong")
        # Handle the alternate case where raw_date != normalized_date.
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
        # Handle the alternate case where account and normalize_text(account) not in account_lookup.
        elif account and normalize_text(account) not in account_lookup:
            if str(account).lower() not in {"sudah berlalu", "tanpa rekening", "debt only", "debt offset"}:
                # Prepare similar for the next step.
                similar = find_similar_name(account, account_lookup)
                issue_name = "account mirip tapi tidak persis dengan sheet accounts" if similar else "account tidak ada di sheet accounts"
                add_issue(issue_name, {"account_input": account, "suggestion": similar or ""})

        if txn_type == "transfer":
            # Handle the missing or empty to_account case.
            if not to_account:
                add_issue("transfer tanpa to_account")
            # Handle the alternate case where normalize_text(to_account) not in account_lookup.
            elif normalize_text(to_account) not in account_lookup:
                # Prepare similar for the next step.
                similar = find_similar_name(to_account, account_lookup)
                issue_name = "to_account mirip tapi tidak persis dengan sheet accounts" if similar else "to_account tidak ada di sheet accounts"
                add_issue(issue_name, {"to_account_input": to_account, "suggestion": similar or ""})

        if txn_type in {"expense", "income"} and to_account:
            add_issue("income/expense punya to_account")

        if txn_type == "expense" and not category:
            add_issue("expense tanpa category")
        elif txn_type == "expense":
            # Prepare category key for the next step.
            category_key = normalize_text(category)
            # Handle the case where category_key not in category_lookup.
            if category_key not in category_lookup:
                # Prepare similar for the next step.
                similar = find_similar_name(category, category_lookup)
                issue_name = "kategori mirip tapi tidak persis dengan sheet categories" if similar else "kategori tidak ada di sheet categories"
                add_issue(issue_name, {"category_input": category, "suggestion": similar or ""})
            if category == "Other Expense":
                add_issue("expense masih Other Expense")
            if category == "Utang Tanpa Cashflow":
                add_issue("expense kategori Utang Tanpa Cashflow")

    # Process each key, count in the current collection.
    for key, count in counters.most_common():
        issues.append({"issue": key, "count": count, "examples": examples[key]})

    # Return issues to the caller.
    return issues

# Define compare summaries for callers in this flow.
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
    # Define diff for callers in this flow.
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
        # Prepare cur for the next step.
        cur = float(current.get(key, 0) or 0)
        # Prepare prev for the next step.
        prev = float(previous.get(key, 0) or 0)
        # Prepare delta for the next step.
        delta = cur - prev
        # Prepare pct for the next step.
        pct = (delta / prev * 100) if prev else None
        # Return { to the caller.
        return {
            "current": cur,
            "current_display": format_rupiah(cur),
            "previous": prev,
            "previous_display": format_rupiah(prev),
            "delta": delta,
            "delta_display": format_rupiah(delta),
            "delta_pct": round(pct, 1) if pct is not None else None,
        # Close the structure that was opened above.
        }

    # Return { to the caller.
    return {
        "income": diff("total_income"),
        "expense": diff("total_expense"),
        "net": diff("net"),
    # Close the structure that was opened above.
    }


# Define build monthly finance context for callers in this flow.
def build_monthly_finance_context(month: str | None = None) -> dict:
    """Build the data structure or message text for monthly finance context."""
    # Prepare month for the next step.
    month = normalize_month_arg(month)
    # Prepare prev month for the next step.
    prev_month = previous_month(month)

    # Prepare records for the next step.
    records = get_month_transactions(month)
    # Prepare prev records for the next step.
    prev_records = get_month_transactions(prev_month)
    # Prepare summary for the next step.
    summary = summarize_transactions(records)
    # Prepare prev summary for the next step.
    prev_summary = summarize_transactions(prev_records)

    summary["expense_by_category"] = add_contribution(
        summary["expense_by_category"],
        summary["total_expense"],
        # Prepare limit for the next step.
        limit=10,
    # Close the structure that was opened above.
    )
    summary["income_by_category"] = add_contribution(
        summary["income_by_category"],
        summary["total_income"],
        # Prepare limit for the next step.
        limit=8,
    # Close the structure that was opened above.
    )

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }


# Define extract keywords for callers in this flow.
def extract_keywords(question: str) -> list[str]:
    """Extract the required part of input for keywords."""
    # Prepare clean for the next step.
    clean = normalize_text(question)
    # Keep meaningful multi-token known phrases.
    keywords = []
    for phrase in ["food beverage", "other expense", "kopi kenangan", "nasi padang", "ptpt"]:
        # Handle the case where phrase in clean.
        if phrase in clean:
            # Update keywords with the current value.
            keywords.append(phrase)
    # Process each token in the current collection.
    for token in clean.split():
        # Handle the case where len(token) < 3.
        if len(token) < 3:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the case where token in STOPWORDS.
        if token in STOPWORDS:
            # Skip the rest of this loop iteration after handling this case.
            continue
        if re.fullmatch(r"\d+", token):
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Update keywords with the current value.
        keywords.append(token)
    # category hint expansion
    for token in list(keywords):
        # Handle the case where token in CATEGORY_HINTS.
        if token in CATEGORY_HINTS:
            # Update keywords with the current value.
            keywords.append(normalize_text(CATEGORY_HINTS[token]))
    # unique preserve order
    seen = set()
    # Prepare unique for the next step.
    unique = []
    # Process each k in the current collection.
    for k in keywords:
        # Handle the case where k not in seen.
        if k not in seen:
            # Update unique with the current value.
            unique.append(k)
            # Update seen with the current value.
            seen.add(k)
    # Return unique[:8] to the caller.
    return unique[:8]


# Define search relevant transactions for callers in this flow.
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
    # Prepare records for the next step.
    records = get_all_records(SHEET_TRANSACTIONS)
    # Prepare records for the next step.
    records = filter_records_by_period(records, date_from, date_to) if (date_from or date_to) else records
    # Prepare records for the next step.
    records = enrich_finance_transactions(records)
    # Prepare keywords for the next step.
    keywords = extract_keywords(question)
    # Handle the missing or empty keywords case.
    if not keywords:
        # Return [] to the caller.
        return []

    # Prepare scored for the next step.
    scored = []
    # Process each r in the current collection.
    for r in records:
        haystack = normalize_text(" ".join(str(r.get(k, "")) for k in [
            "description", "subject", "category", "catatan", "raw_input", "account", "to_account"
        # Close the structure that was opened above.
        ]))
        # Prepare score for the next step.
        score = 0
        # Process each kw in the current collection.
        for kw in keywords:
            # Handle the case where kw and kw in haystack.
            if kw and kw in haystack:
                # Run this statement as part of the current workflow.
                score += 2 if len(kw) > 4 else 1
        # Handle the case where score.
        if score:
            scored_amount = get_effective_expense_amount(r) if str(r.get("type", "")).strip().lower() == "expense" else safe_float(r.get("amount"))
            scored.append((score, str(r.get("date", "")), scored_amount, r))

    # Run this statement as part of the current workflow.
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    # Return [compact_transaction(r) for _, _, _, r in scored[:limit]] to the caller.
    return [compact_transaction(r) for _, _, _, r in scored[:limit]]


# Define has explicit period for callers in this flow.
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
        # Return True to the caller.
        return True
    if re.search(r"\b(0?[1-9]|1[0-2])[-/](20\d{2})\b", raw):
        # Return True to the caller.
        return True
    # Open a multi-line structure for the values below.
    period_words = [
        "hari ini", "hariini", "today", "kemarin", "yesterday",
        "minggu ini", "mingguini", "week", "bulan ini", "bulanini",
        "bulan lalu", "last month", "juni", "july", "juli", "mei",
    # Close the structure that was opened above.
    ]
    # Return any(w in raw for w in period_words) to the caller.
    return any(w in raw for w in period_words)


# Define build ask finance context for callers in this flow.
def build_ask_finance_context(question: str) -> dict:
    """Build the data structure or message text for ask finance context."""
    # Prepare period for the next step.
    period = parse_period_from_text(question)
    month_context = build_monthly_finance_context(period.get("month"))

    # Implementation section
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    explicit_period = has_explicit_period(question)
    # Open a multi-line structure for the values below.
    relevant = search_relevant_transactions(
        # Include this value in the surrounding collection or call.
        question,
        date_from=period.get("date_from") if explicit_period else None,
        date_to=period.get("date_to") if explicit_period else None,
        # Prepare limit for the next step.
        limit=15,
    # Close the structure that was opened above.
    )

    # Return { to the caller.
    return {
        "question": question,
        "period_requested": period,
        "explicit_period": explicit_period,
        "monthly_context": month_context,
        "relevant_transactions": relevant,
        "keyword_used": extract_keywords(question),
    # Close the structure that was opened above.
    }


# Define build audit context for callers in this flow.
def build_audit_context(month: str | None = None) -> dict:
    """Build the data structure or message text for audit context."""
    # Prepare month for the next step.
    month = normalize_month_arg(month)
    # Prepare records for the next step.
    records = get_month_transactions(month)
    # Prepare summary for the next step.
    summary = summarize_transactions(records)
    # Prepare category names for the next step.
    category_names = sorted(get_existing_category_names())
    # Prepare account names for the next step.
    account_names = sorted(get_existing_account_names())
    # Return { to the caller.
    return {
        "period": {"type": "month", "month": month},
        "summary": summary,
        "anomalies": detect_anomalies(records, summary),
        "data_quality_issues": detect_data_quality_issues(records),
        "top_expenses": get_top_transactions(records, "expense", 8),
        "known_categories": category_names,
        "known_accounts": account_names,
        "audit_scope": "kategori transaksi vs sheet categories, rekening transaksi vs sheet accounts, date/ID/plain-text fields",
    # Close the structure that was opened above.
    }


def build_coach_context(month: str | None = None, question: str = "") -> dict:
    """Build the data structure or message text for coach context."""
    # Prepare context for the next step.
    context = build_monthly_finance_context(month)
    # Prepare target saving for the next step.
    target_saving = None
    raw = str(question or "").lower()
    m = re.search(r"(?:nabung|tabung|saving|hemat)\s+(\d+(?:[.,]\d+)?)\s*(juta|jt|rb|ribu|k)?", raw)
    # Handle the case where m.
    if m:
        value = float(m.group(1).replace(",", "."))
        unit = m.group(2) or ""
        if unit in {"juta", "jt"}:
            # Run this statement as part of the current workflow.
            value *= 1_000_000
        elif unit in {"rb", "ribu", "k"}:
            # Run this statement as part of the current workflow.
            value *= 1_000
        # Prepare target saving for the next step.
        target_saving = value

    context["goal"] = {"target_saving": target_saving}
    context["question"] = question
    # Return context to the caller.
    return context


# Define should handle finance question for callers in this flow.
def should_handle_finance_question(text: str) -> bool:
    """Decide whether the flow should handle finance question."""
    raw = str(text or "").strip().lower()
    # Handle the missing or empty raw case.
    if not raw:
        # Return False to the caller.
        return False
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Account flow section
    # Implementation section
    has_amount = bool(re.search(r"\b\d+(?:[.,]\d+)?\s*(rb|ribu|k|jt|juta)?\b", raw))
    # Open a multi-line structure for the values below.
    transaction_or_debt_markers = [
        "ditalangin", "ditalangi", "dibayarin", "duluin", "nitip",
        "talangin", "talangi", "nalangin", "ngetalangin",
        "minjem", "pinjem", "pinjam", "hutang", "utang", "piutang",
        "beli", "bayar", "byr", "jajan", "makan", "minum",
        "transfer", "topup", "top up", "isi", "ngisi",
        "gaji", "dapat", "dapet", "terima", "masuk", "keluar",
    # Close the structure that was opened above.
    ]
    # Handle the case where has_amount and any(k in raw for k in transaction_or_debt_mark....
    if has_amount and any(k in raw for k in transaction_or_debt_markers):
        # Return False to the caller.
        return False

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Only trigger this when the sentence clearly asks for advice, target, or budget guidance.
    if has_amount and not any(k in raw for k in ["nabung", "tabung", "target", "budget", "saran", "coach", "hemat"]):
        # Return False to the caller.
        return False
    # Implementation section
    if len(raw.split()) == 1 and raw not in {"insight", "audit", "coach"}:
        # Return False to the caller.
        return False
    # Return any(k in raw for k in FINANCE_QUESTION_KEYWORDS) to the caller.
    return any(k in raw for k in FINANCE_QUESTION_KEYWORDS)


# Define route finance question mode for callers in this flow.
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


# Define deterministic audit text for callers in this flow.
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

    # Handle the missing or empty issues and not anomalies case.
    if not issues and not anomalies:
        # Return ( to the caller.
        return (
            "✅ Tidak ada anomali bulan ini.\n"
            "Data transaksi, kategori, rekening, dan format utama terlihat aman."
        # Close the structure that was opened above.
        )

    # Handle the case where issues.
    if issues:
        lines.append("\nMasalah kualitas data:")
        # Process each item in the current collection.
        for item in issues[:8]:
            lines.append(f"• {item.get('issue')}: {item.get('count')} transaksi")
            examples = item.get("examples") or []
            # Handle the case where examples.
            if examples:
                # Prepare example for the next step.
                example = examples[0]
                extra = ""
                if example.get("suggestion"):
                    extra = f" → kemungkinan maksudnya {example.get('suggestion')}"
                # Open a multi-line structure for the values below.
                lines.append(
                    f"  Contoh: {example.get('date') or '-'} — {example.get('description') or example.get('subject') or '-'} "
                    f"({example.get('amount_display') or '-'}){extra}"
                # Close the structure that was opened above.
                )

    # Handle the case where anomalies.
    if anomalies:
        lines.append("\nAnomali yang perlu dicek:")
        # Process each item in the current collection.
        for item in anomalies[:8]:
            if item.get("transaction"):
                txn = item["transaction"]
                # Open a multi-line structure for the values below.
                lines.append(
                    f"• {item.get('message')} — {txn.get('date')} {txn.get('description')} {format_rupiah(txn.get('amount', 0))}"
                # Close the structure that was opened above.
                )
            # Handle the fallback path after earlier conditions are skipped.
            else:
                lines.append(f"• {item.get('message')}")

    return "\n".join(lines)


# Define deterministic monthly text for callers in this flow.
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
    # Handle the case where cats.
    if cats:
        lines.append("\nDriver pengeluaran terbesar:")
        # Process each cat in the current collection.
        for cat in cats:
            # Open a multi-line structure for the values below.
            lines.append(
                f"• {cat.get('name')}: {format_rupiah(cat.get('amount', 0))} ({cat.get('contribution_pct', 0)}%)"
            # Close the structure that was opened above.
            )

    budgets = context.get("budget_status", [])[:3]
    # Handle the case where budgets.
    if budgets:
        lines.append("\nBudget yang perlu dipantau:")
        # Process each b in the current collection.
        for b in budgets:
            # Keep this section separated from the surrounding flow.
            lines.append(f"• {b.get('category')}: {b.get('usage_pct')}% terpakai")

    # Keep this section separated from the surrounding flow.
    return "\n".join(lines)
