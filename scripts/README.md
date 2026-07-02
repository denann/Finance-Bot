# scripts

This folder contains helper scripts for setup, debugging, and local testing.

These scripts are useful because they let users check the project before running the full Telegram bot.

## Files

| File | Purpose |
|---|---|
| `setup_check.py` | Lightweight setup validation for new users |
| `debug_check.py` | Deeper diagnostic check for developers |
| `ai_command_tester.py` | Local parser and command tester without Telegram runtime |

Use `setup_check.py` first when installing the project. Use `debug_check.py` when something works locally but fails during runtime.
