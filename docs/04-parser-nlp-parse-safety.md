# 04. Parser, NLP, dan Parse Safety

Layer parser berada di folder `app/nlp/`.

Tujuannya mengubah input natural language seperti:

```text
beli kopi 20k dari Cash
```

menjadi dict terstruktur:

```python
{
    "type": "expense",
    "amount": 20000,
    "category": "Food & Beverage",
    "account": "Cash",
    "description": "Kopi",
    "date": "2026-07-01",
    "parsed_by": "regex"
}
```

## File NLP utama

| File | Fungsi |
|---|---|
| `normalizer.py` | Normalisasi teks dan nominal manusia seperti `20k`, `1.2jt`, `bagi dua` |
| `regex_parser.py` | Parser lokal berbasis rule/regex untuk transaksi umum |
| `parse_safety.py` | Menilai apakah hasil parser aman, perlu warning, Gemini draft, atau klarifikasi |
| `gemini_parser.py` | Fallback parsing transaksi menggunakan Gemini |
| `gemini_image_parser.py` | Parsing struk/gambar menggunakan Gemini Vision |
| `gemini_intent_router.py` | Fallback intent routing untuk command natural |
| `gemini_finance_insight.py` | Prompt dan generator jawaban insight finance |
| `gemini_langchain_client.py` | Wrapper pemanggilan Gemini melalui LangChain |

## Urutan parsing input transaksi

Alur utama ada di `transaction_flow.parse_input()`:

```python
def parse_input(text: str) -> dict:
    result = parse_with_regex(text)
    if result is not None:
        return result

    return parse_with_pending_fallback(text)
```

Artinya:

```text
input user
→ regex parser dulu
→ kalau gagal, fallback Gemini/pending fallback
```

Ini membuat flow lebih hemat dan terkendali karena rule lokal dipakai sebelum AI.

## Regex parser

File: `app/nlp/regex_parser.py`

Fungsi penting:

| Fungsi | Tujuan |
|---|---|
| `parse_with_regex()` | Fungsi utama parser transaksi |
| `parse_debt_input()` | Parser khusus hutang/piutang/talangin/ditalangin |
| `detect_type()` | Mendeteksi expense, income, transfer |
| `detect_category()` | Menentukan kategori transaksi |
| `detect_account()` | Mendeteksi rekening sumber |
| `detect_transfer_accounts()` | Mendeteksi transfer antar rekening |
| `detect_date()` | Mendeteksi tanggal eksplisit/relatif |
| `detect_subject()` | Membuat subject transaksi |
| `extract_description()` | Membersihkan deskripsi transaksi |

Contoh rule yang ditangani:

- `isi bensin 50k dari BRI` → expense Transport
- `isi pulsa 20k dari BRI` → expense Bills & Utilities
- `top up game 50k dari BRI` → expense Entertainment
- `top up DANA 100k dari BRI` → transfer
- `BCA ke DANA 200k` → transfer
- `tf gopay 100k dari BRI` → transfer

## Normalizer

File: `app/nlp/normalizer.py`

Tanggung jawab:

- Mengubah nominal manusia menjadi angka.
- Membersihkan variasi input.
- Mendukung split phrase.

Contoh:

| Input | Output konsep |
|---|---|
| `20k` | `20000` |
| `1.2jt` | `1200000` |
| `2 juta` | `2000000` |
| `bagi dua` | split count 2 |
| `berempat` | split count 4 |

## Parse Safety Routing

File: `app/nlp/parse_safety.py`

Fungsi utama:

```python
assess_parse_safety(text: str, parsed: dict) -> dict
```

Output minimal:

```python
{
    "recommended_action": "warning_preview",
    "risk_level": "medium",
    "risk_flags": ["category_uncertain"],
    "reasons": ["Kategori masih Other Expense, perlu dicek user."]
}
```

Nilai `recommended_action`:

| Action | Artinya |
|---|---|
| `normal_preview` | Hasil parser aman, masuk preview biasa |
| `warning_preview` | Hasil parser mungkin benar, tapi perlu warning |
| `gemini_draft_preview` | Gemini boleh bantu draft, tetap masuk preview warning |
| `clarification` | Jangan preview dulu, tanya maksud user |

## Risk flags penting

| Risk flag | Contoh | Action |
|---|---|---|
| `person_plus_bayar_without_debt_keyword` | `Budi bayar makan 100k` | clarification |
| `ambiguous_money_direction` | `uang Budi 50k` | clarification |
| `balance_or_set_balance_intent` | `saldo BRI 500k` | clarification |
| `topup_non_wallet_target` | `top up game 50k` | expense atau AI review |
| `account_to_account_without_transfer_keyword` | `BCA ke DANA 200k` | transfer |
| `transfer_alias_detected` | `tf DANA 50k dari BCA` | transfer |
| `possible_split_not_attached` | `makan 80k berdua sama Budi` | split/clarification |
| `possible_pending_expense` | `wifi bulan depan 285k` | clarification |
| `category_uncertain` | `makanan ikan 10k` | warning preview |
| `income_category_conflict` | `refund shopee 50k` | warning/Gemini draft |

## Pre-parse clarification vs post-parse safety

`parse_safety.py` punya dua jenis deteksi:

1. **Pre-parse clarification**: sebelum hasil parser dipercaya.
2. **Post-parse flags**: setelah parser menghasilkan dict.

Contoh pre-parse:

```text
Budi bayar makan 100k
```

Kalimat ini ambigu karena bisa berarti:

1. Budi bayar hutang ke user.
2. User mencatat expense makan.
3. Budi yang bayar, tidak perlu ubah saldo user.
4. User menalangi Budi.

Maka bot harus tanya klarifikasi, bukan langsung simpan.

## Gemini sebagai reviewer, bukan decision maker

Gemini dipakai untuk:

- fallback parser jika regex gagal,
- membaca gambar/struk,
- membantu draft parsing untuk input non-sensitive,
- menjelaskan insight finance.

Namun untuk fitur sensitif, Gemini tidak boleh menjadi pengambil keputusan final:

- hutang/piutang,
- bayar hutang,
- talangin/ditalangin,
- split bill,
- debt settlement,
- delete/edit transaction,
- saldo rekening.

Rule lokal dan konfirmasi user tetap menjadi gate utama.
