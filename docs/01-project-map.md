# 01. Project Map

This project is a Telegram-based personal finance assistant.

Main flow:

```text
Telegram user input
→ Telegram handler
→ parser / parse safety
→ preview and edit flow
→ service layer
→ Google Sheets
```

AI flow:

```text
User question or image
→ context builder / image parser
→ Gemini
→ response based on finance data
```

## Layer responsibilities

| Layer | Responsibility |
|---|---|
| `main.py` | Starts the runtime in polling or webhook mode. |
| `app/bot` | Receives Telegram commands, text, images, and callbacks. |
| `app/nlp` | Parses natural language input and decides whether the output is safe. |
| `app/services` | Runs finance business logic. |
| `app/sheets` | Reads and writes Google Sheets safely. |
| `app/scheduler` | Runs scheduled and recurring jobs. |
| `scripts` | Helps with setup, debugging, and regression testing. |

## Practical debugging mindset

When something breaks, locate the layer first.

- Wrong parsing result: check `app/nlp`.
- Wrong button flow: check `app/bot/handler_parts`.
- Wrong saved amount or balance: check `app/services`.
- Google Sheets error: check `app/sheets/client.py` and credentials.
