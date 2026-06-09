from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Daftar rekening
ACCOUNTS = ["Cash", "BRI", "BSI", "DANA", "GoPay"]


def account_keyboard(prefix: str = "acc") -> InlineKeyboardMarkup:
    """
    Keyboard pilihan rekening.
    prefix dipakai untuk membedakan konteks:
      - "acc"      → pilih rekening untuk transaksi biasa
      - "acc_from" → pilih rekening asal untuk transfer
      - "acc_to"   → pilih rekening tujuan untuk transfer
    """
    buttons = [
        InlineKeyboardButton(acc, callback_data=f"{prefix}:{acc}")
        for acc in ACCOUNTS
    ]
    # Susun 3 kolom
    keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(keyboard)


def confirm_keyboard(txn_id: str) -> InlineKeyboardMarkup:
    """Keyboard konfirmasi setelah transaksi ditampilkan."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Simpan", callback_data=f"confirm:{txn_id}"),
            InlineKeyboardButton("❌ Batal", callback_data=f"cancel:{txn_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Keyboard batalkan saja."""
    keyboard = [[InlineKeyboardButton("❌ Batal", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)