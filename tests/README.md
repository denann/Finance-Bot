# tests

## Purpose and Layers

- `unit/`: isolated contracts and pure behavior.
- `service/`: finance service, Sheets fake, retry, idempotency, and reconciliation behavior.
- `integration/`: handler/runtime boundaries with fake adapters.
- `regression/`: fixture-driven protected behavior.
- `fakes/`: deterministic external adapters; no real services.

`tests/conftest.py` owns the default offline external-call guard. Tests must not use real Telegram, Google Sheets, Gemini, HTTP, or credentials. New behavior belongs in the narrowest layer that proves its contract; production data and live evaluation do not belong here.
