# Live Gemini Evaluation

This directory is separate from deterministic pytest. Default test commands never import or run the live evaluator.

## Safety boundary

- Live execution requires `ENABLE_LIVE_AI_EVAL=1` and a Gemini API key.
- Cases are synthetic and contain no production financial history, debt records, credentials, receipt contents, or private user data.
- The runner replaces dynamic category/account lookups with static evaluation lists, so it does not open Google Sheets.
- The runner evaluates Gemini draft parsing, batch parsing, image parsing, and AI-answer grounding contracts. Safety-routing contract cases are included so the report records where Gemini must not be treated as a write decision maker.
- The runner does not build a Telegram application, start the scheduler, or call mutation services.
- Reports do not include API keys, raw prompts, receipt bytes, real private data, or estimated cost.

## Run

```powershell
$env:ENABLE_LIVE_AI_EVAL = "1"
$env:GEMINI_API_KEY = "<evaluation-key>"
python evals/run_parser_eval.py
```

Without both variables, the command exits non-zero before importing Gemini parser/provider paths.

## Compare and gate

```powershell
python evals/compare_runs.py evals/reports/baseline.json evals/reports/candidate.json
python evals/gates.py evals/reports/baseline.json evals/reports/candidate.json
```

Thresholds and critical tags are centralized in `evals/gates.py`. Reports are timestamped and never overwrite an older run.

## Ownership Contract

Evals own opt-in provider evidence and versioned reports. They do not replace offline pytest, modify prompts/models, or use production finance data. Live execution requires explicit opt-in and a key; offline golden contracts belong in the normal test suite.

Current report metadata is derived from the implementation: prompt versions from `app/application/gemini_governance.py`, model values from the active Gemini adapters, and bounds from `app/config.py`. Token usage remains `null` when provider metadata is not exposed to the runner.
