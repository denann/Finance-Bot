from datetime import datetime
from app.sheets.client import (
    append_row,
    get_all_records,
    find_row_index,
    update_cell,
)
from app.config import SHEET_DEBTS, SHEET_DEBT_PAYMENTS


# ── Helpers ───────────────────────────────────────────────────────────────────

def format_rupiah(amount: float) -> str:
    return f"Rp{int(amount):,}".replace(",", ".")


def generate_debt_id() -> str:
    return datetime.now().strftime("debt_%Y%m%d_%H%M%S")


def generate_payment_id() -> str:
    return datetime.now().strftime("pay_%Y%m%d_%H%M%S")


# ── Debt CRUD ─────────────────────────────────────────────────────────────────

def add_debt(
    debt_type: str,
    person_name: str,
    amount: float,
    description: str = "",
    due_date: str = "",
) -> dict:
    """
    Tambah utang atau piutang baru.

    Args:
        debt_type : "payable"    → utang Anda ke orang lain
                    "receivable" → piutang orang lain ke Anda
        person_name: nama orang
        amount     : nominal
        description: keterangan
        due_date   : jatuh tempo YYYY-MM-DD (opsional)

    Return:
        {"success": bool, "debt_id": str, "message": str}
    """
    debt_id = generate_debt_id()
    row = [
        debt_id,
        debt_type,
        person_name,
        amount,
        amount,          # remaining = original saat pertama dibuat
        description,
        due_date,
        "FALSE",         # is_settled
        datetime.now().strftime("%Y-%m-%d"),
        "",              # settled_at
    ]

    try:
        append_row(SHEET_DEBTS, row)
        return {
            "success": True,
            "debt_id": debt_id,
            "message": "ok",
        }
    except Exception as e:
        return {
            "success": False,
            "debt_id": None,
            "message": str(e),
        }


def get_active_debts(debt_type: str = None) -> list[dict]:
    """
    Ambil semua utang/piutang yang belum lunas.

    Args:
        debt_type: "payable" | "receivable" | None (semua)
    """
    records = get_all_records(SHEET_DEBTS)
    result = []

    for r in records:
        # Skip yang sudah lunas
        is_settled = str(r.get("is_settled", "FALSE")).upper()
        if is_settled == "TRUE":
            continue

        if debt_type and r.get("type") != debt_type:
            continue

        result.append(r)

    return result


def get_debt_by_person(person_name: str) -> list[dict]:
    """Cari utang/piutang berdasarkan nama orang."""
    records = get_all_records(SHEET_DEBTS)
    person_lower = person_name.lower()

    return [
        r for r in records
        if person_lower in str(r.get("person_name", "")).lower()
        and str(r.get("is_settled", "FALSE")).upper() != "TRUE"
    ]


def add_payment(debt_id: str, amount: float, note: str = "") -> dict:
    """
    Catat pembayaran untuk utang/piutang tertentu.
    Otomatis update remaining_amount dan tandai lunas jika sudah 0.

    Return:
        {
            "success": bool,
            "remaining": float,
            "is_settled": bool,
            "message": str
        }
    """
    # Cari debt di sheet
    records = get_all_records(SHEET_DEBTS)
    debt_row_index = None
    debt_record = None

    for i, r in enumerate(records):
        if r.get("id") == debt_id:
            debt_row_index = i + 2  # +2: header di baris 1
            debt_record = r
            break

    if not debt_record:
        return {
            "success": False,
            "remaining": 0,
            "is_settled": False,
            "message": f"Debt ID {debt_id} tidak ditemukan.",
        }

    current_remaining = float(debt_record.get("remaining_amount", 0))
    new_remaining = max(0, current_remaining - amount)
    is_settled = new_remaining == 0

    # Kolom sheet debts:
    # 1=id, 2=type, 3=person_name, 4=original_amount, 5=remaining_amount,
    # 6=description, 7=due_date, 8=is_settled, 9=created_at, 10=settled_at
    REMAINING_COL = 5
    IS_SETTLED_COL = 8
    SETTLED_AT_COL = 10

    try:
        update_cell(SHEET_DEBTS, debt_row_index, REMAINING_COL, new_remaining)
        update_cell(SHEET_DEBTS, debt_row_index, IS_SETTLED_COL,
                    "TRUE" if is_settled else "FALSE")

        if is_settled:
            update_cell(
                SHEET_DEBTS,
                debt_row_index,
                SETTLED_AT_COL,
                datetime.now().strftime("%Y-%m-%d")
            )

        # Catat ke sheet debt_payments
        payment_row = [
            generate_payment_id(),
            debt_id,
            amount,
            datetime.now().strftime("%Y-%m-%d"),
            note,
        ]
        append_row(SHEET_DEBT_PAYMENTS, payment_row)

        return {
            "success": True,
            "remaining": new_remaining,
            "is_settled": is_settled,
            "message": "ok",
        }

    except Exception as e:
        return {
            "success": False,
            "remaining": current_remaining,
            "is_settled": False,
            "message": str(e),
        }


def get_debt_summary() -> dict:
    """
    Hitung total utang dan piutang yang masih aktif.

    Return:
    {
        "total_payable": float,      ← total utang Anda
        "total_receivable": float,   ← total piutang Anda
        "payables": list[dict],
        "receivables": list[dict],
    }
    """
    all_active = get_active_debts()

    payables = [r for r in all_active if r.get("type") == "payable"]
    receivables = [r for r in all_active if r.get("type") == "receivable"]

    total_payable = sum(float(r.get("remaining_amount", 0)) for r in payables)
    total_receivable = sum(float(r.get("remaining_amount", 0)) for r in receivables)

    return {
        "total_payable": total_payable,
        "total_receivable": total_receivable,
        "payables": payables,
        "receivables": receivables,
    }