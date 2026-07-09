"""Budget service for monthly budget setup, actual spending calculation, remaining budget, and budget history."""


# Import datetime so this module can use its helpers.
from datetime import datetime, date, timedelta
# Import re for this module's local operations.
import re

# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import (
    append_row_raw,
    get_all_records,
    update_cell,
)
# Import app.config so this module can use its helpers.
from app.config import SHEET_BUDGETS, SHEET_TRANSACTIONS


# ── Constants ─────────────────────────────────────────────────────────────────

DEBT_CASHFLOW_CATEGORIES = {
    "Piutang Diberikan",
    "Pembayaran Piutang",
    "Penerimaan Utang",
    "Bayar Utang",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

# Helper for get current month.
def get_current_month() -> str:
    """Retrieve data needed by the get current month workflow in the service layer.

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


# Helper for normalize month.
def normalize_month(month: str | None = None) -> str:
    """Normalize input values for the normalize month workflow in the service layer.

    Args:
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Validate missing month before continuing.
    if not month:
        return get_current_month()

    month = str(month).strip()
    month = month.replace("/", "-")
    month = re.sub(r"\s+", "-", month)

    match = re.fullmatch(r"(\d{4})-(\d{1,2})", month)
    # Validate missing match before continuing.
    if not match:
        raise ValueError("Format bulan harus YYYY-MM. Contoh: 2026-06")

    year = int(match.group(1))
    month_num = int(match.group(2))

    # Handle month num < 1 or month num > 12.
    if month_num < 1 or month_num > 12:
        raise ValueError("Bulan harus antara 1 sampai 12.")

    return f"{year}-{month_num:02d}"




# Helper for normalize sheet month value.
def normalize_sheet_month_value(value) -> str:
    """Normalize input values for the normalize sheet month value workflow in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%Y-%m")

    if isinstance(value, date):
        return value.strftime("%Y-%m")

    if isinstance(value, (int, float)):
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Google Sheets/Excel serial date origin.
            # Date parsing note: keep explicit and relative Indonesian date formats predictable.
            dt = datetime(1899, 12, 30) + timedelta(days=float(value))
            if 1990 <= dt.year <= 2100:
                return dt.strftime("%Y-%m")
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass
        return str(value).strip()

    # Prepare raw from the incoming input.
    raw = str(value).strip()
    # Validate missing raw before continuing.
    if not raw:
        return ""

    raw = raw.replace("/", "-")

    # 2026-06 atau 2026-6
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", raw)
    if match:
        return normalize_month(f"{match.group(1)}-{match.group(2)}")

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:\s+.*)?", raw)
    if match:
        return normalize_month(f"{match.group(1)}-{match.group(2)}")

    # If gspread mengembalikan display value seperti Jun 2026 / June 2026.
    for fmt in ("%b %Y", "%B %Y", "%Y %B", "%Y %b"):
        # Run this operation in a guarded block so failures can be handled.
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m")
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass

    return raw

# Helper for format month label.
def format_month_label(month: str) -> str:
    """Format data into a readable display for month label."""
    month = normalize_month(month)
    dt = datetime.strptime(month, "%Y-%m")
    return dt.strftime("%B %Y")


# Helper for format rupiah.
def format_rupiah(amount: float) -> str:
    """Format data into a readable display for rupiah."""
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")


# Helper for get budget status emoji.
def get_budget_status_emoji(pct_used: float) -> str:
    """Retrieve data needed by the get budget status emoji workflow in the service layer.

    Args:
        pct_used: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    if pct_used >= 100:
        return "🔴"
    # Fall back when pct used >= 80.
    elif pct_used >= 80:
        return "🟠"
    # Fall back when pct used >= 50.
    elif pct_used >= 50:
        return "🟡"
    # Use the fallback path when no earlier branch matched.
    else:
        return "🟢"


# Helper for generate budget id.
def generate_budget_id(month: str, category: str) -> str:
    """Coordinate the generate budget id logic in the service layer.

    Args:
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        category: Category name or category-like value from user input or sheet data.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    clean_category = re.sub(r"[^a-zA-Z0-9]+", "_", category.strip().lower())
    clean_category = clean_category.strip("_")
    return f"budget_{month}_{clean_category}"


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
    # Run this operation in a guarded block so failures can be handled.
    try:
        return float(value or 0)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return default


# ── Budget CRUD ───────────────────────────────────────────────────────────────

# Helper for set budget.
def set_budget(category: str, amount: float, month: str = None) -> dict:
    """Coordinate the set budget logic in the service layer.

    Args:
        category: Category name or category-like value from user input or sheet data.
        amount: Numeric amount or amount-like user input to parse or format.
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    month = normalize_month(month)
    # Extract amount for validation.
    amount = float(amount or 0)

    if amount <= 0:
        return {
            "success": False,
            "action": "failed",
            "message": "Nominal budget harus lebih dari 0.",
        }

    # Load records for the current calculation.
    records = get_all_records(SHEET_BUDGETS)
    today = datetime.now().strftime("%Y-%m-%d")

    # Iterate through each i, record.
    for i, record in enumerate(records):
        record_month = normalize_sheet_month_value(record.get("month", ""))
        record_category = str(record.get("category", "")).strip().lower()

        # Handle record month == month and record category == category.
        if record_month == month and record_category == category.strip().lower():
            row_index = i + 2

            # Header:
            # 1=id, 2=month, 3=category, 4=budget_amount, 5=created_at, 6=updated_at
            update_cell(SHEET_BUDGETS, row_index, 4, amount)
            update_cell(SHEET_BUDGETS, row_index, 6, today)

            return {
                "success": True,
                "action": "updated",
                "month": month,
                "category": category,
                "amount": amount,
                "message": f"Budget {category} untuk {month} diupdate ke {format_rupiah(amount)}",
            }

    budget_id = generate_budget_id(month, category)

    row = [
        budget_id,
        month,
        category,
        amount,
        today,
        today,
    ]

    append_row_raw(SHEET_BUDGETS, row)

    return {
        "success": True,
        "action": "created",
        "month": month,
        "category": category,
        "amount": amount,
        "message": f"Budget {category} untuk {month} diset {format_rupiah(amount)}",
    }


# Helper for get budget.
def get_budget(category: str, month: str = None) -> float | None:
    """Retrieve data needed by the get budget workflow in the service layer.

    Args:
        category: Category name or category-like value from user input or sheet data.
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `float | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    month = normalize_month(month)

    # Load records for the current calculation.
    records = get_all_records(SHEET_BUDGETS)

    # Iterate through each record.
    for record in records:
        record_month = normalize_sheet_month_value(record.get("month", ""))
        record_category = str(record.get("category", "")).strip().lower()

        # Handle record month == month and record category == category.
        if record_month == month and record_category == category.strip().lower():
            return safe_float(record.get("budget_amount", 0))

    return None


# Helper for get all budgets.
def get_all_budgets(month: str = None) -> list[dict]:
    """Retrieve data needed by the get all budgets workflow in the service layer.

    Args:
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    month = normalize_month(month)

    # Load records for the current calculation.
    records = get_all_records(SHEET_BUDGETS)
    return [
        r for r in records
        if normalize_sheet_month_value(r.get("month", "")) == month
    ]


# Helper for get budget months.
def get_budget_months() -> list[str]:
    """Retrieve data needed by the get budget months workflow in the service layer.

    Args:
        None.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Load records for the current calculation.
    records = get_all_records(SHEET_BUDGETS)
    months = sorted({
        normalize_sheet_month_value(r.get("month", ""))
        # Iterate through each r.
        for r in records
        if normalize_sheet_month_value(r.get("month", ""))
    })

    return months


# ── Realisasi vs Budget ───────────────────────────────────────────────────────

# Helper for budget transaction matches category.
def budget_transaction_matches_category(record: dict, category: str) -> bool:
    """Coordinate the budget transaction matches category logic in the service layer.

    Args:
        record: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        category: Category name or category-like value from user input or sheet data.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep category name, type, symbol, and alias behavior consistent with the documented category flow.
    """
    budget_key = str(category or "").strip().lower()
    # Validate missing budget key before continuing.
    if not budget_key:
        return False

    txn_category = str((record or {}).get("category", "")).strip().lower()
    if txn_category == budget_key:
        return True

    desc = str((record or {}).get("description", "") or "").lower()
    raw = str((record or {}).get("raw_input", "") or "").lower()
    return bool(budget_key and (budget_key in desc or budget_key in raw))


# Helper for calculate budget actual from transactions.
def calculate_budget_actual_from_transactions(transactions: list[dict]) -> dict:
    """Calculate derived values for budget actual from transactions."""
    gross_total = 0.0
    net_total = 0.0

    # Iterate through each txn.
    for txn in transactions or []:
        if str((txn or {}).get("type", "")).strip().lower() != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue

        amount = safe_float((txn or {}).get("amount", 0))
        receivable = safe_float((txn or {}).get("debt_receivable_original", (txn or {}).get("debt_receivable_remaining", 0)))
        gross_total += amount
        net_total += max(amount - receivable, 0.0)

    return {"net": net_total, "gross": gross_total}


# Helper for get actual expense breakdown.
def get_actual_expense_breakdown(category: str, month: str = None) -> dict:
    """Retrieve data needed by the get actual expense breakdown workflow in the service layer.

    Args:
        category: Category name or category-like value from user input or sheet data.
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    month = normalize_month(month)

    # Load records for the current calculation.
    records = get_all_records(SHEET_TRANSACTIONS)
    matched = []

    # Iterate through each record.
    for record in records:
        txn_type = str(record.get("type", "")).strip().lower()
        txn_date = str(record.get("date", "")).strip()

        if txn_type != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Validate missing txn date.startswith(month) before continuing.
        if not txn_date.startswith(month):
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Validate missing budget transaction matches category(record, category) before continuing.
        if not budget_transaction_matches_category(record, category):
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Append the current value to matched.
        matched.append(dict(record or {}))

    # Validate missing matched before continuing.
    if not matched:
        return {"net": 0.0, "gross": 0.0}

    from app.services.report_service import enrich_transactions_with_debt_info

    enriched = enrich_transactions_with_debt_info(matched)
    return calculate_budget_actual_from_transactions(enriched)


# Helper for get actual expense.
def get_actual_expense(category: str, month: str = None) -> float:
    """Retrieve data needed by the get actual expense workflow in the service layer.

    Args:
        category: Category name or category-like value from user input or sheet data.
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return get_actual_expense_breakdown(category, month).get("net", 0.0)


# Helper for get budget summary.
def get_budget_summary(month: str = None) -> list[dict]:
    """Retrieve data needed by the get budget summary workflow in the service layer.

    Args:
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    month = normalize_month(month)

    budgets = get_all_budgets(month)
    # Build result for the response flow.
    result = []

    # Load records for the current calculation.
    records = get_all_records(SHEET_TRANSACTIONS)
    monthly_expenses = []
    # Iterate through each record.
    for record in records:
        txn_type = str(record.get("type", "")).strip().lower()
        txn_date = str(record.get("date", "")).strip()
        if txn_type == "expense" and txn_date.startswith(month):
            # Append the current value to monthly expenses.
            monthly_expenses.append(dict(record or {}))

    if monthly_expenses:
        from app.services.report_service import enrich_transactions_with_debt_info
        monthly_expenses = enrich_transactions_with_debt_info(monthly_expenses)

    # Iterate through each b.
    for b in budgets:
        category = str(b.get("category", "")).strip()
        budget_amount = safe_float(b.get("budget_amount", 0))

        # Validate missing category before continuing.
        if not category:
            # Skip the rest of this loop iteration after handling this case.
            continue

        matched = [
            txn
            # Iterate through each txn.
            for txn in monthly_expenses
            if budget_transaction_matches_category(txn, category)
        ]
        actual_info = calculate_budget_actual_from_transactions(matched)
        actual = actual_info["net"]
        actual_gross = actual_info["gross"]
        remaining = budget_amount - actual
        pct_used = (actual / budget_amount * 100) if budget_amount > 0 else 0

        result.append({
            "month": month,
            "category": category,
            "budget": budget_amount,
            "actual": actual,
            "actual_gross": actual_gross,
            "remaining": remaining,
            "pct_used": round(pct_used, 1),
            "status": "over" if pct_used >= 100 else "warning" if pct_used >= 80 else "ok",
            "emoji": get_budget_status_emoji(pct_used),
        })

    result.sort(key=lambda x: x["pct_used"], reverse=True)
    return result


# Helper for check budget after transaction.
def check_budget_after_transaction(category: str, month: str = None) -> dict | None:
    """Validate conditions for the check budget after transaction workflow in the service layer.

    Args:
        category: Category name or category-like value from user input or sheet data.
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    month = normalize_month(month)

    if category in DEBT_CASHFLOW_CATEGORIES:
        return None

    budget = get_budget(category, month)
    if budget is None:
        return None

    actual = get_actual_expense(category, month)
    remaining = budget - actual
    pct_used = (actual / budget * 100) if budget > 0 else 0
    emoji = get_budget_status_emoji(pct_used)

    alert = False
    alert_msg = ""

    if pct_used >= 100:
        alert = True
        alert_msg = f"🔴 Budget {category} bulan {month} sudah terlampaui {format_rupiah(abs(remaining))}!"
    # Fall back when pct used >= 80.
    elif pct_used >= 80:
        alert = True
        alert_msg = f"🟠 Budget {category} bulan {month} tersisa {format_rupiah(remaining)} ({100 - pct_used:.0f}%)"

    return {
        "month": month,
        "category": category,
        "budget": budget,
        "actual": actual,
        "remaining": remaining,
        "pct_used": round(pct_used, 1),
        "emoji": emoji,
        "alert": alert,
        "alert_msg": alert_msg,
    }
