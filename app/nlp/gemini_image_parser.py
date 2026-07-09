"""Gemini Vision parser that converts receipt or transaction images into draft transaction items."""


# Import json for this module's local operations.
import json
# Import os for this module's local operations.
import os
# Import datetime so this module can use its helpers.
from datetime import datetime

# Import app.config so this module can use its helpers.
from app.config import GEMINI_API_KEY
# Import app.nlp.gemini_langchain_client so this module can use its helpers.
from app.nlp.gemini_langchain_client import generate_text_from_image_with_gemini
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import (
    ensure_category_for_transaction,
    get_account_names_from_sheet,
    get_category_names_from_sheet,
    resolve_account_for_parser,
)
# Import privacy redaction so captions do not pass credential-like text to Gemini.
from app.services.privacy_service import redact_sensitive_text


# Image parsing note: receipt output still goes through preview before saving.
VALID_CATEGORIES = [
    "Food & Beverage", "Transport", "Bills & Utilities", "Shopping",
    "Health", "Entertainment", "Education", "Personal Care",
    "Kos & Utilities", "Zakat & Sedekah", "Investasi", "Other Expense",
    "Salary", "Freelance", "Investment Return", "Other Income",
]

VALID_ACCOUNTS = ["Cash", "BRI", "BSI", "DANA", "GoPay"]
VALID_SPENDING_TYPES = ["Bulanan", "Harian", "Darurat", "Keinginan"]


# Helper for get valid categories.
def get_valid_categories(transaction_type: str | None = None) -> list[str]:
    """Get valid categories from sheet with static fallback."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        names = get_category_names_from_sheet(transaction_type)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        names = []
    return names or list(VALID_CATEGORIES)


# Helper for get valid accounts.
def get_valid_accounts() -> list[str]:
    """Get valid accounts from sheet with static fallback."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        names = get_account_names_from_sheet()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        names = []
    return names or list(VALID_ACCOUNTS)


# Split bill parsing note: separate the paid transaction from each person share.
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash")


# Helper for clean gemini json.
def clean_gemini_json(raw_text: str) -> str:
    """Coordinate the clean gemini json logic in the NLP/parser layer.

    Args:
        raw_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    raw_text = str(raw_text or "").strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            # Prepare raw text from the incoming input.
            raw_text = raw_text[4:]
        # Prepare raw text from the incoming input.
        raw_text = raw_text.strip()

    return raw_text


def build_image_prompt(caption: str = "") -> str:
    """Build the Gemini Vision prompt for receipt or transaction images.

    Args:
        caption: Optional Telegram caption supplied with the image. The caption
            may contain account hints such as `pakai BSI` or parsing hints such
            as `total aja`.

    Returns:
        Prompt text that asks Gemini Vision to return transaction JSON only.

    Side effects:
        Reads category and account names through resolver helpers so the prompt
        can use valid project values. It does not write data or call Gemini.

    Flow constraints:
        Redact credential-like text from the caption before prompting. The image
        result must still go through preview-before-save in the Telegram flow.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    safe_caption = redact_sensitive_text(caption)

    expense_categories = get_valid_categories("expense")
    income_categories = get_valid_categories("income")
    # Extract valid accounts for validation.
    valid_accounts = get_valid_accounts()

    return f"""
Kamu adalah parser transaksi keuangan pribadi berbahasa Indonesia dari GAMBAR.
Gambar bisa berupa struk belanja, nota, screenshot QRIS/e-wallet/bank, atau foto catatan transaksi.
Tugasmu HANYA mengekstrak transaksi dan mengembalikan JSON murni.
Jangan tambahkan penjelasan.
Jangan pakai markdown.
Jangan pakai backtick.

Hari ini: {today}
Caption user jika ada: {safe_caption or "-"}

Kategori pengeluaran valid:
{", ".join(expense_categories)}

Kategori pemasukan valid:
{", ".join(income_categories)}

Rekening valid:
{", ".join(valid_accounts)}

Tipe pengeluaran valid:
Bulanan, Harian, Darurat, Keinginan

ATURAN MODE OUTPUT:
1. DEFAULT untuk struk/nota yang punya baris item jelas: kembalikan BANYAK item, satu transaksi untuk setiap baris barang/jasa.
   Contoh struk berisi Beras, Minyak Goreng, Gula Pasir -> items harus berisi 3 transaksi expense terpisah.
2. Untuk struk restoran/toko, isi objek receipt agar bot bisa menampilkan rincian OCR sebelum memilih rekening.
3. Jangan masukkan service, PPN/tax, biaya layanan, biaya admin, atau diskon sebagai items. Simpan komponen itu di receipt.extra_charges.
4. Kalau user menulis caption seperti "total aja", "satu transaksi", "jangan detail", "rekap total", atau gambar hanya menampilkan total tanpa rincian item, kembalikan SATU transaksi saja dengan amount = total akhir.
5. Kalau gambar jelas berisi beberapa transaksi terpisah dari screenshot mutasi/bank/e-wallet, kembalikan beberapa item sesuai baris transaksi dan isi receipt.is_receipt false.
6. Jangan membuat item dari dashboard/grafik/non-transaksi. Fokus hanya ke area struk/nota/mutasi yang berisi transaksi uang.
7. Jika caption atau gambar berisi credential/token/API key/service account JSON/private key/env value, jangan transkrip credential itu ke output. Abaikan bagian credential dan hanya parse transaksi finance yang jelas.

ATURAN NOMINAL DAN DESKRIPSI:
8. Untuk itemized receipt, amount setiap item = total baris item, bukan harga satuan, jika total baris terlihat.
   Contoh "4.000 Kg x 12.500 Rp 50.000.000" -> amount 50000000.
9. Kalau hanya terlihat harga satuan dan kuantitas, hitung amount = quantity x unit_price.
10. Simpan quantity dan unit_price jika terbaca. Jika tidak terbaca, gunakan quantity 1 dan unit_price sama dengan amount.
11. Jangan menjumlahkan ulang semua item menjadi transaksi tambahan jika kamu sudah mengembalikan itemized rows.
12. Gunakan total akhir hanya untuk validasi, bukan sebagai item tambahan, kecuali mode satu transaksi.
13. Description untuk itemized receipt = nama barang/jasa saja, maksimal 50 karakter.
14. Subject untuk itemized receipt = nama toko/merchant kalau terlihat; kalau tidak terlihat, isi dari nama barang.
15. Catatan boleh berisi info pendek seperti nama toko, nomor struk, qty x harga satuan, atau metode bayar.
16. Jika tanggal di gambar terbaca, gunakan tanggal itu. Kalau tidak ada, gunakan {today}.
17. Jika rekening/metode bayar terlihat dan cocok dengan rekening valid, isi account. Jika tidak yakin, account null.
18. Untuk screenshot transfer antar rekening sendiri, type boleh "transfer" jika rekening asal dan tujuan sama-sama rekening valid.
19. Kalau transfer ke orang/toko dan bukan antar rekening sendiri, itu expense.
20. parsed_by selalu "gemini_image".
21. Jika gambar tidak berisi transaksi keuangan yang jelas, balas items kosong.

ATURAN RECEIPT.EXTRA_CHARGES:
22. Gunakan label "Service" untuk biaya layanan/service charge.
23. Gunakan label "PPN" untuk pajak/tax/restaurant tax.
24. Gunakan label "Diskon" untuk discount/promo/potongan dan set is_discount true.
25. Extra charge amount selalu angka positif. Diskon tetap positif tetapi is_discount true.

ATURAN KATEGORI:
26. Makanan, minuman, restoran, sembako, bahan makanan, beras, minyak, gula, mie masuk "Food & Beverage" kecuali caption menyebut untuk bisnis/stok toko.
27. Belanja barang umum masuk "Shopping".
28. Tagihan/token/listrik/air/internet masuk "Bills & Utilities".
29. Kalau tidak yakin, expense pakai "Other Expense".

Balas HANYA JSON murni dengan format:
{{
  "receipt": {{
    "is_receipt": true,
    "merchant": "",
    "date": "{today}",
    "subtotal": 0,
    "total": 0,
    "extra_charges": [
      {{"label": "Service", "amount": 0, "is_discount": false}},
      {{"label": "PPN", "amount": 0, "is_discount": false}}
    ]
  }},
  "items": [
    {{
      "type": "expense|income|transfer",
      "amount": 0,
      "quantity": 1,
      "unit_price": 0,
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

# Helper for safe number.
def safe_number(value, default: float = 0.0) -> float:
    """Convert a Gemini numeric field into float safely."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        if isinstance(value, str):
            raw = value.strip().replace("Rp", "").replace("rp", "").replace(" ", "")
            raw = "".join(ch for ch in raw if ch.isdigit() or ch in ".,-")
            if "," in raw and "." in raw:
                raw = raw.replace(".", "").replace(",", ".")
            elif "," in raw:
                raw = raw.replace(",", ".")
            elif "." in raw:
                parts = raw.split(".")
                # Handle len(parts) > 1 and all(len(part) == 3 for part in parts[1:]).
                if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
                    raw = raw.replace(".", "")
            return float(raw or default)
        return float(value or default)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return float(default)


# Helper for normalize receipt.
def normalize_receipt(data: dict, items: list[dict]) -> dict:
    """Normalize receipt-level metadata returned by Gemini Vision.

    Args:
        data: Raw JSON object from Gemini.
        items: Normalized transaction items extracted from the image.

    Returns:
        Receipt metadata used by the Telegram receipt review flow.
    """
    raw_receipt = data.get("receipt") if isinstance(data, dict) else {}
    # Prepare raw receipt from the incoming input.
    raw_receipt = raw_receipt if isinstance(raw_receipt, dict) else {}

    merchant = str(raw_receipt.get("merchant") or "").strip()
    # Validate missing merchant and items before continuing.
    if not merchant and items:
        merchant = str(items[0].get("subject") or "").strip()

    date_value = str(raw_receipt.get("date") or "").strip()
    # Run this operation in a guarded block so failures can be handled.
    try:
        datetime.strptime(date_value, "%Y-%m-%d")
    # Handle an expected failure from the guarded operation above.
    except Exception:
        date_value = items[0].get("date") if items else datetime.now().strftime("%Y-%m-%d")

    extra_charges = []
    for charge in raw_receipt.get("extra_charges") or []:
        # Validate missing isinstance(charge, dict) before continuing.
        if not isinstance(charge, dict):
            # Skip the rest of this loop iteration after handling this case.
            continue

        label = str(charge.get("label") or "Biaya tambahan").strip()
        amount = safe_number(charge.get("amount"), 0)
        if amount <= 0:
            # Skip the rest of this loop iteration after handling this case.
            continue

        extra_charges.append({
            "label": label,
            "amount": int(round(amount)),
            "is_discount": bool(charge.get("is_discount")),
        })

    item_total = sum(int(float(item.get("amount", 0) or 0)) for item in items)
    subtotal = int(round(safe_number(raw_receipt.get("subtotal"), item_total)))
    total = int(round(safe_number(raw_receipt.get("total"), 0)))

    return {
        "is_receipt": bool(raw_receipt.get("is_receipt")) or len(items) > 1 or bool(extra_charges),
        "merchant": merchant,
        "date": date_value,
        "subtotal": subtotal or item_total,
        "total": total,
        "extra_charges": extra_charges,
    }


# Helper for normalize item.
def normalize_item(item: dict) -> dict | None:
    """Normalize input values for the normalize item workflow in the NLP/parser layer.

    Args:
        item: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Validate missing isinstance(item, dict) before continuing.
    if not isinstance(item, dict):
        return None

    txn_type = str(item.get("type") or "").strip().lower()
    if txn_type not in ["expense", "income", "transfer"]:
        return None

    # Run this operation in a guarded block so failures can be handled.
    try:
        amount = int(float(item.get("amount", 0) or 0))
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return None

    if amount <= 0:
        return None

    category = item.get("category")
    if txn_type == "transfer":
        # Extract category for validation.
        category = None
    # Use the fallback path when no earlier branch matched.
    else:
        # Extract category for validation.
        category = ensure_category_for_transaction(category, txn_type)

    account = resolve_account_for_parser(item.get("account"))
    to_account = resolve_account_for_parser(item.get("to_account"))

    tipe_pengeluaran = item.get("tipe_pengeluaran") or ""
    if txn_type != "expense":
        tipe_pengeluaran = ""
    # Fall back when tipe pengeluaran not in VALID SPENDING TYPES.
    elif tipe_pengeluaran not in VALID_SPENDING_TYPES:
        tipe_pengeluaran = "Harian"

    date_value = str(item.get("date") or datetime.now().strftime("%Y-%m-%d")).strip()
    # Legacy compatibility note for older records or older in-memory state.
    try:
        datetime.strptime(date_value, "%Y-%m-%d")
    # Handle an expected failure from the guarded operation above.
    except Exception:
        date_value = datetime.now().strftime("%Y-%m-%d")

    raw_text = str(item.get("raw_text") or "").strip()
    catatan = str(item.get("catatan") or "").strip()

    quantity = safe_number(item.get("quantity"), 1)
    if quantity <= 0:
        quantity = 1

    unit_price = safe_number(item.get("unit_price"), 0)
    if unit_price <= 0 and quantity:
        unit_price = amount / quantity

    qty_note = f"Qty {quantity:g} x {int(round(unit_price))}" if unit_price else f"Qty {quantity:g}"
    if qty_note and qty_note.lower() not in catatan.lower():
        catatan = f"{catatan} | {qty_note}".strip(" |")

    if raw_text and raw_text.lower() not in catatan.lower():
        catatan = f"{catatan} | OCR: {raw_text}".strip(" |")

    return {
        "type": txn_type,
        "amount": amount,
        "quantity": quantity,
        "unit_price": unit_price,
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
    """Parse caller input for the parse transactions from image workflow in the NLP/parser layer.

    Args:
        image_bytes: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        mime_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        caption: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Validate missing GEMINI API KEY before continuing.
    if not GEMINI_API_KEY:
        return {
            "success": False,
            "items": [],
            "message": "GEMINI_API_KEY belum tersedia.",
            "raw_response": "",
        }

    # Validate missing image bytes before continuing.
    if not image_bytes:
        return {
            "success": False,
            "items": [],
            "message": "File gambar kosong atau gagal dibaca.",
            "raw_response": "",
        }

    # Run this operation in a guarded block so failures can be handled.
    try:
        prompt = build_image_prompt(caption)
        response_text = generate_text_from_image_with_gemini(
            prompt,
            image_bytes,
            mime_type=mime_type or "image/jpeg",
            model_name=GEMINI_IMAGE_MODEL,
            temperature=0.0,
        )

        # Validate missing response text before continuing.
        if not response_text:
            return {
                "success": False,
                "items": [],
                "message": "Gemini tidak mengembalikan hasil teks.",
                "raw_response": "",
            }

        # Prepare raw text from the incoming input.
        raw_text = clean_gemini_json(response_text)
        data = json.loads(raw_text)
        raw_items = data.get("items", []) if isinstance(data, dict) else []

        items = []
        # Iterate through each raw item.
        for raw_item in raw_items:
            # Normalize normalized before matching.
            normalized = normalize_item(raw_item)
            if normalized:
                # Append the current value to items.
                items.append(normalized)

        receipt = normalize_receipt(data if isinstance(data, dict) else {}, items)

        # Validate missing items before continuing.
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
            "receipt": receipt,
            "message": "OK",
            "raw_response": raw_text,
        }

    # Handle an expected failure from the guarded operation above.
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "items": [],
            "message": f"Output Gemini bukan JSON valid: {str(e)}",
            "raw_response": response_text if "response_text" in locals() else "",
        }
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return {
            "success": False,
            "items": [],
            "message": str(e),
            "raw_response": "",
        }
