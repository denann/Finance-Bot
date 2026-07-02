"""Gemini Vision parser that converts receipt or transaction images into draft transaction items."""


import json
import os
from datetime import datetime

from app.config import GEMINI_API_KEY
from app.nlp.gemini_langchain_client import generate_text_from_image_with_gemini


# Image parsing note: receipt output still goes through preview before saving.
VALID_CATEGORIES = [
    "Food & Beverage", "Transport", "Bills & Utilities", "Shopping",
    "Health", "Entertainment", "Education", "Personal Care",
    "Kos & Utilities", "Zakat & Sedekah", "Investasi", "Other Expense",
    "Salary", "Freelance", "Investment Return", "Other Income",
]

VALID_ACCOUNTS = ["Cash", "BRI", "BSI", "DANA", "GoPay"]
VALID_SPENDING_TYPES = ["Bulanan", "Harian", "Darurat", "Keinginan"]


# Split bill parsing note: separate the paid transaction from each person share.
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash")


def clean_gemini_json(raw_text: str) -> str:
    """Clean input values for gemini json."""
    raw_text = str(raw_text or "").strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    return raw_text


def build_image_prompt(caption: str = "") -> str:
    """Build the data structure or message text for image prompt."""
    today = datetime.now().strftime("%Y-%m-%d")

    expense_categories = [
        c for c in VALID_CATEGORIES
        if c not in ["Salary", "Freelance", "Investment Return", "Other Income"]
    ]

    return f"""
Kamu adalah parser transaksi keuangan pribadi berbahasa Indonesia dari GAMBAR.
Gambar bisa berupa struk belanja, nota, screenshot QRIS/e-wallet/bank, atau foto catatan transaksi.
Tugasmu HANYA mengekstrak transaksi dan mengembalikan JSON murni.
Jangan tambahkan penjelasan.
Jangan pakai markdown.
Jangan pakai backtick.

Hari ini: {today}
Caption user jika ada: {caption or "-"}

Kategori pengeluaran valid:
{", ".join(expense_categories)}

Kategori pemasukan valid:
Salary, Freelance, Investment Return, Other Income

Rekening valid:
{", ".join(VALID_ACCOUNTS)}

Tipe pengeluaran valid:
Bulanan, Harian, Darurat, Keinginan

ATURAN MODE OUTPUT:
1. DEFAULT untuk struk/nota yang punya baris item jelas: kembalikan BANYAK item, satu transaksi untuk setiap baris barang/jasa.
   Contoh struk berisi Beras, Minyak Goreng, Gula Pasir -> items harus berisi 3 transaksi expense terpisah.
2. Kalau user menulis caption seperti "total aja", "satu transaksi", "jangan detail", "rekap total", atau gambar hanya menampilkan total tanpa rincian item, kembalikan SATU transaksi saja dengan amount = total akhir.
3. Kalau gambar jelas berisi beberapa transaksi terpisah dari screenshot mutasi/bank/e-wallet, kembalikan beberapa item sesuai baris transaksi.
4. Jangan membuat item dari dashboard/grafik/non-transaksi. Fokus hanya ke area struk/nota/mutasi yang berisi transaksi uang.

ATURAN NOMINAL DAN DESKRIPSI:
5. Untuk itemized receipt, amount setiap item = total baris item, bukan harga satuan, jika total baris terlihat.
   Contoh "4.000 Kg x 12.500 Rp 50.000.000" -> amount 50000000.
6. Kalau hanya terlihat harga satuan dan kuantitas, hitung amount = quantity x unit price.
7. Jangan menjumlahkan ulang semua item menjadi transaksi tambahan jika kamu sudah mengembalikan itemized rows.
8. Gunakan total akhir hanya untuk validasi, bukan sebagai item tambahan, kecuali mode satu transaksi.
9. Description untuk itemized receipt = nama barang/jasa saja, maksimal 50 karakter.
10. Subject untuk itemized receipt = nama toko/merchant kalau terlihat; kalau tidak terlihat, isi dari nama barang.
11. Catatan boleh berisi info pendek seperti nama toko, nomor struk, qty x harga satuan, atau metode bayar.
12. Jika tanggal di gambar terbaca, gunakan tanggal itu. Kalau tidak ada, gunakan {today}.
13. Jika rekening/metode bayar terlihat dan cocok dengan rekening valid, isi account. Jika tidak yakin, account null.
14. Untuk screenshot transfer antar rekening sendiri, type boleh "transfer" jika rekening asal dan tujuan sama-sama rekening valid.
15. Kalau transfer ke orang/toko dan bukan antar rekening sendiri, itu expense.
16. parsed_by selalu "gemini_image".
17. Jika gambar tidak berisi transaksi keuangan yang jelas, balas items kosong.

ATURAN KATEGORI:
18. Sembako/bahan makanan/beras/minyak/gula/mie masuk "Food & Beverage" kecuali caption menyebut untuk bisnis/stok toko.
19. Belanja barang umum masuk "Shopping".
20. Tagihan/token/listrik/air/internet masuk "Bills & Utilities".
21. Kalau tidak yakin, expense pakai "Other Expense".

Balas HANYA JSON murni dengan format:
{{
  "items": [
    {{
      "type": "expense|income|transfer",
      "amount": 0,
      "category": "nama kategori atau null untuk transfer",
      "account": null,
      "to_account": null,
      "subject": "",
      "description": "",
      "catatan": "",
      "tipe_pengeluaran": "",
      "date": "{today}",
      "raw_text": "teks penting yang terbaca dari gambar, singkat",
      "parsed_by": "gemini_image"
    }}
  ]
}}

Contoh jika gambar struk berisi:
TOKO ABANG, No Struk 211, tanggal 2023-01-10
Beras 4.000 Kg x 12.500 Rp 50.000.000
Minyak Goreng 1600 Kg x 27.500 Rp 44.000.000
Total Rp 94.000.000

Maka output yang benar adalah:
{{
  "items": [
    {{"type":"expense","amount":50000000,"category":"Food & Beverage","account":null,"to_account":null,"subject":"Toko Abang","description":"Beras","catatan":"No. Struk 211 | 4.000 Kg x 12.500","tipe_pengeluaran":"Harian","date":"2023-01-10","raw_text":"Beras 4.000 Kg x 12.500 Rp 50.000.000","parsed_by":"gemini_image"}},
    {{"type":"expense","amount":44000000,"category":"Food & Beverage","account":null,"to_account":null,"subject":"Toko Abang","description":"Minyak Goreng","catatan":"No. Struk 211 | 1600 Kg x 27.500","tipe_pengeluaran":"Harian","date":"2023-01-10","raw_text":"Minyak Goreng 1600 Kg x 27.500 Rp 44.000.000","parsed_by":"gemini_image"}}
  ]
}}
""".strip()

def normalize_item(item: dict) -> dict | None:
    """Normalize and clean input for item."""
    if not isinstance(item, dict):
        return None

    txn_type = str(item.get("type") or "").strip().lower()
    if txn_type not in ["expense", "income", "transfer"]:
        return None

    try:
        amount = int(float(item.get("amount", 0) or 0))
    except Exception:
        return None

    if amount <= 0:
        return None

    category = item.get("category")
    if txn_type == "transfer":
        category = None
    elif category not in VALID_CATEGORIES:
        category = "Other Income" if txn_type == "income" else "Other Expense"

    account = item.get("account")
    if account not in VALID_ACCOUNTS:
        account = None

    to_account = item.get("to_account")
    if to_account not in VALID_ACCOUNTS:
        to_account = None

    tipe_pengeluaran = item.get("tipe_pengeluaran") or ""
    if txn_type != "expense":
        tipe_pengeluaran = ""
    elif tipe_pengeluaran not in VALID_SPENDING_TYPES:
        tipe_pengeluaran = "Harian"

    date_value = str(item.get("date") or datetime.now().strftime("%Y-%m-%d")).strip()
    # Legacy compatibility note for older records or older in-memory state.
    try:
        datetime.strptime(date_value, "%Y-%m-%d")
    except Exception:
        date_value = datetime.now().strftime("%Y-%m-%d")

    raw_text = str(item.get("raw_text") or "").strip()
    catatan = str(item.get("catatan") or "").strip()
    if raw_text and raw_text.lower() not in catatan.lower():
        catatan = f"{catatan} | OCR: {raw_text}".strip(" |")

    return {
        "type": txn_type,
        "amount": amount,
        "category": category,
        "account": account,
        "to_account": to_account,
        "subject": str(item.get("subject") or "").strip(),
        "description": str(item.get("description") or item.get("subject") or "Transaksi dari gambar").strip()[:80],
        "catatan": catatan,
        "tipe_pengeluaran": tipe_pengeluaran,
        "date": date_value,
        "parsed_by": "gemini_image",
    }


def parse_transactions_from_image(image_bytes: bytes, mime_type: str = "image/jpeg", caption: str = "") -> dict:
    """Parse input into structured data for transactions from image."""
    if not GEMINI_API_KEY:
        return {
            "success": False,
            "items": [],
            "message": "GEMINI_API_KEY belum tersedia.",
            "raw_response": "",
        }

    if not image_bytes:
        return {
            "success": False,
            "items": [],
            "message": "File gambar kosong atau gagal dibaca.",
            "raw_response": "",
        }

    try:
        prompt = build_image_prompt(caption)
        response_text = generate_text_from_image_with_gemini(
            prompt,
            image_bytes,
            mime_type=mime_type or "image/jpeg",
            model_name=GEMINI_IMAGE_MODEL,
            temperature=0.0,
        )

        if not response_text:
            return {
                "success": False,
                "items": [],
                "message": "Gemini tidak mengembalikan hasil teks.",
                "raw_response": "",
            }

        raw_text = clean_gemini_json(response_text)
        data = json.loads(raw_text)
        raw_items = data.get("items", []) if isinstance(data, dict) else []

        items = []
        for raw_item in raw_items:
            normalized = normalize_item(raw_item)
            if normalized:
                items.append(normalized)

        if not items:
            return {
                "success": False,
                "items": [],
                "message": "Gambar belum terbaca sebagai transaksi keuangan yang jelas.",
                "raw_response": raw_text,
            }

        return {
            "success": True,
            "items": items,
            "message": "OK",
            "raw_response": raw_text,
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "items": [],
            "message": f"Output Gemini bukan JSON valid: {str(e)}",
            "raw_response": response_text if "response_text" in locals() else "",
        }
    except Exception as e:
        return {
            "success": False,
            "items": [],
            "message": str(e),
            "raw_response": "",
        }
