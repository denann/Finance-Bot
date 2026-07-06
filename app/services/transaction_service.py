"""Transaction service for saving, editing, deleting, batching, account balance updates, and debt relation updates."""


# Import datetime so this module can use its helpers.
from datetime import datetime, timedelta
# Import re for this module's local operations.
import re
# Import uuid for this module's local operations.
import uuid

# Import app.nlp.normalizer so this module can use its helpers.
from app.nlp.normalizer import extract_amount_from_text
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import ensure_category_for_transaction

# Import app.config so this module can use its helpers.
from app.config import SHEET_ACCOUNTS, SHEET_TRANSACTIONS
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import (
    # Include this value in the surrounding collection or call.
    append_row,
    # Include this value in the surrounding collection or call.
    append_rows,
    # Include this value in the surrounding collection or call.
    delete_rows,
    # Include this value in the surrounding collection or call.
    find_row_index,
    # Include this value in the surrounding collection or call.
    get_all_records,
    # Include this value in the surrounding collection or call.
    get_sheet,
    # Include this value in the surrounding collection or call.
    update_cell,
    # Include this value in the surrounding collection or call.
    update_row,
# Close the structure that was opened above.
)

# Open a multi-line structure for the values below.
EXPORT_TRANSACTION_COLUMNS = [
    "id",
    "date",
    "type",
    "amount",
    "category",
    "account",
    "to_account",
    "subject",
    "description",
    "catatan",
    "tipe_pengeluaran",
    "raw_input",
    "parsed_by",
    "hutang_id",
    "tipe_hutang",
# Close the structure that was opened above.
]

# Schema compatibility note for Google Sheets headers and rows.
HUTANG_ID_COL = 14
# Prepare TIPE HUTANG COL for the next step.
TIPE_HUTANG_COL = 15


# Define get current month str for callers in this flow.
def get_current_month_str() -> str:
    """Return the current local month in `YYYY-MM` format."""
    return datetime.now().strftime("%Y-%m")


# Define normalize export period for callers in this flow.
def normalize_export_period(period: str | None = None) -> dict:
    """Normalize input values for the normalize export period workflow in the service layer.

    Args:
        period: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare today for the next step.
    today = datetime.now().date()

    # Handle the missing or empty period case.
    if not period:
        # Prepare month for the next step.
        month = get_current_month_str()
        # Return { to the caller.
        return {
            "type": "month",
            "label": f"bulan {month}",
            "filename_suffix": month,
            "month": month,
            "date_from": None,
            "date_to": None,
        # Close the structure that was opened above.
        }

    # Prepare clean for the next step.
    clean = str(period).strip().lower()

    if clean in ["today", "hariini", "harian", "hari"]:
        today_str = today.strftime("%Y-%m-%d")
        # Return { to the caller.
        return {
            "type": "date_range",
            "label": f"hari ini ({today_str})",
            "filename_suffix": today_str,
            "month": None,
            "date_from": today,
            "date_to": today,
        # Close the structure that was opened above.
        }

    if clean in ["week", "minggu", "mingguan"]:
        # Prepare start week for the next step.
        start_week = today - timedelta(days=today.weekday())
        # Prepare end week for the next step.
        end_week = start_week + timedelta(days=6)

        # Return { to the caller.
        return {
            "type": "date_range",
            "label": f"minggu ini ({start_week} s/d {end_week})",
            "filename_suffix": f"{start_week}_to_{end_week}",
            "month": None,
            "date_from": start_week,
            "date_to": end_week,
        # Close the structure that was opened above.
        }

    if clean in ["month", "bulan", "bulanan"]:
        # Prepare month for the next step.
        month = get_current_month_str()
        # Return { to the caller.
        return {
            "type": "month",
            "label": f"bulan {month}",
            "filename_suffix": month,
            "month": month,
            "date_from": None,
            "date_to": None,
        # Close the structure that was opened above.
        }

    match = re.fullmatch(r"(20\d{2})[-/](0?[1-9]|1[0-2])", clean)
    # Handle the case where match.
    if match:
        # Prepare year for the next step.
        year = match.group(1)
        # Prepare month num for the next step.
        month_num = int(match.group(2))
        month = f"{year}-{month_num:02d}"

        # Return { to the caller.
        return {
            "type": "month",
            "label": f"bulan {month}",
            "filename_suffix": month,
            "month": month,
            "date_from": None,
            "date_to": None,
        # Close the structure that was opened above.
        }

    # Raise a clear error so the caller can stop this invalid flow.
    raise ValueError(
        "Format export tidak dikenali. Gunakan: /download_data, /download_data today, /download_data week, /download_data month, atau /download_data 2026-06."
    # Close the structure that was opened above.
    )


# Define parse date safe for callers in this flow.
def parse_date_safe(value):
    """Parse a `YYYY-MM-DD` value without raising on invalid input.

    Args:
        value: Date-like value from sheet or user filter input.

    Returns:
        `datetime.date` when parsing succeeds, otherwise `None`.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return None to the caller.
        return None


# Define get transactions for export for callers in this flow.
def get_transactions_for_export(period: str | None = None) -> dict:
    """Collect transactions for CSV/export by supported period filter.

    Args:
        period: Optional export period such as `today`, `week`, `month`, or
            `YYYY-MM`.

    Returns:
        Result dict with success flag, filtered records, filter metadata,
        summary data, and message on invalid period.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare filter info for the next step.
        filter_info = normalize_export_period(period)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "records": [],
            "filter": {},
            "summary": {},
            "message": str(e),
        # Close the structure that was opened above.
        }

    # Prepare records for the next step.
    records = get_all_records(SHEET_TRANSACTIONS)
    # Prepare filtered for the next step.
    filtered = []

    # Process each record in the current collection.
    for record in records:
        txn_date_raw = str(record.get("date", "")).strip()

        if filter_info["type"] == "month":
            if txn_date_raw.startswith(filter_info["month"]):
                # Update filtered with the current value.
                filtered.append(record)

        elif filter_info["type"] == "date_range":
            # Prepare txn date for the next step.
            txn_date = parse_date_safe(txn_date_raw)

            # Handle the missing or empty txn_date case.
            if not txn_date:
                # Skip the rest of this loop iteration after handling this case.
                continue

            if filter_info["date_from"] <= txn_date <= filter_info["date_to"]:
                # Update filtered with the current value.
                filtered.append(record)

    # Prepare total income for the next step.
    total_income = 0.0
    # Prepare total expense for the next step.
    total_expense = 0.0
    # Prepare total transfer for the next step.
    total_transfer = 0.0

    # Process each record in the current collection.
    for record in filtered:
        txn_type = str(record.get("type", "")).strip()
        amount = float(record.get("amount", 0) or 0)

        if txn_type == "income":
            # Run this statement as part of the current workflow.
            total_income += amount
        elif txn_type == "expense":
            # Run this statement as part of the current workflow.
            total_expense += amount
        elif txn_type == "transfer":
            # Run this statement as part of the current workflow.
            total_transfer += amount

    # Open a multi-line structure for the values below.
    summary = {
        "count": len(filtered),
        "total_income": total_income,
        "total_expense": total_expense,
        "total_transfer": total_transfer,
        "net": total_income - total_expense,
    # Close the structure that was opened above.
    }

    # Return { to the caller.
    return {
        "success": True,
        "records": filtered,
        "filter": filter_info,
        "summary": summary,
        "message": "ok",
    # Close the structure that was opened above.
    }

# Open a multi-line structure for the values below.
DEBT_CASHFLOW_CATEGORIES = {
    "Piutang Diberikan",
    "Pembayaran Piutang",
    "Penerimaan Utang",
    "Bayar Utang",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
SKIP_ACCOUNT_NAMES = {
    "sudah berlalu",
    "tanpa rekening",
    "tidak masuk rekening",
    "jangan ubah saldo",
    "ditalangin",
    "debt only",
    "debt_only",
    "__skip_account__",
# Close the structure that was opened above.
}


# Define is skip account transaction for callers in this flow.
def is_skip_account_transaction(parsed: dict) -> bool:
    """Check whether a transaction must skip account balance mutation.

    Args:
        parsed: Parsed transaction payload. It may contain `skip_account=True`
            or a sentinel account name such as `Debt Only` or `tanpa rekening`.

    Returns:
        `True` when the row should still be written for audit/reporting but
        should not update any account balance.
    """
    account = str(parsed.get("account") or "").strip().lower()
    return bool(parsed.get("skip_account")) or account in SKIP_ACCOUNT_NAMES

# ── ID Generator ──────────────────────────────────────────────────────────────

# Define generate transaction id for callers in this flow.
def generate_transaction_id() -> str:
    """Generate a unique transaction ID for the transactions sheet.

    Returns:
        ID string with timestamp and random suffix, for example
        `txn_YYYYMMDD_HHMMSS_microseconds_xxxxxxxx`.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    # Prepare unique suffix for the next step.
    unique_suffix = uuid.uuid4().hex[:8]
    return f"txn_{timestamp}_{unique_suffix}"


# ── Row Builder ───────────────────────────────────────────────────────────────

# Define build transaction row for callers in this flow.
def build_transaction_row(parsed: dict, raw_input: str) -> tuple[str, list]:
    """Build a Google Sheets row for one confirmed transaction.

    Args:
        parsed: Confirmed transaction payload containing type, amount,
            category, account fields, debt metadata, and date.
        raw_input: Original user input stored for audit/debugging.

    Returns:
        Tuple of generated transaction ID and ordered row values matching the
        `transactions` sheet schema.

    Flow constraints:
        This function only builds row data. It does not validate accounts,
        mutate balances, or write to Google Sheets.
    """
    # Prepare txn id for the next step.
    txn_id = generate_transaction_id()

    txn_type = parsed.get("type") or ""
    amount = float(parsed.get("amount", 0) or 0)
    category = parsed.get("category") or ""
    account = parsed.get("account") or ""
    to_account = parsed.get("to_account") or ""
    subject = parsed.get("subject") or ""
    description = parsed.get("description") or ""
    catatan = parsed.get("catatan") or ""
    tipe_pengeluaran = parsed.get("tipe_pengeluaran") or ""
    date = parsed.get("date") or datetime.now().strftime("%Y-%m-%d")
    parsed_by = parsed.get("parsed_by") or "regex"
    hutang_id = parsed.get("hutang_id") or parsed.get("debt_id") or ""
    tipe_hutang = parsed.get("tipe_hutang") or parsed.get("debt_type_label") or ""

    # Open a multi-line structure for the values below.
    row = [
        # Include this value in the surrounding collection or call.
        txn_id,
        # Include this value in the surrounding collection or call.
        date,
        # Include this value in the surrounding collection or call.
        txn_type,
        # Include this value in the surrounding collection or call.
        amount,
        # Include this value in the surrounding collection or call.
        category,
        # Include this value in the surrounding collection or call.
        account,
        # Include this value in the surrounding collection or call.
        to_account,
        # Include this value in the surrounding collection or call.
        subject,
        # Include this value in the surrounding collection or call.
        description,
        # Include this value in the surrounding collection or call.
        catatan,
        # Include this value in the surrounding collection or call.
        tipe_pengeluaran,
        # Include this value in the surrounding collection or call.
        raw_input,
        # Include this value in the surrounding collection or call.
        parsed_by,
        # Include this value in the surrounding collection or call.
        hutang_id,
        # Include this value in the surrounding collection or call.
        tipe_hutang,
    # Close the structure that was opened above.
    ]

    # Return txn_id, row to the caller.
    return txn_id, row


# Define update transaction debt relation for callers in this flow.
def update_transaction_debt_relation(
    # Include this value in the surrounding collection or call.
    transaction_id: str,
    # Include this value in the surrounding collection or call.
    debt_ids: list[str],
    tipe_hutang: str = "piutang",
# Close the structure that was opened above.
) -> dict:
    """Apply the update transaction debt relation operation in the service layer.

    Args:
        transaction_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        debt_ids: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        tipe_hutang: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    transaction_id = str(transaction_id or "").strip()
    clean_debt_ids = [str(x).strip() for x in (debt_ids or []) if str(x or "").strip()]
    tipe_hutang = str(tipe_hutang or "").strip()

    # Handle the missing or empty transaction_id case.
    if not transaction_id:
        # Return { to the caller.
        return {
            "success": False,
            "message": "transaction_id kosong.",
        # Close the structure that was opened above.
        }

    # Handle the missing or empty clean_debt_ids case.
    if not clean_debt_ids:
        # Return { to the caller.
        return {
            "success": False,
            "message": "debt_ids kosong.",
        # Close the structure that was opened above.
        }

    # Prepare records for the next step.
    records = get_all_records(SHEET_TRANSACTIONS)

    # Process each row_index, record in the current collection.
    for row_index, record in enumerate(records, start=2):
        if str(record.get("id", "")).strip() == transaction_id:
            update_cell(SHEET_TRANSACTIONS, row_index, HUTANG_ID_COL, ", ".join(clean_debt_ids))
            # Run this statement as part of the current workflow.
            update_cell(SHEET_TRANSACTIONS, row_index, TIPE_HUTANG_COL, tipe_hutang)
            # Return { to the caller.
            return {
                "success": True,
                "message": "ok",
            # Close the structure that was opened above.
            }

    # Return { to the caller.
    return {
        "success": False,
        "message": f"Transaksi {transaction_id} tidak ditemukan.",
    # Close the structure that was opened above.
    }


# Define clear transaction debt relation for callers in this flow.
def clear_transaction_debt_relation(transaction_id: str) -> dict:
    """Remove debt metadata from one transaction row.

    Args:
        transaction_id: Full transaction ID from the `transactions` sheet.

    Returns:
        Result dict with `success` and `message`.

    Side effects:
        Clears `hutang_id` and `tipe_hutang` cells for the matching transaction.
    """
    transaction_id = str(transaction_id or "").strip()
    # Handle the missing or empty transaction_id case.
    if not transaction_id:
        return {"success": False, "message": "transaction_id kosong."}

    # Prepare records for the next step.
    records = get_all_records(SHEET_TRANSACTIONS)
    # Process each row_index, record in the current collection.
    for row_index, record in enumerate(records, start=2):
        if str(record.get("id", "")).strip() == transaction_id:
            update_cell(SHEET_TRANSACTIONS, row_index, HUTANG_ID_COL, "")
            update_cell(SHEET_TRANSACTIONS, row_index, TIPE_HUTANG_COL, "")
            return {"success": True, "message": "ok"}

    return {"success": False, "message": f"Transaksi {transaction_id} tidak ditemukan."}


# Define validate transaction for callers in this flow.
def validate_transaction(parsed: dict) -> tuple[bool, str]:
    """Validate data before it is used by transaction."""
    txn_type = str(parsed.get("type") or "").strip().lower()

    # Run this operation in a guarded block so failures can be handled.
    try:
        amount = float(parsed.get("amount", 0) or 0)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return False, "Nominal transaksi tidak valid."

    account = str(parsed.get("account") or "").strip()
    to_account = str(parsed.get("to_account") or "").strip()

    if txn_type not in ["expense", "income", "transfer", "debt_offset", "debt_only"]:
        return False, "Tipe transaksi tidak valid."

    # Account flow section
    parsed["type"] = txn_type

    # Handle the case where amount <= 0.
    if amount <= 0:
        return False, "Nominal transaksi tidak valid."

    # Prepare skip account for the next step.
    skip_account = is_skip_account_transaction(parsed)

    if txn_type in ["expense", "income"] and not account and not skip_account:
        return False, "Rekening wajib dipilih."

    if txn_type in ["debt_offset", "debt_only"]:
        parsed["skip_account"] = True
        parsed["account"] = account or ("Debt Offset" if txn_type == "debt_offset" else "Debt Only")

    if txn_type == "transfer":
        # Handle the case where skip_account.
        if skip_account:
            return False, "Transfer tetap wajib memilih rekening asal dan tujuan."

        # Handle the missing or empty account or not to_account case.
        if not account or not to_account:
            return False, "Transfer wajib punya rekening asal dan tujuan."

        # Handle the case where account.lower() == to_account.lower().
        if account.lower() == to_account.lower():
            return False, "Rekening asal dan tujuan tidak boleh sama."

    return True, "ok"


# Account flow section

# Define get account balance for callers in this flow.
def get_account_balance(account_name: str) -> float | None:
    """Read the current balance for one account.

    Args:
        account_name: Account name from transaction/account flow.

    Returns:
        Balance as float when the account exists, otherwise `None`.
    """
    # Prepare records for the next step.
    records = get_all_records(SHEET_ACCOUNTS)

    # Process each record in the current collection.
    for record in records:
        if str(record.get("account_name", "")).strip().lower() == str(account_name).strip().lower():
            return float(record.get("balance", 0) or 0)

    # Return None to the caller.
    return None


# Define update account balance for callers in this flow.
def update_account_balance(account_name: str, new_balance: float) -> bool:
    """Apply the update account balance operation in the service layer.

    Args:
        account_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        new_balance: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    # Prepare ACCOUNT NAME COL for the next step.
    ACCOUNT_NAME_COL = 1
    # Prepare BALANCE COL for the next step.
    BALANCE_COL = 3
    # Prepare LAST UPDATED COL for the next step.
    LAST_UPDATED_COL = 5

    # Prepare row index for the next step.
    row_index = find_row_index(SHEET_ACCOUNTS, ACCOUNT_NAME_COL, account_name)
    # Handle the missing or empty row_index case.
    if not row_index:
        # Return False to the caller.
        return False

    # Run this statement as part of the current workflow.
    update_cell(SHEET_ACCOUNTS, row_index, BALANCE_COL, new_balance)
    # Open a multi-line structure for the values below.
    update_cell(
        # Include this value in the surrounding collection or call.
        SHEET_ACCOUNTS,
        # Include this value in the surrounding collection or call.
        row_index,
        # Include this value in the surrounding collection or call.
        LAST_UPDATED_COL,
        datetime.now().strftime("%Y-%m-%d"),
    # Close the structure that was opened above.
    )
    # Return True to the caller.
    return True


# Define get all accounts for callers in this flow.
def get_all_accounts() -> list[dict]:
    """Read every account row from the accounts sheet."""
    # Return get_all_records(SHEET_ACCOUNTS) to the caller.
    return get_all_records(SHEET_ACCOUNTS)


# Define get account index map for callers in this flow.
def get_account_index_map() -> dict:
    """Build a lowercase account-name lookup with row and balance metadata.

    Returns:
        Dict keyed by normalized account name. Values include row index,
        canonical name, and current balance.
    """
    # Prepare records for the next step.
    records = get_all_records(SHEET_ACCOUNTS)
    # Prepare result for the next step.
    result = {}

    # Process each i, record in the current collection.
    for i, record in enumerate(records):
        name = str(record.get("account_name", "")).strip()
        # Handle the missing or empty name case.
        if not name:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Open a multi-line structure for the values below.
        result[name.lower()] = {
            "row": i + 2,  # +2 because row 1 is the header.
            "name": name,
            "balance": float(record.get("balance", 0) or 0),
        # Close the structure that was opened above.
        }

    # Return result to the caller.
    return result


# Define validate accounts exist for callers in this flow.
def validate_accounts_exist(account_deltas: dict) -> tuple[bool, list[str]]:
    """Validate data before it is used by accounts exist."""
    # Handle the missing or empty account_deltas case.
    if not account_deltas:
        # Return True, [] to the caller.
        return True, []

    # Prepare accounts map for the next step.
    accounts_map = get_account_index_map()
    # Prepare missing for the next step.
    missing = []

    # Process each account_name in the current collection.
    for account_name in account_deltas:
        key = str(account_name or "").strip().lower()
        # Handle the case where key and key not in accounts_map.
        if key and key not in accounts_map:
            # Update missing with the current value.
            missing.append(str(account_name))

    # Return len(missing) == 0, missing to the caller.
    return len(missing) == 0, missing


# Define calculate account deltas for callers in this flow.
def calculate_account_deltas(parsed_items: list[dict]) -> dict:
    """Coordinate the calculate account deltas logic in the service layer.

    Args:
        parsed_items: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare deltas for the next step.
    deltas = {}

    # Define add delta for callers in this flow.
    def add_delta(account_name: str, value: float):
        """Accumulate one account delta in the local delta map."""
        # Handle the missing or empty account_name case.
        if not account_name:
            # Return control to the caller.
            return

        # Prepare key for the next step.
        key = str(account_name).strip()
        # Handle the missing or empty key case.
        if not key:
            # Return control to the caller.
            return

        # Run this statement as part of the current workflow.
        deltas[key] = deltas.get(key, 0) + float(value)

    # Process each item in the current collection.
    for item in parsed_items:
        parsed = item["parsed"]
        txn_type = parsed.get("type")
        amount = float(parsed.get("amount", 0) or 0)
        account = parsed.get("account") or ""
        to_account = parsed.get("to_account") or ""

        # Handle the case where is_skip_account_transaction(parsed).
        if is_skip_account_transaction(parsed):
            # Skip the rest of this loop iteration after handling this case.
            continue

        if txn_type == "expense":
            # Run this statement as part of the current workflow.
            add_delta(account, -amount)

        elif txn_type == "income":
            # Run this statement as part of the current workflow.
            add_delta(account, amount)

        elif txn_type == "transfer":
            # Run this statement as part of the current workflow.
            add_delta(account, -amount)
            # Run this statement as part of the current workflow.
            add_delta(to_account, amount)

    # Return deltas to the caller.
    return deltas


# Define apply account deltas for callers in this flow.
def apply_account_deltas(account_deltas: dict) -> dict:
    """Coordinate the apply account deltas logic in the service layer.

    Args:
        account_deltas: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Handle the missing or empty account_deltas case.
    if not account_deltas:
        # Return { to the caller.
        return {
            "success": True,
            "new_balances": {},
            "failed_accounts": [],
        # Close the structure that was opened above.
        }

    # Prepare BALANCE COL for the next step.
    BALANCE_COL = 3
    # Prepare LAST UPDATED COL for the next step.
    LAST_UPDATED_COL = 5

    # Prepare accounts map for the next step.
    accounts_map = get_account_index_map()
    today = datetime.now().strftime("%Y-%m-%d")

    # Prepare new balances for the next step.
    new_balances = {}
    # Prepare failed accounts for the next step.
    failed_accounts = []

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Split bill parsing note: separate the paid transaction from each person share.
    for account_name in account_deltas:
        # Prepare account key for the next step.
        account_key = str(account_name).strip().lower()
        # Handle the case where account_key and account_key not in accounts_map.
        if account_key and account_key not in accounts_map:
            # Update failed accounts with the current value.
            failed_accounts.append(account_name)

    # Handle the case where failed_accounts.
    if failed_accounts:
        # Return { to the caller.
        return {
            "success": False,
            "new_balances": {},
            "failed_accounts": failed_accounts,
        # Close the structure that was opened above.
        }

    # Process each account_name, delta in the current collection.
    for account_name, delta in account_deltas.items():
        # Prepare account key for the next step.
        account_key = str(account_name).strip().lower()
        # Prepare account info for the next step.
        account_info = accounts_map.get(account_key)

        # Handle the missing or empty account_info case.
        if not account_info:
            # Account flow section
            failed_accounts.append(account_name)
            # Skip the rest of this loop iteration after handling this case.
            continue

        new_balance = account_info["balance"] + float(delta)

        update_cell(SHEET_ACCOUNTS, account_info["row"], BALANCE_COL, new_balance)
        update_cell(SHEET_ACCOUNTS, account_info["row"], LAST_UPDATED_COL, today)

        new_balances[account_info["name"]] = new_balance

    # Return { to the caller.
    return {
        "success": len(failed_accounts) == 0,
        "new_balances": new_balances,
        "failed_accounts": failed_accounts,
    # Close the structure that was opened above.
    }


# ── Core transaction functions ────────────────────────────────────────────────

# Define save transaction for callers in this flow.
def save_transaction(parsed: dict, raw_input: str) -> dict:
    """Save one confirmed transaction row and apply account deltas.

    Args:
        parsed: Parsed transaction payload after preview/confirmation. It must
            include a valid `type`, `amount`, and required account fields unless
            `skip_account` marks the row as audit-only.
        raw_input: Original user text stored in the transaction row.

    Returns:
        Result dict with save status, transaction id, message, new balance
        information, and account deltas. Validation failures return
        `success=False` before any row or balance update is attempted.
    """
    # Run this statement as part of the current workflow.
    is_valid, validation_message = validate_transaction(parsed)
    # Handle the missing or empty is_valid case.
    if not is_valid:
        # Return { to the caller.
        return {
            "success": False,
            "transaction_id": None,
            "message": validation_message,
            "new_balance": None,
            "new_balances": {},
        # Close the structure that was opened above.
        }

    if parsed.get("type") in {"expense", "income"}:
        parsed["category"] = ensure_category_for_transaction(parsed.get("category"), parsed.get("type"))

    # Open a multi-line structure for the values below.
    deltas = calculate_account_deltas([
        # Open a multi-line structure for the values below.
        {
            "parsed": parsed,
            "raw": raw_input,
        # Close the structure that was opened above.
        }
    # Close the structure that was opened above.
    ])
    # Run this statement as part of the current workflow.
    accounts_ok, missing_accounts = validate_accounts_exist(deltas)
    # Handle the missing or empty accounts_ok case.
    if not accounts_ok:
        # Return { to the caller.
        return {
            "success": False,
            "transaction_id": None,
            "message": "Rekening tidak ditemukan: " + ", ".join(missing_accounts),
            "new_balance": None,
            "new_balances": {},
        # Close the structure that was opened above.
        }

    # Run this statement as part of the current workflow.
    txn_id, row = build_transaction_row(parsed, raw_input)

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Run this statement as part of the current workflow.
        append_row(SHEET_TRANSACTIONS, row)
        # Run this statement as part of the current workflow.
        sort_transactions_sheet_by_date(desc=True)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "transaction_id": None,
            "message": f"Gagal menyimpan transaksi: {str(e)}",
            "new_balance": None,
            "new_balances": {},
        # Close the structure that was opened above.
        }

    # Prepare new balance for the next step.
    new_balance = None
    # Prepare new balance account for the next step.
    new_balance_account = None

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare balance result for the next step.
        balance_result = apply_account_deltas(deltas)

        if parsed.get("type") == "transfer":
            new_balance_account = parsed.get("to_account") or parsed.get("account")
        # Handle the fallback path after earlier conditions are skipped.
        else:
            new_balance_account = parsed.get("account") or parsed.get("to_account")

        # Handle the case where new_balance_account.
        if new_balance_account:
            for name, balance in balance_result.get("new_balances", {}).items():
                # Handle the case where str(name).lower() == str(new_balance_account).lower().
                if str(name).lower() == str(new_balance_account).lower():
                    # Prepare new balance for the next step.
                    new_balance = balance
                    # Prepare new balance account for the next step.
                    new_balance_account = name
                    # Leave the loop after the target condition has been reached.
                    break

        if balance_result.get("failed_accounts"):
            # Return { to the caller.
            return {
                "success": True,
                "transaction_id": txn_id,
                "message": (
                    "⚠️ Transaksi tersimpan, tapi saldo rekening berikut gagal diupdate: "
                    + ", ".join(balance_result["failed_accounts"])
                # Close the structure that was opened above.
                ),
                "new_balance": new_balance,
                "new_balance_account": new_balance_account,
                "new_balances": balance_result.get("new_balances", {}),
            # Close the structure that was opened above.
            }

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": True,
            "transaction_id": txn_id,
            "message": f"⚠️ Transaksi tersimpan, tapi saldo gagal diupdate: {str(e)}",
            "new_balance": None,
            "new_balances": {},
        # Close the structure that was opened above.
        }

    # Return { to the caller.
    return {
        "success": True,
        "transaction_id": txn_id,
        "message": "ok",
        "new_balance": new_balance,
        "new_balance_account": new_balance_account,
        "new_balances": balance_result.get("new_balances", {}) if "balance_result" in locals() else {},
        "account_deltas": deltas,
    # Close the structure that was opened above.
    }


# Define save transactions batch for callers in this flow.
def save_transactions_batch(parsed_items: list[dict]) -> dict:
    """Save confirmed transaction rows as a batch and apply combined deltas.

    Args:
        parsed_items: List of dicts with `parsed` payload and original `raw`
            input. Each item is validated before rows are appended.

    Returns:
        Batch result containing success count, failed item details, saved ids,
        new balances, and account deltas. Invalid items are skipped instead of
        being written.
    """
    # Handle the missing or empty parsed_items case.
    if not parsed_items:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Tidak ada transaksi untuk disimpan.",
            "success_count": 0,
            "failed_items": [],
            "saved_ids": [],
            "new_balances": {},
        # Close the structure that was opened above.
        }

    # Prepare valid items for the next step.
    valid_items = []
    # Prepare failed items for the next step.
    failed_items = []
    # Prepare rows for the next step.
    rows = []
    # Prepare saved ids for the next step.
    saved_ids = []

    # Process each item in the current collection.
    for item in parsed_items:
        parsed = item["parsed"]
        raw = item["raw"]

        # Run this statement as part of the current workflow.
        is_valid, validation_message = validate_transaction(parsed)
        # Handle the missing or empty is_valid case.
        if not is_valid:
            # Open a multi-line structure for the values below.
            failed_items.append({
                "raw": raw,
                "message": validation_message,
            # Close the structure that was opened above.
            })
            # Skip the rest of this loop iteration after handling this case.
            continue

        if parsed.get("type") in {"expense", "income"}:
            parsed["category"] = ensure_category_for_transaction(parsed.get("category"), parsed.get("type"))

        # Run this statement as part of the current workflow.
        txn_id, row = build_transaction_row(parsed, raw)
        # Update saved ids with the current value.
        saved_ids.append(txn_id)
        # Update rows with the current value.
        rows.append(row)
        # Update valid items with the current value.
        valid_items.append(item)

    # Handle the missing or empty rows case.
    if not rows:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Semua transaksi gagal divalidasi.",
            "success_count": 0,
            "failed_items": failed_items,
            "saved_ids": [],
            "new_balances": {},
        # Close the structure that was opened above.
        }

    # Prepare deltas for the next step.
    deltas = calculate_account_deltas(valid_items)
    # Run this statement as part of the current workflow.
    accounts_ok, missing_accounts = validate_accounts_exist(deltas)
    # Handle the missing or empty accounts_ok case.
    if not accounts_ok:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Rekening tidak ditemukan: " + ", ".join(missing_accounts),
            "success_count": 0,
            "failed_items": failed_items + [
                # Open a multi-line structure for the values below.
                {
                    "raw": "validasi rekening",
                    "message": "Rekening tidak ditemukan: " + ", ".join(missing_accounts),
                # Close the structure that was opened above.
                }
            # Close the structure that was opened above.
            ],
            "saved_ids": [],
            "new_balances": {},
        # Close the structure that was opened above.
        }

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Run this statement as part of the current workflow.
        append_rows(SHEET_TRANSACTIONS, rows)
        # Run this statement as part of the current workflow.
        sort_transactions_sheet_by_date(desc=True)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": f"Gagal menyimpan batch transaksi: {str(e)}",
            "success_count": 0,
            "failed_items": [
                # Open a multi-line structure for the values below.
                {
                    "raw": item["raw"],
                    "message": str(e),
                # Close the structure that was opened above.
                }
                # Process each item in the current collection.
                for item in valid_items
            # Close the structure that was opened above.
            ] + failed_items,
            "saved_ids": [],
            "new_balances": {},
        # Close the structure that was opened above.
        }

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare balance result for the next step.
        balance_result = apply_account_deltas(deltas)

        if balance_result.get("failed_accounts"):
            # Open a multi-line structure for the values below.
            failed_items.append({
                "raw": "update saldo",
                "message": (
                    "Saldo gagal diupdate untuk rekening: "
                    + ", ".join(balance_result["failed_accounts"])
                # Close the structure that was opened above.
                ),
            # Close the structure that was opened above.
            })

        # Return { to the caller.
        return {
            "success": True,
            "message": "ok",
            "success_count": len(valid_items),
            "failed_items": failed_items,
            "saved_ids": saved_ids,
            "new_balances": balance_result.get("new_balances", {}),
            "account_deltas": deltas,
        # Close the structure that was opened above.
        }

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": True,
            "message": f"⚠️ Transaksi tersimpan, tapi saldo gagal diupdate: {str(e)}",
            "success_count": len(valid_items),
            "failed_items": failed_items + [
                # Open a multi-line structure for the values below.
                {
                    "raw": "update saldo",
                    "message": str(e),
                # Close the structure that was opened above.
                }
            # Close the structure that was opened above.
            ],
            "saved_ids": saved_ids,
            "new_balances": {},
        # Close the structure that was opened above.
        }


# ── Query functions ───────────────────────────────────────────────────────────

# Define get transactions by month for callers in this flow.
def get_transactions_by_month(year: int, month: int) -> list[dict]:
    """Read transactions whose date starts with the requested year-month."""
    # Prepare records for the next step.
    records = get_all_records(SHEET_TRANSACTIONS)
    prefix = f"{year}-{month:02d}"
    return [r for r in records if str(r.get("date", "")).startswith(prefix)]


# Define get transactions by date for callers in this flow.
def get_transactions_by_date(date_str: str) -> list[dict]:
    """Read transactions whose sheet date exactly matches `date_str`."""
    # Prepare records for the next step.
    records = get_all_records(SHEET_TRANSACTIONS)
    return [r for r in records if r.get("date") == date_str]


# Define get expense by category for callers in this flow.
def get_expense_by_category(year: int, month: int) -> dict:
    """Aggregate gross expense amount by category for one month."""
    # Prepare transactions for the next step.
    transactions = get_transactions_by_month(year, month)
    # Prepare result for the next step.
    result = {}

    # Process each txn in the current collection.
    for txn in transactions:
        if txn.get("type") != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue

        cat = txn.get("category") or "Other Expense"
        amount = float(txn.get("amount", 0) or 0)
        # Run this statement as part of the current workflow.
        result[cat] = result.get(cat, 0) + amount

    # Return result to the caller.
    return result

# Define is debt cashflow transaction for callers in this flow.
def is_debt_cashflow_transaction(txn: dict) -> bool:
    """Check whether a condition is true for debt cashflow transaction."""
    category = str(txn.get("category", "")).strip()
    parsed_by = str(txn.get("parsed_by", "")).strip().lower()

    return category in DEBT_CASHFLOW_CATEGORIES or parsed_by == "debt"


# Define parse transaction date for callers in this flow.
def parse_transaction_date(date_value: str):
    """Parse a transaction date string into a date object.

    Args:
        date_value: Sheet value expected as `YYYY-MM-DD`.

    Returns:
        `datetime.date` when valid, otherwise `None`.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        return datetime.strptime(str(date_value), "%Y-%m-%d").date()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return None to the caller.
        return None


# Define sort transactions sheet by date for callers in this flow.
def sort_transactions_sheet_by_date(desc: bool = True) -> dict:
    """Sort the transactions sheet by date while preserving stable row order.

    Args:
        desc: Whether newest transactions should appear first.

    Returns:
        Result dict with `success` and `message`.

    Side effects:
        Rewrites the transaction data rows in sorted order.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare sheet for the next step.
        sheet = get_sheet(SHEET_TRANSACTIONS)
        # Prepare values for the next step.
        values = sheet.get_all_values()

        # Handle the case where len(values) <= 2.
        if len(values) <= 2:
            return {"success": True, "message": "Tidak cukup row untuk sort."}

        # Prepare header for the next step.
        header = values[0]
        # Prepare rows for the next step.
        rows = values[1:]
        # Prepare col count for the next step.
        col_count = len(header)

        # Prepare normalized rows for the next step.
        normalized_rows = []
        # Process each idx, row in the current collection.
        for idx, row in enumerate(rows):
            padded = list(row) + [""] * max(0, col_count - len(row))
            # Prepare padded for the next step.
            padded = padded[:col_count]
            date_obj = parse_transaction_date(padded[1] if len(padded) > 1 else "")
            # Update normalized rows with the current value.
            normalized_rows.append((idx, date_obj or datetime.min.date(), padded))

        # Open a multi-line structure for the values below.
        normalized_rows.sort(
            # Prepare key for the next step.
            key=lambda item: (item[1], item[0]),
            # Prepare reverse for the next step.
            reverse=desc,
        # Close the structure that was opened above.
        )

        # Prepare sorted rows for the next step.
        sorted_rows = [item[2] for item in normalized_rows]
        end_col = chr(ord("A") + col_count - 1)
        sheet.update(f"A2:{end_col}{len(sorted_rows) + 1}", sorted_rows)

        return {"success": True, "message": "transactions sorted by date"}

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {"success": False, "message": str(e)}


# Define get transactions with row index for callers in this flow.
def get_transactions_with_row_index() -> list[dict]:
    """Read transactions and attach their one-based sheet row index."""
    # Prepare records for the next step.
    records = get_all_records(SHEET_TRANSACTIONS)
    # Prepare result for the next step.
    result = []

    # Process each i, record in the current collection.
    for i, record in enumerate(records):
        # Prepare item for the next step.
        item = dict(record)
        item["_row_index"] = i + 2
        # Update result with the current value.
        result.append(item)

    # Return result to the caller.
    return result

# Define get recent transactions for callers in this flow.
def get_recent_transactions(
    # Include this value in the surrounding collection or call.
    limit: int = 10,
    # Include this value in the surrounding collection or call.
    period: str | None = None,
    # Include this value in the surrounding collection or call.
    month: str | None = None,
# Close the structure that was opened above.
) -> list[dict]:
    """Read recent transactions with optional period/month filtering.

    Args:
        limit: Maximum number of rows returned.
        period: Optional shortcut filter: `today`, `week`, or `month`.
        month: Optional explicit `YYYY-MM` filter.

    Returns:
        Newest matching transactions, each with `_row_index`.
    """
    # Prepare records for the next step.
    records = get_transactions_with_row_index()
    # Prepare today for the next step.
    today = datetime.now().date()

    # Handle the case where month.
    if month:
        # Open a multi-line structure for the values below.
        records = [
            # Run this statement as part of the current workflow.
            r for r in records
            if str(r.get("date", "")).startswith(month)
        # Close the structure that was opened above.
        ]

    elif period == "today":
        today_str = today.strftime("%Y-%m-%d")
        # Open a multi-line structure for the values below.
        records = [
            # Run this statement as part of the current workflow.
            r for r in records
            if str(r.get("date", "")) == today_str
        # Close the structure that was opened above.
        ]

    elif period == "week":
        # Prepare start week for the next step.
        start_week = today - timedelta(days=today.weekday())
        # Prepare end week for the next step.
        end_week = start_week + timedelta(days=6)

        # Prepare filtered for the next step.
        filtered = []
        # Process each r in the current collection.
        for r in records:
            txn_date = parse_transaction_date(r.get("date", ""))
            # Handle the case where txn_date and start_week <= txn_date <= end_week.
            if txn_date and start_week <= txn_date <= end_week:
                # Update filtered with the current value.
                filtered.append(r)

        # Prepare records for the next step.
        records = filtered

    elif period == "month":
        month_now = today.strftime("%Y-%m")
        # Open a multi-line structure for the values below.
        records = [
            # Run this statement as part of the current workflow.
            r for r in records
            if str(r.get("date", "")).startswith(month_now)
        # Close the structure that was opened above.
        ]

    # Open a multi-line structure for the values below.
    records = sorted(
        # Include this value in the surrounding collection or call.
        records,
        # Open a multi-line structure for the values below.
        key=lambda x: (
            parse_transaction_date(x.get("date", "")) or datetime.min.date(),
            int(x.get("_row_index", 0)),
        # Close the structure that was opened above.
        ),
        # Prepare reverse for the next step.
        reverse=True,
    # Close the structure that was opened above.
    )

    # Return records[:limit] to the caller.
    return records[:limit]

# Define get transaction by id for callers in this flow.
def get_transaction_by_id(txn_id: str) -> dict | None:
    """Retrieve data needed by the get transaction by id workflow in the service layer.

    Args:
        txn_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare records for the next step.
    records = get_transactions_with_row_index()

    # Process each record in the current collection.
    for record in records:
        if str(record.get("id", "")).strip() == str(txn_id).strip():
            # Return record to the caller.
            return record

    # Return None to the caller.
    return None


# Define get transactions by ids for callers in this flow.
def get_transactions_by_ids(txn_ids: list[str]) -> list[dict]:
    """Read transactions whose IDs are in the requested list."""
    # Prepare target ids for the next step.
    target_ids = {str(x).strip() for x in txn_ids if str(x).strip()}
    # Prepare records for the next step.
    records = get_transactions_with_row_index()

    # Return [ to the caller.
    return [
        # Run this statement as part of the current workflow.
        r for r in records
        if str(r.get("id", "")).strip() in target_ids
    # Close the structure that was opened above.
    ]

# Define get transactions by row indices for callers in this flow.
def get_transactions_by_row_indices(row_indices: list[int]) -> list[dict]:
    """Read transactions whose sheet row indexes are requested."""
    # Prepare target rows for the next step.
    target_rows = {int(x) for x in row_indices}
    # Prepare records for the next step.
    records = get_transactions_with_row_index()

    # Return [ to the caller.
    return [
        # Run this statement as part of the current workflow.
        r for r in records
        if int(r.get("_row_index", 0)) in target_rows
    # Close the structure that was opened above.
    ]


# Define calculate reverse deltas for delete for callers in this flow.
def calculate_reverse_deltas_for_delete(transactions: list[dict]) -> dict:
    """Calculate derived values for reverse deltas for delete."""
    # Prepare deltas for the next step.
    deltas = {}

    # Define add delta for callers in this flow.
    def add_delta(account_name: str, value: float):
        """Coordinate the add delta logic in the service layer.

        Args:
            account_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
            value: Raw value supplied by the caller.

        Returns:
            `None` after completing the operation.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
        """
        # Handle the missing or empty account_name case.
        if not account_name:
            # Return control to the caller.
            return

        # Prepare key for the next step.
        key = str(account_name).strip()
        # Handle the missing or empty key case.
        if not key:
            # Return control to the caller.
            return

        # Run this statement as part of the current workflow.
        deltas[key] = deltas.get(key, 0) + float(value)

    # Process each txn in the current collection.
    for txn in transactions:
        txn_type = str(txn.get("type", "")).strip()
        amount = float(txn.get("amount", 0) or 0)
        account = str(txn.get("account", "")).strip()
        to_account = str(txn.get("to_account", "")).strip()

        # Handle the case where is_skip_account_transaction(txn).
        if is_skip_account_transaction(txn):
            # Skip the rest of this loop iteration after handling this case.
            continue

        if txn_type == "expense":
            # Run this statement as part of the current workflow.
            add_delta(account, amount)

        elif txn_type == "income":
            # Run this statement as part of the current workflow.
            add_delta(account, -amount)

        elif txn_type == "transfer":
            # Run this statement as part of the current workflow.
            add_delta(account, amount)
            # Run this statement as part of the current workflow.
            add_delta(to_account, -amount)

    # Return deltas to the caller.
    return deltas


# Define parse transaction debt ids for callers in this flow.
def parse_transaction_debt_ids(txn: dict) -> list[str]:
    """Parse linked debt IDs from a transaction record.

    Args:
        txn: Transaction record containing `hutang_id`.

    Returns:
        Clean debt ID list split from comma, semicolon, or whitespace
        separators.
    """
    raw = str(txn.get("hutang_id", "") or "").strip()
    # Handle the missing or empty raw case.
    if not raw:
        # Return [] to the caller.
        return []
    return [part.strip() for part in re.split(r"[,;\s]+", raw) if part.strip()]


# Define transaction has debt relation for callers in this flow.
def transaction_has_debt_relation(txn: dict) -> bool:
    """Check whether a transaction carries debt linkage metadata.

    Args:
        txn: Transaction record from the `transactions` sheet.

    Returns:
        `True` when `hutang_id` contains IDs or `tipe_hutang` is filled.
    """
    return bool(parse_transaction_debt_ids(txn)) or bool(str(txn.get("tipe_hutang", "") or "").strip())


# Define preview delete transactions by refs for callers in this flow.
def preview_delete_transactions_by_refs(
    # Include this value in the surrounding collection or call.
    row_indices: list[int] | None = None,
    # Include this value in the surrounding collection or call.
    txn_ids: list[str] | None = None,
# Close the structure that was opened above.
) -> dict:
    """Preview deleting transactions by row numbers and/or transaction IDs.

    Args:
        row_indices: Optional one-based sheet row indexes from user refs.
        txn_ids: Optional transaction IDs.

    Returns:
        Dict containing found/deletable/blocked transactions, missing refs, and
        reverse account deltas needed if the delete is confirmed.

    Flow constraints:
        This is preview-only. It must not delete rows, reverse debt, or update
        balances before the bot shows confirmation.
    """
    # Prepare row indices for the next step.
    row_indices = row_indices or []
    # Prepare txn ids for the next step.
    txn_ids = txn_ids or []

    # Prepare by rows for the next step.
    by_rows = get_transactions_by_row_indices(row_indices) if row_indices else []
    # Prepare by ids for the next step.
    by_ids = get_transactions_by_ids(txn_ids) if txn_ids else []

    # Prepare transactions for the next step.
    transactions = []
    # Prepare seen rows for the next step.
    seen_rows = set()

    # Process each txn in the current collection.
    for txn in by_rows + by_ids:
        row_index = int(txn.get("_row_index", 0))
        # Handle the case where row_index and row_index not in seen_rows.
        if row_index and row_index not in seen_rows:
            # Update transactions with the current value.
            transactions.append(txn)
            # Update seen rows with the current value.
            seen_rows.add(row_index)

    found_rows = {int(t.get("_row_index", 0)) for t in by_rows}
    # Prepare requested rows for the next step.
    requested_rows = {int(x) for x in row_indices}
    # Prepare missing rows for the next step.
    missing_rows = sorted(requested_rows - found_rows)

    found_ids = {str(t.get("id", "")).strip() for t in by_ids}
    # Prepare requested ids for the next step.
    requested_ids = {str(x).strip() for x in txn_ids if str(x).strip()}
    # Prepare missing ids for the next step.
    missing_ids = sorted(requested_ids - found_ids)

    # Prepare blocked for the next step.
    blocked = []
    # Prepare deletable for the next step.
    deletable = []

    # Process each txn in the current collection.
    for txn in transactions:
        # Handle the case where is_debt_cashflow_transaction(txn) and not transaction_has_deb....
        if is_debt_cashflow_transaction(txn) and not transaction_has_debt_relation(txn):
            # Update blocked with the current value.
            blocked.append(txn)
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Update deletable with the current value.
            deletable.append(txn)

    # Prepare reverse deltas for the next step.
    reverse_deltas = calculate_reverse_deltas_for_delete(deletable)

    # Return { to the caller.
    return {
        "success": True,
        "requested_count": len(row_indices) + len(txn_ids),
        "found_count": len(transactions),
        "deletable": deletable,
        "blocked": blocked,
        "missing_ids": missing_ids,
        "missing_rows": missing_rows,
        "reverse_deltas": reverse_deltas,
    # Close the structure that was opened above.
    }

# Define preview delete transactions for callers in this flow.
def preview_delete_transactions(txn_ids: list[str]) -> dict:
    """Preview deleting transactions by transaction ID.

    Args:
        txn_ids: Transaction IDs requested by the user.

    Returns:
        Dict containing deletable/blocked transactions, missing IDs, and
        reverse account deltas for final confirmation.

    Flow constraints:
        This is read-only preview logic and must not mutate Sheets.
    """
    # Prepare transactions for the next step.
    transactions = get_transactions_by_ids(txn_ids)
    found_ids = {str(t.get("id", "")).strip() for t in transactions}
    # Prepare requested ids for the next step.
    requested_ids = {str(x).strip() for x in txn_ids}

    # Prepare missing ids for the next step.
    missing_ids = sorted(requested_ids - found_ids)

    # Prepare blocked for the next step.
    blocked = []
    # Prepare deletable for the next step.
    deletable = []

    # Process each txn in the current collection.
    for txn in transactions:
        # Handle the case where is_debt_cashflow_transaction(txn) and not transaction_has_deb....
        if is_debt_cashflow_transaction(txn) and not transaction_has_debt_relation(txn):
            # Update blocked with the current value.
            blocked.append(txn)
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Update deletable with the current value.
            deletable.append(txn)

    # Prepare reverse deltas for the next step.
    reverse_deltas = calculate_reverse_deltas_for_delete(deletable)

    # Return { to the caller.
    return {
        "success": True,
        "requested_count": len(txn_ids),
        "found_count": len(transactions),
        "deletable": deletable,
        "blocked": blocked,
        "missing_ids": missing_ids,
        "reverse_deltas": reverse_deltas,
    # Close the structure that was opened above.
    }


# Define delete transactions by ids for callers in this flow.
def delete_transactions_by_ids(txn_ids: list[str]) -> dict:
    """Apply the delete transactions by ids operation in the service layer.

    Args:
        txn_ids: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    # Prepare preview for the next step.
    preview = preview_delete_transactions(txn_ids)

    deletable = preview["deletable"]
    blocked = preview["blocked"]
    missing_ids = preview["missing_ids"]

    # Handle the missing or empty deletable case.
    if not deletable:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Tidak ada transaksi yang bisa dihapus.",
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "new_balances": {},
        # Close the structure that was opened above.
        }

    reverse_deltas = preview["reverse_deltas"]

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare balance result for the next step.
        balance_result = apply_account_deltas(reverse_deltas)
        if balance_result.get("failed_accounts"):
            # Return { to the caller.
            return {
                "success": False,
                "message": "Rekening tidak ditemukan: " + ", ".join(balance_result["failed_accounts"]),
                "deleted_count": 0,
                "deleted_ids": [],
                "blocked": blocked,
                "missing_ids": missing_ids,
                "new_balances": {},
            # Close the structure that was opened above.
            }
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": f"Gagal reverse saldo: {str(e)}",
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "new_balances": {},
        # Close the structure that was opened above.
        }

    # Prepare linked debt voided ids for the next step.
    linked_debt_voided_ids = []
    # Prepare reversed payment debt items for the next step.
    reversed_payment_debt_items = []
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Import app.services.debt_service so this module can use its helpers.
        from app.services.debt_service import void_debts_for_transaction, reverse_debt_payment_transaction

        # Process each txn in the current collection.
        for txn in deletable:
            txn_id = str(txn.get("id", "") or "").strip()
            # Prepare linked ids for the next step.
            linked_ids = parse_transaction_debt_ids(txn)
            category = str(txn.get("category", "") or "").strip()

            # Account flow section
            # Debt flow section
            if category in {"Pembayaran Piutang", "Bayar Utang"}:
                # Prepare reverse result for the next step.
                reverse_result = reverse_debt_payment_transaction(txn)
                if not reverse_result.get("success"):
                    # Return { to the caller.
                    return {
                        "success": False,
                        "message": reverse_result.get("message", "Gagal membalik pembayaran debt terkait transaksi."),
                        "deleted_count": 0,
                        "deleted_ids": [],
                        "blocked": blocked,
                        "missing_ids": missing_ids,
                        "new_balances": balance_result.get("new_balances", {}),
                    # Close the structure that was opened above.
                    }
                reversed_payment_debt_items.extend(reverse_result.get("reversed", []))
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Handle the missing or empty txn_id and not linked_ids case.
            if not txn_id and not linked_ids:
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Prepare linked result for the next step.
            linked_result = void_debts_for_transaction(txn_id, linked_ids)
            if not linked_result.get("success"):
                # Return { to the caller.
                return {
                    "success": False,
                    "message": linked_result.get("message", "Gagal void debt terkait transaksi."),
                    "deleted_count": 0,
                    "deleted_ids": [],
                    "blocked": blocked,
                    "missing_ids": missing_ids,
                    "new_balances": balance_result.get("new_balances", {}),
                # Close the structure that was opened above.
                }
            linked_debt_voided_ids.extend(linked_result.get("voided_ids", []))
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": f"Gagal sync debt terkait transaksi: {str(e)}",
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "new_balances": balance_result.get("new_balances", {}),
        # Close the structure that was opened above.
        }

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Open a multi-line structure for the values below.
        row_indices = [
            int(txn["_row_index"])
            # Process each txn in the current collection.
            for txn in deletable
            if txn.get("_row_index")
        # Close the structure that was opened above.
        ]

        # Run this statement as part of the current workflow.
        delete_rows(SHEET_TRANSACTIONS, row_indices)

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": (
                "Saldo sudah sempat direverse, tapi row transaksi gagal dihapus. "
                f"Cek manual di sheet. Error: {str(e)}"
            # Close the structure that was opened above.
            ),
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "new_balances": balance_result.get("new_balances", {}),
        # Close the structure that was opened above.
        }

    # Open a multi-line structure for the values below.
    deleted_ids = [
        str(txn.get("id", ""))
        # Process each txn in the current collection.
        for txn in deletable
    # Close the structure that was opened above.
    ]

    # Return { to the caller.
    return {
        "success": True,
        "message": "ok",
        "deleted_count": len(deletable),
        "deleted_ids": deleted_ids,
        "blocked": blocked,
        "missing_ids": missing_ids,
        "new_balances": balance_result.get("new_balances", {}),
        "linked_debts_voided": linked_debt_voided_ids,
        "reversed_payment_debts": reversed_payment_debt_items,
    # Close the structure that was opened above.
    }

# Define delete transactions by refs for callers in this flow.
def delete_transactions_by_refs(
    # Include this value in the surrounding collection or call.
    row_indices: list[int] | None = None,
    # Include this value in the surrounding collection or call.
    txn_ids: list[str] | None = None,
# Close the structure that was opened above.
) -> dict:
    """Apply the delete transactions by refs operation in the service layer.

    Args:
        row_indices: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        txn_ids: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    # Prepare preview for the next step.
    preview = preview_delete_transactions_by_refs(row_indices, txn_ids)

    deletable = preview["deletable"]
    blocked = preview["blocked"]
    missing_ids = preview.get("missing_ids", [])
    missing_rows = preview.get("missing_rows", [])

    # Handle the missing or empty deletable case.
    if not deletable:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Tidak ada transaksi yang bisa dihapus.",
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "missing_rows": missing_rows,
            "new_balances": {},
        # Close the structure that was opened above.
        }

    reverse_deltas = preview["reverse_deltas"]

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare balance result for the next step.
        balance_result = apply_account_deltas(reverse_deltas)
        if balance_result.get("failed_accounts"):
            # Return { to the caller.
            return {
                "success": False,
                "message": "Rekening tidak ditemukan: " + ", ".join(balance_result["failed_accounts"]),
                "deleted_count": 0,
                "deleted_ids": [],
                "blocked": blocked,
                "missing_ids": missing_ids,
                "missing_rows": missing_rows,
                "new_balances": {},
            # Close the structure that was opened above.
            }
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": f"Gagal reverse saldo: {str(e)}",
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "missing_rows": missing_rows,
            "new_balances": {},
        # Close the structure that was opened above.
        }

    # Prepare linked debt voided ids for the next step.
    linked_debt_voided_ids = []
    # Prepare reversed payment debt items for the next step.
    reversed_payment_debt_items = []
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Import app.services.debt_service so this module can use its helpers.
        from app.services.debt_service import void_debts_for_transaction, reverse_debt_payment_transaction

        # Process each txn in the current collection.
        for txn in deletable:
            txn_id = str(txn.get("id", "") or "").strip()
            # Prepare linked ids for the next step.
            linked_ids = parse_transaction_debt_ids(txn)
            category = str(txn.get("category", "") or "").strip()

            if category in {"Pembayaran Piutang", "Bayar Utang"}:
                # Prepare reverse result for the next step.
                reverse_result = reverse_debt_payment_transaction(txn)
                if not reverse_result.get("success"):
                    # Return { to the caller.
                    return {
                        "success": False,
                        "message": reverse_result.get("message", "Gagal membalik pembayaran debt terkait transaksi."),
                        "deleted_count": 0,
                        "deleted_ids": [],
                        "blocked": blocked,
                        "missing_ids": missing_ids,
                        "missing_rows": missing_rows,
                        "new_balances": balance_result.get("new_balances", {}),
                    # Close the structure that was opened above.
                    }
                reversed_payment_debt_items.extend(reverse_result.get("reversed", []))
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Handle the missing or empty txn_id and not linked_ids case.
            if not txn_id and not linked_ids:
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Prepare linked result for the next step.
            linked_result = void_debts_for_transaction(txn_id, linked_ids)
            if not linked_result.get("success"):
                # Return { to the caller.
                return {
                    "success": False,
                    "message": linked_result.get("message", "Gagal void debt terkait transaksi."),
                    "deleted_count": 0,
                    "deleted_ids": [],
                    "blocked": blocked,
                    "missing_ids": missing_ids,
                    "missing_rows": missing_rows,
                    "new_balances": balance_result.get("new_balances", {}),
                # Close the structure that was opened above.
                }
            linked_debt_voided_ids.extend(linked_result.get("voided_ids", []))
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": f"Gagal sync debt terkait transaksi: {str(e)}",
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "missing_rows": missing_rows,
            "new_balances": balance_result.get("new_balances", {}),
        # Close the structure that was opened above.
        }

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Open a multi-line structure for the values below.
        delete_row_indices = [
            int(txn["_row_index"])
            # Process each txn in the current collection.
            for txn in deletable
            if txn.get("_row_index")
        # Close the structure that was opened above.
        ]

        # Run this statement as part of the current workflow.
        delete_rows(SHEET_TRANSACTIONS, delete_row_indices)

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": (
                "Saldo sudah sempat direverse, tapi row transaksi gagal dihapus. "
                f"Cek manual di sheet. Error: {str(e)}"
            # Close the structure that was opened above.
            ),
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "missing_rows": missing_rows,
            "new_balances": balance_result.get("new_balances", {}),
        # Close the structure that was opened above.
        }

    # Open a multi-line structure for the values below.
    deleted_ids = [
        str(txn.get("id", ""))
        # Process each txn in the current collection.
        for txn in deletable
    # Close the structure that was opened above.
    ]

    # Return { to the caller.
    return {
        "success": True,
        "message": "ok",
        "deleted_count": len(deletable),
        "deleted_ids": deleted_ids,
        "blocked": blocked,
        "missing_ids": missing_ids,
        "missing_rows": missing_rows,
        "new_balances": balance_result.get("new_balances", {}),
        "linked_debts_voided": linked_debt_voided_ids,
        "reversed_payment_debts": reversed_payment_debt_items,
    # Close the structure that was opened above.
    }

# Open a multi-line structure for the values below.
TRANSACTION_COLUMNS = [
    "id",
    "date",
    "type",
    "amount",
    "category",
    "account",
    "to_account",
    "subject",
    "description",
    "catatan",
    "tipe_pengeluaran",
    "raw_input",
    "parsed_by",
    "hutang_id",
    "tipe_hutang",
# Close the structure that was opened above.
]


# Open a multi-line structure for the values below.
EDITABLE_TRANSACTION_FIELDS = {
    "date",
    "type",
    "amount",
    "category",
    "account",
    "to_account",
    "subject",
    "description",
    "catatan",
    "tipe_pengeluaran",
# Close the structure that was opened above.
}


# Open a multi-line structure for the values below.
FIELD_ALIASES = {
    "desc": "description",
    "deskripsi": "description",
    "description": "description",
    "deskripsinya": "description",
    "keterangan": "description",
    "ket": "description",

    "note": "catatan",
    "notes": "catatan",
    "catatan": "catatan",
    "catatannya": "catatan",

    "rekening": "account",
    "akun": "account",
    "account": "account",
    "dari": "account",
    "rekening_asal": "account",

    "to": "to_account",
    "to_account": "to_account",
    "ke": "to_account",
    "tujuan": "to_account",
    "rekening_tujuan": "to_account",

    "kategori": "category",
    "category": "category",

    "nominal": "amount",
    "amount": "amount",
    "jumlah": "amount",
    "harga": "amount",
    "jadi": "amount",

    "tipe": "type",
    "type": "type",

    "tanggal": "date",
    "date": "date",

    "subject": "subject",
    "subjek": "subject",
    "orang": "subject",

    "tipe_pengeluaran": "tipe_pengeluaran",
    "jenis_pengeluaran": "tipe_pengeluaran",
# Close the structure that was opened above.
}


# Define normalize edit field for callers in this flow.
def normalize_edit_field(field: str) -> str | None:
    """Normalize input values for the normalize edit field workflow in the service layer.

    Args:
        field: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    key = str(field or "").strip().lower()

    # Split bill parsing note: separate the paid transaction from each person share.
    # Account flow section
    if key in EDITABLE_TRANSACTION_FIELDS:
        # Return key to the caller.
        return key

    # Return FIELD_ALIASES.get(key) to the caller.
    return FIELD_ALIASES.get(key)


# Define normalize edit updates for callers in this flow.
def normalize_edit_updates(updates: dict) -> dict:
    """Normalize input values for the normalize edit updates workflow in the service layer.

    Args:
        updates: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare normalized for the next step.
    normalized = {}

    # Process each raw_field, value in the current collection.
    for raw_field, value in updates.items():
        # Prepare field for the next step.
        field = normalize_edit_field(raw_field)

        # Handle the missing or empty field case.
        if not field:
            raise ValueError(f"Field `{raw_field}` tidak dikenali.")

        # Handle the case where field not in EDITABLE_TRANSACTION_FIELDS.
        if field not in EDITABLE_TRANSACTION_FIELDS:
            raise ValueError(f"Field `{field}` tidak boleh diedit.")

        if field == "amount":
            # Prepare parsed amount for the next step.
            parsed_amount = extract_amount_from_text(str(value))
            # Handle the case where parsed_amount is not None.
            if parsed_amount is not None:
                # Prepare value for the next step.
                value = float(parsed_amount)
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Run this operation in a guarded block so failures can be handled.
                try:
                    # Prepare value for the next step.
                    value = float(value)
                # Handle an expected failure from the guarded operation above.
                except Exception:
                    raise ValueError("Amount harus berupa angka. Contoh: 500k atau 500000.")

            # Handle the case where value <= 0.
            if value <= 0:
                raise ValueError("Amount harus lebih dari 0.")

        elif field == "type":
            # Prepare value for the next step.
            value = str(value).strip().lower()

            if value not in ["expense", "income", "transfer"]:
                raise ValueError("Type harus salah satu: expense, income, transfer.")

        elif field == "date":
            # Prepare value for the next step.
            value = str(value).strip()

            # Run this operation in a guarded block so failures can be handled.
            try:
                datetime.strptime(value, "%Y-%m-%d")
            # Handle an expected failure from the guarded operation above.
            except Exception:
                raise ValueError("Date harus format YYYY-MM-DD. Contoh: 2026-06-10.")

        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Prepare value for the next step.
            value = str(value).strip()

        # Run this statement as part of the current workflow.
        normalized[field] = value

    # Return normalized to the caller.
    return normalized


# Define get single transaction by ref for callers in this flow.
def get_single_transaction_by_ref(
    # Include this value in the surrounding collection or call.
    row_index: int | None = None,
    # Include this value in the surrounding collection or call.
    txn_id: str | None = None,
# Close the structure that was opened above.
) -> dict | None:
    """Resolve one transaction from either row index or transaction ID.

    Args:
        row_index: Optional one-based sheet row reference.
        txn_id: Optional transaction ID reference.

    Returns:
        Matching transaction dict, or `None` when not found.

    Raises:
        ValueError when a transaction ID unexpectedly matches multiple rows.
    """
    # Handle the case where row_index.
    if row_index:
        # Prepare matches for the next step.
        matches = get_transactions_by_row_indices([row_index])
        # Return matches[0] if matches else None to the caller.
        return matches[0] if matches else None

    # Handle the case where txn_id.
    if txn_id:
        # Prepare matches for the next step.
        matches = get_transactions_by_ids([txn_id])

        # Handle the case where len(matches) == 1.
        if len(matches) == 1:
            # Return matches[0] to the caller.
            return matches[0]

        # Handle the case where len(matches) > 1.
        if len(matches) > 1:
            # Raise a clear error so the caller can stop this invalid flow.
            raise ValueError(
                "Transaction ID ini duplikat. Gunakan nomor dari /last agar spesifik."
            # Close the structure that was opened above.
            )

    # Return None to the caller.
    return None


# Define build transaction row from record for callers in this flow.
def build_transaction_row_from_record(txn: dict) -> list:
    """Convert a transaction record dict back into sheet row order."""
    # Return [ to the caller.
    return [
        txn.get("id", ""),
        txn.get("date", ""),
        txn.get("type", ""),
        float(txn.get("amount", 0) or 0),
        txn.get("category", ""),
        txn.get("account", ""),
        txn.get("to_account", ""),
        txn.get("subject", ""),
        txn.get("description", ""),
        txn.get("catatan", ""),
        txn.get("tipe_pengeluaran", ""),
        txn.get("raw_input", ""),
        txn.get("parsed_by", ""),
        txn.get("hutang_id", ""),
        txn.get("tipe_hutang", ""),
    # Close the structure that was opened above.
    ]


# Define calculate account effect for callers in this flow.
def calculate_account_effect(txn: dict) -> dict:
    """Coordinate the calculate account effect logic in the service layer.

    Args:
        txn: Transaction dict or transaction-like row from the finance data layer.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare deltas for the next step.
    deltas = {}

    # Define add delta for callers in this flow.
    def add_delta(account_name: str, value: float):
        """Accumulate one account effect delta for a transaction."""
        # Handle the missing or empty account_name case.
        if not account_name:
            # Return control to the caller.
            return

        # Prepare key for the next step.
        key = str(account_name).strip()
        # Handle the missing or empty key case.
        if not key:
            # Return control to the caller.
            return

        # Run this statement as part of the current workflow.
        deltas[key] = deltas.get(key, 0) + float(value)

    txn_type = str(txn.get("type", "")).strip()
    amount = float(txn.get("amount", 0) or 0)
    account = str(txn.get("account", "")).strip()
    to_account = str(txn.get("to_account", "")).strip()

    # Handle the case where is_skip_account_transaction(txn).
    if is_skip_account_transaction(txn):
        # Return deltas to the caller.
        return deltas

    if txn_type == "expense":
        # Run this statement as part of the current workflow.
        add_delta(account, -amount)

    elif txn_type == "income":
        # Run this statement as part of the current workflow.
        add_delta(account, amount)

    elif txn_type == "transfer":
        # Run this statement as part of the current workflow.
        add_delta(account, -amount)
        # Run this statement as part of the current workflow.
        add_delta(to_account, amount)

    # Return deltas to the caller.
    return deltas


# Define calculate edit net deltas for callers in this flow.
def calculate_edit_net_deltas(old_txn: dict, new_txn: dict) -> dict:
    """Coordinate the calculate edit net deltas logic in the service layer.

    Args:
        old_txn: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        new_txn: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare old effect for the next step.
    old_effect = calculate_account_effect(old_txn)
    # Prepare new effect for the next step.
    new_effect = calculate_account_effect(new_txn)

    # Prepare accounts for the next step.
    accounts = set(old_effect.keys()) | set(new_effect.keys())
    # Prepare result for the next step.
    result = {}

    # Process each account in the current collection.
    for account in accounts:
        # Prepare delta for the next step.
        delta = -old_effect.get(account, 0) + new_effect.get(account, 0)

        # Handle the case where delta != 0.
        if delta != 0:
            # Run this statement as part of the current workflow.
            result[account] = delta

    # Return result to the caller.
    return result


# Define validate edit transaction for callers in this flow.
def validate_edit_transaction(txn: dict) -> tuple[bool, str]:
    """Validate data before it is used by edit transaction."""
    txn_type = str(txn.get("type", "")).strip()
    amount = float(txn.get("amount", 0) or 0)
    account = str(txn.get("account", "")).strip()
    to_account = str(txn.get("to_account", "")).strip()

    if txn_type not in ["expense", "income", "transfer"]:
        return False, "Type transaksi tidak valid."

    # Handle the case where amount <= 0.
    if amount <= 0:
        return False, "Amount harus lebih dari 0."

    if txn_type in ["expense", "income"] and not account:
        return False, "Expense/income wajib punya account."

    if txn_type == "transfer":
        # Handle the missing or empty account or not to_account case.
        if not account or not to_account:
            return False, "Transfer wajib punya account dan to_account."

        # Handle the case where account.lower() == to_account.lower().
        if account.lower() == to_account.lower():
            return False, "Account asal dan tujuan transfer tidak boleh sama."

    return True, "ok"


# Define preview edit transaction by ref for callers in this flow.
def preview_edit_transaction_by_ref(
    # Include this value in the surrounding collection or call.
    updates: dict,
    # Include this value in the surrounding collection or call.
    row_index: int | None = None,
    # Include this value in the surrounding collection or call.
    txn_id: str | None = None,
# Close the structure that was opened above.
) -> dict:
    """Preview editing one transaction and calculate balance deltas.

    Args:
        updates: Raw field updates requested by the user.
        row_index: Optional sheet row reference.
        txn_id: Optional transaction ID reference.

    Returns:
        Success dict with old/new transaction records, normalized updates, and
        net account deltas; or failure dict with a user-facing message.

    Flow constraints:
        This function must stay preview-only. It intentionally blocks unsafe
        debt cashflow edits that could desync `transactions` and `debts`.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare normalized updates for the next step.
        normalized_updates = normalize_edit_updates(updates)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": str(e),
        # Close the structure that was opened above.
        }

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare old txn for the next step.
        old_txn = get_single_transaction_by_ref(row_index=row_index, txn_id=txn_id)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": str(e),
        # Close the structure that was opened above.
        }

    # Handle the missing or empty old_txn case.
    if not old_txn:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Transaksi tidak ditemukan.",
        # Close the structure that was opened above.
        }

    old_payment_category = str(old_txn.get("category", "") or "").strip()
    if old_payment_category in {"Pembayaran Piutang", "Bayar Utang"}:
        # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
        # Debt flow section
        if set(normalized_updates.keys()) != {"amount"}:
            # Return { to the caller.
            return {
                "success": False,
                "message": (
                    "Transaksi pembayaran hutang/piutang hanya boleh diedit nominalnya. "
                    "Untuk koreksi lain, pakai /delete_txn lalu input ulang."
                # Close the structure that was opened above.
                ),
            # Close the structure that was opened above.
            }

    # Prepare old has debt relation for the next step.
    old_has_debt_relation = transaction_has_debt_relation(old_txn)

    # Debt flow section
    # Debt flow section
    # Account flow section
    if is_debt_cashflow_transaction(old_txn) and not old_has_debt_relation:
        # Return { to the caller.
        return {
            "success": False,
            "message": (
                "Transaksi debt cashflow tanpa hutang_id belum boleh diedit dari fitur ini "
                "supaya sheet debts tidak inkonsisten."
            # Close the structure that was opened above.
            ),
        # Close the structure that was opened above.
        }

    # Prepare new txn for the next step.
    new_txn = dict(old_txn)

    # Process each field, value in the current collection.
    for field, value in normalized_updates.items():
        # Run this statement as part of the current workflow.
        new_txn[field] = value

    # Run this statement as part of the current workflow.
    is_valid, validation_message = validate_edit_transaction(new_txn)

    # Handle the missing or empty is_valid case.
    if not is_valid:
        # Return { to the caller.
        return {
            "success": False,
            "message": validation_message,
        # Close the structure that was opened above.
        }

    # Prepare reverse deltas for the next step.
    reverse_deltas = calculate_edit_net_deltas(old_txn, new_txn)

    # Return { to the caller.
    return {
        "success": True,
        "message": "ok",
        "old_txn": old_txn,
        "new_txn": new_txn,
        "updates": normalized_updates,
        "net_deltas": reverse_deltas,
    # Close the structure that was opened above.
    }



def _payment_allocation_note(raw: str, allocations: list[dict], overpayment: float = 0.0, policy: str = "") -> str:
    """Build a reversible debt payment allocation note.

    Args:
        raw: Existing raw input or note text.
        allocations: Debt allocation dicts containing `debt_id` and `amount`.
        overpayment: Optional overpaid amount created by the payment flow.
        policy: Optional overpayment policy label.

    Returns:
        Compact note string that can later be parsed to reverse debt payment
        effects when a transaction is deleted or edited.
    """
    parts = [str(raw or "").strip()]
    # Prepare alloc parts for the next step.
    alloc_parts = []
    # Process each item in the current collection.
    for item in allocations or []:
        debt_id = str(item.get("debt_id") or "").strip()
        amount = item.get("amount")
        # Handle the case where debt_id and amount is not None.
        if debt_id and amount is not None:
            alloc_parts.append(f"{debt_id}:{float(amount)}")
    # Handle the case where alloc_parts.
    if alloc_parts:
        parts.append("debt_allocations=" + ";".join(alloc_parts))
    # Handle the case where overpayment.
    if overpayment:
        parts.append(f"overpayment={float(overpayment)}")
    # Handle the case where policy.
    if policy:
        parts.append(f"overpayment_policy={policy}")
    return " | ".join([p for p in parts if p]).strip(" |")


# Define edit debt payment transaction amount for callers in this flow.
def edit_debt_payment_transaction_amount(preview: dict) -> dict:
    """Apply an approved amount edit for a debt payment transaction.

    Args:
        preview: Successful payload from `preview_edit_transaction_by_ref`.

    Returns:
        Result dict with updated transaction data, account deltas, new balances,
        and debt payment reallocation details.

    Side effects:
        Reverses the old debt payment allocation, allocates the new amount,
        applies account balance delta, updates the transaction row, and resorts
        the transaction sheet.

    Flow constraints:
        Caller must obtain explicit user confirmation before invoking this
        writer because it mutates debts, transactions, and balances.
    """
    old_txn = preview["old_txn"]
    new_txn = preview["new_txn"]
    net_deltas = preview["net_deltas"]
    category = str(old_txn.get("category", "") or "").strip()
    person = str(old_txn.get("subject", "") or "").strip()
    # Handle the missing or empty person case.
    if not person:
        return {"success": False, "message": "Subject/person transaksi payment kosong."}

    target_debt_type = "receivable" if category == "Pembayaran Piutang" else "payable"
    new_amount = float(new_txn.get("amount", 0) or 0)
    raw_note = str(old_txn.get("raw_input", "") or old_txn.get("catatan", "") or "")

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Import app.services.debt_service so this module can use its helpers.
        from app.services.debt_service import reverse_debt_payment_transaction, add_payment_by_person
        # Prepare reverse result for the next step.
        reverse_result = reverse_debt_payment_transaction(old_txn)
        if not reverse_result.get("success"):
            return {"success": False, "message": reverse_result.get("message", "Gagal reverse payment lama.")}

        # Open a multi-line structure for the values below.
        payment_result = add_payment_by_person(
            # Include this value in the surrounding collection or call.
            person,
            # Include this value in the surrounding collection or call.
            new_amount,
            note=f"Edit payment dari transaksi {old_txn.get('id') or '-'}",
            # Prepare target debt type for the next step.
            target_debt_type=target_debt_type,
            overpayment_policy="opposite_debt",
        # Close the structure that was opened above.
        )
        if not payment_result.get("success"):
            return {"success": False, "message": payment_result.get("message", "Gagal alokasi payment baru.")}
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {"success": False, "message": f"Gagal sync debt payment: {str(e)}"}

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare balance result for the next step.
        balance_result = apply_account_deltas(net_deltas)
        if balance_result.get("failed_accounts"):
            return {"success": False, "message": "Rekening tidak ditemukan: " + ", ".join(balance_result["failed_accounts"])}
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {"success": False, "message": f"Gagal update saldo: {str(e)}"}

    # Run this operation in a guarded block so failures can be handled.
    try:
        target_row_index = int(old_txn.get("_row_index"))
        new_txn["id"] = old_txn.get("id")
        new_txn["hutang_id"] = ", ".join([x for x in payment_result.get("affected_debt_ids") or [] if x])
        new_txn["tipe_hutang"] = "piutang" if target_debt_type == "receivable" else "utang"
        new_txn["catatan"] = _payment_allocation_note(
            # Include this value in the surrounding collection or call.
            raw_note,
            payment_result.get("allocations") or [],
            overpayment=float(payment_result.get("overpayment", 0) or 0),
            policy=str(payment_result.get("overpayment_policy") or "opposite_debt"),
        # Close the structure that was opened above.
        )
        old_raw = str(old_txn.get("raw_input", "") or "")
        new_txn["raw_input"] = old_raw if "[edited]" in old_raw else f"{old_raw} [edited]".strip()
        # Run this statement as part of the current workflow.
        update_row(SHEET_TRANSACTIONS, target_row_index, build_transaction_row_from_record(new_txn))
        # Run this statement as part of the current workflow.
        sort_transactions_sheet_by_date(desc=True)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Saldo/debt sudah sempat berubah, tapi update row transaksi gagal. Cek manual. Error: " + str(e),
            "new_balances": balance_result.get("new_balances", {}),
        # Close the structure that was opened above.
        }

    # Return { to the caller.
    return {
        "success": True,
        "message": "ok",
        "old_txn": old_txn,
        "new_txn": new_txn,
        "net_deltas": net_deltas,
        "new_balances": balance_result.get("new_balances", {}),
        "debt_sync": {"success": True, "payment_reallocated": True, "payment_result": payment_result},
    # Close the structure that was opened above.
    }

# Define edit transaction by ref for callers in this flow.
def edit_transaction_by_ref(
    # Include this value in the surrounding collection or call.
    updates: dict,
    # Include this value in the surrounding collection or call.
    row_index: int | None = None,
    # Include this value in the surrounding collection or call.
    txn_id: str | None = None,
# Close the structure that was opened above.
) -> dict:
    """Apply an approved edit to one transaction reference.

    Args:
        updates: Raw field updates requested by the user.
        row_index: Optional sheet row reference.
        txn_id: Optional transaction ID reference.

    Returns:
        Result dict from the edit operation, including updated transaction data
        and account balance effects when applicable.

    Side effects:
        Mutates the transaction row and account balances after validation. Debt
        payment transactions are delegated to debt-aware edit logic.
    """
    # Open a multi-line structure for the values below.
    preview = preview_edit_transaction_by_ref(
        # Prepare updates for the next step.
        updates=updates,
        # Prepare row index for the next step.
        row_index=row_index,
        # Prepare txn id for the next step.
        txn_id=txn_id,
    # Close the structure that was opened above.
    )

    if not preview.get("success"):
        # Return preview to the caller.
        return preview

    old_txn = preview["old_txn"]
    new_txn = preview["new_txn"]
    net_deltas = preview["net_deltas"]

    old_payment_category = str(old_txn.get("category", "") or "").strip()
    if old_payment_category in {"Pembayaran Piutang", "Bayar Utang"}:
        # Return edit_debt_payment_transaction_amount(preview) to the caller.
        return edit_debt_payment_transaction_amount(preview)

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare balance result for the next step.
        balance_result = apply_account_deltas(net_deltas)
        if balance_result.get("failed_accounts"):
            # Return { to the caller.
            return {
                "success": False,
                "message": "Rekening tidak ditemukan: " + ", ".join(balance_result["failed_accounts"]),
            # Close the structure that was opened above.
            }
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": f"Gagal update saldo: {str(e)}",
        # Close the structure that was opened above.
        }

    # Run this operation in a guarded block so failures can be handled.
    try:
        target_row_index = int(old_txn.get("_row_index"))

        # Account flow section
        new_txn["id"] = old_txn.get("id")

        # Implementation note for this project-specific finance flow.
        old_raw = str(old_txn.get("raw_input", "") or "")
        if "[edited]" not in old_raw:
            new_txn["raw_input"] = f"{old_raw} [edited]".strip()
        # Handle the fallback path after earlier conditions are skipped.
        else:
            new_txn["raw_input"] = old_raw

        # Prepare row values for the next step.
        row_values = build_transaction_row_from_record(new_txn)

        # Run this statement as part of the current workflow.
        update_row(SHEET_TRANSACTIONS, target_row_index, row_values)
        # Run this statement as part of the current workflow.
        sort_transactions_sheet_by_date(desc=True)

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": (
                "Saldo sudah sempat berubah, tapi update row transaksi gagal. "
                f"Cek manual di sheet. Error: {str(e)}"
            # Close the structure that was opened above.
            ),
            "new_balances": balance_result.get("new_balances", {}),
        # Close the structure that was opened above.
        }

    debt_sync_result = {"success": True, "updated": [], "overpaid": []}
    # Handle the case where transaction_has_debt_relation(old_txn) or transaction_has_deb....
    if transaction_has_debt_relation(old_txn) or transaction_has_debt_relation(new_txn):
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Import app.services.debt_service so this module can use its helpers.
            from app.services.debt_service import sync_debt_charges_from_transaction_edit

            # Prepare debt sync result for the next step.
            debt_sync_result = sync_debt_charges_from_transaction_edit(old_txn, new_txn)
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            # Open a multi-line structure for the values below.
            debt_sync_result = {
                "success": False,
                "message": str(e),
                "updated": [],
                "overpaid": [],
            # Close the structure that was opened above.
            }

    # Return { to the caller.
    return {
        "success": True,
        "message": "ok" if debt_sync_result.get("success") else "Transaksi diedit, tapi sync debt perlu dicek: " + str(debt_sync_result.get("message") or "-"),
        "old_txn": old_txn,
        "new_txn": new_txn,
        "net_deltas": net_deltas,
        "new_balances": balance_result.get("new_balances", {}),
        "debt_sync": debt_sync_result,
    # Close the structure that was opened above.
    }
