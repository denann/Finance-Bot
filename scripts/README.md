# scripts

This folder contains small operator and documentation helpers.

## Main scripts

- `check_docs.py`: offline command, environment, schema, link, and privacy drift checks.
- `view_logs.py`: filters structured logs, summarizes events, traces transaction IDs, and exports readable CSV.
- `ai_command_tester.py`: compatibility entry point for the canonical tester in `app/scripts/`.

Run `python scripts/check_docs.py` after documentation changes. Use
`python scripts/view_logs.py --help` for log filters and
`python scripts/ai_command_tester.py --help` for local parser-test options.

## Ownership Contract

Top-level scripts are operator/developer helpers. They must avoid production credentials by default and never become a second source for command, configuration, or schema facts.
