from datetime import datetime
from app.sheets.client import (
    append_row,
    get_all_records,
    find_row_index,
    update_cell,
    get_sheet,
)
from app.config import SHEET_BUDGETS, SHEET_TRANSACTIONS


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_current_month() -> str:
    """Return bulan ini dalam format YYYY-MM."""
    return datetime.now().strftime("%Y-%m")


def format_rupiah(amount: float) -> str:
    return f"Rp{int(amount):,}".replace(",", ".")


def get_budget_status_emoji(pct_used: float) -> str:
    """
    Return emoji berdasarkan persentase budget yang terpakai.
    """
    if pct_used >= 100:
        return "🔴"  # Over budget
    elif pct_used >= 80:
        return "🟠"  # Hampir habis
    elif pct_used >= 50:
        return "🟡"  # Setengah jalan
    else:
        return "🟢"  # Aman


# ── Budget CRUD ───────────────────────────────────────────────────────────────

def set_budget(category: str, amount: float, month: str = None) -> dict:
    """
    Set atau update budget untuk kategori tertentu.
    Jika sudah ada, update. Jika belum, tambah baru.

    Return:
        {"success": bool, "action": "created"|"updated", "message": str}
    """
    if not month:
        month = get_current_month()

    records = get_all_records(SHEET_BUDGETS)

    # Cek apakah sudah ada budget untuk kategori + bulan ini
    for i, record in enumerate(records):
        if (
            record.get("category", "").lower() == category.lower()
            and record.get("month") == month
        ):
            # Update baris yang ada
            # Kolom: 1=month, 2=category, 3=budget_amount, 4=created_at
            row_index = i + 2  # +2 karena header di baris 1, data mulai baris 2
            update_cell(SHEET_BUDGETS, row_index, 3, amount)
            return {
                "success": True,
                "action": "updated",
                "message": f"Budget {category} diupdate ke {format_rupiah(amount)}",
            }

    # Belum ada — tambah baru
    row = [
        month,
        category,
        amount,
        datetime.now().strftime("%Y-%m-%d"),
    ]
    append_row(SHEET_BUDGETS, row)
    return {
        "success": True,
        "action": "created",
        "message": f"Budget {category} diset {format_rupiah(amount)}",
    }


def get_budget(category: str, month: str = None) -> float | None:
    """
    Ambil budget untuk kategori tertentu di bulan tertentu.
    Return None jika belum ada budget.
    """
    if not month:
        month = get_current_month()

    records = get_all_records(SHEET_BUDGETS)
    for record in records:
        if (
            record.get("category", "").lower() == category.lower()
            and record.get("month") == month
        ):
            return float(record.get("budget_amount", 0))
    return None


def get_all_budgets(month: str = None) -> list[dict]:
    """Ambil semua budget di bulan tertentu."""
    if not month:
        month = get_current_month()

    records = get_all_records(SHEET_BUDGETS)
    return [r for r in records if r.get("month") == month]


# ── Realisasi vs Budget ───────────────────────────────────────────────────────

def get_actual_expense(category: str, month: str = None) -> float:
    """
    Hitung total pengeluaran aktual untuk kategori tertentu di bulan tertentu.
    """
    if not month:
        month = get_current_month()

    records = get_all_records(SHEET_TRANSACTIONS)
    total = 0.0

    for record in records:
        if (
            record.get("type") == "expense"
            and record.get("category", "").lower() == category.lower()
            and str(record.get("date", "")).startswith(month)
        ):
            total += float(record.get("amount", 0))

    return total


def get_budget_summary(month: str = None) -> list[dict]:
    """
    Ambil ringkasan budget vs realisasi semua kategori.

    Return list of dict:
    [
        {
            "category": str,
            "budget": float,
            "actual": float,
            "remaining": float,
            "pct_used": float,
            "status": str,
            "emoji": str,
        },
        ...
    ]
    """
    if not month:
        month = get_current_month()

    budgets = get_all_budgets(month)
    result = []

    for b in budgets:
        category = b.get("category", "")
        budget_amount = float(b.get("budget_amount", 0))
        actual = get_actual_expense(category, month)
        remaining = budget_amount - actual
        pct_used = (actual / budget_amount * 100) if budget_amount > 0 else 0

        result.append({
            "category": category,
            "budget": budget_amount,
            "actual": actual,
            "remaining": remaining,
            "pct_used": round(pct_used, 1),
            "status": "over" if pct_used >= 100 else "warning" if pct_used >= 80 else "ok",
            "emoji": get_budget_status_emoji(pct_used),
        })

    # Sort: yang paling kritis di atas
    result.sort(key=lambda x: x["pct_used"], reverse=True)
    return result


def check_budget_after_transaction(category: str, month: str = None) -> dict | None:
    """
    Dipanggil setiap kali ada transaksi expense masuk.
    Return info budget jika ada, None jika kategori tidak punya budget.

    Return:
    {
        "category": str,
        "budget": float,
        "actual": float,
        "remaining": float,
        "pct_used": float,
        "emoji": str,
        "alert": bool,   ← True jika perlu notifikasi khusus
        "alert_msg": str
    }
    """
    if not month:
        month = get_current_month()

    budget = get_budget(category, month)
    if budget is None:
        return None  # Tidak ada budget untuk kategori ini

    actual = get_actual_expense(category, month)
    remaining = budget - actual
    pct_used = (actual / budget * 100) if budget > 0 else 0
    emoji = get_budget_status_emoji(pct_used)

    alert = False
    alert_msg = ""

    if pct_used >= 100:
        alert = True
        alert_msg = f"🔴 Budget {category} sudah terlampaui {format_rupiah(abs(remaining))}!"
    elif pct_used >= 80:
        alert = True
        alert_msg = f"🟠 Budget {category} tersisa {format_rupiah(remaining)} ({100 - pct_used:.0f}%)"

    return {
        "category": category,
        "budget": budget,
        "actual": actual,
        "remaining": remaining,
        "pct_used": round(pct_used, 1),
        "emoji": emoji,
        "alert": alert,
        "alert_msg": alert_msg,
    }