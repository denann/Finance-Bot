# 05. Transaction & Preview Flow

The preview flow protects the user from wrong parser output.

A finance bot should not save sensitive data immediately just because the parser guessed something. This project uses preview, edit, warning, clarification, and confirmation steps before writing to Google Sheets.

## Main files

```text
app/bot/handler_parts/message_handlers.py
app/bot/handler_parts/transaction_flow.py
app/bot/handler_parts/callback_handler.py
```

## Normal text flow

```text
message_handler()
→ split input if needed
→ parse each item
→ assess parse safety
→ show preview or clarification
→ user chooses action
→ callback_handler()
→ service layer saves data
```

## Preview actions

Common actions:

| Button | Meaning |
|---|---|
| `Edit dulu` | User wants to correct the parsed result first |
| `Lanjut` | User accepts the preview and continues |
| `Simpan` | User confirms the final save |
| `Batal` | User cancels the flow |

## Warning preview

Warning preview appears when the parser result may be correct but still risky.

Example:

```text
makanan ikan 10k
```

The bot can parse it, but the category may need review. Instead of saving directly, it shows a warning and asks the user to continue, edit, or cancel.

## Clarification flow

Clarification is used when the meaning is too ambiguous.

Example:

```text
Budi bayar makan 100k
```

The bot should ask what the user means instead of forcing one interpretation.

## Debt flow

Debt input also goes through preview.

```text
Budi minjem 50k
→ debt preview
→ Edit dulu / Lanjut / Batal
→ account or final confirmation if needed
→ save
```

## Split bill flow

Split bill can create both a transaction and debt relation.

Examples:

```text
galon 24k dibagi 4
makan 80k bagi dua sama Budi
makan 80k berdua sama Budi
minyak 46k patungan berempat sama Budi Rina Tono
```

The flow makes sure the user confirms how the split should be recorded.

## Pending expense flow

Pending expense is used for planned or incomplete expenses.

Example:

```text
wifi bulan depan 285k
```

This should not immediately change the account balance. It is stored as pending until the user marks it as paid.

## Final save

Final save is handled by service files, not by the parser.

Examples:

- `transaction_service.py`
- `debt_service.py`
- `pending_expense_service.py`
- `net_worth_service.py`

This separation keeps parser logic, user flow, and data writing easier to debug.
