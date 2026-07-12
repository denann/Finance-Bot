# User Flows

## Shared Mutation Lifecycle

Most state-changing flows follow this contract:

```text
input -> deterministic parsing/safety routing -> clarification when required
-> preview -> immutable pending action -> confirm/edit/cancel
-> mutation -> success or reconciliation-required state
```

No shared diagram overrides a flow-specific exception below.

## Flow Matrix

| Flow | Parsing and clarification | Preview and mutation | Important exception |
| :--- | :--- | :--- | :--- |
| Single transaction | Local parser, safety checks, Gemini fallback only within budget; missing account/category is resolved | Exact transaction preview, then confirmed ledger/account mutation | No valid explicit account means account selection; no silent save |
| Missing account | Ask owner to select/create or use historical no-balance option where offered | Updated preview reflects selected account before save | Historical skip does not update balance |
| Multi-input | Parse all items, retain successful items, clarify unresolved items by stable item ID | Final combined preview, then one confirmed batch operation | One bad item does not discard the whole batch; no pre-confirmation batch write |
| Transfer | Detect transfer intent and both accounts | Preview source, destination, amount, date; update both balances and ledger | Never classify as ordinary expense/income |
| Debt creation | Route debt/receivable direction, person, amount, cashflow mode | Debt-specific preview and linked records where required | Direction and fronting mode are not inferred when ambiguous |
| Debt payment | Resolve debt ID/person and payment amount | Preview remaining amount and cashflow effect | Overpayment/settlement choices require explicit handling |
| Partial debt payment | Validate amount below remaining balance | Preview new remaining amount and linked payment | Debt remains active |
| Split bill | Resolve participants/shares and who paid | Preview net owner expense plus receivable/debt records | Gross and net reporting remain distinct |
| Pending expense | Parse future intent and due precision | Preview pending row; no transaction/balance mutation yet | `/pending_paid` later creates the transaction after confirmation |
| Budget mutation | Resolve month, category, amount | Preview create/update | Actual spending remains calculated from transactions |
| Recurring mutation | Parse rule/frequency/date fields | Preview add/edit/off/run action | Reminder is not payment; rule ID plus run date prevents repeat execution |
| Asset mutation | Resolve asset mode and valuation fields | Preview add/update/off | Asset deactivation preserves history |
| Editing | Select transaction by ID/list reference and validate dependencies | Preview before/after values | Linked debt/split effects follow guarded dependency rules |
| Deletion | Select exact transaction and inspect dependencies | Warning preview before delete | Failure can require reconciliation; linked records are not silently orphaned |
| Image receipt | Validate image, parse once normally, clarify ownership/items/account | Itemized preview then final preview | Second Gemini call only for recognized invocation-format compatibility |
| AI commands | Build deterministic aggregates and bounded relevant context | Read-only Gemini response or deterministic fallback | No finance write and at most one generation call |
| Export | Select supported dataset and prepare CSV | Read-only warning then Telegram document | Export contains sensitive personal finance data |

## Callback Compatibility

New bounded callback families are handled by their owner module. Audited legacy prefixes remain routed through the contained legacy handler. Unknown callback data fails closed. A compatibility route does not bypass action identity, preview, or confirmation requirements.

## Cancellation

Buttons labeled `Batal` cancel the active wizard or immutable action where cancellation is possible. `/cancel` and `/batal` remain command aliases. Cancellation never means a remote write was reversed; when a mutation has already started, the resulting commit/rollback/reconciliation state is authoritative.

## Read-Only Flows

Balances, reports, charts, search, history, health, privacy, help, manual, AI answers, and export preparation do not intentionally mutate finance data. Report order is deterministic even if physical transaction sorting maintenance is delayed.
