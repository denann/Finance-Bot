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
    return ACCOUNT_DISPLAY_NAMES.get(account, account.upper() if account != "cash" else "Cash")

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
        if keyword not in text_value:
            return None

        before = text_value.split(keyword)[0].strip()
        noise = ["si", "tadi", "kemarin", "barusan", "nih", "dong"]
        words = [w for w in before.split() if w not in noise]
        name_words = words[-2:] if len(words) >= 2 else words

        return " ".join(name_words).title() if name_words else None

    # ── Receivable explicit: "Sapto hutang ke saya 50k" ─────────────────────
    # Artinya Sapto punya hutang ke user, bukan user hutang ke "Saya".
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

    # ── Incoming transfer from person: "transfer dari Alpat 50k" ─────────────
    # Ini bukan outcome dan bukan transfer antar rekening sendiri.
    # Dalam flow debt, frasa ini biasanya berarti pembayaran piutang dari orang tersebut.
    incoming_transfer_match = re.search(
        r"^\s*(?:transfer(?:an)?|tf|trf)\s+(?:masuk\s+)?dari\s+([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s]{0,40}?)(?=\s*\d|\s*(?:rp|idr))",
        text_lower,
        flags=re.IGNORECASE,
    )
    if incoming_transfer_match:
        person = re.sub(r"\s+", " ", incoming_transfer_match.group(1)).strip()
        # Jangan override transfer antar rekening: "transfer dari BCA ke DANA 250k".
        # Kalau setelah "dari" diawali account sendiri, biarkan parse_with_regex yang menangani.
        first_token = person.split()[0] if person else ""
        if person and first_token not in ACCOUNT_NAMES:
            return {
                "intent": "add_payment",
                "person_name": person.title(),
                "amount": amount,
                "description": f"Transfer dari {person.title()}",
                "date": detect_date(text),
                "raw_input": text,
            }

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
                    "date": detect_date(text),
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
                "date": detect_date(text),
                "raw_input": text,
            }

    # ── Payable natural: "minjem uang Annisa 220k" ───────────────────────────
    # Dalam bahasa natural user, pola ini berarti: Anda meminjam uang milik Annisa
    # sehingga Anda punya UTANG ke Annisa. Ini harus dicek sebelum keyword umum
    # "minjem/pinjem/pinjam" yang dipakai untuk pola "Budi minjem 300k".
    natural_borrow_match = re.search(
        r"\b(?:minjem|pinjem|pinjam)\b\s+(?:uang|duit|dana)?\s*(?:ke|sama|dari)?\s*([a-zA-Z][a-zA-Z\s]{0,40}?)(?=\s*\d|\s*(?:rp|idr))",
        text_lower,
    )
    if natural_borrow_match and not re.search(r"\b(?:minjemin|pinjemin)\b", text_lower):
        person = natural_borrow_match.group(1).strip()
        # Bersihkan kata sambung/noise yang kadang ikut kebaca.
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

    # ── Payable: Anda punya utang ke orang ───────────────────────────────────
    for kw in DEBT_PAYABLE_KEYWORDS:
        if kw in text_lower:
            person = extract_person_after(text_lower, kw)
            return {
                "intent": "add_payable",
                "person_name": person or "",
                "amount": amount,
                "description": extract_description(text, amount),
                "date": detect_date(text),
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
                    "date": detect_date(text),
                    "raw_input": text,
                }

    return None


# ── Helper functions ──────────────────────────────────────────────────────────

def detect_type(text: str) -> str | None:
    text_lower = normalize_text(text)

    # Transfer antar rekening hanya dianggap transfer kalau ada nama rekening
    # yang dikenali (Cash/BRI/BSI/DANA/GoPay).
    # Contoh: "ngisi gopay 50k" -> transfer/topup ke GoPay.
    for kw in TRANSFER_KEYWORDS:
        if kw in text_lower:
            for acc in ACCOUNT_NAMES:
                if acc in text_lower:
                    return "transfer"

    # Pola pemasukan natural yang sebelumnya sering gagal:
    # "uang ptpt bulanan dari opik 200k"
    # "uang ptpt bulanan masuk dari alfath 91.457k"
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
            return display_account_name(acc)

    return None


def detect_transfer_accounts(text: str) -> tuple[str | None, str | None]:
    text_lower = normalize_text(text)
    found = []

    for acc in ACCOUNT_NAMES:
        if acc in text_lower:
            display = display_account_name(acc)
            found.append((text_lower.index(acc), display))

    found.sort(key=lambda x: x[0])

    if len(found) >= 2:
        return found[0][1], found[1][1]

    if len(found) == 1:
        return None, found[0][1]

    return None, None

def parse_explicit_date(date_text: str) -> str | None:
    """
    Parse tanggal eksplisit ke format YYYY-MM-DD.

    Support:
    - 2026-06-01
    - 2026/06/01
    - 01-06-2026
    - 01/06/2026
    """
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
    """
    Parse tanggal hanya angka hari dan gunakan bulan/tahun hari ini.

    Support:
    - tanggal 1
    - tgl 1
    - tg 01
    - date 9
    """
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
    """
    Hapus frasa tanggal dari deskripsi.

    Contoh:
    - beli nasi padang 10k minggu lalu -> beli nasi padang 10k
    - beli nasi padang 10k dua hari yang lalu -> beli nasi padang 10k
    - beli nasi padang 10k tanggal 2026-06-01 -> beli nasi padang 10k
    """
    clean = str(text or "")

    # Hapus "tanggal 2026-06-01", "tgl 01-06-2026", dll.
    clean = re.sub(
        r"\b(?:tanggal|tgl|date|pada tanggal)\s+"
        r"(?:20\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])|"
        r"(?:0?[1-9]|[12]\d|3[01])[-/](?:0?[1-9]|1[0-2])[-/]20\d{2})\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # Hapus "tanggal 1", "tgl 1", "tg 01"; bulan/tahun ikut hari ini.
    clean = re.sub(
        r"\b(?:tanggal|tgl|tg|date|pada tanggal)\s+"
        r"(?:0?[1-9]|[12]\d|3[01])\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # Hapus bare date tanpa kata "tanggal".
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

    # Hapus relative date phrases sederhana.
    clean = re.sub(r"\bhari\s+ini\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bkemarin\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bminggu\s+lalu\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bseminggu\s+(?:yang\s+)?lalu\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bsehari\s+(?:yang\s+)?lalu\b", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bsebulan\s+(?:yang\s+)?lalu\b", " ", clean, flags=re.IGNORECASE)

    # Hapus:
    # 2 hari lalu
    # 2 hari yang lalu
    # dua hari lalu
    # dua hari yang lalu
    # tiga minggu lalu
    # 3 minggu yang lalu
    # 2 bulan yang lalu
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
    """
    Parse angka relative date.

    Support:
    - 2
    - dua
    - tiga
    - seminggu
    - sehari
    """
    clean = str(value or "").strip().lower()

    if clean.isdigit():
        return int(clean)

    return NUMBER_WORDS_ID.get(clean)

def detect_relative_date(text: str) -> str | None:
    """
    Deteksi tanggal relatif.

    Support:
    - kemarin
    - hari ini
    - minggu lalu
    - seminggu lalu
    - dua hari yang lalu
    - 2 hari yang lalu
    - tiga minggu lalu
    - 3 minggu yang lalu
    - sebulan lalu
    - 2 bulan yang lalu
    """
    clean = str(text or "").strip().lower()
    today = datetime.now().date()

    if re.search(r"\bhari\s+ini\b", clean):
        return today.strftime("%Y-%m-%d")

    if re.search(r"\bkemarin\b", clean):
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # minggu lalu / seminggu lalu
    if re.search(r"\bminggu\s+lalu\b", clean) or re.search(r"\bseminggu\s+(?:yang\s+)?lalu\b", clean):
        return (today - timedelta(weeks=1)).strftime("%Y-%m-%d")

    # sehari lalu
    if re.search(r"\bsehari\s+(?:yang\s+)?lalu\b", clean):
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # sebulan lalu
    # Simple approach: 1 bulan = 30 hari untuk relative natural input.
    if re.search(r"\bsebulan\s+(?:yang\s+)?lalu\b", clean):
        return (today - timedelta(days=30)).strftime("%Y-%m-%d")

    # Pattern:
    # 2 hari lalu
    # 2 hari yang lalu
    # dua hari lalu
    # dua hari yang lalu
    # 3 minggu lalu
    # tiga minggu yang lalu
    # 2 bulan yang lalu
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
            # Simple approach: 1 bulan = 30 hari.
            return (today - timedelta(days=number * 30)).strftime("%Y-%m-%d")

    return None

def detect_date(text: str) -> str:
    """
    Deteksi tanggal transaksi.

    Priority:
    1. Explicit date: 2026-06-01, 01-06-2026
    2. Relative date: kemarin, minggu lalu, 2 hari lalu, dua minggu lalu, dll.
    3. Default: hari ini
    """
    clean = str(text or "").strip().lower()
    today = datetime.now().date()

    # Explicit date dengan prefix: tanggal 2026-06-01 / tgl 01-06-2026
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

    # Prefix + angka hari saja: tanggal 1 / tgl 1 / tg 01
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
    clean = str(text or "").strip()

    # Bantu kasus typo tanpa spasi: "Sapto241.457k" -> "Sapto 241.457k".
    clean = re.sub(r"(?<=[A-Za-zÀ-ÖØ-öø-ÿ])(?=\d)", " ", clean)

    # 1. Hapus semua informasi waktu agar tidak masuk description.
    clean = strip_date_phrases(clean)

    # 2. Hapus nominal spesifik dari amount kalau dikirim.
    if amount is not None:
        amount_int = int(float(amount or 0))

        amount_variants = [
            str(amount_int),
            f"{amount_int:,}".replace(",", "."),
            f"{amount_int:,}".replace(",", ","),
        ]

        for variant in amount_variants:
            clean = clean.replace(variant, " ")

    # 3. Hapus nominal umum: 10k, 10 k, 25rb, 25 ribu, 1 juta, dst.
    clean = re.sub(
        r"\b\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)?\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # Hapus sisa satuan yang tertinggal setelah angka bertitik ribuan diganti.
    # Contoh: "Alfath 91.457k" -> replace "91.457" menyisakan "k".
    clean = re.sub(
        r"\b(?:rb|ribu|k|jt|juta|m|miliar|miliard|milyard)\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # Kalau split tanpa nama teman, bersihkan kata operasinya dari deskripsi.
    # Contoh: "Bakso 43k dibagi 2" -> "Bakso", bukan "Bakso Dibagi".
    # Untuk split dengan teman, frasa "dibagi ... sama Sapto" sengaja dibiarkan dulu
    # agar handlers.py bisa membersihkan nama teman setelah split bill terdeteksi.
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

    # 4. Hapus kata kerja transaksi umum di awal.
    # Jangan hapus kata "transfer" kalau transfernya ke orang/non-rekening,
    # supaya deskripsi tetap "Transfer Ke Annisa", bukan cuma "Ke Annisa".
    account_pattern = r"(?:cash|bri|bsi|dana|gopay)"
    person_transfer = re.match(rf"^\s*transfer\s+ke\s+(?!{account_pattern}\b)", clean, flags=re.IGNORECASE)

    if person_transfer:
        start_verbs = r"beli|bayar|byr|jajan|makan|minum|top\s*up|topup|isi|ngisi|gaji|dapet|dapat|terima|masuk"
    else:
        start_verbs = r"beli|bayar|byr|jajan|makan|minum|transfer|top\s*up|topup|isi|ngisi|gaji|dapet|dapat|terima|masuk"

    clean = re.sub(
        rf"^\s*({start_verbs})\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # 5. Hapus info rekening sederhana.
    clean = re.sub(
        r"\b(dari|ke|pakai|pake|via)\s+(cash|bri|bsi|dana|gopay)\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )

    # 6. Rapikan spasi.
    clean = re.sub(r"\s+", " ", clean).strip(" .,-;:")

    if not clean:
        return "Transaksi"

    return clean.title()

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
    note = re.sub(r"\b(di\s*-?\s*bagi|dibagi|bagi|split|share|patungan)\s*(?:jadi\s*)?\d+\b", "", note)

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
    text_without_date = strip_date_phrases(text)
    amount = extract_amount_from_text(text_without_date)
    if not amount:
        return None

    transaction_type = detect_type(text)

    # Fallback untuk input expense tanpa kata kerja, terutama bulk entry:
    # "Nasi kuning 22k 09-05-2026", "Print 6k", "Alquran 80k".
    # Selama ada nominal dan masih ada teks deskripsi setelah nominal/tanggal
    # dibersihkan, anggap sebagai expense agar tidak wajib fallback ke Gemini.
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