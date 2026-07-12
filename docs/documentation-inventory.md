# Documentation Inventory

## Status Definitions

`CURRENT` is an actively maintained source of truth. `PARTIALLY_OBSOLETE` contains useful material that needs alignment. `HISTORICAL` records a dated state and is not current behavior. `GENERATED` is rebuilt from another declared source. `DUPLICATED` repeats a canonical source. `MISSING` is a required artifact that does not yet exist.

## Canonical Sources Identified

| Fact | Canonical implementation source | Documentation owner |
| :--- | :--- | :--- |
| Command names and runtime bindings | `app/bot/command_registry.py` | `app/bot/handler_parts/help_content.py`, user manual |
| Command visibility and compatibility status | Command registry plus `LIABILITY_UNAVAILABLE_COMMANDS`; metadata is incomplete | Phase 4 command metadata/check tooling |
| Callback ownership | `app/bot/handler_parts/callback_dispatcher.py`, `app/bot/callback_contracts.py`, bounded callback modules | Architecture and flow docs |
| Environment variables | `app/config.py` plus direct adapter `os.getenv` calls | `.env.example`, configuration guide |
| Worksheet names and columns | `app/config.py`, `app/sheets/client.py::SHEET_SCHEMAS` | Data-model and Sheets guides |
| Gemini configuration and governance | `app/config.py`, `app/application/gemini_governance.py`, Gemini adapters | AI/Gemini guide |
| Testing commands and guards | `tests/conftest.py`, pytest suites, eval scripts | `docs/testing.md` |
| Manual source and generated PDF | `docs/help_manual.md`, `scripts/generate_help_manual_pdf.py` | `/manual`, `docs/help_manual.pdf` |
| Architecture boundaries | Current modules and contract tests | Current architecture docs |
| Deployment invariants | `main.py`, API entry point, scheduler initialization, health/readiness tests | Deployment guide and runbook |

## Primary Documentation

| Path | Audience | Owner/source | Classification | Generated | Known drift | Recommended action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `README.md` | Users and contributors | Current implementation | PARTIALLY_OBSOLETE | No | Long, duplicates detailed guides, lacks Phase 3 operational boundaries | Restructure and link canonical guides |
| `docs/README.md` | Developers | Documentation set | PARTIALLY_OBSOLETE | No | Index omits architecture, performance, audit status, operations, and source ownership | Replace with complete current/historical index |
| `docs/01-project-map.md` | Developers | Repository layout | PARTIALLY_OBSOLETE | No | Predates current application boundaries | Align or supersede through the requested overview |
| `docs/02-runtime-entrypoint.md` | Operators/developers | Runtime implementation | PARTIALLY_OBSOLETE | No | Does not fully cover worker classes and scheduler ownership | Align or supersede through architecture docs |
| `docs/03-telegram-bot-flow.md` | Developers | Handlers and registries | PARTIALLY_OBSOLETE | No | Needs bounded handler and callback containment state | Align with tested routing |
| `docs/04-parser-nlp-parse-safety.md` | Developers | NLP and safety modules | PARTIALLY_OBSOLETE | No | Needs current Gemini call-budget boundary | Align with current contracts |
| `docs/05-transaction-preview-flow.md` | Developers | Application pending actions | PARTIALLY_OBSOLETE | No | Needs immutable action and reconciliation details | Align with tested flow |
| `docs/06-data-layer-services.md` | Developers | Services and Sheets client | PARTIALLY_OBSOLETE | No | Too brief for current repository/snapshot boundaries | Replace with data-model and Sheets guides |
| `docs/07-ai-insight-layer.md` | Developers | Gemini and insight code | PARTIALLY_OBSOLETE | No | Does not document Phase 3 governance | Replace with current AI/Gemini guide |
| `docs/08-setup-debug-deployment.md` | Operators | Config/runtime code | PARTIALLY_OBSOLETE | No | Incomplete environment and operational coverage | Replace with config/deployment guide and runbook |
| `docs/09-function-reference.md` | Developers | Manual function inventory | DUPLICATED | No | 137 KB unstable private-function dump | Replace with stable public surfaces; generate optional AST inventory |
| `docs/10-glossary.md` | Users/developers | Product terminology | CURRENT | No | Must be link-checked | Retain and link from index |
| `docs/testing.md` | Developers | Tests, guards, evals | PARTIALLY_OBSOLETE | No | No Phase 4 documentation gate | Add official drift-check command |
| `docs/help_manual.md` | Bot users | Command registry, help content, tested flows | PARTIALLY_OBSOLETE | No; canonical source | Must be aligned to current public commands | Update, then regenerate PDF |
| `docs/help_manual.pdf` | Bot users | `docs/help_manual.md` | GENERATED | Yes | Current 16-page output predates Phase 4 alignment | Regenerate and visually inspect every page |
| `docs/architecture/phase-2-boundary-map.md` | Developers | Phase 2 implementation | CURRENT | No | Phase 2 scope only; Phase 3 additions need current architecture guide | Retain as focused current reference |
| `docs/performance/phase-3-baseline.md` | Developers | Offline benchmark | CURRENT | No | Dated synthetic evidence | Retain and label scope |
| `docs/performance/phase-3-benchmark-results.md` | Developers | Corrected offline benchmark | CURRENT | No | Dated synthetic evidence only | Retain and link |
| `docs/testing/debug-matrix-coverage.md` | Test maintainers | Regression fixtures | CURRENT | No | Large generated-style evidence without declared generator | Retain and document owner |
| `docs/testing/regression-expansion-2026-07-11.md` | Test maintainers | Dated regression expansion | HISTORICAL | No | Snapshot, not permanent count | Label as dated evidence |
| `evals/README.md` | AI evaluators | Eval runner | CURRENT | No | None identified | Retain and link |

## Folder Ownership READMEs

| Path | Audience | Classification | Known drift | Recommended action |
| :--- | :--- | :--- | :--- | :--- |
| `app/README.md` | Developers | PARTIALLY_OBSOLETE | Omits `application/` ownership details | Align |
| `app/api/README.md` | Developers/operators | PARTIALLY_OBSOLETE | Verify health/readiness and diagnostic boundaries | Align |
| `app/bot/README.md` | Developers | PARTIALLY_OBSOLETE | Verify registry and bounded handler ownership | Align |
| `app/bot/handler_parts/README.md` | Developers | PARTIALLY_OBSOLETE | Needs dispatcher and legacy containment rules | Align |
| `app/nlp/README.md` | Developers | PARTIALLY_OBSOLETE | Needs Gemini governance dependency | Align |
| `app/scheduler/README.md` | Operators | PARTIALLY_OBSOLETE | Needs single-owner and capacity isolation | Align |
| `app/services/README.md` | Developers | PARTIALLY_OBSOLETE | Needs application/service dependency direction | Align |
| `app/sheets/README.md` | Developers | PARTIALLY_OBSOLETE | Needs snapshot, sort, retry, and reconciliation contracts | Align |
| `scripts/README.md` | Developers | CURRENT | `scripts/ai_command_tester.py` correctly labeled wrapper | Add docs/PDF check ownership |

## Historical Audit Records

All files below are dated evidence. Their last verified behavior is the phase or audit named by the file, and later passing tests/current code take precedence.

| Path | Classification | Recommended action |
| :--- | :--- | :--- |
| `docs/audit/2026-07-10/00-executive-summary.md` | HISTORICAL | Add directory-level historical notice |
| `docs/audit/2026-07-10/01-system-map.md` | HISTORICAL | Preserve evidence |
| `docs/audit/2026-07-10/02-findings-register.md` | HISTORICAL | Preserve finding history; link resolution reports |
| `docs/audit/2026-07-10/03-bug-edge-case-matrix.md` | HISTORICAL | Preserve dated matrix |
| `docs/audit/2026-07-10/04-performance-latency-gemini-cost.md` | HISTORICAL | Preserve pre-Phase 3 findings |
| `docs/audit/2026-07-10/05-testing-and-observability-gaps.md` | HISTORICAL | Preserve pre-fix gaps |
| `docs/audit/2026-07-10/06-ux-flow-audit.md` | HISTORICAL | Preserve dated UX findings |
| `docs/audit/2026-07-10/07-documentation-drift.md` | HISTORICAL | Use as Phase 4 input, not current behavior |
| `docs/audit/2026-07-10/08-configuration-deployment-risk.md` | HISTORICAL | Preserve pre-alignment risks |
| `docs/audit/2026-07-10/09-future-architecture-assessment.md` | HISTORICAL | Preserve recommendations |
| `docs/audit/2026-07-10/10-improvement-roadmap.md` | HISTORICAL | Preserve phase roadmap |
| `docs/audit/2026-07-10/11-verification-log.md` | HISTORICAL | Preserve dated verification |
| `docs/audit/2026-07-10/12-phase-0-implementation-report.md` | HISTORICAL | Preserve Phase 0 state |
| `docs/audit/2026-07-10/13-phase-1a-regression-and-eval-report.md` | HISTORICAL | Preserve Phase 1A state |
| `docs/audit/2026-07-10/14-phase-1b-observability-and-operational-safety-report.md` | HISTORICAL | Preserve Phase 1B state |
| `docs/audit/2026-07-10/15-phase-2-domain-and-module-boundaries-report.md` | HISTORICAL | Preserve Phase 2 state |
| `docs/audit/2026-07-10/16-phase-2-follow-up-legacy-callback-fallback-audit-and-containment-report.md` | HISTORICAL | Preserve containment evidence |
| `docs/audit/2026-07-10/17-regression-known-gap-resolution-report.md` | HISTORICAL | Preserve regression snapshot |
| `docs/audit/2026-07-10/18-phase-3-performance-and-gemini-cost-report.md` | HISTORICAL | Preserve original Phase 3 report |
| `docs/audit/2026-07-10/19-phase-3-correction-pass-report.md` | HISTORICAL | Preserve corrected Phase 3 evidence |

## Missing Phase 4 Artifacts

| Path | Classification | Canonical input | Action |
| :--- | :--- | :--- | :--- |
| `docs/documentation-source-of-truth.md` | MISSING | This inventory and implementation registries | Create in checkpoint 4.1 |
| `docs/01-project-overview.md` | MISSING | Current product and deployment contracts | Create without duplicating the project map |
| `docs/02-architecture.md` | MISSING | Current code and focused boundary maps | Create current architecture overview |
| `docs/03-data-model.md` | MISSING | `SHEET_SCHEMAS` | Create exact schema guide |
| `docs/04-user-flows.md` | MISSING | Current handlers/application services/tests | Create flow guide |
| `docs/05-safety-and-confirmation.md` | MISSING | Pending actions, rollback, reconciliation tests | Create safety guide |
| `docs/06-google-sheets.md` | MISSING | Sheets client and service contracts | Create Sheets guide |
| `docs/07-ai-and-gemini.md` | MISSING | Gemini governance and adapters | Create AI guide |
| `docs/08-configuration-and-deployment.md` | MISSING | Config/runtime/deployment entry points | Create configuration guide |
| `docs/10-maintenance.md` | MISSING | Test and documentation gates | Create maintenance guide |
| `docs/operations/runbook.md` | MISSING | Deployment and incident contracts | Create runbook |
| `scripts/check_docs.py` | MISSING | Canonical registries and docs | Create offline semantic drift checker |
| `docs/audit/2026-07-10/20-phase-4-documentation-alignment-report.md` | MISSING | Completed Phase 4 evidence | Create at final checkpoint |

## Inventory Conclusion

The repository has usable current documentation, but ownership is distributed and many core pages predate Phase 2-3 boundaries. Historical audit reports are preserved as evidence. The Phase 4 documents should become the current narrative layer while focused maps, benchmarks, and dated reports remain linked supporting records.

| Documentation update | Status |
| :--- | :--- |
| Markdown, README, PDF, and generated-source inventory | Completed |
| Canonical implementation sources | Identified |
| Current versus historical classification | Completed |
| Existing owner archive `New Update.zip` | Recorded and untouched |
