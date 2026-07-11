# 05. Transaction Preview Flow

This project uses preview before write.

A normal transaction should follow this pattern:

```text
input
→ preview
→ save / edit / cancel
→ Google Sheets write
```

If a normal text transaction is missing an account, the bot skips the redundant preview step and asks for the account directly:

```text
input
→ choose account
→ final preview
→ save / edit / cancel
```

After choosing an account, the user should see the final full preview with `Simpan / Edit dulu / Batal`, not another unnecessary `Lanjut` step.

## Receipt images

Receipt images are more sensitive than normal text input because the OCR result can be long and imperfect. The bot therefore shows the extracted receipt detail first, including item rows, quantity, unit price, service, PPN, discount, and total check.

```text
photo receipt
→ OCR detail review
→ all items or partial items
→ detailed batch preview / edit / continue
→ choose account
→ compact final batch preview
→ save / edit / cancel
```

When the user chooses all items, each receipt item becomes one batch transaction. Service, PPN, discount, and other extra charges are displayed as separate lines in the detailed preview, but saved as one combined extra-charge transaction.

When the user chooses only part of the receipt, the bot asks which item rows belong to the user, then asks how many people should split the extra charges. The selected rows and the combined extra charge are shown in a detailed batch preview before the account step, then saved as a batch after final confirmation.

Long receipt and multi-input previews are split into multiple Telegram messages when needed. The action buttons are attached to the last message chunk so the user can review the details first.

## Split bill

For paid split bills, the saved expense should use the user's net share. For unpaid split bills, the saved expense uses the gross paid amount and creates receivable records. Split bill inputs use the same multi-step review pattern as other multi inputs: detailed preview first, account selection second, compact final summary last.

If the user edits a single split bill preview after choosing paid/unpaid status, the bot returns to the detailed split bill preview instead of jumping directly to the account picker. The user can review the updated split values, then continue to the account picker. After the account is selected, the final confirmation stays compact and shows split-specific totals such as total paid, user's share, active receivable, category summary, and account impact.

## Debt

Debt-related flows also go through preview so the user can confirm before the bot changes balances or debt records.

## Immutable confirmation actions

Every final financial preview now creates a short-lived in-memory `action_id`. The action stores an immutable copy of the payload shown to the user, the owner user ID, the preview message ID when available, creation/expiry time, and terminal status.

```text
validated input
→ immutable action snapshot
→ final preview with confirm:<action_id> / cancel:<action_id>
→ owner, message, TTL, and one-shot validation
→ write
```

Creating preview B does not change preview A. Pressing A either writes A exactly once or fails safely when it is stale, expired, already used, canceled, owned by another user, or lost after restart. Legacy generic transaction callbacks are rejected and never fall back to the latest mutable pending state.

The action store intentionally remains in memory for the approved single-process deployment. A restart invalidates outstanding previews; it does not restore or execute them.

## Commands that add a confirmation step

The command names and syntax are unchanged, but these mutations now show one final `Simpan / Batal` preview before writing:

- `/pending_paid` and `/pending_cancel`;
- `/recurring_run`, `/recurring_edit`, and `/recurring_off`;
- the recurring reminder `Sudah bayar` button;
- `/asset_update`, `/asset_off`, and `/networth_snapshot`.

The snapshot preview freezes the totals that will be written. Canceling or using an expired/duplicate action does not call a financial write service.
