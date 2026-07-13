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


def _parse_float_env(name: str, default: float) -> float:
    """Parse a positive floating-point environment value."""

    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return float(default)
    try:
        value = float(str(raw).strip())
    except ValueError as exc:
        raise ValueError(f"{name} harus berupa angka.") from exc
    if value <= 0:
        raise ValueError(f"{name} harus lebih dari 0.")
    return value


def _parse_bool_env(name: str, default: bool) -> bool:
    """Parse a strict boolean environment value with a safe default."""

    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return bool(default)
    normalized = str(raw).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} harus berupa true/false.")


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
SHEETS_TIMEOUT_SECONDS = _parse_float_env("SHEETS_TIMEOUT_SECONDS", 20.0)
SHEETS_INTERACTIVE_CONCURRENCY = int(_parse_int_env("SHEETS_INTERACTIVE_CONCURRENCY", 2) or 0)
GEMINI_CONCURRENCY = int(_parse_int_env("GEMINI_CONCURRENCY", 1) or 0)
SCHEDULED_WORK_CONCURRENCY = int(_parse_int_env("SCHEDULED_WORK_CONCURRENCY", 1) or 0)
SHEETS_REQUEST_ROW_BUDGET = int(_parse_int_env("SHEETS_REQUEST_ROW_BUDGET", 50_000) or 0)
TRANSACTION_SORT_MODE = os.getenv("TRANSACTION_SORT_MODE", "server").strip().lower()

# Keep this section separated from the surrounding flow.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_TIMEOUT_SECONDS = _parse_float_env("GEMINI_TIMEOUT_SECONDS", 30.0)
GEMINI_MAX_OUTPUT_TOKENS = int(_parse_int_env("GEMINI_MAX_OUTPUT_TOKENS", 2048) or 0)
GEMINI_MAX_OUTPUT_CHARS = int(_parse_int_env("GEMINI_MAX_OUTPUT_CHARS", 50000) or 0)
GEMINI_MAX_INPUT_CHARS = int(_parse_int_env("GEMINI_MAX_INPUT_CHARS", 100000) or 0)
GEMINI_CALLS_PER_UPDATE = int(_parse_int_env("GEMINI_CALLS_PER_UPDATE", 1) or 0)
AI_CONTEXT_RECORD_LIMIT = int(_parse_int_env("AI_CONTEXT_RECORD_LIMIT", 40) or 0)

# App
# Keep this section separated from the surrounding flow.
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")
# Keep this section separated from the surrounding flow.
APP_PORT = _parse_int_env("APP_PORT", 8000) or 8000
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Jakarta").strip() or "Asia/Jakarta"
APP_INSTANCE_COUNT = int(_parse_int_env("APP_INSTANCE_COUNT", 1) or 0)
SCHEDULER_ENABLED = _parse_bool_env("SCHEDULER_ENABLED", True)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"
LOG_FILE = os.getenv("LOG_FILE", "logs/finance_bot.log").strip()

if APP_INSTANCE_COUNT < 1:
    raise ValueError("APP_INSTANCE_COUNT harus minimal 1.")
if GEMINI_MAX_OUTPUT_TOKENS < 1:
    raise ValueError("GEMINI_MAX_OUTPUT_TOKENS harus minimal 1.")
if GEMINI_MAX_OUTPUT_CHARS < 1:
    raise ValueError("GEMINI_MAX_OUTPUT_CHARS harus minimal 1.")
if min(GEMINI_MAX_INPUT_CHARS, GEMINI_CALLS_PER_UPDATE, AI_CONTEXT_RECORD_LIMIT) < 1:
    raise ValueError("Batas input/call/context Gemini harus minimal 1.")
if min(SHEETS_INTERACTIVE_CONCURRENCY, GEMINI_CONCURRENCY, SCHEDULED_WORK_CONCURRENCY) < 1:
    raise ValueError("Batas concurrency Phase 3 harus minimal 1.")
if SHEETS_REQUEST_ROW_BUDGET < 1:
    raise ValueError("SHEETS_REQUEST_ROW_BUDGET harus minimal 1.")
if TRANSACTION_SORT_MODE not in {"server", "legacy"}:
    raise ValueError("TRANSACTION_SORT_MODE harus 'server' atau 'legacy'.")

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
