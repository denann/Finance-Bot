"""Telegram inline keyboard helpers for account choices, confirmations, and cancellations."""



from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Fallback only. Runtime rekening choices are read from sheet `accounts`.
ACCOUNTS = ["Cash", "BRI", "BSI", "BCA", "DANA", "GoPay", "Seabank"]

# Internal callback value for historical transactions that should not mutate saldo.
SKIP_ACCOUNT_CALLBACK_VALUE = "__skip_account__"
SKIP_ACCOUNT_NAME = "Sudah Berlalu"
SKIP_ACCOUNT_LABEL = "🕘 Sudah berlalu / jangan ubah saldo"


def _get_runtime_account_names() -> list[str]:
    """Read rekening names from sheet `accounts` with a small fallback."""
    try:
        from app.services.resolver_service import get_account_names_from_sheet

        names = get_account_names_from_sheet()
    except Exception:
        names = ACCOUNTS

    clean_names = []
    for name in names or []:
        clean = str(name or "").strip()
        if clean and clean not in clean_names:
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
    account_names = _get_runtime_account_names()
    buttons = [
        InlineKeyboardButton(acc, callback_data=f"{prefix}:{acc}")
        for acc in account_names
    ]
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


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Build a one-button cancel keyboard.

    Returns:
        Inline keyboard that cancels the current pending session.
    """
    keyboard = [[InlineKeyboardButton("❌ Batal", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)

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
