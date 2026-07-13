# Maintenance Guide

## Required Gates

```powershell
python -m pytest -q
python scripts/check_docs.py
python -m compileall -q app evals main.py tests scripts benchmarks
git diff --check
```

Run targeted tests first, then the full suite. Live external evaluation and staging are separate opt-in activities.

## Change Checklists

### New or Changed Command

- Update the canonical command registry and classification.
- Preserve authorization, correlation, preview, and callback ownership.
- Update modular help, manual, README overview, and tester coverage.
- Add semantic alignment tests; do not assert entire paragraphs.

### New or Changed Callback

- Assign one owner module and bounded prefix/exact value.
- Add stale, wrong owner/message/flow, double-click, cancel, and unknown-data tests.
- Update callback routing inventory.
- Do not broaden the legacy fallback.

### Environment Variable

- Add one canonical name and validation/default behavior.
- Update `.env.example` with a safe placeholder.
- Update configuration/deployment and operations guidance.
- Run the AST-based documentation checker.

### Worksheet Schema or Migration

- Stop for owner approval.
- Back up the spreadsheet and specify forward/rollback migration.
- Update `SHEET_SCHEMAS`, service row builders, fakes, data-model/Sheets docs, and tests together.
- Stage with dummy data before production. Never silently reinterpret an existing column.

### Prompt or Gemini Contract

- Preserve model, temperature, prompt meaning, and output schema unless explicitly approved.
- Increment the feature prompt version for intentional prompt changes.
- Update offline golden evaluation, privacy, call-budget, and malformed-output tests.
- Update `evals/cases/gemini_parser_cases.jsonl` only with synthetic data and keep `evals/run_parser_eval.py` default-disabled.
- Run comparison and `evals/gates.py` with fixture reports when changing live-eval metrics or thresholds.
- Do not hard-code prices or invent usage tokens.

## Release Checklist

1. Review worktree and owner changes.
2. Run all required gates.
3. Regenerate and visually inspect the manual PDF when its source changes.
4. Back up and complete dummy-Sheets staging.
5. Confirm one scheduler owner and readiness behavior.
6. Review logs for privacy and reconciliation signals.
7. Record a dated verification snapshot and residual risks.

## Documentation Policy

Current documents explain current tested behavior. Dated audit/implementation reports remain historical evidence and are not rewritten to appear current. Link later resolution reports instead of altering original findings. Avoid permanent test totals in current docs; counts belong in dated verification reports.

## Staging Checklist

Use the [Operations Runbook](operations/runbook.md). Verify Telegram responsiveness, transaction ordering, Sheets telemetry, snapshots, scheduler ownership, Gemini calls/usage, image compatibility, and redacted logs using dummy credentials only.

## Scale Decision Review

Review [ADR-001](architecture/adr-001-scale-and-persistence.md) on a documented RED trigger, after Phase 5 staging, after a material quota/reconciliation incident, or by its review date. A row count or local timing alone does not authorize migration. A second user requires an owner-approved tenant decision before onboarding.

| Maintenance area | Owner |
| :--- | :--- |
| Runtime behavior | Current implementation and contract tests |
| Command/callback metadata | Registries and routing contracts |
| Schema | `SHEET_SCHEMAS` plus approved migration |
| Manual | Markdown source plus generated/verified PDF |
| Historical evidence | Dated audit directory |
