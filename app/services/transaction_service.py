"""Transaction service for saving, editing, deleting, batching, account balance updates, and debt relation updates."""


from datetime import datetime, timedelta
import re
import uuid

from app.nlp.normalizer import extract_amount_from_text
from app.services.resolver_service import ensure_category_for_transaction

from app.config import SHEET_ACCOUNTS, SHEET_TRANSACTIONS
from app.sheets.client import (
    append_row,
    append_rows,
    delete_rows,
    find_row_index,
    get_all_records,
    get_sheet,
    update_cell,
    update_row,
)

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


def get_current_month_str() -> str:
    """Get data needed for current month str."""
    return datetime.now().strftime("%Y-%m")


def normalize_export_period(period: str | None = None) -> dict:
    """Normalize and clean input for export period."""
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
        "Format export tidak dikenali. Gunakan: /download_data, /download_data today, /download_data week, /download_data month, atau /download_data 2026-06."
    )


def parse_date_safe(value):
    """Parse input into structured data for date safe."""
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def get_transactions_for_export(period: str | None = None) -> dict:
    """Get data needed for transactions for export."""
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


def is_skip_account_transaction(parsed: dict) -> bool:
    """Check whether a condition is true for skip account transaction."""
    account = str(parsed.get("account") or "").strip().lower()
    return bool(parsed.get("skip_account")) or account in SKIP_ACCOUNT_NAMES

# ── ID Generator ──────────────────────────────────────────────────────────────

def generate_transaction_id() -> str:
    """Helper for generate transaction id in the finance service layer."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    unique_suffix = uuid.uuid4().hex[:8]
    return f"txn_{timestamp}_{unique_suffix}"


# ── Row Builder ───────────────────────────────────────────────────────────────

def build_transaction_row(parsed: dict, raw_input: str) -> tuple[str, list]:
    """Build the data structure or message text for transaction row."""
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


def update_transaction_debt_relation(
    transaction_id: str,
    debt_ids: list[str],
    tipe_hutang: str = "piutang",
) -> dict:
    """Update existing data for transaction debt relation."""
    transaction_id = str(transaction_id or "").strip()
    clean_debt_ids = [str(x).strip() for x in (debt_ids or []) if str(x or "").strip()]
    tipe_hutang = str(tipe_hutang or "").strip()

    if not transaction_id:
        return {
            "success": False,
            "message": "transaction_id kosong.",
        }

    if not clean_debt_ids:
        return {
            "success": False,
            "message": "debt_ids kosong.",
        }

    records = get_all_records(SHEET_TRANSACTIONS)

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


def clear_transaction_debt_relation(transaction_id: str) -> dict:
    """Helper for clear transaction debt relation in the finance service layer."""
    transaction_id = str(transaction_id or "").strip()
    if not transaction_id:
        return {"success": False, "message": "transaction_id kosong."}

    records = get_all_records(SHEET_TRANSACTIONS)
    for row_index, record in enumerate(records, start=2):
        if str(record.get("id", "")).strip() == transaction_id:
            update_cell(SHEET_TRANSACTIONS, row_index, HUTANG_ID_COL, "")
            update_cell(SHEET_TRANSACTIONS, row_index, TIPE_HUTANG_COL, "")
            return {"success": True, "message": "ok"}

    return {"success": False, "message": f"Transaksi {transaction_id} tidak ditemukan."}


def validate_transaction(parsed: dict) -> tuple[bool, str]:
    """Validate data before it is used by transaction."""
    txn_type = str(parsed.get("type") or "").strip().lower()

    try:
        amount = float(parsed.get("amount", 0) or 0)
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

    skip_account = is_skip_account_transaction(parsed)

    if txn_type in ["expense", "income"] and not account and not skip_account:
        return False, "Rekening wajib dipilih."

    if txn_type in ["debt_offset", "debt_only"]:
        parsed["skip_account"] = True
        parsed["account"] = account or ("Debt Offset" if txn_type == "debt_offset" else "Debt Only")

    if txn_type == "transfer":
        if skip_account:
            return False, "Transfer tetap wajib memilih rekening asal dan tujuan."

        if not account or not to_account:
            return False, "Transfer wajib punya rekening asal dan tujuan."

        if account.lower() == to_account.lower():
            return False, "Rekening asal dan tujuan tidak boleh sama."

    return True, "ok"


# Account flow section

def get_account_balance(account_name: str) -> float | None:
    """Get data needed for account balance."""
    records = get_all_records(SHEET_ACCOUNTS)

    for record in records:
        if str(record.get("account_name", "")).strip().lower() == str(account_name).strip().lower():
            return float(record.get("balance", 0) or 0)

    return None


def update_account_balance(account_name: str, new_balance: float) -> bool:
    """Update existing data for account balance."""
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
    """Get data needed for all accounts."""
    return get_all_records(SHEET_ACCOUNTS)


def get_account_index_map() -> dict:
    """Get data needed for account index map."""
    records = get_all_records(SHEET_ACCOUNTS)
    result = {}

    for i, record in enumerate(records):
        name = str(record.get("account_name", "")).strip()
        if not name:
            continue

        result[name.lower()] = {
            "row": i + 2,  # +2 because row 1 is the header.
            "name": name,
            "balance": float(record.get("balance", 0) or 0),
        }

    return result


def validate_accounts_exist(account_deltas: dict) -> tuple[bool, list[str]]:
    """Validate data before it is used by accounts exist."""
    if not account_deltas:
        return True, []

    accounts_map = get_account_index_map()
    missing = []

    for account_name in account_deltas:
        key = str(account_name or "").strip().lower()
        if key and key not in accounts_map:
            missing.append(str(account_name))

    return len(missing) == 0, missing


def calculate_account_deltas(parsed_items: list[dict]) -> dict:
    """Calculate derived values for account deltas."""
    deltas = {}

    def add_delta(account_name: str, value: float):
        """Helper for add delta in the finance service layer."""
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

        if is_skip_account_transaction(parsed):
            continue

        if txn_type == "expense":
            add_delta(account, -amount)

        elif txn_type == "income":
            add_delta(account, amount)

        elif txn_type == "transfer":
            add_delta(account, -amount)
            add_delta(to_account, amount)

    return deltas


def apply_account_deltas(account_deltas: dict) -> dict:
    """Apply changes for account deltas."""
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

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Split bill parsing note: separate the paid transaction from each person share.
    for account_name in account_deltas:
        account_key = str(account_name).strip().lower()
        if account_key and account_key not in accounts_map:
            failed_accounts.append(account_name)

    if failed_accounts:
        return {
            "success": False,
            "new_balances": {},
            "failed_accounts": failed_accounts,
        }

    for account_name, delta in account_deltas.items():
        account_key = str(account_name).strip().lower()
        account_info = accounts_map.get(account_key)

        if not account_info:
            # Account flow section
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
    """Save data after validation and confirmation for transaction."""
    is_valid, validation_message = validate_transaction(parsed)
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
    if not accounts_ok:
        return {
            "success": False,
            "transaction_id": None,
            "message": "Rekening tidak ditemukan: " + ", ".join(missing_accounts),
            "new_balance": None,
            "new_balances": {},
        }

    txn_id, row = build_transaction_row(parsed, raw_input)

    try:
        append_row(SHEET_TRANSACTIONS, row)
        sort_transactions_sheet_by_date(desc=True)
    except Exception as e:
        return {
            "success": False,
            "transaction_id": None,
            "message": f"Gagal menyimpan transaksi: {str(e)}",
            "new_balance": None,
            "new_balances": {},
        }

    new_balance = None
    new_balance_account = None

    try:
        balance_result = apply_account_deltas(deltas)

        if parsed.get("type") == "transfer":
            new_balance_account = parsed.get("to_account") or parsed.get("account")
        else:
            new_balance_account = parsed.get("account") or parsed.get("to_account")

        if new_balance_account:
            for name, balance in balance_result.get("new_balances", {}).items():
                if str(name).lower() == str(new_balance_account).lower():
                    new_balance = balance
                    new_balance_account = name
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
                "new_balance_account": new_balance_account,
                "new_balances": balance_result.get("new_balances", {}),
            }

    except Exception as e:
        return {
            "success": True,
            "transaction_id": txn_id,
            "message": f"⚠️ Transaksi tersimpan, tapi saldo gagal diupdate: {str(e)}",
            "new_balance": None,
            "new_balances": {},
        }

    return {
        "success": True,
        "transaction_id": txn_id,
        "message": "ok",
        "new_balance": new_balance,
        "new_balance_account": new_balance_account,
        "new_balances": balance_result.get("new_balances", {}) if "balance_result" in locals() else {},
        "account_deltas": deltas,
    }


def save_transactions_batch(parsed_items: list[dict]) -> dict:
    """Save data after validation and confirmation for transactions batch."""
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

        if parsed.get("type") in {"expense", "income"}:
            parsed["category"] = ensure_category_for_transaction(parsed.get("category"), parsed.get("type"))

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

    deltas = calculate_account_deltas(valid_items)
    accounts_ok, missing_accounts = validate_accounts_exist(deltas)
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

    try:
        append_rows(SHEET_TRANSACTIONS, rows)
        sort_transactions_sheet_by_date(desc=True)
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
            "account_deltas": deltas,
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
    """Get data needed for transactions by month."""
    records = get_all_records(SHEET_TRANSACTIONS)
    prefix = f"{year}-{month:02d}"
    return [r for r in records if str(r.get("date", "")).startswith(prefix)]


def get_transactions_by_date(date_str: str) -> list[dict]:
    """Get data needed for transactions by date."""
    records = get_all_records(SHEET_TRANSACTIONS)
    return [r for r in records if r.get("date") == date_str]


def get_expense_by_category(year: int, month: int) -> dict:
    """Get data needed for expense by category."""
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
    """Check whether a condition is true for debt cashflow transaction."""
    category = str(txn.get("category", "")).strip()
    parsed_by = str(txn.get("parsed_by", "")).strip().lower()

    return category in DEBT_CASHFLOW_CATEGORIES or parsed_by == "debt"


def parse_transaction_date(date_value: str):
    """Parse input into structured data for transaction date."""
    try:
        return datetime.strptime(str(date_value), "%Y-%m-%d").date()
    except Exception:
        return None


def sort_transactions_sheet_by_date(desc: bool = True) -> dict:
    """Helper for sort transactions sheet by date in the finance service layer."""
    try:
        sheet = get_sheet(SHEET_TRANSACTIONS)
        values = sheet.get_all_values()

        if len(values) <= 2:
            return {"success": True, "message": "Tidak cukup row untuk sort."}

        header = values[0]
        rows = values[1:]
        col_count = len(header)

        normalized_rows = []
        for idx, row in enumerate(rows):
            padded = list(row) + [""] * max(0, col_count - len(row))
            padded = padded[:col_count]
            date_obj = parse_transaction_date(padded[1] if len(padded) > 1 else "")
            normalized_rows.append((idx, date_obj or datetime.min.date(), padded))

        normalized_rows.sort(
            key=lambda item: (item[1], item[0]),
            reverse=desc,
        )

        sorted_rows = [item[2] for item in normalized_rows]
        end_col = chr(ord("A") + col_count - 1)
        sheet.update(f"A2:{end_col}{len(sorted_rows) + 1}", sorted_rows)

        return {"success": True, "message": "transactions sorted by date"}

    except Exception as e:
        return {"success": False, "message": str(e)}


def get_transactions_with_row_index() -> list[dict]:
    """Get data needed for transactions with row index."""
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
    """Get data needed for recent transactions."""
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
        key=lambda x: (
            parse_transaction_date(x.get("date", "")) or datetime.min.date(),
            int(x.get("_row_index", 0)),
        ),
        reverse=True,
    )

    return records[:limit]

def get_transaction_by_id(txn_id: str) -> dict | None:
    """Get data needed for transaction by id."""
    records = get_transactions_with_row_index()

    for record in records:
        if str(record.get("id", "")).strip() == str(txn_id).strip():
            return record

    return None


def get_transactions_by_ids(txn_ids: list[str]) -> list[dict]:
    """Get data needed for transactions by ids."""
    target_ids = {str(x).strip() for x in txn_ids if str(x).strip()}
    records = get_transactions_with_row_index()

    return [
        r for r in records
        if str(r.get("id", "")).strip() in target_ids
    ]

def get_transactions_by_row_indices(row_indices: list[int]) -> list[dict]:
    """Get data needed for transactions by row indices."""
    target_rows = {int(x) for x in row_indices}
    records = get_transactions_with_row_index()

    return [
        r for r in records
        if int(r.get("_row_index", 0)) in target_rows
    ]


def calculate_reverse_deltas_for_delete(transactions: list[dict]) -> dict:
    """Calculate derived values for reverse deltas for delete."""
    deltas = {}

    def add_delta(account_name: str, value: float):
        """Helper for add delta in the finance service layer."""
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

        if is_skip_account_transaction(txn):
            continue

        if txn_type == "expense":
            add_delta(account, amount)

        elif txn_type == "income":
            add_delta(account, -amount)

        elif txn_type == "transfer":
            add_delta(account, amount)
            add_delta(to_account, -amount)

    return deltas


def parse_transaction_debt_ids(txn: dict) -> list[str]:
    """Parse input into structured data for transaction debt ids."""
    raw = str(txn.get("hutang_id", "") or "").strip()
    if not raw:
        return []
    return [part.strip() for part in re.split(r"[,;\s]+", raw) if part.strip()]


def transaction_has_debt_relation(txn: dict) -> bool:
    """Helper for transaction has debt relation in the finance service layer."""
    return bool(parse_transaction_debt_ids(txn)) or bool(str(txn.get("tipe_hutang", "") or "").strip())


def preview_delete_transactions_by_refs(
    row_indices: list[int] | None = None,
    txn_ids: list[str] | None = None,
) -> dict:
    """Helper for preview delete transactions by refs in the finance service layer."""
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
        if is_debt_cashflow_transaction(txn) and not transaction_has_debt_relation(txn):
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
    """Helper for preview delete transactions in the finance service layer."""
    transactions = get_transactions_by_ids(txn_ids)
    found_ids = {str(t.get("id", "")).strip() for t in transactions}
    requested_ids = {str(x).strip() for x in txn_ids}

    missing_ids = sorted(requested_ids - found_ids)

    blocked = []
    deletable = []

    for txn in transactions:
        if is_debt_cashflow_transaction(txn) and not transaction_has_debt_relation(txn):
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
    """Delete data safely for transactions by ids."""
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
    try:
        from app.services.debt_service import void_debts_for_transaction, reverse_debt_payment_transaction

        for txn in deletable:
            txn_id = str(txn.get("id", "") or "").strip()
            linked_ids = parse_transaction_debt_ids(txn)
            category = str(txn.get("category", "") or "").strip()

            # Account flow section
            # Debt flow section
            if category in {"Pembayaran Piutang", "Bayar Utang"}:
                reverse_result = reverse_debt_payment_transaction(txn)
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
                continue

            if not txn_id and not linked_ids:
                continue

            linked_result = void_debts_for_transaction(txn_id, linked_ids)
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
        "linked_debts_voided": linked_debt_voided_ids,
        "reversed_payment_debts": reversed_payment_debt_items,
    }

def delete_transactions_by_refs(
    row_indices: list[int] | None = None,
    txn_ids: list[str] | None = None,
) -> dict:
    """Delete data safely for transactions by refs."""
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
        if balance_result.get("failed_accounts"):
            return {
                "success": False,
                "message": "Rekening tidak ditemukan: " + ", ".join(balance_result["failed_accounts"]),
                "deleted_count": 0,
                "deleted_ids": [],
                "blocked": blocked,
                "missing_ids": missing_ids,
                "missing_rows": missing_rows,
                "new_balances": {},
            }
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

    linked_debt_voided_ids = []
    reversed_payment_debt_items = []
    try:
        from app.services.debt_service import void_debts_for_transaction, reverse_debt_payment_transaction

        for txn in deletable:
            txn_id = str(txn.get("id", "") or "").strip()
            linked_ids = parse_transaction_debt_ids(txn)
            category = str(txn.get("category", "") or "").strip()

            if category in {"Pembayaran Piutang", "Bayar Utang"}:
                reverse_result = reverse_debt_payment_transaction(txn)
                if not reverse_result.get("success"):
                    return {
                        "success": False,
                        "message": reverse_result.get("message", "Gagal membalik pembayaran debt terkait transaksi."),
                        "deleted_count": 0,
                        "deleted_ids": [],
                        "blocked": blocked,
                        "missing_ids": missing_ids,
                        "missing_rows": missing_rows,
                        "new_balances": balance_result.get("new_balances", {}),
                    }
                reversed_payment_debt_items.extend(reverse_result.get("reversed", []))
                continue

            if not txn_id and not linked_ids:
                continue

            linked_result = void_debts_for_transaction(txn_id, linked_ids)
            if not linked_result.get("success"):
                return {
                    "success": False,
                    "message": linked_result.get("message", "Gagal void debt terkait transaksi."),
                    "deleted_count": 0,
                    "deleted_ids": [],
                    "blocked": blocked,
                    "missing_ids": missing_ids,
                    "missing_rows": missing_rows,
                    "new_balances": balance_result.get("new_balances", {}),
                }
            linked_debt_voided_ids.extend(linked_result.get("voided_ids", []))
    except Exception as e:
        return {
            "success": False,
            "message": f"Gagal sync debt terkait transaksi: {str(e)}",
            "deleted_count": 0,
            "deleted_ids": [],
            "blocked": blocked,
            "missing_ids": missing_ids,
            "missing_rows": missing_rows,
            "new_balances": balance_result.get("new_balances", {}),
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


def normalize_edit_field(field: str) -> str | None:
    """Normalize and clean input for edit field."""
    key = str(field or "").strip().lower()

    # Split bill parsing note: separate the paid transaction from each person share.
    # Account flow section
    if key in EDITABLE_TRANSACTION_FIELDS:
        return key

    return FIELD_ALIASES.get(key)


def normalize_edit_updates(updates: dict) -> dict:
    """Normalize and clean input for edit updates."""
    normalized = {}

    for raw_field, value in updates.items():
        field = normalize_edit_field(raw_field)

        if not field:
            raise ValueError(f"Field `{raw_field}` tidak dikenali.")

        if field not in EDITABLE_TRANSACTION_FIELDS:
            raise ValueError(f"Field `{field}` tidak boleh diedit.")

        if field == "amount":
            parsed_amount = extract_amount_from_text(str(value))
            if parsed_amount is not None:
                value = float(parsed_amount)
            else:
                try:
                    value = float(value)
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
    """Get data needed for single transaction by ref."""
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
    """Build the data structure or message text for transaction row from record."""
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


def calculate_account_effect(txn: dict) -> dict:
    """Calculate derived values for account effect."""
    deltas = {}

    def add_delta(account_name: str, value: float):
        """Helper for add delta in the finance service layer."""
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


def calculate_edit_net_deltas(old_txn: dict, new_txn: dict) -> dict:
    """Calculate derived values for edit net deltas."""
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
        if not account or not to_account:
            return False, "Transfer wajib punya account dan to_account."

        if account.lower() == to_account.lower():
            return False, "Account asal dan tujuan transfer tidak boleh sama."

    return True, "ok"


def preview_edit_transaction_by_ref(
    updates: dict,
    row_index: int | None = None,
    txn_id: str | None = None,
) -> dict:
    """Helper for preview edit transaction by ref in the finance service layer."""
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

    old_payment_category = str(old_txn.get("category", "") or "").strip()
    if old_payment_category in {"Pembayaran Piutang", "Bayar Utang"}:
        # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
        # Debt flow section
        if set(normalized_updates.keys()) != {"amount"}:
            return {
                "success": False,
                "message": (
                    "Transaksi pembayaran hutang/piutang hanya boleh diedit nominalnya. "
                    "Untuk koreksi lain, pakai /delete_txn lalu input ulang."
                ),
            }

    old_has_debt_relation = transaction_has_debt_relation(old_txn)

    # Debt flow section
    # Debt flow section
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



def _payment_allocation_note(raw: str, allocations: list[dict], overpayment: float = 0.0, policy: str = "") -> str:
    """Helper for payment allocation note in the finance service layer."""
    parts = [str(raw or "").strip()]
    alloc_parts = []
    for item in allocations or []:
        debt_id = str(item.get("debt_id") or "").strip()
        amount = item.get("amount")
        if debt_id and amount is not None:
            alloc_parts.append(f"{debt_id}:{float(amount)}")
    if alloc_parts:
        parts.append("debt_allocations=" + ";".join(alloc_parts))
    if overpayment:
        parts.append(f"overpayment={float(overpayment)}")
    if policy:
        parts.append(f"overpayment_policy={policy}")
    return " | ".join([p for p in parts if p]).strip(" |")


def edit_debt_payment_transaction_amount(preview: dict) -> dict:
    """Helper for edit debt payment transaction amount in the finance service layer."""
    old_txn = preview["old_txn"]
    new_txn = preview["new_txn"]
    net_deltas = preview["net_deltas"]
    category = str(old_txn.get("category", "") or "").strip()
    person = str(old_txn.get("subject", "") or "").strip()
    if not person:
        return {"success": False, "message": "Subject/person transaksi payment kosong."}

    target_debt_type = "receivable" if category == "Pembayaran Piutang" else "payable"
    new_amount = float(new_txn.get("amount", 0) or 0)
    raw_note = str(old_txn.get("raw_input", "") or old_txn.get("catatan", "") or "")

    try:
        from app.services.debt_service import reverse_debt_payment_transaction, add_payment_by_person
        reverse_result = reverse_debt_payment_transaction(old_txn)
        if not reverse_result.get("success"):
            return {"success": False, "message": reverse_result.get("message", "Gagal reverse payment lama.")}

        payment_result = add_payment_by_person(
            person,
            new_amount,
            note=f"Edit payment dari transaksi {old_txn.get('id') or '-'}",
            target_debt_type=target_debt_type,
            overpayment_policy="opposite_debt",
        )
        if not payment_result.get("success"):
            return {"success": False, "message": payment_result.get("message", "Gagal alokasi payment baru.")}
    except Exception as e:
        return {"success": False, "message": f"Gagal sync debt payment: {str(e)}"}

    try:
        balance_result = apply_account_deltas(net_deltas)
        if balance_result.get("failed_accounts"):
            return {"success": False, "message": "Rekening tidak ditemukan: " + ", ".join(balance_result["failed_accounts"])}
    except Exception as e:
        return {"success": False, "message": f"Gagal update saldo: {str(e)}"}

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
    except Exception as e:
        return {
            "success": False,
            "message": "Saldo/debt sudah sempat berubah, tapi update row transaksi gagal. Cek manual. Error: " + str(e),
            "new_balances": balance_result.get("new_balances", {}),
        }

    return {
        "success": True,
        "message": "ok",
        "old_txn": old_txn,
        "new_txn": new_txn,
        "net_deltas": net_deltas,
        "new_balances": balance_result.get("new_balances", {}),
        "debt_sync": {"success": True, "payment_reallocated": True, "payment_result": payment_result},
    }

def edit_transaction_by_ref(
    updates: dict,
    row_index: int | None = None,
    txn_id: str | None = None,
) -> dict:
    """Helper for edit transaction by ref in the finance service layer."""
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

    old_payment_category = str(old_txn.get("category", "") or "").strip()
    if old_payment_category in {"Pembayaran Piutang", "Bayar Utang"}:
        return edit_debt_payment_transaction_amount(preview)

    try:
        balance_result = apply_account_deltas(net_deltas)
        if balance_result.get("failed_accounts"):
            return {
                "success": False,
                "message": "Rekening tidak ditemukan: " + ", ".join(balance_result["failed_accounts"]),
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Gagal update saldo: {str(e)}",
        }

    try:
        target_row_index = int(old_txn.get("_row_index"))

        # Account flow section
        new_txn["id"] = old_txn.get("id")

        # Implementation note for this project-specific finance flow.
        old_raw = str(old_txn.get("raw_input", "") or "")
        if "[edited]" not in old_raw:
            new_txn["raw_input"] = f"{old_raw} [edited]".strip()
        else:
            new_txn["raw_input"] = old_raw

        row_values = build_transaction_row_from_record(new_txn)

        update_row(SHEET_TRANSACTIONS, target_row_index, row_values)
        sort_transactions_sheet_by_date(desc=True)

    except Exception as e:
        return {
            "success": False,
            "message": (
                "Saldo sudah sempat berubah, tapi update row transaksi gagal. "
                f"Cek manual di sheet. Error: {str(e)}"
            ),
            "new_balances": balance_result.get("new_balances", {}),
        }

    debt_sync_result = {"success": True, "updated": [], "overpaid": []}
    if transaction_has_debt_relation(old_txn) or transaction_has_debt_relation(new_txn):
        try:
            from app.services.debt_service import sync_debt_charges_from_transaction_edit

            debt_sync_result = sync_debt_charges_from_transaction_edit(old_txn, new_txn)
        except Exception as e:
            debt_sync_result = {
                "success": False,
                "message": str(e),
                "updated": [],
                "overpaid": [],
            }

    return {
        "success": True,
        "message": "ok" if debt_sync_result.get("success") else "Transaksi diedit, tapi sync debt perlu dicek: " + str(debt_sync_result.get("message") or "-"),
        "old_txn": old_txn,
        "new_txn": new_txn,
        "net_deltas": net_deltas,
        "new_balances": balance_result.get("new_balances", {}),
        "debt_sync": debt_sync_result,
    }