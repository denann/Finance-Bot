# Finance Bot Input and Usage Guide

This is the primary guide for using Finance Bot through Telegram. It explains
how to write inputs, choose a command format, review previews, and correct
stored data. All names, amounts, accounts, and transactions in the examples
below are fictional.

The documentation is written in English. Indonesian phrases remain in command
examples because the bot's natural-language parser is optimized for Indonesian
financial input.

## Quick Start

1. Send `/start`, followed by `/quickstart`.
2. Check available accounts with `/saldo`.
3. Set an opening balance with `/set_saldo AccountName Amount` if needed.
4. Send a transaction using everyday Indonesian.
5. Check the transaction type, amount, date, account, and description in the
   preview.
6. Select **Simpan** only when the preview is correct. Select **Edit** or
   **Batal** if anything is wrong.

The interface uses `+` for income or cash-in and `-` for expense or cash-out.
Action buttons start with a symbol so their purpose is visible at a glance.
Number-only buttons are intentional selectors: read the numbered details in
the message, then select the matching number.

Initial example:

```text
/set_saldo DANA 500k
beli kopi 20k dari DANA
gaji masuk 8 juta ke BRI
transfer DANA 100k dari BCA
```

## Natural-Language Input Pattern

The bot does not require spreadsheet syntax. Use an explicit sentence and
include the account when you already know it.

| Goal | Recommended pattern | Example |
| :--- | :--- | :--- |
| Expense | `[action] [item/purpose] [amount] dari [account] [date]` | `beli kopi 20k dari DANA kemarin` |
| Income | `[income source] [amount] ke [account] [date]` | `gaji masuk 8 juta ke BRI` |
| Transfer | `transfer [destination account] [amount] dari [source account]` | `transfer DANA 100k dari BCA` |
| Debt you owe | `saya pinjam [amount] ke [name]` | `saya pinjam 100k ke Budi` |
| Money owed to you | `[name] minjem [amount]` | `Budi minjem 50k` |
| Debt payment | `saya bayar hutang [name] [amount] dari [account]` | `saya bayar hutang Budi 50k dari BRI` |
| Receivable payment | `[name] bayar [amount] ke [account]` | `Budi bayar 25k ke DANA` |
| Split bill | `[purpose] [total] dibagi [people count] sama [names] dari [account]` | `makan 120k dibagi 3 sama Budi Rina dari BCA` |
| Planned expense | `nanti/rencana/perlu [purpose] [amount] [date]` | `nanti bayar wifi 285k bulan depan` |

### Amounts

Common amount formats include:

```text
20000
20k
20rb
1.5 juta
8jt
150.000
```

Use one primary amount per transaction. Always check the normalized amount in
the preview, especially when using a period or comma.

### Dates

The bot recognizes practical date formats such as:

```text
hari ini
kemarin
2026-09-04
04-09-2026
tanggal 20
bulan depan
```

Dates without a year and relative phrases use the configured business time
zone. When a date is invalid, the bot should request a correction instead of
saving the transaction.

### Accounts

- Use `dari` to identify the source account for an expense.
- Use `ke` to identify the destination account for income.
- For a transfer, include both the source and destination accounts.
- Use the same account names shown by `/saldo` or `/set_saldo`.
- If the account is unclear, select it from the bot's buttons.

## Single and Multiple Transactions

For a single transaction, send one sentence:

```text
beli bensin 50k dari BRI
```

For multiple transactions, a new line or semicolon is the safest separator:

```text
beli kopi 10k dari Cash
beli nasi 20k dari DANA
Budi minjem 50k
```

```text
beli kopi 10k dari Cash; beli nasi 20k dari DANA; Budi minjem 50k
```

A comma is also recognized as an item separator, but avoid commas inside a
batch item description. If one item is ambiguous, the bot can clarify that
item without discarding the others. The batch must reach a final preview
before it can be saved.

## Expenses, Income, and Transfers

Expense examples:

```text
beli kopi 25rb
bayar listrik 150.000 dari BRI
jajan bakso 20k dari Cash
```

Income examples:

```text
gaji masuk 8 juta ke BRI
freelance project 500rb ke DANA
dapet bonus 1 juta
```

Transfer examples:

```text
transfer GoPay 200rb dari BRI
top up DANA dari BRI 500rb
BCA ke DANA 200k
```

A transfer only moves money between accounts. It must not become a normal
expense or income entry.

## Debts, Receivables, Fronting, and Split Bills

Use explicit sentences because cash flow and debt relationships have different
effects.

```text
catat utang ke Budi 200k
saya pinjam 100k ke Budi
Budi minjem 50k dari DANA
saya talangin Raka beli nasi kuning 12k dari DANA
saya ditalangin Bagas beli nasi uduk 10k
```

`catat utang ke Budi 200k` records a debt relationship without increasing an
account balance. In contrast, `saya pinjam 100k ke Budi` represents received
money and requires a cash-flow account.

### Writing an Explicit Split Bill

Include the transaction total, the number of people including yourself, the
other participants, and the account when available:

```text
Beli mie goreng 40k dibagi 2 sama Budi dari DANA
makan 120k patungan bertiga sama Budi dan Rina dari BCA
Bayar PAM 199.200k dibagi 4 sama Alpat Opik Sapto tanggal 20
```

Compact input without `sama` is also accepted when the participant count and
names are clear:

```text
Bayar wifi 285.550k via DANA bagi 4 Sapto Alpat Opik tanggal 19 Agustus
```

The explicit `sama` form is still recommended because it is easier to review.
The total before `bagi` or `dibagi` is the gross bill; an account phrase
between the amount and split marker does not change that total.

In the final pattern, `PAM` is the expense subject and the names after `sama`
are split participants. Direct, ambiguous, and multi-input split bills all use
the same guided flow. At the status step, choose **Sudah dibayar** when the
other participants have already paid their shares, or **Belum dibayar** when
their shares should become active receivables. The selected status completes
that item and returns the flow to its preview; it does not ask the same
question again. Do not continue when the names, number of people, or total in
the preview is incorrect.

For an uneven split, use weights or direct amounts:

```text
Beli token 500k dibagi 4 sama Raka:100% Fajar:80% Bagas:100%
Beli token 500k dibagi 4 sama Raka 125k Fajar 100k Bagas 125k
```

## Pending Expenses

A pending expense is a plan, not an actual transaction. It does not change an
account balance until it is marked as paid.

```text
nanti bayar wifi 285k bulan depan
/pending_add bayar wisuda 750k tgl 30 dari BRI
/pending
/pending_paid pending_id BRI
/pending_cancel pending_id
```

Get the `pending_id` from `/pending`. Review the preview before marking an item
as paid or canceling it.

## Choosing a Command Format

The bot uses three primary command patterns. Do not mix patterns within a
command unless an example below explicitly does so.

| Pattern | When to use it | Example |
| :--- | :--- | :--- |
| Positional arguments | Simple commands with a fixed argument order | `/set_saldo DANA 500k` |
| `key=value` | Commands with multiple fields or updates | `/edit_txn 2 amount=15000 account=BRI` |
| Guided wizard | When fields are unknown or button guidance is useful | `/asset_add` |

Quote a `key=value` value when it contains spaces:

```text
/edit_txn 2 category="Food & Beverage" desc="Kopi susu"
/asset_add name="Emas Antam" quantity=10 unit=gram price=1.5jt category=Emas
```

Some asset and recurring commands still accept the legacy pipe format for
compatibility. Use the wizard or `key=value` for new input.

## Viewing, Editing, and Deleting Transactions

Run a transaction-list command first:

```text
/last
/last 20
/last today
/transaksi 2026-09
/cari kopi
```

`/last` and `/transaksi` use the same paginated transaction browser. The list
shows grouped totals and numbered records; open a number for details and edit
or delete actions. These commands do not automatically send a chart. Use
`/grafik` or a report command when a chart is needed.

Use a number from the most recent result:

```text
/edit_txn 2 amount=15000
/edit_txn 2 account=BRI category="Food & Beverage"
/delete_txn 1
/delete_txn 1 3 5
/delete_txn 1-4
```

A bulk edit can contain multiple `/edit_txn` lines. Category decisions and a
final preview are handled before the batch is saved.

### Managing Debts

```text
/hutang Budi
/debt_void 1
/debt_edit 1 nominal 100k
/debt_edit 1 nama Budi
/debt_edit 1 tipe piutang
/debt_settle Budi
/debt_settle Budi 1-3
/debt_settle Budi 1-3 amount=150k account=DANA
```

Debt numbers come from the latest `/hutang Name` details. The person in the
latest details must match the person targeted by the next command. The current
`/debt_edit` handler applies an update after its format and reference pass
validation, without a second preview. Check this command carefully and verify
the result with `/hutang Name`.

When `/hutang` lists people or records, the message contains the descriptive
details while the keyboard uses compact number-only selectors. Six entries fit
on a page in two rows of three buttons. Select the number that matches the
message; pagination and action buttons keep their own symbols.

## Recurring Transactions

Run `/recurring_add` without arguments to start the wizard, or use
`key=value`:

```text
/recurring_add name=Netflix type=expense amount=65000 category=Entertainment account=DANA frequency=monthly day=5 description="Langganan Netflix"
```

The current parser requires `name`, `type`, `amount`, `category`, `account`,
`frequency`, and `day`. Supported frequency values are `monthly` and
`bulanan`. The `description` field is optional.

```text
/recurring
/recurring_edit rec_xxx amount=75000 day=10 account=DANA
/recurring_run
/recurring_off rec_xxx
```

Get the rule ID from `/recurring`. Edit, run, and disable commands show a final
preview before applying the change.

## Assets and Net Worth

The guided wizard is the simplest method:

```text
/asset_add
```

Single-line formats:

```text
/asset_add name=Laptop amount=8jt category=Electronics desc="Laptop kerja"
/asset_add name="Emas Antam" quantity=10 unit=gram price=1.5jt category=Emas
/asset_update asset_id unit_price=2420000
/asset_update asset_id harga_beli=2559000 tanggal_beli=2026-06-10
/asset_off asset_id
```

Get the `asset_id` from `/assets`. Use `/networth` for the current summary,
`/networth_snapshot` to save a snapshot after preview, and
`/networth_history` to view the history.

## Receipt and Transaction Images

Send a receipt, invoice, QRIS, or transaction screenshot. An optional caption
can clarify the intent:

```text
pakai BSI
ini pemasukan
total aja
```

The bot displays the extracted details, item selection, account choice, and
final preview. Do not save when an item, quantity, unit price, tax, service
charge, discount, or total does not match the image.

## Reports and Help

```text
/saldo
/harian
/mingguan
/bulanan
/grafik bar 2026-09
/grafik pie 2026-09
/budget
/networth
/ask bulan ini boros di mana?
```

For help inside Telegram:

```text
/help input
/help debt
/help transaksi
/help commands
/examples
/manual
```

## When an Input Is Misinterpreted

1. Do not select **Simpan**.
2. Select **Edit** when the incorrect field can be corrected.
3. Select **Batal** when the intent is wrong, such as a transfer interpreted as
   an expense.
4. Rewrite the input with a clearer intent, amount, person, and account.
5. Use one transaction per line when a batch is difficult to interpret.
6. Run `/help <topic>` or `/manual` for more detail.

Do not force a classification for an ambiguous input such as
`makan bareng Budi 80k`. It can mean a split bill, treating someone, or a
normal expense.

## Privacy

- Primary financial data is stored in the configured Google Spreadsheet.
- Telegram is the input and output channel.
- Gemini is used only by AI features, image parsing, parser fallback, and
  category alias suggestions that require it.
- Never send tokens, API keys, `.env`, or a service-account file to the bot.
- Exported files contain private financial data. Store and share them
  carefully.
- Use `/privacy` for the in-bot privacy summary.

## Sources of Truth and Maintenance

This guide is derived from the command registry, in-bot help, active handlers,
and contract tests. If they differ, use the project's source-of-truth order:
passing tests, registries, implementation, and then documentation. Maintainers
should run this check after changing commands or input examples:

```powershell
python scripts/check_docs.py
```

The complete command list remains available through `/help commands`. For
technical details, see the [documentation index](../README.md) and
[documentation source of truth](../documentation-source-of-truth.md).
