from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Daftar rekening
ACCOUNTS = ["Cash", "BRI", "BSI", "DANA", "GoPay"]

# Opsi khusus untuk input historis/sudah berlalu.
# Dipakai ketika user ingin mencatat transaksi/debt tanpa mengubah saldo rekening saat ini.
SKIP_ACCOUNT_CALLBACK_VALUE = "__skip_account__"
SKIP_ACCOUNT_NAME = "Sudah Berlalu"
SKIP_ACCOUNT_LABEL = "🕘 Sudah berlalu / jangan ubah saldo"


def account_keyboard(prefix: str = "acc", include_skip: bool = True) -> InlineKeyboardMarkup:
    """
    Keyboard pilihan rekening.
    prefix dipakai untuk membedakan konteks:
      - "acc"      → pilih rekening untuk transaksi biasa
      - "acc_from" → pilih rekening asal untuk transfer
      - "acc_to"   → pilih rekening tujuan untuk transfer

    include_skip=True menambahkan opsi historis/sudah berlalu agar transaksi
    tetap tercatat, tetapi saldo rekening tidak berubah.
    """
    buttons = [
        InlineKeyboardButton(acc, callback_data=f"{prefix}:{acc}")
        for acc in ACCOUNTS
    ]
    # Susun 3 kolom
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