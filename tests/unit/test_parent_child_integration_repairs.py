import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _module(path: str) -> ast.Module:
    return ast.parse((ROOT / path).read_text(encoding="utf-8"))


def _call_name(node: ast.Call) -> str:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        return fn.attr
    return ""


def test_final_delete_callback_imports_preview_revalidation_primitive():
    tree = _module("app/bot/handler_parts/callback_handler.py")
    imported = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "app.bot.handler_parts.common_imports"
        for alias in node.names
    }
    load_sites = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Load)
        and node.id == "preview_delete_transactions_by_refs"
    ]

    assert load_sites, "final delete callback no longer references the preview revalidation primitive"
    assert "preview_delete_transactions_by_refs" in imported


def test_parse_clarification_branches_retire_browser_before_creating_new_flow():
    tree = _module("app/bot/handler_parts/message_handlers.py")
    handler = next(
        node for node in tree.body
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
        and node.name == "message_handler"
    )

    clarification_branches = []
    for node in ast.walk(handler):
        if not isinstance(node, ast.If):
            continue
        calls = [sub for sub in ast.walk(node) if isinstance(sub, ast.Call)]
        if any(_call_name(call) == "send_parse_clarification" for call in calls):
            clarification_branches.append(node)

    assert len(clarification_branches) == 2
    for branch in clarification_branches:
        # The first two direct awaits in each clarification branch must be
        # browser retirement followed by creation/rendering of clarification.
        direct_await_calls = []
        for stmt in branch.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Await) and isinstance(stmt.value.value, ast.Call):
                direct_await_calls.append(_call_name(stmt.value.value))
        assert direct_await_calls[:2] == [
            "retire_transaction_browser_for_new_message",
            "send_parse_clarification",
        ]
