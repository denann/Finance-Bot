"""Typed facade over request-scoped finance worksheet records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from app.sheets.client import get_all_records


@dataclass
class FinanceDataSnapshot:
    """Lazily load each requested finance worksheet through the request cache."""

    loader: Callable[[str], list[dict]] = get_all_records
    _loaded: dict[str, list[dict]] = field(default_factory=dict)

    def records(self, sheet_name: str) -> list[dict]:
        if sheet_name not in self._loaded:
            self._loaded[sheet_name] = [dict(row) for row in self.loader(sheet_name)]
        return [dict(row) for row in self._loaded[sheet_name]]

    @property
    def loaded_worksheets(self) -> tuple[str, ...]:
        return tuple(self._loaded)
