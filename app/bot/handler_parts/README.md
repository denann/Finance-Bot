# app/bot/handler_parts

This folder splits the Telegram handler logic into smaller modules.

The bot has many flows: commands, natural transaction input, image parsing, debt, split bill, pending expense, edit preview, asset, and callback buttons. Keeping everything in one file would make the code hard to maintain.

## Main files

- `command_handlers.py`: explicit slash commands such as `/saldo`, `/quickstart`, `/set_saldo`, `/ask`, and `/audit`.
- `message_handlers.py`: natural text and image routing.
- `callback_handler.py`: inline button actions such as save, edit, cancel, account choice, and split bill decisions.
- `transaction_flow.py`: preview, edit, mixed input, debt preview, and save flow helpers.
- `command_router.py`: typo suggestions and command routing helpers.
- `networth_assets.py`: asset and net worth handlers.
- `core.py`: authorization, safe replies, and base helper functions.
