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
import copy
import threading
from dataclasses import dataclass, field
# Import contextlib so this module can use its helpers.
from contextlib import contextmanager

# Import gspread for this module's local operations.
import gspread
# Import gspread.exceptions so this module can use its helpers.
from gspread.exceptions import WorksheetNotFound
# Import google.oauth2.service_account so this module can use its helpers.
from google.oauth2.service_account import Credentials
# Import app.config so this module can use its helpers.
from app.observability import emit_event, increment_metric
from app.config import (
    GOOGLE_SERVICE_ACCOUNT_JSON,
    GOOGLE_SHEET_ID,
    SHEET_ACCOUNTS,
    SHEET_ASSETS,
    SHEET_BUDGETS,
    SHEET_CATEGORIES,
    SHEET_DEBT_PAYMENTS,
    SHEET_DEBTS,
    SHEET_MONTHLY_SUMMARY,
    SHEET_NET_WORTH_SNAPSHOTS,
    SHEET_PENDING_EXPENSES,
    SHEET_RECURRING_LOGS,
    SHEET_RECURRING_RULES,
    SHEET_TRANSACTIONS,
    SHEETS_REQUEST_ROW_BUDGET,
)

# Required scopes for reading and writing Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

_client = None
_spreadsheet = None
_worksheets = {}
_schema_checked_sheets = set()
_current_transaction = contextvars.ContextVar("sheets_current_transaction", default=None)
_request_snapshot = contextvars.ContextVar("sheets_request_snapshot", default=None)


class SheetsReadBudgetExceeded(RuntimeError):
    """A logical request exceeded its configured row-transfer budget."""


@dataclass
class SheetsRequestSnapshot:
    """Mutable request-local cache shared with worker context copies."""

    row_budget: int = SHEETS_REQUEST_ROW_BUDGET
    records: dict[str, list[dict]] = field(default_factory=dict)
    values: dict[str, list[list]] = field(default_factory=dict)
    rows_read: int = 0
    calls_by_sheet: dict[str, int] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record_read(self, sheet_name: str, rows: int) -> None:
        with self.lock:
            next_total = self.rows_read + max(0, int(rows))
            if next_total > self.row_budget:
                raise SheetsReadBudgetExceeded(
                    f"Batas row read request terlampaui: {next_total}>{self.row_budget}."
                )
            self.rows_read = next_total
            self.calls_by_sheet[sheet_name] = self.calls_by_sheet.get(sheet_name, 0) + 1

    def invalidate(self) -> None:
        with self.lock:
            self.records.clear()
            self.values.clear()


@contextmanager
def sheets_request_snapshot(*, row_budget: int | None = None):
    """Reuse worksheet reads only for the current logical request or job."""

    existing = _request_snapshot.get()
    if existing is not None:
        yield existing
        return
    snapshot = SheetsRequestSnapshot(row_budget=int(row_budget or SHEETS_REQUEST_ROW_BUDGET))
    token = _request_snapshot.set(snapshot)
    try:
        yield snapshot
    finally:
        _request_snapshot.reset(token)


# Central schema definition for all required Google Sheets tabs.

SHEET_SCHEMAS = {
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
    ],
    SHEET_ACCOUNTS: [
        "account_name",
        "type",
        "balance",
        "currency",
        "last_updated",
    ],
    SHEET_BUDGETS: [
        "id",
        "month",
        "category",
        "budget_amount",
        "created_at",
        "updated_at",
    ],
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
    ],
    SHEET_DEBT_PAYMENTS: [
        "id",
        "debt_id",
        "amount",
        "date",
        "note",
    ],
    # categories uses the existing spreadsheet format: category_name, type, emoji, aliases.
    # aliases is a comma-separated keyword list used as category metadata.
    SHEET_CATEGORIES: [
        "category_name",
        "type",
        "emoji",
        "aliases",
    ],
    SHEET_MONTHLY_SUMMARY: [
        "month",
        "total_income",
        "total_expense",
        "net",
        "created_at",
        "updated_at",
    ],
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
    ],
    SHEET_RECURRING_LOGS: [
        "id",
        "rule_id",
        "transaction_id",
        "run_date",
        "status",
        "message",
        "created_at",
    ],
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
    ],
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
    ],
    SHEET_NET_WORTH_SNAPSHOTS: [
        "id",
        "snapshot_date",
        "total_accounts",
        "total_assets",
        "total_liabilities",
        "net_worth",
        "created_at",
    ],
}


DEFAULT_ACCOUNT_ROWS = [
    ["Cash", "cash", 0, "IDR", ""],
    ["BRI", "bank", 0, "IDR", ""],
    ["BSI", "bank", 0, "IDR", ""],
    ["BCA", "bank", 0, "IDR", ""],
    ["DANA", "ewallet", 0, "IDR", ""],
    ["GoPay", "ewallet", 0, "IDR", ""],
    ["Seabank", "bank", 0, "IDR", ""],
]


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
]


# Group the SheetsAtomicWriteError behavior in one class.
class SheetsAtomicWriteError(RuntimeError):
    """Error raised when a Google Sheets write fails after retries and rollback handling is attempted."""

    # Helper for init.
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
        self.original_error = original_error
        self.rollback_ok = rollback_ok
        self.rollback_errors = rollback_errors or []

        base = str(original_error)
        if rollback_ok is True:
            message = (
                "Google Sheets write gagal setelah retry. "
                "Semua perubahan dari operasi ini sudah di-rollback. "
                f"Detail: {base}"
            )
        # Fall back when rollback ok is False.
        elif rollback_ok is False:
            rollback_detail = "; ".join(self.rollback_errors) if self.rollback_errors else "rollback gagal tanpa detail"
            message = (
                "Google Sheets write gagal setelah retry. "
                "Sebagian rollback juga gagal, kemungkinan karena quota masih habis. "
                f"Cek sheet manual. Detail: {base}. Rollback: {rollback_detail}"
            )
        # Use the fallback path when no earlier branch matched.
        else:
            message = base

        super().__init__(message)


class SheetsCommitOutcomeUnknownError(RuntimeError):
    """Signal that a non-idempotent mutation may have committed remotely."""

    def __init__(self, operation: str, original_error: Exception, detail: str | None = None):
        self.operation = operation
        self.original_error = original_error
        self.detail = detail or ""
        message = (
            f"Hasil operasi Google Sheets `{operation}` tidak dapat dipastikan. "
            "Jangan ulangi mutation sebelum rekonsiliasi logical ID."
        )
        if self.detail:
            message += f" Detail: {self.detail}"
        super().__init__(message)


# Schema compatibility note for Google Sheets headers and rows.

# Group the SheetsTransaction behavior in one class.
class SheetsTransaction:
    """Best-effort transaction wrapper for Google Sheets writes. It records successful writes and tries to roll them back if a later write fails."""

    # Helper for init.
    def __init__(self, label: str | None = None):
        """Initialize rollback state for one logical Sheets write operation.

        Args:
            label: Optional diagnostic label for the operation group.

        Side effects:
            Creates in-memory rollback action storage only. No Sheets read/write
            happens during initialization.
        """
        self.label = label or "sheets_operation"
        self.rollback_actions = []
        self.rollback_errors = []
        self.post_commit_actions = {}
        self.post_commit_errors = []
        self.rolled_back = False
        self.failed = False

    # Helper for add rollback.
    def add_rollback(self, description: str, action):
        """Register a rollback action for a successful Sheets mutation.

        Args:
            description: Short label used if rollback fails.
            action: Callable that reverses the successful mutation.

        Side effects:
            Appends the rollback action unless this transaction already rolled
            back. The action is not executed here.
        """
        if self.rolled_back:
            return
        self.rollback_actions.append((description, action))

    def add_post_commit(self, key: str, description: str, action) -> None:
        """Register one deduplicated maintenance action after finance commit.

        Post-commit maintenance must never participate in financial rollback.
        Registering the same key again replaces nothing and keeps the first
        action, which prevents a batch of saves from scheduling duplicate sorts.
        """

        if self.rolled_back or self.failed:
            return
        self.post_commit_actions.setdefault(str(key), (description, action))

    def run_post_commit(self) -> bool:
        """Run best-effort maintenance after the financial transaction commits."""

        actions = list(self.post_commit_actions.values())
        self.post_commit_actions.clear()
        for description, action in actions:
            try:
                action()
                increment_metric("sheets.post_commit.completed")
            except Exception as exc:
                self.post_commit_errors.append(f"{description}: {exc}")
                increment_metric("sheets.post_commit.failed")
                emit_event(
                    "sheets_post_commit_failed",
                    transaction_label=self.label,
                    maintenance=description,
                    error_type=type(exc).__name__,
                )
        return not self.post_commit_errors

    # Helper for rollback.
    def rollback(self) -> bool:
        """Execute registered rollback actions in reverse order.

        Returns:
            `True` when every rollback action succeeds, otherwise `False`.

        Side effects:
            Calls each rollback action, records rollback error messages, and
            clears pending rollback actions after execution.
        """
        if self.rolled_back:
            return len(self.rollback_errors) == 0

        self.rolled_back = True

        # Iterate through each description, action.
        for description, action in reversed(self.rollback_actions):
            # Run this operation in a guarded block so failures can be handled.
            try:
                action()
            # Handle an expected failure from the guarded operation above.
            except Exception as exc:
                self.rollback_errors.append(f"{description}: {exc}")

        self.rollback_actions.clear()
        self.post_commit_actions.clear()
        return len(self.rollback_errors) == 0


# Apply this decorator before the callable is registered or executed.
@contextmanager
# Helper for sheets transaction.
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
    parent = _current_transaction.get()
    if parent is not None:
        # Nested writes share the outer rollback boundary.
        yield parent
        return

    tx = SheetsTransaction(label=label)
    token = _current_transaction.set(tx)

    # Run this operation in a guarded block so failures can be handled.
    try:
        yield tx
    # Handle an expected failure from the guarded operation above.
    except Exception:
        tx.failed = True
        tx.rollback()
        raise
    else:
        if not tx.failed and not tx.rolled_back:
            # Maintenance such as worksheet sorting runs outside the rollback
            # context.  A maintenance failure must not undo committed finance
            # rows or account balances.
            maintenance_token = _current_transaction.set(None)
            try:
                tx.run_post_commit()
            finally:
                _current_transaction.reset(maintenance_token)
    # Run cleanup that must happen after the guarded operation.
    finally:
        _current_transaction.reset(token)


# Helper for rollback current sheets transaction.
def rollback_current_sheets_transaction() -> bool:
    """Rollback the active Sheets transaction if one exists.

    Returns:
        `True` when an active transaction existed and rollback succeeded,
        otherwise `False`.

    Side effects:
        Marks the active transaction as failed and executes its rollback actions.
    """
    tx = _current_transaction.get()
    if tx is None:
        return False

    tx.failed = True
    return tx.rollback()


# Helper for get current sheets transaction.
def get_current_sheets_transaction() -> SheetsTransaction | None:
    """Return the current context-local Sheets transaction.

    Returns:
        Active `SheetsTransaction` or `None` when code is not inside a
        `sheets_transaction` block.
    """
    return _current_transaction.get()


# Helper for is quota or transient error.
def _is_quota_or_transient_error(exc: Exception) -> bool:
    """Check whether a condition is true for quota or transient error."""
    msg = str(exc).lower()
    return any(
        marker in msg
        # Iterate through each marker.
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
        ]
    )


# Helper for call with retry.
def _call_with_retry(
    fn,
    *,
    max_retries: int | None = None,
    operation: str = "read",
    reconcile=None,
):
    """Call a Sheets operation with retry for quota/transient failures.

    Args:
        fn: Zero-argument callable that performs the Sheets API operation.
        max_retries: Optional retry count override. Defaults to
            `SHEETS_MAX_RETRIES`.
        operation: ``read`` or ``idempotent_write`` may be retried directly.
            ``non_idempotent_write`` requires reconciliation after an
            ambiguous transient error.
        reconcile: Optional zero-argument lookup. Return a non-``None`` value
            when the logical mutation already exists remotely; return ``None``
            only when a successful lookup proves it is absent.

    Returns:
        Whatever `fn` returns.

    Raises:
        The original exception when retries are exhausted or the error is not
        quota/transient.
    """
    retries = max_retries if max_retries is not None else int(os.getenv("SHEETS_MAX_RETRIES", "5"))
    base_delay = float(os.getenv("SHEETS_RETRY_BASE_DELAY", "1.0"))

    # Iterate through each attempt.
    for attempt in range(max(1, retries)):
        # Run this operation in a guarded block so failures can be handled.
        try:
            return fn()
        # Handle an expected failure from the guarded operation above.
        except Exception as exc:
            is_last = attempt >= retries - 1
            # Handle is last or not is quota or transient error(exc).
            if is_last or not _is_quota_or_transient_error(exc):
                raise

            if operation == "non_idempotent_write":
                if reconcile is None:
                    raise SheetsCommitOutcomeUnknownError(operation, exc, "reconciliation callback tidak tersedia") from exc
                try:
                    reconciled = reconcile()
                except SheetsCommitOutcomeUnknownError:
                    raise
                except Exception as reconcile_error:
                    raise SheetsCommitOutcomeUnknownError(
                        operation,
                        exc,
                        f"lookup gagal: {reconcile_error}",
                    ) from reconcile_error
                if reconciled is not None:
                    return reconciled

            sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
            time.sleep(sleep_time)


# Helper for execute write.
def _execute_write(fn, *, operation: str = "idempotent_write", reconcile=None):
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
    tx = _current_transaction.get()

    if tx is not None and tx.failed:
        # Raise a clear error so the caller can stop this invalid flow.
        raise SheetsAtomicWriteError(
            "Operasi Google Sheets sebelumnya sudah gagal dan sudah di-rollback. "
            "Input ini harus dianggap gagal, bukan sukses sebagian.",
            rollback_ok=True,
        )

    # Run this operation in a guarded block so failures can be handled.
    try:
        result = _call_with_retry(fn, operation=operation, reconcile=reconcile)
        snapshot = _request_snapshot.get()
        if snapshot is not None:
            snapshot.invalidate()
        return result
    # Handle an expected failure from the guarded operation above.
    except Exception as exc:
        if tx is not None:
            tx.failed = True
            rollback_ok = tx.rollback()
            # Raise a clear error so the caller can stop this invalid flow.
            raise SheetsAtomicWriteError(
                exc,
                rollback_ok=rollback_ok,
                rollback_errors=tx.rollback_errors,
            ) from exc
        raise


# Helper for execute read.
def _execute_read(fn):
    """Execute a Sheets read with retry for transient API failures.

    Args:
        fn: Zero-argument callable that reads Google Sheets.

    Returns:
        Result returned by `fn`.
    """
    return _call_with_retry(fn)


# Helper for get column letter.
def _get_column_letter(col_number: int) -> str:
    """Convert a one-based column number into an A1 notation column letter.

    Args:
        col_number: One-based Google Sheets column number.

    Returns:
        Column letter such as `A`, `Z`, or `AA`. Invalid zero-like input falls
        back to `A`.
    """
    result = ""
    number = int(col_number)
    # Repeat this block while number.
    while number:
        number, remainder = divmod(number - 1, 26)
        # Build result for the response flow.
        result = chr(65 + remainder) + result
    return result or "A"


# Helper for extract updated row index.
def _extract_updated_row_index(response) -> int | None:
    """Extract the required part of input for updated row index."""
    text = str(response or "")
    match = re.search(r"![A-Z]+(\d+)(?::[A-Z]+(\d+))?", text)
    if match:
        return int(match.group(1))
    return None


# Helper for extract updated row range.
def _extract_updated_row_range(response) -> tuple[int, int] | None:
    """Extract the required part of input for updated row range."""
    text = str(response or "")
    match = re.search(r"![A-Z]+(\d+):[A-Z]+(\d+)", text)
    if match:
        return int(match.group(1)), int(match.group(2))

    row = _extract_updated_row_index(response)
    if row:
        return row, row
    return None


# Helper for pad row.
def _pad_row(row: list, width: int) -> list:
    """Normalize a row to an exact column width.

    Args:
        row: Source row values.
        width: Required output length.

    Returns:
        Row padded with empty strings or truncated to `width`.
    """
    values = list(row or [])
    if len(values) < width:
        values += [""] * (width - len(values))
    return values[:width]


# Helper for clean header.
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


# Helper for has data rows.
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


# Helper for is blank header.
def _is_blank_header(header: list[str]) -> bool:
    """Check whether a condition is true for blank header."""
    return not header or not any(str(cell or "").strip() for cell in header)


# Helper for header has expected prefix.
def _header_has_expected_prefix(header: list[str], expected_header: list[str]) -> bool:
    """Check whether a sheet header starts with the expected schema columns.

    Args:
        header: Existing header row from Google Sheets.
        expected_header: Required schema header for the sheet.

    Returns:
        `True` when existing columns match the expected prefix exactly.
    """
    return header[:len(expected_header)] == expected_header


# Helper for header is safe prefix.
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
    if len(header) > len(expected_header):
        return False
    return header == expected_header[:len(header)]


# Helper for resize columns if needed.
def _resize_columns_if_needed(sheet, width: int):
    """Ensure a worksheet has at least the required number of columns.

    Args:
        sheet: gspread worksheet object.
        width: Required minimum column count.

    Side effects:
        Adds columns to the worksheet only when it is too narrow.
    """
    current_cols = int(getattr(sheet, "col_count", 0) or 0)
    if current_cols < width:
        _call_with_retry(lambda: sheet.add_cols(width - current_cols))


# Helper for write header.
def _write_header(sheet, header: list[str]):
    """Write the schema header row to a worksheet.

    Args:
        sheet: gspread worksheet object.
        header: Ordered schema header values.

    Side effects:
        Resizes columns if needed and writes row 1 with `RAW` input option.
    """
    _resize_columns_if_needed(sheet, len(header))
    end_col = _get_column_letter(len(header))
    _call_with_retry(lambda: sheet.update(f"A1:{end_col}1", [header], value_input_option="RAW"))


# Helper for default rows for sheet.
def _default_rows_for_sheet(sheet_name: str) -> list[list]:
    """Return seed rows for a newly initialized sheet.

    Args:
        sheet_name: Google Sheets tab name.

    Returns:
        Default account/category rows for known seedable sheets, otherwise an
        empty list.
    """
    if sheet_name == SHEET_ACCOUNTS:
        return DEFAULT_ACCOUNT_ROWS
    if sheet_name == SHEET_CATEGORIES:
        return DEFAULT_CATEGORY_ROWS
    return []


# Helper for seed default rows if empty.
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
    # Load default rows for the current calculation.
    default_rows = _default_rows_for_sheet(sheet_name)
    # Validate missing default rows or has data rows(values) before continuing.
    if not default_rows or _has_data_rows(values):
        return []

    _call_with_retry(lambda: sheet.append_rows(default_rows, value_input_option="RAW"))
    return [f"seeded_default_rows:{sheet_name}:{len(default_rows)}"]


# Helper for get or create worksheet.
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
        return _call_with_retry(lambda: spreadsheet.worksheet(sheet_name))
    # Handle an expected failure from the guarded operation above.
    except WorksheetNotFound:
        expected_header = SHEET_SCHEMAS.get(sheet_name)
        # Validate missing expected header before continuing.
        if not expected_header:
            raise

        # Load rows for the current calculation.
        rows = max(100, len(_default_rows_for_sheet(sheet_name)) + 10)
        cols = max(10, len(expected_header))
        return _call_with_retry(
            lambda: spreadsheet.add_worksheet(title=sheet_name, rows=rows, cols=cols)
        )


# Helper for ensure sheet schema.
def ensure_sheet_schema(sheet_name: str, sheet=None) -> dict:
    """Ensure that setup is ready for sheet schema."""
    global _worksheets, _schema_checked_sheets

    clean_name = str(sheet_name or "").strip()
    # Validate missing clean name before continuing.
    if not clean_name:
        raise ValueError("sheet_name kosong")

    expected_header = SHEET_SCHEMAS.get(clean_name)
    # Validate missing expected header before continuing.
    if not expected_header:
        return {
            "sheet": clean_name,
            "status": "skipped",
            "actions": [],
        }

    if sheet is None:
        spreadsheet = get_spreadsheet()
        sheet = _get_or_create_worksheet(spreadsheet, clean_name)
        _worksheets[clean_name] = sheet

    actions = []
    # Read the whole sheet first because schema repair must be conservative when old data already exists.
    values = _call_with_retry(lambda: sheet.get_all_values())
    header = _clean_header(values[0]) if values else []
    header_trimmed = header[:len(expected_header)]
    has_data = _has_data_rows(values)

    if _is_blank_header(header):
        _write_header(sheet, expected_header)
        actions.append("header_created")
    # Fall back when header has expected prefix(header, expected header).
    elif _header_has_expected_prefix(header, expected_header):
        # The header already matches. Extra columns after the main schema are left untouched.
        pass
    # Fall back when header is safe prefix(header trimmed, expected header).
    elif _header_is_safe_prefix(header_trimmed, expected_header):
        # Extend old-but-compatible headers, for example when a sheet is missing newly added optional columns.
        _write_header(sheet, expected_header)
        actions.append("header_extended")
    # Fall back when not has data.
    elif not has_data:
        _write_header(sheet, expected_header)
        actions.append("header_repaired_empty_sheet")
    # Use the fallback path when no earlier branch matched.
    else:
        existing_header = ", ".join([h for h in header if h]) or "-"
        # Raise a clear error so the caller can stop this invalid flow.
        raise ValueError(
            f"Format header sheet '{clean_name}' tidak cocok dan sheet sudah berisi data. "
            "Bot tidak mengubah urutan kolom otomatis agar data lama tidak rusak. "
            f"Header yang ada: {existing_header}. "
            f"Header yang dibutuhkan: {', '.join(expected_header)}"
        )

    # Re-read after header changes so default seeding uses the latest state.
    if actions:
        values = _call_with_retry(lambda: sheet.get_all_values())

    # Append the current value to actions.
    actions.extend(_seed_default_rows_if_empty(clean_name, sheet, values))

    # Append the current value to schema checked sheets.
    _schema_checked_sheets.add(clean_name)
    return {
        "sheet": clean_name,
        "status": "ok",
        "actions": actions or ["no_change"],
    }


# Helper for ensure spreadsheet schema.
def ensure_spreadsheet_schema() -> list[dict]:
    """Ensure every configured worksheet exists and has a safe schema header.

    Returns:
        List of per-sheet schema check results.

    Side effects:
        May create missing worksheets, write blank headers, extend safe prefix
        headers, and seed default rows for supported empty sheets.
    """
    spreadsheet = get_spreadsheet()
    # Build results for the response flow.
    results = []

    # Iterate through each sheet name.
    for sheet_name in SHEET_SCHEMAS:
        sheet = _get_or_create_worksheet(spreadsheet, sheet_name)
        _worksheets[sheet_name] = sheet
        # Append the current value to results.
        results.append(ensure_sheet_schema(sheet_name, sheet=sheet))

    return results


# Helper for get spreadsheet.
def get_spreadsheet():
    """Return the cached authorized Google Spreadsheet object.

    Returns:
        gspread spreadsheet instance opened by configured spreadsheet ID.

    Side effects:
        Lazily authorizes the service-account client and caches the spreadsheet
        object for future calls.
    """
    global _client, _spreadsheet

    if _spreadsheet is None:
        creds = Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_JSON,
            scopes=SCOPES,
        )
        _client = gspread.authorize(creds)
        _spreadsheet = _call_with_retry(lambda: _client.open_by_key(GOOGLE_SHEET_ID))

    return _spreadsheet


# Helper for get sheet.
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
    global _worksheets

    clean_name = str(sheet_name or "").strip()
    # Validate missing clean name before continuing.
    if not clean_name:
        raise ValueError("sheet_name kosong")

    if clean_name not in _worksheets:
        spreadsheet = get_spreadsheet()
        _worksheets[clean_name] = _get_or_create_worksheet(spreadsheet, clean_name)

    # Handle clean name in SHEET SCHEMAS and clean name not in schema che.
    if clean_name in SHEET_SCHEMAS and clean_name not in _schema_checked_sheets:
        ensure_sheet_schema(clean_name, sheet=_worksheets[clean_name])

    return _worksheets[clean_name]


def _first_column_values(sheet) -> list[str]:
    """Read first-column logical IDs through the retry-safe read policy."""

    if hasattr(sheet, "col_values"):
        values = _call_with_retry(lambda: sheet.col_values(1), operation="read")
    else:
        rows = _call_with_retry(lambda: sheet.get_all_values(), operation="read")
        values = [row[0] if row else "" for row in rows]
    return [str(value or "").strip() for value in values]


def _synthetic_append_response(sheet, start_row: int, end_row: int | None = None) -> dict:
    """Build a gspread-like response for a remotely reconciled append."""

    title = str(getattr(sheet, "title", "Sheet1") or "Sheet1")
    last_row = end_row or start_row
    return {"updates": {"updatedRange": f"{title}!A{start_row}:Z{last_row}"}, "reconciled": True}


def _reconcile_single_append(sheet, logical_id: str) -> dict | None:
    """Return a synthetic success only when exactly one logical ID exists."""

    matches = [index for index, value in enumerate(_first_column_values(sheet), start=1) if value == logical_id]
    if len(matches) == 1:
        return _synthetic_append_response(sheet, matches[0])
    if len(matches) > 1:
        raise SheetsCommitOutcomeUnknownError("append", RuntimeError("duplicate logical ID"), logical_id)
    return None


def _reconcile_batch_append(sheet, logical_ids: list[str]) -> dict | None:
    """Reconcile a batch only when all IDs exist exactly once or none exist."""

    values = _first_column_values(sheet)
    positions = {logical_id: [i for i, value in enumerate(values, start=1) if value == logical_id] for logical_id in logical_ids}
    found = {logical_id: rows for logical_id, rows in positions.items() if rows}
    if not found:
        return None
    if len(found) != len(logical_ids) or any(len(rows) != 1 for rows in positions.values()):
        raise SheetsCommitOutcomeUnknownError(
            "batch_append",
            RuntimeError("partial or duplicate logical IDs"),
            ", ".join(sorted(found)),
        )
    row_numbers = sorted(rows[0] for rows in positions.values())
    if row_numbers != list(range(row_numbers[0], row_numbers[-1] + 1)):
        raise SheetsCommitOutcomeUnknownError("batch_append", RuntimeError("reconciled rows are not contiguous"))
    return _synthetic_append_response(sheet, row_numbers[0], row_numbers[-1])


def _delete_rows_by_logical_ids(sheet, logical_ids: list[str]) -> None:
    """Delete exactly one current row per immutable first-column logical ID."""

    normalized = [str(value or "").strip() for value in logical_ids if str(value or "").strip()]
    values = _first_column_values(sheet)
    positions: list[int] = []
    for logical_id in normalized:
        matches = [index for index, value in enumerate(values, start=1) if value == logical_id]
        if len(matches) != 1:
            raise RuntimeError(
                f"Rollback logical ID {logical_id!r} membutuhkan tepat satu row, ditemukan {len(matches)}."
            )
        positions.append(matches[0])

    # Delete from the bottom so earlier row indexes remain valid.
    for row_index in sorted(positions, reverse=True):
        _call_with_retry(lambda row_index=row_index: sheet.delete_rows(row_index))


# Helper for append row.
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
    sheet = get_sheet(sheet_name)
    logical_id = str(row[0] if row else "").strip()
    reconcile = (lambda: _reconcile_single_append(sheet, logical_id)) if logical_id else None
    response = _execute_write(
        lambda: sheet.append_row(row, value_input_option="RAW"),
        operation="non_idempotent_write",
        reconcile=reconcile,
    )

    tx = _current_transaction.get()
    row_index = _extract_updated_row_index(response)
    # Prefer immutable logical identity because post-append sorting can move the
    # row before a later finance mutation fails.
    if tx is not None and logical_id:
        tx.add_rollback(
            f"delete appended logical row {sheet_name}:{logical_id}",
            lambda sheet=sheet, logical_id=logical_id: _delete_rows_by_logical_ids(sheet, [logical_id]),
        )
    elif tx is not None and row_index:
        tx.add_rollback(
            f"delete appended row {sheet_name}!{row_index}",
            lambda sheet=sheet, row_index=row_index: _call_with_retry(lambda: sheet.delete_rows(row_index)),
        )

    return response


# Helper for append row raw.
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
    sheet = get_sheet(sheet_name)
    logical_id = str(row[0] if row else "").strip()
    reconcile = (lambda: _reconcile_single_append(sheet, logical_id)) if logical_id else None
    response = _execute_write(
        lambda: sheet.append_row(row, value_input_option="RAW"),
        operation="non_idempotent_write",
        reconcile=reconcile,
    )

    tx = _current_transaction.get()
    row_index = _extract_updated_row_index(response)
    if tx is not None and logical_id:
        tx.add_rollback(
            f"delete appended raw logical row {sheet_name}:{logical_id}",
            lambda sheet=sheet, logical_id=logical_id: _delete_rows_by_logical_ids(sheet, [logical_id]),
        )
    elif tx is not None and row_index:
        tx.add_rollback(
            f"delete appended raw row {sheet_name}!{row_index}",
            lambda sheet=sheet, row_index=row_index: _call_with_retry(lambda: sheet.delete_rows(row_index)),
        )

    return response


# Helper for append rows.
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
    # Validate missing rows before continuing.
    if not rows:
        return None

    sheet = get_sheet(sheet_name)
    logical_ids = [str(row[0] if row else "").strip() for row in rows]
    can_reconcile = all(logical_ids) and len(set(logical_ids)) == len(logical_ids)
    reconcile = (lambda: _reconcile_batch_append(sheet, logical_ids)) if can_reconcile else None
    response = _execute_write(
        lambda: sheet.append_rows(rows, value_input_option="RAW"),
        operation="non_idempotent_write",
        reconcile=reconcile,
    )

    tx = _current_transaction.get()
    row_range = _extract_updated_row_range(response)
    # Prefer immutable IDs because sorting can move the appended range before a
    # later account/debt write triggers rollback.
    if tx is not None and can_reconcile:
        tx.add_rollback(
            f"delete appended logical rows {sheet_name}:{','.join(logical_ids)}",
            lambda sheet=sheet, logical_ids=tuple(logical_ids): _delete_rows_by_logical_ids(sheet, list(logical_ids)),
        )
    elif tx is not None and row_range:
        start_row, end_row = row_range
        tx.add_rollback(
            f"delete appended rows {sheet_name}!{start_row}:{end_row}",
            lambda sheet=sheet, start_row=start_row, end_row=end_row: _call_with_retry(
                lambda: sheet.delete_rows(start_row, end_row)
            ),
        )

    return response


# Helper for get all records.
def get_all_records(sheet_name: str) -> list[dict]:
    """Read all records from a worksheet as dictionaries.

    Args:
        sheet_name: Source worksheet name.

    Returns:
        List of row dictionaries using the header row as keys.
    """
    snapshot = _request_snapshot.get()
    if snapshot is not None and sheet_name in snapshot.records:
        return copy.deepcopy(snapshot.records[sheet_name])
    sheet = get_sheet(sheet_name)
    records = _execute_read(lambda: sheet.get_all_records(value_render_option="UNFORMATTED_VALUE"))
    if snapshot is not None:
        snapshot.record_read(sheet_name, len(records))
        snapshot.records[sheet_name] = copy.deepcopy(records)
    return records


# Helper for get all values.
def get_all_values(sheet_name: str) -> list[list]:
    """Read all raw values from a worksheet.

    Args:
        sheet_name: Source worksheet name.

    Returns:
        Two-dimensional list of cell values.
    """
    snapshot = _request_snapshot.get()
    if snapshot is not None and sheet_name in snapshot.values:
        return copy.deepcopy(snapshot.values[sheet_name])
    sheet = get_sheet(sheet_name)
    values = _execute_read(lambda: sheet.get_all_values())
    if snapshot is not None:
        snapshot.record_read(sheet_name, max(0, len(values) - 1))
        snapshot.values[sheet_name] = copy.deepcopy(values)
    return values


def sort_range(sheet_name: str, sort_specs: tuple[tuple[int, str], ...], cell_range: str):
    """Sort a worksheet range server-side without downloading or rewriting rows."""

    sheet = get_sheet(sheet_name)
    return _execute_write(
        lambda: sheet.sort(*sort_specs, range=cell_range),
        operation="idempotent_write",
    )


# Helper for update cell.
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
    sheet = get_sheet(sheet_name)
    tx = _current_transaction.get()

    old_value = None
    if tx is not None:
        old_value = _execute_read(lambda: sheet.cell(row, col).value)

    cell_range = f"{_get_column_letter(col)}{row}"
    response = _execute_write(lambda: sheet.update(cell_range, [[value]], value_input_option="RAW"))

    if tx is not None:
        tx.add_rollback(
            f"restore cell {sheet_name}!{cell_range}",
            lambda sheet=sheet, cell_range=cell_range, old_value=old_value: _call_with_retry(
                lambda: sheet.update(cell_range, [[old_value]], value_input_option="RAW")
            ),
        )

    return response


# Helper for find row index.
def find_row_index(sheet_name: str, search_col: int, search_value: str) -> int | None:
    """Find the first row index whose column value matches text.

    Args:
        sheet_name: Worksheet name.
        search_col: One-based column number to scan.
        search_value: Case-insensitive value to match.

    Returns:
        One-based row index when found, otherwise `None`.
    """
    sheet = get_sheet(sheet_name)
    col_values = _execute_read(lambda: sheet.col_values(search_col))

    # Iterate through each i, val.
    for i, val in enumerate(col_values):
        if str(val).strip().lower() == str(search_value).strip().lower():
            return i + 1

    return None


# Helper for delete row.
def delete_row(sheet_name: str, row_index: int):
    """Delete one row through the rollback-aware bulk delete helper.

    Args:
        sheet_name: Target worksheet name.
        row_index: One-based row number to delete.

    Returns:
        Result from `delete_rows`.
    """
    delete_rows(sheet_name, [row_index])


# Helper for delete rows.
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
    # Validate missing row indices before continuing.
    if not row_indices:
        return None

    sheet = get_sheet(sheet_name)
    tx = _current_transaction.get()

    responses = []
    # Iterate through each row index.
    for row_index in sorted(set(int(i) for i in row_indices), reverse=True):
        old_row = None
        if tx is not None:
            old_row = _execute_read(lambda row_index=row_index: sheet.row_values(row_index))

        response = _execute_write(lambda row_index=row_index: sheet.delete_rows(row_index))
        # Append the current value to responses.
        responses.append(response)

        if tx is not None:
            tx.add_rollback(
                f"restore deleted row {sheet_name}!{row_index}",
                lambda sheet=sheet, row_index=row_index, old_row=old_row: _call_with_retry(
                    lambda: sheet.insert_row(old_row or [], index=row_index, value_input_option="RAW")
                ),
            )

    return responses


# Helper for update row.
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
    sheet = get_sheet(sheet_name)
    tx = _current_transaction.get()
    width = len(row_values)

    old_row = None
    if tx is not None:
        old_row = _pad_row(_execute_read(lambda: sheet.row_values(row_index)), width)

    end_col = _get_column_letter(width)
    cell_range = f"A{row_index}:{end_col}{row_index}"

    response = _execute_write(lambda: sheet.update(cell_range, [row_values], value_input_option="RAW"))

    if tx is not None:
        tx.add_rollback(
            f"restore row {sheet_name}!{row_index}",
            lambda sheet=sheet, cell_range=cell_range, old_row=old_row: _call_with_retry(
                lambda: sheet.update(cell_range, [old_row or []], value_input_option="RAW")
            ),
        )

    return response


# Helper for update range.
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
    sheet = get_sheet(sheet_name)
    tx = _current_transaction.get()

    old_values = None
    if tx is not None:
        old_values = _execute_read(lambda: sheet.get(cell_range))

    response = _execute_write(lambda: sheet.update(cell_range, values, value_input_option="RAW"))

    if tx is not None:
        tx.add_rollback(
            f"restore range {sheet_name}!{cell_range}",
            lambda sheet=sheet, cell_range=cell_range, old_values=old_values: _call_with_retry(
                lambda: sheet.update(cell_range, old_values or [], value_input_option="RAW")
            ),
        )

    return response
