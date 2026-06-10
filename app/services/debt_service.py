from datetime import datetime
from app.sheets.client import (
    append_row,
    get_all_records,
    update_cell,
)
from app.config import SHEET_DEBTS, SHEET_DEBT_PAYMENTS


# ── Helpers ───────────────────────────────────────────────────────────────────

def format_rupiah(amount: float) -> str:
    return f"Rp{int(amount):,}".replace(",", ".")


def generate_debt_id() -> str:
    return datetime.now().strftime("debt_%Y%m%d_%H%M%S_%f")


def generate_payment_id() -> str:
    return datetime.now().strftime("pay_%Y%m%d_%H%M%S_%f")


def normalize_person_name(name: str) -> str:
    """
    Normalisasi nama supaya 'budi', 'Budi', '  budi  ' dianggap orang yang sama.
    """
    if not name:
        return ""

    return " ".join(str(name).strip().split()).title()


def is_settled_value(value) -> bool:
    return str(value).strip().upper() == "TRUE"


def get_debt_row_by_id(debt_id: str) -> tuple[int | None, dict | None]:
    """
    Cari debt berdasarkan ID.
    Return: (row_index_sheet, record)
    row_index_sheet = index 1-based di Google Sheets, termasuk header.
    """
    records = get_all_records(SHEET_DEBTS)

    for i, record in enumerate(records):
        if str(record.get("id", "")) == str(debt_id):
            return i + 2, record

    return None, None


def get_active_debt_exact_person(person_name: str) -> tuple[int | None, dict | None]:
    """
    Ambil 1 debt aktif berdasarkan nama orang secara exact setelah normalisasi.
    Dengan desain netting, idealnya 1 orang hanya punya 1 debt aktif.
    """
    target = normalize_person_name(person_name)
    records = get_all_records(SHEET_DEBTS)

    for i, record in enumerate(records):
        current_name = normalize_person_name(record.get("person_name", ""))
        if current_name != target:
            continue

        if is_settled_value(record.get("is_settled", "FALSE")):
            continue

        return i + 2, record

    return None, None


def append_debt_mutation(
    debt_id: str,
    amount: float,
    note: str = "",
    mutation_type: str = "payment",
):
    """
    Catat mutasi debt ke sheet debt_payments.

    Struktur lama debt_payments:
    id, debt_id, amount, date, note

    Agar kompatibel dengan header lama, mutation_type dimasukkan ke note.
    """
    payment_row = [
        generate_payment_id(),
        debt_id,
        amount,
        datetime.now().strftime("%Y-%m-%d"),
        f"[{mutation_type}] {note}".strip(),
    ]
    append_row(SHEET_DEBT_PAYMENTS, payment_row)


# ── Debt CRUD / Netting ───────────────────────────────────────────────────────

def add_debt(
    debt_type: str,
    person_name: str,
    amount: float,
    description: str = "",
    due_date: str = "",
) -> dict:
    """
    Tambah utang/piutang dengan sistem netting per orang.

    debt_type:
    - payable    = Anda punya utang ke orang tersebut
    - receivable = orang tersebut punya utang ke Anda

    Aturan:
    1. Jika orang belum punya debt aktif, buat baris baru.
    2. Jika orang sudah punya debt aktif dengan arah sama, tambahkan remaining.
    3. Jika orang sudah punya debt aktif dengan arah berbeda, lakukan netting.
    4. Jika hasil netting 0, tandai settled.
    5. Jika hasil netting berbalik arah, ubah type debt aktif.
    """
    person_name = normalize_person_name(person_name)
    amount = float(amount or 0)

    if debt_type not in ["payable", "receivable"]:
        return {
            "success": False,
            "debt_id": None,
            "message": "Tipe debt tidak valid.",
            "action": "error",
        }

    if not person_name:
        return {
            "success": False,
            "debt_id": None,
            "message": "Nama orang kosong.",
            "action": "error",
        }

    if amount <= 0:
        return {
            "success": False,
            "debt_id": None,
            "message": "Nominal debt tidak valid.",
            "action": "error",
        }

    existing_row, existing = get_active_debt_exact_person(person_name)

    # Kolom sheet debts:
    # 1=id, 2=type, 3=person_name, 4=original_amount, 5=remaining_amount,
    # 6=description, 7=due_date, 8=is_settled, 9=created_at, 10=settled_at
    TYPE_COL = 2
    ORIGINAL_AMOUNT_COL = 4
    REMAINING_COL = 5
    DESCRIPTION_COL = 6
    DUE_DATE_COL = 7
    IS_SETTLED_COL = 8
    SETTLED_AT_COL = 10

    # ── Tidak ada debt aktif, buat baru ──────────────────────────────────────
    if not existing:
        debt_id = generate_debt_id()
        row = [
            debt_id,
            debt_type,
            person_name,
            amount,
            amount,
            description,
            due_date,
            "FALSE",
            datetime.now().strftime("%Y-%m-%d"),
            "",
        ]

        try:
            append_row(SHEET_DEBTS, row)
            append_debt_mutation(
                debt_id,
                amount,
                description or f"Tambah {debt_type} {person_name}",
                mutation_type=f"add_{debt_type}",
            )
            return {
                "success": True,
                "debt_id": debt_id,
                "message": "ok",
                "action": "created",
                "person_name": person_name,
                "type": debt_type,
                "remaining": amount,
                "is_settled": False,
            }
        except Exception as e:
            return {
                "success": False,
                "debt_id": None,
                "message": str(e),
                "action": "error",
            }

    # ── Ada debt aktif, lakukan netting ───────────────────────────────────────
    debt_id = existing.get("id")
    existing_type = existing.get("type")
    existing_remaining = float(existing.get("remaining_amount", 0) or 0)
    existing_original = float(existing.get("original_amount", 0) or 0)
    existing_description = existing.get("description", "") or ""

    try:
        if existing_type == debt_type:
            # Arah sama: tambah nominal
            new_type = existing_type
            new_remaining = existing_remaining + amount
            new_original = existing_original + amount
            is_settled = False
            action = "merged_same_direction"

        else:
            # Arah beda: netting
            if existing_remaining > amount:
                new_type = existing_type
                new_remaining = existing_remaining - amount
                new_original = existing_original
                is_settled = False
                action = "netted_reduced"

            elif existing_remaining < amount:
                new_type = debt_type
                new_remaining = amount - existing_remaining
                new_original = new_remaining
                is_settled = False
                action = "netted_flipped"

            else:
                new_type = existing_type
                new_remaining = 0
                new_original = existing_original
                is_settled = True
                action = "netted_settled"

        new_description_parts = []
        if existing_description:
            new_description_parts.append(existing_description)
        if description:
            new_description_parts.append(description)

        new_description = " | ".join(new_description_parts)
        if len(new_description) > 500:
            new_description = new_description[-500:]

        update_cell(SHEET_DEBTS, existing_row, TYPE_COL, new_type)
        update_cell(SHEET_DEBTS, existing_row, ORIGINAL_AMOUNT_COL, new_original)
        update_cell(SHEET_DEBTS, existing_row, REMAINING_COL, new_remaining)
        update_cell(SHEET_DEBTS, existing_row, DESCRIPTION_COL, new_description)
        if due_date:
            update_cell(SHEET_DEBTS, existing_row, DUE_DATE_COL, due_date)
        update_cell(SHEET_DEBTS, existing_row, IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")
        update_cell(
            SHEET_DEBTS,
            existing_row,
            SETTLED_AT_COL,
            datetime.now().strftime("%Y-%m-%d") if is_settled else "",
        )

        append_debt_mutation(
            debt_id,
            amount,
            description or f"Tambah {debt_type} {person_name}",
            mutation_type=f"netting_{debt_type}",
        )

        return {
            "success": True,
            "debt_id": debt_id,
            "message": "ok",
            "action": action,
            "person_name": person_name,
            "type": new_type,
            "remaining": new_remaining,
            "is_settled": is_settled,
        }

    except Exception as e:
        return {
            "success": False,
            "debt_id": debt_id,
            "message": str(e),
            "action": "error",
        }


def get_active_debts(debt_type: str = None) -> list[dict]:
    """
    Ambil semua utang/piutang yang belum lunas.
    """
    records = get_all_records(SHEET_DEBTS)
    result = []

    for record in records:
        if is_settled_value(record.get("is_settled", "FALSE")):
            continue

        if debt_type and record.get("type") != debt_type:
            continue

        result.append(record)

    return result


def get_debt_by_person(person_name: str) -> list[dict]:
    """
    Cari utang/piutang aktif berdasarkan nama orang.
    Tetap return list supaya kompatibel dengan handler lama.
    """
    target = normalize_person_name(person_name)
    records = get_all_records(SHEET_DEBTS)
    result = []

    for record in records:
        current_name = normalize_person_name(record.get("person_name", ""))

        if target not in current_name and current_name not in target:
            continue

        if is_settled_value(record.get("is_settled", "FALSE")):
            continue

        result.append(record)

    return result


def add_payment(debt_id: str, amount: float, note: str = "") -> dict:
    """
    Catat pembayaran/pengurangan debt tertentu.
    Untuk debt type apa pun, payment berarti mengurangi remaining_amount.
    """
    debt_row_index, debt_record = get_debt_row_by_id(debt_id)

    if not debt_record:
        return {
            "success": False,
            "remaining": 0,
            "is_settled": False,
            "message": f"Debt ID {debt_id} tidak ditemukan.",
        }

    amount = float(amount or 0)
    if amount <= 0:
        return {
            "success": False,
            "remaining": float(debt_record.get("remaining_amount", 0) or 0),
            "is_settled": False,
            "message": "Nominal pembayaran tidak valid.",
        }

    current_remaining = float(debt_record.get("remaining_amount", 0) or 0)
    new_remaining = max(0, current_remaining - amount)
    is_settled = new_remaining == 0

    REMAINING_COL = 5
    IS_SETTLED_COL = 8
    SETTLED_AT_COL = 10

    try:
        update_cell(SHEET_DEBTS, debt_row_index, REMAINING_COL, new_remaining)
        update_cell(SHEET_DEBTS, debt_row_index, IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")

        if is_settled:
            update_cell(
                SHEET_DEBTS,
                debt_row_index,
                SETTLED_AT_COL,
                datetime.now().strftime("%Y-%m-%d"),
            )

        append_debt_mutation(
            debt_id,
            amount,
            note or "Pembayaran/pengurangan debt",
            mutation_type="payment",
        )

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
    Hitung total utang dan piutang aktif.
    """
    all_active = get_active_debts()

    payables = [r for r in all_active if r.get("type") == "payable"]
    receivables = [r for r in all_active if r.get("type") == "receivable"]

    total_payable = sum(float(r.get("remaining_amount", 0) or 0) for r in payables)
    total_receivable = sum(float(r.get("remaining_amount", 0) or 0) for r in receivables)

    return {
        "total_payable": total_payable,
        "total_receivable": total_receivable,
        "payables": payables,
        "receivables": receivables,
    }