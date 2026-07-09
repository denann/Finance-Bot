"""Beginner-friendly setup checker for validating environment variables, service account files, package imports, and Google Sheets schema."""


# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import importlib for this module's local operations.
import importlib
# Import json for this module's local operations.
import json
# Import os for this module's local operations.
import os
# Import sys for this module's local operations.
import sys
# Import pathlib so this module can use its helpers.
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Run this operation in a guarded block so failures can be handled.
try:
    # Import dotenv so this module can use its helpers.
    from dotenv import load_dotenv
# Handle an expected failure from the guarded operation above.
except Exception:  # pragma: no cover - dependency may not be installed yet
    load_dotenv = None

if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")

RESULTS: list[tuple[str, str, str]] = []


def _add(status: str, title: str, detail: str = ""):
    """Coordinate the add logic in the developer utility script.

    Args:
        status: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        title: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        detail: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Append the current value to RESULTS.
    RESULTS.append((status, title, detail))
    icon = {"ok": "✅", "warn": "🟡", "fail": "❌", "skip": "⚪"}.get(status, "•")
    print(f"{icon} {title}" + (f" — {detail}" if detail else ""))


def ok(title: str, detail: str = ""):
    """Coordinate the ok logic in the developer utility script.

    Args:
        title: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        detail: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    _add("ok", title, detail)


def warn(title: str, detail: str = ""):
    """Coordinate the warn logic in the developer utility script.

    Args:
        title: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        detail: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    _add("warn", title, detail)


def fail(title: str, detail: str = ""):
    """Coordinate the fail logic in the developer utility script.

    Args:
        title: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        detail: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    _add("fail", title, detail)


def skip(title: str, detail: str = ""):
    """Coordinate the skip logic in the developer utility script.

    Args:
        title: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        detail: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    _add("skip", title, detail)


# Helper for mask.
def mask(value: str) -> str:
    """Coordinate the mask logic in the developer utility script.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    value = str(value or "")
    if len(value) <= 10:
        return "***" if value else ""
    return f"{value[:4]}...{value[-4:]}"


def env(name: str, default: str = "") -> str:
    """Coordinate the env logic in the developer utility script.

    Args:
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        default: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    return str(os.getenv(name, default) or "").strip()


# Helper for check env file.
def check_env_file():
    """Validate conditions for the check env file workflow in the developer utility script.

    Args:
        None.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        ok(".env ditemukan", str(env_path.relative_to(PROJECT_ROOT)))
    # Use the fallback path when no earlier branch matched.
    else:
        fail(".env belum ditemukan", "copy .env.example menjadi .env lalu isi nilainya")


# Helper for check runtime env.
def check_runtime_env() -> str:
    """Validate conditions for the check runtime env workflow in the developer utility script.

    Args:
        None.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    mode = env("BOT_MODE", "polling").lower()
    if mode not in {"polling", "webhook"}:
        fail("BOT_MODE tidak valid", "gunakan polling atau webhook")
        mode = "polling"
    # Use the fallback path when no earlier branch matched.
    else:
        ok("BOT_MODE", mode)

    required = [
        "TELEGRAM_BOT_TOKEN",
        "ALLOWED_USER_ID",
        "GOOGLE_SHEET_ID",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "GEMINI_API_KEY",
    ]

    # Iterate through each name.
    for name in required:
        value = env(name)
        if value:
            ok(f"{name} terisi", mask(value))
        # Use the fallback path when no earlier branch matched.
        else:
            fail(f"{name} belum diisi")

    if env("GEMINI_MODEL"):
        ok("GEMINI_MODEL terisi", env("GEMINI_MODEL"))
    # Use the fallback path when no earlier branch matched.
    else:
        warn("GEMINI_MODEL belum diisi", "kode punya fallback, tapi README menyarankan isi eksplisit")

    # Run this operation in a guarded block so failures can be handled.
    try:
        int(env("ALLOWED_USER_ID", "0"))
        ok("ALLOWED_USER_ID valid", "angka")
    # Handle an expected failure from the guarded operation above.
    except ValueError:
        fail("ALLOWED_USER_ID tidak valid", "harus berupa angka Telegram user ID")

    if mode == "webhook":
        for name in ["WEBHOOK_URL", "TELEGRAM_WEBHOOK_SECRET", "APP_PORT"]:
            value = env(name)
            if value:
                ok(f"{name} terisi", mask(value))
            # Use the fallback path when no earlier branch matched.
            else:
                fail(f"{name} belum diisi", "wajib untuk webhook mode")

    return mode


# Helper for check service account file.
def check_service_account_file():
    """Validate conditions for the check service account file workflow in the developer utility script.

    Args:
        None.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    raw_path = env("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
    path = Path(raw_path)
    # Validate missing path.is absolute() before continuing.
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    # Validate missing path.exists() before continuing.
    if not path.exists():
        fail("File service account tidak ditemukan", str(path))
        return False

    ok("File service account ditemukan", str(path.relative_to(PROJECT_ROOT)))

    # Run this operation in a guarded block so failures can be handled.
    try:
        data = json.loads(path.read_text())
    # Handle an expected failure from the guarded operation above.
    except Exception as exc:
        fail("File service account tidak bisa dibaca sebagai JSON", f"{type(exc).__name__}: {exc}")
        return False

    client_email = data.get("client_email")
    if client_email:
        ok("client_email service account tersedia", client_email)
        print("   Pastikan Google Sheets sudah di-share ke email ini sebagai Editor.")
    # Use the fallback path when no earlier branch matched.
    else:
        fail("client_email tidak ditemukan di service account JSON")
        return False

    return True


# Helper for check imports.
def check_imports():
    """Validate conditions for the check imports workflow in the developer utility script.

    Args:
        None.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    packages = [
        ("telegram", "python-telegram-bot"),
        ("gspread", "gspread"),
        ("dotenv", "python-dotenv"),
        ("apscheduler", "APScheduler"),
        ("langchain_google_genai", "langchain-google-genai"),
        ("fastapi", "FastAPI, hanya wajib untuk advanced webhook mode"),
    ]

    # Iterate through each module name, label.
    for module_name, label in packages:
        # Run this operation in a guarded block so failures can be handled.
        try:
            importlib.import_module(module_name)
            ok(f"Package import OK: {label}")
        # Handle an expected failure from the guarded operation above.
        except Exception as exc:
            fail(f"Package belum siap: {label}", f"{type(exc).__name__}: {exc}")


# Helper for check google sheets schema.
def check_google_sheets_schema(can_try: bool):
    """Validate conditions for the check google sheets schema workflow in the developer utility script.

    Args:
        can_try: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    needed = ["GOOGLE_SHEET_ID", "GOOGLE_SERVICE_ACCOUNT_JSON"]
    # Validate missing can try or any(not env(name) for name in needed) before continuing.
    if not can_try or any(not env(name) for name in needed):
        skip("Google Sheets schema check", "lengkapi GOOGLE_SHEET_ID dan service account dulu")
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Import app.sheets.client so this module can use its helpers.
        from app.sheets.client import ensure_spreadsheet_schema, get_spreadsheet

        spreadsheet = get_spreadsheet()
        ok("Google Sheets bisa diakses", spreadsheet.title)

        # Build results for the response flow.
        results = ensure_spreadsheet_schema()
        changed = [r for r in results if r.get("actions") != ["no_change"]]
        ok(
            "Google Sheets schema siap",
            f"{len(results)} tab dicek, {len(changed)} tab dibuat/dilengkapi",
        )
    # Handle an expected failure from the guarded operation above.
    except Exception as exc:
        fail("Google Sheets belum bisa diakses / schema belum siap", f"{type(exc).__name__}: {exc}")


# Helper for print summary.
def print_summary():
    """Coordinate the print summary logic in the developer utility script.

    Args:
        None.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    total = len(RESULTS)
    failed = sum(1 for status, _, _ in RESULTS if status == "fail")
    warned = sum(1 for status, _, _ in RESULTS if status == "warn")

    print("\n" + "=" * 72)
    print(f"Setup check selesai: {total} check, {failed} fail, {warned} warning")
    if failed:
        print("❌ Masih ada setup yang perlu diperbaiki sebelum bot dijalankan.")
    # Use the fallback path when no earlier branch matched.
    else:
        print("✅ Setup dasar sudah terlihat siap. Jalankan: python main.py")
    print("=" * 72)

    return failed


# Helper for main.
def main() -> int:
    """Coordinate the main logic in the developer utility script.

    Args:
        None.

    Returns:
        `int` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print("FINANCE BOT SETUP CHECK")
    print(f"Project root: {PROJECT_ROOT}\n")

    check_env_file()
    mode = check_runtime_env()
    # Extract service account ok for validation.
    service_account_ok = check_service_account_file()
    check_imports()
    check_google_sheets_schema(service_account_ok)

    if mode == "polling":
        print("\nMode polling tidak membutuhkan domain, public URL, atau webhook secret.")

    return 1 if print_summary() else 0


if __name__ == "__main__":
    # Raise a clear error so the caller can stop this invalid flow.
    raise SystemExit(main())
