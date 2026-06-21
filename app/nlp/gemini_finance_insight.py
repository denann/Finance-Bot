from __future__ import annotations

import json
import os

from app.config import GEMINI_API_KEY
from app.nlp.gemini_langchain_client import generate_text_with_gemini
from app.services.finance_insight_service import deterministic_audit_text, deterministic_monthly_text


GEMINI_INSIGHT_MODEL = os.getenv("GEMINI_INSIGHT_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

MODE_LABELS = {
    "monthly_auto": "Insight otomatis setelah laporan bulanan",
    "monthly_insight": "Monthly narrative report",
    "ask": "Tanya jawab finansial natural",
    "audit": "Deteksi anomali dan data quality checker",
    "budget_assistant": "Budget assistant",
    "coach": "Financial coach ringan",
}


def _json_dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def build_finance_insight_prompt(mode: str, context: dict, question: str = "") -> str:
    mode_label = MODE_LABELS.get(mode, mode)
    question_line = question or context.get("question") or "-"

    if mode == "monthly_auto":
        length_rule = "Jawab sangat ringkas: maksimal 5 bullet. Fokus ke driver utama, budget risk, dan 1 saran."
    elif mode == "audit":
        length_rule = "Jawab ringkas namun actionable. Kelompokkan masalah data, anomali, dan prioritas perbaikan."
    elif mode == "coach":
        length_rule = "Jawab sebagai financial coach ringan: realistis, berbasis angka, tanpa menghakimi. Beri 3-5 aksi konkret."
    else:
        length_rule = "Jawab jelas dan padat. Boleh pakai bullet, jangan terlalu panjang."

    return f"""
Kamu adalah analis personal finance berbahasa Indonesia.
Mode: {mode_label}
Pertanyaan user: {question_line}

Aturan wajib:
1. Gunakan HANYA angka/data dari konteks JSON.
2. Jangan mengarang transaksi, nominal, rekening, budget, atau tanggal yang tidak ada di konteks.
3. Jika data tidak cukup, bilang data belum cukup dan sarankan command yang relevan.
4. Semua nominal tulis dalam Rupiah, format kira-kira Rp1.000.000.
5. Jangan menyuruh user melakukan hal ekstrem; beri saran praktis.
6. Jangan gunakan markdown table karena Telegram kurang nyaman.
7. Hindari karakter markdown kompleks seperti underscore berlebihan.
8. {length_rule}
9. Jika `chat_history` tersedia, gunakan hanya untuk memahami konteks pertanyaan lanjutan seperti "itu", "yang tadi", atau "yang food". Jangan mengambil nominal/fakta utama dari chat_history jika tidak didukung konteks transaksi/ringkasan.

Konteks JSON:
{_json_dumps(context)}
""".strip()


def generate_finance_insight(mode: str, context: dict, question: str = "") -> str:
    """Generate insight text. Falls back to deterministic text if Gemini fails."""
    if not GEMINI_API_KEY:
        if mode == "audit":
            return deterministic_audit_text(context)
        if "monthly" in mode or mode in {"coach", "budget_assistant", "ask"}:
            base = context.get("monthly_context") if "monthly_context" in context else context
            return deterministic_monthly_text(base)
        return "GEMINI_API_KEY belum tersedia, jadi insight AI belum bisa dibuat."

    try:
        prompt = build_finance_insight_prompt(mode, context, question=question)
        text = generate_text_with_gemini(
            prompt,
            model_name=GEMINI_INSIGHT_MODEL,
            temperature=0.2,
        ).strip()
        if text:
            return text
    except Exception as e:
        fallback_prefix = f"⚠️ Insight Gemini gagal dibuat: {str(e)}\n\nFallback lokal:\n"
        if mode == "audit":
            return fallback_prefix + deterministic_audit_text(context)
        base = context.get("monthly_context") if "monthly_context" in context else context
        return fallback_prefix + deterministic_monthly_text(base)

    base = context.get("monthly_context") if "monthly_context" in context else context
    return deterministic_monthly_text(base)
