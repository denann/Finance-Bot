"""Regression contracts for explicit slash-command routing."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.regression.case_loader import case_id, load_cases


ROOT = Path(__file__).resolve().parents[2]
CASES = load_cases("routing_cases.jsonl")


def _known_commands() -> dict[str, dict]:
    """Read the literal command registry without importing Telegram handlers."""

    path = ROOT / "app/bot/handler_parts/command_router.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assignment = next(
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "KNOWN_COMMANDS" for target in node.targets)
    )
    return ast.literal_eval(assignment.value)


@pytest.mark.regression
@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_slash_command_route(case: dict) -> None:
    """Keep slash-prefixed input in command handling and out of NLP parsing."""

    raw = case["input"]
    assert raw.startswith("/"), f"Case ID: {case['id']} is not slash-prefixed"
    command = raw[1:].split(maxsplit=1)[0].split("@", 1)[0].lower()
    known = _known_commands()
    expected = case["expected"]
    actual_route = "command" if command in known else "unknown_command"

    assert actual_route == expected["route"], (
        f"Case ID: {case['id']}\nRaw input: {raw}\nField: route\n"
        f"Expected: {expected['route']}\nActual: {actual_route}\nFlow: slash_command"
    )
    if expected.get("command"):
        assert command == expected["command"]


def test_unknown_command_handler_does_not_call_natural_parser() -> None:
    """Statically protect the unknown slash path from transaction parsing."""

    path = ROOT / "app/bot/handler_parts/command_router.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    handler = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "unknown_command_handler"
    )
    called = {
        node.func.id for node in ast.walk(handler)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "parse_with_regex" not in called
    assert "parse_input" not in called
