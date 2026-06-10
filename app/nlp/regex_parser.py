import re
from datetime import datetime, timedelta
from app.nlp.normalizer import extract_amount_from_text, normalize_text


# ── Keyword maps ──────────────────────────────────────────────────────────────

EXPENSE_KEYWORDS = [
    "beli", "bayar", "bayarin", "byr", "makan", "minum", "jajan",
    "belanja", "isi", "top up", "topup", "transfer ke", "kirim ke",
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
    "setor tunai", "setor ke", "isi", "top up", "topup",
]

ACCOUNT_NAMES = ["cash", "bri", "bsi", "dana", "gopay"]

CATEGORY_KEYWORDS = {
    "Food & Beverage": [
        "makan", "minum", "kopi", "coffee", "teh", "jus", "juice",
        "nasi", "ayam", "soto", "bakso", "mie", "mi", "pizza", "burger",
        "snack", "cemilan", "jajan", "resto", "restoran", "warung",
        "cafe", "kafe", "warteg", "indomaret", "alfamart", "supermarket",
        "beras", "sayur", "buah", "daging", "telur", "susu",
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
        "alat tulis", "fotocopy", "print",
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


# ── Debt parser ───────────────────────────────────────────────────────────────

DEBT_PAYABLE_KEYWORDS = [
    "hutang ke", "utang ke", "pinjem ke", "pinjam ke",
    "hutang sama", "utang sama", "bayar ke",
    "minjem ke",
]

DEBT_RECEIVABLE_KEYWORDS = [
    "pinjemin", "pinjemin ke", "kasih hutang",
    "pinjem", "pinjam", "minjem",
    "hutangin", "utangin",
]

DEBT_PAYMENT_KEYWORDS = [
    "bayar hutang", "bayar utang", "lunasi", "lunasin",
    "cicil hutang", "cicil utang", "bayar cicilan",
    "transfer balik", "kembaliin", "dibalikin",
]


def parse_debt_input(text: str) -> dict | None:
    text_lower = normalize_text(text)

    amount = extract_amount_from_text(text_lower)
    if not amount:
        return None

    def extract_person_after(text_value: str, keyword: str) -> str | None:
        if keyword not in text_value:
            return None

        after = text_value.split(keyword)[-1].strip()
        words = []

        stop_words = [
            "rb", "ribu", "k", "jt", "juta", "rupiah",
            "buat", "untuk", "karena", "catatan", "note",
            "ke", "dari", "di", "pakai", "pake",
        ]

        for w in after.split():
            if any(c.isdigit() for c in w):
                break
            if w in stop_words:
                break
            words.append(w)
            if len(words) == 2:
                break

        return " ".join(words).title() if words else None

    def extract_person_before(text_value: str, keyword: str) -> str | None:
        if keyword not in text_value:
            return None

        before = text_value.split(keyword)[0].strip()
        noise = ["si", "tadi", "kemarin", "barusan", "nih", "dong"]
        words = [w for w in before.split() if w not in noise]
        name_words = words[-2:] if len(words) >= 2 else words

        return " ".join(name_words).title() if name_words else None

    # ── Payment pattern: "Budi bayar 300k", "Budi balikin 300k" ─────────────
    person_payment_patterns = [
        "bayar", "balikin", "kembaliin", "dibalikin", "ngembaliin",
    ]

    for kw in person_payment_patterns:
        if kw in text_lower:
            person = extract_person_before(text_lower, kw)

            # Hindari salah baca transaksi biasa seperti "bayar kos 1jt"
            # Kalau tidak ada person sebelum kata bayar, jangan dianggap debt payment.
            if person:
                return {
                    "intent": "add_payment",
                    "person_name": person,
                    "amount": amount,
                    "description": f"Pembayaran dari/ke {person}",
                    "raw_input": text,
                }

    # ── Payment explicit: "bayar hutang Budi 300k" ───────────────────────────
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
                "raw_input": text,
            }

    # ── Payable: Anda punya utang ke orang ───────────────────────────────────
    for kw in DEBT_PAYABLE_KEYWORDS:
        if kw in text_lower:
            person = extract_person_after(text_lower, kw)
            return {
                "intent": "add_payable",
                "person_name": person or "",
                "amount": amount,
                "description": extract_description(text, amount),
                "raw_input": text,
            }

    # ── Receivable: orang punya utang ke Anda ────────────────────────────────
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
                    "raw_input": text,
                }

    return None


# ── Helper functions ──────────────────────────────────────────────────────────

def detect_type(text: str) -> str | None:
    text_lower = normalize_text(text)

    for kw in TRANSFER_KEYWORDS:
        if kw in text_lower:
            for acc in ACCOUNT_NAMES:
                if acc in text_lower:
                    return "transfer"

    for kw in INCOME_KEYWORDS:
        if kw in text_lower:
            return "income"

    for kw in EXPENSE_KEYWORDS:
        if kw in text_lower:
            return "expense"

    return None


def detect_category(text: str, transaction_type: str) -> str:
    text_lower = normalize_text(text)

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return category

    if transaction_type == "income":
        return "Other Income"

    return "Other Expense"


def detect_account(text: str) -> str | None:
    text_lower = normalize_text(text)

    for acc in ACCOUNT_NAMES:
        if acc in text_lower:
            return acc.upper() if acc != "cash" else "Cash"

    return None


def detect_transfer_accounts(text: str) -> tuple[str | None, str | None]:
    text_lower = normalize_text(text)
    found = []

    for acc in ACCOUNT_NAMES:
        if acc in text_lower:
            display = acc.upper() if acc != "cash" else "Cash"
            found.append((text_lower.index(acc), display))

    found.sort(key=lambda x: x[0])

    if len(found) >= 2:
        return found[0][1], found[1][1]

    if len(found) == 1:
        return None, found[0][1]

    return None, None


def detect_date(text: str) -> str:
    text_lower = normalize_text(text)
    today = datetime.now()

    if "kemarin" in text_lower:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    if "minggu lalu" in text_lower:
        return (today - timedelta(weeks=1)).strftime("%Y-%m-%d")

    if "2 hari lalu" in text_lower or "dua hari lalu" in text_lower:
        return (today - timedelta(days=2)).strftime("%Y-%m-%d")

    return today.strftime("%Y-%m-%d")


def extract_description(text: str, amount: int) -> str:
    """
    Ambil deskripsi utama transaksi.
    Contoh:
    - "Beli nasi padang 20 k catatan dibagi 2 sama sapto"
      -> "Nasi Padang"
    - "beli obat 45k buat demam"
      -> "Obat"
    - "bayar kos 1.5jt catatan kos bulan Juni"
      -> "Kos"
    """
    desc = text.lower()

    # Buang bagian catatan/note/keterangan terlebih dahulu
    desc = re.split(r"\b(catatan|note|notes|keterangan)\b\s*[:\-]?", desc)[0]

    # Untuk kata "buat/untuk", hanya buang jika tampak sebagai keterangan tambahan.
    # Contoh "beli obat 45k buat demam" -> desc "beli obat 45k"
    # Tapi ini tidak akan terlalu agresif untuk semua kasus.
    desc = re.split(r"\b(buat|untuk)\b", desc)[0]

    # Buang nominal uang: 20k, 20 k, 20 rb, 1.5jt, 1,5 juta, dll.
    desc = re.sub(
        r"\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m|miliar|milyar)?",
        "",
        desc,
    )

    # Buang pola split/patungan
    desc = re.sub(r"\b(di\s*bagi|dibagi|bagi|split|patungan)\s*\d+\b", "", desc)
    desc = re.sub(r"\b(berdua|bertiga|berempat|berlima)\b", "", desc)
    desc = re.sub(r"\b\d+\s*orang\b", "", desc)

    # Buang kata kerja/noise
    noise_words = [
        "beli", "bayar", "bayarin", "byr",
        "tadi", "tadi pagi", "kemarin", "barusan",
        "udah", "sudah", "lupa", "catat",
        "dong", "ya", "nih", "deh", "tolong",
        "pakai", "pake", "dari",
    ]

    for word in noise_words:
        desc = re.sub(rf"\b{re.escape(word)}\b", "", desc)

    desc = " ".join(desc.split()).strip()

    return desc.title() if desc else "Transaksi"


def detect_subject(text: str, transaction_type: str, category: str, description: str) -> str:
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
    """
    Ambil catatan tambahan.
    Contoh:
    - "beli nasi padang 20 k catatan dibagi 2 sama sapto"
      -> "Sama Sapto"
    - "beli obat 45k buat demam"
      -> "Demam"
    - "bayar kos 1.5jt catatan kos bulan Juni"
      -> "Kos Bulan Juni"
    """
    text_lower = normalize_text(text)

    note = ""

    # Prioritas eksplisit: catatan/note/keterangan
    explicit_pattern = r"(?:catatan|note|notes|keterangan)\s*[:\-]?\s*(.+)$"
    explicit_match = re.search(explicit_pattern, text_lower)

    if explicit_match:
        note = explicit_match.group(1).strip()
    else:
        # Fallback: buat/untuk
        fallback_pattern = r"(?:buat|untuk)\s+(.+)$"
        fallback_match = re.search(fallback_pattern, text_lower)
        if fallback_match:
            note = fallback_match.group(1).strip()

    if not note:
        return ""

    # Buang nominal uang di catatan
    note = re.sub(
        r"\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m|miliar|milyar)?",
        "",
        note,
    )

    # Kalau catatan berisi pola split, bersihkan jadi konteks orangnya saja
    # "dibagi 2 sama sapto" -> "sama sapto"
    note = re.sub(r"\b(di\s*bagi|dibagi|bagi|split|patungan)\s*\d+\b", "", note)

    # Buang sisa angka orang
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
    amount = extract_amount_from_text(text)
    if not amount:
        return None

    transaction_type = detect_type(text)
    if not transaction_type:
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