"""Handler facade that re-exports smaller handler modules for a stable import path."""


from app.bot.handler_parts.core import *
from app.bot.handler_parts.networth_assets import *
from app.bot.handler_parts.health_recurring_export import *
from app.bot.handler_parts.command_router import *
from app.bot.handler_parts.transaction_flow import *
from app.bot.handler_parts.command_handlers import *
from app.bot.handler_parts.message_handlers import *
from app.bot.handler_parts.callback_handler import *

__all__ = [
    name for name in globals()
    if name.endswith("_handler") or name in {
        "callback_handler",
        "scheduled_export_transactions",
        "error_handler",
    }
]
