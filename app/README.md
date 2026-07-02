# app

This folder contains the main application code.

The purpose of this folder is to separate the bot into clear layers: Telegram interface, parser/NLP, business services, scheduler, Google Sheets access, and configuration. This structure makes the project easier to debug because each folder has a specific responsibility.

## Main parts

| Folder/File | Purpose |
|---|---|
| `api/` | Optional FastAPI webhook endpoint |
| `bot/` | Telegram bot handlers and UI flow |
| `nlp/` | Parser, normalizer, Gemini parser, and parse safety |
| `scheduler/` | Scheduled jobs such as recurring transactions |
| `services/` | Finance business logic |
| `sheets/` | Google Sheets access and schema validation |
| `config.py` | Environment-based configuration |

The main idea is simple: handlers receive user actions, services decide the finance logic, and the Sheets layer stores the data.
