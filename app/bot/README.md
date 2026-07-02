# app/bot

This folder contains the Telegram bot interface layer.

It is responsible for receiving commands, natural text input, images, and inline button callbacks. It does not own the finance data itself. It calls the parser and service layer to process the actual logic.

## Main files

- `application.py`: builds the Telegram Application and registers handlers.
- `handlers.py`: re-exports handler modules for a stable import path.
- `keyboards.py`: contains reusable inline keyboard helpers.
- `handler_parts/`: contains split handler modules for commands, messages, callbacks, and transaction preview flows.
