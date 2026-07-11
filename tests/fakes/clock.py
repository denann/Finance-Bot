"""Deterministic clock fake used by date and pending-action tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FrozenClock:
    """Return one fixed timezone-aware or naive datetime for every call."""

    value: datetime

    def now(self) -> datetime:
        """Return the configured fixed datetime without reading the host clock."""

        return self.value
