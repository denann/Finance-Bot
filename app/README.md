# app

This folder contains the main application code for the Telegram-based personal finance bot.

The role of this folder is to connect user input, backend logic, Google Sheets, scheduling, and AI assistance into one working system.

## Main folders

- `api/`: optional FastAPI webhook endpoint.
- `bot/`: Telegram bot application, commands, messages, callbacks, and keyboards.
- `nlp/`: parser, normalizer, parse safety, and Gemini helpers.
- `scheduler/`: recurring jobs and automated tasks.
- `services/`: finance business logic.
- `sheets/`: Google Sheets access, schema setup, retry, and rollback helpers.

## Mental model

Telegram handlers should decide what the user wants. Services should decide what finance operation should happen. The Sheets layer should decide how data is read or written safely.
