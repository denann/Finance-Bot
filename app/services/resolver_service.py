"""Central account and category resolvers for finance bot flows."""

# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import re for this module's local operations.
import re
# Import datetime so this module can use its helpers.
from datetime import datetime
# Import difflib so this module can use its helpers.
from difflib import SequenceMatcher
# Import typing so this module can use its helpers.
from typing import Any

# Import app.config so this module can use its helpers.
from app.config import SHEET_ACCOUNTS, SHEET_CATEGORIES
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import append_row_raw, get_all_records, update_cell

DEFAULT_ACCOUNT_NAMES = ["Cash", "BRI", "BSI", "BCA", "DANA", "GoPay", "Seabank"]
# Open a multi-line structure for the values below.
DEFAULT_CATEGORY_ROWS = [
    {"category_name": "Food & Beverage", "type": "expense", "emoji": "🍽️", "aliases": "makan,minum,kopi,nasi,donat,galon"},
    {"category_name": "Jajan", "type": "expense", "emoji": "🍢", "aliases": "jajan,ngemil,cemilan,snack,bakso,cilok,seblak,jajan pasar"},
    {"category_name": "Transport", "type": "expense", "emoji": "🚗", "aliases": "transport,ojek,bensin,parkir,tol"},
    {"category_name": "Bills & Utilities", "type": "expense", "emoji": "💡", "aliases": "listrik,air,wifi,pulsa,token,tagihan"},
    {"category_name": "Entertainment", "type": "expense", "emoji": "🎮", "aliases": "game,ml,netflix,bioskop,hiburan"},
    {"category_name": "Health", "type": "expense", "emoji": "🏥", "aliases": "obat,dokter,klinik,vitamin"},
    {"category_name": "Shopping", "type": "expense", "emoji": "🛍️", "aliases": "belanja,shopee,tokopedia,baju"},
    {"category_name": "Education", "type": "expense", "emoji": "🎓", "aliases": "kuliah,buku,kursus,wisuda,semester"},
    {"category_name": "Housing", "type": "expense", "emoji": "🏠", "aliases": "kos,kontrakan,sewa,rumah"},
    {"category_name": "Charity", "type": "expense", "emoji": "🤲", "aliases": "sedekah,donasi,zakat"},
    {"category_name": "Other Expense", "type": "expense", "emoji": "📦", "aliases": "lainnya,other"},
    {"category_name": "Salary", "type": "income", "emoji": "💼", "aliases": "gaji,salary"},
    {"category_name": "Bonus", "type": "income", "emoji": "🎁", "aliases": "bonus,thr"},
    {"category_name": "Refund", "type": "income", "emoji": "↩️", "aliases": "refund,pengembalian"},
    {"category_name": "Cashback", "type": "income", "emoji": "🏷️", "aliases": "cashback"},
    {"category_name": "Other Income", "type": "income", "emoji": "💰", "aliases": "pemasukan lain,other income"},
# Close the structure that was opened above.
]

# Open a multi-line structure for the values below.
CATEGORY_CANONICAL_ALIASES = {
    "food": "Food & Beverage",
    "food and beverage": "Food & Beverage",
    "fnb": "Food & Beverage",
    "f&b": "Food & Beverage",
    "makanan": "Food & Beverage",
    "minuman": "Food & Beverage",
    "hiburan": "Entertainment",
    "entertainment": "Entertainment",
    "jjajan": "Jajan",
    "jajan": "Jajan",
    "ngemil": "Jajan",
    "cemilan": "Jajan",
    "snack": "Jajan",
    "transportasi": "Transport",
    "transport": "Transport",
    "tagihan": "Bills & Utilities",
    "utilities": "Bills & Utilities",
    "utility": "Bills & Utilities",
    "shopping": "Shopping",
    "belanja": "Shopping",
    "household": "Household & Supplies",
    "household and supplies": "Household & Supplies",
    "kebutuhan rumah": "Household & Supplies",
    "perlengkapan rumah": "Household & Supplies",
    "kesehatan": "Health",
    "health": "Health",
    "pendidikan": "Education",
    "education": "Education",
    "zakat sedekah": "Charity",
    "sedekah": "Charity",
    "donasi": "Charity",
    "gaji": "Salary",
    "salary": "Salary",
    "refund": "Refund",
    "cashback": "Cashback",
# Close the structure that was opened above.
}


# Define normalize lookup key for callers in this flow.
def normalize_lookup_key(value: Any) -> str:
    """Normalize input values for the normalize lookup key workflow in the service layer.

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
    clean = clean.replace("&", " and ")
    clean = re.sub(r"[^a-z0-9À-ÿ]+", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


# Define compact lookup key for callers in this flow.
def compact_lookup_key(value: Any) -> str:
    """Coordinate the compact lookup key logic in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return re.sub(r"\s+", "", normalize_lookup_key(value))


# Define safe records for callers in this flow.
def _safe_records(sheet_name: str, fallback: list[dict]) -> list[dict]:
    """Read records from Sheets with a fallback for offline tests or setup issues."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare records for the next step.
        records = get_all_records(sheet_name)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return list(fallback) to the caller.
        return list(fallback)
    # Return records or list(fallback) to the caller.
    return records or list(fallback)


# Define get account records safe for callers in this flow.
def get_account_records_safe() -> list[dict]:
    """Return account records from the accounts sheet, with safe defaults."""
    # Open a multi-line structure for the values below.
    fallback = [
        {"account_name": name, "type": "bank" if name not in {"Cash", "DANA", "GoPay"} else ("cash" if name == "Cash" else "ewallet"), "balance": 0, "currency": "IDR", "last_updated": ""}
        # Process each name in the current collection.
        for name in DEFAULT_ACCOUNT_NAMES
    # Close the structure that was opened above.
    ]
    # Return _safe_records(SHEET_ACCOUNTS, fallback) to the caller.
    return _safe_records(SHEET_ACCOUNTS, fallback)


# Define get account names from sheet for callers in this flow.
def get_account_names_from_sheet() -> list[str]:
    """Return active account names from the accounts sheet."""
    # Prepare names for the next step.
    names = []
    # Process each record in the current collection.
    for record in get_account_records_safe():
        name = str(record.get("account_name") or "").strip()
        # Handle the case where name and name not in names.
        if name and name not in names:
            # Update names with the current value.
            names.append(name)
    # Return names or list(DEFAULT_ACCOUNT_NAMES) to the caller.
    return names or list(DEFAULT_ACCOUNT_NAMES)


# Define resolve account name for callers in this flow.
def resolve_account_name(account_input: str, *, similarity_threshold: float = 0.78) -> dict:
    """Resolve account input against the accounts sheet.

    Returns a dict with status: exact, similar, missing, or empty.
    """
    raw = str(account_input or "").strip().strip('"').strip("'")
    # Handle the missing or empty raw case.
    if not raw:
        return {"status": "empty", "account_name": None, "suggestions": []}

    # Prepare names for the next step.
    names = get_account_names_from_sheet()
    # Prepare raw key for the next step.
    raw_key = normalize_lookup_key(raw)
    # Prepare raw compact for the next step.
    raw_compact = compact_lookup_key(raw)

    # Process each name in the current collection.
    for name in names:
        # Handle the case where normalize_lookup_key(name) == raw_key.
        if normalize_lookup_key(name) == raw_key:
            return {"status": "exact", "account_name": name, "suggestions": []}

    # Prepare suggestions for the next step.
    suggestions = []
    # Process each name in the current collection.
    for name in names:
        # Prepare name key for the next step.
        name_key = normalize_lookup_key(name)
        # Prepare name compact for the next step.
        name_compact = compact_lookup_key(name)
        # Prepare score for the next step.
        score = SequenceMatcher(None, raw_key, name_key).ratio()
        # Prepare substring match for the next step.
        substring_match = bool(raw_compact and name_compact and (raw_compact in name_compact or name_compact in raw_compact))
        # Handle the case where substring_match or score >= similarity_threshold.
        if substring_match or score >= similarity_threshold:
            suggestions.append({"account_name": name, "score": max(score, 0.95 if substring_match else score)})

    suggestions = sorted(suggestions, key=lambda item: item["score"], reverse=True)
    # Handle the case where suggestions.
    if suggestions:
        # Return { to the caller.
        return {
            "status": "similar",
            "account_name": None,
            "suggestions": [item["account_name"] for item in suggestions[:5]],
        # Close the structure that was opened above.
        }

    return {"status": "missing", "account_name": None, "suggestions": []}


def create_account(account_name: str, initial_balance: float = 0, account_type: str = "bank") -> dict:
    """Create a new account row in the accounts sheet if it does not exist."""
    clean_name = str(account_name or "").strip().strip('"').strip("'")
    # Handle the missing or empty clean_name case.
    if not clean_name:
        return {"success": False, "message": "Nama rekening kosong.", "account_name": ""}

    # Prepare resolved for the next step.
    resolved = resolve_account_name(clean_name)
    if resolved.get("status") == "exact":
        # Return { to the caller.
        return {
            "success": True,
            "created": False,
            "message": "Rekening sudah ada.",
            "account_name": resolved.get("account_name"),
        # Close the structure that was opened above.
        }

    today = datetime.now().strftime("%Y-%m-%d")
    append_row_raw(SHEET_ACCOUNTS, [clean_name, account_type or "bank", float(initial_balance or 0), "IDR", today])
    # Return { to the caller.
    return {
        "success": True,
        "created": True,
        "message": "Rekening baru dibuat.",
        "account_name": clean_name,
    # Close the structure that was opened above.
    }


# Define get category records safe for callers in this flow.
def get_category_records_safe() -> list[dict]:
    """Return category records from the categories sheet, with safe defaults."""
    # Return _safe_records(SHEET_CATEGORIES, DEFAULT_CATEGORY_ROWS) to the caller.
    return _safe_records(SHEET_CATEGORIES, DEFAULT_CATEGORY_ROWS)


def normalize_category_aliases(aliases: Any, category_name: str = "", *, limit: int = 24) -> str:
    """Normalize aliases into the comma-separated `categories.aliases` format.

    Args:
        aliases: Raw aliases from Gemini, manual user input, or existing sheet
            data. Accepted input types are a string (`"a,b,c"`), list, tuple,
            set, `None`, or any value that can be converted to string.
        category_name: Optional category name to force into the first alias
            candidates, for example `Belanja Online`.
        limit: Maximum number of aliases kept after cleanup.

    Returns:
        A comma-separated lowercase string without duplicate compact keys, for
        example `belanja online,shopping,shopee,tokopedia`. Empty or fully
        blocked input returns an empty string.

    Cleanup rules:
        - Split strings by comma, semicolon, or newline.
        - Normalize text with the same lookup rules used by category resolver.
        - Drop overly broad aliases such as `uang`, `bayar`, `expense`, and
          `income`.
        - Deduplicate aliases by compact lookup key so `tiktok shop` and
          `tiktokshop` do not both survive.
    """
    # Accept empty alias input without failing the category wizard.
    if aliases is None:
        # Prepare raw items for the next step.
        raw_items = []
    # Gemini can return a list; manual code may pass tuple/set too.
    elif isinstance(aliases, (list, tuple, set)):
        raw_items = [str(item or "") for item in aliases]
    # Manual text input is split by common list separators.
    else:
        raw_items = re.split(r"[,;\n]+", str(aliases or ""))

    # Always include the category name itself as the first alias candidate.
    if category_name:
        # Prepare raw items for the next step.
        raw_items = [str(category_name)] + list(raw_items)

    # Broad finance words are blocked because they would over-match categories.
    blocked = {
        "uang",
        "bayar",
        "pembayaran",
        "transaksi",
        "masuk",
        "keluar",
        "biaya",
        "expense",
        "income",
        "pengeluaran",
        "pemasukan",
    # Close the structure that was opened above.
    }
    # Compact keys are used for duplicate detection across spacing variants.
    seen = set()
    # Prepare cleaned for the next step.
    cleaned = []
    # Process each item in the current collection.
    for item in raw_items:
        # Keep alias normalization consistent with transaction category lookup.
        alias = normalize_lookup_key(item)
        alias = re.sub(r"\s+", " ", alias).strip()
        # Skip empty aliases and aliases that are too generic.
        if not alias or alias in blocked:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Prepare compact for the next step.
        compact = compact_lookup_key(alias)
        # Skip duplicates such as `tiktok shop` and `tiktokshop`.
        if not compact or compact in seen:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Update seen with the current value.
        seen.add(compact)
        # Update cleaned with the current value.
        cleaned.append(alias)
        # Stop once the sheet-friendly alias limit is reached.
        if len(cleaned) >= int(limit or 24):
            # Leave the loop after the target condition has been reached.
            break

    return ",".join(cleaned)


# Define get category names from sheet for callers in this flow.
def get_category_names_from_sheet(transaction_type: str | None = None) -> list[str]:
    """Retrieve data needed by the get category names from sheet workflow in the service layer.

    Args:
        transaction_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[str]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep category name, type, symbol, and alias behavior consistent with the documented category flow.
    """
    txn_type = str(transaction_type or "").strip().lower()
    # Prepare names for the next step.
    names = []
    # Process each record in the current collection.
    for record in get_category_records_safe():
        name = str(record.get("category_name") or "").strip()
        record_type = str(record.get("type") or "").strip().lower()
        # Handle the missing or empty name case.
        if not name:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the case where txn_type and record_type and record_type != txn_type.
        if txn_type and record_type and record_type != txn_type:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the case where name not in names.
        if name not in names:
            # Update names with the current value.
            names.append(name)
    # Return names to the caller.
    return names


# Define category alias candidates for callers in this flow.
def _category_alias_candidates(record: dict) -> list[str]:
    """Return the category name plus comma-separated aliases for matching.

    Args:
        record: Category sheet record with `category_name` and `aliases`.

    Returns:
        List of candidate strings. Empty aliases are skipped.
    """
    aliases = str(record.get("aliases") or "")
    result = [str(record.get("category_name") or "")]
    result.extend(part.strip() for part in aliases.split(",") if part.strip())
    # Return result to the caller.
    return result


# Define category name exists for callers in this flow.
def _category_name_exists(records: list[dict], category_name: str, transaction_type: str) -> bool:
    """Check whether a canonical category exists for the selected type.

    Args:
        records: Category records read from sheet or fallback defaults.
        category_name: Canonical category target from built-in aliases.
        transaction_type: Normalized target type, either `expense` or `income`.

    Returns:
        True when the exact normalized category exists in records with the same
        type. False prevents built-in aliases from fabricating missing category
        names.
    """
    # Prepare target key for the next step.
    target_key = normalize_lookup_key(category_name)
    # Process each record in the current collection.
    for record in records or []:
        name = str((record or {}).get("category_name") or "").strip()
        record_type = str((record or {}).get("type") or transaction_type).strip().lower() or transaction_type
        # Handle the case where name and record_type == transaction_type and normalize_lookup....
        if name and record_type == transaction_type and normalize_lookup_key(name) == target_key:
            # Return True to the caller.
            return True
    # Return False to the caller.
    return False


# Define default category type for callers in this flow.
def _default_category_type(transaction_type: str | None) -> str:
    """Return the fallback category type for an unresolved transaction.

    Args:
        transaction_type: Parsed transaction type, usually `expense` or
            `income`.

    Returns:
        `income` only for explicit income transactions; otherwise `expense`.
    """
    txn_type = str(transaction_type or "").strip().lower()
    return "income" if txn_type == "income" else "expense"


# Define default category name for callers in this flow.
def _default_category_name(transaction_type: str | None) -> str:
    """Return the canonical fallback category name for a transaction type.

    Args:
        transaction_type: Parsed transaction type, usually `expense` or
            `income`.

    Returns:
        `Other Income` for income transactions, otherwise `Other Expense`.
    """
    return "Other Income" if _default_category_type(transaction_type) == "income" else "Other Expense"


# Define default category emoji for callers in this flow.
def _default_category_emoji(transaction_type: str | None) -> str:
    """Return the fallback category emoji for a transaction type.

    Args:
        transaction_type: Parsed transaction type, usually `expense` or
            `income`.

    Returns:
        Money emoji for income fallback, package emoji for expense fallback.
    """
    return "💰" if _default_category_type(transaction_type) == "income" else "📦"


# Define find category by name for callers in this flow.
def find_category_by_name(category_name: str) -> dict:
    """Find an existing category row by exact normalized category name.

    Args:
        category_name: Category name from `/edit_kategori`, either command args
            or the user's next message. Surrounding quotes are accepted and
            removed.

    Returns:
        A dict with:
        - `found`: bool indicating whether an exact normalized match exists.
        - `record`: the Google Sheets record when found, otherwise `None`.
        - `row_index`: 1-based sheet row index when found, including header row.
        - `suggestions`: up to five similar category names when not found.
        - `message`: read error message when Sheets cannot be read.

    Notes:
        This function reads the live `categories` sheet because edit flow must
        target a real row and should not update fallback defaults.
    """
    # Category names may come from quoted command args.
    clean_name = str(category_name or "").strip().strip('"').strip("'")
    # Empty names cannot match any sheet row.
    if not clean_name:
        return {"found": False, "record": None, "row_index": None}

    # Normalize input once so every row uses the same comparison key.
    clean_key = normalize_lookup_key(clean_name)
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Edit flow must read live sheet data, not fallback defaults.
        records = get_all_records(SHEET_CATEGORIES)
    # Handle an expected failure from the guarded operation above.
    except Exception as exc:
        return {"found": False, "record": None, "row_index": None, "message": str(exc)}

    # Sheet row index starts at 2 because row 1 is the header.
    for index, record in enumerate(records or [], start=2):
        name = str((record or {}).get("category_name") or "").strip()
        # Only exact normalized name matches are accepted for edit target.
        if name and normalize_lookup_key(name) == clean_key:
            return {"found": True, "record": record, "row_index": index}

    # If exact match fails, build suggestions without auto-selecting them.
    suggestions = []
    # Process each record in the current collection.
    for record in records or []:
        # Suggestions are only hints; they are never auto-selected for editing.
        name = str((record or {}).get("category_name") or "").strip()
        # Handle the missing or empty name case.
        if not name:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Prepare score for the next step.
        score = SequenceMatcher(None, clean_key, normalize_lookup_key(name)).ratio()
        # Handle the case where score >= 0.72.
        if score >= 0.72:
            suggestions.append({"name": name, "score": score})

    # Highest similarity suggestions are shown first in Telegram.
    suggestions = sorted(suggestions, key=lambda item: item["score"], reverse=True)
    # Return { to the caller.
    return {
        "found": False,
        "record": None,
        "row_index": None,
        "suggestions": [item["name"] for item in suggestions[:5]],
    # Close the structure that was opened above.
    }


# Define resolve category name for callers in this flow.
def resolve_category_name(category_input: str, transaction_type: str | None = None, *, allow_create: bool = False) -> dict:
    """Resolve category input against existing categories and aliases.

    Args:
        category_input: User or parser category text, for example `household`,
            `kebutuhan rumah`, `Food & Beverage`, or a sheet alias.
        transaction_type: Category type context. `income` restricts matching to
            income rows; every other value uses expense rows.
        allow_create: When true, create a category row after exact, alias, and
            similarity matching fail. This is used at transaction save boundary,
            not at preview-only clarification steps.

    Returns:
        Dict with `status`, `category_name`, and `created`. Status can be:
        `default`, `exact`, `alias`, `similar`, `created`, `fallback`, or
        `missing`.
    """
    raw = str(category_input or "").strip()
    # Prepare txn type for the next step.
    txn_type = _default_category_type(transaction_type)
    # Handle the missing or empty raw case.
    if not raw:
        return {"status": "default", "category_name": _default_category_name(txn_type), "created": False}

    # Prepare records for the next step.
    records = get_category_records_safe()
    # Prepare raw key for the next step.
    raw_key = normalize_lookup_key(raw)
    # Prepare raw compact for the next step.
    raw_compact = compact_lookup_key(raw)
    # Prepare canonical for the next step.
    canonical = CATEGORY_CANONICAL_ALIASES.get(raw_key) or CATEGORY_CANONICAL_ALIASES.get(raw_compact)

    # Handle the case where canonical and _category_name_exists(records, canonical, txn_t....
    if canonical and _category_name_exists(records, canonical, txn_type):
        # Prepare raw for the next step.
        raw = canonical
        # Prepare raw key for the next step.
        raw_key = normalize_lookup_key(raw)
        # Prepare raw compact for the next step.
        raw_compact = compact_lookup_key(raw)

    # Process each record in the current collection.
    for record in records:
        name = str(record.get("category_name") or "").strip()
        # Handle the missing or empty name case.
        if not name:
            # Skip the rest of this loop iteration after handling this case.
            continue
        record_type = str(record.get("type") or txn_type).strip().lower() or txn_type
        # Handle the case where record_type != txn_type.
        if record_type != txn_type:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the case where normalize_lookup_key(name) == raw_key.
        if normalize_lookup_key(name) == raw_key:
            return {"status": "exact", "category_name": name, "created": False}

    # Process each record in the current collection.
    for record in records:
        name = str(record.get("category_name") or "").strip()
        record_type = str(record.get("type") or txn_type).strip().lower() or txn_type
        # Handle the missing or empty name or record_type != txn_type case.
        if not name or record_type != txn_type:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Process each alias in the current collection.
        for alias in _category_alias_candidates(record):
            # Prepare alias key for the next step.
            alias_key = normalize_lookup_key(alias)
            # Prepare alias compact for the next step.
            alias_compact = compact_lookup_key(alias)
            # Handle the case where raw_key == alias_key or (raw_compact and raw_compact == alias....
            if raw_key == alias_key or (raw_compact and raw_compact == alias_compact):
                return {"status": "alias", "category_name": name, "created": False}

    # Prepare best name for the next step.
    best_name = None
    # Prepare best score for the next step.
    best_score = 0.0
    # Process each record in the current collection.
    for record in records:
        name = str(record.get("category_name") or "").strip()
        record_type = str(record.get("type") or txn_type).strip().lower() or txn_type
        # Handle the missing or empty name or record_type != txn_type case.
        if not name or record_type != txn_type:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Process each alias in the current collection.
        for alias in _category_alias_candidates(record):
            # Prepare alias key for the next step.
            alias_key = normalize_lookup_key(alias)
            # Prepare alias compact for the next step.
            alias_compact = compact_lookup_key(alias)
            # Prepare score for the next step.
            score = SequenceMatcher(None, raw_key, alias_key).ratio()
            # Open a multi-line structure for the values below.
            substring_match = bool(
                # Run this statement as part of the current workflow.
                len(raw_compact) >= 5
                # Run this statement as part of the current workflow.
                and len(alias_compact) >= 5
                # Run this statement as part of the current workflow.
                and (raw_compact in alias_compact or alias_compact in raw_compact)
            # Close the structure that was opened above.
            )
            # Prepare effective score for the next step.
            effective_score = max(score, 0.95 if substring_match else score)
            # Handle the case where effective_score > best_score.
            if effective_score > best_score:
                # Prepare best name for the next step.
                best_name = name
                # Prepare best score for the next step.
                best_score = effective_score

    # Handle the case where best_name and best_score >= 0.86.
    if best_name and best_score >= 0.86:
        return {"status": "similar", "category_name": best_name, "created": False}

    # Handle the case where allow_create.
    if allow_create:
        # Prepare created for the next step.
        created = create_category(raw, txn_type)
        # Return { to the caller.
        return {
            "status": "created" if created.get("success") else "fallback",
            "category_name": created.get("category_name") or _default_category_name(txn_type),
            "created": bool(created.get("created")),
        # Close the structure that was opened above.
        }

    return {"status": "missing", "category_name": raw, "created": False}


def create_category(category_name: str, transaction_type: str = "expense", emoji: str | None = None, aliases: str = "") -> dict:
    """Append a new category row when no matching category already exists.

    Args:
        category_name: New category name from the wizard, for example
            `Belanja Online`.
        transaction_type: Category type selected by button. `income` is stored
            as income; all other values become expense.
        emoji: User-provided symbol. This is written to the existing sheet
            column named `emoji`.
        aliases: Comma-separated aliases prepared by the wizard. The value is
            normalized again before write as a final safety step.

    Returns:
        A result dict with `success`, `created`, `message`, and
        `category_name`. If a matching or similar category already exists,
        `success` is true but `created` is false.

    Sheet write:
        Appends `[category_name, type, emoji, aliases]` to the `categories`
        sheet. This function is called only after the user confirms the preview.
    """
    # Clean category name once before validation and matching.
    clean_name = str(category_name or "").strip().strip('"').strip("'")
    # A blank name must not create a row in Google Sheets.
    if not clean_name:
        return {"success": False, "message": "Nama kategori kosong.", "category_name": ""}

    # Keep category type restricted to the existing expense/income convention.
    txn_type = _default_category_type(transaction_type)
    # Prevent duplicate rows by checking exact, alias, and similar matches.
    existing = resolve_category_name(clean_name, txn_type, allow_create=False)
    if existing.get("status") in {"exact", "alias", "similar"}:
        # Return { to the caller.
        return {
            "success": True,
            "created": False,
            "message": "Kategori sudah ada atau mirip kategori existing.",
            "category_name": existing.get("category_name"),
        # Close the structure that was opened above.
        }

    # Normalize aliases again at write boundary as a final safety step.
    clean_aliases = normalize_category_aliases(aliases, clean_name)
    # Preserve the current sheet schema: category_name, type, emoji, aliases.
    append_row_raw(SHEET_CATEGORIES, [clean_name, txn_type, emoji or _default_category_emoji(txn_type), clean_aliases])
    # Return { to the caller.
    return {
        "success": True,
        "created": True,
        "message": "Kategori baru dibuat.",
        "category_name": clean_name,
    # Close the structure that was opened above.
    }


# Define update category for callers in this flow.
def update_category(
    # Include this value in the surrounding collection or call.
    category_name: str,
    # Include this value in the surrounding collection or call.
    *,
    # Include this value in the surrounding collection or call.
    transaction_type: str | None = None,
    # Include this value in the surrounding collection or call.
    emoji: str | None = None,
    # Include this value in the surrounding collection or call.
    aliases: str | list[str] | None = None,
# Close the structure that was opened above.
) -> dict:
    """Update editable fields for an existing category row.

    Args:
        category_name: Existing category name selected in `/edit_kategori`.
        transaction_type: Optional replacement type. `income` is stored as
            income; all other non-None values become expense.
        emoji: Optional replacement symbol for the sheet column named `emoji`.
        aliases: Optional replacement aliases. Accepts comma-separated string or
            list of strings. `None` means the aliases column is not touched.

    Returns:
        A result dict. On success it contains `success`, `message`,
        `category_name`, `row_index`, `updated`, and the old `record`. On
        failure it contains `success: False`, a `message`, and possibly
        `suggestions`.

    Sheet write:
        Updates columns B-D on the matched row: type, emoji, and aliases. The
        category name itself is not renamed by this function.
    """
    # Find the exact row first so updates target a deterministic sheet row.
    found = find_category_by_name(category_name)
    # Missing category names are returned with suggestions when available.
    if not found.get("found"):
        # Return { to the caller.
        return {
            "success": False,
            "message": "Kategori tidak ditemukan.",
            "suggestions": found.get("suggestions") or [],
        # Close the structure that was opened above.
        }

    # Row index is validated before any cell update happens.
    row_index = int(found.get("row_index") or 0)
    record = found.get("record") or {}
    # Handle the case where row_index < 2.
    if row_index < 2:
        return {"success": False, "message": "Row kategori tidak valid."}

    # Track which fields were actually updated for the caller response.
    updated = {}
    # Handle the case where transaction_type is not None.
    if transaction_type is not None:
        # Column B stores the category type.
        txn_type = _default_category_type(transaction_type)
        # Run this statement as part of the current workflow.
        update_cell(SHEET_CATEGORIES, row_index, 2, txn_type)
        updated["type"] = txn_type

    # Handle the case where emoji is not None.
    if emoji is not None:
        # Column C keeps the historical `emoji` schema, used as user symbol.
        clean_emoji = str(emoji or "").strip()
        # Run this statement as part of the current workflow.
        update_cell(SHEET_CATEGORIES, row_index, 3, clean_emoji)
        updated["emoji"] = clean_emoji

    # Handle the case where aliases is not None.
    if aliases is not None:
        # Column D uses one comma-separated aliases string.
        clean_aliases = normalize_category_aliases(aliases, str(record.get("category_name") or category_name))
        # Run this statement as part of the current workflow.
        update_cell(SHEET_CATEGORIES, row_index, 4, clean_aliases)
        updated["aliases"] = clean_aliases

    # Return { to the caller.
    return {
        "success": True,
        "message": "Kategori berhasil diupdate.",
        "category_name": str(record.get("category_name") or category_name).strip(),
        "row_index": row_index,
        "updated": updated,
        "record": record,
    # Close the structure that was opened above.
    }


# Define ensure category for transaction for callers in this flow.
def ensure_category_for_transaction(category_name: str, transaction_type: str | None) -> str:
    """Resolve or create the category used by a parsed transaction."""
    txn_type = str(transaction_type or "").strip().lower()
    if txn_type not in {"expense", "income"}:
        return str(category_name or "").strip()
    # Prepare resolved for the next step.
    resolved = resolve_category_name(category_name, txn_type, allow_create=True)
    return str(resolved.get("category_name") or _default_category_name(txn_type)).strip()


# Define resolve account for parser for callers in this flow.
def resolve_account_for_parser(account_name: str | None) -> str | None:
    """Resolve parser account output to an existing account when possible."""
    # Handle the missing or empty account_name case.
    if not account_name:
        # Return None to the caller.
        return None
    # Prepare resolved for the next step.
    resolved = resolve_account_name(account_name)
    if resolved.get("status") == "exact":
        return str(resolved.get("account_name") or "").strip() or None
    if resolved.get("status") == "similar" and resolved.get("suggestions"):
        return str(resolved["suggestions"][0] or "").strip() or None
    # Return None to the caller.
    return None


def resolve_parsed_transaction(parsed: dict, raw_text: str = "") -> dict:
    """Normalize parsed transaction accounts and category through sheet-backed resolvers."""
    # Handle the missing or empty isinstance(parsed, dict) case.
    if not isinstance(parsed, dict):
        # Return parsed to the caller.
        return parsed

    txn_type = str(parsed.get("type") or "").strip().lower()

    if parsed.get("account"):
        resolved_account = resolve_account_for_parser(parsed.get("account"))
        # Handle the case where resolved_account.
        if resolved_account:
            parsed["account"] = resolved_account

    if parsed.get("to_account"):
        resolved_to_account = resolve_account_for_parser(parsed.get("to_account"))
        # Handle the case where resolved_to_account.
        if resolved_to_account:
            parsed["to_account"] = resolved_to_account

    if txn_type in {"expense", "income"}:
        category = str(parsed.get("category") or "").strip()
        parsed["category"] = ensure_category_for_transaction(category, txn_type)

    # Return parsed to the caller.
    return parsed
