# 10. Glossary

## Account

A funding source such as `Cash`, `BRI`, `BCA`, `DANA`, or `GoPay`.

## Parse safety

A layer that checks whether a parsed input is safe enough for preview or needs warning or clarification.

## Preview before write

The principle that the bot should show data to the user before saving it to Google Sheets.

## Split bill

A transaction shared with other people. Paid split bills save only the user's net share. Unpaid split bills save the gross paid amount and create receivables.

## Net expense

The expense amount after subtracting linked receivable shares from split bill or talangan flows. Reports use this as the primary expense basis.

## Gross expense

The original transaction amount before linked receivable shares are subtracted. When gross differs from net, the bot displays values as `net (gross)`.

## Talangin

A case where the user pays first for someone else.

## Ditalangin

A case where someone else pays first for the user.

## Debt-only payable

A payable debt recorded without changing an account balance. Example: `catat utang ke Budi 200k`.

## Monthly chart

An SVG document generated from monthly report data. The line chart shows daily net expense, the bar chart ranks net expense by category, and the pie chart shows category share from total net expense.

## Polling mode

The default runtime where the bot continuously fetches Telegram updates.

## Webhook mode

An optional runtime where Telegram sends updates to a FastAPI endpoint.
