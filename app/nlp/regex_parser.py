"""Rule-based parser for expenses, income, transfers, debt, split bill, pending expenses, dates, amounts, categories, and accounts."""


# Import re for this module's local operations.
import calendar
import re
# Import dataclass for structured date detection results.
from dataclasses import dataclass
# Import datetime so this module can use its helpers.
from datetime import datetime, timedelta
from app.clock import business_now
# Import app.nlp.normalizer so this module can use its helpers.
from app.nlp.normalizer import extract_amount_from_text, normalize_text


# ── Keyword maps ──────────────────────────────────────────────────────────────

EXPENSE_KEYWORDS = [
    "beli", "bayar", "bayarin", "byr", "makan", "minum", "jajan",
    "belanja", "isi", "ngisi", "top up", "topup", "transfer ke", "kirim ke",
    "servis", "service", "langganan", "subscribe", "sewa", "parkir",
    "bensin", "bbm", "pertalite", "pertamax", "solar",
    "nonton", "main", "game", "beli tiket", "tiket",
    "obat", "dokter", "klinik", "apotek",
    "pulsa", "paket data", "token listrik", "listrik", "pdam", "air",
    "potong rambut", "cukur", "laundry",
    "kos", "kontrakan", "sewa kos",
    "zakat", "sedekah", "infaq", "wakaf", "donasi",
    "nabung", "investasi", "setor",
]

INCOME_KEYWORDS = [
    "gaji", "salary", "upah", "honor", "honorarium",
    "dapat", "terima", "dapet", "masuk", "cair",
    "freelance", "proyek", "project", "fee", "komisi",
    "dividen", "return", "hasil", "untung", "profit",
    "bonus", "thr", "cashback", "refund", "balik",
    "transferan masuk", "kiriman",
]

TRANSFER_KEYWORDS = [
    "transfer", "pindah", "move", "tarik tunai", "tarik",
    "setor tunai", "setor ke", "isi", "ngisi", "top up", "topup",
    "tf", "trf",
]

ACCOUNT_NAMES = ["cash", "bri", "bsi", "bca", "dana", "gopay", "seabank", "sea bank"]
ACCOUNT_DISPLAY_NAMES = {
    "cash": "Cash",
    "bri": "BRI",
    "bsi": "BSI",
    "bca": "BCA",
    "dana": "DANA",
    "gopay": "GoPay",
    "seabank": "Seabank",
    "sea bank": "Seabank",
}


# Helper for display account name.
def display_account_name(account: str) -> str:
    """Coordinate the display account name logic in the NLP/parser layer.

    Args:
        account: Account name or account-like value from user input or sheet data.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    return ACCOUNT_DISPLAY_NAMES.get(account, account.upper() if account != "cash" else "Cash")


# Helper for get runtime account snapshot.
def get_runtime_account_snapshot() -> tuple[tuple[str, ...], bool]:
    """Return one account-name snapshot and whether its external source was trustworthy."""
    try:
        from app.services.resolver_service import get_account_names_snapshot

        names, source_available = get_account_names_snapshot()
    except Exception:
        names, source_available = [], False

    clean_names = []
    for name in names or []:
        clean = str(name or "").strip()
        if clean and clean not in clean_names:
            clean_names.append(clean)

    if not clean_names:
        clean_names = [ACCOUNT_DISPLAY_NAMES.get(acc, acc.title()) for acc in ACCOUNT_NAMES if acc != "sea bank"]

    return tuple(clean_names), bool(source_available)


# Helper for get runtime account names.
def get_runtime_account_names() -> list[str]:
    """Return account names while preserving the parser's legacy list-only API."""
    names, _ = get_runtime_account_snapshot()
    return list(names)


# Helper for account pattern from sheet.
def _account_pattern_from_sheet(runtime_account_names: list[str] | tuple[str, ...] | None = None) -> str:
    """Build an account regex pattern from one runtime-account snapshot."""
    names = list(runtime_account_names if runtime_account_names is not None else get_runtime_account_names())
    variants = set()

    # Iterate through each name.
    for name in names:
        # Normalize clean before matching.
        clean = normalize_text(name)
        if clean:
            variants.add(re.escape(clean).replace(r"\ ", r"\s+"))
            variants.add(re.escape(clean.replace(" ", "")))

    # Iterate through each account.
    for account in ACCOUNT_NAMES:
        variants.add(re.escape(account).replace(r"\ ", r"\s*"))

    return "|".join(sorted(variants, key=len, reverse=True)) or r"cash|bri|bsi|bca|dana|gopay"


# Helper for display runtime account name.
def _is_runtime_account_name(raw: str | None, runtime_account_names: list[str] | tuple[str, ...] | None = None) -> bool:
    """Return True when ``raw`` exactly names a known built-in or runtime account.

    Matching follows the same normalized/compact semantics used by the parser's
    account resolver so multiword and sheet-backed account names are not
    mistaken for people by earlier intent-classification branches.
    """
    if not raw:
        return False

    clean = normalize_text(raw)
    compact = clean.replace(" ", "")
    names = runtime_account_names if runtime_account_names is not None else get_runtime_account_names()
    candidates = [*names, *ACCOUNT_NAMES]
    for name in candidates:
        name_clean = normalize_text(name)
        if clean == name_clean or compact == name_clean.replace(" ", ""):
            return True
    return False


def _display_runtime_account_name(raw: str | None, runtime_account_names: list[str] | tuple[str, ...] | None = None) -> str | None:
    """Resolve a regex account match into the display name from sheet accounts."""
    # Validate missing raw before continuing.
    if not raw:
        return None

    # Normalize clean before matching.
    clean = normalize_text(raw)
    compact = clean.replace(" ", "")

    names = runtime_account_names if runtime_account_names is not None else get_runtime_account_names()

    # Iterate through each name.
    for name in names:
        # Normalize name clean before matching.
        name_clean = normalize_text(name)
        if clean == name_clean or compact == name_clean.replace(" ", ""):
            return name

    if clean == "sea bank":
        clean = "sea bank"
    return display_account_name(clean)



# Helper for extract debt account.
def extract_debt_account(text: str) -> str | None:
    """Extract account for debt/talangin flows using explicit account markers."""
    # Normalize text lower before matching.
    text_lower = normalize_text(text)
    # Extract account pattern for validation.
    account_pattern = _account_pattern_from_sheet()
    marker_match = re.search(
        rf"\b(?:dari|ke|pakai|pake|via|rekening)\s+({account_pattern})\b",
        text_lower,
        flags=re.IGNORECASE,
    )
    if marker_match:
        return _display_runtime_account_name(marker_match.group(1))
    return detect_account(text)


# Helper for attach debt account payload.
def attach_debt_account_payload(payload: dict | None, text: str) -> dict | None:
    """Attach detected account to parsed debt payload if available."""
    # Validate missing isinstance(payload, dict) before continuing.
    if not isinstance(payload, dict):
        return payload
    # Extract account for validation.
    account = extract_debt_account(text)
    if account and not payload.get("account"):
        payload["account"] = account
    return payload

CATEGORY_KEYWORDS = {
    "Jajan": [
        "jajan", "ngemil", "cemilan", "camilan", "snack",
        "bakso", "donat", "donut", "cilok", "seblak", "batagor", "siomay",
        "gorengan", "es teh", "es kopi", "jajan pasar",
    ],
    "Food & Beverage": [
        "makan", "minum", "kopi", "coffee", "teh", "jus", "juice",
        "nasi", "ayam", "soto", "mie", "mi", "pizza", "burger",
        "resto", "restoran", "warung",
        "cafe", "kafe", "warteg", "indomaret", "alfamart", "supermarket",
        "beras", "sayur", "buah", "daging", "telur", "susu",
        "galon", "air galon",
    ],
    "Transport": [
        "bensin", "bbm", "pertalite", "pertamax", "solar",
        "grab", "gojek", "ojek", "taksi", "taxi", "angkot", "bus",
        "kereta", "krl", "mrt", "lrt", "tol", "parkir",
        "isi bensin", "isi bbm", "servis motor", "servis mobil",
    ],
    "Bills & Utilities": [
        "listrik", "token", "pdam", "air", "internet", "wifi",
        "pulsa", "paket data", "telpon", "telepon", "tagihan",
        "iuran", "ipkl", "pbb",
    ],
    "Shopping": [
        "beli baju", "baju", "celana", "sepatu", "sandal",
        "shopee", "tokopedia", "lazada", "tiktok shop",
        "elektronik", "hp", "laptop", "charger", "kabel",
        "perabot", "furniture",
    ],
    "Health": [
        "obat", "dokter", "klinik", "puskesmas", "rs", "rumah sakit",
        "apotek", "apotik", "vitamin", "suplemen", "konsultasi",
        "bpjs", "asuransi kesehatan",
    ],
    "Entertainment": [
        "nonton", "bioskop", "cinema", "film", "netflix", "spotify",
        "youtube premium", "game", "steam", "mobile legend", "ml",
        "main", "karaoke", "liburan", "wisata", "hotel",
    ],
    "Education": [
        "buku", "kursus", "les", "pelatihan", "training", "seminar",
        "udemy", "coursera", "kampus", "kuliah", "spp", "ukt",
        "wisuda", "alat tulis", "fotocopy", "print",
    ],
    "Personal Care": [
        "potong rambut", "cukur", "salon", "barbershop",
        "sabun", "sampo", "shampoo", "pasta gigi", "sikat gigi",
        "laundry", "deterjen", "parfum",
    ],
    "Kos & Utilities": [
        "kos", "kontrakan", "sewa", "kost", "indekos",
        "bayar kos", "bayar kontrakan",
    ],
    "Zakat & Sedekah": [
        "zakat", "sedekah", "infaq", "infak", "wakaf",
        "donasi", "sumbangan", "amal",
    ],
    "Investasi": [
        "nabung", "tabungan", "deposito", "investasi",
        "saham", "reksa dana", "reksadana", "crypto",
        "emas", "logam mulia",
    ],
    "Salary": [
        "gaji", "salary", "upah", "thr", "bonus", "honor",
    ],
    "Freelance": [
        "freelance", "proyek", "project", "fee", "komisi", "jasa",
    ],
    "Investment Return": [
        "dividen", "return", "hasil investasi", "untung saham",
        "bunga deposito", "profit",
    ],
}

SPENDING_TYPE_KEYWORDS = {
    "Bulanan": [
        "kos", "kost", "kontrakan", "sewa", "listrik", "token listrik",
        "pdam", "air", "internet", "wifi", "tagihan", "iuran",
        "langganan", "subscribe", "netflix", "spotify", "youtube premium",
        "cicilan", "bpjs", "asuransi",
    ],
    "Darurat": [
        "darurat", "urgent", "mendadak", "obat", "dokter", "klinik",
        "rumah sakit", "rs", "apotek", "tambal ban", "servis mendadak",
        "service mendadak", "rusak", "kecelakaan",
    ],
    "Keinginan": [
        "game", "steam", "skin", "nonton", "bioskop", "cinema",
        "liburan", "wisata", "hotel", "jajan mahal", "nongkrong",
        "baju", "sepatu", "parfum", "aksesoris", "hiburan",
    ],
    "Harian": [
        "makan", "minum", "kopi", "teh", "nasi", "ayam", "jajan",
        "bensin", "bbm", "parkir", "grab", "gojek", "ojek",
        "laundry", "sabun", "sampo", "belanja harian",
    ],
}



DEBT_PAYABLE_KEYWORDS = [
    "hutang ke", "utang ke", "pinjem ke", "pinjam ke",
    "hutang sama", "utang sama",
    "minjem ke",
]

DEBT_RECEIVABLE_KEYWORDS = [
    "piutang ke", "piutang sama", "piutang dari",
    "minjemin", "minjemin ke", "pinjemin", "pinjemin ke", "kasih hutang",
    "pinjem", "pinjam", "minjem",
    "hutangin", "utangin",
]

DEBT_PAYMENT_KEYWORDS = [
    "bayar hutang", "bayar utang", "lunasi", "lunasin",
    "cicil hutang", "cicil utang", "bayar cicilan",
    "transfer balik", "kembaliin", "dibalikin",
]


# Helper for parse debt input.
def parse_debt_input(text: str) -> dict | None:
    """Parse Indonesian debt input into a structured debt payload.

    Args:
        text: Raw Telegram text. The input must contain a debt keyword and a
            nominal amount. Slash commands are ignored because command routing
            owns those messages.

    Returns:
        A dict with fields such as `intent`, `person_name`, `amount`, `date`,
        and `raw_input`, or `None` when the text is not a debt input. Explicit
        `catat utang ke ...` inputs return `cashflow_mode="debt_only"` so the
        bot records the debt without changing any account balance.
    """
    if str(text or "").strip().startswith("/"):
        return None

    # Normalize text lower before matching.
    text_lower = normalize_text(text)

    # Extract amount for validation.
    amount = extract_amount_from_text(text_lower)
    # Validate missing amount before continuing.
    if not amount:
        return None

    self_borrow_match = re.search(
        r"^\s*(?:saya|aku|gw|gue|gua)\s+(?:minjem|pinjem|pinjam)\s+"
        r"(?:uang\s+)?(?:rp\s*)?\d[\d.,]*\s*(?:rb|ribu|k|jt|juta|m)?\s+dari\s+"
        r"(?P<person>[^\d]+?)(?=\s*(?:tanggal|tgl|kemarin|hari\s+ini|$))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if self_borrow_match:
        person = re.sub(r"\s+", " ", self_borrow_match.group("person")).strip().title()
        if person:
            return attach_debt_account_payload({
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            }, text)

    # Helper for extract person after.
    def extract_person_after(text_value: str, keyword: str) -> str | None:
        """Extract the required part of input for person after."""
        if keyword not in text_value:
            return None

        after = text_value.split(keyword)[-1].strip()
        words = []

        stop_words = [
            "rb", "ribu", "k", "jt", "juta", "rupiah",
            "buat", "untuk", "karena", "catatan", "note",
            "ke", "dari", "di", "pakai", "pake",
        ]
        leading_noise = {"uang", "duit", "dana"}

        # Iterate through each w.
        for w in after.split():
            if any(c.isdigit() for c in w):
                # Leave the loop after the target condition has been reached.
                break
            # Validate missing words and w in leading noise before continuing.
            if not words and w in leading_noise:
                # Skip the rest of this loop iteration after handling this case.
                continue
            if w in stop_words:
                # Leave the loop after the target condition has been reached.
                break
            # Append the current value to words.
            words.append(w)
            if len(words) == 2:
                # Leave the loop after the target condition has been reached.
                break

        return " ".join(words).title() if words else None

    # Helper for extract person before.
    def extract_person_before(text_value: str, keyword: str) -> str | None:
        """Extract the required part of input for person before."""
        if keyword not in text_value:
            return None

        before = text_value.split(keyword)[0].strip()
        noise = ["si", "tadi", "kemarin", "barusan", "nih", "dong"]
        words = [w for w in before.split() if w not in noise]
        name_words = words[-2:] if len(words) >= 2 else words

        return " ".join(name_words).title() if name_words else None

    # Helper for clean fronting description.
    def clean_fronting_description(person: str, mode: str) -> str:
        """Coordinate the clean fronting description logic in the NLP/parser layer.

        Args:
            person: Input value supplied by the caller; accepted shape follows the function signature and local validation.
            mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `str` value as defined by the function signature.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
        """
        desc = extract_description(text, amount) or ""
        # Normalize desc lower before matching.
        desc_lower = desc.lower()
        person_pattern = re.escape(str(person or "").lower())

        # Implementation note for this project-specific finance flow.
        # Legacy compatibility note for older records or older in-memory state.
        desc_lower = re.sub(r"^\s*(?:saya|aku|gw|gue)\s+", "", desc_lower)
        if mode == "ditalangin":
            desc_lower = re.sub(
                rf"\b(?:nitip|ditalangin|ditalangi|dibayarin|duluin)\b\s*(?:sama|ke)?\s*{person_pattern}\b",
                "",
                desc_lower,
                flags=re.IGNORECASE,
            )
        # Use the fallback path when no earlier branch matched.
        else:
            desc_lower = re.sub(
                rf"\b(?:ngetalangin|nalangin|talangin|talangi)\b\s*(?:si\s+)?{person_pattern}\b",
                "",
                desc_lower,
                flags=re.IGNORECASE,
            )

        desc_lower = re.sub(r"^\s*(?:beli|beliin|belikan|bayar|buat|untuk)\s+", "", desc_lower)
        desc_lower = re.sub(r"\s+", " ", desc_lower).strip()

        if desc_lower:
            return desc_lower.title()
        return desc or "Talangan"


    # Phase 2: payment intent must be evaluated before generic `Budi hutang 50k`
    # receivable patterns, otherwise `Budi bayar utang 50k` becomes `Budi Bayar`.
    person_pays_debt_match = re.search(
        r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+"
        r"(?:bayar|byr|melunasi|lunasin|lunasi|nyicil|cicil|transfer\s+balik|kembaliin|balikin|dibalikin)\s+"
        r"(?:sebagian\s+)?(?:hutang(?:nya)?|utang(?:nya)?|piutang|debt|cicilan)\b(?=.*(?:\d|rp|idr))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if person_pays_debt_match:
        person = re.sub(r"\s+", " ", person_pays_debt_match.group("person")).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue", "gua"} and person.lower() not in ACCOUNT_NAMES:
            return attach_debt_account_payload({
                "intent": "add_payment",
                "person_name": person,
                "amount": amount,
                "description": f"Pembayaran piutang dari {person}",
                "date": detect_date(text),
                "raw_input": text,
                "target_debt_type": "receivable",
            }, text)

    # Match explicit user debt payments even when the user omits "saya".
    self_pays_debt_match = re.search(
        r"^\s*(?:(?:saya|aku|gw|gue|gua)\s+)?"
        r"(?:bayar|byr|melunasi|lunasin|lunasi|nyicil|cicil)\s+(?:sebagian\s+)?"
        r"(?:hutang|utang|debt|cicilan)\s+"
        r"(?:ke|sama)?\s*"
        r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)(?=\s*(?:\d|rp|idr))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if self_pays_debt_match:
        person = re.sub(r"\s+", " ", self_pays_debt_match.group("person")).strip().title()
        if person:
            return attach_debt_account_payload({
                "intent": "add_payment",
                "person_name": person,
                "amount": amount,
                "description": f"Bayar hutang ke {person}",
                "date": detect_date(text),
                "raw_input": text,
                "target_debt_type": "payable",
            }, text)

    # Explicit debt-only syntax: record a payable fact without treating it as
    # money received into an account.
    debt_only_payable_match = re.search(
        r"^\s*(?:cuma\s+|hanya\s+)?(?:catat|catetin|record)\s+"
        r"(?:(?:saya|aku|gue|gw|gua)\s+)?"
        r"(?:(?:punya|ada)\s+)?"
        r"(?:hutang|utang)\s+(?:ke|sama)\s+"
        r"(?P<person>[a-zA-Z][a-zA-Z\s]{0,40}?)(?=\s*(?:\d|rp|idr))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if debt_only_payable_match:
        person = re.sub(r"\s+", " ", debt_only_payable_match.group("person")).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue", "gua"}:
            description = extract_description(text, amount)
            # Extract person pattern for validation.
            person_pattern = re.escape(person)
            # Keep the saved detail focused on the reason, not the command words.
            description = re.sub(
                rf"^\s*(?:cuma\s+|hanya\s+)?(?:catat|catetin|record)\s+"
                rf"(?:(?:saya|aku|gue|gw|gua)\s+)?"
                rf"(?:(?:punya|ada)\s+)?"
                rf"(?:hutang|utang)\s+(?:ke|sama)\s+{person_pattern}\b",
                "",
                description or "",
                flags=re.IGNORECASE,
            )
            description = re.sub(
                r"^\s*(?:buat|untuk|karena)\s+",
                "",
                description,
                flags=re.IGNORECASE,
            ).strip(" .,-:")
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": f"Catat utang ke {person}" + (f": {description}" if description else ""),
                "date": detect_date(text),
                "raw_input": text,
                "cashflow_mode": "debt_only",
                "fronting_mode": "catat_utang",
                "account": "Debt Only",
                "skip_account": True,
            }

    # Offset syntax creates a separate opposite-side debt without auto-netting.
    offset_self_context = False
    offset_match = re.search(
        r"\b(?:potong|kurangi|kompensasi|offset|netting)\s+"
        r"(?P<target>piutang|utang|hutang)\s+"
        r"(?:ke|sama|dari)?\s*"
        r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)"
        r"(?=\s*(?:\d|rp|idr))",
        text_lower,
        flags=re.IGNORECASE,
    )
    # Validate missing offset match before continuing.
    if not offset_match:
        offset_match = re.search(
            r"\b(?:saya|aku|gue|gw|gua)\s+berh?utang\s+(?:ke|sama)\s+"
            r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)"
            r"(?=\s*(?:\d|rp|idr))"
            r".*\b(?:potong|kompensasi|offset|netting)\s+(?:dari\s+)?(?P<target>piutang|utang|hutang)\b",
            text_lower,
            flags=re.IGNORECASE,
        )
        # Prepare offset self context from the incoming input.
        offset_self_context = bool(offset_match)
    if offset_match:
        person = re.sub(r"\s+", " ", offset_match.group("person")).strip().title()
        target_word = str(offset_match.group("target") or "piutang").strip().lower()
        if target_word == "piutang":
            target_debt_type = "receivable"
        # Fall back when offset self context.
        elif offset_self_context:
            target_debt_type = "payable"
        # Use the fallback path when no earlier branch matched.
        else:
            target_debt_type = "receivable"
        resulting_debt_type = "payable" if target_debt_type == "receivable" else "receivable"

        if person and person.lower() not in {"saya", "aku", "gw", "gue", "gua"}:
            return {
                "intent": "offset_debt",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
                "target_debt_type": target_debt_type,
                "resulting_debt_type": resulting_debt_type,
                "cashflow_mode": "offset",
                "fronting_mode": "debt_offset",
                "account": "Debt Offset",
                "skip_account": True,
            }

    # ── Covered-by-someone rule ────────────────────────────────────────────────
    # Split bill parsing note: separate the paid transaction from each person share.
    ditalangin_person_first_match = re.search(
        r"\b(?:saya|aku|gw|gue)?\s*"
        r"(?:nitip|ditalangin|ditalangi|dibayarin|duluin)\s+"
        r"(?:sama|ke)?\s*(?:si\s+)?"
        r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)"
        r"(?=\s+(?:beli|beliin|belikan|bayar|buat|untuk)\b)",
        text_lower,
        flags=re.IGNORECASE,
    )
    if ditalangin_person_first_match:
        person = re.sub(
            r"\s+",
            " ",
            ditalangin_person_first_match.group("person"),
        ).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue"}:
            item_desc = clean_fronting_description(person, "ditalangin")
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": f"Ditalangin {person}: {item_desc}",
                "date": detect_date(text),
                "raw_input": text,
                "cashflow_mode": "debt_only",
                "fronting_mode": "ditalangin",
            }

    # ── Covered-by-someone rule ────────────────────────────────────────────────
    ditalangin_item_by_person_match = re.search(
        r"\b(?:saya|aku|gw|gue)?\s*"
        r"(?:nitip|ditalangin|ditalangi|dibayarin|duluin)\s+"
        r"(?P<item>.+?)\s+"
        r"(?:sama|oleh|ke|dari)\s+(?:si\s+)?"
        r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)"
        r"(?=\s+(?:tanggal|tgl|kemarin|hari\s+ini|besok|\d|rp|idr)|\s*$)",
        text_lower,
        flags=re.IGNORECASE,
    )
    if ditalangin_item_by_person_match:
        person = re.sub(
            r"\s+",
            " ",
            ditalangin_item_by_person_match.group("person"),
        ).strip().title()
        item_desc = re.sub(
            r"\s+",
            " ",
            ditalangin_item_by_person_match.group("item"),
        ).strip().title()

        if person and person.lower() not in {"saya", "aku", "gw", "gue"}:
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": f"Ditalangin {person}: {item_desc or 'Talangan'}",
                "date": detect_date(text),
                "raw_input": text,
                "cashflow_mode": "debt_only",
                "fronting_mode": "ditalangin",
            }

    # ── Fronting-money rule without immediate cashflow ────────────────────────
    ditalangin_match = re.search(
        r"\b(?:saya|aku|gw|gue)?\s*(?:nitip|ditalangin|ditalangi|dibayarin|duluin)\s+"
        r"(?:sama|ke)?\s*(?:si\s+)?([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)"
        r"(?=\s+(?:beli|beliin|belikan|bayar|buat|untuk)\b|\s*(?:\d|rp|idr))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if ditalangin_match:
        person = re.sub(r"\s+", " ", ditalangin_match.group(1)).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue"}:
            item_desc = clean_fronting_description(person, "ditalangin")
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": f"Ditalangin {person}: {item_desc}",
                "date": detect_date(text),
                "raw_input": text,
                "cashflow_mode": "debt_only",
                "fronting_mode": "ditalangin",
            }

    # Account flow section
    talangin_match = re.search(
        r"\b(?:saya|aku|gw|gue)?\s*(?:ngetalangin|nalangin|talangin|talangi)\s+"
        r"(?:si\s+)?([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)"
        r"(?=\s+(?:beli|beliin|belikan|bayar|buat|untuk)\b|\s*(?:\d|rp|idr))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if talangin_match:
        person = re.sub(r"\s+", " ", talangin_match.group(1)).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue"}:
            item_desc = clean_fronting_description(person, "talangin")
            return {
                "intent": "add_receivable",
                "person_name": person,
                "amount": amount,
                "description": f"Talangin {person}: {item_desc}",
                "date": detect_date(text),
                "raw_input": text,
                "cashflow_mode": "cashflow",
                "fronting_mode": "talangin",
            }

    person_paid_for_me_match = re.search(
        r"^\s*([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+"
        r"(?:ngetalangin|nalangin|talangin|talangi|beliin|belikan|bayarin|membayari)\s+"
        r"(?:saya|aku|gw|gue)\b",
        text_lower,
        flags=re.IGNORECASE,
    )
    if person_paid_for_me_match:
        person = re.sub(r"\s+", " ", person_paid_for_me_match.group(1)).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue"}:
            item_desc = clean_fronting_description(person, "ditalangin")
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": f"Ditalangin {person}: {item_desc}",
                "date": detect_date(text),
                "raw_input": text,
                "cashflow_mode": "debt_only",
                "fronting_mode": "ditalangin",
            }

    receivable_to_me_match = re.search(
        r"^\s*([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)\s+(?:hutang|utang)\s+ke\s+(?:saya|aku|gw|gue)\b",
        text_lower,
        flags=re.IGNORECASE,
    )
    if receivable_to_me_match:
        person = re.sub(r"\s+", " ", receivable_to_me_match.group(1)).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue"}:
            return {
                "intent": "add_receivable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            }

    explicit_piutang_match = re.search(
        r"\bpiutang\s+(?:ke|sama|dari)?\s*"
        r"([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)(?=\s*(?:\d|rp|idr))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if explicit_piutang_match:
        person = re.sub(r"\s+", " ", explicit_piutang_match.group(1)).strip().title()
        if person:
            return {
                "intent": "add_receivable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            }

    self_payable_match = re.search(
        r"\b(?:saya|aku|gue|gw|gua)\s+berh?utang\s+(?:ke|sama)\s+"
        r"([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)(?=\s*(?:\d|rp|idr|$))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if self_payable_match:
        person = re.sub(r"\s+", " ", self_payable_match.group(1)).strip().title()
        if person:
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            }

    other_receivable_match = re.search(
        r"\b([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)\s+berh?utang\s+"
        r"(?:ke|sama)\s+(?:saya|aku|gue|gw|gua)\b",
        text_lower,
        flags=re.IGNORECASE,
    )
    if other_receivable_match:
        person = re.sub(r"\s+", " ", other_receivable_match.group(1)).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue", "gua"}:
            return {
                "intent": "add_receivable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            }

    short_other_receivable_match = re.search(
        r"\b(?!saya\b|aku\b|gue\b|gw\b|gua\b)"
        r"([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)\s+berh?utang\b"
        r"(?=.*(?:\d|rp|idr))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if short_other_receivable_match:
        person = re.sub(r"\s+", " ", short_other_receivable_match.group(1)).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue", "gua"}:
            return {
                "intent": "add_receivable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            }

    short_hutang_receivable_match = re.search(
        r"^\s*(?!saya\b|aku\b|gue\b|gw\b|gua\b)"
        r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)\s+"
        r"(?:ada\s+)?(?:hutang|utang)\b(?=.*(?:\d|rp|idr))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if short_hutang_receivable_match:
        person = re.sub(r"\s+", " ", short_hutang_receivable_match.group("person")).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue", "gua"}:
            return {
                "intent": "add_receivable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            }

    # Split bill parsing note: separate the paid transaction from each person share.

    # Example cleanup: remove the person prefix so the description stays focused on the expense item.
    person_pays_match = re.search(
        r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+"
        r"(?:bayar|byr|melunasi|lunasin|lunasi|nyicil|cicil|transfer\s+balik|kembaliin|balikin|dibalikin)\b"
        r"(?=.*(?:\d|rp|idr))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if person_pays_match and re.search(r"\b(?:hutang|utang|piutang|debt|cicil|cicilan|lunas|lunasi|lunasin|melunasi|nyicil|transfer\s+balik|kembaliin|balikin|dibalikin)\b", text_lower):
        person = re.sub(r"\s+", " ", person_pays_match.group("person")).strip().title()
        if (
            person
            and person.lower() not in {"saya", "aku", "gw", "gue", "gua"}
            and person.lower() not in ACCOUNT_NAMES
        ):
            return {
                "intent": "add_payment",
                "person_name": person,
                "amount": amount,
                "description": f"Pembayaran piutang dari {person}",
                "date": detect_date(text),
                "raw_input": text,
                "target_debt_type": "receivable",
            }

    self_pays_match = re.search(
        r"^\s*(?:saya|aku|gw|gue|gua)\s+"
        r"(?:bayar|byr|melunasi|lunasin|lunasi|nyicil|cicil)\s+"
        r"(?:hutang|utang|debt|cicilan)\s+"
        r"(?:ke|sama)?\s*"
        r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)(?=\s*(?:\d|rp|idr))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if self_pays_match:
        person = re.sub(r"\s+", " ", self_pays_match.group("person")).strip().title()
        if person:
            return {
                "intent": "add_payment",
                "person_name": person,
                "amount": amount,
                "description": f"Bayar hutang ke {person}",
                "date": detect_date(text),
                "raw_input": text,
                "target_debt_type": "payable",
            }

    for kw in DEBT_PAYMENT_KEYWORDS:
        if kw in text_lower:
            # Extract person for validation.
            person = extract_person_after(text_lower, kw)
            # Validate missing person before continuing.
            if not person:
                # Extract person for validation.
                person = extract_person_before(text_lower, kw)

            return {
                "intent": "add_payment",
                "person_name": person or "",
                "amount": amount,
                "description": f"Bayar hutang {person or ''}".strip(),
                "date": detect_date(text),
                "raw_input": text,
                "target_debt_type": "auto",
            }

    natural_borrow_match = re.search(
        r"\b(?:minjem|pinjem|pinjam)\b\s+(?:uang|duit|dana)?\s*(?:ke|sama|dari)?\s*([a-zA-Z][a-zA-Z\s]{0,40}?)(?=\s*\d|\s*(?:rp|idr))",
        text_lower,
    )
    if natural_borrow_match and not re.search(r"\b(?:minjemin|pinjemin)\b", text_lower):
        # Extract person for validation.
        person = natural_borrow_match.group(1).strip()
        person = re.sub(r"\b(?:uang|duit|dana|ke|sama|dari)\b", " ", person).strip()
        person = re.sub(r"\s+", " ", person).title()
        if person:
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            }

    for kw in DEBT_PAYABLE_KEYWORDS:
        kw_pattern = rf"(?<![a-zA-ZÀ-ÿ]){re.escape(kw)}(?![a-zA-ZÀ-ÿ])"
        if re.search(kw_pattern, text_lower, flags=re.IGNORECASE):
            # Extract person for validation.
            person = extract_person_after(text_lower, kw)
            return {
                "intent": "add_payable",
                "person_name": person or "",
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            }

    for kw in DEBT_RECEIVABLE_KEYWORDS:
        if kw in text_lower:
            # Extract person for validation.
            person = extract_person_before(text_lower, kw)
            # Validate missing person before continuing.
            if not person:
                # Extract person for validation.
                person = extract_person_after(text_lower, kw)

            if person:
                return attach_debt_account_payload({
                    "intent": "add_receivable",
                    "person_name": person,
                    "amount": amount,
                    "description": extract_description(text, amount),
                    "date": detect_date(text),
                    "raw_input": text,
                }, text)

    return None


# ── Helper functions ──────────────────────────────────────────────────────────


def _extract_incoming_transfer_source(text: str) -> str | None:
    """Extract the source token/phrase from the bounded incoming-transfer grammar."""
    match = re.search(
        r"^\s*(?:transaksi|transfer(?:an)?|tf|trf|kiriman|uang)\s+(?:masuk\s+)?dari\s+"
        r"([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)(?=\s*(?:\d|rp|idr|ke\s+|via\s+|pakai\s+|pake\s+))",
        normalize_text(text),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip() or None


# Helper for detect type.
def detect_type(text: str, *, runtime_account_names: list[str] | tuple[str, ...] | None = None) -> str | None:
    """Coordinate the detect type logic in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Normalize text lower before matching.
    text_lower = normalize_text(text)
    # Freeze one runtime-account view for the full classification operation.
    account_names = tuple(runtime_account_names) if runtime_account_names is not None else tuple(get_runtime_account_names())
    # Extract account pattern for validation from the same snapshot.
    account_pattern = _account_pattern_from_sheet(account_names)

    # Account flow section
    # Account flow section
    incoming_source = _extract_incoming_transfer_source(text)
    if incoming_source:
        # Full/runtime own-account names must outrank the person-income grammar.
        # This keeps multiword and sheet-backed accounts on transfer semantics.
        if not _is_runtime_account_name(incoming_source, account_names):
            return "income"

    # Account flow section
    if re.search(rf"\b({account_pattern})\s+ke\s+({account_pattern})\b", text_lower, flags=re.IGNORECASE):
        return "transfer"

    # Alias transfer.
    if re.search(r"\b(?:tf|trf)\b", text_lower) and re.search(rf"\b({account_pattern})\b", text_lower, flags=re.IGNORECASE):
        return "transfer"

    # Keyword transfer eksplisit selain topup/isi.
    explicit_transfer_keywords = [
        "transfer", "pindah", "move", "tarik tunai", "tarik",
        "setor tunai", "setor ke",
    ]
    # Handle any(kw in text lower for kw in explicit transfer keywords).
    if any(kw in text_lower for kw in explicit_transfer_keywords):
        if re.search(rf"\b({account_pattern})\b", text_lower, flags=re.IGNORECASE):
            return "transfer"

    # Account flow section
    topup_to_account = re.search(
        rf"\b(?:top\s*up|topup|isi|ngisi)\s+({account_pattern})\b",
        text_lower,
        flags=re.IGNORECASE,
    )
    topup_ke_account = re.search(
        rf"\b(?:top\s*up|topup|isi|ngisi)\b.*\bke\s+({account_pattern})\b",
        text_lower,
        flags=re.IGNORECASE,
    )
    # Handle topup to account or topup ke account.
    if topup_to_account or topup_ke_account:
        return "transfer"

    if re.search(r"\buang\b.*\b(dari|masuk)\b", text_lower):
        return "income"

    # Iterate through each kw.
    for kw in INCOME_KEYWORDS:
        if kw in text_lower:
            return "income"

    # Iterate through each kw.
    for kw in EXPENSE_KEYWORDS:
        if kw in text_lower:
            return "expense"

    return None

# Helper for detect category.
def detect_category(text: str, transaction_type: str) -> str:
    """Coordinate the detect category logic in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        transaction_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep category name, type, symbol, and alias behavior consistent with the documented category flow.
    """
    # Normalize text lower before matching.
    text_lower = normalize_text(text)

    # Iterate through each category, keywords.
    for category, keywords in CATEGORY_KEYWORDS.items():
        # Iterate through each kw.
        for kw in keywords:
            if kw in text_lower:
                return category

    if transaction_type == "income":
        return "Other Income"

    return "Other Expense"


# Helper for detect account.
def detect_account(text: str, *, runtime_account_names: list[str] | tuple[str, ...] | None = None) -> str | None:
    """Detect an account name using the sheet-backed account resolver."""
    # Normalize text lower before matching.
    text_lower = normalize_text(text)

    account_names = tuple(runtime_account_names) if runtime_account_names is not None else tuple(get_runtime_account_names())

    # Iterate through each account name.
    for account_name in sorted(account_names, key=len, reverse=True):
        # Normalize clean account before matching.
        clean_account = normalize_text(account_name)
        pattern = re.escape(clean_account).replace(r"\ ", r"\s+")
        if re.search(rf"\b{pattern}\b", text_lower, flags=re.IGNORECASE):
            return account_name

    # Iterate through each acc.
    for acc in ACCOUNT_NAMES:
        escaped_acc = re.escape(acc).replace(r"\ ", r"\s*")
        account_pattern = rf"\b{escaped_acc}\b"

        if re.search(account_pattern, text_lower, flags=re.IGNORECASE):
            return display_account_name(acc)

    return None


# Helper for detect transfer accounts.
def detect_transfer_accounts(text: str, *, runtime_account_names: list[str] | tuple[str, ...] | None = None) -> tuple[str | None, str | None]:
    """Coordinate the detect transfer accounts logic in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `tuple[str | None, str | None]` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Normalize text lower before matching.
    text_lower = normalize_text(text)
    # Freeze one runtime-account view for the full transfer extraction operation.
    account_names = tuple(runtime_account_names) if runtime_account_names is not None else tuple(get_runtime_account_names())

    # Extract account pattern for validation from the same snapshot.
    account_pattern = _account_pattern_from_sheet(account_names)

    # Helper for normalize account name.
    def normalize_account_name(raw: str | None) -> str | None:
        """Normalize input values for the normalize account name workflow in the NLP/parser layer.

        Args:
            raw: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `str | None` value as defined by the function signature.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
        """
        return _display_runtime_account_name(raw, account_names)

    # Helper for iter accounts.
    def iter_accounts() -> list[tuple[int, str]]:
        """Coordinate the iter accounts logic in the NLP/parser layer.

        Args:
            None.

        Returns:
            `list[tuple[int, str]]` value as defined by the function signature.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
        """
        matches = []
        for match in re.finditer(rf"\b({account_pattern})\b", text_lower, flags=re.IGNORECASE):
            display = normalize_account_name(match.group(1))
            if display:
                # Append the current value to matches.
                matches.append((match.start(), display))
        return matches

    # Helper for first account after.
    def first_account_after(pattern: str) -> str | None:
        """Coordinate the first account after logic in the NLP/parser layer.

        Args:
            pattern: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `str | None` value as defined by the function signature.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
        """
        match = re.search(pattern, text_lower, flags=re.IGNORECASE)
        # Validate missing match before continuing.
        if not match:
            return None
        return normalize_account_name(match.group(1))

    # Helper for first other account.
    def first_other_account(excluded: set[str]) -> str | None:
        """Coordinate the first other account logic in the NLP/parser layer.

        Args:
            excluded: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `str | None` value as defined by the function signature.

        Side effects:
            None beyond the side effects already performed by the existing implementation.

        Flow constraints:
            Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
        """
        # Iterate through each  , account.
        for _, account in found:
            if account not in excluded:
                return account
        return None

    found = iter_accounts()

    # Validate missing found before continuing.
    if not found:
        return None, None

    # Explicit markers.
    source_account = first_account_after(rf"\b(?:dari|from|pakai|pake|via)\s+({account_pattern})\b")
    target_account = first_account_after(rf"\b(?:ke|to|tujuan|rekening\s+tujuan|ke\s+rekening)\s+({account_pattern})\b")

    # Handle source account and target account and source account != targe.
    if source_account and target_account and source_account != target_account:
        return source_account, target_account

    # Account flow section
    topup_target = first_account_after(rf"\b(?:top\s*up|topup|isi|ngisi)\s+({account_pattern})\b")
    if topup_target:
        # Handle source account and source account != topup target.
        if source_account and source_account != topup_target:
            return source_account, topup_target

        # Extract other account for validation.
        other_account = first_other_account({topup_target})
        if other_account:
            return other_account, topup_target

        return None, topup_target

    # Account flow section
    if source_account:
        # Extract other account for validation.
        other_account = first_other_account({source_account})
        return source_account, other_account

    if target_account:
        # Extract other account for validation.
        other_account = first_other_account({target_account})
        return other_account, target_account

    # Legacy compatibility note for older records or older in-memory state.
    if len(found) >= 2:
        return found[0][1], found[1][1]

    if len(found) == 1:
        return None, found[0][1]

    return None, None

# Helper for parse explicit date.
def parse_explicit_date(date_text: str) -> str | None:
    """Parse caller input for the parse explicit date workflow in the NLP/parser layer.

    Args:
        date_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    text = str(date_text or "").strip()

    # YYYY-MM-DD atau YYYY/MM/DD
    match_ymd = re.fullmatch(r"(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])", text)
    if match_ymd:
        year = int(match_ymd.group(1))
        month = int(match_ymd.group(2))
        day = int(match_ymd.group(3))

        # Run this operation in a guarded block so failures can be handled.
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        # Handle an expected failure from the guarded operation above.
        except ValueError:
            return None

    # DD-MM-YYYY atau DD/MM/YYYY
    match_dmy = re.fullmatch(r"(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](20\d{2})", text)
    if match_dmy:
        day = int(match_dmy.group(1))
        month = int(match_dmy.group(2))
        year = int(match_dmy.group(3))

        # Run this operation in a guarded block so failures can be handled.
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        # Handle an expected failure from the guarded operation above.
        except ValueError:
            return None

    return None


# Helper for parse day only date.
def parse_day_only_date(day_text: str) -> str | None:
    """Parse caller input for the parse day only date workflow in the NLP/parser layer.

    Args:
        day_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    clean = str(day_text or "").strip()

    if not re.fullmatch(r"0?[1-9]|[12]\d|3[01]", clean):
        return None

    today = business_now().date()
    day = int(clean)

    # Run this operation in a guarded block so failures can be handled.
    try:
        return datetime(today.year, today.month, day).strftime("%Y-%m-%d")
    # Handle an expected failure from the guarded operation above.
    except ValueError:
        return None


# Helper for strip date phrases.
def strip_date_phrases(text: str) -> str:
    """Coordinate the strip date phrases logic in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    clean = str(text or "")

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    clean = re.sub(
        r"\b(?:tanggal|tgl|date|pada tanggal)\s+"
        r"(?:20\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])|"
        r"(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]20\d{2})\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # Natural Indonesian absolute dates, with optional marker/year. Keep this
    # aligned with detect_date_result so description/category parsing does not
    # retain date tokens after the date itself has been recognized.
    clean = re.sub(
        r"\b(?:tanggal|tgl|tg|date|pada\s+tanggal)?\s*"
        r"(?:0?[1-9]|[12]\d|3[01])\s+"
        r"(?:januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)"
        r"(?:\s+20\d{2})?\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    clean = re.sub(
        r"\b(?:tanggal|tgl|tg|date|pada tanggal)\s+"
        r"(?:0?[1-9]|[12]\d|3[01])\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    clean = re.sub(
        r"\b20\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    clean = re.sub(
        r"\b(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]20\d{2}\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # Implementation note for this project-specific finance flow.
    clean = re.sub(r"\bhari\s+ini\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bkemarin\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bminggu\s+lalu\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bseminggu\s+(?:yang\s+)?lalu\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bsehari\s+(?:yang\s+)?lalu\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bsebulan\s+(?:yang\s+)?lalu\b", " ", clean, flags=re.IGNORECASE)

    # Implementation note for this project-specific finance flow.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # tiga minggu lalu
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    clean = re.sub(
        r"\b("
        r"\d+|"
        r"satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|"
        r"sebelas|dua belas|tiga belas|empat belas|lima belas|enam belas|"
        r"tujuh belas|delapan belas|sembilan belas|dua puluh"
        r")\s+"
        r"(hari|minggu|bulan)"
        r"\s+(?:yang\s+)?lalu\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    clean = re.sub(r"\s+", " ", clean).strip()

    return clean

NUMBER_WORDS_ID = {
    "se": 1,
    "satu": 1,
    "dua": 2,
    "tiga": 3,
    "empat": 4,
    "lima": 5,
    "enam": 6,
    "tujuh": 7,
    "delapan": 8,
    "sembilan": 9,
    "sepuluh": 10,
    "sebelas": 11,
    "dua belas": 12,
    "tiga belas": 13,
    "empat belas": 14,
    "lima belas": 15,
    "enam belas": 16,
    "tujuh belas": 17,
    "delapan belas": 18,
    "sembilan belas": 19,
    "dua puluh": 20,
    "sebulan": 1,
    "seminggu": 1,
    "sehari": 1,
}


# Helper for parse relative number.
def parse_relative_number(value: str) -> int | None:
    """Parse caller input for the parse relative number workflow in the NLP/parser layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `int | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    clean = str(value or "").strip().lower()

    if clean.isdigit():
        return int(clean)

    return NUMBER_WORDS_ID.get(clean)

# Helper for detect relative date.
def detect_relative_date(text: str) -> str | None:
    """Coordinate the detect relative date logic in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    clean = str(text or "").strip().lower()
    today = business_now().date()

    if re.search(r"\bhari\s+ini\b", clean):
        return today.strftime("%Y-%m-%d")

    if re.search(r"\bkemarin\b", clean):
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # minggu lalu / seminggu lalu
    if re.search(r"\bminggu\s+lalu\b", clean) or re.search(r"\bseminggu\s+(?:yang\s+)?lalu\b", clean):
        return (today - timedelta(weeks=1)).strftime("%Y-%m-%d")

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    if re.search(r"\bsehari\s+(?:yang\s+)?lalu\b", clean):
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    if re.search(r"\bsebulan\s+(?:yang\s+)?lalu\b", clean):
        return _subtract_calendar_months(today, 1).strftime("%Y-%m-%d")

    # Pattern:
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # 3 minggu lalu
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    relative_match = re.search(
        r"\b("
        r"\d+|"
        r"satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|"
        r"sebelas|dua belas|tiga belas|empat belas|lima belas|enam belas|"
        r"tujuh belas|delapan belas|sembilan belas|dua puluh"
        r")\s+"
        r"(hari|minggu|bulan)"
        r"\s+(?:yang\s+)?lalu\b",
        clean,
        flags=re.IGNORECASE,
    )

    if relative_match:
        # Prepare number raw from the incoming input.
        number_raw = relative_match.group(1)
        unit = relative_match.group(2).lower()

        number = parse_relative_number(number_raw)

        # Validate missing number before continuing.
        if not number:
            return None

        if unit == "hari":
            return (today - timedelta(days=number)).strftime("%Y-%m-%d")

        if unit == "minggu":
            return (today - timedelta(weeks=number)).strftime("%Y-%m-%d")

        if unit == "bulan":
            return _subtract_calendar_months(today, number).strftime("%Y-%m-%d")

    return None


def _subtract_calendar_months(value, months: int):
    """Subtract calendar months and clamp to the target month's final day."""

    month_index = value.year * 12 + value.month - 1 - int(months)
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


# Helper for detect date.
@dataclass(frozen=True)
class DateDetectionResult:
    """Describe whether a date was absent, valid, or explicitly invalid.

    ``value`` keeps the existing ``YYYY-MM-DD`` representation for valid and
    absent inputs. Explicitly invalid input has ``value=None`` so callers can
    require clarification instead of silently using today.
    """

    status: str
    value: str | None
    explicit_input: str | None = None


def detect_date_result(text: str) -> DateDetectionResult:
    """Detect a business date while preserving explicit invalid input.

    Args:
        text: Natural-language transaction input.

    Returns:
        ``DateDetectionResult`` with status ``absent``, ``valid``, or
        ``invalid``. Only ``absent`` defaults to the current date.

    Side effects:
        None. The function reads the local clock only for absent, relative, and
        day-only dates, matching the existing business-date behavior.
    """

    clean = str(text or "").strip().lower()
    today = business_now().date()

    explicit_pattern = (
        r"20\d{2}[-/]\d{1,2}[-/]\d{1,2}"
        r"|"
        r"\d{1,2}[-/]\d{1,2}[-/]20\d{2}"
    )
    explicit_match = re.search(
        rf"\b(?:tanggal|tgl|date|pada\s+tanggal)?\s*({explicit_pattern})\b",
        clean,
        flags=re.IGNORECASE,
    )
    if explicit_match:
        raw_value = explicit_match.group(1)
        parsed_value = parse_explicit_date(raw_value)
        if parsed_value:
            return DateDetectionResult("valid", parsed_value, raw_value)
        return DateDetectionResult("invalid", None, raw_value)

    month_names = {
        "januari": 1, "februari": 2, "maret": 3, "april": 4,
        "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
        "september": 9, "oktober": 10, "november": 11, "desember": 12,
    }
    natural_match = re.search(
        r"\b(?:tanggal|tgl|tg|date|pada\s+tanggal)?\s*"
        r"(\d{1,2})\s+"
        r"(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)"
        r"(?:\s+(20\d{2}))?\b",
        str(text or ""),
        flags=re.IGNORECASE,
    )
    if natural_match:
        raw_value = natural_match.group(0)
        day = int(natural_match.group(1))
        month = month_names[natural_match.group(2).lower()]
        year = int(natural_match.group(3)) if natural_match.group(3) else today.year
        try:
            parsed_value = datetime(year, month, day).date().strftime("%Y-%m-%d")
        except ValueError:
            return DateDetectionResult("invalid", None, raw_value)
        return DateDetectionResult("valid", parsed_value, raw_value)

    # Day-only markers are intentionally checked *after* the richer natural
    # month form so `tgl 4 Juli 2025` cannot be consumed as merely `tgl 4`.
    day_only_match = re.search(
        r"\b(?:tanggal|tgl|tg|date|pada\s+tanggal)\s+(\d{1,2})\b",
        clean,
        flags=re.IGNORECASE,
    )
    if day_only_match:
        raw_value = day_only_match.group(1)
        parsed_value = parse_day_only_date(raw_value)
        if parsed_value:
            return DateDetectionResult("valid", parsed_value, raw_value)
        return DateDetectionResult("invalid", None, raw_value)

    relative_date = detect_relative_date(clean)
    if relative_date:
        return DateDetectionResult("valid", relative_date)

    return DateDetectionResult("absent", today.strftime("%Y-%m-%d"))


def detect_date(text: str) -> str | None:
    """Coordinate the detect date logic in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    return detect_date_result(text).value

# Helper for extract description.
def extract_description(text: str, amount=None) -> str:
    """Extract the required part of input for description."""
    clean = str(text or "").strip()

    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    clean = re.sub(r"(?<=[A-Za-zÀ-ÖØ-öø-ÿ])(?=\d)", " ", clean)

    clean = strip_date_phrases(clean)

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    if amount is not None:
        # Extract amount int for validation.
        amount_int = int(float(amount or 0))

        amount_variants = [
            str(amount_int),
            f"{amount_int:,}".replace(",", "."),
            f"{amount_int:,}".replace(",", ","),
        ]

        # Iterate through each variant.
        for variant in amount_variants:
            clean = clean.replace(variant, " ")

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    clean = re.sub(
        r"\b\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)?\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    clean = re.sub(
        r"\b(?:rb|ribu|k|jt|juta|m|miliar|miliard|milyard)\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|split|share|patungan)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"
    has_named_split = re.search(
        rf"\b{split_word}\s*(?:jadi\s*)?\d*\s*(?:orang\s+)?{friend_marker}\b",
        clean,
        flags=re.IGNORECASE,
    )
    # Validate missing has named split before continuing.
    if not has_named_split:
        clean = re.sub(rf"\b{split_word}\b", " ", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\b(?:jadi|orang)\b", " ", clean, flags=re.IGNORECASE)

    # 4. Remove common transaction verbs from the beginning.
    # Account flow section
    account_pattern = r"(?:cash|bri|bsi|bca|dana|gopay|seabank|sea\s*bank)"
    person_transfer = re.match(rf"^\s*transfer\s+ke\s+(?!{account_pattern}\b)", clean, flags=re.IGNORECASE)

    if person_transfer:
        start_verbs = r"beli|bayar|byr|jajan|makan|minum|top\s*up|topup|isi|ngisi|gaji|dapet|dapat|terima|masuk|transaksi|kiriman"
    # Use the fallback path when no earlier branch matched.
    else:
        start_verbs = r"beli|bayar|byr|jajan|makan|minum|transfer|transferan|tf|trf|top\s*up|topup|isi|ngisi|gaji|dapet|dapat|terima|masuk|transaksi|kiriman"

    clean = re.sub(
        rf"^\s*({start_verbs})\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # Account flow section
    clean = re.sub(
        r"\b(dari|ke|pakai|pake|via)\s+(cash|bri|bsi|bca|dana|gopay|seabank|sea\s*bank)\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    clean = re.sub(r"^\s*dari\s+", " ", clean, flags=re.IGNORECASE)

    # 6. Rapikan spasi.
    clean = re.sub(r"\s+", " ", clean).strip(" .,-;:")

    # Validate missing clean before continuing.
    if not clean:
        return "Transaksi"

    return clean.title()

# Helper for detect subject.
def detect_subject(text: str, transaction_type: str, category: str, description: str) -> str:
    """Coordinate the detect subject logic in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        transaction_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        category: Category name or category-like value from user input or sheet data.
        description: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Normalize text lower before matching.
    text_lower = normalize_text(text)

    known_subjects = {
        "PLN": ["pln", "token listrik", "listrik"],
        "PDAM": ["pdam"],
        "BPJS": ["bpjs"],
        "Indomaret": ["indomaret"],
        "Alfamart": ["alfamart"],
        "Shopee": ["shopee"],
        "Tokopedia": ["tokopedia"],
        "GoPay": ["gopay"],
        "DANA": ["dana"],
        "Grab": ["grab"],
        "Gojek": ["gojek"],
        "Netflix": ["netflix"],
        "Spotify": ["spotify"],
        "YouTube Premium": ["youtube premium"],
        "Kos": ["kos", "kost", "kontrakan"],
    }

    # Iterate through each subject, keywords.
    for subject, keywords in known_subjects.items():
        # Iterate through each kw.
        for kw in keywords:
            if kw in text_lower:
                return subject

    if transaction_type == "income":
        if category == "Salary":
            return "Pekerjaan"
        if category == "Freelance":
            return "Client"
        return "Pemasukan"

    if description and description != "Transaksi":
        return description

    return ""


# Helper for extract note.
def extract_note(text: str) -> str:
    """Extract the required part of input for note."""
    # Normalize text lower before matching.
    text_lower = normalize_text(text)

    note = ""

    # Explicit priority: catatan/note/keterangan fields
    explicit_pattern = r"(?:catatan|note|notes|keterangan)\s*[:\-]?\s*(.+)$"
    explicit_match = re.search(explicit_pattern, text_lower)

    if explicit_match:
        note = explicit_match.group(1).strip()
    # Use the fallback path when no earlier branch matched.
    else:
        # Legacy compatibility note for older records or older in-memory state.
        fallback_pattern = r"(?:buat|untuk)\s+(.+)$"
        fallback_match = re.search(fallback_pattern, text_lower)
        if fallback_match:
            note = fallback_match.group(1).strip()

    # Validate missing note before continuing.
    if not note:
        return ""

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    note = re.sub(
        r"\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m|miliar|milyar)?",
        "",
        note,
    )

    # "dibagi 2 sama raka" -> "sama raka"
    note = re.sub(r"\b(di\s*-?\s*bagi|dibagi|bagi|split|share|patungan)\s*(?:jadi\s*)?\d+\b", "", note)

    note = re.sub(r"\b\d+\s*orang\b", "", note)

    # Buang noise ringan
    noise_words = [
        "catatan", "note", "notes", "keterangan",
        "dong", "ya", "nih", "deh",
    ]

    # Iterate through each word.
    for word in noise_words:
        note = re.sub(rf"\b{re.escape(word)}\b", "", note)

    note = " ".join(note.split()).strip()

    return note.title() if note else ""


# Helper for detect spending type.
def detect_spending_type(text: str, category: str, transaction_type: str) -> str:
    """Coordinate the detect spending type logic in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.
        category: Category name or category-like value from user input or sheet data.
        transaction_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    if transaction_type != "expense":
        return ""

    # Normalize text lower before matching.
    text_lower = normalize_text(text)

    # Iterate through each spending type, keywords.
    for spending_type, keywords in SPENDING_TYPE_KEYWORDS.items():
        # Iterate through each kw.
        for kw in keywords:
            if kw in text_lower:
                return spending_type

    if category in ["Kos & Utilities", "Bills & Utilities"]:
        return "Bulanan"

    if category == "Health":
        return "Darurat"

    if category == "Entertainment":
        return "Keinginan"

    return "Harian"


# ── Main parser function ──────────────────────────────────────────────────────

# Helper for parse with regex.
def parse_with_regex(text: str) -> dict | None:
    """Parse caller input for the parse with regex workflow in the NLP/parser layer.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    if str(text or "").strip().startswith("/"):
        return None

    clean = normalize_text(text)
    if re.search(r"^(?:tidak\s+jadi|nggak\s+jadi|ga\s+jadi|batal)\b|\b(?:tapi|namun)\s+batal\b|\bbatal\s*$", clean):
        return None
    if re.search(r"(?:^|\s)-\s*\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m|rupiah)?\b", clean):
        return None

    # Extract text without date for validation.
    text_without_date = strip_date_phrases(text)
    # Extract amount for validation.
    amount = extract_amount_from_text(text_without_date)
    # Validate missing amount before continuing.
    if not amount:
        return None

    # One parse must use one account view, including whether that view is authoritative.
    runtime_account_names, account_source_available = get_runtime_account_snapshot()
    incoming_source = _extract_incoming_transfer_source(text)
    if (
        incoming_source
        and not account_source_available
        and not _is_runtime_account_name(incoming_source, runtime_account_names)
    ):
        transaction_type = "ambiguous"
    else:
        transaction_type = detect_type(text, runtime_account_names=runtime_account_names)

    # Legacy compatibility note for older records or older in-memory state.
    # "Nasi kuning 22k 09-05-2026", "Print 6k", "Alquran 80k".
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Legacy compatibility note for older records or older in-memory state.
    if not transaction_type:
        plain_description = extract_description(text, amount)
        if re.search(r"[A-Za-zÀ-ÿ]", plain_description or ""):
            transaction_type = "expense"
        # Use the fallback path when no earlier branch matched.
        else:
            return None

    # Preserve explicit invalid dates so parse safety can request clarification.
    date_result = detect_date_result(text)
    date = date_result.value
    description = extract_description(text, amount)

    if transaction_type == "ambiguous":
        return {
            "type": "ambiguous",
            "amount": amount,
            "category": None,
            "account": None,
            "to_account": None,
            "subject": incoming_source or "",
            "description": description,
            "catatan": extract_note(text),
            "tipe_pengeluaran": "",
            "date": date,
            "date_status": date_result.status,
            "explicit_date_input": date_result.explicit_input,
            "parsed_by": "regex",
            "parse_ambiguity": "runtime_account_source_unavailable",
        }

    if transaction_type == "transfer":
        from_account, to_account = detect_transfer_accounts(text, runtime_account_names=runtime_account_names)

        return {
            "type": "transfer",
            "amount": amount,
            "category": None,
            "account": from_account,
            "to_account": to_account,
            "subject": to_account or "",
            "description": description,
            "catatan": extract_note(text),
            "tipe_pengeluaran": "",
            "date": date,
            "date_status": date_result.status,
            "explicit_date_input": date_result.explicit_input,
            "parsed_by": "regex",
        }

    # Extract category for validation.
    category = detect_category(text, transaction_type)
    # Extract account for validation.
    account = detect_account(text, runtime_account_names=runtime_account_names)
    subject = detect_subject(text, transaction_type, category, description)
    catatan = extract_note(text)
    tipe_pengeluaran = detect_spending_type(text, category, transaction_type)

    return {
        "type": transaction_type,
        "amount": amount,
        "category": category,
        "account": account,
        "to_account": None,
        "subject": subject,
        "description": description,
        "catatan": catatan,
        "tipe_pengeluaran": tipe_pengeluaran,
        "date": date,
        "date_status": date_result.status,
        "explicit_date_input": date_result.explicit_input,
        "parsed_by": "regex",
    }
