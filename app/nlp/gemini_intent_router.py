"""Gemini-based intent router for natural finance questions and read-only command fallback."""



# Import json for this module's local operations.
import json
# Import re for this module's local operations.
import re
# Import os for this module's local operations.
import os

# Import app.config so this module can use its helpers.
from app.config import GEMINI_API_KEY
# Import app.nlp.gemini_langchain_client so this module can use its helpers.
from app.nlp.gemini_langchain_client import generate_text_with_gemini


GEMINI_INTENT_MODEL = os.getenv("GEMINI_INTENT_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))


# Open a multi-line structure for the values below.
ALLOWED_INTENTS = {
    "saldo",
    "harian",
    "mingguan",
    "bulanan",
    "budget",
    "budget_history",
    "hutang",
    "last",
    "cari",
    "delete_txn",
    "edit_txn",
    "help",
    "unknown",
# Close the structure that was opened above.
}


# Open a multi-line structure for the values below.
DESTRUCTIVE_INTENTS = {
    "delete_txn",
    "edit_txn",
# Close the structure that was opened above.
}


# Open a multi-line structure for the values below.
INTENT_KEYWORDS = [
    "lihat",
    "tampilkan",
    "cek",
    "check",
    "show",
    "cari",
    "search",
    "hapus",
    "delete",
    "detele",
    "edit",
    "ubah",
    "ganti",
    "saldo",
    "budget",
    "hutang",
    "utang",
    "transaksi",
    "riwayat",
    "histori",
    "history",
    "harian",
    "mingguan",
    "bulanan",
    "bulan",
    "minggu",
    "hari",
# Close the structure that was opened above.
]


# Define should try gemini intent router for callers in this flow.
def should_try_gemini_intent_router(text: str) -> bool:
    """Decide whether the flow should try gemini intent router."""
    clean = str(text or "").strip().lower()

    # Handle the missing or empty clean case.
    if not clean:
        # Return False to the caller.
        return False

    if clean.startswith("/"):
        # Return False to the caller.
        return False

    # Prepare words for the next step.
    words = clean.split()

    # Handle the case where len(words) > 30.
    if len(words) > 30:
        # Return False to the caller.
        return False

    # Return any(keyword in clean for keyword in INTENT_KEYWORDS) to the caller.
    return any(keyword in clean for keyword in INTENT_KEYWORDS)


# Define extract json object for callers in this flow.
def extract_json_object(text: str) -> dict:
    """Extract the required part of input for json object."""
    # Handle the missing or empty text case.
    if not text:
        # Return {} to the caller.
        return {}

    # Prepare clean for the next step.
    clean = text.strip()

    clean = re.sub(r"^```json\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^```\s*", "", clean)
    clean = re.sub(r"\s*```$", "", clean)

    start = clean.find("{")
    end = clean.rfind("}")

    # Handle the case where start == -1 or end == -1 or end <= start.
    if start == -1 or end == -1 or end <= start:
        # Return {} to the caller.
        return {}

    # Prepare json text for the next step.
    json_text = clean[start:end + 1]

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Return json.loads(json_text) to the caller.
        return json.loads(json_text)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return {} to the caller.
        return {}


# Define normalize router result for callers in this flow.
def normalize_router_result(data: dict) -> dict:
    """Normalize input values for the normalize router result workflow in the NLP/parser layer.

    Args:
        data: Structured input data used by the current flow.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    intent = str(data.get("intent", "unknown") or "unknown").strip().lower()
    confidence = data.get("confidence", 0)
    args = data.get("args", {}) or {}
    explanation = str(data.get("explanation", "") or "").strip()

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare confidence for the next step.
        confidence = float(confidence)
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Prepare confidence for the next step.
        confidence = 0.0

    # Handle the case where intent not in ALLOWED_INTENTS.
    if intent not in ALLOWED_INTENTS:
        intent = "unknown"

    # Handle the missing or empty isinstance(args, dict) case.
    if not isinstance(args, dict):
        # Prepare args for the next step.
        args = {}

    # Return { to the caller.
    return {
        "intent": intent,
        "confidence": confidence,
        "args": args,
        "explanation": explanation,
        "is_destructive": intent in DESTRUCTIVE_INTENTS,
    # Close the structure that was opened above.
    }


# Define route intent with gemini for callers in this flow.
def route_intent_with_gemini(user_text: str) -> dict:
    """Coordinate the route intent with gemini logic in the NLP/parser layer.

    Args:
        user_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    prompt = f"""
Anda adalah intent router untuk personal finance Telegram bot.

Tugas Anda:
Ubah input user menjadi JSON valid saja.
Jangan menambahkan markdown.
Jangan menambahkan penjelasan di luar JSON.

Daftar intent yang valid:
1. saldo
2. harian
3. mingguan
4. bulanan
5. budget
6. budget_history
7. hutang
8. last
9. cari
10. delete_txn
11. edit_txn
12. help
13. unknown

Deskripsi intent:
- saldo: user ingin melihat saldo rekening.
- harian: user ingin laporan/ringkasan hari ini.
- mingguan: user ingin laporan/ringkasan minggu ini.
- bulanan: user ingin laporan/ringkasan bulan ini.
- budget: user ingin melihat budget, bisa bulan tertentu.
- budget_history: user ingin daftar histori bulan budget.
- hutang: user ingin melihat utang/piutang aktif.
- last: user ingin melihat transaksi terakhir, riwayat, histori transaksi, transaksi hari ini/minggu ini/bulan ini/bulan tertentu.
- cari: user ingin mencari transaksi berdasarkan keyword.
- delete_txn: user ingin menghapus transaksi.
- edit_txn: user ingin mengubah/mengedit transaksi.
- help: user ingin bantuan/panduan.
- unknown: maksud user tidak jelas atau bukan command bot.

Format JSON wajib:
{{
  "intent": "last",
  "confidence": 0.0,
  "args": {{
    "period": null,
    "month": null,
    "limit": null,
    "query": null,
    "ref": null,
    "updates": {{}}
  }},
  "explanation": "alasan singkat"
}}

Aturan args:
- period boleh: today, week, month, null.
- month format YYYY-MM jika ada, selain itu null.
- limit angka jika ada, selain itu null.
- query untuk pencarian /cari.
- ref untuk nomor transaksi atau transaction_id, contoh "2" atau "txn_...".
- updates untuk edit transaksi, contoh {{"amount": "15000"}}, {{"description": "Kopi susu"}}, {{"account": "BRI"}}.

Contoh:
Input: "lihat transaksi hari ini"
Output:
{{"intent":"last","confidence":0.91,"args":{{"period":"today","month":null,"limit":null,"query":null,"ref":null,"updates":{{}}}},"explanation":"User ingin melihat transaksi hari ini."}}

Input: "hapus transaksi nomor 2"
Output:
{{"intent":"delete_txn","confidence":0.9,"args":{{"period":null,"month":null,"limit":null,"query":null,"ref":"2","updates":{{}}}},"explanation":"User ingin menghapus transaksi nomor 2."}}

Input: "edit transaksi nomor 3 jadi 15000"
Output:
{{"intent":"edit_txn","confidence":0.86,"args":{{"period":null,"month":null,"limit":null,"query":null,"ref":"3","updates":{{"amount":"15000"}}}},"explanation":"User ingin mengubah nominal transaksi nomor 3."}}

Input: "cari kopi"
Output:
{{"intent":"cari","confidence":0.92,"args":{{"period":null,"month":null,"limit":null,"query":"kopi","ref":null,"updates":{{}}}},"explanation":"User ingin mencari transaksi kopi."}}

Input user:
{user_text}
"""

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Handle the missing or empty GEMINI_API_KEY case.
        if not GEMINI_API_KEY:
            raw_text = ""
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Open a multi-line structure for the values below.
            raw_text = generate_text_with_gemini(
                # Include this value in the surrounding collection or call.
                prompt,
                # Prepare model name for the next step.
                model_name=GEMINI_INTENT_MODEL,
                # Prepare temperature for the next step.
                temperature=0.0,
            # Close the structure that was opened above.
            )
        # Prepare data for the next step.
        data = extract_json_object(raw_text)
        # Return normalize_router_result(data) to the caller.
        return normalize_router_result(data)

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Return { to the caller.
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "args": {},
            "explanation": f"Gemini intent router error: {str(e)}",
            "is_destructive": False,
            "error": str(e),
        # Close the structure that was opened above.
        }
