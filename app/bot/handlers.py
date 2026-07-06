"""Handler facade that re-exports smaller handler modules for a stable import path."""


# Import app.bot.handler_parts.core so this module can use its helpers.
from app.bot.handler_parts.core import *
# Import app.bot.handler_parts.networth_assets so this module can use its helpers.
from app.bot.handler_parts.networth_assets import *
# Import app.bot.handler_parts.health_recurring_export so this module can use its helpers.
from app.bot.handler_parts.health_recurring_export import *
# Import app.bot.handler_parts.command_router so this module can use its helpers.
from app.bot.handler_parts.command_router import *
# Re-export category wizard handlers for application.py command registration.
from app.bot.handler_parts.category_flow import *
# Import app.bot.handler_parts.transaction_flow so this module can use its helpers.
from app.bot.handler_parts.transaction_flow import *
# Import app.bot.handler_parts.command_handlers so this module can use its helpers.
from app.bot.handler_parts.command_handlers import *
# Import app.bot.handler_parts.message_handlers so this module can use its helpers.
from app.bot.handler_parts.message_handlers import *
# Import app.bot.handler_parts.callback_handler so this module can use its helpers.
from app.bot.handler_parts.callback_handler import *

# Open a multi-line structure for the values below.
__all__ = [
    # Run this statement as part of the current workflow.
    name for name in globals()
    if name.endswith("_handler") or name in {
        "callback_handler",
        "scheduled_export_transactions",
        "error_handler",
    # Close the structure that was opened above.
    }
# Close the structure that was opened above.
]
