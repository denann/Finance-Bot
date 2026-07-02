# 05. Transaction Preview Flow

This project uses preview before write.

A normal transaction should follow this pattern:

```text
input
→ preview
→ save / edit / cancel
→ Google Sheets write
```

If the account is missing:

```text
input
→ preview
→ edit / continue / cancel
→ choose account
→ save / edit / cancel
```

This is the expected behavior after the latest patch. After choosing an account, the user should see `Simpan / Edit dulu / Batal`, not another unnecessary `Lanjut` step.

## Split bill

For paid split bills, the saved expense should use the user's net share. For unpaid split bills, the saved expense uses the gross paid amount and creates receivable records.

## Debt

Debt-related flows also go through preview so the user can confirm before the bot changes balances or debt records.
