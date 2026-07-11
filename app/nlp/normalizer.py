"""Text normalizer for amounts, account names, split bill phrases, and Indonesian finance input patterns."""


# Import re for this module's local operations.
import re


# Helper for normalize amount.
def normalize_amount(text: str) -> int | None:
    """Normalize input values for the normalize amount workflow in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `int | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Validate missing text before continuing.
    if not text:
        return None

    # Lowercase and remove spaces.
    text = text.lower().strip()

    text = text.replace(",", ".")

    pattern = r"(\d+(?:\.\d+)?)(?:\s*(rb|ribu|k|jt|juta|m|miliar|miliard|milyard)\b)?"
    match = re.search(pattern, text)

    # Validate missing match before continuing.
    if not match:
        return None

    number_str = match.group(1)
    unit = match.group(2) or ""

    parsed = parse_amount_value(number_str, unit)
    return parsed


# Helper for normalize text.
def normalize_text(text: str) -> str:
    """Normalize input values for the normalize text workflow in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    return text.lower().strip()


def parse_amount_value(number_str: str, unit: str = "") -> int | None:
    """Parse caller input for the parse amount value workflow in the NLP/parser layer.

    Args:
        number_str: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        unit: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `int | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    raw = str(number_str or "").strip().lower().replace(",", ".")
    unit = str(unit or "").strip().lower()

    # Validate missing raw before continuing.
    if not raw:
        return None

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
        if unit in {"rb", "ribu", "k"}:
            if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
                return int(raw.replace(".", ""))
            return int(float(raw) * 1_000)

        if unit in {"jt", "juta", "m"}:
            return int(float(raw) * 1_000_000)

        if unit in {"miliar", "miliard", "milyard"}:
            return int(float(raw) * 1_000_000_000)

        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
            return int(raw.replace(".", ""))

        return int(float(raw))
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return None


# Helper for extract amount from text.
def extract_amount_from_text(text: str) -> int | None:
    """Extract the required part of input for amount from text."""
    # Prepare text from the incoming input.
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
            # Handle v1 is not None and v2 is not None.
            if v1 is not None and v2 is not None:
                result = v1 + v2 if op == "+" else v1 - v2
                if result > 0:
                    return int(result)

    # Tangani format titik ribuan: "150.000" atau "1.500.000"
    ribuan_pattern = r"\b(\d{1,3}(?:\.\d{3})+)\b"
    ribuan_match = re.search(ribuan_pattern, text)
    if ribuan_match:
        clean = ribuan_match.group(1).replace(".", "")
        return int(clean)

    pattern = r"(\d+(?:[.,]\d+)?)(?:\s*(rb|ribu|k|jt|juta|m|miliar|miliard|milyard)\b)?"
    matches = re.findall(pattern, text)

    # Validate missing matches before continuing.
    if not matches:
        return None

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    best = None
    best_value = 0

    # Iterate through each number str, unit.
    for number_str, unit in matches:
        value = parse_amount_value(number_str, unit or "")
        if value is None:
            # Skip the rest of this loop iteration after handling this case.
            continue
        if value > best_value:
            best_value = value
            best = value
    if best:
        best = apply_split_operation(text, best)
    return best


# Helper for apply split operation.
def apply_split_operation(text: str, base_amount: int) -> int:
    """Return the user-paid amount after applying explicit split-bill wording.

    Args:
        text: Raw Indonesian finance input that may contain split words such as
            `dibagi 4`, `patungan`, `split`, or shorthand `/4`.
        base_amount: Positive integer amount already extracted from `text`.

    Returns:
        Integer amount to store for the main transaction. For explicit split
        phrases this may be divided by the detected participant count. For
        normal non-split inputs it returns `base_amount` unchanged.

    Side effects:
        None.

    Flow constraints:
        Do not treat normal expenses, pending expenses, debts, or recurring
        amounts as split bills unless an explicit split marker is present.
    """
    # Normalize text lower before matching.
    text_lower = text.lower()

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Implementation note for this project-specific finance flow.
    # - "Tissue 10k bagi 4 sama fajar bagas raka"
    # - "Nasi kuning 22k dibagi 2 sama raka"
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"

    participant_token = r"(?:\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|berdua|bertiga|berempat|berlima|berenam)"

    if re.search(rf"\b{split_word}\s*(?:jadi\s*)?{participant_token}\s+(?:orang\s+)?{friend_marker}\b", text_lower):
        return base_amount
    if re.search(rf"\b{friend_marker}\s+[a-zA-ZÀ-ÿ\s]{{1,60}}\s+{split_word}\s*(?:jadi\s*)?{participant_token}\b", text_lower):
        return base_amount
    if re.search(rf"\b(?:berdua|bertiga|berempat|berlima|berenam)\s+{friend_marker}\b", text_lower):
        return base_amount

    # Keep the gross amount when a split divisor has no named participant yet.
    # The clarification layer must resolve the missing people before dividing.
    if re.search(
        rf"\b{split_word}\s*(?:jadi\s*)?(?:\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh)\s*(?:(?:tanggal|tgl)\b|\d{{1,2}}[-/]\d{{1,2}}|$)",
        text_lower,
    ):
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
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Prepare raw divisor from the incoming input.
                raw_divisor = str(match.group(1)).strip().lower()
                divisor = word_map.get(raw_divisor) or int(raw_divisor)
                if divisor > 1:
                    return base_amount // divisor
            # Handle an expected failure from the guarded operation above.
            except (IndexError, ValueError):
                # Skip the rest of this loop iteration after handling this case.
                continue

    # Keep this section separated from the surrounding flow.
    # Keep normal non-split amounts unchanged after all split patterns are checked.
    return base_amount
