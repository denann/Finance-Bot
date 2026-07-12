# Public Surface Reference

This reference intentionally lists stable entry points and contracts instead of every private helper. Use AST or IDE navigation for implementation details.

## Runtime Entry Points

| Surface | Location | Contract |
| :--- | :--- | :--- |
| Application process | `main.py` | Select polling/webhook, validate config, initialize schema/Telegram/scheduler, expose health/readiness, shut down cleanly |
| Telegram application | `app/bot/application.py` | Register command/message/callback handlers and bind correlation, snapshot, Gemini budget, pending actions, and Sheets transaction scopes |
| Command registry | `app/bot/command_registry.py` | Canonical names, handlers, classifications, and unavailable compatibility commands |
| Callback dispatcher | `app/bot/handler_parts/callback_dispatcher.py` | Route owned callback families and fail closed for unknown data |
| Scheduler | `app/scheduler/jobs.py` | Create the single in-process scheduler and scheduled jobs |

## Application Use Cases and Results

| Surface | Location | Contract |
| :--- | :--- | :--- |
| Transaction/debt orchestration | `app/application/transaction_debt.py` | Coordinate cross-domain preview/commit without reversing service dependency direction |
| Bulk input | `app/application/bulk_input.py` | Stable item IDs, item-level clarification, ordered merge, immutable final batch |
| Typed results | `app/application/results.py` | Immutable validation, clarification, preview, commit, failure, and reconciliation outcomes |
| Pending actions | `app/bot/pending_actions.py` | Owner/message/flow-bound one-shot preview actions |
| Finance snapshot | `app/application/finance_snapshot.py` | Lazy request-local worksheet records; no cross-request cache |
| External work | `app/application/external_io.py` | Bounded interactive Sheets, Gemini, and scheduled workers with typed timeout/saturation |
| Gemini budget | `app/application/gemini_governance.py` | One shared request budget and stable prompt versions |

## Service Contracts

| Service family | Location | Responsibility |
| :--- | :--- | :--- |
| Transactions/accounts | `app/services/transaction_service.py` | Ledger rows, balances, ordering, edit/delete dependencies, reconciliation results |
| Debt/receivable | `app/services/debt_service.py` | Direction, principal, payments, settlement, linked records |
| Reports | `app/services/report_service.py` | Deterministic period filters, totals, search, and ordering |
| Finance insight context | `app/services/finance_insight_service.py` | Local aggregates, relevance selection, bounded context metadata |
| Budget/category/pending/recurring/assets | Corresponding modules in `app/services/` | Feature-specific validation and persistence ownership |
| Privacy | `app/services/privacy_service.py` | User notice and AI-context sanitization |

## Sheets Boundary

`app/sheets/client.py` owns `SHEET_SCHEMAS`, credential/client initialization, retry policy, logical-ID reconciliation, rollback registration, request snapshots, row budgets, and server-side sort. Services may call this boundary; Telegram handlers must not bypass confirmation by writing directly.

## Gemini Boundary

`app/nlp/gemini_langchain_client.py` is the governed provider invocation surface. Feature adapters supply model, prompt version, schema, and deterministic fallback behavior. The client enforces input/output limits, request budget, usage capture, compatibility retry classification, and redacted events.

## Configuration

| Surface | Location | Use |
| :--- | :--- | :--- |
| Central loader | `app/config.py` | Validated runtime values and worksheet names |
| Safe example | `.env.example` | Placeholder configuration with no real secrets |
| Runtime policy | `app/operations.py` | Single-instance scheduler rule and readiness state |

## CLI and Offline Tools

| Command | Purpose |
| :--- | :--- |
| `python scripts/setup_check.py` | Local setup validation |
| `python scripts/debug_check.py` | Deeper diagnostics |
| `python scripts/ai_command_tester.py` | Compatibility wrapper for canonical tester in `app/scripts/` |
| `python scripts/check_docs.py` | Offline documentation drift gate |
| `python scripts/generate_help_manual_pdf.py` | Generate PDF from manual Markdown |
| `python -m benchmarks.phase3_synthetic --mode optimized --sizes 100 1000 10000` | Offline synthetic performance profile |
| `python -m evals.run_live_eval` | Live opt-in AI evaluation only when explicitly enabled |

## Change Rules

New commands update the canonical registry, help/manual coverage, tester, and drift checks. New callbacks require an owner prefix and contract tests. New worksheet columns require owner approval and migration. New environment variables update config/direct reads, `.env.example`, configuration docs, and checks.

| Reference change | Result |
| :--- | :--- |
| Private function dump | Removed |
| Stable public/application/service surfaces | Documented |
| Invalid duplicated application paths | Removed |
