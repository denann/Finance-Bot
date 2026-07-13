# Phase 0-5 Change Overview

## Purpose

Phase 0 through Phase 5 turned the Finance Telegram Bot from a working personal bot into a safer, better tested, and better documented single-user finance system. The work focused on data integrity, regression coverage, observability, module boundaries, Gemini governance, documentation ownership, and an evidence-based scale decision.

The overall result is a retained Google Sheets architecture with stronger confirmation, rollback, reconciliation, test, logging, and operational contracts. The phases did not redesign the product into a multi-user system, change worksheet schemas, or replace Google Sheets.

## Verified Current Snapshot

Verified snapshot: 2026-07-13.

Before this task, the latest verified baseline was a dated snapshot of 325 passing tests, documentation checks passed, compileall passed, and `git diff --check` passed. Final verification for the live-evaluation audit task is recorded in [Live AI Evaluation Audit and Baseline Report](../audit/2026-07-10/23-live-ai-evaluation-audit-and-baseline-report.md). Test totals are dated verification evidence, not permanent product facts.

## Phase 0 - Safety and Data Integrity

| Topic | Summary |
| :--- | :--- |
| Original problem | Several mutation paths could be ambiguous under stale callbacks, duplicate clicks, partial Sheets failures, invalid dates, direct-write commands, or recurring duplicate execution. |
| Main implementation | Added immutable one-shot action IDs, stale and duplicate callback protection, explicit rollback and reconciliation states, idempotent recurring run keys, invalid-date guards, and universal final confirmation where required. |
| User-visible effect | Users see safer previews and clearer failure states. State-changing actions require `Simpan` or `Batal` before final write where required. |
| Backend effect | Writes distinguish success, rollback, unknown outcome, and reconciliation-required states. Recurring execution uses existing logs for duplicate prevention in the single-process model. |
| Important code areas | `app/bot/pending_actions.py`, `app/bot/keyboards.py`, `app/bot/handler_parts/`, `app/services/transaction_service.py`, `app/services/recurring_service.py`, `app/sheets/client.py`. |
| Tests and evidence | Unit, service, integration, fake Sheets, fake Telegram, frozen clock, and failure-injection tests; see the historical [Phase 0 report](../audit/2026-07-10/12-phase-0-implementation-report.md). |
| Remaining limitations | Google Sheets is not ACID. Unknown write outcomes still require reconciliation. Pending actions remain in memory and reset on process restart. |

## Phase 1 - Regression Testing and Observability

| Topic | Summary |
| :--- | :--- |
| Original problem | The project needed deterministic regression coverage, offline guards, and sanitized observability before larger changes. |
| Main implementation | Added fixture-driven unit, service, integration, and regression tests; external-call guards; structured redacted logs; correlation IDs; readiness/liveness coverage; scheduler ownership tests; Gemini timeout and usage metadata logging. |
| User-visible effect | Fewer regressions in common transaction, debt, split-bill, cancellation, and confirmation flows. Operational errors are easier to correlate without exposing private finance text. |
| Backend effect | Default pytest cannot contact Telegram, Google Sheets, Gemini, HTTP clients, or arbitrary outbound services. Logs use opaque correlation IDs and redacted JSON metadata. |
| Important code areas | `tests/`, `tests/regression/fixtures/`, `tests/conftest.py`, `app/observability.py`, `app/api/`, `app/application/gemini_governance.py`, `evals/`. |
| Tests and evidence | Historical [Phase 1A report](../audit/2026-07-10/13-phase-1a-regression-and-eval-report.md) and [Phase 1B report](../audit/2026-07-10/14-phase-1b-observability-and-operational-safety-report.md). |
| Remaining limitations | Live Gemini quality and real provider latency require explicit opt-in evaluation with test credentials. |

## Phase 2 - Architecture and Parser Hardening

| Topic | Summary |
| :--- | :--- |
| Original problem | Handlers and parsing paths had legacy coupling, known regression gaps, and ambiguous multi-input behavior. |
| Main implementation | Added bounded callback/application modules, removed transaction/debt dependency cycles, hardened multi-input item-level clarification, consolidated utilities, and cleaned liability compatibility behavior. |
| User-visible effect | Mixed inputs preserve item order better, clarify only the item that needs help, and keep debt/split-bill behavior more predictable. |
| Backend effect | Application contracts became easier to test without Telegram. Legacy callback fallback behavior is contained and documented. |
| Important code areas | `app/application/`, `app/bot/handler_parts/`, `app/bot/callback_contracts.py`, `app/bot/command_registry.py`, `app/nlp/`, `tests/architecture/`. |
| Tests and evidence | Historical [Phase 2 report](../audit/2026-07-10/15-phase-2-domain-and-module-boundaries-report.md), follow-up callback audit, and known-gap resolution report. |
| Remaining limitations | Some old compatibility paths remain intentionally contained until owner-approved removal. |

## Phase 3 - Performance and Gemini Governance

| Topic | Summary |
| :--- | :--- |
| Original problem | Google Sheets reads, synchronous mutations, and Gemini calls needed bounded behavior and cost controls. |
| Main implementation | Added bounded workers, reconciliation-safe mutation behavior, server-side transaction sorting, request-scoped Sheets snapshots, row budgets, Gemini call budgets, bounded AI context, and one-call batch Gemini parsing for unresolved multi-input items. |
| User-visible effect | Multi-input and report flows are less likely to repeat expensive work. Gemini use is bounded and failures fall back or clarify instead of silently writing. |
| Backend effect | Text and multi-input updates have one primary Gemini call budget, image parsing has one normal call plus one compatibility retry for recognized invocation-format errors, and AI context is capped. |
| Important code areas | `app/application/external_io.py`, `app/application/gemini_governance.py`, `app/sheets/client.py`, `app/nlp/gemini_*`, `app/bot/handler_parts/transaction_flow.py`, `benchmarks/`. |
| Tests and evidence | Historical [Phase 3 report](../audit/2026-07-10/18-phase-3-performance-and-gemini-cost-report.md), correction report, and performance docs under `docs/performance/`. |
| Remaining limitations | Real network latency, quota behavior, and provider metadata still need staging evidence. |

## Phase 4 - Documentation and Operations

| Topic | Summary |
| :--- | :--- |
| Original problem | Documentation, help text, manual, architecture notes, and operational guidance needed alignment with the implementation after Phase 0-3. |
| Main implementation | Established a source-of-truth hierarchy, aligned command help/manual/README, updated architecture/schema/Sheets/Gemini/deployment documentation, added an operations runbook, documentation checker, and regenerated PDF manual. |
| User-visible effect | `/start`, `/help`, `/manual`, and documentation better match the current product behavior. |
| Backend effect | `scripts/check_docs.py` validates documentation drift offline, including command coverage, env parity, schema docs, links, historical-label policy, and privacy checks. |
| Important code areas | `docs/`, `scripts/check_docs.py`, `docs/help_manual.md`, `docs/help_manual.pdf`, help content under `app/bot/handler_parts/`. |
| Tests and evidence | Historical [Phase 4 report](../audit/2026-07-10/20-phase-4-documentation-alignment-report.md). |
| Remaining limitations | Real staging confirmation remains separate from documentation alignment. |

## Phase 5 - Scale and Persistence Decision

| Topic | Summary |
| :--- | :--- |
| Original problem | The project needed evidence before deciding whether to migrate away from Google Sheets or add tenant/database infrastructure. |
| Main implementation | Measured current scale behavior, documented migration triggers, accepted ADR-001, and retained the current one-user, one-process, one-spreadsheet architecture. |
| User-visible effect | No product migration occurred. Current workflows remain familiar and spreadsheet-visible. |
| Backend effect | Google Sheets remains the persistence layer. Future tenant and database migration are gated by explicit RED triggers and owner approval. |
| Important code areas | `docs/architecture/adr-001-scale-and-persistence.md`, `docs/architecture/scale-and-migration-triggers.md`, `docs/performance/phase-5-scale-evidence.md`, `tests/unit/test_phase5_*`. |
| Tests and evidence | Historical [Phase 5 report](../audit/2026-07-10/22-phase-5-scale-and-persistence-decision-report.md). |
| Remaining limitations | Second-user support, multi-instance scheduling, and database migration require a separate architecture decision. |

## Post-Phase 5 Operational Enhancement

Structured file logging was added after Phase 5 without changing the application log format:

| Setting | Behavior |
| :--- | :--- |
| `LOG_FILE` | Optional file path for structured JSON logs |
| Default path | `logs/finance_bot.log` |
| Disable behavior | Empty `LOG_FILE` disables file logging |
| Console behavior | Console logging remains enabled |
| File behavior | Events append as one JSON object per line |
| Git behavior | `logs/` is ignored by Git |
| Privacy expectation | Existing redaction boundary applies; prompts, credentials, raw finance text, receipt bytes, and private inputs must not be written to logs |

Canonical details live in [Configuration and Deployment](../08-configuration-and-deployment.md), [AI and Gemini](../07-ai-and-gemini.md), and `app/observability.py`.

## Current Architecture

```text
Telegram
-> routing and authorization
-> application use cases
-> domain/services
-> governed Sheets or Gemini boundary
-> response and structured observability
```

Financial mutations remain confirmation-gated and use reconciliation-aware synchronous boundaries where an offloaded or retried write could create an ambiguous outcome.

## User-Visible Changes

- Safer previews before writes.
- More consistent final confirmation.
- Better multi-input item-level clarification.
- Cancellation and future-intent handling.
- Debt, receivable, and split-bill routing corrections.
- Improved `/help`, `/manual`, and PDF manual.
- Clearer rollback, reconciliation, and unavailable-provider states.

## Backend Changes

- Broader deterministic test coverage.
- External-call guards for offline pytest.
- Bounded command, callback, and application module ownership.
- Write safety with immutable IDs, idempotency, rollback, and reconciliation states.
- Structured redacted logging with correlation IDs and optional file output.
- Bounded workers, request-scoped Sheets snapshots, row budgets, and Gemini call budgets.
- Documentation drift checks and operational runbook.
- Evidence-based decision to keep Google Sheets for current scope.

## Files and Code Areas

| Area | Main code paths | Main documentation | Main tests |
| :--- | :--- | :--- | :--- |
| Confirmation and actions | `app/bot/pending_actions.py`, `app/bot/keyboards.py`, `app/bot/handler_parts/callback_handler.py` | [Safety and Confirmation](../05-safety-and-confirmation.md) | `tests/unit`, `tests/integration`, `tests/regression` |
| Finance services and Sheets | `app/services/`, `app/sheets/client.py` | [Data Model](../03-data-model.md), [Google Sheets](../06-google-sheets.md) | `tests/service`, `tests/fakes` |
| Parsing and multi-input | `app/nlp/`, `app/bot/handler_parts/transaction_flow.py`, `app/application/bulk_input.py` | [User Flows](../04-user-flows.md), [AI and Gemini](../07-ai-and-gemini.md) | `tests/regression`, `tests/unit/test_batch_gemini_parser.py` |
| Gemini and AI answers | `app/application/gemini_governance.py`, `app/nlp/gemini_*`, `evals/` | [AI and Gemini](../07-ai-and-gemini.md), [Testing](../testing.md) | `tests/unit/test_gemini_*`, `tests/unit/test_eval_foundation.py` |
| Observability and runtime | `app/observability.py`, `main.py`, `app/api/`, `app/scheduler/` | [Configuration and Deployment](../08-configuration-and-deployment.md), [Operations Runbook](../operations/runbook.md) | `tests/integration`, `tests/unit/test_observability.py` |
| Documentation and maintenance | `docs/`, `scripts/check_docs.py`, `scripts/generate_help_manual_pdf.py` | [Documentation Source of Truth](../documentation-source-of-truth.md), [Maintenance](../10-maintenance.md) | `tests/unit/test_documentation_drift.py` |
| Scale decision | `benchmarks/`, `docs/architecture/`, `docs/performance/` | [ADR-001](../architecture/adr-001-scale-and-persistence.md), [Scale Triggers](../architecture/scale-and-migration-triggers.md) | `tests/unit/test_phase5_*` |

## Remaining Work

- Live AI evaluation baseline may still be `NOT_RUN` until explicit opt-in and valid test Gemini credentials are available.
- Dummy Telegram and Google Sheets staging is still required before production confidence.
- Real network latency, quota behavior, and provider metadata are not proven by offline tests.
- Second-user support requires explicit architecture review and tenant decision.
- Google Sheets remains intentionally retained for the current single-user, single-process product.

## Canonical Links

- Current architecture: [Architecture](../02-architecture.md)
- Data model: [Data Model](../03-data-model.md)
- Safety guide: [Safety and Confirmation](../05-safety-and-confirmation.md)
- Sheets guide: [Google Sheets](../06-google-sheets.md)
- Gemini guide: [AI and Gemini](../07-ai-and-gemini.md)
- Deployment guide: [Configuration and Deployment](../08-configuration-and-deployment.md)
- Testing guide: [Testing](../testing.md)
- Operations runbook: [Operations Runbook](../operations/runbook.md)
- ADR: [ADR-001 Scale and Persistence](../architecture/adr-001-scale-and-persistence.md)
- Migration triggers: [Scale and Migration Triggers](../architecture/scale-and-migration-triggers.md)
- Phase 0 historical evidence: [Phase 0 Implementation Report](../audit/2026-07-10/12-phase-0-implementation-report.md)
- Phase 1 historical evidence: [Phase 1A Regression and AI Evaluation Report](../audit/2026-07-10/13-phase-1a-regression-and-eval-report.md), [Phase 1B Observability and Operational Safety Report](../audit/2026-07-10/14-phase-1b-observability-and-operational-safety-report.md)
- Phase 2 historical evidence: [Phase 2 Domain and Module Boundaries Report](../audit/2026-07-10/15-phase-2-domain-and-module-boundaries-report.md)
- Phase 3 historical evidence: [Phase 3 Performance and Gemini Cost Report](../audit/2026-07-10/18-phase-3-performance-and-gemini-cost-report.md)
- Phase 4 historical evidence: [Phase 4 Documentation Alignment Report](../audit/2026-07-10/20-phase-4-documentation-alignment-report.md)
- Phase 5 historical evidence: [Phase 5 Scale and Persistence Decision Report](../audit/2026-07-10/22-phase-5-scale-and-persistence-decision-report.md)
