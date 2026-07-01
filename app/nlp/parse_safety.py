"""Routing keamanan parsing untuk input finance natural.

Modul ini tidak menyimpan data dan tidak memanggil Gemini. Tugasnya hanya
mengecek teks mentah + hasil parser, lalu memberi rekomendasi apakah input aman
masuk preview normal, perlu warning, perlu draft Gemini, atau harus klarifikasi.
"""

from __future__ import annotations

import re
from typing import Any

from app.nlp.normalizer import extract_amount_from_text, normalize_text
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


def _has_amount(clean: str) -> bool:
    return bool(extract_amount_from_text(clean))


def _has_debt_keyword(clean: str) -> bool:
    return any(keyword in clean for keyword in DEBT_KEYWORDS)


def _has_account(clean: str) -> bool:
    return bool(re.search(rf"\b({ACCOUNT_PATTERN})\b", clean, flags=re.IGNORECASE))


def _first_token(value: str) -> str:
    return str(value or "").strip().split()[0].lower() if str(value or "").strip() else ""


def _looks_like_person(value: str) -> bool:
    clean = re.sub(r"[^a-zA-ZÀ-ÿ\s]", " ", str(value or "").lower())
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return False
    token = _first_token(clean)
    if token in SELF_WORDS or token in PERSON_STOP_WORDS or token in ACCOUNT_NAMES:
        return False
    if len(clean.split()) > 3:
        return False
    return bool(re.search(r"[a-zA-ZÀ-ÿ]", clean))


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _add_reason(reasons: list[str], reason: str) -> None:
    if reason and reason not in reasons:
        reasons.append(reason)


def extract_person_candidate(text: str) -> str:
    """Ambil kandidat nama orang untuk callback klarifikasi secara best-effort."""
    clean = normalize_text(text)

    patterns = [
        r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+(?:bayar|byr)\b",
        r"^\s*(?:saya|aku|gw|gue|gua)\s+(?:bayar|byr)\s+(?:ke\s+)?(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
        r"^\s*(?:bayar|byr)\s+(?:ke\s+)?(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
        r"^\s*(?:uang|duit|dana|titipan|cash)\s+(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)(?=\s*(?:\d|rp|idr))",
        r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+(?:minjem|pinjem|pinjam)\s+uang\s+dari\s+(?:saya|aku|gw|gue|gua)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, clean, flags=re.IGNORECASE)
        if not match:
            continue
        person = re.sub(r"\s+", " ", match.group("person")).strip()
        if _looks_like_person(person):
            return person.title()

    return ""


def detect_pre_parse_clarification_flags(text: str) -> tuple[list[str], list[str]]:
    """Deteksi risk flags yang wajib ditangkap sebelum debt parser/transaksi jalan."""
    clean = normalize_text(text)
    flags: list[str] = []
    reasons: list[str] = []

    if not clean or not _has_amount(clean):
        return flags, reasons

    # 1) Nama orang + bayar + nominal tanpa keyword hutang/piutang.
    #    Ini ambigu karena bisa berarti debt payment, expense biasa, atau orang lain yang membayar.
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
        for match in (self_pays_person, direct_pay_person):
            if match and _looks_like_person(match.group("person")):
                _append_unique(flags, "person_plus_bayar_without_debt_keyword")
                _add_reason(
                    reasons,
                    "Arah uang pada frasa bayar ke orang belum jelas. Perlu dipilih dulu agar tidak salah mencatat cashflow atau debt.",
                )
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

    # 3) Intent cek/set saldo. Jangan sampai diparse sebagai expense biasa.
    if re.search(rf"\bsaldo\s+({ACCOUNT_PATTERN})\b", clean, flags=re.IGNORECASE) and re.search(r"\b(?:minus|-)?\s*(?:\d|rp|idr)", clean):
        _append_unique(flags, "balance_or_set_balance_intent")
        _add_reason(
            reasons,
            "Input terlihat seperti ingin set/cek saldo rekening, bukan transaksi expense biasa.",
        )

    # 8) Possible pending expense / billing period.
    has_future_period = any(keyword in clean for keyword in FUTURE_OR_BILLING_PERIOD_KEYWORDS)
    has_explicit_pending = any(keyword in clean.split()[:3] for keyword in PENDING_EXPLICIT_KEYWORDS)
    has_past_or_actual = any(keyword in clean for keyword in PAST_OR_ACTUAL_KEYWORDS)
    if has_future_period and not has_explicit_pending and not has_past_or_actual:
        # Jangan blokir laporan/pertanyaan yang tidak punya nominal.
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


def detect_post_parse_flags(text: str, parsed: dict[str, Any] | None) -> tuple[list[str], list[str], list[str], list[str]]:
    """Kembalikan tuple: info_flags, warning_flags, gemini_flags, dan reasons."""
    clean = normalize_text(text)
    parsed = parsed or {}
    info_flags: list[str] = []
    warning_flags: list[str] = []
    gemini_flags: list[str] = []
    reasons: list[str] = []

    txn_type = str(parsed.get("type") or "").strip().lower()
    category = str(parsed.get("category") or "").strip()
    parsed_by = str(parsed.get("parsed_by") or "").strip().lower()

    # 4) topup/isi non-wallet target. Parser seharusnya mengklasifikasikan target non-wallet yang jelas sebagai expense.
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
            if any(keyword in target for keyword in AI_REVIEW_TOPUP_TARGETS):
                _append_unique(gemini_flags, "topup_non_wallet_target")
                _add_reason(
                    reasons,
                    "Top up ke target non-wallet seperti game/ML seharusnya menjadi expense, bukan transfer. Draft perlu dicek.",
                )
            elif target_first in CLEAR_TOPUP_EXPENSE_TARGETS:
                _add_reason(
                    reasons,
                    "Isi/top up ke target non-wallet yang jelas akan diperlakukan sebagai expense, bukan transfer.",
                )
            else:
                _append_unique(warning_flags, "topup_non_wallet_target")
                _add_reason(
                    reasons,
                    "Isi/top up ke target non-wallet perlu dicek agar tidak salah dianggap transfer.",
                )

    # 5) Rekening ke rekening tanpa kata transfer. Jika parser sudah berhasil menjadi transfer, cukup jadi info.
    has_account_to_account_without_keyword = (
        re.search(rf"\b({ACCOUNT_PATTERN})\s+ke\s+({ACCOUNT_PATTERN})\b", clean, flags=re.IGNORECASE)
        and not re.search(r"\b(?:transfer|tf|trf|pindah|move|tarik|setor|top\s*up|topup|isi|ngisi)\b", clean, flags=re.IGNORECASE)
    )
    if has_account_to_account_without_keyword:
        _append_unique(info_flags, "account_to_account_without_transfer_keyword")
        if txn_type != "transfer":
            _append_unique(warning_flags, "account_to_account_without_transfer_keyword")
            _add_reason(reasons, "Input terlihat seperti rekening ke rekening, tapi parser belum membacanya sebagai transfer.")
        else:
            _add_reason(reasons, "Pola rekening ke rekening dikenali sebagai transfer antar rekening.")

    # 6) Transfer alias.
    if re.search(r"\b(?:tf|trf)\b", clean, flags=re.IGNORECASE):
        _append_unique(info_flags, "transfer_alias_detected")
        if txn_type != "transfer" and _has_account(clean):
            _append_unique(warning_flags, "transfer_alias_detected")
            _add_reason(reasons, "Alias tf/trf terdeteksi, tapi hasil parser belum berupa transfer.")
        else:
            _add_reason(reasons, "Alias tf/trf dikenali sebagai transfer.")

    # 7) Pola split dengan angka kata yang belum menempel ke field split_bill.
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
        has_expense_context = any(keyword in clean for keyword in EXPENSE_CONTEXT_KEYWORDS)
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
# Urutan prioritas sengaja konservatif: klarifikasi > Gemini draft > warning > preview normal.

def assess_parse_safety(text: str, parsed: dict | None) -> dict:
    """Nilai keamanan hasil parsing dan tentukan aksi routing.

    Output utama:
    - recommended_action: normal_preview | warning_preview | gemini_draft_preview | clarification
    - risk_level: low | medium | high
    - risk_flags: daftar flag risiko yang terdeteksi
    - reasons: alasan singkat yang bisa ditampilkan ke user
    """
    parsed = parsed or {}
    pre_flags, pre_reasons = detect_pre_parse_clarification_flags(text)
    info_flags, warning_flags, gemini_flags, post_reasons = detect_post_parse_flags(text, parsed)

    risk_flags: list[str] = []
    reasons: list[str] = []
    for flag in pre_flags + info_flags + warning_flags + gemini_flags:
        _append_unique(risk_flags, flag)
    for reason in pre_reasons + post_reasons:
        _add_reason(reasons, reason)

    if pre_flags:
        action = CLARIFICATION
        level = RISK_HIGH
    elif gemini_flags:
        action = GEMINI_DRAFT_PREVIEW
        level = RISK_MEDIUM
    elif warning_flags:
        action = WARNING_PREVIEW
        level = RISK_MEDIUM
    else:
        action = NORMAL_PREVIEW
        level = RISK_LOW

    return {
        "recommended_action": action,
        "risk_level": level,
        "risk_flags": risk_flags,
        "reasons": reasons,
    }
