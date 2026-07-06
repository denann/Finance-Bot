"""Pending expense service for planned expenses or bills that should not immediately affect account balances."""


# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import calendar for this module's local operations.
import calendar
# Import re for this module's local operations.
import re
# Import uuid for this module's local operations.
import uuid
# Import datetime so this module can use its helpers.
from datetime import datetime, timedelta, date

# Import app.config so this module can use its helpers.
from app.config import SHEET_PENDING_EXPENSES
# Import app.nlp.normalizer so this module can use its helpers.
from app.nlp.normalizer import extract_amount_from_text
# Import app.nlp.regex_parser so this module can use its helpers.
from app.nlp.regex_parser import (
    # Include this value in the surrounding collection or call.
    ACCOUNT_DISPLAY_NAMES,
    # Include this value in the surrounding collection or call.
    ACCOUNT_NAMES,
    # Include this value in the surrounding collection or call.
    CATEGORY_KEYWORDS,
    # Include this value in the surrounding collection or call.
    extract_description,
    # Include this value in the surrounding collection or call.
    parse_explicit_date,
    # Include this value in the surrounding collection or call.
    parse_with_regex,
# Close the structure that was opened above.
)
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import append_row_raw, get_all_records, update_cell
# Import app.services.transaction_service so this module can use its helpers.
from app.services.transaction_service import save_transaction
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import get_account_names_from_sheet, resolve_account_for_parser


# Open a multi-line structure for the values below.
PENDING_EXPENSE_COLUMNS = [
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
# Close the structure that was opened above.
]

ACTIVE_STATUSES = {"pending", "planned", "confirmed"}
CLOSED_STATUSES = {"paid", "cancelled", "canceled", "void", "done"}

# Open a multi-line structure for the values below.
PENDING_INTENT_KEYWORDS = {
    "pending", "rencana", "planning", "plan", "nanti", "akan",
    "bakal", "perlu", "butuh", "kudu", "harus",
# Close the structure that was opened above.
}
# Open a multi-line structure for the values below.
DEBT_LIKE_KEYWORDS = {
    "hutang", "utang", "piutang", "minjem", "pinjem", "pinjam",
    "dipinjem", "dipinjam", "talangin", "ditalangin", "dibayarin",
# Close the structure that was opened above.
}
# Open a multi-line structure for the values below.
PAST_OR_ACTUAL_KEYWORDS = {
    "sudah", "udah", "sdh", "barusan", "tadi", "kemarin", "baru aja",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
MONTH_ALIASES_ID = {
    "januari": 1,
    "jan": 1,
    "februari": 2,
    "feb": 2,
    "maret": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "mei": 5,
    "may": 5,
    "juni": 6,
    "jun": 6,
    "juli": 7,
    "jul": 7,
    "agustus": 8,
    "agus": 8,
    "agt": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "oktober": 10,
    "okt": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "desember": 12,
    "des": 12,
    "dec": 12,
# Close the structure that was opened above.
}


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


# Define today for callers in this flow.
def today() -> date:
    """Coordinate the today logic in the service layer.

    Args:
        None.

    Returns:
        `date` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Return datetime.now().date() to the caller.
    return datetime.now().date()


# Define current month for callers in this flow.
def current_month() -> str:
    """Coordinate the current month logic in the service layer.

    Args:
        None.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return datetime.now().strftime("%Y-%m")


# Define format rupiah for callers in this flow.
def format_rupiah(amount: float) -> str:
    """Format data into a readable display for rupiah."""
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")


# Define safe float for callers in this flow.
def safe_float(value, default: float = 0.0) -> float:
    """Coordinate the safe float logic in the service layer.

    Args:
        value: Raw value supplied by the caller.
        default: Input value supplied by the caller; accepted shape follows the function signature and local validation.

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
        # Return default to the caller.
        return default


# Define generate pending id for callers in this flow.
def generate_pending_id() -> str:
    """Coordinate the generate pending id logic in the service layer.

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
    suffix = uuid.uuid4().hex[:8]
    return f"pend_{timestamp}_{suffix}"


# Define normalize month for callers in this flow.
def normalize_month(month: str | None = None) -> str:
    """Normalize input values for the normalize month workflow in the service layer.

    Args:
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Handle the missing or empty month case.
    if not month:
        # Return current_month() to the caller.
        return current_month()

    raw = str(month or "").strip().lower().replace("/", "-")
    raw = re.sub(r"\s+", " ", raw)

    if raw in {"bulan ini", "bulanini", "this month", "month", "sekarang"}:
        # Return current_month() to the caller.
        return current_month()
    if raw in {"bulan lalu", "bulanlalu", "last month"}:
        # Return add_months(current_month(), -1) to the caller.
        return add_months(current_month(), -1)
    if raw in {"bulan depan", "bulandepan", "next month"}:
        # Return add_months(current_month(), 1) to the caller.
        return add_months(current_month(), 1)

    match = re.fullmatch(r"(20\d{2})[-\s](0?[1-9]|1[0-2])", raw)
    # Handle the case where match.
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"

    # Juli 2026 / Jul 2026
    match = re.fullmatch(r"([a-zA-ZÀ-ÿ]+)\s+(20\d{2})", raw)
    # Handle the case where match.
    if match:
        # Prepare month num for the next step.
        month_num = MONTH_ALIASES_ID.get(match.group(1).lower())
        # Handle the case where month_num.
        if month_num:
            return f"{int(match.group(2)):04d}-{month_num:02d}"

    raise ValueError("Format bulan pending tidak dikenali. Gunakan YYYY-MM, bulan ini, bulan lalu, bulan depan, atau all.")


# Define add months for callers in this flow.
def add_months(month: str, delta: int) -> str:
    """Coordinate the add months logic in the service layer.

    Args:
        month: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        delta: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    year, month_num = map(int, month.split("-"))
    # Run this statement as part of the current workflow.
    month_num += delta
    # Repeat this block while month_num <= 0.
    while month_num <= 0:
        # Run this statement as part of the current workflow.
        month_num += 12
        # Run this statement as part of the current workflow.
        year -= 1
    # Repeat this block while month_num > 12.
    while month_num > 12:
        # Run this statement as part of the current workflow.
        month_num -= 12
        # Run this statement as part of the current workflow.
        year += 1
    return f"{year:04d}-{month_num:02d}"


# Define month last day for callers in this flow.
def month_last_day(year: int, month_num: int) -> int:
    """Coordinate the month last day logic in the service layer.

    Args:
        year: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        month_num: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `int` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Return calendar.monthrange(year, month_num)[1] to the caller.
    return calendar.monthrange(year, month_num)[1]


# Define parse day current or next month for callers in this flow.
def parse_day_current_or_next_month(day_raw: str) -> str | None:
    """Parse caller input for the parse day current or next month workflow in the service layer.

    Args:
        day_raw: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare day num for the next step.
        day_num = int(day_raw)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return None to the caller.
        return None
    # Handle the case where day_num < 1 or day_num > 31.
    if day_num < 1 or day_num > 31:
        # Return None to the caller.
        return None

    # Prepare base for the next step.
    base = today()
    # Prepare target day for the next step.
    target_day = min(day_num, month_last_day(base.year, base.month))
    # Prepare target for the next step.
    target = date(base.year, base.month, target_day)

    # Pending expense section
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    if target < base:
        next_month = add_months(base.strftime("%Y-%m"), 1)
        y, m = map(int, next_month.split("-"))
        # Prepare target day for the next step.
        target_day = min(day_num, month_last_day(y, m))
        # Prepare target for the next step.
        target = date(y, m, target_day)

    return target.strftime("%Y-%m-%d")


# Define parse month only from text for callers in this flow.
def parse_month_only_from_text(text: str) -> str | None:
    """Parse caller input for the parse month only from text workflow in the service layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    clean = str(text or "").strip().lower().replace("/", "-")

    if re.search(r"\bbulan\s+ini\b", clean):
        # Return current_month() to the caller.
        return current_month()
    if re.search(r"\bbulan\s+lalu\b", clean):
        # Return add_months(current_month(), -1) to the caller.
        return add_months(current_month(), -1)
    if re.search(r"\bbulan\s+depan\b", clean):
        # Return add_months(current_month(), 1) to the caller.
        return add_months(current_month(), 1)

    match = re.search(r"\b(20\d{2})[-\s](0?[1-9]|1[0-2])\b", clean)
    # Handle the case where match.
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"

    match = re.search(r"\b([a-zA-ZÀ-ÿ]+)\s+(20\d{2})\b", clean)
    # Handle the case where match.
    if match:
        # Prepare month num for the next step.
        month_num = MONTH_ALIASES_ID.get(match.group(1).lower())
        # Handle the case where month_num.
        if month_num:
            return f"{int(match.group(2)):04d}-{month_num:02d}"

    # Return None to the caller.
    return None


# Define detect pending due for callers in this flow.
def detect_pending_due(text: str) -> tuple[str, str, str]:
    """Coordinate the detect pending due logic in the service layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `tuple[str, str, str]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    clean = str(text or "").strip().lower().replace("/", "-")
    # Prepare base for the next step.
    base = today()

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    prefixed = re.search(
        r"\b(?:tanggal|tgl|tg|date|pada tanggal)\s+"
        r"(20\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])|"
        r"(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]20\d{2})\b",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where prefixed.
    if prefixed:
        # Prepare parsed for the next step.
        parsed = parse_explicit_date(prefixed.group(1))
        # Handle the case where parsed.
        if parsed:
            return parsed, parsed[:7], "exact"

    # Open a multi-line structure for the values below.
    bare = re.search(
        r"\b(20\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])|"
        r"(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]20\d{2})\b",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where bare.
    if bare:
        # Prepare parsed for the next step.
        parsed = parse_explicit_date(bare.group(1))
        # Handle the case where parsed.
        if parsed:
            return parsed, parsed[:7], "exact"

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    day_only = re.search(r"\b(?:tanggal|tgl|tg|date|pada tanggal)\s+(0?[1-9]|[12]\d|3[01])\b", clean)
    # Handle the case where day_only.
    if day_only:
        # Prepare parsed for the next step.
        parsed = parse_day_current_or_next_month(day_only.group(1))
        # Handle the case where parsed.
        if parsed:
            return parsed, parsed[:7], "exact"

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    if re.search(r"\bbesok\b", clean):
        # Prepare target for the next step.
        target = base + timedelta(days=1)
        return target.strftime("%Y-%m-%d"), target.strftime("%Y-%m"), "exact"
    if re.search(r"\blusa\b", clean):
        # Prepare target for the next step.
        target = base + timedelta(days=2)
        return target.strftime("%Y-%m-%d"), target.strftime("%Y-%m"), "exact"
    if re.search(r"\bminggu\s+depan\b|\bpekan\s+depan\b", clean):
        # Prepare target for the next step.
        target = base + timedelta(days=7)
        return target.strftime("%Y-%m-%d"), target.strftime("%Y-%m"), "exact"
    if re.search(r"\bakhir\s+bulan\b", clean):
        # Prepare target for the next step.
        target = date(base.year, base.month, month_last_day(base.year, base.month))
        return target.strftime("%Y-%m-%d"), target.strftime("%Y-%m"), "exact"

    # Prepare month only for the next step.
    month_only = parse_month_only_from_text(clean)
    # Handle the case where month_only.
    if month_only:
        return "", month_only, "month"

    return "", current_month(), "unknown"



# Define has past time marker for callers in this flow.
def has_past_time_marker(text: str) -> bool:
    """Evaluate the has past time marker condition in the service layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    clean = str(text or "").strip().lower().replace("/", "-")
    # Handle the missing or empty clean case.
    if not clean:
        # Return False to the caller.
        return False

    # Implementation section
    if re.search(
        r"\b(kemarin|tadi|barusan|baru aja|minggu lalu|pekan lalu|bulan lalu|tahun lalu)\b",
        # Include this value in the surrounding collection or call.
        clean,
    # Close the structure that was opened above.
    ):
        # Return True to the caller.
        return True

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    if re.search(
        r"\b(?:\d+|satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh)\s+"
        r"(?:hari|minggu|pekan|bulan|tahun)\s+(?:yang\s+)?lalu\b",
        # Include this value in the surrounding collection or call.
        clean,
    # Close the structure that was opened above.
    ):
        # Return True to the caller.
        return True

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    date_candidates = []
    # Process each match in the current collection.
    for match in re.finditer(
        r"\b(?:tanggal|tgl|tg|date|pada tanggal)?\s*"
        r"(20\d{2}[-](?:0?[1-9]|1[0-2])[-](?:0?[1-9]|[12]\d|3[01])|"
        r"(?:0?[1-9]|[12]\d|3[01])[-](?:0?[1-9]|1[0-2])[-]20\d{2})\b",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    ):
        # Update date candidates with the current value.
        date_candidates.append(match.group(1))

    # Process each candidate in the current collection.
    for candidate in date_candidates:
        # Prepare parsed for the next step.
        parsed = parse_explicit_date(candidate)
        # Handle the case where parsed.
        if parsed:
            # Run this operation in a guarded block so failures can be handled.
            try:
                parsed_date = datetime.strptime(parsed, "%Y-%m-%d").date()
                # Handle the case where parsed_date < today().
                if parsed_date < today():
                    # Return True to the caller.
                    return True
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Keep this intentionally empty block valid.
                pass

    # Return False to the caller.
    return False

# Define clean pending text for callers in this flow.
def clean_pending_text(text: str) -> str:
    """Coordinate the clean pending text logic in the service layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    clean = str(text or "").strip()
    clean = re.sub(r"^/(pending_add|pending|rencana)\b", "", clean, flags=re.IGNORECASE).strip()

    # Pending expense section
    # Implementation note for this project-specific finance flow.
    # - nanti perlu bayar wisuda 750k -> bayar wisuda 750k
    # - perlu 750k create bayar wisuda -> 750k create bayar wisuda
    # - bakal service motor 300k -> service motor 300k
    clean = re.sub(
        r"^(pengeluaran\s+)?(?:pending|rencana|planning|plan|nanti|akan|bakal|perlu|butuh|kudu|harus)\b",
        "",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    ).strip()
    # Open a multi-line structure for the values below.
    clean = re.sub(
        r"^(?:perlu|butuh|kudu|harus)\s+(?:bayar|beli|buat|untuk)\b",
        "",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    ).strip()
    # Return clean to the caller.
    return clean


# Define is pending expense text for callers in this flow.
def is_pending_expense_text(text: str) -> bool:
    """Check whether a condition is true for pending expense text."""
    raw = str(text or "").strip()
    if not raw or raw.startswith("/"):
        # Return False to the caller.
        return False

    clean = re.sub(r"\s+", " ", raw.lower()).strip()

    # Prepare amount for the next step.
    amount = extract_amount_from_text(clean)
    # Handle the missing or empty amount or amount <= 0 case.
    if not amount or amount <= 0:
        # Return False to the caller.
        return False

    # Handle the case where any(keyword in clean for keyword in DEBT_LIKE_KEYWORDS).
    if any(keyword in clean for keyword in DEBT_LIKE_KEYWORDS):
        # Return False to the caller.
        return False

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Pending expense section
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    if any(keyword in clean for keyword in PAST_OR_ACTUAL_KEYWORDS) or has_past_time_marker(clean):
        # Return False to the caller.
        return False

    # Open a multi-line structure for the values below.
    starts_with_pending = re.match(
        r"^(pending|rencana|planning|plan|nanti|akan|bakal|perlu|butuh|kudu|harus)\b",
        # Include this value in the surrounding collection or call.
        clean,
    # Close the structure that was opened above.
    )
    # Handle the case where starts_with_pending.
    if starts_with_pending:
        # Return True to the caller.
        return True

    # Implementation section
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Pending expense section
    if re.search(r"\b(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)\b", clean):
        # Return False to the caller.
        return False

    # Pending expense section
    # marker waktunya jelas masa depan, misalnya:
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # - "minggu depan service motor 300k"
    # - "besok service motor 300k"
    #
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Implementation section
    future_time_marker = re.search(
        r"\b(besok|lusa|minggu depan|pekan depan|bulan depan|akhir bulan)\b",
        # Include this value in the surrounding collection or call.
        clean,
    # Close the structure that was opened above.
    )
    # Open a multi-line structure for the values below.
    action_marker = re.search(
        r"\b(bayar|beli|service|servis|buat|untuk|tagihan|iuran|perpanjang|top up|isi)\b",
        # Include this value in the surrounding collection or call.
        clean,
    # Close the structure that was opened above.
    )
    # Handle the case where future_time_marker and action_marker.
    if future_time_marker and action_marker:
        # Return True to the caller.
        return True

    # Return False to the caller.
    return False


# Define strip pending time phrases for callers in this flow.
def strip_pending_time_phrases(text: str) -> str:
    """Coordinate the strip pending time phrases logic in the service layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    clean = str(text or "")
    clean = re.sub(r"\b(?:besok|lusa|minggu depan|pekan depan|bulan depan|bulan ini|bulan lalu|akhir bulan)\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])(?:[-/](0?[1-9]|[12]\d|3[01]))?\b", " ", clean)
    clean = re.sub(r"\b(?:tanggal|tgl|tg|date|pada tanggal)\s+(?:0?[1-9]|[12]\d|3[01])\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()
    # Return clean to the caller.
    return clean


# Define infer category for callers in this flow.
def infer_category(text: str, parsed: dict | None = None) -> str:
    """Coordinate the infer category logic in the service layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep category name, type, symbol, and alias behavior consistent with the documented category flow.
    """
    if parsed and parsed.get("category"):
        return str(parsed.get("category")).strip()

    clean = str(text or "").lower()
    # Process each category, keywords in the current collection.
    for category, keywords in CATEGORY_KEYWORDS.items():
        # Handle the case where any(str(keyword).lower() in clean for keyword in keywords).
        if any(str(keyword).lower() in clean for keyword in keywords):
            # Return category to the caller.
            return category
    return "Other Expense"


# Define infer account for callers in this flow.
def infer_account(text: str, parsed: dict | None = None) -> str:
    """Infer account from parsed data or sheet-backed account names."""
    if parsed and parsed.get("account"):
        resolved = resolve_account_for_parser(parsed.get("account"))
        return resolved or str(parsed.get("account")).strip()

    clean = str(text or "").lower()

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare runtime accounts for the next step.
        runtime_accounts = get_account_names_from_sheet()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Prepare runtime accounts for the next step.
        runtime_accounts = []

    # Process each account_name in the current collection.
    for account_name in sorted(runtime_accounts or [], key=len, reverse=True):
        account_pattern = re.escape(str(account_name).strip().lower()).replace(r"\ ", r"\s+")
        if account_pattern and re.search(rf"\b{account_pattern}\b", clean, flags=re.IGNORECASE):
            # Return str(account_name).strip() to the caller.
            return str(account_name).strip()

    # Prepare found for the next step.
    found = []
    # Process each account in the current collection.
    for account in sorted(ACCOUNT_NAMES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(account)}\b", clean):
            # Update found with the current value.
            found.append(ACCOUNT_DISPLAY_NAMES.get(account, account.upper()))
    return found[0] if found else ""


# Define title from description for callers in this flow.
def title_from_description(description: str) -> str:
    """Coordinate the title from description logic in the service layer.

    Args:
        description: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    clean = str(description or "").strip()
    clean = re.sub(r"^(?:beli|bayar|buat|untuk|tagihan)\s+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean.title() if clean else "Pending Expense"


# Define build pending row for callers in this flow.
def build_pending_row(item: dict) -> list:
    """Build the data structure or message text for pending row."""
    return [item.get(col, "") for col in PENDING_EXPENSE_COLUMNS]


# Define build pending expense from text for callers in this flow.
def build_pending_expense_from_text(text: str) -> dict:
    """Build the data structure or message text for pending expense from text."""
    raw_input = str(text or "").strip()
    # Prepare clean text for the next step.
    clean_text = clean_pending_text(raw_input)

    # Handle the missing or empty clean_text case.
    if not clean_text:
        raise ValueError("Tulis rencana/pending expense setelah command.")

    # Prepare amount for the next step.
    amount = extract_amount_from_text(clean_text)
    # Handle the missing or empty amount or amount <= 0 case.
    if not amount or amount <= 0:
        raise ValueError("Nominal pending expense belum terbaca. Contoh: /pending_add bayar wifi 285k")

    # Run this statement as part of the current workflow.
    due_date, month, due_precision = detect_pending_due(clean_text)
    # Prepare parsed for the next step.
    parsed = parse_with_regex(clean_text) or {}
    # Prepare category for the next step.
    category = infer_category(clean_text, parsed)
    # Prepare account for the next step.
    account = infer_account(clean_text, parsed)

    description = parsed.get("description") or extract_description(clean_text, amount) or clean_text
    # Prepare description for the next step.
    description = strip_pending_time_phrases(description)
    description = re.sub(r"\s+", " ", description).strip()
    subject = parsed.get("subject") or title_from_description(description)

    # Prepare created at for the next step.
    created_at = now_str()
    # Return { to the caller.
    return {
        "id": generate_pending_id(),
        "due_date": due_date,
        "month": month,
        "due_precision": due_precision,
        "amount": float(amount),
        "category": category,
        "account": account,
        "subject": subject,
        "description": description or subject,
        "status": "pending",
        "created_at": created_at,
        "updated_at": created_at,
        "paid_transaction_id": "",
        "raw_input": raw_input,
    # Close the structure that was opened above.
    }


# Define save pending expense for callers in this flow.
def save_pending_expense(item: dict) -> dict:
    """Save data after validation and confirmation for pending expense."""
    # Prepare item for the next step.
    item = dict(item or {})
    if not item.get("id"):
        item["id"] = generate_pending_id()
    if not item.get("created_at"):
        item["created_at"] = now_str()
    item["updated_at"] = now_str()
    item["status"] = item.get("status") or "pending"
    item.setdefault("paid_transaction_id", "")
    # Run this statement as part of the current workflow.
    append_row_raw(SHEET_PENDING_EXPENSES, build_pending_row(item))
    # Return item to the caller.
    return item


# Define add pending expense from text for callers in this flow.
def add_pending_expense_from_text(text: str) -> dict:
    """Coordinate the add pending expense from text logic in the service layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Return save_pending_expense(build_pending_expense_from_text(text)) to the caller.
    return save_pending_expense(build_pending_expense_from_text(text))


# Define get pending expenses for callers in this flow.
def get_pending_expenses(period: str | None = None, active_only: bool = True) -> dict:
    """Retrieve data needed by the get pending expenses workflow in the service layer.

    Args:
        period: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        active_only: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Prepare records for the next step.
    records = get_all_records(SHEET_PENDING_EXPENSES)
    clean_period = str(period or "").strip().lower()

    filter_type = "month"
    # Prepare label for the next step.
    label = current_month()
    # Prepare month for the next step.
    month = current_month()

    if clean_period in {"all", "semua", "seluruh"}:
        filter_type = "all"
        label = "semua periode"
        month = ""
    elif clean_period in {"no_date", "tanpa_tanggal", "tanpa tanggal", "belum pasti", "unknown"}:
        filter_type = "unknown"
        label = "tanggal belum pasti"
        month = ""
    # Handle the alternate case where clean_period.
    elif clean_period:
        # Prepare month for the next step.
        month = normalize_month(clean_period)
        # Prepare label for the next step.
        label = month
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare month for the next step.
        month = current_month()
        # Prepare label for the next step.
        label = month

    # Prepare filtered for the next step.
    filtered = []
    # Process each row in the current collection.
    for row in records:
        status = str(row.get("status", "pending") or "pending").strip().lower()
        # Handle the case where active_only and status in CLOSED_STATUSES.
        if active_only and status in CLOSED_STATUSES:
            # Skip the rest of this loop iteration after handling this case.
            continue

        row_month = str(row.get("month", "") or "").strip()
        due_precision = str(row.get("due_precision", "") or "").strip().lower()

        if filter_type == "all":
            # Update filtered with the current value.
            filtered.append(row)
        elif filter_type == "unknown":
            if due_precision == "unknown" or not str(row.get("due_date", "") or "").strip():
                # Update filtered with the current value.
                filtered.append(row)
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Handle the case where row_month == month.
            if row_month == month:
                # Update filtered with the current value.
                filtered.append(row)

    # Define sort key for callers in this flow.
    def sort_key(item: dict):
        """Coordinate the sort key logic in the service layer.

        Args:
            item: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            Value produced by the existing return statements; shape is determined by the current implementation.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
        """
        due = str(item.get("due_date", "") or "")
        return (due == "", due or "9999-99-99", str(item.get("created_at", "")))

    # Prepare filtered for the next step.
    filtered = sorted(filtered, key=sort_key)
    total = sum(safe_float(item.get("amount")) for item in filtered)

    # Return { to the caller.
    return {
        "items": filtered,
        "total": total,
        "count": len(filtered),
        "filter_type": filter_type,
        "month": month,
        "label": label,
        "active_only": active_only,
    # Close the structure that was opened above.
    }


# Define find pending by ref for callers in this flow.
def find_pending_by_ref(ref: str) -> tuple[int | None, dict | None]:
    """Coordinate the find pending by ref logic in the service layer.

    Args:
        ref: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `tuple[int | None, dict | None]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    ref = str(ref or "").strip()
    # Handle the missing or empty ref case.
    if not ref:
        # Return None, None to the caller.
        return None, None

    # Prepare records for the next step.
    records = get_all_records(SHEET_PENDING_EXPENSES)
    # Process each row_index, row in the current collection.
    for row_index, row in enumerate(records, start=2):
        pending_id = str(row.get("id", "") or "").strip()
        # Handle the case where pending_id == ref or pending_id.lower().startswith(ref.lower()).
        if pending_id == ref or pending_id.lower().startswith(ref.lower()):
            # Return row_index, row to the caller.
            return row_index, row
    # Return None, None to the caller.
    return None, None


def update_pending_status(row_index: int, status: str, paid_transaction_id: str = "") -> None:
    # Columns: status=10, updated_at=12, paid_transaction_id=13
    """Apply the update pending status operation in the service layer.

    Args:
        row_index: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        status: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        paid_transaction_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    # Run this statement as part of the current workflow.
    update_cell(SHEET_PENDING_EXPENSES, row_index, 10, status)
    # Run this statement as part of the current workflow.
    update_cell(SHEET_PENDING_EXPENSES, row_index, 12, now_str())
    # Handle the case where paid_transaction_id.
    if paid_transaction_id:
        # Run this statement as part of the current workflow.
        update_cell(SHEET_PENDING_EXPENSES, row_index, 13, paid_transaction_id)


# Define cancel pending expense for callers in this flow.
def cancel_pending_expense(ref: str) -> dict:
    """Coordinate the cancel pending expense logic in the service layer.

    Args:
        ref: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Run this statement as part of the current workflow.
    row_index, item = find_pending_by_ref(ref)
    # Handle the missing or empty item or not row_index case.
    if not item or not row_index:
        return {"success": False, "message": "Pending expense tidak ditemukan."}

    status = str(item.get("status", "pending") or "pending").strip().lower()
    # Handle the case where status in CLOSED_STATUSES.
    if status in CLOSED_STATUSES:
        return {"success": False, "message": f"Pending expense sudah berstatus {status}."}

    update_pending_status(row_index, "cancelled")
    return {"success": True, "item": item, "message": "ok"}


# Define mark pending paid for callers in this flow.
def mark_pending_paid(ref: str, account: str | None = None, paid_date: str | None = None) -> dict:
    """Coordinate the mark pending paid logic in the service layer.

    Args:
        ref: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        account: Account name or account-like value from user input or sheet data.
        paid_date: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Run this statement as part of the current workflow.
    row_index, item = find_pending_by_ref(ref)
    # Handle the missing or empty item or not row_index case.
    if not item or not row_index:
        return {"success": False, "message": "Pending expense tidak ditemukan."}

    status = str(item.get("status", "pending") or "pending").strip().lower()
    # Handle the case where status in CLOSED_STATUSES.
    if status in CLOSED_STATUSES:
        return {"success": False, "message": f"Pending expense sudah berstatus {status}."}

    paid_date = str(paid_date or "").strip() or datetime.now().strftime("%Y-%m-%d")
    txn_account = str(account or item.get("account") or "").strip()
    # Handle the missing or empty txn_account case.
    if not txn_account:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Rekening belum diketahui. Gunakan: /pending_paid pending_id BRI",
        # Close the structure that was opened above.
        }

    # Open a multi-line structure for the values below.
    parsed = {
        "type": "expense",
        "amount": safe_float(item.get("amount")),
        "category": item.get("category") or "Other Expense",
        "account": txn_account,
        "to_account": "",
        "subject": item.get("subject") or item.get("description") or "Pending Expense",
        "description": item.get("description") or item.get("subject") or "Pending Expense",
        "catatan": f"Dibayar dari pending expense {item.get('id')}",
        "tipe_pengeluaran": "Bulanan",
        "date": paid_date,
        "parsed_by": "pending_expense",
    # Close the structure that was opened above.
    }

    result = save_transaction(parsed, item.get("raw_input") or parsed["description"])
    if not result.get("success"):
        # Return result to the caller.
        return result

    txn_id = result.get("transaction_id") or ""
    update_pending_status(row_index, "paid", txn_id)
    # Return { to the caller.
    return {
        "success": True,
        "item": item,
        "transaction_id": txn_id,
        "pending_id": item.get("id") or ref,
        "account": txn_account,
        "amount": parsed.get("amount"),
        "new_balance": result.get("new_balance"),
        "new_balance_account": result.get("new_balance_account") or txn_account,
        "new_balances": result.get("new_balances", {}),
        "message": "ok",
    # Close the structure that was opened above.
    }
