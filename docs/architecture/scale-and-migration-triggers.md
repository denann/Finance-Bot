# Scale and Migration Triggers

## Measurement Rule

Latency and reliability triggers require either three controlled staging runs with at least 30 samples per affected operation and the same dataset/configuration, or repeated production evidence during an owner-approved 14-day window with at least 100 samples. A single local run, isolated error, or row count alone does not trigger migration.

## GREEN - Current Architecture Remains Suitable

- One authorized user and one process remain the product requirement.
- One scheduler owner is sufficient.
- Non-AI interactive p95 is at most 3 seconds, report/search p95 at most 5 seconds, and AI completes within configured timeout in the measurement rule above.
- Reconciliation-required incidents are absent or isolated and operationally resolved.
- Quota/retry incidents do not recur across measurement windows.
- Full-read volume and memory stay inside the approved host budget with operational headroom.

## AMBER - Collect Evidence or Optimize Current Adapter

- Any provisional latency objective is exceeded in one controlled run/window but not recurrently.
- Row transfer approaches/exceeds the configured request budget for a required command.
- Full reads or exports consume material host memory, quota, or retry volume.
- Indexing, pagination, retention, or incremental summaries become desirable but current correctness remains acceptable.
- Reconciliation-required incidents recur twice in 30 days but have a known recovery path.
- Zero-downtime overlap or more scheduled workload is being considered, not yet required.

AMBER actions: collect telemetry, reduce retained/selected data, optimize the current adapter, test pagination/index alternatives, or prepare a migration proof of concept. Do not add tenants or migrate automatically.

## RED - Migration Design Must Begin Before Scope Expansion

### Product

- A second user, public onboarding, organization/team use, separate privacy boundary, per-user quota, or billing is approved.

### Process and Scheduler

- More than one application instance is required.
- Zero-downtime deployment requires overlapping active owners.
- One in-process scheduler owner cannot meet availability requirements.
- Recurring jobs require durable cross-process claim/lease semantics.

### Correctness

- Three or more reconciliation-required incidents occur in 30 days for ordinary expected workload, or any repeated incident cannot be safely recovered.
- Cross-worksheet mutation cannot meet owner-approved correctness requirements.
- Immutable IDs/idempotency cannot protect required concurrent writes.

### Performance and Query

- The same latency objective is exceeded in three controlled staging runs or the agreed production window.
- Quota/retry failures repeatedly prevent required operations after current-adapter optimization.
- Required queries need joins/indexes/pagination that cannot be delivered safely with the current schema/backend.
- Retention/export/deletion requirements exceed approved transfer/memory windows.

## Volume Policy

There is no universal row limit. The observed 50,000-row request budget is a guard and AMBER evidence, not proof that Google Sheets fails at that size. Decisions combine transfer, latency, memory, quota, frequency, retention, and correctness evidence.

## Review Events

Review this decision on any RED product/process trigger, after owner-executed staging, after a material quota/reconciliation incident, or by 2027-01-12 if the product remains active.
