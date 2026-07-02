"""Gemini-based finance insight generator for ask, audit, coach, and monthly insight modes."""


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
    """Helper for json dumps in the NLP and parser layer."""
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def build_finance_insight_prompt(mode: str, context: dict, question: str = "") -> str:
    """Build the data structure or message text for finance insight prompt."""
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
4. Semua nominal tulis dalam Rupiah. Jika ada field `*_display` atau `amount_display`, SALIN field display itu persis untuk output user. Jangan format ulang dari angka float jika field display tersedia.
5. Jangan menyuruh user melakukan hal ekstrem; beri saran praktis.
6. Jangan gunakan markdown table karena Telegram kurang nyaman.
7. Hindari karakter markdown kompleks seperti underscore berlebihan.
8. {length_rule}
9. Jika `chat_history` tersedia, gunakan hanya untuk memahami konteks pertanyaan lanjutan seperti "itu", "yang tadi", atau "yang food". Jangan mengambil nominal/fakta utama dari chat_history jika tidak didukung konteks transaksi/ringkasan.
10. Jika menyarankan command, hanya boleh pakai command yang ada di `available_commands`.
11. Jangan pernah menyebut command yang tidak ada di konteks JSON.
12. Jangan menyebut nama tool palsu seperti `list_transactions`, `edit_transaction`, `update_transaction`, atau `categorize_transaction`. Untuk list transaksi pakai `/transaksi`; untuk koreksi pakai `/edit_txn`; untuk hapus pakai `/delete_txn`.
13. Semua `amount` untuk transaksi expense, `summary.total_expense`, `expense_by_category`, `budget_status.actual`, `top_expenses`, dan `anomalies` sudah memakai NET expense setelah piutang split bill. Jangan pakai/estimasi gross kecuali field gross eksplisit tersedia. Untuk nominal audit, prioritaskan `amount_display`, `threshold_display`, dan `*_display` agar tidak salah skala.
14. Bedakan `top_expenses` dan `anomalies`: transaksi besar/top expense belum tentu anomali.
15. Hanya sebut "anomali" jika item tersebut muncul di field `anomalies`.
16. Hanya sebut "masalah data quality" jika item tersebut muncul di field `data_quality_issues`.
17. Jangan membuat kalimat pembuka generik seperti "Halo! Saya analis..." kalau tidak perlu.

Konteks JSON:
{_json_dumps(context)}
""".strip()


def generate_finance_insight(mode: str, context: dict, question: str = "") -> str:
    """Helper for generate finance insight in the NLP and parser layer."""
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
            temperature=0.0,
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
