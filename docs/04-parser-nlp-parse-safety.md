# 04. Parser, NLP, and Parse Safety

The parser layer lives in `app/nlp/`.

Its job is to turn a natural-language finance message into structured data.

Example:

```text
beli kopi 20k dari Cash
```

can become:

```python
{
    "type": "expense",
    "amount": 20000,
    "category": "Food & Beverage",
    "account": "Cash",
    "description": "Kopi",
    "parsed_by": "regex"
}
```

## Main files

| File | Role |
|---|---|
| `normalizer.py` | Cleans text, human amounts, account names, and split bill phrases |
| `regex_parser.py` | Main local parser based on deterministic rules |
| `parse_safety.py` | Decides whether the parsed result is safe, risky, or needs clarification |
| `gemini_parser.py` | Gemini fallback parser when regex is not enough |
| `gemini_image_parser.py` | Parses receipts or transaction images |
| `gemini_intent_router.py` | Helps route natural read-only commands |
| `gemini_finance_insight.py` | Builds AI finance prompts and responses |

## Parsing order

The bot prioritizes deterministic parsing first:

```text
user input
→ regex parser
→ parse safety
→ preview / warning / clarification
→ Gemini only when useful
```

This design keeps the system controlled. Gemini helps when needed, but it is not the final decision maker for sensitive finance actions.

## Parse safety routing

`assess_parse_safety()` returns the recommended next action:

| Action | Meaning |
|---|---|
| `normal_preview` | The parser result is safe enough for normal preview |
| `warning_preview` | The result may be correct, but user should review it carefully |
| `gemini_draft_preview` | Gemini can help draft the result, but user still reviews it |
| `clarification` | The bot should ask the user what they mean before previewing |

Examples of risky input:

| Input Pattern | Reason |
|---|---|
| `Budi bayar makan 100k` | Could mean payment, expense, or someone else paid |
| `saldo BRI 500k` | Could mean checking balance or setting balance |
| `wifi bulan depan 285k` | Looks like a pending expense, not an immediate transaction |
| `makan 80k berdua sama Budi` | Could be a split bill |

## AI role

Gemini can help with:

- image parsing,
- draft parsing,
- finance insight,
- audit,
- coaching,
- Q&A over finance context.

But final write actions still require backend validation and user confirmation.
