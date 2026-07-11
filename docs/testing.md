# Testing

## Scope and safety

The default suite is offline and deterministic. It protects Phase 0 data-integrity contracts and fixture-driven Phase 1A regressions without contacting Telegram, Google Sheets, Gemini, webhooks, or production schedulers.

An autouse pytest guard removes external credentials and blocks socket, HTTP, Telegram Bot API, and real gspread authorization calls. Tests may replace a boundary only with an explicit local fake.

| Test area | Coverage |
| :--- | :--- |
| Unit | Date states, parser baseline, immutable action lifecycle, typed results, bulk item state, formatting, evaluation metrics, report comparison, and gates |
| Service | Save outcomes, transaction/debt use cases, debt-backed net worth, rollback propagation, recurring exactly-once, and append reconciliation |
| Integration | Diagnostic route policy, public command/callback contracts, confirmation inventory, and bulk clarification translation |
| Architecture | Dependency direction, callback ownership, canonical utilities, and no-Telegram application boundaries |
| Regression | JSONL parser, routing, safety, preview, split-bill, multi-input, manual-edit, and scenario cases |
| Fakes | In-memory worksheet/failure plan, Telegram objects, frozen clock, and optional import stubs |
| Live evaluation | Explicit opt-in Gemini draft parsing with versioned reports; excluded from pytest |

The matrix coverage inventory is maintained in [`docs/testing/debug-matrix-coverage.md`](testing/debug-matrix-coverage.md).

### Regression expansion

The owner-provided expansion adds 49 deterministic cases in `tests/regression/fixtures/expansion_cases.jsonl`:

- 26 active cases that must pass normally.
- 23 known-gap cases that remain strict `xfail` until the implementation satisfies their recorded contracts.

Coverage includes historical Telegram inputs and high-risk nominal, transfer, date, debt, split-bill, multi-input, safety, and confirmation behavior. `test_expansion_fixture_has_unique_ids_and_no_legacy_input_duplicates` rejects duplicate IDs, duplicate expansion inputs, and exact input duplicates against the earlier regression corpus.

The historical integration snapshot is documented in [`docs/testing/regression-expansion-2026-07-11.md`](testing/regression-expansion-2026-07-11.md). Use current pytest collection output for repository-wide totals because later Phase 2 tests increase the count beyond that snapshot.

After Phase 2 integration and callback-fallback containment, the verified merged suite collects 276 tests: 253 pass and 23 remain strict expected failures. There are no failures, unexpected passes, or skipped tests.

## Install dependencies

Use a development environment. `requirements-dev.txt` includes runtime dependencies and pytest.

```powershell
python -m pip install -r requirements-dev.txt
```

No `.env`, Telegram token, service-account JSON, spreadsheet ID, or Gemini key is required for pytest.

## Run tests

Complete offline suite:

```powershell
python -m pytest -q tests
```

Focused suites:

```powershell
python -m pytest -q tests/unit
python -m pytest -q tests/service
python -m pytest -q tests/integration
python -m pytest -q tests/regression
python -m pytest -q tests/architecture
```

Filter by case ID, tag-like keyword, or flow name:

```powershell
python -m pytest -q -k split_bill
python -m pytest -q -k slash_command
python -m pytest -q -k confirmation_security
```

Compile and import smoke checks:

```powershell
python -m compileall -q app evals main.py tests
python -c "from tests.fakes.external_modules import install_external_stubs; install_external_stubs(); import app.nlp.regex_parser, app.nlp.parse_safety, app.bot.pending_actions, evals.metrics, evals.gates"
```

## Regression fixture format

One-shot JSONL cases live under `tests/regression/fixtures/`. A case has a stable ID, matrix source, fixed reference date when needed, tags, raw input, and partial expectations.

```json
{
  "id": "mx02_01_expense_coffee_cash",
  "source": {
    "document": "finance_bot_debug_input_matrix_v2.md",
    "section": "2. Single Transaction Ready to Save",
    "case": 1
  },
  "input": "beli kopi 20k dari Cash",
  "reference_date": "2026-07-10",
  "expected": {
    "route": "transaction",
    "flow": "PREVIEW_SAVE_EDIT_CANCEL",
    "parsed": {
      "type": "expense",
      "amount": 20000,
      "account": "Cash"
    }
  },
  "tags": ["expense", "parser", "critical"]
}
```

Add the case to the fixture matching the boundary being asserted. Do not include dynamic UUIDs, timestamps, preview message IDs, or unrelated metadata. The shared assertion helper compares only fields declared in `expected` and reports the case ID, input, step, field, expected value, actual value, route, and flow.

## Multi-step scenarios

Confirmation scenarios live in `scenario_cases.jsonl`. Supported steps create a preview, bind its message ID, save, cancel, advance time, and assert lifecycle errors.

```json
{
  "id": "scenario_duplicate_save_one_shot",
  "steps": [
    {
      "action": "preview",
      "capture": "preview",
      "message_id": 201,
      "payload": {"subject": "Kopi", "amount": 20000}
    },
    {"action": "save", "target": "preview", "message_id": 201},
    {
      "action": "save",
      "target": "preview",
      "message_id": 201,
      "expect_error": "consumed"
    }
  ],
  "expected": {"mutation_count": 1}
}
```

Scenarios use in-memory state. They do not send Telegram messages or write Sheets.

## Interpreting failures

A fixture failure identifies the exact field or invariant. Correct the fixture only when current approved behavior or business rules prove the old expectation obsolete. Otherwise treat the failure as a regression or a documented product gap.

Critical cases cannot be optional. Do not remove fields or weaken assertions merely to restore a green run.

## Live Gemini evaluation

Live evaluation is separate from pytest and default-disabled. It uses only synthetic inputs, static category/account lists, and parser draft output. It never starts Telegram, writes Sheets, or runs the scheduler.

```powershell
$env:ENABLE_LIVE_AI_EVAL = "1"
$env:GEMINI_API_KEY = "<evaluation-key>"
python evals/run_parser_eval.py
```

The runner exits non-zero before calling Gemini when opt-in or `GEMINI_API_KEY` is missing. Reports are timestamped under `evals/reports/` and include commit, dataset version, prompt version, model configuration, metrics, and failed case IDs. Token usage remains `null` when provider metadata is unavailable; cost is not estimated.

Compare and gate reports:

```powershell
python evals/compare_runs.py evals/reports/baseline.json evals/reports/candidate.json
python evals/gates.py evals/reports/baseline.json evals/reports/candidate.json
```

Gate thresholds and critical tags are centralized in `evals/gates.py`.

## CI

`.github/workflows/offline-tests.yml` uses Python 3.12, installs `requirements-dev.txt`, runs the full offline suite, compiles application/test/evaluation modules, performs import smoke, and checks whitespace. It provides no production credentials and does not run live AI evaluation.

## External staging verification

Offline tests do not prove real Google Sheets rollback behavior, Telegram delivery ordering, Gemini Vision output, or scheduler contention. Use the detailed staging checklist in the debug-matrix coverage document only with an approved staging bot and spreadsheet.

Never run destructive staging checks against the production spreadsheet.
