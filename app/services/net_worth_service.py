import uuid
from datetime import datetime

from app.config import (
    SHEET_ASSETS,
    SHEET_LIABILITIES,
    SHEET_NET_WORTH_SNAPSHOTS,
)

from app.sheets.client import append_row, get_all_records, get_sheet
from app.services.transaction_service import get_all_accounts


ASSET_COLUMNS = [
    "id",
    "name",
    "category",
    "current_value",
    "description",
    "is_active",
    "created_at",
    "updated_at",
]


LIABILITY_COLUMNS = [
    "id",
    "name",
    "category",
    "current_balance",
    "description",
    "is_active",
    "created_at",
    "updated_at",
]


NET_WORTH_SNAPSHOT_COLUMNS = [
    "id",
    "snapshot_date",
    "total_accounts",
    "total_assets",
    "total_liabilities",
    "net_worth",
    "created_at",
]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def generate_id(prefix: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = uuid.uuid4().hex[:6]
    return f"{prefix}_{timestamp}_{suffix}"


def safe_float(value) -> float:
    try:
        if isinstance(value, str):
            value = value.replace(".", "").replace(",", "")
        return float(value or 0)
    except Exception:
        return 0.0


def is_active_record(record: dict) -> bool:
    return str(record.get("is_active", "")).strip().upper() == "TRUE"


def build_asset_row(asset: dict) -> list:
    return [asset.get(col, "") for col in ASSET_COLUMNS]


def build_liability_row(liability: dict) -> list:
    return [liability.get(col, "") for col in LIABILITY_COLUMNS]


def build_snapshot_row(snapshot: dict) -> list:
    return [snapshot.get(col, "") for col in NET_WORTH_SNAPSHOT_COLUMNS]


def add_asset(
    name: str,
    current_value: float,
    category: str = "Other Asset",
    description: str = "",
) -> dict:
    current_value = safe_float(current_value)

    if current_value <= 0:
        raise ValueError("Nilai aset harus lebih dari 0.")

    created_at = now_str()

    asset = {
        "id": generate_id("asset"),
        "name": str(name or "").strip(),
        "category": str(category or "Other Asset").strip(),
        "current_value": current_value,
        "description": str(description or "").strip(),
        "is_active": "TRUE",
        "created_at": created_at,
        "updated_at": created_at,
    }

    if not asset["name"]:
        raise ValueError("Nama aset wajib diisi.")

    append_row(SHEET_ASSETS, build_asset_row(asset))

    return asset


def add_liability(
    name: str,
    current_balance: float,
    category: str = "Other Liability",
    description: str = "",
) -> dict:
    current_balance = safe_float(current_balance)

    if current_balance <= 0:
        raise ValueError("Nominal liabilitas harus lebih dari 0.")

    created_at = now_str()

    liability = {
        "id": generate_id("liab"),
        "name": str(name or "").strip(),
        "category": str(category or "Other Liability").strip(),
        "current_balance": current_balance,
        "description": str(description or "").strip(),
        "is_active": "TRUE",
        "created_at": created_at,
        "updated_at": created_at,
    }

    if not liability["name"]:
        raise ValueError("Nama liabilitas wajib diisi.")

    append_row(SHEET_LIABILITIES, build_liability_row(liability))

    return liability


def get_assets(active_only: bool = True) -> list[dict]:
    records = get_all_records(SHEET_ASSETS)

    if not active_only:
        return records

    return [r for r in records if is_active_record(r)]


def get_liabilities(active_only: bool = True) -> list[dict]:
    records = get_all_records(SHEET_LIABILITIES)

    if not active_only:
        return records

    return [r for r in records if is_active_record(r)]


def get_record_by_id(sheet_name: str, record_id: str) -> dict | None:
    records = get_all_records(sheet_name)

    for record in records:
        if str(record.get("id", "")).strip() == str(record_id).strip():
            return record

    return None


def find_record_row_index(sheet_name: str, record_id: str) -> int | None:
    records = get_all_records(sheet_name)

    for idx, record in enumerate(records, start=2):
        if str(record.get("id", "")).strip() == str(record_id).strip():
            return idx

    return None


def update_record_cells(
    sheet_name: str,
    columns: list[str],
    record_id: str,
    updates: dict,
) -> bool:
    row_index = find_record_row_index(sheet_name, record_id)

    if not row_index:
        return False

    sheet = get_sheet(sheet_name)

    for field, value in updates.items():
        if field not in columns:
            continue

        col_index = columns.index(field) + 1
        sheet.update_cell(row_index, col_index, value)

    return True


def normalize_asset_update_field(field: str) -> str | None:
    key = str(field or "").strip().lower()

    aliases = {
        "name": "name",
        "nama": "name",

        "category": "category",
        "kategori": "category",

        "value": "current_value",
        "nilai": "current_value",
        "current_value": "current_value",
        "amount": "current_value",
        "nominal": "current_value",

        "description": "description",
        "deskripsi": "description",
        "desc": "description",
        "keterangan": "description",

        "active": "is_active",
        "is_active": "is_active",
        "aktif": "is_active",
    }

    return aliases.get(key)


def normalize_liability_update_field(field: str) -> str | None:
    key = str(field or "").strip().lower()

    aliases = {
        "name": "name",
        "nama": "name",

        "category": "category",
        "kategori": "category",

        "balance": "current_balance",
        "current_balance": "current_balance",
        "amount": "current_balance",
        "nominal": "current_balance",
        "sisa": "current_balance",

        "description": "description",
        "deskripsi": "description",
        "desc": "description",
        "keterangan": "description",

        "active": "is_active",
        "is_active": "is_active",
        "aktif": "is_active",
    }

    return aliases.get(key)


def normalize_common_update_value(field: str, value):
    raw = str(value or "").strip()

    if field in ["current_value", "current_balance"]:
        amount = safe_float(raw)

        if amount < 0:
            raise ValueError("Nominal tidak boleh negatif.")

        return amount

    if field == "is_active":
        clean = raw.lower()

        if clean in ["true", "1", "yes", "ya", "aktif", "on"]:
            return "TRUE"

        if clean in ["false", "0", "no", "tidak", "nonaktif", "off"]:
            return "FALSE"

        raise ValueError("Status aktif hanya boleh TRUE/FALSE atau on/off.")

    return raw


def update_asset(asset_id: str, updates: dict) -> dict:
    asset = get_record_by_id(SHEET_ASSETS, asset_id)

    if not asset:
        return {
            "success": False,
            "before": {},
            "after": {},
            "updates": {},
            "message": "Asset tidak ditemukan.",
        }

    normalized_updates = {}

    for raw_field, raw_value in updates.items():
        field = normalize_asset_update_field(raw_field)

        if not field:
            raise ValueError(f"Field `{raw_field}` tidak dikenali.")

        if field in ["id", "created_at", "updated_at"]:
            raise ValueError(f"Field `{field}` tidak boleh diedit.")

        normalized_updates[field] = normalize_common_update_value(field, raw_value)

    normalized_updates["updated_at"] = now_str()

    success = update_record_cells(
        SHEET_ASSETS,
        ASSET_COLUMNS,
        asset_id,
        normalized_updates,
    )

    if not success:
        return {
            "success": False,
            "before": asset,
            "after": {},
            "updates": normalized_updates,
            "message": "Gagal update asset.",
        }

    updated_asset = get_record_by_id(SHEET_ASSETS, asset_id) or {}

    return {
        "success": True,
        "before": asset,
        "after": updated_asset,
        "updates": normalized_updates,
        "message": "Asset berhasil diupdate.",
    }


def update_liability(liability_id: str, updates: dict) -> dict:
    liability = get_record_by_id(SHEET_LIABILITIES, liability_id)

    if not liability:
        return {
            "success": False,
            "before": {},
            "after": {},
            "updates": {},
            "message": "Liability tidak ditemukan.",
        }

    normalized_updates = {}

    for raw_field, raw_value in updates.items():
        field = normalize_liability_update_field(raw_field)

        if not field:
            raise ValueError(f"Field `{raw_field}` tidak dikenali.")

        if field in ["id", "created_at", "updated_at"]:
            raise ValueError(f"Field `{field}` tidak boleh diedit.")

        normalized_updates[field] = normalize_common_update_value(field, raw_value)

    normalized_updates["updated_at"] = now_str()

    success = update_record_cells(
        SHEET_LIABILITIES,
        LIABILITY_COLUMNS,
        liability_id,
        normalized_updates,
    )

    if not success:
        return {
            "success": False,
            "before": liability,
            "after": {},
            "updates": normalized_updates,
            "message": "Gagal update liability.",
        }

    updated_liability = get_record_by_id(SHEET_LIABILITIES, liability_id) or {}

    return {
        "success": True,
        "before": liability,
        "after": updated_liability,
        "updates": normalized_updates,
        "message": "Liability berhasil diupdate.",
    }


def deactivate_asset(asset_id: str) -> bool:
    return update_record_cells(
        SHEET_ASSETS,
        ASSET_COLUMNS,
        asset_id,
        {
            "is_active": "FALSE",
            "updated_at": now_str(),
        },
    )


def deactivate_liability(liability_id: str) -> bool:
    return update_record_cells(
        SHEET_LIABILITIES,
        LIABILITY_COLUMNS,
        liability_id,
        {
            "is_active": "FALSE",
            "updated_at": now_str(),
        },
    )


def calculate_net_worth() -> dict:
    accounts = get_all_accounts()
    assets = get_assets(active_only=True)
    liabilities = get_liabilities(active_only=True)

    total_accounts = sum(
        safe_float(acc.get("balance", 0))
        for acc in accounts
    )

    total_assets = sum(
        safe_float(asset.get("current_value", 0))
        for asset in assets
    )

    total_liabilities = sum(
        safe_float(liability.get("current_balance", 0))
        for liability in liabilities
    )

    net_worth = total_accounts + total_assets - total_liabilities

    return {
        "total_accounts": total_accounts,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth,
        "accounts": accounts,
        "assets": assets,
        "liabilities": liabilities,
    }


def create_net_worth_snapshot() -> dict:
    summary = calculate_net_worth()

    snapshot = {
        "id": generate_id("nws"),
        "snapshot_date": today_str(),
        "total_accounts": summary["total_accounts"],
        "total_assets": summary["total_assets"],
        "total_liabilities": summary["total_liabilities"],
        "net_worth": summary["net_worth"],
        "created_at": now_str(),
    }

    append_row(SHEET_NET_WORTH_SNAPSHOTS, build_snapshot_row(snapshot))

    return snapshot


def get_net_worth_snapshots(limit: int = 12) -> list[dict]:
    records = get_all_records(SHEET_NET_WORTH_SNAPSHOTS)
    records = list(reversed(records))

    return records[:limit]