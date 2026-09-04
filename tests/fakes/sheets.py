"""Small in-memory Google Sheets substitutes with failure injection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FailurePlan:
    """Raise configured exceptions on named mutation attempts."""

    failures: dict[tuple[str, int], Exception] = field(default_factory=dict)
    calls: dict[str, int] = field(default_factory=dict)

    def check(self, operation: str) -> None:
        """Record an operation and raise its configured exception, if any."""

        attempt = self.calls.get(operation, 0) + 1
        self.calls[operation] = attempt
        error = self.failures.get((operation, attempt))
        if error is not None:
            raise error


class InMemoryWorksheet:
    """Represent a worksheet as mutable rows while mimicking used APIs."""

    def __init__(self, title: str, rows: list[list[Any]] | None = None, failure_plan: FailurePlan | None = None):
        self.title = title
        self.rows = [list(row) for row in (rows or [])]
        self.failure_plan = failure_plan or FailurePlan()

    def append_row(self, row: list[Any], **_kwargs: Any) -> dict:
        """Append one row and return a gspread-like updated range."""

        self.failure_plan.check("append_row")
        self.rows.append(list(row))
        return {"updates": {"updatedRange": f"{self.title}!A{len(self.rows)}:Z{len(self.rows)}"}}

    def append_rows(self, rows: list[list[Any]], **_kwargs: Any) -> dict:
        """Append multiple rows and return their gspread-like range."""

        self.failure_plan.check("append_rows")
        start = len(self.rows) + 1
        self.rows.extend(list(row) for row in rows)
        end = len(self.rows)
        return {"updates": {"updatedRange": f"{self.title}!A{start}:Z{end}"}}

    def delete_rows(self, start: int, end: int | None = None) -> None:
        """Delete a one-based inclusive row range."""

        self.failure_plan.check("delete_rows")
        last = end or start
        del self.rows[start - 1:last]

    def get_all_values(self) -> list[list[Any]]:
        """Return a defensive copy of all rows."""

        self.failure_plan.check("get_all_values")
        return [list(row) for row in self.rows]

    def col_values(self, column: int) -> list[Any]:
        """Return one-based column values for append reconciliation."""

        self.failure_plan.check("col_values")
        index = column - 1
        return [row[index] if index < len(row) else "" for row in self.rows]

    def get_all_records(self, **_kwargs: Any) -> list[dict[str, Any]]:
        """Return body rows mapped to the first row as headers."""

        self.failure_plan.check("get_all_records")
        if not self.rows:
            return []
        headers = self.rows[0]
        return [dict(zip(headers, row)) for row in self.rows[1:]]

    def sort(self, *sort_specs: tuple[int, str], range: str) -> dict:
        """Sort body rows using one-based column/direction specifications."""

        self.failure_plan.check("sort")
        assert range.startswith("A2:")
        header, body = self.rows[:1], self.rows[1:]
        for column, direction in reversed(sort_specs):
            index = int(column) - 1
            body.sort(
                key=lambda row: str(row[index] if index < len(row) else ""),
                reverse=str(direction).lower().startswith("des"),
            )
        self.rows = header + body
        return {"sortedRange": range, "sortSpecs": list(sort_specs)}
