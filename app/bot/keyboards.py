"""Telegram inline keyboard helpers for account choices, confirmations, and cancellations."""



# Import telegram so this module can use its helpers.
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Fallback only. Runtime rekening choices are read from sheet `accounts`.
ACCOUNTS = ["Cash", "BRI", "BSI", "BCA", "DANA", "GoPay", "Seabank"]

# Internal callback value for historical transactions that should not mutate saldo.
SKIP_ACCOUNT_CALLBACK_VALUE = "__skip_account__"
SKIP_ACCOUNT_NAME = "Sudah Berlalu"
SKIP_ACCOUNT_LABEL = "🕘 Sudah berlalu / jangan ubah saldo"


# Define get runtime account names for callers in this flow.
def _get_runtime_account_names() -> list[str]:
    """Read rekening names from sheet `accounts` with a small fallback."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Import app.services.resolver_service so this module can use its helpers.
        from app.services.resolver_service import get_account_names_from_sheet

        # Prepare names for the next step.
        names = get_account_names_from_sheet()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Prepare names for the next step.
        names = ACCOUNTS

    # Prepare clean names for the next step.
    clean_names = []
    # Process each name in the current collection.
    for name in names or []:
        clean = str(name or "").strip()
        # Handle the case where clean and clean not in clean_names.
        if clean and clean not in clean_names:
            # Update clean names with the current value.
            clean_names.append(clean)
    # Return clean_names or list(ACCOUNTS) to the caller.
    return clean_names or list(ACCOUNTS)


def account_keyboard(prefix: str = "acc", include_skip: bool = True) -> InlineKeyboardMarkup:
    """Build a dynamic rekening picker keyboard from sheet `accounts`.

    Args:
        prefix: Callback prefix used to route the selected account. Examples are
            `acc`, `mixed_acc`, and `debt_acc`.
        include_skip: Whether to include the historical transaction option.

    Returns:
        Inline keyboard containing account choices, optional historical skip,
        and a cancel button.
    """
    # Prepare account names for the next step.
    account_names = _get_runtime_account_names()
    # Open a multi-line structure for the values below.
    buttons = [
        InlineKeyboardButton(acc, callback_data=f"{prefix}:{acc}")
        # Process each acc in the current collection.
        for acc in account_names
    # Close the structure that was opened above.
    ]
    # Prepare keyboard for the next step.
    keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]

    if include_skip and prefix != "acc_to":
        # Open a multi-line structure for the values below.
        keyboard.append([
            # Open a multi-line structure for the values below.
            InlineKeyboardButton(
                # Include this value in the surrounding collection or call.
                SKIP_ACCOUNT_LABEL,
                callback_data=f"{prefix}:{SKIP_ACCOUNT_CALLBACK_VALUE}",
            # Close the structure that was opened above.
            )
        # Close the structure that was opened above.
        ])

    keyboard.append([InlineKeyboardButton("🚫 Batal", callback_data=f"cancel:{prefix}")])

    # Return InlineKeyboardMarkup(keyboard) to the caller.
    return InlineKeyboardMarkup(keyboard)


# Define confirm keyboard for callers in this flow.
def confirm_keyboard(txn_id: str) -> InlineKeyboardMarkup:
    """Build a simple save/cancel confirmation keyboard.

    Args:
        txn_id: Callback target used after `confirm:` or `cancel:`.

    Returns:
        Inline keyboard with Simpan and Batal buttons.
    """
    # Open a multi-line structure for the values below.
    keyboard = [
        # Open a multi-line structure for the values below.
        [
            InlineKeyboardButton("✅ Simpan", callback_data=f"confirm:{txn_id}"),
            InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{txn_id}"),
        # Close the structure that was opened above.
        ]
    # Close the structure that was opened above.
    ]
    # Return InlineKeyboardMarkup(keyboard) to the caller.
    return InlineKeyboardMarkup(keyboard)


# Define cancel keyboard for callers in this flow.
def cancel_keyboard() -> InlineKeyboardMarkup:
    """Build a one-button cancel keyboard.

    Returns:
        Inline keyboard that cancels the current pending session.
    """
    keyboard = [[InlineKeyboardButton("❌ Batal", callback_data="cancel")]]
    # Return InlineKeyboardMarkup(keyboard) to the caller.
    return InlineKeyboardMarkup(keyboard)

# Define receipt ownership keyboard for callers in this flow.
def receipt_ownership_keyboard() -> InlineKeyboardMarkup:
    """Build the first decision keyboard for receipt image parsing.

    Returns:
        Inline keyboard that lets the user choose whether all receipt items are
        personal expenses, only part of them, or the receipt flow should be
        cancelled.
    """
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ini transaksi saya semua", callback_data="receipt:all")],
        [InlineKeyboardButton("🧩 Saya hanya sebagian", callback_data="receipt:part")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:receipt")],
    # Close the structure that was opened above.
    ])
