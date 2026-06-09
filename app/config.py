import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID"))

# Google Sheets
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# App
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
APP_PORT = int(os.getenv("APP_PORT", 8000))

# Sheet tab names — satu tempat, gampang diubah
SHEET_TRANSACTIONS = "transactions"
SHEET_ACCOUNTS = "accounts"
SHEET_BUDGETS = "budgets"
SHEET_DEBTS = "debts"
SHEET_DEBT_PAYMENTS = "debt_payments"
SHEET_CATEGORIES = "categories"
SHEET_MONTHLY_SUMMARY = "monthly_summary"
