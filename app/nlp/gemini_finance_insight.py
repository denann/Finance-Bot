"""Gemini-based finance insight generator for ask, audit, coach, and monthly insight modes."""


# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import json for this module's local operations.
import json
# Import os for this module's local operations.
import os

# Import app.config so this module can use its helpers.
from app.config import GEMINI_API_KEY
# Import app.nlp.gemini_langchain_client so this module can use its helpers.
from app.nlp.gemini_langchain_client import generate_text_with_gemini
# Import privacy sanitizer so Gemini never receives credential-like context fields.
from app.services.privacy_service import sanitize_ai_context
# Import app.services.finance_insight_service so this module can use its helpers.
from app.services.finance_insight_service import deterministic_audit_text, deterministic_monthly_text


GEMINI_INSIGHT_MODEL = os.getenv("GEMINI_INSIGHT_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

# Open a multi-line structure for the values below.
MODE_LABELS = {
    "monthly_auto": "Insight otomatis setelah laporan bulanan",
    "monthly_insight": "Monthly narrative report",
    "ask": "Tanya jawab finansial natural",
    "audit": "Deteksi anomali dan data quality checker",
    "budget_assistant": "Budget assistant",
    "coach": "Financial coach ringan",
# Close the structure that was opened above.
}


# Define json dumps for callers in this flow.
def _json_dumps(data: dict) -> str:
    """Coordinate the json dumps logic in the NLP/parser layer.

    Args:
        data: Structured input data used by the current flow.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    # Return json.dumps(data, ensure_ascii=False, indent=2, default=str) to the caller.
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def build_finance_insight_prompt(mode: str, context: dict, question: str = "") -> str:
    """Build the Gemini prompt for finance insight features.

    Args:
        mode: Insight mode such as `ask`, `audit`, `coach`,
            `monthly_insight`, or `monthly_auto`.
        context: Structured finance context built from Google Sheets summaries,
            compact transactions, budget status, debt summary, and available
            commands. The context must not contain credentials, and this helper
            applies a final sanitizer before JSON serialization.
        question: Optional user question for `/ask`, `/coach`, or natural AI
            finance questions.

    Returns:
        A complete Indonesian prompt string for Gemini.

    Side effects:
        None. This helper does not call Gemini and does not read or write
        Google Sheets.

    Flow constraints:
        Only send relevant finance context. Remove credential-like keys and
        redact token/private-key patterns before embedding context in the
        prompt.
    """
    # Prepare mode label for the next step.
    mode_label = MODE_LABELS.get(mode, mode)
    sanitized_context = sanitize_ai_context(context or {})
    question_line = sanitize_ai_context(question or sanitized_context.get("question") or "-")

    if mode == "monthly_auto":
        length_rule = "Jawab sangat ringkas: maksimal 5 bullet. Fokus ke driver utama, budget risk, dan 1 saran."
    elif mode == "audit":
        length_rule = "Jawab ringkas, natural, dan actionable. Jika tidak ada issues/anomalies, jawab tenang seperti: ✅ Tidak ada anomali bulan ini. Data transaksi bulan ini terlihat cukup aman."
    elif mode == "coach":
        length_rule = "Jawab sebagai financial coach ringan: realistis, berbasis angka, tanpa menghakimi. Beri 3-5 aksi konkret."
    # Handle the fallback path after earlier conditions are skipped.
    else:
        length_rule = "Jawab natural seperti financial assistant pribadi: mulai dari temuan utama, sebut angka paling penting, jelaskan kemungkinan penyebab, lalu beri 2-3 saran praktis. Tetap ringkas."

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
18. Gunakan bahasa Indonesia yang natural, tidak terlalu kaku, dan jangan terlalu template.
19. Untuk pertanyaan seperti "bulan ini boros di mana?", fokus ke kategori penyumbang terbesar, transaksi yang perlu dicek, dan saran kecil yang bisa langsung dilakukan.
20. Kalau kategori `Other Expense` cukup besar atau muncul di data_quality_issues, jelaskan bahwa insight akan lebih rapi kalau kategorinya diperbaiki.
21. Untuk pertanyaan proyeksi seperti "sampai akhir bulan X kira-kira pengeluaran berapa?", jangan jawab kaku "belum bisa" jika masih ada data berjalan. Beri estimasi kasar berbasis run rate data yang tersedia, sebutkan asumsi dan keterbatasannya. Jika data hanya sedikit, gunakan bahasa seperti "estimasi ini masih kasar" dan jangan tampilkan seolah-olah pasti.
22. Untuk proyeksi lintas bulan, jelaskan basis hitung secara sederhana: periode data yang tersedia, rata-rata harian atau rata-rata bulanan jika ada, lalu estimasi sampai target waktu. Jika konteks tidak menyediakan transaksi lintas bulan, jangan mengarang bulan kosong; pakai data tersedia sebagai baseline sementara.
23. Kalau data quality issues ada tetapi bukan inti pertanyaan, taruh sebagai catatan singkat di akhir, bukan mendominasi jawaban.
24. Jawaban `/ask` harus terasa menjawab pertanyaan user dulu. Hindari template panjang kalau user hanya minta angka perkiraan.
25. Jangan meminta, menampilkan, menebak, atau menyimpan credential seperti token Telegram, Gemini API key, service account JSON, private key, `.env`, atau akses spreadsheet. Jika konteks berisi placeholder `[REDACTED]`, abaikan sebagai credential yang sengaja disensor.
26. Format output wajib rapi untuk Telegram:
    - Jangan pakai `**bold**`. Jika butuh penekanan, pakai `*bold*`.
    - Jangan pakai nested bullet yang terlalu dalam. Maksimal 2 level.
    - Gunakan bullet `•`, bukan `*   ` atau `-`.
    - Jangan tampilkan nama field JSON mentah seperti `total_payable`, `data_quality_issues`, `top_expenses`, atau snake_case lain. Ubah menjadi bahasa manusia.
    - Buat section pendek seperti `*Temuan utama*`, `*Yang perlu dicek*`, dan `*Saran praktis*` jika relevan.
    - Jangan terlalu panjang. Prioritaskan 3-5 poin yang paling penting.

Konteks JSON:
{_json_dumps(sanitized_context)}
""".strip()


def generate_finance_insight(mode: str, context: dict, question: str = "") -> str:
    """Coordinate the generate finance insight logic in the NLP/parser layer.

    Args:
        mode: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        context: Telegram callback context containing args, bot data, user data, and job data.
        question: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Prefer explicit user intent over loose keyword matching and return ambiguity for caller clarification when needed.
    """
    if mode == "audit" and not context.get("data_quality_issues") and not context.get("anomalies"):
        # Return deterministic_audit_text(context) to the caller.
        return deterministic_audit_text(context)

    # Handle the missing or empty GEMINI_API_KEY case.
    if not GEMINI_API_KEY:
        if mode == "audit":
            # Return deterministic_audit_text(context) to the caller.
            return deterministic_audit_text(context)
        if "monthly" in mode or mode in {"coach", "budget_assistant", "ask"}:
            base = context.get("monthly_context") if "monthly_context" in context else context
            # Return deterministic_monthly_text(base) to the caller.
            return deterministic_monthly_text(base)
        return "GEMINI_API_KEY belum tersedia, jadi insight AI belum bisa dibuat."

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare prompt for the next step.
        prompt = build_finance_insight_prompt(mode, context, question=question)
        # Open a multi-line structure for the values below.
        text = generate_text_with_gemini(
            # Include this value in the surrounding collection or call.
            prompt,
            # Prepare model name for the next step.
            model_name=GEMINI_INSIGHT_MODEL,
            # Prepare temperature for the next step.
            temperature=0.25,
        # Close the structure that was opened above.
        ).strip()
        # Handle the case where text.
        if text:
            # Return text to the caller.
            return text
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        fallback_prefix = f"⚠️ Insight Gemini gagal dibuat: {str(e)}\n\nFallback lokal:\n"
        if mode == "audit":
            # Return fallback_prefix + deterministic_audit_text(context) to the caller.
            return fallback_prefix + deterministic_audit_text(context)
        base = context.get("monthly_context") if "monthly_context" in context else context
        # Return fallback_prefix + deterministic_monthly_text(base) to the caller.
        return fallback_prefix + deterministic_monthly_text(base)

    base = context.get("monthly_context") if "monthly_context" in context else context
    # Return deterministic_monthly_text(base) to the caller.
    return deterministic_monthly_text(base)
