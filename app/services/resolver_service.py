"""Central account and category resolvers for finance bot flows."""

from __future__ import annotations

import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from app.config import SHEET_ACCOUNTS, SHEET_CATEGORIES
from app.sheets.client import append_row_raw, get_all_records

DEFAULT_ACCOUNT_NAMES = ["Cash", "BRI", "BSI", "BCA", "DANA", "GoPay", "Seabank"]
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
]

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
}


def normalize_lookup_key(value: Any) -> str:
    """Normalize text for loose account/category matching."""
    clean = str(value or "").strip().lower()
    clean = clean.replace("&", " and ")
    clean = re.sub(r"[^a-z0-9À-ÿ]+", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


def compact_lookup_key(value: Any) -> str:
    """Normalize text into a compact comparison key."""
    return re.sub(r"\s+", "", normalize_lookup_key(value))


def _safe_records(sheet_name: str, fallback: list[dict]) -> list[dict]:
    """Read records from Sheets with a fallback for offline tests or setup issues."""
    try:
        records = get_all_records(sheet_name)
    except Exception:
        return list(fallback)
    return records or list(fallback)


def get_account_records_safe() -> list[dict]:
    """Return account records from the accounts sheet, with safe defaults."""
    fallback = [
        {"account_name": name, "type": "bank" if name not in {"Cash", "DANA", "GoPay"} else ("cash" if name == "Cash" else "ewallet"), "balance": 0, "currency": "IDR", "last_updated": ""}
        for name in DEFAULT_ACCOUNT_NAMES
    ]
    return _safe_records(SHEET_ACCOUNTS, fallback)


def get_account_names_from_sheet() -> list[str]:
    """Return active account names from the accounts sheet."""
    names = []
    for record in get_account_records_safe():
        name = str(record.get("account_name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names or list(DEFAULT_ACCOUNT_NAMES)


def resolve_account_name(account_input: str, *, similarity_threshold: float = 0.78) -> dict:
    """Resolve account input against the accounts sheet.

    Returns a dict with status: exact, similar, missing, or empty.
    """
    raw = str(account_input or "").strip().strip('"').strip("'")
    if not raw:
        return {"status": "empty", "account_name": None, "suggestions": []}

    names = get_account_names_from_sheet()
    raw_key = normalize_lookup_key(raw)
    raw_compact = compact_lookup_key(raw)

    for name in names:
        if normalize_lookup_key(name) == raw_key:
            return {"status": "exact", "account_name": name, "suggestions": []}

    suggestions = []
    for name in names:
        name_key = normalize_lookup_key(name)
        name_compact = compact_lookup_key(name)
        score = SequenceMatcher(None, raw_key, name_key).ratio()
        substring_match = bool(raw_compact and name_compact and (raw_compact in name_compact or name_compact in raw_compact))
        if substring_match or score >= similarity_threshold:
            suggestions.append({"account_name": name, "score": max(score, 0.95 if substring_match else score)})

    suggestions = sorted(suggestions, key=lambda item: item["score"], reverse=True)
    if suggestions:
        return {
            "status": "similar",
            "account_name": None,
            "suggestions": [item["account_name"] for item in suggestions[:5]],
        }

    return {"status": "missing", "account_name": None, "suggestions": []}


def create_account(account_name: str, initial_balance: float = 0, account_type: str = "bank") -> dict:
    """Create a new account row in the accounts sheet if it does not exist."""
    clean_name = str(account_name or "").strip().strip('"').strip("'")
    if not clean_name:
        return {"success": False, "message": "Nama rekening kosong.", "account_name": ""}

    resolved = resolve_account_name(clean_name)
    if resolved.get("status") == "exact":
        return {
            "success": True,
            "created": False,
            "message": "Rekening sudah ada.",
            "account_name": resolved.get("account_name"),
        }

    today = datetime.now().strftime("%Y-%m-%d")
    append_row_raw(SHEET_ACCOUNTS, [clean_name, account_type or "bank", float(initial_balance or 0), "IDR", today])
    return {
        "success": True,
        "created": True,
        "message": "Rekening baru dibuat.",
        "account_name": clean_name,
    }


def get_category_records_safe() -> list[dict]:
    """Return category records from the categories sheet, with safe defaults."""
    return _safe_records(SHEET_CATEGORIES, DEFAULT_CATEGORY_ROWS)


def get_category_names_from_sheet(transaction_type: str | None = None) -> list[str]:
    """Return category names from the categories sheet."""
    txn_type = str(transaction_type or "").strip().lower()
    names = []
    for record in get_category_records_safe():
        name = str(record.get("category_name") or "").strip()
        record_type = str(record.get("type") or "").strip().lower()
        if not name:
            continue
        if txn_type and record_type and record_type != txn_type:
            continue
        if name not in names:
            names.append(name)
    return names


def _category_alias_candidates(record: dict) -> list[str]:
    aliases = str(record.get("aliases") or "")
    result = [str(record.get("category_name") or "")]
    result.extend(part.strip() for part in aliases.split(",") if part.strip())
    return result


def _default_category_type(transaction_type: str | None) -> str:
    txn_type = str(transaction_type or "").strip().lower()
    return "income" if txn_type == "income" else "expense"


def _default_category_name(transaction_type: str | None) -> str:
    return "Other Income" if _default_category_type(transaction_type) == "income" else "Other Expense"


def _default_category_emoji(transaction_type: str | None) -> str:
    return "💰" if _default_category_type(transaction_type) == "income" else "📦"


def resolve_category_name(category_input: str, transaction_type: str | None = None, *, allow_create: bool = False) -> dict:
    """Resolve category input against existing categories and common aliases."""
    raw = str(category_input or "").strip()
    txn_type = _default_category_type(transaction_type)
    if not raw:
        return {"status": "default", "category_name": _default_category_name(txn_type), "created": False}

    records = get_category_records_safe()
    raw_key = normalize_lookup_key(raw)
    raw_compact = compact_lookup_key(raw)
    canonical = CATEGORY_CANONICAL_ALIASES.get(raw_key) or CATEGORY_CANONICAL_ALIASES.get(raw_compact)

    if canonical:
        raw = canonical
        raw_key = normalize_lookup_key(raw)
        raw_compact = compact_lookup_key(raw)

    for record in records:
        name = str(record.get("category_name") or "").strip()
        if not name:
            continue
        record_type = str(record.get("type") or txn_type).strip().lower() or txn_type
        if record_type != txn_type:
            continue
        if normalize_lookup_key(name) == raw_key:
            return {"status": "exact", "category_name": name, "created": False}

    for record in records:
        name = str(record.get("category_name") or "").strip()
        record_type = str(record.get("type") or txn_type).strip().lower() or txn_type
        if not name or record_type != txn_type:
            continue
        for alias in _category_alias_candidates(record):
            alias_key = normalize_lookup_key(alias)
            alias_compact = compact_lookup_key(alias)
            if raw_key == alias_key or (raw_compact and raw_compact == alias_compact):
                return {"status": "alias", "category_name": name, "created": False}

    best_name = None
    best_score = 0.0
    for record in records:
        name = str(record.get("category_name") or "").strip()
        record_type = str(record.get("type") or txn_type).strip().lower() or txn_type
        if not name or record_type != txn_type:
            continue
        for alias in _category_alias_candidates(record):
            score = SequenceMatcher(None, raw_key, normalize_lookup_key(alias)).ratio()
            if score > best_score:
                best_name = name
                best_score = score

    if best_name and best_score >= 0.86:
        return {"status": "similar", "category_name": best_name, "created": False}

    if allow_create:
        created = create_category(raw, txn_type)
        return {
            "status": "created" if created.get("success") else "fallback",
            "category_name": created.get("category_name") or _default_category_name(txn_type),
            "created": bool(created.get("created")),
        }

    return {"status": "missing", "category_name": raw, "created": False}


def create_category(category_name: str, transaction_type: str = "expense", emoji: str | None = None, aliases: str = "") -> dict:
    """Create a category row in the categories sheet if it is truly new."""
    clean_name = str(category_name or "").strip().strip('"').strip("'")
    if not clean_name:
        return {"success": False, "message": "Nama kategori kosong.", "category_name": ""}

    txn_type = _default_category_type(transaction_type)
    existing = resolve_category_name(clean_name, txn_type, allow_create=False)
    if existing.get("status") in {"exact", "alias", "similar"}:
        return {
            "success": True,
            "created": False,
            "message": "Kategori sudah ada atau mirip kategori existing.",
            "category_name": existing.get("category_name"),
        }

    append_row_raw(SHEET_CATEGORIES, [clean_name, txn_type, emoji or _default_category_emoji(txn_type), aliases or normalize_lookup_key(clean_name)])
    return {
        "success": True,
        "created": True,
        "message": "Kategori baru dibuat.",
        "category_name": clean_name,
    }


def ensure_category_for_transaction(category_name: str, transaction_type: str | None) -> str:
    """Resolve or create the category used by a parsed transaction."""
    txn_type = str(transaction_type or "").strip().lower()
    if txn_type not in {"expense", "income"}:
        return str(category_name or "").strip()
    resolved = resolve_category_name(category_name, txn_type, allow_create=True)
    return str(resolved.get("category_name") or _default_category_name(txn_type)).strip()


def resolve_account_for_parser(account_name: str | None) -> str | None:
    """Resolve parser account output to an existing account when possible."""
    if not account_name:
        return None
    resolved = resolve_account_name(account_name)
    if resolved.get("status") == "exact":
        return str(resolved.get("account_name") or "").strip() or None
    if resolved.get("status") == "similar" and resolved.get("suggestions"):
        return str(resolved["suggestions"][0] or "").strip() or None
    return None


def resolve_parsed_transaction(parsed: dict, raw_text: str = "") -> dict:
    """Normalize parsed transaction accounts and category through sheet-backed resolvers."""
    if not isinstance(parsed, dict):
        return parsed

    txn_type = str(parsed.get("type") or "").strip().lower()

    if parsed.get("account"):
        resolved_account = resolve_account_for_parser(parsed.get("account"))
        if resolved_account:
            parsed["account"] = resolved_account

    if parsed.get("to_account"):
        resolved_to_account = resolve_account_for_parser(parsed.get("to_account"))
        if resolved_to_account:
            parsed["to_account"] = resolved_to_account

    if txn_type in {"expense", "income"}:
        category = str(parsed.get("category") or "").strip()
        parsed["category"] = ensure_category_for_transaction(category, txn_type)

    return parsed
