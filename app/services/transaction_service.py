from datetime import datetime
from app.sheets.client import (
    append_row,
    get_all_records,
    get_sheet,
    find_row_index,
    update_cell,
)
from app.config import (
    SHEET_TRANSACTIONS,
    SHEET_ACCOUNTS,
)


# ── ID Generator ──────────────────────────────────────────────────────────────

def generate_transaction_id() -> str:
    """
    Generate unique transaction ID berdasarkan timestamp.
    Format: txn_YYYYMMDD_HHMMSS
    Contoh: txn_20260608_143022
    """
    return datetime.now().strftime("txn_%Y%m%d_%H%M%S")


# ── Account helpers ───────────────────────────────────────────────────────────

def get_account_balance(account_name: str) -> float | None:
    """Ambil saldo rekening berdasarkan nama."""
    records = get_all_records(SHEET_ACCOUNTS)
    for record in records:
        if record["account_name"].lower() == account_name.lower():
            return float(record["balance"])
    return None


def update_account_balance(account_name: str, new_balance: float) -> bool:
    """
    Update saldo rekening di sheet accounts.
    Return True jika berhasil, False jika rekening tidak ditemukan.
    """
    # Kolom di sheet accounts:
    # 1=account_name, 2=type, 3=balance, 4=currency, 5=last_updated
    ACCOUNT_NAME_COL = 1
    BALANCE_COL = 3
    LAST_UPDATED_COL = 5

    row_index = find_row_index(SHEET_ACCOUNTS, ACCOUNT_NAME_COL, account_name)
    if not row_index:
        return False

    update_cell(SHEET_ACCOUNTS, row_index, BALANCE_COL, new_balance)
    update_cell(
        SHEET_ACCOUNTS,
        row_index,
        LAST_UPDATED_COL,
        datetime.now().strftime("%Y-%m-%d")
    )
    return True


def get_all_accounts() -> list[dict]:
    """Ambil semua rekening beserta saldonya."""
    return get_all_records(SHEET_ACCOUNTS)


# ── Core transaction function ─────────────────────────────────────────────────

def save_transaction(parsed: dict, raw_input: str) -> dict:
    """
    Simpan transaksi ke Google Sheets dan update saldo rekening.

    Args:
        parsed: hasil dari regex_parser atau gemini_parser
        raw_input: pesan asli dari user

    Return:
        {
            "success": bool,
            "transaction_id": str,
            "message": str,
            "new_balance": float | None
        }
    """
    txn_id = generate_transaction_id()
    txn_type = parsed.get("type")
    amount = parsed.get("amount", 0)
    category = parsed.get("category") or ""
    account = parsed.get("account") or ""
    to_account = parsed.get("to_account") or ""
    description = parsed.get("description") or ""
    date = parsed.get("date", datetime.now().strftime("%Y-%m-%d"))
    parsed_by = parsed.get("parsed_by", "regex")

    # ── 1. Tulis ke sheet transactions ───────────────────────────────────────
    row = [
        txn_id,
        date,
        txn_type,
        amount,
        category,
        account,
        to_account,
        description,
        raw_input,
        parsed_by,
    ]

    try:
        append_row(SHEET_TRANSACTIONS, row)
    except Exception as e:
        return {
            "success": False,
            "transaction_id": None,
            "message": f"Gagal menyimpan transaksi: {str(e)}",
            "new_balance": None,
        }

    # ── 2. Update saldo rekening ──────────────────────────────────────────────
    new_balance = None

    try:
        if txn_type == "expense" and account:
            current = get_account_balance(account)
            if current is not None:
                new_balance = current - amount
                update_account_balance(account, new_balance)

        elif txn_type == "income" and account:
            current = get_account_balance(account)
            if current is not None:
                new_balance = current + amount
                update_account_balance(account, new_balance)

        elif txn_type == "transfer":
            # Kurangi dari rekening asal
            if account:
                current_from = get_account_balance(account)
                if current_from is not None:
                    update_account_balance(account, current_from - amount)

            # Tambah ke rekening tujuan
            if to_account:
                current_to = get_account_balance(to_account)
                if current_to is not None:
                    new_balance = current_to + amount
                    update_account_balance(to_account, new_balance)

    except Exception as e:
        # Transaksi sudah tersimpan, tapi saldo gagal update
        # Tetap return success tapi kasih warning
        return {
            "success": True,
            "transaction_id": txn_id,
            "message": f"⚠️ Transaksi tersimpan, tapi saldo gagal diupdate: {str(e)}",
            "new_balance": None,
        }

    return {
        "success": True,
        "transaction_id": txn_id,
        "message": "ok",
        "new_balance": new_balance,
    }


# ── Query functions ───────────────────────────────────────────────────────────

def get_transactions_by_month(year: int, month: int) -> list[dict]:
    """Ambil semua transaksi dalam satu bulan."""
    records = get_all_records(SHEET_TRANSACTIONS)
    prefix = f"{year}-{month:02d}"
    return [r for r in records if str(r.get("date", "")).startswith(prefix)]


def get_transactions_by_date(date_str: str) -> list[dict]:
    """Ambil semua transaksi di tanggal tertentu. Format: YYYY-MM-DD"""
    records = get_all_records(SHEET_TRANSACTIONS)
    return [r for r in records if r.get("date") == date_str]


def get_expense_by_category(year: int, month: int) -> dict:
    """
    Hitung total pengeluaran per kategori dalam satu bulan.
    Return: {"Food & Beverage": 250000, "Transport": 150000, ...}
    """
    transactions = get_transactions_by_month(year, month)
    result = {}

    for txn in transactions:
        if txn.get("type") != "expense":
            continue
        cat = txn.get("category", "Other Expense")
        amount = float(txn.get("amount", 0))
        result[cat] = result.get(cat, 0) + amount

    return result