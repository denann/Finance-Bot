# app/nlp

This folder contains the parser and AI language layer.

The goal is to convert messy daily finance input into structured data that the backend can validate and preview.

## Main files

- `regex_parser.py`: rule-based parser for common finance inputs.
- `normalizer.py`: amount, account, and text normalization.
- `parse_safety.py`: risk routing for warning preview, Gemini draft preview, or clarification.
- `gemini_parser.py`: Gemini fallback parser.
- `gemini_image_parser.py`: receipt and image parsing.
- `gemini_intent_router.py`: AI-assisted intent routing for read-only finance questions.
- `gemini_finance_insight.py`: prompt builder and generator for insight, audit, coach, and Q&A.
