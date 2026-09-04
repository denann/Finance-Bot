# app

This folder contains the main application code for the Telegram-based personal finance bot.

The role of this folder is to connect user input, backend logic, Google Sheets, scheduling, and AI assistance into one working system.

## Main folders

- `application/`: typed use cases, request snapshots, bulk state, and governed external work.
- `api/`: optional FastAPI webhook endpoint.
- `bot/`: Telegram bot application, commands, messages, callbacks, and keyboards.
- `nlp/`: parser, normalizer, parse safety, and Gemini helpers.
- `scheduler/`: recurring jobs and automated tasks.
- `services/`: finance business logic.
- `sheets/`: Google Sheets access, schema setup, retry, and rollback helpers.

## Mental model

Telegram handlers should decide what the user wants. Services should decide what finance operation should happen. The Sheets layer should decide how data is read or written safely.

## Ownership Contract

`application/` coordinates typed use cases between Telegram and services. Shared runtime utilities such as configuration, clocks, formatting, observability, and operation boundaries stay at the package root. Dependencies flow from `bot/` and `api/` toward application/services, then through governed `sheets/` or NLP boundaries. Tests live under matching unit, service, and integration suites. Deployment files, generated manuals, and ad hoc finance rules do not belong in unrelated application modules.
