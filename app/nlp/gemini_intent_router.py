"""Gemini-based intent router for natural read-only commands and AI insight requests."""


import json
import re
import os

from app.config import GEMINI_API_KEY
from app.nlp.gemini_langchain_client import generate_text_with_gemini


GEMINI_INTENT_MODEL = os.getenv("GEMINI_INTENT_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))


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
}


DESTRUCTIVE_INTENTS = {
    "delete_txn",
    "edit_txn",
}


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
]


def should_try_gemini_intent_router(text: str) -> bool:
    """Check a boolean condition for should try gemini intent router."""
    clean = str(text or "").strip().lower()

    if not clean:
        return False

    if clean.startswith("/"):
        return False

    words = clean.split()

    if len(words) > 30:
        return False

    return any(keyword in clean for keyword in INTENT_KEYWORDS)


def extract_json_object(text: str) -> dict:
    """Extract the important part of the input for json object."""
    if not text:
        return {}

    clean = text.strip()

    clean = re.sub(r"^```json\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^```\s*", "", clean)
    clean = re.sub(r"\s*```$", "", clean)

    start = clean.find("{")
    end = clean.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return {}

    json_text = clean[start:end + 1]

    try:
        return json.loads(json_text)
    except Exception:
        return {}


def normalize_router_result(data: dict) -> dict:
    """Clean and standardize normalize router result."""
    intent = str(data.get("intent", "unknown") or "unknown").strip().lower()
    confidence = data.get("confidence", 0)
    args = data.get("args", {}) or {}
    explanation = str(data.get("explanation", "") or "").strip()

    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0

    if intent not in ALLOWED_INTENTS:
        intent = "unknown"

    if not isinstance(args, dict):
        args = {}

    return {
        "intent": intent,
        "confidence": confidence,
        "args": args,
        "explanation": explanation,
        "is_destructive": intent in DESTRUCTIVE_INTENTS,
    }


def route_intent_with_gemini(user_text: str) -> dict:
    """Helper for route intent with gemini in the parser and NLP layer."""
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

    try:
        if not GEMINI_API_KEY:
            raw_text = ""
        else:
            raw_text = generate_text_with_gemini(
                prompt,
                model_name=GEMINI_INTENT_MODEL,
                temperature=0.0,
            )
        data = extract_json_object(raw_text)
        return normalize_router_result(data)

    except Exception as e:
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "args": {},
            "explanation": f"Gemini intent router error: {str(e)}",
            "is_destructive": False,
            "error": str(e),
        }