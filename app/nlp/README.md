# app/nlp

This folder contains the parser and AI language layer.

The goal is to convert messy daily finance input into structured data that the backend can validate and preview.

## Main files

- `regex_parser.py`: rule-based parser for common finance inputs.
- `normalizer.py`: amount, account, and text normalization.
- `parse_safety.py`: risk routing for warning preview, Gemini draft preview, or clarification.
- `gemini_parser.py`: Gemini fallback parser.
- `gemini_image_parser.py`: receipt and image parsing, including item quantity, unit price, receipt metadata, and extra charges such as service, PPN, and discount.
- `gemini_intent_router.py`: AI-assisted intent routing for read-only finance questions.
- `gemini_finance_insight.py`: prompt builder and generator for insight, audit, coach, and Q&A.

## Ownership Contract

NLP owns parsing and provider adapters, not final financial confirmation or writes. Gemini calls consume the shared request budget and use the governed client; prompt content and finance payloads must not enter logs. Unit and regression tests cover schemas, call counts, malformed output, privacy, and fallback.
