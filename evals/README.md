# Live Gemini Parser Evaluation

This directory is separate from deterministic pytest. Default test commands never import or run the live evaluator.

## Safety boundary

- Live execution requires `ENABLE_LIVE_AI_EVAL=1` and a Gemini API key.
- Cases are synthetic and contain no financial history, debt records, credentials, or production user data.
- The runner replaces dynamic category/account lookups with static evaluation lists, so it does not open Google Sheets.
- The runner parses drafts only. It does not build a Telegram application or call mutation services.
- Reports do not include API keys, prompts containing secrets, or estimated cost.

## Run

```powershell
$env:ENABLE_LIVE_AI_EVAL = "1"
$env:GEMINI_API_KEY = "<evaluation-key>"
python evals/run_parser_eval.py
```

Without both variables, the command exits non-zero before importing the Gemini parser.

## Compare and gate

```powershell
python evals/compare_runs.py evals/reports/baseline.json evals/reports/candidate.json
python evals/gates.py evals/reports/baseline.json evals/reports/candidate.json
```

Thresholds and critical tags are centralized in `evals/gates.py`. Reports are timestamped and never overwrite an older run.

## Ownership Contract

Evals own opt-in provider evidence and versioned reports. They do not replace offline pytest, modify prompts/models, or use production finance data. Live execution requires explicit opt-in and a key; offline golden contracts belong in the normal test suite.
