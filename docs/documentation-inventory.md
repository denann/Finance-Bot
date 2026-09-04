# Documentation Inventory

This inventory describes files present in the active repository. It deliberately
does not list removed audit, evaluation, CI, or manual-generation artifacts.

## Primary Documents

| Subject | Document | Implementation source |
| :--- | :--- | :--- |
| User input and commands | `docs/input-and-usage/README.md`, `docs/help_manual.md` | Command registry, help content, handlers, parser tests |
| Product overview | `README.md`, `docs/01-project-overview.md` | Current application behavior |
| Architecture | `docs/02-architecture.md` | `app/`, architecture tests |
| Data model and Sheets | `docs/03-data-model.md`, `docs/06-google-sheets.md` | `app/config.py`, `app/sheets/client.py` |
| User and confirmation flows | `docs/04-user-flows.md`, `docs/05-safety-and-confirmation.md` | Handlers, pending actions, services, flow tests |
| Gemini | `docs/07-ai-and-gemini.md` | Gemini adapters and governance code |
| Configuration and operations | `docs/08-configuration-and-deployment.md`, `docs/operations/runbook.md` | Configuration, `main.py`, API and scheduler code |
| Public code surface | `docs/09-function-reference.md` | Current registries and modules |
| Maintenance and testing | `docs/10-maintenance.md`, `docs/testing.md` | Test suite and `scripts/check_docs.py` |

## Folder READMEs

The active folder guides are:

- `app/README.md`
- `app/api/README.md`
- `app/application/README.md`
- `app/bot/README.md`
- `app/bot/handler_parts/README.md`
- `app/nlp/README.md`
- `app/scheduler/README.md`
- `app/scripts/README.md`
- `app/services/README.md`
- `app/sheets/README.md`
- `benchmarks/README.md`
- `scripts/README.md`
- `tests/README.md`

## Secondary and Historical Pages

Older numbered walkthrough pages remain secondary references. The Phase 0-5
README and dated pages under `docs/testing/` are historical snapshots. Current
tests, registries, implementation, and primary documents take precedence when
they differ.

`docs/help_manual.pdf` is a tracked delivery artifact for `/manual`.
`docs/help_manual.md` is the editable source, but the active repository does not
currently contain a PDF-generation script. Do not claim the PDF is synchronized
until it has been regenerated and visually verified with an approved toolchain.

## Maintenance Rule

When user-facing behavior changes, update the input guide, relevant in-bot help,
manual source, and affected folder README. Then run:

```powershell
python scripts/check_docs.py
python -m pytest -q
```
