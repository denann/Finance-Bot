"""Telegram output with contextual icon legends, shared by handlers and jobs."""

from __future__ import annotations

import html
import logging
import re
import unicodedata

from telegram.ext import ExtBot
from telegram.error import TelegramError
from telegram.helpers import escape_markdown


ICON_MEANINGS = {
    "📁": "Kategori", "🏦": "Rekening", "🏷": "Tipe atau label", "📝": "Deskripsi atau input",
    "📅": "Tanggal", "📆": "Periode", "🗓": "Jadwal", "🗒": "Catatan", "🔄": "Transfer atau pembaruan",
    "🧾": "Transaksi atau preview", "💰": "Nominal atau saldo", "💳": "Dampak saldo rekening",
    "💸": "Pembayaran atau arus kas", "💵": "Uang tunai", "🟢": "Piutang atau uang diterima",
    "🔴": "Utang", "👤": "Orang atau pihak pembayar", "👥": "Peserta", "🤝": "Split bill atau relasi utang",
    "🙋": "Saya membayar atau menalangi", "⚖": "Pembagian rata atau saldo bersih", "📊": "Ringkasan atau pembagian",
    "📈": "Tren", "✅": "Setuju, selesai, atau sudah dibayar", "⏳": "Menunggu atau belum dibayar",
    "✏": "Edit", "✍": "Tulis ulang", "🚫": "Batal", "❌": "Batal atau gagal", "⛔": "Tidak diizinkan",
    "🗑": "Hapus", "⏭": "Lewati", "➡": "Lanjut atau rekening tujuan", "↩": "Kembali atau pengembalian",
    "◀": "Sebelumnya", "▶": "Berikutnya", "🔁": "Berulang atau kompensasi", "🔍": "Cari atau periksa",
    "📄": "Halaman atau dokumen", "📋": "Daftar atau salin", "📌": "Informasi utama", "📖": "Panduan",
    "📚": "Referensi", "💡": "Petunjuk", "⚠": "Peringatan", "ℹ": "Informasi", "❓": "Belum diketahui",
    "🤔": "Perlu klarifikasi", "🤖": "Bantuan AI", "🧠": "Analisis AI", "🎯": "Target atau budget",
    "🔔": "Pengingat", "🔕": "Pengingat nonaktif", "⏰": "Waktu pengingat", "🕒": "Waktu", "🕘": "Waktu",
    "📤": "Ekspor atau kirim", "📥": "Input atau diterima", "📦": "Lainnya", "📭": "Belum ada data",
    "🔐": "Keamanan dan privasi", "🔗": "Tautan atau data terkait", "🔖": "Penanda", "🔢": "Nomor atau jumlah",
    "💎": "Aset", "💼": "Pekerjaan atau gaji", "🏠": "Tempat tinggal", "🏥": "Kesehatan", "🚗": "Transportasi",
    "🍢": "Jajan", "🍽": "Makanan dan minuman", "🎮": "Hiburan", "🎓": "Pendidikan", "🎁": "Bonus",
    "🛍": "Belanja", "🤲": "Donasi", "🖼": "Gambar", "📱": "Aplikasi atau ponsel", "👋": "Salam",
    "👍": "Persetujuan", "🏁": "Selesai", "🚀": "Mulai", "🟠": "Perhatian", "🟡": "Perhatian",
    "⚪": "Netral atau kosong", "🗂": "Kelompok data", "📏": "Ukuran", "🧮": "Perhitungan",
    "🧪": "Pemeriksaan", "🧭": "Arahan", "🧩": "Bagian fitur", "🧹": "Bersihkan", "▲": "Naik", "▼": "Turun",
    "∅": "Tidak ada arus kas",
}
ICON_RE = re.compile(r"[\U0001f300-\U0001faff\u2300-\u23ff\u2600-\u27bf\u2b00-\u2bffℹ↩➡◀▶▲▼∅]\ufe0f?")


def icon_legend(text: str, reply_markup=None) -> str:
    """Explain icons present in text and buttons; never resolve or alter finance data."""
    source = text
    markup = reply_markup.to_dict() if hasattr(reply_markup, "to_dict") else reply_markup
    if isinstance(markup, dict):
        source += "\n" + "\n".join(str(button.get("text", "")) for row in markup.get("inline_keyboard", []) for button in row)
    entries = []
    # Ignore formatting, date hyphens, and ordinary list bullets.
    sign_source = re.sub(r"<[^>]+>", "", source)
    sign_source = re.sub(r"\\([+.*_-])", r"\1", sign_source)
    for sign, meaning in (("+", "Pemasukan atau saldo bertambah"), ("-", "Pengeluaran atau saldo berkurang")):
        if re.search(rf"(?mi)^\s*(?:\d+\.\s*)?[*_]*{re.escape(sign)}\s+(?:[*_]|(?:Pemasukan|Pengeluaran|Income|Expense)\b|\d{{4}}-\d{{2}}-\d{{2}})|{re.escape(sign)}[*_]*Rp", sign_source):
            entries.append(f"{sign} = {meaning}")
    seen = set()
    for match in ICON_RE.finditer(source):
        icon = match.group()
        key = icon.rstrip("\ufe0f")
        if key in seen:
            continue
        seen.add(key)
        meaning = ICON_MEANINGS.get(key)
        if not meaning:
            # Custom category symbols have no financial meaning we can infer.
            meaning = "Simbol " + unicodedata.name(key[0], "khusus").lower()
        entries.append(f"{icon} = {meaning}")
    return "Legenda ikon:\n" + " • ".join(entries) if entries else ""


def _wire_length(text: str) -> int:
    """Use UTF-16 units as a conservative Telegram length bound."""
    return len(text.encode("utf-16-le")) // 2


class FinanceBot(ExtBot):
    """Append legends at the common Telegram transport boundary.

    Covers text sends/edits and media captions without changing callback data,
    entity offsets, or returned message IDs. Oversized legends are sent after
    the original message, never by truncating finance content.
    """

    async def _do_post(self, endpoint: str, data: dict, **kwargs):
        if not (endpoint.startswith("send") or endpoint in {"editMessageText", "editMessageCaption"}):
            return await super()._do_post(endpoint, data, **kwargs)
        payload = dict(data)
        field = "text" if endpoint in {"sendMessage", "editMessageText"} else "caption"
        source = str(payload.get(field) or "")
        if endpoint == "sendMediaGroup":
            source = "\n".join(str(getattr(media, "caption", "") or (media.get("caption", "") if isinstance(media, dict) else "")) for media in payload.get("media", []))
        legend = icon_legend(source, payload.get("reply_markup"))
        if not legend:
            return await super()._do_post(endpoint, payload, **kwargs)
        mode = payload.get("parse_mode")
        suffix = html.escape(legend) if mode == "HTML" else escape_markdown(legend, version=2) if mode == "MarkdownV2" else legend
        limit = 4096 if field == "text" else 1024
        combined = source + "\n\n" + suffix
        if endpoint != "sendMediaGroup" and _wire_length(combined) <= limit:
            payload[field] = combined
            return await super()._do_post(endpoint, payload, **kwargs)
        result = await super()._do_post(endpoint, payload, **kwargs)
        chat_id = payload.get("chat_id")
        if chat_id is not None:
            # Transport-level follow-ups must not call our decorator recursively.
            for start in range(0, len(legend), 1800):
                followup = {key: payload[key] for key in ("chat_id", "message_thread_id", "business_connection_id", "disable_notification", "protect_content") if key in payload}
                followup["text"] = legend[start:start + 1800]
                try:
                    await super()._do_post("sendMessage", followup, **kwargs)
                except TelegramError:
                    # The original preview already exists: preserve its returned ID.
                    logging.getLogger(__name__).warning("Telegram legend follow-up delivery failed")
        return result
