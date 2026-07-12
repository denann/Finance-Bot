# Technical Documentation

This directory contains the maintained product, architecture, operations, testing, and user documentation for Finance Bot. Start with [Documentation Source of Truth](documentation-source-of-truth.md) when changing behavior or documentation.

## Current Primary Documents

1. [Project Overview](01-project-overview.md)
2. [Architecture](02-architecture.md)
3. [Data Model](03-data-model.md)
4. [User Flows](04-user-flows.md)
5. [Safety and Confirmation](05-safety-and-confirmation.md)
6. [Google Sheets](06-google-sheets.md)
7. [AI and Gemini](07-ai-and-gemini.md)
8. [Configuration and Deployment](08-configuration-and-deployment.md)
9. [Public Surface Reference](09-function-reference.md)
10. [Maintenance](10-maintenance.md)
11. [Testing](testing.md)
12. [Operations Runbook](operations/runbook.md)
13. [User Manual Source](help_manual.md)

## Focused Supporting Documents

- [Phase 2 Boundary Map](architecture/phase-2-boundary-map.md)
- [Phase 3 Baseline](performance/phase-3-baseline.md)
- [Phase 3 Corrected Benchmark Results](performance/phase-3-benchmark-results.md)
- [Debug Matrix Coverage](testing/debug-matrix-coverage.md)
- [Documentation Inventory](documentation-inventory.md)

The older numbered pages such as `01-project-map.md` and `03-telegram-bot-flow.md` remain focused compatibility references while the primary documents above own the current end-to-end narrative.

## Historical Records

`docs/audit/` contains **historical audit and implementation records**. These files may describe pre-fix behavior and are not the current behavioral source of truth. Preserve their original evidence and use current passing tests, registries, implementation, and primary documents for present behavior.

The documentation is written for an international developer audience. Telegram commands, syntax, and user examples remain Indonesian because that is the product's current interaction contract.
