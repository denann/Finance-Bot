# Regression Expansion — 2026-07-11

## Summary

The regression fixture corpus was expanded from **92 to 141 cases** without adding an exact duplicate input.

| Status | Added cases | Meaning |
| :--- | ---: | :--- |
| Active | 26 | Current implementation already satisfies the expected contract. |
| Known gap | 23 | Intended contract is recorded as a strict expected failure (`xfail`). |
| **Total added** | **49** | New parser, safety, split, multi-input, debt, date, and callback coverage. |

The complete pytest suite now collects **220 tests**. The verified offline result is:

```text
197 passed, 23 xfailed
```

> Historical snapshot: these counts predate integration with the completed Phase 2 boundary work. Use the current full-suite verification in the Phase 2 follow-up report for the merged totals.

> Resolution update: all 23 known-gap contracts were implemented later on 2026-07-11 and promoted to active regression cases. See `docs/audit/2026-07-10/17-regression-known-gap-resolution-report.md`.

## Active coverage added

- Decimal and thousands nominal formats: `1,5 juta`, `1.5jt`, `12.500`, and `12,500`.
- Transfer direction across alternative word orders.
- Historical GoPay top-up from BSI.
- Historical explicit and relative date cases for nasi Padang.
- Historical `3000k` top-up with a date.
- Receivable input with account and relative date.
- Historical decimal debt payment amount.
- Historical `ditalangin Annisa` debt routing.
- Zero-amount and missing-transfer-amount rejection.
- Indonesian day-first slash date.
- Ambiguous payment-to-person clarification.
- End-of-month pending clarification.
- Historical split-bill subject cleanup for galon and ditalangin minyak.
- Multi-transfer, per-item dates, duplicate batch items, and incomplete transfer destination.
- One-shot set-balance confirmation.

## Known gaps recorded

- Negative and implausibly large nominal validation.
- Same-account transfer rejection.
- Ambiguous money sent to a person.
- Future plans and explicit `besok` handling.
- Negated or canceled transaction wording.
- Natural-language invalid dates such as `30 Februari`.
- `saya minjem ... dari ...` debt direction.
- Partial debt-payment wording.
- Split payer detection, participant-count mismatch, and zero divisor.
- Possible split bill with several named people but no split keyword.
- Historical split without participant names.
- Canceled items and reversed debt direction inside multi-input.
- Calendar-month arithmetic for `2 bulan lalu`.

## Duplicate policy

The expansion test normalizes case and whitespace, then rejects any new input that exactly duplicates an input in the legacy JSONL fixtures. Semantically related variations remain allowed when they test a different syntax or risk boundary.
