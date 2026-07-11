"""Recurring transaction service for rules, due dates, logs, and generated transactions."""


# Import calendar for this module's local operations.
import calendar
# Import re for this module's amount and date parsing helpers.
import re
# Import uuid for this module's local operations.
import uuid
# Import threading for single-process recurring occurrence claims.
import threading
# Import datetime so this module can use its helpers.
from datetime import datetime, date

# Import app.config so this module can use its helpers.
from app.config import SHEET_RECURRING_RULES, SHEET_RECURRING_LOGS
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import append_row, get_all_records, update_cell, rollback_current_sheets_transaction, sheets_transaction
# Import app.services.transaction_service so this module can use its helpers.
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

_recurring_run_lock = threading.RLock()
_recurring_inflight: set[str] = set()


def recurring_occurrence_key(rule_id: str, scheduled_run_date: str) -> str:
    """Return the logical identity for one recurring occurrence."""

    return f"{str(rule_id or '').strip()}:{str(scheduled_run_date or '').strip()}"


def find_processed_recurring_run(rule_id: str, scheduled_run_date: str) -> dict | None:
    """Find a successful run in the existing recurring log worksheet.

    Args:
        rule_id: Recurring rule identifier.
        scheduled_run_date: Due date that identifies the occurrence.

    Returns:
        Existing successful log record, otherwise ``None``.

    Side effects:
        Performs a read-only lookup on the existing ``recurring_logs`` sheet.
        No worksheet or column is created.
    """

    success_statuses = {"paid", "success", "processed", "committed"}
    for record in get_all_records(SHEET_RECURRING_LOGS):
        if str(record.get("rule_id") or "").strip() != str(rule_id or "").strip():
            continue
        if str(record.get("run_date") or "").strip() != str(scheduled_run_date or "").strip():
            continue
        if str(record.get("status") or "").strip().lower() in success_statuses:
            return record
    return None


# Helper for now str.
def now_str() -> str:
    """Coordinate the now str logic in the service layer.

    Args:
        None.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Helper for today str.
def today_str() -> str:
    """Coordinate the today str logic in the service layer.

    Args:
        None.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return datetime.now().strftime("%Y-%m-%d")


# Helper for generate recurring id.
def generate_recurring_id() -> str:
    """Coordinate the generate recurring id logic in the service layer.

    Args:
        None.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = uuid.uuid4().hex[:6]
    return f"rec_{timestamp}_{suffix}"


# Helper for generate recurring log id.
def generate_recurring_log_id() -> str:
    """Coordinate the generate recurring log id logic in the service layer.

    Args:
        None.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = uuid.uuid4().hex[:6]
    return f"reclog_{timestamp}_{suffix}"


# Helper for parse date.
def parse_date(value: str) -> date | None:
    """Parse caller input for the parse date workflow in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `date | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return None


# Helper for safe float.
def safe_float(value) -> float:
    """Coordinate the safe float logic in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        return float(value or 0)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return 0.0


# Helper for parse recurring amount value.
def parse_recurring_amount_value(value) -> float:
    """Parse recurring amount input for add and edit flows.

    Args:
        value: Numeric value or user-facing amount text. Supported examples
            include `75000`, `300k`, `65rb`, `1.5 juta`, and `1,5jt`.

    Returns:
        Parsed rupiah amount as a float. Invalid values return `0.0`.

    Side effects:
        None. This helper only parses an amount and never writes to Sheets.

    Flow constraints:
        Keep `/recurring_add` and `/recurring_edit` consistent with help
        examples that use `amount=...` and Indonesian shorthand units.
    """
    # Preserve numeric service inputs from internal callers.
    if isinstance(value, (int, float)):
        return float(value or 0)

    raw = str(value or "").strip().lower()
    if not raw:
        return 0.0

    # Read common Indonesian amount units before removing text.
    multiplier = 1
    if re.search(r"\b(jt|juta)\b", raw):
        multiplier = 1_000_000
    elif re.search(r"\b(rb|ribu|k)\b", raw):
        multiplier = 1_000

    # Keep decimals for shorthand units, but treat plain numbers as rupiah.
    number_text = re.sub(r"\b(jt|juta|rb|ribu|k)\b", "", raw).strip()
    if multiplier != 1:
        number_text = number_text.replace(",", ".")
        number_text = re.sub(r"[^0-9.]", "", number_text)
        if number_text.count(".") > 1:
            first, *rest = number_text.split(".")
            number_text = first + "." + "".join(rest)
    else:
        number_text = re.sub(r"[^0-9]", "", number_text)

    # Return zero on invalid values so callers can raise their existing errors.
    try:
        return float(number_text or 0) * multiplier
    except Exception:
        return 0.0


# Helper for normalize day of month.
def normalize_day_of_month(day) -> int:
    """Normalize input values for the normalize day of month workflow in the service layer.

    Args:
        day: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `int` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        day_int = int(day)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        raise ValueError("Tanggal recurring harus berupa angka 1-31.")

    # Handle day int < 1 or day int > 31.
    if day_int < 1 or day_int > 31:
        raise ValueError("Tanggal recurring harus di antara 1 sampai 31.")

    return day_int


# Helper for normalize frequency.
def normalize_frequency(value: str) -> str:
    """Normalize input values for the normalize frequency workflow in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    clean = str(value or "").strip().lower()

    aliases = {
        "monthly": "monthly",
        "bulan": "monthly",
        "bulanan": "monthly",
        "setiap bulan": "monthly",
    }

    frequency = aliases.get(clean)

    # Validate missing frequency before continuing.
    if not frequency:
        raise ValueError("Frequency belum valid. Saat ini baru support: monthly.")

    return frequency


# Helper for get last day of month.
def get_last_day_of_month(year: int, month: int) -> int:
    """Retrieve data needed by the get last day of month workflow in the service layer.

    Args:
        year: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `int` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return calendar.monthrange(year, month)[1]


# Helper for clamp day.
def clamp_day(year: int, month: int, day: int) -> int:
    """Coordinate the clamp day logic in the service layer.

    Args:
        year: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        day: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `int` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    last_day = get_last_day_of_month(year, month)
    return min(day, last_day)


# Helper for calculate next monthly run.
def calculate_next_monthly_run(day_of_month: int, from_date: date | None = None) -> str:
    """Coordinate the calculate next monthly run logic in the service layer.

    Args:
        day_of_month: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        from_date: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    base = from_date or datetime.now().date()

    target_day = clamp_day(base.year, base.month, day_of_month)
    target = date(base.year, base.month, target_day)

    if target >= base:
        return target.strftime("%Y-%m-%d")

    if base.month == 12:
        next_year = base.year + 1
        next_month = 1
    # Use the fallback path when no earlier branch matched.
    else:
        next_year = base.year
        next_month = base.month + 1

    next_day = clamp_day(next_year, next_month, day_of_month)
    next_target = date(next_year, next_month, next_day)

    return next_target.strftime("%Y-%m-%d")


# Helper for calculate next run after execution.
def calculate_next_run_after_execution(rule: dict, run_date: date | None = None) -> str:
    """Calculate derived values for next run after execution."""
    frequency = normalize_frequency(rule.get("frequency"))
    day_of_month = normalize_day_of_month(rule.get("day_of_month"))

    base = run_date or datetime.now().date()

    if frequency == "monthly":
        if base.month == 12:
            next_year = base.year + 1
            next_month = 1
        # Use the fallback path when no earlier branch matched.
        else:
            next_year = base.year
            next_month = base.month + 1

        next_day = clamp_day(next_year, next_month, day_of_month)
        return date(next_year, next_month, next_day).strftime("%Y-%m-%d")

    raise ValueError("Frequency belum didukung.")


# Helper for build recurring row.
def build_recurring_row(rule: dict) -> list:
    """Build the data structure or message text for recurring row."""
    return [rule.get(col, "") for col in RECURRING_RULE_COLUMNS]


# Helper for build recurring log row.
def build_recurring_log_row(log: dict) -> list:
    """Build the data structure or message text for recurring log row."""
    return [log.get(col, "") for col in RECURRING_LOG_COLUMNS]


# Helper for add recurring rule.
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
    """Coordinate the add recurring rule logic in the service layer.

    Args:
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        txn_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        amount: Numeric amount or amount-like user input to parse or format.
        category: Category name or category-like value from user input or sheet data.
        account: Account name or account-like value from user input or sheet data.
        frequency: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        day_of_month: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        description: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        subject: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        catatan: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        tipe_pengeluaran: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        to_account: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    txn_type = str(txn_type or "").strip().lower()

    if txn_type not in ["expense", "income"]:
        raise ValueError("Type recurring hanya support expense atau income.")

    frequency = normalize_frequency(frequency)
    day_of_month = normalize_day_of_month(day_of_month)

    # Extract amount for validation.
    amount = parse_recurring_amount_value(amount)

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


# Helper for get recurring rules.
def get_recurring_rules(active_only: bool = False) -> list[dict]:
    """Retrieve data needed by the get recurring rules workflow in the service layer.

    Args:
        active_only: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Load records for the current calculation.
    records = get_all_records(SHEET_RECURRING_RULES)

    # Validate missing active only before continuing.
    if not active_only:
        return records

    return [
        r for r in records
        if str(r.get("is_active", "")).strip().upper() == "TRUE"
    ]


# Helper for get due recurring rules.
def get_due_recurring_rules(target_date: date | None = None) -> list[dict]:
    """Retrieve data needed by the get due recurring rules workflow in the service layer.

    Args:
        target_date: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    target = target_date or datetime.now().date()
    active_rules = get_recurring_rules(active_only=True)

    due_rules = []

    # Iterate through each rule.
    for rule in active_rules:
        next_run = parse_date(rule.get("next_run_date"))

        # Validate missing next run before continuing.
        if not next_run:
            # Skip the rest of this loop iteration after handling this case.
            continue

        if next_run <= target:
            # Append the current value to due rules.
            due_rules.append(rule)

    return due_rules


# Helper for find recurring rule row index.
def find_recurring_rule_row_index(rule_id: str) -> int | None:
    """Find a record for recurring rule row index."""
    # Load records for the current calculation.
    records = get_all_records(SHEET_RECURRING_RULES)

    # Iterate through each idx, record.
    for idx, record in enumerate(records, start=2):
        if str(record.get("id", "")).strip() == str(rule_id).strip():
            return idx

    return None


# Helper for update recurring rule cells.
def update_recurring_rule_cells(rule_id: str, updates: dict) -> bool:
    """Apply the update recurring rule cells operation in the service layer.

    Args:
        rule_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        updates: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    row_index = find_recurring_rule_row_index(rule_id)

    # Validate missing row index before continuing.
    if not row_index:
        return False

    # Iterate through each field, value.
    for field, value in updates.items():
        if field not in RECURRING_RULE_COLUMNS:
            # Skip the rest of this loop iteration after handling this case.
            continue

        col_index = RECURRING_RULE_COLUMNS.index(field) + 1
        update_cell(SHEET_RECURRING_RULES, row_index, col_index, value)

    return True


# Helper for disable recurring rule.
def disable_recurring_rule(rule_id: str) -> bool:
    """Coordinate the disable recurring rule logic in the service layer.

    Args:
        rule_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return update_recurring_rule_cells(
        rule_id,
        {
            "is_active": "FALSE",
            "updated_at": now_str(),
        },
    )

# Helper for get recurring rule by id.
def get_recurring_rule_by_id(rule_id: str) -> dict | None:
    """Retrieve data needed by the get recurring rule by id workflow in the service layer.

    Args:
        rule_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Load records for the current calculation.
    records = get_all_records(SHEET_RECURRING_RULES)

    # Iterate through each record.
    for record in records:
        if str(record.get("id", "")).strip() == str(rule_id).strip():
            return record

    return None


# Helper for normalize recurring edit field.
def normalize_recurring_edit_field(field: str) -> str | None:
    """Normalize input values for the normalize recurring edit field workflow in the service layer.

    Args:
        field: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
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


# Helper for normalize recurring edit value.
def normalize_recurring_edit_value(field: str, value):
    """Normalize input values for the normalize recurring edit value workflow in the service layer.

    Args:
        field: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        value: Raw value supplied by the caller.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    value = str(value or "").strip()

    if field == "type":
        # Normalize clean before matching.
        clean = value.lower()
        if clean not in ["expense", "income"]:
            raise ValueError("Type hanya boleh `expense` atau `income`.")
        return clean

    if field == "amount":
        amount = parse_recurring_amount_value(value)

        if amount <= 0:
            raise ValueError("Amount harus lebih dari 0. Contoh: `75000`, `300k`, atau `1.5 juta`.")

        return amount

    if field == "frequency":
        return normalize_frequency(value)

    if field == "day_of_month":
        return normalize_day_of_month(value)

    if field == "next_run_date":
        parsed = parse_date(value)
        # Validate missing parsed before continuing.
        if not parsed:
            raise ValueError("next_run_date harus format YYYY-MM-DD. Contoh: `2026-06-11`.")
        return parsed.strftime("%Y-%m-%d")

    if field == "is_active":
        # Normalize clean before matching.
        clean = value.lower()
        if clean in ["true", "1", "yes", "ya", "aktif", "on"]:
            return "TRUE"
        if clean in ["false", "0", "no", "tidak", "nonaktif", "off"]:
            return "FALSE"
        raise ValueError("is_active hanya boleh TRUE/FALSE atau on/off.")

    return value


# Helper for edit recurring rule.
def edit_recurring_rule(rule_id: str, updates: dict) -> dict:
    """Coordinate the edit recurring rule logic in the service layer.

    Args:
        rule_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        updates: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    rule = get_recurring_rule_by_id(rule_id)

    # Validate missing rule before continuing.
    if not rule:
        return {
            "success": False,
            "rule_before": {},
            "rule_after": {},
            "updates": {},
            "message": "Recurring rule tidak ditemukan.",
        }

    # Normalize normalized updates before matching.
    normalized_updates = {}

    # Iterate through each raw field, raw value.
    for raw_field, raw_value in updates.items():
        field = normalize_recurring_edit_field(raw_field)

        # Validate missing field before continuing.
        if not field:
            raise ValueError(f"Field `{raw_field}` tidak dikenali.")

        if field not in RECURRING_RULE_COLUMNS:
            raise ValueError(f"Field `{raw_field}` tidak bisa diedit.")

        if field in ["id", "created_at", "updated_at"]:
            raise ValueError(f"Field `{field}` tidak boleh diedit.")

        normalized_updates[field] = normalize_recurring_edit_value(field, raw_value)

    # Validate missing normalized updates before continuing.
    if not normalized_updates:
        raise ValueError("Tidak ada field yang diedit.")

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    if (
        ("day_of_month" in normalized_updates or "frequency" in normalized_updates)
        and "next_run_date" not in normalized_updates
    ):
        merged_rule = dict(rule)
        # Append the current value to merged rule.
        merged_rule.update(normalized_updates)

        frequency = normalize_frequency(merged_rule.get("frequency"))
        day_of_month = normalize_day_of_month(merged_rule.get("day_of_month"))

        if frequency == "monthly":
            normalized_updates["next_run_date"] = calculate_next_monthly_run(day_of_month)

    normalized_updates["updated_at"] = now_str()

    success = update_recurring_rule_cells(rule_id, normalized_updates)

    # Validate missing success before continuing.
    if not success:
        return {
            "success": False,
            "rule_before": rule,
            "rule_after": {},
            "updates": normalized_updates,
            "message": "Gagal update recurring rule.",
        }

    # Extract updated rule for validation.
    updated_rule = get_recurring_rule_by_id(rule_id) or {}

    return {
        "success": True,
        "rule_before": rule,
        "rule_after": updated_rule,
        "updates": normalized_updates,
        "message": "Recurring rule berhasil diupdate.",
    }

# Helper for log recurring run.
def log_recurring_run(
    rule_id: str,
    transaction_id: str | None,
    run_date: str,
    status: str,
    message: str,
):
    """Coordinate the log recurring run logic in the service layer.

    Args:
        rule_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        transaction_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        run_date: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        status: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        message: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
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


# Helper for build transaction from recurring rule.
def build_transaction_from_recurring_rule(rule: dict, run_date: str | None = None) -> dict:
    """Build the data structure or message text for transaction from recurring rule."""
    # Extract txn date for validation.
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



# Helper for mark recurring rule paid.
def mark_recurring_rule_paid(
    rule_id: str,
    run_date: date | None = None,
    *,
    scheduled_run_date: date | None = None,
) -> dict:
    """Coordinate the mark recurring rule paid logic in the service layer.

    Args:
        rule_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        run_date: Actual transaction date. Defaults to today.
        scheduled_run_date: Due date embedded in the reminder or selected by
            the scheduler. It forms the logical idempotency key with rule ID.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    rule = get_recurring_rule_by_id(rule_id)
    # Validate missing rule before continuing.
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
    current_due = parse_date(rule.get("next_run_date"))
    requested_due = scheduled_run_date or current_due
    if not current_due or not requested_due:
        return {
            "success": False,
            "message": "Tanggal jatuh tempo recurring tidak valid.",
            "transaction_id": None,
            "next_run_date": rule.get("next_run_date"),
            "rule": rule,
        }
    if requested_due != current_due:
        return {
            "success": False,
            "message": "Reminder recurring ini sudah kedaluwarsa karena occurrence aktif sudah berubah.",
            "transaction_id": None,
            "next_run_date": rule.get("next_run_date"),
            "rule": rule,
            "stale": True,
        }
    if current_due > target:
        return {
            "success": False,
            "message": "Recurring rule belum jatuh tempo.",
            "transaction_id": None,
            "next_run_date": rule.get("next_run_date"),
            "rule": rule,
            "not_due": True,
        }

    scheduled_date_str = current_due.strftime("%Y-%m-%d")
    transaction_date_str = target.strftime("%Y-%m-%d")
    occurrence_key = recurring_occurrence_key(rule_id, scheduled_date_str)

    with _recurring_run_lock:
        existing = find_processed_recurring_run(rule_id, scheduled_date_str)
        if existing or occurrence_key in _recurring_inflight:
            return {
                "success": True,
                "message": "Occurrence recurring ini sudah diproses.",
                "transaction_id": (existing or {}).get("transaction_id"),
                "next_run_date": rule.get("next_run_date"),
                "rule": rule,
                "duplicate": True,
                "logical_run_id": occurrence_key,
            }
        _recurring_inflight.add(occurrence_key)

        try:
            with sheets_transaction(label=f"recurring:{occurrence_key}"):
                existing = find_processed_recurring_run(rule_id, scheduled_date_str)
                if existing:
                    return {
                        "success": True,
                        "message": "Occurrence recurring ini sudah diproses.",
                        "transaction_id": existing.get("transaction_id"),
                        "next_run_date": rule.get("next_run_date"),
                        "rule": rule,
                        "duplicate": True,
                        "logical_run_id": occurrence_key,
                    }

                parsed_txn = build_transaction_from_recurring_rule(rule, run_date=transaction_date_str)
                transaction_result = save_transaction(
                    parsed_txn,
                    raw_input=parsed_txn.get("raw_input") or f"recurring:{rule_id}",
                )
                if not transaction_result.get("success"):
                    raise RuntimeError(transaction_result.get("message", "Gagal membuat transaksi recurring."))

                transaction_id = transaction_result.get("transaction_id")
                next_run_date = calculate_next_run_after_execution(rule, target)
                if not update_recurring_rule_cells(
                    rule_id,
                    {"next_run_date": next_run_date, "updated_at": now_str()},
                ):
                    raise RuntimeError("Gagal memperbarui next_run_date recurring.")

                log = log_recurring_run(
                    rule_id=rule_id,
                    transaction_id=transaction_id,
                    run_date=scheduled_date_str,
                    status="paid",
                    message=f"Recurring marked paid. Next run: {next_run_date}",
                )
                if not log:
                    raise RuntimeError("Gagal mencatat recurring log.")

                return {
                    "success": True,
                    "message": "ok",
                    "transaction_id": transaction_id,
                    "next_run_date": next_run_date,
                    "rule": rule,
                    "new_balance": transaction_result.get("new_balance"),
                    "new_balance_account": transaction_result.get("new_balance_account"),
                    "new_balances": transaction_result.get("new_balances", {}),
                    "amount": parsed_txn.get("amount"),
                    "account": parsed_txn.get("account"),
                    "to_account": parsed_txn.get("to_account"),
                    "type": parsed_txn.get("type"),
                    "duplicate": False,
                    "logical_run_id": occurrence_key,
                }
        except Exception as e:
            rollback_ok = rollback_current_sheets_transaction()
            return {
                "success": False,
                "message": str(e),
                "transaction_id": None,
                "next_run_date": rule.get("next_run_date"),
                "rule": rule,
                "commit_status": "rolled_back" if rollback_ok else "reconciliation_required",
                "reconciliation_required": not rollback_ok,
                "logical_run_id": occurrence_key,
            }
        finally:
            _recurring_inflight.discard(occurrence_key)


# Helper for process due recurring rules.
def process_due_recurring_rules(target_date: date | None = None) -> dict:
    """Coordinate the process due recurring rules logic in the service layer.

    Args:
        target_date: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    target = target_date or datetime.now().date()
    run_date = target.strftime("%Y-%m-%d")

    due_rules = get_due_recurring_rules(target)

    results = {
        "run_date": run_date,
        "count_due": len(due_rules),
        "success": [],
        "failed": [],
    }

    # Iterate through each rule.
    for rule in due_rules:
        rule_id = str(rule.get("id", "")).strip()

        # Run this operation in a guarded block so failures can be handled.
        try:
            scheduled = parse_date(rule.get("next_run_date"))
            result = mark_recurring_rule_paid(
                rule_id,
                run_date=target,
                scheduled_run_date=scheduled,
            )
            if not result.get("success"):
                raise RuntimeError(result.get("message", "Gagal membuat transaksi recurring."))

            transaction_id = result.get("transaction_id")
            next_run_date = result.get("next_run_date")

            results["success"].append(
                {
                    "rule": rule,
                    "transaction_id": transaction_id,
                    "next_run_date": next_run_date,
                }
            )

        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            rollback_current_sheets_transaction()
            message = str(e)

            # Recurring command note: this handles repeated bills or scheduled transactions.
            results["success"] = []
            results["failed"].append(
                {
                    "rule": rule,
                    "message": message,
                }
            )
            # Leave the loop after the target condition has been reached.
            break

    return results

