"""Static and local guards for public command preview-before-write policy."""

from __future__ import annotations

import ast
from pathlib import Path

from app.bot.command_mutations import execute_command_mutation


ROOT = Path(__file__).resolve().parents[2]


def _called_names(path: Path, function_name: str) -> set[str]:
    """Return simple call names used by one async or sync function."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    target = next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
    )
    return {
        node.func.id
        for node in ast.walk(target)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def test_direct_write_commands_only_build_final_preview() -> None:
    """Handlers in F-007 must not call their write services before confirm."""

    cases = [
        ("app/bot/handler_parts/command_handlers.py", "pending_paid_handler", "mark_pending_paid"),
        ("app/bot/handler_parts/command_handlers.py", "pending_cancel_handler", "cancel_pending_expense"),
        ("app/bot/handler_parts/health_recurring_export.py", "recurring_run_handler", "process_due_recurring_rules"),
        ("app/bot/handler_parts/health_recurring_export.py", "recurring_edit_handler", "edit_recurring_rule"),
        ("app/bot/handler_parts/health_recurring_export.py", "recurring_off_handler", "disable_recurring_rule"),
        ("app/bot/handler_parts/networth_assets.py", "asset_update_handler", "update_asset"),
        ("app/bot/handler_parts/networth_assets.py", "asset_off_handler", "deactivate_asset"),
        ("app/bot/handler_parts/networth_assets.py", "networth_snapshot_handler", "create_net_worth_snapshot"),
    ]
    for relative_path, handler_name, writer_name in cases:
        calls = _called_names(ROOT / relative_path, handler_name)
        assert "send_financial_mutation_preview" in calls
        assert writer_name not in calls


def test_unknown_confirmed_operation_fails_without_write() -> None:
    """The confirmation executor is allow-listed and rejects unknown actions."""

    result = execute_command_mutation("unknown", {})
    assert result["success"] is False
    assert "Tidak ada data yang diubah" in result["display_text"]


def test_recurring_reminder_callback_no_longer_writes_directly() -> None:
    """The reminder callback creates a command action instead of a transaction."""

    calls = _called_names(
        ROOT / "app/bot/handler_parts/callback_handler.py",
        "callback_handler",
    )
    assert "mark_recurring_rule_paid" not in calls
    assert "create_pending_action" in calls


def test_legacy_confirmation_targets_are_rejected_before_routing() -> None:
    """Generic legacy confirms cannot fall back to mutable pending state."""

    source = (ROOT / "app/bot/handler_parts/callback_handler.py").read_text(encoding="utf-8")
    assert "Tombol konfirmasi lama sudah tidak berlaku" in source
    assert 'if confirm_target.startswith("a_")' in source


def test_message_date_guard_runs_before_early_debt_route() -> None:
    """Invalid dates are clarified before the early debt parser can preview."""

    source = (ROOT / "app/bot/handler_parts/message_handlers.py").read_text(encoding="utf-8")
    guard_position = source.index("explicit_date = detect_date_result(user_text)")
    debt_position = source.index("early_debt_parsed = parse_debt_input(user_text)")
    assert guard_position < debt_position


def test_budget_handler_builds_preview_without_writing() -> None:
    """Owner-approved budget mutations must remain preview-before-write."""

    calls = _called_names(
        ROOT / "app/bot/handler_parts/command_handlers.py",
        "set_budget_handler",
    )
    assert "confirm_keyboard" in calls
    assert "set_budget" not in calls

    callback_source = (ROOT / "app/bot/handler_parts/callback_handler.py").read_text(encoding="utf-8")
    budget_branch = callback_source.index('if confirm_target == "budget"')
    budget_write = callback_source.index("result = set_budget", budget_branch)
    assert budget_branch < budget_write
