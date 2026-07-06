"""Recurring transaction service for rules, due dates, logs, and generated transactions."""


# Import calendar for this module's local operations.
import calendar
# Import uuid for this module's local operations.
import uuid
# Import datetime so this module can use its helpers.
from datetime import datetime, date

# Import app.config so this module can use its helpers.
from app.config import SHEET_RECURRING_RULES, SHEET_RECURRING_LOGS
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import append_row, get_all_records, update_cell, rollback_current_sheets_transaction, sheets_transaction
# Import app.services.transaction_service so this module can use its helpers.
from app.services.transaction_service import save_transaction


# Open a multi-line structure for the values below.
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
# Close the structure that was opened above.
]


# Open a multi-line structure for the values below.
RECURRING_LOG_COLUMNS = [
    "id",
    "rule_id",
    "transaction_id",
    "run_date",
    "status",
    "message",
    "created_at",
# Close the structure that was opened above.
]


# Define now str for callers in this flow.
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


# Define today str for callers in this flow.
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


# Define generate recurring id for callers in this flow.
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
    # Prepare suffix for the next step.
    suffix = uuid.uuid4().hex[:6]
    return f"rec_{timestamp}_{suffix}"


# Define generate recurring log id for callers in this flow.
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
    # Prepare suffix for the next step.
    suffix = uuid.uuid4().hex[:6]
    return f"reclog_{timestamp}_{suffix}"


# Define parse date for callers in this flow.
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
        # Return None to the caller.
        return None


# Define safe float for callers in this flow.
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
        # Return float(value or 0) to the caller.
        return float(value or 0)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return 0.0 to the caller.
        return 0.0


# Define normalize day of month for callers in this flow.
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
        # Prepare day int for the next step.
        day_int = int(day)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        raise ValueError("Tanggal recurring harus berupa angka 1-31.")

    # Handle the case where day_int < 1 or day_int > 31.
    if day_int < 1 or day_int > 31:
        raise ValueError("Tanggal recurring harus di antara 1 sampai 31.")

    # Return day_int to the caller.
    return day_int


# Define normalize frequency for callers in this flow.
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

    # Open a multi-line structure for the values below.
    aliases = {
        "monthly": "monthly",
        "bulan": "monthly",
        "bulanan": "monthly",
        "setiap bulan": "monthly",
    # Close the structure that was opened above.
    }

    # Prepare frequency for the next step.
    frequency = aliases.get(clean)

    # Handle the missing or empty frequency case.
    if not frequency:
        raise ValueError("Frequency belum valid. Saat ini baru support: monthly.")

    # Return frequency to the caller.
    return frequency


# Define get last day of month for callers in this flow.
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
    # Return calendar.monthrange(year, month)[1] to the caller.
    return calendar.monthrange(year, month)[1]


# Define clamp day for callers in this flow.
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
    # Prepare last day for the next step.
    last_day = get_last_day_of_month(year, month)
    # Return min(day, last_day) to the caller.
    return min(day, last_day)


# Define calculate next monthly run for callers in this flow.
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
    # Prepare base for the next step.
    base = from_date or datetime.now().date()

    # Prepare target day for the next step.
    target_day = clamp_day(base.year, base.month, day_of_month)
    # Prepare target for the next step.
    target = date(base.year, base.month, target_day)

    # Handle the case where target >= base.
    if target >= base:
        return target.strftime("%Y-%m-%d")

    # Handle the case where base.month == 12.
    if base.month == 12:
        # Prepare next year for the next step.
        next_year = base.year + 1
        # Prepare next month for the next step.
        next_month = 1
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare next year for the next step.
        next_year = base.year
        # Prepare next month for the next step.
        next_month = base.month + 1

    # Prepare next day for the next step.
    next_day = clamp_day(next_year, next_month, day_of_month)
    # Prepare next target for the next step.
    next_target = date(next_year, next_month, next_day)

    return next_target.strftime("%Y-%m-%d")


# Define calculate next run after execution for callers in this flow.
def calculate_next_run_after_execution(rule: dict, run_date: date | None = None) -> str:
    """Calculate derived values for next run after execution."""
    frequency = normalize_frequency(rule.get("frequency"))
    day_of_month = normalize_day_of_month(rule.get("day_of_month"))

    # Prepare base for the next step.
    base = run_date or datetime.now().date()

    if frequency == "monthly":
        # Handle the case where base.month == 12.
        if base.month == 12:
            # Prepare next year for the next step.
            next_year = base.year + 1
            # Prepare next month for the next step.
            next_month = 1
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Prepare next year for the next step.
            next_year = base.year
            # Prepare next month for the next step.
            next_month = base.month + 1

        # Prepare next day for the next step.
        next_day = clamp_day(next_year, next_month, day_of_month)
        return date(next_year, next_month, next_day).strftime("%Y-%m-%d")

    raise ValueError("Frequency belum didukung.")


# Define build recurring row for callers in this flow.
def build_recurring_row(rule: dict) -> list:
    """Build the data structure or message text for recurring row."""
    return [rule.get(col, "") for col in RECURRING_RULE_COLUMNS]


# Define build recurring log row for callers in this flow.
def build_recurring_log_row(log: dict) -> list:
    """Build the data structure or message text for recurring log row."""
    return [log.get(col, "") for col in RECURRING_LOG_COLUMNS]


# Define add recurring rule for callers in this flow.
def add_recurring_rule(
    # Include this value in the surrounding collection or call.
    name: str,
    # Include this value in the surrounding collection or call.
    txn_type: str,
    # Include this value in the surrounding collection or call.
    amount: float,
    # Include this value in the surrounding collection or call.
    category: str,
    # Include this value in the surrounding collection or call.
    account: str,
    # Include this value in the surrounding collection or call.
    frequency: str,
    # Include this value in the surrounding collection or call.
    day_of_month: int,
    # Include this value in the surrounding collection or call.
    description: str | None = None,
    # Include this value in the surrounding collection or call.
    subject: str | None = None,
    # Include this value in the surrounding collection or call.
    catatan: str | None = None,
    # Include this value in the surrounding collection or call.
    tipe_pengeluaran: str | None = None,
    # Include this value in the surrounding collection or call.
    to_account: str | None = None,
# Close the structure that was opened above.
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

    # Prepare frequency for the next step.
    frequency = normalize_frequency(frequency)
    # Prepare day of month for the next step.
    day_of_month = normalize_day_of_month(day_of_month)

    # Prepare amount for the next step.
    amount = safe_float(amount)

    # Handle the case where amount <= 0.
    if amount <= 0:
        raise ValueError("Amount recurring harus lebih dari 0.")

    # Prepare created at for the next step.
    created_at = now_str()

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    }

    # Run this statement as part of the current workflow.
    append_row(SHEET_RECURRING_RULES, build_recurring_row(rule))

    # Return rule to the caller.
    return rule


# Define get recurring rules for callers in this flow.
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
    # Prepare records for the next step.
    records = get_all_records(SHEET_RECURRING_RULES)

    # Handle the missing or empty active_only case.
    if not active_only:
        # Return records to the caller.
        return records

    # Return [ to the caller.
    return [
        # Run this statement as part of the current workflow.
        r for r in records
        if str(r.get("is_active", "")).strip().upper() == "TRUE"
    # Close the structure that was opened above.
    ]


# Define get due recurring rules for callers in this flow.
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
    # Prepare target for the next step.
    target = target_date or datetime.now().date()
    # Prepare active rules for the next step.
    active_rules = get_recurring_rules(active_only=True)

    # Prepare due rules for the next step.
    due_rules = []

    # Process each rule in the current collection.
    for rule in active_rules:
        next_run = parse_date(rule.get("next_run_date"))

        # Handle the missing or empty next_run case.
        if not next_run:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Handle the case where next_run <= target.
        if next_run <= target:
            # Update due rules with the current value.
            due_rules.append(rule)

    # Return due_rules to the caller.
    return due_rules


# Define find recurring rule row index for callers in this flow.
def find_recurring_rule_row_index(rule_id: str) -> int | None:
    """Find a record for recurring rule row index."""
    # Prepare records for the next step.
    records = get_all_records(SHEET_RECURRING_RULES)

    # Process each idx, record in the current collection.
    for idx, record in enumerate(records, start=2):
        if str(record.get("id", "")).strip() == str(rule_id).strip():
            # Return idx to the caller.
            return idx

    # Return None to the caller.
    return None


# Define update recurring rule cells for callers in this flow.
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
    # Prepare row index for the next step.
    row_index = find_recurring_rule_row_index(rule_id)

    # Handle the missing or empty row_index case.
    if not row_index:
        # Return False to the caller.
        return False

    # Process each field, value in the current collection.
    for field, value in updates.items():
        # Handle the case where field not in RECURRING_RULE_COLUMNS.
        if field not in RECURRING_RULE_COLUMNS:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Prepare col index for the next step.
        col_index = RECURRING_RULE_COLUMNS.index(field) + 1
        # Run this statement as part of the current workflow.
        update_cell(SHEET_RECURRING_RULES, row_index, col_index, value)

    # Return True to the caller.
    return True


# Define disable recurring rule for callers in this flow.
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
    # Return update_recurring_rule_cells( to the caller.
    return update_recurring_rule_cells(
        # Include this value in the surrounding collection or call.
        rule_id,
        # Open a multi-line structure for the values below.
        {
            "is_active": "FALSE",
            "updated_at": now_str(),
        # Close the structure that was opened above.
        },
    # Close the structure that was opened above.
    )

# Define get recurring rule by id for callers in this flow.
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
    # Prepare records for the next step.
    records = get_all_records(SHEET_RECURRING_RULES)

    # Process each record in the current collection.
    for record in records:
        if str(record.get("id", "")).strip() == str(rule_id).strip():
            # Return record to the caller.
            return record

    # Return None to the caller.
    return None


# Define normalize recurring edit field for callers in this flow.
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

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    }

    # Return aliases.get(key) to the caller.
    return aliases.get(key)


# Define normalize recurring edit value for callers in this flow.
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
        # Prepare clean for the next step.
        clean = value.lower()
        if clean not in ["expense", "income"]:
            raise ValueError("Type hanya boleh `expense` atau `income`.")
        # Return clean to the caller.
        return clean

    if field == "amount":
        clean = value.replace(".", "").replace(",", "")
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare amount for the next step.
            amount = float(clean)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            raise ValueError("Amount harus angka. Contoh: `75000`.")

        # Handle the case where amount <= 0.
        if amount <= 0:
            raise ValueError("Amount harus lebih dari 0.")

        # Return amount to the caller.
        return amount

    if field == "frequency":
        # Return normalize_frequency(value) to the caller.
        return normalize_frequency(value)

    if field == "day_of_month":
        # Return normalize_day_of_month(value) to the caller.
        return normalize_day_of_month(value)

    if field == "next_run_date":
        # Prepare parsed for the next step.
        parsed = parse_date(value)
        # Handle the missing or empty parsed case.
        if not parsed:
            raise ValueError("next_run_date harus format YYYY-MM-DD. Contoh: `2026-06-11`.")
        return parsed.strftime("%Y-%m-%d")

    if field == "is_active":
        # Prepare clean for the next step.
        clean = value.lower()
        if clean in ["true", "1", "yes", "ya", "aktif", "on"]:
            return "TRUE"
        if clean in ["false", "0", "no", "tidak", "nonaktif", "off"]:
            return "FALSE"
        raise ValueError("is_active hanya boleh TRUE/FALSE atau on/off.")

    # Return value to the caller.
    return value


# Define edit recurring rule for callers in this flow.
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
    # Prepare rule for the next step.
    rule = get_recurring_rule_by_id(rule_id)

    # Handle the missing or empty rule case.
    if not rule:
        # Return { to the caller.
        return {
            "success": False,
            "rule_before": {},
            "rule_after": {},
            "updates": {},
            "message": "Recurring rule tidak ditemukan.",
        # Close the structure that was opened above.
        }

    # Prepare normalized updates for the next step.
    normalized_updates = {}

    # Process each raw_field, raw_value in the current collection.
    for raw_field, raw_value in updates.items():
        # Prepare field for the next step.
        field = normalize_recurring_edit_field(raw_field)

        # Handle the missing or empty field case.
        if not field:
            raise ValueError(f"Field `{raw_field}` tidak dikenali.")

        # Handle the case where field not in RECURRING_RULE_COLUMNS.
        if field not in RECURRING_RULE_COLUMNS:
            raise ValueError(f"Field `{raw_field}` tidak bisa diedit.")

        if field in ["id", "created_at", "updated_at"]:
            raise ValueError(f"Field `{field}` tidak boleh diedit.")

        # Run this statement as part of the current workflow.
        normalized_updates[field] = normalize_recurring_edit_value(field, raw_value)

    # Handle the missing or empty normalized_updates case.
    if not normalized_updates:
        raise ValueError("Tidak ada field yang diedit.")

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    if (
        ("day_of_month" in normalized_updates or "frequency" in normalized_updates)
        and "next_run_date" not in normalized_updates
    # Close the structure that was opened above.
    ):
        # Prepare merged rule for the next step.
        merged_rule = dict(rule)
        # Update merged rule with the current value.
        merged_rule.update(normalized_updates)

        frequency = normalize_frequency(merged_rule.get("frequency"))
        day_of_month = normalize_day_of_month(merged_rule.get("day_of_month"))

        if frequency == "monthly":
            normalized_updates["next_run_date"] = calculate_next_monthly_run(day_of_month)

    normalized_updates["updated_at"] = now_str()

    # Prepare success for the next step.
    success = update_recurring_rule_cells(rule_id, normalized_updates)

    # Handle the missing or empty success case.
    if not success:
        # Return { to the caller.
        return {
            "success": False,
            "rule_before": rule,
            "rule_after": {},
            "updates": normalized_updates,
            "message": "Gagal update recurring rule.",
        # Close the structure that was opened above.
        }

    # Prepare updated rule for the next step.
    updated_rule = get_recurring_rule_by_id(rule_id) or {}

    # Return { to the caller.
    return {
        "success": True,
        "rule_before": rule,
        "rule_after": updated_rule,
        "updates": normalized_updates,
        "message": "Recurring rule berhasil diupdate.",
    # Close the structure that was opened above.
    }

# Define log recurring run for callers in this flow.
def log_recurring_run(
    # Include this value in the surrounding collection or call.
    rule_id: str,
    # Include this value in the surrounding collection or call.
    transaction_id: str | None,
    # Include this value in the surrounding collection or call.
    run_date: str,
    # Include this value in the surrounding collection or call.
    status: str,
    # Include this value in the surrounding collection or call.
    message: str,
# Close the structure that was opened above.
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
    # Open a multi-line structure for the values below.
    log = {
        "id": generate_recurring_log_id(),
        "rule_id": rule_id,
        "transaction_id": transaction_id or "",
        "run_date": run_date,
        "status": status,
        "message": message,
        "created_at": now_str(),
    # Close the structure that was opened above.
    }

    # Run this statement as part of the current workflow.
    append_row(SHEET_RECURRING_LOGS, build_recurring_log_row(log))

    # Return log to the caller.
    return log


# Define build transaction from recurring rule for callers in this flow.
def build_transaction_from_recurring_rule(rule: dict, run_date: str | None = None) -> dict:
    """Build the data structure or message text for transaction from recurring rule."""
    # Prepare txn date for the next step.
    txn_date = run_date or today_str()

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }



# Define mark recurring rule paid for callers in this flow.
def mark_recurring_rule_paid(rule_id: str, run_date: date | None = None) -> dict:
    """Coordinate the mark recurring rule paid logic in the service layer.

    Args:
        rule_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        run_date: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare rule for the next step.
    rule = get_recurring_rule_by_id(rule_id)
    # Handle the missing or empty rule case.
    if not rule:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Recurring rule tidak ditemukan.",
            "transaction_id": None,
            "next_run_date": None,
            "rule": None,
        # Close the structure that was opened above.
        }

    if str(rule.get("is_active", "")).strip().upper() != "TRUE":
        # Return { to the caller.
        return {
            "success": False,
            "message": "Recurring rule sudah nonaktif.",
            "transaction_id": None,
            "next_run_date": rule.get("next_run_date"),
            "rule": rule,
        # Close the structure that was opened above.
        }

    # Prepare target for the next step.
    target = run_date or datetime.now().date()
    run_date_str = target.strftime("%Y-%m-%d")

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare parsed txn for the next step.
        parsed_txn = build_transaction_from_recurring_rule(rule, run_date=run_date_str)
        # Open a multi-line structure for the values below.
        transaction_result = save_transaction(
            # Include this value in the surrounding collection or call.
            parsed_txn,
            raw_input=parsed_txn.get("raw_input") or f"recurring:{rule_id}",
        # Close the structure that was opened above.
        )

        if not transaction_result.get("success"):
            raise RuntimeError(transaction_result.get("message", "Gagal membuat transaksi recurring."))

        transaction_id = transaction_result.get("transaction_id")
        # Prepare next run date for the next step.
        next_run_date = calculate_next_run_after_execution(rule, target)

        # Open a multi-line structure for the values below.
        update_recurring_rule_cells(
            # Include this value in the surrounding collection or call.
            rule_id,
            # Open a multi-line structure for the values below.
            {
                "next_run_date": next_run_date,
                "updated_at": now_str(),
            # Close the structure that was opened above.
            },
        # Close the structure that was opened above.
        )

        # Open a multi-line structure for the values below.
        log_recurring_run(
            # Prepare rule id for the next step.
            rule_id=rule_id,
            # Prepare transaction id for the next step.
            transaction_id=transaction_id,
            # Prepare run date for the next step.
            run_date=run_date_str,
            status="paid",
            message=f"Recurring marked paid. Next run: {next_run_date}",
        # Close the structure that was opened above.
        )

        # Return { to the caller.
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
        # Close the structure that was opened above.
        }
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Run this statement as part of the current workflow.
        rollback_current_sheets_transaction()
        # Return { to the caller.
        return {
            "success": False,
            "message": str(e),
            "transaction_id": None,
            "next_run_date": rule.get("next_run_date"),
            "rule": rule,
        # Close the structure that was opened above.
        }


# Define process due recurring rules for callers in this flow.
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
    # Prepare target for the next step.
    target = target_date or datetime.now().date()
    run_date = target.strftime("%Y-%m-%d")

    # Prepare due rules for the next step.
    due_rules = get_due_recurring_rules(target)

    # Open a multi-line structure for the values below.
    results = {
        "run_date": run_date,
        "count_due": len(due_rules),
        "success": [],
        "failed": [],
    # Close the structure that was opened above.
    }

    # Process each rule in the current collection.
    for rule in due_rules:
        rule_id = str(rule.get("id", "")).strip()

        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare parsed txn for the next step.
            parsed_txn = build_transaction_from_recurring_rule(rule, run_date=run_date)
            # Open a multi-line structure for the values below.
            transaction_result = save_transaction(
                # Include this value in the surrounding collection or call.
                parsed_txn,
                raw_input=parsed_txn.get("raw_input") or f"recurring:{rule_id}",
            # Close the structure that was opened above.
            )

            if not transaction_result.get("success"):
                raise RuntimeError(transaction_result.get("message", "Gagal membuat transaksi recurring."))

            transaction_id = transaction_result.get("transaction_id")

            # Prepare next run date for the next step.
            next_run_date = calculate_next_run_after_execution(rule, target)

            # Open a multi-line structure for the values below.
            update_recurring_rule_cells(
                # Include this value in the surrounding collection or call.
                rule_id,
                # Open a multi-line structure for the values below.
                {
                    "next_run_date": next_run_date,
                    "updated_at": now_str(),
                # Close the structure that was opened above.
                },
            # Close the structure that was opened above.
            )

            # Open a multi-line structure for the values below.
            log_recurring_run(
                # Prepare rule id for the next step.
                rule_id=rule_id,
                # Prepare transaction id for the next step.
                transaction_id=transaction_id,
                # Prepare run date for the next step.
                run_date=run_date,
                status="success",
                message=f"Recurring transaction created. Next run: {next_run_date}",
            # Close the structure that was opened above.
            )

            results["success"].append(
                # Open a multi-line structure for the values below.
                {
                    "rule": rule,
                    "transaction_id": transaction_id,
                    "next_run_date": next_run_date,
                # Close the structure that was opened above.
                }
            # Close the structure that was opened above.
            )

        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            # Run this statement as part of the current workflow.
            rollback_current_sheets_transaction()
            # Prepare message for the next step.
            message = str(e)

            # Recurring command note: this handles repeated bills or scheduled transactions.
            # Debt flow section
            results["success"] = []
            results["failed"].append(
                # Open a multi-line structure for the values below.
                {
                    "rule": rule,
                    "message": message,
                # Close the structure that was opened above.
                }
            # Close the structure that was opened above.
            )
            # Leave the loop after the target condition has been reached.
            break

    # Return results to the caller.
    return results

