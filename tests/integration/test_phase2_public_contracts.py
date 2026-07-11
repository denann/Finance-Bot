"""Public command, callback, routing, tester, and liability contracts."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys

from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from app.bot.application import register_handlers
from app.bot.callback_contracts import LEGACY_CALLBACK_PREFIXES, LEGACY_EXACT_CALLBACKS
from app.bot.command_registry import PUBLIC_COMMANDS
from app.bot.handler_parts.bulk_flow import BULK_CALLBACK_PREFIXES
from app.bot.handler_parts.command_router import resolve_command_local


ROOT = Path(__file__).resolve().parents[2]

EXPECTED_COMMANDS = (
    "start", "quickstart", "cancel", "batal", "help", "manual", "privacy",
    "examples", "contoh", "health", "saldo", "set_saldo", "saldo_set",
    "set_balance", "rekening", "harian", "mingguan", "bulanan", "grafik",
    "chart", "cari", "last", "transaksi", "delete_txn", "edit_txn",
    "download_data", "export", "budget", "set_budget", "budget_history",
    "kategori", "categories", "list_kategori", "add_kategori",
    "tambah_kategori", "add_category", "edit_kategori", "ubah_kategori",
    "edit_category", "pending", "pending_add", "rencana", "pending_paid",
    "pending_cancel", "hutang", "ringkasan_hutang", "debt_void", "debt_edit",
    "debt_settle", "recurring", "recurring_add", "recurring_run",
    "recurring_edit", "recurring_off", "networth", "assets", "asset_add",
    "asset_update", "asset_off", "networth_snapshot", "networth_history",
    "insight", "ask", "audit", "coach",
)

EXPECTED_CALLBACK_PREFIXES = {
    "acc:", "batch_acc:", "bulk_edit_category_choice:", "cancel", "cancel:a_",
    "category_type:", "clarify_parse:", "confirm:", "debt_acc:",
    "debt_batch_acc:", "debt_overpay:", "debt_settle_acc:",
    "debt_settle_overpay:", "edit_category_choice:", "editflow:",
    "meal_guard:", "meal_split:", "mixed_acc:", "pay_debt:",
    "recurring_paid:", "set_balance_similar:", "split:",
}

EXPECTED_EXACT_CALLBACKS = {
    "asset_add:skip", "receipt:all", "receipt:part", "recurring_add:skip",
}


class _RecordingApplication:
    """Collect python-telegram-bot handlers without starting an application."""

    def __init__(self) -> None:
        self.handlers: list[object] = []
        self.error_handlers: list[object] = []

    def add_handler(self, handler: object) -> None:
        self.handlers.append(handler)

    def add_error_handler(self, handler: object) -> None:
        self.error_handlers.append(handler)


def _registered_handlers() -> list[object]:
    app = _RecordingApplication()
    register_handlers(app)  # type: ignore[arg-type]
    return app.handlers


def _callback_literals() -> tuple[set[str], set[str]]:
    path = ROOT / "app/bot/handler_parts/callback_handler.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    prefixes: set[str] = set()
    exact: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "startswith"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "data"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            prefixes.add(node.args[0].value)
        if (
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Name)
            and node.left.id == "data"
        ):
            for comparator in node.comparators:
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                    exact.add(comparator.value)
    return prefixes, exact


def test_registered_command_snapshot() -> None:
    """Protect every public command name and alias in registration order."""

    commands = tuple(
        next(iter(handler.commands))
        for handler in _registered_handlers()
        if isinstance(handler, CommandHandler)
    )
    assert commands == EXPECTED_COMMANDS
    assert PUBLIC_COMMANDS == EXPECTED_COMMANDS


def test_message_route_precedence_snapshot() -> None:
    """Specific command/message routes must remain ahead of generic fallbacks."""

    handlers = _registered_handlers()
    assert isinstance(handlers[-4], MessageHandler)
    assert handlers[-4].callback.__name__ == "unknown_command_handler"
    assert isinstance(handlers[-3], MessageHandler)
    assert handlers[-3].callback.__name__ == "image_handler"
    assert isinstance(handlers[-2], MessageHandler)
    assert handlers[-2].callback.__name__ == "message_handler"
    assert isinstance(handlers[-1], CallbackQueryHandler)
    assert handlers[-1].callback.__name__ == "callback_handler"


def test_callback_contract_snapshot() -> None:
    """Protect callback prefixes and exact callback values before extraction."""

    prefixes, exact = _callback_literals()
    assert prefixes == EXPECTED_CALLBACK_PREFIXES
    assert exact == EXPECTED_EXACT_CALLBACKS
    assert set(LEGACY_CALLBACK_PREFIXES) == EXPECTED_CALLBACK_PREFIXES
    assert LEGACY_EXACT_CALLBACKS == EXPECTED_EXACT_CALLBACKS
    assert BULK_CALLBACK_PREFIXES == (
        "bulk_acc:",
        "bulk_split:",
        "bulk_rewrite:",
        "bulk_remove:",
        "bulk_cancel:",
    )


def test_public_handler_import_smoke() -> None:
    """The stable app.bot.handlers facade remains import-compatible."""

    from app.bot import handlers

    for name in (
        "start_handler", "message_handler", "callback_handler", "debt_void_handler",
        "asset_add_handler", "recurring_run_handler", "error_handler",
    ):
        assert callable(getattr(handlers, name))
    assert not any("liabil" in name.lower() for name in dir(handlers))


def test_historical_tester_cli_entry_points() -> None:
    """Both documented tester paths remain executable and offline for --help."""

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    for relative_path in (
        "scripts/ai_command_tester.py",
        "app/scripts/ai_command_tester.py",
    ):
        completed = subprocess.run(
            [sys.executable, str(ROOT / relative_path), "--help"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert "--sample" in completed.stdout


def test_tester_uses_runtime_command_registry_and_one_implementation() -> None:
    """The canonical tester and runtime agree on every registered command."""

    from app.scripts.ai_command_tester import KNOWN_SLASH_COMMANDS

    assert KNOWN_SLASH_COMMANDS == set(PUBLIC_COMMANDS)
    assert not any("liabil" in command for command in KNOWN_SLASH_COMMANDS)
    wrapper = (ROOT / "scripts/ai_command_tester.py").read_text(encoding="utf-8")
    implementation = (ROOT / "app/scripts/ai_command_tester.py").read_text(encoding="utf-8")
    assert "class CommandTester" not in wrapper
    assert "from app.scripts.ai_command_tester import main" in wrapper
    assert "class CommandTester" in implementation


def test_liability_commands_are_explicitly_unavailable() -> None:
    """Removed liability commands direct users to the canonical debt workflow."""

    for command in ("liabilities", "liability_add", "liability_update", "liability_off"):
        result = resolve_command_local(command)
        assert result["status"] == "unavailable"
        assert "/hutang" in result["message"]
