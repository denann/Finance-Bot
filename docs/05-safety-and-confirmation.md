# Safety and Confirmation

## Preview Contract

A mutation preview must show the values that will be used: flow type, amount, accounts, category, person/subject, description, date, and warnings relevant to that flow. Clarification happens before final preview. Bulk items retain stable identities while individual questions are resolved.

## Immutable One-Shot Actions

Each final preview is copied into an in-memory action with an opaque `action_id`, owner ID, flow type, preview message ID, creation/expiry timestamps, and pending status. Confirm consumes it before mutation. Double-clicks, stale buttons, wrong users/messages/flows, canceled actions, expired actions, and actions lost after restart are rejected without a new write.

## Future and Pending Intent

Future wording must not be forced into a current expense. Pending expenses are stored separately and do not change account balances. Marking pending as paid is a second confirmed flow that creates the real transaction and records its ID.

## Batch Safety

Multi-input processing preserves valid items while clarifying others. No financial batch write occurs before the final combined preview. Removing or rewriting one item targets its stable item ID and cannot silently reorder the remaining items.

## Idempotency and Retry

Immutable transaction IDs and operation-specific reconciliation callbacks are used to detect a write that may have succeeded before an error response. Non-idempotent appends and balance updates are not blindly retried. Recurring execution uses rule ID plus scheduled date as a logical idempotency key.

## Rollback and Reconciliation

The Sheets transaction helper records compensating rollback actions for supported writes. A failure after a write attempts rollback in reverse order. Outcomes are explicit:

- mutation committed;
- commit failed and rollback succeeded;
- known failure before mutation;
- commit outcome unknown or rollback failed, requiring reconciliation.

Google Sheets does not provide a cross-worksheet ACID transaction. Therefore the bot never claims all operations are fully atomic.

## Timeout Ambiguity

Canceling or timing out an await does not stop an already-running synchronous thread or prove a remote mutation stopped. Read-only work can return a bounded timeout. Reconciliation-sensitive mutations remain synchronous on covered paths until they can be offloaded without misreporting success/cancellation or retrying a possible committed write.

## Reconciliation Procedure

1. Do not repeat the command immediately.
2. Record the correlation ID and candidate transaction IDs shown by safe diagnostics.
3. Inspect the relevant dummy/owner worksheet rows and account balances.
4. Determine whether append and dependent updates committed.
5. Repair only through an approved edit/delete/settlement flow or an owner-reviewed manual correction.
6. Re-run reports and confirm balances before resuming automation.

## Privacy

Structured logs omit raw input, finance text, prompts, credentials, receipt bytes, personal names, account names, descriptions, and transaction IDs as metric labels. Correlation IDs are opaque operational identifiers. CSV exports and Telegram messages still contain owner-visible finance data and must be handled as sensitive.

| Safety claim | Precise boundary |
| :--- | :--- |
| Preview before finance write | Required for user-driven mutations |
| Callback protection | In-memory, one-shot, owner/message/flow bound |
| Atomicity | Compensating rollback where supported, not database ACID |
| Retry | Operation-specific; no blind retry for ambiguous writes |
| Restart | Pending action state is lost and old buttons fail closed |
