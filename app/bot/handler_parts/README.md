# app/bot/handler_parts

This folder splits Telegram handlers into smaller files.

The main reason is readability. A finance bot has many flows: commands, natural input, image input, preview, edit, debt, split bill, pending expense, recurring, assets, and callbacks. Keeping all of that in one file would be hard to maintain.

## Files

| File | Purpose |
|---|---|
| `core.py` | Basic handler utilities and safe replies |
| `common_imports.py` | Shared imports and formatting helpers |
| `command_handlers.py` | Explicit Telegram commands |
| `command_router.py` | Local command routing and typo handling |
| `message_handlers.py` | Natural text and image input |
| `transaction_flow.py` | Preview, edit, clarification, and confirmation helpers |
| `callback_handler.py` | Inline button decisions |
| `health_recurring_export.py` | Health, recurring, and export handlers |
| `networth_assets.py` | Asset and net worth handlers |

If the issue is about a Telegram button, start from `callback_handler.py`. If the issue is about natural input, start from `message_handlers.py` and `transaction_flow.py`.
