"""Pure public command registry shared by runtime routing and offline tools."""

from __future__ import annotations


BASIC_COMMANDS = (
    ("start", "start_handler"), ("quickstart", "quickstart_handler"),
    ("cancel", "cancel_handler"), ("batal", "cancel_handler"),
    ("help", "help_handler"), ("manual", "manual_handler"),
    ("privacy", "privacy_handler"), ("examples", "examples_handler"),
    ("contoh", "examples_handler"), ("health", "health_handler"),
)

TRANSACTION_COMMANDS = (
    ("saldo", "saldo_handler"), ("set_saldo", "set_saldo_handler"),
    ("saldo_set", "set_saldo_handler"), ("set_balance", "set_saldo_handler"),
    ("rekening", "rekening_handler"), ("harian", "harian_handler"),
    ("mingguan", "mingguan_handler"), ("bulanan", "bulanan_handler"),
    ("grafik", "grafik_handler"), ("chart", "grafik_handler"),
    ("cari", "cari_handler"), ("last", "last_handler"),
    ("transaksi", "transaksi_handler"), ("delete_txn", "delete_txn_handler"),
    ("edit_txn", "edit_txn_handler"),
)

EXPORT_COMMANDS = (("download_data", "export_handler"), ("export", "export_handler"))
BUDGET_COMMANDS = (
    ("budget", "budget_handler"), ("set_budget", "set_budget_handler"),
    ("budget_history", "budget_history_handler"),
)
CATEGORY_COMMANDS = (
    ("kategori", "kategori_handler"), ("categories", "kategori_handler"),
    ("list_kategori", "kategori_handler"), ("add_kategori", "add_kategori_handler"),
    ("tambah_kategori", "add_kategori_handler"), ("add_category", "add_kategori_handler"),
    ("edit_kategori", "edit_kategori_handler"), ("ubah_kategori", "edit_kategori_handler"),
    ("edit_category", "edit_kategori_handler"),
)
PENDING_COMMANDS = (
    ("pending", "pending_handler"), ("pending_add", "pending_add_handler"),
    ("rencana", "pending_add_handler"), ("pending_paid", "pending_paid_handler"),
    ("pending_cancel", "pending_cancel_handler"),
)
DEBT_COMMANDS = (
    ("hutang", "hutang_handler"), ("ringkasan_hutang", "ringkasan_hutang_handler"),
    ("debt_void", "debt_void_handler"), ("debt_edit", "debt_edit_handler"),
    ("debt_settle", "debt_settle_handler"),
)
RECURRING_COMMANDS = (
    ("recurring", "recurring_handler"), ("recurring_add", "recurring_add_handler"),
    ("recurring_run", "recurring_run_handler"), ("recurring_edit", "recurring_edit_handler"),
    ("recurring_off", "recurring_off_handler"),
)
NET_WORTH_COMMANDS = (
    ("networth", "networth_handler"), ("assets", "assets_handler"),
    ("asset_add", "asset_add_handler"), ("asset_update", "asset_update_handler"),
    ("asset_off", "asset_off_handler"), ("networth_snapshot", "networth_snapshot_handler"),
    ("networth_history", "networth_history_handler"),
)
AI_COMMANDS = (
    ("insight", "insight_handler"), ("ask", "ask_handler"),
    ("audit", "audit_handler"), ("coach", "coach_handler"),
)

COMMAND_GROUPS = (
    BASIC_COMMANDS, TRANSACTION_COMMANDS, EXPORT_COMMANDS, BUDGET_COMMANDS,
    CATEGORY_COMMANDS, PENDING_COMMANDS, DEBT_COMMANDS, RECURRING_COMMANDS,
    NET_WORTH_COMMANDS, AI_COMMANDS,
)
PUBLIC_COMMANDS = tuple(name for group in COMMAND_GROUPS for name, _handler in group)

LIABILITY_UNAVAILABLE_COMMANDS = {
    "liabilities": "Liability tidak lagi menjadi fitur terpisah. Gunakan `/hutang` untuk melihat utang dan piutang.",
    "liability_add": "Liability tidak lagi menjadi fitur terpisah. Catat utang atau piutang melalui alur `/hutang`.",
    "liability_update": "Liability tidak lagi menjadi fitur terpisah. Kelola utang atau piutang melalui `/hutang`.",
    "liability_off": "Liability tidak lagi menjadi fitur terpisah. Kelola utang atau piutang melalui `/hutang`.",
}

