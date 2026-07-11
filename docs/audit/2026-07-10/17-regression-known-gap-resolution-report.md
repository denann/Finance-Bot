# Regression Known-Gap Resolution Report

- Date completed: 2026-07-11
- Starting state: 253 passed, 23 strict xfailed
- Final state: 276 passed, 0 xfailed
- External services: not called
- Commit or push: not performed

## Scope

The owner explicitly approved fixing all 23 known-gap regression contracts after the callback-containment follow-up. Expected values were not weakened. Each case was first run with `--runxfail`, fixed in production parsing/safety code, and then promoted from `known_gap` to `active` only after all 50 expansion tests passed.

## Implemented Contracts

| Area | Resolved behavior |
| :--- | :--- |
| Amount validation | Negative transaction amounts are rejected; implausibly large amounts require warning preview. |
| Transfer safety | Same-account transfers and person-directed `kirim` inputs require clarification. |
| Date handling | Calendar-month subtraction replaces fixed 30-day math; invalid natural dates such as `30 Februari` are explicit invalid dates. |
| Future and cancellation intent | `besok`, planned future expenses, `tidak jadi`, and `batal` no longer become completed transactions silently. |
| Debt direction | `saya minjem ... dari ...` becomes payable; partial receivable/payable payment wording preserves person, direction, amount, and account. |
| Split bill | Explicit payer wording is attached; zero divisor, participant mismatch, missing names, and possible unnamed split intent require clarification; gross amount remains intact before participant resolution. |
| Multi-input | Canceled items become ignored items and self-borrow debt direction remains payable per item. |

## Files Changed

- `app/nlp/regex_parser.py`
- `app/nlp/parse_safety.py`
- `app/nlp/normalizer.py`
- `app/bot/handler_parts/transaction_flow.py`
- `tests/regression/fixtures/expansion_cases.jsonl`
- Regression and audit documentation

No Telegram command, callback data, Google Sheets schema, account name, category name, or confirmation contract changed.

## Verification

| Command | Result |
| :--- | :--- |
| `python -m pytest -q tests/regression/test_expansion_regression.py --runxfail` before fixes | 23 failed, 27 passed. |
| Same command after production fixes | 50 passed. |
| Normal expansion suite after status promotion | 50 passed. |
| `python -m pytest -q tests/regression` | 164 passed. |
| `python -m pytest -q` | 276 passed. |
| `python -m compileall -q app evals main.py tests` | Pass. |
| `git diff --check` | Pass. |

The Windows `.pytest_cache` warning remains environmental and does not affect test results. Default offline guards remained active throughout verification.

## Residual Risk

- These rules are deterministic and covered by the exact historical inputs, but real Telegram message timing remains staging-only.
- Future new language variants should be added as active regression fixtures or strict known gaps before parser behavior changes.
