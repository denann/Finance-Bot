from datetime import datetime, date, timedelta
import re

from app.sheets.client import (
    append_row_raw,
    get_all_records,
    update_cell,
)
from app.config import SHEET_BUDGETS, SHEET_TRANSACTIONS


# ── Constants ─────────────────────────────────────────────────────────────────

DEBT_CASHFLOW_CATEGORIES = {
    "Piutang Diberikan",
    "Pembayaran Piutang",
    "Penerimaan Utang",
    "Bayar Utang",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_current_month() -> str:
    """Kembalikan bulan ini dalam format YYYY-MM."""
    return datetime.now().strftime("%Y-%m")


def normalize_month(month: str | None = None) -> str:
    """
    Normalisasi bulan ke format YYYY-MM.

    Mendukung:
    - None          -> bulan sekarang
    - 2026-06
    - 2026/06
    - 2026 06
    """
    if not month:
        return get_current_month()

    month = str(month).strip()
    month = month.replace("/", "-")
    month = re.sub(r"\s+", "-", month)

    match = re.fullmatch(r"(\d{4})-(\d{1,2})", month)
    if not match:
        raise ValueError("Format bulan harus YYYY-MM. Contoh: 2026-06")

    year = int(match.group(1))
    month_num = int(match.group(2))

    if month_num < 1 or month_num > 12:
        raise ValueError("Bulan harus antara 1 sampai 12.")

    return f"{year}-{month_num:02d}"




def normalize_sheet_month_value(value) -> str:
    """
    Normalisasi nilai month dari Google Sheets ke format YYYY-MM.

    Kenapa perlu:
    - Google Sheets bisa auto-convert `2026-06` menjadi date/serial number.
    - Data lama bisa tersimpan sebagai `2026-06-01` atau format date lain.
    """
    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%Y-%m")

    if isinstance(value, date):
        return value.strftime("%Y-%m")

    if isinstance(value, (int, float)):
        try:
            # Google Sheets/Excel serial date origin.
            # `2026-06` yang terlanjur dianggap tanggal biasanya terbaca sebagai serial number.
            dt = datetime(1899, 12, 30) + timedelta(days=float(value))
            if 1990 <= dt.year <= 2100:
                return dt.strftime("%Y-%m")
        except Exception:
            pass
        return str(value).strip()

    raw = str(value).strip()
    if not raw:
        return ""

    raw = raw.replace("/", "-")

    # 2026-06 atau 2026-6
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", raw)
    if match:
        return normalize_month(f"{match.group(1)}-{match.group(2)}")

    # 2026-06-01, 2026-6-1, atau format date dari Google Sheets.
    match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:\s+.*)?", raw)
    if match:
        return normalize_month(f"{match.group(1)}-{match.group(2)}")

    # Kalau gspread mengembalikan display value seperti Jun 2026 / June 2026.
    for fmt in ("%b %Y", "%B %Y", "%Y %B", "%Y %b"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m")
        except Exception:
            pass

    return raw

def format_month_label(month: str) -> str:
    """Ubah YYYY-MM menjadi label singkat."""
    month = normalize_month(month)
    dt = datetime.strptime(month, "%Y-%m")
    return dt.strftime("%B %Y")


def format_rupiah(amount: float) -> str:
    return f"Rp{int(float(amount or 0)):,}".replace(",", ".")


def get_budget_status_emoji(pct_used: float) -> str:
    if pct_used >= 100:
        return "🔴"
    elif pct_used >= 80:
        return "🟠"
    elif pct_used >= 50:
        return "🟡"
    else:
        return "🟢"


def generate_budget_id(month: str, category: str) -> str:
    clean_category = re.sub(r"[^a-zA-Z0-9]+", "_", category.strip().lower())
    clean_category = clean_category.strip("_")
    return f"budget_{month}_{clean_category}"


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except Exception:
        return default


# ── Budget CRUD ───────────────────────────────────────────────────────────────

def set_budget(category: str, amount: float, month: str = None) -> dict:
    """
    Atur atau perbarui budget untuk kategori tertentu pada bulan tertentu.

    Sheet budgets disarankan punya header:
    id | month | category | budget_amount | created_at | updated_at

    Kalau sheet lama kamu masih:
    month | category | budget_amount | created_at

    sebaiknya ubah header-nya dulu agar cocok dengan versi ini.
    """
    month = normalize_month(month)
    amount = float(amount or 0)

    if amount <= 0:
        return {
            "success": False,
            "action": "failed",
            "message": "Nominal budget harus lebih dari 0.",
        }

    records = get_all_records(SHEET_BUDGETS)
    today = datetime.now().strftime("%Y-%m-%d")

    for i, record in enumerate(records):
        record_month = normalize_sheet_month_value(record.get("month", ""))
        record_category = str(record.get("category", "")).strip().lower()

        if record_month == month and record_category == category.strip().lower():
            row_index = i + 2

            # Header:
            # 1=id, 2=month, 3=category, 4=budget_amount, 5=created_at, 6=updated_at
            update_cell(SHEET_BUDGETS, row_index, 4, amount)
            update_cell(SHEET_BUDGETS, row_index, 6, today)

            return {
                "success": True,
                "action": "updated",
                "month": month,
                "category": category,
                "amount": amount,
                "message": f"Budget {category} untuk {month} diupdate ke {format_rupiah(amount)}",
            }

    budget_id = generate_budget_id(month, category)

    row = [
        budget_id,
        month,
        category,
        amount,
        today,
        today,
    ]

    append_row_raw(SHEET_BUDGETS, row)

    return {
        "success": True,
        "action": "created",
        "month": month,
        "category": category,
        "amount": amount,
        "message": f"Budget {category} untuk {month} diset {format_rupiah(amount)}",
    }


def get_budget(category: str, month: str = None) -> float | None:
    """Ambil budget untuk kategori tertentu di bulan tertentu."""
    month = normalize_month(month)

    records = get_all_records(SHEET_BUDGETS)

    for record in records:
        record_month = normalize_sheet_month_value(record.get("month", ""))
        record_category = str(record.get("category", "")).strip().lower()

        if record_month == month and record_category == category.strip().lower():
            return safe_float(record.get("budget_amount", 0))

    return None


def get_all_budgets(month: str = None) -> list[dict]:
    """Ambil semua budget di bulan tertentu."""
    month = normalize_month(month)

    records = get_all_records(SHEET_BUDGETS)
    return [
        r for r in records
        if normalize_sheet_month_value(r.get("month", "")) == month
    ]


def get_budget_months() -> list[str]:
    """Ambil daftar bulan yang punya budget."""
    records = get_all_records(SHEET_BUDGETS)
    months = sorted({
        normalize_sheet_month_value(r.get("month", ""))
        for r in records
        if normalize_sheet_month_value(r.get("month", ""))
    })

    return months


# ── Realisasi vs Budget ───────────────────────────────────────────────────────

def budget_transaction_matches_category(record: dict, category: str) -> bool:
    """Cek apakah transaksi masuk ke budget category tertentu.

    Budget resmi dicocokkan dari kolom category. Budget custom seperti
    `Jajan` tetap bisa match dari description/raw_input.
    """
    budget_key = str(category or "").strip().lower()
    if not budget_key:
        return False

    txn_category = str((record or {}).get("category", "")).strip().lower()
    if txn_category == budget_key:
        return True

    desc = str((record or {}).get("description", "") or "").lower()
    raw = str((record or {}).get("raw_input", "") or "").lower()
    return bool(budget_key and (budget_key in desc or budget_key in raw))


def calculate_budget_actual_from_transactions(transactions: list[dict]) -> dict:
    """Hitung realisasi budget sebagai Bersih (Gross).

    Bersih = gross expense dikurangi piutang aktif yang menempel ke transaksi
    split bill. Ini sengaja disamakan dengan output `/transaksi`, supaya
    `/budget` tidak terlihat gross-only.
    """
    gross_total = 0.0
    net_total = 0.0

    for txn in transactions or []:
        if str((txn or {}).get("type", "")).strip().lower() != "expense":
            continue

        amount = safe_float((txn or {}).get("amount", 0))
        receivable = safe_float((txn or {}).get("debt_receivable_original", (txn or {}).get("debt_receivable_remaining", 0)))
        gross_total += amount
        net_total += max(amount - receivable, 0.0)

    return {"net": net_total, "gross": gross_total}


def get_actual_expense_breakdown(category: str, month: str = None) -> dict:
    """Hitung total pengeluaran bersih dan gross untuk kategori budget."""
    month = normalize_month(month)

    records = get_all_records(SHEET_TRANSACTIONS)
    matched = []

    for record in records:
        txn_type = str(record.get("type", "")).strip().lower()
        txn_date = str(record.get("date", "")).strip()

        if txn_type != "expense":
            continue
        if not txn_date.startswith(month):
            continue
        if not budget_transaction_matches_category(record, category):
            continue

        matched.append(dict(record or {}))

    if not matched:
        return {"net": 0.0, "gross": 0.0}

    # Import lokal supaya budget_service tidak punya circular import saat module load.
    from app.services.report_service import enrich_transactions_with_debt_info

    enriched = enrich_transactions_with_debt_info(matched)
    return calculate_budget_actual_from_transactions(enriched)


def get_actual_expense(category: str, month: str = None) -> float:
    """Kembalikan realisasi budget bersih untuk kategori tertentu."""
    return get_actual_expense_breakdown(category, month).get("net", 0.0)


def get_budget_summary(month: str = None) -> list[dict]:
    """
    Ambil ringkasan budget vs realisasi semua kategori pada bulan tertentu.

    Output `actual` = pengeluaran bersih.
    Output `actual_gross` = pengeluaran gross sebelum piutang aktif dikurangi.
    """
    month = normalize_month(month)

    budgets = get_all_budgets(month)
    result = []

    records = get_all_records(SHEET_TRANSACTIONS)
    monthly_expenses = []
    for record in records:
        txn_type = str(record.get("type", "")).strip().lower()
        txn_date = str(record.get("date", "")).strip()
        if txn_type == "expense" and txn_date.startswith(month):
            monthly_expenses.append(dict(record or {}))

    if monthly_expenses:
        # Import lokal supaya budget_service tidak punya circular import saat module load.
        from app.services.report_service import enrich_transactions_with_debt_info
        monthly_expenses = enrich_transactions_with_debt_info(monthly_expenses)

    for b in budgets:
        category = str(b.get("category", "")).strip()
        budget_amount = safe_float(b.get("budget_amount", 0))

        if not category:
            continue

        matched = [
            txn
            for txn in monthly_expenses
            if budget_transaction_matches_category(txn, category)
        ]
        actual_info = calculate_budget_actual_from_transactions(matched)
        actual = actual_info["net"]
        actual_gross = actual_info["gross"]
        remaining = budget_amount - actual
        pct_used = (actual / budget_amount * 100) if budget_amount > 0 else 0

        result.append({
            "month": month,
            "category": category,
            "budget": budget_amount,
            "actual": actual,
            "actual_gross": actual_gross,
            "remaining": remaining,
            "pct_used": round(pct_used, 1),
            "status": "over" if pct_used >= 100 else "warning" if pct_used >= 80 else "ok",
            "emoji": get_budget_status_emoji(pct_used),
        })

    result.sort(key=lambda x: x["pct_used"], reverse=True)
    return result


def check_budget_after_transaction(category: str, month: str = None) -> dict | None:
    """
    Dipanggil setiap kali ada transaksi expense masuk.
    Kembalikan info budget jika ada, None jika kategori tidak punya budget.
    """
    month = normalize_month(month)

    if category in DEBT_CASHFLOW_CATEGORIES:
        return None

    budget = get_budget(category, month)
    if budget is None:
        return None

    actual = get_actual_expense(category, month)
    remaining = budget - actual
    pct_used = (actual / budget * 100) if budget > 0 else 0
    emoji = get_budget_status_emoji(pct_used)

    alert = False
    alert_msg = ""

    if pct_used >= 100:
        alert = True
        alert_msg = f"🔴 Budget {category} bulan {month} sudah terlampaui {format_rupiah(abs(remaining))}!"
    elif pct_used >= 80:
        alert = True
        alert_msg = f"🟠 Budget {category} bulan {month} tersisa {format_rupiah(remaining)} ({100 - pct_used:.0f}%)"

    return {
        "month": month,
        "category": category,
        "budget": budget,
        "actual": actual,
        "remaining": remaining,
        "pct_used": round(pct_used, 1),
        "emoji": emoji,
        "alert": alert,
        "alert_msg": alert_msg,
    }