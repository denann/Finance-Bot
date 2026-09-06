# app/bot

This folder contains the Telegram bot interface layer.

It is responsible for receiving commands, natural text input, images, and inline button callbacks. It does not own the finance data itself. It calls the parser and service layer to process the actual logic.

## Main files

- `application.py`: builds the Telegram Application and registers handlers.
- `output.py`: adds contextual icon legends to Telegram text and media captions;
  the application and scheduler both use its `FinanceBot` transport.
- `command_registry.py`: canonical command names, aliases, and compatibility metadata.
- `callback_contracts.py`: callback ownership and bounded routing predicates.
- `command_mutations.py`: allow-listed mutations executed after immutable confirmation.
- `handlers.py`: re-exports handler modules for a stable import path.
- `keyboards.py`: contains reusable inline keyboard helpers.
- `pending_actions.py`: immutable, short-lived, one-shot confirmation actions.
- `handler_parts/`: contains split handler modules for commands, messages, callbacks, and transaction preview flows.

The interface uses plain `+` for income/cash-in and `-` for
expense/cash-out. Descriptive inline buttons start with a symbol; compact
number-only selectors are reserved for lists whose details are shown in the
message. Ambiguity choices use contextual icons rather than report-style
signs. Split-bill paths share one wizard keyboard contract.

## Receipt images

Itemized receipt images are handled as a Telegram flow, not saved immediately. The bot shows OCR details first, lets the user choose all items or only selected parts, shows a detailed batch preview, asks for the account, then shows a compact final summary before saving.

## Ownership Contract

Public entry points are the application builder, command registry, handlers, callback dispatcher, keyboards, and pending actions. This layer owns Telegram rendering/state, not finance calculations or direct persistence. Command names and callback data are protected contracts. Coverage lives under integration and regression tests.
