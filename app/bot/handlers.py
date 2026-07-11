"""Explicit compatibility facade for public Telegram handlers."""

from app.bot.handler_parts.callback_dispatcher import callback_handler
from app.bot.handler_parts.category_flow import (
    add_kategori_handler,
    edit_kategori_handler,
    kategori_handler,
)
from app.bot.handler_parts.command_handlers import (
    ask_handler,
    audit_handler,
    budget_handler,
    budget_history_handler,
    bulanan_handler,
    cancel_handler,
    cari_handler,
    coach_handler,
    debt_edit_handler,
    debt_settle_handler,
    debt_void_handler,
    examples_handler,
    grafik_handler,
    harian_handler,
    help_handler,
    hutang_handler,
    insight_handler,
    manual_handler,
    mingguan_handler,
    pending_add_handler,
    pending_cancel_handler,
    pending_handler,
    pending_paid_handler,
    privacy_handler,
    quickstart_handler,
    rekening_handler,
    ringkasan_hutang_handler,
    saldo_handler,
    set_budget_handler,
    set_saldo_handler,
    start_handler,
)
from app.bot.handler_parts.command_router import unknown_command_handler
from app.bot.handler_parts.core import error_handler
from app.bot.handler_parts.health_recurring_export import (
    export_handler,
    health_handler,
    recurring_add_handler,
    recurring_edit_handler,
    recurring_handler,
    recurring_off_handler,
    recurring_run_handler,
    scheduled_export_transactions,
)
from app.bot.handler_parts.message_handlers import (
    bulk_edit_txn_handler,
    debt_message_handler,
    delete_txn_handler,
    edit_txn_handler,
    image_handler,
    last_handler,
    message_handler,
    transaksi_handler,
)
from app.bot.handler_parts.networth_assets import (
    asset_add_handler,
    asset_off_handler,
    asset_update_handler,
    assets_handler,
    networth_handler,
    networth_history_handler,
    networth_snapshot_handler,
)


__all__ = [name for name in globals() if name.endswith("_handler")]
__all__.append("scheduled_export_transactions")
