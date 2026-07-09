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
DEBT_KEYWORDS = {
    "hutang", "utang", "piutang", "debt", "cicil", "nyicil", "cicilan",
    "lunas", "lunasi", "lunasin", "melunasi", "bayar hutang", "bayar utang",
    "kembaliin", "balikin", "dibalikin", "transfer balik",
}

PERSON_STOP_WORDS = {
    "makan", "makanan", "minum", "kopi", "nasi", "parkir", "listrik", "wifi",
    "internet", "pulsa", "bensin", "bbm", "kos", "kost", "kontrakan", "shopee",
    "tokopedia", "gojek", "grab", "gopay", "dana", "bri", "bca", "bsi", "cash",
    "seabank", "bayar", "beli", "ke", "dari", "pakai", "pake", "via",
    "nanti", "akan", "bakal", "rencana", "planning", "tagihan", "bulan",
}

CLEAR_TOPUP_EXPENSE_TARGETS = {
    "bensin", "bbm", "pertalite", "pertamax", "solar",
    "pulsa", "paket", "data", "token", "listrik",
}

AI_REVIEW_TOPUP_TARGETS = {
    "game", "ml", "mobile", "legend", "mobile legend", "steam",
}

EXPENSE_CONTEXT_KEYWORDS = {
    "shopee", "tokopedia", "lazada", "gojek", "grab", "pulsa", "paket data",
    "makan", "makanan", "minum", "kopi", "donat", "bensin", "parkir", "game",
    "ml", "listrik", "wifi", "kos", "laundry", "laundri",
}

AI_REVIEW_CATEGORY_PHRASES = {
    "makanan ikan", "pakan ikan", "pakan kucing", "makanan kucing",
}

WARNING_CATEGORY_PHRASES = {
    "donat qq", "laundri",
}

FUTURE_OR_BILLING_PERIOD_KEYWORDS = {
    "bulan depan", "minggu depan", "pekan depan", "semester depan", "tahun depan",
    "akhir bulan", "januari", "februari", "maret", "april",
    "mei", "juni", "juli", "agustus", "september", "oktober", "november",
    "desember", "jan", "feb", "mar", "apr", "jun", "jul", "agus", "agt",
    "sep", "okt", "nov", "des",
}

PENDING_EXPLICIT_KEYWORDS = {
    "pending", "rencana", "planning", "plan", "nanti", "akan", "bakal",
    "perlu", "butuh", "kudu", "harus",
}

PAST_OR_ACTUAL_KEYWORDS = {
    "sudah", "udah", "sdh", "barusan", "tadi", "kemarin", "baru aja",
    "telah", "dibayar", "lunas",
}


# Helper for contains phrase or word.
def _contains_phrase_or_word(clean: str, keyword: str) -> bool:
    """Return True only when a keyword appears as a full word or phrase.

    This prevents short month aliases such as `jan` from matching inside words
    like `jajan`.
    """
    key = re.escape(str(keyword or "").strip().lower())
    # Validate missing key before continuing.
    if not key:
        return False
    key = key.replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![a-zA-ZÀ-ÿ]){key}(?![a-zA-ZÀ-ÿ])", clean, flags=re.IGNORECASE))


# Helper for has future or billing period.
def _has_future_or_billing_period(clean: str) -> bool:
    """Detect future/billing period keywords without substring false positives."""
    return any(_contains_phrase_or_word(clean, keyword) for keyword in FUTURE_OR_BILLING_PERIOD_KEYWORDS)


# Helper for has past or actual keyword.
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
    return any(_contains_phrase_or_word(clean, keyword) for keyword in PAST_OR_ACTUAL_KEYWORDS)


# Helper for has amount.
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
    return bool(extract_amount_from_text(clean))


# Helper for has debt keyword.
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
    return any(keyword in clean for keyword in DEBT_KEYWORDS)


# Helper for has account.
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


# Helper for first token.
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


# Helper for looks like person.
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
    # Validate missing clean before continuing.
    if not clean:
        return False
    token = _first_token(clean)
    # Handle token in SELF WORDS or token in PERSON STOP WORDS or token in.
    if token in SELF_WORDS or token in PERSON_STOP_WORDS or token in ACCOUNT_NAMES:
        return False
    if len(clean.split()) > 3:
        return False
    return bool(re.search(r"[a-zA-ZÀ-ÿ]", clean))


# Helper for append unique.
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
    if value and value not in items:
        # Append the current value to items.
        items.append(value)


# Helper for add reason.
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
    if reason and reason not in reasons:
        # Append the current value to reasons.
        reasons.append(reason)


# Helper for extract person candidate.
def extract_person_candidate(text: str) -> str:
    """Extract the required part of input for person candidate."""
    # Normalize clean before matching.
    clean = normalize_text(text)

    patterns = [
        r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+(?:bayar|byr)\b",
        r"^\s*(?:saya|aku|gw|gue|gua)\s+(?:bayar|byr)\s+(?:ke\s+)?(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
        r"^\s*(?:bayar|byr)\s+(?:ke\s+)?(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
        r"^\s*(?:uang|duit|dana|titipan|cash)\s+(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
        r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+(?:minjem|pinjem|pinjam)\s+uang\s+dari\s+(?:saya|aku|gw|gue|gua)\b",
    ]

    # Iterate through each pattern.
    for pattern in patterns:
        match = re.search(pattern, clean, flags=re.IGNORECASE)
        # Validate missing match before continuing.
        if not match:
            # Skip the rest of this loop iteration after handling this case.
            continue
        person = re.sub(r"\s+", " ", match.group("person")).strip()
        if _looks_like_person(person):
            return person.title()

    return ""


# Helper for detect pre parse clarification flags.
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
    # Normalize clean before matching.
    clean = normalize_text(text)
    flags: list[str] = []
    reasons: list[str] = []

    # Validate missing clean or not has amount(clean) before continuing.
    if not clean or not _has_amount(clean):
        return flags, reasons

    if not _has_debt_keyword(clean):
        person_pays = re.search(
            r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+(?:bayar|byr)\b(?=.*(?:\d|rp|idr))",
            clean,
            flags=re.IGNORECASE,
        )
        if person_pays and _looks_like_person(person_pays.group("person")):
            _append_unique(flags, "person_plus_bayar_without_debt_keyword")
            _add_reason(
                reasons,
                "Ada nama orang + kata bayar, tapi tidak ada kata hutang/utang/piutang. Ini bisa berarti bayar debt, expense biasa, atau orang lain yang membayar.",
            )

        self_pays_person = re.search(
            r"^\s*(?:saya|aku|gw|gue|gua)\s+(?:bayar|byr)\s+(?:ke\s+)?(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
            clean,
            flags=re.IGNORECASE,
        )
        direct_pay_person = re.search(
            r"^\s*(?:bayar|byr)\s+(?:ke\s+)?(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
            clean,
            flags=re.IGNORECASE,
        )
        # Iterate through each match.
        for match in (self_pays_person, direct_pay_person):
            if match and _looks_like_person(match.group("person")):
                _append_unique(flags, "person_plus_bayar_without_debt_keyword")
                _add_reason(
                    reasons,
                    "Arah uang pada frasa bayar ke orang belum jelas. Perlu dipilih dulu agar tidak salah mencatat cashflow atau debt.",
                )
                # Leave the loop after the target condition has been reached.
                break

    # 2) Ambiguous money direction.
    ambiguous_money = re.search(
        r"^\s*(?:uang|duit|dana|titipan|cash)\s+(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
        clean,
        flags=re.IGNORECASE,
    )
    if ambiguous_money and _looks_like_person(ambiguous_money.group("person")):
        _append_unique(flags, "ambiguous_money_direction")
        _add_reason(
            reasons,
            "Ada kata uang/titipan/cash + nama orang, tapi arah uangnya belum jelas.",
        )

    borrow_from_self = re.search(
        r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+(?:minjem|pinjem|pinjam)\s+uang\s+dari\s+(?:saya|aku|gw|gue|gua)\b",
        clean,
        flags=re.IGNORECASE,
    )
    if borrow_from_self and _looks_like_person(borrow_from_self.group("person")):
        _append_unique(flags, "ambiguous_money_direction")
        _add_reason(
            reasons,
            "Frasa pinjam uang dari saya sengaja diklarifikasi agar tidak salah arah hutang/piutang.",
        )

    # Account flow section
    if re.search(rf"\bsaldo\s+({ACCOUNT_PATTERN})\b", clean, flags=re.IGNORECASE) and re.search(r"\b(?:minus|-)?\s*(?:\d|rp|idr)", clean):
        _append_unique(flags, "balance_or_set_balance_intent")
        _add_reason(
            reasons,
            "Input terlihat seperti ingin set/cek saldo rekening, bukan transaksi expense biasa.",
        )

    # Pending expense section
    has_future_period = _has_future_or_billing_period(clean)
    first_tokens = " ".join(clean.split()[:3])
    has_explicit_pending = any(_contains_phrase_or_word(first_tokens, keyword) for keyword in PENDING_EXPLICIT_KEYWORDS)
    has_past_or_actual = _has_past_or_actual_keyword(clean)
    # Handle has future period and not has explicit pending and not has pa.
    if has_future_period and not has_explicit_pending and not has_past_or_actual:
        # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
        _append_unique(flags, "possible_pending_expense")
        _add_reason(
            reasons,
            "Ada periode tagihan/masa depan, tapi belum jelas apakah sudah dibayar atau baru rencana/pending.",
        )

    # 7) Non-standard split that is too ambiguous.
    if re.search(r"\bbareng\s+[a-zA-ZÀ-ÿ]+\b", clean) and not re.search(r"\b(?:dibagi|di\s*-?\s*bagi|bagi|split|share|patungan|berdua|bertiga|berempat)\b", clean):
        _append_unique(flags, "possible_split_not_attached")
        _add_reason(
            reasons,
            "Ada kata bareng + nama orang, tapi belum jelas apakah ini split bill atau hanya catatan.",
        )

    return flags, reasons


# Helper for detect post parse flags.
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
    # Normalize clean before matching.
    clean = normalize_text(text)
    parsed = parsed or {}
    info_flags: list[str] = []
    warning_flags: list[str] = []
    gemini_flags: list[str] = []
    reasons: list[str] = []

    txn_type = str(parsed.get("type") or "").strip().lower()
    category = str(parsed.get("category") or "").strip()
    parsed_by = str(parsed.get("parsed_by") or "").strip().lower()

    topup_match = re.search(
        r"\b(?:top\s*up|topup|isi|ngisi)\s+(?P<target>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,25}?)(?=\s*(?:\d|rp|idr|dari|pakai|pake|via|ke|$))",
        clean,
        flags=re.IGNORECASE,
    )
    if topup_match:
        target = re.sub(r"\s+", " ", topup_match.group("target")).strip().lower()
        target_first = _first_token(target)
        if target_first and target_first not in ACCOUNT_NAMES and not re.search(rf"^({ACCOUNT_PATTERN})$", target, flags=re.IGNORECASE):
            _append_unique(info_flags, "topup_non_wallet_target")
            # Handle any(keyword in target for keyword in AI REVIEW TOPUP TARGETS).
            if any(keyword in target for keyword in AI_REVIEW_TOPUP_TARGETS):
                _append_unique(gemini_flags, "topup_non_wallet_target")
                _add_reason(
                    reasons,
                    "Top up ke target non-wallet seperti game/ML seharusnya menjadi expense, bukan transfer. Draft perlu dicek.",
                )
            # Fall back when target first in CLEAR TOPUP EXPENSE TARGETS.
            elif target_first in CLEAR_TOPUP_EXPENSE_TARGETS:
                _add_reason(
                    reasons,
                    "Isi/top up ke target non-wallet yang jelas akan diperlakukan sebagai expense, bukan transfer.",
                )
            # Use the fallback path when no earlier branch matched.
            else:
                _append_unique(warning_flags, "topup_non_wallet_target")
                _add_reason(
                    reasons,
                    "Isi/top up ke target non-wallet perlu dicek agar tidak salah dianggap transfer.",
                )

    # Account flow section
    has_account_to_account_without_keyword = (
        re.search(rf"\b({ACCOUNT_PATTERN})\s+ke\s+({ACCOUNT_PATTERN})\b", clean, flags=re.IGNORECASE)
        and not re.search(r"\b(?:transfer|tf|trf|pindah|move|tarik|setor|top\s*up|topup|isi|ngisi)\b", clean, flags=re.IGNORECASE)
    )
    if has_account_to_account_without_keyword:
        _append_unique(info_flags, "account_to_account_without_transfer_keyword")
        if txn_type != "transfer":
            _append_unique(warning_flags, "account_to_account_without_transfer_keyword")
            _add_reason(reasons, "Input terlihat seperti rekening ke rekening, tapi parser belum membacanya sebagai transfer.")
        # Use the fallback path when no earlier branch matched.
        else:
            _add_reason(reasons, "Pola rekening ke rekening dikenali sebagai transfer antar rekening.")

    # 6) Transfer alias.
    if re.search(r"\b(?:tf|trf)\b", clean, flags=re.IGNORECASE):
        _append_unique(info_flags, "transfer_alias_detected")
        if txn_type != "transfer" and _has_account(clean):
            _append_unique(warning_flags, "transfer_alias_detected")
            _add_reason(reasons, "Alias tf/trf terdeteksi, tapi hasil parser belum berupa transfer.")
        # Use the fallback path when no earlier branch matched.
        else:
            _add_reason(reasons, "Alias tf/trf dikenali sebagai transfer.")

    split_word_number = re.search(
        r"\b(?:bagi|dibagi|di\s*-?\s*bagi|patungan|split|share)\s+(?:dua|tiga|empat|lima|enam|berdua|bertiga|berempat)\b|\b(?:berdua|bertiga|berempat)\s+(?:sama|bareng|dengan)\b",
        clean,
        flags=re.IGNORECASE,
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
        # Prepare has expense context from the incoming input.
        has_expense_context = any(keyword in clean for keyword in EXPENSE_CONTEXT_KEYWORDS)
        # Handle has income keyword and has expense context.
        if has_income_keyword and has_expense_context:
            _append_unique(gemini_flags, "income_category_conflict")
            _add_reason(
                reasons,
                "Input bertipe pemasukan, tapi ada keyword yang biasanya terkait expense/kategori belanja. Draft perlu dicek.",
            )

    if parsed_by == "gemini":
        _append_unique(gemini_flags, "gemini_text_parser_used")
        _add_reason(reasons, "Parsing dibuat oleh Gemini, jadi tetap perlu dicek sebelum disimpan.")

    return info_flags, warning_flags, gemini_flags, reasons


# Fungsi utama parse safety.

# Helper for assess parse safety.
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
    parsed = parsed or {}
    pre_flags, pre_reasons = detect_pre_parse_clarification_flags(text)
    info_flags, warning_flags, gemini_flags, post_reasons = detect_post_parse_flags(text, parsed)

    risk_flags: list[str] = []
    reasons: list[str] = []
    # Iterate through each flag.
    for flag in pre_flags + info_flags + warning_flags + gemini_flags:
        _append_unique(risk_flags, flag)
    # Iterate through each reason.
    for reason in pre_reasons + post_reasons:
        _add_reason(reasons, reason)

    if pre_flags:
        action = CLARIFICATION
        level = RISK_HIGH
    # Fall back when gemini flags.
    elif gemini_flags:
        action = GEMINI_DRAFT_PREVIEW
        level = RISK_MEDIUM
    # Fall back when warning flags.
    elif warning_flags:
        action = WARNING_PREVIEW
        level = RISK_MEDIUM
    # Use the fallback path when no earlier branch matched.
    else:
        action = NORMAL_PREVIEW
        level = RISK_LOW

    return {
        "recommended_action": action,
        "risk_level": level,
        "risk_flags": risk_flags,
        "reasons": reasons,
    }
