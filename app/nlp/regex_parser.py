import re
from datetime import datetime, timedelta
from app.nlp.normalizer import extract_amount_from_text, normalize_text

# ── Keyword maps ──────────────────────────────────────────────────────────────

# Kata kunci yang menandakan PENGELUARAN
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

# Kata kunci yang menandakan PEMASUKAN
INCOME_KEYWORDS = [
    "gaji", "salary", "upah", "honor", "honorarium",
    "dapat", "terima", "dapet", "masuk", "cair",
    "freelance", "proyek", "project", "fee", "komisi",
    "dividen", "return", "hasil", "untung", "profit",
    "bonus", "thr", "cashback", "refund", "balik",
    "transferan masuk", "kiriman",
]

# Kata kunci yang menandakan TRANSFER antar rekening
TRANSFER_KEYWORDS = [
    "transfer", "pindah", "move", "tarik tunai", "tarik",
    "setor tunai", "setor ke", "isi", "top up", "topup",
]

# Nama rekening yang dikenal
ACCOUNT_NAMES = ["cash", "bri", "bsi", "dana", "gopay"]

# Mapping kata kunci ke kategori
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
    from app.nlp.normalizer import extract_amount_from_text
    text_lower = normalize_text(text)

    amount = extract_amount_from_text(text_lower)
    if not amount:
        return None

    def extract_person_after(text: str, keyword: str) -> str | None:
        """Ambil nama setelah keyword. Contoh: 'hutang ke Budi' → 'Budi'"""
        if keyword not in text:
            return None
        after = text.split(keyword)[-1].strip()
        words = []
        for w in after.split():
            if any(c.isdigit() for c in w):
                break
            if w in ["rb", "ribu", "k", "jt", "juta", "rupiah"]:
                break
            words.append(w)
            if len(words) == 2:
                break
        return " ".join(words).title() if words else None

    def extract_person_before(text: str, keyword: str) -> str | None:
        """Ambil nama sebelum keyword. Contoh: 'Andi pinjem 200rb' → 'Andi'"""
        if keyword not in text:
            return None
        before = text.split(keyword)[0].strip()
        # Hapus kata-kata noise
        noise = ["si", "si", "tadi", "kemarin"]
        words = [w for w in before.split() if w not in noise]
        # Ambil maksimal 2 kata terakhir sebagai nama
        name_words = words[-2:] if len(words) >= 2 else words
        return " ".join(name_words).title() if name_words else None

    # ── Cek payment dulu ─────────────────────────────────────────────────────
    for kw in DEBT_PAYMENT_KEYWORDS:
        if kw in text_lower:
            person = extract_person_after(text_lower, kw)
            return {
                "intent": "add_payment",
                "person_name": person or "",
                "amount": amount,
                "description": f"Bayar hutang {person or ''}".strip(),
                "raw_input": text,
            }

    # ── Cek payable (utang Anda ke orang lain) ────────────────────────────────
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

    # ── Cek receivable (orang lain hutang ke Anda) ────────────────────────────
    # Pola 1: nama dulu baru keyword → "Andi pinjem 200rb"
    for kw in DEBT_RECEIVABLE_KEYWORDS:
        if kw in text_lower:
            # Coba ambil nama sebelum keyword dulu
            person = extract_person_before(text_lower, kw)

            # Jika tidak ada sebelum, coba setelah keyword
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
    """Deteksi apakah transaksi expense, income, atau transfer."""
    text_lower = normalize_text(text)

    # Cek transfer dulu — lebih spesifik
    for kw in TRANSFER_KEYWORDS:
        if kw in text_lower:
            # Pastikan ada nama rekening tujuan
            for acc in ACCOUNT_NAMES:
                if acc in text_lower:
                    return "transfer"

    # Cek income
    for kw in INCOME_KEYWORDS:
        if kw in text_lower:
            return "income"

    # Cek expense
    for kw in EXPENSE_KEYWORDS:
        if kw in text_lower:
            return "expense"

    return None


def detect_category(text: str, transaction_type: str) -> str:
    """Deteksi kategori berdasarkan kata kunci."""
    text_lower = normalize_text(text)

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return category

    # Default fallback berdasarkan type
    if transaction_type == "income":
        return "Other Income"
    return "Other Expense"


def detect_account(text: str) -> str | None:
    """Deteksi nama rekening dari teks."""
    text_lower = normalize_text(text)
    for acc in ACCOUNT_NAMES:
        if acc in text_lower:
            return acc.upper() if acc != "cash" else "Cash"
    return None


def detect_transfer_accounts(text: str) -> tuple[str | None, str | None]:
    """
    Untuk transaksi transfer, deteksi rekening asal dan tujuan.
    Return: (from_account, to_account)
    """
    text_lower = normalize_text(text)
    found = []

    for acc in ACCOUNT_NAMES:
        if acc in text_lower:
            display = acc.upper() if acc != "cash" else "Cash"
            found.append((text_lower.index(acc), display))

    # Sort berdasarkan posisi kemunculan di teks
    found.sort(key=lambda x: x[0])

    if len(found) >= 2:
        return found[0][1], found[1][1]
    elif len(found) == 1:
        return None, found[0][1]
    return None, None


def detect_date(text: str) -> str:
    """
    Deteksi tanggal dari teks.
    Default: hari ini.
    Handle: 'kemarin', 'tadi', 'tadi pagi', 'minggu lalu'
    """
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
    Bersihkan teks dari nominal dan kata kunci umum
    untuk dijadikan deskripsi singkat.
    """
    desc = text.lower()

    # Hapus nominal dan satuannya
    desc = re.sub(r"\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta|m|miliar|milyard)?", "", desc)

    # Hapus kata kunci umum yang tidak informatif
    noise_words = [
        "beli", "bayar", "bayarin", "tadi", "tadi pagi",
        "kemarin", "udah", "sudah", "lupa", "catat", "catat",
        "dong", "ya", "nih", "deh",
    ]
    for word in noise_words:
        desc = desc.replace(word, "")

    # Bersihkan spasi berlebih
    desc = " ".join(desc.split()).strip()
    return desc.title() if desc else "Transaksi"


# ── Main parser function ──────────────────────────────────────────────────────

def parse_with_regex(text: str) -> dict | None:
    """
    Entry point utama regex parser.

    Return dict jika berhasil parse, None jika gagal
    (akan di-fallback ke Gemini).

    Return format:
    {
        "type": "expense" | "income" | "transfer",
        "amount": int,
        "category": str,
        "account": str | None,
        "to_account": str | None,
        "description": str,
        "date": str,
        "parsed_by": "regex"
    }
    """
    amount = extract_amount_from_text(text)
    if not amount:
        # Tidak ada nominal → tidak bisa parse → kirim ke Gemini
        return None

    transaction_type = detect_type(text)
    if not transaction_type:
        # Tidak bisa deteksi tipe → kirim ke Gemini
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
            "description": description,
            "date": date,
            "parsed_by": "regex",
        }

    category = detect_category(text, transaction_type)
    account = detect_account(text)

    return {
        "type": transaction_type,
        "amount": amount,
        "category": category,
        "account": account,
        "to_account": None,
        "description": description,
        "date": date,
        "parsed_by": "regex",
    }