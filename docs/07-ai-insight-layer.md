# 07. AI Insight Layer

AI is used as an assistant layer, not as the final controller of finance logic.

Main commands:

```text
/ask
/audit
/coach
/insight
```

## High-level flow

```text
User command
→ command handler
→ finance_insight_service builds context
→ gemini_finance_insight builds prompt
→ Gemini generates explanation
→ Telegram response
```

## Context builder

`app/services/finance_insight_service.py` prepares structured context before calling Gemini.

This context can include:

- transactions,
- category summaries,
- account balances,
- budget status,
- debt summary,
- asset and net worth summary,
- anomaly flags,
- data quality issues.

## Gemini prompt layer

`app/nlp/gemini_finance_insight.py` builds the prompt for each mode.

| Mode | Purpose |
|---|---|
| `ask` | Answer a natural finance question based on user data |
| `audit` | Check data quality and suspicious patterns |
| `coach` | Give practical finance suggestions |
| `insight` | Explain monthly spending patterns and priorities |

## Image parser

`app/nlp/gemini_image_parser.py` parses receipts or transaction images.

The output is still treated as a draft. The user must review the preview before data is saved.

## Safety principle

AI can help understand input and explain output, but it should not directly save sensitive data or decide final financial actions.

Sensitive actions still depend on backend rules and user confirmation.
