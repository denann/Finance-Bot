# Architecture

## Request Direction

```text
Telegram update
-> authorization and correlation scope
-> command, message, or callback registry
-> atomic/bounded handler wrapper
-> application use case and typed result
-> finance/domain service
-> governed Sheets or Gemini boundary
-> Telegram response rendering
```

Dependencies point inward from Telegram adapters toward application contracts and finance services. Services do not own Telegram objects. `app/application/` contains extracted use cases, typed immutable results, bulk-input state, request-scoped finance snapshots, Gemini budgets, and bounded external-work policies.

## Routing

`app/bot/command_registry.py` is the canonical command binding registry. `callback_dispatcher.py` routes bounded callback families and fails closed for unknown data. The audited legacy callback handler is reachable only through prefixes and exact values in `callback_contracts.py`; it is compatibility containment, not an unrestricted fallback.

## Pending Actions

Preview builders create an opaque `action_id` bound to owner, flow, message, immutable payload, and expiration. Confirmation synchronously changes the action from pending to consumed before mutation. Reuse, wrong owner/message/flow, cancellation, expiration, or state lost after restart is rejected.

## Application Results and Dependency Direction

Application use cases return immutable results such as `ValidationFailure`, `ClarificationRequired`, `PreviewReady`, `MutationCommitted`, `OperationFailed`, and `ReconciliationRequired`. Transaction/debt orchestration lives in the application layer so transaction services do not need to import debt services in the wrong direction.

## External Work

Read-only Sheets work, Gemini work, and scheduled work have separate bounded worker classes. Correlation context propagates through `asyncio.to_thread`. A worker slot remains reserved until the real thread exits, even if the caller times out.

Not every external operation is non-blocking. Reconciliation-sensitive financial mutations remain synchronous where offloading plus timeout could create an unknown remote write outcome. A timeout does not cancel an already-running synchronous call.

## Sheets Read and Write Behavior

One logical request owns a request-scoped worksheet snapshot. The same worksheet is loaded once unless a successful mutation invalidates it. No cross-request finance cache is enabled. Transaction append uses server-side sorting over rows below the header; read paths still sort defensively when physical maintenance is delayed.

Sheets writes use logical IDs, operation-specific retry safety, rollback actions where possible, and explicit unknown-outcome states. These mechanisms improve safety but do not make Google Sheets a transactional database.

## Gemini Governance

One request-scoped budget is shared by parser, router, AI commands, multi-input, and image parsing. Text/multi-input permits at most one primary call. Image parsing normally uses one call and permits one additional attempt only for recognized invocation-format compatibility errors. Prompt versions, character counts, usage metadata when available, duration, outcome, and fallback metadata are logged without prompt content.

## Scheduler and Operations

`app/scheduler/jobs.py` owns recurring reminders and summaries. `app/operations.py` enforces one scheduler owner when enabled. `/health` proves the process responds; `/ready` reports generic configuration, Sheets, Telegram, scheduler, and startup readiness. Disabling the scheduler is explicit and visible.

## Compatibility References

- [Phase 2 Boundary Map](architecture/phase-2-boundary-map.md)
- [Callback Routing Inventory](architecture/callback-routing-inventory.md)
- [Benchmark Guide](../benchmarks/README.md)

| Architecture area | Current owner |
| :--- | :--- |
| Commands | Command registry and handlers |
| Callbacks | Dispatcher, bounded callback modules, audited legacy contracts |
| Application contracts | `app/application/` and pending actions |
| Finance rules | `app/services/` |
| Persistence | `app/sheets/client.py` |
| AI calls | Gemini governance and NLP adapters |
| Runtime ownership | `main.py`, operations state, scheduler |
