"""Prevent covered synchronous Sheets/Gemini calls from re-entering async handlers."""

from __future__ import annotations

import ast
from pathlib import Path


IO_NAMES = {
    "get_account_balance", "get_all_accounts", "get_budget_summary", "get_budget_months",
    "get_pending_expenses", "find_pending_by_ref", "get_active_debts", "get_debt_by_person",
    "get_recent_transactions", "search_transactions", "get_monthly_report", "get_daily_report",
    "get_weekly_report", "get_account_report", "get_recurring_rule_by_id", "get_recurring_rules",
    "get_due_recurring_rules", "get_assets", "get_asset_by_id", "get_net_worth",
    "get_net_worth_snapshots", "preview_edit_transaction_by_ref",
    "preview_delete_transactions_by_refs", "get_transactions_for_export", "get_all_records",
    "get_all_values", "parse_with_gemini", "parse_with_pending_fallback",
    "generate_category_alias_candidates", "generate_text_with_gemini",
    "generate_text_from_image_with_gemini",
}
WRAPPERS = {"run_sheets_read", "run_gemini", "run_scheduled", "run_external_work", "to_thread"}


def _call_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def test_async_handlers_do_not_call_covered_sync_external_functions_directly() -> None:
    violations: list[str] = []
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parents: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node

        for function in (node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)):
            for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
                name = _call_name(call)
                if name not in IO_NAMES:
                    continue
                current = parents.get(call)
                wrapped = False
                while current is not None and current is not function:
                    if isinstance(current, ast.Call) and _call_name(current) in WRAPPERS:
                        wrapped = True
                        break
                    current = parents.get(current)
                if not wrapped:
                    violations.append(f"{path}:{call.lineno} {function.name} -> {name}")

    assert violations == [], "Synchronous external calls found in async functions:\n" + "\n".join(violations)
