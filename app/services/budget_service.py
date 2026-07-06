"""Budget service for monthly budget setup, actual spending calculation, remaining budget, and budget history."""


# Import datetime so this module can use its helpers.
from datetime import datetime, date, timedelta
# Import re for this module's local operations.
import re

# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import (
    # Include this value in the surrounding collection or call.
    append_row_raw,
    # Include this value in the surrounding collection or call.
    get_all_records,
    # Include this value in the surrounding collection or call.
    update_cell,
# Close the structure that was opened above.
)
# Import app.config so this module can use its helpers.
from app.config import SHEET_BUDGETS, SHEET_TRANSACTIONS


# ── Constants ─────────────────────────────────────────────────────────────────

# Open a multi-line structure for the values below.
DEBT_CASHFLOW_CATEGORIES = {
    "Piutang Diberikan",
    "Pembayaran Piutang",
    "Penerimaan Utang",
    "Bayar Utang",
# Close the structure that was opened above.
}


# ── Helpers ───────────────────────────────────────────────────────────────────

# Define get current month for callers in this flow.
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


# Define normalize month for callers in this flow.
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
    # Handle the missing or empty month case.
    if not month:
        # Return get_current_month() to the caller.
        return get_current_month()

    # Prepare month for the next step.
    month = str(month).strip()
    month = month.replace("/", "-")
    month = re.sub(r"\s+", "-", month)

    match = re.fullmatch(r"(\d{4})-(\d{1,2})", month)
    # Handle the missing or empty match case.
    if not match:
        raise ValueError("Format bulan harus YYYY-MM. Contoh: 2026-06")

    # Prepare year for the next step.
    year = int(match.group(1))
    # Prepare month num for the next step.
    month_num = int(match.group(2))

    # Handle the case where month_num < 1 or month_num > 12.
    if month_num < 1 or month_num > 12:
        raise ValueError("Bulan harus antara 1 sampai 12.")

    return f"{year}-{month_num:02d}"




# Define normalize sheet month value for callers in this flow.
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
    # Handle the case where value is None.
    if value is None:
        return ""

    # Handle the case where isinstance(value, datetime).
    if isinstance(value, datetime):
        return value.strftime("%Y-%m")

    # Handle the case where isinstance(value, date).
    if isinstance(value, date):
        return value.strftime("%Y-%m")

    # Handle the case where isinstance(value, (int, float)).
    if isinstance(value, (int, float)):
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Google Sheets/Excel serial date origin.
            # Date parsing note: keep explicit and relative Indonesian date formats predictable.
            dt = datetime(1899, 12, 30) + timedelta(days=float(value))
            # Handle the case where 1990 <= dt.year <= 2100.
            if 1990 <= dt.year <= 2100:
                return dt.strftime("%Y-%m")
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass
        # Return str(value).strip() to the caller.
        return str(value).strip()

    # Prepare raw for the next step.
    raw = str(value).strip()
    # Handle the missing or empty raw case.
    if not raw:
        return ""

    raw = raw.replace("/", "-")

    # 2026-06 atau 2026-6
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", raw)
    # Handle the case where match.
    if match:
        return normalize_month(f"{match.group(1)}-{match.group(2)}")

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:\s+.*)?", raw)
    # Handle the case where match.
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

    # Return raw to the caller.
    return raw

# Define format month label for callers in this flow.
def format_month_label(month: str) -> str:
    """Format data into a readable display for month label."""
    # Prepare month for the next step.
    month = normalize_month(month)
    dt = datetime.strptime(month, "%Y-%m")
    return dt.strftime("%B %Y")


# Define format rupiah for callers in this flow.
def format_rupiah(amount: float) -> str:
    """Format data into a readable display for rupiah."""
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")


# Define get budget status emoji for callers in this flow.
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
    # Handle the case where pct_used >= 100.
    if pct_used >= 100:
        return "🔴"
    # Handle the alternate case where pct_used >= 80.
    elif pct_used >= 80:
        return "🟠"
    # Handle the alternate case where pct_used >= 50.
    elif pct_used >= 50:
        return "🟡"
    # Handle the fallback path after earlier conditions are skipped.
    else:
        return "🟢"


# Define generate budget id for callers in this flow.
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
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Return float(value or 0) to the caller.
        return float(value or 0)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return default to the caller.
        return default


# ── Budget CRUD ───────────────────────────────────────────────────────────────

# Define set budget for callers in this flow.
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
    # Prepare month for the next step.
    month = normalize_month(month)
    # Prepare amount for the next step.
    amount = float(amount or 0)

    # Handle the case where amount <= 0.
    if amount <= 0:
        # Return { to the caller.
        return {
            "success": False,
            "action": "failed",
            "message": "Nominal budget harus lebih dari 0.",
        # Close the structure that was opened above.
        }

    # Prepare records for the next step.
    records = get_all_records(SHEET_BUDGETS)
    today = datetime.now().strftime("%Y-%m-%d")

    # Process each i, record in the current collection.
    for i, record in enumerate(records):
        record_month = normalize_sheet_month_value(record.get("month", ""))
        record_category = str(record.get("category", "")).strip().lower()

        # Handle the case where record_month == month and record_category == category.strip()....
        if record_month == month and record_category == category.strip().lower():
            # Prepare row index for the next step.
            row_index = i + 2

            # Header:
            # 1=id, 2=month, 3=category, 4=budget_amount, 5=created_at, 6=updated_at
            update_cell(SHEET_BUDGETS, row_index, 4, amount)
            # Run this statement as part of the current workflow.
            update_cell(SHEET_BUDGETS, row_index, 6, today)

            # Return { to the caller.
            return {
                "success": True,
                "action": "updated",
                "month": month,
                "category": category,
                "amount": amount,
                "message": f"Budget {category} untuk {month} diupdate ke {format_rupiah(amount)}",
            # Close the structure that was opened above.
            }

    # Prepare budget id for the next step.
    budget_id = generate_budget_id(month, category)

    # Open a multi-line structure for the values below.
    row = [
        # Include this value in the surrounding collection or call.
        budget_id,
        # Include this value in the surrounding collection or call.
        month,
        # Include this value in the surrounding collection or call.
        category,
        # Include this value in the surrounding collection or call.
        amount,
        # Include this value in the surrounding collection or call.
        today,
        # Include this value in the surrounding collection or call.
        today,
    # Close the structure that was opened above.
    ]

    # Run this statement as part of the current workflow.
    append_row_raw(SHEET_BUDGETS, row)

    # Return { to the caller.
    return {
        "success": True,
        "action": "created",
        "month": month,
        "category": category,
        "amount": amount,
        "message": f"Budget {category} untuk {month} diset {format_rupiah(amount)}",
    # Close the structure that was opened above.
    }


# Define get budget for callers in this flow.
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
    # Prepare month for the next step.
    month = normalize_month(month)

    # Prepare records for the next step.
    records = get_all_records(SHEET_BUDGETS)

    # Process each record in the current collection.
    for record in records:
        record_month = normalize_sheet_month_value(record.get("month", ""))
        record_category = str(record.get("category", "")).strip().lower()

        # Handle the case where record_month == month and record_category == category.strip()....
        if record_month == month and record_category == category.strip().lower():
            return safe_float(record.get("budget_amount", 0))

    # Return None to the caller.
    return None


# Define get all budgets for callers in this flow.
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
    # Prepare month for the next step.
    month = normalize_month(month)

    # Prepare records for the next step.
    records = get_all_records(SHEET_BUDGETS)
    # Return [ to the caller.
    return [
        # Run this statement as part of the current workflow.
        r for r in records
        if normalize_sheet_month_value(r.get("month", "")) == month
    # Close the structure that was opened above.
    ]


# Define get budget months for callers in this flow.
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
    # Prepare records for the next step.
    records = get_all_records(SHEET_BUDGETS)
    # Open a multi-line structure for the values below.
    months = sorted({
        normalize_sheet_month_value(r.get("month", ""))
        # Process each r in the current collection.
        for r in records
        if normalize_sheet_month_value(r.get("month", ""))
    # Close the structure that was opened above.
    })

    # Return months to the caller.
    return months


# ── Realisasi vs Budget ───────────────────────────────────────────────────────

# Define budget transaction matches category for callers in this flow.
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
    # Handle the missing or empty budget_key case.
    if not budget_key:
        # Return False to the caller.
        return False

    txn_category = str((record or {}).get("category", "")).strip().lower()
    # Handle the case where txn_category == budget_key.
    if txn_category == budget_key:
        # Return True to the caller.
        return True

    desc = str((record or {}).get("description", "") or "").lower()
    raw = str((record or {}).get("raw_input", "") or "").lower()
    # Return bool(budget_key and (budget_key in desc or budget_key in raw)) to the caller.
    return bool(budget_key and (budget_key in desc or budget_key in raw))


# Define calculate budget actual from transactions for callers in this flow.
def calculate_budget_actual_from_transactions(transactions: list[dict]) -> dict:
    """Calculate derived values for budget actual from transactions."""
    # Prepare gross total for the next step.
    gross_total = 0.0
    # Prepare net total for the next step.
    net_total = 0.0

    # Process each txn in the current collection.
    for txn in transactions or []:
        if str((txn or {}).get("type", "")).strip().lower() != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue

        amount = safe_float((txn or {}).get("amount", 0))
        receivable = safe_float((txn or {}).get("debt_receivable_original", (txn or {}).get("debt_receivable_remaining", 0)))
        # Run this statement as part of the current workflow.
        gross_total += amount
        # Run this statement as part of the current workflow.
        net_total += max(amount - receivable, 0.0)

    return {"net": net_total, "gross": gross_total}


# Define get actual expense breakdown for callers in this flow.
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
    # Prepare month for the next step.
    month = normalize_month(month)

    # Prepare records for the next step.
    records = get_all_records(SHEET_TRANSACTIONS)
    # Prepare matched for the next step.
    matched = []

    # Process each record in the current collection.
    for record in records:
        txn_type = str(record.get("type", "")).strip().lower()
        txn_date = str(record.get("date", "")).strip()

        if txn_type != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the missing or empty txn_date.startswith(month) case.
        if not txn_date.startswith(month):
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the missing or empty budget_transaction_matches_category(record, category) case.
        if not budget_transaction_matches_category(record, category):
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Update matched with the current value.
        matched.append(dict(record or {}))

    # Handle the missing or empty matched case.
    if not matched:
        return {"net": 0.0, "gross": 0.0}

    # Natural input section
    from app.services.report_service import enrich_transactions_with_debt_info

    # Prepare enriched for the next step.
    enriched = enrich_transactions_with_debt_info(matched)
    # Return calculate_budget_actual_from_transactions(enriched) to the caller.
    return calculate_budget_actual_from_transactions(enriched)


# Define get actual expense for callers in this flow.
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


# Define get budget summary for callers in this flow.
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
    # Prepare month for the next step.
    month = normalize_month(month)

    # Prepare budgets for the next step.
    budgets = get_all_budgets(month)
    # Prepare result for the next step.
    result = []

    # Prepare records for the next step.
    records = get_all_records(SHEET_TRANSACTIONS)
    # Prepare monthly expenses for the next step.
    monthly_expenses = []
    # Process each record in the current collection.
    for record in records:
        txn_type = str(record.get("type", "")).strip().lower()
        txn_date = str(record.get("date", "")).strip()
        if txn_type == "expense" and txn_date.startswith(month):
            # Update monthly expenses with the current value.
            monthly_expenses.append(dict(record or {}))

    # Handle the case where monthly_expenses.
    if monthly_expenses:
        # Natural input section
        from app.services.report_service import enrich_transactions_with_debt_info
        # Prepare monthly expenses for the next step.
        monthly_expenses = enrich_transactions_with_debt_info(monthly_expenses)

    # Process each b in the current collection.
    for b in budgets:
        category = str(b.get("category", "")).strip()
        budget_amount = safe_float(b.get("budget_amount", 0))

        # Handle the missing or empty category case.
        if not category:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Open a multi-line structure for the values below.
        matched = [
            # Run this statement as part of the current workflow.
            txn
            # Process each txn in the current collection.
            for txn in monthly_expenses
            # Handle the case where budget_transaction_matches_category(txn, category).
            if budget_transaction_matches_category(txn, category)
        # Close the structure that was opened above.
        ]
        # Prepare actual info for the next step.
        actual_info = calculate_budget_actual_from_transactions(matched)
        actual = actual_info["net"]
        actual_gross = actual_info["gross"]
        # Prepare remaining for the next step.
        remaining = budget_amount - actual
        # Prepare pct used for the next step.
        pct_used = (actual / budget_amount * 100) if budget_amount > 0 else 0

        # Open a multi-line structure for the values below.
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
        # Close the structure that was opened above.
        })

    result.sort(key=lambda x: x["pct_used"], reverse=True)
    # Return result to the caller.
    return result


# Define check budget after transaction for callers in this flow.
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
    # Prepare month for the next step.
    month = normalize_month(month)

    # Handle the case where category in DEBT_CASHFLOW_CATEGORIES.
    if category in DEBT_CASHFLOW_CATEGORIES:
        # Return None to the caller.
        return None

    # Prepare budget for the next step.
    budget = get_budget(category, month)
    # Handle the case where budget is None.
    if budget is None:
        # Return None to the caller.
        return None

    # Prepare actual for the next step.
    actual = get_actual_expense(category, month)
    # Prepare remaining for the next step.
    remaining = budget - actual
    # Prepare pct used for the next step.
    pct_used = (actual / budget * 100) if budget > 0 else 0
    # Prepare emoji for the next step.
    emoji = get_budget_status_emoji(pct_used)

    # Prepare alert for the next step.
    alert = False
    alert_msg = ""

    # Handle the case where pct_used >= 100.
    if pct_used >= 100:
        # Prepare alert for the next step.
        alert = True
        alert_msg = f"🔴 Budget {category} bulan {month} sudah terlampaui {format_rupiah(abs(remaining))}!"
    # Handle the alternate case where pct_used >= 80.
    elif pct_used >= 80:
        # Prepare alert for the next step.
        alert = True
        alert_msg = f"🟠 Budget {category} bulan {month} tersisa {format_rupiah(remaining)} ({100 - pct_used:.0f}%)"

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }
