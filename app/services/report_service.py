"""Reporting service for daily, weekly, monthly, account-based, category-based, and search reports."""

from functools import partial

from app.formatting import format_rupiah as _format_rupiah


format_rupiah = partial(_format_rupiah, preserve_decimals=False)


# Import datetime so this module can use its helpers.
from datetime import datetime, timedelta
from app.clock import business_now
# Import re for this module's local operations.
import re

# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import get_all_records
# Import app.config so this module can use its helpers.
from app.config import SHEET_TRANSACTIONS, SHEET_DEBTS, SHEET_ACCOUNTS


# ── Helpers ───────────────────────────────────────────────────────────────────

# Helper for get transaction records for report.
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
    # Load records for the current calculation.
    records = get_all_records(SHEET_TRANSACTIONS)
    # Build result for the response flow.
    result = []

    # Iterate through each i, record.
    for i, record in enumerate(records, start=2):
        item = dict(record or {})
        item["_row_index"] = i
        # Append the current value to result.
        result.append(item)

    return result


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

    # Format Indonesia umum: 10.000, 10,000, Rp10.000
    raw = raw.replace("Rp", "").replace("rp", "").strip()

    if "." in raw and "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        parts = raw.split(",")
        if len(parts[-1]) == 2:
            raw = raw.replace(",", ".")
        # Use the fallback path when no earlier branch matched.
        else:
            raw = raw.replace(",", "")
    # Split bill parsing note: separate the paid transaction from each person share.
    elif "." in raw:
        parts = raw.split(".")
        # Handle len(parts) > 1 and all(len(p) == 3 for p in parts[1:]).
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            raw = raw.replace(".", "")

    raw = re.sub(r"[^0-9.-]", "", raw)

    # Run this operation in a guarded block so failures can be handled.
    try:
        return float(raw)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return default



# Helper for normalize category key.
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


# Helper for normalize account key.
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


# Helper for get known report accounts.
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
    # Extract accounts for validation.
    accounts = []
    seen = set()

    # Helper for add.
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
        key = normalize_account_key(value)
        # Handle value and key and key not in seen.
        if value and key and key not in seen:
            # Append the current value to accounts.
            accounts.append(value)
            # Append the current value to seen.
            seen.add(key)

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Iterate through each acc.
        for acc in get_all_records(SHEET_ACCOUNTS):
            add((acc or {}).get("account_name"))
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass

    # Iterate through each record.
    for record in records or []:
        add((record or {}).get("account"))
        add((record or {}).get("to_account"))

    return accounts


# Helper for resolve account filter.
def resolve_account_filter(account_query: str | None, records: list[dict] | None = None) -> str | None:
    """Resolve a user input or reference for account filter."""
    query = str(account_query or "").strip()
    # Validate missing query before continuing.
    if not query:
        return None

    query_key = normalize_account_key(query)
    # Validate missing query key before continuing.
    if not query_key:
        return None

    # Extract accounts for validation.
    accounts = get_known_report_accounts(records)
    # Extract account by key for validation.
    account_by_key = {normalize_account_key(acc): acc for acc in accounts}

    if query_key in account_by_key:
        return account_by_key[query_key]

    partial_matches = [
        acc for acc in accounts
        # Handle query key in normalize account key(acc) or normalize account.
        if query_key in normalize_account_key(acc) or normalize_account_key(acc) in query_key
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]

    # Legacy compatibility note for older records or older in-memory state.
    return query


# Helper for is account match.
def is_account_match(value: str | None, account_key: str | None) -> bool:
    """Check whether a condition is true for account match."""
    # Validate missing account key before continuing.
    if not account_key:
        return False
    return normalize_account_key(value) == account_key


# Helper for is account transaction.
def is_account_transaction(record: dict, account: str | None) -> bool:
    """Check whether a condition is true for account transaction."""
    # Extract account key for validation.
    account_key = normalize_account_key(account)
    # Validate missing account key before continuing.
    if not account_key:
        return True

    txn_type = str((record or {}).get("type", "") or "").strip().lower()
    source_account = (record or {}).get("account")
    target_account = (record or {}).get("to_account")

    if txn_type == "transfer":
        return is_account_match(source_account, account_key) or is_account_match(target_account, account_key)

    return is_account_match(source_account, account_key)


# Helper for split report filter args.
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
    # Validate missing raw before continuing.
    if not raw:
        return None, None, None

    # Prepare tokens from the incoming input.
    tokens = raw.split()
    markers = {"rekening", "akun", "account", "rek"}

    # Iterate through each idx, token.
    for idx, token in enumerate(tokens):
        token_key = normalize_account_key(token)
        if token_key not in markers:
            # Skip the rest of this loop iteration after handling this case.
            continue

        before = " ".join(tokens[:idx]).strip()
        after = " ".join(tokens[idx + 1:]).strip()

        period_arg, category_arg = split_report_period_and_category_arg(before, mode)
        account_period_arg, account_arg = split_report_period_and_category_arg(after, mode)

        # Validate missing period arg and account period arg before continuing.
        if not period_arg and account_period_arg:
            # Extract period arg for validation.
            period_arg = account_period_arg

        # Extract account arg for validation.
        account_arg = account_arg if account_period_arg else after
        return period_arg, category_arg, (account_arg or None)

    period_arg, category_arg = split_report_period_and_category_arg(raw, mode)
    return period_arg, category_arg, None


# Helper for split account period arg.
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
    # Validate missing raw before continuing.
    if not raw:
        return None, "month"

    # Prepare tokens from the incoming input.
    tokens = raw.split()
    # Prepare low tokens from the incoming input.
    low_tokens = [normalize_account_key(t) for t in tokens]

    for marker in ["rekening", "akun", "account", "rek"]:
        # Handle low tokens and low tokens[0] == marker.
        if low_tokens and low_tokens[0] == marker:
            # Prepare tokens from the incoming input.
            tokens = tokens[1:]
            # Prepare low tokens from the incoming input.
            low_tokens = low_tokens[1:]
            raw = " ".join(tokens).strip()
            # Leave the loop after the target condition has been reached.
            break

    # Validate missing raw before continuing.
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
    "Utang Tanpa Ubah Saldo",
    "Piutang Tanpa Cashflow",
    "Piutang Tanpa Ubah Saldo",
    "Pembayaran Debt Tanpa Cashflow",
    "Pembayaran Debt Tanpa Ubah Saldo",
    "Debt Tanpa Cashflow",
    "Debt Tanpa Ubah Saldo",
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


# Helper for get known report categories.
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
    categories = []
    seen = set()

    # Helper for add.
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
        key = normalize_category_key(value)
        # Handle value and key and key not in seen.
        if value and key and key not in seen:
            # Append the current value to categories.
            categories.append(value)
            # Append the current value to seen.
            seen.add(key)

    # Iterate through each cat.
    for cat in DEFAULT_REPORT_CATEGORIES:
        add(cat)

    # Iterate through each record.
    for record in records or []:
        add((record or {}).get("category"))

    return categories


# Helper for resolve category filter.
def resolve_category_filter(category_query: str | None, records: list[dict] | None = None) -> str | None:
    """Resolve a user input or reference for category filter."""
    query = str(category_query or "").strip()
    # Validate missing query before continuing.
    if not query:
        return None

    query_key = normalize_category_key(query)
    # Validate missing query key before continuing.
    if not query_key:
        return None

    # Extract alias category for validation.
    alias_category = CATEGORY_ALIASES.get(query_key)
    if alias_category:
        return alias_category

    categories = get_known_report_categories(records)
    # Extract category by key for validation.
    category_by_key = {normalize_category_key(cat): cat for cat in categories}

    if query_key in category_by_key:
        return category_by_key[query_key]

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    partial_matches = [
        cat for cat in categories
        # Handle query key in normalize category key(cat) or normalize categor.
        if query_key in normalize_category_key(cat) or normalize_category_key(cat) in query_key
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]

    # Legacy compatibility note for older records or older in-memory state.
    return query


# Helper for split report period and category arg.
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
    # Validate missing raw before continuing.
    if not raw:
        return None, None

    parser = parse_report_month_arg if mode == "month" else parse_report_date_arg
    # Prepare tokens from the incoming input.
    tokens = raw.split()
    max_prefix = min(len(tokens), 3)

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    for n in range(max_prefix, 0, -1):
        candidate = " ".join(tokens[:n]).strip()
        rest = " ".join(tokens[n:]).strip() or None
        # Run this operation in a guarded block so failures can be handled.
        try:
            parser(candidate)
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
            parser(candidate)
            return candidate, rest
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Keep this intentionally empty block valid.
            pass

    return None, raw


# Helper for is truthy sheet value.
def is_truthy_sheet_value(value) -> bool:
    """Check whether a condition is true for truthy sheet value."""
    raw = str(value or "").strip().lower()
    return raw in {"true", "yes", "y", "1", "settled", "lunas", "void", "voided"}


# Helper for is voided debt record.
def is_voided_debt_record(debt: dict) -> bool:
    """Check whether a condition is true for voided debt record."""
    description = str((debt or {}).get("description", "") or "")
    return "[VOID" in description.upper()


# Helper for parse transaction debt ids from record.
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
    # Validate missing raw before continuing.
    if not raw:
        return []
    return [part.strip() for part in re.split(r"[,;\s]+", raw) if part.strip()]


# Helper for build debt lookup.
def build_debt_lookup(active_only: bool = True) -> dict:
    """Build the data structure or message text for debt lookup."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Load records for the current calculation.
        records = get_all_records(SHEET_DEBTS)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Load records for the current calculation.
        records = []

    by_id = {}
    by_source_txn = {}

    # Iterate through each debt.
    for debt in records:
        item = dict(debt or {})
        debt_id = str(item.get("id", "") or "").strip()
        # Validate missing debt id before continuing.
        if not debt_id:
            # Skip the rest of this loop iteration after handling this case.
            continue

        if is_voided_debt_record(item):
            # Skip the rest of this loop iteration after handling this case.
            continue

        settled = is_truthy_sheet_value(item.get("is_settled", "FALSE"))
        remaining = safe_float(item.get("remaining_amount", 0))
        # Handle active only and (settled or remaining <= 0).
        if active_only and (settled or remaining <= 0):
            # Skip the rest of this loop iteration after handling this case.
            continue

        by_id[debt_id] = item

        source_txn_id = str(item.get("source_transaction_id", "") or "").strip()
        if source_txn_id:
            by_source_txn.setdefault(source_txn_id, []).append(item)

    return {"by_id": by_id, "by_source_txn": by_source_txn}


# Helper for get linked debts for transaction.
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

    linked = []
    seen = set()

    # Iterate through each debt id.
    for debt_id in parse_transaction_debt_ids_from_record(txn):
        debt = by_id.get(debt_id)
        # Add each linked debt only once to avoid duplicate report rows.
        if debt and debt_id not in seen:
            # Append the current value to linked.
            linked.append(debt)
            # Append the current value to seen.
            seen.add(debt_id)

    txn_id = str((txn or {}).get("id", "") or "").strip()
    # Iterate through each debt.
    for debt in by_source_txn.get(txn_id, []) or []:
        debt_id = str(debt.get("id", "") or "").strip()
        # Handle debt id and debt id not in seen.
        if debt_id and debt_id not in seen:
            # Append the current value to linked.
            linked.append(debt)
            # Append the current value to seen.
            seen.add(debt_id)

    return linked


# Helper for enrich transactions with debt info.
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
    lookup = build_debt_lookup(active_only=False)
    enriched = []

    # Iterate through each txn.
    for txn in transactions or []:
        item = dict(txn or {})
        # Load linked debts for the current calculation.
        linked_debts = get_linked_debts_for_transaction(item, lookup)

        receivable_remaining = 0.0
        payable_remaining = 0.0
        receivable_original = 0.0
        payable_original = 0.0
        people = []
        # Extract receivable by person for validation.
        receivable_by_person = {}
        # Extract payable by person for validation.
        payable_by_person = {}
        # Extract receivable original by person for validation.
        receivable_original_by_person = {}
        # Extract payable original by person for validation.
        payable_original_by_person = {}

        # Iterate through each debt.
        for debt in linked_debts:
            remaining_amount = safe_float(debt.get("remaining_amount", 0))
            original_amount = safe_float(debt.get("original_amount", remaining_amount))
            debt_type = str(debt.get("type", "") or "").strip().lower()
            person = str(debt.get("person_name", "") or "").strip() or "Tanpa nama"
            if person and person not in people:
                # Append the current value to people.
                people.append(person)

            if debt_type == "receivable":
                receivable_remaining += remaining_amount
                receivable_original += original_amount
                if remaining_amount > 0:
                    receivable_by_person[person] = receivable_by_person.get(person, 0.0) + remaining_amount
                if original_amount > 0:
                    receivable_original_by_person[person] = receivable_original_by_person.get(person, 0.0) + original_amount
            elif debt_type == "payable":
                payable_remaining += remaining_amount
                payable_original += original_amount
                if remaining_amount > 0:
                    payable_by_person[person] = payable_by_person.get(person, 0.0) + remaining_amount
                if original_amount > 0:
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
            # Iterate through each person, amount.
            for person, amount in receivable_by_person.items()
            if amount > 0
        ]
        item["debt_payable_parts"] = [
            {"person_name": person, "remaining_amount": amount}
            # Iterate through each person, amount.
            for person, amount in payable_by_person.items()
            if amount > 0
        ]
        item["debt_receivable_original_parts"] = [
            {"person_name": person, "original_amount": amount}
            # Iterate through each person, amount.
            for person, amount in receivable_original_by_person.items()
            if amount > 0
        ]
        item["debt_payable_original_parts"] = [
            {"person_name": person, "original_amount": amount}
            # Iterate through each person, amount.
            for person, amount in payable_original_by_person.items()
            if amount > 0
        ]
        item["net_expense_after_receivable"] = max(expense_amount - receivable_original, 0.0)
        # Append the current value to enriched.
        enriched.append(item)

    return enriched


# Helper for get effective expense amount.
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
        return amount

    if "net_expense_after_receivable" in (txn or {}):
        return max(safe_float((txn or {}).get("net_expense_after_receivable", amount)), 0.0)

    receivable = safe_float(
        (txn or {}).get("debt_receivable_original", (txn or {}).get("debt_receivable_remaining", 0))
    )
    return max(amount - receivable, 0.0)


# Helper for calculate net expense after receivable.
def calculate_net_expense_after_receivable(transactions: list[dict]) -> float:
    """Calculate total net expense after linked receivable shares.

    Args:
        transactions: Enriched or raw transaction rows.

    Returns:
        Sum of expense amounts after subtracting receivable portions created by
        split bill or talangan flows.
    """
    total = 0.0
    # Iterate through each txn.
    for txn in transactions or []:
        txn_type = str((txn or {}).get("type", "") or "").strip().lower()
        if txn_type != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue
        total += get_effective_expense_amount(txn)
    return total


# Helper for calculate net expense by category.
def calculate_net_expense_by_category(transactions: list[dict]) -> dict:
    """Calculate net expense totals grouped by category.

    Args:
        transactions: Enriched or raw transaction rows.

    Returns:
        Category totals sorted descending by net expense.
    """
    # Build result for the response flow.
    result = {}
    # Iterate through each txn.
    for txn in transactions or []:
        txn_type = str((txn or {}).get("type", "") or "").strip().lower()
        if txn_type != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue
        category = str((txn or {}).get("category") or "Other").strip() or "Other"
        result[category] = result.get(category, 0.0) + get_effective_expense_amount(txn)
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


# Helper for attach enriched transactions.
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
    enriched = enrich_transactions_with_debt_info(transactions)
    refreshed = summarize(enriched, account)
    # Iterate through each key.
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
    ]:
        summary[key] = refreshed.get(key, summary.get(key))
    summary["transactions"] = enriched
    summary["total_net_expense_after_receivable"] = summary.get("total_expense", 0)
    summary["by_category_net"] = summary.get("by_category", {})
    return summary


# Helper for build delta info.
def build_delta_info(current_value, previous_value, previous_available: bool = True) -> dict:
    """Build the data structure or message text for delta info."""
    cur = safe_float(current_value, 0)

    # Validate missing previous available before continuing.
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


# Helper for build summary comparison.
def build_summary_comparison(current: dict, previous: dict, previous_available: bool = True) -> dict:
    """Build the data structure or message text for summary comparison."""
    current = current or {}
    previous = previous or {}
    keys = ["total_income", "total_expense", "net", "count"]

    return {
        key: build_delta_info(current.get(key, 0), previous.get(key, 0), previous_available)
        # Iterate through each key.
        for key in keys
    }


# Helper for build category comparison.
def build_category_comparison(current: dict, previous: dict, previous_available: bool = True) -> dict:
    """Build the data structure or message text for category comparison."""
    current = current or {}
    previous = previous or {}
    previous_keys = {normalize_category_key(cat): cat for cat in previous.keys()}
    # Build result for the response flow.
    result = {}

    # Iterate through each category, current amount.
    for category, current_amount in current.items():
        # Extract category key for validation.
        category_key = normalize_category_key(category)
        # Extract has previous category for validation.
        has_previous_category = previous_available and category_key in previous_keys
        # Extract previous category for validation.
        previous_category = previous_keys.get(category_key)
        # Extract previous amount for validation.
        previous_amount = previous.get(previous_category, 0) if previous_category else 0

        result[category] = build_delta_info(
            current_amount,
            previous_amount,
            previous_available=has_previous_category,
        )

    return result

# Helper for parse report date arg.
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
    today = business_now().date()

    # Validate missing value before continuing.
    if not value:
        return today.strftime("%Y-%m-%d")

    # Prepare raw from the incoming input.
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


# Helper for parse report month arg.
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
    today = business_now().date()

    # Validate missing value before continuing.
    if not value:
        return today.year, today.month

    raw = str(value).strip().lower().replace("/", "-")

    if raw in ["month", "bulan", "bulanan", "bulanini", "bulan ini", "this month", "current month"]:
        return today.year, today.month

    if raw in ["last month", "bulan lalu", "bulanlalu", "bln lalu", "blnlalu", "month lalu"]:
        first_this_month = datetime(today.year, today.month, 1).date()
        # Extract last month date for validation.
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
        # Validate missing 1 <= month <= 12 before continuing.
        if not 1 <= month <= 12:
            raise ValueError("Bulan harus antara 1 sampai 12.")
        return year, month

    m = re.fullmatch(r"(\d{1,2})-(20\d{2})", raw)
    if m:
        month = int(m.group(1))
        year = int(m.group(2))
        # Validate missing 1 <= month <= 12 before continuing.
        if not 1 <= month <= 12:
            raise ValueError("Bulan harus antara 1 sampai 12.")
        return year, month

    if re.fullmatch(r"\d{1,2}", raw):
        month = int(raw)
        # Validate missing 1 <= month <= 12 before continuing.
        if not 1 <= month <= 12:
            raise ValueError("Bulan harus antara 1 sampai 12.")
        return today.year, month

    raise ValueError("Format bulan tidak dikenali. Contoh: 2026-06 atau 6.")


# Helper for get week range.
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
    monday = base_date - timedelta(days=base_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


# Helper for get month range.
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
    now = business_now()
    year = int(year or now.year)
    month = int(month or now.month)

    # Validate missing 1 <= month <= 12 before continuing.
    if not 1 <= month <= 12:
        raise ValueError("Bulan harus antara 1 sampai 12.")

    first_dt = datetime(year, month, 1)
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    # Use the fallback path when no earlier branch matched.
    else:
        next_month = datetime(year, month + 1, 1)

    last_dt = next_month - timedelta(days=1)
    return first_dt.strftime("%Y-%m-%d"), last_dt.strftime("%Y-%m-%d")


# Helper for filter transactions.
def filter_transactions(
    records: list[dict],
    date_from: str | None = None,
    date_to: str | None = None,
    txn_type: str | None = None,
    category: str | None = None,
    account: str | None = None,
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
    # Build result for the response flow.
    result = []
    # Extract category key for validation.
    category_key = normalize_category_key(category) if category else None
    account_filter = str(account or "").strip() or None

    # Iterate through each r.
    for r in records:
        date = str(r.get("date", "")).strip()
        record_type = str(r.get("type", "")).strip().lower()
        record_category_key = normalize_category_key(r.get("category"))

        # Validate missing date before continuing.
        if not date:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle date from and date < date from.
        if date_from and date < date_from:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle date to and date > date to.
        if date_to and date > date_to:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle txn type and record type != str(txn type).
        if txn_type and record_type != str(txn_type).strip().lower():
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle category key and record category key != category key.
        if category_key and record_category_key != category_key:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle account filter and not is account transaction(r, account filter).
        if account_filter and not is_account_transaction(r, account_filter):
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Append the current value to result.
        result.append(r)

    return result


# Helper for summarize.
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
    # Extract account key for validation.
    account_key = normalize_account_key(account) if account else None
    total_income = 0.0
    total_expense = 0.0
    total_gross_expense = 0.0
    total_transfer = 0.0
    total_transfer_in = 0.0
    total_transfer_out = 0.0
    # Extract by category for validation.
    by_category = {}
    # Extract by category gross for validation.
    by_category_gross = {}

    # Iterate through each t.
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
                # Extract net amount for validation.
                net_amount = get_effective_expense_amount(t)
                total_expense += net_amount
                total_gross_expense += amount
                by_category[category] = by_category.get(category, 0.0) + net_amount
                by_category_gross[category] = by_category_gross.get(category, 0.0) + amount
        elif txn_type == "transfer":
            if account_key:
                if source_match:
                    total_transfer_out += amount
                if target_match:
                    total_transfer_in += amount
                if source_match or target_match:
                    total_transfer += amount
            # Use the fallback path when no earlier branch matched.
            else:
                total_transfer += amount

    if account_key:
        net = total_income + total_transfer_in - total_expense - total_transfer_out
    # Use the fallback path when no earlier branch matched.
    else:
        net = total_income - total_expense

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
    }


# ── Report functions ──────────────────────────────────────────────────────────

# Helper for get daily report.
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
    # Extract date str for validation.
    date_str = parse_report_date_arg(date_str)
    current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    # Extract previous date for validation.
    previous_date = current_date - timedelta(days=1)
    previous_date_str = previous_date.strftime("%Y-%m-%d")

    # Load records for the current calculation.
    records = get_transaction_records_for_report()
    # Extract category filter for validation.
    category_filter = resolve_category_filter(category, records)
    # Extract account filter for validation.
    account_filter = resolve_account_filter(account, records)
    transactions = filter_transactions(
        records,
        # Extract date from for validation.
        date_from=date_str,
        # Extract date to for validation.
        date_to=date_str,
        # Extract category for validation.
        category=category_filter,
        # Extract account for validation.
        account=account_filter,
    )
    transactions.sort(key=lambda x: int(x.get("_row_index", 0) or 0), reverse=True)

    previous_transactions = filter_transactions(
        records,
        # Extract date from for validation.
        date_from=previous_date_str,
        # Extract date to for validation.
        date_to=previous_date_str,
        # Extract category for validation.
        category=category_filter,
        # Extract account for validation.
        account=account_filter,
    )
    # Load previous transactions for the current calculation.
    previous_transactions = enrich_transactions_with_debt_info(previous_transactions)
    # Build previous summary for the response flow.
    previous_summary = summarize(previous_transactions, account_filter)
    previous_available = len(previous_transactions) > 0

    # Load transactions for the current calculation.
    transactions = enrich_transactions_with_debt_info(transactions)
    # Build summary for the response flow.
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
    attach_enriched_transactions(summary, transactions, account_filter)
    return summary


# Helper for get weekly report.
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
    date_from, date_to = get_week_range(reference_date)
    current_start = datetime.strptime(date_from, "%Y-%m-%d").date()
    previous_start = current_start - timedelta(days=7)
    previous_end = current_start - timedelta(days=1)
    previous_from = previous_start.strftime("%Y-%m-%d")
    previous_to = previous_end.strftime("%Y-%m-%d")

    # Load records for the current calculation.
    records = get_transaction_records_for_report()
    # Extract category filter for validation.
    category_filter = resolve_category_filter(category, records)
    # Extract account filter for validation.
    account_filter = resolve_account_filter(account, records)
    transactions = filter_transactions(
        records,
        # Extract date from for validation.
        date_from=date_from,
        # Extract date to for validation.
        date_to=date_to,
        # Extract category for validation.
        category=category_filter,
        # Extract account for validation.
        account=account_filter,
    )
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    previous_transactions = filter_transactions(
        records,
        # Extract date from for validation.
        date_from=previous_from,
        # Extract date to for validation.
        date_to=previous_to,
        # Extract category for validation.
        category=category_filter,
        # Extract account for validation.
        account=account_filter,
    )
    # Load previous transactions for the current calculation.
    previous_transactions = enrich_transactions_with_debt_info(previous_transactions)
    # Build previous summary for the response flow.
    previous_summary = summarize(previous_transactions, account_filter)
    previous_available = len(previous_transactions) > 0

    # Load transactions for the current calculation.
    transactions = enrich_transactions_with_debt_info(transactions)
    # Build summary for the response flow.
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
    attach_enriched_transactions(summary, transactions, account_filter)
    return summary


# Helper for get monthly report.
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
    date_from, date_to = get_month_range(year, month)
    month_label = date_from[:7]
    current_start = datetime.strptime(date_from, "%Y-%m-%d")

    if current_start.month == 1:
        previous_year, previous_month = current_start.year - 1, 12
    # Use the fallback path when no earlier branch matched.
    else:
        previous_year, previous_month = current_start.year, current_start.month - 1

    previous_from, previous_to = get_month_range(previous_year, previous_month)

    # Load records for the current calculation.
    records = get_transaction_records_for_report()
    # Extract category filter for validation.
    category_filter = resolve_category_filter(category, records)
    # Extract account filter for validation.
    account_filter = resolve_account_filter(account, records)
    transactions = filter_transactions(
        records,
        # Extract date from for validation.
        date_from=date_from,
        # Extract date to for validation.
        date_to=date_to,
        # Extract category for validation.
        category=category_filter,
        # Extract account for validation.
        account=account_filter,
    )
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    previous_transactions = filter_transactions(
        records,
        # Extract date from for validation.
        date_from=previous_from,
        # Extract date to for validation.
        date_to=previous_to,
        # Extract category for validation.
        category=category_filter,
        # Extract account for validation.
        account=account_filter,
    )
    # Load previous transactions for the current calculation.
    previous_transactions = enrich_transactions_with_debt_info(previous_transactions)
    # Build previous summary for the response flow.
    previous_summary = summarize(previous_transactions, account_filter)
    previous_available = len(previous_transactions) > 0

    # Load transactions for the current calculation.
    transactions = enrich_transactions_with_debt_info(transactions)
    # Build summary for the response flow.
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
    attach_enriched_transactions(summary, transactions, account_filter)
    return summary


# Helper for get account balance.
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
    # Extract account key for validation.
    account_key = normalize_account_key(account_name)
    # Validate missing account key before continuing.
    if not account_key:
        return None

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Iterate through each acc.
        for acc in get_all_records(SHEET_ACCOUNTS):
            if normalize_account_key((acc or {}).get("account_name")) == account_key:
                return safe_float((acc or {}).get("balance", 0))
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Keep this intentionally empty block valid.
        pass

    return None


# Helper for get account monthly report.
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
    year, month_num = parse_report_month_arg(month_arg)
    report = get_monthly_report(year, month_num, account=account)
    account_filter = report.get("account_filter") or account
    report["period_label"] = report.get("month", "-")
    report["period_type"] = "month"
    report["account_balance"] = get_account_balance(account_filter)
    return report


# Helper for get account all report.
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
    # Load records for the current calculation.
    records = get_transaction_records_for_report()
    # Extract account filter for validation.
    account_filter = resolve_account_filter(account, records)
    # Load transactions for the current calculation.
    transactions = filter_transactions(records, account=account_filter)
    transactions.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)

    # Load transactions for the current calculation.
    transactions = enrich_transactions_with_debt_info(transactions)
    # Build summary for the response flow.
    summary = summarize(transactions, account_filter)
    summary["period_label"] = "Semua histori"
    summary["period_type"] = "all"
    summary["account_filter"] = account_filter
    summary["category_filter"] = None
    summary["comparison"] = {}
    summary["category_comparison"] = {}
    attach_enriched_transactions(summary, transactions, account_filter)
    summary["account_balance"] = get_account_balance(account_filter)
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
        return get_account_all_report(account)
    return get_account_monthly_report(account, None if normalized_period == "month" else period_arg)


# Helper for search transactions.
def search_transactions(keyword: str, limit: int | None = 10) -> list[dict]:
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
    # Validate missing keyword lower before continuing.
    if not keyword_lower:
        return []

    # Load records for the current calculation.
    records = get_transaction_records_for_report()
    # Build results for the response flow.
    results = []

    # Iterate through each r.
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
            # Append the current value to results.
            results.append(r)

    results.sort(key=lambda x: (str(x.get("date", "")), int(x.get("_row_index", 0) or 0)), reverse=True)
    return enrich_transactions_with_debt_info(results if limit is None else results[:limit])


# Helper for get top expenses.
def get_top_expenses(month: str | None = None, top_n: int = 5) -> list[dict]:
    """Get top monthly expenses sorted by net expense amount.

    Args:
        month: Month string in `YYYY-MM` format. Defaults to current month.
        top_n: Maximum number of rows to return.

    Returns:
        Enriched expense rows sorted by net amount after linked receivables.
    """
    # Validate missing month before continuing.
    if not month:
        month = business_now().strftime("%Y-%m")

    # Load records for the current calculation.
    records = get_transaction_records_for_report()
    expenses = [
        r for r in records
        if str(r.get("type", "")).strip().lower() == "expense"
        and str(r.get("date", "")).startswith(str(month))
    ]

    expenses = enrich_transactions_with_debt_info(expenses)
    expenses.sort(key=get_effective_expense_amount, reverse=True)
    return expenses[:top_n]
