# Phase 2 Follow-Up: Legacy Callback Fallback Audit and Containment

- Date completed: 2026-07-11
- Branch: `codex/phase-2-domain-boundaries`
- Phase 2 baseline before owner archive: 223 passed
- External services: not called
- Commit or push: not performed

## Owner-Provided Regression Expansion Integration

### Files Merged

- `tests/regression/fixtures/expansion_cases.jsonl`
- `tests/regression/test_expansion_regression.py`
- `docs/testing.md`
- `docs/testing/regression-expansion-2026-07-11.md`

### Conflicts and Resolutions

| Conflict | Resolution |
| :--- | :--- |
| The three expansion fixture/test/report files did not exist in the Phase 2 worktree. | Added the owner versions without changing case IDs, inputs, expectations, statuses, or strict `xfail` reasons. |
| Archive `docs/testing.md` predated typed results, bulk state, architecture tests, and other Phase 2 coverage. | Merged only the regression-expansion section into the newer Phase 2 document; retained newer coverage tables and commands. |
| Historical report stated 220 collected and 197 passed. | Preserved it as a dated historical snapshot and added an explicit note directing readers to current merged verification. |
| Repository contained an unrelated untracked `New Update.zip`. | Left untouched and excluded from the merge. |

No approved business rule, command, callback data, Sheets schema, Phase 0 safety contract, Phase 1 privacy contract, or Phase 2 module boundary required a conflict decision.

### Expansion Counts

| Measure | Result |
| :--- | ---: |
| Cases supplied | 49 |
| Active cases added | 26 |
| Strict known-gap cases added | 23 |
| Duplicate case IDs rejected | 0 |
| Exact duplicate inputs rejected | 0 |
| Expansion test result | 27 passed, 23 xfailed |

The twenty-seventh passing test is the duplicate/status integrity test. All active cases pass, every known gap remains a strict expected failure, and there are no unexpected passes or changed failure classifications.

### Baseline Change

| Point | Passed | Xfailed | Collected |
| :--- | ---: | ---: | ---: |
| Phase 2 before archive | 223 | 0 | 223 |
| Archive merged, before callback containment | 250 | 23 | 273 |
| Final follow-up | 253 | 23 | 276 |

No Phase 2 file or test was overwritten by the archive merge.

## Callback Fallback Audit

The Phase 2 dispatcher previously sent every non-bulk callback to `legacy_callback_handler`. Unknown callback data was eventually rejected safely, but only after entering the 3,702-line legacy function.

The audited public callback inventory contains:

- 5 bulk prefixes owned by `bulk_flow`;
- 22 legacy prefixes;
- 4 exact legacy callback values;
- one fail-closed unknown path owned by the dispatcher.

The legacy handler remains large because rewriting multiple finance contexts was outside this follow-up. Its reachability is now explicit and test-protected instead of acting as an unrestricted catch-all.

## Containment Implemented

- Added `app.bot.callback_contracts` as the explicit legacy prefix/exact-value registry.
- Routed only audited legacy callback data into `legacy_callback_handler`.
- Kept bulk callback ownership unchanged.
- Rejected unknown callbacks before legacy execution with the existing unavailable/expired response.
- Preserved authorization and callback-loading behavior on the unknown path.
- Added tests proving known data is unchanged, unknown data cannot reach legacy code, and pending state is not mutated.
- Extended the existing callback snapshot so registry drift fails CI.

No callback string was renamed or rewritten.

## Verification

| Command | Result |
| :--- | :--- |
| `python -m pytest -q` | 253 passed, 23 xfailed, 0 failed, 0 xpassed, 0 skipped. |
| `python -m pytest -q tests/regression` | 141 passed, 23 xfailed. |
| `python -m pytest -q tests/regression/test_expansion_regression.py` | 27 passed, 23 xfailed. |
| `python -m pytest --collect-only -q` | 276 tests collected. |
| Callback containment and contract targets | 43 passed, 23 xfailed. |
| `python -m compileall -q app evals main.py tests` | Pass. |
| `git diff --check` | Pass; line-ending notices are informational. |

The existing Windows pytest cache warning does not affect collection or execution. The default external-call guard remained active, and no real Telegram, Google Sheets, Gemini, HTTP, credential, webhook, or scheduler boundary was called.

## Residual Risk

- `legacy_callback_handler` remains 3,702 lines and should be extracted one bounded context at a time with behavior snapshots.
- The audited registry must be updated together with any future callback branch or button; snapshot tests enforce this coupling.
- Real old-message callback timing and restart behavior remain staging-only checks.
- The 23 known gaps remain intentionally unresolved and are not accepted permanent behavior.

This final residual-risk statement was superseded later on 2026-07-11 when all 23 contracts were implemented and promoted to active tests. See `17-regression-known-gap-resolution-report.md`.

## Recommended Next Step

The fallback is now contained. Continue to Phase 3 after owner review; extract another legacy callback context only when its behavior has dedicated contract coverage.
