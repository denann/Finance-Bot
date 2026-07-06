"""Debt service for payables, receivables, payments, settlement, void, edit, and cashflow relation logic."""


# Import datetime so this module can use its helpers.
from datetime import datetime
# Import re for this module's local operations.
import re
# Import app.sheets.client so this module can use its helpers.
from app.sheets.client import (
    # Include this value in the surrounding collection or call.
    append_row,
    # Include this value in the surrounding collection or call.
    get_all_records,
    # Include this value in the surrounding collection or call.
    update_cell,
    # Include this value in the surrounding collection or call.
    delete_rows,
    # Include this value in the surrounding collection or call.
    rollback_current_sheets_transaction,
# Close the structure that was opened above.
)
# Import app.config so this module can use its helpers.
from app.config import SHEET_DEBTS, SHEET_DEBT_PAYMENTS


# ── Helpers ───────────────────────────────────────────────────────────────────

# Define parse sheet number for callers in this flow.
def parse_sheet_number(value, default: float = 0.0) -> float:
    """Parse a Google Sheets numeric value into float.

    Args:
        value: Sheet value, already numeric or Indonesian-formatted text such
            as `71.387,5`, `71.387`, or `Rp71.387`.
        default: Fallback returned when parsing fails.

    Returns:
        Parsed float, or `default` for blank/invalid values.
    """
    if value is None or value == "":
        # Return default to the caller.
        return default
    # Handle the case where isinstance(value, (int, float)).
    if isinstance(value, (int, float)):
        # Return float(value) to the caller.
        return float(value)

    # Prepare raw for the next step.
    raw = str(value).strip()
    # Handle the missing or empty raw case.
    if not raw:
        # Return default to the caller.
        return default

    raw = raw.replace("Rp", "").replace("rp", "").replace("IDR", "").replace("idr", "")
    raw = raw.replace(" ", "")

    if "," in raw and "." in raw:
        # Format Indonesia: 71.387,5
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        # Debt flow section
        raw = raw.replace(",", ".")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Format ribuan biasa: 71.387
        parts = raw.split(".")
        # Handle the case where len(parts) > 1 and all(len(p) == 3 for p in parts[1:]).
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            raw = raw.replace(".", "")

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Return float(raw) to the caller.
        return float(raw)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return default to the caller.
        return default


# Define format rupiah for callers in this flow.
def format_rupiah(amount: float) -> str:
    """Format data into a readable display for rupiah."""
    # Prepare value for the next step.
    value = float(amount or 0)
    # Handle the case where abs(value - round(value)) < 1e-9.
    if abs(value - round(value)) < 1e-9:
        return f"Rp{int(round(value)):,}".replace(",", ".")

    sign = "-" if value < 0 else ""
    # Prepare value for the next step.
    value = abs(value)
    # Prepare integer part for the next step.
    integer_part = int(value)
    decimal_part = (f"{value:.2f}".split(".", 1)[1]).rstrip("0")
    return f"Rp{sign}{integer_part:,}".replace(",", ".") + f",{decimal_part}"


# Define generate debt id for callers in this flow.
def generate_debt_id() -> str:
    """Generate a unique debt ID for the debts sheet."""
    return datetime.now().strftime("debt_%Y%m%d_%H%M%S_%f")


# Define generate payment id for callers in this flow.
def generate_payment_id() -> str:
    """Coordinate the generate payment id logic in the service layer.

    Args:
        None.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    return datetime.now().strftime("pay_%Y%m%d_%H%M%S_%f")


# Define normalize person name for callers in this flow.
def normalize_person_name(name: str) -> str:
    """Normalize input values for the normalize person name workflow in the service layer.

    Args:
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
    """
    # Handle the missing or empty name case.
    if not name:
        return ""

    return " ".join(str(name).strip().split()).title()


# Define normalize debt person group name for callers in this flow.
def normalize_debt_person_group_name(name: str) -> str:
    """Normalize input values for the normalize debt person group name workflow in the service layer.

    Args:
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Prepare person for the next step.
    person = normalize_person_name(name)
    # Handle the missing or empty person case.
    if not person:
        return ""

    # Open a multi-line structure for the values below.
    prefixes = [
        "Cash", "BRI", "BSI", "BCA", "DANA", "GoPay",
        "Seabank", "Sea Bank",
    # Close the structure that was opened above.
    ]
    # Prepare lower person for the next step.
    lower_person = person.lower()

    # Process each prefix in the current collection.
    for prefix in prefixes:
        prefix_lower = prefix.lower() + " "
        # Handle the case where lower_person.startswith(prefix_lower).
        if lower_person.startswith(prefix_lower):
            # Prepare stripped for the next step.
            stripped = person[len(prefix):].strip()
            # Return normalize_person_name(stripped) or person to the caller.
            return normalize_person_name(stripped) or person

    # Return person to the caller.
    return person


# Define is settled value for callers in this flow.
def is_settled_value(value) -> bool:
    """Check whether a condition is true for settled value."""
    return str(value).strip().upper() == "TRUE"


# Define get debt row by id for callers in this flow.
def get_debt_row_by_id(debt_id: str) -> tuple[int | None, dict | None]:
    """Find one debt row by full debt ID.

    Args:
        debt_id: Full debt ID from the `debts` sheet.

    Returns:
        Tuple of one-based sheet row index and debt record. Both values are
        `None` when no matching debt exists.
    """
    # Prepare records for the next step.
    records = get_all_records(SHEET_DEBTS)

    # Process each i, record in the current collection.
    for i, record in enumerate(records):
        if str(record.get("id", "")) == str(debt_id):
            # Return i + 2, record to the caller.
            return i + 2, record

    # Return None, None to the caller.
    return None, None


# Define get active debt exact person for callers in this flow.
def get_active_debt_exact_person(person_name: str) -> tuple[int | None, dict | None]:
    """Find the first active debt row for an exact normalized person name.

    Args:
        person_name: Counterparty name to match exactly after normalization.

    Returns:
        Tuple of one-based row index and debt record, or `(None, None)`.
    """
    # Prepare target for the next step.
    target = normalize_person_name(person_name)
    # Prepare records for the next step.
    records = get_all_records(SHEET_DEBTS)

    # Process each i, record in the current collection.
    for i, record in enumerate(records):
        current_name = normalize_person_name(record.get("person_name", ""))
        # Handle the case where current_name != target.
        if current_name != target:
            # Skip the rest of this loop iteration after handling this case.
            continue

        if is_settled_value(record.get("is_settled", "FALSE")):
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Return i + 2, record to the caller.
        return i + 2, record

    # Return None, None to the caller.
    return None, None


# Define append debt mutation for callers in this flow.
def append_debt_mutation(
    # Include this value in the surrounding collection or call.
    debt_id: str,
    # Include this value in the surrounding collection or call.
    amount: float,
    note: str = "",
    mutation_type: str = "payment",
# Close the structure that was opened above.
):
    """Apply the append debt mutation operation in the service layer.

    Args:
        debt_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        amount: Numeric amount or amount-like user input to parse or format.
        note: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        mutation_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Open a multi-line structure for the values below.
    payment_row = [
        # Include this value in the surrounding collection or call.
        generate_payment_id(),
        # Include this value in the surrounding collection or call.
        debt_id,
        # Include this value in the surrounding collection or call.
        amount,
        datetime.now().strftime("%Y-%m-%d"),
        f"[{mutation_type}] {note}".strip(),
    # Close the structure that was opened above.
    ]
    # Run this statement as part of the current workflow.
    append_row(SHEET_DEBT_PAYMENTS, payment_row)


# Debt flow section

# Define add debt for callers in this flow.
def add_debt(
    # Include this value in the surrounding collection or call.
    debt_type: str,
    # Include this value in the surrounding collection or call.
    person_name: str,
    # Include this value in the surrounding collection or call.
    amount: float,
    description: str = "",
    due_date: str = "",
    source_transaction_id: str = "",
    cashflow_mode: str = "",
    fronting_mode: str = "",
# Close the structure that was opened above.
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
    # Prepare person name for the next step.
    person_name = normalize_person_name(person_name)
    # Prepare amount for the next step.
    amount = float(amount or 0)

    if debt_type not in ["payable", "receivable"]:
        # Return { to the caller.
        return {
            "success": False,
            "debt_id": None,
            "message": "Tipe debt tidak valid.",
            "action": "error",
        # Close the structure that was opened above.
        }

    # Handle the missing or empty person_name case.
    if not person_name:
        # Return { to the caller.
        return {
            "success": False,
            "debt_id": None,
            "message": "Nama orang kosong.",
            "action": "error",
        # Close the structure that was opened above.
        }

    # Handle the case where amount <= 0.
    if amount <= 0:
        # Return { to the caller.
        return {
            "success": False,
            "debt_id": None,
            "message": "Nominal debt tidak valid.",
            "action": "error",
        # Close the structure that was opened above.
        }


    # Debt flow section
    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # is_settled, created_at, settled_at, source_transaction_id, cashflow_mode, fronting_mode
    debt_id = generate_debt_id()
    # Open a multi-line structure for the values below.
    row = [
        # Include this value in the surrounding collection or call.
        debt_id,
        # Include this value in the surrounding collection or call.
        debt_type,
        # Include this value in the surrounding collection or call.
        person_name,
        # Include this value in the surrounding collection or call.
        amount,
        # Include this value in the surrounding collection or call.
        amount,
        # Include this value in the surrounding collection or call.
        description,
        # Include this value in the surrounding collection or call.
        due_date,
        "FALSE",
        datetime.now().strftime("%Y-%m-%d"),
        "",
        source_transaction_id or "",
        cashflow_mode or "",
        fronting_mode or "",
    # Close the structure that was opened above.
    ]

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Run this statement as part of the current workflow.
        append_row(SHEET_DEBTS, row)
        # Open a multi-line structure for the values below.
        append_debt_mutation(
            # Include this value in the surrounding collection or call.
            debt_id,
            # Include this value in the surrounding collection or call.
            amount,
            description or f"Tambah {debt_type} {person_name}",
            mutation_type=f"add_{debt_type}",
        # Close the structure that was opened above.
        )
        # Return { to the caller.
        return {
            "success": True,
            "debt_id": debt_id,
            "message": "ok",
            "action": "created_granular",
            "person_name": person_name,
            "type": debt_type,
            "remaining": amount,
            "is_settled": False,
        # Close the structure that was opened above.
        }
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "debt_id": None,
            "message": str(e),
            "action": "error",
        # Close the structure that was opened above.
        }

    # Legacy compatibility note for older records or older in-memory state.
    # Debt flow section

    # Run this statement as part of the current workflow.
    existing_row, existing = get_active_debt_exact_person(person_name)

    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # 6=description, 7=due_date, 8=is_settled, 9=created_at, 10=settled_at
    TYPE_COL = 2
    # Prepare ORIGINAL AMOUNT COL for the next step.
    ORIGINAL_AMOUNT_COL = 4
    # Prepare REMAINING COL for the next step.
    REMAINING_COL = 5
    # Prepare DESCRIPTION COL for the next step.
    DESCRIPTION_COL = 6
    # Prepare DUE DATE COL for the next step.
    DUE_DATE_COL = 7
    # Prepare IS SETTLED COL for the next step.
    IS_SETTLED_COL = 8
    # Prepare SETTLED AT COL for the next step.
    SETTLED_AT_COL = 10

    # Implementation section
    if not existing:
        # Prepare debt id for the next step.
        debt_id = generate_debt_id()
        # Open a multi-line structure for the values below.
        row = [
            # Include this value in the surrounding collection or call.
            debt_id,
            # Include this value in the surrounding collection or call.
            debt_type,
            # Include this value in the surrounding collection or call.
            person_name,
            # Include this value in the surrounding collection or call.
            amount,
            # Include this value in the surrounding collection or call.
            amount,
            # Include this value in the surrounding collection or call.
            description,
            # Include this value in the surrounding collection or call.
            due_date,
            "FALSE",
            datetime.now().strftime("%Y-%m-%d"),
            "",
        # Close the structure that was opened above.
        ]

        # Run this operation in a guarded block so failures can be handled.
        try:
            # Run this statement as part of the current workflow.
            append_row(SHEET_DEBTS, row)
            # Open a multi-line structure for the values below.
            append_debt_mutation(
                # Include this value in the surrounding collection or call.
                debt_id,
                # Include this value in the surrounding collection or call.
                amount,
                description or f"Tambah {debt_type} {person_name}",
                mutation_type=f"add_{debt_type}",
            # Close the structure that was opened above.
            )
            # Return { to the caller.
            return {
                "success": True,
                "debt_id": debt_id,
                "message": "ok",
                "action": "created",
                "person_name": person_name,
                "type": debt_type,
                "remaining": amount,
                "is_settled": False,
            # Close the structure that was opened above.
            }
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            # Return { to the caller.
            return {
                "success": False,
                "debt_id": None,
                "message": str(e),
                "action": "error",
            # Close the structure that was opened above.
            }

    # Implementation section
    debt_id = existing.get("id")
    existing_type = existing.get("type")
    existing_remaining = parse_sheet_number(existing.get("remaining_amount", 0))
    existing_original = parse_sheet_number(existing.get("original_amount", 0))
    existing_description = existing.get("description", "") or ""

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Handle the case where existing_type == debt_type.
        if existing_type == debt_type:
            # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
            new_type = existing_type
            # Prepare new remaining for the next step.
            new_remaining = existing_remaining + amount
            # Prepare new original for the next step.
            new_original = existing_original + amount
            # Prepare is settled for the next step.
            is_settled = False
            action = "merged_same_direction"

        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Arah beda: netting
            if existing_remaining > amount:
                # Prepare new type for the next step.
                new_type = existing_type
                # Prepare new remaining for the next step.
                new_remaining = existing_remaining - amount
                # Prepare new original for the next step.
                new_original = existing_original
                # Prepare is settled for the next step.
                is_settled = False
                action = "netted_reduced"

            # Handle the alternate case where existing_remaining < amount.
            elif existing_remaining < amount:
                # Prepare new type for the next step.
                new_type = debt_type
                # Prepare new remaining for the next step.
                new_remaining = amount - existing_remaining
                # Prepare new original for the next step.
                new_original = new_remaining
                # Prepare is settled for the next step.
                is_settled = False
                action = "netted_flipped"

            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Prepare new type for the next step.
                new_type = existing_type
                # Prepare new remaining for the next step.
                new_remaining = 0
                # Prepare new original for the next step.
                new_original = existing_original
                # Prepare is settled for the next step.
                is_settled = True
                action = "netted_settled"

        # Prepare new description parts for the next step.
        new_description_parts = []
        # Handle the case where existing_description.
        if existing_description:
            # Update new description parts with the current value.
            new_description_parts.append(existing_description)
        # Handle the case where description.
        if description:
            # Update new description parts with the current value.
            new_description_parts.append(description)

        new_description = " | ".join(new_description_parts)
        # Handle the case where len(new_description) > 500.
        if len(new_description) > 500:
            # Prepare new description for the next step.
            new_description = new_description[-500:]

        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, existing_row, TYPE_COL, new_type)
        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, existing_row, ORIGINAL_AMOUNT_COL, new_original)
        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, existing_row, REMAINING_COL, new_remaining)
        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, existing_row, DESCRIPTION_COL, new_description)
        # Handle the case where due_date.
        if due_date:
            # Run this statement as part of the current workflow.
            update_cell(SHEET_DEBTS, existing_row, DUE_DATE_COL, due_date)
        update_cell(SHEET_DEBTS, existing_row, IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")
        # Open a multi-line structure for the values below.
        update_cell(
            # Include this value in the surrounding collection or call.
            SHEET_DEBTS,
            # Include this value in the surrounding collection or call.
            existing_row,
            # Include this value in the surrounding collection or call.
            SETTLED_AT_COL,
            datetime.now().strftime("%Y-%m-%d") if is_settled else "",
        # Close the structure that was opened above.
        )

        # Open a multi-line structure for the values below.
        append_debt_mutation(
            # Include this value in the surrounding collection or call.
            debt_id,
            # Include this value in the surrounding collection or call.
            amount,
            description or f"Tambah {debt_type} {person_name}",
            mutation_type=f"netting_{debt_type}",
        # Close the structure that was opened above.
        )

        # Return { to the caller.
        return {
            "success": True,
            "debt_id": debt_id,
            "message": "ok",
            "action": action,
            "person_name": person_name,
            "type": new_type,
            "remaining": new_remaining,
            "is_settled": is_settled,
        # Close the structure that was opened above.
        }

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "debt_id": debt_id,
            "message": str(e),
            "action": "error",
        # Close the structure that was opened above.
        }


# Define get active debts for callers in this flow.
def get_active_debts(debt_type: str = None) -> list[dict]:
    """Read active, unsettled debt rows.

    Args:
        debt_type: Optional exact type filter, usually `payable` or
            `receivable`.

    Returns:
        Active debt records that are not marked settled.
    """
    # Prepare records for the next step.
    records = get_all_records(SHEET_DEBTS)
    # Prepare result for the next step.
    result = []

    # Process each record in the current collection.
    for record in records:
        if is_settled_value(record.get("is_settled", "FALSE")):
            # Skip the rest of this loop iteration after handling this case.
            continue

        if debt_type and record.get("type") != debt_type:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Update result with the current value.
        result.append(record)

    # Return result to the caller.
    return result


# Define get debt by person for callers in this flow.
def get_debt_by_person(person_name: str) -> list[dict]:
    """Read active debts that match a counterparty name.

    Args:
        person_name: Counterparty name or partial normalized name.

    Returns:
        Active debt rows with `_row_index`, excluding settled rows.
    """
    # Prepare target for the next step.
    target = normalize_person_name(person_name)
    # Prepare result for the next step.
    result = []

    # Process each record in the current collection.
    for record in get_debts_with_row_index(active_only=True):
        current_name = normalize_person_name(record.get("person_name", ""))

        # Handle the case where target not in current_name and current_name not in target.
        if target not in current_name and current_name not in target:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Update result with the current value.
        result.append(record)

    # Return result to the caller.
    return result


def add_payment(debt_id: str, amount: float, note: str = "") -> dict:
    """Apply a payment/reduction to one debt ID.

    Args:
        debt_id: Full debt ID.
        amount: Positive amount to subtract from remaining debt.
        note: Mutation note stored in `debt_payments`.

    Returns:
        Result dict with remaining amount, settled flag, and message.

    Side effects:
        Updates remaining amount, settlement status/date, and appends a debt
        mutation row.
    """
    # Run this statement as part of the current workflow.
    debt_row_index, debt_record = get_debt_row_by_id(debt_id)

    # Handle the missing or empty debt_record case.
    if not debt_record:
        # Return { to the caller.
        return {
            "success": False,
            "remaining": 0,
            "is_settled": False,
            "message": f"Debt ID {debt_id} tidak ditemukan.",
        # Close the structure that was opened above.
        }

    # Prepare amount for the next step.
    amount = float(amount or 0)
    # Handle the case where amount <= 0.
    if amount <= 0:
        # Return { to the caller.
        return {
            "success": False,
            "remaining": parse_sheet_number(debt_record.get("remaining_amount", 0)),
            "is_settled": False,
            "message": "Nominal pembayaran tidak valid.",
        # Close the structure that was opened above.
        }

    current_remaining = parse_sheet_number(debt_record.get("remaining_amount", 0))
    # Prepare new remaining for the next step.
    new_remaining = max(0, current_remaining - amount)
    # Prepare is settled for the next step.
    is_settled = new_remaining == 0

    # Prepare REMAINING COL for the next step.
    REMAINING_COL = 5
    # Prepare IS SETTLED COL for the next step.
    IS_SETTLED_COL = 8
    # Prepare SETTLED AT COL for the next step.
    SETTLED_AT_COL = 10

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, debt_row_index, REMAINING_COL, new_remaining)
        update_cell(SHEET_DEBTS, debt_row_index, IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")

        # Handle the case where is_settled.
        if is_settled:
            # Open a multi-line structure for the values below.
            update_cell(
                # Include this value in the surrounding collection or call.
                SHEET_DEBTS,
                # Include this value in the surrounding collection or call.
                debt_row_index,
                # Include this value in the surrounding collection or call.
                SETTLED_AT_COL,
                datetime.now().strftime("%Y-%m-%d"),
            # Close the structure that was opened above.
            )

        # Open a multi-line structure for the values below.
        append_debt_mutation(
            # Include this value in the surrounding collection or call.
            debt_id,
            # Include this value in the surrounding collection or call.
            amount,
            note or "Pembayaran/pengurangan debt",
            mutation_type="payment",
        # Close the structure that was opened above.
        )

        # Return { to the caller.
        return {
            "success": True,
            "remaining": new_remaining,
            "is_settled": is_settled,
            "message": "ok",
        # Close the structure that was opened above.
        }

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "remaining": current_remaining,
            "is_settled": False,
            "message": str(e),
        # Close the structure that was opened above.
        }



# Define add payment by person for callers in this flow.
def add_payment_by_person(
    # Include this value in the surrounding collection or call.
    person_name: str,
    # Include this value in the surrounding collection or call.
    amount: float,
    note: str = "",
    # Include this value in the surrounding collection or call.
    target_debt_type: str | None = None,
    # Include this value in the surrounding collection or call.
    overpayment_policy: str | None = None,
# Close the structure that was opened above.
) -> dict:
    """Allocate a debt payment across active debts for one person.

    Args:
        person_name: Counterparty name.
        amount: Cash/payment amount.
        note: Mutation note for each allocation.
        target_debt_type: Optional target side, `payable`, `receivable`, or
            blank/`auto` to infer from net position.
        overpayment_policy: Policy for overpayment, such as `bonus` or
            `opposite_debt`.

    Returns:
        Result dict with allocations, remaining balances, netting metadata,
        overpayment metadata, and affected debt IDs.

    Side effects:
        Reduces target and opposite debts, appends payment mutations, and may
        create an opposite debt for overpayment.
    """
    # Prepare person name for the next step.
    person_name = normalize_person_name(person_name)
    # Prepare amount for the next step.
    amount = float(amount or 0)

    # Handle the missing or empty person_name case.
    if not person_name:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Nama orang kosong.",
            "remaining": 0,
            "is_settled": False,
            "allocations": [],
        # Close the structure that was opened above.
        }

    # Handle the case where amount <= 0.
    if amount <= 0:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Nominal pembayaran tidak valid.",
            "remaining": 0,
            "is_settled": False,
            "allocations": [],
        # Close the structure that was opened above.
        }

    # Prepare debts before for the next step.
    debts_before = get_debt_by_person(person_name)
    # Handle the missing or empty debts_before case.
    if not debts_before:
        # Return { to the caller.
        return {
            "success": False,
            "message": f"Tidak ada utang/piutang aktif dengan {person_name}.",
            "remaining": 0,
            "is_settled": False,
            "allocations": [],
        # Close the structure that was opened above.
        }

    target_debt_type = str(target_debt_type or "").strip().lower()
    if target_debt_type == "auto":
        target_debt_type = ""

    # Define active rows by type for callers in this flow.
    def _active_rows_by_type(rows: list[dict], debt_type: str) -> list[dict]:
        """Coordinate the active rows by type logic in the service layer.

        Args:
            rows: List of Google Sheets row dicts or row-like mappings.
            debt_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `list[dict]` value as defined by the function signature.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
        """
        # Return [ to the caller.
        return [
            # Run this statement as part of the current workflow.
            d for d in rows
            if str(d.get("type", "")).strip() == debt_type
            and parse_sheet_number(d.get("remaining_amount", 0)) > 0
            # Run this statement as part of the current workflow.
            and not is_voided_debt(d)
        # Close the structure that was opened above.
        ]

    # Define total rows for callers in this flow.
    def _total_rows(rows: list[dict]) -> float:
        """Coordinate the total rows logic in the service layer.

        Args:
            rows: List of Google Sheets row dicts or row-like mappings.

        Returns:
            `float` value as defined by the function signature.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
        """
        return sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in rows)

    payable_before_rows = _active_rows_by_type(debts_before, "payable")
    receivable_before_rows = _active_rows_by_type(debts_before, "receivable")
    # Prepare total payable before for the next step.
    total_payable_before = _total_rows(payable_before_rows)
    # Prepare total receivable before for the next step.
    total_receivable_before = _total_rows(receivable_before_rows)
    # Open a multi-line structure for the values below.
    debt_types = {
        str(d.get("type", "")).strip()
        # Process each d in the current collection.
        for d in debts_before
        if str(d.get("type", "")).strip()
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
        # Run this statement as part of the current workflow.
        and not is_voided_debt(d)
    # Close the structure that was opened above.
    }

    if target_debt_type not in {"payable", "receivable"}:
        # Handle the case where total_receivable_before > total_payable_before.
        if total_receivable_before > total_payable_before:
            target_debt_type = "receivable"
        # Handle the alternate case where total_payable_before > total_receivable_before.
        elif total_payable_before > total_receivable_before:
            target_debt_type = "payable"
        # Handle the alternate case where len(debt_types) == 1.
        elif len(debt_types) == 1:
            # Prepare target debt type for the next step.
            target_debt_type = next(iter(debt_types))
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Return { to the caller.
            return {
                "success": False,
                "message": (
                    f"Ada utang dan piutang aktif dengan {person_name}. "
                    "Pakai input yang lebih spesifik: `Raka bayar hutang 50k` untuk piutang, "
                    "atau `bayar hutang Raka 50k` untuk utang Anda."
                # Close the structure that was opened above.
                ),
                "remaining": total_payable_before + total_receivable_before,
                "is_settled": False,
                "allocations": [],
            # Close the structure that was opened above.
            }

    opposite_type = "payable" if target_debt_type == "receivable" else "receivable"
    target_debts = receivable_before_rows if target_debt_type == "receivable" else payable_before_rows
    opposite_debts = payable_before_rows if target_debt_type == "receivable" else receivable_before_rows
    # Prepare target total before for the next step.
    target_total_before = _total_rows(target_debts)
    # Prepare opposite total before for the next step.
    opposite_total_before = _total_rows(opposite_debts)

    # Handle the missing or empty target_debts case.
    if not target_debts:
        label = "utang" if target_debt_type == "payable" else "piutang"
        # Return { to the caller.
        return {
            "success": False,
            "message": f"Tidak ada {label} aktif dengan {person_name}.",
            "remaining": total_payable_before + total_receivable_before,
            "is_settled": False,
            "allocations": [],
        # Close the structure that was opened above.
        }

    # Debt flow section
    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    offset_capacity = min(target_total_before, opposite_total_before)
    # Prepare net payment capacity for the next step.
    net_payment_capacity = max(0.0, target_total_before - offset_capacity)
    # Prepare net overpayment for the next step.
    net_overpayment = max(0.0, amount - net_payment_capacity)
    overpayment_policy = str(overpayment_policy or "").strip().lower()

    if net_overpayment > 0 and overpayment_policy not in {"bonus", "opposite_debt", "debt", "hutang"}:
        # Return { to the caller.
        return {
            "success": False,
            "message": (
                "Pembayaran melebihi saldo net debt aktif. "
                "Pilih perlakuan overpaid terlebih dahulu."
            # Close the structure that was opened above.
            ),
            "remaining": target_total_before,
            "remaining_payable": total_payable_before,
            "remaining_receivable": total_receivable_before,
            "net_remaining": total_receivable_before - total_payable_before,
            "is_settled": False,
            "allocations": [],
            "overpayment": net_overpayment,
            "type": target_debt_type,
        # Close the structure that was opened above.
        }

    # Run this statement as part of the current workflow.
    allocations: list[dict] = []

    # Define allocate for callers in this flow.
    def _allocate(rows: list[dict], total_amount: float, allocation_type: str, allocation_note: str) -> float:
        """Allocate an amount across sorted debt rows of one type."""
        # Prepare amount left for the next step.
        amount_left = max(0.0, float(total_amount or 0))
        # Prepare allocated total for the next step.
        allocated_total = 0.0
        # Process each debt in the current collection.
        for debt in sorted(rows, key=_debt_row_sort_key_for_settlement):
            # Handle the case where amount_left <= 0.
            if amount_left <= 0:
                # Leave the loop after the target condition has been reached.
                break
            debt_id = str(debt.get("id", "")).strip()
            debt_remaining = parse_sheet_number(debt.get("remaining_amount", 0))
            # Handle the missing or empty debt_id or debt_remaining <= 0 case.
            if not debt_id or debt_remaining <= 0:
                # Skip the rest of this loop iteration after handling this case.
                continue
            # Prepare pay amount for the next step.
            pay_amount = min(amount_left, debt_remaining)
            # Prepare result for the next step.
            result = add_payment(debt_id, pay_amount, allocation_note)
            if not result.get("success"):
                raise RuntimeError(result.get("message", "Gagal alokasi pembayaran."))
            # Open a multi-line structure for the values below.
            allocations.append({
                "debt_id": debt_id,
                "amount": pay_amount,
                "description": debt.get("description", ""),
                "type": allocation_type,
            # Close the structure that was opened above.
            })
            # Run this statement as part of the current workflow.
            amount_left -= pay_amount
            # Run this statement as part of the current workflow.
            allocated_total += pay_amount
        # Return allocated_total to the caller.
        return allocated_total

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare offset amount for the next step.
        offset_amount = offset_capacity if opposite_total_before > 0 else 0.0
        # Prepare cash amount for target for the next step.
        cash_amount_for_target = min(amount, net_payment_capacity)
        # Prepare target allocation amount for the next step.
        target_allocation_amount = min(target_total_before, offset_amount + cash_amount_for_target)
        # Prepare opposite allocation amount for the next step.
        opposite_allocation_amount = min(opposite_total_before, offset_amount)

        # Handle the case where target_allocation_amount > 0.
        if target_allocation_amount > 0:
            # Open a multi-line structure for the values below.
            _allocate(
                # Include this value in the surrounding collection or call.
                target_debts,
                # Include this value in the surrounding collection or call.
                target_allocation_amount,
                # Include this value in the surrounding collection or call.
                target_debt_type,
                note or f"Pembayaran debt {person_name}",
            # Close the structure that was opened above.
            )
        # Handle the case where opposite_allocation_amount > 0.
        if opposite_allocation_amount > 0:
            # Open a multi-line structure for the values below.
            _allocate(
                # Include this value in the surrounding collection or call.
                opposite_debts,
                # Include this value in the surrounding collection or call.
                opposite_allocation_amount,
                # Include this value in the surrounding collection or call.
                opposite_type,
                f"Offset silang otomatis saat pembayaran debt {person_name}: {note or '-'}",
            # Close the structure that was opened above.
            )
    # Handle an expected failure from the guarded operation above.
    except RuntimeError as exc:
        # Return { to the caller.
        return {
            "success": False,
            "message": str(exc),
            "remaining": sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in get_debt_by_person(person_name)),
            "is_settled": False,
            "allocations": allocations,
        # Close the structure that was opened above.
        }

    # Prepare overpayment created for the next step.
    overpayment_created = None
    if net_overpayment > 0 and overpayment_policy in {"opposite_debt", "debt", "hutang"}:
        # Debt flow section
        # Debt flow section
        created = add_debt(
            # Include this value in the surrounding collection or call.
            opposite_type,
            # Include this value in the surrounding collection or call.
            person_name,
            # Include this value in the surrounding collection or call.
            net_overpayment,
            description=f"Kelebihan bayar net debt: {note or 'pembayaran debt'}",
            cashflow_mode="debt_only",
            fronting_mode="overpayment_from_payment",
        # Close the structure that was opened above.
        )
        if not created.get("success"):
            # Run this statement as part of the current workflow.
            rollback_current_sheets_transaction()
            # Return { to the caller.
            return {
                "success": False,
                "message": "Pembayaran gagal disimpan penuh; perubahan sebelumnya sudah dibatalkan. Gagal mencatat overpaid sebagai debt lawan arah: " + created.get("message", ""),
                "remaining": 0,
                "is_settled": False,
                "allocations": allocations,
                "overpayment": net_overpayment,
            # Close the structure that was opened above.
            }
        # Prepare overpayment created for the next step.
        overpayment_created = created

    # Prepare active after for the next step.
    active_after = get_debt_by_person(person_name)
    payable_after_rows = _active_rows_by_type(active_after, "payable")
    receivable_after_rows = _active_rows_by_type(active_after, "receivable")
    # Prepare total payable after for the next step.
    total_payable_after = _total_rows(payable_after_rows)
    # Prepare total receivable after for the next step.
    total_receivable_after = _total_rows(receivable_after_rows)
    remaining_same_type = total_receivable_after if target_debt_type == "receivable" else total_payable_after
    affected_debt_ids = [a.get("debt_id") for a in allocations if a.get("debt_id")]
    if overpayment_created and overpayment_created.get("debt_id"):
        affected_debt_ids.append(overpayment_created.get("debt_id"))

    # Return { to the caller.
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
        # Close the structure that was opened above.
        } if offset_capacity > 0 else None,
        "net_settlement": offset_capacity > 0,
        "overpayment": net_overpayment,
        "overpayment_policy": overpayment_policy,
        "overpayment_created": overpayment_created,
        "type": target_debt_type,
        "debt_id": ", ".join([x for x in affected_debt_ids if x]),
        "affected_debt_ids": [x for x in affected_debt_ids if x],
    # Close the structure that was opened above.
    }

# Define estimate payment outcome for callers in this flow.
def estimate_payment_outcome(person_name: str, amount: float, target_debt_type: str) -> dict:
    """Estimate payment/netting effects without mutating debt rows.

    Args:
        person_name: Counterparty name.
        amount: Candidate payment amount.
        target_debt_type: Debt side being paid, usually `payable` or
            `receivable`.

    Returns:
        Projection dict with before/after payable, receivable, net remaining,
        cash capacity, and overpayment.
    """
    # Prepare person name for the next step.
    person_name = normalize_person_name(person_name)
    # Prepare amount for the next step.
    amount = float(amount or 0)
    target_debt_type = str(target_debt_type or "").strip().lower()
    # Prepare debts for the next step.
    debts = get_debt_by_person(person_name)

    # Define active rows for callers in this flow.
    def _active_rows(debt_type: str) -> list[dict]:
        """Coordinate the active rows logic in the service layer.

        Args:
            debt_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `list[dict]` value as defined by the function signature.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Keep calculations consistent with report, debt, category, and transaction semantics already used by command handlers.
        """
        # Return [ to the caller.
        return [
            # Run this statement as part of the current workflow.
            d for d in debts
            if str(d.get("type", "")).strip() == debt_type
            and parse_sheet_number(d.get("remaining_amount", 0)) > 0
            # Run this statement as part of the current workflow.
            and not is_voided_debt(d)
        # Close the structure that was opened above.
        ]

    payable_rows = _active_rows("payable")
    receivable_rows = _active_rows("receivable")
    total_payable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in payable_rows)
    total_receivable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in receivable_rows)

    if target_debt_type == "receivable":
        # Prepare target remaining for the next step.
        target_remaining = total_receivable
        # Prepare opposite remaining for the next step.
        opposite_remaining = total_payable
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare target remaining for the next step.
        target_remaining = total_payable
        # Prepare opposite remaining for the next step.
        opposite_remaining = total_receivable

    # Prepare offset amount for the next step.
    offset_amount = min(target_remaining, opposite_remaining)
    # Prepare net payment capacity for the next step.
    net_payment_capacity = max(0.0, target_remaining - offset_amount)
    # Prepare overpayment for the next step.
    overpayment = max(0.0, amount - net_payment_capacity)
    # Prepare cash applied to target for the next step.
    cash_applied_to_target = min(amount, net_payment_capacity)
    # Prepare target remaining after for the next step.
    target_remaining_after = max(0.0, target_remaining - offset_amount - cash_applied_to_target)
    # Prepare opposite remaining after for the next step.
    opposite_remaining_after = max(0.0, opposite_remaining - offset_amount)

    if target_debt_type == "receivable":
        # Prepare total receivable after for the next step.
        total_receivable_after = target_remaining_after
        # Prepare total payable after for the next step.
        total_payable_after = opposite_remaining_after
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare total payable after for the next step.
        total_payable_after = target_remaining_after
        # Prepare total receivable after for the next step.
        total_receivable_after = opposite_remaining_after

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }


# Define format debt net position lines for callers in this flow.
def format_debt_net_position_lines(person_name: str, remaining_payable: float, remaining_receivable: float) -> list[str]:
    """Format data into a readable display for debt net position lines."""
    # Prepare net for the next step.
    net = float(remaining_receivable or 0) - float(remaining_payable or 0)
    # Open a multi-line structure for the values below.
    lines = [
        f"📊 Sisa piutang: {format_rupiah(remaining_receivable)}",
        f"📊 Sisa utang Anda: {format_rupiah(remaining_payable)}",
    # Close the structure that was opened above.
    ]
    # Handle the case where net > 0.
    if net > 0:
        lines.append(f"🟢 Posisi akhir: {person_name} masih hutang ke Anda {format_rupiah(net)}")
    # Handle the alternate case where net < 0.
    elif net < 0:
        lines.append(f"🔴 Posisi akhir: Anda masih hutang ke {person_name} {format_rupiah(abs(net))}")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        lines.append(f"⚪ Posisi akhir: debt dengan {person_name} netral/lunas")
    # Return lines to the caller.
    return lines


# Define offset debt by person for callers in this flow.
def offset_debt_by_person(
    # Include this value in the surrounding collection or call.
    person_name: str,
    # Include this value in the surrounding collection or call.
    amount: float,
    description: str = "",
    target_debt_type: str = "receivable",
    resulting_debt_type: str = "payable",
# Close the structure that was opened above.
) -> dict:
    """Offset one side of a person's debt without account cashflow.

    Args:
        person_name: Counterparty name.
        amount: Offset amount to apply.
        description: Mutation note/reason.
        target_debt_type: Existing debt side to reduce.
        resulting_debt_type: Side to create if offset amount exceeds target
            remaining debt.

    Returns:
        Result dict with allocations, created remainder debt, affected IDs, and
        final payable/receivable totals.

    Side effects:
        Reduces target debts, appends offset mutations, and may create a
        debt-only remainder on the opposite side.
    """
    # Prepare person name for the next step.
    person_name = normalize_person_name(person_name)
    # Prepare amount for the next step.
    amount = float(amount or 0)
    target_debt_type = str(target_debt_type or "receivable").strip().lower()
    resulting_debt_type = str(resulting_debt_type or "payable").strip().lower()

    if target_debt_type not in ["payable", "receivable"]:
        # Return { to the caller.
        return {
            "success": False,
            "message": "target_debt_type tidak valid.",
            "allocations": [],
            "affected_debt_ids": [],
        # Close the structure that was opened above.
        }

    if resulting_debt_type not in ["payable", "receivable"]:
        resulting_debt_type = "payable" if target_debt_type == "receivable" else "receivable"

    # Handle the missing or empty person_name case.
    if not person_name:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Nama orang kosong.",
            "allocations": [],
            "affected_debt_ids": [],
        # Close the structure that was opened above.
        }

    # Handle the case where amount <= 0.
    if amount <= 0:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Nominal offset tidak valid.",
            "allocations": [],
            "affected_debt_ids": [],
        # Close the structure that was opened above.
        }

    # Open a multi-line structure for the values below.
    debts = [
        # Run this statement as part of the current workflow.
        d for d in get_debt_by_person(person_name)
        if str(d.get("type", "")).strip() == target_debt_type
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
    # Close the structure that was opened above.
    ]

    # Handle the missing or empty debts case.
    if not debts:
        label = "piutang" if target_debt_type == "receivable" else "utang"
        # Return { to the caller.
        return {
            "success": False,
            "message": f"Tidak ada {label} aktif dengan {person_name} untuk dipotong.",
            "allocations": [],
            "affected_debt_ids": [],
        # Close the structure that was opened above.
        }

    # Prepare remaining offset for the next step.
    remaining_offset = amount
    # Prepare allocations for the next step.
    allocations = []
    # Prepare affected debt ids for the next step.
    affected_debt_ids = []
    today = datetime.now().strftime("%Y-%m-%d")
    note = description or "Kompensasi hutang-piutang"

    # Run this operation in a guarded block so failures can be handled.
    try:
        for debt in sorted(debts, key=lambda d: int(d.get("_row_index", 10**9) or 10**9)):
            # Handle the case where remaining_offset <= 0.
            if remaining_offset <= 0:
                # Leave the loop after the target condition has been reached.
                break

            debt_id = str(debt.get("id", "")).strip()
            row_index = int(debt.get("_row_index"))
            current_remaining = parse_sheet_number(debt.get("remaining_amount", 0))
            # Handle the missing or empty debt_id or current_remaining <= 0 case.
            if not debt_id or current_remaining <= 0:
                # Skip the rest of this loop iteration after handling this case.
                continue

            # Prepare offset amount for the next step.
            offset_amount = min(remaining_offset, current_remaining)
            # Prepare new remaining for the next step.
            new_remaining = current_remaining - offset_amount
            # Prepare is settled for the next step.
            is_settled = new_remaining <= 0

            # Run this statement as part of the current workflow.
            update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, new_remaining)
            update_cell(SHEET_DEBTS, row_index, DEBT_IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")
            # Handle the case where is_settled.
            if is_settled:
                # Run this statement as part of the current workflow.
                update_cell(SHEET_DEBTS, row_index, DEBT_SETTLED_AT_COL, today)

            # Open a multi-line structure for the values below.
            append_debt_mutation(
                # Prepare debt id for the next step.
                debt_id=debt_id,
                # Prepare amount for the next step.
                amount=offset_amount,
                # Prepare note for the next step.
                note=note,
                mutation_type="offset",
            # Close the structure that was opened above.
            )

            # Open a multi-line structure for the values below.
            allocations.append({
                "debt_id": debt_id,
                "amount": offset_amount,
                "description": debt.get("description", ""),
                "remaining_after": new_remaining,
                "type": target_debt_type,
            # Close the structure that was opened above.
            })
            # Update affected debt ids with the current value.
            affected_debt_ids.append(debt_id)
            # Run this statement as part of the current workflow.
            remaining_offset -= offset_amount

        created_debt_id = ""
        # Prepare created debt for the next step.
        created_debt = None
        # Handle the case where remaining_offset > 0.
        if remaining_offset > 0:
            # Open a multi-line structure for the values below.
            created = add_debt(
                # Include this value in the surrounding collection or call.
                resulting_debt_type,
                # Include this value in the surrounding collection or call.
                person_name,
                # Include this value in the surrounding collection or call.
                remaining_offset,
                description=f"Sisa kompensasi: {note}",
                cashflow_mode="debt_only",
                fronting_mode="offset_remainder",
            # Close the structure that was opened above.
            )
            if not created.get("success"):
                # Run this statement as part of the current workflow.
                rollback_current_sheets_transaction()
                # Return { to the caller.
                return {
                    "success": False,
                    "message": "Offset gagal disimpan penuh; perubahan sebelumnya sudah dibatalkan. Gagal membuat sisa debt: " + created.get("message", ""),
                    "allocations": allocations,
                    "affected_debt_ids": affected_debt_ids,
                # Close the structure that was opened above.
                }
            created_debt_id = created.get("debt_id") or ""
            # Prepare created debt for the next step.
            created_debt = created
            # Handle the case where created_debt_id.
            if created_debt_id:
                # Update affected debt ids with the current value.
                affected_debt_ids.append(created_debt_id)

        # Prepare active after for the next step.
        active_after = get_debt_by_person(person_name)
        total_payable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in active_after if d.get("type") == "payable")
        total_receivable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in active_after if d.get("type") == "receivable")

        # Return { to the caller.
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
        # Close the structure that was opened above.
        }

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "success": False,
            "message": str(e),
            "allocations": allocations,
            "affected_debt_ids": affected_debt_ids,
        # Close the structure that was opened above.
        }

# Define debt row sort key for settlement for callers in this flow.
def _debt_row_sort_key_for_settlement(debt: dict) -> tuple[int, str]:
    """Return stable settlement ordering by sheet row then debt ID."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        row_index = int((debt or {}).get("_row_index", 10**9) or 10**9)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Prepare row index for the next step.
        row_index = 10**9
    debt_id = str((debt or {}).get("id", "") or "")
    # Return (row_index, debt_id) to the caller.
    return (row_index, debt_id)


# Define reduce debt remaining for settlement for callers in this flow.
def _reduce_debt_remaining_for_settlement(debt: dict, amount: float, note: str, mutation_type: str) -> dict:
    """Reduce one debt row during settlement/netting.

    Args:
        debt: Debt record with `_row_index`, `id`, and remaining amount.
        amount: Requested reduction amount, capped at current remaining.
        note: Mutation note stored in `debt_payments`.
        mutation_type: Mutation type label, such as `netting`.

    Returns:
        Allocation result dict with amount, remaining_after, debt ID, and type.

    Side effects:
        Updates the debt row and appends a mutation row.
    """
    debt_id = str((debt or {}).get("id", "") or "").strip()
    row_index = int((debt or {}).get("_row_index") or 0)
    current_remaining = parse_sheet_number((debt or {}).get("remaining_amount", 0))
    # Prepare amount for the next step.
    amount = min(float(amount or 0), current_remaining)
    # Handle the missing or empty debt_id or not row_index or amount <= 0 case.
    if not debt_id or not row_index or amount <= 0:
        return {"success": False, "message": "Debt/amount tidak valid.", "debt_id": debt_id, "amount": 0.0}

    # Prepare new remaining for the next step.
    new_remaining = max(0.0, current_remaining - amount)
    # Prepare is settled for the next step.
    is_settled = new_remaining <= 0.0001
    today = datetime.now().strftime("%Y-%m-%d")

    # Run this statement as part of the current workflow.
    update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, 0 if is_settled else new_remaining)
    update_cell(SHEET_DEBTS, row_index, DEBT_IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")
    # Handle the case where is_settled.
    if is_settled:
        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, row_index, DEBT_SETTLED_AT_COL, today)

    # Open a multi-line structure for the values below.
    append_debt_mutation(
        # Prepare debt id for the next step.
        debt_id=debt_id,
        # Prepare amount for the next step.
        amount=amount,
        # Prepare note for the next step.
        note=note,
        # Prepare mutation type for the next step.
        mutation_type=mutation_type,
    # Close the structure that was opened above.
    )

    # Return { to the caller.
    return {
        "success": True,
        "debt_id": debt_id,
        "amount": amount,
        "description": (debt or {}).get("description", ""),
        "remaining_after": 0 if is_settled else new_remaining,
        "type": (debt or {}).get("type", ""),
    # Close the structure that was opened above.
    }


def settle_opposite_debts_by_person(person_name: str, amount: float | None = None, note: str = "Netting hutang-piutang") -> dict:
    """Net payable and receivable debts for one person without cashflow.

    Args:
        person_name: Counterparty name.
        amount: Optional maximum netting amount. When omitted, uses the maximum
            possible offset between both sides.
        note: Mutation note for payable and receivable reductions.

    Returns:
        Result dict with offset amount, allocations, affected IDs, and final
        payable/receivable/net remaining.

    Side effects:
        Reduces debts on both sides and appends netting mutations.
    """
    # Prepare person name for the next step.
    person_name = normalize_person_name(person_name)
    # Handle the missing or empty person_name case.
    if not person_name:
        return {"success": False, "message": "Nama orang kosong.", "offset_amount": 0.0, "allocations": []}

    # Open a multi-line structure for the values below.
    active_debts = [
        # Run this statement as part of the current workflow.
        d for d in get_debt_by_person(person_name)
        # Handle the missing or empty is_voided_debt(d) case.
        if not is_voided_debt(d)
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
        and str(d.get("type", "")).strip() in {"payable", "receivable"}
    # Close the structure that was opened above.
    ]

    payables = [d for d in active_debts if str(d.get("type", "")).strip() == "payable"]
    receivables = [d for d in active_debts if str(d.get("type", "")).strip() == "receivable"]
    total_payable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in payables)
    total_receivable = sum(parse_sheet_number(d.get("remaining_amount", 0)) for d in receivables)
    # Prepare max offset for the next step.
    max_offset = min(total_payable, total_receivable)

    # Handle the case where max_offset <= 0.
    if max_offset <= 0:
        # Return { to the caller.
        return {
            "success": True,
            "message": "Tidak ada hutang/piutang berlawanan yang perlu di-netting.",
            "offset_amount": 0.0,
            "allocations": [],
            "remaining_payable": total_payable,
            "remaining_receivable": total_receivable,
        # Close the structure that was opened above.
        }

    # Prepare offset amount for the next step.
    offset_amount = max_offset if amount is None else min(float(amount or 0), max_offset)
    # Handle the case where offset_amount <= 0.
    if offset_amount <= 0:
        return {"success": False, "message": "Nominal netting tidak valid.", "offset_amount": 0.0, "allocations": []}

    mutation_note = note or "Netting hutang-piutang"
    mutation_type = "netting"
    # Prepare payable allocations for the next step.
    payable_allocations = []
    # Prepare receivable allocations for the next step.
    receivable_allocations = []

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare remaining offset for the next step.
        remaining_offset = offset_amount
        # Process each debt in the current collection.
        for debt in sorted(payables, key=_debt_row_sort_key_for_settlement):
            # Handle the case where remaining_offset <= 0.
            if remaining_offset <= 0:
                # Leave the loop after the target condition has been reached.
                break
            pay_amount = min(remaining_offset, parse_sheet_number(debt.get("remaining_amount", 0)))
            # Prepare result for the next step.
            result = _reduce_debt_remaining_for_settlement(debt, pay_amount, mutation_note, mutation_type)
            if not result.get("success"):
                # Return result to the caller.
                return result
            # Update payable allocations with the current value.
            payable_allocations.append(result)
            # Run this statement as part of the current workflow.
            remaining_offset -= pay_amount

        # Prepare remaining offset for the next step.
        remaining_offset = offset_amount
        # Process each debt in the current collection.
        for debt in sorted(receivables, key=_debt_row_sort_key_for_settlement):
            # Handle the case where remaining_offset <= 0.
            if remaining_offset <= 0:
                # Leave the loop after the target condition has been reached.
                break
            pay_amount = min(remaining_offset, parse_sheet_number(debt.get("remaining_amount", 0)))
            # Prepare result for the next step.
            result = _reduce_debt_remaining_for_settlement(debt, pay_amount, mutation_note, mutation_type)
            if not result.get("success"):
                # Return result to the caller.
                return result
            # Update receivable allocations with the current value.
            receivable_allocations.append(result)
            # Run this statement as part of the current workflow.
            remaining_offset -= pay_amount

        # Prepare active after for the next step.
        active_after = get_debt_by_person(person_name)
        # Open a multi-line structure for the values below.
        remaining_payable = sum(
            parse_sheet_number(d.get("remaining_amount", 0))
            # Process each d in the current collection.
            for d in active_after
            if not is_voided_debt(d) and str(d.get("type", "")).strip() == "payable"
        # Close the structure that was opened above.
        )
        # Open a multi-line structure for the values below.
        remaining_receivable = sum(
            parse_sheet_number(d.get("remaining_amount", 0))
            # Process each d in the current collection.
            for d in active_after
            if not is_voided_debt(d) and str(d.get("type", "")).strip() == "receivable"
        # Close the structure that was opened above.
        )

        # Return { to the caller.
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
        # Close the structure that was opened above.
        }
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {"success": False, "message": str(e), "offset_amount": 0.0, "allocations": []}


# Define is voided debt for callers in this flow.
def is_voided_debt(record: dict) -> bool:
    """Check whether a condition is true for voided debt."""
    description = str(record.get("description", "") or "")
    return "[VOID" in description.upper()


# Define get debt person summary for callers in this flow.
def get_debt_person_summary() -> dict:
    """Summarize active debts by normalized person name.

    Returns:
        Dict with net payable groups, net receivable groups, balanced groups,
        and aggregate totals.
    """
    # Prepare source rows for the next step.
    source_rows = [d for d in get_debts_with_row_index(active_only=True) if not is_voided_debt(d)]

    # Run this statement as part of the current workflow.
    groups: dict[str, dict] = {}

    # Process each debt in the current collection.
    for debt in source_rows:
        # Handle the case where is_voided_debt(debt).
        if is_voided_debt(debt):
            # Skip the rest of this loop iteration after handling this case.
            continue

        person = normalize_debt_person_group_name(debt.get("person_name", ""))
        # Handle the missing or empty person case.
        if not person:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Open a multi-line structure for the values below.
        group = groups.setdefault(person, {
            "person_name": person,
            "payable_total": 0.0,
            "receivable_total": 0.0,
            "debt_count": 0,
            "details": [],
        # Close the structure that was opened above.
        })

        debt_type = str(debt.get("type", "")).strip()
        remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        # Handle the case where remaining <= 0.
        if remaining <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue

        if debt_type == "payable":
            group["payable_total"] += remaining
        elif debt_type == "receivable":
            group["receivable_total"] += remaining
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Skip the rest of this loop iteration after handling this case.
            continue

        group["debt_count"] += 1
        group["details"].append(debt)

    # Prepare payables for the next step.
    payables = []
    # Prepare receivables for the next step.
    receivables = []
    # Prepare balanced for the next step.
    balanced = []

    # Process each group in the current collection.
    for group in groups.values():
        net = group["receivable_total"] - group["payable_total"]
        group["net_amount"] = net
        group["raw_total"] = group["receivable_total"] + group["payable_total"]

        # Handle the case where net > 0.
        if net > 0:
            # Prepare item for the next step.
            item = dict(group)
            item["type"] = "receivable"
            item["remaining_amount"] = net
            # Update receivables with the current value.
            receivables.append(item)
        # Handle the alternate case where net < 0.
        elif net < 0:
            # Prepare item for the next step.
            item = dict(group)
            item["type"] = "payable"
            item["remaining_amount"] = abs(net)
            # Update payables with the current value.
            payables.append(item)
        elif group["debt_count"] > 0:
            # Prepare item for the next step.
            item = dict(group)
            item["type"] = "balanced"
            item["remaining_amount"] = 0.0
            # Update balanced with the current value.
            balanced.append(item)

    payables.sort(key=lambda x: x.get("person_name", ""))
    receivables.sort(key=lambda x: x.get("person_name", ""))
    balanced.sort(key=lambda x: x.get("person_name", ""))

    # Return { to the caller.
    return {
        "total_payable": sum(parse_sheet_number(x.get("remaining_amount", 0)) for x in payables),
        "total_receivable": sum(parse_sheet_number(x.get("remaining_amount", 0)) for x in receivables),
        "payables": payables,
        "receivables": receivables,
        "balanced": balanced,
    # Close the structure that was opened above.
    }


# Define get debt person detail for callers in this flow.
def get_debt_person_detail(person_name: str, include_settled: bool = True) -> dict:
    """Build detailed debt rows and totals for one person.

    Args:
        person_name: Counterparty name or compatible partial name.
        include_settled: Whether settled rows should be included in detail
            history.

    Returns:
        Detail dict with all matching rows, active rows, totals by side,
        progress metrics, and net remaining position.
    """
    # Prepare target for the next step.
    target = normalize_debt_person_group_name(person_name)
    # Prepare raw target for the next step.
    raw_target = normalize_person_name(person_name)
    # Prepare rows for the next step.
    rows = get_debts_with_row_index(active_only=not include_settled)
    # Prepare details for the next step.
    details = []

    # Process each debt in the current collection.
    for debt in rows:
        person_raw = normalize_person_name(debt.get("person_name", ""))
        # Prepare person key for the next step.
        person_key = normalize_debt_person_group_name(person_raw)
        # Handle the missing or empty person_key case.
        if not person_key:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Legacy compatibility note for older records or older in-memory state.
        if target != person_key and raw_target not in person_raw and person_raw not in raw_target:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the case where is_voided_debt(debt).
        if is_voided_debt(debt):
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Update details with the current value.
        details.append(debt)

    # Open a multi-line structure for the values below.
    active_details = [
        # Run this statement as part of the current workflow.
        d for d in details
        if not is_settled_value(d.get("is_settled", "FALSE"))
        and parse_sheet_number(d.get("remaining_amount", 0)) > 0
    # Close the structure that was opened above.
    ]

    # Define totals for for callers in this flow.
    def totals_for(rows_subset: list[dict], debt_type: str) -> dict:
        """Calculate original, remaining, paid, and paid percentage totals."""
        # Open a multi-line structure for the values below.
        original = sum(
            parse_sheet_number(d.get("original_amount", 0))
            # Process each d in the current collection.
            for d in rows_subset
            if str(d.get("type", "")).strip() == debt_type
        # Close the structure that was opened above.
        )
        # Open a multi-line structure for the values below.
        remaining = sum(
            parse_sheet_number(d.get("remaining_amount", 0))
            # Process each d in the current collection.
            for d in rows_subset
            if str(d.get("type", "")).strip() == debt_type
        # Close the structure that was opened above.
        )
        # Prepare paid for the next step.
        paid = max(0.0, original - remaining)
        # Prepare pct for the next step.
        pct = (paid / original * 100) if original > 0 else 0.0
        # Return { to the caller.
        return {
            "original": original,
            "remaining": remaining,
            "paid": paid,
            "paid_pct": pct,
        # Close the structure that was opened above.
        }

    payable_totals = totals_for(details, "payable")
    receivable_totals = totals_for(details, "receivable")
    active_payable = totals_for(active_details, "payable")
    active_receivable = totals_for(active_details, "receivable")

    net_remaining = active_receivable["remaining"] - active_payable["remaining"]

    # Define debt display sort key for callers in this flow.
    def debt_display_sort_key(d: dict) -> tuple[str, int]:
        """Sort debt details by created date and sheet row index."""
        created = str(d.get("created_at", "") or "").strip()
        # Legacy compatibility note for older records or older in-memory state.
        m = re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", created)
        # Handle the case where m.
        if m:
            created = m.group(0).replace("/", "-")
        row_index = int(d.get("_row_index", 0) or 0)
        # Return (created, row_index) to the caller.
        return (created, row_index)

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }


# Define get debt summary for callers in this flow.
def get_debt_summary() -> dict:
    """Read active debts and aggregate total payable/receivable amounts."""
    # Prepare all active for the next step.
    all_active = get_debts_with_row_index(active_only=True)

    payables = [r for r in all_active if r.get("type") == "payable"]
    receivables = [r for r in all_active if r.get("type") == "receivable"]

    total_payable = sum(parse_sheet_number(r.get("remaining_amount", 0)) for r in payables)
    total_receivable = sum(parse_sheet_number(r.get("remaining_amount", 0)) for r in receivables)

    # Return { to the caller.
    return {
        "total_payable": total_payable,
        "total_receivable": total_receivable,
        "payables": payables,
        "receivables": receivables,
    # Close the structure that was opened above.
    }




# Debt flow section

# Define summarize debt rows for settlement for callers in this flow.
def summarize_debt_rows_for_settlement(debts: list[dict]) -> dict:
    """Coordinate the summarize debt rows for settlement logic in the service layer.

    Args:
        debts: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Prepare selected for the next step.
    selected = []
    # Prepare total receivable for the next step.
    total_receivable = 0.0
    # Prepare total payable for the next step.
    total_payable = 0.0

    # Process each debt in the current collection.
    for debt in debts or []:
        # Handle the missing or empty debt or is_voided_debt(debt) case.
        if not debt or is_voided_debt(debt):
            # Skip the rest of this loop iteration after handling this case.
            continue
        remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        # Handle the case where remaining <= 0.
        if remaining <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        debt_type = str(debt.get("type", "") or "").strip().lower()
        if debt_type not in {"receivable", "payable"}:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Prepare item for the next step.
        item = dict(debt)
        item["remaining_amount"] = remaining
        # Update selected with the current value.
        selected.append(item)
        if debt_type == "receivable":
            # Run this statement as part of the current workflow.
            total_receivable += remaining
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Run this statement as part of the current workflow.
            total_payable += remaining

    # Prepare net amount for the next step.
    net_amount = total_receivable - total_payable
    # Handle the case where abs(net_amount) <= 0.0001.
    if abs(net_amount) <= 0.0001:
        net_type = "balanced"
    # Handle the alternate case where net_amount > 0.
    elif net_amount > 0:
        net_type = "receivable"
    # Handle the fallback path after earlier conditions are skipped.
    else:
        net_type = "payable"

    # Return { to the caller.
    return {
        "selected": selected,
        "count": len(selected),
        "total_receivable": total_receivable,
        "total_payable": total_payable,
        "net_amount": net_amount,
        "net_abs": abs(net_amount),
        "net_type": net_type,
    # Close the structure that was opened above.
    }


# Define settle selected debt ids for callers in this flow.
def settle_selected_debt_ids(
    # Include this value in the surrounding collection or call.
    person_name: str,
    # Include this value in the surrounding collection or call.
    debt_ids: list[str],
    note: str = "",
    # Include this value in the surrounding collection or call.
    overpayment_amount: float = 0.0,
    # Include this value in the surrounding collection or call.
    overpayment_policy: str | None = None,
    # Include this value in the surrounding collection or call.
    net_type: str | None = None,
# Close the structure that was opened above.
) -> dict:
    """Settle explicit debt rows after the bot preview is confirmed.

    Args:
        person_name: Counterparty name that must own every selected debt.
        debt_ids: Debt IDs selected from `/hutang Nama` detail or all-person
            settlement.
        note: Mutation note stored in `debt_payments`.
        overpayment_amount: Optional amount above the selected net debt.
        overpayment_policy: Optional policy for overpayment, such as
            `opposite_debt`.
        net_type: Selected net direction, either `receivable`, `payable`, or
            `balanced`.

    Returns:
        Result dict containing settled allocation rows, affected debt IDs,
        remaining payable/receivable totals, and overpayment metadata.

    Side effects:
        Sets selected debt rows to remaining `0`, appends debt mutation rows,
        and may create an opposite debt for overpayment.

    Flow constraints:
        This writer must only be called after a final preview confirmation.
    """
    # Prepare person for the next step.
    person = normalize_person_name(person_name)
    clean_ids = [str(x or "").strip() for x in (debt_ids or []) if str(x or "").strip()]
    # Handle the missing or empty person case.
    if not person:
        return {"success": False, "message": "Nama orang kosong.", "settled": []}
    # Handle the missing or empty clean_ids case.
    if not clean_ids:
        return {"success": False, "message": "Tidak ada debt terpilih.", "settled": []}

    # Prepare rows for the next step.
    rows = []
    # Prepare seen for the next step.
    seen = set()
    # Process each debt_id in the current collection.
    for debt_id in clean_ids:
        # Handle the case where debt_id in seen.
        if debt_id in seen:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Update seen with the current value.
        seen.add(debt_id)
        # Run this statement as part of the current workflow.
        row_index, debt = get_debt_row_by_id(debt_id)
        # Handle the missing or empty row_index or not debt case.
        if not row_index or not debt:
            return {"success": False, "message": f"Debt {debt_id} tidak ditemukan.", "settled": rows}
        current_person = normalize_person_name(debt.get("person_name", ""))
        # Handle the case where current_person != person.
        if current_person != person:
            # Return { to the caller.
            return {
                "success": False,
                "message": f"Debt {debt_id} bukan milik {person}.",
                "settled": rows,
            # Close the structure that was opened above.
            }
        # Handle the case where is_voided_debt(debt).
        if is_voided_debt(debt):
            return {"success": False, "message": f"Debt {debt_id} sudah void.", "settled": rows}
        remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        # Handle the case where remaining <= 0.
        if remaining <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        rows.append({"row_index": row_index, "debt": debt, "remaining": remaining})

    # Handle the missing or empty rows case.
    if not rows:
        return {"success": False, "message": "Semua debt terpilih sudah lunas/tidak aktif.", "settled": []}

    # Prepare settled items for the next step.
    settled_items = []
    mutation_note = note or f"Settlement debt terpilih {person}"
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Process each item in the current collection.
        for item in rows:
            row_index = int(item["row_index"])
            debt = item["debt"]
            remaining = float(item["remaining"] or 0)
            debt_id = str(debt.get("id", "") or "").strip()
            _set_debt_remaining(row_index, 0, parse_sheet_number(debt.get("original_amount", 0)))
            append_debt_mutation(debt_id, remaining, mutation_note, mutation_type="selected_settle")
            # Open a multi-line structure for the values below.
            settled_items.append({
                "debt_id": debt_id,
                "amount": remaining,
                "type": str(debt.get("type", "") or "").strip(),
                "description": debt.get("description", ""),
            # Close the structure that was opened above.
            })
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {"success": False, "message": str(e), "settled": settled_items}

    # Prepare overpayment amount for the next step.
    overpayment_amount = max(0.0, float(overpayment_amount or 0))
    overpayment_policy = str(overpayment_policy or "").strip().lower()
    # Prepare overpayment created for the next step.
    overpayment_created = None
    if overpayment_amount > 0 and overpayment_policy in {"opposite_debt", "debt", "hutang"}:
        # Debt flow section
        # Debt flow section
        # Debt flow section
        opposite_type = "payable" if str(net_type or "").strip() == "receivable" else "receivable"
        # Open a multi-line structure for the values below.
        created = add_debt(
            # Include this value in the surrounding collection or call.
            opposite_type,
            # Include this value in the surrounding collection or call.
            person,
            # Include this value in the surrounding collection or call.
            overpayment_amount,
            description=f"Kelebihan bayar settlement debt terpilih: {mutation_note}",
            cashflow_mode="debt_only",
            fronting_mode="overpayment_from_selected_settle",
        # Close the structure that was opened above.
        )
        if not created.get("success"):
            # Return { to the caller.
            return {
                "success": False,
                "message": "Debt terpilih sudah disettle, tapi gagal mencatat overpaid: " + created.get("message", ""),
                "settled": settled_items,
                "overpayment": overpayment_amount,
            # Close the structure that was opened above.
            }
        # Prepare overpayment created for the next step.
        overpayment_created = created

    # Prepare active after for the next step.
    active_after = get_debt_by_person(person)
    # Open a multi-line structure for the values below.
    total_payable = sum(
        parse_sheet_number(d.get("remaining_amount", 0))
        # Process each d in the current collection.
        for d in active_after
        if str(d.get("type", "") or "").strip() == "payable" and not is_voided_debt(d)
    # Close the structure that was opened above.
    )
    # Open a multi-line structure for the values below.
    total_receivable = sum(
        parse_sheet_number(d.get("remaining_amount", 0))
        # Process each d in the current collection.
        for d in active_after
        if str(d.get("type", "") or "").strip() == "receivable" and not is_voided_debt(d)
    # Close the structure that was opened above.
    )

    affected_ids = [x["debt_id"] for x in settled_items if x.get("debt_id")]
    if overpayment_created and overpayment_created.get("debt_id"):
        affected_ids.append(overpayment_created["debt_id"])

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }

# Debt flow section

# Define parse debt allocation note for callers in this flow.
def parse_debt_allocation_note(note: str) -> list[dict]:
    """Parse reversible debt allocation metadata from a transaction note.

    Args:
        note: Transaction `catatan` text containing
            `debt_allocations=debt_id:amount;...`.

    Returns:
        List of allocation dicts with `debt_id` and numeric `amount`.
        Invalid or missing allocation metadata returns an empty list.
    """
    raw = str(note or "")
    m = re.search(r"debt_allocations=([^|]+)", raw)
    # Handle the missing or empty m case.
    if not m:
        # Return [] to the caller.
        return []
    # Prepare payload for the next step.
    payload = m.group(1).strip()
    # Prepare result for the next step.
    result = []
    for part in payload.split(";"):
        # Prepare part for the next step.
        part = part.strip()
        if not part or ":" not in part:
            # Skip the rest of this loop iteration after handling this case.
            continue
        debt_id, amount_raw = part.split(":", 1)
        # Prepare amount for the next step.
        amount = parse_sheet_number(amount_raw)
        # Handle the case where debt_id.strip() and amount > 0.
        if debt_id.strip() and amount > 0:
            result.append({"debt_id": debt_id.strip(), "amount": amount})
    # Return result to the caller.
    return result


# Define set debt remaining for callers in this flow.
def _set_debt_remaining(row_index: int, new_remaining: float, original_amount: float | None = None):
    """Coordinate the set debt remaining logic in the service layer.

    Args:
        row_index: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        new_remaining: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        original_amount: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Prepare original for the next step.
    original = float(original_amount or 0)
    # Prepare remaining for the next step.
    remaining = max(0.0, float(new_remaining or 0))
    # Prepare is settled for the next step.
    is_settled = remaining <= 0.0001
    # Run this statement as part of the current workflow.
    update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, 0 if is_settled else remaining)
    update_cell(SHEET_DEBTS, row_index, DEBT_IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")
    update_cell(SHEET_DEBTS, row_index, DEBT_SETTLED_AT_COL, datetime.now().strftime("%Y-%m-%d") if is_settled else "")


# Define reverse debt payment transaction for callers in this flow.
def reverse_debt_payment_transaction(txn: dict) -> dict:
    """Reverse debt mutations created by a debt payment transaction.

    Args:
        txn: Transaction record with payment category, amount, `hutang_id`, and
            allocation metadata in `catatan`.

    Returns:
        Result dict with reversed allocation items and status message.

    Side effects:
        Reopens affected debt rows by increasing remaining amounts and appends
        reverse mutation rows. It may also reverse overpayment debt metadata.

    Flow constraints:
        Used by delete/edit rollback paths after the user confirms the
        transaction change.
    """
    # Prepare txn for the next step.
    txn = txn or {}
    category = str(txn.get("category", "") or "").strip()
    if category not in {"Pembayaran Piutang", "Bayar Utang"}:
        return {"success": True, "message": "Bukan transaksi payment debt.", "reversed": []}

    amount_left = parse_sheet_number(txn.get("amount", 0))
    note_text = str(txn.get("catatan", "") or "")
    is_selected_settle = "selected_settle=1" in note_text
    is_net_settle = "net_settle=1" in note_text
    # Handle the case where amount_left <= 0 and not (is_selected_settle or is_net_settle).
    if amount_left <= 0 and not (is_selected_settle or is_net_settle):
        return {"success": False, "message": "Nominal transaksi payment tidak valid.", "reversed": []}

    # Prepare allocations for the next step.
    allocations = parse_debt_allocation_note(note_text)
    # Handle the missing or empty allocations case.
    if not allocations:
        debt_ids = [x.strip() for x in re.split(r"[,;\s]+", str(txn.get("hutang_id", "") or "")) if x.strip()]
        allocations = [{"debt_id": debt_id, "amount": None} for debt_id in debt_ids]

    # Handle the missing or empty allocations case.
    if not allocations:
        return {"success": False, "message": "Transaksi payment tidak punya hutang_id/allocation untuk dibalikkan.", "reversed": []}

    # Prepare reversed items for the next step.
    reversed_items = []
    # Prepare failed for the next step.
    failed = []
    today_note = f"Reverse payment karena transaksi {txn.get('id') or '-'} dihapus/diedit"

    # Debt flow section
    # Debt flow section
    # Debt flow section
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    if is_selected_settle or is_net_settle:
        amount_left = sum(parse_sheet_number(a.get("amount")) for a in allocations)

    # Process each alloc in the current collection.
    for alloc in allocations:
        debt_id = str(alloc.get("debt_id") or "").strip()
        # Handle the missing or empty debt_id or amount_left <= 0 case.
        if not debt_id or amount_left <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Run this statement as part of the current workflow.
        row_index, debt = get_debt_row_by_id(debt_id)
        # Handle the missing or empty row_index or not debt case.
        if not row_index or not debt:
            failed.append(f"{debt_id}: debt tidak ditemukan")
            # Skip the rest of this loop iteration after handling this case.
            continue
        original = parse_sheet_number(debt.get("original_amount", 0))
        current_remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        # Prepare room for the next step.
        room = max(0.0, original - current_remaining)
        # Handle the case where room <= 0.
        if room <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        alloc_amount = alloc.get("amount")
        # Handle the case where (is_selected_settle or is_net_settle) and alloc_amount is not....
        if (is_selected_settle or is_net_settle) and alloc_amount is not None:
            # Prepare reverse amount for the next step.
            reverse_amount = min(room, parse_sheet_number(alloc_amount))
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Prepare reverse amount for the next step.
            reverse_amount = min(amount_left, room, parse_sheet_number(alloc_amount) if alloc_amount is not None else amount_left)
        # Handle the case where reverse_amount <= 0.
        if reverse_amount <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Prepare new remaining for the next step.
        new_remaining = min(original, current_remaining + reverse_amount)
        # Run this statement as part of the current workflow.
        _set_debt_remaining(row_index, new_remaining, original)
        append_debt_mutation(debt_id, -reverse_amount, today_note, mutation_type="reverse_payment")
        reversed_items.append({"debt_id": debt_id, "amount": reverse_amount, "remaining_after": new_remaining})
        # Run this statement as part of the current workflow.
        amount_left -= reverse_amount

    # Debt flow section
    # ketika transaction settlement/payment di-delete.
    overpay_id_match = re.search(r"overpayment_debt_id=([^|;\s]+)", note_text)
    # Handle the case where overpay_id_match.
    if overpay_id_match:
        # Prepare overpay debt id for the next step.
        overpay_debt_id = overpay_id_match.group(1).strip()
        # Run this statement as part of the current workflow.
        row_index, debt = get_debt_row_by_id(overpay_debt_id)
        # Handle the case where row_index and debt.
        if row_index and debt:
            current_remaining = parse_sheet_number(debt.get("remaining_amount", 0))
            # Handle the case where current_remaining > 0.
            if current_remaining > 0:
                _set_debt_remaining(row_index, 0, parse_sheet_number(debt.get("original_amount", 0)))
                append_debt_mutation(overpay_debt_id, current_remaining, today_note, mutation_type="reverse_overpayment_debt")
                reversed_items.append({"debt_id": overpay_debt_id, "amount": current_remaining, "remaining_after": 0})

    # Handle the case where failed.
    if failed:
        return {"success": False, "message": "; ".join(failed), "reversed": reversed_items}

    # Return { to the caller.
    return {
        "success": True,
        "message": "ok",
        "reversed": reversed_items,
        "unreversed_amount": max(0.0, amount_left),
    # Close the structure that was opened above.
    }

# Debt flow section

# Prepare DEBT ID COL for the next step.
DEBT_ID_COL = 1
# Prepare DEBT TYPE COL for the next step.
DEBT_TYPE_COL = 2
# Prepare DEBT PERSON COL for the next step.
DEBT_PERSON_COL = 3
# Prepare DEBT ORIGINAL AMOUNT COL for the next step.
DEBT_ORIGINAL_AMOUNT_COL = 4
# Prepare DEBT REMAINING AMOUNT COL for the next step.
DEBT_REMAINING_AMOUNT_COL = 5
# Prepare DEBT DESCRIPTION COL for the next step.
DEBT_DESCRIPTION_COL = 6
# Prepare DEBT DUE DATE COL for the next step.
DEBT_DUE_DATE_COL = 7
# Prepare DEBT IS SETTLED COL for the next step.
DEBT_IS_SETTLED_COL = 8
# Prepare DEBT SETTLED AT COL for the next step.
DEBT_SETTLED_AT_COL = 10


# Define get debts with row index for callers in this flow.
def get_debts_with_row_index(active_only: bool = True) -> list[dict]:
    """Read debt rows and attach their one-based sheet row index.

    Args:
        active_only: When true, settled rows are excluded.

    Returns:
        Debt records with `_row_index` for later update/delete operations.
    """
    # Prepare records for the next step.
    records = get_all_records(SHEET_DEBTS)
    # Prepare result for the next step.
    result = []

    # Process each i, record in the current collection.
    for i, record in enumerate(records):
        # Prepare item for the next step.
        item = dict(record)
        item["_row_index"] = i + 2

        if active_only and is_settled_value(item.get("is_settled", "FALSE")):
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Update result with the current value.
        result.append(item)

    # Return result to the caller.
    return result


# Define get debt by id any status for callers in this flow.
def get_debt_by_id_any_status(debt_id: str) -> tuple[int | None, dict | None]:
    """Find a debt row by ID regardless of settled status.

    Args:
        debt_id: Full debt ID.

    Returns:
        Tuple of row index and debt record, or `(None, None)`.
    """
    target = str(debt_id or "").strip()
    # Handle the missing or empty target case.
    if not target:
        # Return None, None to the caller.
        return None, None

    # Process each item in the current collection.
    for item in get_debts_with_row_index(active_only=False):
        if str(item.get("id", "")).strip() == target:
            return int(item.get("_row_index")), item

    # Return None, None to the caller.
    return None, None


# Define build active debt display map for callers in this flow.
def build_active_debt_display_map() -> dict[str, dict]:
    """Build numbered references for active debt summary output.

    Returns:
        Mapping of display number to debt ID and sheet row index.
    """
    # Prepare summary for the next step.
    summary = get_debt_summary()
    # Prepare display map for the next step.
    display_map = {}
    # Prepare display no for the next step.
    display_no = 1

    for section in (summary.get("payables") or [], summary.get("receivables") or []):
        # Open a multi-line structure for the values below.
        display_map[str(display_no)] = {
            "debt_id": section.get("id"),
            "row_index": section.get("_row_index"),
        # Close the structure that was opened above.
        }
        # Run this statement as part of the current workflow.
        display_no += 1

    # Return display_map to the caller.
    return display_map


# Define resolve debt ref for callers in this flow.
def resolve_debt_ref(ref: str, last_debt_map: dict | None = None) -> tuple[int | None, dict | None, str | None]:
    """Resolve a user input or reference for debt ref."""
    clean = str(ref or "").strip()
    # Handle the missing or empty clean case.
    if not clean:
        return None, None, "Masukkan nomor debt atau debt ID."

    # Prepare last debt map for the next step.
    last_debt_map = last_debt_map or {}

    # Handle the case where clean in last_debt_map.
    if clean in last_debt_map:
        # Prepare mapped for the next step.
        mapped = last_debt_map[clean]
        # Handle the case where isinstance(mapped, dict).
        if isinstance(mapped, dict):
            debt_id = mapped.get("debt_id")
            # Handle the case where debt_id.
            if debt_id:
                # Run this statement as part of the current workflow.
                row, debt = get_debt_by_id_any_status(debt_id)
                return row, debt, None if debt else "Debt tidak ditemukan."
        # Handle the alternate case where mapped.
        elif mapped:
            # Run this statement as part of the current workflow.
            row, debt = get_debt_by_id_any_status(str(mapped))
            return row, debt, None if debt else "Debt tidak ditemukan."

    # Handle the case where clean.isdigit().
    if clean.isdigit():
        # Debt flow section
        # Debt flow section
        # Debt flow section
        # Debt flow section
        return None, None, "Nomor debt tidak valid. Jalankan /hutang Nama dulu, lalu pakai nomor rincian yang muncul."

    # Run this statement as part of the current workflow.
    row, debt = get_debt_by_id_any_status(clean)
    # Handle the missing or empty debt case.
    if not debt:
        return None, None, "Debt ID tidak ditemukan."

    # Return row, debt, None to the caller.
    return row, debt, None


# Define expected initial cashflow category for callers in this flow.
def expected_initial_cashflow_category(debt: dict) -> str:
    """Return the expected cashflow category for a debt's initial transaction."""
    debt_type = str(debt.get("type", "")).strip()
    if debt_type == "payable":
        return "Penerimaan Utang"
    if debt_type == "receivable":
        return "Piutang Diberikan"
    return ""


# Define find debt initial cashflow candidates for callers in this flow.
def find_debt_initial_cashflow_candidates(debt: dict) -> list[dict]:
    """Find a record for debt initial cashflow candidates."""
    # Import app.services.transaction_service so this module can use its helpers.
    from app.services.transaction_service import (
        # Include this value in the surrounding collection or call.
        get_transactions_with_row_index,
        # Include this value in the surrounding collection or call.
        is_debt_cashflow_transaction,
    # Close the structure that was opened above.
    )

    person = normalize_person_name(debt.get("person_name", ""))
    amount = parse_sheet_number(debt.get("original_amount", 0))
    # Prepare category for the next step.
    category = expected_initial_cashflow_category(debt)
    debt_id = str(debt.get("id", "")).strip()

    # Prepare candidates for the next step.
    candidates = []

    # Process each txn in the current collection.
    for txn in get_transactions_with_row_index():
        # Handle the missing or empty is_debt_cashflow_transaction(txn) case.
        if not is_debt_cashflow_transaction(txn):
            # Skip the rest of this loop iteration after handling this case.
            continue

        txn_category = str(txn.get("category", "")).strip()
        txn_subject = normalize_person_name(txn.get("subject", ""))
        txn_amount = parse_sheet_number(txn.get("amount", 0))
        txn_notes = str(txn.get("catatan", "") or "")
        txn_raw = str(txn.get("raw_input", "") or "")

        # Debt flow section
        if debt_id and (debt_id in txn_notes or debt_id in txn_raw):
            # Update candidates with the current value.
            candidates.append(txn)
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Handle the case where txn_category != category.
        if txn_category != category:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Handle the case where txn_subject != person.
        if txn_subject != person:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Handle the case where abs(txn_amount - amount) > 0.0001.
        if abs(txn_amount - amount) > 0.0001:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Update candidates with the current value.
        candidates.append(txn)

    # Return candidates to the caller.
    return candidates


# Define is debt without initial cashflow for callers in this flow.
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
        # Return True to the caller.
        return True

    if cashflow_mode == "debt_only":
        # Return True to the caller.
        return True

    # Parser metadata is more reliable than description text for new rows.
    debt_only_fronting_modes = {
        "catat_utang",
        "ditalangin",
        "sudah_berlalu",
        "overpayment_from_payment",
        "overpayment_from_selected_settle",
    # Close the structure that was opened above.
    }
    # Handle the case where fronting_mode in debt_only_fronting_modes.
    if fronting_mode in debt_only_fronting_modes:
        # Return True to the caller.
        return True

    # Open a multi-line structure for the values below.
    debt_only_markers = [
        "ditalangin",
        "tanpa cashflow",
        "tanpa ubah saldo",
        "tanpa update saldo",
        "debt_only",
        "catat utang",
        "nitip",
    # Close the structure that was opened above.
    ]
    # Return any(marker in description for marker in debt_only_markers) to the caller.
    return any(marker in description for marker in debt_only_markers)




# Define build debts index for callers in this flow.
def build_debts_index(records: list[dict] | None = None, active_only: bool = False) -> dict:
    """Build lookup indexes for debt rows.

    Args:
        records: Optional debt records. When omitted, rows are read from Sheets.
        active_only: Whether to exclude settled rows when reading records.

    Returns:
        Dict containing flat `items`, `by_id`, and `by_source_txn` lookups.
    """
    # Handle the case where records is None.
    if records is None:
        # Prepare records for the next step.
        records = get_debts_with_row_index(active_only=active_only)

    # Prepare by id for the next step.
    by_id = {}
    # Prepare by source txn for the next step.
    by_source_txn = {}
    # Prepare items for the next step.
    items = []

    # Process each debt in the current collection.
    for debt in records or []:
        # Prepare item for the next step.
        item = dict(debt or {})
        if active_only and is_settled_value(item.get("is_settled", "FALSE")):
            # Skip the rest of this loop iteration after handling this case.
            continue

        debt_id = str(item.get("id", "") or "").strip()
        # Handle the missing or empty debt_id case.
        if not debt_id:
            # Skip the rest of this loop iteration after handling this case.
            continue

        # Update items with the current value.
        items.append(item)
        # Run this statement as part of the current workflow.
        by_id[debt_id] = item

        source_txn = str(item.get("source_transaction_id", "") or "").strip()
        # Handle the case where source_txn.
        if source_txn:
            # Run this statement as part of the current workflow.
            by_source_txn.setdefault(source_txn, []).append(item)

    return {"items": items, "by_id": by_id, "by_source_txn": by_source_txn}


# Define get debts by source transaction id for callers in this flow.
def get_debts_by_source_transaction_id(transaction_id: str, active_only: bool = True, debt_index: dict | None = None) -> list[dict]:
    """Read debts linked to one source transaction ID.

    Args:
        transaction_id: Source transaction ID.
        active_only: Whether settled rows are excluded when reading from Sheets.
        debt_index: Optional prebuilt index to avoid repeated sheet reads.

    Returns:
        Matching debt rows.
    """
    target = str(transaction_id or "").strip()
    # Handle the missing or empty target case.
    if not target:
        # Return [] to the caller.
        return []

    # Handle the case where debt_index is not None.
    if debt_index is not None:
        return list((debt_index.get("by_source_txn", {}) or {}).get(target, []) or [])

    # Prepare result for the next step.
    result = []
    # Process each debt in the current collection.
    for debt in get_debts_with_row_index(active_only=active_only):
        if str(debt.get("source_transaction_id", "")).strip() == target:
            # Update result with the current value.
            result.append(debt)
    # Return result to the caller.
    return result


# Define parse debt ids from transaction record for callers in this flow.
def parse_debt_ids_from_transaction_record(txn: dict) -> list[str]:
    """Parse debt IDs from a transaction record's `hutang_id` field."""
    raw = str((txn or {}).get("hutang_id", "") or "").strip()
    # Handle the missing or empty raw case.
    if not raw:
        # Return [] to the caller.
        return []
    parts = re.split(r"[,;|]", raw)
    # Prepare result for the next step.
    result = []
    # Prepare seen for the next step.
    seen = set()
    # Process each part in the current collection.
    for part in parts:
        clean = str(part or "").strip()
        # Handle the case where clean and clean not in seen.
        if clean and clean not in seen:
            # Update result with the current value.
            result.append(clean)
            # Update seen with the current value.
            seen.add(clean)
    # Return result to the caller.
    return result


# Define get debts linked to transaction record for callers in this flow.
def get_debts_linked_to_transaction_record(txn: dict, active_only: bool = False, debt_index: dict | None = None) -> list[dict]:
    """Resolve debts linked to a transaction by source ID and `hutang_id`.

    Args:
        txn: Transaction record.
        active_only: Whether settled debts should be excluded.
        debt_index: Optional prebuilt debt index.

    Returns:
        Unique linked debt records.
    """
    txn_id = str((txn or {}).get("id", "") or "").strip()
    # Handle the case where debt_index is None.
    if debt_index is None:
        # Prepare debt index for the next step.
        debt_index = build_debts_index(active_only=active_only)

    by_id = debt_index.get("by_id", {}) or {}
    by_source = debt_index.get("by_source_txn", {}) or {}
    # Prepare result for the next step.
    result = []
    # Prepare seen for the next step.
    seen = set()

    # Process each debt in the current collection.
    for debt in by_source.get(txn_id, []) or []:
        debt_id = str(debt.get("id", "") or "").strip()
        # Handle the case where debt_id and debt_id not in seen.
        if debt_id and debt_id not in seen:
            # Update result with the current value.
            result.append(debt)
            # Update seen with the current value.
            seen.add(debt_id)

    # Process each debt_id in the current collection.
    for debt_id in parse_debt_ids_from_transaction_record(txn):
        # Prepare debt for the next step.
        debt = by_id.get(debt_id)
        # Handle the missing or empty debt case.
        if not debt:
            # Skip the rest of this loop iteration after handling this case.
            continue
        if active_only and is_settled_value(debt.get("is_settled", "FALSE")):
            # Skip the rest of this loop iteration after handling this case.
            continue
        clean = str(debt.get("id", "") or "").strip()
        # Handle the case where clean and clean not in seen.
        if clean and clean not in seen:
            # Update result with the current value.
            result.append(dict(debt))
            # Update seen with the current value.
            seen.add(clean)

    # Return result to the caller.
    return result


# Define get debt paid amount from state for callers in this flow.
def get_debt_paid_amount_from_state(debt: dict) -> float:
    """Calculate paid amount from original and remaining debt state."""
    original = parse_sheet_number((debt or {}).get("original_amount", 0))
    remaining = parse_sheet_number((debt or {}).get("remaining_amount", 0))
    # Return max(0.0, original - remaining) to the caller.
    return max(0.0, original - remaining)


# Define find overpaid adjustment for debt for callers in this flow.
def find_overpaid_adjustment_for_debt(debt_id: str, debt_index: dict | None = None) -> tuple[int | None, dict | None]:
    """Find a record for overpaid adjustment for debt."""
    marker = f"overpaid:{str(debt_id or '').strip()}"
    if marker == "overpaid:":
        # Return None, None to the caller.
        return None, None

    # Handle the case where debt_index is not None.
    if debt_index is not None:
        matches = (debt_index.get("by_source_txn", {}) or {}).get(marker, []) or []
        # Handle the case where matches.
        if matches:
            # Prepare debt for the next step.
            debt = matches[0]
            return int(debt.get("_row_index") or 0), debt
        # Return None, None to the caller.
        return None, None

    # Process each debt in the current collection.
    for debt in get_debts_with_row_index(active_only=False):
        if str(debt.get("source_transaction_id", "") or "").strip() == marker:
            return int(debt.get("_row_index") or 0), debt

    # Return None, None to the caller.
    return None, None


# Define upsert overpaid adjustment for callers in this flow.
def upsert_overpaid_adjustment(original_debt: dict, overpaid_amount: float, debt_index: dict | None = None) -> dict:
    """Create or update the opposite-side debt for an overpaid source debt.

    Args:
        original_debt: Source debt row that was overpaid.
        overpaid_amount: Amount that should remain as opposite-side debt.
        debt_index: Optional prebuilt debt index.

    Returns:
        Result dict describing created/updated/no-op adjustment.

    Side effects:
        Updates an existing adjustment debt or creates a new debt-only row.
    """
    # Prepare original debt for the next step.
    original_debt = original_debt or {}
    debt_id = str(original_debt.get("id", "") or "").strip()
    # Handle the missing or empty debt_id case.
    if not debt_id:
        return {"success": False, "message": "Debt sumber kosong.", "overpaid_amount": 0.0}

    # Prepare overpaid amount for the next step.
    overpaid_amount = max(0.0, float(overpaid_amount or 0))
    person = normalize_person_name(original_debt.get("person_name", ""))
    old_type = str(original_debt.get("type", "") or "").strip()
    if old_type not in {"payable", "receivable"} or not person:
        return {"success": False, "message": "Debt sumber tidak valid.", "overpaid_amount": overpaid_amount}

    adjustment_type = "payable" if old_type == "receivable" else "receivable"
    source_marker = f"overpaid:{debt_id}"
    today = datetime.now().strftime("%Y-%m-%d")
    description = f"[OVERPAID_ADJUSTMENT] Kelebihan pembayaran dari {debt_id}"
    # Run this statement as part of the current workflow.
    row_index, existing = find_overpaid_adjustment_for_debt(debt_id, debt_index=debt_index)

    # Handle the case where existing and row_index.
    if existing and row_index:
        # Prepare paid on adjustment for the next step.
        paid_on_adjustment = get_debt_paid_amount_from_state(existing)
        # Prepare new remaining for the next step.
        new_remaining = max(0.0, overpaid_amount - paid_on_adjustment)
        # Prepare is settled for the next step.
        is_settled = new_remaining <= 0.0001
        old_original = parse_sheet_number(existing.get("original_amount", 0))

        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, row_index, DEBT_TYPE_COL, adjustment_type)
        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, row_index, DEBT_PERSON_COL, person)
        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, row_index, DEBT_ORIGINAL_AMOUNT_COL, overpaid_amount)
        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, 0 if is_settled else new_remaining)
        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, row_index, DEBT_DESCRIPTION_COL, description)
        update_cell(SHEET_DEBTS, row_index, DEBT_IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")
        update_cell(SHEET_DEBTS, row_index, DEBT_SETTLED_AT_COL, today if is_settled else "")
        # Open a multi-line structure for the values below.
        append_debt_mutation(
            existing.get("id"),
            # Include this value in the surrounding collection or call.
            overpaid_amount - old_original,
            f"Sync overpaid adjustment dari {debt_id}",
            mutation_type="sync_overpaid_adjustment",
        # Close the structure that was opened above.
        )
        # Return { to the caller.
        return {
            "success": True,
            "action": "updated" if overpaid_amount > 0 else "settled",
            "debt_id": existing.get("id"),
            "type": adjustment_type,
            "person_name": person,
            "overpaid_amount": overpaid_amount,
            "remaining_amount": 0 if is_settled else new_remaining,
        # Close the structure that was opened above.
        }

    # Handle the case where overpaid_amount <= 0.
    if overpaid_amount <= 0:
        return {"success": True, "action": "none", "overpaid_amount": 0.0}

    # Open a multi-line structure for the values below.
    created = add_debt(
        # Include this value in the surrounding collection or call.
        adjustment_type,
        # Include this value in the surrounding collection or call.
        person,
        # Include this value in the surrounding collection or call.
        overpaid_amount,
        # Prepare description for the next step.
        description=description,
        # Prepare source transaction id for the next step.
        source_transaction_id=source_marker,
        cashflow_mode="overpaid_adjustment",
    # Close the structure that was opened above.
    )
    created["overpaid_amount"] = overpaid_amount
    created["type"] = adjustment_type
    # Return created to the caller.
    return created


# Define sync debt charges from transaction edit for callers in this flow.
def sync_debt_charges_from_transaction_edit(old_txn: dict, new_txn: dict) -> dict:
    """Sync linked debt charge amounts after a source transaction edit.

    Args:
        old_txn: Transaction record before edit.
        new_txn: Transaction record after edit.

    Returns:
        Result dict with updated debts, overpaid adjustments, and ratio.

    Side effects:
        Updates linked debt original/remaining amounts and may upsert
        overpayment adjustment debts.
    """
    # Prepare old txn for the next step.
    old_txn = old_txn or {}
    # Prepare new txn for the next step.
    new_txn = new_txn or {}
    # Prepare debt index for the next step.
    debt_index = build_debts_index(active_only=False)
    # Open a multi-line structure for the values below.
    linked_debts = [
        # Run this statement as part of the current workflow.
        d for d in get_debts_linked_to_transaction_record(old_txn, active_only=False, debt_index=debt_index)
        # Handle the missing or empty is_voided_debt(d) case.
        if not is_voided_debt(d)
    # Close the structure that was opened above.
    ]

    # Handle the missing or empty linked_debts case.
    if not linked_debts:
        return {"success": True, "message": "Tidak ada debt charge terkait.", "updated": [], "overpaid": []}

    # Debt flow section
    # Debt flow section
    old_category = str(old_txn.get("category", "") or "").strip()
    new_category = str(new_txn.get("category", "") or "").strip()
    # Debt flow section
    # Debt flow section
    payment_categories = {"Pembayaran Piutang", "Bayar Utang"}
    # Handle the case where old_category in payment_categories or new_category in payment....
    if old_category in payment_categories or new_category in payment_categories:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Transaksi pembayaran hutang/piutang belum bisa di-sync dari edit umum. Pakai flow bayar_hutang/bayar_piutang.",
            "updated": [],
            "overpaid": [],
        # Close the structure that was opened above.
        }

    old_amount = parse_sheet_number(old_txn.get("amount", 0))
    new_amount = parse_sheet_number(new_txn.get("amount", 0))
    # Handle the case where old_amount <= 0 or new_amount <= 0.
    if old_amount <= 0 or new_amount <= 0:
        return {"success": False, "message": "Nominal transaksi lama/baru tidak valid.", "updated": [], "overpaid": []}

    # Prepare ratio for the next step.
    ratio = new_amount / old_amount
    today = datetime.now().strftime("%Y-%m-%d")
    # Prepare updated for the next step.
    updated = []
    # Prepare overpaid items for the next step.
    overpaid_items = []
    # Prepare failed for the next step.
    failed = []

    # Process each debt in the current collection.
    for debt in linked_debts:
        debt_id = str(debt.get("id", "") or "").strip()
        row_index = int(debt.get("_row_index") or 0)
        debt_type = str(debt.get("type", "") or "").strip()
        if not debt_id or not row_index or debt_type not in {"payable", "receivable"}:
            # Skip the rest of this loop iteration after handling this case.
            continue

        old_original = parse_sheet_number(debt.get("original_amount", 0))
        old_remaining = parse_sheet_number(debt.get("remaining_amount", 0))
        # Prepare paid amount for the next step.
        paid_amount = max(0.0, old_original - old_remaining)
        # Prepare new original for the next step.
        new_original = max(0.0, old_original * ratio)
        # Prepare new remaining for the next step.
        new_remaining = max(0.0, new_original - paid_amount)
        # Prepare overpaid amount for the next step.
        overpaid_amount = max(0.0, paid_amount - new_original)
        # Prepare is settled for the next step.
        is_settled = new_remaining <= 0.0001

        # Run this operation in a guarded block so failures can be handled.
        try:
            # Run this statement as part of the current workflow.
            update_cell(SHEET_DEBTS, row_index, DEBT_ORIGINAL_AMOUNT_COL, new_original)
            # Run this statement as part of the current workflow.
            update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, 0 if is_settled else new_remaining)
            update_cell(SHEET_DEBTS, row_index, DEBT_IS_SETTLED_COL, "TRUE" if is_settled else "FALSE")
            update_cell(SHEET_DEBTS, row_index, DEBT_SETTLED_AT_COL, today if is_settled else "")

            # Open a multi-line structure for the values below.
            append_debt_mutation(
                # Include this value in the surrounding collection or call.
                debt_id,
                # Include this value in the surrounding collection or call.
                new_original - old_original,
                # Open a multi-line structure for the values below.
                (
                    f"Sync charge dari edit transaksi {new_txn.get('id') or old_txn.get('id')}: "
                    f"{format_rupiah(old_original)} -> {format_rupiah(new_original)}; "
                    f"paid tetap {format_rupiah(paid_amount)}"
                # Close the structure that was opened above.
                ),
                mutation_type="sync_charge_from_transaction",
            # Close the structure that was opened above.
            )

            # Prepare adjustment for the next step.
            adjustment = upsert_overpaid_adjustment(debt, overpaid_amount, debt_index=debt_index)
            # Handle the case where overpaid_amount > 0.
            if overpaid_amount > 0:
                # Open a multi-line structure for the values below.
                overpaid_items.append({
                    "source_debt_id": debt_id,
                    "person_name": debt.get("person_name", ""),
                    "amount": overpaid_amount,
                    "adjustment": adjustment,
                # Close the structure that was opened above.
                })

            # Open a multi-line structure for the values below.
            updated.append({
                "debt_id": debt_id,
                "person_name": debt.get("person_name", ""),
                "type": debt_type,
                "old_original": old_original,
                "new_original": new_original,
                "paid_amount": paid_amount,
                "new_remaining": 0 if is_settled else new_remaining,
                "overpaid_amount": overpaid_amount,
            # Close the structure that was opened above.
            })
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            failed.append({"debt_id": debt_id, "message": str(e)})

    # Handle the case where failed.
    if failed:
        # Return { to the caller.
        return {
            "success": False,
            "message": "; ".join(f"{x.get('debt_id')}: {x.get('message')}" for x in failed),
            "updated": updated,
            "overpaid": overpaid_items,
            "failed": failed,
        # Close the structure that was opened above.
        }

    # Return { to the caller.
    return {
        "success": True,
        "message": "ok",
        "updated": updated,
        "overpaid": overpaid_items,
        "ratio": ratio,
    # Close the structure that was opened above.
    }


# Define void debts for transaction for callers in this flow.
def void_debts_for_transaction(transaction_id: str, debt_ids: list[str] | None = None) -> dict:
    """Void active debts linked to a source transaction.

    Args:
        transaction_id: Source transaction ID being deleted or corrected.
        debt_ids: Optional explicit debt IDs to include with source-linked rows.

    Returns:
        Result dict listing voided, skipped, and failed debt IDs.

    Side effects:
        Calls `void_linked_debt_only` for each target debt, which mutates debt
        rows and appends mutation records.
    """
    # Prepare targets for the next step.
    targets = []
    # Prepare seen for the next step.
    seen = set()

    # Process each debt_id in the current collection.
    for debt_id in debt_ids or []:
        clean = str(debt_id or "").strip()
        # Handle the case where clean and clean not in seen.
        if clean and clean not in seen:
            # Update targets with the current value.
            targets.append(clean)
            # Update seen with the current value.
            seen.add(clean)

    # Process each debt in the current collection.
    for debt in get_debts_by_source_transaction_id(transaction_id, active_only=True):
        clean = str(debt.get("id", "")).strip()
        # Handle the case where clean and clean not in seen.
        if clean and clean not in seen:
            # Update targets with the current value.
            targets.append(clean)
            # Update seen with the current value.
            seen.add(clean)

    # Prepare results for the next step.
    results = []
    # Process each debt_id in the current collection.
    for debt_id in targets:
        results.append(void_linked_debt_only(debt_id, reason=f"Transaksi sumber {transaction_id} dihapus"))

    failed = [r for r in results if not r.get("success")]
    # Return { to the caller.
    return {
        "success": not failed,
        "message": "ok" if not failed else "; ".join(r.get("message", "Gagal void debt") for r in failed),
        "voided_ids": [r.get("debt_id") for r in results if r.get("success") and not r.get("skipped")],
        "skipped_ids": [r.get("debt_id") for r in results if r.get("success") and r.get("skipped")],
        "failed": failed,
    # Close the structure that was opened above.
    }


def void_linked_debt_only(debt_id: str, reason: str = "Transaksi sumber dihapus") -> dict:
    """Void one unpaid debt that came from a source transaction.

    Args:
        debt_id: Full debt ID to void.
        reason: Human-readable reason appended to the debt description.

    Returns:
        Result dict with status, message, debt ID, and skipped flag.

    Side effects:
        Sets remaining amount to `0`, marks the debt settled, writes settled
        date/description, and appends a void mutation.

    Flow constraints:
        Blocks debts that already have payment/mutation progress to avoid
        silently corrupting debt history.
    """
    # Run this statement as part of the current workflow.
    row_index, debt = get_debt_by_id_any_status(debt_id)

    # Handle the missing or empty debt or not row_index case.
    if not debt or not row_index:
        return {"success": False, "message": f"Debt {debt_id} tidak ditemukan.", "debt_id": debt_id}

    if is_settled_value(debt.get("is_settled", "FALSE")):
        return {"success": True, "message": "Debt sudah settled.", "debt_id": debt_id, "skipped": True}

    original = parse_sheet_number(debt.get("original_amount", 0))
    remaining = parse_sheet_number(debt.get("remaining_amount", 0))
    # Handle the case where abs(original - remaining) > 0.0001.
    if abs(original - remaining) > 0.0001:
        # Return { to the caller.
        return {
            "success": False,
            "message": (
                f"Debt {debt_id} sudah punya pembayaran/mutasi. "
                "Delete transaksi sumber diblok agar debt tidak salah."
            # Close the structure that was opened above.
            ),
            "debt_id": debt_id,
        # Close the structure that was opened above.
        }

    today = datetime.now().strftime("%Y-%m-%d")
    old_description = str(debt.get("description", "") or "").strip()
    void_note = f"[VOID {today}] {reason}"
    new_description = f"{old_description} | {void_note}" if old_description else void_note

    # Run this statement as part of the current workflow.
    update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, 0)
    update_cell(SHEET_DEBTS, row_index, DEBT_IS_SETTLED_COL, "TRUE")
    # Run this statement as part of the current workflow.
    update_cell(SHEET_DEBTS, row_index, DEBT_SETTLED_AT_COL, today)
    # Run this statement as part of the current workflow.
    update_cell(SHEET_DEBTS, row_index, DEBT_DESCRIPTION_COL, new_description)

    # Open a multi-line structure for the values below.
    append_debt_mutation(
        debt_id=debt.get("id"),
        # Prepare amount for the next step.
        amount=remaining,
        # Prepare note for the next step.
        note=void_note,
        mutation_type="void_by_transaction_delete",
    # Close the structure that was opened above.
    )

    return {"success": True, "message": "ok", "debt_id": debt_id, "skipped": False}


# Define preview void debt for callers in this flow.
def preview_void_debt(debt_ref: str, last_debt_map: dict | None = None) -> dict:
    """Preview voiding one debt reference before mutating Sheets.

    Args:
        debt_ref: Debt ID, short reference, or latest `/hutang` detail number.
        last_debt_map: Optional number-to-debt mapping from the latest detail
            output.

    Returns:
        Preview dict containing the debt, linked cashflow transaction when
        found, reverse account deltas, and validation status.

    Flow constraints:
        This function is read-only and must run before any debt void write.
    """
    # Run this statement as part of the current workflow.
    row_index, debt, error = resolve_debt_ref(debt_ref, last_debt_map)

    # Handle the case where error.
    if error:
        # Return { to the caller.
        return {
            "success": False,
            "message": error,
            "debt": None,
            "debt_row_index": None,
            "cashflow_txn": None,
            "reverse_deltas": {},
        # Close the structure that was opened above.
        }

    # Handle the missing or empty debt case.
    if not debt:
        # Return { to the caller.
        return {
            "success": False,
            "message": "Debt tidak ditemukan.",
            "debt": None,
            "debt_row_index": None,
            "cashflow_txn": None,
            "reverse_deltas": {},
        # Close the structure that was opened above.
        }

    if is_settled_value(debt.get("is_settled", "FALSE")):
        # Return { to the caller.
        return {
            "success": False,
            "message": "Debt ini sudah settled/void.",
            "debt": debt,
            "debt_row_index": row_index,
            "cashflow_txn": None,
            "reverse_deltas": {},
        # Close the structure that was opened above.
        }

    original = parse_sheet_number(debt.get("original_amount", 0))
    remaining = parse_sheet_number(debt.get("remaining_amount", 0))

    # Handle the case where abs(original - remaining) > 0.0001.
    if abs(original - remaining) > 0.0001:
        # Return { to the caller.
        return {
            "success": False,
            "message": (
                "Debt ini sudah punya mutasi/pembayaran/netting. "
                "Untuk keamanan, /debt_void hanya bisa membatalkan debt yang belum pernah berubah."
            # Close the structure that was opened above.
            ),
            "debt": debt,
            "debt_row_index": row_index,
            "cashflow_txn": None,
            "reverse_deltas": {},
        # Close the structure that was opened above.
        }

    # Prepare candidates for the next step.
    candidates = find_debt_initial_cashflow_candidates(debt)

    # Handle the case where len(candidates) == 0.
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
            # Return { to the caller.
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
                # Close the structure that was opened above.
                ),
            # Close the structure that was opened above.
            }

        # Return { to the caller.
        return {
            "success": False,
            "message": (
                "Cashflow transaksi terkait debt tidak ditemukan. Untuk utang/payable biasa, "
                "bot perlu cashflow awal supaya saldo bisa direverse dengan aman. "
                "Cek manual di sheet transactions."
            # Close the structure that was opened above.
            ),
            "debt": debt,
            "debt_row_index": row_index,
            "cashflow_txn": None,
            "reverse_deltas": {},
        # Close the structure that was opened above.
        }

    # Handle the case where len(candidates) > 1.
    if len(candidates) > 1:
        # Return { to the caller.
        return {
            "success": False,
            "message": (
                "Ditemukan lebih dari 1 cashflow yang mirip dengan debt ini. "
                "Bot menolak void otomatis agar saldo tidak salah. Rapikan manual dulu."
            # Close the structure that was opened above.
            ),
            "debt": debt,
            "debt_row_index": row_index,
            "cashflow_txn": None,
            "candidate_txns": candidates,
            "reverse_deltas": {},
        # Close the structure that was opened above.
        }

    # Prepare cashflow txn for the next step.
    cashflow_txn = candidates[0]

    # Import app.services.transaction_service so this module can use its helpers.
    from app.services.transaction_service import calculate_reverse_deltas_for_delete
    # Prepare reverse deltas for the next step.
    reverse_deltas = calculate_reverse_deltas_for_delete([cashflow_txn])

    # Return { to the caller.
    return {
        "success": True,
        "message": "ok",
        "debt": debt,
        "debt_row_index": row_index,
        "cashflow_txn": cashflow_txn,
        "candidate_txns": candidates,
        "reverse_deltas": reverse_deltas,
    # Close the structure that was opened above.
    }



# Define resolve person debt targets for callers in this flow.
def resolve_person_debt_targets(person_name: str, detail_ref: str | None = None) -> dict:
    """Resolve a user input or reference for person debt targets."""
    # Prepare clean person for the next step.
    clean_person = normalize_person_name(person_name)
    clean_ref = str(detail_ref or "").strip()

    # Handle the missing or empty clean_person case.
    if not clean_person:
        return {"success": False, "message": "Nama orang tidak boleh kosong.", "person_name": clean_person, "targets": []}

    # Prepare detail for the next step.
    detail = get_debt_person_detail(clean_person, include_settled=True)
    active_details = detail.get("active_details") or []

    # Handle the missing or empty active_details case.
    if not active_details:
        # Return { to the caller.
        return {
            "success": False,
            "message": f"Tidak ada rincian debt aktif untuk {clean_person}.",
            "person_name": clean_person,
            "detail": detail,
            "targets": [],
        # Close the structure that was opened above.
        }

    # Handle the case where clean_ref.
    if clean_ref:
        # Handle the case where clean_ref.isdigit().
        if clean_ref.isdigit():
            # Prepare idx for the next step.
            idx = int(clean_ref)
            # Handle the case where idx < 1 or idx > len(active_details).
            if idx < 1 or idx > len(active_details):
                # Return { to the caller.
                return {
                    "success": False,
                    "message": f"Nomor rincian tidak valid untuk {clean_person}. Pilih 1 sampai {len(active_details)} dari output /hutang {clean_person}.",
                    "person_name": clean_person,
                    "detail": detail,
                    "targets": [],
                # Close the structure that was opened above.
                }
            # Return { to the caller.
            return {
                "success": True,
                "message": "ok",
                "person_name": clean_person,
                "detail": detail,
                "targets": [active_details[idx - 1]],
                "detail_ref": clean_ref,
                "scope": "person_detail",
            # Close the structure that was opened above.
            }

        # Legacy compatibility note for older records or older in-memory state.
        for debt in active_details:
            if str(debt.get("id", "")).strip() == clean_ref:
                # Return { to the caller.
                return {
                    "success": True,
                    "message": "ok",
                    "person_name": clean_person,
                    "detail": detail,
                    "targets": [debt],
                    "detail_ref": clean_ref,
                    "scope": "person_detail",
                # Close the structure that was opened above.
                }

        # Return { to the caller.
        return {
            "success": False,
            "message": f"Rincian {clean_ref} tidak ditemukan untuk {clean_person}.",
            "person_name": clean_person,
            "detail": detail,
            "targets": [],
        # Close the structure that was opened above.
        }

    # Return { to the caller.
    return {
        "success": True,
        "message": "ok",
        "person_name": clean_person,
        "detail": detail,
        "targets": active_details,
        "detail_ref": "",
        "scope": "person_all",
    # Close the structure that was opened above.
    }


# Define preview void debts by person for callers in this flow.
def preview_void_debts_by_person(person_name: str, detail_ref: str | None = None) -> dict:
    """Preview voiding all or selected active debts for one person.

    Args:
        person_name: Counterparty name.
        detail_ref: Optional detail number/range from `/hutang Nama`.

    Returns:
        Bulk preview dict with target debts, per-debt previews, reverse account
        deltas, linked cashflow transactions, and validation status.

    Flow constraints:
        This function only prepares confirmation data. It does not void debts or
        update account balances.
    """
    # Prepare resolved for the next step.
    resolved = resolve_person_debt_targets(person_name, detail_ref)
    if not resolved.get("success"):
        # Return { to the caller.
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
        # Close the structure that was opened above.
        }

    # Prepare previews for the next step.
    previews = []
    # Prepare failed for the next step.
    failed = []
    # Prepare total remaining for the next step.
    total_remaining = 0.0
    # Prepare total original for the next step.
    total_original = 0.0
    # Run this statement as part of the current workflow.
    reverse_deltas: dict[str, float] = {}
    # Prepare cashflow txns for the next step.
    cashflow_txns = []

    for debt in resolved.get("targets") or []:
        debt_id = str(debt.get("id", "")).strip()
        # Prepare item preview for the next step.
        item_preview = preview_void_debt(debt_id, {})
        # Update previews with the current value.
        previews.append(item_preview)

        if not item_preview.get("success"):
            # Update failed with the current value.
            failed.append(item_preview)
            # Skip the rest of this loop iteration after handling this case.
            continue

        preview_debt = item_preview.get("debt") or debt
        total_remaining += parse_sheet_number(preview_debt.get("remaining_amount", 0))
        total_original += parse_sheet_number(preview_debt.get("original_amount", 0))

        if item_preview.get("cashflow_txn"):
            cashflow_txns.append(item_preview.get("cashflow_txn"))

        for account, delta in (item_preview.get("reverse_deltas") or {}).items():
            # Run this statement as part of the current workflow.
            reverse_deltas[account] = reverse_deltas.get(account, 0.0) + float(delta or 0)

    # Handle the case where failed.
    if failed:
        # Prepare messages for the next step.
        messages = []
        # Process each failed_preview in the current collection.
        for failed_preview in failed[:5]:
            debt = failed_preview.get("debt") or {}
            desc = str(debt.get("description") or debt.get("id") or "-").strip()
            messages.append(f"- {desc}: {failed_preview.get('message')}")
        # Return { to the caller.
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
        # Close the structure that was opened above.
        }

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }


# Define void debt ids for callers in this flow.
def void_debt_ids(debt_ids: list[str]) -> dict:
    """Void multiple debt IDs after user confirmation.

    Args:
        debt_ids: Full debt IDs approved for voiding.

    Returns:
        Result dict with per-debt results, aggregate reverse deltas, balances,
        totals, and voided IDs.

    Side effects:
        Mutates each selected debt through `void_debt` and may apply related
        reverse account deltas depending on each debt preview.
    """
    # Prepare clean ids for the next step.
    clean_ids = []
    # Prepare seen for the next step.
    seen = set()
    # Process each debt_id in the current collection.
    for debt_id in debt_ids or []:
        clean = str(debt_id or "").strip()
        # Handle the case where clean and clean not in seen.
        if clean and clean not in seen:
            # Update clean ids with the current value.
            clean_ids.append(clean)
            # Update seen with the current value.
            seen.add(clean)

    # Handle the missing or empty clean_ids case.
    if not clean_ids:
        return {"success": False, "message": "Tidak ada debt_id yang akan divoid.", "results": []}

    # Prepare results for the next step.
    results = []
    # Process each debt_id in the current collection.
    for debt_id in clean_ids:
        # Update results with the current value.
        results.append(void_debt(debt_id, {}))

    failed = [r for r in results if not r.get("success")]
    success_results = [r for r in results if r.get("success")]

    # Run this statement as part of the current workflow.
    reverse_deltas: dict[str, float] = {}
    # Prepare new balances for the next step.
    new_balances = {}
    # Prepare total original for the next step.
    total_original = 0.0
    # Prepare total remaining for the next step.
    total_remaining = 0.0
    # Prepare debts for the next step.
    debts = []
    # Prepare cashflow txns for the next step.
    cashflow_txns = []

    # Process each result in the current collection.
    for result in success_results:
        debt = result.get("debt") or {}
        # Update debts with the current value.
        debts.append(debt)
        total_original += parse_sheet_number(debt.get("original_amount", 0))
        total_remaining += parse_sheet_number(debt.get("remaining_amount", 0))
        if result.get("cashflow_txn"):
            cashflow_txns.append(result.get("cashflow_txn"))
        for account, delta in (result.get("reverse_deltas") or {}).items():
            # Run this statement as part of the current workflow.
            reverse_deltas[account] = reverse_deltas.get(account, 0.0) + float(delta or 0)
        for account, balance in (result.get("new_balances") or {}).items():
            # Run this statement as part of the current workflow.
            new_balances[account] = balance

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }


# Define void debts by person for callers in this flow.
def void_debts_by_person(person_name: str, detail_ref: str | None = None) -> dict:
    """Void all or selected active debts for one person after preview approval.

    Args:
        person_name: Counterparty name.
        detail_ref: Optional detail number/range from `/hutang Nama`.

    Returns:
        Bulk void result enriched with person, scope, and selected detail ref.

    Side effects:
        Delegates to `void_debt_ids`, which mutates debt rows and related
        account/cashflow state.
    """
    # Prepare preview for the next step.
    preview = preview_void_debts_by_person(person_name, detail_ref)
    if not preview.get("success"):
        # Return preview to the caller.
        return preview

    result = void_debt_ids(preview.get("target_debt_ids") or [])
    # Open a multi-line structure for the values below.
    result.update({
        "person_name": preview.get("person_name"),
        "scope": preview.get("scope"),
        "detail_ref": preview.get("detail_ref"),
        "bulk": True,
    # Close the structure that was opened above.
    })
    # Return result to the caller.
    return result

# Define update debt for callers in this flow.
def update_debt(debt_ref: str, updates: dict, last_debt_map: dict | None = None) -> dict:
    """Apply the update debt operation in the service layer.

    Args:
        debt_ref: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        updates: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        last_debt_map: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Run this statement as part of the current workflow.
    row_index, debt, error = resolve_debt_ref(debt_ref, last_debt_map)

    # Handle the case where error.
    if error:
        return {"success": False, "message": error, "debt": debt}

    # Handle the missing or empty debt or not row_index case.
    if not debt or not row_index:
        return {"success": False, "message": "Debt tidak ditemukan.", "debt": debt}

    if is_settled_value(debt.get("is_settled", "FALSE")):
        return {"success": False, "message": "Debt ini sudah settled/void, jadi tidak bisa diedit.", "debt": debt}

    # Prepare cleaned for the next step.
    cleaned = {}
    # Process each key, value in the current collection.
    for key, value in (updates or {}).items():
        # Handle the case where value is None.
        if value is None:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Run this statement as part of the current workflow.
        cleaned[key] = value

    # Handle the missing or empty cleaned case.
    if not cleaned:
        return {"success": False, "message": "Tidak ada field yang diedit.", "debt": debt}

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare changed for the next step.
        changed = {}

        if "person_name" in cleaned:
            new_person = normalize_person_name(cleaned.get("person_name"))
            # Handle the missing or empty new_person case.
            if not new_person:
                return {"success": False, "message": "Nama orang tidak boleh kosong.", "debt": debt}
            # Run this statement as part of the current workflow.
            update_cell(SHEET_DEBTS, row_index, DEBT_PERSON_COL, new_person)
            changed["person_name"] = {"old": debt.get("person_name"), "new": new_person}

        if "type" in cleaned:
            new_type = str(cleaned.get("type") or "").strip().lower()
            if new_type not in {"payable", "receivable"}:
                return {"success": False, "message": "Tipe debt harus payable/receivable.", "debt": debt}
            # Run this statement as part of the current workflow.
            update_cell(SHEET_DEBTS, row_index, DEBT_TYPE_COL, new_type)
            changed["type"] = {"old": debt.get("type"), "new": new_type}

        if "amount" in cleaned:
            new_amount = float(cleaned.get("amount") or 0)
            # Handle the case where new_amount <= 0.
            if new_amount <= 0:
                return {"success": False, "message": "Nominal debt tidak valid.", "debt": debt}

            original = parse_sheet_number(debt.get("original_amount", 0))
            remaining = parse_sheet_number(debt.get("remaining_amount", 0))
            # Handle the case where abs(original - remaining) > 0.0001.
            if abs(original - remaining) > 0.0001:
                # Return { to the caller.
                return {
                    "success": False,
                    "message": (
                        "Debt ini sudah punya mutasi/pembayaran. Untuk keamanan, nominal tidak bisa diedit otomatis. "
                        "Void dulu atau rapikan manual di sheet."
                    # Close the structure that was opened above.
                    ),
                    "debt": debt,
                # Close the structure that was opened above.
                }

            # Run this statement as part of the current workflow.
            update_cell(SHEET_DEBTS, row_index, DEBT_ORIGINAL_AMOUNT_COL, new_amount)
            # Run this statement as part of the current workflow.
            update_cell(SHEET_DEBTS, row_index, DEBT_REMAINING_AMOUNT_COL, new_amount)
            changed["amount"] = {"old": remaining, "new": new_amount}

        if "description" in cleaned:
            new_description = str(cleaned.get("description") or "").strip()
            # Run this statement as part of the current workflow.
            update_cell(SHEET_DEBTS, row_index, DEBT_DESCRIPTION_COL, new_description)
            changed["description"] = {"old": debt.get("description"), "new": new_description}

        if "due_date" in cleaned:
            new_due_date = str(cleaned.get("due_date") or "").strip()
            # Run this statement as part of the current workflow.
            update_cell(SHEET_DEBTS, row_index, DEBT_DUE_DATE_COL, new_due_date)
            changed["due_date"] = {"old": debt.get("due_date"), "new": new_due_date}

        # Handle the case where changed.
        if changed:
            # Open a multi-line structure for the values below.
            append_debt_mutation(
                debt.get("id"),
                float(changed.get("amount", {}).get("new", 0) or 0),
                note=f"[edit] {changed}",
                mutation_type="edit",
            # Close the structure that was opened above.
            )

        _, updated_debt = get_debt_by_id_any_status(debt.get("id"))
        # Return { to the caller.
        return {
            "success": True,
            "message": "ok",
            "debt": updated_debt or debt,
            "old_debt": debt,
            "changed": changed,
        # Close the structure that was opened above.
        }
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {"success": False, "message": str(e), "debt": debt}


# Define void debt for callers in this flow.
def void_debt(debt_ref: str, last_debt_map: dict | None = None) -> dict:
    """Void one debt after preview approval.

    Args:
        debt_ref: Debt ID, short ref, or latest detail number.
        last_debt_map: Optional `/hutang` number mapping.

    Returns:
        Result dict with voided debt, linked cashflow reversal data, and new
        balances when applicable.

    Side effects:
        May reverse account balance deltas, mark the debt settled/voided, append
        a void mutation, and update linked state.
    """
    # Prepare preview for the next step.
    preview = preview_void_debt(debt_ref, last_debt_map)

    if not preview.get("success"):
        # Return preview to the caller.
        return preview

    debt = preview["debt"]
    debt_row_index = int(preview["debt_row_index"])
    cashflow_txn = preview["cashflow_txn"]
    reverse_deltas = preview.get("reverse_deltas", {})
    today = datetime.now().strftime("%Y-%m-%d")

    # Handle the case where cashflow_txn and reverse_deltas.
    if cashflow_txn and reverse_deltas:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Import app.services.transaction_service so this module can use its helpers.
            from app.services.transaction_service import apply_account_deltas
            # Prepare balance result for the next step.
            balance_result = apply_account_deltas(reverse_deltas)
            if balance_result.get("failed_accounts"):
                # Return { to the caller.
                return {
                    "success": False,
                    "message": "Rekening tidak ditemukan: " + ", ".join(balance_result["failed_accounts"]),
                    "debt": debt,
                    "cashflow_txn": cashflow_txn,
                    "reverse_deltas": reverse_deltas,
                    "new_balances": {},
                # Close the structure that was opened above.
                }
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            # Return { to the caller.
            return {
                "success": False,
                "message": f"Gagal reverse saldo rekening: {str(e)}",
                "debt": debt,
                "cashflow_txn": cashflow_txn,
                "reverse_deltas": reverse_deltas,
                "new_balances": {},
            # Close the structure that was opened above.
            }
    # Handle the fallback path after earlier conditions are skipped.
    else:
        balance_result = {"new_balances": {}}

    # Run this operation in a guarded block so failures can be handled.
    try:
        old_description = str(debt.get("description", "") or "").strip()
        void_note = f"[VOID {today}] Dibatalkan lewat /debt_void"
        new_description = f"{old_description} | {void_note}" if old_description else void_note

        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, debt_row_index, DEBT_REMAINING_AMOUNT_COL, 0)
        update_cell(SHEET_DEBTS, debt_row_index, DEBT_IS_SETTLED_COL, "TRUE")
        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, debt_row_index, DEBT_SETTLED_AT_COL, today)
        # Run this statement as part of the current workflow.
        update_cell(SHEET_DEBTS, debt_row_index, DEBT_DESCRIPTION_COL, new_description)

        # Open a multi-line structure for the values below.
        append_debt_mutation(
            debt_id=debt.get("id"),
            amount=parse_sheet_number(debt.get("original_amount", 0)),
            # Prepare note for the next step.
            note=void_note,
            mutation_type="void",
        # Close the structure that was opened above.
        )
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Run this statement as part of the current workflow.
        rollback_current_sheets_transaction()
        # Return { to the caller.
        return {
            "success": False,
            "message": (
                "Debt void gagal disimpan penuh. Perubahan sebelumnya sudah dibatalkan. "
                f"Error: {str(e)}"
            # Close the structure that was opened above.
            ),
            "debt": debt,
            "cashflow_txn": cashflow_txn,
            "reverse_deltas": reverse_deltas,
            "new_balances": balance_result.get("new_balances", {}),
        # Close the structure that was opened above.
        }

    # Handle the case where cashflow_txn.
    if cashflow_txn:
        # Run this operation in a guarded block so failures can be handled.
        try:
            txn_row = int(cashflow_txn.get("_row_index"))
            delete_rows("transactions", [txn_row])
        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            # Run this statement as part of the current workflow.
            rollback_current_sheets_transaction()
            # Return { to the caller.
            return {
                "success": False,
                "message": (
                    "Debt void gagal menghapus cashflow. Perubahan sebelumnya sudah dibatalkan. "
                    f"Error: {str(e)}"
                # Close the structure that was opened above.
                ),
                "debt": debt,
                "cashflow_txn": cashflow_txn,
                "reverse_deltas": reverse_deltas,
                "new_balances": balance_result.get("new_balances", {}),
            # Close the structure that was opened above.
            }

    # Return { to the caller.
    return {
        "success": True,
        "message": "ok",
        "debt": debt,
        "cashflow_txn": cashflow_txn,
        "reverse_deltas": reverse_deltas,
        "new_balances": balance_result.get("new_balances", {}),
    # Close the structure that was opened above.
    }
