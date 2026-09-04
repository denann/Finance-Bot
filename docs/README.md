# Technical Documentation

This directory contains the maintained product, architecture, operations, testing, and user documentation for Finance Bot. Start with [Documentation Source of Truth](documentation-source-of-truth.md) when changing behavior or documentation.

## Current Primary Documents

1. [Input and Usage Guide](input-and-usage/README.md)
2. [Project Overview](01-project-overview.md)
3. [Architecture](02-architecture.md)
4. [Data Model](03-data-model.md)
5. [User Flows](04-user-flows.md)
6. [Safety and Confirmation](05-safety-and-confirmation.md)
7. [Google Sheets](06-google-sheets.md)
8. [AI and Gemini](07-ai-and-gemini.md)
9. [Configuration and Deployment](08-configuration-and-deployment.md)
10. [Public Surface Reference](09-function-reference.md)
11. [Maintenance](10-maintenance.md)
12. [Testing](testing.md)
13. [Operations Runbook](operations/runbook.md)
14. [User Manual Source](help_manual.md)

## Focused Supporting Documents

- [Historical Phase 0-5 Change Overview](phase-0-to-5/README.md)
- [Phase 2 Boundary Map](architecture/phase-2-boundary-map.md)
- [Benchmark Guide](../benchmarks/README.md)
- [Debug Matrix Coverage](testing/debug-matrix-coverage.md)
- [Documentation Inventory](documentation-inventory.md)
- [Phase 5 Current Scale Boundary](architecture/phase-5-current-scale-boundary.md)
- [Persistence Contract Assessment](architecture/persistence-contract-assessment.md)
- [Persistence Options](architecture/persistence-options.md)
- [Scale and Migration Triggers](architecture/scale-and-migration-triggers.md)
- [ADR-001 Scale and Persistence](architecture/adr-001-scale-and-persistence.md)
- [Future Migration and Tenant Plan](architecture/future-migration-and-tenant-plan.md)
- [Phase 5 Scale Staging](testing/phase-5-scale-staging.md)

The older numbered pages such as `01-project-map.md` and `03-telegram-bot-flow.md` remain focused compatibility references while the primary documents above own the current end-to-end narrative.

## Historical Records

The phase overview and dated pages under `docs/testing/` are historical audit and implementation records. They may describe an earlier repository state and
are not the source of truth for current behavior. Use current passing tests,
registries, implementation, and the primary documents above.

The documentation is written for an international developer audience. Telegram commands, syntax, and user examples remain Indonesian because that is the product's current interaction contract.
