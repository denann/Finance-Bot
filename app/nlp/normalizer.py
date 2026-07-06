"""Text normalizer for amounts, account names, split bill phrases, and Indonesian finance input patterns."""


# Import re for this module's local operations.
import re


# Define normalize amount for callers in this flow.
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
    # Handle the missing or empty text case.
    if not text:
        # Return None to the caller.
        return None

    # Lowercase and remove spaces.
    text = text.lower().strip()

    # Parser rule note for an Indonesian finance input edge case.
    text = text.replace(",", ".")

    # Parser rule note for an Indonesian finance input edge case.
    pattern = r"(\d+(?:\.\d+)?)(?:\s*(rb|ribu|k|jt|juta|m|miliar|miliard|milyard)\b)?"
    # Prepare match for the next step.
    match = re.search(pattern, text)

    # Handle the missing or empty match case.
    if not match:
        # Return None to the caller.
        return None

    # Prepare number str for the next step.
    number_str = match.group(1)
    unit = match.group(2) or ""

    # Prepare parsed for the next step.
    parsed = parse_amount_value(number_str, unit)
    # Return parsed to the caller.
    return parsed


# Define normalize text for callers in this flow.
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
    # Return text.lower().strip() to the caller.
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

    # Handle the missing or empty raw case.
    if not raw:
        # Return None to the caller.
        return None

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Parser rule note for an Indonesian finance input edge case.
        # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
        if unit in {"rb", "ribu", "k"}:
            if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
                return int(raw.replace(".", ""))
            # Return int(float(raw) * 1_000) to the caller.
            return int(float(raw) * 1_000)

        if unit in {"jt", "juta", "m"}:
            # Return int(float(raw) * 1_000_000) to the caller.
            return int(float(raw) * 1_000_000)

        if unit in {"miliar", "miliard", "milyard"}:
            # Return int(float(raw) * 1_000_000_000) to the caller.
            return int(float(raw) * 1_000_000_000)

        # Parser rule note for an Indonesian finance input edge case.
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
            return int(raw.replace(".", ""))

        # Return int(float(raw)) to the caller.
        return int(float(raw))
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return None to the caller.
        return None


# Define extract amount from text for callers in this flow.
def extract_amount_from_text(text: str) -> int | None:
    """Extract the required part of input for amount from text."""
    # Prepare text for the next step.
    text = text.lower().strip()

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    unit_pattern = r"rb|ribu|k|jt|juta|m|miliar|miliard|milyard"
    token_pattern = rf"(\d+(?:[.,]\d+)?)(?:\s*({unit_pattern})\b)?"
    # Open a multi-line structure for the values below.
    expr_match = re.search(
        rf"{token_pattern}\s*([+\-])\s*{token_pattern}",
        # Include this value in the surrounding collection or call.
        text,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where expr_match.
    if expr_match:
        # Run this statement as part of the current workflow.
        n1, u1, op, n2, u2 = expr_match.groups()
        # Handle the case where u1 or u2.
        if u1 or u2:
            v1 = parse_amount_value(n1, u1 or "")
            v2 = parse_amount_value(n2, u2 or "")
            # Handle the case where v1 is not None and v2 is not None.
            if v1 is not None and v2 is not None:
                result = v1 + v2 if op == "+" else v1 - v2
                # Handle the case where result > 0.
                if result > 0:
                    # Return int(result) to the caller.
                    return int(result)

    # Tangani format titik ribuan: "150.000" atau "1.500.000"
    # Parser rule note for an Indonesian finance input edge case.
    ribuan_pattern = r"\b(\d{1,3}(?:\.\d{3})+)\b"
    # Prepare ribuan match for the next step.
    ribuan_match = re.search(ribuan_pattern, text)
    # Handle the case where ribuan_match.
    if ribuan_match:
        clean = ribuan_match.group(1).replace(".", "")
        # Return int(clean) to the caller.
        return int(clean)

    # Parser rule note for an Indonesian finance input edge case.
    pattern = r"(\d+(?:[.,]\d+)?)(?:\s*(rb|ribu|k|jt|juta|m|miliar|miliard|milyard)\b)?"
    # Prepare matches for the next step.
    matches = re.findall(pattern, text)

    # Handle the missing or empty matches case.
    if not matches:
        # Return None to the caller.
        return None

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    best = None
    # Prepare best value for the next step.
    best_value = 0

    # Process each number_str, unit in the current collection.
    for number_str, unit in matches:
        value = parse_amount_value(number_str, unit or "")
        # Handle the case where value is None.
        if value is None:
            # Skip the rest of this loop iteration after handling this case.
            continue
        # Handle the case where value > best_value.
        if value > best_value:
            # Prepare best value for the next step.
            best_value = value
            # Prepare best for the next step.
            best = value
    # Handle the case where best.
    if best:
        # Prepare best for the next step.
        best = apply_split_operation(text, best)
    # Return best to the caller.
    return best


# Define apply split operation for callers in this flow.
def apply_split_operation(text: str, base_amount: int) -> int:
    """Coordinate the apply split operation logic in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        base_amount: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `int` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Prepare text lower for the next step.
    text_lower = text.lower()

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Implementation note for this project-specific finance flow.
    # - "Tissue 10k bagi 4 sama fajar bagas raka"
    # - "Nasi kuning 22k dibagi 2 sama raka"
    # Debt flow section
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"

    participant_token = r"(?:\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|berdua|bertiga|berempat|berlima|berenam)"

    if re.search(rf"\b{split_word}\s*(?:jadi\s*)?{participant_token}\s+(?:orang\s+)?{friend_marker}\b", text_lower):
        # Return base_amount to the caller.
        return base_amount
    if re.search(rf"\b{friend_marker}\s+[a-zA-ZÀ-ÿ\s]{{1,60}}\s+{split_word}\s*(?:jadi\s*)?{participant_token}\b", text_lower):
        # Return base_amount to the caller.
        return base_amount
    if re.search(rf"\b(?:berdua|bertiga|berempat|berlima|berenam)\s+{friend_marker}\b", text_lower):
        # Return base_amount to the caller.
        return base_amount

    # Shorthand split bill: "46k/4 sama raka bagas fajar".
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Split bill parsing note: separate the paid transaction from each person share.
    if re.search(rf"/\s*\d+\s+(?:orang\s+)?{friend_marker}\b", text_lower):
        # Return base_amount to the caller.
        return base_amount
    if re.search(r"/\s*\d+\s+[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s,;&]{1,80}", text_lower):
        # Return base_amount to the caller.
        return base_amount

    # Pola: "dibagi N", "di bagi N", "di-bagi N", "bagi N", "split N", "/ N"
    split_patterns = [
        rf"{split_word}\s*(?:jadi\s*)?(\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh)",
        r"/\s*(\d+)",
        r"untuk\s+(\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh)\s+orang",
        r"bertiga|berdua|berempat|berlima|berenam",
        r"(\d+|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh)\s+orang",
    # Close the structure that was opened above.
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
    # Close the structure that was opened above.
    }

    ber_match = re.search(r"\b(berdua|bertiga|berempat|berlima|berenam)\b", text_lower)
    if ber_match and re.search(rf"\b(?:{split_word}|untuk|bareng)\b", text_lower):
        # Prepare divisor for the next step.
        divisor = word_map.get(ber_match.group(1))
        # Handle the case where divisor and divisor > 1.
        if divisor and divisor > 1:
            # Return base_amount // divisor to the caller.
            return base_amount // divisor

    # Split bill parsing note: separate the paid transaction from each person share.
    for pattern in split_patterns:
        # Prepare match for the next step.
        match = re.search(pattern, text_lower)
        # Handle the case where match and match.lastindex.
        if match and match.lastindex:
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Prepare raw divisor for the next step.
                raw_divisor = str(match.group(1)).strip().lower()
                # Prepare divisor for the next step.
                divisor = word_map.get(raw_divisor) or int(raw_divisor)
                # Handle the case where divisor > 1.
                if divisor > 1:
                    # Return base_amount // divisor to the caller.
                    return base_amount // divisor
            # Handle an expected failure from the guarded operation above.
            except (IndexError, ValueError):
                # Skip the rest of this loop iteration after handling this case.
                continue

    # Keep this section separated from the surrounding flow.