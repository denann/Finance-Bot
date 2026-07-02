# 07. AI Insight Layer

The AI layer helps explain finance data, but it does not replace backend business logic.

Main commands:

- `/ask`
- `/audit`
- `/coach`
- `/insight`

## Flow

```text
user command
→ finance context builder
→ Gemini prompt
→ Gemini response
→ Telegram reply
```

Gemini receives structured context from Google Sheets. This keeps answers grounded in the user's data.
