# Phase 0 Implementation Report

Tanggal implementasi: 2026-07-10  
Baseline: `1f07bd213659dd1fab5699589b3876cd8d213523`  
Scope: F-001–F-008  
External services: tidak dipanggil

## Ringkasan

Phase 0 menutup delapan finding data-integrity dan deployment safety tanpa mengganti command, nama/struktur worksheet, kolom Google Sheets, business rule, deployment single-user/single-process, atau persistence backend.

Perubahan utama:

- menambahkan offline pytest foundation, fake Sheets/Telegram/clock, dan failure injection;
- membuat commit/rollback outcome eksplisit sehingga rollback/unknown tidak pernah menjadi sukses;
- membedakan tanggal `absent`, `valid`, dan `invalid` serta menjaga invalid date keluar dari seluruh routing, termasuk debt;
- menonaktifkan `/test-sheets` secara default dan membuat mode opt-in-nya authenticated, read-only, dan redacted;
- mengikat seluruh final confirmation keyboard ke immutable, expiring, one-shot `action_id` in-memory;
- memakai `recurring_logs` existing dan key `rule_id + scheduled_run_date` untuk recurring exactly-once dalam single process;
- membedakan retry read/idempotent write dari append non-idempotent dan merekonsiliasi logical ID sebelum retry;
- mempromosikan post-mutation `success=False` menjadi typed error agar outer rollback boundary dijalankan;
- menambah final `Simpan / Batal` untuk pending, recurring, asset, dan net-worth mutation yang sebelumnya langsung menulis.

| Status | Finding |
| :--- | :--- |
| Closed | F-001, F-002, F-003, F-004, F-005, F-006, F-007, F-008 |
| Partially closed | Tidak ada pada scope implementasi; real external behavior masih membutuhkan staging verification |
| Open | Tidak ada pada Phase 0 |

Keputusan desain utama: action store tetap in-memory; recurring memakai worksheet/log schema existing; logical row ID memakai kolom ID existing; operasi tanpa logical ID yang tidak dapat direkonsiliasi menghasilkan `commit outcome unknown` dan tidak blind retry.

## F-001 — Immutable preview action

- **Status:** Closed.
- **File:** `app/bot/pending_actions.py`, `app/bot/application.py`, `app/bot/keyboards.py`, `transaction_flow.py`, `common_imports.py`, `core.py`, `callback_handler.py`.
- **Implementasi:** final keyboard membuat opaque `action_id`; payload snapshot, owner, flow, preview message ID bila tersedia, created/expiry time, consumed time, dan status disimpan per user. Confirm melakukan owner/message/TTL/status validation dan compare-and-consume sebelum memulihkan exact snapshot. Semua legacy `confirm:<target>` ditolak.
- **Test:** preview A/B, immutable copy, duplicate confirm, confirmed→cancel, canceled→confirm, expiry, wrong user, wrong message, lost store/restart, legacy target guard.
- **Acceptance criteria:** preview A hanya menghasilkan payload A; satu action satu konsumsi; stale/legacy tidak menulis.
- **Residual risk:** action consumed sebelum write agar double-click aman. Jika write gagal, user harus membuat preview baru; action tidak dapat diretry. Restart menghapus pending action sesuai scope.

## F-002 — Save outcome semantics

- **Status:** Closed.
- **File:** `app/services/transaction_service.py`.
- **Implementasi:** single dan batch save mengembalikan `success=False` dengan `commit_status`, `rollback_status`, dan `reconciliation_required`. `SheetsAtomicWriteError` dengan rollback sukses menjadi `commit_failed`; unverified/failed rollback menjadi `commit_outcome_unknown`.
- **Test:** balance exception setelah append, rollback succeeded, plain unknown outcome, batch unknown outcome.
- **Acceptance criteria:** tidak ada save success setelah balance failure/rollback; `transaction_id`/`saved_ids` tidak dipublikasikan sebagai sukses.
- **Residual risk:** unknown outcome masih membutuhkan manual reconciliation; candidate IDs hanya disimpan di internal result.

## F-003 — Multi-step failure contract

- **Status:** Closed.
- **File:** `app/services/operation_errors.py`, `transaction_service.py`, `callback_handler.py`, `core.py`.
- **Implementasi:** `AtomicOperationError`, `PartialMutationError`, `CommitOutcomeUnknownError`, dan `ReconciliationRequiredError` membedakan failure semantics. Result-style failure setelah mutation dipromosikan menjadi exception. Delete/edit/debt payment/split/debt relation flows tidak lagi mengembalikan normal warning-success setelah known partial failure. Outer `sheets_transaction` menerima exception dan menjalankan rollback reverse order.
- **Test:** result-style failure promotion, rollback callback execution, delete balance→debt failure, edit balance→row failure, single/mixed/batch debt/split source guards.
- **Acceptance criteria:** post-mutation failure tidak keluar sebagai normal success; user error membedakan rollback dari reconciliation requirement.
- **Residual risk:** Google Sheets bukan transaction database. Rollback tetap best-effort; outage saat rollback dapat memerlukan reconciliation manual.

## F-004 — Recurring exactly-once

- **Status:** Closed untuk approved single-process model.
- **File:** `app/services/recurring_service.py`, `app/scheduler/jobs.py`, `callback_handler.py`, `command_mutations.py`.
- **Implementasi:** logical identity `rule_id:scheduled_run_date`, existing `recurring_logs` lookup, in-process lock/inflight claim, due/stale validation, and recheck inside Sheets transaction. Reminder carries scheduled date and now opens final preview. Duplicate success is idempotent and does not call save again.
- **Test:** double invocation, duplicate log lookup, stale month, not due, transaction failure, log failure, sequential scheduler/manual race simulation.
- **Acceptance criteria:** one logical occurrence creates at most one transaction; duplicate callback changes no balance.
- **Residual risk:** no distributed exactly-once; deployment must remain single-process. A rollback failure after transaction/log mismatch still requires reconciliation.

## F-005 — Non-idempotent retry

- **Status:** Closed.
- **File:** `app/sheets/client.py`.
- **Implementasi:** retry API accepts operation type. Read/idempotent writes may retry. Append/batch append reconcile first-column logical IDs after ambiguous transient errors. Exactly-one single row or complete contiguous batch returns synthetic reconciled success; partial/duplicate/unverifiable results raise `SheetsCommitOutcomeUnknownError`. Append without usable ID is never blind retried.
- **Test:** 500 after server-side commit, no-ID unknown, partial batch, duplicate prevention, call-count assertion.
- **Acceptance criteria:** ambiguous append does not create two rows with the same logical ID; partial batch is not assumed atomic.
- **Residual risk:** correctness depends on existing logical IDs being unique. Existing historical duplicates are not repaired by Phase 0.

## F-006 — Explicit invalid date

- **Status:** Closed.
- **File:** `app/nlp/regex_parser.py`, `app/nlp/parse_safety.py`, `message_handlers.py`.
- **Implementasi:** `DateDetectionResult` distinguishes `absent`, `valid`, and `invalid`. Only absent defaults to today. Invalid calendar/out-of-range input has `value=None`, high-risk clarification flag, and an early message guard before debt/pending/multi routes.
- **Test:** `31/02/2026`, `2026-02-29`, `29/02/2024`, `31/04/2026`, `2026-13-01`, non-padded date, no date, and debt intent.
- **Acceptance criteria:** explicit invalid date never becomes today; valid and absent behavior remains compatible.
- **Residual risk:** business-day timezone still uses the process clock in many legacy helpers; timezone unification belongs to F-018/Phase 1.

## F-007 — Universal final confirmation

- **Status:** Closed for audited public mutation inventory.
- **File:** `app/bot/command_mutations.py`, `common_imports.py`, `command_handlers.py`, `health_recurring_export.py`, `networth_assets.py`, `callback_handler.py`, `net_worth_service.py`.
- **Implementasi:** `/pending_paid`, `/pending_cancel`, `/recurring_run`, `/recurring_edit`, `/recurring_off`, recurring `Sudah bayar`, `/asset_update`, `/asset_off`, dan `/networth_snapshot` validate/read first, create immutable preview, and write only through the allow-listed confirmation executor. Snapshot totals are frozen from preview to row write.
- **Test:** AST command confirmation matrix ensures handlers contain preview calls and no direct writer calls; unknown operations fail closed; recurring callback has no direct mark-paid call; cancel action changes no financial state.
- **Acceptance criteria:** names/syntax remain; exact mutation shown; no write before confirm; Batal does not write.
- **Residual risk:** Telegram staging is still needed to visually verify copy, button ordering, and real delivery/edit behavior.

## F-008 — `/test-sheets` security

- **Status:** Closed.
- **File:** `app/api/diagnostics.py`, `main.py`, `.env.example`, `.env.webhook.example`, setup docs.
- **Implementasi:** route default-disabled and hidden from OpenAPI. Opt-in requires separate `X-Admin-Secret`, performs a read-only connectivity open, and returns only generic status. It never calls schema ensure/repair or returns title, tabs, credentials, schema actions, or raw exception. `/health` remains cheap read-only liveness.
- **Test:** disabled default, missing secret stops before probe, authorized redacted result, unknown route policy.
- **Acceptance criteria:** anonymous HTTP cannot mutate schema or obtain metadata.
- **Residual risk:** actual FastAPI HTTP test requires the project runtime dependencies; policy was tested through its pure boundary without starting webhook mode.

## Test result

| Command | Result | Count / note |
| :--- | :--- | :--- |
| `python -m pytest -q tests` | Pass | 35 passed during pre-report run; final count recorded again in handoff verification |
| `python -m compileall -q app main.py tests` | Pass | all application/test modules compiled |
| Import smoke with external stubs | Pass | diagnostics, pending actions, command mutations, parser, operation errors, transaction, recurring, and Sheets client |
| `git diff --check` | Pass | no whitespace errors; Git emitted line-ending notices only |
| Lint/type check | Skip | no lint/type tool is configured in the repository |
| Real Telegram/Sheets/Gemini/webhook/scheduler | Skip | prohibited by scope; no production/staging credentials used |

`pytest` was installed into a temporary test-only directory because neither local interpreter nor bundled runtime provided it. Runtime dependency files were not modified; `requirements-dev.txt` declares the durable dev/test dependency.

## Protected contract

| Contract | Phase 0 result |
| :--- | :--- |
| Callback | New previews use opaque `action_id`; all legacy generic confirms fail safe |
| Confirmation flow | One final `Simpan / Batal` step added to audited direct-write commands |
| Route | `/test-sheets` default-disabled, authenticated opt-in, read-only/redacted |
| Command names | Unchanged |
| Command input syntax | Unchanged |
| Worksheet names | Unchanged |
| Google Sheets columns/schema | Unchanged |
| Business rules | Existing transaction/debt/split/recurring meanings retained |
| Deployment model | Single-user, single-process retained |

## Residual risk

- Google Sheets rollback is compensating/best-effort, not an ACID transaction.
- Ambiguous mutation without a stable logical ID fails unknown and needs manual reconciliation.
- Action store/inflight recurring claims are in-memory; restart invalidates previews and relies on recurring logs for completed run recovery.
- Single-process lock is not safe for future multi-process deployment.
- Real Telegram callback ordering, Sheets response semantics, and Google quota behavior were not exercised.
- Timezone unification, full observability, and structural handler refactor remain outside Phase 0.

## Manual staging verification plan

Run only after owner provides a staging bot and staging spreadsheet:

1. Create transaction previews A/B; confirm both in reverse order and compare exact payloads/rows.
2. Double-click one confirmation; verify one row and one balance delta.
3. Press legacy, canceled, expired, wrong-message, and post-restart callbacks; verify zero writes.
4. Trigger one recurring due date from reminder and `/recurring_run` close together; verify one transaction/log.
5. Inject a response failure after append; verify logical-ID lookup prevents a second row.
6. Fail balance/debt/log/relation steps; verify rollback or explicit reconciliation-required outcome.
7. Submit invalid dates across normal, debt, pending, and multiline input; verify clarification.
8. For every F-007 command, verify preview first, exact saved result after `Simpan`, and no write after `Batal`.
9. Verify production-default `/test-sheets` is hidden and cannot mutate; opt-in admin response remains redacted/read-only.

## Diff summary

### Source

- Action lifecycle: `app/bot/pending_actions.py`, keyboard/application/callback helpers.
- Mutation confirmation: `app/bot/command_mutations.py` and affected command handlers.
- Error/retry/data integrity: `operation_errors.py`, transaction/recurring/Sheets services.
- Parser/route safety: regex/parse-safety/message handler and diagnostics/main.

### Tests

- `tests/unit`: parser and action lifecycle.
- `tests/service`: transaction outcomes, atomic failures, recurring, retry.
- `tests/integration`: route security and command confirmation matrix.
- `tests/fakes`: Sheets, Telegram, clock, and import stubs.

### Config

- `.gitignore`: tests are tracked.
- `requirements-dev.txt`: pytest test dependency.
- `.env.example` and `.env.webhook.example`: default-off diagnostic settings.

### Documentation

- `README.md`, `docs/05-transaction-preview-flow.md`, `docs/08-setup-debug-deployment.md`, `docs/help_manual.md`, `docs/testing.md`, `docs/README.md`, and this report.

### Intentionally unchanged

- Google Sheets schema and worksheet names.
- Telegram command registry/names.
- Runtime dependency versions in `requirements.txt`.
- Database/persistence backend and deployment process model.
- Existing audit reports `00`–`11` remain historical evidence and are not rewritten.
