"""Lightweight setup checker for new users before running the bot."""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dependency may not be installed yet
    load_dotenv = None

if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")

RESULTS: list[tuple[str, str, str]] = []


def _add(status: str, title: str, detail: str = ""):
    """Helper for add in the utility script."""
    RESULTS.append((status, title, detail))
    icon = {"ok": "✅", "warn": "🟡", "fail": "❌", "skip": "⚪"}.get(status, "•")
    print(f"{icon} {title}" + (f" — {detail}" if detail else ""))


def ok(title: str, detail: str = ""):
    """Helper for ok in the utility script."""
    _add("ok", title, detail)


def warn(title: str, detail: str = ""):
    """Helper for warn in the utility script."""
    _add("warn", title, detail)


def fail(title: str, detail: str = ""):
    """Helper for fail in the utility script."""
    _add("fail", title, detail)


def skip(title: str, detail: str = ""):
    """Helper for skip in the utility script."""
    _add("skip", title, detail)


def mask(value: str) -> str:
    """Helper for mask in the utility script."""
    value = str(value or "")
    if len(value) <= 10:
        return "***" if value else ""
    return f"{value[:4]}...{value[-4:]}"


def env(name: str, default: str = "") -> str:
    """Helper for env in the utility script."""
    return str(os.getenv(name, default) or "").strip()


def check_env_file():
    """Helper for check env file in the utility script."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        ok(".env ditemukan", str(env_path.relative_to(PROJECT_ROOT)))
    else:
        fail(".env belum ditemukan", "copy .env.example menjadi .env lalu isi nilainya")


def check_runtime_env() -> str:
    """Helper for check runtime env in the utility script."""
    mode = env("BOT_MODE", "polling").lower()
    if mode not in {"polling", "webhook"}:
        fail("BOT_MODE tidak valid", "gunakan polling atau webhook")
        mode = "polling"
    else:
        ok("BOT_MODE", mode)

    required = [
        "TELEGRAM_BOT_TOKEN",
        "ALLOWED_USER_ID",
        "GOOGLE_SHEET_ID",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "GEMINI_API_KEY",
    ]

    for name in required:
        value = env(name)
        if value:
            ok(f"{name} terisi", mask(value))
        else:
            fail(f"{name} belum diisi")

    if env("GEMINI_MODEL"):
        ok("GEMINI_MODEL terisi", env("GEMINI_MODEL"))
    else:
        warn("GEMINI_MODEL belum diisi", "kode punya fallback, tapi README menyarankan isi eksplisit")

    try:
        int(env("ALLOWED_USER_ID", "0"))
        ok("ALLOWED_USER_ID valid", "angka")
    except ValueError:
        fail("ALLOWED_USER_ID tidak valid", "harus berupa angka Telegram user ID")

    if mode == "webhook":
        for name in ["WEBHOOK_URL", "TELEGRAM_WEBHOOK_SECRET", "APP_PORT"]:
            value = env(name)
            if value:
                ok(f"{name} terisi", mask(value))
            else:
                fail(f"{name} belum diisi", "wajib untuk webhook mode")

    return mode


def check_service_account_file():
    """Helper for check service account file in the utility script."""
    raw_path = env("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        fail("File service account tidak ditemukan", str(path))
        return False

    ok("File service account ditemukan", str(path.relative_to(PROJECT_ROOT)))

    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        fail("File service account tidak bisa dibaca sebagai JSON", f"{type(exc).__name__}: {exc}")
        return False

    client_email = data.get("client_email")
    if client_email:
        ok("client_email service account tersedia", client_email)
        print("   Pastikan Google Sheets sudah di-share ke email ini sebagai Editor.")
    else:
        fail("client_email tidak ditemukan di service account JSON")
        return False

    return True


def check_imports():
    """Helper for check imports in the utility script."""
    packages = [
        ("telegram", "python-telegram-bot"),
        ("gspread", "gspread"),
        ("dotenv", "python-dotenv"),
        ("apscheduler", "APScheduler"),
        ("langchain_google_genai", "langchain-google-genai"),
        ("fastapi", "FastAPI, hanya wajib untuk advanced webhook mode"),
    ]

    for module_name, label in packages:
        try:
            importlib.import_module(module_name)
            ok(f"Package import OK: {label}")
        except Exception as exc:
            fail(f"Package belum siap: {label}", f"{type(exc).__name__}: {exc}")


def check_google_sheets_schema(can_try: bool):
    """Helper for check google sheets schema in the utility script."""
    needed = ["GOOGLE_SHEET_ID", "GOOGLE_SERVICE_ACCOUNT_JSON"]
    if not can_try or any(not env(name) for name in needed):
        skip("Google Sheets schema check", "lengkapi GOOGLE_SHEET_ID dan service account dulu")
        return

    try:
        from app.sheets.client import ensure_spreadsheet_schema, get_spreadsheet

        spreadsheet = get_spreadsheet()
        ok("Google Sheets bisa diakses", spreadsheet.title)

        results = ensure_spreadsheet_schema()
        changed = [r for r in results if r.get("actions") != ["no_change"]]
        ok(
            "Google Sheets schema siap",
            f"{len(results)} tab dicek, {len(changed)} tab dibuat/dilengkapi",
        )
    except Exception as exc:
        fail("Google Sheets belum bisa diakses / schema belum siap", f"{type(exc).__name__}: {exc}")


def print_summary():
    """Helper for print summary in the utility script."""
    total = len(RESULTS)
    failed = sum(1 for status, _, _ in RESULTS if status == "fail")
    warned = sum(1 for status, _, _ in RESULTS if status == "warn")

    print("\n" + "=" * 72)
    print(f"Setup check selesai: {total} check, {failed} fail, {warned} warning")
    if failed:
        print("❌ Masih ada setup yang perlu diperbaiki sebelum bot dijalankan.")
    else:
        print("✅ Setup dasar sudah terlihat siap. Jalankan: python main.py")
    print("=" * 72)

    return failed


def main() -> int:
    """Helper for main in the utility script."""
    print("FINANCE BOT SETUP CHECK")
    print(f"Project root: {PROJECT_ROOT}\n")

    check_env_file()
    mode = check_runtime_env()
    service_account_ok = check_service_account_file()
    check_imports()
    check_google_sheets_schema(service_account_ok)

    if mode == "polling":
        print("\nMode polling tidak membutuhkan domain, public URL, atau webhook secret.")

    return 1 if print_summary() else 0


if __name__ == "__main__":
    raise SystemExit(main())
