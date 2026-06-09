import json
import google.generativeai as genai
from datetime import datetime
from app.config import GEMINI_API_KEY

# Setup Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3.1-flash-lite")

# Daftar kategori valid — harus konsisten dengan sheet categories
VALID_CATEGORIES = [
    "Food & Beverage", "Transport", "Bills & Utilities", "Shopping",
    "Health", "Entertainment", "Education", "Personal Care",
    "Kos & Utilities", "Zakat & Sedekah", "Investasi", "Other Expense",
    "Salary", "Freelance", "Investment Return", "Other Income",
]

# Daftar rekening valid
VALID_ACCOUNTS = ["Cash", "BRI", "BSI", "DANA", "GoPay"]


def build_prompt(user_input: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    return f"""
Kamu adalah parser transaksi keuangan pribadi. 
Tugasmu HANYA mengekstrak informasi transaksi dari input user dan mengembalikan JSON.
Jangan tambahkan penjelasan apapun — hanya JSON murni.

Hari ini: {today}

Kategori yang tersedia:
Pengeluaran: {", ".join([c for c in VALID_CATEGORIES if c not in ["Salary", "Freelance", "Investment Return", "Other Income"]])}
Pemasukan: Salary, Freelance, Investment Return, Other Income

Rekening yang tersedia: {", ".join(VALID_ACCOUNTS)}

Aturan:
1. type harus salah satu dari: "expense", "income", "transfer"
2. amount harus integer dalam Rupiah (bukan string)
3. category harus dari daftar kategori di atas, pilih yang paling relevan
4. account adalah rekening asal (null jika tidak disebutkan)
5. to_account hanya diisi jika type = "transfer" (null jika bukan transfer)
6. date format YYYY-MM-DD, interpretasi "kemarin", "tadi", "minggu lalu" dari hari ini
7. description singkat dan informatif, max 50 karakter
8. parsed_by selalu "gemini"

Input user: "{user_input}"

Balas HANYA dengan JSON ini (tanpa markdown, tanpa backtick):
{{
  "type": "expense|income|transfer",
  "amount": 0,
  "category": "nama kategori",
  "account": null,
  "to_account": null,
  "description": "deskripsi singkat",
  "date": "{today}",
  "parsed_by": "gemini"
}}
""".strip()


def parse_with_gemini(user_input: str) -> dict | None:
    """
    Fallback parser menggunakan Gemini API.
    Dipanggil hanya jika regex parser return None.

    Return dict jika berhasil, None jika gagal.
    """
    try:
        prompt = build_prompt(user_input)
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Bersihkan jika Gemini tetap wrap dengan backtick
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        parsed = json.loads(raw_text)

        # Validasi field wajib ada
        required_fields = ["type", "amount", "category", "date"]
        for field in required_fields:
            if field not in parsed:
                return None

        # Validasi type
        if parsed["type"] not in ["expense", "income", "transfer"]:
            return None

        # Validasi amount adalah angka
        parsed["amount"] = int(parsed["amount"])
        if parsed["amount"] <= 0:
            return None

        # Pastikan parsed_by selalu gemini
        parsed["parsed_by"] = "gemini"

        return parsed

    except json.JSONDecodeError:
        # Gemini return bukan JSON valid
        return None
    except Exception:
        # Error apapun (network, rate limit, dll)
        return None


def parse_with_pending_fallback(user_input: str) -> dict:
    """
    Wrapper dengan fallback ke pending jika Gemini gagal.
    Selalu return dict — tidak pernah return None.

    Return format tambahan jika gagal:
    {
        "type": "pending",
        "raw_input": str,
        "parsed_by": "failed"
    }
    """
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
            "description": None,
            "date": datetime.now().strftime("%Y-%m-%d"),
        }

    return result