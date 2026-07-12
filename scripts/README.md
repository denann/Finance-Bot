# scripts

This folder contains helper scripts for setup, debugging, and regression testing.

## Main scripts

- `setup_check.py`: beginner-friendly setup validation.
- `debug_check.py`: deeper developer diagnostic check.
- `ai_command_tester.py`: historical CLI wrapper for the canonical implementation in `app/scripts/ai_command_tester.py`.

Use these scripts before testing the bot manually in Telegram, especially when switching to a dummy Google Sheet.

## Ownership Contract

Top-level scripts are operator/developer entry points for setup, diagnostics, documentation checks, and manual generation. Application-aware tester logic remains in `app/scripts/`. Scripts must avoid production credentials by default and never become a second source for command, configuration, or schema facts.
