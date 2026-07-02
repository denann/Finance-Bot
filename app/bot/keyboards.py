"""Inline keyboard helpers for account selection, confirmation, edit, and cancel flows."""


from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Account list
ACCOUNTS = ["Cash", "BRI", "BSI", "DANA", "GoPay"]

# Implementation note for this project-specific finance flow.
# Account balance note: avoid partial balance updates when validation fails.
SKIP_ACCOUNT_CALLBACK_VALUE = "__skip_account__"
SKIP_ACCOUNT_NAME = "Sudah Berlalu"
SKIP_ACCOUNT_LABEL = "🕘 Sudah berlalu / jangan ubah saldo"


def account_keyboard(prefix: str = "acc", include_skip: bool = True) -> InlineKeyboardMarkup:
    """Helper for account keyboard in the Telegram bot flow."""
    buttons = [
        InlineKeyboardButton(acc, callback_data=f"{prefix}:{acc}")
        for acc in ACCOUNTS
    ]
    # Susun 3 column
    keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]

    if include_skip and prefix != "acc_to":
        keyboard.append([
            InlineKeyboardButton(
                SKIP_ACCOUNT_LABEL,
                callback_data=f"{prefix}:{SKIP_ACCOUNT_CALLBACK_VALUE}",
            )
        ])

    return InlineKeyboardMarkup(keyboard)


def confirm_keyboard(txn_id: str) -> InlineKeyboardMarkup:
    """Helper for confirm keyboard in the Telegram bot flow."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Simpan", callback_data=f"confirm:{txn_id}"),
            InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{txn_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Helper for cancel keyboard in the Telegram bot flow."""
    keyboard = [[InlineKeyboardButton("❌ Batal", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)