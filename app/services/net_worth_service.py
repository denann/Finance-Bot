"""Net worth and asset service for assets, snapshots, active values, and historical net worth calculation."""


# Import re for this module's local operations.
import re
# Import urllib.request for this module's local operations.
import urllib.request
# Import uuid for this module's local operations.
import uuid
# Import datetime so this module can use its helpers.
from datetime import datetime

# Import app.config so this module can use its helpers.
from app.config import (
    SHEET_ASSETS,
    SHEET_NET_WORTH_SNAPSHOTS,
)

# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import append_row, get_all_records, update_cell
# Import app.services.transaction_service so this module can use its helpers.
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
    # Schema compatibility note for Google Sheets headers and rows.
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

LIABILITY_FEATURE_REMOVED_MESSAGE = (
    "Fitur liabilities sudah tidak aktif. "
    "Kewajiban antar orang dikelola lewat /hutang, sedangkan net worth hanya memakai saldo rekening + aset aktif."
)


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


# Helper for generate id.
def generate_id(prefix: str) -> str:
    """Coordinate the generate id logic in the service layer.

    Args:
        prefix: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = uuid.uuid4().hex[:6]
    return f"{prefix}_{timestamp}_{suffix}"


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
        if isinstance(value, str):
            value = value.replace(".", "").replace(",", "")
        return float(value or 0)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return 0.0


# Helper for safe float decimal.
def safe_float_decimal(value) -> float:
    """Coordinate the safe float decimal logic in the service layer.

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
        raw = str(value or "").strip().lower()
        raw = raw.replace("gram", "").replace("gr", "").replace("g", "")
        raw = raw.replace(",", ".")
        raw = re.sub(r"[^0-9.]", "", raw)

        if raw.count(".") > 1:
            first, *rest = raw.split(".")
            raw = first + "." + "".join(rest)

        return float(raw or 0)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return 0.0


# Helper for parse human money.
def parse_human_money(value) -> float:
    """Parse caller input for the parse human money workflow in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    raw = str(value or "").strip().lower()
    # Validate missing raw before continuing.
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


# Helper for normalize date value.
def normalize_date_value(value) -> str:
    """Normalize input values for the normalize date value workflow in the service layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    raw = str(value or "").strip()
    # Validate missing raw before continuing.
    if not raw:
        return ""

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", raw):
        y, m, d = raw.split("-")
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    # Konversi 10/06/2026 or 10-06-2026 into ISO.
    match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", raw)
    if match:
        d, m, y = match.groups()
        y = int(y)
        if y < 100:
            y += 2000
        return f"{y:04d}-{int(m):02d}-{int(d):02d}"

    return raw


# Helper for calculate asset gain.
def calculate_asset_gain(asset: dict) -> dict:
    """Coordinate the calculate asset gain logic in the service layer.

    Args:
        asset: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
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


# Helper for parse price to float.
def parse_price_to_float(value) -> float:
    """Parse caller input for the parse price to float workflow in the service layer.

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
        raw = str(value or "").strip()
        raw = re.sub(r"[^0-9]", "", raw)
        return float(raw or 0)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return 0.0


# Helper for fetch antam buyback price.
def fetch_antam_buyback_price() -> dict:
    """Coordinate the fetch antam buyback price logic in the service layer.

    Args:
        None.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    url = "https://www.logammulia.com/sell/gold"

    # Run this operation in a guarded block so failures can be handled.
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

        # Use a managed resource so it is closed after this operation.
        with urllib.request.urlopen(request, timeout=12) as response:
            html = response.read().decode("utf-8", errors="ignore")

        patterns = [
            r"Harga\s+Buyback[^0-9]{0,80}Rp\s*([0-9.,]+)",
            r"Buyback[^0-9]{0,80}Rp\s*([0-9.,]+)",
        ]

        price = 0.0
        # Iterate through each pattern.
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            if match:
                price = parse_price_to_float(match.group(1))
                # Leave the loop after the target condition has been reached.
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

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {
            "success": False,
            "price_per_gram": 0,
            "source": "antam_buyback",
            "source_url": url,
            "updated_at": now_str(),
            "message": str(e),
        }


# Helper for is gold asset.
def is_gold_asset(record: dict) -> bool:
    """Check whether a condition is true for gold asset."""
    asset_type = str(record.get("asset_type", "")).strip().lower()
    category = str(record.get("category", "")).strip().lower()
    unit = str(record.get("unit", "")).strip().lower()

    return (
        asset_type == "gold"
        or category in ["gold", "emas", "precious metal", "logam mulia"]
        or unit in ["g", "gr", "gram"]
    )


# Helper for is active record.
def is_active_record(record: dict) -> bool:
    """Check whether a condition is true for active record."""
    return str(record.get("is_active", "")).strip().upper() == "TRUE"


# Helper for build asset row.
def build_asset_row(asset: dict) -> list:
    """Build the data structure or message text for asset row."""
    return [asset.get(col, "") for col in ASSET_COLUMNS]


# Helper for build liability row.
def build_liability_row(liability: dict) -> list:
    """Build the data structure or message text for liability row."""
    return [liability.get(col, "") for col in LIABILITY_COLUMNS]


# Helper for build snapshot row.
def build_snapshot_row(snapshot: dict) -> list:
    """Build the data structure or message text for snapshot row."""
    return [snapshot.get(col, "") for col in NET_WORTH_SNAPSHOT_COLUMNS]


# Helper for add asset.
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
    """Coordinate the add asset logic in the service layer.

    Args:
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        current_value: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        category: Category name or category-like value from user input or sheet data.
        description: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        asset_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        quantity: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        unit: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        price_source: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        price_per_unit: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        purchase_price_per_unit: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        purchase_date: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    asset_type = str(asset_type or "manual").strip().lower()
    category = str(category or "Other Asset").strip()
    unit = str(unit or "").strip()
    price_source = str(price_source or "").strip().lower()

    quantity_value = safe_float_decimal(quantity) if quantity not in [None, ""] else 0.0
    unit_price = safe_float(price_per_unit) if price_per_unit not in [None, ""] else 0.0
    purchase_unit_price = safe_float(purchase_price_per_unit) if purchase_price_per_unit not in [None, ""] else ""
    # Extract purchase date value for validation.
    purchase_date_value = normalize_date_value(purchase_date)

    # Asset flow section
    if quantity_value > 0 or unit or unit_price > 0:
        if quantity_value <= 0:
            raise ValueError("Quantity aset harus lebih dari 0. Contoh: `999 gram` atau `1 buah`.")

        # Validate missing unit before continuing.
        if not unit:
            raise ValueError("Satuan aset wajib diisi. Contoh: `gram`, `buah`, `unit`.")

        if unit_price <= 0:
            raise ValueError("Harga satuan aset harus lebih dari 0.")

        current_value = quantity_value * unit_price

        if asset_type == "manual":
            asset_type = "unit"

        # Validate missing price source before continuing.
        if not price_source:
            price_source = "manual"

    # Use the fallback path when no earlier branch matched.
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


# Helper for add liability.
def add_liability(
    name: str,
    current_balance: float,
    category: str = "Other Liability",
    description: str = "",
) -> dict:
    """Coordinate the add liability logic in the service layer.

    Args:
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        current_balance: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        category: Category name or category-like value from user input or sheet data.
        description: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Raise a clear error so the caller can stop this invalid flow.
    raise NotImplementedError(LIABILITY_FEATURE_REMOVED_MESSAGE)

# Helper for refresh gold assets.
def refresh_gold_assets(records: list[dict]) -> list[dict]:
    """Coordinate the refresh gold assets logic in the service layer.

    Args:
        records: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return records


# Helper for get assets.
def get_assets(active_only: bool = True, refresh_gold: bool = True) -> list[dict]:
    """Retrieve data needed by the get assets workflow in the service layer.

    Args:
        active_only: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        refresh_gold: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Load records for the current calculation.
    records = get_all_records(SHEET_ASSETS)

    if refresh_gold:
        # Load records for the current calculation.
        records = refresh_gold_assets(records)

    # Validate missing active only before continuing.
    if not active_only:
        return records

    return [r for r in records if is_active_record(r)]


# Helper for get liabilities.
def get_liabilities(active_only: bool = True) -> list[dict]:
    """Retrieve data needed by the get liabilities workflow in the service layer.

    Args:
        active_only: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return []

# Helper for get record by id.
def get_record_by_id(sheet_name: str, record_id: str) -> dict | None:
    """Retrieve data needed by the get record by id workflow in the service layer.

    Args:
        sheet_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        record_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Load records for the current calculation.
    records = get_all_records(sheet_name)

    # Iterate through each record.
    for record in records:
        if str(record.get("id", "")).strip() == str(record_id).strip():
            return record

    return None


# Helper for find record row index.
def find_record_row_index(sheet_name: str, record_id: str) -> int | None:
    """Coordinate the find record row index logic in the service layer.

    Args:
        sheet_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        record_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `int | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Load records for the current calculation.
    records = get_all_records(sheet_name)

    # Iterate through each idx, record.
    for idx, record in enumerate(records, start=2):
        if str(record.get("id", "")).strip() == str(record_id).strip():
            return idx

    return None


# Helper for update record cells.
def update_record_cells(
    sheet_name: str,
    columns: list[str],
    record_id: str,
    updates: dict,
) -> bool:
    """Apply the update record cells operation in the service layer.

    Args:
        sheet_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        columns: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        record_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        updates: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    row_index = find_record_row_index(sheet_name, record_id)

    # Validate missing row index before continuing.
    if not row_index:
        return False

    # Iterate through each field, value.
    for field, value in updates.items():
        if field not in columns:
            # Skip the rest of this loop iteration after handling this case.
            continue

        col_index = columns.index(field) + 1
        update_cell(sheet_name, row_index, col_index, value)

    return True


# Helper for normalize asset update field.
def normalize_asset_update_field(field: str) -> str | None:
    """Normalize input values for the normalize asset update field workflow in the service layer.

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


# Helper for normalize liability update field.
def normalize_liability_update_field(field: str) -> str | None:
    """Normalize input values for the normalize liability update field workflow in the service layer.

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


# Helper for normalize common update value.
def normalize_common_update_value(field: str, value):
    """Normalize input values for the normalize common update value workflow in the service layer.

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
    raw = str(value or "").strip()

    if field in ["current_value", "current_balance", "price_per_unit", "purchase_price_per_unit"]:
        # Extract amount for validation.
        amount = parse_human_money(raw)

        if amount < 0:
            raise ValueError("Nominal tidak boleh negatif.")

        return amount

    if field == "purchase_date":
        return normalize_date_value(raw)

    if field == "quantity":
        # Extract amount for validation.
        amount = safe_float_decimal(raw)

        if amount < 0:
            raise ValueError("Quantity tidak boleh negatif.")

        return amount

    if field == "is_active":
        # Normalize clean before matching.
        clean = raw.lower()

        if clean in ["true", "1", "yes", "ya", "aktif", "on"]:
            return "TRUE"

        if clean in ["false", "0", "no", "tidak", "nonaktif", "off"]:
            return "FALSE"

        raise ValueError("Status aktif hanya boleh TRUE/FALSE atau on/off.")

    return raw


# Helper for update asset.
def update_asset(asset_id: str, updates: dict) -> dict:
    """Apply the update asset operation in the service layer.

    Args:
        asset_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        updates: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    asset = get_record_by_id(SHEET_ASSETS, asset_id)

    # Validate missing asset before continuing.
    if not asset:
        return {
            "success": False,
            "before": {},
            "after": {},
            "updates": {},
            "message": "Asset tidak ditemukan.",
        }

    # Normalize normalized updates before matching.
    normalized_updates = {}

    # Iterate through each raw field, raw value.
    for raw_field, raw_value in updates.items():
        field = normalize_asset_update_field(raw_field)

        # Validate missing field before continuing.
        if not field:
            raise ValueError(f"Field `{raw_field}` tidak dikenali.")

        if field in ["id", "created_at", "updated_at"]:
            raise ValueError(f"Field `{field}` tidak boleh diedit.")

        normalized_updates[field] = normalize_common_update_value(field, raw_value)

    merged_asset = dict(asset)
    # Append the current value to merged asset.
    merged_asset.update(normalized_updates)

    if is_gold_asset(merged_asset):
        quantity = safe_float_decimal(merged_asset.get("quantity"))
        price = safe_float(merged_asset.get("price_per_unit"))

        # Handle quantity > 0 and price > 0.
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

    # Validate missing success before continuing.
    if not success:
        return {
            "success": False,
            "before": asset,
            "after": {},
            "updates": normalized_updates,
            "message": "Gagal update asset.",
        }

    # Extract updated asset for validation.
    updated_asset = get_record_by_id(SHEET_ASSETS, asset_id) or {}

    return {
        "success": True,
        "before": asset,
        "after": updated_asset,
        "updates": normalized_updates,
        "message": "Asset berhasil diupdate.",
    }


# Helper for update liability.
def update_liability(liability_id: str, updates: dict) -> dict:
    """Apply the update liability operation in the service layer.

    Args:
        liability_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        updates: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    return {
        "success": False,
        "before": {},
        "after": {},
        "updates": {},
        "message": LIABILITY_FEATURE_REMOVED_MESSAGE,
    }

# Helper for deactivate asset.
def deactivate_asset(asset_id: str) -> bool:
    """Coordinate the deactivate asset logic in the service layer.

    Args:
        asset_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return update_record_cells(
        SHEET_ASSETS,
        ASSET_COLUMNS,
        asset_id,
        {
            "is_active": "FALSE",
            "updated_at": now_str(),
        },
    )


# Helper for deactivate liability.
def deactivate_liability(liability_id: str) -> bool:
    """Coordinate the deactivate liability logic in the service layer.

    Args:
        liability_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return False

# Helper for calculate net worth.
def calculate_net_worth() -> dict:
    """Coordinate the calculate net worth logic in the service layer.

    Args:
        None.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Extract accounts for validation.
    accounts = get_all_accounts()
    assets = get_assets(active_only=True)

    total_accounts = sum(
        safe_float(acc.get("balance", 0))
        # Iterate through each acc.
        for acc in accounts
    )

    total_assets = sum(
        safe_float(asset.get("current_value", 0))
        # Iterate through each asset.
        for asset in assets
    )

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

# Helper for create net worth snapshot.
def create_net_worth_snapshot(summary: dict | None = None) -> dict:
    """Coordinate the create net worth snapshot logic in the service layer.

    Args:
        summary: Optional immutable totals shown in the confirmed preview. When
            omitted, totals are calculated using the existing behavior.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Build summary for the response flow.
    summary = dict(summary or calculate_net_worth())

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


# Helper for get net worth snapshots.
def get_net_worth_snapshots(limit: int = 12) -> list[dict]:
    """Retrieve data needed by the get net worth snapshots workflow in the service layer.

    Args:
        limit: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Load records for the current calculation.
    records = get_all_records(SHEET_NET_WORTH_SNAPSHOTS)
    # Load records for the current calculation.
    records = list(reversed(records))

    # Keep this section separated from the surrounding flow.
