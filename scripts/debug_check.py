"""Developer diagnostic script for checking configuration, dependencies, Google Sheets, Gemini, services, handlers, and scheduler setup."""


# Import os for this module's local operations.
import os
# Import sys for this module's local operations.
import sys
# Import traceback for this module's local operations.
import traceback
# Import importlib for this module's local operations.
import importlib
# Import datetime so this module can use its helpers.
from datetime import datetime
# Import pathlib so this module can use its helpers.
from pathlib import Path
# Import inspect for this module's local operations.
import inspect

# ── Setup project root ────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Run this operation in a guarded block so failures can be handled.
try:
    # Import dotenv so this module can use its helpers.
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
# Handle an expected failure from the guarded operation above.
except Exception:
    # Keep this intentionally empty block valid.
    pass


# ── Pretty print helpers ──────────────────────────────────────────────────────

# Build RESULTS for the response flow.
RESULTS = []


# Helper for now str.
def now_str():
    """Coordinate the now str logic in the developer utility script.

    Args:
        None.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Helper for rupiah.
def rupiah(amount):
    """Coordinate the rupiah logic in the developer utility script.

    Args:
        amount: Numeric amount or amount-like user input to parse or format.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        return f"Rp{int(float(amount or 0)):,}".replace(",", ".")
    # Handle an expected failure from the guarded operation above.
    except Exception:
        return str(amount)


def add_result(area, name, status, expected, actual="", error=""):
    """Coordinate the add result logic in the developer utility script.

    Args:
        area: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        status: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        expected: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        actual: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        error: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    RESULTS.append(
        {
            "area": area,
            "name": name,
            "status": status,
            "expected": expected,
            "actual": actual,
            "error": error,
        }
    )


def ok(area, name, expected="OK", actual="OK"):
    """Coordinate the ok logic in the developer utility script.

    Args:
        area: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        expected: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        actual: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    add_result(area, name, "PASS", expected, actual)


def warn(area, name, expected="OK", actual="Warning", error=""):
    """Coordinate the warn logic in the developer utility script.

    Args:
        area: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        expected: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        actual: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        error: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    add_result(area, name, "WARN", expected, actual, error)


def fail(area, name, expected="OK", actual="Failed", error=""):
    """Coordinate the fail logic in the developer utility script.

    Args:
        area: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        expected: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        actual: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        error: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    add_result(area, name, "FAIL", expected, actual, error)


def skip(area, name, expected="Available", actual="Skipped", error=""):
    """Coordinate the skip logic in the developer utility script.

    Args:
        area: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        expected: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        actual: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        error: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    add_result(area, name, "SKIP", expected, actual, error)


# Helper for print header.
def print_header(title):
    """Coordinate the print header logic in the developer utility script.

    Args:
        title: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


# Helper for print summary.
def print_summary():
    """Coordinate the print summary logic in the developer utility script.

    Args:
        None.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("DEBUG SUMMARY")

    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["status"] == "PASS")
    warned = sum(1 for r in RESULTS if r["status"] == "WARN")
    failed = sum(1 for r in RESULTS if r["status"] == "FAIL")
    skipped = sum(1 for r in RESULTS if r["status"] == "SKIP")

    print(f"Run at : {now_str()}")
    print(f"Total  : {total}")
    print(f"PASS   : {passed}")
    print(f"WARN   : {warned}")
    print(f"FAIL   : {failed}")
    print(f"SKIP   : {skipped}")

    print("\nDETAIL:")
    # Iterate through each i, r.
    for i, r in enumerate(RESULTS, 1):
        icon = {
            "PASS": "✅",
            "WARN": "🟡",
            "FAIL": "❌",
            "SKIP": "⚪",
        }.get(r["status"], "❓")

        print(f"\n{i}. {icon} [{r['area']}] {r['name']}")
        print(f"   Expected: {r['expected']}")
        print(f"   Actual  : {r['actual']}")

        if r["error"]:
            print(f"   Error   : {r['error']}")

    print("\n" + "=" * 90)

    if failed == 0:
        print("✅ RESULT: Tidak ada FAIL. Bot terlihat aman secara structural/read-only check.")
    # Use the fallback path when no earlier branch matched.
    else:
        print("❌ RESULT: Ada FAIL. Cek detail error di atas.")

    print("=" * 90)


# Helper for safe run.
def safe_run(area, name, expected, func):
    """Coordinate the safe run logic in the developer utility script.

    Args:
        area: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        expected: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        func: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        actual = func()
        ok(area, name, expected=expected, actual=actual)
        return actual
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        fail(
            area,
            name,
            expected=expected,
            actual="Exception",
            error=f"{type(e).__name__}: {str(e)}",
        )
        return None


def import_module_safe(module_name, area="Import"):
    """Coordinate the import module safe logic in the developer utility script.

    Args:
        module_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        area: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        module = importlib.import_module(module_name)
        ok(area, module_name, expected="Module import sukses", actual="Imported")
        return module
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        fail(
            area,
            module_name,
            expected="Module import sukses",
            actual="Import failed",
            error=f"{type(e).__name__}: {str(e)}",
        )
        return None


# Helper for has function.
def has_function(module, func_name, area):
    """Evaluate the has function condition in the developer utility script.

    Args:
        module: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        func_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        area: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    if module is None:
        skip(area, func_name, expected="Function tersedia", actual="Module tidak tersedia")
        return False

    exists = hasattr(module, func_name)

    if exists:
        ok(area, func_name, expected="Function tersedia", actual="Available")
    # Use the fallback path when no earlier branch matched.
    else:
        fail(area, func_name, expected="Function tersedia", actual="Missing")

    return exists


# ── 1. Environment check ──────────────────────────────────────────────────────

# Helper for check environment.
def check_environment():
    """Validate conditions for the check environment workflow in the developer utility script.

    Args:
        None.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("1. ENVIRONMENT CHECK")

    required_envs = [
        "BOT_MODE",
        "TELEGRAM_BOT_TOKEN",
        "ALLOWED_USER_ID",
        "GOOGLE_SHEET_ID",
        "GEMINI_API_KEY",
    ]

    # Iterate through each env name.
    for env_name in required_envs:
        value = os.getenv(env_name)

        if value:
            masked = str(value)
            if len(masked) > 10:
                masked = masked[:4] + "..." + masked[-4:]
            ok("Env", env_name, expected="Env terisi", actual=masked)
        # Use the fallback path when no earlier branch matched.
        else:
            fail("Env", env_name, expected="Env terisi", actual="Kosong / tidak ditemukan")

    print("Environment check selesai.")


# ── 2. Import check ───────────────────────────────────────────────────────────

# Helper for check imports.
def check_imports():
    """Validate conditions for the check imports workflow in the developer utility script.

    Args:
        None.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("2. IMPORT CHECK")

    modules = {}

    module_names = [
        "app.config",
        "app.sheets.client",
        "app.nlp.normalizer",
        "app.nlp.regex_parser",
        "app.nlp.gemini_parser",
        "app.services.transaction_service",
        "app.services.budget_service",
        "app.services.report_service",
        "app.services.debt_service",
        "app.services.recurring_service",
        "app.services.net_worth_service",
        "app.scheduler.jobs",
        "app.bot.handlers",
        "app.bot.application",
        "main",
    ]

    # Iterate through each module name.
    for module_name in module_names:
        modules[module_name] = import_module_safe(module_name)

    return modules


# ── 3. Config constants check ─────────────────────────────────────────────────

# Helper for check config.
def check_config(modules):
    """Validate conditions for the check config workflow in the developer utility script.

    Args:
        modules: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("3. CONFIG CONSTANTS CHECK")

    config = modules.get("app.config")

    required_constants = [
        "SHEET_TRANSACTIONS",
        "SHEET_ACCOUNTS",
        "SHEET_BUDGETS",
        "SHEET_DEBTS",
        "SHEET_DEBT_PAYMENTS",
    ]

    optional_constants = [
        "SHEET_RECURRING_RULES",
        "SHEET_RECURRING_LOGS",
        "SHEET_ASSETS",
        "SHEET_PENDING_EXPENSES",
        "SHEET_NET_WORTH_SNAPSHOTS",
    ]

    # Iterate through each const.
    for const in required_constants:
        if config and hasattr(config, const):
            ok("Config", const, expected="Constant tersedia", actual=getattr(config, const))
        # Use the fallback path when no earlier branch matched.
        else:
            fail("Config", const, expected="Constant tersedia", actual="Missing")

    # Iterate through each const.
    for const in optional_constants:
        if config and hasattr(config, const):
            ok("Config", const, expected="Constant tersedia", actual=getattr(config, const))
        # Use the fallback path when no earlier branch matched.
        else:
            warn("Config", const, expected="Constant tersedia kalau fitur terkait aktif", actual="Missing")


# ── 4. Google Sheets read check ───────────────────────────────────────────────

# Helper for check google sheets.
def check_google_sheets(modules):
    """Validate conditions for the check google sheets workflow in the developer utility script.

    Args:
        modules: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("4. GOOGLE SHEETS CHECK")

    config = modules.get("app.config")
    sheets = modules.get("app.sheets.client")

    # Validate missing sheets before continuing.
    if not sheets:
        skip("Sheets", "All checks", expected="Sheets client tersedia", actual="Skipped")
        return

    safe_run(
        "Sheets",
        "get_spreadsheet()",
        "Koneksi Google Sheets sukses",
        lambda: getattr(sheets.get_spreadsheet(), "title", "Connected"),
    )

    sheet_constants = [
        ("transactions", "SHEET_TRANSACTIONS"),
        ("accounts", "SHEET_ACCOUNTS"),
        ("budgets", "SHEET_BUDGETS"),
        ("debts", "SHEET_DEBTS"),
        ("debt_payments", "SHEET_DEBT_PAYMENTS"),
        ("recurring_rules", "SHEET_RECURRING_RULES"),
        ("recurring_logs", "SHEET_RECURRING_LOGS"),
        ("assets", "SHEET_ASSETS"),
        ("pending_expenses", "SHEET_PENDING_EXPENSES"),
        ("net_worth_snapshots", "SHEET_NET_WORTH_SNAPSHOTS"),
    ]

    # Iterate through each label, const name.
    for label, const_name in sheet_constants:
        if config and hasattr(config, const_name):
            sheet_name = getattr(config, const_name)

            # Helper for read sheet.
            def read_sheet(sheet_name=sheet_name):
                """Retrieve data needed by the read sheet workflow in the developer utility script.

                Args:
                    sheet_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.

                Returns:
                    Value produced by the existing return statements; shape is determined by the current implementation.

                Side effects:
                    May print diagnostics, read local files, or call local test helpers according to the utility implementation.

                Flow constraints:
                    Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
                """
                # Load records for the current calculation.
                records = sheets.get_all_records(sheet_name)
                return f"{len(records)} row readable"

            safe_run("Sheets", f"Sheet {label}", "Sheet bisa dibaca", read_sheet)
        # Use the fallback path when no earlier branch matched.
        else:
            warn("Sheets", f"Sheet {label}", expected="Constant tersedia", actual=f"{const_name} missing")


# ── 5. NLP parser check ───────────────────────────────────────────────────────

# Helper for check nlp.
def check_nlp(modules):
    """Validate conditions for the check nlp workflow in the developer utility script.

    Args:
        modules: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("5. NLP PARSER CHECK")

    normalizer = modules.get("app.nlp.normalizer")
    regex_parser = modules.get("app.nlp.regex_parser")

    if normalizer and hasattr(normalizer, "extract_amount_from_text"):
        samples = [
            ("25rb", 25000),
            ("8 juta", 8000000),
            ("150.000", 150000),
        ]

        # Iterate through each text, expected amount.
        for text, expected_amount in samples:
            # Helper for run.
            def run(text=text):
                """Coordinate the run logic in the developer utility script.

                Args:
                    text: Raw text input to parse, normalize, validate, or display.

                Returns:
                    Value produced by the existing return statements; shape is determined by the current implementation.

                Side effects:
                    May print diagnostics, read local files, or call local test helpers according to the utility implementation.

                Flow constraints:
                    Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
                """
                return normalizer.extract_amount_from_text(text)

            actual = safe_run("NLP", f"extract_amount_from_text('{text}')", f"{expected_amount}", run)

            # Handle actual is not None and int(float(actual)) != expected amount.
            if actual is not None and int(float(actual)) != expected_amount:
                warn("NLP", f"Amount expectation '{text}'", expected=str(expected_amount), actual=str(actual))
    # Use the fallback path when no earlier branch matched.
    else:
        fail("NLP", "extract_amount_from_text", expected="Function tersedia", actual="Missing")

    if regex_parser and hasattr(regex_parser, "parse_with_regex"):
        parser_samples = [
            ("beli kopi 25000", "expense"),
            ("gaji masuk 8000000", "income"),
        ]

        # Iterate through each text, expected type.
        for text, expected_type in parser_samples:
            # Helper for run.
            def run(text=text):
                """Coordinate the run logic in the developer utility script.

                Args:
                    text: Raw text input to parse, normalize, validate, or display.

                Returns:
                    Value produced by the existing return statements; shape is determined by the current implementation.

                Side effects:
                    May print diagnostics, read local files, or call local test helpers according to the utility implementation.

                Flow constraints:
                    Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
                """
                parsed = regex_parser.parse_with_regex(text)
                # Validate missing parsed before continuing.
                if not parsed:
                    return "None"
                return f"type={parsed.get('type')}, amount={parsed.get('amount')}, category={parsed.get('category')}"

            actual = safe_run("NLP", f"parse_with_regex('{text}')", f"type={expected_type}", run)

            if actual and f"type={expected_type}" not in str(actual):
                warn("NLP", f"Parser expectation '{text}'", expected=f"type={expected_type}", actual=str(actual))
    # Use the fallback path when no earlier branch matched.
    else:
        fail("NLP", "parse_with_regex", expected="Function tersedia", actual="Missing")

    if regex_parser and hasattr(regex_parser, "parse_debt_input"):
        debt_samples = [
            "Budi minjem 300000",
            "hutang ke Budi 300000",
            "bayar hutang Budi 100000",
        ]

        # Iterate through each text.
        for text in debt_samples:
            # Helper for run.
            def run(text=text):
                """Coordinate the run logic in the developer utility script.

                Args:
                    text: Raw text input to parse, normalize, validate, or display.

                Returns:
                    Value produced by the existing return statements; shape is determined by the current implementation.

                Side effects:
                    May print diagnostics, read local files, or call local test helpers according to the utility implementation.

                Flow constraints:
                    Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
                """
                parsed = regex_parser.parse_debt_input(text)
                # Validate missing parsed before continuing.
                if not parsed:
                    return "None"
                return f"intent={parsed.get('intent')}, person={parsed.get('person_name')}, amount={parsed.get('amount')}"

            safe_run("NLP", f"parse_debt_input('{text}')", "Debt intent terbaca", run)
    # Use the fallback path when no earlier branch matched.
    else:
        fail("NLP", "parse_debt_input", expected="Function tersedia", actual="Missing")


# ── 6. Transaction service read-only check ────────────────────────────────────

# Helper for check transaction service.
def check_transaction_service(modules):
    """Validate conditions for the check transaction service workflow in the developer utility script.

    Args:
        modules: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("6. TRANSACTION SERVICE CHECK")

    tx = modules.get("app.services.transaction_service")

    required_functions = [
        "get_all_accounts",
        "save_transaction",
        "save_transactions_batch",
    ]

    optional_functions = [
        "get_recent_transactions",
        "get_transactions_for_export",
        "preview_delete_transactions_by_refs",
        "delete_transactions_by_refs",
        "preview_edit_transaction_by_ref",
        "edit_transaction_by_ref",
    ]

    # Iterate through each fn.
    for fn in required_functions:
        has_function(tx, fn, "Transaction Service")

    # Iterate through each fn.
    for fn in optional_functions:
        if not has_function(tx, fn, "Transaction Service"):
            warn("Transaction Service", fn, expected="Ada kalau phase terkait sudah dipasang", actual="Missing")

    if tx and hasattr(tx, "get_all_accounts"):
        safe_run(
            "Transaction Service",
            "get_all_accounts()",
            "List rekening terbaca",
            lambda: f"{len(tx.get_all_accounts())} accounts",
        )

    if tx and hasattr(tx, "get_recent_transactions"):
        safe_run(
            "Transaction Service",
            "get_recent_transactions(limit=5)",
            "Transaksi terakhir terbaca",
            lambda: f"{len(tx.get_recent_transactions(limit=5))} transactions",
        )

    if tx and hasattr(tx, "get_transactions_for_export"):
        safe_run(
            "Transaction Service",
            "get_transactions_for_export('month')",
            "Export data bulan ini siap",
            lambda: f"{len(tx.get_transactions_for_export('month').get('records', []))} records",
        )


# ── 7. Report service check ───────────────────────────────────────────────────

# Helper for check report service.
def check_report_service(modules):
    """Validate conditions for the check report service workflow in the developer utility script.

    Args:
        modules: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("7. REPORT SERVICE CHECK")

    report = modules.get("app.services.report_service")

    funcs = [
        "get_daily_report",
        "get_weekly_report",
        "get_monthly_report",
        "search_transactions",
    ]

    # Iterate through each fn.
    for fn in funcs:
        has_function(report, fn, "Report Service")

    if report and hasattr(report, "get_daily_report"):
        safe_run(
            "Report Service",
            "get_daily_report()",
            "Report harian terbaca",
            lambda: f"count={report.get_daily_report().get('count')}",
        )

    if report and hasattr(report, "get_weekly_report"):
        safe_run(
            "Report Service",
            "get_weekly_report()",
            "Report mingguan terbaca",
            lambda: f"count={report.get_weekly_report().get('count')}",
        )

    if report and hasattr(report, "get_monthly_report"):
        safe_run(
            "Report Service",
            "get_monthly_report()",
            "Report bulanan terbaca",
            lambda: f"count={report.get_monthly_report().get('count')}",
        )

    if report and hasattr(report, "search_transactions"):
        safe_run(
            "Report Service",
            "search_transactions('kopi')",
            "Search transaksi jalan",
            lambda: f"{len(report.search_transactions('kopi'))} result",
        )


# ── 8. Budget service check ───────────────────────────────────────────────────

# Helper for check budget service.
def check_budget_service(modules):
    """Validate conditions for the check budget service workflow in the developer utility script.

    Args:
        modules: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("8. BUDGET SERVICE CHECK")

    budget = modules.get("app.services.budget_service")

    funcs = [
        "set_budget",
        "get_budget_summary",
        "check_budget_after_transaction",
        "normalize_month",
        "format_month_label",
        "get_budget_months",
    ]

    # Iterate through each fn.
    for fn in funcs:
        has_function(budget, fn, "Budget Service")

    if budget and hasattr(budget, "get_budget_summary"):
        safe_run(
            "Budget Service",
            "get_budget_summary()",
            "Budget summary terbaca",
            lambda: f"{len(budget.get_budget_summary())} category budget",
        )

    if budget and hasattr(budget, "get_budget_months"):
        safe_run(
            "Budget Service",
            "get_budget_months()",
            "Budget history terbaca",
            lambda: f"{len(budget.get_budget_months())} months",
        )



# Helper for check debt service.
def check_debt_service(modules):
    """Validate conditions for the check debt service workflow in the developer utility script.

    Args:
        modules: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep debt and receivable behavior separated from normal expense/income flows and preserve preview-before-write where applicable.
    """
    print_header("9. DEBT SERVICE CHECK")

    debt = modules.get("app.services.debt_service")

    funcs = [
        "add_debt",
        "add_payment",
        "get_debt_summary",
        "get_debt_by_person",
    ]

    # Iterate through each fn.
    for fn in funcs:
        has_function(debt, fn, "Debt Service")

    if debt and hasattr(debt, "get_debt_summary"):
        safe_run(
            "Debt Service",
            "get_debt_summary()",
            "Debt summary terbaca",
            lambda: str(debt.get_debt_summary()),
        )

    if debt and hasattr(debt, "get_debt_by_person"):
        safe_run(
            "Debt Service",
            "get_debt_by_person('__debug_non_existing__')",
            "Search debt aman meski tidak ada",
            lambda: f"{len(debt.get_debt_by_person('__debug_non_existing__'))} result",
        )


# ── 10. Recurring service check ───────────────────────────────────────────────

# Helper for check recurring service.
def check_recurring_service(modules):
    """Validate conditions for the check recurring service workflow in the developer utility script.

    Args:
        modules: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("10. RECURRING SERVICE CHECK")

    recurring = modules.get("app.services.recurring_service")

    funcs = [
        "add_recurring_rule",
        "get_recurring_rules",
        "get_due_recurring_rules",
        "process_due_recurring_rules",
        "disable_recurring_rule",
        "edit_recurring_rule",
    ]

    # Iterate through each fn.
    for fn in funcs:
        has_function(recurring, fn, "Recurring Service")

    if recurring and hasattr(recurring, "get_recurring_rules"):
        safe_run(
            "Recurring Service",
            "get_recurring_rules(active_only=False)",
            "Recurring rules terbaca",
            lambda: f"{len(recurring.get_recurring_rules(active_only=False))} rules",
        )

    if recurring and hasattr(recurring, "get_due_recurring_rules"):
        safe_run(
            "Recurring Service",
            "get_due_recurring_rules()",
            "Due recurring bisa dicek tanpa write",
            lambda: f"{len(recurring.get_due_recurring_rules())} due rules",
        )

    if recurring and hasattr(recurring, "process_due_recurring_rules"):
        skip(
            "Recurring Service",
            "process_due_recurring_rules()",
            expected="Function ada tapi tidak dijalankan by default",
            actual="Skipped karena bisa membuat transaksi baru",
        )


# ── 11. Net worth service check ───────────────────────────────────────────────

# Helper for check net worth service.
def check_net_worth_service(modules):
    """Validate conditions for the check net worth service workflow in the developer utility script.

    Args:
        modules: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("11. NET WORTH SERVICE CHECK")

    nw = modules.get("app.services.net_worth_service")

    funcs = [
        "add_asset",
        "get_assets",
        "update_asset",
        "deactivate_asset",
        "calculate_net_worth",
        "create_net_worth_snapshot",
        "get_net_worth_snapshots",
    ]

    # Iterate through each fn.
    for fn in funcs:
        has_function(nw, fn, "Net Worth Service")

    if nw and hasattr(nw, "get_assets"):
        safe_run(
            "Net Worth Service",
            "get_assets(active_only=True)",
            "Assets terbaca",
            lambda: f"{len(nw.get_assets(active_only=True))} assets",
        )


    if nw and hasattr(nw, "calculate_net_worth"):
        # Helper for run networth.
        def run_networth():
            """Coordinate the run networth logic in the developer utility script.

            Args:
                None.

            Returns:
                Value produced by the existing return statements; shape is determined by the current implementation.

            Side effects:
                May print diagnostics, read local files, or call local test helpers according to the utility implementation.

            Flow constraints:
                Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
            """
            # Build summary for the response flow.
            summary = nw.calculate_net_worth()
            return (
                f"accounts={rupiah(summary.get('total_accounts'))}, "
                f"assets={rupiah(summary.get('total_assets'))}, "
                f"networth={rupiah(summary.get('net_worth'))}"
            )

        safe_run(
            "Net Worth Service",
            "calculate_net_worth()",
            "Net worth bisa dihitung",
            run_networth,
        )

    if nw and hasattr(nw, "get_net_worth_snapshots"):
        safe_run(
            "Net Worth Service",
            "get_net_worth_snapshots(limit=5)",
            "Snapshot history terbaca",
            lambda: f"{len(nw.get_net_worth_snapshots(limit=5))} snapshots",
        )

    if nw and hasattr(nw, "create_net_worth_snapshot"):
        skip(
            "Net Worth Service",
            "create_net_worth_snapshot()",
            expected="Function ada tapi tidak dijalankan by default",
            actual="Skipped karena menulis snapshot baru",
        )


# ── 12. Bot handlers check ────────────────────────────────────────────────────

# Helper for check bot handlers.
def check_bot_handlers(modules):
    """Validate conditions for the check bot handlers workflow in the developer utility script.

    Args:
        modules: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    print_header("12. BOT HANDLERS CHECK")

    handlers = modules.get("app.bot.handlers")

    handler_names = [
        "start_handler",
        "help_handler",
        "examples_handler",
        "saldo_handler",
        "harian_handler",
        "mingguan_handler",
        "bulanan_handler",
        "budget_handler",
        "budget_history_handler",
        "set_budget_handler",
        "cari_handler",
        "hutang_handler",
        "last_handler",
        "delete_txn_handler",
        "edit_txn_handler",
        "export_handler",
        "recurring_handler",
        "recurring_add_handler",
        "recurring_edit_handler",
        "recurring_run_handler",
        "recurring_off_handler",
        "health_handler",
        "networth_handler",
        "assets_handler",
        "asset_add_handler",
        "asset_update_handler",
        "asset_off_handler",
        "networth_snapshot_handler",
        "networth_history_handler",
        "message_handler",
        "callback_handler",
    ]

    # Iterate through each handler name.
    for handler_name in handler_names:
        has_function(handlers, handler_name, "Bot Handlers")


# ── 13. Scheduler check ───────────────────────────────────────────────────────

# Helper for check scheduler.
def check_scheduler(modules):
    """Validate conditions for the check scheduler workflow in the developer utility script.

    Args:
        modules: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        Value produced by the existing return statements; shape is determined by the current implementation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("13. SCHEDULER CHECK")

    jobs = modules.get("app.scheduler.jobs")

    job_names = [
        "send_message",
        "job_daily_summary",
        "job_weekly_summary",
        "job_monthly_summary",
        "job_debt_reminder",
        "job_recurring_run",
        "create_scheduler",
    ]

    # Iterate through each job name.
    for job_name in job_names:
        has_function(jobs, job_name, "Scheduler")

    if jobs and hasattr(jobs, "create_scheduler"):
        # Helper for run scheduler check.
        def run_scheduler_check():
            """Coordinate the run scheduler check logic in the developer utility script.

            Args:
                None.

            Returns:
                Value produced by the existing return statements; shape is determined by the current implementation.

            Side effects:
                May print diagnostics, read local files, or call local test helpers according to the utility implementation.

            Flow constraints:
                Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
            """
            scheduler = jobs.create_scheduler()
            job_ids = [job.id for job in scheduler.get_jobs()]
            # Run this operation in a guarded block so failures can be handled.
            try:
                scheduler.shutdown(wait=False)
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Keep this intentionally empty block valid.
                pass
            return ", ".join(job_ids) if job_ids else "No jobs registered"

        safe_run(
            "Scheduler",
            "create_scheduler()",
            "Scheduler bisa dibuat dan punya jobs",
            run_scheduler_check,
        )

# ── Regression test section ───────────────────────────────────────────────

# Helper for check regression commands.
def check_regression_commands(modules):
    """Validate conditions for the check regression commands workflow in the developer utility script.

    Args:
        modules: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("14. REGRESSION TEST: COMMAND / NATURAL INPUT YANG DULU BUG")

    handlers = modules.get("app.bot.handlers")
    regex_parser = modules.get("app.nlp.regex_parser")
    tx = modules.get("app.services.transaction_service")

    # ── A. Static source order check ──────────────────────────────────────────
    # Regression test note for a previously fixed edge case.
    # Test note for a project-specific regression case.
    if handlers and hasattr(handlers, "message_handler"):
        # Run this operation in a guarded block so failures can be handled.
        try:
            source = inspect.getsource(handlers.message_handler)

            local_pos = source.find("handle_local_natural_intent")
            debt_pos = source.find("parse_debt_input")

            # Handle local pos != -1 and debt pos != -1 and local pos < debt pos.
            if local_pos != -1 and debt_pos != -1 and local_pos < debt_pos:
                ok(
                    "Regression",
                    "Order: local natural intent sebelum debt parser",
                    expected="handle_local_natural_intent sebelum parse_debt_input",
                    actual="OK",
                )
            # Use the fallback path when no earlier branch matched.
            else:
                fail(
                    "Regression",
                    "Order: local natural intent sebelum debt parser",
                    expected="handle_local_natural_intent harus sebelum parse_debt_input",
                    actual=f"local_pos={local_pos}, debt_pos={debt_pos}",
                    error="Kalau ini FAIL, 'cek hutang' bisa ketangkep debt parser lagi.",
                )

        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            fail(
                "Regression",
                "Inspect message_handler source",
                expected="Source bisa dibaca",
                actual="Failed",
                error=f"{type(e).__name__}: {str(e)}",
            )
    # Use the fallback path when no earlier branch matched.
    else:
        fail(
            "Regression",
            "message_handler tersedia",
            expected="message_handler ada",
            actual="Missing",
        )

    local_helper_names = [
        "handle_local_natural_intent",
        "maybe_text_is_command_typo",
    ]

    # Iterate through each helper name.
    for helper_name in local_helper_names:
        has_function(handlers, helper_name, "Regression")

    # Regression test note for a previously fixed edge case.
    if handlers and hasattr(handlers, "maybe_text_is_command_typo"):
        samples_should_return_none = [
            "cek hutang",
            "cek saldo",
            "cari kopi",
            "lihat transaksi hari ini",
            "lihat transaksi minggu ini",
            "tampilkan saldo",
            "lihat budget bulan ini",
            "hapus transaksi nomor 2",
            "edit transaksi nomor 3 deskripsinya Kopi susu",
        ]

        # Iterate through each text.
        for text in samples_should_return_none:
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Build result for the response flow.
                result = handlers.maybe_text_is_command_typo(text)

                if result is None:
                    ok(
                        "Regression",
                        f"maybe_text_is_command_typo('{text}')",
                        expected="None, tidak boleh dianggap command typo",
                        actual="None",
                    )
                # Use the fallback path when no earlier branch matched.
                else:
                    fail(
                        "Regression",
                        f"maybe_text_is_command_typo('{text}')",
                        expected="None, tidak boleh dianggap command typo",
                        actual=str(result),
                        error="Ini bisa bikin natural command dicegat sebelum Gemini/local intent.",
                    )

            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                fail(
                    "Regression",
                    f"maybe_text_is_command_typo('{text}')",
                    expected="Tidak error",
                    actual="Exception",
                    error=f"{type(e).__name__}: {str(e)}",
                )

    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    if handlers and hasattr(handlers, "maybe_text_is_command_typo"):
        samples_should_suggest = [
            "minguan",
            "detele",
            "bugete",
        ]

        # Iterate through each text.
        for text in samples_should_suggest:
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Build result for the response flow.
                result = handlers.maybe_text_is_command_typo(text)

                if result:
                    ok(
                        "Regression",
                        f"maybe_text_is_command_typo('{text}')",
                        expected="Ada suggestion command",
                        actual=str(result).split("\n")[0],
                    )
                # Use the fallback path when no earlier branch matched.
                else:
                    warn(
                        "Regression",
                        f"maybe_text_is_command_typo('{text}')",
                        expected="Ada suggestion command",
                        actual="None",
                        error="Ini bukan fatal, tapi typo resolver pendek jadi kurang aktif.",
                    )

            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                fail(
                    "Regression",
                    f"maybe_text_is_command_typo('{text}')",
                    expected="Tidak error",
                    actual="Exception",
                    error=f"{type(e).__name__}: {str(e)}",
                )

    # Note:
    if regex_parser and hasattr(regex_parser, "parse_debt_input"):
        text = "cek hutang"

        # Run this operation in a guarded block so failures can be handled.
        try:
            # Build debt result for the response flow.
            debt_result = regex_parser.parse_debt_input(text)

            if debt_result:
                warn(
                    "Regression",
                    "parse_debt_input('cek hutang')",
                    expected="Lebih aman None, tapi boleh kalau order message_handler sudah benar",
                    actual=str(debt_result),
                    error="Pastikan order local natural intent sebelum debt parser PASS.",
                )
            # Use the fallback path when no earlier branch matched.
            else:
                ok(
                    "Regression",
                    "parse_debt_input('cek hutang')",
                    expected="None",
                    actual="None",
                )

        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            fail(
                "Regression",
                "parse_debt_input('cek hutang')",
                expected="Tidak error",
                actual="Exception",
                error=f"{type(e).__name__}: {str(e)}",
            )

    # Regression test note for a previously fixed edge case.
    # Test note for a project-specific regression case.
    if handlers and hasattr(handlers, "parse_local_edit_intent"):
        edit_samples = [
            (
                "edit transaksi nomor 3 deskripsinya Kopi susu",
                "3",
                "description",
                "Kopi susu",
            ),
            (
                "edit transaksi nomor 3 deskripsi Kopi susu",
                "3",
                "description",
                "Kopi susu",
            ),
            (
                "edit transaksi nomor 3 desc Kopi susu",
                "3",
                "description",
                "Kopi susu",
            ),
            (
                "edit transaksi nomor 3 jadi 15000",
                "3",
                "amount",
                "15000",
            ),
        ]

        # Iterate through each text, expected ref, expected field, expected contains.
        for text, expected_ref, expected_field, expected_contains in edit_samples:
            # Run this operation in a guarded block so failures can be handled.
            try:
                parsed = handlers.parse_local_edit_intent(text)

                # Validate missing parsed before continuing.
                if not parsed:
                    fail(
                        "Regression",
                        f"parse_local_edit_intent('{text}')",
                        expected=f"ref={expected_ref}, updates.{expected_field}",
                        actual="None",
                        error="Natural edit belum ke-parse.",
                    )
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                ref = str(parsed.get("ref"))
                updates = parsed.get("updates", {}) or {}

                field_ok = expected_field in updates
                value_ok = expected_contains.lower() in str(updates.get(expected_field, "")).lower()

                # Handle ref == expected ref and field ok and value ok.
                if ref == expected_ref and field_ok and value_ok:
                    ok(
                        "Regression",
                        f"parse_local_edit_intent('{text}')",
                        expected=f"ref={expected_ref}, {expected_field}={expected_contains}",
                        actual=str(parsed),
                    )
                # Use the fallback path when no earlier branch matched.
                else:
                    fail(
                        "Regression",
                        f"parse_local_edit_intent('{text}')",
                        expected=f"ref={expected_ref}, {expected_field}={expected_contains}",
                        actual=str(parsed),
                        error="Parser edit natural tidak sesuai expected.",
                    )

            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                fail(
                    "Regression",
                    f"parse_local_edit_intent('{text}')",
                    expected="Tidak error",
                    actual="Exception",
                    error=f"{type(e).__name__}: {str(e)}",
                )
    # Use the fallback path when no earlier branch matched.
    else:
        warn(
            "Regression",
            "parse_local_edit_intent",
            expected="Function tersedia kalau natural edit sudah dipasang",
            actual="Missing",
        )

    # Regression test note for a previously fixed edge case.
    # Test note for a project-specific regression case.
    if tx and hasattr(tx, "normalize_edit_field"):
        field_samples = [
            ("description", "description"),
            ("deskripsi", "description"),
            ("deskripsinya", "description"),
            ("desc", "description"),
            ("amount", "amount"),
            ("nominal", "amount"),
        ]

        # Iterate through each raw field, expected field.
        for raw_field, expected_field in field_samples:
            # Run this operation in a guarded block so failures can be handled.
            try:
                actual = tx.normalize_edit_field(raw_field)

                if actual == expected_field:
                    ok(
                        "Regression",
                        f"normalize_edit_field('{raw_field}')",
                        expected=expected_field,
                        actual=str(actual),
                    )
                # Use the fallback path when no earlier branch matched.
                else:
                    fail(
                        "Regression",
                        f"normalize_edit_field('{raw_field}')",
                        expected=expected_field,
                        actual=str(actual),
                        error="Field alias edit belum sesuai.",
                    )

            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                fail(
                    "Regression",
                    f"normalize_edit_field('{raw_field}')",
                    expected=expected_field,
                    actual="Exception",
                    error=f"{type(e).__name__}: {str(e)}",
                )
    # Use the fallback path when no earlier branch matched.
    else:
        warn(
            "Regression",
            "normalize_edit_field",
            expected="Function tersedia kalau edit_txn sudah dipasang",
            actual="Missing",
        )

    router = modules.get("app.nlp.gemini_intent_router")

    if router and hasattr(router, "should_try_gemini_intent_router"):
        gemini_trigger_samples = [
            ("cek hutang", True),
            ("cek saldo", True),
            ("lihat transaksi hari ini", True),
            ("lihat transaksi minggu ini", True),
            ("tampilkan saldo", True),
            ("lihat budget bulan ini", True),
            ("cari kopi", True),
            ("hapus transaksi nomor 2", True),
            ("edit transaksi nomor 3 deskripsinya Kopi susu", True),
            ("minguan", False),
            ("detele", False),
            ("bugete", False),
        ]

        # Iterate through each text, expected bool.
        for text, expected_bool in gemini_trigger_samples:
            # Run this operation in a guarded block so failures can be handled.
            try:
                actual = bool(router.should_try_gemini_intent_router(text))

                if actual == expected_bool:
                    ok(
                        "Regression",
                        f"should_try_gemini_intent_router('{text}')",
                        expected=str(expected_bool),
                        actual=str(actual),
                    )
                # Use the fallback path when no earlier branch matched.
                else:
                    warn(
                        "Regression",
                        f"should_try_gemini_intent_router('{text}')",
                        expected=str(expected_bool),
                        actual=str(actual),
                        error="Tidak selalu fatal kalau local natural intent sudah handle, tapi perlu dicek.",
                    )

            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                fail(
                    "Regression",
                    f"should_try_gemini_intent_router('{text}')",
                    expected=str(expected_bool),
                    actual="Exception",
                    error=f"{type(e).__name__}: {str(e)}",
                )
    # Use the fallback path when no earlier branch matched.
    else:
        warn(
            "Regression",
            "gemini_intent_router",
            expected="Ada kalau Gemini intent router sudah dipasang",
            actual="Missing",
        )

    # ── Latest transaction history flow ───────────────────────────────────────
    # Regression test note for a previously fixed edge case.
    # Test note for a project-specific regression case.
    if handlers and hasattr(handlers, "build_last_transactions_text"):
        unsafe_txns = [
            {
                "id": "txn_20260610_abc_def_ghi",
                "date": "2026-06-10",
                "type": "expense",
                "amount": 25000,
                "category": "Food_&_Beverage",
                "account": "BRI_Main",
                "to_account": "",
                "description": "Kopi_susu *enak* [test]",
            },
            {
                "id": "txn_20260610_transfer_test",
                "date": "2026-06-10",
                "type": "transfer",
                "amount": 100000,
                "category": "Transfer",
                "account": "BRI_Main",
                "to_account": "DANA_Wallet",
                "description": "Top_up DANA",
            },
        ]

        # Run this operation in a guarded block so failures can be handled.
        try:
            text = handlers.build_last_transactions_text(unsafe_txns, "Transaksi_Test")

            if isinstance(text, str) and len(text) > 0:
                ok(
                    "Regression",
                    "build_last_transactions_text() dengan karakter raw berbahaya",
                    expected="Tidak crash",
                    actual=text[:120].replace("\n", " ") + "...",
                )
            # Use the fallback path when no earlier branch matched.
            else:
                fail(
                    "Regression",
                    "build_last_transactions_text() dengan karakter raw berbahaya",
                    expected="String output",
                    actual=str(text),
                )

        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            fail(
                "Regression",
                "build_last_transactions_text() dengan karakter raw berbahaya",
                expected="Tidak error",
                actual="Exception",
                error=f"{type(e).__name__}: {str(e)}",
            )
    # Use the fallback path when no earlier branch matched.
    else:
        warn(
            "Regression",
            "build_last_transactions_text",
            expected="Function tersedia",
            actual="Missing",
        )

    command_expectations = [
        ("/start", "start_handler"),
        ("/help", "help_handler"),
        ("/examples", "examples_handler"),
        ("/saldo", "saldo_handler"),
        ("/harian", "harian_handler"),
        ("/mingguan", "mingguan_handler"),
        ("/bulanan", "bulanan_handler"),
        ("/budget", "budget_handler"),
        ("/budget_history", "budget_history_handler"),
        ("/pending", "pending_handler"),
        ("/pending_add", "pending_add_handler"),
        ("/pending_paid", "pending_paid_handler"),
        ("/pending_cancel", "pending_cancel_handler"),
        ("/hutang", "hutang_handler"),
        ("/cari", "cari_handler"),
        ("/last", "last_handler"),
        ("/delete_txn", "delete_txn_handler"),
        ("/edit_txn", "edit_txn_handler"),
        ("/export", "export_handler"),
        ("/recurring", "recurring_handler"),
        ("/recurring_add", "recurring_add_handler"),
        ("/recurring_edit", "recurring_edit_handler"),
        ("/recurring_run", "recurring_run_handler"),
        ("/recurring_off", "recurring_off_handler"),
        ("/health", "health_handler"),
        ("/networth", "networth_handler"),
        ("/assets", "assets_handler"),
        ("/asset_add", "asset_add_handler"),
        ("/asset_update", "asset_update_handler"),
        ("/asset_off", "asset_off_handler"),
        ("/networth_snapshot", "networth_snapshot_handler"),
        ("/networth_history", "networth_history_handler"),
    ]

    # Iterate through each command, handler name.
    for command, handler_name in command_expectations:
        if handlers and hasattr(handlers, handler_name):
            ok(
                "Regression",
                f"{command} -> {handler_name}",
                expected="Handler tersedia",
                actual="Available",
            )
        # Use the fallback path when no earlier branch matched.
        else:
            fail(
                "Regression",
                f"{command} -> {handler_name}",
                expected="Handler tersedia",
                actual="Missing",
            )


# ── Main runner ───────────────────────────────────────────────────────────────

# Helper for main.
def main():
    """Coordinate the main logic in the developer utility script.

    Args:
        None.

    Returns:
        `None` after completing the operation.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    print_header("FINANCE BOT DEBUG CHECK")
    print(f"Project root: {PROJECT_ROOT}")
    print("Mode        : READ ONLY")
    print("Note        : Tidak menjalankan save_transaction, delete, edit, recurring_run, snapshot.")

    check_environment()
    modules = check_imports()
    check_config(modules)
    check_google_sheets(modules)
    check_nlp(modules)
    check_transaction_service(modules)
    check_report_service(modules)
    check_budget_service(modules)
    check_debt_service(modules)
    check_recurring_service(modules)
    check_net_worth_service(modules)
    check_bot_handlers(modules)
    check_scheduler(modules)
    check_regression_commands(modules)
    print_summary()


if __name__ == "__main__":
    # Run this operation in a guarded block so failures can be handled.
    try:
        main()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        print("\nFATAL ERROR:")
        traceback.print_exc()
        # Keep this section separated from the surrounding flow.