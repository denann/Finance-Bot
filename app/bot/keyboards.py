"""Telegram inline keyboard helpers for account choices, confirmations, and cancellations."""



# Import telegram so this module can use its helpers.
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Fallback only. Runtime rekening choices are read from sheet `accounts`.
ACCOUNTS = ["Cash", "BRI", "BSI", "BCA", "DANA", "GoPay", "Seabank"]

# Internal callback value for historical transactions that should not mutate saldo.
SKIP_ACCOUNT_CALLBACK_VALUE = "__skip_account__"
SKIP_ACCOUNT_NAME = "Sudah Berlalu"
SKIP_ACCOUNT_LABEL = "🕘 Sudah berlalu / jangan ubah saldo"


# Helper for get runtime account names.
def _get_runtime_account_names() -> list[str]:
    """Read rekening names from sheet `accounts` with a small fallback."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Import app.services.resolver_service so this module can use its helpers.
        from app.services.resolver_service import get_account_names_from_sheet

        names = get_account_names_from_sheet()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        names = ACCOUNTS

    # Normalize clean names before matching.
    clean_names = []
    # Iterate through each name.
    for name in names or []:
        clean = str(name or "").strip()
        # Handle clean and clean not in clean names.
        if clean and clean not in clean_names:
            # Append the current value to clean names.
            clean_names.append(clean)
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
    # Extract account names for validation.
    account_names = _get_runtime_account_names()
    buttons = [
        InlineKeyboardButton(acc, callback_data=f"{prefix}:{acc}")
        # Iterate through each acc.
        for acc in account_names
    ]
    # Build keyboard for the response flow.
    keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]

    if include_skip and prefix != "acc_to":
        keyboard.append([
            InlineKeyboardButton(
                SKIP_ACCOUNT_LABEL,
                callback_data=f"{prefix}:{SKIP_ACCOUNT_CALLBACK_VALUE}",
            )
        ])

    keyboard.append([InlineKeyboardButton("🚫 Batal", callback_data=f"cancel:{prefix}")])

    return InlineKeyboardMarkup(keyboard)


# Helper for confirm keyboard.
def confirm_keyboard(txn_id: str) -> InlineKeyboardMarkup:
    """Build a simple save/cancel confirmation keyboard.

    Args:
        txn_id: Callback target used after `confirm:` or `cancel:`.

    Returns:
        Inline keyboard with Simpan and Batal buttons.
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Simpan", callback_data=f"confirm:{txn_id}"),
            InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{txn_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# Helper for cancel keyboard.
def cancel_keyboard() -> InlineKeyboardMarkup:
    """Build a one-button cancel keyboard.

    Returns:
        Inline keyboard that cancels the current pending session.
    """
    keyboard = [[InlineKeyboardButton("❌ Batal", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)

# Helper for receipt ownership keyboard.
def receipt_ownership_keyboard() -> InlineKeyboardMarkup:
    """Build the first decision keyboard for receipt image parsing.

    Returns:
        Inline keyboard that lets the user choose whether all receipt items are
        personal expenses, only part of them, or the receipt flow should be
        cancelled.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ini transaksi saya semua", callback_data="receipt:all")],
        [InlineKeyboardButton("🧩 Saya hanya sebagian", callback_data="receipt:part")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:receipt")],
    ])
