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
            scopes=SCOPES
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


def get_all_records(sheet_name: str) -> list[dict]:
    """Ambil semua data sebagai list of dict (header = key)."""
    sheet = get_sheet(sheet_name)
    return sheet.get_all_records()


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
        if val == search_value:
            return i + 1  # gspread pakai 1-indexed

    return None