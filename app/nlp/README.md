# app/nlp

This folder contains the parser and AI interpretation layer.

The practical goal is to turn Indonesian finance input into structured data that the backend can validate and save.

## Files

| File | Purpose |
|---|---|
| `normalizer.py` | Cleans input text, amounts, accounts, and split phrases |
| `regex_parser.py` | Main deterministic parser |
| `parse_safety.py` | Decides whether parser output is safe or needs clarification |
| `gemini_parser.py` | Gemini-assisted parser fallback |
| `gemini_image_parser.py` | Image and receipt parser |
| `gemini_intent_router.py` | AI-assisted natural command router |
| `gemini_finance_insight.py` | Prompt and response helpers for insight commands |
| `gemini_langchain_client.py` | Gemini wrapper through LangChain |

The backend should always validate important actions. AI can help draft or explain, but it should not directly save sensitive financial data.
