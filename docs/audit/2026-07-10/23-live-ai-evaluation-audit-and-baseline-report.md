# Live AI Evaluation Audit and Baseline Report

Date: 2026-07-13  
Scope: audit and align existing live AI evaluation after Phase 0-5 and structured file logging  
External services: not called during default verification  
Live evaluation status: `NOT_RUN`

## Executive Summary

The repository already had an opt-in live Gemini parser evaluation framework under `evals/`. This task reused that framework instead of creating a parallel runner, report format, metric layer, or gate. The implementation now aligns the evaluator with Phase 0-5 contracts, current prompt-version metadata, current Gemini call-budget configuration, mixed parser/batch/image/AI-answer coverage, report comparison, and centralized regression gates.

Structured file logging was reused as-is. No new logger, log format, `FileHandler`, or environment variable was added by this live-evaluation work.

## Existing Evaluator Components Reused

| Component | Status | Action |
| :--- | :--- | :--- |
| `evals/run_parser_eval.py` | Reused and extended | Still the single opt-in live runner; now covers mixed live-AI features |
| `evals/cases/gemini_parser_cases.jsonl` | Reused and updated | Expanded with sanitized Phase 0-5 coverage |
| `evals/metrics.py` | Reused and extended | Added pass/fail counts and character accounting |
| `evals/compare_runs.py` | Reused and extended | Added improvement/degradation, pass/fail transitions, schema regression, critical-tag regression, and latency deltas |
| `evals/gates.py` | Reused and extended | Critical tags aligned with current safety contracts |
| `tests/unit/test_eval_foundation.py` | Reused and extended | Added offline checks for default-disabled live eval, credential fail-safe, metadata, and gate CLI failure |
| `evals/reports/` | Reused | Reports remain unique timestamped JSON files outside the application log |

## Reconnaissance Findings

| Area | Finding | Resolution |
| :--- | :--- | :--- |
| Entry points | The only live-AI entry point was `python evals/run_parser_eval.py` | Preserved |
| Dataset | Dataset only covered a small Phase 1A transaction parser subset | Expanded with sanitized parser, routing, batch, image, and AI-answer cases |
| Prompt metadata | Runner used old hard-coded `phase1a` prompt/model constants | Replaced with current prompt versions from `app/application/gemini_governance.py` and model values from active adapters |
| Metrics | Metrics lacked explicit passed/failed counts and character totals | Added `passed_cases`, `failed_cases`, `input_characters`, and `output_characters` |
| Comparison | Comparison only returned metric deltas and basic case transitions | Added required comparison categories |
| Gates | Critical tags did not match current Phase 0-5 list | Updated to transfer, debt, split bill, invalid date, future intent, cancellation, confirmation security, and multi-input |
| Live `/ask` coverage | No AI-answer coverage existed | Added synthetic grounded-answer cases for `/ask`, `/insight`, `/audit`, and `/coach` modes |
| Logging | Evaluation did not need a second logging system | Existing `app/observability.py` and `LOG_FILE` behavior were left intact |

## Dataset Changes

The sanitized dataset now includes cases for:

- normal transaction parsing;
- transfer;
- debt direction safety routing;
- partial debt payment routing;
- split-bill payer routing;
- cancellation language;
- future intent;
- invalid date;
- malformed model output;
- multi-input batch parsing;
- stable multi-input ordering;
- clarification routing;
- image receipt parsing;
- `/ask`;
- `/insight`;
- `/audit`;
- `/coach`;
- context truncation and record caps.

The cases are synthetic and use generic accounts, people, categories, and amounts. No real private financial history, credentials, raw prompts, receipt bytes, or production identifiers were added.

## Metrics and Gates

Reports include:

- `run_id`;
- `timestamp`;
- `git_commit`;
- `dataset_version`;
- feature list;
- prompt versions;
- models;
- model configuration;
- total, passed, and failed cases;
- valid schema rate;
- transaction type, amount, account, category, destination account, and routing accuracy;
- invalid JSON and error rates;
- average, p50, and p95 latency;
- input and output characters;
- token usage only when provider metadata is available;
- failure breakdown by field and tag.

Comparison now identifies metric improvement, metric degradation, pass-to-fail cases, fail-to-pass cases, schema regression, critical-tag regression, and latency change.

Gate mode remains centralized in `evals/gates.py` and returns non-zero for a synthetic critical regression.

## Prompt Version and Call Budget Alignment

The evaluator now derives prompt versions from `PROMPT_VERSIONS` in `app/application/gemini_governance.py`. The report model configuration records:

- `GEMINI_CALLS_PER_UPDATE`;
- `GEMINI_MAX_INPUT_CHARS`;
- `GEMINI_MAX_OUTPUT_TOKENS`;
- `GEMINI_MAX_OUTPUT_CHARS`;
- `AI_CONTEXT_RECORD_LIMIT`;
- parser/image/finance-answer temperatures.

No Gemini model, prompt meaning, output schema, or call-budget implementation was changed.

## Live Execution Status

Live evaluation was not run because the task did not have explicit live-eval opt-in plus valid test credentials.

```text
Live evaluation status: NOT_RUN
```

The default command exits before importing Gemini parser/provider paths when `ENABLE_LIVE_AI_EVAL=1` is absent or `GEMINI_API_KEY` is missing.

## File Logging Compatibility and Privacy

The existing structured file logging implementation remains the only application logging path:

- console logging remains enabled;
- `LOG_FILE` appends JSON lines when configured;
- empty `LOG_FILE` disables file logging;
- `logs/` remains ignored by Git;
- evaluation reports continue to use `evals/reports/`;
- evaluation code does not create another logger or report to the application log file;
- raw prompts, API keys, receipt bytes, and private finance inputs are not written by the evaluator.

## Phase 0-5 README

Created:

```text
docs/phase-0-to-5/README.md
```

The README summarizes each phase by original problem, main implementation, user-visible effect, backend effect, code areas, tests/evidence, limitations, current architecture, user-visible changes, backend changes, remaining work, and canonical links.

It is linked from `docs/README.md` and included in the documentation checker inventory.

## Verification

Commands executed:

| Command | Result |
| :--- | :--- |
| `python -m pytest -q` | 328 passed, 1 cache warning |
| `python -m pytest -q tests\regression` | 164 passed, 1 cache warning |
| `python scripts\check_docs.py` | Documentation checks passed |
| `python -m compileall -q app evals tests scripts` | Passed |
| `git diff --check` | Passed; Git emitted line-ending notices only |
| `python -m pytest -q tests\unit\test_eval_foundation.py` | 6 passed |
| `python evals\run_parser_eval.py` | Exited before live execution because opt-in was absent |
| Missing-credential live-eval check with `ENABLE_LIVE_AI_EVAL=1` and no `GEMINI_API_KEY` | Exited non-zero before live execution |
| Fixture `evals/compare_runs.py` check | Passed and reported metric improvement, fail-to-pass transition, and latency change |
| Fixture `evals/gates.py` pass check | Passed |
| Fixture `evals/gates.py` synthetic critical regression | Returned non-zero |
| Unique report filename construction check | Produced distinct report paths |
| `git check-ignore logs\finance_bot.log` | `logs\finance_bot.log` is ignored |
| Credential-pattern scan over docs/evals/README/.env.example | No matches |

## Protected Contracts

No changes were made to:

- command names or syntax;
- callback data;
- financial calculations;
- Sheets schema;
- parser behavior used by production handlers;
- confirmation behavior;
- rollback or reconciliation;
- Gemini models or prompt meaning;
- Gemini call budgets;
- scheduler ownership;
- application logging format;
- `LOG_FILE` behavior.

## Residual Gaps

- Live Gemini baseline remains `NOT_RUN`.
- Real provider latency, token metadata, safety filters, quota behavior, and image understanding remain unverified without approved test credentials.
- Dummy Telegram and Google Sheets staging is still required for end-to-end operational confidence.
- Safety-routing contract cases document boundaries that must not be delegated to Gemini as write decisions.

## Recommended Next Step

Run a small sanitized live smoke subset only after explicit owner opt-in and valid test Gemini credentials are available. Save the first approved report as the live baseline and evaluate future reports through `evals/compare_runs.py` and `evals/gates.py`.
