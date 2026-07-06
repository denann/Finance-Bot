"""Google Sheets client with worksheet access, schema bootstrap, retry handling, best-effort rollback, and read/write helpers."""


# Import contextvars for this module's local operations.
import contextvars
# Import os for this module's local operations.
import os
# Import random for this module's local operations.
import random
# Import re for this module's local operations.
import re
# Import time for this module's local operations.
import time
# Import contextlib so this module can use its helpers.
from contextlib import contextmanager

# Import gspread for this module's local operations.
import gspread
# Import gspread.exceptions so this module can use its helpers.
from gspread.exceptions import WorksheetNotFound
# Import google.oauth2.service_account so this module can use its helpers.
from google.oauth2.service_account import Credentials
# Import app.config so this module can use its helpers.
from app.config import (
    # Include this value in the surrounding collection or call.
    GOOGLE_SERVICE_ACCOUNT_JSON,
    # Include this value in the surrounding collection or call.
    GOOGLE_SHEET_ID,
    # Include this value in the surrounding collection or call.
    SHEET_ACCOUNTS,
    # Include this value in the surrounding collection or call.
    SHEET_ASSETS,
    # Include this value in the surrounding collection or call.
    SHEET_BUDGETS,
    # Include this value in the surrounding collection or call.
    SHEET_CATEGORIES,
    # Include this value in the surrounding collection or call.
    SHEET_DEBT_PAYMENTS,
    # Include this value in the surrounding collection or call.
    SHEET_DEBTS,
    # Include this value in the surrounding collection or call.
    SHEET_MONTHLY_SUMMARY,
    # Include this value in the surrounding collection or call.
    SHEET_NET_WORTH_SNAPSHOTS,
    # Include this value in the surrounding collection or call.
    SHEET_PENDING_EXPENSES,
    # Include this value in the surrounding collection or call.
    SHEET_RECURRING_LOGS,
    # Include this value in the surrounding collection or call.
    SHEET_RECURRING_RULES,
    # Include this value in the surrounding collection or call.
    SHEET_TRANSACTIONS,
# Close the structure that was opened above.
)

# Required scopes for reading and writing Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
# Close the structure that was opened above.
]

# Prepare client for the next step.
_client = None
# Prepare spreadsheet for the next step.
_spreadsheet = None
# Prepare worksheets for the next step.
_worksheets = {}
# Prepare schema checked sheets for the next step.
_schema_checked_sheets = set()
_current_transaction = contextvars.ContextVar("sheets_current_transaction", default=None)


# Central schema definition for all required Google Sheets tabs.

# Open a multi-line structure for the values below.
SHEET_SCHEMAS = {
    # Open a multi-line structure for the values below.
    SHEET_TRANSACTIONS: [
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
    ],
    # Open a multi-line structure for the values below.
    SHEET_ACCOUNTS: [
        "account_name",
        "type",
        "balance",
        "currency",
        "last_updated",
    # Close the structure that was opened above.
    ],
    # Open a multi-line structure for the values below.
    SHEET_BUDGETS: [
        "id",
        "month",
        "category",
        "budget_amount",
        "created_at",
        "updated_at",
    # Close the structure that was opened above.
    ],
    # Open a multi-line structure for the values below.
    SHEET_DEBTS: [
        "id",
        "type",
        "person_name",
        "original_amount",
        "remaining_amount",
        "description",
        "due_date",
        "is_settled",
        "created_at",
        "settled_at",
        "source_transaction_id",
        "cashflow_mode",
        "fronting_mode",
    # Close the structure that was opened above.
    ],
    # Open a multi-line structure for the values below.
    SHEET_DEBT_PAYMENTS: [
        "id",
        "debt_id",
        "amount",
        "date",
        "note",
    # Close the structure that was opened above.
    ],
    # categories uses the existing spreadsheet format: category_name, type, emoji, aliases.
    # aliases is a comma-separated keyword list used as category metadata.
    SHEET_CATEGORIES: [
        "category_name",
        "type",
        "emoji",
        "aliases",
    # Close the structure that was opened above.
    ],
    # Open a multi-line structure for the values below.
    SHEET_MONTHLY_SUMMARY: [
        "month",
        "total_income",
        "total_expense",
        "net",
        "created_at",
        "updated_at",
    # Close the structure that was opened above.
    ],
    # Open a multi-line structure for the values below.
    SHEET_RECURRING_RULES: [
        "id",
        "name",
        "type",
        "amount",
        "category",
        "account",
        "to_account",
        "subject",
        "description",
        "catatan",
        "tipe_pengeluaran",
        "frequency",
        "day_of_month",
        "next_run_date",
        "is_active",
        "created_at",
        "updated_at",
    # Close the structure that was opened above.
    ],
    # Open a multi-line structure for the values below.
    SHEET_RECURRING_LOGS: [
        "id",
        "rule_id",
        "transaction_id",
        "run_date",
        "status",
        "message",
        "created_at",
    # Close the structure that was opened above.
    ],
    # Open a multi-line structure for the values below.
    SHEET_ASSETS: [
        "id",
        "name",
        "category",
        "current_value",
        "description",
        "is_active",
        "created_at",
        "updated_at",
        "asset_type",
        "quantity",
        "unit",
        "price_source",
        "price_per_unit",
        "last_price_update",
        "purchase_price_per_unit",
        "purchase_date",
    # Close the structure that was opened above.
    ],
    # Open a multi-line structure for the values below.
    SHEET_PENDING_EXPENSES: [
        "id",
        "due_date",
        "month",
        "due_precision",
        "amount",
        "category",
        "account",
        "subject",
        "description",
        "status",
        "created_at",
        "updated_at",
        "paid_transaction_id",
        "raw_input",
    # Close the structure that was opened above.
    ],
    # Open a multi-line structure for the values below.
    SHEET_NET_WORTH_SNAPSHOTS: [
        "id",
        "snapshot_date",
        "total_accounts",
        "total_assets",
        "total_liabilities",
        "net_worth",
        "created_at",
    # Close the structure that was opened above.
    ],
# Close the structure that was opened above.
}


# Open a multi-line structure for the values below.
DEFAULT_ACCOUNT_ROWS = [
    ["Cash", "cash", 0, "IDR", ""],
    ["BRI", "bank", 0, "IDR", ""],
    ["BSI", "bank", 0, "IDR", ""],
    ["BCA", "bank", 0, "IDR", ""],
    ["DANA", "ewallet", 0, "IDR", ""],
    ["GoPay", "ewallet", 0, "IDR", ""],
    ["Seabank", "bank", 0, "IDR", ""],
# Close the structure that was opened above.
]


# Open a multi-line structure for the values below.
DEFAULT_CATEGORY_ROWS = [
    ["Food & Beverage", "expense", "🍽️", "makan,minum,kopi,nasi,donat,galon"],
    ["Transport", "expense", "🚗", "transport,ojek,bensin,parkir,tol"],
    ["Bills & Utilities", "expense", "💡", "listrik,air,wifi,pulsa,token,tagihan"],
    ["Entertainment", "expense", "🎮", "game,ml,netflix,bioskop,hiburan"],
    ["Health", "expense", "🏥", "obat,dokter,klinik,vitamin"],
    ["Shopping", "expense", "🛍️", "belanja,shopee,tokopedia,baju"],
    ["Education", "expense", "🎓", "kuliah,buku,kursus,wisuda,semester"],
    ["Housing", "expense", "🏠", "kos,kontrakan,sewa,rumah"],
    ["Charity", "expense", "🤲", "sedekah,donasi,zakat"],
    ["Other Expense", "expense", "📦", "lainnya,other"],
    ["Salary", "income", "💼", "gaji,salary"],
    ["Bonus", "income", "🎁", "bonus,thr"],
    ["Refund", "income", "↩️", "refund,pengembalian"],
    ["Cashback", "income", "🏷️", "cashback"],
    ["Other Income", "income", "💰", "pemasukan lain,other income"],
# Close the structure that was opened above.
]


# Group the SheetsAtomicWriteError behavior in one class.
class SheetsAtomicWriteError(RuntimeError):
    """Error raised when a Google Sheets write fails after retries and rollback handling is attempted."""

    # Define init for callers in this flow.
    def __init__(self, original_error, rollback_ok: bool | None = None, rollback_errors: list[str] | None = None):
        """Build an error message that preserves write and rollback status.

        Args:
            original_error: Exception or message from the failed Sheets write.
            rollback_ok: `True` when rollback succeeded, `False` when rollback
                failed, or `None` when rollback was not attempted.
            rollback_errors: Human-readable rollback failure details.

        Side effects:
            Stores the original error and rollback metadata on the exception
            instance. It does not perform rollback by itself.
        """
        # Run this statement as part of the current workflow.
        self.original_error = original_error
        # Run this statement as part of the current workflow.
        self.rollback_ok = rollback_ok
        # Run this statement as part of the current workflow.
        self.rollback_errors = rollback_errors or []

        # Prepare base for the next step.
        base = str(original_error)
        # Handle the case where rollback_ok is True.
        if rollback_ok is True:
            # Open a multi-line structure for the values below.
            message = (
                "Google Sheets write gagal setelah retry. "
                "Semua perubahan dari operasi ini sudah di-rollback. "
                f"Detail: {base}"
            # Close the structure that was opened above.
            )
        # Handle the alternate case where rollback_ok is False.
        elif rollback_ok is False:
            rollback_detail = "; ".join(self.rollback_errors) if self.rollback_errors else "rollback gagal tanpa detail"
            # Open a multi-line structure for the values below.
            message = (
                "Google Sheets write gagal setelah retry. "
                "Sebagian rollback juga gagal, kemungkinan karena quota masih habis. "
                f"Cek sheet manual. Detail: {base}. Rollback: {rollback_detail}"
            # Close the structure that was opened above.
            )
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Prepare message for the next step.
            message = base

        # Run this statement as part of the current workflow.
        super().__init__(message)


# Schema compatibility note for Google Sheets headers and rows.
# Implementation section

# Group the SheetsTransaction behavior in one class.
class SheetsTransaction:
    """Best-effort transaction wrapper for Google Sheets writes. It records successful writes and tries to roll them back if a later write fails."""

    # Define init for callers in this flow.
    def __init__(self, label: str | None = None):
        """Initialize rollback state for one logical Sheets write operation.

        Args:
            label: Optional diagnostic label for the operation group.

        Side effects:
            Creates in-memory rollback action storage only. No Sheets read/write
            happens during initialization.
        """
        self.label = label or "sheets_operation"
        # Run this statement as part of the current workflow.
        self.rollback_actions = []
        # Run this statement as part of the current workflow.
        self.rollback_errors = []
        # Run this statement as part of the current workflow.
        self.rolled_back = False
        # Run this statement as part of the current workflow.
        self.failed = False

    # Define add rollback for callers in this flow.
    def add_rollback(self, description: str, action):
        """Register a rollback action for a successful Sheets mutation.

        Args:
            description: Short label used if rollback fails.
            action: Callable that reverses the successful mutation.

        Side effects:
            Appends the rollback action unless this transaction already rolled
            back. The action is not executed here.
        """
        # Handle the case where self.rolled_back.
        if self.rolled_back:
            # Return control to the caller.
            return
        # Run this statement as part of the current workflow.
        self.rollback_actions.append((description, action))

    # Define rollback for callers in this flow.
    def rollback(self) -> bool:
        """Execute registered rollback actions in reverse order.

        Returns:
            `True` when every rollback action succeeds, otherwise `False`.

        Side effects:
            Calls each rollback action, records rollback error messages, and
            clears pending rollback actions after execution.
        """
        # Handle the case where self.rolled_back.
        if self.rolled_back:
            # Return len(self.rollback_errors) == 0 to the caller.
            return len(self.rollback_errors) == 0

        # Run this statement as part of the current workflow.
        self.rolled_back = True

        # Process each description, action in the current collection.
        for description, action in reversed(self.rollback_actions):
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Run this statement as part of the current workflow.
                action()
            # Handle an expected failure from the guarded operation above.
            except Exception as exc:
                self.rollback_errors.append(f"{description}: {exc}")

        # Run this statement as part of the current workflow.
        self.rollback_actions.clear()
        # Return len(self.rollback_errors) == 0 to the caller.
        return len(self.rollback_errors) == 0


# Apply this decorator before the callable is registered or executed.
@contextmanager
# Define sheets transaction for callers in this flow.
def sheets_transaction(label: str | None = None):
    """Group related Google Sheets writes under one rollback context.

    Args:
        label: Optional diagnostic label for the logical write operation.

    Yields:
        Active `SheetsTransaction`. Nested calls reuse the current transaction.

    Side effects:
        Sets a context-local transaction. If an exception escapes the block,
        registered rollback actions are executed before the exception is raised.
    """
    # Prepare parent for the next step.
    parent = _current_transaction.get()
    # Handle the case where parent is not None.
    if parent is not None:
        # Nested writes share the outer rollback boundary.
        yield parent
        # Return control to the caller.
        return

    # Prepare tx for the next step.
    tx = SheetsTransaction(label=label)
    # Prepare token for the next step.
    token = _current_transaction.set(tx)

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Run this statement as part of the current workflow.
        yield tx
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Run this statement as part of the current workflow.
        tx.failed = True
        # Run this statement as part of the current workflow.
        tx.rollback()
        # Run this statement as part of the current workflow.
        raise
    # Run cleanup that must happen after the guarded operation.
    finally:
        # Run this statement as part of the current workflow.
        _current_transaction.reset(token)


# Define rollback current sheets transaction for callers in this flow.
def rollback_current_sheets_transaction() -> bool:
    """Rollback the active Sheets transaction if one exists.

    Returns:
        `True` when an active transaction existed and rollback succeeded,
        otherwise `False`.

    Side effects:
        Marks the active transaction as failed and executes its rollback actions.
    """
    # Prepare tx for the next step.
    tx = _current_transaction.get()
    # Handle the case where tx is None.
    if tx is None:
        # Return False to the caller.
        return False

    # Run this statement as part of the current workflow.
    tx.failed = True
    # Return tx.rollback() to the caller.
    return tx.rollback()


# Define get current sheets transaction for callers in this flow.
def get_current_sheets_transaction() -> SheetsTransaction | None:
    """Return the current context-local Sheets transaction.

    Returns:
        Active `SheetsTransaction` or `None` when code is not inside a
        `sheets_transaction` block.
    """
    # Return _current_transaction.get() to the caller.
    return _current_transaction.get()


# Define is quota or transient error for callers in this flow.
def _is_quota_or_transient_error(exc: Exception) -> bool:
    """Check whether a condition is true for quota or transient error."""
    # Prepare msg for the next step.
    msg = str(exc).lower()
    # Return any( to the caller.
    return any(
        # Run this statement as part of the current workflow.
        marker in msg
        # Process each marker in the current collection.
        for marker in [
            "429",
            "quota exceeded",
            "too many requests",
            "rate limit",
            "rate_limit",
            "resource exhausted",
            "internal error",
            "backend error",
            "503",
            "500",
        # Close the structure that was opened above.
        ]
    # Close the structure that was opened above.
    )


# Define call with retry for callers in this flow.
def _call_with_retry(fn, *, max_retries: int | None = None):
    """Call a Sheets operation with retry for quota/transient failures.

    Args:
        fn: Zero-argument callable that performs the Sheets API operation.
        max_retries: Optional retry count override. Defaults to
            `SHEETS_MAX_RETRIES`.

    Returns:
        Whatever `fn` returns.

    Raises:
        The original exception when retries are exhausted or the error is not
        quota/transient.
    """
    retries = max_retries if max_retries is not None else int(os.getenv("SHEETS_MAX_RETRIES", "5"))
    base_delay = float(os.getenv("SHEETS_RETRY_BASE_DELAY", "1.0"))

    # Process each attempt in the current collection.
    for attempt in range(max(1, retries)):
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Return fn() to the caller.
            return fn()
        # Handle an expected failure from the guarded operation above.
        except Exception as exc:
            # Prepare is last for the next step.
            is_last = attempt >= retries - 1
            # Handle the case where is_last or not _is_quota_or_transient_error(exc).
            if is_last or not _is_quota_or_transient_error(exc):
                # Run this statement as part of the current workflow.
                raise

            # Prepare sleep time for the next step.
            sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
            # Run this statement as part of the current workflow.
            time.sleep(sleep_time)


# Define execute write for callers in this flow.
def _execute_write(fn):
    """Execute a Sheets write with retry and active-transaction rollback.

    Args:
        fn: Zero-argument callable that mutates Google Sheets.

    Returns:
        Result returned by `fn`.

    Raises:
        SheetsAtomicWriteError when the write fails inside an active transaction.

    Flow constraints:
        All sheet mutations should pass through this helper so quota failures do
        not silently leave partial writes.
    """
    # Prepare tx for the next step.
    tx = _current_transaction.get()

    # Handle the case where tx is not None and tx.failed.
    if tx is not None and tx.failed:
        # Raise a clear error so the caller can stop this invalid flow.
        raise SheetsAtomicWriteError(
            "Operasi Google Sheets sebelumnya sudah gagal dan sudah di-rollback. "
            "Input ini harus dianggap gagal, bukan sukses sebagian.",
            # Prepare rollback ok for the next step.
            rollback_ok=True,
        # Close the structure that was opened above.
        )

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Return _call_with_retry(fn) to the caller.
        return _call_with_retry(fn)
    # Handle an expected failure from the guarded operation above.
    except Exception as exc:
        # Handle the case where tx is not None.
        if tx is not None:
            # Run this statement as part of the current workflow.
            tx.failed = True
            # Prepare rollback ok for the next step.
            rollback_ok = tx.rollback()
            # Raise a clear error so the caller can stop this invalid flow.
            raise SheetsAtomicWriteError(
                # Include this value in the surrounding collection or call.
                exc,
                # Prepare rollback ok for the next step.
                rollback_ok=rollback_ok,
                # Prepare rollback errors for the next step.
                rollback_errors=tx.rollback_errors,
            # Close the structure that was opened above.
            ) from exc
        # Run this statement as part of the current workflow.
        raise


# Define execute read for callers in this flow.
def _execute_read(fn):
    """Execute a Sheets read with retry for transient API failures.

    Args:
        fn: Zero-argument callable that reads Google Sheets.

    Returns:
        Result returned by `fn`.
    """
    # Return _call_with_retry(fn) to the caller.
    return _call_with_retry(fn)


# Define get column letter for callers in this flow.
def _get_column_letter(col_number: int) -> str:
    """Convert a one-based column number into an A1 notation column letter.

    Args:
        col_number: One-based Google Sheets column number.

    Returns:
        Column letter such as `A`, `Z`, or `AA`. Invalid zero-like input falls
        back to `A`.
    """
    result = ""
    # Prepare number for the next step.
    number = int(col_number)
    # Repeat this block while number.
    while number:
        # Run this statement as part of the current workflow.
        number, remainder = divmod(number - 1, 26)
        # Prepare result for the next step.
        result = chr(65 + remainder) + result
    return result or "A"


# Define extract updated row index for callers in this flow.
def _extract_updated_row_index(response) -> int | None:
    """Extract the required part of input for updated row index."""
    text = str(response or "")
    match = re.search(r"![A-Z]+(\d+)(?::[A-Z]+(\d+))?", text)
    # Handle the case where match.
    if match:
        # Return int(match.group(1)) to the caller.
        return int(match.group(1))
    # Return None to the caller.
    return None


# Define extract updated row range for callers in this flow.
def _extract_updated_row_range(response) -> tuple[int, int] | None:
    """Extract the required part of input for updated row range."""
    text = str(response or "")
    match = re.search(r"![A-Z]+(\d+):[A-Z]+(\d+)", text)
    # Handle the case where match.
    if match:
        # Return int(match.group(1)), int(match.group(2)) to the caller.
        return int(match.group(1)), int(match.group(2))

    # Prepare row for the next step.
    row = _extract_updated_row_index(response)
    # Handle the case where row.
    if row:
        # Return row, row to the caller.
        return row, row
    # Return None to the caller.
    return None


# Define pad row for callers in this flow.
def _pad_row(row: list, width: int) -> list:
    """Normalize a row to an exact column width.

    Args:
        row: Source row values.
        width: Required output length.

    Returns:
        Row padded with empty strings or truncated to `width`.
    """
    # Prepare values for the next step.
    values = list(row or [])
    # Handle the case where len(values) < width.
    if len(values) < width:
        values += [""] * (width - len(values))
    # Return values[:width] to the caller.
    return values[:width]


# Define clean header for callers in this flow.
def _clean_header(values: list) -> list[str]:
    """Coordinate the clean header logic in the Google Sheets data layer.

    Args:
        values: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    return [str(value or "").strip() for value in values]


# Define has data rows for callers in this flow.
def _has_data_rows(values: list[list]) -> bool:
    """Coordinate the has data rows logic in the Google Sheets data layer.

    Args:
        values: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    return any(any(str(cell or "").strip() for cell in row) for row in values[1:])


# Define is blank header for callers in this flow.
def _is_blank_header(header: list[str]) -> bool:
    """Check whether a condition is true for blank header."""
    return not header or not any(str(cell or "").strip() for cell in header)


# Define header has expected prefix for callers in this flow.
def _header_has_expected_prefix(header: list[str], expected_header: list[str]) -> bool:
    """Check whether a sheet header starts with the expected schema columns.

    Args:
        header: Existing header row from Google Sheets.
        expected_header: Required schema header for the sheet.

    Returns:
        `True` when existing columns match the expected prefix exactly.
    """
    # Return header[:len(expected_header)] == expected_header to the caller.
    return header[:len(expected_header)] == expected_header


# Define header is safe prefix for callers in this flow.
def _header_is_safe_prefix(header: list[str], expected_header: list[str]) -> bool:
    """Check whether an old header is safe to extend without reordering.

    Args:
        header: Existing header row from Google Sheets.
        expected_header: Required schema header for the sheet.

    Returns:
        `True` when the existing header is a prefix of the expected schema.

    Flow constraints:
        This protects existing user sheets from destructive column reordering.
    """
    # Handle the case where len(header) > len(expected_header).
    if len(header) > len(expected_header):
        # Return False to the caller.
        return False
    # Return header == expected_header[:len(header)] to the caller.
    return header == expected_header[:len(header)]


# Define resize columns if needed for callers in this flow.
def _resize_columns_if_needed(sheet, width: int):
    """Ensure a worksheet has at least the required number of columns.

    Args:
        sheet: gspread worksheet object.
        width: Required minimum column count.

    Side effects:
        Adds columns to the worksheet only when it is too narrow.
    """
    current_cols = int(getattr(sheet, "col_count", 0) or 0)
    # Handle the case where current_cols < width.
    if current_cols < width:
        # Run this statement as part of the current workflow.
        _call_with_retry(lambda: sheet.add_cols(width - current_cols))


# Define write header for callers in this flow.
def _write_header(sheet, header: list[str]):
    """Write the schema header row to a worksheet.

    Args:
        sheet: gspread worksheet object.
        header: Ordered schema header values.

    Side effects:
        Resizes columns if needed and writes row 1 with `RAW` input option.
    """
    # Run this statement as part of the current workflow.
    _resize_columns_if_needed(sheet, len(header))
    # Prepare end col for the next step.
    end_col = _get_column_letter(len(header))
    _call_with_retry(lambda: sheet.update(f"A1:{end_col}1", [header], value_input_option="RAW"))


# Define default rows for sheet for callers in this flow.
def _default_rows_for_sheet(sheet_name: str) -> list[list]:
    """Return seed rows for a newly initialized sheet.

    Args:
        sheet_name: Google Sheets tab name.

    Returns:
        Default account/category rows for known seedable sheets, otherwise an
        empty list.
    """
    # Handle the case where sheet_name == SHEET_ACCOUNTS.
    if sheet_name == SHEET_ACCOUNTS:
        # Return DEFAULT_ACCOUNT_ROWS to the caller.
        return DEFAULT_ACCOUNT_ROWS
    # Handle the case where sheet_name == SHEET_CATEGORIES.
    if sheet_name == SHEET_CATEGORIES:
        # Return DEFAULT_CATEGORY_ROWS to the caller.
        return DEFAULT_CATEGORY_ROWS
    # Return [] to the caller.
    return []


# Define seed default rows if empty for callers in this flow.
def _seed_default_rows_if_empty(sheet_name: str, sheet, values: list[list]) -> list[str]:
    """Seed default rows only when a sheet has no user data.

    Args:
        sheet_name: Google Sheets tab name.
        sheet: gspread worksheet object.
        values: Existing worksheet values including header.

    Returns:
        Audit action labels for seeded rows, or an empty list.

    Side effects:
        Appends seed rows for supported sheets only when no data rows exist.
    """
    # Prepare default rows for the next step.
    default_rows = _default_rows_for_sheet(sheet_name)
    # Handle the missing or empty default_rows or _has_data_rows(values) case.
    if not default_rows or _has_data_rows(values):
        # Return [] to the caller.
        return []

    _call_with_retry(lambda: sheet.append_rows(default_rows, value_input_option="RAW"))
    return [f"seeded_default_rows:{sheet_name}:{len(default_rows)}"]


# Define get or create worksheet for callers in this flow.
def _get_or_create_worksheet(spreadsheet, sheet_name: str):
    """Fetch an existing worksheet or create it from known schema.

    Args:
        spreadsheet: gspread spreadsheet object.
        sheet_name: Required worksheet/tab name.

    Returns:
        gspread worksheet object.

    Raises:
        WorksheetNotFound for unknown sheet names without a schema.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Return _call_with_retry(lambda: spreadsheet.worksheet(sheet_name)) to the caller.
        return _call_with_retry(lambda: spreadsheet.worksheet(sheet_name))
    # Handle an expected failure from the guarded operation above.
    except WorksheetNotFound:
        # Prepare expected header for the next step.
        expected_header = SHEET_SCHEMAS.get(sheet_name)
        # Handle the missing or empty expected_header case.
        if not expected_header:
            # Run this statement as part of the current workflow.
            raise

        # Prepare rows for the next step.
        rows = max(100, len(_default_rows_for_sheet(sheet_name)) + 10)
        # Prepare cols for the next step.
        cols = max(10, len(expected_header))
        # Return _call_with_retry( to the caller.
        return _call_with_retry(
            # Run this statement as part of the current workflow.
            lambda: spreadsheet.add_worksheet(title=sheet_name, rows=rows, cols=cols)
        # Close the structure that was opened above.
        )


# Define ensure sheet schema for callers in this flow.
def ensure_sheet_schema(sheet_name: str, sheet=None) -> dict:
    """Ensure that setup is ready for sheet schema."""
    # Run this statement as part of the current workflow.
    global _worksheets, _schema_checked_sheets

    clean_name = str(sheet_name or "").strip()
    # Handle the missing or empty clean_name case.
    if not clean_name:
        raise ValueError("sheet_name kosong")

    # Prepare expected header for the next step.
    expected_header = SHEET_SCHEMAS.get(clean_name)
    # Handle the missing or empty expected_header case.
    if not expected_header:
        # Return { to the caller.
        return {
            "sheet": clean_name,
            "status": "skipped",
            "actions": [],
        # Close the structure that was opened above.
        }

    # Handle the case where sheet is None.
    if sheet is None:
        # Prepare spreadsheet for the next step.
        spreadsheet = get_spreadsheet()
        # Prepare sheet for the next step.
        sheet = _get_or_create_worksheet(spreadsheet, clean_name)
        # Run this statement as part of the current workflow.
        _worksheets[clean_name] = sheet

    # Prepare actions for the next step.
    actions = []
    # Read the whole sheet first because schema repair must be conservative when old data already exists.
    values = _call_with_retry(lambda: sheet.get_all_values())
    # Prepare header for the next step.
    header = _clean_header(values[0]) if values else []
    # Prepare header trimmed for the next step.
    header_trimmed = header[:len(expected_header)]
    # Prepare has data for the next step.
    has_data = _has_data_rows(values)

    # Handle the case where _is_blank_header(header).
    if _is_blank_header(header):
        # Run this statement as part of the current workflow.
        _write_header(sheet, expected_header)
        actions.append("header_created")
    # Handle the alternate case where _header_has_expected_prefix(header, expected_header).
    elif _header_has_expected_prefix(header, expected_header):
        # The header already matches. Extra columns after the main schema are left untouched.
        pass
    # Handle the alternate case where _header_is_safe_prefix(header_trimmed, expected_header).
    elif _header_is_safe_prefix(header_trimmed, expected_header):
        # Extend old-but-compatible headers, for example when a sheet is missing newly added optional columns.
        _write_header(sheet, expected_header)
        actions.append("header_extended")
    # Handle the alternate case where not has_data.
    elif not has_data:
        # Run this statement as part of the current workflow.
        _write_header(sheet, expected_header)
        actions.append("header_repaired_empty_sheet")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        existing_header = ", ".join([h for h in header if h]) or "-"
        # Raise a clear error so the caller can stop this invalid flow.
        raise ValueError(
            f"Format header sheet '{clean_name}' tidak cocok dan sheet sudah berisi data. "
            "Bot tidak mengubah urutan kolom otomatis agar data lama tidak rusak. "
            f"Header yang ada: {existing_header}. "
            f"Header yang dibutuhkan: {', '.join(expected_header)}"
        # Close the structure that was opened above.
        )

    # Re-read after header changes so default seeding uses the latest state.
    if actions:
        # Prepare values for the next step.
        values = _call_with_retry(lambda: sheet.get_all_values())

    # Update actions with the current value.
    actions.extend(_seed_default_rows_if_empty(clean_name, sheet, values))

    # Update schema checked sheets with the current value.
    _schema_checked_sheets.add(clean_name)
    # Return { to the caller.
    return {
        "sheet": clean_name,
        "status": "ok",
        "actions": actions or ["no_change"],
    # Close the structure that was opened above.
    }


# Define ensure spreadsheet schema for callers in this flow.
def ensure_spreadsheet_schema() -> list[dict]:
    """Ensure every configured worksheet exists and has a safe schema header.

    Returns:
        List of per-sheet schema check results.

    Side effects:
        May create missing worksheets, write blank headers, extend safe prefix
        headers, and seed default rows for supported empty sheets.
    """
    # Prepare spreadsheet for the next step.
    spreadsheet = get_spreadsheet()
    # Prepare results for the next step.
    results = []

    # Process each sheet_name in the current collection.
    for sheet_name in SHEET_SCHEMAS:
        # Prepare sheet for the next step.
        sheet = _get_or_create_worksheet(spreadsheet, sheet_name)
        # Run this statement as part of the current workflow.
        _worksheets[sheet_name] = sheet
        # Update results with the current value.
        results.append(ensure_sheet_schema(sheet_name, sheet=sheet))

    # Return results to the caller.
    return results


# Define get spreadsheet for callers in this flow.
def get_spreadsheet():
    """Return the cached authorized Google Spreadsheet object.

    Returns:
        gspread spreadsheet instance opened by configured spreadsheet ID.

    Side effects:
        Lazily authorizes the service-account client and caches the spreadsheet
        object for future calls.
    """
    # Run this statement as part of the current workflow.
    global _client, _spreadsheet

    # Handle the case where _spreadsheet is None.
    if _spreadsheet is None:
        # Open a multi-line structure for the values below.
        creds = Credentials.from_service_account_file(
            # Include this value in the surrounding collection or call.
            GOOGLE_SERVICE_ACCOUNT_JSON,
            # Prepare scopes for the next step.
            scopes=SCOPES,
        # Close the structure that was opened above.
        )
        # Prepare client for the next step.
        _client = gspread.authorize(creds)
        # Prepare spreadsheet for the next step.
        _spreadsheet = _call_with_retry(lambda: _client.open_by_key(GOOGLE_SHEET_ID))

    # Return _spreadsheet to the caller.
    return _spreadsheet


# Define get sheet for callers in this flow.
def get_sheet(sheet_name: str):
    """Return a cached worksheet and ensure schema when configured.

    Args:
        sheet_name: Google Sheets tab name.

    Returns:
        gspread worksheet object.

    Side effects:
        Lazily creates or fetches the worksheet and runs schema checks for known
        sheets once per process.
    """
    # Run this statement as part of the current workflow.
    global _worksheets

    clean_name = str(sheet_name or "").strip()
    # Handle the missing or empty clean_name case.
    if not clean_name:
        raise ValueError("sheet_name kosong")

    # Handle the case where clean_name not in _worksheets.
    if clean_name not in _worksheets:
        # Prepare spreadsheet for the next step.
        spreadsheet = get_spreadsheet()
        # Run this statement as part of the current workflow.
        _worksheets[clean_name] = _get_or_create_worksheet(spreadsheet, clean_name)

    # Handle the case where clean_name in SHEET_SCHEMAS and clean_name not in _schema_che....
    if clean_name in SHEET_SCHEMAS and clean_name not in _schema_checked_sheets:
        # Run this statement as part of the current workflow.
        ensure_sheet_schema(clean_name, sheet=_worksheets[clean_name])

    # Return _worksheets[clean_name] to the caller.
    return _worksheets[clean_name]


# Define append row for callers in this flow.
def append_row(sheet_name: str, row: list):
    """Append one row to a sheet with rollback tracking.

    Args:
        sheet_name: Target worksheet name.
        row: Ordered cell values to append with `RAW` input option.

    Returns:
        gspread append response.

    Side effects:
        Writes one row to Google Sheets and registers a rollback delete action
        when inside `sheets_transaction`.
    """
    # Prepare sheet for the next step.
    sheet = get_sheet(sheet_name)
    response = _execute_write(lambda: sheet.append_row(row, value_input_option="RAW"))

    # Prepare tx for the next step.
    tx = _current_transaction.get()
    # Prepare row index for the next step.
    row_index = _extract_updated_row_index(response)
    # Handle the case where tx is not None and row_index.
    if tx is not None and row_index:
        # Open a multi-line structure for the values below.
        tx.add_rollback(
            f"delete appended row {sheet_name}!{row_index}",
            # Include this value in the surrounding collection or call.
            lambda sheet=sheet, row_index=row_index: _call_with_retry(lambda: sheet.delete_rows(row_index)),
        # Close the structure that was opened above.
        )

    # Return response to the caller.
    return response


# Define append row raw for callers in this flow.
def append_row_raw(sheet_name: str, row: list):
    """Append one raw row to a sheet with rollback tracking.

    Args:
        sheet_name: Target worksheet name.
        row: Ordered cell values to append with `RAW` input option.

    Returns:
        gspread append response.

    Side effects:
        Writes one row to Google Sheets and registers a rollback delete action
        when inside `sheets_transaction`.
    """
    # Prepare sheet for the next step.
    sheet = get_sheet(sheet_name)
    response = _execute_write(lambda: sheet.append_row(row, value_input_option="RAW"))

    # Prepare tx for the next step.
    tx = _current_transaction.get()
    # Prepare row index for the next step.
    row_index = _extract_updated_row_index(response)
    # Handle the case where tx is not None and row_index.
    if tx is not None and row_index:
        # Open a multi-line structure for the values below.
        tx.add_rollback(
            f"delete appended raw row {sheet_name}!{row_index}",
            # Include this value in the surrounding collection or call.
            lambda sheet=sheet, row_index=row_index: _call_with_retry(lambda: sheet.delete_rows(row_index)),
        # Close the structure that was opened above.
        )

    # Return response to the caller.
    return response


# Define append rows for callers in this flow.
def append_rows(sheet_name: str, rows: list[list]):
    """Append multiple rows to a sheet with rollback tracking.

    Args:
        sheet_name: Target worksheet name.
        rows: Ordered row values to append.

    Returns:
        gspread append response, or `None` when `rows` is empty.

    Side effects:
        Writes rows to Google Sheets and registers rollback deletion for the
        appended row range when inside `sheets_transaction`.
    """
    # Handle the missing or empty rows case.
    if not rows:
        # Return None to the caller.
        return None

    # Prepare sheet for the next step.
    sheet = get_sheet(sheet_name)
    response = _execute_write(lambda: sheet.append_rows(rows, value_input_option="RAW"))

    # Prepare tx for the next step.
    tx = _current_transaction.get()
    # Prepare row range for the next step.
    row_range = _extract_updated_row_range(response)
    # Handle the case where tx is not None and row_range.
    if tx is not None and row_range:
        # Run this statement as part of the current workflow.
        start_row, end_row = row_range
        # Open a multi-line structure for the values below.
        tx.add_rollback(
            f"delete appended rows {sheet_name}!{start_row}:{end_row}",
            # Open a multi-line structure for the values below.
            lambda sheet=sheet, start_row=start_row, end_row=end_row: _call_with_retry(
                # Run this statement as part of the current workflow.
                lambda: sheet.delete_rows(start_row, end_row)
            # Close the structure that was opened above.
            ),
        # Close the structure that was opened above.
        )

    # Return response to the caller.
    return response


# Define get all records for callers in this flow.
def get_all_records(sheet_name: str) -> list[dict]:
    """Read all records from a worksheet as dictionaries.

    Args:
        sheet_name: Source worksheet name.

    Returns:
        List of row dictionaries using the header row as keys.
    """
    # Prepare sheet for the next step.
    sheet = get_sheet(sheet_name)
    return _execute_read(lambda: sheet.get_all_records(value_render_option="UNFORMATTED_VALUE"))


# Define get all values for callers in this flow.
def get_all_values(sheet_name: str) -> list[list]:
    """Read all raw values from a worksheet.

    Args:
        sheet_name: Source worksheet name.

    Returns:
        Two-dimensional list of cell values.
    """
    # Prepare sheet for the next step.
    sheet = get_sheet(sheet_name)
    # Return _execute_read(lambda: sheet.get_all_values()) to the caller.
    return _execute_read(lambda: sheet.get_all_values())


# Define update cell for callers in this flow.
def update_cell(sheet_name: str, row: int, col: int, value):
    """Update one cell with rollback tracking.

    Args:
        sheet_name: Target worksheet name.
        row: One-based row number.
        col: One-based column number.
        value: New cell value written with `RAW` input option.

    Returns:
        gspread update response.

    Side effects:
        Writes the cell and registers a rollback restore action when inside
        `sheets_transaction`.
    """
    # Prepare sheet for the next step.
    sheet = get_sheet(sheet_name)
    # Prepare tx for the next step.
    tx = _current_transaction.get()

    # Prepare old value for the next step.
    old_value = None
    # Handle the case where tx is not None.
    if tx is not None:
        # Prepare old value for the next step.
        old_value = _execute_read(lambda: sheet.cell(row, col).value)

    # Prepare cell range for the next step.
    cell_range = f"{_get_column_letter(col)}{row}"
    response = _execute_write(lambda: sheet.update(cell_range, [[value]], value_input_option="RAW"))

    # Handle the case where tx is not None.
    if tx is not None:
        # Open a multi-line structure for the values below.
        tx.add_rollback(
            f"restore cell {sheet_name}!{cell_range}",
            # Open a multi-line structure for the values below.
            lambda sheet=sheet, cell_range=cell_range, old_value=old_value: _call_with_retry(
                lambda: sheet.update(cell_range, [[old_value]], value_input_option="RAW")
            # Close the structure that was opened above.
            ),
        # Close the structure that was opened above.
        )

    # Return response to the caller.
    return response


# Define find row index for callers in this flow.
def find_row_index(sheet_name: str, search_col: int, search_value: str) -> int | None:
    """Find the first row index whose column value matches text.

    Args:
        sheet_name: Worksheet name.
        search_col: One-based column number to scan.
        search_value: Case-insensitive value to match.

    Returns:
        One-based row index when found, otherwise `None`.
    """
    # Prepare sheet for the next step.
    sheet = get_sheet(sheet_name)
    # Prepare col values for the next step.
    col_values = _execute_read(lambda: sheet.col_values(search_col))

    # Process each i, val in the current collection.
    for i, val in enumerate(col_values):
        # Handle the case where str(val).strip().lower() == str(search_value).strip().lower().
        if str(val).strip().lower() == str(search_value).strip().lower():
            # Return i + 1 to the caller.
            return i + 1

    # Return None to the caller.
    return None


# Define delete row for callers in this flow.
def delete_row(sheet_name: str, row_index: int):
    """Delete one row through the rollback-aware bulk delete helper.

    Args:
        sheet_name: Target worksheet name.
        row_index: One-based row number to delete.

    Returns:
        Result from `delete_rows`.
    """
    # Run this statement as part of the current workflow.
    delete_rows(sheet_name, [row_index])


# Define delete rows for callers in this flow.
def delete_rows(sheet_name: str, row_indices: list[int]):
    """Delete rows from a sheet with rollback tracking.

    Args:
        sheet_name: Target worksheet name.
        row_indices: One-based row numbers to delete.

    Returns:
        List of gspread delete responses, or `None` when no rows are provided.

    Side effects:
        Deletes rows in descending order and registers rollback insert actions
        when inside `sheets_transaction`.
    """
    # Handle the missing or empty row_indices case.
    if not row_indices:
        # Return None to the caller.
        return None

    # Prepare sheet for the next step.
    sheet = get_sheet(sheet_name)
    # Prepare tx for the next step.
    tx = _current_transaction.get()

    # Prepare responses for the next step.
    responses = []
    # Process each row_index in the current collection.
    for row_index in sorted(set(int(i) for i in row_indices), reverse=True):
        # Prepare old row for the next step.
        old_row = None
        # Handle the case where tx is not None.
        if tx is not None:
            # Prepare old row for the next step.
            old_row = _execute_read(lambda row_index=row_index: sheet.row_values(row_index))

        # Prepare response for the next step.
        response = _execute_write(lambda row_index=row_index: sheet.delete_rows(row_index))
        # Update responses with the current value.
        responses.append(response)

        # Handle the case where tx is not None.
        if tx is not None:
            # Open a multi-line structure for the values below.
            tx.add_rollback(
                f"restore deleted row {sheet_name}!{row_index}",
                # Open a multi-line structure for the values below.
                lambda sheet=sheet, row_index=row_index, old_row=old_row: _call_with_retry(
                    lambda: sheet.insert_row(old_row or [], index=row_index, value_input_option="RAW")
                # Close the structure that was opened above.
                ),
            # Close the structure that was opened above.
            )

    # Return responses to the caller.
    return responses


# Define update row for callers in this flow.
def update_row(sheet_name: str, row_index: int, row_values: list):
    """Replace one row with rollback tracking.

    Args:
        sheet_name: Target worksheet name.
        row_index: One-based row number.
        row_values: Full row values matching the target schema width.

    Returns:
        gspread update response.

    Side effects:
        Updates the row range and registers rollback restore action when inside
        `sheets_transaction`.
    """
    # Prepare sheet for the next step.
    sheet = get_sheet(sheet_name)
    # Prepare tx for the next step.
    tx = _current_transaction.get()
    # Prepare width for the next step.
    width = len(row_values)

    # Prepare old row for the next step.
    old_row = None
    # Handle the case where tx is not None.
    if tx is not None:
        # Prepare old row for the next step.
        old_row = _pad_row(_execute_read(lambda: sheet.row_values(row_index)), width)

    # Prepare end col for the next step.
    end_col = _get_column_letter(width)
    cell_range = f"A{row_index}:{end_col}{row_index}"

    response = _execute_write(lambda: sheet.update(cell_range, [row_values], value_input_option="RAW"))

    # Handle the case where tx is not None.
    if tx is not None:
        # Open a multi-line structure for the values below.
        tx.add_rollback(
            f"restore row {sheet_name}!{row_index}",
            # Open a multi-line structure for the values below.
            lambda sheet=sheet, cell_range=cell_range, old_row=old_row: _call_with_retry(
                lambda: sheet.update(cell_range, [old_row or []], value_input_option="RAW")
            # Close the structure that was opened above.
            ),
        # Close the structure that was opened above.
        )

    # Return response to the caller.
    return response


# Define update range for callers in this flow.
def update_range(sheet_name: str, cell_range: str, values: list[list]):
    """Update an A1 range with rollback tracking.

    Args:
        sheet_name: Target worksheet name.
        cell_range: A1 range such as `A2:D4`.
        values: Two-dimensional values matching the range.

    Returns:
        gspread update response.

    Side effects:
        Updates the range and registers rollback restore action when inside
        `sheets_transaction`.
    """
    # Prepare sheet for the next step.
    sheet = get_sheet(sheet_name)
    # Prepare tx for the next step.
    tx = _current_transaction.get()

    # Prepare old values for the next step.
    old_values = None
    # Handle the case where tx is not None.
    if tx is not None:
        # Prepare old values for the next step.
        old_values = _execute_read(lambda: sheet.get(cell_range))

    response = _execute_write(lambda: sheet.update(cell_range, values, value_input_option="RAW"))

    # Handle the case where tx is not None.
    if tx is not None:
        # Open a multi-line structure for the values below.
        tx.add_rollback(
            f"restore range {sheet_name}!{cell_range}",
            # Open a multi-line structure for the values below.
            lambda sheet=sheet, cell_range=cell_range, old_values=old_values: _call_with_retry(
                lambda: sheet.update(cell_range, old_values or [], value_input_option="RAW")
            # Close the structure that was opened above.
            ),
        # Close the structure that was opened above.
        )

    # Return response to the caller.
    return response
