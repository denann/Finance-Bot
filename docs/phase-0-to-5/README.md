# Phase 0-5 Historical Overview

This page summarizes an earlier improvement program. It is historical context,
not a release-status page. The detailed audit files that originally accompanied
the program are no longer present in the active repository.

For current behavior, use the [documentation index](../README.md), passing
tests, registries, and implementation.

## What the Program Changed

| Phase | Focus | Lasting repository areas |
| :--- | :--- | :--- |
| 0 | Mutation safety, confirmation, rollback, reconciliation, and invalid-date handling | `app/bot/pending_actions.py`, `app/services/`, `app/sheets/client.py` |
| 1 | Regression coverage, offline test doubles, and redacted observability | `tests/`, `app/observability.py`, `app/api/` |
| 2 | Application boundaries, callback containment, and parser hardening | `app/application/`, `app/bot/callback_contracts.py`, `app/nlp/` |
| 3 | Bounded external work and local benchmark coverage | `app/application/external_io.py`, `app/application/gemini_governance.py`, `benchmarks/` |
| 4 | Documentation ownership and drift checks | `docs/`, `scripts/check_docs.py` |
| 5 | Current-scale persistence decision and migration triggers | `docs/architecture/`, `docs/testing/phase-5-scale-staging.md` |

## Current Interpretation

- Google Sheets remains the persistence layer for the current personal,
  single-process product.
- All state-changing finance flows must preserve preview-before-write and
  explicit confirmation.
- Ambiguous batch items are clarified individually before a final batch
  preview.
- Application modules coordinate business services without importing the
  Telegram interface.
- External provider behavior is not proven by offline tests; Telegram, Google
  Sheets, and Gemini need approved staging checks when production confidence is
  required.

## Historical Verification Note

Earlier revisions recorded dated passing-test counts. Those counts are not
repeated here because the corresponding detailed evidence files are absent and
the active test suite continues to change. Run the current gates instead:

```powershell
python -m pytest -q
python scripts/check_docs.py
python -m compileall -q app main.py tests scripts benchmarks
git diff --check
```

## Current References

- [Architecture](../02-architecture.md)
- [Safety and Confirmation](../05-safety-and-confirmation.md)
- [Testing](../testing.md)
- [Documentation Source of Truth](../documentation-source-of-truth.md)
- [ADR-001 Scale and Persistence](../architecture/adr-001-scale-and-persistence.md)
- [Scale and Migration Triggers](../architecture/scale-and-migration-triggers.md)
- [Phase 5 Scale Staging](../testing/phase-5-scale-staging.md)
