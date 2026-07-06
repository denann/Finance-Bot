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

# Prepare PROJECT ROOT for the next step.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Run this statement as part of the current workflow.
sys.path.insert(0, str(PROJECT_ROOT))

# Run this operation in a guarded block so failures can be handled.
try:
    # Import dotenv so this module can use its helpers.
    from dotenv import load_dotenv
# Handle an expected failure from the guarded operation above.
except Exception:  # pragma: no cover - dependency may not be installed yet
    # Prepare load dotenv for the next step.
    load_dotenv = None

# Handle the case where load_dotenv.
if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")

# Run this statement as part of the current workflow.
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
    # Update RESULTS with the current value.
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


# Define mask for callers in this flow.
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
    # Handle the case where len(value) <= 10.
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


# Define check env file for callers in this flow.
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
    # Handle the case where env_path.exists().
    if env_path.exists():
        ok(".env ditemukan", str(env_path.relative_to(PROJECT_ROOT)))
    # Handle the fallback path after earlier conditions are skipped.
    else:
        fail(".env belum ditemukan", "copy .env.example menjadi .env lalu isi nilainya")


# Define check runtime env for callers in this flow.
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
    # Handle the fallback path after earlier conditions are skipped.
    else:
        ok("BOT_MODE", mode)

    # Open a multi-line structure for the values below.
    required = [
        "TELEGRAM_BOT_TOKEN",
        "ALLOWED_USER_ID",
        "GOOGLE_SHEET_ID",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "GEMINI_API_KEY",
    # Close the structure that was opened above.
    ]

    # Process each name in the current collection.
    for name in required:
        # Prepare value for the next step.
        value = env(name)
        # Handle the case where value.
        if value:
            ok(f"{name} terisi", mask(value))
        # Handle the fallback path after earlier conditions are skipped.
        else:
            fail(f"{name} belum diisi")

    if env("GEMINI_MODEL"):
        ok("GEMINI_MODEL terisi", env("GEMINI_MODEL"))
    # Handle the fallback path after earlier conditions are skipped.
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
            # Prepare value for the next step.
            value = env(name)
            # Handle the case where value.
            if value:
                ok(f"{name} terisi", mask(value))
            # Handle the fallback path after earlier conditions are skipped.
            else:
                fail(f"{name} belum diisi", "wajib untuk webhook mode")

    # Return mode to the caller.
    return mode


# Define check service account file for callers in this flow.
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
    # Prepare path for the next step.
    path = Path(raw_path)
    # Handle the missing or empty path.is_absolute() case.
    if not path.is_absolute():
        # Prepare path for the next step.
        path = PROJECT_ROOT / path

    # Handle the missing or empty path.exists() case.
    if not path.exists():
        fail("File service account tidak ditemukan", str(path))
        # Return False to the caller.
        return False

    ok("File service account ditemukan", str(path.relative_to(PROJECT_ROOT)))

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare data for the next step.
        data = json.loads(path.read_text())
    # Handle an expected failure from the guarded operation above.
    except Exception as exc:
        fail("File service account tidak bisa dibaca sebagai JSON", f"{type(exc).__name__}: {exc}")
        # Return False to the caller.
        return False

    client_email = data.get("client_email")
    # Handle the case where client_email.
    if client_email:
        ok("client_email service account tersedia", client_email)
        print("   Pastikan Google Sheets sudah di-share ke email ini sebagai Editor.")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        fail("client_email tidak ditemukan di service account JSON")
        # Return False to the caller.
        return False

    # Return True to the caller.
    return True


# Define check imports for callers in this flow.
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
    # Open a multi-line structure for the values below.
    packages = [
        ("telegram", "python-telegram-bot"),
        ("gspread", "gspread"),
        ("dotenv", "python-dotenv"),
        ("apscheduler", "APScheduler"),
        ("langchain_google_genai", "langchain-google-genai"),
        ("fastapi", "FastAPI, hanya wajib untuk advanced webhook mode"),
    # Close the structure that was opened above.
    ]

    # Process each module_name, label in the current collection.
    for module_name, label in packages:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Run this statement as part of the current workflow.
            importlib.import_module(module_name)
            ok(f"Package import OK: {label}")
        # Handle an expected failure from the guarded operation above.
        except Exception as exc:
            fail(f"Package belum siap: {label}", f"{type(exc).__name__}: {exc}")


# Define check google sheets schema for callers in this flow.
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
    # Handle the missing or empty can_try or any(not env(name) for name in needed) case.
    if not can_try or any(not env(name) for name in needed):
        skip("Google Sheets schema check", "lengkapi GOOGLE_SHEET_ID dan service account dulu")
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Import app.sheets.client so this module can use its helpers.
        from app.sheets.client import ensure_spreadsheet_schema, get_spreadsheet

        # Prepare spreadsheet for the next step.
        spreadsheet = get_spreadsheet()
        ok("Google Sheets bisa diakses", spreadsheet.title)

        # Prepare results for the next step.
        results = ensure_spreadsheet_schema()
        changed = [r for r in results if r.get("actions") != ["no_change"]]
        # Open a multi-line structure for the values below.
        ok(
            "Google Sheets schema siap",
            f"{len(results)} tab dicek, {len(changed)} tab dibuat/dilengkapi",
        # Close the structure that was opened above.
        )
    # Handle an expected failure from the guarded operation above.
    except Exception as exc:
        fail("Google Sheets belum bisa diakses / schema belum siap", f"{type(exc).__name__}: {exc}")


# Define print summary for callers in this flow.
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
    # Prepare total for the next step.
    total = len(RESULTS)
    failed = sum(1 for status, _, _ in RESULTS if status == "fail")
    warned = sum(1 for status, _, _ in RESULTS if status == "warn")

    print("\n" + "=" * 72)
    print(f"Setup check selesai: {total} check, {failed} fail, {warned} warning")
    # Handle the case where failed.
    if failed:
        print("❌ Masih ada setup yang perlu diperbaiki sebelum bot dijalankan.")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        print("✅ Setup dasar sudah terlihat siap. Jalankan: python main.py")
    print("=" * 72)

    # Return failed to the caller.
    return failed


# Define main for callers in this flow.
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

    # Run this statement as part of the current workflow.
    check_env_file()
    # Prepare mode for the next step.
    mode = check_runtime_env()
    # Prepare service account ok for the next step.
    service_account_ok = check_service_account_file()
    # Run this statement as part of the current workflow.
    check_imports()
    # Run this statement as part of the current workflow.
    check_google_sheets_schema(service_account_ok)

    if mode == "polling":
        print("\nMode polling tidak membutuhkan domain, public URL, atau webhook secret.")

    # Return 1 if print_summary() else 0 to the caller.
    return 1 if print_summary() else 0


if __name__ == "__main__":
    # Raise a clear error so the caller can stop this invalid flow.
    raise SystemExit(main())
