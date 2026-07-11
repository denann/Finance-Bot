"""Transaction service for saving, editing, deleting, batching, account balance updates, and debt relation updates."""


# Import datetime so this module can use its helpers.
from datetime import datetime, timedelta
from app.clock import business_now
# Import re for this module's local operations.
import re
# Import uuid for this module's local operations.
import uuid

# Import app.nlp.normalizer so this module can use its helpers.
from app.nlp.normalizer import extract_amount_from_text
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import ensure_category_for_transaction
from app.services.operation_errors import PartialMutationError, require_success_after_write

# Import app.config so this module can use its helpers.
from app.config import SHEET_ACCOUNTS, SHEET_TRANSACTIONS
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import (
    SheetsAtomicWriteError,
    append_row,
    append_rows,
    delete_rows,
    find_row_index,
    get_all_records,
    get_sheet,
    get_current_sheets_transaction,
    rollback_current_sheets_transaction,
    update_cell,
    update_row,
)


def _post_write_failure_result(error: Exception, *, batch: bool = False, candidate_ids: list[str] | None = None) -> dict:
    """Return an explicit failed/unknown outcome after a mutation started.

    Args:
        error: Failure raised after at least one logical write was attempted.
        batch: Whether to build the batch-shaped result contract.
        candidate_ids: Pre-generated transaction IDs used only for manual
            reconciliation. They are never reported as successfully saved.

    Returns:
        Backward-compatible result dictionary with ``success=False`` plus
        explicit commit, rollback, and reconciliation states.

    Side effects:
        If an active in-memory Sheets transaction has not already rolled back,
        it is rolled back before the result is returned. No new write occurs.
    """

    rollback_ok: bool | None = None
    if isinstance(error, SheetsAtomicWriteError):
        rollback_ok = error.rollback_ok

    transaction = get_current_sheets_transaction()
    if transaction is not None and not transaction.rolled_back:
        rollback_ok = rollback_current_sheets_transaction()

    if rollback_ok is True:
        commit_status = "commit_failed"
        rollback_status = "rollback_succeeded"
        reconciliation_required = False
        message = "Penyimpanan gagal dan seluruh perubahan operasi ini sudah dibatalkan. Tidak ada transaksi yang dinyatakan tersimpan."
    elif rollback_ok is False:
        commit_status = "commit_outcome_unknown"
        rollback_status = "rollback_failed"
        reconciliation_required = True
        message = "Hasil penyimpanan tidak dapat dipastikan karena rollback gagal. Jangan ulangi sebelum data direkonsiliasi."
    else:
        commit_status = "commit_outcome_unknown"
        rollback_status = "rollback_not_verified"
        reconciliation_required = True
        message = "Hasil penyimpanan tidak dapat dipastikan. Jangan ulangi sebelum data direkonsiliasi."

    common = {
        "success": False,
        "message": message,
        "commit_status": commit_status,
        "rollback_status": rollback_status,
        "reconciliation_required": reconciliation_required,
        "candidate_transaction_ids": list(candidate_ids or []),
    }
    if batch:
        return {
            **common,
            "success_count": 0,
            "failed_items": [{"raw": "commit transaksi", "message": str(error)}],
            "saved_ids": [],
            "new_balances": {},
        }
    return {
        **common,
        "transaction_id": None,
        "new_balance": None,
        "new_balances": {},
    }

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
]

# Schema compatibility note for Google Sheets headers and rows.
HUTANG_ID_COL = 14
TIPE_HUTANG_COL = 15


# Helper for get current month str.
def get_current_month_str() -> str:
    """Return the current local month in `YYYY-MM` format."""
    return business_now().strftime("%Y-%m")


# Helper for normalize export period.
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
    today = business_now().date()

    # Validate missing period before continuing.
    if not period:
        month = get_current_month_str()
        return {
            "type": "month",
            "label": f"bulan {month}",
            "filename_suffix": month,
            "month": month,
            "date_from": None,
            "date_to": None,
        }

    # Normalize clean before matching.
    clean = str(period).strip().lower()

    if clean in ["today", "hariini", "harian", "hari"]:
        today_str = today.strftime("%Y-%m-%d")
        return {
            "type": "date_range",
            "label": f"hari ini ({today_str})",
            "filename_suffix": today_str,
            "month": None,
            "date_from": today,
            "date_to": today,
        }

    if clean in ["week", "minggu", "mingguan"]:
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)

        return {
            "type": "date_range",
            "label": f"minggu ini ({start_week} s/d {end_week})",
            "filename_suffix": f"{start_week}_to_{end_week}",
            "month": None,
            "date_from": start_week,
            "date_to": end_week,
        }

    if clean in ["month", "bulan", "bulanan"]:
        month = get_current_month_str()
        return {
            "type": "month",
            "label": f"bulan {month}",
            "filename_suffix": month,
            "month": month,
            "date_from": None,
            "date_to": None,
        }

    match = re.fullmatch(r"(20\d{2})[-/](0?[1-9]|1[0-2])", clean)
    if match:
        year = match.group(1)
        month_num = int(match.group(2))
        month = f"{year}-{month_num:02d}"

        return {
            "type": "month",
            "label": f"bulan {month}",
            "filename_suffix": month,
            "month": month,
            "date_from": None,
            "date_to": None,
        }

    # Raise a clear error so the caller can stop this invalid flow.
    raise ValueError(
        "Format export tidak dikenali. Gunakan: /download_data, /download_data today, /download_data week, /download_data month, atau /download_data 2026-06."
    )


# Helper for parse date safe.
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
        return None


# Helper for get transactions for export.
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
        filter_info = normalize_export_period(period)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {
            "success": False,
            "records": [],
            "filter": {},
            "summary": {},
            "message": str(e),
        }

    # Load records for the current calculation.
    records = get_all_records(SHEET_TRANSACTIONS)
    filtered = []

    # Iterate through each record.
    for record in records:
        txn_date_raw = str(record.get("date", "")).strip()

        if filter_info["type"] == "month":
            if txn_date_raw.startswith(filter_info["month"]):
                # Append the current value to filtered.
                filtered.append(record)

        elif filter_info["type"] == "date_range":
            # Extract txn date for validation.
            txn_date = parse_date_safe(txn_date_raw)

            # Validate missing txn date before continuing.
            if not txn_date:
                # Skip the rest of this loop iteration after handling this case.
                continue

            if filter_info["date_from"] <= txn_date <= filter_info["date_to"]:
                # Append the current value to filtered.
                filtered.append(record)

    total_income = 0.0
    total_expense = 0.0
    total_transfer = 0.0

    # Iterate through each record.
    for record in filtered:
        txn_type = str(record.get("type", "")).strip()
        amount = float(record.get("amount", 0) or 0)

        if txn_type == "income":
            total_income += amount
        elif txn_type == "expense":
            total_expense += amount
        elif txn_type == "transfer":
            total_transfer += amount

    summary = {
        "count": len(filtered),
        "total_income": total_income,
        "total_expense": total_expense,
        "total_transfer": total_transfer,
        "net": total_income - total_expense,
    }

    return {
        "success": True,
        "records": filtered,
        "filter": filter_info,
        "summary": summary,
        "message": "ok",
    }

DEBT_CASHFLOW_CATEGORIES = {
    "Piutang Diberikan",
    "Pembayaran Piutang",
    "Penerimaan Utang",
    "Bayar Utang",
}

SKIP_ACCOUNT_NAMES = {
    "sudah berlalu",
    "tanpa rekening",
    "tidak masuk rekening",
    "jangan ubah saldo",
    "ditalangin",
    "debt only",
    "debt_only",
    "__skip_account__",
}


# Helper for is skip account transaction.
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

# Helper for generate transaction id.
def generate_transaction_id() -> str:
    """Generate a unique transaction ID for the transactions sheet.

    Returns:
        ID string with timestamp and random suffix, for example
        `txn_YYYYMMDD_HHMMSS_microseconds_xxxxxxxx`.
    """
    timestamp = business_now().strftime("%Y%m%d_%H%M%S_%f")
    unique_suffix = uuid.uuid4().hex[:8]
    return f"txn_{timestamp}_{unique_suffix}"


# ── Row Builder ───────────────────────────────────────────────────────────────

# Helper for build transaction row.
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
    date = parsed.get("date") or business_now().strftime("%Y-%m-%d")
    parsed_by = parsed.get("parsed_by") or "regex"
    hutang_id = parsed.get("hutang_id") or parsed.get("debt_id") or ""
    tipe_hutang = parsed.get("tipe_hutang") or parsed.get("debt_type_label") or ""

    row = [
        txn_id,
        date,
        txn_type,
        amount,
        category,
        account,
        to_account,
        subject,
        description,
        catatan,
        tipe_pengeluaran,
        raw_input,
        parsed_by,
        hutang_id,
        tipe_hutang,
    ]

    return txn_id, row


# Helper for update transaction debt relation.
def update_transaction_debt_relation(
    transaction_id: str,
    debt_ids: list[str],
    tipe_hutang: str = "piutang",
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

    # Validate missing transaction id before continuing.
    if not transaction_id:
        return {
            "success": False,
            "message": "transaction_id kosong.",
        }

    # Validate missing clean debt ids before continuing.
    if not clean_debt_ids:
        return {
            "success": False,
            "message": "debt_ids kosong.",
        }

    # Load records for the current calculation.
    records = get_all_records(SHEET_TRANSACTIONS)

    # Iterate through each row index, record.
    for row_index, record in enumerate(records, start=2):
        if str(record.get("id", "")).strip() == transaction_id:
            update_cell(SHEET_TRANSACTIONS, row_index, HUTANG_ID_COL, ", ".join(clean_debt_ids))
            update_cell(SHEET_TRANSACTIONS, row_index, TIPE_HUTANG_COL, tipe_hutang)
            return {
                "success": True,
                "message": "ok",
            }

    return {
        "success": False,
        "message": f"Transaksi {transaction_id} tidak ditemukan.",
    }


# Helper for clear transaction debt relation.
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
    # Validate missing transaction id before continuing.
    if not transaction_id:
        return {"success": False, "message": "transaction_id kosong."}

    # Load records for the current calculation.
    records = get_all_records(SHEET_TRANSACTIONS)
    # Iterate through each row index, record.
    for row_index, record in enumerate(records, start=2):
        if str(record.get("id", "")).strip() == transaction_id:
            update_cell(SHEET_TRANSACTIONS, row_index, HUTANG_ID_COL, "")
            update_cell(SHEET_TRANSACTIONS, row_index, TIPE_HUTANG_COL, "")
            return {"success": True, "message": "ok"}

    return {"success": False, "message": f"Transaksi {transaction_id} tidak ditemukan."}


# Helper for validate transaction.
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

    if amount <= 0:
        return False, "Nominal transaksi tidak valid."

    # Extract skip account for validation.
    skip_account = is_skip_account_transaction(parsed)

    if txn_type in ["expense", "income"] and not account and not skip_account:
        return False, "Rekening wajib dipilih."

    if txn_type in ["debt_offset", "debt_only"]:
        parsed["skip_account"] = True
        parsed["account"] = account or ("Debt Offset" if txn_type == "debt_offset" else "Debt Only")

    if txn_type == "transfer":
        if skip_account:
            return False, "Transfer tetap wajib memilih rekening asal dan tujuan."

        # Validate missing account or not to account before continuing.
        if not account or not to_account:
            return False, "Transfer wajib punya rekening asal dan tujuan."

        if account.lower() == to_account.lower():
            return False, "Rekening asal dan tujuan tidak boleh sama."

    return True, "ok"


# Account flow section

# Helper for get account balance.
def get_account_balance(account_name: str) -> float | None:
    """Read the current balance for one account.

    Args:
        account_name: Account name from transaction/account flow.

    Returns:
        Balance as float when the account exists, otherwise `None`.
    """
    # Load records for the current calculation.
    records = get_all_records(SHEET_ACCOUNTS)

    # Iterate through each record.
    for record in records:
        if str(record.get("account_name", "")).strip().lower() == str(account_name).strip().lower():
            return float(record.get("balance", 0) or 0)

    return None


# Helper for update account balance.
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
    # Extract ACCOUNT NAME COL for validation.
    ACCOUNT_NAME_COL = 1
    BALANCE_COL = 3
    # Extract LAST UPDATED COL for validation.
    LAST_UPDATED_COL = 5

    row_index = find_row_index(SHEET_ACCOUNTS, ACCOUNT_NAME_COL, account_name)
    # Validate missing row index before continuing.
    if not row_index:
        return False

    update_cell(SHEET_ACCOUNTS, row_index, BALANCE_COL, new_balance)
    update_cell(
        SHEET_ACCOUNTS,
        row_index,
        LAST_UPDATED_COL,
        business_now().strftime("%Y-%m-%d"),
    )
    return True


# Helper for get all accounts.
def get_all_accounts() -> list[dict]:
    """Read every account row from the accounts sheet."""
    return get_all_records(SHEET_ACCOUNTS)


# Helper for get account index map.
def get_account_index_map() -> dict:
    """Build a lowercase account-name lookup with row and balance metadata.

    Returns:
        Dict keyed by normalized account name. Values include row index,
        canonical name, and current balance.
    """
    # Load records for the current calculation.
    records = get_all_records(SHEET_ACCOUNTS)
    # Build result for the response flow.
    result = {}

    # Iterate through each i, record.
    for i, record in enumerate(records):
        name = str(record.get("account_name", "")).strip()
        # Validate missing name before continuing.
        if not name:
            # Skip the rest of this loop iteration after handling this case.
            continue

        result[name.lower()] = {
            "row": i + 2,  # +2 because row 1 is the header.
            "name": name,
            "balance": float(record.get("balance", 0) or 0),
        }

    return result


# Helper for validate accounts exist.
def validate_accounts_exist(account_deltas: dict) -> tuple[bool, list[str]]:
    """Validate data before it is used by accounts exist."""
    # Validate missing account deltas before continuing.
    if not account_deltas:
        return True, []

    # Extract accounts map for validation.
    accounts_map = get_account_index_map()
    missing = []

    # Iterate through each account name.
    for account_name in account_deltas:
        key = str(account_name or "").strip().lower()
        # Handle key and key not in accounts map.
        if key and key not in accounts_map:
            # Append the current value to missing.
            missing.append(str(account_name))

    return len(missing) == 0, missing


# Helper for calculate account deltas.
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
    deltas = {}

    # Helper for add delta.
    def add_delta(account_name: str, value: float):
        """Accumulate one account delta in the local delta map."""
        # Validate missing account name before continuing.
        if not account_name:
            return

        key = str(account_name).strip()
        # Validate missing key before continuing.
        if not key:
            return

        deltas[key] = deltas.get(key, 0) + float(value)

    # Iterate through each item.
    for item in parsed_items:
        parsed = item["parsed"]
        txn_type = parsed.get("type")
        amount = float(parsed.get("amount", 0) or 0)
        account = parsed.get("account") or ""
        to_account = parsed.get("to_account") or ""

        if is_skip_account_transaction(parsed):
            # Skip the rest of this loop iteration after handling this case.
            continue

        if txn_type == "expense":
            add_delta(account, -amount)

        elif txn_type == "income":
            add_delta(account, amount)

        elif txn_type == "transfer":
            add_delta(account, -amount)
            add_delta(to_account, amount)

    return deltas


# Helper for apply account deltas.
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
    # Validate missing account deltas before continuing.
    if not account_deltas:
        return {
            "success": True,
            "new_balances": {},
            "failed_accounts": [],
        }

    BALANCE_COL = 3
    # Extract LAST UPDATED COL for validation.
    LAST_UPDATED_COL = 5

    # Extract accounts map for validation.
    accounts_map = get_account_index_map()
    today = business_now().strftime("%Y-%m-%d")

    new_balances = {}
    # Extract failed accounts for validation.
    failed_accounts = []

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Split bill parsing note: separate the paid transaction from each person share.
    for account_name in account_deltas:
        # Extract account key for validation.
        account_key = str(account_name).strip().lower()
        # Handle account key and account key not in accounts map.
        if account_key and account_key not in accounts_map:
            # Append the current value to failed accounts.
            failed_accounts.append(account_name)

    if failed_accounts:
        return {
            "success": False,
            "new_balances": {},
            "failed_accounts": failed_accounts,
        }

    # Iterate through each account name, delta.
    for account_name, delta in account_deltas.items():
        # Extract account key for validation.
        account_key = str(account_name).strip().lower()
        # Extract account info for validation.
        account_info = accounts_map.get(account_key)

        # Validate missing account info before continuing.
        if not account_info:
            # Account flow section
            failed_accounts.append(account_name)
            # Skip the rest of this loop iteration after handling this case.
            continue

        new_balance = account_info["balance"] + float(delta)

        update_cell(SHEET_ACCOUNTS, account_info["row"], BALANCE_COL, new_balance)
        update_cell(SHEET_ACCOUNTS, account_info["row"], LAST_UPDATED_COL, today)

        new_balances[account_info["name"]] = new_balance

    return {
        "success": len(failed_accounts) == 0,
        "new_balances": new_balances,
        "failed_accounts": failed_accounts,
    }


# ── Core transaction functions ────────────────────────────────────────────────

# Helper for save transaction.
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
    is_valid, validation_message = validate_transaction(parsed)
    # Validate missing is valid before continuing.
    if not is_valid:
        return {
            "success": False,
            "transaction_id": None,
            "message": validation_message,
            "new_balance": None,
            "new_balances": {},
        }

    if parsed.get("type") in {"expense", "income"}:
        parsed["category"] = ensure_category_for_transaction(parsed.get("category"), parsed.get("type"))

    deltas = calculate_account_deltas([
        {
            "parsed": parsed,
            "raw": raw_input,
        }
    ])
    accounts_ok, missing_accounts = validate_accounts_exist(deltas)
    # Validate missing accounts ok before continuing.
    if not accounts_ok:
        return {
            "success": False,
            "transaction_id": None,
            "message": "Rekening tidak ditemukan: " + ", ".join(missing_accounts),
            "new_balance": None,
            "new_balances": {},
        }

    txn_id, row = build_transaction_row(parsed, raw_input)

    # Run this operation in a guarded block so failures can be handled.
    try:
        append_row(SHEET_TRANSACTIONS, row)
        sort_transactions_sheet_by_date(desc=True)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {
            "success": False,
            "transaction_id": None,
            "message": f"Gagal menyimpan transaksi: {str(e)}",
            "new_balance": None,
            "new_balances": {},
        }

    new_balance = None
    # Extract new balance account for validation.
    new_balance_account = None

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Build balance result for the response flow.
        balance_result = apply_account_deltas(deltas)

        if parsed.get("type") == "transfer":
            new_balance_account = parsed.get("to_account") or parsed.get("account")
        # Use the fallback path when no earlier branch matched.
        else:
            new_balance_account = parsed.get("account") or parsed.get("to_account")

        if new_balance_account:
            for name, balance in balance_result.get("new_balances", {}).items():
                if str(name).lower() == str(new_balance_account).lower():
                    new_balance = balance
                    # Extract new balance account for validation.
                    new_balance_account = name
                    # Leave the loop after the target condition has been reached.
                    break

        if balance_result.get("failed_accounts"):
            return _post_write_failure_result(
                RuntimeError("Saldo gagal diupdate: " + ", ".join(balance_result["failed_accounts"])),
                candidate_ids=[txn_id],
            )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return _post_write_failure_result(e, candidate_ids=[txn_id])

    return {
        "success": True,
        "commit_status": "commit_succeeded",
        "rollback_status": "rollback_not_needed",
        "reconciliation_required": False,
        "transaction_id": txn_id,
        "message": "ok",
        "new_balance": new_balance,
        "new_balance_account": new_balance_account,
        "new_balances": balance_result.get("new_balances", {}) if "balance_result" in locals() else {},
        "account_deltas": deltas,
    }


# Helper for save transactions batch.
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
    # Validate missing parsed items before continuing.
    if not parsed_items:
        return {
            "success": False,
            "message": "Tidak ada transaksi untuk disimpan.",
            "success_count": 0,
            "failed_items": [],
            "saved_ids": [],
            "new_balances": {},
        }

    valid_items = []
    failed_items = []
    # Load rows for the current calculation.
    rows = []
    saved_ids = []

    # Iterate through each item.
    for item in parsed_items:
        parsed = item["parsed"]
        raw = item["raw"]

        is_valid, validation_message = validate_transaction(parsed)
        # Validate missing is valid before continuing.
        if not is_valid:
            failed_items.append({
                "raw": raw,
                "message": validation_message,
            })
            # Skip the rest of this loop iteration after handling this case.
            continue

        if parsed.get("type") in {"expense", "income"}:
            parsed["category"] = ensure_category_for_transaction(parsed.get("category"), parsed.get("type"))

        txn_id, row = build_transaction_row(parsed, raw)
        # Append the current value to saved ids.
        saved_ids.append(txn_id)
        # Append the current value to rows.
        rows.append(row)
        # Append the current value to valid items.
        valid_items.append(item)

    # Validate missing rows before continuing.
    if not rows:
        return {
            "success": False,
            "message": "Semua transaksi gagal divalidasi.",
            "success_count": 0,
            "failed_items": failed_items,
            "saved_ids": [],
            "new_balances": {},
        }

    deltas = calculate_account_deltas(valid_items)
    accounts_ok, missing_accounts = validate_accounts_exist(deltas)
    # Validate missing accounts ok before continuing.
    if not accounts_ok:
        return {
            "success": False,
            "message": "Rekening tidak ditemukan: " + ", ".join(missing_accounts),
            "success_count": 0,
            "failed_items": failed_items + [
                {
                    "raw": "validasi rekening",
                    "message": "Rekening tidak ditemukan: " + ", ".join(missing_accounts),
                }
            ],
            "saved_ids": [],
            "new_balances": {},
        }

    # Run this operation in a guarded block so failures can be handled.
    try:
        append_rows(SHEET_TRANSACTIONS, rows)
        sort_transactions_sheet_by_date(desc=True)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {
            "success": False,
            "message": f"Gagal menyimpan batch transaksi: {str(e)}",
            "success_count": 0,
            "failed_items": [
                {
                    "raw": item["raw"],
                    "message": str(e),
                }
                # Iterate through each item.
                for item in valid_items
            ] + failed_items,
            "saved_ids": [],
            "new_balances": {},
        }

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Build balance result for the response flow.
        balance_result = apply_account_deltas(deltas)

        if balance_result.get("failed_accounts"):
            return _post_write_failure_result(
                RuntimeError("Saldo gagal diupdate: " + ", ".join(balance_result["failed_accounts"])),
                batch=True,
                candidate_ids=saved_ids,
            )

        return {
            "success": True,
            "commit_status": "commit_succeeded",
            "rollback_status": "rollback_not_needed",
            "reconciliation_required": False,
            "message": "ok",
            "success_count": len(valid_items),
            "failed_items": failed_items,
            "saved_ids": saved_ids,
            "new_balances": balance_result.get("new_balances", {}),
            "account_deltas": deltas,
        }

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return _post_write_failure_result(e, batch=True, candidate_ids=saved_ids)


# ── Query functions ───────────────────────────────────────────────────────────

# Helper for get transactions by month.
def get_transactions_by_month(year: int, month: int) -> list[dict]:
    """Read transactions whose date starts with the requested year-month."""
    # Load records for the current calculation.
    records = get_all_records(SHEET_TRANSACTIONS)
    prefix = f"{year}-{month:02d}"
    return [r for r in records if str(r.get("date", "")).startswith(prefix)]


# Helper for get transactions by date.
def get_transactions_by_date(date_str: str) -> list[dict]:
    """Read transactions whose sheet date exactly matches `date_str`."""
    # Load records for the current calculation.
    records = get_all_records(SHEET_TRANSACTIONS)
    return [r for r in records if r.get("date") == date_str]


# Helper for get expense by category.
def get_expense_by_category(year: int, month: int) -> dict:
    """Aggregate gross expense amount by category for one month."""
    # Load transactions for the current calculation.
    transactions = get_transactions_by_month(year, month)
    # Build result for the response flow.
    result = {}

    # Iterate through each txn.
    for txn in transactions:
        if txn.get("type") != "expense":
            # Skip the rest of this loop iteration after handling this case.
            continue

        cat = txn.get("category") or "Other Expense"
        amount = float(txn.get("amount", 0) or 0)
        result[cat] = result.get(cat, 0) + amount

    return result

# Helper for is debt cashflow transaction.
def is_debt_cashflow_transaction(txn: dict) -> bool:
    """Check whether a condition is true for debt cashflow transaction."""
    category = str(txn.get("category", "")).strip()
    parsed_by = str(txn.get("parsed_by", "")).strip().lower()

    return category in DEBT_CASHFLOW_CATEGORIES or parsed_by == "debt"


# Helper for parse transaction date.
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
        return None


# Helper for sort transactions sheet by date.
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
        sheet = get_sheet(SHEET_TRANSACTIONS)
        values = sheet.get_all_values()

        if len(values) <= 2:
            return {"success": True, "message": "Tidak cukup row untuk sort."}

        header = values[0]
        # Load rows for the current calculation.
        rows = values[1:]
        col_count = len(header)

        # Normalize normalized rows before matching.
        normalized_rows = []
        # Iterate through each idx, row.
        for idx, row in enumerate(rows):
            padded = list(row) + [""] * max(0, col_count - len(row))
            padded = padded[:col_count]
            date_obj = parse_transaction_date(padded[1] if len(padded) > 1 else "")
            # Append the current value to normalized rows.
            normalized_rows.append((idx, date_obj or datetime.min.date(), padded))

        normalized_rows.sort(
            key=lambda item: (item[1], item[0]),
            reverse=desc,
        )

        # Load sorted rows for the current calculation.
        sorted_rows = [item[2] for item in normalized_rows]
        end_col = chr(ord("A") + col_count - 1)
        sheet.update(f"A2:{end_col}{len(sorted_rows) + 1}", sorted_rows)

        return {"success": True, "message": "transactions sorted by date"}

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {"success": False, "message": str(e)}


# Helper for get transactions with row index.
def get_transactions_with_row_index() -> list[dict]:
    """Read transactions and attach their one-based sheet row index."""
    # Load records for the current calculation.
    records = get_all_records(SHEET_TRANSACTIONS)
    # Build result for the response flow.
    result = []

    # Iterate through each i, record.
    for i, record in enumerate(records):
        item = dict(record)
        item["_row_index"] = i + 2
        # Append the current value to result.
        result.append(item)

    return result

# Helper for get recent transactions.
def get_recent_transactions(
    limit: int = 10,
    period: str | None = None,
    month: str | None = None,
) -> list[dict]:
    """Read recent transactions with optional period/month filtering.

    Args:
        limit: Maximum number of rows returned.
        period: Optional shortcut filter: `today`, `week`, or `month`.
        month: Optional explicit `YYYY-MM` filter.

    Returns:
        Newest matching transactions, each with `_row_index`.
    """
    # Load records for the current calculation.
    records = get_transactions_with_row_index()
    today = business_now().date()

    if month:
        records = [
            r for r in records
            if str(r.get("date", "")).startswith(month)
        ]

    elif period == "today":
        today_str = today.strftime("%Y-%m-%d")
        records = [
            r for r in records
            if str(r.get("date", "")) == today_str
        ]

    elif period == "week":
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)

        filtered = []
        # Iterate through each r.
        for r in records:
            txn_date = parse_transaction_date(r.get("date", ""))
            # Handle txn date and start week <= txn date <= end week.
            if txn_date and start_week <= txn_date <= end_week:
                # Append the current value to filtered.
                filtered.append(r)

        # Load records for the current calculation.
        records = filtered

    elif period == "month":
        month_now = today.strftime("%Y-%m")
        records = [
            r for r in records
            if str(r.get("date", "")).startswith(month_now)
        ]

    records = sorted(
        records,
        key=lambda x: (
            parse_transaction_date(x.get("date", "")) or datetime.min.date(),
            int(x.get("_row_index", 0)),
        ),
        reverse=True,
    )

    return records[:limit]

# Helper for get transaction by id.
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
    # Load records for the current calculation.
    records = get_transactions_with_row_index()

    # Iterate through each record.
    for record in records:
        if str(record.get("id", "")).strip() == str(txn_id).strip():
            return record

    return None


# Helper for get transactions by ids.
def get_transactions_by_ids(txn_ids: list[str]) -> list[dict]:
    """Read transactions whose IDs are in the requested list."""
    target_ids = {str(x).strip() for x in txn_ids if str(x).strip()}
    # Load records for the current calculation.
    records = get_transactions_with_row_index()

    return [
        r for r in records
        if str(r.get("id", "")).strip() in target_ids
    ]

# Helper for get transactions by row indices.
def get_transactions_by_row_indices(row_indices: list[int]) -> list[dict]:
    """Read transactions whose sheet row indexes are requested."""
    # Load target rows for the current calculation.
    target_rows = {int(x) for x in row_indices}
    # Load records for the current calculation.
    records = get_transactions_with_row_index()

    return [
        r for r in records
        if int(r.get("_row_index", 0)) in target_rows
    ]


# Helper for calculate reverse deltas for delete.
def calculate_reverse_deltas_for_delete(transactions: list[dict]) -> dict:
    """Calculate derived values for reverse deltas for delete."""
    deltas = {}

    # Helper for add delta.
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
        # Validate missing account name before continuing.
        if not account_name:
            return

        key = str(account_name).strip()
        # Validate missing key before continuing.
        if not key:
            return

        deltas[key] = deltas.get(key, 0) + float(value)

    # Iterate through each txn.
    for txn in transactions:
        txn_type = str(txn.get("type", "")).strip()
        amount = float(txn.get("amount", 0) or 0)
        account = str(txn.get("account", "")).strip()
        to_account = str(txn.get("to_account", "")).strip()

        if is_skip_account_transaction(txn):
            # Skip the rest of this loop iteration after handling this case.
            continue

        if txn_type == "expense":
            add_delta(account, amount)

        elif txn_type == "income":
            add_delta(account, -amount)

        elif txn_type == "transfer":
            add_delta(account, amount)
            add_delta(to_account, -amount)

    return deltas


# Helper for parse transaction debt ids.
def parse_transaction_debt_ids(txn: dict) -> list[str]:
    """Parse linked debt IDs from a transaction record.

    Args:
        txn: Transaction record containing `hutang_id`.

    Returns:
        Clean debt ID list split from comma, semicolon, or whitespace
        separators.
    """
    raw = str(txn.get("hutang_id", "") or "").strip()
    # Validate missing raw before continuing.
    if not raw:
        return []
    return [part.strip() for part in re.split(r"[,;\s]+", raw) if part.strip()]


# Helper for transaction has debt relation.
def transaction_has_debt_relation(txn: dict) -> bool:
    """Check whether a transaction carries debt linkage metadata.

    Args:
        txn: Transaction record from the `transactions` sheet.

    Returns:
        `True` when `hutang_id` contains IDs or `tipe_hutang` is filled.
    """
    return bool(parse_transaction_debt_ids(txn)) or bool(str(txn.get("tipe_hutang", "") or "").strip())


# Helper for preview delete transactions by refs.
def preview_delete_transactions_by_refs(
    row_indices: list[int] | None = None,
    txn_ids: list[str] | None = None,
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
    row_indices = row_indices or []
    txn_ids = txn_ids or []

    # Load by rows for the current calculation.
    by_rows = get_transactions_by_row_indices(row_indices) if row_indices else []
    by_ids = get_transactions_by_ids(txn_ids) if txn_ids else []

    # Load transactions for the current calculation.
    transactions = []
    # Load seen rows for the current calculation.
    seen_rows = set()

    # Iterate through each txn.
    for txn in by_rows + by_ids:
        row_index = int(txn.get("_row_index", 0))
        # Handle row index and row index not in seen rows.
        if row_index and row_index not in seen_rows:
            # Append the current value to transactions.
            transactions.append(txn)
            # Append the current value to seen rows.
            seen_rows.add(row_index)

    found_rows = {int(t.get("_row_index", 0)) for t in by_rows}
    # Load requested rows for the current calculation.
    requested_rows = {int(x) for x in row_indices}
    # Load missing rows for the current calculation.
    missing_rows = sorted(requested_rows - found_rows)

    found_ids = {str(t.get("id", "")).strip() for t in by_ids}
    requested_ids = {str(x).strip() for x in txn_ids if str(x).strip()}
    missing_ids = sorted(requested_ids - found_ids)

    blocked = []
    deletable = []

    # Iterate through each txn.
    for txn in transactions:
        # Handle is debt cashflow transaction(txn) and not transaction has deb.
        if is_debt_cashflow_transaction(txn) and not transaction_has_debt_relation(txn):
            # Append the current value to blocked.
            blocked.append(txn)
        # Use the fallback path when no earlier branch matched.
        else:
            # Append the current value to deletable.
            deletable.append(txn)

    reverse_deltas = calculate_reverse_deltas_for_delete(deletable)

    return {
        "success": True,
        "requested_count": len(row_indices) + len(txn_ids),
        "found_count": len(transactions),
        "deletable": deletable,
        "blocked": blocked,
        "missing_ids": missing_ids,
        "missing_rows": missing_rows,
        "reverse_deltas": reverse_deltas,
    }

# Helper for preview delete transactions.
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
    # Load transactions for the current calculation.
    transactions = get_transactions_by_ids(txn_ids)
    found_ids = {str(t.get("id", "")).strip() for t in transactions}
    requested_ids = {str(x).strip() for x in txn_ids}

    missing_ids = sorted(requested_ids - found_ids)

    blocked = []
    deletable = []

    # Iterate through each txn.
    for txn in transactions:
        # Handle is debt cashflow transaction(txn) and not transaction has deb.
        if is_debt_cashflow_transaction(txn) and not transaction_has_debt_relation(txn):
            # Append the current value to blocked.
            blocked.append(txn)
        # Use the fallback path when no earlier branch matched.
        else:
            # Append the current value to deletable.
            deletable.append(txn)

    reverse_deltas = calculate_reverse_deltas_for_delete(deletable)

    return {
        "success": True,
        "requested_count": len(txn_ids),
        "found_count": len(transactions),
        "deletable": deletable,
        "blocked": blocked,
        "missing_ids": missing_ids,
        "reverse_deltas": reverse_deltas,
    }


# Helper for delete transactions by ids.
def delete_transactions_by_ids(
    txn_ids: list[str],
    *,
    void_debts_for_transaction_fn=None,
    reverse_debt_payment_transaction_fn=None,
) -> dict:
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
    # Build preview for the response flow.
    preview = preview_delete_transactions(txn_ids)

    deletable = preview["deletable"]
    blocked = preview["blocked"]
    missing_ids = preview["missing_ids"]

    # Validate missing deletable before continuing.
    if not deletable:
        return {
            "success": False,
            "message": "Tidak ada transaksi yang bisa dihapus.",
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "new_balances": {},
        }

    reverse_deltas = preview["reverse_deltas"]

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Build balance result for the response flow.
        balance_result = apply_account_deltas(reverse_deltas)
        if balance_result.get("failed_accounts"):
            return {
                "success": False,
                "message": "Rekening tidak ditemukan: " + ", ".join(balance_result["failed_accounts"]),
                "deleted_count": 0,
                "deleted_ids": [],
                "blocked": blocked,
                "missing_ids": missing_ids,
                "new_balances": {},
            }
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {
            "success": False,
            "message": f"Gagal reverse saldo: {str(e)}",
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "new_balances": {},
        }

    linked_debt_voided_ids = []
    reversed_payment_debt_items = []
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Iterate through each txn.
        for txn in deletable:
            txn_id = str(txn.get("id", "") or "").strip()
            linked_ids = parse_transaction_debt_ids(txn)
            category = str(txn.get("category", "") or "").strip()

            # Account flow section
            if category in {"Pembayaran Piutang", "Bayar Utang"}:
                if reverse_debt_payment_transaction_fn is None:
                    raise PartialMutationError(
                        "Debt payment collaborator tidak tersedia.",
                        operation="delete_transaction_reverse_debt_payment",
                    )
                # Build reverse result for the response flow.
                reverse_result = reverse_debt_payment_transaction_fn(txn)
                if not reverse_result.get("success"):
                    return {
                        "success": False,
                        "message": reverse_result.get("message", "Gagal membalik pembayaran debt terkait transaksi."),
                        "deleted_count": 0,
                        "deleted_ids": [],
                        "blocked": blocked,
                        "missing_ids": missing_ids,
                        "new_balances": balance_result.get("new_balances", {}),
                    }
                reversed_payment_debt_items.extend(reverse_result.get("reversed", []))
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Validate missing txn id and not linked ids before continuing.
            if not txn_id and not linked_ids:
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Build linked result for the response flow.
            if void_debts_for_transaction_fn is None:
                raise PartialMutationError(
                    "Debt void collaborator tidak tersedia.",
                    operation="delete_transaction_void_linked_debt",
                )
            linked_result = void_debts_for_transaction_fn(txn_id, linked_ids)
            if not linked_result.get("success"):
                return {
                    "success": False,
                    "message": linked_result.get("message", "Gagal void debt terkait transaksi."),
                    "deleted_count": 0,
                    "deleted_ids": [],
                    "blocked": blocked,
                    "missing_ids": missing_ids,
                    "new_balances": balance_result.get("new_balances", {}),
                }
            linked_debt_voided_ids.extend(linked_result.get("voided_ids", []))
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {
            "success": False,
            "message": f"Gagal sync debt terkait transaksi: {str(e)}",
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "new_balances": balance_result.get("new_balances", {}),
        }

    # Run this operation in a guarded block so failures can be handled.
    try:
        row_indices = [
            int(txn["_row_index"])
            # Iterate through each txn.
            for txn in deletable
            if txn.get("_row_index")
        ]

        delete_rows(SHEET_TRANSACTIONS, row_indices)

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {
            "success": False,
            "message": (
                "Saldo sudah sempat direverse, tapi row transaksi gagal dihapus. "
                f"Cek manual di sheet. Error: {str(e)}"
            ),
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "new_balances": balance_result.get("new_balances", {}),
        }

    deleted_ids = [
        str(txn.get("id", ""))
        # Iterate through each txn.
        for txn in deletable
    ]

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
    }

# Helper for delete transactions by refs.
def delete_transactions_by_refs(
    row_indices: list[int] | None = None,
    txn_ids: list[str] | None = None,
    *,
    void_debts_for_transaction_fn=None,
    reverse_debt_payment_transaction_fn=None,
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
    # Build preview for the response flow.
    preview = preview_delete_transactions_by_refs(row_indices, txn_ids)

    deletable = preview["deletable"]
    blocked = preview["blocked"]
    missing_ids = preview.get("missing_ids", [])
    missing_rows = preview.get("missing_rows", [])

    # Validate missing deletable before continuing.
    if not deletable:
        return {
            "success": False,
            "message": "Tidak ada transaksi yang bisa dihapus.",
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "missing_rows": missing_rows,
            "new_balances": {},
        }

    reverse_deltas = preview["reverse_deltas"]

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Build balance result for the response flow.
        balance_result = apply_account_deltas(reverse_deltas)
        if balance_result.get("failed_accounts"):
            raise PartialMutationError(
                "Rekening gagal direverse: " + ", ".join(balance_result["failed_accounts"]),
                operation="delete_transaction_reverse_balance",
            )
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        if isinstance(e, PartialMutationError):
            raise
        raise PartialMutationError(f"Gagal reverse saldo: {e}", operation="delete_transaction_reverse_balance") from e

    linked_debt_voided_ids = []
    reversed_payment_debt_items = []
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Iterate through each txn.
        for txn in deletable:
            txn_id = str(txn.get("id", "") or "").strip()
            linked_ids = parse_transaction_debt_ids(txn)
            category = str(txn.get("category", "") or "").strip()

            if category in {"Pembayaran Piutang", "Bayar Utang"}:
                if reverse_debt_payment_transaction_fn is None:
                    raise PartialMutationError(
                        "Debt payment collaborator tidak tersedia.",
                        operation="delete_transaction_reverse_debt_payment",
                    )
                # Build reverse result for the response flow.
                reverse_result = reverse_debt_payment_transaction_fn(txn)
                require_success_after_write(
                    reverse_result,
                    operation="delete_transaction_reverse_debt_payment",
                    default_message="Gagal membalik pembayaran debt terkait transaksi.",
                )
                reversed_payment_debt_items.extend(reverse_result.get("reversed", []))
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Validate missing txn id and not linked ids before continuing.
            if not txn_id and not linked_ids:
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Build linked result for the response flow.
            if void_debts_for_transaction_fn is None:
                raise PartialMutationError(
                    "Debt void collaborator tidak tersedia.",
                    operation="delete_transaction_void_linked_debt",
                )
            linked_result = void_debts_for_transaction_fn(txn_id, linked_ids)
            require_success_after_write(
                linked_result,
                operation="delete_transaction_void_linked_debt",
                default_message="Gagal void debt terkait transaksi.",
            )
            linked_debt_voided_ids.extend(linked_result.get("voided_ids", []))
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        if isinstance(e, PartialMutationError):
            raise
        raise PartialMutationError(f"Gagal sync debt terkait transaksi: {e}", operation="delete_transaction_sync_debt") from e

    # Run this operation in a guarded block so failures can be handled.
    try:
        delete_row_indices = [
            int(txn["_row_index"])
            # Iterate through each txn.
            for txn in deletable
            if txn.get("_row_index")
        ]

        delete_rows(SHEET_TRANSACTIONS, delete_row_indices)

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        raise PartialMutationError(
            f"Row transaksi gagal dihapus setelah saldo/debt berubah: {e}",
            operation="delete_transaction_rows",
        ) from e

    deleted_ids = [
        str(txn.get("id", ""))
        # Iterate through each txn.
        for txn in deletable
    ]

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
    }

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
]


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
}


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
}


# Helper for normalize edit field.
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
        return key

    return FIELD_ALIASES.get(key)


# Helper for normalize edit updates.
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
    # Normalize normalized before matching.
    normalized = {}

    # Iterate through each raw field, value.
    for raw_field, value in updates.items():
        field = normalize_edit_field(raw_field)

        # Validate missing field before continuing.
        if not field:
            raise ValueError(f"Field `{raw_field}` tidak dikenali.")

        if field not in EDITABLE_TRANSACTION_FIELDS:
            raise ValueError(f"Field `{field}` tidak boleh diedit.")

        if field == "amount":
            # Extract parsed amount for validation.
            parsed_amount = extract_amount_from_text(str(value))
            if parsed_amount is not None:
                value = float(parsed_amount)
            # Use the fallback path when no earlier branch matched.
            else:
                # Run this operation in a guarded block so failures can be handled.
                try:
                    value = float(value)
                # Handle an expected failure from the guarded operation above.
                except Exception:
                    raise ValueError("Amount harus berupa angka. Contoh: 500k atau 500000.")

            if value <= 0:
                raise ValueError("Amount harus lebih dari 0.")

        elif field == "type":
            value = str(value).strip().lower()

            if value not in ["expense", "income", "transfer"]:
                raise ValueError("Type harus salah satu: expense, income, transfer.")

        elif field == "date":
            value = str(value).strip()

            # Run this operation in a guarded block so failures can be handled.
            try:
                datetime.strptime(value, "%Y-%m-%d")
            # Handle an expected failure from the guarded operation above.
            except Exception:
                raise ValueError("Date harus format YYYY-MM-DD. Contoh: 2026-06-10.")

        # Use the fallback path when no earlier branch matched.
        else:
            value = str(value).strip()

        normalized[field] = value

    return normalized


# Helper for get single transaction by ref.
def get_single_transaction_by_ref(
    row_index: int | None = None,
    txn_id: str | None = None,
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
    if row_index:
        matches = get_transactions_by_row_indices([row_index])
        return matches[0] if matches else None

    if txn_id:
        matches = get_transactions_by_ids([txn_id])

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            # Raise a clear error so the caller can stop this invalid flow.
            raise ValueError(
                "Transaction ID ini duplikat. Gunakan nomor dari /last agar spesifik."
            )

    return None


# Helper for build transaction row from record.
def build_transaction_row_from_record(txn: dict) -> list:
    """Convert a transaction record dict back into sheet row order."""
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
    ]


# Helper for calculate account effect.
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
    deltas = {}

    # Helper for add delta.
    def add_delta(account_name: str, value: float):
        """Accumulate one account effect delta for a transaction."""
        # Validate missing account name before continuing.
        if not account_name:
            return

        key = str(account_name).strip()
        # Validate missing key before continuing.
        if not key:
            return

        deltas[key] = deltas.get(key, 0) + float(value)

    txn_type = str(txn.get("type", "")).strip()
    amount = float(txn.get("amount", 0) or 0)
    account = str(txn.get("account", "")).strip()
    to_account = str(txn.get("to_account", "")).strip()

    if is_skip_account_transaction(txn):
        return deltas

    if txn_type == "expense":
        add_delta(account, -amount)

    elif txn_type == "income":
        add_delta(account, amount)

    elif txn_type == "transfer":
        add_delta(account, -amount)
        add_delta(to_account, amount)

    return deltas


# Helper for calculate edit net deltas.
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
    old_effect = calculate_account_effect(old_txn)
    new_effect = calculate_account_effect(new_txn)

    # Extract accounts for validation.
    accounts = set(old_effect.keys()) | set(new_effect.keys())
    # Build result for the response flow.
    result = {}

    # Iterate through each account.
    for account in accounts:
        delta = -old_effect.get(account, 0) + new_effect.get(account, 0)

        if delta != 0:
            result[account] = delta

    return result


# Helper for validate edit transaction.
def validate_edit_transaction(txn: dict) -> tuple[bool, str]:
    """Validate data before it is used by edit transaction."""
    txn_type = str(txn.get("type", "")).strip()
    amount = float(txn.get("amount", 0) or 0)
    account = str(txn.get("account", "")).strip()
    to_account = str(txn.get("to_account", "")).strip()

    if txn_type not in ["expense", "income", "transfer"]:
        return False, "Type transaksi tidak valid."

    if amount <= 0:
        return False, "Amount harus lebih dari 0."

    if txn_type in ["expense", "income"] and not account:
        return False, "Expense/income wajib punya account."

    if txn_type == "transfer":
        # Validate missing account or not to account before continuing.
        if not account or not to_account:
            return False, "Transfer wajib punya account dan to_account."

        if account.lower() == to_account.lower():
            return False, "Account asal dan tujuan transfer tidak boleh sama."

    return True, "ok"


# Helper for preview edit transaction by ref.
def preview_edit_transaction_by_ref(
    updates: dict,
    row_index: int | None = None,
    txn_id: str | None = None,
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
        # Normalize normalized updates before matching.
        normalized_updates = normalize_edit_updates(updates)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }

    # Run this operation in a guarded block so failures can be handled.
    try:
        old_txn = get_single_transaction_by_ref(row_index=row_index, txn_id=txn_id)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }

    # Validate missing old txn before continuing.
    if not old_txn:
        return {
            "success": False,
            "message": "Transaksi tidak ditemukan.",
        }

    old_payment_category = str(old_txn.get("category", "") or "").strip()
    if old_payment_category in {"Pembayaran Piutang", "Bayar Utang"}:
        # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
        if set(normalized_updates.keys()) != {"amount"}:
            return {
                "success": False,
                "message": (
                    "Transaksi pembayaran hutang/piutang hanya boleh diedit nominalnya. "
                    "Untuk koreksi lain, pakai /delete_txn lalu input ulang."
                ),
            }

    old_has_debt_relation = transaction_has_debt_relation(old_txn)

    # Account flow section
    if is_debt_cashflow_transaction(old_txn) and not old_has_debt_relation:
        return {
            "success": False,
            "message": (
                "Transaksi debt cashflow tanpa hutang_id belum boleh diedit dari fitur ini "
                "supaya sheet debts tidak inkonsisten."
            ),
        }

    new_txn = dict(old_txn)

    # Iterate through each field, value.
    for field, value in normalized_updates.items():
        new_txn[field] = value

    is_valid, validation_message = validate_edit_transaction(new_txn)

    # Validate missing is valid before continuing.
    if not is_valid:
        return {
            "success": False,
            "message": validation_message,
        }

    reverse_deltas = calculate_edit_net_deltas(old_txn, new_txn)

    return {
        "success": True,
        "message": "ok",
        "old_txn": old_txn,
        "new_txn": new_txn,
        "updates": normalized_updates,
        "net_deltas": reverse_deltas,
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
    # Prepare alloc parts from the incoming input.
    alloc_parts = []
    # Iterate through each item.
    for item in allocations or []:
        debt_id = str(item.get("debt_id") or "").strip()
        amount = item.get("amount")
        # Store allocation notes only when both debt id and amount are present.
        if debt_id and amount is not None:
            alloc_parts.append(f"{debt_id}:{float(amount)}")
    if alloc_parts:
        parts.append("debt_allocations=" + ";".join(alloc_parts))
    if overpayment:
        parts.append(f"overpayment={float(overpayment)}")
    if policy:
        parts.append(f"overpayment_policy={policy}")
    return " | ".join([p for p in parts if p]).strip(" |")


# Helper for edit debt payment transaction amount.
def edit_debt_payment_transaction_amount(
    preview: dict,
    *,
    reverse_debt_payment_transaction_fn=None,
    add_payment_by_person_fn=None,
) -> dict:
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
    # Validate missing person before continuing.
    if not person:
        return {"success": False, "message": "Subject/person transaksi payment kosong."}

    target_debt_type = "receivable" if category == "Pembayaran Piutang" else "payable"
    new_amount = float(new_txn.get("amount", 0) or 0)
    raw_note = str(old_txn.get("raw_input", "") or old_txn.get("catatan", "") or "")

    # Run this operation in a guarded block so failures can be handled.
    try:
        if reverse_debt_payment_transaction_fn is None or add_payment_by_person_fn is None:
            raise PartialMutationError(
                "Debt payment collaborators tidak tersedia.",
                operation="edit_debt_payment_sync",
            )
        # Build reverse result for the response flow.
        reverse_result = reverse_debt_payment_transaction_fn(old_txn)
        require_success_after_write(
            reverse_result,
            operation="edit_debt_payment_reverse_old",
            default_message="Gagal reverse payment lama.",
        )

        payment_result = add_payment_by_person_fn(
            person,
            new_amount,
            note=f"Edit payment dari transaksi {old_txn.get('id') or '-'}",
            target_debt_type=target_debt_type,
            overpayment_policy="opposite_debt",
        )
        require_success_after_write(
            payment_result,
            operation="edit_debt_payment_allocate_new",
            default_message="Gagal alokasi payment baru.",
        )
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        if isinstance(e, PartialMutationError):
            raise
        raise PartialMutationError(f"Gagal sync debt payment: {e}", operation="edit_debt_payment_sync") from e

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Build balance result for the response flow.
        balance_result = apply_account_deltas(net_deltas)
        if balance_result.get("failed_accounts"):
            raise PartialMutationError(
                "Rekening gagal diupdate: " + ", ".join(balance_result["failed_accounts"]),
                operation="edit_debt_payment_balance",
            )
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        if isinstance(e, PartialMutationError):
            raise
        raise PartialMutationError(f"Gagal update saldo: {e}", operation="edit_debt_payment_balance") from e

    # Run this operation in a guarded block so failures can be handled.
    try:
        target_row_index = int(old_txn.get("_row_index"))
        new_txn["id"] = old_txn.get("id")
        new_txn["hutang_id"] = ", ".join([x for x in payment_result.get("affected_debt_ids") or [] if x])
        new_txn["tipe_hutang"] = "piutang" if target_debt_type == "receivable" else "utang"
        new_txn["catatan"] = _payment_allocation_note(
            raw_note,
            payment_result.get("allocations") or [],
            overpayment=float(payment_result.get("overpayment", 0) or 0),
            policy=str(payment_result.get("overpayment_policy") or "opposite_debt"),
        )
        old_raw = str(old_txn.get("raw_input", "") or "")
        new_txn["raw_input"] = old_raw if "[edited]" in old_raw else f"{old_raw} [edited]".strip()
        update_row(SHEET_TRANSACTIONS, target_row_index, build_transaction_row_from_record(new_txn))
        sort_transactions_sheet_by_date(desc=True)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        raise PartialMutationError(
            f"Update row transaksi gagal setelah saldo/debt berubah: {e}",
            operation="edit_debt_payment_row",
        ) from e

    return {
        "success": True,
        "message": "ok",
        "old_txn": old_txn,
        "new_txn": new_txn,
        "net_deltas": net_deltas,
        "new_balances": balance_result.get("new_balances", {}),
        "debt_sync": {"success": True, "payment_reallocated": True, "payment_result": payment_result},
    }

# Helper for edit transaction by ref.
def edit_transaction_by_ref(
    updates: dict,
    row_index: int | None = None,
    txn_id: str | None = None,
    *,
    edit_debt_payment_transaction_fn=None,
    sync_debt_charges_from_transaction_edit_fn=None,
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
    preview = preview_edit_transaction_by_ref(
        # Extract updates for validation.
        updates=updates,
        row_index=row_index,
        txn_id=txn_id,
    )

    if not preview.get("success"):
        return preview

    old_txn = preview["old_txn"]
    new_txn = preview["new_txn"]
    net_deltas = preview["net_deltas"]

    old_payment_category = str(old_txn.get("category", "") or "").strip()
    if old_payment_category in {"Pembayaran Piutang", "Bayar Utang"}:
        if edit_debt_payment_transaction_fn is None:
            raise PartialMutationError(
                "Debt payment edit collaborator tidak tersedia.",
                operation="edit_debt_payment_sync",
            )
        return edit_debt_payment_transaction_fn(preview)

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Build balance result for the response flow.
        balance_result = apply_account_deltas(net_deltas)
        if balance_result.get("failed_accounts"):
            raise PartialMutationError(
                "Rekening gagal diupdate: " + ", ".join(balance_result["failed_accounts"]),
                operation="edit_transaction_balance",
            )
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        if isinstance(e, PartialMutationError):
            raise
        raise PartialMutationError(f"Gagal update saldo: {e}", operation="edit_transaction_balance") from e

    # Run this operation in a guarded block so failures can be handled.
    try:
        target_row_index = int(old_txn.get("_row_index"))

        # Account flow section
        new_txn["id"] = old_txn.get("id")

        # Implementation note for this project-specific finance flow.
        old_raw = str(old_txn.get("raw_input", "") or "")
        if "[edited]" not in old_raw:
            new_txn["raw_input"] = f"{old_raw} [edited]".strip()
        # Use the fallback path when no earlier branch matched.
        else:
            new_txn["raw_input"] = old_raw

        row_values = build_transaction_row_from_record(new_txn)

        update_row(SHEET_TRANSACTIONS, target_row_index, row_values)
        sort_transactions_sheet_by_date(desc=True)

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        raise PartialMutationError(
            f"Update row transaksi gagal setelah saldo berubah: {e}",
            operation="edit_transaction_row",
        ) from e

    debt_sync_result = {"success": True, "updated": [], "overpaid": []}
    # Handle transaction has debt relation(old txn) or transaction has deb.
    if transaction_has_debt_relation(old_txn) or transaction_has_debt_relation(new_txn):
        # Run this operation in a guarded block so failures can be handled.
        try:
            if sync_debt_charges_from_transaction_edit_fn is None:
                raise PartialMutationError(
                    "Debt charge sync collaborator tidak tersedia.",
                    operation="edit_transaction_sync_debt",
                )
            # Build debt sync result for the response flow.
            debt_sync_result = sync_debt_charges_from_transaction_edit_fn(old_txn, new_txn)
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            raise PartialMutationError(
                f"Sync debt gagal setelah transaksi diedit: {e}",
                operation="edit_transaction_sync_debt",
            ) from e

        require_success_after_write(
            debt_sync_result,
            operation="edit_transaction_sync_debt",
            default_message="Sync debt gagal setelah transaksi diedit.",
        )

    return {
        "success": True,
        "message": "ok",
        "old_txn": old_txn,
        "new_txn": new_txn,
        "net_deltas": net_deltas,
        "new_balances": balance_result.get("new_balances", {}),
        "debt_sync": debt_sync_result,
    }
