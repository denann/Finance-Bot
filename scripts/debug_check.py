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

# Prepare PROJECT ROOT for the next step.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Run this statement as part of the current workflow.
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

# Prepare RESULTS for the next step.
RESULTS = []


# Define now str for callers in this flow.
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


# Define rupiah for callers in this flow.
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
        # Return str(amount) to the caller.
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
    # Open a multi-line structure for the values below.
    RESULTS.append(
        # Open a multi-line structure for the values below.
        {
            "area": area,
            "name": name,
            "status": status,
            "expected": expected,
            "actual": actual,
            "error": error,
        # Close the structure that was opened above.
        }
    # Close the structure that was opened above.
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


# Define print header for callers in this flow.
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
    # Run this statement as part of the current workflow.
    print(title)
    print("=" * 90)


# Define print summary for callers in this flow.
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

    # Prepare total for the next step.
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
    # Process each i, r in the current collection.
    for i, r in enumerate(RESULTS, 1):
        # Open a multi-line structure for the values below.
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

    # Handle the case where failed == 0.
    if failed == 0:
        print("✅ RESULT: Tidak ada FAIL. Bot terlihat aman secara structural/read-only check.")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        print("❌ RESULT: Ada FAIL. Cek detail error di atas.")

    print("=" * 90)


# Define safe run for callers in this flow.
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
        # Prepare actual for the next step.
        actual = func()
        # Run this statement as part of the current workflow.
        ok(area, name, expected=expected, actual=actual)
        # Return actual to the caller.
        return actual
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Open a multi-line structure for the values below.
        fail(
            # Include this value in the surrounding collection or call.
            area,
            # Include this value in the surrounding collection or call.
            name,
            # Prepare expected for the next step.
            expected=expected,
            actual="Exception",
            error=f"{type(e).__name__}: {str(e)}",
        # Close the structure that was opened above.
        )
        # Return None to the caller.
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
        # Prepare module for the next step.
        module = importlib.import_module(module_name)
        ok(area, module_name, expected="Module import sukses", actual="Imported")
        # Return module to the caller.
        return module
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Open a multi-line structure for the values below.
        fail(
            # Include this value in the surrounding collection or call.
            area,
            # Include this value in the surrounding collection or call.
            module_name,
            expected="Module import sukses",
            actual="Import failed",
            error=f"{type(e).__name__}: {str(e)}",
        # Close the structure that was opened above.
        )
        # Return None to the caller.
        return None


# Define has function for callers in this flow.
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
    # Handle the case where module is None.
    if module is None:
        skip(area, func_name, expected="Function tersedia", actual="Module tidak tersedia")
        # Return False to the caller.
        return False

    # Prepare exists for the next step.
    exists = hasattr(module, func_name)

    # Handle the case where exists.
    if exists:
        ok(area, func_name, expected="Function tersedia", actual="Available")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        fail(area, func_name, expected="Function tersedia", actual="Missing")

    # Return exists to the caller.
    return exists


# ── 1. Environment check ──────────────────────────────────────────────────────

# Define check environment for callers in this flow.
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

    # Open a multi-line structure for the values below.
    required_envs = [
        "BOT_MODE",
        "TELEGRAM_BOT_TOKEN",
        "ALLOWED_USER_ID",
        "GOOGLE_SHEET_ID",
        "GEMINI_API_KEY",
    # Close the structure that was opened above.
    ]

    # Process each env_name in the current collection.
    for env_name in required_envs:
        # Prepare value for the next step.
        value = os.getenv(env_name)

        # Handle the case where value.
        if value:
            # Prepare masked for the next step.
            masked = str(value)
            # Handle the case where len(masked) > 10.
            if len(masked) > 10:
                masked = masked[:4] + "..." + masked[-4:]
            ok("Env", env_name, expected="Env terisi", actual=masked)
        # Handle the fallback path after earlier conditions are skipped.
        else:
            fail("Env", env_name, expected="Env terisi", actual="Kosong / tidak ditemukan")

    print("Environment check selesai.")


# ── 2. Import check ───────────────────────────────────────────────────────────

# Define check imports for callers in this flow.
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

    # Prepare modules for the next step.
    modules = {}

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    ]

    # Process each module_name in the current collection.
    for module_name in module_names:
        # Run this statement as part of the current workflow.
        modules[module_name] = import_module_safe(module_name)

    # Return modules to the caller.
    return modules


# ── 3. Config constants check ─────────────────────────────────────────────────

# Define check config for callers in this flow.
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

    # Open a multi-line structure for the values below.
    required_constants = [
        "SHEET_TRANSACTIONS",
        "SHEET_ACCOUNTS",
        "SHEET_BUDGETS",
        "SHEET_DEBTS",
        "SHEET_DEBT_PAYMENTS",
    # Close the structure that was opened above.
    ]

    # Open a multi-line structure for the values below.
    optional_constants = [
        "SHEET_RECURRING_RULES",
        "SHEET_RECURRING_LOGS",
        "SHEET_ASSETS",
        "SHEET_PENDING_EXPENSES",
        "SHEET_NET_WORTH_SNAPSHOTS",
    # Close the structure that was opened above.
    ]

    # Process each const in the current collection.
    for const in required_constants:
        # Handle the case where config and hasattr(config, const).
        if config and hasattr(config, const):
            ok("Config", const, expected="Constant tersedia", actual=getattr(config, const))
        # Handle the fallback path after earlier conditions are skipped.
        else:
            fail("Config", const, expected="Constant tersedia", actual="Missing")

    # Process each const in the current collection.
    for const in optional_constants:
        # Handle the case where config and hasattr(config, const).
        if config and hasattr(config, const):
            ok("Config", const, expected="Constant tersedia", actual=getattr(config, const))
        # Handle the fallback path after earlier conditions are skipped.
        else:
            warn("Config", const, expected="Constant tersedia kalau fitur terkait aktif", actual="Missing")


# ── 4. Google Sheets read check ───────────────────────────────────────────────

# Define check google sheets for callers in this flow.
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

    # Handle the missing or empty sheets case.
    if not sheets:
        skip("Sheets", "All checks", expected="Sheets client tersedia", actual="Skipped")
        # Return control to the caller.
        return

    # Open a multi-line structure for the values below.
    safe_run(
        "Sheets",
        "get_spreadsheet()",
        "Koneksi Google Sheets sukses",
        lambda: getattr(sheets.get_spreadsheet(), "title", "Connected"),
    # Close the structure that was opened above.
    )

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    ]

    # Process each label, const_name in the current collection.
    for label, const_name in sheet_constants:
        # Handle the case where config and hasattr(config, const_name).
        if config and hasattr(config, const_name):
            # Prepare sheet name for the next step.
            sheet_name = getattr(config, const_name)

            # Define read sheet for callers in this flow.
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
                # Prepare records for the next step.
                records = sheets.get_all_records(sheet_name)
                return f"{len(records)} row readable"

            safe_run("Sheets", f"Sheet {label}", "Sheet bisa dibaca", read_sheet)
        # Handle the fallback path after earlier conditions are skipped.
        else:
            warn("Sheets", f"Sheet {label}", expected="Constant tersedia", actual=f"{const_name} missing")


# ── 5. NLP parser check ───────────────────────────────────────────────────────

# Define check nlp for callers in this flow.
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
        # Open a multi-line structure for the values below.
        samples = [
            ("25rb", 25000),
            ("8 juta", 8000000),
            ("150.000", 150000),
        # Close the structure that was opened above.
        ]

        # Process each text, expected_amount in the current collection.
        for text, expected_amount in samples:
            # Define run for callers in this flow.
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
                # Return normalizer.extract_amount_from_text(text) to the caller.
                return normalizer.extract_amount_from_text(text)

            actual = safe_run("NLP", f"extract_amount_from_text('{text}')", f"{expected_amount}", run)

            # Handle the case where actual is not None and int(float(actual)) != expected_amount.
            if actual is not None and int(float(actual)) != expected_amount:
                warn("NLP", f"Amount expectation '{text}'", expected=str(expected_amount), actual=str(actual))
    # Handle the fallback path after earlier conditions are skipped.
    else:
        fail("NLP", "extract_amount_from_text", expected="Function tersedia", actual="Missing")

    if regex_parser and hasattr(regex_parser, "parse_with_regex"):
        # Open a multi-line structure for the values below.
        parser_samples = [
            ("beli kopi 25000", "expense"),
            ("gaji masuk 8000000", "income"),
        # Close the structure that was opened above.
        ]

        # Process each text, expected_type in the current collection.
        for text, expected_type in parser_samples:
            # Define run for callers in this flow.
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
                # Prepare parsed for the next step.
                parsed = regex_parser.parse_with_regex(text)
                # Handle the missing or empty parsed case.
                if not parsed:
                    return "None"
                return f"type={parsed.get('type')}, amount={parsed.get('amount')}, category={parsed.get('category')}"

            actual = safe_run("NLP", f"parse_with_regex('{text}')", f"type={expected_type}", run)

            if actual and f"type={expected_type}" not in str(actual):
                warn("NLP", f"Parser expectation '{text}'", expected=f"type={expected_type}", actual=str(actual))
    # Handle the fallback path after earlier conditions are skipped.
    else:
        fail("NLP", "parse_with_regex", expected="Function tersedia", actual="Missing")

    if regex_parser and hasattr(regex_parser, "parse_debt_input"):
        # Open a multi-line structure for the values below.
        debt_samples = [
            "Budi minjem 300000",
            "hutang ke Budi 300000",
            "bayar hutang Budi 100000",
        # Close the structure that was opened above.
        ]

        # Process each text in the current collection.
        for text in debt_samples:
            # Define run for callers in this flow.
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
                # Prepare parsed for the next step.
                parsed = regex_parser.parse_debt_input(text)
                # Handle the missing or empty parsed case.
                if not parsed:
                    return "None"
                return f"intent={parsed.get('intent')}, person={parsed.get('person_name')}, amount={parsed.get('amount')}"

            safe_run("NLP", f"parse_debt_input('{text}')", "Debt intent terbaca", run)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        fail("NLP", "parse_debt_input", expected="Function tersedia", actual="Missing")


# ── 6. Transaction service read-only check ────────────────────────────────────

# Define check transaction service for callers in this flow.
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

    # Open a multi-line structure for the values below.
    required_functions = [
        "get_all_accounts",
        "save_transaction",
        "save_transactions_batch",
    # Close the structure that was opened above.
    ]

    # Open a multi-line structure for the values below.
    optional_functions = [
        "get_recent_transactions",
        "get_transactions_for_export",
        "preview_delete_transactions_by_refs",
        "delete_transactions_by_refs",
        "preview_edit_transaction_by_ref",
        "edit_transaction_by_ref",
    # Close the structure that was opened above.
    ]

    # Process each fn in the current collection.
    for fn in required_functions:
        has_function(tx, fn, "Transaction Service")

    # Process each fn in the current collection.
    for fn in optional_functions:
        if not has_function(tx, fn, "Transaction Service"):
            warn("Transaction Service", fn, expected="Ada kalau phase terkait sudah dipasang", actual="Missing")

    if tx and hasattr(tx, "get_all_accounts"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Transaction Service",
            "get_all_accounts()",
            "List rekening terbaca",
            lambda: f"{len(tx.get_all_accounts())} accounts",
        # Close the structure that was opened above.
        )

    if tx and hasattr(tx, "get_recent_transactions"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Transaction Service",
            "get_recent_transactions(limit=5)",
            "Transaksi terakhir terbaca",
            lambda: f"{len(tx.get_recent_transactions(limit=5))} transactions",
        # Close the structure that was opened above.
        )

    if tx and hasattr(tx, "get_transactions_for_export"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Transaction Service",
            "get_transactions_for_export('month')",
            "Export data bulan ini siap",
            lambda: f"{len(tx.get_transactions_for_export('month').get('records', []))} records",
        # Close the structure that was opened above.
        )


# ── 7. Report service check ───────────────────────────────────────────────────

# Define check report service for callers in this flow.
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

    # Open a multi-line structure for the values below.
    funcs = [
        "get_daily_report",
        "get_weekly_report",
        "get_monthly_report",
        "search_transactions",
    # Close the structure that was opened above.
    ]

    # Process each fn in the current collection.
    for fn in funcs:
        has_function(report, fn, "Report Service")

    if report and hasattr(report, "get_daily_report"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Report Service",
            "get_daily_report()",
            "Report harian terbaca",
            lambda: f"count={report.get_daily_report().get('count')}",
        # Close the structure that was opened above.
        )

    if report and hasattr(report, "get_weekly_report"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Report Service",
            "get_weekly_report()",
            "Report mingguan terbaca",
            lambda: f"count={report.get_weekly_report().get('count')}",
        # Close the structure that was opened above.
        )

    if report and hasattr(report, "get_monthly_report"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Report Service",
            "get_monthly_report()",
            "Report bulanan terbaca",
            lambda: f"count={report.get_monthly_report().get('count')}",
        # Close the structure that was opened above.
        )

    if report and hasattr(report, "search_transactions"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Report Service",
            "search_transactions('kopi')",
            "Search transaksi jalan",
            lambda: f"{len(report.search_transactions('kopi'))} result",
        # Close the structure that was opened above.
        )


# ── 8. Budget service check ───────────────────────────────────────────────────

# Define check budget service for callers in this flow.
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

    # Open a multi-line structure for the values below.
    funcs = [
        "set_budget",
        "get_budget_summary",
        "check_budget_after_transaction",
        "normalize_month",
        "format_month_label",
        "get_budget_months",
    # Close the structure that was opened above.
    ]

    # Process each fn in the current collection.
    for fn in funcs:
        has_function(budget, fn, "Budget Service")

    if budget and hasattr(budget, "get_budget_summary"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Budget Service",
            "get_budget_summary()",
            "Budget summary terbaca",
            lambda: f"{len(budget.get_budget_summary())} category budget",
        # Close the structure that was opened above.
        )

    if budget and hasattr(budget, "get_budget_months"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Budget Service",
            "get_budget_months()",
            "Budget history terbaca",
            lambda: f"{len(budget.get_budget_months())} months",
        # Close the structure that was opened above.
        )


# Debt flow section

# Define check debt service for callers in this flow.
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

    # Open a multi-line structure for the values below.
    funcs = [
        "add_debt",
        "add_payment",
        "get_debt_summary",
        "get_debt_by_person",
    # Close the structure that was opened above.
    ]

    # Process each fn in the current collection.
    for fn in funcs:
        has_function(debt, fn, "Debt Service")

    if debt and hasattr(debt, "get_debt_summary"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Debt Service",
            "get_debt_summary()",
            "Debt summary terbaca",
            # Include this value in the surrounding collection or call.
            lambda: str(debt.get_debt_summary()),
        # Close the structure that was opened above.
        )

    if debt and hasattr(debt, "get_debt_by_person"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Debt Service",
            "get_debt_by_person('__debug_non_existing__')",
            "Search debt aman meski tidak ada",
            lambda: f"{len(debt.get_debt_by_person('__debug_non_existing__'))} result",
        # Close the structure that was opened above.
        )


# ── 10. Recurring service check ───────────────────────────────────────────────

# Define check recurring service for callers in this flow.
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

    # Open a multi-line structure for the values below.
    funcs = [
        "add_recurring_rule",
        "get_recurring_rules",
        "get_due_recurring_rules",
        "process_due_recurring_rules",
        "disable_recurring_rule",
        "edit_recurring_rule",
    # Close the structure that was opened above.
    ]

    # Process each fn in the current collection.
    for fn in funcs:
        has_function(recurring, fn, "Recurring Service")

    if recurring and hasattr(recurring, "get_recurring_rules"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Recurring Service",
            "get_recurring_rules(active_only=False)",
            "Recurring rules terbaca",
            lambda: f"{len(recurring.get_recurring_rules(active_only=False))} rules",
        # Close the structure that was opened above.
        )

    if recurring and hasattr(recurring, "get_due_recurring_rules"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Recurring Service",
            "get_due_recurring_rules()",
            "Due recurring bisa dicek tanpa write",
            lambda: f"{len(recurring.get_due_recurring_rules())} due rules",
        # Close the structure that was opened above.
        )

    if recurring and hasattr(recurring, "process_due_recurring_rules"):
        # Open a multi-line structure for the values below.
        skip(
            "Recurring Service",
            "process_due_recurring_rules()",
            expected="Function ada tapi tidak dijalankan by default",
            actual="Skipped karena bisa membuat transaksi baru",
        # Close the structure that was opened above.
        )


# ── 11. Net worth service check ───────────────────────────────────────────────

# Define check net worth service for callers in this flow.
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

    # Open a multi-line structure for the values below.
    funcs = [
        "add_asset",
        "get_assets",
        "update_asset",
        "deactivate_asset",
        "calculate_net_worth",
        "create_net_worth_snapshot",
        "get_net_worth_snapshots",
    # Close the structure that was opened above.
    ]

    # Process each fn in the current collection.
    for fn in funcs:
        has_function(nw, fn, "Net Worth Service")

    if nw and hasattr(nw, "get_assets"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Net Worth Service",
            "get_assets(active_only=True)",
            "Assets terbaca",
            lambda: f"{len(nw.get_assets(active_only=True))} assets",
        # Close the structure that was opened above.
        )


    if nw and hasattr(nw, "calculate_net_worth"):
        # Define run networth for callers in this flow.
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
            # Prepare summary for the next step.
            summary = nw.calculate_net_worth()
            # Return ( to the caller.
            return (
                f"accounts={rupiah(summary.get('total_accounts'))}, "
                f"assets={rupiah(summary.get('total_assets'))}, "
                f"networth={rupiah(summary.get('net_worth'))}"
            # Close the structure that was opened above.
            )

        # Open a multi-line structure for the values below.
        safe_run(
            "Net Worth Service",
            "calculate_net_worth()",
            "Net worth bisa dihitung",
            # Include this value in the surrounding collection or call.
            run_networth,
        # Close the structure that was opened above.
        )

    if nw and hasattr(nw, "get_net_worth_snapshots"):
        # Open a multi-line structure for the values below.
        safe_run(
            "Net Worth Service",
            "get_net_worth_snapshots(limit=5)",
            "Snapshot history terbaca",
            lambda: f"{len(nw.get_net_worth_snapshots(limit=5))} snapshots",
        # Close the structure that was opened above.
        )

    if nw and hasattr(nw, "create_net_worth_snapshot"):
        # Open a multi-line structure for the values below.
        skip(
            "Net Worth Service",
            "create_net_worth_snapshot()",
            expected="Function ada tapi tidak dijalankan by default",
            actual="Skipped karena menulis snapshot baru",
        # Close the structure that was opened above.
        )


# ── 12. Bot handlers check ────────────────────────────────────────────────────

# Define check bot handlers for callers in this flow.
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

    # Open a multi-line structure for the values below.
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
    # Close the structure that was opened above.
    ]

    # Process each handler_name in the current collection.
    for handler_name in handler_names:
        has_function(handlers, handler_name, "Bot Handlers")


# ── 13. Scheduler check ───────────────────────────────────────────────────────

# Define check scheduler for callers in this flow.
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

    # Open a multi-line structure for the values below.
    job_names = [
        "send_message",
        "job_daily_summary",
        "job_weekly_summary",
        "job_monthly_summary",
        "job_debt_reminder",
        "job_recurring_run",
        "create_scheduler",
    # Close the structure that was opened above.
    ]

    # Process each job_name in the current collection.
    for job_name in job_names:
        has_function(jobs, job_name, "Scheduler")

    if jobs and hasattr(jobs, "create_scheduler"):
        # Define run scheduler check for callers in this flow.
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
            # Prepare scheduler for the next step.
            scheduler = jobs.create_scheduler()
            # Prepare job ids for the next step.
            job_ids = [job.id for job in scheduler.get_jobs()]
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Run this statement as part of the current workflow.
                scheduler.shutdown(wait=False)
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Keep this intentionally empty block valid.
                pass
            return ", ".join(job_ids) if job_ids else "No jobs registered"

        # Open a multi-line structure for the values below.
        safe_run(
            "Scheduler",
            "create_scheduler()",
            "Scheduler bisa dibuat dan punya jobs",
            # Include this value in the surrounding collection or call.
            run_scheduler_check,
        # Close the structure that was opened above.
        )

# ── Regression test section ───────────────────────────────────────────────

# Define check regression commands for callers in this flow.
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
    # Debt flow section
    # Test note for a project-specific regression case.
    if handlers and hasattr(handlers, "message_handler"):
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare source for the next step.
            source = inspect.getsource(handlers.message_handler)

            local_pos = source.find("handle_local_natural_intent")
            debt_pos = source.find("parse_debt_input")

            # Handle the case where local_pos != -1 and debt_pos != -1 and local_pos < debt_pos.
            if local_pos != -1 and debt_pos != -1 and local_pos < debt_pos:
                # Open a multi-line structure for the values below.
                ok(
                    "Regression",
                    "Order: local natural intent sebelum debt parser",
                    expected="handle_local_natural_intent sebelum parse_debt_input",
                    actual="OK",
                # Close the structure that was opened above.
                )
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Open a multi-line structure for the values below.
                fail(
                    "Regression",
                    "Order: local natural intent sebelum debt parser",
                    expected="handle_local_natural_intent harus sebelum parse_debt_input",
                    actual=f"local_pos={local_pos}, debt_pos={debt_pos}",
                    error="Kalau ini FAIL, 'cek hutang' bisa ketangkep debt parser lagi.",
                # Close the structure that was opened above.
                )

        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            # Open a multi-line structure for the values below.
            fail(
                "Regression",
                "Inspect message_handler source",
                expected="Source bisa dibaca",
                actual="Failed",
                error=f"{type(e).__name__}: {str(e)}",
            # Close the structure that was opened above.
            )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Open a multi-line structure for the values below.
        fail(
            "Regression",
            "message_handler tersedia",
            expected="message_handler ada",
            actual="Missing",
        # Close the structure that was opened above.
        )

    # Natural input section
    local_helper_names = [
        "handle_local_natural_intent",
        "maybe_text_is_command_typo",
    # Close the structure that was opened above.
    ]

    # Process each helper_name in the current collection.
    for helper_name in local_helper_names:
        has_function(handlers, helper_name, "Regression")

    # Implementation section
    # Regression test note for a previously fixed edge case.
    # Debt flow section
    if handlers and hasattr(handlers, "maybe_text_is_command_typo"):
        # Open a multi-line structure for the values below.
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
        # Close the structure that was opened above.
        ]

        # Process each text in the current collection.
        for text in samples_should_return_none:
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Prepare result for the next step.
                result = handlers.maybe_text_is_command_typo(text)

                # Handle the case where result is None.
                if result is None:
                    # Open a multi-line structure for the values below.
                    ok(
                        "Regression",
                        f"maybe_text_is_command_typo('{text}')",
                        expected="None, tidak boleh dianggap command typo",
                        actual="None",
                    # Close the structure that was opened above.
                    )
                # Handle the fallback path after earlier conditions are skipped.
                else:
                    # Open a multi-line structure for the values below.
                    fail(
                        "Regression",
                        f"maybe_text_is_command_typo('{text}')",
                        expected="None, tidak boleh dianggap command typo",
                        # Prepare actual for the next step.
                        actual=str(result),
                        error="Ini bisa bikin natural command dicegat sebelum Gemini/local intent.",
                    # Close the structure that was opened above.
                    )

            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                # Open a multi-line structure for the values below.
                fail(
                    "Regression",
                    f"maybe_text_is_command_typo('{text}')",
                    expected="Tidak error",
                    actual="Exception",
                    error=f"{type(e).__name__}: {str(e)}",
                # Close the structure that was opened above.
                )

    # Implementation section
    # Command routing note: exact commands and aliases are checked before similarity-based typo handling.
    if handlers and hasattr(handlers, "maybe_text_is_command_typo"):
        # Open a multi-line structure for the values below.
        samples_should_suggest = [
            "minguan",
            "detele",
            "bugete",
        # Close the structure that was opened above.
        ]

        # Process each text in the current collection.
        for text in samples_should_suggest:
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Prepare result for the next step.
                result = handlers.maybe_text_is_command_typo(text)

                # Handle the case where result.
                if result:
                    # Open a multi-line structure for the values below.
                    ok(
                        "Regression",
                        f"maybe_text_is_command_typo('{text}')",
                        expected="Ada suggestion command",
                        actual=str(result).split("\n")[0],
                    # Close the structure that was opened above.
                    )
                # Handle the fallback path after earlier conditions are skipped.
                else:
                    # Open a multi-line structure for the values below.
                    warn(
                        "Regression",
                        f"maybe_text_is_command_typo('{text}')",
                        expected="Ada suggestion command",
                        actual="None",
                        error="Ini bukan fatal, tapi typo resolver pendek jadi kurang aktif.",
                    # Close the structure that was opened above.
                    )

            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                # Open a multi-line structure for the values below.
                fail(
                    "Regression",
                    f"maybe_text_is_command_typo('{text}')",
                    expected="Tidak error",
                    actual="Exception",
                    error=f"{type(e).__name__}: {str(e)}",
                # Close the structure that was opened above.
                )

    # Debt flow section
    # Note:
    # Debt flow section
    # Debt flow section
    if regex_parser and hasattr(regex_parser, "parse_debt_input"):
        text = "cek hutang"

        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare debt result for the next step.
            debt_result = regex_parser.parse_debt_input(text)

            # Handle the case where debt_result.
            if debt_result:
                # Open a multi-line structure for the values below.
                warn(
                    "Regression",
                    "parse_debt_input('cek hutang')",
                    expected="Lebih aman None, tapi boleh kalau order message_handler sudah benar",
                    # Prepare actual for the next step.
                    actual=str(debt_result),
                    error="Pastikan order local natural intent sebelum debt parser PASS.",
                # Close the structure that was opened above.
                )
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Open a multi-line structure for the values below.
                ok(
                    "Regression",
                    "parse_debt_input('cek hutang')",
                    expected="None",
                    actual="None",
                # Close the structure that was opened above.
                )

        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            # Open a multi-line structure for the values below.
            fail(
                "Regression",
                "parse_debt_input('cek hutang')",
                expected="Tidak error",
                actual="Exception",
                error=f"{type(e).__name__}: {str(e)}",
            # Close the structure that was opened above.
            )

    # Natural input section
    # Regression test note for a previously fixed edge case.
    # Test note for a project-specific regression case.
    if handlers and hasattr(handlers, "parse_local_edit_intent"):
        # Open a multi-line structure for the values below.
        edit_samples = [
            # Open a multi-line structure for the values below.
            (
                "edit transaksi nomor 3 deskripsinya Kopi susu",
                "3",
                "description",
                "Kopi susu",
            # Close the structure that was opened above.
            ),
            # Open a multi-line structure for the values below.
            (
                "edit transaksi nomor 3 deskripsi Kopi susu",
                "3",
                "description",
                "Kopi susu",
            # Close the structure that was opened above.
            ),
            # Open a multi-line structure for the values below.
            (
                "edit transaksi nomor 3 desc Kopi susu",
                "3",
                "description",
                "Kopi susu",
            # Close the structure that was opened above.
            ),
            # Open a multi-line structure for the values below.
            (
                "edit transaksi nomor 3 jadi 15000",
                "3",
                "amount",
                "15000",
            # Close the structure that was opened above.
            ),
        # Close the structure that was opened above.
        ]

        # Process each text, expected_ref, expected_field, expected_contains in the current collection.
        for text, expected_ref, expected_field, expected_contains in edit_samples:
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Prepare parsed for the next step.
                parsed = handlers.parse_local_edit_intent(text)

                # Handle the missing or empty parsed case.
                if not parsed:
                    # Open a multi-line structure for the values below.
                    fail(
                        "Regression",
                        f"parse_local_edit_intent('{text}')",
                        expected=f"ref={expected_ref}, updates.{expected_field}",
                        actual="None",
                        error="Natural edit belum ke-parse.",
                    # Close the structure that was opened above.
                    )
                    # Skip the rest of this loop iteration after handling this case.
                    continue

                ref = str(parsed.get("ref"))
                updates = parsed.get("updates", {}) or {}

                # Prepare field ok for the next step.
                field_ok = expected_field in updates
                value_ok = expected_contains.lower() in str(updates.get(expected_field, "")).lower()

                # Handle the case where ref == expected_ref and field_ok and value_ok.
                if ref == expected_ref and field_ok and value_ok:
                    # Open a multi-line structure for the values below.
                    ok(
                        "Regression",
                        f"parse_local_edit_intent('{text}')",
                        expected=f"ref={expected_ref}, {expected_field}={expected_contains}",
                        # Prepare actual for the next step.
                        actual=str(parsed),
                    # Close the structure that was opened above.
                    )
                # Handle the fallback path after earlier conditions are skipped.
                else:
                    # Open a multi-line structure for the values below.
                    fail(
                        "Regression",
                        f"parse_local_edit_intent('{text}')",
                        expected=f"ref={expected_ref}, {expected_field}={expected_contains}",
                        # Prepare actual for the next step.
                        actual=str(parsed),
                        error="Parser edit natural tidak sesuai expected.",
                    # Close the structure that was opened above.
                    )

            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                # Open a multi-line structure for the values below.
                fail(
                    "Regression",
                    f"parse_local_edit_intent('{text}')",
                    expected="Tidak error",
                    actual="Exception",
                    error=f"{type(e).__name__}: {str(e)}",
                # Close the structure that was opened above.
                )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Open a multi-line structure for the values below.
        warn(
            "Regression",
            "parse_local_edit_intent",
            expected="Function tersedia kalau natural edit sudah dipasang",
            actual="Missing",
        # Close the structure that was opened above.
        )

    # Implementation section
    # Regression test note for a previously fixed edge case.
    # Test note for a project-specific regression case.
    if tx and hasattr(tx, "normalize_edit_field"):
        # Open a multi-line structure for the values below.
        field_samples = [
            ("description", "description"),
            ("deskripsi", "description"),
            ("deskripsinya", "description"),
            ("desc", "description"),
            ("amount", "amount"),
            ("nominal", "amount"),
        # Close the structure that was opened above.
        ]

        # Process each raw_field, expected_field in the current collection.
        for raw_field, expected_field in field_samples:
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Prepare actual for the next step.
                actual = tx.normalize_edit_field(raw_field)

                # Handle the case where actual == expected_field.
                if actual == expected_field:
                    # Open a multi-line structure for the values below.
                    ok(
                        "Regression",
                        f"normalize_edit_field('{raw_field}')",
                        # Prepare expected for the next step.
                        expected=expected_field,
                        # Prepare actual for the next step.
                        actual=str(actual),
                    # Close the structure that was opened above.
                    )
                # Handle the fallback path after earlier conditions are skipped.
                else:
                    # Open a multi-line structure for the values below.
                    fail(
                        "Regression",
                        f"normalize_edit_field('{raw_field}')",
                        # Prepare expected for the next step.
                        expected=expected_field,
                        # Prepare actual for the next step.
                        actual=str(actual),
                        error="Field alias edit belum sesuai.",
                    # Close the structure that was opened above.
                    )

            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                # Open a multi-line structure for the values below.
                fail(
                    "Regression",
                    f"normalize_edit_field('{raw_field}')",
                    # Prepare expected for the next step.
                    expected=expected_field,
                    actual="Exception",
                    error=f"{type(e).__name__}: {str(e)}",
                # Close the structure that was opened above.
                )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Open a multi-line structure for the values below.
        warn(
            "Regression",
            "normalize_edit_field",
            expected="Function tersedia kalau edit_txn sudah dipasang",
            actual="Missing",
        # Close the structure that was opened above.
        )

    # Implementation section
    # Debt flow section
    router = modules.get("app.nlp.gemini_intent_router")

    if router and hasattr(router, "should_try_gemini_intent_router"):
        # Open a multi-line structure for the values below.
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
        # Close the structure that was opened above.
        ]

        # Process each text, expected_bool in the current collection.
        for text, expected_bool in gemini_trigger_samples:
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Prepare actual for the next step.
                actual = bool(router.should_try_gemini_intent_router(text))

                # Handle the case where actual == expected_bool.
                if actual == expected_bool:
                    # Open a multi-line structure for the values below.
                    ok(
                        "Regression",
                        f"should_try_gemini_intent_router('{text}')",
                        # Prepare expected for the next step.
                        expected=str(expected_bool),
                        # Prepare actual for the next step.
                        actual=str(actual),
                    # Close the structure that was opened above.
                    )
                # Handle the fallback path after earlier conditions are skipped.
                else:
                    # Open a multi-line structure for the values below.
                    warn(
                        "Regression",
                        f"should_try_gemini_intent_router('{text}')",
                        # Prepare expected for the next step.
                        expected=str(expected_bool),
                        # Prepare actual for the next step.
                        actual=str(actual),
                        error="Tidak selalu fatal kalau local natural intent sudah handle, tapi perlu dicek.",
                    # Close the structure that was opened above.
                    )

            # Handle an expected failure from the guarded operation above.
            except Exception as e:
                # Open a multi-line structure for the values below.
                fail(
                    "Regression",
                    f"should_try_gemini_intent_router('{text}')",
                    # Prepare expected for the next step.
                    expected=str(expected_bool),
                    actual="Exception",
                    error=f"{type(e).__name__}: {str(e)}",
                # Close the structure that was opened above.
                )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Open a multi-line structure for the values below.
        warn(
            "Regression",
            "gemini_intent_router",
            expected="Ada kalau Gemini intent router sudah dipasang",
            actual="Missing",
        # Close the structure that was opened above.
        )

    # ── Latest transaction history flow ───────────────────────────────────────
    # Regression test note for a previously fixed edge case.
    # Test note for a project-specific regression case.
    if handlers and hasattr(handlers, "build_last_transactions_text"):
        # Open a multi-line structure for the values below.
        unsafe_txns = [
            # Open a multi-line structure for the values below.
            {
                "id": "txn_20260610_abc_def_ghi",
                "date": "2026-06-10",
                "type": "expense",
                "amount": 25000,
                "category": "Food_&_Beverage",
                "account": "BRI_Main",
                "to_account": "",
                "description": "Kopi_susu *enak* [test]",
            # Close the structure that was opened above.
            },
            # Open a multi-line structure for the values below.
            {
                "id": "txn_20260610_transfer_test",
                "date": "2026-06-10",
                "type": "transfer",
                "amount": 100000,
                "category": "Transfer",
                "account": "BRI_Main",
                "to_account": "DANA_Wallet",
                "description": "Top_up DANA",
            # Close the structure that was opened above.
            },
        # Close the structure that was opened above.
        ]

        # Run this operation in a guarded block so failures can be handled.
        try:
            text = handlers.build_last_transactions_text(unsafe_txns, "Transaksi_Test")

            # Handle the case where isinstance(text, str) and len(text) > 0.
            if isinstance(text, str) and len(text) > 0:
                # Open a multi-line structure for the values below.
                ok(
                    "Regression",
                    "build_last_transactions_text() dengan karakter raw berbahaya",
                    expected="Tidak crash",
                    actual=text[:120].replace("\n", " ") + "...",
                # Close the structure that was opened above.
                )
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Open a multi-line structure for the values below.
                fail(
                    "Regression",
                    "build_last_transactions_text() dengan karakter raw berbahaya",
                    expected="String output",
                    # Prepare actual for the next step.
                    actual=str(text),
                # Close the structure that was opened above.
                )

        # Handle an expected failure from the guarded operation above.
        except Exception as e:
            # Open a multi-line structure for the values below.
            fail(
                "Regression",
                "build_last_transactions_text() dengan karakter raw berbahaya",
                expected="Tidak error",
                actual="Exception",
                error=f"{type(e).__name__}: {str(e)}",
            # Close the structure that was opened above.
            )
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Open a multi-line structure for the values below.
        warn(
            "Regression",
            "build_last_transactions_text",
            expected="Function tersedia",
            actual="Missing",
        # Close the structure that was opened above.
        )

    # Implementation section
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
    # Close the structure that was opened above.
    ]

    # Process each command, handler_name in the current collection.
    for command, handler_name in command_expectations:
        # Handle the case where handlers and hasattr(handlers, handler_name).
        if handlers and hasattr(handlers, handler_name):
            # Open a multi-line structure for the values below.
            ok(
                "Regression",
                f"{command} -> {handler_name}",
                expected="Handler tersedia",
                actual="Available",
            # Close the structure that was opened above.
            )
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Open a multi-line structure for the values below.
            fail(
                "Regression",
                f"{command} -> {handler_name}",
                expected="Handler tersedia",
                actual="Missing",
            # Close the structure that was opened above.
            )


# ── Main runner ───────────────────────────────────────────────────────────────

# Define main for callers in this flow.
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

    # Run this statement as part of the current workflow.
    check_environment()
    # Prepare modules for the next step.
    modules = check_imports()
    # Run this statement as part of the current workflow.
    check_config(modules)
    # Run this statement as part of the current workflow.
    check_google_sheets(modules)
    # Run this statement as part of the current workflow.
    check_nlp(modules)
    # Run this statement as part of the current workflow.
    check_transaction_service(modules)
    # Run this statement as part of the current workflow.
    check_report_service(modules)
    # Run this statement as part of the current workflow.
    check_budget_service(modules)
    # Run this statement as part of the current workflow.
    check_debt_service(modules)
    # Run this statement as part of the current workflow.
    check_recurring_service(modules)
    # Run this statement as part of the current workflow.
    check_net_worth_service(modules)
    # Run this statement as part of the current workflow.
    check_bot_handlers(modules)
    # Run this statement as part of the current workflow.
    check_scheduler(modules)
    # Run this statement as part of the current workflow.
    check_regression_commands(modules)
    # Run this statement as part of the current workflow.
    print_summary()


if __name__ == "__main__":
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Run this statement as part of the current workflow.
        main()
    # Handle an expected failure from the guarded operation above.
    except Exception:
        print("\nFATAL ERROR:")
        # Run this statement as part of the current workflow.
        traceback.print_exc()
        # Keep this section separated from the surrounding flow.