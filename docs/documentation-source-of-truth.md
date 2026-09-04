# Documentation Source of Truth

## Hierarchy

Resolve conflicts in this order:

1. Passing automated contract and regression tests.
2. Current command, callback, configuration, and worksheet-schema registries.
3. Current implementation.
4. Current architecture and user-facing documentation.
5. Historical audit and implementation reports.

Documentation does not redefine finance behavior. If a current document conflicts with a tested contract, correct the document or stop for an owner decision when the product contract is genuinely ambiguous.

## Ownership Map

| Subject | Canonical source | Maintained documentation |
| :--- | :--- | :--- |
| Telegram command names and handlers | `app/bot/command_registry.py` | `help_content.py`, `docs/help_manual.md`, README overview |
| User input and command formats | Current handlers, parser contracts, and regression tests | `docs/input-and-usage/README.md`, in-bot help, and user manual |
| Command classifications | `COMMAND_CLASSIFICATIONS` and classification sets in the command registry | Help/manual labels and drift checks |
| Callback ownership | `app/bot/handler_parts/callback_dispatcher.py`, `app/bot/callback_contracts.py` | Architecture and user-flow guides |
| Environment variables | `app/config.py`; diagnostic policy accepts an injected environment mapping | `.env.example`, configuration guide |
| Worksheet names and columns | `app/config.py`, `app/sheets/client.py::SHEET_SCHEMAS` | Data-model and Sheets guides |
| Gemini limits and prompt versions | Config loader, `app/application/gemini_governance.py`, Gemini adapters | AI/Gemini guide |
| Test and external-call contracts | `tests/` and benchmark tests | Testing and maintenance guides |
| Manual content | `docs/help_manual.md` | Tracked delivery artifact `docs/help_manual.pdf` |
| Deployment invariants | `main.py`, API, scheduler, health/readiness implementation and tests | Configuration guide and runbook |
| Scale/persistence decision | Phase 5 observed benchmark, triggers, and ADR-001 | Architecture decision and staging package |

## Current, Generated, and Historical Files

- Current primary documents are listed in `docs/README.md`.
- Focused architecture and testing pages remain current within their stated scope.
- `docs/help_manual.pdf` is a delivery artifact and must never be edited directly.
- The Phase 0-5 overview and dated testing evidence are historical snapshots.
  Test totals in them are valid only for their recorded date and phase.
- The detailed artifact classification is maintained in `docs/documentation-inventory.md`.

## Safe Update Workflow

1. Read repository instructions and inspect the worktree.
2. Identify the tested registry or implementation source for every fact being changed.
3. Update the canonical source only when behavior is intentionally changing; documentation-only work must not alter runtime contracts.
4. Update the smallest set of current documents and use links instead of duplicating full command, schema, or configuration lists.
5. Run `python scripts/check_docs.py`.
6. Run the relevant tests and the full offline suite.
7. Regenerate and visually inspect the manual PDF when an approved generator is
   available; otherwise record that the tracked PDF was not refreshed.
8. Record dated verification without presenting the count as permanent.

## Manual and PDF

The canonical editable manual is `docs/help_manual.md`. The `/manual` handler
sends `docs/help_manual.pdf` and does not generate it at runtime. The active
repository does not contain a PDF-generation script, so a Markdown change does
not prove that the tracked PDF is current. Use an approved generator, render
every page, and inspect the output before replacing the PDF.

## Drift Checks

Run:

```powershell
python scripts/check_docs.py
```

Use `--inventory` to print command, environment, worksheet, and documentation-index inventories. The checker is offline and must not import credentials or contact Telegram, Sheets, Gemini, or HTTP services.

| Documentation update | Status |
| :--- | :--- |
| Ownership hierarchy | Defined |
| Manual source | Declared |
| Historical policy | Defined |
| Drift-check command | Defined |
