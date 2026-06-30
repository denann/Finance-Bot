import re


def normalize_amount(text: str) -> int | None:
    """
    Mengubah berbagai format nominal ke integer.

    Contoh:
        "25rb"      → 25000
        "25k"       → 25000
        "25ribu"    → 25000
        "8juta"     → 8000000
        "8jt"       → 8000000
        "1.5juta"   → 1500000
        "150000"    → 150000
        "150rb"     → 150000
        "1,5jt"     → 1500000
    """
    if not text:
        return None

    # Lowercase dan hapus spasi
    text = text.lower().strip()

    # Ganti koma desimal ke titik agar bisa diparse float
    text = text.replace(",", ".")

    # Cari angka (termasuk desimal) + satuan
    pattern = r"(\d+(?:\.\d+)?)(?:\s*(rb|ribu|k|jt|juta|m|miliar|miliard|milyard)\b)?"
    match = re.search(pattern, text)

    if not match:
        return None

    number_str = match.group(1)
    unit = match.group(2) or ""

    parsed = parse_amount_value(number_str, unit)
    return parsed


def normalize_text(text: str) -> str:
    """Lowercase, strip, dan hapus karakter tidak perlu."""
    return text.lower().strip()


def parse_amount_value(number_str: str, unit: str = "") -> int | None:
    """
    Parse satu token nominal menjadi integer.

    Catatan penting untuk kebiasaan input user:
    - 37.5k    -> 37.500  (titik 1-2 digit dianggap desimal)
    - 331.063k -> 331.063 (titik 3 digit dianggap pemisah ribuan, bukan 331 juta)
    - 331k     -> 331.000
    - 150.000  -> 150.000
    """
    raw = str(number_str or "").strip().lower().replace(",", ".")
    unit = str(unit or "").strip().lower()

    if not raw:
        return None

    try:
        # Dengan unit ribuan/juta, bedakan titik ribuan vs desimal.
        # Kasus khas user: "331.063k" maksudnya Rp331.063, bukan Rp331.063.000.
        if unit in {"rb", "ribu", "k"}:
            if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
                return int(raw.replace(".", ""))
            return int(float(raw) * 1_000)

        if unit in {"jt", "juta", "m"}:
            return int(float(raw) * 1_000_000)

        if unit in {"miliar", "miliard", "milyard"}:
            return int(float(raw) * 1_000_000_000)

        # Tanpa unit: titik dengan grup 3 digit dianggap ribuan.
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
            return int(raw.replace(".", ""))

        return int(float(raw))
    except Exception:
        return None


def extract_amount_from_text(text: str) -> int | None:
    """
    Cari dan ekstrak nominal dari kalimat penuh.

    Contoh:
        "beli kopi 25rb"         → 25000
        "gaji masuk 8 juta"      → 8000000
        "bayar listrik 150.000"  → 150000
    """
    text = text.lower().strip()

    # Handle ekspresi nominal sederhana: "70.100k - 19k", "100k + 25k".
    # Wajib ada unit pada salah satu sisi agar tidak salah baca tanggal seperti 15-05-2026.
    unit_pattern = r"rb|ribu|k|jt|juta|m|miliar|miliard|milyard"
    token_pattern = rf"(\d+(?:[.,]\d+)?)(?:\s*({unit_pattern})\b)?"
    expr_match = re.search(
        rf"{token_pattern}\s*([+\-])\s*{token_pattern}",
        text,
        flags=re.IGNORECASE,
    )
    if expr_match:
        n1, u1, op, n2, u2 = expr_match.groups()
        if u1 or u2:
            v1 = parse_amount_value(n1, u1 or "")
            v2 = parse_amount_value(n2, u2 or "")
            if v1 is not None and v2 is not None:
                result = v1 + v2 if op == "+" else v1 - v2
                if result > 0:
                    return int(result)

    # Handle format titik ribuan: "150.000" atau "1.500.000"
    # Deteksi: angka dengan titik yang diikuti tepat 3 digit
    ribuan_pattern = r"\b(\d{1,3}(?:\.\d{3})+)\b"
    ribuan_match = re.search(ribuan_pattern, text)
    if ribuan_match:
        clean = ribuan_match.group(1).replace(".", "")
        return int(clean)

    # Handle format normal dengan satuan
    pattern = r"(\d+(?:[.,]\d+)?)(?:\s*(rb|ribu|k|jt|juta|m|miliar|miliard|milyard)\b)?"
    matches = re.findall(pattern, text)

    if not matches:
        return None

    # Ambil angka terbesar yang ditemukan (biasanya nominal transaksi)
    best = None
    best_value = 0

    for number_str, unit in matches:
        value = parse_amount_value(number_str, unit or "")
        if value is None:
            continue
        if value > best_value:
            best_value = value
            best = value
    if best:
        best = apply_split_operation(text, best)
    return best


def apply_split_operation(text: str, base_amount: int) -> int:
    """
    Deteksi pola pembagian dan aplikasikan ke amount.

    Contoh:
        "45k dibagi 3"      → 15000
        "90rb split 2"      → 45000
        "120k untuk 4 orang" → 30000
        "60rb patungan 3"   → 20000
    """
    text_lower = text.lower()

    # Jangan bagi amount utama untuk split bill dengan teman.
    # Contoh:
    # - "Tissue 10k bagi 4 sama fajar bagas raka"
    # - "Nasi kuning 22k dibagi 2 sama raka"
    # amount transaksi utama harus tetap total asli; piutang dihitung di handlers.py.
    split_word = r"(?:di\s*-?\s*bagi|dibagi|bagi|patungan|split|share)"
    friend_marker = r"(?:sama|ama|dengan|bareng)"

    if re.search(rf"\b{split_word}\s*(?:jadi\s*)?\d+\s+(?:orang\s+)?{friend_marker}\b", text_lower):
        return base_amount
    if re.search(rf"\b{friend_marker}\s+[a-zA-ZÀ-ÿ\s]{{1,60}}\s+{split_word}\s*(?:jadi\s*)?\d+\b", text_lower):
        return base_amount

    # Shorthand split bill: "46k/4 sama raka bagas fajar".
    # Ini harus dibaca sebagai gross 46k yang dibagi 4, bukan nominal 11.5k.
    # Kalau tidak ada nama/marker teman, "46k/4" tetap boleh dianggap hasil bagi.
    if re.search(rf"/\s*\d+\s+(?:orang\s+)?{friend_marker}\b", text_lower):
        return base_amount
    if re.search(r"/\s*\d+\s+[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ\s,;&]{1,80}", text_lower):
        return base_amount

    # Pola: "dibagi N", "di bagi N", "di-bagi N", "bagi N", "split N", "/ N"
    split_patterns = [
        rf"{split_word}\s*(?:jadi\s*)?(\d+)",
        r"/\s*(\d+)",
        r"untuk\s+(\d+)\s+orang",
        r"bertiga|berdua|berempat|berlima",
        r"(\d+)\s+orang",
    ]

    # Handle kata khusus
    word_map = {
        "berdua": 2,
        "bertiga": 3,
        "berempat": 4,
        "berlima": 5,
    }
    for word, divisor in word_map.items():
        if word in text_lower:
            return base_amount // divisor

    # Handle pola angka
    for pattern in split_patterns:
        match = re.search(pattern, text_lower)
        if match and match.lastindex:
            try:
                divisor = int(match.group(1))
                if divisor > 1:
                    return base_amount // divisor
            except (IndexError, ValueError):
                continue

    return base_amount