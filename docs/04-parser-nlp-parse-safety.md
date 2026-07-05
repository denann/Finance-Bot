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

## Debt parser notes

Debt parsing keeps account-moving debt and non-account debt clearly separated.

`catat utang ke Budi 200k` is parsed as:

```python
{
  "intent": "add_payable",
  "person_name": "Budi",
  "amount": 200000,
  "cashflow_mode": "debt_only",
  "fronting_mode": "catat_utang",
  "skip_account": True
}
```

That payload means the bot should preview and save the payable without changing any account balance. It exists for cases where the user owes someone but did not receive money into an account.

Normal borrowing syntax stays separate. For example, `saya pinjam 100k ke Budi` still means money entered the user's account, so the bot must ask for or use an account.

Offset-like wording such as `potong piutang ke Budi 200k` should not silently change historical rows. If it is used to represent a separate liability, the safer syntax is `catat utang ke Budi 200k`; settlement remains a separate explicit debt payment or selected settlement flow.

## Parse safety

Parse safety prevents risky input from being saved too quickly. It can route an input to normal preview, warning preview, Gemini draft preview, or clarification.
