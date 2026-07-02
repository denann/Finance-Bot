"""Text normalizer for user input, amounts, accounts, typo patterns, and split bill phrases."""

import re


def normalize_amount(text: str) -> int | None:
    """Clean and standardize normalize amount."""
    if not text:
        return None

    # Lowercase and remove spaces.
    text = text.lower().strip()

    # Parser rule note for an Indonesian finance input edge case.
    text = text.replace(",", ".")

    # Parser rule note for an Indonesian finance input edge case.
    pattern = r"(\d+(?:\.\d+)?)(?:\s*(rb|ribu|k|jt|juta|m|miliar|miliard|milyard)\b)?"
    match = re.search(pattern, text)

    if not match:
        return None

    number_str = match.group(1)
    unit = match.group(2) or ""

    parsed = parse_amount_value(number_str, unit)
    return parsed


def normalize_text(text: str) -> str:
    """Clean and standardize normalize text."""
    return text.lower().strip()


def parse_amount_value(number_str: str, unit: str = "") -> int | None:
    """Parse input into structured data for the parser and NLP layer."""
    raw = str(number_str or "").strip().lower().replace(",", ".")
    unit = str(unit or "").strip().lower()

    if not raw:
        return None

    try:
        # Parser rule note for an Indonesian finance input edge case.
        # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
        if unit in {"rb", "ribu", "k"}:
            if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
                return int(raw.replace(".", ""))
            return int(float(raw) * 1_000)

        if unit in {"jt", "juta", "m"}:
            return int(float(raw) * 1_000_000)

        if unit in {"miliar", "miliard", "milyard"}:
            return int(float(raw) * 1_000_000_000)

        # Parser rule note for an Indonesian finance input edge case.
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
            return int(raw.replace(".", ""))

        return int(float(raw))
    except Exception:
        return None


def extract_amount_from_text(text: str) -> int | None:
    """Extract the important part of the input for amount from text."""
    text = text.lower().strip()

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    unit_pattern = r"rb|ribu|k|jt|juta|m|miliar|miliard|milyard"
    token_pattern = rf"(\d+(?:[.,]\d+)?)(?:\s*({unit_pattern})\b)?"
    expr_match = re.search(
        rf"{token_pattern}\s*([+\-])\s*{token_pattern}",
        text,
        flags=re.IGNORECASE,
    )
    if expr_match:
        n1, u1, op, n2, u2 = expr_match.groups()
        if u1 or u2:
            v1 = parse_amount_value(n1, u1 or "")
            v2 = parse_amount_value(n2, u2 or "")
            if v1 is not None and v2 is not None:
                result = v1 + v2 if op == "+" else v1 - v2
                if result > 0:
                    return int(result)

    # Tangani format titik ribuan: "150.000" atau "1.500.000"
    # Parser rule note for an Indonesian finance input edge case.
    ribuan_pattern = r"\b(\d{1,3}(?:\.\d{3})+)\b"
    ribuan_match = re.search(ribuan_pattern, text)
    if ribuan_match:
        clean = ribuan_match.group(1).replace(".", "")
        return int(clean)

    # Parser rule note for an Indonesian finance input edge case.
    pattern = r"(\d+(?:[.,]\d+)?)(?:\s*(rb|ribu|k|jt|juta|m|miliar|miliard|milyard)\b)?"
    matches = re.findall(pattern, text)

    if not matches:
        return None

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    best = None
    best_value = 0

    for number_str, unit in matches:
        value = parse_amount_value(number_str, unit or "")
        if value is None:
            continue
        if value > best_value:
            best_value = value
            best = value
    if best:
        best = apply_split_operation(text, best)
    return best


def apply_split_operation(text: str, base_amount: int) -> int:
    """Apply changes for split operation."""
    text_lower = text.lower()

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Contoh:
    # - "Tissue 10k bagi 4 sama fajar bagas raka"
    # - "Nasi kuning 22k dibagi 2 sama raka"
    # Debt command note: keep payable and receivable actions explicit and auditable.
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"

    participant_token = r"(?:\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|berdua|bertiga|berempat|berlima|berenam)"

    if re.search(rf"\b{split_word}\s*(?:jadi\s*)?{participant_token}\s+(?:orang\s+)?{friend_marker}\b", text_lower):
        return base_amount
    if re.search(rf"\b{friend_marker}\s+[a-zA-ZÀ-ÿ\s]{{1,60}}\s+{split_word}\s*(?:jadi\s*)?{participant_token}\b", text_lower):
        return base_amount
    if re.search(rf"\b(?:berdua|bertiga|berempat|berlima|berenam)\s+{friend_marker}\b", text_lower):
        return base_amount

    # Shorthand split bill: "46k/4 sama raka bagas fajar".
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Split bill parsing note: separate the paid transaction from each person share.
    if re.search(rf"/\s*\d+\s+(?:orang\s+)?{friend_marker}\b", text_lower):
        return base_amount
    if re.search(r"/\s*\d+\s+[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s,;&]{1,80}", text_lower):
        return base_amount

    # Pola: "dibagi N", "di bagi N", "di-bagi N", "bagi N", "split N", "/ N"
    split_patterns = [
        rf"{split_word}\s*(?:jadi\s*)?(\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh)",
        r"/\s*(\d+)",
        r"untuk\s+(\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh)\s+orang",
        r"bertiga|berdua|berempat|berlima|berenam",
        r"(\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh)\s+orang",
    ]

    # Split bill parsing note: separate the paid transaction from each person share.
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    word_map = {
        "dua": 2,
        "tiga": 3,
        "empat": 4,
        "lima": 5,
        "enam": 6,
        "tujuh": 7,
        "delapan": 8,
        "sembilan": 9,
        "sepuluh": 10,
        "berdua": 2,
        "bertiga": 3,
        "berempat": 4,
        "berlima": 5,
        "berenam": 6,
    }

    ber_match = re.search(r"\b(berdua|bertiga|berempat|berlima|berenam)\b", text_lower)
    if ber_match and re.search(rf"\b(?:{split_word}|untuk|bareng)\b", text_lower):
        divisor = word_map.get(ber_match.group(1))
        if divisor and divisor > 1:
            return base_amount // divisor

    # Split bill parsing note: separate the paid transaction from each person share.
    for pattern in split_patterns:
        match = re.search(pattern, text_lower)
        if match and match.lastindex:
            try:
                raw_divisor = str(match.group(1)).strip().lower()
                divisor = word_map.get(raw_divisor) or int(raw_divisor)
                if divisor > 1:
                    return base_amount // divisor
            except (IndexError, ValueError):
                continue

    return base_amount