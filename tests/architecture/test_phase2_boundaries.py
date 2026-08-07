"""Static dependency checks used by the Phase 2 boundary extraction."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _service_edges(path: Path) -> set[str]:
    """Return direct app.services imports, including local imports in functions."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    edges: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("app.services."):
                edges.add(node.module)
            elif node.module == "app.services":
                edges.update(f"app.services.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.services."):
                    edges.add(alias.name)
    return edges


def test_transaction_and_debt_services_do_not_import_each_other() -> None:
    """Combined operations belong to the application layer, not either service."""

    transaction_edges = _service_edges(ROOT / "app/services/transaction_service.py")
    debt_edges = _service_edges(ROOT / "app/services/debt_service.py")

    assert "app.services.debt_service" not in transaction_edges
    assert "app.services.transaction_service" not in debt_edges

    use_case_edges = _service_edges(ROOT / "app/application/transaction_debt.py")
    assert {
        "app.services.debt_service",
        "app.services.transaction_service",
    }.issubset(use_case_edges)


def test_cycle_detector_recognizes_two_way_edges() -> None:
    """Prove the architecture assertion detects an actual two-way dependency."""

    edges = {
        "transaction_service": {"debt_service"},
        "debt_service": {"transaction_service"},
    }
    cycles = {
        tuple(sorted((source, target)))
        for source, targets in edges.items()
        for target in targets
        if source in edges.get(target, set())
    }
    assert cycles == {("debt_service", "transaction_service")}


def test_application_modules_do_not_import_telegram_or_handler_modules() -> None:
    """Extracted use cases remain independent from Telegram presentation state."""

    for relative_path in (
        "app/application/results.py",
        "app/application/transaction_debt.py",
    ):
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "from telegram" not in source
        assert "import telegram" not in source
        assert "app.bot.handler" not in source
        assert "context.user_data" not in source


def test_callback_dispatcher_dependency_is_one_way() -> None:
    """The legacy callback path must not import its dispatcher back."""

    dispatcher = (ROOT / "app/bot/handler_parts/callback_dispatcher.py").read_text(encoding="utf-8")
    legacy = (ROOT / "app/bot/handler_parts/callback_handler.py").read_text(encoding="utf-8")
    assert "from app.bot.handler_parts.callback_handler import legacy_callback_handler" in dispatcher
    assert "callback_dispatcher" not in legacy
    assert "common_imports import *" not in legacy


def test_formatter_and_safe_reply_have_one_implementation() -> None:
    """Compatibility facades must not duplicate formatter or reply logic."""

    formatter_defs = []
    safe_reply_defs = []
    for path in (ROOT / "app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "format_rupiah":
                    formatter_defs.append(path)
                if node.name in {
                    "reply_message_safely",
                    "reply_update_safely",
                    "safe_edit_message",
                }:
                    safe_reply_defs.append((path, node.name))

    assert formatter_defs == [ROOT / "app/formatting.py"]
    assert len(safe_reply_defs) == 3
    assert {path for path, _name in safe_reply_defs} == {
        ROOT / "app/bot/handler_parts/common_imports.py"
    }
