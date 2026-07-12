# Phase 4 Documentation Alignment Report

## Executive Summary

Phase 4 establishes a tested documentation source hierarchy, separates current guides from historical audit evidence, aligns user onboarding and the manual with the command registry, documents current application/Sheets/Gemini boundaries, synchronizes 34 environment variables, adds an operational runbook, replaces an unstable private-function dump, adds an offline semantic drift gate, and regenerates the manual PDF.

The verified baseline was 314 passing tests. On 2026-07-12 the final suite collected and passed 317 tests. No Telegram, Google Sheets, Gemini, HTTP, staging, or production service was called.

## Inventory Resolution

The detailed artifact-by-artifact baseline classification remains in `docs/documentation-inventory.md`. Every inventory entry resolves as follows.

| Inventory item(s) | Previous status | Final status | Action and canonical source | Residual risk |
| :--- | :--- | :--- | :--- | :--- |
| `README.md` | PARTIALLY_OBSOLETE | CURRENT | Linked current guides, application layer, and docs gate; implementation/tests remain canonical | Hosted setup needs real staging |
| `docs/README.md` | PARTIALLY_OBSOLETE | CURRENT | Rebuilt current/focused/historical index | Index must be maintained by checker |
| `docs/01-project-map.md` through `08-setup-debug-deployment.md` | PARTIALLY_OBSOLETE | COMPATIBILITY | Preserved as focused older pages; new current guides own end-to-end narrative | Focused prose can still age |
| `docs/09-function-reference.md` | DUPLICATED | CURRENT | Replaced 137 KB private dump with stable public surfaces | Optional full inventory requires AST/IDE |
| `docs/10-glossary.md` | CURRENT | CURRENT | Preserved and indexed | Link/content review remains manual |
| `docs/testing.md` | PARTIALLY_OBSOLETE | CURRENT | Added official docs gate and dated count policy | CI wiring remains repository-owner choice |
| `docs/help_manual.md` | PARTIALLY_OBSOLETE | CURRENT | Aligned onboarding, accounts, confirmations, safety, fictional examples | User prose requires review when behavior changes |
| `docs/help_manual.pdf` | GENERATED | GENERATED/CURRENT | Regenerated from Markdown and visually verified | TOC links are printed, not clickable |
| `docs/architecture/phase-2-boundary-map.md` | CURRENT | CURRENT/FOCUSED | Preserved and linked | Phase-specific scope |
| `docs/performance/phase-3-baseline.md` and benchmark results | CURRENT | HISTORICAL EVIDENCE | Preserved as labeled offline synthetic evidence | Not production latency |
| Debug-matrix and dated regression expansion docs | CURRENT/HISTORICAL | CURRENT EVIDENCE/HISTORICAL | Indexed and test totals labeled as snapshots | Large coverage file remains manually owned |
| `evals/README.md` | CURRENT | CURRENT | Added ownership and opt-in boundary | Live provider evidence remains external |
| Existing `app/`, API, bot, handler, NLP, scheduler, services, Sheets, and scripts READMEs | PARTIALLY_OBSOLETE/CURRENT | CURRENT | Added dependency direction, public ownership, invariants, tests, exclusions | Module growth requires maintenance |
| New application/scripts/tests/benchmarks READMEs | MISSING | CURRENT | Added folder ownership contracts | None identified offline |
| Audit files `00` through `19` | HISTORICAL | HISTORICAL | Preserved original evidence; directory labeled non-authoritative | Old findings remain searchable without per-file banner |
| Documentation inventory/source guide | MISSING | CURRENT | Added canonical ownership and update workflow | Checker policy must evolve with sources |
| Current overview/architecture/data/user/safety guides | MISSING | CURRENT | Added from tests, registries, and implementation | Real staging facts remain unverified |
| Sheets/Gemini/config guides and runbook | MISSING | CURRENT | Added exact contracts, retry matrix, env table, incidents | Provider/platform behavior can drift |
| Maintenance guide and callback inventory | MISSING | CURRENT | Added change gates and bounded callback ownership | Legacy inventory must not broaden |
| `scripts/check_docs.py` and tests | MISSING | CURRENT | Added offline AST/semantic gate | Semantic examples still need human review |
| Phase 4 progress/final reports | MISSING | HISTORICAL | Added dated implementation evidence | Counts are valid only for this verification date |

## Current Versus Historical Documents

### Current Sources of Truth

`README.md`, `docs/README.md`, `docs/documentation-source-of-truth.md`, current numbered Phase 4 guides, `docs/testing.md`, folder READMEs, command/callback registries, `.env.example`, and current implementation/tests.

### Generated Documents

`docs/help_manual.pdf` is generated from `docs/help_manual.md` by `scripts/generate_help_manual_pdf.py`.

### Historical Documents

All `docs/audit/` reports, dated regression expansion records, and Phase 3 benchmark evidence are dated snapshots. They do not override current tests or registries.

### Compatibility Documents

The older project-map/runtime/Telegram/parser/preview/data/AI/setup pages remain focused references. Liability commands are deprecated compatibility responses and are not registered public finance features.

## Command Alignment

| Metric | Result |
| :--- | :--- |
| Registered public command names/aliases | 65 |
| Documented public command names/aliases | 65 |
| Hidden/internal commands advertised | 0 |
| Compatibility/deprecated commands | 4: liability family |
| Missing public commands | 0 |
| Orphan help/manual commands | 0 |

The canonical tester imports `PUBLIC_COMMANDS`; it does not maintain a conflicting command registry. Phase 4 changed `/start` copy only, which is explicitly allowed, and did not add/remove/rename a command or change syntax.

## Configuration Alignment

| Metric | Result |
| :--- | :--- |
| Supported variables found by AST | 34 |
| Variables in `.env.example` | 34 |
| Variables documented | 34 |
| Missing/extra variables | 0 / 0 |
| Obsolete variables removed | None required |
| Secret verification | No token/private-key patterns found; placeholders only |

`APP_PORT`, `WEBHOOK_URL`, and `TELEGRAM_WEBHOOK_SECRET` were added to the example. Direct diagnostic variables are included in AST inventory. No runtime-supported variable was removed.

## Schema Alignment

| Metric | Result |
| :--- | :--- |
| Worksheet names checked | 12 |
| Columns checked | 115 |
| Documentation mismatches after alignment | 0 |
| Schema changes performed | None |

`SHEET_SCHEMAS` remains canonical. The data-model guide documents purpose, identifiers, columns, relations/invariants, mutation ownership, idempotency, and migration policy.

## Architecture, Sheets, and Gemini Alignment

The current architecture documents command/callback registries, bounded compatibility fallback, immutable action lifecycle, typed application outcomes, transaction/debt dependency direction, request snapshots, worker classes, server-side sort, Gemini governance, scheduler ownership, and health versus readiness.

Sheets documentation explicitly states that rollback is compensating rather than ACID, mutations are not blindly retried, a timeout does not prove a synchronous write stopped, and reconciliation may be required. Gemini documentation records current models by environment name, prompt versions, deterministic-first preparation, one-call text/multi budgets, classified image compatibility retry, 40-record context cap, 100,000-character input cap, usage availability, metrics, privacy, and default-disabled live evaluation.

## Documentation Checks

| Check | Result |
| :--- | :--- |
| Internal Markdown links | Passed |
| Indexed repository paths | Passed |
| Primary document index coverage | Passed |
| Duplicate headings | Passed |
| Duplicated invalid application paths in current docs | Passed |
| Public command coverage | Passed |
| Orphan documented commands | Passed |
| Hidden/internal advertising | Passed |
| Compatibility labeling | Passed |
| `.env.example` parity | Passed |
| Worksheet names and columns | Passed |
| Gemini setting documentation | Passed |
| Historical/current test-count policy | Passed |
| Generated PDF source declaration | Passed |
| Major docs index | Passed |
| Historical audit notice | Passed |
| Credential pattern scan | Passed |
| Fictional example notice | Passed |

Three unit tests enforce the full gate and canonical inventory counts.

## PDF Verification

| Item | Result |
| :--- | :--- |
| Canonical source | `docs/help_manual.md` |
| Generation command | `python scripts/generate_help_manual_pdf.py` |
| Output | `docs/help_manual.pdf` |
| Format/page count | A4, 17 pages |
| Text/nonblank check | All 17 pages contain extracted text |
| Visual QA | Every rendered page inspected; no clipping, overlap, broken glyph, duplicate page, or blank trailing page |
| Known limitation | Lightweight renderer prints Markdown TOC anchors; it does not create clickable internal PDF links |

The generator now uses fixed A4 pages and stable page-number footers.

## Docstrings and Comments

The new documentation checker has a contract docstring and focused function docstrings for AST extraction and schema loading. The PDF generator documents stable page finalization. Existing external-I/O rationale comments already explain why a timed-out worker retains its slot. No syntax-narration comments or broad production docstring churn was added.

## Protected Contracts

| Contract | Phase 4 result |
| :--- | :--- |
| Command names and syntax | Unchanged |
| Callback data/routing/ownership | Unchanged |
| Sheets names/columns | Unchanged |
| Finance/parser/debt/split/pending/recurring/budget/asset rules | Unchanged |
| Preview/action identity/confirmation | Unchanged |
| Idempotency/rollback/reconciliation | Unchanged |
| Gemini model, prompt meaning, output schema, budgets | Unchanged |
| Snapshot, concurrency, retry, transaction ordering | Unchanged |
| Scheduler ownership and health/readiness | Unchanged |

Only documentation metadata, user-facing `/start` prose, safe config examples, documentation tooling/tests, and PDF generation/layout changed.

## Verification

| Command group | Result |
| :--- | :--- |
| Baseline `python -m pytest -q` | 314 passed |
| Final `python -m pytest -q` | 317 passed |
| Unit / service / integration / regression | 77 / 29 / 38 / 164 passed |
| Collection | 317 tests |
| Failed / skipped / xfailed / xpassed | 0 / 0 / 0 / 0 |
| `python scripts/check_docs.py --inventory` | Passed |
| PDF generation | Passed |
| `compileall` | Passed |
| `git diff --check` | Passed |
| External services | Not called |

Pytest emitted the existing non-fatal Windows cache warning because `.pytest_cache` could not be created.

## Residual Risks

- Dummy-data staging is still required for Telegram delivery, gspread quota/latency/sort behavior, Gemini timeout/usage metadata, Wispbyte process ownership, and staging SLOs.
- Provider model availability and hosting behavior can change outside repository documentation.
- The PDF has no clickable internal TOC links.
- Historical reports intentionally retain obsolete findings and paths as evidence; the directory notice prevents them from becoming current authority.
- Older focused numbered pages remain compatibility references and may need removal in a later owner-approved cleanup.
- A modification marker without content diff appeared on the Phase 2 callback report during final status inspection; it was not changed or reverted by Phase 4.

## Recommended Next Step

Proceed to **Phase 5 - Evidence-Based Scale and Persistence Decisions** after owner review and completion of the dummy-data staging checklist in `docs/operations/runbook.md`.

| Documentation update | Status |
| :--- | :--- |
| Sources of truth and inventory | Completed |
| User/developer/operations alignment | Completed |
| Automated drift gate | Passing |
| PDF regeneration and visual QA | Completed |
| Commit/push | Not performed |
