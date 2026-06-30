import contextvars
import os
import random
import re
import time
from contextlib import contextmanager

import gspread
from google.oauth2.service_account import Credentials
from app.config import GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEET_ID

# Scope yang dibutuhkan untuk baca + tulis Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

_client = None
_spreadsheet = None
_worksheets = {}
_current_transaction = contextvars.ContextVar("sheets_current_transaction", default=None)


class SheetsAtomicWriteError(RuntimeError):
    """Error write Sheets yang sudah melewati retry dan memicu rollback."""

    def __init__(self, original_error, rollback_ok: bool | None = None, rollback_errors: list[str] | None = None):
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


class SheetsTransaction:
    """Best-effort transaction wrapper untuk operasi Google Sheets.

    Google Sheets bukan database transactional. Karena itu atomicity dibuat
    dengan strategi kompensasi:
    - setiap write sukses mendaftarkan aksi rollback;
    - kalau write berikutnya gagal setelah retry, rollback dijalankan dari aksi
      terakhir ke aksi pertama;
    - kalau rollback juga gagal karena quota, error tetap dinaikkan agar user
      tidak mengira operasi sukses.
    """

    def __init__(self, label: str | None = None):
        self.label = label or "sheets_operation"
        self.rollback_actions = []
        self.rollback_errors = []
        self.rolled_back = False
        self.failed = False

    def add_rollback(self, description: str, action):
        if self.rolled_back:
            return
        self.rollback_actions.append((description, action))

    def rollback(self) -> bool:
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
    """Aktifkan rollback otomatis untuk semua write Sheets di dalam blok ini."""
    parent = _current_transaction.get()
    if parent is not None:
        # Nested operation tetap ikut transaksi paling luar.
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
    """Rollback transaksi Sheets aktif, dipakai untuk logical failure non-exception."""
    tx = _current_transaction.get()
    if tx is None:
        return False

    tx.failed = True
    return tx.rollback()


def get_current_sheets_transaction() -> SheetsTransaction | None:
    return _current_transaction.get()


def _is_quota_or_transient_error(exc: Exception) -> bool:
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
    return _call_with_retry(fn)


def _get_column_letter(col_number: int) -> str:
    result = ""
    number = int(col_number)
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result or "A"


def _extract_updated_row_index(response) -> int | None:
    text = str(response or "")
    match = re.search(r"![A-Z]+(\d+)(?::[A-Z]+(\d+))?", text)
    if match:
        return int(match.group(1))
    return None


def _extract_updated_row_range(response) -> tuple[int, int] | None:
    text = str(response or "")
    match = re.search(r"![A-Z]+(\d+):[A-Z]+(\d+)", text)
    if match:
        return int(match.group(1)), int(match.group(2))

    row = _extract_updated_row_index(response)
    if row:
        return row, row
    return None


def _pad_row(row: list, width: int) -> list:
    values = list(row or [])
    if len(values) < width:
        values += [""] * (width - len(values))
    return values[:width]


def get_spreadsheet():
    """
    Singleton pattern — koneksi dibuat sekali, dipakai ulang.
    Mencegah autentikasi berulang setiap request.
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


def get_sheet(sheet_name: str):
    """Ambil worksheet berdasarkan nama tab.

    Worksheet object di-cache supaya setiap append/update tidak memanggil
    lookup worksheet berulang. Ini penting untuk mengurangi read request
    Google Sheets, terutama pada flow debt/split bill yang menulis beberapa
    sheet sekaligus.
    """
    global _worksheets

    clean_name = str(sheet_name or "").strip()
    if not clean_name:
        raise ValueError("sheet_name kosong")

    if clean_name not in _worksheets:
        spreadsheet = get_spreadsheet()
        _worksheets[clean_name] = _call_with_retry(lambda: spreadsheet.worksheet(clean_name))

    return _worksheets[clean_name]


def append_row(sheet_name: str, row: list):
    """Tambah satu baris baru di akhir sheet dengan retry + rollback."""
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
    """Tambah satu baris baru tanpa auto-format Google Sheets.

    Dipakai untuk field yang harus tetap persis sebagai text, misalnya
    budgets.month = `YYYY-MM`. Kalau pakai USER_ENTERED, Sheets bisa
    mengubah `2026-06` menjadi date/serial number.
    """
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
    """
    Tambah banyak baris sekaligus.
    Ini lebih cepat daripada append_row berkali-kali.
    """
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
    """Ambil semua data sebagai list of dict (header = key).

    Gunakan UNFORMATTED_VALUE supaya angka decimal dari locale Indonesia
    tidak salah dibaca oleh gspread. Contoh nilai sheet 71387,5
    harus terbaca 71387.5, bukan 713875.
    """
    sheet = get_sheet(sheet_name)
    return _execute_read(lambda: sheet.get_all_records(value_render_option="UNFORMATTED_VALUE"))


def get_all_values(sheet_name: str) -> list[list]:
    sheet = get_sheet(sheet_name)
    return _execute_read(lambda: sheet.get_all_values())


def update_cell(sheet_name: str, row: int, col: int, value):
    """Update satu cell berdasarkan posisi row & col (1-indexed)."""
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
    """
    Cari index baris berdasarkan nilai di kolom tertentu.
    Return None jika tidak ditemukan.
    Row index 1-indexed (baris 1 = header).
    """
    sheet = get_sheet(sheet_name)
    col_values = _execute_read(lambda: sheet.col_values(search_col))

    for i, val in enumerate(col_values):
        if str(val).strip().lower() == str(search_value).strip().lower():
            return i + 1

    return None


def delete_row(sheet_name: str, row_index: int):
    """
    Hapus satu baris dari worksheet.
    row_index 1-indexed.
    """
    delete_rows(sheet_name, [row_index])


def delete_rows(sheet_name: str, row_indices: list[int]):
    """
    Hapus banyak baris dari worksheet.
    Hapus dari bawah ke atas supaya index row tidak bergeser.
    """
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
    """
    Update satu baris penuh di worksheet.
    row_index 1-indexed.
    """
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
    """Update range worksheet dengan snapshot rollback."""
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
