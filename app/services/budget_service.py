from datetime import datetime
import re

from app.sheets.client import (
    append_row,
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
    """Return bulan ini dalam format YYYY-MM."""
    return datetime.now().strftime("%Y-%m")


def normalize_month(month: str | None = None) -> str:
    """
    Normalize bulan ke format YYYY-MM.

    Support:
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
    Set atau update budget untuk kategori tertentu pada bulan tertentu.

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
        record_month = str(record.get("month", "")).strip()
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

    append_row(SHEET_BUDGETS, row)

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
        record_month = str(record.get("month", "")).strip()
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
        if str(r.get("month", "")).strip() == month
    ]


def get_budget_months() -> list[str]:
    """Ambil daftar bulan yang punya budget."""
    records = get_all_records(SHEET_BUDGETS)
    months = sorted({
        str(r.get("month", "")).strip()
        for r in records
        if str(r.get("month", "")).strip()
    })

    return months


# ── Realisasi vs Budget ───────────────────────────────────────────────────────

def get_actual_expense(category: str, month: str = None) -> float:
    """
    Hitung total pengeluaran aktual untuk kategori tertentu di bulan tertentu.

    Catatan:
    - Debt cashflow tidak dihitung sebagai konsumsi budget, kecuali kamu sengaja set budget
      untuk kategori debt tersebut.
    """
    month = normalize_month(month)

    records = get_all_records(SHEET_TRANSACTIONS)
    total = 0.0

    for record in records:
        txn_type = str(record.get("type", "")).strip()
        txn_category = str(record.get("category", "")).strip()
        txn_date = str(record.get("date", "")).strip()

        if txn_type != "expense":
            continue

        if txn_category.lower() != category.strip().lower():
            continue

        if not txn_date.startswith(month):
            continue

        total += safe_float(record.get("amount", 0))

    return total


def get_budget_summary(month: str = None) -> list[dict]:
    """
    Ambil ringkasan budget vs realisasi semua kategori pada bulan tertentu.
    """
    month = normalize_month(month)

    budgets = get_all_budgets(month)
    result = []

    for b in budgets:
        category = str(b.get("category", "")).strip()
        budget_amount = safe_float(b.get("budget_amount", 0))

        if not category:
            continue

        actual = get_actual_expense(category, month)
        remaining = budget_amount - actual
        pct_used = (actual / budget_amount * 100) if budget_amount > 0 else 0

        result.append({
            "month": month,
            "category": category,
            "budget": budget_amount,
            "actual": actual,
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
    Return info budget jika ada, None jika kategori tidak punya budget.
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