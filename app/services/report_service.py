"""Reporting service for daily, weekly, monthly, account-based, category-based, and search reports."""


# Import datetime so this module can use its helpers.
from datetime import datetime, timedelta
# Import re for this module's local operations.
import re

# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import get_all_records
# Import app.config so this module can use its helpers.
from app.config import SHEET_TRANSACTIONS, SHEET_DEBTS, SHEET_ACCOUNTS


# ── Helpers ───────────────────────────────────────────────────────────────────

# Define get transaction records for report for callers in this flow.
def get_transaction_records_for_report() -> list[dict]:
    """Retrieve data needed by the get transaction records for report workflow in the service layer.

    Args:
        None.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare records for the next step.
    records = get_all_records(SHEET_TRANSACTIONS)
    # Prepare result for the next step.
    result = []

    # Process each i, record in the current collection.
    for i, record in enumerate(records, start=2):
        # Prepare item for the next step.
        item = dict(record or {})
        item["_row_index"] = i
        # Update result with the current value.
        result.append(item)

    # Return result to the caller.
    return result


# Define format rupiah for callers in this flow.
def format_rupiah(amount: float) -> str:
    """Format data into a readable display for rupiah."""
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")


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

    # Format Indonesia umum: 10.000, 10,000, Rp10.000
    raw = raw.replace("Rp", "").replace("rp", "").strip()

    # Implementation section
    if "." in raw and "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    # Debt flow section
    elif "," in raw:
        parts = raw.split(",")
        # Handle the case where len(parts[-1]) == 2.
        if len(parts[-1]) == 2:
            raw = raw.replace(",", ".")
        # Handle the fallback path after earlier conditions are skipped.
        else:
            raw = raw.replace(",", "")
    # Split bill parsing note: separate the paid transaction from each person share.
    elif "." in raw:
        parts = raw.split(".")
        # Handle the case where len(parts) > 1 and all(len(p) == 3 for p in parts[1:]).
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
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



# Define normalize category key for callers in this flow.
def normalize_category_key(value: str | None) -> str:
    """Normalize input values for the normalize category key workflow in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep category name, type, symbol, and alias behavior consistent with the documented category flow.
    """
    raw = str(value or "").strip().lower()
    raw = raw.replace("&", " and ")
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


# Define normalize account key for callers in this flow.
def normalize_account_key(value: str | None) -> str:
    """Normalize input values for the normalize account key workflow in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    raw = str(value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


# Define get known report accounts for callers in this flow.
def get_known_report_accounts(records: list[dict] | None = None) -> list[str]:
    """Retrieve data needed by the get known report accounts workflow in the service layer.

    Args:
        records: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare accounts for the next step.
    accounts = []
    # Prepare seen for the next step.
    seen = set()

    # Define add for callers in this flow.
    def add(value):
        """Coordinate the add logic in the service layer.

        Args:
            value: Raw value supplied by the caller.

        Returns:
            `None` after completing the operation.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
        """
        value = str(value or "").strip()
        # Prepare key for the next step.
        key = normalize_account_key(value)
        # Handle the case where value and key and key not in seen.
        if value and key and key not in seen:
            # Update accounts with the current value.
            accounts.append(value)
            # Update seen with the current value.
            seen.add(key)

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Process each acc in the current collection.
        for acc in get_all_records(SHEET_ACCOUNTS):
            add((acc or {}).get("account_name"))
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass

    # Process each record in the current collection.
    for record in records or []:
        add((record or {}).get("account"))
        add((record or {}).get("to_account"))

    # Return accounts to the caller.
    return accounts


# Define resolve account filter for callers in this flow.
def resolve_account_filter(account_query: str | None, records: list[dict] | None = None) -> str | None:
    """Resolve a user input or reference for account filter."""
    query = str(account_query or "").strip()
    # Handle the missing or empty query case.
    if not query:
        # Return None to the caller.
        return None

    # Prepare query key for the next step.
    query_key = normalize_account_key(query)
    # Handle the missing or empty query_key case.
    if not query_key:
        # Return None to the caller.
        return None

    # Prepare accounts for the next step.
    accounts = get_known_report_accounts(records)
    # Prepare account by key for the next step.
    account_by_key = {normalize_account_key(acc): acc for acc in accounts}

    # Handle the case where query_key in account_by_key.
    if query_key in account_by_key:
        # Return account_by_key[query_key] to the caller.
        return account_by_key[query_key]

    # Open a multi-line structure for the values below.
    partial_matches = [
        # Run this statement as part of the current workflow.
        acc for acc in accounts
        # Handle the case where query_key in normalize_account_key(acc) or normalize_account_....
        if query_key in normalize_account_key(acc) or normalize_account_key(acc) in query_key
    # Close the structure that was opened above.
    ]
    # Handle the case where len(partial_matches) == 1.
    if len(partial_matches) == 1:
        # Return partial_matches[0] to the caller.
        return partial_matches[0]

    # Legacy compatibility note for older records or older in-memory state.
    return query


# Define is account match for callers in this flow.
def is_account_match(value: str | None, account_key: str | None) -> bool:
    """Check whether a condition is true for account match."""
    # Handle the missing or empty account_key case.
    if not account_key:
        # Return False to the caller.
        return False
    # Return normalize_account_key(value) == account_key to the caller.
    return normalize_account_key(value) == account_key


# Define is account transaction for callers in this flow.
def is_account_transaction(record: dict, account: str | None) -> bool:
    """Check whether a condition is true for account transaction."""
    # Prepare account key for the next step.
    account_key = normalize_account_key(account)
    # Handle the missing or empty account_key case.
    if not account_key:
        # Return True to the caller.
        return True

    txn_type = str((record or {}).get("type", "") or "").strip().lower()
    source_account = (record or {}).get("account")
    target_account = (record or {}).get("to_account")

    if txn_type == "transfer":
        # Return is_account_match(source_account, account_key) or is_account_m... to the caller.
        return is_account_match(source_account, account_key) or is_account_match(target_account, account_key)

    # Return is_account_match(source_account, account_key) to the caller.
    return is_account_match(source_account, account_key)


# Define split report filter args for callers in this flow.
def split_report_filter_args(value: str | None, mode: str) -> tuple[str | None, str | None, str | None]:
    """Coordinate the split report filter args logic in the service layer.

    Args:
        value: Raw value supplied by the caller.
        mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `tuple[str | None, str | None, str | None]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    raw = str(value or "").strip()
    # Handle the missing or empty raw case.
    if not raw:
        # Return None, None, None to the caller.
        return None, None, None

    # Prepare tokens for the next step.
    tokens = raw.split()
    markers = {"rekening", "akun", "account", "rek"}

    # Process each idx, token in the current collection.
    for idx, token in enumerate(tokens):
        # Prepare token key for the next step.
        token_key = normalize_account_key(token)
        # Handle the case where token_key not in markers.
        if token_key not in markers:
            # Skip the rest of this loop iteration after handling this case.
            continue

        before = " ".join(tokens[:idx]).strip()
        after = " ".join(tokens[idx + 1:]).strip()

        # Run this statement as part of the current workflow.
        period_arg, category_arg = split_report_period_and_category_arg(before, mode)
        # Run this statement as part of the current workflow.
        account_period_arg, account_arg = split_report_period_and_category_arg(after, mode)

        # Handle the missing or empty period_arg and account_period_arg case.
        if not period_arg and account_period_arg:
            # Prepare period arg for the next step.
            period_arg = account_period_arg

        # Prepare account arg for the next step.
        account_arg = account_arg if account_period_arg else after
        # Return period_arg, category_arg, (account_arg or None) to the caller.
        return period_arg, category_arg, (account_arg or None)

    # Run this statement as part of the current workflow.
    period_arg, category_arg = split_report_period_and_category_arg(raw, mode)
    # Return period_arg, category_arg, None to the caller.
    return period_arg, category_arg, None


# Define split account period arg for callers in this flow.
def split_account_period_arg(value: str | None) -> tuple[str | None, str]:
    """Coordinate the split account period arg logic in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `tuple[str | None, str]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    raw = str(value or "").strip()
    # Handle the missing or empty raw case.
    if not raw:
        return None, "month"

    # Prepare tokens for the next step.
    tokens = raw.split()
    # Prepare low tokens for the next step.
    low_tokens = [normalize_account_key(t) for t in tokens]

    for marker in ["rekening", "akun", "account", "rek"]:
        # Handle the case where low_tokens and low_tokens[0] == marker.
        if low_tokens and low_tokens[0] == marker:
            # Prepare tokens for the next step.
            tokens = tokens[1:]
            # Prepare low tokens for the next step.
            low_tokens = low_tokens[1:]
            raw = " ".join(tokens).strip()
            # Leave the loop after the target condition has been reached.
            break

    # Handle the missing or empty raw case.
    if not raw:
        return None, "month"

    if low_tokens and low_tokens[-1] in {"all", "semua", "histori", "history"}:
        return " ".join(tokens[:-1]).strip() or None, "all"

    period_arg, account_arg = split_report_period_and_category_arg(raw, "month")
    # Handle the case where period_arg.
    if period_arg:
        # Return account_arg, period_arg to the caller.
        return account_arg, period_arg

    return raw, "month"


# Open a multi-line structure for the values below.
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
    "Utang Tanpa Ubah Saldo",
    "Piutang Tanpa Cashflow",
    "Piutang Tanpa Ubah Saldo",
    "Pembayaran Debt Tanpa Cashflow",
    "Pembayaran Debt Tanpa Ubah Saldo",
    "Debt Tanpa Cashflow",
    "Debt Tanpa Ubah Saldo",
    "Kompensasi Hutang/Piutang",
# Close the structure that was opened above.
]

# Open a multi-line structure for the values below.
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
# Close the structure that was opened above.
}


# Define get known report categories for callers in this flow.
def get_known_report_categories(records: list[dict] | None = None) -> list[str]:
    """Retrieve data needed by the get known report categories workflow in the service layer.

    Args:
        records: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare categories for the next step.
    categories = []
    # Prepare seen for the next step.
    seen = set()

    # Define add for callers in this flow.
    def add(value):
        """Coordinate the add logic in the service layer.

        Args:
            value: Raw value supplied by the caller.

        Returns:
            `None` after completing the operation.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
        """
        value = str(value or "").strip()
        # Prepare key for the next step.
        key = normalize_category_key(value)
        # Handle the case where value and key and key not in seen.
        if value and key and key not in seen:
            # Update categories with the current value.
            categories.append(value)
            # Update seen with the current value.
            seen.add(key)

    # Process each cat in the current collection.
    for cat in DEFAULT_REPORT_CATEGORIES:
        # Run this statement as part of the current workflow.
        add(cat)

    # Process each record in the current collection.
    for record in records or []:
        add((record or {}).get("category"))

    # Return categories to the caller.
    return categories


# Define resolve category filter for callers in this flow.
def resolve_category_filter(category_query: str | None, records: list[dict] | None = None) -> str | None:
    """Resolve a user input or reference for category filter."""
    query = str(category_query or "").strip()
    # Handle the missing or empty query case.
    if not query:
        # Return None to the caller.
        return None

    # Prepare query key for the next step.
    query_key = normalize_category_key(query)
    # Handle the missing or empty query_key case.
    if not query_key:
        # Return None to the caller.
        return None

    # Prepare alias category for the next step.
    alias_category = CATEGORY_ALIASES.get(query_key)
    # Handle the case where alias_category.
    if alias_category:
        # Return alias_category to the caller.
        return alias_category

    # Prepare categories for the next step.
    categories = get_known_report_categories(records)
    # Prepare category by key for the next step.
    category_by_key = {normalize_category_key(cat): cat for cat in categories}

    # Handle the case where query_key in category_by_key.
    if query_key in category_by_key:
        # Return category_by_key[query_key] to the caller.
        return category_by_key[query_key]

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    partial_matches = [
        # Run this statement as part of the current workflow.
        cat for cat in categories
        # Handle the case where query_key in normalize_category_key(cat) or normalize_categor....
        if query_key in normalize_category_key(cat) or normalize_category_key(cat) in query_key
    # Close the structure that was opened above.
    ]
    # Handle the case where len(partial_matches) == 1.
    if len(partial_matches) == 1:
        # Return partial_matches[0] to the caller.
        return partial_matches[0]

    # Legacy compatibility note for older records or older in-memory state.
    return query


# Define split report period and category arg for callers in this flow.
def split_report_period_and_category_arg(value: str | None, mode: str) -> tuple[str | None, str | None]:
    """Coordinate the split report period and category arg logic in the service layer.

    Args:
        value: Raw value supplied by the caller.
        mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `tuple[str | None, str | None]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep category name, type, symbol, and alias behavior consistent with the documented category flow.
    """
    raw = str(value or "").strip()
    # Handle the missing or empty raw case.
    if not raw:
        # Return None, None to the caller.
        return None, None

    parser = parse_report_month_arg if mode == "month" else parse_report_date_arg
    # Prepare tokens for the next step.
    tokens = raw.split()
    # Prepare max prefix for the next step.
    max_prefix = min(len(tokens), 3)

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    for n in range(max_prefix, 0, -1):
        candidate = " ".join(tokens[:n]).strip()
        rest = " ".join(tokens[n:]).strip() or None
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Run this statement as part of the current workflow.
            parser(candidate)
            # Return candidate, rest to the caller.
            return candidate, rest
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    for n in range(max_prefix, 0, -1):
        candidate = " ".join(tokens[-n:]).strip()
        rest = " ".join(tokens[:-n]).strip() or None
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Run this statement as part of the current workflow.
            parser(candidate)
            # Return candidate, rest to the caller.
            return candidate, rest
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass

    # Return None, raw to the caller.
    return None, raw


# Define is truthy sheet value for callers in this flow.
def is_truthy_sheet_value(value) -> bool:
    """Check whether a condition is true for truthy sheet value."""
    raw = str(value or "").strip().lower()
    return raw in {"true", "yes", "y", "1", "settled", "lunas", "void", "voided"}


# Define is voided debt record for callers in this flow.
def is_voided_debt_record(debt: dict) -> bool:
    """Check whether a condition is true for voided debt record."""
    description = str((debt or {}).get("description", "") or "")
    return "[VOID" in description.upper()


# Define parse transaction debt ids from record for callers in this flow.
def parse_transaction_debt_ids_from_record(txn: dict) -> list[str]:
    """Parse caller input for the parse transaction debt ids from record workflow in the service layer.

    Args:
        txn: Transaction dict or transaction-like row from the finance data layer.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    raw = str((txn or {}).get("hutang_id", "") or "").strip()
    # Handle the missing or empty raw case.
    if not raw:
        # Return [] to the caller.
        return []
    return [part.strip() for part in re.split(r"[,;\s]+", raw) if part.strip()]


# Define build debt lookup for callers in this flow.
def build_debt_lookup(active_only: bool = True) -> dict:
    """Build the data structure or message text for debt lookup."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare records for the next step.
        records = get_all_records(SHEET_DEBTS)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Prepare records for the next step.
        records = []

    # Prepare by id for the next step.
    by_id = {}
    # Prepare by source txn for the next step.
    by_source_txn = {}

    # Process each debt in the current collection.
    for debt in records:
        # Prepare item for the next step.
        item = dict(debt or {})
        debt_id = str(item.get("id", "") or "").strip()
        # Handle the missing or empty debt_id case.
        if not debt_id:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Handle the case where is_voided_debt_record(item).
        if is_voided_debt_record(item):
            # Skip the rest of this loop iteration after handling this case.
            continue

        settled = is_truthy_sheet_value(item.get("is_settled", "FALSE"))
        remaining = safe_float(item.get("remaining_amount", 0))
        # Handle the case where active_only and (settled or remaining <= 0).
        if active_only and (settled or remaining <= 0):
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Run this statement as part of the current workflow.
        by_id[debt_id] = item

        source_txn_id = str(item.get("source_transaction_id", "") or "").strip()
        # Handle the case where source_txn_id.
        if source_txn_id:
            # Run this statement as part of the current workflow.
            by_source_txn.setdefault(source_txn_id, []).append(item)

    return {"by_id": by_id, "by_source_txn": by_source_txn}


# Define get linked debts for transaction for callers in this flow.
def get_linked_debts_for_transaction(txn: dict, lookup: dict) -> list[dict]:
    """Retrieve data needed by the get linked debts for transaction workflow in the service layer.

    Args:
        txn: Transaction dict or transaction-like row from the finance data layer.
        lookup: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    by_id = (lookup or {}).get("by_id", {}) or {}
    by_source_txn = (lookup or {}).get("by_source_txn", {}) or {}

    # Prepare linked for the next step.
    linked = []
    # Prepare seen for the next step.
    seen = set()

    # Process each debt_id in the current collection.
    for debt_id in parse_transaction_debt_ids_from_record(txn):
        # Prepare debt for the next step.
        debt = by_id.get(debt_id)
        # Handle the case where debt and debt_id not in seen.
        if debt and debt_id not in seen:
            # Update linked with the current value.
            linked.append(debt)
            # Update seen with the current value.
            seen.add(debt_id)

    txn_id = str((txn or {}).get("id", "") or "").strip()
    # Process each debt in the current collection.
    for debt in by_source_txn.get(txn_id, []) or []:
        debt_id = str(debt.get("id", "") or "").strip()
        # Handle the case where debt_id and debt_id not in seen.
        if debt_id and debt_id not in seen:
            # Update linked with the current value.
            linked.append(debt)
            # Update seen with the current value.
            seen.add(debt_id)

    # Return linked to the caller.
    return linked


# Define enrich transactions with debt info for callers in this flow.
def enrich_transactions_with_debt_info(transactions: list[dict]) -> list[dict]:
    """Coordinate the enrich transactions with debt info logic in the service layer.

    Args:
        transactions: List of transaction dicts or transaction-like rows.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Prepare lookup for the next step.
    lookup = build_debt_lookup(active_only=False)
    # Prepare enriched for the next step.
    enriched = []

    # Process each txn in the current collection.
    for txn in transactions or []:
        # Prepare item for the next step.
        item = dict(txn or {})
        # Prepare linked debts for the next step.
        linked_debts = get_linked_debts_for_transaction(item, lookup)

        # Prepare receivable remaining for the next step.
        receivable_remaining = 0.0
        # Prepare payable remaining for the next step.
        payable_remaining = 0.0
        # Prepare receivable original for the next step.
        receivable_original = 0.0
        # Prepare payable original for the next step.
        payable_original = 0.0
        # Prepare people for the next step.
        people = []
        # Prepare receivable by person for the next step.
        receivable_by_person = {}
        # Prepare payable by person for the next step.
        payable_by_person = {}
        # Prepare receivable original by person for the next step.
        receivable_original_by_person = {}
        # Prepare payable original by person for the next step.
        payable_original_by_person = {}

        # Process each debt in the current collection.
        for debt in linked_debts:
            remaining_amount = safe_float(debt.get("remaining_amount", 0))
            original_amount = safe_float(debt.get("original_amount", remaining_amount))
            debt_type = str(debt.get("type", "") or "").strip().lower()
            person = str(debt.get("person_name", "") or "").strip() or "Tanpa nama"
            # Handle the case where person and person not in people.
            if person and person not in people:
                # Update people with the current value.
                people.append(person)

            if debt_type == "receivable":
                # Run this statement as part of the current workflow.
                receivable_remaining += remaining_amount
                # Run this statement as part of the current workflow.
                receivable_original += original_amount
                # Handle the case where remaining_amount > 0.
                if remaining_amount > 0:
                    # Run this statement as part of the current workflow.
                    receivable_by_person[person] = receivable_by_person.get(person, 0.0) + remaining_amount
                # Handle the case where original_amount > 0.
                if original_amount > 0:
                    # Run this statement as part of the current workflow.
                    receivable_original_by_person[person] = receivable_original_by_person.get(person, 0.0) + original_amount
            elif debt_type == "payable":
                # Run this statement as part of the current workflow.
                payable_remaining += remaining_amount
                # Run this statement as part of the current workflow.
                payable_original += original_amount
                # Handle the case where remaining_amount > 0.
                if remaining_amount > 0:
                    # Run this statement as part of the current workflow.
                    payable_by_person[person] = payable_by_person.get(person, 0.0) + remaining_amount
                # Handle the case where original_amount > 0.
                if original_amount > 0:
                    # Run this statement as part of the current workflow.
                    payable_original_by_person[person] = payable_original_by_person.get(person, 0.0) + original_amount

        expense_amount = safe_float(item.get("amount", 0))
        item["linked_debts"] = linked_debts
        item["debt_receivable_remaining"] = receivable_remaining
        item["debt_payable_remaining"] = payable_remaining
        item["debt_receivable_original"] = receivable_original
        item["debt_payable_original"] = payable_original
        item["debt_people"] = people
        item["debt_receivable_parts"] = [
            {"person_name": person, "remaining_amount": amount}
            # Process each person, amount in the current collection.
            for person, amount in receivable_by_person.items()
            # Handle the case where amount > 0.
            if amount > 0
        # Close the structure that was opened above.
        ]
        item["debt_payable_parts"] = [
            {"person_name": person, "remaining_amount": amount}
            # Process each person, amount in the current collection.
            for person, amount in payable_by_person.items()
            # Handle the case where amount > 0.
            if amount > 0
        # Close the structure that was opened above.
        ]
        item["debt_receivable_original_parts"] = [
            {"person_name": person, "original_amount": amount}
            # Process each person, amount in the current collection.
            for person, amount in receivable_original_by_person.items()
            # Handle the case where amount > 0.
            if amount > 0
        # Close the structure that was opened above.
        ]
        item["debt_payable_original_parts"] = [
            {"person_name": person, "original_amount": amount}
            # Process each person, amount in the current collection.
            for person, amount in payable_original_by_person.items()
            # Handle the case where amount > 0.
            if amount > 0
        # Close the structure that was opened above.
        ]
        item["net_expense_after_receivable"] = max(expense_amount - receivable_original, 0.0)
        # Update enriched with the current value.
        enriched.append(item)

    # Return enriched to the caller.
    return enriched


# Define get effective expense amount for callers in this flow.
def get_effective_expense_amount(txn: dict) -> float:
    """Return the net expense amount after linked receivable shares.

    Args:
        txn: Transaction row. For expense rows, this may already include
            `net_expense_after_receivable` from `enrich_transactions_with_debt_info`.

    Returns:
        Net expense for report calculations. Non-expense rows return their raw
        amount so callers can safely reuse the helper in mixed sorting.
    """
    amount = safe_float((txn or {}).get("amount", 0))
    if str((txn or {}).get("type", "") or "").strip().lower() != "expense":
        # Return amount to the caller.
        return amount

    if "net_expense_after_receivable" in (txn or {}):
        return max(safe_float((txn or {}).get("net_expense_after_receivable", amount)), 0.0)

    # Open a multi-line structure for the values below.
    receivable = safe_float(
        (txn or {}).get("debt_receivable_original", (txn or {}).get("debt_receivable_remaining", 0))
    # Close the structure that was opened above.
    )
    # Return max(amount - receivable, 0.0) to the caller.
    return max(amount - receivable, 0.0)


# Define calculate net expense after receivable for callers in this flow.
def calculate_net_expense_after_receivable(transactions: list[dict]) -> float:
    """Calculate total net expense after linked receivable shares.

    Args:
        transactions: Enriched or raw transaction rows.

    Returns:
        Sum of expense amounts after subtracting receivable portions created by
        split bill or talangan flows.
    """
    # Prepare total for the next step.
    total = 0.0
    # Process each txn in the current collection.
    for txn in transactions or []:
        txn_type = str((txn or {}).get("type", "") or "").strip().lower()
        if txn_type != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Run this statement as part of the current workflow.
        total += get_effective_expense_amount(txn)
    # Return total to the caller.
    return total


# Define calculate net expense by category for callers in this flow.
def calculate_net_expense_by_category(transactions: list[dict]) -> dict:
    """Calculate net expense totals grouped by category.

    Args:
        transactions: Enriched or raw transaction rows.

    Returns:
        Category totals sorted descending by net expense.
    """
    # Prepare result for the next step.
    result = {}
    # Process each txn in the current collection.
    for txn in transactions or []:
        txn_type = str((txn or {}).get("type", "") or "").strip().lower()
        if txn_type != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue
        category = str((txn or {}).get("category") or "Other").strip() or "Other"
        # Run this statement as part of the current workflow.
        result[category] = result.get(category, 0.0) + get_effective_expense_amount(txn)
    # Return dict(sorted(result.items(), key=lambda x: x[1], reverse=True)) to the caller.
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


# Define attach enriched transactions for callers in this flow.
def attach_enriched_transactions(summary: dict, transactions: list[dict], account: str | None = None) -> dict:
    """Attach enriched transactions and refresh net-based summary fields.

    Args:
        summary: Existing report summary dict.
        transactions: Raw or enriched transaction rows for the same report.
        account: Optional account filter used for account-level net movement.

    Returns:
        The same summary dict with transactions attached and expense totals
        normalized to net-after-receivable basis.
    """
    # Prepare enriched for the next step.
    enriched = enrich_transactions_with_debt_info(transactions)
    # Prepare refreshed for the next step.
    refreshed = summarize(enriched, account)
    # Process each key in the current collection.
    for key in [
        "total_income",
        "total_expense",
        "total_gross_expense",
        "total_transfer",
        "total_transfer_in",
        "total_transfer_out",
        "net",
        "by_category",
        "by_category_gross",
        "count",
    # Close the structure that was opened above.
    ]:
        # Run this statement as part of the current workflow.
        summary[key] = refreshed.get(key, summary.get(key))
    summary["transactions"] = enriched
    summary["total_net_expense_after_receivable"] = summary.get("total_expense", 0)
    summary["by_category_net"] = summary.get("by_category", {})
    # Return summary to the caller.
    return summary


# Define build delta info for callers in this flow.
def build_delta_info(current_value, previous_value, previous_available: bool = True) -> dict:
    """Build the data structure or message text for delta info."""
    # Prepare cur for the next step.
    cur = safe_float(current_value, 0)

    # Handle the missing or empty previous_available case.
    if not previous_available:
        # Return { to the caller.
        return {
            "current": cur,
            "previous": None,
            "delta": None,
            "pct": None,
            "available": False,
        # Close the structure that was opened above.
        }

    # Prepare prev for the next step.
    prev = safe_float(previous_value, 0)
    # Prepare delta for the next step.
    delta = cur - prev
    # Prepare pct for the next step.
    pct = (delta / prev * 100) if prev else None

    # Return { to the caller.
    return {
        "current": cur,
        "previous": prev,
        "delta": delta,
        "pct": pct,
        "available": True,
    # Close the structure that was opened above.
    }


# Define build summary comparison for callers in this flow.
def build_summary_comparison(current: dict, previous: dict, previous_available: bool = True) -> dict:
    """Build the data structure or message text for summary comparison."""
    # Prepare current for the next step.
    current = current or {}
    # Prepare previous for the next step.
    previous = previous or {}
    keys = ["total_income", "total_expense", "net", "count"]

    # Return { to the caller.
    return {
        # Run this statement as part of the current workflow.
        key: build_delta_info(current.get(key, 0), previous.get(key, 0), previous_available)
        # Process each key in the current collection.
        for key in keys
    # Close the structure that was opened above.
    }


# Define build category comparison for callers in this flow.
def build_category_comparison(current: dict, previous: dict, previous_available: bool = True) -> dict:
    """Build the data structure or message text for category comparison."""
    # Prepare current for the next step.
    current = current or {}
    # Prepare previous for the next step.
    previous = previous or {}
    # Prepare previous keys for the next step.
    previous_keys = {normalize_category_key(cat): cat for cat in previous.keys()}
    # Prepare result for the next step.
    result = {}

    # Process each category, current_amount in the current collection.
    for category, current_amount in current.items():
        # Prepare category key for the next step.
        category_key = normalize_category_key(category)
        # Prepare has previous category for the next step.
        has_previous_category = previous_available and category_key in previous_keys
        # Prepare previous category for the next step.
        previous_category = previous_keys.get(category_key)
        # Prepare previous amount for the next step.
        previous_amount = previous.get(previous_category, 0) if previous_category else 0

        # Open a multi-line structure for the values below.
        result[category] = build_delta_info(
            # Include this value in the surrounding collection or call.
            current_amount,
            # Include this value in the surrounding collection or call.
            previous_amount,
            # Prepare previous available for the next step.
            previous_available=has_previous_category,
        # Close the structure that was opened above.
        )

    # Return result to the caller.
    return result

# Define parse report date arg for callers in this flow.
def parse_report_date_arg(value: str | None = None) -> str:
    """Parse caller input for the parse report date arg workflow in the service layer.

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
    today = datetime.now().date()

    # Handle the missing or empty value case.
    if not value:
        return today.strftime("%Y-%m-%d")

    # Prepare raw for the next step.
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
    # Handle the case where m.
    if m:
        # Prepare dt for the next step.
        dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
        return dt.strftime("%Y-%m-%d")

    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(20\d{2})", raw)
    # Handle the case where m.
    if m:
        # Prepare dt for the next step.
        dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date()
        return dt.strftime("%Y-%m-%d")

    if re.fullmatch(r"\d{1,2}", raw):
        # Prepare day for the next step.
        day = int(raw)
        # Prepare dt for the next step.
        dt = datetime(today.year, today.month, day).date()
        return dt.strftime("%Y-%m-%d")

    raise ValueError("Format tanggal tidak dikenali. Contoh: 2026-06-01, 01-06-2026, atau 1.")


# Define parse report month arg for callers in this flow.
def parse_report_month_arg(value: str | None = None) -> tuple[int, int]:
    """Parse caller input for the parse report month arg workflow in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `tuple[int, int]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare today for the next step.
    today = datetime.now().date()

    # Handle the missing or empty value case.
    if not value:
        # Return today.year, today.month to the caller.
        return today.year, today.month

    raw = str(value).strip().lower().replace("/", "-")

    if raw in ["month", "bulan", "bulanan", "bulanini", "bulan ini", "this month", "current month"]:
        # Return today.year, today.month to the caller.
        return today.year, today.month

    if raw in ["last month", "bulan lalu", "bulanlalu", "bln lalu", "blnlalu", "month lalu"]:
        # Prepare first this month for the next step.
        first_this_month = datetime(today.year, today.month, 1).date()
        # Prepare last month date for the next step.
        last_month_date = first_this_month - timedelta(days=1)
        # Return last_month_date.year, last_month_date.month to the caller.
        return last_month_date.year, last_month_date.month

    if raw in ["next month", "bulan depan", "bulandepan", "bln depan", "blndepan"]:
        # Handle the case where today.month == 12.
        if today.month == 12:
            # Return today.year + 1, 1 to the caller.
            return today.year + 1, 1
        # Return today.year, today.month + 1 to the caller.
        return today.year, today.month + 1

    m = re.fullmatch(r"(20\d{2})-(\d{1,2})", raw)
    # Handle the case where m.
    if m:
        # Prepare year for the next step.
        year = int(m.group(1))
        # Prepare month for the next step.
        month = int(m.group(2))
        # Handle the missing or empty 1 <= month <= 12 case.
        if not 1 <= month <= 12:
            raise ValueError("Bulan harus antara 1 sampai 12.")
        # Return year, month to the caller.
        return year, month

    m = re.fullmatch(r"(\d{1,2})-(20\d{2})", raw)
    # Handle the case where m.
    if m:
        # Prepare month for the next step.
        month = int(m.group(1))
        # Prepare year for the next step.
        year = int(m.group(2))
        # Handle the missing or empty 1 <= month <= 12 case.
        if not 1 <= month <= 12:
            raise ValueError("Bulan harus antara 1 sampai 12.")
        # Return year, month to the caller.
        return year, month

    if re.fullmatch(r"\d{1,2}", raw):
        # Prepare month for the next step.
        month = int(raw)
        # Handle the missing or empty 1 <= month <= 12 case.
        if not 1 <= month <= 12:
            raise ValueError("Bulan harus antara 1 sampai 12.")
        # Return today.year, month to the caller.
        return today.year, month

    raise ValueError("Format bulan tidak dikenali. Contoh: 2026-06 atau 6.")


# Define get week range for callers in this flow.
def get_week_range(reference_date: str | None = None) -> tuple[str, str]:
    """Retrieve data needed by the get week range workflow in the service layer.

    Args:
        reference_date: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `tuple[str, str]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    base_date = datetime.strptime(parse_report_date_arg(reference_date), "%Y-%m-%d").date()
    # Prepare monday for the next step.
    monday = base_date - timedelta(days=base_date.weekday())
    # Prepare sunday for the next step.
    sunday = monday + timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


# Define get month range for callers in this flow.
def get_month_range(year: int | None = None, month: int | None = None) -> tuple[str, str]:
    """Retrieve data needed by the get month range workflow in the service layer.

    Args:
        year: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `tuple[str, str]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare now for the next step.
    now = datetime.now()
    # Prepare year for the next step.
    year = int(year or now.year)
    # Prepare month for the next step.
    month = int(month or now.month)

    # Handle the missing or empty 1 <= month <= 12 case.
    if not 1 <= month <= 12:
        raise ValueError("Bulan harus antara 1 sampai 12.")

    # Prepare first dt for the next step.
    first_dt = datetime(year, month, 1)
    # Handle the case where month == 12.
    if month == 12:
        # Prepare next month for the next step.
        next_month = datetime(year + 1, 1, 1)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare next month for the next step.
        next_month = datetime(year, month + 1, 1)

    # Prepare last dt for the next step.
    last_dt = next_month - timedelta(days=1)
    return first_dt.strftime("%Y-%m-%d"), last_dt.strftime("%Y-%m-%d")


# Define filter transactions for callers in this flow.
def filter_transactions(
    # Include this value in the surrounding collection or call.
    records: list[dict],
    # Include this value in the surrounding collection or call.
    date_from: str | None = None,
    # Include this value in the surrounding collection or call.
    date_to: str | None = None,
    # Include this value in the surrounding collection or call.
    txn_type: str | None = None,
    # Include this value in the surrounding collection or call.
    category: str | None = None,
    # Include this value in the surrounding collection or call.
    account: str | None = None,
# Close the structure that was opened above.
) -> list[dict]:
    """Coordinate the filter transactions logic in the service layer.

    Args:
        records: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        date_from: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        date_to: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        txn_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        category: Category name or category-like value from user input or sheet data.
        account: Account name or account-like value from user input or sheet data.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare result for the next step.
    result = []
    # Prepare category key for the next step.
    category_key = normalize_category_key(category) if category else None
    account_filter = str(account or "").strip() or None

    # Process each r in the current collection.
    for r in records:
        date = str(r.get("date", "")).strip()
        record_type = str(r.get("type", "")).strip().lower()
        record_category_key = normalize_category_key(r.get("category"))

        # Handle the missing or empty date case.
        if not date:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the case where date_from and date < date_from.
        if date_from and date < date_from:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the case where date_to and date > date_to.
        if date_to and date > date_to:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the case where txn_type and record_type != str(txn_type).strip().lower().
        if txn_type and record_type != str(txn_type).strip().lower():
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the case where category_key and record_category_key != category_key.
        if category_key and record_category_key != category_key:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the case where account_filter and not is_account_transaction(r, account_filter).
        if account_filter and not is_account_transaction(r, account_filter):
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Update result with the current value.
        result.append(r)

    # Return result to the caller.
    return result


# Define summarize for callers in this flow.
def summarize(transactions: list[dict], account: str | None = None) -> dict:
    """Summarize transactions for report totals on a net expense basis.

    Args:
        transactions: Transaction rows, preferably enriched with debt metadata.
            Raw rows still work, but split-bill receivable subtraction only
            happens when debt metadata is available.
        account: Optional account filter. When provided, transfers are treated
            as account inflow/outflow and net becomes account movement.

    Returns:
        Summary dict where `total_expense` and `by_category` are net after
        receivables, while `total_gross_expense` and `by_category_gross` keep
        the original gross values for display as `Net (Gross)`.
    """
    # Prepare account key for the next step.
    account_key = normalize_account_key(account) if account else None
    # Prepare total income for the next step.
    total_income = 0.0
    # Prepare total expense for the next step.
    total_expense = 0.0
    # Prepare total gross expense for the next step.
    total_gross_expense = 0.0
    # Prepare total transfer for the next step.
    total_transfer = 0.0
    # Prepare total transfer in for the next step.
    total_transfer_in = 0.0
    # Prepare total transfer out for the next step.
    total_transfer_out = 0.0
    # Prepare by category for the next step.
    by_category = {}
    # Prepare by category gross for the next step.
    by_category_gross = {}

    # Process each t in the current collection.
    for t in transactions:
        amount = safe_float(t.get("amount", 0))
        txn_type = str(t.get("type", "")).strip().lower()
        category = str(t.get("category") or "Other").strip() or "Other"
        source_match = is_account_match(t.get("account"), account_key) if account_key else True
        target_match = is_account_match(t.get("to_account"), account_key) if account_key else False

        if txn_type == "income":
            # Handle the case where source_match.
            if source_match:
                # Run this statement as part of the current workflow.
                total_income += amount
        elif txn_type == "expense":
            # Handle the case where source_match.
            if source_match:
                # Prepare net amount for the next step.
                net_amount = get_effective_expense_amount(t)
                # Run this statement as part of the current workflow.
                total_expense += net_amount
                # Run this statement as part of the current workflow.
                total_gross_expense += amount
                # Run this statement as part of the current workflow.
                by_category[category] = by_category.get(category, 0.0) + net_amount
                # Run this statement as part of the current workflow.
                by_category_gross[category] = by_category_gross.get(category, 0.0) + amount
        elif txn_type == "transfer":
            # Handle the case where account_key.
            if account_key:
                # Handle the case where source_match.
                if source_match:
                    # Run this statement as part of the current workflow.
                    total_transfer_out += amount
                # Handle the case where target_match.
                if target_match:
                    # Run this statement as part of the current workflow.
                    total_transfer_in += amount
                # Handle the case where source_match or target_match.
                if source_match or target_match:
                    # Run this statement as part of the current workflow.
                    total_transfer += amount
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Run this statement as part of the current workflow.
                total_transfer += amount

    # Handle the case where account_key.
    if account_key:
        # Prepare net for the next step.
        net = total_income + total_transfer_in - total_expense - total_transfer_out
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare net for the next step.
        net = total_income - total_expense

    # Return { to the caller.
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "total_gross_expense": total_gross_expense,
        "total_transfer": total_transfer,
        "total_transfer_in": total_transfer_in,
        "total_transfer_out": total_transfer_out,
        "net": net,
        "by_category": dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True)),
        "by_category_gross": dict(sorted(by_category_gross.items(), key=lambda x: x[1], reverse=True)),
        "count": len(transactions),
    # Close the structure that was opened above.
    }


# ── Report functions ──────────────────────────────────────────────────────────

# Define get daily report for callers in this flow.
def get_daily_report(date_str: str | None = None, category: str | None = None, account: str | None = None) -> dict:
    """Retrieve data needed by the get daily report workflow in the service layer.

    Args:
        date_str: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        category: Category name or category-like value from user input or sheet data.
        account: Account name or account-like value from user input or sheet data.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare date str for the next step.
    date_str = parse_report_date_arg(date_str)
    current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    # Prepare previous date for the next step.
    previous_date = current_date - timedelta(days=1)
    previous_date_str = previous_date.strftime("%Y-%m-%d")

    # Prepare records for the next step.
    records = get_transaction_records_for_report()
    # Prepare category filter for the next step.
    category_filter = resolve_category_filter(category, records)
    # Prepare account filter for the next step.
    account_filter = resolve_account_filter(account, records)
    # Open a multi-line structure for the values below.
    transactions = filter_transactions(
        # Include this value in the surrounding collection or call.
        records,
        # Prepare date from for the next step.
        date_from=date_str,
        # Prepare date to for the next step.
        date_to=date_str,
        # Prepare category for the next step.
        category=category_filter,
        # Prepare account for the next step.
        account=account_filter,
    # Close the structure that was opened above.
    )
    transactions.sort(key=lambda x: int(x.get("_row_index", 0) or 0), reverse=True)

    # Open a multi-line structure for the values below.
    previous_transactions = filter_transactions(
        # Include this value in the surrounding collection or call.
        records,
        # Prepare date from for the next step.
        date_from=previous_date_str,
        # Prepare date to for the next step.
        date_to=previous_date_str,
        # Prepare category for the next step.
        category=category_filter,
        # Prepare account for the next step.
        account=account_filter,
    # Close the structure that was opened above.
    )
    # Prepare previous transactions for the next step.
    previous_transactions = enrich_transactions_with_debt_info(previous_transactions)
    # Prepare previous summary for the next step.
    previous_summary = summarize(previous_transactions, account_filter)
    # Prepare previous available for the next step.
    previous_available = len(previous_transactions) > 0

    # Prepare transactions for the next step.
    transactions = enrich_transactions_with_debt_info(transactions)
    # Prepare summary for the next step.
    summary = summarize(transactions, account_filter)
    summary["date"] = date_str
    summary["previous_date"] = previous_date_str
    summary["category_filter"] = category_filter
    summary["account_filter"] = account_filter
    summary["comparison"] = build_summary_comparison(summary, previous_summary, previous_available)
    summary["category_comparison"] = build_category_comparison(
        summary.get("by_category", {}),
        previous_summary.get("by_category", {}),
        # Include this value in the surrounding collection or call.
        previous_available,
    # Close the structure that was opened above.
    )
    # Run this statement as part of the current workflow.
    attach_enriched_transactions(summary, transactions, account_filter)
    # Return summary to the caller.
    return summary


# Define get weekly report for callers in this flow.
def get_weekly_report(reference_date: str | None = None, category: str | None = None, account: str | None = None) -> dict:
    """Retrieve data needed by the get weekly report workflow in the service layer.

    Args:
        reference_date: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        category: Category name or category-like value from user input or sheet data.
        account: Account name or account-like value from user input or sheet data.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Run this statement as part of the current workflow.
    date_from, date_to = get_week_range(reference_date)
    current_start = datetime.strptime(date_from, "%Y-%m-%d").date()
    # Prepare previous start for the next step.
    previous_start = current_start - timedelta(days=7)
    # Prepare previous end for the next step.
    previous_end = current_start - timedelta(days=1)
    previous_from = previous_start.strftime("%Y-%m-%d")
    previous_to = previous_end.strftime("%Y-%m-%d")

    # Prepare records for the next step.
    records = get_transaction_records_for_report()
    # Prepare category filter for the next step.
    category_filter = resolve_category_filter(category, records)
    # Prepare account filter for the next step.
    account_filter = resolve_account_filter(account, records)
    # Open a multi-line structure for the values below.
    transactions = filter_transactions(
        # Include this value in the surrounding collection or call.
        records,
        # Prepare date from for the next step.
        date_from=date_from,
        # Prepare date to for the next step.
        date_to=date_to,
        # Prepare category for the next step.
        category=category_filter,
        # Prepare account for the next step.
        account=account_filter,
    # Close the structure that was opened above.
    )
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    # Open a multi-line structure for the values below.
    previous_transactions = filter_transactions(
        # Include this value in the surrounding collection or call.
        records,
        # Prepare date from for the next step.
        date_from=previous_from,
        # Prepare date to for the next step.
        date_to=previous_to,
        # Prepare category for the next step.
        category=category_filter,
        # Prepare account for the next step.
        account=account_filter,
    # Close the structure that was opened above.
    )
    # Prepare previous transactions for the next step.
    previous_transactions = enrich_transactions_with_debt_info(previous_transactions)
    # Prepare previous summary for the next step.
    previous_summary = summarize(previous_transactions, account_filter)
    # Prepare previous available for the next step.
    previous_available = len(previous_transactions) > 0

    # Prepare transactions for the next step.
    transactions = enrich_transactions_with_debt_info(transactions)
    # Prepare summary for the next step.
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
        # Include this value in the surrounding collection or call.
        previous_available,
    # Close the structure that was opened above.
    )
    # Run this statement as part of the current workflow.
    attach_enriched_transactions(summary, transactions, account_filter)
    # Return summary to the caller.
    return summary


# Define get monthly report for callers in this flow.
def get_monthly_report(year: int | None = None, month: int | None = None, category: str | None = None, account: str | None = None) -> dict:
    """Retrieve data needed by the get monthly report workflow in the service layer.

    Args:
        year: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        category: Category name or category-like value from user input or sheet data.
        account: Account name or account-like value from user input or sheet data.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Run this statement as part of the current workflow.
    date_from, date_to = get_month_range(year, month)
    # Prepare month label for the next step.
    month_label = date_from[:7]
    current_start = datetime.strptime(date_from, "%Y-%m-%d")

    # Handle the case where current_start.month == 1.
    if current_start.month == 1:
        # Run this statement as part of the current workflow.
        previous_year, previous_month = current_start.year - 1, 12
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Run this statement as part of the current workflow.
        previous_year, previous_month = current_start.year, current_start.month - 1

    # Run this statement as part of the current workflow.
    previous_from, previous_to = get_month_range(previous_year, previous_month)

    # Prepare records for the next step.
    records = get_transaction_records_for_report()
    # Prepare category filter for the next step.
    category_filter = resolve_category_filter(category, records)
    # Prepare account filter for the next step.
    account_filter = resolve_account_filter(account, records)
    # Open a multi-line structure for the values below.
    transactions = filter_transactions(
        # Include this value in the surrounding collection or call.
        records,
        # Prepare date from for the next step.
        date_from=date_from,
        # Prepare date to for the next step.
        date_to=date_to,
        # Prepare category for the next step.
        category=category_filter,
        # Prepare account for the next step.
        account=account_filter,
    # Close the structure that was opened above.
    )
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    # Open a multi-line structure for the values below.
    previous_transactions = filter_transactions(
        # Include this value in the surrounding collection or call.
        records,
        # Prepare date from for the next step.
        date_from=previous_from,
        # Prepare date to for the next step.
        date_to=previous_to,
        # Prepare category for the next step.
        category=category_filter,
        # Prepare account for the next step.
        account=account_filter,
    # Close the structure that was opened above.
    )
    # Prepare previous transactions for the next step.
    previous_transactions = enrich_transactions_with_debt_info(previous_transactions)
    # Prepare previous summary for the next step.
    previous_summary = summarize(previous_transactions, account_filter)
    # Prepare previous available for the next step.
    previous_available = len(previous_transactions) > 0

    # Prepare transactions for the next step.
    transactions = enrich_transactions_with_debt_info(transactions)
    # Prepare summary for the next step.
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
        # Include this value in the surrounding collection or call.
        previous_available,
    # Close the structure that was opened above.
    )
    # Run this statement as part of the current workflow.
    attach_enriched_transactions(summary, transactions, account_filter)
    # Return summary to the caller.
    return summary


# Define get account balance for callers in this flow.
def get_account_balance(account_name: str) -> float | None:
    """Retrieve data needed by the get account balance workflow in the service layer.

    Args:
        account_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `float | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare account key for the next step.
    account_key = normalize_account_key(account_name)
    # Handle the missing or empty account_key case.
    if not account_key:
        # Return None to the caller.
        return None

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Process each acc in the current collection.
        for acc in get_all_records(SHEET_ACCOUNTS):
            if normalize_account_key((acc or {}).get("account_name")) == account_key:
                return safe_float((acc or {}).get("balance", 0))
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass

    # Return None to the caller.
    return None


# Define get account monthly report for callers in this flow.
def get_account_monthly_report(account: str, month_arg: str | None = None) -> dict:
    """Retrieve data needed by the get account monthly report workflow in the service layer.

    Args:
        account: Account name or account-like value from user input or sheet data.
        month_arg: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Run this statement as part of the current workflow.
    year, month_num = parse_report_month_arg(month_arg)
    # Prepare report for the next step.
    report = get_monthly_report(year, month_num, account=account)
    account_filter = report.get("account_filter") or account
    report["period_label"] = report.get("month", "-")
    report["period_type"] = "month"
    report["account_balance"] = get_account_balance(account_filter)
    # Return report to the caller.
    return report


# Define get account all report for callers in this flow.
def get_account_all_report(account: str) -> dict:
    """Retrieve data needed by the get account all report workflow in the service layer.

    Args:
        account: Account name or account-like value from user input or sheet data.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare records for the next step.
    records = get_transaction_records_for_report()
    # Prepare account filter for the next step.
    account_filter = resolve_account_filter(account, records)
    # Prepare transactions for the next step.
    transactions = filter_transactions(records, account=account_filter)
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    # Prepare transactions for the next step.
    transactions = enrich_transactions_with_debt_info(transactions)
    # Prepare summary for the next step.
    summary = summarize(transactions, account_filter)
    summary["period_label"] = "Semua histori"
    summary["period_type"] = "all"
    summary["account_filter"] = account_filter
    summary["category_filter"] = None
    summary["comparison"] = {}
    summary["category_comparison"] = {}
    # Run this statement as part of the current workflow.
    attach_enriched_transactions(summary, transactions, account_filter)
    summary["account_balance"] = get_account_balance(account_filter)
    # Return summary to the caller.
    return summary


def get_account_report(account: str, period_arg: str | None = "month") -> dict:
    """Retrieve data needed by the get account report workflow in the service layer.

    Args:
        account: Account name or account-like value from user input or sheet data.
        period_arg: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    normalized_period = str(period_arg or "month").strip().lower()
    if normalized_period in {"all", "semua", "histori", "history"}:
        # Return get_account_all_report(account) to the caller.
        return get_account_all_report(account)
    return get_account_monthly_report(account, None if normalized_period == "month" else period_arg)


# Define search transactions for callers in this flow.
def search_transactions(keyword: str, limit: int = 10) -> list[dict]:
    """Coordinate the search transactions logic in the service layer.

    Args:
        keyword: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        limit: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    keyword_lower = str(keyword or "").strip().lower()
    # Handle the missing or empty keyword_lower case.
    if not keyword_lower:
        # Return [] to the caller.
        return []

    # Prepare records for the next step.
    records = get_transaction_records_for_report()
    # Prepare results for the next step.
    results = []

    # Process each r in the current collection.
    for r in records:
        searchable = " ".join([
            str(r.get("description", "")),
            str(r.get("subject", "")),
            str(r.get("category", "")),
            str(r.get("account", "")),
            str(r.get("to_account", "")),
            str(r.get("raw_input", "")),
        # Close the structure that was opened above.
        ]).lower()

        # Handle the case where keyword_lower in searchable.
        if keyword_lower in searchable:
            # Update results with the current value.
            results.append(r)

    results.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)
    # Return enrich_transactions_with_debt_info(results[:limit]) to the caller.
    return enrich_transactions_with_debt_info(results[:limit])


# Define get top expenses for callers in this flow.
def get_top_expenses(month: str | None = None, top_n: int = 5) -> list[dict]:
    """Get top monthly expenses sorted by net expense amount.

    Args:
        month: Month string in `YYYY-MM` format. Defaults to current month.
        top_n: Maximum number of rows to return.

    Returns:
        Enriched expense rows sorted by net amount after linked receivables.
    """
    # Handle the missing or empty month case.
    if not month:
        month = datetime.now().strftime("%Y-%m")

    # Prepare records for the next step.
    records = get_transaction_records_for_report()
    # Open a multi-line structure for the values below.
    expenses = [
        # Run this statement as part of the current workflow.
        r for r in records
        if str(r.get("type", "")).strip().lower() == "expense"
        and str(r.get("date", "")).startswith(str(month))
    # Close the structure that was opened above.
    ]

    # Prepare expenses for the next step.
    expenses = enrich_transactions_with_debt_info(expenses)
    # Run this statement as part of the current workflow.
    expenses.sort(key=get_effective_expense_amount, reverse=True)
    # Return expenses[:top_n] to the caller.
    return expenses[:top_n]
