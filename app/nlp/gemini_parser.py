"""Gemini-assisted transaction parser used as a fallback when local parsing is not confident enough."""



# Import json for this module's local operations.
import json
# Import os for this module's local operations.
import os
# Import datetime so this module can use its helpers.
from datetime import datetime
# Import app.config so this module can use its helpers.
from app.config import GEMINI_API_KEY
# Import app.nlp.gemini_langchain_client so this module can use its helpers.
from app.nlp.gemini_langchain_client import generate_text_with_gemini
# Import app.services.resolver_service so this module can use its helpers.
from app.services.resolver_service import (
    # Include this value in the surrounding collection or call.
    ensure_category_for_transaction,
    # Include this value in the surrounding collection or call.
    get_account_names_from_sheet,
    # Include this value in the surrounding collection or call.
    get_category_names_from_sheet,
    # Include this value in the surrounding collection or call.
    resolve_account_for_parser,
# Close the structure that was opened above.
)


GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))


# Open a multi-line structure for the values below.
VALID_CATEGORIES = [
    "Food & Beverage", "Transport", "Bills & Utilities", "Shopping",
    "Health", "Entertainment", "Education", "Personal Care",
    "Kos & Utilities", "Zakat & Sedekah", "Investasi", "Other Expense",
    "Salary", "Freelance", "Investment Return", "Other Income",
# Close the structure that was opened above.
]

VALID_ACCOUNTS = ["Cash", "BRI", "BSI", "DANA", "GoPay"]

VALID_SPENDING_TYPES = ["Bulanan", "Harian", "Darurat", "Keinginan"]


# Define get valid categories for callers in this flow.
def get_valid_categories(transaction_type: str | None = None) -> list[str]:
    """Get valid categories from sheet with static fallback."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare names for the next step.
        names = get_category_names_from_sheet(transaction_type)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Prepare names for the next step.
        names = []
    # Return names or list(VALID_CATEGORIES) to the caller.
    return names or list(VALID_CATEGORIES)


# Define get valid accounts for callers in this flow.
def get_valid_accounts() -> list[str]:
    """Get valid accounts from sheet with static fallback."""
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare names for the next step.
        names = get_account_names_from_sheet()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Prepare names for the next step.
        names = []
    # Return names or list(VALID_ACCOUNTS) to the caller.
    return names or list(VALID_ACCOUNTS)


# Define build prompt for callers in this flow.
def build_prompt(user_input: str) -> str:
    """Build the data structure or message text for prompt."""
    today = datetime.now().strftime("%Y-%m-%d")

    expense_categories = get_valid_categories("expense")
    income_categories = get_valid_categories("income")
    # Prepare valid accounts for the next step.
    valid_accounts = get_valid_accounts()

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
{", ".join(income_categories)}

Rekening valid:
{", ".join(valid_accounts)}

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
5. category sebaiknya memakai kategori valid di atas. Jika benar-benar tidak cocok, boleh buat kategori baru yang singkat dan tidak redundan.
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


# Define clean gemini json for callers in this flow.
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
    # Prepare raw text for the next step.
    raw_text = raw_text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            # Prepare raw text for the next step.
            raw_text = raw_text[4:]
        # Prepare raw text for the next step.
        raw_text = raw_text.strip()

    # Return raw_text to the caller.
    return raw_text


# Define parse with gemini for callers in this flow.
def parse_with_gemini(user_input: str) -> dict | None:
    """Parse caller input for the parse with gemini workflow in the NLP/parser layer.

    Args:
        user_input: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare prompt for the next step.
        prompt = build_prompt(user_input)
        # Handle the missing or empty GEMINI_API_KEY case.
        if not GEMINI_API_KEY:
            # Return None to the caller.
            return None

        # Open a multi-line structure for the values below.
        response_text = generate_text_with_gemini(
            # Include this value in the surrounding collection or call.
            prompt,
            # Prepare model name for the next step.
            model_name=GEMINI_TEXT_MODEL,
            # Prepare temperature for the next step.
            temperature=0.0,
        # Close the structure that was opened above.
        )

        # Handle the missing or empty response_text case.
        if not response_text:
            # Return None to the caller.
            return None

        # Prepare raw text for the next step.
        raw_text = clean_gemini_json(response_text)
        # Prepare parsed for the next step.
        parsed = json.loads(raw_text)

        required_fields = ["type", "amount", "category", "date"]
        # Process each field in the current collection.
        for field in required_fields:
            # Handle the case where field not in parsed.
            if field not in parsed:
                # Return None to the caller.
                return None

        if parsed["type"] not in ["expense", "income", "transfer"]:
            # Return None to the caller.
            return None

        parsed["amount"] = int(parsed["amount"])
        if parsed["amount"] <= 0:
            # Return None to the caller.
            return None

        if parsed["type"] == "transfer":
            parsed["category"] = None
        # Handle the fallback path after earlier conditions are skipped.
        else:
            parsed["category"] = ensure_category_for_transaction(
                parsed.get("category"),
                parsed.get("type"),
            # Close the structure that was opened above.
            )

        parsed["account"] = resolve_account_for_parser(parsed.get("account"))
        parsed["to_account"] = resolve_account_for_parser(parsed.get("to_account"))

        if parsed["type"] != "expense":
            parsed["tipe_pengeluaran"] = ""
        elif parsed.get("tipe_pengeluaran") not in VALID_SPENDING_TYPES:
            parsed["tipe_pengeluaran"] = "Harian"

        parsed["subject"] = parsed.get("subject") or ""
        parsed["description"] = parsed.get("description") or "Transaksi"
        parsed["catatan"] = parsed.get("catatan") or ""
        parsed["parsed_by"] = "gemini"

        # Return parsed to the caller.
        return parsed

    # Handle an expected failure from the guarded operation above.
    except json.JSONDecodeError:
        # Return None to the caller.
        return None
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return None to the caller.
        return None


# Define parse with pending fallback for callers in this flow.
def parse_with_pending_fallback(user_input: str) -> dict:
    """Parse caller input for the parse with pending fallback workflow in the NLP/parser layer.

    Args:
        user_input: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Prepare result for the next step.
    result = parse_with_gemini(user_input)

    # Handle the case where result is None.
    if result is None:
        # Return { to the caller.
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
        # Close the structure that was opened above.
        }

    # Keep this section separated from the surrounding flow.