"""Debt service for payables, receivables, payments, settlement, void, edit, and cashflow relation logic."""


from datetime import datetime
import re
from app.sheets.client import (
    append_row,
    get_all_records,
    update_cell,
    delete_rows,
    rollback_current_sheets_transaction,
)
from app.config import SHEET_DEBTS, SHEET_DEBT_PAYMENTS


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_sheet_number(value, default: float = 0.0) -> float:
    """Parse input into structured data for sheet number."""
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
        # Debt flow section
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
    """Format data into a readable display for rupiah."""
    value = float(amount or 0)
    if abs(value - round(value)) < 1e-9:
        return f"Rp{int(round(value)):,}".replace(",", ".")

    sign = "-" if value < 0 else ""
    value = abs(value)
    integer_part = int(value)
    decimal_part = (f"{value:.2f}".split(".", 1)[1]).rstrip("0")
    return f"Rp{sign}{integer_part:,}".replace(",", ".") + f",{decimal_part}"


def generate_debt_id() -> str:
    """Helper for generate debt id in the finance service layer."""
    return datetime.now().strftime("debt_%Y%m%d_%H%M%S_%f")


def generate_payment_id() -> str:
    """Helper for generate payment id in the finance service layer."""
    return datetime.now().strftime("pay_%Y%m%d_%H%M%S_%f")


def normalize_person_name(name: str) -> str:
    """Normalize and clean input for person name."""
    if not name:
        return ""

    return " ".join(str(name).strip().split()).title()


def normalize_debt_person_group_name(name: str) -> str:
    """Normalize and clean input for debt person group name."""
    person = normalize_person_name(name)
    if not person:
        return ""

    prefixes = [
        "Cash", "BRI", "BSI", "BCA", "DANA", "GoPay",
        "Seabank", "Sea Bank",
    ]
    lower_person = person.lower()

    for prefix in prefixes:
        prefix_lower = prefix.lower() + " "
        if lower_person.startswith(prefix_lower):
            stripped = person[len(prefix):].strip()
            return normalize_person_name(stripped) or person

    return person


def is_settled_value(value) -> bool:
    """Check whether a condition is true for settled value."""
    return str(value).strip().upper() == "TRUE"


def get_debt_row_by_id(debt_id: str) -> tuple[int | None, dict | None]:
    """Get data needed for debt row by id."""
    records = get_all_records(SHEET_DEBTS)

    for i, record in enumerate(records):
        if str(record.get("id", "")) == str(debt_id):
            return i + 2, record

    return None, None


def get_active_debt_exact_person(person_name: str) -> tuple[int | None, dict | None]:
    """Get data needed for active debt exact person."""
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
    """Append data to debt mutation."""
    payment_row = [
        generate_payment_id(),
        debt_id,
        amount,
        datetime.now().strftime("%Y-%m-%d"),
        f"[{mutation_type}] {note}".strip(),
    ]
    append_row(SHEET_DEBT_PAYMENTS, payment_row)


# Debt flow section

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
    """Create a payable or receivable row in the debts sheet.

    Args:
        debt_type: Debt direction. Use `payable` when the user owes another
            person, or `receivable` when another person owes the user.
        person_name: Counterparty name as typed or parsed from Telegram input.
        amount: Original debt amount in rupiah. The value must be positive.
        description: Human-readable reason shown in debt detail commands.
        due_date: Optional due date string. Empty value means no due date.
        source_transaction_id: Optional transaction id linked to this debt.
        cashflow_mode: Optional marker for the initial cashflow behavior. Use
            `debt_only` when the debt row must not imply an account-balance
            mutation.
        fronting_mode: Optional parser/source marker, for example `talangin`,
            `ditalangin`, `catat_utang`, or settlement overpayment modes.

    Returns:
        Result dict with `success`, `debt_id`, `type`, `person_name`,
        `original_amount`, `remaining`, `message`, and `action` keys. When
        validation fails, `success` is false and no sheet row is appended.
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


    # Debt flow section
    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
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

    # Legacy compatibility note for older records or older in-memory state.
    # Debt flow section

    existing_row, existing = get_active_debt_exact_person(person_name)

    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # 6=description, 7=due_date, 8=is_settled, 9=created_at, 10=settled_at
    TYPE_COL = 2
    ORIGINAL_AMOUNT_COL = 4
    REMAINING_COL = 5
    DESCRIPTION_COL = 6
    DUE_DATE_COL = 7
    IS_SETTLED_COL = 8
    SETTLED_AT_COL = 10

    # Implementation section
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

    # Implementation section
    debt_id = existing.get("id")
    existing_type = existing.get("type")
    existing_remaining = parse_sheet_number(existing.get("remaining_amount", 0))
    existing_original = parse_sheet_number(existing.get("original_amount", 0))
    existing_description = existing.get("description", "") or ""

    try:
        if existing_type == debt_type:
            # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
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
    """Get data needed for active debts."""
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
    """Get data needed for debt by person."""
    target = normalize_person_name(person_name)
    result = []

    for record in get_debts_with_row_index(active_only=True):
        current_name = normalize_person_name(record.get("person_name", ""))

        if target not in current_name and current_name not in target:
            continue

        result.append(record)

    return result


def add_payment(debt_id: str, amount: float, note: str = "") -> dict:
    """Helper for add payment in the finance service layer."""
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



def add_payment_by_person(
    person_name: str,
    amount: float,
    note: str = "",
    target_debt_type: str | None = None,
    overpayment_policy: str | None = None,
) -> dict:
    """Helper for add payment by person in the finance service layer."""
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

    debts_before = get_debt_by_person(person_name)
    if not debts_before:
        return {
            "success": False,
            "message": f"Tidak ada utang/piutang aktif dengan {person_name}.",
            "remaining": 0,
            "is_settled": False,
            "allocations": [],
        }

    target_debt_type = str(target_debt_type or "").strip().lower()
    if target_debt_type == "auto":
        target_debt_type = ""

    def _active_rows_by_type(rows: list[dict], debt_type: str) -> list[dict]:
        """Helper for active rows by type in the finance service layer."""
        return [
            d for d in rows
            if str(d.get("type", "")).strip() == debt_type
            and parse_sheet_number(d.get("remaining_amount", 0)) > 0
            and not is_voided_debt(d)
        ]

    def _total_rows(rows: list[dict]) -> float:
        """Helper for total rows in the finance service layer."""
        return sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in rows)

    payable_before_rows = _active_rows_by_type(debts_before, "payable")
    receivable_before_rows = _active_rows_by_type(debts_before, "receivable")
    total_payable_before = _total_rows(payable_before_rows)
    total_receivable_before = _total_rows(receivable_before_rows)
    debt_types = {
        str(d.get("type", "")).strip()
        for d in debts_before
        if str(d.get("type", "")).strip()
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
        and not is_voided_debt(d)
    }

    if target_debt_type not in {"payable", "receivable"}:
        if total_receivable_before > total_payable_before:
            target_debt_type = "receivable"
        elif total_payable_before > total_receivable_before:
            target_debt_type = "payable"
        elif len(debt_types) == 1:
            target_debt_type = next(iter(debt_types))
        else:
            return {
                "success": False,
                "message": (
                    f"Ada utang dan piutang aktif dengan {person_name}. "
                    "Pakai input yang lebih spesifik: `Raka bayar hutang 50k` untuk piutang, "
                    "atau `bayar hutang Raka 50k` untuk utang Anda."
                ),
                "remaining": total_payable_before + total_receivable_before,
                "is_settled": False,
                "allocations": [],
            }

    opposite_type = "payable" if target_debt_type == "receivable" else "receivable"
    target_debts = receivable_before_rows if target_debt_type == "receivable" else payable_before_rows
    opposite_debts = payable_before_rows if target_debt_type == "receivable" else receivable_before_rows
    target_total_before = _total_rows(target_debts)
    opposite_total_before = _total_rows(opposite_debts)

    if not target_debts:
        label = "utang" if target_debt_type == "payable" else "piutang"
        return {
            "success": False,
            "message": f"Tidak ada {label} aktif dengan {person_name}.",
            "remaining": total_payable_before + total_receivable_before,
            "is_settled": False,
            "allocations": [],
        }

    # Debt flow section
    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    offset_capacity = min(target_total_before, opposite_total_before)
    net_payment_capacity = max(0.0, target_total_before - offset_capacity)
    net_overpayment = max(0.0, amount - net_payment_capacity)
    overpayment_policy = str(overpayment_policy or "").strip().lower()

    if net_overpayment > 0 and overpayment_policy not in {"bonus", "opposite_debt", "debt", "hutang"}:
        return {
            "success": False,
            "message": (
                "Pembayaran melebihi saldo net debt aktif. "
                "Pilih perlakuan overpaid terlebih dahulu."
            ),
            "remaining": target_total_before,
            "remaining_payable": total_payable_before,
            "remaining_receivable": total_receivable_before,
            "net_remaining": total_receivable_before - total_payable_before,
            "is_settled": False,
            "allocations": [],
            "overpayment": net_overpayment,
            "type": target_debt_type,
        }

    allocations: list[dict] = []

    def _allocate(rows: list[dict], total_amount: float, allocation_type: str, allocation_note: str) -> float:
        """Helper for allocate in the finance service layer."""
        amount_left = max(0.0, float(total_amount or 0))
        allocated_total = 0.0
        for debt in sorted(rows, key=_debt_row_sort_key_for_settlement):
            if amount_left <= 0:
                break
            debt_id = str(debt.get("id", "")).strip()
            debt_remaining = parse_sheet_number(debt.get("remaining_amount", 0))
            if not debt_id or debt_remaining <= 0:
                continue
            pay_amount = min(amount_left, debt_remaining)
            result = add_payment(debt_id, pay_amount, allocation_note)
            if not result.get("success"):
                raise RuntimeError(result.get("message", "Gagal alokasi pembayaran."))
            allocations.append({
                "debt_id": debt_id,
                "amount": pay_amount,
                "description": debt.get("description", ""),
                "type": allocation_type,
            })
            amount_left -= pay_amount
            allocated_total += pay_amount
        return allocated_total

    try:
        offset_amount = offset_capacity if opposite_total_before > 0 else 0.0
        cash_amount_for_target = min(amount, net_payment_capacity)
        target_allocation_amount = min(target_total_before, offset_amount + cash_amount_for_target)
        opposite_allocation_amount = min(opposite_total_before, offset_amount)

        if target_allocation_amount > 0:
            _allocate(
                target_debts,
                target_allocation_amount,
                target_debt_type,
                note or f"Pembayaran debt {person_name}",
            )
        if opposite_allocation_amount > 0:
            _allocate(
                opposite_debts,
                opposite_allocation_amount,
                opposite_type,
                f"Offset silang otomatis saat pembayaran debt {person_name}: {note or '-'}",
            )
    except RuntimeError as exc:
        return {
            "success": False,
            "message": str(exc),
            "remaining": sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in get_debt_by_person(person_name)),
            "is_settled": False,
            "allocations": allocations,
        }

    overpayment_created = None
    if net_overpayment > 0 and overpayment_policy in {"opposite_debt", "debt", "hutang"}:
        # Debt flow section
        # Debt flow section
        created = add_debt(
            opposite_type,
            person_name,
            net_overpayment,
            description=f"Kelebihan bayar net debt: {note or 'pembayaran debt'}",
            cashflow_mode="debt_only",
            fronting_mode="overpayment_from_payment",
        )
        if not created.get("success"):
            rollback_current_sheets_transaction()
            return {
                "success": False,
                "message": "Pembayaran gagal disimpan penuh; perubahan sebelumnya sudah dibatalkan. Gagal mencatat overpaid sebagai debt lawan arah: " + created.get("message", ""),
                "remaining": 0,
                "is_settled": False,
                "allocations": allocations,
                "overpayment": net_overpayment,
            }
        overpayment_created = created

    active_after = get_debt_by_person(person_name)
    payable_after_rows = _active_rows_by_type(active_after, "payable")
    receivable_after_rows = _active_rows_by_type(active_after, "receivable")
    total_payable_after = _total_rows(payable_after_rows)
    total_receivable_after = _total_rows(receivable_after_rows)
    remaining_same_type = total_receivable_after if target_debt_type == "receivable" else total_payable_after
    affected_debt_ids = [a.get("debt_id") for a in allocations if a.get("debt_id")]
    if overpayment_created and overpayment_created.get("debt_id"):
        affected_debt_ids.append(overpayment_created.get("debt_id"))

    return {
        "success": True,
        "message": "ok",
        "remaining": remaining_same_type,
        "remaining_payable": total_payable_after,
        "remaining_receivable": total_receivable_after,
        "net_remaining": total_receivable_after - total_payable_after,
        "is_settled": remaining_same_type <= 0,
        "allocations": allocations,
        "netting": {
            "offset_amount": offset_capacity,
            "target_debt_type": target_debt_type,
            "opposite_debt_type": opposite_type,
        } if offset_capacity > 0 else None,
        "net_settlement": offset_capacity > 0,
        "overpayment": net_overpayment,
        "overpayment_policy": overpayment_policy,
        "overpayment_created": overpayment_created,
        "type": target_debt_type,
        "debt_id": ", ".join([x for x in affected_debt_ids if x]),
        "affected_debt_ids": [x for x in affected_debt_ids if x],
    }

def estimate_payment_outcome(person_name: str, amount: float, target_debt_type: str) -> dict:
    """Helper for estimate payment outcome in the finance service layer."""
    person_name = normalize_person_name(person_name)
    amount = float(amount or 0)
    target_debt_type = str(target_debt_type or "").strip().lower()
    debts = get_debt_by_person(person_name)

    def _active_rows(debt_type: str) -> list[dict]:
        """Helper for active rows in the finance service layer."""
        return [
            d for d in debts
            if str(d.get("type", "")).strip() == debt_type
            and parse_sheet_number(d.get("remaining_amount", 0)) > 0
            and not is_voided_debt(d)
        ]

    payable_rows = _active_rows("payable")
    receivable_rows = _active_rows("receivable")
    total_payable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in payable_rows)
    total_receivable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in receivable_rows)

    if target_debt_type == "receivable":
        target_remaining = total_receivable
        opposite_remaining = total_payable
    else:
        target_remaining = total_payable
        opposite_remaining = total_receivable

    offset_amount = min(target_remaining, opposite_remaining)
    net_payment_capacity = max(0.0, target_remaining - offset_amount)
    overpayment = max(0.0, amount - net_payment_capacity)
    cash_applied_to_target = min(amount, net_payment_capacity)
    target_remaining_after = max(0.0, target_remaining - offset_amount - cash_applied_to_target)
    opposite_remaining_after = max(0.0, opposite_remaining - offset_amount)

    if target_debt_type == "receivable":
        total_receivable_after = target_remaining_after
        total_payable_after = opposite_remaining_after
    else:
        total_payable_after = target_remaining_after
        total_receivable_after = opposite_remaining_after

    return {
        "person_name": person_name,
        "target_debt_type": target_debt_type,
        "amount": amount,
        "target_remaining_before": target_remaining,
        "opposite_remaining_before": opposite_remaining,
        "net_payment_capacity": net_payment_capacity,
        "offset_amount": offset_amount,
        "remaining_same_type": target_remaining_after,
        "overpayment": overpayment,
        "remaining_payable_before": total_payable,
        "remaining_receivable_before": total_receivable,
        "remaining_payable_after": total_payable_after,
        "remaining_receivable_after": total_receivable_after,
        "net_remaining_after": total_receivable_after - total_payable_after,
    }


def format_debt_net_position_lines(person_name: str, remaining_payable: float, remaining_receivable: float) -> list[str]:
    """Format data into a readable display for debt net position lines."""
    net = float(remaining_receivable or 0) - float(remaining_payable or 0)
    lines = [
        f"📊 Sisa piutang: {format_rupiah(remaining_receivable)}",
        f"📊 Sisa utang Anda: {format_rupiah(remaining_payable)}",
    ]
    if net > 0:
        lines.append(f"🟢 Posisi akhir: {person_name} masih hutang ke Anda {format_rupiah(net)}")
    elif net < 0:
        lines.append(f"🔴 Posisi akhir: Anda masih hutang ke {person_name} {format_rupiah(abs(net))}")
    else:
        lines.append(f"⚪ Posisi akhir: debt dengan {person_name} netral/lunas")
    return lines


def offset_debt_by_person(
    person_name: str,
    amount: float,
    description: str = "",
    target_debt_type: str = "receivable",
    resulting_debt_type: str = "payable",
) -> dict:
    """Helper for offset debt by person in the finance service layer."""
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
                rollback_current_sheets_transaction()
                return {
                    "success": False,
                    "message": "Offset gagal disimpan penuh; perubahan sebelumnya sudah dibatalkan. Gagal membuat sisa debt: " + created.get("message", ""),
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

def _debt_row_sort_key_for_settlement(debt: dict) -> tuple[int, str]:
    """Helper for debt row sort key for settlement in the finance service layer."""
    try:
        row_index = int((debt or {}).get("_row_index", 10**9) or 10**9)
    except Exception:
        row_index = 10**9
    debt_id = str((debt or {}).get("id", "") or "")
    return (row_index, debt_id)


def _reduce_debt_remaining_for_settlement(debt: dict, amount: float, note: str, mutation_type: str) -> dict:
    """Helper for reduce debt remaining for settlement in the finance service layer."""
    debt_id = str((debt or {}).get("id", "") or "").strip()
    row_index = int((debt or {}).get("_row_index") or 0)
    current_remaining = parse_sheet_number((debt or {}).get("remaining_amount", 0))
    amount = min(float(amount or 0), current_remaining)
    if not debt_id or not row_index or amount <= 0:
        return {"success": False, "message": "Debt/amount tidak valid.", "debt_id": debt_id, "amount": 0.0}

    new_remaining = max(0.0, current_remaining - amount)
    is_settled = new_remaining <= 0.0001
    today = datetime.now().strftime("%Y-%m-%d")

    update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, 0 if is_settled else new_remaining)
    update_cell(SHEET_DEBTS, row_index, DEBT_IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")
    if is_settled:
        update_cell(SHEET_DEBTS, row_index, DEBT_SETTLED_AT_COL, today)

    append_debt_mutation(
        debt_id=debt_id,
        amount=amount,
        note=note,
        mutation_type=mutation_type,
    )

    return {
        "success": True,
        "debt_id": debt_id,
        "amount": amount,
        "description": (debt or {}).get("description", ""),
        "remaining_after": 0 if is_settled else new_remaining,
        "type": (debt or {}).get("type", ""),
    }


def settle_opposite_debts_by_person(person_name: str, amount: float | None = None, note: str = "Netting hutang-piutang") -> dict:
    """Helper for settle opposite debts by person in the finance service layer."""
    person_name = normalize_person_name(person_name)
    if not person_name:
        return {"success": False, "message": "Nama orang kosong.", "offset_amount": 0.0, "allocations": []}

    active_debts = [
        d for d in get_debt_by_person(person_name)
        if not is_voided_debt(d)
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
        and str(d.get("type", "")).strip() in {"payable", "receivable"}
    ]

    payables = [d for d in active_debts if str(d.get("type", "")).strip() == "payable"]
    receivables = [d for d in active_debts if str(d.get("type", "")).strip() == "receivable"]
    total_payable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in payables)
    total_receivable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in receivables)
    max_offset = min(total_payable, total_receivable)

    if max_offset <= 0:
        return {
            "success": True,
            "message": "Tidak ada hutang/piutang berlawanan yang perlu di-netting.",
            "offset_amount": 0.0,
            "allocations": [],
            "remaining_payable": total_payable,
            "remaining_receivable": total_receivable,
        }

    offset_amount = max_offset if amount is None else min(float(amount or 0), max_offset)
    if offset_amount <= 0:
        return {"success": False, "message": "Nominal netting tidak valid.", "offset_amount": 0.0, "allocations": []}

    mutation_note = note or "Netting hutang-piutang"
    mutation_type = "netting"
    payable_allocations = []
    receivable_allocations = []

    try:
        remaining_offset = offset_amount
        for debt in sorted(payables, key=_debt_row_sort_key_for_settlement):
            if remaining_offset <= 0:
                break
            pay_amount = min(remaining_offset, parse_sheet_number(debt.get("remaining_amount", 0)))
            result = _reduce_debt_remaining_for_settlement(debt, pay_amount, mutation_note, mutation_type)
            if not result.get("success"):
                return result
            payable_allocations.append(result)
            remaining_offset -= pay_amount

        remaining_offset = offset_amount
        for debt in sorted(receivables, key=_debt_row_sort_key_for_settlement):
            if remaining_offset <= 0:
                break
            pay_amount = min(remaining_offset, parse_sheet_number(debt.get("remaining_amount", 0)))
            result = _reduce_debt_remaining_for_settlement(debt, pay_amount, mutation_note, mutation_type)
            if not result.get("success"):
                return result
            receivable_allocations.append(result)
            remaining_offset -= pay_amount

        active_after = get_debt_by_person(person_name)
        remaining_payable = sum(
            parse_sheet_number(d.get("remaining_amount", 0))
            for d in active_after
            if not is_voided_debt(d) and str(d.get("type", "")).strip() == "payable"
        )
        remaining_receivable = sum(
            parse_sheet_number(d.get("remaining_amount", 0))
            for d in active_after
            if not is_voided_debt(d) and str(d.get("type", "")).strip() == "receivable"
        )

        return {
            "success": True,
            "message": "ok",
            "person_name": person_name,
            "offset_amount": offset_amount,
            "payable_allocations": payable_allocations,
            "receivable_allocations": receivable_allocations,
            "allocations": payable_allocations + receivable_allocations,
            "affected_debt_ids": [a.get("debt_id") for a in payable_allocations + receivable_allocations if a.get("debt_id")],
            "remaining_payable": remaining_payable,
            "remaining_receivable": remaining_receivable,
            "net_remaining": remaining_receivable - remaining_payable,
        }
    except Exception as e:
        return {"success": False, "message": str(e), "offset_amount": 0.0, "allocations": []}


def is_voided_debt(record: dict) -> bool:
    """Check whether a condition is true for voided debt."""
    description = str(record.get("description", "") or "")
    return "[VOID" in description.upper()


def get_debt_person_summary() -> dict:
    """Get data needed for debt person summary."""
    # Debt flow section
    # Debt flow section
    # Schema compatibility note for Google Sheets headers and rows.
    source_rows = [d for d in get_debts_with_row_index(active_only=True) if not is_voided_debt(d)]

    groups: dict[str, dict] = {}

    for debt in source_rows:
        if is_voided_debt(debt):
            continue

        person = normalize_debt_person_group_name(debt.get("person_name", ""))
        if not person:
            continue

        group = groups.setdefault(person, {
            "person_name": person,
            "payable_total": 0.0,
            "receivable_total": 0.0,
            "debt_count": 0,
            "details": [],
        })

        debt_type = str(debt.get("type", "")).strip()
        remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        if remaining <= 0:
            continue

        if debt_type == "payable":
            group["payable_total"] += remaining
        elif debt_type == "receivable":
            group["receivable_total"] += remaining
        else:
            continue

        group["debt_count"] += 1
        group["details"].append(debt)

    payables = []
    receivables = []
    balanced = []

    for group in groups.values():
        net = group["receivable_total"] - group["payable_total"]
        group["net_amount"] = net
        group["raw_total"] = group["receivable_total"] + group["payable_total"]

        if net > 0:
            item = dict(group)
            item["type"] = "receivable"
            item["remaining_amount"] = net
            receivables.append(item)
        elif net < 0:
            item = dict(group)
            item["type"] = "payable"
            item["remaining_amount"] = abs(net)
            payables.append(item)
        elif group["debt_count"] > 0:
            item = dict(group)
            item["type"] = "balanced"
            item["remaining_amount"] = 0.0
            balanced.append(item)

    payables.sort(key=lambda x: x.get("person_name", ""))
    receivables.sort(key=lambda x: x.get("person_name", ""))
    balanced.sort(key=lambda x: x.get("person_name", ""))

    return {
        "total_payable": sum(parse_sheet_number(x.get("remaining_amount", 0)) for x in payables),
        "total_receivable": sum(parse_sheet_number(x.get("remaining_amount", 0)) for x in receivables),
        "payables": payables,
        "receivables": receivables,
        "balanced": balanced,
    }


def get_debt_person_detail(person_name: str, include_settled: bool = True) -> dict:
    """Get data needed for debt person detail."""
    target = normalize_debt_person_group_name(person_name)
    raw_target = normalize_person_name(person_name)
    rows = get_debts_with_row_index(active_only=not include_settled)
    details = []

    for debt in rows:
        person_raw = normalize_person_name(debt.get("person_name", ""))
        person_key = normalize_debt_person_group_name(person_raw)
        if not person_key:
            continue
        # Legacy compatibility note for older records or older in-memory state.
        if target != person_key and raw_target not in person_raw and person_raw not in raw_target:
            continue
        if is_voided_debt(debt):
            continue
        details.append(debt)

    active_details = [
        d for d in details
        if not is_settled_value(d.get("is_settled", "FALSE"))
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
    ]

    def totals_for(rows_subset: list[dict], debt_type: str) -> dict:
        """Helper for totals for in the finance service layer."""
        original = sum(
            parse_sheet_number(d.get("original_amount", 0))
            for d in rows_subset
            if str(d.get("type", "")).strip() == debt_type
        )
        remaining = sum(
            parse_sheet_number(d.get("remaining_amount", 0))
            for d in rows_subset
            if str(d.get("type", "")).strip() == debt_type
        )
        paid = max(0.0, original - remaining)
        pct = (paid / original * 100) if original > 0 else 0.0
        return {
            "original": original,
            "remaining": remaining,
            "paid": paid,
            "paid_pct": pct,
        }

    # Debt flow section
    # Debt flow section
    # Debt flow section
    payable_totals = totals_for(details, "payable")
    receivable_totals = totals_for(details, "receivable")
    active_payable = totals_for(active_details, "payable")
    active_receivable = totals_for(active_details, "receivable")

    net_remaining = active_receivable["remaining"] - active_payable["remaining"]

    def debt_display_sort_key(d: dict) -> tuple[str, int]:
        """Helper for debt display sort key in the finance service layer."""
        created = str(d.get("created_at", "") or "").strip()
        # Legacy compatibility note for older records or older in-memory state.
        m = re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", created)
        if m:
            created = m.group(0).replace("/", "-")
        row_index = int(d.get("_row_index", 0) or 0)
        return (created, row_index)

    return {
        "person_name": target,
        "details": details,
        "active_details": sorted(active_details, key=debt_display_sort_key, reverse=True),
        "payable": payable_totals,
        "receivable": receivable_totals,
        "active_payable": active_payable,
        "active_receivable": active_receivable,
        "net_remaining": net_remaining,
        "net_type": "receivable" if net_remaining > 0 else "payable" if net_remaining < 0 else "balanced",
    }


def get_debt_summary() -> dict:
    """Get data needed for debt summary."""
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




# Debt flow section

def summarize_debt_rows_for_settlement(debts: list[dict]) -> dict:
    """Summarize data for debt rows for settlement."""
    selected = []
    total_receivable = 0.0
    total_payable = 0.0

    for debt in debts or []:
        if not debt or is_voided_debt(debt):
            continue
        remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        if remaining <= 0:
            continue
        debt_type = str(debt.get("type", "") or "").strip().lower()
        if debt_type not in {"receivable", "payable"}:
            continue
        item = dict(debt)
        item["remaining_amount"] = remaining
        selected.append(item)
        if debt_type == "receivable":
            total_receivable += remaining
        else:
            total_payable += remaining

    net_amount = total_receivable - total_payable
    if abs(net_amount) <= 0.0001:
        net_type = "balanced"
    elif net_amount > 0:
        net_type = "receivable"
    else:
        net_type = "payable"

    return {
        "selected": selected,
        "count": len(selected),
        "total_receivable": total_receivable,
        "total_payable": total_payable,
        "net_amount": net_amount,
        "net_abs": abs(net_amount),
        "net_type": net_type,
    }


def settle_selected_debt_ids(
    person_name: str,
    debt_ids: list[str],
    note: str = "",
    overpayment_amount: float = 0.0,
    overpayment_policy: str | None = None,
    net_type: str | None = None,
) -> dict:
    """Helper for settle selected debt ids in the finance service layer."""
    person = normalize_person_name(person_name)
    clean_ids = [str(x or "").strip() for x in (debt_ids or []) if str(x or "").strip()]
    if not person:
        return {"success": False, "message": "Nama orang kosong.", "settled": []}
    if not clean_ids:
        return {"success": False, "message": "Tidak ada debt terpilih.", "settled": []}

    rows = []
    seen = set()
    for debt_id in clean_ids:
        if debt_id in seen:
            continue
        seen.add(debt_id)
        row_index, debt = get_debt_row_by_id(debt_id)
        if not row_index or not debt:
            return {"success": False, "message": f"Debt {debt_id} tidak ditemukan.", "settled": rows}
        current_person = normalize_person_name(debt.get("person_name", ""))
        if current_person != person:
            return {
                "success": False,
                "message": f"Debt {debt_id} bukan milik {person}.",
                "settled": rows,
            }
        if is_voided_debt(debt):
            return {"success": False, "message": f"Debt {debt_id} sudah void.", "settled": rows}
        remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        if remaining <= 0:
            continue
        rows.append({"row_index": row_index, "debt": debt, "remaining": remaining})

    if not rows:
        return {"success": False, "message": "Semua debt terpilih sudah lunas/tidak aktif.", "settled": []}

    settled_items = []
    mutation_note = note or f"Settlement debt terpilih {person}"
    try:
        for item in rows:
            row_index = int(item["row_index"])
            debt = item["debt"]
            remaining = float(item["remaining"] or 0)
            debt_id = str(debt.get("id", "") or "").strip()
            _set_debt_remaining(row_index, 0, parse_sheet_number(debt.get("original_amount", 0)))
            append_debt_mutation(debt_id, remaining, mutation_note, mutation_type="selected_settle")
            settled_items.append({
                "debt_id": debt_id,
                "amount": remaining,
                "type": str(debt.get("type", "") or "").strip(),
                "description": debt.get("description", ""),
            })
    except Exception as e:
        return {"success": False, "message": str(e), "settled": settled_items}

    overpayment_amount = max(0.0, float(overpayment_amount or 0))
    overpayment_policy = str(overpayment_policy or "").strip().lower()
    overpayment_created = None
    if overpayment_amount > 0 and overpayment_policy in {"opposite_debt", "debt", "hutang"}:
        # Debt flow section
        # Debt flow section
        # Debt flow section
        opposite_type = "payable" if str(net_type or "").strip() == "receivable" else "receivable"
        created = add_debt(
            opposite_type,
            person,
            overpayment_amount,
            description=f"Kelebihan bayar settlement debt terpilih: {mutation_note}",
            cashflow_mode="debt_only",
            fronting_mode="overpayment_from_selected_settle",
        )
        if not created.get("success"):
            return {
                "success": False,
                "message": "Debt terpilih sudah disettle, tapi gagal mencatat overpaid: " + created.get("message", ""),
                "settled": settled_items,
                "overpayment": overpayment_amount,
            }
        overpayment_created = created

    active_after = get_debt_by_person(person)
    total_payable = sum(
        parse_sheet_number(d.get("remaining_amount", 0))
        for d in active_after
        if str(d.get("type", "") or "").strip() == "payable" and not is_voided_debt(d)
    )
    total_receivable = sum(
        parse_sheet_number(d.get("remaining_amount", 0))
        for d in active_after
        if str(d.get("type", "") or "").strip() == "receivable" and not is_voided_debt(d)
    )

    affected_ids = [x["debt_id"] for x in settled_items if x.get("debt_id")]
    if overpayment_created and overpayment_created.get("debt_id"):
        affected_ids.append(overpayment_created["debt_id"])

    return {
        "success": True,
        "message": "ok",
        "settled": settled_items,
        "allocations": settled_items,
        "overpayment": overpayment_amount,
        "overpayment_policy": overpayment_policy,
        "overpayment_created": overpayment_created,
        "affected_debt_ids": affected_ids,
        "remaining_payable": total_payable,
        "remaining_receivable": total_receivable,
        "net_remaining": total_receivable - total_payable,
    }

# Debt flow section

def parse_debt_allocation_note(note: str) -> list[dict]:
    """Parse input into structured data for debt allocation note."""
    raw = str(note or "")
    m = re.search(r"debt_allocations=([^|]+)", raw)
    if not m:
        return []
    payload = m.group(1).strip()
    result = []
    for part in payload.split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        debt_id, amount_raw = part.split(":", 1)
        amount = parse_sheet_number(amount_raw)
        if debt_id.strip() and amount > 0:
            result.append({"debt_id": debt_id.strip(), "amount": amount})
    return result


def _set_debt_remaining(row_index: int, new_remaining: float, original_amount: float | None = None):
    """Set a value for debt remaining."""
    original = float(original_amount or 0)
    remaining = max(0.0, float(new_remaining or 0))
    is_settled = remaining <= 0.0001
    update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, 0 if is_settled else remaining)
    update_cell(SHEET_DEBTS, row_index, DEBT_IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")
    update_cell(SHEET_DEBTS, row_index, DEBT_SETTLED_AT_COL, datetime.now().strftime("%Y-%m-%d") if is_settled else "")


def reverse_debt_payment_transaction(txn: dict) -> dict:
    """Helper for reverse debt payment transaction in the finance service layer."""
    txn = txn or {}
    category = str(txn.get("category", "") or "").strip()
    if category not in {"Pembayaran Piutang", "Bayar Utang"}:
        return {"success": True, "message": "Bukan transaksi payment debt.", "reversed": []}

    amount_left = parse_sheet_number(txn.get("amount", 0))
    note_text = str(txn.get("catatan", "") or "")
    is_selected_settle = "selected_settle=1" in note_text
    is_net_settle = "net_settle=1" in note_text
    if amount_left <= 0 and not (is_selected_settle or is_net_settle):
        return {"success": False, "message": "Nominal transaksi payment tidak valid.", "reversed": []}

    allocations = parse_debt_allocation_note(note_text)
    if not allocations:
        debt_ids = [x.strip() for x in re.split(r"[,;\s]+", str(txn.get("hutang_id", "") or "")) if x.strip()]
        allocations = [{"debt_id": debt_id, "amount": None} for debt_id in debt_ids]

    if not allocations:
        return {"success": False, "message": "Transaksi payment tidak punya hutang_id/allocation untuk dibalikkan.", "reversed": []}

    reversed_items = []
    failed = []
    today_note = f"Reverse payment karena transaksi {txn.get('id') or '-'} dihapus/diedit"

    # Debt flow section
    # Debt flow section
    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    if is_selected_settle or is_net_settle:
        amount_left = sum(parse_sheet_number(a.get("amount")) for a in allocations)

    for alloc in allocations:
        debt_id = str(alloc.get("debt_id") or "").strip()
        if not debt_id or amount_left <= 0:
            continue
        row_index, debt = get_debt_row_by_id(debt_id)
        if not row_index or not debt:
            failed.append(f"{debt_id}: debt tidak ditemukan")
            continue
        original = parse_sheet_number(debt.get("original_amount", 0))
        current_remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        room = max(0.0, original - current_remaining)
        if room <= 0:
            continue
        alloc_amount = alloc.get("amount")
        if (is_selected_settle or is_net_settle) and alloc_amount is not None:
            reverse_amount = min(room, parse_sheet_number(alloc_amount))
        else:
            reverse_amount = min(amount_left, room, parse_sheet_number(alloc_amount) if alloc_amount is not None else amount_left)
        if reverse_amount <= 0:
            continue
        new_remaining = min(original, current_remaining + reverse_amount)
        _set_debt_remaining(row_index, new_remaining, original)
        append_debt_mutation(debt_id, -reverse_amount, today_note, mutation_type="reverse_payment")
        reversed_items.append({"debt_id": debt_id, "amount": reverse_amount, "remaining_after": new_remaining})
        amount_left -= reverse_amount

    # Debt flow section
    # ketika transaction settlement/payment di-delete.
    overpay_id_match = re.search(r"overpayment_debt_id=([^|;\s]+)", note_text)
    if overpay_id_match:
        overpay_debt_id = overpay_id_match.group(1).strip()
        row_index, debt = get_debt_row_by_id(overpay_debt_id)
        if row_index and debt:
            current_remaining = parse_sheet_number(debt.get("remaining_amount", 0))
            if current_remaining > 0:
                _set_debt_remaining(row_index, 0, parse_sheet_number(debt.get("original_amount", 0)))
                append_debt_mutation(overpay_debt_id, current_remaining, today_note, mutation_type="reverse_overpayment_debt")
                reversed_items.append({"debt_id": overpay_debt_id, "amount": current_remaining, "remaining_after": 0})

    if failed:
        return {"success": False, "message": "; ".join(failed), "reversed": reversed_items}

    return {
        "success": True,
        "message": "ok",
        "reversed": reversed_items,
        "unreversed_amount": max(0.0, amount_left),
    }

# Debt flow section

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
    """Get data needed for debts with row index."""
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
    """Get data needed for debt by id any status."""
    target = str(debt_id or "").strip()
    if not target:
        return None, None

    for item in get_debts_with_row_index(active_only=False):
        if str(item.get("id", "")).strip() == target:
            return int(item.get("_row_index")), item

    return None, None


def build_active_debt_display_map() -> dict[str, dict]:
    """Build the data structure or message text for active debt display map."""
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
    """Resolve a user input or reference for debt ref."""
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
        # Debt flow section
        # Debt flow section
        # Debt flow section
        # Debt flow section
        return None, None, "Nomor debt tidak valid. Jalankan /hutang Nama dulu, lalu pakai nomor rincian yang muncul."

    row, debt = get_debt_by_id_any_status(clean)
    if not debt:
        return None, None, "Debt ID tidak ditemukan."

    return row, debt, None


def expected_initial_cashflow_category(debt: dict) -> str:
    """Helper for expected initial cashflow category in the finance service layer."""
    debt_type = str(debt.get("type", "")).strip()
    if debt_type == "payable":
        return "Penerimaan Utang"
    if debt_type == "receivable":
        return "Piutang Diberikan"
    return ""


def find_debt_initial_cashflow_candidates(debt: dict) -> list[dict]:
    """Find a record for debt initial cashflow candidates."""
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

        # Debt flow section
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
    """Check whether a debt row was created without an initial account change.

    Args:
        debt: Debt sheet row. The row may include historical description
            markers, or explicit `cashflow_mode` and `fronting_mode` metadata.

    Returns:
        `True` when edit/void logic should not search for an initial cashflow
        transaction because the debt was intentionally recorded as debt-only.
    """
    debt_type = str(debt.get("type", "")).strip()
    description = str(debt.get("description", "") or "").strip().lower()
    cashflow_mode = str(debt.get("cashflow_mode", "") or "").strip().lower()
    fronting_mode = str(debt.get("fronting_mode", "") or "").strip().lower()

    if debt_type == "receivable":
        return True

    if cashflow_mode == "debt_only":
        return True

    # Parser metadata is more reliable than description text for new rows.
    debt_only_fronting_modes = {
        "catat_utang",
        "ditalangin",
        "sudah_berlalu",
        "overpayment_from_payment",
        "overpayment_from_selected_settle",
    }
    if fronting_mode in debt_only_fronting_modes:
        return True

    debt_only_markers = [
        "ditalangin",
        "tanpa cashflow",
        "tanpa ubah saldo",
        "tanpa update saldo",
        "debt_only",
        "catat utang",
        "nitip",
    ]
    return any(marker in description for marker in debt_only_markers)




def build_debts_index(records: list[dict] | None = None, active_only: bool = False) -> dict:
    """Build the data structure or message text for debts index."""
    if records is None:
        records = get_debts_with_row_index(active_only=active_only)

    by_id = {}
    by_source_txn = {}
    items = []

    for debt in records or []:
        item = dict(debt or {})
        if active_only and is_settled_value(item.get("is_settled", "FALSE")):
            continue

        debt_id = str(item.get("id", "") or "").strip()
        if not debt_id:
            continue

        items.append(item)
        by_id[debt_id] = item

        source_txn = str(item.get("source_transaction_id", "") or "").strip()
        if source_txn:
            by_source_txn.setdefault(source_txn, []).append(item)

    return {"items": items, "by_id": by_id, "by_source_txn": by_source_txn}


def get_debts_by_source_transaction_id(transaction_id: str, active_only: bool = True, debt_index: dict | None = None) -> list[dict]:
    """Get data needed for debts by source transaction id."""
    target = str(transaction_id or "").strip()
    if not target:
        return []

    if debt_index is not None:
        return list((debt_index.get("by_source_txn", {}) or {}).get(target, []) or [])

    result = []
    for debt in get_debts_with_row_index(active_only=active_only):
        if str(debt.get("source_transaction_id", "")).strip() == target:
            result.append(debt)
    return result


def parse_debt_ids_from_transaction_record(txn: dict) -> list[str]:
    """Parse input into structured data for debt ids from transaction record."""
    raw = str((txn or {}).get("hutang_id", "") or "").strip()
    if not raw:
        return []
    parts = re.split(r"[,;|]", raw)
    result = []
    seen = set()
    for part in parts:
        clean = str(part or "").strip()
        if clean and clean not in seen:
            result.append(clean)
            seen.add(clean)
    return result


def get_debts_linked_to_transaction_record(txn: dict, active_only: bool = False, debt_index: dict | None = None) -> list[dict]:
    """Get data needed for debts linked to transaction record."""
    txn_id = str((txn or {}).get("id", "") or "").strip()
    if debt_index is None:
        debt_index = build_debts_index(active_only=active_only)

    by_id = debt_index.get("by_id", {}) or {}
    by_source = debt_index.get("by_source_txn", {}) or {}
    result = []
    seen = set()

    for debt in by_source.get(txn_id, []) or []:
        debt_id = str(debt.get("id", "") or "").strip()
        if debt_id and debt_id not in seen:
            result.append(debt)
            seen.add(debt_id)

    for debt_id in parse_debt_ids_from_transaction_record(txn):
        debt = by_id.get(debt_id)
        if not debt:
            continue
        if active_only and is_settled_value(debt.get("is_settled", "FALSE")):
            continue
        clean = str(debt.get("id", "") or "").strip()
        if clean and clean not in seen:
            result.append(dict(debt))
            seen.add(clean)

    return result


def get_debt_paid_amount_from_state(debt: dict) -> float:
    """Get data needed for debt paid amount from state."""
    original = parse_sheet_number((debt or {}).get("original_amount", 0))
    remaining = parse_sheet_number((debt or {}).get("remaining_amount", 0))
    return max(0.0, original - remaining)


def find_overpaid_adjustment_for_debt(debt_id: str, debt_index: dict | None = None) -> tuple[int | None, dict | None]:
    """Find a record for overpaid adjustment for debt."""
    marker = f"overpaid:{str(debt_id or '').strip()}"
    if marker == "overpaid:":
        return None, None

    if debt_index is not None:
        matches = (debt_index.get("by_source_txn", {}) or {}).get(marker, []) or []
        if matches:
            debt = matches[0]
            return int(debt.get("_row_index") or 0), debt
        return None, None

    for debt in get_debts_with_row_index(active_only=False):
        if str(debt.get("source_transaction_id", "") or "").strip() == marker:
            return int(debt.get("_row_index") or 0), debt

    return None, None


def upsert_overpaid_adjustment(original_debt: dict, overpaid_amount: float, debt_index: dict | None = None) -> dict:
    """Helper for upsert overpaid adjustment in the finance service layer."""
    original_debt = original_debt or {}
    debt_id = str(original_debt.get("id", "") or "").strip()
    if not debt_id:
        return {"success": False, "message": "Debt sumber kosong.", "overpaid_amount": 0.0}

    overpaid_amount = max(0.0, float(overpaid_amount or 0))
    person = normalize_person_name(original_debt.get("person_name", ""))
    old_type = str(original_debt.get("type", "") or "").strip()
    if old_type not in {"payable", "receivable"} or not person:
        return {"success": False, "message": "Debt sumber tidak valid.", "overpaid_amount": overpaid_amount}

    adjustment_type = "payable" if old_type == "receivable" else "receivable"
    source_marker = f"overpaid:{debt_id}"
    today = datetime.now().strftime("%Y-%m-%d")
    description = f"[OVERPAID_ADJUSTMENT] Kelebihan pembayaran dari {debt_id}"
    row_index, existing = find_overpaid_adjustment_for_debt(debt_id, debt_index=debt_index)

    if existing and row_index:
        paid_on_adjustment = get_debt_paid_amount_from_state(existing)
        new_remaining = max(0.0, overpaid_amount - paid_on_adjustment)
        is_settled = new_remaining <= 0.0001
        old_original = parse_sheet_number(existing.get("original_amount", 0))

        update_cell(SHEET_DEBTS, row_index, DEBT_TYPE_COL, adjustment_type)
        update_cell(SHEET_DEBTS, row_index, DEBT_PERSON_COL, person)
        update_cell(SHEET_DEBTS, row_index, DEBT_ORIGINAL_AMOUNT_COL, overpaid_amount)
        update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, 0 if is_settled else new_remaining)
        update_cell(SHEET_DEBTS, row_index, DEBT_DESCRIPTION_COL, description)
        update_cell(SHEET_DEBTS, row_index, DEBT_IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")
        update_cell(SHEET_DEBTS, row_index, DEBT_SETTLED_AT_COL, today if is_settled else "")
        append_debt_mutation(
            existing.get("id"),
            overpaid_amount - old_original,
            f"Sync overpaid adjustment dari {debt_id}",
            mutation_type="sync_overpaid_adjustment",
        )
        return {
            "success": True,
            "action": "updated" if overpaid_amount > 0 else "settled",
            "debt_id": existing.get("id"),
            "type": adjustment_type,
            "person_name": person,
            "overpaid_amount": overpaid_amount,
            "remaining_amount": 0 if is_settled else new_remaining,
        }

    if overpaid_amount <= 0:
        return {"success": True, "action": "none", "overpaid_amount": 0.0}

    created = add_debt(
        adjustment_type,
        person,
        overpaid_amount,
        description=description,
        source_transaction_id=source_marker,
        cashflow_mode="overpaid_adjustment",
    )
    created["overpaid_amount"] = overpaid_amount
    created["type"] = adjustment_type
    return created


def sync_debt_charges_from_transaction_edit(old_txn: dict, new_txn: dict) -> dict:
    """Helper for sync debt charges from transaction edit in the finance service layer."""
    old_txn = old_txn or {}
    new_txn = new_txn or {}
    debt_index = build_debts_index(active_only=False)
    linked_debts = [
        d for d in get_debts_linked_to_transaction_record(old_txn, active_only=False, debt_index=debt_index)
        if not is_voided_debt(d)
    ]

    if not linked_debts:
        return {"success": True, "message": "Tidak ada debt charge terkait.", "updated": [], "overpaid": []}

    # Debt flow section
    # Debt flow section
    old_category = str(old_txn.get("category", "") or "").strip()
    new_category = str(new_txn.get("category", "") or "").strip()
    # Debt flow section
    # Debt flow section
    payment_categories = {"Pembayaran Piutang", "Bayar Utang"}
    if old_category in payment_categories or new_category in payment_categories:
        return {
            "success": False,
            "message": "Transaksi pembayaran hutang/piutang belum bisa di-sync dari edit umum. Pakai flow bayar_hutang/bayar_piutang.",
            "updated": [],
            "overpaid": [],
        }

    old_amount = parse_sheet_number(old_txn.get("amount", 0))
    new_amount = parse_sheet_number(new_txn.get("amount", 0))
    if old_amount <= 0 or new_amount <= 0:
        return {"success": False, "message": "Nominal transaksi lama/baru tidak valid.", "updated": [], "overpaid": []}

    ratio = new_amount / old_amount
    today = datetime.now().strftime("%Y-%m-%d")
    updated = []
    overpaid_items = []
    failed = []

    for debt in linked_debts:
        debt_id = str(debt.get("id", "") or "").strip()
        row_index = int(debt.get("_row_index") or 0)
        debt_type = str(debt.get("type", "") or "").strip()
        if not debt_id or not row_index or debt_type not in {"payable", "receivable"}:
            continue

        old_original = parse_sheet_number(debt.get("original_amount", 0))
        old_remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        paid_amount = max(0.0, old_original - old_remaining)
        new_original = max(0.0, old_original * ratio)
        new_remaining = max(0.0, new_original - paid_amount)
        overpaid_amount = max(0.0, paid_amount - new_original)
        is_settled = new_remaining <= 0.0001

        try:
            update_cell(SHEET_DEBTS, row_index, DEBT_ORIGINAL_AMOUNT_COL, new_original)
            update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, 0 if is_settled else new_remaining)
            update_cell(SHEET_DEBTS, row_index, DEBT_IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")
            update_cell(SHEET_DEBTS, row_index, DEBT_SETTLED_AT_COL, today if is_settled else "")

            append_debt_mutation(
                debt_id,
                new_original - old_original,
                (
                    f"Sync charge dari edit transaksi {new_txn.get('id') or old_txn.get('id')}: "
                    f"{format_rupiah(old_original)} -> {format_rupiah(new_original)}; "
                    f"paid tetap {format_rupiah(paid_amount)}"
                ),
                mutation_type="sync_charge_from_transaction",
            )

            adjustment = upsert_overpaid_adjustment(debt, overpaid_amount, debt_index=debt_index)
            if overpaid_amount > 0:
                overpaid_items.append({
                    "source_debt_id": debt_id,
                    "person_name": debt.get("person_name", ""),
                    "amount": overpaid_amount,
                    "adjustment": adjustment,
                })

            updated.append({
                "debt_id": debt_id,
                "person_name": debt.get("person_name", ""),
                "type": debt_type,
                "old_original": old_original,
                "new_original": new_original,
                "paid_amount": paid_amount,
                "new_remaining": 0 if is_settled else new_remaining,
                "overpaid_amount": overpaid_amount,
            })
        except Exception as e:
            failed.append({"debt_id": debt_id, "message": str(e)})

    if failed:
        return {
            "success": False,
            "message": "; ".join(f"{x.get('debt_id')}: {x.get('message')}" for x in failed),
            "updated": updated,
            "overpaid": overpaid_items,
            "failed": failed,
        }

    return {
        "success": True,
        "message": "ok",
        "updated": updated,
        "overpaid": overpaid_items,
        "ratio": ratio,
    }


def void_debts_for_transaction(transaction_id: str, debt_ids: list[str] | None = None) -> dict:
    """Helper for void debts for transaction in the finance service layer."""
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
    """Helper for void linked debt only in the finance service layer."""
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
    """Helper for preview void debt in the finance service layer."""
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
        # Debt flow section
        # Split bill parsing note: separate the paid transaction from each person share.
        # Debt flow section
        # Debt flow section
        # Debt flow section
        #
        # Clean leftover split-bill phrases so subject and description stay readable.
        # Legacy compatibility note for older records or older in-memory state.
        # Debt flow section
        # Debt flow section
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



def resolve_person_debt_targets(person_name: str, detail_ref: str | None = None) -> dict:
    """Resolve a user input or reference for person debt targets."""
    clean_person = normalize_person_name(person_name)
    clean_ref = str(detail_ref or "").strip()

    if not clean_person:
        return {"success": False, "message": "Nama orang tidak boleh kosong.", "person_name": clean_person, "targets": []}

    detail = get_debt_person_detail(clean_person, include_settled=True)
    active_details = detail.get("active_details") or []

    if not active_details:
        return {
            "success": False,
            "message": f"Tidak ada rincian debt aktif untuk {clean_person}.",
            "person_name": clean_person,
            "detail": detail,
            "targets": [],
        }

    if clean_ref:
        if clean_ref.isdigit():
            idx = int(clean_ref)
            if idx < 1 or idx > len(active_details):
                return {
                    "success": False,
                    "message": f"Nomor rincian tidak valid untuk {clean_person}. Pilih 1 sampai {len(active_details)} dari output /hutang {clean_person}.",
                    "person_name": clean_person,
                    "detail": detail,
                    "targets": [],
                }
            return {
                "success": True,
                "message": "ok",
                "person_name": clean_person,
                "detail": detail,
                "targets": [active_details[idx - 1]],
                "detail_ref": clean_ref,
                "scope": "person_detail",
            }

        # Legacy compatibility note for older records or older in-memory state.
        for debt in active_details:
            if str(debt.get("id", "")).strip() == clean_ref:
                return {
                    "success": True,
                    "message": "ok",
                    "person_name": clean_person,
                    "detail": detail,
                    "targets": [debt],
                    "detail_ref": clean_ref,
                    "scope": "person_detail",
                }

        return {
            "success": False,
            "message": f"Rincian {clean_ref} tidak ditemukan untuk {clean_person}.",
            "person_name": clean_person,
            "detail": detail,
            "targets": [],
        }

    return {
        "success": True,
        "message": "ok",
        "person_name": clean_person,
        "detail": detail,
        "targets": active_details,
        "detail_ref": "",
        "scope": "person_all",
    }


def preview_void_debts_by_person(person_name: str, detail_ref: str | None = None) -> dict:
    """Helper for preview void debts by person in the finance service layer."""
    resolved = resolve_person_debt_targets(person_name, detail_ref)
    if not resolved.get("success"):
        return {
            "success": False,
            "message": resolved.get("message"),
            "person_name": resolved.get("person_name") or normalize_person_name(person_name),
            "scope": resolved.get("scope") or ("person_detail" if detail_ref else "person_all"),
            "detail_ref": str(detail_ref or "").strip(),
            "targets": [],
            "previews": [],
            "reverse_deltas": {},
            "cashflow_txns": [],
        }

    previews = []
    failed = []
    total_remaining = 0.0
    total_original = 0.0
    reverse_deltas: dict[str, float] = {}
    cashflow_txns = []

    for debt in resolved.get("targets") or []:
        debt_id = str(debt.get("id", "")).strip()
        item_preview = preview_void_debt(debt_id, {})
        previews.append(item_preview)

        if not item_preview.get("success"):
            failed.append(item_preview)
            continue

        preview_debt = item_preview.get("debt") or debt
        total_remaining += parse_sheet_number(preview_debt.get("remaining_amount", 0))
        total_original += parse_sheet_number(preview_debt.get("original_amount", 0))

        if item_preview.get("cashflow_txn"):
            cashflow_txns.append(item_preview.get("cashflow_txn"))

        for account, delta in (item_preview.get("reverse_deltas") or {}).items():
            reverse_deltas[account] = reverse_deltas.get(account, 0.0) + float(delta or 0)

    if failed:
        messages = []
        for failed_preview in failed[:5]:
            debt = failed_preview.get("debt") or {}
            desc = str(debt.get("description") or debt.get("id") or "-").strip()
            messages.append(f"- {desc}: {failed_preview.get('message')}")
        return {
            "success": False,
            "message": "Beberapa rincian tidak bisa divoid otomatis:\n" + "\n".join(messages),
            "person_name": resolved.get("person_name"),
            "scope": resolved.get("scope"),
            "detail_ref": resolved.get("detail_ref"),
            "targets": resolved.get("targets") or [],
            "previews": previews,
            "failed_previews": failed,
            "reverse_deltas": reverse_deltas,
            "cashflow_txns": cashflow_txns,
        }

    return {
        "success": True,
        "message": "ok",
        "person_name": resolved.get("person_name"),
        "scope": resolved.get("scope"),
        "detail_ref": resolved.get("detail_ref"),
        "targets": resolved.get("targets") or [],
        "previews": previews,
        "reverse_deltas": reverse_deltas,
        "cashflow_txns": cashflow_txns,
        "target_debt_ids": [str((p.get("debt") or {}).get("id", "")).strip() for p in previews if (p.get("debt") or {}).get("id")],
        "total_remaining": total_remaining,
        "total_original": total_original,
        "bulk": True,
    }


def void_debt_ids(debt_ids: list[str]) -> dict:
    """Helper for void debt ids in the finance service layer."""
    clean_ids = []
    seen = set()
    for debt_id in debt_ids or []:
        clean = str(debt_id or "").strip()
        if clean and clean not in seen:
            clean_ids.append(clean)
            seen.add(clean)

    if not clean_ids:
        return {"success": False, "message": "Tidak ada debt_id yang akan divoid.", "results": []}

    results = []
    for debt_id in clean_ids:
        results.append(void_debt(debt_id, {}))

    failed = [r for r in results if not r.get("success")]
    success_results = [r for r in results if r.get("success")]

    reverse_deltas: dict[str, float] = {}
    new_balances = {}
    total_original = 0.0
    total_remaining = 0.0
    debts = []
    cashflow_txns = []

    for result in success_results:
        debt = result.get("debt") or {}
        debts.append(debt)
        total_original += parse_sheet_number(debt.get("original_amount", 0))
        total_remaining += parse_sheet_number(debt.get("remaining_amount", 0))
        if result.get("cashflow_txn"):
            cashflow_txns.append(result.get("cashflow_txn"))
        for account, delta in (result.get("reverse_deltas") or {}).items():
            reverse_deltas[account] = reverse_deltas.get(account, 0.0) + float(delta or 0)
        for account, balance in (result.get("new_balances") or {}).items():
            new_balances[account] = balance

    return {
        "success": not failed,
        "message": "ok" if not failed else "; ".join(str(r.get("message") or "Gagal void debt") for r in failed),
        "results": results,
        "failed": failed,
        "success_results": success_results,
        "debts": debts,
        "cashflow_txns": cashflow_txns,
        "reverse_deltas": reverse_deltas,
        "new_balances": new_balances,
        "total_original": total_original,
        "total_remaining": total_remaining,
        "voided_ids": [str((r.get("debt") or {}).get("id", "")).strip() for r in success_results],
    }


def void_debts_by_person(person_name: str, detail_ref: str | None = None) -> dict:
    """Helper for void debts by person in the finance service layer."""
    preview = preview_void_debts_by_person(person_name, detail_ref)
    if not preview.get("success"):
        return preview

    result = void_debt_ids(preview.get("target_debt_ids") or [])
    result.update({
        "person_name": preview.get("person_name"),
        "scope": preview.get("scope"),
        "detail_ref": preview.get("detail_ref"),
        "bulk": True,
    })
    return result

def update_debt(debt_ref: str, updates: dict, last_debt_map: dict | None = None) -> dict:
    """Update existing data for debt."""
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
    """Helper for void debt in the finance service layer."""
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
        rollback_current_sheets_transaction()
        return {
            "success": False,
            "message": (
                "Debt void gagal disimpan penuh. Perubahan sebelumnya sudah dibatalkan. "
                f"Error: {str(e)}"
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
            rollback_current_sheets_transaction()
            return {
                "success": False,
                "message": (
                    "Debt void gagal menghapus cashflow. Perubahan sebelumnya sudah dibatalkan. "
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
