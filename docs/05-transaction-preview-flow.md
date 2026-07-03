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

## Debt

Debt-related flows also go through preview so the user can confirm before the bot changes balances or debt records.
