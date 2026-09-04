"""Load JSONL regression cases and report field-level assertion failures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"


def load_cases(filename: str) -> list[dict[str, Any]]:
    """Load non-empty JSON objects from one UTF-8 JSONL fixture."""

    path = FIXTURE_ROOT / filename
    cases: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            raise AssertionError(f"Invalid JSONL at {path.name}:{line_number}: {error}") from error
        if not isinstance(case, dict):
            raise AssertionError(f"Case at {path.name}:{line_number} must be a JSON object.")
        cases.append(case)
    return cases


def assert_partial(
    expected: Any,
    actual: Any,
    *,
    case: dict[str, Any],
    field: str = "expected",
    step: str = "single",
) -> None:
    """Recursively compare only fields declared by a fixture expectation."""

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            _fail(case, step, field, expected, actual)
        for key, value in expected.items():
            if key not in actual:
                _fail(case, step, f"{field}.{key}", value, "<missing>")
            assert_partial(value, actual[key], case=case, field=f"{field}.{key}", step=step)
        return

    if isinstance(expected, list):
        if not isinstance(actual, list) or expected != actual:
            _fail(case, step, field, expected, actual)
        return

    if expected != actual:
        _fail(case, step, field, expected, actual)


def _fail(case: dict[str, Any], step: str, field: str, expected: Any, actual: Any) -> None:
    """Raise a diagnostic containing the matrix source and relevant flow."""

    route = (case.get("expected") or {}).get("route", "-")
    flow = (case.get("expected") or {}).get("flow", "-")
    raise AssertionError(
        "\n".join(
            [
                f"Case ID: {case.get('id', '-')}",
                f"Raw input: {case.get('input') or case.get('scenario_name') or '-'}",
                f"Scenario step: {step}",
                f"Field or invariant: {field}",
                f"Expected value: {expected!r}",
                f"Actual value: {actual!r}",
                f"Relevant route/flow: {route}/{flow}",
            ]
        )
    )
