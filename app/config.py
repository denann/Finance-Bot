"""Application configuration loaded from environment variables and .env files."""


import os
from dotenv import load_dotenv

load_dotenv()

def _parse_int_env(name: str, default: int | None = None) -> int | None:
    """Read an environment variable and convert it to integer with a safe fallback."""
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(str(raw).strip())
    except ValueError as exc:
        raise ValueError(f"{name} harus berupa angka.") from exc


# App runtime
BOT_MODE = os.getenv("BOT_MODE", "polling").strip().lower()
if BOT_MODE not in {"polling", "webhook"}:
    raise ValueError("BOT_MODE harus 'polling' atau 'webhook'.")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
ALLOWED_USER_ID = _parse_int_env("ALLOWED_USER_ID", 0)

# Google Sheets
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

# AI routing note: keep transaction/debt inputs away from insight routing when they contain amounts.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# App
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")
APP_PORT = _parse_int_env("APP_PORT", 8000) or 8000

# Sheet tab names — satu tempat, gampang diubah
SHEET_TRANSACTIONS = "transactions"
SHEET_ACCOUNTS = "accounts"
SHEET_BUDGETS = "budgets"
SHEET_DEBTS = "debts"
SHEET_DEBT_PAYMENTS = "debt_payments"
SHEET_CATEGORIES = "categories"
SHEET_MONTHLY_SUMMARY = "monthly_summary"
SHEET_RECURRING_RULES = "recurring_rules"
SHEET_RECURRING_LOGS = "recurring_logs"
SHEET_ASSETS = "assets"
SHEET_PENDING_EXPENSES = "pending_expenses"
SHEET_NET_WORTH_SNAPSHOTS = "net_worth_snapshots"