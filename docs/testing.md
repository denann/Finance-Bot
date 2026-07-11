# Testing

## Scope

The automated suite protects Phase 0 data-integrity contracts without contacting Telegram, Google Sheets, Gemini, webhooks, or production schedulers.

| Test area | Coverage |
| :--- | :--- |
| Unit | Date absent/valid/invalid states, parser regression corpus, immutable action lifecycle |
| Service | Save outcome semantics, rollback propagation, recurring exactly-once, append reconciliation |
| Integration | Diagnostic route policy and public command confirmation inventory |
| Fakes | In-memory worksheet/failure plan, Telegram update/callback objects, frozen clock, optional import stubs |

## Install and run

Use a development environment rather than adding pytest to production-only installation:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
python -m compileall app main.py tests
```

The suite must run without `.env`, Telegram token, service-account JSON, spreadsheet ID, Gemini key, or network access.

## Failure-injection invariants

Tests verify outcomes, not only raised exceptions:

- rollback/unknown commits never return `success=True`;
- a logical transaction ID is not appended twice after an ambiguous response;
- result-style failures after a mutation escape as typed errors so the outer rollback boundary runs;
- a preview action is immutable, owner-bound, message-bound when available, expiring, and consumable once;
- one recurring `rule_id + scheduled_run_date` produces at most one transaction;
- public F-007 commands do not call write services before final confirmation;
- anonymous `/test-sheets` access stops before the Sheets probe.

## External staging verification

Automated tests do not prove real Google Sheets rollback behavior or Telegram delivery ordering. Run the following only with a staging bot and staging spreadsheet after owner approval:

1. Create previews A and B; confirm A, then B, and verify each exact row once.
2. Double-click one confirmation and verify a single transaction/balance delta.
3. Press a legacy/stale callback and verify no write.
4. Trigger one recurring occurrence from reminder and manual run close together; verify one transaction and one successful log.
5. Inject/observe an ambiguous append failure and reconcile the existing logical ID before retry.
6. Enter invalid dates such as `31/02/2026` and verify clarification without a row.
7. Exercise each direct-write command and verify no write before `Simpan`; verify `Batal` writes nothing.
8. Verify `/test-sheets` returns hidden/forbidden by default and never repairs schema.

Record worksheet row IDs, balances, recurring logs, and callback results before and after each staging case. Never run these checks against the production spreadsheet.
