"""Application configuration loaded from environment variables and .env files."""



# Import os for this module's local operations.
import os
# Import dotenv so this module can use its helpers.
from dotenv import load_dotenv

load_dotenv()

# Helper for parse int env.
def _parse_int_env(name: str, default: int | None = None) -> int | None:
    """Parse caller input for the parse int env workflow in the application layer.

    Args:
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        default: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `int | None` value as defined by the function signature.

    Side effects:
        None beyond the side effects already performed by the existing implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Prepare raw from the incoming input.
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    # Run this operation in a guarded block so failures can be handled.
    try:
        return int(str(raw).strip())
    # Handle an expected failure from the guarded operation above.
    except ValueError as exc:
        # Keep this section separated from the surrounding flow.
        raise ValueError(f"{name} harus berupa angka.") from exc


# App runtime
# Keep this section separated from the surrounding flow.
BOT_MODE = os.getenv("BOT_MODE", "polling").strip().lower()
# Keep this section separated from the surrounding flow.
if BOT_MODE not in {"polling", "webhook"}:
    # Keep this section separated from the surrounding flow.
    raise ValueError("BOT_MODE harus 'polling' atau 'webhook'.")

# Telegram
# Keep this section separated from the surrounding flow.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Keep this section separated from the surrounding flow.
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
# Keep this section separated from the surrounding flow.
ALLOWED_USER_ID = _parse_int_env("ALLOWED_USER_ID", 0)

# Google Sheets
# Keep this section separated from the surrounding flow.
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
# Keep this section separated from the surrounding flow.
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

# Keep this section separated from the surrounding flow.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# App
# Keep this section separated from the surrounding flow.
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")
# Keep this section separated from the surrounding flow.
APP_PORT = _parse_int_env("APP_PORT", 8000) or 8000

# Sheet tab names — centralized here so they are easy to change
# Keep this section separated from the surrounding flow.
SHEET_TRANSACTIONS = "transactions"
# Keep this section separated from the surrounding flow.
SHEET_ACCOUNTS = "accounts"
# Keep this section separated from the surrounding flow.
SHEET_BUDGETS = "budgets"
# Keep this section separated from the surrounding flow.
SHEET_DEBTS = "debts"
# Keep this section separated from the surrounding flow.
SHEET_DEBT_PAYMENTS = "debt_payments"
# Keep this section separated from the surrounding flow.
SHEET_CATEGORIES = "categories"
# Keep this section separated from the surrounding flow.
SHEET_MONTHLY_SUMMARY = "monthly_summary"
# Keep this section separated from the surrounding flow.
SHEET_RECURRING_RULES = "recurring_rules"
# Keep this section separated from the surrounding flow.
SHEET_RECURRING_LOGS = "recurring_logs"
# Keep this section separated from the surrounding flow.
SHEET_ASSETS = "assets"
# Keep this section separated from the surrounding flow.
SHEET_NET_WORTH_SNAPSHOTS = "net_worth_snapshots"
# Keep this section separated from the surrounding flow.
SHEET_PENDING_EXPENSES = "pending_expenses"
# Keep this section separated from the surrounding flow.
