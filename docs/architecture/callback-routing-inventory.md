# Callback Routing Inventory

## Dispatch Order

`app/bot/handler_parts/callback_dispatcher.py` is canonical. It routes explicitly owned bounded callback families first, permits the audited legacy inventory second, and rejects unknown callback data.

| Owner | Contract source | Responsibility |
| :--- | :--- | :--- |
| Bulk flow | `bulk_flow.py::BULK_CALLBACK_PREFIXES` | Item clarification, rewrite/remove, payment state, final review/cancel |
| Bounded feature modules | Dispatcher imports and handler-specific predicates | Feature-owned callbacks introduced outside the legacy handler |
| Legacy compatibility | `app/bot/callback_contracts.py` | Exact/prefix inventory only; no arbitrary fallback |
| Unknown | Dispatcher rejection path | Answer callback and fail closed without finance mutation |

## Safety Invariants

- Finance confirmation uses opaque immutable action IDs where the flow has been migrated.
- Owner, preview message, expected flow, status, and expiry are checked before action consumption.
- The action is consumed before mutation, preventing double-click replay in the single-process model.
- Stale, canceled, consumed, expired, wrong-owner, wrong-message, wrong-flow, and unknown callbacks do not create a new write.
- Legacy routing is compatibility containment and must shrink, not broaden.

## Maintenance

Add a callback only with one owner, a bounded predicate/prefix, positive routing tests, unknown/stale tests, and an update to this inventory. Callback data changes are a protected contract and require explicit owner approval.

| Inventory status | Result |
| :--- | :--- |
| Unknown data | Fails closed |
| Legacy inventory | Explicit exact values/prefixes |
| Runtime behavior changed by this document | No |
