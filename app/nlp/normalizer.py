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
    pattern = r"(\d+(?:\.\d+)?)\s*(rb|ribu|k|jt|juta|m|miliar|miliard|milyard)?"
    match = re.search(pattern, text)

    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2) or ""

    multiplier = {
        "rb": 1_000,
        "ribu": 1_000,
        "k": 1_000,
        "jt": 1_000_000,
        "juta": 1_000_000,
        "m": 1_000_000,
        "miliar": 1_000_000_000,
        "miliard": 1_000_000_000,
        "milyard": 1_000_000_000,
    }

    result = number * multiplier.get(unit, 1)
    return int(result)


def normalize_text(text: str) -> str:
    """Lowercase, strip, dan hapus karakter tidak perlu."""
    return text.lower().strip()


def extract_amount_from_text(text: str) -> int | None:
    """
    Cari dan ekstrak nominal dari kalimat penuh.

    Contoh:
        "beli kopi 25rb"         → 25000
        "gaji masuk 8 juta"      → 8000000
        "bayar listrik 150.000"  → 150000
    """
    text = text.lower().strip()

    # Handle format titik ribuan: "150.000" atau "1.500.000"
    # Deteksi: angka dengan titik yang diikuti tepat 3 digit
    ribuan_pattern = r"\b(\d{1,3}(?:\.\d{3})+)\b"
    ribuan_match = re.search(ribuan_pattern, text)
    if ribuan_match:
        clean = ribuan_match.group(1).replace(".", "")
        return int(clean)

    # Handle format normal dengan satuan
    pattern = r"(\d+(?:[.,]\d+)?)\s*(rb|ribu|k|jt|juta|m|miliar|miliard|milyard)?"
    matches = re.findall(pattern, text)

    if not matches:
        return None

    # Ambil angka terbesar yang ditemukan (biasanya nominal transaksi)
    best = None
    best_value = 0

    for number_str, unit in matches:
        number_str = number_str.replace(",", ".")
        try:
            number = float(number_str)
        except ValueError:
            continue

        multiplier = {
            "rb": 1_000,
            "ribu": 1_000,
            "k": 1_000,
            "jt": 1_000_000,
            "juta": 1_000_000,
            "m": 1_000_000,
            "miliar": 1_000_000_000,
            "miliard": 1_000_000_000,
            "milyard": 1_000_000_000,
        }.get(unit, 1)

        value = int(number * multiplier)
        if value > best_value:
            best_value = value
            best = value
    if best:
        best = apply_split_operation(text, best)
    return best

import re

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

    # Pola: "dibagi N", "bagi N", "split N", "/ N"
    split_patterns = [
        r"dibagi\s+(\d+)",
        r"bagi\s+(\d+)",
        r"split\s+(\d+)",
        r"/\s*(\d+)",
        r"untuk\s+(\d+)\s+orang",
        r"bertiga|berdua|berempat|berlima",
        r"(\d+)\s+orang",
        r"patungan\s+(\d+)",
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