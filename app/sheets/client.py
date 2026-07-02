"""Google Sheets client with worksheet access, schema bootstrap, retry handling, best-effort rollback, and read/write helpers."""


import contextvars
import os
import random
import re
import time
from contextlib import contextmanager

import gspread
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials
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


class SheetsAtomicWriteError(RuntimeError):
    """Error raised when a Google Sheets write fails after retries and rollback handling is attempted."""

    def __init__(self, original_error, rollback_ok: bool | None = None, rollback_errors: list[str] | None = None):
        """Helper for init in the Google Sheets data layer."""
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
        elif rollback_ok is False:
            rollback_detail = "; ".join(self.rollback_errors) if self.rollback_errors else "rollback gagal tanpa detail"
            message = (
                "Google Sheets write gagal setelah retry. "
                "Sebagian rollback juga gagal, kemungkinan karena quota masih habis. "
                f"Cek sheet manual. Detail: {base}. Rollback: {rollback_detail}"
            )
        else:
            message = base

        super().__init__(message)


# Schema compatibility note for Google Sheets headers and rows.
# Implementation section

class SheetsTransaction:
    """Best-effort transaction wrapper for Google Sheets writes. It records successful writes and tries to roll them back if a later write fails."""

    def __init__(self, label: str | None = None):
        """Helper for init in the Google Sheets data layer."""
        self.label = label or "sheets_operation"
        self.rollback_actions = []
        self.rollback_errors = []
        self.rolled_back = False
        self.failed = False

    def add_rollback(self, description: str, action):
        """Helper for add rollback in the Google Sheets data layer."""
        if self.rolled_back:
            return
        self.rollback_actions.append((description, action))

    def rollback(self) -> bool:
        """Helper for rollback in the Google Sheets data layer."""
        if self.rolled_back:
            return len(self.rollback_errors) == 0

        self.rolled_back = True

        for description, action in reversed(self.rollback_actions):
            try:
                action()
            except Exception as exc:
                self.rollback_errors.append(f"{description}: {exc}")

        self.rollback_actions.clear()
        return len(self.rollback_errors) == 0


@contextmanager
def sheets_transaction(label: str | None = None):
    """Helper for sheets transaction in the Google Sheets data layer."""
    parent = _current_transaction.get()
    if parent is not None:
        # Implementation section
        yield parent
        return

    tx = SheetsTransaction(label=label)
    token = _current_transaction.set(tx)

    try:
        yield tx
    except Exception:
        tx.failed = True
        tx.rollback()
        raise
    finally:
        _current_transaction.reset(token)


def rollback_current_sheets_transaction() -> bool:
    """Helper for rollback current sheets transaction in the Google Sheets data layer."""
    tx = _current_transaction.get()
    if tx is None:
        return False

    tx.failed = True
    return tx.rollback()


def get_current_sheets_transaction() -> SheetsTransaction | None:
    """Get data needed for current sheets transaction."""
    return _current_transaction.get()


def _is_quota_or_transient_error(exc: Exception) -> bool:
    """Check whether a condition is true for quota or transient error."""
    msg = str(exc).lower()
    return any(
        marker in msg
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


def _call_with_retry(fn, *, max_retries: int | None = None):
    """Helper for call with retry in the Google Sheets data layer."""
    retries = max_retries if max_retries is not None else int(os.getenv("SHEETS_MAX_RETRIES", "5"))
    base_delay = float(os.getenv("SHEETS_RETRY_BASE_DELAY", "1.0"))

    for attempt in range(max(1, retries)):
        try:
            return fn()
        except Exception as exc:
            is_last = attempt >= retries - 1
            if is_last or not _is_quota_or_transient_error(exc):
                raise

            sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
            time.sleep(sleep_time)


def _execute_write(fn):
    """Helper for execute write in the Google Sheets data layer."""
    tx = _current_transaction.get()

    if tx is not None and tx.failed:
        raise SheetsAtomicWriteError(
            "Operasi Google Sheets sebelumnya sudah gagal dan sudah di-rollback. "
            "Input ini harus dianggap gagal, bukan sukses sebagian.",
            rollback_ok=True,
        )

    try:
        return _call_with_retry(fn)
    except Exception as exc:
        if tx is not None:
            tx.failed = True
            rollback_ok = tx.rollback()
            raise SheetsAtomicWriteError(
                exc,
                rollback_ok=rollback_ok,
                rollback_errors=tx.rollback_errors,
            ) from exc
        raise


def _execute_read(fn):
    """Helper for execute read in the Google Sheets data layer."""
    return _call_with_retry(fn)


def _get_column_letter(col_number: int) -> str:
    """Get data needed for column letter."""
    result = ""
    number = int(col_number)
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result or "A"


def _extract_updated_row_index(response) -> int | None:
    """Extract the required part of input for updated row index."""
    text = str(response or "")
    match = re.search(r"![A-Z]+(\d+)(?::[A-Z]+(\d+))?", text)
    if match:
        return int(match.group(1))
    return None


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


def _pad_row(row: list, width: int) -> list:
    """Helper for pad row in the Google Sheets data layer."""
    values = list(row or [])
    if len(values) < width:
        values += [""] * (width - len(values))
    return values[:width]


def _clean_header(values: list) -> list[str]:
    """Clean input values for header."""
    return [str(value or "").strip() for value in values]


def _has_data_rows(values: list[list]) -> bool:
    """Check whether data has data rows."""
    return any(any(str(cell or "").strip() for cell in row) for row in values[1:])


def _is_blank_header(header: list[str]) -> bool:
    """Check whether a condition is true for blank header."""
    return not header or not any(str(cell or "").strip() for cell in header)


def _header_has_expected_prefix(header: list[str], expected_header: list[str]) -> bool:
    """Helper for header has expected prefix in the Google Sheets data layer."""
    return header[:len(expected_header)] == expected_header


def _header_is_safe_prefix(header: list[str], expected_header: list[str]) -> bool:
    # Safe for old headers whose column order is still a prefix of the new schema.
    # Asset flow section
    """Helper for header is safe prefix in the Google Sheets data layer."""
    if len(header) > len(expected_header):
        return False
    return header == expected_header[:len(header)]


def _resize_columns_if_needed(sheet, width: int):
    """Helper for resize columns if needed in the Google Sheets data layer."""
    current_cols = int(getattr(sheet, "col_count", 0) or 0)
    if current_cols < width:
        _call_with_retry(lambda: sheet.add_cols(width - current_cols))


def _write_header(sheet, header: list[str]):
    """Helper for write header in the Google Sheets data layer."""
    _resize_columns_if_needed(sheet, len(header))
    end_col = _get_column_letter(len(header))
    _call_with_retry(lambda: sheet.update(f"A1:{end_col}1", [header], value_input_option="RAW"))


def _default_rows_for_sheet(sheet_name: str) -> list[list]:
    """Helper for default rows for sheet in the Google Sheets data layer."""
    if sheet_name == SHEET_ACCOUNTS:
        return DEFAULT_ACCOUNT_ROWS
    if sheet_name == SHEET_CATEGORIES:
        return DEFAULT_CATEGORY_ROWS
    return []


def _seed_default_rows_if_empty(sheet_name: str, sheet, values: list[list]) -> list[str]:
    """Helper for seed default rows if empty in the Google Sheets data layer."""
    default_rows = _default_rows_for_sheet(sheet_name)
    if not default_rows or _has_data_rows(values):
        return []

    _call_with_retry(lambda: sheet.append_rows(default_rows, value_input_option="RAW"))
    return [f"seeded_default_rows:{sheet_name}:{len(default_rows)}"]


def _get_or_create_worksheet(spreadsheet, sheet_name: str):
    """Get data needed for or create worksheet."""
    try:
        return _call_with_retry(lambda: spreadsheet.worksheet(sheet_name))
    except WorksheetNotFound:
        expected_header = SHEET_SCHEMAS.get(sheet_name)
        if not expected_header:
            raise

        rows = max(100, len(_default_rows_for_sheet(sheet_name)) + 10)
        cols = max(10, len(expected_header))
        return _call_with_retry(
            lambda: spreadsheet.add_worksheet(title=sheet_name, rows=rows, cols=cols)
        )


def ensure_sheet_schema(sheet_name: str, sheet=None) -> dict:
    """Ensure that setup is ready for sheet schema."""
    global _worksheets, _schema_checked_sheets

    clean_name = str(sheet_name or "").strip()
    if not clean_name:
        raise ValueError("sheet_name kosong")

    expected_header = SHEET_SCHEMAS.get(clean_name)
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
    elif _header_has_expected_prefix(header, expected_header):
        # The header already matches. Extra columns after the main schema are left untouched.
        pass
    elif _header_is_safe_prefix(header_trimmed, expected_header):
        # Extend old-but-compatible headers, for example when a sheet is missing newly added optional columns.
        _write_header(sheet, expected_header)
        actions.append("header_extended")
    elif not has_data:
        _write_header(sheet, expected_header)
        actions.append("header_repaired_empty_sheet")
    else:
        existing_header = ", ".join([h for h in header if h]) or "-"
        raise ValueError(
            f"Format header sheet '{clean_name}' tidak cocok dan sheet sudah berisi data. "
            "Bot tidak mengubah urutan kolom otomatis agar data lama tidak rusak. "
            f"Header yang ada: {existing_header}. "
            f"Header yang dibutuhkan: {', '.join(expected_header)}"
        )

    # Re-read after header changes so default seeding uses the latest state.
    if actions:
        values = _call_with_retry(lambda: sheet.get_all_values())

    actions.extend(_seed_default_rows_if_empty(clean_name, sheet, values))

    _schema_checked_sheets.add(clean_name)
    return {
        "sheet": clean_name,
        "status": "ok",
        "actions": actions or ["no_change"],
    }


def ensure_spreadsheet_schema() -> list[dict]:
    """Ensure that setup is ready for spreadsheet schema."""
    spreadsheet = get_spreadsheet()
    results = []

    for sheet_name in SHEET_SCHEMAS:
        sheet = _get_or_create_worksheet(spreadsheet, sheet_name)
        _worksheets[sheet_name] = sheet
        results.append(ensure_sheet_schema(sheet_name, sheet=sheet))

    return results


def get_spreadsheet():
    """Get data needed for spreadsheet."""
    global _client, _spreadsheet

    if _spreadsheet is None:
        creds = Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_JSON,
            scopes=SCOPES,
        )
        _client = gspread.authorize(creds)
        _spreadsheet = _call_with_retry(lambda: _client.open_by_key(GOOGLE_SHEET_ID))

    return _spreadsheet


def get_sheet(sheet_name: str):
    """Get data needed for sheet."""
    global _worksheets

    clean_name = str(sheet_name or "").strip()
    if not clean_name:
        raise ValueError("sheet_name kosong")

    if clean_name not in _worksheets:
        spreadsheet = get_spreadsheet()
        _worksheets[clean_name] = _get_or_create_worksheet(spreadsheet, clean_name)

    if clean_name in SHEET_SCHEMAS and clean_name not in _schema_checked_sheets:
        ensure_sheet_schema(clean_name, sheet=_worksheets[clean_name])

    return _worksheets[clean_name]


def append_row(sheet_name: str, row: list):
    """Append data to row."""
    sheet = get_sheet(sheet_name)
    response = _execute_write(lambda: sheet.append_row(row, value_input_option="USER_ENTERED"))

    tx = _current_transaction.get()
    row_index = _extract_updated_row_index(response)
    if tx is not None and row_index:
        tx.add_rollback(
            f"delete appended row {sheet_name}!{row_index}",
            lambda sheet=sheet, row_index=row_index: _call_with_retry(lambda: sheet.delete_rows(row_index)),
        )

    return response


def append_row_raw(sheet_name: str, row: list):
    """Append data to row raw."""
    sheet = get_sheet(sheet_name)
    response = _execute_write(lambda: sheet.append_row(row, value_input_option="RAW"))

    tx = _current_transaction.get()
    row_index = _extract_updated_row_index(response)
    if tx is not None and row_index:
        tx.add_rollback(
            f"delete appended raw row {sheet_name}!{row_index}",
            lambda sheet=sheet, row_index=row_index: _call_with_retry(lambda: sheet.delete_rows(row_index)),
        )

    return response


def append_rows(sheet_name: str, rows: list[list]):
    """Append data to rows."""
    if not rows:
        return None

    sheet = get_sheet(sheet_name)
    response = _execute_write(lambda: sheet.append_rows(rows, value_input_option="USER_ENTERED"))

    tx = _current_transaction.get()
    row_range = _extract_updated_row_range(response)
    if tx is not None and row_range:
        start_row, end_row = row_range
        tx.add_rollback(
            f"delete appended rows {sheet_name}!{start_row}:{end_row}",
            lambda sheet=sheet, start_row=start_row, end_row=end_row: _call_with_retry(
                lambda: sheet.delete_rows(start_row, end_row)
            ),
        )

    return response


def get_all_records(sheet_name: str) -> list[dict]:
    """Get data needed for all records."""
    sheet = get_sheet(sheet_name)
    return _execute_read(lambda: sheet.get_all_records(value_render_option="UNFORMATTED_VALUE"))


def get_all_values(sheet_name: str) -> list[list]:
    """Get data needed for all values."""
    sheet = get_sheet(sheet_name)
    return _execute_read(lambda: sheet.get_all_values())


def update_cell(sheet_name: str, row: int, col: int, value):
    """Update existing data for cell."""
    sheet = get_sheet(sheet_name)
    tx = _current_transaction.get()

    old_value = None
    if tx is not None:
        old_value = _execute_read(lambda: sheet.cell(row, col).value)

    response = _execute_write(lambda: sheet.update_cell(row, col, value))

    if tx is not None:
        tx.add_rollback(
            f"restore cell {sheet_name}!{_get_column_letter(col)}{row}",
            lambda sheet=sheet, row=row, col=col, old_value=old_value: _call_with_retry(
                lambda: sheet.update_cell(row, col, old_value)
            ),
        )

    return response


def find_row_index(sheet_name: str, search_col: int, search_value: str) -> int | None:
    """Find a record for row index."""
    sheet = get_sheet(sheet_name)
    col_values = _execute_read(lambda: sheet.col_values(search_col))

    for i, val in enumerate(col_values):
        if str(val).strip().lower() == str(search_value).strip().lower():
            return i + 1

    return None


def delete_row(sheet_name: str, row_index: int):
    """Delete data safely for row."""
    delete_rows(sheet_name, [row_index])


def delete_rows(sheet_name: str, row_indices: list[int]):
    """Delete data safely for rows."""
    if not row_indices:
        return None

    sheet = get_sheet(sheet_name)
    tx = _current_transaction.get()

    responses = []
    for row_index in sorted(set(int(i) for i in row_indices), reverse=True):
        old_row = None
        if tx is not None:
            old_row = _execute_read(lambda row_index=row_index: sheet.row_values(row_index))

        response = _execute_write(lambda row_index=row_index: sheet.delete_rows(row_index))
        responses.append(response)

        if tx is not None:
            tx.add_rollback(
                f"restore deleted row {sheet_name}!{row_index}",
                lambda sheet=sheet, row_index=row_index, old_row=old_row: _call_with_retry(
                    lambda: sheet.insert_row(old_row or [], index=row_index, value_input_option="USER_ENTERED")
                ),
            )

    return responses


def update_row(sheet_name: str, row_index: int, row_values: list):
    """Update existing data for row."""
    sheet = get_sheet(sheet_name)
    tx = _current_transaction.get()
    width = len(row_values)

    old_row = None
    if tx is not None:
        old_row = _pad_row(_execute_read(lambda: sheet.row_values(row_index)), width)

    end_col = _get_column_letter(width)
    cell_range = f"A{row_index}:{end_col}{row_index}"

    response = _execute_write(lambda: sheet.update(cell_range, [row_values]))

    if tx is not None:
        tx.add_rollback(
            f"restore row {sheet_name}!{row_index}",
            lambda sheet=sheet, cell_range=cell_range, old_row=old_row: _call_with_retry(
                lambda: sheet.update(cell_range, [old_row or []])
            ),
        )

    return response


def update_range(sheet_name: str, cell_range: str, values: list[list]):
    """Update existing data for range."""
    sheet = get_sheet(sheet_name)
    tx = _current_transaction.get()

    old_values = None
    if tx is not None:
        old_values = _execute_read(lambda: sheet.get(cell_range))

    response = _execute_write(lambda: sheet.update(cell_range, values))

    if tx is not None:
        tx.add_rollback(
            f"restore range {sheet_name}!{cell_range}",
            lambda sheet=sheet, cell_range=cell_range, old_values=old_values: _call_with_retry(
                lambda: sheet.update(cell_range, old_values or [])
            ),
        )

    return response
