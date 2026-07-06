"""Local command testing script for parser, command routing, and regression checks without running Telegram manually."""

# Import __future__ so this module can use its helpers.
from __future__ import annotations

# Import argparse for this module's local operations.
import argparse
# Import copy for this module's local operations.
import copy
# Import importlib for this module's local operations.
import importlib
# Import importlib.util for this module's local operations.
import importlib.util
# Import json for this module's local operations.
import json
# Import os for this module's local operations.
import os
# Import re for this module's local operations.
import re
# Import sys for this module's local operations.
import sys
# Import types for this module's local operations.
import types
# Import warnings for this module's local operations.
import warnings
# Import dataclasses so this module can use its helpers.
from dataclasses import dataclass, field
# Import pathlib so this module can use its helpers.
from pathlib import Path
# Import typing so this module can use its helpers.
from typing import Any

# Keep Windows output safe when dependencies print emoji/UTF-8 text.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
# Handle an expected failure from the guarded operation above.
except Exception:
    # Keep this intentionally empty block valid.
    pass

warnings.filterwarnings("ignore", category=FutureWarning)

# Prepare PROJECT ROOT for the next step.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Run this statement as part of the current workflow.
sys.path.insert(0, str(PROJECT_ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Implementation note for this project-specific finance flow.
# ─────────────────────────────────────────────────────────────────────────────

# Define ensure test env for callers in this flow.
def _ensure_test_env() -> None:
    """Ensure that setup is ready for test env."""
    # Open a multi-line structure for the values below.
    defaults = {
        "TELEGRAM_BOT_TOKEN": "TEST_TOKEN",
        "TELEGRAM_WEBHOOK_SECRET": "TEST_SECRET",
        "ALLOWED_USER_ID": "0",
        "GOOGLE_SHEET_ID": "TEST_SHEET_ID",
        "GOOGLE_SERVICE_ACCOUNT_JSON": "service_account.json",
        "WEBHOOK_URL": "https://example.test/webhook",
        "APP_PORT": "8000",
    # Close the structure that was opened above.
    }
    # Process each key, value in the current collection.
    for key, value in defaults.items():
        # Run this statement as part of the current workflow.
        os.environ.setdefault(key, value)


# Group the Dummy behavior in one class.
class _Dummy:
    """Class used by Dummy in the developer utility script."""
    # Define init for callers in this flow.
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the surrounding object with the values required by the developer utility script.

        Args:
            *args: Command argument list or parsed argument values supplied by the caller.
            **kwargs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `None` value as defined by the function signature.

        Side effects:
            May print diagnostics, read local files, or call local test helpers according to the utility implementation.

        Flow constraints:
            Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
        """
        # Run this statement as part of the current workflow.
        self.args = args
        # Run this statement as part of the current workflow.
        self.kwargs = kwargs
        # Process each key, value in the current collection.
        for key, value in kwargs.items():
            # Run this statement as part of the current workflow.
            setattr(self, key, value)

    def __call__(self, *args: Any, **kwargs: Any) -> "_Dummy":
        """Coordinate the call logic in the developer utility script.

        Args:
            *args: Command argument list or parsed argument values supplied by the caller.
            **kwargs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `'_Dummy'` value as defined by the function signature.

        Side effects:
            May print diagnostics, read local files, or call local test helpers according to the utility implementation.

        Flow constraints:
            Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
        """
        # Return _Dummy(*args, **kwargs) to the caller.
        return _Dummy(*args, **kwargs)

    # Define iter for callers in this flow.
    def __iter__(self):
        """Coordinate the iter logic in the developer utility script.

        Args:
            None.

        Returns:
            Value produced by the existing return statements; shape is determined by the current implementation.

        Side effects:
            May print diagnostics, read local files, or call local test helpers according to the utility implementation.

        Flow constraints:
            Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
        """
        # Return iter([]) to the caller.
        return iter([])

    # Define bool for callers in this flow.
    def __bool__(self) -> bool:
        """Coordinate the bool logic in the developer utility script.

        Args:
            None.

        Returns:
            `bool` value as defined by the function signature.

        Side effects:
            May print diagnostics, read local files, or call local test helpers according to the utility implementation.

        Flow constraints:
            Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
        """
        # Return False to the caller.
        return False


# Group the DummyBadRequest behavior in one class.
class _DummyBadRequest(Exception):
    """Class used by DummyBadRequest in the developer utility script."""
    # Keep this intentionally empty block valid.
    pass


# Define module exists for callers in this flow.
def _module_exists(module_name: str) -> bool:
    """Coordinate the module exists logic in the developer utility script.

    Args:
        module_name: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this operation in a guarded block so failures can be handled.
    try:
        # Return importlib.util.find_spec(module_name) is not None to the caller.
        return importlib.util.find_spec(module_name) is not None
    # Handle an expected failure from the guarded operation above.
    except Exception:
        # Return False to the caller.
        return False


# Define install optional import stubs for callers in this flow.
def _install_optional_import_stubs() -> None:
    """Coordinate the install optional import stubs logic in the developer utility script.

    Args:
        None.

    Returns:
        `None` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    if not _module_exists("dotenv"):
        dotenv_mod = types.ModuleType("dotenv")
        # Run this statement as part of the current workflow.
        dotenv_mod.load_dotenv = lambda *args, **kwargs: None
        sys.modules.setdefault("dotenv", dotenv_mod)

    if not _module_exists("telegram"):
        telegram_mod = types.ModuleType("telegram")
        # Run this statement as part of the current workflow.
        telegram_mod.Update = _Dummy
        # Run this statement as part of the current workflow.
        telegram_mod.InputFile = _Dummy
        # Run this statement as part of the current workflow.
        telegram_mod.InlineKeyboardButton = _Dummy
        # Run this statement as part of the current workflow.
        telegram_mod.InlineKeyboardMarkup = _Dummy

        telegram_ext_mod = types.ModuleType("telegram.ext")
        # Run this statement as part of the current workflow.
        telegram_ext_mod.ContextTypes = types.SimpleNamespace(DEFAULT_TYPE=_Dummy)
        # Process each name in the current collection.
        for name in [
            "Application", "ApplicationBuilder", "CommandHandler", "MessageHandler",
            "CallbackQueryHandler", "filters",
        # Close the structure that was opened above.
        ]:
            # Run this statement as part of the current workflow.
            setattr(telegram_ext_mod, name, _Dummy)

        telegram_helpers_mod = types.ModuleType("telegram.helpers")
        telegram_helpers_mod.escape_markdown = lambda text, *args, **kwargs: str(text or "")

        telegram_error_mod = types.ModuleType("telegram.error")
        # Run this statement as part of the current workflow.
        telegram_error_mod.BadRequest = _DummyBadRequest

        sys.modules.setdefault("telegram", telegram_mod)
        sys.modules.setdefault("telegram.ext", telegram_ext_mod)
        sys.modules.setdefault("telegram.helpers", telegram_helpers_mod)
        sys.modules.setdefault("telegram.error", telegram_error_mod)

    if not _module_exists("gspread"):
        gspread_mod = types.ModuleType("gspread")
        # Run this statement as part of the current workflow.
        gspread_mod.authorize = lambda *args, **kwargs: _Dummy()
        sys.modules.setdefault("gspread", gspread_mod)

    if not _module_exists("google.generativeai"):
        google_mod = sys.modules.get("google") or types.ModuleType("google")
        genai_mod = types.ModuleType("google.generativeai")
        # Run this statement as part of the current workflow.
        genai_mod.configure = lambda *args, **kwargs: None
        sys.modules.setdefault("google", google_mod)
        sys.modules.setdefault("google.generativeai", genai_mod)
        setattr(google_mod, "generativeai", genai_mod)

    if not _module_exists("google.oauth2.service_account"):
        google_mod = sys.modules.get("google") or types.ModuleType("google")
        oauth2_mod = sys.modules.get("google.oauth2") or types.ModuleType("google.oauth2")
        service_account_mod = types.ModuleType("google.oauth2.service_account")

        # Group the Credentials behavior in one class.
        class _Credentials:
            """Class used by Credentials in the developer utility script."""
            # Apply this decorator before the callable is registered or executed.
            @classmethod
            def from_service_account_file(cls, *args: Any, **kwargs: Any) -> "_Credentials":
                """Coordinate the from service account file logic in the developer utility script.

                Args:
                    *args: Command argument list or parsed argument values supplied by the caller.
                    **kwargs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

                Returns:
                    `'_Credentials'` value as defined by the function signature.

                Side effects:
                    May print diagnostics, read local files, or call local test helpers according to the utility implementation.

                Flow constraints:
                    Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
                """
                # Return cls() to the caller.
                return cls()

        # Run this statement as part of the current workflow.
        service_account_mod.Credentials = _Credentials
        sys.modules.setdefault("google", google_mod)
        sys.modules.setdefault("google.oauth2", oauth2_mod)
        sys.modules.setdefault("google.oauth2.service_account", service_account_mod)
        setattr(google_mod, "oauth2", oauth2_mod)
        setattr(oauth2_mod, "service_account", service_account_mod)

    if not _module_exists("langchain_core.messages"):
        lc_core_mod = sys.modules.get("langchain_core") or types.ModuleType("langchain_core")
        lc_messages_mod = types.ModuleType("langchain_core.messages")

        # Group the HumanMessage behavior in one class.
        class HumanMessage:
            """Class used by HumanMessage in the developer utility script."""
            # Define init for callers in this flow.
            def __init__(self, content: Any):
                """Initialize the surrounding object with the values required by the developer utility script.

                Args:
                    content: Input value supplied by the caller; accepted shape follows the function signature and local validation.

                Returns:
                    `None` after completing the operation.

                Side effects:
                    May print diagnostics, read local files, or call local test helpers according to the utility implementation.

                Flow constraints:
                    Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
                """
                # Run this statement as part of the current workflow.
                self.content = content

        # Run this statement as part of the current workflow.
        lc_messages_mod.HumanMessage = HumanMessage
        sys.modules.setdefault("langchain_core", lc_core_mod)
        sys.modules.setdefault("langchain_core.messages", lc_messages_mod)

    if not _module_exists("langchain_google_genai"):
        lc_google_mod = types.ModuleType("langchain_google_genai")

        # Group the ChatGoogleGenerativeAI behavior in one class.
        class ChatGoogleGenerativeAI:
            """Class used by ChatGoogleGenerativeAI in the developer utility script."""
            # Define init for callers in this flow.
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                """Initialize the surrounding object with the values required by the developer utility script.

                Args:
                    *args: Command argument list or parsed argument values supplied by the caller.
                    **kwargs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

                Returns:
                    `None` value as defined by the function signature.

                Side effects:
                    May print diagnostics, read local files, or call local test helpers according to the utility implementation.

                Flow constraints:
                    Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
                """
                # Keep this intentionally empty block valid.
                pass

            # Define invoke for callers in this flow.
            def invoke(self, *args: Any, **kwargs: Any) -> Any:
                """Coordinate the invoke logic in the developer utility script.

                Args:
                    *args: Command argument list or parsed argument values supplied by the caller.
                    **kwargs: Input value supplied by the caller; accepted shape follows the function signature and local validation.

                Returns:
                    `Any` value as defined by the function signature.

                Side effects:
                    May print diagnostics, read local files, or call local test helpers according to the utility implementation.

                Flow constraints:
                    Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
                """
                raise RuntimeError("LangChain Gemini belum terinstall di environment tester ini.")

        # Run this statement as part of the current workflow.
        lc_google_mod.ChatGoogleGenerativeAI = ChatGoogleGenerativeAI
        sys.modules.setdefault("langchain_google_genai", lc_google_mod)


# ─────────────────────────────────────────────────────────────────────────────
# Implementation note for this project-specific finance flow.
# ─────────────────────────────────────────────────────────────────────────────

# Apply this decorator before the callable is registered or executed.
@dataclass
# Group the AssertionResult behavior in one class.
class AssertionResult:
    """Result model for one assertion inside a command test case."""
    # Run this statement as part of the current workflow.
    path: str
    # Run this statement as part of the current workflow.
    expected: Any
    # Run this statement as part of the current workflow.
    actual: Any
    # Run this statement as part of the current workflow.
    status: str  # PASS | WARNING | FAIL
    message: str = ""


# Apply this decorator before the callable is registered or executed.
@dataclass
# Group the CommandRun behavior in one class.
class CommandRun:
    """Result model for one simulated command or user input run."""
    # Run this statement as part of the current workflow.
    name: str
    # Run this statement as part of the current workflow.
    input_text: str
    # Run this statement as part of the current workflow.
    mode: str
    # Run this statement as part of the current workflow.
    parts: list[str]
    # Run this statement as part of the current workflow.
    items: list[dict[str, Any]]
    # Run this statement as part of the current workflow.
    next_action: str
    prompt: str = ""
    preview: str = ""
    # Run this statement as part of the current workflow.
    after_decision: dict[str, Any] | None = None
    # Run this statement as part of the current workflow.
    import_warnings: list[str] = field(default_factory=list)


# Open a multi-line structure for the values below.
KNOWN_SLASH_COMMANDS = {
    "start", "quickstart", "help", "saldo", "set_saldo", "saldo_set", "set_balance", "harian", "mingguan", "bulanan", "transaksi", "cari",
    "budget", "budget_history", "set_budget", "hutang", "debt", "debt_void", "debt_edit",
    "recurring", "recurring_add", "recurring_run", "recurring_off", "recurring_edit",
    "export", "health", "last", "delete_txn", "edit_txn", "ask", "coach", "insight", "audit",
    "networth", "assets", "liabilities", "asset_add", "liability_add", "asset_update",
    "liability_update", "asset_off", "liability_off", "networth_snapshot", "networth_history",
    "account", "account_set", "account_add", "account_rename", "account_off",
# Close the structure that was opened above.
}


# Define classify known route for callers in this flow.
def classify_known_route(text: str) -> dict[str, Any] | None:
    """Coordinate the classify known route logic in the developer utility script.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `dict[str, Any] | None` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    raw = (text or "").strip()
    # Prepare low for the next step.
    low = raw.lower()
    # Handle the missing or empty raw case.
    if not raw:
        # Return None to the caller.
        return None

    if raw.startswith("/"):
        cmd = raw[1:].split()[0].split("@", 1)[0].lower()
        # Handle the case where cmd in KNOWN_SLASH_COMMANDS.
        if cmd in KNOWN_SLASH_COMMANDS:
            # Return { to the caller.
            return {
                "kind": "command",
                "parsed": {"route": "slash_command", "command": cmd, "args": raw.split(maxsplit=1)[1] if len(raw.split(maxsplit=1)) > 1 else ""},
                "raw": raw,
            # Close the structure that was opened above.
            }
        # Return { to the caller.
        return {
            "kind": "unknown_command",
            "parsed": {"route": "unknown_slash_command", "command": cmd},
            "raw": raw,
        # Close the structure that was opened above.
        }

    # Open a multi-line structure for the values below.
    natural_patterns: list[tuple[str, str]] = [
        (r"^(cek|lihat|tampilkan)\s+saldo\b", "saldo"),
        (r"^(cek|lihat|tampilkan)\s+(hutang|utang|piutang)\b", "hutang"),
        (r"^cari\s+.+", "cari"),
        (r"^(lihat|tampilkan)\s+transaksi\b", "transaksi"),
        (r"^hapus\s+transaksi\s+(nomor\s+)?\d+\b", "delete_txn"),
        (r"^edit\s+transaksi\s+(nomor\s+)?\d+\b", "edit_txn"),
        (r"^set\s+budget\b", "set_budget"),
        (r"^(lihat|cek|tampilkan)\s+budget\b", "budget"),
        (r"^(catat|tambah|add)\s+aset\b", "asset_add"),
        (r"^(catat|tambah|add)\s+(liability|kewajiban)\b", "liability_add"),
        (r"^catat\s+hutang\s+paylater\b", "liability_add"),
        (r"^net\s*worth\b", "networth"),
        (r"^(bayar|catat).+\bsetiap\s+(hari|minggu|bulan|tahun)\b", "recurring_add"),
    # Close the structure that was opened above.
    ]
    # Process each pattern, intent in the current collection.
    for pattern, intent in natural_patterns:
        # Handle the case where re.search(pattern, low).
        if re.search(pattern, low):
            # Return { to the caller.
            return {
                "kind": "natural_command",
                "parsed": {"route": "local_natural_intent", "intent": intent},
                "raw": raw,
            # Close the structure that was opened above.
            }

    # Return None to the caller.
    return None


# Group the CommandTester behavior in one class.
class CommandTester:
    """Command test runner that loads cases, simulates bot behavior, and produces regression reports."""
    # Define init for callers in this flow.
    def __init__(self) -> None:
        """Initialize the surrounding object with the values required by the developer utility script.

        Args:
            None.

        Returns:
            `None` value as defined by the function signature.

        Side effects:
            May print diagnostics, read local files, or call local test helpers according to the utility implementation.

        Flow constraints:
            Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
        """
        # Run this statement as part of the current workflow.
        _ensure_test_env()
        # Run this statement as part of the current workflow.
        _install_optional_import_stubs()
        # Run this statement as part of the current workflow.
        self.import_warnings: list[str] = []
        # Run this statement as part of the current workflow.
        self.handlers = self._import_handlers()

    # Define import handlers for callers in this flow.
    def _import_handlers(self):
        """Coordinate the import handlers logic in the developer utility script.

        Args:
            None.

        Returns:
            Value produced by the existing return statements; shape is determined by the current implementation.

        Side effects:
            May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

        Flow constraints:
            Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
        """
        # Run this operation in a guarded block so failures can be handled.
        try:
            return importlib.import_module("app.bot.handlers")
        # Handle an expected failure from the guarded operation above.
        except Exception as first_error:
            # Run this statement as part of the current workflow.
            _install_optional_import_stubs()
            # Run this operation in a guarded block so failures can be handled.
            try:
                return importlib.import_module("app.bot.handlers")
            # Handle an expected failure from the guarded operation above.
            except Exception as second_error:
                # Raise a clear error so the caller can stop this invalid flow.
                raise RuntimeError(
                    "Gagal import app.bot.handlers. Pastikan kamu menjalankan tester "
                    "dari root project dan dependencies sudah install. "
                    f"First error: {type(first_error).__name__}: {first_error}. "
                    f"Second error: {type(second_error).__name__}: {second_error}"
                # Close the structure that was opened above.
                ) from second_error

    def run_command(self, input_text: str, *, name: str = "manual", decision: str | None = None) -> CommandRun:
        """Coordinate the run command logic in the developer utility script.

        Args:
            input_text: Input value supplied by the caller; accepted shape follows the function signature and local validation.
            name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
            decision: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `CommandRun` value as defined by the function signature.

        Side effects:
            May print diagnostics, read local files, or call local test helpers according to the utility implementation.

        Flow constraints:
            Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
        """
        # Prepare h for the next step.
        h = self.handlers
        raw_text = (input_text or "").strip()

        # Natural input section
        # Implementation note for this project-specific finance flow.
        routed = classify_known_route(raw_text)
        if routed is not None and "\n" not in raw_text and ";" not in raw_text:
            # Return CommandRun( to the caller.
            return CommandRun(
                # Prepare name for the next step.
                name=name,
                # Prepare input text for the next step.
                input_text=input_text,
                mode="single",
                # Prepare parts for the next step.
                parts=[raw_text],
                # Prepare items for the next step.
                items=[self._jsonable_item(routed)],
                next_action=routed["parsed"].get("route", "command_route"),
                prompt=f"Route ke handler: {routed['parsed'].get('command') or routed['parsed'].get('intent')}",
                preview="",
                # Prepare after decision for the next step.
                after_decision=None,
                # Prepare import warnings for the next step.
                import_warnings=self.import_warnings,
            # Close the structure that was opened above.
            )

        # Prepare parts for the next step.
        parts = h.split_user_inputs(input_text)
        mode = "batch" if len(parts) > 1 else "single"

        # Run this statement as part of the current workflow.
        items: list[dict[str, Any]] = []
        # Process each part in the current collection.
        for part in parts:
            # Prepare route item for the next step.
            route_item = classify_known_route(part)
            # Handle the case where route_item is not None.
            if route_item is not None:
                # Update items with the current value.
                items.append(route_item)
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Update items with the current value.
                items.append(h.parse_mixed_item(part))

        if mode == "batch":
            transaction_items = [item for item in items if item.get("kind") == "transaction"]
            # Prepare split needed for the next step.
            split_needed = h.mixed_split_bill_needs_decision(transaction_items) if transaction_items else False
            # Prepare account needed for the next step.
            account_needed = h.mixed_needs_account(items) if items else False
            has_missing_amount = any(item.get("kind") == "missing_amount" for item in items)
            has_failed = any(item.get("kind") in {"failed", "unknown_command"} for item in items)

            # Handle the case where has_missing_amount.
            if has_missing_amount:
                next_action = "ask_missing_amount"
                prompt = "Ada income yang belum punya nominal. Bot harus tanya nominal dulu."
                preview = ""
            # Handle the alternate case where split_needed.
            elif split_needed:
                next_action = "ask_split_bill_status"
                # Prepare prompt for the next step.
                prompt = h.build_mixed_split_bill_queue_prompt(transaction_items)
                preview = ""
            # Handle the alternate case where has_failed.
            elif has_failed:
                next_action = "failed_parse"
                prompt = "Ada item yang gagal diparse. Lihat report detail."
                preview = ""
            # Handle the alternate case where account_needed.
            elif account_needed:
                next_action = "offer_edit_before_account"
                prompt = "Mau edit dulu atau lanjut ke rekening?"
                # Prepare preview for the next step.
                preview = h.build_mixed_preview(items)
            # Handle the fallback path after earlier conditions are skipped.
            else:
                next_action = "offer_edit_before_confirm"
                prompt = "Mau edit dulu atau lanjut simpan?"
                preview = h.build_mixed_preview(items) if items else "Command/natural route parsed."

            # Prepare after decision for the next step.
            after_decision = None
            if decision in {"paid", "unpaid"}:
                # Prepare decided items for the next step.
                decided_items = copy.deepcopy(transaction_items)
                if hasattr(h, "apply_split_bill_decision_to_current_mixed"):
                    # Run this statement as part of the current workflow.
                    decided_items, _ = h.apply_split_bill_decision_to_current_mixed(decided_items, decision)
                # Handle the fallback path after earlier conditions are skipped.
                else:
                    # Prepare decided items for the next step.
                    decided_items = h.apply_split_bill_decision_to_mixed(decided_items, decision)
                # Prepare after decision for the next step.
                after_decision = self._summarize_decision(decided_items, decision)

            # Return CommandRun( to the caller.
            return CommandRun(
                # Prepare name for the next step.
                name=name,
                # Prepare input text for the next step.
                input_text=input_text,
                # Prepare mode for the next step.
                mode=mode,
                # Prepare parts for the next step.
                parts=parts,
                # Prepare items for the next step.
                items=self._jsonable_items(items),
                # Prepare next action for the next step.
                next_action=next_action,
                prompt=str(prompt or ""),
                preview=str(preview or ""),
                # Prepare after decision for the next step.
                after_decision=after_decision,
                # Prepare import warnings for the next step.
                import_warnings=self.import_warnings,
            # Close the structure that was opened above.
            )

        # Input single biasa.
        raw = parts[0] if parts else raw_text
        mixed = items[0] if items else {"kind": "failed", "parsed": {}, "raw": raw}
        parsed = mixed.get("parsed", {}) or {}

        if mixed.get("kind") == "missing_amount":
            next_action = "ask_missing_amount"
            prompt = h.build_missing_amount_prompt(raw, parsed) if hasattr(h, "build_missing_amount_prompt") else "Nominalnya berapa?"
            preview = ""
        elif mixed.get("kind") == "transaction" and h.split_bill_needs_decision(parsed):
            next_action = "ask_split_bill_status"
            # Prepare prompt for the next step.
            prompt = h.build_split_bill_prompt_from_parsed(parsed)
            preview = ""
        elif mixed.get("kind") == "transaction" and h.needs_account(parsed):
            next_action = "offer_edit_before_account"
            prompt = "Mau edit dulu atau lanjut ke rekening?"
            # Prepare preview for the next step.
            preview = h.build_preview(parsed)
        elif mixed.get("kind") == "debt" and not parsed.get("account"):
            next_action = "ask_account"
            prompt = "Pilih rekening cashflow untuk debt/payment ini."
            preview = h.build_debt_account_prompt(parsed) if hasattr(h, "build_debt_account_prompt") else "Debt parsed."
        elif mixed.get("kind") in {"failed", "unknown_command"}:
            next_action = "failed_parse"
            prompt = "Parser gagal memahami input."
            preview = ""
        elif mixed.get("kind") in {"command", "natural_command"}:
            next_action = parsed.get("route", "command_route")
            prompt = f"Route ke handler: {parsed.get('command') or parsed.get('intent')}"
            preview = ""
        # Handle the fallback path after earlier conditions are skipped.
        else:
            next_action = "offer_edit_before_confirm" if mixed.get("kind") == "transaction" else "show_preview"
            prompt = "Mau edit dulu atau lanjut simpan?" if mixed.get("kind") == "transaction" else ""
            preview = h.build_preview(parsed) if mixed.get("kind") == "transaction" else "Debt parsed."

        # Prepare after decision for the next step.
        after_decision = None
        if decision in {"paid", "unpaid"} and mixed.get("kind") == "transaction":
            # Prepare decided parsed for the next step.
            decided_parsed = h.apply_split_bill_decision_to_parsed(copy.deepcopy(parsed), decision)
            after_decision = self._summarize_decision([{"kind": "transaction", "parsed": decided_parsed, "raw": raw}], decision)

        # Return CommandRun( to the caller.
        return CommandRun(
            # Prepare name for the next step.
            name=name,
            # Prepare input text for the next step.
            input_text=input_text,
            # Prepare mode for the next step.
            mode=mode,
            # Prepare parts for the next step.
            parts=parts,
            # Prepare items for the next step.
            items=self._jsonable_items(items),
            # Prepare next action for the next step.
            next_action=next_action,
            prompt=str(prompt or ""),
            preview=str(preview or ""),
            # Prepare after decision for the next step.
            after_decision=after_decision,
            # Prepare import warnings for the next step.
            import_warnings=self.import_warnings,
        # Close the structure that was opened above.
        )

    # Define summarize decision for callers in this flow.
    def _summarize_decision(self, items: list[dict[str, Any]], decision: str) -> dict[str, Any]:
        """Coordinate the summarize decision logic in the developer utility script.

        Args:
            items: Input value supplied by the caller; accepted shape follows the function signature and local validation.
            decision: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `dict[str, Any]` value as defined by the function signature.

        Side effects:
            May print diagnostics, read local files, or call local test helpers according to the utility implementation.

        Flow constraints:
            Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
        """
        # Prepare split items for the next step.
        split_items = []
        # Process each idx, item in the current collection.
        for idx, item in enumerate(items, 1):
            parsed = item.get("parsed", {}) or {}
            split = parsed.get("split_bill") or {}
            # Handle the case where split.
            if split:
                # Open a multi-line structure for the values below.
                split_items.append({
                    "index": idx,
                    "description": parsed.get("description"),
                    "amount_after_decision": parsed.get("amount"),
                    "split_status": split.get("status"),
                    "share_amount": split.get("share_amount"),
                    "total_amount": split.get("total_amount"),
                    "total_receivable": 0 if decision == "paid" else split.get("total_receivable"),
                    "person_names": split.get("person_names"),
                # Close the structure that was opened above.
                })
        return {"decision": decision, "split_items": split_items}

    # Define jsonable item for callers in this flow.
    def _jsonable_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Coordinate the jsonable item logic in the developer utility script.

        Args:
            item: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `dict[str, Any]` value as defined by the function signature.

        Side effects:
            May print diagnostics, read local files, or call local test helpers according to the utility implementation.

        Flow constraints:
            Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
        """
        # Return json.loads(json.dumps(item, ensure_ascii=False, default=str)) to the caller.
        return json.loads(json.dumps(item, ensure_ascii=False, default=str))

    # Define jsonable items for callers in this flow.
    def _jsonable_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Coordinate the jsonable items logic in the developer utility script.

        Args:
            items: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            `list[dict[str, Any]]` value as defined by the function signature.

        Side effects:
            May print diagnostics, read local files, or call local test helpers according to the utility implementation.

        Flow constraints:
            Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
        """
        # Return json.loads(json.dumps(items, ensure_ascii=False, default=str)) to the caller.
        return json.loads(json.dumps(items, ensure_ascii=False, default=str))


# ─────────────────────────────────────────────────────────────────────────────
# Assertions + heuristics
# ─────────────────────────────────────────────────────────────────────────────

# Define get path for callers in this flow.
def get_path(data: Any, path: str) -> Any:
    """Retrieve data needed by the get path workflow in the developer utility script.

    Args:
        data: Structured input data used by the current flow.
        path: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `Any` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Prepare current for the next step.
    current = data
    # Handle the missing or empty path case.
    if not path:
        # Return current to the caller.
        return current
    for token in path.split("."):
        # Handle the case where isinstance(current, list).
        if isinstance(current, list):
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Prepare current for the next step.
                current = current[int(token)]
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Return None to the caller.
                return None
        # Handle the alternate case where isinstance(current, dict).
        elif isinstance(current, dict):
            # Prepare current for the next step.
            current = current.get(token)
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Return None to the caller.
            return None
    # Return current to the caller.
    return current


# Define compare value for callers in this flow.
def compare_value(actual: Any, expected: Any) -> bool:
    """Coordinate the compare value logic in the developer utility script.

    Args:
        actual: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        expected: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Handle the case where isinstance(expected, float) or isinstance(actual, float).
    if isinstance(expected, float) or isinstance(actual, float):
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Return abs(float(actual) - float(expected)) < 1e-6 to the caller.
            return abs(float(actual) - float(expected)) < 1e-6
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Return False to the caller.
            return False
    # Return actual == expected to the caller.
    return actual == expected


# Define evaluate expectations for callers in this flow.
def evaluate_expectations(run: CommandRun, expect: dict[str, Any] | None) -> list[AssertionResult]:
    """Coordinate the evaluate expectations logic in the developer utility script.

    Args:
        run: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        expect: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[AssertionResult]` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this statement as part of the current workflow.
    results: list[AssertionResult] = []
    # Handle the missing or empty expect case.
    if not expect:
        # Return results to the caller.
        return results

    # Prepare run dict for the next step.
    run_dict = command_run_to_dict(run)

    for path, expected in (expect.get("paths") or {}).items():
        # Prepare actual for the next step.
        actual = get_path(run_dict, path)
        # Prepare ok for the next step.
        ok = compare_value(actual, expected)
        # Open a multi-line structure for the values below.
        results.append(AssertionResult(
            # Prepare path for the next step.
            path=path,
            # Prepare expected for the next step.
            expected=expected,
            # Prepare actual for the next step.
            actual=actual,
            status="PASS" if ok else "FAIL",
            message="" if ok else "Value mismatch",
        # Close the structure that was opened above.
        ))

    for field_name in ["prompt_contains", "preview_contains"]:
        source_field = field_name.replace("_contains", "")
        source = str(getattr(run, source_field) or "")
        # Process each text in the current collection.
        for text in expect.get(field_name, []) or []:
            # Prepare ok for the next step.
            ok = str(text).lower() in source.lower()
            # Open a multi-line structure for the values below.
            results.append(AssertionResult(
                # Prepare path for the next step.
                path=field_name,
                expected=f"contains: {text}",
                actual=source[:500] + ("..." if len(source) > 500 else ""),
                status="PASS" if ok else "FAIL",
                message="Text not found" if not ok else "",
            # Close the structure that was opened above.
            ))

    if "item_count" in expect:
        # Prepare actual for the next step.
        actual = len(run.items)
        expected = expect["item_count"]
        # Prepare ok for the next step.
        ok = actual == expected
        # Open a multi-line structure for the values below.
        results.append(AssertionResult(
            path="item_count",
            # Prepare expected for the next step.
            expected=expected,
            # Prepare actual for the next step.
            actual=actual,
            status="PASS" if ok else "FAIL",
            message="Jumlah item tidak sesuai" if not ok else "",
        # Close the structure that was opened above.
        ))

    # Return results to the caller.
    return results


# Define has split keyword for callers in this flow.
def _has_split_keyword(text: str) -> bool:
    """Coordinate the has split keyword logic in the developer utility script.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    return bool(re.search(r"\b(di\s*-?\s*bagi|dibagi|bagi|split|patungan)\b", text, flags=re.IGNORECASE))


# Define split has friend name for callers in this flow.
def _split_has_friend_name(text: str) -> bool:
    """Coordinate the split has friend name logic in the developer utility script.

    Args:
        text: Raw text input to parse, normalize, validate, or display.

    Returns:
        `bool` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    low = re.sub(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", " ", text.lower())
    if re.search(r"\bsama\s+[a-zA-Z][a-zA-Z\s,]+", low):
        # Return True to the caller.
        return True
    m = re.search(r"\b(?:di\s*-?\s*bagi|dibagi|bagi|split|patungan)\s+(?:jadi\s+)?\d+\s+([a-zA-Z][a-zA-Z\s,]*)", low)
    # Handle the case where m.
    if m:
        # Prepare tail for the next step.
        tail = m.group(1).strip()
        # Implementation note for this project-specific finance flow.
        if tail and not re.fullmatch(r"(orang|org|x|kali|bagian)", tail):
            # Return True to the caller.
            return True
    # Return False to the caller.
    return False


# Define evaluate heuristics for callers in this flow.
def evaluate_heuristics(run: CommandRun) -> list[AssertionResult]:
    """Coordinate the evaluate heuristics logic in the developer utility script.

    Args:
        run: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[AssertionResult]` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this statement as part of the current workflow.
    results: list[AssertionResult] = []

    # Handle the missing or empty run.items case.
    if not run.items:
        results.append(AssertionResult("items", "> 0", 0, "FAIL", "Tidak ada item yang diparse."))
        # Return results to the caller.
        return results

    comment_items = [item.get("raw", "") for item in run.items if str(item.get("raw", "")).lstrip().startswith("#")]
    # Open a multi-line structure for the values below.
    results.append(AssertionResult(
        "comments_ignored",
        "no item raw starts with #",
        # Include this value in the surrounding collection or call.
        len(comment_items),
        "PASS" if not comment_items else "FAIL",
        "Baris komentar ikut diparse sebagai transaksi." if comment_items else "",
    # Close the structure that was opened above.
    ))

    failed_items = [item for item in run.items if item.get("kind") in {"failed", "unknown_command"}]
    # Open a multi-line structure for the values below.
    results.append(AssertionResult(
        "no_failed_items",
        # Include this value in the surrounding collection or call.
        0,
        # Include this value in the surrounding collection or call.
        len(failed_items),
        "PASS" if not failed_items else "FAIL",
        "Ada item kind=failed/unknown_command." if failed_items else "",
    # Close the structure that was opened above.
    ))

    bad_slash = [item for item in run.items if str(item.get("raw", "")).strip().startswith("/") and item.get("kind") == "transaction"]
    # Handle the case where bad_slash.
    if bad_slash:
        # Open a multi-line structure for the values below.
        results.append(AssertionResult(
            "slash_command_route",
            "slash command routed as command",
            [item.get("raw") for item in bad_slash],
            "FAIL",
            "Command slash masih masuk parser transaksi.",
        # Close the structure that was opened above.
        ))
    elif any(str(item.get("raw", "")).strip().startswith("/") for item in run.items):
        results.append(AssertionResult("slash_command_route", "command route", "ok", "PASS"))

    # Indonesian decimal comma: 24,7k must stay as one item with amount 24700.
    for item in run.items:
        raw = str(item.get("raw", ""))
        match = re.search(r"(\d+)\s*,\s*(\d+)\s*k\b", raw, flags=re.IGNORECASE)
        # Handle the missing or empty match case.
        if not match:
            # Skip the rest of this loop iteration after handling this case.
            continue
        expected = int(round(float(f"{match.group(1)}.{match.group(2)}") * 1000))
        actual = item.get("parsed", {}).get("amount") if item.get("kind") == "transaction" else None
        # Prepare ok for the next step.
        ok = compare_value(actual, expected)
        # Open a multi-line structure for the values below.
        results.append(AssertionResult(
            "decimal_comma_amount",
            # Include this value in the surrounding collection or call.
            expected,
            # Include this value in the surrounding collection or call.
            actual,
            "PASS" if ok else "FAIL",
            "Nominal koma seperti 24,7k harus dibaca 24700 dan tidak boleh pecah jadi 24 + 7k." if not ok else "",
        # Close the structure that was opened above.
        ))

    # Implementation note for this project-specific finance flow.
    # kemungkinan split_user_inputs memecah koma decimal.
    if re.search(r"\d+\s*,\s*\d+\s*k\b", run.input_text, flags=re.IGNORECASE) and not any(
        re.search(r"\d+\s*,\s*\d+\s*k\b", str(item.get("raw", "")), flags=re.IGNORECASE) for item in run.items
    # Close the structure that was opened above.
    ):
        # Open a multi-line structure for the values below.
        results.append(AssertionResult(
            "decimal_comma_split",
            "single decimal amount item",
            # Include this value in the surrounding collection or call.
            run.parts,
            "FAIL",
            "Input decimal koma pecah saat split_user_inputs.",
        # Close the structure that was opened above.
        ))

    # Implementation note for this project-specific finance flow.
    # Debt flow section
    # The bot should enter the amount clarification flow.
    own_accounts = {"cash", "bri", "bsi", "bca", "dana", "gopay", "seabank", "sea bank"}
    # Process each idx, item in the current collection.
    for idx, item in enumerate(run.items, 1):
        raw = str(item.get("raw", ""))
        # Open a multi-line structure for the values below.
        incoming_match = re.search(
            r"^\s*(?:transaksi|transfer(?:an)?|tf|trf|kiriman|uang)\s+(?:masuk\s+)?dari\s+(.+?)\s*$",
            # Include this value in the surrounding collection or call.
            raw,
            # Prepare flags for the next step.
            flags=re.IGNORECASE,
        # Close the structure that was opened above.
        )
        if incoming_match and not re.search(r"\bdari\s+[^\n]+?\s+ke\s+", raw, flags=re.IGNORECASE):
            # Open a multi-line structure for the values below.
            source = re.sub(
                r"\b(?:tgl|tanggal)\s*\d{1,2}(?:[-/]\d{1,2}(?:[-/]\d{2,4})?)?\b",
                " ",
                # Include this value in the surrounding collection or call.
                incoming_match.group(1),
                # Prepare flags for the next step.
                flags=re.IGNORECASE,
            # Close the structure that was opened above.
            )
            source = re.sub(r"\s+", " ", source).strip().lower()
            first_token = source.split()[0] if source else ""
            # Handle the case where first_token and first_token not in own_accounts.
            if first_token and first_token not in own_accounts:
                actual_kind = item.get("kind")
                actual_type = item.get("parsed", {}).get("type")
                # Open a multi-line structure for the values below.
                has_amount = bool(re.search(
                    r"\d+(?:[.,]\d+)?\s*(?:rb|ribu|k|jt|juta)\b|\b\d{4,}\b",
                    # Include this value in the surrounding collection or call.
                    raw,
                    # Prepare flags for the next step.
                    flags=re.IGNORECASE,
                # Close the structure that was opened above.
                ))
                # Open a multi-line structure for the values below.
                ok = (
                    actual_kind == "transaction" and actual_type == "income"
                # Close the structure that was opened above.
                ) or (
                    not has_amount and actual_kind == "missing_amount" and actual_type == "income"
                # Close the structure that was opened above.
                )
                expected = "transaction income" if has_amount else "ask missing amount income"
                # Open a multi-line structure for the values below.
                results.append(AssertionResult(
                    f"incoming_from_person_income.{idx}",
                    # Include this value in the surrounding collection or call.
                    expected,
                    {"kind": actual_kind, "type": actual_type, "raw": raw},
                    "PASS" if ok else "FAIL",
                    "Transfer/transaksi dari orang harus income biasa; kalau nominal belum ada, harus tanya nominal, bukan debt/outcome." if not ok else "",
                # Close the structure that was opened above.
                ))

    # Implementation note for this project-specific finance flow.
    split_items = [item for item in run.items if _has_split_keyword(str(item.get("raw", "")))]
    # Process each idx, item in the current collection.
    for idx, item in enumerate(split_items, 1):
        raw = str(item.get("raw", ""))
        parsed = item.get("parsed", {}) or {}
        split = parsed.get("split_bill") if item.get("kind") == "transaction" else None
        # Prepare has friend for the next step.
        has_friend = _split_has_friend_name(raw)
        # Handle the case where has_friend and not split.
        if has_friend and not split:
            # Open a multi-line structure for the values below.
            results.append(AssertionResult(
                f"split_bill_detected.{idx}",
                "split_bill object exists",
                # Include this value in the surrounding collection or call.
                item,
                "FAIL",
                "Ada keyword split dan nama teman, tapi split_bill tidak terbentuk.",
            # Close the structure that was opened above.
            ))
        # Handle the alternate case where not has_friend and not split.
        elif not has_friend and not split:
            # Open a multi-line structure for the values below.
            results.append(AssertionResult(
                f"split_bill_no_friend.{idx}",
                "warning/clarification",
                {"raw": raw, "amount": parsed.get("amount")},
                "WARNING",
                "Ada keyword split tapi tidak ada nama teman; aman jika memang sengaja disimpan sebagai bagian pribadi, tapi sebaiknya minta klarifikasi.",
            # Close the structure that was opened above.
            ))
        elif split and split.get("status") is None and run.next_action != "ask_split_bill_status":
            # Open a multi-line structure for the values below.
            results.append(AssertionResult(
                f"split_bill_next_action.{idx}",
                "ask_split_bill_status",
                # Include this value in the surrounding collection or call.
                run.next_action,
                "FAIL",
                "Split bill terbentuk tapi flow tidak tanya sudah dibayar/belum.",
            # Close the structure that was opened above.
            ))
        # Handle the alternate case where split.
        elif split:
            # Open a multi-line structure for the values below.
            results.append(AssertionResult(
                f"split_bill_detected.{idx}",
                "split bill + ask status",
                {"share_amount": split.get("share_amount"), "total_receivable": split.get("total_receivable"), "next_action": run.next_action},
                "PASS",
            # Close the structure that was opened above.
            ))

    # Return results to the caller.
    return results


# Define case status for callers in this flow.
def case_status(assertions: list[AssertionResult]) -> str:
    """Coordinate the case status logic in the developer utility script.

    Args:
        assertions: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    if any(a.status == "FAIL" for a in assertions):
        return "FAIL"
    if any(a.status == "WARNING" for a in assertions):
        return "WARNING"
    return "PASS"


# ─────────────────────────────────────────────────────────────────────────────
# Diagnosis
# ─────────────────────────────────────────────────────────────────────────────

# Define deterministic diagnosis for callers in this flow.
def deterministic_diagnosis(run: CommandRun, assertions: list[AssertionResult]) -> str:
    """Coordinate the deterministic diagnosis logic in the developer utility script.

    Args:
        run: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        assertions: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    failed = [a for a in assertions if a.status == "FAIL"]
    warnings_ = [a for a in assertions if a.status == "WARNING"]
    # Handle the missing or empty failed and not warnings_ case.
    if not failed and not warnings_:
        return "Semua check lolos. Output parser/flow sesuai ekspektasi test case."

    # Run this statement as part of the current workflow.
    tips: list[str] = []
    paths = " ".join(a.path for a in failed + warnings_).lower()
    messages = " ".join(a.message for a in failed + warnings_).lower()

    if "split_bill" in paths:
        tips.append("Cek attach_split_bill_if_any(), extract_split_bill_info(), dan urutan flow sebelum account preview.")
    if "decimal_comma" in paths:
        tips.append("Cek split_user_inputs(): jangan split koma yang berada di antara angka, misalnya 24,7k.")
    if "slash_command" in paths:
        tips.append("Pastikan command slash tidak dikirim ke parse_with_regex; harus ditangani CommandHandler/router dulu.")
    if "no_failed_items" in paths or "failed" in messages:
        tips.append("Cek item raw yang gagal; bisa jadi natural command belum masuk local intent atau regex parser terlalu sempit.")
    # Handle the missing or empty tips case.
    if not tips:
        tips.append("Cek assertion detail, lalu telusuri parser sesuai path yang fail/warning.")

    # Open a multi-line structure for the values below.
    detail_rows = [
        f"- {a.status} {a.path}: expected={a.expected!r}, actual={a.actual!r}"
        # Process each a in the current collection.
        for a in (failed + warnings_)[:10]
    # Close the structure that was opened above.
    ]
    return "Ada temuan.\n\nDetail:\n" + "\n".join(detail_rows) + "\n\nDiagnosis awal:\n" + "\n".join(f"- {t}" for t in tips)


# Define ai diagnosis for callers in this flow.
def ai_diagnosis(run: CommandRun, assertions: list[AssertionResult]) -> str:
    """Coordinate the ai diagnosis logic in the developer utility script.

    Args:
        run: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        assertions: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    if not os.getenv("GEMINI_API_KEY"):
        # Return deterministic_diagnosis(run, assertions) to the caller.
        return deterministic_diagnosis(run, assertions)

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Import app.nlp.gemini_langchain_client so this module can use its helpers.
        from app.nlp.gemini_langchain_client import generate_text_with_gemini

        prompt = f"""
Kamu adalah AI QA agent untuk Telegram bot finance berbahasa Indonesia.
Tugasmu menganalisis hasil command parser dan memberi diagnosis teknis yang actionable.

INPUT USER:
{run.input_text}

HASIL AKTUAL JSON:
{json.dumps(command_run_to_dict(run), ensure_ascii=False, indent=2)}

ASSERTION RESULTS:
{json.dumps([a.__dict__ for a in assertions], ensure_ascii=False, indent=2)}

Berikan jawaban ringkas dalam Bahasa Indonesia dengan format:
1. Status
2. Bug utama jika ada
3. Kemungkinan lokasi fungsi/file yang perlu dicek
4. Saran patch konkret
""".strip()
        # Prepare response for the next step.
        response = generate_text_with_gemini(prompt, temperature=0.0)
        # Return response.strip() if response else deterministic_diagnosis(run... to the caller.
        return response.strip() if response else deterministic_diagnosis(run, assertions)
    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        return deterministic_diagnosis(run, assertions) + f"\n\nAI diagnosis gagal dipanggil: {type(e).__name__}: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# IO + report
# ─────────────────────────────────────────────────────────────────────────────

# Define command run to dict for callers in this flow.
def command_run_to_dict(run: CommandRun) -> dict[str, Any]:
    """Coordinate the command run to dict logic in the developer utility script.

    Args:
        run: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict[str, Any]` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Return { to the caller.
    return {
        "name": run.name,
        "input_text": run.input_text,
        "mode": run.mode,
        "parts": run.parts,
        "items": run.items,
        "next_action": run.next_action,
        "prompt": run.prompt,
        "preview": run.preview,
        "after_decision": run.after_decision,
        "import_warnings": run.import_warnings,
    # Close the structure that was opened above.
    }


# Define resolve input path for callers in this flow.
def resolve_input_path(path_text: str) -> Path:
    """Resolve a user input or reference for input path."""
    # Prepare raw for the next step.
    raw = Path(path_text)
    # Prepare candidates for the next step.
    candidates = [raw]
    # Handle the missing or empty raw.is_absolute() case.
    if not raw.is_absolute():
        # Update candidates with the current value.
        candidates.append(PROJECT_ROOT / raw)
        candidates.append(PROJECT_ROOT / str(path_text).replace("\\", "/"))
    # Process each candidate in the current collection.
    for candidate in candidates:
        # Handle the case where candidate.exists().
        if candidate.exists():
            # Return candidate to the caller.
            return candidate
    # Return raw to the caller.
    return raw


# Define load cases for callers in this flow.
def load_cases(path: Path) -> list[dict[str, Any]]:
    """Retrieve data needed by the load cases workflow in the developer utility script.

    Args:
        path: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict[str, Any]]` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    text = path.read_text(encoding="utf-8")
    # Prepare data for the next step.
    data = json.loads(text)
    if isinstance(data, dict) and "cases" in data:
        return list(data["cases"])
    # Handle the case where isinstance(data, list).
    if isinstance(data, list):
        # Return data to the caller.
        return data
    raise ValueError("Format test file harus list atau object dengan key 'cases'.")


# Define load text cases for callers in this flow.
def load_text_cases(path: Path, *, decision: str | None = None) -> list[dict[str, Any]]:
    """Retrieve data needed by the load text cases workflow in the developer utility script.

    Args:
        path: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        decision: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `list[dict[str, Any]]` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    text = path.read_text(encoding="utf-8-sig")
    # Prepare raw lines for the next step.
    raw_lines = text.splitlines()

    # Define is sep for callers in this flow.
    def is_sep(line: str) -> bool:
        """Check whether a condition is true for sep."""
        return line.strip().strip("\ufeff") == "---"

    # Prepare has blocks for the next step.
    has_blocks = any(is_sep(line) for line in raw_lines)
    # Handle the missing or empty has_blocks case.
    if not has_blocks:
        return [{"name": path.name, "input": text, "decision": decision}]

    # Run this statement as part of the current workflow.
    cases: list[dict[str, Any]] = []
    # Run this statement as part of the current workflow.
    current_lines: list[str] = []
    # Run this statement as part of the current workflow.
    current_name: str | None = None

    # Define flush for callers in this flow.
    def flush() -> None:
        """Coordinate the flush logic in the developer utility script.

        Args:
            None.

        Returns:
            `None` value as defined by the function signature.

        Side effects:
            May print diagnostics, read local files, or call local test helpers according to the utility implementation.

        Flow constraints:
            Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
        """
        # Run this statement as part of the current workflow.
        nonlocal current_lines, current_name
        # Run this statement as part of the current workflow.
        cleaned: list[str] = []
        # Process each line in the current collection.
        for line in current_lines:
            # Prepare stripped for the next step.
            stripped = line.strip()
            # Handle the missing or empty stripped case.
            if not stripped:
                # Skip the rest of this loop iteration after handling this case.
                continue
            if stripped.startswith("#"):
                # Skip the rest of this loop iteration after handling this case.
                continue
            # Update cleaned with the current value.
            cleaned.append(line.rstrip())
        # Handle the case where cleaned.
        if cleaned:
            # Open a multi-line structure for the values below.
            cases.append({
                "name": current_name or f"{path.name} case {len(cases) + 1}",
                "input": "\n".join(cleaned),
                "decision": decision,
            # Close the structure that was opened above.
            })
        # Prepare current lines for the next step.
        current_lines = []
        # Prepare current name for the next step.
        current_name = None

    # Process each line in the current collection.
    for line in raw_lines:
        stripped = line.strip().strip("\ufeff")
        # Handle the case where is_sep(line).
        if is_sep(line):
            # Run this statement as part of the current workflow.
            flush()
            # Skip the rest of this loop iteration after handling this case.
            continue
        if stripped.startswith("#") and current_name is None:
            current_name = stripped.lstrip("#").strip() or None
        # Update current lines with the current value.
        current_lines.append(line)

    # Run this statement as part of the current workflow.
    flush()
    # Return cases to the caller.
    return cases


# Define default sample cases for callers in this flow.
def default_sample_cases() -> list[dict[str, Any]]:
    """Coordinate the default sample cases logic in the developer utility script.

    Args:
        None.

    Returns:
        `list[dict[str, Any]]` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Return [ to the caller.
    return [
        # Open a multi-line structure for the values below.
        {
            "name": "split bill single - dibagi",
            "input": "Nasi kuning 22k dibagi 2 sama sapto 09-05-2026",
            "decision": "unpaid",
            "expect": {
                "item_count": 1,
                "paths": {
                    "mode": "single",
                    "next_action": "ask_split_bill_status",
                    "items.0.kind": "transaction",
                    "items.0.parsed.amount": 22000.0,
                    "items.0.parsed.split_bill.share_amount": 11000.0,
                    "items.0.parsed.split_bill.total_receivable": 11000.0,
                    "items.0.parsed.split_bill.person_names.0": "Sapto",
                    "after_decision.split_items.0.amount_after_decision": 22000.0,
                    "after_decision.split_items.0.split_status": "unpaid",
                # Close the structure that was opened above.
                },
                "prompt_contains": ["Split bill", "Sapto", "Rp22.000", "Rp11.000"],
            # Close the structure that was opened above.
            },
        # Close the structure that was opened above.
        },
        # Open a multi-line structure for the values below.
        {
            "name": "split bill single - paid decision saves own share",
            "input": "Nasi kuning 22k bagi 2 sama sapto 09-05-2026",
            "decision": "paid",
            "expect": {
                "paths": {
                    "next_action": "ask_split_bill_status",
                    "items.0.parsed.amount": 22000.0,
                    "items.0.parsed.split_bill.share_amount": 11000.0,
                    "after_decision.split_items.0.amount_after_decision": 11000.0,
                    "after_decision.split_items.0.total_receivable": 0,
                # Close the structure that was opened above.
                }
            # Close the structure that was opened above.
            },
        # Close the structure that was opened above.
        },
        # Open a multi-line structure for the values below.
        {
            "name": "bulk multiline with split bill first row",
            "input": "Nasi kuning 22k dibagi 2 sama sapto 09-05-2026\nPrint 6k 09-05-2026\nJajan boba 8k 09-05-2026\nBubur ayam pak blankon 15k 10-05-2026\nNasi goreng gila yasmin 10k 10-05-2026\nWr pecel ayam sambal 10k 11-05-2026\nAlquran 80k 11-05-2026\nBakso tetelan 43k dibagi 2 11-05-2026\nNasi padang 10k 16-05-2026\nAyam dcelup 13k 20-05-2026\nTop up dana 3000k 26-05-2026\nBuah tangan si ibu 24.7 k 27-05-2026\nAyam dcelup 13k 28-05-2026\nSop sopan 5k 29-05-2026\nNasi 5k 30-05-2026\nTeh kotjok 15k 31-05-2026\nWarteg bahari 11k 31-05-2026",
            "decision": "unpaid",
            "expect": {
                "item_count": 17,
                "paths": {
                    "mode": "batch",
                    "next_action": "ask_split_bill_status",
                    "items.0.kind": "transaction",
                    "items.0.parsed.amount": 22000.0,
                    "items.0.parsed.split_bill.share_amount": 11000.0,
                    "items.0.parsed.split_bill.person_names.0": "Sapto",
                    "after_decision.split_items.0.amount_after_decision": 22000.0,
                    "after_decision.split_items.0.split_status": "unpaid",
                # Close the structure that was opened above.
                },
                "prompt_contains": ["Split bill", "Nasi", "Sapto", "Rp22.000", "Rp11.000"],
            # Close the structure that was opened above.
            },
        # Close the structure that was opened above.
        },
        # Open a multi-line structure for the values below.
        {
            "name": "top up transfer detection",
            "input": "Top up dana 3000k 26-05-2026",
            "expect": {
                "paths": {
                    "items.0.kind": "transaction",
                    "items.0.parsed.type": "transfer",
                    "items.0.parsed.amount": 3000000,
                # Close the structure that was opened above.
                }
            # Close the structure that was opened above.
            },
        # Close the structure that was opened above.
        },
    # Close the structure that was opened above.
    ]


# Define write sample for callers in this flow.
def write_sample(path: Path) -> None:
    """Apply the write sample operation in the developer utility script.

    Args:
        path: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` value as defined by the function signature.

    Side effects:
        May read from or write to the configured Google Sheets/client state according to the existing implementation.

    Flow constraints:
        Do not change Google Sheets schema or bypass explicit confirmation in caller-managed write flows.
    """
    # Run this statement as part of the current workflow.
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"cases": default_sample_cases()}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# Apply this decorator before the callable is registered or executed.
@dataclass
# Group the CaseResult behavior in one class.
class CaseResult:
    """Represent the CaseResult component in the developer utility script.

    Args:
        None for class construction itself; initializer methods document runtime inputs.

    Returns:
        Class object used by callers in this module or related layers.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Run this statement as part of the current workflow.
    run: CommandRun
    # Run this statement as part of the current workflow.
    assertions: list[AssertionResult]
    # Run this statement as part of the current workflow.
    diagnosis: str


# Define run one case for callers in this flow.
def run_one_case(tester: CommandTester, case: dict[str, Any], index: int, *, use_ai: bool) -> CaseResult:
    """Coordinate the run one case logic in the developer utility script.

    Args:
        tester: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        case: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        index: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        use_ai: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `CaseResult` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    name = case.get("name") or f"case-{index}"
    input_text = case.get("input") or ""
    decision = case.get("decision")
    # Prepare run for the next step.
    run = tester.run_command(input_text, name=name, decision=decision)
    assertions = evaluate_expectations(run, case.get("expect")) + evaluate_heuristics(run)
    diagnosis = ai_diagnosis(run, assertions) if use_ai or any(a.status in {"FAIL", "WARNING"} for a in assertions) else deterministic_diagnosis(run, assertions)
    # Return CaseResult(run=run, assertions=assertions, diagnosis=diagnosis) to the caller.
    return CaseResult(run=run, assertions=assertions, diagnosis=diagnosis)


# Define print case report for callers in this flow.
def print_case_report(result: CaseResult, *, show_json: bool, use_ai: bool) -> None:
    """Coordinate the print case report logic in the developer utility script.

    Args:
        result: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        show_json: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        use_ai: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `None` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Prepare run for the next step.
    run = result.run
    # Prepare assertions for the next step.
    assertions = result.assertions
    failed = [a for a in assertions if a.status == "FAIL"]
    warnings_ = [a for a in assertions if a.status == "WARNING"]
    passed = [a for a in assertions if a.status == "PASS"]
    # Prepare status for the next step.
    status = case_status(assertions)

    print("\n" + "=" * 100)
    print(f"[{status}] {run.name}")
    print("=" * 100)
    print(f"Mode        : {run.mode}")
    print(f"Item count  : {len(run.items)}")
    print(f"Next action : {run.next_action}")
    print(f"Checks      : {len(passed)} PASS, {len(warnings_)} WARNING, {len(failed)} FAIL")

    # Handle the case where run.prompt.
    if run.prompt:
        print("\nPROMPT / NEXT MESSAGE:")
        print(run.prompt[:1500] + ("..." if len(run.prompt) > 1500 else ""))

    # Handle the case where failed or warnings_ or show_json.
    if failed or warnings_ or show_json:
        print("\nCHECK DETAIL:")
        # Process each a in the current collection.
        for a in assertions:
            if a.status == "PASS" and not show_json:
                # Skip the rest of this loop iteration after handling this case.
                continue
            print(f"[{a.status}] {a.path} | expected={a.expected!r} | actual={a.actual!r}")
            # Handle the case where a.message.
            if a.message:
                print(f"  note: {a.message}")

    # Handle the case where use_ai or failed or warnings_.
    if use_ai or failed or warnings_:
        print("\nDIAGNOSIS:")
        # Run this statement as part of the current workflow.
        print(result.diagnosis)

    # Handle the case where show_json.
    if show_json:
        print("\nACTUAL JSON:")
        # Run this statement as part of the current workflow.
        print(json.dumps(command_run_to_dict(run), ensure_ascii=False, indent=2, default=str))


# Define make markdown report for callers in this flow.
def make_markdown_report(results: list[CaseResult]) -> str:
    """Coordinate the make markdown report logic in the developer utility script.

    Args:
        results: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Prepare total for the next step.
    total = len(results)
    pass_count = sum(1 for r in results if case_status(r.assertions) == "PASS")
    warn_count = sum(1 for r in results if case_status(r.assertions) == "WARNING")
    fail_count = sum(1 for r in results if case_status(r.assertions) == "FAIL")

    # Run this statement as part of the current workflow.
    lines: list[str] = []
    lines.append("# AI Command Tester Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Total cases | {total} |")
    lines.append(f"| PASS | {pass_count} |")
    lines.append(f"| WARNING | {warn_count} |")
    lines.append(f"| FAIL | {fail_count} |")
    lines.append("")

    # Handle the case where fail_count or warn_count.
    if fail_count or warn_count:
        lines.append("## Cases with findings")
        lines.append("")
        # Process each idx, result in the current collection.
        for idx, result in enumerate(results, 1):
            # Prepare status for the next step.
            status = case_status(result.assertions)
            if status == "PASS":
                # Skip the rest of this loop iteration after handling this case.
                continue
            lines.append(f"### {idx}. [{status}] {result.run.name}")
            lines.append("")
            lines.append("**Input**")
            lines.append("")
            lines.append("```text")
            # Update lines with the current value.
            lines.append(result.run.input_text.strip())
            lines.append("```")
            lines.append("")
            lines.append(f"- Mode: `{result.run.mode}`")
            lines.append(f"- Item count: `{len(result.run.items)}`")
            lines.append(f"- Next action: `{result.run.next_action}`")
            lines.append("")
            lines.append("**Findings**")
            lines.append("")
            # Process each a in the current collection.
            for a in result.assertions:
                if a.status == "PASS":
                    # Skip the rest of this loop iteration after handling this case.
                    continue
                lines.append(f"- **{a.status}** `{a.path}` — {a.message or 'Check mismatch'}")
                lines.append(f"  - Expected: `{a.expected}`")
                lines.append(f"  - Actual: `{a.actual}`")
            lines.append("")
            lines.append("**Diagnosis**")
            lines.append("")
            lines.append("```text")
            # Update lines with the current value.
            lines.append(result.diagnosis)
            lines.append("```")
            lines.append("")

    lines.append("## All case results")
    lines.append("")
    lines.append("| # | Status | Case | Mode | Items | Next action |")
    lines.append("|---:|---|---|---|---:|---|")
    # Process each idx, result in the current collection.
    for idx, result in enumerate(results, 1):
        # Prepare status for the next step.
        status = case_status(result.assertions)
        safe_name = result.run.name.replace("|", "\\|")
        lines.append(f"| {idx} | {status} | {safe_name} | {result.run.mode} | {len(result.run.items)} | `{result.run.next_action}` |")

    lines.append("")
    lines.append("## Raw actual JSON")
    lines.append("")
    lines.append("```json")
    # Open a multi-line structure for the values below.
    payload = [
        # Open a multi-line structure for the values below.
        {
            "status": case_status(result.assertions),
            "assertions": [a.__dict__ for a in result.assertions],
            "run": command_run_to_dict(result.run),
        # Close the structure that was opened above.
        }
        # Process each result in the current collection.
        for result in results
    # Close the structure that was opened above.
    ]
    # Update lines with the current value.
    lines.append(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


# Define run cases for callers in this flow.
def run_cases(cases: list[dict[str, Any]], *, show_json: bool, use_ai: bool, markdown_path: Path | None = None) -> int:
    """Coordinate the run cases logic in the developer utility script.

    Args:
        cases: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        show_json: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        use_ai: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        markdown_path: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `int` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    # Prepare tester for the next step.
    tester = CommandTester()
    # Run this statement as part of the current workflow.
    results: list[CaseResult] = []

    # Process each i, case in the current collection.
    for i, case in enumerate(cases, 1):
        # Prepare result for the next step.
        result = run_one_case(tester, case, i, use_ai=use_ai)
        # Update results with the current value.
        results.append(result)
        # Run this statement as part of the current workflow.
        print_case_report(result, show_json=show_json, use_ai=use_ai)

    # Prepare total for the next step.
    total = len(results)
    pass_count = sum(1 for r in results if case_status(r.assertions) == "PASS")
    warn_count = sum(1 for r in results if case_status(r.assertions) == "WARNING")
    fail_count = sum(1 for r in results if case_status(r.assertions) == "FAIL")

    print("\n" + "=" * 100)
    print(f"FINAL RESULT: {pass_count} PASS, {warn_count} WARNING, {fail_count} FAIL dari {total} case.")
    # Handle the case where fail_count == 0 and warn_count == 0.
    if fail_count == 0 and warn_count == 0:
        print("Semua test case lolos.")
    # Handle the alternate case where fail_count == 0.
    elif fail_count == 0:
        print("Tidak ada FAIL, tapi masih ada WARNING yang perlu direview.")
    # Handle the fallback path after earlier conditions are skipped.
    else:
        print("Masih ada FAIL yang perlu diperbaiki.")
    print("=" * 100)

    # Handle the case where markdown_path.
    if markdown_path:
        # Run this statement as part of the current workflow.
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(make_markdown_report(results), encoding="utf-8")
        print(f"Markdown report ditulis ke: {markdown_path}")

    # Return 1 if fail_count else 0 to the caller.
    return 1 if fail_count else 0


# Define parse args for callers in this flow.
def parse_args() -> argparse.Namespace:
    """Parse caller input for the parse args workflow in the developer utility script.

    Args:
        None.

    Returns:
        `argparse.Namespace` value as defined by the function signature.

    Side effects:
        May print diagnostics, read local files, or call local test helpers according to the utility implementation.

    Flow constraints:
        Keep behavior compatible with existing callers and avoid unrelated schema or flow changes.
    """
    parser = argparse.ArgumentParser(description="AI/local command tester untuk finance bot.")
    # Prepare src for the next step.
    src = parser.add_mutually_exclusive_group(required=False)
    src.add_argument("--input", help="Satu command/manual input untuk dites.")
    src.add_argument("--input-file", help="File .txt berisi input manual/multiline. Bisa berisi banyak case dipisah baris ---. ")
    src.add_argument("--file", help="File JSON test cases. Default: tests/command_cases.json jika ada.")
    src.add_argument("--sample", action="store_true", help="Jalankan sample built-in test cases.")

    parser.add_argument("--decision", choices=["paid", "unpaid"], help="Simulasikan keputusan split bill.")
    parser.add_argument("--ai", action="store_true", help="Pakai Gemini untuk diagnosis jika GEMINI_API_KEY tersedia.")
    parser.add_argument("--json", action="store_true", help="Tampilkan actual JSON penuh di console.")
    parser.add_argument("--markdown", help="Tulis report Markdown ke file, contoh: --markdown report.md")
    parser.add_argument("--write-sample", action="store_true", help="Tulis sample test ke tests/command_cases.json lalu keluar.")
    # Return parser.parse_args() to the caller.
    return parser.parse_args()


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
    # Prepare args for the next step.
    args = parse_args()

    default_file = PROJECT_ROOT / "tests" / "command_cases.json"
    # Handle the case where args.write_sample.
    if args.write_sample:
        # Run this statement as part of the current workflow.
        write_sample(default_file)
        print(f"Sample test cases ditulis ke: {default_file}")
        # Return 0 to the caller.
        return 0

    # Handle the case where args.input is not None.
    if args.input is not None:
        cases = [{"name": "manual input", "input": args.input, "decision": args.decision}]
    # Handle the alternate case where args.input_file.
    elif args.input_file:
        # Prepare cases for the next step.
        cases = load_text_cases(resolve_input_path(args.input_file), decision=args.decision)
    # Handle the alternate case where args.file.
    elif args.file:
        # Prepare cases for the next step.
        cases = load_cases(resolve_input_path(args.file))
    # Handle the alternate case where args.sample.
    elif args.sample:
        # Prepare cases for the next step.
        cases = default_sample_cases()
    # Handle the alternate case where default_file.exists().
    elif default_file.exists():
        # Prepare cases for the next step.
        cases = load_cases(default_file)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Prepare cases for the next step.
        cases = default_sample_cases()

    # Prepare markdown path for the next step.
    markdown_path = Path(args.markdown) if args.markdown else None
    # Return run_cases(cases, show_json=args.json, use_ai=args.ai, markdow... to the caller.
    return run_cases(cases, show_json=args.json, use_ai=args.ai, markdown_path=markdown_path)


if __name__ == "__main__":
    # Raise a clear error so the caller can stop this invalid flow.
    raise SystemExit(main())
