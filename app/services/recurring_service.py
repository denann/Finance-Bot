import calendar
import uuid
from datetime import datetime, date

from app.config import SHEET_RECURRING_RULES, SHEET_RECURRING_LOGS
from app.sheets.client import append_row, get_all_records, update_cell, rollback_current_sheets_transaction, sheets_transaction
from app.services.transaction_service import save_transaction


RECURRING_RULE_COLUMNS = [
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
]


RECURRING_LOG_COLUMNS = [
    "id",
    "rule_id",
    "transaction_id",
    "run_date",
    "status",
    "message",
    "created_at",
]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def generate_recurring_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = uuid.uuid4().hex[:6]
    return f"rec_{timestamp}_{suffix}"


def generate_recurring_log_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = uuid.uuid4().hex[:6]
    return f"reclog_{timestamp}_{suffix}"


def parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def safe_float(value) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def normalize_day_of_month(day) -> int:
    try:
        day_int = int(day)
    except Exception:
        raise ValueError("Tanggal recurring harus berupa angka 1-31.")

    if day_int < 1 or day_int > 31:
        raise ValueError("Tanggal recurring harus di antara 1 sampai 31.")

    return day_int


def normalize_frequency(value: str) -> str:
    clean = str(value or "").strip().lower()

    aliases = {
        "monthly": "monthly",
        "bulan": "monthly",
        "bulanan": "monthly",
        "setiap bulan": "monthly",
    }

    frequency = aliases.get(clean)

    if not frequency:
        raise ValueError("Frequency belum valid. Saat ini baru support: monthly.")

    return frequency


def get_last_day_of_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def clamp_day(year: int, month: int, day: int) -> int:
    last_day = get_last_day_of_month(year, month)
    return min(day, last_day)


def calculate_next_monthly_run(day_of_month: int, from_date: date | None = None) -> str:
    """
    Hitung next_run_date untuk monthly recurring.

    Kalau tanggal target bulan ini masih belum lewat, pakai bulan ini.
    Kalau sudah lewat, pakai bulan depan.

    Contoh:
    - hari ini 2026-06-10, day=25 -> 2026-06-25
    - hari ini 2026-06-10, day=5  -> 2026-07-05
    """
    base = from_date or datetime.now().date()

    target_day = clamp_day(base.year, base.month, day_of_month)
    target = date(base.year, base.month, target_day)

    if target >= base:
        return target.strftime("%Y-%m-%d")

    if base.month == 12:
        next_year = base.year + 1
        next_month = 1
    else:
        next_year = base.year
        next_month = base.month + 1

    next_day = clamp_day(next_year, next_month, day_of_month)
    next_target = date(next_year, next_month, next_day)

    return next_target.strftime("%Y-%m-%d")


def calculate_next_run_after_execution(rule: dict, run_date: date | None = None) -> str:
    frequency = normalize_frequency(rule.get("frequency"))
    day_of_month = normalize_day_of_month(rule.get("day_of_month"))

    base = run_date or datetime.now().date()

    if frequency == "monthly":
        if base.month == 12:
            next_year = base.year + 1
            next_month = 1
        else:
            next_year = base.year
            next_month = base.month + 1

        next_day = clamp_day(next_year, next_month, day_of_month)
        return date(next_year, next_month, next_day).strftime("%Y-%m-%d")

    raise ValueError("Frequency belum didukung.")


def build_recurring_row(rule: dict) -> list:
    return [rule.get(col, "") for col in RECURRING_RULE_COLUMNS]


def build_recurring_log_row(log: dict) -> list:
    return [log.get(col, "") for col in RECURRING_LOG_COLUMNS]


def add_recurring_rule(
    name: str,
    txn_type: str,
    amount: float,
    category: str,
    account: str,
    frequency: str,
    day_of_month: int,
    description: str | None = None,
    subject: str | None = None,
    catatan: str | None = None,
    tipe_pengeluaran: str | None = None,
    to_account: str | None = None,
) -> dict:
    txn_type = str(txn_type or "").strip().lower()

    if txn_type not in ["expense", "income"]:
        raise ValueError("Type recurring hanya support expense atau income.")

    frequency = normalize_frequency(frequency)
    day_of_month = normalize_day_of_month(day_of_month)

    amount = safe_float(amount)

    if amount <= 0:
        raise ValueError("Amount recurring harus lebih dari 0.")

    created_at = now_str()

    rule = {
        "id": generate_recurring_id(),
        "name": str(name or "").strip(),
        "type": txn_type,
        "amount": amount,
        "category": str(category or "").strip(),
        "account": str(account or "").strip(),
        "to_account": str(to_account or "").strip() if to_account else "",
        "subject": str(subject or "").strip() if subject else "",
        "description": str(description or name or "").strip(),
        "catatan": str(catatan or "").strip() if catatan else "",
        "tipe_pengeluaran": str(tipe_pengeluaran or "").strip() if tipe_pengeluaran else "",
        "frequency": frequency,
        "day_of_month": day_of_month,
        "next_run_date": calculate_next_monthly_run(day_of_month),
        "is_active": "TRUE",
        "created_at": created_at,
        "updated_at": created_at,
    }

    append_row(SHEET_RECURRING_RULES, build_recurring_row(rule))

    return rule


def get_recurring_rules(active_only: bool = False) -> list[dict]:
    records = get_all_records(SHEET_RECURRING_RULES)

    if not active_only:
        return records

    return [
        r for r in records
        if str(r.get("is_active", "")).strip().upper() == "TRUE"
    ]


def get_due_recurring_rules(target_date: date | None = None) -> list[dict]:
    target = target_date or datetime.now().date()
    active_rules = get_recurring_rules(active_only=True)

    due_rules = []

    for rule in active_rules:
        next_run = parse_date(rule.get("next_run_date"))

        if not next_run:
            continue

        if next_run <= target:
            due_rules.append(rule)

    return due_rules


def find_recurring_rule_row_index(rule_id: str) -> int | None:
    records = get_all_records(SHEET_RECURRING_RULES)

    for idx, record in enumerate(records, start=2):
        if str(record.get("id", "")).strip() == str(rule_id).strip():
            return idx

    return None


def update_recurring_rule_cells(rule_id: str, updates: dict) -> bool:
    row_index = find_recurring_rule_row_index(rule_id)

    if not row_index:
        return False

    for field, value in updates.items():
        if field not in RECURRING_RULE_COLUMNS:
            continue

        col_index = RECURRING_RULE_COLUMNS.index(field) + 1
        update_cell(SHEET_RECURRING_RULES, row_index, col_index, value)

    return True


def disable_recurring_rule(rule_id: str) -> bool:
    return update_recurring_rule_cells(
        rule_id,
        {
            "is_active": "FALSE",
            "updated_at": now_str(),
        },
    )

def get_recurring_rule_by_id(rule_id: str) -> dict | None:
    records = get_all_records(SHEET_RECURRING_RULES)

    for record in records:
        if str(record.get("id", "")).strip() == str(rule_id).strip():
            return record

    return None


def normalize_recurring_edit_field(field: str) -> str | None:
    key = str(field or "").strip().lower()

    aliases = {
        "name": "name",
        "nama": "name",

        "type": "type",
        "tipe": "type",

        "amount": "amount",
        "nominal": "amount",
        "jumlah": "amount",
        "harga": "amount",

        "category": "category",
        "kategori": "category",

        "account": "account",
        "rekening": "account",
        "akun": "account",

        "to_account": "to_account",
        "rekening_tujuan": "to_account",
        "tujuan": "to_account",

        "subject": "subject",
        "subjek": "subject",
        "orang": "subject",

        "description": "description",
        "desc": "description",
        "deskripsi": "description",
        "keterangan": "description",

        "catatan": "catatan",
        "note": "catatan",

        "tipe_pengeluaran": "tipe_pengeluaran",
        "jenis_pengeluaran": "tipe_pengeluaran",

        "frequency": "frequency",
        "freq": "frequency",

        "day": "day_of_month",
        "tanggal": "day_of_month",
        "day_of_month": "day_of_month",

        "next_run": "next_run_date",
        "next_run_date": "next_run_date",

        "active": "is_active",
        "is_active": "is_active",
        "aktif": "is_active",
    }

    return aliases.get(key)


def normalize_recurring_edit_value(field: str, value):
    value = str(value or "").strip()

    if field == "type":
        clean = value.lower()
        if clean not in ["expense", "income"]:
            raise ValueError("Type hanya boleh `expense` atau `income`.")
        return clean

    if field == "amount":
        clean = value.replace(".", "").replace(",", "")
        try:
            amount = float(clean)
        except Exception:
            raise ValueError("Amount harus angka. Contoh: `75000`.")

        if amount <= 0:
            raise ValueError("Amount harus lebih dari 0.")

        return amount

    if field == "frequency":
        return normalize_frequency(value)

    if field == "day_of_month":
        return normalize_day_of_month(value)

    if field == "next_run_date":
        parsed = parse_date(value)
        if not parsed:
            raise ValueError("next_run_date harus format YYYY-MM-DD. Contoh: `2026-06-11`.")
        return parsed.strftime("%Y-%m-%d")

    if field == "is_active":
        clean = value.lower()
        if clean in ["true", "1", "yes", "ya", "aktif", "on"]:
            return "TRUE"
        if clean in ["false", "0", "no", "tidak", "nonaktif", "off"]:
            return "FALSE"
        raise ValueError("is_active hanya boleh TRUE/FALSE atau on/off.")

    return value


def edit_recurring_rule(rule_id: str, updates: dict) -> dict:
    """
    Edit recurring rule berdasarkan ID.

    Output:
    {
        "success": bool,
        "rule_before": dict,
        "rule_after": dict,
        "updates": dict,
        "message": str
    }
    """
    rule = get_recurring_rule_by_id(rule_id)

    if not rule:
        return {
            "success": False,
            "rule_before": {},
            "rule_after": {},
            "updates": {},
            "message": "Recurring rule tidak ditemukan.",
        }

    normalized_updates = {}

    for raw_field, raw_value in updates.items():
        field = normalize_recurring_edit_field(raw_field)

        if not field:
            raise ValueError(f"Field `{raw_field}` tidak dikenali.")

        if field not in RECURRING_RULE_COLUMNS:
            raise ValueError(f"Field `{raw_field}` tidak bisa diedit.")

        if field in ["id", "created_at", "updated_at"]:
            raise ValueError(f"Field `{field}` tidak boleh diedit.")

        normalized_updates[field] = normalize_recurring_edit_value(field, raw_value)

    if not normalized_updates:
        raise ValueError("Tidak ada field yang diedit.")

    # Kalau tanggal/frequency berubah dan user tidak set next_run_date manual,
    # hitung ulang next_run_date dari hari ini.
    if (
        ("day_of_month" in normalized_updates or "frequency" in normalized_updates)
        and "next_run_date" not in normalized_updates
    ):
        merged_rule = dict(rule)
        merged_rule.update(normalized_updates)

        frequency = normalize_frequency(merged_rule.get("frequency"))
        day_of_month = normalize_day_of_month(merged_rule.get("day_of_month"))

        if frequency == "monthly":
            normalized_updates["next_run_date"] = calculate_next_monthly_run(day_of_month)

    normalized_updates["updated_at"] = now_str()

    success = update_recurring_rule_cells(rule_id, normalized_updates)

    if not success:
        return {
            "success": False,
            "rule_before": rule,
            "rule_after": {},
            "updates": normalized_updates,
            "message": "Gagal update recurring rule.",
        }

    updated_rule = get_recurring_rule_by_id(rule_id) or {}

    return {
        "success": True,
        "rule_before": rule,
        "rule_after": updated_rule,
        "updates": normalized_updates,
        "message": "Recurring rule berhasil diupdate.",
    }

def log_recurring_run(
    rule_id: str,
    transaction_id: str | None,
    run_date: str,
    status: str,
    message: str,
):
    log = {
        "id": generate_recurring_log_id(),
        "rule_id": rule_id,
        "transaction_id": transaction_id or "",
        "run_date": run_date,
        "status": status,
        "message": message,
        "created_at": now_str(),
    }

    append_row(SHEET_RECURRING_LOGS, build_recurring_log_row(log))

    return log


def build_transaction_from_recurring_rule(rule: dict, run_date: str | None = None) -> dict:
    txn_date = run_date or today_str()

    return {
        "date": txn_date,
        "type": str(rule.get("type", "")).strip(),
        "amount": safe_float(rule.get("amount")),
        "category": str(rule.get("category", "")).strip(),
        "account": str(rule.get("account", "")).strip(),
        "to_account": str(rule.get("to_account", "")).strip(),
        "subject": str(rule.get("subject", "")).strip(),
        "description": str(rule.get("description") or rule.get("name") or "").strip(),
        "catatan": str(rule.get("catatan", "")).strip(),
        "tipe_pengeluaran": str(rule.get("tipe_pengeluaran", "")).strip(),
        "raw_input": f"recurring:{rule.get('id')}",
        "parsed_by": "recurring",
    }



def mark_recurring_rule_paid(rule_id: str, run_date: date | None = None) -> dict:
    """
    Tandai recurring sudah dibayar untuk periode jatuh tempo saat ini.

    Efek:
    1. Buat transaksi dari rule recurring.
    2. Perbarui next_run_date ke periode berikutnya.
    3. Catat recurring_logs.
    """
    rule = get_recurring_rule_by_id(rule_id)
    if not rule:
        return {
            "success": False,
            "message": "Recurring rule tidak ditemukan.",
            "transaction_id": None,
            "next_run_date": None,
            "rule": None,
        }

    if str(rule.get("is_active", "")).strip().upper() != "TRUE":
        return {
            "success": False,
            "message": "Recurring rule sudah nonaktif.",
            "transaction_id": None,
            "next_run_date": rule.get("next_run_date"),
            "rule": rule,
        }

    target = run_date or datetime.now().date()
    run_date_str = target.strftime("%Y-%m-%d")

    try:
        parsed_txn = build_transaction_from_recurring_rule(rule, run_date=run_date_str)
        transaction_result = save_transaction(
            parsed_txn,
            raw_input=parsed_txn.get("raw_input") or f"recurring:{rule_id}",
        )

        if not transaction_result.get("success"):
            raise RuntimeError(transaction_result.get("message", "Gagal membuat transaksi recurring."))

        transaction_id = transaction_result.get("transaction_id")
        next_run_date = calculate_next_run_after_execution(rule, target)

        update_recurring_rule_cells(
            rule_id,
            {
                "next_run_date": next_run_date,
                "updated_at": now_str(),
            },
        )

        log_recurring_run(
            rule_id=rule_id,
            transaction_id=transaction_id,
            run_date=run_date_str,
            status="paid",
            message=f"Recurring marked paid. Next run: {next_run_date}",
        )

        return {
            "success": True,
            "message": "ok",
            "transaction_id": transaction_id,
            "next_run_date": next_run_date,
            "rule": rule,
        }
    except Exception as e:
        rollback_current_sheets_transaction()
        return {
            "success": False,
            "message": str(e),
            "transaction_id": None,
            "next_run_date": rule.get("next_run_date"),
            "rule": rule,
        }


def process_due_recurring_rules(target_date: date | None = None) -> dict:
    target = target_date or datetime.now().date()
    run_date = target.strftime("%Y-%m-%d")

    due_rules = get_due_recurring_rules(target)

    results = {
        "run_date": run_date,
        "count_due": len(due_rules),
        "success": [],
        "failed": [],
    }

    for rule in due_rules:
        rule_id = str(rule.get("id", "")).strip()

        try:
            parsed_txn = build_transaction_from_recurring_rule(rule, run_date=run_date)
            transaction_result = save_transaction(
                parsed_txn,
                raw_input=parsed_txn.get("raw_input") or f"recurring:{rule_id}",
            )

            if not transaction_result.get("success"):
                raise RuntimeError(transaction_result.get("message", "Gagal membuat transaksi recurring."))

            transaction_id = transaction_result.get("transaction_id")

            next_run_date = calculate_next_run_after_execution(rule, target)

            update_recurring_rule_cells(
                rule_id,
                {
                    "next_run_date": next_run_date,
                    "updated_at": now_str(),
                },
            )

            log_recurring_run(
                rule_id=rule_id,
                transaction_id=transaction_id,
                run_date=run_date,
                status="success",
                message=f"Recurring transaction created. Next run: {next_run_date}",
            )

            results["success"].append(
                {
                    "rule": rule,
                    "transaction_id": transaction_id,
                    "next_run_date": next_run_date,
                }
            )

        except Exception as e:
            rollback_current_sheets_transaction()
            message = str(e)

            # Karena operasi recurring dibuat all-or-nothing, success yang sudah
            # sempat tercatat di memory tidak boleh ditampilkan sebagai sukses.
            results["success"] = []
            results["failed"].append(
                {
                    "rule": rule,
                    "message": message,
                }
            )
            break

    return results

