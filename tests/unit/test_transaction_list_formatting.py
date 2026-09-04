"""Regression checks for the transaction-list command presentation."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _called_names(function_name: str) -> set[str]:
    """Return direct function calls made by a message-handler function."""

    path = ROOT / "app/bot/handler_parts/message_handlers.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    target = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
    )
    return {
        node.func.id
        for node in ast.walk(target)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def test_last_uses_the_latest_transaction_browser() -> None:
    """Keep /last on the current paginated browser and stable reference flow."""

    calls = _called_names("last_handler")
    assert "start_transaction_browser" in calls
    assert "reply_long_markdown" not in calls
