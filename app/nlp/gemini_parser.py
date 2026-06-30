import json
import os
from datetime import datetime
from app.config import GEMINI_API_KEY
from app.nlp.gemini_langchain_client import generate_text_with_gemini


GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))


VALID_CATEGORIES = [
    "Food & Beverage", "Transport", "Bills & Utilities", "Shopping",
    "Health", "Entertainment", "Education", "Personal Care",
    "Kos & Utilities", "Zakat & Sedekah", "Investasi", "Other Expense",
    "Salary", "Freelance", "Investment Return", "Other Income",
]

VALID_ACCOUNTS = ["Cash", "BRI", "BSI", "DANA", "GoPay"]

VALID_SPENDING_TYPES = ["Bulanan", "Harian", "Darurat", "Keinginan"]


def build_prompt(user_input: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    expense_categories = [
        c for c in VALID_CATEGORIES
        if c not in ["Salary", "Freelance", "Investment Return", "Other Income"]
    ]

    return f"""
Kamu adalah parser transaksi keuangan pribadi berbahasa Indonesia.
Tugasmu HANYA mengekstrak informasi transaksi dari input user dan mengembalikan JSON.
Jangan tambahkan penjelasan apapun.
Jangan pakai markdown.
Jangan pakai backtick.
Balas hanya JSON murni.

Hari ini: {today}

Kategori pengeluaran valid:
{", ".join(expense_categories)}

Kategori pemasukan valid:
Salary, Freelance, Investment Return, Other Income

Rekening valid:
{", ".join(VALID_ACCOUNTS)}

Tipe pengeluaran valid:
Bulanan, Harian, Darurat, Keinginan

Definisi tipe_pengeluaran:
- Bulanan: pengeluaran rutin bulanan seperti kos, listrik, air, internet, langganan, iuran, cicilan, asuransi.
- Harian: kebutuhan rutin harian seperti makan, minum, bensin, transport harian, laundry, belanja harian.
- Darurat: kebutuhan mendadak atau penting seperti obat, dokter, kerusakan, kecelakaan, service mendadak.
- Keinginan: hiburan, game, nongkrong, belanja non-urgent, liburan, barang yang lebih bersifat wants.

Aturan parsing:
1. type harus salah satu dari: "expense", "income", "transfer".
2. amount harus integer dalam Rupiah, bukan string.
3. Jika ada pola split tanpa nama teman, misalnya "dibagi 2", "bagi 2", "split 2", amount boleh dibagi sesuai angka tersebut karena itu dianggap bagian user.
4. Jika ada pola split bill dengan nama teman, misalnya "22k dibagi 2 sama Raka", "22k bagi 2 sama Fajar Bagas Raka", amount harus tetap total tagihan asli, bukan dibagi. Status sudah dibayar/belum dibayar akan ditangani sistem setelah parsing.
5. category harus dari daftar kategori valid.
6. account adalah rekening asal, null jika tidak disebutkan.
7. to_account hanya diisi jika type = "transfer", null jika bukan transfer.
8. subject adalah pihak/tempat/objek utama transaksi.
   Contoh:
   - "beli nasi padang 20k" → subject: "Nasi Padang"
   - "bayar listrik 200k" → subject: "PLN"
   - "bayar kos 1.5jt" → subject: "Kos"
   - "gaji masuk 5jt" → subject: "Pekerjaan"
   - "beli di Shopee 100k" → subject: "Shopee"
9. description adalah ringkasan transaksi utama, maksimal 50 karakter.
   Jangan masukkan catatan, orang patungan, atau konteks tambahan ke description.
   Contoh:
   - "beli nasi padang 20k catatan dibagi 2 sama Raka" → description: "Nasi Padang"
   - "beli obat 45k buat demam" → description: "Obat"
10. catatan adalah detail tambahan jika ada.
   Contoh:
   - "catatan dibagi 2 sama Raka" → catatan: "Dibagi 2 sama Raka"
   - "buat demam" → catatan: "Demam"
   - Jika tidak ada, isi "".
11. tipe_pengeluaran hanya diisi jika type = "expense". Jika type bukan expense, isi "".
12. date format YYYY-MM-DD. Interpretasi "kemarin", "tadi", "minggu lalu" dari hari ini.
13. parsed_by selalu "gemini".

Input user:
"{user_input}"

Balas HANYA JSON dengan format berikut:
{{
  "type": "expense|income|transfer",
  "amount": 0,
  "category": "nama kategori",
  "account": null,
  "to_account": null,
  "subject": "",
  "description": "",
  "catatan": "",
  "tipe_pengeluaran": "",
  "date": "{today}",
  "parsed_by": "gemini"
}}
""".strip()


def clean_gemini_json(raw_text: str) -> str:
    raw_text = raw_text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    return raw_text


def parse_with_gemini(user_input: str) -> dict | None:
    try:
        prompt = build_prompt(user_input)
        if not GEMINI_API_KEY:
            return None

        response_text = generate_text_with_gemini(
            prompt,
            model_name=GEMINI_TEXT_MODEL,
            temperature=0.0,
        )

        if not response_text:
            return None

        raw_text = clean_gemini_json(response_text)
        parsed = json.loads(raw_text)

        required_fields = ["type", "amount", "category", "date"]
        for field in required_fields:
            if field not in parsed:
                return None

        if parsed["type"] not in ["expense", "income", "transfer"]:
            return None

        parsed["amount"] = int(parsed["amount"])
        if parsed["amount"] <= 0:
            return None

        if parsed["type"] == "transfer":
            parsed["category"] = None
        elif parsed.get("category") not in VALID_CATEGORIES:
            parsed["category"] = (
                "Other Income"
                if parsed["type"] == "income"
                else "Other Expense"
            )

        if parsed.get("account") not in VALID_ACCOUNTS:
            parsed["account"] = None

        if parsed.get("to_account") not in VALID_ACCOUNTS:
            parsed["to_account"] = None

        if parsed["type"] != "expense":
            parsed["tipe_pengeluaran"] = ""
        elif parsed.get("tipe_pengeluaran") not in VALID_SPENDING_TYPES:
            parsed["tipe_pengeluaran"] = "Harian"

        parsed["subject"] = parsed.get("subject") or ""
        parsed["description"] = parsed.get("description") or "Transaksi"
        parsed["catatan"] = parsed.get("catatan") or ""
        parsed["parsed_by"] = "gemini"

        return parsed

    except json.JSONDecodeError:
        return None
    except Exception:
        return None


def parse_with_pending_fallback(user_input: str) -> dict:
    result = parse_with_gemini(user_input)

    if result is None:
        return {
            "type": "pending",
            "raw_input": user_input,
            "parsed_by": "failed",
            "amount": 0,
            "category": None,
            "account": None,
            "to_account": None,
            "subject": "",
            "description": None,
            "catatan": "",
            "tipe_pengeluaran": "",
            "date": datetime.now().strftime("%Y-%m-%d"),
        }

    return result