"""Privacy helpers for user-facing notices and Gemini context minimization."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


SENSITIVE_KEYWORDS = (
    "api_key",
    "access_token",
    "refresh_token",
    "bot_token",
    "private_key",
    "service_account",
    "credential",
    "credentials",
    "secret",
    "password",
    "client_email",
    "env",
    "telegram_bot_token",
    "gemini_api_key",
    "google_service_account_json",
)

SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", re.IGNORECASE),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}\b"),
    re.compile(r"\b\d{6,}:[A-Za-z0-9_\-]{20,}\b"),
)


def build_privacy_notice_text() -> str:
    """Build the read-only `/privacy` explanation shown to Telegram users.

    Args:
        None.

    Returns:
        Markdown text that explains data processing, storage, Telegram I/O,
        Gemini usage boundaries, export sensitivity, and credential safety.

    Side effects:
        None. This helper only returns static user-facing text and does not read
        Google Sheets, environment variables, credentials, or Telegram state.

    Flow constraints:
        Keep this command read-only. Do not include a Batal button because the
        output does not open a wizard, preview, or confirmation flow.
    """
    return (
        "🔐 *Data Privacy Finance Bot*\n\n"
        "*Data yang diproses*\n"
        "Bot memproses input chat, foto transaksi/struk, transaksi, saldo rekening, kategori, budget, utang/piutang, pending expense, recurring, aset, dan ringkasan laporan.\n\n"
        "*Penyimpanan data*\n"
        "Data finance utama disimpan di Google Sheets yang terhubung ke bot. Bot tidak menambah storage privacy baru.\n\n"
        "*Telegram*\n"
        "Telegram menjadi jalur input dan output. Pesan, preview, file export, dan hasil laporan dikirim lewat chat Telegram.\n\n"
        "*Gemini*\n"
        "Gemini hanya dipakai untuk fitur AI, image parsing, parser draft, dan generate aliases kategori. Konteks yang dikirim dibatasi ke data relevan untuk fitur tersebut, bukan credential.\n\n"
        "*Export data*\n"
        "File export berisi data finance pribadi. Simpan dan bagikan dengan hati-hati.\n\n"
        "*Yang harus dijaga user*\n"
        "Jaga token Telegram, Gemini API key, file service account, `.env`, dan akses Google Spreadsheet. Jangan kirim credential ke chat, screenshot, atau pihak lain."
    )


def is_sensitive_key(key: str) -> bool:
    """Check whether a context key should be excluded from Gemini prompts.

    Args:
        key: Dictionary key from a nested AI context payload. Expected shape is
            any string-like value.

    Returns:
        `True` when the key looks like a credential, token, secret, service
        account field, or environment value; otherwise `False`.

    Side effects:
        None.

    Flow constraints:
        Do not treat normal finance fields such as `account`, `to_account`, or
        `keyword_used` as credentials. This check intentionally targets explicit
        credential-like names only.
    """
    clean = str(key or "").strip().lower()
    return any(keyword in clean for keyword in SENSITIVE_KEYWORDS)


def redact_sensitive_text(value: str) -> str:
    """Redact credential-like substrings from text before AI prompting.

    Args:
        value: Text from user-provided caption, AI question, chat history, or
            serialized context fields.

    Returns:
        Text with known token/private-key patterns replaced by `[REDACTED]`.

    Side effects:
        None.

    Flow constraints:
        Keep normal finance descriptions intact. Only redact patterns that look
        like API keys, bot tokens, or private keys.
    """
    clean = str(value or "")
    for pattern in SENSITIVE_VALUE_PATTERNS:
        # Redact only credential-shaped values, not ordinary transaction text.
        clean = pattern.sub("[REDACTED]", clean)
    return clean


def sanitize_ai_context(data: Any) -> Any:
    """Remove credential-like keys and redact secrets before Gemini prompts.

    Args:
        data: Nested dict/list/scalar payload prepared for Gemini. Expected
            inputs include finance insight context, ask history, and related
            parser context.

    Returns:
        A sanitized deep copy with sensitive keys removed and sensitive-looking
        string values redacted. Non-container scalar values are returned in a
        safe equivalent form.

    Side effects:
        None. The original `data` object is not mutated.

    Flow constraints:
        This helper must not change Google Sheets schema or business logic. It
        is only a last-mile guard before sending context to Gemini.
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Drop credential-like fields entirely before prompt serialization.
            if is_sensitive_key(str(key)):
                continue
            sanitized[key] = sanitize_ai_context(value)
        return sanitized

    if isinstance(data, list):
        return [sanitize_ai_context(item) for item in data]

    if isinstance(data, str):
        return redact_sensitive_text(data)

    return deepcopy(data)
