# Tests

The test suite protects parser behavior, Telegram flow contracts, finance
services, application boundaries, and documentation consistency.

## Test Layers

- `unit/`: focused parser, formatter, keyboard, state, and helper contracts.
- `service/`: finance-service behavior with in-memory worksheet substitutes.
- `integration/`: handler registration, callbacks, scheduler boundaries, and
  multi-input flows.
- `regression/`: JSONL cases for previously reported inputs and edge cases.
- `architecture/`: dependency direction and public boundary contracts.
- `fakes/`: minimal Telegram, Google Sheets, and optional-import test doubles.

`command_cases.json` contains fictional parser examples. Regression fixtures
live in `regression/fixtures/`; the shared loader compares only the expected
fields declared by each case.

## Run the Suite

```powershell
python -m pytest -q
```

Focused examples:

```powershell
python -m pytest -q tests/unit
python -m pytest -q tests/integration
python -m pytest -q -k split
```

Tests must not use production credentials or finance data. External boundaries
should be replaced with the local helpers in `tests/fakes/` or explicit mocks.
For the complete verification workflow, see [Testing](../docs/testing.md).
