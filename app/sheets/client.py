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
        _spreadsheet = _client.open_by_key(GOOGLE_SHEET_ID)

    return _spreadsheet


def get_sheet(sheet_name: str):
    """Ambil worksheet berdasarkan nama tab."""
    spreadsheet = get_spreadsheet()
    return spreadsheet.worksheet(sheet_name)


def append_row(sheet_name: str, row: list):
    """Tambah satu baris baru di akhir sheet."""
    sheet = get_sheet(sheet_name)
    sheet.append_row(row, value_input_option="USER_ENTERED")


def append_rows(sheet_name: str, rows: list[list]):
    """
    Tambah banyak baris sekaligus.
    Ini lebih cepat daripada append_row berkali-kali.
    """
    if not rows:
        return

    sheet = get_sheet(sheet_name)
    sheet.append_rows(rows, value_input_option="USER_ENTERED")


def get_all_records(sheet_name: str) -> list[dict]:
    """Ambil semua data sebagai list of dict (header = key).

    Gunakan UNFORMATTED_VALUE supaya angka decimal dari locale Indonesia
    tidak salah dibaca oleh gspread. Contoh nilai sheet 71387,5
    harus terbaca 71387.5, bukan 713875.
    """
    sheet = get_sheet(sheet_name)
    return sheet.get_all_records(value_render_option="UNFORMATTED_VALUE")


def update_cell(sheet_name: str, row: int, col: int, value):
    """Update satu cell berdasarkan posisi row & col (1-indexed)."""
    sheet = get_sheet(sheet_name)
    sheet.update_cell(row, col, value)


def find_row_index(sheet_name: str, search_col: int, search_value: str) -> int | None:
    """
    Cari index baris berdasarkan nilai di kolom tertentu.
    Return None jika tidak ditemukan.
    Row index 1-indexed (baris 1 = header).
    """
    sheet = get_sheet(sheet_name)
    col_values = sheet.col_values(search_col)

    for i, val in enumerate(col_values):
        if str(val).strip().lower() == str(search_value).strip().lower():
            return i + 1

    return None

def delete_row(sheet_name: str, row_index: int):
    """
    Hapus satu baris dari worksheet.
    row_index 1-indexed.
    """
    sheet = get_sheet(sheet_name)
    sheet.delete_rows(row_index)


def delete_rows(sheet_name: str, row_indices: list[int]):
    """
    Hapus banyak baris dari worksheet.
    Hapus dari bawah ke atas supaya index row tidak bergeser.
    """
    if not row_indices:
        return

    sheet = get_sheet(sheet_name)

    for row_index in sorted(row_indices, reverse=True):
        sheet.delete_rows(row_index)

def update_row(sheet_name: str, row_index: int, row_values: list):
    """
    Update satu baris penuh di worksheet.
    row_index 1-indexed.
    """
    sheet = get_sheet(sheet_name)

    end_col = chr(ord("A") + len(row_values) - 1)
    cell_range = f"A{row_index}:{end_col}{row_index}"

    sheet.update(cell_range, [row_values])