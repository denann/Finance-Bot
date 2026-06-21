from datetime import datetime
from app.sheets.client import (
    append_row,
    get_all_records,
    update_cell,
    delete_rows,
)
from app.config import SHEET_DEBTS, SHEET_DEBT_PAYMENTS


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_sheet_number(value, default: float = 0.0) -> float:
    """Parse angka dari Google Sheets dengan aman.

    Mendukung:
    - 71387.5  (UNFORMATTED_VALUE)
    - "71387,5" (format locale Indonesia)
    - "71.387,5"
    - "713,875" dari numericise lama akan tetap dibaca apa adanya jika sudah numeric,
      jadi fix utama tetap ada di app/sheets/client.py.
    """
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)

    raw = str(value).strip()
    if not raw:
        return default

    raw = raw.replace("Rp", "").replace("rp", "").replace("IDR", "").replace("idr", "")
    raw = raw.replace(" ", "")

    if "," in raw and "." in raw:
        # Format Indonesia: 71.387,5
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        # Format Indonesia tanpa ribuan: 71387,5
        raw = raw.replace(",", ".")
    else:
        # Format ribuan biasa: 71.387
        parts = raw.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            raw = raw.replace(".", "")

    try:
        return float(raw)
    except Exception:
        return default


def format_rupiah(amount: float) -> str:
    """Format rupiah tanpa menghilangkan pecahan split bill."""
    value = float(amount or 0)
    if abs(value - round(value)) < 1e-9:
        return f"Rp{int(round(value)):,}".replace(",", ".")

    sign = "-" if value < 0 else ""
    value = abs(value)
    integer_part = int(value)
    decimal_part = (f"{value:.2f}".split(".", 1)[1]).rstrip("0")
    return f"Rp{sign}{integer_part:,}".replace(",", ".") + f",{decimal_part}"


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
    source_transaction_id: str = "",
    cashflow_mode: str = "",
    fronting_mode: str = "",
) -> dict:
    """
    Tambah utang/piutang sebagai baris granular per input.

    Catatan desain baru:
    - Tidak lagi melakukan netting/merge per orang.
    - Setiap input debt menghasilkan 1 row debt agar asal nominal mudah ditrace.
    - Ringkasan /hutang dihitung dari agregasi remaining_amount aktif.

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


    # DESAIN BARU: debt granular per input, bukan netting per orang.
    # Header sheet debts yang disarankan:
    # id, type, person_name, original_amount, remaining_amount, description, due_date,
    # is_settled, created_at, settled_at, source_transaction_id, cashflow_mode, fronting_mode
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
        source_transaction_id or "",
        cashflow_mode or "",
        fronting_mode or "",
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
            "action": "created_granular",
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

    # Legacy netting code di bawah dibiarkan sebagai referensi fallback,
    # tetapi tidak dieksekusi karena desain debt sekarang granular.

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
    existing_remaining = parse_sheet_number(existing.get("remaining_amount", 0))
    existing_original = parse_sheet_number(existing.get("original_amount", 0))
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
    Return sudah membawa _row_index supaya pembayaran FIFO bisa stabil.
    """
    target = normalize_person_name(person_name)
    result = []

    for record in get_debts_with_row_index(active_only=True):
        current_name = normalize_person_name(record.get("person_name", ""))

        if target not in current_name and current_name not in target:
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
            "remaining": parse_sheet_number(debt_record.get("remaining_amount", 0)),
            "is_settled": False,
            "message": "Nominal pembayaran tidak valid.",
        }

    current_remaining = parse_sheet_number(debt_record.get("remaining_amount", 0))
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



def add_payment_by_person(person_name: str, amount: float, note: str = "") -> dict:
    """
    Alokasikan pembayaran ke semua debt aktif milik seseorang secara FIFO.

    Dipakai untuk input natural seperti:
    - "Akmal bayar hutang 20k"
    - "bayar hutang Akmal 20k"

    Jika orang punya beberapa debt granular, nominal pembayaran akan mengurangi
    debt paling lama dulu sampai nominal habis.
    """
    person_name = normalize_person_name(person_name)
    amount = float(amount or 0)

    if not person_name:
        return {
            "success": False,
            "message": "Nama orang kosong.",
            "remaining": 0,
            "is_settled": False,
            "allocations": [],
        }

    if amount <= 0:
        return {
            "success": False,
            "message": "Nominal pembayaran tidak valid.",
            "remaining": 0,
            "is_settled": False,
            "allocations": [],
        }

    debts = get_debt_by_person(person_name)
    if not debts:
        return {
            "success": False,
            "message": f"Tidak ada utang/piutang aktif dengan {person_name}.",
            "remaining": 0,
            "is_settled": False,
            "allocations": [],
        }

    debt_types = {str(d.get("type", "")).strip() for d in debts if str(d.get("type", "")).strip()}
    if len(debt_types) > 1:
        return {
            "success": False,
            "message": (
                f"Ada utang dan piutang aktif sekaligus dengan {person_name}. "
                "Gunakan /hutang lalu bayar/void debt yang spesifik dulu agar tidak salah arah."
            ),
            "remaining": sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in debts),
            "is_settled": False,
            "allocations": [],
        }

    remaining_payment = amount
    allocations = []

    # FIFO berdasarkan row sheet/created_at.
    for debt in sorted(debts, key=lambda d: int(d.get("_row_index", 10**9) or 10**9)):
        if remaining_payment <= 0:
            break

        debt_id = str(debt.get("id", "")).strip()
        debt_remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        if not debt_id or debt_remaining <= 0:
            continue

        pay_amount = min(remaining_payment, debt_remaining)
        result = add_payment(debt_id, pay_amount, note or f"Pembayaran dari {person_name}")
        if not result.get("success"):
            return {
                "success": False,
                "message": result.get("message", "Gagal alokasi pembayaran."),
                "remaining": sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in get_debt_by_person(person_name)),
                "is_settled": False,
                "allocations": allocations,
            }

        allocations.append({
            "debt_id": debt_id,
            "amount": pay_amount,
            "description": debt.get("description", ""),
        })
        remaining_payment -= pay_amount

    active_after = get_debt_by_person(person_name)
    total_remaining = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in active_after)

    return {
        "success": True,
        "message": "ok" if remaining_payment <= 0 else f"Pembayaran melebihi saldo aktif sebesar {format_rupiah(remaining_payment)}.",
        "remaining": total_remaining,
        "is_settled": total_remaining <= 0,
        "allocations": allocations,
        "overpayment": max(0, remaining_payment),
        "type": next(iter(debt_types)) if debt_types else "",
    }



def offset_debt_by_person(
    person_name: str,
    amount: float,
    description: str = "",
    target_debt_type: str = "receivable",
    resulting_debt_type: str = "payable",
) -> dict:
    """
    Kompensasi / potong silang hutang-piutang tanpa cashflow rekening.

    Contoh kasus:
    - User punya piutang ke Akmal 50k.
    - User ikut badminton dan berutang ke Akmal 20k.
    - Input: "potong piutang Akmal 20k buat badminton".
    - Efek: piutang receivable Akmal berkurang 20k, transactions tetap mencatat fact row type=debt_offset.

    target_debt_type:
    - receivable: kurangi piutang aktif orang tsb; jika offset lebih besar, sisa jadi payable.
    - payable: kurangi utang aktif user ke orang tsb; jika offset lebih besar, sisa jadi receivable.
    """
    person_name = normalize_person_name(person_name)
    amount = float(amount or 0)
    target_debt_type = str(target_debt_type or "receivable").strip().lower()
    resulting_debt_type = str(resulting_debt_type or "payable").strip().lower()

    if target_debt_type not in ["payable", "receivable"]:
        return {
            "success": False,
            "message": "target_debt_type tidak valid.",
            "allocations": [],
            "affected_debt_ids": [],
        }

    if resulting_debt_type not in ["payable", "receivable"]:
        resulting_debt_type = "payable" if target_debt_type == "receivable" else "receivable"

    if not person_name:
        return {
            "success": False,
            "message": "Nama orang kosong.",
            "allocations": [],
            "affected_debt_ids": [],
        }

    if amount <= 0:
        return {
            "success": False,
            "message": "Nominal offset tidak valid.",
            "allocations": [],
            "affected_debt_ids": [],
        }

    debts = [
        d for d in get_debt_by_person(person_name)
        if str(d.get("type", "")).strip() == target_debt_type
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
    ]

    if not debts:
        label = "piutang" if target_debt_type == "receivable" else "utang"
        return {
            "success": False,
            "message": f"Tidak ada {label} aktif dengan {person_name} untuk dipotong.",
            "allocations": [],
            "affected_debt_ids": [],
        }

    remaining_offset = amount
    allocations = []
    affected_debt_ids = []
    today = datetime.now().strftime("%Y-%m-%d")
    note = description or "Kompensasi hutang-piutang"

    try:
        for debt in sorted(debts, key=lambda d: int(d.get("_row_index", 10**9) or 10**9)):
            if remaining_offset <= 0:
                break

            debt_id = str(debt.get("id", "")).strip()
            row_index = int(debt.get("_row_index"))
            current_remaining = parse_sheet_number(debt.get("remaining_amount", 0))
            if not debt_id or current_remaining <= 0:
                continue

            offset_amount = min(remaining_offset, current_remaining)
            new_remaining = current_remaining - offset_amount
            is_settled = new_remaining <= 0

            update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, new_remaining)
            update_cell(SHEET_DEBTS, row_index, DEBT_IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")
            if is_settled:
                update_cell(SHEET_DEBTS, row_index, DEBT_SETTLED_AT_COL, today)

            append_debt_mutation(
                debt_id=debt_id,
                amount=offset_amount,
                note=note,
                mutation_type="offset",
            )

            allocations.append({
                "debt_id": debt_id,
                "amount": offset_amount,
                "description": debt.get("description", ""),
                "remaining_after": new_remaining,
                "type": target_debt_type,
            })
            affected_debt_ids.append(debt_id)
            remaining_offset -= offset_amount

        created_debt_id = ""
        created_debt = None
        if remaining_offset > 0:
            created = add_debt(
                resulting_debt_type,
                person_name,
                remaining_offset,
                description=f"Sisa kompensasi: {note}",
                cashflow_mode="debt_only",
                fronting_mode="offset_remainder",
            )
            if not created.get("success"):
                return {
                    "success": False,
                    "message": "Offset sebagian berhasil, tapi gagal membuat sisa debt: " + created.get("message", ""),
                    "allocations": allocations,
                    "affected_debt_ids": affected_debt_ids,
                }
            created_debt_id = created.get("debt_id") or ""
            created_debt = created
            if created_debt_id:
                affected_debt_ids.append(created_debt_id)

        active_after = get_debt_by_person(person_name)
        total_payable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in active_after if d.get("type") == "payable")
        total_receivable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in active_after if d.get("type") == "receivable")

        return {
            "success": True,
            "message": "ok",
            "person_name": person_name,
            "type": "offset",
            "target_debt_type": target_debt_type,
            "resulting_debt_type": resulting_debt_type,
            "amount": amount,
            "offset_applied": amount - max(0, remaining_offset),
            "overage": max(0, remaining_offset),
            "created_debt_id": created_debt_id,
            "created_debt": created_debt,
            "affected_debt_ids": affected_debt_ids,
            "debt_id": ", ".join(affected_debt_ids),
            "allocations": allocations,
            "remaining": total_receivable if total_receivable > 0 else total_payable,
            "remaining_receivable": total_receivable,
            "remaining_payable": total_payable,
            "is_settled": total_receivable <= 0 and total_payable <= 0,
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "allocations": allocations,
            "affected_debt_ids": affected_debt_ids,
        }

def get_debt_summary() -> dict:
    """
    Hitung total utang dan piutang aktif.
    """
    all_active = get_debts_with_row_index(active_only=True)

    payables = [r for r in all_active if r.get("type") == "payable"]
    receivables = [r for r in all_active if r.get("type") == "receivable"]

    total_payable = sum(parse_sheet_number(r.get("remaining_amount", 0)) for r in payables)
    total_receivable = sum(parse_sheet_number(r.get("remaining_amount", 0)) for r in receivables)

    return {
        "total_payable": total_payable,
        "total_receivable": total_receivable,
        "payables": payables,
        "receivables": receivables,
    }

# ── Debt Void ─────────────────────────────────────────────────────────────────

DEBT_ID_COL = 1
DEBT_TYPE_COL = 2
DEBT_PERSON_COL = 3
DEBT_ORIGINAL_AMOUNT_COL = 4
DEBT_REMAINING_AMOUNT_COL = 5
DEBT_DESCRIPTION_COL = 6
DEBT_DUE_DATE_COL = 7
DEBT_IS_SETTLED_COL = 8
DEBT_SETTLED_AT_COL = 10


def get_debts_with_row_index(active_only: bool = True) -> list[dict]:
    """
    Ambil debt + _row_index Google Sheets.
    Data mulai row 2 karena row 1 adalah header.
    """
    records = get_all_records(SHEET_DEBTS)
    result = []

    for i, record in enumerate(records):
        item = dict(record)
        item["_row_index"] = i + 2

        if active_only and is_settled_value(item.get("is_settled", "FALSE")):
            continue

        result.append(item)

    return result


def get_debt_by_id_any_status(debt_id: str) -> tuple[int | None, dict | None]:
    """
    Cari debt berdasarkan ID, termasuk yang sudah settled/void.
    """
    target = str(debt_id or "").strip()
    if not target:
        return None, None

    for item in get_debts_with_row_index(active_only=False):
        if str(item.get("id", "")).strip() == target:
            return int(item.get("_row_index")), item

    return None, None


def build_active_debt_display_map() -> dict[str, dict]:
    """
    Bangun mapping nomor debt berdasarkan urutan tampilan /hutang.

    Ini dipakai sebagai fallback saat context.user_data['last_debt_map'] hilang
    karena bot restart/redeploy. Urutannya harus sama dengan hutang_handler:
    payables dulu, lalu receivables.
    """
    summary = get_debt_summary()
    display_map = {}
    display_no = 1

    for section in (summary.get("payables") or [], summary.get("receivables") or []):
        display_map[str(display_no)] = {
            "debt_id": section.get("id"),
            "row_index": section.get("_row_index"),
        }
        display_no += 1

    return display_map


def resolve_debt_ref(ref: str, last_debt_map: dict | None = None) -> tuple[int | None, dict | None, str | None]:
    """
    Resolve argumen /debt_void.

    Support:
    - /debt_void 1        -> nomor dari /hutang terakhir
    - /debt_void debt_xxx -> debt ID langsung
    """
    clean = str(ref or "").strip()
    if not clean:
        return None, None, "Masukkan nomor debt atau debt ID."

    last_debt_map = last_debt_map or {}

    if clean in last_debt_map:
        mapped = last_debt_map[clean]
        if isinstance(mapped, dict):
            debt_id = mapped.get("debt_id")
            if debt_id:
                row, debt = get_debt_by_id_any_status(debt_id)
                return row, debt, None if debt else "Debt tidak ditemukan."
        elif mapped:
            row, debt = get_debt_by_id_any_status(str(mapped))
            return row, debt, None if debt else "Debt tidak ditemukan."

    if clean.isdigit():
        # Fallback kalau mapping session /hutang hilang karena restart/redeploy.
        fallback_map = build_active_debt_display_map()
        mapped = fallback_map.get(clean)
        if mapped and mapped.get("debt_id"):
            row, debt = get_debt_by_id_any_status(mapped.get("debt_id"))
            return row, debt, None if debt else "Debt tidak ditemukan."

        return None, None, "Nomor debt tidak valid. Jalankan /hutang dulu, lalu pakai nomor yang muncul."

    row, debt = get_debt_by_id_any_status(clean)
    if not debt:
        return None, None, "Debt ID tidak ditemukan."

    return row, debt, None


def expected_initial_cashflow_category(debt: dict) -> str:
    debt_type = str(debt.get("type", "")).strip()
    if debt_type == "payable":
        return "Penerimaan Utang"
    if debt_type == "receivable":
        return "Piutang Diberikan"
    return ""


def find_debt_initial_cashflow_candidates(debt: dict) -> list[dict]:
    """
    Cari transaksi cashflow awal yang terkait debt.

    Catatan:
    - Versi lama belum menyimpan debt_id di transactions, jadi matching pakai person, amount,
      category, dan parsed_by/category debt.
    - Kalau hasilnya 0 atau >1, /debt_void akan ditolak agar aman.
    """
    from app.services.transaction_service import (
        get_transactions_with_row_index,
        is_debt_cashflow_transaction,
    )

    person = normalize_person_name(debt.get("person_name", ""))
    amount = parse_sheet_number(debt.get("original_amount", 0))
    category = expected_initial_cashflow_category(debt)
    debt_id = str(debt.get("id", "")).strip()

    candidates = []

    for txn in get_transactions_with_row_index():
        if not is_debt_cashflow_transaction(txn):
            continue

        txn_category = str(txn.get("category", "")).strip()
        txn_subject = normalize_person_name(txn.get("subject", ""))
        txn_amount = parse_sheet_number(txn.get("amount", 0))
        txn_notes = str(txn.get("catatan", "") or "")
        txn_raw = str(txn.get("raw_input", "") or "")

        # Kalau versi baru menyimpan debt_id di catatan/raw_input, pakai itu sebagai match kuat.
        if debt_id and (debt_id in txn_notes or debt_id in txn_raw):
            candidates.append(txn)
            continue

        if txn_category != category:
            continue

        if txn_subject != person:
            continue

        if abs(txn_amount - amount) > 0.0001:
            continue

        candidates.append(txn)

    return candidates


def is_debt_without_initial_cashflow(debt: dict) -> bool:
    """
    Deteksi debt yang memang dibuat tanpa transaksi cashflow awal.

    Contoh: split bill receivable, atau fitur talangan/ditalangin seperti
    "saya nitip Sapto beli nasi 12k". Debt seperti ini aman di-void tanpa
    reverse saldo karena saldo rekening user memang belum pernah berubah.
    """
    debt_type = str(debt.get("type", "")).strip()
    description = str(debt.get("description", "") or "").strip().lower()

    if debt_type == "receivable":
        return True

    debt_only_markers = [
        "ditalangin",
        "tanpa cashflow",
        "debt_only",
        "nitip",
    ]
    return any(marker in description for marker in debt_only_markers)




def get_debts_by_source_transaction_id(transaction_id: str, active_only: bool = True) -> list[dict]:
    """Cari debt granular yang dibuat dari source_transaction_id tertentu."""
    target = str(transaction_id or "").strip()
    if not target:
        return []

    result = []
    for debt in get_debts_with_row_index(active_only=active_only):
        if str(debt.get("source_transaction_id", "")).strip() == target:
            result.append(debt)
    return result


def void_debts_for_transaction(transaction_id: str, debt_ids: list[str] | None = None) -> dict:
    """
    Void semua debt yang terhubung ke transaksi.

    Sumber relasi:
    1. transactions.hutang_id / tipe_hutang
    2. debts.source_transaction_id
    """
    targets = []
    seen = set()

    for debt_id in debt_ids or []:
        clean = str(debt_id or "").strip()
        if clean and clean not in seen:
            targets.append(clean)
            seen.add(clean)

    for debt in get_debts_by_source_transaction_id(transaction_id, active_only=True):
        clean = str(debt.get("id", "")).strip()
        if clean and clean not in seen:
            targets.append(clean)
            seen.add(clean)

    results = []
    for debt_id in targets:
        results.append(void_linked_debt_only(debt_id, reason=f"Transaksi sumber {transaction_id} dihapus"))

    failed = [r for r in results if not r.get("success")]
    return {
        "success": not failed,
        "message": "ok" if not failed else "; ".join(r.get("message", "Gagal void debt") for r in failed),
        "voided_ids": [r.get("debt_id") for r in results if r.get("success") and not r.get("skipped")],
        "skipped_ids": [r.get("debt_id") for r in results if r.get("success") and r.get("skipped")],
        "failed": failed,
    }


def void_linked_debt_only(debt_id: str, reason: str = "Transaksi sumber dihapus") -> dict:
    """
    Void debt yang terhubung ke transaksi yang sedang dihapus.

    Tidak melakukan reverse saldo dan tidak menghapus transaksi cashflow, karena
    reverse/delete transaksi sudah ditangani oleh delete_transactions_by_refs().
    Untuk keamanan, hanya debt yang belum pernah dibayar/berubah yang otomatis di-void.
    """
    row_index, debt = get_debt_by_id_any_status(debt_id)

    if not debt or not row_index:
        return {"success": False, "message": f"Debt {debt_id} tidak ditemukan.", "debt_id": debt_id}

    if is_settled_value(debt.get("is_settled", "FALSE")):
        return {"success": True, "message": "Debt sudah settled.", "debt_id": debt_id, "skipped": True}

    original = parse_sheet_number(debt.get("original_amount", 0))
    remaining = parse_sheet_number(debt.get("remaining_amount", 0))
    if abs(original - remaining) > 0.0001:
        return {
            "success": False,
            "message": (
                f"Debt {debt_id} sudah punya pembayaran/mutasi. "
                "Delete transaksi sumber diblok agar debt tidak salah."
            ),
            "debt_id": debt_id,
        }

    today = datetime.now().strftime("%Y-%m-%d")
    old_description = str(debt.get("description", "") or "").strip()
    void_note = f"[VOID {today}] {reason}"
    new_description = f"{old_description} | {void_note}" if old_description else void_note

    update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, 0)
    update_cell(SHEET_DEBTS, row_index, DEBT_IS_SETTLED_COL, "TRUE")
    update_cell(SHEET_DEBTS, row_index, DEBT_SETTLED_AT_COL, today)
    update_cell(SHEET_DEBTS, row_index, DEBT_DESCRIPTION_COL, new_description)

    append_debt_mutation(
        debt_id=debt.get("id"),
        amount=remaining,
        note=void_note,
        mutation_type="void_by_transaction_delete",
    )

    return {"success": True, "message": "ok", "debt_id": debt_id, "skipped": False}


def preview_void_debt(debt_ref: str, last_debt_map: dict | None = None) -> dict:
    """
    Preview pembatalan debt.
    Tidak mengubah sheet.
    """
    row_index, debt, error = resolve_debt_ref(debt_ref, last_debt_map)

    if error:
        return {
            "success": False,
            "message": error,
            "debt": None,
            "debt_row_index": None,
            "cashflow_txn": None,
            "reverse_deltas": {},
        }

    if not debt:
        return {
            "success": False,
            "message": "Debt tidak ditemukan.",
            "debt": None,
            "debt_row_index": None,
            "cashflow_txn": None,
            "reverse_deltas": {},
        }

    if is_settled_value(debt.get("is_settled", "FALSE")):
        return {
            "success": False,
            "message": "Debt ini sudah settled/void.",
            "debt": debt,
            "debt_row_index": row_index,
            "cashflow_txn": None,
            "reverse_deltas": {},
        }

    original = parse_sheet_number(debt.get("original_amount", 0))
    remaining = parse_sheet_number(debt.get("remaining_amount", 0))

    if abs(original - remaining) > 0.0001:
        return {
            "success": False,
            "message": (
                "Debt ini sudah punya mutasi/pembayaran/netting. "
                "Untuk keamanan, /debt_void hanya bisa membatalkan debt yang belum pernah berubah."
            ),
            "debt": debt,
            "debt_row_index": row_index,
            "cashflow_txn": None,
            "reverse_deltas": {},
        }

    candidates = find_debt_initial_cashflow_candidates(debt)

    if len(candidates) == 0:
        # Piutang sering dibuat TANPA cashflow terpisah, terutama dari split bill:
        # transaksi utama tetap expense, sedangkan bagian teman hanya dicatat sebagai
        # piutang di sheet debts. Karena tidak ada saldo rekening yang pernah berubah
        # dari debt row ini, void yang aman adalah debt-only void: cukup tandai debt
        # sebagai settled/void tanpa mencari/menghapus transaksi cashflow.
        #
        # Patch penting: jangan bergantung pada description berisi "split bill".
        # Data lama bisa saja tidak punya label itu, sehingga /debt_void 5 gagal
        # dengan pesan "Cashflow transaksi terkait debt tidak ditemukan" meskipun
        # itemnya memang piutang aktif dari /hutang.
        if is_debt_without_initial_cashflow(debt):
            return {
                "success": True,
                "message": "ok",
                "debt": debt,
                "debt_row_index": row_index,
                "cashflow_txn": None,
                "candidate_txns": [],
                "reverse_deltas": {},
                "void_mode": "debt_only",
                "warning": (
                    "Cashflow terkait tidak ditemukan. Debt akan di-void tanpa "
                    "mengubah saldo rekening. Ini aman untuk split bill/talangan/ditalangin tanpa cashflow."
                ),
            }

        return {
            "success": False,
            "message": (
                "Cashflow transaksi terkait debt tidak ditemukan. Untuk utang/payable biasa, "
                "bot perlu cashflow awal supaya saldo bisa direverse dengan aman. "
                "Cek manual di sheet transactions."
            ),
            "debt": debt,
            "debt_row_index": row_index,
            "cashflow_txn": None,
            "reverse_deltas": {},
        }

    if len(candidates) > 1:
        return {
            "success": False,
            "message": (
                "Ditemukan lebih dari 1 cashflow yang mirip dengan debt ini. "
                "Bot menolak void otomatis agar saldo tidak salah. Rapikan manual dulu."
            ),
            "debt": debt,
            "debt_row_index": row_index,
            "cashflow_txn": None,
            "candidate_txns": candidates,
            "reverse_deltas": {},
        }

    cashflow_txn = candidates[0]

    from app.services.transaction_service import calculate_reverse_deltas_for_delete
    reverse_deltas = calculate_reverse_deltas_for_delete([cashflow_txn])

    return {
        "success": True,
        "message": "ok",
        "debt": debt,
        "debt_row_index": row_index,
        "cashflow_txn": cashflow_txn,
        "candidate_txns": candidates,
        "reverse_deltas": reverse_deltas,
    }


def update_debt(debt_ref: str, updates: dict, last_debt_map: dict | None = None) -> dict:
    """
    Edit debt/piutang aktif dengan aman.

    Field yang didukung:
    - person_name
    - type: payable / receivable
    - amount: update original_amount + remaining_amount, hanya jika belum ada mutasi pembayaran
    - description
    - due_date
    """
    row_index, debt, error = resolve_debt_ref(debt_ref, last_debt_map)

    if error:
        return {"success": False, "message": error, "debt": debt}

    if not debt or not row_index:
        return {"success": False, "message": "Debt tidak ditemukan.", "debt": debt}

    if is_settled_value(debt.get("is_settled", "FALSE")):
        return {"success": False, "message": "Debt ini sudah settled/void, jadi tidak bisa diedit.", "debt": debt}

    cleaned = {}
    for key, value in (updates or {}).items():
        if value is None:
            continue
        cleaned[key] = value

    if not cleaned:
        return {"success": False, "message": "Tidak ada field yang diedit.", "debt": debt}

    try:
        changed = {}

        if "person_name" in cleaned:
            new_person = normalize_person_name(cleaned.get("person_name"))
            if not new_person:
                return {"success": False, "message": "Nama orang tidak boleh kosong.", "debt": debt}
            update_cell(SHEET_DEBTS, row_index, DEBT_PERSON_COL, new_person)
            changed["person_name"] = {"old": debt.get("person_name"), "new": new_person}

        if "type" in cleaned:
            new_type = str(cleaned.get("type") or "").strip().lower()
            if new_type not in {"payable", "receivable"}:
                return {"success": False, "message": "Tipe debt harus payable/receivable.", "debt": debt}
            update_cell(SHEET_DEBTS, row_index, DEBT_TYPE_COL, new_type)
            changed["type"] = {"old": debt.get("type"), "new": new_type}

        if "amount" in cleaned:
            new_amount = float(cleaned.get("amount") or 0)
            if new_amount <= 0:
                return {"success": False, "message": "Nominal debt tidak valid.", "debt": debt}

            original = parse_sheet_number(debt.get("original_amount", 0))
            remaining = parse_sheet_number(debt.get("remaining_amount", 0))
            if abs(original - remaining) > 0.0001:
                return {
                    "success": False,
                    "message": (
                        "Debt ini sudah punya mutasi/pembayaran. Untuk keamanan, nominal tidak bisa diedit otomatis. "
                        "Void dulu atau rapikan manual di sheet."
                    ),
                    "debt": debt,
                }

            update_cell(SHEET_DEBTS, row_index, DEBT_ORIGINAL_AMOUNT_COL, new_amount)
            update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, new_amount)
            changed["amount"] = {"old": remaining, "new": new_amount}

        if "description" in cleaned:
            new_description = str(cleaned.get("description") or "").strip()
            update_cell(SHEET_DEBTS, row_index, DEBT_DESCRIPTION_COL, new_description)
            changed["description"] = {"old": debt.get("description"), "new": new_description}

        if "due_date" in cleaned:
            new_due_date = str(cleaned.get("due_date") or "").strip()
            update_cell(SHEET_DEBTS, row_index, DEBT_DUE_DATE_COL, new_due_date)
            changed["due_date"] = {"old": debt.get("due_date"), "new": new_due_date}

        if changed:
            append_debt_mutation(
                debt.get("id"),
                float(changed.get("amount", {}).get("new", 0) or 0),
                note=f"[edit] {changed}",
                mutation_type="edit",
            )

        _, updated_debt = get_debt_by_id_any_status(debt.get("id"))
        return {
            "success": True,
            "message": "ok",
            "debt": updated_debt or debt,
            "old_debt": debt,
            "changed": changed,
        }
    except Exception as e:
        return {"success": False, "message": str(e), "debt": debt}


def void_debt(debt_ref: str, last_debt_map: dict | None = None) -> dict:
    """
    Batalkan debt yang salah input dengan aman:
    1. Cari debt aktif.
    2. Cari 1 cashflow awal yang terkait.
    3. Reverse saldo rekening dari cashflow tersebut.
    4. Tandai debt settled/void.
    5. Hapus cashflow transaksi terkait.
    """
    preview = preview_void_debt(debt_ref, last_debt_map)

    if not preview.get("success"):
        return preview

    debt = preview["debt"]
    debt_row_index = int(preview["debt_row_index"])
    cashflow_txn = preview["cashflow_txn"]
    reverse_deltas = preview.get("reverse_deltas", {})
    today = datetime.now().strftime("%Y-%m-%d")

    if cashflow_txn and reverse_deltas:
        try:
            from app.services.transaction_service import apply_account_deltas
            balance_result = apply_account_deltas(reverse_deltas)
            if balance_result.get("failed_accounts"):
                return {
                    "success": False,
                    "message": "Rekening tidak ditemukan: " + ", ".join(balance_result["failed_accounts"]),
                    "debt": debt,
                    "cashflow_txn": cashflow_txn,
                    "reverse_deltas": reverse_deltas,
                    "new_balances": {},
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Gagal reverse saldo rekening: {str(e)}",
                "debt": debt,
                "cashflow_txn": cashflow_txn,
                "reverse_deltas": reverse_deltas,
                "new_balances": {},
            }
    else:
        balance_result = {"new_balances": {}}

    try:
        old_description = str(debt.get("description", "") or "").strip()
        void_note = f"[VOID {today}] Dibatalkan lewat /debt_void"
        new_description = f"{old_description} | {void_note}" if old_description else void_note

        update_cell(SHEET_DEBTS, debt_row_index, DEBT_REMAINING_AMOUNT_COL, 0)
        update_cell(SHEET_DEBTS, debt_row_index, DEBT_IS_SETTLED_COL, "TRUE")
        update_cell(SHEET_DEBTS, debt_row_index, DEBT_SETTLED_AT_COL, today)
        update_cell(SHEET_DEBTS, debt_row_index, DEBT_DESCRIPTION_COL, new_description)

        append_debt_mutation(
            debt_id=debt.get("id"),
            amount=parse_sheet_number(debt.get("original_amount", 0)),
            note=void_note,
            mutation_type="void",
        )
    except Exception as e:
        return {
            "success": False,
            "message": (
                "Saldo rekening sudah direverse, tapi debt gagal ditandai void. "
                f"Cek manual di sheet. Error: {str(e)}"
            ),
            "debt": debt,
            "cashflow_txn": cashflow_txn,
            "reverse_deltas": reverse_deltas,
            "new_balances": balance_result.get("new_balances", {}),
        }

    if cashflow_txn:
        try:
            txn_row = int(cashflow_txn.get("_row_index"))
            delete_rows("transactions", [txn_row])
        except Exception as e:
            return {
                "success": False,
                "message": (
                    "Debt sudah ditandai void dan saldo sudah direverse, "
                    "tapi cashflow transaksi gagal dihapus. Cek manual di sheet transactions. "
                    f"Error: {str(e)}"
                ),
                "debt": debt,
                "cashflow_txn": cashflow_txn,
                "reverse_deltas": reverse_deltas,
                "new_balances": balance_result.get("new_balances", {}),
            }

    return {
        "success": True,
        "message": "ok",
        "debt": debt,
        "cashflow_txn": cashflow_txn,
        "reverse_deltas": reverse_deltas,
        "new_balances": balance_result.get("new_balances", {}),
    }
