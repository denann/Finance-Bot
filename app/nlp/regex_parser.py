"""Rule-based parser for expenses, income, transfers, debt, split bill, pending expenses, dates, amounts, categories, and accounts."""


import re
from datetime import datetime, timedelta
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


def display_account_name(account: str) -> str:
    """Helper for display account name in the NLP and parser layer."""
    return ACCOUNT_DISPLAY_NAMES.get(account, account.upper() if account != "cash" else "Cash")

CATEGORY_KEYWORDS = {
    "Food & Beverage": [
        "makan", "minum", "kopi", "coffee", "teh", "jus", "juice",
        "nasi", "ayam", "soto", "bakso", "mie", "mi", "pizza", "burger",
        "snack", "cemilan", "jajan", "resto", "restoran", "warung",
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


# Debt flow section

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


def parse_debt_input(text: str) -> dict | None:
    """Parse input into structured data for debt input."""
    text_lower = normalize_text(text)

    amount = extract_amount_from_text(text_lower)
    if not amount:
        return None

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

        for w in after.split():
            if any(c.isdigit() for c in w):
                break
            if not words and w in leading_noise:
                continue
            if w in stop_words:
                break
            words.append(w)
            if len(words) == 2:
                break

        return " ".join(words).title() if words else None

    def extract_person_before(text_value: str, keyword: str) -> str | None:
        """Extract the required part of input for person before."""
        if keyword not in text_value:
            return None

        before = text_value.split(keyword)[0].strip()
        noise = ["si", "tadi", "kemarin", "barusan", "nih", "dong"]
        words = [w for w in before.split() if w not in noise]
        name_words = words[-2:] if len(words) >= 2 else words

        return " ".join(name_words).title() if name_words else None

    def clean_fronting_description(person: str, mode: str) -> str:
        """Clean input values for fronting description."""
        desc = extract_description(text, amount) or ""
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

    # Debt flow section
    # Debt flow section
    # Implementation note for this project-specific finance flow.
    # Debt flow section
    # Debt flow section
    # Debt flow section
    # Account flow section
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
    if not offset_match:
        offset_match = re.search(
            r"\b(?:saya|aku|gue|gw|gua)\s+berh?utang\s+(?:ke|sama)\s+"
            r"(?P<person>[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)"
            r"(?=\s*(?:\d|rp|idr))"
            r".*\b(?:potong|kompensasi|offset|netting)\s+(?:dari\s+)?(?P<target>piutang|utang|hutang)\b",
            text_lower,
            flags=re.IGNORECASE,
        )
        offset_self_context = bool(offset_match)
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
        elif offset_self_context:
            target_debt_type = "payable"
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
    # Parser rule note for an Indonesian finance input edge case.
    # Split bill parsing note: separate the paid transaction from each person share.
    # Debt flow section
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
    # Parser rule note for an Indonesian finance input edge case.
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
    # Parser rule note for an Indonesian finance input edge case.
    # Debt flow section
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

    # Implementation section
    # Debt flow section
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

    # Implementation section
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

    # Debt flow section
    # Debt flow section
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

    # Debt flow section
    # Debt flow section
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

    # Debt flow section
    # Debt flow section
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

    # Debt flow section
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

    # Debt flow section
    # Debt flow section
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

    # Debt flow section
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

    # Debt flow section
    for kw in DEBT_PAYMENT_KEYWORDS:
        if kw in text_lower:
            person = extract_person_after(text_lower, kw)
            if not person:
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

    # Natural input section
    # Parser rule note for an Indonesian finance input edge case.
    # Debt flow section
    # Parser rule note for an Indonesian finance input edge case.
    natural_borrow_match = re.search(
        r"\b(?:minjem|pinjem|pinjam)\b\s+(?:uang|duit|dana)?\s*(?:ke|sama|dari)?\s*([a-zA-Z][a-zA-Z\s]{0,40}?)(?=\s*\d|\s*(?:rp|idr))",
        text_lower,
    )
    if natural_borrow_match and not re.search(r"\b(?:minjemin|pinjemin)\b", text_lower):
        person = natural_borrow_match.group(1).strip()
        # Parser rule note for an Indonesian finance input edge case.
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

    # Debt flow section
    for kw in DEBT_PAYABLE_KEYWORDS:
        # Debt flow section
        kw_pattern = rf"(?<![a-zA-ZÀ-ÿ]){re.escape(kw)}(?![a-zA-ZÀ-ÿ])"
        if re.search(kw_pattern, text_lower, flags=re.IGNORECASE):
            person = extract_person_after(text_lower, kw)
            return {
                "intent": "add_payable",
                "person_name": person or "",
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
                "raw_input": text,
            }

    # Debt flow section
    for kw in DEBT_RECEIVABLE_KEYWORDS:
        if kw in text_lower:
            person = extract_person_before(text_lower, kw)
            if not person:
                person = extract_person_after(text_lower, kw)

            if person:
                return {
                    "intent": "add_receivable",
                    "person_name": person,
                    "amount": amount,
                    "description": extract_description(text, amount),
                    "date": detect_date(text),
                    "raw_input": text,
                }

    return None


# ── Helper functions ──────────────────────────────────────────────────────────

def detect_type(text: str) -> str | None:
    """Helper for detect type in the NLP and parser layer."""
    text_lower = normalize_text(text)
    account_pattern = r"cash|bri|bsi|bca|dana|gopay|seabank|sea\s*bank"

    # Account flow section
    # Parser rule note for an Indonesian finance input edge case.
    # Debt flow section
    # Account flow section
    incoming_from_person_match = re.search(
        r"^\s*(?:transaksi|transfer(?:an)?|tf|trf|kiriman|uang)\s+(?:masuk\s+)?dari\s+"
        r"([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)(?=\s*(?:\d|rp|idr|ke\s+|via\s+|pakai\s+|pake\s+))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if incoming_from_person_match:
        source = re.sub(r"\s+", " ", incoming_from_person_match.group(1)).strip()
        first_token = source.split()[0] if source else ""
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
    ]
    if any(kw in text_lower for kw in explicit_transfer_keywords):
        if re.search(rf"\b({account_pattern})\b", text_lower, flags=re.IGNORECASE):
            return "transfer"

    # Account flow section
    # Debt flow section
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
    if topup_to_account or topup_ke_account:
        return "transfer"

    # Parser rule note for an Indonesian finance input edge case.
    # Debt flow section
    # Debt flow section
    if re.search(r"\buang\b.*\b(dari|masuk)\b", text_lower):
        return "income"

    for kw in INCOME_KEYWORDS:
        if kw in text_lower:
            return "income"

    for kw in EXPENSE_KEYWORDS:
        if kw in text_lower:
            return "expense"

    return None

def detect_category(text: str, transaction_type: str) -> str:
    """Helper for detect category in the NLP and parser layer."""
    text_lower = normalize_text(text)

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return category

    if transaction_type == "income":
        return "Other Income"

    return "Other Expense"


def detect_account(text: str) -> str | None:
    """Helper for detect account in the NLP and parser layer."""
    text_lower = normalize_text(text)

    for acc in ACCOUNT_NAMES:
        if acc in text_lower:
            return display_account_name(acc)

    return None


def detect_transfer_accounts(text: str) -> tuple[str | None, str | None]:
    """Helper for detect transfer accounts in the NLP and parser layer."""
    text_lower = normalize_text(text)

    account_pattern = r"cash|bri|bsi|bca|dana|gopay|seabank|sea\s*bank"

    def normalize_account_name(raw: str | None) -> str | None:
        """Normalize and clean input for account name."""
        if not raw:
            return None
        clean = re.sub(r"\s+", " ", str(raw).strip().lower())
        if clean == "sea bank":
            clean = "sea bank"
        return display_account_name(clean)

    def iter_accounts() -> list[tuple[int, str]]:
        """Helper for iter accounts in the NLP and parser layer."""
        matches = []
        for match in re.finditer(rf"\b({account_pattern})\b", text_lower, flags=re.IGNORECASE):
            display = normalize_account_name(match.group(1))
            if display:
                matches.append((match.start(), display))
        return matches

    def first_account_after(pattern: str) -> str | None:
        """Helper for first account after in the NLP and parser layer."""
        match = re.search(pattern, text_lower, flags=re.IGNORECASE)
        if not match:
            return None
        return normalize_account_name(match.group(1))

    def first_other_account(excluded: set[str]) -> str | None:
        """Helper for first other account in the NLP and parser layer."""
        for _, account in found:
            if account not in excluded:
                return account
        return None

    found = iter_accounts()

    if not found:
        return None, None

    # Explicit markers.
    source_account = first_account_after(rf"\b(?:dari|from|pakai|pake|via)\s+({account_pattern})\b")
    target_account = first_account_after(rf"\b(?:ke|to|tujuan|rekening\s+tujuan|ke\s+rekening)\s+({account_pattern})\b")

    if source_account and target_account and source_account != target_account:
        return source_account, target_account

    # Account flow section
    topup_target = first_account_after(rf"\b(?:top\s*up|topup|isi|ngisi)\s+({account_pattern})\b")
    if topup_target:
        if source_account and source_account != topup_target:
            return source_account, topup_target

        other_account = first_other_account({topup_target})
        if other_account:
            # Parser rule note for an Indonesian finance input edge case.
            return other_account, topup_target

        return None, topup_target

    # Account flow section
    # Debt flow section
    if source_account:
        other_account = first_other_account({source_account})
        return source_account, other_account

    if target_account:
        other_account = first_other_account({target_account})
        return other_account, target_account

    # Legacy compatibility note for older records or older in-memory state.
    if len(found) >= 2:
        return found[0][1], found[1][1]

    if len(found) == 1:
        return None, found[0][1]

    return None, None

def parse_explicit_date(date_text: str) -> str | None:
    """Parse input into structured data for explicit date."""
    text = str(date_text or "").strip()

    # YYYY-MM-DD atau YYYY/MM/DD
    match_ymd = re.fullmatch(r"(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])", text)
    if match_ymd:
        year = int(match_ymd.group(1))
        month = int(match_ymd.group(2))
        day = int(match_ymd.group(3))

        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None

    # DD-MM-YYYY atau DD/MM/YYYY
    match_dmy = re.fullmatch(r"(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](20\d{2})", text)
    if match_dmy:
        day = int(match_dmy.group(1))
        month = int(match_dmy.group(2))
        year = int(match_dmy.group(3))

        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None

    return None


def parse_day_only_date(day_text: str) -> str | None:
    """Parse input into structured data for day only date."""
    clean = str(day_text or "").strip()

    if not re.fullmatch(r"0?[1-9]|[12]\d|3[01]", clean):
        return None

    today = datetime.now().date()
    day = int(clean)

    try:
        return datetime(today.year, today.month, day).strftime("%Y-%m-%d")
    except ValueError:
        return None


def strip_date_phrases(text: str) -> str:
    """Helper for strip date phrases in the NLP and parser layer."""
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


def parse_relative_number(value: str) -> int | None:
    """Parse input into structured data for relative number."""
    clean = str(value or "").strip().lower()

    if clean.isdigit():
        return int(clean)

    return NUMBER_WORDS_ID.get(clean)

def detect_relative_date(text: str) -> str | None:
    """Helper for detect relative date in the NLP and parser layer."""
    clean = str(text or "").strip().lower()
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
        clean,
        flags=re.IGNORECASE,
    )

    if relative_match:
        number_raw = relative_match.group(1)
        unit = relative_match.group(2).lower()

        number = parse_relative_number(number_raw)

        if not number:
            return None

        if unit == "hari":
            return (today - timedelta(days=number)).strftime("%Y-%m-%d")

        if unit == "minggu":
            return (today - timedelta(weeks=number)).strftime("%Y-%m-%d")

        if unit == "bulan":
            # Date parsing note: keep explicit and relative Indonesian date formats predictable.
            return (today - timedelta(days=number * 30)).strftime("%Y-%m-%d")

    return None

def detect_date(text: str) -> str:
    """Helper for detect date in the NLP and parser layer."""
    clean = str(text or "").strip().lower()
    today = datetime.now().date()

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    prefixed_date_match = re.search(
        r"\b(?:tanggal|tgl|date|pada tanggal)\s+"
        r"("
        r"20\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])"
        r"|"
        r"(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]20\d{2}"
        r")\b",
        clean,
        flags=re.IGNORECASE,
    )

    if prefixed_date_match:
        parsed_date = parse_explicit_date(prefixed_date_match.group(1))
        if parsed_date:
            return parsed_date

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    day_only_match = re.search(
        r"\b(?:tanggal|tgl|tg|date|pada tanggal)\s+"
        r"(0?[1-9]|[12]\d|3[01])\b",
        clean,
        flags=re.IGNORECASE,
    )

    if day_only_match:
        parsed_date = parse_day_only_date(day_only_match.group(1))
        if parsed_date:
            return parsed_date

    # Bare explicit date: 2026-06-01 / 01-06-2026
    bare_date_match = re.search(
        r"\b("
        r"20\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])"
        r"|"
        r"(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]20\d{2}"
        r")\b",
        clean,
        flags=re.IGNORECASE,
    )

    if bare_date_match:
        parsed_date = parse_explicit_date(bare_date_match.group(1))
        if parsed_date:
            return parsed_date

    relative_date = detect_relative_date(clean)
    if relative_date:
        return relative_date

    return today.strftime("%Y-%m-%d")

def extract_description(text: str, amount=None) -> str:
    """Extract the required part of input for description."""
    clean = str(text or "").strip()

    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    clean = re.sub(r"(?<=[A-Za-zÀ-ÖØ-öø-ÿ])(?=\d)", " ", clean)

    # Parser rule note for an Indonesian finance input edge case.
    clean = strip_date_phrases(clean)

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    if amount is not None:
        amount_int = int(float(amount or 0))

        amount_variants = [
            str(amount_int),
            f"{amount_int:,}".replace(",", "."),
            f"{amount_int:,}".replace(",", ","),
        ]

        for variant in amount_variants:
            clean = clean.replace(variant, " ")

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    clean = re.sub(
        r"\b\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)?\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # Parser rule note for an Indonesian finance input edge case.
    # Parser rule note for an Indonesian finance input edge case.
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
    if not has_named_split:
        clean = re.sub(rf"\b{split_word}\b", " ", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\b(?:jadi|orang)\b", " ", clean, flags=re.IGNORECASE)

    # 4. Remove common transaction verbs from the beginning.
    # Account flow section
    # Parser rule note for an Indonesian finance input edge case.
    account_pattern = r"(?:cash|bri|bsi|bca|dana|gopay|seabank|sea\s*bank)"
    person_transfer = re.match(rf"^\s*transfer\s+ke\s+(?!{account_pattern}\b)", clean, flags=re.IGNORECASE)

    if person_transfer:
        start_verbs = r"beli|bayar|byr|jajan|makan|minum|top\s*up|topup|isi|ngisi|gaji|dapet|dapat|terima|masuk|transaksi|kiriman"
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

    # Parser rule note for an Indonesian finance input edge case.
    # Parser rule note for an Indonesian finance input edge case.
    clean = re.sub(r"^\s*dari\s+", " ", clean, flags=re.IGNORECASE)

    # 6. Rapikan spasi.
    clean = re.sub(r"\s+", " ", clean).strip(" .,-;:")

    if not clean:
        return "Transaksi"

    return clean.title()

def detect_subject(text: str, transaction_type: str, category: str, description: str) -> str:
    """Helper for detect subject in the NLP and parser layer."""
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

    for subject, keywords in known_subjects.items():
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


def extract_note(text: str) -> str:
    """Extract the required part of input for note."""
    text_lower = normalize_text(text)

    note = ""

    # Explicit priority: catatan/note/keterangan fields
    explicit_pattern = r"(?:catatan|note|notes|keterangan)\s*[:\-]?\s*(.+)$"
    explicit_match = re.search(explicit_pattern, text_lower)

    if explicit_match:
        note = explicit_match.group(1).strip()
    else:
        # Legacy compatibility note for older records or older in-memory state.
        fallback_pattern = r"(?:buat|untuk)\s+(.+)$"
        fallback_match = re.search(fallback_pattern, text_lower)
        if fallback_match:
            note = fallback_match.group(1).strip()

    if not note:
        return ""

    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    note = re.sub(
        r"\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m|miliar|milyar)?",
        "",
        note,
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
    ]

    for word in noise_words:
        note = re.sub(rf"\b{re.escape(word)}\b", "", note)

    note = " ".join(note.split()).strip()

    return note.title() if note else ""


def detect_spending_type(text: str, category: str, transaction_type: str) -> str:
    """Helper for detect spending type in the NLP and parser layer."""
    if transaction_type != "expense":
        return ""

    text_lower = normalize_text(text)

    for spending_type, keywords in SPENDING_TYPE_KEYWORDS.items():
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

def parse_with_regex(text: str) -> dict | None:
    """Parse input into structured data for with regex."""
    text_without_date = strip_date_phrases(text)
    amount = extract_amount_from_text(text_without_date)
    if not amount:
        return None

    transaction_type = detect_type(text)

    # Legacy compatibility note for older records or older in-memory state.
    # "Nasi kuning 22k 09-05-2026", "Print 6k", "Alquran 80k".
    # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
    # Legacy compatibility note for older records or older in-memory state.
    if not transaction_type:
        plain_description = extract_description(text, amount)
        if re.search(r"[A-Za-zÀ-ÿ]", plain_description or ""):
            transaction_type = "expense"
        else:
            return None

    date = detect_date(text)
    description = extract_description(text, amount)

    if transaction_type == "transfer":
        from_account, to_account = detect_transfer_accounts(text)

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
        }

    category = detect_category(text, transaction_type)
    account = detect_account(text)
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
        "parsed_by": "regex",
    }