# Testing

## Current Local Gates

Run these commands from the repository root:

```powershell
python -m pytest -q
python scripts/check_docs.py
python -m compileall -q app main.py tests scripts benchmarks
git diff --check
```

Install the application dependencies and pytest when the environment does not
already provide them:

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest
```

No Telegram token, service-account file, spreadsheet ID, or Gemini key is
required for the local suite. Tests must use fictional data and local fakes at
external boundaries.

## Coverage by Layer

| Layer | Current scope |
| :--- | :--- |
| Unit | Parsing, dates, formatting, keyboard consistency, flow state, charts, configuration, and documentation checks |
| Service | Transaction ordering, request-scoped snapshots, debt/net-worth behavior, and mutation outcomes |
| Integration | Public command and callback contracts, bulk clarification, scheduler I/O seams, and callback fallback containment |
| Regression | JSONL parser and flow cases, including split-bill and invalid-date inputs |
| Architecture | Dependency direction and application-layer isolation |
| Fakes | Telegram objects, in-memory worksheets, failure injection, and optional dependency stubs |

## Focused Commands

`tests/unit/test_preview_edit_details_and_legends.py` covers detailed batch
editing, category confirmation and stale callbacks, debt account visibility,
and legend delivery without altering preview IDs or callback data.

```powershell
python -m pytest -q tests/unit
python -m pytest -q tests/service
python -m pytest -q tests/integration
python -m pytest -q tests/regression
python -m pytest -q tests/architecture
python -m pytest -q -k split
```

## Regression Fixture Format

Regression cases live in `tests/regression/fixtures/expansion_cases.jsonl`.
Each line is one JSON object with a stable ID, fictional input, the target
layer, and partial expected output. The shared loader reports the case ID,
input, field, expected value, and actual value when a contract fails.

Add a case when a real bug can be reduced to deterministic local input. Keep
dynamic IDs, timestamps, secrets, and production data out of fixtures.

## Documentation Gate

`python scripts/check_docs.py` checks Markdown links and headings, documentation
index coverage, public command coverage, environment-variable parity, worksheet
schema coverage, and basic secret patterns. The checker reads local source and
does not initialize external services.

## Interpreting Results

A passing local suite proves the checked local contracts. It does not prove
Telegram delivery, Google Sheets permissions or latency, Gemini output quality,
hosting configuration, or scheduler behavior in production. Verify those areas
with an approved staging bot and spreadsheet; never use destructive staging
checks against production data.

Dated test counts in historical documents are snapshots, not permanent
requirements. Use the output from the current run when reporting verification.
