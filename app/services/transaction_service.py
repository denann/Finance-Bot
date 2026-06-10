from datetime import datetime, timedelta
from app.sheets.client import (
    append_row,
    append_rows,
    get_all_records,
    find_row_index,
    update_cell,
    delete_rows,
)
from app.config import (
    SHEET_TRANSACTIONS,
    SHEET_ACCOUNTS,
)
from app.sheets.client import (
    append_row,
    append_rows,
    get_all_records,
    find_row_index,
    update_cell,
    delete_rows,
    update_row,
)
import uuid
from datetime import datetime
import re

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
]


def get_current_month_str() -> str:
    return datetime.now().strftime("%Y-%m")


def normalize_export_period(period: str | None = None) -> dict:
    """
    Normalize argumen /export.

    Support:
    - None      -> bulan ini
    - today     -> hari ini
    - week      -> minggu ini
    - month     -> bulan ini
    - YYYY-MM   -> bulan tertentu
    """
    today = datetime.now().date()

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

    raise ValueError(
        "Format export tidak dikenali. Gunakan: /export, /export today, /export week, /export month, atau /export 2026-06."
    )


def parse_date_safe(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def get_transactions_for_export(period: str | None = None) -> dict:
    """
    Ambil transaksi untuk export CSV.

    Return:
    {
        "success": bool,
        "records": list[dict],
        "filter": dict,
        "summary": dict,
        "message": str
    }
    """
    try:
        filter_info = normalize_export_period(period)
    except Exception as e:
        return {
            "success": False,
            "records": [],
            "filter": {},
            "summary": {},
            "message": str(e),
        }

    records = get_all_records(SHEET_TRANSACTIONS)
    filtered = []

    for record in records:
        txn_date_raw = str(record.get("date", "")).strip()

        if filter_info["type"] == "month":
            if txn_date_raw.startswith(filter_info["month"]):
                filtered.append(record)

        elif filter_info["type"] == "date_range":
            txn_date = parse_date_safe(txn_date_raw)

            if not txn_date:
                continue

            if filter_info["date_from"] <= txn_date <= filter_info["date_to"]:
                filtered.append(record)

    total_income = 0.0
    total_expense = 0.0
    total_transfer = 0.0

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

# ── ID Generator ──────────────────────────────────────────────────────────────

def generate_transaction_id() -> str:
    """
    Generate transaction ID yang unik.

    Format:
    txn_YYYYMMDD_HHMMSS_microsecond_uuid8
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    unique_suffix = uuid.uuid4().hex[:8]
    return f"txn_{timestamp}_{unique_suffix}"


# ── Row Builder ───────────────────────────────────────────────────────────────

def build_transaction_row(parsed: dict, raw_input: str) -> tuple[str, list]:
    """
    Build row transaksi sesuai header Google Sheets:

    id, date, type, amount, category, account, to_account,
    subject, description, catatan, tipe_pengeluaran, raw_input, parsed_by
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
    date = parsed.get("date") or datetime.now().strftime("%Y-%m-%d")
    parsed_by = parsed.get("parsed_by") or "regex"

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
    ]

    return txn_id, row


def validate_transaction(parsed: dict) -> tuple[bool, str]:
    txn_type = parsed.get("type")
    amount = float(parsed.get("amount", 0) or 0)

    if txn_type not in ["expense", "income", "transfer"]:
        return False, "Tipe transaksi tidak valid."

    if amount <= 0:
        return False, "Nominal transaksi tidak valid."

    return True, "ok"


# ── Account helpers ───────────────────────────────────────────────────────────

def get_account_balance(account_name: str) -> float | None:
    """Ambil saldo rekening berdasarkan nama."""
    records = get_all_records(SHEET_ACCOUNTS)

    for record in records:
        if str(record.get("account_name", "")).strip().lower() == str(account_name).strip().lower():
            return float(record.get("balance", 0) or 0)

    return None


def update_account_balance(account_name: str, new_balance: float) -> bool:
    """
    Update saldo rekening di sheet accounts.
    Return True jika berhasil, False jika rekening tidak ditemukan.
    """
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
        datetime.now().strftime("%Y-%m-%d"),
    )
    return True


def get_all_accounts() -> list[dict]:
    """Ambil semua rekening beserta saldonya."""
    return get_all_records(SHEET_ACCOUNTS)


def get_account_index_map() -> dict:
    """
    Ambil semua account sekali saja.
    Return:
    {
        "cash": {"row": 2, "name": "Cash", "balance": 100000},
        "bri": {"row": 3, "name": "BRI", "balance": 500000},
    }
    """
    records = get_all_records(SHEET_ACCOUNTS)
    result = {}

    for i, record in enumerate(records):
        name = str(record.get("account_name", "")).strip()
        if not name:
            continue

        result[name.lower()] = {
            "row": i + 2,  # +2 karena row 1 adalah header
            "name": name,
            "balance": float(record.get("balance", 0) or 0),
        }

    return result


def calculate_account_deltas(parsed_items: list[dict]) -> dict:
    """
    Hitung perubahan saldo per rekening dari banyak transaksi.

    Return:
    {
        "Cash": -50000,
        "BRI": 100000,
    }
    """
    deltas = {}

    def add_delta(account_name: str, value: float):
        if not account_name:
            return

        key = str(account_name).strip()
        if not key:
            return

        deltas[key] = deltas.get(key, 0) + float(value)

    for item in parsed_items:
        parsed = item["parsed"]
        txn_type = parsed.get("type")
        amount = float(parsed.get("amount", 0) or 0)
        account = parsed.get("account") or ""
        to_account = parsed.get("to_account") or ""

        if txn_type == "expense":
            add_delta(account, -amount)

        elif txn_type == "income":
            add_delta(account, amount)

        elif txn_type == "transfer":
            add_delta(account, -amount)
            add_delta(to_account, amount)

    return deltas


def apply_account_deltas(account_deltas: dict) -> dict:
    """
    Update saldo rekening berdasarkan total delta per account.
    Ini lebih cepat daripada update saldo tiap transaksi.

    Return:
    {
        "success": True,
        "new_balances": {"Cash": 50000, "BRI": 1000000},
        "failed_accounts": []
    }
    """
    if not account_deltas:
        return {
            "success": True,
            "new_balances": {},
            "failed_accounts": [],
        }

    BALANCE_COL = 3
    LAST_UPDATED_COL = 5

    accounts_map = get_account_index_map()
    today = datetime.now().strftime("%Y-%m-%d")

    new_balances = {}
    failed_accounts = []

    for account_name, delta in account_deltas.items():
        account_key = str(account_name).strip().lower()
        account_info = accounts_map.get(account_key)

        if not account_info:
            failed_accounts.append(account_name)
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

def save_transaction(parsed: dict, raw_input: str) -> dict:
    """
    Simpan satu transaksi ke Google Sheets dan update saldo rekening.
    Tetap dipakai untuk transaksi single.
    """
    is_valid, validation_message = validate_transaction(parsed)
    if not is_valid:
        return {
            "success": False,
            "transaction_id": None,
            "message": validation_message,
            "new_balance": None,
        }

    txn_id, row = build_transaction_row(parsed, raw_input)

    try:
        append_row(SHEET_TRANSACTIONS, row)
    except Exception as e:
        return {
            "success": False,
            "transaction_id": None,
            "message": f"Gagal menyimpan transaksi: {str(e)}",
            "new_balance": None,
        }

    new_balance = None

    try:
        deltas = calculate_account_deltas([
            {
                "parsed": parsed,
                "raw": raw_input,
            }
        ])

        balance_result = apply_account_deltas(deltas)

        account = parsed.get("to_account") or parsed.get("account")
        if account:
            for name, balance in balance_result.get("new_balances", {}).items():
                if str(name).lower() == str(account).lower():
                    new_balance = balance
                    break

        if balance_result.get("failed_accounts"):
            return {
                "success": True,
                "transaction_id": txn_id,
                "message": (
                    "⚠️ Transaksi tersimpan, tapi saldo rekening berikut gagal diupdate: "
                    + ", ".join(balance_result["failed_accounts"])
                ),
                "new_balance": new_balance,
            }

    except Exception as e:
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


def save_transactions_batch(parsed_items: list[dict]) -> dict:
    """
    Simpan banyak transaksi sekaligus.

    Input:
    [
        {"parsed": parsed_dict, "raw": "beli nasi 30k"},
        {"parsed": parsed_dict, "raw": "beli ayam 20k"},
    ]

    Optimisasi:
    1. append_rows sekali untuk semua transaksi
    2. hitung total delta saldo per rekening
    3. update saldo per rekening sekali
    """
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
    rows = []
    saved_ids = []

    for item in parsed_items:
        parsed = item["parsed"]
        raw = item["raw"]

        is_valid, validation_message = validate_transaction(parsed)
        if not is_valid:
            failed_items.append({
                "raw": raw,
                "message": validation_message,
            })
            continue

        txn_id, row = build_transaction_row(parsed, raw)
        saved_ids.append(txn_id)
        rows.append(row)
        valid_items.append(item)

    if not rows:
        return {
            "success": False,
            "message": "Semua transaksi gagal divalidasi.",
            "success_count": 0,
            "failed_items": failed_items,
            "saved_ids": [],
            "new_balances": {},
        }

    try:
        append_rows(SHEET_TRANSACTIONS, rows)
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
                for item in valid_items
            ] + failed_items,
            "saved_ids": [],
            "new_balances": {},
        }

    try:
        deltas = calculate_account_deltas(valid_items)
        balance_result = apply_account_deltas(deltas)

        if balance_result.get("failed_accounts"):
            failed_items.append({
                "raw": "update saldo",
                "message": (
                    "Saldo gagal diupdate untuk rekening: "
                    + ", ".join(balance_result["failed_accounts"])
                ),
            })

        return {
            "success": True,
            "message": "ok",
            "success_count": len(valid_items),
            "failed_items": failed_items,
            "saved_ids": saved_ids,
            "new_balances": balance_result.get("new_balances", {}),
        }

    except Exception as e:
        return {
            "success": True,
            "message": f"⚠️ Transaksi tersimpan, tapi saldo gagal diupdate: {str(e)}",
            "success_count": len(valid_items),
            "failed_items": failed_items + [
                {
                    "raw": "update saldo",
                    "message": str(e),
                }
            ],
            "saved_ids": saved_ids,
            "new_balances": {},
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

        cat = txn.get("category") or "Other Expense"
        amount = float(txn.get("amount", 0) or 0)
        result[cat] = result.get(cat, 0) + amount

    return result

def is_debt_cashflow_transaction(txn: dict) -> bool:
    category = str(txn.get("category", "")).strip()
    parsed_by = str(txn.get("parsed_by", "")).strip().lower()

    return category in DEBT_CASHFLOW_CATEGORIES or parsed_by == "debt"


def parse_transaction_date(date_value: str):
    try:
        return datetime.strptime(str(date_value), "%Y-%m-%d").date()
    except Exception:
        return None


def get_transactions_with_row_index() -> list[dict]:
    """
    Ambil semua transaksi + _row_index Google Sheets.
    Data mulai row 2 karena row 1 adalah header.
    """
    records = get_all_records(SHEET_TRANSACTIONS)
    result = []

    for i, record in enumerate(records):
        item = dict(record)
        item["_row_index"] = i + 2
        result.append(item)

    return result

def get_recent_transactions(
    limit: int = 10,
    period: str | None = None,
    month: str | None = None,
) -> list[dict]:
    """
    Ambil transaksi terbaru.

    period:
    - today
    - week
    - month

    month:
    - YYYY-MM
    """
    records = get_transactions_with_row_index()
    today = datetime.now().date()

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
        for r in records:
            txn_date = parse_transaction_date(r.get("date", ""))
            if txn_date and start_week <= txn_date <= end_week:
                filtered.append(r)

        records = filtered

    elif period == "month":
        month_now = today.strftime("%Y-%m")
        records = [
            r for r in records
            if str(r.get("date", "")).startswith(month_now)
        ]

    records = sorted(
        records,
        key=lambda x: int(x.get("_row_index", 0)),
        reverse=True,
    )

    return records[:limit]

def get_transaction_by_id(txn_id: str) -> dict | None:
    records = get_transactions_with_row_index()

    for record in records:
        if str(record.get("id", "")).strip() == str(txn_id).strip():
            return record

    return None


def get_transactions_by_ids(txn_ids: list[str]) -> list[dict]:
    target_ids = {str(x).strip() for x in txn_ids if str(x).strip()}
    records = get_transactions_with_row_index()

    return [
        r for r in records
        if str(r.get("id", "")).strip() in target_ids
    ]

def get_transactions_by_row_indices(row_indices: list[int]) -> list[dict]:
    target_rows = {int(x) for x in row_indices}
    records = get_transactions_with_row_index()

    return [
        r for r in records
        if int(r.get("_row_index", 0)) in target_rows
    ]


def calculate_reverse_deltas_for_delete(transactions: list[dict]) -> dict:
    """
    Balik efek saldo dari transaksi yang akan dihapus.

    expense Cash 10k:
    - saat input: Cash -10k
    - saat delete: Cash +10k

    income Cash 10k:
    - saat input: Cash +10k
    - saat delete: Cash -10k

    transfer Cash -> BRI 10k:
    - saat input: Cash -10k, BRI +10k
    - saat delete: Cash +10k, BRI -10k
    """
    deltas = {}

    def add_delta(account_name: str, value: float):
        if not account_name:
            return

        key = str(account_name).strip()
        if not key:
            return

        deltas[key] = deltas.get(key, 0) + float(value)

    for txn in transactions:
        txn_type = str(txn.get("type", "")).strip()
        amount = float(txn.get("amount", 0) or 0)
        account = str(txn.get("account", "")).strip()
        to_account = str(txn.get("to_account", "")).strip()

        if txn_type == "expense":
            add_delta(account, amount)

        elif txn_type == "income":
            add_delta(account, -amount)

        elif txn_type == "transfer":
            add_delta(account, amount)
            add_delta(to_account, -amount)

    return deltas

def preview_delete_transactions_by_refs(
    row_indices: list[int] | None = None,
    txn_ids: list[str] | None = None,
) -> dict:
    """
    Preview delete berdasarkan:
    - row_indices: dari nomor /last
    - txn_ids: kalau user input ID langsung

    Untuk /delete_txn 1 2 3, row_index lebih aman daripada transaction_id.
    """
    row_indices = row_indices or []
    txn_ids = txn_ids or []

    by_rows = get_transactions_by_row_indices(row_indices) if row_indices else []
    by_ids = get_transactions_by_ids(txn_ids) if txn_ids else []

    transactions = []
    seen_rows = set()

    for txn in by_rows + by_ids:
        row_index = int(txn.get("_row_index", 0))
        if row_index and row_index not in seen_rows:
            transactions.append(txn)
            seen_rows.add(row_index)

    found_rows = {int(t.get("_row_index", 0)) for t in by_rows}
    requested_rows = {int(x) for x in row_indices}
    missing_rows = sorted(requested_rows - found_rows)

    found_ids = {str(t.get("id", "")).strip() for t in by_ids}
    requested_ids = {str(x).strip() for x in txn_ids if str(x).strip()}
    missing_ids = sorted(requested_ids - found_ids)

    blocked = []
    deletable = []

    for txn in transactions:
        if is_debt_cashflow_transaction(txn):
            blocked.append(txn)
        else:
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

def preview_delete_transactions(txn_ids: list[str]) -> dict:
    """
    Validasi dan preview transaksi yang akan dihapus.
    Tidak mengubah sheet.
    """
    transactions = get_transactions_by_ids(txn_ids)
    found_ids = {str(t.get("id", "")).strip() for t in transactions}
    requested_ids = {str(x).strip() for x in txn_ids}

    missing_ids = sorted(requested_ids - found_ids)

    blocked = []
    deletable = []

    for txn in transactions:
        if is_debt_cashflow_transaction(txn):
            blocked.append(txn)
        else:
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


def delete_transactions_by_ids(txn_ids: list[str]) -> dict:
    """
    Hapus banyak transaksi sekaligus dan reverse saldo rekening.

    Safety:
    - debt cashflow transaction diblok dulu supaya debts sheet tidak inkonsisten.
    """
    preview = preview_delete_transactions(txn_ids)

    deletable = preview["deletable"]
    blocked = preview["blocked"]
    missing_ids = preview["missing_ids"]

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

    try:
        balance_result = apply_account_deltas(reverse_deltas)
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

    try:
        row_indices = [
            int(txn["_row_index"])
            for txn in deletable
            if txn.get("_row_index")
        ]

        delete_rows(SHEET_TRANSACTIONS, row_indices)

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
    }

def delete_transactions_by_refs(
    row_indices: list[int] | None = None,
    txn_ids: list[str] | None = None,
) -> dict:
    """
    Delete transaksi berdasarkan row_index dan/atau transaction_id.
    """
    preview = preview_delete_transactions_by_refs(row_indices, txn_ids)

    deletable = preview["deletable"]
    blocked = preview["blocked"]
    missing_ids = preview.get("missing_ids", [])
    missing_rows = preview.get("missing_rows", [])

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

    try:
        balance_result = apply_account_deltas(reverse_deltas)
    except Exception as e:
        return {
            "success": False,
            "message": f"Gagal reverse saldo: {str(e)}",
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "missing_rows": missing_rows,
            "new_balances": {},
        }

    try:
        delete_row_indices = [
            int(txn["_row_index"])
            for txn in deletable
            if txn.get("_row_index")
        ]

        delete_rows(SHEET_TRANSACTIONS, delete_row_indices)

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
            "missing_rows": missing_rows,
            "new_balances": balance_result.get("new_balances", {}),
        }

    deleted_ids = [
        str(txn.get("id", ""))
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


def normalize_edit_field(field: str) -> str | None:
    key = str(field or "").strip().lower()

    # Kalau input/Gemini langsung kasih nama field resmi seperti "description",
    # tetap diterima.
    if key in EDITABLE_TRANSACTION_FIELDS:
        return key

    return FIELD_ALIASES.get(key)


def normalize_edit_updates(updates: dict) -> dict:
    normalized = {}

    for raw_field, value in updates.items():
        field = normalize_edit_field(raw_field)

        if not field:
            raise ValueError(f"Field `{raw_field}` tidak dikenali.")

        if field not in EDITABLE_TRANSACTION_FIELDS:
            raise ValueError(f"Field `{field}` tidak boleh diedit.")

        if field == "amount":
            try:
                value = float(value)
            except Exception:
                raise ValueError("Amount harus berupa angka.")

            if value <= 0:
                raise ValueError("Amount harus lebih dari 0.")

        elif field == "type":
            value = str(value).strip().lower()

            if value not in ["expense", "income", "transfer"]:
                raise ValueError("Type harus salah satu: expense, income, transfer.")

        elif field == "date":
            value = str(value).strip()

            try:
                datetime.strptime(value, "%Y-%m-%d")
            except Exception:
                raise ValueError("Date harus format YYYY-MM-DD. Contoh: 2026-06-10.")

        else:
            value = str(value).strip()

        normalized[field] = value

    return normalized


def get_single_transaction_by_ref(
    row_index: int | None = None,
    txn_id: str | None = None,
) -> dict | None:
    if row_index:
        matches = get_transactions_by_row_indices([row_index])
        return matches[0] if matches else None

    if txn_id:
        matches = get_transactions_by_ids([txn_id])

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            raise ValueError(
                "Transaction ID ini duplikat. Gunakan nomor dari /last agar spesifik."
            )

    return None


def build_transaction_row_from_record(txn: dict) -> list:
    """
    Bentuk ulang row sesuai header transactions.
    """
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
    ]


def calculate_account_effect(txn: dict) -> dict:
    """
    Hitung efek saldo asli dari sebuah transaksi.

    expense Cash 10k -> Cash -10k
    income Cash 10k -> Cash +10k
    transfer Cash ke BRI 10k -> Cash -10k, BRI +10k
    """
    deltas = {}

    def add_delta(account_name: str, value: float):
        if not account_name:
            return

        key = str(account_name).strip()
        if not key:
            return

        deltas[key] = deltas.get(key, 0) + float(value)

    txn_type = str(txn.get("type", "")).strip()
    amount = float(txn.get("amount", 0) or 0)
    account = str(txn.get("account", "")).strip()
    to_account = str(txn.get("to_account", "")).strip()

    if txn_type == "expense":
        add_delta(account, -amount)

    elif txn_type == "income":
        add_delta(account, amount)

    elif txn_type == "transfer":
        add_delta(account, -amount)
        add_delta(to_account, amount)

    return deltas


def calculate_edit_net_deltas(old_txn: dict, new_txn: dict) -> dict:
    """
    Net delta saldo untuk edit transaksi.

    Rumus:
    net_delta = -old_effect + new_effect
    """
    old_effect = calculate_account_effect(old_txn)
    new_effect = calculate_account_effect(new_txn)

    accounts = set(old_effect.keys()) | set(new_effect.keys())
    result = {}

    for account in accounts:
        delta = -old_effect.get(account, 0) + new_effect.get(account, 0)

        if delta != 0:
            result[account] = delta

    return result


def validate_edit_transaction(txn: dict) -> tuple[bool, str]:
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
        if not account or not to_account:
            return False, "Transfer wajib punya account dan to_account."

        if account == to_account:
            return False, "Account asal dan tujuan transfer tidak boleh sama."

    return True, "ok"


def preview_edit_transaction_by_ref(
    updates: dict,
    row_index: int | None = None,
    txn_id: str | None = None,
) -> dict:
    """
    Preview edit transaksi.
    Tidak mengubah sheet.
    """
    try:
        normalized_updates = normalize_edit_updates(updates)
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }

    try:
        old_txn = get_single_transaction_by_ref(row_index=row_index, txn_id=txn_id)
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }

    if not old_txn:
        return {
            "success": False,
            "message": "Transaksi tidak ditemukan.",
        }

    if is_debt_cashflow_transaction(old_txn):
        return {
            "success": False,
            "message": (
                "Transaksi debt cashflow belum boleh diedit dari fitur ini "
                "supaya sheet debts tidak inkonsisten."
            ),
        }

    new_txn = dict(old_txn)

    for field, value in normalized_updates.items():
        new_txn[field] = value

    is_valid, validation_message = validate_edit_transaction(new_txn)

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


def edit_transaction_by_ref(
    updates: dict,
    row_index: int | None = None,
    txn_id: str | None = None,
) -> dict:
    """
    Edit transaksi:
    1. Preview dan validasi
    2. Apply net delta saldo
    3. Update row transaksi
    """
    preview = preview_edit_transaction_by_ref(
        updates=updates,
        row_index=row_index,
        txn_id=txn_id,
    )

    if not preview.get("success"):
        return preview

    old_txn = preview["old_txn"]
    new_txn = preview["new_txn"]
    net_deltas = preview["net_deltas"]

    try:
        balance_result = apply_account_deltas(net_deltas)
    except Exception as e:
        return {
            "success": False,
            "message": f"Gagal update saldo: {str(e)}",
        }

    try:
        target_row_index = int(old_txn.get("_row_index"))

        # Jangan ubah ID transaksi.
        new_txn["id"] = old_txn.get("id")

        # Tandai raw_input agar kelihatan pernah diedit.
        old_raw = str(old_txn.get("raw_input", "") or "")
        if "[edited]" not in old_raw:
            new_txn["raw_input"] = f"{old_raw} [edited]".strip()
        else:
            new_txn["raw_input"] = old_raw

        row_values = build_transaction_row_from_record(new_txn)

        update_row(SHEET_TRANSACTIONS, target_row_index, row_values)

    except Exception as e:
        return {
            "success": False,
            "message": (
                "Saldo sudah sempat berubah, tapi update row transaksi gagal. "
                f"Cek manual di sheet. Error: {str(e)}"
            ),
            "new_balances": balance_result.get("new_balances", {}),
        }

    return {
        "success": True,
        "message": "ok",
        "old_txn": old_txn,
        "new_txn": new_txn,
        "net_deltas": net_deltas,
        "new_balances": balance_result.get("new_balances", {}),
    }