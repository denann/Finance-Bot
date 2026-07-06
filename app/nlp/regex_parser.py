"""Rule-based parser for expenses, income, transfers, debt, split bill, pending expenses, dates, amounts, categories, and accounts."""


# Import re for this module's local operations.
import re
# Import datetime so this module can use its helpers.
from datetime import datetime, timedelta
# Import app.nlp.normalizer so this module can use its helpers.
from app.nlp.normalizer import extract_amount_from_text, normalize_text


# ── Keyword maps ──────────────────────────────────────────────────────────────

# Open a multi-line structure for the values below.
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
# Close the structure that was opened above.
]

# Open a multi-line structure for the values below.
INCOME_KEYWORDS = [
    "gaji", "salary", "upah", "honor", "honorarium",
    "dapat", "terima", "dapet", "masuk", "cair",
    "freelance", "proyek", "project", "fee", "komisi",
    "dividen", "return", "hasil", "untung", "profit",
    "bonus", "thr", "cashback", "refund", "balik",
    "transferan masuk", "kiriman",
# Close the structure that was opened above.
]

# Open a multi-line structure for the values below.
TRANSFER_KEYWORDS = [
    "transfer", "pindah", "move", "tarik tunai", "tarik",
    "setor tunai", "setor ke", "isi", "ngisi", "top up", "topup",
    "tf", "trf",
# Close the structure that was opened above.
]

ACCOUNT_NAMES = ["cash", "bri", "bsi", "bca", "dana", "gopay", "seabank", "sea bank"]
# Open a multi-line structure for the values below.
ACCOUNT_DISPLAY_NAMES = {
    "cash": "Cash",
    "bri": "BRI",
    "bsi": "BSI",
    "bca": "BCA",
    "dana": "DANA",
    "gopay": "GoPay",
    "seabank": "Seabank",
    "sea bank": "Seabank",
# Close the structure that was opened above.
}


# Define display account name for callers in this flow.
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


# Define get runtime account names for callers in this flow.
def get_runtime_account_names() -> list[str]:
    """Return account names from sheet `accounts` with hard-coded fallback."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Import app.services.resolver_service so this module can use its helpers.
        from app.services.resolver_service import get_account_names_from_sheet

        # Prepare names for the next step.
        names = get_account_names_from_sheet()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Prepare names for the next step.
        names = []

    # Prepare clean names for the next step.
    clean_names = []
    # Process each name in the current collection.
    for name in names or []:
        clean = str(name or "").strip()
        # Handle the case where clean and clean not in clean_names.
        if clean and clean not in clean_names:
            # Update clean names with the current value.
            clean_names.append(clean)

    # Handle the case where clean_names.
    if clean_names:
        # Return clean_names to the caller.
        return clean_names

    return [ACCOUNT_DISPLAY_NAMES.get(acc, acc.title()) for acc in ACCOUNT_NAMES if acc != "sea bank"]


# Define account pattern from sheet for callers in this flow.
def _account_pattern_from_sheet() -> str:
    """Build an account regex pattern from sheet account names."""
    # Prepare names for the next step.
    names = list(get_runtime_account_names())
    # Prepare variants for the next step.
    variants = set()

    # Process each name in the current collection.
    for name in names:
        # Prepare clean for the next step.
        clean = normalize_text(name)
        # Handle the case where clean.
        if clean:
            variants.add(re.escape(clean).replace(r"\ ", r"\s+"))
            variants.add(re.escape(clean.replace(" ", "")))

    # Process each account in the current collection.
    for account in ACCOUNT_NAMES:
        variants.add(re.escape(account).replace(r"\ ", r"\s*"))

    return "|".join(sorted(variants, key=len, reverse=True)) or r"cash|bri|bsi|bca|dana|gopay"


# Define display runtime account name for callers in this flow.
def _display_runtime_account_name(raw: str | None) -> str | None:
    """Resolve a regex account match into the display name from sheet accounts."""
    # Handle the missing or empty raw case.
    if not raw:
        # Return None to the caller.
        return None

    # Prepare clean for the next step.
    clean = normalize_text(raw)
    compact = clean.replace(" ", "")

    # Process each name in the current collection.
    for name in get_runtime_account_names():
        # Prepare name clean for the next step.
        name_clean = normalize_text(name)
        if clean == name_clean or compact == name_clean.replace(" ", ""):
            # Return name to the caller.
            return name

    if clean == "sea bank":
        clean = "sea bank"
    # Return display_account_name(clean) to the caller.
    return display_account_name(clean)



# Define extract debt account for callers in this flow.
def extract_debt_account(text: str) -> str | None:
    """Extract account for debt/talangin flows using explicit account markers."""
    # Prepare text lower for the next step.
    text_lower = normalize_text(text)
    # Prepare account pattern for the next step.
    account_pattern = _account_pattern_from_sheet()
    # Open a multi-line structure for the values below.
    marker_match = re.search(
        rf"\b(?:dari|ke|pakai|pake|via|rekening)\s+({account_pattern})\b",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where marker_match.
    if marker_match:
        # Return _display_runtime_account_name(marker_match.group(1)) to the caller.
        return _display_runtime_account_name(marker_match.group(1))
    # Return detect_account(text) to the caller.
    return detect_account(text)


# Define attach debt account payload for callers in this flow.
def attach_debt_account_payload(payload: dict | None, text: str) -> dict | None:
    """Attach detected account to parsed debt payload if available."""
    # Handle the missing or empty isinstance(payload, dict) case.
    if not isinstance(payload, dict):
        # Return payload to the caller.
        return payload
    # Prepare account for the next step.
    account = extract_debt_account(text)
    if account and not payload.get("account"):
        payload["account"] = account
    # Return payload to the caller.
    return payload

# Open a multi-line structure for the values below.
CATEGORY_KEYWORDS = {
    "Jajan": [
        "jajan", "ngemil", "cemilan", "camilan", "snack",
        "bakso", "donat", "donut", "cilok", "seblak", "batagor", "siomay",
        "gorengan", "es teh", "es kopi", "jajan pasar",
    # Close the structure that was opened above.
    ],
    "Food & Beverage": [
        "makan", "minum", "kopi", "coffee", "teh", "jus", "juice",
        "nasi", "ayam", "soto", "mie", "mi", "pizza", "burger",
        "resto", "restoran", "warung",
        "cafe", "kafe", "warteg", "indomaret", "alfamart", "supermarket",
        "beras", "sayur", "buah", "daging", "telur", "susu",
        "galon", "air galon",
    # Close the structure that was opened above.
    ],
    "Transport": [
        "bensin", "bbm", "pertalite", "pertamax", "solar",
        "grab", "gojek", "ojek", "taksi", "taxi", "angkot", "bus",
        "kereta", "krl", "mrt", "lrt", "tol", "parkir",
        "isi bensin", "isi bbm", "servis motor", "servis mobil",
    # Close the structure that was opened above.
    ],
    "Bills & Utilities": [
        "listrik", "token", "pdam", "air", "internet", "wifi",
        "pulsa", "paket data", "telpon", "telepon", "tagihan",
        "iuran", "ipkl", "pbb",
    # Close the structure that was opened above.
    ],
    "Shopping": [
        "beli baju", "baju", "celana", "sepatu", "sandal",
        "shopee", "tokopedia", "lazada", "tiktok shop",
        "elektronik", "hp", "laptop", "charger", "kabel",
        "perabot", "furniture",
    # Close the structure that was opened above.
    ],
    "Health": [
        "obat", "dokter", "klinik", "puskesmas", "rs", "rumah sakit",
        "apotek", "apotik", "vitamin", "suplemen", "konsultasi",
        "bpjs", "asuransi kesehatan",
    # Close the structure that was opened above.
    ],
    "Entertainment": [
        "nonton", "bioskop", "cinema", "film", "netflix", "spotify",
        "youtube premium", "game", "steam", "mobile legend", "ml",
        "main", "karaoke", "liburan", "wisata", "hotel",
    # Close the structure that was opened above.
    ],
    "Education": [
        "buku", "kursus", "les", "pelatihan", "training", "seminar",
        "udemy", "coursera", "kampus", "kuliah", "spp", "ukt",
        "wisuda", "alat tulis", "fotocopy", "print",
    # Close the structure that was opened above.
    ],
    "Personal Care": [
        "potong rambut", "cukur", "salon", "barbershop",
        "sabun", "sampo", "shampoo", "pasta gigi", "sikat gigi",
        "laundry", "deterjen", "parfum",
    # Close the structure that was opened above.
    ],
    "Kos & Utilities": [
        "kos", "kontrakan", "sewa", "kost", "indekos",
        "bayar kos", "bayar kontrakan",
    # Close the structure that was opened above.
    ],
    "Zakat & Sedekah": [
        "zakat", "sedekah", "infaq", "infak", "wakaf",
        "donasi", "sumbangan", "amal",
    # Close the structure that was opened above.
    ],
    "Investasi": [
        "nabung", "tabungan", "deposito", "investasi",
        "saham", "reksa dana", "reksadana", "crypto",
        "emas", "logam mulia",
    # Close the structure that was opened above.
    ],
    "Salary": [
        "gaji", "salary", "upah", "thr", "bonus", "honor",
    # Close the structure that was opened above.
    ],
    "Freelance": [
        "freelance", "proyek", "project", "fee", "komisi", "jasa",
    # Close the structure that was opened above.
    ],
    "Investment Return": [
        "dividen", "return", "hasil investasi", "untung saham",
        "bunga deposito", "profit",
    # Close the structure that was opened above.
    ],
# Close the structure that was opened above.
}

# Open a multi-line structure for the values below.
SPENDING_TYPE_KEYWORDS = {
    "Bulanan": [
        "kos", "kost", "kontrakan", "sewa", "listrik", "token listrik",
        "pdam", "air", "internet", "wifi", "tagihan", "iuran",
        "langganan", "subscribe", "netflix", "spotify", "youtube premium",
        "cicilan", "bpjs", "asuransi",
    # Close the structure that was opened above.
    ],
    "Darurat": [
        "darurat", "urgent", "mendadak", "obat", "dokter", "klinik",
        "rumah sakit", "rs", "apotek", "tambal ban", "servis mendadak",
        "service mendadak", "rusak", "kecelakaan",
    # Close the structure that was opened above.
    ],
    "Keinginan": [
        "game", "steam", "skin", "nonton", "bioskop", "cinema",
        "liburan", "wisata", "hotel", "jajan mahal", "nongkrong",
        "baju", "sepatu", "parfum", "aksesoris", "hiburan",
    # Close the structure that was opened above.
    ],
    "Harian": [
        "makan", "minum", "kopi", "teh", "nasi", "ayam", "jajan",
        "bensin", "bbm", "parkir", "grab", "gojek", "ojek",
        "laundry", "sabun", "sampo", "belanja harian",
    # Close the structure that was opened above.
    ],
# Close the structure that was opened above.
}


# Debt flow section

# Open a multi-line structure for the values below.
DEBT_PAYABLE_KEYWORDS = [
    "hutang ke", "utang ke", "pinjem ke", "pinjam ke",
    "hutang sama", "utang sama",
    "minjem ke",
# Close the structure that was opened above.
]

# Open a multi-line structure for the values below.
DEBT_RECEIVABLE_KEYWORDS = [
    "piutang ke", "piutang sama", "piutang dari",
    "minjemin", "minjemin ke", "pinjemin", "pinjemin ke", "kasih hutang",
    "pinjem", "pinjam", "minjem",
    "hutangin", "utangin",
# Close the structure that was opened above.
]

# Open a multi-line structure for the values below.
DEBT_PAYMENT_KEYWORDS = [
    "bayar hutang", "bayar utang", "lunasi", "lunasin",
    "cicil hutang", "cicil utang", "bayar cicilan",
    "transfer balik", "kembaliin", "dibalikin",
# Close the structure that was opened above.
]


# Define parse debt input for callers in this flow.
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
        # Return None to the caller.
        return None

    # Prepare text lower for the next step.
    text_lower = normalize_text(text)

    # Prepare amount for the next step.
    amount = extract_amount_from_text(text_lower)
    # Handle the missing or empty amount case.
    if not amount:
        # Return None to the caller.
        return None

    # Define extract person after for callers in this flow.
    def extract_person_after(text_value: str, keyword: str) -> str | None:
        """Extract the required part of input for person after."""
        # Handle the case where keyword not in text_value.
        if keyword not in text_value:
            # Return None to the caller.
            return None

        # Prepare after for the next step.
        after = text_value.split(keyword)[-1].strip()
        # Prepare words for the next step.
        words = []

        # Open a multi-line structure for the values below.
        stop_words = [
            "rb", "ribu", "k", "jt", "juta", "rupiah",
            "buat", "untuk", "karena", "catatan", "note",
            "ke", "dari", "di", "pakai", "pake",
        # Close the structure that was opened above.
        ]
        leading_noise = {"uang", "duit", "dana"}

        # Process each w in the current collection.
        for w in after.split():
            # Handle the case where any(c.isdigit() for c in w).
            if any(c.isdigit() for c in w):
                # Leave the loop after the target condition has been reached.
                break
            # Handle the missing or empty words and w in leading_noise case.
            if not words and w in leading_noise:
                # Skip the rest of this loop iteration after handling this case.
                continue
            # Handle the case where w in stop_words.
            if w in stop_words:
                # Leave the loop after the target condition has been reached.
                break
            # Update words with the current value.
            words.append(w)
            # Handle the case where len(words) == 2.
            if len(words) == 2:
                # Leave the loop after the target condition has been reached.
                break

        return " ".join(words).title() if words else None

    # Define extract person before for callers in this flow.
    def extract_person_before(text_value: str, keyword: str) -> str | None:
        """Extract the required part of input for person before."""
        # Handle the case where keyword not in text_value.
        if keyword not in text_value:
            # Return None to the caller.
            return None

        # Prepare before for the next step.
        before = text_value.split(keyword)[0].strip()
        noise = ["si", "tadi", "kemarin", "barusan", "nih", "dong"]
        # Prepare words for the next step.
        words = [w for w in before.split() if w not in noise]
        # Prepare name words for the next step.
        name_words = words[-2:] if len(words) >= 2 else words

        return " ".join(name_words).title() if name_words else None

    # Define clean fronting description for callers in this flow.
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
        # Prepare desc lower for the next step.
        desc_lower = desc.lower()
        person_pattern = re.escape(str(person or "").lower())

        # Implementation note for this project-specific finance flow.
        # Legacy compatibility note for older records or older in-memory state.
        desc_lower = re.sub(r"^\s*(?:saya|aku|gw|gue)\s+", "", desc_lower)
        if mode == "ditalangin":
            # Open a multi-line structure for the values below.
            desc_lower = re.sub(
                rf"\b(?:nitip|ditalangin|ditalangi|dibayarin|duluin)\b\s*(?:sama|ke)?\s*{person_pattern}\b",
                "",
                # Include this value in the surrounding collection or call.
                desc_lower,
                # Prepare flags for the next step.
                flags=re.IGNORECASE,
            # Close the structure that was opened above.
            )
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Open a multi-line structure for the values below.
            desc_lower = re.sub(
                rf"\b(?:ngetalangin|nalangin|talangin|talangi)\b\s*(?:si\s+)?{person_pattern}\b",
                "",
                # Include this value in the surrounding collection or call.
                desc_lower,
                # Prepare flags for the next step.
                flags=re.IGNORECASE,
            # Close the structure that was opened above.
            )

        desc_lower = re.sub(r"^\s*(?:beli|beliin|belikan|bayar|buat|untuk)\s+", "", desc_lower)
        desc_lower = re.sub(r"\s+", " ", desc_lower).strip()

        # Handle the case where desc_lower.
        if desc_lower:
            # Return desc_lower.title() to the caller.
            return desc_lower.title()
        return desc or "Talangan"


    # Phase 2: payment intent must be evaluated before generic `Budi hutang 50k`
    # receivable patterns, otherwise `Budi bayar utang 50k` becomes `Budi Bayar`.
    person_pays_debt_match = re.search(
        r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+"
        r"(?:bayar|byr|melunasi|lunasin|lunasi|nyicil|cicil|transfer\s+balik|kembaliin|balikin|dibalikin)\s+"
        r"(?:hutang|utang|piutang|debt|cicilan)\b(?=.*(?:\d|rp|idr))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where person_pays_debt_match.
    if person_pays_debt_match:
        person = re.sub(r"\s+", " ", person_pays_debt_match.group("person")).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue", "gua"} and person.lower() not in ACCOUNT_NAMES:
            # Return attach_debt_account_payload({ to the caller.
            return attach_debt_account_payload({
                "intent": "add_payment",
                "person_name": person,
                "amount": amount,
                "description": f"Pembayaran piutang dari {person}",
                "date": detect_date(text),
                "raw_input": text,
                "target_debt_type": "receivable",
            # Close the structure that was opened above.
            }, text)

    # Open a multi-line structure for the values below.
    self_pays_debt_match = re.search(
        r"^\s*(?:saya|aku|gw|gue|gua)\s+"
        r"(?:bayar|byr|melunasi|lunasin|lunasi|nyicil|cicil)\s+"
        r"(?:hutang|utang|debt|cicilan)\s+"
        r"(?:ke|sama)?\s*"
        r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)(?=\s*(?:\d|rp|idr))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where self_pays_debt_match.
    if self_pays_debt_match:
        person = re.sub(r"\s+", " ", self_pays_debt_match.group("person")).strip().title()
        # Handle the case where person.
        if person:
            # Return attach_debt_account_payload({ to the caller.
            return attach_debt_account_payload({
                "intent": "add_payment",
                "person_name": person,
                "amount": amount,
                "description": f"Bayar hutang ke {person}",
                "date": detect_date(text),
                "raw_input": text,
                "target_debt_type": "payable",
            # Close the structure that was opened above.
            }, text)

    # Explicit debt-only syntax: record a payable fact without treating it as
    # money received into an account.
    debt_only_payable_match = re.search(
        r"^\s*(?:cuma\s+|hanya\s+)?(?:catat|catetin|record)\s+"
        r"(?:(?:saya|aku|gue|gw|gua)\s+)?"
        r"(?:(?:punya|ada)\s+)?"
        r"(?:hutang|utang)\s+(?:ke|sama)\s+"
        r"(?P<person>[a-zA-Z][a-zA-Z\s]{0,40}?)(?=\s*(?:\d|rp|idr))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where debt_only_payable_match.
    if debt_only_payable_match:
        person = re.sub(r"\s+", " ", debt_only_payable_match.group("person")).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue", "gua"}:
            # Prepare description for the next step.
            description = extract_description(text, amount)
            # Prepare person pattern for the next step.
            person_pattern = re.escape(person)
            # Keep the saved detail focused on the reason, not the command words.
            description = re.sub(
                rf"^\s*(?:cuma\s+|hanya\s+)?(?:catat|catetin|record)\s+"
                rf"(?:(?:saya|aku|gue|gw|gua)\s+)?"
                rf"(?:(?:punya|ada)\s+)?"
                rf"(?:hutang|utang)\s+(?:ke|sama)\s+{person_pattern}\b",
                "",
                description or "",
                # Prepare flags for the next step.
                flags=re.IGNORECASE,
            # Close the structure that was opened above.
            )
            # Open a multi-line structure for the values below.
            description = re.sub(
                r"^\s*(?:buat|untuk|karena)\s+",
                "",
                # Include this value in the surrounding collection or call.
                description,
                # Prepare flags for the next step.
                flags=re.IGNORECASE,
            ).strip(" .,-:")
            # Return { to the caller.
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
            # Close the structure that was opened above.
            }

    # Offset syntax creates a separate opposite-side debt without auto-netting.
    offset_self_context = False
    # Open a multi-line structure for the values below.
    offset_match = re.search(
        r"\b(?:potong|kurangi|kompensasi|offset|netting)\s+"
        r"(?P<target>piutang|utang|hutang)\s+"
        r"(?:ke|sama|dari)?\s*"
        r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)"
        r"(?=\s*(?:\d|rp|idr))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the missing or empty offset_match case.
    if not offset_match:
        # Open a multi-line structure for the values below.
        offset_match = re.search(
            r"\b(?:saya|aku|gue|gw|gua)\s+berh?utang\s+(?:ke|sama)\s+"
            r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)"
            r"(?=\s*(?:\d|rp|idr))"
            r".*\b(?:potong|kompensasi|offset|netting)\s+(?:dari\s+)?(?P<target>piutang|utang|hutang)\b",
            # Include this value in the surrounding collection or call.
            text_lower,
            # Prepare flags for the next step.
            flags=re.IGNORECASE,
        # Close the structure that was opened above.
        )
        # Prepare offset self context for the next step.
        offset_self_context = bool(offset_match)
    # Handle the case where offset_match.
    if offset_match:
        person = re.sub(r"\s+", " ", offset_match.group("person")).strip().title()
        target_word = str(offset_match.group("target") or "piutang").strip().lower()
        # Parser rule note for an Indonesian finance input edge case.
        # Debt flow section
        # Debt flow section
        # Debt flow section
        # Debt flow section
        if target_word == "piutang":
            target_debt_type = "receivable"
        # Handle the alternate case where offset_self_context.
        elif offset_self_context:
            target_debt_type = "payable"
        # Handle the fallback path after earlier conditions are skipped.
        else:
            target_debt_type = "receivable"
        resulting_debt_type = "payable" if target_debt_type == "receivable" else "receivable"

        if person and person.lower() not in {"saya", "aku", "gw", "gue", "gua"}:
            # Return { to the caller.
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
            # Close the structure that was opened above.
            }

    # ── Covered-by-someone rule ────────────────────────────────────────────────
    # Parser rule note for an Indonesian finance input edge case.
    # Split bill parsing note: separate the paid transaction from each person share.
    # Debt flow section
    ditalangin_person_first_match = re.search(
        r"\b(?:saya|aku|gw|gue)?\s*"
        r"(?:nitip|ditalangin|ditalangi|dibayarin|duluin)\s+"
        r"(?:sama|ke)?\s*(?:si\s+)?"
        r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)"
        r"(?=\s+(?:beli|beliin|belikan|bayar|buat|untuk)\b)",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where ditalangin_person_first_match.
    if ditalangin_person_first_match:
        # Open a multi-line structure for the values below.
        person = re.sub(
            r"\s+",
            " ",
            ditalangin_person_first_match.group("person"),
        # Close the structure that was opened above.
        ).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue"}:
            item_desc = clean_fronting_description(person, "ditalangin")
            # Return { to the caller.
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": f"Ditalangin {person}: {item_desc}",
                "date": detect_date(text),
                "raw_input": text,
                "cashflow_mode": "debt_only",
                "fronting_mode": "ditalangin",
            # Close the structure that was opened above.
            }

    # ── Covered-by-someone rule ────────────────────────────────────────────────
    # Parser rule note for an Indonesian finance input edge case.
    ditalangin_item_by_person_match = re.search(
        r"\b(?:saya|aku|gw|gue)?\s*"
        r"(?:nitip|ditalangin|ditalangi|dibayarin|duluin)\s+"
        r"(?P<item>.+?)\s+"
        r"(?:sama|oleh|ke|dari)\s+(?:si\s+)?"
        r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)"
        r"(?=\s+(?:tanggal|tgl|kemarin|hari\s+ini|besok|\d|rp|idr)|\s*$)",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where ditalangin_item_by_person_match.
    if ditalangin_item_by_person_match:
        # Open a multi-line structure for the values below.
        person = re.sub(
            r"\s+",
            " ",
            ditalangin_item_by_person_match.group("person"),
        # Close the structure that was opened above.
        ).strip().title()
        # Open a multi-line structure for the values below.
        item_desc = re.sub(
            r"\s+",
            " ",
            ditalangin_item_by_person_match.group("item"),
        # Close the structure that was opened above.
        ).strip().title()

        if person and person.lower() not in {"saya", "aku", "gw", "gue"}:
            # Return { to the caller.
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": f"Ditalangin {person}: {item_desc or 'Talangan'}",
                "date": detect_date(text),
                "raw_input": text,
                "cashflow_mode": "debt_only",
                "fronting_mode": "ditalangin",
            # Close the structure that was opened above.
            }

    # ── Fronting-money rule without immediate cashflow ────────────────────────
    # Parser rule note for an Indonesian finance input edge case.
    # Debt flow section
    ditalangin_match = re.search(
        r"\b(?:saya|aku|gw|gue)?\s*(?:nitip|ditalangin|ditalangi|dibayarin|duluin)\s+"
        r"(?:sama|ke)?\s*(?:si\s+)?([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)"
        r"(?=\s+(?:beli|beliin|belikan|bayar|buat|untuk)\b|\s*(?:\d|rp|idr))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where ditalangin_match.
    if ditalangin_match:
        person = re.sub(r"\s+", " ", ditalangin_match.group(1)).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue"}:
            item_desc = clean_fronting_description(person, "ditalangin")
            # Return { to the caller.
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": f"Ditalangin {person}: {item_desc}",
                "date": detect_date(text),
                "raw_input": text,
                "cashflow_mode": "debt_only",
                "fronting_mode": "ditalangin",
            # Close the structure that was opened above.
            }

    # Implementation section
    # Debt flow section
    # Account flow section
    talangin_match = re.search(
        r"\b(?:saya|aku|gw|gue)?\s*(?:ngetalangin|nalangin|talangin|talangi)\s+"
        r"(?:si\s+)?([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)"
        r"(?=\s+(?:beli|beliin|belikan|bayar|buat|untuk)\b|\s*(?:\d|rp|idr))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where talangin_match.
    if talangin_match:
        person = re.sub(r"\s+", " ", talangin_match.group(1)).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue"}:
            item_desc = clean_fronting_description(person, "talangin")
            # Return { to the caller.
            return {
                "intent": "add_receivable",
                "person_name": person,
                "amount": amount,
                "description": f"Talangin {person}: {item_desc}",
                "date": detect_date(text),
                "raw_input": text,
                "cashflow_mode": "cashflow",
                "fronting_mode": "talangin",
            # Close the structure that was opened above.
            }

    # Implementation section
    person_paid_for_me_match = re.search(
        r"^\s*([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+"
        r"(?:ngetalangin|nalangin|talangin|talangi|beliin|belikan|bayarin|membayari)\s+"
        r"(?:saya|aku|gw|gue)\b",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where person_paid_for_me_match.
    if person_paid_for_me_match:
        person = re.sub(r"\s+", " ", person_paid_for_me_match.group(1)).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue"}:
            item_desc = clean_fronting_description(person, "ditalangin")
            # Return { to the caller.
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": f"Ditalangin {person}: {item_desc}",
                "date": detect_date(text),
                "raw_input": text,
                "cashflow_mode": "debt_only",
                "fronting_mode": "ditalangin",
            # Close the structure that was opened above.
            }

    # Debt flow section
    # Debt flow section
    receivable_to_me_match = re.search(
        r"^\s*([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)\s+(?:hutang|utang)\s+ke\s+(?:saya|aku|gw|gue)\b",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where receivable_to_me_match.
    if receivable_to_me_match:
        person = re.sub(r"\s+", " ", receivable_to_me_match.group(1)).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue"}:
            # Return { to the caller.
            return {
                "intent": "add_receivable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            # Close the structure that was opened above.
            }

    # Debt flow section
    # Debt flow section
    explicit_piutang_match = re.search(
        r"\bpiutang\s+(?:ke|sama|dari)?\s*"
        r"([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)(?=\s*(?:\d|rp|idr))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where explicit_piutang_match.
    if explicit_piutang_match:
        person = re.sub(r"\s+", " ", explicit_piutang_match.group(1)).strip().title()
        # Handle the case where person.
        if person:
            # Return { to the caller.
            return {
                "intent": "add_receivable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            # Close the structure that was opened above.
            }

    # Debt flow section
    # Debt flow section
    self_payable_match = re.search(
        r"\b(?:saya|aku|gue|gw|gua)\s+berh?utang\s+(?:ke|sama)\s+"
        r"([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)(?=\s*(?:\d|rp|idr|$))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where self_payable_match.
    if self_payable_match:
        person = re.sub(r"\s+", " ", self_payable_match.group(1)).strip().title()
        # Handle the case where person.
        if person:
            # Return { to the caller.
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            # Close the structure that was opened above.
            }

    # Debt flow section
    other_receivable_match = re.search(
        r"\b([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)\s+berh?utang\s+"
        r"(?:ke|sama)\s+(?:saya|aku|gue|gw|gua)\b",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where other_receivable_match.
    if other_receivable_match:
        person = re.sub(r"\s+", " ", other_receivable_match.group(1)).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue", "gua"}:
            # Return { to the caller.
            return {
                "intent": "add_receivable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            # Close the structure that was opened above.
            }

    # Debt flow section
    # Debt flow section
    short_other_receivable_match = re.search(
        r"\b(?!saya\b|aku\b|gue\b|gw\b|gua\b)"
        r"([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)\s+berh?utang\b"
        r"(?=.*(?:\d|rp|idr))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where short_other_receivable_match.
    if short_other_receivable_match:
        person = re.sub(r"\s+", " ", short_other_receivable_match.group(1)).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue", "gua"}:
            # Return { to the caller.
            return {
                "intent": "add_receivable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            # Close the structure that was opened above.
            }

    # Open a multi-line structure for the values below.
    short_hutang_receivable_match = re.search(
        r"^\s*(?!saya\b|aku\b|gue\b|gw\b|gua\b)"
        r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)\s+"
        r"(?:ada\s+)?(?:hutang|utang)\b(?=.*(?:\d|rp|idr))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where short_hutang_receivable_match.
    if short_hutang_receivable_match:
        person = re.sub(r"\s+", " ", short_hutang_receivable_match.group("person")).strip().title()
        if person and person.lower() not in {"saya", "aku", "gw", "gue", "gua"}:
            # Return { to the caller.
            return {
                "intent": "add_receivable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            # Close the structure that was opened above.
            }

    # Parser rule note for an Indonesian finance input edge case.
    # Debt flow section
    # Split bill parsing note: separate the paid transaction from each person share.
    # Debt flow section

    # Implementation section
    # Parser rule note for an Indonesian finance input edge case.
    # Example cleanup: remove the person prefix so the description stays focused on the expense item.
    # Parser rule note for an Indonesian finance input edge case.
    person_pays_match = re.search(
        r"^\s*(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,30}?)\s+"
        r"(?:bayar|byr|melunasi|lunasin|lunasi|nyicil|cicil|transfer\s+balik|kembaliin|balikin|dibalikin)\b"
        r"(?=.*(?:\d|rp|idr))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    if person_pays_match and re.search(r"\b(?:hutang|utang|piutang|debt|cicil|cicilan|lunas|lunasi|lunasin|melunasi|nyicil|transfer\s+balik|kembaliin|balikin|dibalikin)\b", text_lower):
        person = re.sub(r"\s+", " ", person_pays_match.group("person")).strip().title()
        # Handle the case where (.
        if (
            # Run this statement as part of the current workflow.
            person
            and person.lower() not in {"saya", "aku", "gw", "gue", "gua"}
            # Run this statement as part of the current workflow.
            and person.lower() not in ACCOUNT_NAMES
        # Close the structure that was opened above.
        ):
            # Return { to the caller.
            return {
                "intent": "add_payment",
                "person_name": person,
                "amount": amount,
                "description": f"Pembayaran piutang dari {person}",
                "date": detect_date(text),
                "raw_input": text,
                "target_debt_type": "receivable",
            # Close the structure that was opened above.
            }

    # Debt flow section
    self_pays_match = re.search(
        r"^\s*(?:saya|aku|gw|gue|gua)\s+"
        r"(?:bayar|byr|melunasi|lunasin|lunasi|nyicil|cicil)\s+"
        r"(?:hutang|utang|debt|cicilan)\s+"
        r"(?:ke|sama)?\s*"
        r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)(?=\s*(?:\d|rp|idr))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where self_pays_match.
    if self_pays_match:
        person = re.sub(r"\s+", " ", self_pays_match.group("person")).strip().title()
        # Handle the case where person.
        if person:
            # Return { to the caller.
            return {
                "intent": "add_payment",
                "person_name": person,
                "amount": amount,
                "description": f"Bayar hutang ke {person}",
                "date": detect_date(text),
                "raw_input": text,
                "target_debt_type": "payable",
            # Close the structure that was opened above.
            }

    # Debt flow section
    for kw in DEBT_PAYMENT_KEYWORDS:
        # Handle the case where kw in text_lower.
        if kw in text_lower:
            # Prepare person for the next step.
            person = extract_person_after(text_lower, kw)
            # Handle the missing or empty person case.
            if not person:
                # Prepare person for the next step.
                person = extract_person_before(text_lower, kw)

            # Return { to the caller.
            return {
                "intent": "add_payment",
                "person_name": person or "",
                "amount": amount,
                "description": f"Bayar hutang {person or ''}".strip(),
                "date": detect_date(text),
                "raw_input": text,
                "target_debt_type": "auto",
            # Close the structure that was opened above.
            }

    # Natural input section
    # Parser rule note for an Indonesian finance input edge case.
    # Debt flow section
    # Parser rule note for an Indonesian finance input edge case.
    natural_borrow_match = re.search(
        r"\b(?:minjem|pinjem|pinjam)\b\s+(?:uang|duit|dana)?\s*(?:ke|sama|dari)?\s*([a-zA-Z][a-zA-Z\s]{0,40}?)(?=\s*\d|\s*(?:rp|idr))",
        # Include this value in the surrounding collection or call.
        text_lower,
    # Close the structure that was opened above.
    )
    if natural_borrow_match and not re.search(r"\b(?:minjemin|pinjemin)\b", text_lower):
        # Prepare person for the next step.
        person = natural_borrow_match.group(1).strip()
        # Parser rule note for an Indonesian finance input edge case.
        person = re.sub(r"\b(?:uang|duit|dana|ke|sama|dari)\b", " ", person).strip()
        person = re.sub(r"\s+", " ", person).title()
        # Handle the case where person.
        if person:
            # Return { to the caller.
            return {
                "intent": "add_payable",
                "person_name": person,
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            # Close the structure that was opened above.
            }

    # Debt flow section
    for kw in DEBT_PAYABLE_KEYWORDS:
        # Debt flow section
        kw_pattern = rf"(?<![a-zA-ZÀ-ÿ]){re.escape(kw)}(?![a-zA-ZÀ-ÿ])"
        # Handle the case where re.search(kw_pattern, text_lower, flags=re.IGNORECASE).
        if re.search(kw_pattern, text_lower, flags=re.IGNORECASE):
            # Prepare person for the next step.
            person = extract_person_after(text_lower, kw)
            # Return { to the caller.
            return {
                "intent": "add_payable",
                "person_name": person or "",
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            # Close the structure that was opened above.
            }

    # Debt flow section
    for kw in DEBT_RECEIVABLE_KEYWORDS:
        # Handle the case where kw in text_lower.
        if kw in text_lower:
            # Prepare person for the next step.
            person = extract_person_before(text_lower, kw)
            # Handle the missing or empty person case.
            if not person:
                # Prepare person for the next step.
                person = extract_person_after(text_lower, kw)

            # Handle the case where person.
            if person:
                # Return { to the caller.
                return {
                    "intent": "add_receivable",
                    "person_name": person,
                    "amount": amount,
                    "description": extract_description(text, amount),
                    "date": detect_date(text),
                    "raw_input": text,
                # Close the structure that was opened above.
                }

    # Return None to the caller.
    return None


# ── Helper functions ──────────────────────────────────────────────────────────

# Define detect type for callers in this flow.
def detect_type(text: str) -> str | None:
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
    # Prepare text lower for the next step.
    text_lower = normalize_text(text)
    # Prepare account pattern for the next step.
    account_pattern = _account_pattern_from_sheet()

    # Account flow section
    # Parser rule note for an Indonesian finance input edge case.
    # Debt flow section
    # Account flow section
    incoming_from_person_match = re.search(
        r"^\s*(?:transaksi|transfer(?:an)?|tf|trf|kiriman|uang)\s+(?:masuk\s+)?dari\s+"
        r"([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)(?=\s*(?:\d|rp|idr|ke\s+|via\s+|pakai\s+|pake\s+))",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where incoming_from_person_match.
    if incoming_from_person_match:
        source = re.sub(r"\s+", " ", incoming_from_person_match.group(1)).strip()
        first_token = source.split()[0] if source else ""
        # Handle the case where source and first_token not in ACCOUNT_NAMES.
        if source and first_token not in ACCOUNT_NAMES:
            return "income"

    # Account flow section
    # Parser rule note for an Indonesian finance input edge case.
    if re.search(rf"\b({account_pattern})\s+ke\s+({account_pattern})\b", text_lower, flags=re.IGNORECASE):
        return "transfer"

    # Alias transfer.
    # Parser rule note for an Indonesian finance input edge case.
    if re.search(r"\b(?:tf|trf)\b", text_lower) and re.search(rf"\b({account_pattern})\b", text_lower, flags=re.IGNORECASE):
        return "transfer"

    # Keyword transfer eksplisit selain topup/isi.
    # Debt flow section
    explicit_transfer_keywords = [
        "transfer", "pindah", "move", "tarik tunai", "tarik",
        "setor tunai", "setor ke",
    # Close the structure that was opened above.
    ]
    # Handle the case where any(kw in text_lower for kw in explicit_transfer_keywords).
    if any(kw in text_lower for kw in explicit_transfer_keywords):
        if re.search(rf"\b({account_pattern})\b", text_lower, flags=re.IGNORECASE):
            return "transfer"

    # Account flow section
    # Debt flow section
    topup_to_account = re.search(
        rf"\b(?:top\s*up|topup|isi|ngisi)\s+({account_pattern})\b",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Open a multi-line structure for the values below.
    topup_ke_account = re.search(
        rf"\b(?:top\s*up|topup|isi|ngisi)\b.*\bke\s+({account_pattern})\b",
        # Include this value in the surrounding collection or call.
        text_lower,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where topup_to_account or topup_ke_account.
    if topup_to_account or topup_ke_account:
        return "transfer"

    # Parser rule note for an Indonesian finance input edge case.
    # Debt flow section
    # Debt flow section
    if re.search(r"\buang\b.*\b(dari|masuk)\b", text_lower):
        return "income"

    # Process each kw in the current collection.
    for kw in INCOME_KEYWORDS:
        # Handle the case where kw in text_lower.
        if kw in text_lower:
            return "income"

    # Process each kw in the current collection.
    for kw in EXPENSE_KEYWORDS:
        # Handle the case where kw in text_lower.
        if kw in text_lower:
            return "expense"

    # Return None to the caller.
    return None

# Define detect category for callers in this flow.
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
    # Prepare text lower for the next step.
    text_lower = normalize_text(text)

    # Process each category, keywords in the current collection.
    for category, keywords in CATEGORY_KEYWORDS.items():
        # Process each kw in the current collection.
        for kw in keywords:
            # Handle the case where kw in text_lower.
            if kw in text_lower:
                # Return category to the caller.
                return category

    if transaction_type == "income":
        return "Other Income"

    return "Other Expense"


# Define detect account for callers in this flow.
def detect_account(text: str) -> str | None:
    """Detect an account name using the sheet-backed account resolver."""
    # Prepare text lower for the next step.
    text_lower = normalize_text(text)

    # Process each account_name in the current collection.
    for account_name in sorted(get_runtime_account_names(), key=len, reverse=True):
        # Prepare clean account for the next step.
        clean_account = normalize_text(account_name)
        pattern = re.escape(clean_account).replace(r"\ ", r"\s+")
        if re.search(rf"\b{pattern}\b", text_lower, flags=re.IGNORECASE):
            # Return account_name to the caller.
            return account_name

    # Process each acc in the current collection.
    for acc in ACCOUNT_NAMES:
        escaped_acc = re.escape(acc).replace(r"\ ", r"\s*")
        account_pattern = rf"\b{escaped_acc}\b"

        # Handle the case where re.search(account_pattern, text_lower, flags=re.IGNORECASE).
        if re.search(account_pattern, text_lower, flags=re.IGNORECASE):
            # Return display_account_name(acc) to the caller.
            return display_account_name(acc)

    # Return None to the caller.
    return None


# Define detect transfer accounts for callers in this flow.
def detect_transfer_accounts(text: str) -> tuple[str | None, str | None]:
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
    # Prepare text lower for the next step.
    text_lower = normalize_text(text)

    # Prepare account pattern for the next step.
    account_pattern = _account_pattern_from_sheet()

    # Define normalize account name for callers in this flow.
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
        # Return _display_runtime_account_name(raw) to the caller.
        return _display_runtime_account_name(raw)

    # Define iter accounts for callers in this flow.
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
        # Prepare matches for the next step.
        matches = []
        for match in re.finditer(rf"\b({account_pattern})\b", text_lower, flags=re.IGNORECASE):
            # Prepare display for the next step.
            display = normalize_account_name(match.group(1))
            # Handle the case where display.
            if display:
                # Update matches with the current value.
                matches.append((match.start(), display))
        # Return matches to the caller.
        return matches

    # Define first account after for callers in this flow.
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
        # Prepare match for the next step.
        match = re.search(pattern, text_lower, flags=re.IGNORECASE)
        # Handle the missing or empty match case.
        if not match:
            # Return None to the caller.
            return None
        # Return normalize_account_name(match.group(1)) to the caller.
        return normalize_account_name(match.group(1))

    # Define first other account for callers in this flow.
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
        # Process each _, account in the current collection.
        for _, account in found:
            # Handle the case where account not in excluded.
            if account not in excluded:
                # Return account to the caller.
                return account
        # Return None to the caller.
        return None

    # Prepare found for the next step.
    found = iter_accounts()

    # Handle the missing or empty found case.
    if not found:
        # Return None, None to the caller.
        return None, None

    # Explicit markers.
    source_account = first_account_after(rf"\b(?:dari|from|pakai|pake|via)\s+({account_pattern})\b")
    target_account = first_account_after(rf"\b(?:ke|to|tujuan|rekening\s+tujuan|ke\s+rekening)\s+({account_pattern})\b")

    # Handle the case where source_account and target_account and source_account != targe....
    if source_account and target_account and source_account != target_account:
        # Return source_account, target_account to the caller.
        return source_account, target_account

    # Account flow section
    topup_target = first_account_after(rf"\b(?:top\s*up|topup|isi|ngisi)\s+({account_pattern})\b")
    # Handle the case where topup_target.
    if topup_target:
        # Handle the case where source_account and source_account != topup_target.
        if source_account and source_account != topup_target:
            # Return source_account, topup_target to the caller.
            return source_account, topup_target

        # Prepare other account for the next step.
        other_account = first_other_account({topup_target})
        # Handle the case where other_account.
        if other_account:
            # Parser rule note for an Indonesian finance input edge case.
            return other_account, topup_target

        # Return None, topup_target to the caller.
        return None, topup_target

    # Account flow section
    # Debt flow section
    if source_account:
        # Prepare other account for the next step.
        other_account = first_other_account({source_account})
        # Return source_account, other_account to the caller.
        return source_account, other_account

    # Handle the case where target_account.
    if target_account:
        # Prepare other account for the next step.
        other_account = first_other_account({target_account})
        # Return other_account, target_account to the caller.
        return other_account, target_account

    # Legacy compatibility note for older records or older in-memory state.
    if len(found) >= 2:
        # Return found[0][1], found[1][1] to the caller.
        return found[0][1], found[1][1]

    # Handle the case where len(found) == 1.
    if len(found) == 1:
        # Return None, found[0][1] to the caller.
        return None, found[0][1]

    # Return None, None to the caller.
    return None, None

# Define parse explicit date for callers in this flow.
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
    # Handle the case where match_ymd.
    if match_ymd:
        # Prepare year for the next step.
        year = int(match_ymd.group(1))
        # Prepare month for the next step.
        month = int(match_ymd.group(2))
        # Prepare day for the next step.
        day = int(match_ymd.group(3))

        # Run this operation in a guarded block so failures can be handled.
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        # Handle an expected failure from the guarded operation above.
        except ValueError:
            # Return None to the caller.
            return None

    # DD-MM-YYYY atau DD/MM/YYYY
    match_dmy = re.fullmatch(r"(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](20\d{2})", text)
    # Handle the case where match_dmy.
    if match_dmy:
        # Prepare day for the next step.
        day = int(match_dmy.group(1))
        # Prepare month for the next step.
        month = int(match_dmy.group(2))
        # Prepare year for the next step.
        year = int(match_dmy.group(3))

        # Run this operation in a guarded block so failures can be handled.
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        # Handle an expected failure from the guarded operation above.
        except ValueError:
            # Return None to the caller.
            return None

    # Return None to the caller.
    return None


# Define parse day only date for callers in this flow.
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
        # Return None to the caller.
        return None

    # Prepare today for the next step.
    today = datetime.now().date()
    # Prepare day for the next step.
    day = int(clean)

    # Run this operation in a guarded block so failures can be handled.
    try:
        return datetime(today.year, today.month, day).strftime("%Y-%m-%d")
    # Handle an expected failure from the guarded operation above.
    except ValueError:
        # Return None to the caller.
        return None


# Define strip date phrases for callers in this flow.
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
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    clean = re.sub(
        r"\b(?:tanggal|tgl|tg|date|pada tanggal)\s+"
        r"(?:0?[1-9]|[12]\d|3[01])\b",
        " ",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    clean = re.sub(
        r"\b20\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])\b",
        " ",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Open a multi-line structure for the values below.
    clean = re.sub(
        r"\b(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]20\d{2}\b",
        " ",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
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
    # Parser rule note for an Indonesian finance input edge case.
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
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    clean = re.sub(r"\s+", " ", clean).strip()

    # Return clean to the caller.
    return clean

# Open a multi-line structure for the values below.
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
# Close the structure that was opened above.
}


# Define parse relative number for callers in this flow.
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

    # Handle the case where clean.isdigit().
    if clean.isdigit():
        # Return int(clean) to the caller.
        return int(clean)

    # Return NUMBER_WORDS_ID.get(clean) to the caller.
    return NUMBER_WORDS_ID.get(clean)

# Define detect relative date for callers in this flow.
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
    # Prepare today for the next step.
    today = datetime.now().date()

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
        return (today - timedelta(days=30)).strftime("%Y-%m-%d")

    # Pattern:
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    # 3 minggu lalu
    # Parser rule note for an Indonesian finance input edge case.
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
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Handle the case where relative_match.
    if relative_match:
        # Prepare number raw for the next step.
        number_raw = relative_match.group(1)
        # Prepare unit for the next step.
        unit = relative_match.group(2).lower()

        # Prepare number for the next step.
        number = parse_relative_number(number_raw)

        # Handle the missing or empty number case.
        if not number:
            # Return None to the caller.
            return None

        if unit == "hari":
            return (today - timedelta(days=number)).strftime("%Y-%m-%d")

        if unit == "minggu":
            return (today - timedelta(weeks=number)).strftime("%Y-%m-%d")

        if unit == "bulan":
            # Date parsing note: keep explicit and relative Indonesian date formats predictable.
            return (today - timedelta(days=number * 30)).strftime("%Y-%m-%d")

    # Return None to the caller.
    return None

# Define detect date for callers in this flow.
def detect_date(text: str) -> str:
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
    clean = str(text or "").strip().lower()
    # Prepare today for the next step.
    today = datetime.now().date()

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    prefixed_date_match = re.search(
        r"\b(?:tanggal|tgl|date|pada tanggal)\s+"
        r"("
        r"20\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])"
        r"|"
        r"(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]20\d{2}"
        r")\b",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Handle the case where prefixed_date_match.
    if prefixed_date_match:
        # Prepare parsed date for the next step.
        parsed_date = parse_explicit_date(prefixed_date_match.group(1))
        # Handle the case where parsed_date.
        if parsed_date:
            # Return parsed_date to the caller.
            return parsed_date

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    day_only_match = re.search(
        r"\b(?:tanggal|tgl|tg|date|pada tanggal)\s+"
        r"(0?[1-9]|[12]\d|3[01])\b",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Handle the case where day_only_match.
    if day_only_match:
        # Prepare parsed date for the next step.
        parsed_date = parse_day_only_date(day_only_match.group(1))
        # Handle the case where parsed_date.
        if parsed_date:
            # Return parsed_date to the caller.
            return parsed_date

    # Bare explicit date: 2026-06-01 / 01-06-2026
    bare_date_match = re.search(
        r"\b("
        r"20\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])"
        r"|"
        r"(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]20\d{2}"
        r")\b",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Handle the case where bare_date_match.
    if bare_date_match:
        # Prepare parsed date for the next step.
        parsed_date = parse_explicit_date(bare_date_match.group(1))
        # Handle the case where parsed_date.
        if parsed_date:
            # Return parsed_date to the caller.
            return parsed_date

    # Prepare relative date for the next step.
    relative_date = detect_relative_date(clean)
    # Handle the case where relative_date.
    if relative_date:
        # Return relative_date to the caller.
        return relative_date

    return today.strftime("%Y-%m-%d")

# Define extract description for callers in this flow.
def extract_description(text: str, amount=None) -> str:
    """Extract the required part of input for description."""
    clean = str(text or "").strip()

    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    clean = re.sub(r"(?<=[A-Za-zÀ-ÖØ-öø-ÿ])(?=\d)", " ", clean)

    # Parser rule note for an Indonesian finance input edge case.
    clean = strip_date_phrases(clean)

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    if amount is not None:
        # Prepare amount int for the next step.
        amount_int = int(float(amount or 0))

        # Open a multi-line structure for the values below.
        amount_variants = [
            # Include this value in the surrounding collection or call.
            str(amount_int),
            f"{amount_int:,}".replace(",", "."),
            f"{amount_int:,}".replace(",", ","),
        # Close the structure that was opened above.
        ]

        # Process each variant in the current collection.
        for variant in amount_variants:
            clean = clean.replace(variant, " ")

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    clean = re.sub(
        r"\b\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)?\b",
        " ",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Parser rule note for an Indonesian finance input edge case.
    # Parser rule note for an Indonesian finance input edge case.
    clean = re.sub(
        r"\b(?:rb|ribu|k|jt|juta|m|miliar|miliard|milyard)\b",
        " ",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    # Split bill parsing note: separate the paid transaction from each person share.
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|split|share|patungan)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"
    # Open a multi-line structure for the values below.
    has_named_split = re.search(
        rf"\b{split_word}\s*(?:jadi\s*)?\d*\s*(?:orang\s+)?{friend_marker}\b",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the missing or empty has_named_split case.
    if not has_named_split:
        clean = re.sub(rf"\b{split_word}\b", " ", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\b(?:jadi|orang)\b", " ", clean, flags=re.IGNORECASE)

    # 4. Remove common transaction verbs from the beginning.
    # Account flow section
    # Parser rule note for an Indonesian finance input edge case.
    account_pattern = r"(?:cash|bri|bsi|bca|dana|gopay|seabank|sea\s*bank)"
    person_transfer = re.match(rf"^\s*transfer\s+ke\s+(?!{account_pattern}\b)", clean, flags=re.IGNORECASE)

    # Handle the case where person_transfer.
    if person_transfer:
        start_verbs = r"beli|bayar|byr|jajan|makan|minum|top\s*up|topup|isi|ngisi|gaji|dapet|dapat|terima|masuk|transaksi|kiriman"
    # Handle the fallback path after earlier conditions are skipped.
    else:
        start_verbs = r"beli|bayar|byr|jajan|makan|minum|transfer|transferan|tf|trf|top\s*up|topup|isi|ngisi|gaji|dapet|dapat|terima|masuk|transaksi|kiriman"

    # Open a multi-line structure for the values below.
    clean = re.sub(
        rf"^\s*({start_verbs})\b",
        " ",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Account flow section
    clean = re.sub(
        r"\b(dari|ke|pakai|pake|via)\s+(cash|bri|bsi|bca|dana|gopay|seabank|sea\s*bank)\b",
        " ",
        # Include this value in the surrounding collection or call.
        clean,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Parser rule note for an Indonesian finance input edge case.
    # Parser rule note for an Indonesian finance input edge case.
    clean = re.sub(r"^\s*dari\s+", " ", clean, flags=re.IGNORECASE)

    # 6. Rapikan spasi.
    clean = re.sub(r"\s+", " ", clean).strip(" .,-;:")

    # Handle the missing or empty clean case.
    if not clean:
        return "Transaksi"

    # Return clean.title() to the caller.
    return clean.title()

# Define detect subject for callers in this flow.
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
    # Prepare text lower for the next step.
    text_lower = normalize_text(text)

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    }

    # Process each subject, keywords in the current collection.
    for subject, keywords in known_subjects.items():
        # Process each kw in the current collection.
        for kw in keywords:
            # Handle the case where kw in text_lower.
            if kw in text_lower:
                # Return subject to the caller.
                return subject

    if transaction_type == "income":
        if category == "Salary":
            return "Pekerjaan"
        if category == "Freelance":
            return "Client"
        return "Pemasukan"

    if description and description != "Transaksi":
        # Return description to the caller.
        return description

    return ""


# Define extract note for callers in this flow.
def extract_note(text: str) -> str:
    """Extract the required part of input for note."""
    # Prepare text lower for the next step.
    text_lower = normalize_text(text)

    note = ""

    # Explicit priority: catatan/note/keterangan fields
    explicit_pattern = r"(?:catatan|note|notes|keterangan)\s*[:\-]?\s*(.+)$"
    # Prepare explicit match for the next step.
    explicit_match = re.search(explicit_pattern, text_lower)

    # Handle the case where explicit_match.
    if explicit_match:
        # Prepare note for the next step.
        note = explicit_match.group(1).strip()
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Legacy compatibility note for older records or older in-memory state.
        fallback_pattern = r"(?:buat|untuk)\s+(.+)$"
        # Prepare fallback match for the next step.
        fallback_match = re.search(fallback_pattern, text_lower)
        # Handle the case where fallback_match.
        if fallback_match:
            # Prepare note for the next step.
            note = fallback_match.group(1).strip()

    # Handle the missing or empty note case.
    if not note:
        return ""

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    note = re.sub(
        r"\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m|miliar|milyar)?",
        "",
        # Include this value in the surrounding collection or call.
        note,
    # Close the structure that was opened above.
    )

    # Parser rule note for an Indonesian finance input edge case.
    # "dibagi 2 sama raka" -> "sama raka"
    note = re.sub(r"\b(di\s*-?\s*bagi|dibagi|bagi|split|share|patungan)\s*(?:jadi\s*)?\d+\b", "", note)

    # Parser rule note for an Indonesian finance input edge case.
    note = re.sub(r"\b\d+\s*orang\b", "", note)

    # Buang noise ringan
    noise_words = [
        "catatan", "note", "notes", "keterangan",
        "dong", "ya", "nih", "deh",
    # Close the structure that was opened above.
    ]

    # Process each word in the current collection.
    for word in noise_words:
        note = re.sub(rf"\b{re.escape(word)}\b", "", note)

    note = " ".join(note.split()).strip()

    return note.title() if note else ""


# Define detect spending type for callers in this flow.
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

    # Prepare text lower for the next step.
    text_lower = normalize_text(text)

    # Process each spending_type, keywords in the current collection.
    for spending_type, keywords in SPENDING_TYPE_KEYWORDS.items():
        # Process each kw in the current collection.
        for kw in keywords:
            # Handle the case where kw in text_lower.
            if kw in text_lower:
                # Return spending_type to the caller.
                return spending_type

    if category in ["Kos & Utilities", "Bills & Utilities"]:
        return "Bulanan"

    if category == "Health":
        return "Darurat"

    if category == "Entertainment":
        return "Keinginan"

    return "Harian"


# ── Main parser function ──────────────────────────────────────────────────────

# Define parse with regex for callers in this flow.
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
        # Return None to the caller.
        return None

    # Prepare text without date for the next step.
    text_without_date = strip_date_phrases(text)
    # Prepare amount for the next step.
    amount = extract_amount_from_text(text_without_date)
    # Handle the missing or empty amount case.
    if not amount:
        # Return None to the caller.
        return None

    # Prepare transaction type for the next step.
    transaction_type = detect_type(text)

    # Legacy compatibility note for older records or older in-memory state.
    # "Nasi kuning 22k 09-05-2026", "Print 6k", "Alquran 80k".
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Legacy compatibility note for older records or older in-memory state.
    if not transaction_type:
        # Prepare plain description for the next step.
        plain_description = extract_description(text, amount)
        if re.search(r"[A-Za-zÀ-ÿ]", plain_description or ""):
            transaction_type = "expense"
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Return None to the caller.
            return None

    # Prepare date for the next step.
    date = detect_date(text)
    # Prepare description for the next step.
    description = extract_description(text, amount)

    if transaction_type == "transfer":
        # Run this statement as part of the current workflow.
        from_account, to_account = detect_transfer_accounts(text)

        # Return { to the caller.
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
            "parsed_by": "regex",
        # Close the structure that was opened above.
        }

    # Prepare category for the next step.
    category = detect_category(text, transaction_type)
    # Prepare account for the next step.
    account = detect_account(text)
    # Prepare subject for the next step.
    subject = detect_subject(text, transaction_type, category, description)
    # Prepare catatan for the next step.
    catatan = extract_note(text)
    # Prepare tipe pengeluaran for the next step.
    tipe_pengeluaran = detect_spending_type(text, category, transaction_type)

    # Return { to the caller.
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
        "parsed_by": "regex",
    # Close the structure that was opened above.
    }
