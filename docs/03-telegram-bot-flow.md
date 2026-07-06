# 03. Telegram Bot Flow

The Telegram layer lives in `app/bot`.

## Main flow

```text
Telegram update
→ Application handler
→ command/message/callback handler
→ parser or service
→ reply to user
```

## Handler types

- Command handler: handles slash commands such as `/saldo`, `/quickstart`, `/set_saldo`, and `/ask`.
- Message handler: handles natural text input and image input.
- Callback handler: handles inline buttons such as save, edit, cancel, account choice, and split bill decisions.

## Category management flow

`/kategori` is read-only and lists existing categories, their type, symbol, and a short aliases preview.

`/add_kategori` and `/edit_kategori` use a guided wizard. The bot asks for the category name, type, symbol, and aliases. Type selection uses one row with two buttons: `Expense` and `Income`; the flow also includes a `Batal` button. For new categories, Gemini generates alias candidates automatically. For edits, aliases can be typed manually, regenerated with `auto`, or kept with `sama`.

The category data is shown as a preview before the bot writes to the `categories` sheet.

When `/edit_txn` changes a transaction category, the bot checks the typed value against existing category names and aliases. If the input maps to an existing category, for example `household` or `kebutuhan rumah` mapping to `Household & Supplies`, the bot asks whether to use that existing category or start a new category flow. This avoids silently creating redundant categories.

Bulk `/edit_txn` keeps the same safety rule. If several pasted edit rows contain category values that match existing categories through name, alias, or similarity, the bot stores a pending category decision queue and asks one row at a time:

```text
Baris 2: input kategori `household` cocok ke `Household & Supplies`.
-> Ikuti Household & Supplies / Tambah kategori baru / Batal
```

After every category decision is resolved, the bot shows the normal bulk edit preview with `Simpan` and `Batal`. Choosing `Tambah kategori baru` pauses the bulk queue and starts the category add wizard first; transaction rows are still not written until the final bulk preview is confirmed.

## Debt-only payable flow

`catat utang ke Budi 200k` creates a payable debt record without changing any account balance. This syntax is for cases where the user wants to acknowledge a liability, but no money entered the user's account at the time of logging.

```text
catat utang ke Budi 200k
-> parse as add_payable with cashflow_mode=debt_only
-> preview explains that saldo rekening will not change
-> save creates the debt row and a debt-only transaction audit row
```

This flow is intentionally separate from normal borrowing syntax such as `saya pinjam 100k ke Budi`, because normal borrowing means money entered an account and the bot must ask for the account.

## Reporting and chart flow

Daily, weekly, monthly, account, and transaction-list summaries use net expense as the primary expense basis. Gross expense remains available for display as `net (gross)` when receivable shares from split bill or talangan make the values different.

`/bulanan` sends three user-facing outputs:

1. Monthly summary.
2. Gemini monthly insight.
3. Monthly time series PNG chart document.

`/grafik` is a read-only chart command. Supported examples:

```text
/grafik
/grafik 2026-06
/grafik line 2026-06
/grafik bar 2026-06
/grafik pie 2026-06
```

The line chart shows daily net expense, the bar chart ranks category net expense, and the pie chart shows category share from total net expense. Chart files are generated as PNG documents.

## Important rule

Slash commands should never be parsed as transactions. If a message starts with `/`, it must go to command handling or unknown command handling, not to the expense parser.

## Receipt image flow

Itemized receipts use a separate review path because OCR can misread item names, quantities, or totals. After Gemini Vision extracts the receipt, the bot shows the parsed merchant, date, item rows, service, PPN, discount, and total check before asking whether all items or only part of the receipt should be recorded.

```text
photo/document image
→ Gemini image parser
→ OCR detail review
→ user chooses all items or selected parts
→ receipt rows become mixed/batch transaction items
→ detailed batch preview / edit / continue
→ choose account
→ compact final preview
→ save / edit / cancel
```

Service, PPN, and discount are shown separately in the detailed preview for transparency, but they are saved as one combined extra-charge transaction so the Google Sheets data stays clean. The final preview stays compact and focuses on totals, account impact, and category summary.
