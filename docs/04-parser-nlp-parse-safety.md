# 04. Parser, NLP, and Parse Safety

The parser layer converts natural Indonesian finance input into structured dictionaries.

Example:

```text
beli kopi 20k dari DANA
```

becomes:

```python
{
  "type": "expense",
  "amount": 20000,
  "category": "Food & Beverage",
  "account": "DANA",
  "description": "Kopi"
}
```

## Main modules

- `regex_parser.py`: local rule-based parser.
- `normalizer.py`: amount and text normalization.
- `parse_safety.py`: warning, clarification, and Gemini draft routing.
- `gemini_parser.py`: fallback parser.
- `gemini_image_parser.py`: image and receipt parser.

## Parse safety

Parse safety prevents risky input from being saved too quickly. It can route an input to normal preview, warning preview, Gemini draft preview, or clarification.
