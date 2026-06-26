import re
import urllib.request
import uuid
from datetime import datetime

from app.config import (
    SHEET_ASSETS,
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
    # Optional columns for auto-valued assets such as gold.
    # Add these headers to the assets sheet to make gold auto valuation work.
    "asset_type",
    "quantity",
    "unit",
    "price_source",
    "price_per_unit",
    "last_price_update",
    "purchase_price_per_unit",
    "purchase_date",
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


def safe_float_decimal(value) -> float:
    """Parse decimal values such as 41, 41.5, 41,5 without treating dot as thousands."""
    try:
        raw = str(value or "").strip().lower()
        raw = raw.replace("gram", "").replace("gr", "").replace("g", "")
        raw = raw.replace(",", ".")
        raw = re.sub(r"[^0-9.]", "", raw)

        if raw.count(".") > 1:
            first, *rest = raw.split(".")
            raw = first + "." + "".join(rest)

        return float(raw or 0)
    except Exception:
        return 0.0


def parse_human_money(value) -> float:
    """Parse 2420000, 2.42 juta, 2,42jt, 91.457k for manual asset prices."""
    raw = str(value or "").strip().lower()
    if not raw:
        return 0.0

    multiplier = 1
    if re.search(r"\b(jt|juta)\b", raw):
        multiplier = 1_000_000
    elif re.search(r"\b(rb|ribu|k)\b", raw):
        multiplier = 1_000

    raw = re.sub(r"\b(jt|juta|rb|ribu|k)\b", "", raw).strip()

    if multiplier != 1:
        raw = raw.replace(",", ".")
        raw = re.sub(r"[^0-9.]", "", raw)
        if raw.count(".") > 1:
            first, *rest = raw.split(".")
            raw = first + "." + "".join(rest)
        return float(raw or 0) * multiplier

    raw = re.sub(r"[^0-9]", "", raw)
    return float(raw or 0)


def normalize_date_value(value) -> str:
    """Normalize common Indonesian date inputs to YYYY-MM-DD when possible."""
    raw = str(value or "").strip()
    if not raw:
        return ""

    # Keep already valid ISO date.
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", raw):
        y, m, d = raw.split("-")
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    # Convert 10/06/2026 or 10-06-2026 into ISO.
    match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", raw)
    if match:
        d, m, y = match.groups()
        y = int(y)
        if y < 100:
            y += 2000
        return f"{y:04d}-{int(m):02d}-{int(d):02d}"

    return raw


def calculate_asset_gain(asset: dict) -> dict:
    """Return acquisition cost, gain/loss, and gain percentage for one asset."""
    current_value = safe_float(asset.get("current_value", 0))
    quantity = safe_float_decimal(asset.get("quantity"))
    purchase_price = safe_float(asset.get("purchase_price_per_unit", 0))

    if purchase_price <= 0:
        return {
            "has_purchase_info": False,
            "purchase_price_per_unit": 0.0,
            "purchase_total": 0.0,
            "gain_loss": 0.0,
            "gain_loss_pct": 0.0,
        }

    purchase_total = purchase_price * quantity if quantity > 0 else purchase_price
    gain_loss = current_value - purchase_total
    gain_loss_pct = (gain_loss / purchase_total * 100) if purchase_total > 0 else 0.0

    return {
        "has_purchase_info": True,
        "purchase_price_per_unit": purchase_price,
        "purchase_total": purchase_total,
        "gain_loss": gain_loss,
        "gain_loss_pct": gain_loss_pct,
    }


def parse_price_to_float(value) -> float:
    """Parse Indonesian price strings like Rp 2,594,000 or 2.594.000."""
    try:
        raw = str(value or "").strip()
        raw = re.sub(r"[^0-9]", "", raw)
        return float(raw or 0)
    except Exception:
        return 0.0


def fetch_antam_buyback_price() -> dict:
    """
    Fetch latest Antam buyback price per gram from Logam Mulia.

    Return:
    {
        "success": bool,
        "price_per_gram": float,
        "source": "antam_buyback",
        "source_url": str,
        "updated_at": str,
        "message": str,
    }

    Notes:
    - Website scraping can break if Logam Mulia changes its HTML.
    - Caller should keep the last known price when this function fails.
    """
    url = "https://www.logammulia.com/sell/gold"

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

        with urllib.request.urlopen(request, timeout=12) as response:
            html = response.read().decode("utf-8", errors="ignore")

        patterns = [
            r"Harga\s+Buyback[^0-9]{0,80}Rp\s*([0-9.,]+)",
            r"Buyback[^0-9]{0,80}Rp\s*([0-9.,]+)",
        ]

        price = 0.0
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            if match:
                price = parse_price_to_float(match.group(1))
                break

        # Guardrail so a broken parser does not write a nonsense value.
        if price < 500_000 or price > 5_000_000:
            return {
                "success": False,
                "price_per_gram": 0,
                "source": "antam_buyback",
                "source_url": url,
                "updated_at": now_str(),
                "message": "Harga buyback Antam tidak valid / tidak ditemukan.",
            }

        return {
            "success": True,
            "price_per_gram": price,
            "source": "antam_buyback",
            "source_url": url,
            "updated_at": now_str(),
            "message": "OK",
        }

    except Exception as e:
        return {
            "success": False,
            "price_per_gram": 0,
            "source": "antam_buyback",
            "source_url": url,
            "updated_at": now_str(),
            "message": str(e),
        }


def is_gold_asset(record: dict) -> bool:
    asset_type = str(record.get("asset_type", "")).strip().lower()
    category = str(record.get("category", "")).strip().lower()
    unit = str(record.get("unit", "")).strip().lower()

    return (
        asset_type == "gold"
        or category in ["gold", "emas", "precious metal", "logam mulia"]
        or unit in ["g", "gr", "gram"]
    )


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
    current_value: float | None,
    category: str = "Other Asset",
    description: str = "",
    asset_type: str = "manual",
    quantity: float | None = None,
    unit: str = "",
    price_source: str = "",
    price_per_unit: float | None = None,
    purchase_price_per_unit: float | None = None,
    purchase_date: str = "",
) -> dict:
    asset_type = str(asset_type or "manual").strip().lower()
    category = str(category or "Other Asset").strip()
    unit = str(unit or "").strip()
    price_source = str(price_source or "").strip().lower()

    quantity_value = safe_float_decimal(quantity) if quantity not in [None, ""] else 0.0
    unit_price = safe_float(price_per_unit) if price_per_unit not in [None, ""] else 0.0
    purchase_unit_price = safe_float(purchase_price_per_unit) if purchase_price_per_unit not in [None, ""] else ""
    purchase_date_value = normalize_date_value(purchase_date)

    # Aset berbasis satuan: emas 41 gram, laptop 1 buah, dll.
    # Nilai aset = quantity × price_per_unit. Tidak auto-scrape external source.
    if quantity_value > 0 or unit or unit_price > 0:
        if quantity_value <= 0:
            raise ValueError("Quantity aset harus lebih dari 0. Contoh: `41 gram` atau `1 buah`.")

        if not unit:
            raise ValueError("Satuan aset wajib diisi. Contoh: `gram`, `buah`, `unit`.")

        if unit_price <= 0:
            raise ValueError("Harga satuan aset harus lebih dari 0.")

        current_value = quantity_value * unit_price

        if asset_type == "manual":
            asset_type = "unit"

        if not price_source:
            price_source = "manual"

    else:
        current_value = safe_float(current_value)
        quantity_value = ""
        unit = ""
        unit_price = ""
        price_source = ""

    if safe_float(current_value) <= 0:
        raise ValueError("Nilai aset harus lebih dari 0.")

    created_at = now_str()

    asset = {
        "id": generate_id("asset"),
        "name": str(name or "").strip(),
        "category": category,
        "current_value": safe_float(current_value),
        "description": str(description or "").strip(),
        "is_active": "TRUE",
        "created_at": created_at,
        "updated_at": created_at,
        "asset_type": asset_type,
        "quantity": quantity_value,
        "unit": unit,
        "price_source": price_source,
        "price_per_unit": unit_price,
        "last_price_update": today_str() if unit_price else "",
        "purchase_price_per_unit": purchase_unit_price,
        "purchase_date": purchase_date_value,
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


def refresh_gold_assets(records: list[dict]) -> list[dict]:
    """Deprecated auto-refresh hook.

    Harga aset sekarang dikelola manual lewat price_per_unit/unit_price agar
    bot tidak bergantung scraping website eksternal yang bisa kena 403.
    Fungsi ini sengaja tidak mengubah records.
    """
    return records


def get_assets(active_only: bool = True, refresh_gold: bool = True) -> list[dict]:
    records = get_all_records(SHEET_ASSETS)

    if refresh_gold:
        records = refresh_gold_assets(records)

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

        "asset_type": "asset_type",
        "type": "asset_type",
        "jenis": "asset_type",
        "quantity": "quantity",
        "qty": "quantity",
        "berat": "quantity",
        "unit": "unit",
        "satuan": "unit",
        "price_source": "price_source",
        "sumber_harga": "price_source",
        "price_per_unit": "price_per_unit",
        "unit_price": "price_per_unit",
        "harga_per_unit": "price_per_unit",
        "harga_satuan": "price_per_unit",
        "harga": "price_per_unit",
        "last_price_update": "last_price_update",
        "purchase_price_per_unit": "purchase_price_per_unit",
        "purchase_price": "purchase_price_per_unit",
        "buy_price": "purchase_price_per_unit",
        "harga_beli": "purchase_price_per_unit",
        "modal": "purchase_price_per_unit",
        "purchase_date": "purchase_date",
        "buy_date": "purchase_date",
        "tanggal_beli": "purchase_date",
        "tgl_beli": "purchase_date",

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

    if field in ["current_value", "current_balance", "price_per_unit", "purchase_price_per_unit"]:
        amount = parse_human_money(raw)

        if amount < 0:
            raise ValueError("Nominal tidak boleh negatif.")

        return amount

    if field == "purchase_date":
        return normalize_date_value(raw)

    if field == "quantity":
        amount = safe_float_decimal(raw)

        if amount < 0:
            raise ValueError("Quantity tidak boleh negatif.")

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

    merged_asset = dict(asset)
    merged_asset.update(normalized_updates)

    if is_gold_asset(merged_asset):
        quantity = safe_float_decimal(merged_asset.get("quantity"))
        price = safe_float(merged_asset.get("price_per_unit"))

        if quantity > 0 and price > 0:
            normalized_updates["current_value"] = quantity * price
            if "price_per_unit" in normalized_updates:
                normalized_updates["last_price_update"] = today_str()

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

    total_accounts = sum(
        safe_float(acc.get("balance", 0))
        for acc in accounts
    )

    total_assets = sum(
        safe_float(asset.get("current_value", 0))
        for asset in assets
    )

    # Liabilities sudah dihapus dari konsep bot.
    # Kewajiban personal antar orang tetap dikelola melalui fitur /hutang.
    total_liabilities = 0.0
    net_worth = total_accounts + total_assets

    return {
        "total_accounts": total_accounts,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth,
        "accounts": accounts,
        "assets": assets,
        "liabilities": [],
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