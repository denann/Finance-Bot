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

`/add_kategori` and `/edit_kategori` use a guided wizard. The bot asks for the category name, type, symbol, and aliases. For new categories, Gemini generates alias candidates automatically. For edits, aliases can be typed manually, regenerated with `auto`, or kept with `sama`.

The category data is shown as a preview before the bot writes to the `categories` sheet.

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
