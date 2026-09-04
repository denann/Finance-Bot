# app/bot/handler_parts

This folder splits the Telegram handler logic into smaller modules.

The bot has many flows: commands, natural transaction input, image parsing, debt, split bill, pending expense, edit preview, asset, and callback buttons. Keeping everything in one file would make the code hard to maintain.

## Main files

- `command_handlers.py`: explicit slash commands such as `/saldo`, `/quickstart`, `/set_saldo`, `/ask`, and `/audit`.
- `health_recurring_export.py`: health, recurring, and export command handlers.
- `message_handlers.py`: natural text routing, image routing, and follow-up text for partial receipt selection.
- `bulk_flow.py`: stable per-item clarification and final batch preview state.
- `category_flow.py`: category add/edit interaction steps and matching decisions.
- `callback_dispatcher.py`: callback-family ownership and fail-closed dispatch.
- `callback_handler.py`: inline button actions such as save, edit, cancel, account choice, receipt ownership choice, and split bill decisions.
- `transaction_flow.py`: preview, edit, mixed input, receipt batch conversion, debt preview, and save flow helpers.
- `transaction_browser.py`: paginated transaction lists, details, and contextual actions.
- `transaction_chart.py`: chart preparation and Telegram delivery helpers.
- `management_browser.py`: compact numbered browsers for debts, categories, pending expenses, recurring rules, and assets.
- `command_router.py`: typo suggestions and command routing helpers.
- `help_content.py`: canonical in-bot help topics and command examples.
- `networth_assets.py`: asset and net worth handlers.
- `state_utils.py`: bounded cleanup of temporary Telegram conversation state.
- `common_imports.py`: shared imports and compatibility helpers for split handler modules.
- `core.py`: authorization, safe replies, and base helper functions.

## Ownership Contract

Each callback family has one owner and bounded predicate. The dispatcher enters legacy handling only for the audited inventory; unknown data fails closed. Cross-domain business rules, raw Sheets access, and duplicate command registries do not belong here. Handler, callback, pending-action, and regression tests verify this folder.

`transaction_flow.py` owns the shared split-wizard keyboard. Direct split input,
ambiguous input, and multi-input clarification must reuse it instead of defining
different payer, allocation, or payment-status buttons.
