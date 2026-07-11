# Phase 1A Regression and AI Evaluation Report

- Date completed: 2026-07-11
- Baseline branch: `codex/check-worktree-access`
- External services: not called
- Live AI evaluation: `NOT_RUN`

## What changed

- Added fixture-driven parser, slash routing, parse-safety, preview readiness, split-bill, multi-input, manual-edit, and multi-step confirmation regressions.
- Added recursive partial assertions with case ID, raw input, scenario step, field, expected value, actual value, route, and flow diagnostics.
- Added an autouse external-call guard for sockets, HTTP clients, Telegram Bot API, real gspread authorization, production credentials, and accidental live-evaluation opt-in.
- Reused the existing Phase 0 pending-action implementation and fake boundaries; no parallel production action store or Sheets implementation was created.
- Added a default-disabled live Gemini parser evaluator with synthetic cases, schema validation, run metadata, metrics, timestamped JSON reports, comparison, and centralized gates.
- Added minimal GitHub Actions CI for Python 3.12 offline tests, compile, import smoke, and whitespace checks.
- Updated the testing guide, root project structure, docs index, and complete debug-matrix coverage inventory.
- Did not modify production handlers, command names, worksheet names, columns, business rules, or persistence architecture.

## Baseline

| Item | Result |
| :--- | :--- |
| Worktree before implementation | Clean on `codex/check-worktree-access` |
| Baseline command | `python -m pytest -q tests` with pytest installed in a temporary test-only path |
| Previous tests | 35 passed, 0 failed, 0 skipped |
| Baseline duration | 1.44 seconds |
| Production credentials | Not loaded |
| External services | Not called |

The system Python did not include pytest. Pytest 8.4.1 was installed to `C:\Users\Administrator\AppData\Local\Temp\codex-phase1a-pytest`; repository dependency manifests were not changed.

## Regression architecture

| Component | Purpose |
| :--- | :--- |
| `tests/regression/fixtures/*.jsonl` | Stable cases with matrix traceability, partial expectations, reference date, and tags |
| `tests/regression/case_loader.py` | JSONL loading and field-level diagnostic assertions |
| Parser/routing/safety tests | Deterministic extraction and safe route decisions |
| Preview/split/multi/edit tests | Continuation requirements, allocation, ordering, and no-write-before-confirm invariants |
| Scenario runner | One-shot action create, bind, save, cancel, expiry, duplicate, and stale-message behavior |
| `tests/conftest.py` | Default external-service and credential guard |
| `evals/` | Explicit live-AI runner, synthetic dataset, metrics, comparison, and gates |

Fixture inventory: 92 JSONL cases, including 5 multi-step scenario cases. The regression suite executes 105 pytest cases because shared schema, decision, guard, and invariant tests add coverage beyond one assertion per fixture.

## Regression coverage

| Area | Matrix cases | Automated | Live AI | Staging/manual | Ambiguous/obsolete |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Command routing and read-only | 24 | 10 | 0 | 14 | 0 |
| Transactions and account readiness | 15 | 15 | 0 | 0 | 0 |
| Date safety seeds | 9 | 9 | 0 | 0 | 0 |
| Parse safety | 9 | 9 | 0 | 0 | 0 |
| Transfers/top-up | 7 | 7 | 0 | 0 | 0 |
| Debt/talangin | 15 | 14 | 0 | 0 | 1 |
| Split bill | 9 | 9 | 0 | 0 | 0 |
| Ditalangin + split/PTPT | 3 | 0 | 0 | 3 | 0 |
| Multi-input | 7 | 6 | 0 | 0 | 1 |
| Pending | 8 | 0 | 0 | 6 | 2 obsolete |
| Budget | 5 | 0 | 0 | 0 | 5 ambiguous |
| Recurring | 5 | 0 | 0 | 1 | 4 obsolete |
| Assets/net worth | 8 | 0 | 0 | 4 | 4 obsolete |
| Edit/delete transaction | 9 | 0 | 0 | 9 | 0 |
| Debt management commands | 9 | 0 | 0 | 9 | 0 |
| Reports/search/AI insight | 11 | 0 | 5 | 6 | 0 |
| Image input | 4 | 0 | 0 | 4 | 0 |
| Manual edit | 10 | 4 | 0 | 6 | 0 |

The authoritative 168-row classification is in `docs/testing/debug-matrix-coverage.md`: 59 `AUTOMATED_OFFLINE`, 15 `AUTOMATED_WITH_FAKE_STATE`, 5 `LIVE_AI_EVAL`, 72 `STAGING_REQUIRED`, 7 `AMBIGUOUS_EXPECTATION`, and 10 `OBSOLETE_EXPECTATION`.

## Cases changed from the supplied matrix

The following old `DIRECT_SAVE_OR_CONFIRM` expectations were changed to immutable final confirmation because Phase 0 established preview-before-write as the approved contract.

| Case | Previous expectation | Current expectation | Reason and evidence |
| :--- | :--- | :--- | :--- |
| Pending 7, `/pending_paid` | Direct save or confirm | Exact final preview, then one-shot `Simpan / Batal` | Phase 0 F-007 confirmation matrix and command mutation executor |
| Pending 8, `/pending_cancel` | Direct save or confirm | Exact final preview, then one-shot `Simpan / Batal` | Phase 0 F-007 confirmation matrix and command mutation executor |
| Recurring 2, `/recurring_add` | Direct create | Final recurring preview before create | Current recurring-add handler builds confirmation preview |
| Recurring 3, `/recurring_run` | Direct run or confirm | Exact run preview, then one-shot `Simpan / Batal` | Phase 0 F-007 confirmation matrix |
| Recurring 4, `/recurring_edit` | Direct update or confirm | Exact edit preview, then one-shot `Simpan / Batal` | Phase 0 F-007 confirmation matrix |
| Recurring 5, `/recurring_off` | Direct disable or confirm | Exact disable preview, then one-shot `Simpan / Batal` | Phase 0 F-007 confirmation matrix |
| Asset 4, `/asset_update ... value` | Direct update or confirm | Exact update preview, then one-shot `Simpan / Batal` | Phase 0 F-007 confirmation matrix |
| Asset 5, `/asset_update ... unit_price` | Direct update or confirm | Exact update preview, then one-shot `Simpan / Batal` | Phase 0 F-007 confirmation matrix |
| Asset 6, `/asset_off` | Direct disable or confirm | Exact disable preview, then one-shot `Simpan / Batal` | Phase 0 F-007 confirmation matrix |
| Asset 7, `/networth_snapshot` | Direct snapshot or confirm | Frozen totals preview, then one-shot `Simpan / Batal` | Phase 0 F-007 snapshot contract |

Budget set remains ambiguous because Phase 0 did not change that product policy.

## Newly verified gaps

| Severity | Classification | Affected cases | Current behavior | Required decision |
| :--- | :--- | :--- | :--- | :--- |
| Medium | Pre-existing parser gap | Debt 2; Multi-input 6 | `Budi minjem 50k dari DANA` parses receivable direction, person, and amount, but does not retain DANA as the account. A mixed batch therefore still requires account clarification. | Decide whether new debt cashflow parsers should extract `dari <account>` in Phase 1B. |
| Medium | Ambiguous product policy | Budget 1-3 and flow checklist | Budget writes remain outside the Phase 0 universal confirmation inventory. | Decide whether budget mutations require final preview. |

No Phase 0 critical regression was discovered. No production fix was made for these gaps because changing debt cashflow account behavior or budget confirmation is a product-contract decision.

## Test results

| Command | Passed | Failed | Skipped | Duration | External calls |
| :--- | ---: | ---: | ---: | ---: | :--- |
| Baseline `python -m pytest -q tests` | 35 | 0 | 0 | 1.44 s | Blocked by existing stubs |
| Final `python -m pytest -q tests` | 143 | 0 | 0 | 1.94 s | Blocked |
| `python -m pytest -q tests/regression` | 105 | 0 | 0 | 1.86 s | Blocked |
| `python -m pytest -q tests/unit` | 14 | 0 | 0 | 0.62 s | Blocked |
| `python -m pytest -q tests/service` | 12 | 0 | 0 | 0.60 s | Blocked |
| `python -m pytest -q tests/integration` | 8 | 0 | 0 | 1.37 s | Blocked |
| External-call guard test | 3 | 0 | 0 | 0.49 s | Expected calls rejected |
| `python -m compileall -q app evals main.py tests` | Pass | 0 | 0 | - | None |
| Import smoke | Pass | 0 | 0 | - | None |
| `git diff --check` | Pass | 0 | 0 | - | None |

Final total: 143 tests, which preserves the previous 35 and adds 108 passing test cases.

## Live AI evaluation status

Status: `NOT_RUN`.

The default-disabled check was executed without opt-in or credentials and stopped before importing/calling Gemini. No model quality, latency, token, or cost result is claimed.

## CI status

`.github/workflows/offline-tests.yml` was added and its local commands pass. The GitHub-hosted workflow was not executed in this task because no commit or push was performed.

## Remaining gaps

- Real Telegram message ordering, message edits, button layout, and delivery failures remain staging-only.
- Real gspread ambiguous commit and compensating rollback semantics remain staging-only.
- Real scheduler/manual recurring contention remains staging-only; approved deployment is still single-process.
- Receipt and transfer image evaluation requires synthetic image fixtures or approved staging Gemini Vision evaluation.
- Management command copy and exact fake-Sheets balance deltas need additional case-specific integration scenarios.
- Manual field-button edits and split/debt/pending/asset recalculation edits need full fake handler state scenarios.
- PTPT/double-debt business semantics and budget confirmation policy remain owner decisions.

## Recommended next step

Proceed to Phase 1B - Observability and Operational Safety after the owner records decisions for debt account extraction and budget confirmation. The current offline suite is green and no critical regression blocks Phase 1B.

No commit or push was performed.
