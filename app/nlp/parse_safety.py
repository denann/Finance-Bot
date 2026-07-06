"""Parse safety module that decides whether a parsed input can be previewed, needs warning, needs Gemini draft, or needs clarification."""



# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import re for this module's local operations.
import re
# Import typing so this module can use its helpers.
from typing import Any

# Import app.nlp.normalizer so this module can use its helpers.
from app.nlp.normalizer import extract_amount_from_text, normalize_text
# Import app.nlp.regex_parser so this module can use its helpers.
from app.nlp.regex_parser import ACCOUNT_NAMES


NORMAL_PREVIEW = "normal_preview"
WARNING_PREVIEW = "warning_preview"
GEMINI_DRAFT_PREVIEW = "gemini_draft_preview"
CLARIFICATION = "clarification"

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"

ACCOUNT_PATTERN = r"cash|bri|bsi|bca|dana|gopay|seabank|sea\s*bank"
SELF_WORDS = {"saya", "aku", "gw", "gue", "gua", "ane"}
# Open a multi-line structure for the values below.
DEBT_KEYWORDS = {
    "hutang", "utang", "piutang", "debt", "cicil", "nyicil", "cicilan",
    "lunas", "lunasi", "lunasin", "melunasi", "bayar hutang", "bayar utang",
    "kembaliin", "balikin", "dibalikin", "transfer balik",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
PERSON_STOP_WORDS = {
    "makan", "makanan", "minum", "kopi", "nasi", "parkir", "listrik", "wifi",
    "internet", "pulsa", "bensin", "bbm", "kos", "kost", "kontrakan", "shopee",
    "tokopedia", "gojek", "grab", "gopay", "dana", "bri", "bca", "bsi", "cash",
    "seabank", "bayar", "beli", "ke", "dari", "pakai", "pake", "via",
    "nanti", "akan", "bakal", "rencana", "planning", "tagihan", "bulan",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
CLEAR_TOPUP_EXPENSE_TARGETS = {
    "bensin", "bbm", "pertalite", "pertamax", "solar",
    "pulsa", "paket", "data", "token", "listrik",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
AI_REVIEW_TOPUP_TARGETS = {
    "game", "ml", "mobile", "legend", "mobile legend", "steam",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
EXPENSE_CONTEXT_KEYWORDS = {
    "shopee", "tokopedia", "lazada", "gojek", "grab", "pulsa", "paket data",
    "makan", "makanan", "minum", "kopi", "donat", "bensin", "parkir", "game",
    "ml", "listrik", "wifi", "kos", "laundry", "laundri",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
AI_REVIEW_CATEGORY_PHRASES = {
    "makanan ikan", "pakan ikan", "pakan kucing", "makanan kucing",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
WARNING_CATEGORY_PHRASES = {
    "donat qq", "laundri",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
FUTURE_OR_BILLING_PERIOD_KEYWORDS = {
    "bulan depan", "minggu depan", "pekan depan", "semester depan", "tahun depan",
    "akhir bulan", "januari", "februari", "maret", "april",
    "mei", "juni", "juli", "agustus", "september", "oktober", "november",
    "desember", "jan", "feb", "mar", "apr", "jun", "jul", "agus", "agt",
    "sep", "okt", "nov", "des",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
PENDING_EXPLICIT_KEYWORDS = {
    "pending", "rencana", "planning", "plan", "nanti", "akan", "bakal",
    "perlu", "butuh", "kudu", "harus",
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
PAST_OR_ACTUAL_KEYWORDS = {
    "sudah", "udah", "sdh", "barusan", "tadi", "kemarin", "baru aja",
    "telah", "dibayar", "lunas",
# Close the structure that was opened above.
}


# Define contains phrase or word for callers in this flow.
def _contains_phrase_or_word(clean: str, keyword: str) -> bool:
    """Return True only when a keyword appears as a full word or phrase.

    This prevents short month aliases such as `jan` from matching inside words
    like `jajan`.
    """
    key = re.escape(str(keyword or "").strip().lower())
    # Handle the missing or empty key case.
    if not key:
        # Return False to the caller.
        return False
    key = key.replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![a-zA-ZÀ-ÿ]){key}(?![a-zA-ZÀ-ÿ])", clean, flags=re.IGNORECASE))


# Define has future or billing period for callers in this flow.
def _has_future_or_billing_period(clean: str) -> bool:
    """Detect future/billing period keywords without substring false positives."""
    # Return any(_contains_phrase_or_word(clean, keyword) for keyword in F... to the caller.
    return any(_contains_phrase_or_word(clean, keyword) for keyword in FUTURE_OR_BILLING_PERIOD_KEYWORDS)


# Define has past or actual keyword for callers in this flow.
def _has_past_or_actual_keyword(clean: str) -> bool:
    """Coordinate the has past or actual keyword logic in the NLP/parser layer.

    Args:
        clean: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Return any(_contains_phrase_or_word(clean, keyword) for keyword in P... to the caller.
    return any(_contains_phrase_or_word(clean, keyword) for keyword in PAST_OR_ACTUAL_KEYWORDS)


# Define has amount for callers in this flow.
def _has_amount(clean: str) -> bool:
    """Coordinate the has amount logic in the NLP/parser layer.

    Args:
        clean: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Return bool(extract_amount_from_text(clean)) to the caller.
    return bool(extract_amount_from_text(clean))


# Define has debt keyword for callers in this flow.
def _has_debt_keyword(clean: str) -> bool:
    """Coordinate the has debt keyword logic in the NLP/parser layer.

    Args:
        clean: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    # Return any(keyword in clean for keyword in DEBT_KEYWORDS) to the caller.
    return any(keyword in clean for keyword in DEBT_KEYWORDS)


# Define has account for callers in this flow.
def _has_account(clean: str) -> bool:
    """Coordinate the has account logic in the NLP/parser layer.

    Args:
        clean: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    return bool(re.search(rf"\b({ACCOUNT_PATTERN})\b", clean, flags=re.IGNORECASE))


# Define first token for callers in this flow.
def _first_token(value: str) -> str:
    """Coordinate the first token logic in the NLP/parser layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    return str(value or "").strip().split()[0].lower() if str(value or "").strip() else ""


# Define looks like person for callers in this flow.
def _looks_like_person(value: str) -> bool:
    """Coordinate the looks like person logic in the NLP/parser layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    clean = re.sub(r"[^a-zA-ZÀ-ÿ\s]", " ", str(value or "").lower())
    clean = re.sub(r"\s+", " ", clean).strip()
    # Handle the missing or empty clean case.
    if not clean:
        # Return False to the caller.
        return False
    # Prepare token for the next step.
    token = _first_token(clean)
    # Handle the case where token in SELF_WORDS or token in PERSON_STOP_WORDS or token in....
    if token in SELF_WORDS or token in PERSON_STOP_WORDS or token in ACCOUNT_NAMES:
        # Return False to the caller.
        return False
    # Handle the case where len(clean.split()) > 3.
    if len(clean.split()) > 3:
        # Return False to the caller.
        return False
    return bool(re.search(r"[a-zA-ZÀ-ÿ]", clean))


# Define append unique for callers in this flow.
def _append_unique(items: list[str], value: str) -> None:
    """Coordinate the append unique logic in the NLP/parser layer.

    Args:
        items: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        value: Raw value supplied by the caller.

    Returns:
        `None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Handle the case where value and value not in items.
    if value and value not in items:
        # Update items with the current value.
        items.append(value)


# Define add reason for callers in this flow.
def _add_reason(reasons: list[str], reason: str) -> None:
    """Coordinate the add reason logic in the NLP/parser layer.

    Args:
        reasons: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        reason: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Handle the case where reason and reason not in reasons.
    if reason and reason not in reasons:
        # Update reasons with the current value.
        reasons.append(reason)


# Define extract person candidate for callers in this flow.
def extract_person_candidate(text: str) -> str:
    """Extract the required part of input for person candidate."""
    # Prepare clean for the next step.
    clean = normalize_text(text)

    # Open a multi-line structure for the values below.
    patterns = [
        r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+(?:bayar|byr)\b",
        r"^\s*(?:saya|aku|gw|gue|gua)\s+(?:bayar|byr)\s+(?:ke\s+)?(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
        r"^\s*(?:bayar|byr)\s+(?:ke\s+)?(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
        r"^\s*(?:uang|duit|dana|titipan|cash)\s+(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
        r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+(?:minjem|pinjem|pinjam)\s+uang\s+dari\s+(?:saya|aku|gw|gue|gua)\b",
    # Close the structure that was opened above.
    ]

    # Process each pattern in the current collection.
    for pattern in patterns:
        # Prepare match for the next step.
        match = re.search(pattern, clean, flags=re.IGNORECASE)
        # Handle the missing or empty match case.
        if not match:
            # Skip the rest of this loop iteration after handling this case.
            continue
        person = re.sub(r"\s+", " ", match.group("person")).strip()
        # Handle the case where _looks_like_person(person).
        if _looks_like_person(person):
            # Return person.title() to the caller.
            return person.title()

    return ""


# Define detect pre parse clarification flags for callers in this flow.
def detect_pre_parse_clarification_flags(text: str) -> tuple[list[str], list[str]]:
    """Parse caller input for the detect pre parse clarification flags workflow in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `tuple[list[str], list[str]]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Prepare clean for the next step.
    clean = normalize_text(text)
    # Run this statement as part of the current workflow.
    flags: list[str] = []
    # Run this statement as part of the current workflow.
    reasons: list[str] = []

    # Handle the missing or empty clean or not _has_amount(clean) case.
    if not clean or not _has_amount(clean):
        # Return flags, reasons to the caller.
        return flags, reasons

    # Debt flow section
    # Debt flow section
    if not _has_debt_keyword(clean):
        # Open a multi-line structure for the values below.
        person_pays = re.search(
            r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+(?:bayar|byr)\b(?=.*(?:\d|rp|idr))",
            # Include this value in the surrounding collection or call.
            clean,
            # Prepare flags for the next step.
            flags=re.IGNORECASE,
        # Close the structure that was opened above.
        )
        if person_pays and _looks_like_person(person_pays.group("person")):
            _append_unique(flags, "person_plus_bayar_without_debt_keyword")
            # Open a multi-line structure for the values below.
            _add_reason(
                # Include this value in the surrounding collection or call.
                reasons,
                "Ada nama orang + kata bayar, tapi tidak ada kata hutang/utang/piutang. Ini bisa berarti bayar debt, expense biasa, atau orang lain yang membayar.",
            # Close the structure that was opened above.
            )

        # Open a multi-line structure for the values below.
        self_pays_person = re.search(
            r"^\s*(?:saya|aku|gw|gue|gua)\s+(?:bayar|byr)\s+(?:ke\s+)?(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
            # Include this value in the surrounding collection or call.
            clean,
            # Prepare flags for the next step.
            flags=re.IGNORECASE,
        # Close the structure that was opened above.
        )
        # Open a multi-line structure for the values below.
        direct_pay_person = re.search(
            r"^\s*(?:bayar|byr)\s+(?:ke\s+)?(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
            # Include this value in the surrounding collection or call.
            clean,
            # Prepare flags for the next step.
            flags=re.IGNORECASE,
        # Close the structure that was opened above.
        )
        # Process each match in the current collection.
        for match in (self_pays_person, direct_pay_person):
            if match and _looks_like_person(match.group("person")):
                _append_unique(flags, "person_plus_bayar_without_debt_keyword")
                # Open a multi-line structure for the values below.
                _add_reason(
                    # Include this value in the surrounding collection or call.
                    reasons,
                    "Arah uang pada frasa bayar ke orang belum jelas. Perlu dipilih dulu agar tidak salah mencatat cashflow atau debt.",
                # Close the structure that was opened above.
                )
                # Leave the loop after the target condition has been reached.
                break

    # 2) Ambiguous money direction.
    ambiguous_money = re.search(
        r"^\s*(?:uang|duit|dana|titipan|cash)\s+(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    if ambiguous_money and _looks_like_person(ambiguous_money.group("person")):
        _append_unique(flags, "ambiguous_money_direction")
        # Open a multi-line structure for the values below.
        _add_reason(
            # Include this value in the surrounding collection or call.
            reasons,
            "Ada kata uang/titipan/cash + nama orang, tapi arah uangnya belum jelas.",
        # Close the structure that was opened above.
        )

    # Open a multi-line structure for the values below.
    borrow_from_self = re.search(
        r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+(?:minjem|pinjem|pinjam)\s+uang\s+dari\s+(?:saya|aku|gw|gue|gua)\b",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    if borrow_from_self and _looks_like_person(borrow_from_self.group("person")):
        _append_unique(flags, "ambiguous_money_direction")
        # Open a multi-line structure for the values below.
        _add_reason(
            # Include this value in the surrounding collection or call.
            reasons,
            "Frasa pinjam uang dari saya sengaja diklarifikasi agar tidak salah arah hutang/piutang.",
        # Close the structure that was opened above.
        )

    # Account flow section
    if re.search(rf"\bsaldo\s+({ACCOUNT_PATTERN})\b", clean, flags=re.IGNORECASE) and re.search(r"\b(?:minus|-)?\s*(?:\d|rp|idr)", clean):
        _append_unique(flags, "balance_or_set_balance_intent")
        # Open a multi-line structure for the values below.
        _add_reason(
            # Include this value in the surrounding collection or call.
            reasons,
            "Input terlihat seperti ingin set/cek saldo rekening, bukan transaksi expense biasa.",
        # Close the structure that was opened above.
        )

    # Pending expense section
    has_future_period = _has_future_or_billing_period(clean)
    first_tokens = " ".join(clean.split()[:3])
    # Prepare has explicit pending for the next step.
    has_explicit_pending = any(_contains_phrase_or_word(first_tokens, keyword) for keyword in PENDING_EXPLICIT_KEYWORDS)
    # Prepare has past or actual for the next step.
    has_past_or_actual = _has_past_or_actual_keyword(clean)
    # Handle the case where has_future_period and not has_explicit_pending and not has_pa....
    if has_future_period and not has_explicit_pending and not has_past_or_actual:
        # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
        _append_unique(flags, "possible_pending_expense")
        # Open a multi-line structure for the values below.
        _add_reason(
            # Include this value in the surrounding collection or call.
            reasons,
            "Ada periode tagihan/masa depan, tapi belum jelas apakah sudah dibayar atau baru rencana/pending.",
        # Close the structure that was opened above.
        )

    # 7) Non-standard split that is too ambiguous.
    if re.search(r"\bbareng\s+[a-zA-ZÀ-ÿ]+\b", clean) and not re.search(r"\b(?:dibagi|di\s*-?\s*bagi|bagi|split|share|patungan|berdua|bertiga|berempat)\b", clean):
        _append_unique(flags, "possible_split_not_attached")
        # Open a multi-line structure for the values below.
        _add_reason(
            # Include this value in the surrounding collection or call.
            reasons,
            "Ada kata bareng + nama orang, tapi belum jelas apakah ini split bill atau hanya catatan.",
        # Close the structure that was opened above.
        )

    # Return flags, reasons to the caller.
    return flags, reasons


# Define detect post parse flags for callers in this flow.
def detect_post_parse_flags(text: str, parsed: dict[str, Any] | None) -> tuple[list[str], list[str], list[str], list[str]]:
    """Parse caller input for the detect post parse flags workflow in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `tuple[list[str], list[str], list[str], list[str]]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Prepare clean for the next step.
    clean = normalize_text(text)
    # Prepare parsed for the next step.
    parsed = parsed or {}
    # Run this statement as part of the current workflow.
    info_flags: list[str] = []
    # Run this statement as part of the current workflow.
    warning_flags: list[str] = []
    # Run this statement as part of the current workflow.
    gemini_flags: list[str] = []
    # Run this statement as part of the current workflow.
    reasons: list[str] = []

    txn_type = str(parsed.get("type") or "").strip().lower()
    category = str(parsed.get("category") or "").strip()
    parsed_by = str(parsed.get("parsed_by") or "").strip().lower()

    # Debt flow section
    topup_match = re.search(
        r"\b(?:top\s*up|topup|isi|ngisi)\s+(?P<target>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,25}?)(?=\s*(?:\d|rp|idr|dari|pakai|pake|via|ke|$))",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where topup_match.
    if topup_match:
        target = re.sub(r"\s+", " ", topup_match.group("target")).strip().lower()
        # Prepare target first for the next step.
        target_first = _first_token(target)
        if target_first and target_first not in ACCOUNT_NAMES and not re.search(rf"^({ACCOUNT_PATTERN})$", target, flags=re.IGNORECASE):
            _append_unique(info_flags, "topup_non_wallet_target")
            # Handle the case where any(keyword in target for keyword in AI_REVIEW_TOPUP_TARGETS).
            if any(keyword in target for keyword in AI_REVIEW_TOPUP_TARGETS):
                _append_unique(gemini_flags, "topup_non_wallet_target")
                # Open a multi-line structure for the values below.
                _add_reason(
                    # Include this value in the surrounding collection or call.
                    reasons,
                    "Top up ke target non-wallet seperti game/ML seharusnya menjadi expense, bukan transfer. Draft perlu dicek.",
                # Close the structure that was opened above.
                )
            # Handle the alternate case where target_first in CLEAR_TOPUP_EXPENSE_TARGETS.
            elif target_first in CLEAR_TOPUP_EXPENSE_TARGETS:
                # Open a multi-line structure for the values below.
                _add_reason(
                    # Include this value in the surrounding collection or call.
                    reasons,
                    "Isi/top up ke target non-wallet yang jelas akan diperlakukan sebagai expense, bukan transfer.",
                # Close the structure that was opened above.
                )
            # Handle the fallback path after earlier conditions are skipped.
            else:
                _append_unique(warning_flags, "topup_non_wallet_target")
                # Open a multi-line structure for the values below.
                _add_reason(
                    # Include this value in the surrounding collection or call.
                    reasons,
                    "Isi/top up ke target non-wallet perlu dicek agar tidak salah dianggap transfer.",
                # Close the structure that was opened above.
                )

    # Account flow section
    has_account_to_account_without_keyword = (
        re.search(rf"\b({ACCOUNT_PATTERN})\s+ke\s+({ACCOUNT_PATTERN})\b", clean, flags=re.IGNORECASE)
        and not re.search(r"\b(?:transfer|tf|trf|pindah|move|tarik|setor|top\s*up|topup|isi|ngisi)\b", clean, flags=re.IGNORECASE)
    # Close the structure that was opened above.
    )
    # Handle the case where has_account_to_account_without_keyword.
    if has_account_to_account_without_keyword:
        _append_unique(info_flags, "account_to_account_without_transfer_keyword")
        if txn_type != "transfer":
            _append_unique(warning_flags, "account_to_account_without_transfer_keyword")
            _add_reason(reasons, "Input terlihat seperti rekening ke rekening, tapi parser belum membacanya sebagai transfer.")
        # Handle the fallback path after earlier conditions are skipped.
        else:
            _add_reason(reasons, "Pola rekening ke rekening dikenali sebagai transfer antar rekening.")

    # 6) Transfer alias.
    if re.search(r"\b(?:tf|trf)\b", clean, flags=re.IGNORECASE):
        _append_unique(info_flags, "transfer_alias_detected")
        if txn_type != "transfer" and _has_account(clean):
            _append_unique(warning_flags, "transfer_alias_detected")
            _add_reason(reasons, "Alias tf/trf terdeteksi, tapi hasil parser belum berupa transfer.")
        # Handle the fallback path after earlier conditions are skipped.
        else:
            _add_reason(reasons, "Alias tf/trf dikenali sebagai transfer.")

    # Parser rule note for an Indonesian finance input edge case.
    split_word_number = re.search(
        r"\b(?:bagi|dibagi|di\s*-?\s*bagi|patungan|split|share)\s+(?:dua|tiga|empat|lima|enam|berdua|bertiga|berempat)\b|\b(?:berdua|bertiga|berempat)\s+(?:sama|bareng|dengan)\b",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    if split_word_number and txn_type == "expense" and not parsed.get("split_bill"):
        _append_unique(warning_flags, "possible_split_not_attached")
        _add_reason(reasons, "Pola split bill tidak standar terdeteksi, tapi belum menempel sebagai split bill. Cek preview sebelum simpan.")

    # 9) Category uncertainty.
    if any(phrase in clean for phrase in AI_REVIEW_CATEGORY_PHRASES):
        _append_unique(gemini_flags, "category_uncertain")
        _add_reason(reasons, "Ada keyword kategori yang rawan salah, jadi draft perlu dicek sebelum disimpan.")
    elif category in {"Other Expense", "Other Income"} or any(phrase in clean for phrase in WARNING_CATEGORY_PHRASES):
        _append_unique(warning_flags, "category_uncertain")
        _add_reason(reasons, "Kategori masih Other atau keyword rawan salah, jadi hasil parsing perlu dicek.")

    # 10) Income vs expense context conflict.
    if txn_type == "income":
        has_income_keyword = re.search(r"\b(?:refund|cashback|bonus|balik|return|dapat|dapet|terima|masuk)\b", clean)
        # Prepare has expense context for the next step.
        has_expense_context = any(keyword in clean for keyword in EXPENSE_CONTEXT_KEYWORDS)
        # Handle the case where has_income_keyword and has_expense_context.
        if has_income_keyword and has_expense_context:
            _append_unique(gemini_flags, "income_category_conflict")
            # Open a multi-line structure for the values below.
            _add_reason(
                # Include this value in the surrounding collection or call.
                reasons,
                "Input bertipe pemasukan, tapi ada keyword yang biasanya terkait expense/kategori belanja. Draft perlu dicek.",
            # Close the structure that was opened above.
            )

    if parsed_by == "gemini":
        _append_unique(gemini_flags, "gemini_text_parser_used")
        _add_reason(reasons, "Parsing dibuat oleh Gemini, jadi tetap perlu dicek sebelum disimpan.")

    # Return info_flags, warning_flags, gemini_flags, reasons to the caller.
    return info_flags, warning_flags, gemini_flags, reasons


# Fungsi utama parse safety.
# Debt flow section

# Define assess parse safety for callers in this flow.
def assess_parse_safety(text: str, parsed: dict | None) -> dict:
    """Parse caller input for the assess parse safety workflow in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        parsed: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Prepare parsed for the next step.
    parsed = parsed or {}
    # Run this statement as part of the current workflow.
    pre_flags, pre_reasons = detect_pre_parse_clarification_flags(text)
    # Run this statement as part of the current workflow.
    info_flags, warning_flags, gemini_flags, post_reasons = detect_post_parse_flags(text, parsed)

    # Run this statement as part of the current workflow.
    risk_flags: list[str] = []
    # Run this statement as part of the current workflow.
    reasons: list[str] = []
    # Process each flag in the current collection.
    for flag in pre_flags + info_flags + warning_flags + gemini_flags:
        # Run this statement as part of the current workflow.
        _append_unique(risk_flags, flag)
    # Process each reason in the current collection.
    for reason in pre_reasons + post_reasons:
        # Run this statement as part of the current workflow.
        _add_reason(reasons, reason)

    # Handle the case where pre_flags.
    if pre_flags:
        # Prepare action for the next step.
        action = CLARIFICATION
        # Prepare level for the next step.
        level = RISK_HIGH
    # Handle the alternate case where gemini_flags.
    elif gemini_flags:
        # Prepare action for the next step.
        action = GEMINI_DRAFT_PREVIEW
        # Prepare level for the next step.
        level = RISK_MEDIUM
    # Handle the alternate case where warning_flags.
    elif warning_flags:
        # Prepare action for the next step.
        action = WARNING_PREVIEW
        # Prepare level for the next step.
        level = RISK_MEDIUM
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare action for the next step.
        action = NORMAL_PREVIEW
        # Prepare level for the next step.
        level = RISK_LOW

    # Return { to the caller.
    return {
        "recommended_action": action,
        "risk_level": level,
        "risk_flags": risk_flags,
        "reasons": reasons,
    # Close the structure that was opened above.
    }
